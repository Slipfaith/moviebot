"""Runtime diagnostics command handler."""

from __future__ import annotations

import asyncio
import time
from typing import Callable, Tuple

from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers_sheet_io import refresh_sheet_index_sync, sheet_index_status
from bot.handlers_transport import _send, _typing
from core.gemini import generate_gemini_reply, is_gemini_enabled
from core.mistral import generate_mistral_reply, is_mistral_enabled
from core.recommendations import probe_kinopoisk_status, probe_tmdb_status
from core.runtime_monitor import get_recent_errors


def _short_error_text(exc: Exception) -> str:
    message = str(exc).strip()
    if len(message) > 220:
        message = message[:220].rstrip() + "..."
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


async def _probe_with_latency(
    func: Callable[[], object],
    *,
    timeout_seconds: float = 8.0,
) -> Tuple[bool, float, str]:
    started = time.monotonic()
    try:
        await asyncio.wait_for(asyncio.to_thread(func), timeout=timeout_seconds)
    except Exception as exc:
        elapsed_ms = (time.monotonic() - started) * 1000.0
        return False, elapsed_ms, _short_error_text(exc)
    elapsed_ms = (time.monotonic() - started) * 1000.0
    return True, elapsed_ms, "ok"


def _probe_gemini_sync() -> object:
    return generate_gemini_reply(
        "Ответь одним словом: OK",
        temperature=0.0,
        max_output_tokens=8,
    )


def _probe_mistral_sync() -> object:
    return generate_mistral_reply(
        "Ответь одним словом: OK",
        temperature=0.0,
        max_output_tokens=8,
    )


async def diag_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with _typing(update, context):
        lines: list[str] = ["🩺 Диагностика сервисов"]

        if is_gemini_enabled():
            ok, latency_ms, details = await _probe_with_latency(_probe_gemini_sync, timeout_seconds=8.0)
            lines.append(
                f"• Gemini: {'OK' if ok else 'ERROR'} ({latency_ms:.0f} ms) {details if not ok else ''}".rstrip()
            )
        else:
            lines.append("• Gemini: disabled")

        if is_mistral_enabled():
            ok, latency_ms, details = await _probe_with_latency(_probe_mistral_sync, timeout_seconds=8.0)
            lines.append(
                f"• Mistral: {'OK' if ok else 'ERROR'} ({latency_ms:.0f} ms) {details if not ok else ''}".rstrip()
            )
        else:
            lines.append("• Mistral: disabled")

        tmdb_started = time.monotonic()
        tmdb_ok, tmdb_details = await asyncio.to_thread(probe_tmdb_status)
        tmdb_latency = (time.monotonic() - tmdb_started) * 1000.0
        tmdb_state = "DISABLED" if tmdb_details == "disabled" else ("OK" if tmdb_ok else "ERROR")
        lines.append(
            f"• TMDB: {tmdb_state} ({tmdb_latency:.0f} ms) {tmdb_details}".rstrip()
        )

        kp_started = time.monotonic()
        kp_ok, kp_details = await asyncio.to_thread(probe_kinopoisk_status)
        kp_latency = (time.monotonic() - kp_started) * 1000.0
        kp_state = "DISABLED" if kp_details == "disabled" else ("OK" if kp_ok else "ERROR")
        lines.append(
            f"• Kinopoisk: {kp_state} ({kp_latency:.0f} ms) {kp_details}".rstrip()
        )

        sheets_ok, sheets_latency, sheets_details = await _probe_with_latency(
            lambda: refresh_sheet_index_sync(force_refresh=True),
            timeout_seconds=12.0,
        )
        status = sheet_index_status()
        status_line = (
            f"cache_rows={status.get('rows', 0)}, "
            f"cache_age={float(status.get('age_seconds', 0.0)):.0f}s"
        )
        if sheets_ok:
            lines.append(f"• Google Sheets: OK ({sheets_latency:.0f} ms) {status_line}")
        else:
            lines.append(
                f"• Google Sheets: ERROR ({sheets_latency:.0f} ms) {sheets_details}; {status_line}"
            )

        recent_errors = get_recent_errors(limit=6)
        if recent_errors:
            lines.append("")
            lines.append("Recent errors:")
            for event in recent_errors:
                lines.append(
                    f"- {event.timestamp_utc} [{event.source}] {event.error_type}: {event.message}"
                )
        else:
            lines.append("")
            lines.append("Recent errors: none")

        await _send(update, "\n".join(lines))


__all__ = ["diag_command"]
