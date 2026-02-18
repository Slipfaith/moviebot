"""Bot setup helpers."""

from __future__ import annotations

import warnings

from telegram.ext import Application, ApplicationBuilder

from bot.handlers_registry import register_handlers
from bot.handlers_sheet_io import ensure_sheet_index_job
from bot.setup_runtime import PatchedApplication, on_error, sync_offline_entries
from core.config import TELEGRAM_TOKEN

# ConversationHandler with callback-based states works correctly in this bot.
# PTB still emits a startup warning about per_message=False, so suppress it.
warnings.filterwarnings(
    "ignore",
    message=(
        r"If 'per_message=False', 'CallbackQueryHandler' will not be tracked "
        r"for every message\..*"
    ),
    category=UserWarning,
)


def create_bot():
    builder = ApplicationBuilder()

    if "_Application__stop_running_marker" not in Application.__slots__:
        builder.application_class(PatchedApplication)
    builder.post_init(sync_offline_entries)

    app = builder.token(TELEGRAM_TOKEN).build()

    register_handlers(app)
    ensure_sheet_index_job(app)
    app.add_error_handler(on_error)

    return app
