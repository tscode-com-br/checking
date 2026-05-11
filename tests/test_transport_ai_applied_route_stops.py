import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.core.config import settings
from sistema.app.routers.transport_ai import _build_transport_ai_applied_route_stop_inputs
from sistema.app.models import AdminUser, TransportAISuggestion, TransportAIAppliedRouteStop, TransportAIRun
from sistema.app.schemas import (
    TransportAgentChangeSummary,
    TransportAgentCostSummary,
    TransportAgentPlan,
    TransportAgentRouteStop,
    TransportAgentVehicleItinerary,
)
from sistema.app.services.transport_ai_agent import TRANSPORT_AI_PROMPT_VERSION
from sistema.app.services.transport_ai_applied_route_stops import (
    TransportAIAppliedRouteStopInput,
    list_transport_ai_applied_route_stops,
    persist_transport_ai_applied_route_stops,
)
from sistema.app.services.transport_ai_runs import create_transport_ai_suggestion


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
    database_url = _build_database_url(tmp_path / "transport_ai_applied_route_stops.db")
    _upgrade_database_to_head(database_url)
    engine = sa.create_engine(database_url)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False), engine


def _create_admin_user(session: Session, *, suffix: str) -> AdminUser:
    timestamp = datetime(2026, 4, 30, 12, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    admin_user = AdminUser(
        chave=f"A{suffix}",
        nome_completo=f"Transport AI Applied Stops Admin {suffix}",
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


def _create_transport_ai_run(session: Session, *, actor_user_id: int, run_key: str) -> TransportAIRun:
    timestamp = datetime(2026, 4, 30, 12, 5, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    transport_ai_run = TransportAIRun(
        run_key=run_key,
        service_date=date(2026, 5, 3),
        route_kind="home_to_work",
        status="applied",
        actor_user_id=actor_user_id,
        earliest_boarding_time="06:50",
        arrival_at_work_time="07:45",
        openai_model="gpt-5-2025-08-07",
        route_provider="here",
        price_currency_code="SGD",
        price_rate_unit="day",
        baseline_snapshot_json=json.dumps({"snapshot_key": run_key}),
        baseline_assignments_json=json.dumps([]),
        baseline_vehicle_state_json=json.dumps([]),
        planning_input_json=json.dumps({"service_date": "2026-05-03", "route_kind": "home_to_work"}),
        planning_input_hash="b" * 64,
        preflight_issues_json=json.dumps([]),
        error_code=None,
        error_message=None,
        created_at=timestamp,
        updated_at=timestamp,
        completed_at=timestamp,
    )
    session.add(transport_ai_run)
    session.flush()
    return transport_ai_run


def _build_suggestion_payload(suggestion_key: str) -> dict[str, str | None]:
    return {
        "suggestion_key": suggestion_key,
        "proposal_key": f"proposal:{suggestion_key}",
        "agent_plan_json": json.dumps({"plan_key": suggestion_key, "status": "applied"}),
        "transport_proposal_json": json.dumps({"proposal_key": f"proposal:{suggestion_key}"}),
        "vehicle_actions_json": json.dumps([{"action_key": f"vehicle:{suggestion_key}"}]),
        "assignment_actions_json": json.dumps([{"request_id": 1, "vehicle_ref": "existing:12"}]),
        "route_itineraries_json": json.dumps([{"vehicle_ref": "existing:12", "stops": []}]),
        "change_summary_json": json.dumps({"vehicle_changes": 1}),
        "cost_summary_json": json.dumps({"currency": "SGD", "total_cost": 140.0}),
        "validation_issues_json": json.dumps([]),
        "raw_model_response_json": json.dumps({"raw": suggestion_key}),
        "prompt_version": TRANSPORT_AI_PROMPT_VERSION,
    }


def _create_transport_ai_suggestion(
    session: Session,
    *,
    run: TransportAIRun,
    suggestion_key: str,
) -> TransportAISuggestion:
    return create_transport_ai_suggestion(
        session,
        run=run,
        status="applied",
        created_at=datetime(2026, 4, 30, 12, 10, 0, tzinfo=ZoneInfo("Asia/Singapore")),
        **_build_suggestion_payload(suggestion_key),
    )


def _build_stop(
    *,
    vehicle_id: int,
    stop_order: int,
    stop_type: str,
    route_kind: str = "home_to_work",
    request_id: int | None,
    user_id: int | None,
    passenger_name: str | None,
    project_name: str = "Marina Bay Project",
    address: str = "10 Bayfront Avenue",
    zip_code: str = "018956",
    country_code: str = "SG",
    longitude: float = 103.8607,
    latitude: float = 1.2834,
    scheduled_time: str = "07:30",
    duration_from_previous_seconds: int | None = None,
    distance_from_previous_meters: int | None = None,
) -> TransportAIAppliedRouteStopInput:
    return TransportAIAppliedRouteStopInput(
        vehicle_id=vehicle_id,
        route_kind=route_kind,
        stop_order=stop_order,
        stop_type=stop_type,
        request_id=request_id,
        user_id=user_id,
        passenger_name=passenger_name,
        project_name=project_name,
        address=address,
        zip_code=zip_code,
        country_code=country_code,
        longitude=longitude,
        latitude=latitude,
        scheduled_time=scheduled_time,
        duration_from_previous_seconds=duration_from_previous_seconds,
        distance_from_previous_meters=distance_from_previous_meters,
    )


def test_transport_ai_applied_route_stops_migration_upgrades_head_on_sqlite(tmp_path):
    database_url = _build_database_url(tmp_path / "transport_ai_applied_route_stops_head.db")

    _upgrade_database_to_head(database_url)

    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)
    column_names = {column["name"] for column in inspector.get_columns("transport_ai_applied_route_stops")}
    unique_constraint_names = {
        constraint["name"] for constraint in inspector.get_unique_constraints("transport_ai_applied_route_stops")
    }
    engine.dispose()

    assert inspector.has_table("transport_ai_applied_route_stops")
    assert {
        "suggestion_id",
        "vehicle_id",
        "route_kind",
        "stop_order",
        "stop_type",
        "request_id",
        "user_id",
        "passenger_name",
        "project_name",
        "address",
        "zip_code",
        "country_code",
        "longitude",
        "latitude",
        "scheduled_time",
        "duration_from_previous_seconds",
        "distance_from_previous_meters",
        "created_at",
    }.issubset(column_names)
    assert "uq_transport_ai_applied_route_stops_vehicle_order" in unique_constraint_names


def test_transport_ai_applied_route_stops_persists_two_pickups_and_destination(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)
    created_at = datetime(2026, 4, 30, 12, 20, 0, tzinfo=ZoneInfo("Asia/Singapore"))

    with session_factory() as session:
        admin_user = _create_admin_user(session, suffix="10")
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id, run_key="run-applied-stops-001")
        suggestion = _create_transport_ai_suggestion(
            session,
            run=run,
            suggestion_key="suggestion-applied-stops-001",
        )
        session.commit()

        persist_transport_ai_applied_route_stops(
            session,
            suggestion=suggestion,
            stops=[
                _build_stop(
                    vehicle_id=12,
                    stop_order=2,
                    stop_type="pickup",
                    request_id=202,
                    user_id=302,
                    passenger_name="Passenger Two",
                    address="25 Raffles Place",
                    zip_code="048621",
                    scheduled_time="07:18",
                    duration_from_previous_seconds=480,
                    distance_from_previous_meters=2600,
                ),
                _build_stop(
                    vehicle_id=12,
                    stop_order=1,
                    stop_type="pickup",
                    request_id=201,
                    user_id=301,
                    passenger_name="Passenger One",
                    address="10 Bayfront Avenue",
                    zip_code="018956",
                    scheduled_time="07:08",
                ),
                _build_stop(
                    vehicle_id=12,
                    stop_order=3,
                    stop_type="destination",
                    request_id=None,
                    user_id=None,
                    passenger_name=None,
                    address="1 Marina Boulevard",
                    zip_code="018989",
                    scheduled_time="07:45",
                    duration_from_previous_seconds=720,
                    distance_from_previous_meters=3900,
                ),
            ],
            created_at=created_at,
        )
        session.commit()

        persisted_stops = list_transport_ai_applied_route_stops(session, suggestion_id=suggestion.id)

    engine.dispose()

    assert [stop.stop_type for stop in persisted_stops] == ["pickup", "pickup", "destination"]
    assert [stop.route_kind for stop in persisted_stops] == ["home_to_work", "home_to_work", "home_to_work"]
    assert [stop.stop_order for stop in persisted_stops] == [1, 2, 3]
    assert persisted_stops[-1].scheduled_time == "07:45"
    assert persisted_stops[-1].distance_from_previous_meters == 3900
    assert all(isinstance(stop, TransportAIAppliedRouteStop) for stop in persisted_stops)


def test_transport_ai_applied_route_stops_persist_bidirectional_legs_for_same_vehicle(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)

    with session_factory() as session:
        admin_user = _create_admin_user(session, suffix="10B")
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id, run_key="run-applied-stops-001b")
        suggestion = _create_transport_ai_suggestion(
            session,
            run=run,
            suggestion_key="suggestion-applied-stops-001b",
        )
        session.commit()

        persist_transport_ai_applied_route_stops(
            session,
            suggestion=suggestion,
            stops=[
                _build_stop(
                    vehicle_id=12,
                    route_kind="home_to_work",
                    stop_order=1,
                    stop_type="pickup",
                    request_id=201,
                    user_id=301,
                    passenger_name="Passenger One",
                    scheduled_time="07:08",
                ),
                _build_stop(
                    vehicle_id=12,
                    route_kind="home_to_work",
                    stop_order=2,
                    stop_type="destination",
                    request_id=None,
                    user_id=None,
                    passenger_name=None,
                    address="1 Marina Boulevard",
                    zip_code="018989",
                    scheduled_time="07:45",
                ),
                _build_stop(
                    vehicle_id=12,
                    route_kind="work_to_home",
                    stop_order=1,
                    stop_type="origin",
                    request_id=None,
                    user_id=None,
                    passenger_name=None,
                    address="1 Marina Boulevard",
                    zip_code="018989",
                    scheduled_time="16:45",
                ),
                _build_stop(
                    vehicle_id=12,
                    route_kind="work_to_home",
                    stop_order=2,
                    stop_type="dropoff",
                    request_id=201,
                    user_id=301,
                    passenger_name="Passenger One",
                    scheduled_time="17:09",
                ),
            ],
        )
        session.commit()

        persisted_stops = list_transport_ai_applied_route_stops(session, suggestion_id=suggestion.id)

    engine.dispose()

    assert [(stop.route_kind, stop.stop_order, stop.stop_type) for stop in persisted_stops] == [
        ("home_to_work", 1, "pickup"),
        ("home_to_work", 2, "destination"),
        ("work_to_home", 1, "origin"),
        ("work_to_home", 2, "dropoff"),
    ]


