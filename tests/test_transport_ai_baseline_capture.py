import sistema.app.services.transport_ai_runs as transport_ai_runs_module
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.core.config import settings
from sistema.app.models import (
    AdminUser,
    MobileAppSettings,
    Project,
    TransportAIRun,
    TransportAssignment,
    TransportRequest,
    TransportVehicleSchedule,
    User,
    Vehicle,
)
from sistema.app.services.transport_ai_runs import (
    capture_transport_ai_baseline,
    reset_transport_ai_requests_to_pending,
    restore_transport_ai_baseline,
    save_transport_ai_baseline,
)
from sistema.app.schemas import TransportAgentDashboardScope
from sistema.app.services.transport_proposals import build_transport_operational_snapshot
from sistema.app.services.transport_reevaluation_events import (
    clear_transport_reevaluation_events,
    list_recent_transport_reevaluation_events,
)
from sistema.app.services.user_projects import add_user_project_membership


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
    database_url = _build_database_url(tmp_path / "transport_ai_baseline_capture.db")
    _upgrade_database_to_head(database_url)
    engine = sa.create_engine(database_url)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False), engine


def _create_admin_user(session: Session) -> AdminUser:
    timestamp = datetime(2026, 4, 30, 13, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    admin_user = AdminUser(
        chave="AI03",
        nome_completo="Transport AI Baseline Admin",
        password_hash=None,
        requires_password_reset=False,
        approved_by_admin_id=None,
        approved_at=None,
        password_reset_requested_at=None,
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(admin_user)
    session.flush()
    return admin_user


def _create_mobile_settings(session: Session) -> None:
    timestamp = datetime(2026, 4, 30, 13, 1, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    settings_row = session.get(MobileAppSettings, 1)
    if settings_row is None:
        settings_row = MobileAppSettings(
            id=1,
            created_at=timestamp,
            updated_at=timestamp,
        )
        session.add(settings_row)

    settings_row.location_update_interval_seconds = 60
    settings_row.location_accuracy_threshold_meters = 30
    settings_row.transport_work_to_home_time = "16:45"
    settings_row.transport_last_update_time = "16:00"
    settings_row.transport_default_car_seats = 3
    settings_row.transport_default_minivan_seats = 6
    settings_row.transport_default_van_seats = 10
    settings_row.transport_default_bus_seats = 40
    settings_row.transport_default_tolerance_minutes = 5
    settings_row.transport_price_currency_code = "SGD"
    settings_row.transport_price_rate_unit = "day"
    settings_row.transport_default_car_price = Decimal("15.00")
    settings_row.transport_default_minivan_price = Decimal("28.00")
    settings_row.transport_default_van_price = Decimal("40.00")
    settings_row.transport_default_bus_price = Decimal("70.00")
    settings_row.coordinate_update_frequency_json = None
    settings_row.updated_at = timestamp
    session.flush()


def _create_project(
    session: Session,
    *,
    name: str = "PBASE1",
    country_code: str = "SG",
    country_name: str = "Singapore",
    address: str = "1 Marina Boulevard",
    zip_code: str = "018989",
) -> Project:
    project = Project(
        name=name,
        country_code=country_code,
        country_name=country_name,
        timezone_name="Asia/Singapore",
        address=address,
        zip_code=zip_code,
    )
    session.add(project)
    session.flush()
    return project


def _create_user(session: Session, *, chave: str, nome: str, projeto: str, address: str, zip_code: str) -> User:
    timestamp = datetime(2026, 4, 30, 13, 2, 0, tzinfo=ZoneInfo("Asia/Singapore"))
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
        last_active_at=timestamp,
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
    requested_time: str,
    request_kind: str = "extra",
    selected_weekdays: list[int] | None = None,
) -> TransportRequest:
    timestamp = datetime(2026, 4, 30, 13, 3, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    if request_kind == "regular":
        recurrence_kind = "weekday"
        selected_weekdays_json = json.dumps(selected_weekdays or [0, 1, 2, 3, 4], ensure_ascii=True, separators=(",", ":"))
        single_date = None
    elif request_kind == "weekend":
        recurrence_kind = "weekend"
        selected_weekdays_json = (
            json.dumps(selected_weekdays, ensure_ascii=True, separators=(",", ":"))
            if selected_weekdays is not None
            else None
        )
        single_date = None
    elif request_kind == "extra":
        recurrence_kind = "single_date"
        selected_weekdays_json = None
        single_date = service_date
    else:
        raise ValueError(f"Unsupported request kind for baseline test fixture: {request_kind}")

    request = TransportRequest(
        user_id=user_id,
        request_kind=request_kind,
        recurrence_kind=recurrence_kind,
        requested_time=requested_time,
        selected_weekdays_json=selected_weekdays_json,
        single_date=single_date,
        created_via="admin",
        status="active",
        created_at=timestamp,
        updated_at=timestamp,
        cancelled_at=None,
    )
    session.add(request)
    session.flush()
    return request


def _create_vehicle(session: Session, *, placa: str, tipo: str, service_scope: str = "extra") -> Vehicle:
    vehicle = Vehicle(
        placa=placa,
        tipo=tipo,
        color="white",
        lugares=4 if tipo == "carro" else 10,
        tolerance=0,
        service_scope=service_scope,
    )
    session.add(vehicle)
    session.flush()
    return vehicle


def _create_vehicle_schedule(
    session: Session,
    *,
    vehicle_id: int,
    service_date: date | None,
    route_kind: str,
    departure_time: str | None,
    service_scope: str = "extra",
    recurrence_kind: str = "single_date",
    weekday: int | None = None,
) -> TransportVehicleSchedule:
    timestamp = datetime(2026, 4, 30, 13, 4, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    schedule = TransportVehicleSchedule(
        vehicle_id=vehicle_id,
        service_scope=service_scope,
        route_kind=route_kind,
        recurrence_kind=recurrence_kind,
        service_date=service_date,
        weekday=weekday,
        departure_time=departure_time,
        is_active=True,
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(schedule)
    session.flush()
    return schedule


def _create_assignment(
    session: Session,
    *,
    request_id: int,
    service_date: date,
    route_kind: str,
    status: str,
    assigned_by_admin_id: int,
    vehicle_id: int | None = None,
    boarding_time: str | None = None,
) -> TransportAssignment:
    timestamp = datetime(2026, 4, 30, 13, 5, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    assignment = TransportAssignment(
        request_id=request_id,
        service_date=service_date,
        route_kind=route_kind,
        vehicle_id=vehicle_id,
        status=status,
        response_message=f"status:{status}",
        boarding_time=boarding_time,
        acknowledged_by_user=False,
        acknowledged_at=None,
        assigned_by_admin_id=assigned_by_admin_id,
        created_at=timestamp,
        updated_at=timestamp,
        notified_at=None,
    )
    session.add(assignment)
    session.flush()
    return assignment


def _create_transport_ai_run(
    session: Session,
    *,
    actor_user_id: int,
    service_date: date = date(2026, 5, 6),
    route_kind: str = "home_to_work",
) -> TransportAIRun:
    timestamp = datetime(2026, 4, 30, 13, 6, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    run = TransportAIRun(
        run_key="run-baseline-001",
        service_date=service_date,
        route_kind=route_kind,
        status="requested",
        actor_user_id=actor_user_id,
        earliest_boarding_time="06:50",
        arrival_at_work_time="07:45",
        openai_model="gpt-5-2025-08-07",
        route_provider="here",
        price_currency_code="SGD",
        price_rate_unit="day",
        baseline_snapshot_json=None,
        baseline_assignments_json=None,
        baseline_vehicle_state_json=None,
        planning_input_json=json.dumps({"service_date": "2026-05-06", "route_kind": "home_to_work"}),
        planning_input_hash="c" * 64,
        preflight_issues_json=json.dumps([]),
        error_code=None,
        error_message=None,
        created_at=timestamp,
        updated_at=timestamp,
        completed_at=None,
    )
    session.add(run)
    session.flush()
    return run


def test_capture_transport_ai_baseline_includes_eligible_requests_and_both_route_assignments(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 6)
    captured_at = datetime(2026, 5, 1, 8, 30, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        project = _create_project(session)
        vehicle_home = _create_vehicle(session, placa="SBA1001A", tipo="carro")
        vehicle_return = _create_vehicle(session, placa="SBA1002B", tipo="van")
        _create_vehicle_schedule(
            session,
            vehicle_id=vehicle_home.id,
            service_date=service_date,
            route_kind="home_to_work",
            departure_time="07:00",
        )
        _create_vehicle_schedule(
            session,
            vehicle_id=vehicle_return.id,
            service_date=service_date,
            route_kind="work_to_home",
            departure_time="18:00",
        )

        user_confirmed = _create_user(
            session,
            chave="U101",
            nome="Confirmed Passenger",
            projeto=project.name,
            address="10 Bayfront Avenue",
            zip_code="018956",
        )
        user_rejected = _create_user(
            session,
            chave="U102",
            nome="Rejected Passenger",
            projeto=project.name,
            address="25 Raffles Place",
            zip_code="048621",
        )
        user_pending = _create_user(
            session,
            chave="U103",
            nome="Pending Passenger",
            projeto=project.name,
            address="80 Robinson Road",
            zip_code="068898",
        )
        request_confirmed = _create_transport_request(session, user_id=user_confirmed.id, service_date=service_date, requested_time="07:05")
        request_rejected = _create_transport_request(session, user_id=user_rejected.id, service_date=service_date, requested_time="07:10")
        request_pending = _create_transport_request(session, user_id=user_pending.id, service_date=service_date, requested_time="07:15")
        _create_assignment(
            session,
            request_id=request_confirmed.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=vehicle_home.id,
        )
        _create_assignment(
            session,
            request_id=request_confirmed.id,
            service_date=service_date,
            route_kind="work_to_home",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=vehicle_return.id,
        )
        _create_assignment(
            session,
            request_id=request_rejected.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="rejected",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=None,
        )
        _create_assignment(
            session,
            request_id=request_pending.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="pending",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=None,
        )
        session.commit()

        baseline_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            captured_at=captured_at,
        )

    engine.dispose()

    eligible_request_ids = [row["request_id"] for row in baseline_capture.assignments_payload["eligible_requests"]]
    assignment_statuses = {
        (row["request_id"], row["route_kind"]): row["status"]
        for row in baseline_capture.assignments_payload["assignments"]
    }

    assert eligible_request_ids == [request_confirmed.id, request_rejected.id, request_pending.id]
    assert assignment_statuses[(request_confirmed.id, "home_to_work")] == "confirmed"
    assert assignment_statuses[(request_confirmed.id, "work_to_home")] == "confirmed"
    assert assignment_statuses[(request_rejected.id, "home_to_work")] == "rejected"
    assert assignment_statuses[(request_pending.id, "home_to_work")] == "pending"
    assert baseline_capture.snapshot_payload["settings"]["price_currency_code"] == "SGD"
    assert baseline_capture.snapshot_payload["snapshot"]["service_date"] == service_date.isoformat()
    assert baseline_capture.baseline_hash == baseline_capture.snapshot_payload["baseline_hash"]
    assert len(baseline_capture.baseline_hash) == 64


def test_capture_transport_ai_baseline_filters_eligible_requests_by_dashboard_scope(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 6)
    captured_at = datetime(2026, 5, 1, 9, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        scoped_project = _create_project(session, name="PBASE1")
        hidden_project = _create_project(
            session,
            name="PBASE2",
            address="2 Raffles Place",
            zip_code="048620",
        )

        scoped_user = _create_user(
            session,
            chave="U111",
            nome="Scoped Passenger",
            projeto=scoped_project.name,
            address="10 Bayfront Avenue",
            zip_code="018956",
        )
        hidden_user = _create_user(
            session,
            chave="U112",
            nome="Hidden Passenger",
            projeto=hidden_project.name,
            address="25 Raffles Place",
            zip_code="048621",
        )
        scoped_request = _create_transport_request(
            session,
            user_id=scoped_user.id,
            service_date=service_date,
            requested_time="07:05",
        )
        scoped_regular_request = _create_transport_request(
            session,
            user_id=scoped_user.id,
            service_date=service_date,
            requested_time="07:07",
            request_kind="regular",
        )
        hidden_request = _create_transport_request(
            session,
            user_id=hidden_user.id,
            service_date=service_date,
            requested_time="07:10",
        )
        _create_assignment(
            session,
            request_id=scoped_request.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=None,
        )
        _create_assignment(
            session,
            request_id=hidden_request.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=None,
        )
        _create_assignment(
            session,
            request_id=scoped_regular_request.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=None,
        )
        session.commit()

        baseline_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            dashboard_scope=TransportAgentDashboardScope(
                project_ids=[scoped_project.id],
                request_kinds=["extra"],
            ),
            captured_at=captured_at,
        )

    engine.dispose()

    eligible_request_ids = [row["request_id"] for row in baseline_capture.assignments_payload["eligible_requests"]]
    assignment_request_ids = [row["request_id"] for row in baseline_capture.assignments_payload["assignments"]]

    assert baseline_capture.assignments_payload["dashboard_scope"] == {
        "project_ids": [scoped_project.id],
        "request_kinds": ["extra"],
    }
    assert baseline_capture.snapshot_payload["dashboard_scope"] == {
        "project_ids": [scoped_project.id],
        "request_kinds": ["extra"],
    }
    assert eligible_request_ids == [scoped_request.id]
    assert assignment_request_ids == [scoped_request.id]


def test_capture_transport_ai_baseline_filters_eligible_requests_by_secondary_membership_scope(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 6)
    captured_at = datetime(2026, 5, 1, 9, 15, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        primary_project = _create_project(session, name="PBASE-MEMBER-PRIMARY")
        secondary_project = _create_project(
            session,
            name="PBASE-MEMBER-SECONDARY",
            address="2 Raffles Place",
            zip_code="048620",
        )
        hidden_project = _create_project(
            session,
            name="PBASE-MEMBER-HIDDEN",
            address="3 Robinson Road",
            zip_code="068877",
        )

        scoped_user = _create_user(
            session,
            chave="U121",
            nome="Secondary Scoped Passenger",
            projeto=primary_project.name,
            address="10 Bayfront Avenue",
            zip_code="018956",
        )
        add_user_project_membership(session, scoped_user, secondary_project.name)
        hidden_user = _create_user(
            session,
            chave="U122",
            nome="Hidden Passenger",
            projeto=hidden_project.name,
            address="25 Raffles Place",
            zip_code="048621",
        )
        scoped_request = _create_transport_request(
            session,
            user_id=scoped_user.id,
            service_date=service_date,
            requested_time="07:05",
        )
        hidden_request = _create_transport_request(
            session,
            user_id=hidden_user.id,
            service_date=service_date,
            requested_time="07:10",
        )
        _create_assignment(
            session,
            request_id=scoped_request.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=None,
        )
        _create_assignment(
            session,
            request_id=hidden_request.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=None,
        )
        session.commit()

        baseline_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            dashboard_scope=TransportAgentDashboardScope(project_ids=[secondary_project.id]),
            captured_at=captured_at,
        )

    engine.dispose()

    eligible_request_ids = [row["request_id"] for row in baseline_capture.assignments_payload["eligible_requests"]]
    assignment_request_ids = [row["request_id"] for row in baseline_capture.assignments_payload["assignments"]]

    assert baseline_capture.assignments_payload["dashboard_scope"] == {
        "project_ids": [secondary_project.id],
        "request_kinds": ["regular", "weekend", "extra"],
    }
    assert eligible_request_ids == [scoped_request.id]
    assert assignment_request_ids == [scoped_request.id]


def test_capture_transport_ai_baseline_includes_relevant_vehicle_state_and_hash_changes_with_data(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 6)
    captured_at = datetime(2026, 5, 1, 8, 45, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        project = _create_project(session)
        vehicle_home = _create_vehicle(session, placa="SBA2001A", tipo="carro")
        vehicle_return = _create_vehicle(session, placa="SBA2002B", tipo="van")
        _create_vehicle_schedule(
            session,
            vehicle_id=vehicle_home.id,
            service_date=service_date,
            route_kind="home_to_work",
            departure_time="07:00",
        )
        _create_vehicle_schedule(
            session,
            vehicle_id=vehicle_return.id,
            service_date=service_date,
            route_kind="work_to_home",
            departure_time="18:00",
        )
        user_confirmed = _create_user(
            session,
            chave="U201",
            nome="Hash Passenger",
            projeto=project.name,
            address="10 Bayfront Avenue",
            zip_code="018956",
        )
        request_confirmed = _create_transport_request(session, user_id=user_confirmed.id, service_date=service_date, requested_time="07:05")
        assignment = _create_assignment(
            session,
            request_id=request_confirmed.id,
            service_date=service_date,
            route_kind="work_to_home",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=vehicle_return.id,
        )
        session.commit()

        first_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            captured_at=captured_at,
        )

        assignment.status = "rejected"
        assignment.vehicle_id = None
        assignment.updated_at = datetime(2026, 5, 1, 9, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))
        session.commit()

        second_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            captured_at=captured_at,
        )

    engine.dispose()

    first_vehicle_ids = first_capture.vehicle_state_payload["relevant_vehicle_ids"]
    second_assignment_statuses = [row["status"] for row in second_capture.assignments_payload["assignments"]]

    assert vehicle_home.id in first_vehicle_ids
    assert vehicle_return.id in first_vehicle_ids
    assert {row["route_kind"] for row in first_capture.vehicle_state_payload["schedules"]} == {"home_to_work", "work_to_home"}
    assert first_capture.vehicle_state_payload["vehicles"][0]["id"] == vehicle_home.id
    assert first_capture.baseline_hash != second_capture.baseline_hash
    assert second_assignment_statuses == ["rejected"]


def test_save_transport_ai_baseline_persists_payloads_on_run(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 6)
    captured_at = datetime(2026, 5, 1, 9, 15, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        project = _create_project(session)
        user_pending = _create_user(
            session,
            chave="U301",
            nome="Run Save Passenger",
            projeto=project.name,
            address="80 Robinson Road",
            zip_code="068898",
        )
        request_pending = _create_transport_request(session, user_id=user_pending.id, service_date=service_date, requested_time="07:15")
        _create_assignment(
            session,
            request_id=request_pending.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="pending",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=None,
        )
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id)
        session.commit()

        baseline_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            captured_at=captured_at,
        )
        save_transport_ai_baseline(
            session,
            run=run,
            baseline_capture=baseline_capture,
            saved_at=captured_at,
        )
        session.commit()

        persisted_run = session.get(TransportAIRun, run.id)

    engine.dispose()

    assert persisted_run is not None
    assert persisted_run.status == "baseline_saved"
    assert persisted_run.updated_at == captured_at
    assert persisted_run.baseline_snapshot_json is not None
    assert persisted_run.baseline_assignments_json is not None
    assert persisted_run.baseline_vehicle_state_json is not None

    snapshot_payload = json.loads(persisted_run.baseline_snapshot_json)
    assignments_payload = json.loads(persisted_run.baseline_assignments_json)
    vehicle_state_payload = json.loads(persisted_run.baseline_vehicle_state_json)

    assert snapshot_payload["baseline_hash"] == baseline_capture.baseline_hash
    assert assignments_payload["baseline_hash"] == baseline_capture.baseline_hash
    assert vehicle_state_payload["baseline_hash"] == baseline_capture.baseline_hash
    assert assignments_payload["eligible_requests"][0]["request_id"] == request_pending.id


def test_restore_transport_ai_baseline_restores_confirmed_and_rejected_assignments(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 6)
    captured_at = datetime(2026, 5, 1, 9, 30, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        project = _create_project(session)
        original_vehicle = _create_vehicle(session, placa="SBA3001A", tipo="carro")
        replacement_vehicle = _create_vehicle(session, placa="SBA3002B", tipo="van")
        _create_vehicle_schedule(
            session,
            vehicle_id=original_vehicle.id,
            service_date=service_date,
            route_kind="home_to_work",
            departure_time="07:00",
        )
        _create_vehicle_schedule(
            session,
            vehicle_id=replacement_vehicle.id,
            service_date=service_date,
            route_kind="home_to_work",
            departure_time="07:10",
        )
        user_confirmed = _create_user(
            session,
            chave="U401",
            nome="Restore Confirmed Passenger",
            projeto=project.name,
            address="10 Bayfront Avenue",
            zip_code="018956",
        )
        user_rejected = _create_user(
            session,
            chave="U402",
            nome="Restore Rejected Passenger",
            projeto=project.name,
            address="25 Raffles Place",
            zip_code="048621",
        )
        request_confirmed = _create_transport_request(session, user_id=user_confirmed.id, service_date=service_date, requested_time="07:05")
        request_rejected = _create_transport_request(session, user_id=user_rejected.id, service_date=service_date, requested_time="07:10")
        _create_assignment(
            session,
            request_id=request_confirmed.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=original_vehicle.id,
            boarding_time="07:05",
        )
        _create_assignment(
            session,
            request_id=request_rejected.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="rejected",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=None,
        )
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id)
        session.commit()

        baseline_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            captured_at=captured_at,
        )
        save_transport_ai_baseline(
            session,
            run=run,
            baseline_capture=baseline_capture,
            saved_at=captured_at,
        )
        session.commit()

        confirmed_assignment = session.execute(
            sa.select(TransportAssignment).where(
                TransportAssignment.request_id == request_confirmed.id,
                TransportAssignment.service_date == service_date,
                TransportAssignment.route_kind == "home_to_work",
            )
        ).scalar_one()
        rejected_assignment = session.execute(
            sa.select(TransportAssignment).where(
                TransportAssignment.request_id == request_rejected.id,
                TransportAssignment.service_date == service_date,
                TransportAssignment.route_kind == "home_to_work",
            )
        ).scalar_one()
        confirmed_assignment.status = "pending"
        confirmed_assignment.vehicle_id = None
        confirmed_assignment.boarding_time = None
        rejected_assignment.status = "pending"
        rejected_assignment.response_message = "reset-to-pending"
        session.commit()

        result = restore_transport_ai_baseline(
            session,
            run=run,
            actor_user_id=admin_user.id,
            restored_at=datetime(2026, 5, 1, 9, 45, 0, tzinfo=ZoneInfo("Asia/Singapore")),
        )
        session.commit()

        restored_confirmed = session.execute(
            sa.select(TransportAssignment).where(
                TransportAssignment.request_id == request_confirmed.id,
                TransportAssignment.service_date == service_date,
                TransportAssignment.route_kind == "home_to_work",
            )
        ).scalar_one()
        restored_rejected = session.execute(
            sa.select(TransportAssignment).where(
                TransportAssignment.request_id == request_rejected.id,
                TransportAssignment.service_date == service_date,
                TransportAssignment.route_kind == "home_to_work",
            )
        ).scalar_one()

    engine.dispose()

    assert result.ok
    assert result.issues == []
    assert restored_confirmed.status == "confirmed"
    assert restored_confirmed.vehicle_id == original_vehicle.id
    assert restored_confirmed.boarding_time == "07:05"
    assert restored_rejected.status == "rejected"
    assert restored_rejected.vehicle_id is None
    assert restored_rejected.boarding_time is None
    assert any(entry.action == "updated" for entry in result.audit_entries)


def test_restore_transport_ai_baseline_removes_pending_created_after_capture_and_is_idempotent(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 6)
    captured_at = datetime(2026, 5, 1, 10, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        project = _create_project(session)
        user_without_assignment = _create_user(
            session,
            chave="U501",
            nome="Restore Pending Removal Passenger",
            projeto=project.name,
            address="80 Robinson Road",
            zip_code="068898",
        )
        request_without_assignment = _create_transport_request(
            session,
            user_id=user_without_assignment.id,
            service_date=service_date,
            requested_time="07:20",
        )
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id)
        session.commit()

        baseline_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            captured_at=captured_at,
        )
        save_transport_ai_baseline(
            session,
            run=run,
            baseline_capture=baseline_capture,
            saved_at=captured_at,
        )
        session.commit()

        injected_pending = _create_assignment(
            session,
            request_id=request_without_assignment.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="pending",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=None,
        )
        session.commit()

        first_restore = restore_transport_ai_baseline(session, run=run, actor_user_id=admin_user.id)
        session.commit()
        remaining_after_first_restore = session.execute(
            sa.select(TransportAssignment).where(
                TransportAssignment.request_id == request_without_assignment.id,
                TransportAssignment.service_date == service_date,
                TransportAssignment.route_kind == "home_to_work",
            )
        ).scalars().all()

        second_restore = restore_transport_ai_baseline(session, run=run, actor_user_id=admin_user.id)
        session.commit()
        remaining_after_second_restore = session.execute(
            sa.select(TransportAssignment).where(
                TransportAssignment.request_id == request_without_assignment.id,
                TransportAssignment.service_date == service_date,
                TransportAssignment.route_kind == "home_to_work",
            )
        ).scalars().all()

    engine.dispose()

    assert first_restore.ok
    assert injected_pending.id in first_restore.deleted_assignment_ids
    assert remaining_after_first_restore == []
    assert second_restore.ok
    assert second_restore.deleted_assignment_ids == []
    assert remaining_after_second_restore == []


def test_restore_transport_ai_baseline_does_not_remove_manual_vehicle_created_after_capture(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 6)
    captured_at = datetime(2026, 5, 1, 10, 15, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        project = _create_project(session)
        user_pending = _create_user(
            session,
            chave="U601",
            nome="Restore Manual Vehicle Passenger",
            projeto=project.name,
            address="10 Bayfront Avenue",
            zip_code="018956",
        )
        _create_transport_request(session, user_id=user_pending.id, service_date=service_date, requested_time="07:25")
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id)
        session.commit()

        baseline_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            captured_at=captured_at,
        )
        save_transport_ai_baseline(
            session,
            run=run,
            baseline_capture=baseline_capture,
            saved_at=captured_at,
        )
        session.commit()

        manual_vehicle = _create_vehicle(session, placa="SBA6001A", tipo="minivan")
        _create_vehicle_schedule(
            session,
            vehicle_id=manual_vehicle.id,
            service_date=service_date,
            route_kind="home_to_work",
            departure_time="07:30",
        )
        session.commit()

        result = restore_transport_ai_baseline(session, run=run, actor_user_id=admin_user.id)
        session.commit()
        persisted_manual_vehicle = session.get(Vehicle, manual_vehicle.id)

    engine.dispose()

    assert result.ok
    assert persisted_manual_vehicle is not None
    assert persisted_manual_vehicle.placa == "SBA6001A"


def test_restore_transport_ai_baseline_returns_issue_when_confirmed_vehicle_is_missing(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 6)
    captured_at = datetime(2026, 5, 1, 10, 30, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        project = _create_project(session)
        original_vehicle = _create_vehicle(session, placa="SBA7001A", tipo="carro")
        _create_vehicle_schedule(
            session,
            vehicle_id=original_vehicle.id,
            service_date=service_date,
            route_kind="home_to_work",
            departure_time="07:00",
        )
        user_confirmed = _create_user(
            session,
            chave="U701",
            nome="Restore Missing Vehicle Passenger",
            projeto=project.name,
            address="10 Bayfront Avenue",
            zip_code="018956",
        )
        request_confirmed = _create_transport_request(session, user_id=user_confirmed.id, service_date=service_date, requested_time="07:05")
        _create_assignment(
            session,
            request_id=request_confirmed.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=original_vehicle.id,
        )
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id)
        session.commit()

        baseline_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            captured_at=captured_at,
        )
        save_transport_ai_baseline(
            session,
            run=run,
            baseline_capture=baseline_capture,
            saved_at=captured_at,
        )
        session.commit()

        corrupted_assignments_payload = json.loads(run.baseline_assignments_json)
        corrupted_assignments_payload["assignments"][0]["vehicle_id"] = 999999
        run.baseline_assignments_json = json.dumps(corrupted_assignments_payload)
        session.commit()

        result = restore_transport_ai_baseline(session, run=run, actor_user_id=admin_user.id)
        session.rollback()

    engine.dispose()

    assert not result.ok
    assert result.restored_assignment_ids == []
    assert result.deleted_assignment_ids == []
    assert any(issue.code == "baseline_vehicle_missing" for issue in result.issues)


