"""add forms submission queue

Revision ID: 0007_add_forms_submission_queue
Revises: 0006_user_inactivity
Create Date: 2026-03-29 12:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_add_forms_submission_queue"
down_revision = "0006_user_inactivity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forms_submissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(length=80), nullable=False),
        sa.Column("rfid", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("chave", sa.String(length=4), nullable=False),
        sa.Column("projeto", sa.String(length=3), nullable=False),
        sa.Column("device_id", sa.String(length=80), nullable=True),
        sa.Column("local", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_forms_submissions_request_id"),
    )


def downgrade() -> None:
    op.drop_table("forms_submissions")