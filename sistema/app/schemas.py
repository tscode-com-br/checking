import re
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

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


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    country_name: str | None = Field(default=None, min_length=2, max_length=80)
    timezone_name: str | None = Field(default=None, min_length=1, max_length=64)

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
    time: datetime
    assiduidade: Literal["Normal", "Retroativo"]


class ProviderFormRow(BaseModel):
    recebimento: datetime
    chave: str
    nome: str
    projeto: str
    timezone_name: str
    timezone_label: str
    atividade: Literal["check-in", "check-out"]
    informe: Literal["normal", "retroativo"]
    data: str
    hora: str


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
    event_time: datetime
    event_time_label: str
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
    workplace: Optional[str] = None
    placa: Optional[str] = None
    end_rua: Optional[str] = None
    zip: Optional[str] = None
    cargo: Optional[str] = None
    email: Optional[str] = None


class TransportWorkplaceUpsert(BaseModel):
    workplace: str = Field(min_length=2, max_length=120)
    address: str = Field(min_length=3, max_length=255)
    zip: str = Field(min_length=1, max_length=10)
    country: str = Field(min_length=2, max_length=80)

    @field_validator("workplace", mode="before")
    @classmethod
    def validate_workplace_name(cls, value: str) -> str:
        return _normalize_required_label(value, "O workplace", max_length=120)

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


class WorkplaceRow(BaseModel):
    id: int
    workplace: str
    address: str
    zip: str
    country: str


class TransportVehicleCreate(BaseModel):
    placa: str = Field(max_length=PLATE_MAX_LENGTH)
    tipo: Literal["carro", "minivan", "van", "onibus"]
    color: str = Field(min_length=2, max_length=40)
    lugares: int = Field(ge=1, le=99)
    tolerance: int = Field(ge=0, le=240)
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

    @field_validator("placa", mode="before")
    @classmethod
    def validate_vehicle_plate(cls, value: str) -> str:
        normalized = _normalize_optional_plate(value)
        if normalized is None:
            raise ValueError("A placa e obrigatoria")
        return normalized

    @field_validator("color", mode="before")
    @classmethod
    def validate_vehicle_color(cls, value: str) -> str:
        return _normalize_required_label(value, "A cor", max_length=40)

    @field_validator("departure_time", mode="before")
    @classmethod
    def validate_vehicle_departure_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not str(value).strip():
            return None
        return _normalize_transport_time(value)


class TransportVehicleRow(BaseModel):
    id: int
    schedule_id: int | None = None
    placa: str
    tipo: str
    color: str | None = None
    lugares: int
    tolerance: int
    service_scope: str
    route_kind: Literal["home_to_work", "work_to_home"] | None = None
    departure_time: str | None = None


class TransportVehicleManagementRow(BaseModel):
    vehicle_id: int
    schedule_id: int | None = None
    placa: str
    tipo: str
    lugares: int
    assigned_count: int = Field(ge=0)
    service_date: date | None = None
    route_kind: Literal["home_to_work", "work_to_home"] | None = None
    departure_time: str | None = None


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


class TransportSettingsResponse(BaseModel):
    work_to_home_time: str = Field(min_length=5, max_length=5)
    last_update_time: str = Field(min_length=5, max_length=5)
    default_car_seats: int = Field(ge=1, le=99)
    default_minivan_seats: int = Field(ge=1, le=99)
    default_van_seats: int = Field(ge=1, le=99)
    default_bus_seats: int = Field(ge=1, le=99)
    default_tolerance_minutes: int = Field(ge=0, le=240)

    @field_validator("work_to_home_time")
    @classmethod
    def validate_work_to_home_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @field_validator("last_update_time")
    @classmethod
    def validate_last_update_time(cls, value: str) -> str:
        return _normalize_transport_time(value)


class TransportSettingsUpdateRequest(BaseModel):
    work_to_home_time: str = Field(min_length=5, max_length=5)
    last_update_time: str = Field(min_length=5, max_length=5)
    default_car_seats: int = Field(ge=1, le=99)
    default_minivan_seats: int = Field(ge=1, le=99)
    default_van_seats: int = Field(ge=1, le=99)
    default_bus_seats: int = Field(ge=1, le=99)
    default_tolerance_minutes: int = Field(ge=0, le=240)

    @field_validator("work_to_home_time")
    @classmethod
    def validate_work_to_home_time(cls, value: str) -> str:
        return _normalize_transport_time(value)

    @field_validator("last_update_time")
    @classmethod
    def validate_last_update_time(cls, value: str) -> str:
        return _normalize_transport_time(value)


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