def test_reset_transport_ai_requests_to_pending_resets_extra_request_and_keeps_vehicle_on_dashboard(tmp_path):
    clear_transport_reevaluation_events()
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 6)
    captured_at = datetime(2026, 5, 1, 11, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        project = _create_project(session)
        vehicle = _create_vehicle(session, placa="SBA8001A", tipo="carro", service_scope="extra")
        _create_vehicle_schedule(
            session,
            vehicle_id=vehicle.id,
            service_date=service_date,
            route_kind="home_to_work",
            departure_time="07:00",
            service_scope="extra",
            recurrence_kind="single_date",
        )
        user = _create_user(
            session,
            chave="U801",
            nome="Reset Extra Passenger",
            projeto=project.name,
            address="10 Bayfront Avenue",
            zip_code="018956",
        )
        request_row = _create_transport_request(
            session,
            user_id=user.id,
            service_date=service_date,
            requested_time="07:05",
            request_kind="extra",
        )
        _create_assignment(
            session,
            request_id=request_row.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=vehicle.id,
        )
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id)
        session.commit()

        baseline_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            captured_at=captured_at,
        )
        save_transport_ai_baseline(session, run=run, baseline_capture=baseline_capture, saved_at=captured_at)
        session.commit()

        result = reset_transport_ai_requests_to_pending(
            session,
            run=run,
            actor_user_id=admin_user.id,
            reset_at=datetime(2026, 5, 1, 11, 10, 0, tzinfo=ZoneInfo("Asia/Singapore")),
        )
        session.commit()

        snapshot = build_transport_operational_snapshot(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            captured_at=datetime(2026, 5, 1, 11, 11, 0, tzinfo=ZoneInfo("Asia/Singapore")),
        )
        request_snapshot = next(row for row in snapshot.extra_requests if row.id == request_row.id)
        recent_events = list_recent_transport_reevaluation_events(limit=5)

    engine.dispose()

    assert result.ok
    assert run.status == "passengers_reset"
    assert request_snapshot.assignment_status == "pending"
    assert request_snapshot.assigned_vehicle is None
    assert any(row.id == vehicle.id for row in snapshot.extra_vehicles)
    assert result.event_emitted is True
    assert recent_events[0].event_type == "transport_assignment_changed"
    assert recent_events[0].source == "transport_admin"

