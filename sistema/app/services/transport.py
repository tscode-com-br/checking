from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    TransportAssignment,
    TransportBotSession,
    TransportNotification,
    TransportRequest,
    TransportVehicleSchedule,
    TransportVehicleScheduleException,
    User,
    Vehicle,
    Workplace,
)
from ..schemas import (
    TransportBotConversationResponse,
    TransportBotReplyMessage,
    TransportDashboardResponse,
    TransportRequestRow,
    TransportVehicleCreate,
    TransportVehicleRow,
    WebTransportStateResponse,
    WorkplaceRow,
)
from .time_utils import now_sgt
from .user_profiles import normalize_person_name
from .user_sync import (
    APP_IMPORTED_USER_NAME,
    WEB_IMPORTED_USER_NAME,
    apply_user_state,
    create_user_sync_event,
    ensure_current_user_state_event,
    find_user_by_chave,
    is_same_singapore_day,
    normalize_user_key,
    resolve_latest_user_activity,
)


_REQUEST_KIND_TO_RECURRENCE = {
    "regular": "weekday",
    "weekend": "weekend",
    "extra": "single_date",
}
_REQUEST_KIND_TO_LABEL = {
    "regular": "REGULAR",
    "weekend": "WEEKEND",
    "extra": "EXTRA",
}
_ROUTE_KIND_TO_LABEL = {
    "home_to_work": "Home to Work",
    "work_to_home": "Work to Home",
}
_PAIRED_ROUTE_KIND = {
    "home_to_work": "work_to_home",
    "work_to_home": "home_to_work",
}
_PLACEHOLDER_NAMES = {APP_IMPORTED_USER_NAME, WEB_IMPORTED_USER_NAME}
_MENU_OPTIONS = ["REGULAR", "WEEKEND", "EXTRA", "CHANGE", "CANCEL"]
_PROJECT_OPTIONS = ["P80", "P82", "P83"]


def build_transport_dashboard(
    db: Session,
    *,
    service_date: date,
    route_kind: str,
) -> TransportDashboardResponse:
    workplaces = list_workplaces(db)
    vehicles_by_scope, vehicle_rows_by_id = _build_vehicle_rows_for_dashboard(
        db,
        service_date=service_date,
        route_kind=route_kind,
    )

    request_rows = {
        "regular": [],
        "weekend": [],
        "extra": [],
    }
    assignments = db.execute(
        select(TransportAssignment).where(
            TransportAssignment.service_date == service_date,
            TransportAssignment.route_kind == route_kind,
        )
    ).scalars().all()
    assignments_by_request_id = {assignment.request_id: assignment for assignment in assignments}
    assigned_vehicle_ids = {assignment.vehicle_id for assignment in assignments if assignment.vehicle_id is not None}
    assigned_vehicle_rows = {
        vehicle.id: _build_vehicle_row(vehicle)
        for vehicle in db.execute(select(Vehicle).where(Vehicle.id.in_(assigned_vehicle_ids))).scalars().all()
    } if assigned_vehicle_ids else {}
    requests = db.execute(
        select(TransportRequest, User)
        .join(User, User.id == TransportRequest.user_id)
        .where(TransportRequest.status == "active")
    ).all()
    for transport_request, user in requests:
        if not request_applies_to_date(transport_request, service_date):
            continue

        assignment = assignments_by_request_id.get(transport_request.id)
        assigned_vehicle = None
        assignment_status = "pending"
        response_message = None
        if assignment is not None:
            assignment_status = assignment.status
            response_message = assignment.response_message
            if assignment.vehicle_id is not None:
                assigned_vehicle = vehicle_rows_by_id.get(assignment.vehicle_id) or assigned_vehicle_rows.get(assignment.vehicle_id)

        request_rows[transport_request.request_kind].append(
            TransportRequestRow(
                id=transport_request.id,
                request_kind=transport_request.request_kind,
                requested_time=transport_request.requested_time,
                service_date=service_date,
                user_id=user.id,
                chave=user.chave,
                nome=user.nome,
                projeto=user.projeto,
                workplace=user.workplace,
                end_rua=user.end_rua,
                zip=user.zip,
                assignment_status=assignment_status,
                awareness_status=(
                    "aware"
                    if assignment is not None and assignment.acknowledged_by_user
                    else "pending"
                ),
                assigned_vehicle=assigned_vehicle,
                response_message=response_message,
            )
        )

    for rows in request_rows.values():
        rows.sort(key=lambda item: (item.requested_time, item.nome.lower(), item.chave))

    return TransportDashboardResponse(
        selected_date=service_date,
        selected_route=route_kind,
        regular_requests=request_rows["regular"],
        weekend_requests=request_rows["weekend"],
        extra_requests=request_rows["extra"],
        regular_vehicles=vehicles_by_scope["regular"],
        weekend_vehicles=vehicles_by_scope["weekend"],
        extra_vehicles=vehicles_by_scope["extra"],
        workplaces=workplaces,
    )