def test_transport_ai_applied_route_stops_are_listed_by_vehicle_id_and_stop_order(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)

    with session_factory() as session:
        admin_user = _create_admin_user(session, suffix="11")
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id, run_key="run-applied-stops-002")
        suggestion = _create_transport_ai_suggestion(
            session,
            run=run,
            suggestion_key="suggestion-applied-stops-002",
        )
        session.commit()

        persist_transport_ai_applied_route_stops(
            session,
            suggestion=suggestion,
            stops=[
                _build_stop(vehicle_id=30, stop_order=2, stop_type="destination", request_id=None, user_id=None, passenger_name=None),
                _build_stop(vehicle_id=18, stop_order=2, stop_type="destination", request_id=None, user_id=None, passenger_name=None),
                _build_stop(vehicle_id=18, stop_order=1, stop_type="pickup", request_id=401, user_id=501, passenger_name="Passenger A"),
                _build_stop(vehicle_id=30, stop_order=1, stop_type="pickup", request_id=402, user_id=502, passenger_name="Passenger B"),
            ],
        )
        session.commit()

        persisted_stops = list_transport_ai_applied_route_stops(session, suggestion_id=suggestion.id)

    engine.dispose()

    assert [(stop.vehicle_id, stop.route_kind, stop.stop_order) for stop in persisted_stops] == [
        (18, "home_to_work", 1),
        (18, "home_to_work", 2),
        (30, "home_to_work", 1),
        (30, "home_to_work", 2),
    ]


