"""change accident unique-active constraint from global to per-project

Drops:  ix_accidents_single_active  (unique on closed_at WHERE NULL)
        ix_accidents_single_active_guard  (unique on (1) WHERE NULL)
Creates: ix_accidents_single_active_per_project  (unique on project_id WHERE NULL)

Revision ID: 0075_accident_unique_per_project
Revises: 0074_add_accident_user_report_awareness
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0075_accident_unique_per_project"
down_revision = "0074_add_accident_user_report_awareness"
branch_labels = None
depends_on = None

_OLD_INDEXES = ("ix_accidents_single_active", "ix_accidents_single_active_guard")
_NEW_INDEX = "ix_accidents_single_active_per_project"
_NEW_INDEX_DDL = (
    f"CREATE UNIQUE INDEX IF NOT EXISTS {_NEW_INDEX} "
    "ON accidents (project_id) WHERE closed_at IS NULL"
)
_OLD_GUARD_DDL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_accidents_single_active_guard "
    "ON accidents ((1)) WHERE closed_at IS NULL"
)
_OLD_ACTIVE_DDL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_accidents_single_active "
    "ON accidents (closed_at) WHERE closed_at IS NULL"
)

# Both SQLite and PostgreSQL accept IF EXISTS / IF NOT EXISTS on index DDL, and
# using it is what makes this migration correct on SQLite. Reflection cannot be
# trusted here: ix_accidents_single_active_guard is an EXPRESSION index
# (ON accidents ((1))), and the SQLite dialect silently skips expression-based
# indexes — "Skipped unsupported reflection of expression-based index". So the
# guard never appeared in inspector.get_indexes(), never got dropped, and survived
# the upgrade: a second accident in a DIFFERENT project then failed with
# "UNIQUE constraint failed: index 'ix_accidents_single_active_guard'", defeating
# the whole point of this revision. Downgrade had the mirror bug — it re-created an
# index that was still there. PostgreSQL reflects expression indexes, so production
# was never affected.


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("accidents"):
        return

    for idx_name in _OLD_INDEXES:
        op.execute(sa.text(f"DROP INDEX IF EXISTS {idx_name}"))

    op.execute(sa.text(_NEW_INDEX_DDL))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("accidents"):
        return

    op.execute(sa.text(f"DROP INDEX IF EXISTS {_NEW_INDEX}"))
    op.execute(sa.text(_OLD_ACTIVE_DDL))
    op.execute(sa.text(_OLD_GUARD_DDL))
