from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import MobileAppSettings, TransportDailySetting
from .time_utils import now_sgt


DEFAULT_LOCATION_UPDATE_INTERVAL_SECONDS = 60
DEFAULT_LOCATION_ACCURACY_THRESHOLD_METERS = 30
DEFAULT_TRANSPORT_WORK_TO_HOME_TIME = "16:45"
DEFAULT_TRANSPORT_LAST_UPDATE_TIME = "16:00"


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