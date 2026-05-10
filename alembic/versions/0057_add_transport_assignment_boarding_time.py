"""add boarding time to transport assignments

Revision ID: 0057_add_transport_assignment_boarding_time
Revises: 0056_add_transport_extra_car_tolerance
Create Date: 2026-05-09 10:10:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0057_add_transport_assignment_boarding_time"
down_revision = "0056_add_transport_extra_car_tolerance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_assignments"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("transport_assignments")}
    if "boarding_time" in existing_columns:
        return

    with op.batch_alter_table("transport_assignments") as batch_op:
        batch_op.add_column(sa.Column("boarding_time", sa.String(length=5), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_assignments"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("transport_assignments")}
    if "boarding_time" not in existing_columns:
        return

    with op.batch_alter_table("transport_assignments") as batch_op:
        batch_op.drop_column("boarding_time")