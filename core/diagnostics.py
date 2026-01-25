"""Startup diagnostics for MovieBot."""

from __future__ import annotations

from pathlib import Path

from core.config import (
    GOOGLE_CREDENTIALS,
    GOOGLE_SHEET_NAME,
    OCR_LOCAL_URL,
    TELEGRAM_TOKEN,
)
from core.gsheet import connect_to_sheet
from core.offline_queue import offline_entry_count


def _format_status(ok: bool) -> str:
    return "✅" if ok else "⚠️"


def print_startup_diagnostics() -> None:
    """Print startup diagnostics before the bot starts."""

    print("🔎 Предстартовая проверка окружения:")

    token_ok = bool(TELEGRAM_TOKEN)
    print(f"{_format_status(token_ok)} TELEGRAM_TOKEN: {'задан' if token_ok else 'не найден'}")

    sheet_ok = bool(GOOGLE_SHEET_NAME)
    print(
        f"{_format_status(sheet_ok)} GOOGLE_SHEET_NAME: "
        f"{'задан' if sheet_ok else 'не найден'}"
    )

    credentials_ok = False
    credentials_note = "не найден"
    if GOOGLE_CREDENTIALS:
        credentials_path = Path(GOOGLE_CREDENTIALS)
        credentials_ok = credentials_path.exists()
        if credentials_ok:
            credentials_note = f"файл найден ({credentials_path})"
        else:
            credentials_note = f"файл не найден ({credentials_path})"
    print(f"{_format_status(credentials_ok)} GOOGLE_CREDENTIALS: {credentials_note}")

    offline_count = offline_entry_count()
    offline_note = (
        f"есть {offline_count} отложенных запис(ей)" if offline_count else "нет отложенных записей"
    )
    print(f"{_format_status(True)} Офлайн-очередь: {offline_note}")

    ocr_ok = bool(OCR_LOCAL_URL)
    ocr_note = OCR_LOCAL_URL if OCR_LOCAL_URL else "не настроен"
    print(f"{_format_status(ocr_ok)} OCR_LOCAL_URL: {ocr_note}")

    try:
        worksheet = connect_to_sheet()
        title = getattr(worksheet, "title", "без названия")
        print(f"{_format_status(True)} Доступ к таблице: OK ({title})")
    except Exception as exc:  # pragma: no cover - depends on external services
        print(f"{_format_status(False)} Доступ к таблице: ошибка ({exc})")
