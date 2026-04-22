from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import CheckEvent, User, UserSyncEvent
from ..schemas import MobileSyncStateResponse, WebCheckHistoryResponse
from .checking_history import record_checking_history
from .time_utils import now_sgt
from .user_activity import mark_user_active

APP_IMPORTED_USER_NAME = "Oriundo do Aplicativo"
WEB_IMPORTED_USER_NAME = "Oriundo da Web"
PROVIDER_ACTIVITY_LOCAL = "Forms"
SYNC_EVENT_FALLBACK_STATUSES = ("queued", "updated", "success", "synced", "created", "submitted")
LOW_PRIORITY_SYNC_SOURCES = frozenset(("state_import",))
SECONDARY_SYNC_SOURCES = frozenset(("provider",))
INTERNAL_DECISION_IGNORED_SYNC_SOURCES = frozenset(("provider", "state_import"))
INTERNAL_DECISION_IGNORED_CHECK_EVENT_SOURCES = frozenset(("provider",))


@dataclass(frozen=True)
class ResolvedUserActivity:
    action: str
    event_time: datetime
    local: str | None
    ontime: bool | None
    source: str | None = None


def normalize_user_key(value: str) -> str:
    return value.strip().upper()


def normalize_event_time(value: datetime) -> datetime:
    target_tz = ZoneInfo(settings.tz_name)
    if value.tzinfo is None:
        return value.replace(tzinfo=target_tz)
    return value.astimezone(target_tz)


def is_same_singapore_day(first: datetime, second: datetime) -> bool:
    return normalize_event_time(first).date() == normalize_event_time(second).date()


def normalize_sync_source(value: str | None) -> str:
    return str(value or "").strip().lower()


def is_sync_source_included(source: str | None, sources: frozenset[str]) -> bool:
    if not sources:
        return False
    return normalize_sync_source(source) in sources


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


def resolve_activity_local(*, local: str | None, source: str | None) -> str | None:
    if local is not None:
        return local
    if normalize_sync_source(source) == "provider":
        return PROVIDER_ACTIVITY_LOCAL
    return None


def get_sync_source_priority(source: str | None) -> int:
    normalized_source = normalize_sync_source(source)
    if normalized_source in LOW_PRIORITY_SYNC_SOURCES:
        return 0
    if normalized_source in SECONDARY_SYNC_SOURCES:
        return 1
    return 2


def filter_sync_events_by_sources(
    events: list[UserSyncEvent],
    *,
    ignored_sources: frozenset[str] = frozenset(),
) -> list[UserSyncEvent]:
    if not ignored_sources:
        return events
    return [event for event in events if not is_sync_source_included(event.source, ignored_sources)]


def list_user_sync_events(
    db: Session,
    *,
    user_id: int,
    action: str | None = None,
) -> list[UserSyncEvent]:
    query = select(UserSyncEvent).where(UserSyncEvent.user_id == user_id)
    if action is None:
        query = query.where(UserSyncEvent.action.in_(("checkin", "checkout")))
    else:
        query = query.where(UserSyncEvent.action == action)

    return db.execute(
        query.order_by(desc(UserSyncEvent.event_time), desc(UserSyncEvent.id))
    ).scalars().all()


def select_preferred_sync_event(events: list[UserSyncEvent]) -> UserSyncEvent | None:
    if not events:
        return None

    latest_day = normalize_event_time(events[0].event_time).date()
    same_day_events = [
        event
        for event in events
        if normalize_event_time(event.event_time).date() == latest_day
    ]
    same_day_events.sort(
        key=lambda event: (
            get_sync_source_priority(event.source),
            normalize_event_time(event.event_time),
            event.id,
        ),
        reverse=True,
    )
    return same_day_events[0]


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
    record_checking_history(
        db,
        chave=user.chave,
        action=action,
        projeto=projeto or user.projeto,
        event_time=event_time,
        ontime=ontime,
    )
    return sync_event


