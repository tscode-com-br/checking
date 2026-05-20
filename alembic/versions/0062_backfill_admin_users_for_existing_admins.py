"""backfill admin_users for existing admin-capable users

Revision ID: 0062_backfill_admin_users_for_existing_admins
Revises: 0061_add_accident_tables
Create Date: 2026-05-20 00:00:00

Background
----------
The schema has two identity tables:
    - ``users``    — person (RFID chave, perfil, login).
    - ``admin_users`` — admin audit identity, used as FK target for
      columns named ``*_by_admin_id`` and ``actor_user_id``.

Until this revision, ``admin_users`` was populated lazily only by the
transport-AI flow (``ensure_admin_user_by_chave``). Other admin code
paths wrote ``users.id`` into FK columns that point at ``admin_users.id``,
which under Postgres FK enforcement fails with
``ForeignKeyViolation``. The visible symptom was the admin-side
"Reportar Acidente" button returning ``Erro ao abrir acidente.``

This migration backfills ``admin_users`` for every existing user that
currently has admin access (perfil digits include ``1`` or ``9``). The
lazy upsert in the application code now guarantees the row exists at
write time too, but this backfill closes the gap for already-deployed
hosts and makes the FK relation correct from the moment the migration
runs.

It also runs an audit report (logged via Alembic's logger) on every
table whose FK targets ``admin_users.id``, flagging any historical rows
whose ``*_by_admin_id`` value does not resolve. In production today the
audit returns zero drifts; the report exists so future regressions are
caught loudly.

Idempotent: skips inserting any chave that already has an
``admin_users`` row. Safe to run on hosts where the lazy upsert has
already created some rows.
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op


revision = "0062_backfill_admin_users_for_existing_admins"
down_revision = "0061_add_accident_tables"
branch_labels = None
depends_on = None


_logger = logging.getLogger("alembic.runtime.migration")


# Columns that act as FK -> admin_users.id. Kept in sync with the SQLAlchemy
# model definitions. Used only by the audit step at the end of upgrade().
_ADMIN_USER_FK_COLUMNS: tuple[tuple[str, str], ...] = (
    ("transport_assignments", "assigned_by_admin_id"),
    ("transport_ai_llm_settings", "updated_by_admin_id"),
    ("transport_ai_project_llm_settings", "updated_by_admin_id"),
    ("transport_ai_runs", "actor_user_id"),
    ("accidents", "opened_by_admin_id"),
    ("accidents", "closed_by_admin_id"),
)


def _profile_grants_admin(perfil: int | None) -> bool:
    """True when the perfil digits include '1' (admin) or '9' (full)."""
    if perfil is None:
        return False
    digits = set(str(int(perfil)))
    return "1" in digits or "9" in digits


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users") or not inspector.has_table("admin_users"):
        # Should never happen on a real deployment, but be defensive when
        # this revision runs against a partially-migrated test DB.
        _logger.info(
            "0062 backfill skipped: users or admin_users table is missing."
        )
        return

    users = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("chave", sa.String),
        sa.column("nome", sa.String),
        sa.column("perfil", sa.Integer),
    )
    admin_users = sa.table(
        "admin_users",
        sa.column("id", sa.Integer),
        sa.column("chave", sa.String),
        sa.column("nome_completo", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("requires_password_reset", sa.Boolean),
        sa.column("approved_by_admin_id", sa.Integer),
        sa.column("approved_at", sa.DateTime(timezone=True)),
        sa.column("password_reset_requested_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    now_expr = sa.func.current_timestamp()

    existing_chaves: set[str] = {
        row[0]
        for row in bind.execute(sa.select(admin_users.c.chave)).fetchall()
    }

    candidates = bind.execute(
        sa.select(users.c.id, users.c.chave, users.c.nome, users.c.perfil)
    ).fetchall()

    inserted: list[str] = []
    for _user_id, chave, nome, perfil in candidates:
        if chave is None:
            continue
        if not _profile_grants_admin(perfil):
            continue
        chave_normalized = str(chave).strip().upper()
        if chave_normalized in existing_chaves:
            continue

        nome_normalized = " ".join(str(nome or "").strip().split()) or chave_normalized
        bind.execute(
            sa.insert(admin_users).values(
                chave=chave_normalized,
                nome_completo=nome_normalized,
                password_hash=None,
                requires_password_reset=False,
                approved_by_admin_id=None,
                approved_at=None,
                password_reset_requested_at=None,
                created_at=now_expr,
                updated_at=now_expr,
            )
        )
        existing_chaves.add(chave_normalized)
        inserted.append(chave_normalized)

    if inserted:
        _logger.info(
            "0062 backfill: created admin_users rows for chaves %s",
            ", ".join(sorted(inserted)),
        )
    else:
        _logger.info(
            "0062 backfill: no missing admin_users rows for admin-capable users."
        )

    # Audit: report any FK drift for visibility. We do NOT mutate or drop
    # the offending rows here; that would be lossy. The report is purely
    # informational.
    for table_name, column_name in _ADMIN_USER_FK_COLUMNS:
        if not inspector.has_table(table_name):
            continue
        orphan_count_row = bind.execute(
            sa.text(
                f"""
                SELECT COUNT(*) FROM {table_name}
                 WHERE {column_name} IS NOT NULL
                   AND {column_name} NOT IN (SELECT id FROM admin_users)
                """
            )
        ).first()
        orphan_count = orphan_count_row[0] if orphan_count_row else 0
        if orphan_count:
            _logger.warning(
                "0062 audit: %s.%s has %d row(s) referencing a non-existent admin_users.id",
                table_name,
                column_name,
                orphan_count,
            )


def downgrade() -> None:
    # The backfill is purely additive. There is no safe automatic
    # downgrade because we cannot tell apart rows that this revision
    # created from rows that the application's lazy upsert created
    # afterwards. Leave the data in place.
    pass
