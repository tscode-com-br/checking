from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from cryptography.fernet import Fernet
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
TRANSPORT_AI_TEST_OPENAI_API_KEY_ENV = "TRANSPORT_AI_TEST_OPENAI_API_KEY"
TRANSPORT_AI_OPENAI_SMOKE_SENTINEL = "transport-ai-openai-smoke-ok"


def _redact_literal_secret(value: str, secret: str) -> str:
    if not secret:
        return value
    return value.replace(secret, "[REDACTED]")


def _build_transport_ai_openai_smoke_env(tmp_path: Path) -> dict[str, str]:
    openai_api_key = os.environ[TRANSPORT_AI_TEST_OPENAI_API_KEY_ENV]
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(REPO_ROOT),
            "APP_ENV": "development",
            "DATABASE_URL": f"sqlite+pysqlite:///{(tmp_path / 'transport_ai_openai_smoke.db').as_posix()}",
            "FORMS_URL": "https://example.com/form",
            "DEVICE_SHARED_KEY": "device-test-key",
            "MOBILE_APP_SHARED_KEY": "mobile-test-key",
            "PROVIDER_SHARED_KEY": "provider-test-key",
            "ADMIN_SESSION_SECRET": "test-admin-session-secret",
            "BOOTSTRAP_ADMIN_KEY": "HR70",
            "BOOTSTRAP_ADMIN_NAME": "Transport AI OpenAI Smoke Admin",
            "BOOTSTRAP_ADMIN_PASSWORD": "eAcacdLe2",
            "FORMS_QUEUE_ENABLED": "false",
            "TRANSPORT_EXPORTS_DIR": str(tmp_path / "transport_ai_openai_smoke_exports"),
            "TRANSPORT_AI_ENABLED": "true",
            "TRANSPORT_AI_AGENT_MODE": "agent",
            "TRANSPORT_AI_ROUTE_PROVIDER": "fake",
            "TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE": "transport-ai-openai-opt-in-smoke",
            "TRANSPORT_AI_MAX_CONCURRENT_RUNS": "1",
            "TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8"),
            "MAPBOX_ACCESS_TOKEN": "test-mapbox-token",
            "OPENAI_TIMEOUT_SECONDS": "120",
            "OPENAI_MAX_RETRIES": "1",
            TRANSPORT_AI_TEST_OPENAI_API_KEY_ENV: openai_api_key,
        }
    )
    env.pop("OPENAI_API_KEY", None)
    return env


