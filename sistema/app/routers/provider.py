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
from ..services.event_logger import log_event
from ..services.project_catalog import ensure_known_project
from ..services.time_utils import now_sgt
from ..services.user_profiles import merge_provider_date_and_time, normalize_person_name
from ..services.user_sync import (
    apply_user_state,
    create_user_sync_event,
    ensure_current_user_state_event,
    find_user_by_chave,
    normalize_event_time,
)

router = APIRouter(prefix="/api/provider", tags=["provider"])
PROVIDER_REQUEST_PATH = "/api/provider/updaterecords"

_ACTION_BY_ACTIVITY = {
    "check-in": "checkin",
    "check-out": "checkout",
}


def require_provider_shared_key(
    x_provider_shared_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> None:
    if x_provider_shared_key == settings.provider_shared_key:
        return

    log_event(
        db,
        source="provider",
        action="auth",
        status="failed",
        message="Provider API request rejected due to invalid shared key",
        request_path=PROVIDER_REQUEST_PATH,
        http_status=401,
        commit=True,
    )
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
    event_time = merge_provider_date_and_time(payload.data, payload.hora)
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
        log_event(
            db,
            source="provider",
            action=action,
            status="duplicate",
            message="Provider event already processed",
            rfid=user.rfid,
            project=user.projeto,
            request_path=PROVIDER_REQUEST_PATH,
            http_status=200,
            ontime=ontime,
            details=(
                f"chave={user.chave}; atividade={payload.atividade}; informe={payload.informe}; "
                f"event_time={event_time.isoformat()}; created_user={created_user}; updated_project={updated_project}; "
                "forms_skipped=true; reason=source_is_forms_database"
            ),
        )
        db.commit()
        notify_admin_data_changed("event")
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
    current_user_time = normalize_event_time(user.time) if user.time is not None else None
    updated_current_state = current_user_time is None or event_time >= current_user_time
    if updated_current_state:
        apply_user_state(
            user,
            action=action,
            event_time=event_time,
            projeto=payload.projeto,
            local=None,
        )

    create_user_sync_event(
        db,
        user=user,
        source="provider",
        action=action,
        event_time=event_time,
        projeto=user.projeto,
        local=None,
        ontime=ontime,
        source_request_id=provider_request_id,
        device_id="provider",
    )
    log_event(
        db,
        idempotency_key=f"provider:{provider_request_id}",
        source="provider",
        action=action,
        status="created" if created_user else ("updated" if updated_project or updated_current_state else "synced"),
        message="Provider event processed successfully",
        rfid=user.rfid,
        project=user.projeto,
        device_id="provider",
        request_path=PROVIDER_REQUEST_PATH,
        http_status=200,
        ontime=ontime,
        submitted_at=now_sgt(),
        details=(
            f"chave={user.chave}; atividade={payload.atividade}; informe={payload.informe}; "
            f"event_time={event_time.isoformat()}; created_user={created_user}; "
            f"updated_project={updated_project}; updated_current_state={updated_current_state}; "
            "forms_skipped=true; reason=source_is_forms_database"
        ),
    )
    db.commit()
    notify_admin_data_changed("event")
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
