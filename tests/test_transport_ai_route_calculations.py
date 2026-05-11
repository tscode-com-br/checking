import os
import subprocess
import sys
import textwrap
from pathlib import Path

from cryptography.fernet import Fernet

from sistema.app.services.transport_ai_agent import TRANSPORT_AI_PROMPT_VERSION


REPO_ROOT = Path(__file__).resolve().parents[1]


def _build_transport_ai_route_calculation_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(REPO_ROOT),
            "APP_ENV": "development",
            "DATABASE_URL": f"sqlite+pysqlite:///{(tmp_path / 'transport_ai_route_calculations.db').as_posix()}",
            "FORMS_URL": "https://example.com/form",
            "DEVICE_SHARED_KEY": "device-test-key",
            "MOBILE_APP_SHARED_KEY": "mobile-test-key",
            "PROVIDER_SHARED_KEY": "provider-test-key",
            "ADMIN_SESSION_SECRET": "test-admin-session-secret",
            "BOOTSTRAP_ADMIN_KEY": "HR70",
            "BOOTSTRAP_ADMIN_NAME": "Transport AI Route Admin",
            "BOOTSTRAP_ADMIN_PASSWORD": "eAcacdLe2",
            "FORMS_QUEUE_ENABLED": "false",
            "TRANSPORT_EXPORTS_DIR": str(tmp_path / "transport_ai_route_calculations_exports"),
            "TRANSPORT_AI_ENABLED": "true",
            "TRANSPORT_AI_AGENT_MODE": "deterministic",
            "TRANSPORT_AI_ROUTE_PROVIDER": "fake",
            "TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE": "phase8-loadtest-2026-05-05",
            "TRANSPORT_AI_MAX_CONCURRENT_RUNS": "1",
            "TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8"),
            "OPENAI_API_KEY": "sk-test-openai-token",
        }
    )
    return env


