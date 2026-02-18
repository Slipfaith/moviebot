"""Unit tests for poster-edit helpers in add-flow UI."""

from __future__ import annotations

import unittest

from bot.callback_ids import (
    ADD_FLOW_CONFIRM_CANCEL,
    ADD_FLOW_CONFIRM_SAVE,
    ADD_FLOW_EDIT_BACK,
    ADD_FLOW_EDIT_OPEN_OWNER,
    ADD_FLOW_EDIT_OPEN_REC,
    ADD_FLOW_EDIT_OPEN_TYPE,
    ADD_FLOW_EDIT_TEXT_PREFIX,
)
from bot.handlers_add_flow_ui import (
    _poster_edit_keyboard,
    _poster_edit_owner_keyboard,
    _poster_edit_preview,
    _poster_edit_recommendation_keyboard,
    _poster_edit_type_keyboard,
)


def _callback_data(markup) -> list[str]:
    return [
        str(button.callback_data)
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data
    ]


class AddFlowPosterEditorUiTests(unittest.TestCase):
    def test_poster_edit_keyboard_contains_required_actions(self) -> None:
        markup = _poster_edit_keyboard(
            {
                "film": "The Matrix",
                "year": "1999",
                "genre": "Sci-Fi",
                "rating": "9",
                "comment": "Классика",
                "type": "фильм",
                "recommendation": "рекомендую",
                "owner": "муж",
            }
        )
        callbacks = _callback_data(markup)
        self.assertIn(f"{ADD_FLOW_EDIT_TEXT_PREFIX}film", callbacks)
        self.assertIn(f"{ADD_FLOW_EDIT_TEXT_PREFIX}year", callbacks)
        self.assertIn(f"{ADD_FLOW_EDIT_TEXT_PREFIX}genre", callbacks)
        self.assertIn(f"{ADD_FLOW_EDIT_TEXT_PREFIX}rating", callbacks)
        self.assertIn(f"{ADD_FLOW_EDIT_TEXT_PREFIX}comment", callbacks)
        self.assertIn(ADD_FLOW_EDIT_OPEN_TYPE, callbacks)
        self.assertIn(ADD_FLOW_EDIT_OPEN_REC, callbacks)
        self.assertIn(ADD_FLOW_EDIT_OPEN_OWNER, callbacks)
        self.assertIn(ADD_FLOW_CONFIRM_SAVE, callbacks)
        self.assertIn(ADD_FLOW_CONFIRM_CANCEL, callbacks)

    def test_choice_keyboards_include_back_button(self) -> None:
        for markup in (
            _poster_edit_type_keyboard(),
            _poster_edit_recommendation_keyboard(),
            _poster_edit_owner_keyboard(),
        ):
            self.assertIn(ADD_FLOW_EDIT_BACK, _callback_data(markup))

    def test_poster_edit_preview_escapes_html_and_renders_note(self) -> None:
        text = _poster_edit_preview(
            {
                "film": "<Matrix>",
                "year": "1999",
                "genre": "Sci-Fi",
                "rating": "9",
                "comment": "Neo & Trinity",
                "type": "фильм",
                "recommendation": "рекомендую",
                "owner": "муж",
            },
            note="проверьте <год>",
        )
        self.assertIn("&lt;Matrix&gt;", text)
        self.assertIn("Neo &amp; Trinity", text)
        self.assertIn("&lt;год&gt;", text)


if __name__ == "__main__":
    unittest.main()
