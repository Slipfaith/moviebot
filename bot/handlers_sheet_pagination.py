"""Pagination helpers for list/top/recent responses."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.callback_ids import NOOP, page_callback
from bot.handlers_sheet_format import _format_entry, _parse_timestamp
from bot.handlers_sheet_io import _safe_fetch_records
from bot.handlers_transport import _send, _send_panel, _typing
from core.gsheet import recent_entries, top_by_rating

_PAGE_SIZE = 5


def _make_page_keyboard(cmd: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    row: List[InlineKeyboardButton] = []
    if page > 0:
        row.append(InlineKeyboardButton("⬅️", callback_data=page_callback(cmd, page - 1)))
    row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data=NOOP))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton("➡️", callback_data=page_callback(cmd, page + 1)))
    return InlineKeyboardMarkup([row])


def _sort_list_items(records: List[Dict[str, str]]) -> List[Dict[str, str]]:
    stamped_rows: List[Tuple[datetime, Dict[str, str]]] = []
    no_stamp_rows: List[Dict[str, str]] = []
    for row in records:
        ts_val = row.get("Добавлено") or row.get("Timestamp") or row.get("Дата") or row.get("Added") or ""
        parsed = _parse_timestamp(str(ts_val)) if ts_val else None
        if parsed:
            stamped_rows.append((parsed, row))
        else:
            no_stamp_rows.append(row)
    if stamped_rows:
        stamped_rows.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in stamped_rows] + no_stamp_rows
    return list(records)


async def _send_paginated_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    cmd: str,
    page: int,
) -> None:
    async with _typing(update, context):
        records = await _safe_fetch_records(update)
        if records is None:
            return

        if cmd == "list":
            items = _sort_list_items(records)
            header = "📝 Последние добавления"
        elif cmd == "top":
            items = top_by_rating(records, 20)
            header = "🏆 Топ фильмов"
        elif cmd == "recent":
            items = recent_entries(records)
            header = "🗓 За последние 30 дней"
        else:
            return

        if not items:
            await _send(update, "Нет записей.")
            return

        total_pages = max(1, (len(items) + _PAGE_SIZE - 1) // _PAGE_SIZE)
        page = max(0, min(page, total_pages - 1))
        start = page * _PAGE_SIZE
        slice_items = items[start : start + _PAGE_SIZE]

        if cmd == "top":
            lines = [f"{start + i + 1}. {_format_entry(row)}" for i, row in enumerate(slice_items)]
        else:
            lines = [_format_entry(row) for row in slice_items]

        text = f"{header}:\n" + "\n".join(lines)
        await _send_panel(update, text, _make_page_keyboard(cmd, page, total_pages))


__all__ = [
    "_make_page_keyboard",
    "_send_paginated_list",
]
