"""Tests for Task E1 — GET /api/web/check/accident/state and POST /api/web/check/accident/open."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import patch

import sqlalchemy as sa
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# App bootstrap (must happen before importing the app)
# ---------------------------------------------------------------------------

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_checking.db")
os.environ.setdefault("FORMS_URL", "https://example.com/form")
os.environ.setdefault("DEVICE_SHARED_KEY", "device-test-key")
os.environ.setdefault("MOBILE_APP_SHARED_KEY", "mobile-test-key")
os.environ.setdefault("PROVIDER_SHARED_KEY", "TESTPROVIDER0001")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-admin-session-secret")
os.environ.setdefault("BOOTSTRAP_ADMIN_KEY", "HR70")
os.environ.setdefault("BOOTSTRAP_ADMIN_NAME", "Tamer Salmem")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "eAcacdLe2")
os.environ.setdefault("FORMS_QUEUE_ENABLED", "false")
os.environ.setdefault("TRANSPORT_EXPORTS_DIR", "./test_transport_exports")

from fastapi.testclient import TestClient  # noqa: E402

from sistema.app.database import Base, SessionLocal, engine  # noqa: E402
from sistema.app.main import app  # noqa: E402
from sistema.app.models import (  # noqa: E402
    Accident,
    AccidentArchive,
    AccidentUserReport,
    AccidentVideoUpload,
    Project,
    User,
)
from sistema.app.services.passwords import hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)

STATE_URL = "/api/web/check/accident/state"
OPEN_URL = "/api/web/check/accident/open"
WEB_LOGIN_URL = "/api/web/auth/login"

_WEB_CHAVE = "E1WB"
_WEB_SENHA = "WebE1Test!"
_WEB_PROJ = "E1PROJ"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_project(db: Session, name: str = _WEB_PROJ) -> Project:
    proj = db.execute(sa.select(Project).where(Project.name == name)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=name,
            country_code="SG",
            country_name="Singapore",
            timezone_name="Asia/Singapore",
            address="1 Addr",
            zip_code="123456",
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)
    return proj


def _ensure_web_user(db: Session) -> User:
    user = db.execute(sa.select(User).where(User.chave == _WEB_CHAVE)).scalar_one_or_none()
    if user is None:
        user = User(
            chave=_WEB_CHAVE,
            nome="E1 Web User",
            projeto=_WEB_PROJ,
            checkin=True,
            local="Site E1",
            last_active_at=datetime.now(tz=timezone.utc),
            inactivity_days=0,
            senha=hash_password(_WEB_SENHA),
            perfil=1,
        )
        db.add(user)
    else:
        user.senha = hash_password(_WEB_SENHA)
        user.checkin = True
    db.commit()
    db.refresh(user)
    return user


def _close_all_accidents(db: Session) -> None:
    now = datetime.now(tz=timezone.utc)
    db.execute(
        sa.update(Accident).where(Accident.closed_at.is_(None)).values(closed_at=now, updated_at=now)
    )
    db.execute(sa.delete(AccidentArchive))
    db.execute(sa.delete(AccidentVideoUpload))
    db.execute(sa.delete(AccidentUserReport))
    db.commit()


def _logged_in_web_client() -> TestClient:
    """Return a TestClient already logged in as the web user."""
    with SessionLocal() as db:
        _ensure_project(db)
        _ensure_web_user(db)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(WEB_LOGIN_URL, json={"chave": _WEB_CHAVE, "senha": _WEB_SENHA})
    assert resp.status_code == 200, f"Web login failed: {resp.status_code} {resp.text}"
    return client


# ---------------------------------------------------------------------------
# test_state_requires_session
# ---------------------------------------------------------------------------


def test_state_requires_session():
    """GET /check/accident/state without a session must return 401."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(STATE_URL, params={"chave": _WEB_CHAVE})
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# test_state_returns_inactive_when_none
# ---------------------------------------------------------------------------


