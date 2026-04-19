import asyncio
import json
from datetime import date, datetime, time as dt_time, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import asc, delete, desc, func, or_, select, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    AdminAccessRequest,
    CheckEvent,
    CheckingHistory,
    ManagedLocation,
    PendingRegistration,
    Project,
    Workplace,
    User,
    UserSyncEvent,
    Vehicle,
)
from ..schemas import (
    AdminAccessRequestCreate,
    AdminActionResponse,
    DatabaseEventFilterOptions,
    DatabaseEventListResponse,
    AdminIdentity,
    AdminLocationsResponse,
    AdminLocationSettingsResponse,
    AdminLocationSettingsUpdate,
    AdminLocationUpsert,
    AdminLoginRequest,
    AdminManagementRow,
    AdminPasswordResetRequest,
    AdminPasswordSetRequest,
    ProjectCreate,
    ProjectRow,
    AdminSessionResponse,
    AdminUserListRow,
    AdminUserUpsert,
    EventArchiveCreateResponse,
    EventArchiveListResponse,
    EventArchiveRow,
    EventRow,
    InactiveUserRow,
    LocationRow,
    PendingRow,
    UserRow,
)
from ..services.admin_auth import (
    ADMIN_ACCESS_DIGIT,
    add_profile_access,
    clear_admin_session,
    describe_user_profile,
    get_authenticated_admin_from_session,
    hash_password,
    normalize_admin_key,
    normalize_user_profile,
    remove_profile_access,
    require_admin_session,
    require_admin_stream_session,
    user_has_admin_access,
    user_profile_has_access,
    verify_password,
)
from ..services.admin_updates import admin_updates_broker, notify_admin_data_changed
from ..services.event_archives import (
    build_event_archives_zip,
    create_event_archive,
    delete_event_archive,
    get_event_archive_path,
    list_event_archives_page,
)
from ..services.event_logger import log_event
from ..services.managed_locations import dump_location_coordinates, extract_location_coordinates
from ..services.location_settings import (
    get_location_accuracy_threshold_meters,
    upsert_location_settings,
)
from ..services.project_catalog import ensure_known_project, list_projects, resolve_default_project_name
from ..services.time_utils import now_sgt
from ..services.user_activity import (
    calculate_inactivity_days,
    has_missing_checkout_since_midnight,
    is_user_inactive,
    sync_user_inactivity,
)
from ..services.user_sync import find_user_by_chave, find_user_by_rfid, resolve_latest_user_activity

router = APIRouter(prefix="/api/admin", tags=["admin"])

EVENT_KEY_FIELDS = ("approved_by", "rejected_by", "revoked_by", "updated_by", "chave")
DATABASE_EVENT_ACTIONS = ("checkin", "checkout")
DATABASE_EVENT_PAGE_SIZE = 50
DATABASE_EVENT_DEFAULT_SORT_BY = "event_time"
DATABASE_EVENT_DEFAULT_SORT_DIRECTION = "desc"
DATABASE_EVENT_SQL_SORT_FIELDS = {
    "id": CheckEvent.id,
    "event_time": CheckEvent.event_time,
    "action": func.lower(func.coalesce(CheckEvent.action, "")),
    "rfid": func.lower(func.coalesce(CheckEvent.rfid, "")),
    "project": func.lower(func.coalesce(CheckEvent.project, "")),
    "local": func.lower(func.coalesce(CheckEvent.local, "")),
    "source": func.lower(func.coalesce(CheckEvent.source, "")),
    "status": func.lower(func.coalesce(CheckEvent.status, "")),
    "http_status": func.coalesce(CheckEvent.http_status, -1),
    "device_id": func.lower(func.coalesce(CheckEvent.device_id, "")),
    "message": func.lower(func.coalesce(CheckEvent.message, "")),
    "details": func.lower(func.coalesce(CheckEvent.details, "")),
}
DATABASE_EVENT_SORTABLE_FIELDS = frozenset((*DATABASE_EVENT_SQL_SORT_FIELDS.keys(), "chave"))
DATABASE_EVENT_SORT_DIRECTIONS = frozenset(("asc", "desc"))


def format_assiduidade_label(ontime: bool | None) -> str:
    return "Retroativo" if ontime is False else "Normal"


def format_quantity(value: int, singular: str, plural: str) -> str:
    return f"{value} {singular if value == 1 else plural}"


def parse_event_details(details: str | None) -> dict[str, str]:
    if not details:
        return {}

    parsed: dict[str, str] = {}
    for part in str(details).split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        normalized_key = key.strip()
        normalized_value = value.strip()
        if normalized_key and normalized_value:
            parsed[normalized_key] = normalized_value
    return parsed


def resolve_event_key(event: CheckEvent, *, user_keys_by_rfid: dict[str, str]) -> str | None:
    details_map = parse_event_details(event.details)
    for field_name in EVENT_KEY_FIELDS:
        field_value = details_map.get(field_name)
        if field_value:
            return field_value.upper()
    if event.rfid:
        return user_keys_by_rfid.get(event.rfid)
    return None


def build_event_row_payload(rows: list[CheckEvent], db: Session) -> list[EventRow]:
    rfids = sorted({row.rfid for row in rows if row.rfid})
    user_keys_by_rfid: dict[str, str] = {}
    if rfids:
        user_keys_by_rfid = {
            rfid: chave
            for rfid, chave in db.execute(select(User.rfid, User.chave).where(User.rfid.in_(rfids))).all()
            if rfid is not None
        }

    return [
        EventRow(
            id=row.id,
            source=row.source,
            rfid=row.rfid,
            chave=resolve_event_key(row, user_keys_by_rfid=user_keys_by_rfid),
            device_id=row.device_id,
            local=row.local,
            action=row.action,
            status=row.status,
            message=row.message,
            details=row.details,
            project=row.project,
            ontime=row.ontime,
            request_path=row.request_path,
            http_status=row.http_status,
            retry_count=row.retry_count,
            event_time=row.event_time,
        )
        for row in rows
    ]


def get_database_event_sort_value(row: EventRow, sort_by: str) -> object:
    if sort_by == "id":
        return row.id
    if sort_by == "event_time":
        return row.event_time
    if sort_by == "http_status":
        return row.http_status if row.http_status is not None else -1
    if sort_by == "chave":
        return (row.chave or "").upper()
    if sort_by == "action":
        return row.action or ""
    if sort_by == "rfid":
        return row.rfid or ""
    if sort_by == "project":
        return row.project or ""
    if sort_by == "local":
        return row.local or ""
    if sort_by == "source":
        return row.source or ""
    if sort_by == "status":
        return row.status or ""
    if sort_by == "device_id":
        return row.device_id or ""
    if sort_by == "message":
        return row.message or ""
    if sort_by == "details":
        return row.details or ""
    return row.event_time


def sort_database_event_payload(items: list[EventRow], sort_by: str, sort_direction: str) -> list[EventRow]:
    reverse = sort_direction == "desc"
    return sorted(
        items,
        key=lambda row: (get_database_event_sort_value(row, sort_by), row.id),
        reverse=reverse,
    )


