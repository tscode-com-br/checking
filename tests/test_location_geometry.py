from datetime import datetime, timezone

import pytest
from shapely.geometry import Point

from sistema.app.models import ManagedLocation
from sistema.app.services.location_geometry import (
    LocationGeometryError,
    build_location_geometry,
    build_user_accuracy_circle,
    distance_from_user_point_to_location_polygon_meters,
    distance_from_user_point_to_location_vertices_meters,
    project_singapore_meters_to_wgs84,
    project_wgs84_to_singapore_meters,
    resolve_expanded_bounds_with_margin_meters,
    user_circle_intersects_location,
    user_circle_intersects_expanded_polygon,
)


def _build_location(
    *,
    location_id: int,
    local: str,
    coordinates: list[dict[str, float]],
    tolerance_meters: int = 50,
) -> ManagedLocation:
    timestamp = datetime(2026, 4, 23, 9, 0, 0, tzinfo=timezone.utc)
    return ManagedLocation(
        id=location_id,
        local=local,
        latitude=coordinates[0]["latitude"],
        longitude=coordinates[0]["longitude"],
        coordinates_json=(
            "["
            + ",".join(
                '{"latitude":' + str(coordinate["latitude"]) + ',"longitude":' + str(coordinate["longitude"]) + "}"
                for coordinate in coordinates
            )
            + "]"
        ),
        projects_json='["P80"]',
        tolerance_meters=tolerance_meters,
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_projection_roundtrip_preserves_coordinate_with_small_error():
    x_coordinate, y_coordinate = project_wgs84_to_singapore_meters(
        latitude=1.255936,
        longitude=103.611066,
    )

    latitude, longitude = project_singapore_meters_to_wgs84(
        x_coordinate=x_coordinate,
        y_coordinate=y_coordinate,
    )

    assert latitude == pytest.approx(1.255936, abs=1e-7)
    assert longitude == pytest.approx(103.611066, abs=1e-7)


def test_build_location_geometry_returns_base_and_expanded_polygons():
    location = _build_location(
        location_id=1,
        local="Area Principal",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611400},
            {"latitude": 1.255800, "longitude": 103.611400},
        ],
        tolerance_meters=40,
    )

    geometry = build_location_geometry(location=location)

    assert geometry.base_area_square_meters > 0
    assert geometry.expanded_area_square_meters > geometry.base_area_square_meters
    assert len(geometry.projected_vertices) == 4


def test_user_circle_intersects_expanded_polygon_near_outer_border():
    location = _build_location(
        location_id=2,
        local="Area Principal",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611400},
            {"latitude": 1.255800, "longitude": 103.611400},
        ],
        tolerance_meters=50,
    )
    geometry = build_location_geometry(location=location)

    assert user_circle_intersects_location(
        location_geometry=geometry,
        latitude=1.255760,
        longitude=103.610980,
        accuracy_meters=12,
    ) is True


def test_user_circle_tangency_counts_as_intersection():
    location = _build_location(
        location_id=22,
        local="Tangencia Valida",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611400},
            {"latitude": 1.255800, "longitude": 103.611400},
        ],
        tolerance_meters=30,
    )
    geometry = build_location_geometry(location=location)
    start_x, start_y = geometry.projected_vertices[0]
    end_x, end_y = geometry.projected_vertices[1]
    edge_dx = end_x - start_x
    edge_dy = end_y - start_y
    edge_length = (edge_dx ** 2 + edge_dy ** 2) ** 0.5
    outward_normal_x = -edge_dy / edge_length
    outward_normal_y = edge_dx / edge_length
    accuracy_meters = 10.0
    midpoint_x = (start_x + end_x) / 2
    midpoint_y = (start_y + end_y) / 2
    offset_meters = geometry.tolerance_meters + accuracy_meters
    user_circle = Point(
        midpoint_x + (outward_normal_x * offset_meters),
        midpoint_y + (outward_normal_y * offset_meters),
    ).buffer(accuracy_meters)

    assert user_circle_intersects_expanded_polygon(
        location_geometry=geometry,
        user_circle=user_circle,
    ) is True


