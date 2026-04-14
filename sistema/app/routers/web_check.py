from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import WebCheckSubmitRequest, WebCheckSubmitResponse
from ..services.forms_submit import FormsSubmitChannel, submit_forms_event
from ..services.user_sync import ensure_web_user

router = APIRouter(prefix="/api/web", tags=["web-check"])

WEB_CHECK_CHANNEL = FormsSubmitChannel(
    event_label="Web check event",
    user_sync_source="web_forms",
    log_source="web",
    request_path="/api/web/check",
    device_id="web-check",
    default_local="Web",
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