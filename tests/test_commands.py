"""Unit tests for command declarations."""

from __future__ import annotations

import unittest

from bot import commands


class CommandsTests(unittest.TestCase):
    def test_registry_order_is_unique(self) -> None:
        self.assertEqual(len(commands.REGISTRY_ORDER), len(set(commands.REGISTRY_ORDER)))

    def test_add_and_cancel_exist(self) -> None:
        self.assertIn(commands.COMMAND_ADD, commands.ALL_COMMANDS)
        self.assertIn(commands.COMMAND_CANCEL, commands.ALL_COMMANDS)

    def test_registry_subset_of_all_commands(self) -> None:
        for command in commands.REGISTRY_ORDER:
            self.assertIn(command, commands.ALL_COMMANDS)

    def test_help_order_subset_of_all_commands(self) -> None:
        for command in commands.HELP_COMMAND_ORDER:
            self.assertIn(command, commands.ALL_COMMANDS)

    def test_help_specs_cover_help_order(self) -> None:
        for command in commands.HELP_COMMAND_ORDER:
            self.assertIn(command, commands.HELP_COMMAND_SPECS)

    def test_slash_helper(self) -> None:
        self.assertEqual(commands.slash(commands.COMMAND_ADD), "/add")
        self.assertEqual(commands.slash(commands.COMMAND_FIND, " <жанр>"), "/find <жанр>")


if __name__ == "__main__":
    unittest.main()
