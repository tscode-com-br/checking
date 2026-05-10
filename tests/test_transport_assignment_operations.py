from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import TransportAssignment, TransportRequest, User, Vehicle
from sistema.app.services.transport_assignment_operations import (
    _find_confirmed_recurring_assignment_conflicts,
    upsert_transport_assignment_with_persistence,
)


def _build_session_factory(db_path: Path):
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def _fixture_timestamp() -> datetime:
    return datetime(2026, 5, 8, 9, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))


def _create_user(session: Session, *, chave: str, projeto: str) -> User:
    user = User(
        rfid=None,
        chave=chave,
        senha=None,
        perfil=0,
        admin_monitored_projects_json=None,
        nome=f"Usuario {chave}",
        projeto=projeto,
        workplace=None,
        vehicle_id=None,
        placa=None,
        end_rua="10 Test Avenue",
        zip="123456",
        cargo=None,
        email=None,
        local=None,
        checkin=None,
        time=None,
        last_active_at=_fixture_timestamp(),
        inactivity_days=0,
    )
    session.add(user)
    session.flush()
    return user


def _create_vehicle(session: Session, *, plate: str) -> Vehicle:
    vehicle = Vehicle(
        placa=plate,
        tipo="van",
        color="White",
        lugares=10,
        tolerance=8,
        service_scope="regular",
    )
    session.add(vehicle)
    session.flush()
    return vehicle


def _create_transport_request(
    session: Session,
    *,
    user_id: int,
    request_kind: str,
    service_date: date,
    selected_weekdays: list[int] | None = None,
    status: str = "active",
) -> TransportRequest:
    timestamp = _fixture_timestamp()
    if request_kind == "extra":
        recurrence_kind = "single_date"
        selected_weekdays_json = None
        single_date = service_date
    elif request_kind == "regular":
        recurrence_kind = "weekday"
        selected_weekdays_json = json.dumps(selected_weekdays or [0, 1, 2, 3, 4])
        single_date = None
    elif request_kind == "weekend":
        recurrence_kind = "weekend"
        selected_weekdays_json = json.dumps(selected_weekdays or [5, 6])
        single_date = None
    else:
        raise ValueError(f"Unsupported request kind: {request_kind!r}")

    transport_request = TransportRequest(
        user_id=user_id,
        request_kind=request_kind,
        recurrence_kind=recurrence_kind,
        requested_time="08:00",
        selected_weekdays_json=selected_weekdays_json,
        single_date=single_date,
        created_via="test",
        status=status,
        created_at=timestamp,
        updated_at=timestamp,
        cancelled_at=None,
    )
    session.add(transport_request)
    session.flush()
    return transport_request


def _create_assignment(
    session: Session,
    *,
    request_id: int,
    service_date: date,
    route_kind: str,
    status: str,
    vehicle_id: int | None,
    boarding_time: str | None = None,
) -> TransportAssignment:
    timestamp = _fixture_timestamp()
    assignment = TransportAssignment(
        request_id=request_id,
        service_date=service_date,
        route_kind=route_kind,
        vehicle_id=vehicle_id,
        status=status,
        response_message="test-assignment",
        boarding_time=boarding_time,
        acknowledged_by_user=False,
        acknowledged_at=None,
        assigned_by_admin_id=None,
        created_at=timestamp,
        updated_at=timestamp,
        notified_at=None,
    )
    session.add(assignment)
    session.flush()
    return assignment


