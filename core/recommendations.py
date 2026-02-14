"""Taste profiling + TMDB candidate retrieval for AI recommendations."""

from __future__ import annotations

import ipaddress
import re
import socket
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import requests

from core.config import (
    OMDB_API_KEY,
    OMDB_BASE_URL,
    OMDB_TIMEOUT_SECONDS,
    TMDB_API_KEY,
    TMDB_LANGUAGE,
    TMDB_REGION,
    TMDB_TIMEOUT_SECONDS,
)

_TMDB_BASE_URLS = (
    "https://api.themoviedb.org/3",
    "https://api.tmdb.org/3",
)
_TMDB_GENRE_CACHE_TTL_SECONDS = 30 * 60
_TMDB_GENRE_CACHE: Optional[Tuple[float, Dict[int, str]]] = None
_TMDB_UNAVAILABLE_COOLDOWN_SECONDS = 10 * 60
_TMDB_UNAVAILABLE_UNTIL_MONO = 0.0
_OMDB_CACHE_TTL_SECONDS = 24 * 60 * 60
_OMDB_CACHE: Dict[str, Tuple[float, Optional[Dict[str, str]]]] = {}


@dataclass
class SeedMovie:
    title: str
    year: Optional[int]
    rating: float
    genres: List[str] = field(default_factory=list)


@dataclass
class TasteProfile:
    total_entries: int
    rated_entries: int
    average_rating: float
    top_genres: List[Tuple[str, float]]
    favorites: List[SeedMovie]
    watched_titles: List[str]
    watched_lookup: Set[str]


@dataclass
class CandidateMovie:
    tmdb_id: int
    title: str
    year: Optional[int]
    tmdb_rating: float
    vote_count: int
    genres: List[str]
    score: float
    reason: str
    imdb_rating: Optional[float] = None
    omdb_plot: str = ""


def tmdb_enabled() -> bool:
    return bool(TMDB_API_KEY)


