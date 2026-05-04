import os
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path

from cryptography.fernet import Fernet


def _build_transport_ai_router_env(tmp_path: Path) -> dict[str, str]:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(repo_root),
            "APP_ENV": "development",
            "DATABASE_URL": f"sqlite+pysqlite:///{(tmp_path / 'transport_ai_router.db').as_posix()}",
            "FORMS_URL": "https://example.com/form",
            "DEVICE_SHARED_KEY": "device-test-key",
            "MOBILE_APP_SHARED_KEY": "mobile-test-key",
            "PROVIDER_SHARED_KEY": "provider-test-key",
            "ADMIN_SESSION_SECRET": "test-admin-session-secret",
            "BOOTSTRAP_ADMIN_KEY": "HR70",
            "BOOTSTRAP_ADMIN_NAME": "Transport AI Router Admin",
            "BOOTSTRAP_ADMIN_PASSWORD": "eAcacdLe2",
            "FORMS_QUEUE_ENABLED": "false",
            "TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8"),
            "TRANSPORT_EXPORTS_DIR": str(tmp_path / "transport_exports"),
            "TRANSPORT_AI_ENABLED": "false",
        }
    )
    env.pop("OPENAI_API_KEY", None)
    env.pop("MAPBOX_ACCESS_TOKEN", None)
    return env