def test_find_confirmed_recurring_assignment_conflicts_returns_only_same_user_date_route_and_applicable_requests(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_assignment_conflicts_weekday.db")
    service_date = date(2026, 4, 21)

    try:
        with session_factory() as session:
            vehicle = _create_vehicle(session, plate="F2A2101")
            user = _create_user(session, chave="F2A1", projeto="P80")
            other_user = _create_user(session, chave="F2A2", projeto="P81")

            current_extra = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="extra",
                service_date=service_date,
            )
            matching_regular = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="regular",
                service_date=service_date,
                selected_weekdays=[service_date.weekday()],
            )
            same_day_other_route = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="regular",
                service_date=service_date,
                selected_weekdays=[service_date.weekday()],
            )
            other_date_regular = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="regular",
                service_date=service_date,
                selected_weekdays=[service_date.weekday()],
            )
            non_applicable_weekend = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="weekend",
                service_date=service_date,
                selected_weekdays=[5],
            )
            pending_regular = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="regular",
                service_date=service_date,
                selected_weekdays=[service_date.weekday()],
            )
            same_day_other_user = _create_transport_request(
                session,
                user_id=other_user.id,
                request_kind="regular",
                service_date=service_date,
                selected_weekdays=[service_date.weekday()],
            )

            current_extra_assignment = _create_assignment(
                session,
                request_id=current_extra.id,
                service_date=service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle_id=vehicle.id,
            )
            matching_assignment = _create_assignment(
                session,
                request_id=matching_regular.id,
                service_date=service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle_id=vehicle.id,
            )
            _create_assignment(
                session,
                request_id=same_day_other_route.id,
                service_date=service_date,
                route_kind="work_to_home",
                status="confirmed",
                vehicle_id=vehicle.id,
            )
            _create_assignment(
                session,
                request_id=other_date_regular.id,
                service_date=service_date.replace(day=22),
                route_kind="home_to_work",
                status="confirmed",
                vehicle_id=vehicle.id,
            )
            _create_assignment(
                session,
                request_id=non_applicable_weekend.id,
                service_date=service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle_id=vehicle.id,
            )
            _create_assignment(
                session,
                request_id=pending_regular.id,
                service_date=service_date,
                route_kind="home_to_work",
                status="pending",
                vehicle_id=None,
            )
            _create_assignment(
                session,
                request_id=same_day_other_user.id,
                service_date=service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle_id=vehicle.id,
            )
            session.commit()

            conflicts = _find_confirmed_recurring_assignment_conflicts(
                session,
                user_id=user.id,
                service_date=service_date,
                route_kind="home_to_work",
                excluded_request_id=current_extra.id,
            )

        assert [assignment.id for assignment in conflicts] == [matching_assignment.id]
        assert current_extra_assignment.id not in [assignment.id for assignment in conflicts]
    finally:
        engine.dispose()


def test_find_confirmed_recurring_assignment_conflicts_returns_weekend_matches_for_weekend_service_dates(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_assignment_conflicts_weekend.db")
    service_date = date(2026, 4, 25)

    try:
        with session_factory() as session:
            vehicle = _create_vehicle(session, plate="F2A2501")
            user = _create_user(session, chave="F2B1", projeto="P83")

            current_extra = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="extra",
                service_date=service_date,
            )
            matching_weekend = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="weekend",
                service_date=service_date,
                selected_weekdays=[service_date.weekday()],
            )
            non_applicable_regular = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="regular",
                service_date=service_date,
                selected_weekdays=[0, 1, 2, 3, 4],
            )
            opposite_route_weekend = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="weekend",
                service_date=service_date,
                selected_weekdays=[service_date.weekday()],
            )

            matching_assignment = _create_assignment(
                session,
                request_id=matching_weekend.id,
                service_date=service_date,
                route_kind="work_to_home",
                status="confirmed",
                vehicle_id=vehicle.id,
            )
            _create_assignment(
                session,
                request_id=current_extra.id,
                service_date=service_date,
                route_kind="work_to_home",
                status="confirmed",
                vehicle_id=vehicle.id,
            )
            _create_assignment(
                session,
                request_id=non_applicable_regular.id,
                service_date=service_date,
                route_kind="work_to_home",
                status="confirmed",
                vehicle_id=vehicle.id,
            )
            _create_assignment(
                session,
                request_id=opposite_route_weekend.id,
                service_date=service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle_id=vehicle.id,
            )
            session.commit()

            conflicts = _find_confirmed_recurring_assignment_conflicts(
                session,
                user_id=user.id,
                service_date=service_date,
                route_kind="work_to_home",
                excluded_request_id=current_extra.id,
            )

        assert [assignment.id for assignment in conflicts] == [matching_assignment.id]
    finally:
        engine.dispose()


