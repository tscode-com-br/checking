"""TP7 (plan003) — guarded END-TO-END for the new-user APPROVAL gate against LIVE production.

EVERY test here reaches PRODUCTION and is marked `@pytest.mark.prod_e2e` → SKIPPED unless
`CHECKING_E2E_PROD=1`. The controlled WRITE test additionally needs `CHECKING_E2E_PROD_SUBMIT=1`
**and** admin credentials + a real project name supplied via env (never hardcoded) **and** human approval.

Assumes the backend is DEPLOYED with migration `0079` applied + EP2/EP3/EP4 live (currently PENDING human
approval — pushing root `main` deploys backend + Check Web; the migration must run first). Until then these
only run with the explicit opt-in (never in the default suite).

SAFETY / CLEANUP:
  • Read-only tests only GET (health, /auth/status for a throwaway key) — no writes.
  • The write test registers ONE throwaway 4-char key (verified unused first), drives pending→approve, then
    in a `finally` ALWAYS rejects any leftover pending row AND deletes any created User for that key, and
    asserts the key is gone. Never loops; never leaves test users in prod.
  • Queue-full (300-row cap) is NOT exercised against prod — it stays LOCAL (TP1#5).
  • Admin credentials come from CHECKING_E2E_ADMIN_CHAVE / CHECKING_E2E_ADMIN_SENHA; the deploy key is
    never read or exposed here.
"""
import os
import uuid

import pytest

httpx = pytest.importorskip("httpx")  # ships with FastAPI TestClient; skip this file if somehow absent

PROD_BASE = os.environ.get("CHECKING_E2E_BASE", "https://tscode.com.br/api")
_E2E_PASSWORD = "e2e123"  # 3–10 chars, satisfies the public registration rule


def _require_submit_optin() -> None:
    if os.environ.get("CHECKING_E2E_PROD_SUBMIT") != "1":
        pytest.skip("approval write e2e needs CHECKING_E2E_PROD_SUBMIT=1 + human approval (writes prod)")


def _admin_credentials() -> tuple[str, str]:
    chave = os.environ.get("CHECKING_E2E_ADMIN_CHAVE")
    senha = os.environ.get("CHECKING_E2E_ADMIN_SENHA")
    if not chave or not senha:
        pytest.skip("approval write e2e needs CHECKING_E2E_ADMIN_CHAVE/CHECKING_E2E_ADMIN_SENHA (admin session)")
    return chave, senha


def _e2e_project() -> str:
    project = os.environ.get("CHECKING_E2E_PROJECT")
    if not project:
        pytest.skip("approval write e2e needs CHECKING_E2E_PROJECT set to a real prod project name")
    return project


def _client() -> "httpx.Client":
    # httpx.Client keeps a cookie jar across requests → admin session persists after login.
    return httpx.Client(base_url=PROD_BASE, timeout=30.0)


def _random_key() -> str:
    # 4 uppercase alphanumerics from a uuid (hex is alnum); good enough for a throwaway, verified-unused key.
    return uuid.uuid4().hex[:4].upper()


def _auth_status(client, chave: str) -> dict:
    r = client.get("/web/auth/status", params={"chave": chave})
    assert r.status_code == 200, f"/auth/status not 200: {r.text}"
    return r.json()


def _fresh_unused_key(client) -> str:
    # Never clobber a real key: generate until /auth/status shows neither a User nor a pending row.
    for _ in range(8):
        candidate = _random_key()
        status = _auth_status(client, candidate)
        if not status.get("found") and not status.get("pending_approval"):
            return candidate
    pytest.skip("could not find an unused throwaway key after several attempts")


def _admin_login(admin) -> None:
    chave, senha = _admin_credentials()
    r = admin.post("/admin/auth/login", json={"chave": chave, "senha": senha})
    assert r.status_code == 200, f"admin login failed: {r.text}"


def _cleanup_key(chave: str) -> None:
    """Idempotent prod cleanup: reject any pending row + delete any created User for `chave`, then assert
    the key is gone. Runs in a fresh admin session so it works even if the test failed mid-flight."""
    with _client() as admin:
        _admin_login(admin)
        pendings = admin.get("/admin/user-pending")
        if pendings.status_code == 200:
            for row in pendings.json():
                if row.get("chave") == chave:
                    admin.post(f"/admin/user-pending/{row['id']}/reject")
        users = admin.get("/admin/users")
        if users.status_code == 200:
            for row in users.json():
                if row.get("chave") == chave:
                    admin.delete(f"/admin/users/{row['id']}")
    with _client() as c:
        final = _auth_status(c, chave)
        assert final.get("found") is False and final.get("pending_approval") is False, (
            f"cleanup left state for {chave}: {final}"
        )


# ── Read-only (opt-in CHECKING_E2E_PROD=1) ──────────────────────────────────────────────────────────
@pytest.mark.prod_e2e
def test_prod_health_ok():
    r = httpx.get(f"{PROD_BASE}/health", timeout=30.0)
    assert r.status_code == 200, r.text


@pytest.mark.prod_e2e
def test_auth_status_exposes_pending_approval_field():
    # Validates 0079/EP2 deployed: /auth/status carries `pending_approval`. A brand-new key (no User, no
    # pending) → field present and False; found False. Read-only (a status GET writes nothing).
    with _client() as c:
        body = _auth_status(c, _random_key())
    assert "pending_approval" in body, "GET /auth/status must expose pending_approval (EP2 deployed?)"
    if not body.get("found"):
        assert body["pending_approval"] is False


# ── Controlled write (opt-in CHECKING_E2E_PROD=1 AND CHECKING_E2E_PROD_SUBMIT=1 + admin creds) ───────
@pytest.mark.prod_e2e
def test_register_pending_then_approve_then_cleanup():
    # register throwaway → 202 pending → /auth/status pending → admin approve → /auth/status found.
    # The finally ALWAYS cleans up (reject leftover pending + delete created User) and asserts the key is gone.
    _require_submit_optin()
    _admin_credentials()  # skip early if admin creds are missing
    project = _e2e_project()

    with _client() as c:
        chave = _fresh_unused_key(c)
        try:
            reg = c.post("/web/auth/register-user", json={
                "chave": chave,
                "nome": "E2E TP7 Throwaway",
                "projetos": [project],
                "email": None,
                "senha": _E2E_PASSWORD,
                "confirmar_senha": _E2E_PASSWORD,
            })
            assert reg.status_code == 202, f"register must be 202 pending (gate ON?): {reg.status_code} {reg.text}"
            body = reg.json()
            assert body.get("status") == "pending"
            assert body.get("pending_approval") is True
            assert body.get("authenticated") is False

            pending_status = _auth_status(c, chave)
            assert pending_status.get("pending_approval") is True
            assert pending_status.get("found") is False

            with _client() as admin:
                _admin_login(admin)
                pendings = admin.get("/admin/user-pending")
                assert pendings.status_code == 200, pendings.text
                row = next((p for p in pendings.json() if p.get("chave") == chave), None)
                assert row is not None, "the pending row must be visible to the admin (project scope)"
                approve = admin.post(f"/admin/user-pending/{row['id']}/approve")
                assert approve.status_code == 200, f"approve failed: {approve.text}"

            approved_status = _auth_status(c, chave)
            assert approved_status.get("found") is True, "after approval the User must exist (found=true)"
            assert approved_status.get("pending_approval") is False
        finally:
            _cleanup_key(chave)
