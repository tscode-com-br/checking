from __future__ import annotations

import calendar
from collections.abc import Iterable
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import TransportAssignment, TransportRequest, TransportVehicleSchedule, TransportVehicleScheduleException, Vehicle
from ..schemas import TransportVehicleCreate, TransportVehicleScheduleDefinition, TransportVehicleScheduleUpdate
from .time_utils import now_sgt


_REGULAR_REQUEST_SELECTED_WEEKDAYS = (0, 1, 2, 3, 4)
_SCOPE_KIND_TO_LABEL = {
    "regular": "Regular",
    "weekend": "Weekend",
    "extra": "Extra",
}
_ROUTE_KIND_TO_LABEL = {
    "home_to_work": "Home to Work",
    "work_to_home": "Work to Home",
}


def resolve_regular_vehicle_selected_weekdays(payload: TransportVehicleCreate) -> tuple[int, ...]:
    return tuple(
        weekday
        for field_name, weekday in (
            ("every_monday", 0),
            ("every_tuesday", 1),
            ("every_wednesday", 2),
            ("every_thursday", 3),
            ("every_friday", 4),
        )
        if getattr(payload, field_name, False)
    )


def build_transport_vehicle_schedule_definitions_from_payload(
    payload: TransportVehicleCreate,
) -> list[TransportVehicleScheduleDefinition]:
    if payload.service_scope == "extra":
        return [
            TransportVehicleScheduleDefinition(
                service_scope=payload.service_scope,
                route_kind=str(payload.route_kind),
                recurrence_kind="single_date",
                service_date=payload.service_date,
                weekday=None,
                departure_time=payload.departure_time,
                is_active=True,
            )
        ]

    route_kinds = ("home_to_work", "work_to_home")
    if payload.service_scope == "weekend":
        selected_weekdays: list[int] = []
        if payload.every_saturday:
            selected_weekdays.append(5)
        if payload.every_sunday:
            selected_weekdays.append(6)
        return [
            TransportVehicleScheduleDefinition(
                service_scope=payload.service_scope,
                route_kind=route_kind,
                recurrence_kind="matching_weekday",
                service_date=payload.service_date,
                weekday=weekday,
                departure_time=None,
                is_active=True,
            )
            for weekday in selected_weekdays
            for route_kind in route_kinds
        ]

    selected_regular_weekdays = resolve_regular_vehicle_selected_weekdays(payload)
    if selected_regular_weekdays == _REGULAR_REQUEST_SELECTED_WEEKDAYS:
        return [
            TransportVehicleScheduleDefinition(
                service_scope=payload.service_scope,
                route_kind=route_kind,
                recurrence_kind="weekday",
                service_date=payload.service_date,
                weekday=None,
                departure_time=None,
                is_active=True,
            )
            for route_kind in route_kinds
        ]

    return [
        TransportVehicleScheduleDefinition(
            service_scope=payload.service_scope,
            route_kind=route_kind,
            recurrence_kind="matching_weekday",
            service_date=payload.service_date,
            weekday=weekday,
            departure_time=None,
            is_active=True,
        )
        for weekday in selected_regular_weekdays
        for route_kind in route_kinds
    ]


def build_transport_vehicle_schedule_model(
    *,
    vehicle_id: int,
    definition: TransportVehicleScheduleDefinition,
    timestamp: datetime,
) -> TransportVehicleSchedule:
    return TransportVehicleSchedule(
        vehicle_id=vehicle_id,
        service_scope=definition.service_scope,
        route_kind=definition.route_kind,
        recurrence_kind=definition.recurrence_kind,
        service_date=definition.service_date,
        weekday=definition.weekday,
        departure_time=definition.departure_time,
        is_active=definition.is_active,
        created_at=timestamp,
        updated_at=timestamp,
    )


def build_transport_vehicle_schedule_definition_from_model(
    schedule: TransportVehicleSchedule,
) -> TransportVehicleScheduleDefinition:
    return TransportVehicleScheduleDefinition.model_construct(
        service_scope=schedule.service_scope,
        route_kind=schedule.route_kind,
        recurrence_kind=schedule.recurrence_kind,
        service_date=schedule.service_date,
        weekday=schedule.weekday,
        departure_time=schedule.departure_time,
        is_active=schedule.is_active,
    )


