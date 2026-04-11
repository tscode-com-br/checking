"""add location accuracy threshold to mobile app settings

Revision ID: 0015_location_accuracy_threshold
Revises: 0014_location_multi_coordinates
Create Date: 2026-04-12 11:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0015_location_accuracy_threshold"
down_revision = "0014_location_multi_coordinates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("mobile_app_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "location_accuracy_threshold_meters",
                sa.Integer(),
                nullable=False,
                server_default="30",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("mobile_app_settings") as batch_op:
        batch_op.drop_column("location_accuracy_threshold_meters")