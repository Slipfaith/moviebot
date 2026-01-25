"""Bot setup helpers."""

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from core.config import TELEGRAM_TOKEN
from core.offline_queue import flush_offline_entries
from bot.handlers import (
    ADD_COMMENT,
    ADD_FILM,
    ADD_GENRE,
    ADD_OWNER,
    ADD_RATING,
    ADD_RECOMMENDATION,
    ADD_TYPE,
    ADD_YEAR,
    add_command,
    add_flow_comment,
    add_flow_comment_skip,
    add_flow_film,
    add_flow_genre,
    add_flow_owner,
    add_flow_owner_select,
    add_flow_rating,
    add_flow_recommendation,
    add_flow_recommendation_select,
    add_flow_type,
    add_flow_type_select,
    add_flow_year,
    cancel_add_flow,
    find_command,
    handle_callback,
    handle_photo,
    handle_message,
    help_command,
    list_command,
    menu_command,
    owner_command,
    random_command,
    recent_command,
    start_command,
    start_add_flow,
    stats_command,
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
    add_flow_handler = ConversationHandler(
        entry_points=[
            CommandHandler("add", add_command),
            CallbackQueryHandler(start_add_flow, pattern="^add_film$"),
        ],
        states={
            ADD_FILM: [
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
                CallbackQueryHandler(add_flow_comment_skip, pattern="^add_flow:skip_comment$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_comment),
            ],
            ADD_TYPE: [
                CallbackQueryHandler(add_flow_type_select, pattern="^add_flow:type:(film|series)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_type),
            ],
            ADD_RECOMMENDATION: [
                CallbackQueryHandler(add_flow_recommendation_select, pattern="^add_flow:rec:(recommend|ok|skip)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_recommendation),
            ],
            ADD_OWNER: [
                CallbackQueryHandler(add_flow_owner_select, pattern="^add_flow:owner:(husband|wife|skip)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_owner),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_add_flow)],
        allow_reentry=True,
    )
    app.add_handler(add_flow_handler)
    app.add_handler(CommandHandler("find", find_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("random", random_command))
    app.add_handler(CommandHandler("owner", owner_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("recent", recent_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    processed = flush_offline_entries()
    if processed:
        print(f"⬆️ Синхронизировал {processed} оффлайн-записи(ей) в таблицу.")

    return app
