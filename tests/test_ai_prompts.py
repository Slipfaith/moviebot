"""Unit tests for AI prompt builders."""

from __future__ import annotations

import unittest

from bot.ai_prompts import (
    AI_REC_OUTPUT_RULES,
    AI_REC_OUTPUT_RULES_QUERY,
    AI_REC_RECENT_TITLES_PREFIX,
    build_ai_recommendation_prompt,
)


class AiPromptsTests(unittest.TestCase):
    def test_build_prompt_includes_required_blocks(self) -> None:
        prompt = build_ai_recommendation_prompt(
            prompt="Найди похожее на Interstellar",
            profile_summary="liked sci-fi",
            candidates_summary="Interstellar 2",
            recent_titles=[],
        )
        self.assertIn("User request:", prompt)
        self.assertIn("Taste profile from Google Sheets:", prompt)
        self.assertIn("TMDB candidate pool:", prompt)
        self.assertIn("Дикая карта:", prompt)
        self.assertIn("Year must be 2000 or newer.", prompt)
        self.assertIn(AI_REC_OUTPUT_RULES, prompt)

    def test_build_prompt_strict_query_mode_uses_query_rules(self) -> None:
        prompt = build_ai_recommendation_prompt(
            prompt="5 лучших фильмов про выживание на острове",
            profile_summary="liked sci-fi",
            candidates_summary="not used",
            recent_titles=[],
            strict_query=True,
        )
        self.assertIn("fulfill the exact user request", prompt)
        self.assertIn("Ignore any candidate that does not match the request topic.", prompt)
        self.assertIn("Year must be 2000 or newer.", prompt)
        self.assertIn(AI_REC_OUTPUT_RULES_QUERY, prompt)
        self.assertNotIn("Then heading 'Дикая карта:'", prompt)

    def test_build_prompt_adds_recent_titles_block(self) -> None:
        prompt = build_ai_recommendation_prompt(
            prompt="anything",
            profile_summary="profile",
            candidates_summary="candidates",
            recent_titles=["A", "B"],
        )
        self.assertIn(AI_REC_RECENT_TITLES_PREFIX, prompt)
        self.assertIn("A, B", prompt)


if __name__ == "__main__":
    unittest.main()
