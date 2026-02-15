"""Mistral API client helpers (chat + audio transcription)."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests

from core.config import (
    MISTRAL_API_KEY,
    MISTRAL_AUDIO_MODEL,
    MISTRAL_MAX_RETRIES,
    MISTRAL_MODEL,
    MISTRAL_RETRY_BASE_DELAY_SECONDS,
    MISTRAL_TIMEOUT_SECONDS,
)
from core.token_usage import record_token_usage

_CHAT_COMPLETIONS_URL = "https://api.mistral.ai/v1/chat/completions"
_AUDIO_TRANSCRIPTIONS_URL = "https://api.mistral.ai/v1/audio/transcriptions"
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_DEFAULT_SYSTEM_PROMPT = (
    "Ты MovieBot. Отвечай кратко, на русском и строго по задаче."
)


class MistralError(RuntimeError):
    """Raised when Mistral API returns an unusable response."""


def is_mistral_enabled() -> bool:
    return bool(MISTRAL_API_KEY)


def _retry_delay_seconds(attempt: int) -> float:
    base = max(MISTRAL_RETRY_BASE_DELAY_SECONDS, 0.1)
    return base * (2 ** max(attempt - 1, 0))


def _extract_error_details(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:250]
    if not isinstance(payload, dict):
        return str(payload)
    if isinstance(payload.get("error"), dict):
        message = payload["error"].get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    if isinstance(payload.get("error"), str) and payload["error"].strip():
        return payload["error"].strip()
    if isinstance(payload.get("message"), str) and payload["message"].strip():
        return payload["message"].strip()
    return str(payload)


def _post_with_retries(
    url: str,
    *,
    json_payload: Optional[Dict[str, object]] = None,
    form_data: Optional[Dict[str, str]] = None,
    files: Optional[Dict[str, object]] = None,
) -> requests.Response:
    if not MISTRAL_API_KEY:
        raise MistralError("MISTRAL_API_KEY is not configured.")

    last_error = "unknown"
    max_retries = max(MISTRAL_MAX_RETRIES, 1)
    headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}"}

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=json_payload,
                data=form_data,
                files=files,
                timeout=MISTRAL_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < max_retries:
                time.sleep(_retry_delay_seconds(attempt))
                continue
            raise MistralError(f"Mistral request failed: {last_error}") from exc

        if response.status_code in _RETRYABLE_STATUS_CODES:
            last_error = f"HTTP {response.status_code}"
            if attempt < max_retries:
                time.sleep(_retry_delay_seconds(attempt))
                continue
            raise MistralError(f"Mistral temporarily unavailable ({last_error}).")

        if response.status_code >= 400:
            details = _extract_error_details(response)
            raise MistralError(
                f"Mistral API error (status={response.status_code}): {details}"
            )
        return response

    raise MistralError(f"Mistral request failed: {last_error}")


def _extract_chat_text(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()
    return ""


def _as_non_negative_int(value: Any) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return 0
    return result if result >= 0 else 0


def _extract_usage_tokens(payload: Dict[str, Any]) -> tuple[int, int]:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return 0, 0

    input_tokens = _as_non_negative_int(usage.get("prompt_tokens"))
    output_tokens = _as_non_negative_int(usage.get("completion_tokens"))
    total_tokens = _as_non_negative_int(usage.get("total_tokens"))

    if total_tokens > 0 and input_tokens <= 0 and output_tokens > 0 and total_tokens >= output_tokens:
        input_tokens = total_tokens - output_tokens
    if total_tokens > 0 and output_tokens <= 0 and input_tokens > 0 and total_tokens >= input_tokens:
        output_tokens = total_tokens - input_tokens

    return input_tokens, output_tokens


def generate_mistral_reply(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    temperature: float = 0.4,
    max_output_tokens: int = 512,
) -> str:
    normalized_prompt = (prompt or "").strip()
    if not normalized_prompt:
        raise ValueError("Prompt cannot be empty.")

    payload: Dict[str, object] = {
        "model": MISTRAL_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    system_prompt
                    if system_prompt is not None
                    else _DEFAULT_SYSTEM_PROMPT
                ),
            },
            {"role": "user", "content": normalized_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_output_tokens,
    }
    response = _post_with_retries(_CHAT_COMPLETIONS_URL, json_payload=payload)
    try:
        body = response.json()
    except ValueError as exc:
        raise MistralError("Mistral returned invalid JSON.") from exc
    if not isinstance(body, dict):
        raise MistralError("Mistral returned unexpected response payload.")

    in_tokens, out_tokens = _extract_usage_tokens(body)
    record_token_usage("mistral", in_tokens, out_tokens)

    text = _extract_chat_text(body)
    if not text:
        raise MistralError("Mistral returned an empty response.")
    return text


def transcribe_mistral_audio(
    *,
    audio_bytes: bytes,
    file_name: str = "voice.ogg",
    mime_type: str = "audio/ogg",
    language: str = "ru",
) -> str:
    if not audio_bytes:
        raise ValueError("Audio payload is empty.")

    response = _post_with_retries(
        _AUDIO_TRANSCRIPTIONS_URL,
        form_data={"model": MISTRAL_AUDIO_MODEL, "language": language},
        files={
            "file": (file_name, audio_bytes, mime_type or "application/octet-stream"),
        },
    )
    try:
        body = response.json()
    except ValueError as exc:
        raise MistralError("Mistral transcription returned invalid JSON.") from exc
    if not isinstance(body, dict):
        raise MistralError("Mistral transcription returned invalid payload.")

    in_tokens, out_tokens = _extract_usage_tokens(body)
    if in_tokens > 0 or out_tokens > 0:
        record_token_usage("mistral", in_tokens, out_tokens)

    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        raise MistralError("Mistral transcription returned empty text.")
    return text.strip()


__all__ = [
    "MistralError",
    "is_mistral_enabled",
    "generate_mistral_reply",
    "transcribe_mistral_audio",
]
