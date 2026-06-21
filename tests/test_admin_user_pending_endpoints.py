"""EP4 (plan003 §2.5) — admin user-pending endpoints. Focused matrix; TP2 expands (union scope, 403).

GET /api/admin/user-pending (project-scoped; perfil 9 = all), POST .../{id}/approve (creates User +
memberships, deletes pending, notifies, audits), POST .../{id}/reject (deletes pending, no User). All
require an admin session (perfil 1/9). Reuses the shared admin_perfil_1 / admin_perfil_9 fixtures.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

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

import pytest  # noqa: E402
import sqlalchemy as sa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from sistema.app.database import Base, SessionLocal, engine  # noqa: E402
from sistema.app.main import app  # noqa: E402
from sistema.app.models import CheckEvent, PendingUserRegistration, Project, User  # noqa: E402
from sistema.app.services.passwords import hash_password  # noqa: E402
from sistema.app.services.user_projects import list_user_project_names, replace_user_project_memberships  # noqa: E402

Base.metadata.create_all(bind=engine)

ADMIN_LOGIN_URL = "/api/admin/auth/login"
# Projects used by the scope tests (decision 2).
_P80, _P83, _P90 = "UP80", "UP83", "UP90"

LIST_URL = "/api/admin/user-pending"
STATUS_URL = "/api/web/auth/status"
_PROJECT = "UPAP"
_PROJECT2 = "UPAP2"


def _ensure_project(name: str) -> None:
    with SessionLocal() as db:
        if db.execute(sa.select(Project).where(Project.name == name)).scalar_one_or_none() is None:
            db.add(
                Project(
                    name=name,
                    country_code="SG",
                    country_name="Singapore",
                    timezone_name="Asia/Singapore",
                    address="1 Pend Rd",
                    zip_code="099111",
                    forms_enabled=False,
                    transport_enabled=False,
                    emergency_phone="",
                )
            )
            db.commit()


def _clear_pending() -> None:
    with SessionLocal() as db:
        db.execute(sa.delete(PendingUserRegistration))
        db.commit()


def _delete_user(chave: str) -> None:
    with SessionLocal() as db:
        user = db.execute(sa.select(User).where(User.chave == chave)).scalar_one_or_none()
        if user is not None:
            db.delete(user)
            db.commit()


def _seed_pending(chave: str, projetos: list[str]) -> int:
    with SessionLocal() as db:
        row = PendingUserRegistration(
            chave=chave,
            nome_completo=f"Pending {chave}",
            projetos_json=json.dumps(projetos),
            email=f"{chave.lower()}@example.com",
            password_hash="hashed-pw",
            client="checking-android",
            requested_at=datetime.now(timezone.utc),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id


def _user_exists(chave: str) -> bool:
    with SessionLocal() as db:
        return db.execute(sa.select(User.id).where(User.chave == chave)).first() is not None


@pytest.fixture(autouse=True)
def _setup():
    _ensure_project(_PROJECT)
    _ensure_project(_PROJECT2)
    _clear_pending()
    for chave in ("UP01", "UP02"):
        _delete_user(chave)
    yield
    _clear_pending()
    for chave in ("UP01", "UP02"):
        _delete_user(chave)


def test_list_user_pending_requires_admin_session():
    with TestClient(app) as client:
        resp = client.get(LIST_URL)
    assert resp.status_code == 401, resp.text


def test_perfil9_sees_all_pendings(admin_perfil_9):
    _seed_pending("UPA1", [_PROJECT])
    _seed_pending("UPA2", [_PROJECT2])
    resp = admin_perfil_9.client.get(LIST_URL)
    assert resp.status_code == 200, resp.text
    chaves = {r["chave"] for r in resp.json()}
    assert {"UPA1", "UPA2"} <= chaves


def test_perfil1_without_memberships_sees_none(admin_perfil_1):
    # admin_perfil_1 has no materialized project memberships → scoping yields nothing (scope gate active).
    _seed_pending("UPB1", [_PROJECT])
    resp = admin_perfil_1.client.get(LIST_URL)
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_approve_creates_user_with_memberships_and_removes_pending(admin_perfil_9):
    pending_id = _seed_pending("UP01", [_PROJECT])
    resp = admin_perfil_9.client.post(f"{LIST_URL}/{pending_id}/approve")
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True

    assert _user_exists("UP01"), "approve must create the User"
    with SessionLocal() as db:
        user = db.execute(sa.select(User).where(User.chave == "UP01")).scalar_one()
        assert _PROJECT in list_user_project_names(db, user)
        assert db.get(PendingUserRegistration, pending_id) is None, "pending row must be deleted"

    # /auth/status now reflects an approved (existing) user, not pending.
    with TestClient(app) as client:
        st = client.get(STATUS_URL, params={"chave": "UP01"}).json()
    assert st["found"] is True
    assert st["pending_approval"] is False

    # Re-approving the same (now-deleted) id → 404.
    again = admin_perfil_9.client.post(f"{LIST_URL}/{pending_id}/approve")
    assert again.status_code == 404, again.text


def test_reject_removes_pending_without_creating_user(admin_perfil_9):
    pending_id = _seed_pending("UP02", [_PROJECT])
    resp = admin_perfil_9.client.post(f"{LIST_URL}/{pending_id}/reject")
    assert resp.status_code == 200, resp.text
    with SessionLocal() as db:
        assert db.get(PendingUserRegistration, pending_id) is None
    assert not _user_exists("UP02"), "reject must NOT create a User"


# ── TP2 — exhaustive additions ──────────────────────────────────────────────────────────────────

_PERFIL0_CHAVE = "PF00"
_PERFIL0_SENHA = "Perfil0Pw!"


@pytest.fixture()
def admin_perfil_0():
    """A perfil-0 user CAN access the admin panel (limited scope, `user_can_access_admin_panel`) but
    lacks FULL admin access, so `require_full_admin_session` → 403 on user-pending."""
    with SessionLocal() as db:
        user = db.execute(sa.select(User).where(User.chave == _PERFIL0_CHAVE)).scalar_one_or_none()
        if user is None:
            user = User(
                rfid=None, chave=_PERFIL0_CHAVE, nome="Limited User", projeto=_PROJECT,
                checkin=False, local=None, last_active_at=datetime.now(timezone.utc),
                inactivity_days=0, perfil=0, senha=hash_password(_PERFIL0_SENHA),
            )
            db.add(user)
        else:
            user.perfil = 0
            user.senha = hash_password(_PERFIL0_SENHA)
        db.commit()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(ADMIN_LOGIN_URL, json={"chave": _PERFIL0_CHAVE, "senha": _PERFIL0_SENHA})
    assert resp.status_code == 200, f"perfil-0 admin-panel login should succeed (limited): {resp.text}"
    try:
        yield client
    finally:
        _delete_user(_PERFIL0_CHAVE)


def _set_user_memberships(chave: str, projects: list[str]) -> None:
    with SessionLocal() as db:
        user = db.execute(sa.select(User).where(User.chave == chave)).scalar_one()
        replace_user_project_memberships(db, user, projects)
        db.commit()


def _seed_user(chave: str) -> None:
    with SessionLocal() as db:
        if db.execute(sa.select(User).where(User.chave == chave)).scalar_one_or_none() is None:
            db.add(
                User(
                    rfid=None, chave=chave, nome="Existing", projeto=_PROJECT,
                    checkin=False, local=None, last_active_at=datetime.now(timezone.utc),
                    inactivity_days=0, senha=None,
                )
            )
            db.commit()


def _count_audit(action: str) -> int:
    with SessionLocal() as db:
        return db.execute(
            sa.select(sa.func.count()).select_from(CheckEvent).where(CheckEvent.action == action)
        ).scalar_one()


def test_perfil0_session_forbidden_403(admin_perfil_0):
    # TP2 #1 — perfil-0 logs into the panel (limited) but user-pending requires FULL admin → 403.
    resp = admin_perfil_0.get(LIST_URL)
    assert resp.status_code == 403, resp.text


def test_perfil1_session_allowed_200(admin_perfil_1):
    # TP2 #1 — a full admin (perfil 1) reaches the endpoint (200).
    assert admin_perfil_1.client.get(LIST_URL).status_code == 200


def test_scope_perfil1_union_and_perfil9_all(admin_perfil_1, admin_perfil_9):
    # TP2 #2 (decision 2) — project scope across P80/P83/P90.
    for p in (_P80, _P83, _P90):
        _ensure_project(p)
    _seed_pending("S80", [_P80])
    _seed_pending("S83", [_P83])
    _seed_pending("S90", [_P90])
    try:
        # perfil 9 → all three.
        chaves9 = {r["chave"] for r in admin_perfil_9.client.get(LIST_URL).json()}
        assert {"S80", "S83", "S90"} <= chaves9

        # perfil 1 scoped to {P80} → only S80.
        _set_user_memberships(admin_perfil_1.user.chave, [_P80])
        seen = {r["chave"] for r in admin_perfil_1.client.get(LIST_URL).json()}
        assert seen & {"S80", "S83", "S90"} == {"S80"}

        # perfil 1 scoped to {P80, P83} → union (S80 + S83), NOT S90.
        _set_user_memberships(admin_perfil_1.user.chave, [_P80, _P83])
        seen = {r["chave"] for r in admin_perfil_1.client.get(LIST_URL).json()}
        assert seen & {"S80", "S83", "S90"} == {"S80", "S83"}
    finally:
        _set_user_memberships(admin_perfil_1.user.chave, [])  # reset shared fixture user


def test_approve_multiproject_sets_fields_and_all_memberships(admin_perfil_9):
    for p in (_P80, _P83):
        _ensure_project(p)
    _delete_user("UPM1")
    pending_id = _seed_pending("UPM1", [_P80, _P83])
    try:
        resp = admin_perfil_9.client.post(f"{LIST_URL}/{pending_id}/approve")
        assert resp.status_code == 200, resp.text
        with SessionLocal() as db:
            user = db.execute(sa.select(User).where(User.chave == "UPM1")).scalar_one()
            assert user.nome == "Pending UPM1"          # nome_completo → User.nome
            assert user.email == "upm1@example.com"
            assert {_P80, _P83} <= set(list_user_project_names(db, user))  # memberships for ALL projetos
            assert db.get(PendingUserRegistration, pending_id) is None
    finally:
        _delete_user("UPM1")


def test_approve_idempotent_when_user_already_exists(admin_perfil_9):
    # TP2 #3 — race: the User already exists for this chave → approve cleans the pending, no 500.
    _delete_user("UPI1")
    pending_id = _seed_pending("UPI1", [_PROJECT])
    _seed_user("UPI1")
    try:
        resp = admin_perfil_9.client.post(f"{LIST_URL}/{pending_id}/approve")
        assert resp.status_code == 200, resp.text
        assert resp.json().get("already_existed") is True
        with SessionLocal() as db:
            assert db.get(PendingUserRegistration, pending_id) is None
    finally:
        _delete_user("UPI1")


def test_reject_status_reflects_no_pending(admin_perfil_9):
    # TP2 #4 — after reject, /auth/status for the key is neither found nor pending.
    _delete_user("UPR1")
    pending_id = _seed_pending("UPR1", [_PROJECT])
    assert admin_perfil_9.client.post(f"{LIST_URL}/{pending_id}/reject").status_code == 200
    assert not _user_exists("UPR1")
    with TestClient(app) as c:
        st = c.get(STATUS_URL, params={"chave": "UPR1"}).json()
    assert st["found"] is False
    assert st["pending_approval"] is False


def test_audit_events_written_for_approve_and_reject(admin_perfil_9):
    # TP2 #5 — approve/reject write a CheckEvent each; action strings ≤ 16 chars.
    assert len("user_approve") <= 16 and len("user_reject") <= 16
    before_a, before_r = _count_audit("user_approve"), _count_audit("user_reject")
    _delete_user("UPA9")
    aid = _seed_pending("UPA9", [_PROJECT])
    rid = _seed_pending("UPR9", [_PROJECT])
    try:
        assert admin_perfil_9.client.post(f"{LIST_URL}/{aid}/approve").status_code == 200
        assert admin_perfil_9.client.post(f"{LIST_URL}/{rid}/reject").status_code == 200
        assert _count_audit("user_approve") == before_a + 1
        assert _count_audit("user_reject") == before_r + 1
    finally:
        _delete_user("UPA9")


def test_approve_missing_id_returns_404(admin_perfil_9):
    # TP2 #6 — missing id → 404.
    assert admin_perfil_9.client.post(f"{LIST_URL}/99999999/approve").status_code == 404


def test_reject_out_of_scope_id_returns_404(admin_perfil_1):
    # TP2 #6 — a perfil-1 admin scoped to {P80} cannot reject a P90-only pending → 404, row untouched.
    _ensure_project(_P80)
    _ensure_project(_P90)
    pending_id = _seed_pending("S90X", [_P90])
    try:
        _set_user_memberships(admin_perfil_1.user.chave, [_P80])
        resp = admin_perfil_1.client.post(f"{LIST_URL}/{pending_id}/reject")
        assert resp.status_code == 404, resp.text
        with SessionLocal() as db:
            assert db.get(PendingUserRegistration, pending_id) is not None, "out-of-scope row must NOT be deleted"
    finally:
        _set_user_memberships(admin_perfil_1.user.chave, [])
