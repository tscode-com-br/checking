from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import Settings, normalize_transport_ai_agent_mode, settings
from ..models import TransportAIRun
from ..schemas import (
    TransportAIFailureCategory,
    TransportAIReviewState,
    TransportAgentPlanningInput,
    TransportAgentProjectLlmRuntimeSnapshot,
    TransportAIPreflightCheckResult,
    TransportAIPreflightIssue,
)
from .location_settings import get_transport_pricing_settings
from .transport_proposals import build_transport_dashboard_scope_labels
from .transport_ai_llm_settings import (
    TransportAILlmRuntimeSettings,
    TransportAILlmSettingsEncryptionError,
    TransportAILlmSettingsProjectNotFoundError,
    TransportAILlmSettingsValidationError,
    get_supported_transport_ai_llm_providers,
    resolve_transport_ai_llm_runtime_settings,
    validate_transport_ai_settings_encryption_availability,
)


_TRANSPORT_AI_ACTIVE_RUN_STATUSES = (
    "requested",
    "baseline_saved",
    "passengers_reset",
    "running",
)
_TRANSPORT_AI_FAILURE_CATEGORY_BY_CODE: dict[str, TransportAIFailureCategory] = {
    "transport_ai_disabled": "configuration",
    "transport_ai_agent_mode_invalid": "configuration",
    "transport_ai_settings_encryption_unavailable": "configuration",
    "transport_ai_llm_settings_missing": "configuration",
    "transport_ai_llm_provider_invalid": "configuration",
    "transport_ai_llm_api_key_missing": "configuration",
    "transport_ai_llm_project_missing": "configuration",
    "transport_ai_llm_runtime_conflict": "configuration",
    "transport_ai_operational_approval_missing": "configuration",
    "transport_ai_pricing_missing": "configuration",
    "transport_ai_max_passengers_per_run_invalid": "configuration",
    "transport_ai_max_runtime_seconds_invalid": "configuration",
    "transport_ai_max_concurrent_runs_invalid": "configuration",
    "mapbox_access_token_missing": "configuration",
    "mapbox_geocode_no_result": "geocoding",
    "transport_ai_deterministic_plan_invalid": "deterministic_validation",
    "transport_ai_agent_plan_invalid_after_response": "deterministic_validation",
    "route_kind_invalid": "configuration",
    "service_date_mismatch": "configuration",
    "route_kind_mismatch": "configuration",
    "no_eligible_requests": "empty_scope",
    "max_passengers_per_run_exceeded": "capacity",
    "transport_ai_concurrency_limit_reached": "capacity",
    "transport_ai_partition_no_vehicle_candidates": "capacity",
    "transport_ai_partition_missing_route_points": "geocoding",
    "transport_ai_partition_no_solution": "solver",
    "transport_ai_request_unallocated": "solver",
    "transport_ai_agent_model_invoke_failed": "llm_invoke",
    "transport_ai_agent_invalid_response": "llm_response",
    "transport_ai_reset_failed": "unexpected",
    "transport_ai_agent_execution_failed": "unexpected",
    "transport_ai_route_calculation_failed": "unexpected",
    "transport_ai_route_calculation_unhandled_error": "unexpected",
}

_TRANSPORT_AI_ROUTE_OPERATION_LABELS = {
    "geocode": "geocoding",
    "matrix": "route matrix calculation",
    "directions": "directions calculation",
}


@dataclass(frozen=True, slots=True)
class TransportAIMessageDescriptor:
    message_key: str
    message_params: dict[str, Any]
    message: str


def _build_transport_ai_preflight_issue(
    *,
    code: str,
    message: str,
    setting_name: str | None = None,
    blocking: bool = True,
) -> TransportAIPreflightIssue:
    return TransportAIPreflightIssue(
        code=code,
        message=message,
        blocking=blocking,
        setting_name=setting_name,
    )


