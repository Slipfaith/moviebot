"""Gemini API client helpers."""

from __future__ import annotations

import base64
import time
from typing import Any, Dict, List, Optional

import requests

from core.config import (
    GEMINI_API_KEY,
    GEMINI_FALLBACK_MODELS,
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL,
    GEMINI_RETRY_BASE_DELAY_SECONDS,
    GEMINI_TIMEOUT_SECONDS,
    GEMINI_TOTAL_TIMEOUT_SECONDS,
)
from core.token_usage import record_token_usage

_API_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
_DEFAULT_SYSTEM_PROMPT = (
    "Ты MovieBot. Отвечай на русском языке кратко и по делу. "
    "Если спрашивают про фильмы или сериалы, давай практичные рекомендации."
)
_RETRYABLE_STATUS_CODES = {429, 500, 503, 504}


class GeminiError(RuntimeError):
    """Raised when Gemini API returns an unusable response."""


def is_gemini_enabled() -> bool:
    return bool(GEMINI_API_KEY)


def _extract_text(payload: Dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return ""

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content")
        if not isinstance(content, dict):
            continue
        parts: List[Any] = content.get("parts", [])
        if not isinstance(parts, list):
            continue
        texts: List[str] = []
        for part in parts:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())
        if texts:
            return "\n".join(texts)
    return ""


def _as_non_negative_int(value: Any) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return 0
    return result if result >= 0 else 0


def _extract_usage_tokens(payload: Dict[str, Any]) -> tuple[int, int]:
    usage = payload.get("usageMetadata")
    if not isinstance(usage, dict):
        return 0, 0

    prompt_tokens = _as_non_negative_int(usage.get("promptTokenCount"))
    cached_tokens = _as_non_negative_int(usage.get("cachedContentTokenCount"))
    input_tokens = prompt_tokens + cached_tokens

    output_tokens = _as_non_negative_int(usage.get("candidatesTokenCount"))
    if output_tokens <= 0:
        output_tokens = _as_non_negative_int(usage.get("outputTokenCount"))

    total_tokens = _as_non_negative_int(usage.get("totalTokenCount"))
    if total_tokens > 0 and input_tokens <= 0 and output_tokens > 0 and total_tokens >= output_tokens:
        input_tokens = total_tokens - output_tokens
    if total_tokens > 0 and output_tokens <= 0 and input_tokens > 0 and total_tokens >= input_tokens:
        output_tokens = total_tokens - input_tokens

    return input_tokens, output_tokens


def _extract_block_reason(payload: Dict[str, Any]) -> Optional[str]:
    prompt_feedback = payload.get("promptFeedback")
    if isinstance(prompt_feedback, dict):
        block_reason = prompt_feedback.get("blockReason")
        if isinstance(block_reason, str) and block_reason:
            return block_reason
    return None


def _iter_models() -> List[str]:
    models = [GEMINI_MODEL, *GEMINI_FALLBACK_MODELS]
    unique_models: List[str] = []
    seen = set()
    for model in models:
        normalized = (model or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_models.append(normalized)
    return unique_models


def _retry_delay_seconds(attempt: int) -> float:
    base = max(GEMINI_RETRY_BASE_DELAY_SECONDS, 0.1)
    return base * (2 ** max(attempt - 1, 0))


def _request_gemini(
    model: str,
    payload: Dict[str, Any],
    *,
    timeout_seconds: float,
) -> requests.Response:
    return requests.post(
        _API_URL_TEMPLATE.format(model=model),
        headers={"x-goog-api-key": GEMINI_API_KEY},
        json=payload,
        timeout=timeout_seconds,
    )


def _run_gemini_payload(payload: Dict[str, Any]) -> str:
    last_error: Optional[str] = None
    max_retries = max(GEMINI_MAX_RETRIES, 1)
    total_timeout = max(GEMINI_TOTAL_TIMEOUT_SECONDS, GEMINI_TIMEOUT_SECONDS)
    deadline = time.monotonic() + total_timeout

    for model in _iter_models():
        for attempt in range(1, max_retries + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise GeminiError(
                    "Gemini is temporarily unavailable. "
                    f"Total timeout exceeded ({total_timeout:.0f}s). "
                    f"Last error: {last_error or 'unknown'}"
                )
            request_timeout = max(0.1, min(GEMINI_TIMEOUT_SECONDS, remaining))
            try:
                response = _request_gemini(
                    model,
                    payload,
                    timeout_seconds=request_timeout,
                )
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt < max_retries:
                    delay = min(_retry_delay_seconds(attempt), max(deadline - time.monotonic(), 0.0))
                    if delay <= 0:
                        continue
                    time.sleep(delay)
                    continue
                break

            if response.status_code in _RETRYABLE_STATUS_CODES:
                last_error = f"HTTP {response.status_code}"
                if attempt < max_retries:
                    delay = min(_retry_delay_seconds(attempt), max(deadline - time.monotonic(), 0.0))
                    if delay <= 0:
                        continue
                    time.sleep(delay)
                    continue
                break

            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                details = ""
                try:
                    error_payload = response.json()
                except ValueError:
                    error_payload = None
                if isinstance(error_payload, dict):
                    details = str(error_payload.get("error") or "")
                message = (
                    f"Gemini API error (model={model}, status={response.status_code})"
                    + (f": {details}" if details else "")
                )
                raise GeminiError(message) from exc

            try:
                data: Dict[str, Any] = response.json()
            except ValueError as exc:
                raise GeminiError("Gemini returned invalid JSON.") from exc

            in_tokens, out_tokens = _extract_usage_tokens(data)
            record_token_usage("gemini", in_tokens, out_tokens)

            block_reason = _extract_block_reason(data)
            if block_reason:
                raise GeminiError(f"Gemini blocked the request: {block_reason}")

            text = _extract_text(data)
            if text:
                return text

            last_error = f"Empty response from model={model}"
            break

    raise GeminiError(
        "Gemini is temporarily unavailable. "
        f"Last error: {last_error or 'unknown'}"
    )


def generate_gemini_reply(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    temperature: float = 0.4,
    max_output_tokens: int = 512,
) -> str:
    if not GEMINI_API_KEY:
        raise GeminiError("GEMINI_API_KEY is not configured.")

    normalized_prompt = (prompt or "").strip()
    if not normalized_prompt:
        raise ValueError("Prompt cannot be empty.")

    prompt_text = system_prompt if system_prompt is not None else _DEFAULT_SYSTEM_PROMPT
    payload: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": normalized_prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if prompt_text:
        payload["systemInstruction"] = {"parts": [{"text": prompt_text}]}
    return _run_gemini_payload(payload)


def generate_gemini_reply_with_image(
    *,
    prompt: str,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    system_prompt: Optional[str] = None,
    temperature: float = 0.2,
    max_output_tokens: int = 512,
) -> str:
    if not GEMINI_API_KEY:
        raise GeminiError("GEMINI_API_KEY is not configured.")

    normalized_prompt = (prompt or "").strip()
    if not normalized_prompt:
        raise ValueError("Prompt cannot be empty.")
    if not image_bytes:
        raise ValueError("Image payload is empty.")

    prompt_text = system_prompt if system_prompt is not None else _DEFAULT_SYSTEM_PROMPT
    encoded = base64.b64encode(image_bytes).decode("ascii")
    payload: Dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": normalized_prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type or "image/jpeg",
                            "data": encoded,
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if prompt_text:
        payload["systemInstruction"] = {"parts": [{"text": prompt_text}]}
    return _run_gemini_payload(payload)
