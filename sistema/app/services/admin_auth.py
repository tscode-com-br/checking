from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import SessionLocal, get_db
from ..models import AdminUser
from .passwords import hash_password, verify_password
from .event_logger import log_event
from .time_utils import now_sgt


def normalize_admin_key(value: str) -> str:
    return value.strip().upper()


def ensure_default_admin(db: Session) -> AdminUser:
    chave = normalize_admin_key(settings.bootstrap_admin_key)
    admin = db.execute(select(AdminUser).where(AdminUser.chave == chave)).scalar_one_or_none()
    if admin is not None:
        return admin

    timestamp = now_sgt()
    admin = AdminUser(
        chave=chave,
        nome_completo=settings.bootstrap_admin_name.strip(),
        password_hash=hash_password(settings.bootstrap_admin_password),
        requires_password_reset=False,
        approved_by_admin_id=None,
        approved_at=timestamp,
        password_reset_requested_at=None,
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    log_event(
        db,
        source="admin",
        action="admin_access",
        status="seeded",
        message="Bootstrap administrator created",
        request_path="startup:seed_default_admin",
        http_status=200,
        details=f"chave={admin.chave}; nome={admin.nome_completo}",
        commit=True,
    )
    return admin


def seed_default_admin() -> None:
    with SessionLocal() as db:
        ensure_default_admin(db)


def get_authenticated_admin_from_session(request: Request, db: Session) -> AdminUser | None:
    admin_id = request.session.get("admin_user_id")
    if admin_id is None:
        return None

    admin = db.get(AdminUser, int(admin_id))
    if admin is None:
        request.session.clear()
        return None
    if admin.password_hash is None or admin.requires_password_reset:
        request.session.clear()
        return None
    return admin


def require_admin_session(
    request: Request,
    db: Session = Depends(get_db),
) -> AdminUser:
    admin = get_authenticated_admin_from_session(request, db)
    if admin is not None:
        return admin

    raise HTTPException(status_code=401, detail="Sessao administrativa invalida ou expirada")


def require_admin_stream_session(
    request: Request,
    db: Session = Depends(get_db),
) -> AdminUser:
    admin = get_authenticated_admin_from_session(request, db)
    if admin is not None:
        return admin

    raise HTTPException(status_code=401, detail="Sessao administrativa invalida ou expirada")