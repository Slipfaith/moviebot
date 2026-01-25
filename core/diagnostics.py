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


def _format(ok: bool) -> str:
    return "✅" if ok else "⚠️"


def print_startup_diagnostics() -> None:
    print("🔎 Предстартовая проверка окружения:")

    print(f"{_format(bool(TELEGRAM_TOKEN))} TELEGRAM_TOKEN: "
          f"{'задан' if TELEGRAM_TOKEN else 'не найден'}")

    print(f"{_format(bool(GOOGLE_SHEET_NAME))} GOOGLE_SHEET_NAME: "
          f"{'задан' if GOOGLE_SHEET_NAME else 'не найден'}")

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
    print(f"✅ Офлайн-очередь: "
          f"{'есть ' + str(offline_count) + ' записей' if offline_count else 'нет отложенных записей'}")

    print(f"{_format(bool(OCR_LOCAL_URL))} OCR_LOCAL_URL: {OCR_LOCAL_URL or 'не настроен'}")

    try:
        ws = connect_to_sheet()
        _ = ws.row_count
        print("✅ Доступ к таблице: OK")
    except Exception as exc:
        print(f"⚠️ Доступ к таблице: {type(exc).__name__}: {exc}")
