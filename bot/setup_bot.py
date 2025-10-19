"""Bot setup helpers."""

from telegram.ext import Application, ApplicationBuilder, MessageHandler, filters

from core.config import TELEGRAM_TOKEN
from bot.handlers import handle_message


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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app
