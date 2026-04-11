from __future__ import annotations

import json
from collections.abc import Iterable
from typing import TypedDict

from ..models import ManagedLocation


class LocationCoordinateValue(TypedDict):
    latitude: float
    longitude: float


def build_location_coordinate(latitude: float, longitude: float) -> LocationCoordinateValue:
    return {"latitude": float(latitude), "longitude": float(longitude)}


def dump_location_coordinates(coordinates: Iterable[LocationCoordinateValue]) -> str:
    normalized = [build_location_coordinate(item["latitude"], item["longitude"]) for item in coordinates]
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