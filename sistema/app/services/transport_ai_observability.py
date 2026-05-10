from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from ..models import AdminUser, TransportAIRun, TransportAISuggestion
from ..schemas import TransportAISettingsResponse
from .event_logger import log_event
from .transport_ai_llm_settings import mask_transport_ai_api_key
from .transport_ai_sanitization import sanitize_transport_ai_raw_value, sanitize_transport_ai_string
from .transport_reevaluation_events import emit_transport_reevaluation_event


logger = logging.getLogger(__name__)

TRANSPORT_AI_ROUTE_CALCULATION_CHANGED_EVENT = "transport_ai_route_calculation_changed"

_TRANSPORT_AI_LIFECYCLE_ACTION_BY_STAGE = {
    "run_created": "run_create",
    "baseline_saved": "baseline_save",
    "passengers_reset": "requests_reset",
    "run_failed": "run_fail",
    "suggestion_generated": "suggestion_gen",
    "suggestion_saved": "suggestion_save",
    "suggestion_discarded": "suggestion_drop",
    "suggestion_applied": "suggestion_apply",
}

_TRANSPORT_AI_LIFECYCLE_MESSAGE_BY_STAGE = {
    "run_created": "Transport AI run created.",
    "baseline_saved": "Transport AI baseline saved.",
    "passengers_reset": "Transport AI reset eligible requests to pending.",
    "run_failed": "Transport AI run failed.",
    "suggestion_generated": "Transport AI suggestion generated and ready for review.",
    "suggestion_saved": "Transport AI suggestion saved for later review.",
    "suggestion_discarded": "Transport AI suggestion discarded and baseline restored.",
    "suggestion_applied": "Transport AI suggestion applied to the operational state.",
}


def _build_transport_ai_settings_message(
    *,
    payload: TransportAISettingsResponse,
) -> str:
    message = (
        "Transport AI settings updated. "
        f"project_id={payload.project_id or '-'}; "
        f"project={payload.project_name or '-'}; "
        f"provider={payload.provider}; "
        f"model={payload.resolved_model}; "
        f"reasoning={payload.reasoning_effort}; "
        f"api_key={payload.api_key_hint or '-'}"
    )
    return sanitize_transport_ai_string(message)[:255]


