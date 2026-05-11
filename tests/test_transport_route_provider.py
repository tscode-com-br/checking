from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from sistema.app.core.config import Settings
from sistema.app.services.transport_route_provider import (
    DEFAULT_FAKE_TRANSPORT_ROUTE_CATALOG,
    DirectionsLeg,
    DirectionsRequest,
    DirectionsResult,
    FakeTransportRouteProvider,
    GeocodeRequest,
    GeocodeResult,
    MatrixRequest,
    MatrixResult,
    TransportRouteCoordinate,
    TransportRouteProvider,
    TransportRouteProviderAuthError,
    TransportRouteProviderInvalidResponseError,
    TransportRouteProviderNoResultError,
    TransportRouteProviderNoRouteError,
    TransportRouteProviderTimeoutError,
    build_transport_route_provider,
)

def test_transport_route_provider_contract_with_fake_provider():
    provider = FakeTransportRouteProvider()
    departure_time = datetime(2026, 5, 6, 6, 50, tzinfo=ZoneInfo("Asia/Singapore"))
    geocode_request = GeocodeRequest(
        address="10 Bayfront Avenue",
        zip_code="018956",
        country_name="Singapore",
        country_code="sg",
    )
    geocode_result = provider.geocode(geocode_request)
    matrix_request = MatrixRequest(
        profile="here/car-fast",
        sources=[geocode_result.coordinate],
        destinations=[TransportRouteCoordinate(longitude=103.8519, latitude=1.2903, label="Project")],
        depart_at=departure_time,
    )
    matrix_result = provider.get_matrix(matrix_request)
    directions_result = provider.get_directions(
        DirectionsRequest(
            profile="here/car-fast",
            coordinates=[*matrix_request.sources, *matrix_request.destinations],
            depart_at=departure_time,
        )
    )

    assert isinstance(provider, TransportRouteProvider)
    assert geocode_result.provider == "fake"
    assert geocode_result.longitude == 103.8607
    assert matrix_result.provider == "fake"
    assert matrix_result.durations_seconds == [[289.986]]
    assert matrix_result.distances_meters == [[1763.9]]
    assert matrix_result.matrix_request_count == 1
    assert matrix_result.matrix_chunk_count == 1
    assert directions_result.provider == "fake"
    assert directions_result.legs[0].duration_seconds == 289.986


def test_transport_route_provider_dtos_serialize_and_validate_nested_payloads():
    departure_time = datetime(2026, 5, 6, 6, 50, tzinfo=ZoneInfo("Asia/Singapore"))
    origin = TransportRouteCoordinate(longitude=103.8607, latitude=1.2834, label="Passenger A")
    destination = TransportRouteCoordinate(longitude=103.8519, latitude=1.2903, label="Project")
    matrix_request = MatrixRequest(
        profile="here/car-fast",
        sources=[origin],
        destinations=[destination],
        depart_at=departure_time,
    )
    directions_result = DirectionsResult(
        provider="fake",
        profile="here/car-fast",
        coordinates=[origin, destination],
        distance_meters=1200.0,
        duration_seconds=300.0,
        geometry={"type": "LineString", "coordinates": [[103.8607, 1.2834], [103.8519, 1.2903]]},
        legs=[
            DirectionsLeg(
                start=origin,
                end=destination,
                distance_meters=1200.0,
                duration_seconds=300.0,
            )
        ],
        depart_at=departure_time,
    )

    serialized_request = matrix_request.model_dump(mode="json")
    serialized_directions = directions_result.model_dump(mode="json")
    round_tripped_request = MatrixRequest.model_validate(serialized_request)
    round_tripped_directions = DirectionsResult.model_validate(serialized_directions)

    assert serialized_request["depart_at"] == departure_time.isoformat()
    assert serialized_request["sources"][0]["longitude"] == 103.8607
    assert serialized_directions["legs"][0]["distance_meters"] == 1200.0
    assert round_tripped_request.destinations[0].label == "Project"
    assert round_tripped_directions.coordinates[1].latitude == 1.2903


