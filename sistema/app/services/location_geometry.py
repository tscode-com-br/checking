from __future__ import annotations

from dataclasses import dataclass

from pyproj import Transformer
from shapely.geometry import Point, Polygon
from shapely.validation import explain_validity

from ..models import ManagedLocation
from .managed_locations import extract_location_coordinates


SINGAPORE_SVY21_CRS = "EPSG:3414"
WGS84_CRS = "EPSG:4326"
_MINIMUM_POLYGON_AREA_SQUARE_METERS = 1e-3
_INTERSECTION_EPSILON_METERS = 1e-6
_TO_SINGAPORE_SVY21 = Transformer.from_crs(WGS84_CRS, SINGAPORE_SVY21_CRS, always_xy=True)
_FROM_SINGAPORE_SVY21 = Transformer.from_crs(SINGAPORE_SVY21_CRS, WGS84_CRS, always_xy=True)


class LocationGeometryError(ValueError):
    pass


@dataclass(frozen=True)
class LocationGeometry:
    location_id: int
    local: str
    tolerance_meters: int
    projected_vertices: tuple[tuple[float, float], ...]
    base_polygon: Polygon
    expanded_polygon: Polygon

    @property
    def base_area_square_meters(self) -> float:
        return float(self.base_polygon.area)

    @property
    def expanded_area_square_meters(self) -> float:
        return float(self.expanded_polygon.area)


def project_wgs84_to_singapore_meters(*, latitude: float, longitude: float) -> tuple[float, float]:
    x_coordinate, y_coordinate = _TO_SINGAPORE_SVY21.transform(longitude, latitude)
    return float(x_coordinate), float(y_coordinate)


def project_singapore_meters_to_wgs84(*, x_coordinate: float, y_coordinate: float) -> tuple[float, float]:
    longitude, latitude = _FROM_SINGAPORE_SVY21.transform(x_coordinate, y_coordinate)
    return float(latitude), float(longitude)


def build_location_geometry(*, location: ManagedLocation) -> LocationGeometry:
    tolerance_meters = int(location.tolerance_meters or 0)
    if tolerance_meters < 1:
        raise LocationGeometryError("The location tolerance must be a positive integer in meters.")

    projected_vertices = _normalize_projected_vertices(location)
    if len(projected_vertices) < 3:
        raise LocationGeometryError("A polygonal location requires at least 3 distinct vertices.")

    base_polygon = Polygon(projected_vertices)
    _validate_polygon(base_polygon=base_polygon, location_name=location.local)

    expanded_polygon = base_polygon.buffer(float(tolerance_meters))
    if expanded_polygon.is_empty or not expanded_polygon.is_valid:
        raise LocationGeometryError(
            f"The expanded polygon for location '{location.local}' is invalid: {explain_validity(expanded_polygon)}"
        )

    return LocationGeometry(
        location_id=int(location.id or 0),
        local=location.local,
        tolerance_meters=tolerance_meters,
        projected_vertices=tuple(projected_vertices),
        base_polygon=base_polygon,
        expanded_polygon=expanded_polygon,
    )


def build_user_accuracy_circle(*, latitude: float, longitude: float, accuracy_meters: float) -> Polygon:
    if accuracy_meters < 0:
        raise LocationGeometryError("The user accuracy radius cannot be negative.")

    point = build_user_point(latitude=latitude, longitude=longitude)
    return point.buffer(float(accuracy_meters))


def build_user_point(*, latitude: float, longitude: float) -> Point:
    x_coordinate, y_coordinate = project_wgs84_to_singapore_meters(
        latitude=latitude,
        longitude=longitude,
    )
    return Point(x_coordinate, y_coordinate)


def user_circle_intersects_location(
    *,
    location_geometry: LocationGeometry,
    latitude: float,
    longitude: float,
    accuracy_meters: float,
) -> bool:
    user_circle = build_user_accuracy_circle(
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=accuracy_meters,
    )
    return user_circle_intersects_expanded_polygon(
        location_geometry=location_geometry,
        user_circle=user_circle,
    )


def user_circle_intersects_expanded_polygon(
    *,
    location_geometry: LocationGeometry,
    user_circle: Polygon,
) -> bool:
    return (
        bool(user_circle.intersects(location_geometry.expanded_polygon))
        or float(user_circle.distance(location_geometry.expanded_polygon)) <= _INTERSECTION_EPSILON_METERS
    )


def distance_from_user_point_to_location_polygon_meters(
    *,
    location_geometry: LocationGeometry,
    latitude: float,
    longitude: float,
) -> float:
    user_point = build_user_point(latitude=latitude, longitude=longitude)
    return float(user_point.distance(location_geometry.base_polygon))


def distance_from_user_point_to_location_vertices_meters(
    *,
    location_geometry: LocationGeometry,
    latitude: float,
    longitude: float,
) -> float:
    user_point = build_user_point(latitude=latitude, longitude=longitude)
    return min(
        float(user_point.distance(Point(x_coordinate, y_coordinate)))
        for x_coordinate, y_coordinate in location_geometry.projected_vertices
    )


def resolve_expanded_bounds_with_margin_meters(
    *,
    location_geometry: LocationGeometry,
    margin_meters: float = 100.0,
) -> tuple[float, float, float, float]:
    if margin_meters < 0:
        raise LocationGeometryError("The map margin cannot be negative.")
    min_x, min_y, max_x, max_y = location_geometry.expanded_polygon.bounds
    return (
        float(min_x - margin_meters),
        float(min_y - margin_meters),
        float(max_x + margin_meters),
        float(max_y + margin_meters),
    )


def _normalize_projected_vertices(location: ManagedLocation) -> list[tuple[float, float]]:
    coordinates = list(extract_location_coordinates(location))
    if len(coordinates) >= 2 and _coordinate_key(coordinates[0]) == _coordinate_key(coordinates[-1]):
        coordinates = coordinates[:-1]

    projected_vertices: list[tuple[float, float]] = []
    seen_vertices: set[tuple[float, float]] = set()
    for coordinate in coordinates:
        projected_vertex = project_wgs84_to_singapore_meters(
            latitude=float(coordinate["latitude"]),
            longitude=float(coordinate["longitude"]),
        )
        if projected_vertex in seen_vertices:
            continue
        seen_vertices.add(projected_vertex)
        projected_vertices.append(projected_vertex)
    return projected_vertices


def _validate_polygon(*, base_polygon: Polygon, location_name: str) -> None:
    if base_polygon.is_empty:
        raise LocationGeometryError(f"The polygon for location '{location_name}' is empty.")
    if not base_polygon.is_valid:
        raise LocationGeometryError(
            f"The polygon for location '{location_name}' is invalid: {explain_validity(base_polygon)}"
        )
    if float(base_polygon.area) <= _MINIMUM_POLYGON_AREA_SQUARE_METERS:
        raise LocationGeometryError(
            f"The polygon for location '{location_name}' has zero or near-zero area."
        )


def _coordinate_key(coordinate: dict[str, float]) -> tuple[float, float]:
    return (round(float(coordinate["latitude"]), 9), round(float(coordinate["longitude"]), 9))