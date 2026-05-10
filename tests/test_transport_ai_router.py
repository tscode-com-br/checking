import json
import os
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from sistema.app.schemas import TransportAgentDashboardScope, TransportAgentRouteRequest
from sistema.app.services.transport_ai_agent import TRANSPORT_AI_PROMPT_VERSION


def test_transport_agent_route_request_normalizes_dashboard_scope_project_ids():
    payload = TransportAgentRouteRequest(
        service_date=date(2026, 6, 12),
        route_kind="home_to_work",
        earliest_boarding_time="06:50",
        arrival_at_work_time="07:45",
        dashboard_scope={"project_ids": [7, 3, 7, 1]},
    )

    assert payload.dashboard_scope == TransportAgentDashboardScope(
        project_ids=[1, 3, 7],
        request_kinds=["regular", "weekend", "extra"],
    )


def test_transport_agent_route_request_normalizes_dashboard_scope_request_kinds():
    payload = TransportAgentRouteRequest(
        service_date=date(2026, 6, 12),
        route_kind="home_to_work",
        earliest_boarding_time="06:50",
        arrival_at_work_time="07:45",
        dashboard_scope={"request_kinds": ["extra", "regular", "extra", "weekend"]},
    )

    assert payload.dashboard_scope == TransportAgentDashboardScope(
        project_ids=[],
        request_kinds=["regular", "weekend", "extra"],
    )


def test_transport_agent_route_request_rejects_invalid_dashboard_scope_project_ids():
    with pytest.raises(ValidationError, match="dashboard_scope.project_ids"):
        TransportAgentRouteRequest(
            service_date=date(2026, 6, 12),
            route_kind="home_to_work",
            earliest_boarding_time="06:50",
            arrival_at_work_time="07:45",
            dashboard_scope={"project_ids": [3, 0, -2]},
        )


def test_transport_agent_route_request_rejects_invalid_dashboard_scope_request_kinds():
    with pytest.raises(ValidationError, match="dashboard_scope.request_kinds"):
        TransportAgentRouteRequest(
            service_date=date(2026, 6, 12),
            route_kind="home_to_work",
            earliest_boarding_time="06:50",
            arrival_at_work_time="07:45",
            dashboard_scope={"request_kinds": ["holiday"]},
        )


def test_transport_agent_route_request_rejects_empty_dashboard_scope_request_kinds():
    with pytest.raises(ValidationError, match="dashboard_scope.request_kinds must contain at least one request kind"):
        TransportAgentRouteRequest(
            service_date=date(2026, 6, 12),
            route_kind="home_to_work",
            earliest_boarding_time="06:50",
            arrival_at_work_time="07:45",
            dashboard_scope={"project_ids": [3], "request_kinds": []},
        )


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
    env.pop("HERE_API_KEY", None)
    return env


