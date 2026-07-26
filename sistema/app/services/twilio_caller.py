from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import Accident, AccidentCallLog, AdminUser, Project, User
from .accident_numbering import format_accident_number
from .admin_updates import notify_admin_data_changed
from .email_sender import send_emergency_notification_email
from .time_utils import now_sgt

_logger = logging.getLogger(__name__)

_ENGLISH_COUNTRIES = {"US", "GB", "AU", "NZ", "CA", "IE", "IN", "SG", "PH", "MY"}

_DEFAULT_MESSAGE_PT = (
    "Alerta de acidente. Petrobras Checking System. Alerta de acidente. "
    "Um acidente foi reportado pelo funcionário Petrobras <nome> às <hora local> do dia <data>. "
    "O local reportado do acidente é <local> referente ao projeto <projeto>. "
    "O usuário solicita auxílio imediato no local. "
    "Caso haja dúvidas, ligue para o número <administrador>. "
    "Repetindo o número: <administrador>. Repetindo o número: <administrador>. "
    "Este alerta será enviado para o e-mail <E-Mail do Serviço Local de Emergência>."
)

_DEFAULT_MESSAGE_EN = (
    "Accident alert. Petrobras Checking System. Accident alert. "
    "An accident was reported by Petrobras employee <nome> at <hora local> on <data>. "
    "The reported location is <local> for project <projeto>. "
    "The user requests immediate assistance at the location. "
    "For inquiries, call <administrador>. "
    "Repeating: <administrador>. Repeating: <administrador>. "
    "An alert will be sent to <E-Mail do Serviço Local de Emergência>."
)


class TwilioNotConfiguredError(Exception):
    pass


class EmergencyCallAlreadyFiredError(Exception):
    pass


class EmergencyCallFailedError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _resolve_voice(country_code: str) -> tuple[str, str]:
    """Return (language, voice) for Twilio <Say> based on project country_code."""
    cc = (country_code or "").strip().upper()
    if cc == "BR":
        return "pt-BR", "Polly.Vitoria"
    return "en-US", "Polly.Joanna"


def _build_twiml(text: str, language: str, voice: str) -> str:
    safe = (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say language="{language}" voice="{voice}">{safe}</Say>'
        "</Response>"
    )


def _format_event_time(event_time: datetime, timezone_name: str) -> tuple[str, str]:
    """Return (hora_local HH:MM, data DD/MM/YYYY) in the project timezone."""
    try:
        tz = ZoneInfo(timezone_name or "UTC")
    except Exception:
        tz = timezone.utc
    local_dt = event_time.astimezone(tz)
    return local_dt.strftime("%H:%M"), local_dt.strftime("%d/%m/%Y")


def _substitute_placeholders(
    template: str,
    *,
    reporter_name: str,
    hora_local: str,
    data: str,
    reporter_local: str,
    project_name: str,
    mobile_admin: str,
    email_local_emergency: str,
) -> str:
    replacements = {
        "<nome>": reporter_name or "(não identificado)",
        "<hora local>": hora_local,
        "<data>": data,
        "<local>": reporter_local or "(não informado)",
        "<projeto>": project_name,
        "<administrador>": mobile_admin or "(não cadastrado)",
        "<E-Mail do Serviço Local de Emergência>": email_local_emergency or "(não cadastrado)",
    }
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result


def _next_call_number(db: Session) -> int:
    result = db.execute(
        select(func.coalesce(func.max(AccidentCallLog.call_number), 0) + 1)
    ).scalar()
    return int(result)


def format_call_number(call_number: int) -> str:
    """Zero-padded 6-digit label for an AccidentCallLog.call_number (vitalício)."""
    return str(int(call_number)).zfill(6)


def _resolve_triggered_by(
    *,
    triggered_by_user: User | None,
    triggered_by_admin_user: AdminUser | None,
    reporter_name_fallback: str,
) -> tuple[str, str, str]:
    """Return (display_name, chave, role) for SSE metadata.

    role is "admin" when an AdminUser drove the call, "user" otherwise.
    """
    if triggered_by_admin_user is not None:
        return (
            triggered_by_admin_user.nome_completo or reporter_name_fallback or "(desconhecido)",
            triggered_by_admin_user.chave or "",
            "admin",
        )
    if triggered_by_user is not None:
        return (
            triggered_by_user.nome or reporter_name_fallback or "(desconhecido)",
            triggered_by_user.chave or "",
            "user",
        )
    return (reporter_name_fallback or "(desconhecido)", "", "user")


