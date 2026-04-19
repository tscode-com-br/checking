"""allow pending transport assignments

Revision ID: 0029_transport_assign_pending
Revises: 0028_transport_req_extra_depart
Create Date: 2026-04-19 23:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0029_transport_assign_pending"
down_revision = "0028_transport_req_extra_depart"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_assignments"):
        return

    check_constraints = {
        constraint.get("name")
        for constraint in inspector.get_check_constraints("transport_assignments")
        if constraint.get("name")
    }

    with op.batch_alter_table("transport_assignments") as batch_op:
        if "ck_transport_assignments_status_allowed" in check_constraints:
            batch_op.drop_constraint("ck_transport_assignments_status_allowed", type_="check")
        batch_op.create_check_constraint(
            "ck_transport_assignments_status_allowed",
            "status IN ('confirmed', 'rejected', 'cancelled', 'pending')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_assignments"):
        return

    check_constraints = {
        constraint.get("name")
        for constraint in inspector.get_check_constraints("transport_assignments")
        if constraint.get("name")
    }

    with op.batch_alter_table("transport_assignments") as batch_op:
        if "ck_transport_assignments_status_allowed" in check_constraints:
            batch_op.drop_constraint("ck_transport_assignments_status_allowed", type_="check")
        batch_op.create_check_constraint(
            "ck_transport_assignments_status_allowed",
            "status IN ('confirmed', 'rejected', 'cancelled')",
        )