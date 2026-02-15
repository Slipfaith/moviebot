"""Unit tests for voice-driven add-flow parsing."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from bot.handlers_add_flow_voice import (
    _build_add_payload_from_structured,
    _extract_voice_entry,
    _infer_comment_from_transcript,
)


class AddFlowVoiceTests(unittest.TestCase):
    def test_build_payload_normalizes_fields(self) -> None:
        payload = _build_add_payload_from_structured(
            {
                "title": "The Matrix",
                "year": "1999",
                "genre": "Sci-Fi",
                "rating": 8.7,
                "comment": "классика",
                "type": "series",
                "recommendation": "recommend",
                "owner": "husband",
            }
        )
        self.assertIn("The Matrix;1999;Sci-Fi;8.7;классика;сериал;рекомендую;муж", payload)

    def test_extract_voice_entry_from_ai_json(self) -> None:
        with patch(
            "bot.handlers_add_flow_voice.generate_mistral_reply",
            return_value=(
                '{"film":"Интерстеллар","year":"2014","genre":"фантастика",'
                '"rating":"9","comment":"космос","type":"film",'
                '"recommendation":"рекомендую","owner":"жена"}'
            ),
        ):
            entry = _extract_voice_entry("интерстеллар 2014")
        self.assertIsNotNone(entry)
        if entry is not None:
            self.assertEqual(entry["film"], "Интерстеллар")
            self.assertEqual(entry["year"], "2014")
            self.assertEqual(entry["genre"], "фантастика")
            self.assertEqual(entry["rating"], "9")
            self.assertEqual(entry["type"], "фильм")
            self.assertEqual(entry["recommendation"], "рекомендую")
            self.assertEqual(entry["owner"], "жена")

    def test_extract_voice_entry_returns_none_if_json_not_found(self) -> None:
        with patch(
            "bot.handlers_add_flow_voice.generate_mistral_reply",
            return_value="Просто текст без JSON",
        ):
            entry = _extract_voice_entry("test")
        self.assertIsNone(entry)

    def test_infer_comment_from_transcript_with_marker_phrase(self) -> None:
        transcript = (
            "Посмотрел Матрицу. Поставь десять. "
            "Нео офигел там. Вот это будет комментарий мой."
        )
        comment = _infer_comment_from_transcript(transcript)
        self.assertEqual(comment, "Нео офигел там")

    def test_extract_voice_entry_autofills_year_genre_and_comment(self) -> None:
        transcript = (
            "А, короче, посмотрел фильм, называется Матрица. "
            "Десяточку поставь. И не знаю, ну, Нео офигел там. "
            "Вот это будет комментарий мой. Ну, и муж, конечно."
        )
        with patch(
            "bot.handlers_add_flow_voice.generate_mistral_reply",
            return_value=(
                '{"film":"Матрица","year":"","genre":"",'
                '"rating":"10","comment":"","type":"film",'
                '"recommendation":"", "owner":""}'
            ),
        ), patch(
            "bot.handlers_add_flow_voice.lookup_omdb_details",
            return_value={"Year": "1999", "Genre": "Action, Sci-Fi", "Type": "movie"},
        ):
            entry = _extract_voice_entry(transcript)

        self.assertIsNotNone(entry)
        if entry is not None:
            self.assertEqual(entry["film"], "Матрица")
            self.assertEqual(entry["year"], "1999")
            self.assertEqual(entry["genre"], "Action, Sci-Fi")
            self.assertEqual(entry["rating"], "10")
            self.assertEqual(entry["comment"], "Нео офигел там")
            self.assertEqual(entry["owner"], "муж")


if __name__ == "__main__":
    unittest.main()
