"""Regression test for the 2026-07-07 admin-panel-500-on-refresh incident.

Root cause: orphan users (projeto=None, created by inactivity de-registration — production had 550)
are inactive and were in a full-scope admin's set, so build_inactive_rows built
InactiveUserRow(projeto=None); InactiveUserRow.projeto is a required str → pydantic ValidationError →
HTTP 500 on GET /api/admin/inactive → the admin SPA fell back to the login screen on every refresh.

Fix: build_inactive_rows skips users with projeto=None (already off the active roster; managed via the
Cadastro tab). These tests lock that behavior and that the endpoint no longer raises.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import Project, User
from sistema.app.routers.admin import build_inactive_rows


def _make_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(
        f"sqlite+pysqlite:///{(tmp_path / 'test_inactive_orphans.db').as_posix()}"
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    return factory()


def _add_user(db: Session, *, chave: str, nome: str, projeto: str | None, activity_time: datetime) -> None:
    db.add(
        User(
            chave=chave,
            nome=nome,
            projeto=projeto,
            checkin=True,
            time=activity_time,
            last_active_at=activity_time,
            inactivity_days=0,
        )
    )


def test_build_inactive_rows_excludes_orphans_without_raising(tmp_path: Path):
    db = _make_session(tmp_path)
    db.add(
        Project(name="P80", country_code="BR", country_name="Brazil", timezone_name="America/Sao_Paulo")
    )
    reference = datetime(2026, 7, 7, tzinfo=timezone.utc)
    long_ago = reference - timedelta(days=200)  # well past any inactivity window
    _add_user(db, chave="NRM1", nome="Registered Inactive", projeto="P80", activity_time=long_ago)
    _add_user(db, chave="ORP1", nome="Orphan Inactive", projeto=None, activity_time=long_ago)
    db.commit()

    # Before the fix this raised pydantic ValidationError (projeto=None) → HTTP 500.
    rows = build_inactive_rows(db, reference_time=reference)

    chaves = {row.chave for row in rows}
    assert "NRM1" in chaves, "a still-registered inactive user must remain in the Inatividade list"
    assert "ORP1" not in chaves, "orphan users (projeto=None) must be excluded from the Inatividade list"
    assert all(row.projeto is not None for row in rows)


def test_build_inactive_rows_all_orphans_returns_empty(tmp_path: Path):
    db = _make_session(tmp_path)
    reference = datetime(2026, 7, 7, tzinfo=timezone.utc)
    long_ago = reference - timedelta(days=200)
    _add_user(db, chave="ORP1", nome="Orphan A", projeto=None, activity_time=long_ago)
    _add_user(db, chave="ORP2", nome="Orphan B", projeto=None, activity_time=long_ago)
    db.commit()

    # A scope consisting only of orphans must yield an empty list, never a 500.
    assert build_inactive_rows(db, reference_time=reference) == []
