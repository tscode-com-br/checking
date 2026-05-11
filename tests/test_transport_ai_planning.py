import json
import sys
import types
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.core.config import Settings
from sistema.app.database import Base
from sistema.app.models import AdminUser, MobileAppSettings, Project, TransportAIRoutePoint, TransportAIRun, TransportRequest, TransportVehicleSchedule, User, Vehicle
from sistema.app.schemas import (
    TRANSPORT_AI_BIDIRECTIONAL_CONTRACT,
    TransportAgentDashboardScope,
    TransportAgentPlan,
    TransportAgentPassengerAllocation,
    TransportAgentPlanningInput,
    TransportAgentRequestRouteKinds,
    TransportAgentResolvedRoutePoint,
    TransportAgentResolvedRoutePointsPartition,
    TransportAgentResolvedRoutePointsResult,
    TransportAgentRouteStop,
    TransportAgentRouteMatricesResult,
    TransportAgentRouteMatrixPartition,
    TransportAgentVehicleItinerary,
)
from sistema.app.services import location_settings as location_settings_module
from sistema.app.services import transport_ai_planning as transport_ai_planning_module
from sistema.app.services.transport_ai_planning import (
    _build_transport_ai_vehicle_review_tables,
    build_transport_agent_plan_from_solver_result,
    build_transport_agent_planning_input,
    build_transport_ai_route_matrices,
    build_transport_ai_vehicle_candidates,
    build_transport_ai_preflight_issues,
    build_transport_proposal_from_agent_plan,
    resolve_transport_ai_route_points,
    schedule_transport_ai_route_times,
    solve_transport_ai_partition,
)
from sistema.app.services.transport_ai_runs import save_transport_ai_planning_input
from sistema.app.services.transport_proposals import (
    build_transport_operational_proposal,
    build_transport_operational_snapshot,
)
from sistema.app.services.user_projects import add_user_project_membership
from sistema.app.services.transport_route_provider import (
    DirectionsRequest,
    DirectionsResult,
    GeocodeRequest,
    GeocodeResult,
    MatrixRequest,
    MatrixResult,
    TransportRouteCoordinate,
    TransportRouteProvider,
    TransportRouteProviderNoResultError,
)


def _build_planning_settings(**overrides) -> Settings:
    values = {
        "transport_ai_max_passengers_per_run": 80,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _build_session_factory(db_path: Path):
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def _configure_transport_settings(
    session: Session,
    *,
    default_car_price: float | None = 120,
    default_minivan_price: float | None = 180,
    default_van_price: float | None = 240,
    default_bus_price: float | None = 400,
    extra_car_tolerance_minutes: int = 30,
) -> None:
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
        default_car_price=default_car_price,
        default_minivan_price=default_minivan_price,
        default_van_price=default_van_price,
        default_bus_price=default_bus_price,
    )
    settings_row = session.get(MobileAppSettings, 1)
    if settings_row is not None:
        settings_row.transport_work_to_home_time = "16:45"
        settings_row.transport_last_update_time = "16:00"
        settings_row.transport_extra_car_tolerance_minutes = extra_car_tolerance_minutes
    session.flush()


def _fixture_timestamp() -> datetime:
    return datetime(2026, 5, 1, 8, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))


