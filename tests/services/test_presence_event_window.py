"""Janela de eventos das telas de presenca (min_event_time).

As telas de presenca do admin so exibem usuarios com atividade nas ultimas 24h
(is_user_inactive), mas carregavam o historico INTEIRO de user_sync_events/check_events a cada
poll — a query de ~7k+ linhas que esgotava CPU/pool em producao. O corte min_event_time limita o
carregamento a janela recente SEM mudar o resultado visivel: quem ficou fora da janela resolve
para None e ja seria descartado pela tela.

Protege:
1. min_event_time filtra os dois loaders (sync events e check events);
2. default (None) preserva o comportamento antigo — historico completo;
3. resolve_latest_user_activities com janela: atividade recente resolve igual, usuario so com
   atividade antiga resolve None (equivalente, para a tela, ao descarte por inatividade).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import CheckEvent, User, UserSyncEvent
from sistema.app.services.user_sync import (
    list_check_activity_events_for_rfids,
    list_user_sync_events_for_users,
    resolve_latest_user_activities,
)

_NOW = datetime(2026, 7, 6, 12, 0, 0, tzinfo=timezone.utc)
_RECENT = _NOW - timedelta(hours=1)
_OLD = _NOW - timedelta(days=10)
_CUTOFF = _NOW - timedelta(hours=72)


def _make_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / 'test_window.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)()


def _make_user(db: Session, *, chave: str, rfid: str | None) -> User:
    user = User(
        rfid=rfid,
        chave=chave,
        nome=f"User {chave}",
        senha=None,
        last_active_at=_NOW,
        inactivity_days=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _add_sync_event(db: Session, user: User, *, event_time: datetime, request_id: str) -> None:
    db.add(
        UserSyncEvent(
            user_id=user.id,
            chave=user.chave,
            rfid=user.rfid,
            source="web",
            action="checkin",
            projeto=None,
            local="Local A",
            ontime=True,
            event_time=event_time,
            created_at=event_time,
            source_request_id=request_id,
        )
    )
    db.commit()


def _add_check_event(db: Session, *, rfid: str, event_time: datetime, key: str) -> None:
    db.add(
        CheckEvent(
            idempotency_key=key,
            source="web",
            rfid=rfid,
            action="checkin",
            status="success",
            message="checkin ok",
            event_time=event_time,
        )
    )
    db.commit()


def test_sync_events_loader_respects_min_event_time(tmp_path: Path) -> None:
    db = _make_session(tmp_path)
    try:
        user = _make_user(db, chave="JW01", rfid=None)
        _add_sync_event(db, user, event_time=_OLD, request_id="req-old")
        _add_sync_event(db, user, event_time=_RECENT, request_id="req-recent")

        bounded = list_user_sync_events_for_users(db, user_ids={user.id}, min_event_time=_CUTOFF)
        assert [event.source_request_id for event in bounded[user.id]] == ["req-recent"]

        unbounded = list_user_sync_events_for_users(db, user_ids={user.id})
        assert {event.source_request_id for event in unbounded[user.id]} == {"req-old", "req-recent"}
    finally:
        db.close()


def test_check_events_loader_respects_min_event_time(tmp_path: Path) -> None:
    db = _make_session(tmp_path)
    try:
        _add_check_event(db, rfid="RFID-JW", event_time=_OLD, key="key-old")
        _add_check_event(db, rfid="RFID-JW", event_time=_RECENT, key="key-recent")

        bounded = list_check_activity_events_for_rfids(db, rfids={"RFID-JW"}, min_event_time=_CUTOFF)
        assert [event.idempotency_key for event in bounded["RFID-JW"]] == ["key-recent"]

        unbounded = list_check_activity_events_for_rfids(db, rfids={"RFID-JW"})
        assert {event.idempotency_key for event in unbounded["RFID-JW"]} == {"key-old", "key-recent"}
    finally:
        db.close()


def test_resolve_with_window_keeps_recent_and_drops_stale_user(tmp_path: Path) -> None:
    db = _make_session(tmp_path)
    try:
        recent_user = _make_user(db, chave="JW02", rfid=None)
        stale_user = _make_user(db, chave="JW03", rfid=None)
        _add_sync_event(db, recent_user, event_time=_OLD, request_id="req-a-old")
        _add_sync_event(db, recent_user, event_time=_RECENT, request_id="req-a-recent")
        _add_sync_event(db, stale_user, event_time=_OLD, request_id="req-b-old")

        resolved = resolve_latest_user_activities(
            db,
            users=[recent_user, stale_user],
            include_current_state=False,
            min_event_time=_CUTOFF,
        )

        recent_activity = resolved[recent_user.id]
        assert recent_activity is not None
        assert recent_activity.source_request_id == "req-a-recent"
        # Fora da janela: resolve None — a tela de presenca ja descartaria (is_user_inactive > 24h).
        assert resolved[stale_user.id] is None

        # Sem janela (default), o comportamento antigo permanece: a atividade antiga aparece.
        resolved_unbounded = resolve_latest_user_activities(
            db,
            users=[stale_user],
            include_current_state=False,
        )
        stale_activity = resolved_unbounded[stale_user.id]
        assert stale_activity is not None
        assert stale_activity.source_request_id == "req-b-old"
    finally:
        db.close()
