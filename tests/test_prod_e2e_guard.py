"""TP0 — proves the production-e2e opt-in guard keeps the default suite offline (plan002 §0.6).

`@pytest.mark.prod_e2e` tests are skipped unless CHECKING_E2E_PROD=1. This file self-verifies that
mechanism so future prod-touching tests (TP8) can rely on it.
"""
import os

import pytest

from tests.conftest import prod_e2e_enabled


def test_guard_disabled_by_default():
    # The default run must never reach production: with no opt-in, prod e2e is disabled.
    if os.environ.get("CHECKING_E2E_PROD") == "1":
        pytest.skip("CHECKING_E2E_PROD=1 set — the offline-default assertion does not apply")
    assert prod_e2e_enabled() is False


@pytest.mark.prod_e2e
def test_prod_e2e_marked_tests_are_skipped_without_optin():
    # If the guard works this body never runs in the default suite. If it DID run without the opt-in,
    # fail loudly: that would mean prod-touching tests are leaking into the default run.
    assert prod_e2e_enabled() is True, (
        "a @prod_e2e test executed without CHECKING_E2E_PROD=1 — the safety guard is broken"
    )