def test_upsert_transport_assignment_with_persistence_resets_same_day_route_conflicts_for_confirmed_extra(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_assignment_extra_override.db")
    service_date = date(2026, 4, 21)
    future_service_date = service_date + timedelta(days=7)

    try:
        with session_factory() as session:
            recurring_vehicle = _create_vehicle(session, plate="F3A2101")
            extra_vehicle = _create_vehicle(session, plate="F3A2102")
            user = _create_user(session, chave="F3A1", projeto="P80")

            regular_request = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="regular",
                service_date=service_date,
                selected_weekdays=[service_date.weekday()],
            )
            extra_request = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="extra",
                service_date=service_date,
            )

            same_day_home_assignment = _create_assignment(
                session,
                request_id=regular_request.id,
                service_date=service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle_id=recurring_vehicle.id,
                boarding_time="07:05",
            )
            same_day_work_assignment = _create_assignment(
                session,
                request_id=regular_request.id,
                service_date=service_date,
                route_kind="work_to_home",
                status="confirmed",
                vehicle_id=recurring_vehicle.id,
            )
            future_home_assignment = _create_assignment(
                session,
                request_id=regular_request.id,
                service_date=future_service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle_id=recurring_vehicle.id,
            )
            session.commit()

            extra_assignment, is_update = upsert_transport_assignment_with_persistence(
                session,
                transport_request=extra_request,
                service_date=service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle=extra_vehicle,
                response_message="Extra confirmed manually",
                boarding_time="07:20",
                admin_user_id=None,
            )
            session.commit()

            refreshed_same_day_home_assignment = session.get(TransportAssignment, same_day_home_assignment.id)
            refreshed_same_day_work_assignment = session.get(TransportAssignment, same_day_work_assignment.id)
            refreshed_future_home_assignment = session.get(TransportAssignment, future_home_assignment.id)
            refreshed_regular_request = session.get(TransportRequest, regular_request.id)

        assert is_update is False
        assert extra_assignment.status == "confirmed"
        assert extra_assignment.vehicle_id == extra_vehicle.id
        assert extra_assignment.boarding_time == "07:20"
        assert extra_assignment.response_message == "Extra confirmed manually"

        assert refreshed_same_day_home_assignment is not None
        assert refreshed_same_day_home_assignment.status == "pending"
        assert refreshed_same_day_home_assignment.vehicle_id is None
        assert refreshed_same_day_home_assignment.boarding_time is None
        assert refreshed_same_day_home_assignment.response_message == (
            "Superseded by confirmed extra transport assignment"
        )

        assert refreshed_regular_request is not None
        assert refreshed_regular_request.status == "active"

        assert refreshed_same_day_work_assignment is not None
        assert refreshed_same_day_work_assignment.status == "confirmed"
        assert refreshed_same_day_work_assignment.vehicle_id == recurring_vehicle.id

        assert refreshed_future_home_assignment is not None
        assert refreshed_future_home_assignment.status == "confirmed"
        assert refreshed_future_home_assignment.vehicle_id == recurring_vehicle.id
    finally:
        engine.dispose()


