"""P1.2 (plan002 change D) — GET /api/web/check/history.

Mirrors the /check/state test harness (shared SQLite + login session). Asserts the new
read-only endpoint returns the user's history newest-first, maps atividade→action,
passes location through (incl. null), and rejects a malformed chave with 422.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

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

HISTORY_URL = "/api/web/check/history"
LOGIN_URL = "/api/web/auth/login"

_CHAVE = "WH01"
_SENHA = "WebHist1!"
_PROJECT = "WHPTEST"
_T0 = datetime(2026, 6, 15, 1, 0, 0, tzinfo=timezone.utc)


def _ensure_user_and_project(db: sa.orm.Session) -> User:
    proj = db.execute(sa.select(Project).where(Project.name == _PROJECT)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=_PROJECT,
            country_code="SG",
            country_name="Singapore",
            timezone_name="Asia/Singapore",
            address="1 History Rd",
            zip_code="099111",
            forms_enabled=True,
            transport_enabled=True,
            emergency_phone="",
        )
        db.add(proj)
        db.flush()

    user = db.execute(sa.select(User).where(User.chave == _CHAVE)).scalar_one_or_none()
    if user is None:
        user = User(
            rfid=None,
            chave=_CHAVE,
            nome="Web History User",
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
    return user


def _seed_history(db: sa.orm.Session) -> None:
    db.execute(sa.delete(CheckingHistory).where(CheckingHistory.chave == _CHAVE))
    # Insert oldest→newest; the endpoint must return them newest-first.
    rows = [
        # time,                atividade,    local
        (_T0,                  "check-in",   "Localização não Cadastrada"),
        (_T0 + timedelta(hours=2), "check-out", None),
        (_T0 + timedelta(hours=4), "check-in",  "Área X"),
    ]
    for ts, atividade, local in rows:
        db.add(
            CheckingHistory(
                chave=_CHAVE,
                atividade=atividade,
                projeto=_PROJECT,
                time=ts,
                informe="normal",
                local=local,
            )
        )
    db.commit()


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture()
def session_cookies(client):
    with SessionLocal() as db:
        _ensure_user_and_project(db)
        _seed_history(db)
    resp = client.post(LOGIN_URL, json={"chave": _CHAVE, "senha": _SENHA})
    assert resp.status_code == 200, resp.text
    return resp.cookies


def test_history_returns_rows_newest_first_with_mapped_action_and_local(client, session_cookies):
    resp = client.get(f"{HISTORY_URL}?chave={_CHAVE}", cookies=session_cookies)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 3

    # Newest-first: the 04:00 check-in at "Área X" comes first.
    assert items[0]["action"] == "checkin"
    assert items[0]["local"] == "Área X"
    assert items[0]["projeto"] == _PROJECT
    assert items[0]["informe"] == "normal"

    # check-out at 02:00 with NULL local maps to "checkout" and passes null through.
    assert items[1]["action"] == "checkout"
    assert items[1]["local"] is None

    # Oldest: the 01:00 check-in at the "não Cadastrada" location.
    assert items[2]["action"] == "checkin"
    assert items[2]["local"] == "Localização não Cadastrada"

    # Strictly descending by time.
    times = [item["time"] for item in items]
    assert times == sorted(times, reverse=True)


def test_history_malformed_chave_returns_422(client, session_cookies):
    resp = client.get(f"{HISTORY_URL}?chave=AB", cookies=session_cookies)
    assert resp.status_code == 422, resp.text


def test_history_without_session_is_unauthorized(client):
    resp = client.get(f"{HISTORY_URL}?chave={_CHAVE}")
    assert resp.status_code == 401, resp.text


def test_history_returns_multiple_projects_and_serializes_null_local(client, session_cookies):
    # TP6 — rows across MULTIPLE projects, check-in AND check-out, with a null local serialized as JSON null.
    with SessionLocal() as db:
        db.execute(sa.delete(CheckingHistory).where(CheckingHistory.chave == _CHAVE))
        db.add(CheckingHistory(
            chave=_CHAVE, atividade="check-in", projeto="WHP-A", time=_T0,
            informe="normal", local="Unidade A",
        ))
        db.add(CheckingHistory(
            chave=_CHAVE, atividade="check-out", projeto="WHP-B", time=_T0 + timedelta(hours=1),
            informe="normal", local=None,
        ))
        db.commit()

    resp = client.get(f"{HISTORY_URL}?chave={_CHAVE}", cookies=session_cookies)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert {i["projeto"] for i in items} == {"WHP-A", "WHP-B"}

    a = next(i for i in items if i["projeto"] == "WHP-A")
    assert a["action"] == "checkin"
    assert a["local"] == "Unidade A"

    b = next(i for i in items if i["projeto"] == "WHP-B")
    assert b["action"] == "checkout"
    assert b["local"] is None  # null local serialized as JSON null
