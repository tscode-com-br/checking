import json
from datetime import date
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..core.config import normalize_transport_ai_agent_mode, settings
from ..database import get_db
from ..models import (
    Project,
    TransportAIRun,
    TransportAISuggestion,
    TransportVehicleSchedule,
    TransportVehicleScheduleException,
    User,
    Vehicle,
)
from ..schemas import (
    TransportAIObservabilitySummary,
    TransportAIRunDiagnosticsEntry,
    TransportAIRunDiagnosticsResponse,
    TransportAIPreflightCheckResult,
    TransportAIPreflightIssue,
    TransportAISettingsResponse,
    TransportAISettingsUpdateRequest,
    TransportAgentDashboardScope,
    TransportAgentPlan,
    TransportAgentPlanningInput,
    TransportAgentRouteStop,
    TransportAgentRouteRequest,
    TransportAgentRunIssue,
    TransportAgentSuggestionAudit,
    TransportAgentSuggestionAuditCluster,
    TransportAgentRunStartResponse,
    TransportAgentRunStatusResponse,
    TransportAgentRunSuggestion,
    TransportIdentity,
    TransportOperationalProposal,
    TransportProposalDecision,
    TransportProposalValidationIssue,
    TransportVehicleCreate,
    TransportVehicleScheduleUpdate,
    TransportVehicleUpdate,
)
from ..services.admin_auth import require_transport_session
from ..services.admin_updates import notify_admin_data_changed
from ..services.location_settings import get_transport_settings_payload
from ..services.time_utils import now_sgt
from ..services.transport_ai_llm_settings import (
    TransportAILlmSettingsEncryptionError,
    TransportAILlmSettingsProjectNotFoundError,
    TransportAILlmSettingsValidationError,
    get_transport_ai_llm_settings,
    get_transport_ai_llm_settings_payload,
    upsert_transport_ai_llm_settings,
)
from ..services.transport_ai_sanitization import sanitize_transport_ai_string
from ..services.transport import create_transport_vehicle_registration, update_transport_vehicle_base
from ..services.transport_ai_agent import run_transport_ai_agent
from ..services.transport_ai_observability import (
    record_transport_ai_lifecycle_transition,
    record_transport_ai_settings_update,
)
from ..services.transport_ai_applied_route_stops import (
    TransportAIAppliedRouteStopInput,
    persist_transport_ai_applied_route_stops,
)
from ..services.transport_ai_planning import (
    build_transport_agent_planning_input,
    build_transport_proposal_from_agent_plan,
)
from ..services.transport_ai_runs import (
    capture_transport_ai_baseline,
    create_transport_ai_suggestion_from_plan,
    ensure_transport_ai_actor_admin_user,
    resolve_transport_ai_run_llm_snapshot_fields,
    get_latest_active_transport_ai_suggestion,
    get_latest_transport_ai_suggestion_for_run,
    get_transport_ai_suggestion_by_key,
    reset_transport_ai_requests_to_pending,
    restore_transport_ai_baseline,
    save_transport_ai_baseline,
    save_transport_ai_planning_input,
    set_transport_ai_suggestion_status,
)
from ..services.transport_ai_runtime import (
    build_transport_ai_concurrency_limit_issue,
    count_transport_ai_active_runs,
    resolve_transport_ai_failure_category,
    resolve_transport_ai_message_descriptor,
    resolve_transport_ai_review_state,
    resolve_transport_ai_shared_llm_runtime_context,
    validate_transport_ai_runtime_configuration,
)
from ..services.transport_proposals import (
    build_transport_dashboard_scope_labels,
    list_transport_dashboard_scope_request_kind_labels,
)
from ..services.transport_proposals import (
    apply_transport_operational_proposal,
    approve_transport_operational_proposal,
    build_transport_operational_proposal_contract,
    proposal_has_blocking_issues,
    validate_transport_operational_proposal,
)
from ..services.transport_reevaluation_events import emit_transport_reevaluation_event
from ..services.transport_vehicle_schedule import (
    find_transport_vehicle_schedule,
    update_transport_vehicle_schedule,
    vehicle_schedule_applies_to_date,
)


router = APIRouter(
    prefix="/api/transport/ai",
    tags=["transport-ai"],
    dependencies=[Depends(require_transport_session)],
)


_TRANSPORT_AI_REGULAR_WEEKDAY_FLAG_BY_INDEX = {
    0: "every_monday",
    1: "every_tuesday",
    2: "every_wednesday",
    3: "every_thursday",
    4: "every_friday",
}
_TRANSPORT_AI_WEEKEND_FLAG_BY_INDEX = {
    5: "every_saturday",
    6: "every_sunday",
}
_TRANSPORT_AI_CREATE_RECURRENCE_FLAG_NAMES = (
    "every_weekend",
    "every_saturday",
    "every_sunday",
    "every_monday",
    "every_tuesday",
    "every_wednesday",
    "every_thursday",
    "every_friday",
)
_TRANSPORT_AI_DEFAULT_CAPACITY_SETTING_BY_TYPE = {
    "carro": "default_car_seats",
    "minivan": "default_minivan_seats",
    "van": "default_van_seats",
    "onibus": "default_bus_seats",
}
_TRANSPORT_AI_RUN_ALLOWED_STATUSES = (
    "requested",
    "baseline_saved",
    "passengers_reset",
    "running",
    "proposed",
    "saved",
    "applied",
    "cancelled",
    "failed",
)
_TRANSPORT_AI_USAGE_CONTAINER_KEYS = {
    "usage",
    "usage_metadata",
    "token_usage",
    "response_metadata",
    "llm_output",
}
_TRANSPORT_AI_USAGE_TOKEN_KEYS = {
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "input_tokens",
    "output_tokens",
}
_TRANSPORT_AI_USAGE_COST_KEYS = (
    "estimated_cost_usd",
    "approximate_cost_usd",
    "call_cost_usd",
    "usage_cost_usd",
    "total_cost_usd",
    "estimated_price_usd",
    "cost_usd",
    "usd_cost",
    "estimated_cost",
    "approximate_cost",
    "call_cost",
    "total_cost",
)
_TRANSPORT_AI_SETTINGS_MESSAGE_KEY_BY_DETAIL = {
    "Transport AI project does not exist.": "ai.settingsProjectMissing",
    "Transport AI API key is required.": "ai.settingsKeyRequired",
    "Transport AI API key is required when creating LLM settings.": "ai.settingsKeyRequired",
    "Transport AI API key is required when changing the LLM provider.": "ai.settingsProviderKeyRequired",
    "Transport AI API key is required when no encrypted key has been stored yet.": "ai.settingsKeyRequired",
    "The configured Transport AI LLM provider is no longer supported. Select OpenAI or DeepSeek and save the AI settings again.": (
        "ai.settingsProviderUnsupported"
    ),
    "Transport AI settings encryption is unavailable.": "ai.settingsEncryptionUnavailable",
}


def _transport_ai_router_json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _transport_ai_router_json_loads(value: str | None) -> object | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None


def _resolve_transport_ai_settings_message_key(detail: str, default_key: str) -> str:
    normalized_detail = str(detail or "").strip()
    if not normalized_detail:
        return default_key
    return _TRANSPORT_AI_SETTINGS_MESSAGE_KEY_BY_DETAIL.get(normalized_detail, default_key)


def _build_transport_ai_router_issue(
    *,
    code: str,
    message: str | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    issue: dict[str, object] = {"code": code}
    normalized_message = str(message or "").strip()
    if normalized_message:
        issue["message"] = normalized_message
    if extra:
        issue.update(extra)
    return issue


def _raise_transport_ai_router_structured_http_error(
    *,
    status_code: int,
    message: str,
    message_key: str,
    error_code: str,
    message_params: dict[str, object] | None = None,
    issues: list[dict[str, object]] | None = None,
    technical_detail: str | None = None,
) -> None:
    normalized_technical_detail = str(technical_detail or "").strip() or None
    normalized_issues = list(issues or [])
    if not normalized_issues:
        normalized_issues = [
            _build_transport_ai_router_issue(
                code=error_code,
                message=normalized_technical_detail,
            )
        ]
    raise HTTPException(
        status_code=status_code,
        detail={
            "message": message,
            "message_key": message_key,
            "message_params": dict(message_params or {}),
            "error_code": error_code,
            "issues": normalized_issues,
            "technical_detail": normalized_technical_detail,
        },
    )
    try:
        return json.loads(normalized)
    except (TypeError, ValueError):
        return None


def _measure_transport_ai_router_elapsed_ms(started_at: float) -> int:
    return max(0, int(round((perf_counter() - started_at) * 1000)))


def _resolve_transport_ai_router_llm_summary_fields(
    *,
    planning_input: TransportAgentPlanningInput,
    llm_provider: str | None,
    llm_model: str | None,
    llm_reasoning_effort: str | None,
) -> tuple[str | None, str | None, str | None]:
    unique_snapshots = {
        (snapshot.provider, snapshot.model_name, snapshot.reasoning_effort)
        for snapshot in planning_input.llm_runtime_projects
    }
    if len(unique_snapshots) == 1:
        return next(iter(unique_snapshots))
    if len(unique_snapshots) > 1:
        return ("multiple", "multiple", "multiple")
    return (
        str(llm_provider or "").strip().lower() or None,
        str(llm_model or "").strip() or None,
        str(llm_reasoning_effort or "").strip().lower() or None,
    )


def _ensure_transport_ai_planning_observability(
    *,
    planning_input: TransportAgentPlanningInput,
    route_provider: str | None,
    llm_provider: str | None,
    llm_model: str | None,
    llm_reasoning_effort: str | None,
) -> TransportAgentPlanningInput:
    llm_provider, llm_model, llm_reasoning_effort = _resolve_transport_ai_router_llm_summary_fields(
        planning_input=planning_input,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_reasoning_effort=llm_reasoning_effort,
    )
    if planning_input.observability is None:
        observability = TransportAIObservabilitySummary(
            total_eligible_request_count=planning_input.total_requests,
            partition_count=len(planning_input.partitions),
            route_provider=route_provider,
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_reasoning_effort=llm_reasoning_effort,
            partitions=[
                {
                    "partition_key": partition.partition_key,
                    "request_kind": partition.request_kind,
                    "project_name": partition.project_name,
                    "eligible_request_count": len(partition.requests),
                    "candidate_vehicle_count": len(partition.candidate_vehicles),
                }
                for partition in planning_input.partitions
            ],
        )
        return planning_input.model_copy(update={"observability": observability})

    planning_input.observability.total_eligible_request_count = planning_input.total_requests
    planning_input.observability.partition_count = len(planning_input.partitions)
    planning_input.observability.route_provider = route_provider
    planning_input.observability.llm_provider = llm_provider
    planning_input.observability.llm_model = llm_model
    planning_input.observability.llm_reasoning_effort = llm_reasoning_effort
    return planning_input


def _load_transport_ai_run_planning_input_model(run: TransportAIRun) -> TransportAgentPlanningInput | None:
    planning_input_json = str(run.planning_input_json or "").strip()
    if not planning_input_json:
        return None
    try:
        return TransportAgentPlanningInput.model_validate_json(planning_input_json)
    except Exception:
        return None


def _set_transport_ai_planning_phase_duration(
    planning_input: TransportAgentPlanningInput,
    *,
    phase_field: str,
    duration_ms: int,
) -> TransportAgentPlanningInput:
    effective_planning_input = planning_input
    if effective_planning_input.observability is None:
        effective_planning_input = _ensure_transport_ai_planning_observability(
            planning_input=effective_planning_input,
            route_provider=None,
            llm_provider=None,
            llm_model=None,
            llm_reasoning_effort=None,
        )
    current_duration = getattr(effective_planning_input.observability.phase_durations_ms, phase_field)
    setattr(
        effective_planning_input.observability.phase_durations_ms,
        phase_field,
        max(duration_ms, 0) if current_duration is None else current_duration + max(duration_ms, 0),
    )
    return effective_planning_input


def _mark_transport_ai_planning_observability_failure(
    planning_input: TransportAgentPlanningInput,
    *,
    failure_layer: str,
    failed_phase: str,
) -> TransportAgentPlanningInput:
    effective_planning_input = planning_input
    if effective_planning_input.observability is None:
        effective_planning_input = _ensure_transport_ai_planning_observability(
            planning_input=effective_planning_input,
            route_provider=None,
            llm_provider=None,
            llm_model=None,
            llm_reasoning_effort=None,
        )
    if not effective_planning_input.observability.failure_layer:
        effective_planning_input.observability.failure_layer = failure_layer
    if not effective_planning_input.observability.failed_phase:
        effective_planning_input.observability.failed_phase = failed_phase
    return effective_planning_input


def _extract_transport_ai_run_observability(run: TransportAIRun) -> TransportAIObservabilitySummary | None:
    payload = _transport_ai_router_json_loads(run.planning_input_json)
    if not isinstance(payload, dict):
        return None
    raw_observability = payload.get("observability")
    if not isinstance(raw_observability, dict):
        return None
    try:
        return TransportAIObservabilitySummary.model_validate(raw_observability)
    except Exception:
        return None


def _build_transport_ai_observability_event_summary(
    observability: TransportAIObservabilitySummary | None,
) -> dict[str, object] | None:
    if observability is None:
        return None

    compact_partitions = [
        {
            "partition_key": partition.partition_key,
            "request_kind": partition.request_kind,
            "eligible_request_count": partition.eligible_request_count,
            "matrix_chunk_count": partition.matrix_chunk_count,
            "solver_algorithm": partition.solver_algorithm,
        }
        for partition in sorted(
            observability.partitions,
            key=lambda partition: (-partition.eligible_request_count, partition.partition_key),
        )[:3]
    ]
    phase_durations = {
        key: value
        for key, value in observability.phase_durations_ms.model_dump(mode="json").items()
        if value is not None
    }
    return {
        "total_eligible_request_count": observability.total_eligible_request_count,
        "partition_count": observability.partition_count,
        "route_provider": observability.route_provider,
        "llm_provider": observability.llm_provider,
        "llm_model": observability.llm_model,
        "llm_attempt_count": observability.llm_attempt_count,
        "geocode_provider_call_count": observability.geocode_provider_call_count,
        "matrix_provider_call_count": observability.matrix_provider_call_count,
        "matrix_chunk_count": observability.matrix_chunk_count,
        "failure_layer": observability.failure_layer,
        "failed_phase": observability.failed_phase,
        "phase_durations_ms": phase_durations,
        "partitions": compact_partitions,
        "remaining_partition_count": max(0, len(observability.partitions) - len(compact_partitions)),
    }


def _truncate_transport_ai_router_message(message: str, *, max_length: int = 500) -> str:
    normalized = " ".join(str(message or "").strip().split())
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[: max_length - 3]}..."


def _sanitize_transport_ai_router_message(
    message: str,
    *,
    extra_literal_secrets: tuple[str | None, ...] = (),
    max_length: int = 500,
) -> str:
    return _truncate_transport_ai_router_message(
        sanitize_transport_ai_string(
            str(message or ""),
            extra_literal_secrets=extra_literal_secrets,
        ),
        max_length=max_length,
    )


_TRANSPORT_AI_ROUTER_BASELINE_RESTORE_NOTE_ALIASES = (
    ("Baseline restored.", "Baseline restored successfully."),
    ("Baseline restored successfully.", "Baseline restored successfully."),
    ("Baseline restore raised an unexpected error.", "Baseline restore raised an unexpected error."),
    (
        "Baseline restore remains available but requires manual review.",
        "Baseline restore remains available but requires manual review.",
    ),
)


def _normalize_transport_ai_router_message_text(
    message: str,
    *,
    extra_literal_secrets: tuple[str | None, ...] = (),
) -> str:
    return " ".join(
        sanitize_transport_ai_string(
            str(message or ""),
            extra_literal_secrets=extra_literal_secrets,
        ).strip().split()
    )


def _ensure_transport_ai_router_sentence(message: str) -> str:
    normalized = " ".join(str(message or "").strip().split())
    if not normalized:
        return ""
    if normalized.endswith((".", "!", "?")):
        return normalized
    return f"{normalized}."


def _resolve_transport_ai_router_restore_note(message: str) -> str | None:
    normalized = _normalize_transport_ai_router_message_text(message)
    if not normalized:
        return None
    for suffix, resolved_note in _TRANSPORT_AI_ROUTER_BASELINE_RESTORE_NOTE_ALIASES:
        if normalized.endswith(suffix):
            return resolved_note
    return None


def _strip_transport_ai_router_restore_note(message: str) -> str:
    normalized = _normalize_transport_ai_router_message_text(message)
    if not normalized:
        return ""
    for suffix, _resolved_note in _TRANSPORT_AI_ROUTER_BASELINE_RESTORE_NOTE_ALIASES:
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)].strip()
    return normalized


def _is_transport_ai_router_generic_failure_message(message: str) -> bool:
    normalized = _strip_transport_ai_router_restore_note(message)
    if not normalized:
        return True
    return (
        normalized == "Transport AI runtime preflight failed."
        or normalized == "Transport AI route calculation failed."
        or normalized.startswith("Transport AI planning validation failed")
        or normalized.startswith("Transport AI route calculation has no eligible pending requests")
    )


