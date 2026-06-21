"""TP5 case 7 — unsupported-project isolation in the FORMS worker.

Each project is its OWN FormsSubmission row with `project_candidates=[project]`, and `_process_submission`
handles one row at a time. So an UnsupportedProject failure for one project marks ONLY its row failed and
leaves the other project's submission untouched. The browser is mocked at the worker boundary
(`submit_with_retries`); the real Playwright automation never runs.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_checking.db")
os.environ.setdefault("FORMS_URL", "https://example.com/form")
os.environ.setdefault("DEVICE_SHARED_KEY", "device-test-key")
os.environ.setdefault("MOBILE_APP_SHARED_KEY", "mobile-test-key")
os.environ.setdefault("PROVIDER_SHARED_KEY", "TESTPROVIDER0001")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-admin-session-secret")
os.environ.setdefault("BOOTSTRAP_ADMIN_KEY", "HR70")
os.environ.setdefault("BOOTSTRAP_ADMIN_NAME", "Tamer Salmem")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "eAcacdLe2")
os.environ.setdefault("FORMS_QUEUE_ENABLED", "false")
os.environ.setdefault("TRANSPORT_EXPORTS_DIR", "./test_transport_exports")

from sistema.app.database import Base, SessionLocal, engine  # noqa: E402
from sistema.app.models import FormsSubmission  # noqa: E402
from sistema.app.services import forms_worker as forms_worker_module  # noqa: E402
from sistema.app.services.forms_queue import _process_submission  # noqa: E402

Base.metadata.create_all(bind=engine)

_NOW = datetime(2026, 6, 18, 10, 0, 0, tzinfo=timezone.utc)


def _fake_submit_with_retries(self, *, action, chave, projeto, ontime, project_candidates, status_callback):
    # Mock the browser boundary: PXX has no Forms xpath mapping → fails; everything else succeeds.
    if projeto == "PXX":
        return {
            "success": False,
            "message": "Nenhum projeto suportado no Forms para esta submissao: PXX",
            "retry_count": 0,
            "error_code": "unsupported_project",
            "audit_events": [],
        }
    return {"success": True, "message": "ok", "retry_count": 0, "audit_events": []}


def _seed_processing(request_id: str, projeto: str) -> int:
    with SessionLocal() as db:
        row = FormsSubmission(
            request_id=request_id, rfid=None, action="checkout", chave="WK01", projeto=projeto,
            device_id="checking-android", local="Escritório", event_time=None,
            request_path="/api/web/check", display_status=None,
            project_candidates_json=json.dumps([projeto]), ontime=True,
            status="processing", retry_count=0, last_error=None,
            created_at=_NOW, updated_at=_NOW, processed_at=None,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id


def test_unsupported_project_fails_only_its_own_row(monkeypatch):
    monkeypatch.setattr(
        forms_worker_module.FormsWorker, "submit_with_retries", _fake_submit_with_retries
    )
    p80_id = _seed_processing("ev-iso:P80", "P80")  # supported
    pxx_id = _seed_processing("ev-iso:PXX", "PXX")  # unsupported (no xpath mapping)

    _process_submission(p80_id)
    _process_submission(pxx_id)

    with SessionLocal() as db:
        p80 = db.get(FormsSubmission, p80_id)
        pxx = db.get(FormsSubmission, pxx_id)

    # PXX fails on its own; P80 succeeds and is completely unaffected.
    assert p80.status == "success"
    assert p80.last_error is None
    assert pxx.status == "failed"
    assert pxx.last_error is not None
