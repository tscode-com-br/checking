"""Shared pytest fixtures for Accident Mode tests.

Registered automatically via ``pytest_plugins`` in ``tests/conftest.py``.
Available to every test_*.py in the project.

Fixture summary
---------------
accident_project        — Project "P-Test" in the shared test DB.
accident_location       — ManagedLocation "L-Test" linked to "P-Test".
user_in_project         — User(perfil=0, checkin=True) in "P-Test" with email.
admin_perfil_1          — AdminSession(user, client) for a full-admin (perfil=1).
admin_perfil_9          — AdminSession(user, client) for a super-admin (perfil=9).
open_accident_fixture   — Yields an open Accident; closes it on teardown.
mock_smtp               — Patches smtplib.SMTP/SMTP_SSL; collects sent messages.
mock_storage            — Patches object_storage.upload_stream to a no-op.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Generator, NamedTuple
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from sistema.app.database import Base, SessionLocal, engine
from sistema.app.main import app
from sistema.app.models import (
    Accident,
    AccidentArchive,
    AccidentUserReport,
    AccidentVideoUpload,
    AdminUser,
    ManagedLocation,
    Project,
    User,
)
from sistema.app.services.accident_lifecycle import (
    close_accident,
    list_active_accident,
    open_accident,
)
from sistema.app.services.passwords import hash_password

# Ensure schema is in place when this module is loaded.
Base.metadata.create_all(bind=engine)

ADMIN_LOGIN_URL = "/api/admin/auth/login"

# ---------------------------------------------------------------------------
# Shared data types
# ---------------------------------------------------------------------------


class AdminSession(NamedTuple):
    """Holds a User record and an authenticated TestClient for admin routes."""

    user: User
    client: TestClient


# ---------------------------------------------------------------------------
# accident_project
# ---------------------------------------------------------------------------


@pytest.fixture
def accident_project() -> Generator[Project, None, None]:
    """Creates (or reuses) the Project 'P-Test' in the shared test DB."""
    with SessionLocal() as db:
        proj = db.execute(
            sa.select(Project).where(Project.name == "P-Test")
        ).scalar_one_or_none()
        if proj is None:
            proj = Project(
                name="P-Test",
                country_code="SG",
                country_name="Singapore",
                timezone_name="Asia/Singapore",
                address="1 Test Street",
                zip_code="000001",
            )
            db.add(proj)
            db.commit()
            db.refresh(proj)
    yield proj


# ---------------------------------------------------------------------------
# accident_location
# ---------------------------------------------------------------------------


@pytest.fixture
def accident_location(accident_project: Project) -> Generator[ManagedLocation, None, None]:
    """Creates (or reuses) ManagedLocation 'L-Test' linked to 'P-Test'."""
    with SessionLocal() as db:
        loc = db.execute(
            sa.select(ManagedLocation).where(ManagedLocation.local == "L-Test")
        ).scalar_one_or_none()
        if loc is None:
            now = datetime.now(timezone.utc)
            loc = ManagedLocation(
                local="L-Test",
                latitude=1.3521,
                longitude=103.8198,
                projects_json=json.dumps(["P-Test"]),
                tolerance_meters=50,
                created_at=now,
                updated_at=now,
            )
            db.add(loc)
            db.commit()
            db.refresh(loc)
    yield loc


# ---------------------------------------------------------------------------
# user_in_project
# ---------------------------------------------------------------------------

_USER_CHAVE = "LTST"
_USER_SENHA = "L1TestUser!"


@pytest.fixture
def user_in_project(accident_project: Project) -> Generator[User, None, None]:
    """Creates (or reuses) User(chave='LTST', perfil=0, checkin=True) in 'P-Test'."""
    with SessionLocal() as db:
        user = db.execute(
            sa.select(User).where(User.chave == _USER_CHAVE)
        ).scalar_one_or_none()
        if user is None:
            user = User(
                chave=_USER_CHAVE,
                nome="L1 Test User",
                projeto="P-Test",
                checkin=True,
                local="Site L1",
                email="l1user@test.example.com",
                last_active_at=datetime.now(timezone.utc),
                inactivity_days=0,
                perfil=0,
                senha=hash_password(_USER_SENHA),
            )
            db.add(user)
        else:
            user.checkin = True
            user.email = "l1user@test.example.com"
            user.perfil = 0
            user.senha = hash_password(_USER_SENHA)
        db.commit()
        db.refresh(user)
    yield user


# ---------------------------------------------------------------------------
# admin_perfil_1
# ---------------------------------------------------------------------------

_ADMIN1_CHAVE = "LA01"
_ADMIN1_SENHA = "L1Admin1!"


@pytest.fixture
def admin_perfil_1() -> Generator[AdminSession, None, None]:
    """User with perfil=1 (full admin, digit '1').  Returns AdminSession(user, client)."""
    with SessionLocal() as db:
        user = db.execute(
            sa.select(User).where(User.chave == _ADMIN1_CHAVE)
        ).scalar_one_or_none()
        if user is None:
            user = User(
                chave=_ADMIN1_CHAVE,
                nome="L1 Admin P1",
                projeto="P-Test",
                checkin=False,
                local=None,
                last_active_at=datetime.now(timezone.utc),
                inactivity_days=0,
                perfil=1,
                senha=hash_password(_ADMIN1_SENHA),
            )
            db.add(user)
        else:
            user.perfil = 1
            user.senha = hash_password(_ADMIN1_SENHA)
        db.commit()
        db.refresh(user)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(ADMIN_LOGIN_URL, json={"chave": _ADMIN1_CHAVE, "senha": _ADMIN1_SENHA})
    assert resp.status_code == 200, (
        f"admin_perfil_1 login failed: {resp.status_code} {resp.text}"
    )
    yield AdminSession(user=user, client=client)


# ---------------------------------------------------------------------------
# admin_perfil_9
# ---------------------------------------------------------------------------

_ADMIN9_CHAVE = "LA09"
_ADMIN9_SENHA = "L1Admin9!"


@pytest.fixture
def admin_perfil_9() -> Generator[AdminSession, None, None]:
    """User with perfil=9 (super-admin, FULL_ACCESS_DIGIT).  Returns AdminSession(user, client)."""
    with SessionLocal() as db:
        user = db.execute(
            sa.select(User).where(User.chave == _ADMIN9_CHAVE)
        ).scalar_one_or_none()
        if user is None:
            user = User(
                chave=_ADMIN9_CHAVE,
                nome="L1 Admin P9",
                projeto="P-Test",
                checkin=False,
                local=None,
                last_active_at=datetime.now(timezone.utc),
                inactivity_days=0,
                perfil=9,
                senha=hash_password(_ADMIN9_SENHA),
            )
            db.add(user)
        else:
            user.perfil = 9
            user.senha = hash_password(_ADMIN9_SENHA)
        db.commit()
        db.refresh(user)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(ADMIN_LOGIN_URL, json={"chave": _ADMIN9_CHAVE, "senha": _ADMIN9_SENHA})
    assert resp.status_code == 200, (
        f"admin_perfil_9 login failed: {resp.status_code} {resp.text}"
    )
    yield AdminSession(user=user, client=client)


# ---------------------------------------------------------------------------
# open_accident_fixture
# ---------------------------------------------------------------------------


def _wipe_accident_rows(db: sa.orm.Session) -> None:
    """Close any open accident and delete all child rows for a clean slate."""
    now = datetime.now(timezone.utc)
    db.execute(
        sa.update(Accident)
        .where(Accident.closed_at.is_(None))
        .values(closed_at=now, updated_at=now)
    )
    db.execute(sa.delete(AccidentArchive))
    db.execute(sa.delete(AccidentVideoUpload))
    db.execute(sa.delete(AccidentUserReport))
    db.commit()


def _ensure_admin_row(db: sa.orm.Session, user: User) -> AdminUser:
    """Return (or create) an AdminUser row matching the given User."""
    admin_row = db.execute(
        sa.select(AdminUser).where(AdminUser.chave == user.chave)
    ).scalar_one_or_none()
    if admin_row is None:
        now = datetime.now(timezone.utc)
        admin_row = AdminUser(
            chave=user.chave,
            nome_completo=user.nome,
            created_at=now,
            updated_at=now,
        )
        db.add(admin_row)
        db.flush()
    return admin_row


@pytest.fixture
def open_accident_fixture(
    accident_project: Project,
    admin_perfil_1: AdminSession,
) -> Generator[Accident, None, None]:
    """Opens an Accident via accident_lifecycle.open_accident; closes it in teardown.

    Uses admin_perfil_1 as the opener and patches both SSE notify calls so
    tests do not require a running Postgres instance.
    """
    with SessionLocal() as db:
        _wipe_accident_rows(db)

    _broker_patches = (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    )

    with _broker_patches[0], _broker_patches[1]:
        with SessionLocal() as db:
            proj = db.get(Project, accident_project.id)
            admin_row = _ensure_admin_row(db, admin_perfil_1.user)
            accident = open_accident(
                db,
                origin="admin",
                project_id=proj.id,
                custom_location_name="Fixture Zone",
                opened_by_admin_id=admin_row.id,
            )
            db.commit()
            db.refresh(accident)
            accident_id = accident.id

    yield accident

    # Teardown — close only if still open to avoid NoActiveAccidentError.
    with _broker_patches[0], _broker_patches[1]:
        with SessionLocal() as db:
            active = list_active_accident(db)
            if active is not None and active.id == accident_id:
                admin_row = _ensure_admin_row(db, admin_perfil_1.user)
                close_accident(db, accident=active, closed_by_admin_id=admin_row.id)
                db.commit()


# ---------------------------------------------------------------------------
# mock_smtp
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_smtp():
    """Patches smtplib.SMTP and smtplib.SMTP_SSL.

    The returned MagicMock accumulates sent ``email.message.Message`` objects
    in ``mock_smtp.sent_messages``.

    Example::

        def test_email_sent(mock_smtp):
            trigger_help_email(...)
            assert len(mock_smtp.sent_messages) == 1
    """
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.sent_messages: list = []

    def _capture(msg, *args, **kwargs):
        mock.sent_messages.append(msg)

    mock.send_message.side_effect = _capture

    with (
        patch("smtplib.SMTP", return_value=mock),
        patch("smtplib.SMTP_SSL", return_value=mock),
    ):
        yield mock


# ---------------------------------------------------------------------------
# mock_storage
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_storage():
    """Patches sistema.app.services.object_storage.upload_stream.

    Returns a no-op that yields a deterministic fake URL:
    ``https://fake-storage.example.com/{object_key}``

    The patch object is yielded so callers can inspect call args if needed::

        def test_video_upload(mock_storage):
            upload_video(...)
            assert mock_storage.call_count == 1
    """

    def _fake_upload(
        *,
        object_key: str,
        stream,
        content_type: str,
        cache_control: str = "private, max-age=0",
    ) -> str:
        return f"https://fake-storage.example.com/{object_key}"

    with patch(
        "sistema.app.services.object_storage.upload_stream",
        side_effect=_fake_upload,
    ) as mock_patch:
        yield mock_patch