def test_transport_ai_applied_route_stops_keep_suggestion_id_integrity(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)

    with session_factory() as session:
        admin_user = _create_admin_user(session, suffix="12")
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id, run_key="run-applied-stops-003")
        primary_suggestion = _create_transport_ai_suggestion(
            session,
            run=run,
            suggestion_key="suggestion-applied-stops-003-primary",
        )
        secondary_suggestion = _create_transport_ai_suggestion(
            session,
            run=run,
            suggestion_key="suggestion-applied-stops-003-secondary",
        )
        session.commit()

        persist_transport_ai_applied_route_stops(
            session,
            suggestion=primary_suggestion,
            stops=[
                _build_stop(vehicle_id=44, stop_order=1, stop_type="pickup", request_id=501, user_id=601, passenger_name="Primary Passenger"),
            ],
        )
        persist_transport_ai_applied_route_stops(
            session,
            suggestion=secondary_suggestion,
            stops=[
                _build_stop(vehicle_id=55, stop_order=1, stop_type="pickup", request_id=502, user_id=602, passenger_name="Secondary Passenger"),
            ],
        )
        session.commit()

        primary_rows = list_transport_ai_applied_route_stops(session, suggestion_id=primary_suggestion.id)
        secondary_rows = list_transport_ai_applied_route_stops(session, suggestion_id=secondary_suggestion.id)

    engine.dispose()

    assert len(primary_rows) == 1
    assert len(secondary_rows) == 1
    assert primary_rows[0].suggestion_id == primary_suggestion.id
    assert secondary_rows[0].suggestion_id == secondary_suggestion.id
    assert primary_rows[0].passenger_name == "Primary Passenger"
    assert secondary_rows[0].passenger_name == "Secondary Passenger"