def build_database_event_filter_options(db: Session) -> DatabaseEventFilterOptions:
    option_rows = db.execute(
        select(
            CheckEvent.rfid,
            CheckEvent.details,
            CheckEvent.action,
            CheckEvent.project,
            CheckEvent.source,
            CheckEvent.status,
        ).where(CheckEvent.action.in_(DATABASE_EVENT_ACTIONS))
    ).all()

    rfids = sorted({rfid for rfid, *_ in option_rows if rfid})
    user_keys_by_rfid: dict[str, str] = {}
    if rfids:
        user_keys_by_rfid = {
            rfid: chave
            for rfid, chave in db.execute(select(User.rfid, User.chave).where(User.rfid.in_(rfids))).all()
            if rfid is not None
        }

    actions: set[str] = set()
    keys: set[str] = set()
    seen_rfids: set[str] = set()
    projects: set[str] = set()
    sources: set[str] = set()
    statuses: set[str] = set()

    for rfid, details, action, project, source, status in option_rows:
        if action:
            actions.add(action)
        if rfid:
            seen_rfids.add(rfid)
        if project:
            projects.add(project)
        if source:
            sources.add(source)
        if status:
            statuses.add(status)

        resolved_key = None
        details_map = parse_event_details(details)
        for field_name in EVENT_KEY_FIELDS:
            field_value = details_map.get(field_name)
            if field_value:
                resolved_key = field_value.upper()
                break
        if resolved_key is None and rfid:
            resolved_key = user_keys_by_rfid.get(rfid)
        if resolved_key:
            keys.add(resolved_key)

    return DatabaseEventFilterOptions(
        action=sorted(actions),
        chave=sorted(keys),
        rfid=sorted(seen_rfids),
        project=sorted(projects),
        source=sorted(sources),
        status=sorted(statuses),
    )


def build_location_settings_log_message(
    *,
    previous_accuracy_threshold_meters: int,
    current_accuracy_threshold_meters: int,
) -> str:
    changes: list[str] = []
    if previous_accuracy_threshold_meters != current_accuracy_threshold_meters:
        changes.append(
            "O valor do erro máximo para considerar a coordenada do usuário foi ajustado para "
            f"{format_quantity(current_accuracy_threshold_meters, 'metro', 'metros')}."
        )
    if changes:
        return " ".join(changes)
    return "As configurações de localização foram salvas sem alterações."


def build_presence_rows(db: Session, *, action: str, reference_time=None) -> list[UserRow]:
    rows = db.execute(select(User).order_by(User.nome, User.id)).scalars().all()
    payload: list[UserRow] = []
    current_time = reference_time or now_sgt()

    for user in rows:
        latest_activity = resolve_latest_user_activity(db, user=user)
        if latest_activity is None or latest_activity.action != action:
            continue
        if is_user_inactive(latest_activity.event_time, reference_time=current_time):
            continue

        payload.append(
            UserRow(
                id=user.id,
                rfid=user.rfid,
                nome=user.nome,
                chave=user.chave,
                projeto=user.projeto,
                local=latest_activity.local if latest_activity.local is not None else user.local,
                checkin=action == "checkin",
                time=latest_activity.event_time,
                assiduidade=format_assiduidade_label(latest_activity.ontime),
            )
        )

    payload.sort(key=lambda row: row.time, reverse=True)
    return payload


def build_missing_checkout_rows(db: Session, *, reference_time=None) -> list[UserRow]:
    rows = db.execute(select(User).order_by(User.nome, User.id)).scalars().all()
    payload: list[UserRow] = []
    current_time = reference_time or now_sgt()

    for user in rows:
        latest_activity = resolve_latest_user_activity(db, user=user)
        if latest_activity is None or latest_activity.action != "checkin":
            continue
        if is_user_inactive(latest_activity.event_time, reference_time=current_time):
            continue
        if not has_missing_checkout_since_midnight(latest_activity.event_time, reference_time=current_time):
            continue

        payload.append(
            UserRow(
                id=user.id,
                rfid=user.rfid,
                nome=user.nome,
                chave=user.chave,
                projeto=user.projeto,
                local=latest_activity.local if latest_activity.local is not None else user.local,
                checkin=True,
                time=latest_activity.event_time,
                assiduidade=format_assiduidade_label(latest_activity.ontime),
            )
        )

    payload.sort(key=lambda row: row.time, reverse=True)
    return payload


def build_inactive_rows(db: Session, *, reference_time=None) -> list[InactiveUserRow]:
    rows = db.execute(select(User).order_by(User.nome, User.id)).scalars().all()
    payload: list[InactiveUserRow] = []
    current_time = reference_time or now_sgt()

    for user in rows:
        latest_activity = resolve_latest_user_activity(db, user=user)
        if latest_activity is None:
            continue
        if not is_user_inactive(latest_activity.event_time, reference_time=current_time):
            continue

        payload.append(
            InactiveUserRow(
                id=user.id,
                rfid=user.rfid,
                nome=user.nome,
                chave=user.chave,
                projeto=user.projeto,
                latest_action=latest_activity.action,
                latest_time=latest_activity.event_time,
                inactivity_days=calculate_inactivity_days(latest_activity.event_time, reference_time=current_time),
            )
        )

    payload.sort(key=lambda row: (-row.inactivity_days, row.nome, row.chave))
    return payload


def notify_admin_views(*reasons: str) -> None:
    for reason in dict.fromkeys(reasons):
        notify_admin_data_changed(reason)


