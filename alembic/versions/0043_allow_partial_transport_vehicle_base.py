"""allow partial transport vehicle base data

Revision ID: 0043_allow_partial_transport_vehicle_base
Revises: 0042_add_transport_workplace_context_and_time_policy
Create Date: 2026-04-29 20:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0043_allow_partial_transport_vehicle_base"
down_revision = "0042_add_transport_workplace_context_and_time_policy"
branch_labels = None
depends_on = None


LEGACY_UNIQUE_NAME = "uq_vehicles_placa"
PARTIAL_INDEX_NAME = "ix_vehicles_placa_present_unique"


def _has_named_constraint(inspector: sa.Inspector, table_name: str, constraint_name: str, *, kind: str) -> bool:
    try:
        if kind == "check":
            constraints = inspector.get_check_constraints(table_name)
        elif kind == "unique":
            constraints = inspector.get_unique_constraints(table_name)
        else:
            return False
    except Exception:
        return False

    return any(constraint.get("name") == constraint_name for constraint in constraints)


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    try:
        return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))
    except Exception:
        return False


def _column_by_name(inspector: sa.Inspector, table_name: str) -> dict[str, dict[str, object]]:
    try:
        return {column["name"]: column for column in inspector.get_columns(table_name)}
    except Exception:
        return {}


def _assert_no_partial_vehicle_rows(bind) -> None:
    has_partial_rows = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM vehicles
            WHERE placa IS NULL
               OR tipo IS NULL
               OR lugares IS NULL
               OR tolerance IS NULL
            LIMIT 1
            """
        )
    ).scalar()
    if has_partial_rows:
        raise RuntimeError(
            "Cannot downgrade transport vehicles while partial vehicle rows still exist. "
            "Fill placa, tipo, lugares and tolerance first."
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("vehicles"):
        return

    vehicle_columns = _column_by_name(inspector, "vehicles")

    with op.batch_alter_table("vehicles") as batch_op:
        if _has_named_constraint(inspector, "vehicles", LEGACY_UNIQUE_NAME, kind="unique"):
            batch_op.drop_constraint(LEGACY_UNIQUE_NAME, type_="unique")

        for constraint_name in (
            "ck_vehicles_tipo_allowed",
            "ck_vehicles_lugares_range",
            "ck_vehicles_tolerance_range",
        ):
            if _has_named_constraint(inspector, "vehicles", constraint_name, kind="check"):
                batch_op.drop_constraint(constraint_name, type_="check")

        if "placa" in vehicle_columns and not bool(vehicle_columns["placa"].get("nullable", False)):
            batch_op.alter_column(
                "placa",
                existing_type=vehicle_columns["placa"]["type"],
                nullable=True,
            )
        if "tipo" in vehicle_columns and not bool(vehicle_columns["tipo"].get("nullable", False)):
            batch_op.alter_column(
                "tipo",
                existing_type=vehicle_columns["tipo"]["type"],
                nullable=True,
            )
        if "lugares" in vehicle_columns and not bool(vehicle_columns["lugares"].get("nullable", False)):
            batch_op.alter_column(
                "lugares",
                existing_type=vehicle_columns["lugares"]["type"],
                nullable=True,
            )
        if "tolerance" in vehicle_columns and not bool(vehicle_columns["tolerance"].get("nullable", False)):
            batch_op.alter_column(
                "tolerance",
                existing_type=vehicle_columns["tolerance"]["type"],
                nullable=True,
            )

        batch_op.create_check_constraint(
            "ck_vehicles_tipo_allowed",
            "tipo IS NULL OR tipo IN ('carro', 'minivan', 'van', 'onibus')",
        )
        batch_op.create_check_constraint(
            "ck_vehicles_lugares_range",
            "lugares IS NULL OR (lugares >= 1 AND lugares <= 99)",
        )
        batch_op.create_check_constraint(
            "ck_vehicles_tolerance_range",
            "tolerance IS NULL OR (tolerance >= 0 AND tolerance <= 240)",
        )

    inspector = sa.inspect(bind)
    if not _has_index(inspector, "vehicles", PARTIAL_INDEX_NAME):
        op.create_index(
            PARTIAL_INDEX_NAME,
            "vehicles",
            ["placa"],
            unique=True,
            sqlite_where=sa.text("placa IS NOT NULL"),
            postgresql_where=sa.text("placa IS NOT NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("vehicles"):
        return

    _assert_no_partial_vehicle_rows(bind)

    if _has_index(inspector, "vehicles", PARTIAL_INDEX_NAME):
        op.drop_index(PARTIAL_INDEX_NAME, table_name="vehicles")

    inspector = sa.inspect(bind)
    vehicle_columns = _column_by_name(inspector, "vehicles")

    with op.batch_alter_table("vehicles") as batch_op:
        for constraint_name in (
            "ck_vehicles_tipo_allowed",
            "ck_vehicles_lugares_range",
            "ck_vehicles_tolerance_range",
        ):
            if _has_named_constraint(inspector, "vehicles", constraint_name, kind="check"):
                batch_op.drop_constraint(constraint_name, type_="check")

        batch_op.create_check_constraint(
            "ck_vehicles_tipo_allowed",
            "tipo IN ('carro', 'minivan', 'van', 'onibus')",
        )
        batch_op.create_check_constraint(
            "ck_vehicles_lugares_range",
            "lugares >= 1 AND lugares <= 99",
        )
        batch_op.create_check_constraint(
            "ck_vehicles_tolerance_range",
            "tolerance >= 0 AND tolerance <= 240",
        )

        if "placa" in vehicle_columns and bool(vehicle_columns["placa"].get("nullable", True)):
            batch_op.alter_column(
                "placa",
                existing_type=vehicle_columns["placa"]["type"],
                nullable=False,
            )
        if "tipo" in vehicle_columns and bool(vehicle_columns["tipo"].get("nullable", True)):
            batch_op.alter_column(
                "tipo",
                existing_type=vehicle_columns["tipo"]["type"],
                nullable=False,
            )
        if "lugares" in vehicle_columns and bool(vehicle_columns["lugares"].get("nullable", True)):
            batch_op.alter_column(
                "lugares",
                existing_type=vehicle_columns["lugares"]["type"],
                nullable=False,
            )
        if "tolerance" in vehicle_columns and bool(vehicle_columns["tolerance"].get("nullable", True)):
            batch_op.alter_column(
                "tolerance",
                existing_type=vehicle_columns["tolerance"]["type"],
                nullable=False,
            )

        if not _has_named_constraint(inspector, "vehicles", LEGACY_UNIQUE_NAME, kind="unique"):
            batch_op.create_unique_constraint(LEGACY_UNIQUE_NAME, ["placa"])