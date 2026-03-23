from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import get_db
from ..models import CheckEvent, PendingRegistration, User
from ..schemas import AdminUserUpsert, EventRow, PendingRow, UserRow
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
            checkin=False,
            time=now_sgt(),
        )
        db.add(user)

    pending = db.execute(select(PendingRegistration).where(PendingRegistration.rfid == payload.rfid)).scalar_one_or_none()
    if pending:
        db.delete(pending)

    db.add(
        CheckEvent(
            idempotency_key=f"register-{uuid4()}",
            rfid=payload.rfid,
            action="register",
            status="done",
            message="User registered via admin",
            project=payload.projeto,
            event_time=now_sgt(),
            submitted_at=now_sgt(),
            retry_count=0,
        )
    )
    db.commit()

    return {"ok": True, "rfid": payload.rfid}


@router.get("/events", response_model=list[EventRow], dependencies=[Depends(require_admin_key)])
def list_events(db: Session = Depends(get_db)) -> list[EventRow]:
    rows = db.execute(select(CheckEvent).order_by(desc(CheckEvent.id)).limit(200)).scalars().all()
    return [
        EventRow(
            id=r.id,
            rfid=r.rfid,
            action=r.action,
            status=r.status,
            message=r.message,
            project=r.project,
            event_time=r.event_time,
        )
        for r in rows
    ]
