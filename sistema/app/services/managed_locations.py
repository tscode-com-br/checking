from __future__ import annotations

import json
from collections.abc import Iterable
from typing import TypedDict

from ..models import ManagedLocation
from .project_catalog import normalize_project_name


class LocationCoordinateValue(TypedDict):
    latitude: float
    longitude: float


def build_location_coordinate(latitude: float, longitude: float) -> LocationCoordinateValue:
    return {"latitude": float(latitude), "longitude": float(longitude)}


def dump_location_coordinates(coordinates: Iterable[LocationCoordinateValue]) -> str:
    normalized = [build_location_coordinate(item["latitude"], item["longitude"]) for item in coordinates]
    return json.dumps(normalized, ensure_ascii=True, separators=(",", ":"))


def normalize_location_project_names(project_names: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for project_name in project_names:
        normalized_name = normalize_project_name(project_name, field_name="O projeto da localização")
        if normalized_name in seen:
            continue
        seen.add(normalized_name)
        normalized.append(normalized_name)
    return normalized


def dump_location_projects(project_names: Iterable[str]) -> str:
    normalized = normalize_location_project_names(project_names)
    return json.dumps(normalized, ensure_ascii=True, separators=(",", ":"))


def extract_location_coordinates(location: ManagedLocation) -> list[LocationCoordinateValue]:
    if location.coordinates_json:
        try:
            raw_items = json.loads(location.coordinates_json)
        except (TypeError, ValueError):
            raw_items = None

        if isinstance(raw_items, list):
            coordinates: list[LocationCoordinateValue] = []
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                latitude = item.get("latitude")
                longitude = item.get("longitude")
                try:
                    coordinates.append(build_location_coordinate(float(latitude), float(longitude)))
                except (TypeError, ValueError):
                    continue
            if coordinates:
                return coordinates

    return [build_location_coordinate(location.latitude, location.longitude)]


def extract_location_projects(location: ManagedLocation) -> list[str]:
    if location.projects_json:
        try:
            raw_items = json.loads(location.projects_json)
        except (TypeError, ValueError):
            raw_items = None

        if isinstance(raw_items, list):
            normalized: list[str] = []
            seen: set[str] = set()
            for item in raw_items:
                try:
                    project_name = normalize_project_name(str(item), field_name="O projeto da localização")
                except ValueError:
                    continue
                if project_name in seen:
                    continue
                seen.add(project_name)
                normalized.append(project_name)
            if normalized:
                return normalized

    return []


def location_supports_project(location: ManagedLocation, project_name: str | None) -> bool:
    normalized_project = str(project_name or "").strip()
    if not normalized_project:
        return True

    normalized_project = normalize_project_name(normalized_project, field_name="O projeto do usuário")
    location_projects = extract_location_projects(location)
    if not location_projects:
        return True
    return normalized_project in set(location_projects)


def filter_locations_for_project(locations: Iterable[ManagedLocation], project_name: str | None) -> list[ManagedLocation]:
    return [location for location in locations if location_supports_project(location, project_name)]