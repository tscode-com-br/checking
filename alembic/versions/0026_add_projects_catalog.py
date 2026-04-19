"""add projects catalog

Revision ID: 0026_projects_catalog
Revises: 0025_transport_daily_settings
Create Date: 2026-04-19 16:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0026_projects_catalog"
down_revision = "0025_transport_daily_settings"
branch_labels = None
depends_on = None


DEFAULT_PROJECT_NAMES = ("P80", "P82", "P83")
PROJECT_NAME_LENGTH = 120


def _list_check_constraint_names(inspector, table_name: str) -> set[str]:
    try:
        return {
            constraint["name"]
            for constraint in inspector.get_check_constraints(table_name)
            if constraint.get("name")
        }
    except Exception:
        return set()


def _ensure_projects_table(inspector) -> None:
    if inspector.has_table("projects"):
        return

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=PROJECT_NAME_LENGTH), nullable=False),
        sa.UniqueConstraint("name", name="uq_projects_name"),
    )


def _seed_default_projects(bind, inspector) -> None:
    if not inspector.has_table("projects"):
        return

    projects_table = sa.table(
        "projects",
        sa.column("name", sa.String(length=PROJECT_NAME_LENGTH)),
    )
    existing_names = {
        row[0]
        for row in bind.execute(sa.select(projects_table.c.name)).all()
        if row[0]
    }
    missing_names = [name for name in DEFAULT_PROJECT_NAMES if name not in existing_names]
    for project_name in missing_names:
        op.execute(projects_table.insert().values(name=project_name))


def _resize_project_columns(inspector) -> None:
    if inspector.has_table("users"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "projeto",
                existing_type=sa.String(length=3),
                type_=sa.String(length=PROJECT_NAME_LENGTH),
                existing_nullable=False,
            )

    if inspector.has_table("check_events"):
        with op.batch_alter_table("check_events") as batch_op:
            batch_op.alter_column(
                "project",
                existing_type=sa.String(length=3),
                type_=sa.String(length=PROJECT_NAME_LENGTH),
                existing_nullable=True,
            )

    if inspector.has_table("forms_submissions"):
        with op.batch_alter_table("forms_submissions") as batch_op:
            batch_op.alter_column(
                "projeto",
                existing_type=sa.String(length=3),
                type_=sa.String(length=PROJECT_NAME_LENGTH),
                existing_nullable=False,
            )

    if inspector.has_table("user_sync_events"):
        with op.batch_alter_table("user_sync_events") as batch_op:
            batch_op.alter_column(
                "projeto",
                existing_type=sa.String(length=3),
                type_=sa.String(length=PROJECT_NAME_LENGTH),
                existing_nullable=True,
            )

    if inspector.has_table("checkinghistory"):
        constraint_names = _list_check_constraint_names(inspector, "checkinghistory")
        with op.batch_alter_table("checkinghistory") as batch_op:
            if "ck_checkinghistory_projeto_allowed" in constraint_names:
                batch_op.drop_constraint("ck_checkinghistory_projeto_allowed", type_="check")
            batch_op.alter_column(
                "projeto",
                existing_type=sa.String(length=3),
                type_=sa.String(length=PROJECT_NAME_LENGTH),
                existing_nullable=False,
            )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _ensure_projects_table(inspector)
    inspector = sa.inspect(bind)
    _seed_default_projects(bind, inspector)
    _resize_project_columns(inspector)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("checkinghistory"):
        constraint_names = _list_check_constraint_names(inspector, "checkinghistory")
        with op.batch_alter_table("checkinghistory") as batch_op:
            if "ck_checkinghistory_projeto_allowed" not in constraint_names:
                batch_op.create_check_constraint(
                    "ck_checkinghistory_projeto_allowed",
                    "projeto IN ('P80', 'P82', 'P83')",
                )
            batch_op.alter_column(
                "projeto",
                existing_type=sa.String(length=PROJECT_NAME_LENGTH),
                type_=sa.String(length=3),
                existing_nullable=False,
            )

    if inspector.has_table("user_sync_events"):
        with op.batch_alter_table("user_sync_events") as batch_op:
            batch_op.alter_column(
                "projeto",
                existing_type=sa.String(length=PROJECT_NAME_LENGTH),
                type_=sa.String(length=3),
                existing_nullable=True,
            )

    if inspector.has_table("forms_submissions"):
        with op.batch_alter_table("forms_submissions") as batch_op:
            batch_op.alter_column(
                "projeto",
                existing_type=sa.String(length=PROJECT_NAME_LENGTH),
                type_=sa.String(length=3),
                existing_nullable=False,
            )

    if inspector.has_table("check_events"):
        with op.batch_alter_table("check_events") as batch_op:
            batch_op.alter_column(
                "project",
                existing_type=sa.String(length=PROJECT_NAME_LENGTH),
                type_=sa.String(length=3),
                existing_nullable=True,
            )

    if inspector.has_table("users"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "projeto",
                existing_type=sa.String(length=PROJECT_NAME_LENGTH),
                type_=sa.String(length=3),
                existing_nullable=False,
            )

    if inspector.has_table("projects"):
        op.drop_table("projects")