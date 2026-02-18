"""Unit tests for photo handler translation helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from bot.handlers_photo import _translate_omdb_fields_to_russian
from core.gemini import GeminiError


class HandlersPhotoTests(unittest.TestCase):
    def test_translate_omdb_fields_skips_when_text_is_already_russian(self) -> None:
        with patch("bot.handlers_photo.generate_gemini_reply") as mocked_translate:
            genre, plot = _translate_omdb_fields_to_russian(
                "боевик, драма",
                "Русский сюжет без перевода.",
            )
        mocked_translate.assert_not_called()
        self.assertEqual(genre, "боевик, драма")
        self.assertEqual(plot, "Русский сюжет без перевода.")

    def test_translate_omdb_fields_uses_gemini_and_parses_json(self) -> None:
        with patch(
            "bot.handlers_photo.generate_gemini_reply",
            return_value=(
                '{"genre_ru":"Боевик, Криминал, Драма", '
                '"plot_ru":"Герой расследует убийство и раскрывает заговор."}'
            ),
        ):
            genre, plot = _translate_omdb_fields_to_russian(
                "Action, Crime, Drama",
                "A hero investigates a murder and uncovers a conspiracy.",
            )
        self.assertEqual(genre, "Боевик, Криминал, Драма")
        self.assertEqual(plot, "Герой расследует убийство и раскрывает заговор.")

    def test_translate_omdb_fields_returns_source_on_gemini_error(self) -> None:
        with patch(
            "bot.handlers_photo.generate_gemini_reply",
            side_effect=GeminiError("temporary unavailable"),
        ):
            genre, plot = _translate_omdb_fields_to_russian(
                "Action, Crime, Drama",
                "A hero investigates a murder.",
            )
        self.assertEqual(genre, "Action, Crime, Drama")
        self.assertEqual(plot, "A hero investigates a murder.")


if __name__ == "__main__":
    unittest.main()
