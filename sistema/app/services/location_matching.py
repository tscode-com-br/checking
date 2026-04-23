from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from collections.abc import Sequence

from ..models import ManagedLocation
from .location_geometry import (
    LocationGeometryError,
    build_location_geometry,
    build_user_accuracy_circle,
    distance_from_user_point_to_location_polygon_meters,
    distance_from_user_point_to_location_vertices_meters,
    user_circle_intersects_expanded_polygon,
)
from .managed_locations import extract_location_coordinates


OUT_OF_RANGE_CHECKOUT_DISTANCE_METERS = 2000.0
CHECKOUT_ZONE_EVENT_LOCAL = "Zona de CheckOut"
CHECKOUT_ZONE_CAPTURED_LOCATION = "Zona de Check-Out"
OUTSIDE_WORKPLACE_CAPTURED_LOCATION = "Fora do Ambiente de Trabalho"

_CHECKOUT_ZONE_NAME_PATTERN = re.compile(r"^zona de checkout(?: \d+)?$", re.IGNORECASE)
_EARTH_RADIUS_METERS = 6_371_000.0

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LocationMatchResult:
    matched_location: ManagedLocation | None
    nearest_workplace_distance_meters: float | None


def _normalize_location_key(value: str | None) -> str:
    return " ".join((value or "").strip().split()).casefold()


def is_checkout_zone_name(value: str | None) -> bool:
    normalized = _normalize_location_key(value)
    if not normalized:
        return False
    return _CHECKOUT_ZONE_NAME_PATTERN.fullmatch(normalized) is not None


def resolve_automation_area_label(value: str | None) -> str | None:
    normalized = " ".join((value or "").strip().split())
    if not normalized:
        return None
    return CHECKOUT_ZONE_EVENT_LOCAL if is_checkout_zone_name(normalized) else normalized


def resolve_distance_to_location(
    *,
    location: ManagedLocation,
    latitude: float,
    longitude: float,
) -> float:
    return min(
        _haversine_distance_meters(
            latitude_1=latitude,
            longitude_1=longitude,
            latitude_2=coordinate["latitude"],
            longitude_2=coordinate["longitude"],
        )
        for coordinate in extract_location_coordinates(location)
    )


def resolve_location_match(
    *,
    managed_locations: Sequence[ManagedLocation],
    latitude: float,
    longitude: float,
    accuracy_meters: float | None = None,
) -> LocationMatchResult:
    if accuracy_meters is not None:
        return _resolve_hybrid_location_match(
            managed_locations=managed_locations,
            latitude=latitude,
            longitude=longitude,
            accuracy_meters=accuracy_meters,
        )

    nearest_regular_location: ManagedLocation | None = None
    nearest_regular_distance_meters: float | None = None
    nearest_checkout_location: ManagedLocation | None = None
    nearest_checkout_distance_meters: float | None = None
    nearest_workplace_distance_meters: float | None = None

    for location in managed_locations:
        distance_meters = resolve_distance_to_location(
            location=location,
            latitude=latitude,
            longitude=longitude,
        )

        if not is_checkout_zone_name(location.local) and (
            nearest_workplace_distance_meters is None
            or distance_meters < nearest_workplace_distance_meters
        ):
            nearest_workplace_distance_meters = distance_meters

        if distance_meters > float(location.tolerance_meters):
            continue

        if is_checkout_zone_name(location.local):
            if (
                nearest_checkout_distance_meters is None
                or distance_meters < nearest_checkout_distance_meters
            ):
                nearest_checkout_location = location
                nearest_checkout_distance_meters = distance_meters
            continue

        if (
            nearest_regular_distance_meters is None
            or distance_meters < nearest_regular_distance_meters
        ):
            nearest_regular_location = location
            nearest_regular_distance_meters = distance_meters

    return LocationMatchResult(
        matched_location=nearest_checkout_location or nearest_regular_location,
        nearest_workplace_distance_meters=nearest_workplace_distance_meters,
    )


