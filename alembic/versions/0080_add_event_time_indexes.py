"""add event_time indexes to check_events and user_sync_events

Revision ID: 0080_add_event_time_indexes
Revises: 0079_add_pending_user_registrations
Create Date: 2026-07-06

As telas de presenca do admin (/api/admin/checkin|checkout) passaram a carregar apenas a janela
recente de eventos (``event_time >= corte``, ver PRESENCE_EVENT_LOOKBACK_HOURS em routers/admin.py).
Sem indice em ``event_time``, esse corte vira seq scan das tabelas de historico, que crescem sem
limite. Os nomes seguem o padrao do SQLAlchemy para ``index=True`` (``ix_<tabela>_<coluna>``),
mantendo models.py e migration em sincronia.
"""
from __future__ import annotations

from alembic import op

revision = "0080_add_event_time_indexes"
down_revision = "0079_add_pending_user_registrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_check_events_event_time", "check_events", ["event_time"])
    op.create_index("ix_user_sync_events_event_time", "user_sync_events", ["event_time"])


def downgrade() -> None:
    op.drop_index("ix_user_sync_events_event_time", table_name="user_sync_events")
    op.drop_index("ix_check_events_event_time", table_name="check_events")
