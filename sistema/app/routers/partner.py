import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import EndpointApiKey, User, Project
from ..schemas import (
    AdminActionResponse,
    CheckingInfoEntry,
    CheckingInfoResponse,
    EndpointApiKeyRow,
    EndpointApiKeyRotateResponse,
)
from ..services.admin_auth import get_authenticated_admin_from_session, user_has_admin_access, require_full_admin_session
from ..services.project_catalog import list_projects
from ..services.time_utils import build_timezone_context, now_sgt
from ..services.user_sync import resolve_latest_user_activities
from ..services.user_activity import is_user_inactive
from ..services.user_projects import list_user_project_names_map, normalize_user_project_names
from ..routers.admin import format_assiduidade_label, build_presence_activity_fields

router = APIRouter(prefix="/api/partner", tags=["partner"])

CHECKINGINFO_ENDPOINT_NAME = "checkinginfo"

ADMIN_PARTNER_PERFIL = 9


def require_partner_admin_session(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Requires an admin session with perfil = 9 (partner manager)."""
    admin = get_authenticated_admin_from_session(request, db)
    if admin is None:
        raise HTTPException(status_code=401, detail="Sessao administrativa invalida ou expirada")
    if not user_has_admin_access(admin):
        raise HTTPException(status_code=403, detail="Este usuario nao possui permissao para esta area do Admin.")
    if (admin.perfil or 0) != ADMIN_PARTNER_PERFIL:
        raise HTTPException(status_code=403, detail="Apenas administradores com perfil 9 podem gerenciar chaves de endpoints.")
    return admin


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_endpoint_key(db: Session, endpoint_name: str) -> EndpointApiKey | None:
    return db.execute(
        select(EndpointApiKey).where(EndpointApiKey.endpoint_name == endpoint_name)
    ).scalar_one_or_none()


def _verify_api_key(db: Session, endpoint_name: str, provided_key: str) -> None:
    record = _get_endpoint_key(db, endpoint_name)
    if record is None:
        raise HTTPException(status_code=403, detail="Endpoint nao configurado.")
    if not secrets.compare_digest(record.secret_key, provided_key):
        raise HTTPException(status_code=403, detail="Chave de acesso invalida.")


# ---------------------------------------------------------------------------
# Public partner endpoint
# ---------------------------------------------------------------------------

@router.get("/checkinginfo", response_model=CheckingInfoResponse)
def get_checking_info(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> CheckingInfoResponse:
    """
    Returns the current check-in and check-out status of all active users.
    Requires the X-API-Key header with the secret key configured for the
    'checkinginfo' endpoint.
    """
    _verify_api_key(db, CHECKINGINFO_ENDPOINT_NAME, x_api_key)

    all_projects = list_projects(db)
    projects_by_name = {project.name: project for project in all_projects}
    current_time = now_sgt()

    users = db.execute(select(User).order_by(User.nome, User.id)).scalars().all()
    latest_activities = resolve_latest_user_activities(db, users=users)

    entries: list[CheckingInfoEntry] = []

    for user in users:
        latest_activity = latest_activities.get(user.id)
        if latest_activity is None:
            continue
        if is_user_inactive(latest_activity.event_time, reference_time=current_time):
            continue

        action = latest_activity.action
        if action not in ("checkin", "checkout"):
            continue

        project = projects_by_name.get(user.projeto)
        timezone_context = build_timezone_context(
            project_name=project.name if project is not None else user.projeto,
            country_name=project.country_name if project is not None else None,
            timezone_name=project.timezone_name if project is not None else None,
            reference_time=latest_activity.event_time,
        )
        raw_time, _date_label, _time_label, _day_key = build_presence_activity_fields(
            event_time=latest_activity.event_time,
            timezone_context=timezone_context,
            can_view_activity_time=True,
        )

        entries.append(
            CheckingInfoEntry(
                nome=user.nome,
                chave=user.chave,
                projeto=user.projeto,
                atividade="check-in" if action == "checkin" else "check-out",
                horario=raw_time,
                local=latest_activity.local if latest_activity.local is not None else user.local,
                assiduidade=format_assiduidade_label(latest_activity.ontime),
            )
        )

    entries.sort(key=lambda e: (e.horario or current_time), reverse=True)

    return CheckingInfoResponse(ok=True, total=len(entries), entries=entries)


# ---------------------------------------------------------------------------
# Admin management endpoints (endpoint API key management)
# ---------------------------------------------------------------------------

@router.get(
    "/admin/endpoint-keys",
    response_model=list[EndpointApiKeyRow],
    dependencies=[Depends(require_partner_admin_session)],
)
def list_endpoint_api_keys(db: Session = Depends(get_db)) -> list[EndpointApiKeyRow]:
    rows = db.execute(select(EndpointApiKey).order_by(EndpointApiKey.id)).scalars().all()
    return [
        EndpointApiKeyRow(
            id=row.id,
            endpoint_name=row.endpoint_name,
            secret_key=row.secret_key,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.post(
    "/admin/endpoint-keys/{endpoint_name}/rotate",
    response_model=EndpointApiKeyRotateResponse,
    dependencies=[Depends(require_partner_admin_session)],
)
def rotate_endpoint_api_key(
    endpoint_name: str,
    db: Session = Depends(get_db),
) -> EndpointApiKeyRotateResponse:
    record = _get_endpoint_key(db, endpoint_name)
    if record is None:
        raise HTTPException(status_code=404, detail="Endpoint nao encontrado.")

    new_key = secrets.token_hex(16)  # 32 hex chars
    record.secret_key = new_key
    record.updated_at = now_sgt()
    db.commit()
    db.refresh(record)

    return EndpointApiKeyRotateResponse(
        ok=True,
        message=f"Chave do endpoint '{endpoint_name}' atualizada com sucesso.",
        endpoint_name=endpoint_name,
        secret_key=new_key,
    )
