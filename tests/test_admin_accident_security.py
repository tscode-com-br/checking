"""HTTP-level tests for the access controls on the admin Accident endpoints.

Two classes of hole, both reachable in production:

  * GET /api/admin/accidents/local-asset/{path} had no session dependency and
    concatenated the client-supplied path straight onto the storage root. Its
    "dev only" 404 is gated on DO Spaces being configured, and a deployment
    without those credentials served accident videos to anonymous callers.
  * No accident endpoint applied the project scope every other admin area
    applies, so a perfil-1 admin could read and act on another project's accident.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import sqlalchemy as sa
from fastapi.testclient import TestClient

from sistema.app.database import SessionLocal
from sistema.app.main import app
from sistema.app.models import (
    Accident,
    AccidentArchive,
    AccidentCallLog,
    AccidentCallNotification,
    AccidentUserReport,
    AccidentVideoUpload,
    Project,
)

from tests.conftest_accident import AdminSession  # type: ignore[import-not-found]

_LIFECYCLE_PATCHES = (
    "sistema.app.services.accident_lifecycle.notify_admin_data_changed",
    "sistema.app.services.accident_lifecycle.notify_web_check_data_changed",
)


def _wipe_accidents() -> None:
    # The test database is shared across the suite, so clear the call trail too:
    # accident_call_logs.call_number is globally unique and a leftover row from an
    # earlier run collides with the one these tests insert.
    with SessionLocal() as db:
        db.execute(sa.delete(AccidentCallNotification))
        db.execute(sa.delete(AccidentCallLog))
        db.execute(sa.delete(AccidentArchive))
        db.execute(sa.delete(AccidentVideoUpload))
        db.execute(sa.delete(AccidentUserReport))
        db.execute(sa.delete(Accident))
        db.commit()


# ---------------------------------------------------------------------------
# local-asset
# ---------------------------------------------------------------------------


def test_local_asset_requires_an_admin_session() -> None:
    anonymous = TestClient(app, raise_server_exceptions=False)
    response = anonymous.get("/api/admin/accidents/local-asset/videos/anything.mp4")
    assert response.status_code in (401, 403), response.text


def test_local_asset_does_not_escape_the_storage_root() -> None:
    """A traversal path must 404 — the same 404 as a missing file.

    Calls the endpoint function directly on purpose: httpx collapses `../` in the
    URL before the request is sent, so an HTTP-level attempt never reaches the
    handler with a traversal path and would prove nothing. What is under test is
    the confinement inside serve_local_asset, which is what a client speaking raw
    HTTP (or any proxy that forwards the path untouched) would hit.
    """
    import pytest
    from fastapi import HTTPException

    from sistema.app.routers.admin import serve_local_asset
    from sistema.app.services.object_storage import _local_root, _use_remote

    if _use_remote():
        with pytest.raises(HTTPException) as exc:
            serve_local_asset("videos/x.mp4")
        assert exc.value.status_code == 404
        return

    root = _local_root().resolve()
    secret = root.parent / "outside_root_secret.txt"
    secret.write_text("must-not-be-served", encoding="utf-8")
    try:
        for attempt in (
            f"../{secret.name}",
            f"../../{secret.name}",
            f"videos/../../{secret.name}",
        ):
            with pytest.raises(HTTPException) as exc:
                serve_local_asset(attempt)
            assert exc.value.status_code == 404, attempt
    finally:
        secret.unlink(missing_ok=True)


def test_local_asset_serves_a_file_inside_the_root(
    admin_perfil_9: AdminSession,
) -> None:
    from sistema.app.services.object_storage import _local_root, _use_remote

    if _use_remote():
        return
    root = _local_root().resolve()
    target = root / "regression" / "ok.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("served", encoding="utf-8")
    try:
        response = admin_perfil_9.client.get(
            "/api/admin/accidents/local-asset/regression/ok.txt"
        )
        assert response.status_code == 200, response.text
        assert response.text == "served"
    finally:
        target.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# project scope
# ---------------------------------------------------------------------------


def _create_foreign_project_accident() -> tuple[int, int]:
    """Open an accident on a project the fixture admins do NOT belong to."""
    from sistema.app.services.accident_lifecycle import open_accident
    from sistema.app.services.admin_identity import ensure_admin_user_by_chave

    with SessionLocal() as db:
        proj = db.execute(
            sa.select(Project).where(Project.name == "PFOR")
        ).scalar_one_or_none()
        if proj is None:
            proj = Project(
                name="PFOR",
                country_code="SG",
                country_name="Singapore",
                timezone_name="Asia/Singapore",
                address="9 Foreign Road",
                zip_code="000099",
            )
            db.add(proj)
            db.commit()
            db.refresh(proj)
        actor = ensure_admin_user_by_chave(
            db, chave="ZZ99", nome_completo="Foreign Admin"
        )
        db.commit()

        with patch(_LIFECYCLE_PATCHES[0]), patch(_LIFECYCLE_PATCHES[1]):
            accident = open_accident(
                db,
                origin="admin",
                project_id=proj.id,
                custom_location_name="Portaria Externa",
                opened_by_admin_id=actor.id,
            )
        return accident.id, proj.id


def test_perfil_1_admin_does_not_see_another_projects_accident(
    admin_perfil_1: AdminSession,
    accident_project,
) -> None:
    _wipe_accidents()
    _create_foreign_project_accident()

    response = admin_perfil_1.client.get("/api/admin/accidents/active")
    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False, (
        "an accident from a project outside the admin's scope must not appear"
    )


def _strip_all_memberships(chave: str) -> None:
    """Leave the admin enrolled in NO project at all."""
    from sistema.app.models import User, UserProjectMembership

    with SessionLocal() as db:
        user = db.execute(sa.select(User).where(User.chave == chave)).scalar_one()
        db.execute(
            sa.delete(UserProjectMembership).where(UserProjectMembership.user_id == user.id)
        )
        db.commit()
        remaining = db.execute(
            sa.select(sa.func.count())
            .select_from(UserProjectMembership)
            .where(UserProjectMembership.user_id == user.id)
        ).scalar_one()
    assert remaining == 0, "precondition: the perfil-9 admin must have no memberships"


def test_perfil_9_admin_sees_every_projects_accident(
    admin_perfil_9: AdminSession,
) -> None:
    _wipe_accidents()
    _create_foreign_project_accident()

    response = admin_perfil_9.client.get("/api/admin/accidents/active")
    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is True, (
        "perfil 9 is unrestricted and must still see every active accident"
    )


def test_perfil_9_with_no_project_at_all_still_has_full_access(
    admin_perfil_9: AdminSession,
) -> None:
    """Project enrolment is irrelevant to a perfil-9 admin.

    For them, being registered in a project only matters for their own check-in /
    check-out. Every accident access must be granted regardless — including when
    they belong to no project whatsoever, which is where a membership-driven scope
    would otherwise deny everything (an empty project set matches nothing).
    """
    _wipe_accidents()
    accident_id, _ = _create_foreign_project_accident()
    _strip_all_memberships(admin_perfil_9.user.chave)

    state = admin_perfil_9.client.get("/api/admin/accidents/active")
    assert state.status_code == 200, state.text
    assert state.json()["is_active"] is True, "must still see the active accident"

    call_logs = admin_perfil_9.client.get(
        f"/api/admin/accidents/{accident_id}/call-logs"
    )
    assert call_logs.status_code == 200, call_logs.text

    notifications = admin_perfil_9.client.get(
        f"/api/admin/accidents/{accident_id}/notifications"
    )
    assert notifications.status_code == 200, notifications.text

    wizard = admin_perfil_9.client.get("/api/admin/accidents/wizard/projects")
    assert wizard.status_code == 200, wizard.text
    assert wizard.json(), "every project must remain selectable for perfil 9"

    with patch(_LIFECYCLE_PATCHES[0]), patch(_LIFECYCLE_PATCHES[1]), patch(
        "sistema.app.routers.admin.build_and_attach_archive_for_accident"
    ):
        closed = admin_perfil_9.client.post(
            f"/api/admin/accidents/{accident_id}/close"
        )
    assert closed.status_code == 200, closed.text

    listing = admin_perfil_9.client.get("/api/admin/accidents")
    assert listing.status_code == 200, listing.text
    rows = listing.json()["rows"]
    assert any(row["id"] == accident_id for row in rows), (
        "the closed accident must be listed for perfil 9"
    )
    assert all(row["can_delete"] for row in rows), (
        "perfil 9 keeps the delete permission with no memberships"
    )

    deleted = admin_perfil_9.client.delete(f"/api/admin/accidents/{accident_id}")
    assert deleted.status_code == 200, deleted.text


def test_sse_scope_is_unrestricted_for_perfil_9() -> None:
    """resolve_effective_admin_project_names returns None for a perfil-9 admin
    before it ever looks at memberships, so the SSE filter lets everything through."""
    from sistema.app.models import User
    from sistema.app.services.admin_project_scope import (
        resolve_effective_admin_project_names,
    )
    from sistema.app.routers.admin import _sse_payload_in_admin_scope

    with SessionLocal() as db:
        admin = db.execute(sa.select(User).where(User.perfil == 9)).scalars().first()
        assert admin is not None, "expected a perfil-9 admin in the test database"
        allowed = resolve_effective_admin_project_names(db, admin)

    assert allowed is None, "perfil 9 must resolve to the unrestricted scope"
    payload = '{"reason": "emergency_call_initiated", "project_name": "QUALQUER"}'
    assert _sse_payload_in_admin_scope(payload, allowed) is True


def test_perfil_1_admin_cannot_close_another_projects_accident(
    admin_perfil_1: AdminSession,
    accident_project,
) -> None:
    _wipe_accidents()
    accident_id, _ = _create_foreign_project_accident()

    response = admin_perfil_1.client.post(f"/api/admin/accidents/{accident_id}/close")
    assert response.status_code == 404, response.text

    with SessionLocal() as db:
        still_open = db.get(Accident, accident_id)
        assert still_open is not None and still_open.closed_at is None, (
            "the out-of-scope accident must remain untouched"
        )


def test_perfil_1_admin_cannot_read_another_projects_call_logs(
    admin_perfil_1: AdminSession,
    accident_project,
) -> None:
    _wipe_accidents()
    accident_id, _ = _create_foreign_project_accident()

    response = admin_perfil_1.client.get(
        f"/api/admin/accidents/{accident_id}/call-logs"
    )
    assert response.status_code == 404, response.text


def test_wizard_projects_only_lists_projects_in_scope(
    admin_perfil_1: AdminSession,
    accident_project,
) -> None:
    _wipe_accidents()
    _create_foreign_project_accident()

    response = admin_perfil_1.client.get("/api/admin/accidents/wizard/projects")
    assert response.status_code == 200, response.text
    names = {row["name"] for row in response.json()}
    assert accident_project.name in names
    assert "PFOR" not in names, (
        "offering a project the admin cannot open an accident for would make the "
        "wizard fail with 404 at the last step"
    )


def test_call_logs_label_does_not_500_for_user_triggered_calls(
    admin_perfil_9: AdminSession,
) -> None:
    """_build_triggered_by_label read User.nome_completo, which does not exist."""
    from sistema.app.models import User

    _wipe_accidents()
    accident_id, project_id = _create_foreign_project_accident()

    with SessionLocal() as db:
        user = db.execute(sa.select(User).limit(1)).scalars().first()
        assert user is not None
        now = datetime.now(timezone.utc)
        db.add(AccidentCallLog(
            call_number=987654,
            call_sid="CAtest",
            accident_id=accident_id,
            project_id=project_id,
            triggered_by_user_id=user.id,
            to_phone="+6580000000",
            from_phone="+6580000001",
            call_status="queued",
            message_twiml="<Response/>",
            created_at=now,
            updated_at=now,
        ))
        db.commit()
        expected_name = user.nome
        expected_chave = user.chave

    response = admin_perfil_9.client.get(
        f"/api/admin/accidents/{accident_id}/call-logs"
    )
    assert response.status_code == 200, response.text
    rows = response.json()
    assert rows, "the call log row should be returned"
    assert rows[0]["triggered_by_label"] == f"{expected_name} ({expected_chave})"
