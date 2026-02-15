"""Photo/poster recognition handler."""

from __future__ import annotations

import asyncio
import html
import logging
import re
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.callback_ids import ADD_FLOW_FROM_POSTER
from bot.handlers_ai_helpers import _extract_json_dict
from bot.handlers_sheet import _normalize_rating
from bot.handlers_transport import _send, _send_panel, _typing
from bot.ui_texts import (
    PHOTO_BUTTON_ADD_WATCHED,
    PHOTO_CONFIDENCE_TEMPLATE,
    PHOTO_FOUND_HEADER_TEMPLATE,
    PHOTO_GENRES_TEMPLATE,
    PHOTO_IMDB_TEMPLATE,
    PHOTO_MSG_DOWNLOAD_FAILED,
    PHOTO_MSG_GEMINI_UNAVAILABLE,
    PHOTO_MSG_NEEDS_GEMINI_KEY,
    PHOTO_MSG_NOT_FOUND,
    PHOTO_MSG_PARSE_FAILED,
    PHOTO_MSG_RECOGNIZE_FAILED,
    PHOTO_MSG_TITLE_UNSURE,
    PHOTO_PLOT_TEMPLATE,
    PHOTO_QUICK_ADD_TEMPLATE,
    PHOTO_REASON_TEMPLATE,
    PHOTO_TYPE_MOVIE,
    PHOTO_TYPE_SERIES,
    PHOTO_TYPE_TEMPLATE,
    PHOTO_TYPE_UNKNOWN,
)
from core.gemini import (
    GeminiError,
    generate_gemini_reply_with_image,
    is_gemini_enabled,
)
from core.normalization import normalize_type
from core.recommendations import lookup_omdb_details

logger = logging.getLogger(__name__)
_PHOTO_PREFILL_KEY = "photo_add_entry"
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2}|2100)\b")


def _extract_year_from_text(raw: str) -> int | None:
    text = (raw or "").strip()
    if text.isdigit() and len(text) == 4:
        value = int(text)
        return value if 1888 <= value <= 2100 else None
    match = _YEAR_RE.search(text)
    if not match:
        return None
    value = int(match.group(1))
    return value if 1888 <= value <= 2100 else None


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        await _send(update, PHOTO_MSG_NOT_FOUND)
        return
    if not is_gemini_enabled():
        await _send(update, PHOTO_MSG_NEEDS_GEMINI_KEY)
        return

    async with _typing(update, context):
        try:
            photo = update.message.photo[-1]
            tg_file = await photo.get_file()
            image_bytes = bytes(await tg_file.download_as_bytearray())
        except Exception as exc:
            logger.error("PHOTO ERROR: %s %s", type(exc).__name__, exc)
            await _send(update, PHOTO_MSG_DOWNLOAD_FAILED)
            return

        prompt = (
            "Определи фильм или сериал по изображению постера.\n"
            "Ответ верни строго JSON без пояснений:\n"
            '{"title":"...", "year":"....", "media_type":"movie|series|unknown", '
            '"confidence":0-100, "reason":"кратко"}\n'
            "Если не уверен, оставь title пустым."
        )

        try:
            ai_answer = await asyncio.to_thread(
                generate_gemini_reply_with_image,
                prompt=prompt,
                image_bytes=image_bytes,
                mime_type="image/jpeg",
                temperature=0.1,
                max_output_tokens=300,
            )
        except GeminiError as exc:
            logger.error("GEMINI ERROR: %s %s", type(exc).__name__, exc)
            await _send(update, PHOTO_MSG_GEMINI_UNAVAILABLE)
            return
        except Exception as exc:
            logger.error("GEMINI ERROR: %s %s", type(exc).__name__, exc)
            await _send(update, PHOTO_MSG_RECOGNIZE_FAILED)
            return

        parsed = _extract_json_dict(ai_answer)
        if not parsed:
            await _send(update, PHOTO_MSG_PARSE_FAILED)
            return

        title = str(parsed.get("title") or "").strip()
        if not title:
            await _send(update, PHOTO_MSG_TITLE_UNSURE)
            return

        year_text = str(parsed.get("year") or "").strip()
        year = int(year_text) if year_text.isdigit() and len(year_text) == 4 else None
        confidence_raw = parsed.get("confidence")
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.0
        media_type = str(parsed.get("media_type") or "unknown").strip().lower()
        reason = str(parsed.get("reason") or "").strip()

        details = await asyncio.to_thread(lookup_omdb_details, title, year)
        year_label = f" ({year})" if year else ""
        type_label = (
            PHOTO_TYPE_MOVIE
            if media_type == "movie"
            else PHOTO_TYPE_SERIES
            if media_type == "series"
            else PHOTO_TYPE_UNKNOWN
        )

        lines = [
            PHOTO_FOUND_HEADER_TEMPLATE.format(title=html.escape(title), year_label=year_label),
            PHOTO_TYPE_TEMPLATE.format(type_label=html.escape(type_label)),
        ]
        if confidence > 0:
            lines.append(PHOTO_CONFIDENCE_TEMPLATE.format(confidence=confidence))
        if reason:
            lines.append(PHOTO_REASON_TEMPLATE.format(reason=html.escape(reason)))

        if details:
            genre = (details.get("Genre") or "").strip()
            imdb_rating = _normalize_rating(details.get("imdbRating") or "")
            plot = (details.get("Plot") or "").strip()
            if genre and genre.lower() != "n/a":
                lines.append(PHOTO_GENRES_TEMPLATE.format(genre=html.escape(genre)))
            if imdb_rating > 0:
                lines.append(PHOTO_IMDB_TEMPLATE.format(imdb_rating=imdb_rating))
            if plot and plot.lower() != "n/a":
                if len(plot) > 280:
                    plot = plot[:280].rstrip() + "..."
                lines.append(PHOTO_PLOT_TEMPLATE.format(plot=html.escape(plot)))

        if not year and details:
            year = _extract_year_from_text(str(details.get("Year") or ""))

        prefill_type = ""
        if media_type in {"movie", "series", "film", "сериал", "фильм"}:
            prefill_type = normalize_type(media_type)

        prefill_entry = {
            "film": title.strip(),
            "year": str(year) if year else "",
            "genre": (details.get("Genre") or "").strip() if details else "",
            "rating": "",
            "comment": reason or "",
            "type": prefill_type,
            "recommendation": "",
            "owner": "",
        }
        if details:
            imdb_rating = _normalize_rating(details.get("imdbRating") or "")
            if imdb_rating > 0:
                prefill_entry["rating"] = f"{imdb_rating:g}"
        context.user_data[_PHOTO_PREFILL_KEY] = prefill_entry

        quick_add_title = prefill_entry["film"].replace(";", ",")
        quick_add_year = prefill_entry["year"] or str(year or datetime.now().year)
        quick_add_genre = (prefill_entry["genre"] or "жанр").replace(";", ",")
        quick_add_rating = prefill_entry["rating"] or "8"

        lines.append("")
        lines.append(
            PHOTO_QUICK_ADD_TEMPLATE.format(
                title=quick_add_title,
                year=quick_add_year,
                genre=quick_add_genre,
                rating=quick_add_rating,
            )
        )
        await _send_panel(
            update,
            "\n".join(lines),
            InlineKeyboardMarkup(
                [[InlineKeyboardButton(PHOTO_BUTTON_ADD_WATCHED, callback_data=ADD_FLOW_FROM_POSTER)]]
            ),
            parse_mode=ParseMode.HTML,
        )


__all__ = ["handle_photo"]
