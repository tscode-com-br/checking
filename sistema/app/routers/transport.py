from __future__ import annotations

import asyncio
import json
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import TransportRequest, User, Vehicle, Workplace
from ..schemas import (
    AdminActionResponse,
    TransportAssignmentUpsert,
    TransportAuthVerifyRequest,
    TransportDateSettingsResponse,
    TransportDateSettingsUpdateRequest,
    TransportDashboardResponse,
    TransportIdentity,
    TransportSettingsResponse,
    TransportSettingsUpdateRequest,
    TransportSessionResponse,
    TransportRequestReject,
    TransportVehicleCreate,
    TransportWorkplaceUpsert,
    WorkplaceRow,
)
from ..services.admin_auth import (
    clear_transport_session,
    get_authenticated_transport_user_from_session,
    normalize_admin_key,
    require_transport_session,
    user_has_transport_access,
    verify_password,
)
from ..services.admin_updates import admin_updates_broker, notify_admin_data_changed, notify_transport_data_changed
from ..services.location_settings import (
    get_transport_last_update_time,
    get_transport_vehicle_default_seat_counts,
    get_transport_work_to_home_time,
    upsert_transport_last_update_time,
    upsert_transport_vehicle_default_seat_counts,
    upsert_transport_work_to_home_time,
    upsert_transport_work_to_home_time_for_date,
)
from ..services.time_utils import now_sgt
from ..services.transport import (
    build_transport_dashboard,
    create_transport_vehicle_registration,
    delete_transport_vehicle_registration,
    find_transport_vehicle_schedule,
    list_workplaces,
    reject_transport_request_and_assignments,
    request_applies_to_date,
    upsert_transport_assignment_with_persistence,
)
from ..services.user_sync import find_user_by_chave


router = APIRouter(prefix="/api/transport", tags=["transport"])


def build_transport_identity(user: User) -> TransportIdentity:
    return TransportIdentity(id=user.id, chave=user.chave, nome_completo=user.nome, perfil=user.perfil)


