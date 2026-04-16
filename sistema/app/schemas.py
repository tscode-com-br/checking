from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


def _normalize_optional_local(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).strip().split())
    if not normalized:
        return None
    if len(normalized) > 40:
        raise ValueError("O local deve ter no maximo 40 caracteres")
    return normalized


def _normalize_required_local(value: str) -> str:
    normalized = " ".join(str(value).strip().split())
    if len(normalized) < 2:
        raise ValueError("O local deve ter ao menos 2 caracteres")
    if len(normalized) > 40:
        raise ValueError("O local deve ter no maximo 40 caracteres")
    return normalized


def _normalize_required_label(value: str, field_name: str, *, max_length: int = 80) -> str:
    normalized = " ".join(str(value).strip().split())
    if len(normalized) < 2:
        raise ValueError(f"{field_name} deve ter ao menos 2 caracteres")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} deve ter no maximo {max_length} caracteres")
    return normalized


def _validate_latitude(value: float) -> float:
    if value < -90 or value > 90:
        raise ValueError("A latitude deve estar entre -90 e 90")
    return value


def _validate_longitude(value: float) -> float:
    if value < -180 or value > 180:
        raise ValueError("A longitude deve estar entre -180 e 180")
    return value


class HealthResponse(BaseModel):
    status: str
    app: str


class HeartbeatRequest(BaseModel):
    device_id: str = Field(min_length=2, max_length=80)
    shared_key: str


class ScanRequest(BaseModel):
    rfid: str = Field(min_length=4, max_length=64)
    local: str = Field(min_length=2, max_length=40)
    action: Literal["checkin", "checkout"]
    device_id: str = Field(min_length=2, max_length=80)
    request_id: str = Field(min_length=8, max_length=80)
    shared_key: str


class ScanResponse(BaseModel):
    outcome: Literal["submitted", "pending_registration", "invalid_key", "duplicate", "failed", "local_updated"]
    led: Literal["white", "orange_4s", "green_1s", "green_blink_3x_1s", "red", "red_2s", "red_blink_5x_1s"]
    message: str


class AdminUserUpsert(BaseModel):
    user_id: int | None = Field(default=None, ge=1)
    rfid: str | None = Field(default=None, min_length=4, max_length=64)
    nome: str = Field(min_length=3, max_length=180)
    chave: str = Field(min_length=4, max_length=4)
    projeto: Literal["P80", "P82", "P83"]

    @model_validator(mode="after")
    def validate_identity(self):
        if self.user_id is None and not self.rfid:
            raise ValueError("user_id or rfid is required")
        return self

    @field_validator("chave")
    @classmethod
    def validate_chave(cls, value: str) -> str:
        if not value.isalnum():
            raise ValueError("chave must be alphanumeric")
        return value.upper()


class LocationCoordinate(BaseModel):
    latitude: float
    longitude: float

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        return _validate_latitude(value)

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        return _validate_longitude(value)


class LocationRow(BaseModel):
    id: int
    local: str
    latitude: float
    longitude: float
    coordinates: list[LocationCoordinate]
    tolerance_meters: int


class AdminLocationsResponse(BaseModel):
    items: list[LocationRow]
    location_accuracy_threshold_meters: int = Field(ge=1, le=9999)


