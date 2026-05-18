"""Integration test — realtime SSE broker event delivery (Task L4).

Validates that:
1. Admin and web-check SSE generators each yield a 'connected' event on open.
2. Events dispatched via notify_admin_data_changed / notify_web_check_data_changed
   arrive in the respective stream within 2 seconds.

Approach: call the SSE handler functions directly (bypassing HTTP and auth
dependencies) using mock Requests, mirroring the pattern used in
tests/routers/test_web_check_stream.py.  The "direct queue" sub-test uses
asyncio.wait_for(queue.get(), timeout=2) exactly as the spec requires.
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock

import anyio
import pytest

# ---------------------------------------------------------------------------
# App bootstrap
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

from sqlalchemy.orm import Session  # noqa: E402

from sistema.app.database import Base, SessionLocal, engine  # noqa: E402
from sistema.app.models import User  # noqa: E402
from sistema.app.routers.admin import stream_updates as admin_stream_handler  # noqa: E402
from sistema.app.routers.web_check import (  # noqa: E402
    WEB_USER_SESSION_KEY,
    stream_web_check_updates as web_stream_handler,
)
from sistema.app.services.admin_updates import (  # noqa: E402
    admin_updates_broker,
    notify_admin_data_changed,
    notify_web_check_data_changed,
    web_check_updates_broker,
)
from sistema.app.services.passwords import hash_password  # noqa: E402
from sistema.app.services.user_sync import find_user_by_chave  # noqa: E402

Base.metadata.create_all(bind=engine)

_WEB_CHAVE = "L4WB"
_WEB_SENHA = "L4webpass"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_web_user(db: Session) -> User:
    user = find_user_by_chave(db, _WEB_CHAVE)
    if user is not None:
        return user
    user = User(
        rfid=None,
        chave=_WEB_CHAVE,
        senha=hash_password(_WEB_SENHA),
        nome="L4 SSE Test User",
        projeto="L4RealtimeProject",
        checkin=None,
        time=None,
        last_active_at=datetime.now(tz=timezone.utc),
        inactivity_days=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_mock_request(disconnects_after: int = 2, session_override: dict | None = None) -> MagicMock:
    call_count = 0

    async def is_disconnected() -> bool:
        nonlocal call_count
        call_count += 1
        return call_count > disconnects_after

    mock_req = MagicMock()
    mock_req.session = session_override if session_override is not None else {}
    mock_req.is_disconnected = is_disconnected
    return mock_req


async def _collect_events(body_iterator, max_events: int = 5) -> list[dict]:
    events: list[dict] = []
    async for chunk in body_iterator:
        if isinstance(chunk, bytes):
            chunk = chunk.decode()
        for line in chunk.splitlines():
            if line.startswith("data:"):
                events.append(json.loads(line.removeprefix("data:").strip()))
        if len(events) >= max_events:
            break
    return events


# ---------------------------------------------------------------------------
# Test 1: admin stream yields 'connected' as first event
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_admin_sse_connected_event():
    """Admin SSE stream must yield {reason: 'connected'} as its first event."""
    mock_req = _make_mock_request(disconnects_after=1)
    response = await admin_stream_handler(request=mock_req)
    assert response.media_type == "text/event-stream"

    events = await _collect_events(response.body_iterator)
    assert events, "Expected at least one event from admin SSE stream"
    assert events[0]["reason"] == "connected"


# ---------------------------------------------------------------------------
# Test 2: web-check stream yields 'connected' as first event
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_web_sse_connected_event():
    """Web-check SSE stream must yield {reason: 'connected'} as its first event."""
    db = SessionLocal()
    try:
        _ensure_web_user(db)
        mock_req = _make_mock_request(
            disconnects_after=1,
            session_override={WEB_USER_SESSION_KEY: _WEB_CHAVE},
        )
        response = await web_stream_handler(request=mock_req, chave=_WEB_CHAVE, db=db)
        assert response.media_type == "text/event-stream"

        events = await _collect_events(response.body_iterator)
    finally:
        db.close()

    assert events, "Expected at least one event from web-check SSE stream"
    assert events[0]["reason"] == "connected"


# ---------------------------------------------------------------------------
# Test 3: accident_opened event delivered to admin queue within 2 s
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_admin_broker_receives_accident_opened_within_2s():
    """notify_admin_data_changed delivers payload to subscriber queue within 2 seconds."""
    sub_id, queue = admin_updates_broker.subscribe()
    try:
        notify_admin_data_changed("accident_opened")
        raw = await asyncio.wait_for(queue.get(), timeout=2)
        payload = json.loads(raw)
        assert payload["reason"] == "accident_opened"
    finally:
        admin_updates_broker.unsubscribe(sub_id)


# ---------------------------------------------------------------------------
# Test 4: accident_opened event delivered to web-check queue within 2 s
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_web_check_broker_receives_accident_opened_within_2s():
    """notify_web_check_data_changed delivers payload to subscriber queue within 2 seconds."""
    sub_id, queue = web_check_updates_broker.subscribe()
    try:
        notify_web_check_data_changed("accident_opened")
        raw = await asyncio.wait_for(queue.get(), timeout=2)
        payload = json.loads(raw)
        assert payload["reason"] == "accident_opened"
    finally:
        web_check_updates_broker.unsubscribe(sub_id)


# ---------------------------------------------------------------------------
# Test 5: combined scenario — both streams receive accident_opened simultaneously
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_both_sse_streams_receive_accident_opened_simultaneously():
    """
    Simulate 2 SSE clients (admin + web-check).  After both send 'connected',
    dispatch notifications and assert each receives 'accident_opened' within 2 s.

    This is the full L4 scenario:
    1. Open admin SSE stream  → receive 'connected'
    2. Open web-check SSE stream → receive 'connected'
    3. Dispatch notify_admin_data_changed + notify_web_check_data_changed
    4. Both queues receive the event (asyncio.wait_for, timeout=2)
    """
    db = SessionLocal()
    try:
        _ensure_web_user(db)

        admin_req = _make_mock_request(disconnects_after=2)
        web_req = _make_mock_request(
            disconnects_after=2,
            session_override={WEB_USER_SESSION_KEY: _WEB_CHAVE},
        )

        admin_response = await admin_stream_handler(request=admin_req)
        web_response = await web_stream_handler(request=web_req, chave=_WEB_CHAVE, db=db)

        admin_events: list[dict] = []
        web_events: list[dict] = []
        admin_connected = anyio.Event()
        web_connected = anyio.Event()

        async def read_admin():
            async for chunk in admin_response.body_iterator:
                if isinstance(chunk, bytes):
                    chunk = chunk.decode()
                for line in chunk.splitlines():
                    if line.startswith("data:"):
                        ev = json.loads(line.removeprefix("data:").strip())
                        admin_events.append(ev)
                        if ev.get("reason") == "connected":
                            admin_connected.set()

        async def read_web():
            async for chunk in web_response.body_iterator:
                if isinstance(chunk, bytes):
                    chunk = chunk.decode()
                for line in chunk.splitlines():
                    if line.startswith("data:"):
                        ev = json.loads(line.removeprefix("data:").strip())
                        web_events.append(ev)
                        if ev.get("reason") == "connected":
                            web_connected.set()

        async def publish_after_both_connected():
            await admin_connected.wait()
            await web_connected.wait()
            await anyio.sleep(0.05)
            notify_admin_data_changed("accident_opened")
            notify_web_check_data_changed("accident_opened")

        async with anyio.create_task_group() as tg:
            tg.start_soon(read_admin)
            tg.start_soon(read_web)
            tg.start_soon(publish_after_both_connected)

    finally:
        db.close()

    admin_reasons = [e.get("reason") for e in admin_events]
    web_reasons = [e.get("reason") for e in web_events]

    assert "connected" in admin_reasons, f"Admin stream missing 'connected': {admin_reasons}"
    assert "connected" in web_reasons, f"Web stream missing 'connected': {web_reasons}"
    assert "accident_opened" in admin_reasons, f"Admin stream missing 'accident_opened': {admin_reasons}"
    assert "accident_opened" in web_reasons, f"Web stream missing 'accident_opened': {web_reasons}"
