"""add admin monitored projects scope

Revision ID: 0040_add_admin_monitored_projects
Revises: 0039_project_country_timezone
Create Date: 2026-04-25 16:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0040_add_admin_monitored_projects"
down_revision = "0039_project_country_timezone"
branch_labels = None
depends_on = None


COLUMN_NAME = "admin_monitored_projects_json"


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return any(column.get("name") == column_name for column in inspector.get_columns(table_name))
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users") or _has_column(inspector, "users", COLUMN_NAME):
        return

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column(COLUMN_NAME, sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users") or not _has_column(inspector, "users", COLUMN_NAME):
        return

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column(COLUMN_NAME)