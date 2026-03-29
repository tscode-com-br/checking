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
from ..services.time_utils import now_sgt
from ..services.user_activity import mark_user_active

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

    user = db.get(User, payload.rfid)

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
    user.local = payload.local

    if action == "checkin" and user.checkin is True:
        user.time = activity_time
        mark_user_active(user, activity_time=user.time)
        log_event(
            db,
            idempotency_key=f"{payload.request_id}:local-updated",
            source="device",
            action=action,
            status="updated",
            message="Active check-in location updated without submitting Forms",
            rfid=user.rfid,
            project=user.projeto,
            device_id=payload.device_id,
            local=payload.local,
            request_path="/api/scan",
            http_status=200,
            details="forms_skipped=true; reason=already_checked_in",
        )
        db.commit()
        notify_admin_data_changed("checkin")
        return ScanResponse(
            outcome="local_updated",
            led="green_blink_3x_1s",
            message="Local updated for active check-in",
        )

    if action == "checkout" and user.checkin is not True:
        log_event(
            db,
            idempotency_key=f"{payload.request_id}:blocked",
            source="device",
            action=action,
            status="blocked",
            message="Checkout blocked because user has no active check-in",
            rfid=user.rfid,
            project=user.projeto,
            device_id=payload.device_id,
            local=payload.local,
            request_path="/api/scan",
            http_status=409,
        )
        db.commit()
        notify_admin_data_changed("checkout")
        return ScanResponse(
            outcome="failed",
            led="red_2s",
            message="Check-in not found for checkout",
        )

    user.checkin = action == "checkin"
    user.time = activity_time
    mark_user_active(user, activity_time=activity_time)

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
        details="forms_deferred=true",
    )
    db.commit()
    notify_admin_data_changed(action)
    return ScanResponse(
        outcome="submitted",
        led="green_1s",
        message="Operation accepted and queued for Forms submission",
    )