def encode_sse(payload: dict[str, str]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def build_admin_identity(admin: User) -> AdminIdentity:
    return AdminIdentity(id=admin.id, chave=admin.chave, nome_completo=admin.nome, perfil=admin.perfil)


def build_location_row(location: ManagedLocation) -> LocationRow:
    coordinates = extract_location_coordinates(location)
    primary_coordinate = coordinates[0]
    return LocationRow(
        id=location.id,
        local=location.local,
        latitude=primary_coordinate["latitude"],
        longitude=primary_coordinate["longitude"],
        coordinates=coordinates,
        tolerance_meters=location.tolerance_meters,
    )


def build_project_row(project: Project) -> ProjectRow:
    return ProjectRow(id=project.id, name=project.name)


def list_admin_rows(db: Session) -> list[AdminManagementRow]:
    admins = db.execute(
        select(User)
        .where(User.perfil != 0)
        .order_by(User.nome, User.chave)
    ).scalars().all()
    requests = db.execute(select(AdminAccessRequest).order_by(AdminAccessRequest.requested_at.desc())).scalars().all()

    rows: list[AdminManagementRow] = []
    for admin in admins:
        status = "password_reset_requested" if admin.senha is None else "active"
        status_label = describe_user_profile(admin.perfil)
        if admin.senha is None:
            status_label = f"{status_label} | senha pendente"
        rows.append(
            AdminManagementRow(
                id=admin.id,
                row_type="admin",
                chave=admin.chave,
                nome=admin.nome,
                perfil=admin.perfil,
                status=status,
                status_label=status_label,
                can_revoke=user_has_admin_access(admin),
                can_approve=False,
                can_reject=False,
                can_set_password=admin.senha is None and user_has_admin_access(admin),
            )
        )

    for request_row in requests:
        rows.append(
            AdminManagementRow(
                id=request_row.id,
                row_type="request",
                chave=request_row.chave,
                nome=request_row.nome_completo,
                perfil=None,
                status="pending",
                status_label="Solicitacao Pendente",
                can_revoke=False,
                can_approve=True,
                can_reject=True,
                can_set_password=False,
            )
        )

    return rows


@router.post("/auth/login", response_model=AdminActionResponse)
def admin_login(payload: AdminLoginRequest, request: Request, db: Session = Depends(get_db)) -> AdminActionResponse:
    key = normalize_admin_key(payload.chave)
    admin = db.execute(select(User).where(User.chave == key)).scalar_one_or_none()

    if admin is None:
        log_event(
            db,
            source="admin",
            action="login",
            status="failed",
            message="Administrative login rejected",
            request_path="/api/admin/auth/login",
            http_status=401,
            details=f"chave={key}",
            commit=True,
        )
        raise HTTPException(status_code=401, detail="Chave ou senha invalida")

    if not user_has_admin_access(admin):
        log_event(
            db,
            source="admin",
            action="login",
            status="blocked",
            message="Administrative login blocked due to missing admin profile",
            request_path="/api/admin/auth/login",
            http_status=403,
            details=f"chave={admin.chave}",
            commit=True,
        )
        raise HTTPException(
            status_code=403,
            detail="Este usuario nao possui acesso ao Admin.",
        )

    if admin.senha is None:
        log_event(
            db,
            source="admin",
            action="login",
            status="blocked",
            message="Administrative login blocked due to missing user password",
            request_path="/api/admin/auth/login",
            http_status=403,
            details=f"chave={admin.chave}",
            commit=True,
        )
        raise HTTPException(status_code=403, detail="Este usuario ainda nao possui senha cadastrada.")

    if not verify_password(payload.senha, admin.senha):
        log_event(
            db,
            source="admin",
            action="login",
            status="failed",
            message="Administrative login rejected",
            request_path="/api/admin/auth/login",
            http_status=401,
            details=f"chave={key}",
            commit=True,
        )
        raise HTTPException(status_code=401, detail="Chave ou senha invalida")

    clear_admin_session(request)
    request.session["admin_user_id"] = admin.id
    log_event(
        db,
        source="admin",
        action="login",
        status="done",
        message="Administrative login completed",
        request_path="/api/admin/auth/login",
        http_status=200,
        details=f"chave={admin.chave}",
        commit=True,
    )
    return AdminActionResponse(ok=True, message="Login realizado com sucesso.")


@router.post("/auth/logout", response_model=AdminActionResponse)
def admin_logout(request: Request, db: Session = Depends(get_db)) -> AdminActionResponse:
    admin = get_authenticated_admin_from_session(request, db)
    if admin is not None:
        log_event(
            db,
            source="admin",
            action="logout",
            status="done",
            message="Administrative logout completed",
            request_path="/api/admin/auth/logout",
            http_status=200,
            details=f"chave={admin.chave}",
            commit=True,
        )
    clear_admin_session(request)
    return AdminActionResponse(ok=True, message="Sessao encerrada com sucesso.")


@router.get("/auth/session", response_model=AdminSessionResponse)
def admin_session(request: Request, db: Session = Depends(get_db)) -> AdminSessionResponse:
    admin = get_authenticated_admin_from_session(request, db)
    if admin is None:
        return AdminSessionResponse(authenticated=False)
    return AdminSessionResponse(authenticated=True, admin=build_admin_identity(admin))


@router.post("/auth/request-access", response_model=AdminActionResponse)
def request_admin_access(payload: AdminAccessRequestCreate, db: Session = Depends(get_db)) -> AdminActionResponse:
    key = normalize_admin_key(payload.chave)
    existing_admin = db.execute(select(User).where(User.chave == key)).scalar_one_or_none()
    if existing_admin is not None and user_has_admin_access(existing_admin):
        log_event(
            db,
            source="admin",
            action="admin_request",
            status="failed",
            message="Administrative access request rejected because key already belongs to an admin",
            request_path="/api/admin/auth/request-access",
            http_status=409,
            details=f"chave={key}",
            commit=True,
        )
        raise HTTPException(status_code=409, detail="Ja existe um administrador com essa chave.")

    pending_request = db.execute(select(AdminAccessRequest).where(AdminAccessRequest.chave == key)).scalar_one_or_none()
    if pending_request is not None:
        log_event(
            db,
            source="admin",
            action="admin_request",
            status="failed",
            message="Administrative access request rejected because another request is already pending",
            request_path="/api/admin/auth/request-access",
            http_status=409,
            details=f"chave={key}",
            commit=True,
        )
        raise HTTPException(status_code=409, detail="Ja existe uma solicitacao pendente para essa chave.")

    db.add(
        AdminAccessRequest(
            chave=key,
            nome_completo=payload.nome_completo.strip(),
            password_hash=hash_password(payload.senha),
            requested_at=now_sgt(),
        )
    )
    log_event(
        db,
        source="admin",
        action="admin_request",
        status="pending",
        message="Administrative access request created",
        request_path="/api/admin/auth/request-access",
        http_status=200,
        details=f"chave={key}; nome={payload.nome_completo.strip()}",
    )
    db.commit()
    notify_admin_views("admin", "event")
    return AdminActionResponse(ok=True, message="Solicitacao enviada para aprovacao de um administrador.")


@router.post("/auth/request-password-reset", response_model=AdminActionResponse)
def request_password_reset(payload: AdminPasswordResetRequest, db: Session = Depends(get_db)) -> AdminActionResponse:
    key = normalize_admin_key(payload.chave)
    admin = db.execute(select(User).where(User.chave == key)).scalar_one_or_none()
    if admin is None or not user_has_admin_access(admin):
        log_event(
            db,
            source="admin",
            action="password",
            status="failed",
            message="Administrative password reset request failed because admin was not found",
            request_path="/api/admin/auth/request-password-reset",
            http_status=404,
            details=f"chave={key}",
            commit=True,
        )
        raise HTTPException(status_code=404, detail="Administrador nao encontrado para a chave informada.")
    if admin.senha is None:
        log_event(
            db,
            source="admin",
            action="password",
            status="failed",
            message="Administrative password reset request rejected because a reset is already pending",
            request_path="/api/admin/auth/request-password-reset",
            http_status=409,
            details=f"chave={admin.chave}",
            commit=True,
        )
        raise HTTPException(status_code=409, detail="Ja existe um pedido de recadastro de senha para esta chave.")

    admin.senha = None
    log_event(
        db,
        source="admin",
        action="password",
        status="pending",
        message="Administrative password reset requested",
        request_path="/api/admin/auth/request-password-reset",
        http_status=200,
        details=f"chave={admin.chave}",
    )
    db.commit()
    notify_admin_views("admin", "event")
    return AdminActionResponse(
        ok=True,
        message="Sua senha foi removida. Outro administrador devera cadastrar uma nova senha.",
    )


@router.get("/stream", dependencies=[Depends(require_admin_stream_session)])
async def stream_updates(request: Request) -> StreamingResponse:
    subscriber_id, queue = admin_updates_broker.subscribe()

    async def event_generator():
        try:
            yield encode_sse({"reason": "connected"})
            while True:
                if await request.is_disconnected():
                    break

                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            admin_updates_broker.unsubscribe(subscriber_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/administrators", response_model=list[AdminManagementRow], dependencies=[Depends(require_admin_session)])
def list_administrators(db: Session = Depends(get_db)) -> list[AdminManagementRow]:
    return list_admin_rows(db)


@router.get("/projects", response_model=list[ProjectRow], dependencies=[Depends(require_admin_session)])
def list_admin_projects(db: Session = Depends(get_db)) -> list[ProjectRow]:
    return [build_project_row(project) for project in list_projects(db)]


@router.post("/projects", response_model=ProjectRow, dependencies=[Depends(require_admin_session)])
def create_admin_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> ProjectRow:
    existing_project = db.execute(select(Project).where(Project.name == payload.name)).scalar_one_or_none()
    if existing_project is not None:
        raise HTTPException(status_code=409, detail="Ja existe um projeto com esse nome.")

    project = Project(name=payload.name)
    db.add(project)
    log_event(
        db,
        source="admin",
        action="register",
        status="done",
        message="Project created via admin",
        request_path="/api/admin/projects",
        http_status=200,
        details=f"updated_by={current_admin.chave}; project_name={payload.name}",
    )
    db.commit()
    db.refresh(project)
    notify_admin_views("register", "event")
    return build_project_row(project)


@router.delete("/projects/{project_id}", response_model=AdminActionResponse, dependencies=[Depends(require_admin_session)])
def remove_admin_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> AdminActionResponse:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto nao encontrado.")

    all_projects = list_projects(db)
    if len(all_projects) <= 1:
        raise HTTPException(status_code=409, detail="Nao e possivel remover o ultimo projeto cadastrado.")

    fallback_project = next((row.name for row in all_projects if row.id != project.id), None)
    linked_users = db.execute(select(User).where(User.projeto == project.name).order_by(User.id)).scalars().all()
    blocked_users = [user for user in linked_users if not user_has_admin_access(user)]
    if blocked_users:
        raise HTTPException(status_code=409, detail="Nao e possivel remover um projeto com usuarios vinculados.")

    for linked_user in linked_users:
        linked_user.projeto = fallback_project or resolve_default_project_name(db)

    db.delete(project)
    log_event(
        db,
        source="admin",
        action="register",
        status="removed",
        message="Project removed via admin",
        request_path=f"/api/admin/projects/{project_id}",
        http_status=200,
        details=(
            f"updated_by={current_admin.chave}; project_name={project.name}; project_id={project_id}; "
            f"reassigned_admin_users={len(linked_users)}"
        ),
    )
    db.commit()
    notify_admin_views("register", "event")
    return AdminActionResponse(ok=True, message="Projeto removido com sucesso.")


@router.post(
    "/administrators/requests/{request_id}/approve",
    response_model=AdminActionResponse,
)
def approve_administrator_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> AdminActionResponse:
    access_request = db.get(AdminAccessRequest, request_id)
    if access_request is None:
        log_event(
            db,
            source="admin",
            action="admin_request",
            status="failed",
            message="Administrative access request approval failed because request was not found",
            request_path=f"/api/admin/administrators/requests/{request_id}/approve",
            http_status=404,
            details=f"request_id={request_id}; approved_by={current_admin.chave}",
            commit=True,
        )
        raise HTTPException(status_code=404, detail="Solicitacao de administrador nao encontrada.")

    existing_admin = db.execute(select(User).where(User.chave == access_request.chave)).scalar_one_or_none()
    default_project_name = resolve_default_project_name(db)
    if existing_admin is not None and user_has_admin_access(existing_admin):
        log_event(
            db,
            source="admin",
            action="admin_request",
            status="failed",
            message="Administrative access request approval failed because target key is already assigned",
            request_path=f"/api/admin/administrators/requests/{request_id}/approve",
            http_status=409,
            details=f"chave={access_request.chave}; approved_by={current_admin.chave}",
            commit=True,
        )
        raise HTTPException(status_code=409, detail="Ja existe um administrador com essa chave.")

    timestamp = now_sgt()
    if existing_admin is None:
        db.add(
            User(
                rfid=None,
                chave=access_request.chave,
                senha=access_request.password_hash,
                perfil=1,
                nome=access_request.nome_completo,
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
        )
    else:
        existing_admin.nome = access_request.nome_completo
        existing_admin.senha = access_request.password_hash
        existing_admin.perfil = add_profile_access(existing_admin.perfil, ADMIN_ACCESS_DIGIT)

    log_event(
        db,
        source="admin",
        action="admin_request",
        status="approved",
        message="Administrative access request approved",
        request_path=f"/api/admin/administrators/requests/{request_id}/approve",
        http_status=200,
        details=f"chave={access_request.chave}; approved_by={current_admin.chave}",
    )
    db.delete(access_request)
    db.commit()
    notify_admin_views("admin", "event")
    return AdminActionResponse(ok=True, message="Administrador aprovado com sucesso.")


@router.post(
    "/administrators/requests/{request_id}/reject",
    response_model=AdminActionResponse,
)
def reject_administrator_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> AdminActionResponse:
    access_request = db.get(AdminAccessRequest, request_id)
    if access_request is None:
        log_event(
            db,
            source="admin",
            action="admin_request",
            status="failed",
            message="Administrative access request rejection failed because request was not found",
            request_path=f"/api/admin/administrators/requests/{request_id}/reject",
            http_status=404,
            details=f"request_id={request_id}; rejected_by={current_admin.chave}",
            commit=True,
        )
        raise HTTPException(status_code=404, detail="Solicitacao de administrador nao encontrada.")

    log_event(
        db,
        source="admin",
        action="admin_request",
        status="rejected",
        message="Administrative access request rejected",
        request_path=f"/api/admin/administrators/requests/{request_id}/reject",
        http_status=200,
        details=f"chave={access_request.chave}; rejected_by={current_admin.chave}",
    )
    db.delete(access_request)
    db.commit()
    notify_admin_views("admin", "event")
    return AdminActionResponse(ok=True, message="Solicitacao rejeitada com sucesso.")


@router.post("/administrators/{admin_id}/revoke", response_model=AdminActionResponse)
def revoke_administrator(
    admin_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> AdminActionResponse:
    admin = db.get(User, admin_id)
    if admin is None or not user_has_admin_access(admin):
        log_event(
            db,
            source="admin",
            action="admin_access",
            status="failed",
            message="Administrator revocation failed because target admin was not found",
            request_path=f"/api/admin/administrators/{admin_id}/revoke",
            http_status=404,
            details=f"admin_id={admin_id}; revoked_by={current_admin.chave}",
            commit=True,
        )
        raise HTTPException(status_code=404, detail="Administrador nao encontrado.")
    if admin.id == current_admin.id:
        log_event(
            db,
            source="admin",
            action="admin_access",
            status="failed",
            message="Administrator revocation rejected because self-revocation is not allowed",
            request_path=f"/api/admin/administrators/{admin_id}/revoke",
            http_status=409,
            details=f"chave={admin.chave}; revoked_by={current_admin.chave}",
            commit=True,
        )
        raise HTTPException(status_code=409, detail="Voce nao pode revogar seu proprio acesso.")

    total_admins = sum(
        1
        for row in db.execute(select(User).where(User.perfil != 0)).scalars().all()
        if user_has_admin_access(row)
    )
    if total_admins <= 1:
        log_event(
            db,
            source="admin",
            action="admin_access",
            status="failed",
            message="Administrator revocation rejected because the last active admin cannot be removed",
            request_path=f"/api/admin/administrators/{admin_id}/revoke",
            http_status=409,
            details=f"chave={admin.chave}; revoked_by={current_admin.chave}",
            commit=True,
        )
        raise HTTPException(status_code=409, detail="Nao e possivel revogar o unico administrador ativo do sistema.")

    admin.perfil = remove_profile_access(admin.perfil, ADMIN_ACCESS_DIGIT)
    log_event(
        db,
        source="admin",
        action="admin_access",
        status="removed",
        message="Administrator access revoked",
        request_path=f"/api/admin/administrators/{admin_id}/revoke",
        http_status=200,
        details=f"chave={admin.chave}; revoked_by={current_admin.chave}",
    )
    db.commit()
    notify_admin_views("admin", "event")
    return AdminActionResponse(ok=True, message="Administrador revogado com sucesso.")


@router.post("/administrators/{admin_id}/set-password", response_model=AdminActionResponse)
def set_administrator_password(
    admin_id: int,
    payload: AdminPasswordSetRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> AdminActionResponse:
    admin = db.get(User, admin_id)
    if admin is None or not user_has_admin_access(admin):
        log_event(
            db,
            source="admin",
            action="password",
            status="failed",
            message="Administrative password update failed because target admin was not found",
            request_path=f"/api/admin/administrators/{admin_id}/set-password",
            http_status=404,
            details=f"admin_id={admin_id}; updated_by={current_admin.chave}",
            commit=True,
        )
        raise HTTPException(status_code=404, detail="Administrador nao encontrado.")
    if admin.senha is not None:
        log_event(
            db,
            source="admin",
            action="password",
            status="failed",
            message="Administrative password update rejected because no reset is pending",
            request_path=f"/api/admin/administrators/{admin_id}/set-password",
            http_status=409,
            details=f"chave={admin.chave}; updated_by={current_admin.chave}",
            commit=True,
        )
        raise HTTPException(status_code=409, detail="Esse administrador nao possui recadastro de senha pendente.")

    admin.senha = hash_password(payload.nova_senha)
    log_event(
        db,
        source="admin",
        action="password",
        status="updated",
        message="Administrative password updated",
        request_path=f"/api/admin/administrators/{admin_id}/set-password",
        http_status=200,
        details=f"chave={admin.chave}; updated_by={current_admin.chave}",
    )
    db.commit()
    notify_admin_views("admin", "event")
    return AdminActionResponse(ok=True, message="Nova senha cadastrada com sucesso.")


@router.get("/checkin", response_model=list[UserRow], dependencies=[Depends(require_admin_session)])
def list_checkin(db: Session = Depends(get_db)) -> list[UserRow]:
    reference_time = now_sgt()
    if sync_user_inactivity(db, reference_time=reference_time):
        db.commit()
    return build_presence_rows(db, action="checkin", reference_time=reference_time)


@router.get("/checkout", response_model=list[UserRow], dependencies=[Depends(require_admin_session)])
def list_checkout(db: Session = Depends(get_db)) -> list[UserRow]:
    reference_time = now_sgt()
    if sync_user_inactivity(db, reference_time=reference_time):
        db.commit()
    return build_presence_rows(db, action="checkout", reference_time=reference_time)


@router.get("/missing-checkout", response_model=list[UserRow], dependencies=[Depends(require_admin_session)])
def list_missing_checkout(db: Session = Depends(get_db)) -> list[UserRow]:
    reference_time = now_sgt()
    if sync_user_inactivity(db, reference_time=reference_time):
        db.commit()
    return build_missing_checkout_rows(db, reference_time=reference_time)


@router.get("/inactive", response_model=list[InactiveUserRow], dependencies=[Depends(require_admin_session)])
def list_inactive(db: Session = Depends(get_db)) -> list[InactiveUserRow]:
    reference_time = now_sgt()
    if sync_user_inactivity(db, reference_time=reference_time):
        db.commit()
    return build_inactive_rows(db, reference_time=reference_time)


@router.get("/pending", response_model=list[PendingRow], dependencies=[Depends(require_admin_session)])
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


@router.get("/locations", response_model=AdminLocationsResponse, dependencies=[Depends(require_admin_session)])
def list_locations(db: Session = Depends(get_db)) -> AdminLocationsResponse:
    rows = db.execute(select(ManagedLocation).order_by(ManagedLocation.local, ManagedLocation.id)).scalars().all()
    return AdminLocationsResponse(
        items=[build_location_row(row) for row in rows],
        location_accuracy_threshold_meters=get_location_accuracy_threshold_meters(db),
    )


@router.post("/locations", response_model=AdminActionResponse, dependencies=[Depends(require_admin_session)])
def upsert_location(
    payload: AdminLocationUpsert,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> AdminActionResponse:
    location = db.get(ManagedLocation, payload.location_id) if payload.location_id is not None else None
    if payload.location_id is not None and location is None:
        raise HTTPException(status_code=404, detail="Localizacao nao encontrada.")

    conflicting_location = db.execute(
        select(ManagedLocation).where(ManagedLocation.local == payload.local)
    ).scalar_one_or_none()
    if conflicting_location is not None and (location is None or conflicting_location.id != location.id):
        raise HTTPException(status_code=409, detail="Ja existe uma localizacao cadastrada com esse nome.")

    timestamp = now_sgt()
    coordinates = [
        {"latitude": coordinate.latitude, "longitude": coordinate.longitude}
        for coordinate in (payload.coordinates or [])
    ]
    primary_coordinate = coordinates[0]
    coordinates_json = dump_location_coordinates(coordinates)
    created = False
    if location is None:
        location = ManagedLocation(
            local=payload.local,
            latitude=primary_coordinate["latitude"],
            longitude=primary_coordinate["longitude"],
            coordinates_json=coordinates_json,
            tolerance_meters=payload.tolerance_meters,
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(location)
        created = True
    else:
        location.local = payload.local
        location.latitude = primary_coordinate["latitude"]
        location.longitude = primary_coordinate["longitude"]
        location.coordinates_json = coordinates_json
        location.tolerance_meters = payload.tolerance_meters
        location.updated_at = timestamp

    coordinates_details = " | ".join(
        f"{coordinate['latitude']:.6f},{coordinate['longitude']:.6f}"
        for coordinate in coordinates
    )

    log_event(
        db,
        source="admin",
        action="location",
        status="created" if created else "updated",
        message="Location saved via admin",
        local=payload.local,
        request_path="/api/admin/locations",
        http_status=200,
        details=(
            f"updated_by={current_admin.chave}; coordinates={coordinates_details}; "
            f"tolerance_meters={payload.tolerance_meters}"
        ),
    )
    db.commit()
    notify_admin_views("location", "event")
    return AdminActionResponse(ok=True, message="Localizacao salva com sucesso.")


@router.post("/locations/settings", response_model=AdminLocationSettingsResponse, dependencies=[Depends(require_admin_session)])
def update_location_settings(
    payload: AdminLocationSettingsUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> AdminLocationSettingsResponse:
    previous_accuracy_threshold_meters = get_location_accuracy_threshold_meters(db)
    settings = upsert_location_settings(
        db,
        accuracy_threshold_meters=payload.location_accuracy_threshold_meters,
    )
    log_message = build_location_settings_log_message(
        previous_accuracy_threshold_meters=previous_accuracy_threshold_meters,
        current_accuracy_threshold_meters=settings.location_accuracy_threshold_meters,
    )
    log_event(
        db,
        source="admin",
        action="location_config",
        status="updated",
        message=log_message,
        request_path="/api/admin/locations/settings",
        http_status=200,
        details=(
            f"updated_by={current_admin.chave}; "
            f"previous_location_accuracy_threshold_meters={previous_accuracy_threshold_meters}; "
            f"location_accuracy_threshold_meters={settings.location_accuracy_threshold_meters}"
        ),
    )
    db.commit()
    notify_admin_views("location", "event")
    return AdminLocationSettingsResponse(
        ok=True,
        message="Configuracoes de localizacao salvas com sucesso.",
        location_accuracy_threshold_meters=settings.location_accuracy_threshold_meters,
    )


@router.delete("/locations/{location_id}", response_model=AdminActionResponse, dependencies=[Depends(require_admin_session)])
def remove_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> AdminActionResponse:
    location = db.get(ManagedLocation, location_id)
    if location is None:
        log_event(
            db,
            source="admin",
            action="location",
            status="failed",
            message="Location not found for removal",
            request_path=f"/api/admin/locations/{location_id}",
            http_status=404,
            details=f"updated_by={current_admin.chave}; location_id={location_id}",
            commit=True,
        )
        raise HTTPException(status_code=404, detail="Localizacao nao encontrada.")

    location_name = location.local
    db.delete(location)
    log_event(
        db,
        source="admin",
        action="location",
        status="removed",
        message="Location removed via admin",
        local=location_name,
        request_path=f"/api/admin/locations/{location_id}",
        http_status=200,
        details=f"updated_by={current_admin.chave}; location_id={location_id}",
    )
    db.commit()
    notify_admin_views("location", "event")
    return AdminActionResponse(ok=True, message="Localizacao removida com sucesso.")


@router.get("/users", response_model=list[AdminUserListRow], dependencies=[Depends(require_admin_session)])
def list_users(db: Session = Depends(get_db)) -> list[AdminUserListRow]:
    rows = db.execute(select(User).order_by(User.nome, User.rfid)).scalars().all()
    return [
        AdminUserListRow(
            id=r.id,
            rfid=r.rfid,
            nome=r.nome,
            chave=r.chave,
            perfil=r.perfil,
            projeto=r.projeto,
            workplace=r.workplace,
            placa=r.placa,
            end_rua=r.end_rua,
            zip=r.zip,
            cargo=r.cargo,
            email=r.email,
        )
        for r in rows
    ]


@router.post("/users", dependencies=[Depends(require_admin_session)])
def upsert_user(
    payload: AdminUserUpsert,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> dict:
    payload.projeto = ensure_known_project(db, payload.projeto)
    payload_fields = set(getattr(payload, "model_fields_set", set()))
    placa_was_provided = "placa" in payload_fields
    user = None
    linked_existing_user = False
    if payload.user_id is not None:
        user = db.get(User, payload.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
    elif payload.rfid:
        user = find_user_by_rfid(db, payload.rfid)
        if user is None:
            user = find_user_by_chave(db, payload.chave)
            if user is not None and user.rfid is None:
                linked_existing_user = True

    conflicting_user = find_user_by_chave(db, payload.chave)
    if conflicting_user is not None and (user is None or conflicting_user.id != user.id):
        if user is None and conflicting_user.rfid is None and payload.rfid is not None:
            user = conflicting_user
            linked_existing_user = True
        else:
            raise HTTPException(status_code=409, detail="Ja existe um usuario cadastrado com essa chave")

    if payload.rfid is not None:
        conflicting_rfid_user = find_user_by_rfid(db, payload.rfid)
        if conflicting_rfid_user is not None and (user is None or conflicting_rfid_user.id != user.id):
            raise HTTPException(status_code=409, detail="Ja existe um usuario cadastrado com esse RFID")

    if placa_was_provided and payload.placa is not None:
        vehicle = db.execute(select(Vehicle).where(Vehicle.placa == payload.placa)).scalar_one_or_none()
        if vehicle is None:
            raise HTTPException(status_code=404, detail="Veiculo nao encontrado para a placa informada")

    if payload.workplace is not None:
        workplace = db.execute(select(Workplace).where(Workplace.workplace == payload.workplace)).scalar_one_or_none()
        if workplace is None:
            raise HTTPException(status_code=404, detail="Workplace nao encontrado para o nome informado")

    if user is not None and user_has_admin_access(user) and not user_profile_has_access(payload.perfil, ADMIN_ACCESS_DIGIT):
        total_admins = sum(
            1
            for row in db.execute(select(User).where(User.perfil != 0)).scalars().all()
            if user_has_admin_access(row)
        )
        if total_admins <= 1:
            raise HTTPException(status_code=409, detail="Nao e possivel remover o unico administrador ativo do sistema.")

    if user:
        previous_key = user.chave
        user.nome = payload.nome
        user.chave = payload.chave
        user.perfil = normalize_user_profile(payload.perfil)
        user.projeto = payload.projeto
        user.workplace = payload.workplace
        user.rfid = payload.rfid
        if placa_was_provided:
            user.placa = payload.placa
        user.end_rua = payload.end_rua
        user.zip = payload.zip
        user.cargo = payload.cargo
        user.email = payload.email
        if previous_key != user.chave:
            db.execute(
                update(UserSyncEvent)
                .where(UserSyncEvent.user_id == user.id)
                .values(chave=user.chave)
            )
            db.execute(
                update(CheckingHistory)
                .where(CheckingHistory.chave == previous_key)
                .values(chave=user.chave)
            )
    else:
        if payload.rfid is None:
            raise HTTPException(status_code=400, detail="RFID is required for new users")
        user = User(
            rfid=payload.rfid,
            nome=payload.nome,
            chave=payload.chave,
            perfil=normalize_user_profile(payload.perfil),
            projeto=payload.projeto,
            workplace=payload.workplace,
            placa=payload.placa,
            end_rua=payload.end_rua,
            zip=payload.zip,
            cargo=payload.cargo,
            email=payload.email,
            local=None,
            checkin=None,
            time=None,
            last_active_at=now_sgt(),
            inactivity_days=0,
        )
        db.add(user)

    pending = None
    if payload.rfid is not None:
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
        details=(
            f"updated_by={current_admin.chave}; chave={payload.chave}; "
            f"nome={payload.nome}; perfil={normalize_user_profile(payload.perfil)}; linked_existing_user={linked_existing_user}; "
            f"placa={(payload.placa if placa_was_provided else user.placa) or '-'}"
        ),
    )
    db.commit()
    notify_admin_views("register", "event")

    return {
        "ok": True,
        "rfid": user.rfid,
        "user_id": user.id,
        "linked_existing_user": linked_existing_user,
    }


@router.delete("/pending/{pending_id}", dependencies=[Depends(require_admin_session)])
def remove_pending(
    pending_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> dict:
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
            details=f"updated_by={current_admin.chave}; pending_id={pending_id}",
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
        details=f"updated_by={current_admin.chave}; pending_id={pending_id}",
    )
    db.commit()
    notify_admin_views("pending", "event")
    return {"ok": True, "id": pending_id}


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin_session)])
def remove_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> dict:
    user = db.get(User, user_id)
    if user is None:
        log_event(
            db,
            source="admin",
            action="register",
            status="failed",
            message="User not found for removal",
            request_path=f"/api/admin/users/{user_id}",
            http_status=404,
            details=f"updated_by={current_admin.chave}; user_id={user_id}",
            commit=True,
        )
        raise HTTPException(status_code=404, detail="User not found")

    if user_has_admin_access(user):
        total_admins = sum(
            1
            for row in db.execute(select(User).where(User.perfil != 0)).scalars().all()
            if user_has_admin_access(row)
        )
        if total_admins <= 1:
            raise HTTPException(status_code=409, detail="Nao e possivel remover o unico administrador ativo do sistema.")

    user_rfid = user.rfid
    user_key = user.chave
    pending = None
    if user_rfid is not None:
        pending = db.execute(select(PendingRegistration).where(PendingRegistration.rfid == user_rfid)).scalar_one_or_none()
    if pending is not None:
        db.delete(pending)

    db.execute(delete(UserSyncEvent).where(UserSyncEvent.user_id == user.id))
    db.delete(user)
    log_event(
        db,
        source="admin",
        action="register",
        status="removed",
        message="User removed via admin",
        rfid=user_rfid,
        request_path=f"/api/admin/users/{user_id}",
        http_status=200,
        details=(
            f"updated_by={current_admin.chave}; chave={user_key}; user_id={user_id}; "
            f"pending_removed={pending is not None}"
        ),
    )
    db.commit()
    notify_admin_views("register", "event")
    return {"ok": True, "user_id": user_id}


@router.post("/users/{user_id}/reset-password", response_model=AdminActionResponse)
def reset_user_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> AdminActionResponse:
    user = db.get(User, user_id)
    if user is None:
        log_event(
            db,
            source="admin",
            action="password",
            status="failed",
            message="User password reset failed because target user was not found",
            request_path=f"/api/admin/users/{user_id}/reset-password",
            http_status=404,
            details=f"updated_by={current_admin.chave}; user_id={user_id}",
            commit=True,
        )
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")

    had_password = bool(user.senha)
    if had_password:
        user.senha = None

    log_event(
        db,
        source="admin",
        action="password",
        status="removed" if had_password else "noop",
        message="Web user password removed via admin" if had_password else "Web user password reset requested via admin but user already had no password",
        request_path=f"/api/admin/users/{user_id}/reset-password",
        http_status=200,
        details=(
            f"updated_by={current_admin.chave}; chave={user.chave}; "
            f"user_id={user_id}; had_password={had_password}"
        ),
    )
    db.commit()
    notify_admin_views("register", "event")
    if had_password:
        return AdminActionResponse(
            ok=True,
            message="Senha removida com sucesso. O usuario podera cadastrar uma nova senha.",
        )
    return AdminActionResponse(
        ok=True,
        message="Esse usuario ja esta sem senha cadastrada e ja pode cadastrar uma nova senha.",
    )


@router.get("/events", response_model=list[EventRow], dependencies=[Depends(require_admin_session)])
def list_events(db: Session = Depends(get_db)) -> list[EventRow]:
    rows = db.execute(
        select(CheckEvent)
        .where(CheckEvent.action != "event_archive")
        .order_by(desc(CheckEvent.id))
        .limit(200)
    ).scalars().all()
    return build_event_row_payload(rows, db)


@router.get(
    "/database-events",
    response_model=DatabaseEventListResponse,
    dependencies=[Depends(require_admin_session)],
)
def list_database_events(
    db: Session = Depends(get_db),
    action: str | None = Query(default=None),
    project: str | None = Query(default=None),
    source: str | None = Query(default=None),
    status: str | None = Query(default=None),
    chave: str | None = Query(default=None, min_length=1, max_length=4),
    rfid: str | None = Query(default=None, min_length=1, max_length=64),
    search: str | None = Query(default=None, min_length=1, max_length=120),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    sort_by: str = Query(default=DATABASE_EVENT_DEFAULT_SORT_BY),
    sort_direction: str = Query(default=DATABASE_EVENT_DEFAULT_SORT_DIRECTION),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DATABASE_EVENT_PAGE_SIZE, ge=1, le=200),
) -> DatabaseEventListResponse:
    normalized_action = str(action or "").strip().lower() or None
    if normalized_action and normalized_action not in DATABASE_EVENT_ACTIONS:
        raise HTTPException(status_code=400, detail="Acao invalida para a consulta de eventos do banco de dados.")

    normalized_project = str(project or "").strip().upper() or None
    normalized_source = str(source or "").strip().lower() or None
    normalized_status = str(status or "").strip().lower() or None
    normalized_key = str(chave or "").strip().upper() or None
    normalized_rfid = str(rfid or "").strip() or None
    normalized_search = str(search or "").strip().lower() or None
    normalized_sort_by = str(sort_by or "").strip().lower() or DATABASE_EVENT_DEFAULT_SORT_BY
    normalized_sort_direction = str(sort_direction or "").strip().lower() or DATABASE_EVENT_DEFAULT_SORT_DIRECTION

    if normalized_sort_by not in DATABASE_EVENT_SORTABLE_FIELDS:
        raise HTTPException(status_code=400, detail="Coluna invalida para ordenacao de eventos.")
    if normalized_sort_direction not in DATABASE_EVENT_SORT_DIRECTIONS:
        raise HTTPException(status_code=400, detail="Direcao invalida para ordenacao de eventos.")

    filter_options = build_database_event_filter_options(db)

    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=400, detail="Intervalo de datas invalido para a consulta de eventos.")

    query = select(CheckEvent).where(CheckEvent.action.in_(DATABASE_EVENT_ACTIONS))

    if normalized_action:
        query = query.where(CheckEvent.action == normalized_action)
    if normalized_project:
        query = query.where(CheckEvent.project == normalized_project)
    if normalized_source:
        query = query.where(func.lower(CheckEvent.source) == normalized_source)
    if normalized_status:
        query = query.where(func.lower(CheckEvent.status) == normalized_status)
    if normalized_rfid:
        query = query.where(CheckEvent.rfid == normalized_rfid)
    if normalized_search:
        like_pattern = f"%{normalized_search}%"
        query = query.where(
            or_(
                func.lower(func.coalesce(CheckEvent.rfid, "")).like(like_pattern),
                func.lower(func.coalesce(CheckEvent.source, "")).like(like_pattern),
                func.lower(func.coalesce(CheckEvent.device_id, "")).like(like_pattern),
                func.lower(func.coalesce(CheckEvent.local, "")).like(like_pattern),
                func.lower(func.coalesce(CheckEvent.status, "")).like(like_pattern),
                func.lower(func.coalesce(CheckEvent.message, "")).like(like_pattern),
                func.lower(func.coalesce(CheckEvent.details, "")).like(like_pattern),
                func.lower(func.coalesce(CheckEvent.project, "")).like(like_pattern),
                func.lower(func.coalesce(CheckEvent.request_path, "")).like(like_pattern),
            )
        )
    if from_date:
        from_datetime = datetime.combine(from_date, dt_time.min, tzinfo=now_sgt().tzinfo)
        query = query.where(CheckEvent.event_time >= from_datetime)
    if to_date:
        to_datetime = datetime.combine(to_date + timedelta(days=1), dt_time.min, tzinfo=now_sgt().tzinfo)
        query = query.where(CheckEvent.event_time < to_datetime)

    if normalized_key:
        key_match = db.execute(select(User.rfid).where(User.chave == normalized_key, User.rfid.is_not(None))).scalars().all()
        details_pattern = f"%{normalized_key}%"
        key_conditions = [func.upper(func.coalesce(CheckEvent.details, "")).like(details_pattern)]
        if key_match:
            key_conditions.append(CheckEvent.rfid.in_(key_match))
        query = query.where(or_(*key_conditions))

    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar_one()
    total_pages = max(1, (total + page_size - 1) // page_size)
    current_page = min(page, total_pages)

    if normalized_sort_by == "chave":
        rows = db.execute(query).scalars().all()
        sorted_items = sort_database_event_payload(
            build_event_row_payload(rows, db),
            sort_by=normalized_sort_by,
            sort_direction=normalized_sort_direction,
        )
        offset = (current_page - 1) * page_size
        paginated_items = sorted_items[offset: offset + page_size]
        return DatabaseEventListResponse(
            items=paginated_items,
            total=total,
            page=current_page,
            page_size=page_size,
            total_pages=total_pages,
            filter_options=filter_options,
        )

    sort_expression = DATABASE_EVENT_SQL_SORT_FIELDS[normalized_sort_by]
    sort_function = asc if normalized_sort_direction == "asc" else desc
    rows = db.execute(
        query
        .order_by(sort_function(sort_expression), sort_function(CheckEvent.id))
        .offset((current_page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    return DatabaseEventListResponse(
        items=build_event_row_payload(rows, db),
        total=total,
        page=current_page,
        page_size=page_size,
        total_pages=total_pages,
        filter_options=filter_options,
    )


@router.post("/events/archive", response_model=EventArchiveCreateResponse, dependencies=[Depends(require_admin_session)])
def archive_events(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> EventArchiveCreateResponse:
    current_rows = db.execute(
        select(CheckEvent)
        .order_by(CheckEvent.event_time, CheckEvent.id)
    ).scalars().all()
    rows = [row for row in current_rows if row.action != "event_archive"]
    archive = create_event_archive(rows)
    pruned_archive_rows = len(current_rows) - len(rows)

    if current_rows:
        db.execute(delete(CheckEvent))
        db.commit()

    if archive is not None:
        log_event(
            db,
            source="admin",
            action="event_archive",
            status="created",
            message="Event log archive created",
            request_path="/api/admin/events/archive",
            http_status=200,
            details=(
                f"file_name={archive.file_name}; period={archive.period}; "
                f"record_count={archive.record_count}; pruned_archive_rows={pruned_archive_rows}; "
                f"created_by={current_admin.chave}"
            )[:1000],
            commit=True,
        )
    else:
        log_event(
            db,
            source="admin",
            action="event_archive",
            status="noop",
            message="Event log archive requested but there were no current events to archive",
            request_path="/api/admin/events/archive",
            http_status=200,
            details=f"pruned_archive_rows={pruned_archive_rows}; created_by={current_admin.chave}",
            commit=True,
        )

    archives_page = list_event_archives_page()

    return EventArchiveCreateResponse(
        created=archive is not None,
        cleared_count=len(rows) if archive is not None else 0,
        archive=EventArchiveRow(**archive.__dict__) if archive is not None else None,
        archives=EventArchiveListResponse(
            items=[EventArchiveRow(**item.__dict__) for item in archives_page.items],
            total=archives_page.total,
            total_size_bytes=archives_page.total_size_bytes,
            page=archives_page.page,
            page_size=archives_page.page_size,
            total_pages=archives_page.total_pages,
            query=archives_page.query,
        ),
    )


@router.get("/events/archives", response_model=EventArchiveListResponse, dependencies=[Depends(require_admin_session)])
def get_event_archives(
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=100),
) -> EventArchiveListResponse:
    archives_page = list_event_archives_page(query=q, page=page, page_size=page_size)
    return EventArchiveListResponse(
        items=[EventArchiveRow(**item.__dict__) for item in archives_page.items],
        total=archives_page.total,
        total_size_bytes=archives_page.total_size_bytes,
        page=archives_page.page,
        page_size=archives_page.page_size,
        total_pages=archives_page.total_pages,
        query=archives_page.query,
    )


@router.get("/events/archives/download-all", dependencies=[Depends(require_admin_session)])
def download_all_event_archives(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> Response:
    try:
        file_name, payload = build_event_archives_zip()
    except FileNotFoundError as exc:
        log_event(
            db,
            source="admin",
            action="event_archive",
            status="failed",
            message="Download of all archived event logs failed because there are no archives",
            request_path="/api/admin/events/archives/download-all",
            http_status=404,
            details=f"downloaded_by={current_admin.chave}",
            commit=True,
        )
        raise HTTPException(status_code=404, detail="No archived event logs found") from exc

    log_event(
        db,
        source="admin",
        action="event_archive",
        status="downloaded",
        message="All archived event logs downloaded as zip",
        request_path="/api/admin/events/archives/download-all",
        http_status=200,
        details=f"file_name={file_name}; downloaded_by={current_admin.chave}",
        commit=True,
    )

    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/events/archives/{file_name}", dependencies=[Depends(require_admin_session)])
def download_event_archive(
    file_name: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> FileResponse:
    try:
        archive_path = get_event_archive_path(file_name)
    except FileNotFoundError as exc:
        log_event(
            db,
            source="admin",
            action="event_archive",
            status="failed",
            message="Archived event log download failed because file was not found",
            request_path=f"/api/admin/events/archives/{file_name}",
            http_status=404,
            details=f"file_name={file_name}; downloaded_by={current_admin.chave}",
            commit=True,
        )
        raise HTTPException(status_code=404, detail="Archived event log not found") from exc

    log_event(
        db,
        source="admin",
        action="event_archive",
        status="downloaded",
        message="Archived event log downloaded",
        request_path=f"/api/admin/events/archives/{file_name}",
        http_status=200,
        details=f"file_name={file_name}; downloaded_by={current_admin.chave}",
        commit=True,
    )

    return FileResponse(path=archive_path, media_type="text/csv", filename=archive_path.name)


@router.delete("/events/archives/{file_name}", dependencies=[Depends(require_admin_session)])
def remove_event_archive(
    file_name: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_session),
) -> dict:
    try:
        delete_event_archive(file_name)
    except FileNotFoundError as exc:
        log_event(
            db,
            source="admin",
            action="event_archive",
            status="failed",
            message="Archived event log removal failed because file was not found",
            request_path=f"/api/admin/events/archives/{file_name}",
            http_status=404,
            details=f"file_name={file_name}; removed_by={current_admin.chave}",
            commit=True,
        )
        raise HTTPException(status_code=404, detail="Archived event log not found") from exc

    log_event(
        db,
        source="admin",
        action="event_archive",
        status="removed",
        message="Archived event log removed",
        request_path=f"/api/admin/events/archives/{file_name}",
        http_status=200,
        details=f"file_name={file_name}; removed_by={current_admin.chave}",
        commit=True,
    )

    return {"ok": True, "file_name": file_name}
