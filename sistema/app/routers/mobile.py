from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import get_db
from ..models import ManagedLocation, UserSyncEvent
from ..schemas import (
    MobileLocationRow,
    MobileLocationsResponse,
    MobileFormsSubmitRequest,
    MobileSubmitRequest,
    MobileSubmitResponse,
    MobileSyncRequest,
    MobileSyncResponse,
    MobileSyncStateResponse,
)
from ..services.admin_updates import notify_admin_data_changed
from ..services.event_logger import log_event
from ..services.forms_queue import enqueue_forms_submission
from ..services.managed_locations import extract_location_coordinates
from ..services.location_settings import (
    get_location_accuracy_threshold_meters,
)
from ..services.user_sync import (
    apply_user_state,
    build_mobile_sync_state,
    create_user_sync_event,
    ensure_mobile_user,
    ensure_current_user_state_event,
    normalize_event_time,
    normalize_user_key,
    resolve_latest_user_activity,
    should_enqueue_forms_for_action,
)
from ..services.time_utils import now_sgt

router = APIRouter(prefix="/api/mobile", tags=["mobile"])
DEFAULT_MOBILE_LOCAL = "Aplicativo"


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


@router.get("/locations", response_model=MobileLocationsResponse, dependencies=[Depends(require_mobile_shared_key)])
def get_mobile_locations(db: Session = Depends(get_db)) -> MobileLocationsResponse:
    rows = db.execute(select(ManagedLocation).order_by(ManagedLocation.local, ManagedLocation.id)).scalars().all()
    return MobileLocationsResponse(
        items=[
            MobileLocationRow(
                id=row.id,
                local=row.local,
                latitude=coordinates[0]["latitude"],
                longitude=coordinates[0]["longitude"],
                coordinates=coordinates,
                tolerance_meters=row.tolerance_meters,
                updated_at=row.updated_at,
            )
            for row in rows
            for coordinates in [extract_location_coordinates(row)]
        ],
        synced_at=now_sgt(),
        location_accuracy_threshold_meters=get_location_accuracy_threshold_meters(db),
    )


