"""Unit tests for random recommendation helpers."""

from __future__ import annotations

import unittest

from bot.handlers_ai_random import _extract_omdb_poster_url


class HandlersAIRandomTests(unittest.TestCase):
    def test_extract_omdb_poster_url_returns_valid_url(self) -> None:
        url = _extract_omdb_poster_url({"Poster": "https://img.omdbapi.com/poster.jpg"})
        self.assertEqual(url, "https://img.omdbapi.com/poster.jpg")

    def test_extract_omdb_poster_url_ignores_na(self) -> None:
        self.assertEqual(_extract_omdb_poster_url({"Poster": "N/A"}), "")
        self.assertEqual(_extract_omdb_poster_url({"Poster": ""}), "")
        self.assertEqual(_extract_omdb_poster_url(None), "")


if __name__ == "__main__":
    unittest.main()
