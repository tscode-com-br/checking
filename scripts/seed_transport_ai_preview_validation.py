from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sistema.app.database import SessionLocal
from sistema.app.models import (
    AdminUser,
    MobileAppSettings,
    Project,
    TransportAssignment,
    TransportRequest,
    TransportVehicleSchedule,
    User,
    Vehicle,
)


FIXTURE_TIMEZONE = ZoneInfo("Asia/Singapore")
FIXTURE_TIMESTAMP = datetime(2026, 5, 4, 8, 0, 0, tzinfo=FIXTURE_TIMEZONE)


@dataclass(frozen=True)
class PreviewScenario:
    project_name: str
    project_address: str
    project_zip: str
    user_key: str
    user_name: str
    user_address: str
    user_zip: str
    vehicle_plate: str
    service_date: date
    seed_confirmed_assignment: bool


def _scenario_service_dates() -> tuple[date, date]:
    today = date.today()
    tomorrow = today + timedelta(days=1)
    return today, tomorrow


def _build_scenarios() -> list[PreviewScenario]:
    today, tomorrow = _scenario_service_dates()
    return [
        PreviewScenario(
            project_name="AI14 Preview Apply",
            project_address="1 Marina Boulevard",
            project_zip="018989",
            user_key="A14A",
            user_name="AI Preview Apply Rider",
            user_address="10 Bayfront Avenue",
            user_zip="018956",
            vehicle_plate="AI14AP1",
            service_date=today,
            seed_confirmed_assignment=False,
        ),
        PreviewScenario(
            project_name="AI14 Preview Cancel",
            project_address="25 Raffles Place",
            project_zip="048622",
            user_key="A14C",
            user_name="AI Preview Cancel Rider",
            user_address="80 Robinson Road",
            user_zip="068898",
            vehicle_plate="AI14CN1",
            service_date=tomorrow,
            seed_confirmed_assignment=True,
        ),
    ]


def _ensure_preview_admin_user(session) -> AdminUser:
    admin_user = session.execute(
        select(AdminUser).where(AdminUser.chave == "HR70")
    ).scalar_one_or_none()
    if admin_user is None:
        admin_user = AdminUser(
            chave="HR70",
            nome_completo="Transport AI Preview Admin",
            password_hash=None,
            requires_password_reset=False,
            approved_by_admin_id=None,
            approved_at=None,
            password_reset_requested_at=None,
            created_at=FIXTURE_TIMESTAMP,
            updated_at=FIXTURE_TIMESTAMP,
        )
        session.add(admin_user)
        session.flush()
    return admin_user


def _ensure_transport_settings(session) -> None:
    settings_row = session.get(MobileAppSettings, 1)
    if settings_row is None:
        settings_row = MobileAppSettings(
            id=1,
            created_at=FIXTURE_TIMESTAMP,
            updated_at=FIXTURE_TIMESTAMP,
        )
        session.add(settings_row)

    settings_row.transport_work_to_home_time = "16:45"
    settings_row.transport_last_update_time = "16:00"
    settings_row.transport_default_car_seats = 4
    settings_row.transport_default_minivan_seats = 6
    settings_row.transport_default_van_seats = 10
    settings_row.transport_default_bus_seats = 40
    settings_row.transport_default_tolerance_minutes = 5
    settings_row.transport_price_currency_code = "SGD"
    settings_row.transport_price_rate_unit = "day"
    settings_row.transport_default_car_price = 15
    settings_row.transport_default_minivan_price = 30
    settings_row.transport_default_van_price = 45
    settings_row.transport_default_bus_price = 70
    settings_row.updated_at = FIXTURE_TIMESTAMP
    session.flush()


def _delete_existing_scenario(session, scenario: PreviewScenario) -> None:
    user = session.execute(
        select(User).where(User.chave == scenario.user_key)
    ).scalar_one_or_none()
    if user is None:
        project = session.execute(
            select(Project).where(Project.name == scenario.project_name)
        ).scalar_one_or_none()
        if project is not None:
            session.delete(project)
            session.flush()
        return

    request_ids = session.execute(
        select(TransportRequest.id).where(TransportRequest.user_id == user.id)
    ).scalars().all()
    vehicle_ids = session.execute(
        select(Vehicle.id).where(Vehicle.placa == scenario.vehicle_plate)
    ).scalars().all()

    if request_ids:
        session.execute(
            delete(TransportAssignment).where(TransportAssignment.request_id.in_(request_ids))
        )
        session.execute(
            delete(TransportRequest).where(TransportRequest.id.in_(request_ids))
        )

    if vehicle_ids:
        session.execute(
            delete(TransportVehicleSchedule).where(TransportVehicleSchedule.vehicle_id.in_(vehicle_ids))
        )
        session.execute(delete(Vehicle).where(Vehicle.id.in_(vehicle_ids)))

    project = session.execute(
        select(Project).where(Project.name == scenario.project_name)
    ).scalar_one_or_none()
    session.delete(user)
    if project is not None:
        session.delete(project)
    session.flush()


