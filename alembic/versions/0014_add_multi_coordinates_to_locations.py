"""add multi coordinates to locations

Revision ID: 0014_location_multi_coordinates
Revises: 0013_mobile_app_settings
Create Date: 2026-04-11 15:30:00
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa


revision = "0014_location_multi_coordinates"
down_revision = "0013_mobile_app_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("locations") as batch_op:
        batch_op.add_column(sa.Column("coordinates_json", sa.Text(), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, latitude, longitude FROM locations")).mappings().all()
    for row in rows:
        coordinates_json = json.dumps(
            [{"latitude": float(row["latitude"]), "longitude": float(row["longitude"])}],
            ensure_ascii=True,
            separators=(",", ":"),
        )
        connection.execute(
            sa.text("UPDATE locations SET coordinates_json = :coordinates_json WHERE id = :location_id"),
            {"coordinates_json": coordinates_json, "location_id": row["id"]},
        )


def downgrade() -> None:
    with op.batch_alter_table("locations") as batch_op:
        batch_op.drop_column("coordinates_json")