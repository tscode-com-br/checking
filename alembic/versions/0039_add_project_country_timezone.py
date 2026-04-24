"""add project country and timezone fields

Revision ID: 0039_project_country_timezone
Revises: 0038_proj_auto_checkout_dist
Create Date: 2026-04-24 12:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0039_project_country_timezone"
down_revision = "0038_proj_auto_checkout_dist"
branch_labels = None
depends_on = None


COUNTRY_CODE_LENGTH = 2
COUNTRY_NAME_LENGTH = 80
TIMEZONE_NAME_LENGTH = 64
DEFAULT_COUNTRY_CODE = "SG"
DEFAULT_COUNTRY_NAME = "Singapore"
DEFAULT_TIMEZONE_NAME = "Asia/Singapore"


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return any(column.get("name") == column_name for column in inspector.get_columns(table_name))
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("projects"):
        return

    if not _has_column(inspector, "projects", "country_code"):
        with op.batch_alter_table("projects") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "country_code",
                    sa.String(length=COUNTRY_CODE_LENGTH),
                    nullable=False,
                    server_default=DEFAULT_COUNTRY_CODE,
                )
            )

    inspector = sa.inspect(bind)
    if not _has_column(inspector, "projects", "country_name"):
        with op.batch_alter_table("projects") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "country_name",
                    sa.String(length=COUNTRY_NAME_LENGTH),
                    nullable=False,
                    server_default=DEFAULT_COUNTRY_NAME,
                )
            )

    inspector = sa.inspect(bind)
    if not _has_column(inspector, "projects", "timezone_name"):
        with op.batch_alter_table("projects") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "timezone_name",
                    sa.String(length=TIMEZONE_NAME_LENGTH),
                    nullable=False,
                    server_default=DEFAULT_TIMEZONE_NAME,
                )
            )

    projects_table = sa.table(
        "projects",
        sa.column("country_code", sa.String(length=COUNTRY_CODE_LENGTH)),
        sa.column("country_name", sa.String(length=COUNTRY_NAME_LENGTH)),
        sa.column("timezone_name", sa.String(length=TIMEZONE_NAME_LENGTH)),
    )

    op.execute(
        projects_table.update().values(
            country_code=sa.func.coalesce(projects_table.c.country_code, DEFAULT_COUNTRY_CODE),
            country_name=sa.func.coalesce(projects_table.c.country_name, DEFAULT_COUNTRY_NAME),
            timezone_name=sa.func.coalesce(projects_table.c.timezone_name, DEFAULT_TIMEZONE_NAME),
        )
    )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column(
            "country_code",
            existing_type=sa.String(length=COUNTRY_CODE_LENGTH),
            nullable=False,
            server_default=None,
        )
        batch_op.alter_column(
            "country_name",
            existing_type=sa.String(length=COUNTRY_NAME_LENGTH),
            nullable=False,
            server_default=None,
        )
        batch_op.alter_column(
            "timezone_name",
            existing_type=sa.String(length=TIMEZONE_NAME_LENGTH),
            nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("projects"):
        return

    with op.batch_alter_table("projects") as batch_op:
        if _has_column(inspector, "projects", "timezone_name"):
            batch_op.drop_column("timezone_name")
        if _has_column(inspector, "projects", "country_name"):
            batch_op.drop_column("country_name")
        if _has_column(inspector, "projects", "country_code"):
            batch_op.drop_column("country_code")