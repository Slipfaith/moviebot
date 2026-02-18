"""Runtime helpers used during bot application setup."""

from __future__ import annotations

import asyncio
import logging

from telegram.ext import Application

from core.config import SHEETS_THREAD_TIMEOUT_SECONDS
from core.gsheet import invalidate_records_cache
from core.offline_queue import flush_offline_entries
from core.runtime_monitor import record_error
from bot.handlers_sheet_io import invalidate_sheet_index_cache

logger = logging.getLogger(__name__)


class PatchedApplication(Application):
    """Application subclass that re-introduces missing private slots.

    python-telegram-bot 21.2 accidentally omits the ``__stop_running_marker`` slot
    from :class:`telegram.ext.Application.__slots__`. When the base
    ``Application`` initialiser tries to assign to the attribute, Python raises
    :class:`AttributeError` because instances don't have a ``__dict__``.
    """

    _base_slots = tuple(Application.__slots__)
    _extra_slots = []
    if "_Application__stop_running_marker" not in _base_slots:
        _extra_slots.append("_Application__stop_running_marker")
    if "__weakref__" not in _base_slots:
        _extra_slots.append("__weakref__")
    __slots__ = _base_slots + tuple(_extra_slots)


async def sync_offline_entries(app: Application) -> None:
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(flush_offline_entries),
            timeout=SHEETS_THREAD_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.error(
            "Offline sync timed out after %.1f seconds.",
            SHEETS_THREAD_TIMEOUT_SECONDS,
        )
        record_error("offline_sync", "Timeout while syncing offline entries")
        return
    except Exception:
        logger.exception("Offline sync failed.")
        record_error("offline_sync", "Unexpected offline sync failure")
        return

    if result.error:
        logger.error(
            "GSHEET ERROR: %s %s",
            type(result.error).__name__,
            result.error,
        )
        record_error("gsheet", result.error)

    if result.processed:
        invalidate_records_cache()
        invalidate_sheet_index_cache()
        logger.info("Synced %s offline entries to Google Sheet.", result.processed)
        for chat_id in result.chat_ids:
            try:
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "✅ Оффлайн-записи синхронизированы: "
                        f"{result.processed} добавлено в таблицу."
                    ),
                )
            except Exception as exc:
                logger.warning(
                    "TELEGRAM ERROR: %s %s",
                    type(exc).__name__,
                    exc,
                )


async def on_error(update, context) -> None:
    error = getattr(context, "error", None)
    if isinstance(error, BaseException):
        logger.error(
            "BOT ERROR: %s %s",
            type(error).__name__,
            error,
            exc_info=(type(error), error, error.__traceback__),
        )
        record_error("telegram", error)
    else:
        logger.error("BOT ERROR: %s", error)
        record_error("telegram", str(error))

    if update and getattr(update, "effective_message", None):
        try:
            await update.effective_message.reply_text(
                "Произошла временная ошибка. Попробуйте ещё раз."
            )
        except Exception:
            pass


__all__ = [
    "PatchedApplication",
    "sync_offline_entries",
    "on_error",
]
