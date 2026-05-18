"""
Light load test — Task L5: 50 concurrent users reporting their accident status.

Validates:
1. All 50 AccidentUserReport rows updated to status='ok' (no DB race conditions).
2. No deadlock on the partial index ix_accidents_single_active.
3. Broker delivers ≥50 'accident_user_report' events.
4. Admin GET /accidents/active returns situation_rows covering all 50 users.
5. Total wall-clock time < 30 s.

Concurrency strategy
---------------------
asyncio.gather + loop.run_in_executor(ThreadPoolExecutor) drives 50 HTTP
calls concurrently.  SQLAlchemy 2.0's pysqlite dialect automatically sets
check_same_thread=False, so sharing the QueuePool across threads is safe.
SQLite serialises write locks internally; with each report taking ~1 ms to
commit, all 50 serialise comfortably within the 5-second busy timeout.
"""
import asyncio
import concurrent.futures
import json
import os
import time
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa

# ---------------------------------------------------------------------------
# App bootstrap (before any project import)
# ---------------------------------------------------------------------------

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_checking.db")
os.environ.setdefault("FORMS_URL", "https://example.com/form")
os.environ.setdefault("DEVICE_SHARED_KEY", "device-test-key")
os.environ.setdefault("MOBILE_APP_SHARED_KEY", "mobile-test-key")
os.environ.setdefault("PROVIDER_SHARED_KEY", "TESTPROVIDER0001")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-admin-session-secret")
os.environ.setdefault("BOOTSTRAP_ADMIN_KEY", "HR70")
os.environ.setdefault("BOOTSTRAP_ADMIN_NAME", "Tamer Salmem")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "eAcacdLe2")
os.environ.setdefault("FORMS_QUEUE_ENABLED", "false")
os.environ.setdefault("TRANSPORT_EXPORTS_DIR", "./test_transport_exports")

from fastapi.testclient import TestClient  # noqa: E402

from sistema.app.database import Base, SessionLocal, engine  # noqa: E402
from sistema.app.main import app  # noqa: E402
from sistema.app.models import (  # noqa: E402
    Accident,
    AccidentUserReport,
    Project,
    User,
)
from sistema.app.services.accident_lifecycle import (  # noqa: E402
    list_active_accident,
    open_accident,
)
from sistema.app.services.admin_updates import web_check_updates_broker  # noqa: E402
from sistema.app.services.passwords import hash_password  # noqa: E402

Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NUM_USERS = 50
_PROJECT_NAME = "L5LoadProject"

_OPENER_CHAVE = "L5OP"
_OPENER_SENHA = "L5oppass!"  # 9 chars

_USER_SENHA = "L5ldpass"  # 8 chars — shared by all 50 load users

_ADMIN_CHAVE = "L5AD"
_ADMIN_SENHA = "L5admin!!"  # 9 chars

WEB_LOGIN_URL = "/api/web/auth/login"
WEB_REPORT_URL = "/api/web/check/accident/report"
ADMIN_LOGIN_URL = "/api/admin/auth/login"
ADMIN_ACTIVE_URL = "/api/admin/accidents/active"


def _chave(i: int) -> str:
    """4-char chave for load user i: 'L500' .. 'L549'."""
    return f"L5{i:02d}"


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------


