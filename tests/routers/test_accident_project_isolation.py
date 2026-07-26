"""Cross-project isolation for Accident Mode.

Requirement: an accident reported in P80 must be invisible and untouchable to
users and perfil-1 admins allocated to P82/P83. Before this, the Check Web state
endpoint fell back to "show every active accident" whenever the user's projects
matched none, so an accident in one project raised the banner for the entire
company, and the wizard offered every project to everyone.

Perfil 9 stays unrestricted by design — it is the super-admin role that monitors
every project.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_checking.db")

from unittest.mock import patch  # noqa: E402

import sqlalchemy as sa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from sistema.app.database import Base, SessionLocal, engine  # noqa: E402
from sistema.app.main import app  # noqa: E402
from sistema.app.models import (  # noqa: E402
    Accident,
    AccidentArchive,
    AccidentUserReport,
    AccidentVideoUpload,
    AdminUser,
    Project,
    User,
    UserProjectMembership,
)
from sistema.app.services.passwords import hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)

WEB_LOGIN_URL = "/api/web/auth/login"
STATE_URL = "/api/web/check/accident/state"
OPEN_URL = "/api/web/check/accident/open"
REPORT_URL = "/api/web/check/accident/report"
ACK_URL = "/api/web/check/accident/acknowledge"
WIZARD_PROJECTS_URL = "/api/web/check/accident/wizard/projects"

_LIFECYCLE_PATCHES = (
    "sistema.app.services.accident_lifecycle.notify_admin_data_changed",
    "sistema.app.services.accident_lifecycle.notify_web_check_data_changed",
)

_PROJ_A = "IZA"       # project where the accident happens
_PROJ_B = "IZB"       # unrelated project — must stay unaware
_USER_A = "IZ1A"
_USER_B = "IZ1B"
_SENHA = "IsolTest9!"
_NOW = datetime(2026, 7, 26, 8, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures (plain helpers — the shared test DB is reused across the suite)
# ---------------------------------------------------------------------------


def _ensure_project(db, name: str) -> Project:
    proj = db.execute(sa.select(Project).where(Project.name == name)).scalar_one_or_none()
    if proj is None:
        proj = Project(
            name=name,
            country_code="SG",
            country_name="Singapore",
            timezone_name="Asia/Singapore",
            address=f"1 {name} Road",
            zip_code="000123",
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)
    return proj


def _ensure_user(db, chave: str, project: Project) -> User:
    user = db.execute(sa.select(User).where(User.chave == chave)).scalar_one_or_none()
    if user is None:
        user = User(
            chave=chave,
            nome=f"Isolation {chave}",
            projeto=project.name,
            checkin=True,
            local="Portaria",
            last_active_at=_NOW,
            inactivity_days=0,
            perfil=0,
            senha=hash_password(_SENHA),
        )
        db.add(user)
    else:
        user.senha = hash_password(_SENHA)
        user.checkin = True
        user.perfil = 0
    db.commit()
    db.refresh(user)

    membership = db.execute(
        sa.select(UserProjectMembership).where(
            UserProjectMembership.user_id == user.id,
            UserProjectMembership.project_id == project.id,
        )
    ).scalar_one_or_none()
    if membership is None:
        db.add(UserProjectMembership(
            user_id=user.id,
            project_id=project.id,
            created_at=_NOW,
            updated_at=_NOW,
        ))
        db.commit()
    # Belongs to THIS project only.
    db.execute(
        sa.delete(UserProjectMembership).where(
            UserProjectMembership.user_id == user.id,
            UserProjectMembership.project_id != project.id,
        )
    )
    db.commit()
    db.refresh(user)
    return user


def _wipe_accidents(db) -> None:
    db.execute(sa.delete(AccidentArchive))
    db.execute(sa.delete(AccidentVideoUpload))
    db.execute(sa.delete(AccidentUserReport))
    db.execute(sa.delete(Accident))
    db.commit()


def _setup() -> tuple[int, int]:
    """Two projects, one user each, an OPEN accident on project A."""
    from sistema.app.services.accident_lifecycle import open_accident
    from sistema.app.services.admin_identity import ensure_admin_user_by_chave

    with SessionLocal() as db:
        proj_a = _ensure_project(db, _PROJ_A)
        proj_b = _ensure_project(db, _PROJ_B)
        _ensure_user(db, _USER_A, proj_a)
        _ensure_user(db, _USER_B, proj_b)
        _wipe_accidents(db)

        actor = ensure_admin_user_by_chave(db, chave="IZAD", nome_completo="Isolation Admin")
        db.commit()
        with patch(_LIFECYCLE_PATCHES[0]), patch(_LIFECYCLE_PATCHES[1]):
            accident = open_accident(
                db,
                origin="admin",
                project_id=proj_a.id,
                custom_location_name="Portaria A",
                opened_by_admin_id=actor.id,
            )
        return accident.id, proj_a.id


def _login(chave: str) -> TestClient:
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(WEB_LOGIN_URL, json={"chave": chave, "senha": _SENHA})
    assert resp.status_code == 200, f"login {chave} failed: {resp.status_code} {resp.text}"
    return client


# ---------------------------------------------------------------------------
# The user in the accident's project
# ---------------------------------------------------------------------------


def test_user_in_the_accident_project_sees_it():
    accident_id, _ = _setup()
    client = _login(_USER_A)

    resp = client.get(STATE_URL, params={"chave": _USER_A})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is True
    assert data["accident_id"] == accident_id


# ---------------------------------------------------------------------------
# The user in an unrelated project
# ---------------------------------------------------------------------------


def test_user_of_another_project_gets_no_alert():
    """The core requirement: an accident in IZA must not reach IZB users."""
    _setup()
    client = _login(_USER_B)

    resp = client.get(STATE_URL, params={"chave": _USER_B})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is False, (
        "a user allocated to another project must not see the accident banner"
    )
    assert not data.get("active_accidents")


def test_user_of_another_project_cannot_report_into_it():
    _setup()
    client = _login(_USER_B)

    with patch(_LIFECYCLE_PATCHES[0]), patch(_LIFECYCLE_PATCHES[1]):
        resp = client.post(
            REPORT_URL, json={"chave": _USER_B, "zone": "safety", "status": "ok"}
        )
    assert resp.status_code == 409, resp.text

    # And no row was created for them in the other project's situation table.
    with SessionLocal() as db:
        user_b = db.execute(sa.select(User).where(User.chave == _USER_B)).scalar_one()
        rows = db.execute(
            sa.select(AccidentUserReport).where(AccidentUserReport.user_id == user_b.id)
        ).scalars().all()
    assert rows == [], "the foreign user must not be inserted into the situation table"


def test_user_of_another_project_cannot_acknowledge_it():
    accident_id, _ = _setup()
    client = _login(_USER_B)

    resp = client.post(ACK_URL, json={"chave": _USER_B})
    assert resp.status_code == 409, resp.text

    # Nor by naming the accident explicitly.
    resp_targeted = client.post(
        ACK_URL, json={"chave": _USER_B, "accident_id": accident_id}
    )
    assert resp_targeted.status_code == 404, resp_targeted.text


def test_wizard_offers_only_the_users_own_project():
    _setup()
    client = _login(_USER_B)

    resp = client.get(WIZARD_PROJECTS_URL, params={"chave": _USER_B})
    assert resp.status_code == 200, resp.text
    names = {row["name"] for row in resp.json()}
    assert names == {_PROJ_B}, f"expected only {_PROJ_B}, got {names}"


def test_user_cannot_open_an_accident_on_another_project():
    """project_id arrives in the body, so the endpoint must enforce membership —
    opening an accident pages that project's entire team."""
    _, proj_a_id = _setup()
    with SessionLocal() as db:
        _wipe_accidents(db)
    client = _login(_USER_B)

    with patch(_LIFECYCLE_PATCHES[0]), patch(_LIFECYCLE_PATCHES[1]):
        resp = client.post(
            OPEN_URL,
            json={
                "chave": _USER_B,
                "project_id": proj_a_id,
                "location_id": None,
                "custom_location_name": "Invasao",
                "zone": "accident",
                "status": "help",
                "description": "nao deveria abrir",
            },
        )
    assert resp.status_code == 404, resp.text

    with SessionLocal() as db:
        opened = db.execute(
            sa.select(Accident).where(Accident.project_id == proj_a_id)
        ).scalars().all()
    assert opened == [], "no accident may be created on a project the user is not in"


