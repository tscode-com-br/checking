"""P5.1 (plan002 change A enabler) — scoped relaxation of the non-operational-local guard.

The Kotlin app (X-Client: checking-android) may CHECK IN at "Localização não Cadastrada";
the browser web app and ANY check-out still 422. The project uses forms_enabled=False so the
submit records the event WITHOUT triggering any FORMS side effects.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa

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
from sistema.app.models import CheckingHistory, Project, User  # noqa: E402
from sistema.app.services.passwords import hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)

SUBMIT_URL = "/api/web/check"
LOGIN_URL = "/api/web/auth/login"
ANDROID_HEADERS = {"X-Client": "checking-android"}

_CHAVE = "UL01"
_SENHA = "UnregLoc1!"
_PROJECT = "SUBMITLOC"
_UNREGISTERED = "Localização não Cadastrada"


def _ensure_user_and_project() -> None:
    with SessionLocal() as db:
        proj = db.execute(sa.select(Project).where(Project.name == _PROJECT)).scalar_one_or_none()
        if proj is None:
            proj = Project(
                name=_PROJECT,
                country_code="SG",
                country_name="Singapore",
                timezone_name="Asia/Singapore",
                address="1 Unreg Loc Rd",
                zip_code="099222",
                forms_enabled=False,  # keep the submit free of FORMS side effects
                transport_enabled=True,
                emergency_phone="",
            )
            db.add(proj)
        else:
            proj.forms_enabled = False
        user = db.execute(sa.select(User).where(User.chave == _CHAVE)).scalar_one_or_none()
        if user is None:
            user = User(
                rfid=None,
                chave=_CHAVE,
                nome="Unreg Loc User",
                projeto=_PROJECT,
                checkin=False,
                local="Escritório",
                last_active_at=datetime.now(tz=timezone.utc),
                inactivity_days=0,
                senha=hash_password(_SENHA),
            )
            db.add(user)
        else:
            user.senha = hash_password(_SENHA)
            user.projeto = _PROJECT
        db.commit()


def _payload(action: str, local: str | None = _UNREGISTERED) -> dict:
    return {
        "chave": _CHAVE,
        "projeto": _PROJECT,
        "action": action,
        "local": local,
        "informe": "normal",
        "event_time": datetime.now(tz=timezone.utc).isoformat(),
        "client_event_id": str(uuid.uuid4()),
    }


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture()
def session_cookies(client):
    _ensure_user_and_project()
    resp = client.post(LOGIN_URL, json={"chave": _CHAVE, "senha": _SENHA})
    assert resp.status_code == 200, resp.text
    return resp.cookies


def test_web_client_checkin_unregistered_local_still_422(client, session_cookies):
    # (a) Browser web app (no X-Client header) + check-in + "não Cadastrada" → still rejected.
    resp = client.post(SUBMIT_URL, json=_payload("checkin"), cookies=session_cookies)
    assert resp.status_code == 422, resp.text


def test_android_checkin_unregistered_local_accepted_and_recorded(client, session_cookies):
    # (b) Kotlin app header + check-in + "não Cadastrada" → 200 and recorded with that local.
    resp = client.post(
        SUBMIT_URL, json=_payload("checkin"), headers=ANDROID_HEADERS, cookies=session_cookies
    )
    assert resp.status_code == 200, resp.text

    with SessionLocal() as db:
        row = db.execute(
            sa.select(CheckingHistory)
            .where(
                CheckingHistory.chave == _CHAVE,
                CheckingHistory.atividade == "check-in",
                CheckingHistory.local == _UNREGISTERED,
            )
            .limit(1)
        ).scalar_one_or_none()
    assert row is not None, "android check-in should record history with the unregistered local"


def test_android_checkout_unregistered_local_still_422(client, session_cookies):
    # (c) Kotlin app header + CHECK-OUT + "não Cadastrada" → still rejected (invariant preserved).
    resp = client.post(
        SUBMIT_URL, json=_payload("checkout"), headers=ANDROID_HEADERS, cookies=session_cookies
    )
    assert resp.status_code == 422, resp.text
