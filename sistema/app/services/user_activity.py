from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Project, User, UserProjectMembership
from .time_utils import now_sgt, resolve_timezone


SYSTEM_REFERENCE_TIMEZONE = resolve_timezone()
SECONDS_PER_DAY = 24 * 60 * 60
INACTIVE_AFTER_CONTINUOUS_HOURS = 24


def _to_reference_timezone(value: datetime) -> datetime:
    return value.astimezone(SYSTEM_REFERENCE_TIMEZONE)


def calculate_inactivity_seconds(last_active_at: datetime | None, *, reference_time: datetime | None = None) -> int:
    if last_active_at is None:
        return 0

    start = _to_reference_timezone(last_active_at)
    end = _to_reference_timezone(reference_time or now_sgt())
    if end <= start:
        return 0

    return max(int((end - start).total_seconds()), 0)


def calculate_inactivity_days(last_active_at: datetime | None, *, reference_time: datetime | None = None) -> int:
    inactivity_seconds = calculate_inactivity_seconds(last_active_at, reference_time=reference_time)
    return inactivity_seconds // SECONDS_PER_DAY


def has_exceeded_continuous_inactivity_window(
    event_time: datetime | None,
    *,
    reference_time: datetime | None = None,
) -> bool:
    inactivity_seconds = calculate_inactivity_seconds(event_time, reference_time=reference_time)
    return inactivity_seconds >= INACTIVE_AFTER_CONTINUOUS_HOURS * 60 * 60


def is_user_inactive(last_active_at: datetime | None, *, reference_time: datetime | None = None) -> bool:
    return has_exceeded_continuous_inactivity_window(last_active_at, reference_time=reference_time)


def mark_user_active(user: User, *, activity_time=None) -> None:
    timestamp = activity_time or now_sgt()
    user.last_active_at = timestamp
    user.inactivity_days = 0


def sync_user_inactivity(db: Session, *, reference_time=None) -> bool:
    now_value = reference_time or now_sgt()
    changed = False
    users = db.execute(select(User)).scalars().all()

    for user in users:
        inactivity_days = calculate_inactivity_days(user.last_active_at, reference_time=now_value)
        if user.inactivity_days != inactivity_days:
            user.inactivity_days = inactivity_days
            changed = True

    if changed:
        db.flush()

    return changed


def apply_inactivity_descadastro(db: Session, *, reference_time=None) -> bool:
    """Remove memberships de usuários que excederam o limite de inatividade por projeto.

    Para cada UserProjectMembership, verifica se user.inactivity_days >=
    project.inactivity_days_threshold. Se sim, remove aquela membership,
    mantendo as demais cujo limite ainda não foi atingido.

    Deve ser chamado após sync_user_inactivity para garantir que inactivity_days
    está atualizado.

    Returns True se houve alguma remoção.
    """
    from .admin_auth import user_has_admin_access  # local: evita import circular
    from .user_projects import replace_user_project_memberships  # evita import circular

    rows = db.execute(
        select(UserProjectMembership, User, Project)
        .join(User, UserProjectMembership.user_id == User.id)
        .join(Project, UserProjectMembership.project_id == Project.id)
        .where(User.inactivity_days > 0)
    ).all()

    if not rows:
        return False

    all_project_names: dict[int, list[str]] = defaultdict(list)
    projects_to_remove: dict[int, set[str]] = defaultdict(set)
    users_map: dict[int, User] = {}

    for membership, user, project in rows:
        # Admins (perfil 1/9) NÃO são descadastrados por inatividade: a membership de um admin é o
        # seu escopo de gestão de projeto, não um indicador de presença em campo. Sem essa isenção,
        # um admin que não faz check-in perde o vínculo de projeto e passa a não enxergar ninguém.
        if user_has_admin_access(user):
            continue
        users_map[user.id] = user
        all_project_names[user.id].append(project.name)
        if user.inactivity_days >= project.inactivity_days_threshold:
            projects_to_remove[user.id].add(project.name)

    if not projects_to_remove:
        return False

    for user_id, remove_set in projects_to_remove.items():
        user = users_map[user_id]
        next_names = [
            name for name in all_project_names[user_id] if name not in remove_set
        ]
        replace_user_project_memberships(db, user, next_names)

    return True