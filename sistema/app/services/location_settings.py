from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import MobileAppSettings, ProjectAutoCheckoutDistance, TransportDailySetting
from .project_catalog import list_project_names, normalize_project_name
from .time_utils import now_sgt


DEFAULT_LOCATION_UPDATE_INTERVAL_SECONDS = 60
DEFAULT_LOCATION_ACCURACY_THRESHOLD_METERS = 30
DEFAULT_MINIMUM_CHECKOUT_DISTANCE_METERS = 2000
DEFAULT_TRANSPORT_WORK_TO_HOME_TIME = "16:45"
DEFAULT_TRANSPORT_LAST_UPDATE_TIME = "16:00"
DEFAULT_TRANSPORT_DEFAULT_CAR_SEATS = 3
DEFAULT_TRANSPORT_DEFAULT_MINIVAN_SEATS = 6
DEFAULT_TRANSPORT_DEFAULT_VAN_SEATS = 10
DEFAULT_TRANSPORT_DEFAULT_BUS_SEATS = 40
DEFAULT_TRANSPORT_DEFAULT_TOLERANCE_MINUTES = 5


@dataclass(frozen=True)
class ProjectMinimumCheckoutDistanceRow:
    project_name: str
    minimum_checkout_distance_meters: int


def _get_or_create_mobile_app_settings(db: Session) -> MobileAppSettings:
    settings = db.get(MobileAppSettings, 1)
    timestamp = now_sgt()

    if settings is None:
        settings = MobileAppSettings(
            id=1,
            location_update_interval_seconds=DEFAULT_LOCATION_UPDATE_INTERVAL_SECONDS,
            location_accuracy_threshold_meters=DEFAULT_LOCATION_ACCURACY_THRESHOLD_METERS,
            transport_work_to_home_time=DEFAULT_TRANSPORT_WORK_TO_HOME_TIME,
            transport_last_update_time=DEFAULT_TRANSPORT_LAST_UPDATE_TIME,
            transport_default_car_seats=DEFAULT_TRANSPORT_DEFAULT_CAR_SEATS,
            transport_default_minivan_seats=DEFAULT_TRANSPORT_DEFAULT_MINIVAN_SEATS,
            transport_default_van_seats=DEFAULT_TRANSPORT_DEFAULT_VAN_SEATS,
            transport_default_bus_seats=DEFAULT_TRANSPORT_DEFAULT_BUS_SEATS,
            transport_default_tolerance_minutes=DEFAULT_TRANSPORT_DEFAULT_TOLERANCE_MINUTES,
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(settings)
        db.flush()
        return settings

    return settings


def get_location_accuracy_threshold_meters(db: Session) -> int:
    settings = db.get(MobileAppSettings, 1)
    if settings is None:
        return DEFAULT_LOCATION_ACCURACY_THRESHOLD_METERS
    return settings.location_accuracy_threshold_meters


def get_minimum_checkout_distance_meters_for_project(
    db: Session,
    project_name: str | None,
) -> int:
    if not project_name:
        return DEFAULT_MINIMUM_CHECKOUT_DISTANCE_METERS

    try:
        normalized_project_name = normalize_project_name(project_name)
    except ValueError:
        return DEFAULT_MINIMUM_CHECKOUT_DISTANCE_METERS

    configured_distance = db.execute(
        select(ProjectAutoCheckoutDistance).where(
            ProjectAutoCheckoutDistance.project_name == normalized_project_name
        )
    ).scalar_one_or_none()
    if configured_distance is None:
        return DEFAULT_MINIMUM_CHECKOUT_DISTANCE_METERS

    return configured_distance.minimum_checkout_distance_meters


def list_project_minimum_checkout_distance_rows(db: Session) -> list[ProjectMinimumCheckoutDistanceRow]:
    project_names = list_project_names(db)
    if not project_names:
        return []

    configured_distances = {
        row.project_name: row.minimum_checkout_distance_meters
        for row in db.execute(
            select(ProjectAutoCheckoutDistance).order_by(ProjectAutoCheckoutDistance.project_name)
        ).scalars().all()
    }
    return [
        ProjectMinimumCheckoutDistanceRow(
            project_name=project_name,
            minimum_checkout_distance_meters=configured_distances.get(
                project_name,
                DEFAULT_MINIMUM_CHECKOUT_DISTANCE_METERS,
            ),
        )
        for project_name in project_names
    ]


def upsert_project_minimum_checkout_distance_rows(
    db: Session,
    items: Sequence[tuple[str, int]],
) -> list[ProjectAutoCheckoutDistance]:
    if not items:
        return []

    timestamp = now_sgt()
    project_names = [project_name for project_name, _distance in items]
    existing_rows = {
        row.project_name: row
        for row in db.execute(
            select(ProjectAutoCheckoutDistance).where(
                ProjectAutoCheckoutDistance.project_name.in_(project_names)
            )
        ).scalars().all()
    }
    persisted_rows: list[ProjectAutoCheckoutDistance] = []

    for project_name, minimum_checkout_distance_meters in items:
        existing_row = existing_rows.get(project_name)
        if existing_row is None:
            existing_row = ProjectAutoCheckoutDistance(
                project_name=project_name,
                minimum_checkout_distance_meters=minimum_checkout_distance_meters,
                created_at=timestamp,
                updated_at=timestamp,
            )
            db.add(existing_row)
            existing_rows[project_name] = existing_row
        else:
            existing_row.minimum_checkout_distance_meters = minimum_checkout_distance_meters
            existing_row.updated_at = timestamp

        persisted_rows.append(existing_row)

    db.flush()
    return persisted_rows


def get_transport_work_to_home_time(db: Session) -> str:
    settings = db.get(MobileAppSettings, 1)
    if settings is None or not settings.transport_work_to_home_time:
        return DEFAULT_TRANSPORT_WORK_TO_HOME_TIME
    return settings.transport_work_to_home_time


def get_transport_last_update_time(db: Session) -> str:
    settings = db.get(MobileAppSettings, 1)
    if settings is None or not settings.transport_last_update_time:
        return DEFAULT_TRANSPORT_LAST_UPDATE_TIME
    return settings.transport_last_update_time


def get_transport_vehicle_default_seat_counts(db: Session) -> dict[str, int]:
    settings = db.get(MobileAppSettings, 1)
    if settings is None:
        return {
            "default_car_seats": DEFAULT_TRANSPORT_DEFAULT_CAR_SEATS,
            "default_minivan_seats": DEFAULT_TRANSPORT_DEFAULT_MINIVAN_SEATS,
            "default_van_seats": DEFAULT_TRANSPORT_DEFAULT_VAN_SEATS,
            "default_bus_seats": DEFAULT_TRANSPORT_DEFAULT_BUS_SEATS,
            "default_tolerance_minutes": DEFAULT_TRANSPORT_DEFAULT_TOLERANCE_MINUTES,
        }

    return {
        "default_car_seats": settings.transport_default_car_seats or DEFAULT_TRANSPORT_DEFAULT_CAR_SEATS,
        "default_minivan_seats": settings.transport_default_minivan_seats or DEFAULT_TRANSPORT_DEFAULT_MINIVAN_SEATS,
        "default_van_seats": settings.transport_default_van_seats or DEFAULT_TRANSPORT_DEFAULT_VAN_SEATS,
        "default_bus_seats": settings.transport_default_bus_seats or DEFAULT_TRANSPORT_DEFAULT_BUS_SEATS,
        "default_tolerance_minutes": (
            settings.transport_default_tolerance_minutes
            if settings.transport_default_tolerance_minutes is not None
            else DEFAULT_TRANSPORT_DEFAULT_TOLERANCE_MINUTES
        ),
    }


def get_transport_work_to_home_time_for_date(
    db: Session,
    *,
    service_date: date,
) -> str:
    daily_setting = db.execute(
        select(TransportDailySetting).where(TransportDailySetting.service_date == service_date)
    ).scalar_one_or_none()
    if daily_setting is not None and daily_setting.work_to_home_time:
        return daily_setting.work_to_home_time
    return get_transport_work_to_home_time(db)


def upsert_location_settings(
    db: Session,
    *,
    accuracy_threshold_meters: int,
) -> MobileAppSettings:
    settings = _get_or_create_mobile_app_settings(db)
    timestamp = now_sgt()

    settings.location_accuracy_threshold_meters = accuracy_threshold_meters
    settings.updated_at = timestamp
    db.flush()
    return settings


def upsert_transport_work_to_home_time(
    db: Session,
    *,
    work_to_home_time: str,
) -> MobileAppSettings:
    settings = _get_or_create_mobile_app_settings(db)
    timestamp = now_sgt()

    settings.transport_work_to_home_time = work_to_home_time
    settings.updated_at = timestamp
    db.flush()
    return settings


def upsert_transport_last_update_time(
    db: Session,
    *,
    last_update_time: str,
) -> MobileAppSettings:
    settings = _get_or_create_mobile_app_settings(db)
    timestamp = now_sgt()

    settings.transport_last_update_time = last_update_time
    settings.updated_at = timestamp
    db.flush()
    return settings


def upsert_transport_vehicle_default_seat_counts(
    db: Session,
    *,
    default_car_seats: int,
    default_minivan_seats: int,
    default_van_seats: int,
    default_bus_seats: int,
    default_tolerance_minutes: int,
) -> MobileAppSettings:
    settings = _get_or_create_mobile_app_settings(db)
    timestamp = now_sgt()

    settings.transport_default_car_seats = default_car_seats
    settings.transport_default_minivan_seats = default_minivan_seats
    settings.transport_default_van_seats = default_van_seats
    settings.transport_default_bus_seats = default_bus_seats
    settings.transport_default_tolerance_minutes = default_tolerance_minutes
    settings.updated_at = timestamp
    db.flush()
    return settings


def upsert_transport_work_to_home_time_for_date(
    db: Session,
    *,
    service_date: date,
    work_to_home_time: str,
) -> TransportDailySetting:
    timestamp = now_sgt()
    daily_setting = db.execute(
        select(TransportDailySetting).where(TransportDailySetting.service_date == service_date)
    ).scalar_one_or_none()

    if daily_setting is None:
        daily_setting = TransportDailySetting(
            service_date=service_date,
            work_to_home_time=work_to_home_time,
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(daily_setting)
        db.flush()
        return daily_setting

    daily_setting.work_to_home_time = work_to_home_time
    daily_setting.updated_at = timestamp
    db.flush()
    return daily_setting