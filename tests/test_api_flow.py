import os
import uuid
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select

# Override settings before app import.
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./test_checking.db"
os.environ["FORMS_URL"] = "https://example.com/form"
os.environ["DEVICE_SHARED_KEY"] = "device-test-key"
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
from sistema.app.database import SessionLocal
from sistema.app.models import AdminAccessRequest, AdminUser, FormsSubmission, User
from sistema.app.services.admin_updates import AdminUpdatesBroker
from sistema.app.services.forms_worker import FormsWorker
from sistema.app.services.forms_queue import process_forms_submission_queue_once
from sistema.app.services import forms_worker as forms_worker_module
from sistema.app.services.time_utils import now_sgt


ADMIN_LOGIN_CHAVE = "HR70"
ADMIN_LOGIN_SENHA = "eAcacdLe2"


def login_admin(client: TestClient, *, chave: str = ADMIN_LOGIN_CHAVE, senha: str = ADMIN_LOGIN_SENHA):
    return client.post("/api/admin/auth/login", json={"chave": chave, "senha": senha})


def ensure_admin_session(client: TestClient) -> None:
    session_response = client.get("/api/admin/auth/session")
    assert session_response.status_code == 200
    if session_response.json().get("authenticated"):
        return

    login_response = login_admin(client)
    assert login_response.status_code == 200, login_response.text


def test_health():
    with TestClient(app) as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


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
        lambda self, action, chave, projeto: {
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
        lambda self, action, chave, projeto: {
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
            user = db.get(User, "CARDFAST")
            queued = db.execute(select(FormsSubmission).where(FormsSubmission.rfid == "CARDFAST")).scalar_one()
            assert user.checkin is True
            assert user.local == "main"
            assert queued.status == "pending"


def test_forms_queue_processing_persists_failure_state(monkeypatch):
    monkeypatch.setattr(
        FormsWorker,
        "submit_with_retries",
        lambda self, action, chave, projeto: {
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
        lambda self, action, chave, projeto: {
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
        "botao_checkin.txt": "//botao_checkin",
        "botao_checkout.txt": "//botao_checkout",
        "botao_enviar.txt": "//botao_enviar",
        "sucesso.txt": "//sucesso",
        "botao_projeto_P80.txt": "//botao_projeto_P80",
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
        "botao_checkin.txt",
        "botao_checkout.txt",
        "botao_enviar.txt",
        "sucesso.txt",
        "botao_projeto_P80.txt",
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
        "botao_checkin.txt": "//botao_checkin",
        "botao_checkout.txt": "//botao_checkout",
        "botao_enviar.txt": "//botao_enviar",
        "sucesso.txt": "//sucesso",
        "botao_projeto_P80.txt": "//botao_projeto_P80",
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

        remove_user = client.delete("/api/admin/users/USERDEL1")
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


def test_inactive_users_are_listed_by_highest_inactivity_and_excluded_from_checkin_checkout(monkeypatch):
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
        assert save_a.status_code == 200
        assert save_b.status_code == 200
        assert save_c.status_code == 200

        scan_active = client.post(
            "/api/scan",
            json={
                "local": "main",
                "rfid": "INA001",
                "action": "checkin",
                "device_id": "ESP32-INACTIVE",
                "request_id": f"req-{uuid.uuid4().hex}",
                "shared_key": "device-test-key",
            },
        )
        assert scan_active.status_code == 200

        with SessionLocal() as db:
            inactive_three_days = now_sgt() - timedelta(days=3)
            inactive_five_days = now_sgt() - timedelta(days=5)

            user_active = db.get(User, "INA001")
            user_active.last_active_at = now_sgt()
            user_active.inactivity_days = 0

            user_two = db.get(User, "INA002")
            user_two.last_active_at = inactive_three_days
            user_two.inactivity_days = 0

            user_three = db.get(User, "INA003")
            user_three.last_active_at = inactive_five_days
            user_three.inactivity_days = 0

            still_active = db.get(User, "INA001")
            still_active.last_active_at = now_sgt()
            still_active.inactivity_days = 0
            db.commit()

        inactive_rows = client.get("/api/admin/inactive")
        assert inactive_rows.status_code == 200
        inactive_payload = inactive_rows.json()
        assert [row["nome"] for row in inactive_payload] == ["Bruno Inativo", "Ana Inativa"]
        assert [row["inactivity_days"] for row in inactive_payload] == [5, 3]

        checkin_rows = client.get("/api/admin/checkin")
        assert checkin_rows.status_code == 200
        assert all(row["rfid"] != "INA002" for row in checkin_rows.json())
        assert all(row["rfid"] != "INA003" for row in checkin_rows.json())


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
        assert len(events_after.json()) == 1
        assert events_after.json()[0]["action"] == "event_archive"
        assert events_after.json()[0]["status"] == "created"

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
        events = events_res.json()

        assert any(
            event["action"] == "event_archive"
            and event["status"] == "created"
            and event["request_path"] == "/api/admin/events/archive"
            for event in events
        )
        assert any(
            event["action"] == "event_archive"
            and event["status"] == "downloaded"
            and event["request_path"] == f"/api/admin/events/archives/{file_name}"
            for event in events
        )
        assert any(
            event["action"] == "event_archive"
            and event["status"] == "downloaded"
            and event["request_path"] == "/api/admin/events/archives/download-all"
            for event in events
        )
        assert any(
            event["action"] == "event_archive"
            and event["status"] == "removed"
            and event["request_path"] == f"/api/admin/events/archives/{file_name}"
            for event in events
        )
        assert any(
            event["action"] == "event_archive"
            and event["status"] == "failed"
            and event["http_status"] == 404
            and event["request_path"] == f"/api/admin/events/archives/{file_name}"
            for event in events
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
