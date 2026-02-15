"""Pure calculations and text builders for stats handlers."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from bot.handlers_sheet import _normalize_rating, _parse_timestamp
from bot.ui_texts import (
    TOKEN_USAGE_BACKUP_LABEL,
    TOKEN_USAGE_FILE_LABEL,
    TOKEN_USAGE_HEADER,
    TOKEN_USAGE_PERSISTENCE_NOTE,
    TOKEN_USAGE_RESET_NOTE,
)
from core.normalization import normalize_owner

_OWNERS = ("муж", "жена")
_RATING_KEYS = ("Оценка", "РћС†РµРЅРєР°", "Rating", "rating")
_OWNER_KEYS = ("Владелец", "Р’Р»Р°РґРµР»РµС†", "Чье", "Р§СЊРµ", "Owner")
_TIMESTAMP_KEYS = ("Добавлено", "Р”РѕР±Р°РІР»РµРЅРѕ", "Timestamp", "Дата", "Р”Р°С‚Р°", "Added")


def _owner_stats_template() -> Dict[str, Dict[str, float]]:
    return {owner: {"count": 0.0, "rated_count": 0.0, "rating_sum": 0.0} for owner in _OWNERS}


def _row_value(row: Dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = row.get(key)
        if value:
            return str(value)
    return ""


def _row_rating(row: Dict[str, str]) -> float:
    return _normalize_rating(_row_value(row, _RATING_KEYS))


def _row_timestamp(row: Dict[str, str]) -> Optional[datetime]:
    raw = _row_value(row, _TIMESTAMP_KEYS)
    if not raw:
        return None
    return _parse_timestamp(raw)


def _avg_for(owner_stats: Dict[str, Dict[str, float]], owner: str) -> Optional[float]:
    rated_count = owner_stats[owner]["rated_count"]
    if rated_count <= 0:
        return None
    return owner_stats[owner]["rating_sum"] / rated_count


def _quality_score(
    owner_stats: Dict[str, Dict[str, float]],
    owner: str,
    prior_rating: float,
) -> float:
    avg = _avg_for(owner_stats, owner)
    if avg is None:
        return 0.0
    rated_count = owner_stats[owner]["rated_count"]
    confidence = min(rated_count / 5.0, 1.0)
    return prior_rating + (avg - prior_rating) * confidence


def build_stats_text(records: List[Dict[str, str]]) -> str:
    ratings: List[float] = []
    for row in records:
        rating_value = _row_rating(row)
        if rating_value > 0:
            ratings.append(rating_value)

    total = len(records)
    rated = len(ratings)
    if rated:
        avg_rating = sum(ratings) / rated
        min_rating = min(ratings)
        max_rating = max(ratings)
        return (
            "📉 Статистика по оценкам:\n"
            f"Всего записей: {total}\n"
            f"С оценкой: {rated}\n"
            f"Средняя: {avg_rating:.1f}/10\n"
            f"Мин: {min_rating:.1f}/10\n"
            f"Макс: {max_rating:.1f}/10"
        )

    return (
        "📉 Статистика по оценкам:\n"
        f"Всего записей: {total}\n"
        "Пока нет оценок для расчета статистики."
    )


def build_winner_text(
    records: List[Dict[str, str]],
    *,
    target_month: datetime,
    month_name: str,
) -> Tuple[int, str]:
    owner_stats = _owner_stats_template()

    for row in records:
        owner = normalize_owner(_row_value(row, _OWNER_KEYS))
        if owner not in owner_stats:
            continue

        timestamp = _row_timestamp(row)
        if (
            not timestamp
            or timestamp.year != target_month.year
            or timestamp.month != target_month.month
        ):
            continue

        owner_stats[owner]["count"] += 1
        rating = _row_rating(row)
        if rating > 0:
            owner_stats[owner]["rated_count"] += 1
            owner_stats[owner]["rating_sum"] += rating

    month_total = int(sum(item["count"] for item in owner_stats.values()))
    if month_total == 0:
        return (
            month_total,
            f"🏁 Победитель месяца ({month_name}):\n"
            "За выбранный месяц нет фильмов с владельцем «муж» или «жена».",
        )

    avg_husband = _avg_for(owner_stats, "муж")
    avg_wife = _avg_for(owner_stats, "жена")

    month_rated_total = owner_stats["муж"]["rated_count"] + owner_stats["жена"]["rated_count"]
    month_rating_sum = owner_stats["муж"]["rating_sum"] + owner_stats["жена"]["rating_sum"]
    prior_rating = (month_rating_sum / month_rated_total) if month_rated_total > 0 else 6.0

    quality_husband = _quality_score(owner_stats, "муж", prior_rating)
    quality_wife = _quality_score(owner_stats, "жена", prior_rating)
    activity_husband = owner_stats["муж"]["count"]
    activity_wife = owner_stats["жена"]["count"]

    if quality_husband <= 0 and quality_wife <= 0:
        quality_winner = "Лига качества: победитель не определен (нет оценок)."
    elif abs(quality_husband - quality_wife) < 1e-9:
        quality_winner = f"Лига качества: ничья ({quality_husband:.2f})."
    elif quality_husband > quality_wife:
        quality_winner = (
            f"Лига качества: победил муж ({quality_husband:.2f} против {quality_wife:.2f})."
        )
    else:
        quality_winner = (
            f"Лига качества: победила жена ({quality_wife:.2f} против {quality_husband:.2f})."
        )

    if abs(activity_husband - activity_wife) < 1e-9:
        activity_winner = f"Лига активности: ничья ({int(activity_husband)} предложений)."
    elif activity_husband > activity_wife:
        activity_winner = (
            f"Лига активности: победил муж ({int(activity_husband)} против {int(activity_wife)} предложений)."
        )
    else:
        activity_winner = (
            f"Лига активности: победила жена ({int(activity_wife)} против {int(activity_husband)} предложений)."
        )

    husband_avg_text = f"{avg_husband:.2f}/10" if avg_husband is not None else "нет оценок"
    wife_avg_text = f"{avg_wife:.2f}/10" if avg_wife is not None else "нет оценок"

    text = (
        f"🏁 Итоги месяца ({month_name}):\n"
        f"{quality_winner}\n"
        f"{activity_winner}\n\n"
        "Статистика за выбранный месяц:\n"
        f"• Муж: предложил {int(activity_husband)}, "
        f"оценок {int(owner_stats['муж']['rated_count'])}, "
        f"средний {husband_avg_text}, качество {quality_husband:.2f}\n"
        f"• Жена: предложила {int(activity_wife)}, "
        f"оценок {int(owner_stats['жена']['rated_count'])}, "
        f"средний {wife_avg_text}, качество {quality_wife:.2f}\n\n"
        "Качество = средний балл с поправкой на размер выборки."
    )
    return month_total, text


def _format_int(value: int) -> str:
    return f"{max(int(value), 0):,}".replace(",", " ")


def _provider_usage(stats: Dict[str, object], provider: str) -> Dict[str, int]:
    providers = stats.get("providers")
    if not isinstance(providers, dict):
        return {"input_tokens": 0, "output_tokens": 0, "requests": 0}
    raw = providers.get(provider)
    if not isinstance(raw, dict):
        return {"input_tokens": 0, "output_tokens": 0, "requests": 0}
    return {
        "input_tokens": int(raw.get("input_tokens", 0) or 0),
        "output_tokens": int(raw.get("output_tokens", 0) or 0),
        "requests": int(raw.get("requests", 0) or 0),
    }


def build_token_usage_text(
    stats: Dict[str, object],
    *,
    file_path: str,
    backup_dir: str,
    was_reset: bool = False,
) -> str:
    gemini = _provider_usage(stats, "gemini")
    mistral = _provider_usage(stats, "mistral")

    totals_raw = stats.get("totals")
    if isinstance(totals_raw, dict):
        total_in = int(totals_raw.get("input_tokens", 0) or 0)
        total_out = int(totals_raw.get("output_tokens", 0) or 0)
        total_requests = int(totals_raw.get("requests", 0) or 0)
    else:
        total_in = gemini["input_tokens"] + mistral["input_tokens"]
        total_out = gemini["output_tokens"] + mistral["output_tokens"]
        total_requests = gemini["requests"] + mistral["requests"]

    lines = [TOKEN_USAGE_HEADER]
    if was_reset:
        lines.append(TOKEN_USAGE_RESET_NOTE)
    lines.extend(
        [
            f"• Gemini: in {_format_int(gemini['input_tokens'])}, "
            f"out {_format_int(gemini['output_tokens'])}, "
            f"запросов {_format_int(gemini['requests'])}",
            f"• Mistral: in {_format_int(mistral['input_tokens'])}, "
            f"out {_format_int(mistral['output_tokens'])}, "
            f"запросов {_format_int(mistral['requests'])}",
            "",
            f"Итого: in {_format_int(total_in)}, out {_format_int(total_out)}, "
            f"запросов {_format_int(total_requests)}",
            TOKEN_USAGE_PERSISTENCE_NOTE,
            "",
            f"{TOKEN_USAGE_FILE_LABEL}: {file_path}",
            f"{TOKEN_USAGE_BACKUP_LABEL}: {backup_dir}",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "build_stats_text",
    "build_winner_text",
    "build_token_usage_text",
]
