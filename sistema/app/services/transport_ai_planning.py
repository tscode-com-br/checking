from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import itertools
import json
import math
from datetime import date, datetime
from numbers import Real
from typing import Any

from sqlalchemy.orm import Session

from ..core.config import Settings, settings
from ..models import TransportRequest
from ..schemas import (
    ProjectRow,
    TransportAgentChangeSummary,
    TransportAgentChangeSummaryByVehicleType,
    TransportAgentCostSummary,
    TransportAgentPassengerAllocation,
    TransportAgentPlan,
    TransportAgentPlanningInput,
    TransportAgentPlanningLimits,
    TransportAgentPlanningPartition,
    TransportAgentPlanningRequest,
    TransportAgentPartitionSolveResult,
    TransportAgentRouteMatricesResult,
    TransportAgentRouteStop,
    TransportAgentSolvedRoute,
    TransportAgentSolvedRoutePassenger,
    TransportAgentVehicleAction,
    TransportAgentVehicleCandidate,
    TransportAgentVehicleCandidatePenaltyConfig,
    TransportAgentVehicleCandidatesPartition,
    TransportAgentVehicleCandidatesResult,
    TransportAgentVehicleItinerary,
    TransportAgentRouteMatrixPartition,
    TransportAgentResolvedRoutePoint,
    TransportAgentResolvedRoutePointsPartition,
    TransportAgentResolvedRoutePointsResult,
    TransportAgentPlanningSettings,
    TransportAgentPlanningVehicle,
    TransportAgentPlanningVehicleTypeConfig,
    TransportAIPreflightIssue,
    TransportOperationalSnapshot,
    TransportProposalDecision,
    TransportProposalValidationIssue,
    TransportRequestRow,
)
from .location_settings import get_transport_settings_payload
from .transport_ai_runtime import _build_transport_ai_preflight_issue
from .transport_proposals import build_transport_operational_snapshot
from .transport_route_cache import (
    get_cached_transport_ai_route_matrix,
    get_cached_transport_ai_route_point,
    upsert_transport_ai_route_matrix,
    upsert_transport_ai_route_point,
)
from .transport_route_provider import (
    GeocodeRequest,
    MatrixRequest,
    MatrixResult,
    TransportRouteCoordinate,
    TransportRouteProvider,
    TransportRouteProviderNoRouteError,
    TransportRouteProviderNoResultError,
    build_transport_route_provider,
)

_SUPPORTED_ROUTE_KINDS = {"home_to_work", "work_to_home"}
_REQUEST_SCOPE_ORDER = ("regular", "weekend", "extra")
_PRICE_SETTING_BY_VEHICLE_TYPE = {
    "carro": "default_car_price",
    "minivan": "default_minivan_price",
    "van": "default_van_price",
    "onibus": "default_bus_price",
}
_SEAT_SETTING_BY_VEHICLE_TYPE = {
    "carro": "default_car_seats",
    "minivan": "default_minivan_seats",
    "van": "default_van_seats",
    "onibus": "default_bus_seats",
}
_SUPPORTED_VEHICLE_TYPES = tuple(_PRICE_SETTING_BY_VEHICLE_TYPE)
_TRANSPORT_AI_ROUTE_POINT_MIN_CONFIDENCE = 0.85
_TRANSPORT_AI_MAX_EXACT_SOLVER_REQUESTS = 8
_TRANSPORT_AI_MAX_EXACT_ROUTE_ORDER_REQUESTS = 8


@dataclass(frozen=True, slots=True)
class _TransportAgentGeocodeLookup:
    normalized_query: str
    formatted_address: str
    longitude: float
    latitude: float
    provider: str
    provider_place_id: str | None
    confidence: float | None
    country_code: str | None
    country_name: str | None
    raw_response_json: Any
    cached: bool


@dataclass(frozen=True, slots=True)
class _TransportAISolverVehicleUnit:
    unit_key: str
    candidate: TransportAgentVehicleCandidate
    unit_index: int
    client_vehicle_key: str | None


@dataclass(frozen=True, slots=True)
class _TransportAISolverSubsetRoute:
    request_ids: tuple[int, ...]
    pickup_order_request_ids: tuple[int, ...]
    total_duration_seconds: int
    total_distance_meters: int


@dataclass(frozen=True, slots=True)
class _TransportAISolverRouteOption:
    option_key: str
    vehicle_unit_key: str
    vehicle_candidate_key: str
    candidate_type: str
    recommended_action_type: str
    client_vehicle_key: str | None
    vehicle_id: int | None
    schedule_id: int | None
    service_scope: str
    route_kind: str
    vehicle_type: str
    plate: str | None
    capacity: int
    request_ids: tuple[int, ...]
    pickup_order_request_ids: tuple[int, ...]
    estimated_cost: float
    cost_cents: int
    change_penalty: int
    total_duration_seconds: int
    total_distance_meters: int


def _dump_transport_ai_planning_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _normalize_project_name(project_name: str | None) -> str:
    return str(project_name or "").strip().upper()