def _first_non_empty(row: Dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _normalize_title(title: str) -> str:
    normalized = (title or "").strip().lower()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _parse_rating(value: str) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _parse_year(value: str) -> Optional[int]:
    text = (value or "").strip()
    if len(text) >= 4 and text[:4].isdigit():
        year_value = int(text[:4])
        if 1888 <= year_value <= 2100:
            return year_value
    return None


def _split_genres(value: str) -> List[str]:
    raw = (value or "").strip()
    if not raw:
        return []
    items = re.split(r"[,/|;]+", raw)
    return [item.strip().lower() for item in items if item.strip()]


def _host_resolves_to_loopback(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        return False

    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if ip.is_loopback:
            return True
    return False


def build_taste_profile(records: Sequence[Dict[str, str]]) -> TasteProfile:
    genre_scores: Dict[str, float] = defaultdict(float)
    favorites: List[SeedMovie] = []
    watched_map: Dict[str, str] = {}
    ratings: List[float] = []

    for row in records:
        title = _first_non_empty(row, "Фильм", "Название", "Film", "Title")
        if not title:
            continue

        year = _parse_year(_first_non_empty(row, "Год", "Year"))
        rating = _parse_rating(_first_non_empty(row, "Оценка", "Rating", "rating"))
        genres = _split_genres(_first_non_empty(row, "Жанр", "Genre"))
        norm_title = _normalize_title(title)
        if norm_title and norm_title not in watched_map:
            watched_map[norm_title] = title

        if rating > 0:
            ratings.append(rating)
            for genre in genres:
                genre_scores[genre] += rating

        favorites.append(
            SeedMovie(
                title=title,
                year=year,
                rating=rating,
                genres=genres,
            )
        )

    favorites.sort(key=lambda item: item.rating, reverse=True)
    top_genres = sorted(genre_scores.items(), key=lambda item: item[1], reverse=True)

    return TasteProfile(
        total_entries=len(records),
        rated_entries=len(ratings),
        average_rating=(sum(ratings) / len(ratings)) if ratings else 0.0,
        top_genres=top_genres[:8],
        favorites=favorites[:25],
        watched_titles=sorted(watched_map.values()),
        watched_lookup=set(watched_map.keys()),
    )


def _tmdb_get(path: str, **params) -> Dict:
    global _TMDB_UNAVAILABLE_UNTIL_MONO
    if not TMDB_API_KEY:
        raise RuntimeError("TMDB_API_KEY is not configured")
    now = time.monotonic()
    if now < _TMDB_UNAVAILABLE_UNTIL_MONO:
        raise RuntimeError("TMDB is temporarily unavailable in this network.")

    query = {
        "api_key": TMDB_API_KEY,
        "language": TMDB_LANGUAGE,
        "region": TMDB_REGION,
    }
    query.update(params)
    last_error: Optional[Exception] = None

    for base_url in _TMDB_BASE_URLS:
        host = base_url.split("/")[2]
        if _host_resolves_to_loopback(host):
            continue
        try:
            response = requests.get(
                f"{base_url}{path}",
                params=query,
                timeout=TMDB_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            continue

    _TMDB_UNAVAILABLE_UNTIL_MONO = time.monotonic() + _TMDB_UNAVAILABLE_COOLDOWN_SECONDS
    if last_error:
        raise last_error
    raise RuntimeError("TMDB hosts are unavailable (loopback DNS or connection failure).")


def _tmdb_genre_map() -> Dict[int, str]:
    global _TMDB_GENRE_CACHE
    now = time.monotonic()
    if _TMDB_GENRE_CACHE and now <= _TMDB_GENRE_CACHE[0]:
        return dict(_TMDB_GENRE_CACHE[1])

    data = _tmdb_get("/genre/movie/list")
    items = data.get("genres", [])
    result: Dict[int, str] = {}
    for item in items:
        if isinstance(item, dict):
            genre_id = item.get("id")
            name = item.get("name")
            if isinstance(genre_id, int) and isinstance(name, str):
                result[genre_id] = name
    _TMDB_GENRE_CACHE = (now + _TMDB_GENRE_CACHE_TTL_SECONDS, dict(result))
    return result


def _match_genre_ids(
    preferred_genres: Iterable[str],
    tmdb_genres: Dict[int, str],
) -> List[int]:
    normalized = {
        genre_id: _normalize_title(name)
        for genre_id, name in tmdb_genres.items()
    }
    matched: List[int] = []
    for pref in preferred_genres:
        pref_norm = _normalize_title(pref)
        if not pref_norm:
            continue
        for genre_id, name_norm in normalized.items():
            if pref_norm in name_norm or name_norm in pref_norm:
                if genre_id not in matched:
                    matched.append(genre_id)
    return matched


def _movie_from_tmdb_item(
    item: Dict,
    genre_map: Dict[int, str],
    *,
    reason: str,
    score: float,
) -> Optional[CandidateMovie]:
    movie_id = item.get("id")
    if not isinstance(movie_id, int):
        return None

    title = item.get("title") or item.get("name")
    if not isinstance(title, str) or not title.strip():
        return None

    date_text = item.get("release_date") or ""
    year = _parse_year(str(date_text))

    rating = _parse_rating(item.get("vote_average"))
    try:
        vote_count = int(item.get("vote_count", 0))
    except (TypeError, ValueError):
        vote_count = 0

    genre_ids = item.get("genre_ids")
    genres: List[str] = []
    if isinstance(genre_ids, list):
        for genre_id in genre_ids:
            if isinstance(genre_id, int) and genre_id in genre_map:
                genres.append(genre_map[genre_id])
    if not genres:
        genres = ["—"]

    return CandidateMovie(
        tmdb_id=movie_id,
        title=title.strip(),
        year=year,
        tmdb_rating=rating,
        vote_count=vote_count,
        genres=genres,
        score=score,
        reason=reason,
    )


def _merge_candidate(bucket: Dict[int, CandidateMovie], candidate: CandidateMovie) -> None:
    existing = bucket.get(candidate.tmdb_id)
    if not existing:
        bucket[candidate.tmdb_id] = candidate
        return
    if candidate.score > existing.score:
        bucket[candidate.tmdb_id] = candidate


def _omdb_cache_key(title: str, year: Optional[int]) -> str:
    return f"{_normalize_title(title)}::{year or ''}"


def _omdb_lookup(title: str, year: Optional[int]) -> Optional[Dict[str, str]]:
    if not OMDB_API_KEY:
        return None

    cache_key = _omdb_cache_key(title, year)
    now = time.monotonic()
    cached = _OMDB_CACHE.get(cache_key)
    if cached and now <= cached[0]:
        return cached[1]

    params = {"apikey": OMDB_API_KEY, "t": title}
    if year:
        params["y"] = str(year)
    try:
        response = requests.get(
            OMDB_BASE_URL,
            params=params,
            timeout=OMDB_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print("OMDB ERROR:", type(exc).__name__, exc)
        _OMDB_CACHE[cache_key] = (now + 60, None)
        return None

    if str(payload.get("Response", "")).lower() != "true":
        # Retry once without year filter when strict year search fails.
        if "y" in params:
            try:
                retry_params = {"apikey": OMDB_API_KEY, "t": title}
                retry_response = requests.get(
                    OMDB_BASE_URL,
                    params=retry_params,
                    timeout=OMDB_TIMEOUT_SECONDS,
                )
                retry_response.raise_for_status()
                payload = retry_response.json()
            except Exception as exc:
                print("OMDB ERROR:", type(exc).__name__, exc)
                payload = {"Response": "False"}

    if str(payload.get("Response", "")).lower() != "true":
        _OMDB_CACHE[cache_key] = (now + 10 * 60, None)
        return None

    result = {
        "Title": str(payload.get("Title", "")),
        "Year": str(payload.get("Year", "")),
        "Genre": str(payload.get("Genre", "")),
        "Type": str(payload.get("Type", "")),
        "imdbRating": str(payload.get("imdbRating", "")),
        "Plot": str(payload.get("Plot", "")),
    }
    _OMDB_CACHE[cache_key] = (now + _OMDB_CACHE_TTL_SECONDS, result)
    return result


def _enrich_candidates_with_omdb(
    candidates: List[CandidateMovie],
    *,
    limit: int = 10,
) -> None:
    if not OMDB_API_KEY:
        return

    top_slice = candidates[:max(limit, 0)]
    if not top_slice:
        return

    def _enrich_one(item: CandidateMovie) -> None:
        payload = _omdb_lookup(item.title, item.year)
        if not payload:
            return
        imdb_rating = _parse_rating(payload.get("imdbRating"))
        if imdb_rating > 0:
            item.imdb_rating = imdb_rating
            item.score += min(imdb_rating / 10.0, 1.0) * 0.8
        plot = (payload.get("Plot") or "").strip()
        if plot and plot.lower() != "n/a":
            item.omdb_plot = plot

    with ThreadPoolExecutor(max_workers=min(6, len(top_slice))) as executor:
        futures = [executor.submit(_enrich_one, item) for item in top_slice]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                print("OMDB ENRICH ERROR:", type(exc).__name__, exc)


def lookup_omdb_details(title: str, year: Optional[int] = None) -> Optional[Dict[str, str]]:
    normalized = (title or "").strip()
    if not normalized:
        return None
    return _omdb_lookup(normalized, year)


def collect_tmdb_candidates(
    profile: TasteProfile,
    *,
    limit: int = 80,
) -> List[CandidateMovie]:
    if not TMDB_API_KEY:
        return []

    try:
        genre_map = _tmdb_genre_map()
    except Exception:
        return []

    preferred_genres = [genre for genre, _ in profile.top_genres[:5]]
    preferred_genre_ids = _match_genre_ids(preferred_genres, genre_map)
    preferred_genre_set = {genre.lower() for genre in preferred_genres}
    candidates: Dict[int, CandidateMovie] = {}

    seed_movies = [item for item in profile.favorites if item.rating >= 8.0][:4]
    if len(seed_movies) < 3:
        seed_movies = [item for item in profile.favorites if item.rating >= 6.5][:4]

    for seed in seed_movies:
        try:
            search_payload = _tmdb_get(
                "/search/movie",
                query=seed.title,
                include_adult="false",
                page=1,
                year=seed.year if seed.year else None,
            )
            search_results = search_payload.get("results", [])
            if not isinstance(search_results, list) or not search_results:
                continue
            seed_item = search_results[0]
            seed_id = seed_item.get("id")
            if not isinstance(seed_id, int):
                continue
            rec_payload = _tmdb_get(
                f"/movie/{seed_id}/recommendations",
                include_adult="false",
                page=1,
            )
            rec_results = rec_payload.get("results", [])
            if not isinstance(rec_results, list):
                continue
        except Exception:
            continue

        for item in rec_results[:15]:
            if not isinstance(item, dict):
                continue
            item_title = str(item.get("title") or item.get("name") or "")
            if _normalize_title(item_title) in profile.watched_lookup:
                continue

            item_genres = item.get("genre_ids") if isinstance(item.get("genre_ids"), list) else []
            overlap = 0
            for genre_id in item_genres:
                genre_name = genre_map.get(genre_id, "").lower()
                if genre_name and genre_name in preferred_genre_set:
                    overlap += 1

            score = (
                seed.rating * 0.9
                + _parse_rating(item.get("vote_average")) * 0.8
                + min(int(item.get("vote_count", 0)) / 4000.0, 2.5)
                + overlap * 1.2
            )
            candidate = _movie_from_tmdb_item(
                item,
                genre_map,
                reason=f"похоже на: {seed.title}",
                score=score,
            )
            if candidate:
                _merge_candidate(candidates, candidate)

    if len(candidates) < 25:
        discover_params = {
            "include_adult": "false",
            "sort_by": "vote_average.desc",
            "vote_count.gte": 700,
            "page": 1,
        }
        if preferred_genre_ids:
            discover_params["with_genres"] = ",".join(str(x) for x in preferred_genre_ids[:3])
        try:
            discover_payload = _tmdb_get("/discover/movie", **discover_params)
            discover_results = discover_payload.get("results", [])
        except Exception:
            discover_results = []

        if isinstance(discover_results, list):
            for item in discover_results:
                if not isinstance(item, dict):
                    continue
                item_title = str(item.get("title") or item.get("name") or "")
                if _normalize_title(item_title) in profile.watched_lookup:
                    continue

                score = (
                    _parse_rating(item.get("vote_average")) * 0.9
                    + min(int(item.get("vote_count", 0)) / 5000.0, 2.0)
                )
                candidate = _movie_from_tmdb_item(
                    item,
                    genre_map,
                    reason="популярное в ваших жанрах",
                    score=score,
                )
                if candidate:
                    _merge_candidate(candidates, candidate)

    ranked = sorted(candidates.values(), key=lambda item: item.score, reverse=True)
    _enrich_candidates_with_omdb(ranked, limit=min(12, len(ranked)))
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[:limit]


def _join_limited(items: Sequence[str], *, max_chars: int) -> str:
    result: List[str] = []
    current = 0
    for item in items:
        if current + len(item) + 1 > max_chars:
            break
        result.append(item)
        current += len(item) + 1
    return ", ".join(result)


def build_profile_summary(profile: TasteProfile) -> str:
    lines = [
        f"Записей в таблице: {profile.total_entries}",
        f"С оценками: {profile.rated_entries}",
        f"Средняя оценка: {profile.average_rating:.2f}/10" if profile.rated_entries else "Средняя оценка: нет данных",
    ]
    if profile.top_genres:
        genre_line = ", ".join(f"{genre} ({score:.1f})" for genre, score in profile.top_genres[:5])
        lines.append(f"Любимые жанры: {genre_line}")
    if profile.favorites:
        fav_line = ", ".join(
            f"{item.title} ({item.rating:g})"
            for item in profile.favorites[:8]
            if item.rating > 0
        )
        if fav_line:
            lines.append(f"Топ по оценке: {fav_line}")
    watched_preview = _join_limited(profile.watched_titles, max_chars=1800)
    lines.append(f"Уже просмотрено: {watched_preview}")
    return "\n".join(lines)


def build_candidates_summary(
    candidates: Sequence[CandidateMovie],
    *,
    max_items: int = 35,
    max_chars: int = 7000,
) -> str:
    if not candidates:
        return "TMDB candidates are unavailable."

    lines: List[str] = []
    current = 0
    for item in candidates[:max_items]:
        year = str(item.year) if item.year else "-"
        genres = ", ".join(item.genres[:3]) if item.genres else "-"
        rating_parts = [f"TMDB {item.tmdb_rating:.1f}/10"]
        if item.imdb_rating and item.imdb_rating > 0:
            rating_parts.append(f"IMDb {item.imdb_rating:.1f}/10")

        line = (
            f"- {item.title} ({year}), {' | '.join(rating_parts)}, "
            f"votes={item.vote_count}, genres={genres}, reason={item.reason}"
        )
        if item.omdb_plot:
            line += f", plot={item.omdb_plot[:140].strip()}"

        if current + len(line) + 1 > max_chars:
            break
        lines.append(line)
        current += len(line) + 1
    return "\n".join(lines)