def _build_route_calculation_script(
    *,
    service_date: str,
    project_name: str,
    user_key: str,
    user_name: str,
    vehicle_plate: str,
    settings_enabled: bool,
    agent_mode: str = "deterministic",
    operational_approval_evidence: str | None = "phase8-loadtest-2026-05-05",
    max_concurrent_runs: int = 1,
    mocked_active_run_count: int | None = None,
    persisted_llm_provider: str | None = None,
    persisted_llm_api_key: str | None = None,
    patch_failure: bool,
    patch_success: bool = False,
    assertions: str,
) -> str:
    if patch_failure and patch_success:
        raise AssertionError("route calculation test helper cannot patch success and failure at the same time")

    patch_block = ""
    if patch_failure:
        patch_block = textwrap.dedent(
            f"""
            def _fake_run_transport_ai_agent(*, db, run, settings_obj, provider=None, model=None, max_validation_retries=None):
                run.status = "failed"
                run.error_code = "synthetic_route_failure"
                run.error_message = "Synthetic route calculation failure."
                run.updated_at = _fixture_timestamp()
                run.completed_at = _fixture_timestamp()
                db.flush()
                return TransportAIAgentRunResult(
                    plan=None,
                    raw_model_response_json=None,
                    prompt_version={TRANSPORT_AI_PROMPT_VERSION!r},
                    openai_model=settings_obj.openai_model,
                    attempt_count=1,
                    error_code="synthetic_route_failure",
                    error_message="Synthetic route calculation failure.",
                )

            transport_ai_router.run_transport_ai_agent = _fake_run_transport_ai_agent
            """
        ).strip()
    elif patch_success:
        patch_block = textwrap.dedent(
            f"""
            def _fake_run_transport_ai_agent(*, db, run, settings_obj, provider=None, model=None, max_validation_retries=None):
                run.status = "proposed"
                run.updated_at = _fixture_timestamp()
                run.completed_at = _fixture_timestamp()
                db.flush()
                return TransportAIAgentRunResult(
                    plan=TransportAgentPlan(
                        plan_key="transport-ai-plan:route-calculation-success-001",
                        service_date=run.service_date,
                        route_kind=run.route_kind,
                        earliest_boarding_time=run.earliest_boarding_time,
                        arrival_at_work_time=run.arrival_at_work_time,
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
                        validation_issues=[],
                    ),
                    raw_model_response_json=None,
                    prompt_version={TRANSPORT_AI_PROMPT_VERSION!r},
                    openai_model=run.openai_model,
                    attempt_count=1,
                )

            transport_ai_router.run_transport_ai_agent = _fake_run_transport_ai_agent
            """
        ).strip()

    if mocked_active_run_count is not None:
        active_run_count_block = textwrap.dedent(
            f"""
            transport_ai_router.count_transport_ai_active_runs = lambda db: {mocked_active_run_count}
            """
        ).strip()
        patch_block = "\n\n".join(part for part in [patch_block, active_run_count_block] if part)

    llm_settings_block = ""
    if persisted_llm_provider is not None and persisted_llm_api_key is not None:
        llm_settings_block = textwrap.dedent(
            f"""
            upsert_transport_ai_llm_settings(
                session,
                project_id=project.id,
                provider={persisted_llm_provider!r},
                api_key={persisted_llm_api_key!r},
                actor_admin_user_id=admin_user.id,
                settings_obj=settings,
            )
            """
        ).strip()

    indented_patch_block = textwrap.indent(patch_block, "        ") if patch_block else ""
    indented_llm_settings_block = textwrap.indent(llm_settings_block, "                ") if llm_settings_block else ""
    indented_assertions = textwrap.indent(assertions, "        ")

    return textwrap.dedent(
        f"""
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
            TransportAISuggestion,
            TransportAssignment,
            TransportRequest,
            TransportVehicleSchedule,
            User,
            Vehicle,
        )
        from sistema.app.routers import transport_ai as transport_ai_router
        from sistema.app.schemas import (
            TransportAgentChangeSummary,
            TransportAgentCostSummary,
            TransportAgentPlan,
        )
        from sistema.app.services.transport_ai_agent import TransportAIAgentRunResult
        from sistema.app.services.transport_ai_llm_settings import (
            upsert_transport_ai_llm_settings,
        )
        from sistema.app.services.transport_reevaluation_events import (
            clear_transport_reevaluation_events,
            list_recent_transport_reevaluation_events,
        )


        def _fixture_timestamp():
            return datetime(2026, 5, 4, 8, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))


        def _create_admin_user(session, *, chave: str, nome_completo: str) -> AdminUser:
            admin_user = AdminUser(
                chave=chave,
                nome_completo=nome_completo,
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


        def _create_project(session, *, name: str) -> Project:
            project = Project(
                name=name,
                country_code="SG",
                country_name="Singapore",
                timezone_name="Asia/Singapore",
                address="1 Marina Boulevard",
                zip_code="018989",
            )
            session.add(project)
            session.flush()
            return project


        def _create_user(session, *, chave: str, nome: str, projeto: str) -> User:
            user = User(
                rfid=None,
                chave=chave,
                senha=None,
                perfil=0,
                admin_monitored_projects_json=None,
                nome=nome,
                projeto=projeto,
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


        def _create_extra_vehicle_candidate(session, *, placa: str, service_date: date) -> Vehicle:
            vehicle = Vehicle(
                placa=placa,
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
                response_message="confirmed-for-ai-route-calculation",
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
            assert response.status_code == 200, response.text
            assert response.json()["authenticated"] is True


        def _seed_route_calculation_scenario(*, service_date: date, project_name: str, user_key: str, user_name: str, vehicle_plate: str):
            with SessionLocal() as session:
                _configure_transport_settings(session)
                admin_user = _create_admin_user(session, chave=f"A{{user_key[1:]}}", nome_completo=f"Admin {{user_name}}")
                project = _create_project(session, name=project_name)
                rider = _create_user(session, chave=user_key, nome=user_name, projeto=project.name)
                request = _create_transport_request(session, user_id=rider.id, service_date=service_date)
                vehicle = _create_extra_vehicle_candidate(session, placa=vehicle_plate, service_date=service_date)
                assignment = _create_assignment(
                    session,
                    request_id=request.id,
                    service_date=service_date,
                    vehicle_id=vehicle.id,
                    assigned_by_admin_id=admin_user.id,
                )
{indented_llm_settings_block}
                session.commit()
                return {{
                    "assignment_id": assignment.id,
                    "vehicle_id": vehicle.id,
                }}


        Base.metadata.create_all(bind=engine)
        settings.transport_ai_enabled = {str(settings_enabled)}
        settings.transport_ai_agent_mode = {agent_mode!r}
        settings.transport_ai_route_provider = "fake"
        settings.transport_ai_operational_approval_evidence = {operational_approval_evidence!r}
        settings.transport_ai_max_concurrent_runs = {max_concurrent_runs}
        settings.here_api_key = "test-here-api-key"
        clear_transport_reevaluation_events()
        seeded = _seed_route_calculation_scenario(
            service_date=date.fromisoformat({service_date!r}),
            project_name={project_name!r},
            user_key={user_key!r},
            user_name={user_name!r},
            vehicle_plate={vehicle_plate!r},
        )

{indented_patch_block}

        with TestClient(app) as client:
            _login_transport(client)
            response = client.post(
                "/api/transport/ai/route-calculations",
                json={{
                    "service_date": {service_date!r},
                    "route_kind": "home_to_work",
                    "earliest_boarding_time": "06:50",
                    "arrival_at_work_time": "07:45",
                }},
            )

{indented_assertions}

        print("route-calculations-ok")
        """
    ).lstrip()


