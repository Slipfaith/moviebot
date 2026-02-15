"""Statistics handlers."""

from __future__ import annotations

from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.callback_ids import MENU_STATS, TOKEN_USAGE_RESET
from bot.handlers_sheet import (
    _month_label,
    _month_with_offset,
    _parse_winner_month_offset,
    _safe_fetch_records,
    _winner_navigation_keyboard,
)
from bot.handlers_stats_logic import (
    build_stats_text,
    build_token_usage_text,
    build_winner_text,
)
from bot.handlers_transport import _send, _send_panel, _typing
from bot.ui_texts import BUTTON_BACK, BUTTON_TOKEN_USAGE_RESET
from core.token_usage import (
    get_token_usage_snapshot,
    reset_token_usage,
    token_usage_backup_dir_path,
    token_usage_file_path,
)


def _token_usage_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(BUTTON_TOKEN_USAGE_RESET, callback_data=TOKEN_USAGE_RESET)],
            [InlineKeyboardButton(BUTTON_BACK, callback_data=MENU_STATS)],
        ]
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with _typing(update, context):
        records = await _safe_fetch_records(update)
        if records is None:
            return

        await _send(update, build_stats_text(records))


async def winner_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with _typing(update, context):
        records = await _safe_fetch_records(update)
        if records is None:
            return

        month_offset = _parse_winner_month_offset(update, context)
        target_month = _month_with_offset(datetime.now(), month_offset)
        month_name = _month_label(target_month)
        _, text = build_winner_text(
            records,
            target_month=target_month,
            month_name=month_name,
        )
        await _send_panel(update, text, _winner_navigation_keyboard(month_offset))


async def token_usage_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stats = get_token_usage_snapshot()
    text = build_token_usage_text(
        stats,
        file_path=str(token_usage_file_path()),
        backup_dir=str(token_usage_backup_dir_path()),
    )
    await _send_panel(update, text, _token_usage_keyboard())


async def token_usage_reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stats = reset_token_usage()
    text = build_token_usage_text(
        stats,
        file_path=str(token_usage_file_path()),
        backup_dir=str(token_usage_backup_dir_path()),
        was_reset=True,
    )
    await _send_panel(update, text, _token_usage_keyboard())


__all__ = [
    "stats_command",
    "winner_command",
    "token_usage_command",
    "token_usage_reset_command",
]
