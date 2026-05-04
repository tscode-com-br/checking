from __future__ import annotations

import json
import logging
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator
from zoneinfo import ZoneInfo

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool, StructuredTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.config import Settings, normalize_transport_ai_agent_mode, settings
from ..models import TransportAIRun
from ..schemas import (
    TransportAgentChangeSummary,
    TransportAgentCostSummary,
    TransportAgentPlan,
    TransportAgentPlanningInput,
    TransportAgentPartitionSolveResult,
    TransportAgentResolvedRoutePointsResult,
    TransportAgentRouteMatricesResult,
    TransportAIPreflightIssue,
    TransportProposalValidationIssue,
)
from .transport_ai_planning import (
    build_transport_agent_plan_from_solver_result,
    build_transport_agent_planning_input,
    build_transport_ai_route_matrices,
    build_transport_ai_vehicle_candidates,
    resolve_transport_ai_route_points,
    schedule_transport_ai_route_times,
    solve_transport_ai_partition,
)
from .transport_ai_llm_settings import (
    TRANSPORT_AI_LLM_DEFAULT_REASONING_EFFORT,
    TransportAILlmRuntimeSettings,
    resolve_transport_ai_llm_runtime_settings,
)
from .transport_ai_sanitization import (
    TRANSPORT_AI_REDACTED_VALUE,
    sanitize_transport_ai_raw_value,
    sanitize_transport_ai_string,
)
from .transport_route_provider import TransportRouteProvider, build_transport_route_provider

TRANSPORT_AI_PROMPT_VERSION = "transport_ai_route_planner_v1"
TRANSPORT_AI_PROMPT_TEMPLATE_VARIABLES = (
    "arrival_at_work_time",
    "directions_profile",
    "earliest_boarding_time",
    "matrix_profile",
    "planning_input_hash",
    "prompt_version",
    "route_kind",
    "route_provider",
    "service_date",
)
TRANSPORT_AI_PROMPT_FILE_PATH = (
    Path(__file__).resolve().parent.parent / "static" / "transport" / f"{TRANSPORT_AI_PROMPT_VERSION}.md"
)
TRANSPORT_AI_PREFERRED_MODEL_TEMPERATURE = 0.0
TRANSPORT_AI_LANGCHAIN_TOOL_NAMES = (
    "load_planning_input",
    "geocode_route_points",
    "build_route_matrices",
    "solve_transport_plan",
    "validate_transport_plan",
    "build_change_summary",
)
TRANSPORT_AI_RAW_RESPONSE_REDACTED_VALUE = TRANSPORT_AI_REDACTED_VALUE

logger = logging.getLogger(__name__)


class TransportAILangChainToolIssue(BaseModel):
    code: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=500)
    blocking: bool = True
    request_id: int | None = Field(default=None, ge=1)
    vehicle_id: int | None = Field(default=None, ge=1)
    setting_name: str | None = Field(default=None, max_length=80)


class TransportAILoadPlanningInputToolArgs(BaseModel):
    refresh: bool = False


class TransportAIPlanningHashToolArgs(BaseModel):
    planning_input_hash: str = Field(min_length=64, max_length=64)
    refresh: bool = False


class TransportAIPlanKeyToolArgs(BaseModel):
    plan_key: str = Field(min_length=1, max_length=120)


class TransportAIPlanningPartitionSummary(BaseModel):
    partition_key: str = Field(min_length=1, max_length=180)
    request_kind: str = Field(min_length=1, max_length=16)
    project_name: str = Field(min_length=1, max_length=120)
    request_count: int = Field(ge=0)
    candidate_vehicle_count: int = Field(ge=0)


class TransportAIRoutePointPartitionSummary(BaseModel):
    partition_key: str = Field(min_length=1, max_length=180)
    passenger_point_count: int = Field(ge=0)
    has_destination_point: bool = False


class TransportAIRouteMatrixPartitionSummary(BaseModel):
    partition_key: str = Field(min_length=1, max_length=180)
    point_count: int = Field(ge=0)
    cached: bool = False


class TransportAIVehicleActionPreview(BaseModel):
    action_key: str = Field(min_length=1, max_length=180)
    action_type: str = Field(min_length=1, max_length=32)
    service_scope: str = Field(min_length=1, max_length=16)
    vehicle_id: int | None = Field(default=None, ge=1)
    client_vehicle_key: str = Field(min_length=1, max_length=96)
    rationale: str = Field(min_length=1, max_length=500)


class TransportAILoadPlanningInputToolOutput(BaseModel):
    ok: bool
    planning_input_hash: str | None = Field(default=None, min_length=64, max_length=64)
    service_date: date | None = None
    route_kind: str | None = Field(default=None, min_length=1, max_length=32)
    total_requests: int = Field(default=0, ge=0)
    total_partitions: int = Field(default=0, ge=0)
    total_candidate_vehicles: int = Field(default=0, ge=0)
    partitions: list[TransportAIPlanningPartitionSummary] = Field(default_factory=list)
    issues: list[TransportAILangChainToolIssue] = Field(default_factory=list)


class TransportAIGeocodeRoutePointsToolOutput(BaseModel):
    ok: bool
    planning_input_hash: str | None = Field(default=None, min_length=64, max_length=64)
    provider: str | None = Field(default=None, min_length=1, max_length=40)
    total_resolved_points: int = Field(default=0, ge=0)
    partitions: list[TransportAIRoutePointPartitionSummary] = Field(default_factory=list)
    issues: list[TransportAILangChainToolIssue] = Field(default_factory=list)


class TransportAIBuildRouteMatricesToolOutput(BaseModel):
    ok: bool
    planning_input_hash: str | None = Field(default=None, min_length=64, max_length=64)
    provider: str | None = Field(default=None, min_length=1, max_length=40)
    profile: str | None = Field(default=None, min_length=1, max_length=80)
    total_matrices: int = Field(default=0, ge=0)
    partitions: list[TransportAIRouteMatrixPartitionSummary] = Field(default_factory=list)
    issues: list[TransportAILangChainToolIssue] = Field(default_factory=list)


class TransportAISolveTransportPlanToolOutput(BaseModel):
    ok: bool
    planning_input_hash: str | None = Field(default=None, min_length=64, max_length=64)
    plan_key: str | None = Field(default=None, min_length=1, max_length=120)
    total_routes: int = Field(default=0, ge=0)
    total_vehicle_actions: int = Field(default=0, ge=0)
    total_passenger_allocations: int = Field(default=0, ge=0)
    partition_algorithms: dict[str, str] = Field(default_factory=dict)
    plan: TransportAgentPlan | None = None
    issues: list[TransportAILangChainToolIssue] = Field(default_factory=list)


class TransportAIValidateTransportPlanToolOutput(BaseModel):
    ok: bool
    can_apply: bool
    planning_input_hash: str | None = Field(default=None, min_length=64, max_length=64)
    plan_key: str | None = Field(default=None, min_length=1, max_length=120)
    total_requests: int = Field(default=0, ge=0)
    allocated_request_count: int = Field(default=0, ge=0)
    request_issue_count: int = Field(default=0, ge=0)
    blocking_issue_count: int = Field(default=0, ge=0)
    warning_issue_count: int = Field(default=0, ge=0)
    unaccounted_request_ids: list[int] = Field(default_factory=list)
    issues: list[TransportAILangChainToolIssue] = Field(default_factory=list)


class TransportAIBuildChangeSummaryToolOutput(BaseModel):
    ok: bool
    plan_key: str | None = Field(default=None, min_length=1, max_length=120)
    objective_summary: str | None = Field(default=None, min_length=1, max_length=500)
    cost_summary: TransportAgentCostSummary | None = None
    change_summary: TransportAgentChangeSummary | None = None
    vehicle_action_preview: list[TransportAIVehicleActionPreview] = Field(default_factory=list)
    issues: list[TransportAILangChainToolIssue] = Field(default_factory=list)


