from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ManagedLocation
from ..schemas import (
    WebCheckHistoryResponse,
    WebLocationOptionsResponse,
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
from ..services.user_sync import build_web_check_history_state, ensure_web_user, normalize_user_key

router = APIRouter(prefix="/api/web", tags=["web-check"])

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


@router.get("/check/state", response_model=WebCheckHistoryResponse)
def get_web_check_state(
    chave: str = Query(min_length=4, max_length=4),
    db: Session = Depends(get_db),
) -> WebCheckHistoryResponse:
    return build_web_check_history_state(db, chave=_validate_public_chave(chave))


@router.get("/check/locations", response_model=WebLocationOptionsResponse)
def get_web_check_locations(db: Session = Depends(get_db)) -> WebLocationOptionsResponse:
    items = db.execute(
        select(ManagedLocation.local).order_by(ManagedLocation.local, ManagedLocation.id)
    ).scalars().all()
    return WebLocationOptionsResponse(items=items)


@router.post("/check/location", response_model=WebLocationMatchResponse)
def match_web_check_location(
    payload: WebLocationMatchRequest,
    db: Session = Depends(get_db),
) -> WebLocationMatchResponse:
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
        label = captured_label or "Localização Desconhecida"
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
    db: Session = Depends(get_db),
) -> WebCheckSubmitResponse:
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