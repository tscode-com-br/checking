"""Tests for the defense-in-depth warning emitted by ``enqueue_forms_submission``
when the Forms worker is observed as down or stale.

These tests cover the contract introduced in Deploy A.5:

  - ``is_forms_worker_healthy_now`` returns ``True``/``False`` matching the
    worker snapshot.
  - ``enqueue_forms_submission`` emits a CheckEvent with
    ``action='forms_warn'`` when the worker is down at enqueue time.
  - The warning is debounced to once per 5 minutes per process.
  - When the worker is healthy, no warning is emitted.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import CheckEvent
from sistema.app.services import forms_queue
from sistema.app.services.forms_queue import (
    _WORKER_DOWN_WARN_DEBOUNCE_SECONDS,
    enqueue_forms_submission,
    is_forms_worker_healthy_now,
    reset_worker_down_warn_debounce_state,
)
from sistema.app.services.time_utils import now_sgt


def _make_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(
        f"sqlite+pysqlite:///{(tmp_path / 'test_worker_warn.db').as_posix()}"
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
    )
    return factory()


def _enqueue(
    db: Session,
    *,
    request_id: str = "req-abc-001",
    chave: str = "AAAA",
    action: str = "checkin",
):
    return enqueue_forms_submission(
        db,
        request_id=request_id,
        rfid=None,
        action=action,
        chave=chave,
        projeto="P80",
        device_id=None,
        local="Escritório",
    )


def _count_forms_warn(db: Session) -> int:
    return db.execute(
        sa.select(sa.func.count())
        .select_from(CheckEvent)
        .where(CheckEvent.action == "forms_warn")
    ).scalar() or 0


def test_is_forms_worker_healthy_now_returns_true_for_healthy_snapshot():
    healthy_snapshot = {
        "enabled": True,
        "running": True,
        "stale": False,
        "consecutive_error_count": 0,
    }
    with patch.object(
        forms_queue, "get_forms_worker_observed_snapshot", return_value=healthy_snapshot
    ):
        assert is_forms_worker_healthy_now() is True


def test_is_forms_worker_healthy_now_returns_false_when_disabled():
    disabled_snapshot = {
        "enabled": False,
        "running": False,
        "stale": False,
        "consecutive_error_count": 0,
    }
    with patch.object(
        forms_queue, "get_forms_worker_observed_snapshot", return_value=disabled_snapshot
    ):
        assert is_forms_worker_healthy_now() is False


def test_is_forms_worker_healthy_now_returns_false_when_stale():
    stale_snapshot = {
        "enabled": True,
        "running": True,
        "stale": True,
        "consecutive_error_count": 0,
    }
    with patch.object(
        forms_queue, "get_forms_worker_observed_snapshot", return_value=stale_snapshot
    ):
        assert is_forms_worker_healthy_now() is False


def test_enqueue_emits_warning_when_worker_is_down(tmp_path: Path):
    reset_worker_down_warn_debounce_state()
    db = _make_session(tmp_path)

    down_snapshot = {
        "enabled": True,
        "running": False,
        "stale": False,
        "consecutive_error_count": 0,
        "last_heartbeat_at": None,
        "last_loop_processed_count": 0,
    }

    with patch.object(
        forms_queue, "get_forms_worker_observed_snapshot", return_value=down_snapshot
    ):
        _enqueue(db, request_id="req-down-1")
        db.commit()

    assert _count_forms_warn(db) == 1
    warn_event = db.execute(
        sa.select(CheckEvent).where(CheckEvent.action == "forms_warn")
    ).scalar_one()
    assert warn_event.status == "warning"
    assert warn_event.source == "system"
    assert "worker is down" in warn_event.message.lower()
    assert "request_id=req-down-1" in (warn_event.details or "")


def test_enqueue_does_not_emit_warning_when_worker_is_healthy(tmp_path: Path):
    reset_worker_down_warn_debounce_state()
    db = _make_session(tmp_path)

    healthy_snapshot = {
        "enabled": True,
        "running": True,
        "stale": False,
        "consecutive_error_count": 0,
        "last_heartbeat_at": now_sgt(),
        "last_loop_processed_count": 0,
    }

    with patch.object(
        forms_queue, "get_forms_worker_observed_snapshot", return_value=healthy_snapshot
    ):
        _enqueue(db, request_id="req-healthy-1")
        db.commit()

    assert _count_forms_warn(db) == 0


def test_enqueue_debounces_warnings_within_window(tmp_path: Path):
    reset_worker_down_warn_debounce_state()
    db = _make_session(tmp_path)

    down_snapshot = {
        "enabled": True,
        "running": False,
        "stale": False,
        "consecutive_error_count": 0,
        "last_heartbeat_at": None,
        "last_loop_processed_count": 0,
    }

    with patch.object(
        forms_queue, "get_forms_worker_observed_snapshot", return_value=down_snapshot
    ):
        for index in range(5):
            _enqueue(db, request_id=f"req-debounce-{index}")
            db.commit()

    assert _count_forms_warn(db) == 1, (
        "Only the first of five quick enqueues should produce a warning event"
    )


def test_enqueue_emits_new_warning_after_debounce_window_expires(tmp_path: Path):
    reset_worker_down_warn_debounce_state()
    db = _make_session(tmp_path)

    down_snapshot = {
        "enabled": True,
        "running": False,
        "stale": False,
        "consecutive_error_count": 0,
        "last_heartbeat_at": None,
        "last_loop_processed_count": 0,
    }

    base_time = now_sgt()
    later_time = base_time + timedelta(
        seconds=_WORKER_DOWN_WARN_DEBOUNCE_SECONDS + 1
    )

    with patch.object(
        forms_queue, "get_forms_worker_observed_snapshot", return_value=down_snapshot
    ), patch.object(forms_queue, "now_sgt", side_effect=[base_time, later_time]):
        _enqueue(db, request_id="req-window-1")
        db.commit()
        _enqueue(db, request_id="req-window-2")
        db.commit()

    assert _count_forms_warn(db) == 2, (
        "After the debounce window expires, a new warning event must be emitted"
    )
