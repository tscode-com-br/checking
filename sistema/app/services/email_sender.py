"""E-mail queue and delivery service for accident help-request notifications."""
import smtplib
import ssl
from email.message import EmailMessage

from sqlalchemy import select

from ..core.config import settings
from ..database import SessionLocal
from ..models import Accident, EmailDeliveryLog, Project, User, UserProjectMembership
from .email_templates import render_help_request_email
from .time_utils import now_sgt


def queue_help_request_emails(*, accident_id: int, requester_user_id: int) -> None:
    """Enfileira (persiste em EmailDeliveryLog) e dispara entrega imediata."""
    with SessionLocal() as db:
        accident = db.get(Accident, accident_id)
        requester = db.get(User, requester_user_id)
        if accident is None or requester is None:
            return

        recipients = (
            db.execute(
                select(User)
                .join(UserProjectMembership, UserProjectMembership.user_id == User.id)
                .join(Project, Project.id == UserProjectMembership.project_id)
                .where(Project.name == accident.project_name_snapshot)
            )
            .scalars()
            .unique()
            .all()
        )

        log_ids: list[int] = []
        for recipient in recipients:
            subject, body = render_help_request_email(
                recipient_name=recipient.nome,
                requester_name=requester.nome,
                requester_chave=requester.chave,
                project_name=accident.project_name_snapshot,
                location_name=accident.location_name_snapshot,
            )
            if not recipient.email:
                log = EmailDeliveryLog(
                    accident_id=accident.id,
                    triggered_by_user_id=requester.id,
                    recipient_email="",
                    recipient_chave=recipient.chave,
                    subject=subject,
                    body_snapshot=body,
                    delivery_status="failed",
                    error_message="Missing recipient email",
                    queued_at=now_sgt(),
                )
                db.add(log)
                continue
            log = EmailDeliveryLog(
                accident_id=accident.id,
                triggered_by_user_id=requester.id,
                recipient_email=recipient.email,
                recipient_chave=recipient.chave,
                subject=subject,
                body_snapshot=body,
                delivery_status="queued",
                queued_at=now_sgt(),
            )
            db.add(log)
            db.flush()
            log_ids.append(log.id)
        db.commit()

    deliver_pending_emails(log_ids)


def deliver_pending_emails(log_ids: list[int]) -> None:
    """Attempt SMTP delivery for the given log IDs; no-op when SMTP is disabled."""
    if not settings.smtp_host:
        return
    with SessionLocal() as db:
        for log_id in log_ids:
            log = db.get(EmailDeliveryLog, log_id)
            if log is None or log.delivery_status != "queued":
                continue
            for attempt in range(settings.smtp_max_retries):
                try:
                    _send_via_smtp(log)
                    log.delivery_status = "sent"
                    log.sent_at = now_sgt()
                    break
                except Exception as exc:
                    log.retry_count = attempt + 1
                    log.error_message = str(exc)[:1000]
                    if attempt == settings.smtp_max_retries - 1:
                        log.delivery_status = "failed"
            db.commit()


def _send_via_smtp(log: EmailDeliveryLog) -> None:
    """Build and dispatch a single EmailMessage via the configured SMTP server."""
    msg = EmailMessage()
    msg["Subject"] = log.subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = log.recipient_email
    msg.set_content(log.body_snapshot)

    if settings.smtp_use_tls:
        # SSL wrapping (SMTP_SSL) — typically port 465
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
            context=ctx,
        ) as server:
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    else:
        # Plain SMTP, optionally upgraded with STARTTLS — typically port 587
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        ) as server:
            if settings.smtp_use_starttls:
                server.starttls(context=ssl.create_default_context())
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