def test_transport_ai_applied_route_stops_roll_back_without_orphans(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)

    with session_factory() as session:
        admin_user = _create_admin_user(session, suffix="13")
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id, run_key="run-applied-stops-004")
        suggestion = _create_transport_ai_suggestion(
            session,
            run=run,
            suggestion_key="suggestion-applied-stops-004",
        )
        session.commit()

        try:
            with session.begin():
                persist_transport_ai_applied_route_stops(
                    session,
                    suggestion=suggestion,
                    stops=[
                        _build_stop(vehicle_id=66, stop_order=1, stop_type="pickup", request_id=701, user_id=801, passenger_name="Rollback Passenger"),
                        _build_stop(vehicle_id=66, stop_order=2, stop_type="destination", request_id=None, user_id=None, passenger_name=None),
                    ],
                )
                raise RuntimeError("force rollback after stop persistence")
        except RuntimeError:
            session.rollback()

        persisted_stops = list_transport_ai_applied_route_stops(session, suggestion_id=suggestion.id)

    engine.dispose()

    assert persisted_stops == []


def test_build_transport_ai_applied_route_stop_inputs_normalizes_legacy_work_to_home_stop_types():
    plan = TransportAgentPlan(
        plan_key="plan-applied-stops-normalization",
        service_date=date(2026, 5, 3),
        route_kind="home_to_work",
        earliest_boarding_time="06:50",
        arrival_at_work_time="07:45",
        objective_summary="Normalize applied stop types for bidirectional legs.",
        vehicle_actions=[],
        passenger_allocations=[],
        route_itineraries=[
            TransportAgentVehicleItinerary(
                route_key="route-outbound-001",
                partition_key="regular:PBAY:SG",
                vehicle_ref="existing:12",
                service_scope="regular",
                route_kind="home_to_work",
                vehicle_type="carro",
                vehicle_id=12,
                schedule_id=21,
                client_vehicle_key="existing:12",
                plate="SBA1200A",
                project_name="Marina Bay Project",
                country_code="SG",
                country_name="Singapore",
                estimated_cost=120.0,
                total_duration_seconds=1500,
                total_distance_meters=6000,
                projected_arrival_time="07:45",
                stops=[
                    TransportAgentRouteStop(
                        stop_order=0,
                        stop_type="pickup",
                        request_id=201,
                        user_id=301,
                        passenger_name="Passenger One",
                        project_name="Marina Bay Project",
                        address="10 Bayfront Avenue",
                        zip_code="018956",
                        country_code="SG",
                        longitude=103.8607,
                        latitude=1.2834,
                        scheduled_time="07:08",
                        duration_from_previous_seconds=None,
                        distance_from_previous_meters=None,
                    ),
                    TransportAgentRouteStop(
                        stop_order=1,
                        stop_type="destination",
                        request_id=None,
                        user_id=None,
                        passenger_name=None,
                        project_name="Marina Bay Project",
                        address="1 Marina Boulevard",
                        zip_code="018989",
                        country_code="SG",
                        longitude=103.8519,
                        latitude=1.2801,
                        scheduled_time="07:45",
                        duration_from_previous_seconds=720,
                        distance_from_previous_meters=3900,
                    ),
                ],
            ),
            TransportAgentVehicleItinerary(
                route_key="route-return-001",
                partition_key="regular:PBAY:SG",
                vehicle_ref="existing:12",
                service_scope="regular",
                route_kind="work_to_home",
                vehicle_type="carro",
                vehicle_id=12,
                schedule_id=21,
                client_vehicle_key="existing:12",
                plate="SBA1200A",
                project_name="Marina Bay Project",
                country_code="SG",
                country_name="Singapore",
                estimated_cost=0.0,
                total_duration_seconds=1440,
                total_distance_meters=5800,
                projected_arrival_time="17:09",
                stops=[
                    TransportAgentRouteStop(
                        stop_order=0,
                        stop_type="pickup",
                        request_id=None,
                        user_id=None,
                        passenger_name=None,
                        project_name="Marina Bay Project",
                        address="1 Marina Boulevard",
                        zip_code="018989",
                        country_code="SG",
                        longitude=103.8519,
                        latitude=1.2801,
                        scheduled_time="16:45",
                        duration_from_previous_seconds=None,
                        distance_from_previous_meters=None,
                    ),
                    TransportAgentRouteStop(
                        stop_order=1,
                        stop_type="destination",
                        request_id=201,
                        user_id=301,
                        passenger_name="Passenger One",
                        project_name="Marina Bay Project",
                        address="10 Bayfront Avenue",
                        zip_code="018956",
                        country_code="SG",
                        longitude=103.8607,
                        latitude=1.2834,
                        scheduled_time="17:09",
                        duration_from_previous_seconds=1440,
                        distance_from_previous_meters=5800,
                    ),
                ],
            ),
        ],
        vehicle_review_tables=[],
        cost_summary=TransportAgentCostSummary(
            price_currency_code="SGD",
            price_rate_unit="day",
            current_total_estimated_cost=120.0,
            suggested_total_estimated_cost=120.0,
            estimated_cost_delta=0.0,
            current_vehicle_count=1,
            suggested_vehicle_count=1,
        ),
        change_summary=TransportAgentChangeSummary(
            total_vehicle_actions=0,
            keep_count=0,
            create_count=0,
            update_count=0,
            remove_from_day_count=0,
            by_vehicle_type=[],
        ),
        validation_issues=[],
    )

    stop_inputs, issues = _build_transport_ai_applied_route_stop_inputs(
        plan=plan,
        suggestion=None,
        vehicle_id_by_ref={"existing:12": 12},
    )

    assert issues == []
    assert [(stop_input.route_kind, stop_input.stop_order, stop_input.stop_type) for stop_input in stop_inputs] == [
        ("home_to_work", 1, "pickup"),
        ("home_to_work", 2, "destination"),
        ("work_to_home", 1, "origin"),
        ("work_to_home", 2, "dropoff"),
    ]
