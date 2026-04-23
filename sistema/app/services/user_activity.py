from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import User
from .time_utils import now_sgt


SINGAPORE_TZ = ZoneInfo(settings.tz_name)
SECONDS_PER_DAY = 24 * 60 * 60
INACTIVE_AFTER_CONTINUOUS_HOURS = 24


def _to_singapore_time(value: datetime) -> datetime:
    return value.astimezone(SINGAPORE_TZ)


def calculate_inactivity_seconds(last_active_at: datetime | None, *, reference_time: datetime | None = None) -> int:
    if last_active_at is None:
        return 0

    start = _to_singapore_time(last_active_at)
    end = _to_singapore_time(reference_time or now_sgt())
    if end <= start:
        return 0

    return max(int((end - start).total_seconds()), 0)


def calculate_inactivity_days(last_active_at: datetime | None, *, reference_time: datetime | None = None) -> int:
    inactivity_seconds = calculate_inactivity_seconds(last_active_at, reference_time=reference_time)
    return inactivity_seconds // SECONDS_PER_DAY


def has_exceeded_continuous_inactivity_window(
    event_time: datetime | None,
    *,
    reference_time: datetime | None = None,
) -> bool:
    inactivity_seconds = calculate_inactivity_seconds(event_time, reference_time=reference_time)
    return inactivity_seconds >= INACTIVE_AFTER_CONTINUOUS_HOURS * 60 * 60


def is_user_inactive(last_active_at: datetime | None, *, reference_time: datetime | None = None) -> bool:
    return has_exceeded_continuous_inactivity_window(last_active_at, reference_time=reference_time)


def mark_user_active(user: User, *, activity_time=None) -> None:
    timestamp = activity_time or now_sgt()
    user.last_active_at = timestamp
    user.inactivity_days = 0


def sync_user_inactivity(db: Session, *, reference_time=None) -> bool:
    now_value = reference_time or now_sgt()
    changed = False
    users = db.execute(select(User)).scalars().all()

    for user in users:
        inactivity_days = calculate_inactivity_days(user.last_active_at, reference_time=now_value)
        if user.inactivity_days != inactivity_days:
            user.inactivity_days = inactivity_days
            changed = True

    if changed:
        db.flush()

    return changed