import asyncio
import dataclasses
import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import SessionLocal, get_db
from ..models import Accident, AccidentUserReport, AdminAccessRequest, ManagedLocation, PendingUserRegistration, Project, TransportRequest, User, UserProjectMembership
from ..schemas import (
    AccidentLocationOption,
    AccidentProjectOption,
    EmergencyCallResponse,
    ProjectRow,
    WebAccidentAcknowledgeRequest,
    WebAccidentActiveItem,
    WebAccidentOpenRequest,
    WebAccidentReportRequest,
    WebAccidentStateResponse,
    WebAccidentUserReport,
    AccidentVideoUploadResponse,
    WebCheckHistoryItem,
    WebCheckHistoryListResponse,
    WebCheckHistoryResponse,
    WebGeofenceCircle,
    WebGeofencesResponse,
    WebLocationOptionsResponse,
    WebPasswordActionResponse,
    WebPasswordChangeRequest,
    WebPasswordLoginRequest,
    WebPasswordRegisterRequest,
    WebPasswordStatusResponse,
    WebUserSelfRegistrationResponse,
    WebUserSelfRegistrationRequest,
    WebCheckSubmitRequest,
    WebCheckSubmitResponse,
    WebLocationMatchRequest,
    WebLocationMatchResponse,
    WebProjectUpdateRequest,
    WebProjectUpdateResponse,
    WebUserProjectsResponse,
    WebUserProjectsUpdateRequest,
    WebUserProjectsUpdateResponse,
    WebTransportActionResponse,
    WebTransportAddressUpdateRequest,
    WebTransportRequestAction,
    WebTransportRequestCreate,
    WebTransportStateResponse,
)
from ..services.admin_updates import (
    notify_admin_data_changed,
    notify_transport_data_changed,
    notify_web_check_data_changed,
    transport_updates_broker,
    web_check_updates_broker,
)
from ..services.accident_lifecycle import (
    AccidentAlreadyActiveError,
    acknowledge_accident,
    attach_video_upload,
    list_active_accidents,
    list_active_accident,
    open_accident,
    upsert_user_safety_report,
)
from ..services.twilio_caller import (
    EmergencyCallAlreadyFiredError,
    EmergencyCallFailedError,
    TwilioNotConfiguredError,
    make_emergency_call,
)
from ..services.accident_numbering import format_accident_number
from ..services.forms_submit import FormsSubmitChannel, submit_forms_event
from ..services.location_matching import (
    resolve_captured_location_label,
    resolve_location_match,
    resolve_submission_local,
)
from ..services.managed_locations import filter_locations_for_projects
from ..services.location_settings import (
    get_location_accuracy_threshold_meters,
    get_mixed_zone_interval_minutes_for_projects,
    get_minimum_checkout_distance_meters_for_project,
)
from ..services.passwords import hash_password, verify_password
from ..services.project_catalog import ensure_known_project, list_projects
from ..services.transport_reevaluation_events import emit_transport_reevaluation_event
from ..services.email_sender import queue_help_request_emails
from ..services.event_logger import log_event
from ..services.time_utils import build_timezone_label, now_sgt, resolve_project_timezone_name
from ..services.transport import (
    TransportRequestConflictError,
    acknowledge_transport_assignments,
    build_web_transport_state,
    cancel_transport_request_and_assignments,
    upsert_transport_request,
)
from ..services.user_projects import (
    assign_existing_user_active_project,
    list_user_project_names,
    normalize_user_project_names,
    replace_user_project_memberships,
    resolve_user_active_project,
    user_belongs_to_project,
)
from ..services.checking_history import list_checking_history
from ..services.user_sync import (
    build_web_check_history_state,
    ensure_web_user,
    find_user_by_chave,
    normalize_user_key,
)

router = APIRouter(prefix="/api/web", tags=["web-check"])

WEB_USER_SESSION_KEY = "web_user_chave"
UNKNOWN_WEB_USER_DETAIL = "A chave do usuario nao esta cadastrada"
WEB_TRANSPORT_REQUEST_LABELS = {
    "regular": "Transporte Rotineiro",
    "weekend": "Transporte Fim de Semana",
    "extra": "Transporte Extra",
}

MAX_VIDEO_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_VIDEO_TYPES = {"video/webm", "video/mp4", "video/quicktime"}

WEB_CHECK_CHANNEL = FormsSubmitChannel(
    event_label="Web check event",
    user_sync_source="web_forms",
    log_source="web",
    request_path="/api/web/check",
    device_id="web-check",
    default_local="Web",
)
# P7 observability: requests carrying the header "X-Client: checking-android" (the Kotlin app) are
# logged with device_id="checking-android" so app traffic is distinguishable from the browser web app
# in check_events (both otherwise log as source=web with device_id="web-check"). Browser unaffected.
CHECKING_ANDROID_CLIENT = "checking-android"
WEB_CHECK_ANDROID_CHANNEL = dataclasses.replace(WEB_CHECK_CHANNEL, device_id=CHECKING_ANDROID_CLIENT)
WEB_NON_OPERATIONAL_SUBMIT_LOCALS = frozenset({
    "Localização não Cadastrada",
})


def _build_project_row(project: Project) -> ProjectRow:
    return ProjectRow(
        id=project.id,
        name=project.name,
        country_code=project.country_code,
        country_name=project.country_name,
        timezone_name=project.timezone_name,
        timezone_label=build_timezone_label(
            country_name=project.country_name,
            timezone_name=project.timezone_name,
        ),
        address=str(project.address or "").strip(),
        zip_code=str(project.zip_code or "").strip(),
        forms_enabled=bool(project.forms_enabled),
        transport_enabled=bool(project.transport_enabled),
        emergency_phone=str(project.emergency_phone or "").strip(),
    )


