from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import TransportAssignment, TransportRequest, TransportVehicleSchedule, User, Vehicle, Workplace
from ..schemas import ProjectRow, TransportDashboardResponse, TransportRequestRow, WorkplaceRow
from .location_settings import get_transport_work_to_home_time_for_date
from .project_catalog import list_projects
from .time_utils import build_timezone_label


def _build_project_row(row) -> ProjectRow:
    return ProjectRow(
        id=row.id,
        name=row.name,
        country_code=row.country_code,
        country_name=row.country_name,
        timezone_name=row.timezone_name,
        timezone_label=build_timezone_label(
            country_name=row.country_name,
            timezone_name=row.timezone_name,
        ),
    )


def list_workplaces(db: Session) -> list[WorkplaceRow]:
    rows = db.execute(select(Workplace).order_by(Workplace.workplace, Workplace.id)).scalars().all()
    return [
        WorkplaceRow(
            id=row.id,
            workplace=row.workplace,
            address=row.address,
            zip=row.zip,
            country=row.country,
            transport_group=row.transport_group,
            boarding_point=row.boarding_point,
            transport_window_start=row.transport_window_start,
            transport_window_end=row.transport_window_end,
            service_restrictions=row.service_restrictions,
            transport_work_to_home_time=row.transport_work_to_home_time,
        )
        for row in rows
    ]