def test_reset_transport_ai_requests_to_pending_respects_dashboard_scope_inherited_from_baseline(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 6)
    captured_at = datetime(2026, 5, 1, 11, 15, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        scoped_project = _create_project(session, name="PBASE1")
        hidden_project = _create_project(
            session,
            name="PBASE2",
            address="2 Raffles Place",
            zip_code="048620",
        )
        scoped_vehicle = _create_vehicle(session, placa="SBA8051A", tipo="carro")
        hidden_vehicle = _create_vehicle(session, placa="SBA8052B", tipo="carro")
        _create_vehicle_schedule(
            session,
            vehicle_id=scoped_vehicle.id,
            service_date=service_date,
            route_kind="home_to_work",
            departure_time="07:00",
        )
        _create_vehicle_schedule(
            session,
            vehicle_id=hidden_vehicle.id,
            service_date=service_date,
            route_kind="home_to_work",
            departure_time="07:00",
        )
        scoped_user = _create_user(
            session,
            chave="U805",
            nome="Scoped Reset Passenger",
            projeto=scoped_project.name,
            address="10 Bayfront Avenue",
            zip_code="018956",
        )
        hidden_user = _create_user(
            session,
            chave="U806",
            nome="Hidden Reset Passenger",
            projeto=hidden_project.name,
            address="25 Raffles Place",
            zip_code="048621",
        )
        scoped_request = _create_transport_request(
            session,
            user_id=scoped_user.id,
            service_date=service_date,
            requested_time="07:05",
            request_kind="extra",
        )
        hidden_request = _create_transport_request(
            session,
            user_id=hidden_user.id,
            service_date=service_date,
            requested_time="07:10",
            request_kind="extra",
        )
        scoped_assignment = _create_assignment(
            session,
            request_id=scoped_request.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=scoped_vehicle.id,
        )
        hidden_assignment = _create_assignment(
            session,
            request_id=hidden_request.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=hidden_vehicle.id,
        )
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id)
        session.commit()

        baseline_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            dashboard_scope=TransportAgentDashboardScope(project_ids=[scoped_project.id]),
            captured_at=captured_at,
        )
        save_transport_ai_baseline(session, run=run, baseline_capture=baseline_capture, saved_at=captured_at)
        session.commit()

        result = reset_transport_ai_requests_to_pending(
            session,
            run=run,
            actor_user_id=admin_user.id,
            reset_at=datetime(2026, 5, 1, 11, 16, 0, tzinfo=ZoneInfo("Asia/Singapore")),
        )
        session.commit()

        persisted_scoped_assignment = session.get(TransportAssignment, scoped_assignment.id)
        persisted_hidden_assignment = session.get(TransportAssignment, hidden_assignment.id)

    engine.dispose()

    assert result.ok
    assert result.reset_request_ids == [scoped_request.id]
    assert result.reset_assignment_ids == [scoped_assignment.id]
    assert persisted_scoped_assignment is not None
    assert persisted_scoped_assignment.status == "pending"
    assert persisted_scoped_assignment.vehicle_id is None
    assert persisted_hidden_assignment is not None
    assert persisted_hidden_assignment.status == "confirmed"
    assert persisted_hidden_assignment.vehicle_id == hidden_vehicle.id