def get_latest_sync_event(
    db: Session,
    *,
    user_id: int,
    action: str,
    ignored_sources: frozenset[str] = frozenset(),
) -> UserSyncEvent | None:
    return select_preferred_sync_event(
        filter_sync_events_by_sources(
            list_user_sync_events(db, user_id=user_id, action=action),
            ignored_sources=ignored_sources,
        )
    )


def get_latest_user_sync_event(
    db: Session,
    *,
    user_id: int,
    ignored_sources: frozenset[str] = frozenset(),
) -> UserSyncEvent | None:
    candidates = [
        event
        for event in (
            get_latest_sync_event(db, user_id=user_id, action="checkin", ignored_sources=ignored_sources),
            get_latest_sync_event(db, user_id=user_id, action="checkout", ignored_sources=ignored_sources),
        )
        if event is not None
    ]
    if not candidates:
        return None

    candidates.sort(
        key=lambda event: (
            normalize_event_time(event.event_time),
            get_sync_source_priority(event.source),
            event.id,
        ),
        reverse=True,
    )
    return candidates[0]


def get_latest_user_sync_event_from_sources(
    db: Session,
    *,
    user_id: int,
    sources: frozenset[str],
) -> UserSyncEvent | None:
    if not sources:
        return None

    candidates = [
        event
        for event in list_user_sync_events(db, user_id=user_id)
        if is_sync_source_included(event.source, sources)
    ]
    if not candidates:
        return None

    candidates.sort(
        key=lambda event: (
            normalize_event_time(event.event_time),
            get_sync_source_priority(event.source),
            event.id,
        ),
        reverse=True,
    )
    return candidates[0]


def get_latest_check_event(
    db: Session,
    *,
    rfid: str,
    action: str,
    ignored_sources: frozenset[str] = frozenset(),
) -> CheckEvent | None:
    events = db.execute(
        select(CheckEvent)
        .where(
            CheckEvent.rfid == rfid,
            CheckEvent.action == action,
            CheckEvent.status.in_(SYNC_EVENT_FALLBACK_STATUSES),
        )
        .order_by(desc(CheckEvent.event_time), desc(CheckEvent.id))
    ).scalars().all()
    for event in events:
        if not is_sync_source_included(event.source, ignored_sources):
            return event
    return None


def get_latest_check_activity_event(
    db: Session,
    *,
    rfid: str,
    ignored_sources: frozenset[str] = frozenset(),
) -> CheckEvent | None:
    events = db.execute(
        select(CheckEvent)
        .where(
            CheckEvent.rfid == rfid,
            CheckEvent.action.in_(("checkin", "checkout")),
            CheckEvent.status.in_(SYNC_EVENT_FALLBACK_STATUSES),
        )
        .order_by(desc(CheckEvent.event_time), desc(CheckEvent.id))
    ).scalars().all()
    for event in events:
        if not is_sync_source_included(event.source, ignored_sources):
            return event
    return None


def is_current_user_state_backed_by_sources(
    db: Session,
    *,
    user: User,
    sources: frozenset[str],
) -> bool:
    if user.time is None or user.checkin is None:
        return False

    latest_source_event = get_latest_user_sync_event_from_sources(db, user_id=user.id, sources=sources)
    if latest_source_event is None:
        return False

    return (
        normalize_event_time(latest_source_event.event_time) == normalize_event_time(user.time)
        and latest_source_event.action == ("checkin" if user.checkin else "checkout")
        and resolve_activity_local(local=latest_source_event.local, source=latest_source_event.source) == user.local
    )


