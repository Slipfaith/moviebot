"""Unit tests for normalization helpers."""

from __future__ import annotations

import unittest

from core.normalization import normalize_owner, normalize_recommendation, normalize_type


class NormalizationTests(unittest.TestCase):
    def test_normalize_type_supports_russian_and_english(self) -> None:
        self.assertEqual(normalize_type("сериал"), "сериал")
        self.assertEqual(normalize_type("series"), "сериал")
        self.assertEqual(normalize_type("movie"), "фильм")

    def test_normalize_recommendation_supports_callback_tokens(self) -> None:
        self.assertEqual(normalize_recommendation("recommend"), "рекомендую")
        self.assertEqual(normalize_recommendation("ok"), "можно посмотреть")
        self.assertEqual(normalize_recommendation("skip"), "в топку")

    def test_normalize_owner_supports_russian_and_english(self) -> None:
        self.assertEqual(normalize_owner("муж"), "муж")
        self.assertEqual(normalize_owner("husband"), "муж")
        self.assertEqual(normalize_owner("wife"), "жена")
        self.assertEqual(normalize_owner("unknown"), "")


if __name__ == "__main__":
    unittest.main()
