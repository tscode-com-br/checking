"""P1.1 (plan002 change D) — CheckingHistory.local population + dedup invariance.

Asserts that record_checking_history now stores the activity location AND that the
idempotent upsert still dedups on the unchanged 5-field key (local is NOT part of it).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import CheckingHistory
from sistema.app.services.checking_history import record_checking_history

_NOW = datetime(2026, 6, 17, 8, 0, 0, tzinfo=timezone.utc)


def _make_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(
        f"sqlite+pysqlite:///{(tmp_path / 'test_history_local.db').as_posix()}"
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
    )
    return factory()


def test_record_checking_history_persists_local(tmp_path: Path):
    db = _make_session(tmp_path)
    row = record_checking_history(
        db,
        chave="U3RD",
        action="checkin",
        projeto="P80",
        event_time=_NOW,
        ontime=True,
        local="Localização não Cadastrada",
    )
    db.commit()
    assert row is not None
    assert row.local == "Localização não Cadastrada"
    assert db.query(CheckingHistory).one().local == "Localização não Cadastrada"


def test_record_checking_history_local_defaults_to_none(tmp_path: Path):
    db = _make_session(tmp_path)
    row = record_checking_history(
        db,
        chave="U3RD",
        action="checkout",
        projeto="P80",
        event_time=_NOW,
    )
    db.commit()
    assert row is not None
    assert row.local is None


def test_record_checking_history_dedups_on_five_key_regardless_of_local(tmp_path: Path):
    db = _make_session(tmp_path)
    first = record_checking_history(
        db,
        chave="U3RD",
        action="checkin",
        projeto="P80",
        event_time=_NOW,
        ontime=True,
        local="Area A",
    )
    db.commit()
    # Same 5-field key (chave/atividade/projeto/time/informe), DIFFERENT local → must return the
    # existing row and NOT insert a new one (local is not part of uq_checkinghistory_event).
    second = record_checking_history(
        db,
        chave="U3RD",
        action="checkin",
        projeto="P80",
        event_time=_NOW,
        ontime=True,
        local="Area B (different)",
    )
    db.commit()
    assert second is first or second.id == first.id
    assert db.query(CheckingHistory).count() == 1
    # The dedup returns the existing row untouched → the original local is preserved.
    assert db.query(CheckingHistory).one().local == "Area A"
