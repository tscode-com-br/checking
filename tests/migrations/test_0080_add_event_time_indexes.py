"""Regression test for alembic revision 0080_add_event_time_indexes.

Guarantees:
    * `alembic upgrade head` cria ix_check_events_event_time e ix_user_sync_events_event_time
      (nomes iguais aos gerados por ``index=True`` em models.py, mantendo create_all e migration
      em sincronia).
    * `alembic downgrade -1` remove os dois indices.

Mesmo harness de test_0061: SQLite temporario, monkeypatch de settings.database_url.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

_EXPECTED_INDEXES = {
    "check_events": "ix_check_events_event_time",
    "user_sync_events": "ix_user_sync_events_event_time",
}


@pytest.fixture
def temp_alembic_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
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


def test_revision_0080_creates_and_drops_event_time_indexes(temp_alembic_db: str):
    cfg = _build_config(temp_alembic_db)
    command.upgrade(cfg, "head")

    engine = create_engine(temp_alembic_db)
    inspector = inspect(engine)
    for table, index_name in _EXPECTED_INDEXES.items():
        index_names = {idx["name"] for idx in inspector.get_indexes(table)}
        assert index_name in index_names, f"missing index after upgrade: {index_name} on {table}"

    command.downgrade(cfg, "0079_add_pending_user_registrations")
    inspector_after = inspect(engine)
    for table, index_name in _EXPECTED_INDEXES.items():
        index_names = {idx["name"] for idx in inspector_after.get_indexes(table)}
        assert index_name not in index_names, f"index still present after downgrade: {index_name}"
