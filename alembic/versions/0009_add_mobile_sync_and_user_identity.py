"""add mobile sync and user identity

Revision ID: 0009_mobile_user_sync
Revises: 0008_add_admin_auth_tables
Create Date: 2026-04-06 15:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_mobile_user_sync"
down_revision = "0008_add_admin_auth_tables"
branch_labels = None
depends_on = None


def _assert_unique_user_keys(connection) -> None:
    duplicate = connection.execute(
        sa.text("SELECT chave FROM users GROUP BY chave HAVING COUNT(*) > 1 LIMIT 1")
    ).fetchone()
    if duplicate is not None:
        raise RuntimeError(f"Cannot migrate users table because chave {duplicate[0]} is duplicated")


def upgrade() -> None:
    connection = op.get_bind()
    dialect_name = connection.dialect.name
    _assert_unique_user_keys(connection)

    op.create_table(
        "users_new",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rfid", sa.String(length=64), nullable=True),
        sa.Column("chave", sa.String(length=4), nullable=False),
        sa.Column("nome", sa.String(length=180), nullable=False),
        sa.Column("projeto", sa.String(length=3), nullable=False),
        sa.Column("local", sa.String(length=40), nullable=True),
        sa.Column("checkin", sa.Boolean(), nullable=True),
        sa.Column("time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inactivity_days", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO users_new (rfid, chave, nome, projeto, local, checkin, time, last_active_at, inactivity_days)
            SELECT rfid, chave, nome, projeto, local, checkin, time, last_active_at, inactivity_days
            FROM users
            """
        )
    )
    op.drop_table("users")
    op.rename_table("users_new", "users")
    if dialect_name == "sqlite":
        op.create_index("ix_users_rfid_unique", "users", ["rfid"], unique=True)
        op.create_index("ix_users_chave_unique", "users", ["chave"], unique=True)
    else:
        op.create_unique_constraint("uq_users_rfid", "users", ["rfid"])
        op.create_unique_constraint("uq_users_chave", "users", ["chave"])

    op.create_table(
        "user_sync_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chave", sa.String(length=4), nullable=False),
        sa.Column("rfid", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("projeto", sa.String(length=3), nullable=True),
        sa.Column("local", sa.String(length=40), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_request_id", sa.String(length=80), nullable=True),
        sa.Column("device_id", sa.String(length=80), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_request_id", name="uq_user_sync_events_source_request_id"),
    )


def downgrade() -> None:
    connection = op.get_bind()
    dialect_name = connection.dialect.name
    user_without_rfid = connection.execute(
        sa.text("SELECT chave FROM users WHERE rfid IS NULL LIMIT 1")
    ).fetchone()
    if user_without_rfid is not None:
        raise RuntimeError(
            f"Cannot downgrade because user with chave {user_without_rfid[0]} has no RFID assigned"
        )

    op.drop_table("user_sync_events")

    op.create_table(
        "users_old",
        sa.Column("rfid", sa.String(length=64), nullable=False),
        sa.Column("chave", sa.String(length=4), nullable=False),
        sa.Column("nome", sa.String(length=180), nullable=False),
        sa.Column("projeto", sa.String(length=3), nullable=False),
        sa.Column("local", sa.String(length=40), nullable=True),
        sa.Column("checkin", sa.Boolean(), nullable=True),
        sa.Column("time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inactivity_days", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("rfid"),
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO users_old (rfid, chave, nome, projeto, local, checkin, time, last_active_at, inactivity_days)
            SELECT rfid, chave, nome, projeto, local, checkin, time, last_active_at, inactivity_days
            FROM users
            """
        )
    )
    if dialect_name == "sqlite":
        op.drop_index("ix_users_chave_unique", table_name="users")
        op.drop_index("ix_users_rfid_unique", table_name="users")
    else:
        op.drop_constraint("uq_users_chave", "users", type_="unique")
        op.drop_constraint("uq_users_rfid", "users", type_="unique")
    op.drop_table("users")
    op.rename_table("users_old", "users")