def _build_transport_ai_openai_smoke_script() -> str:
    return textwrap.dedent(
        f"""
        import os
        from datetime import date, datetime
        from zoneinfo import ZoneInfo

        from fastapi.testclient import TestClient
        from sqlalchemy import select

        from sistema.app.main import app
        from sistema.app.core.config import settings
        from sistema.app.database import Base, SessionLocal, engine
        from sistema.app.models import (
            AdminUser,
            CheckEvent,
            MobileAppSettings,
            Project,
            TransportAIRun,
            TransportAIProjectLlmSettings,
            TransportAISuggestion,
            TransportAssignment,
            TransportRequest,
            TransportVehicleSchedule,
            User,
            Vehicle,
        )


        OPENAI_API_KEY = os.environ[{TRANSPORT_AI_TEST_OPENAI_API_KEY_ENV!r}]
        API_KEY_HINT = f"***{{OPENAI_API_KEY[-4:]}}"


        def _fixture_timestamp() -> datetime:
            return datetime(2026, 5, 6, 9, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))


        def _sanitized_response_text(response) -> str:
            return str(response.text or "").replace(OPENAI_API_KEY, "[REDACTED]")


        def _assert_status_code(response, expected_status_code: int) -> None:
            assert response.status_code == expected_status_code, _sanitized_response_text(response)


        def _configure_transport_settings(session) -> None:
            settings_row = session.get(MobileAppSettings, 1)
            if settings_row is None:
                settings_row = MobileAppSettings(
                    id=1,
                    created_at=_fixture_timestamp(),
                    updated_at=_fixture_timestamp(),
                )
                session.add(settings_row)

            settings_row.transport_work_to_home_time = "16:45"
            settings_row.transport_last_update_time = "16:00"
            settings_row.transport_default_car_seats = 4
            settings_row.transport_default_minivan_seats = 6
            settings_row.transport_default_van_seats = 10
            settings_row.transport_default_bus_seats = 40
            settings_row.transport_default_tolerance_minutes = 5
            settings_row.transport_price_currency_code = "SGD"
            settings_row.transport_price_rate_unit = "day"
            settings_row.transport_default_car_price = 15
            settings_row.transport_default_minivan_price = 30
            settings_row.transport_default_van_price = 45
            settings_row.transport_default_bus_price = 70
            settings_row.updated_at = _fixture_timestamp()
            session.flush()


        def _create_admin_user(session) -> AdminUser:
            admin_user = AdminUser(
                chave="AIO9",
                nome_completo="Transport AI OpenAI Smoke Fixture Admin",
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
            return admin_user


        def _create_project(session) -> Project:
            project = Project(
                name="Transport AI OpenAI Smoke Project",
                country_code="SG",
                country_name="Singapore",
                timezone_name="Asia/Singapore",
                address="1 Marina Boulevard",
                zip_code="018989",
            )
            session.add(project)
            session.flush()
            return project


        def _create_user(session, *, project_name: str) -> User:
            user = User(
                rfid=None,
                chave="SMK901",
                senha=None,
                perfil=0,
                admin_monitored_projects_json=None,
                nome="Transport AI OpenAI Smoke Rider",
                projeto=project_name,
                workplace=None,
                vehicle_id=None,
                placa=None,
                end_rua="10 Bayfront Avenue",
                zip="018956",
                cargo=None,
                email=None,
                local=None,
                checkin=None,
                time=None,
                last_active_at=_fixture_timestamp(),
                inactivity_days=0,
            )
            session.add(user)
            session.flush()
            return user


        def _create_transport_request(session, *, user_id: int, service_date: date) -> TransportRequest:
            request = TransportRequest(
                user_id=user_id,
                request_kind="extra",
                recurrence_kind="single_date",
                requested_time="08:00",
                selected_weekdays_json=None,
                single_date=service_date,
                created_via="admin",
                status="active",
                created_at=_fixture_timestamp(),
                updated_at=_fixture_timestamp(),
                cancelled_at=None,
            )
            session.add(request)
            session.flush()
            return request


        def _create_extra_vehicle_candidate(session, *, service_date: date) -> Vehicle:
            vehicle = Vehicle(
                placa="SBA9909A",
                tipo="carro",
                color="white",
                lugares=4,
                tolerance=0,
                service_scope="extra",
            )
            session.add(vehicle)
            session.flush()

            schedule = TransportVehicleSchedule(
                vehicle_id=vehicle.id,
                service_scope="extra",
                route_kind="home_to_work",
                recurrence_kind="single_date",
                service_date=service_date,
                weekday=None,
                departure_time="07:30",
                is_active=True,
                created_at=_fixture_timestamp(),
                updated_at=_fixture_timestamp(),
            )
            session.add(schedule)
            session.flush()
            return vehicle


        def _create_assignment(session, *, request_id: int, service_date: date, vehicle_id: int, assigned_by_admin_id: int) -> TransportAssignment:
            assignment = TransportAssignment(
                request_id=request_id,
                service_date=service_date,
                route_kind="home_to_work",
                vehicle_id=vehicle_id,
                status="confirmed",
                response_message="confirmed-for-openai-smoke",
                acknowledged_by_user=False,
                acknowledged_at=None,
                assigned_by_admin_id=assigned_by_admin_id,
                created_at=_fixture_timestamp(),
                updated_at=_fixture_timestamp(),
                notified_at=None,
            )
            session.add(assignment)
            session.flush()
            return assignment


        def _login_transport(client: TestClient) -> None:
            response = client.post(
                "/api/transport/auth/verify",
                json={{"chave": "HR70", "senha": "eAcacdLe2"}},
            )
            _assert_status_code(response, 200)
            assert response.json()["authenticated"] is True


        Base.metadata.create_all(bind=engine)
        settings.transport_ai_enabled = True
        settings.transport_ai_agent_mode = "agent"
        settings.transport_ai_route_provider = "fake"
        settings.transport_ai_operational_approval_evidence = "transport-ai-openai-opt-in-smoke"
        settings.transport_ai_max_concurrent_runs = 1
        settings.mapbox_access_token = "test-mapbox-token"
        settings.openai_api_key = None
        settings.openai_model = "legacy-openai-model-ignored"

        with SessionLocal() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session)
            user = _create_user(session, project_name=project.name)
            request = _create_transport_request(session, user_id=user.id, service_date=date(2026, 6, 9))
            vehicle = _create_extra_vehicle_candidate(session, service_date=date(2026, 6, 9))
            _create_assignment(
                session,
                request_id=request.id,
                service_date=date(2026, 6, 9),
                vehicle_id=vehicle.id,
                assigned_by_admin_id=admin_user.id,
            )
            session.commit()
            seeded_project_id = project.id

        with TestClient(app) as client:
            _login_transport(client)

            projects_response = client.get("/api/transport/projects")
            _assert_status_code(projects_response, 200)
            project_rows = projects_response.json()
            assert len(project_rows) == 1
            assert project_rows[0]["id"] == seeded_project_id
            assert project_rows[0]["name"] == "Transport AI OpenAI Smoke Project"

            save_response = client.put(
                "/api/transport/ai/settings",
                json={{
                    "project_id": seeded_project_id,
                    "provider": "openai",
                    "api_key": OPENAI_API_KEY,
                }},
            )
            _assert_status_code(save_response, 200)
            assert OPENAI_API_KEY not in save_response.text
            save_payload = save_response.json()
            assert save_payload == {{
                "project_id": seeded_project_id,
                "project_name": "Transport AI OpenAI Smoke Project",
                "provider": "openai",
                "resolved_model": "gpt-5.4-2026-03-05",
                "reasoning_effort": "high",
                "has_api_key": True,
                "api_key_hint": API_KEY_HINT,
            }}

            get_response = client.get(
                "/api/transport/ai/settings",
                params={{"project_id": seeded_project_id}},
            )
            _assert_status_code(get_response, 200)
            assert OPENAI_API_KEY not in get_response.text
            assert get_response.json() == save_payload

            start_response = client.post(
                "/api/transport/ai/route-calculations",
                json={{
                    "service_date": "2026-06-09",
                    "route_kind": "home_to_work",
                    "earliest_boarding_time": "06:50",
                    "arrival_at_work_time": "07:45",
                }},
            )
            _assert_status_code(start_response, 201)
            assert OPENAI_API_KEY not in start_response.text
            start_payload = start_response.json()
            assert start_payload["ok"] is True
            assert start_payload["status"] == "proposed"
            assert start_payload["suggestion_ready"] is True
            assert start_payload["run_key"]
            assert start_payload["suggestion_key"]

            status_response = client.get(
                f"/api/transport/ai/route-calculations/{{start_payload['run_key']}}"
            )
            _assert_status_code(status_response, 200)
            assert OPENAI_API_KEY not in status_response.text
            status_payload = status_response.json()
            assert status_payload["ok"] is True
            assert status_payload["status"] == "proposed"
            assert status_payload["suggestion_ready"] is True
            assert status_payload["suggestion_key"] == start_payload["suggestion_key"]
            assert status_payload["suggestion"] is not None
            assert status_payload["suggestion"]["status"] == "shown"

        with SessionLocal() as session:
            persisted_settings = session.execute(
                select(TransportAIProjectLlmSettings).where(
                    TransportAIProjectLlmSettings.project_id == seeded_project_id
                )
            ).scalar_one()
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == start_payload["run_key"])
            ).scalar_one()
            suggestion = session.execute(
                select(TransportAISuggestion).where(
                    TransportAISuggestion.suggestion_key == start_payload["suggestion_key"]
                )
            ).scalar_one()
            audit_events = session.execute(
                select(CheckEvent)
                .where(CheckEvent.source == "transport_ai")
                .order_by(CheckEvent.id.asc())
            ).scalars().all()

        assert persisted_settings.project_id == seeded_project_id
        assert persisted_settings.provider == "openai"
        assert persisted_settings.api_key_last4 == OPENAI_API_KEY[-4:]
        assert bool(str(persisted_settings.api_key_ciphertext or "").strip()) is True
        assert persisted_settings.api_key_ciphertext != OPENAI_API_KEY

        assert run.status == "proposed"
        assert run.error_message is None
        assert run.llm_provider == "openai"
        assert run.llm_model == "gpt-5.4-2026-03-05"
        assert run.llm_reasoning_effort == "high"
        assert run.openai_model == "gpt-5.4-2026-03-05"
        assert suggestion.run_id == run.id
        assert suggestion.status == "shown"
        assert OPENAI_API_KEY not in (run.planning_input_json or "")
        assert '"api_key":' not in (run.planning_input_json or "")
        assert '"api_key_ciphertext":' not in (run.planning_input_json or "")
        assert '"api_key_last4":' not in (run.planning_input_json or "")
        assert OPENAI_API_KEY not in (run.raw_model_response_json or "")

        combined_audit_text = "\n".join(
            f"{{event.message or ''}}\n{{event.details or ''}}"
            for event in audit_events
        )
        assert OPENAI_API_KEY not in combined_audit_text
        assert persisted_settings.api_key_ciphertext not in combined_audit_text

        print({TRANSPORT_AI_OPENAI_SMOKE_SENTINEL!r})
        """
    ).strip()


