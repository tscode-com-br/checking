from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.core.config import Settings, settings
from sistema.app.models import TransportAIRouteMatrix, TransportAIRoutePoint
from sistema.app.services.transport_route_cache import (
    get_cached_transport_ai_route_matrix,
    get_cached_transport_ai_route_point,
    normalize_transport_ai_route_point_query,
    upsert_transport_ai_route_matrix,
    upsert_transport_ai_route_point,
)


def _build_database_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path.as_posix()}"


def _upgrade_database_to_head(database_url: str) -> None:
    config = Config("alembic.ini")
    previous_database_url = settings.database_url
    settings.database_url = database_url

    try:
        command.upgrade(config, "head")
    finally:
        settings.database_url = previous_database_url


def _build_session_factory(tmp_path: Path) -> tuple[sessionmaker[Session], sa.Engine]:
    database_url = _build_database_url(tmp_path / "transport_ai_route_cache.db")
    _upgrade_database_to_head(database_url)
    engine = sa.create_engine(database_url)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False), engine


def _build_cache_settings(**overrides) -> Settings:
    values = {
        "mapbox_geocoding_permanent": False,
        "transport_ai_geocode_cache_ttl_days": 30,
        "transport_ai_route_cache_ttl_seconds": 3600,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_transport_ai_route_cache_migration_upgrades_head_on_sqlite(tmp_path):
    database_url = _build_database_url(tmp_path / "transport_ai_route_cache_head.db")

    _upgrade_database_to_head(database_url)

    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)
    route_point_indexes = {index["name"]: index for index in inspector.get_indexes("transport_ai_route_points")}
    route_matrix_indexes = {index["name"]: index for index in inspector.get_indexes("transport_ai_route_matrices")}
    engine.dispose()

    assert inspector.has_table("transport_ai_route_points")
    assert inspector.has_table("transport_ai_route_matrices")
    assert route_point_indexes["ix_transport_ai_route_points_point_key"]["unique"]
    assert route_matrix_indexes["ix_transport_ai_route_matrices_matrix_key"]["unique"]


