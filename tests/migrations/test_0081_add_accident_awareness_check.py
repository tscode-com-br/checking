"""Revision 0081 — the CHECK on accident_user_reports.awareness_status.

0074 added the column but not the constraint models.py declares, so migrated
databases (production included) accepted any string there.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


@pytest.fixture
def temp_alembic_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Fresh sqlite URL for alembic.

    alembic/env.py reads settings.database_url at import time, so setting only
    Config's sqlalchemy.url would silently run the migrations against the shared
    test database. Patch the settings attribute, exactly as
    test_0061_add_accident_tables does.
    """
    db_path = tmp_path / "alembic_test.db"
    db_url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    from sistema.app.core import config as core_config

    monkeypatch.setattr(core_config.settings, "database_url", db_url)
    return db_url


def _build_config(db_url: str) -> Config:
    repo_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(repo_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.set_main_option("script_location", str(repo_root / "alembic"))
    return cfg


def _check_names(engine) -> set[str]:
    return {
        c.get("name")
        for c in inspect(engine).get_check_constraints("accident_user_reports")
    }


def test_revision_0081_adds_and_drops_awareness_check(temp_alembic_db: str):
    cfg = _build_config(temp_alembic_db)
    command.upgrade(cfg, "head")

    engine = create_engine(temp_alembic_db)
    assert "ck_accident_user_reports_awareness_allowed" in _check_names(engine), (
        "0081 should add the awareness_status CHECK"
    )
    # The two constraints inherited from 0061 must survive the SQLite table rebuild.
    names = _check_names(engine)
    assert "ck_accident_user_reports_zone_allowed" in names
    assert "ck_accident_user_reports_status_allowed" in names

    command.downgrade(cfg, "0080_add_event_time_indexes")
    assert "ck_accident_user_reports_awareness_allowed" not in _check_names(
        create_engine(temp_alembic_db)
    )


def test_awareness_check_rejects_unknown_value(temp_alembic_db: str):
    cfg = _build_config(temp_alembic_db)
    command.upgrade(cfg, "head")

    engine = create_engine(temp_alembic_db)
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        insert = (
            "INSERT INTO accident_user_reports ("
            "accident_id, user_id, user_chave_snapshot, user_name_snapshot, "
            "user_projects_snapshot, user_local_snapshot, zone, status, "
            "awareness_status, created_at, updated_at) "
            "VALUES (1, 1, 'AAAA', 'N', '[]', 'L', 'waiting', 'waiting', "
            "'{value}', '2026-01-01', '2026-01-01')"
        )
        with pytest.raises(sa.exc.IntegrityError):
            conn.exec_driver_sql(insert.format(value="bogus"))
        conn.rollback()
        # A permitted value still goes in.
        conn.exec_driver_sql(insert.format(value="acknowledged"))
        conn.commit()