def _resolve_transport_ai_router_primary_issue_message(issues: list[object] | None) -> str | None:
    normalized_issues = list(issues or [])
    for issue in normalized_issues:
        issue_message = _normalize_transport_ai_router_message_text(getattr(issue, "message", ""))
        if issue_message and bool(getattr(issue, "blocking", True)):
            return issue_message
    for issue in normalized_issues:
        issue_message = _normalize_transport_ai_router_message_text(getattr(issue, "message", ""))
        if issue_message:
            return issue_message
    return None


def _resolve_transport_ai_router_primary_issue_code(issues: list[object] | None) -> str | None:
    normalized_issues = list(issues or [])
    for issue in normalized_issues:
        issue_code = str(getattr(issue, "code", "") or "").strip().lower()
        if issue_code and bool(getattr(issue, "blocking", True)):
            return issue_code
    for issue in normalized_issues:
        issue_code = str(getattr(issue, "code", "") or "").strip().lower()
        if issue_code:
            return issue_code
    return None


def _compose_transport_ai_router_failure_message(
    *,
    headline: str,
    restore_note: str | None = None,
    max_length: int = 500,
) -> str:
    normalized_headline = _ensure_transport_ai_router_sentence(headline)
    if not restore_note:
        return _truncate_transport_ai_router_message(normalized_headline, max_length=max_length)

    normalized_restore_note = _ensure_transport_ai_router_sentence(restore_note)
    combined_message = f"{normalized_headline} {normalized_restore_note}"
    if len(combined_message) <= max_length:
        return combined_message
    if len(normalized_headline) >= max_length:
        return _truncate_transport_ai_router_message(normalized_headline, max_length=max_length)

    remaining_length = max_length - len(normalized_headline) - 1
    if remaining_length <= 0:
        return normalized_headline
    return f"{normalized_headline} {_truncate_transport_ai_router_message(normalized_restore_note, max_length=remaining_length)}"


def _build_transport_ai_router_failure_contract(
    *,
    message: str,
    error_code: str | None = None,
    issues: list[object] | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    route_provider: str | None = None,
    extra_literal_secrets: tuple[str | None, ...] = (),
    max_length: int = 500,
) -> tuple[str, str | None, dict[str, object]]:
    normalized_message = _normalize_transport_ai_router_message_text(
        message,
        extra_literal_secrets=extra_literal_secrets,
    )
    restore_note = _resolve_transport_ai_router_restore_note(normalized_message)
    normalized_headline = _strip_transport_ai_router_restore_note(normalized_message)
    primary_issue_message = _resolve_transport_ai_router_primary_issue_message(issues)
    effective_error_code = error_code or _resolve_transport_ai_router_primary_issue_code(issues)
    message_descriptor = resolve_transport_ai_message_descriptor(
        error_code=effective_error_code,
        llm_provider=llm_provider,
        llm_model=llm_model,
        route_provider=route_provider,
    )

    message_key: str | None = None
    message_params: dict[str, object] = {}

    if message_descriptor is not None:
        normalized_headline = message_descriptor.message
        message_key = message_descriptor.message_key
        message_params = dict(message_descriptor.message_params)

    if message_descriptor is None and primary_issue_message and (
        _is_transport_ai_router_generic_failure_message(normalized_message) or not normalized_headline
    ):
        normalized_headline = primary_issue_message
    elif not normalized_headline:
        normalized_headline = primary_issue_message or "Transport AI route calculation failed."

    return (
        _compose_transport_ai_router_failure_message(
            headline=normalized_headline,
            restore_note=restore_note,
            max_length=max_length,
        ),
        message_key,
        message_params,
    )


def _build_transport_ai_router_failure_message(
    *,
    message: str,
    error_code: str | None = None,
    issues: list[object] | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    route_provider: str | None = None,
    extra_literal_secrets: tuple[str | None, ...] = (),
    max_length: int = 500,
) -> str:
    resolved_message, _message_key, _message_params = _build_transport_ai_router_failure_contract(
        message=message,
        error_code=error_code,
        issues=issues,
        llm_provider=llm_provider,
        llm_model=llm_model,
        route_provider=route_provider,
        extra_literal_secrets=extra_literal_secrets,
        max_length=max_length,
    )
    return resolved_message


def _normalize_transport_ai_router_project_name(project_name: str | None) -> str:
    return " ".join(str(project_name or "").strip().split())


def _dedupe_transport_ai_router_project_names(project_names: list[str]) -> list[str]:
    normalized_names: list[str] = []
    seen_names: set[str] = set()

    for project_name in project_names:
        normalized_name = _normalize_transport_ai_router_project_name(project_name)
        if not normalized_name:
            continue
        normalized_key = normalized_name.upper()
        if normalized_key in seen_names:
            continue
        seen_names.add(normalized_key)
        normalized_names.append(normalized_name)

    return normalized_names


def _summarize_transport_ai_router_project_scope(project_names: list[str], *, max_names: int = 3) -> str:
    normalized_names = _dedupe_transport_ai_router_project_names(project_names)
    if not normalized_names:
        return ""
    if len(normalized_names) <= max_names:
        return ", ".join(normalized_names)
    remaining_count = len(normalized_names) - max_names
    return f"{', '.join(normalized_names[:max_names])}, and {remaining_count} more"


def _resolve_transport_ai_dashboard_scope_project_names(
    db: Session,
    *,
    dashboard_scope: TransportAgentDashboardScope | None,
) -> list[str]:
    if dashboard_scope is None or not dashboard_scope.project_ids:
        return []

    project_rows = db.execute(
        select(Project)
        .where(Project.id.in_(dashboard_scope.project_ids))
        .order_by(Project.name.asc(), Project.id.asc())
    ).scalars().all()
    return _dedupe_transport_ai_router_project_names([
        project_row.name
        for project_row in project_rows
    ])


def _build_transport_ai_dashboard_scope_audit_details(
    *,
    dashboard_scope: TransportAgentDashboardScope | None,
    project_names: list[str],
    max_preview_names: int = 5,
) -> dict[str, object]:
    normalized_project_names = _dedupe_transport_ai_router_project_names(project_names)
    normalized_request_kind_labels = list_transport_dashboard_scope_request_kind_labels(
        dashboard_scope,
        include_all=True,
    )
    return {
        "dashboard_scope": (
            dashboard_scope.model_dump(mode="json")
            if dashboard_scope is not None
            else None
        ),
        "dashboard_scope_project_names": normalized_project_names[:max_preview_names],
        "dashboard_scope_project_count": len(normalized_project_names),
        "dashboard_scope_request_kind_labels": normalized_request_kind_labels[:max_preview_names],
        "dashboard_scope_request_kind_count": len(normalized_request_kind_labels),
    }


def _build_transport_ai_dashboard_scope_phrase(
    *,
    dashboard_scope: TransportAgentDashboardScope | None,
    project_names: list[str],
) -> str:
    scope_labels = build_transport_dashboard_scope_labels(
        dashboard_scope=dashboard_scope,
        project_summary=_summarize_transport_ai_router_project_scope(project_names),
        project_filter_applied=bool(dashboard_scope and dashboard_scope.project_ids),
    )
    if not scope_labels:
        return ""
    return f" for the {' and '.join(scope_labels)}"


def _record_transport_ai_settings_failure_event(
    db: Session,
    *,
    transport_user: User,
    project_id: int,
    project_name: str | None,
    provider: str | None,
    api_key: str | None,
    previous_provider: str | None,
    request_path: str,
    http_status: int,
    failure_detail: str,
    response_detail: str,
    timestamp,
) -> None:
    db.rollback()
    actor_admin_user = ensure_transport_ai_actor_admin_user(
        db,
        chave=transport_user.chave,
        nome_completo=transport_user.nome,
        ensured_at=timestamp,
    )
    from ..services.transport_ai_observability import record_transport_ai_settings_failure

    record_transport_ai_settings_failure(
        db,
        actor_admin_user=actor_admin_user,
        project_id=project_id,
        project_name=project_name,
        provider=provider,
        api_key=api_key,
        previous_provider=previous_provider,
        failure_detail=failure_detail,
        response_detail=response_detail,
        request_path=request_path,
        http_status=http_status,
    )
    db.commit()
    notify_admin_data_changed("event")


def _build_transport_ai_run_preflight_issues(run: TransportAIRun) -> list[TransportAgentRunIssue]:
    payload = _transport_ai_router_json_loads(run.preflight_issues_json)
    if not isinstance(payload, list):
        return []

    issues: list[TransportAgentRunIssue] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        message = item.get("message")
        raw_source = str(item.get("source") or "run_preflight").strip().lower()
        source = raw_source if raw_source in {"run_preflight", "run_error"} else "run_preflight"
        if not code or not message:
            continue
        issues.append(
            TransportAgentRunIssue(
                code=str(code),
                message=_truncate_transport_ai_router_message(str(message)),
                blocking=bool(item.get("blocking", True)),
                source=source,
                setting_name=item.get("setting_name"),
                request_id=item.get("request_id"),
                vehicle_id=item.get("vehicle_id"),
            )
        )
    return issues


def _build_transport_ai_poll_suggestion_response(
    suggestion,
    *,
    run: TransportAIRun | None = None,
) -> tuple[TransportAgentRunSuggestion | None, list[TransportAgentRunIssue]]:
    if suggestion is None:
        return None, []

    payload = _transport_ai_router_json_loads(suggestion.agent_plan_json)
    if not isinstance(payload, dict):
        return (
            None,
            [
                TransportAgentRunIssue(
                    code="transport_ai_suggestion_payload_invalid",
                    message="The stored transport AI suggestion payload is unavailable.",
                    blocking=True,
                    source="suggestion_validation",
                )
            ],
        )

    try:
        plan = TransportAgentPlan.model_validate(payload)
    except Exception as exc:
        return (
            None,
            [
                TransportAgentRunIssue(
                    code="transport_ai_suggestion_payload_invalid",
                    message=_truncate_transport_ai_router_message(
                        f"The stored transport AI suggestion payload could not be loaded: {exc}",
                    ),
                    blocking=True,
                    source="suggestion_validation",
                )
            ],
        )

    issues = [
        TransportAgentRunIssue(
            code=issue.code,
            message=issue.message,
            blocking=issue.blocking,
            source="suggestion_validation",
            request_id=issue.request_id,
            vehicle_id=issue.vehicle_id,
        )
        for issue in plan.validation_issues
    ]
    suggestion_audit = _build_transport_ai_suggestion_audit(run=run) if run is not None else None
    return (
        TransportAgentRunSuggestion(
            suggestion_key=suggestion.suggestion_key,
            proposal_key=suggestion.proposal_key,
            status=suggestion.status,
            prompt_version=suggestion.prompt_version,
            created_at=suggestion.created_at,
            updated_at=suggestion.updated_at,
            saved_at=suggestion.saved_at,
            applied_at=suggestion.applied_at,
            discarded_at=suggestion.discarded_at,
            plan=plan,
            audit=suggestion_audit,
        ),
        issues,
    )


def _load_transport_ai_suggestion_plan(
    suggestion,
) -> tuple[TransportAgentPlan | None, list[TransportAgentRunIssue]]:
    suggestion_response, issues = _build_transport_ai_poll_suggestion_response(suggestion)
    if suggestion_response is None:
        return None, issues
    return suggestion_response.plan, issues


def _load_transport_ai_suggestion_proposal(suggestion) -> TransportOperationalProposal | None:
    payload = _transport_ai_router_json_loads(suggestion.transport_proposal_json)
    if not isinstance(payload, dict):
        return None
    try:
        return TransportOperationalProposal.model_validate(payload)
    except Exception:
        return None


def _persist_transport_ai_suggestion_proposal(
    *,
    suggestion,
    proposal: TransportOperationalProposal,
    changed_at,
) -> None:
    suggestion.proposal_key = proposal.proposal_key
    suggestion.transport_proposal_json = _transport_ai_router_json_dumps(proposal.model_dump(mode="json"))
    suggestion.updated_at = changed_at


def _build_transport_ai_run_issue_from_validation_issue(
    issue: TransportProposalValidationIssue,
    *,
    source: str = "suggestion_validation",
) -> TransportAgentRunIssue:
    return TransportAgentRunIssue(
        code=issue.code,
        message=issue.message,
        blocking=issue.blocking,
        source=source,
        request_id=issue.request_id,
        vehicle_id=issue.vehicle_id,
    )


def _build_transport_ai_run_status_message(
    *,
    run: TransportAIRun,
    suggestion,
    suggestion_response: TransportAgentRunSuggestion | None,
    issues: list[TransportAgentRunIssue],
) -> str:
    if run.status == "failed":
        return _build_transport_ai_router_failure_message(
            message=run.error_message or "Transport AI route calculation failed.",
            error_code=run.error_code,
            issues=issues,
            llm_provider=run.llm_provider,
            llm_model=run.llm_model,
            route_provider=run.route_provider,
        )
    if run.status == "requested":
        return "Transport AI route calculation was requested."
    if run.status == "baseline_saved":
        return "Transport AI saved the dashboard baseline and is preparing the route calculation."
    if run.status == "passengers_reset":
        return "Transport AI reset eligible passengers to pending and is preparing the route calculation."
    if run.status == "running":
        return "Transport AI route calculation is running."
    if run.status == "proposed":
        if suggestion_response is not None:
            return "Transport AI suggestion is ready for review."
        if suggestion is not None:
            return "Transport AI finished, but the persisted suggestion payload is unavailable."
        return "Transport AI finished, but no persisted suggestion is available yet."
    if run.status == "saved":
        return "Transport AI suggestion was saved and is ready to be applied."
    if run.status == "applied":
        return "Transport AI suggestion was applied."
    if run.status == "cancelled":
        return "Transport AI suggestion was cancelled and the baseline was restored."
    return "Transport AI route calculation status is unavailable."


def _resolve_transport_ai_run_status_message_contract(
    *,
    run: TransportAIRun,
    suggestion,
    suggestion_response: TransportAgentRunSuggestion | None,
) -> tuple[str | None, dict[str, object]]:
    if run.status == "proposed" and suggestion_response is not None:
        return "ai.agentSettingsReadyForReview", {}
    if run.status == "saved":
        return "ai.changesSaved", {}
    if run.status == "applied":
        return "ai.changesApplied", {}
    if run.status == "cancelled":
        return "ai.changesCancelled", {}
    if run.status == "proposed" and suggestion is None:
        return "ai.routeCalculationFailed", {}
    return None, {}


def _extract_transport_ai_issue_codes(raw_value: str | None) -> tuple[list[str], int]:
    payload = _transport_ai_router_json_loads(raw_value)
    if not isinstance(payload, list):
        return [], 0

    issue_codes: list[str] = []
    blocking_count = 0
    for item in payload:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip().lower().replace(" ", "_")
        if not code:
            continue
        issue_codes.append(code)
        if bool(item.get("blocking", True)):
            blocking_count += 1
    return issue_codes, blocking_count


def _iter_transport_ai_usage_containers(value: object, *, path: tuple[str, ...] = ()):
    if isinstance(value, dict):
        normalized_keys = {str(key).lower() for key in value.keys()}
        if (path and path[-1] in _TRANSPORT_AI_USAGE_CONTAINER_KEYS) or normalized_keys.intersection(_TRANSPORT_AI_USAGE_TOKEN_KEYS):
            yield value
        for key, item in value.items():
            yield from _iter_transport_ai_usage_containers(item, path=(*path, str(key).lower()))
        return

    if isinstance(value, list):
        for item in value:
            yield from _iter_transport_ai_usage_containers(item, path=path)


def _coerce_transport_ai_diagnostic_int(value: object) -> int | None:
    if value in {None, ""} or isinstance(value, bool):
        return None
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        return None
    return coerced if coerced >= 0 else None


def _coerce_transport_ai_diagnostic_float(value: object) -> float | None:
    if value in {None, ""} or isinstance(value, bool):
        return None
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return None
    return coerced if coerced >= 0 else None


def _extract_transport_ai_usage_summary(raw_value: str | None) -> dict[str, object]:
    payload = _transport_ai_router_json_loads(raw_value)
    if not isinstance(payload, dict):
        return {}

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    approximate_cost: float | None = None
    approximate_cost_currency: str | None = None

    for container in _iter_transport_ai_usage_containers(payload):
        if not isinstance(container, dict):
            continue
        normalized = {str(key).lower(): item for key, item in container.items()}
        if prompt_tokens is None:
            prompt_tokens = _coerce_transport_ai_diagnostic_int(
                normalized.get("prompt_tokens", normalized.get("input_tokens"))
            )
        if completion_tokens is None:
            completion_tokens = _coerce_transport_ai_diagnostic_int(
                normalized.get("completion_tokens", normalized.get("output_tokens"))
            )
        if total_tokens is None:
            total_tokens = _coerce_transport_ai_diagnostic_int(normalized.get("total_tokens"))

        if approximate_cost is None:
            has_usage_shape = any(key in normalized for key in _TRANSPORT_AI_USAGE_TOKEN_KEYS)
            for cost_key in _TRANSPORT_AI_USAGE_COST_KEYS:
                if cost_key not in normalized:
                    continue
                if not has_usage_shape and cost_key in {"estimated_cost", "approximate_cost", "call_cost", "total_cost"}:
                    continue
                approximate_cost = _coerce_transport_ai_diagnostic_float(normalized.get(cost_key))
                if approximate_cost is None:
                    continue
                if approximate_cost_currency is None:
                    if cost_key.endswith("_usd") or cost_key == "usd_cost":
                        approximate_cost_currency = "USD"
                    else:
                        approximate_cost_currency = str(
                            normalized.get("currency")
                            or normalized.get("cost_currency")
                            or normalized.get("estimated_cost_currency")
                            or ""
                        ).strip() or None
                break

        if prompt_tokens is not None and completion_tokens is not None and total_tokens is not None and approximate_cost is not None:
            break

    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "approximate_model_call_cost": approximate_cost,
        "approximate_model_call_cost_currency": approximate_cost_currency,
        "has_raw_model_response": True,
    }


