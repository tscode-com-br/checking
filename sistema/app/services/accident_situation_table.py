from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Accident, AccidentUserReport, AccidentVideoUpload
from ..schemas import AccidentVideoLink, SituacaoPessoalRow
from .object_storage import generate_presigned_url


def _resolve_video_public_url(video: AccidentVideoUpload) -> str:
    """Return a URL the admin can use to play the video.

    Generates a fresh URL from the stored object_key so:
      - dev (local storage) → /api/admin/accidents/local-asset/<key>
      - prod (DO Spaces, ACL=private) → presigned URL valid for 5 minutes
    Falls back to the persisted public_url if presigning fails (extremely
    defensive — keeps the link working even if storage misconfigures).
    """
    object_key = (video.object_key or "").strip()
    if not object_key:
        return video.public_url or ""
    try:
        return generate_presigned_url(object_key=object_key, expires_in_seconds=300)
    except Exception:
        return video.public_url or ""


def _align_awareness(left: datetime, right: datetime) -> tuple[datetime, datetime]:
    """Make two datetimes safe to compare.

    DateTime(timezone=True) round-trips as tz-aware in Postgres and as naive in
    SQLite, so a value read from the DB and a value produced elsewhere may not
    agree. Comparing across the two raises TypeError. Only strip tzinfo when the
    awareness actually differs — dropping it unconditionally is what broke
    production. Mirrors services.forms_queue._normalize_datetime_pair.
    """
    if (left.tzinfo is None) == (right.tzinfo is None):
        return left, right
    return left.replace(tzinfo=None), right.replace(tzinfo=None)


def _derive_display(
    report: AccidentUserReport,
    opened_at: datetime,
) -> tuple[str, str, str, int, int]:
    """Return (zone_display, status_display, row_color, priority, section)."""
    # Priority 5 / Section 4: checked-out during this accident
    checked_out_during_accident = False
    if report.last_checkin_action == "check-out" and report.last_action_at is not None:
        last_action_at, opened_at_cmp = _align_awareness(report.last_action_at, opened_at)
        checked_out_during_accident = last_action_at >= opened_at_cmp

    if checked_out_during_accident:
        zone_display = (
            "Segurança"
            if report.zone == "safety"
            else ("Acidente" if report.zone == "accident" else "Aguardando")
        )
        status_display = (
            "OK"
            if report.status == "ok"
            else ("AJUDA" if report.status == "help" else "Aguardando")
        )
        return zone_display, status_display, "light-gray", 5, 4

    # Any explicit call for help is an emergency, whatever zone it came from.
    # WebAccidentReportRequest accepts zone="safety" + status="help" (schemas.py:4537),
    # a normal thing to report — "I reached the safety zone but I need help". That
    # combination had no branch and fell through to the fallback below, rendering as
    # "Aguardando" in light-blue section 3: a call for help displayed as someone who
    # never answered.
    if report.status == "help":
        zone_display = (
            "Acidente"
            if report.zone == "accident"
            else ("Segurança" if report.zone == "safety" else "Aguardando")
        )
        return zone_display, "AJUDA", "blinking-red", 1, 1  # Seção 1: Emergência
    if report.zone == "accident" and report.status == "ok":
        return "Acidente", "OK", "yellow", 2, 2             # Seção 2: Local do Acidente
    if report.zone == "waiting":
        return "Aguardando", "Aguardando", "light-blue", 3, 3  # Seção 3: Não Reportados
    if report.zone == "safety" and report.status == "ok":
        return "Segurança", "OK", "light-green", 4, 4       # Seção 4: Demais
    return "Aguardando", "Aguardando", "light-blue", 3, 3   # fallback → seção 3


def build_situation_rows(
    db: Session,
    *,
    accident: Accident,
) -> list[SituacaoPessoalRow]:
    reports = (
        db.execute(
            select(AccidentUserReport).where(
                AccidentUserReport.accident_id == accident.id
            )
        )
        .scalars()
        .all()
    )

    rows: list[SituacaoPessoalRow] = []
    for report in reports:
        raw_videos = (
            db.execute(
                select(AccidentVideoUpload)
                .where(
                    AccidentVideoUpload.accident_id == accident.id,
                    AccidentVideoUpload.user_id == report.user_id,
                )
                .order_by(AccidentVideoUpload.captured_at.asc())
            )
            .scalars()
            .all()
        )
        videos = [
            AccidentVideoLink(
                video_id=v.id,
                # Always derive the URL from the object_key at read-time:
                # - In dev (local storage), object_storage.generate_presigned_url
                #   returns the /api/admin/accidents/local-asset/<key> endpoint
                #   that admin.serve_local_asset serves.
                # - In prod (DO Spaces with ACL=private), it returns a signed
                #   URL valid for `expires_in_seconds`, so the admin can play
                #   the video without it being publicly accessible.
                # Falls back to the persisted public_url if presigning is
                #   unavailable (e.g. missing object_key — should not happen).
                public_url=_resolve_video_public_url(v),
                captured_at=v.captured_at,
                content_type=v.content_type,
                size_bytes=v.size_bytes,
            )
            for v in raw_videos
        ]

        event_time = report.reported_at or report.last_action_at or report.created_at
        projects: list[str] = json.loads(report.user_projects_snapshot or "[]")
        zone_display, status_display, row_color, priority, section = _derive_display(
            report, accident.opened_at
        )

        # Derive "Atividade/Local" column
        if report.last_checkin_action and report.user_local_snapshot:
            action_label = "Check-In" if report.last_checkin_action == "check-in" else "Check-Out"
            activity_local: str | None = f"{action_label}/{report.user_local_snapshot}"
        elif report.user_local_snapshot:
            activity_local = report.user_local_snapshot
        else:
            activity_local = None

        rows.append(
            SituacaoPessoalRow(
                user_id=report.user_id,
                event_time=event_time,
                name=report.user_name_snapshot,
                chave=report.user_chave_snapshot,
                projects=projects,
                local=report.user_local_snapshot or None,
                activity_local=activity_local,
                zone=zone_display,
                status=status_display,
                phone=report.user_phone_snapshot,
                videos=videos,
                priority=priority,
                section=section,
                awareness_status=report.awareness_status,
                row_color=row_color,
            )
        )

    def _sort_key(row: SituacaoPessoalRow) -> tuple:
        if row.section in (3, 4):
            acknowledged = 0 if row.awareness_status == "acknowledged" else 1
            has_checkin = 0 if (row.activity_local and "Check-In" in row.activity_local) else 1
            event_ts = -row.event_time.timestamp()
            return (row.section, acknowledged, event_ts, has_checkin, row.name)
        # Within sections 1-2: sort by section, then priority, then most-recent first
        return (row.section, row.priority, -row.event_time.timestamp(), 0, row.name)

    rows.sort(key=_sort_key)
    return rows
