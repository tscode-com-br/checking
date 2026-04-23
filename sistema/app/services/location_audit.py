from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import MetaData, Table, inspect as sqlalchemy_inspect, select
from sqlalchemy.orm import Session

from ..models import ManagedLocation
from .location_matching import is_checkout_zone_name
from .managed_locations import build_location_coordinate, extract_location_projects


AuditSeverity = Literal["error", "warning", "info"]
_EARTH_RADIUS_METERS = 6_371_000.0
_AREA_EPSILON_SQUARE_METERS = 1e-3
_GEOMETRY_EPSILON_METERS = 1e-6


@dataclass(frozen=True)
class LocationAuditIssue:
    code: str
    severity: AuditSeverity
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }


@dataclass(frozen=True)
class LocationAuditRow:
    location_id: int
    local: str
    projects: tuple[str, ...]
    is_checkout_zone: bool
    tolerance_meters: int
    coordinate_count: int
    effective_vertex_count: int
    unique_coordinate_count: int
    polygon_area_square_meters: float | None
    issues: tuple[LocationAuditIssue, ...]

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(issue.severity == "warning" for issue in self.issues)

    @property
    def needs_manual_review(self) -> bool:
        manual_review_codes = {
            "self_intersection",
            "potential_vertex_order_problem",
            "duplicate_coordinates",
            "too_few_coordinates",
            "too_few_unique_coordinates",
            "zero_area_polygon",
            "malformed_coordinates_json",
        }
        return any(issue.code in manual_review_codes for issue in self.issues)

    def to_dict(self) -> dict[str, object]:
        return {
            "location_id": self.location_id,
            "local": self.local,
            "projects": list(self.projects),
            "is_checkout_zone": self.is_checkout_zone,
            "tolerance_meters": self.tolerance_meters,
            "coordinate_count": self.coordinate_count,
            "effective_vertex_count": self.effective_vertex_count,
            "unique_coordinate_count": self.unique_coordinate_count,
            "polygon_area_square_meters": self.polygon_area_square_meters,
            "has_errors": self.has_errors,
            "has_warnings": self.has_warnings,
            "needs_manual_review": self.needs_manual_review,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class LocationAuditSummary:
    total_locations: int
    checkout_zone_locations: int
    valid_polygon_locations: int
    locations_with_errors: int
    locations_with_warnings_only: int
    locations_without_issues: int
    locations_requiring_manual_review: int
    issue_counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "total_locations": self.total_locations,
            "checkout_zone_locations": self.checkout_zone_locations,
            "valid_polygon_locations": self.valid_polygon_locations,
            "locations_with_errors": self.locations_with_errors,
            "locations_with_warnings_only": self.locations_with_warnings_only,
            "locations_without_issues": self.locations_without_issues,
            "locations_requiring_manual_review": self.locations_requiring_manual_review,
            "issue_counts": dict(self.issue_counts),
        }


@dataclass(frozen=True)
class LocationAuditReport:
    rows: tuple[LocationAuditRow, ...]
    summary: LocationAuditSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary.to_dict(),
            "rows": [row.to_dict() for row in self.rows],
        }


@dataclass(frozen=True)
class _CoordinateInspection:
    coordinates: tuple[dict[str, float], ...]
    has_coordinates_json: bool
    used_primary_coordinate_fallback: bool
    invalid_entry_count: int
    malformed_coordinates_json: bool


def audit_locations_from_db(db: Session) -> LocationAuditReport:
    rows = _load_locations_for_audit(db)
    return audit_managed_locations(rows)


def audit_managed_locations(locations: list[ManagedLocation]) -> LocationAuditReport:
    audited_rows = tuple(audit_managed_location(location) for location in locations)
    issue_counts = Counter(issue.code for row in audited_rows for issue in row.issues)
    locations_with_errors = sum(1 for row in audited_rows if row.has_errors)
    locations_with_warnings_only = sum(1 for row in audited_rows if not row.has_errors and row.has_warnings)
    locations_without_issues = sum(1 for row in audited_rows if not row.issues)
    valid_polygon_locations = sum(1 for row in audited_rows if not row.has_errors)
    checkout_zone_locations = sum(1 for row in audited_rows if row.is_checkout_zone)
    locations_requiring_manual_review = sum(1 for row in audited_rows if row.needs_manual_review)
    summary = LocationAuditSummary(
        total_locations=len(audited_rows),
        checkout_zone_locations=checkout_zone_locations,
        valid_polygon_locations=valid_polygon_locations,
        locations_with_errors=locations_with_errors,
        locations_with_warnings_only=locations_with_warnings_only,
        locations_without_issues=locations_without_issues,
        locations_requiring_manual_review=locations_requiring_manual_review,
        issue_counts=dict(sorted(issue_counts.items())),
    )
    return LocationAuditReport(rows=audited_rows, summary=summary)


