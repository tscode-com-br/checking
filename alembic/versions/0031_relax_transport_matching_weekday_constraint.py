"""relax transport matching weekday constraint

Revision ID: 0031_transport_matching_weekday
Revises: 0030_drop_transport_bot
Create Date: 2026-04-22 14:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0031_transport_matching_weekday"
down_revision = "0030_drop_transport_bot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_vehicle_schedules"):
        return

    check_constraints = {
        constraint.get("name")
        for constraint in inspector.get_check_constraints("transport_vehicle_schedules")
        if constraint.get("name")
    }

    with op.batch_alter_table("transport_vehicle_schedules") as batch_op:
        if "ck_transport_vehicle_schedules_matching_weekday_required" in check_constraints:
            batch_op.drop_constraint("ck_transport_vehicle_schedules_matching_weekday_required", type_="check")
        batch_op.create_check_constraint(
            "ck_transport_vehicle_schedules_matching_weekday_required",
            "(recurrence_kind = 'matching_weekday' AND weekday IS NOT NULL) OR (recurrence_kind != 'matching_weekday')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_vehicle_schedules"):
        return

    check_constraints = {
        constraint.get("name")
        for constraint in inspector.get_check_constraints("transport_vehicle_schedules")
        if constraint.get("name")
    }

    with op.batch_alter_table("transport_vehicle_schedules") as batch_op:
        if "ck_transport_vehicle_schedules_matching_weekday_required" in check_constraints:
            batch_op.drop_constraint("ck_transport_vehicle_schedules_matching_weekday_required", type_="check")
        batch_op.create_check_constraint(
            "ck_transport_vehicle_schedules_matching_weekday_required",
            "(recurrence_kind = 'matching_weekday' AND weekday IS NOT NULL AND weekday >= 5) OR (recurrence_kind != 'matching_weekday')",
        )