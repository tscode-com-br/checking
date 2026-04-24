"""add project auto checkout distances

Revision ID: 0038_proj_auto_checkout_dist
Revises: 0037_dup_location_names
Create Date: 2026-04-24 10:30:00
"""

from __future__ import annotations

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "0038_proj_auto_checkout_dist"
down_revision = "0037_dup_location_names"
branch_labels = None
depends_on = None


DEFAULT_MINIMUM_CHECKOUT_DISTANCE_METERS = 2000


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("project_auto_checkout_distances"):
        op.create_table(
            "project_auto_checkout_distances",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "project_name",
                sa.String(length=120),
                sa.ForeignKey("projects.name", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "minimum_checkout_distance_meters",
                sa.Integer(),
                nullable=False,
                server_default=str(DEFAULT_MINIMUM_CHECKOUT_DISTANCE_METERS),
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "project_name",
                name="uq_project_auto_checkout_distances_project_name",
            ),
            sa.CheckConstraint(
                "minimum_checkout_distance_meters >= 1",
                name="ck_project_auto_checkout_distances_distance_positive",
            ),
        )

    inspector = sa.inspect(bind)
    if not inspector.has_table("projects"):
        return

    projects_table = sa.table(
        "projects",
        sa.column("name", sa.String(length=120)),
    )
    project_auto_checkout_distances_table = sa.table(
        "project_auto_checkout_distances",
        sa.column("project_name", sa.String(length=120)),
        sa.column("minimum_checkout_distance_meters", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    existing_project_names = {
        row[0]
        for row in bind.execute(sa.select(projects_table.c.name)).all()
        if row[0]
    }
    configured_project_names = {
        row[0]
        for row in bind.execute(
            sa.select(project_auto_checkout_distances_table.c.project_name)
        ).all()
        if row[0]
    }
    missing_project_names = sorted(existing_project_names - configured_project_names)
    if not missing_project_names:
        return

    timestamp = datetime.now(timezone.utc)
    for project_name in missing_project_names:
        op.execute(
            project_auto_checkout_distances_table.insert().values(
                project_name=project_name,
                minimum_checkout_distance_meters=DEFAULT_MINIMUM_CHECKOUT_DISTANCE_METERS,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("project_auto_checkout_distances"):
        op.drop_table("project_auto_checkout_distances")