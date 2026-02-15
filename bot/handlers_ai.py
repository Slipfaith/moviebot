"""AI handlers facade."""

from __future__ import annotations

from bot.handlers_ai_random import random_command
from bot.handlers_ai_recommend import _run_ai_recommendation, ai_command, recommend_command

__all__ = [
    "_run_ai_recommendation",
    "ai_command",
    "recommend_command",
    "random_command",
]
