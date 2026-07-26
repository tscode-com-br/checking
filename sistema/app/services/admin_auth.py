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
COMBINED_ADMIN_TRANSPORT_PROFILE = 3  # replaces legacy profile 12

# The only profile values the system is allowed to store.
#
#   0 → usuário comum.
#   1 → administrador dos projetos em que está cadastrado. Vê tudo daqueles
#       projetos e aprova novos administradores neles, mas NÃO vê os horários das
#       atividades de check-in/check-out.
#   2 → administrador apenas do dashboard Transport.
#   3 → 1 + 2 (o valor canônico do combo; a migração 0071 renomeou o antigo "12").
#   9 → acesso irrestrito a absolutamente tudo, em todos os projetos, esteja ou
#       não cadastrado em algum. É o único perfil que vê os horários das
#       atividades. Para ele, cadastro em projeto vale só para o próprio
#       check-in/check-out.
#
# Anything else is nonsense in this encoding. The profile is a SET OF DIGITS, so a
# value like 19 parses as {1,9} — "admin + tudo" — which is redundant, since 9
# alone already grants everything. Worse, it lands in an inconsistent middle state:
# digit 9 makes it unrestricted by project scope, while the exact `perfil == 9`
# checks (deleting an accident, revoking another super-admin) still refuse it. The
# same ambiguity already bit this project once with the legacy "12", which is why
# 3 exists. Nothing in add_profile_access/remove_profile_access can produce a
# non-canonical value — they collapse to 9 or 0 — but the cadastro API used to
# accept any integer 0–999 straight from the request body, so 19 (or 777) was one
# PUT away. Validation lives in schemas.AdminUserUpsert / AdminProfileUpdateRequest.
CANONICAL_USER_PROFILES: frozenset[int] = frozenset({
    0,
    int(ADMIN_ACCESS_DIGIT),
    int(TRANSPORT_ACCESS_DIGIT),
    COMBINED_ADMIN_TRANSPORT_PROFILE,
    int(FULL_ACCESS_DIGIT),
})


def digits_to_profile(digits: set[str]) -> int:
    """Map a set of access digits to the canonical profile integer.

    {"9", ...} → 9: the full-access digit subsumes every other one, so there is
    nothing to combine. Without this, {"1","9"} produced the literal 19 — an
    "admin + tudo" value that is redundant by definition and lands in an
    inconsistent middle state (unrestricted by project scope because it carries
    the digit 9, yet refused by the exact `perfil == 9` checks). This function was
    the only thing that could mint such a value.

    {"1","2"} → 3 (not 12), same reasoning applied to the legacy combo.
    """
    if not digits:
        return 0
    if FULL_ACCESS_DIGIT in digits:
        return int(FULL_ACCESS_DIGIT)
    if digits == {ADMIN_ACCESS_DIGIT, TRANSPORT_ACCESS_DIGIT}:
        return COMBINED_ADMIN_TRANSPORT_PROFILE
    return int("".join(sorted(digits)))
ADMIN_ACCESS_SCOPE_LIMITED = "limited"
ADMIN_ACCESS_SCOPE_FULL = "full"
LIMITED_ADMIN_TABS = ("checkin", "checkout")
FULL_ADMIN_TABS = ("checkin", "checkout", "forms", "inactive", "cadastro", "relatorios", "eventos", "banco-dados", "acidente")
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
    if normalized == COMBINED_ADMIN_TRANSPORT_PROFILE:
        return {ADMIN_ACCESS_DIGIT, TRANSPORT_ACCESS_DIGIT}
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
    return digits_to_profile(digits)


def remove_profile_access(value: int | str | None, removed_digit: str) -> int:
    digits = get_user_profile_digits(value)
    if not digits:
        return 0
    if FULL_ACCESS_DIGIT in digits:
        return 0
    digits.discard(str(removed_digit))
    return digits_to_profile(digits)


def user_has_admin_access(user: User | None) -> bool:
    return user is not None and user_profile_has_access(user.perfil, ADMIN_ACCESS_DIGIT)


def user_has_full_admin_access(user: User | None) -> bool:
    """True somente para admins FULL (perfil com dígito 9 — ex.: HR70), que NÃO são escopados por
    projeto e enxergam/administram todos os projetos + órfãos.

    Distinto de:
      - `user_has_admin_access` (True para perfil 1 E 9): apenas indica acesso ao painel admin;
      - `get_admin_access_scope` (== "full"/"limited"): trata de quais ABAS, não de quais PROJETOS.
    Um admin perfil 1 tem acesso ao painel mas é escopado às suas memberships de projeto."""
    return user is not None and FULL_ACCESS_DIGIT in get_user_profile_digits(user.perfil)


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


def profile_can_view_activity_time(value: int | str | None) -> bool:
    return normalize_user_profile(value) == 9


def user_can_view_activity_time(user: User | None) -> bool:
    return user is not None and profile_can_view_activity_time(user.perfil)


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
            admin_monitored_projects_json=None,
            workplace=None,
            placa=None,
            end_rua=None,
            zip=None,
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
        if admin.admin_monitored_projects_json is not None:
            admin.admin_monitored_projects_json = None
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


def require_admin_identity(
    request: Request,
    db: Session = Depends(get_db),
):
    """Same auth as ``require_full_admin_session`` but returns ``AdminActorIdentity``.

    Use this dependency in any endpoint that writes to a column whose FK
    targets ``admin_users.id`` (``*_by_admin_id``, ``actor_user_id``). The
    returned ``AdminActorIdentity`` exposes both the session ``User`` and
    the paired ``AdminUser`` row (lazily created if missing), so
    endpoints never have to confuse the two IDs.
    """
    # Local import avoids a circular dependency: admin_identity imports
    # from models, and several callers import admin_auth at module load.
    from .admin_identity import AdminActorIdentity, resolve_admin_user_for_user

    admin = require_full_admin_session(request, db)
    admin_user = resolve_admin_user_for_user(db, admin)
    return AdminActorIdentity(user=admin, admin_user=admin_user)


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