def test_reset_transport_ai_requests_to_pending_respects_request_kind_scope_inherited_from_baseline(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 6)
    captured_at = datetime(2026, 5, 1, 11, 25, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        project = _create_project(session, name="PBASE-REQUEST-KIND")
        extra_user = _create_user(
            session,
            chave="U807",
            nome="Scoped Extra Passenger",
            projeto=project.name,
            address="10 Bayfront Avenue",
            zip_code="018956",
        )
        regular_user = _create_user(
            session,
            chave="U808",
            nome="Scoped Regular Passenger",
            projeto=project.name,
            address="25 Raffles Place",
            zip_code="048621",
        )
        extra_request = _create_transport_request(
            session,
            user_id=extra_user.id,
            service_date=service_date,
            requested_time="07:05",
            request_kind="extra",
        )
        regular_request = _create_transport_request(
            session,
            user_id=regular_user.id,
            service_date=service_date,
            requested_time="07:10",
            request_kind="regular",
        )
        extra_assignment = _create_assignment(
            session,
            request_id=extra_request.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=None,
        )
        regular_assignment = _create_assignment(
            session,
            request_id=regular_request.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=None,
        )
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id)
        session.commit()

        baseline_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            dashboard_scope=TransportAgentDashboardScope(request_kinds=["extra"]),
            captured_at=captured_at,
        )
        save_transport_ai_baseline(session, run=run, baseline_capture=baseline_capture, saved_at=captured_at)
        session.commit()

        result = reset_transport_ai_requests_to_pending(
            session,
            run=run,
            actor_user_id=admin_user.id,
            reset_at=datetime(2026, 5, 1, 11, 26, 0, tzinfo=ZoneInfo("Asia/Singapore")),
        )
        session.commit()

        persisted_extra_assignment = session.get(TransportAssignment, extra_assignment.id)
        persisted_regular_assignment = session.get(TransportAssignment, regular_assignment.id)

    engine.dispose()

    assert result.ok
    assert result.reset_request_ids == [extra_request.id]
    assert result.reset_assignment_ids == [extra_assignment.id]
    assert persisted_extra_assignment is not None
    assert persisted_extra_assignment.status == "pending"
    assert persisted_regular_assignment is not None
    assert persisted_regular_assignment.status == "confirmed"


