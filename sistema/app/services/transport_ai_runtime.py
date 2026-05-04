from __future__ import annotations

from sqlalchemy.orm import Session

from ..core.config import Settings, normalize_transport_ai_agent_mode, settings
from ..schemas import TransportAIPreflightCheckResult, TransportAIPreflightIssue
from .location_settings import get_transport_pricing_settings
from .transport_ai_llm_settings import (
    TransportAILlmSettingsEncryptionError,
    TransportAILlmSettingsValidationError,
    get_transport_ai_llm_settings,
    get_supported_transport_ai_llm_providers,
    resolve_transport_ai_llm_runtime_settings,
)


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


def validate_transport_ai_runtime_configuration(
    db: Session,
    *,
    settings_obj: Settings = settings,
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
        persisted_llm_settings = get_transport_ai_llm_settings(db)
        if persisted_llm_settings is None:
            issues.append(
                _build_transport_ai_preflight_issue(
                    code="transport_ai_llm_settings_missing",
                    message="Transport AI LLM settings have not been configured yet.",
                    setting_name="transport_ai_llm_settings",
                )
            )
        else:
            provider = str(persisted_llm_settings.provider or "").strip().lower()
            if provider not in set(get_supported_transport_ai_llm_providers()):
                issues.append(
                    _build_transport_ai_preflight_issue(
                        code="transport_ai_llm_provider_invalid",
                        message="The configured Transport AI LLM provider is not supported.",
                        setting_name="transport_ai_llm_provider",
                    )
                )
            else:
                try:
                    resolve_transport_ai_llm_runtime_settings(db, settings_obj=settings_obj)
                except (TransportAILlmSettingsValidationError, TransportAILlmSettingsEncryptionError):
                    issues.append(
                        _build_transport_ai_preflight_issue(
                            code="transport_ai_llm_api_key_missing",
                            message="The configured Transport AI API key is missing or could not be decrypted.",
                            setting_name="transport_ai_llm_api_key",
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

    if settings_obj.transport_ai_max_passengers_per_run <= 0:
        issues.append(
            _build_transport_ai_preflight_issue(
                code="transport_ai_max_passengers_per_run_invalid",
                message="The maximum passengers per Transport AI run must be greater than zero.",
                setting_name="transport_ai_max_passengers_per_run",
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

    return TransportAIPreflightCheckResult(
        ok=not any(issue.blocking for issue in issues),
        issues=issues,
    )