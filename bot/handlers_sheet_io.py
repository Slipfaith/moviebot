"""Sheet I/O helpers for handlers."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

from telegram import Update

from bot.handlers_transport import _notify_table_unavailable
from core.config import SHEETS_THREAD_TIMEOUT_SECONDS
from core.gsheet import connect_to_sheet, fetch_records

logger = logging.getLogger(__name__)


def _fetch_records_sync() -> List[Dict[str, str]]:
    ws = connect_to_sheet()
    return fetch_records(ws)


async def _run_sheet_call(callable_obj, *args):
    return await asyncio.wait_for(
        asyncio.to_thread(callable_obj, *args),
        timeout=SHEETS_THREAD_TIMEOUT_SECONDS,
    )


async def _safe_fetch_records(update: Update) -> Optional[List[Dict[str, str]]]:
    try:
        return await _run_sheet_call(_fetch_records_sync)
    except asyncio.TimeoutError:
        logger.error(
            "GSHEET ERROR: timeout after %.1f seconds while fetching records.",
            SHEETS_THREAD_TIMEOUT_SECONDS,
        )
        await _notify_table_unavailable(update)
        return None
    except Exception as exc:
        logger.error("GSHEET ERROR: %s %s", type(exc).__name__, exc)
        await _notify_table_unavailable(update)
        return None


__all__ = [
    "_fetch_records_sync",
    "_run_sheet_call",
    "_safe_fetch_records",
]
