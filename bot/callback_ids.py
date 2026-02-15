"""Callback-data identifiers and parser/builders."""

from __future__ import annotations

from typing import Optional, Tuple

MENU_MAIN = "menu_main"
MENU_RECOMMEND = "menu_recommend"
MENU_LIBRARY = "menu_library"
MENU_STATS = "menu_stats"
MENU_HELP = "menu_help"

ADD_FILM = "add_film"

TOP5 = "top5"
RECENT_ENTRIES = "recent_entries"
LIST_FILMS = "list_films"
RATING_STATS = "rating_stats"
RANDOM_PICK = "random_pick"
TOKEN_USAGE = "token_usage"
TOKEN_USAGE_RESET = "token_usage_reset"

OWNER_HUSBAND = "owner_husband"
OWNER_WIFE = "owner_wife"

SEARCH_GENRE = "search_genre"
SEARCH_TITLE = "search_title"

RECOMMEND_ME = "recommend_me"
AI_HELP = "ai_help"
HELP = "help"
OFFLINE_HELP = "offline_help"
NOOP = "noop"

WINNER_MONTH = "winner_month"
WINNER_MONTH_PREFIX = f"{WINNER_MONTH}:"

PAGE_PREFIX = "page:"

ADD_FLOW_SKIP_COMMENT = "add_flow:skip_comment"
ADD_FLOW_TYPE_FILM = "add_flow:type:film"
ADD_FLOW_TYPE_SERIES = "add_flow:type:series"
ADD_FLOW_REC_RECOMMEND = "add_flow:rec:recommend"
ADD_FLOW_REC_OK = "add_flow:rec:ok"
ADD_FLOW_REC_SKIP = "add_flow:rec:skip"
ADD_FLOW_OWNER_HUSBAND = "add_flow:owner:husband"
ADD_FLOW_OWNER_WIFE = "add_flow:owner:wife"
ADD_FLOW_OWNER_SKIP = "add_flow:owner:skip"
ADD_FLOW_CONFIRM_SAVE = "add_flow:confirm:save"
ADD_FLOW_CONFIRM_CANCEL = "add_flow:confirm:cancel"
ADD_FLOW_FROM_POSTER = "add_flow:from_poster"
ADD_FLOW_VOICE_CLARIFY_TEXT = "add_flow:voice:clarify_text"
ADD_FLOW_VOICE_CLARIFY_VOICE = "add_flow:voice:clarify_voice"
ADD_FLOW_VOICE_CANCEL = "add_flow:voice:cancel"

PATTERN_ADD_FILM = r"^add_film$"
PATTERN_ADD_FLOW_SKIP_COMMENT = r"^add_flow:skip_comment$"
PATTERN_ADD_FLOW_TYPE = r"^add_flow:type:(film|series)$"
PATTERN_ADD_FLOW_REC = r"^add_flow:rec:(recommend|ok|skip)$"
PATTERN_ADD_FLOW_OWNER = r"^add_flow:owner:(husband|wife|skip)$"
PATTERN_ADD_FLOW_CONFIRM_SAVE = r"^add_flow:confirm:save$"
PATTERN_ADD_FLOW_CONFIRM_CANCEL = r"^add_flow:confirm:cancel$"
PATTERN_ADD_FLOW_FROM_POSTER = r"^add_flow:from_poster$"
PATTERN_ADD_FLOW_VOICE_CLARIFY_HINT = r"^add_flow:voice:clarify_(text|voice)$"
PATTERN_ADD_FLOW_VOICE_CANCEL = r"^add_flow:voice:cancel$"


def winner_month_callback(offset: int) -> str:
    return f"{WINNER_MONTH}:{offset}"


def parse_winner_month_offset(data: str) -> Optional[int]:
    if data == WINNER_MONTH:
        return 0
    if not data.startswith(WINNER_MONTH_PREFIX):
        return None
    raw = data.split(":", 1)[1]
    try:
        return int(raw)
    except ValueError:
        return 0


def page_callback(command: str, page: int) -> str:
    return f"page:{command}:{page}"


def parse_page_callback(data: str) -> Optional[Tuple[str, int]]:
    if not data.startswith(PAGE_PREFIX):
        return None
    parts = data.split(":")
    if len(parts) != 3:
        return None
    _, command, raw_page = parts
    try:
        page = int(raw_page)
    except ValueError:
        page = 0
    return command, page


__all__ = [
    "MENU_MAIN",
    "MENU_RECOMMEND",
    "MENU_LIBRARY",
    "MENU_STATS",
    "MENU_HELP",
    "ADD_FILM",
    "TOP5",
    "RECENT_ENTRIES",
    "LIST_FILMS",
    "RATING_STATS",
    "RANDOM_PICK",
    "TOKEN_USAGE",
    "TOKEN_USAGE_RESET",
    "OWNER_HUSBAND",
    "OWNER_WIFE",
    "SEARCH_GENRE",
    "SEARCH_TITLE",
    "RECOMMEND_ME",
    "AI_HELP",
    "HELP",
    "OFFLINE_HELP",
    "NOOP",
    "WINNER_MONTH",
    "WINNER_MONTH_PREFIX",
    "PAGE_PREFIX",
    "ADD_FLOW_SKIP_COMMENT",
    "ADD_FLOW_TYPE_FILM",
    "ADD_FLOW_TYPE_SERIES",
    "ADD_FLOW_REC_RECOMMEND",
    "ADD_FLOW_REC_OK",
    "ADD_FLOW_REC_SKIP",
    "ADD_FLOW_OWNER_HUSBAND",
    "ADD_FLOW_OWNER_WIFE",
    "ADD_FLOW_OWNER_SKIP",
    "ADD_FLOW_CONFIRM_SAVE",
    "ADD_FLOW_CONFIRM_CANCEL",
    "ADD_FLOW_FROM_POSTER",
    "ADD_FLOW_VOICE_CLARIFY_TEXT",
    "ADD_FLOW_VOICE_CLARIFY_VOICE",
    "ADD_FLOW_VOICE_CANCEL",
    "PATTERN_ADD_FILM",
    "PATTERN_ADD_FLOW_SKIP_COMMENT",
    "PATTERN_ADD_FLOW_TYPE",
    "PATTERN_ADD_FLOW_REC",
    "PATTERN_ADD_FLOW_OWNER",
    "PATTERN_ADD_FLOW_CONFIRM_SAVE",
    "PATTERN_ADD_FLOW_CONFIRM_CANCEL",
    "PATTERN_ADD_FLOW_FROM_POSTER",
    "PATTERN_ADD_FLOW_VOICE_CLARIFY_HINT",
    "PATTERN_ADD_FLOW_VOICE_CANCEL",
    "winner_month_callback",
    "parse_winner_month_offset",
    "page_callback",
    "parse_page_callback",
]
