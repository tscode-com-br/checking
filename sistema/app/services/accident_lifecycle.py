from __future__ import annotations

import json
import logging
from typing import Literal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from datetime import datetime

from ..models import (
    Accident,
    AccidentUserReport,
    AccidentVideoUpload,
    ManagedLocation,
    Project,
    User,
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
) -> Accident:
    # Check for existing active accident.
    # NOTE: In Postgres production, add FOR UPDATE to the query for row-level locking.
    # SQLite does not support FOR UPDATE, so we rely on the partial unique index instead.
    existing = db.execute(
        text("SELECT id FROM accidents WHERE closed_at IS NULL")
    ).first()
    if existing is not None:
        raise AccidentAlreadyActiveError("Já existe um acidente ativo")

    project = db.get(Project, project_id)
    if project is None:
        raise ValueError("Projeto não encontrado")

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
            raise ValueError("custom_location_name é obrigatório quando location_id não é fornecido")
        location_name = custom_location_name.strip()
        location_is_registered = False

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
        created_at=now,
        updated_at=now,
    )
    db.add(accident)
    db.flush()

    # Pre-populate AccidentUserReport for all currently checked-in users
    candidates = db.execute(
        select(User).where(User.checkin == True)  # noqa: E712
    ).scalars().all()

    author_report: AccidentUserReport | None = None

    for user in candidates:
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
            last_checkin_action="check-in",
            last_action_at=user.time,
            created_at=now,
            updated_at=now,
        )
        db.add(report)
        if origin == "web" and user.id == opened_by_user_id:
            author_report = report

    if origin == "web" and opened_by_user_id is not None:
        if author_report is not None:
            # Author was checked-in: update the pre-populated row with reported zone/status
            author_report.zone = reporter_zone or "waiting"
            author_report.status = reporter_status or "waiting"
            author_report.reported_at = now
        else:
            # Author was not checked-in: still create a row for them
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
                    reported_at=now,
                    last_checkin_action=None,
                    last_action_at=None,
                    created_at=now,
                    updated_at=now,
                ))

    db.commit()

    metadata: dict[str, object] = {
        "accident_id": accident.id,
        "accident_number_label": format_accident_number(accident.accident_number),
        "project_name": accident.project_name_snapshot,
    }
    notify_admin_data_changed("accident_opened", metadata=metadata)
    notify_web_check_data_changed("accident_opened", metadata=metadata)

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

    notify_admin_data_changed("accident_user_report", metadata={"accident_id": accident.id, "user_id": user.id})
    notify_web_check_data_changed("accident_user_report", metadata={"accident_id": accident.id, "user_id": user.id})

    return report, fired_help_now


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
    existing = db.execute(
        select(AccidentVideoUpload).where(AccidentVideoUpload.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
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

    notify_admin_data_changed("accident_video_uploaded", metadata={"accident_id": accident.id, "user_id": user.id})
    notify_web_check_data_changed("accident_video_uploaded", metadata={"accident_id": accident.id, "user_id": user.id})

    return upload


def update_accident_membership_for_check_event(
    db: Session,
    *,
    accident: Accident,
    user: User,
    action: Literal["check-in", "check-out"],
    event_time: datetime,
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
            user_local_snapshot=user.local or "",
            zone="waiting",
            status="waiting",
            created_at=now,
            updated_at=now,
        )
        db.add(report)
        db.flush()

    report.last_checkin_action = action
    report.last_action_at = event_time
    report.updated_at = now
    db.commit()

    notify_admin_data_changed("accident_user_report", metadata={"accident_id": accident.id, "user_id": user.id})
    notify_web_check_data_changed("accident_user_report", metadata={"accident_id": accident.id, "user_id": user.id})

    return report


def list_active_accident(db: Session) -> Accident | None:
    return db.execute(
        select(Accident).where(Accident.closed_at.is_(None))
    ).scalar_one_or_none()


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
) -> None:
    """Call after any successful check-in/check-out to keep AccidentUserReport in sync.

    Normalises 'checkin'/'checkout' to 'check-in'/'check-out'.
    Never raises — all exceptions are swallowed with a warning log.
    """
    if action in ("checkin", "check-in"):
        normalized: Literal["check-in", "check-out"] = "check-in"
    elif action in ("checkout", "check-out"):
        normalized = "check-out"
    else:
        return

    try:
        active = list_active_accident(db)
        if active is not None:
            update_accident_membership_for_check_event(
                db,
                accident=active,
                user=user,
                action=normalized,
                event_time=event_time,
            )
    except Exception:
        _logger.warning("Accident hook failed for check event", exc_info=True)
        try:
            db.rollback()
        except Exception:
            _logger.warning("Accident hook rollback also failed", exc_info=True)
