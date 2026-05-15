"""Tests for Task D1 — GET /api/admin/accidents/active endpoint."""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
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
from sistema.app.models import Accident, AdminUser, Project, User  # noqa: E402
from sistema.app.services.passwords import hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)

ACTIVE_URL = "/api/admin/accidents/active"
ADMIN_LOGIN_URL = "/api/admin/auth/login"

# Admin credentials used in tests
_ADMIN_CHAVE = "D1AT"
_ADMIN_SENHA = "AdminD1Test!"


def _ensure_admin_user(db: Session) -> User:
    """Create (or reuse) a User record with admin panel access."""
    user = db.execute(
        sa.select(User).where(User.chave == _ADMIN_CHAVE)
    ).scalar_one_or_none()
    if user is None:
        user = User(
            chave=_ADMIN_CHAVE,
            nome="D1 Admin Test",
            projeto="D1PROJ",
            checkin=False,
            local="Sala 1",
            last_active_at=datetime.now(tz=timezone.utc),
            inactivity_days=0,
            senha=hash_password(_ADMIN_SENHA),
            # perfil=19 → digits {"1","9"} → user_has_admin_access=True
            perfil=19,
        )
        db.add(user)
    else:
        user.senha = hash_password(_ADMIN_SENHA)
        user.perfil = 19
    db.commit()
    db.refresh(user)
    return user


def _ensure_project(db: Session, name: str = "D1PROJ") -> Project:
    proj = db.execute(
        sa.select(Project).where(Project.name == name)
    ).scalar_one_or_none()
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


def _close_all_accidents(db: Session) -> None:
    """Close any open accident so tests start clean."""
    now = datetime.now(tz=timezone.utc)
    db.execute(
        sa.update(Accident)
        .where(Accident.closed_at.is_(None))
        .values(closed_at=now, updated_at=now)
    )
    db.commit()


def _open_accident(db: Session, proj: Project, admin_user: User) -> Accident:
    now = datetime.now(tz=timezone.utc)
    # We need an AdminUser row; use admin_users table
    admin_row = db.execute(
        sa.select(AdminUser).where(AdminUser.chave == admin_user.chave)
    ).scalar_one_or_none()
    if admin_row is None:
        admin_row = AdminUser(
            chave=admin_user.chave,
            nome_completo=admin_user.nome,
            created_at=now,
            updated_at=now,
        )
        db.add(admin_row)
        db.flush()

    # Determine next accident_number
    max_row = db.execute(
        sa.text("SELECT COALESCE(MAX(accident_number), -1) + 1 FROM accidents")
    ).scalar_one()
    accident = Accident(
        accident_number=int(max_row),
        project_id=proj.id,
        project_name_snapshot=proj.name,
        location_name_snapshot="Test Location",
        location_is_registered=False,
        origin="admin",
        opened_by_admin_id=admin_row.id,
        opened_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(accident)
    db.commit()
    db.refresh(accident)
    return accident


def _logged_in_client() -> tuple[TestClient, None]:
    """Return a TestClient that is already logged in as admin."""
    with SessionLocal() as db:
        _ensure_project(db)
        _ensure_admin_user(db)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        ADMIN_LOGIN_URL,
        json={"chave": _ADMIN_CHAVE, "senha": _ADMIN_SENHA},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.status_code} {resp.text}"
    return client


# ---------------------------------------------------------------------------
# test_active_requires_session
# ---------------------------------------------------------------------------


def test_active_requires_session():
    """Without an admin session the endpoint must return 401."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(ACTIVE_URL)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# test_active_returns_empty_when_none
# ---------------------------------------------------------------------------


def test_active_returns_empty_when_none():
    """No active accident → is_active=False, accident=null, situation_rows=[]."""
    with SessionLocal() as db:
        _close_all_accidents(db)

    client = _logged_in_client()
    resp = client.get(ACTIVE_URL)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is False
    assert data["accident"] is None
    assert data["situation_rows"] == []


# ---------------------------------------------------------------------------
# test_active_returns_accident_and_rows
# ---------------------------------------------------------------------------


def test_active_returns_accident_and_rows():
    """Active accident → is_active=True, accident populated, situation_rows list."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        proj_name = proj.name
        proj_id = proj.id
        admin_user = _ensure_admin_user(db)
        accident = _open_accident(db, proj, admin_user)
        accident_id = accident.id
        accident_number = accident.accident_number

    client = _logged_in_client()
    resp = client.get(ACTIVE_URL)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is True

    acc = data["accident"]
    assert acc is not None
    assert acc["id"] == accident_id
    assert acc["accident_number"] == accident_number
    assert len(acc["accident_number_label"]) == 4  # zero-padded 4 digits
    assert acc["project_name"] == proj_name
    assert acc["location_name"] == "Test Location"
    assert acc["location_is_registered"] is False
    assert acc["origin"] == "admin"
    assert acc["opened_by_label"] != ""
    assert acc["closed_at"] is None

    # situation_rows is a list (may be empty if no reports yet)
    assert isinstance(data["situation_rows"], list)

    # Clean up
    with SessionLocal() as db:
        _close_all_accidents(db)
