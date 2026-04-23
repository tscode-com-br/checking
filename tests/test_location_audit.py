import json
from datetime import datetime, timezone

from sistema.app.models import ManagedLocation
from sistema.app.services.location_audit import (
    audit_managed_location,
    audit_managed_locations,
    build_location_audit_text,
)


def _build_location(
    *,
    location_id: int,
    local: str,
    coordinates: list[dict[str, float]] | None = None,
    coordinates_json: str | None = None,
    projects: list[str] | None = None,
    tolerance_meters: int = 150,
) -> ManagedLocation:
    timestamp = datetime(2026, 4, 23, 8, 0, 0, tzinfo=timezone.utc)
    if coordinates_json is None and coordinates is not None:
        coordinates_json = json.dumps(coordinates)
    if coordinates:
        primary_coordinate = coordinates[0]
    else:
        primary_coordinate = {"latitude": 1.255936, "longitude": 103.611066}
    return ManagedLocation(
        id=location_id,
        local=local,
        latitude=primary_coordinate["latitude"],
        longitude=primary_coordinate["longitude"],
        coordinates_json=coordinates_json,
        projects_json=json.dumps(projects or ["P80"]),
        tolerance_meters=tolerance_meters,
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_audit_accepts_valid_triangle_without_issues():
    location = _build_location(
        location_id=1,
        local="Triangulo Valido",
        coordinates=[
            {"latitude": 1.255936, "longitude": 103.611066},
            {"latitude": 1.256136, "longitude": 103.611466},
            {"latitude": 1.255536, "longitude": 103.611566},
        ],
    )

    audited = audit_managed_location(location)

    assert audited.has_errors is False
    assert audited.has_warnings is False
    assert audited.coordinate_count == 3
    assert audited.unique_coordinate_count == 3
    assert audited.polygon_area_square_meters is not None
    assert audited.polygon_area_square_meters > 0


def test_audit_flags_legacy_single_coordinate_locations():
    location = _build_location(
        location_id=2,
        local="Ponto Legado",
        coordinates=None,
        coordinates_json=None,
    )

    audited = audit_managed_location(location)
    issue_codes = {issue.code for issue in audited.issues}

    assert "legacy_primary_coordinate_only" in issue_codes
    assert "too_few_coordinates" in issue_codes
    assert audited.has_errors is True


def test_audit_flags_duplicate_vertices_and_degenerate_polygon():
    location = _build_location(
        location_id=3,
        local="Vertices Duplicados",
        coordinates=[
            {"latitude": 1.255936, "longitude": 103.611066},
            {"latitude": 1.255936, "longitude": 103.611066},
            {"latitude": 1.256136, "longitude": 103.611466},
        ],
    )

    audited = audit_managed_location(location)
    issue_codes = {issue.code for issue in audited.issues}

    assert "duplicate_coordinates" in issue_codes
    assert "too_few_unique_coordinates" in issue_codes
    assert "zero_area_polygon" in issue_codes


def test_audit_flags_self_intersecting_polygon_for_manual_review():
    location = _build_location(
        location_id=4,
        local="Laco",
        coordinates=[
            {"latitude": 1.255936, "longitude": 103.611066},
            {"latitude": 1.256436, "longitude": 103.611566},
            {"latitude": 1.255936, "longitude": 103.611566},
            {"latitude": 1.256436, "longitude": 103.611066},
        ],
    )

    audited = audit_managed_location(location)
    issue_codes = {issue.code for issue in audited.issues}

    assert "self_intersection" in issue_codes
    assert "potential_vertex_order_problem" in issue_codes
    assert audited.needs_manual_review is True


def test_audit_flags_malformed_coordinates_json():
    location = _build_location(
        location_id=5,
        local="JSON Invalido",
        coordinates=None,
        coordinates_json="not-json",
    )

    audited = audit_managed_location(location)
    issue_codes = {issue.code for issue in audited.issues}

    assert "malformed_coordinates_json" in issue_codes
    assert "legacy_primary_coordinate_only" in issue_codes
    assert "too_few_coordinates" in issue_codes


def test_audit_flags_invalid_nonpositive_tolerance():
    location = _build_location(
        location_id=8,
        local="Tolerancia Invalida",
        coordinates=[
            {"latitude": 1.255936, "longitude": 103.611066},
            {"latitude": 1.256136, "longitude": 103.611466},
            {"latitude": 1.255536, "longitude": 103.611566},
        ],
        tolerance_meters=0,
    )

    audited = audit_managed_location(location)
    issue_codes = {issue.code for issue in audited.issues}

    assert "invalid_tolerance_meters" in issue_codes
    assert audited.has_errors is True


def test_audit_report_summary_and_text_output_include_flagged_rows():
    valid_location = _build_location(
        location_id=6,
        local="Base Principal",
        coordinates=[
            {"latitude": 1.255936, "longitude": 103.611066},
            {"latitude": 1.256136, "longitude": 103.611466},
            {"latitude": 1.255536, "longitude": 103.611566},
        ],
    )
    checkout_location = _build_location(
        location_id=7,
        local="Zona de CheckOut",
        coordinates=None,
        coordinates_json=None,
    )

    report = audit_managed_locations([valid_location, checkout_location])
    rendered = build_location_audit_text(report)

    assert report.summary.total_locations == 2
    assert report.summary.checkout_zone_locations == 1
    assert report.summary.locations_with_errors == 1
    assert report.summary.issue_counts["too_few_coordinates"] == 1
    assert "#7 Zona de CheckOut" in rendered
    assert "too_few_coordinates" in rendered
    assert "Base Principal" not in rendered