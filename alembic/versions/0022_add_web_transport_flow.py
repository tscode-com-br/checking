"""add web transport acknowledgement fields

Revision ID: 0022_web_transport_flow
Revises: 0021_transport_routes_sched
Create Date: 2026-04-18 23:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0022_web_transport_flow"
down_revision = "0021_transport_routes_sched"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transport_assignments"):
        assignment_columns = {column["name"] for column in inspector.get_columns("transport_assignments")}
        with op.batch_alter_table("transport_assignments") as batch_op:
            if "acknowledged_by_user" not in assignment_columns:
                batch_op.add_column(
                    sa.Column(
                        "acknowledged_by_user",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.false(),
                    )
                )
            if "acknowledged_at" not in assignment_columns:
                batch_op.add_column(sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transport_assignments"):
        assignment_columns = {column["name"] for column in inspector.get_columns("transport_assignments")}
        with op.batch_alter_table("transport_assignments") as batch_op:
            if "acknowledged_at" in assignment_columns:
                batch_op.drop_column("acknowledged_at")
            if "acknowledged_by_user" in assignment_columns:
                batch_op.drop_column("acknowledged_by_user")
