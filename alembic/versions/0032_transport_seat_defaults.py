"""add transport seat defaults to mobile app settings

Revision ID: 0032_transport_seat_defaults
Revises: 0031_transport_matching_weekday
Create Date: 2026-04-22 19:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0032_transport_seat_defaults"
down_revision = "0031_transport_matching_weekday"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("mobile_app_settings"):
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("mobile_app_settings")
    }

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        if "transport_default_car_seats" not in existing_columns:
            batch_op.add_column(sa.Column("transport_default_car_seats", sa.Integer(), nullable=False, server_default="3"))
        if "transport_default_minivan_seats" not in existing_columns:
            batch_op.add_column(sa.Column("transport_default_minivan_seats", sa.Integer(), nullable=False, server_default="6"))
        if "transport_default_van_seats" not in existing_columns:
            batch_op.add_column(sa.Column("transport_default_van_seats", sa.Integer(), nullable=False, server_default="10"))
        if "transport_default_bus_seats" not in existing_columns:
            batch_op.add_column(sa.Column("transport_default_bus_seats", sa.Integer(), nullable=False, server_default="40"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("mobile_app_settings"):
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("mobile_app_settings")
    }

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        if "transport_default_bus_seats" in existing_columns:
            batch_op.drop_column("transport_default_bus_seats")
        if "transport_default_van_seats" in existing_columns:
            batch_op.drop_column("transport_default_van_seats")
        if "transport_default_minivan_seats" in existing_columns:
            batch_op.drop_column("transport_default_minivan_seats")
        if "transport_default_car_seats" in existing_columns:
            batch_op.drop_column("transport_default_car_seats")