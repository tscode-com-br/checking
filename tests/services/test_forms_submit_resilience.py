"""Resilience tests for submit_forms_event.

Reproduces the production regression where the accident hook fired after
a successful check-in/check-out commit and raised because the `accidents`
table did not exist. The original `except Exception` swallowed the Python
exception but Postgres left the surrounding transaction in `InFailedSqlTransaction`
state, so the next statement (`build_mobile_sync_state`) failed and the
endpoint returned HTTP 500.

After Item 1 hardens `fire_accident_hook_for_check_event` with a defensive
`db.rollback()`, `submit_forms_event` must continue to return a healthy
`MobileSubmitResponse` even when the hook explodes.

These tests run under SQLite. The production transaction-abort behaviour
cannot be reproduced under SQLite because SQLite does not abort the whole
block on a failed statement the way Postgres does. The tests therefore
focus on the two contracts that matter:

  1. The hook never raises out of submit_forms_event.
  2. The hook calls db.rollback() when its work fails (so the surrounding
     transaction is freed for the response builder to reuse).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import CheckEvent, Project, User
from sistema.app.routers.web_check import WEB_CHECK_CHANNEL
from sistema.app.schemas import MobileSyncStateResponse
from sistema.app.services.forms_submit import submit_forms_event
from sistema.app.services.user_sync import ensure_web_user


_NOW = datetime(2026, 5, 19, 8, 0, 0, tzinfo=timezone.utc)
_PROJECT_NAME = "P-RESILIENCE"


def _make_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(
        f"sqlite+pysqlite:///{(tmp_path / 'test_resilience.db').as_posix()}"
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
    )
    return factory()


def _make_project(db: Session) -> Project:
    proj = Project(
        name=_PROJECT_NAME,
        country_code="SG",
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address="1 Resilience Way",
        zip_code="000099",
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


def _stub_sync_state(chave: str) -> MobileSyncStateResponse:
    """Used to isolate this test from the unrelated naive/aware datetime
    quirk that arises when build_mobile_sync_state runs against SQLite
    (the production regression we are guarding against is not reproducible
    under SQLite anyway). The actual production fix is the db.rollback()
    inside fire_accident_hook_for_check_event, which is verified by the
    rollback_called spy below.
    """
    return MobileSyncStateResponse(found=True, chave=chave)


def test_submit_forms_event_returns_ok_when_accident_hook_fails(tmp_path: Path):
    """End-to-end repro of the production regression: the accident hook
    raises after the check event is committed; submit_forms_event must
    still return ok=True and the check event row must remain committed.
    """
    db = _make_session(tmp_path)
    _make_project(db)

    rollback_calls: list[str] = []
    original_rollback = db.rollback

    def spy_rollback() -> None:
        rollback_calls.append("called")
        original_rollback()

    with patch(
        "sistema.app.services.accident_lifecycle.list_active_accident",
        side_effect=RuntimeError("forced failure"),
    ), patch(
        "sistema.app.services.forms_submit.build_mobile_sync_state",
        side_effect=lambda db_, *, chave: _stub_sync_state(chave),
    ), patch.object(db, "rollback", side_effect=spy_rollback):
        response = submit_forms_event(
            db,
            chave="TEST",
            projeto=_PROJECT_NAME,
            action="checkin",
            informe="normal",
            local="Escritório Principal",
            event_time=_NOW,
            client_event_id="test-event-001-abcdef",
            ensure_user=ensure_web_user,
            channel=WEB_CHECK_CHANNEL,
        )

    # 1. The submit returned a healthy response.
    assert response.ok is True
    assert response.duplicate is False
    assert response.state is not None

    # 2. The accident-hook rollback was attempted exactly because the
    # mocked list_active_accident raised. This is the core defence
    # against the InFailedSqlTransaction failure mode.
    assert rollback_calls, "fire_accident_hook_for_check_event must call db.rollback() on failure"

    # 3. The user / check_event rows persisted from before the hook fired
    # are still queryable on the same session afterwards, proving the
    # rollback freed the transaction without losing the committed work.
    user = db.execute(sa.select(User).where(User.chave == "TEST")).scalar_one()
    assert user.local == "Escritório Principal"
    assert user.checkin is True
    assert (
        db.execute(sa.select(sa.func.count()).select_from(CheckEvent)).scalar() >= 1
    ), "log_event must have committed at least one CheckEvent before the hook fired"
