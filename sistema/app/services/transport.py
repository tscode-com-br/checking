from __future__ import annotations

import calendar
import json
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

from sqlalchemy import MetaData, Table, delete, inspect, select, update
from sqlalchemy.orm import Session

from ..core.config import settings
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
    TransportVehicleScheduleUpdate,
    TransportVehicleUpdate,
    TransportVehicleManagementRow,
    TransportVehicleRow,
    WebTransportRequestItemResponse,
    WebTransportStateResponse,
    WorkplaceRow,
)
from .location_settings import (
    get_transport_last_update_time,
    get_transport_work_to_home_time,
    get_transport_work_to_home_time_for_context,
    get_transport_work_to_home_time_for_date,
)
from .project_catalog import list_projects
from .time_utils import build_timezone_label, now_sgt
from .transport_vehicle_base import build_transport_vehicle_pending_fields, build_transport_vehicle_base_row, is_transport_vehicle_ready_for_allocation
from .transport_vehicle_schedule import (
    resolve_transport_vehicle_operational_scope,
    vehicle_supports_transport_service_scope,
)


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
_REGULAR_VEHICLE_WEEKDAY_FIELDS = (
    ("every_monday", 0),
    ("every_tuesday", 1),
    ("every_wednesday", 2),
    ("every_thursday", 3),
    ("every_friday", 4),
)
_PAIRED_ROUTE_KIND = {
    "home_to_work": "work_to_home",
    "work_to_home": "home_to_work",
}


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


def _build_transport_export_file_name(timestamp: datetime) -> str:
    from .transport_exports import _build_transport_export_file_name as build_transport_export_file_name_impl

    return build_transport_export_file_name_impl(timestamp)


def _resolve_transport_export_path(file_name: str) -> Path:
    from .transport_exports import _resolve_transport_export_path as resolve_transport_export_path_impl

    return resolve_transport_export_path_impl(file_name)


def build_transport_list_export(
    db: Session,
    *,
    service_date: date,
    selected_route_kind: str,
) -> tuple[str, bytes]:
    from .transport_exports import build_transport_list_export as build_transport_list_export_impl

    return build_transport_list_export_impl(
        db,
        service_date=service_date,
        selected_route_kind=selected_route_kind,
    )


def build_transport_operational_plan_export(
    db: Session,
    *,
    service_date: date,
    selected_route_kind: str,
    proposal,
) -> tuple[str, bytes]:
    from .transport_exports import build_transport_operational_plan_export as build_transport_operational_plan_export_impl

    return build_transport_operational_plan_export_impl(
        db,
        service_date=service_date,
        selected_route_kind=selected_route_kind,
        proposal=proposal,
    )


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
    workplace_name: str | None,
    vehicle: Vehicle | None,
    schedules: list[TransportVehicleSchedule] | None = None,
) -> str:
    resolved_scope = (
        resolve_transport_vehicle_operational_scope(vehicle=vehicle, schedules=schedules)
        if vehicle is not None
        else None
    )
    if route_kind == "work_to_home" and resolved_scope in {"regular", "weekend"}:
        return get_transport_work_to_home_time_for_context(
            db,
            service_date=service_date,
            workplace_name=workplace_name,
        )
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
    workplace_name: str | None,
) -> str | None:
    if service_date is None:
        return boarding_time

    if transport_request.request_kind in {"regular", "weekend"}:
        return get_transport_work_to_home_time_for_context(
            db,
            service_date=service_date,
            workplace_name=workplace_name,
        )

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


def _transport_dashboard_assignment_priority(
    assignment: TransportAssignment,
) -> tuple[int, int, datetime, int]:
    status_rank = {
        "confirmed": 3,
        "rejected": 2,
        "cancelled": 1,
        "pending": 0,
    }
    return (
        status_rank.get(assignment.status, -1),
        1 if assignment.vehicle_id is not None else 0,
        assignment.updated_at,
        assignment.id,
    )


