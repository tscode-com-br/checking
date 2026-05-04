import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.core.config import settings
from sistema.app.models import AdminUser, TransportAIRun, TransportAISuggestion
from sistema.app.services.transport_ai_agent import TRANSPORT_AI_PROMPT_VERSION
from sistema.app.services.transport_ai_runs import (
    create_transport_ai_suggestion,
    get_latest_active_transport_ai_suggestion,
    get_latest_saved_transport_ai_suggestion,
    set_transport_ai_suggestion_status,
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


def _build_session_factory(tmp_path: Path) -> tuple[sessionmaker[Session], sa.Engine]:
    database_url = _build_database_url(tmp_path / "transport_ai_suggestions.db")
    _upgrade_database_to_head(database_url)
    engine = sa.create_engine(database_url)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False), engine


def _create_admin_user(session: Session) -> AdminUser:
    timestamp = datetime(2026, 4, 30, 10, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    admin_user = AdminUser(
        chave="AI02",
        nome_completo="Transport AI Suggestion Admin",
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


def _create_transport_ai_run(session: Session, *, actor_user_id: int) -> TransportAIRun:
    timestamp = datetime(2026, 4, 30, 10, 5, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    transport_ai_run = TransportAIRun(
        run_key="run-suggestions-001",
        service_date=date(2026, 5, 2),
        route_kind="home_to_work",
        status="proposed",
        actor_user_id=actor_user_id,
        earliest_boarding_time="06:50",
        arrival_at_work_time="07:45",
        openai_model="gpt-5-2025-08-07",
        route_provider="mapbox",
        price_currency_code="SGD",
        price_rate_unit="day",
        baseline_snapshot_json=json.dumps({"snapshot_key": "baseline-001"}),
        baseline_assignments_json=json.dumps([]),
        baseline_vehicle_state_json=json.dumps([]),
        planning_input_json=json.dumps({"service_date": "2026-05-02", "route_kind": "home_to_work"}),
        planning_input_hash="a" * 64,
        preflight_issues_json=json.dumps([]),
        error_code=None,
        error_message=None,
        created_at=timestamp,
        updated_at=timestamp,
        completed_at=None,
    )
    session.add(transport_ai_run)
    session.flush()
    return transport_ai_run


def _build_suggestion_payload(suggestion_key: str) -> dict[str, str | None]:
    return {
        "suggestion_key": suggestion_key,
        "proposal_key": f"proposal:{suggestion_key}",
        "agent_plan_json": json.dumps({"plan_key": suggestion_key, "status": "shown"}),
        "transport_proposal_json": json.dumps({"proposal_key": f"proposal:{suggestion_key}"}),
        "vehicle_actions_json": json.dumps([{"action_key": f"vehicle:{suggestion_key}"}]),
        "assignment_actions_json": json.dumps([{"request_id": 1, "vehicle_ref": "existing:1"}]),
        "route_itineraries_json": json.dumps([{"vehicle_ref": "existing:1", "stops": []}]),
        "change_summary_json": json.dumps({"vehicle_changes": 1}),
        "cost_summary_json": json.dumps({"currency": "SGD", "total_cost": 120.0}),
        "validation_issues_json": json.dumps([]),
        "raw_model_response_json": json.dumps({"raw": suggestion_key}),
        "prompt_version": TRANSPORT_AI_PROMPT_VERSION,
    }


def test_transport_ai_suggestions_migration_upgrades_head_on_sqlite(tmp_path):
    database_url = _build_database_url(tmp_path / "transport_ai_suggestions_head.db")

    _upgrade_database_to_head(database_url)

    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)
    index_names = {index["name"]: index for index in inspector.get_indexes("transport_ai_suggestions")}
    column_names = {column["name"] for column in inspector.get_columns("transport_ai_suggestions")}
    engine.dispose()

    assert inspector.has_table("transport_ai_suggestions")
    assert {
        "suggestion_key",
        "run_id",
        "service_date",
        "route_kind",
        "proposal_key",
        "status",
        "agent_plan_json",
        "transport_proposal_json",
        "vehicle_actions_json",
        "assignment_actions_json",
        "route_itineraries_json",
        "change_summary_json",
        "cost_summary_json",
        "validation_issues_json",
        "raw_model_response_json",
        "prompt_version",
        "created_at",
        "updated_at",
        "saved_at",
        "applied_at",
        "discarded_at",
    }.issubset(column_names)
    assert index_names["ix_transport_ai_suggestions_suggestion_key"]["unique"]
    assert index_names["ix_transport_ai_suggestions_suggestion_key"]["column_names"] == ["suggestion_key"]
    assert index_names["ix_transport_ai_suggestions_service_date_route_kind_status_updated_at"]["column_names"] == [
        "service_date",
        "route_kind",
        "status",
        "updated_at",
    ]


def test_transport_ai_suggestion_can_be_created_with_shown_status(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id)
        suggestion = create_transport_ai_suggestion(
            session,
            run=run,
            status="shown",
            created_at=datetime(2026, 4, 30, 10, 10, 0, tzinfo=ZoneInfo("Asia/Singapore")),
            **_build_suggestion_payload("suggestion-shown-001"),
        )
        session.commit()

        persisted_suggestion = session.get(TransportAISuggestion, suggestion.id)

    engine.dispose()

    assert persisted_suggestion is not None
    assert persisted_suggestion.status == "shown"
    assert persisted_suggestion.run_id == run.id
    assert persisted_suggestion.service_date == run.service_date
    assert persisted_suggestion.route_kind == run.route_kind
    assert persisted_suggestion.prompt_version == TRANSPORT_AI_PROMPT_VERSION


def test_transport_ai_suggestion_can_be_marked_saved_and_fetched_by_date_and_route(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id)
        suggestion = create_transport_ai_suggestion(
            session,
            run=run,
            status="shown",
            created_at=datetime(2026, 4, 30, 10, 12, 0, tzinfo=ZoneInfo("Asia/Singapore")),
            **_build_suggestion_payload("suggestion-saved-001"),
        )
        saved_at = datetime(2026, 4, 30, 10, 15, 0, tzinfo=ZoneInfo("Asia/Singapore"))
        set_transport_ai_suggestion_status(
            session,
            suggestion=suggestion,
            status="saved",
            changed_at=saved_at,
        )
        session.commit()

        latest_saved = get_latest_saved_transport_ai_suggestion(
            session,
            service_date=run.service_date,
            route_kind=run.route_kind,
        )

    engine.dispose()

    assert latest_saved is not None
    assert latest_saved.id == suggestion.id
    assert latest_saved.status == "saved"
    assert latest_saved.saved_at == saved_at


def test_transport_ai_latest_active_suggestion_ignores_applied_and_discarded_rows(tmp_path):
    session_factory, engine = _build_session_factory(tmp_path)

    with session_factory() as session:
        admin_user = _create_admin_user(session)
        run = _create_transport_ai_run(session, actor_user_id=admin_user.id)

        saved_suggestion = create_transport_ai_suggestion(
            session,
            run=run,
            status="shown",
            created_at=datetime(2026, 4, 30, 10, 20, 0, tzinfo=ZoneInfo("Asia/Singapore")),
            **_build_suggestion_payload("suggestion-active-saved"),
        )
        set_transport_ai_suggestion_status(
            session,
            suggestion=saved_suggestion,
            status="saved",
            changed_at=datetime(2026, 4, 30, 10, 21, 0, tzinfo=ZoneInfo("Asia/Singapore")),
        )

        applied_suggestion = create_transport_ai_suggestion(
            session,
            run=run,
            status="shown",
            created_at=datetime(2026, 4, 30, 10, 22, 0, tzinfo=ZoneInfo("Asia/Singapore")),
            **_build_suggestion_payload("suggestion-applied"),
        )
        set_transport_ai_suggestion_status(
            session,
            suggestion=applied_suggestion,
            status="applied",
            changed_at=datetime(2026, 4, 30, 10, 23, 0, tzinfo=ZoneInfo("Asia/Singapore")),
        )

        discarded_suggestion = create_transport_ai_suggestion(
            session,
            run=run,
            status="shown",
            created_at=datetime(2026, 4, 30, 10, 24, 0, tzinfo=ZoneInfo("Asia/Singapore")),
            **_build_suggestion_payload("suggestion-discarded"),
        )
        set_transport_ai_suggestion_status(
            session,
            suggestion=discarded_suggestion,
            status="discarded",
            changed_at=datetime(2026, 4, 30, 10, 25, 0, tzinfo=ZoneInfo("Asia/Singapore")),
        )
        session.commit()

        latest_active = get_latest_active_transport_ai_suggestion(
            session,
            service_date=run.service_date,
            route_kind=run.route_kind,
        )

    engine.dispose()

    assert latest_active is not None
    assert latest_active.id == saved_suggestion.id
    assert latest_active.status == "saved"