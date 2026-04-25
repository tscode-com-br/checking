import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AdminAccessRequest, ManagedLocation, Project, TransportRequest, User
from ..schemas import (
    ProjectRow,
    WebCheckHistoryResponse,
    WebLocationOptionsResponse,
    WebPasswordActionResponse,
    WebPasswordChangeRequest,
    WebPasswordLoginRequest,
    WebPasswordRegisterRequest,
    WebPasswordStatusResponse,
    WebUserSelfRegistrationRequest,
    WebCheckSubmitRequest,
    WebCheckSubmitResponse,
    WebLocationMatchRequest,
    WebLocationMatchResponse,
    WebProjectUpdateRequest,
    WebProjectUpdateResponse,
    WebTransportActionResponse,
    WebTransportAddressUpdateRequest,
    WebTransportRequestAction,
    WebTransportRequestCreate,
    WebTransportStateResponse,
)
from ..services.admin_updates import (
    notify_admin_data_changed,
    notify_transport_data_changed,
    transport_updates_broker,
)
from ..services.forms_submit import FormsSubmitChannel, submit_forms_event
from ..services.location_matching import (
    resolve_captured_location_label,
    resolve_location_match,
    resolve_submission_local,
)
from ..services.managed_locations import filter_locations_for_project
from ..services.location_settings import (
    get_location_accuracy_threshold_meters,
    get_minimum_checkout_distance_meters_for_project,
)
from ..services.passwords import hash_password, verify_password
from ..services.project_catalog import ensure_known_project, list_projects
from ..services.time_utils import build_timezone_label, now_sgt, resolve_project_timezone_name
from ..services.transport import (
    acknowledge_transport_assignments,
    build_web_transport_state,
    cancel_transport_request_and_assignments,
    upsert_transport_request,
)
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

WEB_CHECK_CHANNEL = FormsSubmitChannel(
    event_label="Web check event",
    user_sync_source="web_forms",
    log_source="web",
    request_path="/api/web/check",
    device_id="web-check",
    default_local="Web",
)


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
    )


def _validate_public_chave(value: str) -> str:
    normalized = normalize_user_key(value)
    if len(normalized) != 4 or not normalized.isalnum():
        raise HTTPException(status_code=422, detail="A chave deve ter 4 caracteres alfanumericos")
    return normalized


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


