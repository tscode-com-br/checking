from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
from cryptography.fernet import Fernet
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from sistema.app.core.config import Settings, settings
from sistema.app.database import Base
from sistema.app.models import AdminUser, Project, TransportAIProjectLlmSettings
from sistema.app.schemas import (
    ProjectRow,
    TransportAgentPlanningInput,
    TransportAgentPlanningLimits,
    TransportAgentPlanningPartition,
    TransportAgentPlanningSettings,
)
from sistema.app.services import location_settings as location_settings_module
from sistema.app.services import transport_ai_llm_settings as transport_ai_llm_settings_module
from sistema.app.services.transport_ai_llm_settings import (
    upsert_transport_ai_llm_settings,
)
from sistema.app.services.transport_ai_runtime import validate_transport_ai_runtime_configuration


def _build_runtime_settings(**overrides) -> Settings:
    values = {
        "transport_ai_enabled": True,
        "transport_ai_agent_mode": "agent",
        "openai_model": "gpt-5-2025-08-07",
        "openai_api_key": "test-openai-key",
        "mapbox_access_token": "test-mapbox-token",
        "transport_ai_settings_encryption_key": Fernet.generate_key().decode("utf-8"),
        "transport_ai_operational_approval_evidence": "phase8-loadtest-2026-05-05",
        "transport_ai_max_passengers_per_run": 80,
        "transport_ai_max_concurrent_runs": 1,
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


def _create_project(db, *, name: str) -> Project:
    project = Project(
        name=name,
        country_code="SG",
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address="1 Marina Boulevard",
        zip_code="018989",
    )
    db.add(project)
    db.flush()
    return project


def _build_planning_input_for_projects(
    *,
    projects: list[Project],
    settings_obj: Settings,
) -> TransportAgentPlanningInput:
    project_rows = {
        project.name: ProjectRow(
            id=project.id,
            name=project.name,
            country_code=project.country_code,
            country_name=project.country_name,
            timezone_name=project.timezone_name,
            timezone_label=project.timezone_name,
            address=project.address,
            zip_code=project.zip_code,
        )
        for project in projects
    }
    partitions = [
        TransportAgentPlanningPartition(
            partition_key=f"extra:{project.name}:{project.country_code}",
            request_kind="extra",
            project_id=project.id,
            project_name=project.name,
            country_code=project.country_code,
            country_name=project.country_name,
            destination_project=project_rows[project.name],
            requests=[],
            candidate_vehicles=[],
        )
        for project in projects
    ]
    return TransportAgentPlanningInput(
        planning_input_hash="0" * 64,
        service_date=date(2026, 5, 3),
        route_kind="home_to_work",
        snapshot_key="transport-ai-runtime-planning-input",
        captured_at=location_settings_module.now_sgt(),
        limits=TransportAgentPlanningLimits(
            earliest_boarding_time="06:50",
            arrival_at_work_time="07:45",
            max_passengers_per_run=settings_obj.transport_ai_max_passengers_per_run,
            max_runtime_seconds=settings_obj.transport_ai_max_runtime_seconds,
        ),
        settings=TransportAgentPlanningSettings(
            work_to_home_time="16:45",
            last_update_time="16:00",
            default_tolerance_minutes=5,
            price_currency_code=None,
            price_rate_unit="day",
            vehicle_type_configs=[],
        ),
        projects_by_name=project_rows,
        requests_by_scope={"regular": [], "weekend": [], "extra": []},
        vehicles_by_scope={"regular": [], "weekend": [], "extra": []},
        partitions=partitions,
        llm_runtime_projects=[],
        preflight_issues=[],
        total_requests=len(partitions),
        total_candidate_vehicles=0,
    )


def _configure_transport_ai_llm_settings(
    db,
    *,
    settings_obj: Settings,
    project_id: int,
    provider: str = "openai",
    actor_admin_user_id: int | None = None,
) -> None:
    admin_user_id = actor_admin_user_id or _create_admin_user(db).id
    api_key = "persisted-openai-secret" if provider == "openai" else "persisted-deepseek-secret"
    upsert_transport_ai_llm_settings(
        db,
        project_id=project_id,
        provider=provider,
        api_key=api_key,
        actor_admin_user_id=admin_user_id,
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


def test_validate_transport_ai_runtime_configuration_without_planning_input_skips_project_llm_check(tmp_path):
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

        assert result.ok is True
        assert result.issues == []
    finally:
        engine.dispose()


def test_validate_transport_ai_runtime_configuration_reports_unavailable_settings_encryption(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_runtime_settings_encryption_missing.db")
    try:
        with session_factory() as db:
            _configure_transport_pricing(db)
            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=_build_runtime_settings(
                    transport_ai_settings_encryption_key=None,
                ),
            )

        assert result.ok is False
        assert [issue.code for issue in result.issues] == ["transport_ai_settings_encryption_unavailable"]
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
                transport_ai_max_concurrent_runs=0,
                transport_ai_max_runtime_seconds=0,
            )
            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=settings_obj,
            )

        assert result.ok is False
        assert [issue.code for issue in result.issues] == [
            "transport_ai_max_concurrent_runs_invalid",
            "transport_ai_max_runtime_seconds_invalid",
            "transport_ai_max_passengers_per_run_invalid",
        ]
    finally:
        engine.dispose()


