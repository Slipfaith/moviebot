"""Winner-month navigation/date helpers."""

from __future__ import annotations

from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.callback_ids import parse_winner_month_offset, winner_month_callback


def _month_label(dt: datetime) -> str:
    names = [
        "январь",
        "февраль",
        "март",
        "апрель",
        "май",
        "июнь",
        "июль",
        "август",
        "сентябрь",
        "октябрь",
        "ноябрь",
        "декабрь",
    ]
    return f"{names[dt.month - 1]} {dt.year}"


def _month_with_offset(dt: datetime, offset: int) -> datetime:
    month_index = dt.year * 12 + (dt.month - 1) + offset
    year = month_index // 12
    month = (month_index % 12) + 1
    return datetime(year=year, month=month, day=1)


def _parse_winner_month_offset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query and update.callback_query.data:
        parsed = parse_winner_month_offset(update.callback_query.data)
        if parsed is not None:
            return parsed
    if context.args:
        try:
            return int((context.args[0] or "").strip())
        except (TypeError, ValueError):
            return 0
    return 0


def _winner_navigation_keyboard(offset: int) -> InlineKeyboardMarkup:
    prev_offset = offset - 1
    next_offset = min(offset + 1, 0)
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("◀ Пред. месяц", callback_data=winner_month_callback(prev_offset)),
            InlineKeyboardButton("Текущий", callback_data=winner_month_callback(0)),
            InlineKeyboardButton("След. месяц ▶", callback_data=winner_month_callback(next_offset)),
        ]]
    )


__all__ = [
    "_month_label",
    "_month_with_offset",
    "_parse_winner_month_offset",
    "_winner_navigation_keyboard",
]