def test_user_circle_does_not_intersect_when_one_meter_beyond_tangent():
    location = _build_location(
        location_id=23,
        local="Tangencia Invalida",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611400},
            {"latitude": 1.255800, "longitude": 103.611400},
        ],
        tolerance_meters=30,
    )
    geometry = build_location_geometry(location=location)
    start_x, start_y = geometry.projected_vertices[0]
    end_x, end_y = geometry.projected_vertices[1]
    edge_dx = end_x - start_x
    edge_dy = end_y - start_y
    edge_length = (edge_dx ** 2 + edge_dy ** 2) ** 0.5
    outward_normal_x = -edge_dy / edge_length
    outward_normal_y = edge_dx / edge_length
    accuracy_meters = 10.0
    midpoint_x = (start_x + end_x) / 2
    midpoint_y = (start_y + end_y) / 2
    offset_meters = geometry.tolerance_meters + accuracy_meters + 1.0
    user_circle = Point(
        midpoint_x + (outward_normal_x * offset_meters),
        midpoint_y + (outward_normal_y * offset_meters),
    ).buffer(accuracy_meters)

    assert user_circle_intersects_expanded_polygon(
        location_geometry=geometry,
        user_circle=user_circle,
    ) is False


def test_distance_to_polygon_is_zero_inside_and_positive_outside():
    location = _build_location(
        location_id=3,
        local="Area Principal",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611400},
            {"latitude": 1.255800, "longitude": 103.611400},
        ],
        tolerance_meters=30,
    )
    geometry = build_location_geometry(location=location)

    inside_distance = distance_from_user_point_to_location_polygon_meters(
        location_geometry=geometry,
        latitude=1.255950,
        longitude=103.611200,
    )
    outside_distance = distance_from_user_point_to_location_polygon_meters(
        location_geometry=geometry,
        latitude=1.255500,
        longitude=103.611200,
    )

    assert inside_distance == pytest.approx(0.0, abs=1e-6)
    assert outside_distance > 0


def test_distance_to_vertices_supports_future_tie_breaker_logic():
    location = _build_location(
        location_id=4,
        local="Area Principal",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611400},
            {"latitude": 1.255800, "longitude": 103.611400},
        ],
        tolerance_meters=30,
    )
    geometry = build_location_geometry(location=location)

    distance = distance_from_user_point_to_location_vertices_meters(
        location_geometry=geometry,
        latitude=1.255790,
        longitude=103.610990,
    )

    assert distance < 2.0


def test_bounds_with_margin_expand_the_buffer_bounds():
    location = _build_location(
        location_id=5,
        local="Area Principal",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611400},
            {"latitude": 1.255800, "longitude": 103.611400},
        ],
        tolerance_meters=30,
    )
    geometry = build_location_geometry(location=location)

    bounds_without_margin = geometry.expanded_polygon.bounds
    bounds_with_margin = resolve_expanded_bounds_with_margin_meters(
        location_geometry=geometry,
        margin_meters=100,
    )

    assert bounds_with_margin[0] < bounds_without_margin[0]
    assert bounds_with_margin[1] < bounds_without_margin[1]
    assert bounds_with_margin[2] > bounds_without_margin[2]
    assert bounds_with_margin[3] > bounds_without_margin[3]


def test_invalid_geometry_raises_for_too_few_vertices():
    location = _build_location(
        location_id=6,
        local="Poucos Pontos",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611000},
        ],
        tolerance_meters=30,
    )

    with pytest.raises(LocationGeometryError, match="at least 3 distinct vertices"):
        build_location_geometry(location=location)


def test_invalid_geometry_raises_for_self_intersection():
    location = _build_location(
        location_id=7,
        local="Laco",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611400},
            {"latitude": 1.255800, "longitude": 103.611400},
            {"latitude": 1.256100, "longitude": 103.611000},
        ],
        tolerance_meters=30,
    )

    with pytest.raises(LocationGeometryError, match="invalid"):
        build_location_geometry(location=location)


def test_invalid_geometry_raises_for_nonpositive_tolerance():
    location = _build_location(
        location_id=8,
        local="Tolerancia Zero",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611400},
        ],
        tolerance_meters=0,
    )

    with pytest.raises(LocationGeometryError, match="positive integer"):
        build_location_geometry(location=location)


def test_user_accuracy_circle_uses_metric_radius():
    circle = build_user_accuracy_circle(
        latitude=1.255936,
        longitude=103.611066,
        accuracy_meters=25,
    )

    assert circle.area > 0
    assert circle.bounds[2] - circle.bounds[0] == pytest.approx(50, rel=0.05)