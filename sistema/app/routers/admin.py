import asyncio
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AdminAccessRequest, AdminUser, CheckEvent, ManagedLocation, PendingRegistration, User, UserSyncEvent
from ..schemas import (
    AdminAccessRequestCreate,
    AdminActionResponse,
    AdminIdentity,
    AdminLocationsResponse,
    AdminLocationSettingsResponse,
    AdminLocationSettingsUpdate,
    AdminLocationUpsert,
    AdminLoginRequest,
    AdminManagementRow,
    AdminPasswordResetRequest,
    AdminPasswordSetRequest,
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
    get_authenticated_admin_from_session,
    hash_password,
    normalize_admin_key,
    require_admin_session,
    require_admin_stream_session,
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
from ..services.location_settings import get_location_update_interval_seconds, upsert_location_update_interval_seconds
from ..services.time_utils import now_sgt
from ..services.user_activity import (
    calculate_inactivity_days,
    has_missing_checkout_since_midnight,
    is_user_inactive,
    sync_user_inactivity,
)
from ..services.user_sync import find_user_by_chave, find_user_by_rfid, resolve_latest_user_activity

router = APIRouter(prefix="/api/admin", tags=["admin"])


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


def build_admin_identity(admin: AdminUser) -> AdminIdentity:
    return AdminIdentity(id=admin.id, chave=admin.chave, nome_completo=admin.nome_completo)


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


def list_admin_rows(db: Session) -> list[AdminManagementRow]:
    admins = db.execute(select(AdminUser).order_by(AdminUser.nome_completo, AdminUser.chave)).scalars().all()
    requests = db.execute(select(AdminAccessRequest).order_by(AdminAccessRequest.requested_at.desc())).scalars().all()

    rows: list[AdminManagementRow] = []
    for admin in admins:
        status = "password_reset_requested" if admin.requires_password_reset else "active"
        status_label = "Recadastro de Senha Pendente" if admin.requires_password_reset else "Administrador Ativo"
        rows.append(
            AdminManagementRow(
                id=admin.id,
                row_type="admin",
                chave=admin.chave,
                nome=admin.nome_completo,
                status=status,
                status_label=status_label,
                can_revoke=not admin.requires_password_reset,
                can_approve=False,
                can_reject=False,
                can_set_password=admin.requires_password_reset,
            )
        )

    for request_row in requests:
        rows.append(
            AdminManagementRow(
                id=request_row.id,
                row_type="request",
                chave=request_row.chave,
                nome=request_row.nome_completo,
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
    admin = db.execute(select(AdminUser).where(AdminUser.chave == key)).scalar_one_or_none()

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

    if admin.password_hash is None or admin.requires_password_reset:
        log_event(
            db,
            source="admin",
            action="login",
            status="blocked",
            message="Administrative login blocked due to pending password reset",
            request_path="/api/admin/auth/login",
            http_status=403,
            details=f"chave={admin.chave}",
            commit=True,
        )
        raise HTTPException(
            status_code=403,
            detail="Sua senha foi removida. Solicite a outro administrador o recadastro da senha.",
        )

    if not verify_password(payload.senha, admin.password_hash):
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

    request.session.clear()
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
    request.session.clear()
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
    existing_admin = db.execute(select(AdminUser).where(AdminUser.chave == key)).scalar_one_or_none()
    if existing_admin is not None:
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
    admin = db.execute(select(AdminUser).where(AdminUser.chave == key)).scalar_one_or_none()
    if admin is None:
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
    if admin.requires_password_reset:
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

    admin.password_hash = None
    admin.requires_password_reset = True
    admin.password_reset_requested_at = now_sgt()
    admin.updated_at = now_sgt()
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


@router.post(
    "/administrators/requests/{request_id}/approve",
    response_model=AdminActionResponse,
)
def approve_administrator_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin_session),
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

    existing_admin = db.execute(select(AdminUser).where(AdminUser.chave == access_request.chave)).scalar_one_or_none()
    if existing_admin is not None:
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
    db.add(
        AdminUser(
            chave=access_request.chave,
            nome_completo=access_request.nome_completo,
            password_hash=access_request.password_hash,
            requires_password_reset=False,
            approved_by_admin_id=current_admin.id,
            approved_at=timestamp,
            password_reset_requested_at=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
    )
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
    current_admin: AdminUser = Depends(require_admin_session),
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
    current_admin: AdminUser = Depends(require_admin_session),
) -> AdminActionResponse:
    admin = db.get(AdminUser, admin_id)
    if admin is None:
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

    total_admins = db.execute(select(func.count(AdminUser.id))).scalar_one()
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
    db.delete(admin)
    db.commit()
    notify_admin_views("admin", "event")
    return AdminActionResponse(ok=True, message="Administrador revogado com sucesso.")


@router.post("/administrators/{admin_id}/set-password", response_model=AdminActionResponse)
def set_administrator_password(
    admin_id: int,
    payload: AdminPasswordSetRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin_session),
) -> AdminActionResponse:
    admin = db.get(AdminUser, admin_id)
    if admin is None:
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
    if not admin.requires_password_reset:
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

    admin.password_hash = hash_password(payload.nova_senha)
    admin.requires_password_reset = False
    admin.password_reset_requested_at = None
    admin.updated_at = now_sgt()
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
        location_update_interval_seconds=get_location_update_interval_seconds(db),
    )


