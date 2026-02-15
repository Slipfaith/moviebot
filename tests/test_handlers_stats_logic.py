"""Unit tests for stats text builders."""

from __future__ import annotations

import unittest

from bot.handlers_stats_logic import build_token_usage_text


class HandlersStatsLogicTests(unittest.TestCase):
    def test_build_token_usage_text_contains_provider_sections(self) -> None:
        stats = {
            "providers": {
                "gemini": {"input_tokens": 1000, "output_tokens": 250, "requests": 7},
                "mistral": {"input_tokens": 600, "output_tokens": 150, "requests": 4},
            },
            "totals": {"input_tokens": 1600, "output_tokens": 400, "requests": 11},
        }
        text = build_token_usage_text(
            stats,
            file_path="C:/app/moviebot_token_usage.json",
            backup_dir="C:/app/moviebot_token_usage_backups",
        )
        self.assertIn("Gemini: in 1 000, out 250, запросов 7", text)
        self.assertIn("Mistral: in 600, out 150, запросов 4", text)
        self.assertIn("Итого: in 1 600, out 400, запросов 11", text)
        self.assertIn("moviebot_token_usage.json", text)
        self.assertIn("moviebot_token_usage_backups", text)


if __name__ == "__main__":
    unittest.main()