def test_transport_ai_route_point_cache_hits_for_same_normalized_address(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    cache_settings = _build_cache_settings()
    reference_time = datetime(2026, 4, 30, 11, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        persisted_point = upsert_transport_ai_route_point(
            session,
            source_id=101,
            point_type="passenger_origin",
            address=" 10   Bayfront Avenue ",
            zip_code=" 018956 ",
            country_code="sg",
            country_name=" Singapore ",
            longitude=103.8607,
            latitude=1.2834,
            provider="mapbox",
            provider_place_id="place-001",
            confidence=0.95,
            settings_obj=cache_settings,
            created_at=reference_time,
        )
        session.commit()

        cached_point = get_cached_transport_ai_route_point(
            session,
            provider=" mapbox ",
            address="10 Bayfront Avenue",
            zip_code="018956",
            country_name="singapore",
            reference_time=reference_time + timedelta(hours=1),
        )

    engine.dispose()

    assert cached_point is not None
    assert cached_point.id == persisted_point.id
    assert cached_point.normalized_query == normalize_transport_ai_route_point_query(
        address="10 Bayfront Avenue",
        zip_code="018956",
        country_name="Singapore",
    )


def test_transport_ai_route_point_cache_misses_for_different_address(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    cache_settings = _build_cache_settings()
    reference_time = datetime(2026, 4, 30, 11, 15, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        upsert_transport_ai_route_point(
            session,
            source_id=102,
            point_type="project_destination",
            address="1 Marina Boulevard",
            zip_code="018989",
            country_code="SG",
            country_name="Singapore",
            longitude=103.8545,
            latitude=1.2823,
            provider="mapbox",
            confidence=0.88,
            settings_obj=cache_settings,
            created_at=reference_time,
        )
        session.commit()

        cached_point = get_cached_transport_ai_route_point(
            session,
            provider="mapbox",
            address="10 Bayfront Avenue",
            zip_code="018956",
            country_name="Singapore",
            reference_time=reference_time + timedelta(minutes=5),
        )

    engine.dispose()

    assert cached_point is None


def test_transport_ai_route_matrix_cache_expires_and_is_not_reused(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    cache_settings = _build_cache_settings(transport_ai_route_cache_ttl_seconds=60)
    reference_time = datetime(2026, 4, 30, 11, 30, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    sources = [(103.8607, 1.2834), (103.8545, 1.2823)]
    destinations = [(103.8519, 1.2903)]

    with session_factory() as session:
        persisted_matrix = upsert_transport_ai_route_matrix(
            session,
            provider="mapbox",
            profile="mapbox/driving-traffic",
            sources=sources,
            destinations=destinations,
            durations=[[0, 480, 660], [470, 0, 540]],
            distances=[[0, 2500, 3100], [2400, 0, 2800]],
            settings_obj=cache_settings,
            created_at=reference_time,
        )
        session.commit()

        cached_before_expiry = get_cached_transport_ai_route_matrix(
            session,
            provider="mapbox",
            profile="mapbox/driving-traffic",
            sources=sources,
            destinations=destinations,
            reference_time=reference_time + timedelta(seconds=30),
        )
        cached_after_expiry = get_cached_transport_ai_route_matrix(
            session,
            provider="mapbox",
            profile="mapbox/driving-traffic",
            sources=sources,
            destinations=destinations,
            reference_time=reference_time + timedelta(seconds=61),
        )

    engine.dispose()

    assert cached_before_expiry is not None
    assert cached_before_expiry.id == persisted_matrix.id
    assert cached_after_expiry is None


def test_transport_ai_route_matrix_cache_hits_for_same_coordinates_and_profile(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    cache_settings = _build_cache_settings(transport_ai_route_cache_ttl_seconds=600)
    reference_time = datetime(2026, 4, 30, 11, 45, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    sources = [(103.8607004, 1.2834003), (103.8545004, 1.2823001)]
    destinations = [(103.8519004, 1.2903002)]

    with session_factory() as session:
        persisted_matrix = upsert_transport_ai_route_matrix(
            session,
            provider="mapbox",
            profile="mapbox/driving",
            sources=sources,
            destinations=destinations,
            durations=[[0, 480], [470, 0]],
            distances=[[0, 2500], [2400, 0]],
            depart_at=reference_time,
            settings_obj=cache_settings,
            created_at=reference_time,
        )
        session.commit()

        cached_matrix = get_cached_transport_ai_route_matrix(
            session,
            provider="mapbox",
            profile="mapbox/driving",
            sources=[(103.86070039, 1.28340031), (103.85450039, 1.28230009)],
            destinations=[(103.85190039, 1.29030019)],
            depart_at=reference_time,
            reference_time=reference_time + timedelta(minutes=2),
        )

    engine.dispose()

    assert cached_matrix is not None
    assert cached_matrix.id == persisted_matrix.id
    assert isinstance(cached_matrix, TransportAIRouteMatrix)


def test_transport_ai_route_point_does_not_persist_raw_response_when_geocoding_is_not_permanent(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    cache_settings = _build_cache_settings(mapbox_geocoding_permanent=False)
    reference_time = datetime(2026, 4, 30, 12, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        persisted_point = upsert_transport_ai_route_point(
            session,
            source_id=103,
            point_type="passenger_origin",
            address="25 Raffles Place",
            zip_code="048621",
            country_code="SG",
            country_name="Singapore",
            longitude=103.8520,
            latitude=1.2840,
            provider="mapbox",
            provider_place_id="place-raw-001",
            confidence=0.91,
            raw_response_json={"features": [{"id": "place-raw-001"}]},
            settings_obj=cache_settings,
            created_at=reference_time,
        )
        session.commit()

        reloaded_point = session.get(TransportAIRoutePoint, persisted_point.id)

    engine.dispose()

    assert reloaded_point is not None
    assert reloaded_point.raw_response_json is None