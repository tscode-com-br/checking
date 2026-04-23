from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from shapely.geometry import Point, Polygon

from ..models import ManagedLocation
from .location_geometry import (
    LocationGeometryError,
    build_location_geometry,
    build_user_accuracy_circle,
    build_user_point,
    user_circle_intersects_expanded_polygon,
)
from .location_matching import is_checkout_zone_name


@dataclass(frozen=True)
class PolygonMatchCandidate:
    location_id: int
    local: str
    is_checkout_zone: bool
    intersects_user_circle: bool
    nearest_vertex_distance_meters: float
    distance_to_base_polygon_meters: float


@dataclass(frozen=True)
class PolygonMatchSkippedLocation:
    location_id: int
    local: str
    reason: str


@dataclass(frozen=True)
class PolygonLocationMatchResult:
    matched_location: ManagedLocation | None
    nearest_workplace_distance_meters: float | None
    intersecting_candidates: tuple[PolygonMatchCandidate, ...]
    evaluated_candidates: tuple[PolygonMatchCandidate, ...]
    skipped_locations: tuple[PolygonMatchSkippedLocation, ...]


def resolve_polygon_location_match(
    *,
    managed_locations: Sequence[ManagedLocation],
    latitude: float,
    longitude: float,
    accuracy_meters: float,
) -> PolygonLocationMatchResult:
    user_point = build_user_point(latitude=latitude, longitude=longitude)
    user_circle = build_user_accuracy_circle(
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=accuracy_meters,
    )

    nearest_workplace_distance_meters: float | None = None
    evaluated_with_locations: list[tuple[ManagedLocation, PolygonMatchCandidate]] = []
    intersecting_with_locations: list[tuple[ManagedLocation, PolygonMatchCandidate]] = []
    skipped_locations: list[PolygonMatchSkippedLocation] = []

    for location in managed_locations:
        try:
            geometry = build_location_geometry(location=location)
        except LocationGeometryError as error:
            skipped_locations.append(
                PolygonMatchSkippedLocation(
                    location_id=int(location.id or 0),
                    local=location.local,
                    reason=str(error),
                )
            )
            continue

        distance_to_base_polygon_meters = float(user_point.distance(geometry.base_polygon))
        if not is_checkout_zone_name(location.local) and (
            nearest_workplace_distance_meters is None
            or distance_to_base_polygon_meters < nearest_workplace_distance_meters
        ):
            nearest_workplace_distance_meters = distance_to_base_polygon_meters

        candidate = PolygonMatchCandidate(
            location_id=int(location.id or 0),
            local=location.local,
            is_checkout_zone=is_checkout_zone_name(location.local),
            intersects_user_circle=user_circle_intersects_expanded_polygon(
                location_geometry=geometry,
                user_circle=user_circle,
            ),
            nearest_vertex_distance_meters=_distance_from_user_point_to_vertices(
                user_point=user_point,
                projected_vertices=geometry.projected_vertices,
            ),
            distance_to_base_polygon_meters=distance_to_base_polygon_meters,
        )
        evaluated_with_locations.append((location, candidate))
        if candidate.intersects_user_circle:
            intersecting_with_locations.append((location, candidate))

    matched_location = _resolve_best_intersection(intersecting_with_locations)
    return PolygonLocationMatchResult(
        matched_location=matched_location,
        nearest_workplace_distance_meters=nearest_workplace_distance_meters,
        intersecting_candidates=tuple(candidate for _, candidate in intersecting_with_locations),
        evaluated_candidates=tuple(candidate for _, candidate in evaluated_with_locations),
        skipped_locations=tuple(skipped_locations),
    )


def _resolve_best_intersection(
    intersecting_with_locations: list[tuple[ManagedLocation, PolygonMatchCandidate]],
) -> ManagedLocation | None:
    if not intersecting_with_locations:
        return None

    best_location, _ = min(
        intersecting_with_locations,
        key=lambda item: (
            item[1].nearest_vertex_distance_meters,
            int(item[0].id or 0),
        ),
    )
    return best_location


def _distance_from_user_point_to_vertices(
    *,
    user_point: Point,
    projected_vertices: Sequence[tuple[float, float]],
) -> float:
    return min(float(user_point.distance(Point(x_coordinate, y_coordinate))) for x_coordinate, y_coordinate in projected_vertices)