"""Voice-to-add-flow handlers powered by Mistral."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Dict, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.callback_ids import (
    ADD_FLOW_VOICE_CANCEL,
    ADD_FLOW_VOICE_CLARIFY_TEXT,
    ADD_FLOW_VOICE_CLARIFY_VOICE,
)
from bot.handlers_add_flow_cleanup import (
    clear_add_flow_cleanup,
    reply_add_flow,
    reset_add_flow_cleanup,
    track_add_flow_user_message,
)
from bot.handlers_add_flow_ui import _finish_add_flow, _parse_add_payload
from bot.handlers_ai_helpers import _extract_json_dict
from bot.handlers_texts import ADD_VOICE_CLARIFY
from bot.handlers_transport import _send, _typing
from bot.ui_texts import (
    ADD_FLOW_MSG_CANCELLED,
    VOICE_ADD_BTN_CLARIFY_CANCEL,
    VOICE_ADD_BTN_CLARIFY_TEXT,
    VOICE_ADD_BTN_CLARIFY_VOICE,
    VOICE_ADD_MSG_CLARIFY_TEMPLATE,
    VOICE_ADD_MSG_NEEDS_MISTRAL_KEY,
    VOICE_ADD_MSG_PARSE_FAILED,
    VOICE_ADD_MSG_RECOGNIZED_TEMPLATE,
    VOICE_ADD_MSG_TRANSCRIBE_FAILED,
)
from core.mistral import (
    MistralError,
    generate_mistral_reply,
    is_mistral_enabled,
    transcribe_mistral_audio,
)
from core.normalization import normalize_owner, normalize_recommendation, normalize_type
from core.recommendations import lookup_omdb_details

logger = logging.getLogger(__name__)
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2}|2100)\b")
_COMMENT_MARKER_RE = re.compile(r"коммент\w*", re.IGNORECASE)
_OWNER_MALE_RE = re.compile(r"\b(муж|husband)\b", re.IGNORECASE)
_OWNER_FEMALE_RE = re.compile(r"\b(жена|wife)\b", re.IGNORECASE)
_INSTRUCTION_HINTS = (
    "фильм",
    "сериал",
    "называ",
    "оценк",
    "рейтинг",
    "жанр",
    "год",
    "добав",
    "постав",
    "рекоменд",
    "муж",
    "жена",
    "owner",
)


def _clean_text(value: object) -> str:
    text = str(value or "").strip()
    text = text.replace(";", ",")
    text = re.sub(r"\s+", " ", text)
    return text


def _normalize_year(value: object) -> str:
    raw = _clean_text(value)
    if raw.isdigit() and len(raw) == 4:
        return raw
    match = _YEAR_RE.search(raw)
    return match.group(1) if match else ""


def _normalize_rating(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):g}"
    text = _clean_text(value).replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", text)
    return match.group(0) if match else ""


def _is_valid_year(value: str) -> bool:
    return value.isdigit() and len(value) == 4


def _is_valid_rating(value: str) -> bool:
    try:
        rating_value = float((value or "").replace(",", "."))
    except ValueError:
        return False
    return 1 <= rating_value <= 10


def _missing_required_labels(entry: Dict[str, str]) -> list[str]:
    missing: list[str] = []
    if not (entry.get("film") or "").strip():
        missing.append("название")
    if not _is_valid_year(_normalize_year(entry.get("year"))):
        missing.append("год")
    if not (entry.get("genre") or "").strip():
        missing.append("жанр")
    if not _is_valid_rating(_normalize_rating(entry.get("rating"))):
        missing.append("оценка")
    return missing


def _merge_entries(base: Dict[str, str], patch: Dict[str, str]) -> Dict[str, str]:
    merged = dict(base)
    for key, value in patch.items():
        text = _clean_text(value)
        if text:
            merged[key] = text
    return merged


def _voice_clarify_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    VOICE_ADD_BTN_CLARIFY_TEXT,
                    callback_data=ADD_FLOW_VOICE_CLARIFY_TEXT,
                ),
                InlineKeyboardButton(
                    VOICE_ADD_BTN_CLARIFY_VOICE,
                    callback_data=ADD_FLOW_VOICE_CLARIFY_VOICE,
                ),
            ],
            [
                InlineKeyboardButton(
                    VOICE_ADD_BTN_CLARIFY_CANCEL,
                    callback_data=ADD_FLOW_VOICE_CANCEL,
                )
            ],
        ]
    )


def _extract_owner_from_text(transcript: str) -> str:
    normalized = (transcript or "").strip()
    if not normalized:
        return ""
    if _OWNER_MALE_RE.search(normalized):
        return "муж"
    if _OWNER_FEMALE_RE.search(normalized):
        return "жена"
    return ""


def _looks_like_instruction(sentence: str) -> bool:
    lowered = (sentence or "").strip().lower()
    if not lowered:
        return False
    return any(hint in lowered for hint in _INSTRUCTION_HINTS)


def _normalize_comment_fragment(fragment: str) -> str:
    text = _clean_text(fragment)
    if not text:
        return ""
    text = re.sub(
        r"^\s*(?:и\b\s*)?(?:не\s+знаю\b[\s,]*)?(?:ну\b[\s,]*)*(?:короче\b[\s,]*)*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^\s*(?:ну\b\s*)?(?:вот\b\s*)?(?:это\b\s*)?(?:будет\b\s*)?(?:мой\b\s*)?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bкоммент\w*\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" ,.-:")
    return text


def _infer_comment_from_transcript(transcript: str) -> str:
    text = _clean_text(transcript)
    if not text:
        return ""

    sentences = [
        sentence.strip(" ,.-:")
        for sentence in re.split(r"[.!?]+", text)
        if sentence.strip()
    ]
    if not sentences:
        return ""

    for index, sentence in enumerate(sentences):
        if not _COMMENT_MARKER_RE.search(sentence):
            continue

        marker = _COMMENT_MARKER_RE.search(sentence)
        if marker is None:
            continue

        before = _normalize_comment_fragment(sentence[: marker.start()])
        if before and not _looks_like_instruction(before):
            return before

        after = _normalize_comment_fragment(sentence[marker.end() :])
        if after and not _looks_like_instruction(after):
            return after

        for prev_index in range(index - 1, -1, -1):
            candidate = _normalize_comment_fragment(sentences[prev_index])
            if candidate and not _looks_like_instruction(candidate):
                return candidate

    return ""


def _entry_to_payload(entry: Dict[str, str]) -> str:
    return ";".join(
        [
            entry.get("film", ""),
            entry.get("year", ""),
            entry.get("genre", ""),
            entry.get("rating", ""),
            entry.get("comment", ""),
            entry.get("type", ""),
            entry.get("recommendation", ""),
            entry.get("owner", ""),
        ]
    )


def _build_entry_from_structured(data: Dict[str, object]) -> Dict[str, str]:
    return {
        "film": _clean_text(data.get("film") or data.get("title")),
        "year": _normalize_year(data.get("year")),
        "genre": _clean_text(data.get("genre") or data.get("genres")),
        "rating": _normalize_rating(data.get("rating")),
        "comment": _clean_text(data.get("comment")),
        "type": normalize_type(_clean_text(data.get("type") or data.get("media_type"))),
        "recommendation": normalize_recommendation(_clean_text(data.get("recommendation"))),
        "owner": normalize_owner(_clean_text(data.get("owner"))),
    }


def _autofill_entry_from_catalog(entry: Dict[str, str]) -> Dict[str, str]:
    film = entry.get("film", "").strip()
    if not film:
        return entry

    year_text = _normalize_year(entry.get("year", ""))
    year_value = int(year_text) if year_text.isdigit() else None

    if year_text and entry.get("genre", "").strip():
        entry["year"] = year_text
        return entry

    details = lookup_omdb_details(film, year_value)
    if not details:
        entry["year"] = year_text
        return entry

    if not year_text:
        entry["year"] = _normalize_year(details.get("Year"))
    else:
        entry["year"] = year_text

    if not entry.get("genre", "").strip():
        genre = _clean_text(details.get("Genre"))
        if genre:
            entry["genre"] = genre

    if not entry.get("type", "").strip():
        entry["type"] = normalize_type(_clean_text(details.get("Type")))

    return entry


def _enrich_voice_entry(entry: Dict[str, str], transcript: str) -> Dict[str, str]:
    enriched = dict(entry)
    enriched = _autofill_entry_from_catalog(enriched)

    if not enriched.get("comment", "").strip():
        comment = _infer_comment_from_transcript(transcript)
        if comment:
            enriched["comment"] = comment

    if not enriched.get("owner", "").strip():
        owner = _extract_owner_from_text(transcript)
        if owner:
            enriched["owner"] = owner

    return enriched


def _build_add_payload_from_structured(data: Dict[str, object]) -> str:
    return _entry_to_payload(_build_entry_from_structured(data))


def _extract_entry_from_free_text_loose(text: str) -> Optional[Dict[str, str]]:
    prompt = (
        "Извлеки данные фильма из текста и верни строго JSON без markdown.\n"
        "Ключевое: все фразы с впечатлениями/эмоциями/оценочными словами относить в поле comment.\n"
        "Если слышно разговорный мусор (ну, короче, типа) - игнорируй его.\n"
        "Если явно сказано кто добавил (муж/жена), заполни owner.\n"
        "Если year/genre не названы, но фильм общеизвестный, заполни по известным данным.\n"
        "Формат JSON:\n"
        '{"film":"", "year":"", "genre":"", "rating":"", "comment":"", '
        '"type":"film|series", "recommendation":"рекомендую|можно посмотреть|в топку", '
        '"owner":"муж|жена|"}\n'
        "Если поля нет, оставь пустую строку.\n\n"
        f"Текст:\n{text}"
    )
    answer = generate_mistral_reply(
        prompt,
        temperature=0.1,
        max_output_tokens=300,
    )
    payload = _extract_json_dict(answer)
    if not payload:
        return None
    entry = _build_entry_from_structured(payload)
    return _enrich_voice_entry(entry, text)


def _extract_voice_entry(transcript: str) -> Optional[Dict[str, str]]:
    entry = _extract_entry_from_free_text_loose(transcript)
    if not entry:
        return None
    normalized_payload = _entry_to_payload(entry)
    return _parse_add_payload(normalized_payload)


async def _prompt_voice_clarification(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    entry: Dict[str, str],
    *,
    transcript_preview: str = "",
) -> int:
    safe_entry = entry if isinstance(entry, dict) else {}
    context.user_data["add_flow"] = safe_entry
    missing = _missing_required_labels(safe_entry)
    missing_text = ", ".join(missing) if missing else "обязательные поля"
    text = VOICE_ADD_MSG_CLARIFY_TEMPLATE.format(missing=missing_text)
    if transcript_preview:
        text = f"{text}\n\nТранскрипт: {transcript_preview}"
    await reply_add_flow(
        update,
        context,
        text,
        reply_markup=_voice_clarify_keyboard(),
    )
    return ADD_VOICE_CLARIFY


async def _apply_partial_entry_and_continue(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    partial_entry: Dict[str, str],
    *,
    transcript_preview: str = "",
) -> int:
    existing = context.user_data.get("add_flow")
    base_entry = existing if isinstance(existing, dict) else {}
    merged = _merge_entries(base_entry, partial_entry)

    try:
        normalized = _parse_add_payload(_entry_to_payload(merged))
    except ValueError as exc:
        reason = str(exc)
        if reason in {"missing_fields", "invalid_year", "invalid_rating"}:
            return await _prompt_voice_clarification(
                update,
                context,
                merged,
                transcript_preview=transcript_preview,
            )
        clear_add_flow_cleanup(context)
        await _send(update, VOICE_ADD_MSG_PARSE_FAILED)
        return ConversationHandler.END

    context.user_data["add_flow"] = normalized
    return await _finish_add_flow(update, context)


async def add_flow_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    has_existing_entry = isinstance(context.user_data.get("add_flow"), dict)
    if has_existing_entry:
        track_add_flow_user_message(update, context)
    else:
        reset_add_flow_cleanup(update, context)
    if not update.message or not update.message.voice:
        clear_add_flow_cleanup(context)
        await _send(update, VOICE_ADD_MSG_TRANSCRIBE_FAILED)
        return ConversationHandler.END

    if not is_mistral_enabled():
        clear_add_flow_cleanup(context)
        await _send(update, VOICE_ADD_MSG_NEEDS_MISTRAL_KEY)
        return ConversationHandler.END

    async with _typing(update, context):
        try:
            tg_file = await update.message.voice.get_file()
            audio_bytes = bytes(await tg_file.download_as_bytearray())
            mime_type = update.message.voice.mime_type or "audio/ogg"
        except Exception as exc:
            logger.error("VOICE DOWNLOAD ERROR: %s %s", type(exc).__name__, exc)
            clear_add_flow_cleanup(context)
            await _send(update, VOICE_ADD_MSG_TRANSCRIBE_FAILED)
            return ConversationHandler.END

        try:
            transcript = await asyncio.to_thread(
                transcribe_mistral_audio,
                audio_bytes=audio_bytes,
                file_name="voice.ogg",
                mime_type=mime_type,
                language="ru",
            )
        except MistralError as exc:
            logger.error("MISTRAL TRANSCRIBE ERROR: %s %s", type(exc).__name__, exc)
            if has_existing_entry:
                await reply_add_flow(update, context, VOICE_ADD_MSG_TRANSCRIBE_FAILED)
                return ADD_VOICE_CLARIFY
            clear_add_flow_cleanup(context)
            await _send(update, VOICE_ADD_MSG_TRANSCRIBE_FAILED)
            return ConversationHandler.END
        except Exception as exc:
            logger.error("VOICE TRANSCRIBE ERROR: %s %s", type(exc).__name__, exc)
            if has_existing_entry:
                await reply_add_flow(update, context, VOICE_ADD_MSG_TRANSCRIBE_FAILED)
                return ADD_VOICE_CLARIFY
            clear_add_flow_cleanup(context)
            await _send(update, VOICE_ADD_MSG_TRANSCRIBE_FAILED)
            return ConversationHandler.END

        transcript_preview = transcript if len(transcript) <= 200 else transcript[:200] + "..."
        await reply_add_flow(
            update,
            context,
            VOICE_ADD_MSG_RECOGNIZED_TEMPLATE.format(transcript=transcript_preview),
        )

        try:
            partial_entry = await asyncio.to_thread(_extract_entry_from_free_text_loose, transcript)
        except MistralError as exc:
            logger.error("MISTRAL PARSE ERROR: %s %s", type(exc).__name__, exc)
            if has_existing_entry:
                return await _prompt_voice_clarification(
                    update,
                    context,
                    context.user_data.get("add_flow", {}),
                    transcript_preview=transcript_preview,
                )
            clear_add_flow_cleanup(context)
            await _send(update, VOICE_ADD_MSG_PARSE_FAILED)
            return ConversationHandler.END
        except Exception as exc:
            logger.error("VOICE PARSE ERROR: %s %s", type(exc).__name__, exc)
            if has_existing_entry:
                return await _prompt_voice_clarification(
                    update,
                    context,
                    context.user_data.get("add_flow", {}),
                    transcript_preview=transcript_preview,
                )
            clear_add_flow_cleanup(context)
            await _send(update, VOICE_ADD_MSG_PARSE_FAILED)
            return ConversationHandler.END

        if not partial_entry:
            if has_existing_entry:
                return await _prompt_voice_clarification(
                    update,
                    context,
                    context.user_data.get("add_flow", {}),
                    transcript_preview=transcript_preview,
                )
            clear_add_flow_cleanup(context)
            await _send(update, VOICE_ADD_MSG_PARSE_FAILED)
            return ConversationHandler.END

        return await _apply_partial_entry_and_continue(
            update,
            context,
            partial_entry,
            transcript_preview=transcript_preview,
        )


async def add_flow_voice_clarify_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    track_add_flow_user_message(update, context)
    text = (update.message.text or "").strip() if update.message else ""
    if not text:
        entry = context.user_data.get("add_flow", {})
        return await _prompt_voice_clarification(update, context, entry)

    try:
        partial_entry = await asyncio.to_thread(_extract_entry_from_free_text_loose, text)
    except MistralError as exc:
        logger.error("MISTRAL CLARIFY ERROR: %s %s", type(exc).__name__, exc)
        partial_entry = None
    except Exception as exc:
        logger.error("VOICE CLARIFY ERROR: %s %s", type(exc).__name__, exc)
        partial_entry = None

    if not partial_entry:
        existing = context.user_data.get("add_flow")
        base_entry = existing if isinstance(existing, dict) else {}
        if len(_missing_required_labels(base_entry)) == 1:
            only_missing = _missing_required_labels(base_entry)[0]
            fallback_patch: Dict[str, str] = {}
            if only_missing == "год":
                year = _normalize_year(text)
                if _is_valid_year(year):
                    fallback_patch["year"] = year
            elif only_missing == "оценка":
                rating = _normalize_rating(text)
                if _is_valid_rating(rating):
                    fallback_patch["rating"] = rating
            elif only_missing == "жанр":
                fallback_patch["genre"] = _clean_text(text)
            elif only_missing == "название":
                fallback_patch["film"] = _clean_text(text)
            if fallback_patch:
                partial_entry = fallback_patch

    if not partial_entry:
        entry = context.user_data.get("add_flow", {})
        return await _prompt_voice_clarification(update, context, entry)

    return await _apply_partial_entry_and_continue(update, context, partial_entry)


async def add_flow_voice_clarify_hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query:
        return ADD_VOICE_CLARIFY
    data = query.data or ""
    if data.endswith(":clarify_voice"):
        await query.answer("Отправьте новое голосовое с уточнением.")
    else:
        await query.answer("Отправьте текст с уточнением полей.")
    return ADD_VOICE_CLARIFY


async def add_flow_voice_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    context.user_data.pop("add_flow", None)
    clear_add_flow_cleanup(context)
    await _send(update, ADD_FLOW_MSG_CANCELLED)
    return ConversationHandler.END


__all__ = [
    "add_flow_voice",
    "add_flow_voice_clarify_text",
    "add_flow_voice_clarify_hint",
    "add_flow_voice_cancel",
]
