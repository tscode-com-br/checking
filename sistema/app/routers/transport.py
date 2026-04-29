from __future__ import annotations

import asyncio
import json
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import TransportRequest, User, Vehicle, Workplace
from ..schemas import (
    AdminActionResponse,
    TransportAssignmentUpsert,
    TransportAuthVerifyRequest,
    TransportCurrencyCreateRequest,
    TransportCurrencyOptionRow,
    TransportDateSettingsResponse,
    TransportDateSettingsUpdateRequest,
    TransportDashboardResponse,
    TransportIdentity,
    TransportOperationalProposal,
    TransportOperationalProposalApplyRequest,
    TransportOperationalProposalApplyResult,
    TransportOperationalProposalBuildRequest,
    TransportOperationalProposalCommandResult,
    TransportOperationalProposalRejectRequest,
    TransportOperationalSnapshot,
    TransportReevaluationCatalogResponse,
    TransportSettingsResponse,
    TransportSettingsUpdateRequest,
    TransportSessionResponse,
    TransportWorkToHomeTimePolicyResponse,
    TransportRequestReject,
    TransportVehicleCreate,
    TransportVehicleScheduleUpdate,
    TransportVehicleUpdate,
    TransportWorkplaceUpsert,
    TransportWorkplaceUpdate,
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
    create_transport_currency_option,
    get_transport_last_update_time,
    get_transport_settings_payload,
    get_transport_vehicle_default_seat_counts,
    get_transport_work_to_home_time,
    resolve_transport_work_to_home_time_policy,
    upsert_transport_pricing_settings,
    upsert_transport_last_update_time,
    upsert_transport_vehicle_default_seat_counts,
    upsert_transport_work_to_home_time,
    upsert_transport_work_to_home_time_for_date,
)
from ..services.time_utils import now_sgt
from ..services.transport import (
    build_transport_list_export,
    build_transport_operational_plan_export,
    build_transport_dashboard,
    create_transport_vehicle_registration,
    delete_transport_vehicle_registration,
    find_transport_vehicle_schedule,
    list_workplaces,
    reject_transport_request_and_assignments,
    request_applies_to_date,
    update_transport_vehicle_schedule,
    update_transport_vehicle_base,
    upsert_transport_assignment_with_persistence,
)
from ..services.transport_proposals import (
    apply_transport_operational_proposal,
    approve_transport_operational_proposal,
    build_transport_operational_proposal_contract,
    build_transport_operational_snapshot,
    proposal_has_blocking_issues,
    reject_transport_operational_proposal,
    validate_transport_operational_proposal,
)
from ..services.transport_reevaluation_events import (
    build_transport_reevaluation_catalog_response,
    emit_transport_reevaluation_event,
)
from ..services.user_sync import find_user_by_chave


router = APIRouter(prefix="/api/transport", tags=["transport"])


def build_transport_identity(user: User) -> TransportIdentity:
    return TransportIdentity(id=user.id, chave=user.chave, nome_completo=user.nome, perfil=user.perfil)


def build_workplace_row(workplace: Workplace) -> WorkplaceRow:
    return WorkplaceRow(
        id=workplace.id,
        workplace=workplace.workplace,
        address=workplace.address,
        zip=workplace.zip,
        country=workplace.country,
        transport_group=workplace.transport_group,
        boarding_point=workplace.boarding_point,
        transport_window_start=workplace.transport_window_start,
        transport_window_end=workplace.transport_window_end,
        service_restrictions=workplace.service_restrictions,
        transport_work_to_home_time=workplace.transport_work_to_home_time,
    )


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


@router.get(
    "/operational-snapshot",
    response_model=TransportOperationalSnapshot,
    dependencies=[Depends(require_transport_session)],
)
def get_transport_operational_snapshot(
    service_date: date | None = Query(default=None),
    route_kind: Literal["home_to_work", "work_to_home"] = Query(default="home_to_work"),
    db: Session = Depends(get_db),
) -> TransportOperationalSnapshot:
    resolved_date = service_date or now_sgt().date()
    return build_transport_operational_snapshot(
        db,
        service_date=resolved_date,
        route_kind=route_kind,
    )


