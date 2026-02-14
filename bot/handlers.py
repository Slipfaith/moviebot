"""Telegram bot handlers."""

from __future__ import annotations

import asyncio
import hashlib
import html
import json
import random
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes, ConversationHandler

from bot.interface import (
    get_help_menu,
    get_library_menu,
    get_main_menu,
    get_quick_actions_keyboard,
    get_recommend_menu,
    get_stats_menu,
    QUICK_BUTTON_LAST,
    QUICK_BUTTON_MENU,
    QUICK_BUTTON_RANDOM,
    QUICK_BUTTON_RECOMMEND,
    QUICK_BUTTON_STATS,
)
from core.gemini import (
    GeminiError,
    generate_gemini_reply,
    generate_gemini_reply_with_image,
    is_gemini_enabled,
)
from core.gsheet import (
    add_movie_row,
    connect_to_sheet,
    fetch_records,
    filter_by_genre,
    recent_entries,
    top_by_rating,
)
from core.normalization import normalize_owner, normalize_recommendation, normalize_type
from core.offline_queue import add_offline_entry
from core.recommendations import (
    CandidateMovie,
    TasteProfile,
    build_candidates_summary,
    build_profile_summary,
    build_taste_profile,
    collect_tmdb_candidates,
    lookup_omdb_details,
    tmdb_enabled,
)

HELP_TEXT = (
    "Команды:\n"
    "• /add — добавить фильм\n"
    "• /top — топ по оценке\n"
    "• /recent — за последний месяц\n"
    "• /find <жанр> — поиск по жанру\n"
    "• /search <название> — поиск по названию\n"
    "• /list — последние добавления\n"
    "• /stats — статистика по оценкам\n"
    "• /winner — победитель месяца (муж vs жена)\n"
    "• /random — случайный фильм\n"
    "• /owner <муж|жена> — подборка по владельцу\n"
    "• /ai <вопрос> — спросить Gemini\n"
    "• фото постера — распознать фильм и показать инфо\n"
    "• /menu — меню\n"
    "• /help — помощь\n"
    "• /cancel — отменить добавление"
)

OFFLINE_GUIDE_TEXT = "Если таблица недоступна, записи сохраняются оффлайн."
ADD_USAGE_TEXT = (
    "Чтобы добавить запись, используйте формат:\n"
    "/add Название;Год;Жанр;Оценка;Комментарий;Тип;Рекомендация;Владелец\n"
    "Комментарий, тип, рекомендация и владелец — опционально.\n"
    "Можно также отправить /add и заполнить форму пошагово.\n"
    "Пример:\n"
    "/add Интерстеллар;2014;фантастика;9;Шикарный саундтрек;фильм;рекомендую;муж"
)

_CACHE_TTL_SECONDS = 60
_RESPONSE_CACHE: Dict[str, Tuple[float, str]] = {}
_PAGE_SIZE = 5
_AI_CACHE_TTL_SECONDS = 5 * 60
_AI_RESPONSE_CACHE: Dict[str, Tuple[float, str]] = {}
_RECENT_RECOMMENDATIONS_TTL_SECONDS = 30 * 60
_RECENT_RECOMMENDATIONS_BY_SCOPE: Dict[str, Tuple[float, List[str]]] = {}
_PROFILE_CACHE_TTL_SECONDS = 5 * 60
_PROFILE_CACHE: Optional[Tuple[float, "TasteProfile"]] = None

(
    ADD_FILM,
    ADD_YEAR,
    ADD_GENRE,
    ADD_RATING,
    ADD_COMMENT,
    ADD_TYPE,
    ADD_RECOMMENDATION,
    ADD_OWNER,
    ADD_CONFIRM,
) = range(9)

_COMMENT_SKIP_TOKENS = {"-", "пропустить", "skip", "нет", "без"}


def _get_cached_response(cache_key: str) -> Optional[str]:
    cached = _RESPONSE_CACHE.get(cache_key)
    if not cached:
        return None
    expires_at, text = cached
    if time.time() <= expires_at:
        return text
    _RESPONSE_CACHE.pop(cache_key, None)
    return None


def _store_cached_response(cache_key: str, text: str) -> None:
    _RESPONSE_CACHE[cache_key] = (time.time() + _CACHE_TTL_SECONDS, text)


def _invalidate_response_cache() -> None:
    global _PROFILE_CACHE
    _RESPONSE_CACHE.clear()
    _PROFILE_CACHE = None


def _get_cached_profile() -> Optional[TasteProfile]:
    if not _PROFILE_CACHE:
        return None
    expires_at, profile = _PROFILE_CACHE
    if time.time() <= expires_at:
        return profile
    return None


def _store_cached_profile(profile: TasteProfile) -> None:
    global _PROFILE_CACHE
    _PROFILE_CACHE = (time.time() + _PROFILE_CACHE_TTL_SECONDS, profile)


def _get_ai_cached_response(cache_key: str) -> Optional[str]:
    cached = _AI_RESPONSE_CACHE.get(cache_key)
    if not cached:
        return None
    expires_at, text = cached
    if time.time() <= expires_at:
        return text
    _AI_RESPONSE_CACHE.pop(cache_key, None)
    return None


def _store_ai_cached_response(cache_key: str, text: str) -> None:
    _AI_RESPONSE_CACHE[cache_key] = (time.time() + _AI_CACHE_TTL_SECONDS, text)


def _build_ai_cache_key(prompt: str, profile_summary: str) -> str:
    raw = f"{prompt}\n{profile_summary}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _recommendation_scope_key(update: Update) -> str:
    chat_id = update.effective_chat.id if update.effective_chat else "na"
    user_id = update.effective_user.id if update.effective_user else "na"
    return f"{chat_id}:{user_id}"