def build_transport_dashboard(
    db: Session,
    *,
    service_date: date,
    route_kind: str,
) -> TransportDashboardResponse:
    from .transport_dashboard_queries import build_transport_dashboard as build_transport_dashboard_query

    return build_transport_dashboard_query(
        db,
        service_date=service_date,
        route_kind=route_kind,
    )


def list_workplaces(db: Session) -> list[WorkplaceRow]:
    from .transport_dashboard_queries import list_workplaces as list_transport_workplaces_query

    return list_transport_workplaces_query(db)


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


def _resolve_regular_vehicle_selected_weekdays(payload: TransportVehicleCreate) -> tuple[int, ...]:
    from .transport_vehicle_operations import _resolve_regular_vehicle_selected_weekdays as resolve_regular_vehicle_selected_weekdays_impl

    return resolve_regular_vehicle_selected_weekdays_impl(payload)


def vehicle_schedule_applies_to_date(schedule: TransportVehicleSchedule, service_date: date) -> bool:
    from .transport_vehicle_operations import vehicle_schedule_applies_to_date as vehicle_schedule_applies_to_date_impl

    return vehicle_schedule_applies_to_date_impl(schedule, service_date)


def create_transport_vehicle_registration(
    db: Session,
    *,
    payload: TransportVehicleCreate,
) -> tuple[Vehicle, list[TransportVehicleSchedule]]:
    from .transport_vehicle_operations import create_transport_vehicle_registration as create_transport_vehicle_registration_impl

    return create_transport_vehicle_registration_impl(db, payload=payload)


def delete_transport_vehicle_registration(
    db: Session,
    *,
    schedule_id: int,
) -> Vehicle:
    from .transport_vehicle_operations import delete_transport_vehicle_registration as delete_transport_vehicle_registration_impl

    return delete_transport_vehicle_registration_impl(db, schedule_id=schedule_id)


def update_transport_vehicle_base(
    db: Session,
    *,
    vehicle_id: int,
    payload: TransportVehicleUpdate,
) -> Vehicle:
    from .transport_vehicle_base import update_transport_vehicle_base as update_transport_vehicle_base_impl

    return update_transport_vehicle_base_impl(
        db,
        vehicle_id=vehicle_id,
        payload=payload,
    )


def update_transport_vehicle_schedule(
    db: Session,
    *,
    schedule_id: int,
    payload: TransportVehicleScheduleUpdate,
) -> TransportVehicleSchedule:
    from .transport_vehicle_schedule import update_transport_vehicle_schedule as update_transport_vehicle_schedule_impl

    return update_transport_vehicle_schedule_impl(
        db,
        schedule_id=schedule_id,
        payload=payload,
    )


def _purge_foreign_key_dependencies(
    db: Session,
    *,
    target_table: str,
    target_column: str,
    values: list[object],
    mode: str,
    excluded_tables: set[str] | None = None,
) -> None:
    from .transport_vehicle_operations import _purge_foreign_key_dependencies as purge_foreign_key_dependencies_impl

    purge_foreign_key_dependencies_impl(
        db,
        target_table=target_table,
        target_column=target_column,
        values=values,
        mode=mode,
        excluded_tables=excluded_tables,
    )


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
                    workplace_name=user.workplace,
                    vehicle=confirmed_vehicle,
                    schedules=schedules_by_vehicle_id.get(confirmed_vehicle.id, []),
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
            workplace_name=user.workplace,
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
            workplace_name=user.workplace,
            vehicle=confirmed_vehicle,
            schedules=schedules_by_vehicle_id.get(confirmed_vehicle.id, []),
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
    from .transport_assignment_operations import update_transport_assignment as update_transport_assignment_impl

    return update_transport_assignment_impl(
        db,
        transport_request=transport_request,
        service_date=service_date,
        route_kind=route_kind,
        status=status,
        vehicle=vehicle,
        response_message=response_message,
        admin_user_id=admin_user_id,
    )


