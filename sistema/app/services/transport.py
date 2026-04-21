from __future__ import annotations

import calendar
import json
from datetime import date, datetime, timedelta

from sqlalchemy import MetaData, Table, delete, inspect, select, update
from sqlalchemy.orm import Session

from ..models import (
    TransportAssignment,
    TransportRequest,
    TransportVehicleSchedule,
    TransportVehicleScheduleException,
    User,
    Vehicle,
    Workplace,
)
from ..schemas import (
    ProjectRow,
    TransportDashboardResponse,
    TransportRequestRow,
    TransportVehicleCreate,
    TransportVehicleManagementRow,
    TransportVehicleRow,
    WebTransportRequestItemResponse,
    WebTransportStateResponse,
    WorkplaceRow,
)
from .location_settings import (
    get_transport_last_update_time,
    get_transport_work_to_home_time,
    get_transport_work_to_home_time_for_date,
)
from .project_catalog import list_projects
from .time_utils import now_sgt


_REQUEST_KIND_TO_RECURRENCE = {
    "regular": "weekday",
    "weekend": "weekend",
    "extra": "single_date",
}
_REQUEST_KIND_TO_LABEL = {
    "regular": "REGULAR",
    "weekend": "WEEKEND",
    "extra": "EXTRA",
}
_SCOPE_KIND_TO_LABEL = {
    "regular": "Regular",
    "weekend": "Weekend",
    "extra": "Extra",
}
_ROUTE_KIND_TO_LABEL = {
    "home_to_work": "Home to Work",
    "work_to_home": "Work to Home",
}
_DEFAULT_REQUEST_SELECTED_WEEKDAYS = {
    "regular": (0, 1, 2, 3, 4),
    "weekend": (5, 6),
}
_PAIRED_ROUTE_KIND = {
    "home_to_work": "work_to_home",
    "work_to_home": "home_to_work",
}


def _resolve_web_transport_route_order(preferred_route_kind: str | None) -> list[str]:
    if preferred_route_kind in _ROUTE_KIND_TO_LABEL:
        return [preferred_route_kind] + [
            route_kind for route_kind in ("home_to_work", "work_to_home") if route_kind != preferred_route_kind
        ]
    return ["home_to_work", "work_to_home"]


def _normalize_request_selected_weekdays(selected_weekdays: list[int] | tuple[int, ...] | set[int] | None) -> tuple[int, ...]:
    if not selected_weekdays:
        return ()

    normalized: list[int] = []
    for item in selected_weekdays:
        if isinstance(item, bool):
            continue
        try:
            weekday = int(item)
        except (TypeError, ValueError):
            continue
        if 0 <= weekday <= 6:
            normalized.append(weekday)

    return tuple(sorted(dict.fromkeys(normalized)))


def _resolve_request_selected_weekdays(
    request_kind: str,
    selected_weekdays: list[int] | tuple[int, ...] | set[int] | None,
) -> tuple[int, ...]:
    normalized = _normalize_request_selected_weekdays(selected_weekdays)
    if normalized:
        return normalized
    return _DEFAULT_REQUEST_SELECTED_WEEKDAYS.get(request_kind, ())


def _serialize_request_selected_weekdays(selected_weekdays: tuple[int, ...]) -> str | None:
    if not selected_weekdays:
        return None
    return json.dumps(list(selected_weekdays), ensure_ascii=True, separators=(",", ":"))


def _parse_request_selected_weekdays(raw_value: str | None) -> tuple[int, ...]:
    normalized_raw_value = str(raw_value or "").strip()
    if not normalized_raw_value:
        return ()

    try:
        payload = json.loads(normalized_raw_value)
    except json.JSONDecodeError:
        return ()

    if not isinstance(payload, list):
        return ()

    return _normalize_request_selected_weekdays(payload)


def get_transport_request_selected_weekdays(transport_request: TransportRequest) -> set[int]:
    parsed_weekdays = _parse_request_selected_weekdays(transport_request.selected_weekdays_json)
    if parsed_weekdays:
        return set(parsed_weekdays)
    return set(_DEFAULT_REQUEST_SELECTED_WEEKDAYS.get(transport_request.request_kind, ()))


def _find_next_request_service_date(reference_date: date, selected_weekdays: set[int]) -> date | None:
    if not selected_weekdays:
        return None

    for day_offset in range(0, 7):
        candidate = reference_date + timedelta(days=day_offset)
        if candidate.weekday() in selected_weekdays:
            return candidate
    return None


def resolve_transport_request_dashboard_service_date(
    transport_request: TransportRequest,
    dashboard_service_date: date,
) -> date | None:
    if transport_request.status != "active":
        return None

    if request_applies_to_date(transport_request, dashboard_service_date):
        return dashboard_service_date

    if transport_request.request_kind == "regular":
        request_weekdays = get_transport_request_selected_weekdays(transport_request)
        if request_weekdays and dashboard_service_date.weekday() >= 5:
            return dashboard_service_date
        return _find_next_request_service_date(dashboard_service_date, request_weekdays)

    if transport_request.request_kind == "weekend":
        return _find_next_request_service_date(
            dashboard_service_date,
            get_transport_request_selected_weekdays(transport_request),
        )

    if transport_request.request_kind == "extra":
        return transport_request.single_date

    return None


def _resolve_web_transport_boarding_time(
    db: Session,
    *,
    active_request: TransportRequest,
    service_date: date,
    route_kind: str | None,
    vehicle: Vehicle | None,
) -> str:
    if route_kind == "work_to_home" and vehicle is not None and vehicle.service_scope in {"regular", "weekend"}:
        return get_transport_work_to_home_time_for_date(db, service_date=service_date)
    return active_request.requested_time


def _resolve_web_transport_confirmation_deadline_time(
    db: Session,
    *,
    user: User,
    active_request: TransportRequest,
) -> str:
    if user.checkin is True:
        return get_transport_last_update_time(db)
    return active_request.requested_time


def _resolve_web_transport_request_item_boarding_time(
    db: Session,
    *,
    transport_request: TransportRequest,
    service_date: date | None,
    boarding_time: str | None,
) -> str | None:
    if service_date is None:
        return boarding_time

    if transport_request.request_kind in {"regular", "weekend"}:
        return get_transport_work_to_home_time_for_date(db, service_date=service_date)

    return boarding_time


def _parse_transport_clock_time(value: str | None) -> tuple[int, int] | None:
    normalized_value = str(value or "").strip()
    if len(normalized_value) < 5:
        return None

    candidate = normalized_value[:5]
    try:
        parsed_time = datetime.strptime(candidate, "%H:%M")
    except ValueError:
        return None
    return parsed_time.hour, parsed_time.minute


