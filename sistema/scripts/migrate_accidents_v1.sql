-- Migration: accidents v1
-- Apply via: psql $DATABASE_URL -f migrate_accidents_v1.sql
-- Idempotent: uses IF NOT EXISTS where possible.
--
-- Tables created:
--   accidents
--   accident_user_reports
--   accident_video_uploads
--   accident_archives
--   email_delivery_logs
--
-- Prerequisites: tables projects, users, admin_users must already exist.

-- ------------------------------------------------------------
-- accidents
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS accidents (
    id                      SERIAL PRIMARY KEY,
    accident_number         INTEGER NOT NULL,
    project_id              INTEGER NOT NULL
                                REFERENCES projects (id),
    project_name_snapshot   VARCHAR(120) NOT NULL,
    location_name_snapshot  VARCHAR(120) NOT NULL,
    location_is_registered  BOOLEAN NOT NULL,
    origin                  VARCHAR(16) NOT NULL,
    opened_by_admin_id      INTEGER
                                REFERENCES admin_users (id),
    opened_by_user_id       INTEGER
                                REFERENCES users (id),
    opened_at               TIMESTAMPTZ NOT NULL,
    closed_by_admin_id      INTEGER
                                REFERENCES admin_users (id),
    closed_at               TIMESTAMPTZ,
    archive_object_key      VARCHAR(512),
    created_at              TIMESTAMPTZ NOT NULL,
    updated_at              TIMESTAMPTZ NOT NULL,

    CONSTRAINT uq_accidents_accident_number
        UNIQUE (accident_number),

    CONSTRAINT ck_accidents_origin_allowed
        CHECK (origin IN ('admin', 'web')),

    CONSTRAINT ck_accidents_number_non_negative
        CHECK (accident_number >= 0),

    CONSTRAINT ck_accidents_opened_by_actor_required
        CHECK (
            (opened_by_admin_id IS NOT NULL AND opened_by_user_id IS NULL)
            OR
            (opened_by_admin_id IS NULL  AND opened_by_user_id IS NOT NULL)
        )
);

-- Partial unique index: at most one accident with closed_at IS NULL (active).
CREATE UNIQUE INDEX IF NOT EXISTS ix_accidents_single_active
    ON accidents (closed_at)
    WHERE closed_at IS NULL;

-- Guard index (constant expression) to enforce single-active in all Postgres versions.
CREATE UNIQUE INDEX IF NOT EXISTS ix_accidents_single_active_guard
    ON accidents ((1))
    WHERE closed_at IS NULL;

-- ------------------------------------------------------------
-- accident_user_reports
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS accident_user_reports (
    id                      SERIAL PRIMARY KEY,
    accident_id             INTEGER NOT NULL
                                REFERENCES accidents (id) ON DELETE CASCADE,
    user_id                 INTEGER NOT NULL
                                REFERENCES users (id),
    user_chave_snapshot     VARCHAR(4) NOT NULL,
    user_name_snapshot      VARCHAR(180) NOT NULL,
    user_phone_snapshot     VARCHAR(40),
    user_projects_snapshot  TEXT NOT NULL,
    user_local_snapshot     VARCHAR(120) NOT NULL,
    zone                    VARCHAR(16) NOT NULL,
    status                  VARCHAR(16) NOT NULL,
    reported_at             TIMESTAMPTZ,
    last_checkin_action     VARCHAR(16),
    last_action_at          TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL,
    updated_at              TIMESTAMPTZ NOT NULL,

    CONSTRAINT uq_accident_user_reports_accident_id_user_id
        UNIQUE (accident_id, user_id),

    CONSTRAINT ck_accident_user_reports_zone_allowed
        CHECK (zone IN ('waiting', 'safety', 'accident')),

    CONSTRAINT ck_accident_user_reports_status_allowed
        CHECK (status IN ('waiting', 'ok', 'help'))
);

-- ------------------------------------------------------------
-- accident_video_uploads
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS accident_video_uploads (
    id                  SERIAL PRIMARY KEY,
    idempotency_key     VARCHAR(120) NOT NULL,
    accident_id         INTEGER NOT NULL
                            REFERENCES accidents (id) ON DELETE CASCADE,
    user_id             INTEGER NOT NULL
                            REFERENCES users (id),
    object_key          VARCHAR(512) NOT NULL,
    public_url          VARCHAR(1024) NOT NULL,
    content_type        VARCHAR(120) NOT NULL,
    size_bytes          INTEGER NOT NULL,
    duration_seconds    INTEGER,
    captured_at         TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL,

    CONSTRAINT uq_accident_video_uploads_idempotency_key
        UNIQUE (idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_accident_video_uploads_accident_user
    ON accident_video_uploads (accident_id, user_id);

-- ------------------------------------------------------------
-- accident_archives
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS accident_archives (
    id                  SERIAL PRIMARY KEY,
    accident_id         INTEGER NOT NULL
                            REFERENCES accidents (id) ON DELETE CASCADE,
    snapshot_json       TEXT NOT NULL,
    xlsx_object_key     VARCHAR(512) NOT NULL,
    zip_object_key      VARCHAR(512) NOT NULL,
    size_bytes          INTEGER NOT NULL,
    generated_at        TIMESTAMPTZ NOT NULL,

    CONSTRAINT uq_accident_archives_accident_id
        UNIQUE (accident_id)
);

-- ------------------------------------------------------------
-- email_delivery_logs
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS email_delivery_logs (
    id                      SERIAL PRIMARY KEY,
    accident_id             INTEGER
                                REFERENCES accidents (id) ON DELETE SET NULL,
    triggered_by_user_id    INTEGER
                                REFERENCES users (id),
    recipient_email         VARCHAR(255) NOT NULL,
    recipient_chave         VARCHAR(4),
    subject                 VARCHAR(255) NOT NULL,
    body_snapshot           TEXT NOT NULL,
    delivery_status         VARCHAR(16) NOT NULL,
    error_message           VARCHAR(1000),
    queued_at               TIMESTAMPTZ NOT NULL,
    sent_at                 TIMESTAMPTZ,
    retry_count             INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT ck_email_delivery_logs_status_allowed
        CHECK (delivery_status IN ('queued', 'sent', 'failed'))
);

CREATE INDEX IF NOT EXISTS ix_email_delivery_logs_accident
    ON email_delivery_logs (accident_id);

-- ------------------------------------------------------------
-- Rollback (use with caution):
-- DROP TABLE accident_archives, accident_video_uploads, accident_user_reports,
--   email_delivery_logs, accidents CASCADE;
-- ------------------------------------------------------------
