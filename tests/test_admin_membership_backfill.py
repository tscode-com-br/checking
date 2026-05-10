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
    previous_database_url = settings.database_url
    settings.database_url = database_url
    try:
        command.upgrade(config, revision)
    finally:
        settings.database_url = previous_database_url


def _insert_project(connection, name: str) -> None:
    connection.execute(
        sa.text(
            """
            INSERT INTO projects (
                name,
                country_code,
                country_name,
                timezone_name,
                address,
                zip_code
            )
            SELECT
                :name,
                'SG',
                'Singapura',
                'Asia/Singapore',
                '',
                ''
            WHERE NOT EXISTS (
                SELECT 1
                FROM projects
                WHERE name = :name
            )
            """
        ),
        {"name": name},
    )


def _insert_user(
    connection,
    *,
    chave: str,
    nome: str,
    projeto: str,
    perfil: int,
    admin_monitored_projects_json: str | None,
) -> None:
    timestamp = datetime(2026, 5, 7, 12, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    update_result = connection.execute(
        sa.text(
            """
            UPDATE users
            SET
                senha = NULL,
                perfil = :perfil,
                admin_monitored_projects_json = :admin_monitored_projects_json,
                nome = :nome,
                projeto = :projeto,
                workplace = NULL,
                vehicle_id = NULL,
                placa = NULL,
                end_rua = NULL,
                zip = NULL,
                cargo = NULL,
                email = NULL,
                local = NULL,
                checkin = NULL,
                time = NULL,
                last_active_at = :last_active_at,
                inactivity_days = 0
            WHERE chave = :chave
            """
        ),
        {
            "chave": chave,
            "perfil": perfil,
            "admin_monitored_projects_json": admin_monitored_projects_json,
            "nome": nome,
            "projeto": projeto,
            "last_active_at": timestamp,
        },
    )
    if update_result.rowcount:
        return

    connection.execute(
        sa.text(
            """
            INSERT INTO users (
                rfid,
                chave,
                senha,
                perfil,
                admin_monitored_projects_json,
                nome,
                projeto,
                workplace,
                vehicle_id,
                placa,
                end_rua,
                zip,
                cargo,
                email,
                local,
                checkin,
                time,
                last_active_at,
                inactivity_days
            ) VALUES (
                NULL,
                :chave,
                NULL,
                :perfil,
                :admin_monitored_projects_json,
                :nome,
                :projeto,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                :last_active_at,
                0
            )
            """
        ),
        {
            "chave": chave,
            "perfil": perfil,
            "admin_monitored_projects_json": admin_monitored_projects_json,
            "nome": nome,
            "projeto": projeto,
            "last_active_at": timestamp,
        },
    )


def test_user_project_membership_migration_backfills_admin_scope_conservatively(tmp_path):
    database_url = _build_database_url(tmp_path / "admin_membership_backfill.db")

    _upgrade_database("0053_add_transport_ai_project_llm_settings", database_url)

    engine = sa.create_engine(database_url)
    with engine.begin() as connection:
        _insert_project(connection, "P80")
        _insert_project(connection, "P82")
        _insert_project(connection, "P83")
        _insert_user(
            connection,
            chave="USR1",
            nome="Usuario Basico",
            projeto="P83",
            perfil=0,
            admin_monitored_projects_json=None,
        )
        _insert_user(
            connection,
            chave="ADM1",
            nome="Admin Restrito",
            projeto="P83",
            perfil=1,
            admin_monitored_projects_json='["P80"]',
        )
        _insert_user(
            connection,
            chave="ADM2",
            nome="Admin Global",
            projeto="P82",
            perfil=1,
            admin_monitored_projects_json=None,
        )
        _insert_user(
            connection,
            chave="ADM3",
            nome="Admin Json Invalido",
            projeto="P80",
            perfil=1,
            admin_monitored_projects_json='{invalid-json',
        )
        _insert_user(
            connection,
            chave="ADM4",
            nome="Admin Global ALL",
            projeto="P83",
            perfil=1,
            admin_monitored_projects_json='["ALL"]',
        )
        _insert_user(
            connection,
            chave="HR70",
            nome="Bootstrap Admin",
            projeto="P80",
            perfil=9,
            admin_monitored_projects_json='["P83"]',
        )

    _upgrade_database("head", database_url)

    with engine.connect() as connection:
        project_names = connection.execute(
            sa.text("SELECT name FROM projects ORDER BY name")
        ).scalars().all()
        membership_rows = connection.execute(
            sa.text(
                """
                SELECT users.chave AS chave, projects.name AS project_name
                FROM user_project_memberships
                JOIN users ON users.id = user_project_memberships.user_id
                JOIN projects ON projects.id = user_project_memberships.project_id
                ORDER BY users.chave, projects.name
                """
            )
        ).mappings().all()

    engine.dispose()

    memberships_by_key: dict[str, list[str]] = {}
    for row in membership_rows:
        memberships_by_key.setdefault(str(row["chave"]), []).append(str(row["project_name"]))

    assert memberships_by_key["USR1"] == ["P83"]
    assert memberships_by_key["ADM1"] == ["P80", "P83"]
    assert memberships_by_key["ADM2"] == ["P80", "P82", "P83"]
    assert memberships_by_key["ADM3"] == ["P80", "P82", "P83"]
    assert memberships_by_key["ADM4"] == ["P80", "P82", "P83"]
    assert memberships_by_key["HR70"] == ["P80", "P82", "P83"]
    assert "ALL" not in set(project_names)
    assert all(memberships_by_key[key] for key in ("ADM1", "ADM2", "ADM3", "ADM4", "HR70"))


def test_user_project_membership_migration_creates_missing_catalog_projects_for_legacy_users(tmp_path):
    database_url = _build_database_url(tmp_path / "admin_membership_missing_project.db")

    _upgrade_database("0053_add_transport_ai_project_llm_settings", database_url)

    engine = sa.create_engine(database_url)
    with engine.begin() as connection:
        _insert_project(connection, "P80")
        _insert_user(
            connection,
            chave="USR2",
            nome="Usuario Projeto Ausente",
            projeto="P99",
            perfil=0,
            admin_monitored_projects_json=None,
        )

    _upgrade_database("head", database_url)

    with engine.connect() as connection:
        project_names = connection.execute(
            sa.text("SELECT name FROM projects ORDER BY name")
        ).scalars().all()
        membership_rows = connection.execute(
            sa.text(
                """
                SELECT users.chave AS chave, projects.name AS project_name
                FROM user_project_memberships
                JOIN users ON users.id = user_project_memberships.user_id
                JOIN projects ON projects.id = user_project_memberships.project_id
                WHERE users.chave = 'USR2'
                """
            )
        ).mappings().all()

    engine.dispose()

    assert "P99" in set(project_names)
    assert membership_rows == [{"chave": "USR2", "project_name": "P99"}]