def _build_call_notification_metadata(
    *,
    log: AccidentCallLog,
    accident: Accident,
    project: Project,
    triggered_by_name: str,
    triggered_by_chave: str,
    triggered_by_role: str,
    status_event: str,
    occurred_at: datetime,
    duration_seconds: int | None = None,
    ended_by: str | None = None,
) -> dict:
    """Canonical SSE metadata for any emergency-call notification.

    The front (admin2/app.js) uses status_event to choose a localized line via
    _buildNotificationLine. All notifications carry the same shape so the
    notification feed can be persisted/rendered uniformly.
    """
    return {
        "call_number": log.call_number,
        "call_number_label": format_call_number(log.call_number),
        "accident_id": accident.id,
        "project_id": project.id,
        "project_name": accident.project_name_snapshot,
        "triggered_by_name": triggered_by_name,
        "triggered_by_chave": triggered_by_chave,
        "triggered_by_role": triggered_by_role,
        "call_status": log.call_status,
        "status_event": status_event,
        "occurred_at": occurred_at.isoformat() if occurred_at else None,
        "duration_seconds": duration_seconds,
        "ended_by": ended_by,
    }


def _format_notification_timestamp_pt(value: datetime, timezone_name: str | None = None) -> str:
    """Format `value` as 'dd/mm/yyyy hh:mm:ss' in the project's timezone.

    Mirrors the front helper `_formatNotificationTimestamp` in admin2/app.js,
    but server-side we use the project's timezone (not the browser's) so the
    persisted message_pt is consistent for every admin who later reads it.
    """
    if value is None:
        value = now_sgt()
    try:
        tz = ZoneInfo(timezone_name) if timezone_name else None
    except Exception:
        tz = None
    if tz is not None:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        value = value.astimezone(tz)
    return value.strftime("%d/%m/%Y %H:%M:%S")


def _format_notification_message_pt(metadata: dict, *, timezone_name: str | None = None) -> str:
    """Server-side mirror of admin2/app.js _buildNotificationLine.

    Produces the localized pt-BR notification line that the front would show.
    We persist this string so a refreshed admin sees the exact same text.
    """
    occurred_at = metadata.get("occurred_at")
    if isinstance(occurred_at, str):
        try:
            ts_dt = datetime.fromisoformat(occurred_at)
        except ValueError:
            ts_dt = now_sgt()
    elif isinstance(occurred_at, datetime):
        ts_dt = occurred_at
    else:
        ts_dt = now_sgt()
    ts = _format_notification_timestamp_pt(ts_dt, timezone_name)

    label = metadata.get("call_number_label") or str(metadata.get("call_number") or 0).zfill(6)
    project = metadata.get("project_name") or "(projeto desconhecido)"
    triggerer_name = metadata.get("triggered_by_name") or "(desconhecido)"
    triggerer_chave = metadata.get("triggered_by_chave") or ""
    triggerer_label = f"{triggerer_name} ({triggerer_chave})" if triggerer_chave else triggerer_name
    channel = (
        "através da aplicação web"
        if metadata.get("triggered_by_role") == "user"
        else "através do website do administrador"
    )
    duration = metadata.get("duration_seconds")
    ended_by = metadata.get("ended_by") or "system"
    status_event = metadata.get("status_event")

    if status_event == "requested":
        return f"({ts}) Ligação {label} solicitada por {triggerer_label}, {channel}, para o projeto {project}."
    if status_event in ("initiated", "ringing"):
        return f"({ts}) A ligação {label} está sendo completada."
    if status_event == "answered":
        return f"({ts}) A ligação {label} foi atendida."
    if status_event == "completed":
        finalized_by = "pelo receptor" if ended_by == "receiver" else "pelo sistema"
        duration_part = f" Duração total: {duration} segundos." if duration is not None else ""
        return f"({ts}) A ligação {label} foi finalizada {finalized_by}.{duration_part}"
    if status_event == "fallback_success":
        return f"({ts}) A ligação {label} foi solicitada com sucesso."
    if status_event == "failed":
        return f"({ts}) A ligação {label} falhou."
    if status_event == "busy":
        return f"({ts}) A ligação {label} terminou — destino ocupado."
    if status_event == "no_answer":
        return f"({ts}) A ligação {label} terminou sem resposta."
    if status_event == "canceled":
        return f"({ts}) A ligação {label} foi cancelada."
    status = metadata.get("call_status") or "atualização"
    return f"({ts}) Ligação {label}: {status}."


