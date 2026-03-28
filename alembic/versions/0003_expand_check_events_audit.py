"""expand check events audit columns

Revision ID: 0003_expand_check_events_audit
Revises: 0002_add_user_local
Create Date: 2026-03-28 00:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_expand_check_events_audit"
down_revision = "0002_add_user_local"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("check_events", sa.Column("source", sa.String(length=20), nullable=True))
    op.add_column("check_events", sa.Column("details", sa.String(length=1000), nullable=True))
    op.add_column("check_events", sa.Column("device_id", sa.String(length=80), nullable=True))
    op.add_column("check_events", sa.Column("local", sa.String(length=40), nullable=True))
    op.add_column("check_events", sa.Column("request_path", sa.String(length=120), nullable=True))
    op.add_column("check_events", sa.Column("http_status", sa.Integer(), nullable=True))

    op.execute("UPDATE check_events SET source = 'system' WHERE source IS NULL")
    op.alter_column("check_events", "source", nullable=False)


def downgrade() -> None:
    op.drop_column("check_events", "http_status")
    op.drop_column("check_events", "request_path")
    op.drop_column("check_events", "local")
    op.drop_column("check_events", "device_id")
    op.drop_column("check_events", "details")
    op.drop_column("check_events", "source")