@router.post("/events/submit", response_model=MobileSubmitResponse, dependencies=[Depends(require_mobile_shared_key)])
def submit_mobile_event(payload: MobileSubmitRequest, db: Session = Depends(get_db)) -> MobileSubmitResponse:
    resolved_local = payload.local or DEFAULT_MOBILE_LOCAL
    existing = db.execute(
        select(UserSyncEvent).where(
            UserSyncEvent.source == "android",
            UserSyncEvent.source_request_id == payload.client_event_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        state = build_mobile_sync_state(db, chave=payload.chave)
        return MobileSubmitResponse(
            ok=True,
            duplicate=True,
            queued_forms=False,
            message="Mobile event already submitted",
            state=state,
        )

    user, created = ensure_mobile_user(db, chave=payload.chave, projeto=payload.projeto)
    event_time = normalize_event_time(payload.event_time)
    ensure_current_user_state_event(db, user=user)
    latest_activity = resolve_latest_user_activity(db, user=user)
    should_queue_forms = should_enqueue_forms_for_action(
        latest_activity=latest_activity,
        action=payload.action,
        event_time=event_time,
    )
    apply_user_state(
        user,
        action=payload.action,
        event_time=event_time,
        projeto=payload.projeto,
        local=resolved_local,
    )

    if not should_queue_forms:
        create_user_sync_event(
            db,
            user=user,
            source="android",
            action=payload.action,
            event_time=event_time,
            projeto=payload.projeto,
            local=resolved_local,
            source_request_id=payload.client_event_id,
            device_id="android-app",
        )
        log_event(
            db,
            idempotency_key=f"mobile-submit:{payload.client_event_id}",
            source="mobile",
            action=payload.action,
            status="updated",
            message="Mobile event accepted without new Forms submission",
            rfid=user.rfid,
            project=user.projeto,
            local=resolved_local,
            request_path="/api/mobile/events/submit",
            http_status=200,
            details=(
                f"chave={user.chave}; event_time={event_time.isoformat()}; forms_skipped=true; "
                "reason=repeated_same_action_same_day"
            ),
        )
        db.commit()
        notify_admin_data_changed(payload.action)
        state = build_mobile_sync_state(db, chave=user.chave)
        return MobileSubmitResponse(
            ok=True,
            duplicate=False,
            queued_forms=False,
            message="Mobile event accepted without new Forms submission",
            state=state,
        )

    try:
        enqueue_forms_submission(
            db,
            request_id=payload.client_event_id,
            rfid=user.rfid,
            action=payload.action,
            chave=user.chave,
            projeto=user.projeto,
            device_id="android-app",
            local=resolved_local,
        )
    except IntegrityError:
        db.rollback()
        state = build_mobile_sync_state(db, chave=payload.chave)
        return MobileSubmitResponse(
            ok=True,
            duplicate=True,
            queued_forms=False,
            message="Mobile event already submitted",
            state=state,
        )

    create_user_sync_event(
        db,
        user=user,
        source="android",
        action=payload.action,
        event_time=event_time,
        projeto=payload.projeto,
        local=resolved_local,
        source_request_id=payload.client_event_id,
        device_id="android-app",
    )
    log_event(
        db,
        idempotency_key=f"mobile-submit:{payload.client_event_id}",
        source="mobile",
        action=payload.action,
        status="queued",
        message="Mobile event accepted and queued for Forms submission",
        rfid=user.rfid,
        project=user.projeto,
        local=resolved_local,
        request_path="/api/mobile/events/submit",
        http_status=202,
        details=f"chave={user.chave}; event_time={event_time.isoformat()}; forms_deferred=true",
    )
    db.commit()
    notify_admin_data_changed(payload.action)
    state = build_mobile_sync_state(db, chave=user.chave)
    return MobileSubmitResponse(
        ok=True,
        duplicate=False,
        queued_forms=True,
        message="Mobile event accepted and queued for Forms submission",
        state=state,
    )


@router.post("/events/forms-submit", response_model=MobileSubmitResponse, dependencies=[Depends(require_mobile_shared_key)])
def submit_mobile_forms_event(payload: MobileFormsSubmitRequest, db: Session = Depends(get_db)) -> MobileSubmitResponse:
    ontime = payload.informe == "normal"
    resolved_local = payload.local or DEFAULT_MOBILE_LOCAL

    existing = db.execute(
        select(UserSyncEvent).where(
            UserSyncEvent.source == "android_forms",
            UserSyncEvent.source_request_id == payload.client_event_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        state = build_mobile_sync_state(db, chave=payload.chave)
        return MobileSubmitResponse(
            ok=True,
            duplicate=True,
            queued_forms=False,
            message="Mobile Forms event already submitted",
            state=state,
        )

    user, created = ensure_mobile_user(db, chave=payload.chave, projeto=payload.projeto)
    event_time = normalize_event_time(payload.event_time)
    ensure_current_user_state_event(db, user=user)
    latest_activity = resolve_latest_user_activity(db, user=user)
    should_queue_forms = should_enqueue_forms_for_action(
        latest_activity=latest_activity,
        action=payload.action,
        event_time=event_time,
    )
    apply_user_state(
        user,
        action=payload.action,
        event_time=event_time,
        projeto=payload.projeto,
        local=resolved_local,
    )

    if not should_queue_forms:
        create_user_sync_event(
            db,
            user=user,
            source="android_forms",
            action=payload.action,
            event_time=event_time,
            projeto=user.projeto,
            local=resolved_local,
            ontime=ontime,
            source_request_id=payload.client_event_id,
            device_id="android-app",
        )
        log_event(
            db,
            idempotency_key=f"mobile-forms-submit:{payload.client_event_id}",
            source="mobile",
            action=payload.action,
            status="updated",
            message="Mobile Forms event accepted without new Forms submission",
            rfid=user.rfid,
            project=user.projeto,
            local=resolved_local,
            request_path="/api/mobile/events/forms-submit",
            http_status=200,
            ontime=ontime,
            details=(
                f"chave={user.chave}; event_time={event_time.isoformat()}; "
                f"forms_skipped=true; informe={payload.informe}; ontime={ontime}; "
                "reason=repeated_same_action_same_day"
            ),
        )
        db.commit()
        notify_admin_data_changed(payload.action)
        state = build_mobile_sync_state(db, chave=user.chave)
        return MobileSubmitResponse(
            ok=True,
            duplicate=False,
            queued_forms=False,
            message="Mobile Forms event accepted without new Forms submission",
            state=state,
        )

    try:
        enqueue_forms_submission(
            db,
            request_id=payload.client_event_id,
            rfid=user.rfid,
            action=payload.action,
            chave=user.chave,
            projeto=user.projeto,
            device_id="android-app",
            local=resolved_local,
            ontime=ontime,
        )
    except IntegrityError:
        db.rollback()
        state = build_mobile_sync_state(db, chave=payload.chave)
        return MobileSubmitResponse(
            ok=True,
            duplicate=True,
            queued_forms=False,
            message="Mobile Forms event already submitted",
            state=state,
        )

    create_user_sync_event(
        db,
        user=user,
        source="android_forms",
        action=payload.action,
        event_time=event_time,
        projeto=user.projeto,
        local=resolved_local,
        ontime=ontime,
        source_request_id=payload.client_event_id,
        device_id="android-app",
    )
    log_event(
        db,
        idempotency_key=f"mobile-forms-submit:{payload.client_event_id}",
        source="mobile",
        action=payload.action,
        status="queued",
        message="Mobile Forms event accepted and queued for Forms submission",
        rfid=user.rfid,
        project=user.projeto,
        local=resolved_local,
        request_path="/api/mobile/events/forms-submit",
        http_status=202,
        ontime=ontime,
        details=(
            f"chave={user.chave}; event_time={event_time.isoformat()}; "
            f"forms_deferred=true; informe={payload.informe}; ontime={ontime}"
        ),
    )
    db.commit()
    notify_admin_data_changed(payload.action)
    state = build_mobile_sync_state(db, chave=user.chave)
    return MobileSubmitResponse(
        ok=True,
        duplicate=False,
        queued_forms=True,
        message="Mobile Forms event accepted and queued for Forms submission",
        state=state,
    )


@router.post("/events/sync", response_model=MobileSyncResponse, dependencies=[Depends(require_mobile_shared_key)])
def sync_mobile_event(payload: MobileSyncRequest, db: Session = Depends(get_db)) -> MobileSyncResponse:
    resolved_local = payload.local or DEFAULT_MOBILE_LOCAL
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
        local=resolved_local,
    )
    create_user_sync_event(
        db,
        user=user,
        source="android",
        action=payload.action,
        event_time=event_time,
        projeto=payload.projeto,
        local=resolved_local,
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
        local=resolved_local,
        request_path="/api/mobile/events/sync",
        http_status=200,
        details=f"chave={user.chave}; event_time={event_time.isoformat()}",
    )
    db.commit()
    notify_admin_data_changed(payload.action)
    state = build_mobile_sync_state(db, chave=user.chave)
    return MobileSyncResponse(
        ok=True,
        duplicate=False,
        message="Mobile event synchronized successfully",
        state=state,
    )