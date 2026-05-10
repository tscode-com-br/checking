from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.core.config import Settings
from sistema.app.database import Base
from sistema.app.models import MobileAppSettings, Project, TransportAIRouteMatrix, TransportAIRoutePoint, TransportRequest, User, Vehicle, TransportVehicleSchedule
from sistema.app.services import location_settings as location_settings_module
from sistema.app.services.transport_ai_agent import (
    TRANSPORT_AI_LANGCHAIN_TOOL_NAMES,
    TransportAILangChainToolContext,
    build_transport_ai_langchain_tools,
)
from sistema.app.services.transport_ai_planning import build_transport_agent_planning_input
from sistema.app.services.transport_route_provider import FakeTransportRouteProvider


def _build_planning_settings(**overrides) -> Settings:
    values = {
        "transport_ai_max_passengers_per_run": 80,
        "transport_ai_route_provider": "fake",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _build_session_factory(db_path: Path):
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def _fixture_timestamp() -> datetime:
    return datetime(2026, 5, 2, 8, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))


def _configure_transport_settings(session: Session) -> None:
    location_settings_module.upsert_transport_vehicle_default_seat_counts(
        session,
        default_car_seats=3,
        default_minivan_seats=6,
        default_van_seats=10,
        default_bus_seats=40,
        default_tolerance_minutes=5,
    )
    location_settings_module.upsert_transport_pricing_settings(
        session,
        price_currency_code=None,
        price_rate_unit="day",
        default_car_price=120,
        default_minivan_price=180,
        default_van_price=240,
        default_bus_price=400,
    )
    settings_row = session.get(MobileAppSettings, 1)
    if settings_row is not None:
        settings_row.transport_work_to_home_time = "16:45"
        settings_row.transport_last_update_time = "16:00"
    session.flush()


def _create_project(
    session: Session,
    *,
    name: str,
    address: str,
    zip_code: str,
    country_code: str = "SG",
) -> Project:
    project = Project(
        name=name,
        country_code=country_code,
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address=address,
        zip_code=zip_code,
    )
    session.add(project)
    session.flush()
    return project


def _create_user(
    session: Session,
    *,
    chave: str,
    nome: str,
    projeto: str,
    address: str,
    zip_code: str,
) -> User:
    user = User(
        rfid=None,
        chave=chave,
        senha=None,
        perfil=0,
        admin_monitored_projects_json=None,
        nome=nome,
        projeto=projeto,
        workplace=None,
        vehicle_id=None,
        placa=None,
        end_rua=address,
        zip=zip_code,
        cargo=None,
        email=None,
        local=None,
        checkin=None,
        time=None,
        last_active_at=_fixture_timestamp(),
        inactivity_days=0,
    )
    session.add(user)
    session.flush()
    return user


def _create_transport_request(
    session: Session,
    *,
    user_id: int,
    service_date: date,
    request_kind: str = "extra",
) -> TransportRequest:
    timestamp = _fixture_timestamp()
    request = TransportRequest(
        user_id=user_id,
        request_kind=request_kind,
        recurrence_kind="single_date",
        requested_time="08:00",
        selected_weekdays_json=None,
        single_date=service_date,
        created_via="admin",
        status="active",
        created_at=timestamp,
        updated_at=timestamp,
        cancelled_at=None,
    )
    session.add(request)
    session.flush()
    return request


