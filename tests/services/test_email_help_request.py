"""Tests for Task G3 — email_sender service (queue + delivery)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from sistema.app.database import Base
from sistema.app.models import (
    Accident,
    AdminUser,
    EmailDeliveryLog,
    Project,
    User,
    UserProjectMembership,
)
from sistema.app.services.email_sender import _send_via_smtp, deliver_pending_emails, queue_help_request_emails

_NOW = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# Test DB helpers
# ---------------------------------------------------------------------------


def _make_factory(tmp_path: Path):
    engine = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


class _CommitOnlySession:
    """Context manager that commits on __exit__ but does NOT close the session.

    Used to inject a session into services that call `with SessionLocal() as db:`.
    Without this, Session.__exit__ would call close() and detach all objects.
    """

    def __init__(self, factory):
        self._db = factory()

    def __enter__(self):
        return self._db

    def __exit__(self, *args):
        self._db.commit()


def _make_project(db, name: str = "EMAILPROJ") -> Project:
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


def _make_admin(db) -> AdminUser:
    a = AdminUser(chave="EA01", nome_completo="Email Admin", created_at=_NOW, updated_at=_NOW)
    db.add(a)
    db.flush()
    return a


def _make_user(db, chave: str, *, email: str | None = "test@example.com") -> User:
    u = User(
        chave=chave,
        nome=f"User {chave}",
        email=email,
        projeto="EMAILPROJ",
        checkin=True,
        local="Sala A",
        last_active_at=_NOW,
        inactivity_days=0,
    )
    db.add(u)
    db.flush()
    return u


def _make_accident(db, proj: Project, admin: AdminUser) -> Accident:
    a = Accident(
        accident_number=0,
        project_id=proj.id,
        project_name_snapshot=proj.name,
        location_name_snapshot="Gate B",
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


def _make_membership(db, user: User, project: Project) -> UserProjectMembership:
    m = UserProjectMembership(user_id=user.id, project_id=project.id, created_at=_NOW, updated_at=_NOW)
    db.add(m)
    db.flush()
    return m


def _make_queued_log(db, accident: Accident, user: User) -> EmailDeliveryLog:
    log = EmailDeliveryLog(
        accident_id=accident.id,
        triggered_by_user_id=user.id,
        recipient_email="dest@example.com",
        recipient_chave=user.chave,
        subject="(CHECKING) PEDIDO DE SOCORRO",
        body_snapshot="Body text",
        delivery_status="queued",
        queued_at=_NOW,
    )
    db.add(log)
    db.flush()
    return log


# ---------------------------------------------------------------------------
# test_queue_creates_log_per_recipient
# ---------------------------------------------------------------------------


def test_queue_creates_log_per_recipient(tmp_path: Path):
    """queue_help_request_emails creates one queued log per recipient with email."""
    factory = _make_factory(tmp_path)

    setup_db = factory()
    proj = _make_project(setup_db)
    admin = _make_admin(setup_db)
    accident = _make_accident(setup_db, proj, admin)
    accident_id = accident.id

    # Two users with email
    u1 = _make_user(setup_db, "R001", email="r1@example.com")
    u2 = _make_user(setup_db, "R002", email="r2@example.com")
    requester = _make_user(setup_db, "REQ1", email="req@example.com")
    requester_id = requester.id
    _make_membership(setup_db, u1, proj)
    _make_membership(setup_db, u2, proj)
    _make_membership(setup_db, requester, proj)
    setup_db.commit()
    setup_db.close()

    cm1 = _CommitOnlySession(factory)
    with (
        patch("sistema.app.services.email_sender.SessionLocal", return_value=cm1),
        patch("sistema.app.services.email_sender.settings") as mock_settings,
    ):
        mock_settings.smtp_host = None  # delivery disabled
        queue_help_request_emails(accident_id=accident_id, requester_user_id=requester_id)

    check_db = factory()
    logs = check_db.query(EmailDeliveryLog).filter_by(accident_id=accident_id).all()
    queued = [l for l in logs if l.delivery_status == "queued"]
    # All 3 members have email — 3 queued logs
    assert len(queued) == 3
    emails = {l.recipient_email for l in queued}
    assert "r1@example.com" in emails
    assert "r2@example.com" in emails
    check_db.close()


# ---------------------------------------------------------------------------
# test_queue_logs_missing_email_as_failed
# ---------------------------------------------------------------------------


def test_queue_logs_missing_email_as_failed(tmp_path: Path):
    """Recipients with no email get a log with delivery_status='failed'."""
    factory = _make_factory(tmp_path)

    setup_db = factory()
    proj = _make_project(setup_db)
    admin = _make_admin(setup_db)
    accident = _make_accident(setup_db, proj, admin)
    accident_id = accident.id

    no_email_user = _make_user(setup_db, "NE01", email=None)
    requester = _make_user(setup_db, "REQ2", email="req@example.com")
    requester_id = requester.id
    _make_membership(setup_db, no_email_user, proj)
    _make_membership(setup_db, requester, proj)
    setup_db.commit()
    setup_db.close()

    cm1 = _CommitOnlySession(factory)
    with (
        patch("sistema.app.services.email_sender.SessionLocal", return_value=cm1),
        patch("sistema.app.services.email_sender.settings") as mock_settings,
    ):
        mock_settings.smtp_host = None
        queue_help_request_emails(accident_id=accident_id, requester_user_id=requester_id)

    check_db = factory()
    failed_logs = (
        check_db.query(EmailDeliveryLog)
        .filter_by(accident_id=accident_id, delivery_status="failed")
        .all()
    )
    assert any(l.error_message == "Missing recipient email" for l in failed_logs)
    check_db.close()


# ---------------------------------------------------------------------------
# test_queue_idempotent_by_status_transition
# ---------------------------------------------------------------------------


def test_queue_idempotent_by_status_transition(tmp_path: Path):
    """Each call creates new log rows; upstream guarantees the call only happens once
    per status transition (non-help → help).  Here we verify the function completes
    cleanly on a second call without raising errors."""
    factory = _make_factory(tmp_path)

    setup_db = factory()
    proj = _make_project(setup_db)
    admin = _make_admin(setup_db)
    accident = _make_accident(setup_db, proj, admin)
    accident_id = accident.id
    requester = _make_user(setup_db, "REQ3", email="req3@example.com")
    requester_id = requester.id
    _make_membership(setup_db, requester, proj)
    setup_db.commit()
    setup_db.close()

    for _ in range(2):
        cm = _CommitOnlySession(factory)
        with (
            patch("sistema.app.services.email_sender.SessionLocal", return_value=cm),
            patch("sistema.app.services.email_sender.settings") as mock_settings,
        ):
            mock_settings.smtp_host = None
            queue_help_request_emails(accident_id=accident_id, requester_user_id=requester_id)

    check_db = factory()
    count = check_db.query(EmailDeliveryLog).filter_by(accident_id=accident_id).count()
    assert count == 2  # two calls → two rows
    check_db.close()


# ---------------------------------------------------------------------------
# test_send_smtp_disabled_keeps_queued
# ---------------------------------------------------------------------------


def test_send_smtp_disabled_keeps_queued(tmp_path: Path):
    """deliver_pending_emails is a no-op when smtp_host is None."""
    factory = _make_factory(tmp_path)
    setup_db = factory()
    proj = _make_project(setup_db)
    admin = _make_admin(setup_db)
    accident = _make_accident(setup_db, proj, admin)
    user = _make_user(setup_db, "SD01")
    log = _make_queued_log(setup_db, accident, user)
    log_id = log.id
    setup_db.commit()
    setup_db.close()

    with patch("sistema.app.services.email_sender.settings") as mock_settings:
        mock_settings.smtp_host = None
        deliver_pending_emails([log_id])

    check_db = factory()
    row = check_db.get(EmailDeliveryLog, log_id)
    assert row.delivery_status == "queued"
    check_db.close()


# ---------------------------------------------------------------------------
# test_send_smtp_success_marks_sent
# ---------------------------------------------------------------------------


def test_send_smtp_success_marks_sent(tmp_path: Path):
    """Successful SMTP delivery marks log as 'sent'."""
    factory = _make_factory(tmp_path)
    setup_db = factory()
    proj = _make_project(setup_db)
    admin = _make_admin(setup_db)
    accident = _make_accident(setup_db, proj, admin)
    user = _make_user(setup_db, "SS01")
    log = _make_queued_log(setup_db, accident, user)
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
    row = check_db.get(EmailDeliveryLog, log_id)
    assert row.delivery_status == "sent"
    assert row.sent_at is not None
    check_db.close()


# ---------------------------------------------------------------------------
# test_send_smtp_failure_retries_and_fails
# ---------------------------------------------------------------------------


def test_send_smtp_failure_retries_and_fails(tmp_path: Path):
    """SMTP errors trigger retries up to smtp_max_retries, then mark log 'failed'."""
    factory = _make_factory(tmp_path)
    setup_db = factory()
    proj = _make_project(setup_db)
    admin = _make_admin(setup_db)
    accident = _make_accident(setup_db, proj, admin)
    user = _make_user(setup_db, "SF01")
    log = _make_queued_log(setup_db, accident, user)
    log_id = log.id
    setup_db.commit()
    setup_db.close()

    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_smtp.send_message.side_effect = OSError("connection refused")

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
    row = check_db.get(EmailDeliveryLog, log_id)
    assert row.delivery_status == "failed"
    assert row.retry_count == 3
    assert "connection refused" in row.error_message
    check_db.close()


# ---------------------------------------------------------------------------
# test_send_uses_ssl_when_configured
# ---------------------------------------------------------------------------


def test_send_uses_ssl_when_configured(tmp_path: Path):
    """smtp_use_tls=True causes SMTP_SSL to be used instead of plain SMTP."""
    factory = _make_factory(tmp_path)
    setup_db = factory()
    proj = _make_project(setup_db)
    admin = _make_admin(setup_db)
    accident = _make_accident(setup_db, proj, admin)
    user = _make_user(setup_db, "SU01")
    log = _make_queued_log(setup_db, accident, user)
    log_id = log.id
    setup_db.commit()
    setup_db.close()

    mock_smtp_ssl = MagicMock()
    mock_smtp_ssl.__enter__ = MagicMock(return_value=mock_smtp_ssl)
    mock_smtp_ssl.__exit__ = MagicMock(return_value=False)

    cm = _CommitOnlySession(factory)
    with (
        patch("sistema.app.services.email_sender.SessionLocal", return_value=cm),
        patch("sistema.app.services.email_sender.settings") as mock_settings,
        patch("smtplib.SMTP_SSL", return_value=mock_smtp_ssl) as patched_ssl,
        patch("smtplib.SMTP") as patched_plain,
    ):
        mock_settings.smtp_host = "smtp.test.com"
        mock_settings.smtp_port = 465
        mock_settings.smtp_use_tls = True
        mock_settings.smtp_user = None
        mock_settings.smtp_from_name = "CheckCheck"
        mock_settings.smtp_from_email = "noreply@test.com"
        mock_settings.smtp_timeout_seconds = 30
        mock_settings.smtp_max_retries = 3
        deliver_pending_emails([log_id])

    patched_ssl.assert_called_once()
    patched_plain.assert_not_called()


# ---------------------------------------------------------------------------
# test_send_uses_starttls_when_configured
# ---------------------------------------------------------------------------


def test_send_uses_starttls_when_configured(tmp_path: Path):
    """smtp_use_starttls=True causes server.starttls() to be called."""
    factory = _make_factory(tmp_path)
    setup_db = factory()
    proj = _make_project(setup_db)
    admin = _make_admin(setup_db)
    accident = _make_accident(setup_db, proj, admin)
    user = _make_user(setup_db, "STL1")
    log = _make_queued_log(setup_db, accident, user)
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
        patch("smtplib.SMTP_SSL") as patched_ssl,
    ):
        mock_settings.smtp_host = "smtp.test.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_use_tls = False
        mock_settings.smtp_use_starttls = True
        mock_settings.smtp_user = None
        mock_settings.smtp_from_name = "CheckCheck"
        mock_settings.smtp_from_email = "noreply@test.com"
        mock_settings.smtp_timeout_seconds = 30
        mock_settings.smtp_max_retries = 3
        deliver_pending_emails([log_id])

    mock_smtp.starttls.assert_called_once()
    patched_ssl.assert_not_called()
