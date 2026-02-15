"""Unit tests for user-visible handler texts."""

from __future__ import annotations

import unittest

from bot.commands import COMMAND_ADD, HELP_COMMAND_ORDER
from bot.handlers_texts import ADD_USAGE_TEXT, HELP_TEXT


class HandlerTextsTests(unittest.TestCase):
    def test_help_text_contains_declared_commands(self) -> None:
        for command in HELP_COMMAND_ORDER:
            self.assertIn(f"/{command}", HELP_TEXT)

    def test_add_usage_uses_add_command_constant(self) -> None:
        self.assertIn(f"/{COMMAND_ADD} ", ADD_USAGE_TEXT)
        self.assertIn(f"отправить /{COMMAND_ADD}", ADD_USAGE_TEXT)


if __name__ == "__main__":
    unittest.main()