@dataclass(slots=True)
class TransportAIAgentRunResult:
    plan: TransportAgentPlan | None
    raw_model_response_json: str | None = None
    prompt_version: str = TRANSPORT_AI_PROMPT_VERSION
    openai_model: str = ""
    attempt_count: int = 0
    temperature_requested: float | None = None
    temperature_applied: float | None = None
    temperature_omitted: bool = False
    validation_result: TransportAIValidateTransportPlanToolOutput | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class TransportAILangChainToolState:
    planning_input: TransportAgentPlanningInput | None = None
    resolved_route_points: TransportAgentResolvedRoutePointsResult | None = None
    route_matrices: TransportAgentRouteMatricesResult | None = None
    partition_solve_results: list[TransportAgentPartitionSolveResult] = field(default_factory=list)
    plan: TransportAgentPlan | None = None


@dataclass(slots=True)
class TransportAILangChainToolContext:
    db: Session
    service_date: date
    route_kind: str
    earliest_boarding_time: str
    arrival_at_work_time: str
    settings_obj: Settings = field(default_factory=lambda: settings)
    provider: TransportRouteProvider | None = None
    reference_time: datetime | None = None
    prefer_ortools: bool = True
    state: TransportAILangChainToolState = field(default_factory=TransportAILangChainToolState)


@lru_cache(maxsize=4)
def load_transport_ai_route_planner_prompt(*, prompt_path: Path | None = None) -> str:
    effective_prompt_path = prompt_path or TRANSPORT_AI_PROMPT_FILE_PATH
    prompt_text = effective_prompt_path.read_text(encoding="utf-8").strip()
    if not prompt_text:
        raise ValueError(f"Transport AI prompt file is empty: {effective_prompt_path}")
    return prompt_text


def build_transport_ai_route_planner_prompt_template(
    *,
    prompt_path: Path | None = None,
) -> ChatPromptTemplate:
    prompt_text = load_transport_ai_route_planner_prompt(prompt_path=prompt_path)
    return ChatPromptTemplate.from_messages([
        ("system", prompt_text),
    ])


def resolve_transport_ai_model_temperature(*, settings_obj: Settings = settings) -> float:
    configured_temperature = settings_obj.openai_temperature
    if configured_temperature is None:
        return TRANSPORT_AI_PREFERRED_MODEL_TEMPERATURE

    try:
        float(configured_temperature)
    except (TypeError, ValueError):
        return TRANSPORT_AI_PREFERRED_MODEL_TEMPERATURE

    return TRANSPORT_AI_PREFERRED_MODEL_TEMPERATURE


def resolve_transport_ai_agent_mode(*, settings_obj: Settings = settings) -> str:
    agent_mode = normalize_transport_ai_agent_mode(settings_obj.transport_ai_agent_mode)
    if agent_mode is None:
        raise ValueError("Transport AI agent mode must be 'agent' or 'deterministic'.")
    return agent_mode


def _build_transport_ai_tool_issue(
    *,
    code: str,
    message: str,
    blocking: bool = True,
    request_id: int | None = None,
    vehicle_id: int | None = None,
    setting_name: str | None = None,
) -> TransportAILangChainToolIssue:
    return TransportAILangChainToolIssue(
        code=code,
        message=message,
        blocking=blocking,
        request_id=request_id,
        vehicle_id=vehicle_id,
        setting_name=setting_name,
    )


def _coerce_transport_ai_tool_issue(
    issue: TransportAIPreflightIssue | TransportProposalValidationIssue | TransportAILangChainToolIssue,
) -> TransportAILangChainToolIssue:
    if isinstance(issue, TransportAILangChainToolIssue):
        return issue

    return _build_transport_ai_tool_issue(
        code=issue.code,
        message=issue.message,
        blocking=issue.blocking,
        request_id=getattr(issue, "request_id", None),
        vehicle_id=getattr(issue, "vehicle_id", None),
        setting_name=getattr(issue, "setting_name", None),
    )


def _build_transport_ai_tool_issue_from_exception(
    exc: Exception,
    *,
    code: str = "transport_ai_tool_execution_failed",
) -> TransportAILangChainToolIssue:
    return _build_transport_ai_tool_issue(code=code, message=str(exc), blocking=True)


def _has_transport_ai_blocking_issue(issues: list[TransportAILangChainToolIssue]) -> bool:
    return any(issue.blocking for issue in issues)


@contextmanager
def _transport_ai_tool_read_only_scope(db: Session) -> Iterator[None]:
    savepoint = db.begin_nested()
    try:
        yield
    finally:
        if savepoint.is_active:
            savepoint.rollback()


def _build_transport_ai_planning_partition_summaries(
    planning_input: TransportAgentPlanningInput,
) -> list[TransportAIPlanningPartitionSummary]:
    return [
        TransportAIPlanningPartitionSummary(
            partition_key=partition.partition_key,
            request_kind=partition.request_kind,
            project_name=partition.project_name,
            request_count=len(partition.requests),
            candidate_vehicle_count=len(partition.candidate_vehicles),
        )
        for partition in planning_input.partitions
    ]


def _build_transport_ai_route_point_partition_summaries(
    resolved_route_points: TransportAgentResolvedRoutePointsResult,
) -> list[TransportAIRoutePointPartitionSummary]:
    return [
        TransportAIRoutePointPartitionSummary(
            partition_key=partition.partition_key,
            passenger_point_count=len(partition.passenger_points),
            has_destination_point=partition.destination_point is not None,
        )
        for partition in resolved_route_points.partitions
    ]


def _build_transport_ai_route_matrix_partition_summaries(
    route_matrices: TransportAgentRouteMatricesResult,
) -> list[TransportAIRouteMatrixPartitionSummary]:
    return [
        TransportAIRouteMatrixPartitionSummary(
            partition_key=partition.partition_key,
            point_count=len(partition.points),
            cached=partition.cached,
        )
        for partition in route_matrices.partitions
    ]


def _clear_transport_ai_state_after_planning_input(context: TransportAILangChainToolContext) -> None:
    context.state.resolved_route_points = None
    context.state.route_matrices = None
    context.state.partition_solve_results = []
    context.state.plan = None


def _clear_transport_ai_state_after_route_points(context: TransportAILangChainToolContext) -> None:
    context.state.route_matrices = None
    context.state.partition_solve_results = []
    context.state.plan = None


def _clear_transport_ai_state_after_route_matrices(context: TransportAILangChainToolContext) -> None:
    context.state.partition_solve_results = []
    context.state.plan = None


def _require_transport_ai_planning_input(
    context: TransportAILangChainToolContext,
    *,
    planning_input_hash: str,
) -> tuple[TransportAgentPlanningInput | None, list[TransportAILangChainToolIssue]]:
    planning_input = context.state.planning_input
    if planning_input is None:
        return None, [
            _build_transport_ai_tool_issue(
                code="transport_ai_tool_state_missing",
                message="Planning input is not loaded. Call load_planning_input first.",
            )
        ]
    if planning_input.planning_input_hash != planning_input_hash:
        return None, [
            _build_transport_ai_tool_issue(
                code="transport_ai_tool_hash_mismatch",
                message=(
                    f"Planning input hash '{planning_input_hash}' does not match the loaded state "
                    f"'{planning_input.planning_input_hash}'."
                ),
            )
        ]
    return planning_input, []


def _require_transport_ai_route_points(
    context: TransportAILangChainToolContext,
    *,
    planning_input_hash: str,
) -> tuple[TransportAgentResolvedRoutePointsResult | None, list[TransportAILangChainToolIssue]]:
    route_points = context.state.resolved_route_points
    if route_points is None:
        return None, [
            _build_transport_ai_tool_issue(
                code="transport_ai_tool_state_missing",
                message="Resolved route points are not loaded. Call geocode_route_points first.",
            )
        ]
    if route_points.planning_input_hash != planning_input_hash:
        return None, [
            _build_transport_ai_tool_issue(
                code="transport_ai_tool_hash_mismatch",
                message=(
                    f"Resolved route points hash '{route_points.planning_input_hash}' does not match "
                    f"requested planning input '{planning_input_hash}'."
                ),
            )
        ]
    return route_points, []


def _require_transport_ai_route_matrices(
    context: TransportAILangChainToolContext,
    *,
    planning_input_hash: str,
) -> tuple[TransportAgentRouteMatricesResult | None, list[TransportAILangChainToolIssue]]:
    route_matrices = context.state.route_matrices
    if route_matrices is None:
        return None, [
            _build_transport_ai_tool_issue(
                code="transport_ai_tool_state_missing",
                message="Route matrices are not loaded. Call build_route_matrices first.",
            )
        ]
    if route_matrices.planning_input_hash != planning_input_hash:
        return None, [
            _build_transport_ai_tool_issue(
                code="transport_ai_tool_hash_mismatch",
                message=(
                    f"Route matrices hash '{route_matrices.planning_input_hash}' does not match "
                    f"requested planning input '{planning_input_hash}'."
                ),
            )
        ]
    return route_matrices, []


