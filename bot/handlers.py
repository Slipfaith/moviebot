"""Telegram bot handlers."""

from io import BytesIO
from typing import Dict, Iterable, List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from core.gsheet import (
    add_movie_row,
    connect_to_sheet,
    fetch_records,
    filter_by_genre,
    recent_entries,
    top_by_rating,
)
from core.normalization import (
    normalize_owner,
    normalize_recommendation,
    normalize_type,
)
from bot.interface import get_main_menu
from ocr import get_default_ocr


poster_ocr = get_default_ocr()

HELP_TEXT = (
    "Доступные команды:\n"
    "• /add — добавить фильм пошагово\n"
    "• /help — показать эту справку\n"
    "• /menu — открыть главное меню\n"
    "• /find жанр=<жанр> — найти фильмы по жанру\n"
    "• /top n=<число> — топ фильмов по оценке\n"
    "• /recent — что добавлено за последний месяц\n"
    "\nЕсли бот временно оффлайн, вы всё равно можете отправить сообщение вида:\n"
    "Название\nГод\nЖанр\nОценка\nКомментарий\nТип\nРеки\n"
    "Когда бот вернётся онлайн, он обработает такие записи автоматически.\n"
    "Комментарий можно пропустить словом 'пропустить'.\n"
    "Реки — одна из опций: рекомендую, можно посмотреть, в топку."
)

OFFLINE_GUIDE_TEXT = (
    "📥 Офлайн добавление записей:\n\n"
    "1. Отправьте сообщение в чат даже если бот оффлайн.\n"
    "2. Используйте формат из семи строк:\n"
    "   Название\n   Год\n   Жанр\n   Оценка\n   Комментарий\n   Тип\n   Реки\n"
    "3. Комментарий можно пропустить словом 'пропустить'.\n"
    "4. Тип — фильм или сериал.\n"
    "5. Рекомендация: рекомендую, можно посмотреть, в топку.\n\n"
    "Сообщение дождётся бота и будет добавлено в таблицу при следующем запуске."
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Приветственное сообщение и краткая справка."""

    await update.message.reply_text(
        "👋 Привет! Я помогу вести таблицу фильмов.\n"
        "Используй /menu или кнопки ниже, чтобы управлять подборкой.",
        reply_markup=get_main_menu(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Вывести справку по доступным командам."""

    await update.message.reply_text(HELP_TEXT, reply_markup=get_main_menu())


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Открыть главное меню с подсказками."""

    await update.message.reply_text(
        "Главное меню доступно в любой момент:", reply_markup=get_main_menu()
    )


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начать пошаговое добавление фильма."""

    context.user_data["add_movie"] = {"step": "film", "data": {}}
    await update.effective_chat.send_message("🎬 Введите название фильма:")


def _format_entry(row: Dict[str, str]) -> str:
    """Return short human readable description of a movie entry."""

    name = row.get("Название") or row.get("Film") or row.get("Фильм") or "—"
    year = row.get("Год") or row.get("Year") or "—"
    rating = row.get("Оценка") or row.get("Rating") or "—"
    entry_type = row.get("Тип") or row.get("Type") or "фильм"
    entry_type = normalize_type(entry_type)
    genre = row.get("Жанр") or row.get("Genre") or "—"
    recommendation = (
        row.get("Реки")
        or row.get("Рекомендация")
        or row.get("Recommendation")
        or "—"
    )
    owner = row.get("Чье") or row.get("Owner") or ""
    owner_part = f" • нашёл: {owner}" if owner else ""
    return (
        f"{name} ({year}) — {rating}/10 • {entry_type} • {genre} • {recommendation}" + owner_part
    )


def _normalize_rating_text(value: str) -> str:
    normalized = value.replace(",", ".")
    try:
        return f"{float(normalized):g}"
    except ValueError:
        return value


def _parse_offline_submission(message_text: str) -> Optional[Dict[str, str]]:
    lines = [line.strip() for line in message_text.splitlines() if line.strip()]
    if len(lines) >= 7:
        film, year, genre, rating, comment, entry_type, recommendation, *rest = lines + [""]
        if comment.lower() in {"пропустить", "skip", "-"}:
            comment = ""
        owner = normalize_owner(rest[0]) if rest else ""
        return {
            "film": film,
            "year": year,
            "genre": genre,
            "rating": _normalize_rating_text(rating),
            "comment": comment,
            "type": normalize_type(entry_type),
            "recommendation": normalize_recommendation(recommendation),
            "owner": owner,
        }

    if "|" in message_text:
        parts = [p.strip() for p in message_text.split("|")]
        if len(parts) >= 4:
            film, year, genre, rating, *rest = parts + ["", "", "", ""]
            comment = rest[0] if rest else ""
            if comment.lower() in {"пропустить", "skip", "-"}:
                comment = ""
            entry_type = normalize_type(rest[1] if len(rest) > 1 else "фильм")
            recommendation = normalize_recommendation(rest[2] if len(rest) > 2 else "")
            owner = normalize_owner(rest[3] if len(rest) > 3 else "")
            return {
                "film": film,
                "year": year,
                "genre": genre,
                "rating": _normalize_rating_text(rating),
                "comment": comment,
                "type": entry_type,
                "recommendation": recommendation,
                "owner": owner,
            }

    return None


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
        normalize_type(movie_data.get("type", "фильм")),
        normalize_recommendation(movie_data.get("recommendation", "можно посмотреть")),
        normalize_owner(movie_data.get("owner")),
    )

    confirmation = (
        "✅ Фильм добавлен!\n"
        f"Название: {movie_data['film']}\n"
        f"Год: {movie_data['year']}\n"
        f"Жанр: {movie_data['genre']}\n"
        f"Оценка: {movie_data['rating']}/10\n"
        f"Тип: {normalize_type(movie_data.get('type', 'фильм'))}\n"
        f"Комментарий: {movie_data.get('comment', '—') or '—'}\n"
        f"Рекомендация: {normalize_recommendation(movie_data.get('recommendation'))}\n"
        f"Чьё: {normalize_owner(movie_data.get('owner')) or '—'}"
    )
    await update.effective_chat.send_message(confirmation, reply_markup=get_main_menu())


