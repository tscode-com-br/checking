"""add transport pricing settings and currency catalog

Revision ID: 0044_add_transport_pricing_settings_and_currency_options
Revises: 0043_allow_partial_transport_vehicle_base
Create Date: 2026-04-29 22:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0044_add_transport_pricing_settings_and_currency_options"
down_revision = "0043_allow_partial_transport_vehicle_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_currency_options"):
        op.create_table(
            "transport_currency_options",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("code", sa.String(length=12), nullable=False),
            sa.Column("display_label", sa.String(length=80), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("code", name="uq_transport_currency_options_code"),
        )

    inspector = sa.inspect(bind)
    if not inspector.has_table("mobile_app_settings"):
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("mobile_app_settings")
    }

    with op.batch_alter_table("mobile_app_settings") as batch_op:
        if "transport_price_currency_code" not in existing_columns:
            batch_op.add_column(sa.Column("transport_price_currency_code", sa.String(length=12), nullable=True))
        if "transport_price_rate_unit" not in existing_columns:
            batch_op.add_column(sa.Column("transport_price_rate_unit", sa.String(length=16), nullable=True))
        if "transport_default_car_price" not in existing_columns:
            batch_op.add_column(sa.Column("transport_default_car_price", sa.Numeric(12, 2), nullable=True))
        if "transport_default_minivan_price" not in existing_columns:
            batch_op.add_column(sa.Column("transport_default_minivan_price", sa.Numeric(12, 2), nullable=True))
        if "transport_default_van_price" not in existing_columns:
            batch_op.add_column(sa.Column("transport_default_van_price", sa.Numeric(12, 2), nullable=True))
        if "transport_default_bus_price" not in existing_columns:
            batch_op.add_column(sa.Column("transport_default_bus_price", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("mobile_app_settings"):
        existing_columns = {
            column["name"]
            for column in inspector.get_columns("mobile_app_settings")
        }

        with op.batch_alter_table("mobile_app_settings") as batch_op:
            if "transport_default_bus_price" in existing_columns:
                batch_op.drop_column("transport_default_bus_price")
            if "transport_default_van_price" in existing_columns:
                batch_op.drop_column("transport_default_van_price")
            if "transport_default_minivan_price" in existing_columns:
                batch_op.drop_column("transport_default_minivan_price")
            if "transport_default_car_price" in existing_columns:
                batch_op.drop_column("transport_default_car_price")
            if "transport_price_rate_unit" in existing_columns:
                batch_op.drop_column("transport_price_rate_unit")
            if "transport_price_currency_code" in existing_columns:
                batch_op.drop_column("transport_price_currency_code")

    inspector = sa.inspect(bind)
    if inspector.has_table("transport_currency_options"):
        op.drop_table("transport_currency_options")