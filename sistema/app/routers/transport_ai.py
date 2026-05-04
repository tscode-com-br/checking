import json
from datetime import date
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import normalize_transport_ai_agent_mode, settings
from ..database import get_db
from ..models import (
    TransportAIRun,
    TransportAISuggestion,
    TransportVehicleSchedule,
    TransportVehicleScheduleException,
    User,
    Vehicle,
)
from ..schemas import (
    TransportAIRunDiagnosticsEntry,
    TransportAIRunDiagnosticsResponse,
    TransportAIPreflightCheckResult,
    TransportAIPreflightIssue,
    TransportAISettingsResponse,
    TransportAISettingsUpdateRequest,
    TransportAgentPlan,
    TransportAgentRouteStop,
    TransportAgentRouteRequest,
    TransportAgentRunIssue,
    TransportAgentRunStartResponse,
    TransportAgentRunStatusResponse,
    TransportAgentRunSuggestion,
    TransportIdentity,
    TransportOperationalProposal,
    TransportProposalDecision,
    TransportProposalValidationIssue,
    TransportVehicleCreate,
    TransportVehicleUpdate,
)
from ..services.admin_auth import require_transport_session
from ..services.admin_updates import notify_admin_data_changed
from ..services.location_settings import get_transport_settings_payload
from ..services.time_utils import now_sgt
from ..services.transport_ai_llm_settings import (
    TransportAILlmSettingsEncryptionError,
    TransportAILlmSettingsValidationError,
    get_transport_ai_llm_settings,
    get_transport_ai_llm_settings_payload,
    resolve_transport_ai_llm_runtime_settings,
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
    get_latest_active_transport_ai_suggestion,
    get_latest_transport_ai_suggestion_for_run,
    get_transport_ai_suggestion_by_key,
    reset_transport_ai_requests_to_pending,
    restore_transport_ai_baseline,
    save_transport_ai_baseline,
    save_transport_ai_planning_input,
    set_transport_ai_suggestion_status,
)
from ..services.transport_ai_runtime import validate_transport_ai_runtime_configuration
from ..services.transport_proposals import (
    apply_transport_operational_proposal,
    approve_transport_operational_proposal,
    build_transport_operational_proposal_contract,
    proposal_has_blocking_issues,
    validate_transport_operational_proposal,
)
from ..services.transport_reevaluation_events import emit_transport_reevaluation_event
from ..services.transport_vehicle_schedule import vehicle_schedule_applies_to_date


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


def _transport_ai_router_json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _transport_ai_router_json_loads(value: str | None) -> object | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    try:
        return json.loads(normalized)
    except (TypeError, ValueError):
        return None


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


