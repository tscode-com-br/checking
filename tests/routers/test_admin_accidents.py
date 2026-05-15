"""Tests for Task D1/D2 — GET /api/admin/accidents/active and POST /api/admin/accidents/open."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import patch

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
from sistema.app.models import Accident, AccidentArchive, AccidentUserReport, AccidentVideoUpload, AdminUser, ManagedLocation, Project, User  # noqa: E402
from sistema.app.services.passwords import hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)

ACTIVE_URL = "/api/admin/accidents/active"
OPEN_URL = "/api/admin/accidents/open"
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
    """Close any open accident and wipe all child rows so each test starts clean.

    AccidentUserReport rows created by open_accident() would otherwise accumulate
    across runs and trigger UNIQUE(accident_id, user_id) errors on the next run
    when the same accident id gets reused by SQLite.
    """
    now = datetime.now(tz=timezone.utc)
    db.execute(
        sa.update(Accident)
        .where(Accident.closed_at.is_(None))
        .values(closed_at=now, updated_at=now)
    )
    db.execute(sa.delete(AccidentArchive))
    db.execute(sa.delete(AccidentVideoUpload))
    db.execute(sa.delete(AccidentUserReport))
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


# ---------------------------------------------------------------------------
# D2 helpers
# ---------------------------------------------------------------------------

# Credentials for a "limited" admin (panel access only, no full admin)
_LIMITED_CHAVE = "D2LM"
_LIMITED_SENHA = "LimitedD2Test!"


def _ensure_limited_admin_user(db: Session) -> User:
    """Create (or reuse) a User with perfil=0 — admin panel only, no full admin."""
    user = db.execute(
        sa.select(User).where(User.chave == _LIMITED_CHAVE)
    ).scalar_one_or_none()
    if user is None:
        user = User(
            chave=_LIMITED_CHAVE,
            nome="D2 Limited Admin",
            projeto="D1PROJ",
            checkin=False,
            local="Sala 1",
            last_active_at=datetime.now(tz=timezone.utc),
            inactivity_days=0,
            senha=hash_password(_LIMITED_SENHA),
            # perfil=0 → user_can_access_admin_panel=True but user_has_admin_access=False
            perfil=0,
        )
        db.add(user)
    else:
        user.senha = hash_password(_LIMITED_SENHA)
        user.perfil = 0
    db.commit()
    db.refresh(user)
    return user


def _logged_in_limited_client() -> TestClient:
    """Return a TestClient logged in as a limited admin (perfil=0, no full-admin access)."""
    with SessionLocal() as db:
        _ensure_project(db)
        _ensure_limited_admin_user(db)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        ADMIN_LOGIN_URL,
        json={"chave": _LIMITED_CHAVE, "senha": _LIMITED_SENHA},
    )
    assert resp.status_code == 200, f"Limited admin login failed: {resp.status_code} {resp.text}"
    return client


# ---------------------------------------------------------------------------
# test_open_requires_full_admin
# ---------------------------------------------------------------------------


def test_open_requires_full_admin():
    """User with panel-only access (perfil=0) must receive 403 on POST /accidents/open."""
    with SessionLocal() as db:
        _ensure_project(db)

    client = _logged_in_limited_client()
    resp = client.post(
        OPEN_URL,
        json={"project_id": 1, "custom_location_name": "Test Site"},
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# test_open_creates_when_none
# ---------------------------------------------------------------------------


def test_open_creates_when_none():
    """POST /accidents/open with no active accident → 200, is_active=True."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        proj_id = proj.id

    client = _logged_in_client()
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        resp = client.post(
            OPEN_URL,
            json={"project_id": proj_id, "custom_location_name": "Test Site"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is True
    assert data["accident"] is not None
    assert data["accident"]["origin"] == "admin"
    assert data["accident"]["location_name"] == "Test Site"
    assert isinstance(data["situation_rows"], list)

    # Clean up
    with SessionLocal() as db:
        _close_all_accidents(db)


# ---------------------------------------------------------------------------
# test_open_returns_conflict_when_active
# ---------------------------------------------------------------------------


def test_open_returns_conflict_when_active():
    """POST /accidents/open when an accident is already open → 409."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        admin_user = _ensure_admin_user(db)
        _open_accident(db, proj, admin_user)
        proj_id = proj.id

    client = _logged_in_client()
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        resp = client.post(
            OPEN_URL,
            json={"project_id": proj_id, "custom_location_name": "Another Site"},
        )

    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"

    # Clean up
    with SessionLocal() as db:
        _close_all_accidents(db)


# ---------------------------------------------------------------------------
# test_open_validates_payload
# ---------------------------------------------------------------------------


def test_open_validates_payload():
    """POST /accidents/open with invalid body → 422 (FastAPI schema validation)."""
    client = _logged_in_client()

    # Missing project_id entirely
    resp = client.post(OPEN_URL, json={})
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    # Both location_id and custom_location_name provided (XOR violation)
    with SessionLocal() as db:
        proj = _ensure_project(db)
        proj_id = proj.id

    resp = client.post(
        OPEN_URL,
        json={
            "project_id": proj_id,
            "location_id": 1,
            "custom_location_name": "Custom",
        },
    )
    assert resp.status_code == 422, f"Expected 422 for XOR violation, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# test_open_publishes_brokers
# ---------------------------------------------------------------------------


def test_open_publishes_brokers():
    """POST /accidents/open must publish 'accident_opened' to both SSE brokers."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        proj_id = proj.id

    client = _logged_in_client()
    with (
        patch(
            "sistema.app.services.accident_lifecycle.notify_admin_data_changed"
        ) as mock_admin,
        patch(
            "sistema.app.services.accident_lifecycle.notify_web_check_data_changed"
        ) as mock_web,
    ):
        resp = client.post(
            OPEN_URL,
            json={"project_id": proj_id, "custom_location_name": "Broker Test Site"},
        )

    assert resp.status_code == 200, resp.text

    # Both brokers must have been called with "accident_opened"
    mock_admin.assert_called_once()
    assert mock_admin.call_args[0][0] == "accident_opened"
    mock_web.assert_called_once()
    assert mock_web.call_args[0][0] == "accident_opened"

    # Clean up
    with SessionLocal() as db:
        _close_all_accidents(db)


CLOSE_URL = "/api/admin/accidents/close"


# ---------------------------------------------------------------------------
# test_close_requires_full_admin
# ---------------------------------------------------------------------------


def test_close_requires_full_admin():
    """User with panel-only access (perfil=0) must receive 403 on POST /accidents/close."""
    client = _logged_in_limited_client()
    resp = client.post(CLOSE_URL)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# test_close_conflict_when_none_active
# ---------------------------------------------------------------------------


def test_close_conflict_when_none_active():
    """POST /accidents/close with no active accident → 409."""
    with SessionLocal() as db:
        _close_all_accidents(db)

    client = _logged_in_client()
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        resp = client.post(CLOSE_URL)

    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# test_close_marks_closed_and_publishes
# ---------------------------------------------------------------------------


def test_close_marks_closed_and_publishes():
    """POST /accidents/close → 200, is_active=False, accident_closed published to both brokers."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        admin_user = _ensure_admin_user(db)
        _open_accident(db, proj, admin_user)

    client = _logged_in_client()
    with (
        patch(
            "sistema.app.services.accident_lifecycle.notify_admin_data_changed"
        ) as mock_admin,
        patch(
            "sistema.app.services.accident_lifecycle.notify_web_check_data_changed"
        ) as mock_web,
    ):
        resp = client.post(CLOSE_URL)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is False
    assert data["accident"] is None
    assert data["situation_rows"] == []

    # close_accident() must have published accident_closed to both brokers
    assert any(
        call[0][0] == "accident_closed" for call in mock_admin.call_args_list
    ), f"accident_closed not published to admin broker. Calls: {mock_admin.call_args_list}"
    assert any(
        call[0][0] == "accident_closed" for call in mock_web.call_args_list
    ), f"accident_closed not published to web broker. Calls: {mock_web.call_args_list}"


# ---------------------------------------------------------------------------
# test_close_schedules_archive_build
# ---------------------------------------------------------------------------


def test_close_schedules_archive_build():
    """POST /accidents/close must schedule build_and_attach_archive_for_accident as a BackgroundTask."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        admin_user = _ensure_admin_user(db)
        _open_accident(db, proj, admin_user)

    client = _logged_in_client()
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
        patch(
            "sistema.app.routers.admin.build_and_attach_archive_for_accident"
        ) as mock_archive,
    ):
        resp = client.post(CLOSE_URL)

    assert resp.status_code == 200, resp.text
    # BackgroundTasks runs synchronously in TestClient, so mock should have been called
    mock_archive.assert_called_once()
    called_accident_id = mock_archive.call_args[0][0]
    assert isinstance(called_accident_id, int), f"Expected int accident_id, got {called_accident_id!r}"


LIST_URL = "/api/admin/accidents"


def _make_archive_url(accident_id: int) -> str:
    return f"/api/admin/accidents/{accident_id}/archive"


def _insert_closed_accident(db: Session, proj: Project, admin_user: User, number_override: int | None = None) -> Accident:
    """Open then immediately close an accident for list tests."""
    now = datetime.now(tz=timezone.utc)
    if number_override is None:
        max_row = db.execute(
            sa.text("SELECT COALESCE(MAX(accident_number), -1) + 1 FROM accidents")
        ).scalar_one()
        accident_number = int(max_row)
    else:
        accident_number = number_override

    accident = Accident(
        accident_number=accident_number,
        project_id=proj.id,
        project_name_snapshot=proj.name,
        location_name_snapshot="Closed Location",
        location_is_registered=False,
        origin="admin",
        opened_by_admin_id=admin_user.id,
        opened_at=now,
        closed_by_admin_id=admin_user.id,
        closed_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(accident)
    db.commit()
    db.refresh(accident)
    return accident


def _insert_archive(db: Session, accident: Accident) -> None:
    """Insert a fake AccidentArchive row for the given accident (idempotent)."""
    # Remove existing archive to avoid unique constraint violation from prior runs
    existing = db.execute(
        sa.select(AccidentArchive).where(AccidentArchive.accident_id == accident.id)
    ).scalar_one_or_none()
    if existing:
        db.delete(existing)
        db.flush()
    now = datetime.now(tz=timezone.utc)
    archive = AccidentArchive(
        accident_id=accident.id,
        snapshot_json="{}",
        xlsx_object_key=f"archive/{accident.id}.xlsx",
        zip_object_key=f"archive/{accident.id}.zip",
        size_bytes=1024,
        generated_at=now,
    )
    db.add(archive)
    db.commit()


# ---------------------------------------------------------------------------
# test_list_returns_only_closed
# ---------------------------------------------------------------------------


def test_list_returns_only_closed():
    """GET /accidents must return only closed accidents (not the active one)."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        admin_user = _ensure_admin_user(db)
        closed = _insert_closed_accident(db, proj, admin_user)
        closed_id = closed.id
        # Open one active accident (should NOT appear in list)
        active = _open_accident(db, proj, admin_user)
        active_id = active.id

    client = _logged_in_client()
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
    ):
        resp = client.get(LIST_URL)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    ids = [row["id"] for row in data["rows"]]
    assert closed_id in ids, "Closed accident should be in list"
    assert active_id not in ids, "Active accident must NOT be in list"

    # Clean up
    with SessionLocal() as db:
        _close_all_accidents(db)


# ---------------------------------------------------------------------------
# test_list_ordered_desc
# ---------------------------------------------------------------------------


def test_list_ordered_desc():
    """GET /accidents must return closed accidents ordered by accident_number DESC."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        # Delete existing accidents to control numbering cleanly
        db.execute(sa.text("DELETE FROM accidents"))
        db.commit()
        proj = _ensure_project(db)
        admin_user = _ensure_admin_user(db)
        a1 = _insert_closed_accident(db, proj, admin_user, number_override=10)
        a2 = _insert_closed_accident(db, proj, admin_user, number_override=20)
        a3 = _insert_closed_accident(db, proj, admin_user, number_override=15)

    client = _logged_in_client()
    resp = client.get(LIST_URL)

    assert resp.status_code == 200, resp.text
    numbers = [row["accident_number_label"] for row in resp.json()["rows"]]
    # accident_number DESC → 20, 15, 10
    first_num = int(resp.json()["rows"][0]["accident_number_label"])
    last_num = int(resp.json()["rows"][-1]["accident_number_label"])
    assert first_num > last_num, f"Expected DESC order, got {numbers}"


# ---------------------------------------------------------------------------
# test_can_delete_true_only_for_perfil_9
# ---------------------------------------------------------------------------


def test_can_delete_true_only_for_perfil_9():
    """can_delete=True only when the logged-in admin has perfil==9."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        admin_user = _ensure_admin_user(db)  # perfil=19 (has digit 9)
        _insert_closed_accident(db, proj, admin_user)

    # perfil=19 includes digit 9, so can_delete must be True (19 == 9 is False, but spec checks perfil==9)
    # Create a perfil=9 user for the True branch
    with SessionLocal() as db:
        perfil9_user = db.execute(sa.select(User).where(User.chave == "D4P9")).scalar_one_or_none()
        if perfil9_user is None:
            from sistema.app.services.passwords import hash_password as _hp
            perfil9_user = User(
                chave="D4P9",
                nome="D4 Perfil9",
                projeto="D1PROJ",
                checkin=False,
                local="Sala",
                last_active_at=datetime.now(tz=timezone.utc),
                inactivity_days=0,
                senha=_hp("Perfil9D4!"),
                perfil=9,
            )
            db.add(perfil9_user)
        else:
            from sistema.app.services.passwords import hash_password as _hp
            perfil9_user.senha = _hp("Perfil9D4!")
            perfil9_user.perfil = 9
        db.commit()

    # Test perfil=9 admin → can_delete=True
    client_p9 = TestClient(app, raise_server_exceptions=False)
    resp_login = client_p9.post(ADMIN_LOGIN_URL, json={"chave": "D4P9", "senha": "Perfil9D4!"})
    assert resp_login.status_code == 200, f"perfil=9 login failed: {resp_login.text}"
    resp = client_p9.get(LIST_URL)
    assert resp.status_code == 200, resp.text
    rows = resp.json()["rows"]
    assert len(rows) > 0
    assert all(row["can_delete"] is True for row in rows), "perfil=9 must have can_delete=True"

    # Test perfil=19 admin (has digit "1" and "9" but perfil!=9) → can_delete=False
    client_p19 = _logged_in_client()
    resp = client_p19.get(LIST_URL)
    assert resp.status_code == 200, resp.text
    rows = resp.json()["rows"]
    assert len(rows) > 0
    assert all(row["can_delete"] is False for row in rows), "perfil=19 must have can_delete=False (perfil!=9)"


# ---------------------------------------------------------------------------
# test_download_returns_307_when_ready
# ---------------------------------------------------------------------------


def test_download_returns_307_when_ready():
    """GET /accidents/{id}/archive returns 307 redirect when archive exists."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        admin_user = _ensure_admin_user(db)
        accident = _insert_closed_accident(db, proj, admin_user)
        _insert_archive(db, accident)
        accident_id = accident.id

    client = _logged_in_client()
    fake_url = "https://storage.example.com/archive.zip?sig=abc"
    with patch("sistema.app.routers.admin.generate_presigned_url", return_value=fake_url):
        resp = client.get(_make_archive_url(accident_id), follow_redirects=False)

    assert resp.status_code == 307, f"Expected 307, got {resp.status_code}: {resp.text}"
    assert resp.headers["location"] == fake_url


# ---------------------------------------------------------------------------
# test_download_returns_404_when_archive_missing
# ---------------------------------------------------------------------------


def test_download_returns_404_when_archive_missing():
    """GET /accidents/{id}/archive returns 404 when no AccidentArchive row exists."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        admin_user = _ensure_admin_user(db)
        accident = _insert_closed_accident(db, proj, admin_user)
        accident_id = accident.id

    client = _logged_in_client()
    resp = client.get(_make_archive_url(accident_id))
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


def _delete_accident_url(accident_id: int) -> str:
    return f"/api/admin/accidents/{accident_id}"


def _logged_in_perfil9_client() -> TestClient:
    """Return a TestClient logged in as a perfil=9 admin (already created in D4 tests)."""
    with SessionLocal() as db:
        from sistema.app.services.passwords import hash_password as _hp
        user = db.execute(sa.select(User).where(User.chave == "D4P9")).scalar_one_or_none()
        if user is None:
            user = User(
                chave="D4P9",
                nome="D4 Perfil9",
                projeto="D1PROJ",
                checkin=False,
                local="Sala",
                last_active_at=datetime.now(tz=timezone.utc),
                inactivity_days=0,
                senha=_hp("Perfil9D4!"),
                perfil=9,
            )
            db.add(user)
        else:
            user.senha = _hp("Perfil9D4!")
            user.perfil = 9
        db.commit()

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(ADMIN_LOGIN_URL, json={"chave": "D4P9", "senha": "Perfil9D4!"})
    assert resp.status_code == 200, f"perfil=9 login failed: {resp.text}"
    return client


# ---------------------------------------------------------------------------
# test_delete_forbidden_for_non_perfil_9
# ---------------------------------------------------------------------------


def test_delete_forbidden_for_non_perfil_9():
    """DELETE /accidents/{id} must return 403 for admins with perfil != 9."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        admin_user = _ensure_admin_user(db)
        accident = _insert_closed_accident(db, proj, admin_user)
        accident_id = accident.id

    # perfil=19 admin — has full-admin access but perfil!=9
    client = _logged_in_client()
    with (
        patch("sistema.app.routers.admin.notify_admin_data_changed"),
        patch("sistema.app.routers.admin.notify_web_check_data_changed"),
        patch("sistema.app.routers.admin.delete_prefix"),
    ):
        resp = client.delete(_delete_accident_url(accident_id))

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# test_delete_404_when_unknown
# ---------------------------------------------------------------------------


def test_delete_404_when_unknown():
    """DELETE /accidents/{id} must return 404 for non-existent accident id."""
    client = _logged_in_perfil9_client()
    with (
        patch("sistema.app.routers.admin.notify_admin_data_changed"),
        patch("sistema.app.routers.admin.notify_web_check_data_changed"),
        patch("sistema.app.routers.admin.delete_prefix"),
    ):
        resp = client.delete(_delete_accident_url(999999999))

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# test_delete_409_when_active
# ---------------------------------------------------------------------------


def test_delete_409_when_active():
    """DELETE /accidents/{id} must return 409 when accident is still active (not closed)."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        admin_user = _ensure_admin_user(db)
        accident = _open_accident(db, proj, admin_user)
        accident_id = accident.id

    client = _logged_in_perfil9_client()
    with (
        patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
        patch("sistema.app.routers.admin.notify_admin_data_changed"),
        patch("sistema.app.routers.admin.notify_web_check_data_changed"),
        patch("sistema.app.routers.admin.delete_prefix"),
    ):
        resp = client.delete(_delete_accident_url(accident_id))

    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"

    # Clean up
    with SessionLocal() as db:
        _close_all_accidents(db)


# ---------------------------------------------------------------------------
# test_delete_removes_cascade
# ---------------------------------------------------------------------------


def test_delete_removes_cascade():
    """DELETE /accidents/{id} → 200, accident row removed from DB."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        admin_user = _ensure_admin_user(db)
        accident = _insert_closed_accident(db, proj, admin_user)
        accident_id = accident.id

    client = _logged_in_perfil9_client()
    with (
        patch("sistema.app.routers.admin.notify_admin_data_changed"),
        patch("sistema.app.routers.admin.notify_web_check_data_changed"),
        patch("sistema.app.routers.admin.delete_prefix"),
    ):
        resp = client.delete(_delete_accident_url(accident_id))

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is True

    # Verify the accident is gone from the DB
    with SessionLocal() as db:
        gone = db.get(Accident, accident_id)
        assert gone is None, f"Accident {accident_id} should be deleted but still exists"


# ---------------------------------------------------------------------------
# test_delete_calls_delete_prefix
# ---------------------------------------------------------------------------


def test_delete_calls_delete_prefix():
    """DELETE /accidents/{id} must call delete_prefix with the accident's numbered prefix."""
    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        admin_user = _ensure_admin_user(db)
        accident = _insert_closed_accident(db, proj, admin_user, number_override=42)
        accident_id = accident.id

    client = _logged_in_perfil9_client()
    with (
        patch("sistema.app.routers.admin.notify_admin_data_changed"),
        patch("sistema.app.routers.admin.notify_web_check_data_changed"),
        patch("sistema.app.routers.admin.delete_prefix") as mock_delete_prefix,
    ):
        resp = client.delete(_delete_accident_url(accident_id))

    assert resp.status_code == 200, resp.text
    mock_delete_prefix.assert_called_once()
    call_prefix = mock_delete_prefix.call_args[1].get("prefix") or mock_delete_prefix.call_args[0][0]
    # accident_number=42 → format_accident_number → "0042"
    assert "0042" in call_prefix, f"Expected '0042' in prefix, got: {call_prefix!r}"


# ---------------------------------------------------------------------------
# D6 wizard helpers
# ---------------------------------------------------------------------------

WIZARD_PROJECTS_URL = "/api/admin/accidents/wizard/projects"
WIZARD_LOCATIONS_URL = "/api/admin/accidents/wizard/locations"


def _insert_managed_location(db: Session, name: str, projects: list[str]) -> ManagedLocation:
    """Insert a ManagedLocation linked to the given project names."""
    import json as _json
    now = datetime.now(tz=timezone.utc)
    loc = ManagedLocation(
        local=name,
        latitude=1.0,
        longitude=103.0,
        projects_json=_json.dumps(projects),
        tolerance_meters=50,
        created_at=now,
        updated_at=now,
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


# ---------------------------------------------------------------------------
# test_wizard_lists_all_projects
# ---------------------------------------------------------------------------


def test_wizard_lists_all_projects():
    """GET /accidents/wizard/projects returns all registered projects."""
    with SessionLocal() as db:
        proj = _ensure_project(db)
        proj_id = proj.id
        proj_name = proj.name

    client = _logged_in_client()
    resp = client.get(WIZARD_PROJECTS_URL)

    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert isinstance(rows, list)
    ids = [r["id"] for r in rows]
    names = [r["name"] for r in rows]
    assert proj_id in ids
    assert proj_name in names


# ---------------------------------------------------------------------------
# test_wizard_locations_filtered_by_project
# ---------------------------------------------------------------------------


def test_wizard_locations_filtered_by_project():
    """GET /accidents/wizard/locations?project_id=X returns only locations linked to that project."""
    with SessionLocal() as db:
        proj = _ensure_project(db)
        proj_id = proj.id
        proj_name = proj.name
        loc_linked = _insert_managed_location(db, f"WizLoc_{proj_name}", [proj_name])
        loc_unlinked = _insert_managed_location(db, "WizLoc_Other", ["SOMEOTHERPROJECT"])
        linked_id = loc_linked.id
        unlinked_id = loc_unlinked.id

    client = _logged_in_client()
    resp = client.get(WIZARD_LOCATIONS_URL, params={"project_id": proj_id})

    assert resp.status_code == 200, resp.text
    rows = resp.json()
    ids = [r["id"] for r in rows]
    assert linked_id in ids, f"Linked location {linked_id} should appear; got ids={ids}"
    assert unlinked_id not in ids, f"Unlinked location {unlinked_id} must not appear"
    linked_row = next(r for r in rows if r["id"] == linked_id)
    assert linked_row["registered"] is True


# ---------------------------------------------------------------------------
# test_wizard_locations_404_for_unknown_project
# ---------------------------------------------------------------------------


def test_wizard_locations_404_for_unknown_project():
    """GET /accidents/wizard/locations?project_id=999999 returns 404."""
    client = _logged_in_client()
    resp = client.get(WIZARD_LOCATIONS_URL, params={"project_id": 999999999})
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# test_close_admin_accident_calls_real_archive_builder
# ---------------------------------------------------------------------------


def test_close_admin_accident_calls_real_archive_builder(tmp_path):
    """POST /close calls the real archive builder and creates an AccidentArchive row.

    BackgroundTasks runs synchronously in TestClient so the archive is created
    before the response is returned.  We mock only object_storage settings
    (no real Spaces) and the lifecycle + archive brokers (no SSE threads).
    """
    from unittest.mock import MagicMock
    from unittest.mock import patch as _patch
    import sqlalchemy as _sa

    with SessionLocal() as db:
        _close_all_accidents(db)
        proj = _ensure_project(db)
        admin_user = _ensure_admin_user(db)
        accident = _open_accident(db, proj, admin_user)
        accident_id = accident.id

    client = _logged_in_client()

    fake_settings = MagicMock(
        event_archives_dir=str(tmp_path),
        do_spaces_bucket=None,
        do_spaces_access_key=None,
        do_spaces_secret_key=None,
        tz_name="UTC",
    )

    with (
        _patch("sistema.app.services.accident_lifecycle.notify_admin_data_changed"),
        _patch("sistema.app.services.accident_lifecycle.notify_web_check_data_changed"),
        _patch("sistema.app.services.accident_archive_builder.notify_admin_data_changed"),
        _patch("sistema.app.services.object_storage.settings", fake_settings),
        _patch("sistema.app.services.accident_archive_builder._use_remote", return_value=False),
    ):
        resp = client.post("/api/admin/accidents/close")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    with SessionLocal() as db:
        archive = db.execute(
            _sa.select(AccidentArchive).where(AccidentArchive.accident_id == accident_id)
        ).scalar_one_or_none()

    assert archive is not None, "AccidentArchive row not created by real builder"
    assert archive.zip_object_key is not None
    assert archive.xlsx_object_key is not None
    assert archive.size_bytes is not None and archive.size_bytes > 0
