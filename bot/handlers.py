"""Telegram bot handlers."""

from datetime import datetime
import random
import time
from typing import Dict, Iterable, List, Optional, Tuple

from telegram import Update
from telegram.error import BadRequest
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
from core.offline_queue import add_offline_entry
from bot.interface import get_main_menu


HELP_TEXT = (
    "Команды:\n"
    "• /add — добавить фильм\n"
    "• /top — топ по оценке\n"
    "• /recent — за последний месяц\n"
    "• /find <жанр> — поиск по жанру\n"
    "• /list — последние добавления\n"
    "• /stats — статистика по оценкам\n"
    "• /random — случайный фильм\n"
    "• /owner <муж|жена> — подборка по владельцу\n"
    "• /menu — меню\n"
    "• /help — помощь"
)

OFFLINE_GUIDE_TEXT = "Если таблица недоступна, записи сохраняются оффлайн."
ADD_USAGE_TEXT = (
    "Чтобы добавить запись, используйте формат:\n"
    "/add Название;Год;Жанр;Оценка;Комментарий;Тип;Рекомендация;Владелец\n"
    "Комментарий, тип, рекомендация и владелец — опционально.\n"
    "Пример:\n"
    "/add Интерстеллар;2014;фантастика;9;Шикарный саундтрек;фильм;рекомендую;муж"
)
_CACHE_TTL_SECONDS = 60
_RESPONSE_CACHE: Dict[str, Tuple[float, str]] = {}


# -------------------- utils --------------------

def _get_cached_response(cache_key: str) -> Optional[str]:
    cached = _RESPONSE_CACHE.get(cache_key)
    if not cached:
        return None
    expires_at, text = cached
    if time.time() <= expires_at:
        return text
    _RESPONSE_CACHE.pop(cache_key, None)
    return None


def _store_cached_response(cache_key: str, text: str) -> None:
    _RESPONSE_CACHE[cache_key] = (time.time() + _CACHE_TTL_SECONDS, text)


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