def _require_transport_ai_plan(
    context: TransportAILangChainToolContext,
    *,
    plan_key: str,
) -> tuple[TransportAgentPlan | None, list[TransportAILangChainToolIssue]]:
    plan = context.state.plan
    if plan is None:
        return None, [
            _build_transport_ai_tool_issue(
                code="transport_ai_tool_plan_missing",
                message="No transport AI plan is loaded. Call solve_transport_plan first.",
            )
        ]
    if plan.plan_key != plan_key:
        return None, [
            _build_transport_ai_tool_issue(
                code="transport_ai_tool_plan_key_mismatch",
                message=f"Plan key '{plan_key}' does not match the loaded plan '{plan.plan_key}'.",
            )
        ]
    return plan, []


def _build_transport_ai_vehicle_refs_from_plan(plan: TransportAgentPlan) -> set[str]:
    vehicle_refs: set[str] = set()
    for action in plan.vehicle_actions:
        if action.before is not None and isinstance(action.before.get("vehicle_ref"), str):
            vehicle_refs.add(str(action.before["vehicle_ref"]))
        if isinstance(action.after.get("vehicle_ref"), str):
            vehicle_refs.add(str(action.after["vehicle_ref"]))
        if action.vehicle_id is not None:
            vehicle_refs.add(f"existing:{action.vehicle_id}")
        if action.client_vehicle_key.startswith("existing:"):
            vehicle_refs.add(action.client_vehicle_key)
        else:
            vehicle_refs.add(f"new:{action.client_vehicle_key}")
    return vehicle_refs


def _validate_transport_ai_plan_deterministically(
    *,
    planning_input: TransportAgentPlanningInput,
    plan: TransportAgentPlan,
) -> TransportAIValidateTransportPlanToolOutput:
    issues = [_coerce_transport_ai_tool_issue(issue) for issue in plan.validation_issues]

    if plan.service_date != planning_input.service_date:
        issues.append(
            _build_transport_ai_tool_issue(
                code="transport_ai_plan_service_date_mismatch",
                message=(
                    f"Plan service date '{plan.service_date.isoformat()}' does not match planning input "
                    f"'{planning_input.service_date.isoformat()}'."
                ),
            )
        )
    if plan.route_kind != planning_input.route_kind:
        issues.append(
            _build_transport_ai_tool_issue(
                code="transport_ai_plan_route_kind_mismatch",
                message=(
                    f"Plan route kind '{plan.route_kind}' does not match planning input "
                    f"'{planning_input.route_kind}'."
                ),
            )
        )
    if plan.earliest_boarding_time != planning_input.limits.earliest_boarding_time:
        issues.append(
            _build_transport_ai_tool_issue(
                code="transport_ai_plan_earliest_boarding_mismatch",
                message=(
                    f"Plan earliest boarding time '{plan.earliest_boarding_time}' does not match planning input "
                    f"'{planning_input.limits.earliest_boarding_time}'."
                ),
            )
        )
    if plan.arrival_at_work_time != planning_input.limits.arrival_at_work_time:
        issues.append(
            _build_transport_ai_tool_issue(
                code="transport_ai_plan_arrival_time_mismatch",
                message=(
                    f"Plan arrival time '{plan.arrival_at_work_time}' does not match planning input "
                    f"'{planning_input.limits.arrival_at_work_time}'."
                ),
            )
        )

    expected_request_ids = {
        request.request_id
        for partition in planning_input.partitions
        for request in partition.requests
    }
    allocation_counter = Counter(allocation.request_id for allocation in plan.passenger_allocations)
    request_ids_with_plan_issues = {
        issue.request_id
        for issue in plan.validation_issues
        if issue.request_id is not None
    }

    duplicate_allocation_request_ids = sorted(
        request_id
        for request_id, allocation_count in allocation_counter.items()
        if allocation_count > 1
    )
    for request_id in duplicate_allocation_request_ids:
        issues.append(
            _build_transport_ai_tool_issue(
                code="transport_ai_plan_duplicate_allocation",
                message=f"Request '{request_id}' appears more than once in passenger allocations.",
                request_id=request_id,
            )
        )

    unexpected_allocation_request_ids = sorted(
        request_id for request_id in allocation_counter if request_id not in expected_request_ids
    )
    for request_id in unexpected_allocation_request_ids:
        issues.append(
            _build_transport_ai_tool_issue(
                code="transport_ai_plan_unknown_request_allocation",
                message=f"Request '{request_id}' is not present in the planning input but appears in the plan.",
                request_id=request_id,
            )
        )

    unaccounted_request_ids = sorted(
        request_id
        for request_id in expected_request_ids
        if request_id not in allocation_counter and request_id not in request_ids_with_plan_issues
    )
    for request_id in unaccounted_request_ids:
        issues.append(
            _build_transport_ai_tool_issue(
                code="transport_ai_plan_request_unaccounted_for",
                message=(
                    f"Request '{request_id}' is neither allocated nor represented by a validation issue."
                ),
                request_id=request_id,
            )
        )

    valid_vehicle_refs = _build_transport_ai_vehicle_refs_from_plan(plan)
    for allocation in plan.passenger_allocations:
        if allocation.vehicle_ref not in valid_vehicle_refs:
            issues.append(
                _build_transport_ai_tool_issue(
                    code="transport_ai_plan_unknown_vehicle_ref",
                    message=(
                        f"Allocation for request '{allocation.request_id}' references unknown vehicle "
                        f"'{allocation.vehicle_ref}'."
                    ),
                    request_id=allocation.request_id,
                )
            )

    for itinerary in plan.route_itineraries:
        if itinerary.vehicle_ref not in valid_vehicle_refs:
            issues.append(
                _build_transport_ai_tool_issue(
                    code="transport_ai_plan_itinerary_vehicle_ref_unknown",
                    message=(
                        f"Itinerary '{itinerary.route_key}' references unknown vehicle '{itinerary.vehicle_ref}'."
                    ),
                    vehicle_id=itinerary.vehicle_id,
                )
            )
        if not itinerary.stops:
            issues.append(
                _build_transport_ai_tool_issue(
                    code="transport_ai_plan_itinerary_missing_stops",
                    message=f"Itinerary '{itinerary.route_key}' does not contain any stops.",
                    vehicle_id=itinerary.vehicle_id,
                )
            )
            continue
        if itinerary.stops[-1].stop_type != "destination":
            issues.append(
                _build_transport_ai_tool_issue(
                    code="transport_ai_plan_itinerary_missing_destination",
                    message=f"Itinerary '{itinerary.route_key}' must end with a destination stop.",
                    vehicle_id=itinerary.vehicle_id,
                )
            )

    blocking_issue_count = sum(1 for issue in issues if issue.blocking)
    warning_issue_count = len(issues) - blocking_issue_count
    return TransportAIValidateTransportPlanToolOutput(
        ok=blocking_issue_count == 0,
        can_apply=blocking_issue_count == 0,
        planning_input_hash=planning_input.planning_input_hash,
        plan_key=plan.plan_key,
        total_requests=len(expected_request_ids),
        allocated_request_count=len(allocation_counter),
        request_issue_count=len(request_ids_with_plan_issues),
        blocking_issue_count=blocking_issue_count,
        warning_issue_count=warning_issue_count,
        unaccounted_request_ids=unaccounted_request_ids,
        issues=issues,
    )


def _build_transport_ai_change_summary_output(
    *,
    plan: TransportAgentPlan,
) -> TransportAIBuildChangeSummaryToolOutput:
    issues = [_coerce_transport_ai_tool_issue(issue) for issue in plan.validation_issues]
    return TransportAIBuildChangeSummaryToolOutput(
        ok=not _has_transport_ai_blocking_issue(issues),
        plan_key=plan.plan_key,
        objective_summary=plan.objective_summary,
        cost_summary=plan.cost_summary,
        change_summary=plan.change_summary,
        vehicle_action_preview=[
            TransportAIVehicleActionPreview(
                action_key=action.action_key,
                action_type=action.action_type,
                service_scope=action.service_scope,
                vehicle_id=action.vehicle_id,
                client_vehicle_key=action.client_vehicle_key,
                rationale=action.rationale,
            )
            for action in plan.vehicle_actions[:10]
        ],
        issues=issues,
    )


