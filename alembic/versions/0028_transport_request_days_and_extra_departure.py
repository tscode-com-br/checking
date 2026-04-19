"""add transport request weekday selections and extra departure time

Revision ID: 0028_transport_request_days_and_extra_departure
Revises: 0027_transport_last_update_time
Create Date: 2026-04-19 22:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0028_transport_request_days_and_extra_departure"
down_revision = "0027_transport_last_update_time"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transport_requests"):
        request_columns = {column["name"] for column in inspector.get_columns("transport_requests")}
        if "selected_weekdays_json" not in request_columns:
            with op.batch_alter_table("transport_requests") as batch_op:
                batch_op.add_column(sa.Column("selected_weekdays_json", sa.Text(), nullable=True))

        op.execute(
            sa.text(
                """
                UPDATE transport_requests
                SET selected_weekdays_json = CASE
                    WHEN request_kind = 'regular' THEN '[0,1,2,3,4]'
                    WHEN request_kind = 'weekend' THEN '[5,6]'
                    ELSE selected_weekdays_json
                END
                WHERE selected_weekdays_json IS NULL
                  AND request_kind IN ('regular', 'weekend')
                """
            )
        )

    if inspector.has_table("transport_vehicle_schedules"):
        schedule_columns = {column["name"] for column in inspector.get_columns("transport_vehicle_schedules")}
        if "departure_time" not in schedule_columns:
            with op.batch_alter_table("transport_vehicle_schedules") as batch_op:
                batch_op.add_column(sa.Column("departure_time", sa.String(length=5), nullable=True))

    if inspector.has_table("vehicles"):
        vehicle_columns = {column["name"] for column in inspector.get_columns("vehicles")}
        if "tolerance" in vehicle_columns:
            op.execute(sa.text("UPDATE vehicles SET tolerance = 5"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transport_vehicle_schedules"):
        schedule_columns = {column["name"] for column in inspector.get_columns("transport_vehicle_schedules")}
        if "departure_time" in schedule_columns:
            with op.batch_alter_table("transport_vehicle_schedules") as batch_op:
                batch_op.drop_column("departure_time")

    if inspector.has_table("transport_requests"):
        request_columns = {column["name"] for column in inspector.get_columns("transport_requests")}
        if "selected_weekdays_json" in request_columns:
            with op.batch_alter_table("transport_requests") as batch_op:
                batch_op.drop_column("selected_weekdays_json")