"""add leg metadata to transport ai applied route stops

Revision ID: 0058_add_transport_ai_applied_route_stop_legs
Revises: 0057_add_transport_assignment_boarding_time
Create Date: 2026-05-09 15:05:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0058_add_transport_ai_applied_route_stop_legs"
down_revision = "0057_add_transport_assignment_boarding_time"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_ai_applied_route_stops"):
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("transport_ai_applied_route_stops")
    }
    if "route_kind" not in existing_columns:
        with op.batch_alter_table("transport_ai_applied_route_stops") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "route_kind",
                    sa.String(length=16),
                    nullable=True,
                    server_default="home_to_work",
                )
            )

    op.execute(
        sa.text(
            "UPDATE transport_ai_applied_route_stops SET route_kind = 'home_to_work' WHERE route_kind IS NULL"
        )
    )

    inspector = sa.inspect(bind)
    existing_unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("transport_ai_applied_route_stops")
    }
    existing_check_constraints = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("transport_ai_applied_route_stops")
    }

    with op.batch_alter_table("transport_ai_applied_route_stops") as batch_op:
        if "uq_transport_ai_applied_route_stops_vehicle_order" in existing_unique_constraints:
            batch_op.drop_constraint(
                "uq_transport_ai_applied_route_stops_vehicle_order",
                type_="unique",
            )
        if "ck_transport_ai_applied_route_stops_type_allowed" in existing_check_constraints:
            batch_op.drop_constraint(
                "ck_transport_ai_applied_route_stops_type_allowed",
                type_="check",
            )
        if "ck_transport_ai_applied_route_stops_route_kind_allowed" in existing_check_constraints:
            batch_op.drop_constraint(
                "ck_transport_ai_applied_route_stops_route_kind_allowed",
                type_="check",
            )

        batch_op.alter_column(
            "route_kind",
            existing_type=sa.String(length=16),
            nullable=False,
            server_default=None,
        )
        batch_op.create_check_constraint(
            "ck_transport_ai_applied_route_stops_route_kind_allowed",
            "route_kind IN ('home_to_work', 'work_to_home')",
        )
        batch_op.create_check_constraint(
            "ck_transport_ai_applied_route_stops_type_allowed",
            "stop_type IN ('pickup', 'destination', 'origin', 'dropoff')",
        )
        batch_op.create_unique_constraint(
            "uq_transport_ai_applied_route_stops_vehicle_order",
            ["suggestion_id", "vehicle_id", "route_kind", "stop_order"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_ai_applied_route_stops"):
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("transport_ai_applied_route_stops")
    }
    if "route_kind" not in existing_columns:
        return

    existing_unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("transport_ai_applied_route_stops")
    }
    existing_check_constraints = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("transport_ai_applied_route_stops")
    }

    with op.batch_alter_table("transport_ai_applied_route_stops") as batch_op:
        if "uq_transport_ai_applied_route_stops_vehicle_order" in existing_unique_constraints:
            batch_op.drop_constraint(
                "uq_transport_ai_applied_route_stops_vehicle_order",
                type_="unique",
            )
        if "ck_transport_ai_applied_route_stops_type_allowed" in existing_check_constraints:
            batch_op.drop_constraint(
                "ck_transport_ai_applied_route_stops_type_allowed",
                type_="check",
            )
        if "ck_transport_ai_applied_route_stops_route_kind_allowed" in existing_check_constraints:
            batch_op.drop_constraint(
                "ck_transport_ai_applied_route_stops_route_kind_allowed",
                type_="check",
            )

        batch_op.create_check_constraint(
            "ck_transport_ai_applied_route_stops_type_allowed",
            "stop_type IN ('pickup', 'destination')",
        )
        batch_op.create_unique_constraint(
            "uq_transport_ai_applied_route_stops_vehicle_order",
            ["suggestion_id", "vehicle_id", "stop_order"],
        )
        batch_op.drop_column("route_kind")