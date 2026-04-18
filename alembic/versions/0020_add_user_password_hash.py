"""add hashed password column for web users

Revision ID: 0020_add_user_password_hash
Revises: 0019_transport_workflow
Create Date: 2026-04-18 13:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0020_add_user_password_hash"
down_revision = "0019_transport_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users"):
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "senha" in user_columns:
        return

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("senha", sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users"):
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "senha" not in user_columns:
        return

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("senha")