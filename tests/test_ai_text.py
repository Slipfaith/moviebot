"""Unit tests for unified AI text provider."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from core.ai_text import AITextError, generate_text_reply
from core.gemini import GeminiError


class AITextTests(unittest.TestCase):
    def test_uses_gemini_when_available(self) -> None:
        with (
            patch("core.ai_text.is_gemini_enabled", return_value=True),
            patch("core.ai_text.generate_gemini_reply", return_value="gemini ok") as gemini_mock,
            patch("core.ai_text.is_mistral_enabled", return_value=True),
            patch("core.ai_text.generate_mistral_reply", return_value="mistral ok") as mistral_mock,
        ):
            result = generate_text_reply("hello")
        self.assertEqual(result, "gemini ok")
        gemini_mock.assert_called_once()
        mistral_mock.assert_not_called()

    def test_falls_back_to_mistral_if_gemini_fails(self) -> None:
        with (
            patch("core.ai_text.is_gemini_enabled", return_value=True),
            patch(
                "core.ai_text.generate_gemini_reply",
                side_effect=GeminiError("503"),
            ),
            patch("core.ai_text.is_mistral_enabled", return_value=True),
            patch("core.ai_text.generate_mistral_reply", return_value="mistral ok"),
        ):
            result = generate_text_reply("hello")
        self.assertEqual(result, "mistral ok")

    def test_raises_if_no_provider_enabled(self) -> None:
        with (
            patch("core.ai_text.is_gemini_enabled", return_value=False),
            patch("core.ai_text.is_mistral_enabled", return_value=False),
        ):
            with self.assertRaises(AITextError):
                generate_text_reply("hello")


if __name__ == "__main__":
    unittest.main()