def _type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎞️ Фильм", callback_data="type:фильм"),
                InlineKeyboardButton("📺 Сериал", callback_data="type:сериал"),
            ]
        ]
    )


def _recommendation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔥 Рекомендую", callback_data="recommendation:рекомендую")],
            [
                InlineKeyboardButton(
                    "🙂 Можно посмотреть", callback_data="recommendation:можно посмотреть"
                )
            ],
            [InlineKeyboardButton("🗑 В топку", callback_data="recommendation:в топку")],
        ]
    )


def _skip_keyboard(step: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⏭ Пропустить", callback_data=f"skip:{step}")]]
    )


def _comment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⏭ Пропустить комментарий", callback_data="skip:comment")]]
    )


def _owner_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("👨 Муж", callback_data="owner:муж")],
            [InlineKeyboardButton("👩 Жена", callback_data="owner:жена")],
            [InlineKeyboardButton("⏭ Пропустить", callback_data="owner:")],
        ]
    )


async def _handle_find_command(
    update: Update, records: Iterable[Dict[str, str]], genre: str
) -> None:
    matches = filter_by_genre(records, genre)
    if not matches:
        await update.message.reply_text(
            "Ничего не нашёл по указанному жанру. Попробуйте уточнить запрос."
        )
        return

    lines = ["🎭 Найденные записи:"]
    for row in matches[:10]:
        lines.append(_format_entry(row))
    if len(matches) > 10:
        lines.append(f"… и ещё {len(matches) - 10}")
    await update.message.reply_text("\n".join(lines))


async def _handle_top_command(
    update: Update, records: Iterable[Dict[str, str]], amount: int
) -> None:
    top_rows = top_by_rating(records, amount)
    if not top_rows:
        await update.message.reply_text("В таблице нет записей для формирования рейтинга.")
        return

    lines = ["📊 Топ по оценкам:"]
    for idx, row in enumerate(top_rows, start=1):
        lines.append(f"{idx}. {_format_entry(row)}")
    await update.message.reply_text("\n".join(lines))