def test_state_returns_inactive_when_none():
    """No active accident → is_active=False."""
    with SessionLocal() as db:
        _close_all_accidents(db)

    client = _logged_in_web_client()
    resp = client.get(STATE_URL, params={"chave": _WEB_CHAVE})

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is False
    assert data.get("accident_number_label") is None
    assert data.get("current_user_report") is None


# ---------------------------------------------------------------------------
# test_state_returns_user_report_when_active
# ---------------------------------------------------------------------------


def test_state_returns_user_report_when_active():
    """Active accident + user has a report → state contains accident details and current_user_report."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        user = _ensure_web_user(db)
        proj_id = proj.id
        user_id = user.id

    client = _logged_in_web_client()

    # Open accident via the endpoint itself (origin=web)
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        open_resp = client.post(
            OPEN_URL,
            json={
                "chave": _WEB_CHAVE,
                "project_id": proj_id,
                "location_id": None,
                "custom_location_name": "E1 Test Site",
                "zone": "safety",
                "status": "ok",
            },
        )
    assert open_resp.status_code == 200, open_resp.text

    resp = client.get(STATE_URL, params={"chave": _WEB_CHAVE})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is True
    assert data["accident_number_label"] is not None
    assert data["project_name"] == _WEB_PROJ
    assert data["location_name"] == "E1 Test Site"
    assert data["current_user_report"] is not None
    assert data["current_user_report"]["zone"] == "safety"
    assert data["current_user_report"]["status"] == "ok"


# ---------------------------------------------------------------------------
# test_open_creates_with_origin_web
# ---------------------------------------------------------------------------


def test_open_creates_with_origin_web():
    """POST /check/accident/open → creates accident with origin='web'."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        _ensure_web_user(db)
        proj_id = proj.id

    client = _logged_in_web_client()

    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        resp = client.post(
            OPEN_URL,
            json={
                "chave": _WEB_CHAVE,
                "project_id": proj_id,
                "location_id": None,
                "custom_location_name": "E1 Origin Check",
                "zone": "accident",
                "status": "help",
            },
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is True
    assert data["project_name"] == _WEB_PROJ

    # Verify origin=web in DB
    with SessionLocal() as db:
        accident = db.execute(sa.select(Accident).where(Accident.closed_at.is_(None))).scalar_one_or_none()
        assert accident is not None
        assert accident.origin == "web"
        assert accident.opened_by_user_id is not None
        assert accident.opened_by_admin_id is None


# ---------------------------------------------------------------------------
# test_open_returns_409_when_active
# ---------------------------------------------------------------------------


def test_open_returns_409_when_active():
    """POST /check/accident/open when an accident is already active → 409."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        _ensure_web_user(db)
        proj_id = proj.id

    client = _logged_in_web_client()

    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        # First open should succeed
        r1 = client.post(
            OPEN_URL,
            json={
                "chave": _WEB_CHAVE,
                "project_id": proj_id,
                "location_id": None,
                "custom_location_name": "409 Check Site",
                "zone": "safety",
                "status": "ok",
            },
        )
        assert r1.status_code == 200, r1.text

        # Second open must return 409
        r2 = client.post(
            OPEN_URL,
            json={
                "chave": _WEB_CHAVE,
                "project_id": proj_id,
                "location_id": None,
                "custom_location_name": "409 Check Site 2",
                "zone": "safety",
                "status": "ok",
            },
        )

    assert r2.status_code == 409, f"Expected 409, got {r2.status_code}: {r2.text}"


# ---------------------------------------------------------------------------
# test_open_publishes_brokers
# ---------------------------------------------------------------------------


def test_open_publishes_brokers():
    """POST /check/accident/open must call notify_admin_data_changed and notify_web_check_data_changed."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        _ensure_web_user(db)
        proj_id = proj.id

    client = _logged_in_web_client()

    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed") as mock_admin,
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed") as mock_web,
    ):
        resp = client.post(
            OPEN_URL,
            json={
                "chave": _WEB_CHAVE,
                "project_id": proj_id,
                "location_id": None,
                "custom_location_name": "Broker Check Site",
                "zone": "safety",
                "status": "ok",
            },
        )

    assert resp.status_code == 200, resp.text
    mock_admin.assert_called_once()
    mock_web.assert_called_once()


