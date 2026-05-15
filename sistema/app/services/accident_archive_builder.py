"""Archive builder — generates XLSX + ZIP for a closed accident and stores in object storage.

Called as a background task after an accident is closed.  The resulting archive is
attached to the Accident record (archive_object_key) and an AccidentArchive row is
created with metadata.
"""

from __future__ import annotations

import json
import re
import zipfile
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment
from sqlalchemy import select

from ..database import SessionLocal
from ..models import Accident, AccidentArchive, AccidentVideoUpload
from .accident_numbering import format_accident_number
from .accident_situation_table import build_situation_rows
from .admin_updates import notify_admin_data_changed
from .object_storage import _local_root, _use_remote, upload_stream
from .time_utils import now_sgt


COLUMN_ORDER = [
    "Horário",
    "Nome",
    "Chave",
    "Projetos",
    "Local",
    "Zona de",
    "Situação",
    "Contato",
    "Registros",
]


def _slugify(value: str) -> str:
    """Convert an arbitrary string to a safe filename segment."""
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value)[:60]


def _build_xlsx(snapshot_rows, video_files_by_user: dict[int, list[str]]) -> BytesIO:
    """Build the 'Situação de Pessoal' spreadsheet and return it as a BytesIO."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Situacao de Pessoal"
    ws.append(COLUMN_ORDER)

    for row in snapshot_rows:
        videos = video_files_by_user.get(row.user_id, [])
        registros_text = "\n".join(f"Registros/{filename}" for filename in videos)
        ws.append([
            row.event_time.isoformat(),
            row.name,
            row.chave,
            ", ".join(row.projects),
            row.local or "",
            row.zone,
            row.status,
            row.phone or "",
            registros_text,
        ])
        cell = ws.cell(row=ws.max_row, column=9)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        if videos:
            # Excel supports only one hyperlink per cell — link to first video.
            cell.hyperlink = f"Registros/{videos[0]}"

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def _read_video_bytes(object_key: str) -> bytes:
    """Fetch raw video bytes from storage (local or remote)."""
    if _use_remote():
        from ..core.config import settings
        from .object_storage import _make_boto3_client

        client = _make_boto3_client()
        result = client.get_object(Bucket=settings.do_spaces_bucket, Key=object_key)
        return result["Body"].read()

    target = _local_root() / object_key
    return target.read_bytes() if target.exists() else b""


def build_and_attach_archive_for_accident(accident_id: int) -> None:
    """Build XLSX + ZIP archive for *accident_id*, upload to storage, persist metadata."""
    with SessionLocal() as db:
        accident = db.get(Accident, accident_id)
        if accident is None:
            return

        snapshot_rows = build_situation_rows(db, accident=accident)
        videos = (
            db.execute(
                select(AccidentVideoUpload).where(
                    AccidentVideoUpload.accident_id == accident.id
                )
            )
            .scalars()
            .all()
        )

        # Build user_id -> filenames mapping and fetch raw bytes
        video_files_by_user: dict[int, list[str]] = {}
        video_payloads: dict[str, bytes] = {}
        for video in videos:
            ext = video.content_type.split("/")[-1]
            if ext == "quicktime":
                ext = "mov"
            filename = f"{video.user_id}-{_slugify(video.idempotency_key)}.{ext}"
            video_files_by_user.setdefault(video.user_id, []).append(filename)
            video_payloads[filename] = _read_video_bytes(video.object_key)

        xlsx_buffer = _build_xlsx(snapshot_rows, video_files_by_user)

        # Build ZIP
        zip_buffer = BytesIO()
        xlsx_name = f"{format_accident_number(accident.accident_number)}.xlsx"
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(xlsx_name, xlsx_buffer.getvalue())
            for filename, payload in video_payloads.items():
                zf.writestr(f"Registros/{filename}", payload)
        zip_buffer.seek(0)

        # Upload XLSX and ZIP to storage
        acc_label = format_accident_number(accident.accident_number)
        xlsx_key = f"accidents/{acc_label}/archive/{xlsx_name}"
        zip_key = f"accidents/{acc_label}/archive/{acc_label}.zip"

        upload_stream(
            object_key=xlsx_key,
            stream=BytesIO(xlsx_buffer.getvalue()),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        upload_stream(
            object_key=zip_key,
            stream=zip_buffer,
            content_type="application/zip",
        )

        size_bytes = len(zip_buffer.getvalue())

        archive = AccidentArchive(
            accident_id=accident.id,
            snapshot_json=json.dumps(
                [row.model_dump() for row in snapshot_rows], default=str
            ),
            xlsx_object_key=xlsx_key,
            zip_object_key=zip_key,
            size_bytes=size_bytes,
            generated_at=now_sgt(),
        )
        accident.archive_object_key = zip_key
        db.add(archive)
        db.commit()

    # Re-publish so the UI can refresh with archive_ready=True
    notify_admin_data_changed(
        "accident_closed",
        metadata={"accident_id": accident_id, "archive_ready": True},
    )