def _run_load_planning_input_tool(
    context: TransportAILangChainToolContext,
    *,
    refresh: bool,
) -> TransportAILoadPlanningInputToolOutput:
    try:
        if context.state.planning_input is None or refresh:
            context.state.planning_input = build_transport_agent_planning_input(
                context.db,
                service_date=context.service_date,
                route_kind=context.route_kind,
                earliest_boarding_time=context.earliest_boarding_time,
                arrival_at_work_time=context.arrival_at_work_time,
                settings_obj=context.settings_obj,
            )
            _clear_transport_ai_state_after_planning_input(context)

        planning_input = context.state.planning_input
        issues = [_coerce_transport_ai_tool_issue(issue) for issue in planning_input.preflight_issues]
        return TransportAILoadPlanningInputToolOutput(
            ok=not _has_transport_ai_blocking_issue(issues),
            planning_input_hash=planning_input.planning_input_hash,
            service_date=planning_input.service_date,
            route_kind=planning_input.route_kind,
            total_requests=planning_input.total_requests,
            total_partitions=len(planning_input.partitions),
            total_candidate_vehicles=planning_input.total_candidate_vehicles,
            partitions=_build_transport_ai_planning_partition_summaries(planning_input),
            issues=issues,
        )
    except Exception as exc:
        return TransportAILoadPlanningInputToolOutput(
            ok=False,
            issues=[_build_transport_ai_tool_issue_from_exception(exc)],
        )


def _run_geocode_route_points_tool(
    context: TransportAILangChainToolContext,
    *,
    planning_input_hash: str,
    refresh: bool,
) -> TransportAIGeocodeRoutePointsToolOutput:
    planning_input, planning_input_issues = _require_transport_ai_planning_input(
        context,
        planning_input_hash=planning_input_hash,
    )
    if planning_input is None:
        return TransportAIGeocodeRoutePointsToolOutput(
            ok=False,
            planning_input_hash=planning_input_hash,
            issues=planning_input_issues,
        )

    try:
        if context.state.resolved_route_points is None or refresh:
            with _transport_ai_tool_read_only_scope(context.db):
                context.state.resolved_route_points = resolve_transport_ai_route_points(
                    context.db,
                    planning_input=planning_input,
                    settings_obj=context.settings_obj,
                    provider=context.provider,
                    reference_time=context.reference_time,
                )
            _clear_transport_ai_state_after_route_points(context)

        resolved_route_points = context.state.resolved_route_points
        issues = [_coerce_transport_ai_tool_issue(issue) for issue in resolved_route_points.issues]
        return TransportAIGeocodeRoutePointsToolOutput(
            ok=not _has_transport_ai_blocking_issue(issues),
            planning_input_hash=resolved_route_points.planning_input_hash,
            provider=resolved_route_points.provider,
            total_resolved_points=resolved_route_points.total_resolved_points,
            partitions=_build_transport_ai_route_point_partition_summaries(resolved_route_points),
            issues=issues,
        )
    except Exception as exc:
        return TransportAIGeocodeRoutePointsToolOutput(
            ok=False,
            planning_input_hash=planning_input_hash,
            issues=[_build_transport_ai_tool_issue_from_exception(exc)],
        )


def _run_build_route_matrices_tool(
    context: TransportAILangChainToolContext,
    *,
    planning_input_hash: str,
    refresh: bool,
) -> TransportAIBuildRouteMatricesToolOutput:
    route_points, route_point_issues = _require_transport_ai_route_points(
        context,
        planning_input_hash=planning_input_hash,
    )
    if route_points is None:
        return TransportAIBuildRouteMatricesToolOutput(
            ok=False,
            planning_input_hash=planning_input_hash,
            issues=route_point_issues,
        )

    try:
        if context.state.route_matrices is None or refresh:
            with _transport_ai_tool_read_only_scope(context.db):
                context.state.route_matrices = build_transport_ai_route_matrices(
                    context.db,
                    resolved_route_points=route_points,
                    settings_obj=context.settings_obj,
                    provider=context.provider,
                    profile=context.settings_obj.mapbox_matrix_profile,
                    reference_time=context.reference_time,
                )
            _clear_transport_ai_state_after_route_matrices(context)

        route_matrices = context.state.route_matrices
        issues = [_coerce_transport_ai_tool_issue(issue) for issue in route_matrices.issues]
        return TransportAIBuildRouteMatricesToolOutput(
            ok=not _has_transport_ai_blocking_issue(issues),
            planning_input_hash=route_matrices.planning_input_hash,
            provider=route_matrices.provider,
            profile=route_matrices.profile,
            total_matrices=route_matrices.total_matrices,
            partitions=_build_transport_ai_route_matrix_partition_summaries(route_matrices),
            issues=issues,
        )
    except Exception as exc:
        return TransportAIBuildRouteMatricesToolOutput(
            ok=False,
            planning_input_hash=planning_input_hash,
            issues=[_build_transport_ai_tool_issue_from_exception(exc)],
        )


def _run_solve_transport_plan_tool(
    context: TransportAILangChainToolContext,
    *,
    planning_input_hash: str,
    refresh: bool,
) -> TransportAISolveTransportPlanToolOutput:
    planning_input, planning_input_issues = _require_transport_ai_planning_input(
        context,
        planning_input_hash=planning_input_hash,
    )
    if planning_input is None:
        return TransportAISolveTransportPlanToolOutput(
            ok=False,
            planning_input_hash=planning_input_hash,
            issues=planning_input_issues,
        )

    route_matrices, route_matrix_issues = _require_transport_ai_route_matrices(
        context,
        planning_input_hash=planning_input_hash,
    )
    if route_matrices is None:
        return TransportAISolveTransportPlanToolOutput(
            ok=False,
            planning_input_hash=planning_input_hash,
            issues=route_matrix_issues,
        )

    try:
        if context.state.plan is None or refresh:
            vehicle_candidates = build_transport_ai_vehicle_candidates(planning_input=planning_input)
            vehicle_candidates_by_partition_key = {
                partition.partition_key: partition
                for partition in vehicle_candidates.partitions
            }
            partition_solve_results: list[TransportAgentPartitionSolveResult] = []
            for route_matrix_partition in route_matrices.partitions:
                candidate_partition = vehicle_candidates_by_partition_key.get(route_matrix_partition.partition_key)
                if candidate_partition is None:
                    continue

                partition_result = solve_transport_ai_partition(
                    planning_input=planning_input,
                    route_matrix_partition=route_matrix_partition,
                    vehicle_candidates_partition=candidate_partition,
                    prefer_ortools=context.prefer_ortools,
                )
                partition_solve_results.append(
                    schedule_transport_ai_route_times(
                        planning_input=planning_input,
                        route_matrix_partition=route_matrix_partition,
                        partition_solve_result=partition_result,
                    )
                )

            context.state.partition_solve_results = partition_solve_results
            context.state.plan = build_transport_agent_plan_from_solver_result(
                planning_input=planning_input,
                route_matrices_result=route_matrices,
                partition_solve_results=partition_solve_results,
            )

        plan = context.state.plan
        issues = [_coerce_transport_ai_tool_issue(issue) for issue in plan.validation_issues]
        return TransportAISolveTransportPlanToolOutput(
            ok=not _has_transport_ai_blocking_issue(issues),
            planning_input_hash=planning_input.planning_input_hash,
            plan_key=plan.plan_key,
            total_routes=len(plan.route_itineraries),
            total_vehicle_actions=len(plan.vehicle_actions),
            total_passenger_allocations=len(plan.passenger_allocations),
            partition_algorithms={
                result.partition_key: result.algorithm_used
                for result in context.state.partition_solve_results
            },
            plan=plan,
            issues=issues,
        )
    except Exception as exc:
        return TransportAISolveTransportPlanToolOutput(
            ok=False,
            planning_input_hash=planning_input_hash,
            issues=[_build_transport_ai_tool_issue_from_exception(exc)],
        )


