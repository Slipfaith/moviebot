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
    if lowered.startswith("рек") or lowered.startswith("rec"):
        return "рекомендую"
    if lowered.startswith("мож") or "можно" in lowered:
        return "можно посмотреть"
    if lowered.startswith("в топ") or lowered.startswith("втоп") or "топку" in lowered:
        return "в топку"
    if lowered.startswith("skip"):
        return "в топку"
    if lowered in {"ok", "okey", "okay"}:
        return "можно посмотреть"
    return "можно посмотреть"


def normalize_owner(value: Optional[str]) -> str:
    """Normalize owner flag to either ``муж`` or ``жена`` (or empty)."""

    lowered = (value or "").strip().lower()
    if lowered.startswith("муж") or lowered.startswith("husband"):
        return "муж"
    if lowered.startswith("жен") or lowered.startswith("wife"):
        return "жена"
    return ""
