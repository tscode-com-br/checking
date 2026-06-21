"""add local to checkinghistory (change D — history with location)

Revision ID: 0078_add_local_to_checkinghistory
Revises: 0077_add_accident_call_notifications
Create Date: 2026-06-17

Adds a nullable ``local`` column to ``checkinghistory`` so the per-user history
can carry the activity location (plan002 change D). Intentionally NOT part of
``uq_checkinghistory_event`` — the existing 5-field idempotent upsert stays
unchanged, and pre-existing rows keep a blank location.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0078_add_local_to_checkinghistory"
down_revision = "0077_add_accident_call_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("checkinghistory", sa.Column("local", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("checkinghistory", "local")
