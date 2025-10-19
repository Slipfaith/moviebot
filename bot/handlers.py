from telegram import Update
from telegram.ext import ContextTypes
from core.gsheet import connect_to_sheet, add_movie_row

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    worksheet = connect_to_sheet()

    parts = [p.strip() for p in update.message.text.split("|")]
    if len(parts) < 5:
        await update.message.reply_text("❗ Формат: Название | Год | Жанр | Оценка | Коммент")
        return

    film, year, genre, rating, comment = parts[:5]
    add_movie_row(worksheet, film, year, genre, rating, comment)
    await update.message.reply_text(f"✅ Добавил фильм: {film} ({year}) — {rating}/10")
