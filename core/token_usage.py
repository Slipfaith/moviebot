"""Persistent token usage accounting for AI providers."""

from __future__ import annotations

import copy
import json
import logging
import os
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

_PROVIDERS = ("gemini", "mistral")
_STATS_FILE_NAME = "moviebot_token_usage.json"
_BACKUP_DIR_NAME = "moviebot_token_usage_backups"
_BACKUP_PREFIX = "moviebot_token_usage_"
_MAX_BACKUPS = 500
_USAGE_LOCK = threading.RLock()


def _resolve_storage_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    argv0 = (sys.argv[0] if sys.argv else "") or ""
    if argv0:
        try:
            return Path(argv0).resolve().parent
        except OSError:
            pass
    return Path(__file__).resolve().parents[1]


def token_usage_file_path() -> Path:
    return _resolve_storage_dir() / _STATS_FILE_NAME


def token_usage_backup_dir_path() -> Path:
    return _resolve_storage_dir() / _BACKUP_DIR_NAME


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_provider() -> Dict[str, int]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "requests": 0,
    }


def _empty_totals() -> Dict[str, int]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "requests": 0,
    }


def _empty_stats() -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "updated_at": _now_iso(),
        "providers": {provider: _empty_provider() for provider in _PROVIDERS},
        "totals": _empty_totals(),
    }


def _as_non_negative_int(value: Any) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return 0
    return result if result >= 0 else 0


def _normalize_stats(raw: Any) -> Dict[str, Any]:
    base = _empty_stats()
    if not isinstance(raw, dict):
        return base

    providers_raw = raw.get("providers")
    if isinstance(providers_raw, dict):
        for provider in _PROVIDERS:
            provider_raw = providers_raw.get(provider)
            if not isinstance(provider_raw, dict):
                continue
            base_provider = base["providers"][provider]
            base_provider["input_tokens"] = _as_non_negative_int(
                provider_raw.get("input_tokens")
            )
            base_provider["output_tokens"] = _as_non_negative_int(
                provider_raw.get("output_tokens")
            )
            base_provider["requests"] = _as_non_negative_int(provider_raw.get("requests"))

    totals_raw = raw.get("totals")
    if isinstance(totals_raw, dict):
        base["totals"]["input_tokens"] = _as_non_negative_int(totals_raw.get("input_tokens"))
        base["totals"]["output_tokens"] = _as_non_negative_int(totals_raw.get("output_tokens"))
        base["totals"]["requests"] = _as_non_negative_int(totals_raw.get("requests"))
    else:
        base["totals"]["input_tokens"] = sum(
            base["providers"][provider]["input_tokens"] for provider in _PROVIDERS
        )
        base["totals"]["output_tokens"] = sum(
            base["providers"][provider]["output_tokens"] for provider in _PROVIDERS
        )
        base["totals"]["requests"] = sum(
            base["providers"][provider]["requests"] for provider in _PROVIDERS
        )

    updated_at = raw.get("updated_at")
    if isinstance(updated_at, str) and updated_at.strip():
        base["updated_at"] = updated_at.strip()
    return base


def _read_stats_unlocked() -> Dict[str, Any]:
    path = token_usage_file_path()
    if not path.exists():
        return _empty_stats()
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("TOKEN USAGE READ ERROR: %s %s", type(exc).__name__, exc)
        return _empty_stats()
    return _normalize_stats(data)


def _create_backup_unlocked(source_path: Path) -> None:
    if not source_path.exists():
        return

    backup_dir = token_usage_backup_dir_path()
    backup_dir.mkdir(parents=True, exist_ok=True)
    payload = source_path.read_bytes()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")

    for attempt in range(0, 1000):
        suffix = f"_{attempt:03d}" if attempt else ""
        backup_path = backup_dir / f"{_BACKUP_PREFIX}{timestamp}{suffix}.json"
        try:
            with backup_path.open("xb") as handle:
                handle.write(payload)
            break
        except FileExistsError:
            continue
        except OSError as exc:
            logger.warning("TOKEN USAGE BACKUP ERROR: %s %s", type(exc).__name__, exc)
            return

    backups = sorted(
        (
            path
            for path in backup_dir.glob(f"{_BACKUP_PREFIX}*.json")
            if path.is_file()
        ),
        key=lambda item: item.stat().st_mtime,
    )
    overflow = len(backups) - _MAX_BACKUPS
    if overflow <= 0:
        return
    for old_path in backups[:overflow]:
        try:
            old_path.unlink(missing_ok=True)
        except OSError:
            continue


def _write_stats_unlocked(stats: Dict[str, Any]) -> None:
    path = token_usage_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        _create_backup_unlocked(path)

    tmp_path = path.parent / f"{path.stem}.{uuid.uuid4().hex}.tmp"
    try:
        with tmp_path.open("x", encoding="utf-8") as handle:
            json.dump(stats, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def get_token_usage_snapshot() -> Dict[str, Any]:
    with _USAGE_LOCK:
        return copy.deepcopy(_read_stats_unlocked())


def record_token_usage(
    provider: str,
    input_tokens: int,
    output_tokens: int,
    *,
    request_count: int = 1,
) -> None:
    normalized_provider = (provider or "").strip().lower()
    if normalized_provider not in _PROVIDERS:
        return

    in_tokens = _as_non_negative_int(input_tokens)
    out_tokens = _as_non_negative_int(output_tokens)
    requests = _as_non_negative_int(request_count)
    if requests <= 0:
        requests = 1

    try:
        with _USAGE_LOCK:
            stats = _read_stats_unlocked()
            provider_stats = stats["providers"][normalized_provider]
            provider_stats["input_tokens"] += in_tokens
            provider_stats["output_tokens"] += out_tokens
            provider_stats["requests"] += requests

            totals = stats["totals"]
            totals["input_tokens"] += in_tokens
            totals["output_tokens"] += out_tokens
            totals["requests"] += requests
            stats["updated_at"] = _now_iso()
            _write_stats_unlocked(stats)
    except Exception as exc:
        logger.warning("TOKEN USAGE WRITE ERROR: %s %s", type(exc).__name__, exc)


def reset_token_usage() -> Dict[str, Any]:
    with _USAGE_LOCK:
        stats = _empty_stats()
        _write_stats_unlocked(stats)
        return copy.deepcopy(stats)


__all__ = [
    "token_usage_file_path",
    "token_usage_backup_dir_path",
    "get_token_usage_snapshot",
    "record_token_usage",
    "reset_token_usage",
]
