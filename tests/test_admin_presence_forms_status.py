from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import delete

from sistema.app.database import Base, SessionLocal, engine
from sistema.app.models import FormsSubmission, Project, User, UserSyncEvent
from sistema.app.routers.admin import build_presence_rows


Base.metadata.create_all(bind=engine)


def test_presence_rows_include_correlated_forms_status():
    event_time = datetime(2026, 5, 21, 8, 30, tzinfo=ZoneInfo("Asia/Singapore"))

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        db.execute(delete(FormsSubmission))
        db.execute(delete(UserSyncEvent))
        db.execute(delete(User))
        db.execute(delete(Project))

        db.add(
            Project(
                name="P80",
                country_code="SG",
                country_name="Singapore",
                timezone_name="Asia/Singapore",
                address="",
                zip_code="",
            )
        )
        user = User(
            rfid=None,
            chave="WB90",
            nome="Usuario Web",
            projeto="P80",
            local="Web",
            checkin=True,
            time=event_time,
            last_active_at=event_time,
            inactivity_days=0,
        )
        db.add(user)
        db.flush()

        db.add(
            UserSyncEvent(
                user_id=user.id,
                chave=user.chave,
                rfid=user.rfid,
                source="web_forms",
                action="checkin",
                projeto="P80",
                local="Web",
                ontime=True,
                event_time=event_time,
                created_at=event_time,
                source_request_id="web-request-1",
                device_id=None,
            )
        )
        db.add(
            FormsSubmission(
                request_id="web-request-1",
                rfid=None,
                action="checkin",
                chave=user.chave,
                projeto="P80",
                device_id=None,
                local="Web",
                event_time=event_time,
                request_path="/api/web/check",
                display_status="filling",
                project_candidates_json='["P80"]',
                ontime=True,
                status="processing",
                retry_count=0,
                last_error=None,
                created_at=event_time,
                updated_at=event_time,
                processed_at=None,
            )
        )
        db.commit()

        rows, _ = build_presence_rows(db, action="checkin", current_admin=None, reference_time=event_time)

    assert len(rows) == 1
    assert rows[0].forms_status == "filling"


def test_presence_rows_include_not_realized_forms_status_for_skipped_forms():
    event_time = datetime(2026, 5, 21, 9, 15, tzinfo=ZoneInfo("Asia/Singapore"))

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        db.execute(delete(FormsSubmission))
        db.execute(delete(UserSyncEvent))
        db.execute(delete(User))
        db.execute(delete(Project))

        db.add(
            Project(
                name="P80",
                country_code="SG",
                country_name="Singapore",
                timezone_name="Asia/Singapore",
                address="",
                zip_code="",
            )
        )
        user = User(
            rfid=None,
            chave="WB91",
            nome="Usuario Sem Forms",
            projeto="P80",
            local="Web",
            checkin=True,
            time=event_time,
            last_active_at=event_time,
            inactivity_days=0,
        )
        db.add(user)
        db.flush()

        db.add(
            UserSyncEvent(
                user_id=user.id,
                chave=user.chave,
                rfid=user.rfid,
                source="web_forms",
                action="checkin",
                projeto="P80",
                local="Web",
                ontime=True,
                event_time=event_time,
                created_at=event_time,
                source_request_id="web-request-2",
                device_id=None,
            )
        )
        db.add(
            FormsSubmission(
                request_id="web-request-2",
                rfid=None,
                action="checkin",
                chave=user.chave,
                projeto="P80",
                device_id=None,
                local="Web",
                event_time=event_time,
                request_path="/api/web/check",
                display_status="not_realized",
                project_candidates_json='["P80"]',
                ontime=True,
                status="skipped",
                retry_count=0,
                last_error="repeated_same_action_same_day",
                created_at=event_time,
                updated_at=event_time,
                processed_at=event_time,
            )
        )
        db.commit()

        rows, _ = build_presence_rows(db, action="checkin", current_admin=None, reference_time=event_time)

    assert len(rows) == 1
    assert rows[0].forms_status == "not_realized"