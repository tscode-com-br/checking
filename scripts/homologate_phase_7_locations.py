from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_REPORT_PATH = PROJECT_ROOT / "docs" / "context" / "fase_7_homologacao_localizacao_poligonal_web.md"
TEMP_DIR = tempfile.mkdtemp(prefix="checkcheck-phase7-")
DATABASE_PATH = Path(TEMP_DIR) / "phase_7_homologation.db"
TRANSPORT_EXPORTS_DIR = Path(TEMP_DIR) / "transport_exports"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run phase 7 homologation scenarios for polygon-based web location matching.",
    )
    parser.add_argument(
        "--output",
        help="Optional markdown report path. Defaults to docs/context/fase_7_homologacao_localizacao_poligonal_web.md.",
    )
    return parser


ARGS = build_argument_parser().parse_args()
REPORT_PATH = Path(ARGS.output).resolve() if ARGS.output else DEFAULT_REPORT_PATH

os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{DATABASE_PATH.as_posix()}"
os.environ["FORMS_URL"] = "https://example.com/form"
os.environ["DEVICE_SHARED_KEY"] = "device-test-key"
os.environ["MOBILE_APP_SHARED_KEY"] = "mobile-test-key"
os.environ["PROVIDER_SHARED_KEY"] = "PETROBRASP80P82P83"
os.environ["ADMIN_SESSION_SECRET"] = "phase-7-admin-session-secret"
os.environ["BOOTSTRAP_ADMIN_KEY"] = "HR70"
os.environ["BOOTSTRAP_ADMIN_NAME"] = "Tamer Salmem"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "eAcacdLe2"
os.environ["FORMS_QUEUE_ENABLED"] = "false"
os.environ["TRANSPORT_EXPORTS_DIR"] = str(TRANSPORT_EXPORTS_DIR)

from fastapi.testclient import TestClient
from sqlalchemy import select

from sistema.app.main import app
from sistema.app.database import SessionLocal
from sistema.app.models import ManagedLocation, Project, User
from sistema.app.services.location_geometry import (
    build_location_geometry,
    project_singapore_meters_to_wgs84,
)
from sistema.app.services.time_utils import now_sgt
from sistema.app.services.user_sync import find_user_by_chave


ADMIN_LOGIN_CHAVE = "HR70"
ADMIN_LOGIN_SENHA = "eAcacdLe2"
LOCATION_MATCHING_LOGGER = "sistema.app.services.location_matching"


@dataclass(frozen=True)
class ControlledLocation:
    project: str
    local: str
    coordinate_count: int
    tolerance_meters: int
    purpose: str


@dataclass(frozen=True)
class ItemResult:
    item: str
    status: str
    title: str
    evidence: str


class LogCapture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def ensure_project_exists(project_name: str) -> None:
    normalized_name = str(project_name).strip().upper()
    with SessionLocal() as db:
        existing = db.execute(select(Project).where(Project.name == normalized_name)).scalar_one_or_none()
        if existing is not None:
            return
        db.add(Project(name=normalized_name))
        db.commit()


def ensure_web_user_exists(*, chave: str, projeto: str, nome: str) -> None:
    with SessionLocal() as db:
        existing = find_user_by_chave(db, chave)
        if existing is not None:
            return
        db.add(
            User(
                rfid=None,
                nome=nome,
                chave=chave,
                projeto=projeto,
                workplace=None,
                placa=None,
                end_rua=None,
                zip=None,
                cargo=None,
                email=None,
                local=None,
                checkin=None,
                time=None,
                last_active_at=now_sgt(),
                inactivity_days=0,
            )
        )
        db.commit()


def build_rectangle_coordinates(
    latitude: float,
    longitude: float,
    *,
    latitude_delta: float = 0.0002,
    longitude_delta: float = 0.0002,
) -> list[dict[str, float]]:
    base_latitude = float(latitude)
    base_longitude = float(longitude)
    return [
        {"latitude": base_latitude, "longitude": base_longitude},
        {"latitude": base_latitude + latitude_delta, "longitude": base_longitude},
        {"latitude": base_latitude + latitude_delta, "longitude": base_longitude + longitude_delta},
        {"latitude": base_latitude, "longitude": base_longitude + longitude_delta},
    ]