def _resolve_hybrid_location_match(
    *,
    managed_locations: Sequence[ManagedLocation],
    latitude: float,
    longitude: float,
    accuracy_meters: float,
) -> LocationMatchResult:
    user_circle = build_user_accuracy_circle(
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=accuracy_meters,
    )

    nearest_workplace_distance_meters: float | None = None
    polygon_regular_candidate: tuple[float, int, ManagedLocation] | None = None
    polygon_checkout_candidate: tuple[float, int, ManagedLocation] | None = None
    polygon_evaluated_ids: list[int] = []
    polygon_intersection_ids: list[int] = []
    skipped_invalid_entries: list[str] = []

    for location in managed_locations:
        location_id = int(location.id or 0)
        try:
            geometry = build_location_geometry(location=location)
        except LocationGeometryError as error:
            skipped_reason = str(error)
            skipped_invalid_entries.append(f"{location_id}:{location.local}:{skipped_reason}")
            logger.debug(
                "location_match_invalid_polygon_skipped location_id=%s local=%s reason=%s",
                location_id,
                location.local,
                skipped_reason,
            )
            continue

        polygon_evaluated_ids.append(location_id)
        polygon_distance_meters = distance_from_user_point_to_location_polygon_meters(
            location_geometry=geometry,
            latitude=latitude,
            longitude=longitude,
        )
        if not is_checkout_zone_name(location.local) and (
            nearest_workplace_distance_meters is None
            or polygon_distance_meters < nearest_workplace_distance_meters
        ):
            nearest_workplace_distance_meters = polygon_distance_meters

        if user_circle_intersects_expanded_polygon(
            location_geometry=geometry,
            user_circle=user_circle,
        ):
            polygon_intersection_ids.append(location_id)
            nearest_vertex_distance_meters = distance_from_user_point_to_location_vertices_meters(
                location_geometry=geometry,
                latitude=latitude,
                longitude=longitude,
            )

            candidate = (nearest_vertex_distance_meters, int(location.id or 0), location)
            if is_checkout_zone_name(location.local):
                if polygon_checkout_candidate is None or candidate[:2] < polygon_checkout_candidate[:2]:
                    polygon_checkout_candidate = candidate
                continue

            if polygon_regular_candidate is None or candidate[:2] < polygon_regular_candidate[:2]:
                polygon_regular_candidate = candidate

    matched_location = None
    selection_source = "none"
    if polygon_checkout_candidate is not None:
        selection_source = "polygon_checkout"
        matched_location = polygon_checkout_candidate[2]
    elif polygon_regular_candidate is not None:
        selection_source = "polygon_regular"
        matched_location = polygon_regular_candidate[2]

    logger.debug(
        "location_match_decision latitude=%s longitude=%s accuracy_meters=%s selection_source=%s matched_location_id=%s matched_local=%s nearest_workplace_distance_meters=%s polygon_evaluated=%s polygon_intersections=%s skipped_invalid_locations=%s",
        round(latitude, 6),
        round(longitude, 6),
        round(accuracy_meters, 3),
        selection_source,
        int(matched_location.id or 0) if matched_location is not None else None,
        matched_location.local if matched_location is not None else None,
        round(nearest_workplace_distance_meters, 3)
        if nearest_workplace_distance_meters is not None
        else None,
        polygon_evaluated_ids,
        polygon_intersection_ids,
        skipped_invalid_entries,
    )

    return LocationMatchResult(
        matched_location=matched_location,
        nearest_workplace_distance_meters=nearest_workplace_distance_meters,
    )


def resolve_captured_location_label(
    *,
    location: ManagedLocation | None,
    nearest_workplace_distance_meters: float | None,
) -> str | None:
    if location is None:
        if (
            nearest_workplace_distance_meters is not None
            and nearest_workplace_distance_meters > OUT_OF_RANGE_CHECKOUT_DISTANCE_METERS
        ):
            return OUTSIDE_WORKPLACE_CAPTURED_LOCATION
        return None

    if is_checkout_zone_name(location.local):
        return CHECKOUT_ZONE_CAPTURED_LOCATION

    return location.local


def resolve_submission_local(location: ManagedLocation | None) -> str | None:
    if location is None:
        return None
    return resolve_automation_area_label(location.local)


def _haversine_distance_meters(
    *,
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    phi_1 = math.radians(latitude_1)
    phi_2 = math.radians(latitude_2)
    delta_phi = math.radians(latitude_2 - latitude_1)
    delta_lambda = math.radians(longitude_2 - longitude_1)

    haversine = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_1) * math.cos(phi_2) * math.sin(delta_lambda / 2) ** 2
    )
    arc = 2 * math.atan2(math.sqrt(haversine), math.sqrt(max(0.0, 1 - haversine)))
    return _EARTH_RADIUS_METERS * arc