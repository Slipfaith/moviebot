"""Prompt builders for AI recommendation flows."""

from __future__ import annotations

AI_REC_TASK_PREFIX_PROFILE = (
    "Task: recommend NEW movies based on watch history and ratings.\n"
    "NEW means movie title must be absent in watched list.\n\n"
)
AI_REC_TASK_PREFIX_QUERY = (
    "Task: fulfill the exact user request for movie recommendations.\n"
    "Primary goal is semantic relevance to the request.\n"
    "Use taste profile only as a secondary personalization hint.\n"
    "Suggested movie title must be absent in watched list.\n"
    "Ignore any candidate that does not match the request topic.\n\n"
)
AI_REC_RECENT_TITLES_PREFIX = "Do NOT suggest these titles (already recently recommended):\n"
AI_REC_PROFILE_PREFIX = "Taste profile from Google Sheets:\n"
AI_REC_CANDIDATES_PREFIX = "TMDB candidate pool:\n"
AI_REC_CANDIDATE_LOCK_RULE = (
    "If candidate pool is provided and non-empty, select recommendations only from that pool.\n"
    "Do not invent or substitute titles outside the pool.\n"
)
AI_REC_OUTPUT_RULES = (
    "Output format requirements:\n"
    "1) Russian language only.\n"
    "2) Exactly 5-8 numbered recommendations.\n"
    "3) Every item must be: <Title (Year)> - <one short reason>.\n"
    "4) Year must be 2000 or newer.\n"
    "5) Then heading 'Дикая карта:' and one extra item with reason.\n"
    "6) No markdown syntax (** or __)."
)
AI_REC_OUTPUT_RULES_QUERY = (
    "Output format requirements:\n"
    "1) Russian language only.\n"
    "2) Follow user request strictly by theme and constraints.\n"
    "3) If user asked for N movies, return exactly N (3..10). If N is absent, return exactly 5.\n"
    "4) Year must be 2000 or newer.\n"
    "5) Every item must be: <Title (Year)> - <brief plot detail> | <why it matches request>.\n"
    "6) Use real, well-known movies only; do not invent titles.\n"
    "7) No wildcard section and no markdown syntax (** or __)."
)


def build_ai_recommendation_prompt(
    prompt: str,
    profile_summary: str,
    candidates_summary: str,
    recent_titles: list[str],
    *,
    strict_query: bool = False,
    restrict_to_candidates: bool = False,
) -> str:
    """Build a full Gemini prompt for recommendation generation."""

    recent_titles_block = ""
    if recent_titles:
        recent_titles_block = (
            AI_REC_RECENT_TITLES_PREFIX
            + ", ".join(recent_titles[:40])
            + "\n\n"
        )

    task_prefix = AI_REC_TASK_PREFIX_QUERY if strict_query else AI_REC_TASK_PREFIX_PROFILE
    output_rules = AI_REC_OUTPUT_RULES_QUERY if strict_query else AI_REC_OUTPUT_RULES
    candidate_lock_rule = AI_REC_CANDIDATE_LOCK_RULE if restrict_to_candidates else ""

    return (
        task_prefix
        + f"User request:\n{prompt}\n\n"
        + recent_titles_block
        + AI_REC_PROFILE_PREFIX
        + f"{profile_summary}\n\n"
        + AI_REC_CANDIDATES_PREFIX
        + f"{candidates_summary}\n\n"
        + candidate_lock_rule
        + output_rules
    )


__all__ = [
    "AI_REC_TASK_PREFIX_PROFILE",
    "AI_REC_TASK_PREFIX_QUERY",
    "AI_REC_RECENT_TITLES_PREFIX",
    "AI_REC_PROFILE_PREFIX",
    "AI_REC_CANDIDATES_PREFIX",
    "AI_REC_CANDIDATE_LOCK_RULE",
    "AI_REC_OUTPUT_RULES",
    "AI_REC_OUTPUT_RULES_QUERY",
    "build_ai_recommendation_prompt",
]
