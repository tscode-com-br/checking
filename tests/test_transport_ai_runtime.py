from pathlib import Path

from alembic import command
from alembic.config import Config
from cryptography.fernet import Fernet
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from sistema.app.core.config import Settings, settings
from sistema.app.database import Base
from sistema.app.models import AdminUser
from sistema.app.services import location_settings as location_settings_module
from sistema.app.services import transport_ai_llm_settings as transport_ai_llm_settings_module
from sistema.app.services.transport_ai_llm_settings import upsert_transport_ai_llm_settings
from sistema.app.services.transport_ai_runtime import validate_transport_ai_runtime_configuration


def _build_runtime_settings(**overrides) -> Settings:
    values = {
        "transport_ai_enabled": True,
        "transport_ai_agent_mode": "agent",
        "openai_model": "gpt-5-2025-08-07",
        "openai_api_key": "test-openai-key",
        "mapbox_access_token": "test-mapbox-token",
        "transport_ai_settings_encryption_key": Fernet.generate_key().decode("utf-8"),
        "transport_ai_max_passengers_per_run": 80,
        "transport_ai_max_runtime_seconds": 180,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


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
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _configure_transport_pricing(db) -> None:
    location_settings_module.upsert_transport_pricing_settings(
        db,
        price_currency_code=None,
        price_rate_unit="day",
        default_car_price=120,
        default_minivan_price=None,
        default_van_price=None,
        default_bus_price=None,
    )
    db.commit()


def _create_admin_user(db) -> AdminUser:
    admin_user = AdminUser(
        chave="AIRT",
        nome_completo="Transport AI Runtime Admin",
        password_hash=None,
        requires_password_reset=False,
        approved_by_admin_id=None,
        approved_at=None,
        password_reset_requested_at=None,
        created_at=location_settings_module.now_sgt(),
        updated_at=location_settings_module.now_sgt(),
    )
    db.add(admin_user)
    db.flush()
    return admin_user


def _configure_transport_ai_llm_settings(db, *, settings_obj: Settings, provider: str = "openai") -> None:
    admin_user = _create_admin_user(db)
    api_key = "persisted-openai-secret" if provider == "openai" else "persisted-deepseek-secret"
    upsert_transport_ai_llm_settings(
        db,
        provider=provider,
        api_key=api_key,
        actor_admin_user_id=admin_user.id,
        settings_obj=settings_obj,
    )
    db.commit()


def test_validate_transport_ai_runtime_configuration_returns_disabled_issue(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_runtime_disabled.db")
    try:
        with session_factory() as db:
            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=_build_runtime_settings(
                    transport_ai_enabled=False,
                    openai_api_key=None,
                    mapbox_access_token=None,
                ),
            )

        assert result.ok is False
        assert [issue.code for issue in result.issues] == ["transport_ai_disabled"]
    finally:
        engine.dispose()


def test_transport_ai_runtime_migration_adds_llm_snapshot_columns(tmp_path):
    database_url = _build_database_url(tmp_path / "transport_ai_runtime_head.db")

    _upgrade_database_to_head(database_url)

    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)
    column_names = {column["name"] for column in inspector.get_columns("transport_ai_runs")}
    engine.dispose()

    assert inspector.has_table("transport_ai_runs")
    assert {"llm_provider", "llm_model", "llm_reasoning_effort"}.issubset(column_names)


def test_validate_transport_ai_runtime_configuration_reports_missing_persisted_llm_settings(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_runtime_llm_missing.db")
    try:
        with session_factory() as db:
            _configure_transport_pricing(db)
            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=_build_runtime_settings(
                    openai_api_key="legacy-openai-key-should-not-help",
                    openai_model="legacy-openai-model-should-not-help",
                ),
            )

        assert result.ok is False
        assert [issue.code for issue in result.issues] == ["transport_ai_llm_settings_missing"]
    finally:
        engine.dispose()