def record_call_notification(
    db: Session,
    *,
    log: AccidentCallLog,
    metadata: dict,
    project_timezone_name: str | None = None,
) -> "AccidentCallNotification":
    """Persist a single notification line for `log` and return the row.

    The caller still drives notify_admin_data_changed for the live SSE; this
    function only handles durable storage so the admin can refresh the page.
    """
    from ..models import AccidentCallNotification  # local import to avoid cycle at top

    if not metadata or not log or not log.accident_id:
        # Fail-safe: do not persist incomplete rows. The live SSE may still be
        # useful even when persistence is impossible.
        raise ValueError("record_call_notification requires log.accident_id and metadata")

    occurred_at_raw = metadata.get("occurred_at")
    if isinstance(occurred_at_raw, datetime):
        occurred_at = occurred_at_raw
    elif isinstance(occurred_at_raw, str):
        try:
            occurred_at = datetime.fromisoformat(occurred_at_raw)
        except ValueError:
            occurred_at = now_sgt()
    else:
        occurred_at = now_sgt()

    message_pt = _format_notification_message_pt(metadata, timezone_name=project_timezone_name)
    now = now_sgt()
    row = AccidentCallNotification(
        call_log_id=log.id,
        accident_id=log.accident_id,
        event_type=str(metadata.get("status_event") or metadata.get("call_status") or "unknown")[:32],
        message_pt=message_pt,
        occurred_at=occurred_at,
        created_at=now,
    )
    db.add(row)
    db.flush()
    return row