async def _handle_recent_command(
    update: Update, records: Iterable[Dict[str, str]], days: int = 30
) -> None:
    last_rows = recent_entries(records, days)
    if not last_rows:
        await update.message.reply_text(
            "За последний месяц вы не добавляли новых записей."
        )
        return

    lines = ["🗓 За последние 30 дней:"]
    for row in last_rows[:10]:
        timestamp = (
            row.get("Добавлено")
            or row.get("Timestamp")
            or row.get("Дата")
            or row.get("Added")
        )
        lines.append(f"{timestamp}: {_format_entry(row)}")
    if len(last_rows) > 10:
        lines.append(f"… и ещё {len(last_rows) - 10}")
    await update.message.reply_text("\n".join(lines))


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Extract a movie title from a poster photo using OCR."""

    if not update.message or not update.message.photo:
        return

    photo = update.message.photo[-1]
    try:
        telegram_file = await photo.get_file()
        buffer = BytesIO()
        await telegram_file.download_to_memory(buffer)
    except Exception:  # pragma: no cover - network errors are rare
        if context.application and context.application.logger:
            context.application.logger.exception("Failed to download photo for OCR")
        await update.message.reply_text(
            "Не получилось скачать изображение. Попробуйте отправить его ещё раз."
        )
        return

    candidates: List[str] = poster_ocr.extract_candidates(buffer.getvalue())
    if not candidates:
        await update.message.reply_text(
            "Я не смог разобрать название на постере. Попробуйте более чёткое фото."
        )
        return

    best_guess = candidates[0]
    context.user_data["add_movie"] = {"step": "year", "data": {"film": best_guess}}

    extra = ""
    if len(candidates) > 1:
        extra = "\n\nДругие варианты: " + ", ".join(f"«{item}»" for item in candidates[1:3])

    await update.message.reply_text(
        (
            f"📷 Похоже, это «{best_guess}».\n"
            "Я сохранил название. Теперь укажите год выхода (например, 2023)."
            + extra
        ),
        reply_markup=_skip_keyboard("year"),
    )


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
            await update.message.reply_text(
                "📅 Введите год выхода (например, 2023):",
                reply_markup=_skip_keyboard("year"),
            )
            return

        if step == "year":
            if not message_text.isdigit() or len(message_text) != 4:
                await update.message.reply_text(
                    "Укажите год числом из четырёх цифр.", reply_markup=_skip_keyboard("year")
                )
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
                "📝 Общий комментарий (или нажмите кнопку 'Пропустить'):",
                reply_markup=_comment_keyboard(),
            )
            return

        if step == "comment":
            if message_text.lower() in {"пропустить", "skip", "-"}:
                data["comment"] = ""
            else:
                data["comment"] = message_text

            user_session["step"] = "type"
            await update.message.reply_text(
                "Что вы добавляете?", reply_markup=_type_keyboard()
            )
            return

        if step == "type":
            await update.message.reply_text(
                "Пожалуйста, выберите тип с помощью кнопок ниже.",
                reply_markup=_type_keyboard(),
            )
            return

        if step == "recommendation":
            await update.message.reply_text(
                "Выберите рекомендацию с помощью кнопок ниже.",
                reply_markup=_recommendation_keyboard(),
            )
            return
        if step == "owner":
            await update.message.reply_text(
                "Выберите, кто нашёл фильм, с помощью кнопок ниже.",
                reply_markup=_owner_keyboard(),
            )
            return

    submission = _parse_offline_submission(message_text)
    if submission:
        worksheet = connect_to_sheet()
        add_movie_row(
            worksheet,
            submission["film"],
            submission["year"],
            submission["genre"],
            submission["rating"],
            submission["comment"],
            submission["type"],
            submission["recommendation"],
            submission["owner"],
        )
        owner_note = (
            f"\nЧьё: {submission['owner']}" if submission.get("owner") else ""
        )
        await update.message.reply_text(
            f"✅ Добавил фильм: {submission['film']} ({submission['year']}) — {submission['rating']}/10"
            + owner_note
        )
        return

    lowered = message_text.lower()
    if "покажи" in lowered and "месяц" in lowered:
        worksheet = connect_to_sheet()
        records = fetch_records(worksheet)
        await _handle_recent_command(update, records)
        return

    await update.message.reply_text(
        "Не понял сообщение. Используйте /add для пошагового добавления или /help."
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик inline-кнопок."""

    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "add_film":
        await add_command(update, context)
        return

    if data == "list_films":
        worksheet = connect_to_sheet()
        records = fetch_records(worksheet)
        if not records:
            await query.edit_message_text(
                "Пока нет записей. Начните с добавления нового фильма!",
                reply_markup=get_main_menu(),
            )
            return

        lines = ["Последние записи:"]
        for row in records[-5:]:
            lines.append(_format_entry(row))
        await query.edit_message_text("\n".join(lines), reply_markup=get_main_menu())
        return

    if data == "search_genre":
        await query.edit_message_text(
            "Используйте команду /find жанр=<жанр> для поиска по жанру.",
            reply_markup=get_main_menu(),
        )
        return

    if data == "rating_stats":
        await query.edit_message_text(
            "Команда /top n=<число> покажет лучшие оценки.",
            reply_markup=get_main_menu(),
        )
        return
    if data == "offline_help":
        await query.edit_message_text(OFFLINE_GUIDE_TEXT, reply_markup=get_main_menu())
        return

    if data.startswith("skip:"):
        skipped_step = data.split(":", 1)[1]
        user_session = context.user_data.get("add_movie")
        if not user_session:
            await query.edit_message_text(
                "Сессия добавления не найдена. Попробуйте снова через /add.",
                reply_markup=get_main_menu(),
            )
            return

        movie_data = user_session.get("data", {})

        if skipped_step == "year":
            movie_data["year"] = ""
            user_session["step"] = "genre"
            await query.edit_message_text("⏭ Год пропущен.")
            await update.effective_chat.send_message(
                "🎭 Укажите жанр (можно несколько через запятую):"
            )
            return

        if skipped_step == "comment":
            movie_data["comment"] = ""
            user_session["step"] = "type"
            await query.edit_message_text("⏭ Комментарий пропущен.")
            await update.effective_chat.send_message(
                "Что вы добавляете?", reply_markup=_type_keyboard()
            )
            return

        await query.edit_message_text(
            "Неизвестный шаг для пропуска. Попробуйте снова.",
            reply_markup=get_main_menu(),
        )
        return

    if data.startswith("type:"):
        entry_type = data.split(":", 1)[1]
        user_session = context.user_data.get("add_movie")
        if not user_session:
            await query.edit_message_text(
                "Сессия добавления не найдена. Попробуйте снова через /add.",
                reply_markup=get_main_menu(),
            )
            return
        movie_data = user_session.get("data", {})
        movie_data["type"] = normalize_type(entry_type)
        user_session["step"] = "recommendation"
        await query.edit_message_text(
            "Тип выбран! Теперь укажите, рекомендуете ли вы фильм.",
            reply_markup=_recommendation_keyboard(),
        )
        return

    if data.startswith("recommendation:"):
        recommendation = data.split(":", 1)[1]
        user_session = context.user_data.get("add_movie")
        if not user_session:
            await query.edit_message_text(
                "Сессия добавления не найдена. Попробуйте снова через /add.",
                reply_markup=get_main_menu(),
            )
            return
        movie_data = user_session.get("data", {})
        movie_data["recommendation"] = normalize_recommendation(recommendation)
        user_session["step"] = "owner"
        await query.edit_message_text(
            "Кто нашёл фильм?",
            reply_markup=_owner_keyboard(),
        )
        return

    if data.startswith("owner:"):
        owner = data.split(":", 1)[1]
        user_session = context.user_data.get("add_movie")
        if not user_session:
            await query.edit_message_text(
                "Сессия добавления не найдена. Попробуйте снова через /add.",
                reply_markup=get_main_menu(),
            )
            return
        movie_data = user_session.get("data", {})
        movie_data["owner"] = normalize_owner(owner)
        context.user_data.pop("add_movie", None)
        await query.edit_message_text("Сохраняю запись…")
        await _finish_movie_entry(update, movie_data)
        return

    await query.edit_message_text(
        "Неизвестное действие. Попробуйте снова.", reply_markup=get_main_menu()
    )


