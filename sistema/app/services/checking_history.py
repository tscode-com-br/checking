from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CheckingHistory


_HISTORY_ACTIVITY_BY_ACTION = {
    "checkin": "check-in",
    "checkout": "check-out",
}


def normalize_history_activity(action: str) -> str | None:
    return _HISTORY_ACTIVITY_BY_ACTION.get(str(action or "").strip().lower())


def normalize_history_informe(ontime: bool | None) -> str:
    return "retroativo" if ontime is False else "normal"


def record_checking_history(
    db: Session,
    *,
    chave: str,
    action: str,
    projeto: str | None,
    event_time: datetime,
    ontime: bool | None = True,
) -> CheckingHistory | None:
    atividade = normalize_history_activity(action)
    normalized_chave = str(chave or "").strip().upper()
    normalized_projeto = str(projeto or "").strip().upper()
    if not atividade or len(normalized_chave) != 4 or not normalized_projeto:
        return None

    informe = normalize_history_informe(ontime)
    existing = db.execute(
        select(CheckingHistory)
        .where(
            CheckingHistory.chave == normalized_chave,
            CheckingHistory.atividade == atividade,
            CheckingHistory.projeto == normalized_projeto,
            CheckingHistory.time == event_time,
            CheckingHistory.informe == informe,
        )
        .limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    row = CheckingHistory(
        chave=normalized_chave,
        atividade=atividade,
        projeto=normalized_projeto,
        time=event_time,
        informe=informe,
    )
    db.add(row)
    return row
