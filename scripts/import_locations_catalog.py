from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sistema.app.core.config import settings
from sistema.app.database import SessionLocal
from sistema.app.models import ManagedLocation


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import the managed locations catalog from a SQLite database into the configured application database.",
    )
    parser.add_argument(
        "--source",
        default="test_checking.db",
        help="Path to the source SQLite database. Defaults to test_checking.db.",
    )
    parser.add_argument(
        "--allow-sqlite-target",
        action="store_true",
        help="Allow importing into a SQLite target database. Disabled by default to avoid clobbering the local dev DB by accident.",
    )
    return parser


def _parse_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        timestamp = datetime.fromisoformat(value)
    else:
        raise ValueError(f"Unsupported timestamp value: {value!r}")

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp


def _load_source_rows(source_path: Path) -> list[dict[str, object]]:
    if not source_path.exists():
        raise FileNotFoundError(f"Source SQLite database not found: {source_path}")

    connection = sqlite3.connect(source_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT id, local, latitude, longitude, coordinates_json, projects_json,
                   tolerance_meters, created_at, updated_at
            FROM locations
            ORDER BY id
            """
        ).fetchall()
    finally:
        connection.close()

    return [dict(row) for row in rows]


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    database_url = settings.database_url
    if database_url.startswith("sqlite") and not args.allow_sqlite_target:
        parser.error(
            "Refusing to import into a SQLite target database. Set DATABASE_URL to the Compose Postgres database or pass --allow-sqlite-target."
        )

    source_rows = _load_source_rows(Path(args.source))
    if not source_rows:
        parser.error("The source SQLite database does not contain any rows in locations.")

    imported_count = 0
    with SessionLocal() as db:
        db.execute(text("DELETE FROM locations"))
        for row in source_rows:
            db.add(
                ManagedLocation(
                    id=int(row["id"]),
                    local=str(row["local"]),
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    coordinates_json=row["coordinates_json"],
                    projects_json=row["projects_json"],
                    tolerance_meters=int(row["tolerance_meters"]),
                    created_at=_parse_timestamp(row["created_at"]),
                    updated_at=_parse_timestamp(row["updated_at"]),
                )
            )

        db.flush()
        db.execute(
            text(
                "SELECT setval(pg_get_serial_sequence('locations', 'id'), COALESCE((SELECT MAX(id) FROM locations), 1), true)"
            )
        )
        imported_count = db.query(ManagedLocation).count()
        db.commit()

    print(f"source_rows={len(source_rows)}")
    print(f"imported_rows={imported_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())