def _run_transport_ai_router_script(
    tmp_path: Path,
    *,
    script: str,
    env_updates: dict[str, str | None] | None = None,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = _build_transport_ai_router_env(tmp_path)
    if env_updates:
        for key, value in env_updates.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
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
    error_code: str | None = None,
    preflight_issues_json: str | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    llm_reasoning_effort: str | None = None,
    route_provider: str = "fake",
    openai_model: str = "gpt-5-2025-08-07",
    planning_input_json: str = "{}",
    planning_input_hash: str = "0" * 64,
    assertions: str,
) -> str:
    effective_error_code = "synthetic_polling_failure" if error_message is not None and error_code is None else error_code
    effective_preflight_issues_json = preflight_issues_json or (
        '[{"code":"planning_warning","message":"Pending route review.","blocking":false,"setting_name":"transport_ai_polling"}]'
    )
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
                prompt_version=__PROMPT_VERSION__,
                raw_model_response_json=None,
                suggestion_key="transport-ai-suggestion:polling-001",
                proposal_key="transport-ai-proposal:polling-001",
                status="shown",
                created_at=_fixture_timestamp(),
            )
            """
        ).strip().replace("__PROMPT_VERSION__", repr(TRANSPORT_AI_PROMPT_VERSION))

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
                    llm_provider={llm_provider!r},
                    llm_model={llm_model!r},
                    llm_reasoning_effort={llm_reasoning_effort!r},
                    openai_model={openai_model!r},
                    route_provider={route_provider!r},
                    price_currency_code="SGD",
                    price_rate_unit="day",
                    baseline_snapshot_json='{{}}',
                    baseline_assignments_json='{{}}',
                    baseline_vehicle_state_json='{{}}',
                    planning_input_json={planning_input_json!r},
                    planning_input_hash={planning_input_hash!r},
                    preflight_issues_json={effective_preflight_issues_json!r},
                    error_code={effective_error_code!r},
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
                from sistema.app.database import Base, SessionLocal, engine
                from sistema.app.models import Project


                Base.metadata.create_all(bind=engine)

                with SessionLocal() as session:
                    project = Project(
                        name='Transport AI Router Project',
                        country_code='SG',
                        country_name='Singapore',
                        timezone_name='Asia/Singapore',
                        address='100 Transport Avenue',
                        zip_code='018989',
                    )
                    session.add(project)
                    session.commit()
                    project_id = project.id

                with TestClient(app) as client:
                    unauthorized = client.get('/api/transport/ai/preflight')
                    assert unauthorized.status_code == 401, unauthorized.text
                    assert unauthorized.json()['detail'] == 'Sessao de transporte invalida ou expirada'

                    unauthorized_settings = client.get(
                        '/api/transport/ai/settings',
                        params={'project_id': project_id},
                    )
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

                    missing_project = client.get(
                        '/api/transport/ai/settings',
                        params={'project_id': project_id + 999},
                    )
                    assert missing_project.status_code == 404, missing_project.text
                    missing_project_detail = missing_project.json()['detail']
                    assert missing_project_detail['message'] == 'Transport AI project does not exist.'
                    assert missing_project_detail['message_key'] == 'ai.settingsProjectMissing'
                    assert missing_project_detail['error_code'] == 'transport_ai_settings_project_not_found'

                    settings_get = client.get(
                        '/api/transport/ai/settings',
                        params={'project_id': project_id},
                    )
                    assert settings_get.status_code == 200, settings_get.text
                    settings_payload = settings_get.json()
                    assert settings_payload == {
                        'project_id': project_id,
                        'project_name': 'Transport AI Router Project',
                        'provider': 'openai',
                        'resolved_model': 'gpt-5.4-2026-03-05',
                        'reasoning_effort': 'high',
                        'has_api_key': False,
                        'api_key_hint': None,
                    }

                    invalid_settings_update = client.put(
                        '/api/transport/ai/settings',
                        json={'project_id': project_id, 'provider': 'openai', 'api_key': None},
                    )
                    assert invalid_settings_update.status_code == 409, invalid_settings_update.text
                    invalid_settings_update_detail = invalid_settings_update.json()['detail']
                    assert invalid_settings_update_detail['message'] == 'Transport AI API key is required when creating LLM settings.'
                    assert invalid_settings_update_detail['message_key'] == 'ai.settingsKeyRequired'
                    assert invalid_settings_update_detail['error_code'] == 'transport_ai_settings_validation_failed'

                    missing_run = client.get('/api/transport/ai/route-calculations/run-missing-001')
                    assert missing_run.status_code == 404, missing_run.text
                    missing_run_detail = missing_run.json()['detail']
                    assert missing_run_detail['message'] == 'Transport AI run not found.'
                    assert missing_run_detail['message_key'] == 'ai.routeCalculationFailed'
                    assert missing_run_detail['error_code'] == 'transport_ai_run_not_found'

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
                    assert 'TransportAgentRunStartResponse' in schemas
                    assert 'TransportAgentRunStatusResponse' in schemas

                    settings_get_operation = specification['paths']['/api/transport/ai/settings']['get']
                    assert any(
                        parameter['name'] == 'project_id' and parameter['in'] == 'query'
                        for parameter in settings_get_operation['parameters']
                    )

                    settings_update_schema = schemas['TransportAISettingsUpdateRequest']
                    assert 'project_id' in settings_update_schema['properties']
                    assert 'project_id' in settings_update_schema['required']

                    settings_response_schema = schemas['TransportAISettingsResponse']
                    assert 'project_id' in settings_response_schema['properties']
                    assert 'project_name' in settings_response_schema['properties']

                    start_response_schema = schemas['TransportAgentRunStartResponse']
                    assert 'error_code' in start_response_schema['properties']
                    assert 'failure_category' in start_response_schema['properties']
                    assert 'review_state' in start_response_schema['properties']

                    run_status_schema = schemas['TransportAgentRunStatusResponse']
                    assert 'error_code' in run_status_schema['properties']
                    assert 'failure_category' in run_status_schema['properties']
                    assert 'review_state' in run_status_schema['properties']

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
        assert payload["error_code"] is None
        assert payload["failure_category"] is None
        assert payload["review_state"] == "unavailable"
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


def test_transport_ai_route_departure_time_uses_eta_for_extra_home_to_work(tmp_path):
    script = textwrap.dedent(
        """
        from datetime import date

        from sistema.app.routers.transport_ai import _resolve_transport_ai_route_departure_time
        from sistema.app.schemas import (
            TransportAgentChangeSummary,
            TransportAgentCostSummary,
            TransportAgentPlan,
            TransportAgentRouteStop,
            TransportAgentVehicleItinerary,
        )


        def _build_plan(*, route_kind: str, projected_arrival_time: str, first_stop_time: str) -> TransportAgentPlan:
            itinerary = TransportAgentVehicleItinerary(
                route_key=f"route:{route_kind}",
                partition_key="extra:PPLAN1:SG",
                vehicle_ref=f"new:{route_kind}",
                service_scope="extra",
                route_kind=route_kind,
                vehicle_type="carro",
                vehicle_id=None,
                schedule_id=None,
                client_vehicle_key=f"new:{route_kind}",
                plate=None,
                project_name="PPLAN1",
                country_code="SG",
                country_name="Singapore",
                estimated_cost=120,
                total_duration_seconds=1200,
                total_distance_meters=12000,
                projected_arrival_time=projected_arrival_time,
                stops=[
                    TransportAgentRouteStop(
                        stop_order=0,
                        stop_type="pickup",
                        request_id=1,
                        user_id=1,
                        passenger_name="Passenger One",
                        project_name="PPLAN1",
                        address="1 Example Street",
                        zip_code="018989",
                        country_code="SG",
                        longitude=103.85,
                        latitude=1.30,
                        scheduled_time=first_stop_time,
                        duration_from_previous_seconds=None,
                        distance_from_previous_meters=None,
                    ),
                    TransportAgentRouteStop(
                        stop_order=1,
                        stop_type="destination",
                        request_id=None,
                        user_id=None,
                        passenger_name=None,
                        project_name="PPLAN1",
                        address="1 Marina Boulevard",
                        zip_code="018989",
                        country_code="SG",
                        longitude=103.90,
                        latitude=1.31,
                        scheduled_time=projected_arrival_time,
                        duration_from_previous_seconds=1200,
                        distance_from_previous_meters=12000,
                    ),
                ],
            )
            return TransportAgentPlan(
                plan_key=f"plan:{route_kind}",
                service_date=date.fromisoformat("2026-06-12"),
                route_kind=route_kind,
                earliest_boarding_time="06:50",
                arrival_at_work_time="07:45",
                objective_summary="Validate route departure semantics.",
                vehicle_actions=[],
                passenger_allocations=[],
                route_itineraries=[itinerary],
                cost_summary=TransportAgentCostSummary(
                    price_currency_code="SGD",
                    price_rate_unit="day",
                    current_total_estimated_cost=0,
                    suggested_total_estimated_cost=120,
                    estimated_cost_delta=120,
                    current_vehicle_count=0,
                    suggested_vehicle_count=1,
                ),
                change_summary=TransportAgentChangeSummary(
                    total_vehicle_actions=1,
                    keep_count=0,
                    create_count=1,
                    update_count=0,
                    remove_from_day_count=0,
                    by_vehicle_type=[],
                ),
                validation_issues=[],
            )


        extra_home_to_work_plan = _build_plan(
            route_kind="home_to_work",
            projected_arrival_time="19:20",
            first_stop_time="19:05",
        )
        assert _resolve_transport_ai_route_departure_time(
            plan=extra_home_to_work_plan,
            vehicle_ref="new:home_to_work",
            fallback_time="06:50",
        ) == "19:20"

        extra_work_to_home_plan = _build_plan(
            route_kind="work_to_home",
            projected_arrival_time="19:20",
            first_stop_time="19:05",
        )
        assert _resolve_transport_ai_route_departure_time(
            plan=extra_work_to_home_plan,
            vehicle_ref="new:work_to_home",
            fallback_time="06:50",
        ) == "19:05"

        print('transport-ai-route-departure-time-extra-home-ok')
        """
    ).strip()

    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_extra_vehicle_create_payload_rejects_incoherent_reference_time(tmp_path):
    script = textwrap.dedent(
        """
        from datetime import date
        from types import SimpleNamespace

        from sistema.app.routers.transport_ai import (
            _build_transport_ai_vehicle_create_payload,
            _resolve_transport_ai_extra_departure_time,
            _resolve_transport_ai_extra_route_kind,
        )


        def _build_plan(*, route_kind: str, projected_arrival_time: str, first_stop_time: str):
            itinerary = SimpleNamespace(
                vehicle_ref=f"new:{route_kind}",
                service_scope="extra",
                route_kind=route_kind,
                projected_arrival_time=projected_arrival_time,
                stops=[
                    SimpleNamespace(scheduled_time=first_stop_time),
                    SimpleNamespace(scheduled_time=projected_arrival_time),
                ],
            )
            return SimpleNamespace(route_itineraries=[itinerary])


        home_plan = _build_plan(
            route_kind="home_to_work",
            projected_arrival_time="19:20",
            first_stop_time="19:05",
        )
        home_run = SimpleNamespace(service_date=date.fromisoformat("2026-06-13"), route_kind="home_to_work")
        valid_home_action = SimpleNamespace(
            service_scope="extra",
            client_vehicle_key="new:home_to_work",
            action_key="action:extra-home-to-work",
            after={
                "route_kind": "home_to_work",
                "departure_time": "19:20",
                "color": "white",
            },
        )
        route_kind, route_issue = _resolve_transport_ai_extra_route_kind(
            run=home_run,
            action=valid_home_action,
        )
        assert route_kind == "home_to_work"
        assert route_issue is None

        departure_time, departure_issue = _resolve_transport_ai_extra_departure_time(
            plan=home_plan,
            vehicle_ref="new:home_to_work",
            route_kind=route_kind,
            fallback_time="06:50",
            action=valid_home_action,
        )
        assert departure_time == "19:20"
        assert departure_issue is None

        payload, payload_issue = _build_transport_ai_vehicle_create_payload(
            run=home_run,
            action=valid_home_action,
            plate="AIX123",
            vehicle_type="carro",
            capacity=4,
            default_tolerance=15,
            route_kind=route_kind,
            departure_time=departure_time,
        )
        assert payload_issue is None
        assert payload is not None
        assert payload.route_kind == "home_to_work"
        assert payload.departure_time == "19:20"

        invalid_home_action = SimpleNamespace(
            service_scope="extra",
            client_vehicle_key="new:home-to-work-mismatch",
            action_key="action:extra-home-to-work-mismatch",
            after={
                "route_kind": "home_to_work",
                "departure_time": "19:05",
            },
        )
        invalid_home_departure_time, invalid_home_issue = _resolve_transport_ai_extra_departure_time(
            plan=home_plan,
            vehicle_ref="new:home_to_work",
            route_kind="home_to_work",
            fallback_time="06:50",
            action=invalid_home_action,
        )
        assert invalid_home_departure_time is None
        assert invalid_home_issue is not None
        assert invalid_home_issue.code == "transport_ai_extra_vehicle_departure_time_mismatch"

        work_plan = _build_plan(
            route_kind="work_to_home",
            projected_arrival_time="19:40",
            first_stop_time="19:20",
        )
        work_run = SimpleNamespace(service_date=date.fromisoformat("2026-06-13"), route_kind="work_to_home")
        invalid_work_action = SimpleNamespace(
            service_scope="extra",
            client_vehicle_key="new:work-to-home-mismatch",
            action_key="action:extra-work-to-home-mismatch",
            after={
                "route_kind": "work_to_home",
                "departure_time": "19:25",
            },
        )
        invalid_work_departure_time, invalid_work_issue = _resolve_transport_ai_extra_departure_time(
            plan=work_plan,
            vehicle_ref="new:work_to_home",
            route_kind="work_to_home",
            fallback_time="06:50",
            action=invalid_work_action,
        )
        assert invalid_work_departure_time is None
        assert invalid_work_issue is not None
        assert invalid_work_issue.code == "transport_ai_extra_vehicle_departure_time_mismatch"

        print('transport-ai-extra-create-payload-reference-time-ok')
        """
    ).strip()

    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_extra_vehicle_create_payload_rejects_route_kind_override_mismatch(tmp_path):
    script = textwrap.dedent(
        """
        from datetime import date
        from types import SimpleNamespace

        from sistema.app.routers.transport_ai import _resolve_transport_ai_extra_route_kind


        run = SimpleNamespace(service_date=date.fromisoformat("2026-06-13"), route_kind="home_to_work")
        action = SimpleNamespace(
            service_scope="extra",
            client_vehicle_key="new:route-kind-mismatch",
            action_key="action:route-kind-mismatch",
            after={"route_kind": "work_to_home"},
        )

        route_kind, issue = _resolve_transport_ai_extra_route_kind(run=run, action=action)
        assert route_kind is None
        assert issue is not None
        assert issue.code == "transport_ai_extra_vehicle_route_kind_mismatch"

        print('transport-ai-extra-create-payload-route-kind-ok')
        """
    ).strip()

    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_settings_endpoint_returns_sanitized_422_when_project_id_is_missing(tmp_path):
    script = textwrap.dedent(
        """
        from fastapi.testclient import TestClient

        from sistema.app.main import app
        from sistema.app.database import Base, engine


        Base.metadata.create_all(bind=engine)

        with TestClient(app) as client:
            login = client.post(
                '/api/transport/auth/verify',
                json={'chave': 'HR70', 'senha': 'eAcacdLe2'},
            )
            assert login.status_code == 200, login.text
            assert login.json()['authenticated'] is True

            failed = client.put(
                '/api/transport/ai/settings',
                json={
                    'provider': 'openai',
                    'api_key': 'sk-super-secret-1234',
                },
            )
            assert failed.status_code == 422, failed.text
            assert 'sk-super-secret-1234' not in failed.text

            payload = failed.json()
            assert isinstance(payload['detail'], list)
            assert payload['detail']
            first_error = payload['detail'][0]
            assert first_error['loc'] == ['body']
            assert first_error['msg'] == 'Transport AI project is required.'
            assert first_error['input']['provider'] == 'openai'
            assert first_error['input']['api_key'] == '[REDACTED]'

        print('transport-ai-settings-missing-project-sanitized-ok')
        """
    ).strip()

    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_route_calculations_start_accepts_work_to_home_payload(tmp_path):
    script = textwrap.dedent(
        """
        from fastapi.testclient import TestClient

        from sistema.app.main import app
        from sistema.app.database import Base, engine


        Base.metadata.create_all(bind=engine)

        with TestClient(app) as client:
            login = client.post(
                '/api/transport/auth/verify',
                json={'chave': 'HR70', 'senha': 'eAcacdLe2'},
            )
            assert login.status_code == 200, login.text
            assert login.json()['authenticated'] is True

            response = client.post(
                '/api/transport/ai/route-calculations',
                json={
                    'service_date': '2026-06-12',
                    'route_kind': 'work_to_home',
                    'earliest_boarding_time': '06:50',
                    'arrival_at_work_time': '07:45',
                },
            )
            assert response.status_code == 409, response.text
            payload = response.json()
            assert payload['ok'] is False
            assert payload['message'] == 'Transport AI is disabled in the server configuration.'
            assert payload['error_code'] == 'transport_ai_disabled'
            assert payload['failure_category'] == 'configuration'
            assert payload['review_state'] == 'fatal_error'
            assert [issue['code'] for issue in payload['issues']] == ['transport_ai_disabled']

        print('transport-ai-route-calculations-work-to-home-request-ok')
        """
    ).strip()

    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_route_calculations_persist_scope_project_names_and_scope_aware_failure_message(tmp_path):
    script = textwrap.dedent(
        """
        import json

        from fastapi.testclient import TestClient
        from sqlalchemy import select

        from sistema.app.main import app
        from sistema.app.database import Base, SessionLocal, engine
        from sistema.app.models import CheckEvent, Project, TransportAIRun
        from sistema.app.services import location_settings as location_settings_module


        Base.metadata.create_all(bind=engine)

        with SessionLocal() as session:
            project = Project(
                name='Scoped Audit Project',
                country_code='SG',
                country_name='Singapore',
                timezone_name='Asia/Singapore',
                address='100 Scoped Avenue',
                zip_code='018989',
            )
            session.add(project)
            session.flush()
            project_id = project.id

            location_settings_module.upsert_transport_pricing_settings(
                session,
                price_currency_code=None,
                price_rate_unit='day',
                default_car_price=120,
                default_minivan_price=None,
                default_van_price=None,
                default_bus_price=None,
            )
            session.commit()

        with TestClient(app) as client:
            login = client.post(
                '/api/transport/auth/verify',
                json={'chave': 'HR70', 'senha': 'eAcacdLe2'},
            )
            assert login.status_code == 200, login.text
            assert login.json()['authenticated'] is True

            response = client.post(
                '/api/transport/ai/route-calculations',
                json={
                    'service_date': '2026-06-12',
                    'route_kind': 'home_to_work',
                    'earliest_boarding_time': '06:50',
                    'arrival_at_work_time': '07:45',
                    'dashboard_scope': {
                        'project_ids': [project_id],
                        'request_kinds': ['extra', 'extra'],
                    },
                },
            )
            assert response.status_code == 409, response.text
            payload = response.json()
            assert payload['ok'] is False
            assert 'Transport AI planning validation failed' not in payload['message']
            assert 'No pending transport requests are eligible' in payload['message']
            assert 'selected request kind (EXTRA)' in payload['message']
            assert 'selected projects' in payload['message']
            assert 'Scoped Audit Project' in payload['message']
            assert 'Baseline restored successfully.' in payload['message']
            assert payload['error_code'] == 'transport_ai_planning_input_invalid'
            assert payload['failure_category'] == 'empty_scope'
            assert payload['review_state'] == 'fatal_error'
            assert [issue['code'] for issue in payload['issues']] == ['no_eligible_requests']
            assert 'selected request kind (EXTRA)' in payload['issues'][0]['message']
            assert 'selected projects' in payload['issues'][0]['message']
            assert 'Scoped Audit Project' in payload['issues'][0]['message']

        with SessionLocal() as session:
            run = session.execute(
                select(TransportAIRun)
                .order_by(TransportAIRun.id.desc())
                .limit(1)
            ).scalar_one()
            planning_payload = json.loads(run.planning_input_json)
            assert planning_payload['dashboard_scope'] == {
                'project_ids': [project_id],
                'request_kinds': ['extra'],
            }
            assert planning_payload['dashboard_scope_project_names'] == ['Scoped Audit Project']

            run_create_event = session.execute(
                select(CheckEvent)
                .where(
                    CheckEvent.source == 'transport_ai',
                    CheckEvent.action == 'run_create',
                )
                .order_by(CheckEvent.id.desc())
                .limit(1)
            ).scalar_one()
            baseline_save_event = session.execute(
                select(CheckEvent)
                .where(
                    CheckEvent.source == 'transport_ai',
                    CheckEvent.action == 'baseline_save',
                )
                .order_by(CheckEvent.id.desc())
                .limit(1)
            ).scalar_one()
            reset_event = session.execute(
                select(CheckEvent)
                .where(
                    CheckEvent.source == 'transport_ai',
                    CheckEvent.action == 'requests_reset',
                )
                .order_by(CheckEvent.id.desc())
                .limit(1)
            ).scalar_one()
            run_failed_event = session.execute(
                select(CheckEvent)
                .where(
                    CheckEvent.source == 'transport_ai',
                    CheckEvent.action == 'run_fail',
                )
                .order_by(CheckEvent.id.desc())
                .limit(1)
            ).scalar_one()

            run_create_details = json.loads(run_create_event.details)
            baseline_save_details = json.loads(baseline_save_event.details)
            reset_details = json.loads(reset_event.details)
            run_failed_details = json.loads(run_failed_event.details)
            assert run_create_details['extra']['dashboard_scope'] == {
                'project_ids': [project_id],
                'request_kinds': ['extra'],
            }
            assert run_create_details['extra']['dashboard_scope_project_names'] == ['Scoped Audit Project']
            assert run_create_details['extra']['dashboard_scope_project_count'] == 1
            assert run_create_details['extra']['dashboard_scope_request_kind_labels'] == ['EXTRA']
            assert run_create_details['extra']['dashboard_scope_request_kind_count'] == 1
            assert baseline_save_details['extra']['dashboard_scope'] == {
                'project_ids': [project_id],
                'request_kinds': ['extra'],
            }
            assert baseline_save_details['extra']['dashboard_scope_project_names'] == ['Scoped Audit Project']
            assert baseline_save_details['extra']['dashboard_scope_project_count'] == 1
            assert baseline_save_details['extra']['dashboard_scope_request_kind_labels'] == ['EXTRA']
            assert baseline_save_details['extra']['dashboard_scope_request_kind_count'] == 1
            assert baseline_save_details['extra']['baseline_duration_ms'] >= 0
            assert reset_details['extra']['reset_duration_ms'] >= 0
            assert planning_payload['observability']['total_eligible_request_count'] == 0
            assert planning_payload['observability']['partition_count'] == 0
            assert planning_payload['observability']['failure_layer'] == 'local'
            assert planning_payload['observability']['failed_phase'] == 'validation'
            assert planning_payload['observability']['phase_durations_ms']['baseline_ms'] >= 0
            assert planning_payload['observability']['phase_durations_ms']['reset_ms'] >= 0
            assert planning_payload['observability']['phase_durations_ms']['restore_ms'] >= 0
            assert run_failed_details['extra']['error_code'] == 'transport_ai_planning_input_invalid'
            assert run_failed_details['extra']['observability']['failed_phase'] == 'validation'
            assert run_failed_details['extra']['observability']['failure_layer'] == 'local'
            assert run_failed_details['extra']['observability']['phase_durations_ms']['reset_ms'] >= 0

        print('transport-ai-route-calculations-scope-audit-ok')
        """
    ).strip()

    _run_transport_ai_router_script(
        tmp_path,
        script=script,
        env_updates={
            'TRANSPORT_AI_ENABLED': 'true',
            'TRANSPORT_AI_AGENT_MODE': 'deterministic',
            'HERE_API_KEY': 'test-here-api-key',
            'TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE': 'phase8-loadtest-2026-05-05',
            'TRANSPORT_AI_MAX_CONCURRENT_RUNS': '2',
            'TRANSPORT_AI_MAX_RUNTIME_SECONDS': '180',
            'TRANSPORT_AI_MAX_PASSENGERS_PER_RUN': '80',
        },
    )


def test_transport_ai_settings_endpoint_saves_masked_configuration_and_audits_safely(tmp_path):
    script = textwrap.dedent(
        """
        import json

        from fastapi.testclient import TestClient
        from sqlalchemy import select

        from sistema.app.main import app
        from sistema.app.database import Base, SessionLocal, engine
        from sistema.app.models import CheckEvent, Project, TransportAIProjectLlmSettings


        Base.metadata.create_all(bind=engine)

        project_name = 'Transport AI Settings Project'

        with SessionLocal() as session:
            project = Project(
                name=project_name,
                country_code='SG',
                country_name='Singapore',
                timezone_name='Asia/Singapore',
                address='100 Settings Avenue',
                zip_code='018989',
            )
            session.add(project)
            session.commit()
            project_id = project.id

        with TestClient(app) as client:
            login = client.post(
                '/api/transport/auth/verify',
                json={'chave': 'HR70', 'senha': 'eAcacdLe2'},
            )
            assert login.status_code == 200, login.text
            assert login.json()['authenticated'] is True

            created = client.put(
                '/api/transport/ai/settings',
                json={
                    'project_id': project_id,
                    'provider': 'openai',
                    'api_key': 'sk-super-secret-1234',
                },
            )
            assert created.status_code == 200, created.text
            assert 'sk-super-secret-1234' not in created.text
            assert created.json() == {
                'project_id': project_id,
                'project_name': project_name,
                'provider': 'openai',
                'resolved_model': 'gpt-5.4-2026-03-05',
                'reasoning_effort': 'high',
                'has_api_key': True,
                'api_key_hint': '***1234',
            }

            fetched = client.get('/api/transport/ai/settings', params={'project_id': project_id})
            assert fetched.status_code == 200, fetched.text
            assert 'sk-super-secret-1234' not in fetched.text
            assert fetched.json() == created.json()

            invalid_provider_change = client.put(
                '/api/transport/ai/settings',
                json={'project_id': project_id, 'provider': 'deepseek', 'api_key': None},
            )
            assert invalid_provider_change.status_code == 409, invalid_provider_change.text
            assert 'sk-super-secret-1234' not in invalid_provider_change.text
            invalid_provider_change_detail = invalid_provider_change.json()['detail']
            assert invalid_provider_change_detail['message'] == 'Transport AI API key is required when changing the LLM provider.'
            assert invalid_provider_change_detail['message_key'] == 'ai.settingsProviderKeyRequired'
            assert invalid_provider_change_detail['error_code'] == 'transport_ai_settings_validation_failed'

            with SessionLocal() as session:
                persisted_settings = session.execute(
                    select(TransportAIProjectLlmSettings).where(
                        TransportAIProjectLlmSettings.project_id == project_id
                    )
                ).scalar_one_or_none()
                assert persisted_settings is not None
                assert persisted_settings.project_id == project_id
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
                assert audit_details['project_id'] == project_id
                assert audit_details['project_name'] == project_name
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


