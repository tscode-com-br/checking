from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import WebCheckHistoryResponse, WebCheckSubmitRequest, WebCheckSubmitResponse
from ..services.forms_submit import FormsSubmitChannel, submit_forms_event
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