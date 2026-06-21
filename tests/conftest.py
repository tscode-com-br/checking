"""Pytest configuration — set test environment variables before any app module is imported.

conftest.py is processed by pytest before test modules are collected or imported,
ensuring DATABASE_URL and other env vars are in place when sistema.app.database
creates its module-level SQLAlchemy engine.
"""
import os

import pytest

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

# Register accident-mode fixtures so they are available to every test_*.py.
pytest_plugins = ["tests.conftest_accident"]


# ─── Production-touching e2e guard (temp002 TP0 / plan002 §0.6) ─────────────────────────────────────
# SAFETY (plan002 §0.6): a real check-in/check-out submit to PROD for chave TEST writes real events AND
# triggers real FORMS browser automation for TEST's projects. Therefore:
#   • Default the suite to the LOCAL backend (SQLite, in-process TestClient) — it already is; no test in
#     the default run reaches production.
#   • Any test that reaches production MUST be marked `@pytest.mark.prod_e2e`. Such tests are SKIPPED
#     unless `CHECKING_E2E_PROD=1` is set explicitly, so they never run in the default suite or CI.
#   • Use prod ONLY for read verification + a small, clearly-marked, cleaned-up controlled submit. Never
#     loop-submit; never run the FORMS-per-project e2e against prod without explicit human approval.
CHECKING_E2E_PROD_ENV = "CHECKING_E2E_PROD"


def prod_e2e_enabled() -> bool:
    """True only when the operator explicitly opts in to production-touching e2e tests."""
    return os.environ.get(CHECKING_E2E_PROD_ENV) == "1"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "prod_e2e: test reaches PRODUCTION; skipped unless CHECKING_E2E_PROD=1 (plan002 §0.6 safety).",
    )


def pytest_collection_modifyitems(config, items):
    if prod_e2e_enabled():
        return
    skip_prod = pytest.mark.skip(
        reason="production e2e disabled — set CHECKING_E2E_PROD=1 to run (plan002 §0.6)."
    )
    for item in items:
        if "prod_e2e" in item.keywords:
            item.add_marker(skip_prod)
