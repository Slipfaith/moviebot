"""Telegram bot handlers."""

from telegram import Update
from telegram.ext import ContextTypes

from core.gsheet import add_movie_row, connect_to_sheet

HELP_TEXT = (
    "Доступные команды:\n"
    "• /add — добавить фильм пошагово\n"
    "• /help — показать эту справку\n"
    "\nТакже можно отправить строку в формате:\n"
    "Название | Год | Жанр | Оценка | Комментарий\n"
    "Комментарий можно пропустить словом 'пропустить'."
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Приветственное сообщение и краткая справка."""

    await update.message.reply_text(
        "👋 Привет! Я помогу вести таблицу фильмов.\n"
        "Используй команду /add, чтобы добавить новый фильм, или /help для справки."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Вывести справку по доступным командам."""

    await update.message.reply_text(HELP_TEXT)


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начать пошаговое добавление фильма."""

    context.user_data["add_movie"] = {"step": "film", "data": {}}
    await update.message.reply_text("🎬 Введите название фильма:")


async def _finish_movie_entry(update: Update, movie_data: dict) -> None:
    """Добавить запись в таблицу и отправить подтверждение."""

    worksheet = connect_to_sheet()
    add_movie_row(
        worksheet,
        movie_data["film"],
        movie_data["year"],
        movie_data["genre"],
        movie_data["rating"],
        movie_data.get("comment", ""),
    )

    confirmation = (
        "✅ Фильм добавлен!\n"
        f"Название: {movie_data['film']}\n"
        f"Год: {movie_data['year']}\n"
        f"Жанр: {movie_data['genre']}\n"
        f"Оценка: {movie_data['rating']}/10\n"
        f"Комментарий: {movie_data.get('comment', '—') or '—'}"
    )
    await update.message.reply_text(confirmation)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик обычных сообщений и пошагового ввода."""

    user_session = context.user_data.get("add_movie")
    message_text = (update.message.text or "").strip()

    if user_session:
        step = user_session.get("step")
        data = user_session.setdefault("data", {})

        if step == "film":
            if not message_text:
                await update.message.reply_text("Пожалуйста, укажите название фильма.")
                return

            data["film"] = message_text
            user_session["step"] = "year"
            await update.message.reply_text("📅 Введите год выхода (например, 2023):")
            return

        if step == "year":
            if not message_text.isdigit() or len(message_text) != 4:
                await update.message.reply_text("Укажите год числом из четырёх цифр.")
                return

            data["year"] = message_text
            user_session["step"] = "genre"
            await update.message.reply_text("🎭 Укажите жанр (можно несколько через запятую):")
            return

        if step == "genre":
            if not message_text:
                await update.message.reply_text("Жанр не может быть пустым. Попробуйте ещё раз.")
                return

            data["genre"] = message_text
            user_session["step"] = "rating"
            await update.message.reply_text("⭐ Введите оценку от 1 до 10:")
            return

        if step == "rating":
            normalized = message_text.replace(",", ".")
            try:
                rating_value = float(normalized)
            except ValueError:
                await update.message.reply_text("Оценка должна быть числом от 1 до 10.")
                return

            if not 1 <= rating_value <= 10:
                await update.message.reply_text("Оценка должна быть в пределах от 1 до 10.")
                return

            data["rating"] = f"{rating_value:g}"
            user_session["step"] = "comment"
            await update.message.reply_text(
                "📝 Общий комментарий (или напишите 'пропустить'):"
            )
            return

        if step == "comment":
            if message_text.lower() in {"пропустить", "skip", "-"}:
                data["comment"] = ""
            else:
                data["comment"] = message_text

            context.user_data.pop("add_movie", None)
            await _finish_movie_entry(update, data)
            return

    if "|" in message_text:
        parts = [p.strip() for p in message_text.split("|")]
        if len(parts) >= 4:
            film, year, genre, rating, *comment = parts + [""]
            worksheet = connect_to_sheet()
            add_movie_row(worksheet, film, year, genre, rating, comment[0])
            await update.message.reply_text(
                f"✅ Добавил фильм: {film} ({year}) — {rating}/10"
            )
            return

    await update.message.reply_text(
        "Не понял сообщение. Используйте /add для пошагового добавления или /help."
    )