def _run_validate_transport_plan_tool(
    context: TransportAILangChainToolContext,
    *,
    plan_key: str,
) -> TransportAIValidateTransportPlanToolOutput:
    plan, plan_issues = _require_transport_ai_plan(context, plan_key=plan_key)
    if plan is None:
        return TransportAIValidateTransportPlanToolOutput(
            ok=False,
            can_apply=False,
            plan_key=plan_key,
            issues=plan_issues,
        )

    planning_input = context.state.planning_input
    if planning_input is None:
        return TransportAIValidateTransportPlanToolOutput(
            ok=False,
            can_apply=False,
            plan_key=plan_key,
            issues=[
                _build_transport_ai_tool_issue(
                    code="transport_ai_tool_state_missing",
                    message="Planning input is not loaded. Call load_planning_input first.",
                )
            ],
        )

    try:
        return _validate_transport_ai_plan_deterministically(
            planning_input=planning_input,
            plan=plan,
        )
    except Exception as exc:
        return TransportAIValidateTransportPlanToolOutput(
            ok=False,
            can_apply=False,
            planning_input_hash=planning_input.planning_input_hash,
            plan_key=plan_key,
            issues=[_build_transport_ai_tool_issue_from_exception(exc)],
        )


def _run_build_change_summary_tool(
    context: TransportAILangChainToolContext,
    *,
    plan_key: str,
) -> TransportAIBuildChangeSummaryToolOutput:
    plan, plan_issues = _require_transport_ai_plan(context, plan_key=plan_key)
    if plan is None:
        return TransportAIBuildChangeSummaryToolOutput(
            ok=False,
            plan_key=plan_key,
            issues=plan_issues,
        )

    try:
        return _build_transport_ai_change_summary_output(plan=plan)
    except Exception as exc:
        return TransportAIBuildChangeSummaryToolOutput(
            ok=False,
            plan_key=plan_key,
            issues=[_build_transport_ai_tool_issue_from_exception(exc)],
        )


def build_transport_ai_langchain_tools(
    *,
    context: TransportAILangChainToolContext,
) -> list[BaseTool]:
    def load_planning_input(refresh: bool = False) -> dict[str, Any]:
        return _run_load_planning_input_tool(context, refresh=refresh).model_dump(mode="json")

    def geocode_route_points(planning_input_hash: str, refresh: bool = False) -> dict[str, Any]:
        return _run_geocode_route_points_tool(
            context,
            planning_input_hash=planning_input_hash,
            refresh=refresh,
        ).model_dump(mode="json")

    def build_route_matrices(planning_input_hash: str, refresh: bool = False) -> dict[str, Any]:
        return _run_build_route_matrices_tool(
            context,
            planning_input_hash=planning_input_hash,
            refresh=refresh,
        ).model_dump(mode="json")

    def solve_transport_plan(planning_input_hash: str, refresh: bool = False) -> dict[str, Any]:
        return _run_solve_transport_plan_tool(
            context,
            planning_input_hash=planning_input_hash,
            refresh=refresh,
        ).model_dump(mode="json")

    def validate_transport_plan(plan_key: str) -> dict[str, Any]:
        return _run_validate_transport_plan_tool(context, plan_key=plan_key).model_dump(mode="json")

    def build_change_summary(plan_key: str) -> dict[str, Any]:
        return _run_build_change_summary_tool(context, plan_key=plan_key).model_dump(mode="json")

    return [
        StructuredTool.from_function(
            func=load_planning_input,
            name="load_planning_input",
            description=(
                "Build the canonical deterministic planning input for the current run. "
                "Input: optional refresh boolean. Output: planning_input_hash, partition summaries, "
                "request totals, candidate vehicle totals, and structured preflight issues."
            ),
            args_schema=TransportAILoadPlanningInputToolArgs,
        ),
        StructuredTool.from_function(
            func=geocode_route_points,
            name="geocode_route_points",
            description=(
                "Resolve passenger origins and project destinations with the configured route provider "
                "without persisting route-point cache writes. Input: planning_input_hash and optional refresh. "
                "Output: provider name, resolved point totals, partition counts, and structured issues."
            ),
            args_schema=TransportAIPlanningHashToolArgs,
        ),
        StructuredTool.from_function(
            func=build_route_matrices,
            name="build_route_matrices",
            description=(
                "Build deterministic route matrices for the current planning input without persisting matrix cache writes. "
                "Input: planning_input_hash and optional refresh. Output: provider/profile, matrix counts, "
                "partition summaries, and structured issues."
            ),
            args_schema=TransportAIPlanningHashToolArgs,
        ),
        StructuredTool.from_function(
            func=solve_transport_plan,
            name="solve_transport_plan",
            description=(
                "Run the deterministic transport planning pipeline over the loaded matrices, including vehicle candidate "
                "selection, per-partition solving, backward scheduling, and consolidated plan assembly. "
                "Input: planning_input_hash and optional refresh. Output: the structured TransportAgentPlan, per-partition "
                "algorithm summaries, and structured validation issues."
            ),
            args_schema=TransportAIPlanningHashToolArgs,
        ),
        StructuredTool.from_function(
            func=validate_transport_plan,
            name="validate_transport_plan",
            description=(
                "Run deterministic consistency checks against the in-memory plan. Input: plan_key. Output: coverage "
                "counts, apply readiness, unaccounted request ids, and structured validation issues."
            ),
            args_schema=TransportAIPlanKeyToolArgs,
        ),
        StructuredTool.from_function(
            func=build_change_summary,
            name="build_change_summary",
            description=(
                "Return a compact review payload for the current plan. Input: plan_key. Output: objective summary, "
                "cost summary, change summary, a short vehicle-action preview, and structured issues."
            ),
            args_schema=TransportAIPlanKeyToolArgs,
        ),
    ]


def build_transport_ai_chat_model(
    *,
    model_name: str,
    settings_obj: Settings = settings,
    temperature: float | None,
) -> ChatOpenAI:
    if not settings_obj.openai_api_key:
        raise ValueError("OpenAI API key is not configured for the transport AI agent.")

    return build_transport_ai_chat_model_for_provider(
        runtime_settings=TransportAILlmRuntimeSettings(
            provider="openai",
            model_name=model_name,
            reasoning_effort=TRANSPORT_AI_LLM_DEFAULT_REASONING_EFFORT,
            api_key=settings_obj.openai_api_key,
            base_url=None,
        ),
        settings_obj=settings_obj,
        temperature=temperature,
    )


def build_transport_ai_chat_model_for_provider(
    *,
    runtime_settings: TransportAILlmRuntimeSettings,
    settings_obj: Settings = settings,
    temperature: float | None,
    include_reasoning_effort: bool = True,
) -> ChatOpenAI:
    provider = str(runtime_settings.provider or "").strip().lower()
    if provider not in {"openai", "deepseek"}:
        raise ValueError(f"Unsupported transport AI LLM provider: {runtime_settings.provider!r}")

    model_kwargs: dict[str, Any] = {
        "api_key": runtime_settings.api_key,
        "model": runtime_settings.model_name,
        "timeout": settings_obj.openai_timeout_seconds,
        "max_retries": settings_obj.openai_max_retries,
    }
    if include_reasoning_effort:
        model_kwargs["model_kwargs"] = (
            {"reasoning": {"effort": runtime_settings.reasoning_effort}}
            if provider == "openai"
            else {"reasoning_effort": runtime_settings.reasoning_effort}
        )
    if provider == "deepseek" and runtime_settings.base_url:
        model_kwargs["base_url"] = runtime_settings.base_url
    if temperature is not None:
        model_kwargs["temperature"] = temperature
    return ChatOpenAI(**model_kwargs)


def _transport_ai_now(*, settings_obj: Settings = settings) -> datetime:
    return datetime.now(ZoneInfo(settings_obj.tz_name))


def _transport_ai_json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _sanitize_transport_ai_string(value: str, *, settings_obj: Settings = settings) -> str:
    return sanitize_transport_ai_string(value, settings_obj=settings_obj)


def _sanitize_transport_ai_raw_value(value: Any, *, settings_obj: Settings = settings) -> Any:
    return sanitize_transport_ai_raw_value(value, settings_obj=settings_obj)


def _sanitize_transport_ai_string_with_runtime_secrets(
    value: str,
    *,
    settings_obj: Settings = settings,
    runtime_secret_literals: tuple[str, ...] = (),
) -> str:
    return sanitize_transport_ai_string(
        value,
        settings_obj=settings_obj,
        extra_literal_secrets=runtime_secret_literals,
    )


