"""add accident tables (Modo Acidente Bloco B)

Revision ID: 0061_add_accident_tables
Revises: 0060_add_endpoint_api_keys
Create Date: 2026-05-19 00:00:00

This revision creates the five tables that back Modo Acidente:
    - accidents
    - accident_user_reports
    - accident_video_uploads
    - accident_archives
    - email_delivery_logs

The DDL mirrors `sistema/scripts/migrate_accidents_v1.sql`, which until now
was the only way to provision these tables. That manual script was never
executed against production, causing every check-in/check-out request to
fail when the accident hook queried the missing table and aborted the
surrounding Postgres transaction. Promoting the schema to an Alembic
revision lets `alembic upgrade head` self-heal production and any future
fresh environment.

Idempotent: each table is created only when `inspector.has_table(...)` is
false. This keeps the revision safe to re-run on hosts where the SQL file
may have been applied manually before this commit ships.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0061_add_accident_tables"
down_revision = "0060_add_endpoint_api_keys"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("accidents"):
        op.create_table(
            "accidents",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("accident_number", sa.Integer, nullable=False),
            sa.Column(
                "project_id",
                sa.Integer,
                sa.ForeignKey("projects.id"),
                nullable=False,
            ),
            sa.Column("project_name_snapshot", sa.String(120), nullable=False),
            sa.Column("location_name_snapshot", sa.String(120), nullable=False),
            sa.Column("location_is_registered", sa.Boolean, nullable=False),
            sa.Column("origin", sa.String(16), nullable=False),
            sa.Column(
                "opened_by_admin_id",
                sa.Integer,
                sa.ForeignKey("admin_users.id"),
                nullable=True,
            ),
            sa.Column(
                "opened_by_user_id",
                sa.Integer,
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "closed_by_admin_id",
                sa.Integer,
                sa.ForeignKey("admin_users.id"),
                nullable=True,
            ),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("archive_object_key", sa.String(512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "accident_number", name="uq_accidents_accident_number"
            ),
            sa.CheckConstraint(
                "origin IN ('admin', 'web')",
                name="ck_accidents_origin_allowed",
            ),
            sa.CheckConstraint(
                "accident_number >= 0",
                name="ck_accidents_number_non_negative",
            ),
            sa.CheckConstraint(
                "(opened_by_admin_id IS NOT NULL AND opened_by_user_id IS NULL) OR "
                "(opened_by_admin_id IS NULL AND opened_by_user_id IS NOT NULL)",
                name="ck_accidents_opened_by_actor_required",
            ),
        )
        # Partial unique index — at most one accident with closed_at IS NULL (active).
        op.create_index(
            "ix_accidents_single_active",
            "accidents",
            ["closed_at"],
            unique=True,
            postgresql_where=sa.text("closed_at IS NULL"),
            sqlite_where=sa.text("closed_at IS NULL"),
        )
        # Guard index (constant expression) to enforce single-active in all Postgres versions.
        op.create_index(
            "ix_accidents_single_active_guard",
            "accidents",
            [sa.text("(1)")],
            unique=True,
            postgresql_where=sa.text("closed_at IS NULL"),
            sqlite_where=sa.text("closed_at IS NULL"),
        )

    if not inspector.has_table("accident_user_reports"):
        op.create_table(
            "accident_user_reports",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "accident_id",
                sa.Integer,
                sa.ForeignKey("accidents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("user_chave_snapshot", sa.String(4), nullable=False),
            sa.Column("user_name_snapshot", sa.String(180), nullable=False),
            sa.Column("user_phone_snapshot", sa.String(40), nullable=True),
            sa.Column("user_projects_snapshot", sa.Text, nullable=False),
            sa.Column("user_local_snapshot", sa.String(120), nullable=False),
            sa.Column("zone", sa.String(16), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("reported_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_checkin_action", sa.String(16), nullable=True),
            sa.Column("last_action_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "accident_id",
                "user_id",
                name="uq_accident_user_reports_accident_id_user_id",
            ),
            sa.CheckConstraint(
                "zone IN ('waiting', 'safety', 'accident')",
                name="ck_accident_user_reports_zone_allowed",
            ),
            sa.CheckConstraint(
                "status IN ('waiting', 'ok', 'help')",
                name="ck_accident_user_reports_status_allowed",
            ),
        )

    if not inspector.has_table("accident_video_uploads"):
        op.create_table(
            "accident_video_uploads",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("idempotency_key", sa.String(120), nullable=False),
            sa.Column(
                "accident_id",
                sa.Integer,
                sa.ForeignKey("accidents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("object_key", sa.String(512), nullable=False),
            sa.Column("public_url", sa.String(1024), nullable=False),
            sa.Column("content_type", sa.String(120), nullable=False),
            sa.Column("size_bytes", sa.Integer, nullable=False),
            sa.Column("duration_seconds", sa.Integer, nullable=True),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "idempotency_key",
                name="uq_accident_video_uploads_idempotency_key",
            ),
        )
        op.create_index(
            "ix_accident_video_uploads_accident_user",
            "accident_video_uploads",
            ["accident_id", "user_id"],
        )

    if not inspector.has_table("accident_archives"):
        op.create_table(
            "accident_archives",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "accident_id",
                sa.Integer,
                sa.ForeignKey("accidents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("snapshot_json", sa.Text, nullable=False),
            sa.Column("xlsx_object_key", sa.String(512), nullable=False),
            sa.Column("zip_object_key", sa.String(512), nullable=False),
            sa.Column("size_bytes", sa.Integer, nullable=False),
            sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "accident_id", name="uq_accident_archives_accident_id"
            ),
        )

    if not inspector.has_table("email_delivery_logs"):
        op.create_table(
            "email_delivery_logs",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "accident_id",
                sa.Integer,
                sa.ForeignKey("accidents.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "triggered_by_user_id",
                sa.Integer,
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("recipient_email", sa.String(255), nullable=False),
            sa.Column("recipient_chave", sa.String(4), nullable=True),
            sa.Column("subject", sa.String(255), nullable=False),
            sa.Column("body_snapshot", sa.Text, nullable=False),
            sa.Column("delivery_status", sa.String(16), nullable=False),
            sa.Column("error_message", sa.String(1000), nullable=True),
            sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "retry_count", sa.Integer, nullable=False, server_default=sa.text("0")
            ),
            sa.CheckConstraint(
                "delivery_status IN ('queued', 'sent', 'failed')",
                name="ck_email_delivery_logs_status_allowed",
            ),
        )
        op.create_index(
            "ix_email_delivery_logs_accident",
            "email_delivery_logs",
            ["accident_id"],
        )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    # Drop child tables first to respect FK ordering. The CASCADE in the raw
    # SQL counterpart is implicit here because Alembic issues plain DROP
    # TABLE; on environments where FKs forbid the drop, Alembic raises and
    # the operator must resolve manually. The order below is safe in normal
    # circumstances.
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("accident_archives"):
        op.drop_table("accident_archives")

    if inspector.has_table("accident_video_uploads"):
        op.drop_index(
            "ix_accident_video_uploads_accident_user",
            table_name="accident_video_uploads",
        )
        op.drop_table("accident_video_uploads")

    if inspector.has_table("accident_user_reports"):
        op.drop_table("accident_user_reports")

    if inspector.has_table("email_delivery_logs"):
        op.drop_index(
            "ix_email_delivery_logs_accident",
            table_name="email_delivery_logs",
        )
        op.drop_table("email_delivery_logs")

    if inspector.has_table("accidents"):
        op.drop_index("ix_accidents_single_active_guard", table_name="accidents")
        op.drop_index("ix_accidents_single_active", table_name="accidents")
        op.drop_table("accidents")
