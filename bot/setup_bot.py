"""Bot setup helpers."""

import asyncio
import re
import warnings

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.handlers import (
    ADD_COMMENT,
    ADD_CONFIRM,
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
    add_flow_confirm_cancel,
    add_flow_confirm_save,
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
    ai_command,
    cancel_add_flow,
    find_command,
    handle_callback,
    handle_message,
    handle_photo,
    help_command,
    list_command,
    menu_command,
    owner_command,
    random_command,
    recent_command,
    recommend_command,
    search_command,
    start_add_flow,
    start_command,
    stats_command,
    top_command,
    winner_command,
)
from bot.interface import QUICK_BUTTON_ADD
from core.config import TELEGRAM_TOKEN
from core.offline_queue import flush_offline_entries

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


async def _sync_offline_entries(app: Application) -> None:
    result = await asyncio.to_thread(flush_offline_entries)
    if result.error:
        print("GSHEET ERROR:", type(result.error).__name__, result.error)
    if result.processed:
        print(f"⬆️ Синхронизировал {result.processed} оффлайн-записи(ей) в таблицу.")
        if result.chat_ids:
            for chat_id in result.chat_ids:
                try:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            "✅ Оффлайн-записи синхронизированы: "
                            f"{result.processed} добавлено в таблицу."
                        ),
                    )
                except Exception as exc:
                    print("TELEGRAM ERROR:", type(exc).__name__, exc)


async def _on_error(update, context) -> None:
    error = getattr(context, "error", None)
    print("BOT ERROR:", type(error).__name__, error)

    if update and getattr(update, "effective_message", None):
        try:
            await update.effective_message.reply_text(
                "Произошла временная ошибка. Попробуйте ещё раз."
            )
        except Exception:
            pass


def create_bot():
    builder = ApplicationBuilder()

    if "_Application__stop_running_marker" not in Application.__slots__:
        builder.application_class(_PatchedApplication)
    builder.post_init(_sync_offline_entries)

    app = builder.token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("ai", ai_command))
    app.add_handler(CommandHandler("recommend", recommend_command))

    add_flow_handler = ConversationHandler(
        entry_points=[
            CommandHandler("add", add_command),
            CallbackQueryHandler(start_add_flow, pattern="^add_film$"),
            MessageHandler(
                filters.Regex(rf"^{re.escape(QUICK_BUTTON_ADD)}$"),
                start_add_flow,
            ),
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
                CallbackQueryHandler(
                    add_flow_comment_skip,
                    pattern="^add_flow:skip_comment$",
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_comment),
            ],
            ADD_TYPE: [
                CallbackQueryHandler(
                    add_flow_type_select,
                    pattern="^add_flow:type:(film|series)$",
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_type),
            ],
            ADD_RECOMMENDATION: [
                CallbackQueryHandler(
                    add_flow_recommendation_select,
                    pattern="^add_flow:rec:(recommend|ok|skip)$",
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    add_flow_recommendation,
                ),
            ],
            ADD_OWNER: [
                CallbackQueryHandler(
                    add_flow_owner_select,
                    pattern="^add_flow:owner:(husband|wife|skip)$",
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_flow_owner),
            ],
            ADD_CONFIRM: [
                CallbackQueryHandler(
                    add_flow_confirm_save,
                    pattern="^add_flow:confirm:save$",
                ),
                CallbackQueryHandler(
                    add_flow_confirm_cancel,
                    pattern="^add_flow:confirm:cancel$",
                ),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_add_flow)],
        allow_reentry=True,
    )
    app.add_handler(add_flow_handler)

    app.add_handler(CommandHandler("find", find_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("winner", winner_command))
    app.add_handler(CommandHandler("random", random_command))
    app.add_handler(CommandHandler("owner", owner_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("recent", recent_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(_on_error)

    return app