def audit_managed_location(location: ManagedLocation) -> LocationAuditRow:
    issues: list[LocationAuditIssue] = []
    inspection = _inspect_location_coordinates(location)

    if inspection.malformed_coordinates_json:
        issues.append(
            LocationAuditIssue(
                code="malformed_coordinates_json",
                severity="error",
                message="The stored coordinates_json payload is malformed and could not be parsed.",
            )
        )

    if inspection.invalid_entry_count:
        issues.append(
            LocationAuditIssue(
                code="invalid_coordinate_entries",
                severity="warning",
                message=(
                    f"The stored coordinate list contains {inspection.invalid_entry_count} invalid or incomplete entries."
                ),
            )
        )

    if inspection.used_primary_coordinate_fallback:
        issues.append(
            LocationAuditIssue(
                code="legacy_primary_coordinate_only",
                severity="warning",
                message="The location still relies on the legacy primary coordinate fields and has no valid polygon vertex list.",
            )
        )

    coordinates = list(inspection.coordinates)
    coordinate_count = len(coordinates)
    tolerance_meters = int(location.tolerance_meters or 0)
    if tolerance_meters < 1:
        issues.append(
            LocationAuditIssue(
                code="invalid_tolerance_meters",
                severity="error",
                message="The location tolerance must be a positive integer in meters.",
            )
        )

    if coordinate_count < 3:
        issues.append(
            LocationAuditIssue(
                code="too_few_coordinates",
                severity="error",
                message="A polygonal location requires at least 3 coordinates.",
            )
        )

    coordinates, had_redundant_closing_vertex = _strip_redundant_closing_vertex(coordinates)
    if had_redundant_closing_vertex:
        issues.append(
            LocationAuditIssue(
                code="redundant_closing_vertex",
                severity="warning",
                message="The last coordinate repeats the first vertex and should be removed from the stored list.",
            )
        )

    duplicate_coordinates = _find_duplicate_coordinates(coordinates)
    if duplicate_coordinates:
        issues.append(
            LocationAuditIssue(
                code="duplicate_coordinates",
                severity="error",
                message=f"The polygon contains duplicated vertices: {', '.join(duplicate_coordinates)}.",
            )
        )

    unique_coordinate_count = len({_coordinate_key(coordinate) for coordinate in coordinates})
    if unique_coordinate_count < 3:
        issues.append(
            LocationAuditIssue(
                code="too_few_unique_coordinates",
                severity="error",
                message="The polygon does not contain 3 distinct vertices after removing duplicates.",
            )
        )

    polygon_area_square_meters: float | None = None
    projected_coordinates = _project_coordinates_in_meters(coordinates)
    if len(projected_coordinates) >= 3:
        polygon_area_square_meters = _shoelace_area_square_meters(projected_coordinates)
        if polygon_area_square_meters <= _AREA_EPSILON_SQUARE_METERS:
            issues.append(
                LocationAuditIssue(
                    code="zero_area_polygon",
                    severity="error",
                    message="The polygon area is zero or too close to zero, which indicates collinear or degenerate vertices.",
                )
            )

    if len(projected_coordinates) >= 4 and _has_self_intersection(projected_coordinates):
        issues.append(
            LocationAuditIssue(
                code="self_intersection",
                severity="error",
                message="The polygon edges intersect each other and the geometry is invalid.",
            )
        )
        issues.append(
            LocationAuditIssue(
                code="potential_vertex_order_problem",
                severity="warning",
                message="The vertex order likely needs manual review because the polygon is self-intersecting.",
            )
        )

    return LocationAuditRow(
        location_id=int(location.id or 0),
        local=location.local,
        projects=tuple(extract_location_projects(location)),
        is_checkout_zone=is_checkout_zone_name(location.local),
        tolerance_meters=tolerance_meters,
        coordinate_count=coordinate_count,
        effective_vertex_count=len(coordinates),
        unique_coordinate_count=unique_coordinate_count,
        polygon_area_square_meters=polygon_area_square_meters,
        issues=tuple(issues),
    )


