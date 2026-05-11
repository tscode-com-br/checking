import os
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _build_transport_ai_suggestion_commands_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(REPO_ROOT),
            "APP_ENV": "development",
            "DATABASE_URL": f"sqlite+pysqlite:///{(tmp_path / 'transport_ai_suggestion_commands.db').as_posix()}",
            "FORMS_URL": "https://example.com/form",
            "DEVICE_SHARED_KEY": "device-test-key",
            "MOBILE_APP_SHARED_KEY": "mobile-test-key",
            "PROVIDER_SHARED_KEY": "provider-test-key",
            "ADMIN_SESSION_SECRET": "test-admin-session-secret",
            "BOOTSTRAP_ADMIN_KEY": "HR70",
            "BOOTSTRAP_ADMIN_NAME": "Transport AI Suggestion Admin",
            "BOOTSTRAP_ADMIN_PASSWORD": "eAcacdLe2",
            "FORMS_QUEUE_ENABLED": "false",
            "TRANSPORT_EXPORTS_DIR": str(tmp_path / "transport_ai_suggestion_commands_exports"),
            "TRANSPORT_AI_ENABLED": "true",
            "TRANSPORT_AI_AGENT_MODE": "deterministic",
            "TRANSPORT_AI_ROUTE_PROVIDER": "fake",
            "TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE": "phase8-loadtest-2026-05-05",
            "TRANSPORT_AI_MAX_CONCURRENT_RUNS": "1",
            "OPENAI_API_KEY": "sk-test-openai-token",
        }
    )
    return env