def _build_transport_ai_run_duration_seconds(*, run: TransportAIRun, reference_time) -> int | None:
    ended_at = run.completed_at or reference_time
    duration_seconds = int((ended_at - run.created_at).total_seconds())
    return max(duration_seconds, 0)


def _build_transport_ai_runs_diagnostics_response(
    runs: list[TransportAIRun],
    *,
    latest_suggestion_by_run_id: dict[int, TransportAISuggestion],
    reference_time,
) -> list[TransportAIRunDiagnosticsEntry]:
    entries: list[TransportAIRunDiagnosticsEntry] = []

    for run in runs:
        suggestion = latest_suggestion_by_run_id.get(run.id)
        llm_fields = resolve_transport_ai_run_llm_snapshot_fields(run)
        preflight_issue_codes, preflight_blocking_count = _extract_transport_ai_issue_codes(run.preflight_issues_json)
        validation_issue_codes, validation_blocking_count = _extract_transport_ai_issue_codes(
            suggestion.validation_issues_json if suggestion is not None else None
        )
        usage_summary = _extract_transport_ai_usage_summary(
            suggestion.raw_model_response_json if suggestion is not None else None
        )
        observability = _extract_transport_ai_run_observability(run)
        diagnostics_message_key: str | None = None
        diagnostics_message_params: dict[str, object] = {}
        diagnostics_error_message = (
            _truncate_transport_ai_router_message(
                sanitize_transport_ai_string(run.error_message),
            )
            if run.error_message
            else None
        )
        if run.error_code:
            diagnostics_error_message, diagnostics_message_key, diagnostics_message_params = _build_transport_ai_router_failure_contract(
                message=run.error_message or "Transport AI route calculation failed.",
                error_code=run.error_code,
                issues=[],
                llm_provider=llm_fields["llm_provider"],
                llm_model=llm_fields["llm_model"],
                route_provider=run.route_provider,
            )
        entries.append(
            TransportAIRunDiagnosticsEntry(
                run_key=run.run_key,
                service_date=run.service_date,
                route_kind=run.route_kind,
                status=run.status,
                llm_provider=llm_fields["llm_provider"],
                llm_model=llm_fields["llm_model"],
                llm_reasoning_effort=llm_fields["llm_reasoning_effort"],
                openai_model=llm_fields["openai_model"],
                route_provider=run.route_provider,
                suggestion_key=suggestion.suggestion_key if suggestion is not None else None,
                suggestion_status=suggestion.status if suggestion is not None else None,
                prompt_version=suggestion.prompt_version if suggestion is not None else None,
                created_at=run.created_at,
                updated_at=run.updated_at,
                completed_at=run.completed_at,
                duration_seconds=_build_transport_ai_run_duration_seconds(run=run, reference_time=reference_time),
                error_code=run.error_code,
                error_message=diagnostics_error_message,
                message_key=diagnostics_message_key,
                message_params=diagnostics_message_params,
                preflight_issue_codes=preflight_issue_codes,
                validation_issue_codes=validation_issue_codes,
                blocking_issue_count=preflight_blocking_count + validation_blocking_count,
                observability=observability,
                **usage_summary,
            )
        )
    return entries


def _build_transport_ai_run_status_response(
    *,
    run: TransportAIRun,
    suggestion,
) -> TransportAgentRunStatusResponse:
    llm_fields = resolve_transport_ai_run_llm_snapshot_fields(run)
    suggestion_response, suggestion_issues = _build_transport_ai_poll_suggestion_response(suggestion, run=run)
    issues = [*_build_transport_ai_run_preflight_issues(run), *suggestion_issues]
    issue_codes = [issue.code for issue in issues if issue.code]
    suggestion_issue_codes = [issue.code for issue in suggestion_issues if issue.code]
    has_blocking_issues = any(issue.blocking for issue in issues)
    suggestion_status = suggestion.status if suggestion is not None else None
    suggestion_ready = suggestion_response is not None and suggestion_status in {"shown", "saved"}
    can_save = (
        suggestion_response is not None
        and not has_blocking_issues
        and suggestion_status == "shown"
        and run.status in {"proposed", "saved"}
    )
    can_apply = (
        suggestion_response is not None
        and not has_blocking_issues
        and suggestion_status in {"shown", "saved"}
        and run.status in {"proposed", "saved"}
    )
    can_cancel_restore = suggestion_response is not None and suggestion_status in {"shown", "saved"} and run.status in {"proposed", "saved"}
    failure_category = (
        resolve_transport_ai_failure_category(
            error_code=run.error_code,
            issue_codes=issue_codes,
        )
        if run.status == "failed"
        else None
    )
    review_state = resolve_transport_ai_review_state(
        run_status=run.status,
        has_suggestion=suggestion_response is not None,
        suggestion_issue_codes=suggestion_issue_codes,
    )
    message_key, message_params = _resolve_transport_ai_run_status_message_contract(
        run=run,
        suggestion=suggestion,
        suggestion_response=suggestion_response,
    )
    message_text = _build_transport_ai_run_status_message(
        run=run,
        suggestion=suggestion,
        suggestion_response=suggestion_response,
        issues=issues,
    )
    if run.status == "failed":
        message_text, message_key, message_params = _build_transport_ai_router_failure_contract(
            message=run.error_message or "Transport AI route calculation failed.",
            error_code=run.error_code,
            issues=issues,
            llm_provider=llm_fields["llm_provider"],
            llm_model=llm_fields["llm_model"],
            route_provider=run.route_provider,
        )
    return TransportAgentRunStatusResponse(
        ok=run.status != "failed",
        run_key=run.run_key,
        service_date=run.service_date,
        route_kind=run.route_kind,
        status=run.status,
        llm_provider=llm_fields["llm_provider"],
        llm_model=llm_fields["llm_model"],
        llm_reasoning_effort=llm_fields["llm_reasoning_effort"],
        message=message_text,
        message_key=message_key,
        message_params=message_params,
        error_code=run.error_code,
        failure_category=failure_category,
        review_state=review_state,
        issues=issues,
        suggestion_key=suggestion.suggestion_key if suggestion is not None else None,
        suggestion_ready=suggestion_ready,
        can_save=can_save,
        can_apply=can_apply,
        can_cancel_restore=can_cancel_restore,
        created_at=run.created_at,
        updated_at=run.updated_at,
        completed_at=run.completed_at,
        suggestion=suggestion_response,
    )


def _normalize_transport_ai_audit_hash(value: object) -> str | None:
    normalized = str(value or "").strip().lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        return None
    return normalized


def _normalize_transport_ai_audit_time(value: object) -> str | None:
    normalized = str(value or "").strip()
    hour_text, separator, minute_text = normalized.partition(":")
    if separator != ":":
        return None
    if len(hour_text) != 2 or len(minute_text) != 2:
        return None
    if not hour_text.isdigit() or not minute_text.isdigit():
        return None
    hour = int(hour_text)
    minute = int(minute_text)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def _normalize_transport_ai_audit_request_ids(value: object) -> list[int]:
    if not isinstance(value, list):
        return []
    request_ids: list[int] = []
    for item in value:
        try:
            request_id = int(item)
        except (TypeError, ValueError):
            continue
        if request_id < 1:
            continue
        request_ids.append(request_id)
    return request_ids


def _build_transport_ai_suggestion_audit(
    *,
    run: TransportAIRun,
) -> TransportAgentSuggestionAudit | None:
    planning_input_payload = _transport_ai_router_json_loads(run.planning_input_json)
    if not isinstance(planning_input_payload, dict):
        planning_input_payload = {}

    settings_payload = planning_input_payload.get("settings")
    extra_car_tolerance_minutes = None
    if isinstance(settings_payload, dict):
        try:
            candidate_tolerance = int(settings_payload.get("extra_car_tolerance_minutes"))
        except (TypeError, ValueError):
            candidate_tolerance = None
        if candidate_tolerance is not None and candidate_tolerance >= 0:
            extra_car_tolerance_minutes = candidate_tolerance

    extra_clusters: list[TransportAgentSuggestionAuditCluster] = []
    partitions_payload = planning_input_payload.get("partitions")
    if isinstance(partitions_payload, list):
        for partition_payload in partitions_payload:
            if not isinstance(partition_payload, dict):
                continue
            if str(partition_payload.get("request_kind") or "").strip().lower() != "extra":
                continue
            partition_key = str(partition_payload.get("partition_key") or "").strip()
            if not partition_key:
                continue
            temporal_clusters_payload = partition_payload.get("temporal_request_clusters")
            if not isinstance(temporal_clusters_payload, list):
                continue
            for cluster_payload in temporal_clusters_payload:
                if not isinstance(cluster_payload, dict):
                    continue
                cluster_key = str(cluster_payload.get("cluster_key") or "").strip()
                anchor_requested_time = _normalize_transport_ai_audit_time(cluster_payload.get("anchor_requested_time"))
                earliest_requested_time = _normalize_transport_ai_audit_time(cluster_payload.get("earliest_requested_time"))
                latest_requested_time = _normalize_transport_ai_audit_time(cluster_payload.get("latest_requested_time"))
                request_ids = _normalize_transport_ai_audit_request_ids(cluster_payload.get("request_ids"))
                if (
                    not cluster_key
                    or anchor_requested_time is None
                    or earliest_requested_time is None
                    or latest_requested_time is None
                    or not request_ids
                ):
                    continue
                extra_clusters.append(
                    TransportAgentSuggestionAuditCluster(
                        partition_key=partition_key,
                        cluster_key=cluster_key,
                        anchor_requested_time=anchor_requested_time,
                        earliest_requested_time=earliest_requested_time,
                        latest_requested_time=latest_requested_time,
                        request_ids=request_ids,
                        request_count=len(request_ids),
                    )
                )

    if extra_clusters:
        extra_clusters.sort(key=lambda cluster: (cluster.anchor_requested_time, cluster.partition_key, cluster.cluster_key))

    planning_input_hash = _normalize_transport_ai_audit_hash(planning_input_payload.get("planning_input_hash"))
    if planning_input_hash is None:
        planning_input_hash = _normalize_transport_ai_audit_hash(run.planning_input_hash)

    if planning_input_hash is None and extra_car_tolerance_minutes is None and not extra_clusters:
        return None

    return TransportAgentSuggestionAudit(
        planning_input_hash=planning_input_hash,
        extra_car_tolerance_minutes=extra_car_tolerance_minutes,
        extra_clusters=extra_clusters,
    )


def _build_transport_ai_status_response_with_overrides(
    *,
    run: TransportAIRun,
    suggestion,
    ok: bool | None = None,
    message: str | None = None,
    message_key: str | None = None,
    message_params: dict[str, object] | None = None,
    error_code: str | None = None,
    extra_issues: list[TransportAgentRunIssue] | None = None,
) -> TransportAgentRunStatusResponse:
    base_response = _build_transport_ai_run_status_response(run=run, suggestion=suggestion)
    combined_issues = [*base_response.issues, *(extra_issues or [])]
    next_ok = base_response.ok if ok is None else ok
    combined_issue_codes = [issue.code for issue in combined_issues if issue.code]
    return base_response.model_copy(
        update={
            "ok": next_ok,
            "message": message or base_response.message,
            "message_key": message_key if message_key is not None else base_response.message_key,
            "message_params": dict(message_params or base_response.message_params),
            "error_code": error_code if error_code is not None else base_response.error_code,
            "issues": combined_issues,
            "failure_category": (
                resolve_transport_ai_failure_category(
                    error_code=(error_code if error_code is not None else base_response.error_code),
                    issue_codes=combined_issue_codes,
                )
                if not next_ok
                else None
            ),
            "review_state": resolve_transport_ai_review_state(
                run_status=base_response.status,
                has_suggestion=base_response.suggestion is not None,
                suggestion_issue_codes=combined_issue_codes,
            ),
            "can_save": base_response.can_save and not any(issue.blocking for issue in combined_issues),
            "can_apply": base_response.can_apply and not any(issue.blocking for issue in combined_issues),
        },
        deep=True,
    )


def _build_transport_ai_status_error_response(
    *,
    status_code: int,
    response: TransportAgentRunStatusResponse,
) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=response.model_dump(mode="json"))


def _load_transport_ai_suggestion_or_404(
    db: Session,
    *,
    suggestion_key: str,
) -> tuple[TransportAIRun, TransportAISuggestion]:
    suggestion = get_transport_ai_suggestion_by_key(db, suggestion_key=suggestion_key)
    if suggestion is None:
        _raise_transport_ai_router_structured_http_error(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Transport AI suggestion not found.",
            message_key="ai.loadLatestSuggestionFailed",
            error_code="transport_ai_suggestion_not_found",
            technical_detail="Transport AI suggestion not found.",
            issues=[
                _build_transport_ai_router_issue(
                    code="transport_ai_suggestion_not_found",
                    message="Transport AI suggestion not found.",
                    extra={"suggestion_key": suggestion_key},
                )
            ],
        )

    run = db.get(TransportAIRun, suggestion.run_id)
    if run is None:
        _raise_transport_ai_router_structured_http_error(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Transport AI run not found.",
            message_key="ai.routeCalculationFailed",
            error_code="transport_ai_run_not_found",
            technical_detail="Transport AI run not found.",
            issues=[
                _build_transport_ai_router_issue(
                    code="transport_ai_run_not_found",
                    message="Transport AI run not found.",
                    extra={"suggestion_key": suggestion_key},
                )
            ],
        )
    return run, suggestion


def _build_transport_ai_actor_identity(
    *,
    transport_user: User,
    actor_admin_user_id: int,
) -> TransportIdentity:
    return TransportIdentity(
        id=actor_admin_user_id,
        chave=transport_user.chave,
        nome_completo=transport_user.nome,
        perfil=transport_user.perfil,
    )


def _build_transport_ai_vehicle_ref_from_action(action) -> str | None:
    after = action.after or {}
    vehicle_ref = after.get("vehicle_ref")
    if isinstance(vehicle_ref, str) and vehicle_ref.strip():
        return vehicle_ref.strip()
    if action.vehicle_id is not None:
        return f"existing:{action.vehicle_id}"
    if action.action_type == "create" and action.client_vehicle_key:
        return f"new:{action.client_vehicle_key}"
    if action.client_vehicle_key:
        normalized = str(action.client_vehicle_key).strip()
        if normalized:
            return normalized
    return None


def _resolve_transport_ai_existing_vehicle_id(
    *,
    action,
    vehicle_ref: str,
) -> int | None:
    if action.vehicle_id is not None:
        return action.vehicle_id
    if not vehicle_ref.startswith("existing:"):
        return None
    try:
        return int(vehicle_ref.split(":", 1)[1])
    except (TypeError, ValueError):
        return None


def _get_transport_ai_action_state_value(
    state: dict[str, object],
    *keys: str,
) -> tuple[object | None, bool]:
    for key in keys:
        if key in state:
            return state.get(key), True
    return None, False


def _find_transport_ai_route_itinerary(
    *,
    plan: TransportAgentPlan,
    vehicle_ref: str,
):
    return next((item for item in plan.route_itineraries if item.vehicle_ref == vehicle_ref), None)


def _resolve_transport_ai_extra_eta(itinerary) -> str | None:
    if itinerary is None:
        return None
    if itinerary.service_scope != "extra" or itinerary.route_kind != "home_to_work":
        return None
    return itinerary.projected_arrival_time or None


def _resolve_transport_ai_extra_etd(itinerary) -> str | None:
    if itinerary is None:
        return None
    if itinerary.service_scope != "extra" or itinerary.route_kind != "work_to_home":
        return None
    for stop in itinerary.stops:
        if stop.scheduled_time:
            return stop.scheduled_time
    return None


def _normalize_transport_ai_time_literal(value: object) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    hour_text, separator, minute_text = normalized.partition(":")
    if separator != ":":
        return None
    if len(hour_text) != 2 or len(minute_text) != 2:
        return None
    if not hour_text.isdigit() or not minute_text.isdigit():
        return None
    hour = int(hour_text)
    minute = int(minute_text)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def _resolve_transport_ai_extra_route_kind(
    *,
    run: TransportAIRun,
    action,
) -> tuple[str | None, TransportAgentRunIssue | None]:
    after = action.after or {}
    route_kind_value, route_kind_present = _get_transport_ai_action_state_value(after, "route_kind")
    if not route_kind_present:
        return run.route_kind, None

    normalized_route_kind = str(route_kind_value or "").strip()
    if not normalized_route_kind:
        return run.route_kind, None
    if normalized_route_kind != run.route_kind:
        vehicle_ref = str(action.client_vehicle_key or action.action_key or "").strip() or "<unknown>"
        return None, TransportAgentRunIssue(
            code="transport_ai_extra_vehicle_route_kind_mismatch",
            message=(
                "The transport AI suggestion cannot create extra vehicle "
                f"'{vehicle_ref}' with route kind '{normalized_route_kind}' during a "
                f"'{run.route_kind}' run."
            ),
            blocking=True,
            source="suggestion_validation",
        )
    return normalized_route_kind, None


