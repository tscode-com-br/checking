from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from cryptography.fernet import Fernet
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.core.config import Settings, settings
from sistema.app.database import Base
from sistema.app.models import AdminUser, TransportAILlmSettings
from sistema.app.services.transport_ai_llm_settings import (
    TRANSPORT_AI_LLM_DEFAULT_PROVIDER,
    TRANSPORT_AI_LLM_DEEPSEEK_BASE_URL,
    TransportAILlmSettingsEncryptionError,
    TransportAILlmSettingsValidationError,
    build_transport_ai_provider_defaults,
    decrypt_transport_ai_api_key,
    encrypt_transport_ai_api_key,
    get_transport_ai_llm_settings_payload,
    mask_transport_ai_api_key,
    resolve_transport_ai_llm_runtime_settings,
    upsert_transport_ai_llm_settings,
)


def _build_database_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path.as_posix()}"


def _upgrade_database_to_head(database_url: str) -> None:
    config = Config("alembic.ini")
    previous_database_url = settings.database_url
    settings.database_url = database_url

    try:
        command.upgrade(config, "head")
    finally:
        settings.database_url = previous_database_url


def _build_session_factory(db_path: Path):
    database_url = _build_database_url(db_path)
    engine = sa.create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def _fixture_timestamp() -> datetime:
    return datetime(2026, 5, 4, 12, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))