def build_location_audit_text(report: LocationAuditReport, *, include_valid: bool = False) -> str:
    summary = report.summary
    lines = [
        "Location audit summary",
        f"- total_locations: {summary.total_locations}",
        f"- checkout_zone_locations: {summary.checkout_zone_locations}",
        f"- valid_polygon_locations: {summary.valid_polygon_locations}",
        f"- locations_with_errors: {summary.locations_with_errors}",
        f"- locations_with_warnings_only: {summary.locations_with_warnings_only}",
        f"- locations_without_issues: {summary.locations_without_issues}",
        f"- locations_requiring_manual_review: {summary.locations_requiring_manual_review}",
    ]
    if summary.issue_counts:
        lines.append("- issue_counts:")
        for code, count in summary.issue_counts.items():
            lines.append(f"  - {code}: {count}")

    flagged_rows = [row for row in report.rows if include_valid or row.issues]
    if not flagged_rows:
        lines.append("")
        lines.append("No locations with issues were found.")
        return "\n".join(lines)

    lines.append("")
    lines.append("Location details")
    for row in flagged_rows:
        severity_label = "ERROR" if row.has_errors else "WARN" if row.has_warnings else "OK"
        projects_label = ", ".join(row.projects) if row.projects else "all-projects"
        area_label = (
            f"{row.polygon_area_square_meters:.3f}"
            if row.polygon_area_square_meters is not None
            else "n/a"
        )
        lines.append(
            (
                f"- [{severity_label}] #{row.location_id} {row.local}"
                f" | projects={projects_label}"
                f" | checkout_zone={'yes' if row.is_checkout_zone else 'no'}"
                f" | tolerance_meters={row.tolerance_meters}"
                f" | coordinates={row.coordinate_count}"
                f" | effective_vertices={row.effective_vertex_count}"
                f" | unique_vertices={row.unique_coordinate_count}"
                f" | area_m2={area_label}"
            )
        )
        for issue in row.issues:
            lines.append(f"  - {issue.severity.upper()} {issue.code}: {issue.message}")
    return "\n".join(lines)


def _inspect_location_coordinates(location: ManagedLocation) -> _CoordinateInspection:
    primary_coordinate = build_location_coordinate(location.latitude, location.longitude)
    raw_payload = location.coordinates_json
    if not raw_payload:
        return _CoordinateInspection(
            coordinates=(primary_coordinate,),
            has_coordinates_json=False,
            used_primary_coordinate_fallback=True,
            invalid_entry_count=0,
            malformed_coordinates_json=False,
        )

    try:
        raw_items = json.loads(raw_payload)
    except (TypeError, ValueError):
        return _CoordinateInspection(
            coordinates=(primary_coordinate,),
            has_coordinates_json=True,
            used_primary_coordinate_fallback=True,
            invalid_entry_count=0,
            malformed_coordinates_json=True,
        )

    if not isinstance(raw_items, list):
        return _CoordinateInspection(
            coordinates=(primary_coordinate,),
            has_coordinates_json=True,
            used_primary_coordinate_fallback=True,
            invalid_entry_count=0,
            malformed_coordinates_json=True,
        )

    coordinates: list[dict[str, float]] = []
    invalid_entry_count = 0
    for item in raw_items:
        if not isinstance(item, dict):
            invalid_entry_count += 1
            continue
        latitude = item.get("latitude")
        longitude = item.get("longitude")
        try:
            coordinates.append(build_location_coordinate(float(latitude), float(longitude)))
        except (TypeError, ValueError):
            invalid_entry_count += 1

    if coordinates:
        return _CoordinateInspection(
            coordinates=tuple(coordinates),
            has_coordinates_json=True,
            used_primary_coordinate_fallback=False,
            invalid_entry_count=invalid_entry_count,
            malformed_coordinates_json=False,
        )

    return _CoordinateInspection(
        coordinates=(primary_coordinate,),
        has_coordinates_json=True,
        used_primary_coordinate_fallback=True,
        invalid_entry_count=max(invalid_entry_count, len(raw_items)),
        malformed_coordinates_json=False,
    )