def _resolve_transport_ai_extra_departure_time(
    *,
    plan: TransportAgentPlan,
    vehicle_ref: str,
    route_kind: str,
    fallback_time: str,
    action,
) -> tuple[str | None, TransportAgentRunIssue | None]:
    itinerary = _find_transport_ai_route_itinerary(plan=plan, vehicle_ref=vehicle_ref)
    itinerary_reference_time = None
    if route_kind == "home_to_work":
        itinerary_reference_time = _resolve_transport_ai_extra_eta(itinerary)
    elif route_kind == "work_to_home":
        itinerary_reference_time = _resolve_transport_ai_extra_etd(itinerary)

    resolved_departure_time = itinerary_reference_time or _resolve_transport_ai_route_departure_time(
        plan=plan,
        vehicle_ref=vehicle_ref,
        fallback_time=fallback_time,
    )

    after = action.after or {}
    override_value, override_present = _get_transport_ai_action_state_value(after, "departure_time")
    if not override_present:
        return resolved_departure_time, None

    normalized_override = _normalize_transport_ai_time_literal(override_value)
    raw_override = str(override_value or "").strip()
    if normalized_override is None:
        if raw_override:
            return raw_override, None
        return resolved_departure_time, None
    if itinerary_reference_time and normalized_override != itinerary_reference_time:
        vehicle_ref_label = str(action.client_vehicle_key or action.action_key or vehicle_ref or "").strip() or vehicle_ref
        reference_label = "ETA" if route_kind == "home_to_work" else "ETD"
        return None, TransportAgentRunIssue(
            code="transport_ai_extra_vehicle_departure_time_mismatch",
            message=(
                "The transport AI suggestion uses explicit departure_time "
                f"'{normalized_override}' for extra vehicle '{vehicle_ref_label}', but the "
                f"itinerary-derived {reference_label} is '{itinerary_reference_time}'."
            ),
            blocking=True,
            source="suggestion_validation",
        )
    return normalized_override, None


def _resolve_transport_ai_route_departure_time(
    *,
    plan: TransportAgentPlan,
    vehicle_ref: str,
    fallback_time: str,
) -> str:
    matching_itinerary = _find_transport_ai_route_itinerary(plan=plan, vehicle_ref=vehicle_ref)
    if matching_itinerary is None:
        return fallback_time

    extra_eta = _resolve_transport_ai_extra_eta(matching_itinerary)
    if extra_eta:
        return extra_eta

    extra_etd = _resolve_transport_ai_extra_etd(matching_itinerary)
    if extra_etd:
        return extra_etd

    for stop in matching_itinerary.stops:
        if stop.scheduled_time:
            return stop.scheduled_time
    if matching_itinerary.projected_arrival_time:
        return matching_itinerary.projected_arrival_time
    return fallback_time


def _generate_transport_ai_temporary_plate(
    db: Session,
    *,
    run: TransportAIRun,
    sequence: int,
) -> str:
    candidate_sequence = max(sequence, 1)
    while True:
        candidate = f"Plate {candidate_sequence:03d}"
        compact_candidate = candidate.replace(" ", "").upper()
        uppercase_candidate = candidate.upper()
        existing_vehicle_id = db.execute(
            select(Vehicle.id)
            .where(
                or_(
                    Vehicle.placa == candidate,
                    Vehicle.placa == uppercase_candidate,
                    Vehicle.placa == compact_candidate,
                )
            )
            .limit(1)
        ).scalar_one_or_none()
        if existing_vehicle_id is None:
            return candidate
        candidate_sequence += 1


def _build_transport_ai_vehicle_create_payload(
    *,
    run: TransportAIRun,
    action,
    plate: str,
    vehicle_type: str,
    capacity: int,
    default_tolerance: int,
    route_kind: str | None,
    departure_time: str,
) -> tuple[TransportVehicleCreate | None, TransportAgentRunIssue | None]:
    after = action.after or {}
    create_payload: dict[str, object] = {
        "service_scope": action.service_scope,
        "service_date": run.service_date,
        "tipo": vehicle_type,
        "placa": plate,
        "color": after.get("color"),
        "lugares": capacity,
        "tolerance": default_tolerance,
    }

    if action.service_scope == "extra":
        create_payload["route_kind"] = str(route_kind or run.route_kind)
        create_payload["departure_time"] = departure_time
    else:
        recurring_flag_present = False
        for flag_name in _TRANSPORT_AI_CREATE_RECURRENCE_FLAG_NAMES:
            if flag_name not in after:
                continue
            create_payload[flag_name] = bool(after.get(flag_name))
            recurring_flag_present = True

        if not recurring_flag_present:
            weekday_index = run.service_date.weekday()
            if action.service_scope == "regular":
                weekday_flag = _TRANSPORT_AI_REGULAR_WEEKDAY_FLAG_BY_INDEX.get(weekday_index)
                if weekday_flag is None:
                    return None, TransportAgentRunIssue(
                        code="transport_ai_regular_vehicle_weekday_invalid",
                        message=(
                            "The transport AI suggestion cannot create a regular vehicle for "
                            f"service date '{run.service_date.isoformat()}' because it is not a weekday."
                        ),
                        blocking=True,
                        source="suggestion_validation",
                    )
                create_payload[weekday_flag] = True
            elif action.service_scope == "weekend":
                weekday_flag = _TRANSPORT_AI_WEEKEND_FLAG_BY_INDEX.get(weekday_index)
                if weekday_flag is None:
                    return None, TransportAgentRunIssue(
                        code="transport_ai_weekend_vehicle_weekday_invalid",
                        message=(
                            "The transport AI suggestion cannot create a weekend vehicle for "
                            f"service date '{run.service_date.isoformat()}' because it is not Saturday or Sunday."
                        ),
                        blocking=True,
                        source="suggestion_validation",
                    )
                create_payload[weekday_flag] = True

    try:
        return TransportVehicleCreate.model_validate(create_payload), None
    except ValidationError as exc:
        return None, TransportAgentRunIssue(
            code="transport_ai_vehicle_create_payload_invalid",
            message=_truncate_transport_ai_router_message(
                f"The transport AI vehicle create payload is invalid: {exc}"
            ),
            blocking=True,
            source="suggestion_validation",
        )


def _build_transport_ai_vehicle_create_audit_entry(
    *,
    run: TransportAIRun,
    action,
    vehicle_ref: str,
    create_payload: TransportVehicleCreate,
    vehicle: Vehicle,
    schedules: list[TransportVehicleSchedule],
) -> dict[str, object]:
    return {
        "action_key": action.action_key,
        "vehicle_ref": vehicle_ref,
        "client_vehicle_key": action.client_vehicle_key,
        "vehicle_id": vehicle.id,
        "plate": vehicle.placa,
        "vehicle_type": vehicle.tipo,
        "capacity": vehicle.lugares,
        "tolerance": vehicle.tolerance,
        "service_scope": action.service_scope,
        "service_date": run.service_date.isoformat(),
        "create_payload": create_payload.model_dump(mode="json"),
        "schedules": [
            {
                "schedule_id": schedule.id,
                "service_scope": schedule.service_scope,
                "route_kind": schedule.route_kind,
                "recurrence_kind": schedule.recurrence_kind,
                "service_date": schedule.service_date.isoformat() if schedule.service_date is not None else None,
                "weekday": schedule.weekday,
                "departure_time": schedule.departure_time,
            }
            for schedule in schedules
        ],
    }


def _build_transport_ai_vehicle_base_audit_state(
    *,
    vehicle: Vehicle,
    vehicle_ref: str,
) -> dict[str, object]:
    return {
        "vehicle_ref": vehicle_ref,
        "vehicle_id": vehicle.id,
        "plate": vehicle.placa,
        "vehicle_type": vehicle.tipo,
        "color": vehicle.color,
        "capacity": vehicle.lugares,
        "tolerance": vehicle.tolerance,
        "service_scope": vehicle.service_scope,
    }


def _build_transport_ai_vehicle_schedule_audit_state(
    schedule: TransportVehicleSchedule,
) -> dict[str, object]:
    return {
        "schedule_id": schedule.id,
        "service_scope": schedule.service_scope,
        "route_kind": schedule.route_kind,
        "recurrence_kind": schedule.recurrence_kind,
        "service_date": schedule.service_date.isoformat() if schedule.service_date is not None else None,
        "weekday": schedule.weekday,
        "departure_time": schedule.departure_time,
        "is_active": schedule.is_active,
    }


def _resolve_transport_ai_default_vehicle_capacity(
    transport_settings: dict[str, object],
    *,
    vehicle_type: str | None,
) -> int | None:
    normalized_vehicle_type = str(vehicle_type or "").strip().lower()
    if not normalized_vehicle_type:
        return None
    setting_name = _TRANSPORT_AI_DEFAULT_CAPACITY_SETTING_BY_TYPE.get(normalized_vehicle_type)
    if setting_name is None:
        return None
    value = transport_settings.get(setting_name)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_transport_ai_vehicle_update_payload(
    *,
    vehicle: Vehicle,
    action,
    transport_settings: dict[str, object],
) -> tuple[TransportVehicleUpdate | None, TransportAgentRunIssue | None]:
    after = action.after or {}

    next_service_scope, has_service_scope_override = _get_transport_ai_action_state_value(after, "service_scope")
    if has_service_scope_override and next_service_scope is not None and str(next_service_scope).strip() != vehicle.service_scope:
        return None, TransportAgentRunIssue(
            code="transport_ai_vehicle_update_scope_unsupported",
            message=(
                f"The transport AI suggestion cannot change vehicle '{vehicle.id}' scope from "
                f"'{vehicle.service_scope}' to '{next_service_scope}'."
            ),
            blocking=True,
            source="suggestion_validation",
            vehicle_id=vehicle.id,
        )

    next_plate, has_plate_override = _get_transport_ai_action_state_value(after, "plate", "placa")
    next_vehicle_type, has_vehicle_type_override = _get_transport_ai_action_state_value(after, "vehicle_type", "tipo")
    next_color, has_color_override = _get_transport_ai_action_state_value(after, "color")
    next_capacity, has_capacity_override = _get_transport_ai_action_state_value(after, "capacity", "lugares")
    next_tolerance, has_tolerance_override = _get_transport_ai_action_state_value(after, "tolerance")

    resolved_vehicle_type = next_vehicle_type if has_vehicle_type_override else vehicle.tipo
    if not has_capacity_override and has_vehicle_type_override and resolved_vehicle_type != vehicle.tipo:
        next_capacity = _resolve_transport_ai_default_vehicle_capacity(
            transport_settings,
            vehicle_type=str(resolved_vehicle_type) if resolved_vehicle_type is not None else None,
        )
        if next_capacity is None:
            return None, TransportAgentRunIssue(
                code="transport_ai_vehicle_update_capacity_missing",
                message=(
                    "The transport AI suggestion cannot change the vehicle type because the target default capacity "
                    "is unavailable."
                ),
                blocking=True,
                source="suggestion_validation",
                vehicle_id=vehicle.id,
            )
        has_capacity_override = True

    payload_data: dict[str, object] = {
        "placa": next_plate if has_plate_override else vehicle.placa,
        "tipo": resolved_vehicle_type,
        "color": next_color if has_color_override else vehicle.color,
        "lugares": next_capacity if has_capacity_override else vehicle.lugares,
        "tolerance": next_tolerance if has_tolerance_override else vehicle.tolerance,
    }

    try:
        return TransportVehicleUpdate.model_validate(payload_data), None
    except ValidationError as exc:
        return None, TransportAgentRunIssue(
            code="transport_ai_vehicle_update_payload_invalid",
            message=_truncate_transport_ai_router_message(
                f"The transport AI vehicle update payload is invalid: {exc}"
            ),
            blocking=True,
            source="suggestion_validation",
            vehicle_id=vehicle.id,
        )


def _build_transport_ai_vehicle_update_audit_entry(
    *,
    action,
    vehicle_ref: str,
    before_state: dict[str, object],
    update_payload: TransportVehicleUpdate,
    vehicle: Vehicle,
) -> dict[str, object]:
    after_state = _build_transport_ai_vehicle_base_audit_state(vehicle=vehicle, vehicle_ref=vehicle_ref)
    changed_fields = sorted(
        field_name
        for field_name in ("plate", "vehicle_type", "color", "capacity", "tolerance")
        if before_state.get(field_name) != after_state.get(field_name)
    )
    return {
        "action_key": action.action_key,
        "vehicle_ref": vehicle_ref,
        "client_vehicle_key": action.client_vehicle_key,
        "vehicle_id": vehicle.id,
        "before": before_state,
        "after": after_state,
        "update_payload": update_payload.model_dump(mode="json"),
        "changed_fields": changed_fields,
    }


def _build_transport_ai_vehicle_remove_from_day_audit_entry(
    *,
    run: TransportAIRun,
    action,
    vehicle_ref: str,
    before_state: dict[str, object],
    vehicle: Vehicle,
    affected_schedules_before: list[dict[str, object]],
    affected_schedules_after: list[dict[str, object]],
    applied_changes: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "action_key": action.action_key,
        "vehicle_ref": vehicle_ref,
        "client_vehicle_key": action.client_vehicle_key,
        "vehicle_id": vehicle.id,
        "service_date": run.service_date.isoformat(),
        "before": before_state,
        "after": _build_transport_ai_vehicle_base_audit_state(vehicle=vehicle, vehicle_ref=vehicle_ref),
        "affected_schedules_before": affected_schedules_before,
        "affected_schedules_after": affected_schedules_after,
        "applied_changes": applied_changes,
    }


def _record_transport_ai_vehicle_apply_audit(
    suggestion: TransportAISuggestion,
    *,
    audit_entries: list[dict[str, object]],
    audit_key: str,
    count_key: str,
) -> None:
    if not audit_entries:
        return

    existing_change_summary = _transport_ai_router_json_loads(suggestion.change_summary_json)
    if isinstance(existing_change_summary, dict):
        updated_change_summary = dict(existing_change_summary)
    else:
        updated_change_summary = {}

    updated_change_summary[audit_key] = audit_entries
    updated_change_summary[count_key] = len(audit_entries)
    suggestion.change_summary_json = _transport_ai_router_json_dumps(updated_change_summary)


def _record_transport_ai_vehicle_create_audit(
    suggestion: TransportAISuggestion,
    *,
    audit_entries: list[dict[str, object]],
) -> None:
    _record_transport_ai_vehicle_apply_audit(
        suggestion,
        audit_entries=audit_entries,
        audit_key="apply_vehicle_create_audit",
        count_key="apply_vehicle_create_count",
    )


def _record_transport_ai_vehicle_update_audit(
    suggestion: TransportAISuggestion,
    *,
    audit_entries: list[dict[str, object]],
) -> None:
    _record_transport_ai_vehicle_apply_audit(
        suggestion,
        audit_entries=audit_entries,
        audit_key="apply_vehicle_update_audit",
        count_key="apply_vehicle_update_count",
    )


def _record_transport_ai_vehicle_remove_from_day_audit(
    suggestion: TransportAISuggestion,
    *,
    audit_entries: list[dict[str, object]],
) -> None:
    _record_transport_ai_vehicle_apply_audit(
        suggestion,
        audit_entries=audit_entries,
        audit_key="apply_vehicle_remove_from_day_audit",
        count_key="apply_vehicle_remove_from_day_count",
    )