def test_validate_transport_ai_runtime_configuration_reports_missing_operational_approval(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_runtime_approval_missing.db")
    try:
        with session_factory() as db:
            _configure_transport_pricing(db)
            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=_build_runtime_settings(
                    transport_ai_operational_approval_evidence=None,
                ),
            )

        assert result.ok is False
        assert [issue.code for issue in result.issues] == ["transport_ai_operational_approval_missing"]
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
            project = _create_project(db, name="PRUNTIME-COMPLETE")
            _configure_transport_ai_llm_settings(
                db,
                settings_obj=settings_obj,
                project_id=project.id,
                provider="deepseek",
            )
            planning_input = _build_planning_input_for_projects(
                projects=[project],
                settings_obj=settings_obj,
            )
            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=settings_obj,
                planning_input=planning_input,
            )

        assert result.ok is True
        assert result.issues == []
    finally:
        engine.dispose()


def test_validate_transport_ai_runtime_configuration_reports_missing_project_llm_settings(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_runtime_project_missing.db")
    try:
        with session_factory() as db:
            _configure_transport_pricing(db)
            settings_obj = _build_runtime_settings(
                openai_api_key=None,
                openai_model="legacy-openai-model-ignored",
            )
            project = _create_project(db, name="PRUNTIME-MISSING")
            planning_input = _build_planning_input_for_projects(
                projects=[project],
                settings_obj=settings_obj,
            )

            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=settings_obj,
                planning_input=planning_input,
            )

        assert result.ok is False
        assert [issue.code for issue in result.issues] == ["transport_ai_llm_settings_missing"]
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
            project = _create_project(db, name="PRUNTIME-PROVIDER")
            planning_input = _build_planning_input_for_projects(
                projects=[project],
                settings_obj=settings_obj,
            )
            deepseek_defaults = removed_defaults
            assert deepseek_defaults is not None
            transport_ai_llm_settings_module.TRANSPORT_AI_LLM_PROVIDER_DEFAULTS["deepseek"] = deepseek_defaults
            try:
                upsert_transport_ai_llm_settings(
                    db,
                    project_id=project.id,
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
                planning_input=planning_input,
            )

        assert result.ok is False
        assert [issue.code for issue in result.issues] == ["transport_ai_llm_provider_invalid"]
    finally:
        if removed_defaults is not None:
            transport_ai_llm_settings_module.TRANSPORT_AI_LLM_PROVIDER_DEFAULTS["deepseek"] = removed_defaults
        engine.dispose()


