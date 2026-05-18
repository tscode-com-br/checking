"""Tests for Task J1 — log_event calls in accident operations."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

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
    AdminUser,
    CheckEvent,
    EmailDeliveryLog,
    Project,
    User,
    UserProjectMembership,
)
from sistema.app.services.email_sender import deliver_pending_emails  # noqa: E402
from sistema.app.services.passwords import hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)

_NOW = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)

_WEB_CHAVE = "J1WB"
_WEB_SENHA = "WebJ1Test!"
_WEB_PROJ = "J1PROJ"

OPEN_URL = "/api/web/check/accident/open"
REPORT_URL = "/api/web/check/accident/report"
WEB_LOGIN_URL = "/api/web/auth/login"


# ---------------------------------------------------------------------------
# Shared helpers — web endpoint tests
# ---------------------------------------------------------------------------


def _ensure_project(db) -> Project:
    proj = db.execute(sa.select(Project).where(Project.name == _WEB_PROJ)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=_WEB_PROJ,
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


def _ensure_web_user(db) -> User:
    user = db.execute(sa.select(User).where(User.chave == _WEB_CHAVE)).scalar_one_or_none()
    if user is None:
        user = User(
            chave=_WEB_CHAVE,
            nome="J1 Web User",
            projeto=_WEB_PROJ,
            checkin=True,
            local="Site J1",
            last_active_at=_NOW,
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


def _close_all_accidents(db) -> None:
    now = datetime.now(tz=timezone.utc)
    db.execute(
        sa.update(Accident).where(Accident.closed_at.is_(None)).values(closed_at=now, updated_at=now)
    )
    db.execute(sa.delete(AccidentArchive))
    db.execute(sa.delete(AccidentVideoUpload))
    db.execute(sa.delete(AccidentUserReport))
    db.commit()


def _logged_in_web_client() -> TestClient:
    with SessionLocal() as db:
        _ensure_project(db)
        _ensure_web_user(db)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(WEB_LOGIN_URL, json={"chave": _WEB_CHAVE, "senha": _WEB_SENHA})
    assert resp.status_code == 200, f"Web login failed: {resp.status_code} {resp.text}"
    return client


def _latest_check_event(db, action: str) -> CheckEvent | None:
    return db.execute(
        sa.select(CheckEvent)
        .where(CheckEvent.action == action)
        .order_by(CheckEvent.event_time.desc())
    ).scalars().first()


# ---------------------------------------------------------------------------
# test_open_web_accident_logs_event
# ---------------------------------------------------------------------------


def test_open_web_accident_logs_event():
    """POST /check/accident/open must write action='accident_open', source='web' to check_events."""
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
                "custom_location_name": "J1 Log Site",
                "zone": "safety",
                "status": "ok",
            },
        )

    assert resp.status_code == 200, resp.text

    with SessionLocal() as db:
        event = _latest_check_event(db, "accident_open")
        assert event is not None, "Expected check_event with action='accident_open' to exist"
        assert event.source == "web"
        assert event.status == "done"
        assert event.rfid == _WEB_CHAVE


# ---------------------------------------------------------------------------
# test_report_web_accident_logs_event
# ---------------------------------------------------------------------------


def test_report_web_accident_logs_event():
    """POST /check/accident/report must write action='accident_user_report' to check_events."""
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
        client.post(
            OPEN_URL,
            json={
                "chave": _WEB_CHAVE,
                "project_id": proj_id,
                "location_id": None,
                "custom_location_name": "J1 Report Site",
                "zone": "safety",
                "status": "ok",
            },
        )
        resp = client.post(REPORT_URL, json={"chave": _WEB_CHAVE, "zone": "accident", "status": "ok"})

    assert resp.status_code == 200, resp.text

    with SessionLocal() as db:
        event = _latest_check_event(db, "accident_report")
        assert event is not None, "Expected check_event with action='accident_report' to exist"
        assert event.source == "web"
        assert event.status == "done"
        assert event.rfid == _WEB_CHAVE


# ---------------------------------------------------------------------------
# test_video_upload_logs_event
# ---------------------------------------------------------------------------


def test_video_upload_logs_event():
    """POST /check/accident/video must write action='accident_video' to check_events."""
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
        client.post(
            OPEN_URL,
            json={
                "chave": _WEB_CHAVE,
                "project_id": proj_id,
                "location_id": None,
                "custom_location_name": "J1 Video Site",
                "zone": "safety",
                "status": "ok",
            },
        )

    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
        patch("sistema.app.routers.web_check.stream_upload_to_storage", return_value=(1024, "https://cdn.example.com/video.webm")),
    ):
        video_bytes = b"\x00" * 16
        resp = client.post(
            "/api/web/check/accident/video",
            data={"chave": _WEB_CHAVE, "idempotency_key": "J1_VIDEO_KEY_01"},
            files={"video": ("clip.webm", video_bytes, "video/webm")},
        )

    assert resp.status_code == 200, resp.text

    with SessionLocal() as db:
        event = _latest_check_event(db, "accident_video")
        assert event is not None, "Expected check_event with action='accident_video' to exist"
        assert event.source == "web"
        assert event.status == "done"
        assert event.rfid == _WEB_CHAVE


# ---------------------------------------------------------------------------
# Email delivery log event (unit-test style, isolated DB)
# ---------------------------------------------------------------------------


def _make_isolated_factory(tmp_path: Path):
    engine_iso = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / 'j1.db').as_posix()}")
    Base.metadata.create_all(bind=engine_iso)
    return sessionmaker(bind=engine_iso, autocommit=False, autoflush=False, expire_on_commit=False)


class _CommitOnlySession:
    def __init__(self, factory):
        self._db = factory()

    def __enter__(self):
        return self._db

    def __exit__(self, *args):
        self._db.commit()


def _make_iso_project(db, name: str = "J1EMAILPROJ") -> Project:
    p = Project(
        name=name,
        country_code="SG",
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address="1 St",
        zip_code="099999",
    )
    db.add(p)
    db.flush()
    return p


def _make_iso_admin(db) -> AdminUser:
    a = AdminUser(chave="JE01", nome_completo="J1 Email Admin", created_at=_NOW, updated_at=_NOW)
    db.add(a)
    db.flush()
    return a


def _make_iso_accident(db, proj: Project, admin: AdminUser) -> Accident:
    a = Accident(
        accident_number=0,
        project_id=proj.id,
        project_name_snapshot=proj.name,
        location_name_snapshot="J1 Gate",
        location_is_registered=False,
        origin="admin",
        opened_by_admin_id=admin.id,
        opened_at=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )
    db.add(a)
    db.flush()
    return a


def _make_iso_user(db, chave: str) -> User:
    u = User(
        chave=chave,
        nome=f"User {chave}",
        email=f"{chave.lower()}@example.com",
        projeto="J1EMAILPROJ",
        checkin=True,
        local="Sala A",
        last_active_at=_NOW,
        inactivity_days=0,
    )
    db.add(u)
    db.flush()
    return u


def _make_iso_queued_log(db, accident: Accident, user: User) -> EmailDeliveryLog:
    log = EmailDeliveryLog(
        accident_id=accident.id,
        triggered_by_user_id=user.id,
        recipient_email=user.email,
        recipient_chave=user.chave,
        subject="SOCORRO",
        body_snapshot="Body",
        delivery_status="queued",
        queued_at=_NOW,
    )
    db.add(log)
    db.flush()
    return log


def test_deliver_pending_emails_logs_event(tmp_path: Path):
    """deliver_pending_emails must write action='accident_email_help' to check_events after SMTP delivery."""
    factory = _make_isolated_factory(tmp_path)

    setup_db = factory()
    proj = _make_iso_project(setup_db)
    admin = _make_iso_admin(setup_db)
    accident = _make_iso_accident(setup_db, proj, admin)
    user = _make_iso_user(setup_db, "JE02")
    log = _make_iso_queued_log(setup_db, accident, user)
    log_id = log.id
    setup_db.commit()
    setup_db.close()

    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)

    cm = _CommitOnlySession(factory)
    with (
        patch("sistema.app.services.email_sender.SessionLocal", return_value=cm),
        patch("sistema.app.services.email_sender.settings") as mock_settings,
        patch("smtplib.SMTP", return_value=mock_smtp),
    ):
        mock_settings.smtp_host = "smtp.test.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_use_tls = False
        mock_settings.smtp_use_starttls = False
        mock_settings.smtp_user = None
        mock_settings.smtp_from_name = "CheckCheck"
        mock_settings.smtp_from_email = "noreply@test.com"
        mock_settings.smtp_timeout_seconds = 30
        mock_settings.smtp_max_retries = 3
        deliver_pending_emails([log_id])

    check_db = factory()
    event = check_db.execute(
        sa.select(CheckEvent).where(CheckEvent.action == "accident_email")
    ).scalars().first()
    assert event is not None, "Expected check_event with action='accident_email'"
    assert event.source == "system"
    assert event.status == "done"
    assert "recipient_count=1" in (event.details or "")
    assert "sent_count=1" in (event.details or "")
    assert "failed_count=0" in (event.details or "")
    check_db.close()