def test_reset_transport_ai_requests_to_pending_keeps_future_regular_materialization_intact(tmp_path):
    clear_transport_reevaluation_events()
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 6)
    template_date = date(2026, 5, 4)
    future_date = date(2026, 5, 7)
    captured_at = datetime(2026, 5, 1, 11, 20, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        project = _create_project(session)
        vehicle = _create_vehicle(session, placa="SBA8101A", tipo="van", service_scope="regular")
        _create_vehicle_schedule(
            session,
            vehicle_id=vehicle.id,
            service_date=None,
            route_kind="home_to_work",
            departure_time=None,
            service_scope="regular",
            recurrence_kind="weekday",
        )
        user = _create_user(
            session,
            chave="U811",
            nome="Reset Regular Passenger",
            projeto=project.name,
            address="25 Raffles Place",
            zip_code="048621",
        )
        request_row = _create_transport_request(
            session,
            user_id=user.id,
            service_date=service_date,
            requested_time="07:10",
            request_kind="regular",
            selected_weekdays=[0, 1, 2, 3, 4],
        )
        _create_assignment(
            session,
            request_id=request_row.id,
            service_date=template_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=vehicle.id,
        )
        target_assignment = _create_assignment(
            session,
            request_id=request_row.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=vehicle.id,
        )
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id)
        session.commit()

        baseline_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            captured_at=captured_at,
        )
        save_transport_ai_baseline(session, run=run, baseline_capture=baseline_capture, saved_at=captured_at)
        session.commit()

        result = reset_transport_ai_requests_to_pending(
            session,
            run=run,
            actor_user_id=admin_user.id,
            reset_at=datetime(2026, 5, 1, 11, 30, 0, tzinfo=ZoneInfo("Asia/Singapore")),
        )
        session.commit()

        persisted_target_assignment = session.get(TransportAssignment, target_assignment.id)
        future_snapshot = build_transport_operational_snapshot(
            session,
            service_date=future_date,
            route_kind="home_to_work",
            captured_at=datetime(2026, 5, 1, 11, 31, 0, tzinfo=ZoneInfo("Asia/Singapore")),
        )
        future_request_snapshot = next(row for row in future_snapshot.regular_requests if row.id == request_row.id)

    engine.dispose()

    assert result.ok
    assert persisted_target_assignment is not None
    assert persisted_target_assignment.status == "pending"
    assert persisted_target_assignment.vehicle_id is None
    assert future_request_snapshot.assignment_status == "confirmed"
    assert future_request_snapshot.assigned_vehicle is not None
    assert future_request_snapshot.assigned_vehicle.placa == vehicle.placa


