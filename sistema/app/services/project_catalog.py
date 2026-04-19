from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Project


DEFAULT_PROJECT_NAMES = ("P80", "P82", "P83")
PROJECT_NAME_MAX_LENGTH = 120


def normalize_project_name(value: str, *, field_name: str = "O projeto") -> str:
    normalized = " ".join(str(value or "").strip().split()).upper()
    if len(normalized) < 2:
        raise ValueError(f"{field_name} deve ter ao menos 2 caracteres")
    if len(normalized) > PROJECT_NAME_MAX_LENGTH:
        raise ValueError(f"{field_name} deve ter no maximo {PROJECT_NAME_MAX_LENGTH} caracteres")
    return normalized


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

        for project_name in DEFAULT_PROJECT_NAMES:
            db.add(Project(name=project_name))
        db.commit()