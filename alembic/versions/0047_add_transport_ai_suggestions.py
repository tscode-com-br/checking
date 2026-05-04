"""add transport ai suggestions table

Revision ID: 0047_add_transport_ai_suggestions
Revises: 0046_add_transport_ai_runs
Create Date: 2026-04-30 00:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0047_add_transport_ai_suggestions"
down_revision = "0046_add_transport_ai_runs"
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

    if not inspector.has_table("transport_ai_suggestions"):
        op.create_table(
            "transport_ai_suggestions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("suggestion_key", sa.String(length=120), nullable=False),
            sa.Column("run_id", sa.Integer(), sa.ForeignKey("transport_ai_runs.id"), nullable=False),
            sa.Column("service_date", sa.Date(), nullable=False),
            sa.Column("route_kind", sa.String(length=16), nullable=False),
            sa.Column("proposal_key", sa.String(length=120), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("agent_plan_json", sa.Text(), nullable=False),
            sa.Column("transport_proposal_json", sa.Text(), nullable=False),
            sa.Column("vehicle_actions_json", sa.Text(), nullable=False),
            sa.Column("assignment_actions_json", sa.Text(), nullable=False),
            sa.Column("route_itineraries_json", sa.Text(), nullable=False),
            sa.Column("change_summary_json", sa.Text(), nullable=False),
            sa.Column("cost_summary_json", sa.Text(), nullable=False),
            sa.Column("validation_issues_json", sa.Text(), nullable=False),
            sa.Column("raw_model_response_json", sa.Text(), nullable=True),
            sa.Column("prompt_version", sa.String(length=120), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "status IN ('draft', 'shown', 'saved', 'discarded', 'applied', 'expired')",
                name="ck_transport_ai_suggestions_status_allowed",
            ),
            sa.CheckConstraint(
                "route_kind IN ('home_to_work', 'work_to_home')",
                name="ck_transport_ai_suggestions_route_kind_allowed",
            ),
        )

    inspector = sa.inspect(bind)
    existing_indexes = _index_names(inspector, "transport_ai_suggestions")

    if "ix_transport_ai_suggestions_suggestion_key" not in existing_indexes:
        op.create_index(
            "ix_transport_ai_suggestions_suggestion_key",
            "transport_ai_suggestions",
            ["suggestion_key"],
            unique=True,
        )

    if "ix_transport_ai_suggestions_service_date_route_kind_status_updated_at" not in existing_indexes:
        op.create_index(
            "ix_transport_ai_suggestions_service_date_route_kind_status_updated_at",
            "transport_ai_suggestions",
            ["service_date", "route_kind", "status", "updated_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_ai_suggestions"):
        return

    existing_indexes = _index_names(inspector, "transport_ai_suggestions")
    if "ix_transport_ai_suggestions_service_date_route_kind_status_updated_at" in existing_indexes:
        op.drop_index(
            "ix_transport_ai_suggestions_service_date_route_kind_status_updated_at",
            table_name="transport_ai_suggestions",
        )
    if "ix_transport_ai_suggestions_suggestion_key" in existing_indexes:
        op.drop_index("ix_transport_ai_suggestions_suggestion_key", table_name="transport_ai_suggestions")

    op.drop_table("transport_ai_suggestions")