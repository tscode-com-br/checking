"""HTTP-level regression tests for the admin Accident Mode endpoints.

These call the real FastAPI routes via TestClient (not the service layer
directly), so they cover the dependency wiring that the production bug
lived in. Specifically, they would have caught the foreign-key violation
where ``current_admin.id`` (a ``users.id``) was written to
``Accident.opened_by_admin_id`` (FK -> ``admin_users.id``).
"""
from __future__ import annotations

from unittest.mock import patch

import sqlalchemy as sa

from sistema.app.database import SessionLocal
from sistema.app.models import Accident, AccidentArchive, AccidentUserReport, AccidentVideoUpload, AdminUser

from tests.conftest_accident import AdminSession  # type: ignore[import-not-found]


def _wipe_accidents_and_admin_users(chave_to_wipe: str | None = None) -> None:
    """Clean slate: drop any open accidents and (optionally) the admin_users
    row for the given chave so we exercise the lazy-upsert path."""
    from datetime import datetime, timezone

    with SessionLocal() as db:
        now = datetime.now(timezone.utc)
        db.execute(
            sa.update(Accident)
            .where(Accident.closed_at.is_(None))
            .values(closed_at=now, updated_at=now)
        )
        db.execute(sa.delete(AccidentArchive))
        db.execute(sa.delete(AccidentVideoUpload))
        db.execute(sa.delete(AccidentUserReport))
        db.execute(sa.delete(Accident))
        if chave_to_wipe is not None:
            db.execute(sa.delete(AdminUser).where(AdminUser.chave == chave_to_wipe))
        db.commit()


def test_admin_open_accident_creates_admin_user_lazily(
    admin_perfil_1: AdminSession,
    accident_project,
    accident_location,
) -> None:
    """Hitting /api/admin/accidents/open as an admin whose admin_users row
    does not yet exist must succeed: the endpoint must lazily create the
    admin_users mirror and use ITS id for opened_by_admin_id."""
    _wipe_accidents_and_admin_users(chave_to_wipe=admin_perfil_1.user.chave)

    with patch(
        "sistema.app.services.accident_lifecycle.notify_admin_data_changed"
    ), patch(
        "sistema.app.services.accident_lifecycle.notify_web_check_data_changed"
    ):
        response = admin_perfil_1.client.post(
            "/api/admin/accidents/open",
            json={
                "project_id": accident_project.id,
                "location_id": accident_location.id,
            },
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_active"] is True
    assert body["accident"] is not None
    # Critical: opened_by_label must reflect the admin's name, not the
    # fallback "—" string that would appear if the FK pointed at a
    # nonexistent admin_users row.
    assert body["accident"]["opened_by_label"] == admin_perfil_1.user.nome

    with SessionLocal() as db:
        accident = db.execute(
            sa.select(Accident).where(Accident.closed_at.is_(None))
        ).scalar_one()
        # FK must reference a real admin_users row, NOT users.id.
        admin_row = db.get(AdminUser, accident.opened_by_admin_id)
        assert admin_row is not None, (
            "opened_by_admin_id must reference admin_users.id, "
            "not users.id"
        )
        assert admin_row.chave == admin_perfil_1.user.chave


def test_admin_close_accident_uses_admin_users_id(
    admin_perfil_1: AdminSession,
    accident_project,
    accident_location,
) -> None:
    """Closing an accident as admin must also use admin_users.id for
    closed_by_admin_id (same FK class as opened_by_admin_id)."""
    _wipe_accidents_and_admin_users(chave_to_wipe=admin_perfil_1.user.chave)

    with patch(
        "sistema.app.services.accident_lifecycle.notify_admin_data_changed"
    ), patch(
        "sistema.app.services.accident_lifecycle.notify_web_check_data_changed"
    ), patch(
        # The close endpoint schedules a background archive builder that
        # would otherwise try to hit S3. Stub it.
        "sistema.app.routers.admin.build_and_attach_archive_for_accident",
        return_value=None,
    ):
        open_response = admin_perfil_1.client.post(
            "/api/admin/accidents/open",
            json={
                "project_id": accident_project.id,
                "location_id": accident_location.id,
            },
        )
        assert open_response.status_code == 200, open_response.text

        close_response = admin_perfil_1.client.post("/api/admin/accidents/close")
        assert close_response.status_code == 200, close_response.text

    with SessionLocal() as db:
        accident = db.execute(
            sa.select(Accident).order_by(Accident.id.desc())
        ).scalars().first()
        assert accident is not None
        assert accident.closed_at is not None
        admin_row = db.get(AdminUser, accident.closed_by_admin_id)
        assert admin_row is not None, (
            "closed_by_admin_id must reference admin_users.id, "
            "not users.id"
        )
        assert admin_row.chave == admin_perfil_1.user.chave


def test_admin_session_endpoint_returns_identity_after_login(
    admin_perfil_1: AdminSession,
) -> None:
    """Regression: ``GET /api/admin/auth/session`` builds the public
    Pydantic ``AdminIdentity`` (from schemas) via ``build_admin_identity``.

    A previous version of the fix shadowed that symbol with the internal
    ``AdminActorIdentity`` dataclass, causing this endpoint to 500 in
    production with ``TypeError: AdminIdentity.__init__() got an
    unexpected keyword argument 'id'``. The /auth/login endpoint does
    NOT exercise this code path, which is why the failure escaped the
    other tests in this file.
    """
    response = admin_perfil_1.client.get("/api/admin/auth/session")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["authenticated"] is True
    assert body["admin"]["chave"] == admin_perfil_1.user.chave


def test_admin_open_accident_rejects_when_one_is_already_active(
    admin_perfil_1: AdminSession,
    accident_project,
    accident_location,
    open_accident_fixture,
) -> None:
    """Sanity check that the already-active guard still fires through the
    HTTP path (the fixture leaves an open accident in place)."""
    response = admin_perfil_1.client.post(
        "/api/admin/accidents/open",
        json={
            "project_id": accident_project.id,
            "location_id": accident_location.id,
        },
    )
    assert response.status_code == 409, response.text
