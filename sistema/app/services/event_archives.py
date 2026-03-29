from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass
from datetime import datetime
from math import ceil
from pathlib import Path

from ..core.config import settings
from ..models import CheckEvent

CSV_HEADERS = [
    "id",
    "event_time",
    "source",
    "action",
    "status",
    "message",
    "details",
    "device_id",
    "local",
    "rfid",
    "project",
    "http_status",
    "request_path",
    "retry_count",
]


@dataclass
class EventArchiveInfo:
    file_name: str
    period: str
    record_count: int
    size_bytes: int
    created_at: datetime


@dataclass
class EventArchivePage:
    items: list[EventArchiveInfo]
    total: int
    total_size_bytes: int
    page: int
    page_size: int
    total_pages: int
    query: str


def ensure_event_archives_dir() -> Path:
    archive_dir = Path(settings.event_archives_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir


def _format_period_timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H-%M-%S")


def _normalize_file_name(file_name: str) -> str:
    normalized = Path(file_name).name
    if normalized != file_name or not normalized.endswith(".csv"):
        raise FileNotFoundError(file_name)
    return normalized


def _build_period(start_at: datetime, end_at: datetime) -> str:
    return f"{_format_period_timestamp(start_at)} a {_format_period_timestamp(end_at)}"


def _unique_archive_path(period: str) -> Path:
    archive_dir = ensure_event_archives_dir()
    base_name = f"{period}.csv"
    archive_path = archive_dir / base_name
    if not archive_path.exists():
        return archive_path

    suffix = 2
    while True:
        candidate = archive_dir / f"{period} ({suffix}).csv"
        if not candidate.exists():
            return candidate
        suffix += 1


def _row_to_csv(event: CheckEvent) -> list[str | int | None]:
    return [
        event.id,
        event.event_time.isoformat() if event.event_time else None,
        event.source,
        event.action,
        event.status,
        event.message,
        event.details,
        event.device_id,
        event.local,
        event.rfid,
        event.project,
        event.http_status,
        event.request_path,
        event.retry_count,
    ]


def create_event_archive(events: list[CheckEvent]) -> EventArchiveInfo | None:
    if not events:
        return None

    sorted_events = sorted(events, key=lambda event: (event.event_time, event.id))
    period = _build_period(sorted_events[0].event_time, sorted_events[-1].event_time)
    archive_path = _unique_archive_path(period)

    with archive_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(CSV_HEADERS)
        for event in sorted_events:
            writer.writerow(_row_to_csv(event))

    return get_event_archive_info(archive_path.name)


def get_event_archive_path(file_name: str) -> Path:
    normalized = _normalize_file_name(file_name)
    archive_path = ensure_event_archives_dir() / normalized
    if not archive_path.exists() or not archive_path.is_file():
        raise FileNotFoundError(file_name)
    return archive_path


def delete_event_archive(file_name: str) -> None:
    archive_path = get_event_archive_path(file_name)
    archive_path.unlink()


def get_event_archive_info(file_name: str) -> EventArchiveInfo:
    archive_path = get_event_archive_path(file_name)
    stat = archive_path.stat()

    with archive_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        row_count = max(sum(1 for _ in csv_file) - 1, 0)

    return EventArchiveInfo(
        file_name=archive_path.name,
        period=archive_path.stem,
        record_count=row_count,
        size_bytes=stat.st_size,
        created_at=datetime.fromtimestamp(stat.st_mtime),
    )


def list_event_archives() -> list[EventArchiveInfo]:
    archive_dir = ensure_event_archives_dir()
    archive_paths = sorted(archive_dir.glob("*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    return [get_event_archive_info(path.name) for path in archive_paths]


def list_event_archives_page(*, query: str = "", page: int = 1, page_size: int = 8) -> EventArchivePage:
    normalized_query = query.strip().lower()
    all_items = list_event_archives()
    total_size_bytes = sum(item.size_bytes for item in all_items)
    filtered_items = all_items
    if normalized_query:
        filtered_items = [item for item in all_items if normalized_query in item.period.lower()]

    total = len(filtered_items)
    safe_page_size = max(1, page_size)
    total_pages = ceil(total / safe_page_size) if total else 0
    safe_page = max(1, page)
    if total_pages and safe_page > total_pages:
        safe_page = total_pages

    start = (safe_page - 1) * safe_page_size if total else 0
    end = start + safe_page_size

    return EventArchivePage(
        items=filtered_items[start:end],
        total=total,
        total_size_bytes=total_size_bytes,
        page=safe_page,
        page_size=safe_page_size,
        total_pages=total_pages,
        query=query,
    )


def build_event_archives_zip() -> tuple[str, bytes]:
    archives = list_event_archives()
    if not archives:
        raise FileNotFoundError("no event archives available")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for archive in archives:
            archive_path = get_event_archive_path(archive.file_name)
            zip_file.write(archive_path, arcname=archive.file_name)

    zip_name = f"eventos-archives-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.zip"
    return zip_name, buffer.getvalue()