def _create_extra_vehicle_candidate(
    session: Session,
    *,
    placa: str | None,
    service_date: date,
    color: str | None = "white",
) -> Vehicle:
    timestamp = _fixture_timestamp()
    vehicle = Vehicle(
        placa=placa,
        tipo="carro",
        color=color,
        lugares=4,
        tolerance=0,
        service_scope="extra",
    )
    session.add(vehicle)
    session.flush()

    schedule = TransportVehicleSchedule(
        vehicle_id=vehicle.id,
        service_scope="extra",
        route_kind="home_to_work",
        recurrence_kind="single_date",
        service_date=service_date,
        weekday=None,
        departure_time="07:30",
        is_active=True,
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(schedule)
    session.flush()
    return vehicle


def _build_tool_context(
    session: Session,
    *,
    service_date: date,
    settings_obj: Settings | None = None,
    provider: FakeTransportRouteProvider | None = None,
) -> TransportAILangChainToolContext:
    effective_settings = settings_obj or _build_planning_settings()
    effective_provider = provider or FakeTransportRouteProvider(settings_obj=effective_settings)
    return TransportAILangChainToolContext(
        db=session,
        service_date=service_date,
        route_kind="home_to_work",
        earliest_boarding_time="06:50",
        arrival_at_work_time="07:45",
        settings_obj=effective_settings,
        provider=effective_provider,
    )


def _build_tools_by_name(context: TransportAILangChainToolContext):
    return {
        tool.name: tool
        for tool in build_transport_ai_langchain_tools(context=context)
    }


def test_load_planning_input_tool_returns_expected_hash_and_tool_names(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_tools_load.db")
    try:
        service_date = date(2026, 5, 3)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name="PPLAN1", address="1 Marina Boulevard", zip_code="018989")
            user = _create_user(
                session,
                chave="TA01",
                nome="Tool Worker One",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7001A", service_date=service_date)
            session.commit()

            context = _build_tool_context(session, service_date=service_date)
            tools_by_name = _build_tools_by_name(context)
            load_result = tools_by_name["load_planning_input"].invoke({})
            repeated_load_result = tools_by_name["load_planning_input"].invoke({})

        assert set(tools_by_name) == set(TRANSPORT_AI_LANGCHAIN_TOOL_NAMES)
        assert load_result["ok"] is True
        assert load_result["planning_input_hash"] == repeated_load_result["planning_input_hash"]
        assert load_result["planning_input_hash"] == context.state.planning_input.planning_input_hash
        assert load_result["total_requests"] == 1
        assert load_result["total_candidate_vehicles"] == 1
    finally:
        engine.dispose()


def test_geocode_route_points_tool_uses_fake_provider_without_persisting_cache_rows(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_tools_geocode.db")
    try:
        service_date = date(2026, 5, 4)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name="PPLAN1", address="1 Marina Boulevard", zip_code="018989")
            user = _create_user(
                session,
                chave="TA02",
                nome="Tool Worker Two",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7002A", service_date=service_date)
            session.commit()

            context = _build_tool_context(
                session,
                service_date=service_date,
                provider=FakeTransportRouteProvider(settings_obj=_build_planning_settings(), allow_synthetic_geocode=False),
            )
            tools_by_name = _build_tools_by_name(context)
            load_result = tools_by_name["load_planning_input"].invoke({})
            geocode_result = tools_by_name["geocode_route_points"].invoke(
                {"planning_input_hash": load_result["planning_input_hash"]}
            )
            route_point_count = session.query(TransportAIRoutePoint).count()

        assert geocode_result["ok"] is True
        assert geocode_result["provider"] == "fake"
        assert geocode_result["total_resolved_points"] == 2
        assert route_point_count == 0
    finally:
        engine.dispose()


def test_build_route_matrices_tool_keeps_database_unchanged_and_returns_matrix_summary(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_tools_matrices.db")
    try:
        service_date = date(2026, 5, 5)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name="PPLAN1", address="1 Marina Boulevard", zip_code="018989")
            user = _create_user(
                session,
                chave="TA03",
                nome="Tool Worker Three",
                projeto=project.name,
                address="25 Raffles Place",
                zip_code="048621",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7003A", service_date=service_date)
            session.commit()

            context = _build_tool_context(
                session,
                service_date=service_date,
                provider=FakeTransportRouteProvider(settings_obj=_build_planning_settings(), allow_synthetic_geocode=False),
            )
            tools_by_name = _build_tools_by_name(context)
            load_result = tools_by_name["load_planning_input"].invoke({})
            planning_input_hash = load_result["planning_input_hash"]
            tools_by_name["geocode_route_points"].invoke({"planning_input_hash": planning_input_hash})
            matrix_result = tools_by_name["build_route_matrices"].invoke({"planning_input_hash": planning_input_hash})
            matrix_cache_count = session.query(TransportAIRouteMatrix).count()

        assert matrix_result["ok"] is True
        assert matrix_result["total_matrices"] == 1
        assert matrix_result["partitions"][0]["point_count"] == 2
        assert matrix_cache_count == 0
    finally:
        engine.dispose()


def test_solve_transport_plan_tool_returns_deterministic_plan_without_calling_apply(tmp_path, monkeypatch):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_tools_solve.db")
    try:
        service_date = date(2026, 5, 6)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name="PPLAN1", address="1 Marina Boulevard", zip_code="018989")
            user_one = _create_user(
                session,
                chave="TA04",
                nome="Tool Worker Four",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            user_two = _create_user(
                session,
                chave="TA05",
                nome="Tool Worker Five",
                projeto=project.name,
                address="25 Raffles Place",
                zip_code="048621",
            )
            _create_transport_request(session, user_id=user_one.id, service_date=service_date)
            _create_transport_request(session, user_id=user_two.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7004A", service_date=service_date)
            session.commit()

            import sistema.app.services.transport_proposals as transport_proposals

            monkeypatch.setattr(
                transport_proposals,
                "apply_transport_operational_proposal",
                lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("apply must not be called by LangChain tools")),
            )

            context = _build_tool_context(
                session,
                service_date=service_date,
                provider=FakeTransportRouteProvider(settings_obj=_build_planning_settings(), allow_synthetic_geocode=False),
            )
            tools_by_name = _build_tools_by_name(context)
            planning_input_hash = tools_by_name["load_planning_input"].invoke({})["planning_input_hash"]
            tools_by_name["geocode_route_points"].invoke({"planning_input_hash": planning_input_hash})
            tools_by_name["build_route_matrices"].invoke({"planning_input_hash": planning_input_hash})
            first_result = tools_by_name["solve_transport_plan"].invoke({"planning_input_hash": planning_input_hash})
            second_result = tools_by_name["solve_transport_plan"].invoke({"planning_input_hash": planning_input_hash})

        assert first_result["ok"] is True
        assert first_result["plan"]["plan_key"] == second_result["plan"]["plan_key"]
        assert first_result["total_routes"] == 1
        assert first_result["total_passenger_allocations"] == 2
        assert first_result["plan"]["vehicle_actions"][0]["action_type"] == "keep"
    finally:
        engine.dispose()


def test_solve_transport_plan_tool_keeps_existing_vehicle_without_plate_and_color(tmp_path, monkeypatch):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_tools_partial_vehicle_solve.db")
    try:
        service_date = date(2026, 5, 6)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name="PPLAN-PARTIAL", address="1 Marina Boulevard", zip_code="018989")
            user_one = _create_user(
                session,
                chave="TB41",
                nome="Tool Partial Worker One",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            user_two = _create_user(
                session,
                chave="TB42",
                nome="Tool Partial Worker Two",
                projeto=project.name,
                address="25 Raffles Place",
                zip_code="048621",
            )
            _create_transport_request(session, user_id=user_one.id, service_date=service_date)
            _create_transport_request(session, user_id=user_two.id, service_date=service_date)
            vehicle = _create_extra_vehicle_candidate(
                session,
                placa=None,
                color=None,
                service_date=service_date,
            )
            session.commit()

            import sistema.app.services.transport_proposals as transport_proposals

            monkeypatch.setattr(
                transport_proposals,
                "apply_transport_operational_proposal",
                lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("apply must not be called by LangChain tools")),
            )

            context = _build_tool_context(
                session,
                service_date=service_date,
                provider=FakeTransportRouteProvider(settings_obj=_build_planning_settings(), allow_synthetic_geocode=False),
            )
            tools_by_name = _build_tools_by_name(context)
            planning_input_hash = tools_by_name["load_planning_input"].invoke({})["planning_input_hash"]

            planning_input = context.state.planning_input
            assert planning_input is not None
            planning_vehicle = planning_input.partitions[0].candidate_vehicles[0]
            assert planning_vehicle.vehicle_id == vehicle.id
            assert planning_vehicle.plate is None
            assert planning_vehicle.pending_fields == ["placa", "color"]
            assert planning_vehicle.is_ready_for_allocation is True

            tools_by_name["geocode_route_points"].invoke({"planning_input_hash": planning_input_hash})
            tools_by_name["build_route_matrices"].invoke({"planning_input_hash": planning_input_hash})
            result = tools_by_name["solve_transport_plan"].invoke({"planning_input_hash": planning_input_hash})

        assert result["ok"] is True
        assert result["total_routes"] == 1
        assert result["total_passenger_allocations"] == 2
        assert result["plan"]["vehicle_actions"][0]["action_type"] == "keep"
        assert result["plan"]["vehicle_actions"][0]["vehicle_id"] == vehicle.id
        assert result["plan"]["passenger_allocations"][0]["vehicle_ref"] == f"existing:{vehicle.id}"
        assert result["plan"]["route_itineraries"][0]["plate"] is None
    finally:
        engine.dispose()


def test_transport_ai_temporary_plate_generator_uses_sequential_placeholder_namespace(tmp_path):
    from sistema.app.routers.transport_ai import _generate_transport_ai_temporary_plate

    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_tools_placeholder_generator.db")
    try:
        service_date = date(2026, 5, 6)
        with session_factory() as session:
            _configure_transport_settings(session)
            _create_extra_vehicle_candidate(session, placa="Plate 001", service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="Plate 002", service_date=service_date)
            session.commit()

            home_run = SimpleNamespace(id=11, service_date=service_date, route_kind="home_to_work")
            work_run = SimpleNamespace(id=77, service_date=date(2026, 5, 10), route_kind="work_to_home")

            assert _generate_transport_ai_temporary_plate(session, run=home_run, sequence=1) == "Plate 003"
            assert _generate_transport_ai_temporary_plate(session, run=work_run, sequence=1) == "Plate 003"
    finally:
        engine.dispose()


def test_apply_transport_ai_vehicle_create_actions_uses_placeholder_sequence_and_allows_missing_color(tmp_path):
    from sistema.app.routers.transport_ai import apply_transport_ai_vehicle_create_actions

    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_tools_placeholder_create.db")
    try:
        service_date = date(2026, 5, 6)
        with session_factory() as session:
            _configure_transport_settings(session)
            _create_extra_vehicle_candidate(session, placa="Plate 001", service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="Plate 002", service_date=service_date)
            session.commit()

            run = SimpleNamespace(
                id=91,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
            )
            action = SimpleNamespace(
                action_key="action:create-placeholder-sequence",
                action_type="create",
                service_scope="extra",
                vehicle_id=None,
                client_vehicle_key="placeholder-sequence",
                after={
                    "vehicle_type": "carro",
                    "capacity": 4,
                    "route_kind": "home_to_work",
                    "color": None,
                },
            )
            itinerary = SimpleNamespace(
                vehicle_ref="new:placeholder-sequence",
                service_scope="extra",
                route_kind="home_to_work",
                projected_arrival_time="08:15",
                stops=[
                    SimpleNamespace(scheduled_time="07:55"),
                    SimpleNamespace(scheduled_time="08:15"),
                ],
            )
            plan = SimpleNamespace(vehicle_actions=[action], route_itineraries=[itinerary])

            vehicle_id_by_ref, issues, created_vehicle_ids, audit_entries = apply_transport_ai_vehicle_create_actions(
                session,
                run=run,
                plan=plan,
                created_at=_fixture_timestamp(),
            )
            session.commit()

            assert issues == []
            assert vehicle_id_by_ref == {"new:placeholder-sequence": created_vehicle_ids[0]}
            assert len(created_vehicle_ids) == 1

            created_vehicle = session.get(Vehicle, created_vehicle_ids[0])
            assert created_vehicle is not None
            assert created_vehicle.color is None
            assert created_vehicle.placa == "PLATE 003"

            assert len(audit_entries) == 1
            assert audit_entries[0]["vehicle_ref"] == "new:placeholder-sequence"
            assert audit_entries[0]["create_payload"]["color"] is None
            assert audit_entries[0]["create_payload"]["placa"] == "PLATE 003"
    finally:
        engine.dispose()


def test_validate_transport_plan_and_build_change_summary_tools_return_expected_summaries(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_tools_validate.db")
    try:
        service_date = date(2026, 5, 7)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name="PPLAN1", address="1 Marina Boulevard", zip_code="018989")
            user_one = _create_user(
                session,
                chave="TA06",
                nome="Tool Worker Six",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            user_two = _create_user(
                session,
                chave="TA07",
                nome="Tool Worker Seven",
                projeto=project.name,
                address="25 Raffles Place",
                zip_code="048621",
            )
            _create_transport_request(session, user_id=user_one.id, service_date=service_date)
            _create_transport_request(session, user_id=user_two.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7005A", service_date=service_date)
            session.commit()

            context = _build_tool_context(
                session,
                service_date=service_date,
                provider=FakeTransportRouteProvider(settings_obj=_build_planning_settings(), allow_synthetic_geocode=False),
            )
            tools_by_name = _build_tools_by_name(context)
            planning_input_hash = tools_by_name["load_planning_input"].invoke({})["planning_input_hash"]
            tools_by_name["geocode_route_points"].invoke({"planning_input_hash": planning_input_hash})
            tools_by_name["build_route_matrices"].invoke({"planning_input_hash": planning_input_hash})
            solve_result = tools_by_name["solve_transport_plan"].invoke({"planning_input_hash": planning_input_hash})
            plan_key = solve_result["plan_key"]
            validate_result = tools_by_name["validate_transport_plan"].invoke({"plan_key": plan_key})
            change_summary_result = tools_by_name["build_change_summary"].invoke({"plan_key": plan_key})

        assert validate_result["ok"] is True
        assert validate_result["can_apply"] is True
        assert validate_result["allocated_request_count"] == 2
        assert validate_result["unaccounted_request_ids"] == []
        assert change_summary_result["ok"] is True
        assert change_summary_result["change_summary"]["keep_count"] == 1
        assert change_summary_result["cost_summary"]["suggested_vehicle_count"] == 1
        assert change_summary_result["vehicle_action_preview"][0]["action_type"] == "keep"
    finally:
        engine.dispose()


def test_transport_ai_langchain_tools_return_structured_issue_when_state_is_missing(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_tools_state_missing.db")
    try:
        service_date = date(2026, 5, 8)
        with session_factory() as session:
            _configure_transport_settings(session)
            session.commit()

            context = _build_tool_context(session, service_date=service_date)
            tools_by_name = _build_tools_by_name(context)
            result = tools_by_name["build_route_matrices"].invoke({"planning_input_hash": "a" * 64})

        assert result["ok"] is False
        assert result["issues"][0]["code"] == "transport_ai_tool_state_missing"
    finally:
        engine.dispose()