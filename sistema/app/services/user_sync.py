from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import User, UserSyncEvent
from ..schemas import MobileSyncStateResponse
from .time_utils import now_sgt
from .user_activity import mark_user_active

APP_IMPORTED_USER_NAME = "Oriundo do Aplicativo"


def normalize_user_key(value: str) -> str:
    return value.strip().upper()


def normalize_event_time(value: datetime) -> datetime:
    target_tz = ZoneInfo(settings.tz_name)
    if value.tzinfo is None:
        return value.replace(tzinfo=target_tz)
    return value.astimezone(target_tz)


def find_user_by_rfid(db: Session, rfid: str) -> User | None:
    return db.execute(select(User).where(User.rfid == rfid)).scalar_one_or_none()


def find_user_by_chave(db: Session, chave: str) -> User | None:
    normalized_key = normalize_user_key(chave)
    return db.execute(select(User).where(User.chave == normalized_key)).scalar_one_or_none()


def ensure_mobile_user(db: Session, *, chave: str, projeto: str) -> tuple[User, bool]:
    normalized_key = normalize_user_key(chave)
    user = find_user_by_chave(db, normalized_key)
    if user is not None:
        return user, False

    timestamp = now_sgt()
    user = User(
        rfid=None,
        chave=normalized_key,
        nome=APP_IMPORTED_USER_NAME,
        projeto=projeto,
        local=None,
        checkin=None,
        time=None,
        last_active_at=timestamp,
        inactivity_days=0,
    )
    db.add(user)
    db.flush()
    return user, True


def apply_user_state(
    user: User,
    *,
    action: str,
    event_time: datetime,
    projeto: str | None = None,
    local: str | None = None,
) -> None:
    user.checkin = action == "checkin"
    user.time = event_time
    if projeto:
        user.projeto = projeto
    if local is not None:
        user.local = local
    mark_user_active(user, activity_time=event_time)


def create_user_sync_event(
    db: Session,
    *,
    user: User,
    source: str,
    action: str,
    event_time: datetime,
    projeto: str | None,
    local: str | None,
    source_request_id: str | None,
    device_id: str | None,
) -> UserSyncEvent:
    sync_event = UserSyncEvent(
        user_id=user.id,
        chave=user.chave,
        rfid=user.rfid,
        source=source,
        action=action,
        projeto=projeto,
        local=local,
        event_time=event_time,
        created_at=now_sgt(),
        source_request_id=source_request_id,
        device_id=device_id,
    )
    db.add(sync_event)
    return sync_event


def get_latest_sync_event(db: Session, *, user_id: int, action: str) -> UserSyncEvent | None:
    return db.execute(
        select(UserSyncEvent)
        .where(UserSyncEvent.user_id == user_id, UserSyncEvent.action == action)
        .order_by(desc(UserSyncEvent.event_time), desc(UserSyncEvent.id))
        .limit(1)
    ).scalar_one_or_none()


def build_mobile_sync_state(db: Session, *, chave: str) -> MobileSyncStateResponse:
    user = find_user_by_chave(db, chave)
    if user is None:
        return MobileSyncStateResponse(found=False, chave=normalize_user_key(chave))

    latest_checkin = get_latest_sync_event(db, user_id=user.id, action="checkin")
    latest_checkout = get_latest_sync_event(db, user_id=user.id, action="checkout")
    current_action = None
    if user.checkin is True:
        current_action = "checkin"
    elif user.checkin is False:
        current_action = "checkout"

    return MobileSyncStateResponse(
        found=True,
        chave=user.chave,
        nome=user.nome,
        projeto=user.projeto,
        current_action=current_action,
        current_event_time=user.time,
        last_checkin_at=latest_checkin.event_time if latest_checkin is not None else (user.time if user.checkin is True else None),
        last_checkout_at=latest_checkout.event_time if latest_checkout is not None else (user.time if user.checkin is False else None),
    )