def _reset_transport_request_assignments_to_pending(
    db: Session,
    *,
    transport_request: TransportRequest,
    response_message: str | None,
    admin_user_id: int | None,
) -> None:
    from .transport_assignment_operations import _reset_transport_request_assignments_to_pending as reset_transport_request_assignments_to_pending_impl

    reset_transport_request_assignments_to_pending_impl(
        db,
        transport_request=transport_request,
        response_message=response_message,
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
    from .transport_assignment_operations import upsert_transport_assignment_with_persistence as upsert_transport_assignment_with_persistence_impl

    return upsert_transport_assignment_with_persistence_impl(
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
    from .transport_assignment_operations import _propagate_confirmed_recurring_assignment as propagate_confirmed_recurring_assignment_impl

    propagate_confirmed_recurring_assignment_impl(
        db,
        transport_request=transport_request,
        service_date=service_date,
        vehicle=vehicle,
        response_message=response_message,
        admin_user_id=admin_user_id,
    )


def _materialize_recurring_assignments_for_date(
    db: Session,
    *,
    transport_request: TransportRequest,
    service_date: date,
) -> int:
    from .transport_assignment_operations import _materialize_recurring_assignments_for_date as materialize_recurring_assignments_for_date_impl

    return materialize_recurring_assignments_for_date_impl(
        db,
        transport_request=transport_request,
        service_date=service_date,
    )


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
    resolved_scope = resolve_transport_vehicle_operational_scope(vehicle=vehicle, schedules=schedules)

    target_weekdays: set[int]
    if resolved_scope == "regular":
        target_weekdays = {0, 1, 2, 3, 4}
    elif resolved_scope == "weekend":
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
        vehicle_schedules = schedules_by_vehicle_id.get(vehicle.id, [])
        if not vehicle_supports_transport_service_scope(
            vehicle=vehicle,
            service_scope=request_kind,
            schedules=vehicle_schedules,
        ):
            continue

        target_weekdays = _resolve_assignment_template_weekdays(
            transport_request=transport_request,
            vehicle=vehicle,
            schedules=vehicle_schedules,
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
    service_date: date,
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
    for (request_id, weekday), (_assignment, vehicle) in recurring_assignment_templates.items():
        if weekday != service_date.weekday():
            continue
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
                    pending_fields=build_transport_vehicle_pending_fields(vehicle),
                    is_ready_for_allocation=is_transport_vehicle_ready_for_allocation(vehicle),
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
                pending_fields=build_transport_vehicle_pending_fields(vehicle),
                is_ready_for_allocation=is_transport_vehicle_ready_for_allocation(vehicle),
            )
        )

    for scope in ("regular", "weekend"):
        registry_rows[scope] = sorted(
            registry_rows_by_vehicle_id[scope].values(),
            key=lambda row: (row.placa or "", row.vehicle_id),
        )

    registry_rows["extra"].sort(
        key=lambda row: (
            row.service_date or date.min,
            row.route_kind or "",
            row.placa or "",
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
    base_row = build_transport_vehicle_base_row(vehicle)

    return TransportVehicleRow(
        **base_row.model_dump(),
        schedule_id=(schedule.id if schedule is not None else None),
        service_scope=resolve_transport_vehicle_operational_scope(vehicle=vehicle, schedule=schedule),
        route_kind=(schedule.route_kind if schedule is not None else None),
        departure_time=departure_time,
    )


def _build_vehicle_rows_for_dashboard(
    db: Session,
    *,
    service_date: date,
    route_kind: str,
    work_to_home_departure_time: str,
) -> tuple[
    dict[str, list[TransportVehicleRow]],
    dict[int, TransportVehicleRow],
    dict[tuple[int, str | None], TransportVehicleRow],
]:
    vehicles_by_scope: dict[str, list[TransportVehicleRow]] = {
        "regular": [],
        "weekend": [],
        "extra": [],
    }
    vehicle_rows_by_id: dict[int, TransportVehicleRow] = {}
    vehicle_rows_by_assignment_key: dict[tuple[int, str | None], TransportVehicleRow] = {}

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
        vehicle_rows_by_assignment_key[(vehicle.id, schedule.route_kind if schedule.service_scope == "extra" else None)] = vehicle_row
        vehicle_rows_by_id.setdefault(vehicle.id, vehicle_row)

    for rows in vehicles_by_scope.values():
        rows.sort(key=lambda item: (item.placa or "", item.id))

    return vehicles_by_scope, vehicle_rows_by_id, vehicle_rows_by_assignment_key


def _build_schedule_specs_from_payload(payload: TransportVehicleCreate) -> list[dict[str, object]]:
    from .transport_vehicle_operations import _build_schedule_specs_from_payload as build_schedule_specs_from_payload_impl

    return build_schedule_specs_from_payload_impl(payload)


def _classify_vehicle_schedules_for_reuse(
    db: Session,
    *,
    vehicle_id: int,
    reference_date: date,
) -> tuple[list[TransportVehicleSchedule], list[TransportVehicleSchedule]]:
    from .transport_vehicle_operations import _classify_vehicle_schedules_for_reuse as classify_vehicle_schedules_for_reuse_impl

    return classify_vehicle_schedules_for_reuse_impl(
        db,
        vehicle_id=vehicle_id,
        reference_date=reference_date,
    )


def _build_vehicle_schedule_conflict_details(schedules: list[TransportVehicleSchedule]) -> str:
    from .transport_vehicle_operations import _build_vehicle_schedule_conflict_details as build_vehicle_schedule_conflict_details_impl

    return build_vehicle_schedule_conflict_details_impl(schedules)


def _format_vehicle_schedule_conflict_entry(schedule: TransportVehicleSchedule) -> str:
    from .transport_vehicle_operations import _format_vehicle_schedule_conflict_entry as format_vehicle_schedule_conflict_entry_impl

    return format_vehicle_schedule_conflict_entry_impl(schedule)


def _vehicle_has_active_schedule_for_spec(
    db: Session,
    *,
    vehicle_id: int,
    schedule_spec: dict[str, object],
) -> bool:
    from .transport_vehicle_operations import _vehicle_has_active_schedule_for_spec as vehicle_has_active_schedule_for_spec_impl

    return vehicle_has_active_schedule_for_spec_impl(
        db,
        vehicle_id=vehicle_id,
        schedule_spec=schedule_spec,
    )


def _vehicle_has_active_schedule_on_date(
    db: Session,
    *,
    vehicle_id: int,
    service_scope: str,
    route_kind: str,
    service_date: date,
) -> bool:
    from .transport_vehicle_operations import _vehicle_has_active_schedule_on_date as vehicle_has_active_schedule_on_date_impl

    return vehicle_has_active_schedule_on_date_impl(
        db,
        vehicle_id=vehicle_id,
        service_scope=service_scope,
        route_kind=route_kind,
        service_date=service_date,
    )


def find_transport_vehicle_schedule(
    db: Session,
    *,
    vehicle: Vehicle,
    service_date: date,
    route_kind: str,
    service_scope: str | None = None,
) -> TransportVehicleSchedule | None:
    from .transport_vehicle_operations import find_transport_vehicle_schedule as find_transport_vehicle_schedule_impl

    return find_transport_vehicle_schedule_impl(
        db,
        vehicle=vehicle,
        service_date=service_date,
        route_kind=route_kind,
        service_scope=service_scope,
    )


def get_paired_route_kind(route_kind: str) -> str | None:
    from .transport_vehicle_operations import get_paired_route_kind as get_paired_route_kind_impl

    return get_paired_route_kind_impl(route_kind)