def test_upsert_transport_assignment_with_persistence_handles_boarding_time_lifecycle_for_confirmed_home_to_work(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_assignment_boarding_time_lifecycle.db")
    service_date = date(2026, 4, 21)

    try:
        with session_factory() as session:
            vehicle = _create_vehicle(session, plate="F3C2101")
            user = _create_user(session, chave="F3C1", projeto="P80")
            extra_request = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="extra",
                service_date=service_date,
            )
            session.commit()

            assignment_without_time, initial_is_update = upsert_transport_assignment_with_persistence(
                session,
                transport_request=extra_request,
                service_date=service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle=vehicle,
                response_message="Confirmed without pickup time",
                admin_user_id=None,
            )
            session.commit()

            assignment_with_time, is_update = upsert_transport_assignment_with_persistence(
                session,
                transport_request=extra_request,
                service_date=service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle=vehicle,
                response_message="Confirmed with pickup time",
                boarding_time="07:12",
                admin_user_id=None,
            )
            session.commit()
            persisted_boarding_time_after_update = session.get(
                TransportAssignment,
                assignment_with_time.id,
            ).boarding_time

            preserved_assignment, preserved_is_update = upsert_transport_assignment_with_persistence(
                session,
                transport_request=extra_request,
                service_date=service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle=vehicle,
                response_message="Confirmed again without touching pickup time",
                admin_user_id=None,
            )
            session.commit()
            persisted_boarding_time_after_preserve = session.get(
                TransportAssignment,
                preserved_assignment.id,
            ).boarding_time

            reset_assignment, reset_is_update = upsert_transport_assignment_with_persistence(
                session,
                transport_request=extra_request,
                service_date=service_date,
                route_kind="home_to_work",
                status="pending",
                vehicle=None,
                response_message="Reset to pending",
                admin_user_id=None,
            )
            session.commit()

            refreshed_assignment = session.get(TransportAssignment, reset_assignment.id)

        assert initial_is_update is False
        assert assignment_without_time.boarding_time is None
        assert is_update is True
        assert persisted_boarding_time_after_update == "07:12"
        assert preserved_is_update is True
        assert persisted_boarding_time_after_preserve == "07:12"
        assert reset_is_update is True
        assert refreshed_assignment is not None
        assert refreshed_assignment.status == "pending"
        assert refreshed_assignment.vehicle_id is None
        assert refreshed_assignment.boarding_time is None
    finally:
        engine.dispose()


def test_upsert_transport_assignment_with_persistence_does_not_persist_boarding_time_for_work_to_home(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_assignment_boarding_time_work_to_home.db")
    service_date = date(2026, 4, 21)

    try:
        with session_factory() as session:
            vehicle = _create_vehicle(session, plate="F3D2101")
            user = _create_user(session, chave="F3D1", projeto="P80")
            extra_request = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="extra",
                service_date=service_date,
            )
            session.commit()

            assignment, is_update = upsert_transport_assignment_with_persistence(
                session,
                transport_request=extra_request,
                service_date=service_date,
                route_kind="work_to_home",
                status="confirmed",
                vehicle=vehicle,
                response_message="Confirmed work-to-home assignment",
                boarding_time="19:05",
                admin_user_id=None,
            )
            session.commit()

            refreshed_assignment = session.get(TransportAssignment, assignment.id)

        assert is_update is False
        assert refreshed_assignment is not None
        assert refreshed_assignment.status == "confirmed"
        assert refreshed_assignment.vehicle_id == vehicle.id
        assert refreshed_assignment.boarding_time is None
    finally:
        engine.dispose()


