"""add transport last update time setting

Revision ID: 0027_transport_last_update_time
Revises: 0026_projects_catalog
Create Date: 2026-04-19 18:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0027_transport_last_update_time"
down_revision = "0026_projects_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("mobile_app_settings"):
        return

    setting_columns = {column["name"] for column in inspector.get_columns("mobile_app_settings")}
    if "transport_last_update_time" in setting_columns:
        return

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "transport_last_update_time",
                sa.String(length=5),
                nullable=False,
                server_default="16:00",
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("mobile_app_settings"):
        return

    setting_columns = {column["name"] for column in inspector.get_columns("mobile_app_settings")}
    if "transport_last_update_time" not in setting_columns:
        return

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        batch_op.drop_column("transport_last_update_time")