"""add transport extra car tolerance setting

Revision ID: 0056_add_transport_extra_car_tolerance
Revises: 0055_add_transport_arrive_at_work_time
Create Date: 2026-05-07 19:35:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0056_add_transport_extra_car_tolerance"
down_revision = "0055_add_transport_arrive_at_work_time"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("mobile_app_settings"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("mobile_app_settings")}

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        if "transport_extra_car_tolerance_minutes" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "transport_extra_car_tolerance_minutes",
                    sa.Integer(),
                    nullable=False,
                    server_default="30",
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("mobile_app_settings"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("mobile_app_settings")}

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        if "transport_extra_car_tolerance_minutes" in existing_columns:
            batch_op.drop_column("transport_extra_car_tolerance_minutes")