import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..models import MobileAppSettings
from .time_utils import now_sgt


DEFAULT_LOCATION_UPDATE_INTERVAL_SECONDS = 60
DEFAULT_LOCATION_ACCURACY_THRESHOLD_METERS = 30
COORDINATE_UPDATE_FREQUENCY_DAY_LABELS = [
    "Segunda-Feira",
    "Terça-Feira",
    "Quarta-Feira",
    "Quinta-Feira",
    "Sexta-Feira",
    "Sábado",
    "Domingo",
]
COORDINATE_UPDATE_FREQUENCY_PERIOD_VALUES = [
    ("00:01 a 01:00", 3600),
    ("01:01 a 02:00", 3600),
    ("02:01 a 03:00", 3600),
    ("03:01 a 04:00", 3600),
    ("04:01 a 05:00", 3600),
    ("05:01 a 06:00", 3600),
    ("06:01 a 07:00", 3600),
    ("07:01 a 08:00", 180),
    ("08:01 a 09:00", 240),
    ("09:01 a 10:00", 240),
    ("10:01 a 11:00", 240),
    ("11:01 a 12:00", 240),
    ("12:01 a 13:00", 360),
    ("13:01 a 14:00", 240),
    ("14:01 a 15:00", 240),
    ("15:01 a 16:00", 240),
    ("16:01 a 17:00", 180),
    ("17:01 a 18:00", 180),
    ("18:01 a 19:00", 240),
    ("19:01 a 20:00", 240),
    ("20:01 a 21:00", 240),
    ("21:01 a 22:00", 240),
    ("22:01 a 23:00", 480),
    ("23:01 a 00:00", 1800),
]


def _build_default_coordinate_update_frequency_table() -> dict[str, dict[str, int]]:
    return {
        period: {day_label: seconds for day_label in COORDINATE_UPDATE_FREQUENCY_DAY_LABELS}
        for period, seconds in COORDINATE_UPDATE_FREQUENCY_PERIOD_VALUES
    }


def _serialize_coordinate_update_frequency_table(table: dict[str, dict[str, int]]) -> str:
    return json.dumps(table, ensure_ascii=False, separators=(",", ":"))


def _weekday_to_day_label(weekday_index: int) -> str:
    return COORDINATE_UPDATE_FREQUENCY_DAY_LABELS[weekday_index]


def resolve_coordinate_update_frequency_slot(at: datetime | None = None) -> tuple[str, str]:
    reference = at if at is not None else now_sgt()

    if reference.hour == 0 and reference.minute == 0:
        previous_reference = reference - timedelta(days=1)
        return _weekday_to_day_label(previous_reference.weekday()), "23:01 a 00:00"

    day_label = _weekday_to_day_label(reference.weekday())
    period_start_hour = reference.hour if reference.minute >= 1 else (reference.hour - 1) % 24
    period_end_hour = (period_start_hour + 1) % 24
    return day_label, f"{period_start_hour:02d}:01 a {period_end_hour:02d}:00"


