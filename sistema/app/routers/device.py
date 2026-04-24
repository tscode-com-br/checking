from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import get_db
from ..models import CheckEvent, DeviceHeartbeat, PendingRegistration, User
from ..schemas import HeartbeatRequest, ScanRequest, ScanResponse
from ..services.admin_updates import notify_admin_data_changed
from ..services.event_logger import log_event
from ..services.forms_queue import enqueue_forms_submission
from ..services.time_utils import now_sgt, resolve_project_timezone_name
from ..services.user_sync import (
    apply_user_state,
    create_user_sync_event,
    ensure_current_user_state_event,
    find_user_by_rfid,
    resolve_latest_internal_user_activity,
    should_enqueue_forms_for_action,
)

router = APIRouter(prefix="/api", tags=["device"])


@router.post("/device/heartbeat")
def heartbeat(payload: HeartbeatRequest, db: Session = Depends(get_db)) -> dict:
    if payload.shared_key != settings.device_shared_key:
        log_event(
            db,
            source="device",
            action="heartbeat",
            status="failed",
            message="Heartbeat rejected due to invalid shared key",
            device_id=payload.device_id,
            request_path="/api/device/heartbeat",
            http_status=401,
            commit=True,
        )
        return {"ok": False, "led": "red", "message": "invalid shared key"}

    heartbeat_row = DeviceHeartbeat(
        device_id=payload.device_id,
        is_online=True,
        last_seen_at=now_sgt(),
    )
    db.add(heartbeat_row)
    db.commit()
    return {"ok": True, "led": "white"}