def _run_transport_ai_openai_smoke_script(tmp_path: Path) -> None:
    env = _build_transport_ai_openai_smoke_env(tmp_path)
    secret = env[TRANSPORT_AI_TEST_OPENAI_API_KEY_ENV]
    result = subprocess.run(
        [sys.executable, "-c", _build_transport_ai_openai_smoke_script()],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )

    sanitized_stdout = _redact_literal_secret(result.stdout or "", secret)
    sanitized_stderr = _redact_literal_secret(result.stderr or "", secret)
    combined_output = f"{sanitized_stdout}{sanitized_stderr}"

    assert result.returncode == 0, combined_output
    assert TRANSPORT_AI_OPENAI_SMOKE_SENTINEL in sanitized_stdout


@pytest.mark.skipif(
    not os.getenv(TRANSPORT_AI_TEST_OPENAI_API_KEY_ENV),
    reason=(
        "Set TRANSPORT_AI_TEST_OPENAI_API_KEY to run the opt-in Transport AI OpenAI smoke test. "
        "Manual run: $env:TRANSPORT_AI_TEST_OPENAI_API_KEY='<secret>'; "
        "c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_openai_smoke.py -q"
    ),
)
def test_transport_ai_openai_smoke_opt_in(tmp_path):
    _run_transport_ai_openai_smoke_script(tmp_path)