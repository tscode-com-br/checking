"""add pending_user_registrations (plan003 — new-user approval queue)

Revision ID: 0079_add_pending_user_registrations
Revises: 0078_add_local_to_checkinghistory
Create Date: 2026-06-20

Adds the ``pending_user_registrations`` table that holds self-registrations
awaiting admin approval (plan003). The real ``User`` is created only on
approval, so nothing in ``users`` is affected while a registration is pending.
Additive and reversible; unique on ``chave``, indexed on ``requested_at``.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0079_add_pending_user_registrations"
down_revision = "0078_add_local_to_checkinghistory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pending_user_registrations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chave", sa.String(length=4), nullable=False),
        sa.Column("nome_completo", sa.String(length=180), nullable=False),
        sa.Column("projetos_json", sa.Text(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("client", sa.String(length=16), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("chave", name="uq_pending_user_registrations_chave"),
    )
    op.create_index(
        "ix_pending_user_registrations_requested_at",
        "pending_user_registrations",
        ["requested_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pending_user_registrations_requested_at",
        table_name="pending_user_registrations",
    )
    op.drop_table("pending_user_registrations")