def ensure_admin_session(client: TestClient) -> None:
    session_response = client.get("/api/admin/auth/session")
    if session_response.status_code != 200:
        raise RuntimeError(f"Admin session check failed: {session_response.text}")
    if session_response.json().get("authenticated"):
        return
    login_response = client.post(
        "/api/admin/auth/login",
        json={"chave": ADMIN_LOGIN_CHAVE, "senha": ADMIN_LOGIN_SENHA},
    )
    if login_response.status_code != 200:
        raise RuntimeError(f"Admin login failed: {login_response.text}")


def logout_web_user(client: TestClient) -> None:
    client.post("/api/web/auth/logout")


def register_web_password(
    client: TestClient,
    *,
    chave: str,
    projeto: str,
    senha: str,
    nome: str,
) -> None:
    ensure_web_user_exists(chave=chave, projeto=projeto, nome=nome)
    logout_web_user(client)
    register_response = client.post(
        "/api/web/auth/register-password",
        json={"chave": chave, "projeto": projeto, "senha": senha},
    )
    if register_response.status_code == 409:
        login_response = client.post(
            "/api/web/auth/login",
            json={"chave": chave, "senha": senha},
        )
        if login_response.status_code != 200:
            raise RuntimeError(f"Web login failed for {chave}: {login_response.text}")
        return
    if register_response.status_code != 200:
        raise RuntimeError(f"Web password registration failed for {chave}: {register_response.text}")


def set_location_accuracy_threshold(client: TestClient, threshold_meters: int) -> None:
    response = client.post(
        "/api/admin/locations/settings",
        json={"location_accuracy_threshold_meters": threshold_meters},
    )
    if response.status_code != 200:
        raise RuntimeError(f"Updating location settings failed: {response.text}")


