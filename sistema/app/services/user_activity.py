from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import User
from .time_utils import now_sgt


SINGAPORE_TZ = ZoneInfo(settings.tz_name)
SECONDS_PER_DAY = 24 * 60 * 60
INACTIVE_AFTER_BUSINESS_DAYS = 3


def _to_singapore_time(value: datetime) -> datetime:
    return value.astimezone(SINGAPORE_TZ)


def calculate_business_inactivity_seconds(last_active_at: datetime | None, *, reference_time: datetime | None = None) -> int:
    if last_active_at is None:
        return 0

    start = _to_singapore_time(last_active_at)
    end = _to_singapore_time(reference_time or now_sgt())
    if end <= start:
        return 0

    total_seconds = 0.0
    cursor = start

    while cursor.date() < end.date():
        next_midnight = datetime.combine(cursor.date() + timedelta(days=1), time.min, tzinfo=SINGAPORE_TZ)
        if cursor.weekday() < 5:
            total_seconds += (next_midnight - cursor).total_seconds()
        cursor = next_midnight

    if cursor.weekday() < 5:
        total_seconds += (end - cursor).total_seconds()

    return max(int(total_seconds), 0)


def calculate_inactivity_days(last_active_at: datetime | None, *, reference_time: datetime | None = None) -> int:
    inactivity_seconds = calculate_business_inactivity_seconds(last_active_at, reference_time=reference_time)
    return inactivity_seconds // SECONDS_PER_DAY


def calculate_singapore_calendar_day_diff(event_time: datetime | None, *, reference_time: datetime | None = None) -> int:
    if event_time is None:
        return 0

    current_time = reference_time or now_sgt()
    current_local = _to_singapore_time(current_time)
    event_local = _to_singapore_time(event_time)
    return max((current_local.date() - event_local.date()).days, 0)


def has_missing_checkout_since_midnight(checkin_time: datetime | None, *, reference_time: datetime | None = None) -> bool:
    return calculate_singapore_calendar_day_diff(checkin_time, reference_time=reference_time) > 0


def is_user_inactive(last_active_at: datetime | None, *, reference_time: datetime | None = None) -> bool:
    current_time = reference_time or now_sgt()
    if _to_singapore_time(current_time).weekday() >= 5:
        return False

    inactivity_days = calculate_inactivity_days(last_active_at, reference_time=current_time)
    return inactivity_days >= INACTIVE_AFTER_BUSINESS_DAYS


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