def encode_sse(payload: dict[str, str]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.get("/auth/session", response_model=TransportSessionResponse)
def transport_session(request: Request, db: Session = Depends(get_db)) -> TransportSessionResponse:
    transport_user = get_authenticated_transport_user_from_session(request, db)
    if transport_user is None:
        return TransportSessionResponse(authenticated=False)
    return TransportSessionResponse(authenticated=True, user=build_transport_identity(transport_user))


@router.post("/auth/verify", response_model=TransportSessionResponse)
def verify_transport_access(
    payload: TransportAuthVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TransportSessionResponse:
    key = normalize_admin_key(payload.chave)
    transport_user = db.execute(select(User).where(User.chave == key)).scalar_one_or_none()

    if transport_user is None or transport_user.senha is None:
        clear_transport_session(request)
        return TransportSessionResponse(authenticated=False, message="Invalid key or password.")
    if not user_has_transport_access(transport_user):
        clear_transport_session(request)
        return TransportSessionResponse(authenticated=False, message="This user does not have transport access.")
    if not verify_password(payload.senha, transport_user.senha):
        clear_transport_session(request)
        return TransportSessionResponse(authenticated=False, message="Invalid key or password.")

    request.session["transport_user_id"] = transport_user.id
    return TransportSessionResponse(
        authenticated=True,
        user=build_transport_identity(transport_user),
        message="Transport access granted.",
    )


@router.post("/auth/logout", response_model=AdminActionResponse)
def transport_logout(request: Request) -> AdminActionResponse:
    clear_transport_session(request)
    return AdminActionResponse(ok=True, message="Transport session closed.")


@router.get("/stream", dependencies=[Depends(require_transport_session)])
async def stream_transport_updates(request: Request) -> StreamingResponse:
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


@router.get("/dashboard", response_model=TransportDashboardResponse, dependencies=[Depends(require_transport_session)])
def get_transport_dashboard(
    service_date: date | None = Query(default=None),
    route_kind: Literal["home_to_work", "work_to_home"] = Query(default="home_to_work"),
    db: Session = Depends(get_db),
) -> TransportDashboardResponse:
    resolved_date = service_date or now_sgt().date()
    return build_transport_dashboard(db, service_date=resolved_date, route_kind=route_kind)


@router.get("/settings", response_model=TransportSettingsResponse, dependencies=[Depends(require_transport_session)])
def get_transport_settings(db: Session = Depends(get_db)) -> TransportSettingsResponse:
    default_seat_counts = get_transport_vehicle_default_seat_counts(db)
    return TransportSettingsResponse(
        work_to_home_time=get_transport_work_to_home_time(db),
        last_update_time=get_transport_last_update_time(db),
        default_car_seats=default_seat_counts["default_car_seats"],
        default_minivan_seats=default_seat_counts["default_minivan_seats"],
        default_van_seats=default_seat_counts["default_van_seats"],
        default_bus_seats=default_seat_counts["default_bus_seats"],
        default_tolerance_minutes=default_seat_counts["default_tolerance_minutes"],
    )


@router.put("/settings", response_model=TransportSettingsResponse, dependencies=[Depends(require_transport_session)])
def update_transport_settings(
    payload: TransportSettingsUpdateRequest,
    db: Session = Depends(get_db),
) -> TransportSettingsResponse:
    settings_row = upsert_transport_work_to_home_time(db, work_to_home_time=payload.work_to_home_time)
    upsert_transport_last_update_time(db, last_update_time=payload.last_update_time)
    upsert_transport_vehicle_default_seat_counts(
        db,
        default_car_seats=payload.default_car_seats,
        default_minivan_seats=payload.default_minivan_seats,
        default_van_seats=payload.default_van_seats,
        default_bus_seats=payload.default_bus_seats,
        default_tolerance_minutes=payload.default_tolerance_minutes,
    )
    db.commit()
    return TransportSettingsResponse(
        work_to_home_time=settings_row.transport_work_to_home_time,
        last_update_time=settings_row.transport_last_update_time,
        default_car_seats=settings_row.transport_default_car_seats,
        default_minivan_seats=settings_row.transport_default_minivan_seats,
        default_van_seats=settings_row.transport_default_van_seats,
        default_bus_seats=settings_row.transport_default_bus_seats,
        default_tolerance_minutes=settings_row.transport_default_tolerance_minutes,
    )


@router.put("/date-settings", response_model=TransportDateSettingsResponse, dependencies=[Depends(require_transport_session)])
def update_transport_date_settings(
    payload: TransportDateSettingsUpdateRequest,
    db: Session = Depends(get_db),
) -> TransportDateSettingsResponse:
    daily_setting = upsert_transport_work_to_home_time_for_date(
        db,
        service_date=payload.service_date,
        work_to_home_time=payload.work_to_home_time,
    )
    db.commit()
    notify_transport_data_changed("settings")
    return TransportDateSettingsResponse(
        service_date=daily_setting.service_date,
        work_to_home_time=daily_setting.work_to_home_time,
    )


@router.get("/workplaces", response_model=list[WorkplaceRow], dependencies=[Depends(require_transport_session)])
def get_transport_workplaces(db: Session = Depends(get_db)) -> list[WorkplaceRow]:
    return list_workplaces(db)


@router.post("/workplaces", response_model=WorkplaceRow, dependencies=[Depends(require_transport_session)])
def create_transport_workplace(
    payload: TransportWorkplaceUpsert,
    db: Session = Depends(get_db),
) -> WorkplaceRow:
    existing = db.execute(select(Workplace).where(Workplace.workplace == payload.workplace)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A workplace with this name already exists.")

    workplace = Workplace(
        workplace=payload.workplace,
        address=payload.address,
        zip=payload.zip,
        country=payload.country,
    )
    db.add(workplace)
    db.commit()
    db.refresh(workplace)
    notify_admin_data_changed("register")
    return WorkplaceRow(
        id=workplace.id,
        workplace=workplace.workplace,
        address=workplace.address,
        zip=workplace.zip,
        country=workplace.country,
    )


@router.post("/vehicles", response_model=AdminActionResponse, dependencies=[Depends(require_transport_session)])
def create_transport_vehicle(
    payload: TransportVehicleCreate,
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    try:
        create_transport_vehicle_registration(db, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    notify_admin_data_changed("register")
    notify_transport_data_changed("register")
    return AdminActionResponse(ok=True, message="Vehicle saved successfully.")


@router.delete("/vehicles/{schedule_id}", response_model=AdminActionResponse, dependencies=[Depends(require_transport_session)])
def delete_transport_vehicle_for_route(
    schedule_id: int,
    service_date: date = Query(...),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    try:
        delete_transport_vehicle_registration(db, schedule_id=schedule_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    notify_admin_data_changed("event")
    notify_transport_data_changed("event")
    return AdminActionResponse(ok=True, message="Vehicle deleted from the database.")


@router.post("/assignments", response_model=AdminActionResponse)
def save_transport_assignment(
    payload: TransportAssignmentUpsert,
    db: Session = Depends(get_db),
    _current_transport_user: User = Depends(require_transport_session),
) -> AdminActionResponse:
    transport_request = db.get(TransportRequest, payload.request_id)
    if transport_request is None:
        raise HTTPException(status_code=404, detail="Transport request not found.")
    if not request_applies_to_date(transport_request, payload.service_date):
        raise HTTPException(status_code=400, detail="The transport request does not apply to the selected date.")

    vehicle = None
    if payload.vehicle_id is not None:
        vehicle = db.get(Vehicle, payload.vehicle_id)
        if vehicle is None:
            raise HTTPException(status_code=404, detail="Vehicle not found.")
        if vehicle.service_scope != transport_request.request_kind:
            raise HTTPException(status_code=409, detail="The selected vehicle belongs to a different list.")
        if find_transport_vehicle_schedule(
            db,
            vehicle=vehicle,
            service_date=payload.service_date,
            route_kind=payload.route_kind,
        ) is None:
            raise HTTPException(status_code=409, detail="The selected vehicle is not available for this date and route.")

    assignment, is_update = upsert_transport_assignment_with_persistence(
        db,
        transport_request=transport_request,
        service_date=payload.service_date,
        route_kind=payload.route_kind,
        status=payload.status,
        vehicle=vehicle,
        response_message=payload.response_message,
        admin_user_id=None,
    )

    db.commit()

    notify_admin_data_changed("event")
    notify_transport_data_changed("event")
    return AdminActionResponse(ok=True, message="Transport assignment saved successfully.")


@router.post("/requests/reject", response_model=AdminActionResponse)
def reject_transport_request(
    payload: TransportRequestReject,
    db: Session = Depends(get_db),
    _current_transport_user: User = Depends(require_transport_session),
) -> AdminActionResponse:
    transport_request = db.get(TransportRequest, payload.request_id)
    if transport_request is None or transport_request.status != "active":
        raise HTTPException(status_code=404, detail="Transport request not found.")
    if not request_applies_to_date(transport_request, payload.service_date):
        raise HTTPException(status_code=400, detail="The transport request does not apply to the selected date.")

    assignment, is_update = reject_transport_request_and_assignments(
        db,
        transport_request=transport_request,
        service_date=payload.service_date,
        route_kind=payload.route_kind,
        response_message=payload.response_message,
        admin_user_id=None,
    )

    db.commit()

    notify_admin_data_changed("event")
    notify_transport_data_changed("event")
    return AdminActionResponse(
        ok=True,
        message="Transport request rejected successfully.",
    )
