from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import TransportAssignment, TransportRequest, Vehicle
from .time_utils import now_sgt
from .transport_vehicle_base import is_transport_vehicle_ready_for_allocation
from .transport_vehicle_operations import find_transport_vehicle_schedule


EXTRA_ASSIGNMENT_SUPERSEDED_RESPONSE_MESSAGE = "Superseded by confirmed extra transport assignment"
CONFIRMED_EXTRA_OVERRIDE_CONFLICT_MESSAGE_PREFIX = (
    "The user already has a confirmed extra transport override for this date and route"
)
TRANSPORT_ASSIGNMENT_BOARDING_TIME_UNSET = object()


def _resolve_persisted_assignment_boarding_time(
    existing_assignment: TransportAssignment | None,
    *,
    route_kind: str,
    status: str,
    vehicle: Vehicle | None,
    boarding_time: str | None | object,
) -> str | None:
    if status != "confirmed" or vehicle is None or route_kind != "home_to_work":
        return None
    if boarding_time is TRANSPORT_ASSIGNMENT_BOARDING_TIME_UNSET:
        if existing_assignment is None:
            return None
        if existing_assignment.status != "confirmed" or existing_assignment.vehicle_id is None:
            return None
        if existing_assignment.route_kind != "home_to_work":
            return None
        return existing_assignment.boarding_time
    return boarding_time


def update_transport_assignment(
    db: Session,
    *,
    transport_request: TransportRequest,
    service_date: date,
    route_kind: str,
    status: str,
    vehicle: Vehicle | None,
    response_message: str | None,
    boarding_time: str | None | object = TRANSPORT_ASSIGNMENT_BOARDING_TIME_UNSET,
    admin_user_id: int | None,
) -> tuple[TransportAssignment, bool]:
    from .transport import now_sgt as transport_now_sgt

    timestamp = transport_now_sgt()
    next_vehicle_id = vehicle.id if vehicle is not None else None
    assignment = db.execute(
        select(TransportAssignment).where(
            TransportAssignment.request_id == transport_request.id,
            TransportAssignment.service_date == service_date,
            TransportAssignment.route_kind == route_kind,
        )
    ).scalar_one_or_none()
    is_update = assignment is not None
    next_boarding_time = _resolve_persisted_assignment_boarding_time(
        assignment,
        route_kind=route_kind,
        status=status,
        vehicle=vehicle,
        boarding_time=boarding_time,
    )
    if assignment is None:
        assignment = TransportAssignment(
            request_id=transport_request.id,
            service_date=service_date,
            route_kind=route_kind,
            vehicle_id=next_vehicle_id,
            status=status,
            response_message=response_message,
            boarding_time=next_boarding_time,
            acknowledged_by_user=False,
            acknowledged_at=None,
            assigned_by_admin_id=admin_user_id,
            created_at=timestamp,
            updated_at=timestamp,
            notified_at=None,
        )
        db.add(assignment)
        db.flush()
    else:
        assignment_changed = (
            assignment.vehicle_id != next_vehicle_id
            or assignment.status != status
            or assignment.route_kind != route_kind
            or assignment.service_date != service_date
            or assignment.boarding_time != next_boarding_time
        )
        assignment.route_kind = route_kind
        assignment.vehicle_id = next_vehicle_id
        assignment.status = status
        assignment.response_message = response_message
        assignment.boarding_time = next_boarding_time
        if status != "confirmed":
            assignment.acknowledged_by_user = False
            assignment.acknowledged_at = None
        elif assignment_changed:
            assignment.acknowledged_by_user = False
            assignment.acknowledged_at = None
        assignment.assigned_by_admin_id = admin_user_id
        assignment.updated_at = timestamp
        assignment.notified_at = None
    return assignment, is_update


