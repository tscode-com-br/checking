from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import CheckEvent, TransportNotification
from ..schemas import TransportBotConversationResponse, TransportBotReplyMessage, TransportWhatsAppDispatchResponse
from .event_logger import log_event
from .time_utils import now_sgt

WHATSAPP_WEBHOOK_REQUEST_PATH = "/api/transport/whatsapp/webhook"
WHATSAPP_DISPATCH_REQUEST_PATH = "/api/transport/whatsapp/notifications/dispatch"
_ENUMERATED_OPTION_PATTERN = re.compile(r"^\d+[.)]\s")


class WhatsAppConfigurationError(RuntimeError):
    pass


class WhatsAppDeliveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class WhatsAppInboundMessage:
    chat_id: str
    message_id: str
    text: str
    profile_name: str | None = None


@dataclass(frozen=True)
class WhatsAppStatusUpdate:
    message_id: str
    status: str
    recipient_id: str | None = None
    conversation_id: str | None = None


def is_transport_whatsapp_enabled() -> bool:
    return bool(
        settings.whatsapp_enabled
        and settings.whatsapp_provider.strip().lower() == "meta"
        and settings.whatsapp_webhook_verify_token.strip()
        and settings.whatsapp_access_token.strip()
        and settings.whatsapp_phone_number_id.strip()
    )


def ensure_transport_whatsapp_enabled() -> None:
    if is_transport_whatsapp_enabled():
        return
    raise WhatsAppConfigurationError(
        "WhatsApp Cloud API nao esta configurado. Defina WHATSAPP_ENABLED=true, WHATSAPP_WEBHOOK_VERIFY_TOKEN, "
        "WHATSAPP_ACCESS_TOKEN e WHATSAPP_PHONE_NUMBER_ID."
    )


def verify_meta_webhook_challenge(*, mode: str | None, verify_token: str | None, challenge: str | None) -> str:
    ensure_transport_whatsapp_enabled()
    if mode != "subscribe" or verify_token != settings.whatsapp_webhook_verify_token:
        raise ValueError("Invalid WhatsApp webhook verification token")
    if challenge is None:
        raise ValueError("Missing WhatsApp webhook challenge")
    return challenge


def validate_meta_webhook_signature(*, body: bytes, signature_header: str | None) -> None:
    ensure_transport_whatsapp_enabled()
    app_secret = settings.whatsapp_app_secret.strip()
    if not app_secret:
        return
    if signature_header is None or not signature_header.startswith("sha256="):
        raise ValueError("Missing WhatsApp signature header")

    expected_signature = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    received_signature = signature_header.removeprefix("sha256=")
    if not hmac.compare_digest(expected_signature, received_signature):
        raise ValueError("Invalid WhatsApp webhook signature")


def parse_meta_webhook_payload(payload: dict[str, Any]) -> tuple[list[WhatsAppInboundMessage], list[WhatsAppStatusUpdate]]:
    inbound_messages: list[WhatsAppInboundMessage] = []
    status_updates: list[WhatsAppStatusUpdate] = []

    if payload.get("object") != "whatsapp_business_account":
        return inbound_messages, status_updates

    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            if change.get("field") != "messages":
                continue

            value = change.get("value") or {}
            contacts_by_wa_id = {
                str(contact.get("wa_id") or "").strip(): _normalize_optional_text(
                    ((contact.get("profile") or {}).get("name"))
                )
                for contact in value.get("contacts") or []
            }

            for message in value.get("messages") or []:
                if str(message.get("type") or "").strip() != "text":
                    continue
                chat_id = str(message.get("from") or "").strip()
                message_id = str(message.get("id") or "").strip()
                text = _normalize_optional_text(((message.get("text") or {}).get("body")))
                if not chat_id or not message_id or not text:
                    continue
                inbound_messages.append(
                    WhatsAppInboundMessage(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=text,
                        profile_name=contacts_by_wa_id.get(chat_id),
                    )
                )

            for status in value.get("statuses") or []:
                message_id = str(status.get("id") or "").strip()
                state = str(status.get("status") or "").strip().lower()
                if not message_id or not state:
                    continue
                status_updates.append(
                    WhatsAppStatusUpdate(
                        message_id=message_id,
                        status=state,
                        recipient_id=_normalize_optional_text(status.get("recipient_id")),
                        conversation_id=_normalize_optional_text(((status.get("conversation") or {}).get("id"))),
                    )
                )

    return inbound_messages, status_updates