def transport_vehicle_schedule_definition_applies_to_date(
    definition: TransportVehicleScheduleDefinition,
    service_date: date,
) -> bool:
    if not definition.is_active:
        return False
    if definition.recurrence_kind != "single_date" and definition.service_date is not None and service_date < definition.service_date:
        return False
    if definition.recurrence_kind == "weekday":
        return service_date.weekday() < 5
    if definition.recurrence_kind == "matching_weekday":
        return definition.weekday == service_date.weekday()
    return definition.service_date == service_date


def vehicle_schedule_applies_to_date(schedule: TransportVehicleSchedule, service_date: date) -> bool:
    return transport_vehicle_schedule_definition_applies_to_date(
        build_transport_vehicle_schedule_definition_from_model(schedule),
        service_date,
    )


def list_transport_vehicle_active_scopes(
    schedules: Iterable[TransportVehicleSchedule] | None,
) -> set[str]:
    if schedules is None:
        return set()
    return {schedule.service_scope for schedule in schedules if schedule.is_active}


def resolve_transport_vehicle_operational_scope(
    *,
    vehicle: Vehicle,
    schedules: Iterable[TransportVehicleSchedule] | None = None,
    schedule: TransportVehicleSchedule | None = None,
) -> str:
    if schedule is not None and schedule.is_active:
        return schedule.service_scope

    active_scopes = list_transport_vehicle_active_scopes(schedules)
    for candidate_scope in ("regular", "weekend", "extra"):
        if candidate_scope in active_scopes:
            return candidate_scope
    return vehicle.service_scope


def vehicle_supports_transport_service_scope(
    *,
    vehicle: Vehicle,
    service_scope: str,
    schedules: Iterable[TransportVehicleSchedule] | None = None,
) -> bool:
    active_scopes = list_transport_vehicle_active_scopes(schedules)
    if active_scopes:
        return service_scope in active_scopes
    return vehicle.service_scope == service_scope


