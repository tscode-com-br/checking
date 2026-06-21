"""EP7 / plan002 P7.1+P7.2 — FORMS enqueued once per registered project.

Verifies the multi-project fan-out at ENQUEUE level (the real worker needs a browser and is out of
scope for unit tests): one FormsSubmission per project, per-project request_id, per-project
forms_enabled gate, single-candidate per row (so worker failures are isolated), idempotent replay, and
the single-project path unchanged.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import (
    CheckingHistory,
    FormsSubmission,
    Project,
    User,
    UserProjectMembership,
    UserSyncEvent,
)
from sistema.app.routers.web_check import WEB_CHECK_CHANNEL
from sistema.app.schemas import MobileSyncStateResponse
from sistema.app.services.forms_submit import submit_forms_event
from sistema.app.services.user_sync import ensure_web_user

_NOW = datetime(2026, 6, 18, 8, 0, 0, tzinfo=timezone.utc)


def _make_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / 'test_perproj.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)()


def _make_project(db: Session, name: str, *, forms_enabled: bool = True) -> Project:
    proj = Project(
        name=name,
        country_code="SG",
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address="1 Per Project Rd",
        zip_code="099333",
        forms_enabled=forms_enabled,
        transport_enabled=True,
        emergency_phone="",
    )
    db.add(proj)
    db.flush()
    return proj


def _make_user(db: Session, chave: str, projects: list[Project]) -> User:
    user = User(
        rfid=None,
        chave=chave,
        nome="Per Project User",
        projeto=projects[0].name,
        checkin=False,
        local="Escritório",
        last_active_at=_NOW,
        inactivity_days=0,
    )
    db.add(user)
    db.flush()
    for proj in projects:
        db.add(UserProjectMembership(user_id=user.id, project_id=proj.id, created_at=_NOW, updated_at=_NOW))
    db.commit()
    return user


def _stub_sync_state(chave: str) -> MobileSyncStateResponse:
    return MobileSyncStateResponse(found=True, chave=chave)


def _submit(db, *, chave, projeto, action, client_event_id, should_queue=True):
    with patch(
        "sistema.app.services.forms_submit.build_mobile_sync_state",
        side_effect=lambda db_, *, chave: _stub_sync_state(chave),
    ), patch(
        "sistema.app.services.forms_submit.fire_accident_hook_for_check_event",
        return_value=None,
    ), patch(
        "sistema.app.services.forms_submit.should_enqueue_forms_for_action",
        return_value=should_queue,
    ), patch(
        # Isolate the per-project enqueue from latest-activity resolution, which sorts mixed
        # naive/aware datetimes read back from SQLite (a tz artifact of the test DB, not prod).
        # Its result only feeds the (mocked) timing decision + Path-A skip_reason, unused here.
        "sistema.app.services.forms_submit.resolve_latest_internal_user_activity",
        return_value=None,
    ):
        return submit_forms_event(
            db,
            chave=chave,
            projeto=projeto,
            action=action,
            informe="normal",
            local="Escritório",
            event_time=_NOW,
            client_event_id=client_event_id,
            ensure_user=ensure_web_user,
            channel=WEB_CHECK_CHANNEL,
        )


def _rows(db, chave) -> list[FormsSubmission]:
    return list(
        db.execute(sa.select(FormsSubmission).where(FormsSubmission.chave == chave)).scalars().all()
    )


def test_multi_project_first_checkin_enqueues_one_per_project(tmp_path: Path):
    db = _make_session(tmp_path)
    p80, p83 = _make_project(db, "P80"), _make_project(db, "P83")
    _make_user(db, "MP01", [p80, p83])

    _submit(db, chave="MP01", projeto="P80", action="checkin", client_event_id="ev-mp-1")

    rows = _rows(db, "MP01")
    assert len(rows) == 2
    assert {r.projeto for r in rows} == {"P80", "P83"}
    assert all(r.status == "pending" for r in rows)
    assert len({r.request_id for r in rows}) == 2  # distinct per-project request_ids
    # P7.2 isolation: each row carries a SINGLE candidate (its own project) → worker failures per-row.
    for r in rows:
        assert json.loads(r.project_candidates_json) == [r.projeto]


def test_multi_project_checkout_enqueues_one_per_project(tmp_path: Path):
    db = _make_session(tmp_path)
    p80, p83 = _make_project(db, "P80"), _make_project(db, "P83")
    _make_user(db, "MP02", [p80, p83])

    _submit(db, chave="MP02", projeto="P80", action="checkout", client_event_id="ev-mp-2")

    rows = _rows(db, "MP02")
    assert len(rows) == 2
    assert {r.projeto for r in rows} == {"P80", "P83"}
    assert all(r.status == "pending" for r in rows)


def test_multi_project_no_trigger_enqueues_nothing_pending(tmp_path: Path):
    # Timing says "do not queue" (e.g. second check-in of the day) → no pending FORMS enqueued.
    db = _make_session(tmp_path)
    p80, p83 = _make_project(db, "P80"), _make_project(db, "P83")
    _make_user(db, "MP03", [p80, p83])

    _submit(db, chave="MP03", projeto="P80", action="checkin", client_event_id="ev-mp-3", should_queue=False)

    pending = [r for r in _rows(db, "MP03") if r.status == "pending"]
    assert pending == []


def test_multi_project_forms_disabled_project_skipped_others_pending(tmp_path: Path):
    db = _make_session(tmp_path)
    p80 = _make_project(db, "P80", forms_enabled=True)
    p83 = _make_project(db, "P83", forms_enabled=False)
    _make_user(db, "MP04", [p80, p83])

    _submit(db, chave="MP04", projeto="P80", action="checkin", client_event_id="ev-mp-4")

    rows = {r.projeto: r for r in _rows(db, "MP04")}
    assert set(rows) == {"P80", "P83"}
    assert rows["P80"].status == "pending"
    assert rows["P83"].status == "skipped"
    assert rows["P83"].last_error == "forms_disabled_for_project"


def test_single_project_user_enqueues_exactly_one_with_bare_request_id(tmp_path: Path):
    # Regression: single-project path is byte-for-byte (one row, bare request_id == client_event_id).
    db = _make_session(tmp_path)
    p80 = _make_project(db, "P80")
    _make_user(db, "SP01", [p80])

    _submit(db, chave="SP01", projeto="P80", action="checkin", client_event_id="ev-sp-1")

    rows = _rows(db, "SP01")
    assert len(rows) == 1
    assert rows[0].request_id == "ev-sp-1"
    assert rows[0].status == "pending"


def test_replay_same_event_is_idempotent_per_project(tmp_path: Path):
    db = _make_session(tmp_path)
    p80, p83 = _make_project(db, "P80"), _make_project(db, "P83")
    _make_user(db, "MP05", [p80, p83])

    _submit(db, chave="MP05", projeto="P80", action="checkin", client_event_id="ev-mp-5")
    _submit(db, chave="MP05", projeto="P80", action="checkin", client_event_id="ev-mp-5")  # replay

    rows = _rows(db, "MP05")
    assert len(rows) == 2  # no duplicate FormsSubmission rows on replay
    assert {r.projeto for r in rows} == {"P80", "P83"}
    # …and no duplicate UserSyncEvent / CheckingHistory per project either (one each, not doubled).
    sync = db.execute(sa.select(sa.func.count()).select_from(UserSyncEvent).where(UserSyncEvent.chave == "MP05")).scalar()
    hist = db.execute(sa.select(sa.func.count()).select_from(CheckingHistory).where(CheckingHistory.chave == "MP05")).scalar()
    assert sync == 2
    assert hist == 2


def test_multi_project_checkin_records_one_history_row_per_project(tmp_path: Path):
    # Case 8 — change D: each project gets its own CheckingHistory row for the event (so the history
    # dialog can show per-project activity).
    db = _make_session(tmp_path)
    p80, p83 = _make_project(db, "P80"), _make_project(db, "P83")
    _make_user(db, "MP06", [p80, p83])

    _submit(db, chave="MP06", projeto="P80", action="checkin", client_event_id="ev-mp-6")

    hist = db.execute(sa.select(CheckingHistory).where(CheckingHistory.chave == "MP06")).scalars().all()
    assert {h.projeto for h in hist} == {"P80", "P83"}
    assert all(h.atividade == "check-in" for h in hist)
    assert all(h.local == "Escritório" for h in hist)
