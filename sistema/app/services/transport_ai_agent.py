from __future__ import annotations

import json
import logging
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from time import perf_counter
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
    TransportAIMessageParams,
    TransportAIObservabilityPartition,
    TransportAIObservabilitySummary,
    TransportAgentChangeSummary,
    TransportAgentCostSummary,
    TransportAgentDashboardScope,
    TransportAgentPlan,
    TransportAgentPlanningInput,
    TransportAgentProjectLlmRuntimeSnapshot,
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
    TransportAILlmSettingsValidationError,
)
from .transport_ai_runtime import (
    resolve_transport_ai_message_descriptor,
    resolve_transport_ai_shared_llm_runtime_context,
)
from .transport_ai_sanitization import (
    TRANSPORT_AI_REDACTED_VALUE,
    sanitize_transport_ai_raw_value,
    sanitize_transport_ai_string,
)
from .transport_route_provider import (
    TransportRouteProvider,
    TransportRouteProviderAuthError,
    TransportRouteProviderError,
    TransportRouteProviderInvalidResponseError,
    TransportRouteProviderNoResultError,
    TransportRouteProviderNoRouteError,
    TransportRouteProviderTimeoutError,
    build_transport_route_provider,
)

TRANSPORT_AI_PROMPT_VERSION = "transport_ai_route_planner_v4"
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
    message_key: str | None = Field(default=None, min_length=1, max_length=120)
    message_params: TransportAIMessageParams = Field(default_factory=dict)
    blocking: bool = True
    request_id: int | None = Field(default=None, ge=1)
    vehicle_id: int | None = Field(default=None, ge=1)
    setting_name: str | None = Field(default=None, max_length=80)


class TransportAIToolExecutionError(Exception):
    def __init__(
        self,
        *,
        tool_name: str,
        issues: list["TransportAILangChainToolIssue"],
    ) -> None:
        normalized_issues = list(issues)
        if not normalized_issues:
            normalized_issues = [
                TransportAILangChainToolIssue(
                    code="transport_ai_tool_execution_failed",
                    message=f"Tool '{tool_name}' failed without a structured issue payload.",
                    blocking=True,
                )
            ]

        primary_issue = next(
            (issue for issue in normalized_issues if issue.blocking and issue.code),
            normalized_issues[0],
        )
        self.tool_name = tool_name
        self.issues = normalized_issues
        self.error_code = primary_issue.code
        self.message_key = primary_issue.message_key
        self.message_params = dict(primary_issue.message_params or {})
        self.primary_issue_message = primary_issue.message
        super().__init__(_format_transport_ai_tool_issues(tool_name, normalized_issues))


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
    message_key: str | None = None
    message_params: TransportAIMessageParams = field(default_factory=dict)
    issues: list[TransportAIPreflightIssue] = field(default_factory=list)
    observability: TransportAIObservabilitySummary | None = None


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
    dashboard_scope: TransportAgentDashboardScope | None = None
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
    message_key: str | None = None,
    message_params: TransportAIMessageParams | None = None,
    blocking: bool = True,
    request_id: int | None = None,
    vehicle_id: int | None = None,
    setting_name: str | None = None,
) -> TransportAILangChainToolIssue:
    return TransportAILangChainToolIssue(
        code=code,
        message=message,
        message_key=message_key,
        message_params=dict(message_params or {}),
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
        message_key=getattr(issue, "message_key", None),
        message_params=getattr(issue, "message_params", {}) or {},
        blocking=issue.blocking,
        request_id=getattr(issue, "request_id", None),
        vehicle_id=getattr(issue, "vehicle_id", None),
        setting_name=getattr(issue, "setting_name", None),
    )


def _coerce_transport_ai_tool_issue_like(issue: Any) -> TransportAILangChainToolIssue:
    if isinstance(issue, TransportAILangChainToolIssue):
        return issue
    if isinstance(issue, (TransportAIPreflightIssue, TransportProposalValidationIssue)):
        return _coerce_transport_ai_tool_issue(issue)
    if isinstance(issue, dict):
        raw_request_id = issue.get("request_id")
        request_id = raw_request_id if isinstance(raw_request_id, int) and raw_request_id > 0 else None
        raw_vehicle_id = issue.get("vehicle_id")
        vehicle_id = raw_vehicle_id if isinstance(raw_vehicle_id, int) and raw_vehicle_id > 0 else None
        raw_message_params = issue.get("message_params")
        message_params = raw_message_params if isinstance(raw_message_params, dict) else {}
        return _build_transport_ai_tool_issue(
            code=str(issue.get("code") or "").strip() or "transport_ai_tool_execution_failed",
            message=str(issue.get("message") or "").strip() or "Transport AI tool execution failed.",
            message_key=str(issue.get("message_key") or "").strip() or None,
            message_params=message_params,
            blocking=bool(issue.get("blocking", True)),
            request_id=request_id,
            vehicle_id=vehicle_id,
            setting_name=str(issue.get("setting_name") or "").strip() or None,
        )
    return _build_transport_ai_tool_issue(
        code="transport_ai_tool_execution_failed",
        message=str(issue).strip() or "Transport AI tool execution failed.",
        blocking=True,
    )


def _build_transport_ai_tool_issue_from_exception(
    exc: Exception,
    *,
    code: str = "transport_ai_tool_execution_failed",
) -> TransportAILangChainToolIssue:
    normalized_message = _truncate_transport_ai_error_message(str(exc)) or "Transport AI tool execution failed."
    if isinstance(exc, TransportRouteProviderError):
        error_code = _resolve_transport_ai_route_provider_failure_code(exc)
        _friendly_message, message_key, message_params = _resolve_transport_ai_failure_contract(
            error_code=error_code,
            fallback_message=normalized_message,
            route_provider=exc.provider,
        )
        return _build_transport_ai_tool_issue(
            code=error_code,
            message=normalized_message,
            message_key=message_key,
            message_params=message_params,
            blocking=True,
            setting_name=f"transport_ai_{exc.provider}_{exc.operation}",
        )
    return _build_transport_ai_tool_issue(code=code, message=normalized_message, blocking=True)


def _raise_transport_ai_tool_execution_error(
    tool_name: str,
    issues: list[Any] | None,
) -> None:
    raise TransportAIToolExecutionError(
        tool_name=tool_name,
        issues=[_coerce_transport_ai_tool_issue_like(issue) for issue in issues or []],
    )


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


