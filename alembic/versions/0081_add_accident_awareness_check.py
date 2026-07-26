"""add the missing CHECK on accident_user_reports.awareness_status

Revision 0074 added the awareness_status column but not the CHECK constraint that
models.py declares for it (ck_accident_user_reports_awareness_allowed, models.py:853).
The sibling constraints for `zone` and `status` came from 0061 and do exist, so a
migrated database — production included — enforces two of the three enums and
silently accepts any string in the third. Databases built by Base.metadata.create_all
(development) have always had all three, which is why the drift went unnoticed.

Adding it is safe: the only writers are open_accident, upsert_user_safety_report,
update_accident_membership_for_check_event and acknowledge_accident, and every one
of them writes the literal "waiting" or "acknowledged".

Revision ID: 0081_add_accident_awareness_check
Revises: 0080_add_event_time_indexes
Create Date: 2026-07-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0081_add_accident_awareness_check"
down_revision = "0080_add_event_time_indexes"
branch_labels = None
depends_on = None

_TABLE = "accident_user_reports"
_CONSTRAINT = "ck_accident_user_reports_awareness_allowed"
_CONDITION = "awareness_status IN ('waiting', 'acknowledged')"


def _has_constraint(inspector: sa.Inspector) -> bool:
    return any(
        c.get("name") == _CONSTRAINT
        for c in inspector.get_check_constraints(_TABLE)
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(_TABLE):
        return
    if _has_constraint(inspector):
        return

    # Normalise anything unexpected before constraining, so the migration cannot
    # fail on legacy rows written before the column had a default.
    op.execute(
        sa.text(
            f"UPDATE {_TABLE} SET awareness_status = 'waiting' "
            f"WHERE awareness_status IS NULL OR NOT ({_CONDITION})"
        )
    )

    # batch_alter_table so SQLite gets a table rebuild; PostgreSQL takes the plain
    # ALTER TABLE ... ADD CONSTRAINT path.
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.create_check_constraint(_CONSTRAINT, _CONDITION)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(_TABLE):
        return
    if not _has_constraint(inspector):
        return

    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.drop_constraint(_CONSTRAINT, type_="check")
