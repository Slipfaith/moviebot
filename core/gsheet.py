"""Google Sheets access helpers with lightweight in-memory caching."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

import gspread

from core.config import GOOGLE_CREDENTIALS, GOOGLE_SHEET_NAME

_SHEETS_URL_FRAGMENT = "docs.google.com/spreadsheets"
_WORKSHEET_TTL_SECONDS = 5 * 60
_RECORDS_TTL_SECONDS = 3 * 60  # 3 minutes; cache is invalidated on every write

_CACHE_LOCK = threading.Lock()
_CLIENT: Optional[gspread.Client] = None
_WORKSHEET_CACHE: Optional[Tuple[float, gspread.Worksheet]] = None
_RECORDS_CACHE: Optional[Tuple[float, List[Dict[str, str]]]] = None


def _is_sheet_url(value: str) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(("http://", "https://"))
        and _SHEETS_URL_FRAGMENT in value
    )


def _is_sheet_key(value: str) -> bool:
    if not isinstance(value, str):
        return False
    if " " in value or "/" in value:
        return False
    if len(value) < 20:
        return False
    return all(ch.isalnum() or ch in {"-", "_"} for ch in value)


def _open_worksheet(client: gspread.Client) -> gspread.Worksheet:
    if _is_sheet_url(GOOGLE_SHEET_NAME):
        spreadsheet = client.open_by_url(GOOGLE_SHEET_NAME)
    elif _is_sheet_key(GOOGLE_SHEET_NAME):
        spreadsheet = client.open_by_key(GOOGLE_SHEET_NAME)
    else:
        spreadsheet = client.open(GOOGLE_SHEET_NAME)
    return spreadsheet.sheet1


def connect_to_sheet(force_refresh: bool = False) -> gspread.Worksheet:
    if not GOOGLE_CREDENTIALS:
        raise ValueError("GOOGLE_CREDENTIALS is not configured.")
    if not GOOGLE_SHEET_NAME:
        raise ValueError("GOOGLE_SHEET_NAME is not configured.")

    global _CLIENT, _WORKSHEET_CACHE
    now = time.monotonic()

    with _CACHE_LOCK:
        if not force_refresh and _WORKSHEET_CACHE:
            expires_at, worksheet = _WORKSHEET_CACHE
            if now <= expires_at:
                return worksheet

        if _CLIENT is None or force_refresh:
            _CLIENT = gspread.service_account(filename=GOOGLE_CREDENTIALS)

        worksheet = _open_worksheet(_CLIENT)
        _WORKSHEET_CACHE = (now + _WORKSHEET_TTL_SECONDS, worksheet)
        return worksheet


def invalidate_records_cache() -> None:
    global _RECORDS_CACHE
    with _CACHE_LOCK:
        _RECORDS_CACHE = None


def add_movie_row(
    worksheet: gspread.Worksheet,
    film: str,
    year: str,
    genre: str,
    rating: str,
    comment: str,
    entry_type: str,
    recommendation: str,
    owner: str,
) -> None:
    worksheet.append_row(
        [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            film,
            year,
            genre,
            rating,
            comment,
            entry_type,
            recommendation,
            owner,
        ]
    )
    invalidate_records_cache()


def _first_value(row: Dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _normalize_rating(value: str) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _fetch_records_uncached(worksheet: gspread.Worksheet) -> List[Dict[str, str]]:
    try:
        return worksheet.get_all_records()
    except Exception:
        values = worksheet.get_all_values()
        if not values or len(values) < 2:
            return []

        headers = [h.strip() for h in values[0]]
        records: List[Dict[str, str]] = []

        for row in values[1:]:
            record: Dict[str, str] = {}
            for idx, header in enumerate(headers):
                if not header:
                    continue
                record[header] = row[idx] if idx < len(row) else ""
            records.append(record)

        return records


def fetch_records(
    worksheet: Optional[gspread.Worksheet],
    *,
    use_cache: bool = True,
    force_refresh: bool = False,
    ttl_seconds: int = _RECORDS_TTL_SECONDS,
) -> List[Dict[str, str]]:
    global _RECORDS_CACHE

    worksheet = worksheet or connect_to_sheet(force_refresh=force_refresh)
    now = time.monotonic()

    with _CACHE_LOCK:
        cached = _RECORDS_CACHE

    if use_cache and not force_refresh and cached:
        expires_at, records = cached
        if now <= expires_at:
            return list(records)

    records = _fetch_records_uncached(worksheet)

    if use_cache:
        with _CACHE_LOCK:
            _RECORDS_CACHE = (time.monotonic() + max(ttl_seconds, 0), records)
    else:
        with _CACHE_LOCK:
            _RECORDS_CACHE = None

    return list(records)


def filter_by_genre(records: Iterable[Dict[str, str]], genre_query: str) -> List[Dict[str, str]]:
    genre_lower = genre_query.lower()
    return [
        row
        for row in records
        if genre_lower in _first_value(row, "Жанр", "Genre", "жанр").lower()
    ]


def top_by_rating(records: Iterable[Dict[str, str]], limit: int) -> List[Dict[str, str]]:
    sorted_rows = sorted(
        records,
        key=lambda row: (
            _normalize_rating(_first_value(row, "Оценка", "Rating", "rating")),
            _first_value(row, "Название", "Film", "Фильм", "Title"),
        ),
        reverse=True,
    )
    return sorted_rows[:limit]


def recent_entries(records: Iterable[Dict[str, str]], days: int = 30) -> List[Dict[str, str]]:
    cutoff = datetime.now() - timedelta(days=days)
    result: List[Dict[str, str]] = []

    for row in records:
        timestamp = _first_value(row, "Добавлено", "Timestamp", "Дата", "Added")
        if not timestamp:
            continue
        try:
            added_at = datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                added_at = datetime.strptime(timestamp, "%d.%m.%Y %H:%M")
            except ValueError:
                continue
        if added_at >= cutoff:
            result.append(row)

    return result
