from __future__ import annotations

import json
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import get_db
from ..models import TransportAssignment, TransportNotification, TransportRequest, User, Vehicle, Workplace
from ..schemas import (
    AdminActionResponse,
    TransportAssignmentUpsert,
    TransportBotConversationResponse,
    TransportAuthVerifyRequest,
    TransportBotIncomingMessage,
    TransportDashboardResponse,
    TransportIdentity,
    TransportNotificationAckResponse,
    TransportNotificationListResponse,
    TransportNotificationRow,
    TransportSessionResponse,
    TransportWhatsAppDispatchResponse,
    TransportVehicleCreate,
    TransportWorkplaceUpsert,
    WorkplaceRow,
)
from ..services.admin_auth import (
    clear_transport_session,
    get_authenticated_transport_user_from_session,
    normalize_admin_key,
    require_transport_session,
    user_has_transport_access,
    verify_password,
)
from ..services.admin_updates import notify_admin_data_changed
from ..services.event_logger import log_event
from ..services.time_utils import now_sgt
from ..services.transport import (
    build_transport_dashboard,
    create_transport_vehicle_registration,
    find_transport_vehicle_schedule,
    get_paired_route_kind,
    is_transport_registered_user,
    list_workplaces,
    process_bot_message,
    queue_assignment_notification,
    remove_transport_vehicle_availability,
    request_applies_to_date,
    update_transport_assignment,
)
from ..services import whatsapp_meta
from ..services.user_sync import find_user_by_chave


router = APIRouter(prefix="/api/transport", tags=["transport"])


def build_transport_identity(user: User) -> TransportIdentity:
    return TransportIdentity(id=user.id, chave=user.chave, nome_completo=user.nome, perfil=user.perfil)


def require_transport_bot_shared_key(x_transport_bot_shared_key: str | None = Header(default=None)) -> None:
    if x_transport_bot_shared_key == settings.transport_bot_shared_key:
        return
    raise HTTPException(status_code=401, detail="Invalid transport bot shared key")


def _notify_transport_bot_side_effects(response: TransportBotConversationResponse) -> None:
    if response.registration_completed:
        notify_admin_data_changed("register")
        notify_admin_data_changed("checkin")
    if response.request_created:
        notify_admin_data_changed("event")


@router.get("/auth/session", response_model=TransportSessionResponse)
def transport_session(request: Request, db: Session = Depends(get_db)) -> TransportSessionResponse:
    transport_user = get_authenticated_transport_user_from_session(request, db)
    if transport_user is None:
        return TransportSessionResponse(authenticated=False)
    return TransportSessionResponse(authenticated=True, user=build_transport_identity(transport_user))


