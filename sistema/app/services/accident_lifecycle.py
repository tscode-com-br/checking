from __future__ import annotations

import json
import logging
from typing import Literal

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from datetime import datetime

from ..models import (
    Accident,
    AccidentUserReport,
    AccidentVideoUpload,
    ManagedLocation,
    Project,
    User,
    UserProjectMembership,
)
from .accident_numbering import format_accident_number, next_accident_number
from .admin_updates import notify_admin_data_changed, notify_web_check_data_changed
from .time_utils import now_sgt
from .user_projects import list_user_project_names

_logger = logging.getLogger(__name__)


class AccidentAlreadyActiveError(RuntimeError):
    pass


class NoActiveAccidentError(RuntimeError):
    pass


class InvalidAccidentLocationError(ValueError):
    pass


class AccidentProjectNotFoundError(ValueError):
    """The project referenced when opening an accident does not exist.

    Split out of the bare ValueError it used to raise: neither router caught
    plain ValueError, so a wrong project_id answered 500 instead of 404.
    """


class AccidentNumberingConflictError(RuntimeError):
    """Could not obtain a free accident_number after several attempts."""


class VideoIdempotencyConflictError(RuntimeError):
    """The idempotency_key already belongs to a different user or accident."""


def _active_accident_for_project(db: Session, project_id: int) -> Accident | None:
    return db.execute(
        select(Accident).where(
            Accident.project_id == project_id,
            Accident.closed_at.is_(None),
        )
    ).scalars().first()


def open_accident(
    db: Session,
    *,
    origin: Literal["admin", "web"],
    project_id: int,
    location_id: int | None = None,
    custom_location_name: str | None = None,
    opened_by_admin_id: int | None = None,
    opened_by_user_id: int | None = None,
    reporter_zone: str | None = None,
    reporter_status: str | None = None,
    description: str = "",
) -> Accident:
    # Per-project uniqueness: only one active accident per project at a time.
    # This check is advisory — it races with a concurrent open, so the INSERT
    # below is what actually decides, guarded by ix_accidents_single_active_per_project.
    if _active_accident_for_project(db, project_id) is not None:
        raise AccidentAlreadyActiveError("Já existe um acidente ativo para este projeto")

    project = db.get(Project, project_id)
    if project is None:
        raise AccidentProjectNotFoundError("Projeto não encontrado")

    if location_id is not None:
        location = db.get(ManagedLocation, location_id)
        if location is None:
            raise InvalidAccidentLocationError("Local não encontrado")
        location_name = location.local
        location_is_registered = True
        if origin == "admin":
            projects_in_location: list[str] = json.loads(location.projects_json or "[]")
            if project.name not in projects_in_location:
                raise InvalidAccidentLocationError(
                    f"Local '{location_name}' não pertence ao projeto '{project.name}'"
                )
    else:
        if not custom_location_name or not custom_location_name.strip():
            raise InvalidAccidentLocationError(
                "custom_location_name é obrigatório quando location_id não é fornecido"
            )
        location_name = custom_location_name.strip()
        location_is_registered = False

    # Two distinct unique constraints can fire on commit, and they mean opposite
    # things: ix_accidents_single_active_per_project means somebody else already
    # opened this project's accident (terminal, 409), while
    # uq_accidents_accident_number means two projects picked the same MAX+1 at the
    # same instant (transient, retry). Both used to surface as a raw IntegrityError
    # → HTTP 500.
    last_error: Exception | None = None
    for _ in range(3):
        try:
            accident = _create_accident_with_reports(
                db,
                project=project,
                location_name=location_name,
                location_is_registered=location_is_registered,
                origin=origin,
                opened_by_admin_id=opened_by_admin_id,
                opened_by_user_id=opened_by_user_id,
                reporter_zone=reporter_zone,
                reporter_status=reporter_status,
                description=description,
            )
            break
        except IntegrityError as exc:
            db.rollback()
            last_error = exc
            if _active_accident_for_project(db, project.id) is not None:
                raise AccidentAlreadyActiveError(
                    "Já existe um acidente ativo para este projeto"
                ) from exc
            _logger.warning(
                "accident_number collision opening accident for project %s; retrying",
                project.id,
            )
    else:
        raise AccidentNumberingConflictError(
            "Não foi possível gerar um número de acidente livre"
        ) from last_error

    metadata: dict[str, object] = {
        "accident_id": accident.id,
        "accident_number_label": format_accident_number(accident.accident_number),
        "project_name": accident.project_name_snapshot,
    }
    notify_admin_data_changed("accident_opened", metadata=metadata)
    notify_web_check_data_changed("accident_opened", metadata=metadata)

    return accident


def _create_accident_with_reports(
    db: Session,
    *,
    project: Project,
    location_name: str,
    location_is_registered: bool,
    origin: Literal["admin", "web"],
    opened_by_admin_id: int | None,
    opened_by_user_id: int | None,
    reporter_zone: str | None,
    reporter_status: str | None,
    description: str,
) -> Accident:
    """Insert the Accident plus one AccidentUserReport per project member.

    Extracted so open_accident can retry the whole unit after rolling back an
    accident_number collision — the reports are built before the commit, so a
    retry has to rebuild them too.
    """
    project_id = project.id
    now = now_sgt()
    number = next_accident_number(db)
    accident = Accident(
        accident_number=number,
        project_id=project.id,
        project_name_snapshot=project.name,
        location_name_snapshot=location_name,
        location_is_registered=location_is_registered,
        origin=origin,
        opened_by_admin_id=opened_by_admin_id,
        opened_by_user_id=opened_by_user_id,
        opened_at=now,
        description=description.strip(),
        created_at=now,
        updated_at=now,
    )
    db.add(accident)
    db.flush()

    # Pre-populate AccidentUserReport for ALL project members (not just checked-in).
    member_user_ids = [
        row.user_id
        for row in db.execute(
            select(UserProjectMembership).where(UserProjectMembership.project_id == project_id)
        ).scalars().all()
    ]

    # Build a lookup of currently checked-in users for snapshot data
    checked_in_users: dict[int, User] = {}
    if member_user_ids:
        checked_in_list = db.execute(
            select(User).where(
                User.id.in_(member_user_ids),
                User.checkin == True,  # noqa: E712
            )
        ).scalars().all()
        checked_in_users = {u.id: u for u in checked_in_list}

    # Fetch all member Users for snapshot fields
    member_users: dict[int, User] = {}
    if member_user_ids:
        all_members = db.execute(
            select(User).where(User.id.in_(member_user_ids))
        ).scalars().all()
        member_users = {u.id: u for u in all_members}

    author_report: AccidentUserReport | None = None

    for uid in member_user_ids:
        user = member_users.get(uid)
        if user is None:
            continue
        projects = list_user_project_names(db, user)
        checked_in_user = checked_in_users.get(uid)
        report = AccidentUserReport(
            accident_id=accident.id,
            user_id=user.id,
            user_chave_snapshot=user.chave,
            user_name_snapshot=user.nome,
            user_phone_snapshot=None,
            user_projects_snapshot=json.dumps(projects),
            user_local_snapshot=checked_in_user.local or "" if checked_in_user else "",
            zone="waiting",
            status="waiting",
            awareness_status="waiting",
            last_checkin_action="check-in" if checked_in_user else None,
            last_action_at=checked_in_user.time if checked_in_user else None,
            created_at=now,
            updated_at=now,
        )
        db.add(report)
        if origin == "web" and user.id == opened_by_user_id:
            author_report = report

    if origin == "web" and opened_by_user_id is not None:
        if author_report is not None:
            author_report.zone = reporter_zone or "waiting"
            author_report.status = reporter_status or "waiting"
            author_report.reported_at = now
        elif opened_by_user_id not in member_user_ids:
            # Author is not a member of the project — create a report anyway
            author_user = db.get(User, opened_by_user_id)
            if author_user is not None:
                projects = list_user_project_names(db, author_user)
                db.add(AccidentUserReport(
                    accident_id=accident.id,
                    user_id=author_user.id,
                    user_chave_snapshot=author_user.chave,
                    user_name_snapshot=author_user.nome,
                    user_phone_snapshot=None,
                    user_projects_snapshot=json.dumps(projects),
                    user_local_snapshot=author_user.local or "",
                    zone=reporter_zone or "waiting",
                    status=reporter_status or "waiting",
                    awareness_status="waiting",
                    reported_at=now,
                    last_checkin_action=None,
                    last_action_at=None,
                    created_at=now,
                    updated_at=now,
                ))

    db.commit()
    return accident


def upsert_user_safety_report(
    db: Session,
    *,
    accident: Accident,
    user: User,
    zone: str,
    status: str,
) -> tuple[AccidentUserReport, bool]:
    now = now_sgt()
    report = db.execute(
        select(AccidentUserReport).where(
            AccidentUserReport.accident_id == accident.id,
            AccidentUserReport.user_id == user.id,
        )
    ).scalar_one_or_none()

    if report is None:
        projects = list_user_project_names(db, user)
        report = AccidentUserReport(
            accident_id=accident.id,
            user_id=user.id,
            user_chave_snapshot=user.chave,
            user_name_snapshot=user.nome,
            user_phone_snapshot=None,
            user_projects_snapshot=json.dumps(projects),
            user_local_snapshot=user.local or "",
            zone="waiting",
            status="waiting",
            awareness_status="waiting",
            created_at=now,
            updated_at=now,
        )
        db.add(report)
        db.flush()

    previous_status = report.status

    report.zone = zone
    report.status = status
    report.reported_at = now
    report.updated_at = now
    db.commit()

    fired_help_now = (status == "help" and previous_status != "help")

    # project_name travels with every accident event so the admin SSE stream can
    # drop events for projects an admin does not administer.
    metadata = {
        "accident_id": accident.id,
        "user_id": user.id,
        "project_name": accident.project_name_snapshot,
    }
    notify_admin_data_changed("accident_user_report", metadata=metadata)
    notify_web_check_data_changed("accident_user_report", metadata=metadata)

    return report, fired_help_now


def find_video_upload(
    db: Session,
    *,
    idempotency_key: str,
    accident: Accident,
    user: User,
) -> AccidentVideoUpload | None:
    """Return this user's earlier upload for *idempotency_key*, if there is one.

    idempotency_key is UNIQUE across the whole table (models.py:880), not per user,
    and the lookup used to match on it alone. A colliding key therefore returned
    somebody else's row, and the uploader got another user's video URL back in the
    response for a video they never took. Keys come from the client — the browser
    fallback is weak — so collisions are reachable.
    """
    existing = db.execute(
        select(AccidentVideoUpload).where(
            AccidentVideoUpload.idempotency_key == idempotency_key
        )
    ).scalars().first()
    if existing is None:
        return None
    if existing.accident_id != accident.id or existing.user_id != user.id:
        raise VideoIdempotencyConflictError(
            "idempotency_key já utilizado em outro registro"
        )
    return existing


def attach_video_upload(
    db: Session,
    *,
    accident: Accident,
    user: User,
    object_key: str,
    public_url: str,
    content_type: str,
    size_bytes: int,
    duration_seconds: int | None,
    idempotency_key: str,
    captured_at: datetime | None = None,
) -> AccidentVideoUpload:
    existing = find_video_upload(
        db, idempotency_key=idempotency_key, accident=accident, user=user
    )
    if existing is not None:
        return existing

    now = now_sgt()
    upload = AccidentVideoUpload(
        idempotency_key=idempotency_key,
        accident_id=accident.id,
        user_id=user.id,
        object_key=object_key,
        public_url=public_url,
        content_type=content_type,
        size_bytes=size_bytes,
        duration_seconds=duration_seconds,
        captured_at=captured_at or now,
        created_at=now,
    )
    db.add(upload)
    db.commit()

    metadata = {
        "accident_id": accident.id,
        "user_id": user.id,
        "project_name": accident.project_name_snapshot,
    }
    notify_admin_data_changed("accident_video_uploaded", metadata=metadata)
    notify_web_check_data_changed("accident_video_uploaded", metadata=metadata)

    return upload