def classify_transport_vehicle_schedules_for_reuse(
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


def build_transport_vehicle_schedule_conflict_details(schedules: list[TransportVehicleSchedule]) -> str:
    grouped_details: dict[str, list[str]] = {}
    for schedule in schedules:
        grouped_details.setdefault(schedule.service_scope, []).append(
            format_transport_vehicle_schedule_conflict_entry(schedule)
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


def format_transport_vehicle_schedule_conflict_entry(schedule: TransportVehicleSchedule) -> str:
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


def vehicle_has_active_schedule_for_definition(
    db: Session,
    *,
    vehicle_id: int,
    definition: TransportVehicleScheduleDefinition,
    excluded_schedule_id: int | None = None,
) -> bool:
    schedule_query = select(TransportVehicleSchedule).where(
        TransportVehicleSchedule.vehicle_id == vehicle_id,
        TransportVehicleSchedule.service_scope == definition.service_scope,
        TransportVehicleSchedule.route_kind == definition.route_kind,
        TransportVehicleSchedule.is_active.is_(True),
    )
    if excluded_schedule_id is not None:
        schedule_query = schedule_query.where(TransportVehicleSchedule.id != excluded_schedule_id)

    schedules = db.execute(schedule_query).scalars().all()
    if not schedules:
        return False

    if definition.recurrence_kind == "single_date":
        return vehicle_has_active_schedule_on_date(
            db,
            vehicle_id=vehicle_id,
            service_scope=definition.service_scope,
            route_kind=definition.route_kind,
            service_date=definition.service_date,
            excluded_schedule_id=excluded_schedule_id,
        )

    for schedule in schedules:
        if schedule.recurrence_kind != definition.recurrence_kind:
            continue
        if definition.recurrence_kind == "matching_weekday" and schedule.weekday != definition.weekday:
            continue
        if definition.recurrence_kind == "weekday" and schedule.weekday is not None:
            continue
        return True
    return False


def vehicle_has_active_schedule_on_date(
    db: Session,
    *,
    vehicle_id: int,
    service_scope: str,
    route_kind: str,
    service_date: date | None,
    excluded_schedule_id: int | None = None,
) -> bool:
    if service_date is None:
        return False

    schedule_query = select(TransportVehicleSchedule).where(
        TransportVehicleSchedule.vehicle_id == vehicle_id,
        TransportVehicleSchedule.service_scope == service_scope,
        TransportVehicleSchedule.route_kind == route_kind,
        TransportVehicleSchedule.is_active.is_(True),
    )
    if excluded_schedule_id is not None:
        schedule_query = schedule_query.where(TransportVehicleSchedule.id != excluded_schedule_id)

    schedules = db.execute(schedule_query).scalars().all()
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


def _schedule_row_applies_to_date_with_exceptions(
    schedule: TransportVehicleSchedule,
    *,
    service_date: date,
    exception_dates: set[date],
) -> bool:
    if service_date in exception_dates:
        return False
    return vehicle_schedule_applies_to_date(schedule, service_date)


def _build_exception_dates_by_schedule_id(
    db: Session,
    *,
    schedule_ids: list[int],
) -> dict[int, set[date]]:
    if not schedule_ids:
        return {}

    exception_rows = db.execute(
        select(TransportVehicleScheduleException).where(
            TransportVehicleScheduleException.vehicle_schedule_id.in_(schedule_ids)
        )
    ).scalars().all()
    exception_dates_by_schedule_id: dict[int, set[date]] = {}
    for row in exception_rows:
        exception_dates_by_schedule_id.setdefault(row.vehicle_schedule_id, set()).add(row.service_date)
    return exception_dates_by_schedule_id


def _build_updated_active_schedules_for_vehicle(
    db: Session,
    *,
    vehicle_id: int,
    target_schedule_id: int,
    updated_definition: TransportVehicleScheduleDefinition,
) -> tuple[list[TransportVehicleSchedule], dict[int, set[date]]]:
    other_schedules = db.execute(
        select(TransportVehicleSchedule).where(
            TransportVehicleSchedule.vehicle_id == vehicle_id,
            TransportVehicleSchedule.id != target_schedule_id,
            TransportVehicleSchedule.is_active.is_(True),
        )
    ).scalars().all()
    exception_dates_by_schedule_id = _build_exception_dates_by_schedule_id(
        db,
        schedule_ids=[schedule.id for schedule in other_schedules],
    )
    return other_schedules, exception_dates_by_schedule_id


def _confirmed_assignments_impacted_by_schedule_update(
    db: Session,
    *,
    current_schedule: TransportVehicleSchedule,
    updated_definition: TransportVehicleScheduleDefinition,
) -> list[str]:
    if current_schedule.vehicle_id is None:
        return []

    today = now_sgt().date()
    future_confirmed_assignments = db.execute(
        select(TransportAssignment, TransportRequest)
        .join(TransportRequest, TransportRequest.id == TransportAssignment.request_id)
        .where(
            TransportAssignment.vehicle_id == current_schedule.vehicle_id,
            TransportAssignment.status == "confirmed",
            TransportAssignment.service_date >= today,
        )
        .order_by(TransportAssignment.service_date, TransportAssignment.route_kind, TransportAssignment.id)
    ).all()
    if not future_confirmed_assignments:
        return []

    current_exception_dates = _build_exception_dates_by_schedule_id(db, schedule_ids=[current_schedule.id]).get(current_schedule.id, set())
    other_schedules, other_exception_dates_by_schedule_id = _build_updated_active_schedules_for_vehicle(
        db,
        vehicle_id=current_schedule.vehicle_id,
        target_schedule_id=current_schedule.id,
        updated_definition=updated_definition,
    )

    impacted_entries: list[str] = []
    for assignment, transport_request in future_confirmed_assignments:
        if transport_request.request_kind != current_schedule.service_scope:
            continue
        if assignment.route_kind != current_schedule.route_kind:
            continue
        if not _schedule_row_applies_to_date_with_exceptions(
            current_schedule,
            service_date=assignment.service_date,
            exception_dates=current_exception_dates,
        ):
            continue

        covered_by_updated_schedule = (
            updated_definition.is_active
            and updated_definition.service_scope == transport_request.request_kind
            and updated_definition.route_kind == assignment.route_kind
            and transport_vehicle_schedule_definition_applies_to_date(updated_definition, assignment.service_date)
        )
        if covered_by_updated_schedule:
            continue

        covered_by_other_schedule = False
        for other_schedule in other_schedules:
            if other_schedule.service_scope != transport_request.request_kind:
                continue
            if other_schedule.route_kind != assignment.route_kind:
                continue
            if _schedule_row_applies_to_date_with_exceptions(
                other_schedule,
                service_date=assignment.service_date,
                exception_dates=other_exception_dates_by_schedule_id.get(other_schedule.id, set()),
            ):
                covered_by_other_schedule = True
                break
        if covered_by_other_schedule:
            continue

        route_label = _ROUTE_KIND_TO_LABEL.get(assignment.route_kind, assignment.route_kind)
        scope_label = _SCOPE_KIND_TO_LABEL.get(transport_request.request_kind, transport_request.request_kind)
        impacted_entries.append(f"{scope_label} / {route_label} on {assignment.service_date.isoformat()}")

    return impacted_entries


def update_transport_vehicle_schedule(
    db: Session,
    *,
    schedule_id: int,
    payload: TransportVehicleScheduleUpdate,
) -> TransportVehicleSchedule:
    schedule = db.get(TransportVehicleSchedule, schedule_id)
    if schedule is None:
        raise ValueError("Vehicle schedule not found.")

    vehicle = db.get(Vehicle, schedule.vehicle_id)
    if vehicle is None:
        raise ValueError("Vehicle not found.")

    updated_definition = TransportVehicleScheduleDefinition(**payload.model_dump())
    active_scopes = {
        other_schedule.service_scope
        for other_schedule in db.execute(
            select(TransportVehicleSchedule).where(
                TransportVehicleSchedule.vehicle_id == vehicle.id,
                TransportVehicleSchedule.id != schedule.id,
                TransportVehicleSchedule.is_active.is_(True),
            )
        ).scalars().all()
    }
    if updated_definition.is_active:
        active_scopes.add(updated_definition.service_scope)
    if len(active_scopes) > 1:
        raise ValueError("A vehicle cannot have active schedules in different lists.")

    if updated_definition.is_active and vehicle_has_active_schedule_for_definition(
        db,
        vehicle_id=vehicle.id,
        definition=updated_definition,
        excluded_schedule_id=schedule.id,
    ):
        raise ValueError("Another active schedule already exists for the selected list and recurrence pattern.")

    impacted_assignments = _confirmed_assignments_impacted_by_schedule_update(
        db,
        current_schedule=schedule,
        updated_definition=updated_definition,
    )
    if impacted_assignments:
        details = "; ".join(impacted_assignments[:3])
        if len(impacted_assignments) > 3:
            details = f"{details}; ..."
        raise ValueError(
            "Cannot update the schedule because confirmed assignments would become unavailable: "
            f"{details}."
        )

    timestamp = now_sgt()
    schedule.service_scope = updated_definition.service_scope
    schedule.route_kind = updated_definition.route_kind
    schedule.recurrence_kind = updated_definition.recurrence_kind
    schedule.service_date = updated_definition.service_date
    schedule.weekday = updated_definition.weekday
    schedule.departure_time = updated_definition.departure_time
    schedule.is_active = updated_definition.is_active
    schedule.updated_at = timestamp

    schedule_exceptions = db.execute(
        select(TransportVehicleScheduleException).where(
            TransportVehicleScheduleException.vehicle_schedule_id == schedule.id
        )
    ).scalars().all()
    for schedule_exception in schedule_exceptions:
        db.delete(schedule_exception)

    if len(active_scopes) == 1:
        vehicle.service_scope = next(iter(active_scopes))

    db.flush()
    return schedule


def find_transport_vehicle_schedule(
    db: Session,
    *,
    vehicle: Vehicle,
    service_date: date,
    route_kind: str,
    service_scope: str | None = None,
) -> TransportVehicleSchedule | None:
    schedule_query = select(TransportVehicleSchedule).where(
        TransportVehicleSchedule.vehicle_id == vehicle.id,
        TransportVehicleSchedule.route_kind == route_kind,
        TransportVehicleSchedule.is_active.is_(True),
    )
    if service_scope is not None:
        schedule_query = schedule_query.where(TransportVehicleSchedule.service_scope == service_scope)

    schedules = db.execute(schedule_query).scalars().all()
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