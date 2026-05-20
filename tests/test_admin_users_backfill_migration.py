"""Verifies migration 0062 backfills admin_users for admin-capable users.

The migration is the safety net for hosts that were deployed before the
lazy upsert (``ensure_admin_user_by_chave``) covered every admin code
path. Without this migration, a host that never exercised the
transport-AI flow would have an empty ``admin_users`` table even for
users whose perfil grants admin access — and the Postgres FK would
reject any attempt to write ``opened_by_admin_id`` etc.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from sistema.app.core.config import settings


def _build_database_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path.as_posix()}"


def _upgrade_database(revision: str, database_url: str) -> None:
    config = Config("alembic.ini")
    previous = settings.database_url
    settings.database_url = database_url
    try:
        command.upgrade(config, revision)
    finally:
        settings.database_url = previous


def _insert_user(connection, *, chave: str, nome: str, perfil: int) -> None:
    timestamp = datetime(2026, 5, 20, 12, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    connection.execute(
        sa.text(
            """
            INSERT INTO users (
                rfid, chave, senha, perfil, nome, projeto,
                last_active_at, inactivity_days
            ) VALUES (
                NULL, :chave, NULL, :perfil, :nome, 'P-Test', :last_active_at, 0
            )
            """
        ),
        {"chave": chave, "perfil": perfil, "nome": nome, "last_active_at": timestamp},
    )


def _insert_admin_user(connection, *, chave: str, nome_completo: str) -> None:
    timestamp = datetime(2026, 5, 1, 12, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    connection.execute(
        sa.text(
            """
            INSERT INTO admin_users (
                chave, nome_completo, password_hash, requires_password_reset,
                created_at, updated_at
            ) VALUES (
                :chave, :nome_completo, NULL, 0, :ts, :ts
            )
            """
        ),
        {"chave": chave, "nome_completo": nome_completo, "ts": timestamp},
    )


def _admin_chaves(connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(sa.text("SELECT chave FROM admin_users")).fetchall()
    }


def test_migration_creates_admin_users_for_admin_capable_users(tmp_path) -> None:
    database_url = _build_database_url(tmp_path / "admin_users_backfill.db")

    # Stop at the revision JUST BEFORE 0062.
    _upgrade_database("0061_add_accident_tables", database_url)

    engine = sa.create_engine(database_url)
    with engine.begin() as connection:
        # Cast of test users: one non-admin, one perfil=1 (admin), one
        # perfil=9 (super-admin), one perfil=21 (transport+admin), and one
        # whose admin_users row already exists.
        _insert_user(connection, chave="REG1", nome="Regular User", perfil=0)
        _insert_user(connection, chave="AD01", nome="Plain Admin", perfil=1)
        _insert_user(connection, chave="SU09", nome="Super Admin", perfil=9)
        _insert_user(connection, chave="MX21", nome="Transport+Admin", perfil=21)
        _insert_user(connection, chave="EXST", nome="Existing Admin", perfil=1)
        _insert_admin_user(connection, chave="EXST", nome_completo="Existing Admin")

    # Now run the new migration.
    _upgrade_database("0062_backfill_admin_users_for_existing_admins", database_url)

    with engine.begin() as connection:
        chaves = _admin_chaves(connection)
        # Admin-capable users get a row.
        assert "AD01" in chaves
        assert "SU09" in chaves
        assert "MX21" in chaves
        # Non-admin users do NOT get a row.
        assert "REG1" not in chaves
        # Pre-existing row is preserved (not duplicated).
        assert "EXST" in chaves
        count = connection.execute(
            sa.text("SELECT COUNT(*) FROM admin_users WHERE chave = 'EXST'")
        ).scalar_one()
        assert count == 1