def _normalize_title_for_dedupe(value: str) -> str:
    normalized = (value or "").strip().lower()
    normalized = re.sub(r"\(\d{4}\)", "", normalized)
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _get_recent_recommendations(update: Update) -> List[str]:
    key = _recommendation_scope_key(update)
    cached = _RECENT_RECOMMENDATIONS_BY_SCOPE.get(key)
    if not cached:
        return []
    expires_at, titles = cached
    if time.time() <= expires_at:
        return list(titles)
    _RECENT_RECOMMENDATIONS_BY_SCOPE.pop(key, None)
    return []


def _store_recent_recommendations(update: Update, titles: List[str]) -> None:
    if not titles:
        return
    key = _recommendation_scope_key(update)
    existing = _get_recent_recommendations(update)
    merged = existing + titles
    deduped: List[str] = []
    seen: Set[str] = set()
    for title in merged:
        norm = _normalize_title_for_dedupe(title)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        deduped.append(title)
    _RECENT_RECOMMENDATIONS_BY_SCOPE[key] = (
        time.time() + _RECENT_RECOMMENDATIONS_TTL_SECONDS,
        deduped[-40:],
    )


def _extract_titles_from_formatted_recommendations(text: str) -> List[str]:
    titles: List[str] = []
    for raw in re.findall(r"<b>(.*?)</b>", text):
        title = html.unescape(raw).strip()
        lowered = title.lower()
        if lowered in {"new recommendations", "wildcard"}:
            continue
        titles.append(title)
    return titles


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


def _make_page_keyboard(cmd: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    row: List[InlineKeyboardButton] = []
    if page > 0:
        row.append(InlineKeyboardButton("⬅️", callback_data=f"page:{cmd}:{page - 1}"))
    row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton("➡️", callback_data=f"page:{cmd}:{page + 1}"))
    return InlineKeyboardMarkup([row])


async def _send_paginated_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    cmd: str,
    page: int,
) -> None:
    if update.effective_chat:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )
    records = await _safe_fetch_records(update)
    if records is None:
        return

    if cmd == "list":
        stamped_rows: List[Tuple[datetime, Dict[str, str]]] = []
        no_stamp_rows: List[Dict[str, str]] = []
        for row in records:
            ts_val = (
                row.get("Добавлено")
                or row.get("Timestamp")
                or row.get("Дата")
                or row.get("Added")
                or ""
            )
            parsed = _parse_timestamp(str(ts_val)) if ts_val else None
            if parsed:
                stamped_rows.append((parsed, row))
            else:
                no_stamp_rows.append(row)
        if stamped_rows:
            stamped_rows.sort(key=lambda item: item[0], reverse=True)
            items: List[Dict[str, str]] = [r for _, r in stamped_rows] + no_stamp_rows
        else:
            items = list(records)
        header = "📜 Последние добавления"
    elif cmd == "top":
        items = top_by_rating(records, 20)
        header = "🏆 Топ фильмов"
    elif cmd == "recent":
        items = recent_entries(records)
        header = "🗓 За последние 30 дней"
    else:
        return

    if not items:
        await _send(update, "Нет записей.")
        return

    total_pages = max(1, (len(items) + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * _PAGE_SIZE
    slice_items = items[start : start + _PAGE_SIZE]

    if cmd == "top":
        lines = [f"{start + i + 1}. {_format_entry(r)}" for i, r in enumerate(slice_items)]
    else:
        lines = [_format_entry(r) for r in slice_items]

    text = f"{header}:\n" + "\n".join(lines)
    keyboard = _make_page_keyboard(cmd, page, total_pages)
    await _send_panel(update, text, keyboard)


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
    if not is_gemini_enabled():
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
                generate_gemini_reply,
                prompt,
                temperature=0.45,
                max_output_tokens=220,
            )
        except GeminiError as exc:
            print("GEMINI ERROR:", type(exc).__name__, exc)
            return None
        except Exception as exc:
            print("GEMINI ERROR:", type(exc).__name__, exc)
            return None

        title, reason = _parse_single_recommendation(answer)
        if not title:
            continue
        if _normalize_title_for_dedupe(title) in blocked_norm_lookup:
            continue
        if not reason:
            reason = "Похоже по жанрам и оценкам в вашей таблице."
        return title, reason

    return None


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
        if not reason:
            reason = "matches your genres and ratings history"

        formatted = f"<b>{html.escape(title)}</b> - {html.escape(reason)}"
        if wildcard_mode and wildcard_item is None:
            wildcard_item = formatted
        else:
            numbered_items.append(f"{index}. {formatted}")
            index += 1

    if not numbered_items and not wildcard_item:
        return "<b>New Recommendations</b>\n" + html.escape(answer.strip())

    parts = ["<b>New Recommendations</b>"]
    parts.extend(numbered_items[:8])
    if wildcard_item:
        parts.append("")
        parts.append("<b>Wildcard</b>")
        parts.append(f"* {wildcard_item}")
    return "\n".join(parts)


async def _send(
    update: Update,
    text: str,
    *,
    show_menu: bool = False,
    parse_mode: Optional[str] = None,
) -> None:
    reply_markup = get_main_menu() if show_menu else get_quick_actions_keyboard()
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except BadRequest as exc:
            message = str(exc).lower()
            # Callback can expire while we build recommendations; ignore only that case.
            if "query is too old" not in message and "query id is invalid" not in message:
                raise
        if show_menu:
            try:
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
            except BadRequest:
                await update.callback_query.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
        else:
            await update.callback_query.message.reply_text(
                text=text,
                reply_markup=get_quick_actions_keyboard(),
                parse_mode=parse_mode,
            )
        return

    if update.message:
        await update.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )


