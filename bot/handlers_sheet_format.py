"""Formatting and parsing helpers for sheet rows."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from core.normalization import normalize_owner, normalize_type


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


def _normalize_rating(value: str) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


__all__ = [
    "_format_entry",
    "_parse_timestamp",
    "_extract_row_timestamp",
    "_normalize_rating",
]
