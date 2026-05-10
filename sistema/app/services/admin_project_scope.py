from __future__ import annotations

import json
from collections.abc import Iterable

from sqlalchemy.orm import Session

from ..models import User
from .project_catalog import normalize_project_name
from .user_projects import (
    list_materialized_user_project_names,
    list_user_project_names,
    normalize_user_project_names,
)


def normalize_admin_monitored_project_names(project_names: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for project_name in project_names:
        normalized_name = normalize_project_name(
            project_name,
            field_name="O projeto monitorado do administrador",
        )
        if normalized_name in seen:
            continue
        seen.add(normalized_name)
        normalized.append(normalized_name)
    return sorted(normalized)


def dump_admin_monitored_projects(project_names: Iterable[str]) -> str:
    normalized = normalize_admin_monitored_project_names(project_names)
    return json.dumps(normalized, ensure_ascii=True, separators=(",", ":"))


def extract_admin_monitored_projects(user: User) -> list[str] | None:
    if not str(user.admin_monitored_projects_json or "").strip():
        return None

    try:
        raw_items = json.loads(user.admin_monitored_projects_json)
    except (TypeError, ValueError):
        return None

    if not isinstance(raw_items, list):
        return None

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        if item is None:
            continue
        try:
            normalized_name = normalize_project_name(
                str(item),
                field_name="O projeto monitorado do administrador",
            )
        except ValueError:
            continue
        if normalized_name in seen:
            continue
        seen.add(normalized_name)
        normalized.append(normalized_name)

    if not normalized:
        return None

    return sorted(normalized)


def resolve_effective_admin_monitored_projects(
    user: User,
    all_project_names: Iterable[str],
) -> list[str] | None:
    explicit_projects = extract_admin_monitored_projects(user)
    if explicit_projects is None:
        return None

    allowed_projects = set(normalize_admin_monitored_project_names(all_project_names))
    return [project_name for project_name in explicit_projects if project_name in allowed_projects]


def admin_monitors_project(
    user: User,
    project_name: str | None,
    all_project_names: Iterable[str],
) -> bool:
    normalized_project = str(project_name or "").strip()
    if not normalized_project:
        return False

    try:
        normalized_project = normalize_project_name(normalized_project, field_name="O projeto do usuário")
    except ValueError:
        return False

    effective_projects = resolve_effective_admin_monitored_projects(user, all_project_names)
    if effective_projects is None:
        return True
    return normalized_project in set(effective_projects)


def resolve_effective_admin_project_names(
    db: Session,
    user: User | None,
) -> list[str] | None:
    if user is None:
        return None
    return list_materialized_user_project_names(db, user)


def _resolve_effective_admin_project_set(
    db: Session,
    current_admin: User | None,
    *,
    admin_project_names: Iterable[str] | None = None,
) -> set[str] | None:
    if current_admin is None:
        return None

    resolved_names = (
        normalize_user_project_names(
            admin_project_names,
            field_name="O projeto do administrador",
        )
        if admin_project_names is not None
        else resolve_effective_admin_project_names(db, current_admin) or []
    )
    return set(resolved_names)


def user_matches_effective_admin_scope(
    db: Session,
    current_admin: User | None,
    user: User,
    *,
    admin_project_names: Iterable[str] | None = None,
    user_project_names: Iterable[str] | None = None,
) -> bool:
    effective_admin_projects = _resolve_effective_admin_project_set(
        db,
        current_admin,
        admin_project_names=admin_project_names,
    )
    if effective_admin_projects is None:
        return True
    if not effective_admin_projects:
        return False

    resolved_user_projects = normalize_user_project_names(
        user_project_names if user_project_names is not None else list_user_project_names(db, user),
        field_name="O projeto do usuário",
    )
    return bool(effective_admin_projects.intersection(resolved_user_projects))


def project_matches_effective_admin_scope(
    db: Session,
    current_admin: User | None,
    project_name: str | None,
    *,
    admin_project_names: Iterable[str] | None = None,
    allow_blank: bool = True,
) -> bool:
    effective_admin_projects = _resolve_effective_admin_project_set(
        db,
        current_admin,
        admin_project_names=admin_project_names,
    )
    if effective_admin_projects is None:
        return True
    if not effective_admin_projects:
        return False

    normalized_project = str(project_name or "").strip()
    if not normalized_project:
        return allow_blank

    try:
        normalized_project = normalize_project_name(normalized_project, field_name="O projeto do registro")
    except ValueError:
        return False
    return normalized_project in effective_admin_projects


def location_matches_effective_admin_scope(
    db: Session,
    current_admin: User | None,
    project_names: Iterable[str],
    *,
    admin_project_names: Iterable[str] | None = None,
    allow_global_locations: bool = True,
) -> bool:
    effective_admin_projects = _resolve_effective_admin_project_set(
        db,
        current_admin,
        admin_project_names=admin_project_names,
    )
    if effective_admin_projects is None:
        return True
    if not effective_admin_projects:
        return False

    resolved_location_projects = normalize_user_project_names(
        project_names,
        field_name="O projeto da localizacao",
    )
    if not resolved_location_projects:
        return allow_global_locations
    return bool(effective_admin_projects.intersection(resolved_location_projects))