def update_transport_assignment_boarding_time(
    db: Session,
    *,
    transport_request: TransportRequest,
    service_date: date,
    route_kind: str,
    boarding_time: str | None,
    admin_user_id: int | None,
) -> TransportAssignment:
    if route_kind != "home_to_work":
        raise ValueError("Manual boarding_time is only available for confirmed home_to_work assignments.")

    assignment = db.execute(
        select(TransportAssignment).where(
            TransportAssignment.request_id == transport_request.id,
            TransportAssignment.service_date == service_date,
            TransportAssignment.route_kind == route_kind,
        )
    ).scalar_one_or_none()
    if assignment is None or assignment.status != "confirmed" or assignment.vehicle_id is None:
        raise ValueError("A confirmed transport assignment is required to update boarding_time.")

    vehicle = db.get(Vehicle, assignment.vehicle_id)
    if vehicle is None or not is_transport_vehicle_ready_for_allocation(vehicle):
        raise ValueError("The transport assignment is no longer operationally valid for boarding_time updates.")

    updated_assignment, _ = update_transport_assignment(
        db,
        transport_request=transport_request,
        service_date=service_date,
        route_kind=route_kind,
        status=assignment.status,
        vehicle=vehicle,
        response_message=assignment.response_message,
        boarding_time=boarding_time,
        admin_user_id=admin_user_id,
    )
    return updated_assignment


def _find_confirmed_user_assignments_for_service_date_route(
    db: Session,
    *,
    user_id: int,
    service_date: date,
    route_kind: str,
    request_kinds: tuple[str, ...] | list[str] | set[str] | None = None,
    excluded_request_id: int | None = None,
) -> list[TransportAssignment]:
    from .transport import request_applies_to_date

    normalized_request_kinds = tuple(
        sorted(
            {
                str(request_kind or "").strip().lower()
                for request_kind in (request_kinds or ())
                if str(request_kind or "").strip()
            }
        )
    )

    request_query = select(TransportRequest).where(
        TransportRequest.user_id == user_id,
        TransportRequest.status == "active",
    )
    if normalized_request_kinds:
        request_query = request_query.where(TransportRequest.request_kind.in_(normalized_request_kinds))
    if excluded_request_id is not None:
        request_query = request_query.where(TransportRequest.id != excluded_request_id)

    active_requests = db.execute(request_query).scalars().all()
    matching_request_ids = [
        transport_request.id
        for transport_request in active_requests
        if request_applies_to_date(transport_request, service_date)
    ]
    if not matching_request_ids:
        return []

    return db.execute(
        select(TransportAssignment)
        .where(
            TransportAssignment.request_id.in_(matching_request_ids),
            TransportAssignment.service_date == service_date,
            TransportAssignment.route_kind == route_kind,
            TransportAssignment.status == "confirmed",
        )
        .order_by(TransportAssignment.id)
    ).scalars().all()


def _find_confirmed_recurring_assignment_conflicts(
    db: Session,
    *,
    user_id: int,
    service_date: date,
    route_kind: str,
    excluded_request_id: int | None = None,
) -> list[TransportAssignment]:
    return _find_confirmed_user_assignments_for_service_date_route(
        db,
        user_id=user_id,
        service_date=service_date,
        route_kind=route_kind,
        request_kinds={"regular", "weekend"},
        excluded_request_id=excluded_request_id,
    )


def _find_confirmed_extra_assignment_conflicts_for_recurring_confirmation(
    db: Session,
    *,
    user_id: int,
    service_date: date,
    excluded_request_id: int | None = None,
) -> list[TransportAssignment]:
    conflicting_assignments_by_id: dict[int, TransportAssignment] = {}
    for affected_route_kind in ("home_to_work", "work_to_home"):
        for assignment in _find_confirmed_user_assignments_for_service_date_route(
            db,
            user_id=user_id,
            service_date=service_date,
            route_kind=affected_route_kind,
            request_kinds={"extra"},
            excluded_request_id=excluded_request_id,
        ):
            conflicting_assignments_by_id[assignment.id] = assignment
    return [
        conflicting_assignments_by_id[assignment_id]
        for assignment_id in sorted(conflicting_assignments_by_id)
    ]


def _build_confirmed_extra_override_conflict_message(
    *,
    conflicting_assignments: list[TransportAssignment],
) -> str:
    conflicting_route_kinds = ", ".join(
        sorted(
            {
                assignment.route_kind
                for assignment in conflicting_assignments
                if str(assignment.route_kind or "").strip()
            }
        )
    )
    if not conflicting_route_kinds:
        return f"{CONFIRMED_EXTRA_OVERRIDE_CONFLICT_MESSAGE_PREFIX}."
    return f"{CONFIRMED_EXTRA_OVERRIDE_CONFLICT_MESSAGE_PREFIX}: {conflicting_route_kinds}."