def _coerce_frequency_value(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 1 <= value <= 86400 else None
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if 1 <= parsed <= 86400 else None
    return None


def _parse_coordinate_update_frequency_table(raw: str | None) -> dict[str, dict[str, int]]:
    table = _build_default_coordinate_update_frequency_table()
    if not raw:
        return table

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return table

    if not isinstance(payload, dict):
        return table

    for period, _default_seconds in COORDINATE_UPDATE_FREQUENCY_PERIOD_VALUES:
        stored_row = payload.get(period)
        if not isinstance(stored_row, dict):
            continue
        for day_label in COORDINATE_UPDATE_FREQUENCY_DAY_LABELS:
            parsed_value = _coerce_frequency_value(stored_row.get(day_label))
            if parsed_value is not None:
                table[period][day_label] = parsed_value
    return table


def _get_or_create_mobile_app_settings(db: Session) -> MobileAppSettings:
    settings = db.get(MobileAppSettings, 1)
    timestamp = now_sgt()

    if settings is None:
        settings = MobileAppSettings(
            id=1,
            location_update_interval_seconds=DEFAULT_LOCATION_UPDATE_INTERVAL_SECONDS,
            location_accuracy_threshold_meters=DEFAULT_LOCATION_ACCURACY_THRESHOLD_METERS,
            coordinate_update_frequency_json=_serialize_coordinate_update_frequency_table(
                _build_default_coordinate_update_frequency_table()
            ),
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(settings)
        db.flush()
        return settings

    if settings.coordinate_update_frequency_json is None:
        settings.coordinate_update_frequency_json = _serialize_coordinate_update_frequency_table(
            _build_default_coordinate_update_frequency_table()
        )
        settings.updated_at = timestamp
        db.flush()
    return settings


def get_location_accuracy_threshold_meters(db: Session) -> int:
    settings = db.get(MobileAppSettings, 1)
    if settings is None:
        return DEFAULT_LOCATION_ACCURACY_THRESHOLD_METERS
    return settings.location_accuracy_threshold_meters


def get_coordinate_update_frequency_headers() -> list[str]:
    return list(COORDINATE_UPDATE_FREQUENCY_DAY_LABELS)


def get_coordinate_update_frequency_rows(db: Session) -> list[dict[str, object]]:
    table = get_coordinate_update_frequency_table(db)
    return [
        {
            "period": period,
            "values": {day_label: table[period][day_label] for day_label in COORDINATE_UPDATE_FREQUENCY_DAY_LABELS},
        }
        for period, _default_seconds in COORDINATE_UPDATE_FREQUENCY_PERIOD_VALUES
    ]


def get_coordinate_update_frequency_table(db: Session) -> dict[str, dict[str, int]]:
    settings = db.get(MobileAppSettings, 1)
    if settings is None:
        return _build_default_coordinate_update_frequency_table()
    return _parse_coordinate_update_frequency_table(settings.coordinate_update_frequency_json)


def get_location_update_interval_seconds(db: Session, *, at: datetime | None = None) -> int:
    day_label, period_label = resolve_coordinate_update_frequency_slot(at)
    table = get_coordinate_update_frequency_table(db)
    return table[period_label][day_label]


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
    settings = _get_or_create_mobile_app_settings(db)
    timestamp = now_sgt()

    settings.location_update_interval_seconds = get_location_update_interval_seconds(db)
    settings.location_accuracy_threshold_meters = accuracy_threshold_meters
    settings.updated_at = timestamp
    db.flush()
    return settings


def update_coordinate_update_frequency_value(
    db: Session,
    *,
    day_label: str,
    period_label: str,
    value_seconds: int,
) -> dict[str, int | bool]:
    if day_label not in COORDINATE_UPDATE_FREQUENCY_DAY_LABELS:
        raise ValueError("Dia da semana invalido para a frequencia de atualizacao de coordenadas")

    period_labels = {period for period, _default_seconds in COORDINATE_UPDATE_FREQUENCY_PERIOD_VALUES}
    if period_label not in period_labels:
        raise ValueError("Periodo invalido para a frequencia de atualizacao de coordenadas")

    settings = _get_or_create_mobile_app_settings(db)
    table = _parse_coordinate_update_frequency_table(settings.coordinate_update_frequency_json)
    previous_value_seconds = table[period_label][day_label]
    changed = previous_value_seconds != value_seconds
    if changed:
        table[period_label][day_label] = value_seconds
        settings.coordinate_update_frequency_json = _serialize_coordinate_update_frequency_table(table)
        settings.location_update_interval_seconds = get_location_update_interval_seconds(db)
        settings.updated_at = now_sgt()
        db.flush()

    return {
        "previous_value_seconds": previous_value_seconds,
        "current_value_seconds": value_seconds,
        "changed": changed,
    }