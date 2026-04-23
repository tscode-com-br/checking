from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sistema.app.database import SessionLocal
from sistema.app.services.location_audit import audit_locations_from_db, build_location_audit_text


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit stored locations and flag records that need cleanup before polygon matching is enabled.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Defaults to text.",
    )
    parser.add_argument(
        "--output",
        help="Optional path where the report should be written.",
    )
    parser.add_argument(
        "--include-valid",
        action="store_true",
        help="Include locations without issues in text output.",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Return exit code 2 when only warnings are present.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        report = audit_locations_from_db(db)

    if args.format == "json":
        content = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    else:
        content = build_location_audit_text(report, include_valid=args.include_valid)

    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
    else:
        print(content)

    if report.summary.locations_with_errors:
        return 1
    if args.fail_on_warnings and report.summary.locations_with_warnings_only:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())