@router.post("/scan", response_model=ScanResponse)
def scan(payload: ScanRequest, db: Session = Depends(get_db)) -> ScanResponse:
    if payload.shared_key != settings.device_shared_key:
        log_event(
            db,
            idempotency_key=f"{payload.request_id}:invalid",
            source="device",
            action=payload.action,
            status="failed",
            message="Scan rejected due to invalid shared key",
            rfid=payload.rfid,
            device_id=payload.device_id,
            local=payload.local,
            request_path="/api/scan",
            http_status=401,
            commit=True,
        )
        return ScanResponse(
            outcome="invalid_key",
            led="red",
            message="Invalid device shared key",
        )

    existing = db.execute(select(CheckEvent).where(CheckEvent.idempotency_key == payload.request_id)).scalar_one_or_none()
    if existing:
        log_event(
            db,
            idempotency_key=f"{payload.request_id}:duplicate",
            source="device",
            action=payload.action,
            status="duplicate",
            message="Duplicate scan request ignored",
            rfid=payload.rfid,
            device_id=payload.device_id,
            local=payload.local,
            request_path="/api/scan",
            http_status=200,
            commit=True,
        )
        return ScanResponse(
            outcome="duplicate",
            led="white",
            message="Duplicate request ignored",
        )

    log_event(
        db,
        idempotency_key=payload.request_id,
        source="device",
        action=payload.action,
        status="received",
        message="Scan request received",
        rfid=payload.rfid,
        device_id=payload.device_id,
        local=payload.local,
        request_path="/api/scan",
        http_status=200,
        details=f"request_id={payload.request_id}",
        commit=True,
    )

    user = find_user_by_rfid(db, payload.rfid)

    if not user:
        pending = db.execute(
            select(PendingRegistration).where(PendingRegistration.rfid == payload.rfid)
        ).scalar_one_or_none()
        if pending:
            pending.attempts += 1
            pending.last_seen_at = now_sgt()
        else:
            db.add(
                PendingRegistration(
                    rfid=payload.rfid,
                    first_seen_at=now_sgt(),
                    last_seen_at=now_sgt(),
                    attempts=1,
                )
            )

        log_event(
            db,
            idempotency_key=f"{payload.request_id}:pending",
            source="device",
            action=payload.action,
            status="pending",
            message="RFID added to pending registration",
            device_id=payload.device_id,
            local=payload.local,
            request_path="/api/scan",
            http_status=200,
            details=f"rfid={payload.rfid}",
        )
        db.commit()
        notify_admin_data_changed("pending")
        return ScanResponse(
            outcome="pending_registration",
            led="orange_4s",
            message="RFID added to pending registration",
        )

    action = payload.action
    activity_time = now_sgt()
    ensure_current_user_state_event(db, user=user, skip_if_provider_backed=True)
    latest_activity = resolve_latest_internal_user_activity(db, user=user)
    project_timezone_name = resolve_project_timezone_name(db, user.projeto)
    should_queue_forms = should_enqueue_forms_for_action(
        latest_activity=latest_activity,
        action=action,
        event_time=activity_time,
        timezone_name=project_timezone_name,
    )

    if action == "checkout" and latest_activity is None:
        log_event(
            db,
            idempotency_key=f"{payload.request_id}:blocked",
            source="device",
            action=action,
            status="blocked",
            message="Checkout blocked because user has no prior activity",
            rfid=user.rfid,
            project=user.projeto,
            device_id=payload.device_id,
            local=payload.local,
            request_path="/api/scan",
            http_status=409,
            details=f"chave={user.chave}; forms_skipped=true; reason=no_prior_activity",
        )
        db.commit()
        notify_admin_data_changed("checkout")
        return ScanResponse(
            outcome="failed",
            led="red_2s",
            message="Check-in not found for checkout",
        )

    if not should_queue_forms:
        apply_user_state(
            user,
            action=action,
            event_time=activity_time,
            local=payload.local,
        )
        log_event(
            db,
            idempotency_key=f"{payload.request_id}:local-updated",
            source="device",
            action=action,
            status="updated",
            message="Repeated same-day action accepted without submitting Forms",
            rfid=user.rfid,
            project=user.projeto,
            device_id=payload.device_id,
            local=payload.local,
            request_path="/api/scan",
            http_status=200,
            details=(
                f"chave={user.chave}; forms_skipped=true; reason=repeated_same_action_same_day; "
                f"latest_action={latest_activity.action if latest_activity else 'unknown'}"
            ),
        )
        create_user_sync_event(
            db,
            user=user,
            source="rfid",
            action=action,
            event_time=activity_time,
            projeto=user.projeto,
            local=user.local,
            source_request_id=payload.request_id,
            device_id=payload.device_id,
        )
        db.commit()
        notify_admin_data_changed(action)
        return ScanResponse(
            outcome="local_updated",
            led="green_blink_3x_1s",
            message="Operation accepted without new Forms submission",
        )

    apply_user_state(
        user,
        action=action,
        event_time=activity_time,
        local=payload.local,
    )

    try:
        enqueue_forms_submission(
            db,
            request_id=payload.request_id,
            rfid=user.rfid,
            action=action,
            chave=user.chave,
            projeto=user.projeto,
            device_id=payload.device_id,
            local=payload.local,
        )
    except IntegrityError:
        log_event(
            db,
            idempotency_key=f"{payload.request_id}:duplicate",
            source="device",
            action=action,
            status="duplicate",
            message="Duplicate scan request ignored while queueing Forms submission",
            rfid=user.rfid,
            project=user.projeto,
            device_id=payload.device_id,
            local=payload.local,
            request_path="/api/scan",
            http_status=200,
            details=f"chave={user.chave}",
            commit=True,
        )
        return ScanResponse(
            outcome="duplicate",
            led="white",
            message="Duplicate request ignored",
        )

    log_event(
        db,
        idempotency_key=f"{payload.request_id}:queued",
        source="device",
        action=action,
        status="queued",
        message="Scan accepted and Forms submission queued",
        rfid=user.rfid,
        project=user.projeto,
        device_id=payload.device_id,
        local=payload.local,
        request_path="/api/scan",
        http_status=202,
        details=f"chave={user.chave}; forms_deferred=true",
    )
    create_user_sync_event(
        db,
        user=user,
        source="rfid",
        action=action,
        event_time=activity_time,
        projeto=user.projeto,
        local=user.local,
        source_request_id=payload.request_id,
        device_id=payload.device_id,
    )
    db.commit()
    notify_admin_data_changed(action)
    return ScanResponse(
        outcome="submitted",
        led="green_1s",
        message="Operation accepted and queued for Forms submission",
    )
