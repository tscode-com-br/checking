"""drop check event rfid foreign key

Revision ID: 0004_drop_check_event_rfid_fk
Revises: 0003_expand_check_events_audit
Create Date: 2026-03-28 17:15:00
"""

from alembic import op


revision = "0004_drop_check_event_rfid_fk"
down_revision = "0003_expand_check_events_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        return
    with op.batch_alter_table("check_events") as batch_op:
        batch_op.drop_constraint("check_events_rfid_fkey", type_="foreignkey")


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        return
    with op.batch_alter_table("check_events") as batch_op:
        batch_op.create_foreign_key(
            "check_events_rfid_fkey",
            "users",
            ["rfid"],
            ["rfid"],
        )