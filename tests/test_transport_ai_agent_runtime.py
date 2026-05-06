from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from cryptography.fernet import Fernet
import sqlalchemy as sa
from langchain_core.messages import AIMessage
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.core.config import Settings
from sistema.app.database import Base
from sistema.app.models import AdminUser, MobileAppSettings, Project, TransportAIRun, TransportRequest, User, Vehicle, TransportVehicleSchedule
from sistema.app.services import location_settings as location_settings_module
from sistema.app.services.transport_ai_agent import (
    TransportAILangChainToolContext,
    build_transport_ai_chat_model_for_provider,
    build_transport_ai_langchain_tools,
    run_transport_ai_agent,
)
from sistema.app.services.transport_ai_llm_settings import (
    TransportAILlmRuntimeSettings,
    upsert_transport_ai_llm_settings,
)
from sistema.app.services.transport_route_provider import FakeTransportRouteProvider


def _build_settings(**overrides) -> Settings:
    values = {
        "openai_api_key": "sk-test-openai-secret",
        "mapbox_access_token": "pk.test-mapbox-secret",
        "openai_model": "gpt-5-2025-08-07",
        "openai_max_retries": 2,
        "transport_ai_settings_encryption_key": Fernet.generate_key().decode("utf-8"),
        "transport_ai_agent_mode": "agent",
        "transport_ai_max_passengers_per_run": 80,
        "transport_ai_route_provider": "fake",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _build_session_factory(db_path: Path):
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def _fixture_timestamp() -> datetime:
    return datetime(2026, 5, 2, 8, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))


def _configure_transport_settings(session: Session) -> None:
    location_settings_module.upsert_transport_vehicle_default_seat_counts(
        session,
        default_car_seats=3,
        default_minivan_seats=6,
        default_van_seats=10,
        default_bus_seats=40,
        default_tolerance_minutes=5,
    )
    location_settings_module.upsert_transport_pricing_settings(
        session,
        price_currency_code=None,
        price_rate_unit="day",
        default_car_price=120,
        default_minivan_price=180,
        default_van_price=240,
        default_bus_price=400,
    )
    settings_row = session.get(MobileAppSettings, 1)
    if settings_row is not None:
        settings_row.transport_work_to_home_time = "16:45"
        settings_row.transport_last_update_time = "16:00"
    session.flush()


def _create_admin_user(session: Session) -> AdminUser:
    timestamp = _fixture_timestamp()
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


def _create_project(session: Session, *, name: str, address: str, zip_code: str) -> Project:
    project = Project(
        name=name,
        country_code="SG",
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address=address,
        zip_code=zip_code,
    )
    session.add(project)
    session.flush()
    return project


def _create_user(
    session: Session,
    *,
    chave: str,
    nome: str,
    projeto: str,
    address: str,
    zip_code: str,
) -> User:
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
        end_rua=address,
        zip=zip_code,
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


def _create_transport_request(session: Session, *, user_id: int, service_date: date) -> TransportRequest:
    timestamp = _fixture_timestamp()
    request = TransportRequest(
        user_id=user_id,
        request_kind="extra",
        recurrence_kind="single_date",
        requested_time="08:00",
        selected_weekdays_json=None,
        single_date=service_date,
        created_via="admin",
        status="active",
        created_at=timestamp,
        updated_at=timestamp,
        cancelled_at=None,
    )
    session.add(request)
    session.flush()
    return request


def _create_extra_vehicle_candidate(session: Session, *, placa: str, service_date: date) -> Vehicle:
    timestamp = _fixture_timestamp()
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
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(schedule)
    session.flush()
    return vehicle


def _create_transport_ai_run(
    session: Session,
    *,
    actor_user_id: int,
    service_date: date,
    openai_model: str,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    llm_reasoning_effort: str | None = None,
) -> TransportAIRun:
    timestamp = _fixture_timestamp()
    run = TransportAIRun(
        run_key="run-transport-ai-agent-001",
        service_date=service_date,
        route_kind="home_to_work",
        status="requested",
        actor_user_id=actor_user_id,
        earliest_boarding_time="06:50",
        arrival_at_work_time="07:45",
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_reasoning_effort=llm_reasoning_effort,
        openai_model=openai_model,
        route_provider="fake",
        price_currency_code=None,
        price_rate_unit="day",
        baseline_snapshot_json=None,
        baseline_assignments_json=None,
        baseline_vehicle_state_json=None,
        planning_input_json=json.dumps({"seed": True}),
        planning_input_hash="0" * 64,
        preflight_issues_json=None,
        error_code=None,
        error_message=None,
        created_at=timestamp,
        updated_at=timestamp,
        completed_at=None,
    )
    session.add(run)
    session.flush()
    return run


def _build_tool_context(
    session: Session,
    *,
    service_date: date,
    settings_obj: Settings,
    provider: FakeTransportRouteProvider,
) -> TransportAILangChainToolContext:
    return TransportAILangChainToolContext(
        db=session,
        service_date=service_date,
        route_kind="home_to_work",
        earliest_boarding_time="06:50",
        arrival_at_work_time="07:45",
        settings_obj=settings_obj,
        provider=provider,
    )


