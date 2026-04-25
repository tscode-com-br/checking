from __future__ import annotations

from dataclasses import dataclass
import unicodedata
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Project


DEFAULT_PROJECT_NAMES = ("P80", "P82", "P83")
PROJECT_NAME_MAX_LENGTH = 120
DEFAULT_PROJECT_COUNTRY_CODE = "SG"
PROJECT_COUNTRY_NAME_MAX_LENGTH = 80
PROJECT_TIMEZONE_NAME_MAX_LENGTH = 64


@dataclass(frozen=True)
class ProjectCountryConfig:
    country_code: str
    country_name: str
    timezone_name: str


SUPPORTED_PROJECT_COUNTRIES: dict[str, ProjectCountryConfig] = {
    "BR": ProjectCountryConfig(
        country_code="BR",
        country_name="Brasil",
        timezone_name="America/Sao_Paulo",
    ),
    "CN": ProjectCountryConfig(
        country_code="CN",
        country_name="China",
        timezone_name="Asia/Shanghai",
    ),
    "AE": ProjectCountryConfig(
        country_code="AE",
        country_name="Emirados Árabes Unidos",
        timezone_name="Asia/Dubai",
    ),
    "IN": ProjectCountryConfig(
        country_code="IN",
        country_name="Índia",
        timezone_name="Asia/Kolkata",
    ),
    "JP": ProjectCountryConfig(
        country_code="JP",
        country_name="Japão",
        timezone_name="Asia/Tokyo",
    ),
    "KR": ProjectCountryConfig(
        country_code="KR",
        country_name="Coreia do Sul",
        timezone_name="Asia/Seoul",
    ),
    "MY": ProjectCountryConfig(
        country_code="MY",
        country_name="Malásia",
        timezone_name="Asia/Kuala_Lumpur",
    ),
    "PH": ProjectCountryConfig(
        country_code="PH",
        country_name="Filipinas",
        timezone_name="Asia/Manila",
    ),
    "QA": ProjectCountryConfig(
        country_code="QA",
        country_name="Catar",
        timezone_name="Asia/Qatar",
    ),
    "SA": ProjectCountryConfig(
        country_code="SA",
        country_name="Arábia Saudita",
        timezone_name="Asia/Riyadh",
    ),
    "SG": ProjectCountryConfig(
        country_code="SG",
        country_name="Singapura",
        timezone_name="Asia/Singapore",
    ),
    "TH": ProjectCountryConfig(
        country_code="TH",
        country_name="Tailândia",
        timezone_name="Asia/Bangkok",
    ),
    "VN": ProjectCountryConfig(
        country_code="VN",
        country_name="Vietnã",
        timezone_name="Asia/Ho_Chi_Minh",
    ),
}


def normalize_project_name(value: str, *, field_name: str = "O projeto") -> str:
    normalized = " ".join(str(value or "").strip().split()).upper()
    if len(normalized) < 2:
        raise ValueError(f"{field_name} deve ter ao menos 2 caracteres")
    if len(normalized) > PROJECT_NAME_MAX_LENGTH:
        raise ValueError(f"{field_name} deve ter no maximo {PROJECT_NAME_MAX_LENGTH} caracteres")
    return normalized


def normalize_project_country_code(value: str, *, field_name: str = "O país do projeto") -> str:
    normalized = str(value or "").strip().upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError(f"{field_name} deve ser informado como sigla com 2 letras")
    if normalized not in SUPPORTED_PROJECT_COUNTRIES:
        raise ValueError(f"{field_name} não é suportado nesta etapa")
    return normalized


def normalize_optional_project_country_code(value: str | None) -> str | None:
    normalized = str(value or "").strip().upper()
    if not normalized:
        return None
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError("O código do país do projeto deve ter 2 letras")
    return normalized


def normalize_project_country_name(value: str, *, field_name: str = "O país do projeto") -> str:
    normalized = " ".join(str(value or "").strip().split())
    if len(normalized) < 2:
        raise ValueError(f"{field_name} deve ter ao menos 2 caracteres")
    if len(normalized) > PROJECT_COUNTRY_NAME_MAX_LENGTH:
        raise ValueError(f"{field_name} deve ter no maximo {PROJECT_COUNTRY_NAME_MAX_LENGTH} caracteres")
    return normalized


def normalize_project_timezone_name(value: str, *, field_name: str = "O fuso horário do projeto") -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} deve ser informado")
    if len(normalized) > PROJECT_TIMEZONE_NAME_MAX_LENGTH:
        raise ValueError(f"{field_name} deve ter no maximo {PROJECT_TIMEZONE_NAME_MAX_LENGTH} caracteres")
    try:
        ZoneInfo(normalized)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"{field_name} deve usar um identificador IANA válido") from error
    return normalized


