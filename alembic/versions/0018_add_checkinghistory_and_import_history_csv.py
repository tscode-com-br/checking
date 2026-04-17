"""add checkinghistory and import historical csv data

Revision ID: 0018_checkinghistory_csv_import
Revises: 0017_vehicles_user_transport
Create Date: 2026-04-17 18:10:00
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from alembic import op
import sqlalchemy as sa


revision = "0018_checkinghistory_csv_import"
down_revision = "0017_vehicles_user_transport"
branch_labels = None
depends_on = None

_ALLOWED_PROJECTS = {"P80", "P82", "P83"}
_ALLOWED_EVENT_STATUSES = {"queued", "updated", "success", "synced", "created", "submitted"}
_NAME_CONNECTORS = {"de", "do", "da", "dos", "das", "e"}
_SOURCE_RANKS = {
    "csv": 1,
    "check_event": 2,
    "user_sync": 3,
    "user_state": 4,
}


def _normalize_key(value: str | None) -> str | None:
    normalized = str(value or "").strip().upper()
    if len(normalized) != 4 or not normalized.isalnum():
        return None
    return normalized


def _normalize_project(value: str | None) -> str | None:
    normalized = str(value or "").strip().upper()
    return normalized if normalized in _ALLOWED_PROJECTS else None


def _normalize_informe(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"normal", "retroativo"}:
        return normalized
    if normalized == "retroactive":
        return "retroativo"
    return None


def _normalize_informe_from_ontime(value: bool | None) -> str:
    return "retroativo" if value is False else "normal"


def _normalize_activity(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"check-in", "checkin"}:
        return "check-in"
    if normalized in {"check-out", "checkout"}:
        return "check-out"
    return None


def _normalize_name_word(value: str) -> str:
    lowered = value.lower()
    if lowered in _NAME_CONNECTORS:
        return lowered
    if not lowered:
        return lowered
    if "-" in lowered:
        return "-".join(_normalize_name_word(part) for part in lowered.split("-"))
    return lowered[:1].upper() + lowered[1:]


def _normalize_name(value: str | None) -> str | None:
    normalized = " ".join(str(value or "").strip().split())
    if not normalized:
        return None
    return " ".join(_normalize_name_word(part) for part in normalized.split(" "))


def _parse_history_time(date_text: str | None, time_text: str | None, tz_name: str) -> datetime | None:
    raw_date = str(date_text or "").strip()
    raw_time = str(time_text or "").strip()
    if not raw_date or not raw_time:
        return None
    parsed = datetime.strptime(f"{raw_date} {raw_time}", "%d/%m/%Y %H:%M:%S")
    return parsed.replace(tzinfo=ZoneInfo(tz_name))


def _remember_history_row(
    history_rows: list[dict[str, object]],
    history_keys: set[tuple[object, ...]],
    latest_by_chave: dict[str, dict[str, object]],
    *,
    chave: str,
    atividade: str,
    projeto: str,
    event_time: datetime,
    informe: str,
    local: str | None,
    source: str,
    sequence: int,
) -> None:
    history_key = (chave, atividade, projeto, event_time, informe)
    if history_key not in history_keys:
        history_keys.add(history_key)
        history_rows.append(
            {
                "chave": chave,
                "atividade": atividade,
                "projeto": projeto,
                "time": event_time,
                "informe": informe,
            }
        )

    rank = _SOURCE_RANKS[source]
    candidate = {
        "atividade": atividade,
        "projeto": projeto,
        "time": event_time,
        "informe": informe,
        "local": local,
        "sort_key": (event_time, rank, sequence),
    }
    current = latest_by_chave.get(chave)
    if current is None or candidate["sort_key"] > current["sort_key"]:
        latest_by_chave[chave] = candidate


def upgrade() -> None:
    op.create_table(
        "checkinghistory",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("chave", sa.String(length=4), nullable=False),
        sa.Column("atividade", sa.String(length=16), nullable=False),
        sa.Column("projeto", sa.String(length=3), nullable=False),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("informe", sa.String(length=16), nullable=False),
        sa.UniqueConstraint(
            "chave",
            "atividade",
            "projeto",
            "time",
            "informe",
            name="uq_checkinghistory_event",
        ),
        sa.CheckConstraint("atividade IN ('check-in', 'check-out')", name="ck_checkinghistory_atividade_allowed"),
        sa.CheckConstraint("projeto IN ('P80', 'P82', 'P83')", name="ck_checkinghistory_projeto_allowed"),
        sa.CheckConstraint("informe IN ('normal', 'retroativo')", name="ck_checkinghistory_informe_allowed"),
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("cargo", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("email", sa.String(length=255), nullable=True))

    bind = op.get_bind()
    tz_name = os.getenv("TZ_NAME", "Asia/Singapore")

    users = sa.table(
        "users",
        sa.column("id", sa.Integer()),
        sa.column("rfid", sa.String(length=64)),
        sa.column("chave", sa.String(length=4)),
        sa.column("nome", sa.String(length=180)),
        sa.column("projeto", sa.String(length=3)),
        sa.column("placa", sa.String(length=9)),
        sa.column("end_rua", sa.String(length=255)),
        sa.column("zip", sa.String(length=10)),
        sa.column("cargo", sa.String(length=255)),
        sa.column("email", sa.String(length=255)),
        sa.column("local", sa.String(length=40)),
        sa.column("checkin", sa.Boolean()),
        sa.column("time", sa.DateTime(timezone=True)),
        sa.column("last_active_at", sa.DateTime(timezone=True)),
        sa.column("inactivity_days", sa.Integer()),
    )
    user_sync_events = sa.table(
        "user_sync_events",
        sa.column("user_id", sa.Integer()),
        sa.column("chave", sa.String(length=4)),
        sa.column("action", sa.String(length=16)),
        sa.column("projeto", sa.String(length=3)),
        sa.column("local", sa.String(length=40)),
        sa.column("ontime", sa.Boolean()),
        sa.column("event_time", sa.DateTime(timezone=True)),
    )
    check_events = sa.table(
        "check_events",
        sa.column("rfid", sa.String(length=64)),
        sa.column("action", sa.String(length=16)),
        sa.column("status", sa.String(length=16)),
        sa.column("project", sa.String(length=3)),
        sa.column("local", sa.String(length=40)),
        sa.column("ontime", sa.Boolean()),
        sa.column("event_time", sa.DateTime(timezone=True)),
    )
    checkinghistory = sa.table(
        "checkinghistory",
        sa.column("chave", sa.String(length=4)),
        sa.column("atividade", sa.String(length=16)),
        sa.column("projeto", sa.String(length=3)),
        sa.column("time", sa.DateTime(timezone=True)),
        sa.column("informe", sa.String(length=16)),
    )

    existing_users = bind.execute(
        sa.select(
            users.c.id,
            users.c.rfid,
            users.c.chave,
            users.c.nome,
            users.c.projeto,
            users.c.placa,
            users.c.end_rua,
            users.c.zip,
            users.c.cargo,
            users.c.email,
            users.c.local,
            users.c.checkin,
            users.c.time,
            users.c.last_active_at,
            users.c.inactivity_days,
        )
    ).mappings().all()

    users_by_chave = {
        str(row["chave"]).upper(): dict(row)
        for row in existing_users
        if row["chave"] is not None
    }
    users_by_rfid = {
        str(row["rfid"]): dict(row)
        for row in existing_users
        if row["rfid"] is not None
    }

    history_rows: list[dict[str, object]] = []
    history_keys: set[tuple[object, ...]] = set()
    latest_by_chave: dict[str, dict[str, object]] = {}
    profiles_by_chave: dict[str, dict[str, object]] = {}
    sequence = 0

    csv_path = Path(__file__).resolve().parents[2] / "assets" / "tables" / "history.csv"
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=";")
            for row in reader:
                chave = _normalize_key(row.get("Chave"))
                atividade = _normalize_activity(row.get("Tipo de Registro"))
                projeto = _normalize_project(row.get("Projeto"))
                event_time = _parse_history_time(row.get("Dia do Registro"), row.get("Hora do Registro"), tz_name)
                informe = _normalize_informe(row.get("Tipo de Informe"))
                if not chave or not atividade or not projeto or event_time is None or not informe:
                    continue

                sequence += 1
                _remember_history_row(
                    history_rows,
                    history_keys,
                    latest_by_chave,
                    chave=chave,
                    atividade=atividade,
                    projeto=projeto,
                    event_time=event_time,
                    informe=informe,
                    local=None,
                    source="csv",
                    sequence=sequence,
                )

                profile = profiles_by_chave.get(chave, {})
                profile_sort_key = (event_time, sequence)
                current_sort_key = profile.get("sort_key")
                if current_sort_key is None or profile_sort_key >= current_sort_key:
                    profiles_by_chave[chave] = {
                        "nome": _normalize_name(row.get("Nome")) or profile.get("nome"),
                        "projeto": projeto or profile.get("projeto"),
                        "cargo": " ".join(str(row.get("Enfase do cargo") or "").strip().split()) or profile.get("cargo"),
                        "email": str(row.get("Email") or "").strip().lower() or profile.get("email"),
                        "sort_key": profile_sort_key,
                    }

    sync_rows = bind.execute(
        sa.select(
            user_sync_events.c.chave,
            user_sync_events.c.action,
            user_sync_events.c.projeto,
            user_sync_events.c.local,
            user_sync_events.c.ontime,
            user_sync_events.c.event_time,
        ).where(user_sync_events.c.action.in_(("checkin", "checkout")))
    ).mappings().all()
    for row in sync_rows:
        chave = _normalize_key(row["chave"])
        atividade = _normalize_activity(row["action"])
        projeto = _normalize_project(row["projeto"])
        event_time = row["event_time"]
        if not chave or not atividade or not projeto or event_time is None:
            continue
        sequence += 1
        _remember_history_row(
            history_rows,
            history_keys,
            latest_by_chave,
            chave=chave,
            atividade=atividade,
            projeto=projeto,
            event_time=event_time,
            informe=_normalize_informe_from_ontime(row["ontime"]),
            local=row["local"],
            source="user_sync",
            sequence=sequence,
        )

    event_rows = bind.execute(
        sa.select(
            check_events.c.rfid,
            check_events.c.action,
            check_events.c.status,
            check_events.c.project,
            check_events.c.local,
            check_events.c.ontime,
            check_events.c.event_time,
        ).where(
            check_events.c.action.in_(("checkin", "checkout")),
            check_events.c.status.in_(tuple(_ALLOWED_EVENT_STATUSES)),
        )
    ).mappings().all()
    for row in event_rows:
        mapped_user = users_by_rfid.get(str(row["rfid"])) if row["rfid"] is not None else None
        if mapped_user is None:
            continue
        chave = _normalize_key(mapped_user.get("chave"))
        atividade = _normalize_activity(row["action"])
        projeto = _normalize_project(row["project"]) or _normalize_project(mapped_user.get("projeto"))
        event_time = row["event_time"]
        if not chave or not atividade or not projeto or event_time is None:
            continue
        sequence += 1
        _remember_history_row(
            history_rows,
            history_keys,
            latest_by_chave,
            chave=chave,
            atividade=atividade,
            projeto=projeto,
            event_time=event_time,
            informe=_normalize_informe_from_ontime(row["ontime"]),
            local=row["local"],
            source="check_event",
            sequence=sequence,
        )

    for row in existing_users:
        chave = _normalize_key(row["chave"])
        projeto = _normalize_project(row["projeto"])
        event_time = row["time"]
        if chave is None or projeto is None or event_time is None or row["checkin"] is None:
            continue
        atividade = "check-in" if row["checkin"] else "check-out"
        sequence += 1
        _remember_history_row(
            history_rows,
            history_keys,
            latest_by_chave,
            chave=chave,
            atividade=atividade,
            projeto=projeto,
            event_time=event_time,
            informe="normal",
            local=row["local"],
            source="user_state",
            sequence=sequence,
        )

    if history_rows:
        bind.execute(checkinghistory.insert(), history_rows)

    users_to_insert: list[dict[str, object]] = []
    for chave in sorted(set(latest_by_chave) | set(profiles_by_chave)):
        latest = latest_by_chave.get(chave)
        profile = profiles_by_chave.get(chave, {})
        existing = users_by_chave.get(chave)

        desired_project = None
        desired_time = None
        desired_checkin = None
        desired_local = None
        desired_last_active_at = None
        if latest is not None:
            desired_project = latest["projeto"]
            desired_time = latest["time"]
            desired_checkin = latest["atividade"] == "check-in"
            desired_local = latest["local"]
            desired_last_active_at = latest["time"]
        elif existing is not None:
            desired_project = existing.get("projeto")
            desired_time = existing.get("time")
            desired_checkin = existing.get("checkin")
            desired_local = existing.get("local")
            desired_last_active_at = existing.get("last_active_at")
        else:
            desired_project = profile.get("projeto")

        desired_name = profile.get("nome") or (existing.get("nome") if existing is not None else None) or chave
        desired_cargo = profile.get("cargo") or (existing.get("cargo") if existing is not None else None)
        desired_email = profile.get("email") or (existing.get("email") if existing is not None else None)

        if existing is not None:
            bind.execute(
                users.update()
                .where(users.c.id == existing["id"])
                .values(
                    nome=desired_name,
                    projeto=desired_project or existing["projeto"],
                    cargo=desired_cargo,
                    email=desired_email,
                    local=desired_local,
                    checkin=desired_checkin,
                    time=desired_time,
                    last_active_at=desired_last_active_at or existing["last_active_at"],
                )
            )
            continue

        if desired_project is None:
            continue
        timestamp = desired_last_active_at or datetime.now(tz=ZoneInfo(tz_name))
        users_to_insert.append(
            {
                "rfid": None,
                "chave": chave,
                "nome": desired_name,
                "projeto": desired_project,
                "placa": None,
                "end_rua": None,
                "zip": None,
                "cargo": desired_cargo,
                "email": desired_email,
                "local": desired_local,
                "checkin": desired_checkin,
                "time": desired_time,
                "last_active_at": timestamp,
                "inactivity_days": 0,
            }
        )

    if users_to_insert:
        bind.execute(users.insert(), users_to_insert)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("email")
        batch_op.drop_column("cargo")

    op.drop_table("checkinghistory")
