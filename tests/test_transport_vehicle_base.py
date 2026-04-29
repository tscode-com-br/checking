from datetime import date

from sistema.app.models import Vehicle
from sistema.app.schemas import TransportVehicleCreate
from sistema.app.services.transport_vehicle_base import (
    apply_transport_vehicle_base_data,
    build_transport_vehicle_base_data_from_payload,
    vehicle_base_data_matches,
)


def test_transport_vehicle_base_data_ignores_operational_fields():
    regular_payload = TransportVehicleCreate(
        service_scope="regular",
        service_date=date(2026, 4, 17),
        tipo="van",
        placa="BAS2101",
        color="White",
        lugares=12,
        tolerance=8,
    )
    weekend_payload = TransportVehicleCreate(
        service_scope="weekend",
        service_date=date(2026, 4, 18),
        every_saturday=True,
        tipo="van",
        placa="BAS2101",
        color="White",
        lugares=12,
        tolerance=8,
    )

    assert build_transport_vehicle_base_data_from_payload(regular_payload).model_dump() == {
        "placa": "BAS2101",
        "tipo": "van",
        "color": "White",
        "lugares": 12,
        "tolerance": 8,
    }
    assert (
        build_transport_vehicle_base_data_from_payload(regular_payload).model_dump()
        == build_transport_vehicle_base_data_from_payload(weekend_payload).model_dump()
    )


def test_transport_vehicle_base_matching_ignores_legacy_service_scope_mirror():
    vehicle = Vehicle(
        placa="BAS2102",
        tipo="minivan",
        color="Silver",
        lugares=7,
        tolerance=10,
        service_scope="regular",
    )
    weekend_payload = TransportVehicleCreate(
        service_scope="weekend",
        service_date=date(2026, 4, 18),
        every_saturday=True,
        tipo="minivan",
        placa="BAS2102",
        color="Silver",
        lugares=7,
        tolerance=10,
    )
    base_data = build_transport_vehicle_base_data_from_payload(weekend_payload)

    assert vehicle_base_data_matches(vehicle, base_data)

    apply_transport_vehicle_base_data(vehicle, base_data)

    assert vehicle.service_scope == "regular"
