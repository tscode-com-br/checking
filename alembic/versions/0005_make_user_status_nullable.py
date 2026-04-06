"""make user status nullable until first real scan

Revision ID: 0005_make_user_status_nullable
Revises: 0004_drop_check_event_rfid_fk
Create Date: 2026-03-28 19:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_make_user_status_nullable"
down_revision = "0004_drop_check_event_rfid_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("checkin", existing_type=sa.Boolean(), nullable=True, server_default=None)
        batch_op.alter_column("time", existing_type=sa.DateTime(timezone=True), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE users SET checkin = false WHERE checkin IS NULL")
    op.execute("UPDATE users SET time = CURRENT_TIMESTAMP WHERE time IS NULL")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("checkin", existing_type=sa.Boolean(), nullable=False, server_default=sa.false())
        batch_op.alter_column("time", existing_type=sa.DateTime(timezone=True), nullable=False)