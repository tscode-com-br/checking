"""add locations catalog

Revision ID: 0012_locations_catalog
Revises: 0011_ontime_forms_events
Create Date: 2026-04-09 18:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_locations_catalog"
down_revision = "0011_ontime_forms_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("local", sa.String(length=40), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("tolerance_meters", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("local", name="uq_locations_local"),
    )


def downgrade() -> None:
    op.drop_table("locations")