"""CLI helper to queue movie entries while the bot is offline."""

from __future__ import annotations

from core.offline_queue import add_offline_entry
from core.normalization import normalize_recommendation, normalize_type


def _prompt(prompt: str, validator=None, transform=None, default: str | None = None) -> str:
    while True:
        value = input(prompt).strip()
        if not value and default is not None:
            return default
        if not value:
            print("Поле не может быть пустым. Попробуйте ещё раз.")
            continue
        if validator and not validator(value):
            print("Значение не прошло проверку. Попробуйте ещё раз.")
            continue
        return transform(value) if transform else value


def _prompt_year() -> str:
    return _prompt("Год выпуска: ", lambda v: v.isdigit() and len(v) == 4)


def _prompt_rating() -> str:
    def validate(value: str) -> bool:
        try:
            num = float(value.replace(",", "."))
        except ValueError:
            return False
        return 1 <= num <= 10

    def transform(value: str) -> str:
        num = float(value.replace(",", "."))
        return f"{num:g}"

    return _prompt("Оценка (1-10): ", validate, transform)


def _prompt_type() -> str:
    print("Тип (1 — фильм, 2 — сериал). По умолчанию — фильм.")
    value = input("Выбор [1/2]: ").strip()
    mapping = {"1": "фильм", "2": "сериал"}
    return normalize_type(mapping.get(value, value or "фильм"))


def _prompt_recommendation() -> str:
    print("Рекомендация: 1 — рекомендую, 2 — можно посмотреть, 3 — в топку.")
    value = input("Выбор [1/2/3]: ").strip()
    mapping = {"1": "рекомендую", "2": "можно посмотреть", "3": "в топку"}
    return normalize_recommendation(mapping.get(value, value or "можно посмотреть"))


def main() -> None:
    print("Добавление фильма в оффлайн-режиме. Нажмите Ctrl+C для отмены.")
    film = _prompt("Название: ")
    year = _prompt_year()
    genre = _prompt("Жанр: ")
    rating = _prompt_rating()
    comment = input("Комментарий (можно оставить пустым): ").strip()
    entry_type = _prompt_type()
    recommendation = _prompt_recommendation()

    add_offline_entry(
        {
            "film": film,
            "year": year,
            "genre": genre,
            "rating": rating,
            "comment": comment,
            "type": entry_type,
            "recommendation": recommendation,
        }
    )
    print("✅ Запись сохранена локально и будет выгружена при следующем запуске бота.")


if __name__ == "__main__":
    main()
