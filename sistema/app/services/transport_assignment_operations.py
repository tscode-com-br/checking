from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import TransportAssignment, TransportRequest, Vehicle
from .time_utils import now_sgt
from .transport_vehicle_base import is_transport_vehicle_ready_for_allocation
from .transport_vehicle_operations import find_transport_vehicle_schedule


def update_transport_assignment(
    db: Session,
    *,
    transport_request: TransportRequest,
    service_date: date,
    route_kind: str,
    status: str,
    vehicle: Vehicle | None,
    response_message: str | None,
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
    if assignment is None:
        assignment = TransportAssignment(
            request_id=transport_request.id,
            service_date=service_date,
            route_kind=route_kind,
            vehicle_id=next_vehicle_id,
            status=status,
            response_message=response_message,
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
        )
        assignment.route_kind = route_kind
        assignment.vehicle_id = next_vehicle_id
        assignment.status = status
        assignment.response_message = response_message
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


def _reset_transport_request_assignments_to_pending(
    db: Session,
    *,
    transport_request: TransportRequest,
    response_message: str | None,
    admin_user_id: int | None,
) -> None:
    from .transport import _resolve_transport_assignment
    from .transport import now_sgt as transport_now_sgt

    timestamp = transport_now_sgt()
    assignments = db.execute(
        select(TransportAssignment).where(TransportAssignment.request_id == transport_request.id)
    ).scalars().all()

    for assignment in assignments:
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
    admin_user_id: int | None,
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
            )

        assignment, _ = update_transport_assignment(
            db,
            transport_request=transport_request,
            service_date=service_date,
            route_kind=route_kind,
            status=status,
            vehicle=vehicle,
            response_message=response_message,
            admin_user_id=admin_user_id,
        )
        return assignment, is_update

    if status == "confirmed" and vehicle is not None and transport_request.request_kind in {"regular", "weekend"}:
        _propagate_confirmed_recurring_assignment(
            db,
            transport_request=transport_request,
            service_date=service_date,
            vehicle=vehicle,
            response_message=response_message,
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

    return update_transport_assignment(
        db,
        transport_request=transport_request,
        service_date=service_date,
        route_kind=route_kind,
        status=status,
        vehicle=vehicle,
        response_message=response_message,
        admin_user_id=admin_user_id,
    )


def _propagate_confirmed_recurring_assignment(
    db: Session,
    *,
    transport_request: TransportRequest,
    service_date: date,
    vehicle: Vehicle,
    response_message: str | None,
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

        assignment.vehicle_id = vehicle.id
        assignment.status = "confirmed"
        assignment.response_message = response_message
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
            current_assignment = TransportAssignment(
                request_id=transport_request.id,
                service_date=service_date,
                route_kind=target_route_kind,
                vehicle_id=vehicle.id,
                status="confirmed",
                response_message=response_message,
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

        current_assignment.vehicle_id = vehicle.id
        current_assignment.status = "confirmed"
        current_assignment.response_message = response_message
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
            admin_user_id=template_assignment.assigned_by_admin_id,
        )
        materialized += 1

    return materialized
