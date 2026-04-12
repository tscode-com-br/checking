"""add coordinate update frequency table to mobile app settings

Revision ID: 0016_coordinate_update_frequency
Revises: 0015_location_accuracy_threshold
Create Date: 2026-04-12 14:40:00
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa


revision = "0016_coordinate_update_frequency"
down_revision = "0015_location_accuracy_threshold"
branch_labels = None
depends_on = None


DAY_LABELS = [
    "Segunda-Feira",
    "Terça-Feira",
    "Quarta-Feira",
    "Quinta-Feira",
    "Sexta-Feira",
    "Sábado",
    "Domingo",
]
PERIOD_VALUES = [
    ("00:01 a 01:00", 3600),
    ("01:01 a 02:00", 3600),
    ("02:01 a 03:00", 3600),
    ("03:01 a 04:00", 3600),
    ("04:01 a 05:00", 3600),
    ("05:01 a 06:00", 3600),
    ("06:01 a 07:00", 3600),
    ("07:01 a 08:00", 180),
    ("08:01 a 09:00", 240),
    ("09:01 a 10:00", 240),
    ("10:01 a 11:00", 240),
    ("11:01 a 12:00", 240),
    ("12:01 a 13:00", 360),
    ("13:01 a 14:00", 240),
    ("14:01 a 15:00", 240),
    ("15:01 a 16:00", 240),
    ("16:01 a 17:00", 180),
    ("17:01 a 18:00", 180),
    ("18:01 a 19:00", 240),
    ("19:01 a 20:00", 240),
    ("20:01 a 21:00", 240),
    ("21:01 a 22:00", 240),
    ("22:01 a 23:00", 480),
    ("23:01 a 00:00", 1800),
]


def _default_frequency_json() -> str:
    payload = {
        period: {day_label: seconds for day_label in DAY_LABELS}
        for period, seconds in PERIOD_VALUES
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def upgrade() -> None:
    with op.batch_alter_table("mobile_app_settings") as batch_op:
        batch_op.add_column(sa.Column("coordinate_update_frequency_json", sa.Text(), nullable=True))

    op.execute(
        sa.text(
            "UPDATE mobile_app_settings "
            "SET coordinate_update_frequency_json = :coordinate_update_frequency_json "
            "WHERE id = 1"
        ).bindparams(coordinate_update_frequency_json=_default_frequency_json())
    )


def downgrade() -> None:
    with op.batch_alter_table("mobile_app_settings") as batch_op:
        batch_op.drop_column("coordinate_update_frequency_json")