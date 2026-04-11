from sqlalchemy.orm import Session

from ..models import MobileAppSettings
from .time_utils import now_sgt


DEFAULT_LOCATION_UPDATE_INTERVAL_SECONDS = 60
DEFAULT_LOCATION_ACCURACY_THRESHOLD_METERS = 30


def get_location_update_interval_seconds(db: Session) -> int:
    settings = db.get(MobileAppSettings, 1)
    if settings is None:
        return DEFAULT_LOCATION_UPDATE_INTERVAL_SECONDS
    return settings.location_update_interval_seconds


def get_location_accuracy_threshold_meters(db: Session) -> int:
    settings = db.get(MobileAppSettings, 1)
    if settings is None:
        return DEFAULT_LOCATION_ACCURACY_THRESHOLD_METERS
    return settings.location_accuracy_threshold_meters


def upsert_location_update_interval_seconds(db: Session, *, seconds: int) -> MobileAppSettings:
    return upsert_location_settings(
        db,
        seconds=seconds,
        accuracy_threshold_meters=get_location_accuracy_threshold_meters(db),
    )


def upsert_location_settings(
    db: Session,
    *,
    seconds: int,
    accuracy_threshold_meters: int,
) -> MobileAppSettings:
    settings = db.get(MobileAppSettings, 1)
    timestamp = now_sgt()

    if settings is None:
        settings = MobileAppSettings(
            id=1,
            location_update_interval_seconds=seconds,
            location_accuracy_threshold_meters=accuracy_threshold_meters,
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(settings)
        db.flush()
        return settings

    settings.location_update_interval_seconds = seconds
    settings.location_accuracy_threshold_meters = accuracy_threshold_meters
    settings.updated_at = timestamp
    db.flush()
    return settings