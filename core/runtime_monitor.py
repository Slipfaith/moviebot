"""Lightweight runtime observability helpers."""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque, List

_MAX_EVENTS = 100
_LOCK = threading.RLock()


@dataclass(frozen=True)
class ErrorEvent:
    timestamp_utc: str
    source: str
    error_type: str
    message: str


_RECENT_ERRORS: Deque[ErrorEvent] = deque(maxlen=_MAX_EVENTS)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def record_error(source: str, error: BaseException | str) -> None:
    if isinstance(error, BaseException):
        error_type = type(error).__name__
        message = str(error)
    else:
        error_type = "Error"
        message = str(error)
    event = ErrorEvent(
        timestamp_utc=_now_utc_iso(),
        source=(source or "unknown").strip() or "unknown",
        error_type=error_type.strip() or "Error",
        message=(message or "").strip()[:400],
    )
    with _LOCK:
        _RECENT_ERRORS.appendleft(event)


def get_recent_errors(limit: int = 10) -> List[ErrorEvent]:
    safe_limit = max(0, int(limit))
    with _LOCK:
        return list(_RECENT_ERRORS)[:safe_limit]


__all__ = [
    "ErrorEvent",
    "record_error",
    "get_recent_errors",
]
