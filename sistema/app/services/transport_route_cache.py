from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings, settings
from ..models import TransportAIRouteMatrix, TransportAIRoutePoint
from .time_utils import now_sgt


def _normalize_compact_text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _serialize_optional_json_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return _dump_json(value)


def normalize_transport_ai_route_point_query(
    *,
    address: str,
    zip_code: str,
    country_name: str,
) -> str:
    parts = [
        _normalize_compact_text(address).lower(),
        _normalize_compact_text(zip_code).lower(),
        _normalize_compact_text(country_name).lower(),
    ]
    return ", ".join(part for part in parts if part)


def build_transport_ai_route_point_key(*, provider: str, normalized_query: str) -> str:
    payload = f"{_normalize_compact_text(provider).lower()}|{normalized_query}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonicalize_coordinates(coordinates: Sequence[Sequence[float]]) -> list[list[float]]:
    return [
        [round(float(pair[0]), 6), round(float(pair[1]), 6)]
        for pair in coordinates
    ]


def build_transport_ai_coordinate_hash(
    *,
    sources: Sequence[Sequence[float]],
    destinations: Sequence[Sequence[float]],
) -> str:
    payload = _dump_json(
        {
            "sources": _canonicalize_coordinates(sources),
            "destinations": _canonicalize_coordinates(destinations),
        }
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_transport_ai_route_matrix_key(
    *,
    provider: str,
    profile: str,
    depart_at: datetime | None,
    coordinate_hash: str,
) -> str:
    depart_at_key = depart_at.isoformat() if depart_at is not None else ""
    payload = "|".join(
        [
            _normalize_compact_text(provider).lower(),
            _normalize_compact_text(profile).lower(),
            depart_at_key,
            coordinate_hash,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_cached_transport_ai_route_point(
    db: Session,
    *,
    provider: str,
    address: str,
    zip_code: str,
    country_name: str,
    reference_time: datetime | None = None,
) -> TransportAIRoutePoint | None:
    effective_reference_time = reference_time or now_sgt()
    normalized_query = normalize_transport_ai_route_point_query(
        address=address,
        zip_code=zip_code,
        country_name=country_name,
    )
    point_key = build_transport_ai_route_point_key(
        provider=provider,
        normalized_query=normalized_query,
    )
    return db.execute(
        select(TransportAIRoutePoint)
        .where(
            TransportAIRoutePoint.point_key == point_key,
            TransportAIRoutePoint.expires_at > effective_reference_time,
        )
        .limit(1)
    ).scalar_one_or_none()


def upsert_transport_ai_route_point(
    db: Session,
    *,
    source_id: int,
    point_type: str,
    address: str,
    zip_code: str,
    country_code: str,
    country_name: str,
    longitude: float,
    latitude: float,
    provider: str,
    provider_place_id: str | None = None,
    confidence: float | None = None,
    raw_response_json: Any = None,
    settings_obj: Settings = settings,
    created_at: datetime | None = None,
) -> TransportAIRoutePoint:
    timestamp = created_at or now_sgt()
    normalized_query = normalize_transport_ai_route_point_query(
        address=address,
        zip_code=zip_code,
        country_name=country_name,
    )
    point_key = build_transport_ai_route_point_key(
        provider=provider,
        normalized_query=normalized_query,
    )
    ttl_days = max(int(settings_obj.transport_ai_geocode_cache_ttl_days), 0)
    expires_at = timestamp + timedelta(days=ttl_days)
    persisted_raw_response_json = (
        _serialize_optional_json_text(raw_response_json)
        if settings_obj.mapbox_geocoding_permanent
        else None
    )

    route_point = db.execute(
        select(TransportAIRoutePoint)
        .where(TransportAIRoutePoint.point_key == point_key)
        .limit(1)
    ).scalar_one_or_none()

    if route_point is None:
        route_point = TransportAIRoutePoint(
            point_key=point_key,
            point_type=point_type,
            source_id=source_id,
            address=_normalize_compact_text(address),
            zip_code=_normalize_compact_text(zip_code),
            country_code=_normalize_compact_text(country_code).upper(),
            country_name=_normalize_compact_text(country_name),
            normalized_query=normalized_query,
            longitude=float(longitude),
            latitude=float(latitude),
            provider=_normalize_compact_text(provider),
            provider_place_id=_normalize_compact_text(provider_place_id) or None,
            confidence=None if confidence is None else float(confidence),
            raw_response_json=persisted_raw_response_json,
            created_at=timestamp,
            updated_at=timestamp,
            expires_at=expires_at,
        )
        db.add(route_point)
    else:
        route_point.point_type = point_type
        route_point.source_id = source_id
        route_point.address = _normalize_compact_text(address)
        route_point.zip_code = _normalize_compact_text(zip_code)
        route_point.country_code = _normalize_compact_text(country_code).upper()
        route_point.country_name = _normalize_compact_text(country_name)
        route_point.normalized_query = normalized_query
        route_point.longitude = float(longitude)
        route_point.latitude = float(latitude)
        route_point.provider = _normalize_compact_text(provider)
        route_point.provider_place_id = _normalize_compact_text(provider_place_id) or None
        route_point.confidence = None if confidence is None else float(confidence)
        route_point.raw_response_json = persisted_raw_response_json
        route_point.updated_at = timestamp
        route_point.expires_at = expires_at

    db.flush()
    return route_point


def get_cached_transport_ai_route_matrix(
    db: Session,
    *,
    provider: str,
    profile: str,
    sources: Sequence[Sequence[float]],
    destinations: Sequence[Sequence[float]],
    depart_at: datetime | None = None,
    reference_time: datetime | None = None,
) -> TransportAIRouteMatrix | None:
    effective_reference_time = reference_time or now_sgt()
    coordinate_hash = build_transport_ai_coordinate_hash(
        sources=sources,
        destinations=destinations,
    )
    matrix_key = build_transport_ai_route_matrix_key(
        provider=provider,
        profile=profile,
        depart_at=depart_at,
        coordinate_hash=coordinate_hash,
    )
    return db.execute(
        select(TransportAIRouteMatrix)
        .where(
            TransportAIRouteMatrix.matrix_key == matrix_key,
            TransportAIRouteMatrix.expires_at > effective_reference_time,
        )
        .limit(1)
    ).scalar_one_or_none()


def upsert_transport_ai_route_matrix(
    db: Session,
    *,
    provider: str,
    profile: str,
    sources: Sequence[Sequence[float]],
    destinations: Sequence[Sequence[float]],
    durations: Any,
    distances: Any,
    depart_at: datetime | None = None,
    settings_obj: Settings = settings,
    created_at: datetime | None = None,
) -> TransportAIRouteMatrix:
    timestamp = created_at or now_sgt()
    ttl_seconds = max(int(settings_obj.transport_ai_route_cache_ttl_seconds), 0)
    expires_at = timestamp + timedelta(seconds=ttl_seconds)
    canonical_sources = _canonicalize_coordinates(sources)
    canonical_destinations = _canonicalize_coordinates(destinations)
    coordinate_hash = build_transport_ai_coordinate_hash(
        sources=canonical_sources,
        destinations=canonical_destinations,
    )
    matrix_key = build_transport_ai_route_matrix_key(
        provider=provider,
        profile=profile,
        depart_at=depart_at,
        coordinate_hash=coordinate_hash,
    )

    route_matrix = db.execute(
        select(TransportAIRouteMatrix)
        .where(TransportAIRouteMatrix.matrix_key == matrix_key)
        .limit(1)
    ).scalar_one_or_none()

    if route_matrix is None:
        route_matrix = TransportAIRouteMatrix(
            matrix_key=matrix_key,
            provider=_normalize_compact_text(provider),
            profile=_normalize_compact_text(profile),
            depart_at=depart_at,
            coordinate_hash=coordinate_hash,
            sources_json=_dump_json(canonical_sources),
            destinations_json=_dump_json(canonical_destinations),
            durations_json=_serialize_optional_json_text(durations) or "[]",
            distances_json=_serialize_optional_json_text(distances) or "[]",
            created_at=timestamp,
            expires_at=expires_at,
        )
        db.add(route_matrix)
    else:
        route_matrix.provider = _normalize_compact_text(provider)
        route_matrix.profile = _normalize_compact_text(profile)
        route_matrix.depart_at = depart_at
        route_matrix.coordinate_hash = coordinate_hash
        route_matrix.sources_json = _dump_json(canonical_sources)
        route_matrix.destinations_json = _dump_json(canonical_destinations)
        route_matrix.durations_json = _serialize_optional_json_text(durations) or "[]"
        route_matrix.distances_json = _serialize_optional_json_text(distances) or "[]"
        route_matrix.created_at = timestamp
        route_matrix.expires_at = expires_at

    db.flush()
    return route_matrix