def _sanitize_transport_ai_raw_value_with_runtime_secrets(
    value: Any,
    *,
    settings_obj: Settings = settings,
    runtime_secret_literals: tuple[str, ...] = (),
) -> Any:
    return sanitize_transport_ai_raw_value(
        value,
        settings_obj=settings_obj,
        extra_literal_secrets=runtime_secret_literals,
    )


def _build_transport_ai_raw_model_response_json(
    *,
    raw_response: Any,
    parsing_error: Exception | None,
    model_name: str,
    attempt_number: int,
    temperature_requested: float | None,
    temperature_applied: float | None,
    temperature_omitted: bool,
    settings_obj: Settings = settings,
    runtime_secret_literals: tuple[str, ...] = (),
) -> str | None:
    if raw_response is None and parsing_error is None:
        return None

    payload = {
        "attempt": attempt_number,
        "model": model_name,
        "temperature_requested": temperature_requested,
        "temperature_applied": temperature_applied,
        "temperature_omitted": temperature_omitted,
        "raw_response": _sanitize_transport_ai_raw_value_with_runtime_secrets(
            raw_response,
            settings_obj=settings_obj,
            runtime_secret_literals=runtime_secret_literals,
        ),
        "parsing_error": _sanitize_transport_ai_raw_value_with_runtime_secrets(
            parsing_error,
            settings_obj=settings_obj,
            runtime_secret_literals=runtime_secret_literals,
        ),
    }
    return _transport_ai_json_dumps(payload)


def _should_resolve_transport_ai_run_llm_runtime_settings(*, run: TransportAIRun, model: Any | None) -> bool:
    if model is None:
        return True
    return any(
        str(value or "").strip()
        for value in (
            run.llm_provider,
            run.llm_model,
            run.llm_reasoning_effort,
        )
    )


def _resolve_transport_ai_run_llm_runtime_settings(
    *,
    db: Session,
    run: TransportAIRun,
    settings_obj: Settings = settings,
) -> TransportAILlmRuntimeSettings:
    persisted_runtime_settings = resolve_transport_ai_llm_runtime_settings(db, settings_obj=settings_obj)
    provider = str(run.llm_provider or persisted_runtime_settings.provider).strip().lower() or persisted_runtime_settings.provider
    model_name = (
        str(run.llm_model or run.openai_model or persisted_runtime_settings.model_name).strip()
        or persisted_runtime_settings.model_name
    )
    reasoning_effort = (
        str(run.llm_reasoning_effort or persisted_runtime_settings.reasoning_effort).strip().lower()
        or persisted_runtime_settings.reasoning_effort
    )
    base_url = persisted_runtime_settings.base_url if provider == persisted_runtime_settings.provider else None
    return TransportAILlmRuntimeSettings(
        provider=provider,
        model_name=model_name,
        reasoning_effort=reasoning_effort,
        api_key=persisted_runtime_settings.api_key,
        base_url=base_url,
    )


def _truncate_transport_ai_error_message(message: str | None) -> str | None:
    if message is None:
        return None
    normalized = message.strip()
    if len(normalized) <= 1000:
        return normalized
    return f"{normalized[:997]}..."


def _update_transport_ai_run_status(
    *,
    db: Session,
    run: TransportAIRun,
    status: str,
    settings_obj: Settings = settings,
    error_code: str | None = None,
    error_message: str | None = None,
    completed: bool,
) -> None:
    now = _transport_ai_now(settings_obj=settings_obj)
    run.status = status
    run.error_code = error_code
    run.error_message = _truncate_transport_ai_error_message(error_message)
    run.updated_at = now
    run.completed_at = now if completed else None
    db.add(run)
    db.flush()


def _sync_transport_ai_run_planning_input(
    *,
    db: Session,
    run: TransportAIRun,
    planning_input: TransportAgentPlanningInput,
    settings_obj: Settings = settings,
) -> None:
    run.planning_input_json = _transport_ai_json_dumps(planning_input.model_dump(mode="json"))
    run.planning_input_hash = planning_input.planning_input_hash
    if planning_input.preflight_issues:
        run.preflight_issues_json = _transport_ai_json_dumps(
            [issue.model_dump(mode="json") for issue in planning_input.preflight_issues]
        )
    else:
        run.preflight_issues_json = None
    run.updated_at = _transport_ai_now(settings_obj=settings_obj)
    db.add(run)
    db.flush()


def _maybe_seed_transport_ai_context_from_run(
    *,
    context: TransportAILangChainToolContext,
    run: TransportAIRun,
) -> None:
    planning_input_json = (run.planning_input_json or "").strip()
    if not planning_input_json:
        return

    try:
        planning_input = TransportAgentPlanningInput.model_validate_json(planning_input_json)
    except Exception:
        return

    if planning_input.planning_input_hash != run.planning_input_hash:
        return

    context.state.planning_input = planning_input


def _format_transport_ai_tool_issues(tool_name: str, issues: list[Any]) -> str:
    issue_messages: list[str] = []
    for issue in issues[:3]:
        if isinstance(issue, dict):
            message = issue.get("message")
        else:
            message = getattr(issue, "message", None)
        if message:
            issue_messages.append(str(message).strip())
    if not issue_messages:
        return f"Tool '{tool_name}' failed without a structured issue payload."
    return f"Tool '{tool_name}' failed: {' | '.join(issue_messages)}"


def _execute_transport_ai_tool_sequence(
    *,
    context: TransportAILangChainToolContext,
) -> dict[str, dict[str, Any]]:
    tools_by_name = {
        tool.name: tool
        for tool in build_transport_ai_langchain_tools(context=context)
    }

    load_result = tools_by_name["load_planning_input"].invoke({})
    planning_input_hash = load_result.get("planning_input_hash")
    if not planning_input_hash:
        raise ValueError(_format_transport_ai_tool_issues("load_planning_input", load_result.get("issues", [])))

    geocode_result = tools_by_name["geocode_route_points"].invoke({"planning_input_hash": planning_input_hash})
    route_matrix_result = tools_by_name["build_route_matrices"].invoke({"planning_input_hash": planning_input_hash})
    solve_result = tools_by_name["solve_transport_plan"].invoke({"planning_input_hash": planning_input_hash})
    plan_key = solve_result.get("plan_key")
    if not plan_key or context.state.plan is None:
        raise ValueError(_format_transport_ai_tool_issues("solve_transport_plan", solve_result.get("issues", [])))

    validate_result = tools_by_name["validate_transport_plan"].invoke({"plan_key": plan_key})
    change_summary_result = tools_by_name["build_change_summary"].invoke({"plan_key": plan_key})

    return {
        "load_planning_input": load_result,
        "geocode_route_points": geocode_result,
        "build_route_matrices": route_matrix_result,
        "solve_transport_plan": solve_result,
        "validate_transport_plan": validate_result,
        "build_change_summary": change_summary_result,
    }


def _execute_transport_ai_deterministic_plan(
    *,
    context: TransportAILangChainToolContext,
) -> tuple[TransportAgentPlan, TransportAIValidateTransportPlanToolOutput]:
    load_result = _run_load_planning_input_tool(context, refresh=False)
    planning_input_hash = load_result.planning_input_hash
    if not planning_input_hash:
        raise ValueError(_format_transport_ai_tool_issues("load_planning_input", load_result.issues))

    _run_geocode_route_points_tool(
        context,
        planning_input_hash=planning_input_hash,
        refresh=False,
    )
    _run_build_route_matrices_tool(
        context,
        planning_input_hash=planning_input_hash,
        refresh=False,
    )
    solve_result = _run_solve_transport_plan_tool(
        context,
        planning_input_hash=planning_input_hash,
        refresh=False,
    )
    if solve_result.plan is None or not solve_result.plan_key:
        raise ValueError(_format_transport_ai_tool_issues("solve_transport_plan", solve_result.issues))

    validation_result = _run_validate_transport_plan_tool(
        context,
        plan_key=solve_result.plan_key,
    )
    return solve_result.plan, validation_result


