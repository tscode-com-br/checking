"""add transport default tolerance setting

Revision ID: 0034_transport_default_tolerance
Revises: 0033_vehicle_plate_len15
Create Date: 2026-04-22 22:10:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0034_transport_default_tolerance"
down_revision = "0033_vehicle_plate_len15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("mobile_app_settings"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("mobile_app_settings")}

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        if "transport_default_tolerance_minutes" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "transport_default_tolerance_minutes",
                    sa.Integer(),
                    nullable=False,
                    server_default="5",
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("mobile_app_settings"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("mobile_app_settings")}

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        if "transport_default_tolerance_minutes" in existing_columns:
            batch_op.drop_column("transport_default_tolerance_minutes")