def _measure_transport_ai_phase_ms(started_at: float) -> int:
    return max(0, int(round((perf_counter() - started_at) * 1000)))


def _build_transport_ai_observability_partition_index(
    summary: TransportAIObservabilitySummary,
) -> dict[str, TransportAIObservabilityPartition]:
    return {
        partition.partition_key: partition
        for partition in summary.partitions
    }


def _build_transport_ai_llm_snapshot_by_partition_key(
    planning_input: TransportAgentPlanningInput,
) -> dict[str, TransportAgentProjectLlmRuntimeSnapshot]:
    snapshot_by_partition_key: dict[str, TransportAgentProjectLlmRuntimeSnapshot] = {}
    for snapshot in planning_input.llm_runtime_projects:
        for partition_key in snapshot.partition_keys:
            normalized_partition_key = str(partition_key).strip()
            if normalized_partition_key:
                snapshot_by_partition_key[normalized_partition_key] = snapshot
    return snapshot_by_partition_key


def _synchronize_transport_ai_observability_runtime_context(
    summary: TransportAIObservabilitySummary,
    *,
    planning_input: TransportAgentPlanningInput,
    run: TransportAIRun | None,
    route_provider: str,
) -> None:
    summary.total_eligible_request_count = planning_input.total_requests
    summary.partition_count = len(planning_input.partitions)
    summary.route_provider = route_provider

    snapshot_by_partition_key = _build_transport_ai_llm_snapshot_by_partition_key(planning_input)
    partition_index = _build_transport_ai_observability_partition_index(summary)
    for partition_key, snapshot in snapshot_by_partition_key.items():
        partition_summary = partition_index.get(partition_key)
        if partition_summary is None:
            continue
        partition_summary.llm_provider = snapshot.provider
        partition_summary.llm_model = snapshot.model_name
        partition_summary.llm_reasoning_effort = snapshot.reasoning_effort

    llm_provider = str((run.llm_provider if run is not None else summary.llm_provider) or "").strip().lower()
    llm_model = str((run.llm_model if run is not None else summary.llm_model) or "").strip()
    llm_reasoning_effort = str(
        (run.llm_reasoning_effort if run is not None else summary.llm_reasoning_effort) or ""
    ).strip().lower()

    if planning_input.llm_runtime_projects:
        unique_snapshots = {
            (snapshot.provider, snapshot.model_name, snapshot.reasoning_effort)
            for snapshot in planning_input.llm_runtime_projects
        }
        if len(unique_snapshots) == 1:
            llm_provider, llm_model, llm_reasoning_effort = next(iter(unique_snapshots))
        else:
            llm_provider = llm_model = llm_reasoning_effort = "multiple"

    summary.llm_provider = llm_provider or None
    summary.llm_model = llm_model or None
    summary.llm_reasoning_effort = llm_reasoning_effort or None


def _ensure_transport_ai_observability_summary(
    context: TransportAILangChainToolContext,
    *,
    run: TransportAIRun | None = None,
) -> TransportAIObservabilitySummary:
    planning_input = context.state.planning_input
    if planning_input is None:
        raise ValueError("Planning input is not available for transport AI observability.")

    summary = planning_input.observability
    if summary is None:
        snapshot_by_partition_key = _build_transport_ai_llm_snapshot_by_partition_key(planning_input)
        summary = TransportAIObservabilitySummary(
            total_eligible_request_count=planning_input.total_requests,
            partition_count=len(planning_input.partitions),
            route_provider=getattr(context.provider, "provider", None),
            partitions=[
                TransportAIObservabilityPartition(
                    partition_key=partition.partition_key,
                    request_kind=partition.request_kind,
                    project_name=partition.project_name,
                    eligible_request_count=len(partition.requests),
                    candidate_vehicle_count=len(partition.candidate_vehicles),
                    llm_provider=(snapshot_by_partition_key.get(partition.partition_key).provider if snapshot_by_partition_key.get(partition.partition_key) is not None else None),
                    llm_model=(snapshot_by_partition_key.get(partition.partition_key).model_name if snapshot_by_partition_key.get(partition.partition_key) is not None else None),
                    llm_reasoning_effort=(snapshot_by_partition_key.get(partition.partition_key).reasoning_effort if snapshot_by_partition_key.get(partition.partition_key) is not None else None),
                )
                for partition in planning_input.partitions
            ],
        )
        planning_input = planning_input.model_copy(update={"observability": summary})
        context.state.planning_input = planning_input

    _synchronize_transport_ai_observability_runtime_context(
        summary,
        planning_input=context.state.planning_input,
        run=run,
        route_provider=str(getattr(context.provider, "provider", "") or "").strip() or "unknown",
    )
    return summary


def _add_transport_ai_phase_duration(
    summary: TransportAIObservabilitySummary,
    *,
    phase_field: str,
    duration_ms: int,
) -> None:
    current_value = getattr(summary.phase_durations_ms, phase_field)
    if current_value is None:
        setattr(summary.phase_durations_ms, phase_field, max(duration_ms, 0))
        return
    setattr(summary.phase_durations_ms, phase_field, current_value + max(duration_ms, 0))


def _apply_transport_ai_route_point_observability(
    summary: TransportAIObservabilitySummary,
    *,
    resolved_route_points: TransportAgentResolvedRoutePointsResult,
) -> None:
    summary.geocode_provider_call_count = resolved_route_points.total_geocode_provider_calls
    summary.geocode_cache_hit_count = resolved_route_points.total_geocode_cache_hits
    summary.geocode_failure_count = resolved_route_points.total_geocode_failures

    partition_index = _build_transport_ai_observability_partition_index(summary)
    for partition in resolved_route_points.partitions:
        partition_summary = partition_index.get(partition.partition_key)
        if partition_summary is None:
            continue
        partition_summary.resolved_point_count = len(partition.passenger_points) + (
            1 if partition.destination_point is not None else 0
        )
        partition_summary.geocode_provider_call_count = partition.geocode_provider_call_count
        partition_summary.geocode_cache_hit_count = partition.geocode_cache_hit_count
        partition_summary.geocode_failure_count = partition.geocode_failure_count