def _record_transport_ai_settings_failure_event(
    db: Session,
    *,
    transport_user: User,
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
        if not code or not message:
            continue
        issues.append(
            TransportAgentRunIssue(
                code=str(code),
                message=_truncate_transport_ai_router_message(str(message)),
                blocking=bool(item.get("blocking", True)),
                source="run_preflight",
                setting_name=item.get("setting_name"),
                request_id=item.get("request_id"),
                vehicle_id=item.get("vehicle_id"),
            )
        )
    return issues


def _build_transport_ai_poll_suggestion_response(
    suggestion,
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
) -> str:
    if run.status == "failed":
        if run.error_message:
            return _truncate_transport_ai_router_message(run.error_message)
        return "Transport AI route calculation failed."
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


def _resolve_transport_ai_run_llm_snapshot_fields(run: TransportAIRun) -> dict[str, str]:
    llm_model = str(run.llm_model or run.openai_model or "").strip()
    llm_provider = str(run.llm_provider or "").strip().lower()
    llm_reasoning_effort = str(run.llm_reasoning_effort or "").strip().lower()

    if not llm_provider:
        llm_provider = "openai" if llm_model else "unknown"
    if not llm_reasoning_effort:
        llm_reasoning_effort = "high" if llm_model else "unknown"

    return {
        "llm_provider": llm_provider,
        "llm_model": llm_model or "unknown",
        "llm_reasoning_effort": llm_reasoning_effort,
    }


def _build_transport_ai_runs_diagnostics_entries(
    *,
    runs: list[TransportAIRun],
    latest_suggestion_by_run_id: dict[int, TransportAISuggestion],
    reference_time,
) -> list[TransportAIRunDiagnosticsEntry]:
    entries: list[TransportAIRunDiagnosticsEntry] = []
    for run in runs:
        suggestion = latest_suggestion_by_run_id.get(run.id)
        llm_fields = _resolve_transport_ai_run_llm_snapshot_fields(run)
        preflight_issue_codes, preflight_blocking_count = _extract_transport_ai_issue_codes(run.preflight_issues_json)
        validation_issue_codes, validation_blocking_count = _extract_transport_ai_issue_codes(
            suggestion.validation_issues_json if suggestion is not None else None
        )
        usage_summary = _extract_transport_ai_usage_summary(
            suggestion.raw_model_response_json if suggestion is not None else None
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
                openai_model=run.openai_model,
                route_provider=run.route_provider,
                suggestion_key=suggestion.suggestion_key if suggestion is not None else None,
                suggestion_status=suggestion.status if suggestion is not None else None,
                prompt_version=suggestion.prompt_version if suggestion is not None else None,
                created_at=run.created_at,
                updated_at=run.updated_at,
                completed_at=run.completed_at,
                duration_seconds=_build_transport_ai_run_duration_seconds(run=run, reference_time=reference_time),
                error_code=run.error_code,
                error_message=(
                    _truncate_transport_ai_router_message(
                        sanitize_transport_ai_string(run.error_message),
                    )
                    if run.error_message
                    else None
                ),
                preflight_issue_codes=preflight_issue_codes,
                validation_issue_codes=validation_issue_codes,
                blocking_issue_count=preflight_blocking_count + validation_blocking_count,
                **usage_summary,
            )
        )
    return entries


