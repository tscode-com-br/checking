"""add route-aware transport assignments and vehicle schedules

Revision ID: 0021_transport_routes_sched
Revises: 0020_add_user_password_hash
Create Date: 2026-04-18 22:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0021_transport_routes_sched"
down_revision = "0020_add_user_password_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transport_assignments"):
        assignment_columns = {column["name"] for column in inspector.get_columns("transport_assignments")}
        assignment_unique_names = {constraint["name"] for constraint in inspector.get_unique_constraints("transport_assignments")}
        assignment_check_names = {constraint["name"] for constraint in inspector.get_check_constraints("transport_assignments")}

        with op.batch_alter_table("transport_assignments") as batch_op:
            if "route_kind" not in assignment_columns:
                batch_op.add_column(
                    sa.Column(
                        "route_kind",
                        sa.String(length=16),
                        nullable=False,
                        server_default="home_to_work",
                    )
                )
            if "uq_transport_assignments_request_date" in assignment_unique_names:
                batch_op.drop_constraint("uq_transport_assignments_request_date", type_="unique")
            if "uq_transport_assignments_request_date_route" not in assignment_unique_names:
                batch_op.create_unique_constraint(
                    "uq_transport_assignments_request_date_route",
                    ["request_id", "service_date", "route_kind"],
                )
            if "ck_transport_assignments_route_allowed" not in assignment_check_names:
                batch_op.create_check_constraint(
                    "ck_transport_assignments_route_allowed",
                    "route_kind IN ('home_to_work', 'work_to_home')",
                )

    if not inspector.has_table("transport_vehicle_schedules"):
        op.create_table(
            "transport_vehicle_schedules",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("vehicle_id", sa.Integer(), nullable=False),
            sa.Column("service_scope", sa.String(length=16), nullable=False),
            sa.Column("route_kind", sa.String(length=16), nullable=False),
            sa.Column("recurrence_kind", sa.String(length=24), nullable=False),
            sa.Column("service_date", sa.Date(), nullable=True),
            sa.Column("weekday", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("service_scope IN ('regular', 'weekend', 'extra')", name="ck_transport_vehicle_schedules_scope_allowed"),
            sa.CheckConstraint("route_kind IN ('home_to_work', 'work_to_home')", name="ck_transport_vehicle_schedules_route_allowed"),
            sa.CheckConstraint("recurrence_kind IN ('weekday', 'matching_weekday', 'single_date')", name="ck_transport_vehicle_schedules_recurrence_allowed"),
            sa.CheckConstraint("weekday IS NULL OR (weekday >= 0 AND weekday <= 6)", name="ck_transport_vehicle_schedules_weekday_range"),
            sa.CheckConstraint(
                "(recurrence_kind = 'single_date' AND service_date IS NOT NULL) OR (recurrence_kind != 'single_date')",
                name="ck_transport_vehicle_schedules_single_date_required",
            ),
            sa.CheckConstraint(
                "(recurrence_kind = 'matching_weekday' AND weekday IS NOT NULL AND weekday >= 5) OR (recurrence_kind != 'matching_weekday')",
                name="ck_transport_vehicle_schedules_matching_weekday_required",
            ),
            sa.CheckConstraint(
                "(recurrence_kind = 'weekday' AND weekday IS NULL) OR (recurrence_kind != 'weekday')",
                name="ck_transport_vehicle_schedules_weekday_kind_shape",
            ),
            sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not inspector.has_table("transport_vehicle_schedule_exceptions"):
        op.create_table(
            "transport_vehicle_schedule_exceptions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("vehicle_schedule_id", sa.Integer(), nullable=False),
            sa.Column("service_date", sa.Date(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["vehicle_schedule_id"], ["transport_vehicle_schedules.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "vehicle_schedule_id",
                "service_date",
                name="uq_transport_vehicle_schedule_exceptions_schedule_date",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transport_vehicle_schedule_exceptions"):
        op.drop_table("transport_vehicle_schedule_exceptions")

    if inspector.has_table("transport_vehicle_schedules"):
        op.drop_table("transport_vehicle_schedules")

    if inspector.has_table("transport_assignments"):
        assignment_columns = {column["name"] for column in inspector.get_columns("transport_assignments")}
        assignment_unique_names = {constraint["name"] for constraint in inspector.get_unique_constraints("transport_assignments")}
        assignment_check_names = {constraint["name"] for constraint in inspector.get_check_constraints("transport_assignments")}

        with op.batch_alter_table("transport_assignments") as batch_op:
            if "uq_transport_assignments_request_date_route" in assignment_unique_names:
                batch_op.drop_constraint("uq_transport_assignments_request_date_route", type_="unique")
            if "uq_transport_assignments_request_date" not in assignment_unique_names:
                batch_op.create_unique_constraint(
                    "uq_transport_assignments_request_date",
                    ["request_id", "service_date"],
                )
            if "ck_transport_assignments_route_allowed" in assignment_check_names:
                batch_op.drop_constraint("ck_transport_assignments_route_allowed", type_="check")
            if "route_kind" in assignment_columns:
                batch_op.drop_column("route_kind")