def test_transport_ai_settings_endpoint_returns_404_for_missing_project_update_without_leaking_secret(tmp_path):
    script = textwrap.dedent(
        """
        from fastapi.testclient import TestClient
        from sqlalchemy import select

        from sistema.app.main import app
        from sistema.app.database import Base, SessionLocal, engine
        from sistema.app.models import TransportAIProjectLlmSettings


        Base.metadata.create_all(bind=engine)

        with TestClient(app) as client:
            login = client.post(
                '/api/transport/auth/verify',
                json={'chave': 'HR70', 'senha': 'eAcacdLe2'},
            )
            assert login.status_code == 200, login.text
            assert login.json()['authenticated'] is True

            missing_project = client.put(
                '/api/transport/ai/settings',
                json={
                    'project_id': 9999,
                    'provider': 'openai',
                    'api_key': 'sk-missing-project-1234',
                },
            )
            assert missing_project.status_code == 404, missing_project.text
            missing_project_detail = missing_project.json()['detail']
            assert missing_project_detail['message'] == 'Transport AI project does not exist.'
            assert missing_project_detail['message_key'] == 'ai.settingsProjectMissing'
            assert missing_project_detail['error_code'] == 'transport_ai_settings_project_not_found'
            assert 'sk-missing-project-1234' not in missing_project.text

            with SessionLocal() as session:
                persisted_rows = session.execute(select(TransportAIProjectLlmSettings)).scalars().all()
                assert persisted_rows == []

        print('transport-ai-settings-missing-project-update-ok')
        """
    ).strip()

    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_settings_endpoint_keeps_project_rows_isolated_and_rolls_back_failed_provider_change(tmp_path):
    script = textwrap.dedent(
        """
        from fastapi.testclient import TestClient
        from sqlalchemy import select

        from sistema.app.main import app
        from sistema.app.database import Base, SessionLocal, engine
        from sistema.app.models import Project, TransportAILlmSettings, TransportAIProjectLlmSettings
        from sistema.app.routers import transport_ai as transport_ai_router_module
        from sistema.app.services.transport_ai_llm_settings import TransportAILlmSettingsValidationError


        Base.metadata.create_all(bind=engine)

        with SessionLocal() as session:
            project_a = Project(
                name='Transport AI Isolated Project A',
                country_code='SG',
                country_name='Singapore',
                timezone_name='Asia/Singapore',
                address='201 Project Avenue',
                zip_code='018995',
            )
            project_b = Project(
                name='Transport AI Isolated Project B',
                country_code='SG',
                country_name='Singapore',
                timezone_name='Asia/Singapore',
                address='202 Project Avenue',
                zip_code='018996',
            )
            session.add(project_a)
            session.add(project_b)
            session.commit()
            project_a_id = project_a.id
            project_b_id = project_b.id

        original_upsert = transport_ai_router_module.upsert_transport_ai_llm_settings

        with TestClient(app) as client:
            login = client.post(
                '/api/transport/auth/verify',
                json={'chave': 'HR70', 'senha': 'eAcacdLe2'},
            )
            assert login.status_code == 200, login.text
            assert login.json()['authenticated'] is True

            saved_a = client.put(
                '/api/transport/ai/settings',
                json={
                    'project_id': project_a_id,
                    'provider': 'openai',
                    'api_key': 'sk-project-a-1234',
                },
            )
            assert saved_a.status_code == 200, saved_a.text

            saved_b = client.put(
                '/api/transport/ai/settings',
                json={
                    'project_id': project_b_id,
                    'provider': 'deepseek',
                    'api_key': 'deepseek-project-b-9876',
                },
            )
            assert saved_b.status_code == 200, saved_b.text

            def _mutating_failure(db, *, project_id, provider, api_key, actor_admin_user_id):
                persisted = transport_ai_router_module.get_transport_ai_llm_settings(db, project_id=project_id)
                assert persisted is not None
                persisted.provider = 'deepseek'
                persisted.model_name = 'deepseek-v4-pro'
                persisted.reasoning_effort = 'high'
                persisted.api_key_last4 = '0000'
                persisted.api_key_ciphertext = 'leaked-ciphertext-0000'
                db.flush()
                raise TransportAILlmSettingsValidationError(
                    'Transport AI API key is required when changing the LLM provider.'
                )

            transport_ai_router_module.upsert_transport_ai_llm_settings = _mutating_failure
            try:
                failed_change = client.put(
                    '/api/transport/ai/settings',
                    json={
                        'project_id': project_a_id,
                        'provider': 'deepseek',
                        'api_key': None,
                    },
                )
            finally:
                transport_ai_router_module.upsert_transport_ai_llm_settings = original_upsert

            assert failed_change.status_code == 409, failed_change.text
            failed_change_detail = failed_change.json()['detail']
            assert failed_change_detail['message'] == 'Transport AI API key is required when changing the LLM provider.'
            assert failed_change_detail['message_key'] == 'ai.settingsProviderKeyRequired'
            assert failed_change_detail['error_code'] == 'transport_ai_settings_validation_failed'

            fetched_a = client.get('/api/transport/ai/settings', params={'project_id': project_a_id})
            fetched_b = client.get('/api/transport/ai/settings', params={'project_id': project_b_id})
            assert fetched_a.status_code == 200, fetched_a.text
            assert fetched_b.status_code == 200, fetched_b.text
            assert fetched_a.json()['provider'] == 'openai'
            assert fetched_a.json()['api_key_hint'] == '***1234'
            assert fetched_b.json()['provider'] == 'deepseek'
            assert fetched_b.json()['api_key_hint'] == '***9876'

            with SessionLocal() as session:
                project_rows = session.execute(
                    select(TransportAIProjectLlmSettings)
                    .order_by(TransportAIProjectLlmSettings.project_id.asc())
                ).scalars().all()
                legacy_rows = session.execute(select(TransportAILlmSettings)).scalars().all()

                assert [row.project_id for row in project_rows] == [project_a_id, project_b_id]
                assert legacy_rows == []

                project_a_settings = project_rows[0]
                project_b_settings = project_rows[1]

                assert project_a_settings.provider == 'openai'
                assert project_a_settings.api_key_last4 == '1234'
                assert project_a_settings.api_key_ciphertext != 'sk-project-a-1234'
                assert project_a_settings.api_key_ciphertext != 'leaked-ciphertext-0000'

                assert project_b_settings.provider == 'deepseek'
                assert project_b_settings.api_key_last4 == '9876'
                assert project_b_settings.api_key_ciphertext != 'deepseek-project-b-9876'
                assert project_b_settings.api_key_ciphertext != project_a_settings.api_key_ciphertext

        print('transport-ai-settings-isolation-and-rollback-ok')
        """
    ).strip()

    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_settings_endpoint_reports_encryption_unavailable_on_load_when_server_key_is_missing(tmp_path):
    script = textwrap.dedent(
        """
        from fastapi.testclient import TestClient

        from sistema.app.main import app
        from sistema.app.database import Base, SessionLocal, engine
        from sistema.app.models import Project


        Base.metadata.create_all(bind=engine)

        with SessionLocal() as session:
            project = Project(
                name='Transport AI Encryption Project',
                country_code='SG',
                country_name='Singapore',
                timezone_name='Asia/Singapore',
                address='101 Encryption Avenue',
                zip_code='018990',
            )
            session.add(project)
            session.commit()
            project_id = project.id

        with TestClient(app) as client:
            login = client.post(
                '/api/transport/auth/verify',
                json={'chave': 'HR70', 'senha': 'eAcacdLe2'},
            )
            assert login.status_code == 200, login.text
            assert login.json()['authenticated'] is True

            settings_get = client.get('/api/transport/ai/settings', params={'project_id': project_id})
            assert settings_get.status_code == 503, settings_get.text
            settings_get_detail = settings_get.json()['detail']
            assert settings_get_detail['message'] == 'Transport AI settings encryption is unavailable.'
            assert settings_get_detail['message_key'] == 'ai.settingsEncryptionUnavailable'
            assert settings_get_detail['error_code'] == 'transport_ai_settings_encryption_unavailable'

        print('transport-ai-settings-get-encryption-unavailable-ok')
        """
    ).strip()

    _run_transport_ai_router_script(
        tmp_path,
        script=script,
        env_updates={"TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY": "not-a-valid-fernet-key"},
    )


