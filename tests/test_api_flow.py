import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from sqlalchemy import select

# Override settings before app import.
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./test_checking.db"
os.environ["FORMS_URL"] = "https://example.com/form"
os.environ["DEVICE_SHARED_KEY"] = "device-test-key"
os.environ["MOBILE_APP_SHARED_KEY"] = "mobile-test-key"
os.environ["PROVIDER_SHARED_KEY"] = "PETROBRASP80P82P83"
os.environ["ADMIN_SESSION_SECRET"] = "test-admin-session-secret"
os.environ["BOOTSTRAP_ADMIN_KEY"] = "HR70"
os.environ["BOOTSTRAP_ADMIN_NAME"] = "Tamer Salmem"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "eAcacdLe2"
os.environ["FORMS_QUEUE_ENABLED"] = "false"

test_db = Path("test_checking.db")
if test_db.exists():
    test_db.unlink()

from fastapi.testclient import TestClient

from sistema.app.main import app
from sistema.app.core.config import settings
from sistema.app.database import Base, SessionLocal, engine
from sistema.app.models import AdminAccessRequest, AdminUser, CheckEvent, CheckingHistory, FormsSubmission, User, UserSyncEvent, Vehicle
from sistema.app.routers import admin as admin_router
from sistema.app.services.admin_updates import AdminUpdatesBroker, admin_updates_broker
from sistema.app.services.forms_worker import FormsWorker
from sistema.app.services.forms_queue import process_forms_submission_queue_once
from sistema.app.services import forms_worker as forms_worker_module
from sistema.app.services import location_settings as location_settings_module
from sistema.app.services import user_activity as user_activity_module
from sistema.app.services.time_utils import now_sgt
from sistema.app.services.user_sync import find_user_by_chave, find_user_by_rfid, normalize_event_time


ADMIN_LOGIN_CHAVE = "HR70"
ADMIN_LOGIN_SENHA = "eAcacdLe2"
MOBILE_HEADERS = {"x-mobile-shared-key": "mobile-test-key"}
PROVIDER_HEADERS = {"x-provider-shared-key": "PETROBRASP80P82P83"}

Base.metadata.create_all(bind=engine)


def login_admin(client: TestClient, *, chave: str = ADMIN_LOGIN_CHAVE, senha: str = ADMIN_LOGIN_SENHA):
    return client.post("/api/admin/auth/login", json={"chave": chave, "senha": senha})


def ensure_admin_session(client: TestClient) -> None:
    session_response = client.get("/api/admin/auth/session")
    assert session_response.status_code == 200
    if session_response.json().get("authenticated"):
        return

    login_response = login_admin(client)
    assert login_response.status_code == 200, login_response.text


def get_user_by_rfid(db, rfid: str) -> User:
    user = find_user_by_rfid(db, rfid)
    assert user is not None
    return user


def get_user_by_chave(db, chave: str) -> User:
    user = find_user_by_chave(db, chave)
    assert user is not None
    return user


def test_health():
    with TestClient(app) as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


