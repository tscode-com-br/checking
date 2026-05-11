from __future__ import annotations

from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from ..core.config import Settings, settings
from ..models import Project, TransportAILlmSettings, TransportAIProjectLlmSettings
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


class TransportAILlmSettingsProjectNotFoundError(TransportAILlmSettingsValidationError):
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


def _validate_transport_ai_actor_admin_user_id(actor_admin_user_id: int) -> None:
    if actor_admin_user_id <= 0:
        raise TransportAILlmSettingsValidationError(
            "Transport AI LLM settings actor admin user id must be greater than zero."
        )


def _validate_transport_ai_project_id(project_id: int) -> int:
    if project_id <= 0:
        raise TransportAILlmSettingsValidationError(
            "Transport AI project id must be greater than zero."
        )
    return project_id


def _require_transport_ai_project(db: Session, project_id: int) -> Project:
    normalized_project_id = _validate_transport_ai_project_id(project_id)
    project = db.get(Project, normalized_project_id)
    if project is None:
        raise TransportAILlmSettingsProjectNotFoundError("Transport AI project does not exist.")
    return project


def _validate_transport_ai_api_key_update(
    persisted_settings: TransportAILlmSettings | TransportAIProjectLlmSettings | None,
    *,
    normalized_provider: str,
    normalized_api_key: str | None,
) -> None:
    if persisted_settings is None and normalized_api_key is None:
        raise TransportAILlmSettingsValidationError(
            "Transport AI API key is required when creating LLM settings."
        )

    if (
        persisted_settings is not None
        and persisted_settings.provider != normalized_provider
        and normalized_api_key is None
    ):
        raise TransportAILlmSettingsValidationError(
            "Transport AI API key is required when changing the LLM provider."
        )


def _apply_transport_ai_llm_settings_values(
    persisted_settings: TransportAILlmSettings | TransportAIProjectLlmSettings,
    *,
    defaults: TransportAILlmProviderDefaults,
    normalized_api_key: str | None,
    actor_admin_user_id: int,
    settings_obj: Settings,
    timestamp,
) -> None:
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


def _build_transport_ai_llm_settings_payload(
    persisted_settings: TransportAILlmSettings | TransportAIProjectLlmSettings | None,
    *,
    global_settings: TransportAILlmSettings | None = None,
    project: Project | None = None,
    settings_obj: Settings = settings,
) -> TransportAISettingsResponse:
    validate_transport_ai_settings_encryption_availability(settings_obj=settings_obj)
    defaults = _resolve_transport_ai_persisted_provider_defaults(
        persisted_settings.provider if persisted_settings is not None else TRANSPORT_AI_LLM_DEFAULT_PROVIDER
    )
    has_api_key = bool(persisted_settings and persisted_settings.api_key_ciphertext)
    has_here_api_key = bool(global_settings and global_settings.here_api_key_ciphertext)
    return TransportAISettingsResponse(
        project_id=project.id if project is not None else None,
        project_name=project.name if project is not None else None,
        provider=defaults.provider,
        resolved_model=defaults.model_name,
        reasoning_effort=defaults.reasoning_effort,
        has_api_key=has_api_key,
        api_key_hint=(
            mask_transport_ai_api_key(api_key_last4=persisted_settings.api_key_last4)
            if has_api_key
            else None
        ),
        has_here_api_key=has_here_api_key,
        here_api_key_hint=(
            mask_transport_ai_api_key(api_key_last4=global_settings.here_api_key_last4)
            if has_here_api_key
            else None
        ),
    )


def _resolve_transport_ai_llm_runtime_settings_from_persisted_settings(
    persisted_settings: TransportAILlmSettings | TransportAIProjectLlmSettings | None,
    *,
    settings_obj: Settings = settings,
    missing_settings_message: str = "Transport AI LLM settings have not been configured yet.",
    missing_api_key_message: str = "Transport AI API key has not been configured yet.",
) -> TransportAILlmRuntimeSettings:
    if persisted_settings is None:
        raise TransportAILlmSettingsValidationError(missing_settings_message)
    if not persisted_settings.api_key_ciphertext:
        raise TransportAILlmSettingsValidationError(missing_api_key_message)
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


