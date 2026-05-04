"""add transport ai runs table

Revision ID: 0046_add_transport_ai_runs
Revises: 0045_add_project_address_and_zip_code
Create Date: 2026-04-30 00:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0046_add_transport_ai_runs"
down_revision = "0045_add_project_address_and_zip_code"
branch_labels = None
depends_on = None


def _index_names(inspector, table_name: str) -> set[str]:
    try:
        return {index.get("name") for index in inspector.get_indexes(table_name)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_ai_runs"):
        op.create_table(
            "transport_ai_runs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("run_key", sa.String(length=120), nullable=False),
            sa.Column("service_date", sa.Date(), nullable=False),
            sa.Column("route_kind", sa.String(length=16), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=False),
            sa.Column("earliest_boarding_time", sa.String(length=5), nullable=False),
            sa.Column("arrival_at_work_time", sa.String(length=5), nullable=False),
            sa.Column("openai_model", sa.String(length=120), nullable=False),
            sa.Column("route_provider", sa.String(length=40), nullable=False),
            sa.Column("price_currency_code", sa.String(length=12), nullable=True),
            sa.Column("price_rate_unit", sa.String(length=16), nullable=False),
            sa.Column("baseline_snapshot_json", sa.Text(), nullable=True),
            sa.Column("baseline_assignments_json", sa.Text(), nullable=True),
            sa.Column("baseline_vehicle_state_json", sa.Text(), nullable=True),
            sa.Column("planning_input_json", sa.Text(), nullable=False),
            sa.Column("planning_input_hash", sa.String(length=64), nullable=False),
            sa.Column("preflight_issues_json", sa.Text(), nullable=True),
            sa.Column("error_code", sa.String(length=64), nullable=True),
            sa.Column("error_message", sa.String(length=1000), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "status IN ('requested', 'baseline_saved', 'passengers_reset', 'running', 'proposed', 'saved', 'applied', 'cancelled', 'failed')",
                name="ck_transport_ai_runs_status_allowed",
            ),
            sa.CheckConstraint(
                "route_kind IN ('home_to_work', 'work_to_home')",
                name="ck_transport_ai_runs_route_kind_allowed",
            ),
        )

    inspector = sa.inspect(bind)
    existing_indexes = _index_names(inspector, "transport_ai_runs")

    if "ix_transport_ai_runs_run_key" not in existing_indexes:
        op.create_index(
            "ix_transport_ai_runs_run_key",
            "transport_ai_runs",
            ["run_key"],
            unique=True,
        )

    if "ix_transport_ai_runs_service_date_route_kind_created_at" not in existing_indexes:
        op.create_index(
            "ix_transport_ai_runs_service_date_route_kind_created_at",
            "transport_ai_runs",
            ["service_date", "route_kind", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_ai_runs"):
        return

    existing_indexes = _index_names(inspector, "transport_ai_runs")
    if "ix_transport_ai_runs_service_date_route_kind_created_at" in existing_indexes:
        op.drop_index(
            "ix_transport_ai_runs_service_date_route_kind_created_at",
            table_name="transport_ai_runs",
        )
    if "ix_transport_ai_runs_run_key" in existing_indexes:
        op.drop_index("ix_transport_ai_runs_run_key", table_name="transport_ai_runs")

    op.drop_table("transport_ai_runs")