def _create_admin_user(session: Session, *, chave: str = "AI05") -> AdminUser:
    timestamp = _fixture_timestamp()
    admin_user = AdminUser(
        chave=chave,
        nome_completo="Transport AI Planning Admin",
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


def _create_project(
    session: Session,
    *,
    name: str = "PPLAN1",
    address: str = "1 Marina Boulevard",
    zip_code: str = "018989",
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
    address: str = "12 Worker Street",
    zip_code: str = "540123",
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
    requested_time: str = "08:00",
) -> TransportRequest:
    if request_kind == "extra":
        recurrence_kind = "single_date"
        selected_weekdays_json = None
        single_date = service_date
    elif request_kind == "regular":
        recurrence_kind = "weekday"
        selected_weekdays_json = json.dumps([0, 1, 2, 3, 4], ensure_ascii=True, separators=(",", ":"))
        single_date = None
    elif request_kind == "weekend":
        recurrence_kind = "weekend"
        selected_weekdays_json = None
        single_date = None
    else:
        raise ValueError(f"Unsupported request kind: {request_kind}")

    timestamp = _fixture_timestamp()
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


def _create_extra_vehicle_candidate(
    session: Session,
    *,
    placa: str = "SBA5001A",
    tipo: str = "carro",
    lugares: int = 4,
    service_date: date,
    route_kind: str = "home_to_work",
) -> Vehicle:
    timestamp = _fixture_timestamp()
    vehicle = Vehicle(
        placa=placa,
        tipo=tipo,
        color="white",
        lugares=lugares,
        tolerance=0,
        service_scope="extra",
    )
    session.add(vehicle)
    session.flush()

    schedule = TransportVehicleSchedule(
        vehicle_id=vehicle.id,
        service_scope="extra",
        route_kind=route_kind,
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


def _build_transport_agent_passenger_allocation(
    *,
    request: TransportRequest,
    user: User,
    service_date: date,
    vehicle_ref: str,
    project_name: str,
    pickup_order: int = 0,
    route_kind: str = "home_to_work",
    rationale: str = "Assigned by transport AI.",
) -> dict[str, object]:
    return {
        "request_id": request.id,
        "request_kind": request.request_kind,
        "service_date": service_date,
        "route_kind": route_kind,
        "vehicle_ref": vehicle_ref,
        "user_id": user.id,
        "chave": user.chave,
        "nome": user.nome,
        "project_name": project_name,
        "pickup_order": pickup_order,
        "scheduled_pickup_time": "07:20",
        "projected_arrival_time": "07:45",
        "rationale": rationale,
    }


def _build_transport_agent_plan_for_proposal(
    *,
    service_date: date,
    passenger_allocations: list[dict[str, object]] | None = None,
    validation_issues: list[dict[str, object]] | None = None,
    route_kind: str = "home_to_work",
) -> TransportAgentPlan:
    return TransportAgentPlan.model_validate(
        {
            "plan_key": "proposal-conversion-test-plan",
            "service_date": service_date,
            "route_kind": route_kind,
            "earliest_boarding_time": "07:00",
            "arrival_at_work_time": "07:45",
            "objective_summary": "Proposal conversion validation plan.",
            "vehicle_actions": [],
            "passenger_allocations": passenger_allocations or [],
            "route_itineraries": [],
            "cost_summary": {
                "price_currency_code": "SGD",
                "price_rate_unit": "day",
                "current_total_estimated_cost": 0,
                "suggested_total_estimated_cost": 0,
                "estimated_cost_delta": 0,
                "current_vehicle_count": 0,
                "suggested_vehicle_count": 0,
            },
            "change_summary": {
                "total_vehicle_actions": 0,
                "keep_count": 0,
                "create_count": 0,
                "update_count": 0,
                "remove_from_day_count": 0,
                "by_vehicle_type": [],
            },
            "validation_issues": validation_issues or [],
        }
    )


def test_transport_agent_plan_defaults_vehicle_review_tables_for_legacy_payload():
    plan = _build_transport_agent_plan_for_proposal(service_date=date(2026, 6, 1))

    assert plan.vehicle_review_tables == []


def test_transport_ai_bidirectional_contract_freezes_prompt_11_directional_semantics():
    contract = TRANSPORT_AI_BIDIRECTIONAL_CONTRACT

    assert contract["regular_weekend"]["outbound_source_of_truth"] == "home_to_work"
    assert contract["regular_weekend"]["return_leg_mode"] == "derived_from_outbound"
    assert contract["regular_weekend"]["same_vehicle_required"] is True
    assert contract["regular_weekend"]["same_passengers_required"] is True
    assert contract["regular_weekend"]["return_stop_order"] == "reverse_outbound_stops"
    assert contract["regular_weekend"]["return_duration_strategy"] == "recalculate_work_to_home"
    assert contract["extra"]["direction_mode"] == "actual_request_direction"
    assert contract["extra"]["forbid_project_destination_on_work_to_home"] is True
    assert contract["fields"]["canonical_return_time"] == "scheduled_dropoff_time"
    assert contract["fields"]["outbound_boarding_time"] == "boarding_time"
    assert contract["review"]["work_to_home_source"] == "backend_plan"
    assert contract["review"]["forbid_local_return_reconstruction"] is True
    assert contract["vehicle_ref"]["allows_multiple_real_legs"] is True
    assert contract["vehicle_ref"]["grouping_key"] == "vehicle_ref"


def test_transport_agent_passenger_allocation_supports_canonical_scheduled_dropoff_time():
    legacy_allocation = TransportAgentPassengerAllocation.model_validate({
        "request_id": 301,
        "request_kind": "extra",
        "service_date": "2026-06-09",
        "route_kind": "home_to_work",
        "vehicle_ref": "new:solver-1",
        "user_id": 501,
        "chave": "A301",
        "nome": "Alice Tan",
        "project_name": "P80",
        "pickup_order": 0,
        "scheduled_pickup_time": "07:05",
        "projected_arrival_time": "07:45",
        "rationale": "Outbound leg.",
    })

    assert legacy_allocation.scheduled_dropoff_time is None
    assert legacy_allocation.scheduled_pickup_time == "07:05"

    return_allocation = TransportAgentPassengerAllocation.model_validate({
        "request_id": 301,
        "request_kind": "extra",
        "service_date": "2026-06-09",
        "route_kind": "work_to_home",
        "vehicle_ref": "new:solver-1",
        "user_id": 501,
        "chave": "A301",
        "nome": "Alice Tan",
        "project_name": "P80",
        "pickup_order": 0,
        "scheduled_pickup_time": "18:10",
        "scheduled_dropoff_time": "18:40",
        "projected_arrival_time": "18:40",
        "rationale": "Return leg.",
    })

    assert return_allocation.scheduled_dropoff_time == "18:40"
    assert return_allocation.projected_arrival_time == "18:40"
    assert "boarding_time" in (
        TransportAgentPassengerAllocation.model_fields["scheduled_dropoff_time"].description or ""
    )
    assert TransportAgentPassengerAllocation.model_validate_json(return_allocation.model_dump_json()) == return_allocation


def _create_transport_ai_run(session: Session, *, actor_user_id: int) -> TransportAIRun:
    timestamp = _fixture_timestamp()
    transport_ai_run = TransportAIRun(
        run_key="planning-run-001",
        service_date=date(2026, 5, 1),
        route_kind="home_to_work",
        status="requested",
        actor_user_id=actor_user_id,
        earliest_boarding_time="06:50",
        arrival_at_work_time="07:45",
        openai_model="gpt-5-2025-08-07",
        route_provider="fake",
        price_currency_code="SGD",
        price_rate_unit="day",
        baseline_snapshot_json=None,
        baseline_assignments_json=None,
        baseline_vehicle_state_json=None,
        planning_input_json=json.dumps({"placeholder": True}, ensure_ascii=True, separators=(",", ":")),
        planning_input_hash="f" * 64,
        preflight_issues_json=None,
        error_code=None,
        error_message=None,
        created_at=timestamp,
        updated_at=timestamp,
        completed_at=None,
    )
    session.add(transport_ai_run)
    session.flush()
    return transport_ai_run


class _CountingPlanningRouteProvider(TransportRouteProvider):
    provider_name = "counting"

    def __init__(
        self,
        *,
        geocode_results: dict[str, GeocodeResult] | None = None,
        missing_queries: set[str] | None = None,
    ) -> None:
        self._geocode_results = dict(geocode_results or {})
        self._missing_queries = set(missing_queries or set())
        self.geocode_calls: list[str] = []

    def geocode(self, request: GeocodeRequest) -> GeocodeResult:
        self.geocode_calls.append(request.normalized_query)
        if request.normalized_query in self._missing_queries:
            raise TransportRouteProviderNoResultError(
                f"No geocode result for {request.normalized_query}",
                provider=self.provider,
                operation="geocode",
            )
        return self._geocode_results[request.normalized_query]

    def get_matrix(self, request: MatrixRequest) -> MatrixResult:
        raise AssertionError(f"Matrix should not be called during route point resolution tests: {request}")

    def get_directions(self, request: DirectionsRequest) -> DirectionsResult:
        raise AssertionError(f"Directions should not be called during route point resolution tests: {request}")


def _build_geocode_result(
    *,
    provider: str,
    request: GeocodeRequest,
    longitude: float,
    latitude: float,
    formatted_address: str,
    confidence: float,
    country_code: str,
    country_name: str,
) -> GeocodeResult:
    return GeocodeResult(
        provider=provider,
        query=request.normalized_query,
        formatted_address=formatted_address,
        coordinate=TransportRouteCoordinate(
            longitude=longitude,
            latitude=latitude,
            label=formatted_address,
        ),
        confidence=confidence,
        provider_place_id=f"{provider}-{request.normalized_query.replace(', ', '-')}",
        country_code=country_code,
        country_name=country_name,
        raw_response_json={"query": request.normalized_query},
    )


def _build_resolved_route_point(
    *,
    point_type: str = "passenger_origin",
    partition_key: str = "extra:PPLAN1:SG",
    source_id: int,
    request_id: int | None = None,
    project_name: str = "PPLAN1",
    country_code: str = "SG",
    country_name: str = "Singapore",
    label: str,
    address: str,
    zip_code: str,
    longitude: float,
    latitude: float,
    provider: str = "counting",
) -> TransportAgentResolvedRoutePoint:
    return TransportAgentResolvedRoutePoint(
        point_type=point_type,
        partition_key=partition_key,
        source_id=source_id,
        request_id=request_id,
        project_name=project_name,
        country_code=country_code,
        country_name=country_name,
        label=label,
        address=address,
        zip_code=zip_code,
        normalized_query=f"{address.lower()}, {zip_code.lower()}, {country_name.lower()}",
        formatted_address=f"{address}, {country_name} {zip_code}",
        longitude=longitude,
        latitude=latitude,
        provider=provider,
        provider_place_id=f"{provider}-{source_id}",
        confidence=0.99,
        cached=False,
    )


def _build_resolved_route_points_result(
    *,
    passenger_points: list[TransportAgentResolvedRoutePoint],
    destination_point: TransportAgentResolvedRoutePoint | None,
    partition_key: str = "extra:PPLAN1:SG",
    request_kind: str = "extra",
    project_name: str = "PPLAN1",
    country_code: str = "SG",
    country_name: str = "Singapore",
    provider: str = "counting",
) -> TransportAgentResolvedRoutePointsResult:
    return TransportAgentResolvedRoutePointsResult(
        planning_input_hash="a" * 64,
        provider=provider,
        partitions=[
            TransportAgentResolvedRoutePointsPartition(
                partition_key=partition_key,
                request_kind=request_kind,
                project_name=project_name,
                country_code=country_code,
                country_name=country_name,
                destination_point=destination_point,
                passenger_points=passenger_points,
            )
        ],
        issues=[],
        total_resolved_points=len(passenger_points) + (1 if destination_point is not None else 0),
    )


def _build_solver_route_matrix_partition(
    *,
    partition,
    durations_seconds: list[list[int | None]],
    distances_meters: list[list[int | None]] | None = None,
) -> TransportAgentRouteMatrixPartition:
    passenger_points = [
        _build_resolved_route_point(
            point_type="passenger_origin",
            partition_key=partition.partition_key,
            source_id=request.user_id,
            request_id=request.request_id,
            project_name=partition.project_name,
            country_code=partition.country_code,
            country_name=partition.country_name,
            label=request.nome,
            address=request.origin_address,
            zip_code=request.origin_zip_code,
            longitude=103.85 + (index * 0.001),
            latitude=1.28 + (index * 0.001),
            provider="solver-test",
        )
        for index, request in enumerate(partition.requests, start=1)
    ]
    destination_point = _build_resolved_route_point(
        point_type="project_destination",
        partition_key=partition.partition_key,
        source_id=partition.destination_project.id,
        request_id=None,
        project_name=partition.project_name,
        country_code=partition.country_code,
        country_name=partition.country_name,
        label=partition.project_name,
        address=partition.destination_project.address,
        zip_code=partition.destination_project.zip_code,
        longitude=103.90,
        latitude=1.31,
        provider="solver-test",
    )
    if distances_meters is None:
        distances_meters = [
            [None if value is None else value * 10 for value in row]
            for row in durations_seconds
        ]
    return TransportAgentRouteMatrixPartition(
        partition_key=partition.partition_key,
        request_kind=partition.request_kind,
        project_name=partition.project_name,
        country_code=partition.country_code,
        country_name=partition.country_name,
        points=[*passenger_points, destination_point],
        destination_index=len(passenger_points),
        cached=False,
        durations_seconds=durations_seconds,
        distances_meters=distances_meters,
    )


def _build_dense_solver_matrix(
    *,
    passenger_count: int,
    between_passenger_seconds: int,
    passenger_to_destination_seconds: int,
) -> list[list[int]]:
    point_count = passenger_count + 1
    destination_index = point_count - 1
    matrix = [[0 for _ in range(point_count)] for _ in range(point_count)]
    for row_index in range(point_count):
        for column_index in range(point_count):
            if row_index == column_index:
                continue
            if column_index == destination_index:
                matrix[row_index][column_index] = passenger_to_destination_seconds
            elif row_index == destination_index:
                matrix[row_index][column_index] = passenger_to_destination_seconds
            else:
                matrix[row_index][column_index] = between_passenger_seconds
    return matrix


def _expected_partition_solver_algorithm() -> str:
    try:
        import ortools  # noqa: F401
    except Exception:
        return "heuristic"
    return "ortools"


def test_solve_transport_ai_partition_with_ortools_respects_runtime_above_three_seconds(monkeypatch):
    fake_cp_model = types.ModuleType("ortools.sat.python.cp_model")
    created_solvers: list[object] = []

    class _FakeBoolVar:
        def __radd__(self, other):
            return other

        def __mul__(self, other):
            return 0

        __rmul__ = __mul__

    class _FakeCpModel:
        def NewBoolVar(self, _name):
            return _FakeBoolVar()

        def Add(self, _constraint):
            return None

        def Minimize(self, _expression):
            return None

    class _FakeCpSolver:
        def __init__(self):
            self.parameters = types.SimpleNamespace(
                max_time_in_seconds=None,
                num_search_workers=None,
                random_seed=None,
            )
            created_solvers.append(self)

        def Solve(self, _model):
            return fake_cp_model.OPTIMAL

        def Value(self, _variable):
            return 1

    fake_cp_model.CpModel = _FakeCpModel
    fake_cp_model.CpSolver = _FakeCpSolver
    fake_cp_model.OPTIMAL = 4
    fake_cp_model.FEASIBLE = 2

    ortools_module = types.ModuleType("ortools")
    sat_module = types.ModuleType("ortools.sat")
    python_module = types.ModuleType("ortools.sat.python")
    ortools_module.sat = sat_module
    sat_module.python = python_module
    python_module.cp_model = fake_cp_model

    monkeypatch.setitem(sys.modules, "ortools", ortools_module)
    monkeypatch.setitem(sys.modules, "ortools.sat", sat_module)
    monkeypatch.setitem(sys.modules, "ortools.sat.python", python_module)
    monkeypatch.setitem(sys.modules, "ortools.sat.python.cp_model", fake_cp_model)

    algorithm_used, selected_options = transport_ai_planning_module._solve_transport_ai_partition_with_ortools(
        request_ids=(1,),
        route_options=[
            transport_ai_planning_module._TransportAISolverRouteOption(
                option_key="option-1",
                vehicle_unit_key="unit-1",
                vehicle_candidate_key="candidate-1",
                candidate_type="virtual",
                recommended_action_type="create",
                client_vehicle_key="client-1",
                vehicle_id=None,
                schedule_id=None,
                service_scope="regular",
                route_kind="home_to_work",
                vehicle_type="carro",
                plate=None,
                capacity=3,
                request_ids=(1,),
                pickup_order_request_ids=(1,),
                estimated_cost=100.0,
                cost_cents=10000,
                change_penalty=0,
                total_duration_seconds=600,
                total_distance_meters=1200,
            )
        ],
        max_runtime_seconds=11,
    )

    assert algorithm_used == "ortools"
    assert selected_options is not None
    assert len(selected_options) == 1
    assert len(created_solvers) == 1
    assert created_solvers[0].parameters.max_time_in_seconds == pytest.approx(11.0)


def _build_matrix_lookup_key(
    *,
    points: list[TransportAgentResolvedRoutePoint],
    profile: str = "here/car-fast",
) -> tuple[str, tuple[tuple[float, float], ...], tuple[tuple[float, float], ...]]:
    coordinate_pairs = tuple((point.longitude, point.latitude) for point in points)
    return (profile, coordinate_pairs, coordinate_pairs)


def _build_matrix_result(
    *,
    provider: str,
    profile: str,
    points: list[TransportAgentResolvedRoutePoint],
    durations_seconds: list[list[float | None]],
    distances_meters: list[list[float | None]],
) -> MatrixResult:
    coordinates = [
        TransportRouteCoordinate(
            longitude=point.longitude,
            latitude=point.latitude,
            label=point.label,
        )
        for point in points
    ]
    return MatrixResult(
        provider=provider,
        profile=profile,
        sources=coordinates,
        destinations=coordinates,
        durations_seconds=durations_seconds,
        distances_meters=distances_meters,
        matrix_request_count=1,
        matrix_chunk_count=1,
        source_chunk_size=len(coordinates),
        destination_chunk_size=len(coordinates),
    )


class _CountingPlanningMatrixProvider(TransportRouteProvider):
    provider_name = "counting"

    def __init__(
        self,
        *,
        matrix_results: dict[
            tuple[str, tuple[tuple[float, float], ...], tuple[tuple[float, float], ...]],
            MatrixResult,
        ] | None = None,
    ) -> None:
        self._matrix_results = dict(matrix_results or {})
        self.matrix_calls: list[
            tuple[str, tuple[tuple[float, float], ...], tuple[tuple[float, float], ...]]
        ] = []

    def geocode(self, request: GeocodeRequest) -> GeocodeResult:
        raise AssertionError(f"Geocode should not be called during route matrix tests: {request}")

    def get_matrix(self, request: MatrixRequest) -> MatrixResult:
        matrix_key = (
            request.profile,
            tuple(coordinate.as_pair() for coordinate in request.sources),
            tuple(coordinate.as_pair() for coordinate in request.destinations),
        )
        self.matrix_calls.append(matrix_key)
        return self._matrix_results[matrix_key]

    def get_directions(self, request: DirectionsRequest) -> DirectionsResult:
        raise AssertionError(f"Directions should not be called during route matrix tests: {request}")


def test_build_transport_ai_preflight_issues_blocks_missing_car_price_for_candidate_vehicle(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_car_price.db")
    try:
        service_date = date(2026, 5, 2)
        with session_factory() as session:
            _configure_transport_settings(
                session,
                default_car_price=None,
                default_minivan_price=180,
                default_van_price=240,
                default_bus_price=400,
            )
            project = _create_project(session)
            user = _create_user(session, chave="TP01", nome="Worker One", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, service_date=service_date, tipo="carro")
            session.commit()

            issues = build_transport_ai_preflight_issues(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                settings_obj=_build_planning_settings(),
            )

        assert [issue.code for issue in issues] == ["default_car_price_missing"]
        assert issues[0].blocking is True
        assert issues[0].setting_name == "default_car_price"
    finally:
        engine.dispose()


def test_build_transport_ai_preflight_issues_blocks_project_without_destination_address(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_project_address.db")
    try:
        service_date = date(2026, 5, 3)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, address="")
            user = _create_user(session, chave="TP02", nome="Worker Two", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, service_date=service_date, tipo="carro")
            session.commit()

            issues = build_transport_ai_preflight_issues(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                settings_obj=_build_planning_settings(),
            )

        assert [issue.code for issue in issues] == ["project_destination_address_missing"]
        assert "PPLAN1" in issues[0].message
        assert issues[0].blocking is True
    finally:
        engine.dispose()


def test_build_transport_ai_preflight_issues_blocks_passenger_without_origin_address(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_request_address.db")
    try:
        service_date = date(2026, 5, 4)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            user = _create_user(
                session,
                chave="TP03",
                nome="Worker Three",
                projeto=project.name,
                address="",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, service_date=service_date, tipo="carro")
            session.commit()

            issues = build_transport_ai_preflight_issues(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                settings_obj=_build_planning_settings(),
            )

        assert [issue.code for issue in issues] == ["request_origin_address_missing"]
        assert "Worker Three" in issues[0].message
        assert issues[0].setting_name == "end_rua"
    finally:
        engine.dispose()


def test_build_transport_ai_preflight_issues_blocks_passenger_without_origin_zip(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_request_zip.db")
    try:
        service_date = date(2026, 5, 5)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            user = _create_user(
                session,
                chave="TP04",
                nome="Worker Four",
                projeto=project.name,
                zip_code="",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, service_date=service_date, tipo="carro")
            session.commit()

            issues = build_transport_ai_preflight_issues(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                settings_obj=_build_planning_settings(),
            )

        assert [issue.code for issue in issues] == ["request_origin_zip_missing"]
        assert "Worker Four" in issues[0].message
        assert issues[0].setting_name == "zip"
    finally:
        engine.dispose()


def test_build_transport_ai_preflight_issues_returns_informative_issue_when_no_requests_are_eligible(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_no_requests.db")
    try:
        service_date = date(2026, 5, 6)
        with session_factory() as session:
            _configure_transport_settings(session)
            session.commit()

            issues = build_transport_ai_preflight_issues(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                settings_obj=_build_planning_settings(),
            )

        assert [issue.code for issue in issues] == ["no_eligible_requests"]
        assert issues[0].blocking is False
        assert service_date.isoformat() in issues[0].message
    finally:
        engine.dispose()


def test_build_transport_ai_preflight_issues_mentions_selected_projects_when_scope_filters_everything(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_no_requests_scope_message.db")
    try:
        service_date = date(2026, 5, 6)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name="PPLAN-SCOPE")
            session.commit()

            issues = build_transport_ai_preflight_issues(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                dashboard_scope=TransportAgentDashboardScope(project_ids=[project.id]),
                settings_obj=_build_planning_settings(),
            )

        assert [issue.code for issue in issues] == ["no_eligible_requests"]
        assert "selected projects" in issues[0].message
        assert project.name in issues[0].message
    finally:
        engine.dispose()


def test_build_transport_ai_preflight_issues_mentions_selected_request_kind_when_scope_filters_everything(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_request_kind_scope_message.db")
    try:
        service_date = date(2026, 5, 6)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name="PPLAN-REQUEST-KIND")
            user = _create_user(session, chave="TP18", nome="Regular Only Worker", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="regular")
            session.commit()

            issues = build_transport_ai_preflight_issues(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                dashboard_scope=TransportAgentDashboardScope(request_kinds=["extra"]),
                settings_obj=_build_planning_settings(),
            )

        assert [issue.code for issue in issues] == ["no_eligible_requests"]
        assert "selected request kind (EXTRA)" in issues[0].message
        assert "selected projects" not in issues[0].message
    finally:
        engine.dispose()


def test_build_transport_ai_preflight_issues_respects_dashboard_scope_before_project_validation(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_scope_preflight.db")
    try:
        service_date = date(2026, 5, 6)
        with session_factory() as session:
            _configure_transport_settings(session)
            visible_project = _create_project(session, name="PPLAN1", address="1 Marina Boulevard", zip_code="018989")
            hidden_project = _create_project(session, name="PPLAN2", address=None, zip_code="50000")
            visible_user = _create_user(session, chave="TP09", nome="Visible Worker", projeto=visible_project.name)
            hidden_user = _create_user(session, chave="TP19", nome="Hidden Worker", projeto=hidden_project.name)
            _create_transport_request(session, user_id=visible_user.id, service_date=service_date, request_kind="extra")
            _create_transport_request(session, user_id=hidden_user.id, service_date=service_date, request_kind="extra")
            session.commit()

            unscoped_issues = build_transport_ai_preflight_issues(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                settings_obj=_build_planning_settings(),
            )
            scoped_issues = build_transport_ai_preflight_issues(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                dashboard_scope=TransportAgentDashboardScope(project_ids=[visible_project.id]),
                settings_obj=_build_planning_settings(),
            )

        assert "project_destination_address_missing" in [issue.code for issue in unscoped_issues]
        assert "project_destination_address_missing" not in [issue.code for issue in scoped_issues]
    finally:
        engine.dispose()


def test_build_transport_agent_planning_input_batches_high_volume_regular_requests_instead_of_blocking(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_high_volume_regular.db")
    try:
        service_date = date(2026, 5, 4)
        assert service_date.weekday() < 5

        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            for index in range(1, 101):
                user = _create_user(
                    session,
                    chave=f"H{index:03d}",
                    nome=f"High Volume Regular {index}",
                    projeto=project.name,
                )
                _create_transport_request(
                    session,
                    user_id=user.id,
                    service_date=service_date,
                    request_kind="regular",
                )
            session.commit()

            issues = build_transport_ai_preflight_issues(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                settings_obj=_build_planning_settings(),
            )
            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )

        assert [issue.code for issue in issues] == []
        regular_partitions = [partition for partition in planning_input.partitions if partition.request_kind == "regular"]
        assert [partition.partition_key for partition in regular_partitions] == [
            "regular:PPLAN1:SG:batch:1",
            "regular:PPLAN1:SG:batch:2",
        ]
        assert [len(partition.requests) for partition in regular_partitions] == [80, 20]
        assert all(partition.temporal_request_clusters == [] for partition in regular_partitions)
        assert planning_input.total_requests == 100
    finally:
        engine.dispose()


def test_build_transport_agent_planning_input_includes_only_requests_applicable_to_date_and_separates_scopes(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_scopes.db")
    try:
        service_date = date(2026, 5, 4)
        assert service_date.weekday() < 5

        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            regular_user = _create_user(session, chave="TP10", nome="Regular Worker", projeto=project.name)
            weekend_user = _create_user(session, chave="TP11", nome="Weekend Worker", projeto=project.name)
            extra_user = _create_user(session, chave="TP12", nome="Extra Worker", projeto=project.name)

            regular_request = _create_transport_request(
                session,
                user_id=regular_user.id,
                service_date=service_date,
                request_kind="regular",
            )
            _create_transport_request(
                session,
                user_id=weekend_user.id,
                service_date=service_date,
                request_kind="weekend",
            )
            extra_request = _create_transport_request(
                session,
                user_id=extra_user.id,
                service_date=service_date,
                request_kind="extra",
            )
            _create_transport_request(
                session,
                user_id=extra_user.id,
                service_date=date(2026, 5, 5),
                request_kind="extra",
            )
            _create_extra_vehicle_candidate(session, service_date=service_date)
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )

        assert [request.request_id for request in planning_input.requests_by_scope["regular"]] == [regular_request.id]
        assert planning_input.requests_by_scope["weekend"] == []
        assert [request.request_id for request in planning_input.requests_by_scope["extra"]] == [extra_request.id]
        assert planning_input.total_requests == 2
    finally:
        engine.dispose()


def test_build_transport_agent_planning_input_tracks_real_route_kind_per_request_scope_when_run_context_is_work_to_home(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_request_route_kinds.db")
    try:
        service_date = date(2026, 5, 4)
        assert service_date.weekday() < 5

        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            regular_user = _create_user(session, chave="TP17", nome="Regular Return Context", projeto=project.name)
            extra_user = _create_user(session, chave="TP18", nome="Extra Return Context", projeto=project.name)

            regular_request = _create_transport_request(
                session,
                user_id=regular_user.id,
                service_date=service_date,
                request_kind="regular",
                requested_time="07:10",
            )
            extra_request = _create_transport_request(
                session,
                user_id=extra_user.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="18:10",
            )
            _create_extra_vehicle_candidate(
                session,
                service_date=service_date,
                route_kind="work_to_home",
            )
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="work_to_home",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                request_route_kinds=TransportAgentRequestRouteKinds(
                    regular="home_to_work",
                    weekend="home_to_work",
                    extra="work_to_home",
                ),
                settings_obj=_build_planning_settings(),
            )

        assert planning_input.route_kind == "work_to_home"
        assert [request.request_id for request in planning_input.requests_by_scope["regular"]] == [regular_request.id]
        assert [request.request_id for request in planning_input.requests_by_scope["extra"]] == [extra_request.id]
        assert planning_input.requests_by_scope["regular"][0].route_kind == "home_to_work"
        assert planning_input.requests_by_scope["extra"][0].route_kind == "work_to_home"

        regular_partition = next(
            partition for partition in planning_input.partitions if partition.request_kind == "regular"
        )
        extra_partition = next(
            partition for partition in planning_input.partitions if partition.request_kind == "extra"
        )
        assert [request.route_kind for request in regular_partition.requests] == ["home_to_work"]
        assert [request.route_kind for request in extra_partition.requests] == ["work_to_home"]

        roundtrip = TransportAgentPlanningInput.model_validate(planning_input.model_dump(mode="json"))
        assert roundtrip.requests_by_scope["regular"][0].route_kind == "home_to_work"
        assert roundtrip.requests_by_scope["extra"][0].route_kind == "work_to_home"
    finally:
        engine.dispose()


def test_build_transport_agent_planning_input_separates_projects_into_distinct_partitions(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_partitions.db")
    try:
        service_date = date(2026, 5, 7)
        with session_factory() as session:
            _configure_transport_settings(session)
            project_sg = _create_project(session, name="PPLAN1", address="1 Marina Boulevard", zip_code="018989", country_code="SG")
            project_my = _create_project(session, name="PPLAN2", address="1 Jalan Sultan", zip_code="50000", country_code="MY")
            user_sg = _create_user(session, chave="TP13", nome="Worker SG", projeto=project_sg.name)
            user_my = _create_user(session, chave="TP14", nome="Worker MY", projeto=project_my.name)
            _create_transport_request(session, user_id=user_sg.id, service_date=service_date, request_kind="extra")
            _create_transport_request(session, user_id=user_my.id, service_date=service_date, request_kind="extra")
            _create_extra_vehicle_candidate(session, service_date=service_date, tipo="carro")
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )

        assert [partition.partition_key for partition in planning_input.partitions] == [
            "extra:PPLAN1:SG",
            "extra:PPLAN2:MY",
        ]
        assert [partition.project_name for partition in planning_input.partitions] == ["PPLAN1", "PPLAN2"]
    finally:
        engine.dispose()


def test_build_transport_agent_planning_input_filters_requests_by_dashboard_scope_and_persists_scope(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_scope_filter.db")
    try:
        service_date = date(2026, 5, 7)
        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project_sg = _create_project(session, name="PPLAN1", address="1 Marina Boulevard", zip_code="018989", country_code="SG")
            project_my = _create_project(session, name="PPLAN2", address="1 Jalan Sultan", zip_code="50000", country_code="MY")
            user_sg = _create_user(session, chave="TP13", nome="Worker SG", projeto=project_sg.name)
            user_my = _create_user(session, chave="TP14", nome="Worker MY", projeto=project_my.name)
            scoped_request = _create_transport_request(session, user_id=user_sg.id, service_date=service_date, request_kind="extra")
            _create_transport_request(session, user_id=user_sg.id, service_date=service_date, request_kind="regular")
            _create_transport_request(session, user_id=user_my.id, service_date=service_date, request_kind="extra")
            _create_extra_vehicle_candidate(session, service_date=service_date, tipo="carro")
            transport_ai_run = _create_transport_ai_run(session, actor_user_id=admin_user.id)
            transport_ai_run.service_date = service_date
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                dashboard_scope=TransportAgentDashboardScope(
                    project_ids=[project_sg.id],
                    request_kinds=["extra"],
                ),
                settings_obj=_build_planning_settings(),
            )
            save_transport_ai_planning_input(transport_ai_run, planning_input=planning_input)
            session.commit()
            session.refresh(transport_ai_run)

        persisted_payload = json.loads(transport_ai_run.planning_input_json)

        assert planning_input.dashboard_scope == TransportAgentDashboardScope(
            project_ids=[project_sg.id],
            request_kinds=["extra"],
        )
        assert [request.request_id for request in planning_input.requests_by_scope["extra"]] == [scoped_request.id]
        assert planning_input.requests_by_scope["regular"] == []
        assert [partition.partition_key for partition in planning_input.partitions] == ["extra:PPLAN1:SG"]
        assert planning_input.total_requests == 1
        assert persisted_payload["dashboard_scope"] == {
            "project_ids": [project_sg.id],
            "request_kinds": ["extra"],
        }
    finally:
        engine.dispose()


def test_build_transport_agent_planning_input_includes_request_visible_via_secondary_membership_scope(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_secondary_membership_scope.db")
    try:
        service_date = date(2026, 5, 7)
        with session_factory() as session:
            _configure_transport_settings(session)
            primary_project = _create_project(
                session,
                name="PPLAN-MEMBER-PRIMARY",
                address="1 Marina Boulevard",
                zip_code="018989",
                country_code="SG",
            )
            secondary_project = _create_project(
                session,
                name="PPLAN-MEMBER-SECONDARY",
                address="2 Raffles Place",
                zip_code="048620",
                country_code="SG",
            )
            user = _create_user(
                session,
                chave="TPM4",
                nome="Membership Scoped Worker",
                projeto=primary_project.name,
            )
            add_user_project_membership(session, user, secondary_project.name)
            scoped_request = _create_transport_request(
                session,
                user_id=user.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="08:10",
            )
            _create_extra_vehicle_candidate(session, service_date=service_date, tipo="carro")
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                dashboard_scope=TransportAgentDashboardScope(project_ids=[secondary_project.id]),
                settings_obj=_build_planning_settings(),
            )

        assert [request.request_id for request in planning_input.requests_by_scope["extra"]] == [scoped_request.id]
        assert planning_input.total_requests == 1
        assert [partition.project_name for partition in planning_input.partitions] == [primary_project.name]
        assert planning_input.dashboard_scope is not None
        assert planning_input.dashboard_scope.project_ids == [secondary_project.id]
    finally:
        engine.dispose()


def test_build_transport_agent_planning_input_keeps_request_kind_scope_without_project_filter(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_request_kind_without_project_filter.db")
    try:
        service_date = date(2026, 5, 7)
        with session_factory() as session:
            _configure_transport_settings(session)
            project_sg = _create_project(session, name="PPLAN1", address="1 Marina Boulevard", zip_code="018989", country_code="SG")
            project_my = _create_project(session, name="PPLAN2", address="1 Jalan Sultan", zip_code="50000", country_code="MY")
            user_sg = _create_user(session, chave="TP1B", nome="Worker SG", projeto=project_sg.name)
            user_my = _create_user(session, chave="TP1C", nome="Worker MY", projeto=project_my.name)
            request_sg = _create_transport_request(session, user_id=user_sg.id, service_date=service_date, request_kind="extra")
            request_my = _create_transport_request(session, user_id=user_my.id, service_date=service_date, request_kind="extra")
            _create_transport_request(session, user_id=user_my.id, service_date=service_date, request_kind="regular")
            _create_extra_vehicle_candidate(session, service_date=service_date, tipo="carro")
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                dashboard_scope=TransportAgentDashboardScope(request_kinds=["extra"]),
                settings_obj=_build_planning_settings(),
            )

        assert planning_input.dashboard_scope == TransportAgentDashboardScope(request_kinds=["extra"])
        assert [request.request_id for request in planning_input.requests_by_scope["extra"]] == [request_sg.id, request_my.id]
        assert planning_input.requests_by_scope["regular"] == []
        assert [partition.partition_key for partition in planning_input.partitions] == [
            "extra:PPLAN1:SG",
            "extra:PPLAN2:MY",
        ]
        assert planning_input.total_requests == 2
    finally:
        engine.dispose()


def test_build_transport_agent_planning_input_normalizes_multiselect_request_kind_order_for_hash_and_partitions(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_request_kind_order_hash.db")
    try:
        service_date = date(2026, 5, 7)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name="PPLAN-HASH", address="1 Marina Boulevard", zip_code="018989", country_code="SG")
            regular_user = _create_user(session, chave="TP1D", nome="Worker Regular", projeto=project.name)
            extra_user = _create_user(session, chave="TP1E", nome="Worker Extra", projeto=project.name)
            regular_request = _create_transport_request(
                session,
                user_id=regular_user.id,
                service_date=service_date,
                request_kind="regular",
            )
            extra_request = _create_transport_request(
                session,
                user_id=extra_user.id,
                service_date=service_date,
                request_kind="extra",
            )
            _create_extra_vehicle_candidate(session, service_date=service_date, tipo="carro")
            session.commit()

            snapshot = build_transport_operational_snapshot(
                session,
                service_date=service_date,
                route_kind="home_to_work",
            )

            planning_input_extra_regular = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                dashboard_scope=TransportAgentDashboardScope(request_kinds=["extra", "regular"]),
                settings_obj=_build_planning_settings(),
                snapshot=snapshot,
            )
            planning_input_regular_extra = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                dashboard_scope=TransportAgentDashboardScope(request_kinds=["regular", "extra"]),
                settings_obj=_build_planning_settings(),
                snapshot=snapshot,
            )

        assert planning_input_extra_regular.dashboard_scope == TransportAgentDashboardScope(
            request_kinds=["regular", "extra"],
        )
        assert planning_input_regular_extra.dashboard_scope == TransportAgentDashboardScope(
            request_kinds=["regular", "extra"],
        )
        assert [request.request_id for request in planning_input_extra_regular.requests_by_scope["regular"]] == [regular_request.id]
        assert [request.request_id for request in planning_input_extra_regular.requests_by_scope["extra"]] == [extra_request.id]
        assert [partition.partition_key for partition in planning_input_extra_regular.partitions] == [
            "extra:PPLAN-HASH:SG",
            "regular:PPLAN-HASH:SG",
        ]
        assert [partition.partition_key for partition in planning_input_regular_extra.partitions] == [
            "extra:PPLAN-HASH:SG",
            "regular:PPLAN-HASH:SG",
        ]
        assert planning_input_extra_regular.total_requests == 2
        assert planning_input_regular_extra.total_requests == 2
        assert planning_input_extra_regular.planning_input_hash == planning_input_regular_extra.planning_input_hash
    finally:
        engine.dispose()


def test_transport_agent_planning_input_schema_defaults_request_kinds_for_legacy_dashboard_scope_payload(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_legacy_scope_contract.db")
    try:
        service_date = date(2026, 5, 11)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name="PPLAN-LEGACY-SCOPE")
            user = _create_user(session, chave="TP1A", nome="Legacy Scope Worker", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            _create_extra_vehicle_candidate(session, service_date=service_date)
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                dashboard_scope=TransportAgentDashboardScope(project_ids=[project.id]),
                settings_obj=_build_planning_settings(),
            )

        legacy_payload = planning_input.model_dump(mode="json")
        legacy_payload["dashboard_scope"].pop("request_kinds", None)

        restored = TransportAgentPlanningInput.model_validate(legacy_payload)

        assert restored.dashboard_scope == TransportAgentDashboardScope(
            project_ids=[project.id],
            request_kinds=["regular", "weekend", "extra"],
        )
    finally:
        engine.dispose()


def test_build_transport_agent_planning_input_clusters_extra_requests_by_requested_time_anchor(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_extra_clusters.db")
    try:
        service_date = date(2026, 5, 8)
        with session_factory() as session:
            _configure_transport_settings(session, extra_car_tolerance_minutes=30)
            project = _create_project(session)
            user_a = _create_user(session, chave="TP14", nome="Extra Cluster A", projeto=project.name)
            user_b = _create_user(session, chave="TP15", nome="Extra Cluster B", projeto=project.name)
            user_c = _create_user(session, chave="TP16", nome="Extra Cluster C", projeto=project.name)
            request_a = _create_transport_request(
                session,
                user_id=user_a.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:00",
            )
            request_b = _create_transport_request(
                session,
                user_id=user_b.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:20",
            )
            request_c = _create_transport_request(
                session,
                user_id=user_c.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:45",
            )
            _create_extra_vehicle_candidate(session, service_date=service_date)
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )

        partition = planning_input.partitions[0]

        assert planning_input.settings.extra_car_tolerance_minutes == 30
        assert [cluster.cluster_key for cluster in partition.temporal_request_clusters] == [
            f"{partition.partition_key}:time-cluster:1",
            f"{partition.partition_key}:time-cluster:2",
        ]
        assert [cluster.request_ids for cluster in partition.temporal_request_clusters] == [
            [request_a.id, request_b.id],
            [request_c.id],
        ]
        assert [cluster.anchor_requested_time for cluster in partition.temporal_request_clusters] == [
            "19:20",
            "19:45",
        ]
        assert [cluster.earliest_requested_time for cluster in partition.temporal_request_clusters] == [
            "19:00",
            "19:45",
        ]
        assert [cluster.latest_requested_time for cluster in partition.temporal_request_clusters] == [
            "19:20",
            "19:45",
        ]
    finally:
        engine.dispose()


def test_build_transport_agent_planning_input_keeps_temporal_requested_time_clustering_scoped_to_extra_only(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_extra_only_clusters.db")
    try:
        service_date = date(2026, 5, 9)
        weekend_service_date = date(2026, 5, 10)
        with session_factory() as session:
            _configure_transport_settings(session, extra_car_tolerance_minutes=30)
            project = _create_project(session)

            regular_user_a = _create_user(session, chave="TR10", nome="Regular Gap One", projeto=project.name)
            regular_user_b = _create_user(session, chave="TR11", nome="Regular Gap Two", projeto=project.name)
            weekend_user_a = _create_user(session, chave="TW10", nome="Weekend Gap One", projeto=project.name)
            weekend_user_b = _create_user(session, chave="TW11", nome="Weekend Gap Two", projeto=project.name)
            extra_user_a = _create_user(session, chave="TE10", nome="Extra Gap One", projeto=project.name)
            extra_user_b = _create_user(session, chave="TE11", nome="Extra Gap Two", projeto=project.name)
            extra_user_c = _create_user(session, chave="TE12", nome="Extra Gap Three", projeto=project.name)

            _create_transport_request(
                session,
                user_id=regular_user_a.id,
                service_date=service_date,
                request_kind="regular",
                requested_time="06:40",
            )
            _create_transport_request(
                session,
                user_id=regular_user_b.id,
                service_date=service_date,
                request_kind="regular",
                requested_time="09:10",
            )
            _create_transport_request(
                session,
                user_id=weekend_user_a.id,
                service_date=weekend_service_date,
                request_kind="weekend",
                requested_time="07:00",
            )
            _create_transport_request(
                session,
                user_id=weekend_user_b.id,
                service_date=weekend_service_date,
                request_kind="weekend",
                requested_time="09:25",
            )
            extra_request_a = _create_transport_request(
                session,
                user_id=extra_user_a.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:00",
            )
            extra_request_b = _create_transport_request(
                session,
                user_id=extra_user_b.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:20",
            )
            extra_request_c = _create_transport_request(
                session,
                user_id=extra_user_c.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:45",
            )
            _create_extra_vehicle_candidate(session, service_date=service_date)
            session.commit()

            weekday_planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            weekend_planning_input = build_transport_agent_planning_input(
                session,
                service_date=weekend_service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )

        weekday_partitions_by_key = {
            partition.partition_key: partition
            for partition in weekday_planning_input.partitions
        }
        weekend_partitions_by_key = {
            partition.partition_key: partition
            for partition in weekend_planning_input.partitions
        }

        assert weekday_planning_input.settings.extra_car_tolerance_minutes == 30
        assert weekday_partitions_by_key["regular:PPLAN1:SG"].temporal_request_clusters == []
        assert weekend_partitions_by_key["weekend:PPLAN1:SG"].temporal_request_clusters == []
        assert [cluster.request_ids for cluster in weekday_partitions_by_key["extra:PPLAN1:SG"].temporal_request_clusters] == [
            [extra_request_a.id, extra_request_b.id],
            [extra_request_c.id],
        ]
        assert [cluster.anchor_requested_time for cluster in weekday_partitions_by_key["extra:PPLAN1:SG"].temporal_request_clusters] == [
            "19:20",
            "19:45",
        ]
    finally:
        engine.dispose()


def test_build_transport_agent_planning_input_includes_price_and_capacity_by_vehicle_type(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_capacity_price.db")
    try:
        service_date = date(2026, 5, 8)
        with session_factory() as session:
            _configure_transport_settings(session, default_car_price=123, default_minivan_price=222)
            project = _create_project(session)
            user = _create_user(session, chave="TP15", nome="Capacity Worker", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            vehicle = _create_extra_vehicle_candidate(session, service_date=service_date, tipo="carro", lugares=4)
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )

        vehicle_type_config = next(
            config for config in planning_input.settings.vehicle_type_configs if config.vehicle_type == "carro"
        )
        candidate_vehicle = planning_input.vehicles_by_scope["extra"][0]

        assert vehicle_type_config.default_capacity == 3
        assert vehicle_type_config.default_price == 123.0
        assert candidate_vehicle.vehicle_id == vehicle.id
        assert candidate_vehicle.effective_capacity == 4
        assert candidate_vehicle.default_capacity == 3
        assert candidate_vehicle.default_price == 123.0
    finally:
        engine.dispose()


def test_build_transport_agent_planning_input_hash_changes_when_address_price_or_time_changes(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_hash.db")
    try:
        service_date = date(2026, 5, 9)
        with session_factory() as session:
            _configure_transport_settings(session, default_car_price=120)
            project = _create_project(session)
            user = _create_user(session, chave="TP16", nome="Hash Worker", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            _create_extra_vehicle_candidate(session, service_date=service_date)
            session.commit()

            base_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )

            project.address = "2 Marina Boulevard"
            session.commit()
            address_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )

            _configure_transport_settings(session, default_car_price=121)
            session.commit()
            price_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )

            time_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:55",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )

        assert base_input.planning_input_hash != address_input.planning_input_hash
        assert address_input.planning_input_hash != price_input.planning_input_hash
        assert price_input.planning_input_hash != time_input.planning_input_hash
    finally:
        engine.dispose()


def test_save_transport_ai_planning_input_persists_json_and_hash_on_run(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_persist.db")
    try:
        service_date = date(2026, 5, 10)
        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session)
            user = _create_user(session, chave="TP17", nome="Persist Worker", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            _create_extra_vehicle_candidate(session, service_date=service_date)
            transport_ai_run = _create_transport_ai_run(session, actor_user_id=admin_user.id)
            transport_ai_run.service_date = service_date
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            save_transport_ai_planning_input(transport_ai_run, planning_input=planning_input)
            session.commit()
            session.refresh(transport_ai_run)

        persisted_payload = json.loads(transport_ai_run.planning_input_json)
        assert transport_ai_run.planning_input_hash == planning_input.planning_input_hash
        assert persisted_payload["planning_input_hash"] == planning_input.planning_input_hash
        assert persisted_payload["total_requests"] == 1
        assert persisted_payload["partitions"][0]["project_name"] == "PPLAN1"
    finally:
        engine.dispose()


def test_transport_agent_planning_input_schema_defaults_phase4_contract_for_legacy_payload(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_planning_legacy_contract.db")
    try:
        service_date = date(2026, 5, 11)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            user = _create_user(session, chave="TP18", nome="Legacy Contract Worker", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            _create_extra_vehicle_candidate(session, service_date=service_date)
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )

        legacy_payload = planning_input.model_dump(mode="json")
        legacy_payload["settings"].pop("extra_car_tolerance_minutes", None)
        for partition_payload in legacy_payload["partitions"]:
            partition_payload.pop("temporal_request_clusters", None)

        restored = TransportAgentPlanningInput.model_validate(legacy_payload)

        assert restored.settings.extra_car_tolerance_minutes == 30
        assert restored.dashboard_scope is None
        assert restored.dashboard_scope_project_names == []
        assert len(restored.partitions) == 1
        assert restored.partitions[0].temporal_request_clusters == []
    finally:
        engine.dispose()


def test_resolve_transport_ai_route_points_returns_coordinates_for_valid_passenger_origin(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_points_passenger.db")
    try:
        service_date = date(2026, 5, 11)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            user = _create_user(
                session,
                chave="TP20",
                nome="Route Passenger",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            request = _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            _create_extra_vehicle_candidate(session, service_date=service_date)
            session.commit()

            settings_obj = _build_planning_settings(transport_ai_route_provider="fake")
            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=settings_obj,
            )
            resolution = resolve_transport_ai_route_points(
                session,
                planning_input=planning_input,
                settings_obj=settings_obj,
            )

        assert resolution.issues == []
        assert resolution.partitions[0].passenger_points[0].request_id == request.id
        assert resolution.partitions[0].passenger_points[0].longitude == pytest.approx(103.8607)
        assert resolution.partitions[0].passenger_points[0].latitude == pytest.approx(1.2834)
    finally:
        engine.dispose()


def test_resolve_transport_ai_route_points_returns_project_destination_point(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_points_project.db")
    try:
        service_date = date(2026, 5, 12)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            user = _create_user(
                session,
                chave="TP21",
                nome="Destination Passenger",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            _create_extra_vehicle_candidate(session, service_date=service_date)
            session.commit()

            settings_obj = _build_planning_settings(transport_ai_route_provider="fake")
            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=settings_obj,
            )
            resolution = resolve_transport_ai_route_points(
                session,
                planning_input=planning_input,
                settings_obj=settings_obj,
            )

        assert resolution.issues == []
        assert resolution.partitions[0].destination_point is not None
        assert resolution.partitions[0].destination_point.project_name == project.name
        assert resolution.partitions[0].destination_point.longitude == pytest.approx(103.8545)
        assert resolution.partitions[0].destination_point.latitude == pytest.approx(1.2825)
    finally:
        engine.dispose()


def test_resolve_transport_ai_route_points_reuses_duplicate_origin_address_with_single_provider_call(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_points_duplicate.db")
    try:
        service_date = date(2026, 5, 13)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            first_user = _create_user(
                session,
                chave="TP22",
                nome="Duplicate One",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            second_user = _create_user(
                session,
                chave="TP23",
                nome="Duplicate Two",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=first_user.id, service_date=service_date, request_kind="extra")
            _create_transport_request(session, user_id=second_user.id, service_date=service_date, request_kind="extra")
            _create_extra_vehicle_candidate(session, service_date=service_date)
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            passenger_query = GeocodeRequest(
                address="10 Bayfront Avenue",
                zip_code="018956",
                country_name="Singapore",
                country_code="SG",
            )
            project_query = GeocodeRequest(
                address=project.address,
                zip_code=project.zip_code,
                country_name=project.country_name,
                country_code=project.country_code,
            )
            provider = _CountingPlanningRouteProvider(
                geocode_results={
                    passenger_query.normalized_query: _build_geocode_result(
                        provider="counting",
                        request=passenger_query,
                        longitude=103.8607,
                        latitude=1.2834,
                        formatted_address="10 Bayfront Avenue, Singapore 018956",
                        confidence=0.98,
                        country_code="SG",
                        country_name="Singapore",
                    ),
                    project_query.normalized_query: _build_geocode_result(
                        provider="counting",
                        request=project_query,
                        longitude=103.8545,
                        latitude=1.2825,
                        formatted_address="1 Marina Boulevard, Singapore 018989",
                        confidence=0.99,
                        country_code="SG",
                        country_name="Singapore",
                    ),
                }
            )

            resolution = resolve_transport_ai_route_points(
                session,
                planning_input=planning_input,
                provider=provider,
            )
            persisted_point_count = session.execute(sa.select(sa.func.count(TransportAIRoutePoint.id))).scalar_one()

        assert resolution.issues == []
        assert provider.geocode_calls.count(passenger_query.normalized_query) == 1
        assert persisted_point_count == 2
        assert len(resolution.partitions[0].passenger_points) == 2
    finally:
        engine.dispose()


def test_resolve_transport_ai_route_points_returns_blocking_issue_for_country_mismatch(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_points_country.db")
    try:
        service_date = date(2026, 5, 14)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            user = _create_user(
                session,
                chave="TP24",
                nome="Country Worker",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            _create_extra_vehicle_candidate(session, service_date=service_date)
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            passenger_query = GeocodeRequest(
                address="10 Bayfront Avenue",
                zip_code="018956",
                country_name="Singapore",
                country_code="SG",
            )
            project_query = GeocodeRequest(
                address=project.address,
                zip_code=project.zip_code,
                country_name=project.country_name,
                country_code=project.country_code,
            )
            provider = _CountingPlanningRouteProvider(
                geocode_results={
                    passenger_query.normalized_query: _build_geocode_result(
                        provider="counting",
                        request=passenger_query,
                        longitude=101.6869,
                        latitude=3.1390,
                        formatted_address="10 Bayfront Avenue, Kuala Lumpur 018956",
                        confidence=0.97,
                        country_code="MY",
                        country_name="Malaysia",
                    ),
                    project_query.normalized_query: _build_geocode_result(
                        provider="counting",
                        request=project_query,
                        longitude=103.8545,
                        latitude=1.2825,
                        formatted_address="1 Marina Boulevard, Singapore 018989",
                        confidence=0.99,
                        country_code="SG",
                        country_name="Singapore",
                    ),
                }
            )

            resolution = resolve_transport_ai_route_points(
                session,
                planning_input=planning_input,
                provider=provider,
            )

        assert [issue.code for issue in resolution.issues] == ["passenger_origin_country_mismatch"]
        assert resolution.issues[0].blocking is True
        assert resolution.partitions[0].passenger_points == []
    finally:
        engine.dispose()


def test_resolve_transport_ai_route_points_blocks_passenger_when_geocode_has_no_result(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_points_missing.db")
    try:
        service_date = date(2026, 5, 15)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            user = _create_user(
                session,
                chave="TP25",
                nome="Missing Worker",
                projeto=project.name,
                address="99 Unknown Test Avenue",
                zip_code="999999",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            _create_extra_vehicle_candidate(session, service_date=service_date)
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            project_query = GeocodeRequest(
                address=project.address,
                zip_code=project.zip_code,
                country_name=project.country_name,
                country_code=project.country_code,
            )
            provider = _CountingPlanningRouteProvider(
                geocode_results={
                    project_query.normalized_query: _build_geocode_result(
                        provider="counting",
                        request=project_query,
                        longitude=103.8545,
                        latitude=1.2825,
                        formatted_address="1 Marina Boulevard, Singapore 018989",
                        confidence=0.99,
                        country_code="SG",
                        country_name="Singapore",
                    ),
                },
                missing_queries={"99 unknown test avenue, 999999, singapore"},
            )

            resolution = resolve_transport_ai_route_points(
                session,
                planning_input=planning_input,
                provider=provider,
            )

        assert [issue.code for issue in resolution.issues] == ["passenger_origin_geocode_missing"]
        assert resolution.issues[0].blocking is True
        assert resolution.partitions[0].passenger_points == []
        assert resolution.partitions[0].destination_point is not None
    finally:
        engine.dispose()


def test_resolve_transport_ai_route_points_flags_low_confidence_result(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_points_confidence.db")
    try:
        service_date = date(2026, 5, 16)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            user = _create_user(
                session,
                chave="TP26",
                nome="Confidence Worker",
                projeto=project.name,
                address="42 Custom Test Road",
                zip_code="543210",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            _create_extra_vehicle_candidate(session, service_date=service_date)
            session.commit()

            settings_obj = _build_planning_settings(transport_ai_route_provider="fake")
            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=settings_obj,
            )
            resolution = resolve_transport_ai_route_points(
                session,
                planning_input=planning_input,
                settings_obj=settings_obj,
            )

        assert [issue.code for issue in resolution.issues] == ["passenger_origin_geocode_low_confidence"]
        assert resolution.issues[0].blocking is True
        assert resolution.partitions[0].passenger_points == []
        assert resolution.partitions[0].destination_point is not None
    finally:
        engine.dispose()


def test_build_transport_ai_route_matrices_returns_small_square_matrix_with_normalized_values(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_matrices_small.db")
    try:
        with session_factory() as session:
            passenger_point = _build_resolved_route_point(
                source_id=101,
                request_id=201,
                label="Passenger Small",
                address="10 Bayfront Avenue",
                zip_code="018956",
                longitude=103.8607,
                latitude=1.2834,
            )
            destination_point = _build_resolved_route_point(
                point_type="project_destination",
                source_id=301,
                label="PPLAN1",
                address="1 Marina Boulevard",
                zip_code="018989",
                longitude=103.8545,
                latitude=1.2825,
            )
            resolved_route_points = _build_resolved_route_points_result(
                passenger_points=[passenger_point],
                destination_point=destination_point,
            )
            points = [passenger_point, destination_point]
            provider = _CountingPlanningMatrixProvider(
                matrix_results={
                    _build_matrix_lookup_key(points=points): _build_matrix_result(
                        provider="counting",
                        profile="here/car-fast",
                        points=points,
                        durations_seconds=[[0.0, 120.6], [125.2, 0.0]],
                        distances_meters=[[0.0, 1500.6], [1499.6, 0.0]],
                    )
                }
            )

            result = build_transport_ai_route_matrices(
                session,
                resolved_route_points=resolved_route_points,
                provider=provider,
            )

        assert result.issues == []
        assert result.total_matrices == 1
        assert result.partitions[0].durations_seconds == [[0, 121], [125, 0]]
        assert result.partitions[0].distances_meters == [[0, 1501], [1500, 0]]
    finally:
        engine.dispose()


def test_build_transport_ai_route_matrices_returns_issue_for_unroutable_pair(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_matrices_issue.db")
    try:
        with session_factory() as session:
            passenger_point = _build_resolved_route_point(
                source_id=102,
                request_id=202,
                label="Passenger No Route",
                address="10 Bayfront Avenue",
                zip_code="018956",
                longitude=103.8607,
                latitude=1.2834,
            )
            destination_point = _build_resolved_route_point(
                point_type="project_destination",
                source_id=302,
                label="PPLAN1",
                address="1 Marina Boulevard",
                zip_code="018989",
                longitude=103.8545,
                latitude=1.2825,
            )
            resolved_route_points = _build_resolved_route_points_result(
                passenger_points=[passenger_point],
                destination_point=destination_point,
            )
            points = [passenger_point, destination_point]
            provider = _CountingPlanningMatrixProvider(
                matrix_results={
                    _build_matrix_lookup_key(points=points): _build_matrix_result(
                        provider="counting",
                        profile="here/car-fast",
                        points=points,
                        durations_seconds=[[0.0, None], [125.0, 0.0]],
                        distances_meters=[[0.0, None], [1500.0, 0.0]],
                    )
                }
            )

            result = build_transport_ai_route_matrices(
                session,
                resolved_route_points=resolved_route_points,
                provider=provider,
            )

        assert [issue.code for issue in result.issues] == ["route_matrix_pair_no_route"]
        assert result.issues[0].blocking is True
        assert result.partitions[0].durations_seconds[0][1] is None
        assert result.partitions[0].distances_meters[0][1] is None
    finally:
        engine.dispose()


def test_build_transport_ai_route_matrices_reuses_cache_without_second_provider_call(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_matrices_cache.db")
    try:
        with session_factory() as session:
            passenger_point = _build_resolved_route_point(
                source_id=103,
                request_id=203,
                label="Passenger Cache",
                address="10 Bayfront Avenue",
                zip_code="018956",
                longitude=103.8607,
                latitude=1.2834,
            )
            destination_point = _build_resolved_route_point(
                point_type="project_destination",
                source_id=303,
                label="PPLAN1",
                address="1 Marina Boulevard",
                zip_code="018989",
                longitude=103.8545,
                latitude=1.2825,
            )
            resolved_route_points = _build_resolved_route_points_result(
                passenger_points=[passenger_point],
                destination_point=destination_point,
            )
            points = [passenger_point, destination_point]
            provider = _CountingPlanningMatrixProvider(
                matrix_results={
                    _build_matrix_lookup_key(points=points): _build_matrix_result(
                        provider="counting",
                        profile="here/car-fast",
                        points=points,
                        durations_seconds=[[0.0, 121.0], [125.0, 0.0]],
                        distances_meters=[[0.0, 1500.0], [1495.0, 0.0]],
                    )
                }
            )

            first_result = build_transport_ai_route_matrices(
                session,
                resolved_route_points=resolved_route_points,
                provider=provider,
            )
            second_result = build_transport_ai_route_matrices(
                session,
                resolved_route_points=resolved_route_points,
                provider=provider,
            )

        assert len(provider.matrix_calls) == 1
        assert first_result.total_matrix_provider_calls == 1
        assert first_result.total_matrix_chunks == 1
        assert second_result.total_matrix_provider_calls == 0
        assert second_result.total_matrix_chunks == 0
        assert first_result.partitions[0].cached is False
        assert second_result.partitions[0].cached is True
        assert first_result.partitions[0].matrix_request_count == 1
        assert second_result.partitions[0].matrix_request_count == 0
    finally:
        engine.dispose()


def test_build_transport_ai_route_matrices_includes_project_destination_as_last_point(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_matrices_destination.db")
    try:
        with session_factory() as session:
            passenger_points = [
                _build_resolved_route_point(
                    source_id=110 + index,
                    request_id=210 + index,
                    label=f"Passenger {index}",
                    address=f"Passenger Address {index}",
                    zip_code=f"01895{index}",
                    longitude=103.8600 + (index * 0.001),
                    latitude=1.2830 + (index * 0.001),
                )
                for index in range(2)
            ]
            destination_point = _build_resolved_route_point(
                point_type="project_destination",
                source_id=304,
                label="PPLAN1",
                address="1 Marina Boulevard",
                zip_code="018989",
                longitude=103.8545,
                latitude=1.2825,
            )
            resolved_route_points = _build_resolved_route_points_result(
                passenger_points=passenger_points,
                destination_point=destination_point,
            )
            points = [*passenger_points, destination_point]
            provider = _CountingPlanningMatrixProvider(
                matrix_results={
                    _build_matrix_lookup_key(points=points): _build_matrix_result(
                        provider="counting",
                        profile="here/car-fast",
                        points=points,
                        durations_seconds=[
                            [0.0, 60.0, 180.0],
                            [65.0, 0.0, 120.0],
                            [180.0, 120.0, 0.0],
                        ],
                        distances_meters=[
                            [0.0, 600.0, 1800.0],
                            [650.0, 0.0, 1200.0],
                            [1800.0, 1200.0, 0.0],
                        ],
                    )
                }
            )

            result = build_transport_ai_route_matrices(
                session,
                resolved_route_points=resolved_route_points,
                provider=provider,
            )

        partition = result.partitions[0]
        assert partition.destination_index == 2
        assert partition.points[partition.destination_index].point_type == "project_destination"
        assert partition.points[partition.destination_index].label == "PPLAN1"
        assert len(partition.durations_seconds) == 3
        assert len(partition.durations_seconds[0]) == 3
    finally:
        engine.dispose()


def test_build_transport_ai_vehicle_candidates_existing_vehicle_uses_effective_capacity(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_vehicle_candidates_existing.db")
    try:
        service_date = date(2026, 5, 20)
        with session_factory() as session:
            _configure_transport_settings(session, default_car_price=120)
            project = _create_project(session)
            user = _create_user(session, chave="TP30", nome="Candidate Existing", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            vehicle = _create_extra_vehicle_candidate(
                session,
                service_date=service_date,
                tipo="carro",
                lugares=4,
            )
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            result = build_transport_ai_vehicle_candidates(planning_input=planning_input)

        existing_candidate = next(
            candidate
            for candidate in result.partitions[0].candidates
            if candidate.candidate_type == "existing" and candidate.vehicle_id == vehicle.id
        )
        assert existing_candidate.capacity == 4
        assert existing_candidate.default_capacity == 3
    finally:
        engine.dispose()


def test_build_transport_ai_vehicle_candidates_virtual_vehicle_uses_default_capacity(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_vehicle_candidates_virtual.db")
    try:
        service_date = date(2026, 5, 21)
        with session_factory() as session:
            _configure_transport_settings(session, default_minivan_price=180)
            project = _create_project(session)
            user = _create_user(session, chave="TP31", nome="Candidate Virtual", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            _create_extra_vehicle_candidate(session, service_date=service_date, tipo="carro", lugares=4)
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            result = build_transport_ai_vehicle_candidates(planning_input=planning_input)

        virtual_candidate = next(
            candidate
            for candidate in result.partitions[0].candidates
            if candidate.candidate_type == "virtual" and candidate.vehicle_type == "minivan"
        )
        assert virtual_candidate.capacity == 6
        assert virtual_candidate.default_capacity == 6
        assert virtual_candidate.recommended_action_type == "create"
    finally:
        engine.dispose()


def test_build_transport_ai_vehicle_candidates_skips_vehicle_types_without_price(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_vehicle_candidates_missing_price.db")
    try:
        service_date = date(2026, 5, 22)
        with session_factory() as session:
            _configure_transport_settings(session, default_van_price=None)
            project = _create_project(session)
            user = _create_user(session, chave="TP32", nome="Candidate Missing Price", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            _create_extra_vehicle_candidate(session, service_date=service_date, tipo="van", lugares=10)
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            result = build_transport_ai_vehicle_candidates(planning_input=planning_input)

        assert all(candidate.vehicle_type != "van" for candidate in result.partitions[0].candidates)
    finally:
        engine.dispose()


def test_build_transport_ai_vehicle_candidates_existing_keep_penalty_is_lower_than_virtual_create(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_vehicle_candidates_penalty.db")
    try:
        service_date = date(2026, 5, 23)
        with session_factory() as session:
            _configure_transport_settings(session, default_car_price=120)
            project = _create_project(session)
            user = _create_user(session, chave="TP33", nome="Candidate Penalty", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            vehicle = _create_extra_vehicle_candidate(session, service_date=service_date, tipo="carro", lugares=4)
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            result = build_transport_ai_vehicle_candidates(planning_input=planning_input)

        existing_candidate = next(
            candidate
            for candidate in result.partitions[0].candidates
            if candidate.candidate_type == "existing" and candidate.vehicle_id == vehicle.id
        )
        virtual_candidate = next(
            candidate
            for candidate in result.partitions[0].candidates
            if candidate.candidate_type == "virtual" and candidate.vehicle_type == "carro"
        )
        assert existing_candidate.change_penalty < virtual_candidate.change_penalty
    finally:
        engine.dispose()


def test_build_transport_ai_vehicle_candidates_respect_partition_request_kind(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_vehicle_candidates_scope.db")
    try:
        service_date = date(2026, 5, 26)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            extra_user = _create_user(session, chave="TP34", nome="Candidate Extra", projeto=project.name)
            regular_user = _create_user(session, chave="TP35", nome="Candidate Regular", projeto=project.name)
            _create_transport_request(session, user_id=extra_user.id, service_date=service_date, request_kind="extra")
            _create_transport_request(session, user_id=regular_user.id, service_date=service_date, request_kind="regular")
            _create_extra_vehicle_candidate(session, service_date=service_date, tipo="carro", lugares=4)
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            result = build_transport_ai_vehicle_candidates(planning_input=planning_input)

        partitions_by_key = {
            partition.partition_key: partition
            for partition in result.partitions
        }
        extra_partition = partitions_by_key["extra:PPLAN1:SG"]
        regular_partition = partitions_by_key["regular:PPLAN1:SG"]

        assert {candidate.request_kind for candidate in extra_partition.candidates} == {"extra"}
        assert {candidate.service_scope for candidate in extra_partition.candidates} == {"extra"}
        assert {candidate.request_kind for candidate in regular_partition.candidates} == {"regular"}
        assert {candidate.service_scope for candidate in regular_partition.candidates} == {"regular"}
    finally:
        engine.dispose()


def test_solve_transport_ai_partition_chooses_car_when_three_passengers_fit_and_are_cheaper(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_partition_solver_car.db")
    try:
        service_date = date(2026, 5, 27)
        with session_factory() as session:
            _configure_transport_settings(
                session,
                default_car_price=100,
                default_minivan_price=180,
                default_van_price=260,
                default_bus_price=400,
            )
            project = _create_project(session)
            for index in range(1, 4):
                user = _create_user(session, chave=f"TP4{index}", nome=f"Solver Car {index}", projeto=project.name)
                _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=_build_dense_solver_matrix(
                    passenger_count=3,
                    between_passenger_seconds=300,
                    passenger_to_destination_seconds=600,
                ),
            )

            result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )

        assert result.algorithm_used == _expected_partition_solver_algorithm()
        assert result.is_feasible is True
        assert result.total_vehicles_used == 1
        assert len(result.routes) == 1
        assert result.routes[0].vehicle_type == "carro"
        assert sorted(result.routes[0].request_ids) == sorted(request.request_id for request in partition.requests)
    finally:
        engine.dispose()


def test_solve_transport_ai_partition_keeps_heuristic_fallback_working_with_extended_runtime(monkeypatch, tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_partition_solver_extended_runtime_fallback.db")
    observed: dict[str, int] = {}

    def _force_heuristic_fallback(*, request_ids, route_options, max_runtime_seconds):
        observed["max_runtime_seconds"] = max_runtime_seconds
        return "heuristic", None

    monkeypatch.setattr(
        transport_ai_planning_module,
        "_solve_transport_ai_partition_with_ortools",
        _force_heuristic_fallback,
    )

    try:
        service_date = date(2026, 5, 27)
        with session_factory() as session:
            _configure_transport_settings(
                session,
                default_car_price=100,
                default_minivan_price=180,
                default_van_price=260,
                default_bus_price=400,
            )
            project = _create_project(session)
            for index in range(1, 4):
                user = _create_user(session, chave=f"TP9{index}", nome=f"Fallback Runtime {index}", projeto=project.name)
                _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(transport_ai_max_runtime_seconds=11),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=_build_dense_solver_matrix(
                    passenger_count=3,
                    between_passenger_seconds=300,
                    passenger_to_destination_seconds=600,
                ),
            )

            result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )

        assert observed["max_runtime_seconds"] == 11
        assert result.algorithm_used == "heuristic"
        assert result.is_feasible is True
        assert result.total_vehicles_used == 1
    finally:
        engine.dispose()


def test_solve_transport_ai_partition_chooses_minivan_when_cheaper_than_two_cars_for_six_passengers(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_partition_solver_minivan.db")
    try:
        service_date = date(2026, 5, 28)
        with session_factory() as session:
            _configure_transport_settings(
                session,
                default_car_price=100,
                default_minivan_price=180,
                default_van_price=260,
                default_bus_price=400,
            )
            project = _create_project(session)
            for index in range(1, 7):
                user = _create_user(session, chave=f"TP5{index}", nome=f"Solver Minivan {index}", projeto=project.name)
                _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=_build_dense_solver_matrix(
                    passenger_count=6,
                    between_passenger_seconds=240,
                    passenger_to_destination_seconds=600,
                ),
            )

            result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )

        assert result.is_feasible is True
        assert result.total_vehicles_used == 1
        assert result.routes[0].vehicle_type == "minivan"
        assert len(result.routes[0].request_ids) == 6
        assert result.total_estimated_cost == pytest.approx(180.0)
    finally:
        engine.dispose()


def test_solve_transport_ai_partition_splits_passengers_when_single_route_exceeds_time_window(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_partition_solver_split.db")
    try:
        service_date = date(2026, 5, 29)
        with session_factory() as session:
            _configure_transport_settings(
                session,
                default_car_price=100,
                default_minivan_price=180,
                default_van_price=260,
                default_bus_price=400,
            )
            project = _create_project(session)
            for index in range(1, 4):
                user = _create_user(session, chave=f"TP6{index}", nome=f"Solver Split {index}", projeto=project.name)
                _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="07:15",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=_build_dense_solver_matrix(
                    passenger_count=3,
                    between_passenger_seconds=700,
                    passenger_to_destination_seconds=700,
                ),
            )

            result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )

        assert result.is_feasible is True
        assert result.total_vehicles_used == 2
        assert {route.vehicle_type for route in result.routes} == {"carro"}
        assert sorted(request_id for route in result.routes for request_id in route.request_ids) == sorted(
            request.request_id for request in partition.requests
        )
    finally:
        engine.dispose()


def test_solve_transport_ai_partition_returns_blocking_issue_when_no_solution_exists(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_partition_solver_no_solution.db")
    try:
        service_date = date(2026, 5, 30)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            user = _create_user(session, chave="TP70", nome="Solver Impossible", projeto=project.name)
            request = _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="07:20",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=_build_dense_solver_matrix(
                    passenger_count=1,
                    between_passenger_seconds=0,
                    passenger_to_destination_seconds=2000,
                ),
            )

            result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )

        assert result.is_feasible is False
        assert result.routes == []
        assert result.unallocated_request_ids == [request.id]
        assert [issue.code for issue in result.issues] == ["transport_ai_partition_no_solution"]
        assert result.issues[0].blocking is True
    finally:
        engine.dispose()


def test_solve_transport_ai_partition_ignores_vehicle_tolerance_when_evaluating_window(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_partition_solver_tolerance.db")
    try:
        service_date = date(2026, 5, 31)
        with session_factory() as session:
            _configure_transport_settings(
                session,
                default_car_price=100,
                default_minivan_price=180,
                default_van_price=260,
                default_bus_price=400,
            )
            location_settings_module.upsert_transport_vehicle_default_seat_counts(
                session,
                default_car_seats=3,
                default_minivan_seats=6,
                default_van_seats=10,
                default_bus_seats=40,
                default_tolerance_minutes=15,
            )
            project = _create_project(session)
            for index in range(1, 4):
                user = _create_user(session, chave=f"TP8{index}", nome=f"Solver Tolerance {index}", projeto=project.name)
                _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=_build_dense_solver_matrix(
                    passenger_count=3,
                    between_passenger_seconds=1300,
                    passenger_to_destination_seconds=1300,
                ),
            )

            result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )

        assert planning_input.settings.default_tolerance_minutes == 15
        assert result.is_feasible is True
        assert result.total_vehicles_used == 2
        assert {route.vehicle_type for route in result.routes} == {"carro"}
    finally:
        engine.dispose()


def test_schedule_transport_ai_route_times_calculates_expected_pickups_for_simple_route(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_schedule_simple.db")
    try:
        service_date = date(2026, 6, 1)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            for index in range(1, 4):
                user = _create_user(session, chave=f"TP9{index}", nome=f"Schedule Simple {index}", projeto=project.name)
                _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="regular")
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=[
                    [0, 600, 2400, 2700],
                    [600, 0, 480, 1800],
                    [2400, 480, 0, 720],
                    [2700, 1800, 720, 0],
                ],
            )
            solve_result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )

            scheduled_result = schedule_transport_ai_route_times(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                partition_solve_result=solve_result,
            )

        assert scheduled_result.is_feasible is True
        assert scheduled_result.issues == []
        route = scheduled_result.routes[0]
        assert route.projected_arrival_time == "07:45"
        assert [passenger.scheduled_pickup_time for passenger in route.passengers] == ["07:15", "07:25", "07:33"]
    finally:
        engine.dispose()


def test_schedule_transport_ai_route_times_allows_first_pickup_exactly_at_earliest(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_schedule_exact_earliest.db")
    try:
        service_date = date(2026, 6, 2)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            user = _create_user(session, chave="TPA1", nome="Schedule Earliest Exact", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="regular")
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=[
                    [0, 3300],
                    [3300, 0],
                ],
            )
            solve_result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )

            scheduled_result = schedule_transport_ai_route_times(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                partition_solve_result=solve_result,
            )

        assert scheduled_result.is_feasible is True
        assert scheduled_result.routes[0].passengers[0].scheduled_pickup_time == "06:50"
    finally:
        engine.dispose()


def test_schedule_transport_ai_route_times_blocks_when_first_pickup_would_be_before_earliest(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_schedule_before_earliest.db")
    try:
        service_date = date(2026, 6, 3)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            user = _create_user(session, chave="TPA2", nome="Schedule Before Earliest", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="regular")
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            feasible_route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=[
                    [0, 3300],
                    [3300, 0],
                ],
            )
            solve_result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=feasible_route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )
            invalid_route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=[
                    [0, 3360],
                    [3360, 0],
                ],
            )

            scheduled_result = schedule_transport_ai_route_times(
                planning_input=planning_input,
                route_matrix_partition=invalid_route_matrix_partition,
                partition_solve_result=solve_result,
            )

        assert scheduled_result.is_feasible is False
        assert [issue.code for issue in scheduled_result.issues] == ["transport_ai_route_first_pickup_before_earliest"]
        assert scheduled_result.routes[0].passengers[0].scheduled_pickup_time == "06:49"
    finally:
        engine.dispose()


def test_schedule_transport_ai_route_times_blocks_when_arrival_is_after_limit(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_schedule_arrival_limit.db")
    try:
        service_date = date(2026, 6, 4)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            user = _create_user(session, chave="TPA3", nome="Schedule Late Arrival", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="extra")
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=[
                    [0, 1200],
                    [1200, 0],
                ],
            )
            solve_result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )

            scheduled_result = schedule_transport_ai_route_times(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                partition_solve_result=solve_result,
                arrival_at_work_time="07:50",
            )

        assert scheduled_result.is_feasible is False
        assert [issue.code for issue in scheduled_result.issues] == ["transport_ai_route_arrival_after_limit"]
        assert scheduled_result.routes[0].projected_arrival_time == "07:50"
    finally:
        engine.dispose()


def test_schedule_transport_ai_route_times_rounds_seconds_consistently(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_route_schedule_rounding.db")
    try:
        service_date = date(2026, 6, 5)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            user = _create_user(session, chave="TPA4", nome="Schedule Rounded Seconds", projeto=project.name)
            _create_transport_request(session, user_id=user.id, service_date=service_date, request_kind="regular")
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=[
                    [0, 601],
                    [601, 0],
                ],
            )
            solve_result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )

            scheduled_result = schedule_transport_ai_route_times(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                partition_solve_result=solve_result,
            )

        assert scheduled_result.is_feasible is True
        assert scheduled_result.routes[0].passengers[0].scheduled_pickup_time == "07:34"
    finally:
        engine.dispose()


def test_solve_transport_ai_partition_keeps_extra_home_to_work_routes_inside_temporal_clusters(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_extra_home_clusters.db")
    try:
        service_date = date(2026, 6, 6)
        with session_factory() as session:
            _configure_transport_settings(session, extra_car_tolerance_minutes=30)
            project = _create_project(session)
            user_a = _create_user(session, chave="TPA5", nome="Extra Solve A", projeto=project.name)
            user_b = _create_user(session, chave="TPA6", nome="Extra Solve B", projeto=project.name)
            user_c = _create_user(session, chave="TPA7", nome="Extra Solve C", projeto=project.name)
            request_a = _create_transport_request(
                session,
                user_id=user_a.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:00",
            )
            request_b = _create_transport_request(
                session,
                user_id=user_b.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:20",
            )
            request_c = _create_transport_request(
                session,
                user_id=user_c.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:45",
            )
            _create_extra_vehicle_candidate(session, service_date=service_date, lugares=4)
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=_build_dense_solver_matrix(
                    passenger_count=3,
                    between_passenger_seconds=300,
                    passenger_to_destination_seconds=600,
                ),
            )

            solve_result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )

        assert solve_result.is_feasible is True
        assert solve_result.total_vehicles_used == 2
        assert sorted(sorted(route.request_ids) for route in solve_result.routes) == [
            [request_a.id, request_b.id],
            [request_c.id],
        ]
    finally:
        engine.dispose()


def test_solve_transport_ai_partition_keeps_extra_work_to_home_routes_inside_temporal_clusters(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_extra_work_clusters.db")
    try:
        service_date = date(2026, 6, 6)
        with session_factory() as session:
            _configure_transport_settings(session, extra_car_tolerance_minutes=30)
            project = _create_project(session)
            user_a = _create_user(session, chave="A5W1", nome="Extra Work Solve A", projeto=project.name)
            user_b = _create_user(session, chave="A6W1", nome="Extra Work Solve B", projeto=project.name)
            user_c = _create_user(session, chave="A7W1", nome="Extra Work Solve C", projeto=project.name)
            request_a = _create_transport_request(
                session,
                user_id=user_a.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:00",
            )
            request_b = _create_transport_request(
                session,
                user_id=user_b.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:20",
            )
            request_c = _create_transport_request(
                session,
                user_id=user_c.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:45",
            )
            _create_extra_vehicle_candidate(
                session,
                service_date=service_date,
                lugares=4,
                route_kind="work_to_home",
            )
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="work_to_home",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=_build_dense_solver_matrix(
                    passenger_count=3,
                    between_passenger_seconds=300,
                    passenger_to_destination_seconds=600,
                ),
            )

            solve_result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )

        assert solve_result.is_feasible is True
        assert solve_result.total_vehicles_used == 2
        assert sorted(sorted(route.request_ids) for route in solve_result.routes) == [
            [request_a.id, request_b.id],
            [request_c.id],
        ]
    finally:
        engine.dispose()


def test_solve_transport_ai_partition_allows_extra_work_to_home_routes_beyond_home_window(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_extra_work_window.db")
    try:
        service_date = date(2026, 6, 7)
        with session_factory() as session:
            _configure_transport_settings(session, extra_car_tolerance_minutes=30)
            project = _create_project(session)
            user = _create_user(session, chave="A8W1", nome="Extra Work Window", projeto=project.name)
            request = _create_transport_request(
                session,
                user_id=user.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:20",
            )
            _create_extra_vehicle_candidate(
                session,
                service_date=service_date,
                lugares=4,
                route_kind="work_to_home",
            )
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="work_to_home",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=[
                    [0, 4000],
                    [4000, 0],
                ],
            )

            solve_result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )

        assert solve_result.is_feasible is True
        assert solve_result.issues == []
        assert len(solve_result.routes) == 1
        assert solve_result.routes[0].request_ids == [request.id]
    finally:
        engine.dispose()


def test_schedule_transport_ai_route_times_anchors_extra_home_to_work_at_cluster_eta(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_extra_home_eta.db")
    try:
        service_date = date(2026, 6, 7)
        with session_factory() as session:
            _configure_transport_settings(session, extra_car_tolerance_minutes=30)
            project = _create_project(session)
            user_a = _create_user(session, chave="TPA8", nome="Extra Eta A", projeto=project.name)
            user_b = _create_user(session, chave="TPA9", nome="Extra Eta B", projeto=project.name)
            request_a = _create_transport_request(
                session,
                user_id=user_a.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:00",
            )
            request_b = _create_transport_request(
                session,
                user_id=user_b.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:20",
            )
            _create_extra_vehicle_candidate(session, service_date=service_date, lugares=4)
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=_build_dense_solver_matrix(
                    passenger_count=2,
                    between_passenger_seconds=300,
                    passenger_to_destination_seconds=600,
                ),
            )

            solve_result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )
            scheduled_result = schedule_transport_ai_route_times(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                partition_solve_result=solve_result,
            )

        assert scheduled_result.is_feasible is True
        assert scheduled_result.issues == []
        assert len(scheduled_result.routes) == 1
        route = scheduled_result.routes[0]
        assert sorted(route.request_ids) == [request_a.id, request_b.id]
        assert route.projected_arrival_time == "19:20"
        assert sorted(
            passenger.scheduled_pickup_time
            for passenger in route.passengers
            if passenger.scheduled_pickup_time is not None
        ) == ["19:05", "19:10"]
    finally:
        engine.dispose()


def test_schedule_transport_ai_route_times_anchors_extra_work_to_home_at_cluster_etd(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_extra_work_etd.db")
    try:
        service_date = date(2026, 6, 8)
        with session_factory() as session:
            _configure_transport_settings(session, extra_car_tolerance_minutes=30)
            project = _create_project(session)
            user_a = _create_user(session, chave="B1W1", nome="Extra Etd A", projeto=project.name)
            user_b = _create_user(session, chave="B2W1", nome="Extra Etd B", projeto=project.name)
            request_a = _create_transport_request(
                session,
                user_id=user_a.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:00",
            )
            request_b = _create_transport_request(
                session,
                user_id=user_b.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:20",
            )
            _create_extra_vehicle_candidate(
                session,
                service_date=service_date,
                lugares=4,
                route_kind="work_to_home",
            )
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="work_to_home",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=_build_dense_solver_matrix(
                    passenger_count=2,
                    between_passenger_seconds=300,
                    passenger_to_destination_seconds=600,
                ),
            )

            solve_result = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )
            scheduled_result = schedule_transport_ai_route_times(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                partition_solve_result=solve_result,
            )

        assert scheduled_result.is_feasible is True
        assert scheduled_result.issues == []
        assert len(scheduled_result.routes) == 1
        route = scheduled_result.routes[0]
        assert sorted(route.request_ids) == [request_a.id, request_b.id]
        assert route.projected_arrival_time == "19:35"
        assert sorted(
            passenger.scheduled_pickup_time
            for passenger in route.passengers
            if passenger.scheduled_pickup_time is not None
        ) == ["19:20", "19:20"]
    finally:
        engine.dispose()


def test_build_transport_agent_plan_from_solver_result_builds_directional_extra_work_to_home_itinerary(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_extra_work_directional_plan.db")
    try:
        service_date = date(2026, 6, 9)
        with session_factory() as session:
            _configure_transport_settings(session, extra_car_tolerance_minutes=30)
            project = _create_project(session, name="PEXTRAWTH")
            user_a = _create_user(
                session,
                chave="EWT1",
                nome="Extra Return A",
                projeto=project.name,
                address="21 Return Lane",
                zip_code="540210",
            )
            user_b = _create_user(
                session,
                chave="EWT2",
                nome="Extra Return B",
                projeto=project.name,
                address="22 Return Lane",
                zip_code="540220",
            )
            request_a = _create_transport_request(
                session,
                user_id=user_a.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:00",
            )
            request_b = _create_transport_request(
                session,
                user_id=user_b.id,
                service_date=service_date,
                request_kind="extra",
                requested_time="19:20",
            )
            _create_extra_vehicle_candidate(
                session,
                service_date=service_date,
                lugares=4,
                route_kind="work_to_home",
            )
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="work_to_home",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=[
                    [0, 200, 50],
                    [200, 0, 100],
                    [300, 700, 0],
                ],
                distances_meters=[
                    [0, 2000, 500],
                    [2000, 0, 1000],
                    [3000, 7000, 0],
                ],
            )

            solved_partition = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )
            scheduled_partition = schedule_transport_ai_route_times(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                partition_solve_result=solved_partition,
            )
            route_matrices_result = TransportAgentRouteMatricesResult(
                planning_input_hash=planning_input.planning_input_hash,
                provider="solver-test",
                profile="here/car-fast",
                partitions=[route_matrix_partition],
                issues=[],
                total_matrices=1,
            )

            plan = build_transport_agent_plan_from_solver_result(
                planning_input=planning_input,
                route_matrices_result=route_matrices_result,
                partition_solve_results=[scheduled_partition],
            )

        assert plan.validation_issues == []
        assert len(plan.route_itineraries) == 1
        itinerary = plan.route_itineraries[0]
        assert itinerary.route_kind == "work_to_home"
        assert [stop.stop_type for stop in itinerary.stops] == ["pickup", "destination", "destination"]
        assert itinerary.stops[0].request_id is None
        assert itinerary.stops[0].address == project.address
        assert [stop.request_id for stop in itinerary.stops[1:]] == [request_a.id, request_b.id]
        assert [stop.address for stop in itinerary.stops[1:]] == [user_a.end_rua, user_b.end_rua]
        assert [stop.scheduled_time for stop in itinerary.stops] == ["19:20", "19:25", "19:29"]
        assert itinerary.projected_arrival_time == "19:29"

        work_to_home_allocations = sorted(
            plan.passenger_allocations,
            key=lambda allocation: allocation.pickup_order,
        )
        assert [allocation.request_id for allocation in work_to_home_allocations] == [request_a.id, request_b.id]
        assert [allocation.scheduled_pickup_time for allocation in work_to_home_allocations] == ["19:20", "19:20"]
        assert [allocation.scheduled_dropoff_time for allocation in work_to_home_allocations] == ["19:25", "19:29"]
        assert [allocation.projected_arrival_time for allocation in work_to_home_allocations] == ["19:25", "19:29"]
    finally:
        engine.dispose()


def test_build_transport_agent_plan_from_solver_result_consolidates_actions_costs_and_itineraries(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_plan_builder_success.db")
    try:
        service_date = date(2026, 6, 6)
        with session_factory() as session:
            _configure_transport_settings(
                session,
                default_car_price=100,
                default_minivan_price=180,
                default_van_price=260,
                default_bus_price=400,
            )
            first_project = _create_project(session, name="PPLAN1")
            second_project = _create_project(
                session,
                name="PPLAN2",
                address="25 Raffles Place",
                zip_code="048621",
            )
            first_user = _create_user(
                session,
                chave="TPB1",
                nome="Plan Existing 1",
                projeto=first_project.name,
            )
            _create_transport_request(
                session,
                user_id=first_user.id,
                service_date=service_date,
                request_kind="extra",
            )
            for index in range(1, 7):
                user = _create_user(
                    session,
                    chave=f"TPC{index}",
                    nome=f"Plan Virtual {index}",
                    projeto=second_project.name,
                    address=f"{10 + index} Virtual Street",
                    zip_code=f"54012{index}",
                )
                _create_transport_request(
                    session,
                    user_id=user.id,
                    service_date=service_date,
                    request_kind="extra",
                )
            existing_vehicle = _create_extra_vehicle_candidate(
                session,
                placa="SBA6006A",
                tipo="carro",
                lugares=3,
                service_date=service_date,
            )
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partitions_by_project = {
                partition.project_name: partition
                for partition in planning_input.partitions
            }
            vehicle_candidates_by_partition = {
                partition.partition_key: partition
                for partition in build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions
            }
            route_matrix_partitions = [
                _build_solver_route_matrix_partition(
                    partition=partitions_by_project["PPLAN1"],
                    durations_seconds=[
                        [0, 1200],
                        [1200, 0],
                    ],
                ),
                _build_solver_route_matrix_partition(
                    partition=partitions_by_project["PPLAN2"],
                    durations_seconds=_build_dense_solver_matrix(
                        passenger_count=6,
                        between_passenger_seconds=240,
                        passenger_to_destination_seconds=600,
                    ),
                ),
            ]
            scheduled_partition_results = []
            for route_matrix_partition in route_matrix_partitions:
                solved_partition = solve_transport_ai_partition(
                    planning_input=planning_input,
                    route_matrix_partition=route_matrix_partition,
                    vehicle_candidates_partition=vehicle_candidates_by_partition[route_matrix_partition.partition_key],
                )
                scheduled_partition_results.append(
                    schedule_transport_ai_route_times(
                        planning_input=planning_input,
                        route_matrix_partition=route_matrix_partition,
                        partition_solve_result=solved_partition,
                    )
                )

            route_matrices_result = TransportAgentRouteMatricesResult(
                planning_input_hash=planning_input.planning_input_hash,
                provider="solver-test",
                profile="here/car-fast",
                partitions=route_matrix_partitions,
                issues=[],
                total_matrices=len(route_matrix_partitions),
            )

            plan = build_transport_agent_plan_from_solver_result(
                planning_input=planning_input,
                route_matrices_result=route_matrices_result,
                partition_solve_results=scheduled_partition_results,
            )

        assert sorted(allocation.request_id for allocation in plan.passenger_allocations) == sorted(
            request.request_id
            for partition in planning_input.partitions
            for request in partition.requests
        )
        assert {action.action_type for action in plan.vehicle_actions} == {"keep", "create"}
        keep_action = next(action for action in plan.vehicle_actions if action.action_type == "keep")
        create_action = next(action for action in plan.vehicle_actions if action.action_type == "create")
        assert keep_action.vehicle_id == existing_vehicle.id
        assert keep_action.client_vehicle_key.startswith(f"existing:{existing_vehicle.id}")
        assert create_action.vehicle_id is None
        assert create_action.client_vehicle_key is not None
        assert plan.cost_summary.current_total_estimated_cost == pytest.approx(100.0)
        assert plan.cost_summary.suggested_total_estimated_cost == pytest.approx(280.0)
        assert plan.cost_summary.estimated_cost_delta == pytest.approx(180.0)
        change_summary_by_type = {
            row.vehicle_type: row
            for row in plan.change_summary.by_vehicle_type
        }
        assert change_summary_by_type["carro"].keep_count == 1
        assert change_summary_by_type["minivan"].create_count == 1
        assert len(plan.vehicle_review_tables) == len(plan.route_itineraries)
        review_tables_by_action = {
            table.action_type: table
            for table in plan.vehicle_review_tables
        }
        keep_review_table = review_tables_by_action["keep"]
        create_review_table = review_tables_by_action["create"]
        assert keep_review_table.vehicle_ref == keep_action.after["vehicle_ref"]
        assert keep_review_table.vehicle_label == "SBA6006A"
        assert {badge.text for badge in keep_review_table.header_badges} >= {
            "Extra",
            "Home To Work",
            "Keep",
        }
        assert keep_review_table.rows[0].user_name == "Plan Existing 1"
        assert keep_review_table.rows[0].user_address == "12 Worker Street"
        assert keep_review_table.rows[0].home_to_work_boarding is not None
        assert keep_review_table.rows[0].home_to_work_boarding_is_placeholder is False
        assert keep_review_table.rows[0].work_to_home_dropoff is None
        assert keep_review_table.rows[0].work_to_home_dropoff_is_placeholder is True
        assert [row.pickup_order for row in create_review_table.rows] == sorted(
            row.pickup_order for row in create_review_table.rows
        )
        assert create_review_table.rows[0].user_address == "11 Virtual Street"
        assert create_review_table.rows[-1].user_address == "16 Virtual Street"
        assert all(itinerary.stops[-1].stop_type == "destination" for itinerary in plan.route_itineraries)
        assert all(itinerary.stops[-1].request_id is None for itinerary in plan.route_itineraries)
        assert all(itinerary.stops[-1].project_name in {"PPLAN1", "PPLAN2"} for itinerary in plan.route_itineraries)
        assert plan.validation_issues == []
        roundtrip = TransportAgentPlan.model_validate_json(plan.model_dump_json())
        assert roundtrip == plan
    finally:
        engine.dispose()


def test_build_transport_ai_vehicle_review_tables_merges_bidirectional_rows_and_keeps_one_way_placeholders():
    review_tables = _build_transport_ai_vehicle_review_tables(
        vehicle_actions=[],
        passenger_allocations=[
            TransportAgentPassengerAllocation.model_validate({
                "request_id": 301,
                "request_kind": "extra",
                "service_date": "2026-06-09",
                "route_kind": "home_to_work",
                "vehicle_ref": "new:solver-1",
                "user_id": 501,
                "chave": "A301",
                "nome": "Alice Tan",
                "project_name": "P80",
                "pickup_order": 0,
                "scheduled_pickup_time": "07:05",
                "projected_arrival_time": "07:45",
                "rationale": "Home leg.",
            }),
            TransportAgentPassengerAllocation.model_validate({
                "request_id": 301,
                "request_kind": "extra",
                "service_date": "2026-06-09",
                "route_kind": "work_to_home",
                "vehicle_ref": "new:solver-1",
                "user_id": 501,
                "chave": "A301",
                "nome": "Alice Tan",
                "project_name": "P80",
                "pickup_order": 0,
                "scheduled_pickup_time": "18:10",
                "scheduled_dropoff_time": "18:37",
                "projected_arrival_time": "18:40",
                "rationale": "Return leg.",
            }),
            TransportAgentPassengerAllocation.model_validate({
                "request_id": 302,
                "request_kind": "extra",
                "service_date": "2026-06-09",
                "route_kind": "work_to_home",
                "vehicle_ref": "new:solver-1",
                "user_id": 502,
                "chave": "A302",
                "nome": "Bob Lim",
                "project_name": "P80",
                "pickup_order": 1,
                "scheduled_pickup_time": "18:20",
                "projected_arrival_time": "18:55",
                "rationale": "Return-only extra leg.",
            }),
        ],
        route_itineraries=[
            TransportAgentVehicleItinerary.model_validate({
                "route_key": "route:solver-1:home",
                "partition_key": "extra:P80:SG:home",
                "vehicle_ref": "new:solver-1",
                "service_scope": "extra",
                "route_kind": "home_to_work",
                "vehicle_type": "van",
                "client_vehicle_key": "solver-1",
                "plate": "SGX1234",
                "project_name": "P80",
                "country_code": "SG",
                "country_name": "Singapore",
                "estimated_cost": 28,
                "total_duration_seconds": 2400,
                "total_distance_meters": 9800,
                "projected_arrival_time": "07:45",
                "stops": [
                    TransportAgentRouteStop.model_validate({
                        "stop_order": 0,
                        "stop_type": "pickup",
                        "request_id": 301,
                        "user_id": 501,
                        "passenger_name": "Alice Tan",
                        "project_name": "P80",
                        "address": "7 Garden Street, 540123, SG",
                        "zip_code": "540123",
                        "country_code": "SG",
                        "longitude": 103.85,
                        "latitude": 1.30,
                        "scheduled_time": "07:05",
                    }),
                ],
            }),
            TransportAgentVehicleItinerary.model_validate({
                "route_key": "route:solver-1:return",
                "partition_key": "extra:P80:SG:return",
                "vehicle_ref": "new:solver-1",
                "service_scope": "extra",
                "route_kind": "work_to_home",
                "vehicle_type": "van",
                "client_vehicle_key": "solver-1",
                "plate": "SGX1234",
                "project_name": "P80",
                "country_code": "SG",
                "country_name": "Singapore",
                "estimated_cost": 32,
                "total_duration_seconds": 2700,
                "total_distance_meters": 10200,
                "projected_arrival_time": "18:55",
                "stops": [
                    TransportAgentRouteStop.model_validate({
                        "stop_order": 0,
                        "stop_type": "pickup",
                        "request_id": 302,
                        "user_id": 502,
                        "passenger_name": "Bob Lim",
                        "project_name": "P80",
                        "address": "1 Marina Boulevard",
                        "zip_code": "018989",
                        "country_code": "SG",
                        "longitude": 103.85,
                        "latitude": 1.29,
                        "scheduled_time": "18:20",
                    }),
                ],
            }),
        ],
    )

    assert len(review_tables) == 1
    review_table = review_tables[0]
    assert review_table.vehicle_ref == "new:solver-1"
    assert review_table.route_kind is None
    assert review_table.estimated_cost == pytest.approx(60.0)
    assert len(review_table.rows) == 2
    assert [row.request_id for row in review_table.rows] == [301, 302]

    bidirectional_row = review_table.rows[0]
    work_to_home_only_row = review_table.rows[1]
    assert bidirectional_row.user_address == "7 Garden Street"
    assert bidirectional_row.home_to_work_boarding == "07:05"
    assert bidirectional_row.home_to_work_boarding_is_placeholder is False
    assert bidirectional_row.work_to_home_dropoff == "18:37"
    assert bidirectional_row.work_to_home_dropoff_is_placeholder is False

    assert work_to_home_only_row.user_address is None
    assert work_to_home_only_row.home_to_work_boarding is None
    assert work_to_home_only_row.home_to_work_boarding_is_placeholder is True
    assert work_to_home_only_row.work_to_home_dropoff == "18:55"
    assert work_to_home_only_row.work_to_home_dropoff_is_placeholder is False


def test_build_transport_agent_plan_from_solver_result_tracks_unallocated_requests_as_issues(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_plan_builder_unallocated.db")
    try:
        service_date = date(2026, 6, 7)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session)
            user = _create_user(session, chave="TPD1", nome="Plan Unallocated", projeto=project.name)
            request = _create_transport_request(
                session,
                user_id=user.id,
                service_date=service_date,
                request_kind="extra",
            )
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="07:20",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=[
                    [0, 4000],
                    [4000, 0],
                ],
            )
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            solved_partition = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )
            scheduled_partition = schedule_transport_ai_route_times(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                partition_solve_result=solved_partition,
            )
            route_matrices_result = TransportAgentRouteMatricesResult(
                planning_input_hash=planning_input.planning_input_hash,
                provider="solver-test",
                profile="here/car-fast",
                partitions=[route_matrix_partition],
                issues=[],
                total_matrices=1,
            )

            plan = build_transport_agent_plan_from_solver_result(
                planning_input=planning_input,
                route_matrices_result=route_matrices_result,
                partition_solve_results=[scheduled_partition],
            )

        assert plan.passenger_allocations == []
        assert plan.route_itineraries == []
        assert plan.vehicle_review_tables == []
        assert [issue.request_id for issue in plan.validation_issues] == [request.id]
        assert [issue.code for issue in plan.validation_issues] == ["transport_ai_request_unallocated"]
        assert plan.validation_issues[0].blocking is True
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("request_kind", "service_date"),
    [
        ("regular", date(2026, 6, 8)),
        ("weekend", date(2026, 6, 7)),
    ],
)
def test_build_transport_agent_plan_from_solver_result_derives_routine_return_leg(tmp_path, request_kind, service_date):
    engine, session_factory = _build_session_factory(
        tmp_path / f"transport_ai_plan_builder_{request_kind}_return.db"
    )
    try:
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name=f"P{request_kind[:3].upper()}")
            created_requests = []
            for index in range(1, 4):
                user = _create_user(
                    session,
                    chave=f"TR{request_kind[0].upper()}{index}",
                    nome=f"{request_kind.title()} Return {index}",
                    projeto=project.name,
                    address=f"{20 + index} Routine Street",
                    zip_code=f"53012{index}",
                )
                created_requests.append(
                    _create_transport_request(
                        session,
                        user_id=user.id,
                        service_date=service_date,
                        request_kind=request_kind,
                    )
                )
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            assert len(planning_input.partitions) == 1
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=[
                    [0, 600, 2400, 2700],
                    [540, 0, 480, 1800],
                    [2100, 300, 0, 720],
                    [2400, 1500, 660, 0],
                ],
            )
            solved_partition = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )
            scheduled_partition = schedule_transport_ai_route_times(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                partition_solve_result=solved_partition,
            )
            route_matrices_result = TransportAgentRouteMatricesResult(
                planning_input_hash=planning_input.planning_input_hash,
                provider="solver-test",
                profile="here/car-fast",
                partitions=[route_matrix_partition],
                issues=[],
                total_matrices=1,
            )

            plan = build_transport_agent_plan_from_solver_result(
                planning_input=planning_input,
                route_matrices_result=route_matrices_result,
                partition_solve_results=[scheduled_partition],
            )

        assert len(plan.vehicle_actions) == 1
        assert plan.validation_issues == []
        assert len(plan.route_itineraries) == 2

        itineraries_by_route_kind = {
            itinerary.route_kind: itinerary
            for itinerary in plan.route_itineraries
        }
        outbound_itinerary = itineraries_by_route_kind["home_to_work"]
        return_itinerary = itineraries_by_route_kind["work_to_home"]
        assert outbound_itinerary.vehicle_ref == return_itinerary.vehicle_ref
        assert return_itinerary.estimated_cost == pytest.approx(0.0)
        assert return_itinerary.projected_arrival_time == "17:10"
        assert return_itinerary.total_duration_seconds == 1500
        assert return_itinerary.total_distance_meters == 15000

        outbound_request_ids = [
            stop.request_id
            for stop in outbound_itinerary.stops
            if stop.request_id is not None
        ]
        return_request_ids = [
            stop.request_id
            for stop in return_itinerary.stops
            if stop.request_id is not None
        ]
        assert outbound_request_ids == [request.id for request in created_requests]
        assert return_request_ids == [request.id for request in reversed(created_requests)]
        assert return_itinerary.stops[0].request_id is None
        assert return_itinerary.stops[0].scheduled_time == "16:45"
        assert [stop.scheduled_time for stop in return_itinerary.stops[1:]] == ["16:56", "17:01", "17:10"]

        allocations_by_route_kind = {
            route_kind: sorted(
                [allocation for allocation in plan.passenger_allocations if allocation.route_kind == route_kind],
                key=lambda allocation: allocation.pickup_order,
            )
            for route_kind in {allocation.route_kind for allocation in plan.passenger_allocations}
        }
        assert len(allocations_by_route_kind["home_to_work"]) == 3
        assert len(allocations_by_route_kind["work_to_home"]) == 3
        assert {allocation.vehicle_ref for allocation in plan.passenger_allocations} == {outbound_itinerary.vehicle_ref}
        assert [allocation.request_id for allocation in allocations_by_route_kind["work_to_home"]] == [
            request.id for request in reversed(created_requests)
        ]
        assert [allocation.scheduled_dropoff_time for allocation in allocations_by_route_kind["work_to_home"]] == [
            "16:56",
            "17:01",
            "17:10",
        ]
        assert [allocation.projected_arrival_time for allocation in allocations_by_route_kind["work_to_home"]] == [
            "16:56",
            "17:01",
            "17:10",
        ]

        assert len(plan.vehicle_review_tables) == 1
        review_table = plan.vehicle_review_tables[0]
        assert [row.request_id for row in review_table.rows] == [request.id for request in created_requests]
        assert [row.work_to_home_dropoff for row in review_table.rows] == ["17:10", "17:01", "16:56"]
        roundtrip = TransportAgentPlan.model_validate_json(plan.model_dump_json())
        assert roundtrip == plan
    finally:
        engine.dispose()


def test_schedule_transport_ai_route_times_keeps_regular_solver_anchored_to_home_to_work_when_run_context_is_work_to_home(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_regular_work_context_return.db")
    try:
        service_date = date(2026, 6, 8)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name="PREGCTX")
            for index in range(1, 3):
                user = _create_user(
                    session,
                    chave=f"RC{index}",
                    nome=f"Regular Context {index}",
                    projeto=project.name,
                    address=f"{30 + index} Context Street",
                    zip_code=f"52022{index}",
                )
                _create_transport_request(
                    session,
                    user_id=user.id,
                    service_date=service_date,
                    request_kind="regular",
                )
            session.commit()

            planning_input = build_transport_agent_planning_input(
                session,
                service_date=service_date,
                route_kind="work_to_home",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                settings_obj=_build_planning_settings(),
            )
            partition = planning_input.partitions[0]
            vehicle_candidates_partition = build_transport_ai_vehicle_candidates(planning_input=planning_input).partitions[0]
            assert {candidate.route_kind for candidate in vehicle_candidates_partition.candidates} == {"home_to_work"}

            route_matrix_partition = _build_solver_route_matrix_partition(
                partition=partition,
                durations_seconds=[
                    [0, 1200, 2400],
                    [540, 0, 900],
                    [1500, 660, 0],
                ],
            )
            solved_partition = solve_transport_ai_partition(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                vehicle_candidates_partition=vehicle_candidates_partition,
            )
            scheduled_partition = schedule_transport_ai_route_times(
                planning_input=planning_input,
                route_matrix_partition=route_matrix_partition,
                partition_solve_result=solved_partition,
            )

        assert scheduled_partition.is_feasible is True
        assert scheduled_partition.issues == []
        assert len(scheduled_partition.routes) == 1
        assert scheduled_partition.routes[0].route_kind == "home_to_work"
        assert scheduled_partition.routes[0].projected_arrival_time == "07:45"
        assert [passenger.scheduled_pickup_time for passenger in scheduled_partition.routes[0].passengers] == [
            "07:10",
            "07:30",
        ]
    finally:
        engine.dispose()


def test_build_transport_proposal_from_agent_plan_resolves_existing_and_new_vehicle_refs(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_proposal_conversion_refs.db")
    try:
        service_date = date(2026, 6, 29)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name="TPROP1")
            existing_user = _create_user(session, chave="TPR01", nome="Proposal Existing", projeto=project.name)
            new_user = _create_user(session, chave="TPR02", nome="Proposal New", projeto=project.name)
            existing_request = _create_transport_request(
                session,
                user_id=existing_user.id,
                service_date=service_date,
                request_kind="extra",
            )
            new_request = _create_transport_request(
                session,
                user_id=new_user.id,
                service_date=service_date,
                request_kind="extra",
            )
            existing_vehicle = _create_extra_vehicle_candidate(
                session,
                placa="SBA5101A",
                service_date=service_date,
            )
            session.commit()

            plan = _build_transport_agent_plan_for_proposal(
                service_date=service_date,
                passenger_allocations=[
                    _build_transport_agent_passenger_allocation(
                        request=existing_request,
                        user=existing_user,
                        service_date=service_date,
                        vehicle_ref=f"existing:{existing_vehicle.id}",
                        project_name=project.name,
                    ),
                    _build_transport_agent_passenger_allocation(
                        request=new_request,
                        user=new_user,
                        service_date=service_date,
                        vehicle_ref="new:solver-created-vehicle",
                        project_name=project.name,
                        pickup_order=1,
                    ),
                ],
            )

            decisions, issues = build_transport_proposal_from_agent_plan(
                session,
                plan=plan,
                vehicle_id_by_ref={
                    f"existing:{existing_vehicle.id}": existing_vehicle.id,
                    "new:solver-created-vehicle": 9991,
                },
            )

        assert issues == []
        assert [
            (decision.request_id, decision.suggested_status, decision.vehicle_id, decision.boarding_time)
            for decision in decisions
        ] == [
            (existing_request.id, "confirmed", existing_vehicle.id, "07:20"),
            (new_request.id, "confirmed", 9991, "07:20"),
        ]
    finally:
        engine.dispose()


def test_build_transport_proposal_from_agent_plan_marks_blocked_allocations_pending(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_proposal_conversion_pending.db")
    try:
        service_date = date(2026, 6, 30)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name="TPROP2")
            user = _create_user(session, chave="TPR03", nome="Proposal Pending", projeto=project.name)
            request = _create_transport_request(
                session,
                user_id=user.id,
                service_date=service_date,
                request_kind="extra",
            )
            vehicle = _create_extra_vehicle_candidate(
                session,
                placa="SBA5102A",
                service_date=service_date,
            )
            session.commit()

            plan = _build_transport_agent_plan_for_proposal(
                service_date=service_date,
                passenger_allocations=[
                    _build_transport_agent_passenger_allocation(
                        request=request,
                        user=user,
                        service_date=service_date,
                        vehicle_ref=f"existing:{vehicle.id}",
                        project_name=project.name,
                    )
                ],
                validation_issues=[
                    {
                        "code": "transport_ai_request_requires_review",
                        "message": "Request needs manual review before confirmation.",
                        "blocking": True,
                        "request_id": request.id,
                    }
                ],
            )

            decisions, issues = build_transport_proposal_from_agent_plan(
                session,
                plan=plan,
                vehicle_id_by_ref={f"existing:{vehicle.id}": vehicle.id},
            )

        assert issues == []
        assert len(decisions) == 1
        assert decisions[0].request_id == request.id
        assert decisions[0].suggested_status == "pending"
        assert decisions[0].vehicle_id is None
        assert decisions[0].boarding_time is None
        assert decisions[0].response_message == "Request needs manual review before confirmation."
        assert "Keep request" in decisions[0].rationale
    finally:
        engine.dispose()


def test_build_transport_proposal_from_agent_plan_adds_pending_issue_only_requests_to_summary(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_proposal_conversion_summary.db")
    try:
        service_date = date(2026, 7, 1)
        with session_factory() as session:
            _configure_transport_settings(session)
            project = _create_project(session, name="TPROP3")
            confirmed_user = _create_user(session, chave="TPR04", nome="Proposal Confirmed", projeto=project.name)
            pending_user = _create_user(session, chave="TPR05", nome="Proposal Issue Only", projeto=project.name)
            confirmed_request = _create_transport_request(
                session,
                user_id=confirmed_user.id,
                service_date=service_date,
                request_kind="extra",
            )
            pending_request = _create_transport_request(
                session,
                user_id=pending_user.id,
                service_date=service_date,
                request_kind="extra",
            )
            vehicle = _create_extra_vehicle_candidate(
                session,
                placa="SBA5103A",
                service_date=service_date,
            )
            session.commit()

            plan = _build_transport_agent_plan_for_proposal(
                service_date=service_date,
                passenger_allocations=[
                    _build_transport_agent_passenger_allocation(
                        request=confirmed_request,
                        user=confirmed_user,
                        service_date=service_date,
                        vehicle_ref=f"existing:{vehicle.id}",
                        project_name=project.name,
                    )
                ],
                validation_issues=[
                    {
                        "code": "transport_ai_request_unallocated",
                        "message": "Request is not present in the final consolidated allocations.",
                        "blocking": True,
                        "request_id": pending_request.id,
                    }
                ],
            )

            decisions, issues = build_transport_proposal_from_agent_plan(
                session,
                plan=plan,
                vehicle_id_by_ref={f"existing:{vehicle.id}": vehicle.id},
            )
            snapshot = build_transport_operational_snapshot(
                session,
                service_date=service_date,
                route_kind="home_to_work",
            )
            proposal = build_transport_operational_proposal(
                snapshot=snapshot,
                origin="agent",
                decisions=decisions,
            )

        assert issues == []
        assert [(decision.request_id, decision.suggested_status) for decision in decisions] == [
            (confirmed_request.id, "confirmed"),
            (pending_request.id, "pending"),
        ]
        assert proposal.origin == "agent"
        assert proposal.summary.total_decisions == 2
        assert proposal.summary.confirmed_decisions == 1
        assert proposal.summary.pending_decisions == 1
        assert proposal.summary.rejected_decisions == 0
    finally:
        engine.dispose()