async def _send_panel(
    update: Update,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    *,
    parse_mode: Optional[str] = None,
) -> None:
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except BadRequest as exc:
            message = str(exc).lower()
            if "query is too old" not in message and "query id is invalid" not in message:
                raise
        try:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        except BadRequest:
            await update.callback_query.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        return

    if update.message:
        await update.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )


async def _reply(
    update: Update,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)


async def _notify_table_unavailable(update: Update, action: str = "запрос") -> None:
    await _send(
        update,
        "⚠️ Сейчас нет связи с таблицей, поэтому выполнить "
        f"{action} не получилось. Попробуйте позже.",
    )


def _fetch_records_sync() -> List[Dict[str, str]]:
    ws = connect_to_sheet()
    return fetch_records(ws)


async def _safe_fetch_records(update: Update) -> Optional[List[Dict[str, str]]]:
    try:
        return await asyncio.to_thread(_fetch_records_sync)
    except Exception as exc:
        print("GSHEET ERROR:", type(exc).__name__, exc)
        await _notify_table_unavailable(update)
        return None


def _format_entry(row: Dict[str, str]) -> str:
    name = row.get("Фильм") or row.get("Название") or row.get("Film") or row.get("Title") or "—"
    year = row.get("Год") or row.get("Year") or "—"
    rating = row.get("Оценка") or row.get("Rating") or row.get("rating") or "—"
    genre = row.get("Жанр") or row.get("Genre") or "—"
    entry_type = normalize_type(row.get("Тип") or row.get("Type"))
    owner = normalize_owner(row.get("Владелец") or row.get("Чье") or row.get("Owner") or "")
    owner_part = f" • {owner}" if owner else ""
    return f"{name} ({year}) — {rating}/10 • {entry_type} • {genre}{owner_part}"


def _parse_timestamp(value: str) -> Optional[datetime]:
    for fmt in (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _extract_row_timestamp(row: Dict[str, str]) -> Optional[datetime]:
    value = (
        row.get("Добавлено")
        or row.get("Timestamp")
        or row.get("Дата")
        or row.get("Added")
        or ""
    )
    if not value:
        return None
    return _parse_timestamp(str(value))


def _month_label(dt: datetime) -> str:
    names = [
        "январь",
        "февраль",
        "март",
        "апрель",
        "май",
        "июнь",
        "июль",
        "август",
        "сентябрь",
        "октябрь",
        "ноябрь",
        "декабрь",
    ]
    return f"{names[dt.month - 1]} {dt.year}"


def _normalize_rating(value: str) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _extract_add_payload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if context.args:
        return " ".join(context.args).strip()
    if update.message and update.message.text:
        text = update.message.text
        if text.startswith("/add"):
            return text.partition(" ")[2].strip()
    return ""


def _parse_add_payload(payload: str) -> Dict[str, str]:
    parts = [part.strip() for part in payload.split(";")]
    if len(parts) < 4:
        raise ValueError("missing_fields")

    if len(parts) > 8:
        comment = ";".join(parts[4:-3]).strip()
        parts = parts[:4] + [comment] + parts[-3:]

    while len(parts) < 8:
        parts.append("")

    film, year, genre, rating, comment, entry_type, recommendation, owner = parts[:8]

    if not film or not year or not genre or not rating:
        raise ValueError("missing_fields")
    if not (year.isdigit() and len(year) == 4):
        raise ValueError("invalid_year")
    try:
        rating_value = float(rating.replace(",", "."))
    except ValueError as exc:
        raise ValueError("invalid_rating") from exc
    if not (1 <= rating_value <= 10):
        raise ValueError("invalid_rating")

    return {
        "film": film,
        "year": year,
        "genre": genre,
        "rating": f"{rating_value:g}",
        "comment": comment,
        "type": normalize_type(entry_type),
        "recommendation": normalize_recommendation(recommendation),
        "owner": normalize_owner(owner),
    }


def _add_entry_to_sheet_sync(entry: Dict[str, str]) -> None:
    ws = connect_to_sheet()
    add_movie_row(
        ws,
        entry["film"],
        entry["year"],
        entry["genre"],
        entry["rating"],
        entry.get("comment", ""),
        entry.get("type", ""),
        entry.get("recommendation", ""),
        entry.get("owner", ""),
    )


async def _add_entry_to_sheet(entry: Dict[str, str]) -> Optional[Exception]:
    last_exc: Optional[Exception] = None
    for attempt in range(2):
        try:
            await asyncio.to_thread(_add_entry_to_sheet_sync, entry)
            return None
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                await asyncio.sleep(1)
    return last_exc


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Сохранить", callback_data="add_flow:confirm:save"),
                InlineKeyboardButton("❌ Отмена", callback_data="add_flow:confirm:cancel"),
            ]
        ]
    )


def _comment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Пропустить", callback_data="add_flow:skip_comment")]]
    )


def _type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Фильм", callback_data="add_flow:type:film"),
                InlineKeyboardButton("Сериал", callback_data="add_flow:type:series"),
            ]
        ]
    )


def _recommendation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Рекомендую", callback_data="add_flow:rec:recommend")],
            [InlineKeyboardButton("Можно посмотреть", callback_data="add_flow:rec:ok")],
            [InlineKeyboardButton("В топку", callback_data="add_flow:rec:skip")],
        ]
    )


