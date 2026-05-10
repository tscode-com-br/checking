"""add user project memberships

Revision ID: 0054_add_user_project_memberships
Revises: 0053_add_transport_ai_project_llm_settings
Create Date: 2026-05-07 16:15:00
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "0054_add_user_project_memberships"
down_revision = "0053_add_transport_ai_project_llm_settings"
branch_labels = None
depends_on = None


BOOTSTRAP_ADMIN_KEYS = {"UTO9", "CYMQ", "U32N", "RNA7", "U4ZR", "HR70"}
GLOBAL_MONITORED_SCOPE_MARKERS = {"ALL"}
DEFAULT_PROJECT_COUNTRY_CODE = "SG"
DEFAULT_PROJECT_COUNTRY_NAME = "Singapura"
DEFAULT_PROJECT_TIMEZONE_NAME = "Asia/Singapore"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_project_name(value: object) -> str | None:
    normalized = " ".join(str(value or "").strip().split()).upper()
    return normalized or None


def _normalize_admin_key(value: object) -> str:
    return str(value or "").strip().upper()


def _is_global_scope_marker(value: object) -> bool:
    normalized = _normalize_project_name(value)
    return normalized in GLOBAL_MONITORED_SCOPE_MARKERS


def _profile_digits(value: object) -> set[str]:
    normalized = str(value or "0").strip()
    return {character for character in normalized if character.isdigit() and character != "0"}


def _user_has_admin_access(user_row: dict[str, object]) -> bool:
    digits = _profile_digits(user_row.get("perfil"))
    return "1" in digits or "9" in digits


def _is_bootstrap_admin(user_row: dict[str, object]) -> bool:
    return _normalize_admin_key(user_row.get("chave")) in BOOTSTRAP_ADMIN_KEYS


def _is_global_monitored_scope(raw_value: object) -> bool:
    normalized_raw = str(raw_value or "").strip()
    if not normalized_raw:
        return False
    if _is_global_scope_marker(normalized_raw):
        return True

    try:
        parsed = json.loads(normalized_raw)
    except (TypeError, ValueError):
        return False

    if isinstance(parsed, list):
        return any(_is_global_scope_marker(item) for item in parsed)
    return _is_global_scope_marker(parsed)


def _extract_monitored_projects(raw_value: object) -> list[str] | None:
    normalized_raw = str(raw_value or "").strip()
    if not normalized_raw:
        return None
    if _is_global_monitored_scope(raw_value):
        return None

    try:
        parsed = json.loads(normalized_raw)
    except (TypeError, ValueError):
        return None

    if not isinstance(parsed, list):
        return None

    normalized_names: list[str] = []
    seen: set[str] = set()
    for item in parsed:
        normalized_name = _normalize_project_name(item)
        if normalized_name is None or normalized_name in seen:
            continue
        seen.add(normalized_name)
        normalized_names.append(normalized_name)

    if not normalized_names:
        return None

    return sorted(normalized_names)


def _collect_referenced_project_names(users_rows: list[dict[str, object]]) -> list[str]:
    project_names: set[str] = set()
    for user_row in users_rows:
        active_project = _normalize_project_name(user_row.get("projeto"))
        if active_project is not None:
            project_names.add(active_project)
        monitored_projects = _extract_monitored_projects(user_row.get("admin_monitored_projects_json"))
        if monitored_projects is not None:
            project_names.update(monitored_projects)
    return sorted(project_names)


def _load_tables(bind) -> tuple[sa.Table, sa.Table, sa.Table]:
    metadata = sa.MetaData()
    users = sa.Table("users", metadata, autoload_with=bind)
    projects = sa.Table("projects", metadata, autoload_with=bind)
    user_project_memberships = sa.Table("user_project_memberships", metadata, autoload_with=bind)
    return users, projects, user_project_memberships


def _ensure_project_rows(bind, projects: sa.Table, project_names: list[str]) -> None:
    if not project_names:
        return

    existing_names = {
        row[0]
        for row in bind.execute(
            sa.select(projects.c.name).where(projects.c.name.in_(project_names))
        ).all()
    }
    missing_names = [project_name for project_name in project_names if project_name not in existing_names]
    if not missing_names:
        return

    bind.execute(
        projects.insert(),
        [
            {
                "name": project_name,
                "country_code": DEFAULT_PROJECT_COUNTRY_CODE,
                "country_name": DEFAULT_PROJECT_COUNTRY_NAME,
                "timezone_name": DEFAULT_PROJECT_TIMEZONE_NAME,
                "address": "",
                "zip_code": "",
            }
            for project_name in missing_names
        ],
    )


def _project_ids_by_name(bind, projects: sa.Table) -> dict[str, int]:
    return {
        str(row.name): int(row.id)
        for row in bind.execute(
            sa.select(projects.c.id, projects.c.name).order_by(projects.c.name, projects.c.id)
        ).mappings().all()
    }


def _resolve_admin_membership_names(
    user_row: dict[str, object],
    all_project_names: list[str],
) -> list[str]:
    active_project = _normalize_project_name(user_row.get("projeto"))
    if _is_bootstrap_admin(user_row):
        return list(all_project_names)
    if _is_global_monitored_scope(user_row.get("admin_monitored_projects_json")):
        return list(all_project_names)

    monitored_projects = _extract_monitored_projects(user_row.get("admin_monitored_projects_json"))
    if monitored_projects is None:
        return list(all_project_names)

    monitored_project_set = set(monitored_projects)
    if set(all_project_names).issubset(monitored_project_set):
        return list(all_project_names)

    membership_names = set(monitored_projects)
    if active_project is not None:
        membership_names.add(active_project)
    if membership_names:
        return sorted(membership_names)
    return list(all_project_names)


def _build_membership_names_by_user_id(
    users_rows: list[dict[str, object]],
    all_project_names: list[str],
) -> dict[int, set[str]]:
    membership_names_by_user_id: dict[int, set[str]] = {}

    for user_row in users_rows:
        user_id = int(user_row["id"])
        active_project = _normalize_project_name(user_row.get("projeto"))
        if active_project is not None:
            membership_names_by_user_id.setdefault(user_id, set()).add(active_project)

    for user_row in users_rows:
        if not _user_has_admin_access(user_row) and not _is_bootstrap_admin(user_row):
            continue

        user_id = int(user_row["id"])
        membership_names = membership_names_by_user_id.setdefault(user_id, set())
        membership_names.update(_resolve_admin_membership_names(user_row, all_project_names))
        if membership_names:
            continue

        active_project = _normalize_project_name(user_row.get("projeto"))
        if active_project is not None:
            membership_names.add(active_project)
        membership_names.update(all_project_names)

    return membership_names_by_user_id


def _normalize_user_projects(bind, users: sa.Table) -> None:
    for user_row in bind.execute(
        sa.select(users.c.id, users.c.projeto).order_by(users.c.id)
    ).mappings().all():
        normalized_project = _normalize_project_name(user_row.get("projeto"))
        if normalized_project is None or normalized_project == user_row.get("projeto"):
            continue
        bind.execute(
            users.update()
            .where(users.c.id == user_row["id"])
            .values(projeto=normalized_project)
        )


def _backfill_memberships(bind, users: sa.Table, projects: sa.Table, user_project_memberships: sa.Table) -> None:
    users_rows = [
        dict(row)
        for row in bind.execute(
            sa.select(
                users.c.id,
                users.c.chave,
                users.c.perfil,
                users.c.projeto,
                users.c.admin_monitored_projects_json,
            ).order_by(users.c.id)
        ).mappings().all()
    ]

    referenced_project_names = _collect_referenced_project_names(users_rows)
    _ensure_project_rows(bind, projects, referenced_project_names)
    _normalize_user_projects(bind, users)

    users_rows = [
        dict(row)
        for row in bind.execute(
            sa.select(
                users.c.id,
                users.c.chave,
                users.c.perfil,
                users.c.projeto,
                users.c.admin_monitored_projects_json,
            ).order_by(users.c.id)
        ).mappings().all()
    ]
    all_project_names = sorted(_project_ids_by_name(bind, projects))
    project_id_by_name = _project_ids_by_name(bind, projects)
    membership_names_by_user_id = _build_membership_names_by_user_id(users_rows, all_project_names)
    existing_pairs = {
        (int(row.user_id), int(row.project_id))
        for row in bind.execute(
            sa.select(
                user_project_memberships.c.user_id,
                user_project_memberships.c.project_id,
            )
        ).mappings().all()
    }
    timestamp = _utcnow()
    rows_to_insert: list[dict[str, object]] = []

    for user_id, membership_names in membership_names_by_user_id.items():
        for membership_name in sorted(membership_names):
            project_id = project_id_by_name.get(membership_name)
            if project_id is None:
                continue
            pair = (user_id, project_id)
            if pair in existing_pairs:
                continue
            existing_pairs.add(pair)
            rows_to_insert.append(
                {
                    "user_id": user_id,
                    "project_id": project_id,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )

    if rows_to_insert:
        bind.execute(user_project_memberships.insert(), rows_to_insert)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users") or not inspector.has_table("projects"):
        return

    if not inspector.has_table("user_project_memberships"):
        op.create_table(
            "user_project_memberships",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "project_id",
                sa.Integer(),
                sa.ForeignKey("projects.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "user_id",
                "project_id",
                name="uq_user_project_memberships_user_id_project_id",
            ),
        )
        op.create_index(
            "ix_user_project_memberships_user_id",
            "user_project_memberships",
            ["user_id"],
        )
        op.create_index(
            "ix_user_project_memberships_project_id",
            "user_project_memberships",
            ["project_id"],
        )

    users, projects, user_project_memberships = _load_tables(bind)
    _backfill_memberships(bind, users, projects, user_project_memberships)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("user_project_memberships"):
        op.drop_table("user_project_memberships")
