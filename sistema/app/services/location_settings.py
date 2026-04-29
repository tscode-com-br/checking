from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import MobileAppSettings, ProjectAutoCheckoutDistance, TransportCurrencyOption, TransportDailySetting, Workplace
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
DEFAULT_TRANSPORT_PRICE_RATE_UNIT = "day"
TRANSPORT_PRICE_QUANTUM = Decimal("0.01")
TRANSPORT_PRICE_RATE_UNITS = {"hour", "day", "week", "month"}


@dataclass(frozen=True)
class ProjectMinimumCheckoutDistanceRow:
    project_name: str
    minimum_checkout_distance_meters: int


@dataclass(frozen=True)
class ResolvedTransportWorkToHomeTimePolicy:
    service_date: date
    workplace: str | None
    resolved_work_to_home_time: str
    source: str
    global_work_to_home_time: str
    date_override_work_to_home_time: str | None
    workplace_work_to_home_time: str | None
    transport_group: str | None
    boarding_point: str | None
    transport_window_start: str | None
    transport_window_end: str | None
    service_restrictions: str | None


@dataclass(frozen=True)
class TransportCurrencyOptionRow:
    code: str
    display_label: str | None


def _normalize_transport_currency_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = "".join(str(value).upper().split())
    return normalized or None


def _normalize_transport_price_rate_unit(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in TRANSPORT_PRICE_RATE_UNITS:
        return DEFAULT_TRANSPORT_PRICE_RATE_UNIT
    return normalized


def _normalize_transport_price_value(value: float | int | Decimal | str | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        normalized_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Transport price must be a valid number.") from exc
    if normalized_value < 0:
        raise ValueError("Transport price cannot be negative.")
    if normalized_value > Decimal("9999999999.99"):
        raise ValueError("Transport price cannot exceed 9999999999.99.")
    return normalized_value.quantize(TRANSPORT_PRICE_QUANTUM, rounding=ROUND_HALF_UP)


def _serialize_transport_price_value(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


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


def list_transport_currency_options(db: Session) -> list[TransportCurrencyOptionRow]:
    rows = db.execute(
        select(TransportCurrencyOption)
        .where(TransportCurrencyOption.is_active.is_(True))
        .order_by(TransportCurrencyOption.code)
    ).scalars().all()
    return [
        TransportCurrencyOptionRow(code=row.code, display_label=row.display_label)
        for row in rows
    ]


def get_transport_pricing_settings(db: Session) -> dict[str, object]:
    settings = db.get(MobileAppSettings, 1)
    if settings is None:
        return {
            "price_currency_code": None,
            "price_rate_unit": DEFAULT_TRANSPORT_PRICE_RATE_UNIT,
            "default_car_price": None,
            "default_minivan_price": None,
            "default_van_price": None,
            "default_bus_price": None,
        }

    return {
        "price_currency_code": _normalize_transport_currency_code(settings.transport_price_currency_code),
        "price_rate_unit": _normalize_transport_price_rate_unit(settings.transport_price_rate_unit),
        "default_car_price": _serialize_transport_price_value(settings.transport_default_car_price),
        "default_minivan_price": _serialize_transport_price_value(settings.transport_default_minivan_price),
        "default_van_price": _serialize_transport_price_value(settings.transport_default_van_price),
        "default_bus_price": _serialize_transport_price_value(settings.transport_default_bus_price),
    }


def get_transport_settings_payload(db: Session) -> dict[str, object]:
    default_seat_counts = get_transport_vehicle_default_seat_counts(db)
    pricing_settings = get_transport_pricing_settings(db)
    return {
        "work_to_home_time": get_transport_work_to_home_time(db),
        "last_update_time": get_transport_last_update_time(db),
        "default_car_seats": default_seat_counts["default_car_seats"],
        "default_minivan_seats": default_seat_counts["default_minivan_seats"],
        "default_van_seats": default_seat_counts["default_van_seats"],
        "default_bus_seats": default_seat_counts["default_bus_seats"],
        "default_tolerance_minutes": default_seat_counts["default_tolerance_minutes"],
        "price_currency_code": pricing_settings["price_currency_code"],
        "price_rate_unit": pricing_settings["price_rate_unit"],
        "default_car_price": pricing_settings["default_car_price"],
        "default_minivan_price": pricing_settings["default_minivan_price"],
        "default_van_price": pricing_settings["default_van_price"],
        "default_bus_price": pricing_settings["default_bus_price"],
        "available_currencies": [
            {
                "code": row.code,
                "display_label": row.display_label,
            }
            for row in list_transport_currency_options(db)
        ],
    }


def get_transport_work_to_home_time_for_date(
    db: Session,
    *,
    service_date: date,
) -> str:
    return get_transport_work_to_home_time_for_context(db, service_date=service_date, workplace_name=None)


def get_transport_work_to_home_time_for_context(
    db: Session,
    *,
    service_date: date,
    workplace_name: str | None,
) -> str:
    return resolve_transport_work_to_home_time_policy(
        db,
        service_date=service_date,
        workplace_name=workplace_name,
    ).resolved_work_to_home_time


def resolve_transport_work_to_home_time_policy(
    db: Session,
    *,
    service_date: date,
    workplace_name: str | None,
) -> ResolvedTransportWorkToHomeTimePolicy:
    global_work_to_home_time = get_transport_work_to_home_time(db)
    daily_setting = db.execute(
        select(TransportDailySetting).where(TransportDailySetting.service_date == service_date)
    ).scalar_one_or_none()
    workplace = None
    if workplace_name is not None:
        workplace = db.execute(select(Workplace).where(Workplace.workplace == workplace_name)).scalar_one_or_none()

    date_override_work_to_home_time = (
        daily_setting.work_to_home_time
        if daily_setting is not None and daily_setting.work_to_home_time
        else None
    )
    workplace_work_to_home_time = (
        workplace.transport_work_to_home_time
        if workplace is not None and workplace.transport_work_to_home_time
        else None
    )

    if date_override_work_to_home_time is not None:
        resolved_work_to_home_time = date_override_work_to_home_time
        source = "date_override"
    elif workplace_work_to_home_time is not None:
        resolved_work_to_home_time = workplace_work_to_home_time
        source = "workplace_context"
    else:
        resolved_work_to_home_time = global_work_to_home_time
        source = "global"

    return ResolvedTransportWorkToHomeTimePolicy(
        service_date=service_date,
        workplace=workplace.workplace if workplace is not None else workplace_name,
        resolved_work_to_home_time=resolved_work_to_home_time,
        source=source,
        global_work_to_home_time=global_work_to_home_time,
        date_override_work_to_home_time=date_override_work_to_home_time,
        workplace_work_to_home_time=workplace_work_to_home_time,
        transport_group=workplace.transport_group if workplace is not None else None,
        boarding_point=workplace.boarding_point if workplace is not None else None,
        transport_window_start=workplace.transport_window_start if workplace is not None else None,
        transport_window_end=workplace.transport_window_end if workplace is not None else None,
        service_restrictions=workplace.service_restrictions if workplace is not None else None,
    )


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


def create_transport_currency_option(
    db: Session,
    *,
    code: str,
    display_label: str | None,
) -> TransportCurrencyOption:
    normalized_code = _normalize_transport_currency_code(code)
    if normalized_code is None:
        raise ValueError("Currency code is required.")

    existing_row = db.execute(
        select(TransportCurrencyOption).where(TransportCurrencyOption.code == normalized_code)
    ).scalar_one_or_none()
    if existing_row is not None:
        raise ValueError("Currency code already exists.")

    timestamp = now_sgt()
    row = TransportCurrencyOption(
        code=normalized_code,
        display_label=display_label,
        is_active=True,
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(row)
    db.flush()
    return row


def upsert_transport_pricing_settings(
    db: Session,
    *,
    price_currency_code: str | None,
    price_rate_unit: str,
    default_car_price: float | None,
    default_minivan_price: float | None,
    default_van_price: float | None,
    default_bus_price: float | None,
) -> MobileAppSettings:
    normalized_currency_code = _normalize_transport_currency_code(price_currency_code)
    if normalized_currency_code is not None:
        available_currency = db.execute(
            select(TransportCurrencyOption).where(
                TransportCurrencyOption.code == normalized_currency_code,
                TransportCurrencyOption.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if available_currency is None:
            raise ValueError("The selected currency is not available.")

    settings = _get_or_create_mobile_app_settings(db)
    timestamp = now_sgt()

    settings.transport_price_currency_code = normalized_currency_code
    settings.transport_price_rate_unit = _normalize_transport_price_rate_unit(price_rate_unit)
    settings.transport_default_car_price = _normalize_transport_price_value(default_car_price)
    settings.transport_default_minivan_price = _normalize_transport_price_value(default_minivan_price)
    settings.transport_default_van_price = _normalize_transport_price_value(default_van_price)
    settings.transport_default_bus_price = _normalize_transport_price_value(default_bus_price)
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