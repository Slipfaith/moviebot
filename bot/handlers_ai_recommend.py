"""AI text recommendation handlers."""

from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.ai_prompts import build_ai_recommendation_prompt
from bot.commands import COMMAND_AI, slash
from bot.handlers_ai_helpers import (
    _build_ai_cache_key,
    _build_quick_add_keyboard_from_formatted,
    _filter_candidates_by_min_year,
    _filter_recent_candidates,
    _format_ai_answer_for_telegram,
    _get_ai_cached_response,
    _store_ai_cached_response,
)
from bot.handlers_cache import (
    _get_cached_profile,
    _get_recent_recommendations,
    _store_cached_profile,
    _store_recent_recommendations,
)
from bot.handlers_sheet import _safe_fetch_records
from bot.handlers_transport import _send, _send_panel, _typing
from bot.ui_texts import (
    AI_MSG_GEMINI_BLOCKED,
    AI_MSG_GEMINI_NOT_CONFIGURED,
    AI_MSG_GEMINI_NO_RESPONSE,
    AI_MSG_GEMINI_TEMP_UNAVAILABLE,
    AI_MSG_USAGE_TEMPLATE,
)
from core.ai_text import AITextError, generate_text_reply, is_text_ai_enabled
from core.recommendations import (
    build_candidates_summary,
    build_profile_summary,
    build_taste_profile,
    collect_tmdb_candidates,
    tmdb_enabled,
)

logger = logging.getLogger(__name__)


async def _run_ai_recommendation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prompt: str,
    *,
    use_response_cache: bool = True,
    avoid_recent_titles: bool = False,
    include_tmdb_candidates: bool = True,
    strict_query: bool = False,
    temperature: float = 0.4,
    max_output_tokens: int = 512,
) -> None:
    if not is_text_ai_enabled():
        await _send(update, AI_MSG_GEMINI_NOT_CONFIGURED)
        return

    async with _typing(update, context):
        records = await _safe_fetch_records(update)
        if records is None:
            return

        profile = _get_cached_profile()
        if profile is None:
            profile = build_taste_profile(records)
            _store_cached_profile(profile)
        profile_summary = build_profile_summary(profile)
        recent_titles = _get_recent_recommendations(update) if avoid_recent_titles else []
        ai_cache_key = _build_ai_cache_key(prompt, profile_summary)

        if use_response_cache:
            cached = _get_ai_cached_response(ai_cache_key)
            if cached:
                cached_keyboard, _ = _build_quick_add_keyboard_from_formatted(cached)
                if cached_keyboard:
                    await _send_panel(update, cached, cached_keyboard, parse_mode=ParseMode.HTML)
                else:
                    await _send(update, cached, parse_mode=ParseMode.HTML)
                return

        candidates_summary = "TMDB candidates were not used."
        if include_tmdb_candidates and tmdb_enabled():
            tmdb_candidates = await asyncio.to_thread(collect_tmdb_candidates, profile)
            tmdb_candidates = _filter_candidates_by_min_year(tmdb_candidates)
            tmdb_candidates = _filter_recent_candidates(tmdb_candidates, recent_titles)
            candidates_summary = build_candidates_summary(tmdb_candidates)

        prompt_with_context = build_ai_recommendation_prompt(
            prompt=prompt,
            profile_summary=profile_summary,
            candidates_summary=candidates_summary,
            recent_titles=recent_titles,
            strict_query=strict_query,
        )

        try:
            answer = await asyncio.to_thread(
                generate_text_reply,
                prompt_with_context,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
        except AITextError as exc:
            logger.error("AI ERROR: %s %s", type(exc).__name__, exc)
            reason = str(exc).lower()
            if "blocked" in reason:
                await _send(update, AI_MSG_GEMINI_BLOCKED)
            else:
                await _send(update, AI_MSG_GEMINI_TEMP_UNAVAILABLE)
            return
        except Exception as exc:
            logger.error("AI ERROR: %s %s", type(exc).__name__, exc)
            await _send(update, AI_MSG_GEMINI_NO_RESPONSE)
            return

        formatted = _format_ai_answer_for_telegram(answer)
        if len(formatted) > 3900:
            formatted = formatted[:3900].rstrip() + "..."
        quick_add_keyboard, formatted_titles = _build_quick_add_keyboard_from_formatted(formatted)

        if use_response_cache:
            _store_ai_cached_response(ai_cache_key, formatted)
        if avoid_recent_titles:
            _store_recent_recommendations(update, formatted_titles)

        if quick_add_keyboard:
            await _send_panel(update, formatted, quick_add_keyboard, parse_mode=ParseMode.HTML)
        else:
            await _send(update, formatted, parse_mode=ParseMode.HTML)


async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = " ".join(context.args).strip() if context.args else ""
    if not prompt:
        await _send(
            update,
            AI_MSG_USAGE_TEMPLATE.format(ai_usage=slash(COMMAND_AI, " <your request>")),
        )
        return
    await _run_ai_recommendation(
        update,
        context,
        prompt,
        use_response_cache=False,
        include_tmdb_candidates=False,
        strict_query=True,
        temperature=0.25,
        max_output_tokens=900,
    )


async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    custom_hint = " ".join(context.args).strip() if context.args else ""
    if custom_hint:
        prompt = f"Recommend movies for this preference: {custom_hint}"
    else:
        prompt = "Recommend new movies based on my watch history and ratings."
    await _run_ai_recommendation(
        update,
        context,
        prompt,
        use_response_cache=False,
        avoid_recent_titles=True,
    )


__all__ = [
    "_run_ai_recommendation",
    "ai_command",
    "recommend_command",
]