def apply_transport_ai_vehicle_remove_from_day_actions(
    db: Session,
    *,
    run: TransportAIRun,
    plan: TransportAgentPlan,
    created_at,
) -> tuple[list[TransportAgentRunIssue], list[dict[str, object]]]:
    issues: list[TransportAgentRunIssue] = []
    audit_entries: list[dict[str, object]] = []

    for action in plan.vehicle_actions:
        if action.action_type != "remove_from_day":
            continue

        vehicle_ref = _build_transport_ai_vehicle_ref_from_action(action)
        if vehicle_ref is None:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_vehicle_action_invalid",
                    message="A transport AI vehicle remove action is missing a resolvable vehicle reference.",
                    blocking=True,
                    source="suggestion_validation",
                    vehicle_id=action.vehicle_id,
                )
            )
            continue

        existing_vehicle_id = _resolve_transport_ai_existing_vehicle_id(action=action, vehicle_ref=vehicle_ref)
        if existing_vehicle_id is None:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_existing_vehicle_missing",
                    message=f"The suggestion references existing vehicle '{vehicle_ref}' without a vehicle id.",
                    blocking=True,
                    source="suggestion_validation",
                )
            )
            continue

        vehicle = db.get(Vehicle, existing_vehicle_id)
        if vehicle is None:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_existing_vehicle_missing",
                    message=f"The suggestion references missing vehicle '{vehicle_ref}'.",
                    blocking=True,
                    source="suggestion_validation",
                    vehicle_id=existing_vehicle_id,
                )
            )
            continue

        active_schedules = db.execute(
            select(TransportVehicleSchedule)
            .where(
                TransportVehicleSchedule.vehicle_id == vehicle.id,
                TransportVehicleSchedule.is_active.is_(True),
            )
            .order_by(TransportVehicleSchedule.id.asc())
        ).scalars().all()
        if not active_schedules:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_vehicle_remove_from_day_unavailable",
                    message=(
                        f"The suggestion cannot remove vehicle '{vehicle_ref}' from {run.service_date.isoformat()} "
                        "because it no longer has active schedules."
                    ),
                    blocking=True,
                    source="suggestion_validation",
                    vehicle_id=vehicle.id,
                )
            )
            continue

        schedule_ids = [schedule.id for schedule in active_schedules]
        existing_exception_by_schedule_id = {
            row.vehicle_schedule_id: row
            for row in db.execute(
                select(TransportVehicleScheduleException).where(
                    TransportVehicleScheduleException.vehicle_schedule_id.in_(schedule_ids),
                    TransportVehicleScheduleException.service_date == run.service_date,
                )
            ).scalars().all()
        } if schedule_ids else {}

        applicable_schedules = [
            schedule
            for schedule in active_schedules
            if schedule.service_scope == action.service_scope
            and schedule.id not in existing_exception_by_schedule_id
            and vehicle_schedule_applies_to_date(schedule, run.service_date)
        ]
        if not applicable_schedules:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_vehicle_remove_from_day_unavailable",
                    message=(
                        f"The suggestion cannot remove vehicle '{vehicle_ref}' from {run.service_date.isoformat()} "
                        "because it is no longer available on that date."
                    ),
                    blocking=True,
                    source="suggestion_validation",
                    vehicle_id=vehicle.id,
                )
            )
            continue

        before_state = _build_transport_ai_vehicle_base_audit_state(vehicle=vehicle, vehicle_ref=vehicle_ref)
        affected_schedules_before = [
            _build_transport_ai_vehicle_schedule_audit_state(schedule)
            for schedule in applicable_schedules
        ]
        applied_changes: list[dict[str, object]] = []

        for schedule in applicable_schedules:
            if schedule.recurrence_kind == "single_date":
                schedule.is_active = False
                schedule.updated_at = created_at
                applied_changes.append(
                    {
                        "schedule_id": schedule.id,
                        "route_kind": schedule.route_kind,
                        "recurrence_kind": schedule.recurrence_kind,
                        "change_kind": "deactivate_single_date",
                        "exception_id": None,
                        "exception_service_date": None,
                    }
                )
                continue

            schedule_exception = existing_exception_by_schedule_id.get(schedule.id)
            if schedule_exception is None:
                schedule_exception = TransportVehicleScheduleException(
                    vehicle_schedule_id=schedule.id,
                    service_date=run.service_date,
                    created_at=created_at,
                )
                db.add(schedule_exception)
                db.flush()

            applied_changes.append(
                {
                    "schedule_id": schedule.id,
                    "route_kind": schedule.route_kind,
                    "recurrence_kind": schedule.recurrence_kind,
                    "change_kind": "add_exception",
                    "exception_id": schedule_exception.id,
                    "exception_service_date": run.service_date.isoformat(),
                }
            )

        affected_schedules_after = [
            _build_transport_ai_vehicle_schedule_audit_state(schedule)
            for schedule in applicable_schedules
        ]
        audit_entries.append(
            _build_transport_ai_vehicle_remove_from_day_audit_entry(
                run=run,
                action=action,
                vehicle_ref=vehicle_ref,
                before_state=before_state,
                vehicle=vehicle,
                affected_schedules_before=affected_schedules_before,
                affected_schedules_after=affected_schedules_after,
                applied_changes=applied_changes,
            )
        )

    return issues, audit_entries


def apply_transport_ai_vehicle_create_actions(
    db: Session,
    *,
    run: TransportAIRun,
    plan: TransportAgentPlan,
    created_at,
) -> tuple[dict[str, int], list[TransportAgentRunIssue], list[int], list[dict[str, object]]]:
    issues: list[TransportAgentRunIssue] = []
    vehicle_id_by_ref: dict[str, int] = {}
    created_vehicle_ids: list[int] = []
    audit_entries: list[dict[str, object]] = []
    transport_settings = get_transport_settings_payload(db)
    default_tolerance = int(transport_settings["default_tolerance_minutes"])
    create_sequence = 0

    for action in plan.vehicle_actions:
        if action.action_type != "create":
            continue

        vehicle_ref = _build_transport_ai_vehicle_ref_from_action(action)
        if vehicle_ref is None:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_vehicle_action_invalid",
                    message="A transport AI vehicle create action is missing a resolvable vehicle reference.",
                    blocking=True,
                    source="suggestion_validation",
                    vehicle_id=action.vehicle_id,
                )
            )
            continue
        if vehicle_ref in vehicle_id_by_ref:
            continue

        after = action.after or {}
        vehicle_type = after.get("vehicle_type")
        capacity_value = after.get("capacity")
        if vehicle_type is None or capacity_value is None:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_vehicle_create_payload_incomplete",
                    message=f"The suggestion is missing vehicle base data required to create '{vehicle_ref}'.",
                    blocking=True,
                    source="suggestion_validation",
                )
            )
            continue

        try:
            capacity = int(capacity_value)
        except (TypeError, ValueError):
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_vehicle_capacity_invalid",
                    message=f"The suggestion uses an invalid capacity for '{vehicle_ref}'.",
                    blocking=True,
                    source="suggestion_validation",
                )
            )
            continue

        create_sequence += 1
        plate = str(after.get("plate") or "").strip() or _generate_transport_ai_temporary_plate(
            db,
            run=run,
            sequence=create_sequence,
        )
        resolved_route_kind = None
        if action.service_scope == "extra":
            resolved_route_kind, route_kind_issue = _resolve_transport_ai_extra_route_kind(
                run=run,
                action=action,
            )
            if resolved_route_kind is None:
                if route_kind_issue is not None:
                    issues.append(route_kind_issue)
                continue

            departure_time, departure_time_issue = _resolve_transport_ai_extra_departure_time(
                plan=plan,
                vehicle_ref=vehicle_ref,
                route_kind=resolved_route_kind,
                fallback_time=run.earliest_boarding_time,
                action=action,
            )
            if departure_time is None:
                if departure_time_issue is not None:
                    issues.append(departure_time_issue)
                continue
        else:
            departure_time = _resolve_transport_ai_route_departure_time(
                plan=plan,
                vehicle_ref=vehicle_ref,
                fallback_time=run.earliest_boarding_time,
            )
        create_payload, payload_issue = _build_transport_ai_vehicle_create_payload(
            run=run,
            action=action,
            plate=plate,
            vehicle_type=str(vehicle_type),
            capacity=capacity,
            default_tolerance=default_tolerance,
            route_kind=resolved_route_kind,
            departure_time=departure_time,
        )
        if create_payload is None:
            if payload_issue is not None:
                issues.append(payload_issue)
            continue

        vehicle, schedules = create_transport_vehicle_registration(
            db,
            payload=create_payload,
        )
        vehicle_id_by_ref[vehicle_ref] = vehicle.id
        created_vehicle_ids.append(vehicle.id)
        audit_entries.append(
            _build_transport_ai_vehicle_create_audit_entry(
                run=run,
                action=action,
                vehicle_ref=vehicle_ref,
                create_payload=create_payload,
                vehicle=vehicle,
                schedules=schedules,
            )
        )

    return vehicle_id_by_ref, issues, created_vehicle_ids, audit_entries


def apply_transport_ai_vehicle_update_actions(
    db: Session,
    *,
    plan: TransportAgentPlan,
) -> tuple[dict[str, int], list[TransportAgentRunIssue], list[dict[str, object]]]:
    issues: list[TransportAgentRunIssue] = []
    vehicle_id_by_ref: dict[str, int] = {}
    audit_entries: list[dict[str, object]] = []
    transport_settings = get_transport_settings_payload(db)

    for action in plan.vehicle_actions:
        if action.action_type != "update":
            continue

        vehicle_ref = _build_transport_ai_vehicle_ref_from_action(action)
        if vehicle_ref is None:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_vehicle_action_invalid",
                    message="A transport AI vehicle update action is missing a resolvable vehicle reference.",
                    blocking=True,
                    source="suggestion_validation",
                    vehicle_id=action.vehicle_id,
                )
            )
            continue

        existing_vehicle_id = _resolve_transport_ai_existing_vehicle_id(action=action, vehicle_ref=vehicle_ref)
        if existing_vehicle_id is None:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_existing_vehicle_missing",
                    message=f"The suggestion references existing vehicle '{vehicle_ref}' without a vehicle id.",
                    blocking=True,
                    source="suggestion_validation",
                )
            )
            continue

        vehicle = db.get(Vehicle, existing_vehicle_id)
        if vehicle is None:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_existing_vehicle_missing",
                    message=f"The suggestion references missing vehicle '{vehicle_ref}'.",
                    blocking=True,
                    source="suggestion_validation",
                    vehicle_id=existing_vehicle_id,
                )
            )
            continue

        before_state = _build_transport_ai_vehicle_base_audit_state(vehicle=vehicle, vehicle_ref=vehicle_ref)
        update_payload, payload_issue = _build_transport_ai_vehicle_update_payload(
            vehicle=vehicle,
            action=action,
            transport_settings=transport_settings,
        )
        if update_payload is None:
            if payload_issue is not None:
                issues.append(payload_issue)
            continue

        try:
            updated_vehicle = update_transport_vehicle_base(
                db,
                vehicle_id=vehicle.id,
                payload=update_payload,
            )
        except ValueError as exc:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_vehicle_update_conflict",
                    message=_truncate_transport_ai_router_message(str(exc)),
                    blocking=True,
                    source="suggestion_validation",
                    vehicle_id=vehicle.id,
                )
            )
            continue

        vehicle_id_by_ref[vehicle_ref] = updated_vehicle.id
        audit_entries.append(
            _build_transport_ai_vehicle_update_audit_entry(
                action=action,
                vehicle_ref=vehicle_ref,
                before_state=before_state,
                update_payload=update_payload,
                vehicle=updated_vehicle,
            )
        )

    return vehicle_id_by_ref, issues, audit_entries


def _sync_transport_ai_existing_extra_vehicle_departure_times(
    db: Session,
    *,
    run: TransportAIRun,
    plan: TransportAgentPlan,
    vehicle_id_by_ref: dict[str, int],
) -> list[TransportAgentRunIssue]:
    issues: list[TransportAgentRunIssue] = []
    processed_vehicle_refs: set[str] = set()

    for action in plan.vehicle_actions:
        if action.action_type not in {"keep", "update"} or action.service_scope != "extra":
            continue

        vehicle_ref = _build_transport_ai_vehicle_ref_from_action(action)
        if vehicle_ref is None or vehicle_ref in processed_vehicle_refs:
            continue
        processed_vehicle_refs.add(vehicle_ref)

        vehicle_id = vehicle_id_by_ref.get(vehicle_ref)
        if vehicle_id is None:
            continue

        vehicle = db.get(Vehicle, vehicle_id)
        if vehicle is None:
            continue

        route_kind, route_kind_issue = _resolve_transport_ai_extra_route_kind(
            run=run,
            action=action,
        )
        if route_kind is None:
            if route_kind_issue is not None:
                issues.append(route_kind_issue)
            continue

        schedule = find_transport_vehicle_schedule(
            db,
            vehicle=vehicle,
            service_date=run.service_date,
            route_kind=route_kind,
            service_scope="extra",
        )
        if schedule is None:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_extra_vehicle_schedule_missing",
                    message=(
                        f"The suggestion references extra vehicle '{vehicle_ref}' but its active "
                        f"schedule for {run.service_date.isoformat()} is no longer available."
                    ),
                    blocking=True,
                    source="suggestion_validation",
                    vehicle_id=vehicle.id,
                )
            )
            continue

        departure_time, departure_time_issue = _resolve_transport_ai_extra_departure_time(
            plan=plan,
            vehicle_ref=vehicle_ref,
            route_kind=route_kind,
            fallback_time=run.earliest_boarding_time,
            action=action,
        )
        if departure_time is None:
            if departure_time_issue is not None:
                issues.append(departure_time_issue)
            continue
        if schedule.departure_time == departure_time:
            continue

        try:
            update_transport_vehicle_schedule(
                db,
                schedule_id=schedule.id,
                payload=TransportVehicleScheduleUpdate(
                    service_scope=schedule.service_scope,
                    route_kind=schedule.route_kind,
                    recurrence_kind=schedule.recurrence_kind,
                    service_date=schedule.service_date,
                    weekday=schedule.weekday,
                    departure_time=departure_time,
                    is_active=schedule.is_active,
                ),
            )
        except ValueError as exc:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_extra_vehicle_schedule_update_conflict",
                    message=_truncate_transport_ai_router_message(str(exc)),
                    blocking=True,
                    source="suggestion_validation",
                    vehicle_id=vehicle.id,
                )
            )

    return issues


def _materialize_transport_ai_vehicle_actions(
    db: Session,
    *,
    run: TransportAIRun,
    plan: TransportAgentPlan,
    created_at,
) -> tuple[
    dict[str, int],
    list[TransportAgentRunIssue],
    list[int],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    issues: list[TransportAgentRunIssue] = []
    vehicle_id_by_ref: dict[str, int] = {}

    for action in plan.vehicle_actions:
        vehicle_ref = _build_transport_ai_vehicle_ref_from_action(action)
        if vehicle_ref is None:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_vehicle_action_invalid",
                    message="A transport AI vehicle action is missing a resolvable vehicle reference.",
                    blocking=True,
                    source="suggestion_validation",
                    vehicle_id=action.vehicle_id,
                )
            )
            continue

        if action.action_type == "keep":
            existing_vehicle_id = _resolve_transport_ai_existing_vehicle_id(action=action, vehicle_ref=vehicle_ref)
            if existing_vehicle_id is None:
                issues.append(
                    TransportAgentRunIssue(
                        code="transport_ai_existing_vehicle_missing",
                        message=f"The suggestion references existing vehicle '{vehicle_ref}' without a vehicle id.",
                        blocking=True,
                        source="suggestion_validation",
                    )
                )
                continue

            vehicle = db.get(Vehicle, existing_vehicle_id)
            if vehicle is None:
                issues.append(
                    TransportAgentRunIssue(
                        code="transport_ai_existing_vehicle_missing",
                        message=f"The suggestion references missing vehicle '{vehicle_ref}'.",
                        blocking=True,
                        source="suggestion_validation",
                        vehicle_id=existing_vehicle_id,
                    )
                )
                continue
            vehicle_id_by_ref[vehicle_ref] = vehicle.id
            continue

        if action.action_type in {"create", "update", "remove_from_day"}:
            continue

        issues.append(
            TransportAgentRunIssue(
                code="transport_ai_vehicle_action_unsupported",
                message=(
                    f"The suggestion contains unsupported vehicle action '{action.action_type}' for apply."
                ),
                blocking=True,
                source="suggestion_validation",
                vehicle_id=action.vehicle_id,
            )
        )

    remove_issues, remove_audit_entries = apply_transport_ai_vehicle_remove_from_day_actions(
        db,
        run=run,
        plan=plan,
        created_at=created_at,
    )
    issues.extend(remove_issues)

    updated_vehicle_id_by_ref, update_issues, update_audit_entries = apply_transport_ai_vehicle_update_actions(
        db,
        plan=plan,
    )
    vehicle_id_by_ref.update(updated_vehicle_id_by_ref)
    issues.extend(update_issues)

    created_vehicle_id_by_ref, create_issues, created_vehicle_ids, create_audit_entries = apply_transport_ai_vehicle_create_actions(
        db,
        run=run,
        plan=plan,
        created_at=created_at,
    )
    vehicle_id_by_ref.update(created_vehicle_id_by_ref)
    issues.extend(create_issues)

    issues.extend(
        _sync_transport_ai_existing_extra_vehicle_departure_times(
            db,
            run=run,
            plan=plan,
            vehicle_id_by_ref=vehicle_id_by_ref,
        )
    )
    return vehicle_id_by_ref, issues, created_vehicle_ids, create_audit_entries, update_audit_entries, remove_audit_entries


def _build_transport_ai_proposal_decisions(
    db: Session,
    *,
    plan: TransportAgentPlan,
    vehicle_id_by_ref: dict[str, int],
) -> tuple[list[TransportProposalDecision], list[TransportAgentRunIssue]]:
    if not plan.passenger_allocations:
        return [], [
            TransportAgentRunIssue(
                code="transport_ai_suggestion_empty",
                message="The transport AI suggestion does not contain passenger allocations to apply.",
                blocking=True,
                source="suggestion_validation",
            )
        ]

    decisions, conversion_issues = build_transport_proposal_from_agent_plan(
        db,
        plan=plan,
        vehicle_id_by_ref=vehicle_id_by_ref,
    )
    return decisions, [
        _build_transport_ai_run_issue_from_validation_issue(
            issue,
            source="suggestion_validation",
        )
        for issue in conversion_issues
    ]


