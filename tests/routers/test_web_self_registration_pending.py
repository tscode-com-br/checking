"""EP3 (plan003 §2.4) — register-user approval gate. Focused matrix; TP1 expands this file.

Flag ON (default): self-registration creates a `pending_user_registrations` row and does NOT
authenticate (no `User`, no session). Flag OFF: legacy create-and-authenticate. Pending queue cap →
"queue_full". Duplicates → 409. Invalid payload → 422. The gate is system-wide (NOT X-Client-gated);
`X-Client` is recorded only as `client`.
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

from sistema.app.core.config import settings  # noqa: E402
from sistema.app.database import Base, SessionLocal, engine  # noqa: E402
from sistema.app.main import app  # noqa: E402
from sistema.app.models import AdminAccessRequest, PendingUserRegistration, Project, User  # noqa: E402

Base.metadata.create_all(bind=engine)

REGISTER_URL = "/api/web/auth/register-user"
STATUS_URL = "/api/web/auth/status"
ANDROID_HEADERS = {"X-Client": "checking-android"}
_PROJECT = "PENDREG"


def _ensure_project() -> None:
    with SessionLocal() as db:
        proj = db.execute(sa.select(Project).where(Project.name == _PROJECT)).scalar_one_or_none()
        if proj is None:
            db.add(
                Project(
                    name=_PROJECT,
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


def _pending_count() -> int:
    with SessionLocal() as db:
        return db.execute(sa.select(sa.func.count()).select_from(PendingUserRegistration)).scalar_one()


def _user_exists(chave: str) -> bool:
    with SessionLocal() as db:
        return db.execute(sa.select(User.id).where(User.chave == chave)).first() is not None


def _payload(chave: str) -> dict:
    return {
        "chave": chave,
        "nome": "Pending User",
        "projetos": [_PROJECT],
        "email": "pend@example.com",
        "senha": "abc123",
        "confirmar_senha": "abc123",
    }


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    _ensure_project()
    _clear_pending()
    monkeypatch.setattr(settings, "check_user_approval_required", True)  # gate ON by default
    yield
    _clear_pending()


def test_flag_on_android_creates_pending_not_authenticated(client):
    chave = "PNA1"
    _delete_user(chave)
    resp = client.post(REGISTER_URL, json=_payload(chave), headers=ANDROID_HEADERS)
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["authenticated"] is False
    assert body["pending_approval"] is True

    assert not _user_exists(chave), "pending registration must NOT create a User"
    with SessionLocal() as db:
        row = db.execute(
            sa.select(PendingUserRegistration).where(PendingUserRegistration.chave == chave)
        ).scalar_one()
        assert row.client == "checking-android"
        assert row.nome_completo == "Pending User"

    # /auth/status reflects pending and NO session (not authenticated).
    st = client.get(STATUS_URL, params={"chave": chave})
    assert st.status_code == 200
    sb = st.json()
    assert sb["found"] is False
    assert sb["pending_approval"] is True
    assert sb["authenticated"] is False


def test_flag_on_web_no_header_also_pending(client):
    # Gate is system-wide: a browser client (no X-Client) is queued too; client recorded as "web".
    chave = "PNW1"
    _delete_user(chave)
    resp = client.post(REGISTER_URL, json=_payload(chave))
    assert resp.status_code == 202, resp.text
    assert resp.json()["status"] == "pending"
    with SessionLocal() as db:
        row = db.execute(
            sa.select(PendingUserRegistration).where(PendingUserRegistration.chave == chave)
        ).scalar_one()
        assert row.client == "web"


def test_flag_on_queue_full_inserts_nothing(client, monkeypatch):
    monkeypatch.setattr(settings, "pending_user_registration_limit", 2)
    for chave in ("PF01", "PF02"):
        assert client.post(REGISTER_URL, json=_payload(chave), headers=ANDROID_HEADERS).status_code == 202
    assert _pending_count() == 2

    resp = client.post(REGISTER_URL, json=_payload("PF03"), headers=ANDROID_HEADERS)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "queue_full"
    assert body["queue_full"] is True
    assert _pending_count() == 2, "queue-full must insert nothing"
    assert not _user_exists("PF03")


def test_flag_off_legacy_authenticates_and_creates_user(client, monkeypatch):
    monkeypatch.setattr(settings, "check_user_approval_required", False)
    chave = "PLG1"
    _delete_user(chave)
    try:
        resp = client.post(REGISTER_URL, json=_payload(chave), headers=ANDROID_HEADERS)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "registered"
        assert body["authenticated"] is True
        assert _user_exists(chave)
        assert _pending_count() == 0
    finally:
        _delete_user(chave)


def test_duplicate_chave_returns_409(client):
    chave = "PDP1"
    _delete_user(chave)
    assert client.post(REGISTER_URL, json=_payload(chave), headers=ANDROID_HEADERS).status_code == 202
    # Second registration for the same chave (existing pending) → 409.
    resp = client.post(REGISTER_URL, json=_payload(chave), headers=ANDROID_HEADERS)
    assert resp.status_code == 409, resp.text


def test_invalid_payload_returns_422_no_pending(client):
    bad = _payload("PIV1")
    bad["senha"] = "x"  # too short (min 3)
    resp = client.post(REGISTER_URL, json=bad, headers=ANDROID_HEADERS)
    assert resp.status_code == 422, resp.text
    assert _pending_count() == 0


# ── TP1 — exhaustive additions ──────────────────────────────────────────────────────────────────

USER_PROJECTS_URL = "/api/web/user-projects"  # authenticated-only (proves "no session")


def _seed_user(chave: str) -> None:
    with SessionLocal() as db:
        if db.execute(sa.select(User).where(User.chave == chave)).scalar_one_or_none() is None:
            db.add(
                User(
                    rfid=None,
                    chave=chave,
                    nome="Existing User",
                    projeto=_PROJECT,
                    checkin=False,
                    local=None,
                    last_active_at=datetime.now(timezone.utc),
                    inactivity_days=0,
                    senha=None,
                )
            )
            db.commit()


def _seed_admin_access_request(chave: str) -> None:
    with SessionLocal() as db:
        if db.execute(
            sa.select(AdminAccessRequest).where(AdminAccessRequest.chave == chave)
        ).scalar_one_or_none() is None:
            db.add(
                AdminAccessRequest(
                    chave=chave,
                    nome_completo="Admin Req",
                    password_hash="seed-hash",
                    requested_profile=1,
                    requested_at=datetime.now(timezone.utc),
                )
            )
            db.commit()


def _clear_admin_access_request(chave: str) -> None:
    with SessionLocal() as db:
        row = db.execute(
            sa.select(AdminAccessRequest).where(AdminAccessRequest.chave == chave)
        ).scalar_one_or_none()
        if row is not None:
            db.delete(row)
            db.commit()


def _seed_pending_rows(n: int) -> None:
    """Bulk-insert N pending rows directly (distinct 4-char chaves Q000..Q###)."""
    with SessionLocal() as db:
        now = datetime.now(timezone.utc)
        for i in range(n):
            db.add(
                PendingUserRegistration(
                    chave=f"Q{i:03d}",
                    nome_completo=f"Seed {i}",
                    projetos_json=json.dumps([_PROJECT]),
                    email=None,
                    password_hash="seed-hash",
                    client="web",
                    requested_at=now,
                )
            )
        db.commit()


def test_status_reports_pending_for_pending_key(client):
    # TP1 #3 — /auth/status is the server-derived source of truth for the awaiting state.
    chave = "PST1"
    _delete_user(chave)
    assert client.post(REGISTER_URL, json=_payload(chave), headers=ANDROID_HEADERS).status_code == 202
    sb = client.get(STATUS_URL, params={"chave": chave}).json()
    assert sb["found"] is False
    assert sb["pending_approval"] is True
    assert sb["authenticated"] is False
    assert sb["has_password"] is False


def test_pending_registration_sets_no_web_session(client):
    # TP1 #1 — a pending registration must NOT establish an authenticated session: a follow-up call to an
    # authenticated-only endpoint on the same client is rejected.
    chave = "PNS1"
    _delete_user(chave)
    assert client.post(REGISTER_URL, json=_payload(chave), headers=ANDROID_HEADERS).status_code == 202
    resp = client.get(USER_PROJECTS_URL)
    assert resp.status_code in (401, 403), resp.text


def test_existing_user_chave_returns_409_no_pending(client):
    # TP1 #4 — a chave that is already a real User → 409; no pending row created.
    chave = "EXUS"
    try:
        _seed_user(chave)
        resp = client.post(REGISTER_URL, json=_payload(chave), headers=ANDROID_HEADERS)
        assert resp.status_code == 409, resp.text
        with SessionLocal() as db:
            assert db.execute(
                sa.select(PendingUserRegistration).where(PendingUserRegistration.chave == chave)
            ).scalar_one_or_none() is None
    finally:
        _delete_user(chave)


def test_admin_access_request_chave_returns_409_no_pending(client):
    # TP1 #4 — a chave with a pending admin-access request → 409; no pending row created.
    chave = "ADRQ"
    _delete_user(chave)
    try:
        _seed_admin_access_request(chave)
        resp = client.post(REGISTER_URL, json=_payload(chave), headers=ANDROID_HEADERS)
        assert resp.status_code == 409, resp.text
        with SessionLocal() as db:
            assert db.execute(
                sa.select(PendingUserRegistration).where(PendingUserRegistration.chave == chave)
            ).scalar_one_or_none() is None
    finally:
        _clear_admin_access_request(chave)


def test_queue_full_at_real_default_limit_300(client):
    # TP1 #5 — at the REAL default cap (300, no monkeypatch): the 301st registration is queue-full and
    # inserts nothing.
    assert settings.pending_user_registration_limit == 300
    _seed_pending_rows(300)
    assert _pending_count() == 300
    resp = client.post(REGISTER_URL, json=_payload("QF01"), headers=ANDROID_HEADERS)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "queue_full"
    assert body["queue_full"] is True
    assert body["authenticated"] is False
    assert _pending_count() == 300, "queue-full must insert nothing"
    assert not _user_exists("QF01")


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda p: p.update(nome="ab"), id="short-name"),
        pytest.param(lambda p: p.update(email="not-an-email"), id="bad-email"),
        pytest.param(lambda p: p.update(senha="ab", confirmar_senha="ab"), id="password-too-short"),
        pytest.param(lambda p: p.update(senha="01234567890", confirmar_senha="01234567890"), id="password-too-long"),
        pytest.param(lambda p: p.update(projetos=[]), id="empty-projects"),
        pytest.param(lambda p: p.update(confirmar_senha="different1"), id="confirmation-mismatch"),
    ],
)
def test_invalid_payloads_return_422_no_pending(client, mutate):
    # TP1 #6 — every invalid field → 422; nothing queued.
    payload = _payload("PIV2")
    mutate(payload)
    resp = client.post(REGISTER_URL, json=payload, headers=ANDROID_HEADERS)
    assert resp.status_code == 422, resp.text
    assert _pending_count() == 0


def test_flag_off_web_no_header_also_authenticates(client, monkeypatch):
    # TP1 #7 — flag OFF for a WEB client (no X-Client) → legacy 201 authenticated, User created.
    monkeypatch.setattr(settings, "check_user_approval_required", False)
    chave = "PLW1"
    _delete_user(chave)
    try:
        resp = client.post(REGISTER_URL, json=_payload(chave))
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "registered"
        assert body["authenticated"] is True
        assert _user_exists(chave)
        assert _pending_count() == 0
    finally:
        _delete_user(chave)