def list_workplaces(db: Session) -> list[WorkplaceRow]:
    rows = db.execute(select(Workplace).order_by(Workplace.workplace, Workplace.id)).scalars().all()
    return [
        WorkplaceRow(
            id=row.id,
            workplace=row.workplace,
            address=row.address,
            zip=row.zip,
            country=row.country,
        )
        for row in rows
    ]


def request_applies_to_date(transport_request: TransportRequest, service_date: date) -> bool:
    if transport_request.status != "active":
        return False
    if transport_request.recurrence_kind == "weekday":
        return service_date.weekday() < 5
    if transport_request.recurrence_kind == "weekend":
        return service_date.weekday() >= 5
    return transport_request.single_date == service_date


def vehicle_schedule_applies_to_date(schedule: TransportVehicleSchedule, service_date: date) -> bool:
    if not schedule.is_active:
        return False
    if schedule.recurrence_kind == "weekday":
        return service_date.weekday() < 5
    if schedule.recurrence_kind == "matching_weekday":
        return schedule.weekday == service_date.weekday()
    return schedule.service_date == service_date


def create_transport_vehicle_registration(
    db: Session,
    *,
    payload: TransportVehicleCreate,
) -> tuple[Vehicle, list[TransportVehicleSchedule]]:
    timestamp = now_sgt()
    vehicle = db.execute(select(Vehicle).where(Vehicle.placa == payload.placa)).scalar_one_or_none()

    if vehicle is None:
        vehicle = Vehicle(
            placa=payload.placa,
            tipo=payload.tipo,
            color=payload.color,
            lugares=payload.lugares,
            tolerance=payload.tolerance,
            service_scope=payload.service_scope,
        )
        db.add(vehicle)
        db.flush()
    else:
        if vehicle.service_scope != payload.service_scope:
            raise ValueError("A vehicle with this plate already exists in another list.")
        if (
            vehicle.tipo != payload.tipo
            or (vehicle.color or "") != payload.color
            or vehicle.lugares != payload.lugares
            or vehicle.tolerance != payload.tolerance
        ):
            raise ValueError("A vehicle with this plate already exists with a different configuration.")

    created_schedules: list[TransportVehicleSchedule] = []
    for schedule_spec in _build_schedule_specs_from_payload(payload):
        if _vehicle_has_active_schedule_on_date(
            db,
            vehicle_id=vehicle.id,
            service_scope=schedule_spec["service_scope"],
            route_kind=schedule_spec["route_kind"],
            service_date=payload.service_date,
        ):
            raise ValueError("An active vehicle already exists for the selected list, route, and date.")

        schedule = TransportVehicleSchedule(
            vehicle_id=vehicle.id,
            service_scope=schedule_spec["service_scope"],
            route_kind=schedule_spec["route_kind"],
            recurrence_kind=schedule_spec["recurrence_kind"],
            service_date=schedule_spec["service_date"],
            weekday=schedule_spec["weekday"],
            is_active=True,
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(schedule)
        db.flush()
        created_schedules.append(schedule)

    return vehicle, created_schedules


def remove_transport_vehicle_availability(
    db: Session,
    *,
    schedule_id: int,
    service_date: date,
) -> TransportVehicleSchedule:
    timestamp = now_sgt()
    schedule = db.get(TransportVehicleSchedule, schedule_id)
    if schedule is None or not schedule.is_active:
        raise ValueError("Vehicle schedule not found.")
    if not vehicle_schedule_applies_to_date(schedule, service_date):
        raise ValueError("The vehicle schedule does not apply to the selected date.")

    if schedule.recurrence_kind == "single_date":
        schedule.is_active = False
        schedule.updated_at = timestamp
    else:
        existing_exception = db.execute(
            select(TransportVehicleScheduleException).where(
                TransportVehicleScheduleException.vehicle_schedule_id == schedule.id,
                TransportVehicleScheduleException.service_date == service_date,
            )
        ).scalar_one_or_none()
        if existing_exception is None:
            db.add(
                TransportVehicleScheduleException(
                    vehicle_schedule_id=schedule.id,
                    service_date=service_date,
                    created_at=timestamp,
                )
            )

    assignments = db.execute(
        select(TransportAssignment).where(
            TransportAssignment.service_date == service_date,
            TransportAssignment.route_kind == schedule.route_kind,
            TransportAssignment.vehicle_id == schedule.vehicle_id,
        )
    ).scalars().all()
    for assignment in assignments:
        assignment.vehicle_id = None
        assignment.status = "cancelled"
        assignment.response_message = "Vehicle removed from this route"
        assignment.updated_at = timestamp
        assignment.notified_at = None

    return schedule


def upsert_transport_request(
    db: Session,
    *,
    user: User,
    request_kind: str,
    requested_time: str,
    requested_date: date | None,
    created_via: str,
) -> TransportRequest:
    timestamp = now_sgt()
    recurrence_kind = _REQUEST_KIND_TO_RECURRENCE[request_kind]

    existing_requests = db.execute(
        select(TransportRequest)
        .where(
            TransportRequest.user_id == user.id,
            TransportRequest.request_kind == request_kind,
            TransportRequest.status == "active",
        )
        .order_by(TransportRequest.created_at.desc(), TransportRequest.id.desc())
    ).scalars().all()

    if request_kind == "extra":
        for existing in existing_requests:
            if existing.single_date == requested_date and existing.requested_time == requested_time:
                return existing
    else:
        for existing in existing_requests:
            if existing.requested_time == requested_time and existing.recurrence_kind == recurrence_kind:
                return existing

    if request_kind != "extra":
        for existing in existing_requests:
            existing.status = "cancelled"
            existing.cancelled_at = timestamp
            existing.updated_at = timestamp

    transport_request = TransportRequest(
        user_id=user.id,
        request_kind=request_kind,
        recurrence_kind=recurrence_kind,
        requested_time=requested_time,
        single_date=requested_date,
        created_via=created_via,
        status="active",
        created_at=timestamp,
        updated_at=timestamp,
        cancelled_at=None,
    )
    db.add(transport_request)
    db.flush()
    return transport_request


def get_latest_active_transport_request(
    db: Session,
    *,
    user: User,
    request_kind: str,
) -> TransportRequest | None:
    return db.execute(
        select(TransportRequest)
        .where(
            TransportRequest.user_id == user.id,
            TransportRequest.request_kind == request_kind,
            TransportRequest.status == "active",
        )
        .order_by(TransportRequest.updated_at.desc(), TransportRequest.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def cancel_transport_requests(db: Session, *, user: User, request_kind: str, reference_date: date) -> int:
    timestamp = now_sgt()
    requests = db.execute(
        select(TransportRequest)
        .where(
            TransportRequest.user_id == user.id,
            TransportRequest.request_kind == request_kind,
            TransportRequest.status == "active",
        )
        .order_by(TransportRequest.id.desc())
    ).scalars().all()
    cancelled = 0
    for transport_request in requests:
        if request_kind == "extra" and transport_request.single_date is not None and transport_request.single_date < reference_date:
            continue
        transport_request.status = "cancelled"
        transport_request.cancelled_at = timestamp
        transport_request.updated_at = timestamp
        cancelled += 1
    return cancelled


def cancel_transport_request_and_assignments(
    db: Session,
    *,
    transport_request: TransportRequest,
) -> None:
    timestamp = now_sgt()
    transport_request.status = "cancelled"
    transport_request.cancelled_at = timestamp
    transport_request.updated_at = timestamp

    assignments = db.execute(
        select(TransportAssignment).where(TransportAssignment.request_id == transport_request.id)
    ).scalars().all()
    for assignment in assignments:
        assignment.vehicle_id = None
        assignment.status = "cancelled"
        assignment.response_message = "Cancelled by web user"
        assignment.acknowledged_by_user = False
        assignment.acknowledged_at = None
        assignment.updated_at = timestamp
        assignment.notified_at = None


def acknowledge_transport_assignments(
    db: Session,
    *,
    transport_request: TransportRequest,
    service_date: date,
) -> int:
    timestamp = now_sgt()
    assignments = db.execute(
        select(TransportAssignment).where(
            TransportAssignment.request_id == transport_request.id,
            TransportAssignment.service_date == service_date,
            TransportAssignment.status == "confirmed",
            TransportAssignment.vehicle_id.is_not(None),
        )
    ).scalars().all()
    acknowledged = 0
    for assignment in assignments:
        assignment.acknowledged_by_user = True
        assignment.acknowledged_at = timestamp
        assignment.updated_at = timestamp
        acknowledged += 1
    return acknowledged


def build_web_transport_state(
    db: Session,
    *,
    user: User,
    service_date: date,
) -> WebTransportStateResponse:
    active_request = get_latest_active_transport_request(db, user=user, request_kind="regular")
    if active_request is None or not request_applies_to_date(active_request, service_date):
        return WebTransportStateResponse(
            chave=user.chave,
            end_rua=user.end_rua,
            zip=user.zip,
            status="available",
        )

    assignments = db.execute(
        select(TransportAssignment)
        .where(
            TransportAssignment.request_id == active_request.id,
            TransportAssignment.service_date == service_date,
        )
        .order_by(TransportAssignment.route_kind, TransportAssignment.id)
    ).scalars().all()
    confirmed_assignments = [
        assignment
        for assignment in assignments
        if assignment.status == "confirmed" and assignment.vehicle_id is not None
    ]
    confirmed_assignment = confirmed_assignments[0] if confirmed_assignments else None
    confirmed_vehicle = db.get(Vehicle, confirmed_assignment.vehicle_id) if confirmed_assignment is not None else None
    awareness_confirmed = bool(confirmed_assignments) and all(
        assignment.acknowledged_by_user for assignment in confirmed_assignments
    )

    if confirmed_assignment is not None and confirmed_vehicle is not None:
        return WebTransportStateResponse(
            chave=user.chave,
            end_rua=user.end_rua,
            zip=user.zip,
            status="confirmed",
            request_id=active_request.id,
            request_kind=active_request.request_kind,
            service_date=service_date,
            requested_time=active_request.requested_time,
            confirmation_deadline_time=active_request.requested_time,
            vehicle_type=confirmed_vehicle.tipo,
            vehicle_plate=confirmed_vehicle.placa,
            tolerance_minutes=confirmed_vehicle.tolerance,
            awareness_required=True,
            awareness_confirmed=awareness_confirmed,
        )

    return WebTransportStateResponse(
        chave=user.chave,
        end_rua=user.end_rua,
        zip=user.zip,
        status="pending",
        request_id=active_request.id,
        request_kind=active_request.request_kind,
        service_date=service_date,
        requested_time=active_request.requested_time,
        confirmation_deadline_time=active_request.requested_time,
        awareness_required=False,
        awareness_confirmed=False,
    )


def get_or_create_bot_session(db: Session, *, chat_id: str) -> TransportBotSession:
    session = db.execute(select(TransportBotSession).where(TransportBotSession.chat_id == chat_id)).scalar_one_or_none()
    if session is not None:
        return session

    timestamp = now_sgt()
    session = TransportBotSession(
        chat_id=chat_id,
        user_id=None,
        chave=None,
        state="awaiting_key",
        context_json=None,
        created_at=timestamp,
        updated_at=timestamp,
        last_message_at=timestamp,
    )
    db.add(session)
    db.flush()
    return session


def process_bot_message(db: Session, *, chat_id: str, message: str) -> TransportBotConversationResponse:
    session = get_or_create_bot_session(db, chat_id=chat_id)
    timestamp = now_sgt()
    session.last_message_at = timestamp
    session.updated_at = timestamp

    context = _load_session_context(session)
    normalized_message = " ".join(str(message or "").strip().split())
    replies: list[TransportBotReplyMessage] = []
    registration_completed = False
    request_created = False

    if session.state == "awaiting_key":
        normalized_key = _normalize_key_candidate(normalized_message)
        if normalized_key is None:
            replies.append(TransportBotReplyMessage(text="Send your 4-character alphanumeric key first."))
            return _save_bot_response(session, context, replies)

        session.chave = normalized_key
        user = find_user_by_chave(db, normalized_key)
        session.user_id = user.id if user is not None else None
        if user is not None and is_transport_registered_user(user):
            session.state = "ready"
            replies.append(TransportBotReplyMessage(text=f"Key {normalized_key} validated for {user.nome}."))
            replies.append(_menu_reply())
            return _save_bot_response(session, context, replies)

        session.state = "awaiting_name"
        if user is not None:
            _remember_existing_user(context, user)
        replies.append(TransportBotReplyMessage(text="Registration is incomplete. Enter your full name."))
        return _save_bot_response(session, context, replies)

    if session.state == "awaiting_name":
        try:
            context["nome"] = normalize_person_name(normalized_message)
        except ValueError:
            replies.append(TransportBotReplyMessage(text="The name must contain at least 3 characters."))
            return _save_bot_response(session, context, replies)
        session.state = "awaiting_project"
        replies.append(TransportBotReplyMessage(text="Enter the project.", options=_PROJECT_OPTIONS))
        return _save_bot_response(session, context, replies)

    if session.state == "awaiting_project":
        project = _normalize_project_code(normalized_message)
        if project is None:
            replies.append(TransportBotReplyMessage(text="Invalid project. Choose P80, P82, or P83.", options=_PROJECT_OPTIONS))
            return _save_bot_response(session, context, replies)
        context["projeto"] = project
        workplaces = list_workplaces(db)
        if not workplaces:
            replies.append(TransportBotReplyMessage(text="No workplace is registered in the system. Add a workplace before continuing."))
            return _save_bot_response(session, context, replies)
        session.state = "awaiting_workplace"
        replies.append(
            TransportBotReplyMessage(
                text="Choose your workplace by sending the name or the list number.",
                options=[f"{index + 1}. {row.workplace}" for index, row in enumerate(workplaces)],
            )
        )
        return _save_bot_response(session, context, replies)

    if session.state == "awaiting_workplace":
        selected_workplace = _resolve_workplace_choice(db, normalized_message)
        if selected_workplace is None:
            workplaces = list_workplaces(db)
            replies.append(
                TransportBotReplyMessage(
                    text="Invalid workplace. Choose an existing workplace by name or number.",
                    options=[f"{index + 1}. {row.workplace}" for index, row in enumerate(workplaces)],
                )
            )
            return _save_bot_response(session, context, replies)
        context["workplace"] = selected_workplace.workplace
        session.state = "awaiting_address"
        replies.append(TransportBotReplyMessage(text="Enter your home address."))
        return _save_bot_response(session, context, replies)

    if session.state == "awaiting_address":
        address = _normalize_free_text(normalized_message, min_length=3, max_length=255)
        if address is None:
            replies.append(TransportBotReplyMessage(text="Enter a valid home address."))
            return _save_bot_response(session, context, replies)
        context["end_rua"] = address
        session.state = "awaiting_zip"
        replies.append(TransportBotReplyMessage(text="Enter your ZIP code."))
        return _save_bot_response(session, context, replies)

    if session.state == "awaiting_zip":
        zip_code = _normalize_compact_text(normalized_message, max_length=10)
        if zip_code is None:
            replies.append(TransportBotReplyMessage(text="Enter a valid ZIP code."))
            return _save_bot_response(session, context, replies)
        context["zip"] = zip_code
        user = _upsert_registered_user_from_session(db, session=session, context=context)
        session.user_id = user.id
        session.state = "ready"
        registration_completed = True
        _ensure_transport_registration_checkin(db, user=user, chat_id=chat_id)
        replies.append(TransportBotReplyMessage(text=f"Registration completed for {user.nome}."))
        replies.append(_menu_reply())
        return _save_bot_response(
            session,
            context,
            replies,
            registration_completed=registration_completed,
        )

    if session.state == "awaiting_cancel_kind":
        request_kind = _resolve_request_kind(normalized_message)
        if request_kind is None:
            replies.append(TransportBotReplyMessage(text="Choose REGULAR, WEEKEND, or EXTRA.", options=_MENU_OPTIONS[:3]))
            return _save_bot_response(session, context, replies)
        user = _require_session_user(db, session)
        cancelled = cancel_transport_requests(db, user=user, request_kind=request_kind, reference_date=timestamp.date())
        if context.get("replace_after_cancel"):
            context.pop("replace_after_cancel", None)
            context["pending_kind"] = request_kind
            session.state = "awaiting_request_time"
            if cancelled == 0:
                replies.append(TransportBotReplyMessage(text=f"No active {_REQUEST_KIND_TO_LABEL[request_kind]} request was found. Enter the new time anyway."))
            else:
                replies.append(TransportBotReplyMessage(text=f"The {_REQUEST_KIND_TO_LABEL[request_kind]} request was removed. Enter the new time in hh:mm format."))
            return _save_bot_response(session, context, replies)

        session.state = "ready"
        if cancelled == 0:
            replies.append(TransportBotReplyMessage(text=f"No active {_REQUEST_KIND_TO_LABEL[request_kind]} request was found."))
        else:
            replies.append(TransportBotReplyMessage(text=f"The {_REQUEST_KIND_TO_LABEL[request_kind]} request was cancelled."))
        replies.append(_menu_reply())
        return _save_bot_response(session, context, replies)

    if session.state == "awaiting_request_time":
        requested_time = _normalize_time_message(normalized_message)
        request_kind = str(context.get("pending_kind") or "")
        if requested_time is None or request_kind not in _REQUEST_KIND_TO_RECURRENCE:
            replies.append(TransportBotReplyMessage(text="Enter the time in hh:mm format."))
            return _save_bot_response(session, context, replies)
        user = _require_session_user(db, session)
        transport_request = upsert_transport_request(
            db,
            user=user,
            request_kind=request_kind,
            requested_time=requested_time,
            requested_date=(timestamp.date() if request_kind == "extra" else None),
            created_via="bot",
        )
        session.state = "ready"
        context.pop("pending_kind", None)
        request_created = True
        replies.append(
            TransportBotReplyMessage(
                text=(
                    f"The {_REQUEST_KIND_TO_LABEL[transport_request.request_kind]} request was recorded for {transport_request.requested_time}. "
                    "Your name stays red until a vehicle is assigned."
                )
            )
        )
        replies.append(_menu_reply())
        return _save_bot_response(session, context, replies, request_created=request_created)

    user = _require_session_user(db, session)
    command = _normalize_command(normalized_message)
    request_kind = _resolve_request_kind(command)
    if request_kind is not None:
        session.state = "awaiting_request_time"
        context["pending_kind"] = request_kind
        replies.append(TransportBotReplyMessage(text="Enter the desired time in hh:mm format."))
        return _save_bot_response(session, context, replies)

    if command in {"CHANGE", "ALTERAR"}:
        session.state = "awaiting_cancel_kind"
        replies.append(
            TransportBotReplyMessage(
                text="Choose which type you want to replace. After that, send the new time.",
                options=_MENU_OPTIONS[:3],
            )
        )
        context["replace_after_cancel"] = True
        return _save_bot_response(session, context, replies)

    if command in {"CANCEL", "CANCELAR"}:
        session.state = "awaiting_cancel_kind"
        replies.append(TransportBotReplyMessage(text="Choose which type you want to cancel.", options=_MENU_OPTIONS[:3]))
        context.pop("replace_after_cancel", None)
        return _save_bot_response(session, context, replies)

    replies.append(TransportBotReplyMessage(text=f"Key validated for {user.nome}."))
    replies.append(_menu_reply())
    return _save_bot_response(session, context, replies)


def update_transport_assignment(
    db: Session,
    *,
    transport_request: TransportRequest,
    service_date: date,
    route_kind: str,
    status: str,
    vehicle: Vehicle | None,
    response_message: str | None,
    admin_user_id: int | None,
) -> tuple[TransportAssignment, bool]:
    timestamp = now_sgt()
    next_vehicle_id = vehicle.id if vehicle is not None else None
    assignment = db.execute(
        select(TransportAssignment).where(
            TransportAssignment.request_id == transport_request.id,
            TransportAssignment.service_date == service_date,
            TransportAssignment.route_kind == route_kind,
        )
    ).scalar_one_or_none()
    is_update = assignment is not None
    if assignment is None:
        assignment = TransportAssignment(
            request_id=transport_request.id,
            service_date=service_date,
            route_kind=route_kind,
            vehicle_id=next_vehicle_id,
            status=status,
            response_message=response_message,
            acknowledged_by_user=False,
            acknowledged_at=None,
            assigned_by_admin_id=admin_user_id,
            created_at=timestamp,
            updated_at=timestamp,
            notified_at=None,
        )
        db.add(assignment)
        db.flush()
    else:
        assignment_changed = (
            assignment.vehicle_id != next_vehicle_id
            or assignment.status != status
            or assignment.route_kind != route_kind
            or assignment.service_date != service_date
        )
        assignment.route_kind = route_kind
        assignment.vehicle_id = next_vehicle_id
        assignment.status = status
        assignment.response_message = response_message
        if status != "confirmed":
            assignment.acknowledged_by_user = False
            assignment.acknowledged_at = None
        elif assignment_changed:
            assignment.acknowledged_by_user = False
            assignment.acknowledged_at = None
        assignment.assigned_by_admin_id = admin_user_id
        assignment.updated_at = timestamp
        assignment.notified_at = None
    return assignment, is_update


def queue_assignment_notification(
    db: Session,
    *,
    transport_request: TransportRequest,
    assignment: TransportAssignment,
    user: User,
    vehicle: Vehicle | None,
    is_update: bool,
) -> TransportNotification | None:
    session = db.execute(
        select(TransportBotSession)
        .where(TransportBotSession.user_id == user.id)
        .order_by(TransportBotSession.updated_at.desc(), TransportBotSession.id.desc())
    ).scalar_one_or_none()
    if session is None:
        return None

    timestamp = now_sgt()
    message = _build_assignment_message(
        transport_request=transport_request,
        assignment=assignment,
        vehicle=vehicle,
        is_update=is_update,
    )
    notification = TransportNotification(
        user_id=user.id,
        chat_id=session.chat_id,
        request_id=transport_request.id,
        assignment_id=assignment.id,
        message=message,
        status="pending",
        created_at=timestamp,
        sent_at=None,
    )
    db.add(notification)
    return notification


def _build_vehicle_row(vehicle: Vehicle) -> TransportVehicleRow:
    return _build_vehicle_row_for_schedule(vehicle, schedule=None)


def _build_vehicle_row_for_schedule(
    vehicle: Vehicle,
    *,
    schedule: TransportVehicleSchedule | None,
) -> TransportVehicleRow:
    return TransportVehicleRow(
        id=vehicle.id,
        schedule_id=(schedule.id if schedule is not None else None),
        placa=vehicle.placa,
        tipo=vehicle.tipo,
        color=vehicle.color,
        lugares=vehicle.lugares,
        tolerance=vehicle.tolerance,
        service_scope=vehicle.service_scope,
        route_kind=(schedule.route_kind if schedule is not None else None),
    )


def _build_assignment_message(
    *,
    transport_request: TransportRequest,
    assignment: TransportAssignment,
    vehicle: Vehicle | None,
    is_update: bool,
) -> str:
    kind_label = _REQUEST_KIND_TO_LABEL[transport_request.request_kind]
    route_label = _ROUTE_KIND_TO_LABEL.get(assignment.route_kind, assignment.route_kind)
    if assignment.status == "confirmed" and vehicle is not None:
        prefix = "Your transport has been updated" if is_update else "Your transport has been confirmed"
        vehicle_description = f"{vehicle.tipo} {vehicle.placa}"
        if vehicle.color:
            vehicle_description = f"{vehicle_description}, color {vehicle.color}"
        return (
            f"{prefix}: {kind_label} at {transport_request.requested_time} ({route_label}) with {vehicle_description}. "
            f"Tolerance: {vehicle.tolerance} minutes."
        )
    if assignment.status == "rejected":
        return f"Your {kind_label} transport at {transport_request.requested_time} ({route_label}) was rejected."
    return f"Your {kind_label} transport at {transport_request.requested_time} ({route_label}) was cancelled."


def _build_vehicle_rows_for_dashboard(
    db: Session,
    *,
    service_date: date,
    route_kind: str,
) -> tuple[dict[str, list[TransportVehicleRow]], dict[int, TransportVehicleRow]]:
    vehicles_by_scope: dict[str, list[TransportVehicleRow]] = {
        "regular": [],
        "weekend": [],
        "extra": [],
    }
    vehicle_rows_by_id: dict[int, TransportVehicleRow] = {}

    schedule_rows = db.execute(
        select(TransportVehicleSchedule, Vehicle)
        .join(Vehicle, Vehicle.id == TransportVehicleSchedule.vehicle_id)
        .where(
            TransportVehicleSchedule.is_active.is_(True),
            TransportVehicleSchedule.route_kind == route_kind,
        )
        .order_by(TransportVehicleSchedule.service_scope, Vehicle.placa, TransportVehicleSchedule.id)
    ).all()
    schedule_ids = [schedule.id for schedule, _ in schedule_rows]
    exception_schedule_ids = {
        row.vehicle_schedule_id
        for row in db.execute(
            select(TransportVehicleScheduleException).where(
                TransportVehicleScheduleException.vehicle_schedule_id.in_(schedule_ids),
                TransportVehicleScheduleException.service_date == service_date,
            )
        ).scalars().all()
    } if schedule_ids else set()

    for schedule, vehicle in schedule_rows:
        if schedule.id in exception_schedule_ids:
            continue
        if not vehicle_schedule_applies_to_date(schedule, service_date):
            continue

        vehicle_row = _build_vehicle_row_for_schedule(vehicle, schedule=schedule)
        vehicles_by_scope.setdefault(schedule.service_scope, []).append(vehicle_row)
        vehicle_rows_by_id[vehicle.id] = vehicle_row

    for rows in vehicles_by_scope.values():
        rows.sort(key=lambda item: (item.placa, item.id))

    return vehicles_by_scope, vehicle_rows_by_id


def _build_schedule_specs_from_payload(payload: TransportVehicleCreate) -> list[dict[str, object]]:
    if payload.service_scope == "extra":
        return [
            {
                "service_scope": payload.service_scope,
                "route_kind": payload.route_kind,
                "recurrence_kind": "single_date",
                "service_date": payload.service_date,
                "weekday": None,
            }
        ]

    route_kinds = ["home_to_work", "work_to_home"]
    if payload.service_scope == "weekend":
        recurrence_kind = "matching_weekday" if payload.every_weekend else "single_date"
        return [
            {
                "service_scope": payload.service_scope,
                "route_kind": route_kind,
                "recurrence_kind": recurrence_kind,
                "service_date": (None if payload.every_weekend else payload.service_date),
                "weekday": (payload.service_date.weekday() if payload.every_weekend else None),
            }
            for route_kind in route_kinds
        ]

    return [
        {
            "service_scope": payload.service_scope,
            "route_kind": route_kind,
            "recurrence_kind": "weekday",
            "service_date": None,
            "weekday": None,
        }
        for route_kind in route_kinds
    ]


def _vehicle_has_active_schedule_on_date(
    db: Session,
    *,
    vehicle_id: int,
    service_scope: str,
    route_kind: str,
    service_date: date,
) -> bool:
    schedules = db.execute(
        select(TransportVehicleSchedule).where(
            TransportVehicleSchedule.vehicle_id == vehicle_id,
            TransportVehicleSchedule.service_scope == service_scope,
            TransportVehicleSchedule.route_kind == route_kind,
            TransportVehicleSchedule.is_active.is_(True),
        )
    ).scalars().all()
    if not schedules:
        return False

    schedule_ids = [schedule.id for schedule in schedules]
    exception_schedule_ids = {
        row.vehicle_schedule_id
        for row in db.execute(
            select(TransportVehicleScheduleException).where(
                TransportVehicleScheduleException.vehicle_schedule_id.in_(schedule_ids),
                TransportVehicleScheduleException.service_date == service_date,
            )
        ).scalars().all()
    } if schedule_ids else set()

    for schedule in schedules:
        if schedule.id in exception_schedule_ids:
            continue
        if vehicle_schedule_applies_to_date(schedule, service_date):
            return True
    return False


def find_transport_vehicle_schedule(
    db: Session,
    *,
    vehicle: Vehicle,
    service_date: date,
    route_kind: str,
) -> TransportVehicleSchedule | None:
    schedules = db.execute(
        select(TransportVehicleSchedule).where(
            TransportVehicleSchedule.vehicle_id == vehicle.id,
            TransportVehicleSchedule.route_kind == route_kind,
            TransportVehicleSchedule.is_active.is_(True),
        )
    ).scalars().all()
    if not schedules:
        return None

    schedule_ids = [schedule.id for schedule in schedules]
    exception_schedule_ids = {
        row.vehicle_schedule_id
        for row in db.execute(
            select(TransportVehicleScheduleException).where(
                TransportVehicleScheduleException.vehicle_schedule_id.in_(schedule_ids),
                TransportVehicleScheduleException.service_date == service_date,
            )
        ).scalars().all()
    } if schedule_ids else set()

    for schedule in schedules:
        if schedule.id in exception_schedule_ids:
            continue
        if vehicle_schedule_applies_to_date(schedule, service_date):
            return schedule
    return None


def get_paired_route_kind(route_kind: str) -> str | None:
    return _PAIRED_ROUTE_KIND.get(route_kind)


def _upsert_registered_user_from_session(db: Session, *, session: TransportBotSession, context: dict[str, str]) -> User:
    timestamp = now_sgt()
    user = db.get(User, session.user_id) if session.user_id is not None else None
    if user is None:
        if session.chave is None:
            raise ValueError("The user key is missing from the session.")
        user = find_user_by_chave(db, session.chave)
    if user is None:
        user = User(
            rfid=None,
            chave=normalize_user_key(session.chave or ""),
            nome=context["nome"],
            projeto=context["projeto"],
            workplace=context["workplace"],
            placa=None,
            end_rua=context["end_rua"],
            zip=context["zip"],
            cargo=None,
            email=None,
            local=None,
            checkin=None,
            time=None,
            last_active_at=timestamp,
            inactivity_days=0,
        )
        db.add(user)
        db.flush()
        return user

    user.nome = context["nome"]
    user.projeto = context["projeto"]
    user.workplace = context["workplace"]
    user.end_rua = context["end_rua"]
    user.zip = context["zip"]
    user.last_active_at = timestamp
    return user


def _ensure_transport_registration_checkin(db: Session, *, user: User, chat_id: str) -> bool:
    timestamp = now_sgt()
    latest_activity = resolve_latest_user_activity(db, user=user)
    if latest_activity is not None and latest_activity.action == "checkin" and is_same_singapore_day(latest_activity.event_time, timestamp):
        return False

    ensure_current_user_state_event(db, user=user)
    apply_user_state(
        user,
        action="checkin",
        event_time=timestamp,
        projeto=user.projeto,
        local=user.workplace or user.local,
    )
    request_hash = hashlib.sha1(f"bot-register|{chat_id}|{timestamp.isoformat()}".encode("utf-8")).hexdigest()
    create_user_sync_event(
        db,
        user=user,
        source="bot",
        action="checkin",
        event_time=timestamp,
        projeto=user.projeto,
        local=user.workplace or user.local,
        ontime=True,
        source_request_id=request_hash,
        device_id="transport-bot",
    )
    return True


def is_transport_registered_user(user: User) -> bool:
    normalized_name = " ".join(str(user.nome or "").strip().split())
    return bool(
        normalized_name
        and normalized_name not in _PLACEHOLDER_NAMES
        and user.projeto
        and user.workplace
        and user.end_rua
        and user.zip
    )


def _remember_existing_user(context: dict[str, str], user: User) -> None:
    if user.nome and user.nome not in _PLACEHOLDER_NAMES:
        context.setdefault("nome", user.nome)
    if user.projeto:
        context.setdefault("projeto", user.projeto)
    if user.workplace:
        context.setdefault("workplace", user.workplace)
    if user.end_rua:
        context.setdefault("end_rua", user.end_rua)
    if user.zip:
        context.setdefault("zip", user.zip)


def _load_session_context(session: TransportBotSession) -> dict[str, str]:
    raw_value = str(session.context_json or "").strip()
    if not raw_value:
        return {}
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _save_bot_response(
    session: TransportBotSession,
    context: dict[str, str],
    replies: list[TransportBotReplyMessage],
    *,
    registration_completed: bool = False,
    request_created: bool = False,
) -> TransportBotConversationResponse:
    session.context_json = json.dumps(context, ensure_ascii=True, separators=(",", ":")) if context else None
    return TransportBotConversationResponse(
        ok=True,
        state=session.state,
        user_key=session.chave,
        registration_completed=registration_completed,
        request_created=request_created,
        messages=replies,
    )


def _require_session_user(db: Session, session: TransportBotSession) -> User:
    user = db.get(User, session.user_id) if session.user_id is not None else None
    if user is None and session.chave:
        user = find_user_by_chave(db, session.chave)
    if user is None:
        raise ValueError("The bot session does not have a linked user.")
    return user


def _normalize_key_candidate(value: str) -> str | None:
    normalized = str(value or "").strip().upper()
    if len(normalized) != 4 or not normalized.isalnum():
        return None
    return normalized


def _normalize_project_code(value: str) -> str | None:
    normalized = str(value or "").strip().upper()
    return normalized if normalized in _PROJECT_OPTIONS else None


def _normalize_free_text(value: str, *, min_length: int, max_length: int) -> str | None:
    normalized = " ".join(str(value or "").strip().split())
    if len(normalized) < min_length or len(normalized) > max_length:
        return None
    return normalized


def _normalize_compact_text(value: str, *, max_length: int) -> str | None:
    normalized = str(value or "").strip()
    if not normalized or len(normalized) > max_length:
        return None
    return normalized


def _normalize_time_message(value: str) -> str | None:
    normalized = str(value or "").strip()
    parts = normalized.split(":")
    if len(parts) != 2 or any(not part.isdigit() for part in parts):
        return None
    hour, minute = int(parts[0]), int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def _normalize_command(value: str) -> str:
    collapsed = " ".join(str(value or "").strip().split())
    normalized = unicodedata.normalize("NFKD", collapsed)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized.upper()


def _resolve_request_kind(value: str) -> str | None:
    normalized = _normalize_command(value)
    if normalized == "REGULAR":
        return "regular"
    if normalized in {"FIM DE SEMANA", "WEEKEND"}:
        return "weekend"
    if normalized == "EXTRA":
        return "extra"
    return None


def _resolve_workplace_choice(db: Session, value: str) -> Workplace | None:
    workplaces = db.execute(select(Workplace).order_by(Workplace.workplace, Workplace.id)).scalars().all()
    if not workplaces:
        return None
    normalized = str(value or "").strip()
    if normalized.isdigit():
        index = int(normalized) - 1
        if 0 <= index < len(workplaces):
            return workplaces[index]
    lowered = normalized.casefold()
    for workplace in workplaces:
        if workplace.workplace.casefold() == lowered:
            return workplace
    return None


def _menu_reply() -> TransportBotReplyMessage:
    return TransportBotReplyMessage(text="Choose an option.", options=_MENU_OPTIONS)