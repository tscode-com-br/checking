"""enrich workplaces with transport planning context

Revision ID: 0042_add_transport_workplace_context_and_time_policy
Revises: 0041_add_user_vehicle_id_link
Create Date: 2026-04-28 14:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0042_add_transport_workplace_context_and_time_policy"
down_revision = "0041_add_user_vehicle_id_link"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return any(column.get("name") == column_name for column in inspector.get_columns(table_name))
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("workplaces"):
        return

    with op.batch_alter_table("workplaces") as batch_op:
        if not _has_column(inspector, "workplaces", "transport_group"):
            batch_op.add_column(sa.Column("transport_group", sa.String(length=80), nullable=True))
        if not _has_column(inspector, "workplaces", "boarding_point"):
            batch_op.add_column(sa.Column("boarding_point", sa.String(length=255), nullable=True))
        if not _has_column(inspector, "workplaces", "transport_window_start"):
            batch_op.add_column(sa.Column("transport_window_start", sa.String(length=5), nullable=True))
        if not _has_column(inspector, "workplaces", "transport_window_end"):
            batch_op.add_column(sa.Column("transport_window_end", sa.String(length=5), nullable=True))
        if not _has_column(inspector, "workplaces", "service_restrictions"):
            batch_op.add_column(sa.Column("service_restrictions", sa.Text(), nullable=True))
        if not _has_column(inspector, "workplaces", "transport_work_to_home_time"):
            batch_op.add_column(sa.Column("transport_work_to_home_time", sa.String(length=5), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("workplaces"):
        return

    with op.batch_alter_table("workplaces") as batch_op:
        if _has_column(inspector, "workplaces", "transport_work_to_home_time"):
            batch_op.drop_column("transport_work_to_home_time")
        if _has_column(inspector, "workplaces", "service_restrictions"):
            batch_op.drop_column("service_restrictions")
        if _has_column(inspector, "workplaces", "transport_window_end"):
            batch_op.drop_column("transport_window_end")
        if _has_column(inspector, "workplaces", "transport_window_start"):
            batch_op.drop_column("transport_window_start")
        if _has_column(inspector, "workplaces", "boarding_point"):
            batch_op.drop_column("boarding_point")
        if _has_column(inspector, "workplaces", "transport_group"):
            batch_op.drop_column("transport_group")