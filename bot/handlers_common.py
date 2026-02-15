"""Compatibility facade for legacy imports from handlers_common."""

from __future__ import annotations

from bot.handlers_sheet import (
    _extract_row_timestamp,
    _fetch_records_sync,
    _format_entry,
    _make_page_keyboard,
    _month_label,
    _month_with_offset,
    _normalize_rating,
    _parse_timestamp,
    _parse_winner_month_offset,
    _run_sheet_call,
    _safe_fetch_records,
    _send_paginated_list,
    _winner_navigation_keyboard,
)
from bot.handlers_transport import (
    _notify_table_unavailable,
    _reply,
    _send,
    _send_panel,
)

__all__ = [
    "_make_page_keyboard",
    "_send_paginated_list",
    "_send",
    "_send_panel",
    "_reply",
    "_notify_table_unavailable",
    "_fetch_records_sync",
    "_run_sheet_call",
    "_safe_fetch_records",
    "_format_entry",
    "_parse_timestamp",
    "_extract_row_timestamp",
    "_month_label",
    "_month_with_offset",
    "_parse_winner_month_offset",
    "_winner_navigation_keyboard",
    "_normalize_rating",
]
