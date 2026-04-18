"""add user perfil column

Revision ID: 0023_user_perfil
Revises: 0022_web_transport_flow
Create Date: 2026-04-19 02:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0023_user_perfil"
down_revision = "0022_web_transport_flow"
branch_labels = None
depends_on = None


PROFILE_BY_KEY = {
    "UTO9": 1,
    "CYMQ": 1,
    "U32N": 1,
    "RNA7": 1,
    "U4ZR": 1,
    "HR70": 9,
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users"):
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "perfil" not in user_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(sa.Column("perfil", sa.Integer(), nullable=False, server_default="0"))

    users_table = sa.table(
        "users",
        sa.column("chave", sa.String(length=4)),
        sa.column("perfil", sa.Integer()),
    )
    op.execute(users_table.update().values(perfil=0))
    for chave, perfil in PROFILE_BY_KEY.items():
        op.execute(users_table.update().where(users_table.c.chave == chave).values(perfil=perfil))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users"):
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "perfil" in user_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("perfil")