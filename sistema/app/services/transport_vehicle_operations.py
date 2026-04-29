from __future__ import annotations

from datetime import date

from sqlalchemy import MetaData, Table, delete, inspect, select, update
from sqlalchemy.orm import Session

from ..models import (
    TransportAssignment,
    TransportVehicleSchedule,
    TransportVehicleScheduleException,
    User,
    Vehicle,
)
from ..schemas import TransportVehicleCreate
from .transport_vehicle_base import (
    apply_transport_vehicle_base_data,
    build_transport_vehicle_base_data_from_payload,
    list_users_linked_to_vehicle,
    sync_vehicle_legacy_service_scope,
    sync_users_vehicle_reference,
    vehicle_base_data_matches,
)
from .transport_vehicle_schedule import (
    build_transport_vehicle_schedule_conflict_details as build_transport_vehicle_schedule_conflict_details_impl,
    build_transport_vehicle_schedule_definitions_from_payload,
    build_transport_vehicle_schedule_model,
    classify_transport_vehicle_schedules_for_reuse as classify_transport_vehicle_schedules_for_reuse_impl,
    find_transport_vehicle_schedule as find_transport_vehicle_schedule_impl,
    format_transport_vehicle_schedule_conflict_entry as format_transport_vehicle_schedule_conflict_entry_impl,
    vehicle_has_active_schedule_for_definition,
    vehicle_has_active_schedule_on_date as vehicle_has_active_schedule_on_date_impl,
    vehicle_schedule_applies_to_date as vehicle_schedule_applies_to_date_impl,
)


_PAIRED_ROUTE_KIND = {
    "home_to_work": "work_to_home",
    "work_to_home": "home_to_work",
}


def vehicle_schedule_applies_to_date(schedule: TransportVehicleSchedule, service_date: date) -> bool:
    return vehicle_schedule_applies_to_date_impl(schedule, service_date)


def create_transport_vehicle_registration(
    db: Session,
    *,
    payload: TransportVehicleCreate,
) -> tuple[Vehicle, list[TransportVehicleSchedule]]:
    from .transport import now_sgt as transport_now_sgt

    timestamp = transport_now_sgt()
    base_data = build_transport_vehicle_base_data_from_payload(payload)
    vehicle = None
    if payload.placa is not None:
        vehicle = db.execute(select(Vehicle).where(Vehicle.placa == payload.placa)).scalar_one_or_none()

    if vehicle is None:
        vehicle = Vehicle(
            placa=base_data.placa,
            tipo=base_data.tipo,
            color=base_data.color,
            lugares=base_data.lugares,
            tolerance=base_data.tolerance,
            service_scope=payload.service_scope,
        )
        db.add(vehicle)
        db.flush()
    else:
        blocking_schedules, reusable_schedules = classify_transport_vehicle_schedules_for_reuse_impl(
            db,
            vehicle_id=vehicle.id,
            reference_date=payload.service_date,
        )
        if not blocking_schedules:
            for schedule in reusable_schedules:
                schedule.is_active = False
                schedule.updated_at = timestamp

            apply_transport_vehicle_base_data(vehicle, base_data)
            sync_vehicle_legacy_service_scope(vehicle, payload.service_scope)
        else:
            schedule_details = build_transport_vehicle_schedule_conflict_details_impl(blocking_schedules)
            blocking_scopes = {schedule.service_scope for schedule in blocking_schedules}
            if any(scope != payload.service_scope for scope in blocking_scopes):
                raise ValueError(
                    f"A vehicle with this plate already exists in another list: {schedule_details}."
                )
            if not vehicle_base_data_matches(vehicle, base_data):
                raise ValueError(
                    "A vehicle with this plate already exists with a different configuration: "
                    f"{schedule_details}."
                )

    created_schedules: list[TransportVehicleSchedule] = []
    for schedule_definition in build_transport_vehicle_schedule_definitions_from_payload(payload):
        if vehicle_has_active_schedule_for_definition(
            db,
            vehicle_id=vehicle.id,
            definition=schedule_definition,
        ):
            raise ValueError("An active vehicle already exists for the selected list and recurrence pattern.")

        schedule = build_transport_vehicle_schedule_model(
            vehicle_id=vehicle.id,
            definition=schedule_definition,
            timestamp=timestamp,
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

    if vehicle.placa is not None:
        _purge_foreign_key_dependencies(
            db,
            target_table="vehicles",
            target_column="placa",
            values=[vehicle.placa],
            mode="set_null",
            excluded_tables={"transport_vehicle_schedules", "transport_assignments"},
        )

    linked_users = list_users_linked_to_vehicle(db, vehicle=vehicle)
    sync_users_vehicle_reference(linked_users, None)

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


def _build_schedule_specs_from_payload(payload: TransportVehicleCreate) -> list[dict[str, object]]:
    return [definition.model_dump() for definition in build_transport_vehicle_schedule_definitions_from_payload(payload)]


def _classify_vehicle_schedules_for_reuse(
    db: Session,
    *,
    vehicle_id: int,
    reference_date: date,
) -> tuple[list[TransportVehicleSchedule], list[TransportVehicleSchedule]]:
    return classify_transport_vehicle_schedules_for_reuse_impl(
        db,
        vehicle_id=vehicle_id,
        reference_date=reference_date,
    )


def _build_vehicle_schedule_conflict_details(schedules: list[TransportVehicleSchedule]) -> str:
    return build_transport_vehicle_schedule_conflict_details_impl(schedules)


def _format_vehicle_schedule_conflict_entry(schedule: TransportVehicleSchedule) -> str:
    return format_transport_vehicle_schedule_conflict_entry_impl(schedule)


def _vehicle_has_active_schedule_for_spec(
    db: Session,
    *,
    vehicle_id: int,
    schedule_spec: dict[str, object],
) -> bool:
    from ..schemas import TransportVehicleScheduleDefinition

    return vehicle_has_active_schedule_for_definition(
        db,
        vehicle_id=vehicle_id,
        definition=TransportVehicleScheduleDefinition(**schedule_spec),
    )


def _vehicle_has_active_schedule_on_date(
    db: Session,
    *,
    vehicle_id: int,
    service_scope: str,
    route_kind: str,
    service_date: date,
) -> bool:
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
    return find_transport_vehicle_schedule_impl(
        db,
        vehicle=vehicle,
        service_date=service_date,
        route_kind=route_kind,
        service_scope=service_scope,
    )


def get_paired_route_kind(route_kind: str) -> str | None:
    return _PAIRED_ROUTE_KIND.get(route_kind)