def test_transport_route_provider_raises_typed_error_for_geocode_without_result():
    provider = FakeTransportRouteProvider(allow_synthetic_geocode=False)

    with pytest.raises(TransportRouteProviderNoResultError) as exc_info:
        provider.geocode(
            GeocodeRequest(
                address="99 Unknown Test Avenue",
                zip_code="999999",
                country_name="Singapore",
            )
        )

    assert exc_info.value.provider == "fake"
    assert exc_info.value.operation == "geocode"
    assert "99 unknown test avenue, 999999, singapore" in str(exc_info.value)


def test_fake_transport_route_provider_returns_same_coordinate_for_same_address():
    provider = FakeTransportRouteProvider()
    request = GeocodeRequest(
        address="42 Custom Test Road",
        zip_code="543210",
        country_name="Singapore",
        country_code="SG",
    )

    first_result = provider.geocode(request)
    second_result = provider.geocode(request)

    assert first_result.provider == "fake"
    assert first_result.coordinate == second_result.coordinate
    assert first_result.formatted_address == "42 Custom Test Road, Singapore 543210"


def test_fake_transport_route_provider_matrix_and_directions_match_expected_values():
    provider = FakeTransportRouteProvider()
    origin = TransportRouteCoordinate(longitude=100.0, latitude=1.0, label="Origin")
    destination = TransportRouteCoordinate(longitude=100.01, latitude=1.02, label="Destination")

    matrix_result = provider.get_matrix(
        MatrixRequest(
            profile="here/car-fast",
            sources=[origin, destination],
            destinations=[origin, destination],
        )
    )
    directions_result = provider.get_directions(
        DirectionsRequest(
            profile="here/car-fast",
            coordinates=[origin, destination],
        )
    )

    assert matrix_result.durations_seconds == [[0.0, 506.111], [506.111, 0.0]]
    assert matrix_result.distances_meters == [[0.0, 3320.0], [3320.0, 0.0]]
    assert directions_result.distance_meters == pytest.approx(3320.0)
    assert directions_result.duration_seconds == pytest.approx(506.111)
    assert directions_result.legs[0].distance_meters == pytest.approx(3320.0)
    assert directions_result.geometry == {
        "type": "LineString",
        "coordinates": [[100.0, 1.0], [100.01, 1.02]],
    }


def test_build_transport_route_provider_can_enable_asymmetric_fake_provider_by_config():
    provider = build_transport_route_provider(
        settings_obj=Settings(
            transport_ai_route_provider="fake",
            transport_ai_fake_matrix_asymmetric=True,
        )
    )
    origin = TransportRouteCoordinate(longitude=100.0, latitude=1.0, label="Origin")
    destination = TransportRouteCoordinate(longitude=100.01, latitude=1.02, label="Destination")

    matrix_result = provider.get_matrix(
        MatrixRequest(
            profile="here/car-fast",
            sources=[origin, destination],
            destinations=[origin, destination],
        )
    )

    assert isinstance(provider, FakeTransportRouteProvider)
    assert matrix_result.distances_meters == [[0.0, 3620.0], [3420.0, 0.0]]
    assert matrix_result.durations_seconds == [[0.0, 547.778], [520.0, 0.0]]


def test_fake_transport_route_provider_exposes_catalog_entries_for_fixture_addresses():
    provider = FakeTransportRouteProvider(catalog=DEFAULT_FAKE_TRANSPORT_ROUTE_CATALOG)

    result = provider.geocode(
        GeocodeRequest(
            address="1 Marina Boulevard",
            zip_code="018989",
            country_name="Singapore",
        )
    )

    assert result.provider_place_id == "fake-place-1-marina-boulevard"
    assert result.longitude == pytest.approx(103.8545)
    assert result.latitude == pytest.approx(1.2825)
