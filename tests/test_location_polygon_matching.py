from datetime import datetime, timezone
import time

from sistema.app.models import ManagedLocation
from sistema.app.services.location_polygon_matching import resolve_polygon_location_match


def _build_location(
    *,
    location_id: int,
    local: str,
    coordinates: list[dict[str, float]],
    tolerance_meters: int = 50,
) -> ManagedLocation:
    timestamp = datetime(2026, 4, 23, 10, 0, 0, tzinfo=timezone.utc)
    coordinates_json = (
        "["
        + ",".join(
            '{"latitude":' + str(coordinate["latitude"]) + ',"longitude":' + str(coordinate["longitude"]) + "}"
            for coordinate in coordinates
        )
        + "]"
    )
    return ManagedLocation(
        id=location_id,
        local=local,
        latitude=coordinates[0]["latitude"],
        longitude=coordinates[0]["longitude"],
        coordinates_json=coordinates_json,
        projects_json='["P80"]',
        tolerance_meters=tolerance_meters,
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_polygon_match_returns_matching_location_when_circle_intersects_buffer():
    location = _build_location(
        location_id=1,
        local="Area Principal",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611400},
            {"latitude": 1.255800, "longitude": 103.611400},
        ],
        tolerance_meters=45,
    )

    result = resolve_polygon_location_match(
        managed_locations=[location],
        latitude=1.255760,
        longitude=103.610990,
        accuracy_meters=12,
    )

    assert result.matched_location is not None
    assert result.matched_location.local == "Area Principal"
    assert len(result.intersecting_candidates) == 1
    assert result.nearest_workplace_distance_meters is not None


def test_polygon_match_uses_nearest_vertex_tie_breaker_between_intersections():
    nearer = _build_location(
        location_id=10,
        local="Mais Perto",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611300},
            {"latitude": 1.255800, "longitude": 103.611300},
        ],
        tolerance_meters=120,
    )
    farther = _build_location(
        location_id=11,
        local="Mais Longe",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611350},
            {"latitude": 1.256100, "longitude": 103.611350},
            {"latitude": 1.256100, "longitude": 103.611650},
            {"latitude": 1.255800, "longitude": 103.611650},
        ],
        tolerance_meters=120,
    )

    result = resolve_polygon_location_match(
        managed_locations=[farther, nearer],
        latitude=1.255790,
        longitude=103.611010,
        accuracy_meters=70,
    )

    assert result.matched_location is not None
    assert result.matched_location.local == "Mais Perto"
    assert len(result.intersecting_candidates) == 2


def test_polygon_match_uses_lowest_id_for_absolute_distance_tie():
    first = _build_location(
        location_id=20,
        local="Empate A",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256000, "longitude": 103.611000},
            {"latitude": 1.256000, "longitude": 103.611200},
            {"latitude": 1.255800, "longitude": 103.611200},
        ],
        tolerance_meters=90,
    )
    second = _build_location(
        location_id=21,
        local="Empate B",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256000, "longitude": 103.611000},
            {"latitude": 1.256000, "longitude": 103.611200},
            {"latitude": 1.255800, "longitude": 103.611200},
        ],
        tolerance_meters=90,
    )

    result = resolve_polygon_location_match(
        managed_locations=[second, first],
        latitude=1.255900,
        longitude=103.611100,
        accuracy_meters=5,
    )

    assert result.matched_location is not None
    assert result.matched_location.id == 20


def test_polygon_match_ignores_checkout_zone_for_nearest_workplace_distance():
    workplace = _build_location(
        location_id=30,
        local="Area Principal",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611400},
            {"latitude": 1.255800, "longitude": 103.611400},
        ],
        tolerance_meters=30,
    )
    checkout_zone = _build_location(
        location_id=31,
        local="Zona de CheckOut",
        coordinates=[
            {"latitude": 1.255200, "longitude": 103.610500},
            {"latitude": 1.255400, "longitude": 103.610500},
            {"latitude": 1.255400, "longitude": 103.610700},
            {"latitude": 1.255200, "longitude": 103.610700},
        ],
        tolerance_meters=30,
    )

    result = resolve_polygon_location_match(
        managed_locations=[checkout_zone, workplace],
        latitude=1.255300,
        longitude=103.610600,
        accuracy_meters=5,
    )

    assert result.nearest_workplace_distance_meters is not None
    assert result.nearest_workplace_distance_meters > 0


def test_polygon_match_skips_invalid_geometries_without_crashing():
    invalid = _build_location(
        location_id=40,
        local="Invalida",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.255800, "longitude": 103.611000},
        ],
        tolerance_meters=30,
    )
    valid = _build_location(
        location_id=41,
        local="Valida",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611400},
            {"latitude": 1.255800, "longitude": 103.611400},
        ],
        tolerance_meters=40,
    )

    result = resolve_polygon_location_match(
        managed_locations=[invalid, valid],
        latitude=1.255760,
        longitude=103.610990,
        accuracy_meters=12,
    )

    assert result.matched_location is not None
    assert result.matched_location.local == "Valida"
    assert len(result.skipped_locations) == 1
    assert result.skipped_locations[0].local == "Invalida"


def test_polygon_match_returns_none_when_no_expanded_polygon_intersects():
    location = _build_location(
        location_id=50,
        local="Area Principal",
        coordinates=[
            {"latitude": 1.255800, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611000},
            {"latitude": 1.256100, "longitude": 103.611400},
            {"latitude": 1.255800, "longitude": 103.611400},
        ],
        tolerance_meters=20,
    )

    result = resolve_polygon_location_match(
        managed_locations=[location],
        latitude=1.257500,
        longitude=103.613000,
        accuracy_meters=8,
    )

    assert result.matched_location is None
    assert len(result.intersecting_candidates) == 0
    assert result.nearest_workplace_distance_meters is not None


def test_polygon_match_handles_many_locations_within_basic_time_budget():
    locations = []
    location_id = 100
    for row_index in range(15):
        for column_index in range(15):
            latitude = 1.240000 + (row_index * 0.0012)
            longitude = 103.600000 + (column_index * 0.0012)
            locations.append(
                _build_location(
                    location_id=location_id,
                    local=f"Area {location_id}",
                    coordinates=[
                        {"latitude": latitude, "longitude": longitude},
                        {"latitude": latitude + 0.00018, "longitude": longitude},
                        {"latitude": latitude + 0.00018, "longitude": longitude + 0.00018},
                        {"latitude": latitude, "longitude": longitude + 0.00018},
                    ],
                    tolerance_meters=40,
                )
            )
            location_id += 1

    start = time.perf_counter()
    result = resolve_polygon_location_match(
        managed_locations=locations,
        latitude=1.240050,
        longitude=103.600050,
        accuracy_meters=12,
    )
    elapsed_seconds = time.perf_counter() - start

    assert result.matched_location is not None
    assert len(result.evaluated_candidates) == len(locations)
    assert elapsed_seconds < 3.0, f"expected polygon matching smoke test to stay under 3.0s, got {elapsed_seconds:.3f}s"