"""add project address and zip code

Revision ID: 0045_add_project_address_and_zip_code
Revises: 0044_add_transport_pricing_settings_and_currency_options
Create Date: 2026-04-29 23:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0045_add_project_address_and_zip_code"
down_revision = "0044_add_transport_pricing_settings_and_currency_options"
branch_labels = None
depends_on = None


ADDRESS_LENGTH = 255
ZIP_CODE_LENGTH = 32
DEFAULT_TEXT = ""


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

    if not _has_column(inspector, "projects", "address"):
        with op.batch_alter_table("projects") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "address",
                    sa.String(length=ADDRESS_LENGTH),
                    nullable=False,
                    server_default=DEFAULT_TEXT,
                )
            )

    inspector = sa.inspect(bind)
    if not _has_column(inspector, "projects", "zip_code"):
        with op.batch_alter_table("projects") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "zip_code",
                    sa.String(length=ZIP_CODE_LENGTH),
                    nullable=False,
                    server_default=DEFAULT_TEXT,
                )
            )

    projects_table = sa.table(
        "projects",
        sa.column("address", sa.String(length=ADDRESS_LENGTH)),
        sa.column("zip_code", sa.String(length=ZIP_CODE_LENGTH)),
    )

    op.execute(
        projects_table.update().values(
            address=sa.func.coalesce(projects_table.c.address, DEFAULT_TEXT),
            zip_code=sa.func.coalesce(projects_table.c.zip_code, DEFAULT_TEXT),
        )
    )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column(
            "address",
            existing_type=sa.String(length=ADDRESS_LENGTH),
            nullable=False,
            server_default=None,
        )
        batch_op.alter_column(
            "zip_code",
            existing_type=sa.String(length=ZIP_CODE_LENGTH),
            nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("projects"):
        return

    with op.batch_alter_table("projects") as batch_op:
        if _has_column(inspector, "projects", "zip_code"):
            batch_op.drop_column("zip_code")
        if _has_column(inspector, "projects", "address"):
            batch_op.drop_column("address")