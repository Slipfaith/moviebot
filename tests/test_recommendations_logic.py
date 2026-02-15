"""Unit tests for recommendation scoring helpers."""

from __future__ import annotations

import unittest

from core.recommendations import (
    _pick_best_seed_item,
    _reason_from_shared_genres,
    _shared_preferred_genres,
)


class RecommendationsLogicTests(unittest.TestCase):
    def test_reason_prefers_shared_genres(self) -> None:
        reason = _reason_from_shared_genres(["фантастика", "триллер"])
        self.assertIn("совпадают жанры", reason)
        self.assertIn("фантастика", reason)

    def test_shared_preferred_genres_extracts_intersection(self) -> None:
        shared = _shared_preferred_genres(
            [878, 28, 35],
            {878: "фантастика", 28: "боевик", 35: "комедия"},
            {"фантастика", "триллер"},
        )
        self.assertEqual(shared, ["фантастика"])

    def test_pick_best_seed_item_prefers_title_year_match(self) -> None:
        results = [
            {"id": 1, "title": "Матрица: Перезагрузка", "release_date": "2003-05-15"},
            {"id": 2, "title": "Матрица", "release_date": "1999-03-31", "vote_count": 1000},
        ]
        best = _pick_best_seed_item(results, seed_title="Матрица", seed_year=1999)
        self.assertIsNotNone(best)
        if best is not None:
            self.assertEqual(best.get("id"), 2)


if __name__ == "__main__":
    unittest.main()