def _build_transport_ai_settings_details(
    *,
    actor_admin_user: AdminUser,
    payload: TransportAISettingsResponse,
    previous_provider: str | None,
    request_path: str | None,
) -> str:
    sanitized_payload = sanitize_transport_ai_raw_value(
        {
            "actor_admin_user_id": actor_admin_user.id,
            "actor_admin_key": actor_admin_user.chave,
            "project_id": payload.project_id,
            "project_name": payload.project_name,
            "provider": payload.provider,
            "resolved_model": payload.resolved_model,
            "reasoning_effort": payload.reasoning_effort,
            "has_api_key": payload.has_api_key,
            "api_key_hint": payload.api_key_hint,
            "previous_provider": previous_provider,
            "provider_changed": previous_provider != payload.provider,
            "request_path": request_path,
        }
    )
    return json.dumps(sanitized_payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _build_transport_ai_settings_failure_message(
    *,
    project_id: int | None,
    project_name: str | None,
    provider: str | None,
    api_key: str | None,
    response_detail: str,
) -> str:
    message = (
        "Transport AI settings update failed. "
        f"project_id={project_id or '-'}; "
        f"project={project_name or '-'}; "
        f"provider={str(provider or '').strip().lower() or '-'}; "
        f"api_key_hint={mask_transport_ai_api_key(api_key=api_key) or '-'}; "
        f"detail={response_detail}"
    )
    return sanitize_transport_ai_string(
        message,
        extra_literal_secrets=(api_key,),
    )[:255]


def _build_transport_ai_settings_failure_details(
    *,
    actor_admin_user: AdminUser,
    project_id: int | None,
    project_name: str | None,
    provider: str | None,
    api_key: str | None,
    previous_provider: str | None,
    failure_detail: str,
    response_detail: str,
    request_path: str | None,
) -> str:
    sanitized_payload = sanitize_transport_ai_raw_value(
        {
            "actor_admin_user_id": actor_admin_user.id,
            "actor_admin_key": actor_admin_user.chave,
            "project_id": project_id,
            "project_name": project_name,
            "requested_provider": str(provider or "").strip().lower() or None,
            "submitted_has_api_key": bool(str(api_key or "").strip()),
            "api_key_hint": mask_transport_ai_api_key(api_key=api_key),
            "previous_provider": previous_provider,
            "failure_detail": failure_detail,
            "response_detail": response_detail,
            "request_path": request_path,
        },
        extra_literal_secrets=(api_key,),
    )
    return json.dumps(sanitized_payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _build_transport_ai_lifecycle_message(
    *,
    stage: str,
    run: TransportAIRun,
    suggestion: TransportAISuggestion | None,
    message: str | None,
) -> str:
    normalized_stage = str(stage or "").strip().lower()
    if normalized_stage not in _TRANSPORT_AI_LIFECYCLE_ACTION_BY_STAGE:
        raise ValueError(f"Unsupported transport AI lifecycle stage: {stage!r}")

    base_message = sanitize_transport_ai_string(
        str(message or _TRANSPORT_AI_LIFECYCLE_MESSAGE_BY_STAGE[normalized_stage]).strip()
    )
    lifecycle_message = (
        f"{base_message} run_key={run.run_key}; "
        f"suggestion_key={suggestion.suggestion_key if suggestion is not None else '-'}"
    )
    return lifecycle_message[:255]


def _build_transport_ai_lifecycle_details(
    *,
    stage: str,
    run: TransportAIRun,
    suggestion: TransportAISuggestion | None,
    request_path: str | None,
    extra_details: dict[str, Any] | None,
) -> str:
    payload = {
        "stage": stage,
        "run_key": run.run_key,
        "suggestion_key": suggestion.suggestion_key if suggestion is not None else None,
        "service_date": run.service_date.isoformat(),
        "route_kind": run.route_kind,
        "run_status": run.status,
        "suggestion_status": suggestion.status if suggestion is not None else None,
        "proposal_key": suggestion.proposal_key if suggestion is not None else None,
        "request_path": request_path,
        "extra": extra_details or {},
    }
    sanitized_payload = sanitize_transport_ai_raw_value(payload)
    return json.dumps(sanitized_payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def record_transport_ai_lifecycle_transition(
    db: Session,
    *,
    stage: str,
    run: TransportAIRun,
    suggestion: TransportAISuggestion | None = None,
    message: str | None = None,
    request_path: str | None = None,
    http_status: int | None = None,
    extra_details: dict[str, Any] | None = None,
) -> None:
    normalized_stage = str(stage or "").strip().lower()
    action = _TRANSPORT_AI_LIFECYCLE_ACTION_BY_STAGE.get(normalized_stage)
    if action is None:
        raise ValueError(f"Unsupported transport AI lifecycle stage: {stage!r}")

    lifecycle_message = _build_transport_ai_lifecycle_message(
        stage=normalized_stage,
        run=run,
        suggestion=suggestion,
        message=message,
    )
    lifecycle_details = _build_transport_ai_lifecycle_details(
        stage=normalized_stage,
        run=run,
        suggestion=suggestion,
        request_path=request_path,
        extra_details=extra_details,
    )

    logger.info("transport_ai_lifecycle %s", lifecycle_details)
    log_event(
        db,
        source="transport_ai",
        action=action,
        status="success",
        message=lifecycle_message,
        request_path=request_path,
        http_status=http_status,
        details=lifecycle_details,
        commit=False,
    )
    emit_transport_reevaluation_event(
        event_type=TRANSPORT_AI_ROUTE_CALCULATION_CHANGED_EVENT,
        reason=normalized_stage,
        source="transport_admin",
        message=lifecycle_message,
        service_date=run.service_date,
        route_kind=run.route_kind,
        proposal_key=suggestion.proposal_key if suggestion is not None else None,
    )


def record_transport_ai_settings_update(
    db: Session,
    *,
    actor_admin_user: AdminUser,
    payload: TransportAISettingsResponse,
    previous_provider: str | None,
    request_path: str | None = None,
    http_status: int | None = None,
) -> None:
    message = _build_transport_ai_settings_message(payload=payload)
    details = _build_transport_ai_settings_details(
        actor_admin_user=actor_admin_user,
        payload=payload,
        previous_provider=previous_provider,
        request_path=request_path,
    )
    logger.info("transport_ai_settings %s", details)
    log_event(
        db,
        source="transport_ai",
        action="settings_update",
        status="success",
        message=message,
        request_path=request_path,
        http_status=http_status,
        details=details,
        commit=False,
    )


def record_transport_ai_settings_failure(
    db: Session,
    *,
    actor_admin_user: AdminUser,
    project_id: int | None,
    project_name: str | None,
    provider: str | None,
    api_key: str | None,
    previous_provider: str | None,
    failure_detail: str,
    response_detail: str,
    request_path: str | None = None,
    http_status: int | None = None,
) -> None:
    message = _build_transport_ai_settings_failure_message(
        project_id=project_id,
        project_name=project_name,
        provider=provider,
        api_key=api_key,
        response_detail=response_detail,
    )
    details = _build_transport_ai_settings_failure_details(
        actor_admin_user=actor_admin_user,
        project_id=project_id,
        project_name=project_name,
        provider=provider,
        api_key=api_key,
        previous_provider=previous_provider,
        failure_detail=failure_detail,
        response_detail=response_detail,
        request_path=request_path,
    )
    logger.warning("transport_ai_settings %s", details)
    log_event(
        db,
        source="transport_ai",
        action="settings_update",
        status="failed",
        message=message,
        request_path=request_path,
        http_status=http_status,
        details=details,
        commit=False,
    )