#!/usr/bin/env python3
"""
Accident Mode post-deploy monitoring script.

Runs 3 SQL health checks against the production database and emits
structured log lines (JSON).  On threshold violations, optionally sends
an alert e-mail via the configured SMTP settings.

Designed to run as a cron job every 15 minutes:
    */15 * * * * /opt/checking/.venv/bin/python \
        /opt/checking/scripts/monitor_accident_mode.py \
        --database-url "$DATABASE_URL" \
        >> /var/log/checking/accident_monitor.log 2>&1

Checks performed
----------------
1. EMAIL_FAIL_RATE  — delivery_status='failed' ratio > 5 % in the last 24h.
2. FORGOTTEN_ACCIDENT — any accident with closed_at IS NULL older than 24h.
3. LARGE_ARCHIVE — any accident_archive with size_bytes > 200 MB.

Exit codes
----------
    0   All checks passed (no violations).
    1   One or more threshold violations detected.
    2   Fatal error (DB connection, missing args, etc.).
"""
from __future__ import annotations

import argparse
import json
import smtplib
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

try:
    import sqlalchemy as sa
    from sqlalchemy import text
except ImportError:
    print('{"level":"ERROR","msg":"sqlalchemy not installed"}', flush=True)
    sys.exit(2)


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

EMAIL_FAIL_RATE_THRESHOLD = 0.05      # 5 %
FORGOTTEN_ACCIDENT_HOURS = 24         # hours open before alert
LARGE_ARCHIVE_BYTES = 200 * 1024 * 1024  # 200 MB


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class CheckViolation:
    check: str
    severity: str  # "warning" | "critical"
    message: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckResult:
    check: str
    status: str  # "ok" | "violation" | "error"
    message: str
    violations: list[CheckViolation] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# SQL checks
# ---------------------------------------------------------------------------


