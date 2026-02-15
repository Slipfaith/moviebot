"""Utilities for storing movie entries when the bot is offline."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set

from core.gsheet import add_movie_row, connect_to_sheet
from core.normalization import normalize_owner, normalize_recommendation, normalize_type

_QUEUE_FILE = Path(__file__).resolve().parent.parent / "data" / "offline_entries.json"
_QUEUE_LOCK = threading.RLock()

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


@dataclass
class OfflineSyncResult:
    processed: int
    failed: int
    error: Optional[Exception] = None
    chat_ids: Set[int] = field(default_factory=set)


def _read_queue_unlocked() -> List[Dict[str, Any]]:
    if not _QUEUE_FILE.exists():
        return []
    try:
        with _QUEUE_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, list):
                return [
                    entry for entry in data if isinstance(entry, dict)
                ]
    except (json.JSONDecodeError, OSError):
        return []
    return []


def _write_queue_unlocked(entries: List[Dict[str, Any]]) -> None:
    _QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=f"{_QUEUE_FILE.stem}.",
        suffix=".tmp",
        dir=str(_QUEUE_FILE.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(entries, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, _QUEUE_FILE)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _persist_queue_unlocked(entries: List[Dict[str, Any]]) -> None:
    if entries:
        _write_queue_unlocked(entries)
        return
    _QUEUE_FILE.unlink(missing_ok=True)


def _read_queue() -> List[Dict[str, Any]]:
    with _QUEUE_LOCK:
        return _read_queue_unlocked()


def _remove_processed_entries(
    current_entries: List[Dict[str, Any]],
    processed_entries: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    remaining = list(current_entries)
    for processed in processed_entries:
        for index, entry in enumerate(remaining):
            if entry == processed:
                remaining.pop(index)
                break
    return remaining


def add_offline_entry(entry: Dict[str, Any]) -> None:
    """Append an entry to the offline queue."""

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

    chat_id = entry.get("chat_id")
    if chat_id is not None:
        try:
            normalized_entry["chat_id"] = int(chat_id)
        except (TypeError, ValueError):
            pass

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

    with _QUEUE_LOCK:
        latest_entries = _read_queue_unlocked()
        latest_entries.append(normalized_entry)
        _persist_queue_unlocked(latest_entries)


def flush_offline_entries() -> OfflineSyncResult:
    """Upload queued entries to Google Sheets."""

    with _QUEUE_LOCK:
        entries = _read_queue_unlocked()
    if not entries:
        return OfflineSyncResult(processed=0, failed=0, chat_ids=set())

    try:
        worksheet = connect_to_sheet()
    except Exception as exc:
        return OfflineSyncResult(
            processed=0,
            failed=len(entries),
            error=exc,
            chat_ids=set(),
        )

    processed_entries: List[Dict[str, Any]] = []
    processed_chat_ids: Set[int] = set()
    error: Optional[Exception] = None

    for entry in entries:
        try:
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
            processed_entries.append(entry)
            chat_id = entry.get("chat_id")
            if isinstance(chat_id, int):
                processed_chat_ids.add(chat_id)
        except Exception as exc:
            error = exc
            break

    with _QUEUE_LOCK:
        latest_entries = _read_queue_unlocked()
        remaining_entries = _remove_processed_entries(latest_entries, processed_entries)
        _persist_queue_unlocked(remaining_entries)

    return OfflineSyncResult(
        processed=len(processed_entries),
        failed=len(entries) - len(processed_entries),
        error=error,
        chat_ids=processed_chat_ids,
    )


def has_offline_entries() -> bool:
    """Return True when there are queued offline entries waiting for sync."""

    return bool(_read_queue())


def offline_entry_count() -> int:
    """Return the number of queued offline entries."""

    return len(_read_queue())