# ---------------------------------------------------------------------------
# E2 — report endpoint
# ---------------------------------------------------------------------------

REPORT_URL = "/api/web/check/accident/report"


def _open_accident_via_api(client: TestClient, proj_id: int) -> None:
    """Open an accident via the web API (mocking brokers)."""
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        r = client.post(
            OPEN_URL,
            json={
                "chave": _WEB_CHAVE,
                "project_id": proj_id,
                "location_id": None,
                "custom_location_name": "Report Test Site",
                "zone": "safety",
                "status": "ok",
            },
        )
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# test_report_409_when_no_active
# ---------------------------------------------------------------------------


def test_report_409_when_no_active():
    """POST /check/accident/report when no accident is active → 409."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        _ensure_project(db)
        _ensure_web_user(db)

    client = _logged_in_web_client()
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        resp = client.post(REPORT_URL, json={"chave": _WEB_CHAVE, "zone": "safety", "status": "ok"})

    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# test_report_upserts
# ---------------------------------------------------------------------------


def test_report_upserts():
    """POST /check/accident/report updates zone/status and returns updated state."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        _ensure_web_user(db)
        proj_id = proj.id

    client = _logged_in_web_client()
    _open_accident_via_api(client, proj_id)

    # First report: zone=safety, status=ok
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        r1 = client.post(REPORT_URL, json={"chave": _WEB_CHAVE, "zone": "safety", "status": "ok"})
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1["is_active"] is True
    assert d1["current_user_report"]["zone"] == "safety"
    assert d1["current_user_report"]["status"] == "ok"

    # Second report: zone=accident, status=help (upsert)
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
        patch("sistema.app.routers.web_check.queue_help_request_emails"),
    ):
        r2 = client.post(REPORT_URL, json={"chave": _WEB_CHAVE, "zone": "accident", "status": "help"})
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["current_user_report"]["zone"] == "accident"
    assert d2["current_user_report"]["status"] == "help"


# ---------------------------------------------------------------------------
# test_report_schedules_email_on_help_transition
# ---------------------------------------------------------------------------


def test_report_schedules_email_on_help_transition():
    """Transitioning to status=help must schedule queue_help_request_emails."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        _ensure_web_user(db)
        proj_id = proj.id

    client = _logged_in_web_client()
    _open_accident_via_api(client, proj_id)

    # Report status=ok first (no help transition)
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        client.post(REPORT_URL, json={"chave": _WEB_CHAVE, "zone": "safety", "status": "ok"})

    # Now transition to help → email should be scheduled
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
        patch("sistema.app.routers.web_check.queue_help_request_emails") as mock_queue,
    ):
        resp = client.post(REPORT_URL, json={"chave": _WEB_CHAVE, "zone": "accident", "status": "help"})

    assert resp.status_code == 200, resp.text
    mock_queue.assert_called_once()
    call_kwargs = mock_queue.call_args
    assert call_kwargs is not None


# ---------------------------------------------------------------------------
# test_report_does_not_schedule_email_on_repeat_help
# ---------------------------------------------------------------------------


def test_report_does_not_schedule_email_on_repeat_help():
    """Sending help again when already in help status must NOT re-schedule emails."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        _ensure_web_user(db)
        proj_id = proj.id

    client = _logged_in_web_client()
    _open_accident_via_api(client, proj_id)

    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
        patch("sistema.app.routers.web_check.queue_help_request_emails"),
    ):
        # First help → should schedule
        client.post(REPORT_URL, json={"chave": _WEB_CHAVE, "zone": "accident", "status": "help"})

    # Second help (already in help) → must NOT schedule
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
        patch("sistema.app.routers.web_check.queue_help_request_emails") as mock_no_queue,
    ):
        resp = client.post(REPORT_URL, json={"chave": _WEB_CHAVE, "zone": "accident", "status": "help"})

    assert resp.status_code == 200, resp.text
    mock_no_queue.assert_not_called()