def _owner_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Муж", callback_data="add_flow:owner:husband"),
                InlineKeyboardButton("Жена", callback_data="add_flow:owner:wife"),
            ],
            [InlineKeyboardButton("Не указывать", callback_data="add_flow:owner:skip")],
        ]
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_panel(
        update,
        "Выберите раздел:",
        get_main_menu(),
    )
    await _send(update, "Быстрые кнопки внизу.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, HELP_TEXT)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_panel(update, "Главное меню:", get_main_menu())
    await _send(update, "Быстрые кнопки внизу.")


async def _run_ai_recommendation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prompt: str,
    *,
    use_response_cache: bool = True,
    avoid_recent_titles: bool = False,
) -> None:
    if not is_gemini_enabled():
        await _send(
            update,
            "Gemini is not configured. Set GEMINI_API_KEY in .env and restart the bot.",
        )
        return

    if update.effective_chat:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )

    records = await _safe_fetch_records(update)
    if records is None:
        return

    profile = _get_cached_profile()
    if profile is None:
        profile = build_taste_profile(records)
        _store_cached_profile(profile)
    profile_summary = build_profile_summary(profile)
    recent_titles = _get_recent_recommendations(update) if avoid_recent_titles else []
    ai_cache_key = _build_ai_cache_key(prompt, profile_summary)
    if use_response_cache:
        cached = _get_ai_cached_response(ai_cache_key)
        if cached:
            await _send(update, cached, parse_mode=ParseMode.HTML)
            return

    candidates_summary = "TMDB candidates were not used."
    if tmdb_enabled():
        tmdb_candidates = await asyncio.to_thread(collect_tmdb_candidates, profile)
        tmdb_candidates = _filter_recent_candidates(tmdb_candidates, recent_titles)
        candidates_summary = build_candidates_summary(tmdb_candidates)

    recent_titles_block = ""
    if recent_titles:
        recent_titles_block = (
            "Do NOT suggest these titles (already recently recommended):\n"
            + ", ".join(recent_titles[:40])
            + "\n\n"
        )

    prompt_with_context = (
        "Task: recommend NEW movies based on watch history and ratings.\n"
        "NEW means movie title must be absent in watched list.\n\n"
        f"User request:\n{prompt}\n\n"
        f"{recent_titles_block}"
        "Taste profile from Google Sheets:\n"
        f"{profile_summary}\n\n"
        "TMDB candidate pool:\n"
        f"{candidates_summary}\n\n"
        "Output format requirements:\n"
        "1) Russian language only.\n"
        "2) Exactly 5-8 numbered recommendations.\n"
        "3) Every item must be: <Title (Year)> - <one short reason>.\n"
        "4) Then heading 'Дикая карта:' and one extra item with reason.\n"
        "5) No markdown syntax (** or __)."
    )

    try:
        answer = await asyncio.to_thread(generate_gemini_reply, prompt_with_context)
    except GeminiError as exc:
        print("GEMINI ERROR:", type(exc).__name__, exc)
        reason = str(exc).lower()
        if "blocked" in reason:
            await _send(update, "Gemini blocked this request. Please rephrase it.")
        else:
            await _send(
                update,
                "Gemini is temporarily unavailable. Please try again in a minute.",
            )
        return
    except Exception as exc:
        print("GEMINI ERROR:", type(exc).__name__, exc)
        await _send(update, "Could not get a response from Gemini. Please try later.")
        return

    formatted = _format_ai_answer_for_telegram(answer)
    if len(formatted) > 3900:
        formatted = formatted[:3900].rstrip() + "..."
    if use_response_cache:
        _store_ai_cached_response(ai_cache_key, formatted)
    if avoid_recent_titles:
        _store_recent_recommendations(
            update,
            _extract_titles_from_formatted_recommendations(formatted),
        )
    await _send(update, formatted, parse_mode=ParseMode.HTML)


async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = " ".join(context.args).strip() if context.args else ""
    if not prompt:
        await _send(update, "Usage: /ai <your request>")
        return
    await _run_ai_recommendation(update, context, prompt)


async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    custom_hint = " ".join(context.args).strip() if context.args else ""
    if custom_hint:
        prompt = f"Recommend movies for this preference: {custom_hint}"
    else:
        prompt = "Recommend new movies based on my watch history and ratings."
    await _run_ai_recommendation(
        update,
        context,
        prompt,
        use_response_cache=False,
        avoid_recent_titles=True,
    )


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    payload = _extract_add_payload(update, context)
    if not payload:
        context.user_data["add_flow"] = {}
        await _reply(update, "Введите название фильма или сериала:")
        return ADD_FILM

    try:
        entry = _parse_add_payload(payload)
    except ValueError as exc:
        if str(exc) in {"missing_fields", "invalid_year", "invalid_rating"}:
            await _send(update, f"Некорректные данные.\n\n{ADD_USAGE_TEXT}")
        else:
            await _send(update, "Не удалось разобрать данные для добавления.")
        return ConversationHandler.END

    error = await _add_entry_to_sheet(entry)
    if error:
        print("GSHEET ERROR:", type(error).__name__, error)
        if update.effective_chat:
            entry["chat_id"] = update.effective_chat.id
        add_offline_entry(entry)
        await _send(
            update,
            "⚠️ Сейчас нет связи с таблицей. "
            "Запись сохранена оффлайн и будет выгружена позже.",
        )
        return ConversationHandler.END

    _invalidate_response_cache()
    await _send(update, "✅ Запись добавлена в таблицу.")
    return ConversationHandler.END


async def start_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["add_flow"] = {}
    await _reply(update, "Введите название фильма или сериала:")
    return ADD_FILM


async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await _send(update, "Использование: /find <жанр>")
        return

    genre = " ".join(context.args).strip()
    cache_key = f"find:{genre.lower()}"
    cached = _get_cached_response(cache_key)
    if cached:
        await _send(update, cached)
        return

    if update.effective_chat:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )

    records = await _safe_fetch_records(update)
    if records is None:
        return

    filtered = filter_by_genre(records, genre)
    if not filtered:
        await _send(update, "Ничего не найдено.")
        return

    text = "🔎 Найдено:\n" + "\n".join(_format_entry(r) for r in filtered[:10])
    _store_cached_response(cache_key, text)
    await _send(update, text)


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_paginated_list(update, context, "top", 0)


