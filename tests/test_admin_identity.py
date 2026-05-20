"""Unit tests for services.admin_identity.

Verifies the helper that bridges users -> admin_users for audit FKs.
These would have caught the FK-violation regression where
``current_admin.id`` (users.id) was written to ``opened_by_admin_id``
(FK -> admin_users.id).
"""
from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa

from sistema.app.database import SessionLocal
from sistema.app.models import AdminUser, User
from sistema.app.services.admin_identity import (
    ensure_admin_user_by_chave,
    resolve_admin_user_for_user,
)
from sistema.app.services.passwords import hash_password


_CHAVE = "AI01"


def _wipe_admin_user_with_chave(db: sa.orm.Session, chave: str) -> None:
    db.execute(sa.delete(AdminUser).where(AdminUser.chave == chave))
    db.commit()


def _make_user(db: sa.orm.Session, *, chave: str, nome: str, perfil: int = 1) -> User:
    user = db.execute(sa.select(User).where(User.chave == chave)).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            chave=chave,
            nome=nome,
            projeto="P-Test",
            checkin=False,
            local=None,
            last_active_at=now,
            inactivity_days=0,
            perfil=perfil,
            senha=hash_password("ignored-test-pw"),
        )
        db.add(user)
    else:
        user.nome = nome
        user.perfil = perfil
    db.commit()
    db.refresh(user)
    return user


def test_ensure_admin_user_creates_when_absent() -> None:
    with SessionLocal() as db:
        _wipe_admin_user_with_chave(db, _CHAVE)

        admin_user = ensure_admin_user_by_chave(
            db, chave=_CHAVE, nome_completo="Test Admin"
        )
        db.commit()

        assert admin_user.id is not None
        assert admin_user.chave == _CHAVE
        assert admin_user.nome_completo == "Test Admin"
        assert admin_user.password_hash is None

        # Confirm the row really landed in the DB
        fetched = db.execute(
            sa.select(AdminUser).where(AdminUser.chave == _CHAVE)
        ).scalar_one()
        assert fetched.id == admin_user.id


def test_ensure_admin_user_is_idempotent() -> None:
    with SessionLocal() as db:
        _wipe_admin_user_with_chave(db, _CHAVE)
        first = ensure_admin_user_by_chave(
            db, chave=_CHAVE, nome_completo="Test Admin"
        )
        db.commit()
        first_id = first.id

        second = ensure_admin_user_by_chave(
            db, chave=_CHAVE, nome_completo="Test Admin"
        )
        db.commit()

        assert second.id == first_id  # same row, no duplicate


def test_ensure_admin_user_updates_name_when_changed() -> None:
    with SessionLocal() as db:
        _wipe_admin_user_with_chave(db, _CHAVE)
        ensure_admin_user_by_chave(db, chave=_CHAVE, nome_completo="Old Name")
        db.commit()

        updated = ensure_admin_user_by_chave(
            db, chave=_CHAVE, nome_completo="New Name"
        )
        db.commit()

        assert updated.nome_completo == "New Name"


def test_resolve_admin_user_for_user_creates_paired_row() -> None:
    with SessionLocal() as db:
        _wipe_admin_user_with_chave(db, _CHAVE)
        user = _make_user(db, chave=_CHAVE, nome="Test Admin Person")

        admin_user = resolve_admin_user_for_user(db, user)
        db.commit()

        assert admin_user.chave == user.chave
        assert admin_user.nome_completo == user.nome
        # The two IDs must NOT be confused: they live in different tables and
        # are not guaranteed to coincide. The test simply asserts that we got
        # a valid admin_users row back.
        assert admin_user.id is not None


def test_resolve_admin_user_is_idempotent_across_calls() -> None:
    with SessionLocal() as db:
        _wipe_admin_user_with_chave(db, _CHAVE)
        user = _make_user(db, chave=_CHAVE, nome="Test Admin Person")

        first = resolve_admin_user_for_user(db, user)
        second = resolve_admin_user_for_user(db, user)
        db.commit()

        assert first.id == second.id