def _reset_recurring_assignment_conflicts_for_confirmed_extra(
    db: Session,
    *,
    transport_request: TransportRequest,
    service_date: date,
    route_kind: str,
    admin_user_id: int | None,
) -> None:
    conflicting_assignments = _find_confirmed_recurring_assignment_conflicts(
        db,
        user_id=transport_request.user_id,
        service_date=service_date,
        route_kind=route_kind,
        excluded_request_id=transport_request.id,
    )
    if not conflicting_assignments:
        return

    for conflicting_request_id in sorted({assignment.request_id for assignment in conflicting_assignments}):
        conflicting_request = db.get(TransportRequest, conflicting_request_id)
        if conflicting_request is None:
            continue
        _reset_transport_request_assignments_to_pending(
            db,
            transport_request=conflicting_request,
            response_message=EXTRA_ASSIGNMENT_SUPERSEDED_RESPONSE_MESSAGE,
            admin_user_id=admin_user_id,
            service_date=service_date,
            route_kind=route_kind,
            pending_reset_scope="service_date_route",
        )


def _reset_transport_request_assignments_to_pending(
    db: Session,
    *,
    transport_request: TransportRequest,
    response_message: str | None,
    admin_user_id: int | None,
    service_date: date | None = None,
    route_kind: str | None = None,
    pending_reset_scope: str = "all_assignments",
) -> None:
    from .transport import _resolve_transport_assignment
    from .transport import now_sgt as transport_now_sgt

    normalized_pending_reset_scope = str(pending_reset_scope or "all_assignments").strip().lower()
    if normalized_pending_reset_scope not in {"all_assignments", "service_date_route"}:
        raise ValueError(f"Unsupported pending reset scope: {pending_reset_scope!r}")
    if normalized_pending_reset_scope == "service_date_route" and (service_date is None or route_kind is None):
        raise ValueError("service_date and route_kind are required for service_date_route pending resets.")

    timestamp = transport_now_sgt()
    assignments = db.execute(
        select(TransportAssignment).where(TransportAssignment.request_id == transport_request.id)
    ).scalars().all()

    for assignment in assignments:
        if normalized_pending_reset_scope == "service_date_route" and (
            assignment.service_date != service_date or assignment.route_kind != route_kind
        ):
            continue
        _resolve_transport_assignment(
            assignment,
            status="pending",
            response_message=response_message,
            timestamp=timestamp,
            admin_user_id=admin_user_id,
        )