def _normalize_transport_ai_issue_codes(issue_codes: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    normalized_codes: list[str] = []
    for raw_code in issue_codes or ():
        normalized_code = str(raw_code or "").strip().lower()
        if normalized_code:
            normalized_codes.append(normalized_code)
    return tuple(normalized_codes)


def _resolve_transport_ai_failure_category_from_code(
    code: str | None,
) -> TransportAIFailureCategory | None:
    normalized_code = str(code or "").strip().lower()
    if not normalized_code:
        return None
    if normalized_code in _TRANSPORT_AI_FAILURE_CATEGORY_BY_CODE:
        return _TRANSPORT_AI_FAILURE_CATEGORY_BY_CODE[normalized_code]
    if normalized_code == "mapbox_geocode_no_result":
        return "geocoding"
    if normalized_code.startswith("transport_ai_plan_"):
        return "deterministic_validation"
    if normalized_code.startswith("transport_ai_duplicate_"):
        return "deterministic_validation"
    if normalized_code.startswith("transport_ai_vehicle_reference_"):
        return "deterministic_validation"
    if normalized_code.startswith("transport_ai_request_missing_for_"):
        return "deterministic_validation"
    if "route_point" in normalized_code:
        return "geocoding"
    if normalized_code.startswith("mapbox_"):
        return "route_provider"
    if "route_matrix" in normalized_code or "pair_no_route" in normalized_code or "segment_missing" in normalized_code:
        return "route_provider"
    if normalized_code.startswith("transport_ai_partition_"):
        return "solver"
    if normalized_code.startswith("transport_ai_route_"):
        return "solver"
    if normalized_code.startswith("transport_ai_return_leg_"):
        return "solver"
    if normalized_code.startswith("transport_ai_extra_return_"):
        return "solver"
    return None


def resolve_transport_ai_failure_category(
    *,
    error_code: str | None = None,
    issue_codes: list[str] | tuple[str, ...] | None = None,
) -> TransportAIFailureCategory | None:
    normalized_issue_codes = _normalize_transport_ai_issue_codes(issue_codes)
    for issue_code in normalized_issue_codes:
        category = _resolve_transport_ai_failure_category_from_code(issue_code)
        if category is not None:
            return category
    category = _resolve_transport_ai_failure_category_from_code(error_code)
    if category is not None:
        return category
    if normalized_issue_codes or str(error_code or "").strip():
        return "unexpected"
    return None


def resolve_transport_ai_review_state(
    *,
    run_status: str | None,
    has_suggestion: bool,
    suggestion_issue_codes: list[str] | tuple[str, ...] | None = None,
) -> TransportAIReviewState:
    normalized_status = str(run_status or "").strip().lower()
    normalized_issue_codes = _normalize_transport_ai_issue_codes(suggestion_issue_codes)
    if has_suggestion:
        return "review_with_exceptions" if normalized_issue_codes else "review_ready"
    if normalized_status == "failed":
        return "fatal_error"
    return "unavailable"


def _format_transport_ai_provider_label(provider: str | None) -> str:
    normalized_provider = str(provider or "").strip().lower()
    if normalized_provider == "openai":
        return "OpenAI"
    if normalized_provider == "deepseek":
        return "DeepSeek"
    if normalized_provider == "mapbox":
        return "Mapbox"
    return normalized_provider or "the configured provider"


def _build_transport_ai_llm_message_descriptor(
    *,
    error_code: str,
    llm_provider: str | None,
    llm_model: str | None,
) -> TransportAIMessageDescriptor | None:
    provider_label = _format_transport_ai_provider_label(llm_provider)
    model_name = str(llm_model or "").strip() or None
    params = {
        "provider": provider_label,
        "model": model_name,
    }

    if error_code == "transport_ai_llm_settings_missing":
        return TransportAIMessageDescriptor(
            message_key="transport_ai.error.llm_settings_missing",
            message_params=params,
            message="Transport AI cannot calculate routes because the selected scope has no AI settings configured.",
        )
    if error_code == "transport_ai_llm_provider_invalid":
        return TransportAIMessageDescriptor(
            message_key="transport_ai.error.llm_provider_invalid",
            message_params=params,
            message="Transport AI cannot calculate routes because the selected scope is configured with an unsupported AI provider.",
        )
    if error_code == "transport_ai_llm_api_key_missing":
        return TransportAIMessageDescriptor(
            message_key="transport_ai.error.llm_api_key_missing",
            message_params=params,
            message=f"Transport AI cannot calculate routes because {provider_label} is missing an API key.",
        )
    if error_code == "transport_ai_llm_runtime_conflict":
        return TransportAIMessageDescriptor(
            message_key="transport_ai.error.llm_runtime_conflict",
            message_params=params,
            message="Transport AI cannot calculate routes because the selected scope mixes incompatible AI settings in the same run.",
        )
    if error_code == "transport_ai_agent_model_invoke_failed":
        return TransportAIMessageDescriptor(
            message_key="transport_ai.error.llm_invoke_failed",
            message_params=params,
            message=f"Transport AI could not obtain a route calculation response from {provider_label}.",
        )
    if error_code == "transport_ai_agent_invalid_response":
        return TransportAIMessageDescriptor(
            message_key="transport_ai.error.llm_invalid_response",
            message_params=params,
            message=f"Transport AI received an invalid structured response from {provider_label}.",
        )
    if error_code == "transport_ai_agent_plan_invalid_after_response":
        return TransportAIMessageDescriptor(
            message_key="transport_ai.error.llm_plan_invalid_after_response",
            message_params=params,
            message=f"Transport AI received a route plan from {provider_label}, but deterministic validation rejected it before review.",
        )
    if error_code == "transport_ai_deterministic_plan_invalid":
        return TransportAIMessageDescriptor(
            message_key="transport_ai.error.deterministic_plan_invalid",
            message_params={},
            message="Transport AI produced a route plan, but deterministic validation rejected it before review.",
        )
    return None


def _build_transport_ai_mapbox_message_descriptor(error_code: str) -> TransportAIMessageDescriptor | None:
    normalized_code = str(error_code or "").strip().lower()
    if normalized_code == "mapbox_access_token_missing":
        return TransportAIMessageDescriptor(
            message_key="transport_ai.error.mapbox_access_token_missing",
            message_params={"provider": "Mapbox"},
            message="Transport AI cannot calculate routes because the Mapbox access token is not configured.",
        )

    prefix = "mapbox_"
    if not normalized_code.startswith(prefix):
        return None

    remainder = normalized_code[len(prefix):]
    operation, separator, suffix = remainder.partition("_")
    operation_label = _TRANSPORT_AI_ROUTE_OPERATION_LABELS.get(operation)
    if not separator or operation_label is None:
        return None

    params = {
        "provider": "Mapbox",
        "operation": operation,
        "operation_label": operation_label,
    }

    if suffix == "auth_failed":
        return TransportAIMessageDescriptor(
            message_key=f"transport_ai.error.mapbox_{operation}_auth_failed",
            message_params=params,
            message=f"Transport AI could not use Mapbox for {operation_label} because the configured token was rejected.",
        )
    if suffix == "timeout":
        return TransportAIMessageDescriptor(
            message_key=f"transport_ai.error.mapbox_{operation}_timeout",
            message_params=params,
            message=f"Transport AI timed out while waiting for Mapbox {operation_label}.",
        )
    if suffix == "request_4xx":
        return TransportAIMessageDescriptor(
            message_key=f"transport_ai.error.mapbox_{operation}_request_4xx",
            message_params=params,
            message=f"Transport AI could not finish Mapbox {operation_label} because Mapbox rejected the request.",
        )
    if suffix == "request_5xx":
        return TransportAIMessageDescriptor(
            message_key=f"transport_ai.error.mapbox_{operation}_request_5xx",
            message_params=params,
            message=f"Transport AI could not finish Mapbox {operation_label} because Mapbox returned a server error.",
        )
    if suffix == "invalid_response":
        return TransportAIMessageDescriptor(
            message_key=f"transport_ai.error.mapbox_{operation}_invalid_response",
            message_params=params,
            message=f"Transport AI received an invalid Mapbox response during {operation_label}.",
        )
    if suffix == "no_result":
        return TransportAIMessageDescriptor(
            message_key=f"transport_ai.error.mapbox_{operation}_no_result",
            message_params=params,
            message="Transport AI could not geocode at least one required address with Mapbox.",
        )
    if suffix == "no_route":
        return TransportAIMessageDescriptor(
            message_key=f"transport_ai.error.mapbox_{operation}_no_route",
            message_params=params,
            message=(
                "Transport AI could not calculate routes because Mapbox reported at least one unreachable route matrix cell."
                if operation == "matrix"
                else f"Transport AI could not calculate routes because Mapbox did not return a valid result for {operation_label}."
            ),
        )
    return None


def resolve_transport_ai_message_descriptor(
    *,
    error_code: str | None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    route_provider: str | None = None,
) -> TransportAIMessageDescriptor | None:
    normalized_code = str(error_code or "").strip().lower()
    if not normalized_code:
        return None

    mapbox_descriptor = _build_transport_ai_mapbox_message_descriptor(normalized_code)
    if mapbox_descriptor is not None:
        return mapbox_descriptor

    llm_descriptor = _build_transport_ai_llm_message_descriptor(
        error_code=normalized_code,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )
    if llm_descriptor is not None:
        return llm_descriptor

    if normalized_code == "transport_ai_agent_execution_failed":
        return TransportAIMessageDescriptor(
            message_key="transport_ai.error.unexpected_runtime_failure",
            message_params={
                "llm_provider": _format_transport_ai_provider_label(llm_provider),
                "route_provider": _format_transport_ai_provider_label(route_provider),
            },
            message="Transport AI could not complete the route calculation because an unexpected runtime error occurred.",
        )
    if normalized_code == "transport_ai_route_calculation_unhandled_error":
        return TransportAIMessageDescriptor(
            message_key="transport_ai.error.unhandled_failure",
            message_params={
                "llm_provider": _format_transport_ai_provider_label(llm_provider),
                "route_provider": _format_transport_ai_provider_label(route_provider),
            },
            message="Transport AI could not complete the route calculation because an unexpected server error occurred.",
        )
    return None


@dataclass(frozen=True, slots=True)
class TransportAIProjectLlmRuntimeContext:
    project_id: int
    project_name: str
    partition_keys: tuple[str, ...]
    runtime_settings: TransportAILlmRuntimeSettings


def _collect_transport_ai_planning_projects(
    planning_input: TransportAgentPlanningInput,
) -> list[tuple[int, str, tuple[str, ...]]]:
    project_rows_by_id: dict[int, tuple[str, list[str]]] = {}

    for partition in planning_input.partitions:
        project_name, partition_keys = project_rows_by_id.setdefault(
            int(partition.project_id),
            (partition.project_name, []),
        )
        if project_name != partition.project_name:
            project_name = partition.project_name
        partition_keys.append(partition.partition_key)
        project_rows_by_id[int(partition.project_id)] = (project_name, partition_keys)

    return [
        (
            project_id,
            project_rows_by_id[project_id][0],
            tuple(sorted(set(project_rows_by_id[project_id][1]))),
        )
        for project_id in sorted(project_rows_by_id)
    ]


def _normalize_transport_ai_runtime_project_name(project_name: str | None) -> str:
    return " ".join(str(project_name or "").strip().split())


def _collect_transport_ai_selected_project_names(planning_input: TransportAgentPlanningInput) -> list[str]:
    project_names = list(planning_input.dashboard_scope_project_names or [])
    if not project_names:
        project_names = [
            project_name
            for _project_id, project_name, _partition_keys in _collect_transport_ai_planning_projects(planning_input)
        ]

    normalized_names: list[str] = []
    seen_names: set[str] = set()
    for project_name in project_names:
        normalized_name = _normalize_transport_ai_runtime_project_name(project_name)
        if not normalized_name:
            continue
        normalized_key = normalized_name.upper()
        if normalized_key in seen_names:
            continue
        seen_names.add(normalized_key)
        normalized_names.append(normalized_name)
    return normalized_names


def _summarize_transport_ai_selected_projects(planning_input: TransportAgentPlanningInput, *, max_names: int = 3) -> str:
    project_names = _collect_transport_ai_selected_project_names(planning_input)
    if not project_names:
        return ""
    if len(project_names) <= max_names:
        return ", ".join(project_names)
    remaining_count = len(project_names) - max_names
    return f"{', '.join(project_names[:max_names])}, and {remaining_count} more"


def _build_transport_ai_selected_projects_label(planning_input: TransportAgentPlanningInput) -> str:
    project_summary = _summarize_transport_ai_selected_projects(planning_input)
    scope_labels = build_transport_dashboard_scope_labels(
        dashboard_scope=planning_input.dashboard_scope,
        project_summary=project_summary,
        project_filter_applied=bool(planning_input.dashboard_scope and planning_input.dashboard_scope.project_ids),
    )
    if scope_labels:
        return " and ".join(scope_labels)
    if project_summary:
        return f"referenced projects ({project_summary})"
    return "referenced projects"


def resolve_transport_ai_project_llm_runtime_contexts(
    db: Session,
    *,
    planning_input: TransportAgentPlanningInput,
    settings_obj: Settings = settings,
) -> list[TransportAIProjectLlmRuntimeContext]:
    resolved_contexts: list[TransportAIProjectLlmRuntimeContext] = []

    for project_id, project_name, partition_keys in _collect_transport_ai_planning_projects(planning_input):
        runtime_settings = resolve_transport_ai_llm_runtime_settings(
            db,
            project_id=project_id,
            settings_obj=settings_obj,
        )
        resolved_contexts.append(
            TransportAIProjectLlmRuntimeContext(
                project_id=project_id,
                project_name=project_name,
                partition_keys=partition_keys,
                runtime_settings=runtime_settings,
            )
        )

    return resolved_contexts


def build_transport_ai_project_llm_runtime_snapshots(
    resolved_contexts: list[TransportAIProjectLlmRuntimeContext],
) -> list[TransportAgentProjectLlmRuntimeSnapshot]:
    return [
        TransportAgentProjectLlmRuntimeSnapshot(
            project_id=context.project_id,
            project_name=context.project_name,
            partition_keys=list(context.partition_keys),
            provider=context.runtime_settings.provider,
            model_name=context.runtime_settings.model_name,
            reasoning_effort=context.runtime_settings.reasoning_effort,
        )
        for context in resolved_contexts
    ]


def resolve_transport_ai_shared_llm_runtime_context(
    db: Session,
    *,
    planning_input: TransportAgentPlanningInput,
    settings_obj: Settings = settings,
) -> tuple[TransportAILlmRuntimeSettings, list[TransportAgentProjectLlmRuntimeSnapshot]]:
    resolved_contexts = resolve_transport_ai_project_llm_runtime_contexts(
        db,
        planning_input=planning_input,
        settings_obj=settings_obj,
    )
    if not resolved_contexts:
        selected_projects_label = _build_transport_ai_selected_projects_label(planning_input)
        raise TransportAILlmSettingsValidationError(
            "Transport AI planning input does not reference any eligible project partitions "
            f"within the {selected_projects_label}."
        )

    first_runtime_settings = resolved_contexts[0].runtime_settings
    selected_projects_label = _build_transport_ai_selected_projects_label(planning_input)
    conflicting_project_names = sorted(
        {
            context.project_name
            for context in resolved_contexts
            if context.runtime_settings != first_runtime_settings
        }
    )
    if conflicting_project_names:
        project_names = ", ".join(conflicting_project_names)
        raise TransportAILlmSettingsValidationError(
            "Transport AI agent mode currently requires the same project-specific LLM provider, model, "
            f"reasoning effort, and API key across all {selected_projects_label} in a single run. "
            f"Conflicting projects: {project_names}."
        )

    return first_runtime_settings, build_transport_ai_project_llm_runtime_snapshots(resolved_contexts)


def _build_transport_ai_project_runtime_issue(
    *,
    code: str,
    message: str,
    setting_name: str,
) -> TransportAIPreflightIssue:
    return _build_transport_ai_preflight_issue(
        code=code,
        message=message,
        setting_name=setting_name,
    )


def _build_transport_ai_project_runtime_preflight_issues(
    db: Session,
    *,
    planning_input: TransportAgentPlanningInput,
    settings_obj: Settings,
) -> list[TransportAIPreflightIssue]:
    issues: list[TransportAIPreflightIssue] = []
    resolved_contexts: list[TransportAIProjectLlmRuntimeContext] = []

    for project_id, project_name, partition_keys in _collect_transport_ai_planning_projects(planning_input):
        try:
            runtime_settings = resolve_transport_ai_llm_runtime_settings(
                db,
                project_id=project_id,
                settings_obj=settings_obj,
            )
        except TransportAILlmSettingsProjectNotFoundError:
            issues.append(
                _build_transport_ai_project_runtime_issue(
                    code="transport_ai_llm_project_missing",
                    message=(
                        f"Transport AI project '{project_name}' is no longer available for runtime resolution."
                    ),
                    setting_name="transport_ai_llm_settings",
                )
            )
            continue
        except TransportAILlmSettingsEncryptionError:
            issues.append(
                _build_transport_ai_project_runtime_issue(
                    code="transport_ai_llm_api_key_missing",
                    message=(
                        f"Transport AI API key for project '{project_name}' is missing or could not be decrypted."
                    ),
                    setting_name="transport_ai_llm_api_key",
                )
            )
            continue
        except TransportAILlmSettingsValidationError as exc:
            normalized_message = str(exc).strip()
            normalized_message_lower = normalized_message.lower()
            if "api key" in normalized_message_lower:
                issues.append(
                    _build_transport_ai_project_runtime_issue(
                        code="transport_ai_llm_api_key_missing",
                        message=(
                            f"Transport AI API key has not been configured for project '{project_name}' yet."
                        ),
                        setting_name="transport_ai_llm_api_key",
                    )
                )
            elif "provider" in normalized_message_lower and "supported" in normalized_message_lower:
                issues.append(
                    _build_transport_ai_project_runtime_issue(
                        code="transport_ai_llm_provider_invalid",
                        message=(
                            f"The configured Transport AI LLM provider for project '{project_name}' is not supported."
                        ),
                        setting_name="transport_ai_llm_provider",
                    )
                )
            else:
                issues.append(
                    _build_transport_ai_project_runtime_issue(
                        code="transport_ai_llm_settings_missing",
                        message=(
                            f"Transport AI LLM settings have not been configured for project '{project_name}' yet."
                        ),
                        setting_name="transport_ai_llm_settings",
                    )
                )
            continue

        resolved_contexts.append(
            TransportAIProjectLlmRuntimeContext(
                project_id=project_id,
                project_name=project_name,
                partition_keys=partition_keys,
                runtime_settings=runtime_settings,
            )
        )

    if issues:
        return issues

    if not resolved_contexts:
        return issues

    first_runtime_settings = resolved_contexts[0].runtime_settings
    selected_projects_label = _build_transport_ai_selected_projects_label(planning_input)
    conflicting_project_names = sorted(
        {
            context.project_name
            for context in resolved_contexts
            if context.runtime_settings != first_runtime_settings
        }
    )
    if conflicting_project_names:
        issues.append(
            _build_transport_ai_project_runtime_issue(
                code="transport_ai_llm_runtime_conflict",
                message=(
                    "Transport AI agent mode currently requires the same project-specific LLM provider, model, "
                    f"reasoning effort, and API key across all {selected_projects_label} in a single run. "
                    f"Conflicting projects: {', '.join(conflicting_project_names)}."
                ),
                setting_name="transport_ai_llm_settings",
            )
        )

    return issues


def get_transport_ai_operational_readiness_issues(
    *,
    settings_obj: Settings = settings,
) -> list[TransportAIPreflightIssue]:
    issues: list[TransportAIPreflightIssue] = []

    if not str(settings_obj.transport_ai_operational_approval_evidence or "").strip():
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_operational_approval_missing",
                message=(
                    "Transport AI requires explicit operational approval evidence covering resource approval "
                    "and dedicated load validation before new runs can start."
                ),
                setting_name="transport_ai_operational_approval_evidence",
            )
        )

    if settings_obj.transport_ai_max_concurrent_runs <= 0:
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_max_concurrent_runs_invalid",
                message="The maximum concurrent Transport AI runs must be greater than zero.",
                setting_name="transport_ai_max_concurrent_runs",
            )
        )

    if settings_obj.transport_ai_max_runtime_seconds <= 0:
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_max_runtime_seconds_invalid",
                message="The maximum Transport AI runtime must be greater than zero seconds.",
                setting_name="transport_ai_max_runtime_seconds",
            )
        )

    return issues