def _run_transport_ai_suggestion_commands_script(tmp_path: Path, *, script: str) -> None:
    env = _build_transport_ai_suggestion_commands_env(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "transport-ai-suggestion-commands-ok" in result.stdout


def _build_transport_ai_suggestion_script(
    *,
    service_date: str,
    project_name: str,
    user_key: str,
    user_name: str,
    vehicle_plate: str | None,
    seed_existing_assignment: bool,
    request_kind: str = "extra",
    steps: str,
) -> str:
    indented_steps = textwrap.indent(steps, "        ")
    vehicle_plate_literal = repr(vehicle_plate)

    return textwrap.dedent(
        f"""
        import json
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
            TransportAIAppliedRouteStop,
            TransportAIRun,
            TransportAISuggestion,
            TransportAssignment,
            TransportRequest,
            TransportVehicleSchedule,
            TransportVehicleScheduleException,
            User,
            Vehicle,
        )
        from sistema.app.services.transport_reevaluation_events import (
            clear_transport_reevaluation_events,
            list_recent_transport_reevaluation_events,
        )


        def _fixture_timestamp():
            return datetime(2026, 5, 6, 8, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))


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
            selected_weekdays_json = None
            recurrence_kind = "single_date"
            single_date = service_date
            if {request_kind!r} == "regular":
                weekday = service_date.weekday()
                if weekday > 4:
                    raise AssertionError("regular transport AI suggestion fixtures must use a weekday service date")
                selected_weekdays_json = json.dumps([weekday])
                recurrence_kind = "weekday"
                single_date = None
            elif {request_kind!r} == "weekend":
                weekday = service_date.weekday()
                if weekday not in {{5, 6}}:
                    raise AssertionError("weekend transport AI suggestion fixtures must use a Saturday or Sunday service date")
                selected_weekdays_json = json.dumps([weekday])
                recurrence_kind = "weekend"
                single_date = None

            request = TransportRequest(
                user_id=user_id,
                request_kind={request_kind!r},
                recurrence_kind=recurrence_kind,
                requested_time="08:00",
                selected_weekdays_json=selected_weekdays_json,
                single_date=single_date,
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
            return _create_vehicle_candidate_for_scope(
                session,
                placa=placa,
                service_scope="extra",
                service_date=service_date,
            )


        def _create_vehicle_candidate_for_scope(
            session,
            *,
            placa: str,
            service_scope: str,
            service_date: date,
        ) -> Vehicle:
            vehicle = Vehicle(
                placa=placa,
                tipo="carro",
                color="white",
                lugares=4,
                tolerance=0,
                service_scope=service_scope,
            )
            session.add(vehicle)
            session.flush()

            if service_scope == "extra":
                schedule_specs = [
                    ("home_to_work", "single_date", None, "07:30"),
                ]
            elif service_scope == "regular":
                schedule_specs = [
                    ("home_to_work", "weekday", None, None),
                    ("work_to_home", "weekday", None, None),
                ]
            elif service_scope == "weekend":
                weekday = service_date.weekday()
                if weekday not in {{5, 6}}:
                    raise AssertionError("weekend vehicle fixtures must use a Saturday or Sunday service date")
                schedule_specs = [
                    ("home_to_work", "matching_weekday", weekday, None),
                    ("work_to_home", "matching_weekday", weekday, None),
                ]
            else:
                raise AssertionError(f"unsupported vehicle fixture scope: {{service_scope}}")

            for route_kind, recurrence_kind, weekday, departure_time in schedule_specs:
                session.add(
                    TransportVehicleSchedule(
                        vehicle_id=vehicle.id,
                        service_scope=service_scope,
                        route_kind=route_kind,
                        recurrence_kind=recurrence_kind,
                        service_date=service_date,
                        weekday=weekday,
                        departure_time=departure_time,
                        is_active=True,
                        created_at=_fixture_timestamp(),
                        updated_at=_fixture_timestamp(),
                    )
                )

            session.flush()
            return vehicle


        def _create_assignment(session, *, request_id: int, service_date: date, vehicle_id: int, assigned_by_admin_id: int) -> TransportAssignment:
            assignment = TransportAssignment(
                request_id=request_id,
                service_date=service_date,
                route_kind="home_to_work",
                vehicle_id=vehicle_id,
                status="confirmed",
                response_message="confirmed-for-ai-suggestion-command",
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


        def _seed_transport_ai_suggestion_scenario(
            *,
            service_date: date,
            project_name: str,
            user_key: str,
            user_name: str,
            vehicle_plate: str | None,
            seed_existing_assignment: bool,
            request_kind: str,
        ):
            with SessionLocal() as session:
                _configure_transport_settings(session)
                admin_user = _create_admin_user(session, chave=f"A{{user_key[1:]}}", nome_completo=f"Admin {{user_name}}")
                project = _create_project(session, name=project_name)
                rider = _create_user(session, chave=user_key, nome=user_name, projeto=project.name)
                request = _create_transport_request(session, user_id=rider.id, service_date=service_date)
                seeded = {{
                    "request_id": request.id,
                    "vehicle_id": None,
                    "assignment_id": None,
                }}

                if seed_existing_assignment:
                    if {request_kind!r} != "extra":
                        raise AssertionError("seed_existing_assignment fixtures are only supported for extra requests")
                    vehicle = _create_extra_vehicle_candidate(
                        session,
                        placa=str(vehicle_plate),
                        service_date=service_date,
                    )
                    assignment = _create_assignment(
                        session,
                        request_id=request.id,
                        service_date=service_date,
                        vehicle_id=vehicle.id,
                        assigned_by_admin_id=admin_user.id,
                    )
                    seeded["vehicle_id"] = vehicle.id
                    seeded["assignment_id"] = assignment.id

                session.commit()
                return seeded


        def _dump_transport_ai_payload(payload) -> str:
            return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


        def _rebuild_transport_ai_change_summary(plan_payload: dict[str, object]) -> dict[str, object]:
            action_count_keys = {{
                "keep": "keep_count",
                "create": "create_count",
                "update": "update_count",
                "remove_from_day": "remove_from_day_count",
            }}
            change_counts = {{count_key: 0 for count_key in action_count_keys.values()}}
            counts_by_vehicle_type: dict[str, dict[str, object]] = {{}}

            for action in plan_payload.get("vehicle_actions", []):
                action_type = str(action.get("action_type") or "").strip()
                count_key = action_count_keys.get(action_type)
                if count_key is None:
                    continue
                change_counts[count_key] += 1

                state = action.get("after") or action.get("before") or {{}}
                vehicle_type = str(state.get("vehicle_type") or "carro")
                type_counts = counts_by_vehicle_type.setdefault(
                    vehicle_type,
                    {{
                        "vehicle_type": vehicle_type,
                        "keep_count": 0,
                        "create_count": 0,
                        "update_count": 0,
                        "remove_from_day_count": 0,
                        "total_count": 0,
                    }},
                )
                type_counts[count_key] += 1
                type_counts["total_count"] += 1

            return {{
                "total_vehicle_actions": sum(change_counts.values()),
                **change_counts,
                "by_vehicle_type": [counts_by_vehicle_type[key] for key in sorted(counts_by_vehicle_type)],
            }}


        def _rewrite_transport_ai_suggestion_as_vehicle_update(
            suggestion_key: str,
            *,
            vehicle_id: int,
            vehicle_updates: dict[str, object],
            rationale: str,
            omit_after_fields: list[str] | None = None,
        ) -> None:
            with SessionLocal() as session:
                suggestion = session.execute(
                    select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
                ).scalar_one()
                vehicle = session.get(Vehicle, vehicle_id)
                assert vehicle is not None

                plan_payload = json.loads(suggestion.agent_plan_json)
                vehicle_ref = f"existing:{{vehicle.id}}"
                existing_action = dict(plan_payload["vehicle_actions"][0])
                before_state = dict(existing_action.get("before") or {{}})
                before_state.update(
                    {{
                        "vehicle_ref": vehicle_ref,
                        "vehicle_id": vehicle.id,
                        "schedule_id": existing_action.get("schedule_id"),
                        "client_vehicle_key": vehicle_ref,
                        "service_scope": existing_action.get("service_scope") or vehicle.service_scope,
                        "route_kind": plan_payload["route_kind"],
                        "vehicle_type": vehicle.tipo,
                        "plate": vehicle.placa,
                        "color": vehicle.color,
                        "capacity": vehicle.lugares,
                        "tolerance": vehicle.tolerance,
                    }}
                )
                after_state = dict(before_state)
                after_state.update(vehicle_updates)
                for field_name in omit_after_fields or []:
                    after_state.pop(field_name, None)

                plan_payload["vehicle_actions"] = [
                    {{
                        "action_key": f"update:existing:{{vehicle.id}}",
                        "action_type": "update",
                        "service_scope": existing_action.get("service_scope") or vehicle.service_scope,
                        "vehicle_id": vehicle.id,
                        "schedule_id": existing_action.get("schedule_id"),
                        "client_vehicle_key": vehicle_ref,
                        "before": before_state,
                        "after": after_state,
                        "rationale": rationale,
                        "cost_delta": 0.0,
                    }}
                ]

                for allocation in plan_payload.get("passenger_allocations", []):
                    allocation["vehicle_ref"] = vehicle_ref
                    allocation["rationale"] = rationale

                for itinerary in plan_payload.get("route_itineraries", []):
                    itinerary["vehicle_ref"] = vehicle_ref
                    itinerary["vehicle_id"] = vehicle.id
                    itinerary["client_vehicle_key"] = vehicle_ref
                    itinerary["vehicle_type"] = after_state.get("vehicle_type")
                    itinerary["plate"] = after_state.get("plate")

                plan_payload["change_summary"] = _rebuild_transport_ai_change_summary(plan_payload)

                suggestion.agent_plan_json = _dump_transport_ai_payload(plan_payload)
                suggestion.vehicle_actions_json = _dump_transport_ai_payload(plan_payload.get("vehicle_actions", []))
                suggestion.assignment_actions_json = _dump_transport_ai_payload(plan_payload.get("passenger_allocations", []))
                suggestion.route_itineraries_json = _dump_transport_ai_payload(plan_payload.get("route_itineraries", []))
                suggestion.change_summary_json = _dump_transport_ai_payload(plan_payload.get("change_summary", {{}}))
                suggestion.validation_issues_json = _dump_transport_ai_payload(plan_payload.get("validation_issues", []))
                session.commit()


        def _rewrite_transport_ai_suggestion_as_vehicle_remove_from_day(
            suggestion_key: str,
            *,
            vehicle_id: int,
            rationale: str,
        ) -> None:
            with SessionLocal() as session:
                suggestion = session.execute(
                    select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
                ).scalar_one()
                vehicle = session.get(Vehicle, vehicle_id)
                assert vehicle is not None
                schedules = session.execute(
                    select(TransportVehicleSchedule)
                    .where(
                        TransportVehicleSchedule.vehicle_id == vehicle.id,
                        TransportVehicleSchedule.is_active.is_(True),
                    )
                    .order_by(TransportVehicleSchedule.id.asc())
                ).scalars().all()
                assert schedules

                primary_schedule = schedules[0]
                vehicle_ref = f"existing:{{vehicle.id}}"
                plan_payload = json.loads(suggestion.agent_plan_json)
                remove_action = {{
                    "action_key": f"remove_from_day:existing:{{vehicle.id}}",
                    "action_type": "remove_from_day",
                    "service_scope": primary_schedule.service_scope,
                    "vehicle_id": vehicle.id,
                    "schedule_id": primary_schedule.id,
                    "client_vehicle_key": vehicle_ref,
                    "before": {{
                        "vehicle_ref": vehicle_ref,
                        "vehicle_id": vehicle.id,
                        "schedule_id": primary_schedule.id,
                        "client_vehicle_key": vehicle_ref,
                        "service_scope": primary_schedule.service_scope,
                        "route_kind": plan_payload["route_kind"],
                        "vehicle_type": vehicle.tipo,
                        "plate": vehicle.placa,
                        "color": vehicle.color,
                        "capacity": vehicle.lugares,
                        "tolerance": vehicle.tolerance,
                    }},
                    "after": {{}},
                    "rationale": rationale,
                    "cost_delta": 0.0,
                }}
                existing_actions = [dict(action) for action in plan_payload.get("vehicle_actions", [])]
                plan_payload["vehicle_actions"] = [remove_action, *existing_actions]
                plan_payload["change_summary"] = _rebuild_transport_ai_change_summary(plan_payload)

                suggestion.agent_plan_json = _dump_transport_ai_payload(plan_payload)
                suggestion.vehicle_actions_json = _dump_transport_ai_payload(plan_payload.get("vehicle_actions", []))
                suggestion.assignment_actions_json = _dump_transport_ai_payload(plan_payload.get("passenger_allocations", []))
                suggestion.route_itineraries_json = _dump_transport_ai_payload(plan_payload.get("route_itineraries", []))
                suggestion.change_summary_json = _dump_transport_ai_payload(plan_payload.get("change_summary", {{}}))
                suggestion.validation_issues_json = _dump_transport_ai_payload(plan_payload.get("validation_issues", []))
                session.commit()


        def _rewrite_transport_ai_suggestion_as_keep_existing_vehicle(
            suggestion_key: str,
            *,
            vehicle_id: int,
            rationale: str,
        ) -> None:
            with SessionLocal() as session:
                suggestion = session.execute(
                    select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
                ).scalar_one()
                vehicle = session.get(Vehicle, vehicle_id)
                assert vehicle is not None
                schedules = session.execute(
                    select(TransportVehicleSchedule)
                    .where(
                        TransportVehicleSchedule.vehicle_id == vehicle.id,
                        TransportVehicleSchedule.is_active.is_(True),
                    )
                    .order_by(TransportVehicleSchedule.id.asc())
                ).scalars().all()
                assert schedules

                primary_schedule = schedules[0]
                vehicle_ref = f"existing:{{vehicle.id}}"
                plan_payload = json.loads(suggestion.agent_plan_json)
                keep_action = {{
                    "action_key": f"keep:existing:{{vehicle.id}}",
                    "action_type": "keep",
                    "service_scope": primary_schedule.service_scope,
                    "vehicle_id": vehicle.id,
                    "schedule_id": primary_schedule.id,
                    "client_vehicle_key": vehicle_ref,
                    "before": {{
                        "vehicle_ref": vehicle_ref,
                        "vehicle_id": vehicle.id,
                        "schedule_id": primary_schedule.id,
                        "client_vehicle_key": vehicle_ref,
                        "service_scope": primary_schedule.service_scope,
                        "route_kind": plan_payload["route_kind"],
                        "vehicle_type": vehicle.tipo,
                        "plate": vehicle.placa,
                        "color": vehicle.color,
                        "capacity": vehicle.lugares,
                        "tolerance": vehicle.tolerance,
                    }},
                    "after": {{}},
                    "rationale": rationale,
                    "cost_delta": 0.0,
                }}

                plan_payload["vehicle_actions"] = [keep_action]

                for allocation in plan_payload.get("passenger_allocations", []):
                    allocation["vehicle_ref"] = vehicle_ref
                    allocation["rationale"] = rationale

                for itinerary in plan_payload.get("route_itineraries", []):
                    itinerary["vehicle_ref"] = vehicle_ref
                    itinerary["vehicle_id"] = vehicle.id
                    itinerary["client_vehicle_key"] = vehicle_ref
                    itinerary["vehicle_type"] = vehicle.tipo
                    itinerary["plate"] = vehicle.placa

                plan_payload["change_summary"] = _rebuild_transport_ai_change_summary(plan_payload)

                suggestion.agent_plan_json = _dump_transport_ai_payload(plan_payload)
                suggestion.vehicle_actions_json = _dump_transport_ai_payload(plan_payload.get("vehicle_actions", []))
                suggestion.assignment_actions_json = _dump_transport_ai_payload(plan_payload.get("passenger_allocations", []))
                suggestion.route_itineraries_json = _dump_transport_ai_payload(plan_payload.get("route_itineraries", []))
                suggestion.change_summary_json = _dump_transport_ai_payload(plan_payload.get("change_summary", {{}}))
                suggestion.validation_issues_json = _dump_transport_ai_payload(plan_payload.get("validation_issues", []))
                session.commit()


        Base.metadata.create_all(bind=engine)
        settings.transport_ai_enabled = True
        settings.transport_ai_agent_mode = "deterministic"
        settings.transport_ai_route_provider = "fake"
        settings.transport_ai_operational_approval_evidence = "phase8-loadtest-2026-05-05"
        settings.transport_ai_max_concurrent_runs = 1
        settings.here_api_key = "test-here-api-key"
        clear_transport_reevaluation_events()
        seeded = _seed_transport_ai_suggestion_scenario(
            service_date=date.fromisoformat({service_date!r}),
            project_name={project_name!r},
            user_key={user_key!r},
            user_name={user_name!r},
            vehicle_plate={vehicle_plate_literal},
            seed_existing_assignment={str(seed_existing_assignment)},
            request_kind={request_kind!r},
        )

        with TestClient(app) as client:
            _login_transport(client)
            start_response = client.post(
                "/api/transport/ai/route-calculations",
                json={{
                    "service_date": {service_date!r},
                    "route_kind": "home_to_work",
                    "earliest_boarding_time": "06:50",
                    "arrival_at_work_time": "07:45",
                }},
            )
            assert start_response.status_code == 201, start_response.text
            start_payload = start_response.json()

            status_response = client.get(f"/api/transport/ai/route-calculations/{{start_payload['run_key']}}")
            assert status_response.status_code == 200, status_response.text
            status_payload = status_response.json()
            suggestion_key = status_payload["suggestion_key"]
            assert suggestion_key is not None

{indented_steps}

        print("transport-ai-suggestion-commands-ok")
        """
    ).lstrip()


def test_transport_ai_latest_suggestion_returns_not_found_when_none_exists(tmp_path):
    script = textwrap.dedent(
        """
        from fastapi.testclient import TestClient

        from sistema.app.main import app
        from sistema.app.database import Base, engine


        Base.metadata.create_all(bind=engine)

        with TestClient(app) as client:
            login = client.post(
                "/api/transport/auth/verify",
                json={"chave": "HR70", "senha": "eAcacdLe2"},
            )
            assert login.status_code == 200, login.text
            assert login.json()["authenticated"] is True

            latest = client.get(
                "/api/transport/ai/suggestions/latest",
                params={"service_date": "2026-06-10", "route_kind": "home_to_work"},
            )
            assert latest.status_code == 404, latest.text
            assert latest.json()["detail"]["message"] == "Transport AI suggestion not found."

        print("transport-ai-suggestion-commands-ok")
        """
    ).lstrip()
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_save_and_latest_return_saved_suggestion(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert status_payload["suggestion"]["status"] == "shown"

        clear_transport_reevaluation_events()

        first_save = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/save")
        assert first_save.status_code == 200, first_save.text
        first_save_payload = first_save.json()
        assert first_save_payload["status"] == "saved"
        assert first_save_payload["suggestion"]["status"] == "saved"
        assert first_save_payload["can_save"] is False
        assert first_save_payload["can_apply"] is True
        assert first_save_payload["can_cancel_restore"] is True

        second_save = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/save")
        assert second_save.status_code == 200, second_save.text
        assert second_save.json()["status"] == "saved"

        latest = client.get(
            "/api/transport/ai/suggestions/latest",
            params={"service_date": "2026-06-11", "route_kind": "home_to_work"},
        )
        assert latest.status_code == 200, latest.text
        latest_payload = latest.json()
        assert latest_payload["run_key"] == start_payload["run_key"]
        assert latest_payload["suggestion_key"] == suggestion_key
        assert latest_payload["status"] == "saved"
        assert latest_payload["suggestion"]["status"] == "saved"

        with SessionLocal() as session:
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == start_payload["run_key"])
            ).scalar_one()
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            assignment = session.get(TransportAssignment, seeded["assignment_id"])
            audit_events = session.execute(
                select(CheckEvent)
                .where(CheckEvent.source == "transport_ai")
                .order_by(CheckEvent.id.asc())
            ).scalars().all()

        assert run.status == "saved"
        assert suggestion.status == "saved"
        assert suggestion.saved_at is not None
        assert assignment is not None
        assert assignment.status == "pending"
        assert assignment.vehicle_id is None
        assert any(event.action == "suggestion_save" for event in audit_events)

        combined_audit_text = "\\n".join(
            f"{event.message or ''}\\n{event.details or ''}"
            for event in audit_events
        )
        assert start_payload["run_key"] in combined_audit_text
        assert suggestion_key in combined_audit_text
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
        assert "suggestion_saved" in recent_ai_reasons
        assert "transport_ai_route_calculation_changed" in recent_event_types
        assert "transport_operational_review_changed" in recent_event_types
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-11",
        project_name="PAIR84A",
        user_key="R841",
        user_name="Suggestion Save Rider",
        vehicle_plate="SBA8401A",
        seed_existing_assignment=True,
        request_kind="extra",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_cancel_restores_baseline_and_is_idempotent(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert seeded["assignment_id"] is not None
        assert seeded["vehicle_id"] is not None

        clear_transport_reevaluation_events()

        first_cancel = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/cancel")
        assert first_cancel.status_code == 200, first_cancel.text
        first_cancel_payload = first_cancel.json()
        assert first_cancel_payload["status"] == "cancelled"
        assert first_cancel_payload["suggestion"]["status"] == "discarded"
        assert first_cancel_payload["can_apply"] is False
        assert first_cancel_payload["can_cancel_restore"] is False

        second_cancel = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/cancel")
        assert second_cancel.status_code == 200, second_cancel.text
        assert second_cancel.json()["status"] == "cancelled"

        with SessionLocal() as session:
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == start_payload["run_key"])
            ).scalar_one()
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            assignment = session.get(TransportAssignment, seeded["assignment_id"])
            audit_events = session.execute(
                select(CheckEvent)
                .where(CheckEvent.source == "transport_ai")
                .order_by(CheckEvent.id.asc())
            ).scalars().all()

        assert run.status == "cancelled"
        assert suggestion.status == "discarded"
        assert suggestion.discarded_at is not None
        assert assignment is not None
        assert assignment.status == "confirmed"
        assert assignment.vehicle_id == seeded["vehicle_id"]
        assert any(event.action == "suggestion_drop" for event in audit_events)

        recent_ai_reasons = {
            event.reason
            for event in list_recent_transport_reevaluation_events(limit=10)
            if event.event_type == "transport_ai_route_calculation_changed"
        }
        recent_event_types = {
            event.event_type
            for event in list_recent_transport_reevaluation_events(limit=10)
        }
        assert "suggestion_discarded" in recent_ai_reasons
        assert "transport_assignment_changed" in recent_event_types
        assert "transport_operational_review_changed" in recent_event_types
        assert "transport_ai_route_calculation_changed" in recent_event_types
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-12",
        project_name="PAIR84B",
        user_key="R842",
        user_name="Suggestion Cancel Rider",
        vehicle_plate="SBA8402A",
        seed_existing_assignment=True,
        request_kind="extra",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_creates_vehicle_assignments_and_route_stops(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert status_payload["suggestion"]["plan"]["vehicle_actions"]
        assert status_payload["suggestion"]["plan"]["vehicle_actions"][0]["action_type"] == "create"

        clear_transport_reevaluation_events()

        import sistema.app.routers.transport_ai as transport_ai_router_module

        proposal_call_order = []
        original_validate_transport_operational_proposal = transport_ai_router_module.validate_transport_operational_proposal
        original_approve_transport_operational_proposal = transport_ai_router_module.approve_transport_operational_proposal
        original_apply_transport_operational_proposal = transport_ai_router_module.apply_transport_operational_proposal

        def _tracked_validate_transport_operational_proposal(db, *, proposal, actor, validated_at=None):
            proposal_call_order.append("validate")
            return original_validate_transport_operational_proposal(
                db,
                proposal=proposal,
                actor=actor,
                validated_at=validated_at,
            )

        def _tracked_approve_transport_operational_proposal(db, *, proposal, actor, approved_at=None):
            proposal_call_order.append("approve")
            return original_approve_transport_operational_proposal(
                db,
                proposal=proposal,
                actor=actor,
                approved_at=approved_at,
            )

        def _tracked_apply_transport_operational_proposal(db, *, proposal, actor, applied_at=None):
            proposal_call_order.append("apply")
            return original_apply_transport_operational_proposal(
                db,
                proposal=proposal,
                actor=actor,
                applied_at=applied_at,
            )

        transport_ai_router_module.validate_transport_operational_proposal = _tracked_validate_transport_operational_proposal
        transport_ai_router_module.approve_transport_operational_proposal = _tracked_approve_transport_operational_proposal
        transport_ai_router_module.apply_transport_operational_proposal = _tracked_apply_transport_operational_proposal
        try:
            first_apply = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
        finally:
            transport_ai_router_module.validate_transport_operational_proposal = original_validate_transport_operational_proposal
            transport_ai_router_module.approve_transport_operational_proposal = original_approve_transport_operational_proposal
            transport_ai_router_module.apply_transport_operational_proposal = original_apply_transport_operational_proposal

        assert first_apply.status_code == 200, first_apply.text
        first_apply_payload = first_apply.json()
        assert first_apply_payload["status"] == "applied"
        assert first_apply_payload["suggestion"]["status"] == "applied"
        assert first_apply_payload["can_apply"] is False
        assert first_apply_payload["can_cancel_restore"] is False
        assert proposal_call_order == ["validate", "approve", "apply"]
        planned_pickup_time = first_apply_payload["suggestion"]["plan"]["passenger_allocations"][0]["scheduled_pickup_time"]

        applied_plan_stops = first_apply_payload["suggestion"]["plan"]["route_itineraries"][0]["stops"]

        second_apply = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
        assert second_apply.status_code == 200, second_apply.text
        assert second_apply.json()["status"] == "applied"

        latest = client.get(
            "/api/transport/ai/suggestions/latest",
            params={"service_date": "2026-06-13", "route_kind": "home_to_work"},
        )
        assert latest.status_code == 404, latest.text

        with SessionLocal() as session:
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == start_payload["run_key"])
            ).scalar_one()
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            assignment = session.execute(
                select(TransportAssignment).where(
                    TransportAssignment.request_id == seeded["request_id"],
                    TransportAssignment.service_date == date.fromisoformat("2026-06-13"),
                    TransportAssignment.route_kind == "home_to_work",
                )
            ).scalar_one()
            vehicle = session.get(Vehicle, assignment.vehicle_id)
            schedules = session.execute(
                select(TransportVehicleSchedule)
                .where(TransportVehicleSchedule.vehicle_id == vehicle.id)
                .order_by(TransportVehicleSchedule.id.asc())
            ).scalars().all()
            applied_stops = session.execute(
                select(TransportAIAppliedRouteStop)
                .where(TransportAIAppliedRouteStop.suggestion_id == suggestion.id)
                .order_by(TransportAIAppliedRouteStop.stop_order.asc())
            ).scalars().all()
            audit_events = session.execute(
                select(CheckEvent)
                .where(CheckEvent.source == "transport_ai")
                .order_by(CheckEvent.id.asc())
            ).scalars().all()

        proposal_payload = json.loads(suggestion.transport_proposal_json)
        proposal_audit_actions = [entry["action"] for entry in proposal_payload["audit_trail"]]

        dashboard = client.get(
            "/api/transport/dashboard",
            params={"service_date": "2026-06-13", "route_kind": "home_to_work"},
        )
        assert dashboard.status_code == 200, dashboard.text
        dashboard_payload = dashboard.json()
        dashboard_rows = [row for row in dashboard_payload["extra_vehicles"] if row["id"] == vehicle.id]
        dashboard_request_row = next(
            row for row in dashboard_payload["extra_requests"] if row["id"] == seeded["request_id"]
        )

        assert run.status == "applied"
        assert suggestion.status == "applied"
        assert assignment.status == "confirmed"
        assert assignment.boarding_time == planned_pickup_time
        assert vehicle is not None
        assert vehicle.placa is not None
        assert vehicle.placa.startswith("PLATE ")
        assert vehicle.tipo == "carro"
        assert vehicle.lugares == 4
        assert vehicle.tolerance == 5
        assert len(schedules) == 1
        assert schedules[0].service_scope == "extra"
        assert schedules[0].route_kind == "home_to_work"
        assert schedules[0].recurrence_kind == "single_date"
        assert schedules[0].service_date == date.fromisoformat("2026-06-13")
        assert len(applied_stops) == len(applied_plan_stops)
        assert applied_stops[0].stop_order == 1
        assert applied_stops[-1].stop_type == "destination"
        assert [stop.stop_type for stop in applied_stops] == [stop["stop_type"] for stop in applied_plan_stops]
        assert [stop.project_name for stop in applied_stops] == [stop["project_name"] for stop in applied_plan_stops]
        assert [stop.address for stop in applied_stops] == [stop["address"] for stop in applied_plan_stops]
        assert [stop.zip_code for stop in applied_stops] == [stop["zip_code"] for stop in applied_plan_stops]
        assert [stop.country_code for stop in applied_stops] == [stop["country_code"] for stop in applied_plan_stops]
        assert [stop.scheduled_time for stop in applied_stops] == [stop["scheduled_time"] for stop in applied_plan_stops]
        assert [stop.request_id for stop in applied_stops] == [stop["request_id"] for stop in applied_plan_stops]
        assert [stop.user_id for stop in applied_stops] == [stop["user_id"] for stop in applied_plan_stops]
        assert [stop.passenger_name for stop in applied_stops] == [stop["passenger_name"] for stop in applied_plan_stops]
        assert [stop.duration_from_previous_seconds for stop in applied_stops] == [
            stop["duration_from_previous_seconds"] for stop in applied_plan_stops
        ]
        assert [stop.distance_from_previous_meters for stop in applied_stops] == [
            stop["distance_from_previous_meters"] for stop in applied_plan_stops
        ]
        assert [round(stop.longitude, 6) for stop in applied_stops] == [round(stop["longitude"], 6) for stop in applied_plan_stops]
        assert [round(stop.latitude, 6) for stop in applied_stops] == [round(stop["latitude"], 6) for stop in applied_plan_stops]
        assert dashboard_rows and dashboard_rows[0]["placa"] == vehicle.placa
        assert dashboard_request_row["boarding_time"] == planned_pickup_time
        assert suggestion.proposal_key == proposal_payload["proposal_key"]
        assert suggestion.proposal_key != f"transport-ai-proposal:{start_payload['run_key']}"
        assert proposal_payload["origin"] == "agent"
        assert proposal_payload["proposal_status"] == "applied"
        assert proposal_payload["decisions"][0]["boarding_time"] == planned_pickup_time
        assert proposal_payload["replaces_proposal_key"] is None
        assert proposal_payload["audit_trail"][0]["message"] == "Proposal generated from an operational snapshot."
        assert proposal_payload["audit_trail"][0]["context"]["proposal_origin"] == "agent"
        assert proposal_payload["audit_trail"][0]["context"]["replaces_proposal_key"] is None
        assert proposal_audit_actions[0] == "generated"
        assert "validated" in proposal_audit_actions
        assert "approved" in proposal_audit_actions
        assert proposal_audit_actions[-1] == "applied"
        change_summary_payload = json.loads(suggestion.change_summary_json)
        assert change_summary_payload["apply_vehicle_create_count"] == 1
        assert change_summary_payload["apply_vehicle_create_audit"][0]["vehicle_id"] == vehicle.id
        assert change_summary_payload["apply_vehicle_create_audit"][0]["schedules"][0]["recurrence_kind"] == "single_date"
        assert any(event.action == "suggestion_apply" for event in audit_events)

        combined_audit_text = "\\n".join(
            f"{event.message or ''}\\n{event.details or ''}"
            for event in audit_events
        )
        assert start_payload["run_key"] in combined_audit_text
        assert suggestion_key in combined_audit_text
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
        assert "suggestion_applied" in recent_ai_reasons
        assert "transport_vehicle_supply_changed" in recent_event_types
        assert "transport_assignment_changed" in recent_event_types
        assert "transport_operational_review_changed" in recent_event_types
        assert "transport_ai_route_calculation_changed" in recent_event_types
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-13",
        project_name="PAIR84C",
        user_key="R843",
        user_name="Suggestion Apply Rider",
        vehicle_plate=None,
        seed_existing_assignment=False,
        request_kind="extra",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_rolls_back_applied_route_stops_when_later_step_fails(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert status_payload["suggestion"]["plan"]["vehicle_actions"][0]["action_type"] == "create"

        import sistema.app.routers.transport_ai as transport_ai_router_module

        original_set_transport_ai_suggestion_status = transport_ai_router_module.set_transport_ai_suggestion_status

        def _fail_after_route_stop_persist(db, *, suggestion, status, changed_at=None):
            raise RuntimeError("transport-ai-route-stop-persist-failed-after-write")

        transport_ai_router_module.set_transport_ai_suggestion_status = _fail_after_route_stop_persist
        try:
            try:
                client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
                raise AssertionError("apply should have raised after the simulated post-stop failure")
            except RuntimeError as exc:
                assert "transport-ai-route-stop-persist-failed-after-write" in str(exc)
        finally:
            transport_ai_router_module.set_transport_ai_suggestion_status = original_set_transport_ai_suggestion_status

        with SessionLocal() as session:
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == start_payload["run_key"])
            ).scalar_one()
            assignments = session.execute(
                select(TransportAssignment).where(
                    TransportAssignment.request_id == seeded["request_id"],
                    TransportAssignment.service_date == date.fromisoformat("2026-06-17"),
                    TransportAssignment.route_kind == "home_to_work",
                )
            ).scalars().all()
            vehicles = session.execute(
                select(Vehicle).where(Vehicle.placa.like("PLATE %"))
            ).scalars().all()
            schedules = session.execute(select(TransportVehicleSchedule)).scalars().all()
            applied_stops = session.execute(select(TransportAIAppliedRouteStop)).scalars().all()

        assert run.status == "proposed"
        assert suggestion.status == "shown"
        assert suggestion.applied_at is None
        assert len(assignments) == 1
        assert assignments[0].status == "pending"
        assert assignments[0].vehicle_id is None
        assert vehicles == []
        assert schedules == []
        assert applied_stops == []
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-17",
        project_name="PAIR93E",
        user_key="R935",
        user_name="Suggestion Stop Rollback Rider",
        vehicle_plate=None,
        seed_existing_assignment=False,
        request_kind="extra",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_blocks_when_request_state_drifts_before_apply(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"

        with SessionLocal() as session:
            drift_vehicle = _create_extra_vehicle_candidate(
                session,
                placa="DRF9301A",
                service_date=date.fromisoformat("2026-06-14"),
            )
            assignment = session.execute(
                select(TransportAssignment).where(
                    TransportAssignment.request_id == seeded["request_id"],
                    TransportAssignment.service_date == date.fromisoformat("2026-06-14"),
                    TransportAssignment.route_kind == "home_to_work",
                )
            ).scalar_one()
            assignment.status = "confirmed"
            assignment.vehicle_id = drift_vehicle.id
            assignment.updated_at = _fixture_timestamp()
            session.commit()

        apply_response = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
        assert apply_response.status_code == 409, apply_response.text
        apply_payload = apply_response.json()
        assert apply_payload["status"] == "proposed"
        assert apply_payload["suggestion"]["status"] == "shown"
        assert any(issue["code"] == "request_not_pending" for issue in apply_payload["issues"])

        with SessionLocal() as session:
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == start_payload["run_key"])
            ).scalar_one()
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            assignment = session.execute(
                select(TransportAssignment).where(
                    TransportAssignment.request_id == seeded["request_id"],
                    TransportAssignment.service_date == date.fromisoformat("2026-06-14"),
                    TransportAssignment.route_kind == "home_to_work",
                )
            ).scalar_one()

        proposal_payload = json.loads(suggestion.transport_proposal_json)
        proposal_audit_actions = [entry["action"] for entry in proposal_payload["audit_trail"]]

        assert run.status == "proposed"
        assert suggestion.status == "shown"
        assert suggestion.proposal_key == proposal_payload["proposal_key"]
        assert assignment.status == "confirmed"
        assert proposal_payload["origin"] == "agent"
        assert proposal_payload["proposal_status"] == "draft"
        assert proposal_audit_actions[0] == "generated"
        assert proposal_audit_actions[-1] == "validated"
        assert proposal_payload["audit_trail"][-1]["outcome"] == "blocked"
        assert "request_not_pending" in proposal_payload["validation_issues"][0]["code"]
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-14",
        project_name="PAIR93A",
        user_key="R931",
        user_name="Suggestion Request Drift Rider",
        vehicle_plate=None,
        seed_existing_assignment=False,
        request_kind="extra",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_blocks_when_vehicle_availability_drifts_before_apply(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert seeded["vehicle_id"] is not None

        _rewrite_transport_ai_suggestion_as_keep_existing_vehicle(
            suggestion_key,
            vehicle_id=seeded["vehicle_id"],
            rationale="Keep the existing vehicle and validate proposal drift before apply.",
        )

        with SessionLocal() as session:
            schedules = session.execute(
                select(TransportVehicleSchedule)
                .where(TransportVehicleSchedule.vehicle_id == seeded["vehicle_id"])
                .order_by(TransportVehicleSchedule.id.asc())
            ).scalars().all()
            assert schedules
            for schedule in schedules:
                schedule.is_active = False
                schedule.updated_at = _fixture_timestamp()
            session.commit()

        apply_response = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
        assert apply_response.status_code == 409, apply_response.text
        apply_payload = apply_response.json()
        assert apply_payload["status"] == "proposed"
        assert apply_payload["suggestion"]["status"] == "shown"
        assert any(
            issue["code"] in {"vehicle_missing_from_snapshot", "transport_ai_extra_vehicle_schedule_missing"}
            for issue in apply_payload["issues"]
        )

        with SessionLocal() as session:
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == start_payload["run_key"])
            ).scalar_one()
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            assignment = session.get(TransportAssignment, seeded["assignment_id"])

        proposal_payload = json.loads(suggestion.transport_proposal_json) if suggestion.transport_proposal_json else None

        assert run.status == "proposed"
        assert suggestion.status == "shown"
        assert assignment is not None
        assert assignment.status == "pending"
        if proposal_payload and proposal_payload.get("audit_trail"):
            proposal_audit_actions = [entry["action"] for entry in proposal_payload["audit_trail"]]
            assert proposal_payload["origin"] == "agent"
            assert proposal_payload["proposal_status"] == "draft"
            assert proposal_payload["replaces_proposal_key"] is None
            assert proposal_audit_actions[0] == "generated"
            assert proposal_audit_actions[-1] == "validated"
            assert proposal_payload["audit_trail"][-1]["outcome"] == "blocked"
            assert any(
                issue["code"] in {"vehicle_missing_from_snapshot", "transport_ai_extra_vehicle_schedule_missing"}
                for issue in proposal_payload["validation_issues"]
            )
        else:
            assert proposal_payload is None or "audit_trail" not in proposal_payload
            if proposal_payload and proposal_payload.get("validation_issues"):
                assert any(
                    issue["code"] in {"vehicle_missing_from_snapshot", "transport_ai_extra_vehicle_schedule_missing"}
                    for issue in proposal_payload["validation_issues"]
                )
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-16",
        project_name="PAIR93B",
        user_key="R932",
        user_name="Suggestion Vehicle Drift Rider",
        vehicle_plate="DRF9302A",
        seed_existing_assignment=True,
        request_kind="extra",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_updates_existing_extra_vehicle_departure_time_from_home_eta(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert seeded["vehicle_id"] is not None

        expected_departure_time = status_payload["suggestion"]["plan"]["route_itineraries"][0]["projected_arrival_time"]
        expected_boarding_time = status_payload["suggestion"]["plan"]["passenger_allocations"][0]["scheduled_pickup_time"]
        assert expected_departure_time
        assert expected_boarding_time
        assert expected_departure_time != "07:30"

        with SessionLocal() as session:
            seeded_assignment = session.get(TransportAssignment, seeded["assignment_id"])
            assert seeded_assignment is not None
            seeded_assignment.boarding_time = "07:55"
            session.commit()

        assert expected_boarding_time != "07:55"

        _rewrite_transport_ai_suggestion_as_keep_existing_vehicle(
            suggestion_key,
            vehicle_id=seeded["vehicle_id"],
            rationale="Keep existing extra vehicle while syncing the ETA into the active schedule.",
        )

        apply_response = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
        assert apply_response.status_code == 200, apply_response.text
        apply_payload = apply_response.json()
        assert apply_payload["status"] == "applied"
        assert apply_payload["suggestion"]["status"] == "applied"

        dashboard_response = client.get(
            "/api/transport/dashboard",
            params={"service_date": "2026-06-18", "route_kind": "home_to_work"},
        )
        assert dashboard_response.status_code == 200, dashboard_response.text
        dashboard_payload = dashboard_response.json()
        dashboard_request = next(
            row for row in dashboard_payload["extra_requests"] if row["id"] == seeded["request_id"]
        )

        with SessionLocal() as session:
            schedule = session.execute(
                select(TransportVehicleSchedule)
                .where(TransportVehicleSchedule.vehicle_id == seeded["vehicle_id"])
                .order_by(TransportVehicleSchedule.id.asc())
            ).scalars().first()
            assert schedule is not None

            assignment = session.get(TransportAssignment, seeded["assignment_id"])
            assert assignment is not None

        assert schedule.departure_time == expected_departure_time
        assert assignment.status == "confirmed"
        assert assignment.boarding_time == expected_boarding_time

        dashboard_vehicle = next(
            vehicle for vehicle in dashboard_payload["extra_vehicles"] if vehicle["id"] == seeded["vehicle_id"]
        )
        assert dashboard_vehicle["departure_time"] == expected_departure_time
        assert dashboard_request["boarding_time"] == expected_boarding_time
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-18",
        project_name="PAIR93B",
        user_key="R932",
        user_name="Suggestion Keep Existing Rider",
        vehicle_plate="PAIR93B1",
        seed_existing_assignment=True,
        request_kind="extra",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_creates_regular_vehicle_with_matching_weekday_schedules(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert status_payload["suggestion"]["plan"]["vehicle_actions"][0]["action_type"] == "create"

        apply_response = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
        assert apply_response.status_code == 200, apply_response.text
        assert apply_response.json()["status"] == "applied"

        with SessionLocal() as session:
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            assignment = session.execute(
                select(TransportAssignment).where(
                    TransportAssignment.request_id == seeded["request_id"],
                    TransportAssignment.service_date == date.fromisoformat("2026-06-15"),
                    TransportAssignment.route_kind == "home_to_work",
                )
            ).scalar_one()
            vehicle = session.get(Vehicle, assignment.vehicle_id)
            schedules = session.execute(
                select(TransportVehicleSchedule)
                .where(TransportVehicleSchedule.vehicle_id == vehicle.id)
                .order_by(TransportVehicleSchedule.route_kind.asc(), TransportVehicleSchedule.weekday.asc())
            ).scalars().all()

        monday_dashboard = client.get(
            "/api/transport/dashboard",
            params={"service_date": "2026-06-15", "route_kind": "home_to_work"},
        )
        tuesday_dashboard = client.get(
            "/api/transport/dashboard",
            params={"service_date": "2026-06-16", "route_kind": "home_to_work"},
        )
        assert monday_dashboard.status_code == 200, monday_dashboard.text
        assert tuesday_dashboard.status_code == 200, tuesday_dashboard.text

        monday_rows = [row for row in monday_dashboard.json()["regular_vehicles"] if row["id"] == vehicle.id]
        tuesday_rows = [row for row in tuesday_dashboard.json()["regular_vehicles"] if row["id"] == vehicle.id]

        assert vehicle.placa is not None and vehicle.placa.startswith("PLATE ")
        assert len(schedules) == 2
        assert {row.route_kind for row in schedules} == {"home_to_work", "work_to_home"}
        assert all(row.service_scope == "regular" for row in schedules)
        assert all(row.recurrence_kind == "matching_weekday" for row in schedules)
        assert {row.weekday for row in schedules} == {0}
        assert all(row.service_date == date.fromisoformat("2026-06-15") for row in schedules)
        assert len(monday_rows) == 1
        assert len(tuesday_rows) == 0

        change_summary_payload = json.loads(suggestion.change_summary_json)
        assert change_summary_payload["apply_vehicle_create_count"] == 1
        assert change_summary_payload["apply_vehicle_create_audit"][0]["schedules"][0]["service_scope"] == "regular"
        assert {item["weekday"] for item in change_summary_payload["apply_vehicle_create_audit"][0]["schedules"]} == {0}
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-15",
        project_name="PAIR91A",
        user_key="R911",
        user_name="Suggestion Regular Rider",
        vehicle_plate=None,
        seed_existing_assignment=False,
        request_kind="regular",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_creates_weekend_vehicle_with_matching_weekday_schedules(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert status_payload["suggestion"]["plan"]["vehicle_actions"][0]["action_type"] == "create"

        apply_response = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
        assert apply_response.status_code == 200, apply_response.text
        assert apply_response.json()["status"] == "applied"

        with SessionLocal() as session:
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            assignment = session.execute(
                select(TransportAssignment).where(
                    TransportAssignment.request_id == seeded["request_id"],
                    TransportAssignment.service_date == date.fromisoformat("2026-06-20"),
                    TransportAssignment.route_kind == "home_to_work",
                )
            ).scalar_one()
            vehicle = session.get(Vehicle, assignment.vehicle_id)
            schedules = session.execute(
                select(TransportVehicleSchedule)
                .where(TransportVehicleSchedule.vehicle_id == vehicle.id)
                .order_by(TransportVehicleSchedule.route_kind.asc(), TransportVehicleSchedule.weekday.asc())
            ).scalars().all()

        saturday_dashboard = client.get(
            "/api/transport/dashboard",
            params={"service_date": "2026-06-20", "route_kind": "home_to_work"},
        )
        sunday_dashboard = client.get(
            "/api/transport/dashboard",
            params={"service_date": "2026-06-21", "route_kind": "home_to_work"},
        )
        assert saturday_dashboard.status_code == 200, saturday_dashboard.text
        assert sunday_dashboard.status_code == 200, sunday_dashboard.text

        saturday_rows = [row for row in saturday_dashboard.json()["weekend_vehicles"] if row["id"] == vehicle.id]
        sunday_rows = [row for row in sunday_dashboard.json()["weekend_vehicles"] if row["id"] == vehicle.id]

        assert vehicle.placa is not None and vehicle.placa.startswith("PLATE ")
        assert len(schedules) == 2
        assert {row.route_kind for row in schedules} == {"home_to_work", "work_to_home"}
        assert all(row.service_scope == "weekend" for row in schedules)
        assert all(row.recurrence_kind == "matching_weekday" for row in schedules)
        assert {row.weekday for row in schedules} == {5}
        assert all(row.service_date == date.fromisoformat("2026-06-20") for row in schedules)
        assert len(saturday_rows) == 1
        assert len(sunday_rows) == 0

        change_summary_payload = json.loads(suggestion.change_summary_json)
        assert change_summary_payload["apply_vehicle_create_count"] == 1
        assert change_summary_payload["apply_vehicle_create_audit"][0]["schedules"][0]["service_scope"] == "weekend"
        assert {item["weekday"] for item in change_summary_payload["apply_vehicle_create_audit"][0]["schedules"]} == {5}
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-20",
        project_name="PAIR91B",
        user_key="R912",
        user_name="Suggestion Weekend Rider",
        vehicle_plate=None,
        seed_existing_assignment=False,
        request_kind="weekend",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_rolls_back_created_vehicle_when_create_action_fails(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert status_payload["suggestion"]["plan"]["vehicle_actions"][0]["action_type"] == "create"

        import sistema.app.routers.transport_ai as transport_ai_router_module

        original_create_transport_vehicle_registration = transport_ai_router_module.create_transport_vehicle_registration

        def _fail_after_create(db, *, payload):
            vehicle, schedules = original_create_transport_vehicle_registration(db, payload=payload)
            raise RuntimeError("transport-ai-create-failed-after-write")

        transport_ai_router_module.create_transport_vehicle_registration = _fail_after_create
        try:
            try:
                client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
                raise AssertionError("apply should have raised after the simulated create failure")
            except RuntimeError as exc:
                assert "transport-ai-create-failed-after-write" in str(exc)
        finally:
            transport_ai_router_module.create_transport_vehicle_registration = original_create_transport_vehicle_registration

        with SessionLocal() as session:
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == start_payload["run_key"])
            ).scalar_one()
            assignments = session.execute(
                select(TransportAssignment).where(
                    TransportAssignment.request_id == seeded["request_id"],
                    TransportAssignment.service_date == date.fromisoformat("2026-06-22"),
                    TransportAssignment.route_kind == "home_to_work",
                )
            ).scalars().all()
            vehicles = session.execute(
                select(Vehicle).where(Vehicle.placa.like("PLATE %"))
            ).scalars().all()
            schedules = session.execute(select(TransportVehicleSchedule)).scalars().all()
            applied_stops = session.execute(select(TransportAIAppliedRouteStop)).scalars().all()

        assert run.status == "proposed"
        assert suggestion.status == "shown"
        assert len(assignments) == 1
        assert assignments[0].status == "pending"
        assert assignments[0].vehicle_id is None
        assert vehicles == []
        assert schedules == []
        assert applied_stops == []
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-22",
        project_name="PAIR91C",
        user_key="R913",
        user_name="Suggestion Rollback Rider",
        vehicle_plate=None,
        seed_existing_assignment=False,
        request_kind="regular",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_updates_existing_vehicle_base_fields(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert seeded["vehicle_id"] is not None

        with SessionLocal() as session:
            original_schedule_ids = [
                schedule.id
                for schedule in session.execute(
                    select(TransportVehicleSchedule)
                    .where(TransportVehicleSchedule.vehicle_id == seeded["vehicle_id"])
                    .order_by(TransportVehicleSchedule.id.asc())
                ).scalars().all()
            ]

        _rewrite_transport_ai_suggestion_as_vehicle_update(
            suggestion_key,
            vehicle_id=seeded["vehicle_id"],
            vehicle_updates={
                "vehicle_type": "van",
                "capacity": 10,
                "plate": "UPD9201B",
                "color": "Black",
                "tolerance": 12,
            },
            rationale="Update the existing vehicle base fields before applying assignments.",
        )

        apply_response = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
        assert apply_response.status_code == 200, apply_response.text
        assert apply_response.json()["status"] == "applied"

        with SessionLocal() as session:
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            assignment = session.execute(
                select(TransportAssignment).where(
                    TransportAssignment.request_id == seeded["request_id"],
                    TransportAssignment.service_date == date.fromisoformat("2026-06-23"),
                    TransportAssignment.route_kind == "home_to_work",
                )
            ).scalar_one()
            vehicle = session.get(Vehicle, seeded["vehicle_id"])
            schedules = session.execute(
                select(TransportVehicleSchedule)
                .where(TransportVehicleSchedule.vehicle_id == seeded["vehicle_id"])
                .order_by(TransportVehicleSchedule.id.asc())
            ).scalars().all()

        dashboard = client.get(
            "/api/transport/dashboard",
            params={"service_date": "2026-06-23", "route_kind": "home_to_work"},
        )
        assert dashboard.status_code == 200, dashboard.text
        dashboard_rows = [row for row in dashboard.json()["extra_vehicles"] if row["id"] == seeded["vehicle_id"]]

        assert assignment.vehicle_id == seeded["vehicle_id"]
        assert vehicle is not None
        assert vehicle.placa == "UPD9201B"
        assert vehicle.tipo == "van"
        assert vehicle.color == "Black"
        assert vehicle.lugares == 10
        assert vehicle.tolerance == 12
        assert [schedule.id for schedule in schedules] == original_schedule_ids
        assert dashboard_rows and dashboard_rows[0]["placa"] == "UPD9201B"

        change_summary_payload = json.loads(suggestion.change_summary_json)
        assert change_summary_payload["apply_vehicle_update_count"] == 1
        assert change_summary_payload["apply_vehicle_update_audit"][0]["vehicle_id"] == seeded["vehicle_id"]
        assert set(change_summary_payload["apply_vehicle_update_audit"][0]["changed_fields"]) == {
            "capacity",
            "color",
            "plate",
            "tolerance",
            "vehicle_type",
        }
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-23",
        project_name="PAIR92A",
        user_key="R921",
        user_name="Suggestion Update Rider",
        vehicle_plate="UPD9201A",
        seed_existing_assignment=True,
        request_kind="extra",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_uses_default_capacity_when_vehicle_type_changes(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert seeded["vehicle_id"] is not None

        _rewrite_transport_ai_suggestion_as_vehicle_update(
            suggestion_key,
            vehicle_id=seeded["vehicle_id"],
            vehicle_updates={"vehicle_type": "van"},
            rationale="Change the vehicle type and let transport defaults resolve the new capacity.",
            omit_after_fields=["capacity"],
        )

        apply_response = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
        assert apply_response.status_code == 200, apply_response.text
        assert apply_response.json()["status"] == "applied"

        with SessionLocal() as session:
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            vehicle = session.get(Vehicle, seeded["vehicle_id"])

        assert vehicle is not None
        assert vehicle.tipo == "van"
        assert vehicle.lugares == 10

        change_summary_payload = json.loads(suggestion.change_summary_json)
        assert change_summary_payload["apply_vehicle_update_count"] == 1
        assert change_summary_payload["apply_vehicle_update_audit"][0]["update_payload"]["lugares"] == 10
        assert set(change_summary_payload["apply_vehicle_update_audit"][0]["changed_fields"]) == {
            "capacity",
            "vehicle_type",
        }
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-24",
        project_name="PAIR92B",
        user_key="R922",
        user_name="Suggestion Default Capacity Rider",
        vehicle_plate="UPD9202A",
        seed_existing_assignment=True,
        request_kind="extra",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_vehicle_update_blocks_future_capacity_conflict(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert seeded["vehicle_id"] is not None

        with SessionLocal() as session:
            admin_user = session.execute(select(AdminUser).order_by(AdminUser.id.asc())).scalars().first()
            assert admin_user is not None
            for suffix in ("A", "B"):
                future_rider = _create_user(
                    session,
                    chave=f"F9{suffix}",
                    nome=f"Future Capacity {suffix}",
                    projeto="PAIR92C",
                )
                future_request = _create_transport_request(
                    session,
                    user_id=future_rider.id,
                    service_date=date.fromisoformat("2026-06-30"),
                )
                _create_assignment(
                    session,
                    request_id=future_request.id,
                    service_date=date.fromisoformat("2026-06-30"),
                    vehicle_id=seeded["vehicle_id"],
                    assigned_by_admin_id=admin_user.id,
                )
            session.commit()

        _rewrite_transport_ai_suggestion_as_vehicle_update(
            suggestion_key,
            vehicle_id=seeded["vehicle_id"],
            vehicle_updates={"capacity": 1},
            rationale="Attempt to reduce capacity below future confirmed demand.",
        )

        apply_response = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
        assert apply_response.status_code == 409, apply_response.text
        apply_payload = apply_response.json()
        assert apply_payload["status"] == "proposed"
        assert any(issue["code"] == "transport_ai_vehicle_update_conflict" for issue in apply_payload["issues"])
        assert any("confirmed assignments would exceed the new capacity" in issue["message"] for issue in apply_payload["issues"])

        with SessionLocal() as session:
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == start_payload["run_key"])
            ).scalar_one()
            vehicle = session.get(Vehicle, seeded["vehicle_id"])

        assert run.status == "proposed"
        assert suggestion.status == "shown"
        assert vehicle is not None
        assert vehicle.lugares == 4
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-25",
        project_name="PAIR92C",
        user_key="R923",
        user_name="Suggestion Capacity Conflict Rider",
        vehicle_plate="UPD9203A",
        seed_existing_assignment=True,
        request_kind="extra",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_rolls_back_vehicle_update_when_later_step_fails(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert seeded["vehicle_id"] is not None

        _rewrite_transport_ai_suggestion_as_vehicle_update(
            suggestion_key,
            vehicle_id=seeded["vehicle_id"],
            vehicle_updates={
                "vehicle_type": "van",
                "capacity": 10,
                "plate": "UPD9204B",
                "color": "Silver",
                "tolerance": 11,
            },
            rationale="Update the existing vehicle, then fail later to validate savepoint rollback.",
        )

        import sistema.app.routers.transport_ai as transport_ai_router_module

        original_approve_transport_operational_proposal = transport_ai_router_module.approve_transport_operational_proposal

        def _fail_after_vehicle_update(db, *, proposal, actor, approved_at=None):
            raise RuntimeError("transport-ai-update-failed-after-write")

        transport_ai_router_module.approve_transport_operational_proposal = _fail_after_vehicle_update
        try:
            try:
                client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
                raise AssertionError("apply should have raised after the simulated update failure")
            except RuntimeError as exc:
                assert "transport-ai-update-failed-after-write" in str(exc)
        finally:
            transport_ai_router_module.approve_transport_operational_proposal = original_approve_transport_operational_proposal

        with SessionLocal() as session:
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == start_payload["run_key"])
            ).scalar_one()
            vehicle = session.get(Vehicle, seeded["vehicle_id"])
            assignments = session.execute(
                select(TransportAssignment).where(
                    TransportAssignment.request_id == seeded["request_id"],
                    TransportAssignment.service_date == date.fromisoformat("2026-06-26"),
                    TransportAssignment.route_kind == "home_to_work",
                )
            ).scalars().all()
            applied_stops = session.execute(select(TransportAIAppliedRouteStop)).scalars().all()

        assert run.status == "proposed"
        assert suggestion.status == "shown"
        assert vehicle is not None
        assert vehicle.placa == "UPD9204A"
        assert vehicle.tipo == "carro"
        assert vehicle.color == "white"
        assert vehicle.lugares == 4
        assert vehicle.tolerance == 0
        assert len(assignments) == 1
        assert assignments[0].status == "pending"
        assert assignments[0].vehicle_id is None
        assert applied_stops == []
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-26",
        project_name="PAIR92D",
        user_key="R924",
        user_name="Suggestion Update Rollback Rider",
        vehicle_plate="UPD9204A",
        seed_existing_assignment=True,
        request_kind="extra",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_remove_from_day_regular_vehicle_keeps_future_availability(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert status_payload["suggestion"]["plan"]["vehicle_actions"][0]["action_type"] == "create"

        with SessionLocal() as session:
            removed_vehicle = _create_vehicle_candidate_for_scope(
                session,
                placa="RMD9301A",
                service_scope="regular",
                service_date=date.fromisoformat("2026-06-29"),
            )
            session.commit()
            removed_vehicle_id = removed_vehicle.id

        _rewrite_transport_ai_suggestion_as_vehicle_remove_from_day(
            suggestion_key,
            vehicle_id=removed_vehicle_id,
            rationale="Remove the regular vehicle from the selected service date only.",
        )

        apply_response = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
        assert apply_response.status_code == 200, apply_response.text
        assert apply_response.json()["status"] == "applied"

        selected_dashboard = client.get(
            "/api/transport/dashboard",
            params={"service_date": "2026-06-29", "route_kind": "home_to_work"},
        )
        future_dashboard = client.get(
            "/api/transport/dashboard",
            params={"service_date": "2026-06-30", "route_kind": "home_to_work"},
        )
        assert selected_dashboard.status_code == 200, selected_dashboard.text
        assert future_dashboard.status_code == 200, future_dashboard.text
        assert all(row["placa"] != "RMD9301A" for row in selected_dashboard.json()["regular_vehicles"])
        assert any(row["placa"] == "RMD9301A" for row in future_dashboard.json()["regular_vehicles"])

        with SessionLocal() as session:
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            schedule_ids = session.execute(
                select(TransportVehicleSchedule.id).where(TransportVehicleSchedule.vehicle_id == removed_vehicle_id)
            ).scalars().all()
            exceptions = session.execute(
                select(TransportVehicleScheduleException)
                .where(TransportVehicleScheduleException.vehicle_schedule_id.in_(schedule_ids))
                .order_by(TransportVehicleScheduleException.vehicle_schedule_id.asc())
            ).scalars().all()

        assert len(schedule_ids) == 2
        assert len(exceptions) == 2
        assert {exception.service_date for exception in exceptions} == {date.fromisoformat("2026-06-29")}

        change_summary_payload = json.loads(suggestion.change_summary_json)
        assert change_summary_payload["apply_vehicle_remove_from_day_count"] == 1
        assert change_summary_payload["apply_vehicle_remove_from_day_audit"][0]["vehicle_id"] == removed_vehicle_id
        assert {
            item["change_kind"]
            for item in change_summary_payload["apply_vehicle_remove_from_day_audit"][0]["applied_changes"]
        } == {"add_exception"}
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-29",
        project_name="PAIR93A",
        user_key="R931",
        user_name="Suggestion Remove Regular Rider",
        vehicle_plate=None,
        seed_existing_assignment=False,
        request_kind="regular",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_remove_from_day_weekend_vehicle_keeps_future_recurrence(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert status_payload["suggestion"]["plan"]["vehicle_actions"][0]["action_type"] == "create"

        with SessionLocal() as session:
            removed_vehicle = _create_vehicle_candidate_for_scope(
                session,
                placa="RMD9302A",
                service_scope="weekend",
                service_date=date.fromisoformat("2026-06-27"),
            )
            session.commit()
            removed_vehicle_id = removed_vehicle.id

        _rewrite_transport_ai_suggestion_as_vehicle_remove_from_day(
            suggestion_key,
            vehicle_id=removed_vehicle_id,
            rationale="Remove the weekend vehicle from the selected Saturday only.",
        )

        apply_response = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
        assert apply_response.status_code == 200, apply_response.text
        assert apply_response.json()["status"] == "applied"

        selected_dashboard = client.get(
            "/api/transport/dashboard",
            params={"service_date": "2026-06-27", "route_kind": "home_to_work"},
        )
        future_dashboard = client.get(
            "/api/transport/dashboard",
            params={"service_date": "2026-07-04", "route_kind": "home_to_work"},
        )
        assert selected_dashboard.status_code == 200, selected_dashboard.text
        assert future_dashboard.status_code == 200, future_dashboard.text
        assert all(row["placa"] != "RMD9302A" for row in selected_dashboard.json()["weekend_vehicles"])
        assert any(row["placa"] == "RMD9302A" for row in future_dashboard.json()["weekend_vehicles"])

        with SessionLocal() as session:
            schedule_ids = session.execute(
                select(TransportVehicleSchedule.id).where(TransportVehicleSchedule.vehicle_id == removed_vehicle_id)
            ).scalars().all()
            exceptions = session.execute(
                select(TransportVehicleScheduleException)
                .where(TransportVehicleScheduleException.vehicle_schedule_id.in_(schedule_ids))
                .order_by(TransportVehicleScheduleException.vehicle_schedule_id.asc())
            ).scalars().all()

        assert len(schedule_ids) == 2
        assert len(exceptions) == 2
        assert {exception.service_date for exception in exceptions} == {date.fromisoformat("2026-06-27")}
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-06-27",
        project_name="PAIR93B",
        user_key="R932",
        user_name="Suggestion Remove Weekend Rider",
        vehicle_plate=None,
        seed_existing_assignment=False,
        request_kind="weekend",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_remove_from_day_extra_vehicle_hides_vehicle_and_keeps_assignments_off_it(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert status_payload["suggestion"]["plan"]["vehicle_actions"][0]["action_type"] == "create"

        with SessionLocal() as session:
            removed_vehicle = _create_vehicle_candidate_for_scope(
                session,
                placa="RMD9303A",
                service_scope="extra",
                service_date=date.fromisoformat("2026-07-01"),
            )
            session.commit()
            removed_vehicle_id = removed_vehicle.id

        _rewrite_transport_ai_suggestion_as_vehicle_remove_from_day(
            suggestion_key,
            vehicle_id=removed_vehicle_id,
            rationale="Remove the extra vehicle from the selected service date.",
        )

        apply_response = client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
        assert apply_response.status_code == 200, apply_response.text
        assert apply_response.json()["status"] == "applied"

        dashboard = client.get(
            "/api/transport/dashboard",
            params={"service_date": "2026-07-01", "route_kind": "home_to_work"},
        )
        assert dashboard.status_code == 200, dashboard.text
        assert all(row["placa"] != "RMD9303A" for row in dashboard.json()["extra_vehicles"])

        with SessionLocal() as session:
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            assignment = session.execute(
                select(TransportAssignment).where(
                    TransportAssignment.request_id == seeded["request_id"],
                    TransportAssignment.service_date == date.fromisoformat("2026-07-01"),
                    TransportAssignment.route_kind == "home_to_work",
                )
            ).scalar_one()
            schedules = session.execute(
                select(TransportVehicleSchedule)
                .where(TransportVehicleSchedule.vehicle_id == removed_vehicle_id)
                .order_by(TransportVehicleSchedule.id.asc())
            ).scalars().all()
            exceptions = session.execute(
                select(TransportVehicleScheduleException)
                .where(TransportVehicleScheduleException.vehicle_schedule_id.in_([schedule.id for schedule in schedules]))
            ).scalars().all()

        assert len(schedules) == 1
        assert schedules[0].is_active is False
        assert exceptions == []
        assert assignment.vehicle_id != removed_vehicle_id

        change_summary_payload = json.loads(suggestion.change_summary_json)
        assert change_summary_payload["apply_vehicle_remove_from_day_count"] == 1
        assert change_summary_payload["apply_vehicle_remove_from_day_audit"][0]["vehicle_id"] == removed_vehicle_id
        assert change_summary_payload["apply_vehicle_remove_from_day_audit"][0]["applied_changes"][0]["change_kind"] == "deactivate_single_date"
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-07-01",
        project_name="PAIR93C",
        user_key="R933",
        user_name="Suggestion Remove Extra Rider",
        vehicle_plate=None,
        seed_existing_assignment=False,
        request_kind="extra",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)


def test_transport_ai_apply_remove_from_day_rolls_back_when_later_step_fails(tmp_path):
    steps = textwrap.dedent(
        """
        assert status_payload["status"] == "proposed"
        assert status_payload["suggestion"]["plan"]["vehicle_actions"][0]["action_type"] == "create"

        with SessionLocal() as session:
            removed_vehicle = _create_vehicle_candidate_for_scope(
                session,
                placa="RMD9304A",
                service_scope="regular",
                service_date=date.fromisoformat("2026-07-02"),
            )
            session.commit()
            removed_vehicle_id = removed_vehicle.id

        _rewrite_transport_ai_suggestion_as_vehicle_remove_from_day(
            suggestion_key,
            vehicle_id=removed_vehicle_id,
            rationale="Remove the regular vehicle, then fail later to validate rollback.",
        )

        import sistema.app.routers.transport_ai as transport_ai_router_module

        original_approve_transport_operational_proposal = transport_ai_router_module.approve_transport_operational_proposal

        def _fail_after_remove_from_day(db, *, proposal, actor, approved_at=None):
            raise RuntimeError("transport-ai-remove-from-day-failed-after-write")

        transport_ai_router_module.approve_transport_operational_proposal = _fail_after_remove_from_day
        try:
            try:
                client.post(f"/api/transport/ai/suggestions/{suggestion_key}/apply")
                raise AssertionError("apply should have raised after the simulated remove_from_day failure")
            except RuntimeError as exc:
                assert "transport-ai-remove-from-day-failed-after-write" in str(exc)
        finally:
            transport_ai_router_module.approve_transport_operational_proposal = original_approve_transport_operational_proposal

        dashboard = client.get(
            "/api/transport/dashboard",
            params={"service_date": "2026-07-02", "route_kind": "home_to_work"},
        )
        assert dashboard.status_code == 200, dashboard.text
        assert any(row["placa"] == "RMD9304A" for row in dashboard.json()["regular_vehicles"])

        with SessionLocal() as session:
            suggestion = session.execute(
                select(TransportAISuggestion).where(TransportAISuggestion.suggestion_key == suggestion_key)
            ).scalar_one()
            run = session.execute(
                select(TransportAIRun).where(TransportAIRun.run_key == start_payload["run_key"])
            ).scalar_one()
            schedule_ids = session.execute(
                select(TransportVehicleSchedule.id).where(TransportVehicleSchedule.vehicle_id == removed_vehicle_id)
            ).scalars().all()
            exceptions = session.execute(
                select(TransportVehicleScheduleException)
                .where(TransportVehicleScheduleException.vehicle_schedule_id.in_(schedule_ids))
            ).scalars().all()

        assert run.status == "proposed"
        assert suggestion.status == "shown"
        assert exceptions == []
        """
    ).strip()
    script = _build_transport_ai_suggestion_script(
        service_date="2026-07-02",
        project_name="PAIR93D",
        user_key="R934",
        user_name="Suggestion Remove Rollback Rider",
        vehicle_plate=None,
        seed_existing_assignment=False,
        request_kind="regular",
        steps=steps,
    )
    _run_transport_ai_suggestion_commands_script(tmp_path, script=script)