def upsert_transport_assignment_with_persistence(
    db: Session,
    *,
    transport_request: TransportRequest,
    service_date: date,
    route_kind: str,
    status: str,
    vehicle: Vehicle | None,
    response_message: str | None,
    boarding_time: str | None | object = TRANSPORT_ASSIGNMENT_BOARDING_TIME_UNSET,
    admin_user_id: int | None,
    pending_reset_scope: str = "all_assignments",
) -> tuple[TransportAssignment, bool]:
    existing_assignment = db.execute(
        select(TransportAssignment).where(
            TransportAssignment.request_id == transport_request.id,
            TransportAssignment.service_date == service_date,
            TransportAssignment.route_kind == route_kind,
        )
    ).scalar_one_or_none()
    is_update = existing_assignment is not None

    if status == "confirmed" and vehicle is not None and not is_transport_vehicle_ready_for_allocation(vehicle):
        raise ValueError("The selected vehicle is not ready for allocation.")

    if status == "pending":
        if transport_request.request_kind in {"regular", "weekend"}:
            _reset_transport_request_assignments_to_pending(
                db,
                transport_request=transport_request,
                response_message=response_message,
                admin_user_id=admin_user_id,
                service_date=service_date,
                route_kind=route_kind,
                pending_reset_scope=pending_reset_scope,
            )

        assignment, _ = update_transport_assignment(
            db,
            transport_request=transport_request,
            service_date=service_date,
            route_kind=route_kind,
            status=status,
            vehicle=vehicle,
            response_message=response_message,
            boarding_time=boarding_time,
            admin_user_id=admin_user_id,
        )
        return assignment, is_update

    if status == "confirmed" and vehicle is not None and transport_request.request_kind in {"regular", "weekend"}:
        conflicting_extra_assignments = _find_confirmed_extra_assignment_conflicts_for_recurring_confirmation(
            db,
            user_id=transport_request.user_id,
            service_date=service_date,
            excluded_request_id=transport_request.id,
        )
        if conflicting_extra_assignments:
            raise ValueError(
                _build_confirmed_extra_override_conflict_message(
                    conflicting_assignments=conflicting_extra_assignments
                )
            )
        _propagate_confirmed_recurring_assignment(
            db,
            transport_request=transport_request,
            service_date=service_date,
            route_kind=route_kind,
            vehicle=vehicle,
            response_message=response_message,
            boarding_time=boarding_time,
            admin_user_id=admin_user_id,
        )
        assignment = db.execute(
            select(TransportAssignment).where(
                TransportAssignment.request_id == transport_request.id,
                TransportAssignment.service_date == service_date,
                TransportAssignment.route_kind == route_kind,
            )
        ).scalar_one()
        return assignment, is_update

    if status == "confirmed" and vehicle is not None and transport_request.request_kind == "extra":
        assignment, _ = update_transport_assignment(
            db,
            transport_request=transport_request,
            service_date=service_date,
            route_kind=route_kind,
            status=status,
            vehicle=vehicle,
            response_message=response_message,
            boarding_time=boarding_time,
            admin_user_id=admin_user_id,
        )
        _reset_recurring_assignment_conflicts_for_confirmed_extra(
            db,
            transport_request=transport_request,
            service_date=service_date,
            route_kind=route_kind,
            admin_user_id=admin_user_id,
        )
        return assignment, is_update

    return update_transport_assignment(
        db,
        transport_request=transport_request,
        service_date=service_date,
        route_kind=route_kind,
        status=status,
        vehicle=vehicle,
        response_message=response_message,
        boarding_time=boarding_time,
        admin_user_id=admin_user_id,
    )


def _propagate_confirmed_recurring_assignment(
    db: Session,
    *,
    transport_request: TransportRequest,
    service_date: date,
    route_kind: str,
    vehicle: Vehicle,
    response_message: str | None,
    boarding_time: str | None | object,
    admin_user_id: int | None,
) -> None:
    from .transport import (
        _load_active_schedules_by_vehicle_id,
        _resolve_assignment_template_weekdays,
        now_sgt as transport_now_sgt,
        request_applies_to_date,
    )

    timestamp = transport_now_sgt()
    schedules_by_vehicle_id = _load_active_schedules_by_vehicle_id(db, vehicle_ids={vehicle.id})
    target_weekdays = _resolve_assignment_template_weekdays(
        transport_request=transport_request,
        vehicle=vehicle,
        schedules=schedules_by_vehicle_id.get(vehicle.id, []),
        reference_date=service_date,
    )
    if not target_weekdays:
        target_weekdays = {service_date.weekday()}

    assignments = db.execute(
        select(TransportAssignment).where(TransportAssignment.request_id == transport_request.id)
    ).scalars().all()
    assignments_by_key = {
        (assignment.service_date, assignment.route_kind): assignment
        for assignment in assignments
    }

    for assignment in assignments:
        if not request_applies_to_date(transport_request, assignment.service_date):
            continue
        if assignment.service_date.weekday() not in target_weekdays:
            continue

        next_boarding_time = _resolve_persisted_assignment_boarding_time(
            assignment,
            route_kind=assignment.route_kind,
            status="confirmed",
            vehicle=vehicle,
            boarding_time=(
                boarding_time
                if assignment.service_date == service_date and assignment.route_kind == route_kind
                else TRANSPORT_ASSIGNMENT_BOARDING_TIME_UNSET
            ),
        )

        assignment.vehicle_id = vehicle.id
        assignment.status = "confirmed"
        assignment.response_message = response_message
        assignment.boarding_time = next_boarding_time
        assignment.acknowledged_by_user = False
        assignment.acknowledged_at = None
        assignment.assigned_by_admin_id = admin_user_id
        assignment.updated_at = timestamp
        assignment.notified_at = None

    for target_route_kind in ("home_to_work", "work_to_home"):
        if find_transport_vehicle_schedule(
            db,
            vehicle=vehicle,
            service_date=service_date,
            route_kind=target_route_kind,
        ) is None:
            continue

        current_assignment = assignments_by_key.get((service_date, target_route_kind))
        if current_assignment is None:
            next_boarding_time = _resolve_persisted_assignment_boarding_time(
                None,
                route_kind=target_route_kind,
                status="confirmed",
                vehicle=vehicle,
                boarding_time=(
                    boarding_time
                    if target_route_kind == route_kind
                    else TRANSPORT_ASSIGNMENT_BOARDING_TIME_UNSET
                ),
            )
            current_assignment = TransportAssignment(
                request_id=transport_request.id,
                service_date=service_date,
                route_kind=target_route_kind,
                vehicle_id=vehicle.id,
                status="confirmed",
                response_message=response_message,
                boarding_time=next_boarding_time,
                acknowledged_by_user=False,
                acknowledged_at=None,
                assigned_by_admin_id=admin_user_id,
                created_at=timestamp,
                updated_at=timestamp,
                notified_at=None,
            )
            db.add(current_assignment)
            db.flush()
            assignments_by_key[(service_date, target_route_kind)] = current_assignment
            continue

        next_boarding_time = _resolve_persisted_assignment_boarding_time(
            current_assignment,
            route_kind=target_route_kind,
            status="confirmed",
            vehicle=vehicle,
            boarding_time=(
                boarding_time
                if target_route_kind == route_kind
                else TRANSPORT_ASSIGNMENT_BOARDING_TIME_UNSET
            ),
        )

        current_assignment.vehicle_id = vehicle.id
        current_assignment.status = "confirmed"
        current_assignment.response_message = response_message
        current_assignment.boarding_time = next_boarding_time
        current_assignment.acknowledged_by_user = False
        current_assignment.acknowledged_at = None
        current_assignment.assigned_by_admin_id = admin_user_id
        current_assignment.updated_at = timestamp
        current_assignment.notified_at = None