def _build_transport_ai_deterministic_validation_failure_message(
    validation_result: TransportAIValidateTransportPlanToolOutput,
) -> str:
    issue_messages = [issue.message for issue in validation_result.issues[:5]]
    if not issue_messages:
        return "Deterministic transport AI execution produced an invalid plan."
    return f"Deterministic transport AI execution produced an invalid plan: {' | '.join(issue_messages)}"


def _build_transport_ai_retry_feedback_from_validation(
    validation_result: TransportAIValidateTransportPlanToolOutput,
) -> str:
    issue_messages = [issue.message for issue in validation_result.issues[:5]]
    if not issue_messages:
        return (
            "The previous response failed deterministic validation. Return a corrected TransportAgentPlan "
            "using only the authoritative execution context."
        )
    return (
        "The previous response failed deterministic validation: "
        f"{' | '.join(issue_messages)}. Return a corrected TransportAgentPlan using only the authoritative execution context."
    )


def _build_transport_ai_retry_feedback_from_parsing_error(parsing_error: Exception) -> str:
    return (
        "The previous response did not parse into TransportAgentPlan: "
        f"{parsing_error}. Return only a valid TransportAgentPlan."
    )


def _build_transport_ai_runtime_messages(
    *,
    context: TransportAILangChainToolContext,
    tool_results: dict[str, dict[str, Any]],
    retry_feedback: str | None = None,
) -> list[BaseMessage]:
    planning_input = context.state.planning_input
    if planning_input is None:
        raise ValueError("Planning input is not loaded for the transport AI runtime.")

    prompt_template = build_transport_ai_route_planner_prompt_template()
    route_provider = getattr(context.provider, "provider", context.settings_obj.transport_ai_route_provider)
    base_messages = list(
        prompt_template.format_messages(
            prompt_version=TRANSPORT_AI_PROMPT_VERSION,
            service_date=context.service_date.isoformat(),
            route_kind=context.route_kind,
            earliest_boarding_time=context.earliest_boarding_time,
            arrival_at_work_time=context.arrival_at_work_time,
            route_provider=route_provider,
            matrix_profile=context.settings_obj.mapbox_matrix_profile,
            directions_profile=context.settings_obj.mapbox_directions_profile,
            planning_input_hash=planning_input.planning_input_hash,
        )
    )

    runtime_payload = {
        "instructions": {
            "return_schema": "TransportAgentPlan",
            "authoritative_source": "Use only this deterministic execution context.",
            "preserve_candidate_plan_when_valid": True,
        },
        "execution_context": tool_results,
    }
    base_messages.append(HumanMessage(content=_transport_ai_json_dumps(runtime_payload)))
    if retry_feedback:
        base_messages.append(HumanMessage(content=retry_feedback))
    return base_messages


def _invoke_transport_ai_structured_model(
    *,
    model: Any,
    messages: list[BaseMessage],
) -> tuple[TransportAgentPlan | None, Any, Exception | None]:
    structured_model = model.with_structured_output(
        TransportAgentPlan,
        method="function_calling",
        include_raw=True,
    )
    response = structured_model.invoke(messages)

    raw_response = None
    parsing_error = None
    parsed_payload: Any = response
    if isinstance(response, dict) and {"raw", "parsed", "parsing_error"}.issubset(response):
        raw_response = response.get("raw")
        parsing_error = response.get("parsing_error")
        parsed_payload = response.get("parsed")

    if parsed_payload is None:
        return None, raw_response, parsing_error
    if isinstance(parsed_payload, TransportAgentPlan):
        return parsed_payload, raw_response, parsing_error
    return TransportAgentPlan.model_validate(parsed_payload), raw_response, parsing_error


def _is_transport_ai_parameter_unsupported_error(
    exc: Exception,
    *,
    parameter_markers: tuple[str, ...],
) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in parameter_markers) and any(
        marker in message
        for marker in (
            "unsupported",
            "not supported",
            "unknown parameter",
            "invalid",
            "not permitted",
            "not allowed",
        )
    )


def _is_transport_ai_temperature_unsupported_error(exc: Exception) -> bool:
    return _is_transport_ai_parameter_unsupported_error(exc, parameter_markers=("temperature",))


def _is_transport_ai_reasoning_unsupported_error(exc: Exception) -> bool:
    return _is_transport_ai_parameter_unsupported_error(
        exc,
        parameter_markers=("reasoning_effort", "reasoning"),
    )


def _build_transport_ai_compatible_chat_model(
    *,
    runtime_settings: TransportAILlmRuntimeSettings,
    settings_obj: Settings,
    requested_temperature: float | None,
    temperature_omitted: bool,
    reasoning_omitted: bool,
) -> tuple[ChatOpenAI, float | None, bool, bool]:
    applied_temperature = None if temperature_omitted else requested_temperature

    while True:
        try:
            return (
                build_transport_ai_chat_model_for_provider(
                    runtime_settings=runtime_settings,
                    settings_obj=settings_obj,
                    temperature=applied_temperature,
                    include_reasoning_effort=not reasoning_omitted,
                ),
                applied_temperature,
                temperature_omitted,
                reasoning_omitted,
            )
        except Exception as exc:
            if not reasoning_omitted and _is_transport_ai_reasoning_unsupported_error(exc):
                logger.warning(
                    "Transport AI model %s rejected the provider-specific reasoning payload; retrying without reasoning parameter.",
                    runtime_settings.model_name,
                )
                reasoning_omitted = True
                continue

            if (
                not temperature_omitted
                and requested_temperature is not None
                and _is_transport_ai_temperature_unsupported_error(exc)
            ):
                logger.warning(
                    "Transport AI model %s rejected temperature=%s; retrying without temperature.",
                    runtime_settings.model_name,
                    requested_temperature,
                )
                temperature_omitted = True
                applied_temperature = None
                continue

            raise


