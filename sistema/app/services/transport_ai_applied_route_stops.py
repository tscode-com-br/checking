from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from sqlalchemy import case, delete, select
from sqlalchemy.orm import Session

from ..models import TransportAIAppliedRouteStop, TransportAISuggestion
from .time_utils import now_sgt


TRANSPORT_AI_APPLIED_ROUTE_STOP_TYPES = frozenset({"pickup", "destination", "origin", "dropoff"})
TRANSPORT_AI_APPLIED_ROUTE_KINDS = frozenset({"home_to_work", "work_to_home"})


@dataclass(frozen=True, slots=True)
class TransportAIAppliedRouteStopInput:
    vehicle_id: int
    stop_order: int
    stop_type: str
    project_name: str
    address: str
    zip_code: str
    country_code: str
    longitude: float
    latitude: float
    scheduled_time: str
    request_id: int | None = None
    user_id: int | None = None
    passenger_name: str | None = None
    duration_from_previous_seconds: int | None = None
    distance_from_previous_meters: int | None = None
    route_kind: str = "home_to_work"


def _normalize_compact_text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_stop_type(value: str) -> str:
    normalized = _normalize_compact_text(value).lower()
    if normalized not in TRANSPORT_AI_APPLIED_ROUTE_STOP_TYPES:
        raise ValueError(f"Unsupported applied route stop type: {value!r}")
    return normalized


def _normalize_route_kind(value: str) -> str:
    normalized = _normalize_compact_text(value).lower()
    if normalized not in TRANSPORT_AI_APPLIED_ROUTE_KINDS:
        raise ValueError(f"Unsupported applied route kind: {value!r}")
    return normalized


def _build_applied_route_stop_sort_key(stop: TransportAIAppliedRouteStopInput) -> tuple[int, int, int]:
    normalized_route_kind = _normalize_route_kind(stop.route_kind)
    return (
        int(stop.vehicle_id),
        0 if normalized_route_kind == "home_to_work" else 1,
        int(stop.stop_order),
    )


def persist_transport_ai_applied_route_stops(
    db: Session,
    *,
    suggestion: TransportAISuggestion,
    stops: Sequence[TransportAIAppliedRouteStopInput],
    created_at: datetime | None = None,
) -> list[TransportAIAppliedRouteStop]:
    timestamp = created_at or now_sgt()

    db.execute(
        delete(TransportAIAppliedRouteStop).where(
            TransportAIAppliedRouteStop.suggestion_id == suggestion.id,
        )
    )

    persisted_stops: list[TransportAIAppliedRouteStop] = []
    for stop in sorted(stops, key=_build_applied_route_stop_sort_key):
        normalized_route_kind = _normalize_route_kind(stop.route_kind)
        persisted_stop = TransportAIAppliedRouteStop(
            suggestion_id=suggestion.id,
            vehicle_id=int(stop.vehicle_id),
            route_kind=normalized_route_kind,
            stop_order=int(stop.stop_order),
            stop_type=_normalize_stop_type(stop.stop_type),
            request_id=None if stop.request_id is None else int(stop.request_id),
            user_id=None if stop.user_id is None else int(stop.user_id),
            passenger_name=_normalize_compact_text(stop.passenger_name) or None,
            project_name=_normalize_compact_text(stop.project_name),
            address=_normalize_compact_text(stop.address),
            zip_code=_normalize_compact_text(stop.zip_code),
            country_code=_normalize_compact_text(stop.country_code).upper(),
            longitude=float(stop.longitude),
            latitude=float(stop.latitude),
            scheduled_time=_normalize_compact_text(stop.scheduled_time),
            duration_from_previous_seconds=(
                None if stop.duration_from_previous_seconds is None else int(stop.duration_from_previous_seconds)
            ),
            distance_from_previous_meters=(
                None if stop.distance_from_previous_meters is None else int(stop.distance_from_previous_meters)
            ),
            created_at=timestamp,
        )
        db.add(persisted_stop)
        persisted_stops.append(persisted_stop)

    db.flush()
    return persisted_stops


def list_transport_ai_applied_route_stops(
    db: Session,
    *,
    suggestion_id: int,
) -> list[TransportAIAppliedRouteStop]:
    route_kind_order = case(
        (TransportAIAppliedRouteStop.route_kind == "home_to_work", 0),
        else_=1,
    )
    return db.execute(
        select(TransportAIAppliedRouteStop)
        .where(TransportAIAppliedRouteStop.suggestion_id == suggestion_id)
        .order_by(
            TransportAIAppliedRouteStop.vehicle_id.asc(),
            route_kind_order.asc(),
            TransportAIAppliedRouteStop.stop_order.asc(),
            TransportAIAppliedRouteStop.id.asc(),
        )
    ).scalars().all()