def test_reset_transport_ai_requests_to_pending_resets_weekend_request_to_pending(tmp_path):
    clear_transport_reevaluation_events()
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 9)
    captured_at = datetime(2026, 5, 1, 11, 40, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        project = _create_project(session)
        vehicle = _create_vehicle(session, placa="SBA8201A", tipo="van", service_scope="weekend")
        _create_vehicle_schedule(
            session,
            vehicle_id=vehicle.id,
            service_date=None,
            route_kind="home_to_work",
            departure_time=None,
            service_scope="weekend",
            recurrence_kind="matching_weekday",
            weekday=service_date.weekday(),
        )
        user = _create_user(
            session,
            chave="U821",
            nome="Reset Weekend Passenger",
            projeto=project.name,
            address="80 Robinson Road",
            zip_code="068898",
        )
        request_row = _create_transport_request(
            session,
            user_id=user.id,
            service_date=service_date,
            requested_time="07:15",
            request_kind="weekend",
            selected_weekdays=[service_date.weekday()],
        )
        target_assignment = _create_assignment(
            session,
            request_id=request_row.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=vehicle.id,
        )
        run = _create_transport_ai_run(
            session,
            actor_user_id=admin_user.id,
            service_date=service_date,
            route_kind="home_to_work",
        )
        session.commit()

        baseline_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            captured_at=captured_at,
        )
        save_transport_ai_baseline(session, run=run, baseline_capture=baseline_capture, saved_at=captured_at)
        session.commit()

        result = reset_transport_ai_requests_to_pending(
            session,
            run=run,
            actor_user_id=admin_user.id,
            reset_at=datetime(2026, 5, 1, 11, 50, 0, tzinfo=ZoneInfo("Asia/Singapore")),
        )
        session.commit()

        persisted_target_assignment = session.get(TransportAssignment, target_assignment.id)
        snapshot = build_transport_operational_snapshot(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            captured_at=datetime(2026, 5, 1, 11, 51, 0, tzinfo=ZoneInfo("Asia/Singapore")),
        )
        request_snapshot = next(row for row in snapshot.weekend_requests if row.id == request_row.id)

    engine.dispose()

    assert result.ok
    assert persisted_target_assignment is not None
    assert persisted_target_assignment.status == "pending"
    assert persisted_target_assignment.vehicle_id is None
    assert request_snapshot.assignment_status == "pending"