def _normalize_country_name(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _has_positive_number(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and value > 0


def _has_non_negative_number(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and value >= 0


def _iter_pending_requests_by_scope(
    snapshot: TransportOperationalSnapshot,
    *,
    service_date: date,
) -> dict[str, list[TransportRequestRow]]:
    requests_by_scope: dict[str, list[TransportRequestRow]] = {}

    for request_scope in _REQUEST_SCOPE_ORDER:
        request_rows = sorted(
            getattr(snapshot, f"{request_scope}_requests"),
            key=lambda row: (row.id, row.user_id, row.requested_time),
        )
        pending_rows = [
            row
            for row in request_rows
            if row.assignment_status == "pending" and row.service_date == service_date
        ]
        if pending_rows:
            requests_by_scope[request_scope] = pending_rows

    return requests_by_scope


def _build_project_issue(
    *,
    code: str,
    message: str,
    blocking: bool = True,
) -> TransportAIPreflightIssue:
    return _build_transport_ai_preflight_issue(
        code=code,
        message=message,
        setting_name="transport_projects",
        blocking=blocking,
    )


def _build_transport_ai_route_point_issue(
    *,
    code: str,
    message: str,
    blocking: bool = True,
) -> TransportAIPreflightIssue:
    return _build_transport_ai_preflight_issue(
        code=code,
        message=message,
        setting_name="transport_route_points",
        blocking=blocking,
    )


def _build_transport_ai_route_matrix_issue(
    *,
    code: str,
    message: str,
    blocking: bool = True,
) -> TransportAIPreflightIssue:
    return _build_transport_ai_preflight_issue(
        code=code,
        message=message,
        setting_name="transport_route_matrices",
        blocking=blocking,
    )


def _build_transport_ai_solver_issue(
    *,
    code: str,
    message: str,
    blocking: bool = True,
) -> TransportAIPreflightIssue:
    return _build_transport_ai_preflight_issue(
        code=code,
        message=message,
        setting_name="transport_ai_solver",
        blocking=blocking,
    )


def _build_transport_ai_route_schedule_issue(
    *,
    code: str,
    message: str,
    blocking: bool = True,
) -> TransportAIPreflightIssue:
    return _build_transport_ai_preflight_issue(
        code=code,
        message=message,
        setting_name="transport_ai_route_schedule",
        blocking=blocking,
    )


def _build_transport_agent_geocode_lookup_from_cache(route_point_row) -> _TransportAgentGeocodeLookup:
    return _TransportAgentGeocodeLookup(
        normalized_query=route_point_row.normalized_query,
        formatted_address=route_point_row.address,
        longitude=float(route_point_row.longitude),
        latitude=float(route_point_row.latitude),
        provider=str(route_point_row.provider),
        provider_place_id=route_point_row.provider_place_id,
        confidence=None if route_point_row.confidence is None else float(route_point_row.confidence),
        country_code=route_point_row.country_code,
        country_name=route_point_row.country_name,
        raw_response_json=None,
        cached=True,
    )


def _build_transport_agent_geocode_lookup_from_provider_result(geocode_result) -> _TransportAgentGeocodeLookup:
    return _TransportAgentGeocodeLookup(
        normalized_query=geocode_result.query,
        formatted_address=geocode_result.formatted_address,
        longitude=float(geocode_result.longitude),
        latitude=float(geocode_result.latitude),
        provider=geocode_result.provider,
        provider_place_id=geocode_result.provider_place_id,
        confidence=geocode_result.confidence,
        country_code=geocode_result.country_code,
        country_name=geocode_result.country_name,
        raw_response_json=geocode_result.raw_response_json,
        cached=False,
    )


def _has_transport_ai_route_point_country_mismatch(
    *,
    expected_country_code: str,
    expected_country_name: str,
    lookup: _TransportAgentGeocodeLookup,
) -> bool:
    resolved_country_code = str(lookup.country_code or "").strip().upper()
    if resolved_country_code and resolved_country_code != expected_country_code:
        return True

    resolved_country_name = _normalize_country_name(lookup.country_name)
    return bool(resolved_country_name and resolved_country_name != _normalize_country_name(expected_country_name))


def _build_transport_agent_resolved_route_point(
    *,
    point_type: str,
    partition_key: str,
    source_id: int,
    request_id: int | None,
    project_name: str,
    country_code: str,
    country_name: str,
    label: str,
    address: str,
    zip_code: str,
    lookup: _TransportAgentGeocodeLookup,
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
        normalized_query=lookup.normalized_query,
        formatted_address=lookup.formatted_address,
        longitude=lookup.longitude,
        latitude=lookup.latitude,
        provider=lookup.provider,
        provider_place_id=lookup.provider_place_id,
        confidence=lookup.confidence,
        cached=lookup.cached,
    )


def _build_transport_route_coordinate_from_resolved_point(
    point: TransportAgentResolvedRoutePoint,
) -> TransportRouteCoordinate:
    return TransportRouteCoordinate(
        longitude=point.longitude,
        latitude=point.latitude,
        label=point.label,
    )


def _normalize_transport_ai_matrix_value(value: float | int | None) -> int | None:
    if value is None:
        return None
    return int(round(float(value)))


def _normalize_transport_ai_matrix(
    matrix: list[list[float | int | None]],
) -> list[list[int | None]]:
    return [
        [_normalize_transport_ai_matrix_value(value) for value in row]
        for row in matrix
    ]


def _parse_transport_ai_hhmm_to_seconds(value: str) -> int:
    hour_text, minute_text = str(value or "").strip().split(":", 1)
    return (int(hour_text) * 60 + int(minute_text)) * 60


def _round_transport_ai_duration_seconds_to_minute_ceiling(duration_seconds: int) -> int:
    if duration_seconds <= 0:
        return 0
    return int(math.ceil(duration_seconds / 60.0) * 60)


def _format_transport_ai_seconds_to_hhmm(total_seconds: int) -> str:
    if total_seconds < 0:
        raise ValueError("Transport AI route schedule times must not be negative")
    total_minutes = total_seconds // 60
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def _build_transport_ai_solver_vehicle_units(
    *,
    candidates: list[TransportAgentVehicleCandidate],
    request_count: int,
) -> list[_TransportAISolverVehicleUnit]:
    units: list[_TransportAISolverVehicleUnit] = []
    max_virtual_units = max(1, request_count)

    for candidate in sorted(candidates, key=lambda row: (row.candidate_key, row.vehicle_id or 0, row.vehicle_type)):
        if candidate.candidate_type == "existing":
            units.append(
                _TransportAISolverVehicleUnit(
                    unit_key=candidate.candidate_key,
                    candidate=candidate,
                    unit_index=1,
                    client_vehicle_key=None,
                )
            )
            continue

        for unit_index in range(1, max_virtual_units + 1):
            client_vehicle_key = candidate.client_vehicle_key
            if client_vehicle_key and unit_index > 1:
                client_vehicle_key = f"{client_vehicle_key}-{unit_index}"
            units.append(
                _TransportAISolverVehicleUnit(
                    unit_key=f"{candidate.candidate_key}:unit:{unit_index}",
                    candidate=candidate,
                    unit_index=unit_index,
                    client_vehicle_key=client_vehicle_key,
                )
            )

    return units


def _build_transport_ai_request_point_index(
    route_matrix_partition: TransportAgentRouteMatrixPartition,
) -> dict[int, int]:
    request_point_index: dict[int, int] = {}
    for point_index, point in enumerate(route_matrix_partition.points):
        if point.point_type != "passenger_origin" or point.request_id is None:
            continue
        request_point_index[point.request_id] = point_index
    return request_point_index


def _evaluate_transport_ai_pickup_order(
    *,
    pickup_order_request_ids: tuple[int, ...],
    route_matrix_partition: TransportAgentRouteMatrixPartition,
    request_point_index_by_request_id: dict[int, int],
) -> tuple[int, int] | None:
    if not pickup_order_request_ids:
        return 0, 0

    indices = [request_point_index_by_request_id[request_id] for request_id in pickup_order_request_ids]
    indices.append(route_matrix_partition.destination_index)

    total_duration_seconds = 0
    total_distance_meters = 0
    for from_index, to_index in zip(indices, indices[1:]):
        duration_seconds = route_matrix_partition.durations_seconds[from_index][to_index]
        distance_meters = route_matrix_partition.distances_meters[from_index][to_index]
        if duration_seconds is None or distance_meters is None:
            return None
        total_duration_seconds += duration_seconds
        total_distance_meters += distance_meters

    return total_duration_seconds, total_distance_meters


def _build_transport_ai_greedy_pickup_order(
    *,
    subset_request_ids: tuple[int, ...],
    route_matrix_partition: TransportAgentRouteMatrixPartition,
    request_point_index_by_request_id: dict[int, int],
) -> tuple[int, ...] | None:
    remaining_request_ids = list(sorted(subset_request_ids))
    if not remaining_request_ids:
        return tuple()

    current_index = route_matrix_partition.destination_index
    reversed_order: list[int] = []

    while remaining_request_ids:
        next_request_id = min(
            remaining_request_ids,
            key=lambda request_id: (
                route_matrix_partition.durations_seconds[request_point_index_by_request_id[request_id]][current_index]
                if route_matrix_partition.durations_seconds[request_point_index_by_request_id[request_id]][current_index] is not None
                else float("inf"),
                route_matrix_partition.distances_meters[request_point_index_by_request_id[request_id]][current_index]
                if route_matrix_partition.distances_meters[request_point_index_by_request_id[request_id]][current_index] is not None
                else float("inf"),
                request_id,
            ),
        )
        leg_duration_seconds = route_matrix_partition.durations_seconds[
            request_point_index_by_request_id[next_request_id]
        ][current_index]
        leg_distance_meters = route_matrix_partition.distances_meters[
            request_point_index_by_request_id[next_request_id]
        ][current_index]
        if leg_duration_seconds is None or leg_distance_meters is None:
            return None

        reversed_order.append(next_request_id)
        current_index = request_point_index_by_request_id[next_request_id]
        remaining_request_ids.remove(next_request_id)

    return tuple(reversed(reversed_order))


def _build_transport_ai_best_subset_route(
    *,
    subset_request_ids: tuple[int, ...],
    route_matrix_partition: TransportAgentRouteMatrixPartition,
    request_point_index_by_request_id: dict[int, int],
    available_window_seconds: int,
) -> _TransportAISolverSubsetRoute | None:
    normalized_request_ids = tuple(sorted(subset_request_ids))
    if not normalized_request_ids:
        return None

    if len(normalized_request_ids) <= _TRANSPORT_AI_MAX_EXACT_ROUTE_ORDER_REQUESTS:
        candidate_orders = itertools.permutations(normalized_request_ids)
    else:
        greedy_order = _build_transport_ai_greedy_pickup_order(
            subset_request_ids=normalized_request_ids,
            route_matrix_partition=route_matrix_partition,
            request_point_index_by_request_id=request_point_index_by_request_id,
        )
        if greedy_order is None:
            return None
        candidate_orders = [greedy_order]

    best_route: _TransportAISolverSubsetRoute | None = None
    best_sort_key: tuple[int, int, tuple[int, ...]] | None = None

    for pickup_order_request_ids in candidate_orders:
        route_metrics = _evaluate_transport_ai_pickup_order(
            pickup_order_request_ids=tuple(pickup_order_request_ids),
            route_matrix_partition=route_matrix_partition,
            request_point_index_by_request_id=request_point_index_by_request_id,
        )
        if route_metrics is None:
            continue

        total_duration_seconds, total_distance_meters = route_metrics
        if total_duration_seconds > available_window_seconds:
            continue

        sort_key = (total_duration_seconds, total_distance_meters, tuple(pickup_order_request_ids))
        if best_sort_key is not None and sort_key >= best_sort_key:
            continue

        best_sort_key = sort_key
        best_route = _TransportAISolverSubsetRoute(
            request_ids=normalized_request_ids,
            pickup_order_request_ids=tuple(pickup_order_request_ids),
            total_duration_seconds=total_duration_seconds,
            total_distance_meters=total_distance_meters,
        )

    return best_route


def _build_transport_ai_exact_subset_routes(
    *,
    request_ids: tuple[int, ...],
    route_matrix_partition: TransportAgentRouteMatrixPartition,
    request_point_index_by_request_id: dict[int, int],
    available_window_seconds: int,
    max_route_passengers: int,
) -> dict[tuple[int, ...], _TransportAISolverSubsetRoute]:
    subset_routes: dict[tuple[int, ...], _TransportAISolverSubsetRoute] = {}
    effective_max_route_passengers = min(max_route_passengers, len(request_ids))

    for subset_size in range(1, effective_max_route_passengers + 1):
        for subset_request_ids in itertools.combinations(request_ids, subset_size):
            subset_route = _build_transport_ai_best_subset_route(
                subset_request_ids=subset_request_ids,
                route_matrix_partition=route_matrix_partition,
                request_point_index_by_request_id=request_point_index_by_request_id,
                available_window_seconds=available_window_seconds,
            )
            if subset_route is not None:
                subset_routes[subset_request_ids] = subset_route

    return subset_routes


def _build_transport_ai_route_options_from_subset_routes(
    *,
    vehicle_units: list[_TransportAISolverVehicleUnit],
    subset_routes: dict[tuple[int, ...], _TransportAISolverSubsetRoute],
) -> list[_TransportAISolverRouteOption]:
    route_options: list[_TransportAISolverRouteOption] = []

    for vehicle_unit in vehicle_units:
        candidate = vehicle_unit.candidate
        for subset_request_ids, subset_route in sorted(
            subset_routes.items(),
            key=lambda item: (len(item[0]), item[0]),
        ):
            if len(subset_request_ids) > candidate.capacity:
                continue

            route_options.append(
                _TransportAISolverRouteOption(
                    option_key=f"{vehicle_unit.unit_key}|{'-'.join(str(request_id) for request_id in subset_request_ids)}",
                    vehicle_unit_key=vehicle_unit.unit_key,
                    vehicle_candidate_key=candidate.candidate_key,
                    candidate_type=candidate.candidate_type,
                    recommended_action_type=candidate.recommended_action_type,
                    client_vehicle_key=vehicle_unit.client_vehicle_key,
                    vehicle_id=candidate.vehicle_id,
                    schedule_id=candidate.schedule_id,
                    service_scope=candidate.service_scope,
                    route_kind=candidate.route_kind,
                    vehicle_type=candidate.vehicle_type,
                    plate=candidate.plate,
                    capacity=candidate.capacity,
                    request_ids=subset_route.request_ids,
                    pickup_order_request_ids=subset_route.pickup_order_request_ids,
                    estimated_cost=candidate.estimated_cost,
                    cost_cents=int(round(candidate.estimated_cost * 100)),
                    change_penalty=candidate.change_penalty,
                    total_duration_seconds=subset_route.total_duration_seconds,
                    total_distance_meters=subset_route.total_distance_meters,
                )
            )

    return route_options


def _solve_transport_ai_partition_with_ortools(
    *,
    request_ids: tuple[int, ...],
    route_options: list[_TransportAISolverRouteOption],
    max_runtime_seconds: int,
) -> tuple[str, list[_TransportAISolverRouteOption] | None]:
    try:
        from ortools.sat.python import cp_model
    except Exception:
        return "heuristic", None

    if not route_options:
        return "heuristic", None

    route_count_upper_bound = max(1, len(request_ids))
    max_cost_cents = max(option.cost_cents for option in route_options)
    max_duration_seconds = max(option.total_duration_seconds for option in route_options)
    max_distance_meters = max(option.total_distance_meters for option in route_options)
    max_change_penalty = max(option.change_penalty for option in route_options)

    penalty_upper_bound = route_count_upper_bound * max_change_penalty
    distance_upper_bound = route_count_upper_bound * max_distance_meters
    duration_upper_bound = route_count_upper_bound * max_duration_seconds
    distance_weight = penalty_upper_bound + 1
    duration_weight = distance_upper_bound * distance_weight + penalty_upper_bound + 1
    route_count_weight = duration_upper_bound * duration_weight + distance_upper_bound * distance_weight + penalty_upper_bound + 1
    cost_weight = route_count_upper_bound * route_count_weight + duration_upper_bound * duration_weight + distance_upper_bound * distance_weight + penalty_upper_bound + 1

    model = cp_model.CpModel()
    route_variables = [
        model.NewBoolVar(f"transport_ai_route_option_{index}")
        for index, _ in enumerate(route_options)
    ]

    for request_id in request_ids:
        covering_variables = [
            route_variable
            for route_variable, route_option in zip(route_variables, route_options)
            if request_id in route_option.request_ids
        ]
        if not covering_variables:
            return "heuristic", None
        model.Add(sum(covering_variables) == 1)

    route_variables_by_unit_key: dict[str, list[Any]] = defaultdict(list)
    for route_variable, route_option in zip(route_variables, route_options):
        route_variables_by_unit_key[route_option.vehicle_unit_key].append(route_variable)
    for unit_route_variables in route_variables_by_unit_key.values():
        model.Add(sum(unit_route_variables) <= 1)

    model.Minimize(
        sum(
            route_variable
            * (
                route_option.cost_cents * cost_weight
                + route_count_weight
                + route_option.total_duration_seconds * duration_weight
                + route_option.total_distance_meters * distance_weight
                + route_option.change_penalty
            )
            for route_variable, route_option in zip(route_variables, route_options)
        )
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(max(1, min(max_runtime_seconds, 3)))
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return "heuristic", None

    selected_options = [
        route_option
        for route_variable, route_option in zip(route_variables, route_options)
        if solver.Value(route_variable)
    ]
    return "ortools", selected_options


def _build_transport_ai_greedy_route_option(
    *,
    seed_request_id: int,
    remaining_request_ids: set[int],
    vehicle_unit: _TransportAISolverVehicleUnit,
    route_matrix_partition: TransportAgentRouteMatrixPartition,
    request_point_index_by_request_id: dict[int, int],
    available_window_seconds: int,
) -> _TransportAISolverRouteOption | None:
    selected_request_ids = [seed_request_id]
    best_subset_route = _build_transport_ai_best_subset_route(
        subset_request_ids=(seed_request_id,),
        route_matrix_partition=route_matrix_partition,
        request_point_index_by_request_id=request_point_index_by_request_id,
        available_window_seconds=available_window_seconds,
    )
    if best_subset_route is None:
        return None

    while len(selected_request_ids) < vehicle_unit.candidate.capacity:
        best_extension_sort_key: tuple[int, int, tuple[int, ...]] | None = None
        best_extension_route: _TransportAISolverSubsetRoute | None = None

        for candidate_request_id in sorted(remaining_request_ids - set(selected_request_ids)):
            candidate_subset_route = _build_transport_ai_best_subset_route(
                subset_request_ids=tuple(sorted([*selected_request_ids, candidate_request_id])),
                route_matrix_partition=route_matrix_partition,
                request_point_index_by_request_id=request_point_index_by_request_id,
                available_window_seconds=available_window_seconds,
            )
            if candidate_subset_route is None:
                continue

            extension_sort_key = (
                candidate_subset_route.total_duration_seconds,
                candidate_subset_route.total_distance_meters,
                candidate_subset_route.pickup_order_request_ids,
            )
            if best_extension_sort_key is not None and extension_sort_key >= best_extension_sort_key:
                continue

            best_extension_sort_key = extension_sort_key
            best_extension_route = candidate_subset_route

        if best_extension_route is None:
            break

        selected_request_ids = list(best_extension_route.request_ids)
        best_subset_route = best_extension_route

    candidate = vehicle_unit.candidate
    return _TransportAISolverRouteOption(
        option_key=f"{vehicle_unit.unit_key}|{'-'.join(str(request_id) for request_id in best_subset_route.request_ids)}",
        vehicle_unit_key=vehicle_unit.unit_key,
        vehicle_candidate_key=candidate.candidate_key,
        candidate_type=candidate.candidate_type,
        recommended_action_type=candidate.recommended_action_type,
        client_vehicle_key=vehicle_unit.client_vehicle_key,
        vehicle_id=candidate.vehicle_id,
        schedule_id=candidate.schedule_id,
        service_scope=candidate.service_scope,
        route_kind=candidate.route_kind,
        vehicle_type=candidate.vehicle_type,
        plate=candidate.plate,
        capacity=candidate.capacity,
        request_ids=best_subset_route.request_ids,
        pickup_order_request_ids=best_subset_route.pickup_order_request_ids,
        estimated_cost=candidate.estimated_cost,
        cost_cents=int(round(candidate.estimated_cost * 100)),
        change_penalty=candidate.change_penalty,
        total_duration_seconds=best_subset_route.total_duration_seconds,
        total_distance_meters=best_subset_route.total_distance_meters,
    )


def _solve_transport_ai_partition_with_heuristic(
    *,
    request_ids: tuple[int, ...],
    vehicle_units: list[_TransportAISolverVehicleUnit],
    route_matrix_partition: TransportAgentRouteMatrixPartition,
    request_point_index_by_request_id: dict[int, int],
    available_window_seconds: int,
) -> list[_TransportAISolverRouteOption] | None:
    remaining_request_ids = set(request_ids)
    unused_vehicle_units = list(vehicle_units)
    selected_options: list[_TransportAISolverRouteOption] = []

    while remaining_request_ids:
        next_seed_request_id = max(
            remaining_request_ids,
            key=lambda request_id: (
                route_matrix_partition.durations_seconds[
                    request_point_index_by_request_id[request_id]
                ][route_matrix_partition.destination_index]
                if route_matrix_partition.durations_seconds[
                    request_point_index_by_request_id[request_id]
                ][route_matrix_partition.destination_index] is not None
                else -1,
                request_id,
            ),
        )

        best_option: _TransportAISolverRouteOption | None = None
        best_option_sort_key: tuple[int, float, int, int, int, str] | None = None
        for vehicle_unit in unused_vehicle_units:
            route_option = _build_transport_ai_greedy_route_option(
                seed_request_id=next_seed_request_id,
                remaining_request_ids=remaining_request_ids,
                vehicle_unit=vehicle_unit,
                route_matrix_partition=route_matrix_partition,
                request_point_index_by_request_id=request_point_index_by_request_id,
                available_window_seconds=available_window_seconds,
            )
            if route_option is None:
                continue

            option_sort_key = (
                -len(route_option.request_ids),
                route_option.estimated_cost,
                route_option.total_duration_seconds,
                route_option.total_distance_meters,
                route_option.change_penalty,
                route_option.option_key,
            )
            if best_option_sort_key is not None and option_sort_key >= best_option_sort_key:
                continue

            best_option_sort_key = option_sort_key
            best_option = route_option

        if best_option is None:
            return None

        selected_options.append(best_option)
        remaining_request_ids.difference_update(best_option.request_ids)
        unused_vehicle_units = [
            vehicle_unit
            for vehicle_unit in unused_vehicle_units
            if vehicle_unit.unit_key != best_option.vehicle_unit_key
        ]

    return selected_options


def _build_transport_ai_solved_routes(
    *,
    partition: TransportAgentPlanningPartition,
    selected_options: list[_TransportAISolverRouteOption],
) -> list[TransportAgentSolvedRoute]:
    request_by_id = {request.request_id: request for request in partition.requests}
    solved_routes: list[TransportAgentSolvedRoute] = []

    for route_index, selected_option in enumerate(
        sorted(
            selected_options,
            key=lambda option: (option.pickup_order_request_ids, option.vehicle_type, option.vehicle_unit_key),
        ),
        start=1,
    ):
        passengers = []
        for pickup_order, request_id in enumerate(selected_option.pickup_order_request_ids):
            planning_request = request_by_id[request_id]
            passengers.append(
                TransportAgentSolvedRoutePassenger(
                    request_id=planning_request.request_id,
                    user_id=planning_request.user_id,
                    chave=planning_request.chave,
                    nome=planning_request.nome,
                    pickup_order=pickup_order,
                )
            )

        solved_routes.append(
            TransportAgentSolvedRoute(
                route_key=f"{partition.partition_key}:route:{route_index}",
                partition_key=partition.partition_key,
                vehicle_candidate_key=selected_option.vehicle_candidate_key,
                vehicle_unit_key=selected_option.vehicle_unit_key,
                candidate_type=selected_option.candidate_type,
                recommended_action_type=selected_option.recommended_action_type,
                client_vehicle_key=selected_option.client_vehicle_key,
                vehicle_id=selected_option.vehicle_id,
                schedule_id=selected_option.schedule_id,
                service_scope=selected_option.service_scope,
                route_kind=selected_option.route_kind,
                vehicle_type=selected_option.vehicle_type,
                plate=selected_option.plate,
                capacity=selected_option.capacity,
                request_ids=list(selected_option.request_ids),
                pickup_order_request_ids=list(selected_option.pickup_order_request_ids),
                passengers=passengers,
                estimated_cost=selected_option.estimated_cost,
                change_penalty=selected_option.change_penalty,
                total_duration_seconds=selected_option.total_duration_seconds,
                total_distance_meters=selected_option.total_distance_meters,
            )
        )

    return solved_routes


def _build_transport_ai_partition_solve_result(
    *,
    planning_input: TransportAgentPlanningInput,
    partition: TransportAgentPlanningPartition,
    algorithm_used: str,
    selected_options: list[_TransportAISolverRouteOption],
    issues: list[TransportAIPreflightIssue],
    unallocated_request_ids: list[int],
) -> TransportAgentPartitionSolveResult:
    solved_routes = _build_transport_ai_solved_routes(
        partition=partition,
        selected_options=selected_options,
    )
    return TransportAgentPartitionSolveResult(
        planning_input_hash=planning_input.planning_input_hash,
        partition_key=partition.partition_key,
        request_kind=partition.request_kind,
        project_name=partition.project_name,
        country_code=partition.country_code,
        country_name=partition.country_name,
        algorithm_used=algorithm_used,
        routes=solved_routes,
        unallocated_request_ids=sorted(unallocated_request_ids),
        issues=issues,
        total_estimated_cost=sum(route.estimated_cost for route in solved_routes),
        total_change_penalty=sum(route.change_penalty for route in solved_routes),
        total_duration_seconds=sum(route.total_duration_seconds for route in solved_routes),
        total_distance_meters=sum(route.total_distance_meters for route in solved_routes),
        total_vehicles_used=len(solved_routes),
        is_feasible=not unallocated_request_ids and not any(issue.blocking for issue in issues),
    )


def _build_unroutable_transport_ai_matrix(point_count: int) -> list[list[int | None]]:
    return [
        [0 if row_index == column_index else None for column_index in range(point_count)]
        for row_index in range(point_count)
    ]


def _build_transport_ai_matrix_result_from_cache(
    *,
    cached_route_matrix,
    points: list[TransportAgentResolvedRoutePoint],
) -> MatrixResult:
    coordinates = [
        _build_transport_route_coordinate_from_resolved_point(point)
        for point in points
    ]
    return MatrixResult(
        provider=str(cached_route_matrix.provider),
        profile=str(cached_route_matrix.profile),
        sources=coordinates,
        destinations=coordinates,
        durations_seconds=json.loads(cached_route_matrix.durations_json or "[]"),
        distances_meters=json.loads(cached_route_matrix.distances_json or "[]"),
        depart_at=cached_route_matrix.depart_at,
    )


def _collect_transport_ai_route_matrix_pair_issues(
    *,
    partition_key: str,
    points: list[TransportAgentResolvedRoutePoint],
    durations_seconds: list[list[int | None]],
    distances_meters: list[list[int | None]],
) -> list[TransportAIPreflightIssue]:
    issues: list[TransportAIPreflightIssue] = []
    for row_index, source_point in enumerate(points):
        for column_index, destination_point in enumerate(points):
            if row_index == column_index:
                continue

            duration_seconds = durations_seconds[row_index][column_index]
            distance_meters = distances_meters[row_index][column_index]
            if duration_seconds is not None and distance_meters is not None:
                continue

            issues.append(
                _build_transport_ai_route_matrix_issue(
                    code="route_matrix_pair_no_route",
                    message=(
                        f"Partition '{partition_key}' has no route from '{source_point.label}' to "
                        f"'{destination_point.label}'."
                    ),
                )
            )
    return issues


def _resolve_transport_ai_route_point_lookup(
    db: Session,
    *,
    provider: TransportRouteProvider,
    address: str,
    zip_code: str,
    country_code: str,
    country_name: str,
    reference_time: datetime | None,
    lookup_cache: dict[str, _TransportAgentGeocodeLookup | None],
) -> tuple[str, _TransportAgentGeocodeLookup | None]:
    geocode_request = GeocodeRequest(
        address=address,
        zip_code=zip_code,
        country_name=country_name,
        country_code=country_code,
    )
    lookup_key = f"{provider.provider}:{country_code}:{geocode_request.normalized_query}"
    if lookup_key in lookup_cache:
        return lookup_key, lookup_cache[lookup_key]

    cached_route_point = get_cached_transport_ai_route_point(
        db,
        provider=provider.provider,
        address=address,
        zip_code=zip_code,
        country_name=country_name,
        reference_time=reference_time,
    )
    if cached_route_point is not None:
        lookup_cache[lookup_key] = _build_transport_agent_geocode_lookup_from_cache(cached_route_point)
        return lookup_key, lookup_cache[lookup_key]

    try:
        geocode_result = provider.geocode(geocode_request)
    except TransportRouteProviderNoResultError:
        lookup_cache[lookup_key] = None
        return lookup_key, None

    lookup_cache[lookup_key] = _build_transport_agent_geocode_lookup_from_provider_result(geocode_result)
    return lookup_key, lookup_cache[lookup_key]


def _build_transport_agent_vehicle_type_configs(
    transport_settings: dict[str, object],
) -> list[TransportAgentPlanningVehicleTypeConfig]:
    return [
        TransportAgentPlanningVehicleTypeConfig(
            vehicle_type=vehicle_type,
            default_capacity=transport_settings.get(_SEAT_SETTING_BY_VEHICLE_TYPE[vehicle_type]),
            default_price=transport_settings.get(_PRICE_SETTING_BY_VEHICLE_TYPE[vehicle_type]),
            capacity_setting_name=_SEAT_SETTING_BY_VEHICLE_TYPE[vehicle_type],
            price_setting_name=_PRICE_SETTING_BY_VEHICLE_TYPE[vehicle_type],
        )
        for vehicle_type in _SUPPORTED_VEHICLE_TYPES
    ]


def _build_transport_agent_vehicle_type_config_index(
    planning_input: TransportAgentPlanningInput,
) -> dict[str, TransportAgentPlanningVehicleTypeConfig]:
    return {
        config.vehicle_type: config
        for config in planning_input.settings.vehicle_type_configs
    }


def _build_transport_ai_virtual_client_vehicle_key(
    *,
    planning_input_hash: str,
    partition_key: str,
    vehicle_type: str,
) -> str:
    digest = hashlib.sha256(
        f"{planning_input_hash}|{partition_key}|{vehicle_type}".encode("utf-8")
    ).hexdigest()[:12]
    return f"new-{vehicle_type}-{digest}"


def _build_transport_ai_existing_vehicle_candidate(
    *,
    planning_input: TransportAgentPlanningInput,
    partition: TransportAgentPlanningPartition,
    planning_vehicle: TransportAgentPlanningVehicle,
    type_config: TransportAgentPlanningVehicleTypeConfig | None,
    penalties: TransportAgentVehicleCandidatePenaltyConfig,
) -> TransportAgentVehicleCandidate | None:
    if planning_vehicle.vehicle_type is None:
        return None

    default_capacity = planning_vehicle.default_capacity
    if not _has_positive_number(default_capacity) and type_config is not None:
        default_capacity = type_config.default_capacity

    default_price = planning_vehicle.default_price
    if not _has_non_negative_number(default_price) and type_config is not None:
        default_price = type_config.default_price

    capacity = planning_vehicle.effective_capacity
    if not _has_positive_number(capacity):
        capacity = default_capacity

    if not _has_positive_number(capacity):
        return None
    if not _has_non_negative_number(default_price):
        return None

    return TransportAgentVehicleCandidate(
        candidate_key=f"{partition.partition_key}:existing:{planning_vehicle.vehicle_id}",
        partition_key=partition.partition_key,
        request_kind=partition.request_kind,
        project_name=partition.project_name,
        country_code=partition.country_code,
        country_name=partition.country_name,
        candidate_type="existing",
        recommended_action_type="keep",
        available_action_types=["keep", "update", "remove_from_day"],
        client_vehicle_key=None,
        vehicle_id=planning_vehicle.vehicle_id,
        schedule_id=planning_vehicle.schedule_id,
        service_scope=planning_vehicle.service_scope,
        route_kind=planning_input.route_kind,
        vehicle_type=planning_vehicle.vehicle_type,
        plate=planning_vehicle.plate,
        capacity=int(capacity),
        default_capacity=None if default_capacity is None else int(default_capacity),
        default_price=float(default_price),
        estimated_cost=float(default_price),
        change_penalty=penalties.keep_existing,
        update_penalty=penalties.update_existing,
        remove_from_day_penalty=penalties.remove_existing_from_day,
        change_vehicle_type_penalty=penalties.change_existing_type,
        assigned_count=planning_vehicle.assigned_count,
        pending_fields=list(planning_vehicle.pending_fields),
        is_ready_for_allocation=planning_vehicle.is_ready_for_allocation,
    )


def _build_transport_ai_virtual_vehicle_candidate(
    *,
    planning_input: TransportAgentPlanningInput,
    partition: TransportAgentPlanningPartition,
    type_config: TransportAgentPlanningVehicleTypeConfig,
    penalties: TransportAgentVehicleCandidatePenaltyConfig,
) -> TransportAgentVehicleCandidate | None:
    if not _has_positive_number(type_config.default_capacity):
        return None
    if not _has_non_negative_number(type_config.default_price):
        return None

    client_vehicle_key = _build_transport_ai_virtual_client_vehicle_key(
        planning_input_hash=planning_input.planning_input_hash,
        partition_key=partition.partition_key,
        vehicle_type=type_config.vehicle_type,
    )
    return TransportAgentVehicleCandidate(
        candidate_key=f"{partition.partition_key}:virtual:{type_config.vehicle_type}",
        partition_key=partition.partition_key,
        request_kind=partition.request_kind,
        project_name=partition.project_name,
        country_code=partition.country_code,
        country_name=partition.country_name,
        candidate_type="virtual",
        recommended_action_type="create",
        available_action_types=["create"],
        client_vehicle_key=client_vehicle_key,
        vehicle_id=None,
        schedule_id=None,
        service_scope=partition.request_kind,
        route_kind=planning_input.route_kind,
        vehicle_type=type_config.vehicle_type,
        plate=None,
        capacity=int(type_config.default_capacity),
        default_capacity=int(type_config.default_capacity),
        default_price=float(type_config.default_price),
        estimated_cost=float(type_config.default_price),
        change_penalty=penalties.create_virtual,
        update_penalty=None,
        remove_from_day_penalty=None,
        change_vehicle_type_penalty=None,
        assigned_count=0,
        pending_fields=[],
        is_ready_for_allocation=True,
    )


def _build_transport_agent_request(
    request_row: TransportRequestRow,
    *,
    project_row: ProjectRow,
) -> TransportAgentPlanningRequest:
    return TransportAgentPlanningRequest(
        request_id=request_row.id,
        request_kind=request_row.request_kind,
        service_date=request_row.service_date,
        requested_time=request_row.requested_time,
        user_id=request_row.user_id,
        chave=request_row.chave,
        nome=request_row.nome,
        project_name=project_row.name,
        country_code=project_row.country_code,
        country_name=project_row.country_name,
        workplace=request_row.workplace,
        origin_address=str(request_row.end_rua or "").strip(),
        origin_zip_code=str(request_row.zip or "").strip(),
    )


def _request_is_ready_for_transport_agent_planning(
    request_row: TransportRequestRow,
    *,
    project_row: ProjectRow | None,
) -> bool:
    if project_row is None:
        return False
    if not str(request_row.end_rua or "").strip():
        return False
    if not str(request_row.zip or "").strip():
        return False
    if not str(project_row.address or "").strip():
        return False
    if not str(project_row.zip_code or "").strip():
        return False
    if not str(project_row.country_code or "").strip():
        return False
    return True


def _build_transport_agent_vehicle_scope_index(
    snapshot: TransportOperationalSnapshot,
    *,
    transport_settings: dict[str, object],
) -> dict[str, list[TransportAgentPlanningVehicle]]:
    vehicles_by_scope: dict[str, list[TransportAgentPlanningVehicle]] = {}

    for request_scope in _REQUEST_SCOPE_ORDER:
        registry_by_vehicle_id = {
            registry_row.vehicle_id: registry_row
            for registry_row in getattr(snapshot, f"{request_scope}_vehicle_registry")
        }
        vehicle_rows = sorted(
            getattr(snapshot, f"{request_scope}_vehicles"),
            key=lambda row: (row.id, row.schedule_id or 0),
        )
        scope_vehicle_rows: list[TransportAgentPlanningVehicle] = []

        for vehicle_row in vehicle_rows:
            normalized_vehicle_type = str(vehicle_row.tipo or "").strip().lower()
            if normalized_vehicle_type not in _SUPPORTED_VEHICLE_TYPES:
                continue
            if not vehicle_row.is_ready_for_allocation:
                continue

            registry_row = registry_by_vehicle_id.get(vehicle_row.id)
            scope_vehicle_rows.append(
                TransportAgentPlanningVehicle(
                    vehicle_id=vehicle_row.id,
                    schedule_id=vehicle_row.schedule_id,
                    service_scope=request_scope,
                    route_kind=vehicle_row.route_kind,
                    departure_time=vehicle_row.departure_time,
                    plate=vehicle_row.placa,
                    vehicle_type=normalized_vehicle_type,
                    effective_capacity=vehicle_row.lugares,
                    default_capacity=transport_settings.get(_SEAT_SETTING_BY_VEHICLE_TYPE[normalized_vehicle_type]),
                    default_price=transport_settings.get(_PRICE_SETTING_BY_VEHICLE_TYPE[normalized_vehicle_type]),
                    assigned_count=registry_row.assigned_count if registry_row is not None else 0,
                    pending_fields=list(vehicle_row.pending_fields),
                    is_ready_for_allocation=vehicle_row.is_ready_for_allocation,
                )
            )

        vehicles_by_scope[request_scope] = scope_vehicle_rows

    return vehicles_by_scope


def _build_transport_agent_planning_input_hash(
    planning_input: TransportAgentPlanningInput,
) -> str:
    payload = planning_input.model_dump(mode="json", exclude={"planning_input_hash"})
    return hashlib.sha256(_dump_transport_ai_planning_json(payload).encode("utf-8")).hexdigest()


def build_transport_agent_planning_input(
    db: Session,
    *,
    service_date: date,
    route_kind: str,
    earliest_boarding_time: str,
    arrival_at_work_time: str,
    settings_obj: Settings = settings,
    snapshot: TransportOperationalSnapshot | None = None,
    transport_settings: dict[str, object] | None = None,
    preflight_issues: list[TransportAIPreflightIssue] | None = None,
) -> TransportAgentPlanningInput:
    if route_kind not in _SUPPORTED_ROUTE_KINDS:
        raise ValueError(f"Unsupported route kind for planning input: {route_kind}")

    effective_snapshot = snapshot or build_transport_operational_snapshot(
        db,
        service_date=service_date,
        route_kind=route_kind,
    )
    effective_transport_settings = transport_settings or get_transport_settings_payload(db)
    effective_preflight_issues = preflight_issues or build_transport_ai_preflight_issues(
        db,
        service_date=service_date,
        route_kind=route_kind,
        settings_obj=settings_obj,
        snapshot=effective_snapshot,
        transport_settings=effective_transport_settings,
    )

    project_rows_by_normalized_name = {
        _normalize_project_name(project_row.name): project_row
        for project_row in effective_snapshot.projects
    }
    pending_requests_by_scope = _iter_pending_requests_by_scope(
        effective_snapshot,
        service_date=service_date,
    )

    valid_requests_by_scope: dict[str, list[TransportAgentPlanningRequest]] = {
        request_scope: []
        for request_scope in _REQUEST_SCOPE_ORDER
    }
    referenced_project_rows: dict[str, ProjectRow] = {}
    partitions_by_key: dict[tuple[str, str, str], list[TransportAgentPlanningRequest]] = defaultdict(list)

    for request_scope in _REQUEST_SCOPE_ORDER:
        for request_row in pending_requests_by_scope.get(request_scope, []):
            project_row = project_rows_by_normalized_name.get(_normalize_project_name(request_row.projeto))
            if not _request_is_ready_for_transport_agent_planning(request_row, project_row=project_row):
                continue

            planning_request = _build_transport_agent_request(request_row, project_row=project_row)
            valid_requests_by_scope[request_scope].append(planning_request)
            referenced_project_rows[project_row.name] = project_row
            partitions_by_key[(request_scope, project_row.name, project_row.country_code)].append(planning_request)

    vehicles_by_scope = _build_transport_agent_vehicle_scope_index(
        effective_snapshot,
        transport_settings=effective_transport_settings,
    )
    partitions = [
        TransportAgentPlanningPartition(
            partition_key=f"{request_scope}:{project_name}:{country_code}",
            request_kind=request_scope,
            project_name=project_name,
            country_code=country_code,
            country_name=referenced_project_rows[project_name].country_name,
            destination_project=referenced_project_rows[project_name],
            requests=sorted(partition_requests, key=lambda row: (row.request_id, row.user_id, row.requested_time)),
            candidate_vehicles=list(vehicles_by_scope[request_scope]),
        )
        for request_scope, project_name, country_code in sorted(partitions_by_key)
        for partition_requests in [partitions_by_key[(request_scope, project_name, country_code)]]
    ]

    planning_input = TransportAgentPlanningInput(
        planning_input_hash="0" * 64,
        service_date=service_date,
        route_kind=route_kind,
        snapshot_key=effective_snapshot.snapshot_key,
        captured_at=effective_snapshot.captured_at,
        limits=TransportAgentPlanningLimits(
            earliest_boarding_time=earliest_boarding_time,
            arrival_at_work_time=arrival_at_work_time,
            max_passengers_per_run=settings_obj.transport_ai_max_passengers_per_run,
            max_runtime_seconds=settings_obj.transport_ai_max_runtime_seconds,
        ),
        settings=TransportAgentPlanningSettings(
            work_to_home_time=str(effective_transport_settings["work_to_home_time"]),
            last_update_time=str(effective_transport_settings["last_update_time"]),
            default_tolerance_minutes=int(effective_transport_settings["default_tolerance_minutes"]),
            price_currency_code=effective_transport_settings.get("price_currency_code"),
            price_rate_unit=str(effective_transport_settings["price_rate_unit"]),
            vehicle_type_configs=_build_transport_agent_vehicle_type_configs(effective_transport_settings),
        ),
        projects_by_name={
            project_name: referenced_project_rows[project_name]
            for project_name in sorted(referenced_project_rows)
        },
        requests_by_scope={
            request_scope: list(valid_requests_by_scope[request_scope])
            for request_scope in _REQUEST_SCOPE_ORDER
        },
        vehicles_by_scope={
            request_scope: list(vehicles_by_scope[request_scope])
            for request_scope in _REQUEST_SCOPE_ORDER
        },
        partitions=partitions,
        preflight_issues=list(effective_preflight_issues),
        total_requests=sum(len(valid_requests_by_scope[request_scope]) for request_scope in _REQUEST_SCOPE_ORDER),
        total_candidate_vehicles=sum(len(vehicles_by_scope[request_scope]) for request_scope in _REQUEST_SCOPE_ORDER),
    )
    planning_input_hash = _build_transport_agent_planning_input_hash(planning_input)
    return planning_input.model_copy(update={"planning_input_hash": planning_input_hash})


def resolve_transport_ai_route_points(
    db: Session,
    *,
    planning_input: TransportAgentPlanningInput,
    settings_obj: Settings = settings,
    provider: TransportRouteProvider | None = None,
    min_confidence: float = _TRANSPORT_AI_ROUTE_POINT_MIN_CONFIDENCE,
    reference_time: datetime | None = None,
) -> TransportAgentResolvedRoutePointsResult:
    effective_provider = provider or build_transport_route_provider(settings_obj=settings_obj)
    owns_provider = provider is None
    lookup_cache: dict[str, _TransportAgentGeocodeLookup | None] = {}
    persisted_lookup_keys: set[str] = set()
    issues: list[TransportAIPreflightIssue] = []
    resolved_partitions: list[TransportAgentResolvedRoutePointsPartition] = []

    try:
        for partition in planning_input.partitions:
            destination_point: TransportAgentResolvedRoutePoint | None = None
            passenger_points: list[TransportAgentResolvedRoutePoint] = []

            destination_lookup_key, destination_lookup = _resolve_transport_ai_route_point_lookup(
                db,
                provider=effective_provider,
                address=partition.destination_project.address,
                zip_code=partition.destination_project.zip_code,
                country_code=partition.country_code,
                country_name=partition.country_name,
                reference_time=reference_time,
                lookup_cache=lookup_cache,
            )
            if destination_lookup is None:
                issues.append(
                    _build_transport_ai_route_point_issue(
                        code="project_destination_geocode_missing",
                        message=(
                            f"Project '{partition.project_name}' destination could not be geocoded for "
                            f"'{partition.destination_project.address}, {partition.destination_project.zip_code}, {partition.country_name}'."
                        ),
                    )
                )
            elif destination_lookup.confidence is not None and destination_lookup.confidence < min_confidence:
                issues.append(
                    _build_transport_ai_route_point_issue(
                        code="project_destination_geocode_low_confidence",
                        message=(
                            f"Project '{partition.project_name}' destination returned low geocode confidence "
                            f"({destination_lookup.confidence:.2f})."
                        ),
                    )
                )
            elif _has_transport_ai_route_point_country_mismatch(
                expected_country_code=partition.country_code,
                expected_country_name=partition.country_name,
                lookup=destination_lookup,
            ):
                resolved_country = destination_lookup.country_code or destination_lookup.country_name or "unknown"
                issues.append(
                    _build_transport_ai_route_point_issue(
                        code="project_destination_country_mismatch",
                        message=(
                            f"Project '{partition.project_name}' destination geocoded to '{resolved_country}' "
                            f"but expected '{partition.country_code}'."
                        ),
                    )
                )
            else:
                if not destination_lookup.cached and destination_lookup_key not in persisted_lookup_keys:
                    upsert_transport_ai_route_point(
                        db,
                        source_id=partition.destination_project.id,
                        point_type="project_destination",
                        address=partition.destination_project.address,
                        zip_code=partition.destination_project.zip_code,
                        country_code=partition.country_code,
                        country_name=partition.country_name,
                        longitude=destination_lookup.longitude,
                        latitude=destination_lookup.latitude,
                        provider=destination_lookup.provider,
                        provider_place_id=destination_lookup.provider_place_id,
                        confidence=destination_lookup.confidence,
                        raw_response_json=destination_lookup.raw_response_json,
                        settings_obj=settings_obj,
                        created_at=reference_time,
                    )
                    persisted_lookup_keys.add(destination_lookup_key)

                destination_point = _build_transport_agent_resolved_route_point(
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
                    lookup=destination_lookup,
                )

            for request in partition.requests:
                passenger_lookup_key, passenger_lookup = _resolve_transport_ai_route_point_lookup(
                    db,
                    provider=effective_provider,
                    address=request.origin_address,
                    zip_code=request.origin_zip_code,
                    country_code=request.country_code,
                    country_name=request.country_name,
                    reference_time=reference_time,
                    lookup_cache=lookup_cache,
                )
                if passenger_lookup is None:
                    issues.append(
                        _build_transport_ai_route_point_issue(
                            code="passenger_origin_geocode_missing",
                            message=(
                                f"Passenger '{request.nome}' ({request.chave}) could not be geocoded for "
                                f"'{request.origin_address}, {request.origin_zip_code}, {request.country_name}'."
                            ),
                        )
                    )
                    continue

                if passenger_lookup.confidence is not None and passenger_lookup.confidence < min_confidence:
                    issues.append(
                        _build_transport_ai_route_point_issue(
                            code="passenger_origin_geocode_low_confidence",
                            message=(
                                f"Passenger '{request.nome}' ({request.chave}) returned low geocode confidence "
                                f"({passenger_lookup.confidence:.2f})."
                            ),
                        )
                    )
                    continue

                if _has_transport_ai_route_point_country_mismatch(
                    expected_country_code=request.country_code,
                    expected_country_name=request.country_name,
                    lookup=passenger_lookup,
                ):
                    resolved_country = passenger_lookup.country_code or passenger_lookup.country_name or "unknown"
                    issues.append(
                        _build_transport_ai_route_point_issue(
                            code="passenger_origin_country_mismatch",
                            message=(
                                f"Passenger '{request.nome}' ({request.chave}) geocoded to '{resolved_country}' "
                                f"but expected '{request.country_code}'."
                            ),
                        )
                    )
                    continue

                if not passenger_lookup.cached and passenger_lookup_key not in persisted_lookup_keys:
                    upsert_transport_ai_route_point(
                        db,
                        source_id=request.user_id,
                        point_type="passenger_origin",
                        address=request.origin_address,
                        zip_code=request.origin_zip_code,
                        country_code=request.country_code,
                        country_name=request.country_name,
                        longitude=passenger_lookup.longitude,
                        latitude=passenger_lookup.latitude,
                        provider=passenger_lookup.provider,
                        provider_place_id=passenger_lookup.provider_place_id,
                        confidence=passenger_lookup.confidence,
                        raw_response_json=passenger_lookup.raw_response_json,
                        settings_obj=settings_obj,
                        created_at=reference_time,
                    )
                    persisted_lookup_keys.add(passenger_lookup_key)

                passenger_points.append(
                    _build_transport_agent_resolved_route_point(
                        point_type="passenger_origin",
                        partition_key=partition.partition_key,
                        source_id=request.user_id,
                        request_id=request.request_id,
                        project_name=partition.project_name,
                        country_code=request.country_code,
                        country_name=request.country_name,
                        label=request.nome,
                        address=request.origin_address,
                        zip_code=request.origin_zip_code,
                        lookup=passenger_lookup,
                    )
                )

            resolved_partitions.append(
                TransportAgentResolvedRoutePointsPartition(
                    partition_key=partition.partition_key,
                    request_kind=partition.request_kind,
                    project_name=partition.project_name,
                    country_code=partition.country_code,
                    country_name=partition.country_name,
                    destination_point=destination_point,
                    passenger_points=sorted(passenger_points, key=lambda point: (point.request_id or 0, point.source_id)),
                )
            )

        return TransportAgentResolvedRoutePointsResult(
            planning_input_hash=planning_input.planning_input_hash,
            provider=effective_provider.provider,
            partitions=resolved_partitions,
            issues=issues,
            total_resolved_points=sum(
                len(partition.passenger_points) + (1 if partition.destination_point is not None else 0)
                for partition in resolved_partitions
            ),
        )
    finally:
        close_method = getattr(effective_provider, "close", None)
        if owns_provider and callable(close_method):
            close_method()


def build_transport_ai_route_matrices(
    db: Session,
    *,
    resolved_route_points: TransportAgentResolvedRoutePointsResult,
    settings_obj: Settings = settings,
    provider: TransportRouteProvider | None = None,
    profile: str | None = None,
    depart_at: datetime | None = None,
    reference_time: datetime | None = None,
) -> TransportAgentRouteMatricesResult:
    effective_provider = provider or build_transport_route_provider(settings_obj=settings_obj)
    owns_provider = provider is None
    effective_profile = str(profile or settings_obj.mapbox_matrix_profile)
    resolved_partitions: list[TransportAgentRouteMatrixPartition] = []
    issues: list[TransportAIPreflightIssue] = []

    try:
        for partition in resolved_route_points.partitions:
            if partition.destination_point is None or not partition.passenger_points:
                continue

            points = [*partition.passenger_points, partition.destination_point]
            coordinates = [
                _build_transport_route_coordinate_from_resolved_point(point)
                for point in points
            ]
            coordinate_pairs = [coordinate.as_pair() for coordinate in coordinates]

            cached_route_matrix = get_cached_transport_ai_route_matrix(
                db,
                provider=effective_provider.provider,
                profile=effective_profile,
                sources=coordinate_pairs,
                destinations=coordinate_pairs,
                depart_at=depart_at,
                reference_time=reference_time,
            )

            matrix_cached = cached_route_matrix is not None
            pair_issues: list[TransportAIPreflightIssue] = []
            if cached_route_matrix is not None:
                matrix_result = _build_transport_ai_matrix_result_from_cache(
                    cached_route_matrix=cached_route_matrix,
                    points=points,
                )
                durations_seconds = _normalize_transport_ai_matrix(matrix_result.durations_seconds)
                distances_meters = _normalize_transport_ai_matrix(matrix_result.distances_meters or [])
                pair_issues = _collect_transport_ai_route_matrix_pair_issues(
                    partition_key=partition.partition_key,
                    points=points,
                    durations_seconds=durations_seconds,
                    distances_meters=distances_meters,
                )
                issues.extend(pair_issues)
            else:
                try:
                    matrix_result = effective_provider.get_matrix(
                        MatrixRequest(
                            profile=effective_profile,
                            sources=coordinates,
                            destinations=coordinates,
                            depart_at=depart_at,
                        )
                    )
                except TransportRouteProviderNoRouteError:
                    durations_seconds = _build_unroutable_transport_ai_matrix(len(points))
                    distances_meters = _build_unroutable_transport_ai_matrix(len(points))
                    issues.append(
                        _build_transport_ai_route_matrix_issue(
                            code="route_matrix_partition_no_route",
                            message=(
                                f"Partition '{partition.partition_key}' does not have a complete route matrix "
                                "for the resolved passenger origins and project destination."
                            ),
                        )
                    )
                else:
                    durations_seconds = _normalize_transport_ai_matrix(matrix_result.durations_seconds)
                    if matrix_result.distances_meters is None:
                        distances_meters = _build_unroutable_transport_ai_matrix(len(points))
                    else:
                        distances_meters = _normalize_transport_ai_matrix(matrix_result.distances_meters)

                    pair_issues = _collect_transport_ai_route_matrix_pair_issues(
                        partition_key=partition.partition_key,
                        points=points,
                        durations_seconds=durations_seconds,
                        distances_meters=distances_meters,
                    )
                    issues.extend(pair_issues)
                    if not pair_issues:
                        upsert_transport_ai_route_matrix(
                            db,
                            provider=matrix_result.provider,
                            profile=matrix_result.profile,
                            sources=coordinate_pairs,
                            destinations=coordinate_pairs,
                            durations=durations_seconds,
                            distances=distances_meters,
                            depart_at=matrix_result.depart_at,
                            settings_obj=settings_obj,
                            created_at=reference_time,
                        )

            resolved_partitions.append(
                TransportAgentRouteMatrixPartition(
                    partition_key=partition.partition_key,
                    request_kind=partition.request_kind,
                    project_name=partition.project_name,
                    country_code=partition.country_code,
                    country_name=partition.country_name,
                    points=points,
                    destination_index=len(points) - 1,
                    cached=matrix_cached,
                    durations_seconds=durations_seconds,
                    distances_meters=distances_meters,
                )
            )

        return TransportAgentRouteMatricesResult(
            planning_input_hash=resolved_route_points.planning_input_hash,
            provider=effective_provider.provider,
            profile=effective_profile,
            partitions=resolved_partitions,
            issues=issues,
            total_matrices=len(resolved_partitions),
        )
    finally:
        close_method = getattr(effective_provider, "close", None)
        if owns_provider and callable(close_method):
            close_method()


def build_transport_ai_vehicle_candidates(
    *,
    planning_input: TransportAgentPlanningInput,
    penalties: TransportAgentVehicleCandidatePenaltyConfig | None = None,
) -> TransportAgentVehicleCandidatesResult:
    effective_penalties = penalties or TransportAgentVehicleCandidatePenaltyConfig()
    type_config_by_vehicle_type = _build_transport_agent_vehicle_type_config_index(planning_input)
    resolved_partitions: list[TransportAgentVehicleCandidatesPartition] = []

    for partition in planning_input.partitions:
        partition_candidates: list[TransportAgentVehicleCandidate] = []

        for planning_vehicle in sorted(
            partition.candidate_vehicles,
            key=lambda vehicle: (vehicle.vehicle_id, vehicle.schedule_id or 0),
        ):
            type_config = None
            if planning_vehicle.vehicle_type is not None:
                type_config = type_config_by_vehicle_type.get(planning_vehicle.vehicle_type)
            candidate = _build_transport_ai_existing_vehicle_candidate(
                planning_input=planning_input,
                partition=partition,
                planning_vehicle=planning_vehicle,
                type_config=type_config,
                penalties=effective_penalties,
            )
            if candidate is not None:
                partition_candidates.append(candidate)

        for vehicle_type in _SUPPORTED_VEHICLE_TYPES:
            type_config = type_config_by_vehicle_type.get(vehicle_type)
            if type_config is None:
                continue
            candidate = _build_transport_ai_virtual_vehicle_candidate(
                planning_input=planning_input,
                partition=partition,
                type_config=type_config,
                penalties=effective_penalties,
            )
            if candidate is not None:
                partition_candidates.append(candidate)

        resolved_partitions.append(
            TransportAgentVehicleCandidatesPartition(
                partition_key=partition.partition_key,
                request_kind=partition.request_kind,
                project_name=partition.project_name,
                country_code=partition.country_code,
                country_name=partition.country_name,
                candidates=partition_candidates,
            )
        )

    return TransportAgentVehicleCandidatesResult(
        planning_input_hash=planning_input.planning_input_hash,
        penalties=effective_penalties,
        partitions=resolved_partitions,
        total_candidates=sum(len(partition.candidates) for partition in resolved_partitions),
    )


def solve_transport_ai_partition(
    *,
    planning_input: TransportAgentPlanningInput,
    route_matrix_partition: TransportAgentRouteMatrixPartition,
    vehicle_candidates_partition: TransportAgentVehicleCandidatesPartition,
    prefer_ortools: bool = True,
) -> TransportAgentPartitionSolveResult:
    partition = next(
        (row for row in planning_input.partitions if row.partition_key == route_matrix_partition.partition_key),
        None,
    )
    if partition is None:
        raise ValueError(
            f"Partition '{route_matrix_partition.partition_key}' was not found in the planning input"
        )
    if vehicle_candidates_partition.partition_key != partition.partition_key:
        raise ValueError("The vehicle candidates partition does not match the route matrix partition")

    request_ids = tuple(sorted(request.request_id for request in partition.requests))
    if not request_ids:
        return _build_transport_ai_partition_solve_result(
            planning_input=planning_input,
            partition=partition,
            algorithm_used="heuristic",
            selected_options=[],
            issues=[],
            unallocated_request_ids=[],
        )

    request_point_index_by_request_id = _build_transport_ai_request_point_index(route_matrix_partition)
    missing_request_ids = sorted(
        request_id for request_id in request_ids if request_id not in request_point_index_by_request_id
    )
    if missing_request_ids:
        return _build_transport_ai_partition_solve_result(
            planning_input=planning_input,
            partition=partition,
            algorithm_used="heuristic",
            selected_options=[],
            issues=[
                _build_transport_ai_solver_issue(
                    code="transport_ai_partition_missing_route_points",
                    message=(
                        f"Partition '{partition.partition_key}' is missing resolved route points for requests "
                        f"{', '.join(str(request_id) for request_id in missing_request_ids)}."
                    ),
                )
            ],
            unallocated_request_ids=missing_request_ids,
        )

    vehicle_units = _build_transport_ai_solver_vehicle_units(
        candidates=vehicle_candidates_partition.candidates,
        request_count=len(request_ids),
    )
    if not vehicle_units:
        return _build_transport_ai_partition_solve_result(
            planning_input=planning_input,
            partition=partition,
            algorithm_used="heuristic",
            selected_options=[],
            issues=[
                _build_transport_ai_solver_issue(
                    code="transport_ai_partition_no_vehicle_candidates",
                    message=(
                        f"Partition '{partition.partition_key}' does not have any feasible vehicle candidates."
                    ),
                )
            ],
            unallocated_request_ids=list(request_ids),
        )

    available_window_seconds = (
        _parse_transport_ai_hhmm_to_seconds(planning_input.limits.arrival_at_work_time)
        - _parse_transport_ai_hhmm_to_seconds(planning_input.limits.earliest_boarding_time)
    )
    max_route_passengers = min(
        len(request_ids),
        max(vehicle_unit.candidate.capacity for vehicle_unit in vehicle_units),
    )
    subset_routes: dict[tuple[int, ...], _TransportAISolverSubsetRoute] = {}
    if len(request_ids) <= _TRANSPORT_AI_MAX_EXACT_SOLVER_REQUESTS:
        subset_routes = _build_transport_ai_exact_subset_routes(
            request_ids=request_ids,
            route_matrix_partition=route_matrix_partition,
            request_point_index_by_request_id=request_point_index_by_request_id,
            available_window_seconds=available_window_seconds,
            max_route_passengers=max_route_passengers,
        )

    selected_options: list[_TransportAISolverRouteOption] | None = None
    algorithm_used = "heuristic"
    if prefer_ortools and subset_routes:
        route_options = _build_transport_ai_route_options_from_subset_routes(
            vehicle_units=vehicle_units,
            subset_routes=subset_routes,
        )
        algorithm_used, selected_options = _solve_transport_ai_partition_with_ortools(
            request_ids=request_ids,
            route_options=route_options,
            max_runtime_seconds=planning_input.limits.max_runtime_seconds,
        )

    if selected_options is None:
        selected_options = _solve_transport_ai_partition_with_heuristic(
            request_ids=request_ids,
            vehicle_units=vehicle_units,
            route_matrix_partition=route_matrix_partition,
            request_point_index_by_request_id=request_point_index_by_request_id,
            available_window_seconds=available_window_seconds,
        )
        algorithm_used = "heuristic"

    if not selected_options:
        return _build_transport_ai_partition_solve_result(
            planning_input=planning_input,
            partition=partition,
            algorithm_used=algorithm_used,
            selected_options=[],
            issues=[
                _build_transport_ai_solver_issue(
                    code="transport_ai_partition_no_solution",
                    message=(
                        f"Partition '{partition.partition_key}' does not have a feasible assignment that respects "
                        "capacity and the configured boarding/arrival window."
                    ),
                )
            ],
            unallocated_request_ids=list(request_ids),
        )

    allocated_request_ids = sorted(
        request_id
        for selected_option in selected_options
        for request_id in selected_option.request_ids
    )
    if allocated_request_ids != list(request_ids):
        allocated_request_id_set = set(allocated_request_ids)
        return _build_transport_ai_partition_solve_result(
            planning_input=planning_input,
            partition=partition,
            algorithm_used=algorithm_used,
            selected_options=selected_options,
            issues=[
                _build_transport_ai_solver_issue(
                    code="transport_ai_partition_no_solution",
                    message=(
                        f"Partition '{partition.partition_key}' could only allocate part of the passenger set "
                        "within the hard capacity and time-window constraints."
                    ),
                )
            ],
            unallocated_request_ids=[
                request_id for request_id in request_ids if request_id not in allocated_request_id_set
            ],
        )

    return _build_transport_ai_partition_solve_result(
        planning_input=planning_input,
        partition=partition,
        algorithm_used=algorithm_used,
        selected_options=selected_options,
        issues=[],
        unallocated_request_ids=[],
    )


def schedule_transport_ai_route_times(
    *,
    planning_input: TransportAgentPlanningInput,
    route_matrix_partition: TransportAgentRouteMatrixPartition,
    partition_solve_result: TransportAgentPartitionSolveResult,
    arrival_at_work_time: str | None = None,
) -> TransportAgentPartitionSolveResult:
    if partition_solve_result.partition_key != route_matrix_partition.partition_key:
        raise ValueError("The partition solve result does not match the route matrix partition")

    request_point_index_by_request_id = _build_transport_ai_request_point_index(route_matrix_partition)
    issues = list(partition_solve_result.issues)
    earliest_boarding_seconds = _parse_transport_ai_hhmm_to_seconds(planning_input.limits.earliest_boarding_time)
    configured_arrival_seconds = _parse_transport_ai_hhmm_to_seconds(planning_input.limits.arrival_at_work_time)
    effective_arrival_time = arrival_at_work_time or planning_input.limits.arrival_at_work_time
    effective_arrival_seconds = _parse_transport_ai_hhmm_to_seconds(effective_arrival_time)

    if effective_arrival_seconds > configured_arrival_seconds:
        issues.append(
            _build_transport_ai_route_schedule_issue(
                code="transport_ai_route_arrival_after_limit",
                message=(
                    f"Partition '{partition_solve_result.partition_key}' cannot project arrival at "
                    f"'{effective_arrival_time}' because the configured latest arrival is "
                    f"'{planning_input.limits.arrival_at_work_time}'."
                ),
            )
        )

    scheduled_routes: list[TransportAgentSolvedRoute] = []
    for route in partition_solve_result.routes:
        passenger_seconds_by_request_id: dict[int, int] = {}
        next_point_index = route_matrix_partition.destination_index
        total_duration_seconds = 0
        total_distance_meters = 0

        for request_id in reversed(route.pickup_order_request_ids):
            point_index = request_point_index_by_request_id.get(request_id)
            if point_index is None:
                issues.append(
                    _build_transport_ai_route_schedule_issue(
                        code="transport_ai_route_schedule_request_point_missing",
                        message=(
                            f"Route '{route.route_key}' does not have a resolved matrix point for request "
                            f"'{request_id}'."
                        ),
                    )
                )
                passenger_seconds_by_request_id.clear()
                break

            duration_seconds = route_matrix_partition.durations_seconds[point_index][next_point_index]
            distance_meters = route_matrix_partition.distances_meters[point_index][next_point_index]
            if duration_seconds is None or distance_meters is None:
                issues.append(
                    _build_transport_ai_route_schedule_issue(
                        code="transport_ai_route_schedule_pair_no_route",
                        message=(
                            f"Route '{route.route_key}' is missing a routable segment for request "
                            f"'{request_id}'."
                        ),
                    )
                )
                passenger_seconds_by_request_id.clear()
                break

            total_duration_seconds += duration_seconds
            total_distance_meters += distance_meters
            rounded_offset_seconds = _round_transport_ai_duration_seconds_to_minute_ceiling(total_duration_seconds)
            passenger_seconds_by_request_id[request_id] = effective_arrival_seconds - rounded_offset_seconds
            next_point_index = point_index

        scheduled_passengers = []
        for passenger in sorted(route.passengers, key=lambda row: (row.pickup_order, row.request_id)):
            scheduled_pickup_seconds = passenger_seconds_by_request_id.get(passenger.request_id)
            scheduled_pickup_time = None
            if scheduled_pickup_seconds is not None and scheduled_pickup_seconds >= 0:
                scheduled_pickup_time = _format_transport_ai_seconds_to_hhmm(scheduled_pickup_seconds)

            scheduled_passengers.append(
                passenger.model_copy(update={"scheduled_pickup_time": scheduled_pickup_time})
            )

        if route.pickup_order_request_ids:
            first_pickup_seconds = passenger_seconds_by_request_id.get(route.pickup_order_request_ids[0])
            if first_pickup_seconds is not None and first_pickup_seconds < earliest_boarding_seconds:
                issues.append(
                    _build_transport_ai_route_schedule_issue(
                        code="transport_ai_route_first_pickup_before_earliest",
                        message=(
                            f"Route '{route.route_key}' starts at '{_format_transport_ai_seconds_to_hhmm(first_pickup_seconds)}', "
                            f"before the earliest allowed boarding time '{planning_input.limits.earliest_boarding_time}'."
                        ),
                    )
                )

        scheduled_routes.append(
            route.model_copy(
                update={
                    "passengers": scheduled_passengers,
                    "projected_arrival_time": effective_arrival_time,
                    "total_duration_seconds": total_duration_seconds,
                    "total_distance_meters": total_distance_meters,
                }
            )
        )

    blocking_issue_present = any(issue.blocking for issue in issues)
    return partition_solve_result.model_copy(
        update={
            "routes": scheduled_routes,
            "issues": issues,
            "total_duration_seconds": sum(route.total_duration_seconds for route in scheduled_routes),
            "total_distance_meters": sum(route.total_distance_meters for route in scheduled_routes),
            "is_feasible": not partition_solve_result.unallocated_request_ids and not blocking_issue_present,
        }
    )


def _build_transport_ai_plan_issue(
    *,
    code: str,
    message: str,
    blocking: bool = True,
    request_id: int | None = None,
    vehicle_id: int | None = None,
) -> TransportProposalValidationIssue:
    return TransportProposalValidationIssue(
        code=code,
        message=message,
        blocking=blocking,
        request_id=request_id,
        vehicle_id=vehicle_id,
    )


def _truncate_transport_ai_planning_text(message: str, *, max_length: int) -> str:
    normalized = " ".join(str(message or "").strip().split())
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[: max_length - 3]}..."


def _build_transport_ai_pending_decision_rationale(
    *,
    request_id: int,
    issue: TransportProposalValidationIssue,
) -> str:
    return _truncate_transport_ai_planning_text(
        f"Keep request '{request_id}' pending because the transport AI plan reported: {issue.message}",
        max_length=500,
    )


def _build_transport_ai_plan_vehicle_ref(
    route: TransportAgentSolvedRoute,
) -> str:
    if route.vehicle_id is not None:
        return f"existing:{route.vehicle_id}"
    if route.client_vehicle_key:
        return f"new:{route.client_vehicle_key}"
    raise ValueError(f"Route '{route.route_key}' is missing a resolvable vehicle reference")


def _build_transport_ai_plan_action_client_vehicle_key(
    route: TransportAgentSolvedRoute,
) -> str:
    if route.vehicle_id is not None:
        return f"existing:{route.vehicle_id}"
    if route.client_vehicle_key:
        return route.client_vehicle_key
    raise ValueError(f"Route '{route.route_key}' is missing a client vehicle key")


def _build_transport_ai_plan_action_state(
    route: TransportAgentSolvedRoute,
    *,
    vehicle_ref: str,
    client_vehicle_key: str,
) -> dict[str, object]:
    return {
        "vehicle_ref": vehicle_ref,
        "vehicle_id": route.vehicle_id,
        "schedule_id": route.schedule_id,
        "client_vehicle_key": client_vehicle_key,
        "service_scope": route.service_scope,
        "route_kind": route.route_kind,
        "vehicle_type": route.vehicle_type,
        "plate": route.plate,
        "capacity": route.capacity,
        "estimated_cost": float(route.estimated_cost),
    }


def _build_transport_ai_plan_key(
    *,
    planning_input_hash: str,
    vehicle_actions: list[TransportAgentVehicleAction],
    passenger_allocations: list[TransportAgentPassengerAllocation],
    route_itineraries: list[TransportAgentVehicleItinerary],
    validation_issues: list[TransportProposalValidationIssue],
) -> str:
    payload = {
        "planning_input_hash": planning_input_hash,
        "vehicle_actions": [action.model_dump(mode="json") for action in vehicle_actions],
        "passenger_allocations": [allocation.model_dump(mode="json") for allocation in passenger_allocations],
        "route_itineraries": [itinerary.model_dump(mode="json") for itinerary in route_itineraries],
        "validation_issues": [issue.model_dump(mode="json") for issue in validation_issues],
    }
    digest = hashlib.sha256(_dump_transport_ai_planning_json(payload).encode("utf-8")).hexdigest()
    return f"transport-ai-plan:{digest}"


def _format_transport_ai_plan_cost_text(
    *,
    amount: float,
    currency_code: str | None,
    rate_unit: str,
) -> str:
    amount_text = f"{amount:.2f}"
    if currency_code:
        amount_text = f"{currency_code} {amount_text}"
    return f"{amount_text}/{rate_unit}"


def _build_transport_ai_plan_objective_summary(
    *,
    route_count: int,
    cost_summary: TransportAgentCostSummary,
    validation_issue_count: int,
) -> str:
    if cost_summary.estimated_cost_delta < 0:
        delta_text = (
            "saving "
            + _format_transport_ai_plan_cost_text(
                amount=abs(cost_summary.estimated_cost_delta),
                currency_code=cost_summary.price_currency_code,
                rate_unit=cost_summary.price_rate_unit,
            )
        )
    elif cost_summary.estimated_cost_delta > 0:
        delta_text = (
            "adding "
            + _format_transport_ai_plan_cost_text(
                amount=cost_summary.estimated_cost_delta,
                currency_code=cost_summary.price_currency_code,
                rate_unit=cost_summary.price_rate_unit,
            )
        )
    else:
        delta_text = "matching the current estimated fleet cost"

    suggested_cost_text = _format_transport_ai_plan_cost_text(
        amount=cost_summary.suggested_total_estimated_cost,
        currency_code=cost_summary.price_currency_code,
        rate_unit=cost_summary.price_rate_unit,
    )
    issue_text = "1 validation issue" if validation_issue_count == 1 else f"{validation_issue_count} validation issues"
    return (
        f"Suggested {cost_summary.suggested_vehicle_count} vehicles across {route_count} routes, {delta_text}, "
        f"for an estimated total of {suggested_cost_text}; {issue_text}."
    )


def build_transport_agent_plan_from_solver_result(
    *,
    planning_input: TransportAgentPlanningInput,
    route_matrices_result: TransportAgentRouteMatricesResult,
    partition_solve_results: list[TransportAgentPartitionSolveResult],
) -> TransportAgentPlan:
    if route_matrices_result.planning_input_hash != planning_input.planning_input_hash:
        raise ValueError("The route matrices result does not match the planning input hash")

    partition_by_key = {
        partition.partition_key: partition
        for partition in planning_input.partitions
    }
    route_matrix_by_partition_key = {
        partition.partition_key: partition
        for partition in route_matrices_result.partitions
    }
    partition_result_by_key = {
        partition_result.partition_key: partition_result
        for partition_result in partition_solve_results
    }

    validation_issues: list[TransportProposalValidationIssue] = []
    seen_issue_keys: set[tuple[str, str, int | None, int | None]] = set()
    requests_with_validation_issues: set[int] = set()

    def add_validation_issue(
        *,
        code: str,
        message: str,
        blocking: bool = True,
        request_id: int | None = None,
        vehicle_id: int | None = None,
    ) -> None:
        issue = _build_transport_ai_plan_issue(
            code=code,
            message=message,
            blocking=blocking,
            request_id=request_id,
            vehicle_id=vehicle_id,
        )
        issue_key = (issue.code, issue.message, issue.request_id, issue.vehicle_id)
        if issue_key in seen_issue_keys:
            return
        seen_issue_keys.add(issue_key)
        validation_issues.append(issue)
        if request_id is not None:
            requests_with_validation_issues.add(request_id)

    for preflight_issue in planning_input.preflight_issues:
        add_validation_issue(
            code=preflight_issue.code,
            message=preflight_issue.message,
            blocking=preflight_issue.blocking,
        )

    for route_matrix_issue in route_matrices_result.issues:
        add_validation_issue(
            code=route_matrix_issue.code,
            message=route_matrix_issue.message,
            blocking=route_matrix_issue.blocking,
        )

    all_request_ids = {
        request.request_id
        for partition in planning_input.partitions
        for request in partition.requests
    }
    allocated_request_ids: set[int] = set()

    vehicle_actions_by_ref: dict[str, TransportAgentVehicleAction] = {}
    passenger_allocations: list[TransportAgentPassengerAllocation] = []
    route_itineraries: list[TransportAgentVehicleItinerary] = []
    used_existing_vehicle_route_keys: defaultdict[int, list[str]] = defaultdict(list)

    for partition in planning_input.partitions:
        partition_result = partition_result_by_key.get(partition.partition_key)
        if partition_result is None:
            for request in partition.requests:
                add_validation_issue(
                    code="transport_ai_partition_result_missing",
                    message=(
                        f"Partition '{partition.partition_key}' is missing a consolidated solver result for "
                        f"request '{request.request_id}'."
                    ),
                    request_id=request.request_id,
                )
            continue

        if partition_result.planning_input_hash != planning_input.planning_input_hash:
            raise ValueError(
                f"The solve result for partition '{partition.partition_key}' does not match the planning input hash"
            )

        route_matrix_partition = route_matrix_by_partition_key.get(partition.partition_key)
        request_by_id = {
            request.request_id: request
            for request in partition.requests
        }
        request_point_index_by_request_id = {}
        if route_matrix_partition is not None:
            request_point_index_by_request_id = _build_transport_ai_request_point_index(route_matrix_partition)
        else:
            add_validation_issue(
                code="transport_ai_partition_matrix_missing",
                message=(
                    f"Partition '{partition.partition_key}' is missing a route matrix required to build the itinerary."
                ),
            )

        for route in sorted(partition_result.routes, key=lambda row: row.route_key):
            vehicle_ref = _build_transport_ai_plan_vehicle_ref(route)
            action_client_vehicle_key = _build_transport_ai_plan_action_client_vehicle_key(route)
            action_state = _build_transport_ai_plan_action_state(
                route,
                vehicle_ref=vehicle_ref,
                client_vehicle_key=action_client_vehicle_key,
            )

            if vehicle_ref not in vehicle_actions_by_ref:
                action_type = "keep" if route.vehicle_id is not None else "create"
                rationale = (
                    f"Keep existing {route.vehicle_type} for partition '{route.partition_key}' because it satisfies "
                    "the selected route at the chosen cost."
                    if route.vehicle_id is not None
                    else f"Create a new {route.vehicle_type} for partition '{route.partition_key}' because no existing "
                    "vehicle was selected for this route at the chosen cost."
                )
                vehicle_actions_by_ref[vehicle_ref] = TransportAgentVehicleAction(
                    action_key=f"{action_type}:{action_client_vehicle_key}",
                    action_type=action_type,
                    service_scope=route.service_scope,
                    vehicle_id=route.vehicle_id,
                    schedule_id=route.schedule_id,
                    client_vehicle_key=action_client_vehicle_key,
                    before=action_state if route.vehicle_id is not None else None,
                    after=action_state,
                    rationale=rationale,
                    cost_delta=0.0 if route.vehicle_id is not None else float(route.estimated_cost),
                )

            if route.vehicle_id is not None:
                used_existing_vehicle_route_keys[route.vehicle_id].append(route.route_key)

            passenger_by_request_id = {
                passenger.request_id: passenger
                for passenger in route.passengers
            }
            stops: list[TransportAgentRouteStop] = []
            previous_point_index: int | None = None

            for stop_order, request_id in enumerate(route.pickup_order_request_ids):
                request_row = request_by_id.get(request_id)
                passenger = passenger_by_request_id.get(request_id)
                if request_row is None or passenger is None:
                    add_validation_issue(
                        code="transport_ai_route_passenger_missing",
                        message=(
                            f"Route '{route.route_key}' is missing passenger data for request '{request_id}'."
                        ),
                        request_id=request_id,
                        vehicle_id=route.vehicle_id,
                    )
                    continue

                if passenger.scheduled_pickup_time is None or route.projected_arrival_time is None:
                    add_validation_issue(
                        code="transport_ai_route_schedule_missing",
                        message=(
                            f"Route '{route.route_key}' is missing a scheduled pickup or arrival time for request "
                            f"'{request_id}'."
                        ),
                        request_id=request_id,
                        vehicle_id=route.vehicle_id,
                    )
                    continue

                passenger_allocations.append(
                    TransportAgentPassengerAllocation(
                        request_id=request_row.request_id,
                        request_kind=request_row.request_kind,
                        service_date=planning_input.service_date,
                        route_kind=planning_input.route_kind,
                        vehicle_ref=vehicle_ref,
                        user_id=request_row.user_id,
                        chave=request_row.chave,
                        nome=request_row.nome,
                        project_name=request_row.project_name,
                        pickup_order=passenger.pickup_order,
                        scheduled_pickup_time=passenger.scheduled_pickup_time,
                        projected_arrival_time=route.projected_arrival_time,
                        rationale=(
                            f"Assign request '{request_row.request_id}' to route '{route.route_key}' using "
                            f"{vehicle_ref}."
                        ),
                    )
                )
                allocated_request_ids.add(request_row.request_id)

                if route_matrix_partition is None:
                    continue

                point_index = request_point_index_by_request_id.get(request_id)
                if point_index is None:
                    add_validation_issue(
                        code="transport_ai_route_point_missing",
                        message=(
                            f"Route '{route.route_key}' is missing a resolved route point for request '{request_id}'."
                        ),
                        request_id=request_id,
                        vehicle_id=route.vehicle_id,
                    )
                    continue

                duration_from_previous_seconds = None
                distance_from_previous_meters = None
                if previous_point_index is not None:
                    duration_from_previous_seconds = route_matrix_partition.durations_seconds[previous_point_index][point_index]
                    distance_from_previous_meters = route_matrix_partition.distances_meters[previous_point_index][point_index]
                    if duration_from_previous_seconds is None or distance_from_previous_meters is None:
                        add_validation_issue(
                            code="transport_ai_route_segment_missing",
                            message=(
                                f"Route '{route.route_key}' is missing a matrix segment for request '{request_id}'."
                            ),
                            request_id=request_id,
                            vehicle_id=route.vehicle_id,
                        )
                        duration_from_previous_seconds = None
                        distance_from_previous_meters = None

                point = route_matrix_partition.points[point_index]
                stops.append(
                    TransportAgentRouteStop(
                        stop_order=stop_order,
                        stop_type="pickup",
                        request_id=request_row.request_id,
                        user_id=request_row.user_id,
                        passenger_name=request_row.nome,
                        project_name=request_row.project_name,
                        address=point.address,
                        zip_code=point.zip_code,
                        country_code=point.country_code,
                        longitude=point.longitude,
                        latitude=point.latitude,
                        scheduled_time=passenger.scheduled_pickup_time,
                        duration_from_previous_seconds=duration_from_previous_seconds,
                        distance_from_previous_meters=distance_from_previous_meters,
                    )
                )
                previous_point_index = point_index

            if route_matrix_partition is not None and route.projected_arrival_time is not None:
                destination_point = route_matrix_partition.points[route_matrix_partition.destination_index]
                destination_duration_seconds = None
                destination_distance_meters = None
                if previous_point_index is not None:
                    destination_duration_seconds = route_matrix_partition.durations_seconds[previous_point_index][
                        route_matrix_partition.destination_index
                    ]
                    destination_distance_meters = route_matrix_partition.distances_meters[previous_point_index][
                        route_matrix_partition.destination_index
                    ]
                    if destination_duration_seconds is None or destination_distance_meters is None:
                        add_validation_issue(
                            code="transport_ai_destination_segment_missing",
                            message=(
                                f"Route '{route.route_key}' is missing the final segment to the project destination."
                            ),
                            vehicle_id=route.vehicle_id,
                        )
                        destination_duration_seconds = None
                        destination_distance_meters = None

                stops.append(
                    TransportAgentRouteStop(
                        stop_order=len(stops),
                        stop_type="destination",
                        request_id=None,
                        user_id=None,
                        passenger_name=None,
                        project_name=partition.project_name,
                        address=destination_point.address,
                        zip_code=destination_point.zip_code,
                        country_code=destination_point.country_code,
                        longitude=destination_point.longitude,
                        latitude=destination_point.latitude,
                        scheduled_time=route.projected_arrival_time,
                        duration_from_previous_seconds=destination_duration_seconds,
                        distance_from_previous_meters=destination_distance_meters,
                    )
                )
                route_itineraries.append(
                    TransportAgentVehicleItinerary(
                        route_key=route.route_key,
                        partition_key=route.partition_key,
                        vehicle_ref=vehicle_ref,
                        service_scope=route.service_scope,
                        route_kind=route.route_kind,
                        vehicle_type=route.vehicle_type,
                        vehicle_id=route.vehicle_id,
                        schedule_id=route.schedule_id,
                        client_vehicle_key=action_client_vehicle_key,
                        plate=route.plate,
                        project_name=partition.project_name,
                        country_code=partition.country_code,
                        country_name=partition.country_name,
                        estimated_cost=float(route.estimated_cost),
                        total_duration_seconds=route.total_duration_seconds,
                        total_distance_meters=route.total_distance_meters,
                        projected_arrival_time=route.projected_arrival_time,
                        stops=stops,
                    )
                )

        for request_id in sorted(partition_result.unallocated_request_ids):
            add_validation_issue(
                code="transport_ai_request_unallocated",
                message=(
                    f"Request '{request_id}' in partition '{partition.partition_key}' could not be allocated to a "
                    "feasible route."
                ),
                request_id=request_id,
            )

    for vehicle_id, route_keys in sorted(used_existing_vehicle_route_keys.items()):
        unique_route_keys = sorted(set(route_keys))
        if len(unique_route_keys) < 2:
            continue
        add_validation_issue(
            code="transport_ai_existing_vehicle_reused",
            message=(
                f"Existing vehicle '{vehicle_id}' was selected by multiple routes: {', '.join(unique_route_keys)}."
            ),
            vehicle_id=vehicle_id,
        )

    for request_id in sorted(all_request_ids - allocated_request_ids - requests_with_validation_issues):
        add_validation_issue(
            code="transport_ai_request_unallocated",
            message=f"Request '{request_id}' is not present in the final consolidated allocations.",
            request_id=request_id,
        )

    vehicle_actions = sorted(
        vehicle_actions_by_ref.values(),
        key=lambda action: (action.service_scope, action.action_type, action.client_vehicle_key, action.vehicle_id or 0),
    )
    passenger_allocations = sorted(
        passenger_allocations,
        key=lambda allocation: (allocation.project_name, allocation.vehicle_ref, allocation.pickup_order, allocation.request_id),
    )
    route_itineraries = sorted(
        route_itineraries,
        key=lambda itinerary: (itinerary.partition_key, itinerary.route_key),
    )
    validation_issues = sorted(
        validation_issues,
        key=lambda issue: (issue.request_id or 0, issue.vehicle_id or 0, issue.code, issue.message),
    )

    current_vehicle_cost_by_id: dict[int, float] = {}
    for partition in planning_input.partitions:
        for planning_vehicle in partition.candidate_vehicles:
            if planning_vehicle.vehicle_id in current_vehicle_cost_by_id:
                continue
            if planning_vehicle.default_price is None:
                continue
            current_vehicle_cost_by_id[planning_vehicle.vehicle_id] = float(planning_vehicle.default_price)

    suggested_total_estimated_cost = sum(
        float(action.after.get("estimated_cost") or 0.0)
        for action in vehicle_actions
    )
    cost_summary = TransportAgentCostSummary(
        price_currency_code=planning_input.settings.price_currency_code,
        price_rate_unit=planning_input.settings.price_rate_unit,
        current_total_estimated_cost=sum(current_vehicle_cost_by_id.values()),
        suggested_total_estimated_cost=suggested_total_estimated_cost,
        estimated_cost_delta=suggested_total_estimated_cost - sum(current_vehicle_cost_by_id.values()),
        current_vehicle_count=len(current_vehicle_cost_by_id),
        suggested_vehicle_count=len(vehicle_actions),
    )

    change_counts = {
        "keep_count": 0,
        "create_count": 0,
        "update_count": 0,
        "remove_from_day_count": 0,
    }
    change_counts_by_vehicle_type: defaultdict[str, dict[str, int]] = defaultdict(
        lambda: {
            "keep_count": 0,
            "create_count": 0,
            "update_count": 0,
            "remove_from_day_count": 0,
            "total_count": 0,
        }
    )
    for action in vehicle_actions:
        counter_key = f"{action.action_type}_count"
        if counter_key in change_counts:
            change_counts[counter_key] += 1
        vehicle_type = str(action.after.get("vehicle_type") or "").strip().lower()
        if vehicle_type in _SUPPORTED_VEHICLE_TYPES:
            change_counts_by_vehicle_type[vehicle_type][counter_key] += 1
            change_counts_by_vehicle_type[vehicle_type]["total_count"] += 1

    change_summary = TransportAgentChangeSummary(
        total_vehicle_actions=len(vehicle_actions),
        keep_count=change_counts["keep_count"],
        create_count=change_counts["create_count"],
        update_count=change_counts["update_count"],
        remove_from_day_count=change_counts["remove_from_day_count"],
        by_vehicle_type=[
            TransportAgentChangeSummaryByVehicleType(
                vehicle_type=vehicle_type,
                keep_count=counts["keep_count"],
                create_count=counts["create_count"],
                update_count=counts["update_count"],
                remove_from_day_count=counts["remove_from_day_count"],
                total_count=counts["total_count"],
            )
            for vehicle_type, counts in sorted(change_counts_by_vehicle_type.items())
        ],
    )

    plan_key = _build_transport_ai_plan_key(
        planning_input_hash=planning_input.planning_input_hash,
        vehicle_actions=vehicle_actions,
        passenger_allocations=passenger_allocations,
        route_itineraries=route_itineraries,
        validation_issues=validation_issues,
    )
    return TransportAgentPlan(
        plan_key=plan_key,
        service_date=planning_input.service_date,
        route_kind=planning_input.route_kind,
        earliest_boarding_time=planning_input.limits.earliest_boarding_time,
        arrival_at_work_time=planning_input.limits.arrival_at_work_time,
        objective_summary=_build_transport_ai_plan_objective_summary(
            route_count=len(route_itineraries),
            cost_summary=cost_summary,
            validation_issue_count=len(validation_issues),
        ),
        vehicle_actions=vehicle_actions,
        passenger_allocations=passenger_allocations,
        route_itineraries=route_itineraries,
        cost_summary=cost_summary,
        change_summary=change_summary,
        validation_issues=validation_issues,
    )


def build_transport_proposal_from_agent_plan(
    db: Session,
    *,
    plan: TransportAgentPlan,
    vehicle_id_by_ref: dict[str, int],
) -> tuple[list[TransportProposalDecision], list[TransportProposalValidationIssue]]:
    decisions: list[TransportProposalDecision] = []
    issues: list[TransportProposalValidationIssue] = []
    blocking_issues_by_request_id: defaultdict[int, list[TransportProposalValidationIssue]] = defaultdict(list)
    seen_request_ids: set[int] = set()

    for validation_issue in plan.validation_issues:
        if validation_issue.request_id is None or not validation_issue.blocking:
            continue
        blocking_issues_by_request_id[validation_issue.request_id].append(validation_issue)

    for allocation in sorted(
        plan.passenger_allocations,
        key=lambda item: (item.request_id, item.pickup_order, item.vehicle_ref),
    ):
        if allocation.request_id in seen_request_ids:
            issues.append(
                _build_transport_ai_plan_issue(
                    code="transport_ai_duplicate_allocation_decision",
                    message=f"Request {allocation.request_id} appears more than once in the transport AI allocations.",
                    request_id=allocation.request_id,
                )
            )
            continue

        request_issues = blocking_issues_by_request_id.get(allocation.request_id, [])
        if request_issues:
            first_issue = request_issues[0]
            decisions.append(
                TransportProposalDecision(
                    request_id=allocation.request_id,
                    request_kind=allocation.request_kind,
                    service_date=allocation.service_date,
                    route_kind=allocation.route_kind,
                    suggested_status="pending",
                    response_message=_truncate_transport_ai_planning_text(first_issue.message, max_length=255),
                    rationale=_build_transport_ai_pending_decision_rationale(
                        request_id=allocation.request_id,
                        issue=first_issue,
                    ),
                )
            )
            seen_request_ids.add(allocation.request_id)
            continue

        vehicle_id = vehicle_id_by_ref.get(allocation.vehicle_ref)
        if vehicle_id is None:
            issues.append(
                _build_transport_ai_plan_issue(
                    code="transport_ai_vehicle_reference_unresolved",
                    message=(
                        f"The transport AI plan could not resolve vehicle reference '{allocation.vehicle_ref}' "
                        f"for request {allocation.request_id}."
                    ),
                    request_id=allocation.request_id,
                )
            )
            continue

        decisions.append(
            TransportProposalDecision(
                request_id=allocation.request_id,
                request_kind=allocation.request_kind,
                service_date=allocation.service_date,
                route_kind=allocation.route_kind,
                suggested_status="confirmed",
                vehicle_id=vehicle_id,
                response_message="Transport AI suggestion applied.",
                rationale=allocation.rationale,
            )
        )
        seen_request_ids.add(allocation.request_id)

    for request_id in sorted(blocking_issues_by_request_id):
        if request_id in seen_request_ids:
            continue

        transport_request = db.get(TransportRequest, request_id)
        if transport_request is None:
            issues.append(
                _build_transport_ai_plan_issue(
                    code="transport_ai_request_missing_for_pending_decision",
                    message=(
                        f"The transport AI plan reported validation issues for request {request_id}, but the request "
                        "could not be loaded to build a pending proposal decision."
                    ),
                    request_id=request_id,
                )
            )
            continue

        first_issue = blocking_issues_by_request_id[request_id][0]
        decisions.append(
            TransportProposalDecision(
                request_id=request_id,
                request_kind=transport_request.request_kind,
                service_date=plan.service_date,
                route_kind=plan.route_kind,
                suggested_status="pending",
                response_message=_truncate_transport_ai_planning_text(first_issue.message, max_length=255),
                rationale=_build_transport_ai_pending_decision_rationale(
                    request_id=request_id,
                    issue=first_issue,
                ),
            )
        )
        seen_request_ids.add(request_id)

    return (
        sorted(decisions, key=lambda decision: (decision.request_id, decision.suggested_status, decision.vehicle_id or 0)),
        sorted(issues, key=lambda issue: (issue.request_id or 0, issue.vehicle_id or 0, issue.code, issue.message)),
    )


def build_transport_ai_preflight_issues(
    db: Session,
    *,
    service_date: date,
    route_kind: str,
    settings_obj: Settings = settings,
    snapshot: TransportOperationalSnapshot | None = None,
    transport_settings: dict[str, object] | None = None,
) -> list[TransportAIPreflightIssue]:
    issues: list[TransportAIPreflightIssue] = []

    if route_kind not in _SUPPORTED_ROUTE_KINDS:
        return [
            _build_transport_ai_preflight_issue(
                code="route_kind_invalid",
                message=f"Route kind '{route_kind}' is not supported for Transport AI planning.",
                setting_name="route_kind",
            )
        ]

    effective_snapshot = snapshot or build_transport_operational_snapshot(
        db,
        service_date=service_date,
        route_kind=route_kind,
    )
    effective_transport_settings = transport_settings or get_transport_settings_payload(db)

    if effective_snapshot.service_date != service_date:
        issues.append(
            _build_transport_ai_preflight_issue(
                code="service_date_mismatch",
                message=(
                    "The operational snapshot does not match the requested service date "
                    f"'{service_date.isoformat()}'."
                ),
                setting_name="service_date",
            )
        )

    if effective_snapshot.route_kind != route_kind:
        issues.append(
            _build_transport_ai_preflight_issue(
                code="route_kind_mismatch",
                message=(
                    "The operational snapshot does not match the requested route kind "
                    f"'{route_kind}'."
                ),
                setting_name="route_kind",
            )
        )

    pending_requests_by_scope = _iter_pending_requests_by_scope(
        effective_snapshot,
        service_date=service_date,
    )
    eligible_requests = [
        request_row
        for request_scope in _REQUEST_SCOPE_ORDER
        for request_row in pending_requests_by_scope.get(request_scope, [])
    ]

    if not eligible_requests:
        return issues + [
            _build_transport_ai_preflight_issue(
                code="no_eligible_requests",
                message=(
                    "No pending transport requests are eligible for "
                    f"{service_date.isoformat()} on route '{route_kind}'."
                ),
                setting_name="service_date",
                blocking=False,
            )
        ]

    max_passengers_per_run = settings_obj.transport_ai_max_passengers_per_run
    if max_passengers_per_run > 0 and len(eligible_requests) > max_passengers_per_run:
        issues.append(
            _build_transport_ai_preflight_issue(
                code="max_passengers_per_run_exceeded",
                message=(
                    f"The selected date and route have {len(eligible_requests)} pending passengers, "
                    f"which exceeds the configured limit of {max_passengers_per_run}."
                ),
                setting_name="transport_ai_max_passengers_per_run",
            )
        )

    project_rows_by_name = {
        _normalize_project_name(project_row.name): project_row
        for project_row in effective_snapshot.projects
    }
    requests_by_project: dict[str, list[TransportRequestRow]] = defaultdict(list)

    for request_row in eligible_requests:
        normalized_project_name = _normalize_project_name(request_row.projeto)
        if not normalized_project_name:
            issues.append(
                _build_project_issue(
                    code="request_project_missing",
                    message=(
                        f"Passenger '{request_row.nome}' ({request_row.chave}) is missing a project "
                        "and cannot be routed."
                    ),
                )
            )
        else:
            requests_by_project[normalized_project_name].append(request_row)

        if not str(request_row.end_rua or "").strip():
            issues.append(
                _build_transport_ai_preflight_issue(
                    code="request_origin_address_missing",
                    message=(
                        f"Passenger '{request_row.nome}' ({request_row.chave}) is missing the origin "
                        "address and cannot be routed."
                    ),
                    setting_name="end_rua",
                )
            )

        if not str(request_row.zip or "").strip():
            issues.append(
                _build_transport_ai_preflight_issue(
                    code="request_origin_zip_missing",
                    message=(
                        f"Passenger '{request_row.nome}' ({request_row.chave}) is missing the origin "
                        "ZIP code and cannot be routed."
                    ),
                    setting_name="zip",
                )
            )

    for project_name in sorted(requests_by_project):
        project_row = project_rows_by_name.get(project_name)
        impacted_requests = requests_by_project[project_name]
        impacted_count = len(impacted_requests)

        if project_row is None:
            issues.append(
                _build_project_issue(
                    code="project_missing",
                    message=(
                        f"Project '{project_name}' is not available in the operational snapshot and blocks "
                        f"{impacted_count} eligible passenger(s)."
                    ),
                )
            )
            continue

        if not str(project_row.address or "").strip():
            issues.append(
                _build_project_issue(
                    code="project_destination_address_missing",
                    message=(
                        f"Project '{project_row.name}' is missing a destination address and blocks "
                        f"{impacted_count} eligible passenger(s)."
                    ),
                )
            )

        if not str(project_row.zip_code or "").strip():
            issues.append(
                _build_project_issue(
                    code="project_destination_zip_missing",
                    message=(
                        f"Project '{project_row.name}' is missing a destination ZIP code and blocks "
                        f"{impacted_count} eligible passenger(s)."
                    ),
                )
            )

        if not str(project_row.country_code or "").strip():
            issues.append(
                _build_project_issue(
                    code="project_country_missing",
                    message=(
                        f"Project '{project_row.name}' is missing a country code and blocks "
                        f"{impacted_count} eligible passenger(s)."
                    ),
                )
            )

    candidate_vehicle_types: set[str] = set()
    for request_scope in _REQUEST_SCOPE_ORDER:
        if not pending_requests_by_scope.get(request_scope):
            continue

        for vehicle_row in getattr(effective_snapshot, f"{request_scope}_vehicles"):
            if not vehicle_row.is_ready_for_allocation:
                continue
            normalized_vehicle_type = str(vehicle_row.tipo or "").strip().lower()
            if normalized_vehicle_type in _PRICE_SETTING_BY_VEHICLE_TYPE:
                candidate_vehicle_types.add(normalized_vehicle_type)

    for vehicle_type in (vehicle for vehicle in _PRICE_SETTING_BY_VEHICLE_TYPE if vehicle in candidate_vehicle_types):
        seat_setting_name = _SEAT_SETTING_BY_VEHICLE_TYPE[vehicle_type]
        if not _has_positive_number(effective_transport_settings.get(seat_setting_name)):
            issues.append(
                _build_transport_ai_preflight_issue(
                    code=f"{seat_setting_name}_invalid",
                    message=(
                        f"The default seat count for vehicle type '{vehicle_type}' must be configured "
                        "before planning routes."
                    ),
                    setting_name=seat_setting_name,
                )
            )

        price_setting_name = _PRICE_SETTING_BY_VEHICLE_TYPE[vehicle_type]
        if not _has_positive_number(effective_transport_settings.get(price_setting_name)):
            issues.append(
                _build_transport_ai_preflight_issue(
                    code=f"{price_setting_name}_missing",
                    message=(
                        f"The default price for vehicle type '{vehicle_type}' must be configured "
                        "before planning routes."
                    ),
                    setting_name=price_setting_name,
                )
            )

    return issues