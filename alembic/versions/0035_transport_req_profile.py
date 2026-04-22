"""add requested profile to admin access requests

Revision ID: 0035_transport_req_profile
Revises: 0034_transport_default_tolerance
Create Date: 2026-04-22 23:05:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0035_transport_req_profile"
down_revision = "0034_transport_default_tolerance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("admin_access_requests"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("admin_access_requests")}

    with op.batch_alter_table("admin_access_requests") as batch_op:
        if "requested_profile" not in existing_columns:
            batch_op.add_column(
                sa.Column("requested_profile", sa.Integer(), nullable=False, server_default="1")
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("admin_access_requests"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("admin_access_requests")}

    with op.batch_alter_table("admin_access_requests") as batch_op:
        if "requested_profile" in existing_columns:
            batch_op.drop_column("requested_profile")