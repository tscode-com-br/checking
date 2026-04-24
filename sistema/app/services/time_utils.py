from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..core.config import settings
from .project_catalog import get_project_by_name


SYSTEM_TIMEZONE_FALLBACK_LABEL = "Sistema"


@dataclass(frozen=True)
class ResolvedProjectTimezone:
    project_name: str | None
    country_name: str
    timezone_name: str
    timezone: ZoneInfo
    timezone_label: str


def resolve_system_timezone_name() -> str:
    return str(settings.tz_name).strip() or "UTC"


def resolve_timezone_name(timezone_name: str | None = None) -> str:
    normalized = str(timezone_name or "").strip()
    return normalized or resolve_system_timezone_name()


def resolve_timezone(timezone_name: str | None = None) -> ZoneInfo:
    return ZoneInfo(resolve_timezone_name(timezone_name))


def _coerce_aware_reference_time(reference_time: datetime | None = None) -> datetime:
    resolved = reference_time or datetime.now(timezone.utc)
    if resolved.tzinfo is None:
        return resolved.replace(tzinfo=timezone.utc)
    return resolved


def format_timezone_offset(timezone_name: str | None, *, reference_time: datetime | None = None) -> str:
    target_timezone = resolve_timezone(timezone_name)
    target_offset = _coerce_aware_reference_time(reference_time).astimezone(target_timezone).utcoffset() or timedelta(0)
    total_minutes = int(target_offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    absolute_minutes = abs(total_minutes)
    hours, minutes = divmod(absolute_minutes, 60)
    if minutes == 0:
        return f"{sign}{hours}"
    return f"{sign}{hours}:{minutes:02d}"


def build_timezone_label(
    *,
    country_name: str | None,
    timezone_name: str | None,
    reference_time: datetime | None = None,
    fallback_country_name: str = SYSTEM_TIMEZONE_FALLBACK_LABEL,
) -> str:
    resolved_country_name = str(country_name or "").strip() or fallback_country_name
    return f"{resolved_country_name} ({format_timezone_offset(timezone_name, reference_time=reference_time)})"


def build_timezone_context(
    *,
    project_name: str | None,
    country_name: str | None,
    timezone_name: str | None,
    reference_time: datetime | None = None,
    fallback_country_name: str = SYSTEM_TIMEZONE_FALLBACK_LABEL,
) -> ResolvedProjectTimezone:
    resolved_timezone_name = resolve_timezone_name(timezone_name)
    resolved_country_name = str(country_name or "").strip() or fallback_country_name
    return ResolvedProjectTimezone(
        project_name=project_name,
        country_name=resolved_country_name,
        timezone_name=resolved_timezone_name,
        timezone=resolve_timezone(resolved_timezone_name),
        timezone_label=build_timezone_label(
            country_name=resolved_country_name,
            timezone_name=resolved_timezone_name,
            reference_time=reference_time,
            fallback_country_name=fallback_country_name,
        ),
    )


def resolve_project_timezone_context(
    db: Session,
    project_name: str | None,
    *,
    reference_time: datetime | None = None,
    fallback_country_name: str = SYSTEM_TIMEZONE_FALLBACK_LABEL,
) -> ResolvedProjectTimezone:
    project = get_project_by_name(db, project_name) if project_name else None
    return build_timezone_context(
        project_name=project.name if project is not None else project_name,
        country_name=project.country_name if project is not None else None,
        timezone_name=project.timezone_name if project is not None else None,
        reference_time=reference_time,
        fallback_country_name=fallback_country_name,
    )


def resolve_project_timezone_name(db: Session, project_name: str | None) -> str:
    return resolve_project_timezone_context(db, project_name).timezone_name


def resolve_project_timezone(db: Session, project_name: str | None) -> ZoneInfo:
    return resolve_project_timezone_context(db, project_name).timezone


def resolve_project_timezone_label(
    db: Session,
    project_name: str | None,
    *,
    reference_time: datetime | None = None,
    fallback_country_name: str = SYSTEM_TIMEZONE_FALLBACK_LABEL,
) -> str:
    return resolve_project_timezone_context(
        db,
        project_name,
        reference_time=reference_time,
        fallback_country_name=fallback_country_name,
    ).timezone_label


def now_sgt() -> datetime:
    return datetime.now(tz=resolve_timezone())


def format_sgt(dt: datetime) -> str:
    local_dt = dt.astimezone(resolve_timezone())
    return local_dt.strftime("%Y-%m-%d-%H-%M-%S")