def build_transport_dashboard(
    db: Session,
    *,
    service_date: date,
    route_kind: str,
) -> TransportDashboardResponse:
    from .transport import (
        _build_recurring_assignment_template_index,
        _build_transport_vehicle_registry_rows,
        _build_vehicle_row,
        _build_vehicle_rows_for_dashboard,
        _list_active_transport_schedule_rows,
        _list_transport_assignments_for_requests,
        _transport_dashboard_assignment_priority,
        find_transport_vehicle_schedule,
        resolve_transport_request_dashboard_service_date,
    )

    projects = [_build_project_row(row) for row in list_projects(db)]
    workplaces = list_workplaces(db)
    work_to_home_departure_time = get_transport_work_to_home_time_for_date(db, service_date=service_date)
    vehicles_by_scope, vehicle_rows_by_id, vehicle_rows_by_assignment_key = _build_vehicle_rows_for_dashboard(
        db,
        service_date=service_date,
        route_kind=route_kind,
        work_to_home_departure_time=work_to_home_departure_time,
    )

    request_rows = {
        "regular": [],
        "weekend": [],
        "extra": [],
    }
    requests = db.execute(
        select(TransportRequest, User)
        .join(User, User.id == TransportRequest.user_id)
        .where(TransportRequest.status == "active")
    ).all()

    request_kind_by_id = {
        transport_request.id: transport_request.request_kind
        for transport_request, _ in requests
    }
    request_ids = list(request_kind_by_id.keys())
    assignments = _list_transport_assignments_for_requests(db, request_ids=request_ids)
    explicit_assignments_by_key = {
        (assignment.request_id, assignment.service_date, assignment.route_kind): assignment
        for assignment in assignments
    }
    explicit_assignments_by_request_date: dict[tuple[int, date], TransportAssignment] = {}
    for assignment in assignments:
        lookup_key = (assignment.request_id, assignment.service_date)
        current_assignment = explicit_assignments_by_request_date.get(lookup_key)
        if current_assignment is None or _transport_dashboard_assignment_priority(assignment) > _transport_dashboard_assignment_priority(current_assignment):
            explicit_assignments_by_request_date[lookup_key] = assignment

    active_schedule_rows = _list_active_transport_schedule_rows(db)
    schedules_by_vehicle_id: dict[int, list[TransportVehicleSchedule]] = {}
    vehicles_by_id: dict[int, Vehicle] = {}
    for schedule, vehicle in active_schedule_rows:
        schedules_by_vehicle_id.setdefault(vehicle.id, []).append(schedule)
        vehicles_by_id[vehicle.id] = vehicle

    missing_vehicle_ids = {
        assignment.vehicle_id
        for assignment in assignments
        if assignment.vehicle_id is not None and assignment.vehicle_id not in vehicles_by_id
    }
    if missing_vehicle_ids:
        for vehicle in db.execute(select(Vehicle).where(Vehicle.id.in_(missing_vehicle_ids))).scalars().all():
            vehicles_by_id[vehicle.id] = vehicle
            schedules_by_vehicle_id.setdefault(vehicle.id, [])

    recurring_assignment_templates = _build_recurring_assignment_template_index(
        assignments=assignments,
        requests_by_id={transport_request.id: transport_request for transport_request, _ in requests},
        vehicles_by_id=vehicles_by_id,
        schedules_by_vehicle_id=schedules_by_vehicle_id,
    )
    vehicle_schedule_cache: dict[tuple[int, date, str], TransportVehicleSchedule | None] = {}

    def find_available_schedule_for_date(
        target_vehicle: Vehicle,
        target_service_date: date,
    ) -> TransportVehicleSchedule | None:
        cache_key = (target_vehicle.id, target_service_date, route_kind)
        if cache_key not in vehicle_schedule_cache:
            vehicle_schedule_cache[cache_key] = find_transport_vehicle_schedule(
                db,
                vehicle=target_vehicle,
                service_date=target_service_date,
                route_kind=route_kind,
            )
        return vehicle_schedule_cache[cache_key]

    for transport_request, user in requests:
        row_service_date = resolve_transport_request_dashboard_service_date(transport_request, service_date)
        if row_service_date is None:
            continue

        assigned_vehicle = None
        assignment_status = "pending"
        response_message = None
        awareness_status = "pending"
        assignment = explicit_assignments_by_key.get((transport_request.id, row_service_date, route_kind))
        if assignment is None and transport_request.request_kind == "extra":
            assignment = explicit_assignments_by_request_date.get((transport_request.id, row_service_date))
        if assignment is not None:
            assignment_status = assignment.status
            response_message = assignment.response_message
            awareness_status = "aware" if assignment.acknowledged_by_user else "pending"
            if assignment.vehicle_id is not None:
                explicit_vehicle = vehicles_by_id.get(assignment.vehicle_id)
                assigned_vehicle = vehicle_rows_by_assignment_key.get(
                    (
                        assignment.vehicle_id,
                        assignment.route_kind if transport_request.request_kind == "extra" else None,
                    )
                )
                if assigned_vehicle is None:
                    assigned_vehicle = vehicle_rows_by_id.get(assignment.vehicle_id)
                if assigned_vehicle is None and explicit_vehicle is not None:
                    assigned_vehicle = _build_vehicle_row(explicit_vehicle)
        elif transport_request.request_kind in {"regular", "weekend"}:
            recurring_assignment = recurring_assignment_templates.get((transport_request.id, row_service_date.weekday()))
            if recurring_assignment is not None:
                template_assignment, template_vehicle = recurring_assignment
                if find_available_schedule_for_date(template_vehicle, row_service_date) is not None:
                    assignment_status = "confirmed"
                    response_message = template_assignment.response_message
                    assigned_vehicle = (
                        vehicle_rows_by_assignment_key.get((template_vehicle.id, None))
                        or vehicle_rows_by_id.get(template_vehicle.id)
                        or _build_vehicle_row(template_vehicle)
                    )

        request_rows[transport_request.request_kind].append(
            TransportRequestRow(
                id=transport_request.id,
                request_kind=transport_request.request_kind,
                requested_time=transport_request.requested_time,
                service_date=row_service_date,
                user_id=user.id,
                chave=user.chave,
                nome=user.nome,
                projeto=user.projeto,
                workplace=user.workplace,
                end_rua=user.end_rua,
                zip=user.zip,
                assignment_status=assignment_status,
                awareness_status=awareness_status,
                assigned_vehicle=assigned_vehicle,
                response_message=response_message,
            )
        )

    for rows in request_rows.values():
        rows.sort(key=lambda item: (item.service_date, item.requested_time, item.nome.lower(), item.chave))

    vehicle_registry = _build_transport_vehicle_registry_rows(
        active_schedule_rows=active_schedule_rows,
        request_kind_by_id=request_kind_by_id,
        recurring_assignment_templates=recurring_assignment_templates,
        explicit_assignments=assignments,
        service_date=service_date,
        route_kind=route_kind,
        work_to_home_departure_time=work_to_home_departure_time,
    )

    return TransportDashboardResponse(
        selected_date=service_date,
        selected_route=route_kind,
        work_to_home_departure_time=work_to_home_departure_time,
        projects=projects,
        regular_requests=request_rows["regular"],
        weekend_requests=request_rows["weekend"],
        extra_requests=request_rows["extra"],
        regular_vehicles=vehicles_by_scope["regular"],
        weekend_vehicles=vehicles_by_scope["weekend"],
        extra_vehicles=vehicles_by_scope["extra"],
        regular_vehicle_registry=vehicle_registry["regular"],
        weekend_vehicle_registry=vehicle_registry["weekend"],
        extra_vehicle_registry=vehicle_registry["extra"],
        workplaces=workplaces,
    )