def resolve_project_country_config_by_name(country_name: str | None) -> ProjectCountryConfig | None:
    if country_name is None:
        return None
    normalized_name = normalize_project_country_name(country_name).casefold()
    for config in SUPPORTED_PROJECT_COUNTRIES.values():
        if config.country_name.casefold() == normalized_name:
            return config
    return None


def derive_project_country_code(country_name: str, country_code: str | None = None) -> str:
    normalized_country_code = normalize_optional_project_country_code(country_code)
    if normalized_country_code is not None:
        return normalized_country_code

    known_config = resolve_project_country_config_by_name(country_name)
    if known_config is not None:
        return known_config.country_code

    normalized_country_name = normalize_project_country_name(country_name)
    ascii_letters = "".join(
        character
        for character in unicodedata.normalize("NFD", normalized_country_name)
        if character.isascii() and character.isalpha()
    ).upper()
    if len(ascii_letters) >= 2:
        return ascii_letters[:2]
    if len(ascii_letters) == 1:
        return f"{ascii_letters}X"
    return DEFAULT_PROJECT_COUNTRY_CODE


def list_supported_project_countries() -> list[ProjectCountryConfig]:
    return [SUPPORTED_PROJECT_COUNTRIES[key] for key in sorted(SUPPORTED_PROJECT_COUNTRIES)]


def resolve_project_country_config(country_code: str | None = None) -> ProjectCountryConfig:
    if country_code is None:
        return SUPPORTED_PROJECT_COUNTRIES[DEFAULT_PROJECT_COUNTRY_CODE]
    return SUPPORTED_PROJECT_COUNTRIES[normalize_project_country_code(country_code)]


def build_project_fields_for_country(country_code: str | None = None) -> dict[str, str]:
    config = resolve_project_country_config(country_code)
    return {
        "country_code": config.country_code,
        "country_name": config.country_name,
        "timezone_name": config.timezone_name,
    }


def build_project_fields(
    *,
    country_name: str,
    timezone_name: str,
    country_code: str | None = None,
) -> dict[str, str]:
    normalized_country_name = normalize_project_country_name(country_name)
    normalized_timezone_name = normalize_project_timezone_name(timezone_name)
    return {
        "country_code": derive_project_country_code(normalized_country_name, country_code),
        "country_name": normalized_country_name,
        "timezone_name": normalized_timezone_name,
    }


def normalize_project_country_payload(
    *,
    country_code: str | None = None,
    country_name: str | None = None,
    timezone_name: str | None = None,
) -> dict[str, str]:
    normalized_country_name = " ".join(str(country_name or "").strip().split())
    normalized_timezone_name = str(timezone_name or "").strip()
    if normalized_country_name or normalized_timezone_name:
        if not normalized_country_name or not normalized_timezone_name:
            raise ValueError("Informe país e fuso horário do projeto em conjunto")
        return build_project_fields(
            country_name=normalized_country_name,
            timezone_name=normalized_timezone_name,
            country_code=country_code,
        )
    return build_project_fields_for_country(country_code)


def list_projects(db: Session) -> list[Project]:
    return db.execute(select(Project).order_by(Project.name, Project.id)).scalars().all()


def list_project_names(db: Session) -> list[str]:
    return [row.name for row in list_projects(db)]


def get_project_by_name(db: Session, project_name: str) -> Project | None:
    normalized_name = normalize_project_name(project_name)
    return db.execute(select(Project).where(Project.name == normalized_name)).scalar_one_or_none()


def ensure_known_project(db: Session, project_name: str, *, detail: str = "Projeto nao encontrado.") -> str:
    normalized_name = normalize_project_name(project_name)
    if get_project_by_name(db, normalized_name) is None:
        raise HTTPException(status_code=422, detail=detail)
    return normalized_name


def resolve_default_project_name(db: Session) -> str:
    project_names = list_project_names(db)
    if project_names:
        return project_names[0]
    return DEFAULT_PROJECT_NAMES[0]


def seed_default_projects() -> None:
    with SessionLocal() as db:
        if db.bind is None:
            return

        try:
            inspector = inspect(db.bind)
        except Exception:
            return

        if not inspector.has_table("projects"):
            return

        existing_names = list_project_names(db)
        if existing_names:
            return

        default_fields = build_project_fields_for_country(DEFAULT_PROJECT_COUNTRY_CODE)
        for project_name in DEFAULT_PROJECT_NAMES:
            db.add(Project(name=project_name, **default_fields))
        db.commit()