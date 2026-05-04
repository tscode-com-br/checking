from __future__ import annotations

from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from ..core.config import Settings, settings
from ..models import TransportAILlmSettings
from ..schemas import TransportAISettingsResponse
from .time_utils import now_sgt


TRANSPORT_AI_LLM_DEFAULT_PROVIDER = "openai"
TRANSPORT_AI_LLM_DEFAULT_REASONING_EFFORT = "high"
TRANSPORT_AI_LLM_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
TRANSPORT_AI_LLM_UNSUPPORTED_PROVIDER_MESSAGE = (
    "The configured Transport AI LLM provider is no longer supported. "
    "Select OpenAI or DeepSeek and save the AI settings again."
)
TRANSPORT_AI_LLM_PROVIDER_DEFAULTS = {
    "openai": {
        "provider": "openai",
        "model_name": "gpt-5.4-2026-03-05",
        "reasoning_effort": TRANSPORT_AI_LLM_DEFAULT_REASONING_EFFORT,
        "base_url": None,
    },
    "deepseek": {
        "provider": "deepseek",
        "model_name": "deepseek-v4-pro",
        "reasoning_effort": TRANSPORT_AI_LLM_DEFAULT_REASONING_EFFORT,
        "base_url": TRANSPORT_AI_LLM_DEEPSEEK_BASE_URL,
    },
}


class TransportAILlmSettingsError(RuntimeError):
    pass


class TransportAILlmSettingsEncryptionError(TransportAILlmSettingsError):
    pass


class TransportAILlmSettingsValidationError(TransportAILlmSettingsError):
    pass


@dataclass(frozen=True, slots=True)
class TransportAILlmProviderDefaults:
    provider: str
    model_name: str
    reasoning_effort: str
    base_url: str | None = None


@dataclass(frozen=True, slots=True)
class TransportAILlmRuntimeSettings:
    provider: str
    model_name: str
    reasoning_effort: str
    api_key: str
    base_url: str | None = None


def get_supported_transport_ai_llm_providers() -> tuple[str, ...]:
    return tuple(sorted(TRANSPORT_AI_LLM_PROVIDER_DEFAULTS))


