import gspread
from datetime import datetime, timedelta
from typing import Iterable, List, Dict

from core.config import GOOGLE_SHEET_NAME, GOOGLE_CREDENTIALS

def connect_to_sheet():
    gc = gspread.service_account(filename=GOOGLE_CREDENTIALS)
    sh = gc.open(GOOGLE_SHEET_NAME)
    return sh.sheet1

def add_movie_row(worksheet, film, year, genre, rating, comment, entry_type):
    worksheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        film,
        year,
        genre,
        rating,
        comment,
        entry_type,
    ])


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


def fetch_records(worksheet) -> List[Dict[str, str]]:
    """Return all worksheet rows as dictionaries with column headers."""

    return worksheet.get_all_records()


def filter_by_genre(records: Iterable[Dict[str, str]], genre_query: str) -> List[Dict[str, str]]:
    """Filter records containing the requested genre (case insensitive)."""

    genre_lower = genre_query.lower()
    return [
        row
        for row in records
        if genre_lower in _first_value(row, "Жанр", "Genre", "жанр").lower()
    ]


def top_by_rating(records: Iterable[Dict[str, str]], limit: int) -> List[Dict[str, str]]:
    """Return rows sorted by rating (desc) limited to the requested amount."""

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
    """Return entries added during the last ``days`` days."""

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
