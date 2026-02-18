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
    ADD_FLOW_EDIT_BACK,
    ADD_FLOW_EDIT_OPEN_OWNER,
    ADD_FLOW_EDIT_OPEN_REC,
    ADD_FLOW_EDIT_OPEN_TYPE,
    ADD_FLOW_EDIT_SET_OWNER_PREFIX,
    ADD_FLOW_EDIT_SET_REC_PREFIX,
    ADD_FLOW_EDIT_SET_TYPE_PREFIX,
    ADD_FLOW_EDIT_TEXT_PREFIX,
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
from bot.handlers_add_flow_cleanup import upsert_add_flow_panel
from bot.handlers_transport import _send
from bot.ui_texts import (
    ADD_FLOW_BTN_CONFIRM_CANCEL,
    ADD_FLOW_BTN_CONFIRM_SAVE,
    ADD_FLOW_BTN_EDIT_BACK,
    ADD_FLOW_BTN_EDIT_COMMENT,
    ADD_FLOW_BTN_EDIT_GENRE,
    ADD_FLOW_BTN_EDIT_OWNER,
    ADD_FLOW_BTN_EDIT_RATING,
    ADD_FLOW_BTN_EDIT_RECOMMENDATION,
    ADD_FLOW_BTN_EDIT_TITLE,
    ADD_FLOW_BTN_EDIT_TYPE,
    ADD_FLOW_BTN_EDIT_YEAR,
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
    ADD_FLOW_POSTER_EDITOR_NOTE_TEMPLATE,
    ADD_FLOW_POSTER_EDITOR_TEMPLATE,
    ADD_FLOW_PREVIEW_TEMPLATE,
    ADD_FLOW_SKIP_TOKENS,
    ADD_FLOW_VALUE_DASH,
    ADD_FLOW_VALUE_UNSPECIFIED,
)
from core.normalization import normalize_owner, normalize_recommendation, normalize_type

_COMMENT_SKIP_TOKENS = ADD_FLOW_SKIP_TOKENS


def _short_button_value(value: str, *, fallback: str = "—", max_len: int = 20) -> str:
    cleaned = " ".join((value or "").split()).strip()
    if not cleaned:
        return fallback
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[: max_len - 1].rstrip()}…"


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


def _poster_edit_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(ADD_FLOW_BTN_EDIT_BACK, callback_data=ADD_FLOW_EDIT_BACK)]]
    )


def _poster_edit_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    ADD_FLOW_BTN_TYPE_FILM,
                    callback_data=f"{ADD_FLOW_EDIT_SET_TYPE_PREFIX}film",
                ),
                InlineKeyboardButton(
                    ADD_FLOW_BTN_TYPE_SERIES,
                    callback_data=f"{ADD_FLOW_EDIT_SET_TYPE_PREFIX}series",
                ),
            ],
            [InlineKeyboardButton(ADD_FLOW_BTN_EDIT_BACK, callback_data=ADD_FLOW_EDIT_BACK)],
        ]
    )


def _poster_edit_recommendation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    ADD_FLOW_BTN_REC_RECOMMEND,
                    callback_data=f"{ADD_FLOW_EDIT_SET_REC_PREFIX}recommend",
                )
            ],
            [
                InlineKeyboardButton(
                    ADD_FLOW_BTN_REC_OK,
                    callback_data=f"{ADD_FLOW_EDIT_SET_REC_PREFIX}ok",
                )
            ],
            [
                InlineKeyboardButton(
                    ADD_FLOW_BTN_REC_SKIP,
                    callback_data=f"{ADD_FLOW_EDIT_SET_REC_PREFIX}skip",
                )
            ],
            [InlineKeyboardButton(ADD_FLOW_BTN_EDIT_BACK, callback_data=ADD_FLOW_EDIT_BACK)],
        ]
    )


def _poster_edit_owner_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    ADD_FLOW_BTN_OWNER_HUSBAND,
                    callback_data=f"{ADD_FLOW_EDIT_SET_OWNER_PREFIX}husband",
                ),
                InlineKeyboardButton(
                    ADD_FLOW_BTN_OWNER_WIFE,
                    callback_data=f"{ADD_FLOW_EDIT_SET_OWNER_PREFIX}wife",
                ),
            ],
            [
                InlineKeyboardButton(
                    ADD_FLOW_BTN_OWNER_SKIP,
                    callback_data=f"{ADD_FLOW_EDIT_SET_OWNER_PREFIX}skip",
                )
            ],
            [InlineKeyboardButton(ADD_FLOW_BTN_EDIT_BACK, callback_data=ADD_FLOW_EDIT_BACK)],
        ]
    )


