"""AI helper functions shared by recommendation handlers."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import html
import json
import logging
import random
import re
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Set, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.commands import COMMAND_ADD, slash
from bot.handlers_cache import _normalize_title_for_dedupe
from core.ai_text import AITextError, generate_text_reply, is_text_ai_enabled
from core.recommendations import CandidateMovie, lookup_omdb_details

logger = logging.getLogger(__name__)

_AI_CACHE_TTL_SECONDS = 30 * 24 * 60 * 60
_AI_RESPONSE_CACHE: Dict[str, Tuple[float, str]] = {}
_AI_CACHE_LOCK = threading.RLock()
_MIN_RECOMMEND_YEAR = 2000
_NO_VALID_RECOMMENDATIONS_TEXT = (
    "<b>New Recommendations</b>\n"
    "Не нашёл подходящих фильмов с годом выхода 2000+."
)

_QUERY_STOPWORDS = {
    "и",
    "или",
    "на",
    "в",
    "во",
    "с",
    "со",
    "для",
    "про",
    "по",
    "как",
    "что",
    "мне",
    "мой",
    "моя",
    "мои",
    "наши",
    "лучшие",
    "фильмы",
    "фильм",
    "сериал",
    "сериалы",
    "recommend",
    "movie",
    "movies",
    "please",
    "new",
}

_QUERY_SEMANTIC_SYNONYMS = {
    "island": {"insular"},
    "survival": {"survive", "survivor"},
    "остров": {"island", "insular"},
    "выжив": {"survival", "survive", "survivor"},
    "космос": {"space", "spaceship", "astronaut"},
    "зомби": {"zombie", "undead"},
}


def _extract_year_from_title_label(title: str) -> Optional[int]:
    match = re.search(r"\((\d{4})\)", title or "")
    if not match:
        return None
    try:
        year = int(match.group(1))
    except ValueError:
        return None
    return year if 1888 <= year <= 2100 else None


def _is_allowed_recommendation_year(year: Optional[int]) -> bool:
    return isinstance(year, int) and year >= _MIN_RECOMMEND_YEAR


def _filter_candidates_by_min_year(
    candidates: List[CandidateMovie],
    *,
    min_year: int = _MIN_RECOMMEND_YEAR,
) -> List[CandidateMovie]:
    return [
        item
        for item in candidates
        if isinstance(item.year, int) and item.year >= min_year
    ]


def _clean_title_for_prefill(title: str) -> str:
    clean_title = re.sub(r"\(\d{4}\)", "", title or "")
    clean_title = re.sub(r"\s+", " ", clean_title).strip().replace(";", ",")
    return clean_title or "Название"


def _build_add_prefill_query(title: str, year: Optional[int]) -> str:
    clean_title = _clean_title_for_prefill(title)
    year_value = year if year and 1888 <= year <= 2100 else datetime.now().year
    prefill = f"{slash(COMMAND_ADD)} {clean_title};{year_value};жанр;8"
    if len(prefill) > 220:
        prefill = prefill[:220].rstrip()
    return prefill


def _short_button_title(title: str, *, max_len: int = 32) -> str:
    clean = _clean_title_for_prefill(title)
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 1].rstrip() + "…"


def _build_quick_add_keyboard(title: str, year: Optional[int]) -> InlineKeyboardMarkup:
    prefill = _build_add_prefill_query(title, year)
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(
                "➕ Добавить этот фильм в таблицу",
                switch_inline_query_current_chat=prefill,
            )
        ]]
    )


def _build_watched_dedupe_lookup(records: List[Dict[str, str]]) -> Set[str]:
    watched: Set[str] = set()
    for row in records:
        title = (
            row.get("Фильм")
            or row.get("Название")
            or row.get("Film")
            or row.get("Title")
            or ""
        )
        normalized = _normalize_title_for_dedupe(str(title))
        if normalized:
            watched.add(normalized)
    return watched


def _pick_weighted_random_candidate(
    candidates: List[CandidateMovie],
    *,
    top_pool: int = 35,
) -> CandidateMovie:
    pool = candidates[: max(1, top_pool)]
    weights = [max(item.score, 0.1) for item in pool]
    return random.choices(pool, weights=weights, k=1)[0]


def _parse_single_recommendation(answer: str) -> Tuple[str, str]:
    for raw_line in answer.splitlines():
        line = raw_line.replace("**", "").strip()
        line = re.sub(r"^[-*]\s*", "", line)
        line = re.sub(r"^\d+[\.\)]\s*", "", line)
        if not line:
            continue
        if ":" in line and " - " not in line and not re.search(r"\(\d{4}\)", line):
            continue
        if " - " in line:
            title, reason = line.split(" - ", 1)
        else:
            title, reason = line, ""
        title = title.strip(" .")
        reason = reason.strip(" .")
        if title:
            return title, reason
    return "", ""


def _extract_json_dict(text: str) -> Optional[Dict[str, object]]:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    candidate = raw
    if not candidate.startswith("{"):
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            return None
        candidate = match.group(0)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


async def _ai_single_unseen_pick(
    profile_summary: str,
    blocked_titles: List[str],
) -> Optional[Tuple[str, str]]:
    if not is_text_ai_enabled():
        return None

    blocked_norm_lookup = {
        _normalize_title_for_dedupe(item)
        for item in blocked_titles
        if _normalize_title_for_dedupe(item)
    }
    blocked_preview = ", ".join(blocked_titles[:200])
    prompt = (
        "Задача: предложи РОВНО 1 НОВЫЙ фильм, который пользователь еще НЕ смотрел.\n"
        "Нужно опираться на высоко оцененные жанры и похожесть по сюжету.\n"
        "Год фильма должен быть не раньше 2000.\n"
        "Не делай вывод только по одному общему широкому жанру.\n"
        "В обосновании укажи конкретные совпадения (2-3 жанра или сюжетные мотивы).\n"
        "Нельзя предлагать фильмы из списка ниже.\n\n"
        f"Уже просмотрено: {blocked_preview}\n\n"
        "Профиль вкуса:\n"
        f"{profile_summary}\n\n"
        "Ответ в формате:\n"
        "<Название (Год)> - <почему это подходит>\n"
        "Без markdown."
    )

    for _ in range(2):
        try:
            answer = await asyncio.to_thread(
                generate_text_reply,
                prompt,
                temperature=0.45,
                max_output_tokens=220,
            )
        except AITextError as exc:
            logger.error("AI ERROR: %s %s", type(exc).__name__, exc)
            return None
        except Exception as exc:
            logger.error("AI ERROR: %s %s", type(exc).__name__, exc)
            return None

        title, reason = _parse_single_recommendation(answer)
        if not title:
            continue
        year = _extract_year_from_title_label(title)
        if not _is_allowed_recommendation_year(year):
            continue
        if _normalize_title_for_dedupe(title) in blocked_norm_lookup:
            continue
        if not reason:
            reason = "Похоже по жанрам и оценкам в вашей таблице."
        return title, reason

    return None


def _get_ai_cached_response(cache_key: str) -> Optional[str]:
    with _AI_CACHE_LOCK:
        cached = _AI_RESPONSE_CACHE.get(cache_key)
    if not cached:
        return None
    expires_at, text = cached
    if time.time() <= expires_at:
        return text
    with _AI_CACHE_LOCK:
        _AI_RESPONSE_CACHE.pop(cache_key, None)
    return None


def _store_ai_cached_response(cache_key: str, text: str) -> None:
    with _AI_CACHE_LOCK:
        _AI_RESPONSE_CACHE[cache_key] = (time.time() + _AI_CACHE_TTL_SECONDS, text)


def _build_ai_cache_key(prompt: str, profile_summary: str) -> str:
    raw = f"{prompt}\n{profile_summary}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _extract_titles_from_formatted_recommendations(text: str) -> List[str]:
    titles: List[str] = []
    for raw in re.findall(r"<b>(.*?)</b>", text):
        title = html.unescape(raw).strip()
        lowered = title.lower()
        if lowered in {"new recommendations", "wildcard"}:
            continue
        if not _is_allowed_recommendation_year(_extract_year_from_title_label(title)):
            continue
        titles.append(title)
    return titles


def _build_quick_add_keyboard_from_formatted(
    text: str,
) -> Tuple[Optional[InlineKeyboardMarkup], List[str]]:
    titles = _extract_titles_from_formatted_recommendations(text)
    if not titles:
        return None, titles

    unique_titles: List[str] = []
    seen: Set[str] = set()
    for title in titles:
        key = _normalize_title_for_dedupe(title)
        if not key or key in seen:
            continue
        seen.add(key)
        unique_titles.append(title)

    if not unique_titles:
        return None, []

    rows: List[List[InlineKeyboardButton]] = []
    for index, title in enumerate(unique_titles[:8], start=1):
        year = _extract_year_from_title_label(title)
        prefill = _build_add_prefill_query(title, year)
        button_label = f"➕ {index}. {_short_button_title(title)}"
        rows.append(
            [
                InlineKeyboardButton(
                    button_label,
                    switch_inline_query_current_chat=prefill,
                )
            ]
        )

    return InlineKeyboardMarkup(rows), unique_titles


def _filter_recent_candidates(
    candidates: List[CandidateMovie],
    recent_titles: List[str],
) -> List[CandidateMovie]:
    if not candidates or not recent_titles:
        return candidates
    blocked = {_normalize_title_for_dedupe(title) for title in recent_titles}
    return [
        item
        for item in candidates
        if _normalize_title_for_dedupe(item.title) not in blocked
    ]


def _query_keywords(prompt: str) -> Set[str]:
    words = re.findall(r"[A-Za-zА-Яа-я0-9]{3,}", (prompt or "").lower())
    return {word for word in words if word not in _QUERY_STOPWORDS}


def _expand_query_keywords(keywords: Set[str]) -> Set[str]:
    if not keywords:
        return set()
    expanded = set(keywords)
    for token in list(keywords):
        for pattern, synonyms in _QUERY_SEMANTIC_SYNONYMS.items():
            if token == pattern or token.startswith(pattern) or pattern in token:
                expanded.update(synonyms)
    return expanded


def _candidate_text_blob(candidate: CandidateMovie) -> str:
    # Intentionally ignore "reason": it may be generated from query and can cause false relevance hits.
    parts = [candidate.title, candidate.omdb_plot, ", ".join(candidate.genres)]
    return " ".join(part for part in parts if part).lower()


def _hard_filter_tmdb_candidates(
    candidates: Sequence[CandidateMovie],
    *,
    prompt: str,
    strict_query: bool,
    min_year: int = _MIN_RECOMMEND_YEAR,
    max_items: int = 40,
) -> List[CandidateMovie]:
    if not candidates:
        return []

    keywords = _expand_query_keywords(_query_keywords(prompt))
    required_hits = 1
    if strict_query and len(keywords) >= 3:
        required_hits = 2
    if strict_query and len(keywords) >= 6:
        required_hits = 3
    filtered: List[CandidateMovie] = []
    seen_titles: Set[str] = set()
    for item in candidates:
        if not isinstance(item.year, int) or item.year < min_year:
            continue
        norm_title = _normalize_title_for_dedupe(item.title)
        if not norm_title or norm_title in seen_titles:
            continue

        has_quality = (item.tmdb_rating >= 6.0) or ((item.imdb_rating or 0.0) >= 6.0)
        enough_votes = item.vote_count >= 80 or item.imdb_rating is not None
        if not has_quality and not enough_votes:
            continue

        relevance_bonus = 0.0
        if keywords:
            blob = _candidate_text_blob(item)
            hits = sum(1 for token in keywords if token in blob)
            if strict_query and hits < required_hits:
                continue
            relevance_bonus = float(hits) * 1.6

        ranked_score = item.score + relevance_bonus
        filtered.append(
            CandidateMovie(
                tmdb_id=item.tmdb_id,
                title=item.title,
                year=item.year,
                tmdb_rating=item.tmdb_rating,
                vote_count=item.vote_count,
                genres=list(item.genres),
                score=ranked_score,
                reason=item.reason,
                imdb_rating=item.imdb_rating,
                omdb_plot=item.omdb_plot,
                poster_url=item.poster_url,
            )
        )
        seen_titles.add(norm_title)

    filtered.sort(key=lambda movie: movie.score, reverse=True)
    if strict_query and keywords and len(filtered) < 5:
        # Relax query matching only when pool is too small.
        relaxed = [
            item
            for item in candidates
            if isinstance(item.year, int) and item.year >= min_year
        ]
        relaxed.sort(key=lambda movie: movie.score, reverse=True)
        for item in relaxed:
            norm_title = _normalize_title_for_dedupe(item.title)
            if not norm_title or norm_title in seen_titles:
                continue
            blob = _candidate_text_blob(item)
            hits = sum(1 for token in keywords if token in blob)
            if hits <= 0:
                continue
            filtered.append(item)
            seen_titles.add(norm_title)
            if len(filtered) >= max_items:
                break
    return filtered[:max_items]


def _render_candidates_as_formatted(
    candidates: Sequence[CandidateMovie],
    *,
    max_items: int = 8,
) -> str:
    if not candidates:
        return _NO_VALID_RECOMMENDATIONS_TEXT
    lines = ["<b>New Recommendations</b>"]
    for index, item in enumerate(candidates[: max(1, max_items)], start=1):
        year = item.year or datetime.now().year
        title_label = f"{item.title} ({year})"
        reason = item.reason or "matches your genres and ratings history"
        lines.append(
            f"{index}. <b>{html.escape(title_label)}</b> - {html.escape(reason)}"
        )
    return "\n".join(lines)


def _restrict_formatted_to_candidate_pool(
    text: str,
    candidates: Sequence[CandidateMovie],
    *,
    max_items: int = 8,
) -> str:
    if not text or not candidates:
        return text

    lookup = {
        _normalize_title_for_dedupe(item.title): item
        for item in candidates
        if _normalize_title_for_dedupe(item.title)
    }
    if not lookup:
        return text

    output_lines: List[str] = []
    title_pattern = re.compile(r"<b>(.*?)</b>")
    for line in text.splitlines():
        if "<b>New Recommendations</b>" in line:
            output_lines.append("<b>New Recommendations</b>")
            continue
        if not line.strip():
            continue
        match = title_pattern.search(line)
        if not match:
            continue
        title_label = html.unescape(match.group(1)).strip()
        norm_label = _normalize_title_for_dedupe(title_label)
        if norm_label in {"new recommendations", "wildcard"}:
            continue
        candidate = lookup.get(norm_label)
        if not candidate:
            # Also try matching without year suffix.
            normalized = _normalize_title_for_dedupe(re.sub(r"\(\d{4}\)", "", title_label))
            candidate = lookup.get(normalized)
        if not candidate:
            continue
        year = candidate.year or _extract_year_from_title_label(title_label) or datetime.now().year
        final_title = f"{candidate.title} ({year})"
        reason = candidate.reason or "matches your genres and ratings history"
        output_lines.append(
            f"<b>{html.escape(final_title)}</b> - {html.escape(reason)}"
        )

    deduped_lines: List[str] = []
    seen: Set[str] = set()
    for line in output_lines:
        if line == "<b>New Recommendations</b>":
            deduped_lines.append(line)
            continue
        title_match = re.search(r"<b>(.*?)</b>", line)
        if not title_match:
            continue
        key = _normalize_title_for_dedupe(html.unescape(title_match.group(1)))
        if not key or key in seen:
            continue
        seen.add(key)
        deduped_lines.append(line)
        if len(seen) >= max_items:
            break

    if len(seen) == 0:
        return _render_candidates_as_formatted(candidates, max_items=max_items)

    numbered: List[str] = ["<b>New Recommendations</b>"]
    index = 1
    for line in deduped_lines:
        if line == "<b>New Recommendations</b>":
            continue
        numbered.append(f"{index}. {line}")
        index += 1
    return "\n".join(numbered)


def _rating_cache_key_from_title_label(title_label: str) -> str:
    title_norm = _normalize_title_for_dedupe(_clean_title_for_prefill(title_label))
    year = _extract_year_from_title_label(title_label)
    return f"{title_norm}::{year or ''}"


def _lookup_imdb_rating_label(title_label: str) -> str:
    year = _extract_year_from_title_label(title_label)
    clean_title = _clean_title_for_prefill(title_label)
    details = lookup_omdb_details(clean_title, year)
    if not details:
        return ""

    raw = str(details.get("imdbRating") or "").strip()
    if not raw or raw.lower() == "n/a":
        return ""
    try:
        value = float(raw.replace(",", "."))
    except ValueError:
        return ""
    if value <= 0:
        return ""
    return f"IMDb {value:.1f}/10"


def _enrich_formatted_recommendations_with_ratings(
    text: str,
    *,
    max_items: int = 8,
) -> str:
    lines = text.splitlines()
    if not lines:
        return text

    title_labels: List[str] = []
    seen_keys: Set[str] = set()
    for raw in re.findall(r"<b>(.*?)</b>", text):
        title = html.unescape(raw).strip()
        lowered = title.lower()
        if lowered in {"new recommendations", "wildcard"}:
            continue
        if not _is_allowed_recommendation_year(_extract_year_from_title_label(title)):
            continue
        key = _rating_cache_key_from_title_label(title)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        title_labels.append(title)

    if not title_labels:
        return text

    top_labels = title_labels[: max(1, max_items)]
    rating_map: Dict[str, str] = {}

    def _fetch_one(label: str) -> Tuple[str, str]:
        return _rating_cache_key_from_title_label(label), _lookup_imdb_rating_label(label)

    with ThreadPoolExecutor(max_workers=min(4, len(top_labels))) as executor:
        futures = [executor.submit(_fetch_one, label) for label in top_labels]
        for future in as_completed(futures):
            try:
                key, rating = future.result()
            except Exception as exc:
                logger.error("OMDB RATING ENRICH ERROR: %s %s", type(exc).__name__, exc)
                continue
            if rating:
                rating_map[key] = rating

    if not rating_map:
        return text

    enriched_lines: List[str] = []
    line_pattern = re.compile(r"(<b>(.*?)</b>)\s*-\s*(.*)$")
    for line in lines:
        match = line_pattern.search(line)
        if not match:
            enriched_lines.append(line)
            continue

        title_label = html.unescape(match.group(2)).strip()
        key = _rating_cache_key_from_title_label(title_label)
        rating_label = rating_map.get(key)
        if not rating_label:
            enriched_lines.append(line)
            continue

        reason_text = html.unescape(match.group(3)).strip()
        if re.search(r"(?i)\b(imdb|tmdb)\b", reason_text):
            enriched_lines.append(line)
            continue

        new_reason = f"{rating_label} • {reason_text}" if reason_text else rating_label
        prefix = line[: match.start()]
        enriched_lines.append(f"{prefix}<b>{html.escape(title_label)}</b> - {html.escape(new_reason)}")

    return "\n".join(enriched_lines)


def _format_ai_answer_for_telegram(answer: str) -> str:
    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    if not lines:
        return "<b>New Recommendations</b>\nNo data."

    numbered_items: List[str] = []
    wildcard_item: Optional[str] = None
    wildcard_mode = False
    index = 1

    for raw_line in lines:
        line = raw_line.replace("**", "").strip()
        lowered = line.lower()

        if "wildcard" in lowered or "card" in lowered:
            wildcard_mode = True
            continue

        line = re.sub(r"^[-*]\s*", "", line)
        line = re.sub(r"^\d+[\.\)]\s*", "", line)
        if not line:
            continue

        if ":" in line and not re.search(r"\(\d{4}\)", line) and " - " not in line:
            if "card" in lowered:
                wildcard_mode = True
            continue

        if " - " in line:
            title, reason = line.split(" - ", 1)
        else:
            if not re.search(r"\(\d{4}\)", line):
                continue
            title, reason = line, ""

        title = title.strip(" .")
        reason = reason.strip(" .")
        year = _extract_year_from_title_label(title)
        if not _is_allowed_recommendation_year(year):
            continue
        if not reason:
            reason = "matches your genres and ratings history"

        formatted = f"<b>{html.escape(title)}</b> - {html.escape(reason)}"
        if wildcard_mode and wildcard_item is None:
            wildcard_item = formatted
        else:
            numbered_items.append(f"{index}. {formatted}")
            index += 1

    if not numbered_items and not wildcard_item:
        return _NO_VALID_RECOMMENDATIONS_TEXT

    parts = ["<b>New Recommendations</b>"]
    parts.extend(numbered_items[:8])
    if wildcard_item:
        parts.append("")
        parts.append("<b>Wildcard</b>")
        parts.append(f"* {wildcard_item}")
    return "\n".join(parts)


__all__ = [
    "_extract_year_from_title_label",
    "_is_allowed_recommendation_year",
    "_filter_candidates_by_min_year",
    "_build_quick_add_keyboard",
    "_build_watched_dedupe_lookup",
    "_pick_weighted_random_candidate",
    "_parse_single_recommendation",
    "_extract_json_dict",
    "_ai_single_unseen_pick",
    "_get_ai_cached_response",
    "_store_ai_cached_response",
    "_build_ai_cache_key",
    "_extract_titles_from_formatted_recommendations",
    "_build_quick_add_keyboard_from_formatted",
    "_filter_recent_candidates",
    "_hard_filter_tmdb_candidates",
    "_render_candidates_as_formatted",
    "_restrict_formatted_to_candidate_pool",
    "_enrich_formatted_recommendations_with_ratings",
    "_format_ai_answer_for_telegram",
]