# ---------------------------------------------------------------------------
# E3 — video upload tests
# ---------------------------------------------------------------------------

VIDEO_URL = "/api/web/check/accident/video"
_IDEM_KEY = "test-idem-key-001"


def _make_video_form(
    *,
    content: bytes = b"fake-video-data",
    content_type: str = "video/mp4",
    chave: str = _WEB_CHAVE,
    idempotency_key: str = _IDEM_KEY,
    duration_seconds: str | None = None,
) -> dict:
    """Build a multipart form dict for the video upload endpoint."""
    fields: dict = {
        "chave": (None, chave, "text/plain"),
        "idempotency_key": (None, idempotency_key, "text/plain"),
        "video": ("clip.mp4", content, content_type),
    }
    if duration_seconds is not None:
        fields["duration_seconds"] = (None, duration_seconds, "text/plain")
    return fields


def _open_and_get_client() -> tuple[TestClient, int]:
    """Open an accident and return (client, proj_id)."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        _ensure_web_user(db)
        proj_id = proj.id

    client = _logged_in_web_client()
    _open_accident_via_api(client, proj_id)
    return client, proj_id


# ---------------------------------------------------------------------------
# test_video_requires_active_accident
# ---------------------------------------------------------------------------


def test_video_requires_active_accident():
    """POST /check/accident/video when no accident is active → 409."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        _ensure_project(db)
        _ensure_web_user(db)

    client = _logged_in_web_client()
    resp = client.post(VIDEO_URL, files=_make_video_form())
    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# test_video_rejects_unsupported_type
# ---------------------------------------------------------------------------


def test_video_rejects_unsupported_type():
    """Unsupported content-type → 415."""
    client, _ = _open_and_get_client()

    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        resp = client.post(
            VIDEO_URL,
            files=_make_video_form(content_type="video/avi", idempotency_key="unsupported-type-key"),
        )

    assert resp.status_code == 415, f"Expected 415, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# test_video_rejects_oversized
# ---------------------------------------------------------------------------


def test_video_rejects_oversized():
    """Video > 50MB → 413."""
    client, _ = _open_and_get_client()

    oversized = b"x" * (50 * 1024 * 1024 + 1)
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        resp = client.post(
            VIDEO_URL,
            files=_make_video_form(content=oversized, idempotency_key="oversized-video-key1"),
        )

    assert resp.status_code == 413, f"Expected 413, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# test_video_upload_success
# ---------------------------------------------------------------------------


def test_video_upload_success():
    """Valid upload → 200 with video_id and public_url."""
    client, _ = _open_and_get_client()

    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        resp = client.post(
            VIDEO_URL,
            files=_make_video_form(idempotency_key="success-upload-key1"),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "video_id" in data
    assert "public_url" in data
    assert data["public_url"] != ""
    assert "captured_at" in data


# ---------------------------------------------------------------------------
# test_video_upload_idempotent
# ---------------------------------------------------------------------------


def test_video_upload_idempotent():
    """Same idempotency_key twice → same video_id returned."""
    client, _ = _open_and_get_client()

    idem = "idempotent-key-xyz1"
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        r1 = client.post(VIDEO_URL, files=_make_video_form(idempotency_key=idem))
        r2 = client.post(VIDEO_URL, files=_make_video_form(idempotency_key=idem))

    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    assert r1.json()["video_id"] == r2.json()["video_id"]
    assert r1.json()["public_url"] == r2.json()["public_url"]

