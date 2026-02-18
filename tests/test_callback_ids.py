"""Unit tests for callback-data helpers."""

from __future__ import annotations

import unittest

from bot.callback_ids import (
    ADD_FLOW_EDIT_BACK,
    ADD_FLOW_EDIT_OPEN_OWNER,
    ADD_FLOW_EDIT_OPEN_REC,
    ADD_FLOW_EDIT_OPEN_TYPE,
    ADD_FLOW_EDIT_SET_OWNER_PREFIX,
    ADD_FLOW_EDIT_SET_REC_PREFIX,
    ADD_FLOW_EDIT_SET_TYPE_PREFIX,
    ADD_FLOW_EDIT_TEXT_PREFIX,
    ADD_FLOW_VOICE_CANCEL,
    ADD_FLOW_VOICE_CLARIFY_TEXT,
    ADD_FLOW_VOICE_CLARIFY_VOICE,
    PAGE_PREFIX,
    PATTERN_ADD_FLOW_EDIT_BACK,
    PATTERN_ADD_FLOW_EDIT_OPEN,
    PATTERN_ADD_FLOW_EDIT_SET_OWNER,
    PATTERN_ADD_FLOW_EDIT_SET_REC,
    PATTERN_ADD_FLOW_EDIT_SET_TYPE,
    PATTERN_ADD_FLOW_EDIT_TEXT,
    PATTERN_ADD_FLOW_VOICE_CANCEL,
    PATTERN_ADD_FLOW_VOICE_CLARIFY_HINT,
    TOKEN_USAGE,
    TOKEN_USAGE_RESET,
    WINNER_MONTH,
    page_callback,
    parse_page_callback,
    parse_winner_month_offset,
    winner_month_callback,
)


class CallbackIdsTests(unittest.TestCase):
    def test_winner_month_roundtrip(self) -> None:
        data = winner_month_callback(-2)
        self.assertEqual(data, "winner_month:-2")
        self.assertEqual(parse_winner_month_offset(data), -2)
        self.assertEqual(parse_winner_month_offset(WINNER_MONTH), 0)

    def test_page_roundtrip(self) -> None:
        data = page_callback("top", 3)
        self.assertTrue(data.startswith(PAGE_PREFIX))
        self.assertEqual(parse_page_callback(data), ("top", 3))

    def test_page_parse_invalid(self) -> None:
        self.assertIsNone(parse_page_callback("noop"))
        self.assertIsNone(parse_page_callback("page:onlytwo"))
        self.assertEqual(parse_page_callback("page:list:not_number"), ("list", 0))

    def test_voice_clarify_callbacks_have_expected_format(self) -> None:
        self.assertRegex(ADD_FLOW_VOICE_CLARIFY_TEXT, PATTERN_ADD_FLOW_VOICE_CLARIFY_HINT)
        self.assertRegex(ADD_FLOW_VOICE_CLARIFY_VOICE, PATTERN_ADD_FLOW_VOICE_CLARIFY_HINT)
        self.assertRegex(ADD_FLOW_VOICE_CANCEL, PATTERN_ADD_FLOW_VOICE_CANCEL)

    def test_poster_editor_callbacks_have_expected_format(self) -> None:
        self.assertRegex(f"{ADD_FLOW_EDIT_TEXT_PREFIX}film", PATTERN_ADD_FLOW_EDIT_TEXT)
        self.assertRegex(ADD_FLOW_EDIT_OPEN_TYPE, PATTERN_ADD_FLOW_EDIT_OPEN)
        self.assertRegex(ADD_FLOW_EDIT_OPEN_REC, PATTERN_ADD_FLOW_EDIT_OPEN)
        self.assertRegex(ADD_FLOW_EDIT_OPEN_OWNER, PATTERN_ADD_FLOW_EDIT_OPEN)
        self.assertRegex(f"{ADD_FLOW_EDIT_SET_TYPE_PREFIX}film", PATTERN_ADD_FLOW_EDIT_SET_TYPE)
        self.assertRegex(f"{ADD_FLOW_EDIT_SET_REC_PREFIX}recommend", PATTERN_ADD_FLOW_EDIT_SET_REC)
        self.assertRegex(f"{ADD_FLOW_EDIT_SET_OWNER_PREFIX}husband", PATTERN_ADD_FLOW_EDIT_SET_OWNER)
        self.assertRegex(ADD_FLOW_EDIT_BACK, PATTERN_ADD_FLOW_EDIT_BACK)

    def test_token_usage_callbacks_are_stable(self) -> None:
        self.assertEqual(TOKEN_USAGE, "token_usage")
        self.assertEqual(TOKEN_USAGE_RESET, "token_usage_reset")


if __name__ == "__main__":
    unittest.main()