def _build_transport_ai_run_status_response(
    *,
    run: TransportAIRun,
    suggestion,
) -> TransportAgentRunStatusResponse:
    llm_fields = _resolve_transport_ai_run_llm_snapshot_fields(run)
    suggestion_response, suggestion_issues = _build_transport_ai_poll_suggestion_response(suggestion)
    issues = [*_build_transport_ai_run_preflight_issues(run), *suggestion_issues]
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
    return TransportAgentRunStatusResponse(
        ok=run.status != "failed",
        run_key=run.run_key,
        service_date=run.service_date,
        route_kind=run.route_kind,
        status=run.status,
        llm_provider=llm_fields["llm_provider"],
        llm_model=llm_fields["llm_model"],
        llm_reasoning_effort=llm_fields["llm_reasoning_effort"],
        message=_build_transport_ai_run_status_message(
            run=run,
            suggestion=suggestion,
            suggestion_response=suggestion_response,
        ),
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


def _build_transport_ai_status_response_with_overrides(
    *,
    run: TransportAIRun,
    suggestion,
    ok: bool | None = None,
    message: str | None = None,
    extra_issues: list[TransportAgentRunIssue] | None = None,
) -> TransportAgentRunStatusResponse:
    base_response = _build_transport_ai_run_status_response(run=run, suggestion=suggestion)
    combined_issues = [*base_response.issues, *(extra_issues or [])]
    return base_response.model_copy(
        update={
            "ok": base_response.ok if ok is None else ok,
            "message": message or base_response.message,
            "issues": combined_issues,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transport AI suggestion not found.")

    run = db.get(TransportAIRun, suggestion.run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transport AI run not found.")
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


def _resolve_transport_ai_route_departure_time(
    *,
    plan: TransportAgentPlan,
    vehicle_ref: str,
    fallback_time: str,
) -> str:
    matching_itinerary = next((item for item in plan.route_itineraries if item.vehicle_ref == vehicle_ref), None)
    if matching_itinerary is None:
        return fallback_time

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
    route_code = "H" if run.route_kind == "home_to_work" else "W"
    date_fragment = run.service_date.strftime("%m%d")
    run_fragment = f"{run.id % 100:02d}"
    candidate_sequence = max(sequence, 1)
    while True:
        candidate = f"AI{route_code}{date_fragment}{run_fragment}{candidate_sequence:02d}"
        existing_vehicle_id = db.execute(
            select(Vehicle.id)
            .where(Vehicle.placa == candidate)
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
        create_payload["route_kind"] = str(after.get("route_kind") or run.route_kind)
        create_payload["departure_time"] = str(after.get("departure_time") or departure_time)
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
                    stop_order=stop.stop_order + 1,
                    stop_type=stop.stop_type,
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
    issues: list[TransportAIPreflightIssue] | None = None,
    can_cancel_restore: bool = False,
    suggestion_ready: bool = False,
) -> TransportAgentRunStartResponse:
    return TransportAgentRunStartResponse(
        ok=ok,
        run_key=run_key,
        suggestion_key=suggestion_key,
        status=status_value,
        message=_truncate_transport_ai_router_message(message),
        issues=list(issues or []),
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
) -> tuple[list[TransportAIPreflightIssue], bool, str]:
    _mark_transport_ai_run_failed(
        db=db,
        run=run,
        timestamp=timestamp,
        error_code=base_error_code,
        error_message=base_error_message,
    )

    if not str(run.baseline_assignments_json or "").strip():
        return [], False, base_error_message

    try:
        restore_result = restore_transport_ai_baseline(
            db,
            run=run,
            actor_user_id=actor_user_id,
            restored_at=timestamp,
        )
    except Exception as exc:
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
            f"{base_error_message} Baseline restore raised an unexpected error.",
        )

    if restore_result.ok:
        emit_transport_reevaluation_event(
            event_type="transport_assignment_changed",
            reason="event",
            source="transport_admin",
            message="Transport AI restored the baseline after a failed route calculation.",
            service_date=run.service_date,
            route_kind=run.route_kind,
        )
        return [], False, f"{base_error_message} Baseline restored."

    return (
        _coerce_restore_issues_to_preflight_issues(restore_result.issues),
        True,
        f"{base_error_message} Baseline restore remains available but requires manual review.",
    )


@router.get("/preflight", response_model=TransportAIPreflightCheckResult)
def get_transport_ai_preflight(db: Session = Depends(get_db)) -> TransportAIPreflightCheckResult:
    return validate_transport_ai_runtime_configuration(db)


@router.get("/settings", response_model=TransportAISettingsResponse)
def get_transport_ai_settings(db: Session = Depends(get_db)) -> TransportAISettingsResponse:
    try:
        return get_transport_ai_llm_settings_payload(db)
    except TransportAILlmSettingsValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_sanitize_transport_ai_router_message(str(exc)),
        ) from exc


@router.put("/settings", response_model=TransportAISettingsResponse)
def update_transport_ai_settings(
    payload: TransportAISettingsUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    transport_user: User = Depends(require_transport_session),
) -> TransportAISettingsResponse:
    request_path = str(request.url.path or "").strip() or "/api/transport/ai/settings"
    current_settings = get_transport_ai_llm_settings(db)
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
            provider=payload.provider,
            api_key=payload.api_key,
            actor_admin_user_id=actor_admin_user.id,
        )
    except TransportAILlmSettingsValidationError as exc:
        response_detail = _sanitize_transport_ai_router_message(
            str(exc),
            extra_literal_secrets=(payload.api_key,),
        )
        _record_transport_ai_settings_failure_event(
            db,
            transport_user=transport_user,
            provider=payload.provider,
            api_key=payload.api_key,
            previous_provider=previous_provider,
            request_path=request_path,
            http_status=status.HTTP_409_CONFLICT,
            failure_detail=response_detail,
            response_detail=response_detail,
            timestamp=timestamp,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=response_detail,
        ) from exc
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
            provider=payload.provider,
            api_key=payload.api_key,
            previous_provider=previous_provider,
            request_path=request_path,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            failure_detail=failure_detail,
            response_detail=response_detail,
            timestamp=timestamp,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response_detail,
        ) from exc

    response_payload = get_transport_ai_llm_settings_payload(db)
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

    entries = _build_transport_ai_runs_diagnostics_entries(
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transport AI run not found.")

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transport AI suggestion not found.")

    run = db.get(TransportAIRun, suggestion.run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transport AI run not found.")
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

    timestamp = now_sgt()
    actor_admin_user = ensure_transport_ai_actor_admin_user(
        db,
        chave=transport_user.chave,
        nome_completo=transport_user.nome,
        ensured_at=timestamp,
    )
    llm_runtime_settings = None
    if normalize_transport_ai_agent_mode(settings.transport_ai_agent_mode) == "agent":
        llm_runtime_settings = resolve_transport_ai_llm_runtime_settings(db)
    transport_settings = get_transport_settings_payload(db)
    run = TransportAIRun(
        run_key=f"transport-ai-run:{uuid4().hex}",
        service_date=payload.service_date,
        route_kind=payload.route_kind,
        status="requested",
        actor_user_id=actor_admin_user.id,
        earliest_boarding_time=payload.earliest_boarding_time,
        arrival_at_work_time=payload.arrival_at_work_time,
        llm_provider=llm_runtime_settings.provider if llm_runtime_settings is not None else None,
        llm_model=llm_runtime_settings.model_name if llm_runtime_settings is not None else None,
        llm_reasoning_effort=llm_runtime_settings.reasoning_effort if llm_runtime_settings is not None else None,
        openai_model=(
            llm_runtime_settings.model_name
            if llm_runtime_settings is not None
            else settings.openai_model
        ),
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
            "llm_provider": run.llm_provider,
            "llm_model": run.llm_model,
            "llm_reasoning_effort": run.llm_reasoning_effort,
            "openai_model": run.openai_model,
            "route_provider": run.route_provider,
        },
    )

    baseline_capture = capture_transport_ai_baseline(
        db,
        service_date=payload.service_date,
        route_kind=payload.route_kind,
        actor_user_id=actor_admin_user.id,
        captured_at=timestamp,
    )
    save_transport_ai_baseline(
        db,
        run=run,
        baseline_capture=baseline_capture,
        saved_at=timestamp,
    )
    record_transport_ai_lifecycle_transition(
        db,
        stage="baseline_saved",
        run=run,
        request_path="/api/transport/ai/route-calculations",
        extra_details={
            "baseline_hash": baseline_capture.baseline_hash,
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
        db.commit()
        notify_admin_data_changed("event")
        return _build_transport_ai_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response=_build_transport_ai_start_response(
                ok=False,
                run_key=run.run_key,
                status_value=run.status,
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
            settings_obj=settings,
        )
        save_transport_ai_planning_input(
            run,
            planning_input=planning_input,
            saved_at=timestamp,
        )

        planning_issues = list(planning_input.preflight_issues)
        if planning_input.total_requests <= 0 or any(issue.blocking for issue in planning_issues):
            failure_message = (
                "Transport AI route calculation has no eligible pending requests after reset."
                if planning_input.total_requests <= 0
                else "Transport AI planning validation failed after resetting eligible requests."
            )
            restore_issues, can_cancel_restore, final_message = _restore_transport_ai_baseline_after_failure(
                db=db,
                run=run,
                actor_user_id=actor_admin_user.id,
                timestamp=now_sgt(),
                base_error_code="transport_ai_planning_input_invalid",
                base_error_message=failure_message,
            )
            db.commit()
            notify_admin_data_changed("event")
            return _build_transport_ai_error_response(
                status_code=status.HTTP_409_CONFLICT,
                response=_build_transport_ai_start_response(
                    ok=False,
                    run_key=run.run_key,
                    status_value=run.status,
                    message=final_message,
                    issues=[*planning_issues, *restore_issues],
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
            )
            db.commit()
            notify_admin_data_changed("event")
            return _build_transport_ai_error_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                response=_build_transport_ai_start_response(
                    ok=False,
                    run_key=run.run_key,
                    status_value=run.status,
                    message=final_message,
                    issues=restore_issues,
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
        )
        db.commit()
        notify_admin_data_changed("event")
        return _build_transport_ai_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response=_build_transport_ai_start_response(
                ok=False,
                run_key=run.run_key,
                status_value=run.status,
                message=final_message,
                issues=restore_issues,
                can_cancel_restore=can_cancel_restore,
            ),
        )