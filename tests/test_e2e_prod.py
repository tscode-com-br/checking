"""TP8 — guarded END-TO-END against the LIVE production API (plan002 §0.6).

EVERY test here reaches PRODUCTION and is marked `@pytest.mark.prod_e2e` → SKIPPED unless
`CHECKING_E2E_PROD=1`. WRITE/submit tests ADDITIONALLY require `CHECKING_E2E_PROD_SUBMIT=1`: they create
real events AND trigger real FORMS browser automation for TEST's projects, so they need explicit human
approval and must NEVER be looped.

They also assume EP1/EP5/EP7 are DEPLOYED (currently pending human approval — see temp002 §3 EP1-1/EP5-1/
EP7-1): `GET /check/history` (EP1) returns the location-bearing list; an android "Localização não
Cadastrada" check-in → 200 (EP5); FORMS once per project (EP7). Until deployed, the history/android-200
assertions will fail — which is why they only run with the explicit opt-in (never in the default suite).

STEP 2 (prod DB read-only inspection) is a MANUAL operator step, not automated here (needs SSH+docker per
§0.6). Recipe:
    wsl bash -c "cp /mnt/c/dev/projetos/checkcheck/deploy/keys/do_checkcheck /tmp/do_ck && chmod 600 /tmp/do_ck && \
      ssh -o StrictHostKeyChecking=no -i /tmp/do_ck root@157.230.35.21 \
      'docker exec checkcheck-db-1 psql -U checking -d checking -c \"SELECT projeto, atividade, local, time \
       FROM checkinghistory WHERE chave='\\''TEST'\\'' ORDER BY time DESC LIMIT 10;\"'; rm -f /tmp/do_ck"
  → confirm, for a recent TEST event: one checkinghistory row per project, forms_submission rows per
    project, and check_events.local matching the history.
"""
import os
import uuid
from datetime import datetime, timezone

import pytest

httpx = pytest.importorskip("httpx")  # ships with FastAPI TestClient; skip this file if somehow absent

PROD_BASE = os.environ.get("CHECKING_E2E_BASE", "https://tscode.com.br/api")
TEST_CHAVE = "TEST"
TEST_SENHA = "000000"
ANDROID_HEADERS = {"X-Client": "checking-android"}
_UNREGISTERED = "Localização não Cadastrada"


def _require_submit_optin() -> None:
    if os.environ.get("CHECKING_E2E_PROD_SUBMIT") != "1":
        pytest.skip("write/submit e2e needs CHECKING_E2E_PROD_SUBMIT=1 + human approval (writes prod + FORMS)")


def _client() -> "httpx.Client":
    return httpx.Client(base_url=PROD_BASE, timeout=30.0)


def _login(c) -> None:
    r = c.post("/web/auth/login", json={"chave": TEST_CHAVE, "senha": TEST_SENHA})
    assert r.status_code == 200, f"login failed: {r.text}"


def _active_projeto(c) -> str:
    return c.get("/web/check/state", params={"chave": TEST_CHAVE}).json().get("projeto") or "P80"


# ── Read-only (opt-in CHECKING_E2E_PROD=1) ──────────────────────────────────────────────────────────
@pytest.mark.prod_e2e
def test_health_ok():
    r = httpx.get(f"{PROD_BASE}/health", timeout=30.0)
    assert r.status_code == 200, r.text


@pytest.mark.prod_e2e
def test_login_and_read_only_endpoints():
    with _client() as c:
        _login(c)
        assert c.get("/web/check/state", params={"chave": TEST_CHAVE}).status_code == 200
        hist = c.get("/web/check/history", params={"chave": TEST_CHAVE})  # EP1
        assert hist.status_code == 200, f"GET /check/history not 200 (EP1 deployed?): {hist.text}"
        for it in hist.json().get("items", []):
            assert {"action", "projeto", "local", "time", "informe"} <= set(it.keys())
        assert c.get("/web/check/locations").status_code == 200


@pytest.mark.prod_e2e
def test_web_client_unregistered_local_checkin_still_422():
    # Negative check (server rejects BEFORE recording → no write): the browser web app cannot submit a
    # check-in at "Localização não Cadastrada". Preserved invariant, independent of EP5.
    with _client() as c:
        _login(c)
        r = c.post("/web/check", json={
            "chave": TEST_CHAVE, "projeto": _active_projeto(c), "action": "checkin",
            "local": _UNREGISTERED, "informe": "normal",
            "event_time": datetime.now(timezone.utc).isoformat(),
            "client_event_id": f"e2e-web-{uuid.uuid4()}",
        })  # no X-Client → web client
        assert r.status_code == 422, f"web client must 422 on unregistered local, got {r.status_code}: {r.text}"


# ── Writes (opt-in CHECKING_E2E_PROD=1 AND CHECKING_E2E_PROD_SUBMIT=1; trigger real FORMS) ───────────
@pytest.mark.prod_e2e
def test_android_unregistered_local_checkin_accepted():
    # EP5: the app (X-Client) may check in at "Localização não Cadastrada" → 200.
    _require_submit_optin()
    with _client() as c:
        _login(c)
        r = c.post("/web/check", headers=ANDROID_HEADERS, json={
            "chave": TEST_CHAVE, "projeto": _active_projeto(c), "action": "checkin",
            "local": _UNREGISTERED, "informe": "normal",
            "event_time": datetime.now(timezone.utc).isoformat(),
            "client_event_id": f"e2e-android-{uuid.uuid4()}",
        })
        assert r.status_code == 200, f"android unregistered check-in must 200 (EP5 deployed?): {r.text}"


@pytest.mark.prod_e2e
def test_controlled_checkin_appears_in_history_with_location():
    # One controlled check-in via the app channel → it appears in /check/history WITH its location.
    # The "no duplicate on re-foreground" guarantee is CLIENT-side (change A) → device matrix (TP9).
    _require_submit_optin()
    with _client() as c:
        _login(c)
        projeto = _active_projeto(c)
        areas = c.get("/web/check/locations").json().get("items", [])
        area = next((a for a in areas if "checkout" not in a.lower() and "mista" not in a.lower()), None)
        assert area, "TEST needs ≥1 registered (non-CheckOut/Mista) area for this test"
        c.post("/web/check", headers=ANDROID_HEADERS, json={
            "chave": TEST_CHAVE, "projeto": projeto, "action": "checkin", "local": area,
            "informe": "normal", "event_time": datetime.now(timezone.utc).isoformat(),
            "client_event_id": f"e2e-checkin-{uuid.uuid4()}",
        }).raise_for_status()
        hist = c.get("/web/check/history", params={"chave": TEST_CHAVE}).json().get("items", [])
        assert any(it["action"] == "checkin" and it["local"] == area for it in hist), \
            "the controlled check-in should appear in /check/history with its location"
