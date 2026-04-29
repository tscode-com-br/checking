from __future__ import annotations

from collections import Counter
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..models import TransportAssignment, User, Vehicle
from ..schemas import TransportVehicleBaseData, TransportVehicleBaseRow, TransportVehicleCreate, TransportVehicleUpdate
from .time_utils import now_sgt


_ROUTE_KIND_TO_LABEL = {
    "home_to_work": "Home to Work",
    "work_to_home": "Work to Home",
}
_TRANSPORT_VEHICLE_PENDING_FIELD_ORDER = ("tipo", "placa", "color", "lugares", "tolerance")
_TRANSPORT_VEHICLE_READY_FIELD_ORDER = ("tipo", "placa", "lugares", "tolerance")


def _resolve_vehicle_field_value(source: object, field_name: str) -> object:
    if isinstance(source, dict):
        return source.get(field_name)
    return getattr(source, field_name, None)


def _is_transport_vehicle_field_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def build_transport_vehicle_pending_fields(source: object) -> list[str]:
    return [
        field_name
        for field_name in _TRANSPORT_VEHICLE_PENDING_FIELD_ORDER
        if _is_transport_vehicle_field_missing(_resolve_vehicle_field_value(source, field_name))
    ]


def is_transport_vehicle_ready_for_allocation(source: object) -> bool:
    return all(
        not _is_transport_vehicle_field_missing(_resolve_vehicle_field_value(source, field_name))
        for field_name in _TRANSPORT_VEHICLE_READY_FIELD_ORDER
    )


def build_transport_vehicle_base_data_from_payload(payload: TransportVehicleCreate) -> TransportVehicleBaseData:
    return TransportVehicleBaseData(
        placa=payload.placa,
        tipo=payload.tipo,
        color=payload.color,
        lugares=payload.lugares,
        tolerance=payload.tolerance,
    )


def build_transport_vehicle_base_row(vehicle: Vehicle) -> TransportVehicleBaseRow:
    return TransportVehicleBaseRow(
        id=vehicle.id,
        placa=vehicle.placa,
        tipo=vehicle.tipo,
        color=vehicle.color,
        lugares=vehicle.lugares,
        tolerance=vehicle.tolerance,
        pending_fields=build_transport_vehicle_pending_fields(vehicle),
        is_ready_for_allocation=is_transport_vehicle_ready_for_allocation(vehicle),
    )


def apply_transport_vehicle_base_data(vehicle: Vehicle, base_data: TransportVehicleBaseData) -> None:
    vehicle.placa = base_data.placa
    vehicle.tipo = base_data.tipo
    vehicle.color = base_data.color
    vehicle.lugares = base_data.lugares
    vehicle.tolerance = base_data.tolerance


def vehicle_base_data_matches(vehicle: Vehicle, base_data: TransportVehicleBaseData) -> bool:
    return (
        vehicle.placa == base_data.placa
        and vehicle.tipo == base_data.tipo
        and vehicle.color == base_data.color
        and vehicle.lugares == base_data.lugares
        and vehicle.tolerance == base_data.tolerance
    )


def sync_vehicle_legacy_service_scope(vehicle: Vehicle, service_scope: str) -> None:
    vehicle.service_scope = service_scope


def resolve_vehicle_for_user_transport_link(
    db: Session,
    *,
    vehicle_id: int | None,
    plate: str | None,
) -> Vehicle | None:
    if vehicle_id is not None:
        vehicle = db.get(Vehicle, vehicle_id)
        if vehicle is None:
            raise ValueError("Vehicle not found for the provided id.")
        if plate is not None and vehicle.placa != plate:
            raise ValueError("The provided vehicle_id does not match the provided plate.")
        return vehicle

    if plate is None:
        return None

    vehicle = db.execute(select(Vehicle).where(Vehicle.placa == plate)).scalar_one_or_none()
    if vehicle is None:
        raise ValueError("Vehicle not found for the provided plate.")
    return vehicle


def sync_user_vehicle_reference(user: User, vehicle: Vehicle | None) -> None:
    user.vehicle_id = vehicle.id if vehicle is not None else None
    user.placa = vehicle.placa if vehicle is not None else None


