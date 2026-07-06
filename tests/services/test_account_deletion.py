"""LGPD art. 18 — self-service account deletion (services/account_deletion.py).

Runs with SQLite FOREIGN KEY enforcement ON (dev normally has it off), so the FK-safe delete ordering is
actually exercised — this is the NO-ACTION trap that passes in dev and explodes in Postgres prod.
Covers: (1) a full delete of a worker's data leaves nothing behind and does NOT tear down the shared
accident; (2) the three guards (admin / accident-opener / active-accident) block the delete.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import event, select
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import (
    Accident,
    AccidentCallLog,
    AccidentUserReport,
    AccidentVideoUpload,
    AdminUser,
    CheckEvent,
    CheckingHistory,
    EmailDeliveryLog,
    FormsSubmission,
    Project,
    TransportAssignment,
    TransportRequest,
    User,
    UserSyncEvent,
)
from sistema.app.services.account_deletion import (
    AccountDeletionBlocked,
    assert_user_can_self_delete,
    delete_user_account,
)

_NOW = datetime(2026, 7, 6, 12, 0, 0, tzinfo=timezone.utc)


def _session(tmp_path: Path) -> Session:
    engine = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / 'del.db').as_posix()}")

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _rec):  # noqa: ANN001 — enforce FKs so NO-ACTION blocks are real (like prod)
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def _project(db: Session) -> Project:
    p = Project(
        name="P80", country_code="SG", country_name="Singapore", timezone_name="Asia/Singapore",
        address="1 Rd", zip_code="000011", forms_enabled=True, transport_enabled=True, emergency_phone="",
    )
    db.add(p)
    db.commit()
    return p


def _admin(db: Session) -> AdminUser:
    a = AdminUser(chave="AD01", nome_completo="Admin", created_at=_NOW, updated_at=_NOW)
    db.add(a)
    db.commit()
    return a


def _user(db: Session, *, chave="WK01", rfid="RF-WK01", perfil=0) -> User:
    u = User(chave=chave, rfid=rfid, nome="Worker", projeto="P80", perfil=perfil,
             last_active_at=_NOW, inactivity_days=0, senha="hash")
    db.add(u)
    db.commit()
    return u


def _accident(db: Session, *, opener_admin=None, opener_user=None, closed=True) -> Accident:
    acc = Accident(
        accident_number=1, project_id=1, project_name_snapshot="P80", location_name_snapshot="L",
        location_is_registered=True, origin="admin" if opener_admin else "web",
        opened_by_admin_id=opener_admin, opened_by_user_id=opener_user,
        opened_at=_NOW, closed_at=(_NOW + timedelta(hours=1)) if closed else None,
        description="", created_at=_NOW, updated_at=_NOW,
    )
    db.add(acc)
    db.commit()
    return acc


def _populate_worker_data(db: Session, user: User, accident: Accident) -> None:
    """Give the worker a row in every table a self-delete must reach."""
    db.add(UserSyncEvent(user_id=user.id, chave=user.chave, rfid=user.rfid, source="web_forms",
                         action="checkin", event_time=_NOW, created_at=_NOW, source_request_id="sync-1"))
    db.add(CheckEvent(idempotency_key="ck-1", source="web", rfid=user.rfid, action="checkin",
                      status="ok", message="m", event_time=_NOW))
    db.add(CheckingHistory(chave=user.chave, atividade="check-in", projeto="P80", time=_NOW, informe="normal"))
    db.add(FormsSubmission(request_id="fs-1", rfid=user.rfid, action="checkin", chave=user.chave,
                           projeto="P80", created_at=_NOW, updated_at=_NOW))
    req = TransportRequest(user_id=user.id, request_kind="regular", recurrence_kind="weekday",
                           requested_time="07:00", created_at=_NOW, updated_at=_NOW)
    db.add(req)
    db.commit()
    db.add(TransportAssignment(request_id=req.id, service_date=_NOW.date(), route_kind="home_to_work",
                              created_at=_NOW, updated_at=_NOW))
    db.add(AccidentUserReport(accident_id=accident.id, user_id=user.id, user_chave_snapshot=user.chave,
                              user_name_snapshot="Worker", user_projects_snapshot="P80", user_local_snapshot="L",
                              zone="safety", status="ok", created_at=_NOW, updated_at=_NOW))
    db.add(AccidentVideoUpload(idempotency_key="vid-1", accident_id=accident.id, user_id=user.id,
                               object_key="accidents/vid-1.mp4", public_url="https://x/vid-1.mp4",
                               content_type="video/mp4", size_bytes=1, captured_at=_NOW, created_at=_NOW))
    db.add(EmailDeliveryLog(triggered_by_user_id=user.id, recipient_email="w@x.com", recipient_chave=user.chave,
                            subject="s", body_snapshot="b", delivery_status="sent", queued_at=_NOW))
    db.add(AccidentCallLog(call_number=1, accident_id=accident.id, triggered_by_user_id=user.id,
                           to_phone="+100", from_phone="+200", message_twiml="<Response/>",
                           created_at=_NOW, updated_at=_NOW))
    db.commit()


def test_full_delete_removes_all_user_data_and_retains_the_accident(tmp_path: Path):
    db = _session(tmp_path)
    _project(db)
    admin = _admin(db)
    user = _user(db)
    accident = _accident(db, opener_admin=admin.id, closed=True)  # opened by admin → worker is a participant
    _populate_worker_data(db, user, accident)
    uid, chave, rfid = user.id, user.chave, user.rfid

    assert_user_can_self_delete(db, user)  # must not raise
    video_keys = delete_user_account(db, user)
    db.commit()

    # the video's storage key is returned for post-commit cleanup (not deleted mid-transaction)
    assert video_keys == ["accidents/vid-1.mp4"]

    # the user and every user-linked row are gone
    assert db.get(User, uid) is None
    assert db.execute(select(sa.func.count()).select_from(UserSyncEvent).where(UserSyncEvent.user_id == uid)).scalar() == 0
    assert db.execute(select(sa.func.count()).select_from(CheckEvent).where(CheckEvent.rfid == rfid)).scalar() == 0
    assert db.execute(select(sa.func.count()).select_from(CheckingHistory).where(CheckingHistory.chave == chave)).scalar() == 0
    assert db.execute(select(sa.func.count()).select_from(FormsSubmission).where(FormsSubmission.chave == chave)).scalar() == 0
    assert db.execute(select(sa.func.count()).select_from(TransportRequest).where(TransportRequest.user_id == uid)).scalar() == 0
    assert db.execute(select(sa.func.count()).select_from(AccidentUserReport).where(AccidentUserReport.user_id == uid)).scalar() == 0
    assert db.execute(select(sa.func.count()).select_from(AccidentVideoUpload).where(AccidentVideoUpload.user_id == uid)).scalar() == 0

    # the shared accident record is RETAINED (not torn down by one user leaving)
    assert db.get(Accident, accident.id) is not None

    # emergency audit rows are ANONYMIZED (user link nulled + free-text body scrubbed), not deleted
    email = db.execute(select(EmailDeliveryLog)).scalar_one()
    assert email.triggered_by_user_id is None
    assert email.recipient_chave is None
    assert email.recipient_email == ""
    assert email.body_snapshot == ""  # the body carried the user's name + chave
    call = db.execute(select(AccidentCallLog)).scalar_one()
    assert call.triggered_by_user_id is None


def test_guard_blocks_admin(tmp_path: Path):
    db = _session(tmp_path)
    _project(db)
    admin_user = _user(db, chave="AD09", rfid="RF-AD09", perfil=9)
    with pytest.raises(AccountDeletionBlocked) as exc:
        assert_user_can_self_delete(db, admin_user)
    assert exc.value.code == "admin"


def test_guard_blocks_accident_opener(tmp_path: Path):
    db = _session(tmp_path)
    _project(db)
    user = _user(db)
    _accident(db, opener_user=user.id, closed=True)  # user opened a (closed) accident
    with pytest.raises(AccountDeletionBlocked) as exc:
        assert_user_can_self_delete(db, user)
    assert exc.value.code == "accident_opener"


def test_guard_blocks_active_accident_participant(tmp_path: Path):
    db = _session(tmp_path)
    _project(db)
    admin = _admin(db)
    user = _user(db)
    acc = _accident(db, opener_admin=admin.id, closed=False)  # OPEN accident opened by admin
    db.add(AccidentUserReport(accident_id=acc.id, user_id=user.id, user_chave_snapshot=user.chave,
                              user_name_snapshot="W", user_projects_snapshot="P80", user_local_snapshot="L",
                              zone="safety", status="ok", created_at=_NOW, updated_at=_NOW))
    db.commit()
    with pytest.raises(AccountDeletionBlocked) as exc:
        assert_user_can_self_delete(db, user)
    assert exc.value.code == "active_accident"


def test_guard_blocks_open_accident_video_participant_without_report(tmp_path: Path):
    # A user can be part of a LIVE accident via a video upload alone (no report row) — must still block,
    # so the emergency video is never erased mid-emergency.
    db = _session(tmp_path)
    _project(db)
    admin = _admin(db)
    user = _user(db)
    acc = _accident(db, opener_admin=admin.id, closed=False)  # OPEN accident
    db.add(AccidentVideoUpload(idempotency_key="vid-open", accident_id=acc.id, user_id=user.id,
                               object_key="accidents/vid-open.mp4", public_url="https://x/o.mp4",
                               content_type="video/mp4", size_bytes=1, captured_at=_NOW, created_at=_NOW))
    db.commit()
    with pytest.raises(AccountDeletionBlocked) as exc:
        assert_user_can_self_delete(db, user)
    assert exc.value.code == "active_accident"