def _load_locations_for_audit(db: Session) -> list[ManagedLocation]:
    bind = db.get_bind()
    inspector = sqlalchemy_inspect(bind)
    if "locations" not in set(inspector.get_table_names()):
        return []

    metadata = MetaData()
    locations_table = Table("locations", metadata, autoload_with=bind)
    available_columns = set(locations_table.c.keys())
    query_columns = [
        locations_table.c.id,
        locations_table.c.local,
        locations_table.c.latitude,
        locations_table.c.longitude,
    ]
    optional_column_names = [
        "coordinates_json",
        "projects_json",
        "tolerance_meters",
        "created_at",
        "updated_at",
    ]
    for column_name in optional_column_names:
        if column_name in available_columns:
            query_columns.append(locations_table.c[column_name])

    rows = db.execute(
        select(*query_columns).order_by(locations_table.c.local, locations_table.c.id)
    ).mappings().all()

    fallback_timestamp = datetime.now(timezone.utc)
    managed_locations: list[ManagedLocation] = []
    for row in rows:
        managed_locations.append(
            ManagedLocation(
                id=row["id"],
                local=row["local"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                coordinates_json=row.get("coordinates_json"),
                projects_json=row.get("projects_json"),
                tolerance_meters=row.get("tolerance_meters") or 0,
                created_at=row.get("created_at") or fallback_timestamp,
                updated_at=row.get("updated_at") or fallback_timestamp,
            )
        )
    return managed_locations


def _strip_redundant_closing_vertex(
    coordinates: list[dict[str, float]],
) -> tuple[list[dict[str, float]], bool]:
    if len(coordinates) < 2:
        return coordinates, False
    if _coordinate_key(coordinates[0]) != _coordinate_key(coordinates[-1]):
        return coordinates, False
    return coordinates[:-1], True


def _find_duplicate_coordinates(coordinates: list[dict[str, float]]) -> list[str]:
    seen: set[tuple[float, float]] = set()
    duplicates: list[str] = []
    for coordinate in coordinates:
        key = _coordinate_key(coordinate)
        if key in seen:
            duplicates.append(_format_coordinate_key(key))
            continue
        seen.add(key)
    return duplicates


def _coordinate_key(coordinate: dict[str, float]) -> tuple[float, float]:
    return (round(float(coordinate["latitude"]), 9), round(float(coordinate["longitude"]), 9))


def _format_coordinate_key(key: tuple[float, float]) -> str:
    latitude, longitude = key
    return f"{latitude:.9f},{longitude:.9f}"


def _project_coordinates_in_meters(coordinates: list[dict[str, float]]) -> list[tuple[float, float]]:
    if not coordinates:
        return []
    origin_latitude = sum(float(coordinate["latitude"]) for coordinate in coordinates) / len(coordinates)
    origin_longitude = sum(float(coordinate["longitude"]) for coordinate in coordinates) / len(coordinates)
    origin_latitude_radians = math.radians(origin_latitude)
    origin_longitude_radians = math.radians(origin_longitude)
    projected: list[tuple[float, float]] = []
    for coordinate in coordinates:
        latitude_radians = math.radians(float(coordinate["latitude"]))
        longitude_radians = math.radians(float(coordinate["longitude"]))
        projected.append(
            (
                _EARTH_RADIUS_METERS
                * (longitude_radians - origin_longitude_radians)
                * math.cos(origin_latitude_radians),
                _EARTH_RADIUS_METERS * (latitude_radians - origin_latitude_radians),
            )
        )
    return projected


def _shoelace_area_square_meters(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    total = 0.0
    for index, (x_1, y_1) in enumerate(points):
        x_2, y_2 = points[(index + 1) % len(points)]
        total += (x_1 * y_2) - (x_2 * y_1)
    return abs(total) / 2.0


def _has_self_intersection(points: list[tuple[float, float]]) -> bool:
    point_count = len(points)
    if point_count < 4:
        return False

    for first_index in range(point_count):
        first_start = points[first_index]
        first_end = points[(first_index + 1) % point_count]
        for second_index in range(first_index + 1, point_count):
            if first_index == second_index:
                continue
            if (first_index + 1) % point_count == second_index:
                continue
            if (second_index + 1) % point_count == first_index:
                continue

            second_start = points[second_index]
            second_end = points[(second_index + 1) % point_count]
            if _segments_intersect(first_start, first_end, second_start, second_end):
                return True

    return False


def _segments_intersect(
    first_start: tuple[float, float],
    first_end: tuple[float, float],
    second_start: tuple[float, float],
    second_end: tuple[float, float],
) -> bool:
    orientation_1 = _orientation(first_start, first_end, second_start)
    orientation_2 = _orientation(first_start, first_end, second_end)
    orientation_3 = _orientation(second_start, second_end, first_start)
    orientation_4 = _orientation(second_start, second_end, first_end)

    if orientation_1 != orientation_2 and orientation_3 != orientation_4:
        return True

    if orientation_1 == 0 and _point_on_segment(first_start, second_start, first_end):
        return True
    if orientation_2 == 0 and _point_on_segment(first_start, second_end, first_end):
        return True
    if orientation_3 == 0 and _point_on_segment(second_start, first_start, second_end):
        return True
    if orientation_4 == 0 and _point_on_segment(second_start, first_end, second_end):
        return True

    return False


def _orientation(
    first: tuple[float, float],
    second: tuple[float, float],
    third: tuple[float, float],
) -> int:
    cross_product = (
        (second[1] - first[1]) * (third[0] - second[0])
        - (second[0] - first[0]) * (third[1] - second[1])
    )
    if abs(cross_product) <= _GEOMETRY_EPSILON_METERS:
        return 0
    return 1 if cross_product > 0 else -1


def _point_on_segment(
    start: tuple[float, float],
    point: tuple[float, float],
    end: tuple[float, float],
) -> bool:
    return (
        min(start[0], end[0]) - _GEOMETRY_EPSILON_METERS <= point[0] <= max(start[0], end[0]) + _GEOMETRY_EPSILON_METERS
        and min(start[1], end[1]) - _GEOMETRY_EPSILON_METERS <= point[1] <= max(start[1], end[1]) + _GEOMETRY_EPSILON_METERS
    )