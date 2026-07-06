from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import User, UserSyncEvent
from ..schemas import MobileSubmitResponse
from .admin_updates import notify_admin_data_changed
from .accident_lifecycle import fire_accident_hook_for_check_event
from .event_logger import log_event
from .forms_queue import enqueue_forms_submission, is_forms_worker_healthy_now, record_forms_submission_skip
from .project_catalog import is_forms_enabled_for_project
from .time_utils import resolve_project_timezone_name
from .user_projects import list_user_project_names
from .user_sync import (
    apply_user_state,
    build_mobile_sync_state,
    create_user_sync_event,
    ensure_current_user_state_event,
    get_forms_skip_reason,
    normalize_event_time,
    resolve_latest_internal_user_activity,
    should_enqueue_forms_for_action,
)


EnsureUserCallback = Callable[..., tuple[User, bool]]


@dataclass(frozen=True)
class FormsSubmitChannel:
    event_label: str
    user_sync_source: str
    log_source: str
    request_path: str
    device_id: str | None
    default_local: str


def submit_forms_event(
    db: Session,
    *,
    chave: str,
    projeto: str,
    action: str,
    informe: str,
    local: str | None,
    event_time: datetime,
    client_event_id: str,
    ensure_user: EnsureUserCallback,
    channel: FormsSubmitChannel,
    fill_forms: bool = True,
) -> MobileSubmitResponse:
    ontime = informe == "normal"
    resolved_local = local or channel.default_local

    existing = db.execute(
        select(UserSyncEvent).where(
            UserSyncEvent.source == channel.user_sync_source,
            UserSyncEvent.source_request_id == client_event_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        state = build_mobile_sync_state(db, chave=chave)
        return MobileSubmitResponse(
            ok=True,
            duplicate=True,
            queued_forms=False,
            message=f"{channel.event_label} already submitted",
            state=state,
        )

    user, _created = ensure_user(db, chave=chave, projeto=projeto)
    project_timezone_name = resolve_project_timezone_name(db, projeto)
    normalized_event_time = normalize_event_time(event_time, timezone_name=project_timezone_name)
    ensure_current_user_state_event(db, user=user, skip_if_provider_backed=True)
    latest_activity = resolve_latest_internal_user_activity(db, user=user)
    skip_reason = get_forms_skip_reason(
        latest_activity=latest_activity,
        action=action,
        event_time=normalized_event_time,
        timezone_name=project_timezone_name,
    )
    should_queue_forms = should_enqueue_forms_for_action(
        latest_activity=latest_activity,
        action=action,
        event_time=normalized_event_time,
        timezone_name=project_timezone_name,
    )
    # Change E (P7.1): the user's registered projects. Single-project keeps the exact legacy path
    # (one submission, gated on user.projeto); multi-project enqueues one submission PER project,
    # each gated by its own forms_enabled inside _enqueue_forms_per_project_and_record.
    project_candidates = list_user_project_names(db, user)
    single_project = len(project_candidates) <= 1
    # GATE — verificar se Forms está habilitado para o projeto. Single-project only: for multi-project
    # the gate is per project (so an enabled project still submits even if user.projeto is disabled).
    if single_project and not is_forms_enabled_for_project(db, projeto=user.projeto):
        should_queue_forms = False
        skip_reason = "forms_disabled_for_project"
    # 24h FORMS window (multi-day offline replay). The client owns this decision because only it can see
    # the full offline backlog: it sets fill_forms=False for events older than 24h relative to the NEWEST
    # queued activity (so a device offline for days fills FORMS with one recent check-in/out, not one per
    # day). The activity is STILL recorded at its real time below (create_user_sync_event →
    # record_checking_history); only the FORMS fill is suppressed. Live submissions send fill_forms=True
    # (the default), so they are never affected.
    if should_queue_forms and not fill_forms:
        should_queue_forms = False
        skip_reason = "offline_beyond_24h"
    apply_user_state(
        user,
        action=action,
        event_time=normalized_event_time,
        projeto=projeto,
        local=resolved_local,
    )

    if not should_queue_forms:
        project_candidates = list_user_project_names(db, user)
        record_forms_submission_skip(
            db,
            request_id=client_event_id,
            rfid=user.rfid,
            action=action,
            chave=user.chave,
            projeto=user.projeto,
            device_id=channel.device_id,
            local=resolved_local,
            event_time=normalized_event_time,
            request_path=channel.request_path,
            project_candidates=project_candidates,
            ontime=ontime,
            skip_reason=skip_reason,
        )
        create_user_sync_event(
            db,
            user=user,
            source=channel.user_sync_source,
            action=action,
            event_time=normalized_event_time,
            projeto=user.projeto,
            local=resolved_local,
            ontime=ontime,
            source_request_id=client_event_id,
            device_id=channel.device_id,
        )
        message = f"{channel.event_label} accepted without new Forms submission"
        log_event(
            db,
            idempotency_key=f"{channel.user_sync_source}:{client_event_id}",
            source=channel.log_source,
            action=action,
            status="updated",
            message=message,
            rfid=user.rfid,
            project=user.projeto,
            local=resolved_local,
            request_path=channel.request_path,
            http_status=200,
            ontime=ontime,
            details=(
                f"chave={user.chave}; event_time={normalized_event_time.isoformat()}; "
                f"forms_skipped=true; informe={informe}; ontime={ontime}; "
                f"reason={skip_reason or 'not_realized'}"
            ),
        )
        db.commit()
        notify_admin_data_changed(action)
        fire_accident_hook_for_check_event(db, user=user, action=action, event_time=normalized_event_time)
        state = build_mobile_sync_state(db, chave=user.chave)
        return MobileSubmitResponse(
            ok=True,
            duplicate=False,
            queued_forms=False,
            message=message,
            state=state,
        )

    if single_project:
        try:
            enqueue_forms_submission(
                db,
                request_id=client_event_id,
                rfid=user.rfid,
                action=action,
                chave=user.chave,
                projeto=user.projeto,
                device_id=channel.device_id,
                local=resolved_local,
                event_time=normalized_event_time,
                request_path=channel.request_path,
                project_candidates=project_candidates,
                ontime=ontime,
            )
        except IntegrityError:
            db.rollback()
            state = build_mobile_sync_state(db, chave=chave)
            return MobileSubmitResponse(
                ok=True,
                duplicate=True,
                queued_forms=False,
                message=f"{channel.event_label} already submitted",
                state=state,
            )

        create_user_sync_event(
            db,
            user=user,
            source=channel.user_sync_source,
            action=action,
            event_time=normalized_event_time,
            projeto=user.projeto,
            local=resolved_local,
            ontime=ontime,
            source_request_id=client_event_id,
            device_id=channel.device_id,
        )
    else:
        # Change E (P7.1): one FormsSubmission + sync/history row PER registered project.
        try:
            recorded_projects = _enqueue_forms_per_project_and_record(
                db,
                user=user,
                action=action,
                channel=channel,
                client_event_id=client_event_id,
                resolved_local=resolved_local,
                normalized_event_time=normalized_event_time,
                ontime=ontime,
                project_candidates=project_candidates,
            )
        except IntegrityError:
            db.rollback()
            state = build_mobile_sync_state(db, chave=chave)
            return MobileSubmitResponse(
                ok=True,
                duplicate=True,
                queued_forms=False,
                message=f"{channel.event_label} already submitted",
                state=state,
            )
        if recorded_projects == 0:
            # Full replay — every project was already recorded for this event. Mirror the
            # single-project top-of-function short-circuit (no second log_event/commit).
            db.rollback()
            state = build_mobile_sync_state(db, chave=chave)
            return MobileSubmitResponse(
                ok=True,
                duplicate=True,
                queued_forms=False,
                message=f"{channel.event_label} already submitted",
                state=state,
            )
    message = f"{channel.event_label} accepted and queued for Forms submission"
    log_event(
        db,
        idempotency_key=f"{channel.user_sync_source}:{client_event_id}",
        source=channel.log_source,
        action=action,
        status="queued",
        message=message,
        rfid=user.rfid,
        project=user.projeto,
        local=resolved_local,
        request_path=channel.request_path,
        http_status=202,
        ontime=ontime,
        details=(
            f"chave={user.chave}; event_time={normalized_event_time.isoformat()}; "
            f"forms_deferred=true; informe={informe}; ontime={ontime}"
        ),
    )
    db.commit()
    notify_admin_data_changed(action)
    fire_accident_hook_for_check_event(db, user=user, action=action, event_time=normalized_event_time)
    state = build_mobile_sync_state(db, chave=user.chave)
    return MobileSubmitResponse(
        ok=True,
        duplicate=False,
        queued_forms=True,
        worker_healthy=is_forms_worker_healthy_now(),
        message=message,
        state=state,
    )


def _short_project_token(project: str) -> str:
    """Stable, bounded per-project suffix for FormsSubmission.request_id (String(80), unique).

    Project names are String(120), so the raw name cannot be embedded without risking overflow; a
    12-char sha1 prefix keeps `{client_event_id}:{token}` well under 80 chars while staying
    deterministic across retries (the readable project lives in the row's own `projeto` column).
    """
    return hashlib.sha1(project.strip().encode("utf-8")).hexdigest()[:12]


def _enqueue_forms_per_project_and_record(
    db: Session,
    *,
    user: User,
    action: str,
    channel: FormsSubmitChannel,
    client_event_id: str,
    resolved_local: str | None,
    normalized_event_time: datetime,
    ontime: bool,
    project_candidates: list[str],
) -> int:
    """Change E (P7.1): enqueue one FormsSubmission + record one sync/history row PER registered
    project, each keyed by a per-project request_id so retries stay idempotent and projects don't
    collide on the unique request_id. A project with forms disabled is recorded as a per-project skip
    (diagnostics stay accurate) but still gets its sync/history row. Per-project idempotency is
    enforced by checking the UserSyncEvent before writing, so a replay records each project once.

    Returns the number of projects newly recorded this call (0 → full replay, all already recorded).
    """
    recorded = 0
    for project in project_candidates:
        per_project_request_id = f"{client_event_id}:{_short_project_token(project)}"
        already = db.execute(
            select(UserSyncEvent).where(
                UserSyncEvent.source == channel.user_sync_source,
                UserSyncEvent.source_request_id == per_project_request_id,
            )
        ).scalar_one_or_none()
        if already is not None:
            continue  # retry-safe: this project was already recorded for this event
        if is_forms_enabled_for_project(db, projeto=project):
            enqueue_forms_submission(
                db,
                request_id=per_project_request_id,
                rfid=user.rfid,
                action=action,
                chave=user.chave,
                projeto=project,
                device_id=channel.device_id,
                local=resolved_local,
                event_time=normalized_event_time,
                request_path=channel.request_path,
                project_candidates=[project],
                ontime=ontime,
            )
        else:
            record_forms_submission_skip(
                db,
                request_id=per_project_request_id,
                rfid=user.rfid,
                action=action,
                chave=user.chave,
                projeto=project,
                device_id=channel.device_id,
                local=resolved_local,
                event_time=normalized_event_time,
                request_path=channel.request_path,
                project_candidates=[project],
                ontime=ontime,
                skip_reason="forms_disabled_for_project",
            )
        create_user_sync_event(
            db,
            user=user,
            source=channel.user_sync_source,
            action=action,
            event_time=normalized_event_time,
            projeto=project,
            local=resolved_local,
            ontime=ontime,
            source_request_id=per_project_request_id,
            device_id=channel.device_id,
        )
        recorded += 1
    return recorded