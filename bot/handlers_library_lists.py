"""List/top/recent library handlers."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers_sheet import _send_paginated_list


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_paginated_list(update, context, "top", 0)


async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_paginated_list(update, context, "recent", 0)


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_paginated_list(update, context, "list", 0)


__all__ = [
    "top_command",
    "recent_command",
    "list_command",
]
