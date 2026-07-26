"""Tests for Task C4 — accident_situation_table service."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import (
    Accident,
    AccidentUserReport,
    AccidentVideoUpload,
    AdminUser,
    Project,
    User,
)
from sistema.app.services.accident_situation_table import (
    _derive_display,
    build_situation_rows,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    return factory()


_NOW = datetime(2026, 1, 1, 8, 0, 0)  # naive, like SQLite stores


def _make_project(db: Session) -> Project:
    proj = Project(
        name="PROJ",
        country_code="SG",
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address="1 St",
        zip_code="123456",
    )
    db.add(proj)
    db.flush()
    return proj


def _make_admin(db: Session) -> AdminUser:
    admin = AdminUser(
        chave="A001",
        nome_completo="Admin",
        created_at=_NOW,
        updated_at=_NOW,
    )
    db.add(admin)
    db.flush()
    return admin


def _make_accident(db: Session, proj: Project, admin: AdminUser, opened_at=None) -> Accident:
    opened_at = opened_at or _NOW
    a = Accident(
        accident_number=0,
        project_id=proj.id,
        project_name_snapshot=proj.name,
        location_name_snapshot="Sala",
        location_is_registered=False,
        origin="admin",
        opened_by_admin_id=admin.id,
        opened_at=opened_at,
        created_at=opened_at,
        updated_at=opened_at,
    )
    db.add(a)
    db.flush()
    return a


def _make_user(db: Session, chave: str) -> User:
    user = User(
        chave=chave,
        nome=f"User {chave}",
        projeto="PROJ",
        checkin=False,
        local="Sala 1",
        last_active_at=_NOW,
        inactivity_days=0,
    )
    db.add(user)
    db.flush()
    return user


def _make_report(
    db: Session,
    accident: Accident,
    user: User,
    *,
    zone: str,
    status: str,
    reported_at=None,
    last_checkin_action=None,
    last_action_at=None,
    created_at=None,
) -> AccidentUserReport:
    now = created_at or _NOW
    report = AccidentUserReport(
        accident_id=accident.id,
        user_id=user.id,
        user_chave_snapshot=user.chave,
        user_name_snapshot=user.nome,
        user_phone_snapshot=None,
        user_projects_snapshot=json.dumps(["PROJ"]),
        user_local_snapshot="Sala 1",
        zone=zone,
        status=status,
        reported_at=reported_at,
        last_checkin_action=last_checkin_action,
        last_action_at=last_action_at,
        created_at=now,
        updated_at=now,
    )
    db.add(report)
    db.flush()
    return report


def _make_video(
    db: Session,
    accident: Accident,
    user: User,
    *,
    captured_at: datetime,
    key: str = "v1",
) -> AccidentVideoUpload:
    v = AccidentVideoUpload(
        idempotency_key=key,
        accident_id=accident.id,
        user_id=user.id,
        object_key=f"videos/{key}.mp4",
        public_url=f"https://example.com/{key}.mp4",
        content_type="video/mp4",
        size_bytes=1024,
        captured_at=captured_at,
        created_at=captured_at,
    )
    db.add(v)
    db.flush()
    return v


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_priority_1_help_blinking_red(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin)
    user = _make_user(db, "U001")
    _make_report(db, accident, user, zone="accident", status="help", reported_at=_NOW)
    db.commit()

    rows = build_situation_rows(db, accident=accident)
    assert len(rows) == 1
    assert rows[0].priority == 1
    assert rows[0].row_color == "blinking-red"
    assert rows[0].zone == "Acidente"
    assert rows[0].status == "AJUDA"


def test_priority_2_accident_ok_yellow(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin)
    user = _make_user(db, "U002")
    _make_report(db, accident, user, zone="accident", status="ok", reported_at=_NOW)
    db.commit()

    rows = build_situation_rows(db, accident=accident)
    assert rows[0].priority == 2
    assert rows[0].row_color == "yellow"
    assert rows[0].zone == "Acidente"
    assert rows[0].status == "OK"


def test_priority_3_waiting_turquoise(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin)
    user = _make_user(db, "U003")
    _make_report(db, accident, user, zone="waiting", status="waiting")
    db.commit()

    rows = build_situation_rows(db, accident=accident)
    assert rows[0].priority == 3
    assert rows[0].row_color == "light-blue"
    assert rows[0].zone == "Aguardando"


def test_priority_4_safety_ok_light_green(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin)
    user = _make_user(db, "U004")
    _make_report(db, accident, user, zone="safety", status="ok", reported_at=_NOW)
    db.commit()

    rows = build_situation_rows(db, accident=accident)
    assert rows[0].priority == 4
    assert rows[0].row_color == "light-green"
    assert rows[0].zone == "Segurança"
    assert rows[0].status == "OK"


def test_priority_5_checked_out_after_open_light_gray(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    opened_at = _NOW
    accident = _make_accident(db, proj, admin, opened_at=opened_at)
    user = _make_user(db, "U005")
    checkout_time = opened_at + timedelta(minutes=10)
    _make_report(
        db,
        accident,
        user,
        zone="safety",
        status="ok",
        last_checkin_action="check-out",
        last_action_at=checkout_time,
        reported_at=_NOW,
    )
    db.commit()

    rows = build_situation_rows(db, accident=accident)
    assert rows[0].priority == 5
    assert rows[0].row_color == "light-gray"


def test_within_same_priority_more_recent_first(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin)
    user_a = _make_user(db, "UA01")
    user_b = _make_user(db, "UB02")

    earlier = _NOW
    later = _NOW + timedelta(minutes=5)

    _make_report(db, accident, user_a, zone="waiting", status="waiting", created_at=earlier)
    _make_report(db, accident, user_b, zone="waiting", status="waiting", created_at=later)
    db.commit()

    rows = build_situation_rows(db, accident=accident)
    # Both are priority 3; more recent (user_b) should come first
    assert rows[0].user_id == user_b.id
    assert rows[1].user_id == user_a.id


def test_videos_included_per_user(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin)
    user = _make_user(db, "U006")
    _make_report(db, accident, user, zone="waiting", status="waiting")
    _make_video(db, accident, user, captured_at=_NOW, key="vid1")
    db.commit()

    rows = build_situation_rows(db, accident=accident)
    assert len(rows[0].videos) == 1
    # Phase 9.1: the URL is now regenerated from object_key at read-time so
    # private DO Spaces objects still yield a working presigned URL for the
    # admin. In dev (local storage) that resolves to the local-asset endpoint.
    assert rows[0].videos[0].public_url == "/api/admin/accidents/local-asset/videos/vid1.mp4"


def test_videos_ordered_by_captured_at_asc(tmp_path: Path):
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin)
    user = _make_user(db, "U007")
    _make_report(db, accident, user, zone="waiting", status="waiting")

    t1 = _NOW
    t2 = _NOW + timedelta(minutes=5)
    t3 = _NOW + timedelta(minutes=10)
    _make_video(db, accident, user, captured_at=t3, key="v3")
    _make_video(db, accident, user, captured_at=t1, key="v1")
    _make_video(db, accident, user, captured_at=t2, key="v2")
    db.commit()

    rows = build_situation_rows(db, accident=accident)
    times = [v.captured_at for v in rows[0].videos]
    assert times == sorted(times)


# ---------------------------------------------------------------------------
# Regression — production incident of 2026-07-26
#
# DateTime(timezone=True) round-trips as tz-aware in Postgres and as naive in
# SQLite. _derive_display used to strip tzinfo from opened_at unconditionally
# and then compare it against report.last_action_at (still aware under
# Postgres), raising "TypeError: can't compare offset-naive and offset-aware
# datetimes". It only fired once some row had a check-out recorded, so every
# test above — all naive, all SQLite — stayed green while
# GET /api/admin/accidents/active returned 500 in production, leaving the admin
# unable to see the accident number, the situation tables, or close the
# accident at all.
#
# These call _derive_display with plain objects so the Postgres awareness is
# reproduced without needing Postgres.
# ---------------------------------------------------------------------------

_SGT = timezone(timedelta(hours=8))


def _report_stub(**overrides) -> AccidentUserReport:
    fields = dict(
        accident_id=1,
        user_id=1,
        user_chave_snapshot="U999",
        user_name_snapshot="User U999",
        user_phone_snapshot=None,
        user_projects_snapshot=json.dumps(["PROJ"]),
        user_local_snapshot="Sala 1",
        zone="safety",
        status="ok",
        awareness_status="waiting",
        created_at=_NOW,
        updated_at=_NOW,
    )
    fields.update(overrides)
    return AccidentUserReport(**fields)


def test_derive_display_handles_tz_aware_datetimes_from_postgres():
    """Both datetimes aware (Postgres): must classify, not raise."""
    opened_at = datetime(2026, 7, 26, 0, 49, 37, tzinfo=_SGT)
    report = _report_stub(
        last_checkin_action="check-out",
        last_action_at=opened_at + timedelta(minutes=10),
    )

    _, _, row_color, priority, section = _derive_display(report, opened_at)

    assert (priority, section, row_color) == (5, 4, "light-gray")


def test_derive_display_tz_aware_check_out_before_open_is_not_priority_5():
    """The comparison must stay correct under awareness, not merely not raise."""
    opened_at = datetime(2026, 7, 26, 0, 49, 37, tzinfo=_SGT)
    report = _report_stub(
        last_checkin_action="check-out",
        last_action_at=opened_at - timedelta(hours=3),
    )

    _, _, row_color, priority, section = _derive_display(report, opened_at)

    # Checked out before the accident opened → ordinary safety/ok row.
    assert (priority, section, row_color) == (4, 4, "light-green")


def test_derive_display_handles_mixed_awareness():
    """A naive value meeting an aware one must not raise either."""
    aware_opened_at = datetime(2026, 7, 26, 0, 49, 37, tzinfo=_SGT)
    naive_report = _report_stub(
        last_checkin_action="check-out",
        last_action_at=datetime(2026, 7, 26, 1, 0, 0),
    )

    _, _, _, priority, _ = _derive_display(naive_report, aware_opened_at)
    assert priority == 5

    naive_opened_at = datetime(2026, 7, 26, 0, 49, 37)
    aware_report = _report_stub(
        last_checkin_action="check-out",
        last_action_at=datetime(2026, 7, 26, 1, 0, 0, tzinfo=_SGT),
    )

    _, _, _, priority, _ = _derive_display(aware_report, naive_opened_at)
    assert priority == 5


# ---------------------------------------------------------------------------
# A call for help must never be rendered as "did not answer"
# ---------------------------------------------------------------------------


def test_safety_zone_help_is_an_emergency_not_waiting(tmp_path: Path):
    """zone='safety' + status='help' is a valid report the API accepts.

    It had no branch in _derive_display and fell through to the fallback, so it
    rendered as "Aguardando"/light-blue in section 3 — indistinguishable from a
    user who never responded.
    """
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin)
    user = _make_user(db, "U008")
    _make_report(db, accident, user, zone="safety", status="help", reported_at=_NOW)
    db.commit()

    rows = build_situation_rows(db, accident=accident)
    assert rows[0].status == "AJUDA"
    assert rows[0].zone == "Segurança"
    assert rows[0].row_color == "blinking-red"
    assert (rows[0].priority, rows[0].section) == (1, 1)


def test_help_sorts_above_everyone_else(tmp_path: Path):
    """A safety+help row must outrank ordinary rows, not sink into section 3."""
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin)
    calm = _make_user(db, "U009")
    helper = _make_user(db, "U010")
    _make_report(db, accident, calm, zone="accident", status="ok", reported_at=_NOW)
    _make_report(db, accident, helper, zone="safety", status="help", reported_at=_NOW)
    db.commit()

    rows = build_situation_rows(db, accident=accident)
    assert rows[0].user_id == helper.id
    assert rows[0].status == "AJUDA"


def test_accident_zone_help_still_blinking_red(tmp_path: Path):
    """The original emergency combination keeps its exact rendering."""
    db = _make_session(tmp_path)
    proj = _make_project(db)
    admin = _make_admin(db)
    accident = _make_accident(db, proj, admin)
    user = _make_user(db, "U011")
    _make_report(db, accident, user, zone="accident", status="help", reported_at=_NOW)
    db.commit()

    rows = build_situation_rows(db, accident=accident)
    assert (rows[0].zone, rows[0].status) == ("Acidente", "AJUDA")
    assert (rows[0].priority, rows[0].section, rows[0].row_color) == (1, 1, "blinking-red")