def _validate_public_chave(value: str) -> str:
    normalized = normalize_user_key(value)
    if len(normalized) != 4 or not normalized.isalnum():
        raise HTTPException(status_code=422, detail="A chave deve ter 4 caracteres alfanumericos")
    return normalized


def _reject_non_operational_web_submit_local(
    local: str | None,
    *,
    is_android_client: bool = False,
    action: str | None = None,
) -> None:
    normalized_local = " ".join(str(local or "").strip().split())
    if normalized_local not in WEB_NON_OPERATIONAL_SUBMIT_LOCALS:
        return
    # Change A enabler (plan002 P5.1): the Kotlin app (X-Client: checking-android) may CHECK IN at
    # "Localização não Cadastrada" — a real continuation state when the user is near but not inside any
    # registered area. The browser web app, and ANY check-out, still 422 (the deliberate invariant).
    if is_android_client and str(action or "").strip().lower() == "checkin":
        return
    raise HTTPException(
        status_code=422,
        detail="O estado 'Localização não Cadastrada' nao e um local operacional valido para submit pela Web.",
    )


def _get_web_session_chave(request: Request) -> str | None:
    session_value = request.session.get(WEB_USER_SESSION_KEY)
    if not isinstance(session_value, str):
        return None

    normalized = normalize_user_key(session_value)
    if len(normalized) != 4 or not normalized.isalnum():
        request.session.pop(WEB_USER_SESSION_KEY, None)
        return None
    return normalized


