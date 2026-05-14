"""Tests for Task C1 — accident_numbering service."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import Accident, AdminUser, Project
from sistema.app.services.accident_numbering import (
    format_accident_number,
    next_accident_number,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session(tmp_path: Path, name: str = "test.db") -> tuple[Session, sa.Engine]:
    engine = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / name).as_posix()}")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    return factory(), engine


def _create_project(db: Session) -> Project:
    proj = Project(
        name="PROJ",
        country_code="SG",
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address="1 St",
        zip_code="123456",
    )
    db.add(proj)
    db.flush()
    return proj


def _create_admin(db: Session) -> AdminUser:
    now = datetime.now(timezone.utc)
    admin = AdminUser(
        chave="A001",
        nome_completo="Admin Test",
        created_at=now,
        updated_at=now,
    )
    db.add(admin)
    db.flush()
    return admin


def _insert_accident(db: Session, number: int, project: Project, admin: AdminUser) -> Accident:
    now = datetime.now(timezone.utc)
    acc = Accident(
        accident_number=number,
        project_id=project.id,
        project_name_snapshot=project.name,
        location_name_snapshot="Loc",
        location_is_registered=False,
        origin="admin",
        opened_by_admin_id=admin.id,
        opened_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(acc)
    db.flush()
    return acc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_next_accident_number_starts_at_zero(tmp_path: Path):
    db, _ = _make_session(tmp_path)
    assert next_accident_number(db) == 0


def test_next_accident_number_increments(tmp_path: Path):
    db, _ = _make_session(tmp_path)
    proj = _create_project(db)
    admin = _create_admin(db)
    _insert_accident(db, 42, proj, admin)
    assert next_accident_number(db) == 43


def test_format_accident_number_pads_to_4_digits():
    assert format_accident_number(0) == "0000"
    assert format_accident_number(42) == "0042"
    assert format_accident_number(9999) == "9999"
    assert format_accident_number(1) == "0001"


def test_format_accident_number_handles_large_values():
    assert format_accident_number(10000) == "10000"
    assert format_accident_number(99999) == "99999"