def test_upsert_transport_assignment_with_persistence_resets_same_user_conflicts_across_request_ids(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_assignment_same_user_multi_request.db")
    service_date = date(2026, 4, 21)
    future_service_date = service_date + timedelta(days=7)

    try:
        with session_factory() as session:
            first_recurring_vehicle = _create_vehicle(session, plate="F3B2101")
            second_recurring_vehicle = _create_vehicle(session, plate="F3B2102")
            extra_vehicle = _create_vehicle(session, plate="F3B2103")
            user = _create_user(session, chave="F3B1", projeto="P80")

            first_regular_request = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="regular",
                service_date=service_date,
                selected_weekdays=[service_date.weekday()],
            )
            second_regular_request = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="regular",
                service_date=service_date,
                selected_weekdays=[service_date.weekday()],
            )
            extra_request = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="extra",
                service_date=service_date,
            )

            first_same_day_home_assignment = _create_assignment(
                session,
                request_id=first_regular_request.id,
                service_date=service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle_id=first_recurring_vehicle.id,
            )
            first_same_day_work_assignment = _create_assignment(
                session,
                request_id=first_regular_request.id,
                service_date=service_date,
                route_kind="work_to_home",
                status="confirmed",
                vehicle_id=first_recurring_vehicle.id,
            )
            first_future_home_assignment = _create_assignment(
                session,
                request_id=first_regular_request.id,
                service_date=future_service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle_id=first_recurring_vehicle.id,
            )

            second_same_day_home_assignment = _create_assignment(
                session,
                request_id=second_regular_request.id,
                service_date=service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle_id=second_recurring_vehicle.id,
            )
            second_same_day_work_assignment = _create_assignment(
                session,
                request_id=second_regular_request.id,
                service_date=service_date,
                route_kind="work_to_home",
                status="confirmed",
                vehicle_id=second_recurring_vehicle.id,
            )
            second_future_home_assignment = _create_assignment(
                session,
                request_id=second_regular_request.id,
                service_date=future_service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle_id=second_recurring_vehicle.id,
            )
            session.commit()

            extra_assignment, is_update = upsert_transport_assignment_with_persistence(
                session,
                transport_request=extra_request,
                service_date=service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle=extra_vehicle,
                response_message="Extra confirmed manually",
                admin_user_id=None,
            )
            session.commit()

            refreshed_first_same_day_home_assignment = session.get(TransportAssignment, first_same_day_home_assignment.id)
            refreshed_first_same_day_work_assignment = session.get(TransportAssignment, first_same_day_work_assignment.id)
            refreshed_first_future_home_assignment = session.get(TransportAssignment, first_future_home_assignment.id)
            refreshed_second_same_day_home_assignment = session.get(TransportAssignment, second_same_day_home_assignment.id)
            refreshed_second_same_day_work_assignment = session.get(TransportAssignment, second_same_day_work_assignment.id)
            refreshed_second_future_home_assignment = session.get(TransportAssignment, second_future_home_assignment.id)
            refreshed_first_regular_request = session.get(TransportRequest, first_regular_request.id)
            refreshed_second_regular_request = session.get(TransportRequest, second_regular_request.id)

        assert is_update is False
        assert extra_assignment.status == "confirmed"
        assert extra_assignment.vehicle_id == extra_vehicle.id

        assert refreshed_first_same_day_home_assignment is not None
        assert refreshed_first_same_day_home_assignment.status == "pending"
        assert refreshed_first_same_day_home_assignment.vehicle_id is None
        assert refreshed_first_same_day_home_assignment.response_message == (
            "Superseded by confirmed extra transport assignment"
        )

        assert refreshed_second_same_day_home_assignment is not None
        assert refreshed_second_same_day_home_assignment.status == "pending"
        assert refreshed_second_same_day_home_assignment.vehicle_id is None
        assert refreshed_second_same_day_home_assignment.response_message == (
            "Superseded by confirmed extra transport assignment"
        )

        assert refreshed_first_same_day_work_assignment is not None
        assert refreshed_first_same_day_work_assignment.status == "confirmed"
        assert refreshed_first_same_day_work_assignment.vehicle_id == first_recurring_vehicle.id

        assert refreshed_second_same_day_work_assignment is not None
        assert refreshed_second_same_day_work_assignment.status == "confirmed"
        assert refreshed_second_same_day_work_assignment.vehicle_id == second_recurring_vehicle.id

        assert refreshed_first_future_home_assignment is not None
        assert refreshed_first_future_home_assignment.status == "confirmed"
        assert refreshed_first_future_home_assignment.vehicle_id == first_recurring_vehicle.id

        assert refreshed_second_future_home_assignment is not None
        assert refreshed_second_future_home_assignment.status == "confirmed"
        assert refreshed_second_future_home_assignment.vehicle_id == second_recurring_vehicle.id

        assert refreshed_first_regular_request is not None
        assert refreshed_first_regular_request.status == "active"

        assert refreshed_second_regular_request is not None
        assert refreshed_second_regular_request.status == "active"
    finally:
        engine.dispose()


