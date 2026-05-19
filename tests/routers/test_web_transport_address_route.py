"""Regression test for the /api/web/check/transport/address route registration.

The decorator `@router.post("/transport/address", ...)` was accidentally
dropped from `sistema/app/routers/web_check.py` during the Accident Mode
commit (`73f4907`). The function `update_web_transport_address` remained in
the module body but had no route binding, so `POST /api/web/transport/address`
returned 404. Item 6 restores the decorator. This test locks the route in
place so a future refactor cannot silently drop it again.

Note: the web_check router prefix is `/api/web` (not `/api/web/check`), so
the absolute URL is `/api/web/transport/address`. The other `/check/*`
routes in the same file simply happen to start with `/check`.

The test only verifies that the route is registered; it does not assert any
authentication or validation semantics. Any non-404 status is acceptable
because the unauthenticated request may legitimately be rejected with 401/422.
"""
from __future__ import annotations

import os

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

from sistema.app.database import Base, engine  # noqa: E402
from sistema.app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)

ROUTE_PATH = "/api/web/transport/address"


def test_route_transport_address_is_registered():
    """The FastAPI app must expose POST /api/web/check/transport/address."""
    matching_routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == ROUTE_PATH
        and "POST" in getattr(route, "methods", set())
    ]
    assert matching_routes, (
        f"POST {ROUTE_PATH} is not registered; the decorator was likely dropped again. "
        "See sistema/app/routers/web_check.py around update_web_transport_address."
    )


def test_route_transport_address_does_not_return_404():
    """An unauthenticated POST must not produce 404 (route presence smoke)."""
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(ROUTE_PATH, json={})
    assert response.status_code != 404, (
        f"POST {ROUTE_PATH} returned 404 — the route is missing. "
        f"Body: {response.text[:200]}"
    )
