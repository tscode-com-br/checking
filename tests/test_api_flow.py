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
                "rfid": "ABC12345",
                "device_id": "ESP32-TEST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_pending.status_code == 200
        assert scan_pending.json()["outcome"] == "pending_registration"

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
                "rfid": "ZZZ99999",
                "device_id": "ESP32-TEST",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_unknown.status_code == 200
        assert scan_unknown.json()["outcome"] == "pending_registration"