@router.post("/auth/verify", response_model=TransportSessionResponse)
def verify_transport_access(
    payload: TransportAuthVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TransportSessionResponse:
    key = normalize_admin_key(payload.chave)
    transport_user = db.execute(select(User).where(User.chave == key)).scalar_one_or_none()

    if transport_user is None or transport_user.senha is None:
        clear_transport_session(request)
        return TransportSessionResponse(authenticated=False, message="Invalid key or password.")
    if not user_has_transport_access(transport_user):
        clear_transport_session(request)
        return TransportSessionResponse(authenticated=False, message="This user does not have transport access.")
    if not verify_password(payload.senha, transport_user.senha):
        clear_transport_session(request)
        return TransportSessionResponse(authenticated=False, message="Invalid key or password.")

    request.session["transport_user_id"] = transport_user.id
    return TransportSessionResponse(
        authenticated=True,
        user=build_transport_identity(transport_user),
        message="Transport access granted.",
    )


@router.post("/auth/logout", response_model=AdminActionResponse)
def transport_logout(request: Request) -> AdminActionResponse:
    clear_transport_session(request)
    return AdminActionResponse(ok=True, message="Transport session closed.")


@router.get("/dashboard", response_model=TransportDashboardResponse, dependencies=[Depends(require_transport_session)])
def get_transport_dashboard(
    service_date: date | None = Query(default=None),
    route_kind: Literal["home_to_work", "work_to_home"] = Query(default="home_to_work"),
    db: Session = Depends(get_db),
) -> TransportDashboardResponse:
    resolved_date = service_date or now_sgt().date()
    return build_transport_dashboard(db, service_date=resolved_date, route_kind=route_kind)


@router.get("/workplaces", response_model=list[WorkplaceRow], dependencies=[Depends(require_transport_session)])
def get_transport_workplaces(db: Session = Depends(get_db)) -> list[WorkplaceRow]:
    return list_workplaces(db)


@router.post("/workplaces", response_model=WorkplaceRow, dependencies=[Depends(require_transport_session)])
def create_transport_workplace(
    payload: TransportWorkplaceUpsert,
    db: Session = Depends(get_db),
) -> WorkplaceRow:
    existing = db.execute(select(Workplace).where(Workplace.workplace == payload.workplace)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Ja existe um workplace cadastrado com esse nome")

    workplace = Workplace(
        workplace=payload.workplace,
        address=payload.address,
        zip=payload.zip,
        country=payload.country,
    )
    db.add(workplace)
    db.commit()
    db.refresh(workplace)
    notify_admin_data_changed("register")
    return WorkplaceRow(
        id=workplace.id,
        workplace=workplace.workplace,
        address=workplace.address,
        zip=workplace.zip,
        country=workplace.country,
    )


@router.post("/vehicles", response_model=AdminActionResponse, dependencies=[Depends(require_transport_session)])
def create_transport_vehicle(
    payload: TransportVehicleCreate,
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    try:
        create_transport_vehicle_registration(db, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    notify_admin_data_changed("register")
    return AdminActionResponse(ok=True, message="Veiculo cadastrado com sucesso.")


@router.delete("/vehicles/{schedule_id}", response_model=AdminActionResponse, dependencies=[Depends(require_transport_session)])
def delete_transport_vehicle_for_route(
    schedule_id: int,
    service_date: date = Query(...),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    try:
        remove_transport_vehicle_availability(db, schedule_id=schedule_id, service_date=service_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    notify_admin_data_changed("event")
    return AdminActionResponse(ok=True, message="Veiculo removido do trajeto selecionado.")


@router.post("/assignments", response_model=AdminActionResponse)
def save_transport_assignment(
    payload: TransportAssignmentUpsert,
    db: Session = Depends(get_db),
    _current_transport_user: User = Depends(require_transport_session),
) -> AdminActionResponse:
    transport_request = db.get(TransportRequest, payload.request_id)
    if transport_request is None:
        raise HTTPException(status_code=404, detail="Pedido de transporte nao encontrado")
    if not request_applies_to_date(transport_request, payload.service_date):
        raise HTTPException(status_code=400, detail="Pedido de transporte nao se aplica a data informada")

    vehicle = None
    if payload.vehicle_id is not None:
        vehicle = db.get(Vehicle, payload.vehicle_id)
        if vehicle is None:
            raise HTTPException(status_code=404, detail="Veiculo nao encontrado")
        if vehicle.service_scope != transport_request.request_kind:
            raise HTTPException(status_code=409, detail="O veiculo selecionado nao pertence a lista correta")
        if find_transport_vehicle_schedule(
            db,
            vehicle=vehicle,
            service_date=payload.service_date,
            route_kind=payload.route_kind,
        ) is None:
            raise HTTPException(status_code=409, detail="O veiculo selecionado nao esta disponivel para essa data e trajeto")

    assignment, is_update = update_transport_assignment(
        db,
        transport_request=transport_request,
        service_date=payload.service_date,
        route_kind=payload.route_kind,
        status=payload.status,
        vehicle=vehicle,
        response_message=payload.response_message,
        admin_user_id=None,
    )

    if payload.status == "confirmed" and vehicle is not None and transport_request.request_kind != "extra":
        paired_route_kind = get_paired_route_kind(payload.route_kind)
        if paired_route_kind and find_transport_vehicle_schedule(
            db,
            vehicle=vehicle,
            service_date=payload.service_date,
            route_kind=paired_route_kind,
        ) is not None:
            existing_paired_assignment = db.execute(
                select(TransportAssignment).where(
                    TransportAssignment.request_id == transport_request.id,
                    TransportAssignment.service_date == payload.service_date,
                    TransportAssignment.route_kind == paired_route_kind,
                )
            ).scalar_one_or_none()
            if existing_paired_assignment is None:
                update_transport_assignment(
                    db,
                    transport_request=transport_request,
                    service_date=payload.service_date,
                    route_kind=paired_route_kind,
                    status="confirmed",
                    vehicle=vehicle,
                    response_message="Mirrored from the paired route",
                    admin_user_id=None,
                )

    user = db.get(User, transport_request.user_id)
    queued_notification = None
    if user is not None:
        queued_notification = queue_assignment_notification(
            db,
            transport_request=transport_request,
            assignment=assignment,
            user=user,
            vehicle=vehicle,
            is_update=is_update,
        )

    db.commit()
    notification_message_suffix = ""
    if queued_notification is not None:
        try:
            dispatch_result = whatsapp_meta.dispatch_pending_transport_notifications(
                db,
                notification_ids=[queued_notification.id],
                limit=1,
            )
            if dispatch_result.sent > 0:
                notification_message_suffix = " Notificacao WhatsApp enviada."
            elif dispatch_result.failed > 0:
                notification_message_suffix = " Alocacao salva, mas o envio do WhatsApp falhou e a notificacao permaneceu pendente."
        except whatsapp_meta.WhatsAppConfigurationError:
            notification_message_suffix = " Alocacao salva; notificacao WhatsApp ficou pendente porque a Cloud API nao esta configurada."

    notify_admin_data_changed("event")
    return AdminActionResponse(ok=True, message=f"Alocacao de transporte salva com sucesso.{notification_message_suffix}")


@router.post(
    "/bot/messages",
    response_model=TransportBotConversationResponse,
    dependencies=[Depends(require_transport_bot_shared_key)],
)
def receive_transport_bot_message(
    payload: TransportBotIncomingMessage,
    db: Session = Depends(get_db),
) -> TransportBotConversationResponse:
    try:
        response = process_bot_message(db, chat_id=payload.chat_id, message=payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    _notify_transport_bot_side_effects(response)
    return response


@router.get(
    "/bot/notifications/pending",
    response_model=TransportNotificationListResponse,
    dependencies=[Depends(require_transport_bot_shared_key)],
)
def get_pending_transport_notifications(db: Session = Depends(get_db)) -> TransportNotificationListResponse:
    rows = db.execute(
        select(TransportNotification)
        .where(TransportNotification.status == "pending")
        .order_by(TransportNotification.created_at, TransportNotification.id)
    ).scalars().all()
    return TransportNotificationListResponse(
        items=[
            TransportNotificationRow(
                id=row.id,
                chat_id=row.chat_id,
                message=row.message,
                created_at=row.created_at,
                request_id=row.request_id,
                assignment_id=row.assignment_id,
            )
            for row in rows
        ]
    )


@router.post(
    "/bot/notifications/{notification_id}/sent",
    response_model=TransportNotificationAckResponse,
    dependencies=[Depends(require_transport_bot_shared_key)],
)
def mark_transport_notification_sent(notification_id: int, db: Session = Depends(get_db)) -> TransportNotificationAckResponse:
    notification = db.get(TransportNotification, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notificacao nao encontrada")
    notification.status = "sent"
    notification.sent_at = now_sgt()
    db.commit()
    return TransportNotificationAckResponse(ok=True)


@router.get("/whatsapp/webhook", include_in_schema=False)
def verify_transport_whatsapp_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    try:
        challenge = whatsapp_meta.verify_meta_webhook_challenge(
            mode=hub_mode,
            verify_token=hub_verify_token,
            challenge=hub_challenge,
        )
    except whatsapp_meta.WhatsAppConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return PlainTextResponse(challenge)


@router.post("/whatsapp/webhook", include_in_schema=False)
async def receive_transport_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: str | None = Header(default=None),
) -> JSONResponse:
    try:
        raw_body = await request.body()
        whatsapp_meta.validate_meta_webhook_signature(body=raw_body, signature_header=x_hub_signature_256)
    except whatsapp_meta.WhatsAppConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        log_event(
            db,
            source="transport_whatsapp",
            action="webhook",
            status="failed",
            message="WhatsApp webhook rejected due to invalid signature",
            request_path=whatsapp_meta.WHATSAPP_WEBHOOK_REQUEST_PATH,
            http_status=403,
            details=str(exc),
            commit=True,
        )
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid WhatsApp webhook payload") from exc

    inbound_messages, status_updates = whatsapp_meta.parse_meta_webhook_payload(payload)
    processed_messages = 0
    duplicate_messages = 0
    replies_sent = 0
    status_events_logged = 0

    for status_update in status_updates:
        if whatsapp_meta.log_status_update_if_new(db, status_update=status_update):
            status_events_logged += 1

    if status_updates:
        db.commit()

    for inbound_message in inbound_messages:
        if whatsapp_meta.has_processed_inbound_message(db, message_id=inbound_message.message_id):
            duplicate_messages += 1
            whatsapp_meta.log_duplicate_inbound_message(db, inbound_message=inbound_message)
            continue

        try:
            response = process_bot_message(db, chat_id=inbound_message.chat_id, message=inbound_message.text)
        except ValueError as exc:
            log_event(
                db,
                source="transport_whatsapp",
                action="inbound",
                status="failed",
                message="WhatsApp inbound message could not be processed",
                request_path=whatsapp_meta.WHATSAPP_WEBHOOK_REQUEST_PATH,
                details=(
                    f"chat_id={inbound_message.chat_id}; message_id={inbound_message.message_id}; error={exc}"
                ),
            )
            db.commit()
            continue

        whatsapp_meta.mark_inbound_message_processed(db, inbound_message=inbound_message, conversation=response)
        db.commit()
        _notify_transport_bot_side_effects(response)
        processed_messages += 1

        try:
            replies_sent += len(whatsapp_meta.send_transport_bot_replies(chat_id=inbound_message.chat_id, conversation=response))
        except whatsapp_meta.WhatsAppDeliveryError as exc:
            log_event(
                db,
                source="transport_whatsapp",
                action="reply",
                status="failed",
                message="WhatsApp reply delivery failed",
                request_path=whatsapp_meta.WHATSAPP_WEBHOOK_REQUEST_PATH,
                details=(
                    f"chat_id={inbound_message.chat_id}; message_id={inbound_message.message_id}; error={exc}"
                ),
                commit=True,
            )

    return JSONResponse(
        {
            "ok": True,
            "processed_messages": processed_messages,
            "duplicate_messages": duplicate_messages,
            "status_events_logged": status_events_logged,
            "replies_sent": replies_sent,
        }
    )


@router.post(
    "/whatsapp/notifications/dispatch",
    response_model=TransportWhatsAppDispatchResponse,
    dependencies=[Depends(require_transport_session)],
)
def dispatch_transport_whatsapp_notifications(
    db: Session = Depends(get_db),
    notification_id: int | None = Query(default=None, ge=1),
    chat_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> TransportWhatsAppDispatchResponse:
    try:
        return whatsapp_meta.dispatch_pending_transport_notifications(
            db,
            notification_ids=([notification_id] if notification_id is not None else None),
            chat_id=chat_id,
            limit=limit,
        )
    except whatsapp_meta.WhatsAppConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc