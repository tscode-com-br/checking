from __future__ import annotations

import threading
from pathlib import Path
from time import sleep

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..database import SessionLocal
from ..models import FormsSubmission
from .admin_updates import notify_admin_data_changed
from .event_logger import log_event
from .forms_worker import FormsWorker
from .time_utils import now_sgt

FORMS_QUEUE_POLL_SECONDS = 0.25


def _assets_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "assets"


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


def _reserve_next_submission_id() -> int | None:
    with SessionLocal() as db:
        submission = db.execute(
            select(FormsSubmission)
            .where(FormsSubmission.status == "pending")
            .order_by(FormsSubmission.id)
            .limit(1)
        ).scalar_one_or_none()
        if submission is None:
            return None

        submission.status = "processing"
        submission.updated_at = now_sgt()
        db.commit()
        return submission.id


def _process_submission(submission_id: int) -> None:
    with SessionLocal() as db:
        submission = db.get(FormsSubmission, submission_id)
        if submission is None or submission.status != "processing":
            return

        worker = FormsWorker(assets_dir=_assets_dir())
        result = worker.submit_with_retries(
            action=submission.action,
            chave=submission.chave,
            projeto=submission.projeto,
            ontime=submission.ontime,
        )

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
            request_path="/api/scan",
            http_status=200 if result.get("success") else 500,
            ontime=submission.ontime,
            submitted_at=submission.processed_at if result.get("success") else None,
            retry_count=result.get("retry_count", 0),
            details=(
                (
                    f"chave={submission.chave}; "
                    f"ontime={submission.ontime}; "
                    f"queue_status={submission.status}; "
                    f"error_code={result.get('error_code', 'none')}; "
                    f"failed_step={result.get('failed_step', '-')}; "
                    f"forms_details={final_audit_event.get('details', '-') if final_audit_event else '-'}"
                )[:1000]
            ),
        )
        db.commit()
        notify_admin_data_changed(submission.action)


class FormsSubmissionWorker:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._run, name="forms-submission-worker", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            thread = self._thread
            if thread is None:
                return
            self._stop_event.set()
        thread.join(timeout=2)
        with self._lock:
            self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            processed = process_forms_submission_queue_once(max_items=10)
            if processed == 0:
                self._stop_event.wait(FORMS_QUEUE_POLL_SECONDS)
            else:
                sleep(0)


forms_submission_worker = FormsSubmissionWorker()