def validate_transport_ai_settings_encryption_availability(*, settings_obj: Settings = settings) -> None:
    _get_transport_ai_settings_fernet(settings_obj=settings_obj)


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


def get_legacy_transport_ai_llm_settings(db: Session) -> TransportAILlmSettings | None:
    return db.get(TransportAILlmSettings, 1)


def get_legacy_transport_ai_llm_settings_payload(
    db: Session,
    *,
    settings_obj: Settings = settings,
) -> TransportAISettingsResponse:
    return _build_transport_ai_llm_settings_payload(
        get_legacy_transport_ai_llm_settings(db),
        settings_obj=settings_obj,
    )


def get_transport_ai_llm_settings(
    db: Session,
    *,
    project_id: int,
) -> TransportAIProjectLlmSettings | None:
    normalized_project_id = _validate_transport_ai_project_id(project_id)
    return (
        db.query(TransportAIProjectLlmSettings)
        .filter(TransportAIProjectLlmSettings.project_id == normalized_project_id)
        .one_or_none()
    )


def get_transport_ai_project_llm_settings(
    db: Session,
    project_id: int,
) -> TransportAIProjectLlmSettings | None:
    return get_transport_ai_llm_settings(db, project_id=project_id)


def get_transport_ai_llm_settings_payload(
    db: Session,
    *,
    project_id: int,
    settings_obj: Settings = settings,
) -> TransportAISettingsResponse:
    project = _require_transport_ai_project(db, project_id)
    return _build_transport_ai_llm_settings_payload(
        get_transport_ai_llm_settings(db, project_id=project_id),
        global_settings=get_legacy_transport_ai_llm_settings(db),
        project=project,
        settings_obj=settings_obj,
    )


def get_transport_ai_project_llm_settings_payload(
    db: Session,
    *,
    project_id: int,
    settings_obj: Settings = settings,
) -> TransportAISettingsResponse:
    return get_transport_ai_llm_settings_payload(
        db,
        project_id=project_id,
        settings_obj=settings_obj,
    )