def send_transport_bot_replies(*, chat_id: str, conversation: TransportBotConversationResponse) -> list[str]:
    ensure_transport_whatsapp_enabled()
    sent_message_ids: list[str] = []
    for reply in conversation.messages:
        reply_text = format_transport_bot_reply(reply)
        sent_message_ids.append(send_whatsapp_text_message(chat_id=chat_id, text=reply_text))
    return sent_message_ids


def dispatch_pending_transport_notifications(
    db: Session,
    *,
    notification_ids: list[int] | None = None,
    chat_id: str | None = None,
    limit: int = 20,
) -> TransportWhatsAppDispatchResponse:
    ensure_transport_whatsapp_enabled()

    query = select(TransportNotification).where(TransportNotification.status == "pending").order_by(
        TransportNotification.created_at,
        TransportNotification.id,
    )
    if notification_ids:
        query = query.where(TransportNotification.id.in_(notification_ids))
    if chat_id is not None:
        query = query.where(TransportNotification.chat_id == chat_id)

    notifications = db.execute(query.limit(limit)).scalars().all()
    attempted = 0
    sent = 0
    failed = 0
    skipped = 0

    for notification in notifications:
        if not notification.chat_id:
            skipped += 1
            log_event(
                db,
                idempotency_key=_build_meta_idempotency_key("transport-whatsapp-skip", str(notification.id)),
                source="transport_whatsapp",
                action="notify",
                status="skipped",
                message="WhatsApp notification skipped due to missing chat_id",
                request_path=WHATSAPP_DISPATCH_REQUEST_PATH,
                details=f"notification_id={notification.id}",
            )
            continue

        attempted += 1
        try:
            provider_message_id = send_whatsapp_text_message(chat_id=notification.chat_id, text=notification.message)
        except WhatsAppDeliveryError as exc:
            failed += 1
            log_event(
                db,
                idempotency_key=_build_meta_idempotency_key("transport-whatsapp-fail", str(notification.id)),
                source="transport_whatsapp",
                action="notify",
                status="failed",
                message="WhatsApp notification delivery failed",
                request_path=WHATSAPP_DISPATCH_REQUEST_PATH,
                details=f"notification_id={notification.id}; chat_id={notification.chat_id}; error={exc}",
            )
            continue

        notification.status = "sent"
        notification.sent_at = now_sgt()
        sent += 1
        log_event(
            db,
            idempotency_key=_build_meta_idempotency_key("transport-whatsapp-sent", str(notification.id)),
            source="transport_whatsapp",
            action="notify",
            status="sent",
            message="WhatsApp notification sent successfully",
            request_path=WHATSAPP_DISPATCH_REQUEST_PATH,
            details=(
                f"notification_id={notification.id}; chat_id={notification.chat_id}; provider_message_id={provider_message_id}"
            ),
        )

    db.commit()
    return TransportWhatsAppDispatchResponse(
        ok=True,
        attempted=attempted,
        sent=sent,
        failed=failed,
        skipped=skipped,
        message=(
            f"Despacho do WhatsApp concluido: {sent} enviada(s), {failed} com falha, {skipped} ignorada(s)."
        ),
    )


def send_whatsapp_text_message(*, chat_id: str, text: str) -> str:
    ensure_transport_whatsapp_enabled()
    normalized_chat_id = str(chat_id or "").strip()
    normalized_text = _normalize_optional_text(text)
    if not normalized_chat_id or not normalized_text:
        raise WhatsAppDeliveryError("chat_id e texto sao obrigatorios para envio")

    url = (
        f"https://graph.facebook.com/{settings.whatsapp_graph_api_version.strip() or 'v22.0'}/"
        f"{settings.whatsapp_phone_number_id.strip()}/messages"
    )
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": normalized_chat_id,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": normalized_text,
        },
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=15.0)
    except httpx.HTTPError as exc:
        raise WhatsAppDeliveryError(f"Erro de rede ao chamar a Cloud API do WhatsApp: {exc}") from exc

    try:
        response_payload = response.json()
    except ValueError:
        response_payload = None

    if response.status_code < 200 or response.status_code >= 300:
        raise WhatsAppDeliveryError(_extract_meta_error_message(response_payload, response.status_code))

    provider_messages = response_payload.get("messages") if isinstance(response_payload, dict) else None
    if not isinstance(provider_messages, list) or not provider_messages:
        raise WhatsAppDeliveryError("Cloud API do WhatsApp respondeu sem ID da mensagem enviada")
    provider_message_id = str((provider_messages[0] or {}).get("id") or "").strip()
    if not provider_message_id:
        raise WhatsAppDeliveryError("Cloud API do WhatsApp respondeu com ID de mensagem vazio")
    return provider_message_id


