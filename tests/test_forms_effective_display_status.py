"""Testes unitários (sem DB) do helper puro que resolve o display_status EFETIVO quando a submissão
vinculada à atividade mais recente é um skip deduplicado (temp005 / Prompt 1).

Regra: considerar APENAS as irmãs não-skip; escolher por prioridade de ciclo de vida
success(4) > failed(3) > processing(2) > pending(1), desempatando por processed_at, depois event_time,
depois submission_id (mais recente vence); devolver o display_status da escolhida. Sem irmã não-skip → None.
"""
from datetime import datetime, timezone

from sistema.app.services.forms_queue import (
    FORMS_SUBMISSION_STATUS_PRIORITY,
    FormsSiblingCandidate,
    resolve_effective_skipped_display_status,
)


def _dt(microsecond: int) -> datetime:
    return datetime(2026, 5, 21, 8, 30, microsecond=microsecond, tzinfo=timezone.utc)


def test_empty_candidates_returns_none():
    assert resolve_effective_skipped_display_status([]) is None


def test_only_skipped_candidates_returns_none():
    candidates = [
        FormsSiblingCandidate(
            status="skipped",
            display_status="not_realized",
            processed_at=_dt(118000),
            event_time=_dt(118000),
            submission_id=2,
        ),
        FormsSiblingCandidate(
            status="skipped",
            display_status="not_realized",
            processed_at=_dt(54000),
            event_time=_dt(54000),
            submission_id=1,
        ),
    ]
    assert resolve_effective_skipped_display_status(candidates) is None


def test_success_sibling_wins_over_skipped_duplicate():
    candidates = [
        FormsSiblingCandidate(
            status="success",
            display_status="sent",
            processed_at=_dt(54000),
            event_time=_dt(54000),
            submission_id=1,
        ),
        FormsSiblingCandidate(
            status="skipped",
            display_status="not_realized",
            processed_at=_dt(118000),
            event_time=_dt(118000),
            submission_id=2,
        ),
    ]
    assert resolve_effective_skipped_display_status(candidates) == "sent"


def test_failed_sibling_surfaces_its_display_status():
    candidates = [
        FormsSiblingCandidate(
            status="failed",
            display_status="aborted",
            processed_at=_dt(54000),
            event_time=_dt(54000),
            submission_id=1,
        ),
        FormsSiblingCandidate(
            status="skipped",
            display_status="not_realized",
            processed_at=_dt(118000),
            event_time=_dt(118000),
            submission_id=2,
        ),
    ]
    assert resolve_effective_skipped_display_status(candidates) == "aborted"


def test_in_progress_sibling_surfaces_its_display_status():
    candidates = [
        FormsSiblingCandidate(
            status="processing",
            display_status="filling",
            processed_at=None,
            event_time=_dt(54000),
            submission_id=1,
        ),
        FormsSiblingCandidate(
            status="skipped",
            display_status="not_realized",
            processed_at=_dt(118000),
            event_time=_dt(118000),
            submission_id=2,
        ),
    ]
    assert resolve_effective_skipped_display_status(candidates) == "filling"


def test_lifecycle_priority_prefers_success_over_lower_states_even_if_older():
    # success é prioridade máxima mesmo sendo mais antigo que um processing mais recente.
    candidates = [
        FormsSiblingCandidate(
            status="processing",
            display_status="filling",
            processed_at=_dt(900000),
            event_time=_dt(900000),
            submission_id=9,
        ),
        FormsSiblingCandidate(
            status="success",
            display_status="sent",
            processed_at=_dt(100000),
            event_time=_dt(100000),
            submission_id=1,
        ),
    ]
    assert resolve_effective_skipped_display_status(candidates) == "sent"


def test_tiebreak_same_status_prefers_most_recent_processed_at():
    candidates = [
        FormsSiblingCandidate(
            status="failed",
            display_status="aborted",
            processed_at=_dt(100000),
            event_time=_dt(100000),
            submission_id=1,
        ),
        FormsSiblingCandidate(
            status="failed",
            display_status="not_found",
            processed_at=_dt(800000),
            event_time=_dt(800000),
            submission_id=2,
        ),
    ]
    assert resolve_effective_skipped_display_status(candidates) == "not_found"


def test_priority_table_ordering_is_well_defined():
    assert (
        FORMS_SUBMISSION_STATUS_PRIORITY["success"]
        > FORMS_SUBMISSION_STATUS_PRIORITY["failed"]
        > FORMS_SUBMISSION_STATUS_PRIORITY["processing"]
        > FORMS_SUBMISSION_STATUS_PRIORITY["pending"]
        > FORMS_SUBMISSION_STATUS_PRIORITY["skipped"]
    )