def _parse_timestamp(value: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _normalize_rating(value: str) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _extract_add_payload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if context.args:
        return " ".join(context.args).strip()
    if update.message and update.message.text:
        text = update.message.text
        if text.startswith("/add"):
            return text.partition(" ")[2].strip()
    return ""


def _parse_add_payload(payload: str) -> Dict[str, str]:
    parts = [part.strip() for part in payload.split(";")]
    if len(parts) < 4:
        raise ValueError("missing_fields")

    if len(parts) > 8:
        comment = ";".join(parts[4:-3]).strip()
        parts = parts[:4] + [comment] + parts[-3:]

    while len(parts) < 8:
        parts.append("")

    film, year, genre, rating, comment, entry_type, recommendation, owner = parts[:8]

    if not film or not year or not genre or not rating:
        raise ValueError("missing_fields")
    if not (year.isdigit() and len(year) == 4):
        raise ValueError("invalid_year")
    try:
        rating_value = float(rating.replace(",", "."))
    except ValueError as exc:
        raise ValueError("invalid_rating") from exc
    if not (1 <= rating_value <= 10):
        raise ValueError("invalid_rating")

    normalized_rating = f"{rating_value:g}"

    return {
        "film": film,
        "year": year,
        "genre": genre,
        "rating": normalized_rating,
        "comment": comment,
        "type": normalize_type(entry_type),
        "recommendation": normalize_recommendation(recommendation),
        "owner": normalize_owner(owner),
    }


# -------------------- commands --------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, "🎬 MovieBot готов к работе.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, HELP_TEXT)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, "Меню:")


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payload = _extract_add_payload(update, context)
    if not payload:
        await _send(update, ADD_USAGE_TEXT)
        return

    try:
        entry = _parse_add_payload(payload)
    except ValueError as exc:
        if str(exc) in {"missing_fields", "invalid_year", "invalid_rating"}:
            await _send(update, f"Некорректные данные.\n\n{ADD_USAGE_TEXT}")
        else:
            await _send(update, "Не удалось разобрать данные для добавления.")
        return

    try:
        ws = connect_to_sheet()
        add_movie_row(
            ws,
            entry["film"],
            entry["year"],
            entry["genre"],
            entry["rating"],
            entry["comment"],
            entry["type"],
            entry["recommendation"],
            entry["owner"],
        )
    except Exception as exc:
        print("GSHEET ERROR:", type(exc).__name__, exc)
        add_offline_entry(entry)
        await _send(
            update,
            "⚠️ Сейчас нет связи с таблицей. "
            "Запись сохранена оффлайн и будет выгружена позже.",
        )
        return

    await _send(update, "✅ Запись добавлена в таблицу.")


async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await _send(update, "Использование: /find <жанр>")
        return

    genre = " ".join(context.args).strip()
    cache_key = f"find:{genre.lower()}"
    cached = _get_cached_response(cache_key)
    if cached:
        await _send(update, cached)
        return

    records = await _safe_fetch_records(update)
    if records is None:
        return

    filtered = filter_by_genre(records, genre)

    if not filtered:
        await _send(update, "Ничего не найдено.")
        return

    text = "🔎 Найдено:\n" + "\n".join(
        _format_entry(r) for r in filtered[:10]
    )
    _store_cached_response(cache_key, text)
    await _send(update, text)


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cached = _get_cached_response("top")
    if cached:
        await _send(update, cached)
        return

    records = await _safe_fetch_records(update)
    if records is None:
        return

    rows = top_by_rating(records, 5)
    text = "🏆 Топ:\n" + "\n".join(
        f"{i+1}. {_format_entry(r)}" for i, r in enumerate(rows)
    )
    _store_cached_response("top", text)
    await _send(update, text)


async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cached = _get_cached_response("recent")
    if cached:
        await _send(update, cached)
        return

    records = await _safe_fetch_records(update)
    if records is None:
        return

    rows = recent_entries(records)
    text = "🗓 Последние:\n" + "\n".join(
        _format_entry(r) for r in rows[:10]
    )
    _store_cached_response("recent", text)
    await _send(update, text)


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    records = await _safe_fetch_records(update)
    if records is None:
        return

    stamped_rows = []
    no_stamp = []
    for row in records:
        timestamp = (
            row.get("Добавлено")
            or row.get("Timestamp")
            or row.get("Дата")
            or row.get("Added")
            or ""
        )
        parsed = _parse_timestamp(str(timestamp)) if timestamp else None
        if parsed:
            stamped_rows.append((parsed, row))
        else:
            no_stamp.append(row)

    if stamped_rows:
        stamped_rows.sort(key=lambda item: item[0], reverse=True)
        ordered = [row for _, row in stamped_rows] + no_stamp
    else:
        ordered = list(records)

    if not ordered:
        await _send(update, "Пока нет добавленных записей.")
        return

    text = "📜 Последние добавления:\n" + "\n".join(
        _format_entry(r) for r in ordered[:10]
    )
    await _send(update, text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    records = await _safe_fetch_records(update)
    if records is None:
        return

    ratings = []
    for row in records:
        raw_rating = row.get("Оценка") or row.get("Rating") or row.get("rating")
        rating_value = _normalize_rating(raw_rating)
        if rating_value > 0:
            ratings.append(rating_value)

    total = len(records)
    rated = len(ratings)
    if rated:
        avg_rating = sum(ratings) / rated
        min_rating = min(ratings)
        max_rating = max(ratings)
        text = (
            "📊 Статистика по оценкам:\n"
            f"Всего записей: {total}\n"
            f"С оценкой: {rated}\n"
            f"Средняя: {avg_rating:.1f}/10\n"
            f"Мин: {min_rating:.1f}/10\n"
            f"Макс: {max_rating:.1f}/10"
        )
    else:
        text = (
            "📊 Статистика по оценкам:\n"
            f"Всего записей: {total}\n"
            "Пока нет оценок для расчета статистики."
        )
    await _send(update, text)


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    records = await _safe_fetch_records(update)
    if records is None:
        return

    if not records:
        await _send(update, "Пока нет записей для случайной рекомендации.")
        return

    row = random.choice(records)
    await _send(update, f"🎲 Случайный выбор:\n{_format_entry(row)}")


async def owner_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await _send(update, "Использование: /owner <муж|жена>")
        return

    owner = normalize_owner(" ".join(context.args))
    if not owner:
        await _send(update, "Использование: /owner <муж|жена>")
        return

    records = await _safe_fetch_records(update)
    if records is None:
        return

    filtered = [
        row
        for row in records
        if normalize_owner(row.get("Владелец") or row.get("Чье") or "") == owner
    ]

    if not filtered:
        await _send(update, f"Для владельца «{owner}» ничего не найдено.")
        return

    text = f"👤 Подборка ({owner}):\n" + "\n".join(
        _format_entry(r) for r in filtered[:10]
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

    if data == "list_films":
        await list_command(update, context)
        return

    if data == "rating_stats":
        await stats_command(update, context)
        return

    if data == "search_genre":
        await _send(update, "Использование: /find <жанр>")
        return

    if data == "help":
        await _send(update, HELP_TEXT)
        return

    if data == "offline_help":
        await _send(update, OFFLINE_GUIDE_TEXT)
        return

    if data == "add_film":
        await _send(update, ADD_USAGE_TEXT)
        return

    await update.callback_query.answer()


# -------------------- messages --------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, "Используйте меню или /help.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, "Обработка изображений отключена.")
