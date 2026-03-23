from datetime import datetime
from zoneinfo import ZoneInfo

from ..core.config import settings


def now_sgt() -> datetime:
    return datetime.now(tz=ZoneInfo(settings.tz_name))


def format_sgt(dt: datetime) -> str:
    local_dt = dt.astimezone(ZoneInfo(settings.tz_name))
    return local_dt.strftime("%Y-%m-%d-%H-%M-%S")