def _apply_transport_ai_route_matrix_observability(
    summary: TransportAIObservabilitySummary,
    *,
    route_matrices: TransportAgentRouteMatricesResult,
) -> None:
    summary.matrix_provider_call_count = route_matrices.total_matrix_provider_calls
    summary.matrix_chunk_count = route_matrices.total_matrix_chunks

    partition_index = _build_transport_ai_observability_partition_index(summary)
    for partition in route_matrices.partitions:
        partition_summary = partition_index.get(partition.partition_key)
        if partition_summary is None:
            continue
        partition_summary.matrix_point_count = len(partition.points)
        partition_summary.matrix_request_count = partition.matrix_request_count
        partition_summary.matrix_chunk_count = partition.matrix_chunk_count
        partition_summary.matrix_cached = partition.cached


def _apply_transport_ai_partition_solve_observability(
    summary: TransportAIObservabilitySummary,
    *,
    partition_solve_results: list[TransportAgentPartitionSolveResult],
) -> None:
    partition_index = _build_transport_ai_observability_partition_index(summary)
    for partition_result in partition_solve_results:
        partition_summary = partition_index.get(partition_result.partition_key)
        if partition_summary is None:
            continue
        partition_summary.solver_algorithm = partition_result.algorithm_used
        partition_summary.solver_duration_ms = partition_result.solver_duration_ms


def _mark_transport_ai_observability_failure(
    summary: TransportAIObservabilitySummary,
    *,
    failure_layer: str,
    failed_phase: str,
) -> None:
    if not summary.failure_layer:
        summary.failure_layer = failure_layer
    if not summary.failed_phase:
        summary.failed_phase = failed_phase


def _maybe_sync_transport_ai_run_observability(
    *,
    db: Session,
    run: TransportAIRun,
    context: TransportAILangChainToolContext,
    settings_obj: Settings,
) -> None:
    planning_input = context.state.planning_input
    if planning_input is None:
        return
    _sync_transport_ai_run_planning_input(
        db=db,
        run=run,
        planning_input=planning_input,
        settings_obj=settings_obj,
    )


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
    allocation_leg_counter = Counter(
        (allocation.request_id, allocation.route_kind) for allocation in plan.passenger_allocations
    )
    allocated_request_ids = {allocation.request_id for allocation in plan.passenger_allocations}
    request_ids_with_plan_issues = {
        issue.request_id
        for issue in plan.validation_issues
        if issue.request_id is not None
    }

    duplicate_allocation_request_ids = sorted(
        {
            request_id
            for (request_id, route_kind), allocation_count in allocation_leg_counter.items()
            if allocation_count > 1
        }
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
        request_id for request_id in allocated_request_ids if request_id not in expected_request_ids
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
        if request_id not in allocated_request_ids and request_id not in request_ids_with_plan_issues
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
        allocated_request_count=len(allocated_request_ids),
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
                dashboard_scope=context.dashboard_scope,
                settings_obj=context.settings_obj,
            )
            context.dashboard_scope = context.state.planning_input.dashboard_scope
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
                    profile=context.settings_obj.here_matrix_profile,
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
    return True


def _build_transport_ai_run_llm_snapshot_signature(
    snapshots: list[TransportAgentProjectLlmRuntimeSnapshot],
) -> list[tuple[int, str, str, str, tuple[str, ...]]]:
    normalized_rows: list[tuple[int, str, str, str, tuple[str, ...]]] = []
    for snapshot in snapshots:
        normalized_rows.append(
            (
                int(snapshot.project_id),
                str(snapshot.provider or "").strip().lower(),
                str(snapshot.model_name or "").strip(),
                str(snapshot.reasoning_effort or "").strip().lower(),
                tuple(
                    sorted(
                        {
                            str(partition_key).strip()
                            for partition_key in snapshot.partition_keys
                            if str(partition_key).strip()
                        }
                    )
                ),
            )
        )
    return sorted(normalized_rows)


def _validate_transport_ai_run_llm_snapshot_consistency(
    *,
    run: TransportAIRun,
    planning_input: TransportAgentPlanningInput,
    persisted_runtime_settings: TransportAILlmRuntimeSettings,
    llm_runtime_projects: list[TransportAgentProjectLlmRuntimeSnapshot],
) -> None:
    if planning_input.llm_runtime_projects:
        if _build_transport_ai_run_llm_snapshot_signature(
            planning_input.llm_runtime_projects
        ) != _build_transport_ai_run_llm_snapshot_signature(llm_runtime_projects):
            raise TransportAILlmSettingsValidationError(
                "Transport AI run LLM snapshot no longer matches the current project-specific AI settings. "
                "Start a new run after saving consistent AI settings for the referenced projects."
            )
        return

    snapshot_provider = str(run.llm_provider or "").strip().lower()
    snapshot_model_name = str(run.llm_model or "").strip()
    snapshot_reasoning_effort = str(run.llm_reasoning_effort or "").strip().lower()
    if not any((snapshot_provider, snapshot_model_name, snapshot_reasoning_effort)):
        return

    if (
        (snapshot_provider and snapshot_provider != persisted_runtime_settings.provider)
        or (snapshot_model_name and snapshot_model_name != persisted_runtime_settings.model_name)
        or (
            snapshot_reasoning_effort
            and snapshot_reasoning_effort != persisted_runtime_settings.reasoning_effort
        )
    ):
        raise TransportAILlmSettingsValidationError(
            "Transport AI run LLM snapshot no longer matches the current project-specific AI settings. "
            "Start a new run after saving consistent AI settings for the referenced projects."
        )


def _resolve_transport_ai_run_llm_runtime_settings(
    *,
    db: Session,
    run: TransportAIRun,
    planning_input: TransportAgentPlanningInput,
    settings_obj: Settings = settings,
) -> tuple[TransportAILlmRuntimeSettings, TransportAgentPlanningInput]:
    persisted_runtime_settings, llm_runtime_projects = resolve_transport_ai_shared_llm_runtime_context(
        db,
        planning_input=planning_input,
        settings_obj=settings_obj,
    )
    _validate_transport_ai_run_llm_snapshot_consistency(
        run=run,
        planning_input=planning_input,
        persisted_runtime_settings=persisted_runtime_settings,
        llm_runtime_projects=llm_runtime_projects,
    )

    updated_planning_input = planning_input
    if not planning_input.llm_runtime_projects:
        updated_planning_input = planning_input.model_copy(update={"llm_runtime_projects": llm_runtime_projects})

    return (
        persisted_runtime_settings,
        updated_planning_input,
    )


def _truncate_transport_ai_error_message(message: str | None) -> str | None:
    if message is None:
        return None
    normalized = message.strip()
    if len(normalized) <= 1000:
        return normalized
    return f"{normalized[:997]}..."


