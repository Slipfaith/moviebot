"""Unit tests for AI helper keyboard generation."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from bot.handlers_ai_helpers import (
    _build_quick_add_keyboard_from_formatted,
    _enrich_formatted_recommendations_with_ratings,
    _format_ai_answer_for_telegram,
)


class HandlersAIHelpersTests(unittest.TestCase):
    def test_build_quick_add_keyboard_from_formatted_creates_buttons_for_each_title(self) -> None:
        formatted = (
            "<b>New Recommendations</b>\n"
            "1. <b>Матрица: Перезагрузка (2003)</b> - reason\n"
            "2. <b>Начало (2010)</b> - reason\n"
            "3. <b>Мементо (2000)</b> - reason\n"
        )
        keyboard, titles = _build_quick_add_keyboard_from_formatted(formatted)
        self.assertIsNotNone(keyboard)
        self.assertEqual(len(titles), 3)
        assert keyboard is not None
        self.assertEqual(len(keyboard.inline_keyboard), 3)
        first_button = keyboard.inline_keyboard[0][0]
        self.assertIn("/add", first_button.switch_inline_query_current_chat or "")
        self.assertIn("Матрица: Перезагрузка;2003", first_button.switch_inline_query_current_chat or "")

    def test_build_quick_add_keyboard_from_formatted_deduplicates_titles(self) -> None:
        formatted = (
            "<b>New Recommendations</b>\n"
            "1. <b>Матрица: Перезагрузка (2003)</b> - reason\n"
            "2. <b>Матрица: Перезагрузка (2003)</b> - reason\n"
        )
        keyboard, titles = _build_quick_add_keyboard_from_formatted(formatted)
        self.assertIsNotNone(keyboard)
        self.assertEqual(len(titles), 1)
        assert keyboard is not None
        self.assertEqual(len(keyboard.inline_keyboard), 1)

    def test_format_ai_answer_filters_out_movies_before_2000(self) -> None:
        answer = (
            "1. Матрица (1999) - киберпанк\n"
            "2. Начало (2010) - сон внутри сна\n"
            "3. Паразиты (2019) - социальный триллер\n"
        )
        formatted = _format_ai_answer_for_telegram(answer)
        self.assertNotIn("Матрица (1999)", formatted)
        self.assertIn("Начало (2010)", formatted)
        self.assertIn("Паразиты (2019)", formatted)

    def test_format_ai_answer_returns_empty_message_when_all_movies_are_old(self) -> None:
        answer = (
            "1. Матрица (1999) - киберпанк\n"
            "2. Семь (1995) - детектив\n"
        )
        formatted = _format_ai_answer_for_telegram(answer)
        self.assertIn("2000+", formatted)
        self.assertNotIn("Матрица (1999)", formatted)
        self.assertNotIn("Семь (1995)", formatted)

    def test_enrich_formatted_recommendations_with_ratings_adds_imdb(self) -> None:
        formatted = (
            "<b>New Recommendations</b>\n"
            "1. <b>Начало (2010)</b> - отличный фантастический триллер\n"
            "2. <b>Паразиты (2019)</b> - напряженная социальная драма\n"
        )

        def _fake_lookup(title: str, year: int | None) -> dict | None:
            if title == "Начало" and year == 2010:
                return {"imdbRating": "8.8"}
            if title == "Паразиты" and year == 2019:
                return {"imdbRating": "8.5"}
            return None

        with patch("bot.handlers_ai_helpers.lookup_omdb_details", side_effect=_fake_lookup):
            enriched = _enrich_formatted_recommendations_with_ratings(formatted)

        self.assertIn("IMDb 8.8/10", enriched)
        self.assertIn("IMDb 8.5/10", enriched)


if __name__ == "__main__":
    unittest.main()
