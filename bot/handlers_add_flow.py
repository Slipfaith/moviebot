"""Add-flow facade and conversation handler wiring."""

from __future__ import annotations

import re

from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.callback_ids import (
    PATTERN_ADD_FILM,
    PATTERN_ADD_FLOW_CONFIRM_CANCEL,
    PATTERN_ADD_FLOW_CONFIRM_SAVE,
    PATTERN_ADD_FLOW_EDIT_BACK,
    PATTERN_ADD_FLOW_EDIT_OPEN,
    PATTERN_ADD_FLOW_EDIT_SET_OWNER,
    PATTERN_ADD_FLOW_EDIT_SET_REC,
    PATTERN_ADD_FLOW_EDIT_SET_TYPE,
    PATTERN_ADD_FLOW_EDIT_TEXT,
    PATTERN_ADD_FLOW_FROM_POSTER,
    PATTERN_ADD_FLOW_OWNER,
    PATTERN_ADD_FLOW_REC,
    PATTERN_ADD_FLOW_SKIP_COMMENT,
    PATTERN_ADD_FLOW_TYPE,
    PATTERN_ADD_FLOW_VOICE_CANCEL,
    PATTERN_ADD_FLOW_VOICE_CLARIFY_HINT,
)
from bot.commands import COMMAND_ADD, COMMAND_CANCEL
from bot.handlers_add_flow_steps import (
    add_command,
    add_flow_comment,
    add_flow_comment_skip,
    add_flow_confirm_cancel,
    add_flow_confirm_save,
    add_flow_film,
    add_flow_genre,
    add_flow_owner,
    add_flow_owner_select,
    add_flow_poster_edit_back,
    add_flow_poster_edit_open,
    add_flow_poster_edit_set_owner,
    add_flow_poster_edit_set_recommendation,
    add_flow_poster_edit_set_type,
    add_flow_poster_edit_text_start,
    add_flow_poster_edit_text_value,
    add_flow_rating,
    add_flow_recommendation,
    add_flow_recommendation_select,
    add_flow_type,
    add_flow_type_select,
    add_flow_year,
    cancel_add_flow,
    start_add_flow_from_poster,
    start_add_flow,
)
from bot.handlers_add_flow_voice import (
    add_flow_voice,
    add_flow_voice_cancel,
    add_flow_voice_clarify_hint,
    add_flow_voice_clarify_text,
)
from bot.handlers_add_flow_storage import _add_entry_to_sheet, _add_entry_to_sheet_sync
from bot.handlers_add_flow_ui import (
    _comment_keyboard,
    _confirm_keyboard,
    _extract_add_payload,
    _finish_add_flow,
    _owner_keyboard,
    _parse_add_payload,
    _recommendation_keyboard,
    _type_keyboard,
)
from bot.handlers_texts import (
    ADD_COMMENT,
    ADD_CONFIRM,
    ADD_FILM,
    ADD_GENRE,
    ADD_OWNER,
    ADD_POSTER_EDIT,
    ADD_POSTER_EDIT_TEXT,
    ADD_RATING,
    ADD_RECOMMENDATION,
    ADD_TYPE,
    ADD_VOICE_CLARIFY,
    ADD_YEAR,
)
from bot.interface import QUICK_BUTTON_ADD


