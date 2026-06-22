from __future__ import annotations

import json
import logging
import os
import threading
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from ..core.config import settings
from ..database import SessionLocal
from ..models import FormsSubmission
from .admin_updates import notify_admin_data_changed
from .event_archives import ensure_event_archives_dir
from .event_logger import log_event
from .time_utils import now_sgt

FORMS_QUEUE_POLL_SECONDS = 0.25
FORMS_QUEUE_RECENT_PROCESSING_SAMPLE_SIZE = 100
FORMS_QUEUE_LOGGER = logging.getLogger("checking.forms_queue")
FORMS_QUEUE_BACKLOG_STATUSES = ("pending", "processing")
FORMS_QUEUE_TERMINAL_STATUSES = ("success", "failed")
FORMS_QUEUE_MAX_CLAIM_ATTEMPTS = 5
FORMS_WORKER_HEALTH_FILE_NAME = "forms_worker_health.json"
FORMS_WORKER_ERROR_BACKOFF_BASE_SECONDS = 1.0
FORMS_WORKER_ERROR_BACKOFF_MAX_SECONDS = 15.0
FORMS_WORKER_SUPERVISOR_RESTART_BASE_SECONDS = 2.0
FORMS_WORKER_SUPERVISOR_RESTART_MAX_SECONDS = 30.0
FORMS_WORKER_DATETIME_FIELDS = (
    "started_at",
    "last_heartbeat_at",
    "last_loop_started_at",
    "last_loop_completed_at",
)
FORMS_DISPLAY_STATUS_BY_LABEL = {
    "URL Carregada": "url_loaded",
    "Preenchendo...": "filling",
    "Preenchido": "filled",
    "Enviado": "sent",
    "Abortado": "aborted",
    "Nao Encontrado": "not_found",
}
FORMS_TERMINAL_DISPLAY_STATUS_BY_RESULT = {
    True: "sent",
    False: "aborted",
}

# temp005 / Prompt 1 — resolução do display_status EFETIVO quando a submissão vinculada à atividade mais
# recente é um skip deduplicado (repeated_same_action_same_day / repeated_checkout). Nesse caso o
# 'not_realized' do duplicado NÃO deve esconder a submissão IRMÃ real (mesmo chave/action/dia-projeto)
# que de fato foi processada. Prioridade de ciclo de vida (maior vence):
FORMS_SUBMISSION_STATUS_PRIORITY = {
    "success": 4,
    "failed": 3,
    "processing": 2,
    "pending": 1,
    "skipped": 0,
}

FormsSiblingCandidate = namedtuple(
    "FormsSiblingCandidate",
    ("status", "display_status", "processed_at", "event_time", "submission_id"),
)


def _forms_sibling_recency_value(value: datetime | None) -> float:
    """Epoch (UTC) comparável e robusto a None/naive, usado só como desempate entre irmãs de mesmo
    status (o resultado entre dois skipped é irrelevante; entre não-skip há no máximo uma na prática)."""
    if value is None:
        return float("-inf")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).timestamp()
    return value.timestamp()


def resolve_effective_skipped_display_status(
    candidates: list[FormsSiblingCandidate],
) -> str | None:
    """Devolve o display_status EFETIVO da submissão IRMÃ real, ou None se não houver irmã não-skip.

    Considera APENAS candidatas com status != 'skipped'. Escolhe a de maior prioridade de ciclo de vida
    (success>failed>processing>pending), desempatando por processed_at, depois event_time, depois
    submission_id (mais recente vence), e devolve o display_status dela. Quando não existe nenhuma
    candidata não-skip, devolve None e o chamador mantém o 'not_realized' do skip."""
    real_candidates = [candidate for candidate in candidates if candidate.status != "skipped"]
    if not real_candidates:
        return None
    best = max(
        real_candidates,
        key=lambda candidate: (
            FORMS_SUBMISSION_STATUS_PRIORITY.get(candidate.status, -1),
            _forms_sibling_recency_value(candidate.processed_at),
            _forms_sibling_recency_value(candidate.event_time),
            candidate.submission_id or 0,
        ),
    )
    return best.display_status