async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Поиск фильмов по жанру."""

    parts = update.message.text.split()
    params: Dict[str, str] = {}
    for raw in parts[1:]:
        if "=" in raw:
            key, value = raw.split("=", 1)
            params[key.lower()] = value

    genre = params.get("жанр") or params.get("genre")
    if not genre:
        await update.message.reply_text(
            "Укажите жанр в формате /find жанр=комедия", reply_markup=get_main_menu()
        )
        return

    worksheet = connect_to_sheet()
    records = fetch_records(worksheet)
    await _handle_find_command(update, records, genre)


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать топ фильмов по оценке."""

    params: Dict[str, str] = {}
    for raw in update.message.text.split()[1:]:
        if "=" in raw:
            key, value = raw.split("=", 1)
            params[key.lower()] = value

    amount_raw = params.get("n") or params.get("количество")
    try:
        amount = int(amount_raw) if amount_raw else 5
    except ValueError:
        await update.message.reply_text(
            "Количество должно быть числом, например /top n=5."
        )
        return

    worksheet = connect_to_sheet()
    records = fetch_records(worksheet)
    await _handle_top_command(update, records, max(amount, 1))


async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать записи за последний месяц."""

    worksheet = connect_to_sheet()
    records = fetch_records(worksheet)
    await _handle_recent_command(update, records)