def run_transport_ai_agent(
    *,
    db: Session,
    run: TransportAIRun,
    settings_obj: Settings = settings,
    provider: TransportRouteProvider | None = None,
    model: Any | None = None,
    max_validation_retries: int | None = None,
) -> TransportAIAgentRunResult:
    effective_provider = provider or build_transport_route_provider(settings_obj=settings_obj)
    agent_mode = resolve_transport_ai_agent_mode(settings_obj=settings_obj)
    validation_retries = settings_obj.openai_max_retries if max_validation_retries is None else max_validation_retries
    max_attempts = max(1, int(validation_retries) + 1)
    requested_temperature = (
        resolve_transport_ai_model_temperature(settings_obj=settings_obj)
        if agent_mode == "agent"
        else None
    )
    applied_temperature = requested_temperature
    temperature_omitted = False
    reasoning_omitted = False
    resolved_llm_runtime_settings: TransportAILlmRuntimeSettings | None = None
    runtime_secret_literals: tuple[str, ...] = ()
    effective_model_name = run.llm_model or run.openai_model or settings_obj.openai_model
    last_raw_model_response_json: str | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    validation_result: TransportAIValidateTransportPlanToolOutput | None = None

    context = TransportAILangChainToolContext(
        db=db,
        service_date=run.service_date,
        route_kind=run.route_kind,
        earliest_boarding_time=run.earliest_boarding_time,
        arrival_at_work_time=run.arrival_at_work_time,
        settings_obj=settings_obj,
        provider=effective_provider,
    )
    _maybe_seed_transport_ai_context_from_run(context=context, run=run)

    try:
        if agent_mode == "agent" and _should_resolve_transport_ai_run_llm_runtime_settings(run=run, model=model):
            resolved_llm_runtime_settings = _resolve_transport_ai_run_llm_runtime_settings(
                db=db,
                run=run,
                settings_obj=settings_obj,
            )
            runtime_secret_literals = (resolved_llm_runtime_settings.api_key,)
            effective_model_name = resolved_llm_runtime_settings.model_name

        _update_transport_ai_run_status(
            db=db,
            run=run,
            status="running",
            settings_obj=settings_obj,
            completed=False,
        )
        if agent_mode == "deterministic":
            plan, validation_result = _execute_transport_ai_deterministic_plan(context=context)

            planning_input = context.state.planning_input
            if planning_input is None:
                raise ValueError("Planning input is not available after deterministic execution.")
            _sync_transport_ai_run_planning_input(
                db=db,
                run=run,
                planning_input=planning_input,
                settings_obj=settings_obj,
            )

            if not validation_result.ok:
                failure_code = "transport_ai_deterministic_plan_invalid"
                failure_message = _sanitize_transport_ai_string_with_runtime_secrets(
                    _build_transport_ai_deterministic_validation_failure_message(validation_result),
                    settings_obj=settings_obj,
                    runtime_secret_literals=runtime_secret_literals,
                )
                _update_transport_ai_run_status(
                    db=db,
                    run=run,
                    status="failed",
                    settings_obj=settings_obj,
                    error_code=failure_code,
                    error_message=failure_message,
                    completed=True,
                )
                return TransportAIAgentRunResult(
                    plan=None,
                    raw_model_response_json=None,
                    prompt_version=TRANSPORT_AI_PROMPT_VERSION,
                    openai_model=effective_model_name,
                    attempt_count=1,
                    temperature_requested=None,
                    temperature_applied=None,
                    temperature_omitted=False,
                    validation_result=validation_result,
                    error_code=failure_code,
                    error_message=failure_message,
                )

            _update_transport_ai_run_status(
                db=db,
                run=run,
                status="proposed",
                settings_obj=settings_obj,
                completed=True,
            )
            return TransportAIAgentRunResult(
                plan=plan,
                raw_model_response_json=None,
                prompt_version=TRANSPORT_AI_PROMPT_VERSION,
                openai_model=effective_model_name,
                attempt_count=1,
                temperature_requested=None,
                temperature_applied=None,
                temperature_omitted=False,
                validation_result=validation_result,
            )

        tool_results = _execute_transport_ai_tool_sequence(context=context)

        planning_input = context.state.planning_input
        if planning_input is None:
            raise ValueError("Planning input is not available after deterministic tool execution.")
        _sync_transport_ai_run_planning_input(
            db=db,
            run=run,
            planning_input=planning_input,
            settings_obj=settings_obj,
        )

        effective_model = model
        if effective_model is None:
            if resolved_llm_runtime_settings is None:
                raise ValueError("Transport AI LLM runtime settings are not available for agent execution.")
            effective_model, applied_temperature, temperature_omitted, reasoning_omitted = _build_transport_ai_compatible_chat_model(
                runtime_settings=resolved_llm_runtime_settings,
                settings_obj=settings_obj,
                requested_temperature=requested_temperature,
                temperature_omitted=temperature_omitted,
                reasoning_omitted=reasoning_omitted,
            )

        retry_feedback: str | None = None
        for attempt_number in range(1, max_attempts + 1):
            messages = _build_transport_ai_runtime_messages(
                context=context,
                tool_results=tool_results,
                retry_feedback=retry_feedback,
            )

            while True:
                try:
                    plan, raw_response, parsing_error = _invoke_transport_ai_structured_model(
                        model=effective_model,
                        messages=messages,
                    )
                    break
                except Exception as exc:
                    if (
                        model is None
                        and not reasoning_omitted
                        and _is_transport_ai_reasoning_unsupported_error(exc)
                    ):
                        if resolved_llm_runtime_settings is None:
                            raise
                        reasoning_omitted = True
                        effective_model, applied_temperature, temperature_omitted, reasoning_omitted = _build_transport_ai_compatible_chat_model(
                            runtime_settings=resolved_llm_runtime_settings,
                            settings_obj=settings_obj,
                            requested_temperature=requested_temperature,
                            temperature_omitted=temperature_omitted,
                            reasoning_omitted=reasoning_omitted,
                        )
                        continue

                    if (
                        model is None
                        and not temperature_omitted
                        and requested_temperature is not None
                        and _is_transport_ai_temperature_unsupported_error(exc)
                    ):
                        if resolved_llm_runtime_settings is None:
                            raise
                        temperature_omitted = True
                        effective_model, applied_temperature, temperature_omitted, reasoning_omitted = _build_transport_ai_compatible_chat_model(
                            runtime_settings=resolved_llm_runtime_settings,
                            settings_obj=settings_obj,
                            requested_temperature=requested_temperature,
                            temperature_omitted=temperature_omitted,
                            reasoning_omitted=reasoning_omitted,
                        )
                        continue

                    last_error_code = "transport_ai_agent_model_invoke_failed"
                    last_error_message = _sanitize_transport_ai_string_with_runtime_secrets(
                        f"Attempt {attempt_number} failed during model invocation: {exc}",
                        settings_obj=settings_obj,
                        runtime_secret_literals=runtime_secret_literals,
                    )
                    plan = None
                    raw_response = None
                    parsing_error = None
                    break

            last_raw_model_response_json = _build_transport_ai_raw_model_response_json(
                raw_response=raw_response,
                parsing_error=parsing_error,
                model_name=effective_model_name,
                attempt_number=attempt_number,
                temperature_requested=requested_temperature,
                temperature_applied=applied_temperature,
                temperature_omitted=temperature_omitted,
                settings_obj=settings_obj,
                runtime_secret_literals=runtime_secret_literals,
            )

            if plan is None:
                if parsing_error is not None:
                    last_error_code = "transport_ai_agent_invalid_response"
                    last_error_message = _sanitize_transport_ai_string_with_runtime_secrets(
                        _build_transport_ai_retry_feedback_from_parsing_error(parsing_error),
                        settings_obj=settings_obj,
                        runtime_secret_literals=runtime_secret_literals,
                    )
                    retry_feedback = last_error_message
                    continue

                if last_error_message is None:
                    last_error_code = "transport_ai_agent_invalid_response"
                    last_error_message = (
                        "Transport AI agent returned no structured plan and no parsing error details."
                    )
                retry_feedback = last_error_message
                continue

            validation_result = _validate_transport_ai_plan_deterministically(
                planning_input=planning_input,
                plan=plan,
            )
            if not validation_result.ok:
                last_error_code = "transport_ai_agent_invalid_response"
                last_error_message = _sanitize_transport_ai_string_with_runtime_secrets(
                    _build_transport_ai_retry_feedback_from_validation(validation_result),
                    settings_obj=settings_obj,
                    runtime_secret_literals=runtime_secret_literals,
                )
                retry_feedback = last_error_message
                continue

            _update_transport_ai_run_status(
                db=db,
                run=run,
                status="proposed",
                settings_obj=settings_obj,
                completed=True,
            )
            return TransportAIAgentRunResult(
                plan=plan,
                raw_model_response_json=last_raw_model_response_json,
                prompt_version=TRANSPORT_AI_PROMPT_VERSION,
                openai_model=effective_model_name,
                attempt_count=attempt_number,
                temperature_requested=requested_temperature,
                temperature_applied=applied_temperature,
                temperature_omitted=temperature_omitted,
                validation_result=validation_result,
            )

        failure_code = last_error_code or "transport_ai_agent_invalid_response"
        failure_message = last_error_message or (
            "Transport AI agent exhausted retries without producing a valid structured plan."
        )
        _update_transport_ai_run_status(
            db=db,
            run=run,
            status="failed",
            settings_obj=settings_obj,
            error_code=failure_code,
            error_message=failure_message,
            completed=True,
        )
        return TransportAIAgentRunResult(
            plan=None,
            raw_model_response_json=last_raw_model_response_json,
            prompt_version=TRANSPORT_AI_PROMPT_VERSION,
            openai_model=effective_model_name,
            attempt_count=max_attempts,
            temperature_requested=requested_temperature,
            temperature_applied=applied_temperature,
            temperature_omitted=temperature_omitted,
            validation_result=validation_result,
            error_code=failure_code,
            error_message=failure_message,
        )
    except Exception as exc:
        failure_message = _sanitize_transport_ai_string_with_runtime_secrets(
            str(exc),
            settings_obj=settings_obj,
            runtime_secret_literals=runtime_secret_literals,
        )
        _update_transport_ai_run_status(
            db=db,
            run=run,
            status="failed",
            settings_obj=settings_obj,
            error_code="transport_ai_agent_execution_failed",
            error_message=failure_message,
            completed=True,
        )
        return TransportAIAgentRunResult(
            plan=None,
            raw_model_response_json=last_raw_model_response_json,
            prompt_version=TRANSPORT_AI_PROMPT_VERSION,
            openai_model=effective_model_name,
            attempt_count=0,
            temperature_requested=requested_temperature,
            temperature_applied=applied_temperature,
            temperature_omitted=temperature_omitted,
            validation_result=validation_result,
            error_code="transport_ai_agent_execution_failed",
            error_message=failure_message,
        )