async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_paginated_list(update, context, "recent", 0)


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_paginated_list(update, context, "list", 0)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )
    records = await _safe_fetch_records(update)
    if records is None:
        return

    ratings: List[float] = []
    for row in records:
        raw_rating = row.get("Оценка") or row.get("Rating") or row.get("rating")
        rating_value = _normalize_rating(str(raw_rating))
        if rating_value > 0:
            ratings.append(rating_value)

    total = len(records)
    rated = len(ratings)
    if rated:
        avg_rating = sum(ratings) / rated
        min_rating = min(ratings)
        max_rating = max(ratings)
        text = (
            "📊 Статистика по оценкам:\n"
            f"Всего записей: {total}\n"
            f"С оценкой: {rated}\n"
            f"Средняя: {avg_rating:.1f}/10\n"
            f"Мин: {min_rating:.1f}/10\n"
            f"Макс: {max_rating:.1f}/10"
        )
    else:
        text = (
            "📊 Статистика по оценкам:\n"
            f"Всего записей: {total}\n"
            "Пока нет оценок для расчета статистики."
        )
    await _send(update, text)


async def winner_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )
    records = await _safe_fetch_records(update)
    if records is None:
        return

    now = datetime.now()
    owners = ("муж", "жена")
    owner_stats: Dict[str, Dict[str, float]] = {
        owner: {"count": 0.0, "rated_count": 0.0, "rating_sum": 0.0}
        for owner in owners
    }

    for row in records:
        owner = normalize_owner(
            row.get("Владелец") or row.get("Чье") or row.get("Owner") or ""
        )
        if owner not in owner_stats:
            continue

        timestamp = _extract_row_timestamp(row)
        if not timestamp or timestamp.year != now.year or timestamp.month != now.month:
            continue

        owner_stats[owner]["count"] += 1
        rating_raw = row.get("Оценка") or row.get("Rating") or row.get("rating")
        rating = _normalize_rating(str(rating_raw))
        if rating > 0:
            owner_stats[owner]["rated_count"] += 1
            owner_stats[owner]["rating_sum"] += rating

    month_total = int(sum(item["count"] for item in owner_stats.values()))
    month_name = _month_label(now)
    if month_total == 0:
        await _send(
            update,
            f"🏁 Победитель месяца ({month_name}):\n"
            "За текущий месяц нет фильмов с владельцем «муж» или «жена».",
        )
        return

    def avg_for(owner: str) -> Optional[float]:
        rated_count = owner_stats[owner]["rated_count"]
        if rated_count <= 0:
            return None
        return owner_stats[owner]["rating_sum"] / rated_count

    avg_husband = avg_for("муж")
    avg_wife = avg_for("жена")

    month_rated_total = owner_stats["муж"]["rated_count"] + owner_stats["жена"]["rated_count"]
    month_rating_sum = owner_stats["муж"]["rating_sum"] + owner_stats["жена"]["rating_sum"]
    prior_rating = (month_rating_sum / month_rated_total) if month_rated_total > 0 else 6.0

    def quality_score(owner: str) -> float:
        avg = avg_for(owner)
        if avg is None:
            return 0.0
        rated_count = owner_stats[owner]["rated_count"]
        confidence = min(rated_count / 5.0, 1.0)
        # Pull tiny samples toward monthly prior to avoid "1 film = champion".
        return prior_rating + (avg - prior_rating) * confidence

    quality_husband = quality_score("муж")
    quality_wife = quality_score("жена")
    activity_husband = owner_stats["муж"]["count"]
    activity_wife = owner_stats["жена"]["count"]

    if quality_husband <= 0 and quality_wife <= 0:
        quality_winner = "Лига качества: победитель не определён (нет оценок)."
    elif abs(quality_husband - quality_wife) < 1e-9:
        quality_winner = f"Лига качества: ничья ({quality_husband:.2f})."
    elif quality_husband > quality_wife:
        quality_winner = (
            f"Лига качества: победил муж "
            f"({quality_husband:.2f} против {quality_wife:.2f})."
        )
    else:
        quality_winner = (
            f"Лига качества: победила жена "
            f"({quality_wife:.2f} против {quality_husband:.2f})."
        )

    if abs(activity_husband - activity_wife) < 1e-9:
        activity_winner = f"Лига активности: ничья ({int(activity_husband)} предложений)."
    elif activity_husband > activity_wife:
        activity_winner = (
            f"Лига активности: победил муж "
            f"({int(activity_husband)} против {int(activity_wife)} предложений)."
        )
    else:
        activity_winner = (
            f"Лига активности: победила жена "
            f"({int(activity_wife)} против {int(activity_husband)} предложений)."
        )

    husband_avg_text = f"{avg_husband:.2f}/10" if avg_husband is not None else "нет оценок"
    wife_avg_text = f"{avg_wife:.2f}/10" if avg_wife is not None else "нет оценок"

    text = (
        f"🏁 Итоги месяца ({month_name}):\n"
        f"{quality_winner}\n"
        f"{activity_winner}\n\n"
        "Статистика за текущий месяц:\n"
        f"• Муж: предложил {int(activity_husband)}, "
        f"оценок {int(owner_stats['муж']['rated_count'])}, "
        f"средний {husband_avg_text}, качество {quality_husband:.2f}\n"
        f"• Жена: предложила {int(activity_wife)}, "
        f"оценок {int(owner_stats['жена']['rated_count'])}, "
        f"средний {wife_avg_text}, качество {quality_wife:.2f}\n\n"
        "Качество = средний балл с поправкой на размер выборки."
    )
    await _send(update, text)


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    records = await _safe_fetch_records(update)
    if records is None:
        return

    if not records:
        await _send(update, "Пока нет записей. Добавьте фильмы, чтобы подбирать новые похожие.")
        return

    if update.effective_chat:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )

    profile = _get_cached_profile()
    if profile is None:
        profile = build_taste_profile(records)
        _store_cached_profile(profile)
    watched_lookup = _build_watched_dedupe_lookup(records)
    recent_titles = _get_recent_recommendations(update)
    recent_lookup = {_normalize_title_for_dedupe(item) for item in recent_titles}

    candidates: List[CandidateMovie] = []
    if tmdb_enabled():
        candidates = await asyncio.to_thread(collect_tmdb_candidates, profile)

    if candidates:
        filtered = [
            item
            for item in candidates
            if _normalize_title_for_dedupe(item.title) not in watched_lookup
            and _normalize_title_for_dedupe(item.title) not in recent_lookup
        ]
        if not filtered:
            filtered = [
                item
                for item in candidates
                if _normalize_title_for_dedupe(item.title) not in watched_lookup
            ]
        if filtered:
            picked = _pick_weighted_random_candidate(filtered)
            _store_recent_recommendations(update, [picked.title])

            year = str(picked.year) if picked.year else "—"
            genres = ", ".join(picked.genres[:3]) if picked.genres else "—"
            rating_parts: List[str] = []
            if picked.tmdb_rating > 0:
                rating_parts.append(f"TMDB {picked.tmdb_rating:.1f}/10")
            if picked.imdb_rating and picked.imdb_rating > 0:
                rating_parts.append(f"IMDb {picked.imdb_rating:.1f}/10")
            ratings_line = " | ".join(rating_parts) if rating_parts else "нет данных"
            reason = picked.reason or "Похоже по жанру и оценкам на ваши высоко оцененные фильмы."

            text = (
                "🎲 Новый случайный фильм (ещё не смотрели):\n"
                f"<b>{html.escape(picked.title)} ({year})</b>\n"
                f"Жанры: {html.escape(genres)}\n"
                f"Рейтинг: {html.escape(ratings_line)}\n"
                f"Почему: {html.escape(reason)}"
            )
            if picked.omdb_plot:
                plot = picked.omdb_plot.strip()
                if len(plot) > 240:
                    plot = plot[:240].rstrip() + "..."
                text += f"\nСюжет: {html.escape(plot)}"
            await _send(update, text, parse_mode=ParseMode.HTML)
            return

    blocked_for_ai = list(profile.watched_titles) + recent_titles
    ai_pick = await _ai_single_unseen_pick(
        profile_summary=build_profile_summary(profile),
        blocked_titles=blocked_for_ai,
    )
    if ai_pick:
        title, reason = ai_pick
        if _normalize_title_for_dedupe(title) not in watched_lookup:
            _store_recent_recommendations(update, [title])
            await _send(
                update,
                (
                    "🎲 Новый случайный фильм (ещё не смотрели):\n"
                    f"<b>{html.escape(title)}</b>\n"
                    f"Почему: {html.escape(reason)}"
                ),
                parse_mode=ParseMode.HTML,
            )
            return

    await _send(
        update,
        (
            "Сейчас не получилось подобрать новый фильм вне вашей таблицы.\n"
            "Проверьте доступ к TMDB/Gemini и попробуйте снова."
        ),
    )