def test_validate_transport_ai_runtime_configuration_allows_deterministic_mode_without_openai_key(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_runtime_deterministic_no_openai.db")
    try:
        with session_factory() as db:
            _configure_transport_pricing(db)
            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=_build_runtime_settings(
                    transport_ai_agent_mode="deterministic",
                    openai_api_key=None,
                ),
            )

        assert result.ok is True
        assert result.issues == []
    finally:
        engine.dispose()


def test_validate_transport_ai_runtime_configuration_reports_missing_mapbox_token(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_runtime_mapbox_missing.db")
    try:
        with session_factory() as db:
            _configure_transport_pricing(db)
            settings_obj = _build_runtime_settings(mapbox_access_token=None)
            _configure_transport_ai_llm_settings(db, settings_obj=settings_obj)
            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=settings_obj,
            )

        assert result.ok is False
        assert [issue.code for issue in result.issues] == ["mapbox_access_token_missing"]
    finally:
        engine.dispose()


def test_validate_transport_ai_runtime_configuration_reports_missing_pricing(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_runtime_pricing_missing.db")
    try:
        with session_factory() as db:
            settings_obj = _build_runtime_settings()
            _configure_transport_ai_llm_settings(db, settings_obj=settings_obj)
            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=settings_obj,
            )

        assert result.ok is False
        assert [issue.code for issue in result.issues] == ["transport_ai_pricing_missing"]
    finally:
        engine.dispose()


def test_validate_transport_ai_runtime_configuration_reports_invalid_runtime_limits(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_runtime_limits_invalid.db")
    try:
        with session_factory() as db:
            _configure_transport_pricing(db)
            settings_obj = _build_runtime_settings(
                transport_ai_max_passengers_per_run=0,
                transport_ai_max_runtime_seconds=0,
            )
            _configure_transport_ai_llm_settings(db, settings_obj=settings_obj)
            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=settings_obj,
            )

        assert result.ok is False
        assert [issue.code for issue in result.issues] == [
            "transport_ai_max_passengers_per_run_invalid",
            "transport_ai_max_runtime_seconds_invalid",
        ]
    finally:
        engine.dispose()


def test_validate_transport_ai_runtime_configuration_accepts_complete_configuration(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_runtime_complete.db")
    try:
        with session_factory() as db:
            _configure_transport_pricing(db)
            settings_obj = _build_runtime_settings(
                openai_api_key=None,
                openai_model="legacy-openai-model-ignored",
            )
            admin_user = _create_admin_user(db)
            upsert_transport_ai_llm_settings(
                db,
                provider="deepseek",
                api_key="deepseek-runtime-secret",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            db.commit()
            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=settings_obj,
            )

        assert result.ok is True
        assert result.issues == []
    finally:
        engine.dispose()


def test_validate_transport_ai_runtime_configuration_reports_removed_supported_provider(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_runtime_provider_removed.db")
    removed_defaults = transport_ai_llm_settings_module.TRANSPORT_AI_LLM_PROVIDER_DEFAULTS.pop("deepseek", None)
    try:
        with session_factory() as db:
            _configure_transport_pricing(db)
            settings_obj = _build_runtime_settings(
                openai_api_key=None,
                openai_model="legacy-openai-model-ignored",
            )
            admin_user = _create_admin_user(db)
            deepseek_defaults = removed_defaults
            assert deepseek_defaults is not None
            transport_ai_llm_settings_module.TRANSPORT_AI_LLM_PROVIDER_DEFAULTS["deepseek"] = deepseek_defaults
            try:
                upsert_transport_ai_llm_settings(
                    db,
                    provider="deepseek",
                    api_key="deepseek-runtime-secret",
                    actor_admin_user_id=admin_user.id,
                    settings_obj=settings_obj,
                )
                db.commit()
            finally:
                transport_ai_llm_settings_module.TRANSPORT_AI_LLM_PROVIDER_DEFAULTS.pop("deepseek", None)

            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=settings_obj,
            )

        assert result.ok is False
        assert [issue.code for issue in result.issues] == ["transport_ai_llm_provider_invalid"]
    finally:
        if removed_defaults is not None:
            transport_ai_llm_settings_module.TRANSPORT_AI_LLM_PROVIDER_DEFAULTS["deepseek"] = removed_defaults
        engine.dispose()