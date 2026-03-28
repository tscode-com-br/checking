"""add user local field

Revision ID: 0002_add_user_local
Revises: 0001_initial
Create Date: 2026-03-28 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_user_local"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("local", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "local")