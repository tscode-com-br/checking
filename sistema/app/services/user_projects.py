from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Project, User, UserProjectMembership
from .project_catalog import normalize_project_name
from .time_utils import now_sgt


def normalize_user_project_names(
    project_names: Iterable[str],
    *,
    field_name: str = "O projeto do usuário",
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for project_name in project_names:
        normalized_name = normalize_project_name(project_name, field_name=field_name)
        if normalized_name in seen:
            continue
        seen.add(normalized_name)
        normalized.append(normalized_name)
    return sorted(normalized)


def _normalize_optional_project_name(
    value: str | None,
    *,
    field_name: str = "O projeto do usuário",
) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    return normalize_project_name(normalized, field_name=field_name)


def _require_persisted_user(user: User) -> None:
    if user.id is None:
        raise ValueError("O usuário precisa estar persistido antes de alterar memberships")


def _list_materialized_project_names(db: Session, user: User) -> list[str]:
    _require_persisted_user(user)
    return db.execute(
        select(Project.name)
        .join(UserProjectMembership, UserProjectMembership.project_id == Project.id)
        .where(UserProjectMembership.user_id == user.id)
        .order_by(Project.name, Project.id, UserProjectMembership.id)
    ).scalars().all()


def list_materialized_user_project_names(db: Session, user: User) -> list[str]:
    return _list_materialized_project_names(db, user)


def _require_projects_by_name(db: Session, project_names: Sequence[str]) -> dict[str, Project]:
    normalized_names = normalize_user_project_names(project_names)
    if not normalized_names:
        return {}

    rows = db.execute(
        select(Project)
        .where(Project.name.in_(normalized_names))
        .order_by(Project.name, Project.id)
    ).scalars().all()
    project_by_name = {project.name: project for project in rows}
    missing_names = [project_name for project_name in normalized_names if project_name not in project_by_name]
    if missing_names:
        raise ValueError(
            f"Projetos nao encontrados para o vínculo do usuário: {', '.join(missing_names)}"
        )
    return project_by_name


def list_user_project_names(db: Session, user: User) -> list[str]:
    materialized_names = _list_materialized_project_names(db, user)
    if materialized_names:
        return materialized_names

    legacy_active_project = _normalize_optional_project_name(
        user.projeto,
        field_name="O projeto ativo do usuário",
    )
    if legacy_active_project is None:
        return []
    return [legacy_active_project]


def list_user_project_names_map(db: Session, users: Sequence[User]) -> dict[int, list[str]]:
    persisted_users = [user for user in users if user.id is not None]
    if not persisted_users:
        return {}

    user_ids = [user.id for user in persisted_users if user.id is not None]
    rows = db.execute(
        select(UserProjectMembership.user_id, Project.name)
        .join(Project, Project.id == UserProjectMembership.project_id)
        .where(UserProjectMembership.user_id.in_(user_ids))
        .order_by(UserProjectMembership.user_id, Project.name, Project.id, UserProjectMembership.id)
    ).all()

    project_names_by_user_id: dict[int, list[str]] = {user_id: [] for user_id in user_ids}
    for user_id, project_name in rows:
        project_names_by_user_id[user_id].append(project_name)

    for user in persisted_users:
        if user.id is None:
            continue
        if project_names_by_user_id[user.id]:
            continue
        legacy_active_project = _normalize_optional_project_name(
            user.projeto,
            field_name="O projeto ativo do usuário",
        )
        project_names_by_user_id[user.id] = [legacy_active_project] if legacy_active_project is not None else []

    return project_names_by_user_id


def resolve_user_active_project(
    user: User,
    project_names: Sequence[str] | None = None,
) -> str:
    normalized_project_names = normalize_user_project_names(project_names or ())
    current_active_project = _normalize_optional_project_name(
        user.projeto,
        field_name="O projeto ativo do usuário",
    )

    if not normalized_project_names:
        if current_active_project is None:
            raise ValueError("O usuário precisa ter ao menos um projeto vinculado")
        return current_active_project

    if current_active_project in set(normalized_project_names):
        return current_active_project
    return normalized_project_names[0]


def replace_user_project_memberships(
    db: Session,
    user: User,
    project_names: Iterable[str],
) -> list[str]:
    _require_persisted_user(user)
    normalized_project_names = normalize_user_project_names(project_names)
    if not normalized_project_names:
        raise ValueError("O usuário precisa permanecer vinculado a ao menos um projeto")

    project_by_name = _require_projects_by_name(db, normalized_project_names)
    existing_memberships = db.execute(
        select(UserProjectMembership)
        .where(UserProjectMembership.user_id == user.id)
        .order_by(UserProjectMembership.id)
    ).scalars().all()
    existing_membership_by_project_id = {
        membership.project_id: membership for membership in existing_memberships
    }
    desired_project_ids = {project_by_name[project_name].id for project_name in normalized_project_names}
    timestamp = now_sgt()

    for membership in existing_memberships:
        if membership.project_id in desired_project_ids:
            membership.updated_at = timestamp
            continue
        db.delete(membership)

    for project_name in normalized_project_names:
        project = project_by_name[project_name]
        if project.id in existing_membership_by_project_id:
            continue
        db.add(
            UserProjectMembership(
                user_id=user.id,
                project_id=project.id,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )

    user.projeto = resolve_user_active_project(user, normalized_project_names)
    db.flush()
    return normalized_project_names


def add_user_project_membership(db: Session, user: User, project_name: str) -> list[str]:
    current_project_names = list_user_project_names(db, user)
    return replace_user_project_memberships(db, user, [*current_project_names, project_name])


def assign_user_active_project(db: Session, user: User, project_name: str) -> list[str]:
    normalized_project_name = normalize_project_name(
        project_name,
        field_name="O projeto ativo do usuário",
    )
    current_project_names = list_user_project_names(db, user)
    next_project_names = normalize_user_project_names([*current_project_names, normalized_project_name])
    materialized_project_names = replace_user_project_memberships(db, user, next_project_names)
    user.projeto = normalized_project_name
    db.flush()
    return materialized_project_names


def assign_existing_user_active_project(db: Session, user: User, project_name: str) -> list[str]:
    normalized_project_name = normalize_project_name(
        project_name,
        field_name="O projeto ativo do usuário",
    )
    current_project_names = list_user_project_names(db, user)
    if normalized_project_name not in set(current_project_names):
        raise ValueError("O projeto informado nao pertence aos projetos cadastrados do usuário")

    materialized_project_names = ensure_user_active_project_is_member(db, user)
    user.projeto = normalized_project_name
    db.flush()
    return materialized_project_names


def remove_user_project_membership(db: Session, user: User, project_name: str) -> list[str]:
    current_project_names = list_user_project_names(db, user)
    normalized_project_name = normalize_project_name(project_name, field_name="O projeto do usuário")
    next_project_names = [
        current_project_name
        for current_project_name in current_project_names
        if current_project_name != normalized_project_name
    ]
    if len(next_project_names) == len(current_project_names):
        return ensure_user_active_project_is_member(db, user)
    if not next_project_names:
        raise ValueError("O usuário precisa permanecer vinculado a ao menos um projeto")
    return replace_user_project_memberships(db, user, next_project_names)


def user_belongs_to_project(db: Session, user: User, project_name: str) -> bool:
    normalized_project_name = normalize_project_name(project_name, field_name="O projeto do usuário")
    return normalized_project_name in set(list_user_project_names(db, user))


def ensure_user_active_project_is_member(db: Session, user: User) -> list[str]:
    current_project_names = list_user_project_names(db, user)
    if not current_project_names:
        raise ValueError("O usuário precisa ter ao menos um projeto vinculado")
    return replace_user_project_memberships(db, user, current_project_names)
