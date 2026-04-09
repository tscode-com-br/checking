from uuid import uuid4

from sqlalchemy.orm import Session

from ..models import CheckEvent
from .admin_updates import notify_admin_data_changed
from .time_utils import now_sgt


def log_event(
    db: Session,
    *,
    source: str,
    action: str,
    status: str,
    message: str,
    idempotency_key: str | None = None,
    rfid: str | None = None,
    project: str | None = None,
    device_id: str | None = None,
    local: str | None = None,
    request_path: str | None = None,
    http_status: int | None = None,
    submitted_at=None,
    retry_count: int = 0,
    details: str | None = None,
    ontime: bool | None = None,
    commit: bool = False,
) -> CheckEvent:
    derived_ontime = ontime
    if derived_ontime is None and source == "device" and action in {"checkin", "checkout"}:
        derived_ontime = True

    event = CheckEvent(
        idempotency_key=idempotency_key or str(uuid4()),
        source=source[:20],
        action=action[:16],
        status=status[:16],
        message=message[:255],
        details=(details or "")[:1000] or None,
        request_path=(request_path or "")[:120] or None,
        http_status=http_status,
        device_id=(device_id or "")[:80] or None,
        local=(local or "")[:40] or None,
        rfid=rfid,
        project=project,
        ontime=derived_ontime,
        event_time=now_sgt(),
        submitted_at=submitted_at,
        retry_count=retry_count,
    )
    db.add(event)
    if commit:
        db.commit()
        notify_admin_data_changed("event")
    return event