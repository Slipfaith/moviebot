"""Unified text generation layer over Gemini and Mistral."""

from __future__ import annotations

from typing import Optional

from core.gemini import GeminiError, generate_gemini_reply, is_gemini_enabled
from core.mistral import MistralError, generate_mistral_reply, is_mistral_enabled


class AITextError(RuntimeError):
    """Raised when no configured text AI provider can return a response."""


def is_text_ai_enabled() -> bool:
    return is_gemini_enabled() or is_mistral_enabled()


def generate_text_reply(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    temperature: float = 0.4,
    max_output_tokens: int = 512,
) -> str:
    errors: list[str] = []

    if is_gemini_enabled():
        try:
            return generate_gemini_reply(
                prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
        except GeminiError as exc:
            errors.append(str(exc))

    if is_mistral_enabled():
        try:
            return generate_mistral_reply(
                prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
        except MistralError as exc:
            errors.append(str(exc))

    if not errors:
        raise AITextError("No text AI provider is configured.")
    raise AITextError(" | ".join(errors))


__all__ = [
    "AITextError",
    "is_text_ai_enabled",
    "generate_text_reply",
]
