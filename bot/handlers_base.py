"""Base UI handlers."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers_router import route_callback, route_quick_button
from bot.handlers_texts import HELP_TEXT
from bot.handlers_transport import _send, _send_panel
from bot.interface import get_main_menu
from bot.ui_texts import PANEL_TITLE_MAIN, PANEL_TITLE_START, QUICK_BUTTONS_HINT_TEXT, UNKNOWN_TEXT_GUIDE


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_panel(update, PANEL_TITLE_START, get_main_menu())
    await _send(update, QUICK_BUTTONS_HINT_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, HELP_TEXT)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_panel(update, PANEL_TITLE_MAIN, get_main_menu())
    await _send(update, QUICK_BUTTONS_HINT_TEXT)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await route_callback(update, context):
        return
    if update.callback_query:
        await update.callback_query.answer()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip() if update.message else ""
    if await route_quick_button(update, context, text):
        return
    await _send(update, UNKNOWN_TEXT_GUIDE)


__all__ = [
    "start_command",
    "help_command",
    "menu_command",
    "handle_callback",
    "handle_message",
]
