"""add transport ai applied route stops

Revision ID: 0049_add_transport_ai_applied_route_stops
Revises: 0048_add_transport_ai_route_cache_tables
Create Date: 2026-04-30 02:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0049_add_transport_ai_applied_route_stops"
down_revision = "0048_add_transport_ai_route_cache_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transport_ai_applied_route_stops"):
        return

    op.create_table(
        "transport_ai_applied_route_stops",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("suggestion_id", sa.Integer(), sa.ForeignKey("transport_ai_suggestions.id"), nullable=False),
        sa.Column("vehicle_id", sa.Integer(), nullable=False),
        sa.Column("stop_order", sa.Integer(), nullable=False),
        sa.Column("stop_type", sa.String(length=16), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("passenger_name", sa.String(length=180), nullable=True),
        sa.Column("project_name", sa.String(length=120), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("zip_code", sa.String(length=32), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("scheduled_time", sa.String(length=5), nullable=False),
        sa.Column("duration_from_previous_seconds", sa.Integer(), nullable=True),
        sa.Column("distance_from_previous_meters", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "suggestion_id",
            "vehicle_id",
            "stop_order",
            name="uq_transport_ai_applied_route_stops_vehicle_order",
        ),
        sa.CheckConstraint(
            "vehicle_id >= 1",
            name="ck_transport_ai_applied_route_stops_vehicle_id_positive",
        ),
        sa.CheckConstraint(
            "stop_order >= 1",
            name="ck_transport_ai_applied_route_stops_stop_order_positive",
        ),
        sa.CheckConstraint(
            "stop_type IN ('pickup', 'destination')",
            name="ck_transport_ai_applied_route_stops_type_allowed",
        ),
        sa.CheckConstraint(
            "request_id IS NULL OR request_id >= 1",
            name="ck_transport_ai_applied_route_stops_request_id_positive",
        ),
        sa.CheckConstraint(
            "user_id IS NULL OR user_id >= 1",
            name="ck_transport_ai_applied_route_stops_user_id_positive",
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="ck_transport_ai_applied_route_stops_longitude_range",
        ),
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="ck_transport_ai_applied_route_stops_latitude_range",
        ),
        sa.CheckConstraint(
            "duration_from_previous_seconds IS NULL OR duration_from_previous_seconds >= 0",
            name="ck_transport_ai_applied_route_stops_duration_non_negative",
        ),
        sa.CheckConstraint(
            "distance_from_previous_meters IS NULL OR distance_from_previous_meters >= 0",
            name="ck_transport_ai_applied_route_stops_distance_non_negative",
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transport_ai_applied_route_stops"):
        op.drop_table("transport_ai_applied_route_stops")