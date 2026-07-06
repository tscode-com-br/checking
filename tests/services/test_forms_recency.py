"""24h FORMS recency window (multi-day offline replay), server side.

The CLIENT decides recency (only it sees the full offline backlog) and signals it via `fill_forms` on
the check submit. The server contract: when `fill_forms=False`, the activity is still recorded in
user_sync_events + CheckingHistory at its REAL event time, but no FORMS submission is enqueued (it is
recorded as a skip with reason `offline_beyond_24h`). `fill_forms=True` (the default) is unchanged
behaviour. See the client side in checking_kotlin PendingCheckReplayer.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import CheckingHistory, FormsSubmission, Project, User, UserSyncEvent
from sistema.app.routers.web_check import WEB_CHECK_CHANNEL
from sistema.app.schemas import MobileSyncStateResponse
from sistema.app.services.forms_submit import submit_forms_event
from sistema.app.services.user_sync import ensure_web_user

_EVENT_TIME = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
_PROJECT_NAME = "P-RECENCY"


def _make_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / 'test_recency.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)()


def _make_project(db: Session) -> Project:
    proj = Project(
        name=_PROJECT_NAME,
        country_code="SG",
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address="1 Recency Way",
        zip_code="000022",
        forms_enabled=True,
        transport_enabled=True,
        emergency_phone="",
    )
    db.add(proj)
    db.commit()
    return proj


def _stub_sync_state(chave: str) -> MobileSyncStateResponse:
    return MobileSyncStateResponse(found=True, chave=chave)


def _submit(db, *, chave, action, client_event_id, fill_forms=True, informe="normal"):
    with patch(
        "sistema.app.services.forms_submit.build_mobile_sync_state",
        side_effect=lambda db_, *, chave: _stub_sync_state(chave),
    ), patch(
        "sistema.app.services.forms_submit.fire_accident_hook_for_check_event",
        return_value=None,
    ), patch(
        "sistema.app.services.forms_submit.enqueue_forms_submission",
        wraps=_stub_enqueue,
    ), patch(
        # Isolate recency from latest-activity resolution, which sorts mixed naive/aware datetimes read
        # back from SQLite (a tz artifact of the test DB, not prod). Same shim as test_forms_submit_per_project.
        "sistema.app.services.forms_submit.resolve_latest_internal_user_activity",
        return_value=None,
    ):
        return submit_forms_event(
            db,
            chave=chave,
            projeto=_PROJECT_NAME,
            action=action,
            informe=informe,
            local="Escritório",
            event_time=_EVENT_TIME,
            client_event_id=client_event_id,
            ensure_user=ensure_web_user,
            channel=WEB_CHECK_CHANNEL,
            fill_forms=fill_forms,
        )


def _stub_enqueue(db: Session, **kwargs) -> FormsSubmission:
    from sistema.app.services.time_utils import now_sgt

    now = now_sgt()
    submission = FormsSubmission(
        request_id=kwargs["request_id"],
        rfid=kwargs.get("rfid"),
        action=kwargs["action"],
        chave=kwargs["chave"],
        projeto=kwargs["projeto"],
        device_id=kwargs.get("device_id"),
        local=kwargs.get("local"),
        event_time=kwargs.get("event_time"),
        request_path=kwargs.get("request_path"),
        display_status="pending",
        ontime=kwargs.get("ontime", True),
        status="pending",
        retry_count=0,
        last_error=None,
        created_at=now,
        updated_at=now,
    )
    db.add(submission)
    db.flush()
    return submission


def _rows(db, chave) -> list[FormsSubmission]:
    return list(
        db.execute(sa.select(FormsSubmission).where(FormsSubmission.chave == chave)).scalars().all()
    )


def _as_sgt_instant(value: datetime) -> datetime:
    """Re-attach the project zone to a naive datetime read back from SQLite so instants compare."""
    return value.replace(tzinfo=ZoneInfo("Asia/Singapore")) if value.tzinfo is None else value


def test_fill_forms_true_enqueues(tmp_path: Path):
    db = _make_session(tmp_path)
    _make_project(db)

    response = _submit(db, chave="RC01", action="checkin", client_event_id="rc-fill", fill_forms=True)

    assert response.queued_forms is True
    assert _rows(db, "RC01")[0].status == "pending"


def test_fill_forms_false_skips_forms_but_records_history_at_real_time(tmp_path: Path):
    db = _make_session(tmp_path)
    _make_project(db)

    response = _submit(db, chave="RC02", action="checkin", client_event_id="rc-nofill", fill_forms=False)

    # FORMS skipped …
    assert response.queued_forms is False
    row = _rows(db, "RC02")[0]
    assert row.status == "skipped"
    assert row.last_error == "offline_beyond_24h"

    # … but the activity IS registered, at its REAL instant. The DB stores the SGT-normalized time
    # naive (a SQLite artifact), so re-attach SGT and compare instants.
    sync = db.execute(sa.select(UserSyncEvent).where(UserSyncEvent.chave == "RC02")).scalar_one()
    assert _as_sgt_instant(sync.event_time) == _EVENT_TIME
    hist = db.execute(sa.select(CheckingHistory).where(CheckingHistory.chave == "RC02")).scalar_one()
    assert _as_sgt_instant(hist.time) == _EVENT_TIME
    assert hist.atividade == "check-in"


def test_fill_forms_defaults_true(tmp_path: Path):
    """A caller that omits fill_forms (older client / live submission) enqueues, unchanged."""
    db = _make_session(tmp_path)
    _make_project(db)

    with patch(
        "sistema.app.services.forms_submit.build_mobile_sync_state",
        side_effect=lambda db_, *, chave: _stub_sync_state(chave),
    ), patch(
        "sistema.app.services.forms_submit.fire_accident_hook_for_check_event",
        return_value=None,
    ), patch(
        "sistema.app.services.forms_submit.enqueue_forms_submission",
        wraps=_stub_enqueue,
    ), patch(
        "sistema.app.services.forms_submit.resolve_latest_internal_user_activity",
        return_value=None,
    ):
        response = submit_forms_event(
            db,
            chave="RC03",
            projeto=_PROJECT_NAME,
            action="checkin",
            informe="normal",
            local="Escritório",
            event_time=_EVENT_TIME,
            client_event_id="rc-default",
            ensure_user=ensure_web_user,
            channel=WEB_CHECK_CHANNEL,
            # fill_forms omitted → defaults True
        )

    assert response.queued_forms is True
    assert _rows(db, "RC03")[0].status == "pending"