def test_validate_transport_ai_runtime_configuration_reports_project_runtime_conflict(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_runtime_project_conflict.db")
    try:
        with session_factory() as db:
            _configure_transport_pricing(db)
            settings_obj = _build_runtime_settings(
                openai_api_key=None,
                openai_model="legacy-openai-model-ignored",
            )
            admin_user = _create_admin_user(db)
            project_a = _create_project(db, name="PRUNTIME-CONFLICT-A")
            project_b = _create_project(db, name="PRUNTIME-CONFLICT-B")
            _configure_transport_ai_llm_settings(
                db,
                settings_obj=settings_obj,
                project_id=project_a.id,
                provider="openai",
                actor_admin_user_id=admin_user.id,
            )
            _configure_transport_ai_llm_settings(
                db,
                settings_obj=settings_obj,
                project_id=project_b.id,
                provider="deepseek",
                actor_admin_user_id=admin_user.id,
            )
            planning_input = _build_planning_input_for_projects(
                projects=[project_a, project_b],
                settings_obj=settings_obj,
            )

            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=settings_obj,
                planning_input=planning_input,
            )

        assert result.ok is False
        assert [issue.code for issue in result.issues] == ["transport_ai_llm_runtime_conflict"]
    finally:
        engine.dispose()


def test_validate_transport_ai_runtime_configuration_reports_project_runtime_conflict_for_different_api_keys(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_runtime_project_key_conflict.db")
    try:
        with session_factory() as db:
            _configure_transport_pricing(db)
            settings_obj = _build_runtime_settings(
                openai_api_key=None,
                openai_model="legacy-openai-model-ignored",
            )
            admin_user = _create_admin_user(db)
            project_a = _create_project(db, name="PRUNTIME-KEY-CONFLICT-A")
            project_b = _create_project(db, name="PRUNTIME-KEY-CONFLICT-B")
            upsert_transport_ai_llm_settings(
                db,
                project_id=project_a.id,
                provider="openai",
                api_key="key-conflict-openai-1111",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            upsert_transport_ai_llm_settings(
                db,
                project_id=project_b.id,
                provider="openai",
                api_key="key-conflict-openai-2222",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            db.commit()
            planning_input = _build_planning_input_for_projects(
                projects=[project_a, project_b],
                settings_obj=settings_obj,
            )

            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=settings_obj,
                planning_input=planning_input,
            )

        assert result.ok is False
        assert [issue.code for issue in result.issues] == ["transport_ai_llm_runtime_conflict"]
    finally:
        engine.dispose()


def test_validate_transport_ai_runtime_configuration_conflict_serialization_excludes_api_keys_and_ciphertexts(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_runtime_project_key_conflict_redaction.db")
    try:
        with session_factory() as db:
            _configure_transport_pricing(db)
            settings_obj = _build_runtime_settings(
                openai_api_key=None,
                openai_model="legacy-openai-model-ignored",
            )
            admin_user = _create_admin_user(db)
            project_a = _create_project(db, name="PRUNTIME-KEY-REDACT-A")
            project_b = _create_project(db, name="PRUNTIME-KEY-REDACT-B")
            upsert_transport_ai_llm_settings(
                db,
                project_id=project_a.id,
                provider="openai",
                api_key="runtime-redaction-openai-1111",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            upsert_transport_ai_llm_settings(
                db,
                project_id=project_b.id,
                provider="openai",
                api_key="runtime-redaction-openai-2222",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            db.commit()

            persisted_rows = db.execute(
                sa.select(TransportAIProjectLlmSettings)
                .order_by(TransportAIProjectLlmSettings.project_id.asc())
            ).scalars().all()
            planning_input = _build_planning_input_for_projects(
                projects=[project_a, project_b],
                settings_obj=settings_obj,
            )

            result = validate_transport_ai_runtime_configuration(
                db,
                settings_obj=settings_obj,
                planning_input=planning_input,
            )
            serialized_result = result.model_dump_json()

        assert result.ok is False
        assert [issue.code for issue in result.issues] == ["transport_ai_llm_runtime_conflict"]
        assert result.issues[0].message.endswith("Conflicting projects: PRUNTIME-KEY-REDACT-B.")
        assert "runtime-redaction-openai-1111" not in serialized_result
        assert "runtime-redaction-openai-2222" not in serialized_result
        assert '"api_key":' not in serialized_result
        assert '"api_key_ciphertext":' not in serialized_result
        assert all(row.api_key_ciphertext not in serialized_result for row in persisted_rows)
    finally:
        engine.dispose()