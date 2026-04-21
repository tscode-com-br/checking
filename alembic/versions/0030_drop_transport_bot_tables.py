"""drop transport bot tables

Revision ID: 0030_drop_transport_bot
Revises: 0029_transport_assign_pending
Create Date: 2026-04-21 13:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0030_drop_transport_bot"
down_revision = "0029_transport_assign_pending"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transport_notifications"):
        op.drop_table("transport_notifications")
    if inspector.has_table("transport_bot_sessions"):
        op.drop_table("transport_bot_sessions")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

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