def resolve_latest_user_activity(
    db: Session,
    *,
    user: User,
    ignored_sync_sources: frozenset[str] = frozenset(),
    ignored_check_event_sources: frozenset[str] = frozenset(),
    include_current_state: bool = True,
) -> ResolvedUserActivity | None:
    candidates: list[tuple[datetime, int, ResolvedUserActivity]] = []

    latest_sync = get_latest_user_sync_event(db, user_id=user.id, ignored_sources=ignored_sync_sources)
    if latest_sync is not None:
        candidates.append(
            (
                latest_sync.event_time,
                3,
                ResolvedUserActivity(
                    action=latest_sync.action,
                    event_time=latest_sync.event_time,
                    local=resolve_activity_local(local=latest_sync.local, source=latest_sync.source),
                    ontime=latest_sync.ontime,
                    source=latest_sync.source,
                ),
            )
        )

    if include_current_state and user.time is not None and user.checkin is not None:
        candidates.append(
            (
                user.time,
                1,
                ResolvedUserActivity(
                    action="checkin" if user.checkin else "checkout",
                    event_time=user.time,
                    local=user.local,
                    ontime=True,
                    source="state",
                ),
            )
        )

    if user.rfid:
        latest_check_event = get_latest_check_activity_event(
            db,
            rfid=user.rfid,
            ignored_sources=ignored_check_event_sources,
        )
        if latest_check_event is not None:
            candidates.append(
                (
                    latest_check_event.event_time,
                    1,
                    ResolvedUserActivity(
                        action=latest_check_event.action,
                        event_time=latest_check_event.event_time,
                        local=resolve_activity_local(local=latest_check_event.local, source=latest_check_event.source),
                        ontime=(latest_check_event.ontime if latest_check_event.ontime is not None else True),
                        source=latest_check_event.source,
                    ),
                )
            )

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][2]


def resolve_latest_internal_user_activity(db: Session, *, user: User) -> ResolvedUserActivity | None:
    return resolve_latest_user_activity(
        db,
        user=user,
        ignored_sync_sources=INTERNAL_DECISION_IGNORED_SYNC_SOURCES,
        ignored_check_event_sources=INTERNAL_DECISION_IGNORED_CHECK_EVENT_SOURCES,
        include_current_state=not is_current_user_state_backed_by_sources(
            db,
            user=user,
            sources=SECONDARY_SYNC_SOURCES,
        ),
    )


def ensure_current_user_state_event(db: Session, *, user: User, skip_if_provider_backed: bool = False) -> None:
    if user.time is None or user.checkin is None:
        return

    if skip_if_provider_backed and is_current_user_state_backed_by_sources(
        db,
        user=user,
        sources=SECONDARY_SYNC_SOURCES,
    ):
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
    latest_activity = resolve_latest_user_activity(db, user=user)
    fallback_checkin = get_latest_check_event(db, rfid=user.rfid, action="checkin") if user.rfid else None
    fallback_checkout = get_latest_check_event(db, rfid=user.rfid, action="checkout") if user.rfid else None
    current_action = latest_activity.action if latest_activity is not None else None
    current_event_time = latest_activity.event_time if latest_activity is not None else user.time
    current_local = latest_activity.local if latest_activity is not None and latest_activity.local is not None else user.local

    return MobileSyncStateResponse(
        found=True,
        chave=user.chave,
        nome=user.nome,
        projeto=user.projeto,
        current_action=current_action,
        current_event_time=current_event_time,
        current_local=current_local,
        last_checkin_at=(
            latest_checkin.event_time
            if latest_checkin is not None
            else (
                fallback_checkin.event_time
                if fallback_checkin is not None
                else (current_event_time if current_action == "checkin" else None)
            )
        ),
        last_checkout_at=(
            latest_checkout.event_time
            if latest_checkout is not None
            else (
                fallback_checkout.event_time
                if fallback_checkout is not None
                else (current_event_time if current_action == "checkout" else None)
            )
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
        has_current_day_checkin=(
            state.last_checkin_at is not None and is_same_singapore_day(state.last_checkin_at, now_sgt())
        ),
        last_checkin_at=state.last_checkin_at,
        last_checkout_at=state.last_checkout_at,
    )
