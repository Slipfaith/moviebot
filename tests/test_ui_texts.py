"""Unit tests for shared UI text constants."""

from __future__ import annotations

import unittest

from bot.commands import (
    COMMAND_ADD,
    COMMAND_AI,
    COMMAND_FIND,
    COMMAND_HELP,
    COMMAND_MENU,
    COMMAND_OWNER,
    COMMAND_RANDOM,
    COMMAND_SEARCH,
    slash,
)
from bot.ui_texts import (
    ADD_FLOW_ERROR_MISSING_ENTRY_TEMPLATE,
    ADD_FLOW_MSG_CANCELLED,
    ADD_FLOW_MSG_OFFLINE_SAVED,
    ADD_FLOW_MSG_SAVED,
    ADD_FLOW_PROMPT_COMMENT,
    ADD_FLOW_PROMPT_GENRE,
    ADD_FLOW_PROMPT_GENRE_INVALID,
    ADD_FLOW_PROMPT_OWNER,
    ADD_FLOW_PROMPT_RATING,
    ADD_FLOW_PROMPT_RATING_INVALID,
    ADD_FLOW_PROMPT_RECOMMENDATION,
    ADD_FLOW_PROMPT_TITLE,
    ADD_FLOW_PROMPT_TYPE,
    ADD_FLOW_PROMPT_YEAR,
    ADD_FLOW_PROMPT_YEAR_INVALID,
    AI_MSG_GEMINI_BLOCKED,
    AI_MSG_GEMINI_NOT_CONFIGURED,
    AI_MSG_GEMINI_NO_RESPONSE,
    AI_MSG_GEMINI_TEMP_UNAVAILABLE,
    AI_MSG_USAGE_TEMPLATE,
    AI_HELP_HINT_TEXT,
    BUTTON_TOKEN_USAGE,
    BUTTON_TOKEN_USAGE_RESET,
    LIB_FIND_NOT_FOUND_TEXT,
    LIB_FIND_USAGE_TEXT,
    LIB_OWNER_USAGE_TEXT,
    LIB_SEARCH_NOT_FOUND_TEMPLATE,
    LIB_SEARCH_USAGE_TEXT,
    PHOTO_QUICK_ADD_TEMPLATE,
    QUICK_BUTTONS_HINT_TEXT,
    SEARCH_GENRE_HINT_TEXT,
    SEARCH_TITLE_HINT_TEXT,
    TOKEN_USAGE_BACKUP_LABEL,
    TOKEN_USAGE_FILE_LABEL,
    TOKEN_USAGE_HEADER,
    TOKEN_USAGE_PERSISTENCE_NOTE,
    TOKEN_USAGE_RESET_NOTE,
    UNKNOWN_TEXT_GUIDE,
    VOICE_ADD_MSG_INCOMPLETE_TEMPLATE,
    VOICE_ADD_MSG_CLARIFY_TEMPLATE,
    VOICE_ADD_MSG_NEEDS_MISTRAL_KEY,
    VOICE_ADD_MSG_PARSE_FAILED,
    VOICE_ADD_MSG_RECOGNIZED_TEMPLATE,
    VOICE_ADD_MSG_TRANSCRIBE_FAILED,
    VOICE_ADD_BTN_CLARIFY_TEXT,
    VOICE_ADD_BTN_CLARIFY_VOICE,
    VOICE_ADD_BTN_CLARIFY_CANCEL,
)


