"""Caching and dedupe helpers for handlers."""

from __future__ import annotations

import re
import threading
import time
from typing import Dict, List, Optional, Set, Tuple

from telegram import Update

from core.recommendations import TasteProfile

_CACHE_TTL_SECONDS = 60

_RESPONSE_CACHE: Dict[str, Tuple[float, str]] = {}

_RECENT_RECOMMENDATIONS_TTL_SECONDS = 24 * 60 * 60

_RECENT_RECOMMENDATIONS_MAX_SCOPES = 500

_RECENT_RECOMMENDATIONS_BY_SCOPE: Dict[str, Tuple[float, List[str]]] = {}

_PROFILE_CACHE_TTL_SECONDS = 5 * 60

_PROFILE_CACHE: Optional[Tuple[float, "TasteProfile"]] = None

_CACHE_LOCK = threading.RLock()

def _get_cached_response(cache_key: str) -> Optional[str]:
    with _CACHE_LOCK:
        cached = _RESPONSE_CACHE.get(cache_key)
    if not cached:
        return None
    expires_at, text = cached
    if time.time() <= expires_at:
        return text
    with _CACHE_LOCK:
        _RESPONSE_CACHE.pop(cache_key, None)
    return None

def _store_cached_response(cache_key: str, text: str) -> None:
    with _CACHE_LOCK:
        _RESPONSE_CACHE[cache_key] = (time.time() + _CACHE_TTL_SECONDS, text)

def _invalidate_response_cache() -> None:
    global _PROFILE_CACHE
    with _CACHE_LOCK:
        _RESPONSE_CACHE.clear()
        _PROFILE_CACHE = None

def _get_cached_profile() -> Optional[TasteProfile]:
    global _PROFILE_CACHE
    with _CACHE_LOCK:
        cached = _PROFILE_CACHE
    if not cached:
        return None
    expires_at, profile = cached
    if time.time() <= expires_at:
        return profile
    with _CACHE_LOCK:
        if _PROFILE_CACHE and _PROFILE_CACHE[0] <= time.time():
            _PROFILE_CACHE = None
    return None

def _store_cached_profile(profile: TasteProfile) -> None:
    global _PROFILE_CACHE
    with _CACHE_LOCK:
        _PROFILE_CACHE = (time.time() + _PROFILE_CACHE_TTL_SECONDS, profile)

def _recommendation_scope_key(update: Update) -> str:
    chat_id = update.effective_chat.id if update.effective_chat else "na"
    user_id = update.effective_user.id if update.effective_user else "na"
    return f"{chat_id}:{user_id}"

def _normalize_title_for_dedupe(value: str) -> str:
    normalized = (value or "").strip().lower()
    normalized = re.sub(r"\(\d{4}\)", "", normalized)
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized

def _get_recent_recommendations(update: Update) -> List[str]:
    key = _recommendation_scope_key(update)
    with _CACHE_LOCK:
        cached = _RECENT_RECOMMENDATIONS_BY_SCOPE.get(key)
    if not cached:
        return []
    expires_at, titles = cached
    if time.time() <= expires_at:
        return list(titles)
    with _CACHE_LOCK:
        _RECENT_RECOMMENDATIONS_BY_SCOPE.pop(key, None)
    return []

def _prune_recent_recommendations_cache(now: Optional[float] = None) -> None:
    now_ts = now if now is not None else time.time()
    with _CACHE_LOCK:
        expired_keys = [
            key
            for key, (expires_at, _) in _RECENT_RECOMMENDATIONS_BY_SCOPE.items()
            if expires_at <= now_ts
        ]
        for key in expired_keys:
            _RECENT_RECOMMENDATIONS_BY_SCOPE.pop(key, None)

        overflow = len(_RECENT_RECOMMENDATIONS_BY_SCOPE) - _RECENT_RECOMMENDATIONS_MAX_SCOPES
        if overflow <= 0:
            return
        keys_to_drop = sorted(
            _RECENT_RECOMMENDATIONS_BY_SCOPE.items(),
            key=lambda item: item[1][0],
        )[:overflow]
        for key, _ in keys_to_drop:
            _RECENT_RECOMMENDATIONS_BY_SCOPE.pop(key, None)

def _store_recent_recommendations(update: Update, titles: List[str]) -> None:
    if not titles:
        return
    key = _recommendation_scope_key(update)
    existing = _get_recent_recommendations(update)
    merged = existing + titles
    deduped: List[str] = []
    seen: Set[str] = set()
    for title in merged:
        norm = _normalize_title_for_dedupe(title)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        deduped.append(title)
    now_ts = time.time()
    _prune_recent_recommendations_cache(now_ts)
    with _CACHE_LOCK:
        _RECENT_RECOMMENDATIONS_BY_SCOPE[key] = (
            now_ts + _RECENT_RECOMMENDATIONS_TTL_SECONDS,
            deduped[-200:],
        )

__all__ = [
    "_get_cached_response",
    "_store_cached_response",
    "_invalidate_response_cache",
    "_get_cached_profile",
    "_store_cached_profile",
    "_recommendation_scope_key",
    "_normalize_title_for_dedupe",
    "_get_recent_recommendations",
    "_prune_recent_recommendations_cache",
    "_store_recent_recommendations",
]
