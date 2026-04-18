"""add workplaces and transport request workflow tables

Revision ID: 0019_transport_workflow
Revises: 0018_checkinghistory_csv_import
Create Date: 2026-04-18 01:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0019_transport_workflow"
down_revision = "0018_checkinghistory_csv_import"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("workplaces"):
        op.create_table(
            "workplaces",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("workplace", sa.String(length=120), nullable=False),
            sa.Column("address", sa.String(length=255), nullable=False),
            sa.Column("zip", sa.String(length=10), nullable=False),
            sa.Column("country", sa.String(length=80), nullable=False),
            sa.UniqueConstraint("workplace", name="uq_workplaces_workplace"),
        )
    else:
        workplace_columns = {column["name"] for column in inspector.get_columns("workplaces")}
        with op.batch_alter_table("workplaces") as batch_op:
            if "localtrabalho" in workplace_columns and "workplace" not in workplace_columns:
                batch_op.alter_column(
                    "localtrabalho",
                    existing_type=sa.String(length=120),
                    new_column_name="workplace",
                )
            if "address" not in workplace_columns:
                batch_op.add_column(sa.Column("address", sa.String(length=255), nullable=True))
            if "zip" not in workplace_columns:
                batch_op.add_column(sa.Column("zip", sa.String(length=10), nullable=True))
            if "country" not in workplace_columns:
                batch_op.add_column(sa.Column("country", sa.String(length=80), nullable=True))

    inspector = sa.inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    user_foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("users") if fk.get("name")}
    with op.batch_alter_table("users") as batch_op:
        if "localtrabalho" in user_columns and "workplace" not in user_columns:
            batch_op.alter_column(
                "localtrabalho",
                existing_type=sa.String(length=120),
                new_column_name="workplace",
            )
        elif "workplace" not in user_columns:
            batch_op.add_column(sa.Column("workplace", sa.String(length=120), nullable=True))
        if "fk_users_workplace_workplaces" not in user_foreign_keys:
            batch_op.create_foreign_key(
                "fk_users_workplace_workplaces",
                "workplaces",
                ["workplace"],
                ["workplace"],
            )

    vehicle_columns = {column["name"] for column in inspector.get_columns("vehicles")}
    with op.batch_alter_table("vehicles") as batch_op:
        if "color" not in vehicle_columns:
            batch_op.add_column(sa.Column("color", sa.String(length=40), nullable=True))
        if "tolerance" not in vehicle_columns:
            batch_op.add_column(sa.Column("tolerance", sa.Integer(), nullable=False, server_default="0"))
        if "service_scope" not in vehicle_columns:
            batch_op.add_column(sa.Column("service_scope", sa.String(length=16), nullable=False, server_default="regular"))
        batch_op.create_check_constraint("ck_vehicles_tolerance_range", "tolerance >= 0 AND tolerance <= 240")
        batch_op.create_check_constraint(
            "ck_vehicles_service_scope_allowed",
            "service_scope IN ('regular', 'weekend', 'extra')",
        )

    if not inspector.has_table("transport_requests"):
        op.create_table(
            "transport_requests",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("request_kind", sa.String(length=16), nullable=False),
            sa.Column("recurrence_kind", sa.String(length=16), nullable=False),
            sa.Column("requested_time", sa.String(length=5), nullable=False),
            sa.Column("single_date", sa.Date(), nullable=True),
            sa.Column("created_via", sa.String(length=20), nullable=False, server_default="admin"),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint("request_kind IN ('regular', 'weekend', 'extra')", name="ck_transport_requests_kind_allowed"),
            sa.CheckConstraint(
                "recurrence_kind IN ('weekday', 'weekend', 'single_date')",
                name="ck_transport_requests_recurrence_allowed",
            ),
            sa.CheckConstraint("status IN ('active', 'cancelled')", name="ck_transport_requests_status_allowed"),
        )

    if not inspector.has_table("transport_assignments"):
        op.create_table(
            "transport_assignments",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("request_id", sa.Integer(), sa.ForeignKey("transport_requests.id"), nullable=False),
            sa.Column("service_date", sa.Date(), nullable=False),
            sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="confirmed"),
            sa.Column("response_message", sa.String(length=255), nullable=True),
            sa.Column("assigned_by_admin_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("request_id", "service_date", name="uq_transport_assignments_request_date"),
            sa.CheckConstraint(
                "status IN ('confirmed', 'rejected', 'cancelled')",
                name="ck_transport_assignments_status_allowed",
            ),
        )

    if not inspector.has_table("transport_bot_sessions"):
        op.create_table(
            "transport_bot_sessions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("chat_id", sa.String(length=120), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("chave", sa.String(length=4), nullable=True),
            sa.Column("state", sa.String(length=32), nullable=False, server_default="awaiting_key"),
            sa.Column("context_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("chat_id", name="uq_transport_bot_sessions_chat_id"),
        )

    if not inspector.has_table("transport_notifications"):
        op.create_table(
            "transport_notifications",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("chat_id", sa.String(length=120), nullable=True),
            sa.Column("request_id", sa.Integer(), sa.ForeignKey("transport_requests.id"), nullable=True),
            sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("transport_assignments.id"), nullable=True),
            sa.Column("message", sa.String(length=500), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint("status IN ('pending', 'sent')", name="ck_transport_notifications_status_allowed"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transport_notifications"):
        op.drop_table("transport_notifications")
    if inspector.has_table("transport_bot_sessions"):
        op.drop_table("transport_bot_sessions")
    if inspector.has_table("transport_assignments"):
        op.drop_table("transport_assignments")
    if inspector.has_table("transport_requests"):
        op.drop_table("transport_requests")

    if inspector.has_table("vehicles"):
        vehicle_columns = {column["name"] for column in inspector.get_columns("vehicles")}
        with op.batch_alter_table("vehicles") as batch_op:
            if "ck_vehicles_service_scope_allowed" in {check["name"] for check in inspector.get_check_constraints("vehicles") if check.get("name")}:
                batch_op.drop_constraint("ck_vehicles_service_scope_allowed", type_="check")
            if "ck_vehicles_tolerance_range" in {check["name"] for check in inspector.get_check_constraints("vehicles") if check.get("name")}:
                batch_op.drop_constraint("ck_vehicles_tolerance_range", type_="check")
            if "service_scope" in vehicle_columns:
                batch_op.drop_column("service_scope")
            if "tolerance" in vehicle_columns:
                batch_op.drop_column("tolerance")
            if "color" in vehicle_columns:
                batch_op.drop_column("color")

    if inspector.has_table("users"):
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        user_foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("users") if fk.get("name")}
        with op.batch_alter_table("users") as batch_op:
            if "fk_users_workplace_workplaces" in user_foreign_keys:
                batch_op.drop_constraint("fk_users_workplace_workplaces", type_="foreignkey")
            if "workplace" in user_columns:
                batch_op.drop_column("workplace")

    if inspector.has_table("workplaces"):
        op.drop_table("workplaces")