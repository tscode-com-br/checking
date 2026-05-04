"""add llm snapshot columns to transport ai runs

Revision ID: 0051_add_transport_ai_run_llm_snapshot
Revises: 0050_transport_ai_llm_settings
Create Date: 2026-05-04 14:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0051_add_transport_ai_run_llm_snapshot"
down_revision = "0050_transport_ai_llm_settings"
branch_labels = None
depends_on = None


def _column_names(inspector, table_name: str) -> set[str]:
    try:
        return {column.get("name") for column in inspector.get_columns(table_name)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("transport_ai_runs"):
        return

    existing_columns = _column_names(inspector, "transport_ai_runs")
    if "llm_provider" not in existing_columns:
        op.add_column("transport_ai_runs", sa.Column("llm_provider", sa.String(length=16), nullable=True))
    if "llm_model" not in existing_columns:
        op.add_column("transport_ai_runs", sa.Column("llm_model", sa.String(length=120), nullable=True))
    if "llm_reasoning_effort" not in existing_columns:
        op.add_column(
            "transport_ai_runs",
            sa.Column("llm_reasoning_effort", sa.String(length=32), nullable=True),
        )

    op.execute(
        sa.text(
            """
            UPDATE transport_ai_runs
            SET llm_provider = COALESCE(llm_provider, 'openai'),
                llm_model = COALESCE(llm_model, openai_model),
                llm_reasoning_effort = COALESCE(llm_reasoning_effort, 'high')
            WHERE openai_model IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("transport_ai_runs"):
        return

    existing_columns = _column_names(inspector, "transport_ai_runs")
    drop_columns: list[str] = []
    for column_name in ("llm_provider", "llm_model", "llm_reasoning_effort"):
        if column_name in existing_columns:
            drop_columns.append(column_name)

    if not drop_columns:
        return

    with op.batch_alter_table("transport_ai_runs") as batch_op:
        for column_name in drop_columns:
            batch_op.drop_column(column_name)
