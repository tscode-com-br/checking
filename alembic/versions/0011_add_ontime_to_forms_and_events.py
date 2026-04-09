"""add ontime to forms and events

Revision ID: 0011_ontime_forms_events
Revises: 0010_forms_rfid_nullable
Create Date: 2026-04-09 12:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_ontime_forms_events"
down_revision = "0010_forms_rfid_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        op.create_table(
            "check_events_new",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("idempotency_key", sa.String(length=80), nullable=False),
            sa.Column("source", sa.String(length=20), nullable=False),
            sa.Column("rfid", sa.String(length=64), nullable=True),
            sa.Column("action", sa.String(length=16), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("message", sa.String(length=255), nullable=False),
            sa.Column("details", sa.String(length=1000), nullable=True),
            sa.Column("project", sa.String(length=3), nullable=True),
            sa.Column("device_id", sa.String(length=80), nullable=True),
            sa.Column("local", sa.String(length=40), nullable=True),
            sa.Column("request_path", sa.String(length=120), nullable=True),
            sa.Column("http_status", sa.Integer(), nullable=True),
            sa.Column("ontime", sa.Boolean(), nullable=True),
            sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False),
            sa.UniqueConstraint("idempotency_key", name="uq_check_events_idempotency_key"),
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO check_events_new (
                    id, idempotency_key, source, rfid, action, status, message, details,
                    project, device_id, local, request_path, http_status, ontime,
                    event_time, submitted_at, retry_count
                )
                SELECT id, idempotency_key, source, rfid, action, status, message, details,
                       project, device_id, local, request_path, http_status,
                       CASE WHEN action IN ('checkin', 'checkout') THEN 1 ELSE NULL END,
                       event_time, submitted_at, retry_count
                FROM check_events
                """
            )
        )
        op.drop_table("check_events")
        op.rename_table("check_events_new", "check_events")

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
            sa.Column("ontime", sa.Boolean(), nullable=False, server_default=sa.text("1")),
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
                    id, request_id, rfid, action, chave, projeto, device_id, local, ontime,
                    status, retry_count, last_error, created_at, updated_at, processed_at
                )
                SELECT id, request_id, rfid, action, chave, projeto, device_id, local, 1,
                       status, retry_count, last_error, created_at, updated_at, processed_at
                FROM forms_submissions
                """
            )
        )
        op.drop_table("forms_submissions")
        op.rename_table("forms_submissions_new", "forms_submissions")

        op.create_table(
            "user_sync_events_new",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("chave", sa.String(length=4), nullable=False),
            sa.Column("rfid", sa.String(length=64), nullable=True),
            sa.Column("source", sa.String(length=20), nullable=False),
            sa.Column("action", sa.String(length=16), nullable=False),
            sa.Column("projeto", sa.String(length=3), nullable=True),
            sa.Column("local", sa.String(length=40), nullable=True),
            sa.Column("ontime", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source_request_id", sa.String(length=80), nullable=True),
            sa.Column("device_id", sa.String(length=80), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.UniqueConstraint("source", "source_request_id", name="uq_user_sync_events_source_request_id"),
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO user_sync_events_new (
                    id, user_id, chave, rfid, source, action, projeto, local, ontime,
                    event_time, created_at, source_request_id, device_id
                )
                SELECT id, user_id, chave, rfid, source, action, projeto, local, 1,
                       event_time, created_at, source_request_id, device_id
                FROM user_sync_events
                """
            )
        )
        op.drop_table("user_sync_events")
        op.rename_table("user_sync_events_new", "user_sync_events")
        return

    op.add_column("check_events", sa.Column("ontime", sa.Boolean(), nullable=True))
    op.add_column(
        "forms_submissions",
        sa.Column("ontime", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "user_sync_events",
        sa.Column("ontime", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    connection.execute(
        sa.text(
            """
            UPDATE check_events
            SET ontime = CASE WHEN action IN ('checkin', 'checkout') THEN true ELSE NULL END
            WHERE ontime IS NULL
            """
        )
    )
    connection.execute(sa.text("UPDATE forms_submissions SET ontime = true WHERE ontime IS NULL"))
    connection.execute(sa.text("UPDATE user_sync_events SET ontime = true WHERE ontime IS NULL"))
    op.alter_column("forms_submissions", "ontime", server_default=None)
    op.alter_column("user_sync_events", "ontime", server_default=None)


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        op.create_table(
            "user_sync_events_old",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
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
            sa.UniqueConstraint("source", "source_request_id", name="uq_user_sync_events_source_request_id"),
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO user_sync_events_old (
                    id, user_id, chave, rfid, source, action, projeto, local,
                    event_time, created_at, source_request_id, device_id
                )
                SELECT id, user_id, chave, rfid, source, action, projeto, local,
                       event_time, created_at, source_request_id, device_id
                FROM user_sync_events
                """
            )
        )
        op.drop_table("user_sync_events")
        op.rename_table("user_sync_events_old", "user_sync_events")

        op.create_table(
            "forms_submissions_old",
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

        op.create_table(
            "check_events_old",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("idempotency_key", sa.String(length=80), nullable=False),
            sa.Column("source", sa.String(length=20), nullable=False),
            sa.Column("rfid", sa.String(length=64), nullable=True),
            sa.Column("action", sa.String(length=16), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("message", sa.String(length=255), nullable=False),
            sa.Column("details", sa.String(length=1000), nullable=True),
            sa.Column("project", sa.String(length=3), nullable=True),
            sa.Column("device_id", sa.String(length=80), nullable=True),
            sa.Column("local", sa.String(length=40), nullable=True),
            sa.Column("request_path", sa.String(length=120), nullable=True),
            sa.Column("http_status", sa.Integer(), nullable=True),
            sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False),
            sa.UniqueConstraint("idempotency_key", name="uq_check_events_idempotency_key"),
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO check_events_old (
                    id, idempotency_key, source, rfid, action, status, message, details,
                    project, device_id, local, request_path, http_status,
                    event_time, submitted_at, retry_count
                )
                SELECT id, idempotency_key, source, rfid, action, status, message, details,
                       project, device_id, local, request_path, http_status,
                       event_time, submitted_at, retry_count
                FROM check_events
                """
            )
        )
        op.drop_table("check_events")
        op.rename_table("check_events_old", "check_events")
        return

    op.drop_column("user_sync_events", "ontime")
    op.drop_column("forms_submissions", "ontime")
    op.drop_column("check_events", "ontime")