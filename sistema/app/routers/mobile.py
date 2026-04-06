from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import get_db
from ..models import UserSyncEvent
from ..schemas import MobileSyncRequest, MobileSyncResponse, MobileSyncStateResponse
from ..services.event_logger import log_event
from ..services.user_sync import (
    apply_user_state,
    build_mobile_sync_state,
    create_user_sync_event,
    ensure_mobile_user,
    ensure_current_user_state_event,
    normalize_event_time,
    normalize_user_key,
)

router = APIRouter(prefix="/api/mobile", tags=["mobile"])


def require_mobile_shared_key(
    x_mobile_shared_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> None:
    if x_mobile_shared_key == settings.mobile_app_shared_key:
        return

    log_event(
        db,
        source="mobile",
        action="auth",
        status="failed",
        message="Mobile API request rejected due to invalid shared key",
        request_path="/api/mobile",
        http_status=401,
        commit=True,
    )
    raise HTTPException(status_code=401, detail="Invalid mobile shared key")


@router.get("/state", response_model=MobileSyncStateResponse, dependencies=[Depends(require_mobile_shared_key)])
def get_mobile_state(chave: str, db: Session = Depends(get_db)) -> MobileSyncStateResponse:
    return build_mobile_sync_state(db, chave=normalize_user_key(chave))


@router.post("/events/sync", response_model=MobileSyncResponse, dependencies=[Depends(require_mobile_shared_key)])
def sync_mobile_event(payload: MobileSyncRequest, db: Session = Depends(get_db)) -> MobileSyncResponse:
    existing = db.execute(
        select(UserSyncEvent).where(
            UserSyncEvent.source == "android",
            UserSyncEvent.source_request_id == payload.client_event_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        state = build_mobile_sync_state(db, chave=payload.chave)
        return MobileSyncResponse(ok=True, duplicate=True, message="Mobile event already synchronized", state=state)

    user, created = ensure_mobile_user(db, chave=payload.chave, projeto=payload.projeto)
    event_time = normalize_event_time(payload.event_time)
    ensure_current_user_state_event(db, user=user)
    apply_user_state(
        user,
        action=payload.action,
        event_time=event_time,
        projeto=payload.projeto,
    )
    create_user_sync_event(
        db,
        user=user,
        source="android",
        action=payload.action,
        event_time=event_time,
        projeto=payload.projeto,
        local=None,
        source_request_id=payload.client_event_id,
        device_id=None,
    )
    log_event(
        db,
        idempotency_key=f"mobile:{payload.client_event_id}",
        source="mobile",
        action=payload.action,
        status="created" if created else "synced",
        message="Mobile event synchronized",
        rfid=user.rfid,
        project=user.projeto,
        request_path="/api/mobile/events/sync",
        http_status=200,
        details=f"chave={user.chave}; event_time={event_time.isoformat()}",
    )
    db.commit()
    state = build_mobile_sync_state(db, chave=user.chave)
    return MobileSyncResponse(
        ok=True,
        duplicate=False,
        message="Mobile event synchronized successfully",
        state=state,
    )