def upsert_legacy_transport_ai_llm_settings(
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
    persisted_settings = get_legacy_transport_ai_llm_settings(db)
    timestamp = now_sgt()

    _validate_transport_ai_actor_admin_user_id(actor_admin_user_id)
    _validate_transport_ai_api_key_update(
        persisted_settings,
        normalized_provider=normalized_provider,
        normalized_api_key=normalized_api_key,
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

    _apply_transport_ai_llm_settings_values(
        persisted_settings,
        defaults=defaults,
        normalized_api_key=normalized_api_key,
        actor_admin_user_id=actor_admin_user_id,
        settings_obj=settings_obj,
        timestamp=timestamp,
    )

    db.flush()
    return persisted_settings


def upsert_transport_ai_llm_settings(
    db: Session,
    *,
    project_id: int,
    provider: str,
    api_key: str | None,
    actor_admin_user_id: int,
    settings_obj: Settings = settings,
) -> TransportAIProjectLlmSettings:
    project = _require_transport_ai_project(db, project_id)
    normalized_provider = _normalize_transport_ai_provider(provider)
    normalized_api_key = _normalize_transport_ai_api_key(api_key)
    defaults = build_transport_ai_provider_defaults(normalized_provider)
    persisted_settings = get_transport_ai_llm_settings(db, project_id=project.id)
    timestamp = now_sgt()

    _validate_transport_ai_actor_admin_user_id(actor_admin_user_id)
    _validate_transport_ai_api_key_update(
        persisted_settings,
        normalized_provider=normalized_provider,
        normalized_api_key=normalized_api_key,
    )

    if persisted_settings is None:
        persisted_settings = TransportAIProjectLlmSettings(
            project_id=project.id,
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

    _apply_transport_ai_llm_settings_values(
        persisted_settings,
        defaults=defaults,
        normalized_api_key=normalized_api_key,
        actor_admin_user_id=actor_admin_user_id,
        settings_obj=settings_obj,
        timestamp=timestamp,
    )

    db.flush()
    return persisted_settings


def upsert_transport_ai_project_llm_settings(
    db: Session,
    *,
    project_id: int,
    provider: str,
    api_key: str | None,
    actor_admin_user_id: int,
    settings_obj: Settings = settings,
) -> TransportAIProjectLlmSettings:
    return upsert_transport_ai_llm_settings(
        db,
        project_id=project_id,
        provider=provider,
        api_key=api_key,
        actor_admin_user_id=actor_admin_user_id,
        settings_obj=settings_obj,
    )


def resolve_legacy_transport_ai_llm_runtime_settings(
    db: Session,
    *,
    settings_obj: Settings = settings,
) -> TransportAILlmRuntimeSettings:
    return _resolve_transport_ai_llm_runtime_settings_from_persisted_settings(
        get_legacy_transport_ai_llm_settings(db),
        settings_obj=settings_obj,
    )


def resolve_transport_ai_llm_runtime_settings(
    db: Session,
    *,
    project_id: int,
    settings_obj: Settings = settings,
) -> TransportAILlmRuntimeSettings:
    _require_transport_ai_project(db, project_id)
    return _resolve_transport_ai_llm_runtime_settings_from_persisted_settings(
        get_transport_ai_llm_settings(db, project_id=project_id),
        settings_obj=settings_obj,
        missing_settings_message=(
            "Transport AI LLM settings have not been configured for this project yet."
        ),
        missing_api_key_message=(
            "Transport AI API key has not been configured for this project yet."
        ),
    )


def resolve_transport_ai_project_llm_runtime_settings(
    db: Session,
    *,
    project_id: int,
    settings_obj: Settings = settings,
) -> TransportAILlmRuntimeSettings:
    return resolve_transport_ai_llm_runtime_settings(
        db,
        project_id=project_id,
        settings_obj=settings_obj,
    )


def save_transport_ai_here_api_key(
    db: Session,
    *,
    api_key: str,
    actor_admin_user_id: int,
    settings_obj: Settings = settings,
) -> TransportAILlmSettings:
    _validate_transport_ai_actor_admin_user_id(actor_admin_user_id)
    normalized_api_key = _normalize_transport_ai_api_key(api_key)
    if normalized_api_key is None:
        raise TransportAILlmSettingsValidationError("HERE API key is required.")

    timestamp = now_sgt()
    global_row = get_legacy_transport_ai_llm_settings(db)
    if global_row is None:
        defaults = build_transport_ai_provider_defaults(TRANSPORT_AI_LLM_DEFAULT_PROVIDER)
        global_row = TransportAILlmSettings(
            id=1,
            provider=defaults.provider,
            model_name=defaults.model_name,
            reasoning_effort=defaults.reasoning_effort,
            api_key_ciphertext=None,
            api_key_last4=None,
            here_api_key_ciphertext=None,
            here_api_key_last4=None,
            updated_by_admin_id=actor_admin_user_id,
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(global_row)

    global_row.here_api_key_ciphertext = encrypt_transport_ai_api_key(
        normalized_api_key,
        settings_obj=settings_obj,
    )
    global_row.here_api_key_last4 = normalized_api_key[-4:]
    global_row.updated_by_admin_id = actor_admin_user_id
    global_row.updated_at = timestamp
    db.flush()
    return global_row


def get_transport_ai_here_api_key_decrypted(
    db: Session,
    *,
    settings_obj: Settings = settings,
) -> str | None:
    global_row = get_legacy_transport_ai_llm_settings(db)
    if global_row is None or not global_row.here_api_key_ciphertext:
        return None
    return decrypt_transport_ai_api_key(
        global_row.here_api_key_ciphertext,
        settings_obj=settings_obj,
    )