def _materialize_recurring_assignments_for_date(
    db: Session,
    *,
    transport_request: TransportRequest,
    service_date: date,
) -> int:
    from .transport import (
        _build_recurring_assignment_template_index,
        _list_transport_assignments_for_requests,
        _load_active_schedules_by_vehicle_id,
    )

    if transport_request.request_kind not in {"regular", "weekend"}:
        return 0

    assignments = _list_transport_assignments_for_requests(db, request_ids=[transport_request.id])
    explicit_assignments_by_key = {
        (assignment.request_id, assignment.service_date, assignment.route_kind): assignment
        for assignment in assignments
    }
    vehicle_ids = {assignment.vehicle_id for assignment in assignments if assignment.vehicle_id is not None}
    if not vehicle_ids:
        return 0

    vehicles_by_id = {
        vehicle.id: vehicle
        for vehicle in db.execute(select(Vehicle).where(Vehicle.id.in_(vehicle_ids))).scalars().all()
    }
    schedules_by_vehicle_id = _load_active_schedules_by_vehicle_id(db, vehicle_ids=vehicle_ids)
    recurring_assignment_templates = _build_recurring_assignment_template_index(
        assignments=assignments,
        requests_by_id={transport_request.id: transport_request},
        vehicles_by_id=vehicles_by_id,
        schedules_by_vehicle_id=schedules_by_vehicle_id,
    )
    recurring_assignment = recurring_assignment_templates.get((transport_request.id, service_date.weekday()))
    if recurring_assignment is None:
        return 0

    template_assignment, template_vehicle = recurring_assignment
    materialized = 0
    for target_route_kind in ("home_to_work", "work_to_home"):
        if explicit_assignments_by_key.get((transport_request.id, service_date, target_route_kind)) is not None:
            continue
        if find_transport_vehicle_schedule(
            db,
            vehicle=template_vehicle,
            service_date=service_date,
            route_kind=target_route_kind,
        ) is None:
            continue

        update_transport_assignment(
            db,
            transport_request=transport_request,
            service_date=service_date,
            route_kind=target_route_kind,
            status="confirmed",
            vehicle=template_vehicle,
            response_message=template_assignment.response_message,
            boarding_time=TRANSPORT_ASSIGNMENT_BOARDING_TIME_UNSET,
            admin_user_id=template_assignment.assigned_by_admin_id,
        )
        materialized += 1

    return materialized