def _encode_sse(payload: dict[str, str]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _set_web_session_chave(request: Request, chave: str) -> None:
    request.session[WEB_USER_SESSION_KEY] = chave


def _clear_web_session_chave(request: Request) -> None:
    request.session.pop(WEB_USER_SESSION_KEY, None)


def _raise_unknown_web_user() -> None:
    raise HTTPException(status_code=404, detail=UNKNOWN_WEB_USER_DETAIL)


def _build_web_password_status(
    *, request: Request, user: User | None, chave: str, pending_approval: bool = False,
) -> WebPasswordStatusResponse:
    has_password = bool(user and user.senha)
    authenticated = has_password and _get_web_session_chave(request) == chave

    if not has_password:
        return WebPasswordStatusResponse(
            found=user is not None,
            chave=chave,
            has_password=False,
            authenticated=False,
            message="Digite sua chave e crie uma senha.",
            pending_approval=pending_approval,
        )

    if not authenticated:
        return WebPasswordStatusResponse(
            found=True,
            chave=chave,
            has_password=True,
            authenticated=False,
            message="Digite sua senha para iniciar.",
        )

    return WebPasswordStatusResponse(
        found=True,
        chave=chave,
        has_password=True,
        authenticated=True,
        message="Aplicacao liberada.",
    )


def _list_web_projects(db: Session) -> list[ProjectRow]:
    return [_build_project_row(project) for project in list_projects(db)]


def _normalize_known_web_user_projects(db: Session, project_names: list[str]) -> list[str]:
    return normalize_user_project_names(
        ensure_known_project(db, project_name)
        for project_name in project_names
    )


def _build_web_user_projects_response(db: Session, user: User) -> WebUserProjectsResponse:
    project_names = list_user_project_names(db, user)
    return WebUserProjectsResponse(
        projects=project_names,
        active_project=resolve_user_active_project(user, project_names),
    )


def _require_known_user_membership_project(db: Session, user: User, project_name: str) -> str:
    normalized_project_name = ensure_known_project(db, project_name)
    if not user_belongs_to_project(db, user, normalized_project_name):
        raise HTTPException(
            status_code=409,
            detail="O projeto informado nao pertence aos projetos cadastrados do usuario.",
        )
    return normalized_project_name


def _require_authenticated_web_user(request: Request, db: Session) -> User:
    session_chave = _get_web_session_chave(request)
    if session_chave is None:
        raise HTTPException(status_code=401, detail="Sessao do usuario invalida ou expirada")

    user = find_user_by_chave(db, session_chave)
    if user is None or not user.senha:
        _clear_web_session_chave(request)
        raise HTTPException(status_code=401, detail="Sessao do usuario invalida ou expirada")
    return user


def _require_matching_authenticated_web_user(request: Request, db: Session, chave: str) -> User:
    user = _require_authenticated_web_user(request, db)
    normalized_chave = _validate_public_chave(chave)
    if user.chave != normalized_chave:
        raise HTTPException(status_code=401, detail="A chave informada nao corresponde a sessao atual")
    return user


def _resolve_web_transport_route_preference(*, db: Session, user: User) -> str | None:
    history_state = build_web_check_history_state(db, chave=user.chave)
    if history_state.current_action == "checkin":
        return "work_to_home"
    if history_state.current_action == "checkout":
        return "home_to_work"
    return None


def _resolve_web_transport_state(*, db: Session, user: User) -> WebTransportStateResponse:
    return build_web_transport_state(
        db,
        user=user,
        service_date=now_sgt().date(),
        preferred_route_kind=_resolve_web_transport_route_preference(db=db, user=user),
    )


def _require_owned_transport_request(*, user: User, db: Session, request_id: int):
    transport_request = db.get(TransportRequest, request_id)
    if transport_request is None or transport_request.user_id != user.id or transport_request.status != "active":
        raise HTTPException(status_code=404, detail="Solicitacao de transporte nao encontrada")
    return transport_request


def _build_web_transport_request_message(*, request_kind: str, created: bool) -> str:
    request_label = WEB_TRANSPORT_REQUEST_LABELS.get(request_kind, "Transporte")
    if created:
        return f"Solicitacao de {request_label} enviada."
    return f"Ja existe uma solicitacao de {request_label} ativa."


def _has_complete_web_transport_address(user: User) -> bool:
    normalized_address = str(user.end_rua or "").strip()
    normalized_zip_code = "".join(ch for ch in str(user.zip or "") if ch.isdigit())
    return len(normalized_address) >= 3 and len(normalized_zip_code) == 6


def _validate_web_transport_request_eligibility(*, user: User, payload: WebTransportRequestCreate) -> None:
    if not _has_complete_web_transport_address(user):
        raise HTTPException(status_code=400, detail="Cadastre um endereco completo antes de solicitar o transporte.")

    if payload.request_kind == "extra":
        if payload.requested_date is None:
            raise HTTPException(status_code=400, detail="Informe a data do transporte extra.")
        if not payload.requested_time:
            raise HTTPException(status_code=400, detail="Informe o horario do transporte extra.")


def _create_web_transport_request_response(
    payload: WebTransportRequestCreate,
    request: Request,
    db: Session,
) -> WebTransportActionResponse:
    user = _require_matching_authenticated_web_user(request, db, payload.chave)
    _validate_web_transport_request_eligibility(user=user, payload=payload)

    requested_time = payload.requested_time or now_sgt().strftime("%H:%M")
    requested_date = payload.requested_date if payload.request_kind == "extra" else None

    try:
        _transport_request, created = upsert_transport_request(
            db,
            user=user,
            request_kind=payload.request_kind,
            requested_time=requested_time,
            requested_date=requested_date,
            created_via="web",
            selected_weekdays=payload.selected_weekdays,
        )
    except TransportRequestConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if created:
        db.commit()
        notify_admin_data_changed("event")
        emit_transport_reevaluation_event(
            event_type="transport_request_changed",
            reason="event",
            source="web_transport",
            message="A web transport request changed the rider demand state.",
            request_id=_transport_request.id,
        )

    return WebTransportActionResponse(
        ok=True,
        message=_build_web_transport_request_message(request_kind=payload.request_kind, created=created),
        state=_resolve_web_transport_state(db=db, user=user),
    )


@router.get("/auth/status", response_model=WebPasswordStatusResponse)
def get_web_password_status(
    request: Request,
    chave: str = Query(min_length=4, max_length=4),
    db: Session = Depends(get_db),
) -> WebPasswordStatusResponse:
    normalized = _validate_public_chave(chave)
    user = find_user_by_chave(db, normalized)
    # plan003 — when there is no User, this chave may have a self-registration awaiting approval.
    pending_approval = False
    if user is None:
        pending_approval = (
            db.execute(
                select(PendingUserRegistration.id).where(PendingUserRegistration.chave == normalized)
            ).first()
            is not None
        )
    status_payload = _build_web_password_status(
        request=request, user=user, chave=normalized, pending_approval=pending_approval,
    )
    if not status_payload.authenticated and _get_web_session_chave(request) == normalized:
        _clear_web_session_chave(request)
    return status_payload


@router.post("/auth/register-password", response_model=WebPasswordActionResponse)
def register_web_password(
    payload: WebPasswordRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebPasswordActionResponse:
    normalized = _validate_public_chave(payload.chave)
    user = find_user_by_chave(db, normalized)
    if user is None:
        _clear_web_session_chave(request)
        _raise_unknown_web_user()

    if user.senha:
        raise HTTPException(status_code=409, detail="Esta chave ja possui uma senha cadastrada")

    user.senha = hash_password(payload.senha)
    db.commit()
    _set_web_session_chave(request, normalized)
    return WebPasswordActionResponse(
        ok=True,
        authenticated=True,
        has_password=True,
        message="Senha cadastrada com sucesso.",
    )


def create_user_from_registration(
    db: Session,
    *,
    chave: str,
    nome: str,
    projetos: list[str],
    email: str | None,
    password_hash: str | None,
) -> User:
    """Create a ``User`` + project memberships from a (self-)registration.

    Shared by the legacy self-registration path and (plan003) the admin
    approval path. Adds + flushes the user and replaces its memberships;
    the **caller** owns commit / session / notify. Byte-identical to the
    original inline construction in ``register_web_user``.
    """
    user = User(
        rfid=None,
        chave=chave,
        senha=password_hash,
        nome=nome,
        projeto=projetos[0],
        workplace=None,
        placa=None,
        end_rua=None,
        zip=None,
        email=email,
        local=None,
        checkin=None,
        time=None,
        last_active_at=now_sgt(),
        inactivity_days=0,
    )
    db.add(user)
    db.flush()
    replace_user_project_memberships(db, user, projetos)
    return user


def _registration_queue_full_response() -> WebUserSelfRegistrationResponse:
    return WebUserSelfRegistrationResponse(
        ok=False,
        authenticated=False,
        has_password=False,
        message="Fila de cadastro cheia. Informe ao administrador do sistema.",
        status="queue_full",
        pending_approval=False,
        queue_full=True,
    )


@router.post("/auth/register-user", response_model=WebUserSelfRegistrationResponse, status_code=201)
def register_web_user(
    payload: WebUserSelfRegistrationRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> WebUserSelfRegistrationResponse:
    normalized = _validate_public_chave(payload.chave)
    project_names = _normalize_known_web_user_projects(db, payload.projetos)
    if find_user_by_chave(db, normalized) is not None:
        raise HTTPException(status_code=409, detail="Esta chave ja esta cadastrada")
    existing_pending = db.execute(
        select(PendingUserRegistration.id).where(PendingUserRegistration.chave == normalized)
    ).first()
    if existing_pending is not None:
        raise HTTPException(status_code=409, detail="Ja existe uma solicitacao pendente para essa chave")
    admin_access_request = db.execute(
        select(AdminAccessRequest).where(AdminAccessRequest.chave == normalized)
    ).scalar_one_or_none()
    if admin_access_request is not None:
        raise HTTPException(status_code=409, detail="Ja existe uma solicitacao pendente para essa chave")

    # plan003 — system-wide approval gate (decision 1). Flag OFF restores the legacy
    # create-and-authenticate behavior exactly (instant rollback without a deploy).
    if not settings.check_user_approval_required:
        user = create_user_from_registration(
            db,
            chave=normalized,
            nome=payload.nome,
            projetos=project_names,
            email=payload.email,
            password_hash=hash_password(payload.senha),
        )
        db.commit()
        _set_web_session_chave(request, normalized)
        notify_admin_data_changed("admin")
        notify_admin_data_changed("register")
        return WebUserSelfRegistrationResponse(
            ok=True,
            authenticated=True,
            has_password=True,
            message="Cadastro concluido com sucesso.",
            status="registered",
            projects=project_names,
            active_project=user.projeto,
        )

    # Gate ON: queue the registration for admin approval — NO User, NO session.
    limit = settings.pending_user_registration_limit
    if db.execute(select(func.count()).select_from(PendingUserRegistration)).scalar_one() >= limit:
        response.status_code = 200
        return _registration_queue_full_response()

    db.add(
        PendingUserRegistration(
            chave=normalized,
            nome_completo=payload.nome,
            projetos_json=json.dumps(project_names),
            email=payload.email,
            password_hash=hash_password(payload.senha),
            client=(request.headers.get("X-Client") or "web")[:16],
            requested_at=now_sgt(),
        )
    )
    db.flush()
    # Cap race guard: if a concurrent insert pushed us past the limit, undo and report queue-full.
    if db.execute(select(func.count()).select_from(PendingUserRegistration)).scalar_one() > limit:
        db.rollback()
        response.status_code = 200
        return _registration_queue_full_response()
    db.commit()
    notify_admin_data_changed("admin")
    notify_admin_data_changed("register")
    response.status_code = 202
    return WebUserSelfRegistrationResponse(
        ok=True,
        authenticated=False,
        has_password=False,
        message="Cadastro recebido. Aguardando aprovacao do administrador.",
        status="pending",
        pending_approval=True,
        projects=project_names,
        active_project="",
    )


@router.get("/projects", response_model=list[ProjectRow])
def list_web_projects(db: Session = Depends(get_db)) -> list[ProjectRow]:
    return _list_web_projects(db)


@router.get("/user-projects", response_model=WebUserProjectsResponse)
def get_web_user_projects(request: Request, db: Session = Depends(get_db)) -> WebUserProjectsResponse:
    user = _require_authenticated_web_user(request, db)
    return _build_web_user_projects_response(db, user)


@router.put("/user-projects", response_model=WebUserProjectsUpdateResponse)
def update_web_user_projects(
    payload: WebUserProjectsUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebUserProjectsUpdateResponse:
    user = _require_authenticated_web_user(request, db)
    project_names = _normalize_known_web_user_projects(db, payload.projects)
    replace_user_project_memberships(db, user, project_names)
    db.commit()
    notify_admin_data_changed("register")
    return WebUserProjectsUpdateResponse(
        ok=True,
        message="Projetos atualizados com sucesso.",
        projects=project_names,
        active_project=user.projeto,
    )


@router.put("/project", response_model=WebProjectUpdateResponse)
def update_web_project(
    payload: WebProjectUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebProjectUpdateResponse:
    user = _require_authenticated_web_user(request, db)
    project_name = _require_known_user_membership_project(db, user, payload.project)
    project_names = assign_existing_user_active_project(db, user, project_name)
    db.commit()
    notify_admin_data_changed("register")
    return WebProjectUpdateResponse(
        ok=True,
        message="Projeto ativo atualizado com sucesso.",
        project=project_name,
        projects=project_names,
        active_project=user.projeto,
    )


@router.post("/auth/login", response_model=WebPasswordActionResponse)
def login_web_user(
    payload: WebPasswordLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebPasswordActionResponse:
    normalized = _validate_public_chave(payload.chave)
    user = find_user_by_chave(db, normalized)
    if user is None:
        _clear_web_session_chave(request)
        _raise_unknown_web_user()

    if not user.senha:
        _clear_web_session_chave(request)
        raise HTTPException(status_code=404, detail="Nao existe senha cadastrada para esta chave")

    if not verify_password(payload.senha, user.senha):
        _clear_web_session_chave(request)
        raise HTTPException(status_code=401, detail="Chave ou senha invalida")

    _set_web_session_chave(request, normalized)
    return WebPasswordActionResponse(
        ok=True,
        authenticated=True,
        has_password=True,
        message="Autenticacao concluida.",
    )


@router.post("/auth/logout", response_model=WebPasswordActionResponse)
def logout_web_user(request: Request) -> WebPasswordActionResponse:
    _clear_web_session_chave(request)
    return WebPasswordActionResponse(
        ok=True,
        authenticated=False,
        has_password=False,
        message="Sessao encerrada.",
    )


@router.post("/auth/change-password", response_model=WebPasswordActionResponse)
def change_web_password(
    payload: WebPasswordChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebPasswordActionResponse:
    normalized = _validate_public_chave(payload.chave)
    user = find_user_by_chave(db, normalized)
    if user is None:
        _clear_web_session_chave(request)
        _raise_unknown_web_user()

    if not user.senha:
        _clear_web_session_chave(request)
        raise HTTPException(status_code=404, detail="Nao existe senha cadastrada para esta chave")

    if not verify_password(payload.senha_antiga, user.senha):
        raise HTTPException(status_code=401, detail="Senha antiga invalida")

    user.senha = hash_password(payload.nova_senha)
    db.commit()
    _set_web_session_chave(request, normalized)
    return WebPasswordActionResponse(
        ok=True,
        authenticated=True,
        has_password=True,
        message="Senha alterada com sucesso.",
    )


@router.get("/transport/state", response_model=WebTransportStateResponse)
def get_web_transport_state(
    request: Request,
    chave: str = Query(min_length=4, max_length=4),
    db: Session = Depends(get_db),
) -> WebTransportStateResponse:
    user = _require_matching_authenticated_web_user(request, db, chave)
    return _resolve_web_transport_state(db=db, user=user)


@router.get("/transport/stream")
async def stream_web_transport_updates(
    request: Request,
    chave: str = Query(min_length=4, max_length=4),
) -> StreamingResponse:
    # Authenticate with a short-lived session that is released BEFORE the streaming loop.
    # Using Depends(get_db) here would keep a pooled DB connection checked out for the entire
    # (indefinite) life of the SSE stream, exhausting the pool with only a handful of clients.
    with SessionLocal() as db:
        _require_matching_authenticated_web_user(request, db, chave)
    subscriber_id, queue = transport_updates_broker.subscribe()

    async def event_generator():
        try:
            yield _encode_sse({"reason": "connected"})
            while True:
                if await request.is_disconnected():
                    break

                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            transport_updates_broker.unsubscribe(subscriber_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/check/stream")
async def stream_web_check_updates(
    request: Request,
    chave: str = Query(min_length=4, max_length=4),
) -> StreamingResponse:
    # Authenticate with a short-lived session that is released BEFORE the streaming loop.
    # Using Depends(get_db) here would keep a pooled DB connection checked out for the entire
    # (indefinite) life of the SSE stream, exhausting the pool with only a handful of clients.
    with SessionLocal() as db:
        _require_matching_authenticated_web_user(request, db, chave)
    subscriber_id, queue = web_check_updates_broker.subscribe()

    async def event_generator():
        try:
            yield _encode_sse({"reason": "connected"})
            while True:
                if await request.is_disconnected():
                    break

                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            web_check_updates_broker.unsubscribe(subscriber_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/transport/address", response_model=WebTransportActionResponse)
def update_web_transport_address(
    payload: WebTransportAddressUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebTransportActionResponse:
    user = _require_matching_authenticated_web_user(request, db, payload.chave)
    user.end_rua = payload.end_rua
    user.zip = payload.zip
    db.commit()
    notify_admin_data_changed("register")
    emit_transport_reevaluation_event(
        event_type="transport_user_context_changed",
        reason="register",
        source="web_transport",
        message="A rider transport address changed and may affect future planning.",
    )
    return WebTransportActionResponse(
        ok=True,
        message="Endereco atualizado com sucesso.",
        state=_resolve_web_transport_state(db=db, user=user),
    )


@router.post("/transport/vehicle-request", response_model=WebTransportActionResponse)
def create_web_transport_vehicle_request(
    payload: WebTransportRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> WebTransportActionResponse:
    return _create_web_transport_request_response(payload, request, db)


@router.post("/transport/request", response_model=WebTransportActionResponse)
def create_web_transport_request(
    payload: WebTransportRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> WebTransportActionResponse:
    return _create_web_transport_request_response(payload, request, db)


@router.post("/transport/cancel", response_model=WebTransportActionResponse)
def cancel_web_transport_request(
    payload: WebTransportRequestAction,
    request: Request,
    db: Session = Depends(get_db),
) -> WebTransportActionResponse:
    user = _require_matching_authenticated_web_user(request, db, payload.chave)
    transport_request = _require_owned_transport_request(user=user, db=db, request_id=payload.request_id)
    cancel_transport_request_and_assignments(db, transport_request=transport_request)
    db.commit()
    notify_admin_data_changed("event")
    emit_transport_reevaluation_event(
        event_type="transport_request_changed",
        reason="event",
        source="web_transport",
        message="A web transport request was cancelled and the day demand changed.",
        request_id=transport_request.id,
    )
    return WebTransportActionResponse(
        ok=True,
        message="Solicitacao de transporte cancelada.",
        state=_resolve_web_transport_state(db=db, user=user),
    )


@router.post("/transport/acknowledge", response_model=WebTransportActionResponse)
def acknowledge_web_transport_request(
    payload: WebTransportRequestAction,
    request: Request,
    db: Session = Depends(get_db),
) -> WebTransportActionResponse:
    user = _require_matching_authenticated_web_user(request, db, payload.chave)
    transport_request = _require_owned_transport_request(user=user, db=db, request_id=payload.request_id)
    acknowledged = acknowledge_transport_assignments(
        db,
        transport_request=transport_request,
        service_date=now_sgt().date(),
    )
    if acknowledged == 0:
        raise HTTPException(status_code=409, detail="Ainda nao existe confirmacao de transporte para registrar ciencia")

    db.commit()
    notify_admin_data_changed("event")
    notify_transport_data_changed("event")
    return WebTransportActionResponse(
        ok=True,
        message="Ciencia registrada com sucesso.",
        state=_resolve_web_transport_state(db=db, user=user),
    )


@router.get("/check/state", response_model=WebCheckHistoryResponse)
def get_web_check_state(
    request: Request,
    chave: str = Query(min_length=4, max_length=4),
    db: Session = Depends(get_db),
) -> WebCheckHistoryResponse:
    _require_matching_authenticated_web_user(request, db, chave)
    return build_web_check_history_state(db, chave=_validate_public_chave(chave))


@router.get("/check/history", response_model=WebCheckHistoryListResponse)
def get_web_check_history(
    request: Request,
    chave: str = Query(min_length=4, max_length=4),
    db: Session = Depends(get_db),
) -> WebCheckHistoryListResponse:
    # Read-only, additive (change D). Same access model as /check/state: a matching authenticated
    # web session. Returns the user's full check-in/out history (newest-first) including location.
    user = _require_matching_authenticated_web_user(request, db, chave)
    items = [
        WebCheckHistoryItem(
            action="checkin" if row.atividade == "check-in" else "checkout",
            projeto=row.projeto,
            local=row.local,
            time=row.time,
            informe=row.informe,
        )
        for row in list_checking_history(db, chave=user.chave)
    ]
    return WebCheckHistoryListResponse(items=items)


@router.get("/check/locations", response_model=WebLocationOptionsResponse)
def get_web_check_locations(request: Request, db: Session = Depends(get_db)) -> WebLocationOptionsResponse:
    user = _require_authenticated_web_user(request, db)
    user_project_names = list_user_project_names(db, user)
    rows = db.execute(
        select(ManagedLocation).order_by(ManagedLocation.local, ManagedLocation.id)
    ).scalars().all()
    items = [row.local for row in filter_locations_for_projects(rows, user_project_names)]
    return WebLocationOptionsResponse(
        items=items,
        location_accuracy_threshold_meters=get_location_accuracy_threshold_meters(db),
        mixed_zone_interval_minutes=get_mixed_zone_interval_minutes_for_projects(db, user_project_names),
    )


@router.get("/check/geofences", response_model=WebGeofencesResponse)
def get_web_check_geofences(
    request: Request,
    chave: str = Query(min_length=4, max_length=4),
    db: Session = Depends(get_db),
) -> WebGeofencesResponse:
    # Coarse bounding circles for the user's project locations — native geofence wake-up
    # geometry for the mobile app (§23.2). Precise matching stays in POST /check/location.
    user = _require_matching_authenticated_web_user(request, db, chave)
    user_project_names = list_user_project_names(db, user)
    rows = db.execute(
        select(ManagedLocation).order_by(ManagedLocation.local, ManagedLocation.id)
    ).scalars().all()
    circles = [
        WebGeofenceCircle(
            id=loc.id,
            local=loc.local,
            center_lat=loc.latitude,
            center_lng=loc.longitude,
            radius_meters=float(loc.tolerance_meters),
        )
        for loc in filter_locations_for_projects(rows, user_project_names)
    ]
    return WebGeofencesResponse(locations=circles)


@router.post("/check/location", response_model=WebLocationMatchResponse)
def match_web_check_location(
    payload: WebLocationMatchRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebLocationMatchResponse:
    user = _require_authenticated_web_user(request, db)
    user_project_names = list_user_project_names(db, user)
    accuracy_threshold_meters = get_location_accuracy_threshold_meters(db)
    minimum_checkout_distance_meters = get_minimum_checkout_distance_meters_for_project(db, user.projeto)
    all_locations = db.execute(
        select(ManagedLocation).order_by(ManagedLocation.local, ManagedLocation.id)
    ).scalars().all()
    locations = filter_locations_for_projects(all_locations, user_project_names)

    if not locations:
        return WebLocationMatchResponse(
            matched=False,
            resolved_local=None,
            label="Sem localização cadastrada",
            status="no_known_locations",
            message="Nao ha localizacoes conhecidas cadastradas para validar a posicao nos projetos cadastrados do usuario.",
            accuracy_meters=payload.accuracy_meters,
            accuracy_threshold_meters=accuracy_threshold_meters,
            minimum_checkout_distance_meters=minimum_checkout_distance_meters,
            nearest_workplace_distance_meters=None,
        )

    if (
        payload.accuracy_meters is None
        or payload.accuracy_meters > float(accuracy_threshold_meters)
    ):
        accuracy_message = (
            "Nao foi possivel confirmar o local porque a precisao da localizacao esta acima do limite permitido."
        )
        return WebLocationMatchResponse(
            matched=False,
            resolved_local=None,
            label="Precisao insuficiente",
            status="accuracy_too_low",
            message=accuracy_message,
            accuracy_meters=payload.accuracy_meters,
            accuracy_threshold_meters=accuracy_threshold_meters,
            minimum_checkout_distance_meters=minimum_checkout_distance_meters,
            nearest_workplace_distance_meters=None,
        )

    match_result = resolve_location_match(
        managed_locations=locations,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_meters=payload.accuracy_meters,
    )
    matched_location = match_result.matched_location
    captured_label = resolve_captured_location_label(
        location=matched_location,
        nearest_workplace_distance_meters=match_result.nearest_workplace_distance_meters,
        minimum_checkout_distance_meters=minimum_checkout_distance_meters,
    )

    if matched_location is None:
        status = (
            "outside_workplace"
            if captured_label is not None
            else "not_in_known_location"
        )
        label = captured_label or "Localização não Cadastrada"
        return WebLocationMatchResponse(
            matched=False,
            resolved_local=None,
            label=label,
            status=status,
            message="",
            accuracy_meters=payload.accuracy_meters,
            accuracy_threshold_meters=accuracy_threshold_meters,
            minimum_checkout_distance_meters=minimum_checkout_distance_meters,
            nearest_workplace_distance_meters=match_result.nearest_workplace_distance_meters,
        )

    resolved_local = resolve_submission_local(matched_location)
    label = captured_label or matched_location.local
    return WebLocationMatchResponse(
        matched=True,
        resolved_local=resolved_local,
        label=label,
        status="matched",
        message=f"Localizacao identificada em {label}.",
        accuracy_meters=payload.accuracy_meters,
        accuracy_threshold_meters=accuracy_threshold_meters,
        minimum_checkout_distance_meters=minimum_checkout_distance_meters,
        nearest_workplace_distance_meters=match_result.nearest_workplace_distance_meters,
    )


@router.post("/check", response_model=WebCheckSubmitResponse)
def submit_web_check(
    payload: WebCheckSubmitRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebCheckSubmitResponse:
    user = _require_matching_authenticated_web_user(request, db, payload.chave)
    payload.projeto = _require_known_user_membership_project(db, user, payload.projeto)
    is_android_client = request.headers.get("X-Client") == CHECKING_ANDROID_CLIENT
    _reject_non_operational_web_submit_local(
        payload.local,
        is_android_client=is_android_client,
        action=payload.action,
    )
    channel = WEB_CHECK_ANDROID_CHANNEL if is_android_client else WEB_CHECK_CHANNEL
    response = submit_forms_event(
        db,
        chave=payload.chave,
        projeto=payload.projeto,
        action=payload.action,
        informe=payload.informe,
        local=payload.local,
        event_time=payload.event_time,
        client_event_id=payload.client_event_id,
        ensure_user=ensure_web_user,
        channel=channel,
    )
    return WebCheckSubmitResponse(**response.model_dump())


# ---------------------------------------------------------------------------
# E1 — Accident state & open
# ---------------------------------------------------------------------------


@router.get("/check/accident/state", response_model=WebAccidentStateResponse)
def get_web_accident_state(
    request: Request,
    chave: str = Query(min_length=4, max_length=4),
    db: Session = Depends(get_db),
) -> WebAccidentStateResponse:
    user = _require_matching_authenticated_web_user(request, db, chave)
    actives = list_active_accidents(db)
    if not actives:
        return WebAccidentStateResponse(is_active=False)

    # Prefer accidents the user belongs to. Fall back to the full list when
    # the user has no membership match (legacy behaviour kept so the banner
    # still shows for everyone during a global accident).
    user_project_ids = {
        m.project_id
        for m in db.execute(
            select(UserProjectMembership).where(UserProjectMembership.user_id == user.id)
        ).scalars().all()
    }
    matching = [a for a in actives if a.project_id in user_project_ids]
    relevant = matching if matching else actives

    items: list[WebAccidentActiveItem] = []
    for accident in relevant:
        report = db.execute(
            select(AccidentUserReport).where(
                AccidentUserReport.accident_id == accident.id,
                AccidentUserReport.user_id == user.id,
            )
        ).scalar_one_or_none()
        current_user_report = None
        if report is not None:
            current_user_report = WebAccidentUserReport(
                zone=(
                    "safety" if report.zone == "safety"
                    else "accident" if report.zone == "accident"
                    else None
                ),
                status=(
                    "ok" if report.status == "ok"
                    else "help" if report.status == "help"
                    else None
                ),
                reported_at=report.reported_at,
            )
        items.append(WebAccidentActiveItem(
            accident_id=accident.id,
            accident_number_label=format_accident_number(accident.accident_number),
            project_id=accident.project_id,
            project_name=accident.project_name_snapshot,
            location_name=accident.location_name_snapshot,
            description=accident.description or None,
            awareness_status=report.awareness_status if report else "waiting",
            current_user_report=current_user_report,
        ))

    # Legacy/compat scalars come from the first relevant accident.
    first = items[0]
    return WebAccidentStateResponse(
        is_active=True,
        accident_id=first.accident_id,
        accident_number_label=first.accident_number_label,
        project_id=first.project_id,
        project_name=first.project_name,
        location_name=first.location_name,
        description=first.description,
        awareness_status=first.awareness_status,
        current_user_report=first.current_user_report,
        active_accidents=items,
    )


@router.post("/check/accident/open", response_model=WebAccidentStateResponse)
def open_web_accident(
    payload: WebAccidentOpenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebAccidentStateResponse:
    user = _require_matching_authenticated_web_user(request, db, payload.chave)
    try:
        accident = open_accident(
            db,
            origin="web",
            project_id=payload.project_id,
            location_id=payload.location_id,
            custom_location_name=payload.custom_location_name,
            opened_by_admin_id=None,
            opened_by_user_id=user.id,
            reporter_zone=payload.zone,
            reporter_status=payload.status,
            description=payload.description,
        )
    except AccidentAlreadyActiveError:
        raise HTTPException(status_code=409, detail="Outro usuario ja reportou um acidente.")
    log_event(
        db,
        source="web",
        action="accident_open",
        status="done",
        message="Accident opened by web user",
        request_path="/api/web/check/accident/open",
        http_status=200,
        rfid=user.chave,
        details=f"accident_number={accident.accident_number} project_id={payload.project_id}",
        commit=True,
    )
    return get_web_accident_state(request=request, chave=payload.chave, db=db)


@router.post("/check/accident/report", response_model=WebAccidentStateResponse)
def report_web_accident_status(
    payload: WebAccidentReportRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> WebAccidentStateResponse:
    user = _require_matching_authenticated_web_user(request, db, payload.chave)
    active = list_active_accident(db)
    if active is None:
        raise HTTPException(status_code=409, detail="Nenhum acidente em curso.")
    _, fired_help = upsert_user_safety_report(db, accident=active, user=user, zone=payload.zone, status=payload.status)
    if fired_help:
        background_tasks.add_task(queue_help_request_emails, accident_id=active.id, requester_user_id=user.id)
    log_event(
        db,
        source="web",
        action="accident_report",
        status="done",
        message="User safety report submitted",
        request_path="/api/web/check/accident/report",
        http_status=200,
        rfid=user.chave,
        details=f"accident_id={active.id} zone={payload.zone} status={payload.status}",
        commit=True,
    )
    return get_web_accident_state(request=request, chave=payload.chave, db=db)


# ---------------------------------------------------------------------------
# E3a — Acknowledge accident
# ---------------------------------------------------------------------------

@router.post("/check/accident/acknowledge")
def acknowledge_web_accident(
    payload: WebAccidentAcknowledgeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    user = _require_matching_authenticated_web_user(request, db, payload.chave)
    actives = list_active_accidents(db)
    if not actives:
        raise HTTPException(status_code=409, detail="Nenhum acidente em curso.")

    if payload.accident_id is not None:
        # Targeted ack: caller must explicitly identify which active accident
        # to acknowledge. Reject if the id is not currently active.
        target = next((a for a in actives if a.id == payload.accident_id), None)
        if target is None:
            raise HTTPException(status_code=404, detail="Acidente não está ativo.")
    else:
        # Legacy fallback: pick the first active accident matching the user's
        # projects, or the first global active accident if none match.
        user_project_ids = {
            m.project_id
            for m in db.execute(
                select(UserProjectMembership).where(UserProjectMembership.user_id == user.id)
            ).scalars().all()
        }
        matching = [a for a in actives if a.project_id in user_project_ids]
        target = matching[0] if matching else actives[0]

    acknowledge_accident(db, target.id, user)
    log_event(
        db,
        source="web",
        action="accident_ack",
        status="done",
        message="User acknowledged accident",
        request_path="/api/web/check/accident/acknowledge",
        http_status=200,
        rfid=user.chave,
        details=f"accident_id={target.id}",
        commit=True,
    )
    return {"ok": True, "accident_id": target.id}


# ---------------------------------------------------------------------------
# E3b — Emergency call (user-triggered)
# ---------------------------------------------------------------------------

@router.post("/check/accident/emergency-call", response_model=EmergencyCallResponse)
def trigger_user_emergency_call(
    payload: WebAccidentAcknowledgeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> EmergencyCallResponse:
    user = _require_matching_authenticated_web_user(request, db, payload.chave)
    actives = list_active_accidents(db)
    user_project_ids = {
        m.project_id
        for m in db.execute(
            select(UserProjectMembership).where(UserProjectMembership.user_id == user.id)
        ).scalars().all()
    }
    matching = [a for a in actives if a.project_id in user_project_ids]
    active = matching[0] if matching else None
    if active is None:
        raise HTTPException(status_code=404, detail="Nenhum acidente em curso para seu projeto.")

    project = db.get(Project, active.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    from ..services.time_utils import now_sgt as _now
    try:
        log = make_emergency_call(
            db,
            accident=active,
            project=project,
            triggered_by_user=user,
            reporter_name=user.nome,
            reporter_local=user.local or active.location_name_snapshot,
            event_time=_now(),
        )
    except EmergencyCallAlreadyFiredError:
        raise HTTPException(
            status_code=409,
            detail="Uma chamada de emergência já foi realizada por outro usuário neste acidente.",
        )
    except TwilioNotConfiguredError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except EmergencyCallFailedError as exc:
        raise HTTPException(status_code=502, detail=exc.message)

    log_event(
        db,
        source="web",
        action="accident_call",
        status="done",
        message=f"Emergency call #{log.call_number} initiated by user",
        request_path="/api/web/check/accident/emergency-call",
        http_status=200,
        rfid=user.chave,
        details=f"accident_id={active.id} call_sid={log.call_sid}",
        commit=True,
    )
    return EmergencyCallResponse(
        call_number=log.call_number,
        call_number_label=str(log.call_number).zfill(6),
        call_sid=log.call_sid,
        call_status=log.call_status,
        message=f"Chamada de emergência #{str(log.call_number).zfill(6)} iniciada.",
    )


# ---------------------------------------------------------------------------
# E3 — Video upload
# ---------------------------------------------------------------------------


async def stream_upload_to_storage(
    *,
    object_key: str,
    upload_file: UploadFile,
    content_type: str,
    max_bytes: int,
) -> tuple[int, str]:
    from ..services.object_storage import stream_upload_to_storage as _stream_upload
    return await _stream_upload(
        object_key=object_key,
        upload_file=upload_file,
        content_type=content_type,
        max_bytes=max_bytes,
    )


@router.post("/check/accident/video", response_model=AccidentVideoUploadResponse)
async def upload_accident_video(
    request: Request,
    chave: str = Form(...),
    idempotency_key: str = Form(..., min_length=8, max_length=80),
    duration_seconds: int | None = Form(None),
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> AccidentVideoUploadResponse:
    user = _require_matching_authenticated_web_user(request, db, chave)
    active = list_active_accident(db)
    if active is None:
        raise HTTPException(status_code=409, detail="Nenhum acidente em curso.")
    if video.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=415, detail="Tipo de video nao suportado.")

    accident_label = format_accident_number(active.accident_number)
    ext_map = {"video/webm": "webm", "video/mp4": "mp4", "video/quicktime": "mov"}
    ext = ext_map[video.content_type]
    safe_key = idempotency_key.replace("/", "_").replace(" ", "_")
    object_key = f"accidents/{accident_label}/{user.chave}/{safe_key}.{ext}"

    size_bytes, public_url = await stream_upload_to_storage(
        object_key=object_key,
        upload_file=video,
        content_type=video.content_type,
        max_bytes=MAX_VIDEO_BYTES,
    )

    upload = attach_video_upload(
        db,
        accident=active,
        user=user,
        object_key=object_key,
        public_url=public_url,
        content_type=video.content_type,
        size_bytes=size_bytes,
        duration_seconds=duration_seconds,
        idempotency_key=idempotency_key,
    )
    log_event(
        db,
        source="web",
        action="accident_video",
        status="done",
        message="Accident video uploaded",
        request_path="/api/web/check/accident/video",
        http_status=200,
        rfid=user.chave,
        details=f"accident_id={active.id} size_bytes={size_bytes}",
        commit=True,
    )
    return AccidentVideoUploadResponse(
        video_id=upload.id,
        public_url=upload.public_url,
        captured_at=upload.captured_at,
    )


@router.get("/check/accident/wizard/projects", response_model=list[AccidentProjectOption])
def list_web_accident_projects(
    request: Request,
    chave: str = Query(...),
    db: Session = Depends(get_db),
) -> list[AccidentProjectOption]:
    _require_matching_authenticated_web_user(request, db, chave)
    return [AccidentProjectOption(id=p.id, name=p.name) for p in list_projects(db)]


@router.get("/check/accident/wizard/locations", response_model=list[AccidentLocationOption])
def list_web_accident_locations(
    request: Request,
    chave: str = Query(...),
    project_id: int = Query(...),
    db: Session = Depends(get_db),
) -> list[AccidentLocationOption]:
    _require_matching_authenticated_web_user(request, db, chave)
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto nao encontrado.")
    options = []
    for loc in db.execute(select(ManagedLocation)).scalars().all():
        try:
            projects = json.loads(loc.projects_json or "[]")
        except Exception:
            projects = []
        if project.name in projects:
            options.append(AccidentLocationOption(id=loc.id, name=loc.local, registered=True))
    return options
