from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from ..core.config import settings


_NAME_CONNECTORS = {"de", "do", "da", "dos", "das", "e"}


def normalize_person_name(value: str) -> str:
    normalized = " ".join(str(value or "").strip().split())
    if len(normalized) < 3:
        raise ValueError("O nome deve ter ao menos 3 caracteres")
    return " ".join(_normalize_person_name_word(part) for part in normalized.split(" "))


def merge_provider_date_and_time(date_value: str, time_value: str) -> datetime:
    parsed = datetime.strptime(
        f"{str(date_value or '').strip()} {str(time_value or '').strip()}",
        "%d/%m/%Y %H:%M:%S",
    )
    return parsed.replace(tzinfo=ZoneInfo(settings.tz_name))


def _normalize_person_name_word(value: str) -> str:
    lowered = str(value or "").lower()
    if lowered in _NAME_CONNECTORS:
        return lowered
    if "-" in lowered:
        return "-".join(_normalize_person_name_word(part) for part in lowered.split("-"))
    return lowered[:1].upper() + lowered[1:]