def build_add_flow_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler(COMMAND_ADD, add_command),
            CallbackQueryHandler(start_add_flow, pattern=PATTERN_ADD_FILM),
            CallbackQueryHandler(start_add_flow_from_poster, pattern=PATTERN_ADD_FLOW_FROM_POSTER),
            MessageHandler(filters.VOICE & ~filters.COMMAND, add_flow_voice),
            MessageHandler(
                filters.Regex(rf"^{re.escape(QUICK_BUTTON_ADD)}$"),
                start_add_flow,
            ),
        ],
        states={
            ADD_FILM: [
                MessageHandler(filters.VOICE & ~filters.COMMAND, add_flow_voice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_film),
            ],
            ADD_YEAR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_year),
            ],
            ADD_GENRE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_genre),
            ],
            ADD_RATING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_rating),
            ],
            ADD_COMMENT: [
                CallbackQueryHandler(
                    add_flow_comment_skip,
                    pattern=PATTERN_ADD_FLOW_SKIP_COMMENT,
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_comment),
            ],
            ADD_TYPE: [
                CallbackQueryHandler(
                    add_flow_type_select,
                    pattern=PATTERN_ADD_FLOW_TYPE,
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_type),
            ],
            ADD_RECOMMENDATION: [
                CallbackQueryHandler(
                    add_flow_recommendation_select,
                    pattern=PATTERN_ADD_FLOW_REC,
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    add_flow_recommendation,
                ),
            ],
            ADD_OWNER: [
                CallbackQueryHandler(
                    add_flow_owner_select,
                    pattern=PATTERN_ADD_FLOW_OWNER,
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_owner),
            ],
            ADD_POSTER_EDIT: [
                CallbackQueryHandler(
                    add_flow_poster_edit_text_start,
                    pattern=PATTERN_ADD_FLOW_EDIT_TEXT,
                ),
                CallbackQueryHandler(
                    add_flow_poster_edit_open,
                    pattern=PATTERN_ADD_FLOW_EDIT_OPEN,
                ),
                CallbackQueryHandler(
                    add_flow_poster_edit_set_type,
                    pattern=PATTERN_ADD_FLOW_EDIT_SET_TYPE,
                ),
                CallbackQueryHandler(
                    add_flow_poster_edit_set_recommendation,
                    pattern=PATTERN_ADD_FLOW_EDIT_SET_REC,
                ),
                CallbackQueryHandler(
                    add_flow_poster_edit_set_owner,
                    pattern=PATTERN_ADD_FLOW_EDIT_SET_OWNER,
                ),
                CallbackQueryHandler(
                    add_flow_poster_edit_back,
                    pattern=PATTERN_ADD_FLOW_EDIT_BACK,
                ),
                CallbackQueryHandler(
                    add_flow_confirm_save,
                    pattern=PATTERN_ADD_FLOW_CONFIRM_SAVE,
                ),
                CallbackQueryHandler(
                    add_flow_confirm_cancel,
                    pattern=PATTERN_ADD_FLOW_CONFIRM_CANCEL,
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_poster_edit_text_value),
            ],
            ADD_POSTER_EDIT_TEXT: [
                CallbackQueryHandler(
                    add_flow_poster_edit_text_start,
                    pattern=PATTERN_ADD_FLOW_EDIT_TEXT,
                ),
                CallbackQueryHandler(
                    add_flow_poster_edit_open,
                    pattern=PATTERN_ADD_FLOW_EDIT_OPEN,
                ),
                CallbackQueryHandler(
                    add_flow_poster_edit_set_type,
                    pattern=PATTERN_ADD_FLOW_EDIT_SET_TYPE,
                ),
                CallbackQueryHandler(
                    add_flow_poster_edit_set_recommendation,
                    pattern=PATTERN_ADD_FLOW_EDIT_SET_REC,
                ),
                CallbackQueryHandler(
                    add_flow_poster_edit_set_owner,
                    pattern=PATTERN_ADD_FLOW_EDIT_SET_OWNER,
                ),
                CallbackQueryHandler(
                    add_flow_poster_edit_back,
                    pattern=PATTERN_ADD_FLOW_EDIT_BACK,
                ),
                CallbackQueryHandler(
                    add_flow_confirm_save,
                    pattern=PATTERN_ADD_FLOW_CONFIRM_SAVE,
                ),
                CallbackQueryHandler(
                    add_flow_confirm_cancel,
                    pattern=PATTERN_ADD_FLOW_CONFIRM_CANCEL,
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_poster_edit_text_value),
            ],
            ADD_CONFIRM: [
                CallbackQueryHandler(
                    add_flow_confirm_save,
                    pattern=PATTERN_ADD_FLOW_CONFIRM_SAVE,
                ),
                CallbackQueryHandler(
                    add_flow_confirm_cancel,
                    pattern=PATTERN_ADD_FLOW_CONFIRM_CANCEL,
                ),
            ],
            ADD_VOICE_CLARIFY: [
                CallbackQueryHandler(
                    add_flow_voice_clarify_hint,
                    pattern=PATTERN_ADD_FLOW_VOICE_CLARIFY_HINT,
                ),
                CallbackQueryHandler(
                    add_flow_voice_cancel,
                    pattern=PATTERN_ADD_FLOW_VOICE_CANCEL,
                ),
                MessageHandler(filters.VOICE & ~filters.COMMAND, add_flow_voice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_voice_clarify_text),
            ],
        },
        fallbacks=[CommandHandler(COMMAND_CANCEL, cancel_add_flow)],
        allow_reentry=True,
    )


__all__ = [
    "ADD_FILM",
    "ADD_YEAR",
    "ADD_GENRE",
    "ADD_RATING",
    "ADD_COMMENT",
    "ADD_TYPE",
    "ADD_RECOMMENDATION",
    "ADD_OWNER",
    "ADD_CONFIRM",
    "ADD_VOICE_CLARIFY",
    "ADD_POSTER_EDIT",
    "ADD_POSTER_EDIT_TEXT",
    "_extract_add_payload",
    "_parse_add_payload",
    "_add_entry_to_sheet_sync",
    "_add_entry_to_sheet",
    "_confirm_keyboard",
    "_comment_keyboard",
    "_type_keyboard",
    "_recommendation_keyboard",
    "_owner_keyboard",
    "_finish_add_flow",
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
    "add_flow_poster_edit_text_start",
    "add_flow_poster_edit_open",
    "add_flow_poster_edit_set_type",
    "add_flow_poster_edit_set_recommendation",
    "add_flow_poster_edit_set_owner",
    "add_flow_poster_edit_back",
    "add_flow_poster_edit_text_value",
    "add_flow_confirm_save",
    "add_flow_confirm_cancel",
    "cancel_add_flow",
    "add_flow_voice",
    "add_flow_voice_clarify_text",
    "add_flow_voice_clarify_hint",
    "add_flow_voice_cancel",
    "build_add_flow_handler",
]
