from __future__ import annotations

import json
from collections.abc import Iterable

from ..models import User
from .project_catalog import normalize_project_name


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