"""Command identifiers and registration order."""

from __future__ import annotations

from typing import Dict, Tuple

COMMAND_START = "start"
COMMAND_HELP = "help"
COMMAND_MENU = "menu"
COMMAND_DIAG = "diag"
COMMAND_AI = "ai"
COMMAND_RECOMMEND = "recommend"
COMMAND_ADD = "add"
COMMAND_FIND = "find"
COMMAND_SEARCH = "search"
COMMAND_LIST = "list"
COMMAND_STATS = "stats"
COMMAND_WINNER = "winner"
COMMAND_RANDOM = "random"
COMMAND_OWNER = "owner"
COMMAND_TOP = "top"
COMMAND_RECENT = "recent"
COMMAND_CANCEL = "cancel"

BASE_COMMANDS = (
    COMMAND_START,
    COMMAND_HELP,
    COMMAND_MENU,
    COMMAND_DIAG,
)

AI_COMMANDS = (
    COMMAND_AI,
    COMMAND_RECOMMEND,
    COMMAND_RANDOM,
)

LIBRARY_COMMANDS = (
    COMMAND_FIND,
    COMMAND_SEARCH,
    COMMAND_LIST,
    COMMAND_OWNER,
    COMMAND_TOP,
    COMMAND_RECENT,
)

STATS_COMMANDS = (
    COMMAND_STATS,
    COMMAND_WINNER,
)

REGISTRY_ORDER = (
    COMMAND_START,
    COMMAND_HELP,
    COMMAND_MENU,
    COMMAND_DIAG,
    COMMAND_AI,
    COMMAND_RECOMMEND,
    COMMAND_FIND,
    COMMAND_SEARCH,
    COMMAND_LIST,
    COMMAND_STATS,
    COMMAND_WINNER,
    COMMAND_RANDOM,
    COMMAND_OWNER,
    COMMAND_TOP,
    COMMAND_RECENT,
)

HELP_COMMAND_ORDER = (
    COMMAND_ADD,
    COMMAND_TOP,
    COMMAND_RECENT,
    COMMAND_FIND,
    COMMAND_SEARCH,
    COMMAND_LIST,
    COMMAND_STATS,
    COMMAND_WINNER,
    COMMAND_RANDOM,
    COMMAND_OWNER,
    COMMAND_AI,
    COMMAND_DIAG,
    COMMAND_MENU,
    COMMAND_HELP,
    COMMAND_CANCEL,
)

HELP_COMMAND_SPECS: Dict[str, Tuple[str, str]] = {
    COMMAND_ADD: ("", "добавить фильм"),
    COMMAND_TOP: ("", "топ по оценке"),
    COMMAND_RECENT: ("", "за последний месяц"),
    COMMAND_FIND: (" <жанр>", "поиск по жанру"),
    COMMAND_SEARCH: (" <название>", "поиск по названию"),
    COMMAND_LIST: ("", "последние добавления"),
    COMMAND_STATS: ("", "статистика по оценкам"),
    COMMAND_WINNER: ("", "победитель месяца (муж vs жена)"),
    COMMAND_RANDOM: ("", "случайный фильм"),
    COMMAND_OWNER: (" <муж|жена>", "подборка по владельцу"),
    COMMAND_AI: (" <вопрос>", "спросить AI"),
    COMMAND_DIAG: ("", "диагностика сервисов"),
    COMMAND_MENU: ("", "меню"),
    COMMAND_HELP: ("", "помощь"),
    COMMAND_CANCEL: ("", "отменить добавление"),
}

ALL_COMMANDS = (
    *BASE_COMMANDS,
    COMMAND_ADD,
    *AI_COMMANDS,
    *LIBRARY_COMMANDS,
    *STATS_COMMANDS,
    COMMAND_CANCEL,
)


def slash(command: str, suffix: str = "") -> str:
    return f"/{command}{suffix}"


__all__ = [
    "COMMAND_START",
    "COMMAND_HELP",
    "COMMAND_MENU",
    "COMMAND_DIAG",
    "COMMAND_AI",
    "COMMAND_RECOMMEND",
    "COMMAND_ADD",
    "COMMAND_FIND",
    "COMMAND_SEARCH",
    "COMMAND_LIST",
    "COMMAND_STATS",
    "COMMAND_WINNER",
    "COMMAND_RANDOM",
    "COMMAND_OWNER",
    "COMMAND_TOP",
    "COMMAND_RECENT",
    "COMMAND_CANCEL",
    "BASE_COMMANDS",
    "AI_COMMANDS",
    "LIBRARY_COMMANDS",
    "STATS_COMMANDS",
    "REGISTRY_ORDER",
    "HELP_COMMAND_ORDER",
    "HELP_COMMAND_SPECS",
    "ALL_COMMANDS",
    "slash",
]
