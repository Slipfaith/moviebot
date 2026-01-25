"""Utilities for storing movie entries when the bot is offline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence

from core.gsheet import add_movie_row, connect_to_sheet
from core.normalization import normalize_owner, normalize_recommendation, normalize_type

_QUEUE_FILE = Path(__file__).resolve().parent.parent / "data" / "offline_entries.json"

_ENTRY_FIELDS: Sequence[str] = (
    "film",
    "year",
    "genre",
    "rating",
    "comment",
    "type",
    "recommendation",
    "owner",
)


def _read_queue() -> List[Dict[str, Any]]:
    if not _QUEUE_FILE.exists():
        return []
    try:
        with _QUEUE_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, list):
                return [
                    entry for entry in data if isinstance(entry, dict)
                ]
    except json.JSONDecodeError:
        return []
    return []


def _write_queue(entries: List[Dict[str, Any]]) -> None:
    _QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _QUEUE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(entries, handle, ensure_ascii=False, indent=2)


def add_offline_entry(entry: Dict[str, Any]) -> None:
    """Append an entry to the offline queue."""

    entries = _read_queue()
    normalized_entry: Dict[str, Any] = {
        "film": entry.get("film", ""),
        "year": entry.get("year", ""),
        "genre": entry.get("genre", ""),
        "rating": entry.get("rating", ""),
        "comment": entry.get("comment", ""),
        "type": normalize_type(entry.get("type", "фильм")),
        "recommendation": normalize_recommendation(
            entry.get("recommendation", "можно посмотреть")
        ),
        "owner": normalize_owner(entry.get("owner", "")),
    }

    if "conf" in entry:
        raw_conf = entry.get("conf", [])
        if isinstance(raw_conf, (list, tuple)):
            conf_list = list(raw_conf)
        else:
            conf_list = []

        normalized_conf = [
            str(conf_list[idx]) if idx < len(conf_list) else "0"
            for idx in range(len(_ENTRY_FIELDS))
        ]
        if len(conf_list) > len(_ENTRY_FIELDS):
            normalized_conf.extend(
                str(value) for value in conf_list[len(_ENTRY_FIELDS) :]
            )

        normalized_entry["conf"] = normalized_conf

    entries.append(normalized_entry)
    _write_queue(entries)


def flush_offline_entries() -> int:
    """Upload queued entries to Google Sheets. Returns number of rows synced."""

    entries = _read_queue()
    if not entries:
        return 0

    worksheet = connect_to_sheet()
    for entry in entries:
        add_movie_row(
            worksheet,
            entry.get("film", ""),
            entry.get("year", ""),
            entry.get("genre", ""),
            entry.get("rating", ""),
            entry.get("comment", ""),
            normalize_type(entry.get("type")),
            normalize_recommendation(entry.get("recommendation")),
            normalize_owner(entry.get("owner")),
        )

    _QUEUE_FILE.unlink(missing_ok=True)
    return len(entries)


def has_offline_entries() -> bool:
    """Return True when there are queued offline entries waiting for sync."""

    return bool(_read_queue())


def offline_entry_count() -> int:
    """Return the number of queued offline entries."""

    return len(_read_queue())
