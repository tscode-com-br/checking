"""allow duplicate managed location names

Revision ID: 0037_dup_location_names
Revises: 0036_add_location_projects
Create Date: 2026-04-23 15:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0037_dup_location_names"
down_revision = "0036_add_location_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("locations"):
        return

    unique_names = {constraint["name"] for constraint in inspector.get_unique_constraints("locations")}
    if "uq_locations_local" not in unique_names:
        return

    with op.batch_alter_table("locations") as batch_op:
        batch_op.drop_constraint("uq_locations_local", type_="unique")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("locations"):
        return

    unique_names = {constraint["name"] for constraint in inspector.get_unique_constraints("locations")}
    if "uq_locations_local" in unique_names:
        return

    with op.batch_alter_table("locations") as batch_op:
        batch_op.create_unique_constraint("uq_locations_local", ["local"])
