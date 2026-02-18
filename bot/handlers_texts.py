"""Shared handler texts and conversation constants."""

from __future__ import annotations

from bot.commands import COMMAND_ADD, HELP_COMMAND_ORDER, HELP_COMMAND_SPECS, slash


def _build_help_text() -> str:
    lines = ["Команды:"]
    for command in HELP_COMMAND_ORDER:
        usage_suffix, description = HELP_COMMAND_SPECS[command]
        lines.append(f"• {slash(command, usage_suffix)} — {description}")
    lines.append("• фото постера — распознать фильм и показать инфо")
    return "\n".join(lines)


HELP_TEXT = _build_help_text()

OFFLINE_GUIDE_TEXT = "Если таблица недоступна, записи сохраняются оффлайн."
ADD_USAGE_TEXT = (
    "Чтобы добавить запись, используйте формат:\n"
    f"{slash(COMMAND_ADD)} Название;Год;Жанр;Оценка;Комментарий;Тип;Рекомендация;Владелец\n"
    "Комментарий, тип, рекомендация и владелец — опционально.\n"
    f"Можно также отправить {slash(COMMAND_ADD)} и заполнить форму пошагово.\n"
    "Пример:\n"
    f"{slash(COMMAND_ADD)} Интерстеллар;2014;фантастика;9;Шикарный саундтрек;фильм;рекомендую;муж"
)

(
    ADD_FILM,
    ADD_YEAR,
    ADD_GENRE,
    ADD_RATING,
    ADD_COMMENT,
    ADD_TYPE,
    ADD_RECOMMENDATION,
    ADD_OWNER,
    ADD_CONFIRM,
    ADD_VOICE_CLARIFY,
    ADD_POSTER_EDIT,
    ADD_POSTER_EDIT_TEXT,
) = range(12)

__all__ = [
    "HELP_TEXT",
    "OFFLINE_GUIDE_TEXT",
    "ADD_USAGE_TEXT",
    "ADD_FILM",
    "ADD_YEAR",
    "ADD_GENRE",
    "ADD_RATING",
    "ADD_COMMENT",
    "ADD_TYPE",
    "ADD_RECOMMENDATION",
    "ADD_OWNER",
    "ADD_CONFIRM",
    "ADD_VOICE_CLARIFY",
    "ADD_POSTER_EDIT",
    "ADD_POSTER_EDIT_TEXT",
]
