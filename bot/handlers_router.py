"""Routing helpers for callback data and quick-button text."""

from __future__ import annotations

from typing import Awaitable, Callable, Dict

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot.callback_ids import (
    AI_HELP,
    HELP,
    LIST_FILMS,
    MENU_HELP,
    MENU_LIBRARY,
    MENU_MAIN,
    MENU_RECOMMEND,
    MENU_STATS,
    NOOP,
    OFFLINE_HELP,
    OWNER_HUSBAND,
    OWNER_WIFE,
    RANDOM_PICK,
    RATING_STATS,
    RECENT_ENTRIES,
    RECOMMEND_ME,
    SEARCH_GENRE,
    SEARCH_TITLE,
    TOKEN_USAGE,
    TOKEN_USAGE_RESET,
    TOP5,
    WINNER_MONTH,
    parse_page_callback,
    parse_winner_month_offset,
)
from bot.handlers_ai_random import random_command
from bot.handlers_ai_recommend import recommend_command
from bot.handlers_library_lists import list_command, recent_command, top_command
from bot.handlers_library_queries import owner_command
from bot.handlers_sheet import _send_paginated_list
from bot.handlers_stats import (
    stats_command,
    token_usage_command,
    token_usage_reset_command,
    winner_command,
)
from bot.handlers_texts import HELP_TEXT, OFFLINE_GUIDE_TEXT
from bot.handlers_transport import _send, _send_panel
from bot.interface import (
    QUICK_BUTTON_LAST,
    QUICK_BUTTON_MENU,
    QUICK_BUTTON_RANDOM,
    QUICK_BUTTON_RECOMMEND,
    QUICK_BUTTON_STATS,
    get_help_menu,
    get_library_menu,
    get_main_menu,
    get_recommend_menu,
    get_stats_menu,
)
from bot.ui_texts import (
    AI_HELP_HINT_TEXT,
    PANEL_TITLE_HELP,
    PANEL_TITLE_LIBRARY,
    PANEL_TITLE_MAIN,
    PANEL_TITLE_RECOMMEND,
    PANEL_TITLE_STATS,
    QUICK_BUTTONS_HINT_TEXT,
    RECOMMEND_LOADING_TEXT,
    SEARCH_GENRE_HINT_TEXT,
    SEARCH_TITLE_HINT_TEXT,
)

HandlerCallback = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]
PanelFactory = Callable[[], object]

_PANEL_ROUTES: Dict[str, tuple[str, PanelFactory]] = {
    MENU_MAIN: (PANEL_TITLE_MAIN, get_main_menu),
    MENU_RECOMMEND: (PANEL_TITLE_RECOMMEND, get_recommend_menu),
    MENU_LIBRARY: (PANEL_TITLE_LIBRARY, get_library_menu),
    MENU_STATS: (PANEL_TITLE_STATS, get_stats_menu),
    MENU_HELP: (PANEL_TITLE_HELP, get_help_menu),
}

_ACTION_ROUTES: Dict[str, HandlerCallback] = {
    TOP5: top_command,
    RECENT_ENTRIES: recent_command,
    LIST_FILMS: list_command,
    RATING_STATS: stats_command,
    WINNER_MONTH: winner_command,
    RANDOM_PICK: random_command,
    TOKEN_USAGE: token_usage_command,
    TOKEN_USAGE_RESET: token_usage_reset_command,
}

_OWNER_ROUTES = {
    OWNER_HUSBAND: "муж",
    OWNER_WIFE: "жена",
}

_MESSAGE_ROUTES = {
    SEARCH_GENRE: SEARCH_GENRE_HINT_TEXT,
    SEARCH_TITLE: SEARCH_TITLE_HINT_TEXT,
    AI_HELP: AI_HELP_HINT_TEXT,
    HELP: HELP_TEXT,
    OFFLINE_HELP: OFFLINE_GUIDE_TEXT,
}

_QUICK_BUTTON_ROUTES: Dict[str, HandlerCallback] = {
    QUICK_BUTTON_RECOMMEND: recommend_command,
    QUICK_BUTTON_LAST: list_command,
    QUICK_BUTTON_RANDOM: random_command,
    QUICK_BUTTON_STATS: stats_command,
}


async def _answer_callback_quietly(update: Update) -> None:
    if not update.callback_query:
        return
    try:
        await update.callback_query.answer()
    except BadRequest:
        pass


async def route_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.callback_query:
        return False
    data = update.callback_query.data or ""

    panel_route = _PANEL_ROUTES.get(data)
    if panel_route:
        title, panel_builder = panel_route
        await _send_panel(update, title, panel_builder())
        return True

    action = _ACTION_ROUTES.get(data)
    if action:
        await _answer_callback_quietly(update)
        await action(update, context)
        return True

    if parse_winner_month_offset(data) is not None:
        await _answer_callback_quietly(update)
        await winner_command(update, context)
        return True

    owner_arg = _OWNER_ROUTES.get(data)
    if owner_arg:
        await _answer_callback_quietly(update)
        context.args = [owner_arg]
        await owner_command(update, context)
        return True

    text_message = _MESSAGE_ROUTES.get(data)
    if text_message:
        await _send(update, text_message)
        return True

    if data == RECOMMEND_ME:
        try:
            await update.callback_query.answer(RECOMMEND_LOADING_TEXT)
        except BadRequest:
            pass
        await recommend_command(update, context)
        return True

    if data == NOOP:
        await update.callback_query.answer()
        return True

    page_data = parse_page_callback(data)
    if page_data is not None:
        await _answer_callback_quietly(update)
        cmd, page = page_data
        await _send_paginated_list(update, context, cmd, page)
        return True

    return False


async def route_quick_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> bool:
    action = _QUICK_BUTTON_ROUTES.get(text)
    if action:
        await action(update, context)
        return True

    if text == QUICK_BUTTON_MENU:
        await _send_panel(update, PANEL_TITLE_MAIN, get_main_menu())
        await _send(update, QUICK_BUTTONS_HINT_TEXT)
        return True

    return False


__all__ = ["route_callback", "route_quick_button"]
