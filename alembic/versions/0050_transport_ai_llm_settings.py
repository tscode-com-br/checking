"""add transport ai llm settings

Revision ID: 0050_transport_ai_llm_settings
Revises: 0049_add_transport_ai_applied_route_stops
Create Date: 2026-05-04 10:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0050_transport_ai_llm_settings"
down_revision = "0049_add_transport_ai_applied_route_stops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transport_ai_llm_settings"):
        return

    op.create_table(
        "transport_ai_llm_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False, nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("reasoning_effort", sa.String(length=32), nullable=False),
        sa.Column("api_key_ciphertext", sa.Text(), nullable=True),
        sa.Column("api_key_last4", sa.String(length=8), nullable=True),
        sa.Column("updated_by_admin_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "provider IN ('openai', 'deepseek')",
            name="ck_transport_ai_llm_settings_provider_allowed",
        ),
        sa.CheckConstraint(
            "reasoning_effort IN ('high')",
            name="ck_transport_ai_llm_settings_reasoning_effort_allowed",
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transport_ai_llm_settings"):
        op.drop_table("transport_ai_llm_settings")