def _run_transport_ai_route_calculation_script(tmp_path: Path, *, script: str) -> None:
    env = _build_transport_ai_route_calculation_env(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "route-calculations-ok" in result.stdout


def test_route_calculations_preflight_failure_does_not_create_run_or_reset(tmp_path):
    assertions = textwrap.dedent(
        """
        assert response.status_code == 409, response.text
        payload = response.json()
        assert payload["ok"] is False
        assert payload["run_key"] is None
        assert payload["issues"][0]["code"] == "transport_ai_disabled"

        with SessionLocal() as session:
            assignment = session.get(TransportAssignment, seeded["assignment_id"])
            runs = session.execute(
                select(TransportAIRun).where(TransportAIRun.service_date == date.fromisoformat("2026-06-01"))
            ).scalars().all()

        assert assignment is not None
        assert assignment.status == "confirmed"
        assert assignment.vehicle_id == seeded["vehicle_id"]
        assert runs == []
        assert list_recent_transport_reevaluation_events(limit=5) == []
        """
    ).strip()
    script = _build_route_calculation_script(
        service_date="2026-06-01",
        project_name="PAIR82A",
        user_key="R821",
        user_name="Route Rider One",
        vehicle_plate="SBA8201A",
        settings_enabled=False,
        agent_mode="deterministic",
        patch_failure=False,
        assertions=assertions,
    )
    _run_transport_ai_route_calculation_script(tmp_path, script=script)


def test_route_calculations_preflight_failure_reports_missing_operational_approval(tmp_path):
    assertions = textwrap.dedent(
        """
        assert response.status_code == 409, response.text
        payload = response.json()
        assert payload["ok"] is False
        assert payload["run_key"] is None
        assert [issue["code"] for issue in payload["issues"]] == ["transport_ai_operational_approval_missing"]

        with SessionLocal() as session:
            assignment = session.get(TransportAssignment, seeded["assignment_id"])
            runs = session.execute(
                select(TransportAIRun).where(TransportAIRun.service_date == date.fromisoformat("2026-06-06"))
            ).scalars().all()

        assert assignment is not None
        assert assignment.status == "confirmed"
        assert assignment.vehicle_id == seeded["vehicle_id"]
        assert runs == []
        """
    ).strip()
    script = _build_route_calculation_script(
        service_date="2026-06-06",
        project_name="PAIR82F",
        user_key="R826",
        user_name="Route Rider Six",
        vehicle_plate="SBA8206A",
        settings_enabled=True,
        operational_approval_evidence=None,
        agent_mode="deterministic",
        patch_failure=False,
        assertions=assertions,
    )
    _run_transport_ai_route_calculation_script(tmp_path, script=script)


def test_route_calculations_preflight_failure_reports_concurrency_limit(tmp_path):
    assertions = textwrap.dedent(
        """
        assert response.status_code == 409, response.text
        payload = response.json()
        assert payload["ok"] is False
        assert payload["run_key"] is None
        assert [issue["code"] for issue in payload["issues"]] == ["transport_ai_concurrency_limit_reached"]

        with SessionLocal() as session:
            assignment = session.get(TransportAssignment, seeded["assignment_id"])
            runs = session.execute(
                select(TransportAIRun).where(TransportAIRun.service_date == date.fromisoformat("2026-06-07"))
            ).scalars().all()

        assert assignment is not None
        assert assignment.status == "confirmed"
        assert assignment.vehicle_id == seeded["vehicle_id"]
        assert runs == []
        """
    ).strip()
    script = _build_route_calculation_script(
        service_date="2026-06-07",
        project_name="PAIR82G",
        user_key="R827",
        user_name="Route Rider Seven",
        vehicle_plate="SBA8207A",
        settings_enabled=True,
        max_concurrent_runs=1,
        mocked_active_run_count=1,
        agent_mode="deterministic",
        patch_failure=False,
        assertions=assertions,
    )
    _run_transport_ai_route_calculation_script(tmp_path, script=script)


def test_route_calculations_success_saves_baseline_resets_pending_and_creates_suggestion(tmp_path):
    assertions = textwrap.dedent(
        """
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["ok"] is True
        assert payload["status"] == "proposed"
        assert payload["suggestion_ready"] is True
        assert payload["can_cancel_restore"] is True

        with SessionLocal() as session:
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == payload["run_key"])
            ).scalar_one()
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == payload["suggestion_key"])
            ).scalar_one()
            assignment = session.get(TransportAssignment, seeded["assignment_id"])
            audit_events = session.execute(
                select(CheckEvent)
                .where(CheckEvent.source == "transport_ai")
                .order_by(CheckEvent.id.asc())
            ).scalars().all()

        assert run.baseline_snapshot_json is not None
        assert run.baseline_assignments_json is not None
        assert run.baseline_vehicle_state_json is not None
        assert run.status == "proposed"
        assert run.completed_at is not None
        assert suggestion.run_id == run.id
        assert suggestion.status == "shown"
        assert assignment is not None
        assert assignment.status == "pending"
        assert assignment.vehicle_id is None
        assert {event.action for event in audit_events} >= {
            "run_create",
            "baseline_save",
            "requests_reset",
            "suggestion_gen",
        }

        combined_audit_text = "\\n".join(
            f"{event.message or ''}\\n{event.details or ''}"
            for event in audit_events
        )
        assert payload["run_key"] in combined_audit_text
        assert payload["suggestion_key"] in combined_audit_text
        assert "sk-test-openai-token" not in combined_audit_text

        recent_ai_reasons = {
            event.reason
            for event in list_recent_transport_reevaluation_events(limit=10)
            if event.event_type == "transport_ai_route_calculation_changed"
        }
        recent_event_types = {
            event.event_type
            for event in list_recent_transport_reevaluation_events(limit=10)
        }
        assert recent_ai_reasons >= {
            "run_created",
            "baseline_saved",
            "passengers_reset",
            "suggestion_generated",
        }
        assert "transport_assignment_changed" in recent_event_types
        assert "transport_operational_review_changed" in recent_event_types
        assert "transport_ai_route_calculation_changed" in recent_event_types
        """
    ).strip()
    script = _build_route_calculation_script(
        service_date="2026-06-02",
        project_name="PAIR82B",
        user_key="R822",
        user_name="Route Rider Two",
        vehicle_plate="SBA8202A",
        settings_enabled=True,
        agent_mode="deterministic",
        patch_failure=False,
        assertions=assertions,
    )
    _run_transport_ai_route_calculation_script(tmp_path, script=script)


def test_route_calculations_failure_after_reset_restores_baseline(tmp_path):
    assertions = textwrap.dedent(
        """
        assert response.status_code == 500, response.text
        payload = response.json()
        assert payload["ok"] is False
        assert payload["status"] == "failed"
        assert payload["can_cancel_restore"] is False
        assert "Baseline restored" in payload["message"]

        with SessionLocal() as session:
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == payload["run_key"])
            ).scalar_one()
            assignment = session.get(TransportAssignment, seeded["assignment_id"])
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.run_id == run.id)
            ).scalar_one_or_none()

        assert run.status == "failed"
        assert assignment is not None
        assert assignment.status == "confirmed"
        assert assignment.vehicle_id == seeded["vehicle_id"]
        assert suggestion is None
        """
    ).strip()
    script = _build_route_calculation_script(
        service_date="2026-06-03",
        project_name="PAIR82C",
        user_key="R823",
        user_name="Route Rider Three",
        vehicle_plate="SBA8203A",
        settings_enabled=True,
        agent_mode="deterministic",
        patch_failure=True,
        assertions=assertions,
    )
    _run_transport_ai_route_calculation_script(tmp_path, script=script)


def test_route_calculations_agent_mode_uses_persisted_llm_snapshot(tmp_path):
    assertions = textwrap.dedent(
        """
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["ok"] is True
        assert payload["status"] == "proposed"
        assert payload["suggestion_ready"] is True
        assert "deepseek-runtime-secret-4321" not in response.text

        with SessionLocal() as session:
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == payload["run_key"])
            ).scalar_one()
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == payload["suggestion_key"])
            ).scalar_one()
            audit_events = session.execute(
                select(CheckEvent)
                .where(CheckEvent.source == "transport_ai")
                .order_by(CheckEvent.id.asc())
            ).scalars().all()

        assert run.status == "proposed"
        assert run.llm_provider == "deepseek"
        assert run.llm_model == "deepseek-v4-pro"
        assert run.llm_reasoning_effort == "high"
        assert run.openai_model == "deepseek-v4-pro"
        assert suggestion.run_id == run.id

        combined_audit_text = "\\n".join(
            f"{event.message or ''}\\n{event.details or ''}"
            for event in audit_events
        )
        assert '"llm_provider":"deepseek"' in combined_audit_text
        assert '"llm_model":"deepseek-v4-pro"' in combined_audit_text
        assert "deepseek-runtime-secret-4321" not in combined_audit_text
        """
    ).strip()
    script = _build_route_calculation_script(
        service_date="2026-06-04",
        project_name="PAIR82D",
        user_key="R824",
        user_name="Route Rider Four",
        vehicle_plate="SBA8204A",
        settings_enabled=True,
        agent_mode="agent",
        persisted_llm_provider="deepseek",
        persisted_llm_api_key="deepseek-runtime-secret-4321",
        patch_failure=False,
        patch_success=True,
        assertions=assertions,
    )
    _run_transport_ai_route_calculation_script(tmp_path, script=script)


def test_route_calculations_agent_mode_reports_missing_project_llm_settings_as_controlled_preflight_failure(tmp_path):
    assertions = textwrap.dedent(
        """
        assert response.status_code == 409, response.text
        payload = response.json()
        assert payload["ok"] is False
        assert payload["status"] == "failed"
        assert payload["run_key"] is not None
        assert payload["can_cancel_restore"] is False
        assert any(issue["code"] == "transport_ai_llm_settings_missing" for issue in payload["issues"])

        with SessionLocal() as session:
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == payload["run_key"])
            ).scalar_one()
            assignment = session.get(TransportAssignment, seeded["assignment_id"])
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.run_id == run.id)
            ).scalar_one_or_none()

        assert run.status == "failed"
        assert assignment is not None
        assert assignment.status == "confirmed"
        assert assignment.vehicle_id == seeded["vehicle_id"]
        assert suggestion is None
        """
    ).strip()
    script = _build_route_calculation_script(
        service_date="2026-06-05",
        project_name="PAIR82E",
        user_key="R825",
        user_name="Route Rider Five",
        vehicle_plate="SBA8205A",
        settings_enabled=True,
        agent_mode="agent",
        patch_failure=False,
        assertions=assertions,
    )
    _run_transport_ai_route_calculation_script(tmp_path, script=script)
