"""make forms submission rfid nullable

Revision ID: 0010_forms_submission_rfid_nullable
Revises: 0009_mobile_user_sync
Create Date: 2026-04-08 17:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_forms_submission_rfid_nullable"
down_revision = "0009_mobile_user_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        op.create_table(
            "forms_submissions_new",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("request_id", sa.String(length=80), nullable=False),
            sa.Column("rfid", sa.String(length=64), nullable=True),
            sa.Column("action", sa.String(length=16), nullable=False),
            sa.Column("chave", sa.String(length=4), nullable=False),
            sa.Column("projeto", sa.String(length=3), nullable=False),
            sa.Column("device_id", sa.String(length=80), nullable=True),
            sa.Column("local", sa.String(length=40), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.String(length=1000), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("request_id", name="uq_forms_submissions_request_id"),
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO forms_submissions_new (
                    id, request_id, rfid, action, chave, projeto, device_id, local,
                    status, retry_count, last_error, created_at, updated_at, processed_at
                )
                SELECT id, request_id, rfid, action, chave, projeto, device_id, local,
                       status, retry_count, last_error, created_at, updated_at, processed_at
                FROM forms_submissions
                """
            )
        )
        op.drop_table("forms_submissions")
        op.rename_table("forms_submissions_new", "forms_submissions")
    else:
        op.alter_column("forms_submissions", "rfid", existing_type=sa.String(length=64), nullable=True)


def downgrade() -> None:
    connection = op.get_bind()
    mobile_without_rfid = connection.execute(
        sa.text("SELECT request_id FROM forms_submissions WHERE rfid IS NULL LIMIT 1")
    ).fetchone()
    if mobile_without_rfid is not None:
        raise RuntimeError(
            f"Cannot downgrade because forms submission {mobile_without_rfid[0]} has no RFID assigned"
        )

    if connection.dialect.name == "sqlite":
        op.create_table(
            "forms_submissions_old",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("request_id", sa.String(length=80), nullable=False),
            sa.Column("rfid", sa.String(length=64), nullable=False),
            sa.Column("action", sa.String(length=16), nullable=False),
            sa.Column("chave", sa.String(length=4), nullable=False),
            sa.Column("projeto", sa.String(length=3), nullable=False),
            sa.Column("device_id", sa.String(length=80), nullable=True),
            sa.Column("local", sa.String(length=40), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.String(length=1000), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("request_id", name="uq_forms_submissions_request_id"),
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO forms_submissions_old (
                    id, request_id, rfid, action, chave, projeto, device_id, local,
                    status, retry_count, last_error, created_at, updated_at, processed_at
                )
                SELECT id, request_id, rfid, action, chave, projeto, device_id, local,
                       status, retry_count, last_error, created_at, updated_at, processed_at
                FROM forms_submissions
                """
            )
        )
        op.drop_table("forms_submissions")
        op.rename_table("forms_submissions_old", "forms_submissions")
    else:
        op.alter_column("forms_submissions", "rfid", existing_type=sa.String(length=64), nullable=False)