from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import get_db
from ..models import CheckEvent, DeviceHeartbeat, PendingRegistration, User
from ..schemas import HeartbeatRequest, ScanRequest, ScanResponse
from ..services.event_logger import log_event
from ..services.forms_worker import FormsWorker
from ..services.time_utils import now_sgt

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
    log_event(
        db,
        source="device",
        action="heartbeat",
        status="success",
        message="Heartbeat accepted",
        device_id=payload.device_id,
        request_path="/api/device/heartbeat",
        http_status=200,
    )
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
        return ScanResponse(
            outcome="pending_registration",
            led="orange_4s",
            message="RFID added to pending registration",
        )

    action = payload.action
    user.local = payload.local

    if action == "checkin" and user.checkin:
        user.time = now_sgt()
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
        return ScanResponse(
            outcome="local_updated",
            led="green_blink_3x_1s",
            message="Local updated for active check-in",
        )

    if action == "checkout" and not user.checkin:
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
        return ScanResponse(
            outcome="failed",
            led="red_2s",
            message="Check-in not found for checkout",
        )

    worker = FormsWorker(assets_dir=Path("assets"))
    log_event(
        db,
        idempotency_key=f"{payload.request_id}:forms-attempt",
        source="forms",
        action=action,
        status="attempt",
        message="Starting Microsoft Forms submission",
        rfid=user.rfid,
        project=user.projeto,
        device_id=payload.device_id,
        local=payload.local,
        request_path="/api/scan",
        http_status=200,
    )
    submission = worker.submit_with_retries(action=action, chave=user.chave, projeto=user.projeto)

    for idx, event in enumerate(submission.get("audit_events", []), start=1):
        log_event(
            db,
            idempotency_key=f"{payload.request_id}:forms:{idx}",
            source=event.get("source", "forms"),
            action=event.get("action", action),
            status=event.get("status", "attempt"),
            message=event.get("message", "Forms event"),
            rfid=user.rfid,
            project=user.projeto,
            device_id=payload.device_id,
            local=payload.local,
            request_path="/api/scan",
            http_status=200 if submission.get("success") else 500,
            retry_count=submission.get("retry_count", 0),
            details=event.get("details"),
        )

    was_success = bool(submission["success"])
    if was_success:
        user.checkin = action == "checkin"
        user.time = now_sgt()

    log_event(
        db,
        idempotency_key=f"{payload.request_id}:result",
        source="device",
        action=action,
        status="success" if was_success else "failed",
        message=submission["message"],
        rfid=user.rfid,
        project=user.projeto,
        device_id=payload.device_id,
        local=payload.local,
        request_path="/api/scan",
        http_status=200 if was_success else 500,
        submitted_at=now_sgt() if was_success else None,
        retry_count=submission.get("retry_count", 0),
        details=f"error_code={submission.get('error_code', 'none')}; failed_step={submission.get('failed_step', '-')}",
    )
    db.commit()

    if was_success:
        return ScanResponse(
            outcome="submitted",
            led="green_1s",
            message="Operation submitted to Forms",
        )

    return ScanResponse(
        outcome="failed",
        led="red_blink_5x_1s",
        message=submission["message"],
    )