def test_reset_transport_ai_requests_to_pending_restores_baseline_when_reset_fails(tmp_path, monkeypatch: pytest.MonkeyPatch):
    clear_transport_reevaluation_events()
    session_factory, engine = _build_session_factory(tmp_path)
    service_date = date(2026, 5, 6)
    captured_at = datetime(2026, 5, 1, 12, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        _create_mobile_settings(session)
        project = _create_project(session)
        vehicle = _create_vehicle(session, placa="SBA8301A", tipo="carro", service_scope="extra")
        _create_vehicle_schedule(
            session,
            vehicle_id=vehicle.id,
            service_date=service_date,
            route_kind="home_to_work",
            departure_time="07:00",
            service_scope="extra",
            recurrence_kind="single_date",
        )
        first_user = _create_user(
            session,
            chave="U831",
            nome="Reset Failure Passenger 1",
            projeto=project.name,
            address="10 Bayfront Avenue",
            zip_code="018956",
        )
        second_user = _create_user(
            session,
            chave="U832",
            nome="Reset Failure Passenger 2",
            projeto=project.name,
            address="25 Raffles Place",
            zip_code="048621",
        )
        first_request = _create_transport_request(
            session,
            user_id=first_user.id,
            service_date=service_date,
            requested_time="07:05",
            request_kind="extra",
        )
        second_request = _create_transport_request(
            session,
            user_id=second_user.id,
            service_date=service_date,
            requested_time="07:10",
            request_kind="extra",
        )
        first_assignment = _create_assignment(
            session,
            request_id=first_request.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=vehicle.id,
        )
        second_assignment = _create_assignment(
            session,
            request_id=second_request.id,
            service_date=service_date,
            route_kind="home_to_work",
            status="confirmed",
            assigned_by_admin_id=admin_user.id,
            vehicle_id=vehicle.id,
        )
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id)
        session.commit()

        baseline_capture = capture_transport_ai_baseline(
            session,
            service_date=service_date,
            route_kind="home_to_work",
            actor_user_id=admin_user.id,
            captured_at=captured_at,
        )
        save_transport_ai_baseline(session, run=run, baseline_capture=baseline_capture, saved_at=captured_at)
        session.commit()

        original_upsert = transport_ai_runs_module.upsert_transport_assignment_with_persistence
        upsert_calls = {"count": 0}

        def flaky_upsert(*args, **kwargs):
            upsert_calls["count"] += 1
            if upsert_calls["count"] == 2:
                raise RuntimeError("forced reset failure")
            return original_upsert(*args, **kwargs)

        original_restore = transport_ai_runs_module.restore_transport_ai_baseline
        restore_calls = {"count": 0}

        def tracking_restore(*args, **kwargs):
            restore_calls["count"] += 1
            return original_restore(*args, **kwargs)

        monkeypatch.setattr(transport_ai_runs_module, "upsert_transport_assignment_with_persistence", flaky_upsert)
        monkeypatch.setattr(transport_ai_runs_module, "restore_transport_ai_baseline", tracking_restore)

        result = reset_transport_ai_requests_to_pending(
            session,
            run=run,
            actor_user_id=admin_user.id,
            reset_at=datetime(2026, 5, 1, 12, 10, 0, tzinfo=ZoneInfo("Asia/Singapore")),
        )
        session.commit()

        persisted_first_assignment = session.get(TransportAssignment, first_assignment.id)
        persisted_second_assignment = session.get(TransportAssignment, second_assignment.id)
        recent_events = list_recent_transport_reevaluation_events(limit=5)

    engine.dispose()

    assert not result.ok
    assert "forced reset failure" in str(result.error_message)
    assert result.restore_result is not None
    assert result.restore_result.ok
    assert restore_calls["count"] == 1
    assert run.status == "baseline_saved"
    assert persisted_first_assignment is not None
    assert persisted_first_assignment.status == "confirmed"
    assert persisted_first_assignment.vehicle_id == vehicle.id
    assert persisted_second_assignment is not None
    assert persisted_second_assignment.status == "confirmed"
    assert persisted_second_assignment.vehicle_id == vehicle.id
    assert recent_events == []