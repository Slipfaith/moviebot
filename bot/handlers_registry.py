"""Registration helpers for telegram handlers."""

from __future__ import annotations

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.commands import (
    COMMAND_AI,
    COMMAND_FIND,
    COMMAND_HELP,
    COMMAND_LIST,
    COMMAND_MENU,
    COMMAND_OWNER,
    COMMAND_RANDOM,
    COMMAND_RECENT,
    COMMAND_RECOMMEND,
    COMMAND_SEARCH,
    COMMAND_START,
    COMMAND_STATS,
    COMMAND_TOP,
    COMMAND_WINNER,
    REGISTRY_ORDER,
)
from bot.handlers_add_flow import build_add_flow_handler
from bot.handlers_ai_random import random_command
from bot.handlers_ai_recommend import ai_command, recommend_command
from bot.handlers_base import handle_callback, handle_message, help_command, menu_command, start_command
from bot.handlers_library_lists import list_command, recent_command, top_command
from bot.handlers_library_queries import find_command, owner_command, search_command
from bot.handlers_photo import handle_photo
from bot.handlers_stats import stats_command, winner_command


_COMMAND_CALLBACKS = {
    COMMAND_START: start_command,
    COMMAND_HELP: help_command,
    COMMAND_MENU: menu_command,
    COMMAND_AI: ai_command,
    COMMAND_RECOMMEND: recommend_command,
    COMMAND_FIND: find_command,
    COMMAND_SEARCH: search_command,
    COMMAND_LIST: list_command,
    COMMAND_STATS: stats_command,
    COMMAND_WINNER: winner_command,
    COMMAND_RANDOM: random_command,
    COMMAND_OWNER: owner_command,
    COMMAND_TOP: top_command,
    COMMAND_RECENT: recent_command,
}


def register_handlers(app: Application) -> None:
    for command in REGISTRY_ORDER:
        app.add_handler(CommandHandler(command, _COMMAND_CALLBACKS[command]))

    app.add_handler(build_add_flow_handler())
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))


__all__ = ["register_handlers"]
