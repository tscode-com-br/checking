"""add user inactivity tracking

Revision ID: 0006_user_inactivity
Revises: 0005_make_user_status_nullable
Create Date: 2026-03-29 07:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_user_inactivity"
down_revision = "0005_make_user_status_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("inactivity_days", sa.Integer(), nullable=False, server_default="0"))
    op.execute("UPDATE users SET last_active_at = COALESCE(time, CURRENT_TIMESTAMP)")
    op.execute("UPDATE users SET inactivity_days = 0")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("last_active_at", existing_type=sa.DateTime(timezone=True), nullable=False)


def downgrade() -> None:
    op.drop_column("users", "inactivity_days")
    op.drop_column("users", "last_active_at")