def _build_transport_ai_applied_route_stop_inputs(
    *,
    plan: TransportAgentPlan,
    suggestion,
    vehicle_id_by_ref: dict[str, int],
) -> tuple[list[TransportAIAppliedRouteStopInput], list[TransportAgentRunIssue]]:
    stop_inputs: list[TransportAIAppliedRouteStopInput] = []
    issues: list[TransportAgentRunIssue] = []

    def normalize_applied_stop_type(*, route_kind: str, stop_type: str) -> str:
        normalized_route_kind = str(route_kind or "").strip().lower()
        normalized_stop_type = str(stop_type or "").strip().lower()
        if normalized_route_kind != "work_to_home":
            return normalized_stop_type
        if normalized_stop_type == "pickup":
            return "origin"
        if normalized_stop_type == "destination":
            return "dropoff"
        return normalized_stop_type

    for itinerary in plan.route_itineraries:
        vehicle_id = vehicle_id_by_ref.get(itinerary.vehicle_ref)
        if vehicle_id is None:
            issues.append(
                TransportAgentRunIssue(
                    code="transport_ai_itinerary_vehicle_unresolved",
                    message=(
                        f"The suggestion could not resolve itinerary vehicle reference '{itinerary.vehicle_ref}'."
                    ),
                    blocking=True,
                    source="suggestion_validation",
                    vehicle_id=itinerary.vehicle_id,
                )
            )
            continue

        for stop in itinerary.stops:
            stop_inputs.append(
                TransportAIAppliedRouteStopInput(
                    vehicle_id=vehicle_id,
                    route_kind=itinerary.route_kind,
                    stop_order=stop.stop_order + 1,
                    stop_type=normalize_applied_stop_type(
                        route_kind=itinerary.route_kind,
                        stop_type=stop.stop_type,
                    ),
                    request_id=stop.request_id,
                    user_id=stop.user_id,
                    passenger_name=stop.passenger_name,
                    project_name=stop.project_name,
                    address=stop.address,
                    zip_code=stop.zip_code,
                    country_code=stop.country_code,
                    longitude=stop.longitude,
                    latitude=stop.latitude,
                    scheduled_time=stop.scheduled_time,
                    duration_from_previous_seconds=stop.duration_from_previous_seconds,
                    distance_from_previous_meters=stop.distance_from_previous_meters,
                )
            )
    return stop_inputs, issues


def _build_transport_ai_start_response(
    *,
    ok: bool,
    message: str,
    run_key: str | None = None,
    suggestion_key: str | None = None,
    status_value: str | None = None,
    error_code: str | None = None,
    issues: list[TransportAIPreflightIssue] | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    route_provider: str | None = None,
    can_cancel_restore: bool = False,
    suggestion_ready: bool = False,
) -> TransportAgentRunStartResponse:
    normalized_issues = list(issues or [])
    primary_issue_code = next((issue.code for issue in normalized_issues if issue.blocking and issue.code), None)
    if primary_issue_code is None:
        primary_issue_code = next((issue.code for issue in normalized_issues if issue.code), None)
    effective_error_code = error_code or primary_issue_code
    response_message, response_message_key, response_message_params = (
        _build_transport_ai_router_failure_contract(
            message=message,
            error_code=effective_error_code,
            issues=normalized_issues,
            llm_provider=llm_provider,
            llm_model=llm_model,
            route_provider=route_provider,
        )
        if not ok
        else (_truncate_transport_ai_router_message(message), None, {})
    )
    return TransportAgentRunStartResponse(
        ok=ok,
        run_key=run_key,
        suggestion_key=suggestion_key,
        status=status_value,
        message=response_message,
        message_key=response_message_key,
        message_params=response_message_params,
        error_code=effective_error_code,
        failure_category=(
            resolve_transport_ai_failure_category(
                error_code=effective_error_code,
                issue_codes=[issue.code for issue in normalized_issues if issue.code],
            )
            if not ok
            else None
        ),
        review_state=resolve_transport_ai_review_state(
            run_status=status_value,
            has_suggestion=False,
        ),
        issues=normalized_issues,
        can_cancel_restore=can_cancel_restore,
        suggestion_ready=suggestion_ready,
    )


def _build_transport_ai_error_response(
    *,
    status_code: int,
    response: TransportAgentRunStartResponse,
) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=response.model_dump(mode="json"))


def _coerce_restore_issues_to_preflight_issues(issues: list[object]) -> list[TransportAIPreflightIssue]:
    coerced_issues: list[TransportAIPreflightIssue] = []
    for issue in issues:
        code = getattr(issue, "code", None)
        message = getattr(issue, "message", None)
        blocking = bool(getattr(issue, "blocking", True))
        if not code or not message:
            continue
        coerced_issues.append(
            TransportAIPreflightIssue(
                code=str(code),
                message=str(message),
                blocking=blocking,
                setting_name="transport_ai_baseline_restore",
            )
        )
    return coerced_issues


def _mark_transport_ai_run_failed(
    *,
    db: Session,
    run: TransportAIRun,
    timestamp,
    error_code: str,
    error_message: str,
) -> None:
    run.status = "failed"
    run.error_code = error_code
    run.error_message = _truncate_transport_ai_router_message(error_message, max_length=1000)
    run.updated_at = timestamp
    run.completed_at = timestamp
    db.add(run)
    db.flush()


def _restore_transport_ai_baseline_after_failure(
    *,
    db: Session,
    run: TransportAIRun,
    actor_user_id: int,
    timestamp,
    base_error_code: str,
    base_error_message: str,
    issues: list[TransportAIPreflightIssue] | None = None,
    planning_input: TransportAgentPlanningInput | None = None,
    observability: TransportAIObservabilitySummary | None = None,
) -> tuple[list[TransportAIPreflightIssue], bool, str]:
    effective_planning_input = planning_input or _load_transport_ai_run_planning_input_model(run)
    if effective_planning_input is not None:
        effective_planning_input = _ensure_transport_ai_planning_observability(
            planning_input=effective_planning_input,
            route_provider=run.route_provider,
            llm_provider=run.llm_provider,
            llm_model=run.llm_model,
            llm_reasoning_effort=run.llm_reasoning_effort,
        )
        if observability is None:
            observability = effective_planning_input.observability

    resolved_base_error_message = _build_transport_ai_router_failure_message(
        message=base_error_message,
        error_code=base_error_code,
        issues=list(issues or []),
        llm_provider=run.llm_provider,
        llm_model=run.llm_model,
        route_provider=run.route_provider,
        max_length=1000,
    )
    _mark_transport_ai_run_failed(
        db=db,
        run=run,
        timestamp=timestamp,
        error_code=base_error_code,
        error_message=resolved_base_error_message,
    )

    if not str(run.baseline_assignments_json or "").strip():
        if effective_planning_input is not None:
            save_transport_ai_planning_input(run, planning_input=effective_planning_input, saved_at=timestamp)
        record_transport_ai_lifecycle_transition(
            db,
            stage="run_failed",
            run=run,
            message=resolved_base_error_message,
            request_path="/api/transport/ai/route-calculations",
            extra_details={
                "error_code": base_error_code,
                "observability": _build_transport_ai_observability_event_summary(observability),
            },
        )
        return [], False, resolved_base_error_message

    restore_started_at = perf_counter()
    try:
        restore_result = restore_transport_ai_baseline(
            db,
            run=run,
            actor_user_id=actor_user_id,
            restored_at=timestamp,
        )
    except Exception as exc:
        restore_duration_ms = _measure_transport_ai_router_elapsed_ms(restore_started_at)
        if effective_planning_input is not None:
            effective_planning_input = _set_transport_ai_planning_phase_duration(
                effective_planning_input,
                phase_field="restore_ms",
                duration_ms=restore_duration_ms,
            )
            save_transport_ai_planning_input(run, planning_input=effective_planning_input, saved_at=timestamp)
        final_message = _compose_transport_ai_router_failure_message(
            headline=resolved_base_error_message,
            restore_note="Baseline restore raised an unexpected error.",
            max_length=1000,
        )
        run.error_message = _truncate_transport_ai_router_message(final_message, max_length=1000)
        db.add(run)
        db.flush()
        record_transport_ai_lifecycle_transition(
            db,
            stage="run_failed",
            run=run,
            message=final_message,
            request_path="/api/transport/ai/route-calculations",
            extra_details={
                "error_code": base_error_code,
                "restore_status": "unexpected_error",
                "restore_duration_ms": restore_duration_ms,
                "observability": _build_transport_ai_observability_event_summary(observability),
            },
        )
        return (
            [
                TransportAIPreflightIssue(
                    code="transport_ai_baseline_restore_failed",
                    message=_truncate_transport_ai_router_message(str(exc)),
                    blocking=True,
                    setting_name="transport_ai_baseline_restore",
                )
            ],
            True,
            final_message,
        )

    restore_duration_ms = _measure_transport_ai_router_elapsed_ms(restore_started_at)
    if effective_planning_input is not None:
        effective_planning_input = _set_transport_ai_planning_phase_duration(
            effective_planning_input,
            phase_field="restore_ms",
            duration_ms=restore_duration_ms,
        )
        save_transport_ai_planning_input(run, planning_input=effective_planning_input, saved_at=timestamp)

    if restore_result.ok:
        final_message = _compose_transport_ai_router_failure_message(
            headline=resolved_base_error_message,
            restore_note="Baseline restored successfully.",
            max_length=1000,
        )
        run.error_message = _truncate_transport_ai_router_message(final_message, max_length=1000)
        db.add(run)
        db.flush()
        emit_transport_reevaluation_event(
            event_type="transport_assignment_changed",
            reason="event",
            source="transport_admin",
            message="Transport AI restored the baseline after a failed route calculation.",
            service_date=run.service_date,
            route_kind=run.route_kind,
        )
        record_transport_ai_lifecycle_transition(
            db,
            stage="run_failed",
            run=run,
            message=final_message,
            request_path="/api/transport/ai/route-calculations",
            extra_details={
                "error_code": base_error_code,
                "restore_status": "restored",
                "restore_duration_ms": restore_duration_ms,
                "observability": _build_transport_ai_observability_event_summary(observability),
            },
        )
        return [], False, final_message

    final_message = _compose_transport_ai_router_failure_message(
        headline=resolved_base_error_message,
        restore_note="Baseline restore remains available but requires manual review.",
        max_length=1000,
    )
    run.error_message = _truncate_transport_ai_router_message(final_message, max_length=1000)
    db.add(run)
    db.flush()
    record_transport_ai_lifecycle_transition(
        db,
        stage="run_failed",
        run=run,
        message=final_message,
        request_path="/api/transport/ai/route-calculations",
        extra_details={
            "error_code": base_error_code,
            "restore_status": "manual_review_required",
            "restore_duration_ms": restore_duration_ms,
            "observability": _build_transport_ai_observability_event_summary(observability),
        },
    )
    return (
        _coerce_restore_issues_to_preflight_issues(restore_result.issues),
        True,
        final_message,
    )


@router.get("/preflight", response_model=TransportAIPreflightCheckResult)
def get_transport_ai_preflight(db: Session = Depends(get_db)) -> TransportAIPreflightCheckResult:
    return validate_transport_ai_runtime_configuration(db)


@router.get("/settings", response_model=TransportAISettingsResponse)
def get_transport_ai_settings(
    project_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
) -> TransportAISettingsResponse:
    try:
        return get_transport_ai_llm_settings_payload(db, project_id=project_id)
    except TransportAILlmSettingsProjectNotFoundError as exc:
        response_detail = _sanitize_transport_ai_router_message(str(exc))
        _raise_transport_ai_router_structured_http_error(
            status_code=status.HTTP_404_NOT_FOUND,
            message=response_detail,
            message_key=_resolve_transport_ai_settings_message_key(
                response_detail,
                "ai.settingsProjectMissing",
            ),
            error_code="transport_ai_settings_project_not_found",
            technical_detail=response_detail,
            issues=[
                _build_transport_ai_router_issue(
                    code="transport_ai_settings_project_not_found",
                    message=response_detail,
                    extra={"project_id": project_id},
                )
            ],
        )
    except TransportAILlmSettingsValidationError as exc:
        response_detail = _sanitize_transport_ai_router_message(str(exc))
        _raise_transport_ai_router_structured_http_error(
            status_code=status.HTTP_409_CONFLICT,
            message=response_detail,
            message_key=_resolve_transport_ai_settings_message_key(
                response_detail,
                "ai.settingsLoadFailed",
            ),
            error_code="transport_ai_settings_validation_failed",
            technical_detail=response_detail,
        )
    except TransportAILlmSettingsEncryptionError as exc:
        response_detail = _sanitize_transport_ai_router_message(
            "Transport AI settings encryption is unavailable."
        )
        technical_detail = _sanitize_transport_ai_router_message(str(exc))
        _raise_transport_ai_router_structured_http_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=response_detail,
            message_key=_resolve_transport_ai_settings_message_key(
                response_detail,
                "ai.settingsEncryptionUnavailable",
            ),
            error_code="transport_ai_settings_encryption_unavailable",
            technical_detail=technical_detail,
        )


@router.put("/settings", response_model=TransportAISettingsResponse)
def update_transport_ai_settings(
    payload: TransportAISettingsUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    transport_user: User = Depends(require_transport_session),
) -> TransportAISettingsResponse:
    request_path = str(request.url.path or "").strip() or "/api/transport/ai/settings"
    project = db.get(Project, payload.project_id)
    project_name = str(project.name).strip() if project is not None and str(project.name).strip() else None
    current_settings = get_transport_ai_llm_settings(db, project_id=payload.project_id)
    previous_provider = current_settings.provider if current_settings is not None else None
    timestamp = now_sgt()
    actor_admin_user = ensure_transport_ai_actor_admin_user(
        db,
        chave=transport_user.chave,
        nome_completo=transport_user.nome,
        ensured_at=timestamp,
    )

    try:
        upsert_transport_ai_llm_settings(
            db,
            project_id=payload.project_id,
            provider=payload.provider,
            api_key=payload.api_key,
            actor_admin_user_id=actor_admin_user.id,
        )
    except TransportAILlmSettingsProjectNotFoundError as exc:
        response_detail = _sanitize_transport_ai_router_message(
            str(exc),
            extra_literal_secrets=(payload.api_key,),
        )
        _record_transport_ai_settings_failure_event(
            db,
            transport_user=transport_user,
            project_id=payload.project_id,
            project_name=project_name,
            provider=payload.provider,
            api_key=payload.api_key,
            previous_provider=previous_provider,
            request_path=request_path,
            http_status=status.HTTP_404_NOT_FOUND,
            failure_detail=response_detail,
            response_detail=response_detail,
            timestamp=timestamp,
        )
        _raise_transport_ai_router_structured_http_error(
            status_code=status.HTTP_404_NOT_FOUND,
            message=response_detail,
            message_key=_resolve_transport_ai_settings_message_key(
                response_detail,
                "ai.settingsProjectMissing",
            ),
            error_code="transport_ai_settings_project_not_found",
            technical_detail=response_detail,
            issues=[
                _build_transport_ai_router_issue(
                    code="transport_ai_settings_project_not_found",
                    message=response_detail,
                    extra={"project_id": payload.project_id},
                )
            ],
        )
    except TransportAILlmSettingsValidationError as exc:
        response_detail = _sanitize_transport_ai_router_message(
            str(exc),
            extra_literal_secrets=(payload.api_key,),
        )
        _record_transport_ai_settings_failure_event(
            db,
            transport_user=transport_user,
            project_id=payload.project_id,
            project_name=project_name,
            provider=payload.provider,
            api_key=payload.api_key,
            previous_provider=previous_provider,
            request_path=request_path,
            http_status=status.HTTP_409_CONFLICT,
            failure_detail=response_detail,
            response_detail=response_detail,
            timestamp=timestamp,
        )
        _raise_transport_ai_router_structured_http_error(
            status_code=status.HTTP_409_CONFLICT,
            message=response_detail,
            message_key=_resolve_transport_ai_settings_message_key(
                response_detail,
                "ai.settingsSaveFailed",
            ),
            error_code="transport_ai_settings_validation_failed",
            technical_detail=response_detail,
        )
    except TransportAILlmSettingsEncryptionError as exc:
        response_detail = _sanitize_transport_ai_router_message(
            "Transport AI settings encryption is unavailable.",
            extra_literal_secrets=(payload.api_key,),
        )
        failure_detail = _sanitize_transport_ai_router_message(
            str(exc),
            extra_literal_secrets=(payload.api_key,),
        )
        _record_transport_ai_settings_failure_event(
            db,
            transport_user=transport_user,
            project_id=payload.project_id,
            project_name=project_name,
            provider=payload.provider,
            api_key=payload.api_key,
            previous_provider=previous_provider,
            request_path=request_path,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            failure_detail=failure_detail,
            response_detail=response_detail,
            timestamp=timestamp,
        )
        _raise_transport_ai_router_structured_http_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=response_detail,
            message_key=_resolve_transport_ai_settings_message_key(
                response_detail,
                "ai.settingsEncryptionUnavailable",
            ),
            error_code="transport_ai_settings_encryption_unavailable",
            technical_detail=failure_detail,
        )

    response_payload = get_transport_ai_llm_settings_payload(db, project_id=payload.project_id)
    record_transport_ai_settings_update(
        db,
        actor_admin_user=actor_admin_user,
        payload=response_payload,
        previous_provider=previous_provider,
        request_path=request_path,
        http_status=status.HTTP_200_OK,
    )
    db.commit()
    notify_admin_data_changed("event")
    return response_payload