def _build_valid_plan(session: Session, *, service_date: date, settings_obj: Settings, provider: FakeTransportRouteProvider):
    context = _build_tool_context(
        session,
        service_date=service_date,
        settings_obj=settings_obj,
        provider=provider,
    )
    tools_by_name = {
        tool.name: tool
        for tool in build_transport_ai_langchain_tools(context=context)
    }
    load_result = tools_by_name["load_planning_input"].invoke({})
    planning_input_hash = load_result["planning_input_hash"]
    tools_by_name["geocode_route_points"].invoke({"planning_input_hash": planning_input_hash})
    tools_by_name["build_route_matrices"].invoke({"planning_input_hash": planning_input_hash})
    tools_by_name["solve_transport_plan"].invoke({"planning_input_hash": planning_input_hash})
    assert context.state.plan is not None
    return context.state.plan


class _FakeStructuredRunnable:
    def __init__(self, owner: "_FakeChatModel") -> None:
        self._owner = owner

    def invoke(self, messages):
        self._owner.invocations.append(messages)
        response = self._owner.responses[self._owner.response_index]
        self._owner.response_index += 1
        if isinstance(response, Exception):
            raise response
        return response


class _FakeChatModel:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.response_index = 0
        self.invocations: list[list[object]] = []
        self.structured_output_calls: list[dict[str, object]] = []

    def with_structured_output(self, schema, **kwargs):
        self.structured_output_calls.append({"schema": schema, **kwargs})
        return _FakeStructuredRunnable(self)


def test_build_transport_ai_chat_model_for_deepseek_uses_openai_compatible_adapter(monkeypatch):
    captured_kwargs: dict[str, object] = {}

    class _CapturedChatOpenAI:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

    from sistema.app.services import transport_ai_agent as transport_ai_agent_module

    monkeypatch.setattr(transport_ai_agent_module, "ChatOpenAI", _CapturedChatOpenAI)

    model = build_transport_ai_chat_model_for_provider(
        runtime_settings=TransportAILlmRuntimeSettings(
            provider="deepseek",
            model_name="deepseek-v4-pro",
            reasoning_effort="high",
            api_key="deepseek-test-secret",
            base_url="https://api.deepseek.com/v1",
        ),
        settings_obj=_build_settings(),
        temperature=0.0,
    )

    assert isinstance(model, _CapturedChatOpenAI)
    assert captured_kwargs["api_key"] == "deepseek-test-secret"
    assert captured_kwargs["model"] == "deepseek-v4-pro"
    assert captured_kwargs["base_url"] == "https://api.deepseek.com/v1"
    assert captured_kwargs["temperature"] == 0.0
    assert captured_kwargs["model_kwargs"] == {"reasoning_effort": "high"}


def test_build_transport_ai_chat_model_for_deepseek_can_omit_reasoning_payload_for_compatibility(monkeypatch):
    captured_kwargs: dict[str, object] = {}

    class _CapturedChatOpenAI:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

    from sistema.app.services import transport_ai_agent as transport_ai_agent_module

    monkeypatch.setattr(transport_ai_agent_module, "ChatOpenAI", _CapturedChatOpenAI)

    model = build_transport_ai_chat_model_for_provider(
        runtime_settings=TransportAILlmRuntimeSettings(
            provider="deepseek",
            model_name="deepseek-v4-pro",
            reasoning_effort="high",
            api_key="deepseek-test-secret",
            base_url="https://api.deepseek.com/v1",
        ),
        settings_obj=_build_settings(),
        temperature=0.0,
        include_reasoning_effort=False,
    )

    assert isinstance(model, _CapturedChatOpenAI)
    assert captured_kwargs["api_key"] == "deepseek-test-secret"
    assert captured_kwargs["model"] == "deepseek-v4-pro"
    assert captured_kwargs["base_url"] == "https://api.deepseek.com/v1"
    assert captured_kwargs["temperature"] == 0.0
    assert "model_kwargs" not in captured_kwargs


