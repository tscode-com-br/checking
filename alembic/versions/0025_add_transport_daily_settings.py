"""add transport daily settings

Revision ID: 0025_transport_daily_settings
Revises: 0024_transport_work_to_home_time
Create Date: 2026-04-19 12:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0025_transport_daily_settings"
down_revision = "0024_transport_work_to_home_time"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transport_daily_settings"):
        return

    op.create_table(
        "transport_daily_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("work_to_home_time", sa.String(length=5), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("service_date", name="uq_transport_daily_settings_service_date"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_daily_settings"):
        return

    op.drop_table("transport_daily_settings")