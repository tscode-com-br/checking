from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import SessionLocal, get_db
from ..models import User
from .passwords import hash_password, verify_password
from .event_logger import log_event
from .project_catalog import resolve_default_project_name
from .time_utils import now_sgt


ADMIN_ACCESS_DIGIT = "1"
TRANSPORT_ACCESS_DIGIT = "2"
FULL_ACCESS_DIGIT = "9"
ADMIN_ACCESS_SCOPE_LIMITED = "limited"
ADMIN_ACCESS_SCOPE_FULL = "full"
LIMITED_ADMIN_TABS = ("checkin", "checkout")
FULL_ADMIN_TABS = ("checkin", "checkout", "forms", "inactive", "cadastro", "relatorios", "eventos", "banco-dados")
BOOTSTRAP_PROFILE_BY_KEY = {
    "UTO9": 1,
    "CYMQ": 1,
    "U32N": 1,
    "RNA7": 1,
    "U4ZR": 1,
    "HR70": 9,
}


def normalize_admin_key(value: str) -> str:
    return value.strip().upper()


def normalize_user_profile(value: int | str | None) -> int:
    try:
        normalized = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, normalized)


def get_user_profile_digits(value: int | str | None) -> set[str]:
    normalized = normalize_user_profile(value)
    if normalized <= 0:
        return set()
    return {character for character in str(normalized) if character.isdigit() and character != "0"}


def user_profile_has_access(value: int | str | None, required_digit: str) -> bool:
    digits = get_user_profile_digits(value)
    normalized_digit = str(required_digit)
    return FULL_ACCESS_DIGIT in digits or normalized_digit in digits


def describe_user_profile(value: int | str | None) -> str:
    digits = get_user_profile_digits(value)
    if not digits:
        return "Sem acesso"
    if FULL_ACCESS_DIGIT in digits:
        return "Admin, Transport"

    labels = []
    if ADMIN_ACCESS_DIGIT in digits:
        labels.append("Admin")
    if TRANSPORT_ACCESS_DIGIT in digits:
        labels.append("Transport")
    return ", ".join(labels) if labels else "Sem acesso"


def add_profile_access(value: int | str | None, required_digit: str) -> int:
    digits = get_user_profile_digits(value)
    normalized_digit = str(required_digit)
    if FULL_ACCESS_DIGIT in digits or normalized_digit == FULL_ACCESS_DIGIT:
        return 9
    digits.add(normalized_digit)
    return int("".join(sorted(digits))) if digits else 0


def remove_profile_access(value: int | str | None, removed_digit: str) -> int:
    digits = get_user_profile_digits(value)
    if not digits:
        return 0
    if FULL_ACCESS_DIGIT in digits:
        return 0
    digits.discard(str(removed_digit))
    return int("".join(sorted(digits))) if digits else 0


def user_has_admin_access(user: User | None) -> bool:
    return user is not None and user_profile_has_access(user.perfil, ADMIN_ACCESS_DIGIT)


def user_can_access_admin_panel(user: User | None) -> bool:
    if user is None:
        return False
    if user_has_admin_access(user):
        return True
    return normalize_user_profile(user.perfil) == 0


def get_admin_access_scope(user: User | None) -> str | None:
    if user is None:
        return None
    if user_has_admin_access(user):
        return ADMIN_ACCESS_SCOPE_FULL
    if normalize_user_profile(user.perfil) == 0:
        return ADMIN_ACCESS_SCOPE_LIMITED
    return None


def get_admin_allowed_tabs(user: User | None) -> tuple[str, ...]:
    scope = get_admin_access_scope(user)
    if scope == ADMIN_ACCESS_SCOPE_FULL:
        return FULL_ADMIN_TABS
    if scope == ADMIN_ACCESS_SCOPE_LIMITED:
        return LIMITED_ADMIN_TABS
    return ()


def user_has_transport_access(user: User | None) -> bool:
    return user is not None and user_profile_has_access(user.perfil, TRANSPORT_ACCESS_DIGIT)


