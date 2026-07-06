"""Tests for the forms-worker self-recycling + orphan reclamation added after the 2026-07-06
production incident (the worker leaked OS threads over ~13 days until Playwright could no longer
fork Chromium — BlockingIOError/EAGAIN — and silently stopped filling the Forms; because docker's
``restart: unless-stopped`` only fires on process EXIT, a merely-wedged process never recovered).

Covered contracts:
  - ``_should_recycle_after_submissions`` / ``_should_recycle_after_errors`` pure gates (<=0 disables).
  - ``_request_recycle`` sets the stop event and records the (first) reason.
  - ``reclaim_orphaned_processing_submissions`` resets stranded 'processing' rows to 'pending'.
  - ``_run_consumer`` recycles the process proactively after N submissions and reactively after N
    consecutive infra-level errors.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import FormsSubmission
from sistema.app.services import forms_queue
from sistema.app.services.forms_queue import (
    FormsSubmissionWorker,
    _should_recycle_after_errors,
    _should_recycle_after_submissions,
    reclaim_orphaned_processing_submissions,
)


def _make_factory(tmp_path: Path) -> sessionmaker:
    engine = sa.create_engine(
        f"sqlite+pysqlite:///{(tmp_path / 'test_recycle.db').as_posix()}"
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def _add_submission(db: Session, *, request_id: str, status: str) -> None:
    now = datetime.now(timezone.utc)
    db.add(
        FormsSubmission(
            request_id=request_id,
            action="checkin",
            chave="AAAA",
            projeto="P80",
            status=status,
            retry_count=0,
            created_at=now,
            updated_at=now,
        )
    )


# --------------------------------------------------------------------------- pure gates


def test_should_recycle_after_submissions_gate():
    assert _should_recycle_after_submissions(lifetime_processed=200, max_submissions=200) is True
    assert _should_recycle_after_submissions(lifetime_processed=201, max_submissions=200) is True
    assert _should_recycle_after_submissions(lifetime_processed=199, max_submissions=200) is False
    # <=0 disables the guard entirely.
    assert _should_recycle_after_submissions(lifetime_processed=10_000, max_submissions=0) is False
    assert _should_recycle_after_submissions(lifetime_processed=10_000, max_submissions=-1) is False


def test_should_recycle_after_errors_gate():
    assert _should_recycle_after_errors(consecutive_errors=5, max_errors=5) is True
    assert _should_recycle_after_errors(consecutive_errors=6, max_errors=5) is True
    assert _should_recycle_after_errors(consecutive_errors=4, max_errors=5) is False
    assert _should_recycle_after_errors(consecutive_errors=10_000, max_errors=0) is False
    assert _should_recycle_after_errors(consecutive_errors=10_000, max_errors=-3) is False


# --------------------------------------------------------------------------- _request_recycle


def test_request_recycle_sets_stop_event_and_records_first_reason():
    worker = FormsSubmissionWorker()
    assert worker.stop_requested() is False

    worker._request_recycle("first-reason")
    assert worker.stop_requested() is True
    assert worker.snapshot()["recycle_reason"] == "first-reason"

    # First reason wins — a second recycle during wind-down does not overwrite it.
    worker._request_recycle("second-reason")
    assert worker.snapshot()["recycle_reason"] == "first-reason"


# --------------------------------------------------------------------------- reclamation


def test_reclaim_resets_only_processing_rows(tmp_path: Path, monkeypatch):
    factory = _make_factory(tmp_path)
    with factory() as db:
        _add_submission(db, request_id="proc-1", status="processing")
        _add_submission(db, request_id="proc-2", status="processing")
        _add_submission(db, request_id="pending-1", status="pending")
        _add_submission(db, request_id="success-1", status="success")
        db.commit()

    monkeypatch.setattr(forms_queue, "SessionLocal", factory)
    reclaimed = reclaim_orphaned_processing_submissions()
    assert reclaimed == 2

    with factory() as db:
        statuses = dict(
            db.execute(sa.select(FormsSubmission.request_id, FormsSubmission.status)).all()
        )
    assert statuses["proc-1"] == "pending"
    assert statuses["proc-2"] == "pending"
    assert statuses["pending-1"] == "pending"
    assert statuses["success-1"] == "success"  # terminal rows untouched


def test_reclaim_is_noop_when_no_processing_rows(tmp_path: Path, monkeypatch):
    factory = _make_factory(tmp_path)
    with factory() as db:
        _add_submission(db, request_id="pending-only", status="pending")
        db.commit()
    monkeypatch.setattr(forms_queue, "SessionLocal", factory)
    assert reclaim_orphaned_processing_submissions() == 0


# --------------------------------------------------------------------------- _run_consumer recycle


def _run_consumer_to_completion(worker: FormsSubmissionWorker, *, timeout: float = 5.0) -> threading.Thread:
    thread = threading.Thread(target=worker._run_consumer, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    return thread


def test_run_consumer_recycles_after_max_submissions(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(forms_queue.settings, "forms_worker_max_submissions_per_process", 3)
    monkeypatch.setattr(forms_queue.settings, "forms_worker_max_consecutive_errors_before_recycle", 0)
    # Each loop successfully "processes" one submission; no idle waits.
    monkeypatch.setattr(forms_queue, "_reserve_next_submission_id", lambda: 1)
    monkeypatch.setattr(forms_queue, "_process_submission", lambda submission_id: None)

    worker = FormsSubmissionWorker()
    thread = _run_consumer_to_completion(worker)

    assert not thread.is_alive(), "consumer must exit after reaching the submission cap"
    assert worker.stop_requested() is True
    assert worker._lifetime_processed >= 3
    assert "max_submissions_per_process" in (worker.snapshot()["recycle_reason"] or "")


def test_run_consumer_recycles_after_consecutive_errors(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(forms_queue.settings, "forms_worker_max_submissions_per_process", 0)
    monkeypatch.setattr(forms_queue.settings, "forms_worker_max_consecutive_errors_before_recycle", 2)
    monkeypatch.setattr(forms_queue, "FORMS_WORKER_ERROR_BACKOFF_BASE_SECONDS", 0.01)
    monkeypatch.setattr(forms_queue, "FORMS_WORKER_ERROR_BACKOFF_MAX_SECONDS", 0.02)

    def _boom() -> int:
        raise RuntimeError("cannot fork")

    monkeypatch.setattr(forms_queue, "_reserve_next_submission_id", _boom)

    worker = FormsSubmissionWorker()
    thread = _run_consumer_to_completion(worker)

    assert not thread.is_alive(), "consumer must exit after the consecutive-error cap"
    assert worker.stop_requested() is True
    assert "consecutive_errors" in (worker.snapshot()["recycle_reason"] or "")
