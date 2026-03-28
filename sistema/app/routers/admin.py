from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import get_db
from ..models import CheckEvent, PendingRegistration, User
from ..schemas import AdminUserUpsert, EventRow, PendingRow, UserRow
from ..services.event_logger import log_event
from ..services.time_utils import now_sgt

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin_key(x_admin_key: str = Header(default="")) -> None:
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")


@router.get("/checkin", response_model=list[UserRow], dependencies=[Depends(require_admin_key)])
def list_checkin(db: Session = Depends(get_db)) -> list[UserRow]:
    rows = db.execute(select(User).where(User.checkin.is_(True)).order_by(desc(User.time))).scalars().all()
    return [
        UserRow(
            rfid=r.rfid,
            nome=r.nome,
            chave=r.chave,
            projeto=r.projeto,
            local=r.local,
            checkin=r.checkin,
            time=r.time,
        )
        for r in rows
    ]


@router.get("/checkout", response_model=list[UserRow], dependencies=[Depends(require_admin_key)])
def list_checkout(db: Session = Depends(get_db)) -> list[UserRow]:
    rows = db.execute(select(User).where(User.checkin.is_(False)).order_by(desc(User.time))).scalars().all()
    return [
        UserRow(
            rfid=r.rfid,
            nome=r.nome,
            chave=r.chave,
            projeto=r.projeto,
            local=r.local,
            checkin=r.checkin,
            time=r.time,
        )
        for r in rows
    ]


@router.get("/pending", response_model=list[PendingRow], dependencies=[Depends(require_admin_key)])
def list_pending(db: Session = Depends(get_db)) -> list[PendingRow]:
    rows = db.execute(select(PendingRegistration).order_by(desc(PendingRegistration.last_seen_at))).scalars().all()
    return [
        PendingRow(
            id=r.id,
            rfid=r.rfid,
            first_seen_at=r.first_seen_at,
            last_seen_at=r.last_seen_at,
            attempts=r.attempts,
        )
        for r in rows
    ]


@router.post("/users", dependencies=[Depends(require_admin_key)])
def upsert_user(payload: AdminUserUpsert, db: Session = Depends(get_db)) -> dict:
    user = db.get(User, payload.rfid)
    if user:
        user.nome = payload.nome
        user.chave = payload.chave
        user.projeto = payload.projeto
    else:
        user = User(
            rfid=payload.rfid,
            nome=payload.nome,
            chave=payload.chave,
            projeto=payload.projeto,
            local=None,
            checkin=False,
            time=now_sgt(),
        )
        db.add(user)

    pending = db.execute(select(PendingRegistration).where(PendingRegistration.rfid == payload.rfid)).scalar_one_or_none()
    if pending:
        db.delete(pending)

    log_event(
        db,
        idempotency_key=f"register-{uuid4()}",
        source="admin",
        action="register",
        status="done",
        message="User registered via admin",
        rfid=payload.rfid,
        project=payload.projeto,
        request_path="/api/admin/users",
        http_status=200,
        submitted_at=now_sgt(),
        details=f"nome={payload.nome}",
    )
    db.commit()

    return {"ok": True, "rfid": payload.rfid}


@router.delete("/pending/{pending_id}", dependencies=[Depends(require_admin_key)])
def remove_pending(pending_id: int, db: Session = Depends(get_db)) -> dict:
    pending = db.get(PendingRegistration, pending_id)
    if pending is None:
        log_event(
            db,
            source="admin",
            action="pending",
            status="failed",
            message="Pending registration not found for removal",
            request_path=f"/api/admin/pending/{pending_id}",
            http_status=404,
            details=f"pending_id={pending_id}",
            commit=True,
        )
        raise HTTPException(status_code=404, detail="Pending registration not found")

    pending_rfid = pending.rfid
    db.delete(pending)
    log_event(
        db,
        source="admin",
        action="pending",
        status="removed",
        message="Pending registration removed via admin",
        rfid=pending_rfid,
        request_path=f"/api/admin/pending/{pending_id}",
        http_status=200,
        details=f"pending_id={pending_id}",
    )
    db.commit()
    return {"ok": True, "id": pending_id}


@router.get("/events", response_model=list[EventRow], dependencies=[Depends(require_admin_key)])
def list_events(db: Session = Depends(get_db)) -> list[EventRow]:
    rows = db.execute(select(CheckEvent).order_by(desc(CheckEvent.id)).limit(200)).scalars().all()
    return [
        EventRow(
            id=r.id,
            source=r.source,
            rfid=r.rfid,
            device_id=r.device_id,
            local=r.local,
            action=r.action,
            status=r.status,
            message=r.message,
            details=r.details,
            project=r.project,
            request_path=r.request_path,
            http_status=r.http_status,
            retry_count=r.retry_count,
            event_time=r.event_time,
        )
        for r in rows
    ]
