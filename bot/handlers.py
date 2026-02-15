"""Public handlers facade for legacy imports."""

from __future__ import annotations

from typing import Dict, List, Tuple

_DELEGATED_NAMES: Dict[str, Tuple[str, str]] = {
    "ADD_FILM": ("bot.handlers_add_flow", "ADD_FILM"),
    "ADD_YEAR": ("bot.handlers_add_flow", "ADD_YEAR"),
    "ADD_GENRE": ("bot.handlers_add_flow", "ADD_GENRE"),
    "ADD_RATING": ("bot.handlers_add_flow", "ADD_RATING"),
    "ADD_COMMENT": ("bot.handlers_add_flow", "ADD_COMMENT"),
    "ADD_TYPE": ("bot.handlers_add_flow", "ADD_TYPE"),
    "ADD_RECOMMENDATION": ("bot.handlers_add_flow", "ADD_RECOMMENDATION"),
    "ADD_OWNER": ("bot.handlers_add_flow", "ADD_OWNER"),
    "ADD_CONFIRM": ("bot.handlers_add_flow", "ADD_CONFIRM"),
    "ADD_VOICE_CLARIFY": ("bot.handlers_add_flow", "ADD_VOICE_CLARIFY"),
    "add_command": ("bot.handlers_add_flow", "add_command"),
    "start_add_flow": ("bot.handlers_add_flow", "start_add_flow"),
    "start_add_flow_from_poster": ("bot.handlers_add_flow", "start_add_flow_from_poster"),
    "add_flow_film": ("bot.handlers_add_flow", "add_flow_film"),
    "add_flow_year": ("bot.handlers_add_flow", "add_flow_year"),
    "add_flow_genre": ("bot.handlers_add_flow", "add_flow_genre"),
    "add_flow_rating": ("bot.handlers_add_flow", "add_flow_rating"),
    "add_flow_comment": ("bot.handlers_add_flow", "add_flow_comment"),
    "add_flow_comment_skip": ("bot.handlers_add_flow", "add_flow_comment_skip"),
    "add_flow_type": ("bot.handlers_add_flow", "add_flow_type"),
    "add_flow_type_select": ("bot.handlers_add_flow", "add_flow_type_select"),
    "add_flow_recommendation": ("bot.handlers_add_flow", "add_flow_recommendation"),
    "add_flow_recommendation_select": ("bot.handlers_add_flow", "add_flow_recommendation_select"),
    "add_flow_owner": ("bot.handlers_add_flow", "add_flow_owner"),
    "add_flow_owner_select": ("bot.handlers_add_flow", "add_flow_owner_select"),
    "add_flow_confirm_save": ("bot.handlers_add_flow", "add_flow_confirm_save"),
    "add_flow_confirm_cancel": ("bot.handlers_add_flow", "add_flow_confirm_cancel"),
    "cancel_add_flow": ("bot.handlers_add_flow", "cancel_add_flow"),
    "add_flow_voice": ("bot.handlers_add_flow", "add_flow_voice"),
    "add_flow_voice_clarify_text": ("bot.handlers_add_flow", "add_flow_voice_clarify_text"),
    "add_flow_voice_clarify_hint": ("bot.handlers_add_flow", "add_flow_voice_clarify_hint"),
    "add_flow_voice_cancel": ("bot.handlers_add_flow", "add_flow_voice_cancel"),
    "build_add_flow_handler": ("bot.handlers_add_flow", "build_add_flow_handler"),
    "start_command": ("bot.handlers_base", "start_command"),
    "help_command": ("bot.handlers_base", "help_command"),
    "menu_command": ("bot.handlers_base", "menu_command"),
    "handle_message": ("bot.handlers_base", "handle_message"),
    "handle_callback": ("bot.handlers_base", "handle_callback"),
    "ai_command": ("bot.handlers_ai", "ai_command"),
    "recommend_command": ("bot.handlers_ai", "recommend_command"),
    "random_command": ("bot.handlers_ai", "random_command"),
    "find_command": ("bot.handlers_library", "find_command"),
    "search_command": ("bot.handlers_library", "search_command"),
    "list_command": ("bot.handlers_library", "list_command"),
    "top_command": ("bot.handlers_library", "top_command"),
    "recent_command": ("bot.handlers_library", "recent_command"),
    "owner_command": ("bot.handlers_library", "owner_command"),
    "stats_command": ("bot.handlers_stats", "stats_command"),
    "winner_command": ("bot.handlers_stats", "winner_command"),
    "handle_photo": ("bot.handlers_photo", "handle_photo"),
}


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


__all__ = list(_DELEGATED_NAMES)