def update_accident_membership_for_check_event(
    db: Session,
    *,
    accident: Accident,
    user: User,
    action: Literal["check-in", "check-out"],
    event_time: datetime,
    local: str = "",
) -> AccidentUserReport:
    now = now_sgt()
    report = db.execute(
        select(AccidentUserReport).where(
            AccidentUserReport.accident_id == accident.id,
            AccidentUserReport.user_id == user.id,
        )
    ).scalar_one_or_none()

    if report is None:
        projects = list_user_project_names(db, user)
        report = AccidentUserReport(
            accident_id=accident.id,
            user_id=user.id,
            user_chave_snapshot=user.chave,
            user_name_snapshot=user.nome,
            user_phone_snapshot=None,
            user_projects_snapshot=json.dumps(projects),
            user_local_snapshot=local,
            zone="waiting",
            status="waiting",
            awareness_status="waiting",
            created_at=now,
            updated_at=now,
        )
        db.add(report)
        db.flush()

    report.last_checkin_action = action
    report.last_action_at = event_time
    if local:
        report.user_local_snapshot = local
    report.updated_at = now
    db.commit()

    metadata = {
        "accident_id": accident.id,
        "user_id": user.id,
        "project_name": accident.project_name_snapshot,
    }
    notify_admin_data_changed("accident_user_report", metadata=metadata)
    notify_web_check_data_changed("accident_user_report", metadata=metadata)

    return report


def acknowledge_accident(db: Session, accident_id: int, user: User) -> None:
    report = db.execute(
        select(AccidentUserReport).where(
            AccidentUserReport.accident_id == accident_id,
            AccidentUserReport.user_id == user.id,
        )
    ).scalar_one_or_none()
    if report is not None and report.awareness_status != "acknowledged":
        report.awareness_status = "acknowledged"
        report.updated_at = now_sgt()
        db.commit()
        accident = db.get(Accident, accident_id)
        notify_admin_data_changed(
            "accident_acknowledged",
            metadata={
                "accident_id": accident_id,
                "user_id": user.id,
                "project_name": accident.project_name_snapshot if accident else None,
            },
        )


def list_active_accidents(db: Session) -> list[Accident]:
    return list(
        db.execute(
            select(Accident).where(Accident.closed_at.is_(None)).order_by(Accident.accident_number)
        ).scalars().all()
    )


def list_active_accident(db: Session) -> Accident | None:
    """Backward-compat: return the first active accident, or None."""
    actives = list_active_accidents(db)
    return actives[0] if actives else None


def close_accident(
    db: Session,
    *,
    accident: Accident,
    closed_by_admin_id: int,
) -> Accident:
    if accident.closed_at is not None:
        raise NoActiveAccidentError("O acidente já está encerrado")

    now = now_sgt()
    accident.closed_at = now
    accident.closed_by_admin_id = closed_by_admin_id
    accident.updated_at = now
    db.commit()

    metadata: dict[str, object] = {
        "accident_id": accident.id,
        "accident_number_label": format_accident_number(accident.accident_number),
        "project_name": accident.project_name_snapshot,
    }
    notify_admin_data_changed("accident_closed", metadata=metadata)
    notify_web_check_data_changed("accident_closed", metadata=metadata)

    return accident


def fire_accident_hook_for_check_event(
    db: "Session",
    *,
    user: "User",
    action: str,
    event_time: "datetime",
    local: str = "",
) -> None:
    """Call after any successful check-in/check-out to keep AccidentUserReport in sync.

    Normalises 'checkin'/'checkout' to 'check-in'/'check-out'.
    Updates all active accidents whose project the user belongs to.
    Never raises — all exceptions are swallowed with a warning log.
    """
    if action in ("checkin", "check-in"):
        normalized: Literal["check-in", "check-out"] = "check-in"
    elif action in ("checkout", "check-out"):
        normalized = "check-out"
    else:
        return

    try:
        # Resolve active accidents relevant to this user's projects
        user_project_ids = {
            m.project_id
            for m in db.execute(
                select(UserProjectMembership).where(UserProjectMembership.user_id == user.id)
            ).scalars().all()
        }
        actives = list_active_accidents(db)
        relevant = [a for a in actives if a.project_id in user_project_ids]
        for accident in relevant:
            update_accident_membership_for_check_event(
                db,
                accident=accident,
                user=user,
                action=normalized,
                event_time=event_time,
                local=local,
            )
    except Exception:
        _logger.warning("Accident hook failed for check event", exc_info=True)
        try:
            db.rollback()
        except Exception:
            _logger.warning("Accident hook rollback also failed", exc_info=True)
