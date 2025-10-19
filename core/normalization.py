"""Normalization helpers for user-provided values."""

from typing import Optional


def normalize_type(value: Optional[str]) -> str:
    """Normalize media type to either ``фильм`` or ``сериал``."""

    lowered = (value or "").strip().lower()
    if lowered.startswith("сериал") or lowered.startswith("series"):
        return "сериал"
    return "фильм"


def normalize_recommendation(value: Optional[str]) -> str:
    """Normalize recommendation flag to known values."""

    lowered = (value or "").strip().lower()
    if lowered.startswith("рек"):
        return "рекомендую"
    if lowered.startswith("мож") or "можно" in lowered:
        return "можно посмотреть"
    if lowered.startswith("в топ") or lowered.startswith("втоп") or "топку" in lowered:
        return "в топку"
    if lowered in {"ok", "okey", "okay"}:
        return "можно посмотреть"
    return "можно посмотреть"
