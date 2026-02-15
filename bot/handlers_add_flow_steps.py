"""Conversation step handlers for add-flow."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.commands import COMMAND_ADD, slash
from bot.handlers_add_flow_cleanup import (
    cleanup_add_flow_messages,
    clear_add_flow_cleanup,
    reply_add_flow,
    reset_add_flow_cleanup,
    track_add_flow_user_message,
)
from bot.handlers_add_flow_storage import _add_entry_to_sheet
from bot.handlers_add_flow_ui import (
    _COMMENT_SKIP_TOKENS,
    _comment_keyboard,
    _extract_add_payload,
    _finish_add_flow,
    _owner_keyboard,
    _parse_add_payload,
    _recommendation_keyboard,
    _type_keyboard,
)
from bot.handlers_cache import _invalidate_response_cache
from bot.handlers_texts import (
    ADD_COMMENT,
    ADD_FILM,
    ADD_GENRE,
    ADD_OWNER,
    ADD_RATING,
    ADD_RECOMMENDATION,
    ADD_TYPE,
    ADD_USAGE_TEXT,
    ADD_YEAR,
)
from bot.handlers_transport import _send
from bot.interface import get_quick_actions_keyboard
from bot.ui_texts import (
    ADD_FLOW_ERROR_INVALID_DATA,
    ADD_FLOW_ERROR_MISSING_ENTRY_TEMPLATE,
    ADD_FLOW_ERROR_PARSE_FAILED,
    ADD_FLOW_MSG_CANCELLED,
    ADD_FLOW_MSG_OFFLINE_SAVED,
    ADD_FLOW_MSG_SAVED_TEMPLATE,
    ADD_FLOW_PROMPT_COMMENT,
    ADD_FLOW_PROMPT_GENRE,
    ADD_FLOW_PROMPT_GENRE_INVALID,
    ADD_FLOW_PROMPT_OWNER,
    ADD_FLOW_PROMPT_RATING,
    ADD_FLOW_PROMPT_RATING_INVALID,
    ADD_FLOW_PROMPT_RECOMMENDATION,
    ADD_FLOW_PROMPT_TITLE,
    ADD_FLOW_PROMPT_TYPE,
    ADD_FLOW_PROMPT_YEAR,
    ADD_FLOW_PROMPT_YEAR_INVALID,
    PHOTO_MSG_PREFILL_EXPIRED,
)
from core.normalization import normalize_owner, normalize_recommendation, normalize_type
from core.offline_queue import add_offline_entry

logger = logging.getLogger(__name__)

_PHOTO_PREFILL_KEY = "photo_add_entry"


def _has_valid_year(value: str) -> bool:
    return value.isdigit() and len(value) == 4


def _has_valid_rating(value: str) -> bool:
    try:
        rating = float((value or "").replace(",", "."))
    except ValueError:
        return False
    return 1 <= rating <= 10


async def _continue_prefilled_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    entry = context.user_data.get("add_flow", {})

    if not (entry.get("film") or "").strip():
        await reply_add_flow(update, context, ADD_FLOW_PROMPT_TITLE)
        return ADD_FILM
    if not _has_valid_year((entry.get("year") or "").strip()):
        await reply_add_flow(update, context, ADD_FLOW_PROMPT_YEAR)
        return ADD_YEAR
    if not (entry.get("genre") or "").strip():
        await reply_add_flow(update, context, ADD_FLOW_PROMPT_GENRE)
        return ADD_GENRE
    if not _has_valid_rating((entry.get("rating") or "").strip()):
        await reply_add_flow(update, context, ADD_FLOW_PROMPT_RATING)
        return ADD_RATING

    if not (entry.get("comment") or "").strip():
        await reply_add_flow(
            update,
            context,
            ADD_FLOW_PROMPT_COMMENT,
            reply_markup=_comment_keyboard(),
        )
        return ADD_COMMENT
    if not (entry.get("type") or "").strip():
        await reply_add_flow(
            update,
            context,
            ADD_FLOW_PROMPT_TYPE,
            reply_markup=_type_keyboard(),
        )
        return ADD_TYPE
    if not (entry.get("recommendation") or "").strip():
        await reply_add_flow(
            update,
            context,
            ADD_FLOW_PROMPT_RECOMMENDATION,
            reply_markup=_recommendation_keyboard(),
        )
        return ADD_RECOMMENDATION
    if not (entry.get("owner") or "").strip():
        await reply_add_flow(
            update,
            context,
            ADD_FLOW_PROMPT_OWNER,
            reply_markup=_owner_keyboard(),
        )
        return ADD_OWNER

    return await _finish_add_flow(update, context)


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reset_add_flow_cleanup(update, context)
    payload = _extract_add_payload(update, context)
    if not payload:
        context.user_data["add_flow"] = {}
        await reply_add_flow(update, context, ADD_FLOW_PROMPT_TITLE)
        return ADD_FILM

    try:
        entry = _parse_add_payload(payload)
    except ValueError as exc:
        if str(exc) in {"missing_fields", "invalid_year", "invalid_rating"}:
            await _send(update, f"{ADD_FLOW_ERROR_INVALID_DATA}\n\n{ADD_USAGE_TEXT}")
        else:
            await _send(update, ADD_FLOW_ERROR_PARSE_FAILED)
        clear_add_flow_cleanup(context)
        return ConversationHandler.END

    context.user_data["add_flow"] = entry
    return await _finish_add_flow(update, context)


async def start_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reset_add_flow_cleanup(update, context)
    context.user_data["add_flow"] = {}
    await reply_add_flow(update, context, ADD_FLOW_PROMPT_TITLE)
    return ADD_FILM


async def start_add_flow_from_poster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    reset_add_flow_cleanup(update, context)
    prefill = context.user_data.get(_PHOTO_PREFILL_KEY)
    if not isinstance(prefill, dict):
        clear_add_flow_cleanup(context)
        await _send(update, PHOTO_MSG_PREFILL_EXPIRED)
        return ConversationHandler.END
    context.user_data["add_flow"] = dict(prefill)
    return await _continue_prefilled_add_flow(update, context)


async def add_flow_film(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    track_add_flow_user_message(update, context)
    film = (update.message.text or "").strip()
    if not film:
        await reply_add_flow(update, context, ADD_FLOW_PROMPT_TITLE)
        return ADD_FILM
    context.user_data["add_flow"] = {"film": film}
    await reply_add_flow(update, context, ADD_FLOW_PROMPT_YEAR)
    return ADD_YEAR


async def add_flow_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    track_add_flow_user_message(update, context)
    year = (update.message.text or "").strip()
    if not _has_valid_year(year):
        await reply_add_flow(update, context, ADD_FLOW_PROMPT_YEAR_INVALID)
        return ADD_YEAR
    context.user_data["add_flow"]["year"] = year
    await reply_add_flow(update, context, ADD_FLOW_PROMPT_GENRE)
    return ADD_GENRE


async def add_flow_genre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    track_add_flow_user_message(update, context)
    genre = (update.message.text or "").strip()
    if not genre:
        await reply_add_flow(update, context, ADD_FLOW_PROMPT_GENRE_INVALID)
        return ADD_GENRE
    context.user_data["add_flow"]["genre"] = genre
    await reply_add_flow(update, context, ADD_FLOW_PROMPT_RATING)
    return ADD_RATING


async def add_flow_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    track_add_flow_user_message(update, context)
    rating_raw = (update.message.text or "").strip()
    try:
        rating_value = float(rating_raw.replace(",", "."))
    except ValueError:
        rating_value = 0
    if not (1 <= rating_value <= 10):
        await reply_add_flow(update, context, ADD_FLOW_PROMPT_RATING_INVALID)
        return ADD_RATING
    context.user_data["add_flow"]["rating"] = f"{rating_value:g}"
    await reply_add_flow(
        update,
        context,
        ADD_FLOW_PROMPT_COMMENT,
        reply_markup=_comment_keyboard(),
    )
    return ADD_COMMENT


async def add_flow_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    track_add_flow_user_message(update, context)
    comment = (update.message.text or "").strip()
    if comment.lower() in _COMMENT_SKIP_TOKENS:
        comment = ""
    context.user_data["add_flow"]["comment"] = comment
    await reply_add_flow(update, context, ADD_FLOW_PROMPT_TYPE, reply_markup=_type_keyboard())
    return ADD_TYPE


async def add_flow_comment_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    context.user_data["add_flow"]["comment"] = ""
    await reply_add_flow(update, context, ADD_FLOW_PROMPT_TYPE, reply_markup=_type_keyboard())
    return ADD_TYPE


async def add_flow_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    track_add_flow_user_message(update, context)
    entry_type = (update.message.text or "").strip()
    context.user_data["add_flow"]["type"] = normalize_type(entry_type)
    await reply_add_flow(
        update,
        context,
        ADD_FLOW_PROMPT_RECOMMENDATION,
        reply_markup=_recommendation_keyboard(),
    )
    return ADD_RECOMMENDATION


async def add_flow_type_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    choice = update.callback_query.data.rsplit(":", 1)[-1]
    context.user_data["add_flow"]["type"] = normalize_type(choice)
    await reply_add_flow(
        update,
        context,
        ADD_FLOW_PROMPT_RECOMMENDATION,
        reply_markup=_recommendation_keyboard(),
    )
    return ADD_RECOMMENDATION


async def add_flow_recommendation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    track_add_flow_user_message(update, context)
    recommendation = (update.message.text or "").strip()
    context.user_data["add_flow"]["recommendation"] = normalize_recommendation(recommendation)
    await reply_add_flow(update, context, ADD_FLOW_PROMPT_OWNER, reply_markup=_owner_keyboard())
    return ADD_OWNER


async def add_flow_recommendation_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    choice = update.callback_query.data.rsplit(":", 1)[-1]
    context.user_data["add_flow"]["recommendation"] = normalize_recommendation(choice)
    await reply_add_flow(update, context, ADD_FLOW_PROMPT_OWNER, reply_markup=_owner_keyboard())
    return ADD_OWNER


async def add_flow_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    track_add_flow_user_message(update, context)
    owner = normalize_owner((update.message.text or "").strip())
    context.user_data["add_flow"]["owner"] = owner
    return await _finish_add_flow(update, context)


async def add_flow_owner_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    choice = update.callback_query.data.rsplit(":", 1)[-1]
    context.user_data["add_flow"]["owner"] = normalize_owner(choice)
    return await _finish_add_flow(update, context)


async def add_flow_confirm_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    entry = context.user_data.get("add_flow", {})
    if not entry:
        clear_add_flow_cleanup(context)
        await _send(
            update,
            ADD_FLOW_ERROR_MISSING_ENTRY_TEMPLATE.format(add_command=slash(COMMAND_ADD)),
        )
        return ConversationHandler.END

    error = await _add_entry_to_sheet(entry)
    if error:
        logger.error("GSHEET ERROR: %s %s", type(error).__name__, error)
        if update.effective_chat:
            entry["chat_id"] = update.effective_chat.id
        add_offline_entry(entry)
        clear_add_flow_cleanup(context)
        await _send(update, ADD_FLOW_MSG_OFFLINE_SAVED)
        context.user_data.pop("add_flow", None)
        return ConversationHandler.END

    _invalidate_response_cache()
    film = str(entry.get("film") or "Фильм")
    await cleanup_add_flow_messages(update, context)
    context.user_data.pop("add_flow", None)
    if update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=ADD_FLOW_MSG_SAVED_TEMPLATE.format(film=film),
            reply_markup=get_quick_actions_keyboard(),
        )
    else:
        await _send(update, ADD_FLOW_MSG_SAVED_TEMPLATE.format(film=film))
    return ConversationHandler.END


async def add_flow_confirm_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    context.user_data.pop("add_flow", None)
    clear_add_flow_cleanup(context)
    await _send(update, ADD_FLOW_MSG_CANCELLED)
    return ConversationHandler.END


async def cancel_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("add_flow", None)
    clear_add_flow_cleanup(context)
    await _send(update, ADD_FLOW_MSG_CANCELLED)
    return ConversationHandler.END


__all__ = [
    "add_command",
    "start_add_flow",
    "start_add_flow_from_poster",
    "add_flow_film",
    "add_flow_year",
    "add_flow_genre",
    "add_flow_rating",
    "add_flow_comment",
    "add_flow_comment_skip",
    "add_flow_type",
    "add_flow_type_select",
    "add_flow_recommendation",
    "add_flow_recommendation_select",
    "add_flow_owner",
    "add_flow_owner_select",
    "add_flow_confirm_save",
    "add_flow_confirm_cancel",
    "cancel_add_flow",
]