def _create_project(session, scenario: PreviewScenario) -> Project:
    project = Project(
        name=scenario.project_name,
        country_code="SG",
        country_name="Singapore",
        timezone_name="Asia/Singapore",
        address=scenario.project_address,
        zip_code=scenario.project_zip,
    )
    session.add(project)
    session.flush()
    return project


def _create_user(session, scenario: PreviewScenario) -> User:
    user = User(
        rfid=None,
        chave=scenario.user_key,
        senha=None,
        perfil=0,
        admin_monitored_projects_json=None,
        nome=scenario.user_name,
        projeto=scenario.project_name,
        workplace=None,
        vehicle_id=None,
        placa=None,
        end_rua=scenario.user_address,
        zip=scenario.user_zip,
        cargo=None,
        email=None,
        local=None,
        checkin=None,
        time=None,
        last_active_at=FIXTURE_TIMESTAMP,
        inactivity_days=0,
    )
    session.add(user)
    session.flush()
    return user


def _create_transport_request(session, *, user_id: int, service_date: date) -> TransportRequest:
    transport_request = TransportRequest(
        user_id=user_id,
        request_kind="extra",
        recurrence_kind="single_date",
        requested_time="08:00",
        selected_weekdays_json=None,
        single_date=service_date,
        created_via="admin",
        status="active",
        created_at=FIXTURE_TIMESTAMP,
        updated_at=FIXTURE_TIMESTAMP,
        cancelled_at=None,
    )
    session.add(transport_request)
    session.flush()
    return transport_request


def _create_vehicle(session, scenario: PreviewScenario) -> Vehicle:
    vehicle = Vehicle(
        placa=scenario.vehicle_plate,
        tipo="carro",
        color="white",
        lugares=4,
        tolerance=0,
        service_scope="extra",
    )
    session.add(vehicle)
    session.flush()

    schedule = TransportVehicleSchedule(
        vehicle_id=vehicle.id,
        service_scope="extra",
        route_kind="home_to_work",
        recurrence_kind="single_date",
        service_date=scenario.service_date,
        weekday=scenario.service_date.weekday(),
        departure_time="07:30",
        is_active=True,
        created_at=FIXTURE_TIMESTAMP,
        updated_at=FIXTURE_TIMESTAMP,
    )
    session.add(schedule)
    session.flush()
    return vehicle


def _create_confirmed_assignment(
    session,
    *,
    transport_request: TransportRequest,
    scenario: PreviewScenario,
    vehicle: Vehicle,
    admin_user: AdminUser,
) -> None:
    assignment = TransportAssignment(
        request_id=transport_request.id,
        service_date=scenario.service_date,
        route_kind="home_to_work",
        vehicle_id=vehicle.id,
        status="confirmed",
        response_message="preview-validation-baseline",
        acknowledged_by_user=False,
        acknowledged_at=None,
        assigned_by_admin_id=admin_user.id,
        created_at=FIXTURE_TIMESTAMP,
        updated_at=FIXTURE_TIMESTAMP,
        notified_at=None,
    )
    session.add(assignment)
    session.flush()


def seed_transport_ai_preview_validation() -> list[dict[str, str]]:
    scenarios = _build_scenarios()
    seeded_rows: list[dict[str, str]] = []

    with SessionLocal() as session:
        admin_user = _ensure_preview_admin_user(session)
        _ensure_transport_settings(session)

        for scenario in scenarios:
            _delete_existing_scenario(session, scenario)
            _create_project(session, scenario)
            user = _create_user(session, scenario)
            transport_request = _create_transport_request(
                session,
                user_id=user.id,
                service_date=scenario.service_date,
            )
            vehicle = _create_vehicle(session, scenario)

            if scenario.seed_confirmed_assignment:
                _create_confirmed_assignment(
                    session,
                    transport_request=transport_request,
                    scenario=scenario,
                    vehicle=vehicle,
                    admin_user=admin_user,
                )

            seeded_rows.append(
                {
                    "service_date": scenario.service_date.isoformat(),
                    "project_name": scenario.project_name,
                    "user_key": scenario.user_key,
                    "user_name": scenario.user_name,
                    "vehicle_plate": scenario.vehicle_plate,
                    "baseline_assignment": "confirmed" if scenario.seed_confirmed_assignment else "pending",
                }
            )

        session.commit()

    return seeded_rows


def main() -> None:
    seeded_rows = seed_transport_ai_preview_validation()
    print("Transport AI preview validation seed completed.")
    print("Transport login: HR70 / eAcacdLe2")
    for row in seeded_rows:
        print(
            " - "
            f"{row['service_date']} | {row['project_name']} | {row['user_key']} | "
            f"vehicle={row['vehicle_plate']} | baseline={row['baseline_assignment']}"
        )


if __name__ == "__main__":
    main()