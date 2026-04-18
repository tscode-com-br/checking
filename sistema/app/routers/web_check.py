from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ManagedLocation, User
from ..schemas import (
    WebCheckHistoryResponse,
    WebLocationOptionsResponse,
    WebPasswordActionResponse,
    WebPasswordChangeRequest,
    WebPasswordLoginRequest,
    WebPasswordRegisterRequest,
    WebPasswordStatusResponse,
    WebCheckSubmitRequest,
    WebCheckSubmitResponse,
    WebLocationMatchRequest,
    WebLocationMatchResponse,
)
from ..services.forms_submit import FormsSubmitChannel, submit_forms_event
from ..services.location_matching import (
    resolve_captured_location_label,
    resolve_location_match,
    resolve_submission_local,
)
from ..services.location_settings import get_location_accuracy_threshold_meters
from ..services.passwords import hash_password, verify_password
from ..services.user_sync import (
    build_web_check_history_state,
    ensure_web_user,
    find_user_by_chave,
    normalize_user_key,
)

router = APIRouter(prefix="/api/web", tags=["web-check"])

WEB_USER_SESSION_KEY = "web_user_chave"

WEB_CHECK_CHANNEL = FormsSubmitChannel(
    event_label="Web check event",
    user_sync_source="web_forms",
    log_source="web",
    request_path="/api/web/check",
    device_id="web-check",
    default_local="Web",
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


def _set_web_session_chave(request: Request, chave: str) -> None:
    request.session[WEB_USER_SESSION_KEY] = chave


def _clear_web_session_chave(request: Request) -> None:
    request.session.pop(WEB_USER_SESSION_KEY, None)


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
        user, _ = ensure_web_user(db, chave=normalized, projeto=payload.projeto)

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


@router.post("/auth/login", response_model=WebPasswordActionResponse)
def login_web_user(
    payload: WebPasswordLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebPasswordActionResponse:
    normalized = _validate_public_chave(payload.chave)
    user = find_user_by_chave(db, normalized)
    if user is None or not user.senha:
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


@router.post("/auth/change-password", response_model=WebPasswordActionResponse)
def change_web_password(
    payload: WebPasswordChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebPasswordActionResponse:
    normalized = _validate_public_chave(payload.chave)
    user = find_user_by_chave(db, normalized)
    if user is None or not user.senha:
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
    _require_authenticated_web_user(request, db)
    items = db.execute(
        select(ManagedLocation.local).order_by(ManagedLocation.local, ManagedLocation.id)
    ).scalars().all()
    return WebLocationOptionsResponse(items=items)


@router.post("/check/location", response_model=WebLocationMatchResponse)
def match_web_check_location(
    payload: WebLocationMatchRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebLocationMatchResponse:
    _require_authenticated_web_user(request, db)
    accuracy_threshold_meters = get_location_accuracy_threshold_meters(db)
    locations = db.execute(
        select(ManagedLocation).order_by(ManagedLocation.local, ManagedLocation.id)
    ).scalars().all()

    if not locations:
        return WebLocationMatchResponse(
            matched=False,
            resolved_local=None,
            label="Sem localização cadastrada",
            status="no_known_locations",
            message="Nao ha localizacoes conhecidas cadastradas para validar a posicao.",
            accuracy_meters=payload.accuracy_meters,
            accuracy_threshold_meters=accuracy_threshold_meters,
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
            nearest_workplace_distance_meters=None,
        )

    match_result = resolve_location_match(
        managed_locations=locations,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    matched_location = match_result.matched_location
    captured_label = resolve_captured_location_label(
        location=matched_location,
        nearest_workplace_distance_meters=match_result.nearest_workplace_distance_meters,
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
        nearest_workplace_distance_meters=match_result.nearest_workplace_distance_meters,
    )


@router.post("/check", response_model=WebCheckSubmitResponse)
def submit_web_check(
    payload: WebCheckSubmitRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebCheckSubmitResponse:
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