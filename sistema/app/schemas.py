import re
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from .models import ManagedLocation
from .services.admin_project_scope import normalize_admin_monitored_project_names
from .services.location_audit import audit_managed_location
from .services.managed_locations import dump_location_coordinates
from .services.project_catalog import (
    normalize_optional_project_country_code,
    normalize_project_country_name,
    normalize_project_country_payload,
    normalize_project_name,
    normalize_project_timezone_name,
)
from .services.user_profiles import normalize_person_name


PLATE_MAX_LENGTH = 15
PLATE_ALLOWED_PATTERN = re.compile(r"^[A-Z0-9.-]+$")
TRANSPORT_CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z0-9]{2,12}$")
TRANSPORT_PRICE_RATE_UNITS = {"hour", "day", "week", "month"}


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


def _normalize_optional_label(value: str | None, field_name: str, *, max_length: int = 80) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).strip().split())
    if not normalized:
        return None
    return _normalize_required_label(normalized, field_name, max_length=max_length)


def _normalize_optional_text(value: str | None, field_name: str, *, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).strip().split())
    if not normalized:
        return None
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} deve ter no maximo {max_length} caracteres")
    return normalized


def _normalize_optional_compact_text(value: str | None, field_name: str, *, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} deve ter no maximo {max_length} caracteres")
    return normalized


def _normalize_required_compact_text(value: str, field_name: str, *, max_length: int) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} e obrigatorio")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} deve ter no maximo {max_length} caracteres")
    return normalized


def _normalize_optional_plate(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper().replace(" ", "")
    if not normalized:
        return None
    if len(normalized) > PLATE_MAX_LENGTH:
        raise ValueError(f"A placa deve ter no maximo {PLATE_MAX_LENGTH} caracteres")
    if not PLATE_ALLOWED_PATTERN.fullmatch(normalized):
        raise ValueError("A placa deve conter apenas letras, numeros, '-' e '.'")
    return normalized


def _validate_latitude(value: float) -> float:
    if value < -90 or value > 90:
        raise ValueError("A latitude deve estar entre -90 e 90")
    return value


def _validate_longitude(value: float) -> float:
    if value < -180 or value > 180:
        raise ValueError("A longitude deve estar entre -180 e 180")
    return value


def _build_transient_location_for_admin_validation(
    *,
    local: str,
    coordinates: list["LocationCoordinate"],
    tolerance_meters: int,
) -> ManagedLocation:
    primary_coordinate = coordinates[0]
    timestamp = datetime.now()
    return ManagedLocation(
        id=0,
        local=local,
        latitude=primary_coordinate.latitude,
        longitude=primary_coordinate.longitude,
        coordinates_json=dump_location_coordinates(
            {
                "latitude": coordinate.latitude,
                "longitude": coordinate.longitude,
            }
            for coordinate in coordinates
        ),
        projects_json='[]',
        tolerance_meters=tolerance_meters,
        created_at=timestamp,
        updated_at=timestamp,
    )


def _validate_admin_location_polygon_payload(
    *,
    local: str,
    coordinates: list["LocationCoordinate"],
    tolerance_meters: int,
) -> None:
    audited_location = audit_managed_location(
        _build_transient_location_for_admin_validation(
            local=local,
            coordinates=coordinates,
            tolerance_meters=tolerance_meters,
        )
    )

    issue_codes = {issue.code for issue in audited_location.issues}
    if "redundant_closing_vertex" in issue_codes:
        raise ValueError("Nao repita a primeira coordenada no final; o poligono e fechado automaticamente")
    if "too_few_coordinates" in issue_codes or "too_few_unique_coordinates" in issue_codes:
        raise ValueError("Informe ao menos 3 coordenadas distintas para formar o poligono do local")
    if "duplicate_coordinates" in issue_codes:
        raise ValueError("Remova coordenadas duplicadas antes de salvar a localizacao")
    if "self_intersection" in issue_codes or "potential_vertex_order_problem" in issue_codes:
        raise ValueError("A localizacao precisa formar um poligono valido sem auto-interseccao")
    if "zero_area_polygon" in issue_codes:
        raise ValueError("A localizacao precisa formar uma area valida; os vertices atuais geram area zero")


def _normalize_transport_time(value: str) -> str:
    normalized = str(value or "").strip()
    try:
        parsed = datetime.strptime(normalized, "%H:%M")
    except ValueError as exc:
        raise ValueError("O horario deve estar no formato hh:mm") from exc
    return parsed.strftime("%H:%M")


def _normalize_transport_currency_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"\s+", "", str(value).upper())
    if not normalized:
        return None
    if not TRANSPORT_CURRENCY_CODE_PATTERN.fullmatch(normalized):
        raise ValueError("Currency code must contain 2 to 12 uppercase letters or digits.")
    return normalized


