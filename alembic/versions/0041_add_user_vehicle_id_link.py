"""move user vehicle linkage to stable vehicle ids

Revision ID: 0041_add_user_vehicle_id_link
Revises: 0040_add_admin_monitored_projects
Create Date: 2026-04-28 10:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0041_add_user_vehicle_id_link"
down_revision = "0040_add_admin_monitored_projects"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return any(column.get("name") == column_name for column in inspector.get_columns(table_name))
    except Exception:
        return False


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    try:
        return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))
    except Exception:
        return False


def _find_users_plate_fk(inspector) -> str | None:
    try:
        for foreign_key in inspector.get_foreign_keys("users"):
            constrained_columns = foreign_key.get("constrained_columns") or []
            referred_table = foreign_key.get("referred_table")
            referred_columns = foreign_key.get("referred_columns") or []
            if constrained_columns == ["placa"] and referred_table == "vehicles" and referred_columns == ["placa"]:
                return foreign_key.get("name")
    except Exception:
        return None
    return None


def _has_users_vehicle_id_fk(inspector) -> bool:
    try:
        for foreign_key in inspector.get_foreign_keys("users"):
            constrained_columns = foreign_key.get("constrained_columns") or []
            referred_table = foreign_key.get("referred_table")
            referred_columns = foreign_key.get("referred_columns") or []
            if constrained_columns == ["vehicle_id"] and referred_table == "vehicles" and referred_columns == ["id"]:
                return True
    except Exception:
        return False
    return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users") or not inspector.has_table("vehicles"):
        return

    has_vehicle_id_column = _has_column(inspector, "users", "vehicle_id")
    has_vehicle_id_fk = _has_users_vehicle_id_fk(inspector)
    has_vehicle_id_index = _has_index(inspector, "users", "ix_users_vehicle_id")
    users_plate_fk_name = _find_users_plate_fk(inspector)

    with op.batch_alter_table("users") as batch_op:
        if not has_vehicle_id_column:
            batch_op.add_column(sa.Column("vehicle_id", sa.Integer(), nullable=True))
        if not has_vehicle_id_fk:
            batch_op.create_foreign_key("fk_users_vehicle_id_vehicles", "vehicles", ["vehicle_id"], ["id"])
        if not has_vehicle_id_index:
            batch_op.create_index("ix_users_vehicle_id", ["vehicle_id"], unique=False)
        if users_plate_fk_name:
            batch_op.drop_constraint(users_plate_fk_name, type_="foreignkey")

    bind.execute(
        sa.text(
            """
            UPDATE users
            SET vehicle_id = (
                SELECT vehicles.id
                FROM vehicles
                WHERE vehicles.placa = users.placa
            )
            WHERE vehicle_id IS NULL
              AND placa IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users") or not inspector.has_table("vehicles"):
        return

    if _has_column(inspector, "users", "vehicle_id"):
        bind.execute(
            sa.text(
                """
                UPDATE users
                SET placa = (
                    SELECT vehicles.placa
                    FROM vehicles
                    WHERE vehicles.id = users.vehicle_id
                )
                WHERE vehicle_id IS NOT NULL
                """
            )
        )

    inspector = sa.inspect(bind)
    has_vehicle_id_column = _has_column(inspector, "users", "vehicle_id")
    has_vehicle_id_fk = _has_users_vehicle_id_fk(inspector)
    has_vehicle_id_index = _has_index(inspector, "users", "ix_users_vehicle_id")
    users_plate_fk_name = _find_users_plate_fk(inspector)

    with op.batch_alter_table("users") as batch_op:
        if not users_plate_fk_name:
            batch_op.create_foreign_key("fk_users_placa_vehicles", "vehicles", ["placa"], ["placa"])
        if has_vehicle_id_index:
            batch_op.drop_index("ix_users_vehicle_id")
        if has_vehicle_id_fk:
            batch_op.drop_constraint("fk_users_vehicle_id_vehicles", type_="foreignkey")
        if has_vehicle_id_column:
            batch_op.drop_column("vehicle_id")