def _resolve_transport_ai_failure_contract(
    *,
    error_code: str | None,
    fallback_message: str,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    route_provider: str | None = None,
) -> tuple[str, str | None, TransportAIMessageParams]:
    descriptor = resolve_transport_ai_message_descriptor(
        error_code=error_code,
        llm_provider=llm_provider,
        llm_model=llm_model,
        route_provider=route_provider,
    )
    if descriptor is None:
        return (
            _truncate_transport_ai_error_message(fallback_message) or "Transport AI runtime failure.",
            None,
            {},
        )
    return descriptor.message, descriptor.message_key, dict(descriptor.message_params)


def _build_transport_ai_retry_feedback_payload(
    *,
    error_code: str,
    message: str,
    technical_detail: str,
    correction: str,
    issues: list[TransportProposalValidationIssue | TransportAIPreflightIssue] | None = None,
    message_key: str | None = None,
    message_params: TransportAIMessageParams | None = None,
) -> str:
    payload = {
        "retry_feedback": {
            "error_code": error_code,
            "message": _truncate_transport_ai_error_message(message) or "Transport AI retry required.",
            "message_key": message_key,
            "message_params": dict(message_params or {}),
            "technical_detail": _truncate_transport_ai_error_message(technical_detail)
            or "Transport AI retry required.",
            "issues": [issue.model_dump(mode="json") for issue in issues or []],
            "correction": correction,
        }
    }
    return _transport_ai_json_dumps(payload)


def _build_transport_ai_runtime_issue(
    *,
    code: str,
    message: str,
    message_key: str | None = None,
    message_params: TransportAIMessageParams | None = None,
    setting_name: str | None = None,
) -> TransportAIPreflightIssue:
    normalized_message = _truncate_transport_ai_error_message(message) or "Transport AI runtime failure."
    return TransportAIPreflightIssue(
        code=code,
        message=normalized_message,
        message_key=message_key,
        message_params=dict(message_params or {}),
        blocking=True,
        setting_name=setting_name,
    )


def _build_transport_ai_runtime_issues_from_tool_issues(
    issues: list[TransportAILangChainToolIssue],
) -> list[TransportAIPreflightIssue]:
    if not issues:
        return [
            _build_transport_ai_runtime_issue(
                code="transport_ai_tool_execution_failed",
                message="Transport AI tool execution failed.",
                setting_name="transport_ai_runtime",
            )
        ]

    return [
        _build_transport_ai_runtime_issue(
            code=issue.code,
            message=issue.message,
            message_key=issue.message_key,
            message_params=issue.message_params,
            setting_name=issue.setting_name,
        )
        for issue in issues
    ]


def _resolve_transport_ai_route_provider_failure_code(exc: TransportRouteProviderError) -> str:
    provider = str(exc.provider or "").strip().lower()
    operation = str(exc.operation or "").strip().lower()

    if provider == "here":
        if isinstance(exc, TransportRouteProviderAuthError):
            if exc.status_code in {401, 403}:
                return f"here_{operation}_auth_failed"
            return "here_api_key_missing"
        if isinstance(exc, TransportRouteProviderTimeoutError):
            return f"here_{operation}_timeout"
        if isinstance(exc, TransportRouteProviderNoResultError):
            if operation == "geocode":
                return "here_geocode_no_result"
            return f"here_{operation}_invalid_response"
        if isinstance(exc, TransportRouteProviderNoRouteError):
            return f"here_{operation}_no_route"
        if isinstance(exc, TransportRouteProviderInvalidResponseError):
            if exc.status_code is not None:
                return (
                    f"here_{operation}_request_5xx"
                    if int(exc.status_code) >= 500
                    else f"here_{operation}_request_4xx"
                )
            return f"here_{operation}_invalid_response"
        return "transport_ai_agent_execution_failed"

    return "transport_ai_agent_execution_failed"


def _build_transport_ai_route_provider_failure_details(
    exc: TransportRouteProviderError,
    *,
    settings_obj: Settings,
    runtime_secret_literals: tuple[str, ...],
) -> tuple[str, str, str | None, TransportAIMessageParams, list[TransportAIPreflightIssue]]:
    error_code = _resolve_transport_ai_route_provider_failure_code(exc)
    technical_message = _sanitize_transport_ai_string_with_runtime_secrets(
        str(exc),
        settings_obj=settings_obj,
        runtime_secret_literals=runtime_secret_literals,
    )
    friendly_message, message_key, message_params = _resolve_transport_ai_failure_contract(
        error_code=error_code,
        fallback_message=technical_message,
        route_provider=exc.provider,
    )
    issue = _build_transport_ai_runtime_issue(
        code=error_code,
        message=technical_message,
        message_key=message_key,
        message_params=message_params,
        setting_name=f"transport_ai_{exc.provider}_{exc.operation}",
    )
    return error_code, friendly_message, message_key, message_params, [issue]