def _poster_edit_keyboard(entry: Dict[str, str]) -> InlineKeyboardMarkup:
    film_value = _short_button_value(str(entry.get("film") or ""), fallback="название")
    year_value = _short_button_value(str(entry.get("year") or ""), fallback="год")
    genre_value = _short_button_value(str(entry.get("genre") or ""), fallback="жанр")
    rating_value = _short_button_value(str(entry.get("rating") or ""), fallback="оценка")
    comment_value = _short_button_value(str(entry.get("comment") or ""), fallback="комментарий")
    type_value = _short_button_value(str(entry.get("type") or ""), fallback="тип")
    rec_value = _short_button_value(str(entry.get("recommendation") or ""), fallback="рекомендация")
    owner_value = _short_button_value(str(entry.get("owner") or ""), fallback="владелец")
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"{ADD_FLOW_BTN_EDIT_TITLE}: {film_value}",
                    callback_data=f"{ADD_FLOW_EDIT_TEXT_PREFIX}film",
                ),
                InlineKeyboardButton(
                    f"{ADD_FLOW_BTN_EDIT_YEAR}: {year_value}",
                    callback_data=f"{ADD_FLOW_EDIT_TEXT_PREFIX}year",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{ADD_FLOW_BTN_EDIT_GENRE}: {genre_value}",
                    callback_data=f"{ADD_FLOW_EDIT_TEXT_PREFIX}genre",
                ),
                InlineKeyboardButton(
                    f"{ADD_FLOW_BTN_EDIT_RATING}: {rating_value}",
                    callback_data=f"{ADD_FLOW_EDIT_TEXT_PREFIX}rating",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{ADD_FLOW_BTN_EDIT_COMMENT}: {comment_value}",
                    callback_data=f"{ADD_FLOW_EDIT_TEXT_PREFIX}comment",
                )
            ],
            [
                InlineKeyboardButton(
                    f"{ADD_FLOW_BTN_EDIT_TYPE}: {type_value}",
                    callback_data=ADD_FLOW_EDIT_OPEN_TYPE,
                ),
                InlineKeyboardButton(
                    f"{ADD_FLOW_BTN_EDIT_RECOMMENDATION}: {rec_value}",
                    callback_data=ADD_FLOW_EDIT_OPEN_REC,
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{ADD_FLOW_BTN_EDIT_OWNER}: {owner_value}",
                    callback_data=ADD_FLOW_EDIT_OPEN_OWNER,
                )
            ],
            [
                InlineKeyboardButton(
                    ADD_FLOW_BTN_CONFIRM_SAVE,
                    callback_data=ADD_FLOW_CONFIRM_SAVE,
                ),
                InlineKeyboardButton(
                    ADD_FLOW_BTN_CONFIRM_CANCEL,
                    callback_data=ADD_FLOW_CONFIRM_CANCEL,
                ),
            ],
        ]
    )


def _poster_edit_preview(entry: Dict[str, str], *, note: str | None = None) -> str:
    rec = entry.get("recommendation") or ADD_FLOW_VALUE_DASH
    owner = entry.get("owner") or ADD_FLOW_VALUE_UNSPECIFIED
    comment = entry.get("comment") or ADD_FLOW_VALUE_DASH
    entry_type = entry.get("type") or ADD_FLOW_VALUE_DASH
    preview = ADD_FLOW_POSTER_EDITOR_TEMPLATE.format(
        film=html.escape(str(entry.get("film") or ADD_FLOW_VALUE_DASH)),
        year=html.escape(str(entry.get("year") or ADD_FLOW_VALUE_DASH)),
        genre=html.escape(str(entry.get("genre") or ADD_FLOW_VALUE_DASH)),
        rating=html.escape(str(entry.get("rating") or ADD_FLOW_VALUE_DASH)),
        entry_type=html.escape(entry_type),
        recommendation=html.escape(rec),
        owner=html.escape(owner),
        comment=html.escape(comment),
    )
    if note:
        preview += ADD_FLOW_POSTER_EDITOR_NOTE_TEMPLATE.format(note=html.escape(note))
    return preview


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
    await upsert_add_flow_panel(
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
    "_poster_edit_back_keyboard",
    "_poster_edit_type_keyboard",
    "_poster_edit_recommendation_keyboard",
    "_poster_edit_owner_keyboard",
    "_poster_edit_keyboard",
    "_poster_edit_preview",
    "_finish_add_flow",
]