# ---------------------------------------------------------------------------
# Admin SSE fan-out filter
# ---------------------------------------------------------------------------


def test_sse_filter_drops_other_projects_accident_events():
    """The admin front renders the emergency-call bar straight from the SSE
    payload, so filtering has to happen before the event leaves the server."""
    import json

    from sistema.app.routers.admin import _sse_payload_in_admin_scope

    p80_call = json.dumps({
        "reason": "emergency_call_initiated",
        "project_name": "P80",
        "call_number_label": "000013",
    })
    p80_accident = json.dumps({"reason": "accident_opened", "project_name": "P80"})
    p82_accident = json.dumps({"reason": "accident_opened", "project_name": "P82"})
    presence = json.dumps({"reason": "refresh"})

    # perfil 1 scoped to P82
    assert _sse_payload_in_admin_scope(p82_accident, ["P82"]) is True
    assert _sse_payload_in_admin_scope(p80_accident, ["P82"]) is False
    assert _sse_payload_in_admin_scope(p80_call, ["P82"]) is False
    # non-accident traffic is never filtered
    assert _sse_payload_in_admin_scope(presence, ["P82"]) is True
    # perfil 9 (None = unrestricted) receives everything
    assert _sse_payload_in_admin_scope(p80_call, None) is True
    assert _sse_payload_in_admin_scope(p80_accident, None) is True
    # an admin of several projects
    assert _sse_payload_in_admin_scope(p80_accident, ["P80", "P82"]) is True


def test_sse_filter_is_fail_open_for_malformed_or_unlabelled_payloads():
    """Payloads without a project cannot leak project data on their own, and the
    endpoints they trigger a refetch of apply the scope server-side."""
    import json

    from sistema.app.routers.admin import _sse_payload_in_admin_scope

    assert _sse_payload_in_admin_scope("not json at all", ["P82"]) is True
    assert _sse_payload_in_admin_scope("[1,2,3]", ["P82"]) is True
    assert _sse_payload_in_admin_scope(
        json.dumps({"reason": "accident_user_report"}), ["P82"]
    ) is True
    assert _sse_payload_in_admin_scope(
        json.dumps({"reason": "accident_opened", "project_name": ""}), ["P82"]
    ) is True
