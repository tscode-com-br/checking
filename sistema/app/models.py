from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    rfid: Mapped[str] = mapped_column(String(64), primary_key=True)
    chave: Mapped[str] = mapped_column(String(4), nullable=False)
    nome: Mapped[str] = mapped_column(String(180), nullable=False)
    projeto: Mapped[str] = mapped_column(String(3), nullable=False)
    local: Mapped[str | None] = mapped_column(String(40), nullable=True)
    checkin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PendingRegistration(Base):
    __tablename__ = "pending_registrations"
    __table_args__ = (UniqueConstraint("rfid", name="uq_pending_rfid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rfid: Mapped[str] = mapped_column(String(64), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class CheckEvent(Base):
    __tablename__ = "check_events"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_check_events_idempotency_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="system")
    rfid: Mapped[str] = mapped_column(String(64), ForeignKey("users.rfid"), nullable=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    project: Mapped[str] = mapped_column(String(3), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    local: Mapped[str | None] = mapped_column(String(40), nullable=True)
    request_path: Mapped[str | None] = mapped_column(String(120), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DeviceHeartbeat(Base):
    __tablename__ = "device_heartbeats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(80), nullable=False)
    is_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
