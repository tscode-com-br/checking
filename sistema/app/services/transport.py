from __future__ import annotations

import calendar
import hashlib
import json
import unicodedata
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    TransportAssignment,
    TransportBotSession,
    TransportNotification,
    TransportRequest,
    TransportVehicleSchedule,
    TransportVehicleScheduleException,
    User,
    Vehicle,
    Workplace,
)
from ..schemas import (
    ProjectRow,
    TransportBotConversationResponse,
    TransportBotReplyMessage,
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
from .project_catalog import list_project_names, list_projects, normalize_project_name
from .time_utils import now_sgt
from .user_profiles import normalize_person_name
from .user_sync import (
    APP_IMPORTED_USER_NAME,
    WEB_IMPORTED_USER_NAME,
    apply_user_state,
    create_user_sync_event,
    ensure_current_user_state_event,
    find_user_by_chave,
    is_same_singapore_day,
    normalize_user_key,
    resolve_latest_user_activity,
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
_PAIRED_ROUTE_KIND = {
    "home_to_work": "work_to_home",
    "work_to_home": "home_to_work",
}
_PLACEHOLDER_NAMES = {APP_IMPORTED_USER_NAME, WEB_IMPORTED_USER_NAME}
_MENU_OPTIONS = ["REGULAR", "WEEKEND", "EXTRA", "CHANGE", "CANCEL"]


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
        return None

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
        notifications = db.execute(
            select(TransportNotification).where(TransportNotification.assignment_id.in_(assignment_ids))
        ).scalars().all()
        for notification in notifications:
            db.delete(notification)

        assignments = db.execute(
            select(TransportAssignment).where(TransportAssignment.id.in_(assignment_ids))
        ).scalars().all()
        for assignment in assignments:
            db.delete(assignment)

    if schedule_ids:
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

    db.delete(vehicle)
    return vehicle


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
            request_status = "rejected" if latest_assignment is not None and latest_assignment.status == "rejected" else "cancelled"

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
        return WebTransportStateResponse(
            chave=user.chave,
            end_rua=user.end_rua,
            zip=user.zip,
            status="confirmed",
            request_id=active_request.id,
            request_kind=active_request.request_kind,
            route_kind=resolved_route_kind,
            service_date=service_date,
            requested_time=active_request.requested_time,
            boarding_time=_resolve_web_transport_boarding_time(
                db,
                active_request=active_request,
                service_date=service_date,
                route_kind=resolved_route_kind,
                vehicle=confirmed_vehicle,
            ),
            confirmation_deadline_time=confirmation_deadline_time,
            vehicle_type=confirmed_vehicle.tipo,
            vehicle_plate=confirmed_vehicle.placa,
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


def get_or_create_bot_session(db: Session, *, chat_id: str) -> TransportBotSession:
    session = db.execute(select(TransportBotSession).where(TransportBotSession.chat_id == chat_id)).scalar_one_or_none()
    if session is not None:
        return session

    timestamp = now_sgt()
    session = TransportBotSession(
        chat_id=chat_id,
        user_id=None,
        chave=None,
        state="awaiting_key",
        context_json=None,
        created_at=timestamp,
        updated_at=timestamp,
        last_message_at=timestamp,
    )
    db.add(session)
    db.flush()
    return session


def process_bot_message(db: Session, *, chat_id: str, message: str) -> TransportBotConversationResponse:
    session = get_or_create_bot_session(db, chat_id=chat_id)
    timestamp = now_sgt()
    session.last_message_at = timestamp
    session.updated_at = timestamp

    context = _load_session_context(session)
    normalized_message = " ".join(str(message or "").strip().split())
    replies: list[TransportBotReplyMessage] = []
    registration_completed = False
    request_created = False

    if session.state == "awaiting_key":
        normalized_key = _normalize_key_candidate(normalized_message)
        if normalized_key is None:
            replies.append(TransportBotReplyMessage(text="Send your 4-character alphanumeric key first."))
            return _save_bot_response(session, context, replies)

        session.chave = normalized_key
        user = find_user_by_chave(db, normalized_key)
        session.user_id = user.id if user is not None else None
        if user is not None and is_transport_registered_user(user):
            session.state = "ready"
            replies.append(TransportBotReplyMessage(text=f"Key {normalized_key} validated for {user.nome}."))
            replies.append(_menu_reply())
            return _save_bot_response(session, context, replies)

        session.state = "awaiting_name"
        if user is not None:
            _remember_existing_user(context, user)
        replies.append(TransportBotReplyMessage(text="Registration is incomplete. Enter your full name."))
        return _save_bot_response(session, context, replies)

    if session.state == "awaiting_name":
        try:
            context["nome"] = normalize_person_name(normalized_message)
        except ValueError:
            replies.append(TransportBotReplyMessage(text="The name must contain at least 3 characters."))
            return _save_bot_response(session, context, replies)
        project_options = list_project_names(db)
        if not project_options:
            replies.append(TransportBotReplyMessage(text="No project is registered in the system. Add a project before continuing."))
            return _save_bot_response(session, context, replies)
        session.state = "awaiting_project"
        replies.append(TransportBotReplyMessage(text="Enter the project.", options=project_options))
        return _save_bot_response(session, context, replies)

    if session.state == "awaiting_project":
        project_options = list_project_names(db)
        project = _normalize_project_code(db, normalized_message)
        if project is None:
            replies.append(TransportBotReplyMessage(text="Invalid project. Choose a registered project.", options=project_options))
            return _save_bot_response(session, context, replies)
        context["projeto"] = project
        workplaces = list_workplaces(db)
        if not workplaces:
            replies.append(TransportBotReplyMessage(text="No workplace is registered in the system. Add a workplace before continuing."))
            return _save_bot_response(session, context, replies)
        session.state = "awaiting_workplace"
        replies.append(
            TransportBotReplyMessage(
                text="Choose your workplace by sending the name or the list number.",
                options=[f"{index + 1}. {row.workplace}" for index, row in enumerate(workplaces)],
            )
        )
        return _save_bot_response(session, context, replies)

    if session.state == "awaiting_workplace":
        selected_workplace = _resolve_workplace_choice(db, normalized_message)
        if selected_workplace is None:
            workplaces = list_workplaces(db)
            replies.append(
                TransportBotReplyMessage(
                    text="Invalid workplace. Choose an existing workplace by name or number.",
                    options=[f"{index + 1}. {row.workplace}" for index, row in enumerate(workplaces)],
                )
            )
            return _save_bot_response(session, context, replies)
        context["workplace"] = selected_workplace.workplace
        session.state = "awaiting_address"
        replies.append(TransportBotReplyMessage(text="Enter your home address."))
        return _save_bot_response(session, context, replies)

    if session.state == "awaiting_address":
        address = _normalize_free_text(normalized_message, min_length=3, max_length=255)
        if address is None:
            replies.append(TransportBotReplyMessage(text="Enter a valid home address."))
            return _save_bot_response(session, context, replies)
        context["end_rua"] = address
        session.state = "awaiting_zip"
        replies.append(TransportBotReplyMessage(text="Enter your ZIP code."))
        return _save_bot_response(session, context, replies)

    if session.state == "awaiting_zip":
        zip_code = _normalize_compact_text(normalized_message, max_length=10)
        if zip_code is None:
            replies.append(TransportBotReplyMessage(text="Enter a valid ZIP code."))
            return _save_bot_response(session, context, replies)
        context["zip"] = zip_code
        user = _upsert_registered_user_from_session(db, session=session, context=context)
        session.user_id = user.id
        session.state = "ready"
        registration_completed = True
        _ensure_transport_registration_checkin(db, user=user, chat_id=chat_id)
        replies.append(TransportBotReplyMessage(text=f"Registration completed for {user.nome}."))
        replies.append(_menu_reply())
        return _save_bot_response(
            session,
            context,
            replies,
            registration_completed=registration_completed,
        )

    if session.state == "awaiting_cancel_kind":
        request_kind = _resolve_request_kind(normalized_message)
        if request_kind is None:
            replies.append(TransportBotReplyMessage(text="Choose REGULAR, WEEKEND, or EXTRA.", options=_MENU_OPTIONS[:3]))
            return _save_bot_response(session, context, replies)
        user = _require_session_user(db, session)
        cancelled = cancel_transport_requests(db, user=user, request_kind=request_kind, reference_date=timestamp.date())
        if context.get("replace_after_cancel"):
            context.pop("replace_after_cancel", None)
            context["pending_kind"] = request_kind
            session.state = "awaiting_request_time"
            if cancelled == 0:
                replies.append(TransportBotReplyMessage(text=f"No active {_REQUEST_KIND_TO_LABEL[request_kind]} request was found. Enter the new time anyway."))
            else:
                replies.append(TransportBotReplyMessage(text=f"The {_REQUEST_KIND_TO_LABEL[request_kind]} request was removed. Enter the new time in hh:mm format."))
            return _save_bot_response(session, context, replies)

        session.state = "ready"
        if cancelled == 0:
            replies.append(TransportBotReplyMessage(text=f"No active {_REQUEST_KIND_TO_LABEL[request_kind]} request was found."))
        else:
            replies.append(TransportBotReplyMessage(text=f"The {_REQUEST_KIND_TO_LABEL[request_kind]} request was cancelled."))
        replies.append(_menu_reply())
        return _save_bot_response(session, context, replies)

    if session.state == "awaiting_request_time":
        requested_time = _normalize_time_message(normalized_message)
        request_kind = str(context.get("pending_kind") or "")
        if requested_time is None or request_kind not in _REQUEST_KIND_TO_RECURRENCE:
            replies.append(TransportBotReplyMessage(text="Enter the time in hh:mm format."))
            return _save_bot_response(session, context, replies)
        user = _require_session_user(db, session)
        transport_request, _created = upsert_transport_request(
            db,
            user=user,
            request_kind=request_kind,
            requested_time=requested_time,
            requested_date=(timestamp.date() if request_kind == "extra" else None),
            created_via="bot",
        )
        session.state = "ready"
        context.pop("pending_kind", None)
        request_created = True
        replies.append(
            TransportBotReplyMessage(
                text=(
                    f"The {_REQUEST_KIND_TO_LABEL[transport_request.request_kind]} request was recorded for {transport_request.requested_time}. "
                    "Your name stays red until a vehicle is assigned."
                )
            )
        )
        replies.append(_menu_reply())
        return _save_bot_response(session, context, replies, request_created=request_created)

    user = _require_session_user(db, session)
    command = _normalize_command(normalized_message)
    request_kind = _resolve_request_kind(command)
    if request_kind is not None:
        session.state = "awaiting_request_time"
        context["pending_kind"] = request_kind
        replies.append(TransportBotReplyMessage(text="Enter the desired time in hh:mm format."))
        return _save_bot_response(session, context, replies)

    if command in {"CHANGE", "ALTERAR"}:
        session.state = "awaiting_cancel_kind"
        replies.append(
            TransportBotReplyMessage(
                text="Choose which type you want to replace. After that, send the new time.",
                options=_MENU_OPTIONS[:3],
            )
        )
        context["replace_after_cancel"] = True
        return _save_bot_response(session, context, replies)

    if command in {"CANCEL", "CANCELAR"}:
        session.state = "awaiting_cancel_kind"
        replies.append(TransportBotReplyMessage(text="Choose which type you want to cancel.", options=_MENU_OPTIONS[:3]))
        context.pop("replace_after_cancel", None)
        return _save_bot_response(session, context, replies)

    replies.append(TransportBotReplyMessage(text=f"Key validated for {user.nome}."))
    replies.append(_menu_reply())
    return _save_bot_response(session, context, replies)


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


def queue_assignment_notification(
    db: Session,
    *,
    transport_request: TransportRequest,
    assignment: TransportAssignment,
    user: User,
    vehicle: Vehicle | None,
    is_update: bool,
) -> TransportNotification | None:
    session = db.execute(
        select(TransportBotSession)
        .where(TransportBotSession.user_id == user.id)
        .order_by(TransportBotSession.updated_at.desc(), TransportBotSession.id.desc())
    ).scalar_one_or_none()
    if session is None:
        return None

    timestamp = now_sgt()
    message = _build_assignment_message(
        transport_request=transport_request,
        assignment=assignment,
        vehicle=vehicle,
        is_update=is_update,
    )
    notification = TransportNotification(
        user_id=user.id,
        chat_id=session.chat_id,
        request_id=transport_request.id,
        assignment_id=assignment.id,
        message=message,
        status="pending",
        created_at=timestamp,
        sent_at=None,
    )
    db.add(notification)
    return notification


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


def _build_assignment_message(
    *,
    transport_request: TransportRequest,
    assignment: TransportAssignment,
    vehicle: Vehicle | None,
    is_update: bool,
) -> str:
    kind_label = _REQUEST_KIND_TO_LABEL[transport_request.request_kind]
    route_label = _ROUTE_KIND_TO_LABEL.get(assignment.route_kind, assignment.route_kind)
    if assignment.status == "confirmed" and vehicle is not None:
        prefix = "Your transport has been updated" if is_update else "Your transport has been confirmed"
        vehicle_description = f"{vehicle.tipo} {vehicle.placa}"
        if vehicle.color:
            vehicle_description = f"{vehicle_description}, color {vehicle.color}"
        return (
            f"{prefix}: {kind_label} at {transport_request.requested_time} ({route_label}) with {vehicle_description}. "
            f"Tolerance: {vehicle.tolerance} minutes."
        )
    if assignment.status == "rejected":
        return f"Your {kind_label} transport at {transport_request.requested_time} ({route_label}) was rejected."
    return f"Your {kind_label} transport at {transport_request.requested_time} ({route_label}) was cancelled."


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


def _upsert_registered_user_from_session(db: Session, *, session: TransportBotSession, context: dict[str, str]) -> User:
    timestamp = now_sgt()
    user = db.get(User, session.user_id) if session.user_id is not None else None
    if user is None:
        if session.chave is None:
            raise ValueError("The user key is missing from the session.")
        user = find_user_by_chave(db, session.chave)
    if user is None:
        user = User(
            rfid=None,
            chave=normalize_user_key(session.chave or ""),
            nome=context["nome"],
            projeto=context["projeto"],
            workplace=context["workplace"],
            placa=None,
            end_rua=context["end_rua"],
            zip=context["zip"],
            cargo=None,
            email=None,
            local=None,
            checkin=None,
            time=None,
            last_active_at=timestamp,
            inactivity_days=0,
        )
        db.add(user)
        db.flush()
        return user

    user.nome = context["nome"]
    user.projeto = context["projeto"]
    user.workplace = context["workplace"]
    user.end_rua = context["end_rua"]
    user.zip = context["zip"]
    user.last_active_at = timestamp
    return user


def _ensure_transport_registration_checkin(db: Session, *, user: User, chat_id: str) -> bool:
    timestamp = now_sgt()
    latest_activity = resolve_latest_user_activity(db, user=user)
    if latest_activity is not None and latest_activity.action == "checkin" and is_same_singapore_day(latest_activity.event_time, timestamp):
        return False

    ensure_current_user_state_event(db, user=user)
    apply_user_state(
        user,
        action="checkin",
        event_time=timestamp,
        projeto=user.projeto,
        local=user.workplace or user.local,
    )
    request_hash = hashlib.sha1(f"bot-register|{chat_id}|{timestamp.isoformat()}".encode("utf-8")).hexdigest()
    create_user_sync_event(
        db,
        user=user,
        source="bot",
        action="checkin",
        event_time=timestamp,
        projeto=user.projeto,
        local=user.workplace or user.local,
        ontime=True,
        source_request_id=request_hash,
        device_id="transport-bot",
    )
    return True


def is_transport_registered_user(user: User) -> bool:
    normalized_name = " ".join(str(user.nome or "").strip().split())
    return bool(
        normalized_name
        and normalized_name not in _PLACEHOLDER_NAMES
        and user.projeto
        and user.workplace
        and user.end_rua
        and user.zip
    )


def _remember_existing_user(context: dict[str, str], user: User) -> None:
    if user.nome and user.nome not in _PLACEHOLDER_NAMES:
        context.setdefault("nome", user.nome)
    if user.projeto:
        context.setdefault("projeto", user.projeto)
    if user.workplace:
        context.setdefault("workplace", user.workplace)
    if user.end_rua:
        context.setdefault("end_rua", user.end_rua)
    if user.zip:
        context.setdefault("zip", user.zip)


def _load_session_context(session: TransportBotSession) -> dict[str, str]:
    raw_value = str(session.context_json or "").strip()
    if not raw_value:
        return {}
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _save_bot_response(
    session: TransportBotSession,
    context: dict[str, str],
    replies: list[TransportBotReplyMessage],
    *,
    registration_completed: bool = False,
    request_created: bool = False,
) -> TransportBotConversationResponse:
    session.context_json = json.dumps(context, ensure_ascii=True, separators=(",", ":")) if context else None
    return TransportBotConversationResponse(
        ok=True,
        state=session.state,
        user_key=session.chave,
        registration_completed=registration_completed,
        request_created=request_created,
        messages=replies,
    )


def _require_session_user(db: Session, session: TransportBotSession) -> User:
    user = db.get(User, session.user_id) if session.user_id is not None else None
    if user is None and session.chave:
        user = find_user_by_chave(db, session.chave)
    if user is None:
        raise ValueError("The bot session does not have a linked user.")
    return user


def _normalize_key_candidate(value: str) -> str | None:
    normalized = str(value or "").strip().upper()
    if len(normalized) != 4 or not normalized.isalnum():
        return None
    return normalized


def _normalize_project_code(db: Session, value: str) -> str | None:
    try:
        normalized = normalize_project_name(value)
    except ValueError:
        return None
    return normalized if normalized in set(list_project_names(db)) else None


def _normalize_free_text(value: str, *, min_length: int, max_length: int) -> str | None:
    normalized = " ".join(str(value or "").strip().split())
    if len(normalized) < min_length or len(normalized) > max_length:
        return None
    return normalized


def _normalize_compact_text(value: str, *, max_length: int) -> str | None:
    normalized = str(value or "").strip()
    if not normalized or len(normalized) > max_length:
        return None
    return normalized


def _normalize_time_message(value: str) -> str | None:
    normalized = str(value or "").strip()
    parts = normalized.split(":")
    if len(parts) != 2 or any(not part.isdigit() for part in parts):
        return None
    hour, minute = int(parts[0]), int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def _normalize_command(value: str) -> str:
    collapsed = " ".join(str(value or "").strip().split())
    normalized = unicodedata.normalize("NFKD", collapsed)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized.upper()


def _resolve_request_kind(value: str) -> str | None:
    normalized = _normalize_command(value)
    if normalized == "REGULAR":
        return "regular"
    if normalized in {"FIM DE SEMANA", "WEEKEND"}:
        return "weekend"
    if normalized == "EXTRA":
        return "extra"
    return None


def _resolve_workplace_choice(db: Session, value: str) -> Workplace | None:
    workplaces = db.execute(select(Workplace).order_by(Workplace.workplace, Workplace.id)).scalars().all()
    if not workplaces:
        return None
    normalized = str(value or "").strip()
    if normalized.isdigit():
        index = int(normalized) - 1
        if 0 <= index < len(workplaces):
            return workplaces[index]
    lowered = normalized.casefold()
    for workplace in workplaces:
        if workplace.workplace.casefold() == lowered:
            return workplace
    return None


def _menu_reply() -> TransportBotReplyMessage:
    return TransportBotReplyMessage(text="Choose an option.", options=_MENU_OPTIONS)