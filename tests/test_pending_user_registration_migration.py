"""Verifies migration 0079 creates (and cleanly drops) pending_user_registrations.

plan003 EP1 — the table backs the new-user approval queue. The migration is
additive and reversible; the real ``User`` is created only on approval, so this
table is fully independent of ``users``. This test exercises the whole chain on
a fresh SQLite (upgrade to 0079, then downgrade back to 0078).
"""
from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sistema.app.core.config import settings

TABLE = "pending_user_registrations"


def _build_database_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path.as_posix()}"


def _run(database_url: str, revision: str, *, downgrade: bool = False) -> None:
    config = Config("alembic.ini")
    previous = settings.database_url
    settings.database_url = database_url
    try:
        if downgrade:
            command.downgrade(config, revision)
        else:
            command.upgrade(config, revision)
    finally:
        settings.database_url = previous


def test_migration_creates_and_drops_pending_user_registrations(tmp_path) -> None:
    database_url = _build_database_url(tmp_path / "pending_user_reg.db")

    # Upgrade the whole chain up to and including 0079.
    _run(database_url, "0079_add_pending_user_registrations")

    engine = sa.create_engine(database_url)
    try:
        inspector = sa.inspect(engine)
        assert TABLE in inspector.get_table_names()

        cols = {c["name"] for c in inspector.get_columns(TABLE)}
        assert {
            "id", "chave", "nome_completo", "projetos_json",
            "email", "password_hash", "client", "requested_at",
        } <= cols

        # `chave` is unique (as a table constraint or a unique index).
        unique_sets = {tuple(u["column_names"]) for u in inspector.get_unique_constraints(TABLE)}
        unique_sets |= {
            tuple(ix["column_names"]) for ix in inspector.get_indexes(TABLE) if ix.get("unique")
        }
        assert ("chave",) in unique_sets

        # `requested_at` is indexed (for newest-first ordering).
        index_sets = {tuple(ix["column_names"]) for ix in inspector.get_indexes(TABLE)}
        assert ("requested_at",) in index_sets
    finally:
        engine.dispose()

    # Downgrade one step (0079 -> 0078) drops the table cleanly.
    _run(database_url, "0078_add_local_to_checkinghistory", downgrade=True)

    engine = sa.create_engine(database_url)
    try:
        assert TABLE not in sa.inspect(engine).get_table_names()
    finally:
        engine.dispose()