class AdminLocationUpsert(BaseModel):
    location_id: int | None = Field(default=None, ge=1)
    local: str
    latitude: float | None = None
    longitude: float | None = None
    coordinates: list[LocationCoordinate] | None = None
    tolerance_meters: int = Field(ge=1, le=9999)

    @model_validator(mode="before")
    @classmethod
    def normalize_coordinates_payload(cls, value):
        if not isinstance(value, dict):
            return value
        if value.get("coordinates") is not None:
            return value

        latitude = value.get("latitude")
        longitude = value.get("longitude")
        if latitude is None and longitude is None:
            return value

        normalized = dict(value)
        normalized["coordinates"] = [{"latitude": latitude, "longitude": longitude}]
        return normalized

    @field_validator("local", mode="before")
    @classmethod
    def validate_location_name(cls, value: str) -> str:
        return _normalize_required_local(value)

    @field_validator("latitude")
    @classmethod
    def validate_optional_latitude(cls, value: float | None) -> float | None:
        if value is None:
            return None
        return _validate_latitude(value)

    @field_validator("longitude")
    @classmethod
    def validate_optional_longitude(cls, value: float | None) -> float | None:
        if value is None:
            return None
        return _validate_longitude(value)

    @model_validator(mode="after")
    def validate_coordinates(self):
        if not self.coordinates:
            raise ValueError("Informe ao menos uma coordenada para o local")
        return self


class AdminLocationSettingsUpdate(BaseModel):
    location_accuracy_threshold_meters: int = Field(ge=1, le=9999)


class AdminLoginRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    senha: str = Field(min_length=3, max_length=20)

    @field_validator("chave")
    @classmethod
    def validate_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized


class AdminAccessRequestCreate(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    nome_completo: str = Field(min_length=3, max_length=180)
    senha: str = Field(min_length=3, max_length=20)

    @field_validator("chave")
    @classmethod
    def validate_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized


class AdminPasswordResetRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)

    @field_validator("chave")
    @classmethod
    def validate_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized


class AdminPasswordSetRequest(BaseModel):
    nova_senha: str = Field(min_length=3, max_length=20)


class AdminIdentity(BaseModel):
    id: int
    chave: str
    nome_completo: str


class AdminSessionResponse(BaseModel):
    authenticated: bool
    admin: AdminIdentity | None = None
    message: str | None = None


class AdminManagementRow(BaseModel):
    id: int
    row_type: Literal["admin", "request"]
    chave: str
    nome: str
    status: Literal["active", "pending", "password_reset_requested"]
    status_label: str
    can_revoke: bool
    can_approve: bool
    can_reject: bool
    can_set_password: bool


class AdminActionResponse(BaseModel):
    ok: bool
    message: str


class AdminLocationSettingsResponse(AdminActionResponse):
    location_accuracy_threshold_meters: int = Field(ge=1, le=9999)


class UserRow(BaseModel):
    id: int
    rfid: Optional[str]
    nome: str
    chave: str
    projeto: str
    local: Optional[str]
    checkin: bool
    time: datetime
    assiduidade: Literal["Normal", "Retroativo"]


class AdminUserListRow(BaseModel):
    id: int
    rfid: Optional[str]
    nome: str
    chave: str
    projeto: str


class PendingRow(BaseModel):
    id: int
    rfid: str
    first_seen_at: datetime
    last_seen_at: datetime
    attempts: int


class EventRow(BaseModel):
    id: int
    source: str
    rfid: Optional[str]
    chave: Optional[str]
    device_id: Optional[str]
    local: Optional[str]
    action: str
    status: str
    message: str
    details: Optional[str]
    project: Optional[str]
    ontime: bool | None
    request_path: Optional[str]
    http_status: Optional[int]
    retry_count: int
    event_time: datetime


class InactiveUserRow(BaseModel):
    id: int
    rfid: Optional[str]
    nome: str
    chave: str
    projeto: str
    latest_action: Literal["checkin", "checkout"]
    latest_time: datetime
    inactivity_days: int


class EventArchiveRow(BaseModel):
    file_name: str
    period: str
    record_count: int
    size_bytes: int
    created_at: datetime


class EventArchiveListResponse(BaseModel):
    items: list[EventArchiveRow]
    total: int
    total_size_bytes: int
    page: int
    page_size: int
    total_pages: int
    query: str = ""


class EventArchiveCreateResponse(BaseModel):
    created: bool
    cleared_count: int
    archive: EventArchiveRow | None
    archives: EventArchiveListResponse


class MobileSyncRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    projeto: Literal["P80", "P82", "P83"]
    action: Literal["checkin", "checkout"]
    local: str | None = None
    event_time: datetime
    client_event_id: str = Field(min_length=8, max_length=80)

    @field_validator("chave")
    @classmethod
    def validate_mobile_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("local", mode="before")
    @classmethod
    def validate_mobile_sync_local(cls, value: str | None) -> str | None:
        return _normalize_optional_local(value)


class MobileSubmitRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    projeto: Literal["P80", "P82", "P83"]
    action: Literal["checkin", "checkout"]
    local: str | None = None
    event_time: datetime
    client_event_id: str = Field(min_length=8, max_length=80)

    @field_validator("chave")
    @classmethod
    def validate_mobile_submit_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("local", mode="before")
    @classmethod
    def validate_mobile_submit_local(cls, value: str | None) -> str | None:
        return _normalize_optional_local(value)


class MobileFormsSubmitRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    projeto: Literal["P80", "P82", "P83"]
    action: Literal["checkin", "checkout"]
    local: str | None = None
    informe: Literal["normal", "retroativo"]
    event_time: datetime
    client_event_id: str = Field(min_length=8, max_length=80)

    @field_validator("chave")
    @classmethod
    def validate_mobile_forms_submit_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("informe", mode="before")
    @classmethod
    def validate_informe(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in {"normal", "retroativo"}:
            raise ValueError("Informe deve ser 'Normal' ou 'Retroativo'")
        return normalized

    @field_validator("local", mode="before")
    @classmethod
    def validate_mobile_forms_submit_local(cls, value: str | None) -> str | None:
        return _normalize_optional_local(value)


class WebCheckSubmitRequest(MobileFormsSubmitRequest):
    pass


class WebLocationMatchRequest(BaseModel):
    latitude: float
    longitude: float
    accuracy_meters: float | None = Field(default=None, ge=0)

    @field_validator("latitude")
    @classmethod
    def validate_web_location_latitude(cls, value: float) -> float:
        return _validate_latitude(value)

    @field_validator("longitude")
    @classmethod
    def validate_web_location_longitude(cls, value: float) -> float:
        return _validate_longitude(value)


class WebLocationMatchResponse(BaseModel):
    matched: bool
    resolved_local: str | None = None
    label: str
    status: Literal[
        "matched",
        "accuracy_too_low",
        "not_in_known_location",
        "outside_workplace",
        "no_known_locations",
    ]
    message: str
    accuracy_meters: float | None = Field(default=None, ge=0)
    accuracy_threshold_meters: int = Field(ge=1, le=9999)
    nearest_workplace_distance_meters: float | None = Field(default=None, ge=0)


class WebCheckHistoryResponse(BaseModel):
    found: bool
    chave: str
    last_checkin_at: datetime | None = None
    last_checkout_at: datetime | None = None


class WebLocationOptionsResponse(BaseModel):
    items: list[str]


class MobileSyncStateResponse(BaseModel):
    found: bool
    chave: str
    nome: str | None = None
    projeto: str | None = None
    current_action: Literal["checkin", "checkout"] | None = None
    current_event_time: datetime | None = None
    current_local: str | None = None
    last_checkin_at: datetime | None = None
    last_checkout_at: datetime | None = None


class MobileSyncResponse(BaseModel):
    ok: bool
    duplicate: bool = False
    message: str
    state: MobileSyncStateResponse


class MobileSubmitResponse(BaseModel):
    ok: bool
    duplicate: bool = False
    queued_forms: bool = True
    message: str
    state: MobileSyncStateResponse


class WebCheckSubmitResponse(MobileSubmitResponse):
    pass


class MobileLocationRow(BaseModel):
    id: int
    local: str
    latitude: float
    longitude: float
    coordinates: list[LocationCoordinate]
    tolerance_meters: int
    updated_at: datetime


class MobileLocationsResponse(BaseModel):
    items: list[MobileLocationRow]
    synced_at: datetime
    location_accuracy_threshold_meters: int = Field(ge=1, le=9999)
