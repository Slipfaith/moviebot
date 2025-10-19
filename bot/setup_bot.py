from telegram.ext import ApplicationBuilder, MessageHandler, filters
from core.config import TELEGRAM_TOKEN
from bot.handlers import handle_message

def create_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app
