"""open_accident / attach_video_upload error paths.

Each of these used to reach the routers as an unmapped exception and answer 500.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import (
    Accident,
    AccidentVideoUpload,
    AdminUser,
    ManagedLocation,
    Project,
    User,
)
from sistema.app.services.accident_lifecycle import (
    AccidentAlreadyActiveError,
    AccidentProjectNotFoundError,
    InvalidAccidentLocationError,
    VideoIdempotencyConflictError,
    attach_video_upload,
    find_video_upload,
    open_accident,
)

_NOW = datetime(2026, 1, 1, 8, 0, 0)


def _make_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / 'lifecycle.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    return factory()


def _make_project(db: Session, name: str = "PROJ") -> Project:
    proj = Project(
        name=name,
        country_code="SG",
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address="1 St",
        zip_code="123456",
    )
    db.add(proj)
    db.commit()
    return proj


def _make_admin(db: Session) -> AdminUser:
    admin = AdminUser(chave="A001", nome_completo="Admin", created_at=_NOW, updated_at=_NOW)
    db.add(admin)
    db.commit()
    return admin


def _make_user(db: Session, chave: str) -> User:
    user = User(
        chave=chave,
        nome=f"User {chave}",
        projeto="PROJ",
        checkin=False,
        local="Sala 1",
        last_active_at=_NOW,
        inactivity_days=0,
    )
    db.add(user)
    db.commit()
    return user


# ---------------------------------------------------------------------------
# open_accident
# ---------------------------------------------------------------------------


def test_unknown_project_raises_typed_error(tmp_path: Path):
    db = _make_session(tmp_path)
    admin = _make_admin(db)

    with pytest.raises(AccidentProjectNotFoundError):
        open_accident(
            db,
            origin="admin",
            project_id=999_999,
            custom_location_name="Portaria",
            opened_by_admin_id=admin.id,
        )


def test_blank_custom_location_raises_location_error(tmp_path: Path):
    """Used to be a bare ValueError, which neither router caught."""
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)

    with pytest.raises(InvalidAccidentLocationError):
        open_accident(
            db,
            origin="admin",
            project_id=proj.id,
            custom_location_name="   ",
            opened_by_admin_id=admin.id,
        )


def test_unknown_location_raises_location_error(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)

    with pytest.raises(InvalidAccidentLocationError):
        open_accident(
            db,
            origin="admin",
            project_id=proj.id,
            location_id=424_242,
            opened_by_admin_id=admin.id,
        )


def test_location_outside_project_raises_location_error(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    loc = ManagedLocation(
        local="Outro Local",
        latitude=1.0,
        longitude=2.0,
        projects_json=json.dumps(["OUTRO"]),
        tolerance_meters=50,
        created_at=_NOW,
        updated_at=_NOW,
    )
    db.add(loc)
    db.commit()

    with pytest.raises(InvalidAccidentLocationError):
        open_accident(
            db,
            origin="admin",
            project_id=proj.id,
            location_id=loc.id,
            opened_by_admin_id=admin.id,
        )


def test_second_accident_same_project_is_already_active(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)

    open_accident(
        db,
        origin="admin",
        project_id=proj.id,
        custom_location_name="Portaria",
        opened_by_admin_id=admin.id,
    )
    with pytest.raises(AccidentAlreadyActiveError):
        open_accident(
            db,
            origin="admin",
            project_id=proj.id,
            custom_location_name="Portaria",
            opened_by_admin_id=admin.id,
        )


def test_two_projects_can_hold_an_accident_each(tmp_path: Path):
    """Uniqueness is per project since revision 0075."""
    db = _make_session(tmp_path)
    proj_a = _make_project(db, "PRJA")
    proj_b = _make_project(db, "PRJB")
    admin = _make_admin(db)

    a = open_accident(
        db, origin="admin", project_id=proj_a.id,
        custom_location_name="A", opened_by_admin_id=admin.id,
    )
    b = open_accident(
        db, origin="admin", project_id=proj_b.id,
        custom_location_name="B", opened_by_admin_id=admin.id,
    )
    assert a.id != b.id
    assert a.accident_number != b.accident_number
    actives = db.execute(
        sa.select(Accident).where(Accident.closed_at.is_(None))
    ).scalars().all()
    assert len(actives) == 2


# ---------------------------------------------------------------------------
# video idempotency
# ---------------------------------------------------------------------------


def _open(db: Session, proj: Project, admin: AdminUser) -> Accident:
    return open_accident(
        db, origin="admin", project_id=proj.id,
        custom_location_name="Portaria", opened_by_admin_id=admin.id,
    )


def test_same_user_same_key_is_idempotent(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _open(db, proj, admin)
    user = _make_user(db, "V001")

    first = attach_video_upload(
        db, accident=accident, user=user, object_key="k1", public_url="/u/1",
        content_type="video/mp4", size_bytes=10, duration_seconds=1,
        idempotency_key="dup-key",
    )
    second = attach_video_upload(
        db, accident=accident, user=user, object_key="k2", public_url="/u/2",
        content_type="video/mp4", size_bytes=20, duration_seconds=2,
        idempotency_key="dup-key",
    )
    assert first.id == second.id
    assert db.query(AccidentVideoUpload).count() == 1


def test_key_owned_by_another_user_is_rejected(tmp_path: Path):
    """idempotency_key is globally unique, so a collision used to hand the second
    user the first user's row — and its public_url."""
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _open(db, proj, admin)
    owner = _make_user(db, "V002")
    intruder = _make_user(db, "V003")

    attach_video_upload(
        db, accident=accident, user=owner, object_key="k1", public_url="/u/owner",
        content_type="video/mp4", size_bytes=10, duration_seconds=1,
        idempotency_key="shared-key",
    )

    with pytest.raises(VideoIdempotencyConflictError):
        attach_video_upload(
            db, accident=accident, user=intruder, object_key="k2", public_url="/u/intruder",
            content_type="video/mp4", size_bytes=10, duration_seconds=1,
            idempotency_key="shared-key",
        )
    with pytest.raises(VideoIdempotencyConflictError):
        find_video_upload(
            db, idempotency_key="shared-key", accident=accident, user=intruder
        )


def test_find_video_upload_returns_none_for_unused_key(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _open(db, proj, admin)
    user = _make_user(db, "V004")

    assert find_video_upload(
        db, idempotency_key="never-seen", accident=accident, user=user
    ) is None
