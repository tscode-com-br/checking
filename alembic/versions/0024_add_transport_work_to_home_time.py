"""add transport work to home time setting

Revision ID: 0024_transport_work_to_home_time
Revises: 0023_user_perfil
Create Date: 2026-04-19 09:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0024_transport_work_to_home_time"
down_revision = "0023_user_perfil"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("mobile_app_settings"):
        return

    setting_columns = {column["name"] for column in inspector.get_columns("mobile_app_settings")}
    if "transport_work_to_home_time" in setting_columns:
        return

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "transport_work_to_home_time",
                sa.String(length=5),
                nullable=False,
                server_default="16:45",
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("mobile_app_settings"):
        return

    setting_columns = {column["name"] for column in inspector.get_columns("mobile_app_settings")}
    if "transport_work_to_home_time" not in setting_columns:
        return

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        batch_op.drop_column("transport_work_to_home_time")