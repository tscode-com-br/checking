import os
import uuid
from pathlib import Path

# Override settings before app import.
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./test_checking.db"
os.environ["FORMS_URL"] = "https://example.com/form"
os.environ["DEVICE_SHARED_KEY"] = "device-test-key"
os.environ["ADMIN_API_KEY"] = "admin-test-key"

test_db = Path("test_checking.db")
if test_db.exists():
    test_db.unlink()

from fastapi.testclient import TestClient

from sistema.app.main import app
from sistema.app.services.forms_worker import FormsWorker


def test_health():
    with TestClient(app) as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


def test_pending_registration_flow():
    with TestClient(app) as client:
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

        pending_list = client.get("/api/admin/pending", headers={"x-admin-key": "admin-test-key"})
        assert pending_list.status_code == 200
        assert len(pending_list.json()) >= 1

        save_user = client.post(
            "/api/admin/users",
            headers={"x-admin-key": "admin-test-key"},
            json={"rfid": "ABC12345", "nome": "Usuario Teste", "chave": "HR70", "projeto": "P80"},
        )
        assert save_user.status_code == 200

        checkin_rows = client.get("/api/admin/checkout", headers={"x-admin-key": "admin-test-key"})
        assert checkin_rows.status_code == 200


def test_unknown_rfid_goes_pending():
    with TestClient(app) as client:
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

        events = client.get("/api/admin/events", headers={"x-admin-key": "admin-test-key"})
        assert events.status_code == 200
        assert any(event["status"] == "received" and event["request_path"] == "/api/scan" for event in events.json())
        assert any(event["status"] == "pending" and event["source"] == "device" for event in events.json())


def test_explicit_checkin_and_checkout_flow(monkeypatch):
    monkeypatch.setattr(
        FormsWorker,
        "submit_with_retries",
        lambda self, action, chave, projeto: {
            "success": True,
            "message": f"mocked {action}",
            "retry_count": 0,
        },
    )

    with TestClient(app) as client:
        save_user = client.post(
            "/api/admin/users",
            headers={"x-admin-key": "admin-test-key"},
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

        checkin_rows = client.get("/api/admin/checkin", headers={"x-admin-key": "admin-test-key"})
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

        checkin_rows_updated = client.get("/api/admin/checkin", headers={"x-admin-key": "admin-test-key"})
        assert checkin_rows_updated.status_code == 200
        assert any(row["rfid"] == "CARD1000" and row["local"] == "un83" for row in checkin_rows_updated.json())

        checkout_rows_after_checkin = client.get("/api/admin/checkout", headers={"x-admin-key": "admin-test-key"})
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

        checkout_rows = client.get("/api/admin/checkout", headers={"x-admin-key": "admin-test-key"})
        assert checkout_rows.status_code == 200
        assert any(row["rfid"] == "CARD1000" and row["local"] == "co83" for row in checkout_rows.json())

        checkin_rows_after = client.get("/api/admin/checkin", headers={"x-admin-key": "admin-test-key"})
        assert checkin_rows_after.status_code == 200
        assert all(row["rfid"] != "CARD1000" for row in checkin_rows_after.json())


def test_checkout_without_checkin_returns_red_2s(monkeypatch):
    monkeypatch.setattr(
        FormsWorker,
        "submit_with_retries",
        lambda self, action, chave, projeto: {
            "success": True,
            "message": f"mocked {action}",
            "retry_count": 0,
        },
    )

    with TestClient(app) as client:
        save_user = client.post(
            "/api/admin/users",
            headers={"x-admin-key": "admin-test-key"},
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

        events = client.get("/api/admin/events", headers={"x-admin-key": "admin-test-key"})
        assert events.status_code == 200
        assert any(event["rfid"] == "CARD2000" and event["status"] == "blocked" for event in events.json())


def test_forms_step_timeout_returns_red_blink_pattern(monkeypatch):
    monkeypatch.setattr(
        FormsWorker,
        "submit_with_retries",
        lambda self, action, chave, projeto: {
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
        save_user = client.post(
            "/api/admin/users",
            headers={"x-admin-key": "admin-test-key"},
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
        assert scan_failed.json()["outcome"] == "failed"
        assert scan_failed.json()["led"] == "red_blink_5x_1s"

        events = client.get("/api/admin/events", headers={"x-admin-key": "admin-test-key"})
        assert events.status_code == 200
        assert any(event["rfid"] == "CARDFAIL" and event["status"] == "failed" for event in events.json())
        assert any(event["source"] == "forms" and event["status"] == "failed" for event in events.json())


def test_heartbeat_is_logged_in_events():
    with TestClient(app) as client:
        heartbeat = client.post(
            "/api/device/heartbeat",
            json={"device_id": "ESP32-TEST", "shared_key": "device-test-key"},
        )
        assert heartbeat.status_code == 200

        events = client.get("/api/admin/events", headers={"x-admin-key": "admin-test-key"})
        assert events.status_code == 200
        assert any(
            event["action"] == "heartbeat"
            and event["status"] == "success"
            and event["device_id"] == "ESP32-TEST"
            for event in events.json()
        )


def test_remove_pending_registration():
    with TestClient(app) as client:
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

        pending_list = client.get("/api/admin/pending", headers={"x-admin-key": "admin-test-key"})
        assert pending_list.status_code == 200
        pending_id = next(row["id"] for row in pending_list.json() if row["rfid"] == "PENDING01")

        remove_res = client.delete(f"/api/admin/pending/{pending_id}", headers={"x-admin-key": "admin-test-key"})
        assert remove_res.status_code == 200

        pending_list_after = client.get("/api/admin/pending", headers={"x-admin-key": "admin-test-key"})
        assert pending_list_after.status_code == 200
        assert all(row["id"] != pending_id for row in pending_list_after.json())
