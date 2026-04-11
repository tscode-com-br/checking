"""add mobile app settings

Revision ID: 0013_mobile_app_settings
Revises: 0012_locations_catalog
Create Date: 2026-04-11 10:20:00
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "0013_mobile_app_settings"
down_revision = "0012_locations_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mobile_app_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False, nullable=False),
        sa.Column("location_update_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    timestamp = datetime.now(timezone.utc)
    op.bulk_insert(
        sa.table(
            "mobile_app_settings",
            sa.column("id", sa.Integer()),
            sa.column("location_update_interval_seconds", sa.Integer()),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "id": 1,
                "location_update_interval_seconds": 60,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("mobile_app_settings")