"""Random recommendation handler."""

from __future__ import annotations

import asyncio
import html
import logging
from typing import List

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot.handlers_ai_helpers import (
    _ai_single_unseen_pick,
    _build_quick_add_keyboard,
    _build_watched_dedupe_lookup,
    _extract_year_from_title_label,
    _filter_candidates_by_min_year,
    _pick_weighted_random_candidate,
)
from bot.handlers_cache import (
    _get_cached_profile,
    _get_recent_recommendations,
    _normalize_title_for_dedupe,
    _store_cached_profile,
    _store_recent_recommendations,
)
from bot.handlers_sheet import _safe_fetch_records
from bot.handlers_transport import _send, _send_panel, _typing
from bot.ui_texts import (
    RANDOM_AI_PICK_TEMPLATE,
    RANDOM_MSG_NO_RECORDS,
    RANDOM_MSG_UNAVAILABLE,
    RANDOM_PICK_TEMPLATE,
    RANDOM_PLOT_TEMPLATE,
    RANDOM_RATINGS_UNKNOWN,
    RANDOM_REASON_DEFAULT,
    RANDOM_VALUE_UNKNOWN,
)
from core.recommendations import (
    CandidateMovie,
    build_profile_summary,
    build_taste_profile,
    collect_tmdb_candidates,
    lookup_omdb_details,
    tmdb_enabled,
)

logger = logging.getLogger(__name__)


def _extract_omdb_poster_url(details: dict | None) -> str:
    if not details:
        return ""
    poster = str(details.get("Poster") or "").strip()
    if not poster or poster.lower() == "n/a":
        return ""
    return poster


def _build_random_pick_caption(picked: CandidateMovie) -> str:
    year = str(picked.year) if picked.year else RANDOM_VALUE_UNKNOWN
    genres = ", ".join(picked.genres[:3]) if picked.genres else RANDOM_VALUE_UNKNOWN

    rating_parts: List[str] = []
    if picked.tmdb_rating > 0:
        rating_parts.append(f"TMDB {picked.tmdb_rating:.1f}/10")
    if picked.imdb_rating and picked.imdb_rating > 0:
        rating_parts.append(f"IMDb {picked.imdb_rating:.1f}/10")
    ratings_line = " | ".join(rating_parts) if rating_parts else RANDOM_RATINGS_UNKNOWN

    reason = picked.reason or RANDOM_REASON_DEFAULT

    text = RANDOM_PICK_TEMPLATE.format(
        title=html.escape(picked.title),
        year=html.escape(year),
        genres=html.escape(genres),
        ratings=html.escape(ratings_line),
        reason=html.escape(reason),
    )
    if picked.omdb_plot:
        plot = picked.omdb_plot.strip()
        if len(plot) > 240:
            plot = plot[:240].rstrip() + "..."
        text += RANDOM_PLOT_TEMPLATE.format(plot=html.escape(plot))
    return text


async def _try_send_candidate_with_poster(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    picked: CandidateMovie,
    text: str,
) -> bool:
    if not update.effective_chat:
        return False

    if update.callback_query:
        try:
            await update.callback_query.answer()
        except BadRequest as exc:
            message = str(exc).lower()
            if "query is too old" not in message and "query id is invalid" not in message:
                raise

    poster_candidates: List[tuple[str, str]] = []
    if picked.poster_url:
        poster_candidates.append((picked.poster_url, "TMDB"))

    if not poster_candidates or picked.poster_url.startswith("https://image.tmdb.org/"):
        details = await asyncio.to_thread(lookup_omdb_details, picked.title, picked.year)
        omdb_poster = _extract_omdb_poster_url(details)
        if omdb_poster and all(omdb_poster != url for url, _ in poster_candidates):
            poster_candidates.append((omdb_poster, "OMDB"))

    for poster_url, source in poster_candidates:
        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=poster_url,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=_build_quick_add_keyboard(picked.title, picked.year),
            )
            return True
        except Exception as exc:
            logger.warning(
                "%s POSTER ERROR: %s %s",
                source,
                type(exc).__name__,
                exc,
            )
            continue
    return False


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with _typing(update, context):
        records = await _safe_fetch_records(update)
        if records is None:
            return

        if not records:
            await _send(update, RANDOM_MSG_NO_RECORDS)
            return

        profile = _get_cached_profile()
        if profile is None:
            profile = build_taste_profile(records)
            _store_cached_profile(profile)

        watched_lookup = _build_watched_dedupe_lookup(records)
        recent_titles = _get_recent_recommendations(update)
        recent_lookup = {_normalize_title_for_dedupe(item) for item in recent_titles}

        candidates: List[CandidateMovie] = []
        if tmdb_enabled():
            candidates = await asyncio.to_thread(collect_tmdb_candidates, profile)
            candidates = _filter_candidates_by_min_year(candidates)

        if candidates:
            filtered = [
                item
                for item in candidates
                if _normalize_title_for_dedupe(item.title) not in watched_lookup
                and _normalize_title_for_dedupe(item.title) not in recent_lookup
            ]
            if not filtered:
                filtered = [
                    item
                    for item in candidates
                    if _normalize_title_for_dedupe(item.title) not in watched_lookup
                ]
            if filtered:
                picked = _pick_weighted_random_candidate(filtered)
                _store_recent_recommendations(update, [picked.title])

                text = _build_random_pick_caption(picked)
                if await _try_send_candidate_with_poster(update, context, picked, text):
                    return

                await _send_panel(
                    update,
                    text,
                    _build_quick_add_keyboard(picked.title, picked.year),
                    parse_mode=ParseMode.HTML,
                )
                return

        blocked_for_ai = list(profile.watched_titles) + recent_titles
        ai_pick = await _ai_single_unseen_pick(
            profile_summary=build_profile_summary(profile),
            blocked_titles=blocked_for_ai,
        )
        if ai_pick:
            title, reason = ai_pick
            if _normalize_title_for_dedupe(title) not in watched_lookup:
                _store_recent_recommendations(update, [title])
                quick_add_keyboard = _build_quick_add_keyboard(
                    title,
                    _extract_year_from_title_label(title),
                )
                ai_text = RANDOM_AI_PICK_TEMPLATE.format(
                    title=html.escape(title),
                    reason=html.escape(reason),
                )
                await _send_panel(
                    update,
                    ai_text,
                    quick_add_keyboard,
                    parse_mode=ParseMode.HTML,
                )
                return

        await _send(update, RANDOM_MSG_UNAVAILABLE)


__all__ = [
    "random_command",
]
