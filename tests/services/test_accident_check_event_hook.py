"""Tests for Task C5 — accident check-in/check-out hook.

Covers fire_accident_hook_for_check_event and its integration into forms_submit.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import (
    Accident,
    AccidentUserReport,
    AdminUser,
    Project,
    User,
)
from sistema.app.services.accident_lifecycle import (
    fire_accident_hook_for_check_event,
    list_active_accident,
)


# ---------------------------------------------------------------------------
# Session helper
# ---------------------------------------------------------------------------

def _make_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    return factory()


_NOW = datetime(2026, 1, 1, 8, 0, 0)


def _make_project(db: Session) -> Project:
    proj = Project(
        name="PROJ",
        country_code="SG",
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address="1 St",
        zip_code="123456",
    )
    db.add(proj)
    db.flush()
    return proj


def _make_admin(db: Session) -> AdminUser:
    admin = AdminUser(
        chave="A001",
        nome_completo="Admin",
        created_at=_NOW,
        updated_at=_NOW,
    )
    db.add(admin)
    db.flush()
    return admin


def _make_user(db: Session, chave: str = "U001", *, checkin: bool = True) -> User:
    user = User(
        chave=chave,
        nome=f"User {chave}",
        projeto="PROJ",
        checkin=checkin,
        local="Sala 1",
        time=_NOW if checkin else None,
        last_active_at=_NOW,
        inactivity_days=0,
    )
    db.add(user)
    db.flush()
    return user


def _make_accident(db: Session, proj: Project, admin: AdminUser) -> Accident:
    a = Accident(
        accident_number=0,
        project_id=proj.id,
        project_name_snapshot=proj.name,
        location_name_snapshot="Sala",
        location_is_registered=False,
        origin="admin",
        opened_by_admin_id=admin.id,
        opened_at=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )
    db.add(a)
    db.commit()
    return a


# ---------------------------------------------------------------------------
# Unit tests for fire_accident_hook_for_check_event
# ---------------------------------------------------------------------------

def test_hook_skips_when_no_active_accident(tmp_path: Path):
    db = _make_session(tmp_path)
    user = _make_user(db)
    db.commit()

    # No accident exists — hook must be a no-op
    fire_accident_hook_for_check_event(db, user=user, action="checkin", event_time=_NOW)

    reports = db.execute(select(AccidentUserReport)).scalars().all()
    assert reports == []


def test_hook_creates_waiting_report_for_new_user_check_in(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin)
    user = _make_user(db, "U002", checkin=False)
    db.commit()

    fire_accident_hook_for_check_event(db, user=user, action="checkin", event_time=_NOW)

    report = db.execute(
        select(AccidentUserReport).where(
            AccidentUserReport.accident_id == accident.id,
            AccidentUserReport.user_id == user.id,
        )
    ).scalar_one()
    assert report.zone == "waiting"
    assert report.status == "waiting"
    assert report.last_checkin_action == "check-in"


def test_hook_updates_last_action_for_existing_user_check_out(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin)
    user = _make_user(db, "U003")
    db.commit()

    # First create a report via check-in
    fire_accident_hook_for_check_event(db, user=user, action="checkin", event_time=_NOW)

    # Now check-out — should update last_checkin_action but preserve zone/status
    checkout_time = datetime(2026, 1, 1, 9, 0, 0)
    fire_accident_hook_for_check_event(db, user=user, action="checkout", event_time=checkout_time)

    report = db.execute(
        select(AccidentUserReport).where(
            AccidentUserReport.accident_id == accident.id,
            AccidentUserReport.user_id == user.id,
        )
    ).scalar_one()
    assert report.last_checkin_action == "check-out"
    assert report.zone == "waiting"
    assert report.status == "waiting"


def test_hook_swallows_exceptions(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    _make_accident(db, proj, admin)
    user = _make_user(db)
    db.commit()

    with patch(
        "sistema.app.services.accident_lifecycle.update_accident_membership_for_check_event",
        side_effect=RuntimeError("boom"),
    ):
        # Must not raise
        fire_accident_hook_for_check_event(db, user=user, action="checkin", event_time=_NOW)


def test_hook_ignores_unknown_action(tmp_path: Path):
    db = _make_session(tmp_path)
    user = _make_user(db)
    db.commit()
    # Should silently return without touching DB
    fire_accident_hook_for_check_event(db, user=user, action="heartbeat", event_time=_NOW)
    assert db.execute(select(AccidentUserReport)).scalars().all() == []


def test_fire_accident_hook_rollback_after_query_failure(tmp_path: Path):
    """Reproduces the production regression where list_active_accident raised
    `psycopg.errors.UndefinedTable` because the accidents table was missing.

    Postgres aborts the surrounding transaction on such failures, leaving the
    session in `InFailedSqlTransaction` for any subsequent query. The hook must
    swallow the exception AND call db.rollback() so the response builder that
    runs immediately after (build_mobile_sync_state) can still query the
    session successfully.
    """
    db = _make_session(tmp_path)
    user = _make_user(db)
    db.commit()

    with patch(
        "sistema.app.services.accident_lifecycle.list_active_accident",
        side_effect=RuntimeError("forced failure"),
    ):
        # Must not raise
        fire_accident_hook_for_check_event(db, user=user, action="checkin", event_time=_NOW)

    # The session must still be usable for follow-up queries (this is what
    # build_mobile_sync_state would do right after the hook in production).
    fetched = db.execute(select(User).where(User.id == user.id)).scalar_one()
    assert fetched.chave == user.chave


# ---------------------------------------------------------------------------
# Integration test — /api/web/check POST calls the hook
# ---------------------------------------------------------------------------

# App bootstrap must happen before importing app module
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


def test_web_check_post_calls_hook():
    """Integration test: POST /api/web/check calls fire_accident_hook_for_check_event."""
    from fastapi.testclient import TestClient
    from sistema.app.database import Base as AppBase, SessionLocal, engine as app_engine
    from sistema.app.main import app
    from sistema.app.models import User as AppUser, Project as AppProject, UserProjectMembership
    from sistema.app.services.passwords import hash_password

    AppBase.metadata.create_all(bind=app_engine)

    test_chave = "HKTT"
    test_senha = "Senha123"
    test_projeto = "PROJHKT"
    test_event_id = str(uuid.uuid4())

    with SessionLocal() as db:
        # Ensure project exists
        proj = db.execute(
            sa.select(AppProject).where(AppProject.name == test_projeto)
        ).scalar_one_or_none()
        if proj is None:
            proj = AppProject(
                name=test_projeto,
                country_code="SG",
                country_name="Singapore",
                timezone_name="Asia/Singapore",
                address="1 Addr",
                zip_code="123456",
            )
            db.add(proj)
            db.flush()

        # Ensure user exists and has senha
        user = db.execute(
            sa.select(AppUser).where(AppUser.chave == test_chave)
        ).scalar_one_or_none()
        if user is None:
            user = AppUser(
                chave=test_chave,
                nome="Hook Test User",
                projeto=test_projeto,
                checkin=False,
                local="Sala 1",
                last_active_at=datetime.now(timezone.utc),
                inactivity_days=0,
                senha=hash_password(test_senha),
            )
            db.add(user)
            db.flush()
        else:
            user.senha = hash_password(test_senha)
            user.projeto = test_projeto
            db.flush()

        # Ensure user has membership for this project (clear others, add this one)
        db.execute(
            sa.delete(UserProjectMembership).where(UserProjectMembership.user_id == user.id)
        )
        now = datetime.now(timezone.utc)
        membership = UserProjectMembership(user_id=user.id, project_id=proj.id, created_at=now, updated_at=now)
        db.add(membership)
        db.commit()

    client = TestClient(app, raise_server_exceptions=False)

    # Login to get session cookie
    login_resp = client.post(
        "/api/web/auth/login",
        json={"chave": test_chave, "senha": test_senha},
    )
    assert login_resp.status_code == 200

    payload = {
        "chave": test_chave,
        "projeto": test_projeto,
        "action": "checkin",
        "local": "Sala 1",
        "informe": "normal",
        "event_time": datetime.now(timezone.utc).isoformat(),
        "client_event_id": test_event_id,
    }

    with patch(
        "sistema.app.services.forms_submit.fire_accident_hook_for_check_event"
    ) as mock_hook:
        resp = client.post("/api/web/check", json=payload)

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    mock_hook.assert_called_once()
    call_kwargs = mock_hook.call_args.kwargs
    assert call_kwargs["action"] == "checkin"