def _normalize_transport_ai_provider(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in TRANSPORT_AI_LLM_PROVIDER_DEFAULTS:
        raise TransportAILlmSettingsValidationError(
            "Transport AI LLM provider must be 'openai' or 'deepseek'."
        )
    return normalized


def _resolve_transport_ai_persisted_provider_defaults(provider: str) -> TransportAILlmProviderDefaults:
    try:
        return build_transport_ai_provider_defaults(provider)
    except TransportAILlmSettingsValidationError as exc:
        raise TransportAILlmSettingsValidationError(
            TRANSPORT_AI_LLM_UNSUPPORTED_PROVIDER_MESSAGE
        ) from exc


def _normalize_transport_ai_api_key(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _get_transport_ai_settings_fernet(*, settings_obj: Settings = settings) -> Fernet:
    encryption_key = str(settings_obj.transport_ai_settings_encryption_key or "").strip()
    if not encryption_key:
        raise TransportAILlmSettingsEncryptionError(
            "Transport AI settings encryption key is not configured."
        )
    try:
        return Fernet(encryption_key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise TransportAILlmSettingsEncryptionError(
            "Transport AI settings encryption key is invalid."
        ) from exc


def build_transport_ai_provider_defaults(provider: str) -> TransportAILlmProviderDefaults:
    normalized_provider = _normalize_transport_ai_provider(provider)
    defaults = TRANSPORT_AI_LLM_PROVIDER_DEFAULTS[normalized_provider]
    return TransportAILlmProviderDefaults(
        provider=defaults["provider"],
        model_name=defaults["model_name"],
        reasoning_effort=defaults["reasoning_effort"],
        base_url=defaults["base_url"],
    )


def encrypt_transport_ai_api_key(
    api_key: str,
    *,
    settings_obj: Settings = settings,
) -> str:
    normalized_api_key = _normalize_transport_ai_api_key(api_key)
    if normalized_api_key is None:
        raise TransportAILlmSettingsValidationError("Transport AI API key is required.")
    return _get_transport_ai_settings_fernet(settings_obj=settings_obj).encrypt(
        normalized_api_key.encode("utf-8")
    ).decode("utf-8")


def decrypt_transport_ai_api_key(
    api_key_ciphertext: str,
    *,
    settings_obj: Settings = settings,
) -> str:
    normalized_ciphertext = str(api_key_ciphertext or "").strip()
    if not normalized_ciphertext:
        raise TransportAILlmSettingsValidationError(
            "Transport AI API key ciphertext is required."
        )
    try:
        decrypted_bytes = _get_transport_ai_settings_fernet(settings_obj=settings_obj).decrypt(
            normalized_ciphertext.encode("utf-8")
        )
    except InvalidToken as exc:
        raise TransportAILlmSettingsEncryptionError(
            "Transport AI API key ciphertext could not be decrypted."
        ) from exc
    decrypted_value = decrypted_bytes.decode("utf-8").strip()
    if not decrypted_value:
        raise TransportAILlmSettingsEncryptionError(
            "Transport AI API key ciphertext resolved to an empty value."
        )
    return decrypted_value


def mask_transport_ai_api_key(api_key: str | None = None, *, api_key_last4: str | None = None) -> str | None:
    if api_key_last4 is not None:
        normalized_last4 = str(api_key_last4).strip()
        if normalized_last4:
            return f"***{normalized_last4}"
    normalized_api_key = _normalize_transport_ai_api_key(api_key)
    if normalized_api_key is None:
        return None
    return f"***{normalized_api_key[-4:]}"


def get_transport_ai_llm_settings(db: Session) -> TransportAILlmSettings | None:
    return db.get(TransportAILlmSettings, 1)


def get_transport_ai_llm_settings_payload(db: Session) -> TransportAISettingsResponse:
    persisted_settings = get_transport_ai_llm_settings(db)
    defaults = _resolve_transport_ai_persisted_provider_defaults(
        persisted_settings.provider if persisted_settings is not None else TRANSPORT_AI_LLM_DEFAULT_PROVIDER
    )
    has_api_key = bool(persisted_settings and persisted_settings.api_key_ciphertext)
    return TransportAISettingsResponse(
        provider=defaults.provider,
        resolved_model=defaults.model_name,
        reasoning_effort=defaults.reasoning_effort,
        has_api_key=has_api_key,
        api_key_hint=(
            mask_transport_ai_api_key(api_key_last4=persisted_settings.api_key_last4)
            if has_api_key
            else None
        ),
    )


def upsert_transport_ai_llm_settings(
    db: Session,
    *,
    provider: str,
    api_key: str | None,
    actor_admin_user_id: int,
    settings_obj: Settings = settings,
) -> TransportAILlmSettings:
    normalized_provider = _normalize_transport_ai_provider(provider)
    normalized_api_key = _normalize_transport_ai_api_key(api_key)
    defaults = build_transport_ai_provider_defaults(normalized_provider)
    persisted_settings = get_transport_ai_llm_settings(db)
    timestamp = now_sgt()

    if actor_admin_user_id <= 0:
        raise TransportAILlmSettingsValidationError(
            "Transport AI LLM settings actor admin user id must be greater than zero."
        )

    if persisted_settings is None and normalized_api_key is None:
        raise TransportAILlmSettingsValidationError(
            "Transport AI API key is required when creating LLM settings."
        )

    if persisted_settings is not None and persisted_settings.provider != normalized_provider and normalized_api_key is None:
        raise TransportAILlmSettingsValidationError(
            "Transport AI API key is required when changing the LLM provider."
        )

    if persisted_settings is None:
        persisted_settings = TransportAILlmSettings(
            id=1,
            provider=defaults.provider,
            model_name=defaults.model_name,
            reasoning_effort=defaults.reasoning_effort,
            api_key_ciphertext=None,
            api_key_last4=None,
            updated_by_admin_id=actor_admin_user_id,
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(persisted_settings)

    if normalized_api_key is not None:
        persisted_settings.api_key_ciphertext = encrypt_transport_ai_api_key(
            normalized_api_key,
            settings_obj=settings_obj,
        )
        persisted_settings.api_key_last4 = normalized_api_key[-4:]
    elif not persisted_settings.api_key_ciphertext:
        raise TransportAILlmSettingsValidationError(
            "Transport AI API key is required when no encrypted key has been stored yet."
        )

    persisted_settings.provider = defaults.provider
    persisted_settings.model_name = defaults.model_name
    persisted_settings.reasoning_effort = defaults.reasoning_effort
    persisted_settings.updated_by_admin_id = actor_admin_user_id
    persisted_settings.updated_at = timestamp

    db.flush()
    return persisted_settings


def resolve_transport_ai_llm_runtime_settings(
    db: Session,
    *,
    settings_obj: Settings = settings,
) -> TransportAILlmRuntimeSettings:
    persisted_settings = get_transport_ai_llm_settings(db)
    if persisted_settings is None:
        raise TransportAILlmSettingsValidationError(
            "Transport AI LLM settings have not been configured yet."
        )
    if not persisted_settings.api_key_ciphertext:
        raise TransportAILlmSettingsValidationError(
            "Transport AI API key has not been configured yet."
        )
    defaults = _resolve_transport_ai_persisted_provider_defaults(persisted_settings.provider)
    return TransportAILlmRuntimeSettings(
        provider=defaults.provider,
        model_name=defaults.model_name,
        reasoning_effort=defaults.reasoning_effort,
        api_key=decrypt_transport_ai_api_key(
            persisted_settings.api_key_ciphertext,
            settings_obj=settings_obj,
        ),
        base_url=defaults.base_url,
    )
