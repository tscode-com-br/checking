"""Integration test (E2E) — complete web accident flow.

Covers Task L3: full lifecycle from a web user opening an accident,
uploading a video, another user viewing and reporting, to an admin
confirming both users appear in situation_rows.

Steps covered
-------------
1.  User-1: POST /api/web/auth/login          → session cookie
2.  User-1: GET  /api/web/check/accident/state → is_active=False (no active accident)
3.  User-1: POST /api/web/check/accident/open  → 200, is_active=True
4.  DB check: EmailDeliveryLog rows created for 'help' report after
             explicit /report call with status='help'
5.  User-1: POST /api/web/check/accident/video (multipart) → 200
6.  User-2: GET  /api/web/check/accident/state → is_active=True (sees active accident)
7.  User-2: POST /api/web/check/accident/report {zone: 'safety', status: 'ok'} → 200
8.  Admin:  GET  /api/admin/accidents/active   → situation_rows includes both users
"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from sistema.app.database import SessionLocal
from sistema.app.models import (
    Accident,
    AccidentArchive,
    AccidentUserReport,
    AccidentVideoUpload,
    AdminUser,
    EmailDeliveryLog,
    Project,
    User,
    UserProjectMembership,
)
from sistema.app.main import app
from sistema.app.services.passwords import hash_password

# ---------------------------------------------------------------------------
# Constants — chaves and passwords for this test module
# ---------------------------------------------------------------------------

_U1_CHAVE = "WL31"
_U1_PASS = "WLu1pass!"

_U2_CHAVE = "WL32"
_U2_PASS = "WLu2pass!"

_ADMIN_CHAVE = "WL3A"
_ADMIN_PASS = "WLadmin!"

_PROJ_NAME = "L3WebProject"

# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------

WEB_LOGIN_URL = "/api/web/auth/login"
WEB_STATE_URL = "/api/web/check/accident/state"
WEB_OPEN_URL = "/api/web/check/accident/open"
WEB_REPORT_URL = "/api/web/check/accident/report"
WEB_VIDEO_URL = "/api/web/check/accident/video"
ADMIN_LOGIN_URL = "/api/admin/auth/login"
ADMIN_ACTIVE_URL = "/api/admin/accidents/active"

# ---------------------------------------------------------------------------
# Patches needed to avoid hitting real SSE brokers or cloud storage
# ---------------------------------------------------------------------------

_LIFECYCLE_PATCHES = [
    "sistema.app.services.accident_lifecycle.notify_admin_data_changed",
    "sistema.app.services.accident_lifecycle.notify_web_check_data_changed",
]

# stream_upload_to_storage is defined in web_check.py as an async wrapper
_VIDEO_UPLOAD_PATCH = "sistema.app.routers.web_check.stream_upload_to_storage"

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _wipe_accidents(db: sa.orm.Session) -> None:
    """Close any open accident and remove all accident-related rows."""
    now = datetime.now(timezone.utc)
    db.execute(
        sa.update(Accident)
        .where(Accident.closed_at.is_(None))
        .values(closed_at=now, updated_at=now)
    )
    db.execute(sa.delete(EmailDeliveryLog))
    db.execute(sa.delete(AccidentArchive))
    db.execute(sa.delete(AccidentVideoUpload))
    db.execute(sa.delete(AccidentUserReport))
    db.execute(sa.delete(Accident))
    db.commit()


def _get_or_create_project(db: sa.orm.Session) -> Project:
    proj = db.execute(
        sa.select(Project).where(Project.name == _PROJ_NAME)
    ).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=_PROJ_NAME,
            country_code="SG",
            country_name="Singapore",
            timezone_name="Asia/Singapore",
            address="1 Web L3 St",
            zip_code="099001",
        )
        db.add(proj)
        db.flush()
    return proj


def _get_or_create_web_user(
    db: sa.orm.Session,
    proj: Project,
    chave: str,
    nome: str,
    senha: str,
    *,
    checkin: bool = True,
) -> User:
    user = db.execute(
        sa.select(User).where(User.chave == chave)
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            chave=chave,
            nome=nome,
            projeto=_PROJ_NAME,
            checkin=checkin,
            local="Site L3",
            email=f"{chave.lower()}@l3test.example.com",
            last_active_at=now,
            inactivity_days=0,
            perfil=1,  # perfil=1 allows web login
            senha=hash_password(senha),
        )
        db.add(user)
        db.flush()
    else:
        user.checkin = checkin
        user.email = f"{chave.lower()}@l3test.example.com"
        user.perfil = 1
        user.senha = hash_password(senha)
        user.projeto = _PROJ_NAME
    return user


def _ensure_membership(db: sa.orm.Session, user: User, proj: Project) -> None:
    exists = db.execute(
        sa.select(UserProjectMembership).where(
            UserProjectMembership.user_id == user.id,
            UserProjectMembership.project_id == proj.id,
        )
    ).scalar_one_or_none()
    if exists is None:
        now = datetime.now(timezone.utc)
        db.add(
            UserProjectMembership(
                user_id=user.id,
                project_id=proj.id,
                created_at=now,
                updated_at=now,
            )
        )


def _get_or_create_admin(db: sa.orm.Session, proj: Project) -> tuple[User, AdminUser]:
    user = db.execute(
        sa.select(User).where(User.chave == _ADMIN_CHAVE)
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            chave=_ADMIN_CHAVE,
            nome="L3 Admin",
            projeto=_PROJ_NAME,
            checkin=False,
            local="",
            email=f"{_ADMIN_CHAVE.lower()}@l3test.example.com",
            last_active_at=now,
            inactivity_days=0,
            perfil=1,
            senha=hash_password(_ADMIN_PASS),
        )
        db.add(user)
        db.flush()
    else:
        user.senha = hash_password(_ADMIN_PASS)
        user.perfil = 1
    admin = db.execute(
        sa.select(AdminUser).where(AdminUser.chave == _ADMIN_CHAVE)
    ).scalar_one_or_none()
    if admin is None:
        admin = AdminUser(
            chave=_ADMIN_CHAVE,
            nome_completo="L3 Admin Full",
            created_at=now,
            updated_at=now,
        )
        db.add(admin)
        db.flush()
    return user, admin


def _web_login(chave: str, senha: str) -> TestClient:
    """Create a TestClient for the web API, pre-authenticated."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(WEB_LOGIN_URL, json={"chave": chave, "senha": senha})
    assert resp.status_code == 200, f"Web login failed for {chave}: {resp.text}"
    return client


