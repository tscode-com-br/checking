"""add transport ai route cache tables

Revision ID: 0048_add_transport_ai_route_cache_tables
Revises: 0047_add_transport_ai_suggestions
Create Date: 2026-04-30 01:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0048_add_transport_ai_route_cache_tables"
down_revision = "0047_add_transport_ai_suggestions"
branch_labels = None
depends_on = None


def _index_names(inspector, table_name: str) -> set[str]:
    try:
        return {index.get("name") for index in inspector.get_indexes(table_name)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("transport_ai_route_points"):
        op.create_table(
            "transport_ai_route_points",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("point_key", sa.String(length=64), nullable=False),
            sa.Column("point_type", sa.String(length=24), nullable=False),
            sa.Column("source_id", sa.Integer(), nullable=False),
            sa.Column("address", sa.String(length=255), nullable=False),
            sa.Column("zip_code", sa.String(length=32), nullable=False),
            sa.Column("country_code", sa.String(length=2), nullable=False),
            sa.Column("country_name", sa.String(length=80), nullable=False),
            sa.Column("normalized_query", sa.String(length=512), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("provider_place_id", sa.String(length=255), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("raw_response_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "point_type IN ('passenger_origin', 'project_destination')",
                name="ck_transport_ai_route_points_type_allowed",
            ),
            sa.CheckConstraint(
                "longitude >= -180 AND longitude <= 180",
                name="ck_transport_ai_route_points_longitude_range",
            ),
            sa.CheckConstraint(
                "latitude >= -90 AND latitude <= 90",
                name="ck_transport_ai_route_points_latitude_range",
            ),
            sa.CheckConstraint(
                "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
                name="ck_transport_ai_route_points_confidence_range",
            ),
        )

    if not inspector.has_table("transport_ai_route_matrices"):
        op.create_table(
            "transport_ai_route_matrices",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("matrix_key", sa.String(length=64), nullable=False),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("profile", sa.String(length=80), nullable=False),
            sa.Column("depart_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("coordinate_hash", sa.String(length=64), nullable=False),
            sa.Column("sources_json", sa.Text(), nullable=False),
            sa.Column("destinations_json", sa.Text(), nullable=False),
            sa.Column("durations_json", sa.Text(), nullable=False),
            sa.Column("distances_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )

    inspector = sa.inspect(bind)
    route_point_indexes = _index_names(inspector, "transport_ai_route_points")
    if "ix_transport_ai_route_points_point_key" not in route_point_indexes:
        op.create_index(
            "ix_transport_ai_route_points_point_key",
            "transport_ai_route_points",
            ["point_key"],
            unique=True,
        )

    route_matrix_indexes = _index_names(inspector, "transport_ai_route_matrices")
    if "ix_transport_ai_route_matrices_matrix_key" not in route_matrix_indexes:
        op.create_index(
            "ix_transport_ai_route_matrices_matrix_key",
            "transport_ai_route_matrices",
            ["matrix_key"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transport_ai_route_matrices"):
        route_matrix_indexes = _index_names(inspector, "transport_ai_route_matrices")
        if "ix_transport_ai_route_matrices_matrix_key" in route_matrix_indexes:
            op.drop_index("ix_transport_ai_route_matrices_matrix_key", table_name="transport_ai_route_matrices")
        op.drop_table("transport_ai_route_matrices")

    inspector = sa.inspect(bind)
    if inspector.has_table("transport_ai_route_points"):
        route_point_indexes = _index_names(inspector, "transport_ai_route_points")
        if "ix_transport_ai_route_points_point_key" in route_point_indexes:
            op.drop_index("ix_transport_ai_route_points_point_key", table_name="transport_ai_route_points")
        op.drop_table("transport_ai_route_points")