def _run_transport_ai_router_script(tmp_path: Path, *, script: str) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = _build_transport_ai_router_env(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def _build_transport_ai_run_status_script(
    *,
    run_status: str,
    include_suggestion: bool,
    run_key: str,
    error_message: str | None,
    assertions: str,
) -> str:
    suggestion_block = ""
    if include_suggestion:
        suggestion_block = textwrap.dedent(
            """
            plan = TransportAgentPlan(
                plan_key="plan-polling-001",
                service_date=date.fromisoformat("2026-06-10"),
                route_kind="home_to_work",
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                objective_summary="Minimize total transport cost.",
                vehicle_actions=[],
                passenger_allocations=[],
                route_itineraries=[],
                cost_summary=TransportAgentCostSummary(
                    price_currency_code="SGD",
                    price_rate_unit="day",
                    current_total_estimated_cost=15,
                    suggested_total_estimated_cost=15,
                    estimated_cost_delta=0,
                    current_vehicle_count=1,
                    suggested_vehicle_count=1,
                ),
                change_summary=TransportAgentChangeSummary(
                    total_vehicle_actions=0,
                    keep_count=0,
                    create_count=0,
                    update_count=0,
                    remove_from_day_count=0,
                    by_vehicle_type=[],
                ),
                validation_issues=[
                    TransportProposalValidationIssue(
                        code="manual_review_recommended",
                        message="Review the generated route before applying it.",
                        blocking=False,
                    )
                ],
            )
            create_transport_ai_suggestion_from_plan(
                session,
                run=run,
                plan=plan,
                prompt_version="transport_ai_route_planner_v1",
                raw_model_response_json=None,
                suggestion_key="transport-ai-suggestion:polling-001",
                proposal_key="transport-ai-proposal:polling-001",
                status="shown",
                created_at=_fixture_timestamp(),
            )
            """
        ).strip()

    indented_suggestion_block = textwrap.indent(suggestion_block, "                ") if suggestion_block else ""
    indented_assertions = textwrap.indent(assertions, "            ")
    completed_at_expression = (
        "_fixture_timestamp()"
        if run_status in {"proposed", "failed", "saved", "applied", "cancelled"}
        else "None"
    )

    return textwrap.dedent(
        f"""
        from datetime import date, datetime
        from zoneinfo import ZoneInfo

        from fastapi.testclient import TestClient

        from sistema.app.main import app
        from sistema.app.database import Base, SessionLocal, engine
        from sistema.app.models import AdminUser, TransportAIRun
        from sistema.app.schemas import (
            TransportAgentChangeSummary,
            TransportAgentCostSummary,
            TransportAgentPlan,
            TransportProposalValidationIssue,
        )
        from sistema.app.services.transport_ai_runs import create_transport_ai_suggestion_from_plan


        def _fixture_timestamp():
            return datetime(2026, 5, 5, 9, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))


        def _seed_run():
            with SessionLocal() as session:
                admin_user = AdminUser(
                    chave="A810",
                    nome_completo="Transport AI Polling Admin",
                    password_hash=None,
                    requires_password_reset=False,
                    approved_by_admin_id=None,
                    approved_at=None,
                    password_reset_requested_at=None,
                    created_at=_fixture_timestamp(),
                    updated_at=_fixture_timestamp(),
                )
                session.add(admin_user)
                session.flush()

                run = TransportAIRun(
                    run_key={run_key!r},
                    service_date=date.fromisoformat("2026-06-10"),
                    route_kind="home_to_work",
                    status={run_status!r},
                    actor_user_id=admin_user.id,
                    earliest_boarding_time="06:50",
                    arrival_at_work_time="07:45",
                    openai_model="gpt-5-2025-08-07",
                    route_provider="fake",
                    price_currency_code="SGD",
                    price_rate_unit="day",
                    baseline_snapshot_json='{{}}',
                    baseline_assignments_json='{{}}',
                    baseline_vehicle_state_json='{{}}',
                    planning_input_json='{{}}',
                    planning_input_hash="0" * 64,
                    preflight_issues_json='[{{"code":"planning_warning","message":"Pending route review.","blocking":false,"setting_name":"transport_ai_polling"}}]',
                    error_code={"synthetic_polling_failure" if error_message else None!r},
                    error_message={error_message!r},
                    created_at=_fixture_timestamp(),
                    updated_at=_fixture_timestamp(),
                    completed_at={completed_at_expression},
                )
                session.add(run)
                session.flush()

{indented_suggestion_block}

                session.commit()


        Base.metadata.create_all(bind=engine)
        _seed_run()

        with TestClient(app) as client:
            login = client.post(
                "/api/transport/auth/verify",
                json={{"chave": "HR70", "senha": "eAcacdLe2"}},
            )
            assert login.status_code == 200, login.text
            assert login.json()["authenticated"] is True

            response = client.get("/api/transport/ai/route-calculations/" + {run_key!r})

{indented_assertions}

        print("transport-ai-run-status-ok")
        """
            ).lstrip()


def test_transport_ai_router_requires_transport_session_and_exposes_openapi(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    env = _build_transport_ai_router_env(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            textwrap.dedent(
                """
                from fastapi.testclient import TestClient
                from sistema.app.main import app

                with TestClient(app) as client:
                    unauthorized = client.get('/api/transport/ai/preflight')
                    assert unauthorized.status_code == 401, unauthorized.text
                    assert unauthorized.json()['detail'] == 'Sessao de transporte invalida ou expirada'

                    unauthorized_settings = client.get('/api/transport/ai/settings')
                    assert unauthorized_settings.status_code == 401, unauthorized_settings.text
                    assert unauthorized_settings.json()['detail'] == 'Sessao de transporte invalida ou expirada'

                    login = client.post(
                        '/api/transport/auth/verify',
                        json={'chave': 'HR70', 'senha': 'eAcacdLe2'},
                    )
                    assert login.status_code == 200, login.text
                    assert login.json()['authenticated'] is True

                    preflight = client.get('/api/transport/ai/preflight')
                    assert preflight.status_code == 200, preflight.text
                    payload = preflight.json()
                    assert payload['ok'] is False
                    assert [issue['code'] for issue in payload['issues']] == ['transport_ai_disabled']

                    settings_get = client.get('/api/transport/ai/settings')
                    assert settings_get.status_code == 200, settings_get.text
                    settings_payload = settings_get.json()
                    assert settings_payload == {
                        'provider': 'openai',
                        'resolved_model': 'gpt-5.4-2026-03-05',
                        'reasoning_effort': 'high',
                        'has_api_key': False,
                        'api_key_hint': None,
                    }

                    invalid_settings_update = client.put(
                        '/api/transport/ai/settings',
                        json={'provider': 'openai', 'api_key': None},
                    )
                    assert invalid_settings_update.status_code == 409, invalid_settings_update.text
                    assert invalid_settings_update.json()['detail'] == 'Transport AI API key is required when creating LLM settings.'

                    missing_run = client.get('/api/transport/ai/route-calculations/run-missing-001')
                    assert missing_run.status_code == 404, missing_run.text
                    assert missing_run.json()['detail'] == 'Transport AI run not found.'

                    openapi = client.get('/openapi.json')
                    assert openapi.status_code == 200, openapi.text
                    specification = openapi.json()
                    assert '/api/transport/ai/preflight' in specification['paths']
                    assert '/api/transport/ai/settings' in specification['paths']
                    assert '/api/transport/ai/runs' in specification['paths']
                    assert '/api/transport/ai/route-calculations/{run_key}' in specification['paths']
                    schemas = specification['components']['schemas']
                    assert 'TransportAIPreflightCheckResult' in schemas
                    assert 'TransportAIPreflightIssue' in schemas
                    assert 'TransportAIRunDiagnosticsEntry' in schemas
                    assert 'TransportAIRunDiagnosticsResponse' in schemas
                    assert 'TransportAISettingsResponse' in schemas
                    assert 'TransportAISettingsUpdateRequest' in schemas
                    assert 'TransportAgentRunStatusResponse' in schemas

                print('transport-ai-router-ok')
                """
            ),
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "transport-ai-router-ok" in result.stdout


def test_transport_ai_run_status_returns_running_without_suggestion(tmp_path):
    assertions = textwrap.dedent(
        """
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["ok"] is True
        assert payload["status"] == "running"
        assert payload["suggestion_ready"] is False
        assert payload["suggestion_key"] is None
        assert payload["suggestion"] is None
        assert payload["can_save"] is False
        assert payload["can_apply"] is False
        assert payload["can_cancel_restore"] is False
        assert payload["message"] == "Transport AI route calculation is running."
        assert payload["issues"][0]["code"] == "planning_warning"
        assert payload["issues"][0]["source"] == "run_preflight"
        """
    ).strip()
    script = _build_transport_ai_run_status_script(
        run_status="running",
        include_suggestion=False,
        run_key="transport-ai-run:polling-running-001",
        error_message=None,
        assertions=assertions,
    )
    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_settings_endpoint_saves_masked_configuration_and_audits_safely(tmp_path):
    script = textwrap.dedent(
        """
        import json

        from fastapi.testclient import TestClient
        from sqlalchemy import select

        from sistema.app.main import app
        from sistema.app.database import Base, SessionLocal, engine
        from sistema.app.models import CheckEvent, TransportAILlmSettings


        Base.metadata.create_all(bind=engine)

        with TestClient(app) as client:
            login = client.post(
                '/api/transport/auth/verify',
                json={'chave': 'HR70', 'senha': 'eAcacdLe2'},
            )
            assert login.status_code == 200, login.text
            assert login.json()['authenticated'] is True

            created = client.put(
                '/api/transport/ai/settings',
                json={'provider': 'openai', 'api_key': 'sk-super-secret-1234'},
            )
            assert created.status_code == 200, created.text
            assert 'sk-super-secret-1234' not in created.text
            assert created.json() == {
                'provider': 'openai',
                'resolved_model': 'gpt-5.4-2026-03-05',
                'reasoning_effort': 'high',
                'has_api_key': True,
                'api_key_hint': '***1234',
            }

            fetched = client.get('/api/transport/ai/settings')
            assert fetched.status_code == 200, fetched.text
            assert 'sk-super-secret-1234' not in fetched.text
            assert fetched.json() == created.json()

            invalid_provider_change = client.put(
                '/api/transport/ai/settings',
                json={'provider': 'deepseek', 'api_key': None},
            )
            assert invalid_provider_change.status_code == 409, invalid_provider_change.text
            assert 'sk-super-secret-1234' not in invalid_provider_change.text
            assert invalid_provider_change.json()['detail'] == 'Transport AI API key is required when changing the LLM provider.'

            with SessionLocal() as session:
                persisted_settings = session.get(TransportAILlmSettings, 1)
                assert persisted_settings is not None
                assert persisted_settings.provider == 'openai'
                assert persisted_settings.model_name == 'gpt-5.4-2026-03-05'
                assert persisted_settings.reasoning_effort == 'high'
                assert persisted_settings.api_key_last4 == '1234'
                assert persisted_settings.api_key_ciphertext != 'sk-super-secret-1234'
                assert persisted_settings.api_key_ciphertext not in created.text
                assert persisted_settings.api_key_ciphertext not in fetched.text
                assert persisted_settings.api_key_ciphertext not in invalid_provider_change.text

                audit_event = session.execute(
                    select(CheckEvent)
                    .where(
                        CheckEvent.source == 'transport_ai',
                        CheckEvent.action == 'settings_update',
                        CheckEvent.status == 'success',
                    )
                    .order_by(CheckEvent.id.desc())
                    .limit(1)
                ).scalar_one_or_none()

                assert audit_event is not None
                assert audit_event.status == 'success'
                assert audit_event.request_path == '/api/transport/ai/settings'
                assert audit_event.http_status == 200
                assert 'sk-super-secret-1234' not in audit_event.message
                assert 'sk-super-secret-1234' not in (audit_event.details or '')
                assert '***1234' in audit_event.message

                audit_details = json.loads(audit_event.details)
                assert audit_details['provider'] == 'openai'
                assert audit_details['resolved_model'] == 'gpt-5.4-2026-03-05'
                assert audit_details['reasoning_effort'] == 'high'
                assert bool(audit_details['has_api_key']) is True
                assert audit_details['api_key_hint'] == '***1234'
                assert audit_details['previous_provider'] is None
                assert bool(audit_details['provider_changed']) is True
                assert audit_details['request_path'] == '/api/transport/ai/settings'

        print('transport-ai-settings-endpoints-ok')
        """
    ).strip()

    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_settings_endpoint_returns_controlled_error_when_saved_provider_is_no_longer_supported(tmp_path):
    script = textwrap.dedent(
        """
        from fastapi.testclient import TestClient

        from sistema.app.main import app
        from sistema.app.database import Base, engine
        from sistema.app.services import transport_ai_llm_settings as transport_ai_llm_settings_module


        Base.metadata.create_all(bind=engine)

        with TestClient(app) as client:
            login = client.post(
                '/api/transport/auth/verify',
                json={'chave': 'HR70', 'senha': 'eAcacdLe2'},
            )
            assert login.status_code == 200, login.text
            assert login.json()['authenticated'] is True

            created = client.put(
                '/api/transport/ai/settings',
                json={'provider': 'deepseek', 'api_key': 'deepseek-secret-5678'},
            )
            assert created.status_code == 200, created.text

            removed_defaults = transport_ai_llm_settings_module.TRANSPORT_AI_LLM_PROVIDER_DEFAULTS.pop('deepseek', None)
            assert removed_defaults is not None
            try:
                invalid = client.get('/api/transport/ai/settings')
                assert invalid.status_code == 409, invalid.text
                assert invalid.json()['detail'] == (
                    'The configured Transport AI LLM provider is no longer supported. '
                    'Select OpenAI or DeepSeek and save the AI settings again.'
                )

                repaired = client.put(
                    '/api/transport/ai/settings',
                    json={'provider': 'openai', 'api_key': 'sk-openai-1234'},
                )
                assert repaired.status_code == 200, repaired.text
                assert repaired.json() == {
                    'provider': 'openai',
                    'resolved_model': 'gpt-5.4-2026-03-05',
                    'reasoning_effort': 'high',
                    'has_api_key': True,
                    'api_key_hint': '***1234',
                }

                fetched = client.get('/api/transport/ai/settings')
                assert fetched.status_code == 200, fetched.text
                assert fetched.json() == repaired.json()
            finally:
                transport_ai_llm_settings_module.TRANSPORT_AI_LLM_PROVIDER_DEFAULTS['deepseek'] = removed_defaults

        print('transport-ai-settings-unsupported-provider-ok')
        """
    ).strip()

    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_latest_suggestion_keeps_run_llm_snapshot_after_provider_changes(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    env = _build_transport_ai_router_env(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            textwrap.dedent(
                """
                from datetime import date, datetime
                from zoneinfo import ZoneInfo

                from fastapi.testclient import TestClient

                from sistema.app.main import app
                from sistema.app.database import Base, SessionLocal, engine
                from sistema.app.models import AdminUser, TransportAIRun
                from sistema.app.schemas import (
                    TransportAgentChangeSummary,
                    TransportAgentCostSummary,
                    TransportAgentPlan,
                    TransportProposalValidationIssue,
                )
                from sistema.app.services.transport_ai_runs import create_transport_ai_suggestion_from_plan


                def _fixture_timestamp(hour: int = 9, minute: int = 0):
                    return datetime(2026, 6, 12, hour, minute, 0, tzinfo=ZoneInfo("Asia/Singapore"))


                Base.metadata.create_all(bind=engine)

                with SessionLocal() as session:
                    admin_user = AdminUser(
                        chave="A812",
                        nome_completo="Transport AI Saved Suggestion Admin",
                        password_hash=None,
                        requires_password_reset=False,
                        approved_by_admin_id=None,
                        approved_at=None,
                        password_reset_requested_at=None,
                        created_at=_fixture_timestamp(8, 0),
                        updated_at=_fixture_timestamp(8, 0),
                    )
                    session.add(admin_user)
                    session.flush()

                    run = TransportAIRun(
                        run_key="transport-ai-run:latest-llm-snapshot-001",
                        service_date=date.fromisoformat("2026-06-12"),
                        route_kind="home_to_work",
                        status="saved",
                        actor_user_id=admin_user.id,
                        earliest_boarding_time="06:50",
                        arrival_at_work_time="07:45",
                        llm_provider="deepseek",
                        llm_model="deepseek-v4-pro",
                        llm_reasoning_effort="high",
                        openai_model="deepseek-v4-pro",
                        route_provider="fake",
                        price_currency_code="SGD",
                        price_rate_unit="day",
                        baseline_snapshot_json='{}',
                        baseline_assignments_json='{}',
                        baseline_vehicle_state_json='{}',
                        planning_input_json='{}',
                        planning_input_hash="3" * 64,
                        preflight_issues_json='[]',
                        error_code=None,
                        error_message=None,
                        created_at=_fixture_timestamp(9, 0),
                        updated_at=_fixture_timestamp(9, 8),
                        completed_at=_fixture_timestamp(9, 8),
                    )
                    session.add(run)
                    session.flush()

                    plan = TransportAgentPlan(
                        plan_key="plan-latest-llm-snapshot-001",
                        service_date=date.fromisoformat("2026-06-12"),
                        route_kind="home_to_work",
                        earliest_boarding_time="06:50",
                        arrival_at_work_time="07:45",
                        objective_summary="Keep the saved suggestion tied to the original LLM snapshot.",
                        vehicle_actions=[],
                        passenger_allocations=[],
                        route_itineraries=[],
                        cost_summary=TransportAgentCostSummary(
                            price_currency_code="SGD",
                            price_rate_unit="day",
                            current_total_estimated_cost=15,
                            suggested_total_estimated_cost=15,
                            estimated_cost_delta=0,
                            current_vehicle_count=1,
                            suggested_vehicle_count=1,
                        ),
                        change_summary=TransportAgentChangeSummary(
                            total_vehicle_actions=0,
                            keep_count=0,
                            create_count=0,
                            update_count=0,
                            remove_from_day_count=0,
                            by_vehicle_type=[],
                        ),
                        validation_issues=[
                            TransportProposalValidationIssue(
                                code="manual_review_recommended",
                                message="Review the generated route before applying it.",
                                blocking=False,
                            )
                        ],
                    )
                    create_transport_ai_suggestion_from_plan(
                        session,
                        run=run,
                        plan=plan,
                        prompt_version="transport_ai_route_planner_v1",
                        raw_model_response_json=None,
                        suggestion_key="transport-ai-suggestion:latest-llm-snapshot-001",
                        proposal_key="transport-ai-proposal:latest-llm-snapshot-001",
                        status="saved",
                        created_at=_fixture_timestamp(9, 7),
                    )
                    session.commit()

                with TestClient(app) as client:
                    login = client.post(
                        '/api/transport/auth/verify',
                        json={'chave': 'HR70', 'senha': 'eAcacdLe2'},
                    )
                    assert login.status_code == 200, login.text
                    assert login.json()['authenticated'] is True

                    current_settings = client.put(
                        '/api/transport/ai/settings',
                        json={'provider': 'openai', 'api_key': 'sk-openai-1234'},
                    )
                    assert current_settings.status_code == 200, current_settings.text
                    assert current_settings.json()['provider'] == 'openai'

                    latest = client.get(
                        '/api/transport/ai/suggestions/latest',
                        params={'service_date': '2026-06-12', 'route_kind': 'home_to_work'},
                    )
                    assert latest.status_code == 200, latest.text
                    latest_payload = latest.json()
                    assert latest_payload['status'] == 'saved'
                    assert latest_payload['suggestion']['status'] == 'saved'
                    assert latest_payload['llm_provider'] == 'deepseek'
                    assert latest_payload['llm_model'] == 'deepseek-v4-pro'
                    assert latest_payload['llm_reasoning_effort'] == 'high'
                    assert latest_payload['llm_provider'] != current_settings.json()['provider']

                    saved = client.post('/api/transport/ai/suggestions/transport-ai-suggestion:latest-llm-snapshot-001/save')
                    assert saved.status_code == 200, saved.text
                    saved_payload = saved.json()
                    assert saved_payload['status'] == 'saved'
                    assert saved_payload['llm_provider'] == 'deepseek'
                    assert saved_payload['llm_model'] == 'deepseek-v4-pro'
                    assert saved_payload['llm_reasoning_effort'] == 'high'

                print('transport-ai-latest-suggestion-llm-snapshot-ok')
                """
            ),
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "transport-ai-latest-suggestion-llm-snapshot-ok" in result.stdout


def test_transport_ai_settings_endpoint_sanitizes_failed_update_details_and_audit(tmp_path):
    script = textwrap.dedent(
        """
        import json

        from fastapi.testclient import TestClient
        from sqlalchemy import select

        from sistema.app.main import app
        from sistema.app.database import Base, SessionLocal, engine
        from sistema.app.models import CheckEvent
        from sistema.app.routers import transport_ai as transport_ai_router_module
        from sistema.app.services.transport_ai_llm_settings import TransportAILlmSettingsValidationError


        Base.metadata.create_all(bind=engine)


        def _boom(*args, **kwargs):
            raise TransportAILlmSettingsValidationError(
                'Synthetic settings failure leaked deepseek-secret-5678 and Bearer top-secret.'
            )


        original_upsert = transport_ai_router_module.upsert_transport_ai_llm_settings
        transport_ai_router_module.upsert_transport_ai_llm_settings = _boom
        try:
            with TestClient(app) as client:
                login = client.post(
                    '/api/transport/auth/verify',
                    json={'chave': 'HR70', 'senha': 'eAcacdLe2'},
                )
                assert login.status_code == 200, login.text
                assert login.json()['authenticated'] is True

                failed = client.put(
                    '/api/transport/ai/settings',
                    json={'provider': 'deepseek', 'api_key': 'deepseek-secret-5678'},
                )
                assert failed.status_code == 409, failed.text
                assert 'deepseek-secret-5678' not in failed.text
                assert 'Bearer top-secret' not in failed.text
                assert '[REDACTED]' in failed.json()['detail']

                with SessionLocal() as session:
                    audit_event = session.execute(
                        select(CheckEvent)
                        .where(
                            CheckEvent.source == 'transport_ai',
                            CheckEvent.action == 'settings_update',
                            CheckEvent.status == 'failed',
                        )
                        .order_by(CheckEvent.id.desc())
                        .limit(1)
                    ).scalar_one_or_none()

                    assert audit_event is not None
                    assert audit_event.request_path == '/api/transport/ai/settings'
                    assert audit_event.http_status == 409
                    assert 'deepseek-secret-5678' not in audit_event.message
                    assert 'deepseek-secret-5678' not in (audit_event.details or '')
                    assert 'Bearer top-secret' not in audit_event.message
                    assert 'Bearer top-secret' not in (audit_event.details or '')
                    assert '***5678' in audit_event.message

                    audit_details = json.loads(audit_event.details)
                    assert audit_details['requested_provider'] == 'deepseek'
                    assert bool(audit_details['submitted_has_api_key']) is True
                    assert audit_details['submitted_api_key_hint'] == '***5678'
                    assert audit_details['failure_detail'] == failed.json()['detail']
                    assert audit_details['request_path'] == '/api/transport/ai/settings'
        finally:
            transport_ai_router_module.upsert_transport_ai_llm_settings = original_upsert

        print('transport-ai-settings-failure-sanitized-ok')
        """
    ).strip()

    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_run_status_returns_proposed_suggestion(tmp_path):
    assertions = textwrap.dedent(
        """
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["ok"] is True
        assert payload["status"] == "proposed"
        assert payload["suggestion_ready"] is True
        assert payload["suggestion_key"] == "transport-ai-suggestion:polling-001"
        assert payload["can_save"] is True
        assert payload["can_apply"] is True
        assert payload["can_cancel_restore"] is True
        assert payload["message"] == "Transport AI suggestion is ready for review."
        assert payload["suggestion"]["status"] == "shown"
        assert payload["suggestion"]["prompt_version"] == "transport_ai_route_planner_v1"
        assert payload["suggestion"]["plan"]["plan_key"] == "plan-polling-001"
        issue_codes = {issue["code"] for issue in payload["issues"]}
        assert "planning_warning" in issue_codes
        assert "manual_review_recommended" in issue_codes
        suggestion_issue_sources = {
            issue["source"]
            for issue in payload["issues"]
            if issue["code"] == "manual_review_recommended"
        }
        assert suggestion_issue_sources == {"suggestion_validation"}
        """
    ).strip()
    script = _build_transport_ai_run_status_script(
        run_status="proposed",
        include_suggestion=True,
        run_key="transport-ai-run:polling-proposed-001",
        error_message=None,
        assertions=assertions,
    )
    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_run_status_returns_failed_error_message(tmp_path):
    assertions = textwrap.dedent(
        """
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["ok"] is False
        assert payload["status"] == "failed"
        assert payload["suggestion_ready"] is False
        assert payload["suggestion"] is None
        assert payload["can_save"] is False
        assert payload["can_apply"] is False
        assert payload["can_cancel_restore"] is False
        assert payload["message"] == "Synthetic polling failure after reset."
        assert payload["issues"][0]["code"] == "planning_warning"
        """
    ).strip()
    script = _build_transport_ai_run_status_script(
        run_status="failed",
        include_suggestion=False,
        run_key="transport-ai-run:polling-failed-001",
        error_message="Synthetic polling failure after reset.",
        assertions=assertions,
    )
    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_runs_endpoint_lists_recent_runs_filters_and_redacts_sensitive_fields(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    env = _build_transport_ai_router_env(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            textwrap.dedent(
                """
                import json
                from datetime import date, datetime
                from zoneinfo import ZoneInfo

                from fastapi.testclient import TestClient

                from sistema.app.main import app
                from sistema.app.database import Base, SessionLocal, engine
                from sistema.app.models import AdminUser, TransportAIRun, TransportAISuggestion


                def _fixture_timestamp(year, month, day, hour, minute=0):
                    return datetime(year, month, day, hour, minute, 0, tzinfo=ZoneInfo("Asia/Singapore"))


                def _seed_runs():
                    with SessionLocal() as session:
                        admin_user = AdminUser(
                            chave="A811",
                            nome_completo="Transport AI Diagnostics Admin",
                            password_hash=None,
                            requires_password_reset=False,
                            approved_by_admin_id=None,
                            approved_at=None,
                            password_reset_requested_at=None,
                            created_at=_fixture_timestamp(2026, 6, 9, 8),
                            updated_at=_fixture_timestamp(2026, 6, 9, 8),
                        )
                        session.add(admin_user)
                        session.flush()

                        failed_run = TransportAIRun(
                            run_key="transport-ai-run:diagnostic-failed-001",
                            service_date=date.fromisoformat("2026-06-10"),
                            route_kind="home_to_work",
                            status="failed",
                            actor_user_id=admin_user.id,
                            earliest_boarding_time="06:50",
                            arrival_at_work_time="07:45",
                            llm_provider=None,
                            llm_model=None,
                            llm_reasoning_effort=None,
                            openai_model="gpt-5-2025-08-07",
                            route_provider="fake",
                            price_currency_code="SGD",
                            price_rate_unit="day",
                            baseline_snapshot_json='{}',
                            baseline_assignments_json='{}',
                            baseline_vehicle_state_json='{}',
                            planning_input_json='{}',
                            planning_input_hash="1" * 64,
                            preflight_issues_json='[{"code":"openai_retry_exhausted","message":"Retries exhausted.","blocking":true}]',
                            error_code="transport_ai_provider_failed",
                            error_message="Provider failure leaked sk-test-openai-token and Bearer top-secret.",
                            created_at=_fixture_timestamp(2026, 6, 10, 8, 10),
                            updated_at=_fixture_timestamp(2026, 6, 10, 8, 12),
                            completed_at=_fixture_timestamp(2026, 6, 10, 8, 12),
                        )
                        session.add(failed_run)

                        applied_run = TransportAIRun(
                            run_key="transport-ai-run:diagnostic-applied-001",
                            service_date=date.fromisoformat("2026-06-11"),
                            route_kind="home_to_work",
                            status="applied",
                            actor_user_id=admin_user.id,
                            earliest_boarding_time="06:50",
                            arrival_at_work_time="07:45",
                            llm_provider="deepseek",
                            llm_model="deepseek-v4-pro",
                            llm_reasoning_effort="high",
                            openai_model="deepseek-v4-pro",
                            route_provider="fake",
                            price_currency_code="SGD",
                            price_rate_unit="day",
                            baseline_snapshot_json='{}',
                            baseline_assignments_json='{}',
                            baseline_vehicle_state_json='{}',
                            planning_input_json='{}',
                            planning_input_hash="2" * 64,
                            preflight_issues_json='[]',
                            error_code=None,
                            error_message=None,
                            created_at=_fixture_timestamp(2026, 6, 11, 9, 5),
                            updated_at=_fixture_timestamp(2026, 6, 11, 9, 9),
                            completed_at=_fixture_timestamp(2026, 6, 11, 9, 9),
                        )
                        session.add(applied_run)
                        session.flush()

                        suggestion = TransportAISuggestion(
                            suggestion_key="transport-ai-suggestion:diagnostic-applied-001",
                            run_id=applied_run.id,
                            service_date=applied_run.service_date,
                            route_kind=applied_run.route_kind,
                            proposal_key="transport-ai-proposal:diagnostic-applied-001",
                            status="applied",
                            agent_plan_json='{}',
                            transport_proposal_json='{}',
                            vehicle_actions_json='[]',
                            assignment_actions_json='[]',
                            route_itineraries_json='[]',
                            change_summary_json='{}',
                            cost_summary_json='{}',
                            validation_issues_json='[{"code":"manual_review_recommended","message":"Review before rollout.","blocking":false}]',
                            raw_model_response_json=json.dumps(
                                {
                                    "attempt": 1,
                                    "raw_response": {
                                        "response_metadata": {
                                            "usage": {
                                                "prompt_tokens": 321,
                                                "completion_tokens": 123,
                                                "total_tokens": 444,
                                                "estimated_cost_usd": 0.0195,
                                            }
                                        },
                                        "content": "sk-test-openai-token and Bearer hidden-secret",
                                    },
                                }
                            ),
                            prompt_version="transport_ai_route_planner_v1",
                            created_at=_fixture_timestamp(2026, 6, 11, 9, 8),
                            updated_at=_fixture_timestamp(2026, 6, 11, 9, 9),
                            saved_at=_fixture_timestamp(2026, 6, 11, 9, 8),
                            applied_at=_fixture_timestamp(2026, 6, 11, 9, 9),
                            discarded_at=None,
                        )
                        session.add(suggestion)
                        session.commit()


                Base.metadata.create_all(bind=engine)
                _seed_runs()

                with TestClient(app) as client:
                    unauthorized = client.get('/api/transport/ai/runs')
                    assert unauthorized.status_code == 401, unauthorized.text
                    assert unauthorized.json()['detail'] == 'Sessao de transporte invalida ou expirada'

                    login = client.post(
                        '/api/transport/auth/verify',
                        json={'chave': 'HR70', 'senha': 'eAcacdLe2'},
                    )
                    assert login.status_code == 200, login.text
                    assert login.json()['authenticated'] is True

                    response = client.get('/api/transport/ai/runs', params={'limit': 2})
                    assert response.status_code == 200, response.text
                    payload = response.json()
                    assert payload['count'] == 2
                    assert payload['statuses'] == []
                    assert payload['service_date'] is None
                    assert [item['run_key'] for item in payload['runs']] == [
                        'transport-ai-run:diagnostic-applied-001',
                        'transport-ai-run:diagnostic-failed-001',
                    ]

                    newest = payload['runs'][0]
                    assert newest['status'] == 'applied'
                    assert newest['llm_provider'] == 'deepseek'
                    assert newest['llm_model'] == 'deepseek-v4-pro'
                    assert newest['llm_reasoning_effort'] == 'high'
                    assert newest['openai_model'] == 'deepseek-v4-pro'
                    assert newest['suggestion_key'] == 'transport-ai-suggestion:diagnostic-applied-001'
                    assert newest['suggestion_status'] == 'applied'
                    assert newest['prompt_version'] == 'transport_ai_route_planner_v1'
                    assert newest['validation_issue_codes'] == ['manual_review_recommended']
                    assert newest['blocking_issue_count'] == 0
                    assert newest['approximate_model_call_cost'] == 0.0195
                    assert newest['approximate_model_call_cost_currency'] == 'USD'
                    assert newest['prompt_tokens'] == 321
                    assert newest['completion_tokens'] == 123
                    assert newest['total_tokens'] == 444
                    assert newest['has_raw_model_response'] is True

                    oldest = payload['runs'][1]
                    assert oldest['status'] == 'failed'
                    assert oldest['llm_provider'] == 'openai'
                    assert oldest['llm_model'] == 'gpt-5-2025-08-07'
                    assert oldest['llm_reasoning_effort'] == 'high'
                    assert oldest['error_code'] == 'transport_ai_provider_failed'
                    assert 'sk-test-openai-token' not in oldest['error_message']
                    assert 'top-secret' not in oldest['error_message']
                    assert '[REDACTED]' in oldest['error_message']
                    assert oldest['preflight_issue_codes'] == ['openai_retry_exhausted']
                    assert oldest['blocking_issue_count'] == 1
                    assert oldest['approximate_model_call_cost'] is None
                    assert oldest['has_raw_model_response'] is False

                    filtered_status = client.get('/api/transport/ai/runs', params=[('status', 'failed')])
                    assert filtered_status.status_code == 200, filtered_status.text
                    filtered_status_payload = filtered_status.json()
                    assert filtered_status_payload['count'] == 1
                    assert filtered_status_payload['statuses'] == ['failed']
                    assert [item['run_key'] for item in filtered_status_payload['runs']] == [
                        'transport-ai-run:diagnostic-failed-001'
                    ]

                    filtered_date = client.get('/api/transport/ai/runs', params={'service_date': '2026-06-11'})
                    assert filtered_date.status_code == 200, filtered_date.text
                    filtered_date_payload = filtered_date.json()
                    assert filtered_date_payload['count'] == 1
                    assert filtered_date_payload['service_date'] == '2026-06-11'
                    assert [item['run_key'] for item in filtered_date_payload['runs']] == [
                        'transport-ai-run:diagnostic-applied-001'
                    ]

                    serialized_payload = response.text
                    assert 'sk-test-openai-token' not in serialized_payload
                    assert 'Bearer hidden-secret' not in serialized_payload
                    assert 'raw_model_response_json' not in serialized_payload

                print('transport-ai-runs-diagnostics-ok')
                """
            ),
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "transport-ai-runs-diagnostics-ok" in result.stdout