def _build_web_password_status(*, request: Request, user: User | None, chave: str) -> WebPasswordStatusResponse:
    has_password = bool(user and user.senha)
    authenticated = has_password and _get_web_session_chave(request) == chave

    if not has_password:
        return WebPasswordStatusResponse(
            found=user is not None,
            chave=chave,
            has_password=False,
            authenticated=False,
            message="Digite sua chave e crie uma senha.",
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


def _create_web_transport_request_response(
    payload: WebTransportRequestCreate,
    request: Request,
    db: Session,
) -> WebTransportActionResponse:
    user = _require_matching_authenticated_web_user(request, db, payload.chave)

    service_date = now_sgt().date()
    requested_time = payload.requested_time or now_sgt().strftime("%H:%M")
    requested_date = payload.requested_date if payload.request_kind == "extra" else None
    if payload.request_kind == "extra" and requested_date is None:
        requested_date = service_date

    _transport_request, created = upsert_transport_request(
        db,
        user=user,
        request_kind=payload.request_kind,
        requested_time=requested_time,
        requested_date=requested_date,
        created_via="web",
        selected_weekdays=payload.selected_weekdays,
    )
    if created:
        db.commit()
        notify_admin_data_changed("event")
        notify_transport_data_changed("event")

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
    status_payload = _build_web_password_status(request=request, user=user, chave=normalized)
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


@router.post("/auth/register-user", response_model=WebPasswordActionResponse, status_code=201)
def register_web_user(
    payload: WebUserSelfRegistrationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebPasswordActionResponse:
    normalized = _validate_public_chave(payload.chave)
    payload.projeto = ensure_known_project(db, payload.projeto)
    existing_user = find_user_by_chave(db, normalized)
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="Esta chave ja esta cadastrada")
    pending_request = db.execute(select(AdminAccessRequest).where(AdminAccessRequest.chave == normalized)).scalar_one_or_none()
    if pending_request is not None:
        raise HTTPException(status_code=409, detail="Ja existe uma solicitacao pendente para essa chave")

    user = User(
        rfid=None,
        chave=normalized,
        senha=hash_password(payload.senha),
        nome=payload.nome,
        projeto=payload.projeto,
        workplace=None,
        placa=None,
        end_rua=None,
        zip=None,
        cargo=None,
        email=payload.email,
        local=None,
        checkin=None,
        time=None,
        last_active_at=now_sgt(),
        inactivity_days=0,
    )
    db.add(user)
    db.commit()
    _set_web_session_chave(request, normalized)
    notify_admin_data_changed("admin")
    notify_admin_data_changed("register")
    return WebPasswordActionResponse(
        ok=True,
        authenticated=True,
        has_password=True,
        message="Cadastro concluido com sucesso.",
    )


@router.get("/projects", response_model=list[ProjectRow])
def list_web_projects(db: Session = Depends(get_db)) -> list[ProjectRow]:
    return _list_web_projects(db)


@router.put("/project", response_model=WebProjectUpdateResponse)
def update_web_project(
    payload: WebProjectUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebProjectUpdateResponse:
    user = _require_matching_authenticated_web_user(request, db, payload.chave)
    payload.projeto = ensure_known_project(db, payload.projeto)
    if user.projeto == payload.projeto:
        return WebProjectUpdateResponse(ok=True, message="Projeto atualizado com sucesso.", project=user.projeto)

    user.projeto = payload.projeto
    db.commit()
    notify_admin_data_changed("register")
    return WebProjectUpdateResponse(ok=True, message="Projeto atualizado com sucesso.", project=user.projeto)


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
    db: Session = Depends(get_db),
) -> StreamingResponse:
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
    notify_transport_data_changed("register")
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
    notify_transport_data_changed("event")
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


@router.get("/check/locations", response_model=WebLocationOptionsResponse)
def get_web_check_locations(request: Request, db: Session = Depends(get_db)) -> WebLocationOptionsResponse:
    user = _require_authenticated_web_user(request, db)
    rows = db.execute(
        select(ManagedLocation).order_by(ManagedLocation.local, ManagedLocation.id)
    ).scalars().all()
    items = [row.local for row in filter_locations_for_project(rows, user.projeto)]
    return WebLocationOptionsResponse(
        items=items,
        location_accuracy_threshold_meters=get_location_accuracy_threshold_meters(db),
    )


@router.post("/check/location", response_model=WebLocationMatchResponse)
def match_web_check_location(
    payload: WebLocationMatchRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebLocationMatchResponse:
    user = _require_authenticated_web_user(request, db)
    accuracy_threshold_meters = get_location_accuracy_threshold_meters(db)
    minimum_checkout_distance_meters = get_minimum_checkout_distance_meters_for_project(db, user.projeto)
    all_locations = db.execute(
        select(ManagedLocation).order_by(ManagedLocation.local, ManagedLocation.id)
    ).scalars().all()
    locations = filter_locations_for_project(all_locations, user.projeto)

    if not locations:
        return WebLocationMatchResponse(
            matched=False,
            resolved_local=None,
            label="Sem localização cadastrada",
            status="no_known_locations",
            message="Nao ha localizacoes conhecidas cadastradas para validar a posicao no projeto atual.",
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
    payload.projeto = ensure_known_project(db, payload.projeto)
    _require_matching_authenticated_web_user(request, db, payload.chave)
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
        channel=WEB_CHECK_CHANNEL,
    )
    return WebCheckSubmitResponse(**response.model_dump())