"""Search/query library handlers."""

from __future__ import annotations

import html
from typing import List

from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers_cache import _get_cached_response, _store_cached_response
from bot.handlers_sheet import _format_entry, _safe_fetch_records
from bot.handlers_transport import _send, _typing
from bot.ui_texts import (
    LIB_FIND_FOUND_HEADER,
    LIB_FIND_NOT_FOUND_TEXT,
    LIB_FIND_USAGE_TEXT,
    LIB_OWNER_HEADER_TEMPLATE,
    LIB_OWNER_NOT_FOUND_TEMPLATE,
    LIB_OWNER_USAGE_TEXT,
    LIB_SEARCH_MORE_TEMPLATE,
    LIB_SEARCH_NOT_FOUND_TEMPLATE,
    LIB_SEARCH_RESULTS_HEADER_TEMPLATE,
    LIB_SEARCH_USAGE_TEXT,
)
from core.gsheet import filter_by_genre
from core.normalization import normalize_owner


async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await _send(update, LIB_FIND_USAGE_TEXT)
        return

    genre = " ".join(context.args).strip()
    cache_key = f"find:{genre.lower()}"
    cached = _get_cached_response(cache_key)
    if cached:
        await _send(update, cached)
        return

    async with _typing(update, context):
        records = await _safe_fetch_records(update)
        if records is None:
            return

        filtered = filter_by_genre(records, genre)
        if not filtered:
            await _send(update, LIB_FIND_NOT_FOUND_TEXT)
            return

        text = f"{LIB_FIND_FOUND_HEADER}\n" + "\n".join(_format_entry(r) for r in filtered[:10])
        _store_cached_response(cache_key, text)
        await _send(update, text)


async def owner_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await _send(update, LIB_OWNER_USAGE_TEXT)
        return

    owner = normalize_owner(" ".join(context.args))
    if not owner:
        await _send(update, LIB_OWNER_USAGE_TEXT)
        return

    async with _typing(update, context):
        records = await _safe_fetch_records(update)
        if records is None:
            return

        filtered = [
            row
            for row in records
            if normalize_owner(row.get("Владелец") or row.get("Чье") or row.get("Owner") or "") == owner
        ]

        if not filtered:
            await _send(update, LIB_OWNER_NOT_FOUND_TEMPLATE.format(owner=owner))
            return

        text = f"{LIB_OWNER_HEADER_TEMPLATE.format(owner=owner)}\n" + "\n".join(
            _format_entry(r) for r in filtered[:10]
        )
        await _send(update, text)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await _send(update, LIB_SEARCH_USAGE_TEXT)
        return

    query = " ".join(context.args).strip()
    async with _typing(update, context):
        records = await _safe_fetch_records(update)
        if records is None:
            return

        query_lower = query.lower()
        filtered = [
            row
            for row in records
            if query_lower in (
                row.get("Фильм") or row.get("Название") or row.get("Film") or row.get("Title") or ""
            ).lower()
        ]

        if not filtered:
            await _send(update, LIB_SEARCH_NOT_FOUND_TEMPLATE.format(query=html.escape(query)))
            return

        lines: List[str] = [_format_entry(r) for r in filtered[:10]]
        text = f"{LIB_SEARCH_RESULTS_HEADER_TEMPLATE.format(query=html.escape(query))}\n" + "\n".join(lines)
        if len(filtered) > 10:
            text += LIB_SEARCH_MORE_TEMPLATE.format(count=len(filtered) - 10)
        await _send(update, text)


__all__ = [
    "find_command",
    "search_command",
    "owner_command",
]