def _normalize_transport_price_rate_unit(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in TRANSPORT_PRICE_RATE_UNITS:
        raise ValueError("Billing unit must be one of: hour, day, week, month.")
    return normalized


def _normalize_optional_transport_time(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return _normalize_transport_time(normalized)


def _normalize_optional_integer_input(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _normalize_transport_weekday_list(value: object) -> list[int] | None:
    if value is None:
        return None
    if isinstance(value, str):
        raise ValueError("Os dias selecionados devem ser enviados como lista")
    if not isinstance(value, (list, tuple, set)):
        raise ValueError("Os dias selecionados devem ser enviados como lista")

    normalized: list[int] = []
    for item in value:
        if isinstance(item, bool):
            raise ValueError("Os dias selecionados devem conter numeros entre 0 e 6")
        try:
            weekday = int(item)
        except (TypeError, ValueError) as exc:
            raise ValueError("Os dias selecionados devem conter numeros entre 0 e 6") from exc
        if weekday < 0 or weekday > 6:
            raise ValueError("Os dias selecionados devem conter numeros entre 0 e 6")
        normalized.append(weekday)

    return sorted(dict.fromkeys(normalized))


_REGULAR_VEHICLE_WEEKDAY_FIELDS = (
    ("every_monday", 0),
    ("every_tuesday", 1),
    ("every_wednesday", 2),
    ("every_thursday", 3),
    ("every_friday", 4),
)


def _resolve_regular_vehicle_weekdays(source: object) -> list[int]:
    if isinstance(source, dict):
        return [
            weekday
            for field_name, weekday in _REGULAR_VEHICLE_WEEKDAY_FIELDS
            if bool(source.get(field_name))
        ]

    return [
        weekday
        for field_name, weekday in _REGULAR_VEHICLE_WEEKDAY_FIELDS
        if bool(getattr(source, field_name, False))
    ]


def _validate_web_password(value: str, field_name: str) -> str:
    password = str(value)
    if len(password) < 3 or len(password) > 10:
        raise ValueError(f"{field_name} deve ter entre 3 e 10 caracteres")
    if not password.strip():
        raise ValueError(f"{field_name} nao pode conter apenas espacos")
    return password


def _normalize_project_value(value: str) -> str:
    return normalize_project_name(value)


def _normalize_optional_project_metadata_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _normalize_admin_monitored_projects_value(value: object) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        raise ValueError("Os projetos monitorados devem ser enviados como lista")
    if not isinstance(value, (list, tuple, set)):
        raise ValueError("Os projetos monitorados devem ser enviados como lista")

    normalized = normalize_admin_monitored_project_names(value)
    if not normalized:
        raise ValueError("Selecione ao menos um projeto para o administrador.")
    return normalized


def _validate_monitored_projects_against_catalog(
    monitored_projects: list[str] | None,
    info: ValidationInfo,
) -> list[str] | None:
    if monitored_projects is None:
        return None

    context = info.context if isinstance(info.context, dict) else None
    allowed_project_names = context.get("allowed_project_names") if context else None
    if allowed_project_names is None:
        return monitored_projects

    allowed_projects = set(normalize_admin_monitored_project_names(allowed_project_names))
    invalid_projects = [project_name for project_name in monitored_projects if project_name not in allowed_projects]
    if invalid_projects:
        raise ValueError("Um ou mais projetos monitorados nao existem no catalogo atual")
    return monitored_projects


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
    perfil: int = Field(default=0, ge=0, le=999)
    projeto: str = Field(min_length=2, max_length=120)
    workplace: str | None = Field(default=None, max_length=120)
    vehicle_id: int | None = Field(default=None, ge=1)
    placa: str | None = Field(default=None, max_length=PLATE_MAX_LENGTH)
    end_rua: str | None = Field(default=None, max_length=255)
    zip: str | None = Field(default=None, max_length=10)
    cargo: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)

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

    @field_validator("rfid", mode="before")
    @classmethod
    def validate_rfid(cls, value: str | None) -> str | None:
        return _normalize_optional_compact_text(value, "O RFID", max_length=64)

    @field_validator("placa", mode="before")
    @classmethod
    def validate_placa(cls, value: str | None) -> str | None:
        return _normalize_optional_plate(value)

    @field_validator("workplace", mode="before")
    @classmethod
    def validate_workplace(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "O workplace", max_length=120)

    @field_validator("end_rua", mode="before")
    @classmethod
    def validate_end_rua(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "O endereco", max_length=255)

    @field_validator("zip", mode="before")
    @classmethod
    def validate_zip(cls, value: str | None) -> str | None:
        return _normalize_optional_compact_text(value, "O ZIP code", max_length=10)

    @field_validator("cargo", mode="before")
    @classmethod
    def validate_cargo(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "O cargo", max_length=255)

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_compact_text(value, "O email", max_length=255)
        return normalized.lower() if normalized is not None else None

    @field_validator("projeto", mode="before")
    @classmethod
    def validate_projeto(cls, value: str) -> str:
        return _normalize_project_value(value)


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
    projects: list[str] = Field(default_factory=list)
    tolerance_meters: int


class AdminLocationsResponse(BaseModel):
    items: list[LocationRow]
    location_accuracy_threshold_meters: int = Field(ge=1, le=9999)


class AdminProjectMinimumCheckoutDistanceRow(BaseModel):
    project_name: str
    minimum_checkout_distance_meters: int = Field(ge=1, le=999999)


class AdminProjectMinimumCheckoutDistanceListResponse(BaseModel):
    items: list[AdminProjectMinimumCheckoutDistanceRow] = Field(default_factory=list)


class AdminProjectMinimumCheckoutDistanceUpdateRow(BaseModel):
    project_name: str = Field(min_length=2, max_length=120)
    minimum_checkout_distance_meters: int = Field(ge=1, le=999999)

    @field_validator("project_name", mode="before")
    @classmethod
    def validate_project_name(cls, value: str) -> str:
        return _normalize_project_value(value)


class AdminProjectMinimumCheckoutDistanceUpdate(BaseModel):
    items: list[AdminProjectMinimumCheckoutDistanceUpdateRow] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_projects(self):
        project_names = [item.project_name for item in self.items]
        if len(project_names) != len(set(project_names)):
            raise ValueError("Nao e permitido repetir o mesmo projeto na mesma salvacao.")
        return self


class LocationAuditIssueRow(BaseModel):
    code: str
    severity: Literal["error", "warning", "info"]
    message: str


class LocationAuditRowResponse(BaseModel):
    location_id: int
    local: str
    projects: list[str] = Field(default_factory=list)
    is_checkout_zone: bool
    tolerance_meters: int
    coordinate_count: int
    effective_vertex_count: int
    unique_coordinate_count: int
    polygon_area_square_meters: float | None
    has_errors: bool
    has_warnings: bool
    needs_manual_review: bool
    issues: list[LocationAuditIssueRow] = Field(default_factory=list)


class LocationAuditSummaryResponse(BaseModel):
    total_locations: int
    checkout_zone_locations: int
    valid_polygon_locations: int
    locations_with_errors: int
    locations_with_warnings_only: int
    locations_without_issues: int
    locations_requiring_manual_review: int
    issue_counts: dict[str, int] = Field(default_factory=dict)


class AdminLocationAuditResponse(BaseModel):
    summary: LocationAuditSummaryResponse
    rows: list[LocationAuditRowResponse] = Field(default_factory=list)


class AdminLocationUpsert(BaseModel):
    location_id: int | None = Field(default=None, ge=1)
    local: str
    latitude: float | None = None
    longitude: float | None = None
    coordinates: list[LocationCoordinate] | None = None
    projects: list[str] = Field(min_length=1)
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

    @field_validator("projects", mode="before")
    @classmethod
    def validate_location_projects(cls, value: object) -> list[str]:
        if value is None:
            raise ValueError("Selecione ao menos um projeto para a localização")
        if isinstance(value, str):
            raw_items = [value]
        elif isinstance(value, (list, tuple, set)):
            raw_items = list(value)
        else:
            raise ValueError("Os projetos da localização devem ser enviados como lista")

        normalized: list[str] = []
        seen: set[str] = set()
        for item in raw_items:
            project_name = _normalize_project_value(str(item))
            if project_name in seen:
                continue
            seen.add(project_name)
            normalized.append(project_name)

        if not normalized:
            raise ValueError("Selecione ao menos um projeto para a localização")
        return normalized

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
            raise ValueError("Informe ao menos 3 coordenadas distintas para formar o poligono do local")

        _validate_admin_location_polygon_payload(
            local=self.local,
            coordinates=self.coordinates,
            tolerance_meters=self.tolerance_meters,
        )
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


class AdminSelfAccessStatusResponse(BaseModel):
    found: bool
    chave: str
    has_password: bool
    is_admin: bool
    has_pending_request: bool
    message: str


class AdminSelfAccessRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    nome_completo: str | None = Field(default=None, min_length=3, max_length=180)
    projeto: str | None = Field(default=None, min_length=2, max_length=120)
    senha: str | None = Field(default=None, min_length=3, max_length=10)
    confirmar_senha: str | None = Field(default=None, min_length=3, max_length=10)

    @field_validator("chave")
    @classmethod
    def validate_self_access_request_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("nome_completo", mode="before")
    @classmethod
    def validate_self_access_request_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_person_name(str(value))

    @field_validator("projeto", mode="before")
    @classmethod
    def validate_self_access_request_project(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_project_value(value)

    @field_validator("senha", "confirmar_senha", mode="before")
    @classmethod
    def validate_self_access_request_password(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_web_password(value, "A senha")

    @model_validator(mode="after")
    def validate_self_access_request_password_confirmation(self):
        password_provided = self.senha is not None
        confirmation_provided = self.confirmar_senha is not None
        if password_provided != confirmation_provided:
            raise ValueError("Informe e confirme a senha")
        if self.senha is not None and self.confirmar_senha is not None and self.senha != self.confirmar_senha:
            raise ValueError("A confirmacao de senha nao confere")
        return self


class AdminProfileUpdateRequest(BaseModel):
    perfil: int = Field(ge=0, le=999)
    monitored_projects: list[str] | None = None

    @field_validator("perfil", mode="before")
    @classmethod
    def validate_admin_profile_value(cls, value: int | str | None) -> int:
        return max(0, int(value or 0))

    @field_validator("monitored_projects", mode="before")
    @classmethod
    def validate_admin_monitored_projects(cls, value: object) -> list[str] | None:
        return _normalize_admin_monitored_projects_value(value)

    @field_validator("monitored_projects")
    @classmethod
    def validate_admin_monitored_projects_against_catalog(
        cls,
        value: list[str] | None,
        info: ValidationInfo,
    ) -> list[str] | None:
        return _validate_monitored_projects_against_catalog(value, info)


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


class AdminSelfPasswordVerifyRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    senha_atual: str = Field(min_length=3, max_length=20)

    @field_validator("chave")
    @classmethod
    def validate_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("senha_atual")
    @classmethod
    def validate_current_password(cls, value: str) -> str:
        password = str(value)
        if len(password) < 3 or len(password) > 20:
            raise ValueError("A senha atual deve ter entre 3 e 20 caracteres")
        if not password.strip():
            raise ValueError("A senha atual nao pode conter apenas espacos")
        return password


class AdminSelfPasswordChangeRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    senha_atual: str = Field(min_length=3, max_length=20)
    nova_senha: str = Field(min_length=3, max_length=10)
    confirmar_senha: str = Field(min_length=3, max_length=10)

    @field_validator("chave")
    @classmethod
    def validate_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("senha_atual")
    @classmethod
    def validate_current_password(cls, value: str) -> str:
        password = str(value)
        if len(password) < 3 or len(password) > 20:
            raise ValueError("A senha atual deve ter entre 3 e 20 caracteres")
        if not password.strip():
            raise ValueError("A senha atual nao pode conter apenas espacos")
        return password

    @field_validator("nova_senha")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _validate_web_password(value, "A nova senha")

    @field_validator("confirmar_senha")
    @classmethod
    def validate_confirmation_password(cls, value: str) -> str:
        return _validate_web_password(value, "A confirmacao da senha")

    @model_validator(mode="after")
    def validate_password_change(self):
        if self.nova_senha == self.senha_atual:
            raise ValueError("A nova senha deve ser diferente da senha atual")
        if self.confirmar_senha != self.nova_senha:
            raise ValueError("A confirmacao da senha deve ser identica a nova senha")
        return self


class AdminIdentity(BaseModel):
    id: int
    chave: str
    nome_completo: str
    perfil: int
    can_view_activity_time: bool
    access_scope: Literal["limited", "full"]
    allowed_tabs: list[Literal["checkin", "checkout", "forms", "inactive", "cadastro", "relatorios", "eventos", "banco-dados"]] = Field(default_factory=list)


class AdminSessionResponse(BaseModel):
    authenticated: bool
    admin: AdminIdentity | None = None
    message: str | None = None


class AdminManagementRow(BaseModel):
    id: int
    row_type: Literal["admin", "request"]
    chave: str
    nome: str
    perfil: int | None = None
    monitored_projects: list[str] = Field(default_factory=list)
    status: Literal["active", "pending", "password_reset_requested"]
    status_label: str
    can_revoke: bool
    can_approve: bool
    can_reject: bool
    can_set_password: bool

    @field_validator("monitored_projects", mode="before")
    @classmethod
    def validate_management_row_monitored_projects(cls, value: object) -> list[str]:
        normalized = _normalize_admin_monitored_projects_value(value)
        return normalized or []

    @field_validator("monitored_projects")
    @classmethod
    def validate_management_row_monitored_projects_against_catalog(
        cls,
        value: list[str],
        info: ValidationInfo,
    ) -> list[str]:
        validated = _validate_monitored_projects_against_catalog(value, info)
        return validated or []


class TransportIdentity(BaseModel):
    id: int
    chave: str
    nome_completo: str
    perfil: int


class TransportAuthVerifyRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    senha: str = Field(min_length=1, max_length=255)

    @field_validator("chave")
    @classmethod
    def validate_transport_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized


class TransportSessionResponse(BaseModel):
    authenticated: bool
    user: TransportIdentity | None = None
    message: str | None = None


class AdminActionResponse(BaseModel):
    ok: bool
    message: str


class AdminProjectMinimumCheckoutDistanceSaveResponse(AdminActionResponse):
    items: list[AdminProjectMinimumCheckoutDistanceRow] = Field(default_factory=list)


class AdminPasswordVerifyResponse(BaseModel):
    ok: bool
    valid: bool
    message: str


class ProjectRow(BaseModel):
    id: int
    name: str
    country_code: str
    country_name: str
    timezone_name: str
    timezone_label: str
    address: str
    zip_code: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    country_name: str | None = Field(default=None, min_length=2, max_length=80)
    timezone_name: str | None = Field(default=None, min_length=1, max_length=64)
    address: str = Field(default="", max_length=255)
    zip_code: str = Field(default="", max_length=32)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _normalize_project_value(value)

    @field_validator("country_code", mode="before")
    @classmethod
    def validate_country_code(cls, value: str | None) -> str | None:
        return normalize_optional_project_country_code(value)

    @field_validator("country_name", mode="before")
    @classmethod
    def validate_country_name(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        return normalize_project_country_name(value)

    @field_validator("timezone_name", mode="before")
    @classmethod
    def validate_timezone_name(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        return normalize_project_timezone_name(value)

    @field_validator("address", "zip_code", mode="before")
    @classmethod
    def validate_optional_metadata_text(cls, value: object) -> str:
        return _normalize_optional_project_metadata_text(value)

    @model_validator(mode="after")
    def normalize_country_payload(self):
        normalized = normalize_project_country_payload(
            country_code=self.country_code,
            country_name=self.country_name,
            timezone_name=self.timezone_name,
        )
        self.country_code = normalized["country_code"]
        self.country_name = normalized["country_name"]
        self.timezone_name = normalized["timezone_name"]
        return self


class ProjectUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    country_name: str | None = Field(default=None, min_length=2, max_length=80)
    timezone_name: str | None = Field(default=None, min_length=1, max_length=64)
    address: str = Field(default="", max_length=255)
    zip_code: str = Field(default="", max_length=32)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _normalize_project_value(value)

    @field_validator("country_code", mode="before")
    @classmethod
    def validate_country_code(cls, value: str | None) -> str | None:
        return normalize_optional_project_country_code(value)

    @field_validator("country_name", mode="before")
    @classmethod
    def validate_country_name(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        return normalize_project_country_name(value)

    @field_validator("timezone_name", mode="before")
    @classmethod
    def validate_timezone_name(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        return normalize_project_timezone_name(value)

    @field_validator("address", "zip_code", mode="before")
    @classmethod
    def validate_optional_metadata_text(cls, value: object) -> str:
        return _normalize_optional_project_metadata_text(value)

    @model_validator(mode="after")
    def normalize_country_payload(self):
        normalized = normalize_project_country_payload(
            country_code=self.country_code,
            country_name=self.country_name,
            timezone_name=self.timezone_name,
        )
        self.country_code = normalized["country_code"]
        self.country_name = normalized["country_name"]
        self.timezone_name = normalized["timezone_name"]
        return self


class AdminLocationSettingsResponse(AdminActionResponse):
    location_accuracy_threshold_meters: int = Field(ge=1, le=9999)


class UserRow(BaseModel):
    id: int
    rfid: Optional[str]
    nome: str
    chave: str
    projeto: str
    timezone_name: str
    timezone_label: str
    local: Optional[str]
    checkin: bool
    time: datetime | None = None
    activity_date_label: str
    activity_time_label: str | None = None
    activity_day_key: str
    assiduidade: Literal["Normal", "Retroativo"]


class ProviderFormRow(BaseModel):
    recebimento: datetime | None = None
    recebimento_date_label: str
    recebimento_time_label: str | None = None
    chave: str
    nome: str
    projeto: str
    timezone_name: str
    timezone_label: str
    atividade: Literal["check-in", "check-out"]
    informe: Literal["normal", "retroativo"]
    data: str
    hora: str | None = None


class ReportPersonRow(BaseModel):
    id: int
    rfid: Optional[str]
    nome: str
    chave: str
    projeto: str
    timezone_name: str
    timezone_label: str


class ReportEventRow(BaseModel):
    id: int
    source: str
    source_label: str
    action: Literal["checkin", "checkout"]
    action_label: str
    projeto: str
    local: Optional[str]
    local_label: str
    ontime: bool
    assiduidade: Literal["Normal", "Retroativo"]
    event_time: datetime | None = None
    event_time_label: str | None = None
    timezone_name: str
    timezone_label: str
    event_date: str


class ReportEventsResponse(BaseModel):
    person: ReportPersonRow
    events: list[ReportEventRow] = Field(default_factory=list)


class AdminUserListRow(BaseModel):
    id: int
    rfid: Optional[str]
    nome: str
    chave: str
    perfil: int = 0
    projeto: str
    vehicle_id: Optional[int] = None
    workplace: Optional[str] = None
    placa: Optional[str] = None
    end_rua: Optional[str] = None
    zip: Optional[str] = None
    cargo: Optional[str] = None
    email: Optional[str] = None


class TransportWorkplaceOperationalData(BaseModel):
    address: str = Field(min_length=3, max_length=255)
    zip: str = Field(min_length=1, max_length=10)
    country: str = Field(min_length=2, max_length=80)
    transport_group: str | None = Field(default=None, max_length=80)
    boarding_point: str | None = Field(default=None, max_length=255)
    transport_window_start: str | None = Field(default=None, min_length=5, max_length=5)
    transport_window_end: str | None = Field(default=None, min_length=5, max_length=5)
    service_restrictions: str | None = Field(default=None, max_length=500)
    transport_work_to_home_time: str | None = Field(default=None, min_length=5, max_length=5)

    @field_validator("address", mode="before")
    @classmethod
    def validate_workplace_address(cls, value: str) -> str:
        return _normalize_required_label(value, "O endereco", max_length=255)

    @field_validator("zip", mode="before")
    @classmethod
    def validate_workplace_zip(cls, value: str) -> str:
        return _normalize_required_compact_text(value, "O ZIP code", max_length=10)

    @field_validator("country", mode="before")
    @classmethod
    def validate_workplace_country(cls, value: str) -> str:
        return _normalize_required_label(value, "O pais", max_length=80)

    @field_validator("transport_group", mode="before")
    @classmethod
    def validate_transport_group(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "O grupo de transporte", max_length=80)

    @field_validator("boarding_point", mode="before")
    @classmethod
    def validate_boarding_point(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "O ponto operacional", max_length=255)

    @field_validator("transport_window_start", mode="before")
    @classmethod
    def validate_transport_window_start(cls, value: str | None) -> str | None:
        return _normalize_optional_transport_time(value)

    @field_validator("transport_window_end", mode="before")
    @classmethod
    def validate_transport_window_end(cls, value: str | None) -> str | None:
        return _normalize_optional_transport_time(value)

    @field_validator("service_restrictions", mode="before")
    @classmethod
    def validate_service_restrictions(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "As restricoes de atendimento", max_length=500)

    @field_validator("transport_work_to_home_time", mode="before")
    @classmethod
    def validate_transport_work_to_home_time(cls, value: str | None) -> str | None:
        return _normalize_optional_transport_time(value)

    @model_validator(mode="after")
    def validate_transport_window(self):
        if (self.transport_window_start is None) != (self.transport_window_end is None):
            raise ValueError("transport_window_start and transport_window_end must be provided together")
        if (
            self.transport_window_start is not None
            and self.transport_window_end is not None
            and self.transport_window_end <= self.transport_window_start
        ):
            raise ValueError("transport_window_end must be later than transport_window_start")
        return self


class TransportWorkplaceUpsert(TransportWorkplaceOperationalData):
    workplace: str = Field(min_length=2, max_length=120)

    @field_validator("workplace", mode="before")
    @classmethod
    def validate_workplace_name(cls, value: str) -> str:
        return _normalize_required_label(value, "O workplace", max_length=120)


class TransportWorkplaceUpdate(TransportWorkplaceOperationalData):
    pass


class WorkplaceRow(TransportWorkplaceOperationalData):
    id: int
    workplace: str


class TransportVehicleBaseData(BaseModel):
    placa: str | None = Field(default=None, max_length=PLATE_MAX_LENGTH)
    tipo: Literal["carro", "minivan", "van", "onibus"] | None = None
    color: str | None = Field(default=None, max_length=40)
    lugares: int | None = Field(default=None, ge=1, le=99)
    tolerance: int | None = Field(default=None, ge=0, le=240)

    @field_validator("placa", mode="before")
    @classmethod
    def validate_vehicle_plate(cls, value: str | None) -> str | None:
        return _normalize_optional_plate(value)

    @field_validator("tipo", mode="before")
    @classmethod
    def validate_vehicle_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip().lower()
        if not normalized:
            return None
        return normalized

    @field_validator("color", mode="before")
    @classmethod
    def validate_vehicle_color(cls, value: str | None) -> str | None:
        return _normalize_optional_label(value, "A cor", max_length=40)

    @field_validator("lugares", "tolerance", mode="before")
    @classmethod
    def normalize_optional_vehicle_integer_fields(cls, value: object) -> object:
        return _normalize_optional_integer_input(value)


class TransportVehicleCreate(TransportVehicleBaseData):
    service_scope: Literal["regular", "weekend", "extra"]
    service_date: date
    route_kind: Literal["home_to_work", "work_to_home"] | None = None
    departure_time: str | None = None
    every_weekend: bool = False
    every_saturday: bool = False
    every_sunday: bool = False
    every_monday: bool = False
    every_tuesday: bool = False
    every_wednesday: bool = False
    every_thursday: bool = False
    every_friday: bool = False

    @model_validator(mode="before")
    @classmethod
    def apply_regular_weekday_defaults(cls, value: object):
        if not isinstance(value, dict):
            return value

        if str(value.get("service_scope") or "").strip().lower() != "regular":
            return value

        if any(field_name in value for field_name, _ in _REGULAR_VEHICLE_WEEKDAY_FIELDS):
            return value

        normalized = dict(value)
        for field_name, _ in _REGULAR_VEHICLE_WEEKDAY_FIELDS:
            normalized[field_name] = True
        return normalized

    @model_validator(mode="after")
    def validate_scope_specific_rules(self):
        if self.service_scope == "weekend" and self.every_weekend and not (self.every_saturday or self.every_sunday):
            self.every_saturday = True
            self.every_sunday = True

        if self.service_scope == "extra":
            if self.route_kind is None:
                raise ValueError("route_kind is required for extra vehicles")
            if self.departure_time is None:
                raise ValueError("departure_time is required for extra vehicles")
            if self.every_weekend or self.every_saturday or self.every_sunday:
                raise ValueError("weekend persistence is not allowed for extra vehicles")
            if _resolve_regular_vehicle_weekdays(self):
                raise ValueError("regular persistence is not allowed for extra vehicles")
            return self

        if self.route_kind is not None:
            raise ValueError("route_kind is only allowed for extra vehicles")
        if self.departure_time is not None:
            raise ValueError("departure_time is only allowed for extra vehicles")

        if self.service_scope == "weekend":
            if _resolve_regular_vehicle_weekdays(self):
                raise ValueError("regular persistence is only allowed for regular vehicles")
            if not self.every_saturday and not self.every_sunday:
                raise ValueError(
                    "Weekend vehicles must be persistent. Select Every Saturday and/or Every Sunday, or create the vehicle in Extra Transport List"
                )
            return self

        if self.every_weekend or self.every_saturday or self.every_sunday:
            raise ValueError("weekend persistence is only allowed for weekend vehicles")
        if not _resolve_regular_vehicle_weekdays(self):
            raise ValueError("Regular vehicles must be persistent. Select at least one weekday")
        return self

    @field_validator("departure_time", mode="before")
    @classmethod
    def validate_vehicle_departure_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not str(value).strip():
            return None
        return _normalize_transport_time(value)


class TransportVehicleUpdate(TransportVehicleBaseData):
    pass


class TransportVehicleScheduleDefinition(BaseModel):
    service_scope: Literal["regular", "weekend", "extra"]
    route_kind: Literal["home_to_work", "work_to_home"]
    recurrence_kind: Literal["weekday", "matching_weekday", "single_date"]
    service_date: date | None = None
    weekday: int | None = Field(default=None, ge=0, le=6)
    departure_time: str | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def validate_schedule_definition(self):
        if self.recurrence_kind == "single_date":
            if self.service_date is None:
                raise ValueError("service_date is required for single-date schedules")
            if self.weekday is not None:
                raise ValueError("weekday is not allowed for single-date schedules")
        elif self.recurrence_kind == "matching_weekday":
            if self.weekday is None:
                raise ValueError("weekday is required for matching-weekday schedules")
        elif self.weekday is not None:
            raise ValueError("weekday is only allowed for matching-weekday schedules")

        if self.service_scope == "extra":
            if self.recurrence_kind != "single_date":
                raise ValueError("extra schedules must use single_date recurrence")
            if self.departure_time is None:
                raise ValueError("departure_time is required for extra schedules")
            return self

        if self.departure_time is not None:
            raise ValueError("departure_time is only allowed for extra schedules")
        return self

    @field_validator("departure_time", mode="before")
    @classmethod
    def validate_schedule_departure_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not str(value).strip():
            return None
        return _normalize_transport_time(value)


class TransportVehicleScheduleUpdate(TransportVehicleScheduleDefinition):
    pass


class TransportVehicleBaseRow(BaseModel):
    id: int
    placa: str | None = None
    tipo: str | None = None
    color: str | None = None
    lugares: int | None = None
    tolerance: int | None = None
    pending_fields: list[str] = Field(default_factory=list)
    is_ready_for_allocation: bool


class TransportVehicleRow(TransportVehicleBaseRow):
    schedule_id: int | None = None
    service_scope: str
    route_kind: Literal["home_to_work", "work_to_home"] | None = None
    departure_time: str | None = None


class TransportVehicleManagementRow(BaseModel):
    vehicle_id: int
    schedule_id: int | None = None
    placa: str | None = None
    tipo: str | None = None
    lugares: int | None = None
    assigned_count: int = Field(ge=0)
    service_date: date | None = None
    route_kind: Literal["home_to_work", "work_to_home"] | None = None
    departure_time: str | None = None
    pending_fields: list[str] = Field(default_factory=list)
    is_ready_for_allocation: bool


class TransportRequestCreate(BaseModel):
    user_id: int | None = Field(default=None, ge=1)
    chave: str | None = Field(default=None, min_length=4, max_length=4)
    request_kind: Literal["regular", "weekend", "extra"]
    requested_time: str = Field(min_length=5, max_length=5)
    requested_date: date | None = None
    selected_weekdays: list[int] | None = None

    @model_validator(mode="after")
    def validate_target_identity(self):
        if self.user_id is None and not self.chave:
            raise ValueError("user_id or chave is required")
        if self.request_kind == "extra" and self.requested_date is None:
            raise ValueError("requested_date is required for extra requests")
        if self.request_kind != "extra" and self.requested_date is not None:
            raise ValueError("requested_date is only allowed for extra requests")
        if self.request_kind == "extra":
            if self.selected_weekdays:
                raise ValueError("selected_weekdays is only allowed for recurring requests")
            return self

        if self.request_kind == "regular":
            if self.selected_weekdays is None:
                self.selected_weekdays = [0, 1, 2, 3, 4]
            if not self.selected_weekdays:
                raise ValueError("selected_weekdays is required for regular requests")
            if any(weekday >= 5 for weekday in self.selected_weekdays):
                raise ValueError("regular requests only allow weekdays from Monday to Friday")
            return self

        if self.selected_weekdays is None:
            self.selected_weekdays = [5, 6]
        if not self.selected_weekdays:
            raise ValueError("selected_weekdays is required for weekend requests")
        if any(weekday < 5 for weekday in self.selected_weekdays):
            raise ValueError("weekend requests only allow Saturday or Sunday")
        return self

    @field_validator("chave")
    @classmethod
    def validate_request_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("requested_time")
    @classmethod
    def validate_requested_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @field_validator("selected_weekdays", mode="before")
    @classmethod
    def validate_selected_weekdays(cls, value: object) -> list[int] | None:
        return _normalize_transport_weekday_list(value)


class TransportAssignmentUpsert(BaseModel):
    request_id: int = Field(ge=1)
    service_date: date
    route_kind: Literal["home_to_work", "work_to_home"]
    status: Literal["confirmed", "rejected", "cancelled", "pending"]
    vehicle_id: int | None = Field(default=None, ge=1)
    response_message: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_assignment(self):
        if self.status == "confirmed" and self.vehicle_id is None:
            raise ValueError("vehicle_id is required when status is confirmed")
        if self.status != "confirmed" and self.vehicle_id is not None:
            raise ValueError("vehicle_id is only allowed when status is confirmed")
        return self

    @field_validator("response_message", mode="before")
    @classmethod
    def validate_response_message(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "A resposta", max_length=255)


class TransportRequestReject(BaseModel):
    request_id: int = Field(ge=1)
    service_date: date
    route_kind: Literal["home_to_work", "work_to_home"]
    response_message: str | None = Field(default=None, max_length=255)

    @field_validator("response_message", mode="before")
    @classmethod
    def validate_reject_response_message(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "A resposta", max_length=255)


class TransportRequestRow(BaseModel):
    id: int
    request_kind: str
    requested_time: str
    service_date: date
    user_id: int
    chave: str
    nome: str
    projeto: str
    workplace: str | None = None
    end_rua: str | None = None
    zip: str | None = None
    assignment_status: Literal["pending", "confirmed", "rejected", "cancelled"]
    awareness_status: Literal["pending", "aware"] = "pending"
    assigned_vehicle: TransportVehicleRow | None = None
    response_message: str | None = None


class TransportDashboardResponse(BaseModel):
    selected_date: date
    selected_route: Literal["home_to_work", "work_to_home"]
    work_to_home_departure_time: str = Field(min_length=5, max_length=5)
    projects: list[ProjectRow]
    regular_requests: list[TransportRequestRow]
    weekend_requests: list[TransportRequestRow]
    extra_requests: list[TransportRequestRow]
    regular_vehicles: list[TransportVehicleRow]
    weekend_vehicles: list[TransportVehicleRow]
    extra_vehicles: list[TransportVehicleRow]
    regular_vehicle_registry: list[TransportVehicleManagementRow]
    weekend_vehicle_registry: list[TransportVehicleManagementRow]
    extra_vehicle_registry: list[TransportVehicleManagementRow]
    workplaces: list[WorkplaceRow]


class TransportOperationalSnapshot(BaseModel):
    snapshot_key: str = Field(min_length=1, max_length=180)
    service_date: date
    route_kind: Literal["home_to_work", "work_to_home"]
    captured_at: datetime
    work_to_home_departure_time: str = Field(min_length=5, max_length=5)
    projects: list[ProjectRow]
    regular_requests: list[TransportRequestRow]
    weekend_requests: list[TransportRequestRow]
    extra_requests: list[TransportRequestRow]
    regular_vehicles: list[TransportVehicleRow]
    weekend_vehicles: list[TransportVehicleRow]
    extra_vehicles: list[TransportVehicleRow]
    regular_vehicle_registry: list[TransportVehicleManagementRow]
    weekend_vehicle_registry: list[TransportVehicleManagementRow]
    extra_vehicle_registry: list[TransportVehicleManagementRow]
    workplaces: list[WorkplaceRow]


class TransportProposalDecision(BaseModel):
    request_id: int = Field(ge=1)
    request_kind: Literal["regular", "weekend", "extra"]
    service_date: date
    route_kind: Literal["home_to_work", "work_to_home"]
    suggested_status: Literal["confirmed", "rejected", "pending"]
    vehicle_id: int | None = Field(default=None, ge=1)
    response_message: str | None = Field(default=None, max_length=255)
    rationale: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_decision(self):
        if self.suggested_status == "confirmed" and self.vehicle_id is None:
            raise ValueError("vehicle_id is required when suggested_status is confirmed")
        if self.suggested_status != "confirmed" and self.vehicle_id is not None:
            raise ValueError("vehicle_id is only allowed when suggested_status is confirmed")
        return self

    @field_validator("response_message", mode="before")
    @classmethod
    def validate_proposal_response_message(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "A resposta", max_length=255)

    @field_validator("rationale", mode="before")
    @classmethod
    def validate_proposal_rationale(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "A justificativa", max_length=500)


class TransportProposalValidationIssue(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=500)
    blocking: bool = True
    request_id: int | None = Field(default=None, ge=1)
    vehicle_id: int | None = Field(default=None, ge=1)

    @field_validator("code")
    @classmethod
    def validate_issue_code(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise ValueError("Issue code is required")
        return normalized


class TransportAIPreflightIssue(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=500)
    blocking: bool = True
    setting_name: str | None = Field(default=None, max_length=80)

    @field_validator("code")
    @classmethod
    def validate_issue_code(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise ValueError("Issue code is required")
        return normalized

    @field_validator("setting_name", mode="before")
    @classmethod
    def validate_setting_name(cls, value: str | None) -> str | None:
        return _normalize_optional_compact_text(value, "A configuracao", max_length=80)


class TransportAIPreflightCheckResult(BaseModel):
    ok: bool
    issues: list[TransportAIPreflightIssue] = Field(default_factory=list)


class TransportAgentRouteRequest(BaseModel):
    service_date: date
    route_kind: Literal["home_to_work", "work_to_home"]
    earliest_boarding_time: str = Field(min_length=5, max_length=5)
    arrival_at_work_time: str = Field(min_length=5, max_length=5)

    @field_validator("earliest_boarding_time", "arrival_at_work_time", mode="before")
    @classmethod
    def validate_transport_agent_route_request_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @model_validator(mode="after")
    def validate_transport_agent_route_request(self) -> TransportAgentRouteRequest:
        if self.route_kind != "home_to_work":
            raise ValueError("Transport AI route calculations currently support only home_to_work")
        if self.earliest_boarding_time >= self.arrival_at_work_time:
            raise ValueError("The earliest boarding time must be earlier than the arrival time")
        return self


class TransportAgentRunStartResponse(BaseModel):
    ok: bool
    run_key: str | None = Field(default=None, min_length=1, max_length=120)
    suggestion_key: str | None = Field(default=None, min_length=1, max_length=120)
    status: str | None = Field(default=None, min_length=1, max_length=24)
    message: str = Field(min_length=1, max_length=500)
    issues: list[TransportAIPreflightIssue] = Field(default_factory=list)
    can_cancel_restore: bool = False
    suggestion_ready: bool = False

    @field_validator("run_key", "suggestion_key", "status", mode="before")
    @classmethod
    def validate_transport_agent_run_start_optional_text(cls, value: object) -> str | None:
        return _normalize_optional_compact_text(value, "O texto", max_length=120)

    @field_validator("message", mode="before")
    @classmethod
    def validate_transport_agent_run_start_message(cls, value: object) -> str:
        normalized = _normalize_optional_text(value, "A mensagem", max_length=500)
        if normalized is None:
            raise ValueError("The route calculation response message is required")
        return normalized


class TransportAgentRunIssue(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=500)
    blocking: bool = True
    source: Literal[
        "run_preflight",
        "suggestion_validation",
        "proposal_validation",
        "proposal_apply",
    ]
    setting_name: str | None = Field(default=None, max_length=80)
    request_id: int | None = Field(default=None, ge=1)
    vehicle_id: int | None = Field(default=None, ge=1)

    @field_validator("code")
    @classmethod
    def validate_transport_agent_run_issue_code(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise ValueError("Issue code is required")
        return normalized

    @field_validator("setting_name", mode="before")
    @classmethod
    def validate_transport_agent_run_issue_setting_name(cls, value: object) -> str | None:
        return _normalize_optional_compact_text(value, "A configuracao", max_length=80)


class TransportAgentPlanningVehicleTypeConfig(BaseModel):
    vehicle_type: Literal["carro", "minivan", "van", "onibus"]
    default_capacity: int | None = Field(default=None, ge=1)
    default_price: float | None = Field(default=None, ge=0)
    capacity_setting_name: str = Field(min_length=1, max_length=80)
    price_setting_name: str = Field(min_length=1, max_length=80)

    @field_validator("capacity_setting_name", "price_setting_name", mode="before")
    @classmethod
    def validate_config_setting_name(cls, value: str) -> str:
        normalized = _normalize_optional_compact_text(value, "A configuracao", max_length=80)
        if normalized is None:
            raise ValueError("The planning config setting name is required")
        return normalized


class TransportAgentPlanningSettings(BaseModel):
    work_to_home_time: str = Field(min_length=5, max_length=5)
    last_update_time: str = Field(min_length=5, max_length=5)
    default_tolerance_minutes: int = Field(ge=0)
    price_currency_code: str | None = Field(default=None, max_length=12)
    price_rate_unit: str = Field(min_length=1, max_length=16)
    vehicle_type_configs: list[TransportAgentPlanningVehicleTypeConfig] = Field(default_factory=list)

    @field_validator("work_to_home_time", "last_update_time", mode="before")
    @classmethod
    def validate_planning_setting_time(cls, value: str) -> str:
        return _normalize_transport_time(value)


class TransportAgentPlanningLimits(BaseModel):
    earliest_boarding_time: str = Field(min_length=5, max_length=5)
    arrival_at_work_time: str = Field(min_length=5, max_length=5)
    max_passengers_per_run: int = Field(ge=0)
    max_runtime_seconds: int = Field(ge=0)

    @field_validator("earliest_boarding_time", "arrival_at_work_time", mode="before")
    @classmethod
    def validate_planning_limit_time(cls, value: str) -> str:
        return _normalize_transport_time(value)


class TransportAgentPlanningRequest(BaseModel):
    request_id: int = Field(ge=1)
    request_kind: Literal["regular", "weekend", "extra"]
    service_date: date
    requested_time: str = Field(min_length=5, max_length=5)
    user_id: int = Field(ge=1)
    chave: str = Field(min_length=1, max_length=4)
    nome: str = Field(min_length=1, max_length=180)
    project_name: str = Field(min_length=1, max_length=120)
    country_code: str = Field(min_length=2, max_length=2)
    country_name: str = Field(min_length=2, max_length=80)
    workplace: str | None = Field(default=None, max_length=120)
    origin_address: str = Field(min_length=1, max_length=255)
    origin_zip_code: str = Field(min_length=1, max_length=32)

    @field_validator("requested_time", mode="before")
    @classmethod
    def validate_planning_request_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @field_validator(
        "chave",
        "nome",
        "project_name",
        "country_code",
        "country_name",
        "workplace",
        "origin_address",
        "origin_zip_code",
        mode="before",
    )
    @classmethod
    def validate_planning_request_text(cls, value: object) -> str | None:
        return _normalize_optional_text(value, "O texto", max_length=255)


class TransportAgentPlanningVehicle(BaseModel):
    vehicle_id: int = Field(ge=1)
    schedule_id: int | None = Field(default=None, ge=1)
    service_scope: Literal["regular", "weekend", "extra"]
    route_kind: Literal["home_to_work", "work_to_home"] | None = None
    departure_time: str | None = Field(default=None, min_length=5, max_length=5)
    plate: str | None = Field(default=None, max_length=15)
    vehicle_type: Literal["carro", "minivan", "van", "onibus"] | None = None
    effective_capacity: int | None = Field(default=None, ge=1)
    default_capacity: int | None = Field(default=None, ge=1)
    default_price: float | None = Field(default=None, ge=0)
    assigned_count: int = Field(ge=0)
    pending_fields: list[str] = Field(default_factory=list)
    is_ready_for_allocation: bool

    @field_validator("departure_time", mode="before")
    @classmethod
    def validate_planning_vehicle_departure_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_transport_time(value)

    @field_validator("plate", mode="before")
    @classmethod
    def validate_planning_vehicle_plate(cls, value: object) -> str | None:
        return _normalize_optional_text(value, "A placa", max_length=15)


class TransportAgentPlanningPartition(BaseModel):
    partition_key: str = Field(min_length=1, max_length=180)
    request_kind: Literal["regular", "weekend", "extra"]
    project_name: str = Field(min_length=1, max_length=120)
    country_code: str = Field(min_length=2, max_length=2)
    country_name: str = Field(min_length=2, max_length=80)
    destination_project: ProjectRow
    requests: list[TransportAgentPlanningRequest] = Field(default_factory=list)
    candidate_vehicles: list[TransportAgentPlanningVehicle] = Field(default_factory=list)


class TransportAgentPlanningInput(BaseModel):
    planning_input_hash: str = Field(min_length=64, max_length=64)
    service_date: date
    route_kind: Literal["home_to_work", "work_to_home"]
    snapshot_key: str = Field(min_length=1, max_length=180)
    captured_at: datetime
    limits: TransportAgentPlanningLimits
    settings: TransportAgentPlanningSettings
    projects_by_name: dict[str, ProjectRow] = Field(default_factory=dict)
    requests_by_scope: dict[str, list[TransportAgentPlanningRequest]] = Field(default_factory=dict)
    vehicles_by_scope: dict[str, list[TransportAgentPlanningVehicle]] = Field(default_factory=dict)
    partitions: list[TransportAgentPlanningPartition] = Field(default_factory=list)
    preflight_issues: list[TransportAIPreflightIssue] = Field(default_factory=list)
    total_requests: int = Field(ge=0)
    total_candidate_vehicles: int = Field(ge=0)

    @field_validator("planning_input_hash", mode="before")
    @classmethod
    def validate_planning_input_hash(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("The planning input hash must be a 64-character hex digest")
        return normalized


class TransportAgentResolvedRoutePoint(BaseModel):
    point_type: Literal["passenger_origin", "project_destination"]
    partition_key: str = Field(min_length=1, max_length=180)
    source_id: int = Field(ge=1)
    request_id: int | None = Field(default=None, ge=1)
    project_name: str = Field(min_length=1, max_length=120)
    country_code: str = Field(min_length=2, max_length=3)
    country_name: str = Field(min_length=2, max_length=80)
    label: str = Field(min_length=1, max_length=180)
    address: str = Field(min_length=1, max_length=255)
    zip_code: str = Field(min_length=1, max_length=32)
    normalized_query: str = Field(min_length=1, max_length=400)
    formatted_address: str = Field(min_length=1, max_length=255)
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    provider: str = Field(min_length=1, max_length=40)
    provider_place_id: str | None = Field(default=None, max_length=255)
    confidence: float | None = Field(default=None, ge=0, le=1)
    cached: bool = False


class TransportAgentResolvedRoutePointsPartition(BaseModel):
    partition_key: str = Field(min_length=1, max_length=180)
    request_kind: Literal["regular", "weekend", "extra"]
    project_name: str = Field(min_length=1, max_length=120)
    country_code: str = Field(min_length=2, max_length=3)
    country_name: str = Field(min_length=2, max_length=80)
    destination_point: TransportAgentResolvedRoutePoint | None = None
    passenger_points: list[TransportAgentResolvedRoutePoint] = Field(default_factory=list)


class TransportAgentResolvedRoutePointsResult(BaseModel):
    planning_input_hash: str = Field(min_length=64, max_length=64)
    provider: str = Field(min_length=1, max_length=40)
    partitions: list[TransportAgentResolvedRoutePointsPartition] = Field(default_factory=list)
    issues: list[TransportAIPreflightIssue] = Field(default_factory=list)
    total_resolved_points: int = Field(ge=0)

    @field_validator("planning_input_hash", mode="before")
    @classmethod
    def validate_resolved_route_points_hash(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("The planning input hash must be a 64-character hex digest")
        return normalized


class TransportAgentRouteMatrixPartition(BaseModel):
    partition_key: str = Field(min_length=1, max_length=180)
    request_kind: Literal["regular", "weekend", "extra"]
    project_name: str = Field(min_length=1, max_length=120)
    country_code: str = Field(min_length=2, max_length=3)
    country_name: str = Field(min_length=2, max_length=80)
    points: list[TransportAgentResolvedRoutePoint] = Field(default_factory=list)
    destination_index: int = Field(default=0, ge=0)
    cached: bool = False
    durations_seconds: list[list[int | None]] = Field(default_factory=list)
    distances_meters: list[list[int | None]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_route_matrix_partition(self) -> TransportAgentRouteMatrixPartition:
        point_count = len(self.points)
        if point_count == 0:
            if self.durations_seconds or self.distances_meters:
                raise ValueError("Route matrix partitions without points must not contain matrix values")
            return self

        if self.destination_index >= point_count:
            raise ValueError("destination_index must point to an existing route point")
        if self.points[self.destination_index].point_type != "project_destination":
            raise ValueError("destination_index must reference the project destination point")

        for field_name, matrix in (
            ("durations_seconds", self.durations_seconds),
            ("distances_meters", self.distances_meters),
        ):
            if len(matrix) != point_count:
                raise ValueError(f"{field_name} row count must match points length ({point_count})")
            for row in matrix:
                if len(row) != point_count:
                    raise ValueError(f"{field_name} column count must match points length ({point_count})")

        return self


class TransportAgentRouteMatricesResult(BaseModel):
    planning_input_hash: str = Field(min_length=64, max_length=64)
    provider: str = Field(min_length=1, max_length=40)
    profile: str = Field(min_length=1, max_length=80)
    partitions: list[TransportAgentRouteMatrixPartition] = Field(default_factory=list)
    issues: list[TransportAIPreflightIssue] = Field(default_factory=list)
    total_matrices: int = Field(ge=0)

    @field_validator("planning_input_hash", mode="before")
    @classmethod
    def validate_route_matrices_hash(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("The planning input hash must be a 64-character hex digest")
        return normalized


class TransportAgentVehicleCandidatePenaltyConfig(BaseModel):
    keep_existing: int = Field(default=0, ge=0)
    create_virtual: int = Field(default=50, ge=0)
    update_existing: int = Field(default=100, ge=0)
    remove_existing_from_day: int = Field(default=150, ge=0)
    change_existing_type: int = Field(default=300, ge=0)


class TransportAgentVehicleCandidate(BaseModel):
    candidate_key: str = Field(min_length=1, max_length=180)
    partition_key: str = Field(min_length=1, max_length=180)
    request_kind: Literal["regular", "weekend", "extra"]
    project_name: str = Field(min_length=1, max_length=120)
    country_code: str = Field(min_length=2, max_length=3)
    country_name: str = Field(min_length=2, max_length=80)
    candidate_type: Literal["existing", "virtual"]
    recommended_action_type: Literal["keep", "create"]
    available_action_types: list[Literal["keep", "create", "update", "remove_from_day"]] = Field(min_length=1)
    client_vehicle_key: str | None = Field(default=None, max_length=64)
    vehicle_id: int | None = Field(default=None, ge=1)
    schedule_id: int | None = Field(default=None, ge=1)
    service_scope: Literal["regular", "weekend", "extra"]
    route_kind: Literal["home_to_work", "work_to_home"]
    vehicle_type: Literal["carro", "minivan", "van", "onibus"]
    plate: str | None = Field(default=None, max_length=15)
    capacity: int = Field(ge=1)
    default_capacity: int | None = Field(default=None, ge=1)
    default_price: float = Field(ge=0)
    estimated_cost: float = Field(ge=0)
    change_penalty: int = Field(ge=0)
    update_penalty: int | None = Field(default=None, ge=0)
    remove_from_day_penalty: int | None = Field(default=None, ge=0)
    change_vehicle_type_penalty: int | None = Field(default=None, ge=0)
    assigned_count: int = Field(default=0, ge=0)
    pending_fields: list[str] = Field(default_factory=list)
    is_ready_for_allocation: bool = True


class TransportAgentVehicleCandidatesPartition(BaseModel):
    partition_key: str = Field(min_length=1, max_length=180)
    request_kind: Literal["regular", "weekend", "extra"]
    project_name: str = Field(min_length=1, max_length=120)
    country_code: str = Field(min_length=2, max_length=3)
    country_name: str = Field(min_length=2, max_length=80)
    candidates: list[TransportAgentVehicleCandidate] = Field(default_factory=list)


class TransportAgentVehicleCandidatesResult(BaseModel):
    planning_input_hash: str = Field(min_length=64, max_length=64)
    penalties: TransportAgentVehicleCandidatePenaltyConfig
    partitions: list[TransportAgentVehicleCandidatesPartition] = Field(default_factory=list)
    total_candidates: int = Field(ge=0)

    @field_validator("planning_input_hash", mode="before")
    @classmethod
    def validate_vehicle_candidates_hash(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("The planning input hash must be a 64-character hex digest")
        return normalized


class TransportAgentSolvedRoutePassenger(BaseModel):
    request_id: int = Field(ge=1)
    user_id: int = Field(ge=1)
    chave: str = Field(min_length=1, max_length=80)
    nome: str = Field(min_length=1, max_length=255)
    pickup_order: int = Field(ge=0)
    scheduled_pickup_time: str | None = Field(default=None, min_length=5, max_length=5)

    @field_validator("scheduled_pickup_time", mode="before")
    @classmethod
    def validate_solved_route_passenger_pickup_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_transport_time(value)


class TransportAgentSolvedRoute(BaseModel):
    route_key: str = Field(min_length=1, max_length=255)
    partition_key: str = Field(min_length=1, max_length=180)
    vehicle_candidate_key: str = Field(min_length=1, max_length=180)
    vehicle_unit_key: str = Field(min_length=1, max_length=220)
    candidate_type: Literal["existing", "virtual"]
    recommended_action_type: Literal["keep", "create"]
    client_vehicle_key: str | None = Field(default=None, max_length=96)
    vehicle_id: int | None = Field(default=None, ge=1)
    schedule_id: int | None = Field(default=None, ge=1)
    service_scope: Literal["regular", "weekend", "extra"]
    route_kind: Literal["home_to_work", "work_to_home"]
    vehicle_type: Literal["carro", "minivan", "van", "onibus"]
    plate: str | None = Field(default=None, max_length=15)
    capacity: int = Field(ge=1)
    request_ids: list[int] = Field(default_factory=list)
    pickup_order_request_ids: list[int] = Field(default_factory=list)
    passengers: list[TransportAgentSolvedRoutePassenger] = Field(default_factory=list)
    projected_arrival_time: str | None = Field(default=None, min_length=5, max_length=5)
    estimated_cost: float = Field(ge=0)
    change_penalty: int = Field(ge=0)
    total_duration_seconds: int = Field(ge=0)
    total_distance_meters: int = Field(ge=0)

    @field_validator("projected_arrival_time", mode="before")
    @classmethod
    def validate_solved_route_arrival_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_transport_time(value)


class TransportAgentPartitionSolveResult(BaseModel):
    planning_input_hash: str = Field(min_length=64, max_length=64)
    partition_key: str = Field(min_length=1, max_length=180)
    request_kind: Literal["regular", "weekend", "extra"]
    project_name: str = Field(min_length=1, max_length=120)
    country_code: str = Field(min_length=2, max_length=3)
    country_name: str = Field(min_length=2, max_length=80)
    algorithm_used: Literal["ortools", "heuristic"]
    routes: list[TransportAgentSolvedRoute] = Field(default_factory=list)
    unallocated_request_ids: list[int] = Field(default_factory=list)
    issues: list[TransportAIPreflightIssue] = Field(default_factory=list)
    total_estimated_cost: float = Field(ge=0)
    total_change_penalty: int = Field(ge=0)
    total_duration_seconds: int = Field(ge=0)
    total_distance_meters: int = Field(ge=0)
    total_vehicles_used: int = Field(ge=0)
    is_feasible: bool = True

    @field_validator("planning_input_hash", mode="before")
    @classmethod
    def validate_partition_solve_hash(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("The planning input hash must be a 64-character hex digest")
        return normalized


class TransportAgentVehicleAction(BaseModel):
    action_key: str = Field(min_length=1, max_length=180)
    action_type: Literal["keep", "create", "update", "remove_from_day"]
    service_scope: Literal["regular", "weekend", "extra"]
    vehicle_id: int | None = Field(default=None, ge=1)
    schedule_id: int | None = Field(default=None, ge=1)
    client_vehicle_key: str = Field(min_length=1, max_length=96)
    before: dict[str, object] | None = None
    after: dict[str, object] = Field(default_factory=dict)
    rationale: str = Field(min_length=1, max_length=500)
    cost_delta: float | None = None

    @field_validator("action_key", "client_vehicle_key", mode="before")
    @classmethod
    def validate_transport_agent_vehicle_action_key(cls, value: object) -> str:
        normalized = _normalize_optional_compact_text(value, "A chave da acao", max_length=180)
        if normalized is None:
            raise ValueError("The vehicle action key is required")
        return normalized

    @field_validator("rationale", mode="before")
    @classmethod
    def validate_transport_agent_vehicle_action_rationale(cls, value: object) -> str:
        normalized = _normalize_optional_text(value, "A justificativa", max_length=500)
        if normalized is None:
            raise ValueError("The vehicle action rationale is required")
        return normalized


class TransportAgentPassengerAllocation(BaseModel):
    request_id: int = Field(ge=1)
    request_kind: Literal["regular", "weekend", "extra"]
    service_date: date
    route_kind: Literal["home_to_work", "work_to_home"]
    vehicle_ref: str = Field(min_length=1, max_length=120)
    user_id: int = Field(ge=1)
    chave: str = Field(min_length=1, max_length=80)
    nome: str = Field(min_length=1, max_length=255)
    project_name: str = Field(min_length=1, max_length=120)
    pickup_order: int = Field(ge=0)
    scheduled_pickup_time: str = Field(min_length=5, max_length=5)
    projected_arrival_time: str = Field(min_length=5, max_length=5)
    rationale: str = Field(min_length=1, max_length=500)

    @field_validator("vehicle_ref", mode="before")
    @classmethod
    def validate_transport_agent_passenger_allocation_vehicle_ref(cls, value: object) -> str:
        normalized = _normalize_optional_compact_text(value, "A referencia do veiculo", max_length=120)
        if normalized is None:
            raise ValueError("The vehicle reference is required")
        if not normalized.startswith("existing:") and not normalized.startswith("new:"):
            raise ValueError("The vehicle reference must start with 'existing:' or 'new:'")
        return normalized

    @field_validator("scheduled_pickup_time", "projected_arrival_time", mode="before")
    @classmethod
    def validate_transport_agent_passenger_allocation_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @field_validator("chave", "nome", "project_name", "rationale", mode="before")
    @classmethod
    def validate_transport_agent_passenger_allocation_text(cls, value: object) -> str:
        normalized = _normalize_optional_text(value, "O texto", max_length=500)
        if normalized is None:
            raise ValueError("The passenger allocation text value is required")
        return normalized


class TransportAgentRouteStop(BaseModel):
    stop_order: int = Field(ge=0)
    stop_type: Literal["pickup", "destination"]
    request_id: int | None = Field(default=None, ge=1)
    user_id: int | None = Field(default=None, ge=1)
    passenger_name: str | None = Field(default=None, max_length=255)
    project_name: str = Field(min_length=1, max_length=120)
    address: str = Field(min_length=1, max_length=255)
    zip_code: str = Field(min_length=1, max_length=32)
    country_code: str = Field(min_length=2, max_length=3)
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    scheduled_time: str = Field(min_length=5, max_length=5)
    duration_from_previous_seconds: int | None = Field(default=None, ge=0)
    distance_from_previous_meters: int | None = Field(default=None, ge=0)

    @field_validator("scheduled_time", mode="before")
    @classmethod
    def validate_transport_agent_route_stop_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @field_validator("passenger_name", mode="before")
    @classmethod
    def validate_transport_agent_route_stop_passenger_name(cls, value: object) -> str | None:
        return _normalize_optional_text(value, "O passageiro", max_length=255)

    @field_validator("project_name", "address", "zip_code", "country_code", mode="before")
    @classmethod
    def validate_transport_agent_route_stop_text(cls, value: object) -> str:
        normalized = _normalize_optional_text(value, "O texto", max_length=255)
        if normalized is None:
            raise ValueError("The route stop text value is required")
        return normalized


class TransportAgentVehicleItinerary(BaseModel):
    route_key: str = Field(min_length=1, max_length=255)
    partition_key: str = Field(min_length=1, max_length=180)
    vehicle_ref: str = Field(min_length=1, max_length=120)
    service_scope: Literal["regular", "weekend", "extra"]
    route_kind: Literal["home_to_work", "work_to_home"]
    vehicle_type: Literal["carro", "minivan", "van", "onibus"]
    vehicle_id: int | None = Field(default=None, ge=1)
    schedule_id: int | None = Field(default=None, ge=1)
    client_vehicle_key: str | None = Field(default=None, max_length=96)
    plate: str | None = Field(default=None, max_length=15)
    project_name: str = Field(min_length=1, max_length=120)
    country_code: str = Field(min_length=2, max_length=3)
    country_name: str = Field(min_length=2, max_length=80)
    estimated_cost: float = Field(ge=0)
    total_duration_seconds: int = Field(ge=0)
    total_distance_meters: int = Field(ge=0)
    projected_arrival_time: str = Field(min_length=5, max_length=5)
    stops: list[TransportAgentRouteStop] = Field(default_factory=list)

    @field_validator("route_key", "partition_key", "vehicle_ref", mode="before")
    @classmethod
    def validate_transport_agent_vehicle_itinerary_key(cls, value: object) -> str:
        normalized = _normalize_optional_compact_text(value, "A chave", max_length=255)
        if normalized is None:
            raise ValueError("The itinerary key is required")
        return normalized

    @field_validator("project_name", "country_code", "country_name", mode="before")
    @classmethod
    def validate_transport_agent_vehicle_itinerary_text(cls, value: object) -> str:
        normalized = _normalize_optional_text(value, "O texto", max_length=255)
        if normalized is None:
            raise ValueError("The itinerary text value is required")
        return normalized

    @field_validator("projected_arrival_time", mode="before")
    @classmethod
    def validate_transport_agent_vehicle_itinerary_arrival_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @field_validator("client_vehicle_key", mode="before")
    @classmethod
    def validate_transport_agent_vehicle_itinerary_client_key(cls, value: object) -> str | None:
        return _normalize_optional_compact_text(value, "A chave do veiculo", max_length=96)

    @field_validator("plate", mode="before")
    @classmethod
    def validate_transport_agent_vehicle_itinerary_plate(cls, value: object) -> str | None:
        return _normalize_optional_text(value, "A placa", max_length=15)


class TransportAgentCostSummary(BaseModel):
    price_currency_code: str | None = Field(default=None, max_length=12)
    price_rate_unit: str = Field(min_length=1, max_length=16)
    current_total_estimated_cost: float = Field(ge=0)
    suggested_total_estimated_cost: float = Field(ge=0)
    estimated_cost_delta: float
    current_vehicle_count: int = Field(ge=0)
    suggested_vehicle_count: int = Field(ge=0)

    @field_validator("price_currency_code", mode="before")
    @classmethod
    def validate_transport_agent_cost_summary_currency(cls, value: object) -> str | None:
        return _normalize_optional_text(value, "A moeda", max_length=12)

    @field_validator("price_rate_unit", mode="before")
    @classmethod
    def validate_transport_agent_cost_summary_rate_unit(cls, value: object) -> str:
        normalized = _normalize_optional_compact_text(value, "A unidade", max_length=16)
        if normalized is None:
            raise ValueError("The price rate unit is required")
        return normalized


class TransportAgentChangeSummaryByVehicleType(BaseModel):
    vehicle_type: Literal["carro", "minivan", "van", "onibus"]
    keep_count: int = Field(default=0, ge=0)
    create_count: int = Field(default=0, ge=0)
    update_count: int = Field(default=0, ge=0)
    remove_from_day_count: int = Field(default=0, ge=0)
    total_count: int = Field(default=0, ge=0)


class TransportAgentChangeSummary(BaseModel):
    total_vehicle_actions: int = Field(ge=0)
    keep_count: int = Field(default=0, ge=0)
    create_count: int = Field(default=0, ge=0)
    update_count: int = Field(default=0, ge=0)
    remove_from_day_count: int = Field(default=0, ge=0)
    by_vehicle_type: list[TransportAgentChangeSummaryByVehicleType] = Field(default_factory=list)


class TransportAgentPlan(BaseModel):
    plan_key: str = Field(min_length=1, max_length=120)
    service_date: date
    route_kind: Literal["home_to_work", "work_to_home"]
    earliest_boarding_time: str = Field(min_length=5, max_length=5)
    arrival_at_work_time: str = Field(min_length=5, max_length=5)
    objective_summary: str = Field(min_length=1, max_length=500)
    vehicle_actions: list[TransportAgentVehicleAction] = Field(default_factory=list)
    passenger_allocations: list[TransportAgentPassengerAllocation] = Field(default_factory=list)
    route_itineraries: list[TransportAgentVehicleItinerary] = Field(default_factory=list)
    cost_summary: TransportAgentCostSummary
    change_summary: TransportAgentChangeSummary
    validation_issues: list[TransportProposalValidationIssue] = Field(default_factory=list)

    @field_validator("plan_key", mode="before")
    @classmethod
    def validate_transport_agent_plan_key(cls, value: object) -> str:
        normalized = _normalize_optional_compact_text(value, "A chave do plano", max_length=120)
        if normalized is None:
            raise ValueError("The plan key is required")
        return normalized

    @field_validator("earliest_boarding_time", "arrival_at_work_time", mode="before")
    @classmethod
    def validate_transport_agent_plan_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @field_validator("objective_summary", mode="before")
    @classmethod
    def validate_transport_agent_plan_objective_summary(cls, value: object) -> str:
        normalized = _normalize_optional_text(value, "O resumo do objetivo", max_length=500)
        if normalized is None:
            raise ValueError("The objective summary is required")
        return normalized


class TransportAgentRunSuggestion(BaseModel):
    suggestion_key: str = Field(min_length=1, max_length=120)
    proposal_key: str | None = Field(default=None, min_length=1, max_length=120)
    status: str = Field(min_length=1, max_length=24)
    prompt_version: str = Field(min_length=1, max_length=120)
    created_at: datetime
    updated_at: datetime
    saved_at: datetime | None = None
    applied_at: datetime | None = None
    discarded_at: datetime | None = None
    plan: TransportAgentPlan

    @field_validator("suggestion_key", "proposal_key", "status", "prompt_version", mode="before")
    @classmethod
    def validate_transport_agent_run_suggestion_text(cls, value: object) -> str | None:
        return _normalize_optional_compact_text(value, "O texto", max_length=120)


class TransportAgentRunStatusResponse(BaseModel):
    ok: bool
    run_key: str = Field(min_length=1, max_length=120)
    service_date: date
    route_kind: Literal["home_to_work", "work_to_home"]
    status: str = Field(min_length=1, max_length=24)
    llm_provider: str = Field(min_length=1, max_length=40)
    llm_model: str = Field(min_length=1, max_length=120)
    llm_reasoning_effort: str = Field(min_length=1, max_length=40)
    message: str = Field(min_length=1, max_length=500)
    issues: list[TransportAgentRunIssue] = Field(default_factory=list)
    suggestion_key: str | None = Field(default=None, min_length=1, max_length=120)
    suggestion_ready: bool = False
    can_save: bool = False
    can_apply: bool = False
    can_cancel_restore: bool = False
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    suggestion: TransportAgentRunSuggestion | None = None

    @field_validator(
        "run_key",
        "status",
        "llm_provider",
        "llm_model",
        "llm_reasoning_effort",
        "suggestion_key",
        mode="before",
    )
    @classmethod
    def validate_transport_agent_run_status_text(cls, value: object) -> str | None:
        return _normalize_optional_compact_text(value, "O texto", max_length=120)

    @field_validator("message", mode="before")
    @classmethod
    def validate_transport_agent_run_status_message(cls, value: object) -> str:
        normalized = _normalize_optional_text(value, "A mensagem", max_length=500)
        if normalized is None:
            raise ValueError("The route calculation status message is required")
        return normalized


class TransportAIRunDiagnosticsEntry(BaseModel):
    run_key: str = Field(min_length=1, max_length=120)
    service_date: date
    route_kind: Literal["home_to_work", "work_to_home"]
    status: str = Field(min_length=1, max_length=24)
    llm_provider: str = Field(min_length=1, max_length=40)
    llm_model: str = Field(min_length=1, max_length=120)
    llm_reasoning_effort: str = Field(min_length=1, max_length=40)
    openai_model: str = Field(min_length=1, max_length=120)
    route_provider: str = Field(min_length=1, max_length=40)
    suggestion_key: str | None = Field(default=None, min_length=1, max_length=120)
    suggestion_status: str | None = Field(default=None, min_length=1, max_length=24)
    prompt_version: str | None = Field(default=None, min_length=1, max_length=120)
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    error_code: str | None = Field(default=None, min_length=1, max_length=64)
    error_message: str | None = Field(default=None, max_length=500)
    preflight_issue_codes: list[str] = Field(default_factory=list)
    validation_issue_codes: list[str] = Field(default_factory=list)
    blocking_issue_count: int = Field(default=0, ge=0)
    approximate_model_call_cost: float | None = Field(default=None, ge=0)
    approximate_model_call_cost_currency: str | None = Field(default=None, min_length=1, max_length=12)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    has_raw_model_response: bool = False

    @field_validator(
        "run_key",
        "status",
        "llm_provider",
        "llm_model",
        "llm_reasoning_effort",
        "openai_model",
        "route_provider",
        "suggestion_key",
        "suggestion_status",
        "prompt_version",
        "error_code",
        "approximate_model_call_cost_currency",
        mode="before",
    )
    @classmethod
    def validate_transport_ai_diagnostics_compact_text(cls, value: object) -> str | None:
        return _normalize_optional_compact_text(value, "O texto", max_length=120)

    @field_validator("error_message", mode="before")
    @classmethod
    def validate_transport_ai_diagnostics_message(cls, value: object) -> str | None:
        return _normalize_optional_text(value, "A mensagem", max_length=500)

    @field_validator("preflight_issue_codes", "validation_issue_codes", mode="before")
    @classmethod
    def validate_transport_ai_diagnostics_codes(cls, value: object) -> list[str]:
        if value is None or value == "":
            return []
        if not isinstance(value, list):
            raise ValueError("The diagnostics issue codes must be a list")
        normalized_codes: list[str] = []
        for item in value:
            normalized = _normalize_optional_compact_text(item, "O codigo", max_length=64)
            if normalized is None:
                continue
            normalized_codes.append(normalized)
        return normalized_codes


class TransportAIRunDiagnosticsResponse(BaseModel):
    runs: list[TransportAIRunDiagnosticsEntry] = Field(default_factory=list)
    count: int = Field(default=0, ge=0)
    service_date: date | None = None
    statuses: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator("statuses", mode="before")
    @classmethod
    def validate_transport_ai_diagnostics_statuses(cls, value: object) -> list[str]:
        if value is None or value == "":
            return []
        if not isinstance(value, list):
            raise ValueError("The diagnostics statuses must be a list")
        normalized_statuses: list[str] = []
        for item in value:
            normalized = _normalize_optional_compact_text(item, "O status", max_length=24)
            if normalized is None:
                continue
            normalized_statuses.append(normalized)
        return normalized_statuses


class TransportProposalAuditContext(BaseModel):
    proposal_key: str = Field(min_length=1, max_length=120)
    proposal_origin: Literal["manual", "system", "agent"]
    proposal_snapshot_key: str = Field(min_length=1, max_length=180)
    evaluation_snapshot_key: str = Field(min_length=1, max_length=180)
    service_date: date
    route_kind: Literal["home_to_work", "work_to_home"]
    total_decisions: int = Field(ge=0)
    confirmed_decisions: int = Field(ge=0)
    rejected_decisions: int = Field(ge=0)
    pending_decisions: int = Field(ge=0)
    decision_request_ids: list[int] = Field(default_factory=list)
    decision_vehicle_ids: list[int] = Field(default_factory=list)
    replaces_proposal_key: str | None = Field(default=None, max_length=120)


class TransportProposalAuditResult(BaseModel):
    proposal_status: Literal["draft", "approved", "rejected", "applied", "expired"]
    validation_issue_count: int = Field(ge=0)
    validation_issue_codes: list[str] = Field(default_factory=list)
    applied_assignment_count: int = Field(ge=0)
    applied_assignment_ids: list[int] = Field(default_factory=list)


class TransportProposalAuditEntry(BaseModel):
    audit_entry_key: str = Field(min_length=1, max_length=120)
    action: Literal["generated", "validated", "approved", "rejected", "applied"]
    outcome: Literal["generated", "passed", "blocked", "approved", "rejected", "applied"]
    actor: TransportIdentity
    occurred_at: datetime
    message: str | None = Field(default=None, max_length=255)
    context: TransportProposalAuditContext
    result: TransportProposalAuditResult

    @field_validator("message", mode="before")
    @classmethod
    def validate_audit_message(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "A mensagem", max_length=255)


class TransportOperationalProposalSummary(BaseModel):
    total_snapshot_requests: int = Field(ge=0)
    total_snapshot_vehicles: int = Field(ge=0)
    total_decisions: int = Field(ge=0)
    confirmed_decisions: int = Field(ge=0)
    rejected_decisions: int = Field(ge=0)
    pending_decisions: int = Field(ge=0)


class TransportOperationalProposal(BaseModel):
    proposal_key: str = Field(min_length=1, max_length=120)
    proposal_status: Literal["draft", "approved", "rejected", "applied", "expired"]
    origin: Literal["manual", "system", "agent"]
    replaces_proposal_key: str | None = Field(default=None, max_length=120)
    created_at: datetime
    expires_at: datetime | None = None
    snapshot: TransportOperationalSnapshot
    decisions: list[TransportProposalDecision] = Field(default_factory=list)
    summary: TransportOperationalProposalSummary
    validation_issues: list[TransportProposalValidationIssue] = Field(default_factory=list)
    audit_trail: list[TransportProposalAuditEntry] = Field(default_factory=list)


class TransportOperationalProposalCommandResult(BaseModel):
    ok: bool
    message: str
    proposal: TransportOperationalProposal


class TransportOperationalProposalRejectRequest(BaseModel):
    proposal: TransportOperationalProposal
    message: str | None = Field(default=None, max_length=255)

    @field_validator("message", mode="before")
    @classmethod
    def validate_reject_message(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, "A mensagem", max_length=255)


class TransportOperationalProposalBuildRequest(BaseModel):
    service_date: date
    route_kind: Literal["home_to_work", "work_to_home"]
    origin: Literal["manual", "system", "agent"] = "manual"
    replaces_proposal_key: str | None = Field(default=None, max_length=120)
    decisions: list[TransportProposalDecision] = Field(default_factory=list)
    captured_at: datetime | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None


class TransportOperationalAppliedAssignment(BaseModel):
    assignment_id: int = Field(ge=1)
    request_id: int = Field(ge=1)
    service_date: date
    route_kind: Literal["home_to_work", "work_to_home"]
    status: Literal["confirmed", "rejected", "cancelled", "pending"]
    vehicle_id: int | None = Field(default=None, ge=1)
    was_update: bool


class TransportOperationalProposalApplyRequest(BaseModel):
    proposal: TransportOperationalProposal


class TransportOperationalProposalApplyResult(BaseModel):
    ok: bool
    message: str
    proposal: TransportOperationalProposal
    applied_assignments: list[TransportOperationalAppliedAssignment] = Field(default_factory=list)


class TransportReevaluationCatalogEntry(BaseModel):
    event_type: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    downstream_actions: list[
        Literal[
            "refresh_snapshot",
            "revalidate_constraints",
            "rebuild_proposal",
            "regenerate_export",
            "refresh_transport_state",
        ]
    ] = Field(default_factory=list)


class TransportReevaluationEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=120)
    event_type: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=1, max_length=40)
    source: Literal["transport_admin", "web_transport", "transport_proposal"]
    message: str = Field(min_length=1, max_length=255)
    emitted_at: datetime
    service_date: date | None = None
    route_kind: Literal["home_to_work", "work_to_home"] | None = None
    request_id: int | None = Field(default=None, ge=1)
    vehicle_id: int | None = Field(default=None, ge=1)
    schedule_id: int | None = Field(default=None, ge=1)
    workplace_id: int | None = Field(default=None, ge=1)
    proposal_key: str | None = Field(default=None, max_length=120)
    downstream_actions: list[
        Literal[
            "refresh_snapshot",
            "revalidate_constraints",
            "rebuild_proposal",
            "regenerate_export",
            "refresh_transport_state",
        ]
    ] = Field(default_factory=list)

    @field_validator("message", mode="before")
    @classmethod
    def validate_reevaluation_message(cls, value: str) -> str:
        return _normalize_required_label(value, "A mensagem do evento", max_length=255)


class TransportReevaluationCatalogResponse(BaseModel):
    catalog: list[TransportReevaluationCatalogEntry] = Field(default_factory=list)
    recent_events: list[TransportReevaluationEvent] = Field(default_factory=list)


class TransportCurrencyOptionRow(BaseModel):
    code: str = Field(min_length=2, max_length=12)
    display_label: str | None = Field(default=None, max_length=80)

    @field_validator("code")
    @classmethod
    def validate_currency_code(cls, value: str) -> str:
        normalized = _normalize_transport_currency_code(value)
        if normalized is None:
            raise ValueError("Currency code is required.")
        return normalized

    @field_validator("display_label")
    @classmethod
    def validate_display_label(cls, value: str | None) -> str | None:
        return _normalize_optional_label(value, "O rótulo da moeda", max_length=80)


TransportPriceRateUnit = Literal["hour", "day", "week", "month"]
TransportAILlmProvider = Literal["openai", "deepseek"]


class TransportAISettingsResponse(BaseModel):
    provider: TransportAILlmProvider
    resolved_model: str = Field(min_length=1, max_length=120)
    reasoning_effort: str = Field(min_length=1, max_length=32)
    has_api_key: bool = False
    api_key_hint: str | None = Field(default=None, max_length=32)

    @field_validator("resolved_model", "reasoning_effort", "api_key_hint", mode="before")
    @classmethod
    def validate_transport_ai_settings_response_text(cls, value: object) -> str | None:
        return _normalize_optional_compact_text(value, "O texto", max_length=120)


class TransportAISettingsUpdateRequest(BaseModel):
    provider: TransportAILlmProvider
    api_key: str | None = Field(default=None, max_length=4096)

    @field_validator("api_key", mode="before")
    @classmethod
    def validate_transport_ai_settings_api_key(cls, value: object) -> str | None:
        return _normalize_optional_compact_text(value, "A chave API", max_length=4096)


class TransportSettingsResponse(BaseModel):
    work_to_home_time: str = Field(min_length=5, max_length=5)
    last_update_time: str = Field(min_length=5, max_length=5)
    default_car_seats: int = Field(ge=1, le=99)
    default_minivan_seats: int = Field(ge=1, le=99)
    default_van_seats: int = Field(ge=1, le=99)
    default_bus_seats: int = Field(ge=1, le=99)
    default_tolerance_minutes: int = Field(ge=0, le=240)
    price_currency_code: str | None = Field(default=None, min_length=2, max_length=12)
    price_rate_unit: TransportPriceRateUnit
    default_car_price: float | None = Field(default=None, ge=0, le=9999999999.99, multiple_of=0.01)
    default_minivan_price: float | None = Field(default=None, ge=0, le=9999999999.99, multiple_of=0.01)
    default_van_price: float | None = Field(default=None, ge=0, le=9999999999.99, multiple_of=0.01)
    default_bus_price: float | None = Field(default=None, ge=0, le=9999999999.99, multiple_of=0.01)
    available_currencies: list[TransportCurrencyOptionRow] = Field(default_factory=list)

    @field_validator("work_to_home_time")
    @classmethod
    def validate_work_to_home_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @field_validator("last_update_time")
    @classmethod
    def validate_last_update_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @field_validator("price_currency_code")
    @classmethod
    def validate_price_currency_code(cls, value: str | None) -> str | None:
        return _normalize_transport_currency_code(value)

    @field_validator("price_rate_unit")
    @classmethod
    def validate_price_rate_unit(cls, value: str) -> str:
        return _normalize_transport_price_rate_unit(value)


class TransportSettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_to_home_time: str = Field(min_length=5, max_length=5)
    last_update_time: str = Field(min_length=5, max_length=5)
    default_car_seats: int = Field(ge=1, le=99)
    default_minivan_seats: int = Field(ge=1, le=99)
    default_van_seats: int = Field(ge=1, le=99)
    default_bus_seats: int = Field(ge=1, le=99)
    default_tolerance_minutes: int = Field(ge=0, le=240)
    price_currency_code: str | None = Field(default=None, min_length=2, max_length=12)
    price_rate_unit: TransportPriceRateUnit
    default_car_price: float | None = Field(default=None, ge=0, le=9999999999.99, multiple_of=0.01)
    default_minivan_price: float | None = Field(default=None, ge=0, le=9999999999.99, multiple_of=0.01)
    default_van_price: float | None = Field(default=None, ge=0, le=9999999999.99, multiple_of=0.01)
    default_bus_price: float | None = Field(default=None, ge=0, le=9999999999.99, multiple_of=0.01)

    @field_validator("work_to_home_time")
    @classmethod
    def validate_work_to_home_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @field_validator("last_update_time")
    @classmethod
    def validate_last_update_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @field_validator("price_currency_code")
    @classmethod
    def validate_price_currency_code(cls, value: str | None) -> str | None:
        return _normalize_transport_currency_code(value)

    @field_validator("price_rate_unit")
    @classmethod
    def validate_price_rate_unit(cls, value: str) -> str:
        return _normalize_transport_price_rate_unit(value)


class TransportCurrencyCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=12)
    display_label: str | None = Field(default=None, max_length=80)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        normalized = _normalize_transport_currency_code(value)
        if normalized is None:
            raise ValueError("Currency code is required.")
        return normalized

    @field_validator("display_label")
    @classmethod
    def validate_display_label(cls, value: str | None) -> str | None:
        return _normalize_optional_label(value, "O rótulo da moeda", max_length=80)


class TransportDateSettingsResponse(BaseModel):
    service_date: date
    work_to_home_time: str = Field(min_length=5, max_length=5)

    @field_validator("work_to_home_time")
    @classmethod
    def validate_work_to_home_time(cls, value: str) -> str:
        return _normalize_transport_time(value)


class TransportDateSettingsUpdateRequest(BaseModel):
    service_date: date
    work_to_home_time: str = Field(min_length=5, max_length=5)

    @field_validator("work_to_home_time")
    @classmethod
    def validate_work_to_home_time(cls, value: str) -> str:
        return _normalize_transport_time(value)


class TransportWorkToHomeTimePolicyResponse(BaseModel):
    service_date: date
    workplace: str | None = None
    resolved_work_to_home_time: str = Field(min_length=5, max_length=5)
    source: Literal["global", "workplace_context", "date_override"]
    global_work_to_home_time: str = Field(min_length=5, max_length=5)
    date_override_work_to_home_time: str | None = Field(default=None, min_length=5, max_length=5)
    workplace_work_to_home_time: str | None = Field(default=None, min_length=5, max_length=5)
    transport_group: str | None = None
    boarding_point: str | None = None
    transport_window_start: str | None = Field(default=None, min_length=5, max_length=5)
    transport_window_end: str | None = Field(default=None, min_length=5, max_length=5)
    service_restrictions: str | None = None

    @field_validator("resolved_work_to_home_time")
    @classmethod
    def validate_resolved_work_to_home_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @field_validator("global_work_to_home_time")
    @classmethod
    def validate_global_work_to_home_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @field_validator("date_override_work_to_home_time", mode="before")
    @classmethod
    def validate_date_override_work_to_home_time(cls, value: str | None) -> str | None:
        return _normalize_optional_transport_time(value)

    @field_validator("workplace_work_to_home_time", mode="before")
    @classmethod
    def validate_workplace_work_to_home_time(cls, value: str | None) -> str | None:
        return _normalize_optional_transport_time(value)

    @field_validator("transport_window_start", mode="before")
    @classmethod
    def validate_policy_transport_window_start(cls, value: str | None) -> str | None:
        return _normalize_optional_transport_time(value)

    @field_validator("transport_window_end", mode="before")
    @classmethod
    def validate_policy_transport_window_end(cls, value: str | None) -> str | None:
        return _normalize_optional_transport_time(value)


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
    event_time: datetime | None = None
    event_date_label: str
    event_time_label: str | None = None
    timezone_name: str
    timezone_label: str


class DatabaseEventFilterOptions(BaseModel):
    action: list[str] = Field(default_factory=list)
    chave: list[str] = Field(default_factory=list)
    rfid: list[str] = Field(default_factory=list)
    project: list[str] = Field(default_factory=list)
    source: list[str] = Field(default_factory=list)
    status: list[str] = Field(default_factory=list)


class DatabaseEventListResponse(BaseModel):
    items: list[EventRow]
    total: int
    page: int
    page_size: int
    total_pages: int
    filter_options: DatabaseEventFilterOptions = Field(default_factory=DatabaseEventFilterOptions)


class InactiveUserRow(BaseModel):
    id: int
    rfid: Optional[str]
    nome: str
    chave: str
    projeto: str
    timezone_name: str
    timezone_label: str
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
    projeto: str = Field(min_length=2, max_length=120)
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

    @field_validator("projeto", mode="before")
    @classmethod
    def validate_mobile_sync_project(cls, value: str) -> str:
        return _normalize_project_value(value)


class MobileSubmitRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    projeto: str = Field(min_length=2, max_length=120)
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

    @field_validator("projeto", mode="before")
    @classmethod
    def validate_mobile_submit_project(cls, value: str) -> str:
        return _normalize_project_value(value)


class MobileFormsSubmitRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    projeto: str = Field(min_length=2, max_length=120)
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

    @field_validator("projeto", mode="before")
    @classmethod
    def validate_mobile_forms_submit_project(cls, value: str) -> str:
        return _normalize_project_value(value)


class WebCheckSubmitRequest(MobileFormsSubmitRequest):
    pass


class WebPasswordStatusResponse(BaseModel):
    found: bool
    chave: str
    has_password: bool
    authenticated: bool
    message: str


class WebPasswordRegisterRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    projeto: str = Field(min_length=2, max_length=120)
    senha: str = Field(min_length=3, max_length=10)

    @field_validator("chave")
    @classmethod
    def validate_web_password_register_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("senha", mode="before")
    @classmethod
    def validate_web_password_register_value(cls, value: str) -> str:
        return _validate_web_password(value, "A senha")

    @field_validator("projeto", mode="before")
    @classmethod
    def validate_web_password_project(cls, value: str) -> str:
        return _normalize_project_value(value)


class WebUserSelfRegistrationRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    nome: str = Field(min_length=3, max_length=180)
    projeto: str = Field(min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    senha: str = Field(min_length=3, max_length=10)
    confirmar_senha: str = Field(min_length=3, max_length=10)

    @field_validator("chave")
    @classmethod
    def validate_web_user_self_registration_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("nome", mode="before")
    @classmethod
    def validate_web_user_self_registration_nome(cls, value: str) -> str:
        return normalize_person_name(str(value))

    @field_validator("projeto", mode="before")
    @classmethod
    def validate_web_user_self_registration_project(cls, value: str) -> str:
        return _normalize_project_value(value)

    @field_validator("email", mode="before")
    @classmethod
    def validate_web_user_self_registration_email(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_compact_text(value, "O email", max_length=255)
        if normalized is None:
            return None
        normalized = normalized.lower()
        if normalized.count("@") != 1:
            raise ValueError("O email deve ser um endereco valido")
        local_part, domain = normalized.split("@", 1)
        if not local_part or not domain:
            raise ValueError("O email deve ser um endereco valido")
        return normalized

    @field_validator("senha", mode="before")
    @classmethod
    def validate_web_user_self_registration_password(cls, value: str) -> str:
        return _validate_web_password(value, "A senha")

    @field_validator("confirmar_senha", mode="before")
    @classmethod
    def validate_web_user_self_registration_password_confirmation(cls, value: str) -> str:
        return _validate_web_password(value, "A confirmacao da senha")

    @model_validator(mode="after")
    def validate_web_user_self_registration_password_match(self):
        if self.senha != self.confirmar_senha:
            raise ValueError("A confirmacao da senha nao confere")
        return self


class WebPasswordLoginRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    senha: str = Field(min_length=1, max_length=10)

    @field_validator("chave")
    @classmethod
    def validate_web_password_login_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("senha", mode="before")
    @classmethod
    def validate_web_password_login_value(cls, value: str) -> str:
        password = str(value)
        if len(password) < 1 or len(password) > 10:
            raise ValueError("A senha deve ter entre 1 e 10 caracteres")
        return password


class WebPasswordChangeRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    senha_antiga: str = Field(min_length=3, max_length=10)
    nova_senha: str = Field(min_length=3, max_length=10)

    @field_validator("chave")
    @classmethod
    def validate_web_password_change_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("senha_antiga", mode="before")
    @classmethod
    def validate_web_password_old_value(cls, value: str) -> str:
        return _validate_web_password(value, "A senha antiga")

    @field_validator("nova_senha", mode="before")
    @classmethod
    def validate_web_password_new_value(cls, value: str) -> str:
        return _validate_web_password(value, "A nova senha")


class WebPasswordActionResponse(BaseModel):
    ok: bool
    authenticated: bool
    has_password: bool
    message: str


class WebTransportRequestItemResponse(BaseModel):
    request_id: int
    request_kind: Literal["regular", "weekend", "extra"]
    status: Literal["pending", "confirmed", "rejected", "cancelled", "realized"]
    is_active: bool = False
    service_date: date | None = None
    requested_time: str | None = None
    selected_weekdays: list[int] = Field(default_factory=list)
    route_kind: Literal["home_to_work", "work_to_home"] | None = None
    boarding_time: str | None = None
    confirmation_deadline_time: str | None = None
    vehicle_type: Literal["carro", "minivan", "van", "onibus"] | None = None
    vehicle_plate: str | None = None
    vehicle_color: str | None = None
    tolerance_minutes: int | None = Field(default=None, ge=0, le=240)
    awareness_required: bool = False
    awareness_confirmed: bool = False
    response_message: str | None = None
    created_at: datetime


class WebTransportStateResponse(BaseModel):
    chave: str
    end_rua: str | None = None
    zip: str | None = None
    status: Literal["available", "pending", "confirmed", "realized"] = "available"
    request_id: int | None = None
    request_kind: Literal["regular", "weekend", "extra"] | None = None
    route_kind: Literal["home_to_work", "work_to_home"] | None = None
    service_date: date | None = None
    requested_time: str | None = None
    boarding_time: str | None = None
    confirmation_deadline_time: str | None = None
    vehicle_type: Literal["carro", "minivan", "van", "onibus"] | None = None
    vehicle_plate: str | None = None
    vehicle_color: str | None = None
    tolerance_minutes: int | None = Field(default=None, ge=0, le=240)
    awareness_required: bool = False
    awareness_confirmed: bool = False
    requests: list[WebTransportRequestItemResponse] = Field(default_factory=list)


class WebTransportActionResponse(BaseModel):
    ok: bool
    message: str
    state: WebTransportStateResponse


class WebTransportAddressUpdateRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    end_rua: str = Field(min_length=3, max_length=255)
    zip: str = Field(min_length=6, max_length=6)

    @field_validator("chave")
    @classmethod
    def validate_transport_address_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("end_rua", mode="before")
    @classmethod
    def validate_transport_address_value(cls, value: str) -> str:
        return _normalize_required_label(value, "O endereco", max_length=255)

    @field_validator("zip", mode="before")
    @classmethod
    def validate_transport_zip_code(cls, value: str) -> str:
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        if len(digits) != 6:
            raise ValueError("O Codigo ZIP deve conter exatamente 6 numeros")
        return digits


class WebTransportRequestCreate(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    request_kind: Literal["regular", "weekend", "extra"]
    requested_time: str | None = None
    requested_date: date | None = None
    selected_weekdays: list[int] | None = None

    @field_validator("chave")
    @classmethod
    def validate_transport_request_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("requested_time")
    @classmethod
    def validate_web_transport_requested_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_transport_time(value)

    @field_validator("selected_weekdays", mode="before")
    @classmethod
    def validate_web_transport_selected_weekdays(cls, value: object) -> list[int] | None:
        return _normalize_transport_weekday_list(value)

    @model_validator(mode="after")
    def validate_web_transport_request(self):
        if self.request_kind != "extra" and self.requested_date is not None:
            raise ValueError("requested_date is only allowed for extra requests")

        if self.request_kind == "extra":
            if self.selected_weekdays:
                raise ValueError("selected_weekdays is only allowed for recurring requests")
            return self

        if self.request_kind == "regular":
            if self.selected_weekdays is None:
                self.selected_weekdays = [0, 1, 2, 3, 4]
            if not self.selected_weekdays:
                raise ValueError("selected_weekdays is required for regular requests")
            if any(weekday >= 5 for weekday in self.selected_weekdays):
                raise ValueError("regular requests only allow weekdays from Monday to Friday")
            return self

        if self.selected_weekdays is None:
            self.selected_weekdays = [5, 6]
        if not self.selected_weekdays:
            raise ValueError("selected_weekdays is required for weekend requests")
        if any(weekday < 5 for weekday in self.selected_weekdays):
            raise ValueError("weekend requests only allow Saturday or Sunday")
        return self


class WebTransportRequestAction(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    request_id: int = Field(ge=1)

    @field_validator("chave")
    @classmethod
    def validate_transport_action_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized


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
    minimum_checkout_distance_meters: int = Field(ge=1, le=999999)
    nearest_workplace_distance_meters: float | None = Field(default=None, ge=0)


class WebCheckHistoryResponse(BaseModel):
    found: bool
    chave: str
    projeto: str | None = None
    current_action: Literal["checkin", "checkout"] | None = None
    current_local: str | None = None
    has_current_day_checkin: bool = False
    last_checkin_at: datetime | None = None
    last_checkout_at: datetime | None = None


class WebLocationOptionsResponse(BaseModel):
    items: list[str]
    location_accuracy_threshold_meters: int = Field(ge=1, le=9999)


class WebProjectUpdateRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    projeto: str = Field(min_length=2, max_length=120)

    @field_validator("chave")
    @classmethod
    def validate_web_project_update_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("projeto", mode="before")
    @classmethod
    def validate_web_project_update_project(cls, value: str) -> str:
        return _normalize_project_value(value)


class WebProjectUpdateResponse(BaseModel):
    ok: bool
    message: str
    project: str


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


class ProviderCheckSubmitRequest(BaseModel):
    chave: str = Field(min_length=4, max_length=4)
    nome: str = Field(min_length=3, max_length=180)
    projeto: str = Field(min_length=2, max_length=120)
    atividade: Literal["check-in", "check-out"]
    informe: Literal["normal", "retroativo"]
    data: str = Field(min_length=10, max_length=10)
    hora: str = Field(min_length=8, max_length=8)

    @field_validator("chave")
    @classmethod
    def validate_provider_chave(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 4 or not normalized.isalnum():
            raise ValueError("A chave deve ter 4 caracteres alfanumericos")
        return normalized

    @field_validator("nome", mode="before")
    @classmethod
    def validate_provider_nome(cls, value: str) -> str:
        return _normalize_required_label(str(value), "O nome", max_length=180)

    @field_validator("projeto", mode="before")
    @classmethod
    def validate_provider_project(cls, value: str) -> str:
        return _normalize_project_value(value)

    @field_validator("informe", mode="before")
    @classmethod
    def validate_provider_informe(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in {"normal", "retroativo"}:
            raise ValueError("Informe deve ser 'normal' ou 'retroativo'")
        return normalized

    @field_validator("atividade", mode="before")
    @classmethod
    def validate_provider_atividade(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in {"check-in", "check-out"}:
            raise ValueError("Atividade deve ser 'check-in' ou 'check-out'")
        return normalized

    @field_validator("data")
    @classmethod
    def validate_provider_data(cls, value: str) -> str:
        normalized = str(value).strip()
        if len(normalized) != 10:
            raise ValueError("A data deve estar no formato dd/mm/aaaa")
        return normalized

    @field_validator("hora")
    @classmethod
    def validate_provider_hora(cls, value: str) -> str:
        normalized = str(value).strip()
        if len(normalized) != 8:
            raise ValueError("A hora deve estar no formato hh:mm:ss")
        return normalized


class ProviderCheckSubmitResponse(BaseModel):
    ok: bool
    duplicate: bool = False
    created_user: bool = False
    updated_project: bool = False
    updated_current_state: bool = False
    message: str
    chave: str
    projeto: str
    atividade: Literal["check-in", "check-out"]
    informe: Literal["normal", "retroativo"]
    time: datetime


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
    minimum_checkout_distance_meters_by_project: dict[str, int] = Field(default_factory=dict)
