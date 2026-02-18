"""Cleanup helpers for add-flow conversational messages."""

from __future__ import annotations

from telegram import InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot.handlers_transport import _reply

_TRACKED_ADD_FLOW_MESSAGE_IDS = "_add_flow_message_ids"
_ADD_FLOW_PANEL_MESSAGE_ID = "_add_flow_panel_message_id"


def _tracked_message_ids(context: ContextTypes.DEFAULT_TYPE) -> list[int]:
    raw = context.user_data.get(_TRACKED_ADD_FLOW_MESSAGE_IDS)
    if isinstance(raw, list):
        return raw
    ids: list[int] = []
    context.user_data[_TRACKED_ADD_FLOW_MESSAGE_IDS] = ids
    return ids


def _track_message_id(context: ContextTypes.DEFAULT_TYPE, message_id: int | None) -> None:
    if not message_id:
        return
    ids = _tracked_message_ids(context)
    if message_id not in ids:
        ids.append(message_id)


def clear_add_flow_cleanup(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(_TRACKED_ADD_FLOW_MESSAGE_IDS, None)
    context.user_data.pop(_ADD_FLOW_PANEL_MESSAGE_ID, None)


def reset_add_flow_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_add_flow_cleanup(context)
    track_add_flow_user_message(update, context)


def track_add_flow_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        _track_message_id(context, update.message.message_id)


async def reply_add_flow(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
) -> None:
    message = await _reply(
        update,
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
    if message:
        _track_message_id(context, message.message_id)


def _panel_message_id(context: ContextTypes.DEFAULT_TYPE) -> int | None:
    raw = context.user_data.get(_ADD_FLOW_PANEL_MESSAGE_ID)
    return raw if isinstance(raw, int) else None


def _set_panel_message_id(context: ContextTypes.DEFAULT_TYPE, message_id: int | None) -> None:
    if not message_id:
        return
    context.user_data[_ADD_FLOW_PANEL_MESSAGE_ID] = message_id
    _track_message_id(context, message_id)


async def upsert_add_flow_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
) -> None:
    chat = update.effective_chat
    chat_id = chat.id if chat else None

    if update.callback_query and update.callback_query.message:
        message = update.callback_query.message
        try:
            await message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            _set_panel_message_id(context, message.message_id)
            return
        except BadRequest:
            pass
        except Exception:
            pass

    panel_id = _panel_message_id(context)
    if chat_id and panel_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=panel_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return
        except BadRequest:
            pass
        except Exception:
            pass

    message = await _reply(
        update,
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
    if message:
        _set_panel_message_id(context, message.message_id)


async def cleanup_add_flow_messages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    chat = update.effective_chat
    ids = list(_tracked_message_ids(context))
    clear_add_flow_cleanup(context)
    if not chat or not ids:
        return

    for message_id in ids:
        try:
            await context.bot.delete_message(chat_id=chat.id, message_id=message_id)
        except BadRequest:
            continue
        except Exception:
            continue


__all__ = [
    "clear_add_flow_cleanup",
    "reset_add_flow_cleanup",
    "track_add_flow_user_message",
    "reply_add_flow",
    "upsert_add_flow_panel",
    "cleanup_add_flow_messages",
]
