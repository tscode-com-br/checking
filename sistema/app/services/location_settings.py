from sqlalchemy.orm import Session

from ..models import MobileAppSettings
from .time_utils import now_sgt


DEFAULT_LOCATION_UPDATE_INTERVAL_SECONDS = 60


def get_location_update_interval_seconds(db: Session) -> int:
    settings = db.get(MobileAppSettings, 1)
    if settings is None:
        return DEFAULT_LOCATION_UPDATE_INTERVAL_SECONDS
    return settings.location_update_interval_seconds


def upsert_location_update_interval_seconds(db: Session, *, seconds: int) -> MobileAppSettings:
    settings = db.get(MobileAppSettings, 1)
    timestamp = now_sgt()

    if settings is None:
        settings = MobileAppSettings(
            id=1,
            location_update_interval_seconds=seconds,
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(settings)
        db.flush()
        return settings

    settings.location_update_interval_seconds = seconds
    settings.updated_at = timestamp
    db.flush()
    return settings