from datetime import date

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from sistema.app.database import Base
from sistema.app.schemas import TransportVehicleCreate, _normalize_optional_plate
from sistema.app.services.transport_vehicle_operations import create_transport_vehicle_registration


def _build_session_factory(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path.as_posix()}"
    engine = sa.create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def test_normalize_optional_plate_accepts_literal_placeholder_namespace():
    assert _normalize_optional_plate("  Plate   001  ") == "PLATE 001"


def test_normalize_optional_plate_keeps_manual_plates_compact():
    assert _normalize_optional_plate("  sba 7001a  ") == "SBA7001A"


def test_normalize_optional_plate_rejects_invalid_placeholder_characters():
    with pytest.raises(ValueError, match="A placa deve conter apenas letras, numeros, '-' e '.'"):
        _normalize_optional_plate("Plate_001")


def test_transport_vehicle_registration_persists_literal_placeholder_and_detects_conflict_by_normalized_variant(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_vehicle_plate_validation.db")
    try:
        with session_factory() as session:
            first_payload = TransportVehicleCreate(
                service_scope="extra",
                service_date=date(2026, 4, 17),
                route_kind="work_to_home",
                departure_time="17:45",
                tipo="carro",
                placa="Plate 001",
                color="Orange",
                lugares=4,
                tolerance=6,
            )
            vehicle, schedules = create_transport_vehicle_registration(session, payload=first_payload)
            session.commit()

            assert vehicle.placa == "PLATE 001"
            assert len(schedules) == 1

            duplicate_payload = TransportVehicleCreate(
                service_scope="regular",
                service_date=date(2026, 4, 17),
                tipo="carro",
                placa="  plate   001  ",
                color="Orange",
                lugares=4,
                tolerance=6,
            )
            with pytest.raises(ValueError, match="A vehicle with this plate already exists in another list"):
                create_transport_vehicle_registration(session, payload=duplicate_payload)
    finally:
        engine.dispose()