def _setup_test_data() -> tuple[int, int]:
    """
    Create (or refresh) in the shared test DB:
      - Project "L5LoadProject"
      - Opener user "L5OP"  (checkin=False)
      - 50 load users "L500".."L549"  (checkin=True)
      - Admin user "L5AD"  (perfil=1)
    Returns (project_id, opener_id).
    """
    with SessionLocal() as db:
        # Project
        proj = db.execute(
            sa.select(Project).where(Project.name == _PROJECT_NAME)
        ).scalar_one_or_none()
        if proj is None:
            proj = Project(
                name=_PROJECT_NAME,
                country_code="SG",
                country_name="Singapore",
                timezone_name="Asia/Singapore",
                address="1 Load Street",
                zip_code="000050",
            )
            db.add(proj)
            db.flush()
        project_id = proj.id

        # Opener (not checked-in so it doesn't inflate the pre-populated rows)
        opener = db.execute(
            sa.select(User).where(User.chave == _OPENER_CHAVE)
        ).scalar_one_or_none()
        if opener is None:
            opener = User(
                chave=_OPENER_CHAVE,
                nome="L5 Opener",
                projeto=_PROJECT_NAME,
                checkin=False,
                last_active_at=datetime.now(timezone.utc),
                inactivity_days=0,
                perfil=0,
                senha=hash_password(_OPENER_SENHA),
            )
            db.add(opener)
        else:
            opener.checkin = False
            opener.senha = hash_password(_OPENER_SENHA)
        db.flush()
        opener_id = opener.id

        # 50 load users — all checkin=True so they get pre-populated rows
        for i in range(NUM_USERS):
            chave = _chave(i)
            user = db.execute(
                sa.select(User).where(User.chave == chave)
            ).scalar_one_or_none()
            if user is None:
                db.add(User(
                    chave=chave,
                    nome=f"L5 User {i:02d}",
                    projeto=_PROJECT_NAME,
                    checkin=True,
                    local=f"Zone {i}",
                    last_active_at=datetime.now(timezone.utc),
                    inactivity_days=0,
                    perfil=0,
                    senha=hash_password(_USER_SENHA),
                ))
            else:
                user.checkin = True
                user.senha = hash_password(_USER_SENHA)

        # Admin user (perfil=1 for admin routes)
        admin = db.execute(
            sa.select(User).where(User.chave == _ADMIN_CHAVE)
        ).scalar_one_or_none()
        if admin is None:
            db.add(User(
                chave=_ADMIN_CHAVE,
                nome="L5 Admin",
                projeto=_PROJECT_NAME,
                checkin=False,
                last_active_at=datetime.now(timezone.utc),
                inactivity_days=0,
                perfil=1,
                senha=hash_password(_ADMIN_SENHA),
            ))
        else:
            admin.perfil = 1
            admin.senha = hash_password(_ADMIN_SENHA)

        db.commit()

    return project_id, opener_id


def _open_test_accident(project_id: int, opener_id: int) -> int:
    """
    Close any currently active accident, then open a fresh one.
    Returns the new accident's id.
    The 50 load users (checkin=True) get pre-populated AccidentUserReport rows.
    """
    with SessionLocal() as db:
        existing = list_active_accident(db)
        if existing is not None:
            now = datetime.now(timezone.utc)
            existing.closed_at = now
            existing.updated_at = now
            db.commit()

        accident = open_accident(
            db,
            origin="web",
            project_id=project_id,
            location_id=None,
            custom_location_name="L5 Load Test Zone",
            opened_by_admin_id=None,
            opened_by_user_id=opener_id,
            reporter_zone="safety",
            reporter_status="ok",
        )
        return accident.id


def _teardown_accident() -> None:
    """Force-close any open accident directly in the DB (no AdminUser FK required)."""
    with SessionLocal() as db:
        now = datetime.now(timezone.utc)
        db.execute(
            sa.update(Accident)
            .where(Accident.closed_at.is_(None))
            .values(closed_at=now, updated_at=now)
        )
        db.commit()


# ---------------------------------------------------------------------------
# Thread worker
# ---------------------------------------------------------------------------