def _log_forms_queue_event(event: str, **fields: object) -> None:
    FORMS_QUEUE_LOGGER.info(
        json.dumps(
            {
                "event": event,
                **fields,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )


def _normalize_project_candidates(project_candidates: list[str] | tuple[str, ...] | None) -> list[str]:
    normalized: list[str] = []
    for value in project_candidates or []:
        candidate = str(value or "").strip().upper()
        if candidate and candidate not in normalized:
            normalized.append(candidate)
    return normalized


def _dump_project_candidates_json(project_candidates: list[str] | tuple[str, ...] | None) -> str | None:
    normalized_candidates = _normalize_project_candidates(project_candidates)
    if not normalized_candidates:
        return None
    return json.dumps(normalized_candidates, separators=(",", ":"), ensure_ascii=True)


def _load_project_candidates_json(project_candidates_json: str | None) -> list[str]:
    if not project_candidates_json:
        return []
    try:
        payload = json.loads(project_candidates_json)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    return _normalize_project_candidates(payload)


def _normalize_display_status_from_worker_label(status_label: str | None) -> str | None:
    normalized_label = str(status_label or "").strip()
    if not normalized_label:
        return None
    return FORMS_DISPLAY_STATUS_BY_LABEL.get(normalized_label)


def _persist_submission_display_status(db, *, submission_id: int, action: str, display_status: str) -> None:
    submission = db.get(FormsSubmission, submission_id)
    if submission is None or submission.display_status == display_status:
        return
    submission.display_status = display_status
    submission.updated_at = now_sgt()
    db.commit()
    notify_admin_data_changed(action)


def _age_seconds(reference_time: datetime, timestamp: datetime | None) -> int | None:
    if timestamp is None:
        return None
    normalized_reference_time, normalized_timestamp = _normalize_datetime_pair(reference_time, timestamp)
    return max(int((normalized_reference_time - normalized_timestamp).total_seconds()), 0)


def _normalize_datetime_pair(left: datetime, right: datetime) -> tuple[datetime, datetime]:
    if (left.tzinfo is None) == (right.tzinfo is None):
        return left, right
    return left.replace(tzinfo=None), right.replace(tzinfo=None)


def _recent_processing_durations_ms(rows: list[tuple[datetime, datetime | None]]) -> list[int]:
    durations: list[int] = []
    for created_at, processed_at in rows:
        if processed_at is None:
            continue
        normalized_processed_at, normalized_created_at = _normalize_datetime_pair(processed_at, created_at)
        durations.append(max(int((normalized_processed_at - normalized_created_at).total_seconds() * 1000), 0))
    return durations


def _compute_exponential_backoff_seconds(*, base_seconds: float, max_seconds: float, attempt: int) -> float:
    normalized_attempt = max(int(attempt), 1)
    return min(base_seconds * (2 ** (normalized_attempt - 1)), max_seconds)


def _forms_worker_health_path() -> Path:
    return ensure_event_archives_dir() / FORMS_WORKER_HEALTH_FILE_NAME


def _serialize_forms_worker_health_snapshot(snapshot: dict[str, object]) -> dict[str, object]:
    serialized: dict[str, object] = {}
    for key, value in snapshot.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


def _write_forms_worker_health_snapshot(snapshot: dict[str, object]) -> None:
    health_path = _forms_worker_health_path()
    temp_path = health_path.with_suffix(".tmp")
    payload = json.dumps(
        _serialize_forms_worker_health_snapshot(snapshot),
        separators=(",", ":"),
        sort_keys=True,
    )
    try:
        temp_path.write_text(payload, encoding="utf-8")
        temp_path.replace(health_path)
    except OSError as exc:
        _log_forms_queue_event(
            "forms_queue_worker_health_write_failed",
            error=str(exc)[:1000],
            health_file=str(health_path),
        )


def _parse_snapshot_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _read_forms_worker_health_snapshot() -> dict[str, object] | None:
    health_path = _forms_worker_health_path()
    try:
        payload = json.loads(health_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        _log_forms_queue_event(
            "forms_queue_worker_health_read_failed",
            error=str(exc)[:1000],
            health_file=str(health_path),
        )
        return None

    if not isinstance(payload, dict):
        return None

    snapshot = dict(payload)
    for field_name in FORMS_WORKER_DATETIME_FIELDS:
        snapshot[field_name] = _parse_snapshot_datetime(snapshot.get(field_name))
    return snapshot


def _build_observed_worker_snapshot(
    raw_snapshot: dict[str, object],
    *,
    reference_time: datetime,
    enabled_default: bool,
) -> dict[str, object]:
    last_heartbeat_at = raw_snapshot.get("last_heartbeat_at")
    if not isinstance(last_heartbeat_at, datetime):
        last_heartbeat_at = None

    heartbeat_age_seconds = _age_seconds(reference_time, last_heartbeat_at)
    enabled = bool(raw_snapshot.get("enabled", enabled_default))
    stale = bool(
        enabled
        and heartbeat_age_seconds is not None
        and heartbeat_age_seconds > settings.forms_worker_health_stale_seconds
    )
    running = bool(raw_snapshot.get("running", False)) and not stale
    status = str(raw_snapshot.get("status") or ("running" if running else "stopped"))
    if stale:
        status = "stale"

    return {
        "enabled": enabled,
        "running": running,
        "status": status,
        "poll_interval_seconds": settings.forms_worker_idle_poll_seconds,
        "thread_name": raw_snapshot.get("thread_name"),
        "process_id": raw_snapshot.get("process_id"),
        "started_at": raw_snapshot.get("started_at"),
        "last_heartbeat_at": last_heartbeat_at,
        "heartbeat_age_seconds": heartbeat_age_seconds,
        "stale": stale,
        "last_loop_started_at": raw_snapshot.get("last_loop_started_at"),
        "last_loop_completed_at": raw_snapshot.get("last_loop_completed_at"),
        "last_loop_processed_count": int(raw_snapshot.get("last_loop_processed_count") or 0),
        "consecutive_error_count": int(raw_snapshot.get("consecutive_error_count") or 0),
        "current_backoff_seconds": float(raw_snapshot.get("current_backoff_seconds") or 0),
        "restart_count": int(raw_snapshot.get("restart_count") or 0),
        "last_error": raw_snapshot.get("last_error"),
        "concurrency": int(raw_snapshot.get("concurrency") or settings.forms_worker_concurrency),
        "consumer_threads_alive": int(raw_snapshot.get("consumer_threads_alive") or 0),
    }


def get_forms_worker_observed_snapshot(*, reference_time: datetime | None = None) -> dict[str, object]:
    reference = reference_time or now_sgt()
    persisted_snapshot = _read_forms_worker_health_snapshot()
    if persisted_snapshot is not None:
        return _build_observed_worker_snapshot(
            persisted_snapshot,
            reference_time=reference,
            enabled_default=True,
        )

    return _build_observed_worker_snapshot(
        forms_submission_worker.snapshot(),
        reference_time=reference,
        enabled_default=settings.forms_queue_enabled,
    )


def get_forms_worker_health_failure_reason(snapshot: dict[str, object] | None = None) -> str | None:
    observed_snapshot = snapshot or get_forms_worker_observed_snapshot()
    if not bool(observed_snapshot.get("enabled")):
        return "forms worker disabled"
    if bool(observed_snapshot.get("stale")):
        return "forms worker heartbeat stale"
    if not bool(observed_snapshot.get("running")):
        return "forms worker not running"
    if int(observed_snapshot.get("consecutive_error_count") or 0) >= settings.forms_worker_unhealthy_consecutive_errors:
        return "forms worker exceeded consecutive error threshold"
    return None


def write_forms_worker_disabled_snapshot() -> None:
    _write_forms_worker_health_snapshot(
        {
            "enabled": False,
            "running": False,
            "status": "disabled",
            "thread_name": None,
            "process_id": os.getpid(),
            "started_at": None,
            "last_heartbeat_at": now_sgt(),
            "last_loop_started_at": None,
            "last_loop_completed_at": None,
            "last_loop_processed_count": 0,
            "consecutive_error_count": 0,
            "current_backoff_seconds": 0.0,
            "restart_count": 0,
            "last_error": None,
        }
    )


def get_forms_queue_diagnostics(*, db) -> dict[str, object]:
    reference_time = now_sgt()
    count_rows = db.execute(
        select(FormsSubmission.status, func.count())
        .group_by(FormsSubmission.status)
    ).all()
    counts = {status: count for status, count in count_rows}

    oldest_pending_created_at = db.execute(
        select(FormsSubmission.created_at)
        .where(FormsSubmission.status == "pending")
        .order_by(FormsSubmission.created_at)
        .limit(1)
    ).scalar_one_or_none()
    oldest_processing_created_at = db.execute(
        select(FormsSubmission.created_at)
        .where(FormsSubmission.status == "processing")
        .order_by(FormsSubmission.created_at)
        .limit(1)
    ).scalar_one_or_none()
    oldest_backlog_created_at = db.execute(
        select(FormsSubmission.created_at)
        .where(FormsSubmission.status.in_(FORMS_QUEUE_BACKLOG_STATUSES))
        .order_by(FormsSubmission.created_at)
        .limit(1)
    ).scalar_one_or_none()

    recent_processed_rows = db.execute(
        select(FormsSubmission.created_at, FormsSubmission.processed_at)
        .where(
            FormsSubmission.status.in_(FORMS_QUEUE_TERMINAL_STATUSES),
            FormsSubmission.processed_at.is_not(None),
        )
        .order_by(FormsSubmission.processed_at.desc())
        .limit(FORMS_QUEUE_RECENT_PROCESSING_SAMPLE_SIZE)
    ).all()
    recent_processing_ms = _recent_processing_durations_ms(recent_processed_rows)
    worker_snapshot = get_forms_worker_observed_snapshot(reference_time=reference_time)

    return {
        "generated_at": reference_time,
        "backlog_count": counts.get("pending", 0) + counts.get("processing", 0),
        "pending_count": counts.get("pending", 0),
        "processing_count": counts.get("processing", 0),
        "success_count": counts.get("success", 0),
        "failed_count": counts.get("failed", 0),
        "oldest_backlog_age_seconds": _age_seconds(reference_time, oldest_backlog_created_at),
        "oldest_pending_age_seconds": _age_seconds(reference_time, oldest_pending_created_at),
        "oldest_processing_age_seconds": _age_seconds(reference_time, oldest_processing_created_at),
        "recent_average_processing_ms": (
            int(sum(recent_processing_ms) / len(recent_processing_ms)) if recent_processing_ms else None
        ),
        "recent_processed_sample_size": len(recent_processing_ms),
        "worker": worker_snapshot,
    }


def _assets_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "assets"


_WORKER_DOWN_WARN_DEBOUNCE_SECONDS = 300
_worker_down_warn_state: dict[str, Any] = {"last_emitted_at": None}
_worker_down_warn_lock = threading.Lock()


def is_forms_worker_healthy_now(*, snapshot: dict[str, Any] | None = None) -> bool:
    return get_forms_worker_health_failure_reason(snapshot=snapshot) is None


def _should_emit_worker_down_warning(reference_time: datetime) -> bool:
    with _worker_down_warn_lock:
        last_emitted_at = _worker_down_warn_state.get("last_emitted_at")
        if last_emitted_at is not None:
            elapsed_seconds = (reference_time - last_emitted_at).total_seconds()
            if elapsed_seconds < _WORKER_DOWN_WARN_DEBOUNCE_SECONDS:
                return False
        _worker_down_warn_state["last_emitted_at"] = reference_time
        return True


def reset_worker_down_warn_debounce_state() -> None:
    with _worker_down_warn_lock:
        _worker_down_warn_state["last_emitted_at"] = None


def _maybe_emit_worker_down_warning(
    db,
    *,
    request_id: str,
    reference_time: datetime | None = None,
) -> bool:
    reference = reference_time or now_sgt()
    snapshot = get_forms_worker_observed_snapshot(reference_time=reference)
    reason = get_forms_worker_health_failure_reason(snapshot=snapshot)
    if reason is None:
        return False
    if not _should_emit_worker_down_warning(reference):
        return False
    backlog_count = int(snapshot.get("last_loop_processed_count") or 0)
    log_event(
        db,
        source="system",
        action="forms_warn",
        status="warning",
        message="Forms enqueued while worker is down",
        details=(
            f"reason={reason}; "
            f"running={bool(snapshot.get('running'))}; "
            f"stale={bool(snapshot.get('stale'))}; "
            f"request_id={request_id}; "
            f"last_heartbeat_at={snapshot.get('last_heartbeat_at')}; "
            f"recent_processed={backlog_count}"
        ),
    )
    return True


def enqueue_forms_submission(
    db,
    *,
    request_id: str,
    rfid: str | None,
    action: str,
    chave: str,
    projeto: str,
    device_id: str | None,
    local: str | None,
    event_time: datetime | None = None,
    request_path: str | None = None,
    project_candidates: list[str] | tuple[str, ...] | None = None,
    ontime: bool = True,
) -> FormsSubmission:
    timestamp = now_sgt()
    submission = FormsSubmission(
        request_id=request_id,
        rfid=rfid,
        action=action,
        chave=chave,
        projeto=projeto,
        device_id=device_id,
        local=local,
        event_time=event_time,
        request_path=request_path,
        display_status=None,
        project_candidates_json=_dump_project_candidates_json(project_candidates),
        ontime=ontime,
        status="pending",
        retry_count=0,
        last_error=None,
        created_at=timestamp,
        updated_at=timestamp,
        processed_at=None,
    )
    db.add(submission)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise
    _maybe_emit_worker_down_warning(db, request_id=request_id, reference_time=timestamp)
    return submission


def record_forms_submission_skip(
    db,
    *,
    request_id: str,
    rfid: str | None,
    action: str,
    chave: str,
    projeto: str,
    device_id: str | None,
    local: str | None,
    event_time: datetime | None = None,
    request_path: str | None = None,
    project_candidates: list[str] | tuple[str, ...] | None = None,
    ontime: bool = True,
    skip_reason: str | None = None,
) -> FormsSubmission:
    timestamp = now_sgt()
    submission = FormsSubmission(
        request_id=request_id,
        rfid=rfid,
        action=action,
        chave=chave,
        projeto=projeto,
        device_id=device_id,
        local=local,
        event_time=event_time,
        request_path=request_path,
        display_status="not_realized",
        project_candidates_json=_dump_project_candidates_json(project_candidates),
        ontime=ontime,
        status="skipped",
        retry_count=0,
        last_error=skip_reason,
        created_at=timestamp,
        updated_at=timestamp,
        processed_at=timestamp,
    )
    db.add(submission)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise
    return submission


def process_forms_submission_queue_once(*, max_items: int = 10) -> int:
    processed = 0
    while processed < max_items:
        submission_id = _reserve_next_submission_id()
        if submission_id is None:
            break
        _process_submission(submission_id)
        processed += 1
    return processed


def _select_next_pending_submission_row(db):
    return db.execute(
        select(FormsSubmission.id, FormsSubmission.request_id)
        .where(FormsSubmission.status == "pending")
        .order_by(FormsSubmission.id)
        .limit(1)
    ).first()


def _claim_submission_for_processing(db, *, submission_id: int, updated_at: datetime) -> bool:
    updated_rows = db.execute(
        update(FormsSubmission)
        .where(
            FormsSubmission.id == submission_id,
            FormsSubmission.status == "pending",
        )
        .values(status="processing", updated_at=updated_at)
    )
    return updated_rows.rowcount == 1


def _reserve_next_submission_id() -> int | None:
    with SessionLocal() as db:
        for _ in range(FORMS_QUEUE_MAX_CLAIM_ATTEMPTS):
            submission = _select_next_pending_submission_row(db)
            if submission is None:
                return None

            updated_at = now_sgt()
            if not _claim_submission_for_processing(db, submission_id=submission.id, updated_at=updated_at):
                db.rollback()
                continue

            db.commit()
            _log_forms_queue_event(
                "forms_queue_reserved",
                request_id=submission.request_id,
                status="processing",
                submission_id=submission.id,
            )
            return submission.id
        return None


def _process_submission(submission_id: int) -> None:
    from .forms_worker import FormsWorker

    with SessionLocal() as db:
        submission = db.get(FormsSubmission, submission_id)
        if submission is None or submission.status != "processing":
            return

        worker = FormsWorker(assets_dir=_assets_dir())

        def _status_callback(status_label: str) -> None:
            display_status = _normalize_display_status_from_worker_label(status_label)
            if display_status is None:
                return
            _persist_submission_display_status(
                db,
                submission_id=submission.id,
                action=submission.action,
                display_status=display_status,
            )

        result = worker.submit_with_retries(
            action=submission.action,
            chave=submission.chave,
            projeto=submission.projeto,
            ontime=submission.ontime,
            project_candidates=_load_project_candidates_json(submission.project_candidates_json),
            status_callback=_status_callback,
        )

        submission = db.get(FormsSubmission, submission_id)
        if submission is None:
            return

        final_audit_event = next(
            (
                event
                for event in reversed(result.get("audit_events", []))
                if event.get("status") in {"completed", "failed"}
            ),
            None,
        )

        submission.retry_count = result.get("retry_count", 0)
        submission.updated_at = now_sgt()
        submission.processed_at = now_sgt()
        if result.get("success"):
            submission.status = "success"
            submission.last_error = None
        else:
            submission.status = "failed"
            submission.last_error = (result.get("message") or "unknown error")[:1000]
        if result.get("error_code") == "forms_step_timeout":
            submission.display_status = "not_found"
        elif submission.display_status is None:
            submission.display_status = FORMS_TERMINAL_DISPLAY_STATUS_BY_RESULT[bool(result.get("success"))]

        log_event(
            db,
            idempotency_key=f"{submission.request_id}:result",
            source="forms",
            action=submission.action,
            status="success" if result.get("success") else "failed",
            message=result.get("message", "Forms submission processed"),
            rfid=submission.rfid,
            project=submission.projeto,
            device_id=submission.device_id,
            local=submission.local,
            request_path=submission.request_path or "/api/scan",
            http_status=200 if result.get("success") else 500,
            ontime=submission.ontime,
            submitted_at=submission.processed_at if result.get("success") else None,
            retry_count=result.get("retry_count", 0),
            details=(
                (
                    f"chave={submission.chave}; "
                    f"ontime={submission.ontime}; "
                    f"queue_status={submission.status}; "
                    f"display_status={submission.display_status or '-'}; "
                    f"error_code={result.get('error_code', 'none')}; "
                    f"failed_step={result.get('failed_step', '-')}; "
                    f"forms_details={final_audit_event.get('details', '-') if final_audit_event else '-'}"
                )[:1000]
            ),
        )
        db.commit()
        _log_forms_queue_event(
            "forms_queue_processed",
            action=submission.action,
            error_code=result.get("error_code"),
            failed_step=result.get("failed_step"),
            request_id=submission.request_id,
            retry_count=submission.retry_count,
            status=submission.status,
            submission_id=submission.id,
            turnaround_ms=_recent_processing_durations_ms([(submission.created_at, submission.processed_at)])[0],
        )
        notify_admin_data_changed(submission.action)


class FormsSubmissionWorker:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._consumer_threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._status = "stopped"
        self._started_at: datetime | None = None
        self._start_count = 0
        self._per_thread: dict[int, dict] = {}
        self._supervisor_backoff_seconds = 0.0

    def start(self) -> None:
        """Idempotente. Spawna threads consumidoras faltantes até atingir concurrency."""
        with self._lock:
            if self._stop_event.is_set():
                self._stop_event = threading.Event()
            target_count = max(int(settings.forms_worker_concurrency), 1)
            alive = [t for t in self._consumer_threads if t.is_alive()]
            self._consumer_threads = alive
            if len(alive) >= target_count:
                return
            if not alive:
                self._started_at = now_sgt()
                self._per_thread = {}
                self._start_count += 1
                self._status = "starting"
            for _ in range(target_count - len(alive)):
                thread_index = len(self._consumer_threads)
                t = threading.Thread(
                    target=self._run_consumer,
                    name=f"forms-submission-worker-{thread_index}",
                    daemon=True,
                )
                self._consumer_threads.append(t)
                t.start()
        _log_forms_queue_event(
            "forms_queue_worker_started",
            poll_interval_seconds=settings.forms_worker_idle_poll_seconds,
            concurrency=target_count,
        )

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            threads = list(self._consumer_threads)
        for t in threads:
            t.join(timeout=2)
        with self._lock:
            self._consumer_threads = []
            self._status = "stopped"
        _log_forms_queue_event("forms_queue_worker_stopped")

    def stop_requested(self) -> bool:
        return self._stop_event.is_set()

    def has_alive_consumers(self) -> bool:
        """API pública usada pelo supervisor (substitui leitura direta de _thread)."""
        with self._lock:
            return any(t.is_alive() for t in self._consumer_threads)

    def consumer_threads_alive_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._consumer_threads if t.is_alive())

    def mark_supervisor_restart_wait(self, *, backoff_seconds: float) -> None:
        with self._lock:
            self._status = "restarting"
            self._supervisor_backoff_seconds = backoff_seconds

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            alive_count = sum(1 for t in self._consumer_threads if t.is_alive())
            states = list(self._per_thread.values())
            running = alive_count > 0
            if self._status == "restarting":
                aggregated_status = "restarting"
            elif any(s.get("status") == "degraded" for s in states):
                aggregated_status = "degraded"
            elif alive_count == 0:
                aggregated_status = "stopped"
            elif any(s.get("status") == "running" for s in states):
                aggregated_status = "running"
            else:
                aggregated_status = "idle"
            last_loop_started_at = max(
                (s.get("last_loop_started_at") for s in states if s.get("last_loop_started_at")),
                default=None,
            )
            last_loop_completed_at = max(
                (s.get("last_loop_completed_at") for s in states if s.get("last_loop_completed_at")),
                default=None,
            )
            processed_total = sum(int(s.get("processed_total") or 0) for s in states)
            max_consecutive_errors = max((int(s.get("consecutive_errors") or 0) for s in states), default=0)
            max_backoff = max((float(s.get("current_backoff_seconds") or 0) for s in states), default=0.0)
            last_error = next(
                (s.get("last_error") for s in states if s.get("last_error")),
                None,
            )
            primary_thread_name = (
                self._consumer_threads[0].name
                if self._consumer_threads and self._consumer_threads[0].is_alive()
                else None
            )
            return {
                "running": running,
                "status": aggregated_status,
                "thread_name": primary_thread_name,
                "started_at": self._started_at,
                "last_loop_started_at": last_loop_started_at,
                "last_loop_completed_at": last_loop_completed_at,
                "last_loop_processed_count": processed_total,
                "consecutive_error_count": max_consecutive_errors,
                "current_backoff_seconds": max(max_backoff, self._supervisor_backoff_seconds),
                "restart_count": max(self._start_count - 1, 0),
                "last_error": last_error,
                "concurrency": int(settings.forms_worker_concurrency),
                "consumer_threads_alive": alive_count,
            }

    def _run_consumer(self) -> None:
        """Loop por thread consumidora — self-watchdog, nunca sai voluntariamente."""
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        with self._lock:
            self._per_thread[thread_id] = {
                "thread_name": thread_name,
                "status": "running",
                "last_loop_started_at": None,
                "last_loop_completed_at": None,
                "processed_total": 0,
                "consecutive_errors": 0,
                "current_backoff_seconds": 0.0,
                "last_error": None,
            }

        while not self._stop_event.is_set():
            with self._lock:
                state = self._per_thread[thread_id]
                state["status"] = "running"
                state["last_loop_started_at"] = now_sgt()

            try:
                submission_id = _reserve_next_submission_id()
                if submission_id is None:
                    processed = 0
                else:
                    _process_submission(submission_id)
                    processed = 1
            except Exception as exc:
                backoff_seconds = _compute_exponential_backoff_seconds(
                    base_seconds=FORMS_WORKER_ERROR_BACKOFF_BASE_SECONDS,
                    max_seconds=FORMS_WORKER_ERROR_BACKOFF_MAX_SECONDS,
                    attempt=state["consecutive_errors"] + 1,
                )
                with self._lock:
                    state["status"] = "degraded"
                    state["last_loop_completed_at"] = now_sgt()
                    state["consecutive_errors"] += 1
                    state["current_backoff_seconds"] = backoff_seconds
                    state["last_error"] = str(exc)[:1000]
                _log_forms_queue_event(
                    "forms_queue_consumer_error",
                    backoff_seconds=backoff_seconds,
                    consecutive_error_count=state["consecutive_errors"],
                    error=str(exc)[:1000],
                    thread_name=thread_name,
                )
                self._stop_event.wait(backoff_seconds)
                continue

            with self._lock:
                state["status"] = "idle" if processed == 0 else "running"
                state["last_loop_completed_at"] = now_sgt()
                state["processed_total"] += processed
                state["consecutive_errors"] = 0
                state["current_backoff_seconds"] = 0.0
                state["last_error"] = None
            if processed == 0:
                self._stop_event.wait(settings.forms_worker_idle_poll_seconds)


forms_submission_worker = FormsSubmissionWorker()


def run_forms_submission_worker_forever() -> None:
    supervisor_restart_count = 0
    _log_forms_queue_event(
        "forms_queue_worker_supervisor_started",
        health_file=str(_forms_worker_health_path()),
        heartbeat_interval_seconds=settings.forms_worker_health_update_seconds,
        process_id=os.getpid(),
    )
    try:
        forms_submission_worker.start()
        while True:
            worker_snapshot = forms_submission_worker.snapshot()
            _write_forms_worker_health_snapshot(
                {
                    **worker_snapshot,
                    "enabled": True,
                    "last_heartbeat_at": now_sgt(),
                    "process_id": os.getpid(),
                    "restart_count": max(int(worker_snapshot.get("restart_count") or 0), supervisor_restart_count),
                }
            )

            if forms_submission_worker.has_alive_consumers():
                if forms_submission_worker._stop_event.wait(settings.forms_worker_health_update_seconds):
                    break
                continue

            if forms_submission_worker.stop_requested():
                break

            supervisor_restart_count += 1
            backoff_seconds = _compute_exponential_backoff_seconds(
                base_seconds=FORMS_WORKER_SUPERVISOR_RESTART_BASE_SECONDS,
                max_seconds=FORMS_WORKER_SUPERVISOR_RESTART_MAX_SECONDS,
                attempt=supervisor_restart_count,
            )
            forms_submission_worker.mark_supervisor_restart_wait(backoff_seconds=backoff_seconds)
            _write_forms_worker_health_snapshot(
                {
                    **forms_submission_worker.snapshot(),
                    "enabled": True,
                    "last_heartbeat_at": now_sgt(),
                    "process_id": os.getpid(),
                    "restart_count": supervisor_restart_count,
                }
            )
            _log_forms_queue_event(
                "forms_queue_worker_supervisor_restart_scheduled",
                backoff_seconds=backoff_seconds,
                last_error=forms_submission_worker.snapshot().get("last_error"),
                restart_count=supervisor_restart_count,
            )
            if forms_submission_worker._stop_event.wait(backoff_seconds):
                break
            forms_submission_worker.start()
    except KeyboardInterrupt:
        pass
    finally:
        forms_submission_worker.stop()
        _write_forms_worker_health_snapshot(
            {
                **forms_submission_worker.snapshot(),
                "enabled": True,
                "last_heartbeat_at": now_sgt(),
                "process_id": os.getpid(),
                "restart_count": supervisor_restart_count,
            }
        )
        _log_forms_queue_event(
            "forms_queue_worker_supervisor_stopped",
            process_id=os.getpid(),
            restart_count=supervisor_restart_count,
        )