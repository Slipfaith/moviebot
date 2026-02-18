"""Compatibility layer for legacy imports from bot.handlers_shared."""

from __future__ import annotations

from typing import Dict, List, Tuple

from bot.handlers_texts import (
    ADD_COMMENT,
    ADD_CONFIRM,
    ADD_FILM,
    ADD_GENRE,
    ADD_OWNER,
    ADD_POSTER_EDIT,
    ADD_POSTER_EDIT_TEXT,
    ADD_RATING,
    ADD_RECOMMENDATION,
    ADD_TYPE,
    ADD_USAGE_TEXT,
    ADD_VOICE_CLARIFY,
    ADD_YEAR,
    HELP_TEXT,
    OFFLINE_GUIDE_TEXT,
)


def _pairs(module_name: str, *names: str) -> Dict[str, Tuple[str, str]]:
    return {name: (module_name, name) for name in names}


_DELEGATED_NAMES: Dict[str, Tuple[str, str]] = {}
_DELEGATED_NAMES.update(
    _pairs(
        "bot.handlers_add_flow",
        "_add_entry_to_sheet",
        "_add_entry_to_sheet_sync",
        "_comment_keyboard",
        "_confirm_keyboard",
        "_extract_add_payload",
        "_finish_add_flow",
        "_owner_keyboard",
        "_parse_add_payload",
        "_recommendation_keyboard",
        "_type_keyboard",
        "add_command",
        "add_flow_comment",
        "add_flow_comment_skip",
        "add_flow_confirm_cancel",
        "add_flow_confirm_save",
        "add_flow_film",
        "add_flow_genre",
        "add_flow_owner",
        "add_flow_owner_select",
        "add_flow_poster_edit_text_start",
        "add_flow_poster_edit_open",
        "add_flow_poster_edit_set_type",
        "add_flow_poster_edit_set_recommendation",
        "add_flow_poster_edit_set_owner",
        "add_flow_poster_edit_back",
        "add_flow_poster_edit_text_value",
        "add_flow_rating",
        "add_flow_recommendation",
        "add_flow_recommendation_select",
        "add_flow_type",
        "add_flow_type_select",
        "add_flow_voice",
        "add_flow_voice_clarify_text",
        "add_flow_voice_clarify_hint",
        "add_flow_voice_cancel",
        "add_flow_year",
        "build_add_flow_handler",
        "cancel_add_flow",
        "start_add_flow_from_poster",
        "start_add_flow",
    )
)
_DELEGATED_NAMES.update(
    _pairs(
        "bot.handlers_ai_helpers",
        "_ai_single_unseen_pick",
        "_build_ai_cache_key",
        "_build_quick_add_keyboard",
        "_build_quick_add_keyboard_from_formatted",
        "_build_watched_dedupe_lookup",
        "_extract_json_dict",
        "_extract_titles_from_formatted_recommendations",
        "_extract_year_from_title_label",
        "_filter_recent_candidates",
        "_format_ai_answer_for_telegram",
        "_get_ai_cached_response",
        "_parse_single_recommendation",
        "_pick_weighted_random_candidate",
        "_store_ai_cached_response",
    )
)
_DELEGATED_NAMES.update(
    _pairs(
        "bot.handlers_cache",
        "_get_cached_profile",
        "_get_cached_response",
        "_get_recent_recommendations",
        "_invalidate_response_cache",
        "_normalize_title_for_dedupe",
        "_prune_recent_recommendations_cache",
        "_recommendation_scope_key",
        "_store_cached_profile",
        "_store_cached_response",
        "_store_recent_recommendations",
    )
)
_DELEGATED_NAMES.update(
    _pairs(
        "bot.handlers_sheet",
        "_extract_row_timestamp",
        "_fetch_records_sync",
        "_format_entry",
        "_make_page_keyboard",
        "_month_label",
        "_month_with_offset",
        "_normalize_rating",
        "_parse_timestamp",
        "_parse_winner_month_offset",
        "_run_sheet_call",
        "_safe_fetch_records",
        "_send_paginated_list",
        "_winner_navigation_keyboard",
    )
)
_DELEGATED_NAMES.update(
    _pairs(
        "bot.handlers_transport",
        "_notify_table_unavailable",
        "_reply",
        "_send",
        "_send_panel",
    )
)
_DELEGATED_NAMES.update(_pairs("bot.handlers_ai", "_run_ai_recommendation", "ai_command", "recommend_command", "random_command"))
_DELEGATED_NAMES.update(
    _pairs(
        "bot.handlers_library",
        "find_command",
        "list_command",
        "owner_command",
        "recent_command",
        "search_command",
        "top_command",
    )
)
_DELEGATED_NAMES.update(_pairs("bot.handlers_base", "handle_callback", "handle_message", "help_command", "menu_command", "start_command"))
_DELEGATED_NAMES.update(_pairs("bot.handlers_stats", "stats_command", "winner_command"))
_DELEGATED_NAMES.update(_pairs("bot.handlers_diag", "diag_command"))
_DELEGATED_NAMES.update(_pairs("bot.handlers_photo", "handle_photo"))


def __getattr__(name: str):
    target = _DELEGATED_NAMES.get(name)
    if not target:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = __import__(module_name, fromlist=[attr_name])
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> List[str]:
    return sorted(set(globals()) | set(_DELEGATED_NAMES))


__all__ = [
    "HELP_TEXT",
    "OFFLINE_GUIDE_TEXT",
    "ADD_USAGE_TEXT",
    "ADD_FILM",
    "ADD_YEAR",
    "ADD_GENRE",
    "ADD_RATING",
    "ADD_COMMENT",
    "ADD_TYPE",
    "ADD_RECOMMENDATION",
    "ADD_OWNER",
    "ADD_CONFIRM",
    "ADD_VOICE_CLARIFY",
    "ADD_POSTER_EDIT",
    "ADD_POSTER_EDIT_TEXT",
] + list(_DELEGATED_NAMES)
