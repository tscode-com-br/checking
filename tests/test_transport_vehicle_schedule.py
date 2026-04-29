from datetime import date

import pytest

from sistema.app.models import TransportVehicleSchedule, Vehicle
from sistema.app.schemas import TransportVehicleCreate, TransportVehicleScheduleDefinition
from sistema.app.services.time_utils import now_sgt
from sistema.app.services.transport_vehicle_schedule import (
    build_transport_vehicle_schedule_definitions_from_payload,
    resolve_transport_vehicle_operational_scope,
    vehicle_supports_transport_service_scope,
)


def test_transport_vehicle_schedule_definitions_expand_regular_payload_into_two_weekday_routes():
    payload = TransportVehicleCreate(
        service_scope="regular",
        service_date=date(2026, 4, 17),
        tipo="van",
        placa="SCH2201",
        color="White",
        lugares=10,
        tolerance=8,
    )

    definitions = build_transport_vehicle_schedule_definitions_from_payload(payload)

    assert [definition.route_kind for definition in definitions] == ["home_to_work", "work_to_home"]
    assert all(definition.recurrence_kind == "weekday" for definition in definitions)
    assert all(definition.service_scope == "regular" for definition in definitions)
    assert all(definition.departure_time is None for definition in definitions)


def test_transport_vehicle_schedule_definition_requires_departure_time_for_extra_scope():
    with pytest.raises(ValueError, match="departure_time is required for extra schedules"):
        TransportVehicleScheduleDefinition(
            service_scope="extra",
            route_kind="work_to_home",
            recurrence_kind="single_date",
            service_date=date(2026, 4, 17),
            weekday=None,
            departure_time=None,
            is_active=True,
        )


def test_transport_vehicle_operational_scope_prefers_active_schedule_scope_over_legacy_vehicle_mirror():
    timestamp = now_sgt()
    vehicle = Vehicle(
        placa="SCH2202",
        tipo="van",
        color="White",
        lugares=10,
        tolerance=8,
        service_scope="extra",
    )
    regular_schedule = TransportVehicleSchedule(
        vehicle_id=1,
        service_scope="regular",
        route_kind="work_to_home",
        recurrence_kind="weekday",
        service_date=None,
        weekday=None,
        departure_time=None,
        is_active=True,
        created_at=timestamp,
        updated_at=timestamp,
    )

    assert resolve_transport_vehicle_operational_scope(vehicle=vehicle, schedules=[regular_schedule]) == "regular"
    assert vehicle_supports_transport_service_scope(
        vehicle=vehicle,
        service_scope="regular",
        schedules=[regular_schedule],
    )
    assert not vehicle_supports_transport_service_scope(
        vehicle=vehicle,
        service_scope="extra",
        schedules=[regular_schedule],
    )