async def owner_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await _send(update, "Использование: /owner <муж|жена>")
        return

    owner = normalize_owner(" ".join(context.args))
    if not owner:
        await _send(update, "Использование: /owner <муж|жена>")
        return

    if update.effective_chat:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )
    records = await _safe_fetch_records(update)
    if records is None:
        return

    filtered = [
        row
        for row in records
        if normalize_owner(row.get("Владелец") or row.get("Чье") or row.get("Owner") or "") == owner
    ]

    if not filtered:
        await _send(update, f"Для владельца «{owner}» ничего не найдено.")
        return

    text = f"👤 Подборка ({owner}):\n" + "\n".join(_format_entry(r) for r in filtered[:10])
    await _send(update, text)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await _send(update, "Использование: /search <часть названия>")
        return

    query = " ".join(context.args).strip()
    if update.effective_chat:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )

    records = await _safe_fetch_records(update)
    if records is None:
        return

    query_lower = query.lower()
    filtered = [
        row
        for row in records
        if query_lower in (
            row.get("Фильм") or row.get("Название") or row.get("Film") or row.get("Title") or ""
        ).lower()
    ]

    if not filtered:
        await _send(update, f"По запросу «{html.escape(query)}» ничего не найдено.")
        return

    lines = [_format_entry(r) for r in filtered[:10]]
    text = f"🔍 Результаты поиска «{html.escape(query)}»:\n" + "\n".join(lines)
    if len(filtered) > 10:
        text += f"\n\n…и ещё {len(filtered) - 10} совпадений. Уточните запрос."
    await _send(update, text)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.callback_query:
        return
    data = update.callback_query.data

    if data == "menu_main":
        await _send_panel(update, "Главное меню:", get_main_menu())
        return
    if data == "menu_recommend":
        await _send_panel(update, "Раздел рекомендаций:", get_recommend_menu())
        return
    if data == "menu_library":
        await _send_panel(update, "Библиотека:", get_library_menu())
        return
    if data == "menu_stats":
        await _send_panel(update, "Статистика и подборки:", get_stats_menu())
        return
    if data == "menu_help":
        await _send_panel(update, "Помощь:", get_help_menu())
        return

    if data == "top5":
        await top_command(update, context)
        return
    if data == "recent_entries":
        await recent_command(update, context)
        return
    if data == "list_films":
        await list_command(update, context)
        return
    if data == "rating_stats":
        await stats_command(update, context)
        return
    if data == "winner_month":
        await winner_command(update, context)
        return
    if data == "random_pick":
        await random_command(update, context)
        return

    if data == "owner_husband":
        context.args = ["муж"]
        await owner_command(update, context)
        return
    if data == "owner_wife":
        context.args = ["жена"]
        await owner_command(update, context)
        return

    if data == "search_genre":
        await _send(update, "Используйте команду: /find <жанр>")
        return
    if data == "search_title":
        await _send(update, "Используйте команду: /search <часть названия>")
        return

    if data == "recommend_me":
        try:
            await update.callback_query.answer("Подбираю рекомендации...")
        except BadRequest:
            pass
        await _run_ai_recommendation(
            update,
            context,
            "Recommend new movies based on my watch history and ratings.",
            use_response_cache=False,
            avoid_recent_titles=True,
        )
        return

    if data == "ai_help":
        await _send(update, "Спросите AI: /ai <ваш вопрос или запрос по фильмам>")
        return
    if data == "help":
        await _send(update, HELP_TEXT)
        return
    if data == "offline_help":
        await _send(update, OFFLINE_GUIDE_TEXT)
        return

    if data == "noop":
        await update.callback_query.answer()
        return

    if data.startswith("page:"):
        parts = data.split(":")
        if len(parts) == 3:
            _, cmd, raw_page = parts
            try:
                page = int(raw_page)
            except ValueError:
                page = 0
            await _send_paginated_list(update, context, cmd, page)
        else:
            await update.callback_query.answer()
        return

    await update.callback_query.answer()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip() if update.message else ""
    if text == QUICK_BUTTON_RECOMMEND:
        await recommend_command(update, context)
        return
    if text == QUICK_BUTTON_LAST:
        await list_command(update, context)
        return
    if text == QUICK_BUTTON_RANDOM:
        await random_command(update, context)
        return
    if text == QUICK_BUTTON_STATS:
        await stats_command(update, context)
        return
    if text == QUICK_BUTTON_MENU:
        await menu_command(update, context)
        return
    await _send(update, "Используйте /menu, /help или кнопки снизу.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        await _send(update, "Фото не найдено. Отправьте постер фильма.")
        return
    if not is_gemini_enabled():
        await _send(update, "Для распознавания постера нужен GEMINI_API_KEY.")
        return

    if update.effective_chat:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )

    try:
        photo = update.message.photo[-1]
        tg_file = await photo.get_file()
        image_bytes = bytes(await tg_file.download_as_bytearray())
    except Exception as exc:
        print("PHOTO ERROR:", type(exc).__name__, exc)
        await _send(update, "Не удалось загрузить фото. Попробуйте ещё раз.")
        return

    prompt = (
        "Определи фильм или сериал по изображению постера.\n"
        "Ответ верни строго JSON без пояснений:\n"
        '{"title":"...", "year":"....", "media_type":"movie|series|unknown", '
        '"confidence":0-100, "reason":"кратко"}\n'
        "Если не уверен, оставь title пустым."
    )

    try:
        ai_answer = await asyncio.to_thread(
            generate_gemini_reply_with_image,
            prompt=prompt,
            image_bytes=image_bytes,
            mime_type="image/jpeg",
            temperature=0.1,
            max_output_tokens=300,
        )
    except GeminiError as exc:
        print("GEMINI ERROR:", type(exc).__name__, exc)
        await _send(update, "Gemini сейчас недоступен для распознавания фото.")
        return
    except Exception as exc:
        print("GEMINI ERROR:", type(exc).__name__, exc)
        await _send(update, "Не удалось распознать постер. Попробуйте позже.")
        return

    parsed = _extract_json_dict(ai_answer)
    if not parsed:
        await _send(
            update,
            "Не удалось разобрать ответ Gemini по фото. Отправьте более чёткий постер.",
        )
        return

    title = str(parsed.get("title") or "").strip()
    if not title:
        await _send(
            update,
            "Не смог уверенно определить фильм по этому постеру. Попробуйте другое фото.",
        )
        return

    year_text = str(parsed.get("year") or "").strip()
    year = int(year_text) if year_text.isdigit() and len(year_text) == 4 else None
    confidence_raw = parsed.get("confidence")
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.0
    media_type = str(parsed.get("media_type") or "unknown").strip().lower()
    reason = str(parsed.get("reason") or "").strip()

    details = await asyncio.to_thread(lookup_omdb_details, title, year)
    year_label = f" ({year})" if year else ""
    type_label = "фильм" if media_type == "movie" else "сериал" if media_type == "series" else "медиа"

    lines = [
        f"🖼 Нашёл по постеру: <b>{html.escape(title)}{year_label}</b>",
        f"Тип: {html.escape(type_label)}",
    ]
    if confidence > 0:
        lines.append(f"Уверенность Gemini: {confidence:.0f}%")
    if reason:
        lines.append(f"Почему: {html.escape(reason)}")

    if details:
        genre = (details.get("Genre") or "").strip()
        imdb_rating = _normalize_rating(details.get("imdbRating") or "")
        plot = (details.get("Plot") or "").strip()
        if genre and genre.lower() != "n/a":
            lines.append(f"Жанры: {html.escape(genre)}")
        if imdb_rating > 0:
            lines.append(f"IMDb: {imdb_rating:.1f}/10")
        if plot and plot.lower() != "n/a":
            if len(plot) > 280:
                plot = plot[:280].rstrip() + "..."
            lines.append(f"Сюжет: {html.escape(plot)}")

    lines.append("")
    lines.append(f"Быстро добавить: /add {title};{year or datetime.now().year};жанр;8")
    await _send(update, "\n".join(lines), parse_mode=ParseMode.HTML)