def _is_web_transport_request_realized(
    *,
    request_status: str,
    service_date: date | None,
    departure_time: str | None,
    reference_datetime: datetime,
) -> bool:
    if request_status != "confirmed" or service_date is None:
        return False

    current_date = reference_datetime.date()
    if service_date < current_date:
        return True
    if service_date > current_date:
        return False

    parsed_departure = _parse_transport_clock_time(departure_time)
    if parsed_departure is None:
        return False

    departure_minutes = (parsed_departure[0] * 60) + parsed_departure[1]
    current_minutes = (reference_datetime.hour * 60) + reference_datetime.minute
    return departure_minutes <= current_minutes


def _resolve_vehicle_departure_time(
    *,
    route_kind: str,
    service_scope: str | None,
    work_to_home_departure_time: str,
    schedule: TransportVehicleSchedule | None = None,
) -> str | None:
    if service_scope == "extra" and schedule is not None:
        departure_time = str(schedule.departure_time or "").strip()
        return departure_time or None
    if route_kind != "work_to_home" or service_scope not in {"regular", "weekend"}:
        return None
    return work_to_home_departure_time


def build_transport_dashboard(
    db: Session,
    *,
    service_date: date,
    route_kind: str,
) -> TransportDashboardResponse:
    projects = [ProjectRow(id=row.id, name=row.name) for row in list_projects(db)]
    workplaces = list_workplaces(db)
    work_to_home_departure_time = get_transport_work_to_home_time_for_date(db, service_date=service_date)
    vehicles_by_scope, vehicle_rows_by_id = _build_vehicle_rows_for_dashboard(
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
        if assignment is not None:
            assignment_status = assignment.status
            response_message = assignment.response_message
            awareness_status = "aware" if assignment.acknowledged_by_user else "pending"
            if assignment.vehicle_id is not None:
                explicit_vehicle = vehicles_by_id.get(assignment.vehicle_id)
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
                    assigned_vehicle = vehicle_rows_by_id.get(template_vehicle.id) or _build_vehicle_row(template_vehicle)

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


def list_workplaces(db: Session) -> list[WorkplaceRow]:
    rows = db.execute(select(Workplace).order_by(Workplace.workplace, Workplace.id)).scalars().all()
    return [
        WorkplaceRow(
            id=row.id,
            workplace=row.workplace,
            address=row.address,
            zip=row.zip,
            country=row.country,
        )
        for row in rows
    ]


def request_applies_to_date(transport_request: TransportRequest, service_date: date) -> bool:
    if transport_request.status != "active":
        return False
    if transport_request.recurrence_kind in {"weekday", "weekend"}:
        return service_date.weekday() in get_transport_request_selected_weekdays(transport_request)
    return transport_request.single_date == service_date


def request_is_visible_on_service_date(transport_request: TransportRequest, service_date: date) -> bool:
    if request_applies_to_date(transport_request, service_date):
        return True

    return (
        transport_request.status == "active"
        and transport_request.request_kind == "regular"
        and bool(get_transport_request_selected_weekdays(transport_request))
        and service_date.weekday() >= 5
    )


def vehicle_schedule_applies_to_date(schedule: TransportVehicleSchedule, service_date: date) -> bool:
    if not schedule.is_active:
        return False
    if schedule.recurrence_kind == "weekday":
        return service_date.weekday() < 5
    if schedule.recurrence_kind == "matching_weekday":
        return schedule.weekday == service_date.weekday()
    return schedule.service_date == service_date


def create_transport_vehicle_registration(
    db: Session,
    *,
    payload: TransportVehicleCreate,
) -> tuple[Vehicle, list[TransportVehicleSchedule]]:
    timestamp = now_sgt()
    vehicle = db.execute(select(Vehicle).where(Vehicle.placa == payload.placa)).scalar_one_or_none()

    if vehicle is None:
        vehicle = Vehicle(
            placa=payload.placa,
            tipo=payload.tipo,
            color=payload.color,
            lugares=payload.lugares,
            tolerance=payload.tolerance,
            service_scope=payload.service_scope,
        )
        db.add(vehicle)
        db.flush()
    else:
        blocking_schedules, reusable_schedules = _classify_vehicle_schedules_for_reuse(
            db,
            vehicle_id=vehicle.id,
            reference_date=payload.service_date,
        )
        if not blocking_schedules:
            for schedule in reusable_schedules:
                schedule.is_active = False
                schedule.updated_at = timestamp

            vehicle.tipo = payload.tipo
            vehicle.color = payload.color
            vehicle.lugares = payload.lugares
            vehicle.tolerance = payload.tolerance
            vehicle.service_scope = payload.service_scope
        else:
            schedule_details = _build_vehicle_schedule_conflict_details(blocking_schedules)
            if vehicle.service_scope != payload.service_scope:
                raise ValueError(
                    f"A vehicle with this plate already exists in another list: {schedule_details}."
                )
            if (
                vehicle.tipo != payload.tipo
                or (vehicle.color or "") != payload.color
                or vehicle.lugares != payload.lugares
                or vehicle.tolerance != payload.tolerance
            ):
                raise ValueError(
                    "A vehicle with this plate already exists with a different configuration: "
                    f"{schedule_details}."
                )

    created_schedules: list[TransportVehicleSchedule] = []
    for schedule_spec in _build_schedule_specs_from_payload(payload):
        if _vehicle_has_active_schedule_for_spec(
            db,
            vehicle_id=vehicle.id,
            schedule_spec=schedule_spec,
        ):
            raise ValueError("An active vehicle already exists for the selected list and recurrence pattern.")

        schedule = TransportVehicleSchedule(
            vehicle_id=vehicle.id,
            service_scope=schedule_spec["service_scope"],
            route_kind=schedule_spec["route_kind"],
            recurrence_kind=schedule_spec["recurrence_kind"],
            service_date=schedule_spec["service_date"],
            weekday=schedule_spec["weekday"],
            departure_time=schedule_spec["departure_time"],
            is_active=True,
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(schedule)
        db.flush()
        created_schedules.append(schedule)

    return vehicle, created_schedules


def delete_transport_vehicle_registration(
    db: Session,
    *,
    schedule_id: int,
) -> Vehicle:
    schedule = db.get(TransportVehicleSchedule, schedule_id)
    if schedule is None:
        raise ValueError("Vehicle schedule not found.")

    vehicle = db.get(Vehicle, schedule.vehicle_id)
    if vehicle is None:
        raise ValueError("Vehicle not found.")

    schedule_ids = db.execute(
        select(TransportVehicleSchedule.id).where(TransportVehicleSchedule.vehicle_id == vehicle.id)
    ).scalars().all()
    assignment_ids = db.execute(
        select(TransportAssignment.id).where(TransportAssignment.vehicle_id == vehicle.id)
    ).scalars().all()

    if assignment_ids:
        _purge_foreign_key_dependencies(
            db,
            target_table="transport_assignments",
            target_column="id",
            values=assignment_ids,
            mode="delete",
        )

        assignments = db.execute(
            select(TransportAssignment).where(TransportAssignment.id.in_(assignment_ids))
        ).scalars().all()
        for assignment in assignments:
            db.delete(assignment)

    if schedule_ids:
        _purge_foreign_key_dependencies(
            db,
            target_table="transport_vehicle_schedules",
            target_column="id",
            values=schedule_ids,
            mode="delete",
            excluded_tables={"transport_vehicle_schedule_exceptions"},
        )

        schedule_exceptions = db.execute(
            select(TransportVehicleScheduleException).where(
                TransportVehicleScheduleException.vehicle_schedule_id.in_(schedule_ids)
            )
        ).scalars().all()
        for schedule_exception in schedule_exceptions:
            db.delete(schedule_exception)

        schedules = db.execute(
            select(TransportVehicleSchedule).where(TransportVehicleSchedule.id.in_(schedule_ids))
        ).scalars().all()
        for vehicle_schedule in schedules:
            db.delete(vehicle_schedule)

    _purge_foreign_key_dependencies(
        db,
        target_table="vehicles",
        target_column="placa",
        values=[vehicle.placa],
        mode="set_null",
    )

    linked_users = db.execute(
        select(User).where(User.placa == vehicle.placa)
    ).scalars().all()
    for linked_user in linked_users:
        linked_user.placa = None

    _purge_foreign_key_dependencies(
        db,
        target_table="vehicles",
        target_column="id",
        values=[vehicle.id],
        mode="delete",
        excluded_tables={"transport_vehicle_schedules", "transport_assignments"},
    )

    db.delete(vehicle)
    return vehicle


def _purge_foreign_key_dependencies(
    db: Session,
    *,
    target_table: str,
    target_column: str,
    values: list[object],
    mode: str,
    excluded_tables: set[str] | None = None,
) -> None:
    if not values:
        return

    bind = db.get_bind()
    if bind is None:
        return

    inspector = inspect(bind)
    metadata = MetaData()
    skip_tables = set(excluded_tables or set())
    normalized_values = list(dict.fromkeys(values))

    for table_name in inspector.get_table_names():
        if table_name == target_table or table_name in skip_tables:
            continue

        nullable_by_column = {
            column["name"]: column.get("nullable", True)
            for column in inspector.get_columns(table_name)
        }
        matched_columns: list[tuple[str, bool]] = []
        for foreign_key in inspector.get_foreign_keys(table_name):
            constrained_columns = foreign_key.get("constrained_columns") or []
            referred_columns = foreign_key.get("referred_columns") or []
            if foreign_key.get("referred_table") != target_table:
                continue
            if len(constrained_columns) != 1 or len(referred_columns) != 1:
                continue
            if referred_columns[0] != target_column:
                continue
            column_name = constrained_columns[0]
            matched_columns.append((column_name, nullable_by_column.get(column_name, True)))

        if not matched_columns:
            continue

        reflected_table = Table(table_name, metadata, autoload_with=bind)
        for column_name, nullable in matched_columns:
            target = reflected_table.c[column_name]
            if mode == "set_null" and nullable:
                db.execute(
                    update(reflected_table)
                    .where(target.in_(normalized_values))
                    .values({column_name: None})
                )
                continue

            db.execute(delete(reflected_table).where(target.in_(normalized_values)))


def upsert_transport_request(
    db: Session,
    *,
    user: User,
    request_kind: str,
    requested_time: str,
    requested_date: date | None,
    created_via: str,
    selected_weekdays: list[int] | tuple[int, ...] | set[int] | None = None,
) -> tuple[TransportRequest, bool]:
    timestamp = now_sgt()
    recurrence_kind = _REQUEST_KIND_TO_RECURRENCE[request_kind]
    resolved_selected_weekdays = _resolve_request_selected_weekdays(request_kind, selected_weekdays)
    selected_weekdays_json = _serialize_request_selected_weekdays(resolved_selected_weekdays)

    existing_requests = db.execute(
        select(TransportRequest)
        .where(
            TransportRequest.user_id == user.id,
            TransportRequest.request_kind == request_kind,
            TransportRequest.status == "active",
        )
        .order_by(TransportRequest.created_at.desc(), TransportRequest.id.desc())
    ).scalars().all()

    if request_kind == "extra":
        for existing in existing_requests:
            if existing.single_date == requested_date and existing.requested_time == requested_time:
                return existing, False
    else:
        for existing in existing_requests:
            if (
                existing.requested_time == requested_time
                and existing.recurrence_kind == recurrence_kind
                and get_transport_request_selected_weekdays(existing) == set(resolved_selected_weekdays)
            ):
                return existing, False

    if request_kind != "extra":
        for existing in existing_requests:
            _close_transport_request_assignments(
                db,
                transport_request=existing,
                timestamp=timestamp,
                assignment_status="cancelled",
                response_message="Cancelled by newer transport request",
            )

    transport_request = TransportRequest(
        user_id=user.id,
        request_kind=request_kind,
        recurrence_kind=recurrence_kind,
        requested_time=requested_time,
        selected_weekdays_json=selected_weekdays_json,
        single_date=requested_date,
        created_via=created_via,
        status="active",
        created_at=timestamp,
        updated_at=timestamp,
        cancelled_at=None,
    )
    db.add(transport_request)
    db.flush()
    return transport_request, True


def get_latest_active_transport_request(
    db: Session,
    *,
    user: User,
    request_kind: str,
) -> TransportRequest | None:
    return db.execute(
        select(TransportRequest)
        .where(
            TransportRequest.user_id == user.id,
            TransportRequest.request_kind == request_kind,
            TransportRequest.status == "active",
        )
        .order_by(TransportRequest.updated_at.desc(), TransportRequest.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def cancel_transport_requests(db: Session, *, user: User, request_kind: str, reference_date: date) -> int:
    timestamp = now_sgt()
    requests = db.execute(
        select(TransportRequest)
        .where(
            TransportRequest.user_id == user.id,
            TransportRequest.request_kind == request_kind,
            TransportRequest.status == "active",
        )
        .order_by(TransportRequest.id.desc())
    ).scalars().all()
    cancelled = 0
    for transport_request in requests:
        if request_kind == "extra" and transport_request.single_date is not None and transport_request.single_date < reference_date:
            continue
        _close_transport_request_assignments(
            db,
            transport_request=transport_request,
            timestamp=timestamp,
            assignment_status="cancelled",
            response_message="Cancelled by user",
        )
        cancelled += 1
    return cancelled


def _close_transport_request(transport_request: TransportRequest, *, timestamp) -> None:
    transport_request.status = "cancelled"
    transport_request.cancelled_at = timestamp
    transport_request.updated_at = timestamp


def _resolve_transport_assignment(
    assignment: TransportAssignment,
    *,
    status: str,
    response_message: str | None,
    timestamp,
    admin_user_id: int | None,
) -> None:
    assignment.vehicle_id = None
    assignment.status = status
    assignment.response_message = response_message
    assignment.acknowledged_by_user = False
    assignment.acknowledged_at = None
    assignment.updated_at = timestamp
    assignment.notified_at = None
    if admin_user_id is not None:
        assignment.assigned_by_admin_id = admin_user_id


def _close_transport_request_assignments(
    db: Session,
    *,
    transport_request: TransportRequest,
    timestamp,
    assignment_status: str,
    response_message: str | None,
    admin_user_id: int | None = None,
) -> list[TransportAssignment]:
    _close_transport_request(transport_request, timestamp=timestamp)

    assignments = db.execute(
        select(TransportAssignment).where(TransportAssignment.request_id == transport_request.id)
    ).scalars().all()
    for assignment in assignments:
        _resolve_transport_assignment(
            assignment,
            status=assignment_status,
            response_message=response_message,
            timestamp=timestamp,
            admin_user_id=admin_user_id,
        )
    return assignments


def cancel_transport_request_and_assignments(
    db: Session,
    *,
    transport_request: TransportRequest,
) -> None:
    timestamp = now_sgt()
    _close_transport_request_assignments(
        db,
        transport_request=transport_request,
        timestamp=timestamp,
        assignment_status="cancelled",
        response_message="Cancelled by web user",
    )


def reject_transport_request_and_assignments(
    db: Session,
    *,
    transport_request: TransportRequest,
    service_date: date,
    route_kind: str,
    response_message: str | None = None,
    admin_user_id: int | None = None,
) -> tuple[TransportAssignment, bool]:
    timestamp = now_sgt()
    resolved_response_message = response_message or "Rejected by transport admin"
    assignments = _close_transport_request_assignments(
        db,
        transport_request=transport_request,
        timestamp=timestamp,
        assignment_status="rejected",
        response_message=resolved_response_message,
        admin_user_id=admin_user_id,
    )

    target_assignment = next(
        (
            assignment
            for assignment in assignments
            if assignment.service_date == service_date and assignment.route_kind == route_kind
        ),
        None,
    )
    if target_assignment is not None:
        return target_assignment, True

    target_assignment = TransportAssignment(
        request_id=transport_request.id,
        service_date=service_date,
        route_kind=route_kind,
        vehicle_id=None,
        status="rejected",
        response_message=resolved_response_message,
        acknowledged_by_user=False,
        acknowledged_at=None,
        assigned_by_admin_id=admin_user_id,
        created_at=timestamp,
        updated_at=timestamp,
        notified_at=None,
    )
    db.add(target_assignment)
    db.flush()
    return target_assignment, False


def acknowledge_transport_assignments(
    db: Session,
    *,
    transport_request: TransportRequest,
    service_date: date,
) -> int:
    _materialize_recurring_assignments_for_date(
        db,
        transport_request=transport_request,
        service_date=service_date,
    )
    timestamp = now_sgt()
    assignments = db.execute(
        select(TransportAssignment).where(
            TransportAssignment.request_id == transport_request.id,
            TransportAssignment.service_date == service_date,
            TransportAssignment.status == "confirmed",
            TransportAssignment.vehicle_id.is_not(None),
        )
    ).scalars().all()
    acknowledged = 0
    for assignment in assignments:
        assignment.acknowledged_by_user = True
        assignment.acknowledged_at = timestamp
        assignment.updated_at = timestamp
        acknowledged += 1
    return acknowledged


def _resolve_transport_request_reference_service_date(
    transport_request: TransportRequest,
    *,
    reference_date: date,
) -> date | None:
    if transport_request.request_kind == "extra":
        return transport_request.single_date

    return _find_next_request_service_date(
        reference_date,
        get_transport_request_selected_weekdays(transport_request),
    )


def _build_web_transport_request_items(
    db: Session,
    *,
    user: User,
    service_date: date,
    preferred_route_kind: str | None,
) -> list[WebTransportRequestItemResponse]:
    reference_datetime = now_sgt()
    transport_requests = db.execute(
        select(TransportRequest)
        .where(TransportRequest.user_id == user.id)
        .order_by(TransportRequest.created_at.desc(), TransportRequest.id.desc())
    ).scalars().all()
    if not transport_requests:
        return []

    request_ids = [transport_request.id for transport_request in transport_requests]
    requests_by_id = {transport_request.id: transport_request for transport_request in transport_requests}
    assignments = _list_transport_assignments_for_requests(db, request_ids=request_ids)
    assignments_by_request_id: dict[int, list[TransportAssignment]] = {}
    explicit_assignments_by_key: dict[tuple[int, date, str], TransportAssignment] = {}
    for assignment in assignments:
        assignments_by_request_id.setdefault(assignment.request_id, []).append(assignment)
        explicit_assignments_by_key[(assignment.request_id, assignment.service_date, assignment.route_kind)] = assignment

    vehicle_ids = {assignment.vehicle_id for assignment in assignments if assignment.vehicle_id is not None}
    vehicles_by_id = {
        vehicle.id: vehicle
        for vehicle in db.execute(select(Vehicle).where(Vehicle.id.in_(vehicle_ids))).scalars().all()
    } if vehicle_ids else {}
    schedules_by_vehicle_id = _load_active_schedules_by_vehicle_id(db, vehicle_ids=vehicle_ids)
    recurring_assignment_templates = _build_recurring_assignment_template_index(
        assignments=assignments,
        requests_by_id=requests_by_id,
        vehicles_by_id=vehicles_by_id,
        schedules_by_vehicle_id=schedules_by_vehicle_id,
    )
    route_order = _resolve_web_transport_route_order(preferred_route_kind)

    request_items: list[WebTransportRequestItemResponse] = []
    for transport_request in transport_requests:
        selected_weekdays = sorted(get_transport_request_selected_weekdays(transport_request))
        request_assignments = assignments_by_request_id.get(transport_request.id, [])
        latest_assignment = max(
            request_assignments,
            key=lambda assignment: (assignment.updated_at, assignment.id),
            default=None,
        )
        item_service_date = _resolve_transport_request_reference_service_date(
            transport_request,
            reference_date=service_date,
        )
        resolved_route_kind = latest_assignment.route_kind if latest_assignment is not None else (
            preferred_route_kind if preferred_route_kind in _ROUTE_KIND_TO_LABEL else None
        )
        response_message = latest_assignment.response_message if latest_assignment is not None else None
        boarding_time = None
        vehicle_type = None
        vehicle_plate = None
        vehicle_color = None
        tolerance_minutes = None
        awareness_required = False
        awareness_confirmed = False
        confirmation_deadline_time = None

        if transport_request.status == "active":
            request_status = "pending"
            confirmation_deadline_time = _resolve_web_transport_confirmation_deadline_time(
                db,
                user=user,
                active_request=transport_request,
            )
            confirmed_assignments: list[tuple[TransportAssignment, Vehicle, bool, str]] = []
            rejected_assignment = None
            cancelled_assignment = None
            if item_service_date is not None:
                for target_route_kind in route_order:
                    assignment = explicit_assignments_by_key.get((transport_request.id, item_service_date, target_route_kind))
                    if assignment is not None:
                        if assignment.status == "confirmed" and assignment.vehicle_id is not None:
                            confirmed_vehicle = vehicles_by_id.get(assignment.vehicle_id)
                            if confirmed_vehicle is not None:
                                confirmed_assignments.append((assignment, confirmed_vehicle, False, target_route_kind))
                        elif assignment.status == "rejected" and rejected_assignment is None:
                            rejected_assignment = (assignment, target_route_kind)
                        elif assignment.status == "cancelled" and cancelled_assignment is None:
                            cancelled_assignment = (assignment, target_route_kind)
                        continue

                    recurring_assignment = recurring_assignment_templates.get((transport_request.id, item_service_date.weekday()))
                    if recurring_assignment is None:
                        continue

                    template_assignment, template_vehicle = recurring_assignment
                    if find_transport_vehicle_schedule(
                        db,
                        vehicle=template_vehicle,
                        service_date=item_service_date,
                        route_kind=target_route_kind,
                    ) is None:
                        continue
                    confirmed_assignments.append((template_assignment, template_vehicle, True, target_route_kind))

            if confirmed_assignments:
                confirmed_assignment = confirmed_assignments[0][0]
                confirmed_vehicle = confirmed_assignments[0][1]
                resolved_route_kind = confirmed_assignments[0][3]
                boarding_time = _resolve_web_transport_boarding_time(
                    db,
                    active_request=transport_request,
                    service_date=item_service_date or service_date,
                    route_kind=resolved_route_kind,
                    vehicle=confirmed_vehicle,
                )
                vehicle_type = confirmed_vehicle.tipo
                vehicle_plate = confirmed_vehicle.placa
                vehicle_color = confirmed_vehicle.color
                tolerance_minutes = confirmed_vehicle.tolerance
                awareness_required = True
                awareness_confirmed = all(
                    (not is_synthetic) and assignment.acknowledged_by_user
                    for assignment, _, is_synthetic, _ in confirmed_assignments
                )
                response_message = confirmed_assignment.response_message
                request_status = "confirmed"
            elif rejected_assignment is not None:
                response_message = rejected_assignment[0].response_message
                resolved_route_kind = rejected_assignment[1]
                request_status = "rejected"
            elif cancelled_assignment is not None:
                response_message = cancelled_assignment[0].response_message
                resolved_route_kind = cancelled_assignment[1]
                request_status = "cancelled"
        else:
            request_status = "cancelled"

        boarding_time = _resolve_web_transport_request_item_boarding_time(
            db,
            transport_request=transport_request,
            service_date=item_service_date,
            boarding_time=boarding_time,
        )
        if _is_web_transport_request_realized(
            request_status=request_status,
            service_date=item_service_date,
            departure_time=boarding_time or transport_request.requested_time,
            reference_datetime=reference_datetime,
        ):
            request_status = "realized"

        request_items.append(
            WebTransportRequestItemResponse(
                request_id=transport_request.id,
                request_kind=transport_request.request_kind,
                status=request_status,
                is_active=transport_request.status == "active",
                service_date=item_service_date,
                requested_time=transport_request.requested_time,
                selected_weekdays=selected_weekdays,
                route_kind=resolved_route_kind,
                boarding_time=boarding_time,
                confirmation_deadline_time=confirmation_deadline_time,
                vehicle_type=vehicle_type,
                vehicle_plate=vehicle_plate,
                vehicle_color=vehicle_color,
                tolerance_minutes=tolerance_minutes,
                awareness_required=awareness_required,
                awareness_confirmed=awareness_confirmed,
                response_message=response_message,
                created_at=transport_request.created_at,
            )
        )

    return request_items

def build_web_transport_state(
    db: Session,
    *,
    user: User,
    service_date: date,
    preferred_route_kind: str | None = None,
) -> WebTransportStateResponse:
    request_items = _build_web_transport_request_items(
        db,
        user=user,
        service_date=service_date,
        preferred_route_kind=preferred_route_kind,
    )
    active_requests = db.execute(
        select(TransportRequest)
        .where(
            TransportRequest.user_id == user.id,
            TransportRequest.status == "active",
        )
        .order_by(TransportRequest.updated_at.desc(), TransportRequest.id.desc())
    ).scalars().all()
    active_request = next(
        (candidate for candidate in active_requests if request_is_visible_on_service_date(candidate, service_date)),
        active_requests[0] if active_requests else None,
    )
    if active_request is None:
        return WebTransportStateResponse(
            chave=user.chave,
            end_rua=user.end_rua,
            zip=user.zip,
            status="available",
            requests=request_items,
        )

    assignments = _list_transport_assignments_for_requests(db, request_ids=[active_request.id])
    explicit_assignments_by_key = {
        (assignment.request_id, assignment.service_date, assignment.route_kind): assignment
        for assignment in assignments
    }
    vehicle_ids = {assignment.vehicle_id for assignment in assignments if assignment.vehicle_id is not None}
    vehicles_by_id = {
        vehicle.id: vehicle
        for vehicle in db.execute(select(Vehicle).where(Vehicle.id.in_(vehicle_ids))).scalars().all()
    } if vehicle_ids else {}
    schedules_by_vehicle_id = _load_active_schedules_by_vehicle_id(db, vehicle_ids=vehicle_ids)
    recurring_assignment_templates = _build_recurring_assignment_template_index(
        assignments=assignments,
        requests_by_id={active_request.id: active_request},
        vehicles_by_id=vehicles_by_id,
        schedules_by_vehicle_id=schedules_by_vehicle_id,
    )

    route_order = _resolve_web_transport_route_order(preferred_route_kind)
    confirmed_assignments: list[tuple[TransportAssignment, Vehicle, bool, str]] = []
    for target_route_kind in route_order:
        assignment = explicit_assignments_by_key.get((active_request.id, service_date, target_route_kind))
        if assignment is not None:
            if assignment.status == "confirmed" and assignment.vehicle_id is not None:
                confirmed_vehicle = vehicles_by_id.get(assignment.vehicle_id)
                if confirmed_vehicle is not None:
                    confirmed_assignments.append((assignment, confirmed_vehicle, False, target_route_kind))
            continue

        recurring_assignment = recurring_assignment_templates.get((active_request.id, service_date.weekday()))
        if recurring_assignment is None:
            continue

        template_assignment, template_vehicle = recurring_assignment
        if find_transport_vehicle_schedule(
            db,
            vehicle=template_vehicle,
            service_date=service_date,
            route_kind=target_route_kind,
        ) is None:
            continue
        confirmed_assignments.append((template_assignment, template_vehicle, True, target_route_kind))

    confirmed_assignment = confirmed_assignments[0][0] if confirmed_assignments else None
    confirmed_vehicle = confirmed_assignments[0][1] if confirmed_assignments else None
    resolved_route_kind = confirmed_assignments[0][3] if confirmed_assignments else (
        preferred_route_kind if preferred_route_kind in _ROUTE_KIND_TO_LABEL else None
    )
    confirmation_deadline_time = _resolve_web_transport_confirmation_deadline_time(
        db,
        user=user,
        active_request=active_request,
    )
    awareness_confirmed = bool(confirmed_assignments) and all(
        (not is_synthetic) and assignment.acknowledged_by_user
        for assignment, _, is_synthetic, _ in confirmed_assignments
    )

    if confirmed_assignment is not None and confirmed_vehicle is not None:
        boarding_time = _resolve_web_transport_boarding_time(
            db,
            active_request=active_request,
            service_date=service_date,
            route_kind=resolved_route_kind,
            vehicle=confirmed_vehicle,
        )
        resolved_status = "realized" if _is_web_transport_request_realized(
            request_status="confirmed",
            service_date=service_date,
            departure_time=boarding_time or active_request.requested_time,
            reference_datetime=now_sgt(),
        ) else "confirmed"
        return WebTransportStateResponse(
            chave=user.chave,
            end_rua=user.end_rua,
            zip=user.zip,
            status=resolved_status,
            request_id=active_request.id,
            request_kind=active_request.request_kind,
            route_kind=resolved_route_kind,
            service_date=service_date,
            requested_time=active_request.requested_time,
            boarding_time=boarding_time,
            confirmation_deadline_time=confirmation_deadline_time,
            vehicle_type=confirmed_vehicle.tipo,
            vehicle_plate=confirmed_vehicle.placa,
            vehicle_color=confirmed_vehicle.color,
            tolerance_minutes=confirmed_vehicle.tolerance,
            awareness_required=True,
            awareness_confirmed=awareness_confirmed,
            requests=request_items,
        )

    return WebTransportStateResponse(
        chave=user.chave,
        end_rua=user.end_rua,
        zip=user.zip,
        status="pending",
        request_id=active_request.id,
        request_kind=active_request.request_kind,
        route_kind=resolved_route_kind,
        service_date=service_date,
        requested_time=active_request.requested_time,
        confirmation_deadline_time=confirmation_deadline_time,
        awareness_required=False,
        awareness_confirmed=False,
        requests=request_items,
    )


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
    timestamp = now_sgt()
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
    timestamp = now_sgt()
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
    timestamp = now_sgt()
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


def _list_transport_assignments_for_requests(
    db: Session,
    *,
    request_ids: list[int],
) -> list[TransportAssignment]:
    if not request_ids:
        return []
    return db.execute(
        select(TransportAssignment).where(TransportAssignment.request_id.in_(request_ids))
    ).scalars().all()


def _list_active_transport_schedule_rows(
    db: Session,
) -> list[tuple[TransportVehicleSchedule, Vehicle]]:
    return db.execute(
        select(TransportVehicleSchedule, Vehicle)
        .join(Vehicle, Vehicle.id == TransportVehicleSchedule.vehicle_id)
        .where(TransportVehicleSchedule.is_active.is_(True))
        .order_by(TransportVehicleSchedule.service_scope, Vehicle.placa, TransportVehicleSchedule.id)
    ).all()


def _load_active_schedules_by_vehicle_id(
    db: Session,
    *,
    vehicle_ids: set[int],
) -> dict[int, list[TransportVehicleSchedule]]:
    if not vehicle_ids:
        return {}

    schedules = db.execute(
        select(TransportVehicleSchedule).where(
            TransportVehicleSchedule.vehicle_id.in_(vehicle_ids),
            TransportVehicleSchedule.is_active.is_(True),
        )
    ).scalars().all()
    schedules_by_vehicle_id: dict[int, list[TransportVehicleSchedule]] = {}
    for schedule in schedules:
        schedules_by_vehicle_id.setdefault(schedule.vehicle_id, []).append(schedule)
    return schedules_by_vehicle_id


def _resolve_assignment_template_weekdays(
    *,
    transport_request: TransportRequest | None,
    vehicle: Vehicle,
    schedules: list[TransportVehicleSchedule],
    reference_date: date,
) -> set[int]:
    target_weekdays: set[int]
    if vehicle.service_scope == "regular":
        target_weekdays = {0, 1, 2, 3, 4}
    elif vehicle.service_scope == "weekend":
        matching_weekdays = {
            schedule.weekday
            for schedule in schedules
            if schedule.service_scope == "weekend"
            and schedule.recurrence_kind == "matching_weekday"
            and schedule.weekday is not None
        }
        if matching_weekdays:
            target_weekdays = matching_weekdays
        elif reference_date.weekday() >= 5:
            target_weekdays = {reference_date.weekday()}
        else:
            target_weekdays = set()
    else:
        target_weekdays = set()

    if transport_request is None or transport_request.request_kind not in {"regular", "weekend"}:
        return target_weekdays

    request_weekdays = get_transport_request_selected_weekdays(transport_request)
    if not request_weekdays:
        return target_weekdays
    if not target_weekdays:
        return request_weekdays
    return target_weekdays & request_weekdays


def _build_recurring_assignment_template_index(
    *,
    assignments: list[TransportAssignment],
    requests_by_id: dict[int, TransportRequest],
    vehicles_by_id: dict[int, Vehicle],
    schedules_by_vehicle_id: dict[int, list[TransportVehicleSchedule]],
) -> dict[tuple[int, int], tuple[TransportAssignment, Vehicle]]:
    recurring_assignment_templates: dict[tuple[int, int], tuple[TransportAssignment, Vehicle]] = {}

    for assignment in sorted(assignments, key=lambda row: (row.updated_at, row.id), reverse=True):
        if assignment.status != "confirmed" or assignment.vehicle_id is None:
            continue

        transport_request = requests_by_id.get(assignment.request_id)
        request_kind = transport_request.request_kind if transport_request is not None else None
        vehicle = vehicles_by_id.get(assignment.vehicle_id)
        if request_kind not in {"regular", "weekend"} or vehicle is None:
            continue
        if vehicle.service_scope != request_kind:
            continue

        target_weekdays = _resolve_assignment_template_weekdays(
            transport_request=transport_request,
            vehicle=vehicle,
            schedules=schedules_by_vehicle_id.get(vehicle.id, []),
            reference_date=assignment.service_date,
        )
        for weekday in target_weekdays:
            recurring_assignment_templates.setdefault((assignment.request_id, weekday), (assignment, vehicle))

    return recurring_assignment_templates


def _build_transport_vehicle_registry_rows(
    *,
    active_schedule_rows: list[tuple[TransportVehicleSchedule, Vehicle]],
    request_kind_by_id: dict[int, str],
    recurring_assignment_templates: dict[tuple[int, int], tuple[TransportAssignment, Vehicle]],
    explicit_assignments: list[TransportAssignment],
    route_kind: str,
    work_to_home_departure_time: str,
) -> dict[str, list[TransportVehicleManagementRow]]:
    registry_rows: dict[str, list[TransportVehicleManagementRow]] = {
        "regular": [],
        "weekend": [],
        "extra": [],
    }

    assigned_request_ids_by_vehicle_id: dict[str, dict[int, set[int]]] = {
        "regular": {},
        "weekend": {},
    }
    for (request_id, _weekday), (_assignment, vehicle) in recurring_assignment_templates.items():
        request_kind = request_kind_by_id.get(request_id)
        if request_kind not in {"regular", "weekend"}:
            continue
        assigned_request_ids_by_vehicle_id.setdefault(request_kind, {}).setdefault(vehicle.id, set()).add(request_id)

    extra_assigned_request_ids_by_schedule_key: dict[tuple[int, date, str], set[int]] = {}
    for assignment in explicit_assignments:
        if assignment.status != "confirmed" or assignment.vehicle_id is None:
            continue
        if request_kind_by_id.get(assignment.request_id) != "extra":
            continue
        schedule_key = (assignment.vehicle_id, assignment.service_date, assignment.route_kind)
        extra_assigned_request_ids_by_schedule_key.setdefault(schedule_key, set()).add(assignment.request_id)

    registry_rows_by_vehicle_id: dict[str, dict[int, TransportVehicleManagementRow]] = {
        "regular": {},
        "weekend": {},
    }
    for schedule, vehicle in active_schedule_rows:
        if schedule.service_scope in {"regular", "weekend"}:
            existing_row = registry_rows_by_vehicle_id[schedule.service_scope].get(vehicle.id)
            if existing_row is None:
                registry_rows_by_vehicle_id[schedule.service_scope][vehicle.id] = TransportVehicleManagementRow(
                    vehicle_id=vehicle.id,
                    schedule_id=schedule.id,
                    placa=vehicle.placa,
                    tipo=vehicle.tipo,
                    lugares=vehicle.lugares,
                    departure_time=_resolve_vehicle_departure_time(
                        route_kind=route_kind,
                        service_scope=schedule.service_scope,
                        work_to_home_departure_time=work_to_home_departure_time,
                        schedule=schedule,
                    ),
                    assigned_count=len(
                        assigned_request_ids_by_vehicle_id.get(schedule.service_scope, {}).get(vehicle.id, set())
                    ),
                )
            continue

        if schedule.service_scope != "extra":
            continue

        schedule_key = (
            vehicle.id,
            schedule.service_date,
            schedule.route_kind,
        )
        registry_rows["extra"].append(
            TransportVehicleManagementRow(
                vehicle_id=vehicle.id,
                schedule_id=schedule.id,
                placa=vehicle.placa,
                tipo=vehicle.tipo,
                lugares=vehicle.lugares,
                assigned_count=len(extra_assigned_request_ids_by_schedule_key.get(schedule_key, set())),
                service_date=schedule.service_date,
                route_kind=schedule.route_kind,
                departure_time=_resolve_vehicle_departure_time(
                    route_kind=schedule.route_kind,
                    service_scope=schedule.service_scope,
                    work_to_home_departure_time=work_to_home_departure_time,
                    schedule=schedule,
                ),
            )
        )

    for scope in ("regular", "weekend"):
        registry_rows[scope] = sorted(
            registry_rows_by_vehicle_id[scope].values(),
            key=lambda row: (row.placa, row.vehicle_id),
        )

    registry_rows["extra"].sort(
        key=lambda row: (
            row.service_date or date.min,
            row.route_kind or "",
            row.placa,
            row.schedule_id or 0,
        )
    )
    return registry_rows


def _build_vehicle_row(vehicle: Vehicle) -> TransportVehicleRow:
    return _build_vehicle_row_for_schedule(vehicle, schedule=None)


def _build_vehicle_row_for_schedule(
    vehicle: Vehicle,
    *,
    schedule: TransportVehicleSchedule | None,
    departure_time: str | None = None,
) -> TransportVehicleRow:
    return TransportVehicleRow(
        id=vehicle.id,
        schedule_id=(schedule.id if schedule is not None else None),
        placa=vehicle.placa,
        tipo=vehicle.tipo,
        color=vehicle.color,
        lugares=vehicle.lugares,
        tolerance=vehicle.tolerance,
        service_scope=vehicle.service_scope,
        route_kind=(schedule.route_kind if schedule is not None else None),
        departure_time=departure_time,
    )


def _build_vehicle_rows_for_dashboard(
    db: Session,
    *,
    service_date: date,
    route_kind: str,
    work_to_home_departure_time: str,
) -> tuple[dict[str, list[TransportVehicleRow]], dict[int, TransportVehicleRow]]:
    vehicles_by_scope: dict[str, list[TransportVehicleRow]] = {
        "regular": [],
        "weekend": [],
        "extra": [],
    }
    vehicle_rows_by_id: dict[int, TransportVehicleRow] = {}

    schedule_rows = db.execute(
        select(TransportVehicleSchedule, Vehicle)
        .join(Vehicle, Vehicle.id == TransportVehicleSchedule.vehicle_id)
        .where(TransportVehicleSchedule.is_active.is_(True))
        .order_by(TransportVehicleSchedule.service_scope, Vehicle.placa, TransportVehicleSchedule.id)
    ).all()
    schedule_ids = [schedule.id for schedule, _ in schedule_rows]
    exception_schedule_ids = {
        row.vehicle_schedule_id
        for row in db.execute(
            select(TransportVehicleScheduleException).where(
                TransportVehicleScheduleException.vehicle_schedule_id.in_(schedule_ids),
                TransportVehicleScheduleException.service_date == service_date,
            )
        ).scalars().all()
    } if schedule_ids else set()

    for schedule, vehicle in schedule_rows:
        if schedule.id in exception_schedule_ids:
            continue
        if not vehicle_schedule_applies_to_date(schedule, service_date):
            continue
        if schedule.service_scope != "extra" and schedule.route_kind != route_kind:
            continue

        vehicle_row = _build_vehicle_row_for_schedule(
            vehicle,
            schedule=schedule,
            departure_time=_resolve_vehicle_departure_time(
                route_kind=route_kind,
                service_scope=schedule.service_scope,
                work_to_home_departure_time=work_to_home_departure_time,
                schedule=schedule,
            ),
        )
        vehicles_by_scope.setdefault(schedule.service_scope, []).append(vehicle_row)
        vehicle_rows_by_id[vehicle.id] = vehicle_row

    for rows in vehicles_by_scope.values():
        rows.sort(key=lambda item: (item.placa, item.id))

    return vehicles_by_scope, vehicle_rows_by_id


def _build_schedule_specs_from_payload(payload: TransportVehicleCreate) -> list[dict[str, object]]:
    if payload.service_scope == "extra":
        return [
            {
                "service_scope": payload.service_scope,
                "route_kind": payload.route_kind,
                "recurrence_kind": "single_date",
                "service_date": payload.service_date,
                "weekday": None,
                "departure_time": payload.departure_time,
            }
        ]

    route_kinds = ["home_to_work", "work_to_home"]
    if payload.service_scope == "weekend":
        selected_weekdays: list[int] = []
        if payload.every_saturday:
            selected_weekdays.append(5)
        if payload.every_sunday:
            selected_weekdays.append(6)
        return [
            {
                "service_scope": payload.service_scope,
                "route_kind": route_kind,
                "recurrence_kind": "matching_weekday",
                "service_date": None,
                "weekday": weekday,
                "departure_time": None,
            }
            for weekday in selected_weekdays
            for route_kind in route_kinds
        ]

    return [
        {
            "service_scope": payload.service_scope,
            "route_kind": route_kind,
            "recurrence_kind": "weekday",
            "service_date": None,
            "weekday": None,
            "departure_time": None,
        }
        for route_kind in route_kinds
    ]


def _classify_vehicle_schedules_for_reuse(
    db: Session,
    *,
    vehicle_id: int,
    reference_date: date,
) -> tuple[list[TransportVehicleSchedule], list[TransportVehicleSchedule]]:
    schedules = db.execute(
        select(TransportVehicleSchedule).where(
            TransportVehicleSchedule.vehicle_id == vehicle_id,
            TransportVehicleSchedule.is_active.is_(True),
        )
    ).scalars().all()
    if not schedules:
        return [], []

    schedule_ids = [schedule.id for schedule in schedules]
    exception_dates_by_schedule_id: dict[int, set[date]] = {}
    if schedule_ids:
        exception_rows = db.execute(
            select(TransportVehicleScheduleException).where(
                TransportVehicleScheduleException.vehicle_schedule_id.in_(schedule_ids)
            )
        ).scalars().all()
        for row in exception_rows:
            exception_dates_by_schedule_id.setdefault(row.vehicle_schedule_id, set()).add(row.service_date)

    blocking_schedules: list[TransportVehicleSchedule] = []
    reusable_schedules: list[TransportVehicleSchedule] = []
    for schedule in schedules:
        schedule_exception_dates = exception_dates_by_schedule_id.get(schedule.id, set())
        if schedule.recurrence_kind != "single_date":
            blocking_schedules.append(schedule)
            continue
        if schedule.service_date is None:
            blocking_schedules.append(schedule)
            continue
        if schedule.service_date in schedule_exception_dates:
            reusable_schedules.append(schedule)
            continue
        if schedule.service_date >= reference_date:
            blocking_schedules.append(schedule)
            continue
        reusable_schedules.append(schedule)

    return blocking_schedules, reusable_schedules


def _build_vehicle_schedule_conflict_details(schedules: list[TransportVehicleSchedule]) -> str:
    grouped_details: dict[str, list[str]] = {}
    for schedule in schedules:
        grouped_details.setdefault(schedule.service_scope, []).append(
            _format_vehicle_schedule_conflict_entry(schedule)
        )

    parts: list[str] = []
    for scope in ("regular", "weekend", "extra"):
        scope_entries = grouped_details.get(scope)
        if not scope_entries:
            continue
        scope_label = _SCOPE_KIND_TO_LABEL.get(scope, scope.title())
        unique_entries = list(dict.fromkeys(scope_entries))
        parts.append(f"{scope_label} list ({', '.join(unique_entries)})")
    return "; ".join(parts)


def _format_vehicle_schedule_conflict_entry(schedule: TransportVehicleSchedule) -> str:
    route_label = _ROUTE_KIND_TO_LABEL.get(schedule.route_kind, schedule.route_kind)
    if schedule.recurrence_kind == "weekday":
        return f"{route_label} on weekdays"
    if schedule.recurrence_kind == "matching_weekday":
        if schedule.weekday is None:
            return f"{route_label} every weekend"
        return f"{route_label} every {calendar.day_name[schedule.weekday]}"
    if schedule.service_date is not None:
        return f"{route_label} on {schedule.service_date.isoformat()}"
    return route_label


def _vehicle_has_active_schedule_for_spec(
    db: Session,
    *,
    vehicle_id: int,
    schedule_spec: dict[str, object],
) -> bool:
    schedules = db.execute(
        select(TransportVehicleSchedule).where(
            TransportVehicleSchedule.vehicle_id == vehicle_id,
            TransportVehicleSchedule.service_scope == schedule_spec["service_scope"],
            TransportVehicleSchedule.route_kind == schedule_spec["route_kind"],
            TransportVehicleSchedule.is_active.is_(True),
        )
    ).scalars().all()
    if not schedules:
        return False

    recurrence_kind = schedule_spec["recurrence_kind"]
    if recurrence_kind == "single_date":
        service_date = schedule_spec["service_date"]
        return _vehicle_has_active_schedule_on_date(
            db,
            vehicle_id=vehicle_id,
            service_scope=str(schedule_spec["service_scope"]),
            route_kind=str(schedule_spec["route_kind"]),
            service_date=service_date,
        )

    for schedule in schedules:
        if schedule.recurrence_kind != recurrence_kind:
            continue
        if recurrence_kind == "matching_weekday" and schedule.weekday != schedule_spec["weekday"]:
            continue
        if recurrence_kind == "weekday" and schedule.weekday is not None:
            continue
        return True
    return False


def _vehicle_has_active_schedule_on_date(
    db: Session,
    *,
    vehicle_id: int,
    service_scope: str,
    route_kind: str,
    service_date: date,
) -> bool:
    schedules = db.execute(
        select(TransportVehicleSchedule).where(
            TransportVehicleSchedule.vehicle_id == vehicle_id,
            TransportVehicleSchedule.service_scope == service_scope,
            TransportVehicleSchedule.route_kind == route_kind,
            TransportVehicleSchedule.is_active.is_(True),
        )
    ).scalars().all()
    if not schedules:
        return False

    schedule_ids = [schedule.id for schedule in schedules]
    exception_schedule_ids = {
        row.vehicle_schedule_id
        for row in db.execute(
            select(TransportVehicleScheduleException).where(
                TransportVehicleScheduleException.vehicle_schedule_id.in_(schedule_ids),
                TransportVehicleScheduleException.service_date == service_date,
            )
        ).scalars().all()
    } if schedule_ids else set()

    for schedule in schedules:
        if schedule.id in exception_schedule_ids:
            continue
        if vehicle_schedule_applies_to_date(schedule, service_date):
            return True
    return False


def find_transport_vehicle_schedule(
    db: Session,
    *,
    vehicle: Vehicle,
    service_date: date,
    route_kind: str,
) -> TransportVehicleSchedule | None:
    schedules = db.execute(
        select(TransportVehicleSchedule).where(
            TransportVehicleSchedule.vehicle_id == vehicle.id,
            TransportVehicleSchedule.route_kind == route_kind,
            TransportVehicleSchedule.is_active.is_(True),
        )
    ).scalars().all()
    if not schedules:
        return None

    schedule_ids = [schedule.id for schedule in schedules]
    exception_schedule_ids = {
        row.vehicle_schedule_id
        for row in db.execute(
            select(TransportVehicleScheduleException).where(
                TransportVehicleScheduleException.vehicle_schedule_id.in_(schedule_ids),
                TransportVehicleScheduleException.service_date == service_date,
            )
        ).scalars().all()
    } if schedule_ids else set()

    for schedule in schedules:
        if schedule.id in exception_schedule_ids:
            continue
        if vehicle_schedule_applies_to_date(schedule, service_date):
            return schedule
    return None


def get_paired_route_kind(route_kind: str) -> str | None:
    return _PAIRED_ROUTE_KIND.get(route_kind)