def format_transport_bot_reply(reply: TransportBotReplyMessage) -> str:
    base_text = _normalize_optional_text(reply.text) or "Mensagem vazia"
    if not reply.options:
        return base_text

    option_lines: list[str] = []
    for option in reply.options:
        normalized_option = _normalize_optional_text(option)
        if not normalized_option:
            continue
        if _ENUMERATED_OPTION_PATTERN.match(normalized_option):
            option_lines.append(normalized_option)
        else:
            option_lines.append(f"- {normalized_option}")

    if not option_lines:
        return base_text
    return f"{base_text}\n\n" + "\n".join(option_lines)


def mark_inbound_message_processed(
    db: Session,
    *,
    inbound_message: WhatsAppInboundMessage,
    conversation: TransportBotConversationResponse,
) -> None:
    log_event(
        db,
        idempotency_key=_build_meta_idempotency_key("transport-whatsapp-inbound", inbound_message.message_id),
        source="transport_whatsapp",
        action="inbound",
        status="processed",
        message="WhatsApp inbound message processed",
        request_path=WHATSAPP_WEBHOOK_REQUEST_PATH,
        details=(
            f"chat_id={inbound_message.chat_id}; message_id={inbound_message.message_id}; "
            f"state={conversation.state}; registration_completed={conversation.registration_completed}; "
            f"request_created={conversation.request_created}"
        ),
    )


def has_processed_inbound_message(db: Session, *, message_id: str) -> bool:
    idempotency_key = _build_meta_idempotency_key("transport-whatsapp-inbound", message_id)
    existing = db.execute(select(CheckEvent.id).where(CheckEvent.idempotency_key == idempotency_key)).scalar_one_or_none()
    return existing is not None


def log_duplicate_inbound_message(db: Session, *, inbound_message: WhatsAppInboundMessage) -> None:
    log_event(
        db,
        idempotency_key=_build_meta_idempotency_key("transport-whatsapp-duplicate", inbound_message.message_id),
        source="transport_whatsapp",
        action="inbound",
        status="duplicate",
        message="WhatsApp inbound message ignored because it was already processed",
        request_path=WHATSAPP_WEBHOOK_REQUEST_PATH,
        details=f"chat_id={inbound_message.chat_id}; message_id={inbound_message.message_id}",
        commit=True,
    )


def log_status_update_if_new(db: Session, *, status_update: WhatsAppStatusUpdate) -> bool:
    idempotency_key = _build_meta_idempotency_key(
        "transport-whatsapp-status",
        f"{status_update.message_id}|{status_update.status}|{status_update.recipient_id or ''}",
    )
    existing = db.execute(select(CheckEvent.id).where(CheckEvent.idempotency_key == idempotency_key)).scalar_one_or_none()
    if existing is not None:
        return False

    log_event(
        db,
        idempotency_key=idempotency_key,
        source="transport_whatsapp",
        action="status",
        status="received",
        message="WhatsApp status webhook received",
        request_path=WHATSAPP_WEBHOOK_REQUEST_PATH,
        details=(
            f"provider_message_id={status_update.message_id}; status={status_update.status}; "
            f"recipient_id={status_update.recipient_id or ''}; conversation_id={status_update.conversation_id or ''}"
        ),
    )
    return True


def _build_meta_idempotency_key(prefix: str, raw_value: str) -> str:
    digest = hashlib.sha1(raw_value.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _extract_meta_error_message(payload: Any, status_code: int) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = _normalize_optional_text(error.get("message"))
            error_type = _normalize_optional_text(error.get("type"))
            code = error.get("code")
            if message and error_type and code is not None:
                return f"Cloud API do WhatsApp retornou erro {code} ({error_type}): {message}"
            if message:
                return f"Cloud API do WhatsApp retornou erro: {message}"
    return f"Cloud API do WhatsApp retornou HTTP {status_code}"


def _normalize_optional_text(value: Any) -> str | None:
    normalized = " ".join(str(value or "").strip().split())
    return normalized or None