@router.get("/runs", response_model=TransportAIRunDiagnosticsResponse)
def list_transport_ai_runs(
    service_date: date | None = Query(default=None),
    run_status: list[str] | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> TransportAIRunDiagnosticsResponse:
    normalized_statuses: list[str] = []
    if run_status:
        for item in run_status:
            normalized = str(item or "").strip().lower()
            if not normalized:
                continue
            if normalized not in _TRANSPORT_AI_RUN_ALLOWED_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported transport AI run status filter: {item!r}",
                )
            if normalized not in normalized_statuses:
                normalized_statuses.append(normalized)

    query = select(TransportAIRun)
    if service_date is not None:
        query = query.where(TransportAIRun.service_date == service_date)
    if normalized_statuses:
        query = query.where(TransportAIRun.status.in_(normalized_statuses))

    runs = db.execute(
        query.order_by(TransportAIRun.created_at.desc(), TransportAIRun.id.desc()).limit(limit)
    ).scalars().all()

    latest_suggestion_by_run_id: dict[int, TransportAISuggestion] = {}
    run_ids = [run.id for run in runs]
    if run_ids:
        suggestions = db.execute(
            select(TransportAISuggestion)
            .where(TransportAISuggestion.run_id.in_(run_ids))
            .order_by(
                TransportAISuggestion.run_id.asc(),
                TransportAISuggestion.updated_at.desc(),
                TransportAISuggestion.id.desc(),
            )
        ).scalars().all()
        for suggestion in suggestions:
            latest_suggestion_by_run_id.setdefault(suggestion.run_id, suggestion)

    entries = _build_transport_ai_runs_diagnostics_response(
        runs=runs,
        latest_suggestion_by_run_id=latest_suggestion_by_run_id,
        reference_time=now_sgt(),
    )
    return TransportAIRunDiagnosticsResponse(
        runs=entries,
        count=len(entries),
        service_date=service_date,
        statuses=normalized_statuses,
        limit=limit,
    )


@router.get(
    "/route-calculations/{run_key}",
    response_model=TransportAgentRunStatusResponse,
)
def get_transport_ai_route_calculation_status(
    run_key: str,
    db: Session = Depends(get_db),
) -> TransportAgentRunStatusResponse:
    run = db.execute(
        select(TransportAIRun)
        .where(TransportAIRun.run_key == run_key)
        .limit(1)
    ).scalar_one_or_none()
    if run is None:
        _raise_transport_ai_router_structured_http_error(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Transport AI run not found.",
            message_key="ai.routeCalculationFailed",
            error_code="transport_ai_run_not_found",
            technical_detail="Transport AI run not found.",
            issues=[
                _build_transport_ai_router_issue(
                    code="transport_ai_run_not_found",
                    message="Transport AI run not found.",
                    extra={"run_key": run_key},
                )
            ],
        )

    suggestion = get_latest_transport_ai_suggestion_for_run(db, run_id=run.id)
    return _build_transport_ai_run_status_response(run=run, suggestion=suggestion)


@router.get(
    "/suggestions/latest",
    response_model=TransportAgentRunStatusResponse,
)
def get_transport_ai_latest_suggestion(
    service_date: date = Query(...),
    route_kind: str = Query(...),
    db: Session = Depends(get_db),
) -> TransportAgentRunStatusResponse:
    suggestion = get_latest_active_transport_ai_suggestion(
        db,
        service_date=service_date,
        route_kind=route_kind,
    )
    if suggestion is None:
        _raise_transport_ai_router_structured_http_error(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Transport AI suggestion not found.",
            message_key="ai.noSavedSuggestion",
            error_code="transport_ai_suggestion_not_found",
            technical_detail="Transport AI suggestion not found.",
            issues=[
                _build_transport_ai_router_issue(
                    code="transport_ai_suggestion_not_found",
                    message="Transport AI suggestion not found.",
                    extra={"service_date": service_date.isoformat(), "route_kind": route_kind},
                )
            ],
        )

    run = db.get(TransportAIRun, suggestion.run_id)
    if run is None:
        _raise_transport_ai_router_structured_http_error(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Transport AI run not found.",
            message_key="ai.routeCalculationFailed",
            error_code="transport_ai_run_not_found",
            technical_detail="Transport AI run not found.",
            issues=[
                _build_transport_ai_router_issue(
                    code="transport_ai_run_not_found",
                    message="Transport AI run not found.",
                    extra={"service_date": service_date.isoformat(), "route_kind": route_kind},
                )
            ],
        )
    return _build_transport_ai_run_status_response(run=run, suggestion=suggestion)


@router.post(
    "/suggestions/{suggestion_key}/save",
    response_model=TransportAgentRunStatusResponse,
)
def save_transport_ai_suggestion(
    suggestion_key: str,
    db: Session = Depends(get_db),
) -> TransportAgentRunStatusResponse | JSONResponse:
    run, suggestion = _load_transport_ai_suggestion_or_404(db, suggestion_key=suggestion_key)
    if suggestion.status == "saved" and run.status == "saved":
        return _build_transport_ai_run_status_response(run=run, suggestion=suggestion)
    if suggestion.status not in {"shown", "saved"} or run.status not in {"proposed", "saved"}:
        return _build_transport_ai_status_error_response(
            status_code=status.HTTP_409_CONFLICT,
            response=_build_transport_ai_status_response_with_overrides(
                run=run,
                suggestion=suggestion,
                ok=False,
                message="The transport AI suggestion can no longer be saved.",
                message_key="ai.changesSaveFailed",
                error_code="transport_ai_suggestion_save_conflict",
            ),
        )

    plan, plan_issues = _load_transport_ai_suggestion_plan(suggestion)
    if plan is None or any(issue.blocking for issue in plan_issues):
        return _build_transport_ai_status_error_response(
            status_code=status.HTTP_409_CONFLICT,
            response=_build_transport_ai_status_response_with_overrides(
                run=run,
                suggestion=suggestion,
                ok=False,
                message="The transport AI suggestion cannot be saved because its payload is invalid.",
                message_key="ai.changesSaveFailed",
                error_code="transport_ai_suggestion_payload_invalid",
                extra_issues=plan_issues,
            ),
        )

    timestamp = now_sgt()
    set_transport_ai_suggestion_status(db, suggestion=suggestion, status="saved", changed_at=timestamp)
    run.status = "saved"
    run.updated_at = timestamp
    db.add(run)
    record_transport_ai_lifecycle_transition(
        db,
        stage="suggestion_saved",
        run=run,
        suggestion=suggestion,
        request_path=f"/api/transport/ai/suggestions/{suggestion_key}/save",
    )
    db.commit()

    notify_admin_data_changed("event")
    emit_transport_reevaluation_event(
        event_type="transport_operational_review_changed",
        reason="event",
        source="transport_admin",
        message="A transport AI suggestion was saved for later review.",
        service_date=run.service_date,
        route_kind=run.route_kind,
        proposal_key=suggestion.proposal_key,
    )
    return _build_transport_ai_run_status_response(run=run, suggestion=suggestion)


@router.post(
    "/suggestions/{suggestion_key}/cancel",
    response_model=TransportAgentRunStatusResponse,
)
def cancel_transport_ai_suggestion(
    suggestion_key: str,
    db: Session = Depends(get_db),
    transport_user: User = Depends(require_transport_session),
) -> TransportAgentRunStatusResponse | JSONResponse:
    run, suggestion = _load_transport_ai_suggestion_or_404(db, suggestion_key=suggestion_key)
    if suggestion.status == "discarded" and run.status == "cancelled":
        return _build_transport_ai_run_status_response(run=run, suggestion=suggestion)
    if suggestion.status == "applied" or run.status == "applied":
        return _build_transport_ai_status_error_response(
            status_code=status.HTTP_409_CONFLICT,
            response=_build_transport_ai_status_response_with_overrides(
                run=run,
                suggestion=suggestion,
                ok=False,
                message="The transport AI suggestion was already applied and cannot be cancelled.",
                message_key="ai.changesCancelFailed",
                error_code="transport_ai_suggestion_cancel_already_applied",
            ),
        )
    if suggestion.status not in {"shown", "saved", "discarded"} or run.status not in {"proposed", "saved", "cancelled"}:
        return _build_transport_ai_status_error_response(
            status_code=status.HTTP_409_CONFLICT,
            response=_build_transport_ai_status_response_with_overrides(
                run=run,
                suggestion=suggestion,
                ok=False,
                message="The transport AI suggestion can no longer be cancelled.",
                message_key="ai.changesCancelFailed",
                error_code="transport_ai_suggestion_cancel_conflict",
            ),
        )

    timestamp = now_sgt()
    actor_admin_user = ensure_transport_ai_actor_admin_user(
        db,
        chave=transport_user.chave,
        nome_completo=transport_user.nome,
        ensured_at=timestamp,
    )
    restore_result = restore_transport_ai_baseline(
        db,
        run=run,
        actor_user_id=actor_admin_user.id,
        restored_at=timestamp,
    )
    if not restore_result.ok:
        restore_issues = [
            _build_transport_ai_run_issue_from_validation_issue(
                TransportProposalValidationIssue(
                    code=issue.code,
                    message=issue.message,
                    blocking=issue.blocking,
                    request_id=getattr(issue, "request_id", None),
                    vehicle_id=getattr(issue, "vehicle_id", None),
                ),
                source="baseline_restore",
            )
            for issue in restore_result.issues
        ]
        return _build_transport_ai_status_error_response(
            status_code=status.HTTP_409_CONFLICT,
            response=_build_transport_ai_status_response_with_overrides(
                run=run,
                suggestion=suggestion,
                ok=False,
                message=restore_result.error_message or "Transport AI baseline restore requires manual review.",
                message_key="ai.changesCancelFailed",
                error_code="transport_ai_baseline_restore_failed",
                extra_issues=restore_issues,
            ),
        )

    set_transport_ai_suggestion_status(db, suggestion=suggestion, status="discarded", changed_at=timestamp)
    run.status = "cancelled"
    run.updated_at = timestamp
    run.completed_at = timestamp
    db.add(run)
    record_transport_ai_lifecycle_transition(
        db,
        stage="suggestion_discarded",
        run=run,
        suggestion=suggestion,
        request_path=f"/api/transport/ai/suggestions/{suggestion_key}/cancel",
    )
    db.commit()

    notify_admin_data_changed("event")
    emit_transport_reevaluation_event(
        event_type="transport_assignment_changed",
        reason="event",
        source="transport_admin",
        message="A transport AI suggestion was cancelled and the baseline was restored.",
        service_date=run.service_date,
        route_kind=run.route_kind,
        proposal_key=suggestion.proposal_key,
    )
    emit_transport_reevaluation_event(
        event_type="transport_operational_review_changed",
        reason="event",
        source="transport_admin",
        message="A transport AI suggestion review was cancelled.",
        service_date=run.service_date,
        route_kind=run.route_kind,
        proposal_key=suggestion.proposal_key,
    )
    return _build_transport_ai_run_status_response(run=run, suggestion=suggestion)


@router.post(
    "/suggestions/{suggestion_key}/apply",
    response_model=TransportAgentRunStatusResponse,
)
def apply_transport_ai_suggestion(
    suggestion_key: str,
    db: Session = Depends(get_db),
    transport_user: User = Depends(require_transport_session),
) -> TransportAgentRunStatusResponse | JSONResponse:
    run, suggestion = _load_transport_ai_suggestion_or_404(db, suggestion_key=suggestion_key)
    if suggestion.status == "applied" and run.status == "applied":
        return _build_transport_ai_run_status_response(run=run, suggestion=suggestion)
    if suggestion.status in {"discarded"} or run.status in {"cancelled", "failed"}:
        return _build_transport_ai_status_error_response(
            status_code=status.HTTP_409_CONFLICT,
            response=_build_transport_ai_status_response_with_overrides(
                run=run,
                suggestion=suggestion,
                ok=False,
                message="The transport AI suggestion can no longer be applied.",
                message_key="ai.changesApplyFailed",
                error_code="transport_ai_suggestion_apply_conflict",
            ),
        )

    plan, plan_issues = _load_transport_ai_suggestion_plan(suggestion)
    if plan is None or any(issue.blocking for issue in plan_issues):
        return _build_transport_ai_status_error_response(
            status_code=status.HTTP_409_CONFLICT,
            response=_build_transport_ai_status_response_with_overrides(
                run=run,
                suggestion=suggestion,
                ok=False,
                message="The transport AI suggestion cannot be applied because its payload is invalid.",
                message_key="ai.changesApplyFailed",
                error_code="transport_ai_suggestion_payload_invalid",
                extra_issues=plan_issues,
            ),
        )

    timestamp = now_sgt()
    actor_admin_user = ensure_transport_ai_actor_admin_user(
        db,
        chave=transport_user.chave,
        nome_completo=transport_user.nome,
        ensured_at=timestamp,
    )
    actor_identity = _build_transport_ai_actor_identity(
        transport_user=transport_user,
        actor_admin_user_id=actor_admin_user.id,
    )

    savepoint = db.begin_nested()
    try:
        previous_proposal = _load_transport_ai_suggestion_proposal(suggestion)
        (
            vehicle_id_by_ref,
            vehicle_issues,
            created_vehicle_ids,
            vehicle_create_audit_entries,
            vehicle_update_audit_entries,
            vehicle_remove_audit_entries,
        ) = _materialize_transport_ai_vehicle_actions(
            db,
            run=run,
            plan=plan,
            created_at=timestamp,
        )
        decisions, decision_issues = _build_transport_ai_proposal_decisions(
            db,
            plan=plan,
            vehicle_id_by_ref=vehicle_id_by_ref,
        )
        stop_inputs, stop_issues = _build_transport_ai_applied_route_stop_inputs(
            plan=plan,
            suggestion=suggestion,
            vehicle_id_by_ref=vehicle_id_by_ref,
        )
        pre_apply_issues = [*vehicle_issues, *decision_issues, *stop_issues]
        if any(issue.blocking for issue in pre_apply_issues):
            savepoint.rollback()
            return _build_transport_ai_status_error_response(
                status_code=status.HTTP_409_CONFLICT,
                response=_build_transport_ai_status_response_with_overrides(
                    run=run,
                    suggestion=suggestion,
                    ok=False,
                    message="The transport AI suggestion could not be materialized for apply.",
                    message_key="ai.changesApplyFailed",
                    error_code="transport_ai_suggestion_materialization_failed",
                    extra_issues=pre_apply_issues,
                ),
            )

        proposal = build_transport_operational_proposal_contract(
            db,
            service_date=run.service_date,
            route_kind=run.route_kind,
            origin="agent",
            actor=actor_identity,
            replaces_proposal_key=(previous_proposal.proposal_key if previous_proposal is not None else None),
            decisions=decisions,
            captured_at=timestamp,
            created_at=timestamp,
        )
        validated_proposal = validate_transport_operational_proposal(
            db,
            proposal=proposal,
            actor=actor_identity,
            validated_at=timestamp,
        )
        if proposal_has_blocking_issues(validated_proposal):
            savepoint.rollback()
            _persist_transport_ai_suggestion_proposal(
                suggestion=suggestion,
                proposal=validated_proposal,
                changed_at=timestamp,
            )
            db.add(suggestion)
            db.commit()
            proposal_issues = [
                _build_transport_ai_run_issue_from_validation_issue(issue, source="proposal_validation")
                for issue in validated_proposal.validation_issues
            ]
            return _build_transport_ai_status_error_response(
                status_code=status.HTTP_409_CONFLICT,
                response=_build_transport_ai_status_response_with_overrides(
                    run=run,
                    suggestion=suggestion,
                    ok=False,
                    message="The transport AI suggestion could not be validated against the current operational snapshot.",
                    message_key="ai.changesApplyFailed",
                    error_code="transport_ai_suggestion_validation_failed",
                    extra_issues=proposal_issues,
                ),
            )

        approved_proposal = approve_transport_operational_proposal(
            db,
            proposal=validated_proposal,
            actor=actor_identity,
            approved_at=timestamp,
        )
        if proposal_has_blocking_issues(approved_proposal) or approved_proposal.proposal_status != "approved":
            savepoint.rollback()
            _persist_transport_ai_suggestion_proposal(
                suggestion=suggestion,
                proposal=approved_proposal,
                changed_at=timestamp,
            )
            db.add(suggestion)
            db.commit()
            proposal_issues = [
                _build_transport_ai_run_issue_from_validation_issue(issue, source="proposal_validation")
                for issue in approved_proposal.validation_issues
            ]
            return _build_transport_ai_status_error_response(
                status_code=status.HTTP_409_CONFLICT,
                response=_build_transport_ai_status_response_with_overrides(
                    run=run,
                    suggestion=suggestion,
                    ok=False,
                    message="The transport AI suggestion could not be approved against the current operational snapshot.",
                    message_key="ai.changesApplyFailed",
                    error_code="transport_ai_suggestion_approval_failed",
                    extra_issues=proposal_issues,
                ),
            )

        applied_proposal, _applied_assignments = apply_transport_operational_proposal(
            db,
            proposal=approved_proposal,
            actor=actor_identity,
            applied_at=timestamp,
        )
        if proposal_has_blocking_issues(applied_proposal) or applied_proposal.proposal_status != "applied":
            savepoint.rollback()
            _persist_transport_ai_suggestion_proposal(
                suggestion=suggestion,
                proposal=applied_proposal,
                changed_at=timestamp,
            )
            db.add(suggestion)
            db.commit()
            proposal_issues = [
                _build_transport_ai_run_issue_from_validation_issue(issue, source="proposal_apply")
                for issue in applied_proposal.validation_issues
            ]
            return _build_transport_ai_status_error_response(
                status_code=status.HTTP_409_CONFLICT,
                response=_build_transport_ai_status_response_with_overrides(
                    run=run,
                    suggestion=suggestion,
                    ok=False,
                    message="The transport AI suggestion could not be applied because the operational state changed.",
                    message_key="ai.changesApplyFailed",
                    error_code="transport_ai_suggestion_apply_state_changed",
                    extra_issues=proposal_issues,
                ),
            )

        persist_transport_ai_applied_route_stops(
            db,
            suggestion=suggestion,
            stops=stop_inputs,
            created_at=timestamp,
        )
        _record_transport_ai_vehicle_create_audit(
            suggestion,
            audit_entries=vehicle_create_audit_entries,
        )
        _record_transport_ai_vehicle_update_audit(
            suggestion,
            audit_entries=vehicle_update_audit_entries,
        )
        _record_transport_ai_vehicle_remove_from_day_audit(
            suggestion,
            audit_entries=vehicle_remove_audit_entries,
        )
        _persist_transport_ai_suggestion_proposal(
            suggestion=suggestion,
            proposal=applied_proposal,
            changed_at=timestamp,
        )
        set_transport_ai_suggestion_status(db, suggestion=suggestion, status="applied", changed_at=timestamp)
        run.status = "applied"
        run.updated_at = timestamp
        run.completed_at = timestamp
        db.add(run)
        savepoint.commit()
    except Exception:
        savepoint.rollback()
        raise

    record_transport_ai_lifecycle_transition(
        db,
        stage="suggestion_applied",
        run=run,
        suggestion=suggestion,
        request_path=f"/api/transport/ai/suggestions/{suggestion_key}/apply",
        extra_details={
            "created_vehicle_count": len(created_vehicle_ids),
        },
    )
    db.commit()

    notify_admin_data_changed("event")
    emit_transport_reevaluation_event(
        event_type="transport_vehicle_supply_changed",
        reason="event",
        source="transport_admin",
        message="A transport AI suggestion changed the available transport supply.",
        service_date=run.service_date,
        route_kind=run.route_kind,
        vehicle_id=created_vehicle_ids[0] if len(created_vehicle_ids) == 1 else None,
        proposal_key=suggestion.proposal_key,
    )
    emit_transport_reevaluation_event(
        event_type="transport_assignment_changed",
        reason="event",
        source="transport_admin",
        message="A transport AI suggestion was applied to transport assignments.",
        service_date=run.service_date,
        route_kind=run.route_kind,
        proposal_key=suggestion.proposal_key,
    )
    emit_transport_reevaluation_event(
        event_type="transport_operational_review_changed",
        reason="event",
        source="transport_admin",
        message="A transport AI suggestion review was completed by applying the proposal.",
        service_date=run.service_date,
        route_kind=run.route_kind,
        proposal_key=suggestion.proposal_key,
    )
    return _build_transport_ai_run_status_response(run=run, suggestion=suggestion)


