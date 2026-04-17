"""add vehicles table and user transport fields

Revision ID: 0017_vehicles_user_transport
Revises: 0016_coordinate_update_frequency
Create Date: 2026-04-17 12:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0017_vehicles_user_transport"
down_revision = "0016_coordinate_update_frequency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("placa", sa.String(length=9), nullable=False),
        sa.Column("tipo", sa.String(length=16), nullable=False),
        sa.Column("lugares", sa.Integer(), nullable=False),
        sa.UniqueConstraint("placa", name="uq_vehicles_placa"),
        sa.CheckConstraint("tipo IN ('carro', 'minivan', 'van', 'onibus')", name="ck_vehicles_tipo_allowed"),
        sa.CheckConstraint("lugares >= 1 AND lugares <= 99", name="ck_vehicles_lugares_range"),
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("placa", sa.String(length=9), nullable=True))
        batch_op.add_column(sa.Column("end_rua", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("zip", sa.String(length=10), nullable=True))
        batch_op.create_foreign_key("fk_users_placa_vehicles", "vehicles", ["placa"], ["placa"])


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_placa_vehicles", type_="foreignkey")
        batch_op.drop_column("zip")
        batch_op.drop_column("end_rua")
        batch_op.drop_column("placa")

    op.drop_table("vehicles")
