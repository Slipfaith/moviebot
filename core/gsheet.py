import gspread
from datetime import datetime, timedelta
from typing import Iterable, List, Dict

from core.config import GOOGLE_SHEET_NAME, GOOGLE_CREDENTIALS

_SHEETS_URL_FRAGMENT = "docs.google.com/spreadsheets"


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


def connect_to_sheet():
    if not GOOGLE_CREDENTIALS:
        raise ValueError("GOOGLE_CREDENTIALS is not configured.")
    if not GOOGLE_SHEET_NAME:
        raise ValueError("GOOGLE_SHEET_NAME is not configured.")

    gc = gspread.service_account(filename=GOOGLE_CREDENTIALS)

    if _is_sheet_url(GOOGLE_SHEET_NAME):
        spreadsheet = gc.open_by_url(GOOGLE_SHEET_NAME)
    elif _is_sheet_key(GOOGLE_SHEET_NAME):
        spreadsheet = gc.open_by_key(GOOGLE_SHEET_NAME)
    else:
        spreadsheet = gc.open(GOOGLE_SHEET_NAME)

    return spreadsheet.sheet1


def add_movie_row(
    worksheet,
    film,
    year,
    genre,
    rating,
    comment,
    entry_type,
    recommendation,
    owner,
):
    worksheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        film,
        year,
        genre,
        rating,
        comment,
        entry_type,
        recommendation,
        owner,
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
    try:
        return worksheet.get_all_records()
    except Exception:
        values = worksheet.get_all_values()
        if not values or len(values) < 2:
            return []

        headers = [h.strip() for h in values[0]]
        records: List[Dict[str, str]] = []

        for row in values[1:]:
            record = {}
            for idx, header in enumerate(headers):
                if not header:
                    continue
                record[header] = row[idx] if idx < len(row) else ""
            records.append(record)

        return records


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
