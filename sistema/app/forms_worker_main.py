from __future__ import annotations

from .core.config import settings
from .database import Base, engine
from .services.event_archives import ensure_event_archives_dir
from .services.forms_queue import (
    reclaim_orphaned_processing_submissions,
    run_forms_submission_worker_forever,
    write_forms_worker_disabled_snapshot,
)
from .services.project_catalog import seed_default_projects


def main() -> int:
    if not settings.forms_queue_enabled:
        write_forms_worker_disabled_snapshot()
        return 0

    ensure_event_archives_dir()
    if settings.app_env == "development":
        Base.metadata.create_all(bind=engine)
    seed_default_projects()
    # Reclaim rows stranded in 'processing' by a previous process that crashed or was recycled
    # mid-flight, so they get retried instead of showing FORMS "-" in the admin forever.
    reclaim_orphaned_processing_submissions()
    run_forms_submission_worker_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())