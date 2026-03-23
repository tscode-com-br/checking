"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-22 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("rfid", sa.String(length=64), nullable=False),
        sa.Column("chave", sa.String(length=4), nullable=False),
        sa.Column("nome", sa.String(length=180), nullable=False),
        sa.Column("projeto", sa.String(length=3), nullable=False),
        sa.Column("checkin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("rfid"),
    )

    op.create_table(
        "pending_registrations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rfid", sa.String(length=64), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rfid", name="uq_pending_rfid"),
    )

    op.create_table(
        "device_heartbeats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.String(length=80), nullable=False),
        sa.Column("is_online", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "check_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("rfid", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("project", sa.String(length=3), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["rfid"], ["users.rfid"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_check_events_idempotency_key"),
    )


def downgrade() -> None:
    op.drop_table("check_events")
    op.drop_table("device_heartbeats")
    op.drop_table("pending_registrations")
    op.drop_table("users")
