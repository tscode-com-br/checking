from __future__ import annotations

from collections import deque
from datetime import date
from uuid import uuid4

from ..schemas import (
    TransportReevaluationCatalogEntry,
    TransportReevaluationCatalogResponse,
    TransportReevaluationEvent,
)
from .admin_updates import notify_transport_data_changed
from .time_utils import now_sgt


_TRANSPORT_REEVALUATION_CATALOG: tuple[TransportReevaluationCatalogEntry, ...] = (
    TransportReevaluationCatalogEntry(
        event_type="transport_request_changed",
        description="A transport request was created or replaced, changing the demand that the day snapshot must represent.",
        downstream_actions=[
            "refresh_snapshot",
            "revalidate_constraints",
            "rebuild_proposal",
            "regenerate_export",
            "refresh_transport_state",
        ],
    ),
    TransportReevaluationCatalogEntry(
        event_type="transport_user_context_changed",
        description="A rider context input changed, such as pickup address, affecting future operational proposals.",
        downstream_actions=[
            "refresh_snapshot",
            "rebuild_proposal",
            "regenerate_export",
            "refresh_transport_state",
        ],
    ),
    TransportReevaluationCatalogEntry(
        event_type="transport_vehicle_supply_changed",
        description="Vehicle inventory changed, affecting the supply available for planning and assignment review.",
        downstream_actions=[
            "refresh_snapshot",
            "revalidate_constraints",
            "rebuild_proposal",
            "regenerate_export",
            "refresh_transport_state",
        ],
    ),
    TransportReevaluationCatalogEntry(
        event_type="transport_vehicle_schedule_changed",
        description="Vehicle availability or route schedule changed and must trigger a new operational read of the day.",
        downstream_actions=[
            "refresh_snapshot",
            "revalidate_constraints",
            "rebuild_proposal",
            "regenerate_export",
            "refresh_transport_state",
        ],
    ),
    TransportReevaluationCatalogEntry(
        event_type="transport_assignment_changed",
        description="An assignment decision changed and downstream artifacts may need to be refreshed or revalidated.",
        downstream_actions=[
            "refresh_snapshot",
            "revalidate_constraints",
            "regenerate_export",
            "refresh_transport_state",
        ],
    ),
    TransportReevaluationCatalogEntry(
        event_type="transport_timing_policy_changed",
        description="A global or date-specific timing policy changed and must be reflected in reads, proposals and exports.",
        downstream_actions=[
            "refresh_snapshot",
            "rebuild_proposal",
            "regenerate_export",
            "refresh_transport_state",
        ],
    ),
    TransportReevaluationCatalogEntry(
        event_type="transport_workplace_context_changed",
        description="A workplace operational context changed, affecting grouping, timing and future planning context.",
        downstream_actions=[
            "refresh_snapshot",
            "rebuild_proposal",
            "regenerate_export",
            "refresh_transport_state",
        ],
    ),
    TransportReevaluationCatalogEntry(
        event_type="transport_operational_review_changed",
        description="An operational proposal was validated, approved or rejected during manual review of the day.",
        downstream_actions=[
            "refresh_snapshot",
            "revalidate_constraints",
            "regenerate_export",
            "refresh_transport_state",
        ],
    ),
)

_TRANSPORT_REEVALUATION_CATALOG_INDEX = {
    entry.event_type: entry for entry in _TRANSPORT_REEVALUATION_CATALOG
}
_RECENT_TRANSPORT_REEVALUATION_EVENTS: deque[TransportReevaluationEvent] = deque(maxlen=50)


def list_transport_reevaluation_catalog() -> list[TransportReevaluationCatalogEntry]:
    return [entry.model_copy(deep=True) for entry in _TRANSPORT_REEVALUATION_CATALOG]


def list_recent_transport_reevaluation_events(*, limit: int = 20) -> list[TransportReevaluationEvent]:
    normalized_limit = max(1, min(limit, 50))
    return [
        entry.model_copy(deep=True)
        for entry in list(_RECENT_TRANSPORT_REEVALUATION_EVENTS)[-normalized_limit:][::-1]
    ]


def build_transport_reevaluation_catalog_response(*, limit: int = 20) -> TransportReevaluationCatalogResponse:
    return TransportReevaluationCatalogResponse(
        catalog=list_transport_reevaluation_catalog(),
        recent_events=list_recent_transport_reevaluation_events(limit=limit),
    )


def clear_transport_reevaluation_events() -> None:
    _RECENT_TRANSPORT_REEVALUATION_EVENTS.clear()


def emit_transport_reevaluation_event(
    *,
    event_type: str,
    reason: str,
    source: str,
    message: str,
    service_date: date | None = None,
    route_kind: str | None = None,
    request_id: int | None = None,
    vehicle_id: int | None = None,
    schedule_id: int | None = None,
    workplace_id: int | None = None,
    proposal_key: str | None = None,
) -> TransportReevaluationEvent:
    catalog_entry = _TRANSPORT_REEVALUATION_CATALOG_INDEX.get(event_type)
    if catalog_entry is None:
        raise ValueError(f"Unknown transport reevaluation event type: {event_type}")

    event = TransportReevaluationEvent(
        event_id=f"transport-reevaluation:{uuid4().hex}",
        event_type=event_type,
        reason=reason,
        source=source,
        message=message,
        emitted_at=now_sgt(),
        service_date=service_date,
        route_kind=route_kind,
        request_id=request_id,
        vehicle_id=vehicle_id,
        schedule_id=schedule_id,
        workplace_id=workplace_id,
        proposal_key=proposal_key,
        downstream_actions=list(catalog_entry.downstream_actions),
    )
    _RECENT_TRANSPORT_REEVALUATION_EVENTS.append(event)

    notify_transport_data_changed(
        reason=reason,
        metadata={
            "event_id": event.event_id,
            "event_type": event.event_type,
            "source": event.source,
            "message": event.message,
            "service_date": event.service_date.isoformat() if event.service_date is not None else None,
            "route_kind": event.route_kind,
            "request_id": event.request_id,
            "vehicle_id": event.vehicle_id,
            "schedule_id": event.schedule_id,
            "workplace_id": event.workplace_id,
            "proposal_key": event.proposal_key,
            "downstream_actions": event.downstream_actions,
        },
    )
    return event