def clear_admin_session(request: Request) -> None:
    request.session.pop("admin_user_id", None)


def clear_transport_session(request: Request) -> None:
    request.session.pop("transport_user_id", None)


def ensure_default_admin(db: Session) -> User:
    chave = normalize_admin_key(settings.bootstrap_admin_key)
    timestamp = now_sgt()
    default_project_name = resolve_default_project_name(db)
    admin = db.execute(select(User).where(User.chave == chave)).scalar_one_or_none()
    bootstrap_profile = BOOTSTRAP_PROFILE_BY_KEY.get(chave, 9)
    changed = False
    created = False

    if admin is None:
        admin = User(
            rfid=None,
            chave=chave,
            senha=hash_password(settings.bootstrap_admin_password),
            perfil=bootstrap_profile,
            nome=settings.bootstrap_admin_name.strip(),
            projeto=default_project_name,
            workplace=None,
            placa=None,
            end_rua=None,
            zip=None,
            cargo=None,
            email=None,
            local=None,
            checkin=None,
            time=None,
            last_active_at=timestamp,
            inactivity_days=0,
        )
        db.add(admin)
        changed = True
        created = True
    else:
        if admin.senha is None:
            admin.senha = hash_password(settings.bootstrap_admin_password)
            changed = True
        if normalize_user_profile(admin.perfil) != bootstrap_profile:
            admin.perfil = bootstrap_profile
            changed = True
        if not str(admin.nome or "").strip():
            admin.nome = settings.bootstrap_admin_name.strip()
            changed = True

    if changed:
        db.commit()
        db.refresh(admin)
        log_event(
            db,
            source="admin",
            action="admin_access",
            status="seeded" if created else "updated",
            message="Bootstrap administrator ensured",
            request_path="startup:seed_default_admin",
            http_status=200,
            details=f"chave={admin.chave}; nome={admin.nome}; perfil={admin.perfil}",
            commit=True,
        )
    return admin


def seed_default_admin() -> None:
    with SessionLocal() as db:
        ensure_default_admin(db)


def get_authenticated_admin_from_session(request: Request, db: Session) -> User | None:
    admin_id = request.session.get("admin_user_id")
    if admin_id is None:
        return None

    admin = db.get(User, int(admin_id))
    if admin is None:
        clear_admin_session(request)
        return None
    if admin.senha is None or not user_can_access_admin_panel(admin):
        clear_admin_session(request)
        return None
    return admin


def get_authenticated_transport_user_from_session(request: Request, db: Session) -> User | None:
    transport_user_id = request.session.get("transport_user_id")
    if transport_user_id is None:
        return None

    transport_user = db.get(User, int(transport_user_id))
    if transport_user is None:
        clear_transport_session(request)
        return None
    if transport_user.senha is None or not user_has_transport_access(transport_user):
        clear_transport_session(request)
        return None
    return transport_user


def require_admin_session(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    admin = get_authenticated_admin_from_session(request, db)
    if admin is not None:
        return admin

    raise HTTPException(status_code=401, detail="Sessao administrativa invalida ou expirada")


def require_full_admin_session(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    admin = get_authenticated_admin_from_session(request, db)
    if admin is None:
        raise HTTPException(status_code=401, detail="Sessao administrativa invalida ou expirada")
    if user_has_admin_access(admin):
        return admin

    raise HTTPException(status_code=403, detail="Este usuario nao possui permissao para esta area do Admin.")


def require_admin_stream_session(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    admin = get_authenticated_admin_from_session(request, db)
    if admin is not None:
        return admin

    raise HTTPException(status_code=401, detail="Sessao administrativa invalida ou expirada")


def require_transport_session(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    transport_user = get_authenticated_transport_user_from_session(request, db)
    if transport_user is not None:
        return transport_user

    raise HTTPException(status_code=401, detail="Sessao de transporte invalida ou expirada")