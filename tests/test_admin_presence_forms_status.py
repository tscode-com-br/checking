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


def _reset_schema(db):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
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


def _seed_user_with_two_submissions(
    db,
    *,
    chave,
    action,
    earlier_event_time,
    later_event_time,
    earlier_status,
    earlier_display_status,
    later_status,
    later_display_status,
    later_last_error,
):
    """Cria um usuário com DUAS submissões da mesma `action` no mesmo dia-projeto, espelhando o duplo
    check-in real (CY22): a primeira (event_time mais antigo) é a submissão "real"; a segunda (event_time
    mais novo) é o duplicado deduplicado. A 2ª vence o desempate por event_time e vira a atividade mais
    recente, então é a vinculada à coluna Forms."""
    user = User(
        rfid=None,
        chave=chave,
        nome="Usuario Web",
        projeto="P80",
        local="Web",
        checkin=(action == "checkin"),
        time=later_event_time,
        last_active_at=later_event_time,
        inactivity_days=0,
    )
    db.add(user)
    db.flush()

    submissions = [
        (earlier_event_time, earlier_status, earlier_display_status, None, f"req-{chave}-early"),
        (later_event_time, later_status, later_display_status, later_last_error, f"req-{chave}-late"),
    ]
    for event_time, status, display_status, last_error, request_id in submissions:
        db.add(
            UserSyncEvent(
                user_id=user.id,
                chave=user.chave,
                rfid=user.rfid,
                source="web_forms",
                action=action,
                projeto="P80",
                local="Web",
                ontime=True,
                event_time=event_time,
                created_at=event_time,
                source_request_id=request_id,
                device_id=None,
            )
        )
        db.add(
            FormsSubmission(
                request_id=request_id,
                rfid=None,
                action=action,
                chave=user.chave,
                projeto="P80",
                device_id=None,
                local="Web",
                event_time=event_time,
                request_path="/api/web/check",
                display_status=display_status,
                project_candidates_json='["P80"]',
                ontime=True,
                status=status,
                retry_count=0,
                last_error=last_error,
                created_at=event_time,
                updated_at=event_time,
                processed_at=event_time if status in ("success", "failed", "skipped") else None,
            )
        )
    return user


def test_presence_rows_prefer_sent_sibling_over_skipped_duplicate_checkin():
    # Replica CY22: 1º check-in enviado (sent); 2º check-in (mais novo) deduplicado (skipped/not_realized).
    earlier = datetime(2026, 5, 21, 8, 30, microsecond=54000, tzinfo=ZoneInfo("Asia/Singapore"))
    later = datetime(2026, 5, 21, 8, 30, microsecond=118000, tzinfo=ZoneInfo("Asia/Singapore"))

    with SessionLocal() as db:
        _reset_schema(db)
        _seed_user_with_two_submissions(
            db,
            chave="CY22",
            action="checkin",
            earlier_event_time=earlier,
            later_event_time=later,
            earlier_status="success",
            earlier_display_status="sent",
            later_status="skipped",
            later_display_status="not_realized",
            later_last_error="repeated_same_action_same_day",
        )
        db.commit()

        rows, _ = build_presence_rows(db, action="checkin", current_admin=None, reference_time=later)

    assert len(rows) == 1
    assert rows[0].forms_status == "sent"


def test_presence_rows_prefer_sent_sibling_over_skipped_duplicate_checkout():
    earlier = datetime(2026, 5, 21, 17, 0, microsecond=10000, tzinfo=ZoneInfo("Asia/Singapore"))
    later = datetime(2026, 5, 21, 17, 0, microsecond=90000, tzinfo=ZoneInfo("Asia/Singapore"))

    with SessionLocal() as db:
        _reset_schema(db)
        _seed_user_with_two_submissions(
            db,
            chave="CY23",
            action="checkout",
            earlier_event_time=earlier,
            later_event_time=later,
            earlier_status="success",
            earlier_display_status="sent",
            later_status="skipped",
            later_display_status="not_realized",
            later_last_error="repeated_checkout",
        )
        db.commit()

        rows, _ = build_presence_rows(db, action="checkout", current_admin=None, reference_time=later)

    assert len(rows) == 1
    assert rows[0].forms_status == "sent"


def test_presence_rows_surface_failed_sibling_status_for_skipped_duplicate():
    earlier = datetime(2026, 5, 21, 8, 30, microsecond=54000, tzinfo=ZoneInfo("Asia/Singapore"))
    later = datetime(2026, 5, 21, 8, 30, microsecond=118000, tzinfo=ZoneInfo("Asia/Singapore"))

    with SessionLocal() as db:
        _reset_schema(db)
        _seed_user_with_two_submissions(
            db,
            chave="CY24",
            action="checkin",
            earlier_event_time=earlier,
            later_event_time=later,
            earlier_status="failed",
            earlier_display_status="aborted",
            later_status="skipped",
            later_display_status="not_realized",
            later_last_error="repeated_same_action_same_day",
        )
        db.commit()

        rows, _ = build_presence_rows(db, action="checkin", current_admin=None, reference_time=later)

    assert len(rows) == 1
    assert rows[0].forms_status == "aborted"


def test_presence_rows_surface_in_progress_sibling_status_for_skipped_duplicate():
    earlier = datetime(2026, 5, 21, 8, 30, microsecond=54000, tzinfo=ZoneInfo("Asia/Singapore"))
    later = datetime(2026, 5, 21, 8, 30, microsecond=118000, tzinfo=ZoneInfo("Asia/Singapore"))

    with SessionLocal() as db:
        _reset_schema(db)
        _seed_user_with_two_submissions(
            db,
            chave="CY25",
            action="checkin",
            earlier_event_time=earlier,
            later_event_time=later,
            earlier_status="processing",
            earlier_display_status="filling",
            later_status="skipped",
            later_display_status="not_realized",
            later_last_error="repeated_same_action_same_day",
        )
        db.commit()

        rows, _ = build_presence_rows(db, action="checkin", current_admin=None, reference_time=later)

    assert len(rows) == 1
    assert rows[0].forms_status == "filling"