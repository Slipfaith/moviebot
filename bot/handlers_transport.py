"""Telegram transport helpers shared by handlers."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from typing import Optional

from telegram import InlineKeyboardMarkup, Message, Update
from telegram.constants import ChatAction
from telegram.error import BadRequest

from bot.interface import get_main_menu, get_quick_actions_keyboard


async def _send(
    update: Update,
    text: str,
    *,
    show_menu: bool = False,
    parse_mode: Optional[str] = None,
) -> Optional[Message]:
    reply_markup = get_main_menu() if show_menu else get_quick_actions_keyboard()
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except BadRequest as exc:
            message = str(exc).lower()
            # Callback can expire while we build recommendations; ignore only that case.
            if "query is too old" not in message and "query id is invalid" not in message:
                raise
        if show_menu:
            try:
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
                return None
            except BadRequest:
                return await update.callback_query.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
        else:
            return await update.callback_query.message.reply_text(
                text=text,
                reply_markup=get_quick_actions_keyboard(),
                parse_mode=parse_mode,
            )

    if update.message:
        return await update.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    return None


async def _send_panel(
    update: Update,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    *,
    parse_mode: Optional[str] = None,
) -> Optional[Message]:
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except BadRequest as exc:
            message = str(exc).lower()
            if "query is too old" not in message and "query id is invalid" not in message:
                raise
        try:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return None
        except BadRequest:
            return await update.callback_query.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )

    if update.message:
        return await update.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    return None


async def _reply(
    update: Update,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    *,
    parse_mode: Optional[str] = None,
) -> Optional[Message]:
    if update.callback_query:
        return await update.callback_query.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    elif update.message:
        return await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    return None


async def _notify_table_unavailable(update: Update, action: str = "запрос") -> None:
    await _send(
        update,
        "⚠️ Сейчас нет связи с таблицей, поэтому выполнить "
        f"{action} не получилось. Попробуйте позже.",
    )


@asynccontextmanager
async def _typing(
    update: Update,
    context,
    *,
    interval_seconds: float = 4.0,
):
    chat = update.effective_chat
    if not chat:
        yield
        return

    # Show typing immediately and then refresh it until handler completes.
    try:
        await context.bot.send_chat_action(
            chat_id=chat.id,
            action=ChatAction.TYPING,
        )
    except Exception:
        pass

    stop_event = asyncio.Event()

    async def _loop() -> None:
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=max(interval_seconds, 1.0))
                break
            except asyncio.TimeoutError:
                pass
            try:
                await context.bot.send_chat_action(
                    chat_id=chat.id,
                    action=ChatAction.TYPING,
                )
            except Exception:
                pass

    task = asyncio.create_task(_loop())
    try:
        yield
    finally:
        stop_event.set()
        with suppress(Exception):
            await asyncio.wait_for(task, timeout=1.5)


__all__ = [
    "_send",
    "_send_panel",
    "_reply",
    "_notify_table_unavailable",
    "_typing",
]