@router.post(
    "/route-calculations",
    response_model=TransportAgentRunStartResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_transport_ai_route_calculation(
    payload: TransportAgentRouteRequest,
    db: Session = Depends(get_db),
    transport_user: User = Depends(require_transport_session),
) -> TransportAgentRunStartResponse | JSONResponse:
    runtime_preflight = validate_transport_ai_runtime_configuration(db)
    if not runtime_preflight.ok:
        return _build_transport_ai_error_response(
            status_code=status.HTTP_409_CONFLICT,
            response=_build_transport_ai_start_response(
                ok=False,
                status_value="failed",
                message="Transport AI runtime preflight failed.",
                issues=runtime_preflight.issues,
            ),
        )

    active_run_count = count_transport_ai_active_runs(db)
    if active_run_count >= settings.transport_ai_max_concurrent_runs:
        concurrency_issue = build_transport_ai_concurrency_limit_issue(
            active_run_count=active_run_count,
            settings_obj=settings,
        )
        return _build_transport_ai_error_response(
            status_code=status.HTTP_409_CONFLICT,
            response=_build_transport_ai_start_response(
                ok=False,
                status_value="failed",
                message="Transport AI runtime admission is blocked by the concurrency limit.",
                issues=[concurrency_issue],
            ),
        )

    timestamp = now_sgt()
    actor_admin_user = ensure_transport_ai_actor_admin_user(
        db,
        chave=transport_user.chave,
        nome_completo=transport_user.nome,
        ensured_at=timestamp,
    )
    transport_settings = get_transport_settings_payload(db)
    dashboard_scope_project_names = _resolve_transport_ai_dashboard_scope_project_names(
        db,
        dashboard_scope=payload.dashboard_scope,
    )
    dashboard_scope_audit_details = _build_transport_ai_dashboard_scope_audit_details(
        dashboard_scope=payload.dashboard_scope,
        project_names=dashboard_scope_project_names,
    )
    run = TransportAIRun(
        run_key=f"transport-ai-run:{uuid4().hex}",
        service_date=payload.service_date,
        route_kind=payload.route_kind,
        status="requested",
        actor_user_id=actor_admin_user.id,
        earliest_boarding_time=payload.earliest_boarding_time,
        arrival_at_work_time=payload.arrival_at_work_time,
        llm_provider=None,
        llm_model=None,
        llm_reasoning_effort=None,
        openai_model=settings.openai_model,
        route_provider=str(settings.transport_ai_route_provider or "mapbox").strip() or "mapbox",
        price_currency_code=transport_settings.get("price_currency_code"),
        price_rate_unit=str(transport_settings["price_rate_unit"]),
        baseline_snapshot_json=None,
        baseline_assignments_json=None,
        baseline_vehicle_state_json=None,
        planning_input_json=_transport_ai_router_json_dumps(
            {
                "service_date": payload.service_date.isoformat(),
                "route_kind": payload.route_kind,
                "earliest_boarding_time": payload.earliest_boarding_time,
                "arrival_at_work_time": payload.arrival_at_work_time,
                "request_route_kinds": (
                    payload.request_route_kinds.model_dump(mode="json", exclude_none=True)
                    if payload.request_route_kinds is not None
                    else None
                ),
                "dashboard_scope": (
                    payload.dashboard_scope.model_dump(mode="json")
                    if payload.dashboard_scope is not None
                    else None
                ),
                "dashboard_scope_project_names": dashboard_scope_project_names,
            }
        ),
        planning_input_hash="0" * 64,
        preflight_issues_json=None,
        error_code=None,
        error_message=None,
        created_at=timestamp,
        updated_at=timestamp,
        completed_at=None,
    )
    db.add(run)
    db.flush()
    record_transport_ai_lifecycle_transition(
        db,
        stage="run_created",
        run=run,
        request_path="/api/transport/ai/route-calculations",
        extra_details={
            "actor_user_id": actor_admin_user.id,
            **dashboard_scope_audit_details,
            "llm_provider": run.llm_provider,
            "llm_model": run.llm_model,
            "llm_reasoning_effort": run.llm_reasoning_effort,
            "openai_model": run.openai_model,
            "route_provider": run.route_provider,
        },
    )

    baseline_started_at = perf_counter()
    baseline_capture = capture_transport_ai_baseline(
        db,
        service_date=payload.service_date,
        route_kind=payload.route_kind,
        actor_user_id=actor_admin_user.id,
        dashboard_scope=payload.dashboard_scope,
        captured_at=timestamp,
    )
    save_transport_ai_baseline(
        db,
        run=run,
        baseline_capture=baseline_capture,
        saved_at=timestamp,
    )
    baseline_duration_ms = _measure_transport_ai_router_elapsed_ms(baseline_started_at)
    record_transport_ai_lifecycle_transition(
        db,
        stage="baseline_saved",
        run=run,
        request_path="/api/transport/ai/route-calculations",
        extra_details={
            "baseline_hash": baseline_capture.baseline_hash,
            "baseline_duration_ms": baseline_duration_ms,
            **dashboard_scope_audit_details,
        },
    )

    reset_result = reset_transport_ai_requests_to_pending(
        db,
        run=run,
        actor_user_id=actor_admin_user.id,
        reset_at=timestamp,
    )
    if not reset_result.ok:
        reset_issues = _coerce_restore_issues_to_preflight_issues(reset_result.issues)
        if reset_result.restore_result is not None:
            reset_issues.extend(_coerce_restore_issues_to_preflight_issues(reset_result.restore_result.issues))
        error_message = reset_result.error_message or "Transport AI could not reset eligible requests to pending."
        _mark_transport_ai_run_failed(
            db=db,
            run=run,
            timestamp=timestamp,
            error_code="transport_ai_reset_failed",
            error_message=error_message,
        )
        record_transport_ai_lifecycle_transition(
            db,
            stage="run_failed",
            run=run,
            message=error_message,
            request_path="/api/transport/ai/route-calculations",
            extra_details={
                "error_code": "transport_ai_reset_failed",
                "observability": {
                    "failure_layer": "local",
                    "failed_phase": "reset",
                    "phase_durations_ms": {
                        "baseline_ms": baseline_duration_ms,
                        "reset_ms": reset_result.duration_ms,
                    },
                },
            },
        )
        db.commit()
        notify_admin_data_changed("event")
        return _build_transport_ai_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response=_build_transport_ai_start_response(
                ok=False,
                run_key=run.run_key,
                status_value=run.status,
                error_code="transport_ai_reset_failed",
                message=error_message,
                issues=reset_issues,
                can_cancel_restore=not (reset_result.restore_result and reset_result.restore_result.ok),
            ),
        )

    try:
        planning_input = build_transport_agent_planning_input(
            db,
            service_date=payload.service_date,
            route_kind=payload.route_kind,
            earliest_boarding_time=payload.earliest_boarding_time,
            arrival_at_work_time=payload.arrival_at_work_time,
            request_route_kinds=payload.request_route_kinds,
            dashboard_scope=payload.dashboard_scope,
            settings_obj=settings,
        )
        planning_issues = list(planning_input.preflight_issues)
        if normalize_transport_ai_agent_mode(settings.transport_ai_agent_mode) == "agent":
            project_runtime_preflight = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=settings,
                planning_input=planning_input,
            )
            planning_issues.extend(project_runtime_preflight.issues)

            if project_runtime_preflight.ok:
                try:
                    resolved_llm_runtime_settings, llm_runtime_projects = resolve_transport_ai_shared_llm_runtime_context(
                        db,
                        planning_input=planning_input,
                        settings_obj=settings,
                    )
                except (
                    TransportAILlmSettingsEncryptionError,
                    TransportAILlmSettingsProjectNotFoundError,
                    TransportAILlmSettingsValidationError,
                ) as exc:
                    planning_issues.append(
                        TransportAIPreflightIssue(
                            code="transport_ai_llm_runtime_unavailable",
                            message=_sanitize_transport_ai_router_message(str(exc)),
                            blocking=True,
                            setting_name="transport_ai_llm_settings",
                        )
                    )
                else:
                    planning_input = planning_input.model_copy(
                        update={"llm_runtime_projects": llm_runtime_projects}
                    )
                    run.llm_provider = resolved_llm_runtime_settings.provider
                    run.llm_model = resolved_llm_runtime_settings.model_name
                    run.llm_reasoning_effort = resolved_llm_runtime_settings.reasoning_effort
                    run.openai_model = resolved_llm_runtime_settings.model_name

        planning_input = _ensure_transport_ai_planning_observability(
            planning_input=planning_input,
            route_provider=run.route_provider,
            llm_provider=run.llm_provider,
            llm_model=run.llm_model,
            llm_reasoning_effort=run.llm_reasoning_effort,
        )
        planning_input = _set_transport_ai_planning_phase_duration(
            planning_input,
            phase_field="baseline_ms",
            duration_ms=baseline_duration_ms,
        )
        if reset_result.duration_ms is not None:
            planning_input = _set_transport_ai_planning_phase_duration(
                planning_input,
                phase_field="reset_ms",
                duration_ms=reset_result.duration_ms,
            )
        planning_input = planning_input.model_copy(update={"preflight_issues": planning_issues})
        save_transport_ai_planning_input(
            run,
            planning_input=planning_input,
            saved_at=timestamp,
        )

        if planning_input.total_requests <= 0 or any(issue.blocking for issue in planning_input.preflight_issues):
            scope_phrase = _build_transport_ai_dashboard_scope_phrase(
                dashboard_scope=payload.dashboard_scope,
                project_names=planning_input.dashboard_scope_project_names,
            )
            failure_message = (
                f"Transport AI route calculation has no eligible pending requests{scope_phrase} after reset."
                if planning_input.total_requests <= 0
                else f"Transport AI planning validation failed{scope_phrase} after resetting eligible requests."
            )
            planning_input = _mark_transport_ai_planning_observability_failure(
                planning_input,
                failure_layer="local",
                failed_phase="validation",
            )
            save_transport_ai_planning_input(
                run,
                planning_input=planning_input,
                saved_at=timestamp,
            )
            restore_issues, can_cancel_restore, final_message = _restore_transport_ai_baseline_after_failure(
                db=db,
                run=run,
                actor_user_id=actor_admin_user.id,
                timestamp=now_sgt(),
                base_error_code="transport_ai_planning_input_invalid",
                base_error_message=failure_message,
                issues=planning_input.preflight_issues,
                planning_input=planning_input,
                observability=planning_input.observability,
            )
            db.commit()
            notify_admin_data_changed("event")
            return _build_transport_ai_error_response(
                status_code=status.HTTP_409_CONFLICT,
                response=_build_transport_ai_start_response(
                    ok=False,
                    run_key=run.run_key,
                    status_value=run.status,
                    error_code="transport_ai_planning_input_invalid",
                    message=final_message,
                    issues=[*planning_input.preflight_issues, *restore_issues],
                    can_cancel_restore=can_cancel_restore,
                ),
            )

        agent_result = run_transport_ai_agent(
            db=db,
            run=run,
            settings_obj=settings,
        )
        if agent_result.plan is None:
            restore_issues, can_cancel_restore, final_message = _restore_transport_ai_baseline_after_failure(
                db=db,
                run=run,
                actor_user_id=actor_admin_user.id,
                timestamp=now_sgt(),
                base_error_code=agent_result.error_code or "transport_ai_route_calculation_failed",
                base_error_message=agent_result.error_message or "Transport AI route calculation failed.",
                issues=agent_result.issues,
                planning_input=_load_transport_ai_run_planning_input_model(run),
                observability=agent_result.observability,
            )
            db.commit()
            notify_admin_data_changed("event")
            return _build_transport_ai_error_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                response=_build_transport_ai_start_response(
                    ok=False,
                    run_key=run.run_key,
                    status_value=run.status,
                    error_code=agent_result.error_code or "transport_ai_route_calculation_failed",
                    message=final_message,
                    issues=[*agent_result.issues, *restore_issues],
                    llm_provider=run.llm_provider,
                    llm_model=run.llm_model,
                    route_provider=run.route_provider,
                    can_cancel_restore=can_cancel_restore,
                ),
            )

        suggestion = create_transport_ai_suggestion_from_plan(
            db,
            run=run,
            plan=agent_result.plan,
            prompt_version=agent_result.prompt_version,
            raw_model_response_json=agent_result.raw_model_response_json,
            suggestion_key=f"transport-ai-suggestion:{uuid4().hex}",
            proposal_key=f"transport-ai-proposal:{run.run_key}",
            status="shown",
            created_at=now_sgt(),
        )
        record_transport_ai_lifecycle_transition(
            db,
            stage="suggestion_generated",
            run=run,
            suggestion=suggestion,
            request_path="/api/transport/ai/route-calculations",
            extra_details={
                "prompt_version": agent_result.prompt_version,
                "llm_provider": run.llm_provider,
                "llm_model": run.llm_model,
                "llm_reasoning_effort": run.llm_reasoning_effort,
                "openai_model": run.openai_model,
                "observability": _build_transport_ai_observability_event_summary(
                    agent_result.observability or _extract_transport_ai_run_observability(run)
                ),
            },
        )
        emit_transport_reevaluation_event(
            event_type="transport_operational_review_changed",
            reason="event",
            source="transport_admin",
            message="Transport AI suggestion is ready for review.",
            service_date=run.service_date,
            route_kind=run.route_kind,
            proposal_key=suggestion.proposal_key,
        )
        db.commit()
        notify_admin_data_changed("event")
        return _build_transport_ai_start_response(
            ok=True,
            run_key=run.run_key,
            suggestion_key=suggestion.suggestion_key,
            status_value=run.status,
            message="Transport AI route calculation completed successfully.",
            can_cancel_restore=True,
            suggestion_ready=True,
        )
    except Exception as exc:
        restore_issues, can_cancel_restore, final_message = _restore_transport_ai_baseline_after_failure(
            db=db,
            run=run,
            actor_user_id=actor_admin_user.id,
            timestamp=now_sgt(),
            base_error_code="transport_ai_route_calculation_unhandled_error",
            base_error_message=str(exc),
            planning_input=_load_transport_ai_run_planning_input_model(run),
            observability=_extract_transport_ai_run_observability(run),
        )
        db.commit()
        notify_admin_data_changed("event")
        return _build_transport_ai_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response=_build_transport_ai_start_response(
                ok=False,
                run_key=run.run_key,
                status_value=run.status,
                error_code="transport_ai_route_calculation_unhandled_error",
                message=final_message,
                issues=restore_issues,
                can_cancel_restore=can_cancel_restore,
            ),
        )
