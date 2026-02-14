from __future__ import annotations

from pathlib import Path

from core.config import (
    GEMINI_API_KEY,
    GEMINI_FALLBACK_MODELS,
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL,
    GOOGLE_CREDENTIALS,
    GOOGLE_SHEET_NAME,
    KINOPOISK_TOKEN,
    OMDB_API_KEY,
    TELEGRAM_TOKEN,
    TMDB_API_KEY,
)
from core.gsheet import connect_to_sheet
from core.offline_queue import offline_entry_count


def _format(ok: bool) -> str:
    return "✅" if ok else "⚠️"


def print_startup_diagnostics(check_sheet: bool = True) -> None:
    print("🔎 Предстартовая проверка окружения:")

    print(
        f"{_format(bool(TELEGRAM_TOKEN))} TELEGRAM_TOKEN: "
        f"{'задан' if TELEGRAM_TOKEN else 'не найден'}"
    )
    print(
        f"{_format(bool(GOOGLE_SHEET_NAME))} GOOGLE_SHEET_NAME: "
        f"{'задан' if GOOGLE_SHEET_NAME else 'не найден'}"
    )

    credentials_ok = False
    credentials_note = "не найден"
    if GOOGLE_CREDENTIALS:
        path = Path(GOOGLE_CREDENTIALS)
        credentials_ok = path.exists()
        credentials_note = (
            f"файл найден ({path})" if credentials_ok else f"файл не найден ({path})"
        )
    print(f"{_format(credentials_ok)} GOOGLE_CREDENTIALS: {credentials_note}")

    offline_count = offline_entry_count()
    print(
        "✅ Офлайн-очередь: "
        f"{'есть ' + str(offline_count) + ' записей' if offline_count else 'нет отложенных записей'}"
    )

    print(
        f"{_format(bool(GEMINI_API_KEY))} GEMINI_API_KEY: "
        f"{'задан' if GEMINI_API_KEY else 'не найден'}"
    )
    if GEMINI_API_KEY:
        print(f"✅ GEMINI_MODEL: {GEMINI_MODEL}")
        if GEMINI_FALLBACK_MODELS:
            print(f"✅ GEMINI_FALLBACK_MODELS: {', '.join(GEMINI_FALLBACK_MODELS)}")
        print(f"✅ GEMINI_MAX_RETRIES: {GEMINI_MAX_RETRIES}")
    print(
        f"{_format(bool(TMDB_API_KEY))} TMDB_API_KEY: "
        f"{'задан' if TMDB_API_KEY else 'не найден'}"
    )
    print(
        f"{_format(bool(OMDB_API_KEY))} OMDB_API_KEY: "
        f"{'задан' if OMDB_API_KEY else 'не найден'}"
    )
    print(
        f"{_format(bool(KINOPOISK_TOKEN))} KINOPOISK_TOKEN: "
        f"{'задан' if KINOPOISK_TOKEN else 'не найден'}"
    )

    if not check_sheet:
        print("ℹ️ Проверка доступа к таблице пропущена (STARTUP_CHECK_SHEET=0).")
        return

    try:
        ws = connect_to_sheet()
        _ = ws.row_count
        print("✅ Доступ к таблице: OK")
    except Exception as exc:
        print(f"⚠️ Доступ к таблице: {type(exc).__name__}: {exc}")
