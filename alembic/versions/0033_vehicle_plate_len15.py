"""expand vehicle plate length to 15 characters

Revision ID: 0033_vehicle_plate_len15
Revises: 0032_transport_seat_defaults
Create Date: 2026-04-22 20:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0033_vehicle_plate_len15"
down_revision = "0032_transport_seat_defaults"
branch_labels = None
depends_on = None


def _column_length(columns: list[dict[str, object]], column_name: str) -> int | None:
    for column in columns:
        if column.get("name") != column_name:
            continue
        return getattr(column.get("type"), "length", None)
    return None


def _get_user_plate_fk_names(inspector: sa.Inspector) -> list[str]:
    if not inspector.has_table("users"):
        return []

    fk_names: list[str] = []
    for foreign_key in inspector.get_foreign_keys("users"):
        if foreign_key.get("referred_table") != "vehicles":
            continue
        if foreign_key.get("constrained_columns") != ["placa"]:
            continue
        fk_name = foreign_key.get("name")
        if fk_name:
            fk_names.append(str(fk_name))
    return fk_names


def _ensure_no_overlong_vehicle_plates(bind) -> None:
    overlong_vehicle_plate = bind.execute(sa.text("SELECT placa FROM vehicles WHERE LENGTH(placa) > 9 LIMIT 1")).scalar()
    if overlong_vehicle_plate:
        raise RuntimeError("Cannot downgrade vehicles.placa to 9 characters while longer vehicle plates exist.")

    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "placa" not in user_columns:
        return

    overlong_user_plate = bind.execute(sa.text("SELECT placa FROM users WHERE placa IS NOT NULL AND LENGTH(placa) > 9 LIMIT 1")).scalar()
    if overlong_user_plate:
        raise RuntimeError("Cannot downgrade users.placa to 9 characters while longer user plate references exist.")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("vehicles"):
        return

    user_plate_fk_names = _get_user_plate_fk_names(inspector)
    vehicle_columns = inspector.get_columns("vehicles")
    vehicle_plate_length = _column_length(vehicle_columns, "placa") or 9

    has_users_table = inspector.has_table("users")
    user_columns = inspector.get_columns("users") if has_users_table else []
    user_plate_length = _column_length(user_columns, "placa")

    if user_plate_fk_names:
        with op.batch_alter_table("users") as batch_op:
            for fk_name in user_plate_fk_names:
                batch_op.drop_constraint(fk_name, type_="foreignkey")

    if vehicle_plate_length != 15:
        with op.batch_alter_table("vehicles") as batch_op:
            batch_op.alter_column(
                "placa",
                existing_type=sa.String(length=vehicle_plate_length),
                type_=sa.String(length=15),
                existing_nullable=False,
            )

    if has_users_table and user_plate_length is not None and user_plate_length != 15:
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "placa",
                existing_type=sa.String(length=user_plate_length),
                type_=sa.String(length=15),
                existing_nullable=True,
            )

    inspector = sa.inspect(bind)
    if inspector.has_table("users"):
        current_user_columns = {column["name"] for column in inspector.get_columns("users")}
        current_fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("users") if fk.get("name")}
        if "placa" in current_user_columns and "fk_users_placa_vehicles" not in current_fk_names:
            with op.batch_alter_table("users") as batch_op:
                batch_op.create_foreign_key("fk_users_placa_vehicles", "vehicles", ["placa"], ["placa"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("vehicles"):
        return

    _ensure_no_overlong_vehicle_plates(bind)

    user_plate_fk_names = _get_user_plate_fk_names(inspector)
    vehicle_columns = inspector.get_columns("vehicles")
    vehicle_plate_length = _column_length(vehicle_columns, "placa") or 15

    has_users_table = inspector.has_table("users")
    user_columns = inspector.get_columns("users") if has_users_table else []
    user_plate_length = _column_length(user_columns, "placa")

    if user_plate_fk_names:
        with op.batch_alter_table("users") as batch_op:
            for fk_name in user_plate_fk_names:
                batch_op.drop_constraint(fk_name, type_="foreignkey")

    if has_users_table and user_plate_length is not None and user_plate_length != 9:
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "placa",
                existing_type=sa.String(length=user_plate_length),
                type_=sa.String(length=9),
                existing_nullable=True,
            )

    if vehicle_plate_length != 9:
        with op.batch_alter_table("vehicles") as batch_op:
            batch_op.alter_column(
                "placa",
                existing_type=sa.String(length=vehicle_plate_length),
                type_=sa.String(length=9),
                existing_nullable=False,
            )

    inspector = sa.inspect(bind)
    if inspector.has_table("users"):
        current_user_columns = {column["name"] for column in inspector.get_columns("users")}
        current_fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("users") if fk.get("name")}
        if "placa" in current_user_columns and "fk_users_placa_vehicles" not in current_fk_names:
            with op.batch_alter_table("users") as batch_op:
                batch_op.create_foreign_key("fk_users_placa_vehicles", "vehicles", ["placa"], ["placa"])