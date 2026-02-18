"""Sheet I/O helpers for handlers."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import warnings
from copy import deepcopy
from typing import Dict, List, Optional

from telegram import Update
from telegram.ext import Application, CallbackContext

from bot.handlers_transport import _notify_table_unavailable
from core.config import SHEETS_THREAD_TIMEOUT_SECONDS
from core.gsheet import connect_to_sheet, fetch_records
from core.runtime_monitor import record_error

logger = logging.getLogger(__name__)

_SHEET_INDEX_TTL_SECONDS = 5 * 60.0
_SHEET_INDEX_MAX_STALE_SECONDS = 30 * 60.0
_SHEET_INDEX_JOB_NAME = "sheet_index_refresh"
_SHEET_INDEX_LOCK = threading.RLock()
_SHEET_INDEX_CACHE: Optional[tuple[float, float, List[Dict[str, str]]]] = None
_SHEET_INDEX_LAST_ERROR: str = ""


def _sheet_error_text(exc: Exception) -> str:
    message = str(exc).strip()
    if len(message) > 320:
        message = message[:320].rstrip() + "..."
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


def _set_sheet_index_error(error_text: str) -> None:
    global _SHEET_INDEX_LAST_ERROR
    with _SHEET_INDEX_LOCK:
        _SHEET_INDEX_LAST_ERROR = (error_text or "").strip()


def _cache_records(records: List[Dict[str, str]]) -> None:
    global _SHEET_INDEX_CACHE
    now = time.monotonic()
    snapshot = deepcopy(records)
    with _SHEET_INDEX_LOCK:
        _SHEET_INDEX_CACHE = (
            now + _SHEET_INDEX_TTL_SECONDS,
            now,
            snapshot,
        )
        _set_sheet_index_error("")


def _get_cached_records(*, allow_stale: bool) -> Optional[List[Dict[str, str]]]:
    now = time.monotonic()
    with _SHEET_INDEX_LOCK:
        cached = _SHEET_INDEX_CACHE
    if not cached:
        return None
    fresh_until, loaded_at, records = cached
    if now <= fresh_until:
        return deepcopy(records)
    if allow_stale and (now - loaded_at) <= _SHEET_INDEX_MAX_STALE_SECONDS:
        return deepcopy(records)
    return None


def invalidate_sheet_index_cache() -> None:
    global _SHEET_INDEX_CACHE
    with _SHEET_INDEX_LOCK:
        _SHEET_INDEX_CACHE = None


def refresh_sheet_index_sync(*, force_refresh: bool = True) -> List[Dict[str, str]]:
    return _refresh_sheet_index_sync(force_refresh=force_refresh)


def _refresh_sheet_index_sync(*, force_refresh: bool = True) -> List[Dict[str, str]]:
    try:
        ws = connect_to_sheet(force_refresh=force_refresh)
        records = fetch_records(ws, force_refresh=force_refresh)
    except Exception as exc:
        error_text = _sheet_error_text(exc)
        _set_sheet_index_error(error_text)
        record_error("gsheet", exc)
        raise
    _cache_records(records)
    return records


def _get_sheet_index_records_sync() -> List[Dict[str, str]]:
    cached = _get_cached_records(allow_stale=False)
    if cached is not None:
        return cached
    try:
        return _refresh_sheet_index_sync(force_refresh=True)
    except Exception:
        stale = _get_cached_records(allow_stale=True)
        if stale is not None:
            return stale
        raise


def sheet_index_status() -> Dict[str, object]:
    now = time.monotonic()
    with _SHEET_INDEX_LOCK:
        cached = _SHEET_INDEX_CACHE
        last_error = _SHEET_INDEX_LAST_ERROR
    if not cached:
        return {
            "has_cache": False,
            "rows": 0,
            "fresh_for_seconds": 0.0,
            "age_seconds": 0.0,
            "last_error": last_error,
        }
    fresh_until, loaded_at, records = cached
    return {
        "has_cache": True,
        "rows": len(records),
        "fresh_for_seconds": max(0.0, fresh_until - now),
        "age_seconds": max(0.0, now - loaded_at),
        "last_error": last_error,
    }


async def _refresh_sheet_index_job(context: CallbackContext) -> None:
    try:
        await asyncio.to_thread(_refresh_sheet_index_sync, force_refresh=True)
    except Exception as exc:
        logger.warning("SHEET INDEX REFRESH ERROR: %s", _sheet_error_text(exc))


def ensure_sheet_index_job(app: Application) -> None:
    # Access private attribute first to avoid PTB warning when job-queue extra is not installed.
    job_queue = getattr(app, "_job_queue", None)
    if job_queue is None:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"No `JobQueue` set up\..*",
                category=UserWarning,
            )
            job_queue = getattr(app, "job_queue", None)

    if job_queue is None:
        return
    existing = job_queue.get_jobs_by_name(_SHEET_INDEX_JOB_NAME)
    if existing:
        return
    interval_seconds = max(_SHEET_INDEX_TTL_SECONDS, 60.0)
    job_queue.run_repeating(
        _refresh_sheet_index_job,
        interval=interval_seconds,
        first=5.0,
        name=_SHEET_INDEX_JOB_NAME,
    )


def _fetch_records_sync() -> List[Dict[str, str]]:
    return _get_sheet_index_records_sync()


async def _run_sheet_call(callable_obj, *args):
    return await asyncio.wait_for(
        asyncio.to_thread(callable_obj, *args),
        timeout=SHEETS_THREAD_TIMEOUT_SECONDS,
    )


async def _safe_fetch_records(update: Update) -> Optional[List[Dict[str, str]]]:
    cached = _get_cached_records(allow_stale=False)
    if cached is not None:
        return cached

    try:
        return await _run_sheet_call(_fetch_records_sync)
    except asyncio.TimeoutError:
        logger.error(
            "GSHEET ERROR: timeout after %.1f seconds while fetching records.",
            SHEETS_THREAD_TIMEOUT_SECONDS,
        )
        stale = _get_cached_records(allow_stale=True)
        if stale is not None:
            record_error("gsheet", "Timeout; returned stale cache")
            return stale
        record_error("gsheet", "Timeout while fetching records")
        await _notify_table_unavailable(update)
        return None
    except Exception as exc:
        logger.error("GSHEET ERROR: %s %s", type(exc).__name__, exc)
        stale = _get_cached_records(allow_stale=True)
        if stale is not None:
            record_error("gsheet", f"{type(exc).__name__}; returned stale cache")
            return stale
        record_error("gsheet", exc)
        await _notify_table_unavailable(update)
        return None


__all__ = [
    "_fetch_records_sync",
    "_run_sheet_call",
    "_safe_fetch_records",
    "invalidate_sheet_index_cache",
    "refresh_sheet_index_sync",
    "sheet_index_status",
    "ensure_sheet_index_job",
]
