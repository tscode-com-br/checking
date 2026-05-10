"""add transport arrive at work time

Revision ID: 0055_add_transport_arrive_at_work_time
Revises: 0054_add_user_project_memberships
Create Date: 2026-05-07 18:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0055_add_transport_arrive_at_work_time"
down_revision = "0054_add_user_project_memberships"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("mobile_app_settings"):
        return

    setting_columns = {column["name"] for column in inspector.get_columns("mobile_app_settings")}
    if "transport_arrive_at_work_time" in setting_columns:
        return

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "transport_arrive_at_work_time",
                sa.String(length=5),
                nullable=False,
                server_default="07:45",
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("mobile_app_settings"):
        return

    setting_columns = {column["name"] for column in inspector.get_columns("mobile_app_settings")}
    if "transport_arrive_at_work_time" not in setting_columns:
        return

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        batch_op.drop_column("transport_arrive_at_work_time")