async def add_flow_film(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    film = (update.message.text or "").strip()
    if not film:
        await _reply(update, "Введите название фильма или сериала:")
        return ADD_FILM
    context.user_data["add_flow"] = {"film": film}
    await _reply(update, "Год выпуска (например, 2014):")
    return ADD_YEAR


async def add_flow_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    year = (update.message.text or "").strip()
    if not (year.isdigit() and len(year) == 4):
        await _reply(update, "Введите год из 4 цифр (например, 2014):")
        return ADD_YEAR
    context.user_data["add_flow"]["year"] = year
    await _reply(update, "Жанр (например, фантастика):")
    return ADD_GENRE


async def add_flow_genre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    genre = (update.message.text or "").strip()
    if not genre:
        await _reply(update, "Введите жанр (например, фантастика):")
        return ADD_GENRE
    context.user_data["add_flow"]["genre"] = genre
    await _reply(update, "Оценка от 1 до 10 (например, 8.5):")
    return ADD_RATING


async def add_flow_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    rating_raw = (update.message.text or "").strip()
    try:
        rating_value = float(rating_raw.replace(",", "."))
    except ValueError:
        rating_value = 0
    if not (1 <= rating_value <= 10):
        await _reply(update, "Введите число от 1 до 10 (например, 8 или 8.5):")
        return ADD_RATING
    context.user_data["add_flow"]["rating"] = f"{rating_value:g}"
    await _reply(
        update,
        "Комментарий (можно пропустить):",
        reply_markup=_comment_keyboard(),
    )
    return ADD_COMMENT


async def add_flow_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    comment = (update.message.text or "").strip()
    if comment.lower() in _COMMENT_SKIP_TOKENS:
        comment = ""
    context.user_data["add_flow"]["comment"] = comment
    await _reply(update, "Тип записи:", reply_markup=_type_keyboard())
    return ADD_TYPE


async def add_flow_comment_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    context.user_data["add_flow"]["comment"] = ""
    await _reply(update, "Тип записи:", reply_markup=_type_keyboard())
    return ADD_TYPE


async def add_flow_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    entry_type = (update.message.text or "").strip()
    context.user_data["add_flow"]["type"] = normalize_type(entry_type)
    await _reply(update, "Рекомендация:", reply_markup=_recommendation_keyboard())
    return ADD_RECOMMENDATION


async def add_flow_type_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    choice = update.callback_query.data.rsplit(":", 1)[-1]
    context.user_data["add_flow"]["type"] = "сериал" if choice == "series" else "фильм"
    await _reply(update, "Рекомендация:", reply_markup=_recommendation_keyboard())
    return ADD_RECOMMENDATION


async def add_flow_recommendation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    recommendation = (update.message.text or "").strip()
    context.user_data["add_flow"]["recommendation"] = normalize_recommendation(recommendation)
    await _reply(update, "Кто добавил?", reply_markup=_owner_keyboard())
    return ADD_OWNER


async def add_flow_recommendation_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    mapping = {
        "recommend": "рекомендую",
        "ok": "можно посмотреть",
        "skip": "в топку",
    }
    choice = update.callback_query.data.rsplit(":", 1)[-1]
    context.user_data["add_flow"]["recommendation"] = mapping.get(choice, "можно посмотреть")
    await _reply(update, "Кто добавил?", reply_markup=_owner_keyboard())
    return ADD_OWNER


async def add_flow_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    owner = normalize_owner((update.message.text or "").strip())
    context.user_data["add_flow"]["owner"] = owner
    return await _finish_add_flow(update, context)


async def add_flow_owner_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    choice = update.callback_query.data.rsplit(":", 1)[-1]
    if choice == "husband":
        owner = "муж"
    elif choice == "wife":
        owner = "жена"
    else:
        owner = ""
    context.user_data["add_flow"]["owner"] = owner
    return await _finish_add_flow(update, context)


async def _finish_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    entry = context.user_data.get("add_flow", {})
    required = ["film", "year", "genre", "rating"]
    if not all(entry.get(key) for key in required):
        await _send(update, "Не удалось собрать данные. Попробуйте /add заново.")
        context.user_data.pop("add_flow", None)
        return ConversationHandler.END

    rec = entry.get("recommendation") or "—"
    owner = entry.get("owner") or "не указан"
    comment = entry.get("comment") or "—"
    entry_type = entry.get("type") or "—"

    preview = (
        "📋 <b>Проверьте данные перед сохранением:</b>\n\n"
        f"🎬 <b>{html.escape(entry['film'])}</b> ({html.escape(entry['year'])})\n"
        f"Жанр: {html.escape(entry['genre'])}\n"
        f"Оценка: {html.escape(entry['rating'])}/10\n"
        f"Тип: {html.escape(entry_type)}\n"
        f"Рекомендация: {html.escape(rec)}\n"
        f"Владелец: {html.escape(owner)}\n"
        f"Комментарий: {html.escape(comment)}"
    )
    await _reply(update, preview, reply_markup=_confirm_keyboard())
    return ADD_CONFIRM


async def add_flow_confirm_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    entry = context.user_data.get("add_flow", {})
    if not entry:
        await _send(update, "Данные не найдены. Попробуйте /add заново.")
        return ConversationHandler.END

    error = await _add_entry_to_sheet(entry)
    if error:
        print("GSHEET ERROR:", type(error).__name__, error)
        if update.effective_chat:
            entry["chat_id"] = update.effective_chat.id
        add_offline_entry(entry)
        await _send(
            update,
            "⚠️ Сейчас нет связи с таблицей. "
            "Запись сохранена оффлайн и будет выгружена позже.",
        )
        context.user_data.pop("add_flow", None)
        return ConversationHandler.END

    _invalidate_response_cache()
    await _send(update, "✅ Запись добавлена в таблицу.")
    context.user_data.pop("add_flow", None)
    return ConversationHandler.END


async def add_flow_confirm_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    context.user_data.pop("add_flow", None)
    await _send(update, "Добавление отменено.")
    return ConversationHandler.END


async def cancel_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("add_flow", None)
    await _send(update, "Добавление отменено.")
    return ConversationHandler.END