def test_run_transport_ai_agent_returns_valid_plan_with_fake_model(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_valid.db")
    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(transport_ai_agent_mode="agent")
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session, name="PRUNTIME1", address="1 Marina Boulevard", zip_code="018989")
            upsert_transport_ai_llm_settings(
                session,
                project_id=project.id,
                provider="openai",
                api_key="sk-project-runtime-1001",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            user = _create_user(
                session,
                chave="RT01",
                nome="Runtime Worker One",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7001A", service_date=service_date)
            run = _create_transport_ai_run(
                session,
                actor_user_id=admin_user.id,
                service_date=service_date,
                openai_model=settings_obj.openai_model,
            )
            session.commit()

            valid_plan = _build_valid_plan(
                session,
                service_date=service_date,
                settings_obj=settings_obj,
                provider=provider,
            )
            fake_model = _FakeChatModel([
                {
                    "raw": AIMessage(content="raw response sk-test-openai-secret"),
                    "parsed": valid_plan,
                    "parsing_error": None,
                }
            ])

            result = run_transport_ai_agent(
                db=session,
                run=run,
                settings_obj=settings_obj,
                provider=provider,
                model=fake_model,
            )

            assert result.plan is not None
            assert result.plan.plan_key == valid_plan.plan_key
            assert result.validation_result is not None
            assert result.validation_result.ok is True
            assert run.status == "proposed"
            assert run.completed_at is not None
            assert len(fake_model.invocations) == 1
            planning_input_payload = json.loads(run.planning_input_json or "{}")
            assert planning_input_payload["llm_runtime_projects"] == [
                {
                    "project_id": project.id,
                    "project_name": project.name,
                    "partition_keys": [f"extra:{project.name}:{project.country_code}"],
                    "provider": "openai",
                    "model_name": "gpt-5.4-2026-03-05",
                    "reasoning_effort": "high",
                }
            ]
            assert run.llm_provider == "openai"
            assert run.llm_model == "gpt-5.4-2026-03-05"
            assert run.llm_reasoning_effort == "high"
    finally:
        engine.dispose()


def test_run_transport_ai_agent_uses_run_llm_snapshot_and_sanitizes_persisted_api_key(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_deepseek.db")
    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(
            openai_api_key=None,
            openai_model="legacy-openai-model-ignored",
        )
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session, name="PRUNTIME-DP", address="1 Marina Boulevard", zip_code="018989")
            upsert_transport_ai_llm_settings(
                session,
                project_id=project.id,
                provider="deepseek",
                api_key="deepseek-test-secret-4321",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            user = _create_user(
                session,
                chave="RTD1",
                nome="Runtime Worker DeepSeek",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7999A", service_date=service_date)
            run = _create_transport_ai_run(
                session,
                actor_user_id=admin_user.id,
                service_date=service_date,
                openai_model="deepseek-v4-pro",
                llm_provider="deepseek",
                llm_model="deepseek-v4-pro",
                llm_reasoning_effort="high",
            )
            session.commit()

            valid_plan = _build_valid_plan(
                session,
                service_date=service_date,
                settings_obj=settings_obj,
                provider=provider,
            )
            fake_model = _FakeChatModel([
                {
                    "raw": AIMessage(content="deepseek key deepseek-test-secret-4321"),
                    "parsed": valid_plan,
                    "parsing_error": None,
                }
            ])

            result = run_transport_ai_agent(
                db=session,
                run=run,
                settings_obj=settings_obj,
                provider=provider,
                model=fake_model,
            )

            assert result.plan is not None
            assert result.openai_model == "deepseek-v4-pro"
            assert result.raw_model_response_json is not None
            assert "deepseek-test-secret-4321" not in result.raw_model_response_json
            assert "[REDACTED]" in result.raw_model_response_json
            assert run.status == "proposed"
            assert run.completed_at is not None
    finally:
        engine.dispose()


def test_run_transport_ai_agent_persists_project_llm_runtime_snapshots_without_api_keys(tmp_path, monkeypatch):
    from sistema.app.services import transport_ai_agent as transport_ai_agent_module

    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_snapshot.db")
    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(
            openai_api_key=None,
            openai_model="legacy-openai-model-ignored",
        )
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session, name="PRUNTIME-SNAPSHOT", address="1 Marina Boulevard", zip_code="018989")
            upsert_transport_ai_llm_settings(
                session,
                project_id=project.id,
                provider="deepseek",
                api_key="deepseek-snapshot-secret-7788",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            user = _create_user(
                session,
                chave="RTSP",
                nome="Runtime Snapshot Worker",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7444A", service_date=service_date)
            run = _create_transport_ai_run(
                session,
                actor_user_id=admin_user.id,
                service_date=service_date,
                openai_model="",
            )
            session.commit()

            valid_plan = _build_valid_plan(
                session,
                service_date=service_date,
                settings_obj=settings_obj,
                provider=provider,
            )
            fake_model = _FakeChatModel([
                {
                    "raw": AIMessage(content="deepseek snapshot secret deepseek-snapshot-secret-7788"),
                    "parsed": valid_plan,
                    "parsing_error": None,
                }
            ])
            monkeypatch.setattr(
                transport_ai_agent_module,
                "build_transport_ai_chat_model_for_provider",
                lambda **kwargs: fake_model,
            )

            result = run_transport_ai_agent(
                db=session,
                run=run,
                settings_obj=settings_obj,
                provider=provider,
                model=None,
            )

            planning_input_payload = json.loads(run.planning_input_json or "{}")
            runtime_projects = planning_input_payload.get("llm_runtime_projects")

            assert result.plan is not None
            assert runtime_projects == [
                {
                    "project_id": project.id,
                    "project_name": project.name,
                    "partition_keys": [f"extra:{project.name}:{project.country_code}"],
                    "provider": "deepseek",
                    "model_name": "deepseek-v4-pro",
                    "reasoning_effort": "high",
                }
            ]
            assert "deepseek-snapshot-secret-7788" not in run.planning_input_json
            assert "api_key" not in run.planning_input_json
            assert "api_key_ciphertext" not in run.planning_input_json
            assert run.llm_provider == "deepseek"
            assert run.llm_model == "deepseek-v4-pro"
            assert run.llm_reasoning_effort == "high"
            assert run.openai_model == "deepseek-v4-pro"
    finally:
        engine.dispose()


def test_run_transport_ai_agent_persists_openai_project_snapshots_without_secret_fields(tmp_path, monkeypatch):
    from sistema.app.services import transport_ai_agent as transport_ai_agent_module

    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_openai_snapshot.db")
    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(
            openai_api_key=None,
            openai_model="legacy-openai-model-ignored",
        )
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session, name="PRUNTIME-OPENAI-SNAPSHOT", address="1 Marina Boulevard", zip_code="018989")
            upsert_transport_ai_llm_settings(
                session,
                project_id=project.id,
                provider="openai",
                api_key="snapshot-openai-secret-7788",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            user = _create_user(
                session,
                chave="RTSO",
                nome="Runtime Snapshot Worker OpenAI",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7222A", service_date=service_date)
            run = _create_transport_ai_run(
                session,
                actor_user_id=admin_user.id,
                service_date=service_date,
                openai_model="",
            )
            session.commit()

            valid_plan = _build_valid_plan(
                session,
                service_date=service_date,
                settings_obj=settings_obj,
                provider=provider,
            )
            fake_model = _FakeChatModel([
                {
                    "raw": AIMessage(content="openai snapshot secret snapshot-openai-secret-7788"),
                    "parsed": valid_plan,
                    "parsing_error": None,
                }
            ])
            monkeypatch.setattr(
                transport_ai_agent_module,
                "build_transport_ai_chat_model_for_provider",
                lambda **kwargs: fake_model,
            )

            result = run_transport_ai_agent(
                db=session,
                run=run,
                settings_obj=settings_obj,
                provider=provider,
                model=None,
            )

            planning_input_payload = json.loads(run.planning_input_json or "{}")
            runtime_projects = planning_input_payload.get("llm_runtime_projects")

            assert result.plan is not None
            assert runtime_projects == [
                {
                    "project_id": project.id,
                    "project_name": project.name,
                    "partition_keys": [f"extra:{project.name}:{project.country_code}"],
                    "provider": "openai",
                    "model_name": "gpt-5.4-2026-03-05",
                    "reasoning_effort": "high",
                }
            ]
            assert "snapshot-openai-secret-7788" not in run.planning_input_json
            assert '"api_key":' not in run.planning_input_json
            assert '"api_key_ciphertext":' not in run.planning_input_json
            assert '"api_key_last4":' not in run.planning_input_json
            assert run.llm_provider == "openai"
            assert run.llm_model == "gpt-5.4-2026-03-05"
            assert run.llm_reasoning_effort == "high"
            assert run.openai_model == "gpt-5.4-2026-03-05"
    finally:
        engine.dispose()


def test_run_transport_ai_agent_fails_when_project_llm_snapshot_drifts_from_current_settings(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_snapshot_drift.db")
    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(
            openai_api_key=None,
            openai_model="legacy-openai-model-ignored",
        )
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session, name="PRUNTIME-SNAPSHOT-DRIFT", address="1 Marina Boulevard", zip_code="018989")
            upsert_transport_ai_llm_settings(
                session,
                project_id=project.id,
                provider="openai",
                api_key="snapshot-openai-1234",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            user = _create_user(
                session,
                chave="RTSD",
                nome="Runtime Snapshot Drift Worker",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7998A", service_date=service_date)
            run = _create_transport_ai_run(
                session,
                actor_user_id=admin_user.id,
                service_date=service_date,
                openai_model="gpt-5.4-2026-03-05",
                llm_provider="openai",
                llm_model="gpt-5.4-2026-03-05",
                llm_reasoning_effort="high",
            )
            run.planning_input_json = json.dumps(
                {
                    "planning_input_hash": run.planning_input_hash,
                    "service_date": service_date.isoformat(),
                    "route_kind": run.route_kind,
                    "snapshot_key": "transport-ai-snapshot-drift",
                    "captured_at": _fixture_timestamp().isoformat(),
                    "limits": {
                        "max_passengers_per_run": 80,
                    },
                    "settings": {
                        "route_provider": "fake",
                        "price_currency_code": "SGD",
                        "price_rate_unit": "day",
                        "matrix_profile": settings_obj.mapbox_matrix_profile,
                        "directions_profile": settings_obj.mapbox_directions_profile,
                    },
                    "projects_by_name": {
                        project.name: {
                            "id": project.id,
                            "name": project.name,
                        }
                    },
                    "requests_by_scope": {},
                    "vehicles_by_scope": {},
                    "partitions": [
                        {
                            "partition_key": f"extra:{project.name}:{project.country_code}",
                            "request_kind": "extra",
                            "project_id": project.id,
                            "project_name": project.name,
                            "country_code": project.country_code,
                            "country_name": project.country_name,
                            "destination_project": {
                                "id": project.id,
                                "name": project.name,
                            },
                            "requests": [],
                            "candidate_vehicles": [],
                        }
                    ],
                    "llm_runtime_projects": [
                        {
                            "project_id": project.id,
                            "project_name": project.name,
                            "partition_keys": [f"extra:{project.name}:{project.country_code}"],
                            "provider": "openai",
                            "model_name": "gpt-5.4-2026-03-05",
                            "reasoning_effort": "high",
                        }
                    ],
                    "preflight_issues": [],
                    "total_requests": 0,
                    "total_candidate_vehicles": 0,
                },
                ensure_ascii=True,
                sort_keys=True,
            )
            session.flush()

            upsert_transport_ai_llm_settings(
                session,
                project_id=project.id,
                provider="deepseek",
                api_key="snapshot-deepseek-5678",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            session.commit()

            result = run_transport_ai_agent(
                db=session,
                run=run,
                settings_obj=settings_obj,
                provider=provider,
                model=None,
            )

            assert result.plan is None
            assert result.error_code == "transport_ai_agent_execution_failed"
            assert run.status == "failed"
            assert "run LLM snapshot no longer matches the current project-specific AI settings" in (run.error_message or "")
    finally:
        engine.dispose()


def test_run_transport_ai_agent_retries_without_reasoning_payload_when_deepseek_rejects_it(tmp_path, monkeypatch):
    from sistema.app.services import transport_ai_agent as transport_ai_agent_module

    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_deepseek_reasoning_retry.db")
    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(
            openai_api_key=None,
            openai_model="legacy-openai-model-ignored",
        )
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session, name="PRUNTIME-DP-R", address="1 Marina Boulevard", zip_code="018989")
            upsert_transport_ai_llm_settings(
                session,
                project_id=project.id,
                provider="deepseek",
                api_key="deepseek-test-secret-5678",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            user = _create_user(
                session,
                chave="RTDR",
                nome="Runtime Worker DeepSeek Retry",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7888A", service_date=service_date)
            run = _create_transport_ai_run(
                session,
                actor_user_id=admin_user.id,
                service_date=service_date,
                openai_model="deepseek-v4-pro",
                llm_provider="deepseek",
                llm_model="deepseek-v4-pro",
                llm_reasoning_effort="high",
            )
            session.commit()

            valid_plan = _build_valid_plan(
                session,
                service_date=service_date,
                settings_obj=settings_obj,
                provider=provider,
            )
            incompatible_model = _FakeChatModel([
                ValueError("reasoning_effort is not supported by this OpenAI-compatible endpoint"),
            ])
            compatible_model = _FakeChatModel([
                {
                    "raw": AIMessage(content="deepseek retry response"),
                    "parsed": valid_plan,
                    "parsing_error": None,
                }
            ])
            build_calls: list[bool] = []

            def _fake_build_transport_ai_chat_model_for_provider(*, include_reasoning_effort=True, **kwargs):
                build_calls.append(include_reasoning_effort)
                return incompatible_model if include_reasoning_effort else compatible_model

            monkeypatch.setattr(
                transport_ai_agent_module,
                "build_transport_ai_chat_model_for_provider",
                _fake_build_transport_ai_chat_model_for_provider,
            )

            result = run_transport_ai_agent(
                db=session,
                run=run,
                settings_obj=settings_obj,
                provider=provider,
                model=None,
            )

            assert result.plan is not None
            assert result.plan.plan_key == valid_plan.plan_key
            assert result.openai_model == "deepseek-v4-pro"
            assert build_calls == [True, False]
            assert len(incompatible_model.invocations) == 1
            assert len(compatible_model.invocations) == 1
            assert run.status == "proposed"
            assert run.completed_at is not None
    finally:
        engine.dispose()


def test_run_transport_ai_agent_retries_without_reasoning_payload_when_deepseek_reasoner_rejects_tool_choice(tmp_path, monkeypatch):
    from sistema.app.services import transport_ai_agent as transport_ai_agent_module

    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_deepseek_tool_choice_retry.db")

    class _MethodAwareStructuredRunnable:
        def __init__(self, method: str, valid_plan: TransportAgentPlan) -> None:
            self._method = method
            self._valid_plan = valid_plan

        def invoke(self, messages):
            if self._method == "function_calling":
                raise ValueError(
                    "Error code: 400 - {'error': {'message': 'deepseek-reasoner does not support this tool_choice'}}"
                )
            return {
                "raw": AIMessage(content=f"deepseek tool choice retry response via {self._method}"),
                "parsed": self._valid_plan,
                "parsing_error": None,
            }

    class _MethodAwareChatModel:
        def __init__(self, valid_plan: TransportAgentPlan) -> None:
            self.valid_plan = valid_plan
            self.invocations: list[str] = []
            self.structured_output_calls: list[dict[str, object]] = []
            self.bind_tools_calls: list[dict[str, object]] = []

        def with_structured_output(self, schema, **kwargs):
            self.structured_output_calls.append({"schema": schema, **kwargs})
            self.invocations.append(str(kwargs.get("method")))
            return _MethodAwareStructuredRunnable(str(kwargs.get("method")), self.valid_plan)

        def bind_tools(self, tools, **kwargs):
            self.bind_tools_calls.append({"tools": tools, **kwargs})
            owner = self

            class _AutoToolRunnable:
                def invoke(self_inner, messages):
                    return AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "TransportAgentPlan",
                                "args": owner.valid_plan.model_dump(mode="json"),
                                "id": "call_runtime_fallback",
                                "type": "tool_call",
                            }
                        ],
                    )

            return _AutoToolRunnable()

    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(
            openai_api_key=None,
            openai_model="legacy-openai-model-ignored",
        )
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session, name="PRUNTIME-DP-T", address="1 Marina Boulevard", zip_code="018989")
            upsert_transport_ai_llm_settings(
                session,
                project_id=project.id,
                provider="deepseek",
                api_key="deepseek-test-secret-7788",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            user = _create_user(
                session,
                chave="RTDT",
                nome="Runtime Worker DeepSeek Tool Choice",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7999A", service_date=service_date)
            run = _create_transport_ai_run(
                session,
                actor_user_id=admin_user.id,
                service_date=service_date,
                openai_model="deepseek-v4-pro",
                llm_provider="deepseek",
                llm_model="deepseek-v4-pro",
                llm_reasoning_effort="high",
            )
            session.commit()

            valid_plan = _build_valid_plan(
                session,
                service_date=service_date,
                settings_obj=settings_obj,
                provider=provider,
            )
            build_calls: list[bool] = []

            def _fake_build_transport_ai_chat_model_for_provider(*, include_reasoning_effort=True, **kwargs):
                build_calls.append(include_reasoning_effort)
                return _MethodAwareChatModel(valid_plan)

            monkeypatch.setattr(
                transport_ai_agent_module,
                "build_transport_ai_chat_model_for_provider",
                _fake_build_transport_ai_chat_model_for_provider,
            )

            result = run_transport_ai_agent(
                db=session,
                run=run,
                settings_obj=settings_obj,
                provider=provider,
                model=None,
            )

            assert result.plan is not None
            assert result.plan.plan_key == valid_plan.plan_key
            assert result.openai_model == "deepseek-v4-pro"
            assert build_calls == [True]
            assert run.status == "proposed"
            assert run.completed_at is not None
    finally:
        engine.dispose()


def test_invoke_transport_ai_structured_model_falls_back_from_function_calling_when_tool_choice_is_unsupported(tmp_path):
    from sistema.app.services.transport_ai_agent import _invoke_transport_ai_structured_model

    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_structured_output_fallback.db")

    class _MethodAwareChatModel:
        def __init__(self, valid_plan: TransportAgentPlan) -> None:
            self.valid_plan = valid_plan
            self.structured_output_calls: list[dict[str, object]] = []
            self.bind_tools_calls: list[dict[str, object]] = []

        def with_structured_output(self, schema, **kwargs):
            self.structured_output_calls.append({"schema": schema, **kwargs})
            class _FunctionCallingRunnable:
                def invoke(self_inner, messages):
                    raise ValueError(
                        "Error code: 400 - {'error': {'message': 'deepseek-reasoner does not support this tool_choice'}}"
                    )

            return _FunctionCallingRunnable()

        def bind_tools(self, tools, **kwargs):
            self.bind_tools_calls.append({"tools": tools, **kwargs})
            owner = self

            class _AutoToolRunnable:
                def invoke(self_inner, messages):
                    return AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "TransportAgentPlan",
                                "args": owner.valid_plan.model_dump(mode="json"),
                                "id": "call_fallback",
                                "type": "tool_call",
                            }
                        ],
                    )

            return _AutoToolRunnable()

    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(transport_ai_agent_mode="agent")
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session, name="PRUNTIME-DP-S", address="1 Marina Boulevard", zip_code="018989")
            user = _create_user(
                session,
                chave="RTDS",
                nome="Runtime Worker DeepSeek Structured Output",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7333A", service_date=service_date)
            session.commit()

            valid_plan = _build_valid_plan(
                session,
                service_date=service_date,
                settings_obj=settings_obj,
                provider=provider,
            )
            model = _MethodAwareChatModel(valid_plan)

            parsed_plan, raw_response, parsing_error = _invoke_transport_ai_structured_model(
                model=model,
                messages=[],
            )

            assert parsed_plan is not None
            assert parsed_plan.plan_key == valid_plan.plan_key
            assert parsing_error is None
            assert isinstance(raw_response, AIMessage)
            assert [call["method"] for call in model.structured_output_calls] == ["function_calling"]
            assert model.bind_tools_calls[0]["tool_choice"] == "auto"
    finally:
        engine.dispose()


def test_run_transport_ai_agent_returns_valid_plan_in_deterministic_mode_without_openai_key(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_deterministic.db")
    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(
            transport_ai_agent_mode="deterministic",
            openai_api_key=None,
        )
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session, name="PRUNTIME1D", address="1 Marina Boulevard", zip_code="018989")
            user = _create_user(
                session,
                chave="R1D1",
                nome="Runtime Worker Deterministic",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7101A", service_date=service_date)
            run = _create_transport_ai_run(
                session,
                actor_user_id=admin_user.id,
                service_date=service_date,
                openai_model=settings_obj.openai_model,
            )
            session.commit()

            result = run_transport_ai_agent(
                db=session,
                run=run,
                settings_obj=settings_obj,
                provider=provider,
            )

            assert result.plan is not None
            assert result.validation_result is not None
            assert result.validation_result.ok is True
            assert result.raw_model_response_json is None
            assert result.attempt_count == 1
            assert run.status == "proposed"
            assert run.completed_at is not None
    finally:
        engine.dispose()


def test_run_transport_ai_agent_retries_invalid_response_until_plan_valid(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_retry.db")
    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(transport_ai_agent_mode="agent")
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session, name="PRUNTIME2", address="1 Marina Boulevard", zip_code="018989")
            upsert_transport_ai_llm_settings(
                session,
                project_id=project.id,
                provider="openai",
                api_key="sk-project-runtime-2002",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            user = _create_user(
                session,
                chave="RT02",
                nome="Runtime Worker Two",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7002A", service_date=service_date)
            run = _create_transport_ai_run(
                session,
                actor_user_id=admin_user.id,
                service_date=service_date,
                openai_model=settings_obj.openai_model,
            )
            session.commit()

            valid_plan = _build_valid_plan(
                session,
                service_date=service_date,
                settings_obj=settings_obj,
                provider=provider,
            )
            fake_model = _FakeChatModel([
                {
                    "raw": AIMessage(content="attempt one sk-test-openai-secret"),
                    "parsed": None,
                    "parsing_error": ValueError("invalid structured output sk-test-openai-secret"),
                },
                {
                    "raw": AIMessage(content="attempt two"),
                    "parsed": valid_plan,
                    "parsing_error": None,
                },
            ])

            result = run_transport_ai_agent(
                db=session,
                run=run,
                settings_obj=settings_obj,
                provider=provider,
                model=fake_model,
                max_validation_retries=1,
            )

            assert result.plan is not None
            assert result.plan.plan_key == valid_plan.plan_key
            assert result.attempt_count == 2
            assert len(fake_model.invocations) == 2
            assert run.status == "proposed"
    finally:
        engine.dispose()


def test_run_transport_ai_agent_marks_run_failed_after_retry_exhaustion(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_failed.db")
    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(transport_ai_agent_mode="agent")
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session, name="PRUNTIME3", address="1 Marina Boulevard", zip_code="018989")
            upsert_transport_ai_llm_settings(
                session,
                project_id=project.id,
                provider="openai",
                api_key="sk-project-runtime-3003",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            user = _create_user(
                session,
                chave="RT03",
                nome="Runtime Worker Three",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7003A", service_date=service_date)
            run = _create_transport_ai_run(
                session,
                actor_user_id=admin_user.id,
                service_date=service_date,
                openai_model=settings_obj.openai_model,
            )
            session.commit()

            fake_model = _FakeChatModel([
                {
                    "raw": AIMessage(content="attempt one"),
                    "parsed": None,
                    "parsing_error": ValueError("invalid response one"),
                },
                {
                    "raw": AIMessage(content="attempt two"),
                    "parsed": None,
                    "parsing_error": ValueError("invalid response two"),
                },
            ])

            result = run_transport_ai_agent(
                db=session,
                run=run,
                settings_obj=settings_obj,
                provider=provider,
                model=fake_model,
                max_validation_retries=1,
            )

            assert result.plan is None
            assert result.error_code == "transport_ai_agent_invalid_response"
            assert run.status == "failed"
            assert run.error_code == "transport_ai_agent_invalid_response"
            assert run.completed_at is not None
            assert len(fake_model.invocations) == 2
    finally:
        engine.dispose()


def test_run_transport_ai_agent_sanitizes_raw_response(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_sanitize.db")
    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(transport_ai_agent_mode="agent")
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session, name="PRUNTIME4", address="1 Marina Boulevard", zip_code="018989")
            upsert_transport_ai_llm_settings(
                session,
                project_id=project.id,
                provider="openai",
                api_key="sk-project-runtime-4004",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            user = _create_user(
                session,
                chave="RT04",
                nome="Runtime Worker Four",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7004A", service_date=service_date)
            run = _create_transport_ai_run(
                session,
                actor_user_id=admin_user.id,
                service_date=service_date,
                openai_model=settings_obj.openai_model,
            )
            session.commit()

            valid_plan = _build_valid_plan(
                session,
                service_date=service_date,
                settings_obj=settings_obj,
                provider=provider,
            )
            fake_model = _FakeChatModel([
                {
                    "raw": AIMessage(
                        content=(
                            "OpenAI key sk-test-openai-secret and mapbox pk.test-mapbox-secret and Bearer top-secret"
                        ),
                        additional_kwargs={
                            "api_key": "sk-test-openai-secret",
                            "access_token": "pk.test-mapbox-secret",
                        },
                    ),
                    "parsed": valid_plan,
                    "parsing_error": None,
                }
            ])

            result = run_transport_ai_agent(
                db=session,
                run=run,
                settings_obj=settings_obj,
                provider=provider,
                model=fake_model,
            )

            assert result.raw_model_response_json is not None
            assert "sk-test-openai-secret" not in result.raw_model_response_json
            assert "pk.test-mapbox-secret" not in result.raw_model_response_json
            assert "Bearer top-secret" not in result.raw_model_response_json
            assert "[REDACTED]" in result.raw_model_response_json
    finally:
        engine.dispose()


def test_run_transport_ai_agent_requires_persisted_llm_settings_in_agent_mode(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_agent_requires_llm_settings.db")
    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(
            transport_ai_agent_mode="agent",
            openai_api_key=None,
        )
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project = _create_project(session, name="PRUNTIME5", address="1 Marina Boulevard", zip_code="018989")
            user = _create_user(
                session,
                chave="RT05",
                nome="Runtime Worker Five",
                projeto=project.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            _create_transport_request(session, user_id=user.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7005A", service_date=service_date)
            run = _create_transport_ai_run(
                session,
                actor_user_id=admin_user.id,
                service_date=service_date,
                openai_model=settings_obj.openai_model,
            )
            session.commit()

            result = run_transport_ai_agent(
                db=session,
                run=run,
                settings_obj=settings_obj,
                provider=provider,
            )

            assert result.plan is None
            assert result.error_code == "transport_ai_agent_execution_failed"
            assert run.status == "failed"
            assert "Transport AI LLM settings have not been configured for this project yet." in (run.error_message or "")
    finally:
        engine.dispose()


def test_run_transport_ai_agent_fails_for_conflicting_project_llm_runtime_settings(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_project_conflict.db")
    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(
            transport_ai_agent_mode="agent",
            openai_api_key=None,
            openai_model="legacy-openai-model-ignored",
        )
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project_a = _create_project(session, name="PRUNTIME6A", address="1 Marina Boulevard", zip_code="018989")
            project_b = _create_project(session, name="PRUNTIME6B", address="2 Marina Boulevard", zip_code="018990")
            upsert_transport_ai_llm_settings(
                session,
                project_id=project_a.id,
                provider="openai",
                api_key="conflict-openai-secret",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            upsert_transport_ai_llm_settings(
                session,
                project_id=project_b.id,
                provider="deepseek",
                api_key="conflict-deepseek-secret",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            user_a = _create_user(
                session,
                chave="RT6A",
                nome="Runtime Worker Six A",
                projeto=project_a.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            user_b = _create_user(
                session,
                chave="RT6B",
                nome="Runtime Worker Six B",
                projeto=project_b.name,
                address="20 Bayfront Avenue",
                zip_code="018957",
            )
            _create_transport_request(session, user_id=user_a.id, service_date=service_date)
            _create_transport_request(session, user_id=user_b.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7666A", service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7667A", service_date=service_date)
            run = _create_transport_ai_run(
                session,
                actor_user_id=admin_user.id,
                service_date=service_date,
                openai_model=settings_obj.openai_model,
            )
            session.commit()

            result = run_transport_ai_agent(
                db=session,
                run=run,
                settings_obj=settings_obj,
                provider=provider,
                model=None,
            )

            assert result.plan is None
            assert result.error_code == "transport_ai_agent_execution_failed"
            assert run.status == "failed"
            assert "requires the same project-specific LLM provider" in (run.error_message or "")
    finally:
        engine.dispose()


def test_run_transport_ai_agent_fails_for_conflicting_project_api_keys_with_same_provider(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_ai_agent_runtime_project_key_conflict.db")
    try:
        service_date = date(2026, 5, 3)
        settings_obj = _build_settings(
            transport_ai_agent_mode="agent",
            openai_api_key=None,
            openai_model="legacy-openai-model-ignored",
        )
        provider = FakeTransportRouteProvider(settings_obj=settings_obj, allow_synthetic_geocode=False)

        with session_factory() as session:
            _configure_transport_settings(session)
            admin_user = _create_admin_user(session)
            project_a = _create_project(session, name="PRUNTIME7A", address="1 Marina Boulevard", zip_code="018989")
            project_b = _create_project(session, name="PRUNTIME7B", address="2 Marina Boulevard", zip_code="018990")
            upsert_transport_ai_llm_settings(
                session,
                project_id=project_a.id,
                provider="openai",
                api_key="same-provider-conflict-1111",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            upsert_transport_ai_llm_settings(
                session,
                project_id=project_b.id,
                provider="openai",
                api_key="same-provider-conflict-2222",
                actor_admin_user_id=admin_user.id,
                settings_obj=settings_obj,
            )
            user_a = _create_user(
                session,
                chave="RT7A",
                nome="Runtime Worker Seven A",
                projeto=project_a.name,
                address="10 Bayfront Avenue",
                zip_code="018956",
            )
            user_b = _create_user(
                session,
                chave="RT7B",
                nome="Runtime Worker Seven B",
                projeto=project_b.name,
                address="20 Bayfront Avenue",
                zip_code="018957",
            )
            _create_transport_request(session, user_id=user_a.id, service_date=service_date)
            _create_transport_request(session, user_id=user_b.id, service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7771A", service_date=service_date)
            _create_extra_vehicle_candidate(session, placa="SBA7772A", service_date=service_date)
            run = _create_transport_ai_run(
                session,
                actor_user_id=admin_user.id,
                service_date=service_date,
                openai_model=settings_obj.openai_model,
            )
            session.commit()

            result = run_transport_ai_agent(
                db=session,
                run=run,
                settings_obj=settings_obj,
                provider=provider,
                model=None,
            )

            assert result.plan is None
            assert result.error_code == "transport_ai_agent_execution_failed"
            assert run.status == "failed"
            assert "API key across all referenced projects" in (run.error_message or "")
    finally:
        engine.dispose()