"""UI, parsing, and preview helpers for add-flow handlers."""

from __future__ import annotations

import html
from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from bot.commands import COMMAND_ADD, slash
from bot.callback_ids import (
    ADD_FLOW_CONFIRM_CANCEL,
    ADD_FLOW_CONFIRM_SAVE,
    ADD_FLOW_OWNER_HUSBAND,
    ADD_FLOW_OWNER_SKIP,
    ADD_FLOW_OWNER_WIFE,
    ADD_FLOW_REC_OK,
    ADD_FLOW_REC_RECOMMEND,
    ADD_FLOW_REC_SKIP,
    ADD_FLOW_SKIP_COMMENT,
    ADD_FLOW_TYPE_FILM,
    ADD_FLOW_TYPE_SERIES,
)
from bot.handlers_texts import (
    ADD_CONFIRM,
)
from bot.handlers_add_flow_cleanup import reply_add_flow
from bot.handlers_transport import _send
from bot.ui_texts import (
    ADD_FLOW_BTN_CONFIRM_CANCEL,
    ADD_FLOW_BTN_CONFIRM_SAVE,
    ADD_FLOW_BTN_OWNER_HUSBAND,
    ADD_FLOW_BTN_OWNER_SKIP,
    ADD_FLOW_BTN_OWNER_WIFE,
    ADD_FLOW_BTN_REC_OK,
    ADD_FLOW_BTN_REC_RECOMMEND,
    ADD_FLOW_BTN_REC_SKIP,
    ADD_FLOW_BTN_SKIP_COMMENT,
    ADD_FLOW_BTN_TYPE_FILM,
    ADD_FLOW_BTN_TYPE_SERIES,
    ADD_FLOW_ERROR_BUILD_FAILED_TEMPLATE,
    ADD_FLOW_PREVIEW_TEMPLATE,
    ADD_FLOW_SKIP_TOKENS,
    ADD_FLOW_VALUE_DASH,
    ADD_FLOW_VALUE_UNSPECIFIED,
)
from core.normalization import normalize_owner, normalize_recommendation, normalize_type

_COMMENT_SKIP_TOKENS = ADD_FLOW_SKIP_TOKENS


def _extract_add_payload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if context.args:
        return " ".join(context.args).strip()
    if update.message and update.message.text:
        text = update.message.text
        if text.startswith(slash(COMMAND_ADD)):
            return text.partition(" ")[2].strip()
    return ""


def _parse_add_payload(payload: str) -> Dict[str, str]:
    parts = [part.strip() for part in payload.split(";")]
    if len(parts) < 4:
        raise ValueError("missing_fields")

    if len(parts) > 8:
        comment = ";".join(parts[4:-3]).strip()
        parts = parts[:4] + [comment] + parts[-3:]

    while len(parts) < 8:
        parts.append("")

    film, year, genre, rating, comment, entry_type, recommendation, owner = parts[:8]

    if not film or not year or not genre or not rating:
        raise ValueError("missing_fields")
    if not (year.isdigit() and len(year) == 4):
        raise ValueError("invalid_year")
    try:
        rating_value = float(rating.replace(",", "."))
    except ValueError as exc:
        raise ValueError("invalid_rating") from exc
    if not (1 <= rating_value <= 10):
        raise ValueError("invalid_rating")

    return {
        "film": film,
        "year": year,
        "genre": genre,
        "rating": f"{rating_value:g}",
        "comment": comment,
        "type": normalize_type(entry_type),
        "recommendation": normalize_recommendation(recommendation),
        "owner": normalize_owner(owner),
    }


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(ADD_FLOW_BTN_CONFIRM_SAVE, callback_data=ADD_FLOW_CONFIRM_SAVE),
            InlineKeyboardButton(ADD_FLOW_BTN_CONFIRM_CANCEL, callback_data=ADD_FLOW_CONFIRM_CANCEL),
        ]]
    )


def _comment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(ADD_FLOW_BTN_SKIP_COMMENT, callback_data=ADD_FLOW_SKIP_COMMENT)]]
    )


def _type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(ADD_FLOW_BTN_TYPE_FILM, callback_data=ADD_FLOW_TYPE_FILM),
            InlineKeyboardButton(ADD_FLOW_BTN_TYPE_SERIES, callback_data=ADD_FLOW_TYPE_SERIES),
        ]]
    )


def _recommendation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(ADD_FLOW_BTN_REC_RECOMMEND, callback_data=ADD_FLOW_REC_RECOMMEND)],
            [InlineKeyboardButton(ADD_FLOW_BTN_REC_OK, callback_data=ADD_FLOW_REC_OK)],
            [InlineKeyboardButton(ADD_FLOW_BTN_REC_SKIP, callback_data=ADD_FLOW_REC_SKIP)],
        ]
    )


def _owner_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(ADD_FLOW_BTN_OWNER_HUSBAND, callback_data=ADD_FLOW_OWNER_HUSBAND),
                InlineKeyboardButton(ADD_FLOW_BTN_OWNER_WIFE, callback_data=ADD_FLOW_OWNER_WIFE),
            ],
            [InlineKeyboardButton(ADD_FLOW_BTN_OWNER_SKIP, callback_data=ADD_FLOW_OWNER_SKIP)],
        ]
    )


async def _finish_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    entry = context.user_data.get("add_flow", {})
    required = ["film", "year", "genre", "rating"]
    if not all(entry.get(key) for key in required):
        await _send(
            update,
            ADD_FLOW_ERROR_BUILD_FAILED_TEMPLATE.format(add_command=slash(COMMAND_ADD)),
        )
        context.user_data.pop("add_flow", None)
        return ConversationHandler.END

    rec = entry.get("recommendation") or ADD_FLOW_VALUE_DASH
    owner = entry.get("owner") or ADD_FLOW_VALUE_UNSPECIFIED
    comment = entry.get("comment") or ADD_FLOW_VALUE_DASH
    entry_type = entry.get("type") or ADD_FLOW_VALUE_DASH

    preview = ADD_FLOW_PREVIEW_TEMPLATE.format(
        film=html.escape(entry["film"]),
        year=html.escape(entry["year"]),
        genre=html.escape(entry["genre"]),
        rating=html.escape(entry["rating"]),
        entry_type=html.escape(entry_type),
        recommendation=html.escape(rec),
        owner=html.escape(owner),
        comment=html.escape(comment),
    )
    await reply_add_flow(
        update,
        context,
        preview,
        reply_markup=_confirm_keyboard(),
        parse_mode=ParseMode.HTML,
    )
    return ADD_CONFIRM


__all__ = [
    "_COMMENT_SKIP_TOKENS",
    "_extract_add_payload",
    "_parse_add_payload",
    "_confirm_keyboard",
    "_comment_keyboard",
    "_type_keyboard",
    "_recommendation_keyboard",
    "_owner_keyboard",
    "_finish_add_flow",
]