def test_vehicle_schema_and_user_transport_fields_persist_expected_values():
    with SessionLocal() as db:
        vehicle = Vehicle(placa="SGX1234A", tipo="van", lugares=18)
        db.add(vehicle)
        db.flush()

        user = User(
            rfid=None,
            nome="Usuario Transporte",
            chave="TR01",
            projeto="P80",
            placa="SGX1234A",
            end_rua="123 Harbour Road",
            zip="0012345678",
            local=None,
            checkin=None,
            time=None,
            last_active_at=now_sgt(),
            inactivity_days=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        persisted_vehicle = db.execute(select(Vehicle).where(Vehicle.placa == "SGX1234A")).scalar_one()
        persisted_user = db.execute(select(User).where(User.chave == "TR01")).scalar_one()

        assert persisted_vehicle.tipo == "van"
        assert persisted_vehicle.lugares == 18
        assert persisted_user.placa == "SGX1234A"
        assert persisted_user.end_rua == "123 Harbour Road"
        assert persisted_user.zip == "0012345678"


def test_mobile_sync_records_checkinghistory_entry():
    event_time = now_sgt().replace(microsecond=0)

    with TestClient(app) as client:
        response = client.post(
            "/api/mobile/events/sync",
            headers=MOBILE_HEADERS,
            json={
                "chave": "HC01",
                "projeto": "P82",
                "action": "checkin",
                "event_time": event_time.isoformat(),
                "client_event_id": f"android-{uuid.uuid4().hex}",
            },
        )
        assert response.status_code == 200

    with SessionLocal() as db:
        row = db.execute(
            select(CheckingHistory)
            .where(CheckingHistory.chave == "HC01")
            .order_by(CheckingHistory.id.desc())
            .limit(1)
        ).scalar_one()

    assert row.atividade == "check-in"
    assert row.projeto == "P82"
    assert row.informe == "normal"
    assert row.time.replace(tzinfo=ZoneInfo(settings.tz_name)) == event_time


def test_admin_users_support_extended_profile_fields_and_key_updates_history():
    with SessionLocal() as db:
        db.add(Vehicle(placa="TRP1234A", tipo="van", lugares=18))
        db.commit()

    with TestClient(app) as client:
        ensure_admin_session(client)
        created = client.post(
            "/api/admin/users",
            json={
                "rfid": "USR9001",
                "nome": "Usuario Completo",
                "chave": "UF01",
                "projeto": "P82",
                "placa": "TRP1234A",
                "end_rua": "123 Harbour Road",
                "zip": "0012345678",
                "cargo": "Cargo Inicial",
                "email": "USER@EXAMPLE.COM",
            },
        )
        assert created.status_code == 200

        sync_res = client.post(
            "/api/mobile/events/sync",
            headers=MOBILE_HEADERS,
            json={
                "chave": "UF01",
                "projeto": "P82",
                "action": "checkin",
                "event_time": now_sgt().isoformat(),
                "client_event_id": f"android-{uuid.uuid4().hex}",
            },
        )
        assert sync_res.status_code == 200

        users = client.get("/api/admin/users")
        assert users.status_code == 200
        user_row = next(row for row in users.json() if row["chave"] == "UF01")
        assert user_row["placa"] == "TRP1234A"
        assert user_row["end_rua"] == "123 Harbour Road"
        assert user_row["zip"] == "0012345678"
        assert user_row["cargo"] == "Cargo Inicial"
        assert user_row["email"] == "user@example.com"

        updated = client.post(
            "/api/admin/users",
            json={
                "user_id": user_row["id"],
                "rfid": "USR9002",
                "nome": "Usuario Ajustado",
                "chave": "UF02",
                "projeto": "P83",
                "placa": "TRP1234A",
                "end_rua": "456 Harbour Road",
                "zip": "0000001234",
                "cargo": "Cargo Final",
                "email": "final@example.com",
            },
        )
        assert updated.status_code == 200

        users_after = client.get("/api/admin/users")
        assert users_after.status_code == 200
        updated_row = next(row for row in users_after.json() if row["id"] == user_row["id"])
        assert updated_row["rfid"] == "USR9002"
        assert updated_row["nome"] == "Usuario Ajustado"
        assert updated_row["chave"] == "UF02"
        assert updated_row["projeto"] == "P83"
        assert updated_row["placa"] == "TRP1234A"
        assert updated_row["end_rua"] == "456 Harbour Road"
        assert updated_row["zip"] == "0000001234"
        assert updated_row["cargo"] == "Cargo Final"
        assert updated_row["email"] == "final@example.com"

    with SessionLocal() as db:
        sync_rows = db.execute(
            select(UserSyncEvent)
            .where(UserSyncEvent.user_id == user_row["id"])
            .order_by(UserSyncEvent.id)
        ).scalars().all()
        history_rows = db.execute(
            select(CheckingHistory)
            .where(CheckingHistory.chave == "UF02")
            .order_by(CheckingHistory.id)
        ).scalars().all()

    assert sync_rows
    assert all(row.chave == "UF02" for row in sync_rows)
    assert history_rows
    assert all(row.chave == "UF02" for row in history_rows)


def test_provider_endpoint_requires_valid_shared_key():
    with TestClient(app) as client:
        response = client.post(
            "/api/provider/updaterecords",
            json={
                "chave": "PV01",
                "nome": "Usuario Provider",
                "projeto": "P80",
                "atividade": "check-in",
                "informe": "normal",
                "data": "17/04/2026",
                "hora": "08:00:00",
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid provider shared key"


def test_provider_endpoint_creates_user_and_history_with_normalized_name():
    with TestClient(app) as client:
        response = client.post(
            "/api/provider/updaterecords",
            headers=PROVIDER_HEADERS,
            json={
                "chave": "PV11",
                "nome": "ADRIANO JOSE DA SILVA",
                "projeto": "P82",
                "atividade": "check-in",
                "informe": "normal",
                "data": "17/04/2026",
                "hora": "07:26:00",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["created_user"] is True
        assert payload["updated_current_state"] is True

    with SessionLocal() as db:
        user = get_user_by_chave(db, "PV11")
        history_rows = db.execute(
            select(CheckingHistory)
            .where(CheckingHistory.chave == "PV11")
            .order_by(CheckingHistory.id)
        ).scalars().all()
        provider_events = db.execute(
            select(UserSyncEvent)
            .where(UserSyncEvent.chave == "PV11", UserSyncEvent.source == "provider")
            .order_by(UserSyncEvent.id)
        ).scalars().all()
        forms_rows = db.execute(
            select(FormsSubmission)
            .where(FormsSubmission.chave == "PV11")
            .order_by(FormsSubmission.id)
        ).scalars().all()

    assert user.nome == "Adriano Jose da Silva"
    assert user.projeto == "P82"
    assert user.checkin is True
    assert user.time.strftime("%d/%m/%Y %H:%M:%S") == "17/04/2026 07:26:00"
    assert len(history_rows) == 1
    assert history_rows[0].atividade == "check-in"
    assert history_rows[0].informe == "normal"
    assert len(provider_events) == 1
    assert forms_rows == []


def test_provider_endpoint_never_enqueues_forms_even_for_multiple_events():
    with TestClient(app) as client:
        first = client.post(
            "/api/provider/updaterecords",
            headers=PROVIDER_HEADERS,
            json={
                "chave": "PV21",
                "nome": "USUARIO FORMS",
                "projeto": "P80",
                "atividade": "check-in",
                "informe": "normal",
                "data": "17/04/2026",
                "hora": "07:30:00",
            },
        )
        second = client.post(
            "/api/provider/updaterecords",
            headers=PROVIDER_HEADERS,
            json={
                "chave": "PV21",
                "nome": "USUARIO FORMS",
                "projeto": "P80",
                "atividade": "check-out",
                "informe": "normal",
                "data": "17/04/2026",
                "hora": "18:00:00",
            },
        )
        assert first.status_code == 200
        assert second.status_code == 200

    with SessionLocal() as db:
        forms_rows = db.execute(
            select(FormsSubmission)
            .where(FormsSubmission.chave == "PV21")
            .order_by(FormsSubmission.id)
        ).scalars().all()
        provider_log_rows = db.execute(
            select(CheckEvent)
            .where(CheckEvent.source == "provider", CheckEvent.project == "P80")
            .order_by(CheckEvent.id.desc())
        ).scalars().all()

    assert forms_rows == []
    assert provider_log_rows
    assert all("forms_skipped=true" in (row.details or "") for row in provider_log_rows[:2])


def test_provider_endpoint_updates_project_but_keeps_existing_name():
    with SessionLocal() as db:
        db.add(
            User(
                rfid=None,
                chave="PV12",
                nome="Nome Original",
                projeto="P80",
                local=None,
                checkin=None,
                time=None,
                last_active_at=now_sgt(),
                inactivity_days=0,
            )
        )
        db.commit()

    with TestClient(app) as client:
        response = client.post(
            "/api/provider/updaterecords",
            headers=PROVIDER_HEADERS,
            json={
                "chave": "PV12",
                "nome": "NOME NAO DEVE TROCAR",
                "projeto": "P83",
                "atividade": "check-out",
                "informe": "retroativo",
                "data": "17/04/2026",
                "hora": "19:40:00",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["created_user"] is False
        assert payload["updated_project"] is True

    with SessionLocal() as db:
        user = get_user_by_chave(db, "PV12")
        history_row = db.execute(
            select(CheckingHistory)
            .where(CheckingHistory.chave == "PV12")
            .order_by(CheckingHistory.id.desc())
            .limit(1)
        ).scalar_one()

    assert user.nome == "Nome Original"
    assert user.projeto == "P83"
    assert user.checkin is False
    assert history_row.atividade == "check-out"
    assert history_row.informe == "retroativo"


def test_provider_endpoint_keeps_newer_current_user_state_while_recording_older_history():
    newer_time = datetime(2026, 4, 18, 9, 0, tzinfo=ZoneInfo(settings.tz_name))
    with SessionLocal() as db:
        db.add(
            User(
                rfid=None,
                chave="PV13",
                nome="Usuario Atual",
                projeto="P82",
                local="main",
                checkin=False,
                time=newer_time,
                last_active_at=newer_time,
                inactivity_days=0,
            )
        )
        db.commit()

    with TestClient(app) as client:
        response = client.post(
            "/api/provider/updaterecords",
            headers=PROVIDER_HEADERS,
            json={
                "chave": "PV13",
                "nome": "IGNORADO",
                "projeto": "P82",
                "atividade": "check-in",
                "informe": "normal",
                "data": "17/04/2026",
                "hora": "08:00:00",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["updated_current_state"] is False

        duplicate = client.post(
            "/api/provider/updaterecords",
            headers=PROVIDER_HEADERS,
            json={
                "chave": "PV13",
                "nome": "IGNORADO",
                "projeto": "P82",
                "atividade": "check-in",
                "informe": "normal",
                "data": "17/04/2026",
                "hora": "08:00:00",
            },
        )
        assert duplicate.status_code == 200
        assert duplicate.json()["duplicate"] is True

    with SessionLocal() as db:
        user = get_user_by_chave(db, "PV13")
        history_rows = db.execute(
            select(CheckingHistory)
            .where(CheckingHistory.chave == "PV13")
            .order_by(CheckingHistory.id)
        ).scalars().all()
        provider_events = db.execute(
            select(UserSyncEvent)
            .where(UserSyncEvent.chave == "PV13", UserSyncEvent.source == "provider")
            .order_by(UserSyncEvent.id)
        ).scalars().all()

    assert normalize_event_time(user.time) == newer_time
    assert user.checkin is False
    assert user.local == "main"
    assert len(history_rows) == 2
    assert history_rows[0].atividade == "check-out"
    assert history_rows[1].atividade == "check-in"
    assert len(provider_events) == 1


def test_admin_stream_requires_valid_session():
    with TestClient(app) as client:
        forbidden = client.get("/api/admin/stream")
        assert forbidden.status_code == 401


def test_admin_routes_do_not_accept_legacy_header_only():
    with TestClient(app) as client:
        forbidden = client.get("/api/admin/pending", headers={"x-admin-key": "admin-test-key"})
        assert forbidden.status_code == 401


def test_admin_updates_broker_publishes_payload():
    broker = AdminUpdatesBroker()
    subscriber_id, queue = broker.subscribe()

    try:
        broker.publish("pending")
        payload = queue.get_nowait()
        assert '"reason": "pending"' in payload
        assert '"emitted_at":' in payload
    finally:
        broker.unsubscribe(subscriber_id)


def test_pending_registration_flow():
    with TestClient(app) as client:
        ensure_admin_session(client)
        heartbeat = client.post(
            "/api/device/heartbeat",
            json={"device_id": "ESP32-TEST", "shared_key": "device-test-key"},
        )
        assert heartbeat.status_code == 200

        scan_pending = client.post(
            "/api/scan",
            json={
                "local": "main",
                "rfid": "ABC12345",
                "action": "checkin",
                "device_id": "ESP32-TEST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_pending.status_code == 200
        assert scan_pending.json()["outcome"] == "pending_registration"
        assert scan_pending.json()["led"] == "orange_4s"

        pending_list = client.get("/api/admin/pending")
        assert pending_list.status_code == 200
        assert len(pending_list.json()) >= 1

        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "ABC12345", "nome": "Usuario Teste", "chave": "HR70", "projeto": "P80"},
        )
        assert save_user.status_code == 200

        checkin_rows = client.get("/api/admin/checkin")
        assert checkin_rows.status_code == 200
        assert all(row["rfid"] != "ABC12345" for row in checkin_rows.json())

        checkout_rows = client.get("/api/admin/checkout")
        assert checkout_rows.status_code == 200
        assert all(row["rfid"] != "ABC12345" for row in checkout_rows.json())


def test_unknown_rfid_goes_pending():
    with TestClient(app) as client:
        ensure_admin_session(client)
        scan_unknown = client.post(
            "/api/scan",
            json={
                "local": "main",
                "rfid": "ZZZ99999",
                "action": "checkout",
                "device_id": "ESP32-TEST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_unknown.status_code == 200
        assert scan_unknown.json()["outcome"] == "pending_registration"
        assert scan_unknown.json()["led"] == "orange_4s"

        events = client.get("/api/admin/events")
        assert events.status_code == 200
        assert any(event["status"] == "received" and event["request_path"] == "/api/scan" for event in events.json())
        assert any(event["status"] == "pending" and event["source"] == "device" for event in events.json())


def test_explicit_checkin_and_checkout_flow(monkeypatch):
    monkeypatch.setattr(
        FormsWorker,
        "submit_with_retries",
        lambda self, action, chave, projeto, ontime=True: {
            "success": True,
            "message": f"mocked {action}",
            "retry_count": 0,
        },
    )

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "CARD1000", "nome": "Usuario Fluxo", "chave": "AB12", "projeto": "P83"},
        )
        assert save_user.status_code == 200

        scan_checkin = client.post(
            "/api/scan",
            json={
                "local": "main",
                "rfid": "CARD1000",
                "action": "checkin",
                "device_id": "ESP32-TEST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_checkin.status_code == 200
        assert scan_checkin.json()["outcome"] == "submitted"
        assert scan_checkin.json()["led"] == "green_1s"

        processed_first = process_forms_submission_queue_once()
        assert processed_first >= 1

        checkin_rows = client.get("/api/admin/checkin")
        assert checkin_rows.status_code == 200
        assert any(row["rfid"] == "CARD1000" and row["local"] == "main" for row in checkin_rows.json())

        scan_checkin_again = client.post(
            "/api/scan",
            json={
                "local": "un83",
                "rfid": "CARD1000",
                "action": "checkin",
                "device_id": "ESP32-TEST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_checkin_again.status_code == 200
        assert scan_checkin_again.json()["outcome"] == "local_updated"
        assert scan_checkin_again.json()["led"] == "green_blink_3x_1s"

        checkin_rows_updated = client.get("/api/admin/checkin")
        assert checkin_rows_updated.status_code == 200
        assert any(row["rfid"] == "CARD1000" and row["local"] == "un83" for row in checkin_rows_updated.json())

        checkout_rows_after_checkin = client.get("/api/admin/checkout")
        assert checkout_rows_after_checkin.status_code == 200
        assert all(row["rfid"] != "CARD1000" for row in checkout_rows_after_checkin.json())

        scan_checkout = client.post(
            "/api/scan",
            json={
                "local": "co83",
                "rfid": "CARD1000",
                "action": "checkout",
                "device_id": "ESP32-TEST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_checkout.status_code == 200
        assert scan_checkout.json()["outcome"] == "submitted"
        assert scan_checkout.json()["led"] == "green_1s"

        processed_second = process_forms_submission_queue_once()
        assert processed_second >= 1

        checkout_rows = client.get("/api/admin/checkout")
        assert checkout_rows.status_code == 200
        assert any(row["rfid"] == "CARD1000" and row["local"] == "co83" for row in checkout_rows.json())

        checkin_rows_after = client.get("/api/admin/checkin")
        assert checkin_rows_after.status_code == 200
        assert all(row["rfid"] != "CARD1000" for row in checkin_rows_after.json())

        events = client.get("/api/admin/events")
        assert events.status_code == 200
        assert any(
            event["rfid"] == "CARD1000"
            and event["chave"] == "AB12"
            and event["request_path"] == "/api/scan"
            for event in events.json()
        )


def test_checkout_without_checkin_returns_red_2s(monkeypatch):
    monkeypatch.setattr(
        FormsWorker,
        "submit_with_retries",
        lambda self, action, chave, projeto, ontime=True: {
            "success": True,
            "message": f"mocked {action}",
            "retry_count": 0,
        },
    )

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "CARD2000", "nome": "Usuario Sem Checkin", "chave": "EF56", "projeto": "P80"},
        )
        assert save_user.status_code == 200

        scan_checkout = client.post(
            "/api/scan",
            json={
                "local": "main",
                "rfid": "CARD2000",
                "action": "checkout",
                "device_id": "ESP32-TEST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_checkout.status_code == 200
        assert scan_checkout.json()["outcome"] == "failed"
        assert scan_checkout.json()["led"] == "red_2s"
        assert "Check-in not found" in scan_checkout.json()["message"]

        events = client.get("/api/admin/events")
        assert events.status_code == 200
        assert any(event["rfid"] == "CARD2000" and event["status"] == "blocked" for event in events.json())


def test_repeated_same_day_checkout_updates_state_without_forms_submission(monkeypatch):
    monkeypatch.setattr(
        FormsWorker,
        "submit_with_retries",
        lambda self, action, chave, projeto, ontime=True: {
            "success": True,
            "message": f"mocked {action}",
            "retry_count": 0,
        },
    )

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "CARD2001", "nome": "Usuario Checkout Repetido", "chave": "EG57", "projeto": "P80"},
        )
        assert save_user.status_code == 200

        scan_checkin = client.post(
            "/api/scan",
            json={
                "local": "main",
                "rfid": "CARD2001",
                "action": "checkin",
                "device_id": "ESP32-TEST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_checkin.status_code == 200
        assert scan_checkin.json()["outcome"] == "submitted"

        first_checkout = client.post(
            "/api/scan",
            json={
                "local": "co80-a",
                "rfid": "CARD2001",
                "action": "checkout",
                "device_id": "ESP32-TEST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert first_checkout.status_code == 200
        assert first_checkout.json()["outcome"] == "submitted"

        second_checkout = client.post(
            "/api/scan",
            json={
                "local": "co80-b",
                "rfid": "CARD2001",
                "action": "checkout",
                "device_id": "ESP32-TEST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert second_checkout.status_code == 200
        assert second_checkout.json()["outcome"] == "local_updated"
        assert second_checkout.json()["led"] == "green_blink_3x_1s"

        with SessionLocal() as db:
            user = get_user_by_rfid(db, "CARD2001")
            queued = db.execute(select(FormsSubmission).where(FormsSubmission.rfid == "CARD2001")).scalars().all()

            assert user.checkin is False
            assert user.local == "co80-b"
            assert len(queued) == 2


def test_repeated_checkout_after_singapore_midnight_is_queued_again(monkeypatch):
    monkeypatch.setattr(
        FormsWorker,
        "submit_with_retries",
        lambda self, action, chave, projeto, ontime=True: {
            "success": True,
            "message": f"mocked {action}",
            "retry_count": 0,
        },
    )

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "CARD2002", "nome": "Usuario Midnight", "chave": "EG58", "projeto": "P83"},
        )
        assert save_user.status_code == 200

        with SessionLocal() as db:
            user = get_user_by_rfid(db, "CARD2002")
            prior_checkout = now_sgt() - timedelta(days=1)
            user.checkin = False
            user.local = "co83-old"
            user.time = prior_checkout
            user.last_active_at = prior_checkout
            db.commit()

        scan_checkout = client.post(
            "/api/scan",
            json={
                "local": "co83-new",
                "rfid": "CARD2002",
                "action": "checkout",
                "device_id": "ESP32-TEST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_checkout.status_code == 200
        assert scan_checkout.json()["outcome"] == "submitted"
        assert scan_checkout.json()["led"] == "green_1s"

        with SessionLocal() as db:
            user = get_user_by_rfid(db, "CARD2002")
            queued = db.execute(select(FormsSubmission).where(FormsSubmission.rfid == "CARD2002")).scalars().all()

            assert user.checkin is False
            assert user.local == "co83-new"
            assert len(queued) == 1


def test_forms_step_timeout_returns_red_blink_pattern(monkeypatch):
    monkeypatch.setattr(
        FormsWorker,
        "submit_with_retries",
        lambda self, action, chave, projeto, ontime=True: {
            "success": False,
            "message": "Step 'digitar_chave' not found within 10 seconds",
            "retry_count": 0,
            "error_code": "forms_step_timeout",
            "failed_step": "digitar_chave",
            "audit_events": [
                {
                    "source": "forms",
                    "action": "forms",
                    "status": "failed",
                    "message": "Forms step timeout",
                    "details": "step=digitar_chave; timeout=10",
                }
            ],
        },
    )

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "CARDFAIL", "nome": "Usuario Falha", "chave": "CD34", "projeto": "P80"},
        )
        assert save_user.status_code == 200

        scan_failed = client.post(
            "/api/scan",
            json={
                "local": "co80",
                "rfid": "CARDFAIL",
                "action": "checkin",
                "device_id": "ESP32-TEST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_failed.status_code == 200
        assert scan_failed.json()["outcome"] == "submitted"
        assert scan_failed.json()["led"] == "green_1s"

        processed = process_forms_submission_queue_once()
        assert processed >= 1

        events = client.get("/api/admin/events")
        assert events.status_code == 200
        assert any(event["rfid"] == "CARDFAIL" and event["status"] == "failed" for event in events.json())
        assert any(event["source"] == "forms" and event["status"] == "failed" for event in events.json())
        assert all(
            not (event["source"] == "forms" and event["message"] == "Forms step timeout")
            for event in events.json()
        )


def test_valid_scan_updates_user_before_forms_processing(monkeypatch):
    monkeypatch.setattr(
        FormsWorker,
        "submit_with_retries",
        lambda self, action, chave, projeto, ontime=True: {
            "success": True,
            "message": f"mocked {action}",
            "retry_count": 0,
        },
    )

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "CARDFAST", "nome": "Usuario Rapido", "chave": "QP12", "projeto": "P80"},
        )
        assert save_user.status_code == 200

        scan_response = client.post(
            "/api/scan",
            json={
                "local": "main",
                "rfid": "CARDFAST",
                "action": "checkin",
                "device_id": "ESP32-FAST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_response.status_code == 200
        assert scan_response.json()["outcome"] == "submitted"
        assert scan_response.json()["led"] == "green_1s"

        with SessionLocal() as db:
            user = get_user_by_rfid(db, "CARDFAST")
            queued = db.execute(select(FormsSubmission).where(FormsSubmission.rfid == "CARDFAST")).scalar_one()
            assert user.checkin is True
            assert user.local == "main"
            assert queued.status == "pending"


def test_forms_queue_processing_persists_failure_state(monkeypatch):
    monkeypatch.setattr(
        FormsWorker,
        "submit_with_retries",
        lambda self, action, chave, projeto, ontime=True: {
            "success": False,
            "message": "mocked queue failure",
            "retry_count": 2,
            "error_code": "forms_runtime_error",
            "failed_step": "botao_enviar",
            "audit_events": [
                {
                    "source": "forms",
                    "action": "forms",
                    "status": "failed",
                    "message": "Forms runtime error",
                    "details": "mocked queue failure",
                }
            ],
        },
    )

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "QUEUEFAIL", "nome": "Fila Falha", "chave": "LM34", "projeto": "P83"},
        )
        assert save_user.status_code == 200

        scan_response = client.post(
            "/api/scan",
            json={
                "local": "line-2",
                "rfid": "QUEUEFAIL",
                "action": "checkin",
                "device_id": "ESP32-QUEUE",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_response.status_code == 200
        assert scan_response.json()["outcome"] == "submitted"

        processed = process_forms_submission_queue_once()
        assert processed >= 1

        with SessionLocal() as db:
            queued = db.execute(select(FormsSubmission).where(FormsSubmission.rfid == "QUEUEFAIL")).scalar_one()
            assert queued.status == "failed"
            assert queued.retry_count == 2
            assert queued.last_error == "mocked queue failure"


def test_forms_success_generates_single_final_forms_event(monkeypatch):
    monkeypatch.setattr(
        FormsWorker,
        "submit_with_retries",
        lambda self, action, chave, projeto, ontime=True: {
            "success": True,
            "message": "Form submitted successfully",
            "retry_count": 0,
            "audit_events": [
                {
                    "source": "forms",
                    "action": "forms",
                    "status": "opened",
                    "message": "Microsoft Forms opened",
                    "details": None,
                },
                {
                    "source": "forms",
                    "action": "forms",
                    "status": "completed",
                    "message": "Microsoft Forms completed",
                    "details": "steps=ok; success_xpath_visible=true",
                },
            ],
        },
    )

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "FORMSOK", "nome": "Forms Final", "chave": "ZX12", "projeto": "P80"},
        )
        assert save_user.status_code == 200

        scan_response = client.post(
            "/api/scan",
            json={
                "local": "main",
                "rfid": "FORMSOK",
                "action": "checkin",
                "device_id": "ESP32-FORMS",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_response.status_code == 200

        processed = process_forms_submission_queue_once()
        assert processed >= 1

        events = client.get("/api/admin/events")
        assert events.status_code == 200
        forms_events = [event for event in events.json() if event["rfid"] == "FORMSOK" and event["source"] == "forms"]
        assert len(forms_events) == 1
        assert forms_events[0]["status"] == "success"
        assert "forms_details=steps=ok; success_xpath_visible=true" in (forms_events[0]["details"] or "")


def test_forms_worker_requires_success_xpath_after_submit(tmp_path, monkeypatch):
    xpath_dir = tmp_path / "xpath"
    xpath_dir.mkdir(parents=True)
    xpaths = {
        "digitar_chave.txt": "//digitar_chave",
        "confirmar_chave.txt": "//confirmar_chave",
        "botao_normal.txt": "//botao_normal",
        "botao_retroativo.txt": "//botao_retroativo",
        "botao_checkin.txt": "//botao_checkin",
        "botao_checkout.txt": "//botao_checkout",
        "botao_enviar.txt": "//botao_enviar",
        "sucesso.txt": "//sucesso",
        "botao_projeto_P80.txt": "//botao_projeto_P80",
        "botao_projeto_P82.txt": "//botao_projeto_P82",
        "botao_projeto_P83.txt": "//botao_projeto_P83",
    }
    for name, content in xpaths.items():
        (xpath_dir / name).write_text(content, encoding="utf-8")

    send_selector = "xpath=//botao_enviar"
    success_selector = "xpath=//sucesso"

    class FakeLocator:
        def __init__(self, page, selector: str):
            self.page = page
            self.selector = selector

        def fill(self, value: str) -> None:
            self.page.filled[self.selector] = value

        def click(self) -> None:
            self.page.clicked.append(self.selector)
            self.page.checked.add(self.selector)
            if self.selector == send_selector:
                self.page.success_visible = True
                self.page.url = f"{self.page.url}#submitted"

        def input_value(self) -> str:
            return self.page.filled.get(self.selector, "")

        def is_checked(self) -> bool:
            return self.selector in self.page.checked

        def inner_text(self) -> str:
            if self.selector == success_selector:
                return "Sua resposta foi enviada."
            return ""

    class FakePage:
        def __init__(self):
            self.url = ""
            self.success_visible = False
            self.filled = {}
            self.clicked = []
            self.checked = set()
            self.visible_selectors = {
                "xpath=//digitar_chave",
                "xpath=//confirmar_chave",
                "xpath=//botao_normal",
                "xpath=//botao_checkin",
                "xpath=//botao_checkout",
                send_selector,
                "xpath=//botao_projeto_P80",
                "xpath=//botao_projeto_P83",
            }

        def goto(self, url: str, timeout: int) -> None:
            self.url = url

        def wait_for_selector(self, selector: str, state: str = "visible", timeout: int = 0):
            if selector == success_selector and self.success_visible:
                return True
            if selector in self.visible_selectors:
                return True
            raise forms_worker_module.PlaywrightTimeoutError("timeout")

        def locator(self, selector: str) -> FakeLocator:
            return FakeLocator(self, selector)

    class FakeBrowser:
        def __init__(self, page: FakePage):
            self.page = page

        def new_page(self) -> FakePage:
            return self.page

        def close(self) -> None:
            return None

    class FakePlaywright:
        def __init__(self, page: FakePage):
            self.chromium = SimpleNamespace(launch=lambda headless=True: FakeBrowser(page))

    class FakePlaywrightContext:
        def __init__(self, page: FakePage):
            self.page = page

        def __enter__(self):
            return FakePlaywright(self.page)

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_page = FakePage()
    monkeypatch.setattr(forms_worker_module, "sync_playwright", lambda: FakePlaywrightContext(fake_page))

    worker = FormsWorker(assets_dir=tmp_path)
    result = worker.submit_with_retries(action="checkin", chave="HR70", projeto="P80")

    assert result["success"] is True
    completed_event = next(event for event in result["audit_events"] if event["status"] == "completed")
    assert "steps=digitar_chave:filled+verified,confirmar_chave:filled+verified,botao_normal:clicked+verified,botao_checkin:clicked+verified,botao_projeto_P80:clicked+verified,botao_enviar:clicked,sucesso:visible" in completed_event["details"]
    assert "success_xpath_visible=true" in completed_event["details"]
    assert "submit_to_success_ms=" in completed_event["details"]
    assert "success_text=Sua resposta foi enviada." in completed_event["details"]


def test_forms_worker_rejects_success_xpath_visible_before_submit(tmp_path, monkeypatch):
    xpath_dir = tmp_path / "xpath"
    xpath_dir.mkdir(parents=True)
    for name in [
        "digitar_chave.txt",
        "confirmar_chave.txt",
        "botao_normal.txt",
        "botao_retroativo.txt",
        "botao_checkin.txt",
        "botao_checkout.txt",
        "botao_enviar.txt",
        "sucesso.txt",
        "botao_projeto_P80.txt",
            "botao_projeto_P82.txt",
        "botao_projeto_P83.txt",
    ]:
        (xpath_dir / name).write_text(f"//{name}", encoding="utf-8")

    success_selector = "xpath=//sucesso.txt"

    class FakeLocator:
        def __init__(self, selector: str):
            self.selector = selector

        def fill(self, value: str) -> None:
            return None

        def click(self) -> None:
            return None

        def input_value(self) -> str:
            return "HR70"

        def is_checked(self) -> bool:
            return True

        def inner_text(self) -> str:
            return ""

    class FakePage:
        url = "https://example.com/form"

        def goto(self, url: str, timeout: int) -> None:
            self.url = url

        def wait_for_selector(self, selector: str, state: str = "visible", timeout: int = 0):
            if selector == success_selector:
                return True
            return True

        def locator(self, selector: str) -> FakeLocator:
            return FakeLocator(selector)

    class FakeBrowser:
        def new_page(self) -> FakePage:
            return FakePage()

        def close(self) -> None:
            return None

    class FakePlaywright:
        chromium = SimpleNamespace(launch=lambda headless=True: FakeBrowser())

    class FakePlaywrightContext:
        def __enter__(self):
            return FakePlaywright()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(forms_worker_module, "sync_playwright", lambda: FakePlaywrightContext())

    worker = FormsWorker(assets_dir=tmp_path)
    result = worker.submit_with_retries(action="checkin", chave="HR70", projeto="P80")

    assert result["success"] is False
    assert result["error_code"] == "forms_validation_error"
    assert "XPath de sucesso ja estava visivel antes do envio" in result["message"]


def test_forms_worker_fails_when_first_field_is_not_confirmed(tmp_path, monkeypatch):
    xpath_dir = tmp_path / "xpath"
    xpath_dir.mkdir(parents=True)
    xpaths = {
        "digitar_chave.txt": "//digitar_chave",
        "confirmar_chave.txt": "//confirmar_chave",
        "botao_normal.txt": "//botao_normal",
        "botao_retroativo.txt": "//botao_retroativo",
        "botao_checkin.txt": "//botao_checkin",
        "botao_checkout.txt": "//botao_checkout",
        "botao_enviar.txt": "//botao_enviar",
        "sucesso.txt": "//sucesso",
        "botao_projeto_P80.txt": "//botao_projeto_P80",
        "botao_projeto_P82.txt": "//botao_projeto_P82",
        "botao_projeto_P83.txt": "//botao_projeto_P83",
    }
    for name, content in xpaths.items():
        (xpath_dir / name).write_text(content, encoding="utf-8")

    class FakeLocator:
        def __init__(self, selector: str):
            self.selector = selector

        def fill(self, value: str) -> None:
            return None

        def click(self) -> None:
            return None

        def input_value(self) -> str:
            return ""

        def is_checked(self) -> bool:
            return False

        def inner_text(self) -> str:
            return ""

    class FakePage:
        url = "https://example.com/form"

        def goto(self, url: str, timeout: int) -> None:
            self.url = url

        def wait_for_selector(self, selector: str, state: str = "visible", timeout: int = 0):
            return True

        def locator(self, selector: str) -> FakeLocator:
            return FakeLocator(selector)

    class FakeBrowser:
        def new_page(self) -> FakePage:
            return FakePage()

        def close(self) -> None:
            return None

    class FakePlaywright:
        chromium = SimpleNamespace(launch=lambda headless=True: FakeBrowser())

    class FakePlaywrightContext:
        def __enter__(self):
            return FakePlaywright()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(forms_worker_module, "sync_playwright", lambda: FakePlaywrightContext())

    worker = FormsWorker(assets_dir=tmp_path)
    result = worker.submit_with_retries(action="checkin", chave="HR70", projeto="P80")

    assert result["success"] is False
    assert result["error_code"] == "forms_step_validation_failed"
    assert result["failed_step"] == "digitar_chave"
    assert "expected_value=HR70" in result["audit_events"][0]["details"]


def test_heartbeat_success_is_not_logged_in_events():
    with TestClient(app) as client:
        ensure_admin_session(client)
        heartbeat = client.post(
            "/api/device/heartbeat",
            json={"device_id": "ESP32-TEST", "shared_key": "device-test-key"},
        )
        assert heartbeat.status_code == 200

        events = client.get("/api/admin/events")
        assert events.status_code == 200
        assert all(
            not (
                event["action"] == "heartbeat"
                and event["status"] == "success"
                and event["device_id"] == "ESP32-TEST"
            )
            for event in events.json()
        )


def test_heartbeat_failure_is_logged_in_events():
    with TestClient(app) as client:
        ensure_admin_session(client)
        heartbeat = client.post(
            "/api/device/heartbeat",
            json={"device_id": "ESP32-BAD", "shared_key": "wrong-key"},
        )
        assert heartbeat.status_code == 200
        assert heartbeat.json()["ok"] is False

        events = client.get("/api/admin/events")
        assert events.status_code == 200
        assert any(
            event["action"] == "heartbeat"
            and event["status"] == "failed"
            and event["device_id"] == "ESP32-BAD"
            for event in events.json()
        )


def test_remove_pending_registration():
    with TestClient(app) as client:
        ensure_admin_session(client)
        scan_unknown = client.post(
            "/api/scan",
            json={
                "local": "main",
                "rfid": "PENDING01",
                "action": "checkin",
                "device_id": "ESP32-TEST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_unknown.status_code == 200

        pending_list = client.get("/api/admin/pending")
        assert pending_list.status_code == 200
        pending_id = next(row["id"] for row in pending_list.json() if row["rfid"] == "PENDING01")

        remove_res = client.delete(f"/api/admin/pending/{pending_id}")
        assert remove_res.status_code == 200

        pending_list_after = client.get("/api/admin/pending")
        assert pending_list_after.status_code == 200
        assert all(row["id"] != pending_id for row in pending_list_after.json())


def test_list_and_remove_registered_user():
    with TestClient(app) as client:
        ensure_admin_session(client)
        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "USERDEL1", "nome": "Usuario Cadastro", "chave": "GH78", "projeto": "P83"},
        )
        assert save_user.status_code == 200

        checkout_before = client.get("/api/admin/checkout")
        assert checkout_before.status_code == 200
        assert all(row["rfid"] != "USERDEL1" for row in checkout_before.json())

        checkin_before = client.get("/api/admin/checkin")
        assert checkin_before.status_code == 200
        assert all(row["rfid"] != "USERDEL1" for row in checkin_before.json())

        events_before = client.get("/api/admin/events")
        assert events_before.status_code == 200
        assert any(event["rfid"] == "USERDEL1" for event in events_before.json())

        users_before = client.get("/api/admin/users")
        assert users_before.status_code == 200
        assert any(row["rfid"] == "USERDEL1" and row["nome"] == "Usuario Cadastro" for row in users_before.json())

        user_id = next(row["id"] for row in users_before.json() if row["rfid"] == "USERDEL1")

        remove_user = client.delete(f"/api/admin/users/{user_id}")
        assert remove_user.status_code == 200

        users_after = client.get("/api/admin/users")
        assert users_after.status_code == 200
        assert all(row["rfid"] != "USERDEL1" for row in users_after.json())

        checkout_after = client.get("/api/admin/checkout")
        assert checkout_after.status_code == 200
        assert all(row["rfid"] != "USERDEL1" for row in checkout_after.json())

        checkin_after = client.get("/api/admin/checkin")
        assert checkin_after.status_code == 200
        assert all(row["rfid"] != "USERDEL1" for row in checkin_after.json())

        events_after = client.get("/api/admin/events")
        assert events_after.status_code == 200
        assert any(event["rfid"] == "USERDEL1" for event in events_after.json())


def test_overdue_checkins_stay_visible_and_populate_missing_checkout(monkeypatch):
    fixed_now = datetime(2024, 4, 8, 12, 0, tzinfo=ZoneInfo(settings.tz_name))
    monkeypatch.setattr(admin_router, "now_sgt", lambda: fixed_now)
    monkeypatch.setattr(user_activity_module, "now_sgt", lambda: fixed_now)

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_a = client.post(
            "/api/admin/users",
            json={"rfid": "INA001", "nome": "Zelda Ativa", "chave": "AA11", "projeto": "P80"},
        )
        save_b = client.post(
            "/api/admin/users",
            json={"rfid": "INA002", "nome": "Ana Inativa", "chave": "BB22", "projeto": "P83"},
        )
        save_c = client.post(
            "/api/admin/users",
            json={"rfid": "INA003", "nome": "Bruno Inativo", "chave": "CC33", "projeto": "P80"},
        )
        save_d = client.post(
            "/api/admin/users",
            json={"rfid": "INA004", "nome": "Carlos Checkout", "chave": "DD55", "projeto": "P82"},
        )
        save_e = client.post(
            "/api/admin/users",
            json={"rfid": "INA005", "nome": "Eva Sem Checkout", "chave": "EE66", "projeto": "P83"},
        )
        assert save_a.status_code == 200
        assert save_b.status_code == 200
        assert save_c.status_code == 200
        assert save_d.status_code == 200
        assert save_e.status_code == 200

        with SessionLocal() as db:
            user_active = get_user_by_rfid(db, "INA001")
            user_active.checkin = True
            user_active.local = "main"
            user_active.time = fixed_now - timedelta(hours=3)
            user_active.last_active_at = fixed_now - timedelta(hours=3)
            user_active.inactivity_days = 0

            user_two = get_user_by_rfid(db, "INA002")
            user_two.checkin = True
            user_two.local = "co83"
            user_two.time = datetime(2024, 4, 3, 11, 0, tzinfo=ZoneInfo(settings.tz_name))
            user_two.last_active_at = user_two.time
            user_two.inactivity_days = 0

            user_three = get_user_by_rfid(db, "INA003")
            user_three.checkin = False
            user_three.local = "main"
            user_three.time = datetime(2024, 4, 3, 9, 0, tzinfo=ZoneInfo(settings.tz_name))
            user_three.last_active_at = user_three.time
            user_three.inactivity_days = 0

            user_four = get_user_by_rfid(db, "INA004")
            user_four.checkin = False
            user_four.local = "co80"
            user_four.time = datetime(2024, 4, 4, 9, 0, tzinfo=ZoneInfo(settings.tz_name))
            user_four.last_active_at = user_four.time
            user_four.inactivity_days = 0

            user_five = get_user_by_rfid(db, "INA005")
            user_five.checkin = True
            user_five.local = "un83"
            user_five.time = datetime(2024, 4, 5, 11, 0, tzinfo=ZoneInfo(settings.tz_name))
            user_five.last_active_at = user_five.time
            user_five.inactivity_days = 0
            db.commit()

        inactive_rows = client.get("/api/admin/inactive")
        assert inactive_rows.status_code == 200
        inactive_payload = inactive_rows.json()
        assert all(isinstance(row["id"], int) and row["id"] > 0 for row in inactive_payload)
        assert [row["nome"] for row in inactive_payload] == ["Ana Inativa", "Bruno Inativo"]
        assert [row["inactivity_days"] for row in inactive_payload] == [3, 3]
        assert [row["latest_action"] for row in inactive_payload] == ["checkin", "checkout"]
        assert inactive_payload[0]["latest_time"].startswith("2024-04-03T11:00:00")
        assert inactive_payload[1]["latest_time"].startswith("2024-04-03T09:00:00")

        checkin_rows = client.get("/api/admin/checkin")
        assert checkin_rows.status_code == 200
        checkin_payload = checkin_rows.json()
        assert any(row["rfid"] == "INA001" and row["id"] > 0 for row in checkin_payload)
        assert all(row["rfid"] != "INA002" for row in checkin_payload)
        assert any(row["rfid"] == "INA005" and row["id"] > 0 for row in checkin_payload)

        missing_checkout_rows = client.get("/api/admin/missing-checkout")
        assert missing_checkout_rows.status_code == 200
        missing_checkout_payload = missing_checkout_rows.json()
        assert [row["rfid"] for row in missing_checkout_payload] == ["INA005"]
        assert missing_checkout_payload[0]["time"].startswith("2024-04-05T11:00:00")

        checkout_rows = client.get("/api/admin/checkout")
        assert checkout_rows.status_code == 200
        checkout_payload = checkout_rows.json()
        assert all(row["rfid"] != "INA003" for row in checkout_payload)
        assert any(row["rfid"] == "INA004" and row["id"] > 0 for row in checkout_payload)


def test_weekends_do_not_increase_inactivity_before_threshold(monkeypatch):
    fixed_now = datetime(2024, 4, 7, 12, 0, tzinfo=ZoneInfo(settings.tz_name))
    monkeypatch.setattr(admin_router, "now_sgt", lambda: fixed_now)
    monkeypatch.setattr(user_activity_module, "now_sgt", lambda: fixed_now)

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "INA010", "nome": "Fabio Fim Semana", "chave": "DD44", "projeto": "P82"},
        )
        assert save_user.status_code == 200

        with SessionLocal() as db:
            weekend_user = get_user_by_rfid(db, "INA010")
            weekend_user.checkin = True
            weekend_user.local = "main"
            weekend_user.time = datetime(2024, 4, 4, 9, 0, tzinfo=ZoneInfo(settings.tz_name))
            weekend_user.last_active_at = weekend_user.time
            weekend_user.inactivity_days = 0
            db.commit()

        inactive_rows = client.get("/api/admin/inactive")
        assert inactive_rows.status_code == 200
        assert inactive_rows.json() == []

        checkin_rows = client.get("/api/admin/checkin")
        assert checkin_rows.status_code == 200
        assert any(row["rfid"] == "INA010" for row in checkin_rows.json())

        missing_checkout_rows = client.get("/api/admin/missing-checkout")
        assert missing_checkout_rows.status_code == 200
        assert any(row["rfid"] == "INA010" for row in missing_checkout_rows.json())

        with SessionLocal() as db:
            weekend_user = get_user_by_rfid(db, "INA010")
            assert weekend_user.inactivity_days == 1


def test_users_past_business_inactivity_threshold_stay_inactive_on_weekends(monkeypatch):
    fixed_now = datetime(2024, 4, 7, 12, 0, tzinfo=ZoneInfo(settings.tz_name))
    monkeypatch.setattr(admin_router, "now_sgt", lambda: fixed_now)
    monkeypatch.setattr(user_activity_module, "now_sgt", lambda: fixed_now)

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_checkin_user = client.post(
            "/api/admin/users",
            json={"rfid": "INA011", "nome": "Gil Checkin Weekend", "chave": "GF11", "projeto": "P80"},
        )
        save_checkout_user = client.post(
            "/api/admin/users",
            json={"rfid": "INA012", "nome": "Helena Checkout Weekend", "chave": "HF12", "projeto": "P82"},
        )
        assert save_checkin_user.status_code == 200
        assert save_checkout_user.status_code == 200

        with SessionLocal() as db:
            weekend_checkin_user = get_user_by_rfid(db, "INA011")
            weekend_checkin_user.checkin = True
            weekend_checkin_user.local = "main"
            weekend_checkin_user.time = datetime(2024, 4, 2, 9, 0, tzinfo=ZoneInfo(settings.tz_name))
            weekend_checkin_user.last_active_at = weekend_checkin_user.time
            weekend_checkin_user.inactivity_days = 0

            weekend_checkout_user = get_user_by_rfid(db, "INA012")
            weekend_checkout_user.checkin = False
            weekend_checkout_user.local = "co80"
            weekend_checkout_user.time = datetime(2024, 4, 2, 8, 0, tzinfo=ZoneInfo(settings.tz_name))
            weekend_checkout_user.last_active_at = weekend_checkout_user.time
            weekend_checkout_user.inactivity_days = 0
            db.commit()

        inactive_rows = client.get("/api/admin/inactive")
        assert inactive_rows.status_code == 200
        inactive_payload = inactive_rows.json()
        assert [row["nome"] for row in inactive_payload] == ["Gil Checkin Weekend", "Helena Checkout Weekend"]
        assert [row["inactivity_days"] for row in inactive_payload] == [3, 3]
        assert [row["latest_action"] for row in inactive_payload] == ["checkin", "checkout"]

        checkin_rows = client.get("/api/admin/checkin")
        assert checkin_rows.status_code == 200
        assert all(row["rfid"] != "INA011" for row in checkin_rows.json())

        checkout_rows = client.get("/api/admin/checkout")
        assert checkout_rows.status_code == 200
        assert all(row["rfid"] != "INA012" for row in checkout_rows.json())

        missing_checkout_rows = client.get("/api/admin/missing-checkout")
        assert missing_checkout_rows.status_code == 200
        assert all(row["rfid"] != "INA011" for row in missing_checkout_rows.json())

        with SessionLocal() as db:
            weekend_checkin_user = get_user_by_rfid(db, "INA011")
            weekend_checkout_user = get_user_by_rfid(db, "INA012")
            assert weekend_checkin_user.inactivity_days == 3
            assert weekend_checkout_user.inactivity_days == 3


def test_admin_presence_lists_follow_latest_activity_even_when_current_state_is_missing_or_stale():
    with SessionLocal() as db:
        stale_user = User(
            rfid="LATE001",
            chave="LT01",
            nome="Usuario Estado Antigo",
            projeto="P80",
            local="main",
            checkin=True,
            time=now_sgt() - timedelta(days=5),
            last_active_at=now_sgt() - timedelta(days=5),
            inactivity_days=0,
        )
        check_event_only_user = User(
            rfid="LATE002",
            chave="LT02",
            nome="Usuario Historico RFID",
            projeto="P83",
            local=None,
            checkin=None,
            time=None,
            last_active_at=now_sgt() - timedelta(days=3),
            inactivity_days=0,
        )
        no_activity_user = User(
            rfid="LATE003",
            chave="LT03",
            nome="Usuario Sem Atividade",
            projeto="P82",
            local=None,
            checkin=None,
            time=None,
            last_active_at=now_sgt(),
            inactivity_days=0,
        )
        db.add_all([stale_user, check_event_only_user, no_activity_user])
        db.flush()

        db.add(
            UserSyncEvent(
                user_id=stale_user.id,
                chave=stale_user.chave,
                rfid=stale_user.rfid,
                source="android",
                action="checkout",
                projeto=stale_user.projeto,
                local="co80",
                event_time=now_sgt() - timedelta(hours=6),
                created_at=now_sgt(),
                source_request_id=f"android-{uuid.uuid4().hex}",
                device_id=None,
            )
        )
        db.add(
            CheckEvent(
                idempotency_key=f"late-checkout-{uuid.uuid4().hex}",
                source="device",
                rfid="LATE002",
                action="checkout",
                status="queued",
                message="checkout antigo",
                details=None,
                project="P83",
                device_id="ESP32-LATE",
                local="main",
                request_path="/api/scan",
                http_status=202,
                event_time=now_sgt() - timedelta(days=2),
                submitted_at=None,
                retry_count=0,
            )
        )
        db.add(
            CheckEvent(
                idempotency_key=f"late-checkin-{uuid.uuid4().hex}",
                source="device",
                rfid="LATE002",
                action="checkin",
                status="queued",
                message="checkin recente",
                details=None,
                project="P83",
                device_id="ESP32-LATE",
                local="co83",
                request_path="/api/scan",
                http_status=202,
                event_time=now_sgt() - timedelta(hours=3),
                submitted_at=None,
                retry_count=0,
            )
        )
        db.commit()

    with TestClient(app) as client:
        ensure_admin_session(client)

        checkin_rows = client.get("/api/admin/checkin")
        assert checkin_rows.status_code == 200
        checkin_payload = checkin_rows.json()

        checkout_rows = client.get("/api/admin/checkout")
        assert checkout_rows.status_code == 200
        checkout_payload = checkout_rows.json()

        assert all(row["chave"] != "LT01" for row in checkin_payload)
        stale_checkout = next(row for row in checkout_payload if row["chave"] == "LT01")
        assert stale_checkout["local"] == "co80"
        assert stale_checkout["checkin"] is False

        fallback_checkin = next(row for row in checkin_payload if row["chave"] == "LT02")
        assert fallback_checkin["local"] == "co83"
        assert fallback_checkin["checkin"] is True
        assert all(row["chave"] != "LT02" for row in checkout_payload)

        assert all(row["chave"] != "LT03" for row in checkin_payload)
        assert all(row["chave"] != "LT03" for row in checkout_payload)


def test_admin_presence_lists_include_assiduidade_labels():
    with TestClient(app) as client:
        ensure_admin_session(client)

        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "ASSI01", "nome": "Usuario RFID", "chave": "AQ11", "projeto": "P80"},
        )
        assert save_user.status_code == 200

        rfid_checkin = client.post(
            "/api/scan",
            json={
                "local": "main",
                "rfid": "ASSI01",
                "action": "checkin",
                "device_id": "ESP32-ASSI",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert rfid_checkin.status_code == 200

        retroativo_checkout = client.post(
            "/api/mobile/events/forms-submit",
            headers=MOBILE_HEADERS,
            json={
                "chave": "AQ22",
                "projeto": "P82",
                "action": "checkout",
                "informe": "Retroativo",
                "event_time": now_sgt().isoformat(),
                "client_event_id": f"android-forms-assiduidade-{uuid.uuid4().hex}",
            },
        )
        assert retroativo_checkout.status_code == 200

        checkin_rows = client.get("/api/admin/checkin")
        assert checkin_rows.status_code == 200
        checkin_match = next(row for row in checkin_rows.json() if row["chave"] == "AQ11")
        assert checkin_match["assiduidade"] == "Normal"

        checkout_rows = client.get("/api/admin/checkout")
        assert checkout_rows.status_code == 200
        checkout_match = next(row for row in checkout_rows.json() if row["chave"] == "AQ22")
        assert checkout_match["assiduidade"] == "Retroativo"


def test_mobile_sync_autocreates_user_and_updates_state():
    with TestClient(app) as client:
        event_time = now_sgt().isoformat()
        response = client.post(
            "/api/mobile/events/sync",
            headers=MOBILE_HEADERS,
            json={
                "chave": "AP11",
                "projeto": "P80",
                "action": "checkin",
                "event_time": event_time,
                "client_event_id": f"android-{uuid.uuid4().hex}",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["duplicate"] is False
        assert payload["state"]["found"] is True
        assert payload["state"]["last_checkin_at"] is not None

        with SessionLocal() as db:
            user = get_user_by_chave(db, "AP11")
            assert user.nome == "Oriundo do Aplicativo"
            assert user.rfid is None
            assert user.checkin is True


def test_mobile_submit_autocreates_user_with_app_origin_name():
    client_event_id = f"android-submit-{uuid.uuid4().hex}"

    with TestClient(app) as client:
        response = client.post(
            "/api/mobile/events/submit",
            headers=MOBILE_HEADERS,
            json={
                "chave": "AS11",
                "projeto": "P83",
                "action": "checkout",
                "event_time": now_sgt().isoformat(),
                "client_event_id": client_event_id,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["duplicate"] is False
        assert payload["state"]["found"] is True
        assert payload["state"]["projeto"] == "P83"

        with SessionLocal() as db:
            user = get_user_by_chave(db, "AS11")
            assert user.nome == "Oriundo do Aplicativo"
            assert user.rfid is None
            assert user.projeto == "P83"


def test_mobile_forms_submit_autocreates_user_with_app_origin_name():
    client_event_id = f"android-forms-create-{uuid.uuid4().hex}"

    with TestClient(app) as client:
        response = client.post(
            "/api/mobile/events/forms-submit",
            headers=MOBILE_HEADERS,
            json={
                "chave": "AF11",
                "projeto": "P82",
                "action": "checkin",
                "informe": "normal",
                "event_time": now_sgt().isoformat(),
                "client_event_id": client_event_id,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["duplicate"] is False
        assert payload["state"]["found"] is True
        assert payload["state"]["projeto"] == "P82"

        with SessionLocal() as db:
            user = get_user_by_chave(db, "AF11")
            assert user.nome == "Oriundo do Aplicativo"
            assert user.rfid is None
            assert user.projeto == "P82"


def test_mobile_forms_submit_skips_same_day_repeated_action():
    first_event_time = now_sgt()
    second_event_time = first_event_time + timedelta(minutes=5)

    with TestClient(app) as client:
        first = client.post(
            "/api/mobile/events/forms-submit",
            headers=MOBILE_HEADERS,
            json={
                "chave": "AF12",
                "projeto": "P82",
                "action": "checkin",
                "local": "Area A",
                "informe": "normal",
                "event_time": first_event_time.isoformat(),
                "client_event_id": f"android-forms-same-day-1-{uuid.uuid4().hex}",
            },
        )
        second = client.post(
            "/api/mobile/events/forms-submit",
            headers=MOBILE_HEADERS,
            json={
                "chave": "AF12",
                "projeto": "P82",
                "action": "checkin",
                "local": "Area B",
                "informe": "normal",
                "event_time": second_event_time.isoformat(),
                "client_event_id": f"android-forms-same-day-2-{uuid.uuid4().hex}",
            },
        )

        assert first.status_code == 200
        assert first.json()["queued_forms"] is True
        assert second.status_code == 200
        assert second.json()["ok"] is True
        assert second.json()["duplicate"] is False
        assert second.json()["queued_forms"] is False

        with SessionLocal() as db:
            user = get_user_by_chave(db, "AF12")
            queued = db.execute(select(FormsSubmission).where(FormsSubmission.chave == "AF12")).scalars().all()
            sync_events = db.execute(
                select(UserSyncEvent).where(UserSyncEvent.chave == "AF12", UserSyncEvent.action == "checkin")
            ).scalars().all()

            assert user.checkin is True
            assert user.local == "Area B"
            assert len(queued) == 1
            assert len(sync_events) == 2


def test_mobile_forms_submit_requeues_same_action_after_singapore_midnight():
    first_event_time = now_sgt() - timedelta(days=1)
    second_event_time = now_sgt()

    with TestClient(app) as client:
        first = client.post(
            "/api/mobile/events/forms-submit",
            headers=MOBILE_HEADERS,
            json={
                "chave": "AF13",
                "projeto": "P83",
                "action": "checkin",
                "local": "Area A",
                "informe": "normal",
                "event_time": first_event_time.isoformat(),
                "client_event_id": f"android-forms-next-day-1-{uuid.uuid4().hex}",
            },
        )
        second = client.post(
            "/api/mobile/events/forms-submit",
            headers=MOBILE_HEADERS,
            json={
                "chave": "AF13",
                "projeto": "P83",
                "action": "checkin",
                "local": "Area C",
                "informe": "normal",
                "event_time": second_event_time.isoformat(),
                "client_event_id": f"android-forms-next-day-2-{uuid.uuid4().hex}",
            },
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["ok"] is True
        assert second.json()["duplicate"] is False
        assert second.json()["queued_forms"] is True

        with SessionLocal() as db:
            queued = db.execute(select(FormsSubmission).where(FormsSubmission.chave == "AF13")).scalars().all()
            user = get_user_by_chave(db, "AF13")

            assert len(queued) == 2
            assert user.checkin is True
            assert user.local == "Area C"


def test_mobile_state_returns_current_location_for_checked_in_user():
    with TestClient(app) as client:
        submit_response = client.post(
            "/api/mobile/events/forms-submit",
            headers=MOBILE_HEADERS,
            json={
                "chave": "AF14",
                "projeto": "P80",
                "action": "checkin",
                "local": "Base P80",
                "informe": "normal",
                "event_time": now_sgt().isoformat(),
                "client_event_id": f"android-forms-state-{uuid.uuid4().hex}",
            },
        )
        assert submit_response.status_code == 200

        state_response = client.get(
            "/api/mobile/state?chave=AF14",
            headers=MOBILE_HEADERS,
        )
        assert state_response.status_code == 200
        payload = state_response.json()
        assert payload["found"] is True
        assert payload["current_action"] == "checkin"
        assert payload["current_local"] == "Base P80"


def test_admin_checkin_list_accepts_mobile_user_without_rfid():
    with TestClient(app) as client:
        created = client.post(
            "/api/mobile/events/sync",
            headers=MOBILE_HEADERS,
            json={
                "chave": "AP15",
                "projeto": "P80",
                "action": "checkin",
                "event_time": now_sgt().isoformat(),
                "client_event_id": f"android-{uuid.uuid4().hex}",
            },
        )
        assert created.status_code == 200

        ensure_admin_session(client)
        checkin_rows = client.get("/api/admin/checkin")
        assert checkin_rows.status_code == 200
        payload = checkin_rows.json()
        matched = next(row for row in payload if row["chave"] == "AP15")
        assert matched["rfid"] is None
        assert matched["checkin"] is True


def test_mobile_sync_notifies_admin_realtime_subscribers():
    subscriber_id, queue = admin_updates_broker.subscribe()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/mobile/events/sync",
                headers=MOBILE_HEADERS,
                json={
                    "chave": "AP16",
                    "projeto": "P83",
                    "action": "checkout",
                    "event_time": now_sgt().isoformat(),
                    "client_event_id": f"android-{uuid.uuid4().hex}",
                },
            )

        assert response.status_code == 200
        payload = queue.get_nowait()
        assert '"reason": "checkout"' in payload
    finally:
        admin_updates_broker.unsubscribe(subscriber_id)


def test_mobile_sync_is_idempotent_for_same_event_id():
    with TestClient(app) as client:
        client_event_id = f"android-{uuid.uuid4().hex}"
        payload = {
            "chave": "AP12",
            "projeto": "P83",
            "action": "checkout",
            "event_time": now_sgt().isoformat(),
            "client_event_id": client_event_id,
        }
        first = client.post("/api/mobile/events/sync", headers=MOBILE_HEADERS, json=payload)
        second = client.post("/api/mobile/events/sync", headers=MOBILE_HEADERS, json=payload)
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["duplicate"] is True


def test_admin_can_edit_mobile_created_user_without_rfid():
    with TestClient(app) as client:
        created = client.post(
            "/api/mobile/events/sync",
            headers=MOBILE_HEADERS,
            json={
                "chave": "AP13",
                "projeto": "P80",
                "action": "checkin",
                "event_time": now_sgt().isoformat(),
                "client_event_id": f"android-{uuid.uuid4().hex}",
            },
        )
        assert created.status_code == 200

        ensure_admin_session(client)
        users = client.get("/api/admin/users")
        assert users.status_code == 200
        created_user = next(row for row in users.json() if row["chave"] == "AP13")
        assert created_user["rfid"] is None

        updated = client.post(
            "/api/admin/users",
            json={
                "user_id": created_user["id"],
                "nome": "Nome Corrigido",
                "chave": "AP13",
                "projeto": "P83",
            },
        )
        assert updated.status_code == 200

        users_after = client.get("/api/admin/users")
        assert users_after.status_code == 200
        updated_user = next(row for row in users_after.json() if row["id"] == created_user["id"])
        assert updated_user["nome"] == "Nome Corrigido"
        assert updated_user["projeto"] == "P83"


def test_admin_can_attach_rfid_to_mobile_created_user_by_unique_chave():
    with TestClient(app) as client:
        created = client.post(
            "/api/mobile/events/sync",
            headers=MOBILE_HEADERS,
            json={
                "chave": "AP14",
                "projeto": "P82",
                "action": "checkin",
                "event_time": now_sgt().isoformat(),
                "client_event_id": f"android-{uuid.uuid4().hex}",
            },
        )
        assert created.status_code == 200

        ensure_admin_session(client)
        attached = client.post(
            "/api/admin/users",
            json={
                "rfid": "APPRFID1",
                "nome": "Nome Ajustado",
                "chave": "AP14",
                "projeto": "P82",
            },
        )
        assert attached.status_code == 200
        assert attached.json()["linked_existing_user"] is True

        users = client.get("/api/admin/users")
        assert users.status_code == 200
        matched = [row for row in users.json() if row["chave"] == "AP14"]
        assert len(matched) == 1
        assert matched[0]["rfid"] == "APPRFID1"
        assert matched[0]["nome"] == "Nome Ajustado"
        assert matched[0]["projeto"] == "P82"


def test_pending_registration_links_rfid_to_existing_mobile_user_by_chave():
    with TestClient(app) as client:
        created = client.post(
            "/api/mobile/events/sync",
            headers=MOBILE_HEADERS,
            json={
                "chave": "AP17",
                "projeto": "P80",
                "action": "checkin",
                "event_time": now_sgt().isoformat(),
                "client_event_id": f"android-{uuid.uuid4().hex}",
            },
        )
        assert created.status_code == 200

        ensure_admin_session(client)
        scan_pending = client.post(
            "/api/scan",
            json={
                "local": "main",
                "rfid": "LINKRFID17",
                "action": "checkin",
                "device_id": "ESP32-LINK",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_pending.status_code == 200
        assert scan_pending.json()["outcome"] == "pending_registration"

        attached = client.post(
            "/api/admin/users",
            json={
                "rfid": "LINKRFID17",
                "nome": "Nome Vindo da Pendência",
                "chave": "AP17",
                "projeto": "P83",
            },
        )
        assert attached.status_code == 200
        assert attached.json()["linked_existing_user"] is True

        users = client.get("/api/admin/users")
        assert users.status_code == 200
        matched = [row for row in users.json() if row["chave"] == "AP17"]
        assert len(matched) == 1
        assert matched[0]["rfid"] == "LINKRFID17"
        assert matched[0]["nome"] == "Nome Vindo da Pendência"
        assert matched[0]["projeto"] == "P83"

        pending = client.get("/api/admin/pending")
        assert pending.status_code == 200
        assert all(row["rfid"] != "LINKRFID17" for row in pending.json())


def test_mobile_state_reflects_rfid_scan_history(monkeypatch):
    monkeypatch.setattr(
        FormsWorker,
        "submit_with_retries",
        lambda self, action, chave, projeto, ontime=True: {
            "success": True,
            "message": f"mocked {action}",
            "retry_count": 0,
        },
    )

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "RFIDSYNC1", "nome": "Usuario Sync", "chave": "SY11", "projeto": "P80"},
        )
        assert save_user.status_code == 200

        scan_response = client.post(
            "/api/scan",
            json={
                "local": "main",
                "rfid": "RFIDSYNC1",
                "action": "checkin",
                "device_id": "ESP32-SYNC",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_response.status_code == 200

        mobile_state = client.get("/api/mobile/state?chave=SY11", headers=MOBILE_HEADERS)
        assert mobile_state.status_code == 200
        payload = mobile_state.json()
        assert payload["found"] is True
        assert payload["current_action"] == "checkin"
        assert payload["last_checkin_at"] is not None


def test_mobile_forms_submit_accepts_retroativo_and_persists_ontime_false(monkeypatch):
    monkeypatch.setattr(
        FormsWorker,
        "submit_with_retries",
        lambda self, action, chave, projeto, ontime=True: {
            "success": True,
            "message": f"mocked {action}",
            "retry_count": 0,
        },
    )

    client_event_id = f"android-forms-{uuid.uuid4().hex}"

    with TestClient(app) as client:
        response = client.post(
            "/api/mobile/events/forms-submit",
            headers=MOBILE_HEADERS,
            json={
                "chave": "RT11",
                "projeto": "P82",
                "action": "checkin",
                "informe": "Retroativo",
                "event_time": now_sgt().isoformat(),
                "client_event_id": client_event_id,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["duplicate"] is False
        assert payload["queued_forms"] is True
        assert payload["state"]["current_action"] == "checkin"

        with SessionLocal() as db:
            queued = db.execute(
                select(FormsSubmission).where(FormsSubmission.request_id == client_event_id)
            ).scalar_one()
            sync_event = db.execute(
                select(UserSyncEvent).where(
                    UserSyncEvent.source == "android_forms",
                    UserSyncEvent.source_request_id == client_event_id,
                )
            ).scalar_one()
            assert queued.ontime is False
            assert sync_event.ontime is False

        processed = process_forms_submission_queue_once()
        assert processed >= 1

        ensure_admin_session(client)
        events = client.get("/api/admin/events")
        assert events.status_code == 200
        assert any(
            event["request_path"] == "/api/mobile/events/forms-submit"
            and event["ontime"] is False
            and event["status"] == "queued"
            and event["chave"] == "RT11"
            for event in events.json()
        )
        assert any(
            event["source"] == "forms"
            and event["ontime"] is False
            and event["status"] == "success"
            and event["chave"] == "RT11"
            for event in events.json()
        )


def test_mobile_forms_submit_is_idempotent_for_same_event_id():
    with TestClient(app) as client:
        client_event_id = f"android-forms-{uuid.uuid4().hex}"
        payload = {
            "chave": "RT12",
            "projeto": "P80",
            "action": "checkout",
            "informe": "normal",
            "event_time": now_sgt().isoformat(),
            "client_event_id": client_event_id,
        }
        first = client.post("/api/mobile/events/forms-submit", headers=MOBILE_HEADERS, json=payload)
        second = client.post("/api/mobile/events/forms-submit", headers=MOBILE_HEADERS, json=payload)
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["duplicate"] is True


def test_mobile_check_page_is_served_on_user_path():
    with TestClient(app) as client:
        response = client.get("/user")
        assert response.status_code == 200
        assert "Registrar" in response.text
        assert "Local" in response.text
        assert "Atualizar local" in response.text
        assert "Chave Petrobras" in response.text
        assert "Último Check-In" in response.text
        assert "Último Check-Out" in response.text
        assert "/api/web/check" in response.text
        assert "/api/web/check/state" in response.text
        assert "/api/web/check/location" in response.text


def test_transport_page_is_served_on_transport_path():
    with TestClient(app) as client:
        response = client.get("/transport")
        assert response.status_code == 200
        assert "User List" in response.text
        assert "Regular Car List" in response.text
        assert "Extra Car List" in response.text
        assert "Today" in response.text
        assert 'id="tela01menu"' in response.text
        assert 'id="tela01main_dir_down"' in response.text


def test_admin_page_is_served_on_admin_path():
    with TestClient(app) as client:
        response = client.get("/admin")
        assert response.status_code == 200
        assert "Checking Admin" in response.text
        assert "Acesso Administrativo" in response.text


def test_web_check_autocreates_user_with_web_origin_name():
    client_event_id = f"web-check-create-{uuid.uuid4().hex}"

    with TestClient(app) as client:
        response = client.post(
            "/api/web/check",
            json={
                "chave": "WB11",
                "projeto": "P82",
                "action": "checkin",
                "informe": "normal",
                "event_time": now_sgt().isoformat(),
                "client_event_id": client_event_id,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["duplicate"] is False
        assert payload["queued_forms"] is True
        assert payload["state"]["found"] is True
        assert payload["state"]["projeto"] == "P82"

        with SessionLocal() as db:
            user = get_user_by_chave(db, "WB11")
            assert user.nome == "Oriundo da Web"
            assert user.rfid is None
            assert user.projeto == "P82"


def test_web_location_match_returns_known_location_when_accuracy_is_good():
    with TestClient(app) as client:
        ensure_admin_session(client)

        create_location = client.post(
            "/api/admin/locations",
            json={
                "local": "Web Match P80",
                "latitude": 1.255936,
                "longitude": 103.611066,
                "tolerance_meters": 150,
            },
        )
        assert create_location.status_code == 200

        update_settings = client.post(
            "/api/admin/locations/settings",
            json={"location_accuracy_threshold_meters": 25},
        )
        assert update_settings.status_code == 200

        match_response = client.post(
            "/api/web/check/location",
            json={
                "latitude": 1.255936,
                "longitude": 103.611066,
                "accuracy_meters": 8,
            },
        )

        assert match_response.status_code == 200
        payload = match_response.json()
        assert payload["matched"] is True
        assert payload["resolved_local"] == "Web Match P80"
        assert payload["label"] == "Web Match P80"
        assert payload["status"] == "matched"
        assert payload["accuracy_threshold_meters"] == 25


def test_web_location_match_blocks_low_accuracy_before_matching():
    with TestClient(app) as client:
        ensure_admin_session(client)

        create_location = client.post(
            "/api/admin/locations",
            json={
                "local": "Web Accuracy P80",
                "latitude": 1.300001,
                "longitude": 103.800001,
                "tolerance_meters": 120,
            },
        )
        assert create_location.status_code == 200

        update_settings = client.post(
            "/api/admin/locations/settings",
            json={"location_accuracy_threshold_meters": 15},
        )
        assert update_settings.status_code == 200

        match_response = client.post(
            "/api/web/check/location",
            json={
                "latitude": 1.300001,
                "longitude": 103.800001,
                "accuracy_meters": 44,
            },
        )

        assert match_response.status_code == 200
        payload = match_response.json()
        assert payload["matched"] is False
        assert payload["resolved_local"] is None
        assert payload["label"] == "Precisao insuficiente"
        assert payload["status"] == "accuracy_too_low"
        assert payload["accuracy_threshold_meters"] == 15


def test_web_location_match_returns_unregistered_location_without_message_within_two_km():
    with TestClient(app) as client:
        ensure_admin_session(client)

        create_location = client.post(
            "/api/admin/locations",
            json={
                "local": "Web Nearby P80",
                "latitude": 1.255936,
                "longitude": 103.611066,
                "tolerance_meters": 120,
            },
        )
        assert create_location.status_code == 200

        update_settings = client.post(
            "/api/admin/locations/settings",
            json={"location_accuracy_threshold_meters": 25},
        )
        assert update_settings.status_code == 200

        match_response = client.post(
            "/api/web/check/location",
            json={
                "latitude": 1.260936,
                "longitude": 103.611066,
                "accuracy_meters": 8,
            },
        )

        assert match_response.status_code == 200
        payload = match_response.json()
        assert payload["matched"] is False
        assert payload["resolved_local"] is None
        assert payload["label"] == "Localização não Cadastrada"
        assert payload["status"] == "not_in_known_location"
        assert payload["message"] == ""
        assert payload["nearest_workplace_distance_meters"] < 2000


def test_web_location_match_returns_outside_workplace_without_message():
    with TestClient(app) as client:
        ensure_admin_session(client)

        create_location = client.post(
            "/api/admin/locations",
            json={
                "local": "Web Far P80",
                "latitude": 1.255936,
                "longitude": 103.611066,
                "tolerance_meters": 120,
            },
        )
        assert create_location.status_code == 200

        update_settings = client.post(
            "/api/admin/locations/settings",
            json={"location_accuracy_threshold_meters": 25},
        )
        assert update_settings.status_code == 200

        match_response = client.post(
            "/api/web/check/location",
            json={
                "latitude": 1.285936,
                "longitude": 103.611066,
                "accuracy_meters": 8,
            },
        )

        assert match_response.status_code == 200
        payload = match_response.json()
        assert payload["matched"] is False
        assert payload["resolved_local"] is None
        assert payload["label"] == "Fora do Ambiente de Trabalho"
        assert payload["status"] == "outside_workplace"
        assert payload["message"] == ""
        assert payload["nearest_workplace_distance_meters"] > 2000


def test_web_check_updates_user_local_when_location_is_provided():
    client_event_id = f"web-check-local-{uuid.uuid4().hex}"

    with TestClient(app) as client:
        response = client.post(
            "/api/web/check",
            json={
                "chave": "WB14",
                "projeto": "P80",
                "action": "checkin",
                "local": "Web Match P80",
                "informe": "normal",
                "event_time": now_sgt().isoformat(),
                "client_event_id": client_event_id,
            },
        )
        history = client.get("/api/web/check/state", params={"chave": "WB14"})

        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert history.status_code == 200
        assert history.json() == {
            "found": True,
            "chave": "WB14",
            "projeto": "P80",
            "current_action": "checkin",
            "current_local": "Web Match P80",
            "last_checkin_at": response.json()["state"]["last_checkin_at"],
            "last_checkout_at": None,
        }

        with SessionLocal() as db:
            user = get_user_by_chave(db, "WB14")
            assert user.local == "Web Match P80"


def test_web_check_reuses_flutter_like_hidden_project_for_checkout():
    first_event_time = now_sgt()
    second_event_time = first_event_time + timedelta(minutes=4)

    with TestClient(app) as client:
        first = client.post(
            "/api/web/check",
            json={
                "chave": "WB12",
                "projeto": "P83",
                "action": "checkout",
                "informe": "retroativo",
                "event_time": first_event_time.isoformat(),
                "client_event_id": f"web-check-1-{uuid.uuid4().hex}",
            },
        )
        second = client.post(
            "/api/web/check",
            json={
                "chave": "WB12",
                "projeto": "P83",
                "action": "checkout",
                "informe": "retroativo",
                "event_time": second_event_time.isoformat(),
                "client_event_id": f"web-check-2-{uuid.uuid4().hex}",
            },
        )

        assert first.status_code == 200
        assert first.json()["queued_forms"] is True
        assert second.status_code == 200
        assert second.json()["queued_forms"] is False

        with SessionLocal() as db:
            user = get_user_by_chave(db, "WB12")
            queued = db.execute(select(FormsSubmission).where(FormsSubmission.chave == "WB12")).scalars().all()
            sync_events = db.execute(
                select(UserSyncEvent).where(
                    UserSyncEvent.source == "web_forms",
                    UserSyncEvent.chave == "WB12",
                )
            ).scalars().all()
            request_events = db.execute(
                select(CheckEvent).where(CheckEvent.request_path == "/api/web/check", CheckEvent.rfid.is_(None))
            ).scalars().all()

            assert user.nome == "Oriundo da Web"
            assert user.projeto == "P83"
            assert user.checkin is False
            assert len(queued) == 1
            assert len(sync_events) == 2
            assert any(event.ontime is False and event.action == "checkout" for event in sync_events)
            assert any(event.action == "checkout" and event.status == "queued" for event in request_events)


def test_web_check_state_returns_latest_public_history():
    checkin_at = now_sgt() - timedelta(hours=1)
    checkout_at = now_sgt()

    with TestClient(app) as client:
        first = client.post(
            "/api/web/check",
            json={
                "chave": "WB13",
                "projeto": "P80",
                "action": "checkin",
                "informe": "normal",
                "event_time": checkin_at.isoformat(),
                "client_event_id": f"web-history-1-{uuid.uuid4().hex}",
            },
        )
        second = client.post(
            "/api/web/check",
            json={
                "chave": "WB13",
                "projeto": "P80",
                "action": "checkout",
                "informe": "normal",
                "event_time": checkout_at.isoformat(),
                "client_event_id": f"web-history-2-{uuid.uuid4().hex}",
            },
        )
        history = client.get("/api/web/check/state", params={"chave": "WB13"})

        assert first.status_code == 200
        assert second.status_code == 200
        assert history.status_code == 200

        payload = history.json()
        assert payload == {
            "found": True,
            "chave": "WB13",
            "projeto": "P80",
            "current_action": "checkout",
            "current_local": "Web",
            "last_checkin_at": checkin_at.replace(tzinfo=None).isoformat(),
            "last_checkout_at": checkout_at.replace(tzinfo=None).isoformat(),
        }


def test_web_check_state_returns_not_found_for_unknown_key():
    with TestClient(app) as client:
        response = client.get("/api/web/check/state", params={"chave": "ZZ99"})

        assert response.status_code == 200
        assert response.json() == {
            "found": False,
            "chave": "ZZ99",
            "projeto": None,
            "current_action": None,
            "current_local": None,
            "last_checkin_at": None,
            "last_checkout_at": None,
        }


def test_mobile_sync_accepts_project_p82():
    with TestClient(app) as client:
        response = client.post(
            "/api/mobile/events/sync",
            headers=MOBILE_HEADERS,
            json={
                "chave": "AP82",
                "projeto": "P82",
                "action": "checkin",
                "event_time": now_sgt().isoformat(),
                "client_event_id": f"android-{uuid.uuid4().hex}",
            },
        )
        assert response.status_code == 200
        assert response.json()["state"]["projeto"] == "P82"


def test_mobile_checkout_preserves_previous_checkin_history_without_existing_sync_events():
    previous_checkin_at = now_sgt() - timedelta(hours=2)
    checkout_at = now_sgt()

    with SessionLocal() as db:
        user = User(
            rfid=None,
            chave="LG11",
            nome="Legado Mobile",
            projeto="P80",
            local=None,
            checkin=True,
            time=previous_checkin_at,
            last_active_at=previous_checkin_at,
            inactivity_days=0,
        )
        db.add(user)
        db.commit()

    with TestClient(app) as client:
        response = client.post(
            "/api/mobile/events/sync",
            headers=MOBILE_HEADERS,
            json={
                "chave": "LG11",
                "projeto": "P80",
                "action": "checkout",
                "event_time": checkout_at.isoformat(),
                "client_event_id": f"android-{uuid.uuid4().hex}",
            },
        )

        assert response.status_code == 200
        state = response.json()["state"]
        assert state["current_action"] == "checkout"
        assert state["last_checkin_at"] is not None
        assert state["last_checkout_at"] is not None


def test_mobile_state_falls_back_to_check_events_history():
    checkin_at = now_sgt() - timedelta(hours=3)
    checkout_at = now_sgt() - timedelta(hours=1)

    with SessionLocal() as db:
        user = User(
            rfid="RFBACK1",
            chave="FB11",
            nome="Fallback Historico",
            projeto="P80",
            local="main",
            checkin=False,
            time=checkout_at,
            last_active_at=checkout_at,
            inactivity_days=0,
        )
        db.add(user)
        db.flush()
        db.add(
            CheckEvent(
                idempotency_key=f"fallback-checkin-{uuid.uuid4().hex}",
                source="device",
                rfid="RFBACK1",
                action="checkin",
                status="queued",
                message="checkin historico",
                details=None,
                project="P80",
                device_id="ESP32-FALLBACK",
                local="main",
                request_path="/api/scan",
                http_status=202,
                event_time=checkin_at,
                submitted_at=None,
                retry_count=0,
            )
        )
        db.add(
            CheckEvent(
                idempotency_key=f"fallback-checkout-{uuid.uuid4().hex}",
                source="device",
                rfid="RFBACK1",
                action="checkout",
                status="queued",
                message="checkout historico",
                details=None,
                project="P80",
                device_id="ESP32-FALLBACK",
                local="main",
                request_path="/api/scan",
                http_status=202,
                event_time=checkout_at,
                submitted_at=None,
                retry_count=0,
            )
        )
        db.commit()

    with TestClient(app) as client:
        response = client.get("/api/mobile/state?chave=FB11", headers=MOBILE_HEADERS)

        assert response.status_code == 200
        state = response.json()
        assert state["found"] is True
        assert state["current_action"] == "checkout"
        assert state["last_checkin_at"] is not None
        assert state["last_checkout_at"] is not None


def test_archive_events_creates_csv_clears_table_and_lists_downloads(tmp_path):
    settings.event_archives_dir = str(tmp_path / "event_archives")

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "ARC1000", "nome": "Usuario Arquivo", "chave": "JK90", "projeto": "P80"},
        )
        assert save_user.status_code == 200

        archive_res = client.post("/api/admin/events/archive")
        assert archive_res.status_code == 200

        archive_payload = archive_res.json()
        assert archive_payload["created"] is True
        assert archive_payload["cleared_count"] >= 1
        assert archive_payload["archive"]["file_name"].endswith(".csv")
        assert " a " in archive_payload["archive"]["period"]
        assert archive_payload["archive"]["record_count"] >= 1
        assert archive_payload["archives"]["total"] >= 1
        assert archive_payload["archives"]["total_size_bytes"] >= archive_payload["archive"]["size_bytes"]
        assert archive_payload["archives"]["items"][0]["file_name"] == archive_payload["archive"]["file_name"]

        events_after = client.get("/api/admin/events")
        assert events_after.status_code == 200
        assert events_after.json() == []

        archives_list = client.get("/api/admin/events/archives")
        assert archives_list.status_code == 200
        assert archives_list.json()["items"][0]["file_name"] == archive_payload["archive"]["file_name"]
        assert archives_list.json()["page"] == 1
        assert archives_list.json()["page_size"] == 8

        download_res = client.get(
            f"/api/admin/events/archives/{archive_payload['archive']['file_name']}",
        )
        assert download_res.status_code == 200
        assert "attachment;" in download_res.headers["content-disposition"]
        assert "event_time" in download_res.text
        assert "ARC1000" in download_res.text

        download_all_res = client.get("/api/admin/events/archives/download-all")
        assert download_all_res.status_code == 200
        assert download_all_res.headers["content-type"].startswith("application/zip")
        assert len(download_all_res.content) > 0


def test_delete_archived_event_csv(tmp_path):
    settings.event_archives_dir = str(tmp_path / "event_archives")

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "ARCDEL", "nome": "Usuario Delete", "chave": "DL90", "projeto": "P80"},
        )
        assert save_user.status_code == 200

        archive_res = client.post("/api/admin/events/archive")
        assert archive_res.status_code == 200
        file_name = archive_res.json()["archive"]["file_name"]

        delete_res = client.delete(f"/api/admin/events/archives/{file_name}")
        assert delete_res.status_code == 200
        assert delete_res.json()["ok"] is True

        list_res = client.get("/api/admin/events/archives")
        assert list_res.status_code == 200
        assert all(item["file_name"] != file_name for item in list_res.json()["items"])

        missing_res = client.get(f"/api/admin/events/archives/{file_name}")
        assert missing_res.status_code == 404


def test_event_archive_operations_are_logged(tmp_path):
    settings.event_archives_dir = str(tmp_path / "event_archives")

    with TestClient(app) as client:
        ensure_admin_session(client)
        save_user = client.post(
            "/api/admin/users",
            json={"rfid": "ARCAUD1", "nome": "Usuario Auditoria", "chave": "AU90", "projeto": "P80"},
        )
        assert save_user.status_code == 200

        archive_res = client.post("/api/admin/events/archive")
        assert archive_res.status_code == 200
        file_name = archive_res.json()["archive"]["file_name"]

        single_download = client.get(f"/api/admin/events/archives/{file_name}")
        assert single_download.status_code == 200

        download_all = client.get("/api/admin/events/archives/download-all")
        assert download_all.status_code == 200

        delete_res = client.delete(f"/api/admin/events/archives/{file_name}")
        assert delete_res.status_code == 200

        missing_res = client.get(f"/api/admin/events/archives/{file_name}")
        assert missing_res.status_code == 404

        events_res = client.get("/api/admin/events")
        assert events_res.status_code == 200
        assert events_res.json() == []

        with SessionLocal() as db:
            archive_events = db.execute(
                select(CheckEvent)
                .where(CheckEvent.action == "event_archive")
                .order_by(CheckEvent.id)
            ).scalars().all()

        assert any(
            event.status == "created"
            and event.request_path == "/api/admin/events/archive"
            for event in archive_events
        )
        assert any(
            event.status == "downloaded"
            and event.request_path == f"/api/admin/events/archives/{file_name}"
            for event in archive_events
        )
        assert any(
            event.status == "downloaded"
            and event.request_path == "/api/admin/events/archives/download-all"
            for event in archive_events
        )
        assert any(
            event.status == "removed"
            and event.request_path == f"/api/admin/events/archives/{file_name}"
            for event in archive_events
        )
        assert any(
            event.status == "failed"
            and event.http_status == 404
            and event.request_path == f"/api/admin/events/archives/{file_name}"
            for event in archive_events
        )


def test_archive_events_without_current_rows_returns_existing_archives(tmp_path):
    settings.event_archives_dir = str(tmp_path / "event_archives")

    with TestClient(app) as client:
        ensure_admin_session(client)
        first = client.post(
            "/api/admin/users",
            json={"rfid": "ARCEMPTY", "nome": "Usuario Empty", "chave": "EM90", "projeto": "P83"},
        )
        assert first.status_code == 200

        archive_first = client.post("/api/admin/events/archive")
        assert archive_first.status_code == 200
        assert archive_first.json()["created"] is True

        archive_second = client.post("/api/admin/events/archive")
        assert archive_second.status_code == 200
        assert archive_second.json()["created"] is False
        assert archive_second.json()["cleared_count"] == 0
        assert archive_second.json()["archives"]["total"] == 1


def test_list_event_archives_supports_backend_filter_and_pagination(tmp_path):
    settings.event_archives_dir = str(tmp_path / "event_archives")
    archive_dir = tmp_path / "event_archives"
    archive_dir.mkdir(parents=True, exist_ok=True)

    for index in range(12):
        file_path = archive_dir / f"2026-03-{index + 1:02d} 10-00-00 a 2026-03-{index + 1:02d} 11-00-00.csv"
        file_path.write_text("id,event_time\n1,2026-03-01T10:00:00\n", encoding="utf-8-sig")

    with TestClient(app) as client:
        ensure_admin_session(client)
        paged = client.get("/api/admin/events/archives?page=2&page_size=5")
        assert paged.status_code == 200
        payload = paged.json()
        assert payload["total"] == 12
        assert payload["page"] == 2
        assert payload["page_size"] == 5
        assert payload["total_pages"] == 3
        assert payload["total_size_bytes"] > 0
        assert len(payload["items"]) == 5

        filtered = client.get("/api/admin/events/archives?q=2026-03-01&page=1&page_size=5")
        assert filtered.status_code == 200
        filtered_payload = filtered.json()
        assert filtered_payload["total"] >= 1
        assert filtered_payload["query"] == "2026-03-01"
        assert all("2026-03-01" in item["period"] for item in filtered_payload["items"])


def test_admin_login_session_and_logout_flow():
    with TestClient(app) as client:
        session_before = client.get("/api/admin/auth/session")
        assert session_before.status_code == 200
        assert session_before.json()["authenticated"] is False

        login_response = login_admin(client)
        assert login_response.status_code == 200
        assert login_response.json()["ok"] is True

        session_after = client.get("/api/admin/auth/session")
        assert session_after.status_code == 200
        assert session_after.json()["authenticated"] is True
        assert session_after.json()["admin"]["chave"] == "HR70"

        admins = client.get("/api/admin/administrators")
        assert admins.status_code == 200
        assert any(row["chave"] == "HR70" and row["status"] == "active" for row in admins.json())

        logout_response = client.post("/api/admin/auth/logout")
        assert logout_response.status_code == 200
        assert logout_response.json()["ok"] is True

        session_final = client.get("/api/admin/auth/session")
        assert session_final.status_code == 200
        assert session_final.json()["authenticated"] is False


def test_admin_request_access_and_approval_flow():
    with TestClient(app) as client:
        request_response = client.post(
            "/api/admin/auth/request-access",
            json={
                "chave": "TS11",
                "nome_completo": "Teste Solicitante",
                "senha": "Senha@123",
            },
        )
        assert request_response.status_code == 200
        assert request_response.json()["ok"] is True

        duplicate_response = client.post(
            "/api/admin/auth/request-access",
            json={
                "chave": "TS11",
                "nome_completo": "Teste Solicitante",
                "senha": "Senha@123",
            },
        )
        assert duplicate_response.status_code == 409

        login_response = login_admin(client)
        assert login_response.status_code == 200

        list_response = client.get("/api/admin/administrators")
        assert list_response.status_code == 200
        pending_row = next(row for row in list_response.json() if row["chave"] == "TS11")
        assert pending_row["status"] == "pending"

        approve_response = client.post(f"/api/admin/administrators/requests/{pending_row['id']}/approve")
        assert approve_response.status_code == 200
        assert approve_response.json()["ok"] is True

        relogin = client.post("/api/admin/auth/logout")
        assert relogin.status_code == 200

        new_admin_login = login_admin(client, chave="TS11", senha="Senha@123")
        assert new_admin_login.status_code == 200

        with SessionLocal() as db:
            admin = db.execute(select(AdminUser).where(AdminUser.chave == "TS11")).scalar_one_or_none()
            pending = db.execute(select(AdminAccessRequest).where(AdminAccessRequest.chave == "TS11")).scalar_one_or_none()
            assert admin is not None
            assert pending is None


def test_admin_password_reset_and_redefine_flow():
    with TestClient(app) as client:
        login_response = login_admin(client)
        assert login_response.status_code == 200

        request_new_admin = client.post(
            "/api/admin/auth/request-access",
            json={
                "chave": "AB12",
                "nome_completo": "Admin Auxiliar",
                "senha": "SenhaNova1",
            },
        )
        assert request_new_admin.status_code == 200

        admins_before = client.get("/api/admin/administrators")
        pending_row = next(row for row in admins_before.json() if row["chave"] == "AB12")
        approve_response = client.post(f"/api/admin/administrators/requests/{pending_row['id']}/approve")
        assert approve_response.status_code == 200

        reset_response = client.post("/api/admin/auth/request-password-reset", json={"chave": "AB12"})
        assert reset_response.status_code == 200
        assert "Outro administrador" in reset_response.json()["message"]

        blocked_login = login_admin(client, chave="AB12", senha="SenhaNova1")
        assert blocked_login.status_code == 403

        admins_after_reset = client.get("/api/admin/administrators")
        reset_row = next(row for row in admins_after_reset.json() if row["chave"] == "AB12")
        assert reset_row["status"] == "password_reset_requested"

        set_password_response = client.post(
            f"/api/admin/administrators/{reset_row['id']}/set-password",
            json={"nova_senha": "SenhaFinal2"},
        )
        assert set_password_response.status_code == 200

        client.post("/api/admin/auth/logout")
        relogin_new_password = login_admin(client, chave="AB12", senha="SenhaFinal2")
        assert relogin_new_password.status_code == 200


def test_admin_event_audit_covers_new_auth_lifecycle():
    with TestClient(app) as client:
        first_request = client.post(
            "/api/admin/auth/request-access",
            json={
                "chave": "EV12",
                "nome_completo": "Evento Auditoria",
                "senha": "SenhaEvt1",
            },
        )
        assert first_request.status_code == 200

        duplicate_request = client.post(
            "/api/admin/auth/request-access",
            json={
                "chave": "EV12",
                "nome_completo": "Evento Auditoria",
                "senha": "SenhaEvt1",
            },
        )
        assert duplicate_request.status_code == 409

        assert login_admin(client).status_code == 200

        administrators = client.get("/api/admin/administrators")
        pending_row = next(row for row in administrators.json() if row["chave"] == "EV12")

        approve_response = client.post(f"/api/admin/administrators/requests/{pending_row['id']}/approve")
        assert approve_response.status_code == 200

        first_reset = client.post("/api/admin/auth/request-password-reset", json={"chave": "EV12"})
        assert first_reset.status_code == 200

        duplicate_reset = client.post("/api/admin/auth/request-password-reset", json={"chave": "EV12"})
        assert duplicate_reset.status_code == 409

        blocked_login = login_admin(client, chave="EV12", senha="SenhaEvt1")
        assert blocked_login.status_code == 403

        administrators_after_reset = client.get("/api/admin/administrators")
        reset_row = next(row for row in administrators_after_reset.json() if row["chave"] == "EV12")

        set_password = client.post(
            f"/api/admin/administrators/{reset_row['id']}/set-password",
            json={"nova_senha": "SenhaEvt2"},
        )
        assert set_password.status_code == 200

        revoke_response = client.post(f"/api/admin/administrators/{reset_row['id']}/revoke")
        assert revoke_response.status_code == 200

        events_response = client.get("/api/admin/events")
        assert events_response.status_code == 200
        events = events_response.json()

        assert any(
            event["action"] == "admin_request"
            and event["status"] == "pending"
            and event["request_path"] == "/api/admin/auth/request-access"
            and "chave=EV12" in (event["details"] or "")
            for event in events
        )
        assert any(
            event["action"] == "admin_request"
            and event["status"] == "failed"
            and event["http_status"] == 409
            and event["request_path"] == "/api/admin/auth/request-access"
            and "chave=EV12" in (event["details"] or "")
            for event in events
        )
        assert any(
            event["action"] == "admin_request"
            and event["status"] == "approved"
            and event["request_path"] == f"/api/admin/administrators/requests/{pending_row['id']}/approve"
            for event in events
        )
        assert any(
            event["action"] == "password"
            and event["status"] == "pending"
            and event["request_path"] == "/api/admin/auth/request-password-reset"
            for event in events
        )
        assert any(
            event["action"] == "password"
            and event["status"] == "failed"
            and event["http_status"] == 409
            and event["request_path"] == "/api/admin/auth/request-password-reset"
            for event in events
        )
        assert any(
            event["action"] == "login"
            and event["status"] == "blocked"
            and event["request_path"] == "/api/admin/auth/login"
            and "chave=EV12" in (event["details"] or "")
            for event in events
        )
        assert any(
            event["action"] == "password"
            and event["status"] == "updated"
            and event["request_path"] == f"/api/admin/administrators/{reset_row['id']}/set-password"
            for event in events
        )
        assert any(
            event["action"] == "admin_access"
            and event["status"] == "removed"
            and event["request_path"] == f"/api/admin/administrators/{reset_row['id']}/revoke"
            for event in events
        )


def test_admin_locations_crud_and_mobile_catalog_sync():
    with TestClient(app) as client:
        ensure_admin_session(client)
        reset_location_settings = client.post(
            "/api/admin/locations/settings",
            json={"location_accuracy_threshold_meters": 30},
        )
        assert reset_location_settings.status_code == 200

        create_location = client.post(
            "/api/admin/locations",
            json={
                "local": "Base P80",
                "latitude": 1.255936,
                "longitude": 103.611066,
                "tolerance_meters": 150,
            },
        )
        assert create_location.status_code == 200
        assert create_location.json()["ok"] is True

        locations = client.get("/api/admin/locations")
        assert locations.status_code == 200
        assert locations.json()["location_accuracy_threshold_meters"] == 30
        base_p80 = next(row for row in locations.json()["items"] if row["local"] == "Base P80")
        assert base_p80["coordinates"] == [{"latitude": 1.255936, "longitude": 103.611066}]
        assert base_p80["tolerance_meters"] == 150

        update_location_settings = client.post(
            "/api/admin/locations/settings",
            json={"location_accuracy_threshold_meters": 45},
        )
        assert update_location_settings.status_code == 200
        assert update_location_settings.json()["ok"] is True
        assert update_location_settings.json()["location_accuracy_threshold_meters"] == 45

        events = client.get("/api/admin/events")
        assert events.status_code == 200
        location_settings_event = next(
            event
            for event in events.json()
            if event["action"] == "location_config" and event["request_path"] == "/api/admin/locations/settings"
        )
        assert location_settings_event["chave"] == ADMIN_LOGIN_CHAVE
        assert location_settings_event["message"] == (
            "O valor do erro máximo para considerar a coordenada do usuário foi ajustado para 45 metros."
        )

        update_location = client.post(
            "/api/admin/locations",
            json={
                "location_id": base_p80["id"],
                "local": "Base P80",
                "coordinates": [
                    {"latitude": 1.255936, "longitude": 103.611066},
                    {"latitude": 1.260001, "longitude": 103.612002},
                ],
                "tolerance_meters": 250,
            },
        )
        assert update_location.status_code == 200
        assert update_location.json()["ok"] is True

        updated_locations = client.get("/api/admin/locations")
        assert updated_locations.status_code == 200
        updated_base_p80 = next(row for row in updated_locations.json()["items"] if row["local"] == "Base P80")
        assert updated_base_p80["coordinates"] == [
            {"latitude": 1.255936, "longitude": 103.611066},
            {"latitude": 1.260001, "longitude": 103.612002},
        ]
        assert updated_base_p80["latitude"] == 1.255936
        assert updated_base_p80["longitude"] == 103.611066

        mobile_catalog = client.get("/api/mobile/locations", headers=MOBILE_HEADERS)
        assert mobile_catalog.status_code == 200
        assert mobile_catalog.json()["location_accuracy_threshold_meters"] == 45
        assert "coordinate_update_frequency_headers" not in mobile_catalog.json()
        assert "coordinate_update_frequency_rows" not in mobile_catalog.json()
        synced_row = next(row for row in mobile_catalog.json()["items"] if row["local"] == "Base P80")
        assert synced_row["tolerance_meters"] == 250
        assert synced_row["coordinates"] == [
            {"latitude": 1.255936, "longitude": 103.611066},
            {"latitude": 1.260001, "longitude": 103.612002},
        ]
        assert synced_row["latitude"] == 1.255936
        assert synced_row["longitude"] == 103.611066

        remove_location = client.delete(f"/api/admin/locations/{base_p80['id']}")
        assert remove_location.status_code == 200
        assert remove_location.json()["ok"] is True


def test_mobile_forms_submit_uses_default_and_custom_local():
    with TestClient(app) as client:
        first_event = client.post(
            "/api/mobile/events/forms-submit",
            headers=MOBILE_HEADERS,
            json={
                "chave": "LX01",
                "projeto": "P83",
                "action": "checkin",
                "informe": "normal",
                "event_time": now_sgt().isoformat(),
                "client_event_id": f"mobile-{uuid.uuid4().hex}",
            },
        )
        assert first_event.status_code == 200
        assert first_event.json()["ok"] is True

        with SessionLocal() as db:
            user = get_user_by_chave(db, "LX01")
            queued = db.execute(
                select(FormsSubmission)
                .where(FormsSubmission.chave == "LX01")
                .order_by(FormsSubmission.id.desc())
            ).scalars().first()
            sync_event = db.execute(
                select(UserSyncEvent)
                .where(UserSyncEvent.chave == "LX01")
                .order_by(UserSyncEvent.id.desc())
            ).scalars().first()

            assert user.local == "Aplicativo"
            assert queued is not None and queued.local == "Aplicativo"
            assert sync_event is not None and sync_event.local == "Aplicativo"

        second_event = client.post(
            "/api/mobile/events/forms-submit",
            headers=MOBILE_HEADERS,
            json={
                "chave": "LX01",
                "projeto": "P83",
                "action": "checkout",
                "local": "Base P80",
                "informe": "retroativo",
                "event_time": now_sgt().isoformat(),
                "client_event_id": f"mobile-{uuid.uuid4().hex}",
            },
        )
        assert second_event.status_code == 200
        assert second_event.json()["ok"] is True

        with SessionLocal() as db:
            user = get_user_by_chave(db, "LX01")
            queued = db.execute(
                select(FormsSubmission)
                .where(FormsSubmission.chave == "LX01")
                .order_by(FormsSubmission.id.desc())
            ).scalars().first()
            sync_event = db.execute(
                select(UserSyncEvent)
                .where(UserSyncEvent.chave == "LX01")
                .order_by(UserSyncEvent.id.desc())
            ).scalars().first()

            assert user.local == "Base P80"
            assert queued is not None and queued.local == "Base P80"
            assert sync_event is not None and sync_event.local == "Base P80"