def make_emergency_call(
    db: Session,
    *,
    accident: Accident,
    project: Project,
    triggered_by_user: User | None = None,
    triggered_by_admin_user: AdminUser | None = None,
    reporter_name: str,
    reporter_local: str,
    event_time: datetime,
) -> AccidentCallLog:
    # Validate Twilio config for this project
    account_sid = project.twilio_account_sid or settings.twilio_account_sid or ""
    auth_token = project.twilio_auth_token or settings.twilio_auth_token or ""
    from_phone = project.twilio_phone_number or settings.twilio_phone_number or ""
    to_phone = project.emergency_phone or ""

    if not all([account_sid, auth_token, from_phone, to_phone]):
        raise TwilioNotConfiguredError(
            "Twilio não está totalmente configurado para este projeto. "
            "Verifique Account SID, Auth Token, número Twilio e Telefone de Emergência Local."
        )

    # One user-triggered call per accident, whoever fires it first. Nothing in the
    # schema enforces that, so the predicate below can legitimately match several
    # rows (two users racing both pass the check and each insert a log); with
    # scalar_one_or_none that turned into MultipleResultsFound → HTTP 500 on every
    # later attempt, permanently breaking the guard for that accident.
    if triggered_by_user is not None:
        existing_call = db.execute(
            select(AccidentCallLog).where(
                AccidentCallLog.accident_id == accident.id,
                AccidentCallLog.triggered_by_user_id.is_not(None),
            )
        ).scalars().first()
        if existing_call is not None:
            raise EmergencyCallAlreadyFiredError(
                "Uma chamada de emergência já foi realizada por outro usuário neste acidente."
            )

    hora_local, data = _format_event_time(event_time, project.timezone_name)
    language, voice = _resolve_voice(project.country_code)

    message_template = project.emergency_call_message or (
        _DEFAULT_MESSAGE_PT if project.country_code == "BR" else _DEFAULT_MESSAGE_EN
    )
    message_text = _substitute_placeholders(
        message_template,
        reporter_name=reporter_name,
        hora_local=hora_local,
        data=data,
        reporter_local=reporter_local,
        project_name=accident.project_name_snapshot,
        mobile_admin=project.mobile_admin,
        email_local_emergency=project.email_local_emergency,
    )
    twiml_xml = _build_twiml(message_text, language, voice)

    call_number = _next_call_number(db)
    now = now_sgt()
    log = AccidentCallLog(
        call_number=call_number,
        call_sid=None,
        accident_id=accident.id,
        project_id=project.id,
        triggered_by_user_id=triggered_by_user.id if triggered_by_user else None,
        triggered_by_admin_id=triggered_by_admin_user.id if triggered_by_admin_user else None,
        to_phone=to_phone,
        from_phone=from_phone,
        call_status="queued",
        message_twiml=twiml_xml,
        created_at=now,
        updated_at=now,
    )
    db.add(log)
    db.commit()

    triggered_by_name, triggered_by_chave, triggered_by_role = _resolve_triggered_by(
        triggered_by_user=triggered_by_user,
        triggered_by_admin_user=triggered_by_admin_user,
        reporter_name_fallback=reporter_name,
    )

    # Fire the canonical "requested" notification immediately after the log row
    # is committed. This matches item 3.2.5.1 of docs/temp002_alteracoes.txt and
    # — critically — guarantees the front shows a confirmation even when the
    # Twilio SDK is unavailable or when no status callbacks ever arrive
    # (item 5.5.1 fallback).
    requested_metadata = _build_call_notification_metadata(
        log=log,
        accident=accident,
        project=project,
        triggered_by_name=triggered_by_name,
        triggered_by_chave=triggered_by_chave,
        triggered_by_role=triggered_by_role,
        status_event="requested",
        occurred_at=log.created_at,
    )
    # Persist so the admin can refresh and still see the line (item 3.2.3).
    record_call_notification(
        db, log=log, metadata=requested_metadata,
        project_timezone_name=project.timezone_name,
    )
    db.commit()
    notify_admin_data_changed("emergency_call_initiated", metadata=requested_metadata)

    try:
        from twilio.rest import Client  # lazy import — not installed in dev by default

        client = Client(account_sid, auth_token)
        call_kwargs: dict = dict(
            to=to_phone,
            from_=from_phone,
            twiml=twiml_xml,
        )
        if settings.public_base_url:
            call_kwargs["status_callback"] = (
                f"{settings.public_base_url}/api/twilio/status-callback"
            )
            call_kwargs["status_callback_method"] = "POST"
            call_kwargs["status_callback_event"] = [
                "initiated", "ringing", "in-progress", "completed"
            ]

        call = client.calls.create(**call_kwargs)
        log.call_sid = call.sid
        log.call_status = "initiated"
    except ImportError:
        # SDK absent. In development that is expected: keep the log queued, do NOT
        # raise, and let the caller show the confirmation — the "requested" SSE
        # already went out and status callbacks would never arrive anyway.
        #
        # Anywhere else it is a misconfiguration, and staying silent is dangerous:
        # the caller reports "Chamada de emergência iniciada" to someone in an
        # emergency when no call was ever placed. twilio>=9.0.0 is in
        # requirements.txt, so reaching this branch outside dev means the runtime
        # is broken and the operator has to hear about it.
        _logger.warning("Twilio SDK not installed — call queued but not sent")
        log.error_message = "Twilio SDK not installed (twilio>=9.0.0 required)"
        log.updated_at = now_sgt()
        if settings.app_env != "development":
            log.call_status = "failed"
            db.commit()
            raise TwilioNotConfiguredError(
                "O componente de telefonia não está instalado no servidor. "
                "A chamada NÃO foi realizada — acione a emergência por outro meio."
            )
        db.commit()
        return log
    except Exception as exc:
        log.call_status = "failed"
        log.error_message = str(exc)[:1000]
        log.updated_at = now_sgt()
        db.commit()
        _logger.error("Twilio call failed", exc_info=True)
        # Surface a "failed" SSE so the front can show the error line. The
        # initial "requested" SSE has already been delivered.
        failed_metadata = _build_call_notification_metadata(
            log=log,
            accident=accident,
            project=project,
            triggered_by_name=triggered_by_name,
            triggered_by_chave=triggered_by_chave,
            triggered_by_role=triggered_by_role,
            status_event="failed",
            occurred_at=log.updated_at,
        )
        try:
            record_call_notification(
                db, log=log, metadata=failed_metadata,
                project_timezone_name=project.timezone_name,
            )
            db.commit()
        except Exception:
            _logger.warning("Failed to persist 'failed' call notification", exc_info=True)
            db.rollback()
        notify_admin_data_changed("emergency_call_status_update", metadata=failed_metadata)
        raise EmergencyCallFailedError(str(exc)) from exc

    log.updated_at = now_sgt()
    db.commit()

    send_emergency_notification_email(
        accident_number_label=format_accident_number(accident.accident_number),
        project=project,
        location_name=reporter_local or accident.location_name_snapshot or "",
        reporter_name=reporter_name,
        call_number=call_number,
        event_time=event_time,
    )

    return log
