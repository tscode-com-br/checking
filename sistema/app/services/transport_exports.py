from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from openpyxl import Workbook
from sqlalchemy.orm import Session

from ..core.config import settings
from ..schemas import TransportDashboardResponse, TransportRequestRow
from .time_utils import now_sgt
from .transport import build_transport_dashboard

TRANSPORT_EXPORT_HEADERS = [
    "Nome/Name",
    "Chave/Key",
    "Projeto/Project",
    "Endereço/Address",
    "Data/Date",
    "Partida/Departure",
]


@dataclass
class TransportExportFile:
    download_name: str
    storage_path: Path
    row_count: int


def ensure_transport_exports_dir() -> Path:
    export_dir = Path(settings.transport_exports_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def _build_download_name(timestamp: datetime) -> str:
    return f"Transport List - {timestamp.strftime('%Y%m%d')} - {timestamp.strftime('%H%M%S')}.xlsx"


def _unique_export_path(download_name: str) -> Path:
    export_dir = ensure_transport_exports_dir()
    base_path = export_dir / download_name
    if not base_path.exists():
        return base_path

    stem = Path(download_name).stem
    suffix = Path(download_name).suffix
    counter = 2
    while True:
        candidate = export_dir / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _collect_confirmed_rows(dashboard: TransportDashboardResponse) -> list[TransportRequestRow]:
    confirmed_rows = [
        row
        for row in [
            *dashboard.regular_requests,
            *dashboard.weekend_requests,
            *dashboard.extra_requests,
        ]
        if row.assignment_status == "confirmed"
    ]
    confirmed_rows.sort(key=lambda item: (item.service_date, item.nome.lower(), item.chave))
    return confirmed_rows


def _append_headers(worksheet) -> None:
    for column_index, header in enumerate(TRANSPORT_EXPORT_HEADERS, start=1):
        worksheet.cell(row=1, column=column_index, value=header)


def _append_rows(worksheet, rows: list[TransportRequestRow]) -> None:
    for row_index, request_row in enumerate(rows, start=2):
        worksheet.cell(row=row_index, column=1, value=request_row.nome)
        worksheet.cell(row=row_index, column=2, value=request_row.chave)
        worksheet.cell(row=row_index, column=3, value=request_row.projeto)
        worksheet.cell(row=row_index, column=4, value=request_row.end_rua or "")
        worksheet.cell(row=row_index, column=5, value=request_row.service_date.isoformat())
        worksheet.cell(row=row_index, column=6, value="")


def create_transport_list_export(
    db: Session,
    *,
    service_date: date,
    route_kind: Literal["home_to_work", "work_to_home"],
) -> TransportExportFile:
    timestamp = now_sgt()
    download_name = _build_download_name(timestamp)
    storage_path = _unique_export_path(download_name)
    dashboard = build_transport_dashboard(db, service_date=service_date, route_kind=route_kind)
    rows = _collect_confirmed_rows(dashboard)

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Transport List"
    _append_headers(worksheet)
    _append_rows(worksheet, rows)
    workbook.save(storage_path)
    workbook.close()

    return TransportExportFile(download_name=download_name, storage_path=storage_path, row_count=len(rows))