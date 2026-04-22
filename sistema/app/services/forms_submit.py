from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import User, UserSyncEvent
from ..schemas import MobileSubmitResponse
from .admin_updates import notify_admin_data_changed
from .event_logger import log_event
from .forms_queue import enqueue_forms_submission
from .user_sync import (
    apply_user_state,
    build_mobile_sync_state,
    create_user_sync_event,
    ensure_current_user_state_event,
    normalize_event_time,
    resolve_latest_internal_user_activity,
    should_enqueue_forms_for_action,
)


EnsureUserCallback = Callable[..., tuple[User, bool]]


@dataclass(frozen=True)
class FormsSubmitChannel:
    event_label: str
    user_sync_source: str
    log_source: str
    request_path: str
    device_id: str | None
    default_local: str


def submit_forms_event(
    db: Session,
    *,
    chave: str,
    projeto: str,
    action: str,
    informe: str,
    local: str | None,
    event_time: datetime,
    client_event_id: str,
    ensure_user: EnsureUserCallback,
    channel: FormsSubmitChannel,
) -> MobileSubmitResponse:
    ontime = informe == "normal"
    resolved_local = local or channel.default_local

    existing = db.execute(
        select(UserSyncEvent).where(
            UserSyncEvent.source == channel.user_sync_source,
            UserSyncEvent.source_request_id == client_event_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        state = build_mobile_sync_state(db, chave=chave)
        return MobileSubmitResponse(
            ok=True,
            duplicate=True,
            queued_forms=False,
            message=f"{channel.event_label} already submitted",
            state=state,
        )

    user, _created = ensure_user(db, chave=chave, projeto=projeto)
    normalized_event_time = normalize_event_time(event_time)
    ensure_current_user_state_event(db, user=user, skip_if_provider_backed=True)
    latest_activity = resolve_latest_internal_user_activity(db, user=user)
    should_queue_forms = should_enqueue_forms_for_action(
        latest_activity=latest_activity,
        action=action,
        event_time=normalized_event_time,
    )
    apply_user_state(
        user,
        action=action,
        event_time=normalized_event_time,
        projeto=projeto,
        local=resolved_local,
    )

    if not should_queue_forms:
        create_user_sync_event(
            db,
            user=user,
            source=channel.user_sync_source,
            action=action,
            event_time=normalized_event_time,
            projeto=user.projeto,
            local=resolved_local,
            ontime=ontime,
            source_request_id=client_event_id,
            device_id=channel.device_id,
        )
        message = f"{channel.event_label} accepted without new Forms submission"
        log_event(
            db,
            idempotency_key=f"{channel.user_sync_source}:{client_event_id}",
            source=channel.log_source,
            action=action,
            status="updated",
            message=message,
            rfid=user.rfid,
            project=user.projeto,
            local=resolved_local,
            request_path=channel.request_path,
            http_status=200,
            ontime=ontime,
            details=(
                f"chave={user.chave}; event_time={normalized_event_time.isoformat()}; "
                f"forms_skipped=true; informe={informe}; ontime={ontime}; "
                "reason=repeated_same_action_same_day"
            ),
        )
        db.commit()
        notify_admin_data_changed(action)
        state = build_mobile_sync_state(db, chave=user.chave)
        return MobileSubmitResponse(
            ok=True,
            duplicate=False,
            queued_forms=False,
            message=message,
            state=state,
        )

    try:
        enqueue_forms_submission(
            db,
            request_id=client_event_id,
            rfid=user.rfid,
            action=action,
            chave=user.chave,
            projeto=user.projeto,
            device_id=channel.device_id,
            local=resolved_local,
            ontime=ontime,
        )
    except IntegrityError:
        db.rollback()
        state = build_mobile_sync_state(db, chave=chave)
        return MobileSubmitResponse(
            ok=True,
            duplicate=True,
            queued_forms=False,
            message=f"{channel.event_label} already submitted",
            state=state,
        )

    create_user_sync_event(
        db,
        user=user,
        source=channel.user_sync_source,
        action=action,
        event_time=normalized_event_time,
        projeto=user.projeto,
        local=resolved_local,
        ontime=ontime,
        source_request_id=client_event_id,
        device_id=channel.device_id,
    )
    message = f"{channel.event_label} accepted and queued for Forms submission"
    log_event(
        db,
        idempotency_key=f"{channel.user_sync_source}:{client_event_id}",
        source=channel.log_source,
        action=action,
        status="queued",
        message=message,
        rfid=user.rfid,
        project=user.projeto,
        local=resolved_local,
        request_path=channel.request_path,
        http_status=202,
        ontime=ontime,
        details=(
            f"chave={user.chave}; event_time={normalized_event_time.isoformat()}; "
            f"forms_deferred=true; informe={informe}; ontime={ontime}"
        ),
    )
    db.commit()
    notify_admin_data_changed(action)
    state = build_mobile_sync_state(db, chave=user.chave)
    return MobileSubmitResponse(
        ok=True,
        duplicate=False,
        queued_forms=True,
        message=message,
        state=state,
    )