def _login_and_report(user_idx: int) -> tuple[str, int, int]:
    """
    Called from a thread pool worker.
    Creates its own TestClient, logs in, then POSTs /report.
    Returns (chave, login_status_code, report_status_code).
    """
    chave = _chave(user_idx)
    client = TestClient(app, raise_server_exceptions=False)
    login_r = client.post(WEB_LOGIN_URL, json={"chave": chave, "senha": _USER_SENHA})
    if login_r.status_code != 200:
        return chave, login_r.status_code, -1
    report_r = client.post(
        WEB_REPORT_URL,
        json={"chave": chave, "zone": "safety", "status": "ok"},
    )
    return chave, login_r.status_code, report_r.status_code


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_50_users_report_concurrently():
    """
    Light load: 50 concurrent POST /report calls via asyncio.gather.

    Steps
    -----
    1. Create project + 50 checkin users + opener + admin user.
    2. Open accident → 50 AccidentUserReport rows pre-populated (zone='waiting', status='waiting').
    3. Subscribe to web_check_updates_broker to count delivered events.
    4. asyncio.gather over 50 asyncio.to_thread workers, each: login + POST /report.
    5. Drain broker queue.
    6. Assert: all HTTP 200; 50 DB rows with status='ok';
       broker delivered ≥50 'accident_user_report' events;
       admin /active shows ≥50 situation_rows;
       elapsed < 30 s.
    """
    start = time.monotonic()

    # --- Setup -----------------------------------------------------------
    project_id, opener_id = _setup_test_data()
    accident_id = _open_test_accident(project_id, opener_id)

    # Subscribe BEFORE concurrent phase so call_soon_threadsafe callbacks
    # have a live queue to write to.
    sub_id, queue = web_check_updates_broker.subscribe()

    # Drain the queue continuously so it never fills up (default maxsize=20).
    # The collector list is written from the event loop thread only (no lock needed).
    broker_events: list[dict] = []

    async def _drain_continuously() -> None:
        while True:
            payload = await queue.get()
            broker_events.append(json.loads(payload))

    drain_task = asyncio.create_task(_drain_continuously())

    try:
        # --- Concurrent phase --------------------------------------------
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_USERS) as executor:
            futures = [
                loop.run_in_executor(executor, _login_and_report, i)
                for i in range(NUM_USERS)
            ]
            results: list[tuple[str, int, int]] = await asyncio.gather(*futures)

        # Allow the event loop to process any remaining call_soon_threadsafe callbacks
        await asyncio.sleep(0.3)

    finally:
        drain_task.cancel()
        try:
            await drain_task
        except asyncio.CancelledError:
            pass
        web_check_updates_broker.unsubscribe(sub_id)

    # --- Admin /active check (accident still open) -----------------------
    admin_client = TestClient(app, raise_server_exceptions=False)
    admin_login = admin_client.post(
        ADMIN_LOGIN_URL, json={"chave": _ADMIN_CHAVE, "senha": _ADMIN_SENHA}
    )
    active_resp = admin_client.get(ADMIN_ACTIVE_URL)

    # --- Teardown --------------------------------------------------------
    _teardown_accident()

    elapsed = time.monotonic() - start

    # =====================================================================
    # Assertions
    # =====================================================================

    # All 50 HTTP requests succeeded (login + report both 200)
    failed_reqs = [(c, lc, rc) for c, lc, rc in results if lc != 200 or rc != 200]
    assert not failed_reqs, (
        f"{len(failed_reqs)}/{NUM_USERS} requests failed: first 5={failed_reqs[:5]}"
    )

    # All 50 DB rows have status='ok'
    with SessionLocal() as db:
        chaves = [_chave(i) for i in range(NUM_USERS)]
        ok_count = db.execute(
            sa.select(sa.func.count())
            .select_from(AccidentUserReport)
            .join(User, AccidentUserReport.user_id == User.id)
            .where(
                User.chave.in_(chaves),
                AccidentUserReport.status == "ok",
                AccidentUserReport.accident_id == accident_id,
            )
        ).scalar()
    assert ok_count == NUM_USERS, (
        f"Only {ok_count}/{NUM_USERS} AccidentUserReport rows have status='ok' — possible race condition"
    )

    # Broker delivered ≥50 accident_user_report events
    report_events = [e for e in broker_events if e.get("reason") == "accident_user_report"]
    assert len(report_events) >= NUM_USERS, (
        f"Broker delivered {len(report_events)} 'accident_user_report' events; expected ≥{NUM_USERS}. "
        f"Total broker events: {len(broker_events)}"
    )

    # Admin /active returned the full picture before teardown
    assert admin_login.status_code == 200, (
        f"Admin login failed: {admin_login.status_code} {admin_login.text}"
    )
    assert active_resp.status_code == 200, (
        f"Admin /active failed: {active_resp.status_code} {active_resp.text}"
    )
    active_data = active_resp.json()
    assert active_data["is_active"], "Accident was not active when admin checked"
    situation_rows = active_data.get("situation_rows", [])
    # The 50 load users all reported status='ok', so they should appear in situation_rows.
    # (The opener may also appear with its row, so total ≥50.)
    assert len(situation_rows) >= NUM_USERS, (
        f"Admin /active returned only {len(situation_rows)} situation_rows; expected ≥{NUM_USERS}"
    )

    # Wall-clock time
    assert elapsed < 30, f"Load test took {elapsed:.1f}s, exceeds 30s CI budget"