def _create_admin_user(session: Session, *, chave: str = "AI07") -> AdminUser:
    timestamp = _fixture_timestamp()
    admin_user = AdminUser(
        chave=chave,
        nome_completo="Transport AI LLM Settings Admin",
        password_hash=None,
        requires_password_reset=False,
        approved_by_admin_id=None,
        approved_at=None,
        password_reset_requested_at=None,
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(admin_user)
    session.flush()
    return admin_user


def _build_settings(**overrides) -> Settings:
    values = {
        "transport_ai_settings_encryption_key": Fernet.generate_key().decode("utf-8"),
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_transport_ai_llm_settings_migration_upgrades_head_on_sqlite(tmp_path):
    database_url = _build_database_url(tmp_path / "transport_ai_llm_settings_head.db")

    _upgrade_database_to_head(database_url)

    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)
    column_names = {column["name"] for column in inspector.get_columns("transport_ai_llm_settings")}
    engine.dispose()

    assert inspector.has_table("transport_ai_llm_settings")
    assert {
        "id",
        "provider",
        "model_name",
        "reasoning_effort",
        "api_key_ciphertext",
        "api_key_last4",
        "updated_by_admin_id",
        "created_at",
        "updated_at",
    }.issubset(column_names)


def test_transport_ai_llm_settings_provider_defaults_are_fixed():
    openai_defaults = build_transport_ai_provider_defaults("openai")
    deepseek_defaults = build_transport_ai_provider_defaults("deepseek")

    assert TRANSPORT_AI_LLM_DEFAULT_PROVIDER == "openai"
    assert openai_defaults.provider == "openai"
    assert openai_defaults.model_name == "gpt-5.4-2026-03-05"
    assert openai_defaults.reasoning_effort == "high"
    assert openai_defaults.base_url is None
    assert deepseek_defaults.provider == "deepseek"
    assert deepseek_defaults.model_name == "deepseek-v4-pro"
    assert deepseek_defaults.reasoning_effort == "high"
    assert deepseek_defaults.base_url == TRANSPORT_AI_LLM_DEEPSEEK_BASE_URL


def test_transport_ai_llm_settings_encrypts_decrypts_and_masks_api_key():
    configured_settings = _build_settings()

    ciphertext = encrypt_transport_ai_api_key("sk-test-secret-1234", settings_obj=configured_settings)
    decrypted_value = decrypt_transport_ai_api_key(ciphertext, settings_obj=configured_settings)

    assert ciphertext != "sk-test-secret-1234"
    assert decrypted_value == "sk-test-secret-1234"
    assert mask_transport_ai_api_key("sk-test-secret-1234") == "***1234"
    assert mask_transport_ai_api_key(api_key_last4="1234") == "***1234"


def test_transport_ai_llm_settings_rejects_missing_or_invalid_encryption_key():
    missing_key_settings = _build_settings(transport_ai_settings_encryption_key=None)
    invalid_key_settings = _build_settings(transport_ai_settings_encryption_key="not-a-valid-fernet-key")

    try:
        encrypt_transport_ai_api_key("sk-test-secret", settings_obj=missing_key_settings)
        raise AssertionError("encrypt should fail when the encryption key is missing")
    except TransportAILlmSettingsEncryptionError:
        pass

    try:
        encrypt_transport_ai_api_key("sk-test-secret", settings_obj=invalid_key_settings)
        raise AssertionError("encrypt should fail when the encryption key is invalid")
    except TransportAILlmSettingsEncryptionError:
        pass


def test_transport_ai_llm_settings_payload_masks_secret_and_runtime_resolution_decrypts_it(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_llm_settings_payload.db")
    configured_settings = _build_settings()
    try:
        with session_factory() as session:
            admin_user = _create_admin_user(session)
            persisted_settings = upsert_transport_ai_llm_settings(
                session,
                provider="openai",
                api_key="sk-test-openai-1234",
                actor_admin_user_id=admin_user.id,
                settings_obj=configured_settings,
            )
            session.commit()

            payload = get_transport_ai_llm_settings_payload(session)
            runtime_settings = resolve_transport_ai_llm_runtime_settings(
                session,
                settings_obj=configured_settings,
            )
            serialized_payload = payload.model_dump_json()

        assert payload.provider == "openai"
        assert payload.resolved_model == "gpt-5.4-2026-03-05"
        assert payload.reasoning_effort == "high"
        assert payload.has_api_key is True
        assert payload.api_key_hint == "***1234"
        assert "sk-test-openai-1234" not in serialized_payload
        assert persisted_settings.api_key_ciphertext not in serialized_payload
        assert runtime_settings.provider == "openai"
        assert runtime_settings.model_name == "gpt-5.4-2026-03-05"
        assert runtime_settings.reasoning_effort == "high"
        assert runtime_settings.api_key == "sk-test-openai-1234"
        assert persisted_settings.api_key_ciphertext != "sk-test-openai-1234"
    finally:
        engine.dispose()


def test_transport_ai_llm_settings_preserves_existing_key_when_provider_is_unchanged(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_llm_settings_preserve.db")
    configured_settings = _build_settings()
    try:
        with session_factory() as session:
            admin_user = _create_admin_user(session)
            first_persisted_settings = upsert_transport_ai_llm_settings(
                session,
                provider="openai",
                api_key="sk-test-openai-1234",
                actor_admin_user_id=admin_user.id,
                settings_obj=configured_settings,
            )
            first_ciphertext = first_persisted_settings.api_key_ciphertext
            session.commit()

            updated_settings = upsert_transport_ai_llm_settings(
                session,
                provider="openai",
                api_key=None,
                actor_admin_user_id=admin_user.id,
                settings_obj=configured_settings,
            )
            session.commit()

            runtime_settings = resolve_transport_ai_llm_runtime_settings(
                session,
                settings_obj=configured_settings,
            )

        assert updated_settings.api_key_ciphertext == first_ciphertext
        assert runtime_settings.api_key == "sk-test-openai-1234"
    finally:
        engine.dispose()


def test_transport_ai_llm_settings_requires_key_on_first_save_and_provider_change(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_llm_settings_validation.db")
    configured_settings = _build_settings()
    try:
        with session_factory() as session:
            admin_user = _create_admin_user(session)

            try:
                upsert_transport_ai_llm_settings(
                    session,
                    provider="openai",
                    api_key=None,
                    actor_admin_user_id=admin_user.id,
                    settings_obj=configured_settings,
                )
                raise AssertionError("first save should require an API key")
            except TransportAILlmSettingsValidationError:
                session.rollback()

            upsert_transport_ai_llm_settings(
                session,
                provider="openai",
                api_key="sk-test-openai-1234",
                actor_admin_user_id=admin_user.id,
                settings_obj=configured_settings,
            )
            session.commit()

            try:
                upsert_transport_ai_llm_settings(
                    session,
                    provider="deepseek",
                    api_key=None,
                    actor_admin_user_id=admin_user.id,
                    settings_obj=configured_settings,
                )
                raise AssertionError("provider change should require a new API key")
            except TransportAILlmSettingsValidationError:
                session.rollback()

            updated_settings = upsert_transport_ai_llm_settings(
                session,
                provider="deepseek",
                api_key="deepseek-secret-9876",
                actor_admin_user_id=admin_user.id,
                settings_obj=configured_settings,
            )
            session.commit()

            persisted_settings = session.get(TransportAILlmSettings, 1)

        assert updated_settings.provider == "deepseek"
        assert updated_settings.model_name == "deepseek-v4-pro"
        assert updated_settings.reasoning_effort == "high"
        assert updated_settings.api_key_last4 == "9876"
        assert persisted_settings is not None
        assert persisted_settings.provider == "deepseek"
    finally:
        engine.dispose()
