from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
import hashlib
from math import ceil
from typing import Any, Literal
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..core.config import Settings, settings


def _normalize_required_text(value: object, *, field_name: str) -> str:
    normalized = " ".join(str(value or "").strip().split())
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _normalize_optional_text(value: object) -> str | None:
    normalized = " ".join(str(value or "").strip().split())
    return normalized or None


class TransportRouteCoordinate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    label: str | None = Field(default=None, max_length=120)

    @field_validator("label")
    @classmethod
    def _validate_label(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    def as_pair(self) -> tuple[float, float]:
        return (self.longitude, self.latitude)


class GeocodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: str
    zip_code: str
    country_name: str
    country_code: str | None = Field(default=None, min_length=2, max_length=3)
    language: str | None = Field(default=None, min_length=2, max_length=16)
    limit: int = Field(default=1, ge=1, le=10)

    @field_validator("address", "zip_code", "country_name")
    @classmethod
    def _validate_required_text_fields(cls, value: str, info) -> str:
        return _normalize_required_text(value, field_name=info.field_name)

    @field_validator("country_code")
    @classmethod
    def _validate_country_code(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        return normalized.upper() if normalized is not None else None

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        return normalized.lower() if normalized is not None else None

    @property
    def normalized_query(self) -> str:
        return ", ".join(
            part.lower()
            for part in [self.address, self.zip_code, self.country_name]
            if part
        )


class GeocodeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    query: str
    formatted_address: str
    coordinate: TransportRouteCoordinate
    confidence: float | None = Field(default=None, ge=0, le=1)
    provider_place_id: str | None = Field(default=None, max_length=255)
    country_code: str | None = Field(default=None, min_length=2, max_length=3)
    country_name: str | None = Field(default=None, max_length=120)
    raw_response_json: dict[str, Any] | list[Any] | None = None

    @field_validator("provider", "query", "formatted_address")
    @classmethod
    def _validate_required_text_fields(cls, value: str, info) -> str:
        return _normalize_required_text(value, field_name=info.field_name)

    @field_validator("provider_place_id", "country_name")
    @classmethod
    def _validate_optional_text_fields(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("country_code")
    @classmethod
    def _validate_country_code(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        return normalized.upper() if normalized is not None else None

    @property
    def longitude(self) -> float:
        return self.coordinate.longitude

    @property
    def latitude(self) -> float:
        return self.coordinate.latitude


class MatrixRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: str
    sources: list[TransportRouteCoordinate] = Field(min_length=1)
    destinations: list[TransportRouteCoordinate] = Field(min_length=1)
    depart_at: datetime | None = None
    annotations: tuple[Literal["duration", "distance"], ...] = ("duration", "distance")

    @field_validator("profile")
    @classmethod
    def _validate_profile(cls, value: str) -> str:
        return _normalize_required_text(value, field_name="profile")

    @field_validator("annotations")
    @classmethod
    def _validate_annotations(
        cls,
        value: tuple[Literal["duration", "distance"], ...],
    ) -> tuple[Literal["duration", "distance"], ...]:
        if not value:
            raise ValueError("annotations must include at least one requested matrix value")
        return value

    def source_pairs(self) -> list[tuple[float, float]]:
        return [coordinate.as_pair() for coordinate in self.sources]

    def destination_pairs(self) -> list[tuple[float, float]]:
        return [coordinate.as_pair() for coordinate in self.destinations]


class MatrixResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    profile: str
    sources: list[TransportRouteCoordinate] = Field(min_length=1)
    destinations: list[TransportRouteCoordinate] = Field(min_length=1)
    durations_seconds: list[list[float | None]]
    distances_meters: list[list[float | None]] | None = None
    depart_at: datetime | None = None
    matrix_request_count: int = Field(default=0, ge=0)
    matrix_chunk_count: int = Field(default=0, ge=0)
    source_chunk_size: int | None = Field(default=None, ge=1)
    destination_chunk_size: int | None = Field(default=None, ge=1)

    @field_validator("provider", "profile")
    @classmethod
    def _validate_required_text_fields(cls, value: str, info) -> str:
        return _normalize_required_text(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _validate_matrix_shapes(self) -> MatrixResult:
        expected_row_count = len(self.sources)
        expected_column_count = len(self.destinations)

        def _validate_shape(matrix: list[list[float | None]], *, field_name: str) -> None:
            if len(matrix) != expected_row_count:
                raise ValueError(
                    f"{field_name} row count must match sources length ({expected_row_count})."
                )
            for row in matrix:
                if len(row) != expected_column_count:
                    raise ValueError(
                        f"{field_name} column count must match destinations length ({expected_column_count})."
                    )

        _validate_shape(self.durations_seconds, field_name="durations_seconds")
        if self.distances_meters is not None:
            _validate_shape(self.distances_meters, field_name="distances_meters")
        return self


class DirectionsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: str
    coordinates: list[TransportRouteCoordinate] = Field(min_length=2)
    depart_at: datetime | None = None
    geometry_format: Literal["geojson", "polyline", "polyline6"] = "geojson"
    include_steps: bool = False

    @field_validator("profile")
    @classmethod
    def _validate_profile(cls, value: str) -> str:
        return _normalize_required_text(value, field_name="profile")

    def coordinate_pairs(self) -> list[tuple[float, float]]:
        return [coordinate.as_pair() for coordinate in self.coordinates]


class DirectionsLeg(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: TransportRouteCoordinate
    end: TransportRouteCoordinate
    distance_meters: float = Field(ge=0)
    duration_seconds: float = Field(ge=0)


class DirectionsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    profile: str
    coordinates: list[TransportRouteCoordinate] = Field(min_length=2)
    distance_meters: float = Field(ge=0)
    duration_seconds: float = Field(ge=0)
    geometry: dict[str, Any] | str | None = None
    legs: list[DirectionsLeg] = Field(default_factory=list)
    depart_at: datetime | None = None

    @field_validator("provider", "profile")
    @classmethod
    def _validate_required_text_fields(cls, value: str, info) -> str:
        return _normalize_required_text(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _validate_leg_count(self) -> DirectionsResult:
        if self.legs and len(self.legs) != len(self.coordinates) - 1:
            raise ValueError("legs length must match coordinate hops")
        return self


class TransportRouteProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        provider: str,
        operation: Literal["geocode", "matrix", "directions"],
        status_code: int | None = None,
    ) -> None:
        self.provider = _normalize_required_text(provider, field_name="provider")
        self.operation = operation
        self.status_code = status_code
        super().__init__(message)


class TransportRouteProviderAuthError(TransportRouteProviderError):
    pass


class TransportRouteProviderTimeoutError(TransportRouteProviderError):
    pass


class TransportRouteProviderInvalidResponseError(TransportRouteProviderError):
    pass


class TransportRouteProviderNoRouteError(TransportRouteProviderError):
    pass


class TransportRouteProviderNoResultError(TransportRouteProviderError):
    pass


class TransportRouteProvider(ABC):
    provider_name: str = ""

    @property
    def provider(self) -> str:
        return _normalize_required_text(self.provider_name, field_name="provider_name")

    @abstractmethod
    def geocode(self, request: GeocodeRequest) -> GeocodeResult:
        raise NotImplementedError

    @abstractmethod
    def get_matrix(self, request: MatrixRequest) -> MatrixResult:
        raise NotImplementedError

    @abstractmethod
    def get_directions(self, request: DirectionsRequest) -> DirectionsResult:
        raise NotImplementedError


class FakeTransportRouteCatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formatted_address: str
    coordinate: TransportRouteCoordinate
    confidence: float | None = Field(default=1.0, ge=0, le=1)
    provider_place_id: str | None = Field(default=None, max_length=255)
    country_code: str | None = Field(default=None, min_length=2, max_length=3)
    country_name: str | None = Field(default=None, max_length=120)

    @field_validator("formatted_address")
    @classmethod
    def _validate_formatted_address(cls, value: str) -> str:
        return _normalize_required_text(value, field_name="formatted_address")

    @field_validator("provider_place_id", "country_name")
    @classmethod
    def _validate_optional_text_fields(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("country_code")
    @classmethod
    def _validate_country_code(cls, value: str | None) -> str | None:
        normalized = _normalize_optional_text(value)
        return normalized.upper() if normalized is not None else None


DEFAULT_FAKE_TRANSPORT_ROUTE_CATALOG: dict[str, FakeTransportRouteCatalogEntry] = {
    "10 bayfront avenue, 018956, singapore": FakeTransportRouteCatalogEntry(
        formatted_address="10 Bayfront Avenue, Singapore 018956",
        coordinate=TransportRouteCoordinate(
            longitude=103.8607,
            latitude=1.2834,
            label="10 Bayfront Avenue",
        ),
        confidence=1.0,
        provider_place_id="fake-place-10-bayfront-avenue",
        country_code="SG",
        country_name="Singapore",
    ),
    "25 raffles place, 048621, singapore": FakeTransportRouteCatalogEntry(
        formatted_address="25 Raffles Place, Singapore 048621",
        coordinate=TransportRouteCoordinate(
            longitude=103.8520,
            latitude=1.2840,
            label="25 Raffles Place",
        ),
        confidence=1.0,
        provider_place_id="fake-place-25-raffles-place",
        country_code="SG",
        country_name="Singapore",
    ),
    "80 robinson road, 068898, singapore": FakeTransportRouteCatalogEntry(
        formatted_address="80 Robinson Road, Singapore 068898",
        coordinate=TransportRouteCoordinate(
            longitude=103.8486,
            latitude=1.2786,
            label="80 Robinson Road",
        ),
        confidence=1.0,
        provider_place_id="fake-place-80-robinson-road",
        country_code="SG",
        country_name="Singapore",
    ),
    "1 marina boulevard, 018989, singapore": FakeTransportRouteCatalogEntry(
        formatted_address="1 Marina Boulevard, Singapore 018989",
        coordinate=TransportRouteCoordinate(
            longitude=103.8545,
            latitude=1.2825,
            label="1 Marina Boulevard",
        ),
        confidence=1.0,
        provider_place_id="fake-place-1-marina-boulevard",
        country_code="SG",
        country_name="Singapore",
    ),
}

_FAKE_COUNTRY_NAME_TO_CODE = {
    "brazil": "BR",
    "brasil": "BR",
    "chile": "CL",
    "china": "CN",
    "malasia": "MY",
    "malaysia": "MY",
    "malásia": "MY",
    "singapore": "SG",
    "singapura": "SG",
}

_FAKE_COUNTRY_ANCHORS = {
    "BR": (-46.6333, -23.5505),
    "CL": (-70.6693, -33.4489),
    "CN": (113.2644, 23.1291),
    "MY": (101.6869, 3.1390),
    "SG": (103.8198, 1.3521),
}


class FakeTransportRouteProvider(TransportRouteProvider):
    provider_name = "fake"

    def __init__(
        self,
        *,
        settings_obj: Settings = settings,
        catalog: dict[str, FakeTransportRouteCatalogEntry] | None = None,
        asymmetric_matrix: bool | None = None,
        allow_synthetic_geocode: bool = True,
    ) -> None:
        self._settings = settings_obj
        self._catalog = dict(catalog or DEFAULT_FAKE_TRANSPORT_ROUTE_CATALOG)
        self._asymmetric_matrix = (
            settings_obj.transport_ai_fake_matrix_asymmetric
            if asymmetric_matrix is None
            else bool(asymmetric_matrix)
        )
        self._allow_synthetic_geocode = bool(allow_synthetic_geocode)

    def geocode(self, request: GeocodeRequest) -> GeocodeResult:
        entry = self._catalog.get(request.normalized_query)
        if entry is None:
            if not self._allow_synthetic_geocode:
                raise TransportRouteProviderNoResultError(
                    f"No geocode result for {request.normalized_query}",
                    provider=self.provider,
                    operation="geocode",
                )
            entry = self._build_synthetic_catalog_entry(request)

        effective_country_code = request.country_code or entry.country_code
        effective_country_name = request.country_name or entry.country_name
        return GeocodeResult(
            provider=self.provider,
            query=request.normalized_query,
            formatted_address=entry.formatted_address,
            coordinate=entry.coordinate,
            confidence=entry.confidence,
            provider_place_id=entry.provider_place_id or self._build_fake_place_id(request.normalized_query),
            country_code=effective_country_code,
            country_name=effective_country_name,
            raw_response_json={
                "catalog_match": request.normalized_query in self._catalog,
                "query": request.normalized_query,
                "coordinate": entry.coordinate.model_dump(mode="json"),
            },
        )

    def get_matrix(self, request: MatrixRequest) -> MatrixResult:
        durations: list[list[float]] = []
        distances: list[list[float]] | None = [] if "distance" in request.annotations else None
        request_plan = describe_transport_route_matrix_request_plan(
            provider_name=self.provider,
            profile=request.profile,
            source_count=len(request.sources),
            destination_count=len(request.destinations),
        )

        for source in request.sources:
            duration_row: list[float] = []
            distance_row: list[float] = []
            for destination in request.destinations:
                distance_meters, duration_seconds = self._estimate_leg(
                    start=source,
                    end=destination,
                    profile=request.profile,
                )
                duration_row.append(duration_seconds)
                distance_row.append(distance_meters)
            durations.append(duration_row)
            if distances is not None:
                distances.append(distance_row)

        return MatrixResult(
            provider=self.provider,
            profile=_normalize_required_text(request.profile, field_name="profile"),
            sources=request.sources,
            destinations=request.destinations,
            durations_seconds=durations,
            distances_meters=distances,
            depart_at=request.depart_at,
            matrix_request_count=int(request_plan["matrix_request_count"] or 0),
            matrix_chunk_count=int(request_plan["matrix_chunk_count"] or 0),
            source_chunk_size=int(request_plan["source_chunk_size"] or len(request.sources)),
            destination_chunk_size=int(request_plan["destination_chunk_size"] or len(request.destinations)),
        )

    def get_directions(self, request: DirectionsRequest) -> DirectionsResult:
        legs: list[DirectionsLeg] = []
        total_distance = 0.0
        total_duration = 0.0

        for start, end in zip(request.coordinates, request.coordinates[1:]):
            distance_meters, duration_seconds = self._estimate_leg(
                start=start,
                end=end,
                profile=request.profile,
            )
            legs.append(
                DirectionsLeg(
                    start=start,
                    end=end,
                    distance_meters=distance_meters,
                    duration_seconds=duration_seconds,
                )
            )
            total_distance += distance_meters
            total_duration += duration_seconds

        return DirectionsResult(
            provider=self.provider,
            profile=_normalize_required_text(request.profile, field_name="profile"),
            coordinates=request.coordinates,
            distance_meters=round(total_distance, 3),
            duration_seconds=round(total_duration, 3),
            geometry=self._build_geometry(request),
            legs=legs,
            depart_at=request.depart_at,
        )

    def _build_synthetic_catalog_entry(self, request: GeocodeRequest) -> FakeTransportRouteCatalogEntry:
        query_hash = hashlib.sha256(request.normalized_query.encode("utf-8")).digest()
        country_code = self._resolve_country_code(request)
        base_longitude, base_latitude = _FAKE_COUNTRY_ANCHORS.get(country_code, (0.0, 0.0))
        longitude_offset = ((int.from_bytes(query_hash[:2], "big") / 65535.0) - 0.5) * 0.18
        latitude_offset = ((int.from_bytes(query_hash[2:4], "big") / 65535.0) - 0.5) * 0.12
        coordinate = TransportRouteCoordinate(
            longitude=round(base_longitude + longitude_offset, 6),
            latitude=round(base_latitude + latitude_offset, 6),
            label=request.address,
        )
        return FakeTransportRouteCatalogEntry(
            formatted_address=f"{request.address}, {request.country_name} {request.zip_code}",
            coordinate=coordinate,
            confidence=0.84,
            provider_place_id=self._build_fake_place_id(request.normalized_query),
            country_code=country_code or request.country_code,
            country_name=request.country_name,
        )

    def _resolve_country_code(self, request: GeocodeRequest) -> str | None:
        if request.country_code:
            return request.country_code
        normalized_country_name = str(request.country_name).strip().lower()
        return _FAKE_COUNTRY_NAME_TO_CODE.get(normalized_country_name)

    def _estimate_leg(
        self,
        *,
        start: TransportRouteCoordinate,
        end: TransportRouteCoordinate,
        profile: str,
    ) -> tuple[float, float]:
        if start.as_pair() == end.as_pair():
            return 0.0, 0.0

        longitude_delta = abs(end.longitude - start.longitude)
        latitude_delta = abs(end.latitude - start.latitude)
        distance_meters = round((longitude_delta * 85_000.0) + (latitude_delta * 111_000.0) + 250.0, 3)
        if self._asymmetric_matrix:
            if end.longitude > start.longitude:
                distance_meters += 180.0
            elif end.longitude < start.longitude:
                distance_meters += 60.0
            if end.latitude > start.latitude:
                distance_meters += 120.0
            elif end.latitude < start.latitude:
                distance_meters += 40.0

        normalized_profile = _normalize_required_text(profile, field_name="profile").lower()
        speed_meters_per_second = 7.2 if normalized_profile.endswith("driving-traffic") else 9.8
        duration_seconds = round((distance_meters / speed_meters_per_second) + 45.0, 3)
        return round(distance_meters, 3), duration_seconds

    def _build_geometry(self, request: DirectionsRequest) -> dict[str, Any] | str:
        if request.geometry_format == "geojson":
            return {
                "type": "LineString",
                "coordinates": [list(coordinate.as_pair()) for coordinate in request.coordinates],
            }

        precision = 6 if request.geometry_format == "polyline6" else 5
        return ";".join(
            f"{coordinate.longitude:.{precision}f},{coordinate.latitude:.{precision}f}"
            for coordinate in request.coordinates
        )

    def _build_fake_place_id(self, normalized_query: str) -> str:
        digest = hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()[:16]
        return f"fake-place-{digest}"


def _normalize_transport_route_provider_name(value: str) -> str:
    normalized = _normalize_required_text(value, field_name="transport_ai_route_provider").lower()
    if normalized not in {"fake", "mapbox"}:
        raise ValueError(f"Unsupported transport route provider: {normalized}")
    return normalized


def _normalize_mapbox_profile(value: str) -> str:
    normalized = _normalize_required_text(value, field_name="profile").lower()
    if normalized.startswith("mapbox/"):
        return normalized
    return f"mapbox/{normalized}"


def _format_coordinate_path(coordinates: list[TransportRouteCoordinate]) -> str:
    return ";".join(f"{coordinate.longitude},{coordinate.latitude}" for coordinate in coordinates)


def _build_matrix_coordinate_payload(
    sources: list[TransportRouteCoordinate],
    destinations: list[TransportRouteCoordinate],
) -> tuple[list[TransportRouteCoordinate], list[int], list[int]]:
    coordinates = list(sources)
    source_indexes = list(range(len(sources)))
    index_by_pair: dict[tuple[float, float], int] = {}

    for index, coordinate in enumerate(coordinates):
        index_by_pair.setdefault(coordinate.as_pair(), index)

    destination_indexes: list[int] = []
    for coordinate in destinations:
        pair = coordinate.as_pair()
        index = index_by_pair.get(pair)
        if index is None:
            index = len(coordinates)
            coordinates.append(coordinate)
            index_by_pair[pair] = index
        destination_indexes.append(index)

    return coordinates, source_indexes, destination_indexes


def _iter_index_chunks(total_count: int, chunk_size: int):
    for start in range(0, total_count, chunk_size):
        yield list(range(start, min(start + chunk_size, total_count)))


def _get_mapbox_matrix_coordinate_limit(profile: str) -> int:
    normalized = _normalize_mapbox_profile(profile)
    if normalized == "mapbox/driving-traffic":
        return 10
    return 25


def _select_mapbox_matrix_chunk_sizes(
    *,
    source_count: int,
    destination_count: int,
    coordinate_limit: int,
) -> tuple[int, int]:
    if coordinate_limit < 2:
        raise ValueError("coordinate_limit must be at least 2")

    best_chunk_sizes: tuple[int, int] | None = None
    best_score: tuple[int, int, int] | None = None
    max_source_chunk_size = min(source_count, coordinate_limit - 1)

    for source_chunk_size in range(1, max_source_chunk_size + 1):
        destination_chunk_size = min(destination_count, coordinate_limit - source_chunk_size)
        if destination_chunk_size <= 0:
            continue
        tile_count = ceil(source_count / source_chunk_size) * ceil(destination_count / destination_chunk_size)
        score = (
            tile_count,
            -(source_chunk_size * destination_chunk_size),
            abs(source_chunk_size - destination_chunk_size),
        )
        if best_score is None or score < best_score:
            best_score = score
            best_chunk_sizes = (source_chunk_size, destination_chunk_size)

    if best_chunk_sizes is None:
        raise ValueError("unable to determine matrix chunk sizes")
    return best_chunk_sizes


def describe_transport_route_matrix_request_plan(
    *,
    provider_name: str,
    profile: str,
    source_count: int,
    destination_count: int,
) -> dict[str, int | None]:
    normalized_provider_name = _normalize_required_text(provider_name, field_name="provider_name").lower()
    if source_count <= 0 or destination_count <= 0:
        return {
            "matrix_request_count": 0,
            "matrix_chunk_count": 0,
            "source_chunk_size": None,
            "destination_chunk_size": None,
        }

    if normalized_provider_name != "mapbox":
        return {
            "matrix_request_count": 1,
            "matrix_chunk_count": 1,
            "source_chunk_size": source_count,
            "destination_chunk_size": destination_count,
        }

    coordinate_limit = _get_mapbox_matrix_coordinate_limit(profile)
    source_chunk_size, destination_chunk_size = _select_mapbox_matrix_chunk_sizes(
        source_count=source_count,
        destination_count=destination_count,
        coordinate_limit=coordinate_limit,
    )
    matrix_request_count = ceil(source_count / source_chunk_size) * ceil(destination_count / destination_chunk_size)
    return {
        "matrix_request_count": matrix_request_count,
        "matrix_chunk_count": matrix_request_count,
        "source_chunk_size": source_chunk_size,
        "destination_chunk_size": destination_chunk_size,
    }


class MapboxTransportRouteProvider(TransportRouteProvider):
    provider_name = "mapbox"

    def __init__(
        self,
        *,
        settings_obj: Settings = settings,
        client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings_obj
        self._client = client or httpx.Client(
            base_url="https://api.mapbox.com",
            timeout=float(settings_obj.mapbox_timeout_seconds),
        )
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def geocode(self, request: GeocodeRequest) -> GeocodeResult:
        query = ", ".join(part for part in [request.address, request.zip_code, request.country_name] if part)
        payload = self._request_json(
            operation="geocode",
            path=f"/geocoding/v5/mapbox.places/{quote(query, safe='')}.json",
            params={
                "limit": request.limit,
                "autocomplete": "false",
                "permanent": str(bool(self._settings.mapbox_geocoding_permanent)).lower(),
                "country_code": request.country_code,
                "language": request.language,
            },
        )
        features = payload.get("features")
        if not isinstance(features, list):
            raise TransportRouteProviderInvalidResponseError(
                "Mapbox geocode response did not include a features array.",
                provider=self.provider,
                operation="geocode",
            )
        if not features:
            raise TransportRouteProviderNoResultError(
                f"No geocode result for {request.normalized_query}",
                provider=self.provider,
                operation="geocode",
            )

        feature = features[0]
        if not isinstance(feature, dict):
            raise TransportRouteProviderInvalidResponseError(
                "Mapbox geocode response returned an invalid feature payload.",
                provider=self.provider,
                operation="geocode",
            )

        coordinate = self._parse_mapbox_coordinate(feature, operation="geocode")
        relevance = feature.get("relevance")
        confidence = float(relevance) if isinstance(relevance, int | float) else None
        formatted_address = feature.get("place_name") or feature.get("text") or query

        return GeocodeResult(
            provider=self.provider,
            query=request.normalized_query,
            formatted_address=str(formatted_address),
            coordinate=coordinate,
            confidence=confidence,
            provider_place_id=str(feature.get("id") or "") or None,
            country_code=request.country_code,
            country_name=request.country_name,
            raw_response_json=payload,
        )

    def get_matrix(self, request: MatrixRequest) -> MatrixResult:
        row_count = len(request.sources)
        column_count = len(request.destinations)
        durations_matrix: list[list[float | None]] = [
            [None for _ in range(column_count)] for _ in range(row_count)
        ]
        distances_matrix: list[list[float | None]] | None = None
        if "distance" in request.annotations:
            distances_matrix = [[None for _ in range(column_count)] for _ in range(row_count)]

        request_plan = describe_transport_route_matrix_request_plan(
            provider_name=self.provider,
            profile=request.profile,
            source_count=row_count,
            destination_count=column_count,
        )
        source_chunk_size = int(request_plan["source_chunk_size"] or row_count)
        destination_chunk_size = int(request_plan["destination_chunk_size"] or column_count)

        for source_indexes in _iter_index_chunks(row_count, source_chunk_size):
            for destination_indexes in _iter_index_chunks(column_count, destination_chunk_size):
                chunk_durations, chunk_distances = self._request_matrix_chunk(
                    request=request,
                    source_indexes=source_indexes,
                    destination_indexes=destination_indexes,
                )
                for local_row_index, global_row_index in enumerate(source_indexes):
                    for local_column_index, global_column_index in enumerate(destination_indexes):
                        durations_matrix[global_row_index][global_column_index] = chunk_durations[
                            local_row_index
                        ][local_column_index]
                        if distances_matrix is not None and chunk_distances is not None:
                            distances_matrix[global_row_index][global_column_index] = chunk_distances[
                                local_row_index
                            ][local_column_index]

        if any(value is None for row in durations_matrix for value in row):
            raise TransportRouteProviderInvalidResponseError(
                "Mapbox matrix response left gaps in the duration matrix.",
                provider=self.provider,
                operation="matrix",
            )
        if distances_matrix is not None and any(value is None for row in distances_matrix for value in row):
            raise TransportRouteProviderInvalidResponseError(
                "Mapbox matrix response left gaps in the distance matrix.",
                provider=self.provider,
                operation="matrix",
            )

        return MatrixResult(
            provider=self.provider,
            profile=_normalize_mapbox_profile(request.profile),
            sources=request.sources,
            destinations=request.destinations,
            durations_seconds=durations_matrix,
            distances_meters=distances_matrix,
            depart_at=request.depart_at,
            matrix_request_count=int(request_plan["matrix_request_count"] or 0),
            matrix_chunk_count=int(request_plan["matrix_chunk_count"] or 0),
            source_chunk_size=source_chunk_size,
            destination_chunk_size=destination_chunk_size,
        )

    def get_directions(self, request: DirectionsRequest) -> DirectionsResult:
        payload = self._request_json(
            operation="directions",
            path=(
                f"/directions/v5/{_normalize_mapbox_profile(request.profile)}"
                f"/{_format_coordinate_path(request.coordinates)}"
            ),
            params={
                "geometries": request.geometry_format,
                "overview": "full",
                "steps": str(request.include_steps).lower(),
                **(
                    {"depart_at": request.depart_at.isoformat()}
                    if request.depart_at is not None
                    else {}
                ),
            },
        )
        code = str(payload.get("code") or "")
        if code == "NoRoute":
            raise TransportRouteProviderNoRouteError(
                "Mapbox did not return a route for the requested directions.",
                provider=self.provider,
                operation="directions",
            )
        if code not in {"", "Ok"}:
            raise TransportRouteProviderInvalidResponseError(
                f"Mapbox directions request failed with code {code}.",
                provider=self.provider,
                operation="directions",
            )

        routes = payload.get("routes")
        if not isinstance(routes, list) or not routes:
            raise TransportRouteProviderNoRouteError(
                "Mapbox did not return a route for the requested directions.",
                provider=self.provider,
                operation="directions",
            )

        route = routes[0]
        if not isinstance(route, dict):
            raise TransportRouteProviderInvalidResponseError(
                "Mapbox directions response returned an invalid route payload.",
                provider=self.provider,
                operation="directions",
            )

        distance_meters = self._coerce_non_negative_float(
            route.get("distance"),
            operation="directions",
            field_name="distance",
        )
        duration_seconds = self._coerce_non_negative_float(
            route.get("duration"),
            operation="directions",
            field_name="duration",
        )
        raw_legs = route.get("legs")
        if not isinstance(raw_legs, list) or len(raw_legs) != len(request.coordinates) - 1:
            raise TransportRouteProviderInvalidResponseError(
                "Mapbox directions response returned an unexpected legs payload.",
                provider=self.provider,
                operation="directions",
            )

        legs: list[DirectionsLeg] = []
        for index, raw_leg in enumerate(raw_legs):
            if not isinstance(raw_leg, dict):
                raise TransportRouteProviderInvalidResponseError(
                    "Mapbox directions response returned an invalid leg payload.",
                    provider=self.provider,
                    operation="directions",
                )
            legs.append(
                DirectionsLeg(
                    start=request.coordinates[index],
                    end=request.coordinates[index + 1],
                    distance_meters=self._coerce_non_negative_float(
                        raw_leg.get("distance"),
                        operation="directions",
                        field_name="leg.distance",
                    ),
                    duration_seconds=self._coerce_non_negative_float(
                        raw_leg.get("duration"),
                        operation="directions",
                        field_name="leg.duration",
                    ),
                )
            )

        return DirectionsResult(
            provider=self.provider,
            profile=_normalize_mapbox_profile(request.profile),
            coordinates=request.coordinates,
            distance_meters=distance_meters,
            duration_seconds=duration_seconds,
            geometry=route.get("geometry"),
            legs=legs,
            depart_at=request.depart_at,
        )

    def _request_matrix_chunk(
        self,
        *,
        request: MatrixRequest,
        source_indexes: list[int],
        destination_indexes: list[int],
    ) -> tuple[list[list[float]], list[list[float]] | None]:
        sources = [request.sources[index] for index in source_indexes]
        destinations = [request.destinations[index] for index in destination_indexes]
        coordinates, request_source_indexes, request_destination_indexes = _build_matrix_coordinate_payload(
            sources,
            destinations,
        )
        payload = self._request_json(
            operation="matrix",
            path=(
                f"/directions-matrix/v1/{_normalize_mapbox_profile(request.profile)}"
                f"/{_format_coordinate_path(coordinates)}"
            ),
            params={
                "annotations": ",".join(request.annotations),
                "sources": ";".join(str(index) for index in request_source_indexes),
                "destinations": ";".join(str(index) for index in request_destination_indexes),
                **(
                    {"depart_at": request.depart_at.isoformat()}
                    if request.depart_at is not None
                    else {}
                ),
            },
        )
        code = str(payload.get("code") or "")
        if code == "NoRoute":
            raise TransportRouteProviderNoRouteError(
                "Mapbox did not return a route matrix for the requested coordinates.",
                provider=self.provider,
                operation="matrix",
            )
        if code not in {"", "Ok"}:
            raise TransportRouteProviderInvalidResponseError(
                f"Mapbox matrix request failed with code {code}.",
                provider=self.provider,
                operation="matrix",
            )

        durations = self._parse_matrix_values(
            payload.get("durations"),
            row_count=len(sources),
            column_count=len(destinations),
            field_name="durations",
        )
        distances: list[list[float]] | None = None
        if "distance" in request.annotations:
            distances = self._parse_matrix_values(
                payload.get("distances"),
                row_count=len(sources),
                column_count=len(destinations),
                field_name="distances",
            )
        return durations, distances

    def _request_json(
        self,
        *,
        operation: Literal["geocode", "matrix", "directions"],
        path: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        token = self._get_access_token(operation=operation)
        request_params = dict(params)
        if operation == "geocode":
            country_code = _normalize_optional_text(request_params.pop("country_code", None))
            language = _normalize_optional_text(request_params.pop("language", None))
            if country_code:
                request_params["country"] = country_code.lower()
            if language:
                request_params["language"] = language.lower()
        request_params["access_token"] = token

        attempt_count = max(1, int(self._settings.mapbox_max_retries) + 1)
        last_retryable_status_code: int | None = None
        for attempt in range(1, attempt_count + 1):
            try:
                response = self._client.get(
                    path,
                    params=request_params,
                    headers={"Accept": "application/json"},
                )
            except httpx.TimeoutException as exc:
                if attempt < attempt_count:
                    continue
                raise TransportRouteProviderTimeoutError(
                    (
                        f"Mapbox {operation} request timed out after "
                        f"{self._settings.mapbox_timeout_seconds} seconds."
                    ),
                    provider=self.provider,
                    operation=operation,
                ) from exc
            except httpx.TransportError as exc:
                if attempt < attempt_count:
                    continue
                raise TransportRouteProviderInvalidResponseError(
                    f"Mapbox {operation} request failed before a response was received.",
                    provider=self.provider,
                    operation=operation,
                ) from exc

            if response.status_code in {401, 403}:
                raise TransportRouteProviderAuthError(
                    "Mapbox rejected the configured access token.",
                    provider=self.provider,
                    operation=operation,
                    status_code=response.status_code,
                )
            if response.status_code == 429 or response.status_code >= 500:
                last_retryable_status_code = response.status_code
                if attempt < attempt_count:
                    continue
            if response.status_code >= 400:
                raise TransportRouteProviderInvalidResponseError(
                    f"Mapbox {operation} request failed with status {response.status_code}.",
                    provider=self.provider,
                    operation=operation,
                    status_code=response.status_code,
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise TransportRouteProviderInvalidResponseError(
                    f"Mapbox {operation} response was not valid JSON.",
                    provider=self.provider,
                    operation=operation,
                    status_code=response.status_code,
                ) from exc
            if not isinstance(payload, dict):
                raise TransportRouteProviderInvalidResponseError(
                    f"Mapbox {operation} response must be a JSON object.",
                    provider=self.provider,
                    operation=operation,
                    status_code=response.status_code,
                )
            return payload

        raise TransportRouteProviderInvalidResponseError(
            f"Mapbox {operation} request failed after retry exhaustion.",
            provider=self.provider,
            operation=operation,
            status_code=last_retryable_status_code,
        )

    def _get_access_token(
        self,
        *,
        operation: Literal["geocode", "matrix", "directions"],
    ) -> str:
        token = str(self._settings.mapbox_access_token or "").strip()
        if not token:
            raise TransportRouteProviderAuthError(
                "The Mapbox access token is not configured.",
                provider=self.provider,
                operation=operation,
            )
        return token

    def _parse_mapbox_coordinate(
        self,
        feature: dict[str, Any],
        *,
        operation: Literal["geocode", "matrix", "directions"],
    ) -> TransportRouteCoordinate:
        center = feature.get("center")
        if not (isinstance(center, list) and len(center) >= 2):
            geometry = feature.get("geometry")
            center = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if not (isinstance(center, list) and len(center) >= 2):
            raise TransportRouteProviderInvalidResponseError(
                "Mapbox geocode response did not include valid coordinates.",
                provider=self.provider,
                operation=operation,
            )
        longitude = center[0]
        latitude = center[1]
        if not isinstance(longitude, int | float) or not isinstance(latitude, int | float):
            raise TransportRouteProviderInvalidResponseError(
                "Mapbox geocode response did not include numeric coordinates.",
                provider=self.provider,
                operation=operation,
            )

        return TransportRouteCoordinate(
            longitude=float(longitude),
            latitude=float(latitude),
            label=_normalize_optional_text(feature.get("text") or feature.get("place_name")),
        )

    def _parse_matrix_values(
        self,
        raw_matrix: Any,
        *,
        row_count: int,
        column_count: int,
        field_name: str,
    ) -> list[list[float]]:
        if not isinstance(raw_matrix, list) or len(raw_matrix) != row_count:
            raise TransportRouteProviderInvalidResponseError(
                f"Mapbox matrix response returned an invalid {field_name} payload.",
                provider=self.provider,
                operation="matrix",
            )

        parsed_matrix: list[list[float]] = []
        for row_index, raw_row in enumerate(raw_matrix):
            if not isinstance(raw_row, list) or len(raw_row) != column_count:
                raise TransportRouteProviderInvalidResponseError(
                    f"Mapbox matrix response returned an invalid {field_name} row.",
                    provider=self.provider,
                    operation="matrix",
                )
            parsed_row: list[float] = []
            for column_index, value in enumerate(raw_row):
                if value is None:
                    raise TransportRouteProviderNoRouteError(
                        (
                            "Mapbox matrix returned an unroutable cell at "
                            f"source {row_index} and destination {column_index}."
                        ),
                        provider=self.provider,
                        operation="matrix",
                    )
                if not isinstance(value, int | float):
                    raise TransportRouteProviderInvalidResponseError(
                        f"Mapbox matrix response returned a non-numeric {field_name} value.",
                        provider=self.provider,
                        operation="matrix",
                    )
                parsed_row.append(float(value))
            parsed_matrix.append(parsed_row)
        return parsed_matrix

    def _coerce_non_negative_float(
        self,
        value: Any,
        *,
        operation: Literal["geocode", "matrix", "directions"],
        field_name: str,
    ) -> float:
        if not isinstance(value, int | float) or float(value) < 0:
            raise TransportRouteProviderInvalidResponseError(
                f"Mapbox {operation} response returned an invalid {field_name} value.",
                provider=self.provider,
                operation=operation,
            )
        return float(value)


def build_transport_route_provider(
    *,
    settings_obj: Settings = settings,
    client: httpx.Client | None = None,
    fake_catalog: dict[str, FakeTransportRouteCatalogEntry] | None = None,
    allow_synthetic_geocode: bool = True,
) -> TransportRouteProvider:
    provider_name = _normalize_transport_route_provider_name(settings_obj.transport_ai_route_provider)
    if provider_name == "fake":
        return FakeTransportRouteProvider(
            settings_obj=settings_obj,
            catalog=fake_catalog,
            allow_synthetic_geocode=allow_synthetic_geocode,
        )
    return MapboxTransportRouteProvider(settings_obj=settings_obj, client=client)
