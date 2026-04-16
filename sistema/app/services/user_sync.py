from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import CheckEvent, User, UserSyncEvent
from ..schemas import MobileSyncStateResponse, WebCheckHistoryResponse
from .time_utils import now_sgt
from .user_activity import mark_user_active

APP_IMPORTED_USER_NAME = "Oriundo do Aplicativo"
WEB_IMPORTED_USER_NAME = "Oriundo da Web"
SYNC_EVENT_FALLBACK_STATUSES = ("queued", "updated", "success", "synced", "created", "submitted")


@dataclass(frozen=True)
class ResolvedUserActivity:
    action: str
    event_time: datetime
    local: str | None
    ontime: bool | None


def normalize_user_key(value: str) -> str:
    return value.strip().upper()


def normalize_event_time(value: datetime) -> datetime:
    target_tz = ZoneInfo(settings.tz_name)
    if value.tzinfo is None:
        return value.replace(tzinfo=target_tz)
    return value.astimezone(target_tz)


def is_same_singapore_day(first: datetime, second: datetime) -> bool:
    return normalize_event_time(first).date() == normalize_event_time(second).date()


def should_enqueue_forms_for_action(
    *,
    latest_activity: ResolvedUserActivity | None,
    action: str,
    event_time: datetime,
) -> bool:
    if latest_activity is None:
        return True

    return latest_activity.action != action or not is_same_singapore_day(latest_activity.event_time, event_time)


def find_user_by_rfid(db: Session, rfid: str) -> User | None:
    return db.execute(select(User).where(User.rfid == rfid)).scalar_one_or_none()


def find_user_by_chave(db: Session, chave: str) -> User | None:
    normalized_key = normalize_user_key(chave)
    return db.execute(select(User).where(User.chave == normalized_key)).scalar_one_or_none()


def ensure_placeholder_user(
    db: Session,
    *,
    chave: str,
    projeto: str,
    nome: str,
) -> tuple[User, bool]:
    normalized_key = normalize_user_key(chave)
    user = find_user_by_chave(db, normalized_key)
    if user is not None:
        return user, False

    timestamp = now_sgt()
    user = User(
        rfid=None,
        chave=normalized_key,
        nome=nome,
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


def ensure_mobile_user(db: Session, *, chave: str, projeto: str) -> tuple[User, bool]:
    return ensure_placeholder_user(
        db,
        chave=chave,
        projeto=projeto,
        nome=APP_IMPORTED_USER_NAME,
    )


def ensure_web_user(db: Session, *, chave: str, projeto: str) -> tuple[User, bool]:
    return ensure_placeholder_user(
        db,
        chave=chave,
        projeto=projeto,
        nome=WEB_IMPORTED_USER_NAME,
    )


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
    ontime: bool = True,
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
        ontime=ontime,
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


def get_latest_user_sync_event(db: Session, *, user_id: int) -> UserSyncEvent | None:
    return db.execute(
        select(UserSyncEvent)
        .where(UserSyncEvent.user_id == user_id, UserSyncEvent.action.in_(("checkin", "checkout")))
        .order_by(desc(UserSyncEvent.event_time), desc(UserSyncEvent.id))
        .limit(1)
    ).scalar_one_or_none()


def get_latest_check_event(db: Session, *, rfid: str, action: str) -> CheckEvent | None:
    return db.execute(
        select(CheckEvent)
        .where(
            CheckEvent.rfid == rfid,
            CheckEvent.action == action,
            CheckEvent.status.in_(SYNC_EVENT_FALLBACK_STATUSES),
        )
        .order_by(desc(CheckEvent.event_time), desc(CheckEvent.id))
        .limit(1)
    ).scalar_one_or_none()


def get_latest_check_activity_event(db: Session, *, rfid: str) -> CheckEvent | None:
    return db.execute(
        select(CheckEvent)
        .where(
            CheckEvent.rfid == rfid,
            CheckEvent.action.in_(("checkin", "checkout")),
            CheckEvent.status.in_(SYNC_EVENT_FALLBACK_STATUSES),
        )
        .order_by(desc(CheckEvent.event_time), desc(CheckEvent.id))
        .limit(1)
    ).scalar_one_or_none()


def resolve_latest_user_activity(db: Session, *, user: User) -> ResolvedUserActivity | None:
    candidates: list[tuple[datetime, int, ResolvedUserActivity]] = []

    if user.time is not None and user.checkin is not None:
        candidates.append(
            (
                user.time,
                2,
                ResolvedUserActivity(
                    action="checkin" if user.checkin else "checkout",
                    event_time=user.time,
                    local=user.local,
                    ontime=True,
                ),
            )
        )

    latest_sync = get_latest_user_sync_event(db, user_id=user.id)
    if latest_sync is not None:
        candidates.append(
            (
                latest_sync.event_time,
                3,
                ResolvedUserActivity(
                    action=latest_sync.action,
                    event_time=latest_sync.event_time,
                    local=latest_sync.local,
                    ontime=latest_sync.ontime,
                ),
            )
        )

    if user.rfid:
        latest_check_event = get_latest_check_activity_event(db, rfid=user.rfid)
        if latest_check_event is not None:
            candidates.append(
                (
                    latest_check_event.event_time,
                    1,
                    ResolvedUserActivity(
                        action=latest_check_event.action,
                        event_time=latest_check_event.event_time,
                        local=latest_check_event.local,
                        ontime=(latest_check_event.ontime if latest_check_event.ontime is not None else True),
                    ),
                )
            )

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][2]


def ensure_current_user_state_event(db: Session, *, user: User) -> None:
    if user.time is None or user.checkin is None:
        return

    action = "checkin" if user.checkin else "checkout"
    existing = db.execute(
        select(UserSyncEvent)
        .where(
            UserSyncEvent.user_id == user.id,
            UserSyncEvent.action == action,
            UserSyncEvent.event_time == user.time,
        )
        .limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        return

    create_user_sync_event(
        db,
        user=user,
        source="state_import",
        action=action,
        event_time=user.time,
        projeto=user.projeto,
        local=user.local,
        ontime=True,
        source_request_id=None,
        device_id=None,
    )


def build_mobile_sync_state(db: Session, *, chave: str) -> MobileSyncStateResponse:
    user = find_user_by_chave(db, chave)
    if user is None:
        return MobileSyncStateResponse(found=False, chave=normalize_user_key(chave))

    latest_checkin = get_latest_sync_event(db, user_id=user.id, action="checkin")
    latest_checkout = get_latest_sync_event(db, user_id=user.id, action="checkout")
    fallback_checkin = get_latest_check_event(db, rfid=user.rfid, action="checkin") if user.rfid else None
    fallback_checkout = get_latest_check_event(db, rfid=user.rfid, action="checkout") if user.rfid else None
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
        current_local=user.local,
        last_checkin_at=(
            latest_checkin.event_time
            if latest_checkin is not None
            else (fallback_checkin.event_time if fallback_checkin is not None else (user.time if user.checkin is True else None))
        ),
        last_checkout_at=(
            latest_checkout.event_time
            if latest_checkout is not None
            else (fallback_checkout.event_time if fallback_checkout is not None else (user.time if user.checkin is False else None))
        ),
    )


def build_web_check_history_state(db: Session, *, chave: str) -> WebCheckHistoryResponse:
    state = build_mobile_sync_state(db, chave=normalize_user_key(chave))
    return WebCheckHistoryResponse(
        found=state.found,
        chave=state.chave,
        projeto=state.projeto,
        current_action=state.current_action,
        current_local=state.current_local,
        last_checkin_at=state.last_checkin_at,
        last_checkout_at=state.last_checkout_at,
    )