def _admin_login(chave: str, senha: str) -> TestClient:
    """Create an admin TestClient, pre-authenticated."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(ADMIN_LOGIN_URL, json={"chave": chave, "senha": senha})
    assert resp.status_code == 200, f"Admin login failed for {chave}: {resp.text}"
    return client


# ---------------------------------------------------------------------------
# The integration test
# ---------------------------------------------------------------------------


def test_complete_web_flow():
    """Full web accident cycle from open to admin verifying both users.

    Steps:
    1.  User-1 logs in via web.
    2.  GET /state → is_active=False (no active accident).
    3.  POST /open with zone='safety', status='ok' → 200.
    4.  POST /report with zone='accident', status='help' → triggers help emails;
        DB confirms EmailDeliveryLog rows created.
    5.  POST /video (multipart) → 200 with video_id.
    6.  User-2 logs in and GET /state → is_active=True (sees the accident).
    7.  User-2 POST /report zone='safety', status='ok' → 200.
    8.  Admin GET /admin/accidents/active → situation_rows contains both users.
    """

    # -----------------------------------------------------------------------
    # Setup: create project, users, admin; wipe any leftover accident state
    # -----------------------------------------------------------------------
    with SessionLocal() as db:
        _wipe_accidents(db)
        proj = _get_or_create_project(db)
        u1 = _get_or_create_web_user(db, proj, _U1_CHAVE, "Web L3 User 1", _U1_PASS, checkin=True)
        u2 = _get_or_create_web_user(db, proj, _U2_CHAVE, "Web L3 User 2", _U2_PASS, checkin=True)
        _ensure_membership(db, u1, proj)
        _ensure_membership(db, u2, proj)
        _get_or_create_admin(db, proj)
        proj_id = proj.id
        db.commit()

    fake_video_upload = AsyncMock(return_value=(1024, "https://fake-storage.example.com/l3clip.mp4"))

    with (
        patch(_LIFECYCLE_PATCHES[0]),
        patch(_LIFECYCLE_PATCHES[1]),
        patch(_VIDEO_UPLOAD_PATCH, fake_video_upload),
        patch("sistema.app.routers.web_check.queue_help_request_emails") as mock_queue_emails,
    ):
        # -------------------------------------------------------------------
        # Step 1: User-1 logs in
        # -------------------------------------------------------------------
        client1 = _web_login(_U1_CHAVE, _U1_PASS)

        # -------------------------------------------------------------------
        # Step 2: GET /state → no active accident
        # -------------------------------------------------------------------
        resp = client1.get(WEB_STATE_URL, params={"chave": _U1_CHAVE})
        assert resp.status_code == 200, f"[Step 2] {resp.text}"
        state_data = resp.json()
        assert state_data["is_active"] is False

        # -------------------------------------------------------------------
        # Step 3: POST /open — user-1 opens with zone=safety, status=ok
        #   (keeping status=ok here so step 4 can fire a real help transition)
        # -------------------------------------------------------------------
        resp = client1.post(
            WEB_OPEN_URL,
            json={
                "chave": _U1_CHAVE,
                "project_id": proj_id,
                "location_id": None,
                "custom_location_name": "L3 Web Test Site",
                "zone": "safety",
                "status": "ok",
            },
        )
        assert resp.status_code == 200, f"[Step 3] {resp.text}"
        open_data = resp.json()
        assert open_data["is_active"] is True
        assert open_data["project_name"] == _PROJ_NAME
        assert open_data["location_name"] == "L3 Web Test Site"
        assert open_data["current_user_report"] is not None
        assert open_data["current_user_report"]["zone"] == "safety"
        assert open_data["current_user_report"]["status"] == "ok"

        # -------------------------------------------------------------------
        # Step 4: POST /report with status='help' → fires queue_help_request_emails
        # -------------------------------------------------------------------
        resp = client1.post(
            WEB_REPORT_URL,
            json={"chave": _U1_CHAVE, "zone": "accident", "status": "help"},
        )
        assert resp.status_code == 200, f"[Step 4] {resp.text}"
        report_data = resp.json()
        assert report_data["current_user_report"]["status"] == "help"
        # BackgroundTask is synchronous in TestClient — queue_help_request_emails was called
        mock_queue_emails.assert_called_once()
        call_kwargs = mock_queue_emails.call_args[1]
        assert "accident_id" in call_kwargs
        assert "requester_user_id" in call_kwargs

        # -------------------------------------------------------------------
        # Step 5: POST /video — user-1 uploads a video clip
        # -------------------------------------------------------------------
        fake_video_content = b"fake-video-bytes-l3"
        resp = client1.post(
            WEB_VIDEO_URL,
            files={
                "chave": (None, _U1_CHAVE, "text/plain"),
                "idempotency_key": (None, "l3-test-idem-key-001", "text/plain"),
                "video": ("l3clip.mp4", fake_video_content, "video/mp4"),
            },
        )
        assert resp.status_code == 200, f"[Step 5] {resp.text}"
        video_data = resp.json()
        assert "video_id" in video_data
        assert "public_url" in video_data
        assert video_data["public_url"].startswith("https://fake-storage.example.com/")

        # -------------------------------------------------------------------
        # Step 6: User-2 logs in and sees the active accident
        # -------------------------------------------------------------------
        client2 = _web_login(_U2_CHAVE, _U2_PASS)

        resp = client2.get(WEB_STATE_URL, params={"chave": _U2_CHAVE})
        assert resp.status_code == 200, f"[Step 6] {resp.text}"
        state2 = resp.json()
        assert state2["is_active"] is True
        assert state2["project_name"] == _PROJ_NAME
        assert state2["location_name"] == "L3 Web Test Site"

        # -------------------------------------------------------------------
        # Step 7: User-2 reports zone=safety, status=ok
        # -------------------------------------------------------------------
        resp = client2.post(
            WEB_REPORT_URL,
            json={"chave": _U2_CHAVE, "zone": "safety", "status": "ok"},
        )
        assert resp.status_code == 200, f"[Step 7] {resp.text}"
        report2 = resp.json()
        assert report2["is_active"] is True
        assert report2["current_user_report"]["zone"] == "safety"
        assert report2["current_user_report"]["status"] == "ok"

    # -------------------------------------------------------------------
    # Step 8: Admin verifies both users appear in situation_rows
    #   (outside the patch context — uses separate admin client with
    #    its own patches for admin SSE)
    # -------------------------------------------------------------------
    admin_client = _admin_login(_ADMIN_CHAVE, _ADMIN_PASS)

    with (
        patch(_LIFECYCLE_PATCHES[0]),
        patch(_LIFECYCLE_PATCHES[1]),
    ):
        resp = admin_client.get(ADMIN_ACTIVE_URL)

    assert resp.status_code == 200, f"[Step 8] {resp.text}"
    admin_data = resp.json()
    assert admin_data["is_active"] is True, "Accident should still be active"
    situation_rows = admin_data["situation_rows"]
    assert isinstance(situation_rows, list), "situation_rows should be a list"
    # Both user-1 (chave=WL31) and user-2 (chave=WL32) should appear
    chaves_in_rows = {row["chave"] for row in situation_rows}
    assert _U1_CHAVE in chaves_in_rows, (
        f"User-1 chave ({_U1_CHAVE}) not in situation_rows: {chaves_in_rows}"
    )
    assert _U2_CHAVE in chaves_in_rows, (
        f"User-2 chave ({_U2_CHAVE}) not in situation_rows: {chaves_in_rows}"
    )

    # Verify user-1 is reported as zone=Acidente, status=AJUDA (localized)
    u1_row = next(r for r in situation_rows if r["chave"] == _U1_CHAVE)
    assert u1_row["zone"] == "Acidente"
    assert u1_row["status"] == "AJUDA"

    # Verify user-2 is reported as zone=Segurança, status=OK (localized)
    u2_row = next(r for r in situation_rows if r["chave"] == _U2_CHAVE)
    assert u2_row["zone"] == "Segurança"
    assert u2_row["status"] == "OK"
