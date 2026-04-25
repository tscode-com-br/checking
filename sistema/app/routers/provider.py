from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import get_db
from ..models import User, UserSyncEvent
from ..schemas import ProviderCheckSubmitRequest, ProviderCheckSubmitResponse
from ..services.admin_updates import notify_admin_data_changed
from ..services.project_catalog import ensure_known_project
from ..services.time_utils import resolve_project_timezone_name
from ..services.user_profiles import merge_provider_date_and_time, normalize_person_name
from ..services.user_sync import (
    apply_user_state,
    create_user_sync_event,
    ensure_current_user_state_event,
    find_user_by_chave,
    normalize_event_time,
    PROVIDER_ACTIVITY_LOCAL,
    resolve_latest_user_activity,
)

router = APIRouter(prefix="/api/provider", tags=["provider"])
PROVIDER_REQUEST_PATH = "/api/provider/updaterecords"

_ACTION_BY_ACTIVITY = {
    "check-in": "checkin",
    "check-out": "checkout",
}


def require_provider_shared_key(
    x_provider_shared_key: str | None = Header(default=None),
) -> None:
    if x_provider_shared_key == settings.provider_shared_key:
        return

    raise HTTPException(status_code=401, detail="Invalid provider shared key")


def _build_provider_request_id(*, chave: str, projeto: str, atividade: str, informe: str, event_time_iso: str) -> str:
    raw_value = f"{chave}|{projeto}|{atividade}|{informe}|{event_time_iso}"
    return hashlib.sha1(raw_value.encode("utf-8")).hexdigest()


@router.post("/updaterecords", response_model=ProviderCheckSubmitResponse, dependencies=[Depends(require_provider_shared_key)])
def submit_provider_checking(
    payload: ProviderCheckSubmitRequest,
    db: Session = Depends(get_db),
) -> ProviderCheckSubmitResponse:
    payload.projeto = ensure_known_project(db, payload.projeto)
    # This endpoint mirrors data that already originated from FORMS.
    # It must only update the local database and must never enqueue or submit
    # anything back to FORMS, otherwise production could enter a feedback loop.
    action = _ACTION_BY_ACTIVITY[payload.atividade]
    ontime = payload.informe == "normal"
    project_timezone_name = resolve_project_timezone_name(db, payload.projeto)
    event_time = merge_provider_date_and_time(
        payload.data,
        payload.hora,
        timezone_name=project_timezone_name,
    )
    provider_request_id = _build_provider_request_id(
        chave=payload.chave,
        projeto=payload.projeto,
        atividade=payload.atividade,
        informe=payload.informe,
        event_time_iso=event_time.isoformat(),
    )

    user = find_user_by_chave(db, payload.chave)
    created_user = False
    updated_project = False
    if user is None:
        user = User(
            rfid=None,
            chave=payload.chave,
            nome=normalize_person_name(payload.nome),
            projeto=payload.projeto,
            placa=None,
            end_rua=None,
            zip=None,
            cargo=None,
            email=None,
            local=None,
            checkin=None,
            time=None,
            last_active_at=event_time,
            inactivity_days=0,
        )
        db.add(user)
        db.flush()
        created_user = True
    elif user.projeto != payload.projeto:
        user.projeto = payload.projeto
        updated_project = True

    existing_event = db.execute(
        select(UserSyncEvent).where(
            UserSyncEvent.source == "provider",
            UserSyncEvent.source_request_id == provider_request_id,
        )
    ).scalar_one_or_none()
    if existing_event is not None:
        db.commit()
        if created_user or updated_project:
            notify_admin_data_changed("register")
        return ProviderCheckSubmitResponse(
            ok=True,
            duplicate=True,
            created_user=created_user,
            updated_project=updated_project,
            updated_current_state=False,
            message="Provider event already processed",
            chave=user.chave,
            projeto=user.projeto,
            atividade=payload.atividade,
            informe=payload.informe,
            time=event_time,
        )

    ensure_current_user_state_event(db, user=user)

    create_user_sync_event(
        db,
        user=user,
        source="provider",
        action=action,
        event_time=event_time,
        projeto=user.projeto,
        local=PROVIDER_ACTIVITY_LOCAL,
        ontime=ontime,
        source_request_id=provider_request_id,
        device_id="provider",
    )
    db.flush()

    preferred_activity = resolve_latest_user_activity(db, user=user)
    updated_current_state = False
    if preferred_activity is not None:
        preferred_event_time = normalize_event_time(
            preferred_activity.event_time,
            timezone_name=project_timezone_name,
        )
        current_user_time = (
            normalize_event_time(user.time, timezone_name=project_timezone_name)
            if user.time is not None
            else None
        )
        next_checkin = preferred_activity.action == "checkin"
        next_local = preferred_activity.local
        should_update_current_state = (
            current_user_time is None
            or user.checkin is None
            or current_user_time != preferred_event_time
            or bool(user.checkin) != next_checkin
            or user.local != next_local
        )
        if should_update_current_state:
            apply_user_state(
                user,
                action=preferred_activity.action,
                event_time=preferred_event_time,
                projeto=payload.projeto,
                local=next_local,
            )

        updated_current_state = (
            preferred_activity.source == "provider"
            and preferred_activity.action == action
            and preferred_event_time == event_time
        )

    db.commit()
    notify_admin_data_changed(action)
    if created_user or updated_project:
        notify_admin_data_changed("register")
    return ProviderCheckSubmitResponse(
        ok=True,
        duplicate=False,
        created_user=created_user,
        updated_project=updated_project,
        updated_current_state=updated_current_state,
        message="Provider event processed successfully",
        chave=user.chave,
        projeto=user.projeto,
        atividade=payload.atividade,
        informe=payload.informe,
        time=event_time,
    )