@router.get(
    "/reevaluation-events",
    response_model=TransportReevaluationCatalogResponse,
    dependencies=[Depends(require_transport_session)],
)
def get_transport_reevaluation_events(
    limit: int = Query(default=20, ge=1, le=50),
) -> TransportReevaluationCatalogResponse:
    return build_transport_reevaluation_catalog_response(limit=limit)


@router.post("/proposals/build", response_model=TransportOperationalProposal)
def build_transport_proposal_command(
    payload: TransportOperationalProposalBuildRequest,
    transport_user: User = Depends(require_transport_session),
    db: Session = Depends(get_db),
) -> TransportOperationalProposal:
    return build_transport_operational_proposal_contract(
        db,
        service_date=payload.service_date,
        route_kind=payload.route_kind,
        origin=payload.origin,
        actor=build_transport_identity(transport_user),
        replaces_proposal_key=payload.replaces_proposal_key,
        decisions=payload.decisions,
        captured_at=payload.captured_at,
        created_at=payload.created_at,
        expires_at=payload.expires_at,
    )


@router.post("/proposals/validate", response_model=TransportOperationalProposalCommandResult)
def validate_transport_proposal_command(
    payload: TransportOperationalProposal,
    transport_user: User = Depends(require_transport_session),
    db: Session = Depends(get_db),
) -> TransportOperationalProposalCommandResult:
    validated_proposal = validate_transport_operational_proposal(
        db,
        proposal=payload,
        actor=build_transport_identity(transport_user),
    )
    is_ok = not proposal_has_blocking_issues(validated_proposal)
    emit_transport_reevaluation_event(
        event_type="transport_operational_review_changed",
        reason="event",
        source="transport_proposal",
        message="A transport proposal was validated for operational review.",
        service_date=validated_proposal.snapshot.service_date,
        route_kind=validated_proposal.snapshot.route_kind,
        proposal_key=validated_proposal.proposal_key,
    )
    return TransportOperationalProposalCommandResult(
        ok=is_ok,
        message=(
            "Proposal validation passed without blocking issues."
            if is_ok
            else "Proposal validation found blocking issues."
        ),
        proposal=validated_proposal,
    )


@router.post("/proposals/approve", response_model=TransportOperationalProposalCommandResult)
def approve_transport_proposal_command(
    payload: TransportOperationalProposal,
    transport_user: User = Depends(require_transport_session),
    db: Session = Depends(get_db),
) -> TransportOperationalProposalCommandResult:
    approved_proposal = approve_transport_operational_proposal(
        db,
        proposal=payload,
        actor=build_transport_identity(transport_user),
    )
    is_ok = approved_proposal.proposal_status == "approved"
    emit_transport_reevaluation_event(
        event_type="transport_operational_review_changed",
        reason="event",
        source="transport_proposal",
        message="A transport proposal approval outcome was recorded.",
        service_date=approved_proposal.snapshot.service_date,
        route_kind=approved_proposal.snapshot.route_kind,
        proposal_key=approved_proposal.proposal_key,
    )
    return TransportOperationalProposalCommandResult(
        ok=is_ok,
        message=(
            "Proposal approved without applying assignments."
            if is_ok
            else "Proposal approval was blocked by validation issues."
        ),
        proposal=approved_proposal,
    )


@router.post("/proposals/reject", response_model=TransportOperationalProposalCommandResult)
def reject_transport_proposal_command(
    payload: TransportOperationalProposalRejectRequest,
    transport_user: User = Depends(require_transport_session),
) -> TransportOperationalProposalCommandResult:
    rejected_proposal = reject_transport_operational_proposal(
        proposal=payload.proposal,
        actor=build_transport_identity(transport_user),
        message=payload.message,
    )
    emit_transport_reevaluation_event(
        event_type="transport_operational_review_changed",
        reason="event",
        source="transport_proposal",
        message="A transport proposal was rejected during operational review.",
        service_date=rejected_proposal.snapshot.service_date,
        route_kind=rejected_proposal.snapshot.route_kind,
        proposal_key=rejected_proposal.proposal_key,
    )
    return TransportOperationalProposalCommandResult(
        ok=True,
        message="Proposal rejected without applying assignments.",
        proposal=rejected_proposal,
    )