def test_transport_ai_settings_endpoint_returns_controlled_error_when_saved_provider_is_no_longer_supported(tmp_path):
    script = textwrap.dedent(
        """
        from fastapi.testclient import TestClient

        from sistema.app.main import app
        from sistema.app.database import Base, SessionLocal, engine
        from sistema.app.models import Project
        from sistema.app.services import transport_ai_llm_settings as transport_ai_llm_settings_module


        Base.metadata.create_all(bind=engine)

        project_name = 'Transport AI Unsupported Provider Project'

        with SessionLocal() as session:
            project = Project(
                name=project_name,
                country_code='SG',
                country_name='Singapore',
                timezone_name='Asia/Singapore',
                address='102 Provider Avenue',
                zip_code='018991',
            )
            session.add(project)
            session.commit()
            project_id = project.id

        with TestClient(app) as client:
            login = client.post(
                '/api/transport/auth/verify',
                json={'chave': 'HR70', 'senha': 'eAcacdLe2'},
            )
            assert login.status_code == 200, login.text
            assert login.json()['authenticated'] is True

            created = client.put(
                '/api/transport/ai/settings',
                json={
                    'project_id': project_id,
                    'provider': 'deepseek',
                    'api_key': 'deepseek-secret-5678',
                },
            )
            assert created.status_code == 200, created.text

            removed_defaults = transport_ai_llm_settings_module.TRANSPORT_AI_LLM_PROVIDER_DEFAULTS.pop('deepseek', None)
            assert removed_defaults is not None
            try:
                invalid = client.get('/api/transport/ai/settings', params={'project_id': project_id})
                assert invalid.status_code == 409, invalid.text
                invalid_detail = invalid.json()['detail']
                assert invalid_detail['message'] == (
                    'The configured Transport AI LLM provider is no longer supported. '
                    'Select OpenAI or DeepSeek and save the AI settings again.'
                )
                assert invalid_detail['message_key'] == 'ai.settingsProviderUnsupported'
                assert invalid_detail['error_code'] == 'transport_ai_settings_validation_failed'

                repaired = client.put(
                    '/api/transport/ai/settings',
                    json={
                        'project_id': project_id,
                        'provider': 'openai',
                        'api_key': 'sk-openai-1234',
                    },
                )
                assert repaired.status_code == 200, repaired.text
                assert repaired.json() == {
                    'project_id': project_id,
                    'project_name': project_name,
                    'provider': 'openai',
                    'resolved_model': 'gpt-5.4-2026-03-05',
                    'reasoning_effort': 'high',
                    'has_api_key': True,
                    'api_key_hint': '***1234',
                }

                fetched = client.get('/api/transport/ai/settings', params={'project_id': project_id})
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
                from sistema.app.models import AdminUser, Project, TransportAIRun
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

                    project = Project(
                        name='Transport AI Snapshot Project',
                        country_code='SG',
                        country_name='Singapore',
                        timezone_name='Asia/Singapore',
                        address='103 Snapshot Avenue',
                        zip_code='018992',
                    )
                    session.add(project)
                    session.flush()
                    project_id = project.id

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
                        prompt_version=__PROMPT_VERSION__,
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
                        json={
                            'project_id': project_id,
                            'provider': 'openai',
                            'api_key': 'sk-openai-1234',
                        },
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
            ).replace("__PROMPT_VERSION__", repr(TRANSPORT_AI_PROMPT_VERSION)),
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
        from sistema.app.models import CheckEvent, Project
        from sistema.app.routers import transport_ai as transport_ai_router_module
        from sistema.app.services.transport_ai_llm_settings import TransportAILlmSettingsValidationError


        Base.metadata.create_all(bind=engine)

        with SessionLocal() as session:
            project = Project(
                name='Transport AI Failure Project',
                country_code='SG',
                country_name='Singapore',
                timezone_name='Asia/Singapore',
                address='104 Failure Avenue',
                zip_code='018993',
            )
            session.add(project)
            session.commit()
            project_id = project.id


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
                    json={
                        'project_id': project_id,
                        'provider': 'deepseek',
                        'api_key': 'deepseek-secret-5678',
                    },
                )
                assert failed.status_code == 409, failed.text
                assert 'deepseek-secret-5678' not in failed.text
                assert 'Bearer top-secret' not in failed.text
                failed_detail = failed.json()['detail']
                assert '[REDACTED]' in failed_detail['message']
                assert failed_detail['message_key'] == 'ai.settingsSaveFailed'
                assert failed_detail['error_code'] == 'transport_ai_settings_validation_failed'

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
                    assert 'project_id=1' in audit_event.message
                    assert 'project=Transport AI Failure Project' in audit_event.message
                    assert '***5678' in audit_event.message

                    audit_details = json.loads(audit_event.details)
                    assert audit_details['project_id'] == project_id
                    assert audit_details['project_name'] == 'Transport AI Failure Project'
                    assert audit_details['requested_provider'] == 'deepseek'
                    assert bool(audit_details['submitted_has_api_key']) is True
                    assert audit_details['api_key_hint'] == '***5678'
                    assert audit_details['failure_detail'] == failed_detail['message']
                    assert audit_details['request_path'] == '/api/transport/ai/settings'
        finally:
            transport_ai_router_module.upsert_transport_ai_llm_settings = original_upsert

        print('transport-ai-settings-failure-sanitized-ok')
        """
    ).strip()

    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_settings_endpoint_sanitizes_encryption_failure_on_save(tmp_path):
    script = textwrap.dedent(
        """
        import json

        from fastapi.testclient import TestClient
        from sqlalchemy import select

        from sistema.app.main import app
        from sistema.app.database import Base, SessionLocal, engine
        from sistema.app.models import CheckEvent, Project
        from sistema.app.routers import transport_ai as transport_ai_router_module
        from sistema.app.services.transport_ai_llm_settings import TransportAILlmSettingsEncryptionError


        Base.metadata.create_all(bind=engine)

        with SessionLocal() as session:
            project = Project(
                name='Transport AI Encryption Failure Project',
                country_code='SG',
                country_name='Singapore',
                timezone_name='Asia/Singapore',
                address='105 Encryption Avenue',
                zip_code='018994',
            )
            session.add(project)
            session.commit()
            project_id = project.id


        def _boom(*args, **kwargs):
            raise TransportAILlmSettingsEncryptionError(
                'Transport AI settings encryption key is invalid; leaked deepseek-secret-9911, Bearer encryption-secret, and gAAAAABmCiphertextValue9911_ABCDEFGHIJKLMN.'
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
                    json={
                        'project_id': project_id,
                        'provider': 'deepseek',
                        'api_key': 'deepseek-secret-9911',
                    },
                )
                assert failed.status_code == 503, failed.text
                failed_detail = failed.json()['detail']
                assert failed_detail['message'] == 'Transport AI settings encryption is unavailable.'
                assert failed_detail['message_key'] == 'ai.settingsEncryptionUnavailable'
                assert failed_detail['error_code'] == 'transport_ai_settings_encryption_unavailable'
                assert 'deepseek-secret-9911' not in failed.text
                assert 'Bearer encryption-secret' not in failed.text
                assert 'gAAAAABmCiphertextValue9911_ABCDEFGHIJKLMN' not in failed.text

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
                    assert audit_event.http_status == 503
                    assert 'deepseek-secret-9911' not in audit_event.message
                    assert 'deepseek-secret-9911' not in (audit_event.details or '')
                    assert 'Bearer encryption-secret' not in audit_event.message
                    assert 'Bearer encryption-secret' not in (audit_event.details or '')
                    assert 'gAAAAABmCiphertextValue9911_ABCDEFGHIJKLMN' not in audit_event.message
                    assert 'gAAAAABmCiphertextValue9911_ABCDEFGHIJKLMN' not in (audit_event.details or '')
                    assert 'project=Transport AI Encryption Failure Project' in audit_event.message
                    assert 'api_key_hint=***9911' in audit_event.message

                    audit_details = json.loads(audit_event.details)
                    assert audit_details['project_id'] == project_id
                    assert audit_details['project_name'] == 'Transport AI Encryption Failure Project'
                    assert audit_details['requested_provider'] == 'deepseek'
                    assert audit_details['api_key_hint'] == '***9911'
                    assert audit_details['response_detail'] == 'Transport AI settings encryption is unavailable.'
                    assert 'deepseek-secret-9911' not in audit_details['failure_detail']
                    assert 'Bearer encryption-secret' not in audit_details['failure_detail']
                    assert 'gAAAAABmCiphertextValue9911_ABCDEFGHIJKLMN' not in audit_details['failure_detail']
                    assert '[REDACTED]' in audit_details['failure_detail']
        finally:
            transport_ai_router_module.upsert_transport_ai_llm_settings = original_upsert

        print('transport-ai-settings-encryption-failure-sanitized-ok')
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
        assert payload["error_code"] is None
        assert payload["failure_category"] is None
        assert payload["review_state"] == "review_with_exceptions"
        assert payload["can_save"] is True
        assert payload["can_apply"] is True
        assert payload["can_cancel_restore"] is True
        assert payload["message"] == "Transport AI suggestion is ready for review."
        assert payload["suggestion"]["status"] == "shown"
        assert payload["suggestion"]["prompt_version"] == __PROMPT_VERSION__
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
    ).strip().replace("__PROMPT_VERSION__", repr(TRANSPORT_AI_PROMPT_VERSION))
    script = _build_transport_ai_run_status_script(
        run_status="proposed",
        include_suggestion=True,
        run_key="transport-ai-run:polling-proposed-001",
        error_message=None,
        assertions=assertions,
    )
    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_run_status_returns_extra_cluster_audit_summary(tmp_path):
    planning_input_json = json.dumps(
        {
            "planning_input_hash": "4" * 64,
            "settings": {"extra_car_tolerance_minutes": 30},
            "partitions": [
                {
                    "partition_key": "extra:P80:SG",
                    "request_kind": "extra",
                    "temporal_request_clusters": [
                        {
                            "cluster_key": "cluster:extra:night:1",
                            "anchor_requested_time": "19:20",
                            "earliest_requested_time": "19:00",
                            "latest_requested_time": "19:20",
                            "request_ids": [301, 302],
                        },
                        {
                            "cluster_key": "cluster:extra:night:2",
                            "anchor_requested_time": "19:45",
                            "earliest_requested_time": "19:45",
                            "latest_requested_time": "19:45",
                            "request_ids": [303],
                        },
                    ],
                }
            ],
        }
    )
    assertions = textwrap.dedent(
        """
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "proposed"
        assert payload["suggestion"]["audit"]["planning_input_hash"] == "4" * 64
        assert payload["suggestion"]["audit"]["extra_car_tolerance_minutes"] == 30
        assert len(payload["suggestion"]["audit"]["extra_clusters"]) == 2
        first_cluster = payload["suggestion"]["audit"]["extra_clusters"][0]
        second_cluster = payload["suggestion"]["audit"]["extra_clusters"][1]
        assert first_cluster["cluster_key"] == "cluster:extra:night:1"
        assert first_cluster["partition_key"] == "extra:P80:SG"
        assert first_cluster["anchor_requested_time"] == "19:20"
        assert first_cluster["request_ids"] == [301, 302]
        assert first_cluster["request_count"] == 2
        assert second_cluster["cluster_key"] == "cluster:extra:night:2"
        assert second_cluster["anchor_requested_time"] == "19:45"
        """
    ).strip()
    script = _build_transport_ai_run_status_script(
        run_status="proposed",
        include_suggestion=True,
        run_key="transport-ai-run:polling-audit-001",
        error_message=None,
        planning_input_json=planning_input_json,
        planning_input_hash="4" * 64,
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
        assert payload["error_code"] == "synthetic_polling_failure"
        assert payload["failure_category"] == "unexpected"
        assert payload["review_state"] == "fatal_error"
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


def test_transport_ai_run_status_rewrites_legacy_planning_failure_envelope_to_primary_cause(tmp_path):
    assertions = textwrap.dedent(
        """
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["ok"] is False
        assert payload["status"] == "failed"
        assert payload["error_code"] == "transport_ai_planning_input_invalid"
        assert payload["failure_category"] == "capacity"
        assert payload["review_state"] == "fatal_error"
        assert payload["message"] == "The selected date and route have 100 pending passengers, which exceeds the configured limit of 80. Baseline restored successfully."
        assert "Transport AI planning validation failed" not in payload["message"]
        assert payload["issues"][0]["code"] == "max_passengers_per_run_exceeded"
        """
    ).strip()
    script = _build_transport_ai_run_status_script(
        run_status="failed",
        include_suggestion=False,
        run_key="transport-ai-run:polling-capacity-001",
        error_code="transport_ai_planning_input_invalid",
        error_message="Transport AI planning validation failed after resetting eligible requests. Baseline restored.",
        preflight_issues_json='[{"code":"max_passengers_per_run_exceeded","message":"The selected date and route have 100 pending passengers, which exceeds the configured limit of 80.","blocking":true,"setting_name":"transport_ai_max_passengers_per_run"}]',
        assertions=assertions,
    )
    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_run_status_humanizes_mapbox_timeout_and_keeps_runtime_issue_detail(tmp_path):
    assertions = textwrap.dedent(
        """
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["ok"] is False
        assert payload["status"] == "failed"
        assert payload["suggestion"] is None
        assert payload["suggestion_ready"] is False
        assert payload["error_code"] == "mapbox_geocode_timeout"
        assert payload["failure_category"] == "route_provider"
        assert payload["review_state"] == "fatal_error"
        assert payload["message_key"] == "transport_ai.error.mapbox_geocode_timeout"
        assert payload["message"] == "Transport AI timed out while waiting for Mapbox geocoding."
        assert payload["message"] != payload["issues"][0]["message"]
        assert payload["issues"][0]["code"] == "mapbox_geocode_timeout"
        assert payload["issues"][0]["source"] == "run_error"
        assert payload["issues"][0]["message"] == "Mapbox geocode request timed out after 20 seconds."
        """
    ).strip()
    script = _build_transport_ai_run_status_script(
        run_status="failed",
        include_suggestion=False,
        run_key="transport-ai-run:polling-mapbox-timeout-001",
        error_code="mapbox_geocode_timeout",
        error_message="Mapbox geocode request timed out after 20 seconds.",
        preflight_issues_json='[{"code":"mapbox_geocode_timeout","message":"Mapbox geocode request timed out after 20 seconds.","blocking":true,"setting_name":"transport_ai_mapbox_geocode","source":"run_error"}]',
        route_provider="mapbox",
        assertions=assertions,
    )
    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_run_status_humanizes_passenger_geocode_low_confidence_issue(tmp_path):
    assertions = textwrap.dedent(
        """
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["ok"] is False
        assert payload["status"] == "failed"
        assert payload["error_code"] == "passenger_origin_geocode_low_confidence"
        assert payload["failure_category"] == "geocoding"
        assert payload["review_state"] == "fatal_error"
        assert payload["message_key"] == "transport_ai.error.passenger_origin_geocode_low_confidence"
        assert payload["message"] == "Transport AI could not calculate routes because one or more passenger addresses returned low geocoding confidence."
        assert payload["issues"][0]["code"] == "passenger_origin_geocode_low_confidence"
        assert payload["issues"][0]["source"] == "run_error"
        assert "returned low geocode confidence" in payload["issues"][0]["message"]
        """
    ).strip()
    script = _build_transport_ai_run_status_script(
        run_status="failed",
        include_suggestion=False,
        run_key="transport-ai-run:polling-geocode-confidence-001",
        error_code="passenger_origin_geocode_low_confidence",
        error_message="Passenger 'Worker 42' (W042) returned low geocode confidence (0.64).",
        preflight_issues_json='[{"code":"passenger_origin_geocode_low_confidence","message":"Passenger \'Worker 42\' (W042) returned low geocode confidence (0.64).","blocking":true,"setting_name":"transport_route_points","source":"run_error"}]',
        route_provider="mapbox",
        assertions=assertions,
    )
    _run_transport_ai_router_script(tmp_path, script=script)


def test_transport_ai_run_status_humanizes_llm_invoke_failure_and_exposes_message_params(tmp_path):
    assertions = textwrap.dedent(
        """
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["ok"] is False
        assert payload["status"] == "failed"
        assert payload["error_code"] == "transport_ai_agent_model_invoke_failed"
        assert payload["failure_category"] == "llm_invoke"
        assert payload["review_state"] == "fatal_error"
        assert payload["message_key"] == "transport_ai.error.llm_invoke_failed"
        assert payload["message"] == "Transport AI could not obtain a route calculation response from OpenAI."
        assert payload["message_params"] == {"provider": "OpenAI", "model": "gpt-4.1-mini"}
        assert payload["issues"][0]["code"] == "transport_ai_agent_model_invoke_failed"
        assert payload["issues"][0]["source"] == "run_error"
        assert payload["issues"][0]["message"] == "openai upstream gateway timeout"
        """
    ).strip()
    script = _build_transport_ai_run_status_script(
        run_status="failed",
        include_suggestion=False,
        run_key="transport-ai-run:polling-openai-invoke-001",
        error_code="transport_ai_agent_model_invoke_failed",
        error_message="openai upstream gateway timeout",
        preflight_issues_json='[{"code":"transport_ai_agent_model_invoke_failed","message":"openai upstream gateway timeout","blocking":true,"setting_name":"transport_ai_llm","source":"run_error"}]',
        llm_provider="openai",
        llm_model="gpt-4.1-mini",
        openai_model="gpt-4.1-mini",
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
                            planning_input_json=json.dumps({
                                "observability": {
                                    "total_eligible_request_count": 0,
                                    "partition_count": 0,
                                    "route_provider": "fake",
                                    "llm_provider": "openai",
                                    "llm_model": "gpt-5-2025-08-07",
                                    "llm_reasoning_effort": "high",
                                    "failure_layer": "llm",
                                    "failed_phase": "llm",
                                    "phase_durations_ms": {"baseline_ms": 12, "reset_ms": 8, "llm_ms": 41},
                                    "partitions": [],
                                }
                            }),
                            planning_input_hash="1" * 64,
                            preflight_issues_json='[{"code":"transport_ai_agent_model_invoke_failed","message":"openai upstream gateway timeout","blocking":true,"source":"run_error"}]',
                            error_code="transport_ai_agent_model_invoke_failed",
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
                            llm_provider="openai",
                            llm_model="gpt-5-2025-08-07",
                            llm_reasoning_effort="high",
                            openai_model="gpt-5-2025-08-07",
                            route_provider="fake",
                            price_currency_code="SGD",
                            price_rate_unit="day",
                            baseline_snapshot_json='{}',
                            baseline_assignments_json='{}',
                            baseline_vehicle_state_json='{}',
                            planning_input_json=json.dumps({
                                "observability": {
                                    "total_eligible_request_count": 3,
                                    "partition_count": 1,
                                    "route_provider": "fake",
                                    "llm_provider": "deepseek",
                                    "llm_model": "deepseek-v4-pro",
                                    "llm_reasoning_effort": "high",
                                    "llm_attempt_count": 1,
                                    "geocode_provider_call_count": 3,
                                    "matrix_provider_call_count": 1,
                                    "matrix_chunk_count": 1,
                                    "phase_durations_ms": {"baseline_ms": 11, "reset_ms": 7, "geocode_ms": 18, "matrix_ms": 13, "solve_ms": 9, "validation_ms": 4},
                                    "partitions": [
                                        {
                                            "partition_key": "project:41:home_to_work",
                                            "request_kind": "extra",
                                            "project_name": "Diagnostics Project",
                                            "eligible_request_count": 3,
                                            "candidate_vehicle_count": 1,
                                            "resolved_point_count": 4,
                                            "geocode_provider_call_count": 3,
                                            "matrix_request_count": 1,
                                            "matrix_chunk_count": 1,
                                            "matrix_cached": False,
                                            "solver_algorithm": "heuristic",
                                            "solver_duration_ms": 9
                                        }
                                    ]
                                },
                                "llm_runtime_projects": [
                                    {
                                        "project_id": 41,
                                        "project_name": "Diagnostics Project",
                                        "partition_keys": ["project:41:home_to_work"],
                                        "provider": "deepseek",
                                        "model_name": "deepseek-v4-pro",
                                        "reasoning_effort": "high",
                                    }
                                ]
                            }),
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
                            prompt_version=__PROMPT_VERSION__,
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
                    assert newest['prompt_version'] == __PROMPT_VERSION__
                    assert newest['validation_issue_codes'] == ['manual_review_recommended']
                    assert newest['blocking_issue_count'] == 0
                    assert newest['approximate_model_call_cost'] == 0.0195
                    assert newest['approximate_model_call_cost_currency'] == 'USD'
                    assert newest['prompt_tokens'] == 321
                    assert newest['completion_tokens'] == 123
                    assert newest['total_tokens'] == 444
                    assert newest['has_raw_model_response'] is True
                    assert newest['observability']['total_eligible_request_count'] == 3
                    assert newest['observability']['phase_durations_ms']['geocode_ms'] == 18
                    assert newest['observability']['partitions'][0]['matrix_chunk_count'] == 1

                    oldest = payload['runs'][1]
                    assert oldest['status'] == 'failed'
                    assert oldest['llm_provider'] == 'openai'
                    assert oldest['llm_model'] == 'gpt-5-2025-08-07'
                    assert oldest['llm_reasoning_effort'] == 'high'
                    assert oldest['error_code'] == 'transport_ai_agent_model_invoke_failed'
                    assert oldest['message_key'] == 'transport_ai.error.llm_invoke_failed'
                    assert oldest['message_params'] == {'provider': 'OpenAI', 'model': 'gpt-5-2025-08-07'}
                    assert 'sk-test-openai-token' not in oldest['error_message']
                    assert 'top-secret' not in oldest['error_message']
                    assert oldest['error_message'] == 'Transport AI could not obtain a route calculation response from OpenAI.'
                    assert oldest['preflight_issue_codes'] == ['transport_ai_agent_model_invoke_failed']
                    assert oldest['blocking_issue_count'] == 1
                    assert oldest['approximate_model_call_cost'] is None
                    assert oldest['has_raw_model_response'] is False
                    assert oldest['observability']['failure_layer'] == 'llm'
                    assert oldest['observability']['phase_durations_ms']['llm_ms'] == 41

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
            ).replace("__PROMPT_VERSION__", repr(TRANSPORT_AI_PROMPT_VERSION)),
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "transport-ai-runs-diagnostics-ok" in result.stdout
