"""Regression tests for alembic revision 0061_add_accident_tables.

Guarantees:
    * `alembic upgrade head` creates the five accident-related tables.
    * The partial unique index `ix_accidents_single_active` is present and unique.
    * `alembic downgrade -1` removes all five tables.

The test runs against a temporary SQLite database. SQLite is the lowest
common denominator across the project's test matrix; it also supports
partial unique indexes via the `sqlite_where` Alembic option, which is what
the revision uses. Postgres-specific behaviour (TIMESTAMPTZ, partial index
guard with constant expression) is exercised in production by
`deploy/maintenance/run_app_rollout.sh --phase migrate`.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


# Tables touched by revision 0061, in the same order they appear in
# the SQL counterpart at sistema/scripts/migrate_accidents_v1.sql.
_ACCIDENT_TABLES = (
    "accidents",
    "accident_user_reports",
    "accident_video_uploads",
    "accident_archives",
    "email_delivery_logs",
)


@pytest.fixture
def temp_alembic_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Yields a fresh sqlite URL that alembic will use. alembic/env.py reads
    `settings.database_url` at import time, so we monkeypatch that attribute
    directly (the module-level Settings instance was already constructed by
    the shared test conftest). The env var override is kept as a belt-and-
    suspenders measure for any subprocess invocation.
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
    # alembic.ini uses `script_location = alembic`, resolved relative to the
    # ini file; pass an absolute path so the test is independent of cwd.
    cfg.set_main_option("script_location", str(repo_root / "alembic"))
    return cfg


def test_revision_0061_creates_and_drops_accident_tables(temp_alembic_db: str):
    cfg = _build_config(temp_alembic_db)
    command.upgrade(cfg, "head")

    engine = create_engine(temp_alembic_db)
    inspector = inspect(engine)

    table_names = set(inspector.get_table_names())
    for table in _ACCIDENT_TABLES:
        assert table in table_names, f"missing table after upgrade: {table}"

    # This upgrades to HEAD, not to 0061, so the uniqueness rule in place here is
    # the one revision 0075 left behind: one active accident PER PROJECT, indexed
    # on project_id. 0061's global ix_accidents_single_active is gone by then, and
    # asserting the old name left this test failing on main after 0075 shipped.
    indexes = {idx["name"]: idx for idx in inspector.get_indexes("accidents")}
    assert (
        "ix_accidents_single_active_per_project" in indexes
    ), "missing partial unique index ix_accidents_single_active_per_project on accidents.project_id"
    # SQLAlchemy returns the unique flag as int (1) for some dialects and
    # bool for others; coerce before comparing.
    assert bool(indexes["ix_accidents_single_active_per_project"]["unique"]) is True
    assert "ix_accidents_single_active" not in indexes, (
        "0075 must drop the old global unique index"
    )

    # Regression: the expression-based guard index from 0061 must be gone too.
    # SQLite does not reflect expression indexes, so get_indexes() cannot see it —
    # query sqlite_master directly.
    with engine.connect() as conn:
        leftover_guard = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master "
            "WHERE type='index' AND name='ix_accidents_single_active_guard'"
        ).fetchall()
    assert not leftover_guard, (
        "ix_accidents_single_active_guard survived the upgrade — a second accident "
        "in a different project would fail its unique constraint"
    )

    # Downgrade one revision must drop the same tables.
    command.downgrade(cfg, "0060_add_endpoint_api_keys")
    inspector_after = inspect(engine)
    for table in _ACCIDENT_TABLES:
        assert (
            table not in set(inspector_after.get_table_names())
        ), f"table still present after downgrade: {table}"
