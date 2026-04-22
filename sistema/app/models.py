from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("name", name="uq_projects_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class Workplace(Base):
    __tablename__ = "workplaces"
    __table_args__ = (UniqueConstraint("workplace", name="uq_workplaces_workplace"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workplace: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    zip: Mapped[str] = mapped_column(String(10), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rfid: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    chave: Mapped[str] = mapped_column(String(4), nullable=False, unique=True)
    senha: Mapped[str | None] = mapped_column(String(255), nullable=True)
    perfil: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nome: Mapped[str] = mapped_column(String(180), nullable=False)
    projeto: Mapped[str] = mapped_column(String(120), nullable=False)
    workplace: Mapped[str | None] = mapped_column(String(120), ForeignKey("workplaces.workplace"), nullable=True)
    placa: Mapped[str | None] = mapped_column(String(9), ForeignKey("vehicles.placa"), nullable=True)
    end_rua: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zip: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cargo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
        CheckConstraint("tolerance >= 0 AND tolerance <= 240", name="ck_vehicles_tolerance_range"),
        CheckConstraint("service_scope IN ('regular', 'weekend', 'extra')", name="ck_vehicles_service_scope_allowed"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    placa: Mapped[str] = mapped_column(String(9), nullable=False)
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    color: Mapped[str | None] = mapped_column(String(40), nullable=True)
    lugares: Mapped[int] = mapped_column(Integer, nullable=False)
    tolerance: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    service_scope: Mapped[str] = mapped_column(String(16), nullable=False, default="regular")


class TransportVehicleSchedule(Base):
    __tablename__ = "transport_vehicle_schedules"
    __table_args__ = (
        CheckConstraint("service_scope IN ('regular', 'weekend', 'extra')", name="ck_transport_vehicle_schedules_scope_allowed"),
        CheckConstraint(
            "route_kind IN ('home_to_work', 'work_to_home')",
            name="ck_transport_vehicle_schedules_route_allowed",
        ),
        CheckConstraint(
            "recurrence_kind IN ('weekday', 'matching_weekday', 'single_date')",
            name="ck_transport_vehicle_schedules_recurrence_allowed",
        ),
        CheckConstraint("weekday IS NULL OR (weekday >= 0 AND weekday <= 6)", name="ck_transport_vehicle_schedules_weekday_range"),
        CheckConstraint(
            "(recurrence_kind = 'single_date' AND service_date IS NOT NULL) OR (recurrence_kind != 'single_date')",
            name="ck_transport_vehicle_schedules_single_date_required",
        ),
        CheckConstraint(
            "(recurrence_kind = 'matching_weekday' AND weekday IS NOT NULL) OR (recurrence_kind != 'matching_weekday')",
            name="ck_transport_vehicle_schedules_matching_weekday_required",
        ),
        CheckConstraint(
            "(recurrence_kind = 'weekday' AND weekday IS NULL) OR (recurrence_kind != 'weekday')",
            name="ck_transport_vehicle_schedules_weekday_kind_shape",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    service_scope: Mapped[str] = mapped_column(String(16), nullable=False)
    route_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    recurrence_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    service_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    weekday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    departure_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TransportVehicleScheduleException(Base):
    __tablename__ = "transport_vehicle_schedule_exceptions"
    __table_args__ = (
        UniqueConstraint("vehicle_schedule_id", "service_date", name="uq_transport_vehicle_schedule_exceptions_schedule_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_schedule_id: Mapped[int] = mapped_column(ForeignKey("transport_vehicle_schedules.id"), nullable=False)
    service_date: Mapped[date] = mapped_column(Date(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TransportDailySetting(Base):
    __tablename__ = "transport_daily_settings"
    __table_args__ = (UniqueConstraint("service_date", name="uq_transport_daily_settings_service_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_date: Mapped[date] = mapped_column(Date(), nullable=False)
    work_to_home_time: Mapped[str] = mapped_column(String(5), nullable=False, default="16:45")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TransportRequest(Base):
    __tablename__ = "transport_requests"
    __table_args__ = (
        CheckConstraint("request_kind IN ('regular', 'weekend', 'extra')", name="ck_transport_requests_kind_allowed"),
        CheckConstraint(
            "recurrence_kind IN ('weekday', 'weekend', 'single_date')",
            name="ck_transport_requests_recurrence_allowed",
        ),
        CheckConstraint("status IN ('active', 'cancelled')", name="ck_transport_requests_status_allowed"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    request_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    recurrence_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_time: Mapped[str] = mapped_column(String(5), nullable=False)
    selected_weekdays_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    single_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    created_via: Mapped[str] = mapped_column(String(20), nullable=False, default="admin")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TransportAssignment(Base):
    __tablename__ = "transport_assignments"
    __table_args__ = (
        UniqueConstraint("request_id", "service_date", "route_kind", name="uq_transport_assignments_request_date_route"),
        CheckConstraint(
            "route_kind IN ('home_to_work', 'work_to_home')",
            name="ck_transport_assignments_route_allowed",
        ),
        CheckConstraint(
            "status IN ('confirmed', 'rejected', 'cancelled', 'pending')",
            name="ck_transport_assignments_status_allowed",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("transport_requests.id"), nullable=False)
    service_date: Mapped[date] = mapped_column(Date(), nullable=False)
    route_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="home_to_work")
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="confirmed")
    response_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acknowledged_by_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    project: Mapped[str] = mapped_column(String(120), nullable=True)
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
    projeto: Mapped[str] = mapped_column(String(120), nullable=False)
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
    transport_work_to_home_time: Mapped[str] = mapped_column(String(5), nullable=False, default="16:45")
    transport_last_update_time: Mapped[str] = mapped_column(String(5), nullable=False, default="16:00")
    transport_default_car_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    transport_default_minivan_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    transport_default_van_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    transport_default_bus_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
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
    projeto: Mapped[str | None] = mapped_column(String(120), nullable=True)
    local: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ontime: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(80), nullable=True)


class CheckingHistory(Base):
    __tablename__ = "checkinghistory"
    __table_args__ = (
        UniqueConstraint(
            "chave",
            "atividade",
            "projeto",
            "time",
            "informe",
            name="uq_checkinghistory_event",
        ),
        CheckConstraint("atividade IN ('check-in', 'check-out')", name="ck_checkinghistory_atividade_allowed"),
        CheckConstraint("informe IN ('normal', 'retroativo')", name="ck_checkinghistory_informe_allowed"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chave: Mapped[str] = mapped_column(String(4), nullable=False)
    atividade: Mapped[str] = mapped_column(String(16), nullable=False)
    projeto: Mapped[str] = mapped_column(String(120), nullable=False)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    informe: Mapped[str] = mapped_column(String(16), nullable=False)


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