def _update_transport_ai_run_status(
    *,
    db: Session,
    run: TransportAIRun,
    status: str,
    settings_obj: Settings = settings,
    error_code: str | None = None,
    error_message: str | None = None,
    issues: list[TransportAIPreflightIssue] | None = None,
    completed: bool,
) -> None:
    now = _transport_ai_now(settings_obj=settings_obj)
    run.status = status
    run.error_code = error_code
    run.error_message = _truncate_transport_ai_error_message(error_message)
    if issues is not None:
        run.preflight_issues_json = (
            _transport_ai_json_dumps(
                [
                    {
                        **issue.model_dump(mode="json"),
                        "source": "run_error",
                    }
                    for issue in issues
                ]
            )
            if issues
            else None
        )
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
    existing_runtime_issue_entries: list[dict[str, Any]] = []
    if str(run.preflight_issues_json or "").strip():
        try:
            existing_issue_entries = json.loads(run.preflight_issues_json)
        except (TypeError, ValueError):
            existing_issue_entries = []
        if isinstance(existing_issue_entries, list):
            existing_runtime_issue_entries = [
                entry
                for entry in existing_issue_entries
                if isinstance(entry, dict) and str(entry.get("source") or "").strip().lower() == "run_error"
            ]

    merged_issue_entries = [issue.model_dump(mode="json") for issue in planning_input.preflight_issues]
    merged_issue_entries.extend(existing_runtime_issue_entries)
    run.preflight_issues_json = (
        _transport_ai_json_dumps(merged_issue_entries)
        if merged_issue_entries
        else None
    )
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
        planning_payload = json.loads(planning_input_json)
    except Exception:
        planning_payload = None
    if isinstance(planning_payload, dict):
        raw_dashboard_scope = planning_payload.get("dashboard_scope")
        if raw_dashboard_scope is not None:
            try:
                context.dashboard_scope = TransportAgentDashboardScope.model_validate(raw_dashboard_scope)
            except Exception:
                context.dashboard_scope = None

    try:
        planning_input = TransportAgentPlanningInput.model_validate_json(planning_input_json)
    except Exception:
        return

    if planning_input.planning_input_hash != run.planning_input_hash:
        return

    context.state.planning_input = planning_input
    context.dashboard_scope = planning_input.dashboard_scope


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
    run: TransportAIRun | None = None,
) -> dict[str, dict[str, Any]]:
    tools_by_name = {
        tool.name: tool
        for tool in build_transport_ai_langchain_tools(context=context)
    }

    load_result = tools_by_name["load_planning_input"].invoke({})
    planning_input_hash = load_result.get("planning_input_hash")
    if not planning_input_hash:
        _raise_transport_ai_tool_execution_error("load_planning_input", load_result.get("issues", []))
    summary = _ensure_transport_ai_observability_summary(context, run=run)

    geocode_started_at = perf_counter()
    geocode_result = tools_by_name["geocode_route_points"].invoke({"planning_input_hash": planning_input_hash})
    _add_transport_ai_phase_duration(
        summary,
        phase_field="geocode_ms",
        duration_ms=_measure_transport_ai_phase_ms(geocode_started_at),
    )
    if context.state.resolved_route_points is not None:
        _apply_transport_ai_route_point_observability(
            summary,
            resolved_route_points=context.state.resolved_route_points,
        )
    if not bool(geocode_result.get("ok", False)):
        _mark_transport_ai_observability_failure(
            summary,
            failure_layer="route_provider",
            failed_phase="geocode",
        )
        _raise_transport_ai_tool_execution_error("geocode_route_points", geocode_result.get("issues", []))

    matrix_started_at = perf_counter()
    route_matrix_result = tools_by_name["build_route_matrices"].invoke({"planning_input_hash": planning_input_hash})
    _add_transport_ai_phase_duration(
        summary,
        phase_field="matrix_ms",
        duration_ms=_measure_transport_ai_phase_ms(matrix_started_at),
    )
    if context.state.route_matrices is not None:
        _apply_transport_ai_route_matrix_observability(
            summary,
            route_matrices=context.state.route_matrices,
        )
    if not bool(route_matrix_result.get("ok", False)):
        _mark_transport_ai_observability_failure(
            summary,
            failure_layer="route_provider",
            failed_phase="matrix",
        )
        _raise_transport_ai_tool_execution_error("build_route_matrices", route_matrix_result.get("issues", []))

    solve_started_at = perf_counter()
    solve_result = tools_by_name["solve_transport_plan"].invoke({"planning_input_hash": planning_input_hash})
    _add_transport_ai_phase_duration(
        summary,
        phase_field="solve_ms",
        duration_ms=_measure_transport_ai_phase_ms(solve_started_at),
    )
    if context.state.partition_solve_results:
        _apply_transport_ai_partition_solve_observability(
            summary,
            partition_solve_results=context.state.partition_solve_results,
        )
    plan_key = solve_result.get("plan_key")
    if not plan_key or context.state.plan is None:
        _mark_transport_ai_observability_failure(
            summary,
            failure_layer="local",
            failed_phase="solve",
        )
        _raise_transport_ai_tool_execution_error("solve_transport_plan", solve_result.get("issues", []))

    validate_started_at = perf_counter()
    validate_result = tools_by_name["validate_transport_plan"].invoke({"plan_key": plan_key})
    _add_transport_ai_phase_duration(
        summary,
        phase_field="validation_ms",
        duration_ms=_measure_transport_ai_phase_ms(validate_started_at),
    )
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
    run: TransportAIRun | None = None,
) -> tuple[TransportAgentPlan, TransportAIValidateTransportPlanToolOutput]:
    load_result = _run_load_planning_input_tool(context, refresh=False)
    planning_input_hash = load_result.planning_input_hash
    if not planning_input_hash:
        _raise_transport_ai_tool_execution_error("load_planning_input", load_result.issues)
    summary = _ensure_transport_ai_observability_summary(context, run=run)

    geocode_started_at = perf_counter()
    geocode_result = _run_geocode_route_points_tool(
        context,
        planning_input_hash=planning_input_hash,
        refresh=False,
    )
    _add_transport_ai_phase_duration(
        summary,
        phase_field="geocode_ms",
        duration_ms=_measure_transport_ai_phase_ms(geocode_started_at),
    )
    if context.state.resolved_route_points is not None:
        _apply_transport_ai_route_point_observability(
            summary,
            resolved_route_points=context.state.resolved_route_points,
        )
    if not geocode_result.ok:
        _mark_transport_ai_observability_failure(
            summary,
            failure_layer="route_provider",
            failed_phase="geocode",
        )
        _raise_transport_ai_tool_execution_error("geocode_route_points", geocode_result.issues)

    matrix_started_at = perf_counter()
    route_matrices_result = _run_build_route_matrices_tool(
        context,
        planning_input_hash=planning_input_hash,
        refresh=False,
    )
    _add_transport_ai_phase_duration(
        summary,
        phase_field="matrix_ms",
        duration_ms=_measure_transport_ai_phase_ms(matrix_started_at),
    )
    if context.state.route_matrices is not None:
        _apply_transport_ai_route_matrix_observability(
            summary,
            route_matrices=context.state.route_matrices,
        )
    if not route_matrices_result.ok:
        _mark_transport_ai_observability_failure(
            summary,
            failure_layer="route_provider",
            failed_phase="matrix",
        )
        _raise_transport_ai_tool_execution_error("build_route_matrices", route_matrices_result.issues)

    solve_started_at = perf_counter()
    solve_result = _run_solve_transport_plan_tool(
        context,
        planning_input_hash=planning_input_hash,
        refresh=False,
    )
    _add_transport_ai_phase_duration(
        summary,
        phase_field="solve_ms",
        duration_ms=_measure_transport_ai_phase_ms(solve_started_at),
    )
    if context.state.partition_solve_results:
        _apply_transport_ai_partition_solve_observability(
            summary,
            partition_solve_results=context.state.partition_solve_results,
        )
    if solve_result.plan is None or not solve_result.plan_key:
        _mark_transport_ai_observability_failure(
            summary,
            failure_layer="local",
            failed_phase="solve",
        )
        _raise_transport_ai_tool_execution_error("solve_transport_plan", solve_result.issues)

    validate_started_at = perf_counter()
    validation_result = _run_validate_transport_plan_tool(
        context,
        plan_key=solve_result.plan_key,
    )
    _add_transport_ai_phase_duration(
        summary,
        phase_field="validation_ms",
        duration_ms=_measure_transport_ai_phase_ms(validate_started_at),
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
    *,
    error_code: str,
    message: str,
    technical_detail: str,
    message_key: str | None = None,
    message_params: TransportAIMessageParams | None = None,
) -> str:
    correction = (
        "Return a corrected TransportAgentPlan that resolves the blocking deterministic validation issues "
        "using only the authoritative execution context."
    )
    if not validation_result.issues:
        correction = (
            "Return a corrected TransportAgentPlan using only the authoritative execution context and ensure it passes "
            "deterministic validation before completion."
        )
    return _build_transport_ai_retry_feedback_payload(
        error_code=error_code,
        message=message,
        technical_detail=technical_detail,
        correction=correction,
        issues=validation_result.issues[:5],
        message_key=message_key,
        message_params=message_params,
    )


