"""Storage helpers for add-flow handlers."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional

from bot.handlers_sheet import _run_sheet_call
from core.config import SHEETS_THREAD_TIMEOUT_SECONDS
from core.gsheet import add_movie_row, connect_to_sheet

logger = logging.getLogger(__name__)


def _add_entry_to_sheet_sync(entry: Dict[str, str]) -> None:
    ws = connect_to_sheet()
    add_movie_row(
        ws,
        entry["film"],
        entry["year"],
        entry["genre"],
        entry["rating"],
        entry.get("comment", ""),
        entry.get("type", ""),
        entry.get("recommendation", ""),
        entry.get("owner", ""),
    )


async def _add_entry_to_sheet(entry: Dict[str, str]) -> Optional[Exception]:
    last_exc: Optional[Exception] = None
    for attempt in range(2):
        try:
            await _run_sheet_call(_add_entry_to_sheet_sync, entry)
            return None
        except asyncio.TimeoutError as exc:
            last_exc = exc
            logger.error(
                "GSHEET ERROR: timeout after %.1f seconds while saving entry.",
                SHEETS_THREAD_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            last_exc = exc
        if attempt == 0:
            await asyncio.sleep(1)
    return last_exc


__all__ = [
    "_add_entry_to_sheet_sync",
    "_add_entry_to_sheet",
]