@router.post("/proposals/apply", response_model=TransportOperationalProposalApplyResult)
def apply_transport_proposal_command(
    payload: TransportOperationalProposalApplyRequest,
    transport_user: User = Depends(require_transport_session),
    db: Session = Depends(get_db),
) -> TransportOperationalProposalApplyResult:
    applied_proposal, applied_assignments = apply_transport_operational_proposal(
        db,
        proposal=payload.proposal,
        actor=build_transport_identity(transport_user),
    )
    is_ok = applied_proposal.proposal_status == "applied"
    if is_ok:
        db.commit()
        notify_admin_data_changed("event")
        emit_transport_reevaluation_event(
            event_type="transport_assignment_changed",
            reason="event",
            source="transport_proposal",
            message="An approved transport proposal was applied to transport assignments.",
            service_date=applied_proposal.snapshot.service_date,
            route_kind=applied_proposal.snapshot.route_kind,
            proposal_key=applied_proposal.proposal_key,
        )

    return TransportOperationalProposalApplyResult(
        ok=is_ok,
        message=(
            "Proposal applied to transport assignments."
            if is_ok
            else "Proposal application was blocked by validation issues."
        ),
        proposal=applied_proposal,
        applied_assignments=applied_assignments,
    )


@router.get("/exports/transport-list", dependencies=[Depends(require_transport_session)])
def export_transport_list(
    service_date: date = Query(...),
    route_kind: Literal["home_to_work", "work_to_home"] = Query(default="home_to_work"),
    db: Session = Depends(get_db),
) -> Response:
    file_name, content = build_transport_list_export(
        db,
        service_date=service_date,
        selected_route_kind=route_kind,
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.post("/exports/operational-plan", dependencies=[Depends(require_transport_session)])
def export_transport_operational_plan(
    payload: TransportOperationalProposal,
    db: Session = Depends(get_db),
) -> Response:
    file_name, content = build_transport_operational_plan_export(
        db,
        service_date=payload.snapshot.service_date,
        selected_route_kind=payload.snapshot.route_kind,
        proposal=payload,
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/settings", response_model=TransportSettingsResponse, dependencies=[Depends(require_transport_session)])
def get_transport_settings(db: Session = Depends(get_db)) -> TransportSettingsResponse:
    return TransportSettingsResponse(**get_transport_settings_payload(db))


@router.put("/settings", response_model=TransportSettingsResponse, dependencies=[Depends(require_transport_session)])
def update_transport_settings(
    payload: TransportSettingsUpdateRequest,
    db: Session = Depends(get_db),
) -> TransportSettingsResponse:
    previous_work_to_home_time = get_transport_work_to_home_time(db)
    previous_last_update_time = get_transport_last_update_time(db)

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
    try:
        upsert_transport_pricing_settings(
            db,
            price_currency_code=payload.price_currency_code,
            price_rate_unit=payload.price_rate_unit,
            default_car_price=payload.default_car_price,
            default_minivan_price=payload.default_minivan_price,
            default_van_price=payload.default_van_price,
            default_bus_price=payload.default_bus_price,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    if (
        previous_work_to_home_time != payload.work_to_home_time
        or previous_last_update_time != payload.last_update_time
    ):
        emit_transport_reevaluation_event(
            event_type="transport_timing_policy_changed",
            reason="settings",
            source="transport_admin",
            message="The global transport timing policy was updated.",
            route_kind="work_to_home",
        )
    return TransportSettingsResponse(**get_transport_settings_payload(db))


@router.post(
    "/settings/currencies",
    response_model=TransportCurrencyOptionRow,
    dependencies=[Depends(require_transport_session)],
)
def create_transport_settings_currency(
    payload: TransportCurrencyCreateRequest,
    db: Session = Depends(get_db),
) -> TransportCurrencyOptionRow:
    try:
        currency_row = create_transport_currency_option(
            db,
            code=payload.code,
            display_label=payload.display_label,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    return TransportCurrencyOptionRow(code=currency_row.code, display_label=currency_row.display_label)


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
    emit_transport_reevaluation_event(
        event_type="transport_timing_policy_changed",
        reason="settings",
        source="transport_admin",
        message="A date-specific transport timing override was updated.",
        service_date=daily_setting.service_date,
        route_kind="work_to_home",
    )
    return TransportDateSettingsResponse(
        service_date=daily_setting.service_date,
        work_to_home_time=daily_setting.work_to_home_time,
    )


@router.get(
    "/work-to-home-time-policy",
    response_model=TransportWorkToHomeTimePolicyResponse,
    dependencies=[Depends(require_transport_session)],
)
def get_transport_work_to_home_time_policy(
    service_date: date = Query(...),
    workplace: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> TransportWorkToHomeTimePolicyResponse:
    normalized_workplace = workplace.strip() if workplace is not None else None
    if normalized_workplace:
        resolved_workplace = db.execute(
            select(Workplace).where(Workplace.workplace == normalized_workplace)
        ).scalar_one_or_none()
        if resolved_workplace is None:
            raise HTTPException(status_code=404, detail="Workplace not found for the provided policy context.")
        normalized_workplace = resolved_workplace.workplace
    elif normalized_workplace == "":
        normalized_workplace = None

    policy = resolve_transport_work_to_home_time_policy(
        db,
        service_date=service_date,
        workplace_name=normalized_workplace,
    )
    return TransportWorkToHomeTimePolicyResponse(
        service_date=policy.service_date,
        workplace=policy.workplace,
        resolved_work_to_home_time=policy.resolved_work_to_home_time,
        source=policy.source,
        global_work_to_home_time=policy.global_work_to_home_time,
        date_override_work_to_home_time=policy.date_override_work_to_home_time,
        workplace_work_to_home_time=policy.workplace_work_to_home_time,
        transport_group=policy.transport_group,
        boarding_point=policy.boarding_point,
        transport_window_start=policy.transport_window_start,
        transport_window_end=policy.transport_window_end,
        service_restrictions=policy.service_restrictions,
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
        transport_group=payload.transport_group,
        boarding_point=payload.boarding_point,
        transport_window_start=payload.transport_window_start,
        transport_window_end=payload.transport_window_end,
        service_restrictions=payload.service_restrictions,
        transport_work_to_home_time=payload.transport_work_to_home_time,
    )
    db.add(workplace)
    db.commit()
    db.refresh(workplace)
    notify_admin_data_changed("register")
    emit_transport_reevaluation_event(
        event_type="transport_workplace_context_changed",
        reason="register",
        source="transport_admin",
        message="A workplace operational context was created.",
        workplace_id=workplace.id,
    )
    return build_workplace_row(workplace)


@router.put("/workplaces/{workplace_id}", response_model=WorkplaceRow, dependencies=[Depends(require_transport_session)])
def update_transport_workplace(
    workplace_id: int,
    payload: TransportWorkplaceUpdate,
    db: Session = Depends(get_db),
) -> WorkplaceRow:
    workplace = db.get(Workplace, workplace_id)
    if workplace is None:
        raise HTTPException(status_code=404, detail="Workplace not found.")

    workplace.address = payload.address
    workplace.zip = payload.zip
    workplace.country = payload.country
    workplace.transport_group = payload.transport_group
    workplace.boarding_point = payload.boarding_point
    workplace.transport_window_start = payload.transport_window_start
    workplace.transport_window_end = payload.transport_window_end
    workplace.service_restrictions = payload.service_restrictions
    workplace.transport_work_to_home_time = payload.transport_work_to_home_time

    db.commit()
    db.refresh(workplace)
    notify_admin_data_changed("register")
    emit_transport_reevaluation_event(
        event_type="transport_workplace_context_changed",
        reason="register",
        source="transport_admin",
        message="A workplace operational context was updated.",
        workplace_id=workplace.id,
    )
    return build_workplace_row(workplace)


@router.post("/vehicles", response_model=AdminActionResponse, dependencies=[Depends(require_transport_session)])
def create_transport_vehicle(
    payload: TransportVehicleCreate,
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    try:
        vehicle, created_schedules = create_transport_vehicle_registration(db, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    notify_admin_data_changed("register")
    emit_transport_reevaluation_event(
        event_type="transport_vehicle_supply_changed",
        reason="register",
        source="transport_admin",
        message="A vehicle registration changed the available transport supply.",
        service_date=payload.service_date,
        route_kind=payload.route_kind,
        vehicle_id=vehicle.id,
        schedule_id=created_schedules[0].id if len(created_schedules) == 1 else None,
    )
    return AdminActionResponse(ok=True, message="Vehicle saved successfully.")


@router.delete("/vehicles/{schedule_id}", response_model=AdminActionResponse, dependencies=[Depends(require_transport_session)])
def delete_transport_vehicle_for_route(
    schedule_id: int,
    service_date: date = Query(...),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    try:
        vehicle = delete_transport_vehicle_registration(db, schedule_id=schedule_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    notify_admin_data_changed("event")
    emit_transport_reevaluation_event(
        event_type="transport_vehicle_schedule_changed",
        reason="event",
        source="transport_admin",
        message="A vehicle schedule was removed from operational availability.",
        service_date=service_date,
        vehicle_id=vehicle.id,
        schedule_id=schedule_id,
    )
    return AdminActionResponse(ok=True, message="Vehicle deleted from the database.")


@router.put("/vehicles/{vehicle_id}", response_model=AdminActionResponse, dependencies=[Depends(require_transport_session)])
def update_transport_vehicle(
    vehicle_id: int,
    payload: TransportVehicleUpdate,
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    try:
        vehicle = update_transport_vehicle_base(
            db,
            vehicle_id=vehicle_id,
            payload=payload,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "Vehicle not found.":
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=409, detail=detail) from exc

    db.commit()
    notify_admin_data_changed("register")
    emit_transport_reevaluation_event(
        event_type="transport_vehicle_supply_changed",
        reason="register",
        source="transport_admin",
        message="A vehicle configuration changed the transport supply context.",
        vehicle_id=vehicle.id,
    )
    return AdminActionResponse(ok=True, message="Vehicle updated successfully.")


@router.put("/vehicle-schedules/{schedule_id}", response_model=AdminActionResponse, dependencies=[Depends(require_transport_session)])
def update_transport_vehicle_schedule_route(
    schedule_id: int,
    payload: TransportVehicleScheduleUpdate,
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    try:
        schedule = update_transport_vehicle_schedule(
            db,
            schedule_id=schedule_id,
            payload=payload,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "Vehicle schedule not found." or detail == "Vehicle not found.":
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=409, detail=detail) from exc

    db.commit()
    notify_admin_data_changed("event")
    emit_transport_reevaluation_event(
        event_type="transport_vehicle_schedule_changed",
        reason="event",
        source="transport_admin",
        message="A vehicle schedule changed the operational availability for transport planning.",
        service_date=payload.service_date,
        route_kind=payload.route_kind,
        vehicle_id=schedule.vehicle_id,
        schedule_id=schedule.id,
    )
    return AdminActionResponse(ok=True, message="Vehicle schedule updated successfully.")


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
        scoped_schedule = find_transport_vehicle_schedule(
            db,
            vehicle=vehicle,
            service_date=payload.service_date,
            route_kind=payload.route_kind,
            service_scope=transport_request.request_kind,
        )
        if scoped_schedule is None:
            if find_transport_vehicle_schedule(
                db,
                vehicle=vehicle,
                service_date=payload.service_date,
                route_kind=payload.route_kind,
            ) is not None:
                raise HTTPException(status_code=409, detail="The selected vehicle belongs to a different list.")
            raise HTTPException(status_code=409, detail="The selected vehicle is not available for this date and route.")

    try:
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
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()

    notify_admin_data_changed("event")
    emit_transport_reevaluation_event(
        event_type="transport_assignment_changed",
        reason="event",
        source="transport_admin",
        message="A transport assignment decision changed the operational state of the day.",
        service_date=payload.service_date,
        route_kind=payload.route_kind,
        request_id=transport_request.id,
        vehicle_id=vehicle.id if vehicle is not None else None,
    )
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
    emit_transport_reevaluation_event(
        event_type="transport_assignment_changed",
        reason="event",
        source="transport_admin",
        message="A transport request rejection changed the operational state of the day.",
        service_date=payload.service_date,
        route_kind=payload.route_kind,
        request_id=transport_request.id,
    )
    return AdminActionResponse(
        ok=True,
        message="Transport request rejected successfully.",
    )
