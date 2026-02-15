"""Smoke tests for handler facades and bot wiring."""

from __future__ import annotations

import importlib
import unittest
from unittest.mock import patch

from telegram.ext import ConversationHandler


class HandlersSmokeTests(unittest.TestCase):
    def test_handler_facades_resolve_all_exports(self) -> None:
        for module_name in ("bot.handlers", "bot.handlers_shared"):
            module = importlib.import_module(module_name)
            for name in module.__all__:
                getattr(module, name)

    def test_create_bot_registers_expected_handlers(self) -> None:
        setup_bot = importlib.import_module("bot.setup_bot")
        with patch.object(setup_bot, "TELEGRAM_TOKEN", "123456:TEST_TOKEN"):
            app = setup_bot.create_bot()

        handlers = app.handlers.get(0, [])
        callback_names = []
        for handler in handlers:
            callback = getattr(handler, "callback", None)
            if callback is not None:
                callback_names.append(callback.__name__)

        self.assertIn("start_command", callback_names)
        self.assertIn("help_command", callback_names)
        self.assertIn("menu_command", callback_names)
        self.assertIn("recommend_command", callback_names)
        self.assertIn("random_command", callback_names)
        self.assertIn("handle_photo", callback_names)
        self.assertIn("handle_message", callback_names)
        self.assertIn("handle_callback", callback_names)
        self.assertTrue(any(isinstance(handler, ConversationHandler) for handler in handlers))


if __name__ == "__main__":
    unittest.main()
