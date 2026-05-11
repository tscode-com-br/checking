import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.core.config import settings
from sistema.app.models import AdminUser, TransportAIRun
from sistema.app.services.transport_ai_runs import resolve_transport_ai_run_llm_snapshot_fields


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


def _build_session_factory(tmp_path: Path) -> tuple[sessionmaker[Session], sa.Engine]:
    database_url = _build_database_url(tmp_path / "transport_ai_runs.db")
    _upgrade_database_to_head(database_url)
    engine = sa.create_engine(database_url)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False), engine


def _create_admin_user(session: Session) -> AdminUser:
    timestamp = datetime(2026, 4, 30, 9, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    admin_user = AdminUser(
        chave="AI01",
        nome_completo="Transport AI Admin",
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


def _build_transport_ai_run(*, actor_user_id: int, status: str = "requested", run_key: str = "run-requested-001") -> TransportAIRun:
    timestamp = datetime(2026, 4, 30, 9, 15, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    return TransportAIRun(
        run_key=run_key,
        service_date=date(2026, 5, 1),
        route_kind="home_to_work",
        status=status,
        actor_user_id=actor_user_id,
        earliest_boarding_time="06:30",
        arrival_at_work_time="08:00",
        openai_model="gpt-5-2025-08-07",
        route_provider="here",
        price_currency_code="SGD",
        price_rate_unit="day",
        baseline_snapshot_json=None,
        baseline_assignments_json=None,
        baseline_vehicle_state_json=None,
        planning_input_json=json.dumps({"service_date": "2026-05-01", "route_kind": "home_to_work"}),
        planning_input_hash="f" * 64,
        preflight_issues_json=None,
        error_code=None,
        error_message=None,
        created_at=timestamp,
        updated_at=timestamp,
        completed_at=None,
    )


def test_transport_ai_runs_migration_upgrades_head_on_sqlite(tmp_path):
    database_url = _build_database_url(tmp_path / "transport_ai_runs_head.db")

    _upgrade_database_to_head(database_url)

    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)
    index_names = {index["name"]: index for index in inspector.get_indexes("transport_ai_runs")}
    column_names = {column["name"] for column in inspector.get_columns("transport_ai_runs")}

    assert inspector.has_table("transport_ai_runs")
    assert {
        "run_key",
        "service_date",
        "route_kind",
        "status",
        "actor_user_id",
        "earliest_boarding_time",
        "arrival_at_work_time",
        "openai_model",
        "route_provider",
        "price_currency_code",
        "price_rate_unit",
        "baseline_snapshot_json",
        "baseline_assignments_json",
        "baseline_vehicle_state_json",
        "planning_input_json",
        "planning_input_hash",
        "preflight_issues_json",
        "error_code",
        "error_message",
        "created_at",
        "updated_at",
        "completed_at",
    }.issubset(column_names)
    assert index_names["ix_transport_ai_runs_run_key"]["unique"]
    assert index_names["ix_transport_ai_runs_run_key"]["column_names"] == ["run_key"]
    assert index_names["ix_transport_ai_runs_service_date_route_kind_created_at"]["column_names"] == [
        "service_date",
        "route_kind",
        "created_at",
    ]


def test_transport_ai_run_can_be_created_with_requested_status(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        transport_ai_run = _build_transport_ai_run(actor_user_id=admin_user.id)
        session.add(transport_ai_run)
        session.commit()

        persisted_run = session.get(TransportAIRun, transport_ai_run.id)

    engine.dispose()

    assert persisted_run is not None
    assert persisted_run.status == "requested"
    assert persisted_run.run_key == "run-requested-001"


def test_transport_ai_run_blocks_invalid_status(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        invalid_run = _build_transport_ai_run(
            actor_user_id=admin_user.id,
            status="invalid_status",
            run_key="run-invalid-status",
        )
        session.add(invalid_run)

        with pytest.raises(sa.exc.IntegrityError):
            session.flush()

        session.rollback()

    engine.dispose()


def test_transport_ai_run_can_be_fetched_by_run_key(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        transport_ai_run = _build_transport_ai_run(
            actor_user_id=admin_user.id,
            run_key="run-query-001",
        )
        session.add(transport_ai_run)
        session.commit()

        persisted_run = session.execute(
            select(TransportAIRun).where(TransportAIRun.run_key == "run-query-001")
        ).scalar_one()

    engine.dispose()

    assert persisted_run.id == transport_ai_run.id
    assert persisted_run.run_key == "run-query-001"
    assert persisted_run.actor_user_id == admin_user.id


def test_resolve_transport_ai_run_llm_snapshot_fields_prefers_single_project_snapshot():
    run = _build_transport_ai_run(actor_user_id=1, run_key="run-llm-snapshot-single")
    run.llm_provider = "openai"
    run.llm_model = "gpt-5-2025-08-07"
    run.llm_reasoning_effort = "high"
    run.planning_input_json = json.dumps(
        {
            "llm_runtime_projects": [
                {
                    "project_id": 41,
                    "project_name": "Projeto Snapshot",
                    "partition_keys": ["project:41:home_to_work"],
                    "provider": "deepseek",
                    "model_name": "deepseek-v4-pro",
                    "reasoning_effort": "high",
                }
            ]
        },
        ensure_ascii=True,
        sort_keys=True,
    )

    llm_fields = resolve_transport_ai_run_llm_snapshot_fields(run)

    assert llm_fields == {
        "llm_provider": "deepseek",
        "llm_model": "deepseek-v4-pro",
        "llm_reasoning_effort": "high",
        "openai_model": "deepseek-v4-pro",
    }


def test_resolve_transport_ai_run_llm_snapshot_fields_reports_multiple_for_conflicting_projects():
    run = _build_transport_ai_run(actor_user_id=1, run_key="run-llm-snapshot-multiple")
    run.llm_provider = "openai"
    run.llm_model = "gpt-5-2025-08-07"
    run.llm_reasoning_effort = "high"
    run.planning_input_json = json.dumps(
        {
            "llm_runtime_projects": [
                {
                    "project_id": 41,
                    "project_name": "Projeto A",
                    "partition_keys": ["project:41:home_to_work"],
                    "provider": "openai",
                    "model_name": "gpt-5-2025-08-07",
                    "reasoning_effort": "high",
                },
                {
                    "project_id": 42,
                    "project_name": "Projeto B",
                    "partition_keys": ["project:42:home_to_work"],
                    "provider": "deepseek",
                    "model_name": "deepseek-v4-pro",
                    "reasoning_effort": "high",
                },
            ]
        },
        ensure_ascii=True,
        sort_keys=True,
    )

    llm_fields = resolve_transport_ai_run_llm_snapshot_fields(run)

    assert llm_fields == {
        "llm_provider": "multiple",
        "llm_model": "multiple",
        "llm_reasoning_effort": "multiple",
        "openai_model": "multiple",
    }