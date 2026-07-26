"""Only canonical profile values may be stored.

  0 usuário comum · 1 admin dos seus projetos · 2 admin do Transport
  3 admin dos seus projetos + Transport · 9 admin irrestrito

The profile is a set of access digits, so an arbitrary integer parses into
something that looks meaningful but is not: 19 reads as {1,9} = "admin + tudo",
redundant because 9 already grants everything, and inconsistent because the digit
9 makes it unrestricted by project scope while the exact `perfil == 9` checks
(deleting an accident, revoking a super-admin, viewing activity times) still
refuse it. The project already hit this once with the legacy "12", which is why 3
exists.

Two independent doors had to be closed: digits_to_profile could mint 19, and the
cadastro API accepted any integer 0-999 straight from the request body.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sistema.app.models import User
from sistema.app.schemas import AdminProfileUpdateRequest, AdminUserUpsert
from sistema.app.services.admin_auth import (
    CANONICAL_USER_PROFILES,
    add_profile_access,
    digits_to_profile,
    get_admin_allowed_tabs,
    get_user_profile_digits,
    profile_can_view_activity_time,
    remove_profile_access,
    user_has_admin_access,
    user_has_full_admin_access,
    user_has_transport_access,
)

_CANONICAL = [0, 1, 2, 3, 9]
_REJECTED = [19, 12, 29, 91, 99, 777, 11, 4, 5]


def test_canonical_set_is_exactly_the_documented_five():
    assert set(CANONICAL_USER_PROFILES) == set(_CANONICAL)


# ---------------------------------------------------------------------------
# digits_to_profile — the only function that could mint a non-canonical value
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "digits, expected",
    [
        (set(), 0),
        ({"1"}, 1),
        ({"2"}, 2),
        ({"1", "2"}, 3),      # legacy "12" collapsed to 3
        ({"9"}, 9),
        ({"1", "9"}, 9),      # used to be 19
        ({"2", "9"}, 9),      # used to be 29
        ({"1", "2", "9"}, 9),
    ],
)
def test_digits_to_profile_only_yields_canonical_values(digits, expected):
    result = digits_to_profile(digits)
    assert result == expected
    assert result in CANONICAL_USER_PROFILES


def test_granting_access_never_produces_a_hybrid_of_nine():
    assert add_profile_access(1, "9") == 9
    assert add_profile_access(9, "1") == 9
    assert add_profile_access(9, "2") == 9
    assert add_profile_access(1, "2") == 3
    # And a legacy 19 already in the database normalises on the next write.
    assert add_profile_access(19, "1") == 9
    assert add_profile_access(19, "2") == 9


def test_revoking_from_full_admin_clears_everything():
    assert remove_profile_access(9, "1") == 0
    assert remove_profile_access(3, "2") == 1
    assert remove_profile_access(3, "1") == 2


# ---------------------------------------------------------------------------
# Perfil 3 must be exactly perfil 1 + perfil 2 — nothing more, nothing less
# ---------------------------------------------------------------------------


def _user(perfil: int) -> User:
    """Unsaved User: every predicate under test reads only `.perfil`."""
    return User(chave="TST0", nome="Perfil Teste", projeto="P80", perfil=perfil)


def test_profile_3_digits_are_the_union_of_1_and_2():
    assert get_user_profile_digits(3) == (
        get_user_profile_digits(1) | get_user_profile_digits(2)
    )


def test_profile_3_grants_admin_exactly_like_profile_1():
    three, one = _user(3), _user(1)
    assert user_has_admin_access(three) == user_has_admin_access(one) is True
    assert get_admin_allowed_tabs(three) == get_admin_allowed_tabs(one)
    # Scoped by project just like a perfil 1 — 3 carries no full-access digit.
    assert user_has_full_admin_access(three) is False
    # And, like perfil 1, does NOT see check-in/check-out activity times.
    assert profile_can_view_activity_time(3) == profile_can_view_activity_time(1) is False


def test_profile_3_grants_transport_exactly_like_profile_2():
    assert user_has_transport_access(_user(3)) == user_has_transport_access(_user(2)) is True


def test_profile_3_grants_nothing_beyond_1_and_2():
    """It must not creep towards perfil 9."""
    three, nine = _user(3), _user(9)
    assert user_has_full_admin_access(three) is not user_has_full_admin_access(nine)
    assert profile_can_view_activity_time(3) is not profile_can_view_activity_time(9)


def test_combining_1_and_2_lands_on_3_from_either_direction():
    assert add_profile_access(1, "2") == 3
    assert add_profile_access(2, "1") == 3


def test_splitting_3_returns_the_original_halves():
    assert remove_profile_access(3, "2") == 1
    assert remove_profile_access(3, "1") == 2


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


def _upsert_payload(perfil):
    return {
        "rfid": "RF0001",
        "nome": "Usuario Teste",
        "chave": "ZQ12",
        "perfil": perfil,
        "projeto": "P80",
        "projetos": ["P80"],
    }


@pytest.mark.parametrize("perfil", _CANONICAL)
def test_upsert_accepts_canonical_profiles(perfil):
    model = AdminUserUpsert(**_upsert_payload(perfil))
    assert model.perfil == perfil


@pytest.mark.parametrize("perfil", _REJECTED)
def test_upsert_rejects_non_canonical_profiles(perfil):
    with pytest.raises(ValidationError) as exc:
        AdminUserUpsert(**_upsert_payload(perfil))
    assert "Perfil invalido" in str(exc.value)


@pytest.mark.parametrize("perfil", _CANONICAL)
def test_profile_update_accepts_canonical_profiles(perfil):
    assert AdminProfileUpdateRequest(perfil=perfil).perfil == perfil


@pytest.mark.parametrize("perfil", _REJECTED)
def test_profile_update_rejects_non_canonical_profiles(perfil):
    with pytest.raises(ValidationError):
        AdminProfileUpdateRequest(perfil=perfil)


def test_negative_and_garbage_profiles_are_rejected():
    for bad in (-1, "abc", 1000):
        with pytest.raises(ValidationError):
            AdminProfileUpdateRequest(perfil=bad)


# ---------------------------------------------------------------------------
# Only perfil 9 sees check-in / check-out activity times
# ---------------------------------------------------------------------------


def test_only_full_admin_sees_activity_times():
    assert profile_can_view_activity_time(9) is True
    for perfil in (0, 1, 2, 3):
        assert profile_can_view_activity_time(perfil) is False, perfil
