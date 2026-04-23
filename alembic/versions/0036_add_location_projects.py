"""add project assignments to managed locations

Revision ID: 0036_add_location_projects
Revises: 0035_transport_req_profile
Create Date: 2026-04-23 11:20:00
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op


revision = "0036_add_location_projects"
down_revision = "0035_transport_req_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("locations"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("locations")}

    with op.batch_alter_table("locations") as batch_op:
        if "projects_json" not in existing_columns:
            batch_op.add_column(sa.Column("projects_json", sa.Text(), nullable=True))

    if not inspector.has_table("projects"):
        return

    project_names = [
        str(row[0]).strip().upper()
        for row in bind.execute(sa.text("SELECT name FROM projects ORDER BY name, id")).all()
        if str(row[0] or "").strip()
    ]
    if not project_names:
        return

    projects_json = json.dumps(sorted(dict.fromkeys(project_names)), ensure_ascii=True, separators=(",", ":"))
    bind.execute(
        sa.text(
            "UPDATE locations SET projects_json = :projects_json "
            "WHERE projects_json IS NULL OR TRIM(projects_json) = ''"
        ),
        {"projects_json": projects_json},
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("locations"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("locations")}

    with op.batch_alter_table("locations") as batch_op:
        if "projects_json" in existing_columns:
            batch_op.drop_column("projects_json")