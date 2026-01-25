"""Telegram bot handlers."""

from typing import Dict, Iterable, List, Optional

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from core.gsheet import (
    connect_to_sheet,
    fetch_records,
    filter_by_genre,
    recent_entries,
    top_by_rating,
)
from core.normalization import normalize_owner, normalize_type
from bot.interface import get_main_menu


HELP_TEXT = (
    "Команды:\n"
    "• /add — добавить фильм\n"
    "• /top — топ по оценке\n"
    "• /recent — за последний месяц\n"
    "• /find <жанр> — поиск по жанру\n"
    "• /menu — меню\n"
    "• /help — помощь"
)

OFFLINE_GUIDE_TEXT = "Если таблица недоступна, записи сохраняются оффлайн."


# -------------------- utils --------------------

async def _send(update: Update, text: str) -> None:
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text, reply_markup=get_main_menu()
            )
        except BadRequest:
            await update.callback_query.answer()
    else:
        await update.message.reply_text(text, reply_markup=get_main_menu())


async def _notify_table_unavailable(update: Update, action: str = "запрос") -> None:
    await _send(
        update,
        "⚠️ Сейчас нет связи с таблицей, поэтому выполнить "
        f"{action} не получилось. Попробуйте позже.",
    )


async def _safe_fetch_records(update: Update) -> Optional[List[Dict[str, str]]]:
    try:
        ws = connect_to_sheet()
        return fetch_records(ws)
    except Exception as exc:
        print("GSHEET ERROR:", type(exc).__name__, exc)
        await _notify_table_unavailable(update)
        return None


def _format_entry(row: Dict[str, str]) -> str:
    name = row.get("Фильм") or row.get("Название") or "—"
    year = row.get("Год") or "—"
    rating = row.get("Оценка") or "—"
    genre = row.get("Жанр") or "—"
    entry_type = normalize_type(row.get("Тип"))
    owner = normalize_owner(row.get("Владелец") or row.get("Чье") or "")
    owner_part = f" • {owner}" if owner else ""
    return f"{name} ({year}) — {rating}/10 • {entry_type} • {genre}{owner_part}"


# -------------------- commands --------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, "🎬 MovieBot готов к работе.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, HELP_TEXT)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, "Меню:")


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, "Добавление временно отключено.")


async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await _send(update, "Использование: /find <жанр>")
        return

    records = await _safe_fetch_records(update)
    if records is None:
        return

    genre = " ".join(context.args)
    filtered = filter_by_genre(records, genre)

    if not filtered:
        await _send(update, "Ничего не найдено.")
        return

    text = "🔎 Найдено:\n" + "\n".join(
        _format_entry(r) for r in filtered[:10]
    )
    await _send(update, text)


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    records = await _safe_fetch_records(update)
    if records is None:
        return

    rows = top_by_rating(records, 5)
    text = "🏆 Топ:\n" + "\n".join(
        f"{i+1}. {_format_entry(r)}" for i, r in enumerate(rows)
    )
    await _send(update, text)


async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    records = await _safe_fetch_records(update)
    if records is None:
        return

    rows = recent_entries(records)
    text = "🗓 Последние:\n" + "\n".join(
        _format_entry(r) for r in rows[:10]
    )
    await _send(update, text)


# -------------------- callbacks --------------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = update.callback_query.data

    if data == "top5":
        await top_command(update, context)
        return

    if data == "recent_entries":
        await recent_command(update, context)
        return

    if data == "help":
        await _send(update, HELP_TEXT)
        return

    if data == "offline_help":
        await _send(update, OFFLINE_GUIDE_TEXT)
        return

    await update.callback_query.answer()


# -------------------- messages --------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, "Используйте меню или /help.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, "Обработка изображений отключена.")