@router.post("/locations", response_model=AdminActionResponse, dependencies=[Depends(require_admin_session)])
def upsert_location(payload: AdminLocationUpsert, db: Session = Depends(get_db)) -> AdminActionResponse:
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
        details=f"coordinates={coordinates_details}; tolerance_meters={payload.tolerance_meters}",
    )
    db.commit()
    notify_admin_views("location", "event")
    return AdminActionResponse(ok=True, message="Localizacao salva com sucesso.")


@router.post("/locations/settings", response_model=AdminLocationSettingsResponse, dependencies=[Depends(require_admin_session)])
def update_location_settings(payload: AdminLocationSettingsUpdate, db: Session = Depends(get_db)) -> AdminLocationSettingsResponse:
    settings = upsert_location_update_interval_seconds(
        db,
        seconds=payload.location_update_interval_seconds,
    )
    log_event(
        db,
        source="admin",
        action="location_settings",
        status="updated",
        message="Location update interval saved via admin",
        request_path="/api/admin/locations/settings",
        http_status=200,
        details=f"location_update_interval_seconds={settings.location_update_interval_seconds}",
    )
    db.commit()
    notify_admin_views("location", "event")
    return AdminLocationSettingsResponse(
        ok=True,
        message="Tempo de atualizacao da localizacao salvo com sucesso.",
        location_update_interval_seconds=settings.location_update_interval_seconds,
    )


@router.delete("/locations/{location_id}", response_model=AdminActionResponse, dependencies=[Depends(require_admin_session)])
def remove_location(location_id: int, db: Session = Depends(get_db)) -> AdminActionResponse:
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
            details=f"location_id={location_id}",
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
        details=f"location_id={location_id}",
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
            projeto=r.projeto,
        )
        for r in rows
    ]


@router.post("/users", dependencies=[Depends(require_admin_session)])
def upsert_user(payload: AdminUserUpsert, db: Session = Depends(get_db)) -> dict:
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

    if user:
        if payload.rfid is not None and user.rfid not in {None, payload.rfid}:
            raise HTTPException(status_code=409, detail="Este usuario ja possui outro RFID vinculado")
        user.nome = payload.nome
        user.chave = payload.chave
        user.projeto = payload.projeto
        if payload.rfid is not None:
            user.rfid = payload.rfid
    else:
        if payload.rfid is None:
            raise HTTPException(status_code=400, detail="RFID is required for new users")
        user = User(
            rfid=payload.rfid,
            nome=payload.nome,
            chave=payload.chave,
            projeto=payload.projeto,
            local=None,
            checkin=None,
            time=None,
            last_active_at=now_sgt(),
            inactivity_days=0,
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
    notify_admin_views("register", "event")

    return {
        "ok": True,
        "rfid": payload.rfid,
        "user_id": user.id,
        "linked_existing_user": linked_existing_user,
    }


@router.delete("/pending/{pending_id}", dependencies=[Depends(require_admin_session)])
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
    notify_admin_views("pending", "event")
    return {"ok": True, "id": pending_id}


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin_session)])
def remove_user(user_id: int, db: Session = Depends(get_db)) -> dict:
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
            details=f"user_id={user_id}",
            commit=True,
        )
        raise HTTPException(status_code=404, detail="User not found")

    pending = None
    if user.rfid is not None:
        pending = db.execute(select(PendingRegistration).where(PendingRegistration.rfid == user.rfid)).scalar_one_or_none()
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
        rfid=user.rfid,
        request_path=f"/api/admin/users/{user_id}",
        http_status=200,
        details=f"user_id={user_id}; pending_removed={pending is not None}",
    )
    db.commit()
    notify_admin_views("register", "event")
    return {"ok": True, "user_id": user_id}


@router.get("/events", response_model=list[EventRow], dependencies=[Depends(require_admin_session)])
def list_events(db: Session = Depends(get_db)) -> list[EventRow]:
    rows = db.execute(
        select(CheckEvent)
        .where(CheckEvent.action != "event_archive")
        .order_by(desc(CheckEvent.id))
        .limit(200)
    ).scalars().all()
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
            ontime=r.ontime,
            request_path=r.request_path,
            http_status=r.http_status,
            retry_count=r.retry_count,
            event_time=r.event_time,
        )
        for r in rows
    ]


@router.post("/events/archive", response_model=EventArchiveCreateResponse, dependencies=[Depends(require_admin_session)])
def archive_events(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin_session),
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
    current_admin: AdminUser = Depends(require_admin_session),
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
    current_admin: AdminUser = Depends(require_admin_session),
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
    current_admin: AdminUser = Depends(require_admin_session),
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
