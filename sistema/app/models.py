from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rfid: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    chave: Mapped[str] = mapped_column(String(4), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(180), nullable=False)
    projeto: Mapped[str] = mapped_column(String(3), nullable=False)
    placa: Mapped[str | None] = mapped_column(String(9), ForeignKey("vehicles.placa"), nullable=True)
    end_rua: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zip: Mapped[str | None] = mapped_column(String(10), nullable=True)
    local: Mapped[str | None] = mapped_column(String(40), nullable=True)
    checkin: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    inactivity_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint("placa", name="uq_vehicles_placa"),
        CheckConstraint("tipo IN ('carro', 'minivan', 'van', 'onibus')", name="ck_vehicles_tipo_allowed"),
        CheckConstraint("lugares >= 1 AND lugares <= 99", name="ck_vehicles_lugares_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    placa: Mapped[str] = mapped_column(String(9), nullable=False)
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    lugares: Mapped[int] = mapped_column(Integer, nullable=False)


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
    rfid: Mapped[str] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    project: Mapped[str] = mapped_column(String(3), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    local: Mapped[str | None] = mapped_column(String(40), nullable=True)
    request_path: Mapped[str | None] = mapped_column(String(120), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ontime: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DeviceHeartbeat(Base):
    __tablename__ = "device_heartbeats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(80), nullable=False)
    is_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FormsSubmission(Base):
    __tablename__ = "forms_submissions"
    __table_args__ = (UniqueConstraint("request_id", name="uq_forms_submissions_request_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(80), nullable=False)
    rfid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    chave: Mapped[str] = mapped_column(String(4), nullable=False)
    projeto: Mapped[str] = mapped_column(String(3), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    local: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ontime: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ManagedLocation(Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("local", name="uq_locations_local"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    local: Mapped[str] = mapped_column(String(40), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    coordinates_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    tolerance_meters: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MobileAppSettings(Base):
    __tablename__ = "mobile_app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    location_update_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    location_accuracy_threshold_meters: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    coordinate_update_frequency_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserSyncEvent(Base):
    __tablename__ = "user_sync_events"
    __table_args__ = (UniqueConstraint("source", "source_request_id", name="uq_user_sync_events_source_request_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    chave: Mapped[str] = mapped_column(String(4), nullable=False)
    rfid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    projeto: Mapped[str | None] = mapped_column(String(3), nullable=True)
    local: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ontime: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(80), nullable=True)


class AdminUser(Base):
    __tablename__ = "admin_users"
    __table_args__ = (UniqueConstraint("chave", name="uq_admin_users_chave"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chave: Mapped[str] = mapped_column(String(4), nullable=False)
    nome_completo: Mapped[str] = mapped_column(String(180), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requires_password_reset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by_admin_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_reset_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdminAccessRequest(Base):
    __tablename__ = "admin_access_requests"
    __table_args__ = (UniqueConstraint("chave", name="uq_admin_access_requests_chave"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chave: Mapped[str] = mapped_column(String(4), nullable=False)
    nome_completo: Mapped[str] = mapped_column(String(180), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