def list_users_linked_to_vehicle(db: Session, *, vehicle: Vehicle) -> list[User]:
    predicates = [User.vehicle_id == vehicle.id]
    if vehicle.placa is not None:
        predicates.append(and_(User.vehicle_id.is_(None), User.placa == vehicle.placa))

    return db.execute(select(User).where(or_(*predicates))).scalars().all()


def sync_users_vehicle_reference(users: list[User], vehicle: Vehicle | None) -> None:
    for linked_user in users:
        sync_user_vehicle_reference(linked_user, vehicle)


def _future_confirmed_assignment_slots(
    db: Session,
    *,
    vehicle: Vehicle,
) -> list[tuple[date, str, int]]:
    today = now_sgt().date()
    future_confirmed_assignments = db.execute(
        select(TransportAssignment).where(
            TransportAssignment.vehicle_id == vehicle.id,
            TransportAssignment.status == "confirmed",
            TransportAssignment.service_date >= today,
        )
    ).scalars().all()
    if not future_confirmed_assignments:
        return []

    assignments_per_service_slot = Counter(
        (assignment.service_date, assignment.route_kind)
        for assignment in future_confirmed_assignments
    )
    return [
        (service_date, route_kind, assigned_count)
        for (service_date, route_kind), assigned_count in sorted(assignments_per_service_slot.items())
    ]


def _format_future_confirmed_assignment_slot(service_date: date, route_kind: str, details: str) -> str:
    route_label = _ROUTE_KIND_TO_LABEL.get(route_kind, route_kind)
    return f"{route_label} on {service_date.isoformat()} ({details})"


def _future_confirmed_assignment_capacity_conflicts(
    db: Session,
    *,
    vehicle: Vehicle,
    next_capacity: int,
) -> list[str]:
    conflicts: list[str] = []
    for service_date, route_kind, assigned_count in _future_confirmed_assignment_slots(db, vehicle=vehicle):
        if assigned_count <= next_capacity:
            continue
        conflicts.append(
            _format_future_confirmed_assignment_slot(
                service_date,
                route_kind,
                f"{assigned_count} confirmed / {next_capacity} seats",
            )
        )
    return conflicts


def update_transport_vehicle_base(
    db: Session,
    *,
    vehicle_id: int,
    payload: TransportVehicleUpdate,
) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise ValueError("Vehicle not found.")

    if payload.placa is not None:
        conflicting_vehicle = db.execute(select(Vehicle).where(Vehicle.placa == payload.placa)).scalar_one_or_none()
        if conflicting_vehicle is not None and conflicting_vehicle.id != vehicle.id:
            raise ValueError("A vehicle with this plate already exists.")

    if is_transport_vehicle_ready_for_allocation(vehicle) and not is_transport_vehicle_ready_for_allocation(payload):
        operational_conflicts = [
            _format_future_confirmed_assignment_slot(service_date, route_kind, f"{assigned_count} confirmed")
            for service_date, route_kind, assigned_count in _future_confirmed_assignment_slots(db, vehicle=vehicle)
        ]
        if operational_conflicts:
            details = "; ".join(operational_conflicts[:3])
            if len(operational_conflicts) > 3:
                details = f"{details}; ..."
            raise ValueError(
                "Cannot make the vehicle incomplete because future confirmed assignments exist: "
                f"{details}."
            )

    if payload.lugares is not None:
        capacity_conflicts = _future_confirmed_assignment_capacity_conflicts(
            db,
            vehicle=vehicle,
            next_capacity=payload.lugares,
        )
        if capacity_conflicts:
            details = "; ".join(capacity_conflicts[:3])
            if len(capacity_conflicts) > 3:
                details = f"{details}; ..."
            raise ValueError(
                "Cannot update the vehicle because confirmed assignments would exceed the new capacity: "
                f"{details}."
            )

    linked_users = list_users_linked_to_vehicle(db, vehicle=vehicle)
    apply_transport_vehicle_base_data(vehicle, payload)
    db.flush()

    sync_users_vehicle_reference(linked_users, vehicle)

    return vehicle