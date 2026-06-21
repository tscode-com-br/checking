"""EP1 (plan004 §2.1) — guarded END-TO-END read of GET /api/web/check/history against LIVE production.

Every test here reaches PRODUCTION and is marked `@pytest.mark.prod_e2e` → SKIPPED unless
`CHECKING_E2E_PROD=1` (the default suite stays offline; see `tests/conftest.py`). Read-only — a single GET
(plus a login to obtain the session). No writes, no loops.

Purpose: verify the "change D" history bundle (plan004 §0.6 / §2.1) ONCE DEPLOYED — i.e. `GET /check/history`
returns the user's history with each row carrying a `local` (location). Until the bundle is committed +
pushed and **migration 0078 has run in production**, prod returns 404 for this endpoint; running this test
with the opt-in before then will fail BY DESIGN — that failure is exactly the "deploy still pending" signal.
"""
import os

import pytest

httpx = pytest.importorskip("httpx")  # ships with FastAPI TestClient; skip this file if somehow absent

PROD_BASE = os.environ.get("CHECKING_E2E_BASE", "https://tscode.com.br/api")
TEST_CHAVE = "TEST"
TEST_SENHA = "000000"


def _client() -> "httpx.Client":
    return httpx.Client(base_url=PROD_BASE, timeout=30.0)


def _login(c) -> None:
    r = c.post("/web/auth/login", json={"chave": TEST_CHAVE, "senha": TEST_SENHA})
    assert r.status_code == 200, f"login failed: {r.text}"


@pytest.mark.prod_e2e
def test_history_endpoint_returns_items_with_location():
    with _client() as c:
        _login(c)
        r = c.get("/web/check/history", params={"chave": TEST_CHAVE})
        assert r.status_code == 200, (
            "GET /check/history not 200 — is the change-D bundle deployed and migration 0078 run? "
            f"{r.status_code} {r.text}"
        )
        body = r.json()
        items = body.get("items")
        assert isinstance(items, list), f"expected an 'items' list, got: {body}"
        # Each row must carry the change-D shape, including the `local` field key.
        for item in items:
            assert {"action", "projeto", "local", "time", "informe"} <= set(item.keys()), item
        # Post-deploy with real attendance data: at least one row should carry a non-null location.
        assert any(item.get("local") for item in items), (
            "no history row has a non-null `local` — either pre-deploy data only, or the location write "
            "path is not live yet (record a located check-in for TEST after deploy, then re-run)"
        )