class UiTextsTests(unittest.TestCase):
    def test_command_hints_use_slash_commands(self) -> None:
        self.assertIn(slash(COMMAND_FIND), SEARCH_GENRE_HINT_TEXT)
        self.assertIn(slash(COMMAND_SEARCH), SEARCH_TITLE_HINT_TEXT)
        self.assertIn(slash(COMMAND_AI), AI_HELP_HINT_TEXT)

    def test_unknown_guide_mentions_menu_and_help(self) -> None:
        self.assertIn(slash(COMMAND_MENU), UNKNOWN_TEXT_GUIDE)
        self.assertIn(slash(COMMAND_HELP), UNKNOWN_TEXT_GUIDE)
        self.assertTrue(QUICK_BUTTONS_HINT_TEXT)

    def test_library_texts_use_declared_commands(self) -> None:
        self.assertIn(slash(COMMAND_FIND), LIB_FIND_USAGE_TEXT)
        self.assertIn(slash(COMMAND_OWNER), LIB_OWNER_USAGE_TEXT)
        self.assertIn(slash(COMMAND_SEARCH), LIB_SEARCH_USAGE_TEXT)
        self.assertIn(slash(COMMAND_FIND), LIB_FIND_NOT_FOUND_TEXT)
        self.assertIn(slash(COMMAND_SEARCH), LIB_FIND_NOT_FOUND_TEXT)
        self.assertIn(slash(COMMAND_RANDOM), LIB_FIND_NOT_FOUND_TEXT)
        self.assertIn(slash(COMMAND_FIND), LIB_SEARCH_NOT_FOUND_TEMPLATE)
        self.assertIn(slash(COMMAND_RANDOM), LIB_SEARCH_NOT_FOUND_TEMPLATE)

    def test_photo_quick_add_template_uses_add_command(self) -> None:
        self.assertIn(slash(COMMAND_ADD), PHOTO_QUICK_ADD_TEMPLATE)

    def test_add_flow_texts_are_present(self) -> None:
        for value in (
            ADD_FLOW_PROMPT_TITLE,
            ADD_FLOW_PROMPT_YEAR,
            ADD_FLOW_PROMPT_YEAR_INVALID,
            ADD_FLOW_PROMPT_GENRE,
            ADD_FLOW_PROMPT_GENRE_INVALID,
            ADD_FLOW_PROMPT_RATING,
            ADD_FLOW_PROMPT_RATING_INVALID,
            ADD_FLOW_PROMPT_COMMENT,
            ADD_FLOW_PROMPT_TYPE,
            ADD_FLOW_PROMPT_RECOMMENDATION,
            ADD_FLOW_PROMPT_OWNER,
            ADD_FLOW_MSG_OFFLINE_SAVED,
            ADD_FLOW_MSG_SAVED,
            ADD_FLOW_MSG_CANCELLED,
        ):
            self.assertTrue(value)
        self.assertIn(slash(COMMAND_ADD), ADD_FLOW_ERROR_MISSING_ENTRY_TEMPLATE.format(add_command=slash(COMMAND_ADD)))

    def test_ai_texts_are_present(self) -> None:
        self.assertTrue(AI_MSG_GEMINI_NOT_CONFIGURED)
        self.assertIn("MISTRAL", AI_MSG_GEMINI_NOT_CONFIGURED.upper())
        self.assertTrue(AI_MSG_GEMINI_BLOCKED)
        self.assertTrue(AI_MSG_GEMINI_TEMP_UNAVAILABLE)
        self.assertTrue(AI_MSG_GEMINI_NO_RESPONSE)
        self.assertIn(
            slash(COMMAND_AI),
            AI_MSG_USAGE_TEMPLATE.format(ai_usage=slash(COMMAND_AI, " <your request>")),
        )

    def test_voice_add_texts_are_present(self) -> None:
        self.assertTrue(VOICE_ADD_MSG_NEEDS_MISTRAL_KEY)
        self.assertTrue(VOICE_ADD_MSG_TRANSCRIBE_FAILED)
        self.assertTrue(VOICE_ADD_MSG_PARSE_FAILED)
        self.assertIn("{transcript}", VOICE_ADD_MSG_INCOMPLETE_TEMPLATE)
        self.assertIn("{transcript}", VOICE_ADD_MSG_RECOGNIZED_TEMPLATE)
        self.assertIn("{missing}", VOICE_ADD_MSG_CLARIFY_TEMPLATE)
        self.assertTrue(VOICE_ADD_BTN_CLARIFY_TEXT)
        self.assertTrue(VOICE_ADD_BTN_CLARIFY_VOICE)
        self.assertTrue(VOICE_ADD_BTN_CLARIFY_CANCEL)

    def test_token_usage_texts_are_present(self) -> None:
        self.assertTrue(BUTTON_TOKEN_USAGE)
        self.assertTrue(BUTTON_TOKEN_USAGE_RESET)
        self.assertTrue(TOKEN_USAGE_HEADER)
        self.assertTrue(TOKEN_USAGE_RESET_NOTE)
        self.assertTrue(TOKEN_USAGE_PERSISTENCE_NOTE)
        self.assertTrue(TOKEN_USAGE_FILE_LABEL)
        self.assertTrue(TOKEN_USAGE_BACKUP_LABEL)


if __name__ == "__main__":
    unittest.main()
