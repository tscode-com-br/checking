"""add admin auth tables

Revision ID: 0008_add_admin_auth_tables
Revises: 0007_add_forms_submission_queue
Create Date: 2026-03-29 18:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_add_admin_auth_tables"
down_revision = "0007_add_forms_submission_queue"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chave", sa.String(length=4), nullable=False),
        sa.Column("nome_completo", sa.String(length=180), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("requires_password_reset", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("approved_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_reset_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chave", name="uq_admin_users_chave"),
    )

    op.create_table(
        "admin_access_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chave", sa.String(length=4), nullable=False),
        sa.Column("nome_completo", sa.String(length=180), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chave", name="uq_admin_access_requests_chave"),
    )


def downgrade() -> None:
    op.drop_table("admin_access_requests")
    op.drop_table("admin_users")