"""Tests for /api/web/check/stream SSE endpoint — Task B2."""
import asyncio
import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock

import anyio
import pytest

# ---------------------------------------------------------------------------
# App bootstrap (must happen before importing the app)
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
from sqlalchemy.orm import Session  # noqa: E402

from sistema.app.database import Base, SessionLocal, engine  # noqa: E402
from sistema.app.main import app  # noqa: E402
from sistema.app.models import User  # noqa: E402
from sistema.app.routers.web_check import (  # noqa: E402
    WEB_USER_SESSION_KEY,
    stream_web_check_updates,
)
from sistema.app.services.admin_updates import notify_web_check_data_changed  # noqa: E402
from sistema.app.services.passwords import hash_password  # noqa: E402
from sistema.app.services.user_sync import find_user_by_chave  # noqa: E402

Base.metadata.create_all(bind=engine)

TEST_CHAVE = "STSM"
TEST_SENHA = "senha123"

STREAM_URL = f"/api/web/check/stream?chave={TEST_CHAVE}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_test_user(db: Session) -> User:
    """Create (or reuse) a user with TEST_CHAVE in the DB."""
    user = find_user_by_chave(db, TEST_CHAVE)
    if user is not None:
        return user
    user = User(
        rfid=None,
        chave=TEST_CHAVE,
        senha=hash_password(TEST_SENHA),
        nome="Test SSE User",
        projeto="TestProject",
        checkin=None,
        time=None,
        last_active_at=datetime.now(tz=timezone.utc),
        inactivity_days=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_mock_request(chave: str = TEST_CHAVE, disconnects_after: int = 1) -> MagicMock:
    """
    Build a mock Starlette Request with a valid session and a controllable
    is_disconnected() that returns True after `disconnects_after` calls.
    """
    call_count = 0

    async def is_disconnected() -> bool:
        nonlocal call_count
        call_count += 1
        return call_count > disconnects_after

    mock_req = MagicMock()
    mock_req.session = {WEB_USER_SESSION_KEY: chave}
    mock_req.is_disconnected = is_disconnected
    return mock_req


async def _collect_events(body_iterator, max_events: int = 20) -> list[dict]:
    """Consume the SSE body_iterator and return parsed data: payloads."""
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
# test_stream_requires_session  (HTTP — no session → 401)
# ---------------------------------------------------------------------------


def test_stream_requires_session():
    """Calling the stream endpoint without a session must return 401."""
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(STREAM_URL)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# test_stream_initial_connected_event
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_stream_initial_connected_event():
    """The event generator must yield {"reason": "connected"} as first event."""
    db = SessionLocal()
    try:
        _ensure_test_user(db)
        mock_req = _make_mock_request(disconnects_after=1)

        streaming_response = await stream_web_check_updates(
            request=mock_req,
            chave=TEST_CHAVE,
            db=db,
        )
        assert streaming_response.media_type == "text/event-stream"

        events = await _collect_events(streaming_response.body_iterator)
    finally:
        db.close()

    assert events, "No events received from stream"
    assert events[0]["reason"] == "connected"


# ---------------------------------------------------------------------------
# test_stream_receives_published_payload
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_stream_receives_published_payload():
    """A message published via notify_web_check_data_changed must arrive in the stream."""
    db = SessionLocal()
    try:
        _ensure_test_user(db)
        # disconnects_after=2: let the loop run twice (once waiting for queue, once to exit)
        mock_req = _make_mock_request(disconnects_after=2)

        streaming_response = await stream_web_check_updates(
            request=mock_req,
            chave=TEST_CHAVE,
            db=db,
        )

        received: list[dict] = []
        connected_ev = anyio.Event()

        async def read_stream():
            async for chunk in streaming_response.body_iterator:
                if isinstance(chunk, bytes):
                    chunk = chunk.decode()
                for line in chunk.splitlines():
                    if line.startswith("data:"):
                        data = json.loads(line.removeprefix("data:").strip())
                        received.append(data)
                        if data.get("reason") == "connected":
                            connected_ev.set()

        async def publish_after_connected():
            await connected_ev.wait()
            await anyio.sleep(0.05)
            notify_web_check_data_changed("broker_test_event", metadata={"x": 1})

        async with anyio.create_task_group() as tg:
            tg.start_soon(read_stream)
            tg.start_soon(publish_after_connected)

    finally:
        db.close()

    reasons = [e.get("reason") for e in received]
    assert "connected" in reasons, f"No 'connected' event in: {reasons}"
    assert "broker_test_event" in reasons, f"No 'broker_test_event' in: {reasons}"


# ---------------------------------------------------------------------------
# test_stream_keepalive_after_15s
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_stream_keepalive_after_15s(monkeypatch):
    """When the queue times out, the generator must yield a keep-alive comment."""
    import sistema.app.routers.web_check as web_check_module

    async def instant_timeout(coro, timeout):
        coro.close()
        raise asyncio.TimeoutError()

    monkeypatch.setattr(web_check_module.asyncio, "wait_for", instant_timeout)

    db = SessionLocal()
    try:
        _ensure_test_user(db)
        # disconnects_after=1: one keep-alive cycle then disconnect
        mock_req = _make_mock_request(disconnects_after=1)

        streaming_response = await stream_web_check_updates(
            request=mock_req,
            chave=TEST_CHAVE,
            db=db,
        )

        raw_chunks: list[str] = []
        async for chunk in streaming_response.body_iterator:
            if isinstance(chunk, bytes):
                chunk = chunk.decode()
            raw_chunks.append(chunk)

    finally:
        db.close()

    all_text = "".join(raw_chunks)
    assert ": keep-alive" in all_text, f"No keep-alive in: {all_text!r}"