def test_upsert_transport_assignment_with_persistence_blocks_recurring_confirmation_when_extra_exists_on_same_route(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_assignment_extra_block_same_route.db")
    service_date = date(2026, 4, 21)

    try:
        with session_factory() as session:
            recurring_vehicle = _create_vehicle(session, plate="F4A2101")
            extra_vehicle = _create_vehicle(session, plate="F4A2102")
            user = _create_user(session, chave="F4A1", projeto="P80")

            regular_request = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="regular",
                service_date=service_date,
                selected_weekdays=[service_date.weekday()],
            )
            extra_request = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="extra",
                service_date=service_date,
            )

            pending_home_assignment = _create_assignment(
                session,
                request_id=regular_request.id,
                service_date=service_date,
                route_kind="home_to_work",
                status="pending",
                vehicle_id=None,
            )
            confirmed_extra_assignment = _create_assignment(
                session,
                request_id=extra_request.id,
                service_date=service_date,
                route_kind="home_to_work",
                status="confirmed",
                vehicle_id=extra_vehicle.id,
            )
            session.commit()

            with pytest.raises(
                ValueError,
                match=(
                    "The user already has a confirmed extra transport override for this date and route: "
                    "home_to_work\\."
                ),
            ):
                upsert_transport_assignment_with_persistence(
                    session,
                    transport_request=regular_request,
                    service_date=service_date,
                    route_kind="home_to_work",
                    status="confirmed",
                    vehicle=recurring_vehicle,
                    response_message="Regular confirmed manually",
                    admin_user_id=None,
                )

            refreshed_pending_home_assignment = session.get(TransportAssignment, pending_home_assignment.id)
            refreshed_confirmed_extra_assignment = session.get(TransportAssignment, confirmed_extra_assignment.id)

        assert refreshed_pending_home_assignment is not None
        assert refreshed_pending_home_assignment.status == "pending"
        assert refreshed_pending_home_assignment.vehicle_id is None

        assert refreshed_confirmed_extra_assignment is not None
        assert refreshed_confirmed_extra_assignment.status == "confirmed"
        assert refreshed_confirmed_extra_assignment.vehicle_id == extra_vehicle.id
    finally:
        engine.dispose()


def test_upsert_transport_assignment_with_persistence_blocks_recurring_confirmation_when_extra_exists_on_opposite_route(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "transport_assignment_extra_block_opposite_route.db")
    service_date = date(2026, 4, 21)

    try:
        with session_factory() as session:
            recurring_vehicle = _create_vehicle(session, plate="F4B2101")
            extra_vehicle = _create_vehicle(session, plate="F4B2102")
            user = _create_user(session, chave="F4B1", projeto="P80")

            regular_request = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="regular",
                service_date=service_date,
                selected_weekdays=[service_date.weekday()],
            )
            extra_request = _create_transport_request(
                session,
                user_id=user.id,
                request_kind="extra",
                service_date=service_date,
            )

            pending_home_assignment = _create_assignment(
                session,
                request_id=regular_request.id,
                service_date=service_date,
                route_kind="home_to_work",
                status="pending",
                vehicle_id=None,
            )
            pending_work_assignment = _create_assignment(
                session,
                request_id=regular_request.id,
                service_date=service_date,
                route_kind="work_to_home",
                status="pending",
                vehicle_id=None,
            )
            confirmed_extra_assignment = _create_assignment(
                session,
                request_id=extra_request.id,
                service_date=service_date,
                route_kind="work_to_home",
                status="confirmed",
                vehicle_id=extra_vehicle.id,
            )
            session.commit()

            with pytest.raises(
                ValueError,
                match=(
                    "The user already has a confirmed extra transport override for this date and route: "
                    "work_to_home\\."
                ),
            ):
                upsert_transport_assignment_with_persistence(
                    session,
                    transport_request=regular_request,
                    service_date=service_date,
                    route_kind="home_to_work",
                    status="confirmed",
                    vehicle=recurring_vehicle,
                    response_message="Regular confirmed manually",
                    admin_user_id=None,
                )

            refreshed_pending_home_assignment = session.get(TransportAssignment, pending_home_assignment.id)
            refreshed_pending_work_assignment = session.get(TransportAssignment, pending_work_assignment.id)
            refreshed_confirmed_extra_assignment = session.get(TransportAssignment, confirmed_extra_assignment.id)

        assert refreshed_pending_home_assignment is not None
        assert refreshed_pending_home_assignment.status == "pending"
        assert refreshed_pending_home_assignment.vehicle_id is None

        assert refreshed_pending_work_assignment is not None
        assert refreshed_pending_work_assignment.status == "pending"
        assert refreshed_pending_work_assignment.vehicle_id is None

        assert refreshed_confirmed_extra_assignment is not None
        assert refreshed_confirmed_extra_assignment.status == "confirmed"
        assert refreshed_confirmed_extra_assignment.vehicle_id == extra_vehicle.id
    finally:
        engine.dispose()