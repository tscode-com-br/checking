from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import User
from .time_utils import now_sgt


def mark_user_active(user: User, *, activity_time=None) -> None:
    timestamp = activity_time or now_sgt()
    user.last_active_at = timestamp
    user.inactivity_days = 0


def sync_user_inactivity(db: Session, *, reference_time=None) -> bool:
    now_value = reference_time or now_sgt()
    changed = False
    users = db.execute(select(User)).scalars().all()

    for user in users:
        baseline = user.last_active_at
        inactivity_days = max((now_value.date() - baseline.date()).days, 0)
        if user.inactivity_days != inactivity_days:
            user.inactivity_days = inactivity_days
            changed = True

    if changed:
        db.flush()

    return changed