def check_email_fail_rate(conn: Any) -> CheckResult:
    """Alert if delivery_status='failed' rate > 5% in last 24h."""
    row = conn.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE delivery_status = 'failed') AS failed_count,
            COUNT(*) AS total_count
        FROM email_delivery_logs
        WHERE queued_at >= NOW() - INTERVAL '24 hours'
    """)).mappings().one()

    failed = int(row["failed_count"] or 0)
    total = int(row["total_count"] or 0)
    rate = (failed / total) if total > 0 else 0.0

    data = {"failed_count": failed, "total_count": total, "fail_rate_pct": round(rate * 100, 1)}

    if total == 0:
        return CheckResult(check="EMAIL_FAIL_RATE", status="ok",
                           message="No emails queued in the last 24h.", data=data)

    if rate > EMAIL_FAIL_RATE_THRESHOLD:
        v = CheckViolation(
            check="EMAIL_FAIL_RATE",
            severity="critical",
            message=f"Email fail rate {rate*100:.1f}% exceeds threshold {EMAIL_FAIL_RATE_THRESHOLD*100:.0f}%.",
            data=data,
        )
        return CheckResult(check="EMAIL_FAIL_RATE", status="violation",
                           message=v.message, violations=[v], data=data)

    return CheckResult(check="EMAIL_FAIL_RATE", status="ok",
                       message=f"Email fail rate {rate*100:.1f}% is within threshold.", data=data)


def check_forgotten_accidents(conn: Any) -> CheckResult:
    """Alert if any accident has been open for > 24h (closed_at IS NULL)."""
    rows = conn.execute(text("""
        SELECT id, accident_number, project_name_snapshot,
               opened_at,
               EXTRACT(EPOCH FROM (NOW() - opened_at)) / 3600.0 AS hours_open
        FROM accidents
        WHERE closed_at IS NULL
          AND opened_at < NOW() - INTERVAL '24 hours'
        ORDER BY opened_at ASC
    """)).mappings().all()

    data = {
        "forgotten_count": len(rows),
        "accidents": [
            {
                "id": int(r["id"]),
                "accident_number": int(r["accident_number"]),
                "project": r["project_name_snapshot"],
                "hours_open": round(float(r["hours_open"]), 1),
            }
            for r in rows
        ],
    }

    if not rows:
        return CheckResult(check="FORGOTTEN_ACCIDENT", status="ok",
                           message="No accidents open > 24h.", data=data)

    v = CheckViolation(
        check="FORGOTTEN_ACCIDENT",
        severity="critical",
        message=f"{len(rows)} accident(s) open for more than {FORGOTTEN_ACCIDENT_HOURS}h without being closed.",
        data=data,
    )
    return CheckResult(check="FORGOTTEN_ACCIDENT", status="violation",
                       message=v.message, violations=[v], data=data)


def check_large_archives(conn: Any) -> CheckResult:
    """Alert if any archive ZIP exceeds 200 MB."""
    rows = conn.execute(text("""
        SELECT aa.id, aa.accident_id, aa.size_bytes,
               a.accident_number, a.project_name_snapshot
        FROM accident_archives aa
        JOIN accidents a ON a.id = aa.accident_id
        WHERE aa.size_bytes > :threshold
        ORDER BY aa.size_bytes DESC
    """), {"threshold": LARGE_ARCHIVE_BYTES}).mappings().all()

    data = {
        "large_archive_count": len(rows),
        "threshold_mb": LARGE_ARCHIVE_BYTES // (1024 * 1024),
        "archives": [
            {
                "archive_id": int(r["id"]),
                "accident_id": int(r["accident_id"]),
                "accident_number": int(r["accident_number"]),
                "project": r["project_name_snapshot"],
                "size_mb": round(int(r["size_bytes"]) / (1024 * 1024), 1),
            }
            for r in rows
        ],
    }

    if not rows:
        return CheckResult(check="LARGE_ARCHIVE", status="ok",
                           message=f"No archives exceed {LARGE_ARCHIVE_BYTES // (1024*1024)} MB.", data=data)

    v = CheckViolation(
        check="LARGE_ARCHIVE",
        severity="warning",
        message=f"{len(rows)} archive(s) exceed {LARGE_ARCHIVE_BYTES // (1024*1024)} MB. Consider increasing storage quota.",
        data=data,
    )
    return CheckResult(check="LARGE_ARCHIVE", status="violation",
                       message=v.message, violations=[v], data=data)


# ---------------------------------------------------------------------------
# Alert e-mail
# ---------------------------------------------------------------------------


def _send_alert_email(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str | None,
    smtp_password: str | None,
    smtp_use_tls: bool,
    smtp_use_starttls: bool,
    from_email: str,
    from_name: str,
    to_email: str,
    subject: str,
    body: str,
) -> None:
    msg = EmailMessage()
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    if smtp_use_tls:
        import ssl
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx, timeout=30) as server:
            if smtp_user:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            if smtp_use_starttls:
                server.starttls()
            if smtp_user:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)


def _build_alert_body(results: list[CheckResult], run_at: str) -> str:
    lines = [
        f"CheckCheck — Accident Mode Monitor",
        f"Run at: {run_at}",
        "",
        "VIOLATIONS DETECTED:",
        "=" * 50,
    ]
    for r in results:
        if r.status == "violation":
            lines.append(f"\n[{r.check}] {r.message}")
            for v in r.violations:
                lines.append(f"  Severity : {v.severity.upper()}")
                lines.append(f"  Data     : {json.dumps(v.data, ensure_ascii=False)}")
    lines += ["", "=" * 50, "Monitor: scripts/monitor_accident_mode.py"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------


def _log(level: str, check: str, status: str, message: str, **extra: Any) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "check": check,
        "status": status,
        "msg": message,
        **extra,
    }
    print(json.dumps(record, ensure_ascii=False), flush=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Accident Mode monitoring checks")
    parser.add_argument("--database-url", required=True, help="SQLAlchemy database URL")
    parser.add_argument("--alert-email", default=None,
                        help="Recipient for violation alert e-mails")
    parser.add_argument("--smtp-host", default=None)
    parser.add_argument("--smtp-port", type=int, default=587)
    parser.add_argument("--smtp-user", default=None)
    parser.add_argument("--smtp-password", default=None)
    parser.add_argument("--smtp-from-email", default="monitor@checkcheck.local")
    parser.add_argument("--smtp-from-name", default="CheckCheck Monitor")
    parser.add_argument("--smtp-use-tls", action="store_true")
    parser.add_argument("--smtp-use-starttls", action="store_true", default=True)
    args = parser.parse_args()

    run_at = datetime.now(timezone.utc).isoformat()
    violations_found = False

    try:
        engine = sa.create_engine(args.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            checks = [
                check_email_fail_rate(conn),
                check_forgotten_accidents(conn),
                check_large_archives(conn),
            ]
    except Exception as exc:
        _log("ERROR", "DB_CONNECT", "error", str(exc)[:300])
        return 2

    for result in checks:
        level = "INFO" if result.status == "ok" else "WARNING"
        _log(level, result.check, result.status, result.message, **result.data)
        if result.violations:
            violations_found = True

    # Send alert e-mail if violations and SMTP configured
    if violations_found and args.alert_email and args.smtp_host:
        violation_names = [r.check for r in checks if r.violations]
        subject = f"[CheckCheck] Accident Monitor ALERT: {', '.join(violation_names)}"
        body = _build_alert_body(checks, run_at)
        try:
            _send_alert_email(
                smtp_host=args.smtp_host,
                smtp_port=args.smtp_port,
                smtp_user=args.smtp_user,
                smtp_password=args.smtp_password,
                smtp_use_tls=args.smtp_use_tls,
                smtp_use_starttls=args.smtp_use_starttls,
                from_email=args.smtp_from_email,
                from_name=args.smtp_from_name,
                to_email=args.alert_email,
                subject=subject,
                body=body,
            )
            _log("INFO", "ALERT_EMAIL", "sent", f"Alert sent to {args.alert_email}")
        except Exception as exc:
            _log("ERROR", "ALERT_EMAIL", "error", f"Failed to send alert: {exc}")

    return 1 if violations_found else 0


if __name__ == "__main__":
    sys.exit(main())
