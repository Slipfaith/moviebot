"""Bot setup helpers."""

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from core.config import TELEGRAM_TOKEN
from core.offline_queue import flush_offline_entries
from bot.handlers import (
    add_command,
    find_command,
    handle_callback,
    handle_photo,
    handle_message,
    help_command,
    menu_command,
    recent_command,
    start_command,
    top_command,
)


class _PatchedApplication(Application):
    """Application subclass that re-introduces missing private slots.

    python-telegram-bot 21.2 accidentally omits the ``__stop_running_marker`` slot
    from :class:`telegram.ext.Application.__slots__`. When the base
    ``Application`` initialiser tries to assign to the attribute, Python raises
    :class:`AttributeError` because instances don't have a ``__dict__``. We work
    around the issue by providing a thin subclass that adds the missing slot and
    asking :class:`telegram.ext.ApplicationBuilder` to use it.
    """

    __slots__ = Application.__slots__ + ("_Application__stop_running_marker",)


def create_bot():
    builder = ApplicationBuilder()

    if "_Application__stop_running_marker" not in Application.__slots__:
        builder.application_class(_PatchedApplication)

    app = builder.token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("find", find_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("recent", recent_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    processed = flush_offline_entries()
    if processed:
        print(f"⬆️ Синхронизировал {processed} оффлайн-записи(ей) в таблицу.")

    return app
