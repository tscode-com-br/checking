from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import get_db
from ..models import CheckEvent, DeviceHeartbeat, PendingRegistration, User
from ..schemas import HeartbeatRequest, ScanRequest, ScanResponse
from ..services.forms_worker import FormsWorker
from ..services.time_utils import now_sgt

router = APIRouter(prefix="/api", tags=["device"])


@router.post("/device/heartbeat")
def heartbeat(payload: HeartbeatRequest, db: Session = Depends(get_db)) -> dict:
    if payload.shared_key != settings.device_shared_key:
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
        return ScanResponse(
            outcome="invalid_key",
            led="red",
            message="Invalid device shared key",
        )

    existing = db.execute(select(CheckEvent).where(CheckEvent.idempotency_key == payload.request_id)).scalar_one_or_none()
    if existing:
        return ScanResponse(
            outcome="duplicate",
            led="white",
            message="Duplicate request ignored",
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

        db.add(
            CheckEvent(
                idempotency_key=payload.request_id,
                rfid=None,
                action=payload.action,
                status="pending_registration",
                message=f"RFID not registered yet for {payload.action}",
                project=None,
                event_time=now_sgt(),
                submitted_at=None,
                retry_count=0,
            )
        )
        db.commit()
        return ScanResponse(
            outcome="pending_registration",
            led="orange_4s",
            message="RFID added to pending registration",
        )

    action = payload.action
    user.local = payload.local
    worker = FormsWorker(assets_dir=Path("assets"))
    submission = worker.submit_with_retries(action=action, chave=user.chave, projeto=user.projeto)

    was_success = bool(submission["success"])
    if was_success:
        user.checkin = action == "checkin"
        user.time = now_sgt()

    db.add(
        CheckEvent(
            idempotency_key=payload.request_id,
            rfid=user.rfid,
            action=action,
            status="submitted" if was_success else "failed",
            message=submission["message"],
            project=user.projeto,
            event_time=now_sgt(),
            submitted_at=now_sgt() if was_success else None,
            retry_count=submission.get("retry_count", 0),
        )
    )
    db.commit()

    if was_success:
        return ScanResponse(
            outcome="submitted",
            led="green_2s",
            message="Operation submitted to Forms",
        )

    return ScanResponse(
        outcome="failed",
        led="red",
        message="Operation failed after retries",
    )