def _build_transport_ai_retry_feedback_from_parsing_error(
    parsing_error: Exception,
    *,
    error_code: str,
    message: str,
    technical_detail: str,
    message_key: str | None = None,
    message_params: TransportAIMessageParams | None = None,
) -> str:
    return _build_transport_ai_retry_feedback_payload(
        error_code=error_code,
        message=message,
        technical_detail=technical_detail,
        correction="Return only a valid TransportAgentPlan that matches the required schema exactly.",
        issues=[
            TransportAIPreflightIssue(
                code=error_code,
                message=_truncate_transport_ai_error_message(str(parsing_error))
                or "Transport AI returned invalid structured output.",
                message_key=message_key,
                message_params=dict(message_params or {}),
                blocking=True,
            )
        ],
        message_key=message_key,
        message_params=message_params,
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
            matrix_profile=context.settings_obj.here_matrix_profile,
            directions_profile=context.settings_obj.here_directions_profile,
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
    try:
        structured_model = model.with_structured_output(
            TransportAgentPlan,
            method="function_calling",
            include_raw=True,
        )
        response = structured_model.invoke(messages)
    except Exception as exc:
        if not _is_transport_ai_structured_output_tool_choice_error(exc) or not hasattr(model, "bind_tools"):
            raise

        fallback_model = model.bind_tools(
            [TransportAgentPlan],
            tool_choice="auto",
            parallel_tool_calls=False,
        )
        fallback_response = fallback_model.invoke(messages)
        fallback_tool_calls = getattr(fallback_response, "tool_calls", None) or []
        parsed_tool_args = None
        if fallback_tool_calls:
            first_tool_call = fallback_tool_calls[0]
            if isinstance(first_tool_call, dict):
                parsed_tool_args = first_tool_call.get("args")
        response = {
            "raw": fallback_response,
            "parsed": parsed_tool_args,
            "parsing_error": None,
        }

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


def _is_transport_ai_deepseek_reasoning_tool_choice_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "tool_choice" in message and "deepseek-reasoner" in message


def _is_transport_ai_structured_output_tool_choice_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "tool_choice" in message and any(
        marker in message
        for marker in (
            "does not support",
            "unsupported",
            "not supported",
            "invalid_request_error",
        )
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
    last_error_detail: str | None = None
    last_message_key: str | None = None
    last_message_params: TransportAIMessageParams = {}
    validation_result: TransportAIValidateTransportPlanToolOutput | None = None
    observability_summary: TransportAIObservabilitySummary | None = None
    current_phase = "planning"

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
        _update_transport_ai_run_status(
            db=db,
            run=run,
            status="running",
            settings_obj=settings_obj,
            completed=False,
        )
        if agent_mode == "deterministic":
            current_phase = "deterministic"
            plan, validation_result = _execute_transport_ai_deterministic_plan(context=context, run=run)
            observability_summary = _ensure_transport_ai_observability_summary(context, run=run)

            planning_input = context.state.planning_input
            if planning_input is None:
                raise ValueError("Planning input is not available after deterministic execution.")
            _maybe_sync_transport_ai_run_observability(
                db=db,
                run=run,
                context=context,
                settings_obj=settings_obj,
            )

            if not validation_result.ok:
                failure_code = "transport_ai_deterministic_plan_invalid"
                technical_failure_message = _sanitize_transport_ai_string_with_runtime_secrets(
                    _build_transport_ai_deterministic_validation_failure_message(validation_result),
                    settings_obj=settings_obj,
                    runtime_secret_literals=runtime_secret_literals,
                )
                failure_message, failure_message_key, failure_message_params = _resolve_transport_ai_failure_contract(
                    error_code=failure_code,
                    fallback_message=technical_failure_message,
                    route_provider=run.route_provider,
                )
                failure_issues = [
                    _build_transport_ai_runtime_issue(
                        code=failure_code,
                        message=technical_failure_message,
                        message_key=failure_message_key,
                        message_params=failure_message_params,
                        setting_name="transport_ai_validation",
                    )
                ]
                _mark_transport_ai_observability_failure(
                    observability_summary,
                    failure_layer="local",
                    failed_phase="validation",
                )
                _maybe_sync_transport_ai_run_observability(
                    db=db,
                    run=run,
                    context=context,
                    settings_obj=settings_obj,
                )
                _update_transport_ai_run_status(
                    db=db,
                    run=run,
                    status="failed",
                    settings_obj=settings_obj,
                    error_code=failure_code,
                    error_message=failure_message,
                    issues=failure_issues,
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
                    message_key=failure_message_key,
                    message_params=failure_message_params,
                    issues=failure_issues,
                    observability=observability_summary,
                )

            _update_transport_ai_run_status(
                db=db,
                run=run,
                status="proposed",
                settings_obj=settings_obj,
                completed=True,
            )
            _maybe_sync_transport_ai_run_observability(
                db=db,
                run=run,
                context=context,
                settings_obj=settings_obj,
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
                observability=observability_summary,
            )

        current_phase = "tool_sequence"
        tool_results = _execute_transport_ai_tool_sequence(context=context, run=run)
        observability_summary = _ensure_transport_ai_observability_summary(context, run=run)

        planning_input = context.state.planning_input
        if planning_input is None:
            raise ValueError("Planning input is not available after deterministic tool execution.")

        if agent_mode == "agent" and _should_resolve_transport_ai_run_llm_runtime_settings(run=run, model=model):
            current_phase = "llm_runtime"
            resolved_llm_runtime_settings, planning_input = _resolve_transport_ai_run_llm_runtime_settings(
                db=db,
                run=run,
                planning_input=planning_input,
                settings_obj=settings_obj,
            )
            context.state.planning_input = planning_input
            runtime_secret_literals = (resolved_llm_runtime_settings.api_key,)
            effective_model_name = resolved_llm_runtime_settings.model_name
            run.llm_provider = resolved_llm_runtime_settings.provider
            run.llm_model = resolved_llm_runtime_settings.model_name
            run.llm_reasoning_effort = resolved_llm_runtime_settings.reasoning_effort
            run.openai_model = resolved_llm_runtime_settings.model_name
            observability_summary = _ensure_transport_ai_observability_summary(context, run=run)

        _maybe_sync_transport_ai_run_observability(
            db=db,
            run=run,
            context=context,
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
            if observability_summary is not None:
                observability_summary.llm_attempt_count = max(observability_summary.llm_attempt_count, attempt_number)
            messages = _build_transport_ai_runtime_messages(
                context=context,
                tool_results=tool_results,
                retry_feedback=retry_feedback,
            )

            while True:
                current_phase = "llm"
                llm_started_at = perf_counter()
                try:
                    plan, raw_response, parsing_error = _invoke_transport_ai_structured_model(
                        model=effective_model,
                        messages=messages,
                    )
                    if observability_summary is not None:
                        _add_transport_ai_phase_duration(
                            observability_summary,
                            phase_field="llm_ms",
                            duration_ms=_measure_transport_ai_phase_ms(llm_started_at),
                        )
                    break
                except Exception as exc:
                    if observability_summary is not None:
                        _add_transport_ai_phase_duration(
                            observability_summary,
                            phase_field="llm_ms",
                            duration_ms=_measure_transport_ai_phase_ms(llm_started_at),
                        )
                    if (
                        model is None
                        and not reasoning_omitted
                        and (
                            _is_transport_ai_reasoning_unsupported_error(exc)
                            or _is_transport_ai_deepseek_reasoning_tool_choice_error(exc)
                        )
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
                    last_error_detail = _sanitize_transport_ai_string_with_runtime_secrets(
                        f"Attempt {attempt_number} failed during model invocation: {exc}",
                        settings_obj=settings_obj,
                        runtime_secret_literals=runtime_secret_literals,
                    )
                    last_error_message, last_message_key, last_message_params = _resolve_transport_ai_failure_contract(
                        error_code=last_error_code,
                        fallback_message=last_error_detail,
                        llm_provider=run.llm_provider,
                        llm_model=effective_model_name,
                        route_provider=run.route_provider,
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
                    last_error_detail = _sanitize_transport_ai_string_with_runtime_secrets(
                        (
                            "Transport AI returned a response that did not match the expected "
                            f"TransportAgentPlan schema: {parsing_error}"
                        ),
                        settings_obj=settings_obj,
                        runtime_secret_literals=runtime_secret_literals,
                    )
                    last_error_message, last_message_key, last_message_params = _resolve_transport_ai_failure_contract(
                        error_code=last_error_code,
                        fallback_message=last_error_detail,
                        llm_provider=run.llm_provider,
                        llm_model=effective_model_name,
                        route_provider=run.route_provider,
                    )
                    retry_feedback = _build_transport_ai_retry_feedback_from_parsing_error(
                        parsing_error,
                        error_code=last_error_code,
                        message=last_error_message,
                        technical_detail=last_error_detail,
                        message_key=last_message_key,
                        message_params=last_message_params,
                    )
                    continue

                if last_error_message is None:
                    last_error_code = "transport_ai_agent_invalid_response"
                    last_error_detail = (
                        "Transport AI agent returned no structured plan and no parsing error details."
                    )
                    last_error_message, last_message_key, last_message_params = _resolve_transport_ai_failure_contract(
                        error_code=last_error_code,
                        fallback_message=last_error_detail,
                        llm_provider=run.llm_provider,
                        llm_model=effective_model_name,
                        route_provider=run.route_provider,
                    )
                retry_feedback = _build_transport_ai_retry_feedback_payload(
                    error_code=last_error_code or "transport_ai_agent_invalid_response",
                    message=last_error_message or "Transport AI returned an invalid structured response.",
                    technical_detail=last_error_detail or last_error_message or "Transport AI returned an invalid structured response.",
                    correction="Return only a valid TransportAgentPlan that matches the required schema exactly.",
                    issues=[
                        _build_transport_ai_runtime_issue(
                            code=last_error_code or "transport_ai_agent_invalid_response",
                            message=last_error_detail or last_error_message or "Transport AI returned an invalid structured response.",
                            message_key=last_message_key,
                            message_params=last_message_params,
                            setting_name="transport_ai_llm_runtime",
                        )
                    ],
                    message_key=last_message_key,
                    message_params=last_message_params,
                )
                continue

            current_phase = "validation"
            validation_started_at = perf_counter()
            validation_result = _validate_transport_ai_plan_deterministically(
                planning_input=planning_input,
                plan=plan,
            )
            if observability_summary is not None:
                _add_transport_ai_phase_duration(
                    observability_summary,
                    phase_field="validation_ms",
                    duration_ms=_measure_transport_ai_phase_ms(validation_started_at),
                )
            if not validation_result.ok:
                last_error_code = "transport_ai_agent_plan_invalid_after_response"
                last_error_detail = _sanitize_transport_ai_string_with_runtime_secrets(
                    _build_transport_ai_deterministic_validation_failure_message(validation_result),
                    settings_obj=settings_obj,
                    runtime_secret_literals=runtime_secret_literals,
                )
                last_error_message, last_message_key, last_message_params = _resolve_transport_ai_failure_contract(
                    error_code=last_error_code,
                    fallback_message=last_error_detail,
                    llm_provider=run.llm_provider,
                    llm_model=effective_model_name,
                    route_provider=run.route_provider,
                )
                retry_feedback = _build_transport_ai_retry_feedback_from_validation(
                    validation_result,
                    error_code=last_error_code,
                    message=last_error_message,
                    technical_detail=last_error_detail,
                    message_key=last_message_key,
                    message_params=last_message_params,
                )
                continue

            _update_transport_ai_run_status(
                db=db,
                run=run,
                status="proposed",
                settings_obj=settings_obj,
                completed=True,
            )
            _maybe_sync_transport_ai_run_observability(
                db=db,
                run=run,
                context=context,
                settings_obj=settings_obj,
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
                observability=observability_summary,
            )

        failure_code = last_error_code or "transport_ai_agent_invalid_response"
        technical_failure_message = last_error_detail or last_error_message or (
            "Transport AI agent exhausted retries without producing a valid structured plan."
        )
        if last_error_message is None:
            failure_message, failure_message_key, failure_message_params = _resolve_transport_ai_failure_contract(
                error_code=failure_code,
                fallback_message=technical_failure_message,
                llm_provider=run.llm_provider,
                llm_model=effective_model_name,
                route_provider=run.route_provider,
            )
        else:
            failure_message = last_error_message
            failure_message_key = last_message_key
            failure_message_params = dict(last_message_params)
        failure_issues = [
            _build_transport_ai_runtime_issue(
                code=failure_code,
                message=technical_failure_message,
                message_key=failure_message_key,
                message_params=failure_message_params,
                setting_name=(
                    "transport_ai_validation"
                    if failure_code in {"transport_ai_agent_plan_invalid_after_response", "transport_ai_deterministic_plan_invalid"}
                    else "transport_ai_llm_runtime"
                ),
            )
        ]
        if observability_summary is not None:
            _mark_transport_ai_observability_failure(
                observability_summary,
                failure_layer="llm",
                failed_phase=(
                    "validation"
                    if failure_code in {"transport_ai_agent_plan_invalid_after_response", "transport_ai_deterministic_plan_invalid"}
                    else "llm"
                ),
            )
        _update_transport_ai_run_status(
            db=db,
            run=run,
            status="failed",
            settings_obj=settings_obj,
            error_code=failure_code,
            error_message=failure_message,
            issues=failure_issues,
            completed=True,
        )
        _maybe_sync_transport_ai_run_observability(
            db=db,
            run=run,
            context=context,
            settings_obj=settings_obj,
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
            message_key=failure_message_key,
            message_params=failure_message_params,
            issues=failure_issues,
            observability=observability_summary,
        )
    except Exception as exc:
        if observability_summary is None and context.state.planning_input is not None:
            observability_summary = _ensure_transport_ai_observability_summary(context, run=run)
        if observability_summary is not None:
            if isinstance(exc, TransportRouteProviderError):
                _mark_transport_ai_observability_failure(
                    observability_summary,
                    failure_layer="route_provider",
                    failed_phase=exc.operation,
                )
            elif current_phase in {"llm_runtime", "llm"}:
                _mark_transport_ai_observability_failure(
                    observability_summary,
                    failure_layer="llm",
                    failed_phase="llm" if current_phase == "llm" else current_phase,
                )
            else:
                _mark_transport_ai_observability_failure(
                    observability_summary,
                    failure_layer="local",
                    failed_phase=current_phase or "planning",
                )
        raw_failure_message = (
            exc.primary_issue_message
            if isinstance(exc, TransportAIToolExecutionError)
            else str(exc)
        )
        technical_failure_message = _sanitize_transport_ai_string_with_runtime_secrets(
            raw_failure_message,
            settings_obj=settings_obj,
            runtime_secret_literals=runtime_secret_literals,
        )
        failure_code = "transport_ai_agent_execution_failed"
        failure_issues: list[TransportAIPreflightIssue]
        failure_message_key: str | None = None
        failure_message_params: TransportAIMessageParams = {}
        if isinstance(exc, TransportRouteProviderError):
            failure_code, failure_message, failure_message_key, failure_message_params, failure_issues = _build_transport_ai_route_provider_failure_details(
                exc,
                settings_obj=settings_obj,
                runtime_secret_literals=runtime_secret_literals,
            )
        elif isinstance(exc, TransportAILlmSettingsValidationError):
            failure_message = technical_failure_message
            failure_issues = [
                _build_transport_ai_runtime_issue(
                    code=failure_code,
                    message=technical_failure_message,
                    message_key=None,
                    message_params={},
                    setting_name="transport_ai_llm_runtime",
                )
            ]
        elif isinstance(exc, TransportAIToolExecutionError):
            failure_code = str(exc.error_code or "").strip() or failure_code
            failure_message, failure_message_key, failure_message_params = _resolve_transport_ai_failure_contract(
                error_code=failure_code,
                fallback_message=technical_failure_message,
                llm_provider=run.llm_provider,
                llm_model=effective_model_name,
                route_provider=run.route_provider,
            )
            if failure_message_key is None and exc.message_key:
                failure_message_key = exc.message_key
            if not failure_message_params and exc.message_params:
                failure_message_params = dict(exc.message_params)
            failure_issues = _build_transport_ai_runtime_issues_from_tool_issues(
                [
                    issue.model_copy(
                        update={
                            "message": _sanitize_transport_ai_string_with_runtime_secrets(
                                issue.message,
                                settings_obj=settings_obj,
                                runtime_secret_literals=runtime_secret_literals,
                            )
                        }
                    )
                    for issue in exc.issues
                ]
            )
        else:
            failure_message, failure_message_key, failure_message_params = _resolve_transport_ai_failure_contract(
                error_code=failure_code,
                fallback_message=technical_failure_message,
                llm_provider=run.llm_provider,
                llm_model=effective_model_name,
                route_provider=run.route_provider,
            )
            failure_issues = [
                _build_transport_ai_runtime_issue(
                    code=failure_code,
                    message=technical_failure_message,
                    message_key=failure_message_key,
                    message_params=failure_message_params,
                    setting_name="transport_ai_runtime",
                )
            ]
        _update_transport_ai_run_status(
            db=db,
            run=run,
            status="failed",
            settings_obj=settings_obj,
            error_code=failure_code,
            error_message=failure_message,
            issues=failure_issues,
            completed=True,
        )
        _maybe_sync_transport_ai_run_observability(
            db=db,
            run=run,
            context=context,
            settings_obj=settings_obj,
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
            error_code=failure_code,
            error_message=failure_message,
            message_key=failure_message_key,
            message_params=failure_message_params,
            issues=failure_issues,
            observability=observability_summary,
        )