def count_transport_ai_active_runs(db: Session) -> int:
    return int(
        db.execute(
            select(func.count(TransportAIRun.id)).where(TransportAIRun.status.in_(_TRANSPORT_AI_ACTIVE_RUN_STATUSES))
        ).scalar_one()
        or 0
    )


def build_transport_ai_concurrency_limit_issue(
    *,
    active_run_count: int,
    settings_obj: Settings = settings,
) -> TransportAIPreflightIssue:
    return _build_transport_ai_preflight_issue(
        code="transport_ai_concurrency_limit_reached",
        message=(
            f"Transport AI already has {active_run_count} active run(s), which meets the configured "
            f"limit of {settings_obj.transport_ai_max_concurrent_runs}."
        ),
        setting_name="transport_ai_max_concurrent_runs",
    )


def validate_transport_ai_runtime_configuration(
    db: Session,
    *,
    settings_obj: Settings = settings,
    planning_input: TransportAgentPlanningInput | None = None,
) -> TransportAIPreflightCheckResult:
    issues: list[TransportAIPreflightIssue] = []

    if not bool(settings_obj.transport_ai_enabled):
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_disabled",
                message="Transport AI is disabled in the server configuration.",
                setting_name="transport_ai_enabled",
            )
        )
        return TransportAIPreflightCheckResult(ok=False, issues=issues)

    agent_mode = normalize_transport_ai_agent_mode(settings_obj.transport_ai_agent_mode)
    if agent_mode is None:
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_agent_mode_invalid",
                message="Transport AI agent mode must be 'agent' or 'deterministic'.",
                setting_name="transport_ai_agent_mode",
            )
        )
    elif agent_mode == "agent":
        settings_encryption_available = True
        try:
            validate_transport_ai_settings_encryption_availability(settings_obj=settings_obj)
        except TransportAILlmSettingsEncryptionError:
            settings_encryption_available = False
            issues.append(
                _build_transport_ai_preflight_issue(
                    code="transport_ai_settings_encryption_unavailable",
                    message="Transport AI settings encryption key is missing or invalid in the server configuration.",
                    setting_name="transport_ai_settings_encryption_key",
                )
            )

        if planning_input is not None and settings_encryption_available:
            issues.extend(
                _build_transport_ai_project_runtime_preflight_issues(
                    db,
                    planning_input=planning_input,
                    settings_obj=settings_obj,
                )
            )

    if not str(settings_obj.mapbox_access_token or "").strip():
        issues.append(
            _build_transport_ai_preflight_issue(
                code="mapbox_access_token_missing",
                message="The Mapbox access token is not configured.",
                setting_name="mapbox_access_token",
            )
        )

    pricing_settings = get_transport_pricing_settings(db)
    configured_prices = (
        pricing_settings["default_car_price"],
        pricing_settings["default_minivan_price"],
        pricing_settings["default_van_price"],
        pricing_settings["default_bus_price"],
    )
    if all(price is None for price in configured_prices):
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_pricing_missing",
                message="At least one transport vehicle price must be configured before running Transport AI.",
                setting_name="transport_pricing",
            )
        )

    issues.extend(get_transport_ai_operational_readiness_issues(settings_obj=settings_obj))

    if settings_obj.transport_ai_max_passengers_per_run <= 0:
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_max_passengers_per_run_invalid",
                message="The Transport AI partition batch size must be greater than zero.",
                setting_name="transport_ai_max_passengers_per_run",
            )
        )

    return TransportAIPreflightCheckResult(
        ok=not any(issue.blocking for issue in issues),
        issues=issues,
    )