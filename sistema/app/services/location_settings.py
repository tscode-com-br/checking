from sqlalchemy.orm import Session

from ..models import MobileAppSettings
from .time_utils import now_sgt


DEFAULT_LOCATION_UPDATE_INTERVAL_SECONDS = 60
DEFAULT_LOCATION_ACCURACY_THRESHOLD_METERS = 30
def _get_or_create_mobile_app_settings(db: Session) -> MobileAppSettings:
    settings = db.get(MobileAppSettings, 1)
    timestamp = now_sgt()

    if settings is None:
        settings = MobileAppSettings(
            id=1,
            location_update_interval_seconds=DEFAULT_LOCATION_UPDATE_INTERVAL_SECONDS,
            location_accuracy_threshold_meters=DEFAULT_LOCATION_ACCURACY_THRESHOLD_METERS,
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