def create_location(
    client: TestClient,
    *,
    local: str,
    coordinates: list[dict[str, float]],
    project: str,
    tolerance_meters: int,
) -> None:
    response = client.post(
        "/api/admin/locations",
        json={
            "local": local,
            "coordinates": coordinates,
            "projects": [project],
            "tolerance_meters": tolerance_meters,
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"Creating location {local} failed: {response.text}")


def fetch_location_by_name(local: str) -> ManagedLocation:
    with SessionLocal() as db:
        location = db.execute(select(ManagedLocation).where(ManagedLocation.local == local)).scalar_one_or_none()
        if location is None:
            raise RuntimeError(f"Location {local} was not found in the homologation catalog.")
        return location


def build_left_edge_payload(*, local: str, accuracy_meters: float, extra_offset_meters: float) -> dict[str, float]:
    location = fetch_location_by_name(local)
    geometry = build_location_geometry(location=location)
    min_x, _, _, _ = geometry.expanded_polygon.bounds
    _, min_y, _, max_y = geometry.base_polygon.bounds
    center_y = float((min_y + max_y) / 2.0)
    center_x = float(min_x - accuracy_meters - extra_offset_meters)
    latitude, longitude = project_singapore_meters_to_wgs84(
        x_coordinate=center_x,
        y_coordinate=center_y,
    )
    return {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy_meters": float(accuracy_meters),
    }


def call_web_match(
    client: TestClient,
    *,
    chave: str,
    projeto: str,
    senha: str,
    payload: dict[str, float],
    nome: str,
    capture_logs: bool = False,
) -> tuple[dict, list[str]]:
    register_web_password(client, chave=chave, projeto=projeto, senha=senha, nome=nome)
    logger = logging.getLogger(LOCATION_MATCHING_LOGGER)
    previous_level = logger.level
    handler = LogCapture()
    logs: list[str] = []
    if capture_logs:
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    try:
        response = client.post("/api/web/check/location", json=payload)
    finally:
        if capture_logs:
            logger.removeHandler(handler)
            logger.setLevel(previous_level)
            logs = list(handler.messages)
    if response.status_code != 200:
        raise RuntimeError(f"Web location match failed for {chave}: {response.text}")
    return response.json(), logs


def format_distance(distance_meters: float | None) -> str:
    if distance_meters is None:
        return "n/a"
    return f"{distance_meters:.2f} m"


def render_markdown(
    *,
    generated_at: str,
    controlled_locations: list[ControlledLocation],
    item_results: list[ItemResult],
    audit_summary: dict,
    audit_row_count: int,
    decision_logs: list[str],
) -> str:
    automatic_results = [result for result in item_results if result.item in {"7.2", "7.3", "7.4", "7.5", "7.6", "7.7", "7.8", "7.12"}]
    automatic_passes = sum(1 for result in automatic_results if result.status == "aprovado")
    lines = [
        "# Fase 7 - homologacao funcional da localizacao poligonal no webapp",
        "",
        "## 1. Resumo da execucao",
        "",
        f"- Script executado: `scripts/homologate_phase_7_locations.py`.",
        f"- Gerado em: `{generated_at}`.",
        "- Ambiente: SQLite temporario isolado criado apenas para a homologacao automatizada.",
        f"- Resultado automatico: `{automatic_passes}/{len(automatic_results)}` cenarios automaveis aprovados.",
        "- Escopo manual pendente: itens `7.9` e `7.10`, que dependem de usuarios de negocio e uso guiado do admin.",
        "",
        "## 2. Conjunto controlado preparado",
        "",
        "| Projeto | Local | Vertices | Tolerancia (m) | Finalidade |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for location in controlled_locations:
        lines.append(
            f"| {location.project} | {location.local} | {location.coordinate_count} | {location.tolerance_meters} | {location.purpose} |"
        )

    lines.extend(
        [
            "",
            "## 3. Resultado por item da Fase 7",
            "",
            "| Item | Status | Evidencia |",
            "| --- | --- | --- |",
        ]
    )
    for result in item_results:
        lines.append(f"| {result.item} | {result.status} | {result.title}: {result.evidence} |")

    lines.extend(
        [
            "",
            "## 4. Auditoria do conjunto controlado",
            "",
            f"- Linhas auditadas: `{audit_row_count}`.",
            f"- Localizacoes com erro: `{audit_summary['locations_with_errors']}`.",
            f"- Localizacoes apenas com warning: `{audit_summary['locations_with_warnings_only']}`.",
            f"- Total de zonas de checkout: `{audit_summary['checkout_zone_locations']}`.",
            f"- Contagem de issues: `{audit_summary['issue_counts']}`.",
            "",
            "## 5. Evidencia de logs de decisao geometrica",
            "",
            "```text",
        ]
    )
    if decision_logs:
        lines.extend(decision_logs)
    else:
        lines.append("Nenhum log de decisao foi capturado.")
    lines.extend(
        [
            "```",
            "",
            "## 6. Pendencias humanas para concluir a homologacao em campo",
            "",
            "- Item 7.9: validar com usuarios de negocio, em local fisico real, se a area interpretada pelo poligono corresponde ao perimetro operacional esperado.",
            "- Item 7.10: pedir que um usuario administrativo monte e reordene vertices no admin sem assistencia tecnica, registrando se a ordem dos vertices ficou compreensivel.",
            "- Item 7.11 no catalogo real: repetir a auditoria no ambiente alvo antes do corte, porque este relatorio cobre apenas o conjunto controlado usado na homologacao automatizada.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    controlled_locations: list[ControlledLocation] = []
    item_results: list[ItemResult] = []

    if REPORT_PATH.exists():
        REPORT_PATH.unlink()

    try:
        with TestClient(app) as client:
            ensure_admin_session(client)

            ensure_project_exists("H71")
            create_location(
                client,
                local="Homolog Dentro H71",
                coordinates=build_rectangle_coordinates(1.255936, 103.611066),
                project="H71",
                tolerance_meters=150,
            )
            controlled_locations.append(
                ControlledLocation(
                    project="H71",
                    local="Homolog Dentro H71",
                    coordinate_count=4,
                    tolerance_meters=150,
                    purpose="cenario base de usuario claramente dentro da area",
                )
            )
            set_location_accuracy_threshold(client, 25)
            payload, _ = call_web_match(
                client,
                chave="H711",
                projeto="H71",
                senha="h71123",
                nome="Homolog 7.2",
                payload={"latitude": 1.255936, "longitude": 103.611066, "accuracy_meters": 8.0},
            )
            item_results.append(
                ItemResult(
                    item="7.2",
                    status="aprovado" if payload["matched"] and payload["status"] == "matched" else "falhou",
                    title="Usuario claramente dentro da area",
                    evidence=(
                        f"status={payload['status']}; label={payload['label']}; resolved_local={payload['resolved_local']}"
                    ),
                )
            )

            ensure_project_exists("H72")
            create_location(
                client,
                local="Homolog Fora H72",
                coordinates=build_rectangle_coordinates(1.265936, 103.621066),
                project="H72",
                tolerance_meters=25,
            )
            controlled_locations.append(
                ControlledLocation(
                    project="H72",
                    local="Homolog Fora H72",
                    coordinate_count=4,
                    tolerance_meters=25,
                    purpose="cenario de usuario claramente fora da area expandida",
                )
            )
            set_location_accuracy_threshold(client, 25)
            payload, _ = call_web_match(
                client,
                chave="H721",
                projeto="H72",
                senha="h72123",
                nome="Homolog 7.3",
                payload=build_left_edge_payload(local="Homolog Fora H72", accuracy_meters=8.0, extra_offset_meters=25.0),
            )
            item_results.append(
                ItemResult(
                    item="7.3",
                    status="aprovado" if (not payload["matched"] and payload["status"] == "not_in_known_location") else "falhou",
                    title="Usuario claramente fora da area",
                    evidence=(
                        f"status={payload['status']}; label={payload['label']}; nearest={format_distance(payload['nearest_workplace_distance_meters'])}"
                    ),
                )
            )

            ensure_project_exists("H73")
            create_location(
                client,
                local="Homolog Borda H73",
                coordinates=build_rectangle_coordinates(1.275936, 103.631066),
                project="H73",
                tolerance_meters=25,
            )
            controlled_locations.append(
                ControlledLocation(
                    project="H73",
                    local="Homolog Borda H73",
                    coordinate_count=4,
                    tolerance_meters=25,
                    purpose="cenario de tangencia na borda do poligono expandido",
                )
            )
            set_location_accuracy_threshold(client, 20)
            payload, _ = call_web_match(
                client,
                chave="H731",
                projeto="H73",
                senha="h73123",
                nome="Homolog 7.4",
                payload=build_left_edge_payload(local="Homolog Borda H73", accuracy_meters=8.0, extra_offset_meters=-0.05),
            )
            item_results.append(
                ItemResult(
                    item="7.4",
                    status="aprovado" if payload["matched"] and payload["status"] == "matched" else "falhou",
                    title="Usuario na borda da area expandida",
                    evidence=(
                        f"status={payload['status']}; label={payload['label']}; resolved_local={payload['resolved_local']}"
                    ),
                )
            )

            ensure_project_exists("H74")
            create_location(
                client,
                local="Homolog Precisao H74",
                coordinates=build_rectangle_coordinates(1.285936, 103.641066),
                project="H74",
                tolerance_meters=120,
            )
            controlled_locations.append(
                ControlledLocation(
                    project="H74",
                    local="Homolog Precisao H74",
                    coordinate_count=4,
                    tolerance_meters=120,
                    purpose="cenario de rejeicao por baixa qualidade do GPS",
                )
            )
            set_location_accuracy_threshold(client, 15)
            payload, _ = call_web_match(
                client,
                chave="H741",
                projeto="H74",
                senha="h74123",
                nome="Homolog 7.5",
                payload={"latitude": 1.285936, "longitude": 103.641066, "accuracy_meters": 44.0},
            )
            item_results.append(
                ItemResult(
                    item="7.5",
                    status="aprovado" if payload["status"] == "accuracy_too_low" else "falhou",
                    title="Baixa precisao GPS rejeitada pelo limite global",
                    evidence=(
                        f"status={payload['status']}; label={payload['label']}; threshold={payload['accuracy_threshold_meters']}"
                    ),
                )
            )

            ensure_project_exists("H75")
            create_location(
                client,
                local="Homolog Multiplo A H75",
                coordinates=[
                    {"latitude": 1.255800, "longitude": 103.611000},
                    {"latitude": 1.256100, "longitude": 103.611000},
                    {"latitude": 1.256100, "longitude": 103.611300},
                    {"latitude": 1.255800, "longitude": 103.611300},
                ],
                project="H75",
                tolerance_meters=120,
            )
            create_location(
                client,
                local="Homolog Multiplo B H75",
                coordinates=[
                    {"latitude": 1.255800, "longitude": 103.611350},
                    {"latitude": 1.256100, "longitude": 103.611350},
                    {"latitude": 1.256100, "longitude": 103.611650},
                    {"latitude": 1.255800, "longitude": 103.611650},
                ],
                project="H75",
                tolerance_meters=120,
            )
            controlled_locations.extend(
                [
                    ControlledLocation(
                        project="H75",
                        local="Homolog Multiplo A H75",
                        coordinate_count=4,
                        tolerance_meters=120,
                        purpose="primeiro poligono do cenario de multiplas interseccoes",
                    ),
                    ControlledLocation(
                        project="H75",
                        local="Homolog Multiplo B H75",
                        coordinate_count=4,
                        tolerance_meters=120,
                        purpose="segundo poligono do cenario de multiplas interseccoes",
                    ),
                ]
            )
            set_location_accuracy_threshold(client, 80)
            payload, _ = call_web_match(
                client,
                chave="H751",
                projeto="H75",
                senha="h75123",
                nome="Homolog 7.6",
                payload={"latitude": 1.255790, "longitude": 103.611010, "accuracy_meters": 70.0},
            )
            item_results.append(
                ItemResult(
                    item="7.6",
                    status="aprovado" if payload["resolved_local"] == "Homolog Multiplo A H75" else "falhou",
                    title="Multiplos poligonos proximos com desempate deterministico",
                    evidence=(
                        f"status={payload['status']}; resolved_local={payload['resolved_local']}; label={payload['label']}"
                    ),
                )
            )

            ensure_project_exists("H76")
            create_location(
                client,
                local="Homolog Proximo H76",
                coordinates=build_rectangle_coordinates(1.295936, 103.651066),
                project="H76",
                tolerance_meters=120,
            )
            controlled_locations.append(
                ControlledLocation(
                    project="H76",
                    local="Homolog Proximo H76",
                    coordinate_count=4,
                    tolerance_meters=120,
                    purpose="cenario de localizacao nao cadastrada ainda dentro do ambiente de trabalho",
                )
            )
            set_location_accuracy_threshold(client, 25)
            payload, _ = call_web_match(
                client,
                chave="H761",
                projeto="H76",
                senha="h76123",
                nome="Homolog 7.7",
                payload={"latitude": 1.300936, "longitude": 103.651066, "accuracy_meters": 8.0},
            )
            item_results.append(
                ItemResult(
                    item="7.7",
                    status="aprovado" if payload["status"] == "not_in_known_location" else "falhou",
                    title="Localizacao nao cadastrada dentro do ambiente de trabalho",
                    evidence=(
                        f"status={payload['status']}; label={payload['label']}; nearest={format_distance(payload['nearest_workplace_distance_meters'])}"
                    ),
                )
            )

            ensure_project_exists("H77")
            create_location(
                client,
                local="Homolog Trabalho Distante H77",
                coordinates=build_rectangle_coordinates(1.285936, 103.611066),
                project="H77",
                tolerance_meters=120,
            )
            create_location(
                client,
                local="Zona de CheckOut",
                coordinates=build_rectangle_coordinates(1.255936, 103.611066),
                project="H77",
                tolerance_meters=20,
            )
            controlled_locations.extend(
                [
                    ControlledLocation(
                        project="H77",
                        local="Homolog Trabalho Distante H77",
                        coordinate_count=4,
                        tolerance_meters=120,
                        purpose="local de trabalho usado para validar a regra acima de 2 km",
                    ),
                    ControlledLocation(
                        project="H77",
                        local="Zona de CheckOut",
                        coordinate_count=4,
                        tolerance_meters=20,
                        purpose="checkout zone proxima que deve ser ignorada no calculo dos 2 km",
                    ),
                ]
            )
            set_location_accuracy_threshold(client, 25)
            payload, _ = call_web_match(
                client,
                chave="H771",
                projeto="H77",
                senha="h77123",
                nome="Homolog 7.8",
                payload={"latitude": 1.257936, "longitude": 103.611066, "accuracy_meters": 8.0},
            )
            item_results.append(
                ItemResult(
                    item="7.8",
                    status="aprovado" if payload["status"] == "outside_workplace" else "falhou",
                    title="Fora do local de trabalho acima de 2 km",
                    evidence=(
                        f"status={payload['status']}; label={payload['label']}; nearest={format_distance(payload['nearest_workplace_distance_meters'])}"
                    ),
                )
            )

            ensure_project_exists("H7L")
            create_location(
                client,
                local="Homolog Regular H7L",
                coordinates=build_rectangle_coordinates(1.265936, 103.621066),
                project="H7L",
                tolerance_meters=90,
            )
            create_location(
                client,
                local="Zona de CheckOut",
                coordinates=build_rectangle_coordinates(1.265956, 103.621086),
                project="H7L",
                tolerance_meters=90,
            )
            controlled_locations.extend(
                [
                    ControlledLocation(
                        project="H7L",
                        local="Homolog Regular H7L",
                        coordinate_count=4,
                        tolerance_meters=90,
                        purpose="local regular usado para captura de logs detalhados",
                    ),
                    ControlledLocation(
                        project="H7L",
                        local="Zona de CheckOut",
                        coordinate_count=4,
                        tolerance_meters=90,
                        purpose="checkout zone usada para validar logs de decisao geometrica",
                    ),
                ]
            )
            set_location_accuracy_threshold(client, 25)
            payload, decision_logs = call_web_match(
                client,
                chave="H7L1",
                projeto="H7L",
                senha="h7l123",
                nome="Homolog 7.12",
                payload={"latitude": 1.266010, "longitude": 103.621120, "accuracy_meters": 8.0},
                capture_logs=True,
            )
            relevant_logs = [
                message
                for message in decision_logs
                if "location_match_decision" in message or "location_match_invalid_polygon_skipped" in message
            ]
            item_results.append(
                ItemResult(
                    item="7.12",
                    status=(
                        "aprovado"
                        if payload["matched"] and any("selection_source=polygon_checkout" in message for message in relevant_logs)
                        else "falhou"
                    ),
                    title="Logs de decisao geometrica revisados durante a homologacao",
                    evidence=(
                        f"status={payload['status']}; label={payload['label']}; logs_capturados={len(relevant_logs)}"
                    ),
                )
            )

            audit_response = client.get("/api/admin/locations/audit", params={"include_valid": "true"})
            if audit_response.status_code != 200:
                raise RuntimeError(f"Location audit request failed: {audit_response.text}")
            audit_payload = audit_response.json()
            audit_summary = audit_payload["summary"]
            audit_row_count = len(audit_payload["rows"])

            item_results.insert(
                0,
                ItemResult(
                    item="7.1",
                    status="parcial",
                    title="Conjunto controlado preparado para homologacao",
                    evidence=(
                        f"{len(controlled_locations)} localizacoes validas criadas em banco isolado; o ambiente atual nao expunha um catalogo real revisado para replicar o item com dados operacionais"
                    ),
                ),
            )
            item_results.append(
                ItemResult(
                    item="7.9",
                    status="pendente manual",
                    title="Validacao com usuarios de negocio sobre a area fisica",
                    evidence="nao executavel no workspace sem deslocamento em campo e sem operador de negocio acompanhando os casos reais",
                )
            )
            item_results.append(
                ItemResult(
                    item="7.10",
                    status="pendente manual",
                    title="Validacao de compreensao da ordem dos vertices no admin",
                    evidence="nao executavel apenas com API e testes automatizados; depende de sessao assistida de UX com quem cadastra localizacoes",
                )
            )
            item_results.append(
                ItemResult(
                    item="7.11",
                    status="parcial" if audit_summary["locations_with_errors"] == 0 else "falhou",
                    title="Correcao de localizacoes problematica antes da ativacao",
                    evidence=(
                        f"auditoria do conjunto controlado retornou errors={audit_summary['locations_with_errors']} e warnings={audit_summary['locations_with_warnings_only']}; o catalogo real do ambiente alvo segue pendente de reauditoria antes do corte"
                    ),
                )
            )

            report_content = render_markdown(
                generated_at=datetime.now(timezone.utc).isoformat(),
                controlled_locations=controlled_locations,
                item_results=item_results,
                audit_summary=audit_summary,
                audit_row_count=audit_row_count,
                decision_logs=relevant_logs,
            )
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            REPORT_PATH.write_text(report_content, encoding="utf-8")

            automatic_failures = [
                result
                for result in item_results
                if result.item in {"7.2", "7.3", "7.4", "7.5", "7.6", "7.7", "7.8", "7.12"}
                and result.status != "aprovado"
            ]
            return 1 if automatic_failures else 0
    finally:
        shutil.rmtree(TEMP_DIR, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())