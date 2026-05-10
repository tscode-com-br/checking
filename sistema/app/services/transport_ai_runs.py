from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    AdminUser,
    TransportAIRun,
    TransportAISuggestion,
    TransportAssignment,
    TransportRequest,
    TransportVehicleSchedule,
    TransportVehicleScheduleException,
    Vehicle,
)
from ..schemas import TransportAgentDashboardScope, TransportAgentPlan, TransportAgentPlanningInput
from .location_settings import get_transport_settings_payload
from .time_utils import now_sgt
from .transport_assignment_operations import upsert_transport_assignment_with_persistence
from .transport_ai_observability import record_transport_ai_lifecycle_transition
from .transport_proposals import (
    build_transport_operational_snapshot,
    build_transport_snapshot_request_scope_index,
    resolve_transport_operational_dashboard_scope,
    resolve_transport_operational_dashboard_scope_project_names,
)
from .transport_reevaluation_events import emit_transport_reevaluation_event


TRANSPORT_AI_BASELINE_VERSION = "transport_ai_baseline_v1"
TRANSPORT_AI_BASELINE_ROUTE_KINDS = ("home_to_work", "work_to_home")
TRANSPORT_AI_SUGGESTION_ACTIVE_STATUSES = ("shown", "saved")
TRANSPORT_AI_SUGGESTION_ALLOWED_STATUSES = frozenset(
    {"draft", "shown", "saved", "discarded", "applied", "expired"}
)


@dataclass(frozen=True, slots=True)
class TransportAIBaselineCapture:
    baseline_hash: str
    snapshot_payload: dict[str, Any]
    assignments_payload: dict[str, Any]
    vehicle_state_payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class TransportAIBaselineRestoreIssue:
    code: str
    message: str
    blocking: bool = True
    request_id: int | None = None
    route_kind: str | None = None
    vehicle_id: int | None = None


@dataclass(frozen=True, slots=True)
class TransportAIBaselineRestoreAuditEntry:
    action: str
    message: str
    request_id: int | None = None
    route_kind: str | None = None
    assignment_id: int | None = None


@dataclass(frozen=True, slots=True)
class TransportAIBaselineRestoreResult:
    restored_assignment_ids: list[int]
    deleted_assignment_ids: list[int]
    issues: list[TransportAIBaselineRestoreIssue]
    audit_entries: list[TransportAIBaselineRestoreAuditEntry]

    @property
    def ok(self) -> bool:
        return not any(issue.blocking for issue in self.issues)


@dataclass(frozen=True, slots=True)
class TransportAIResetToPendingResult:
    reset_request_ids: list[int]
    reset_assignment_ids: list[int]
    issues: list[TransportAIBaselineRestoreIssue]
    restore_result: TransportAIBaselineRestoreResult | None = None
    event_emitted: bool = False
    error_message: str | None = None
    duration_ms: int | None = None

    @property
    def ok(self) -> bool:
        return (
            self.error_message is None
            and not any(issue.blocking for issue in self.issues)
            and (self.restore_result is None or self.restore_result.ok)
        )


def _dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _measure_transport_ai_run_elapsed_ms(started_at: float) -> int:
    return max(0, int(round((perf_counter() - started_at) * 1000)))


def extract_transport_ai_run_llm_runtime_projects(run: TransportAIRun) -> list[dict[str, Any]]:
    planning_input_json = str(run.planning_input_json or "").strip()
    if not planning_input_json:
        return []

    try:
        payload = json.loads(planning_input_json)
    except Exception:
        return []

    snapshots = payload.get("llm_runtime_projects")
    if not isinstance(snapshots, list):
        return []

    normalized_snapshots: list[dict[str, Any]] = []
    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            continue

        provider = str(snapshot.get("provider") or "").strip().lower()
        model_name = str(snapshot.get("model_name") or "").strip()
        reasoning_effort = str(snapshot.get("reasoning_effort") or "").strip().lower()
        project_name = str(snapshot.get("project_name") or "").strip()
        project_id_value = snapshot.get("project_id")
        try:
            project_id = int(project_id_value)
        except (TypeError, ValueError):
            project_id = 0

        partition_keys = snapshot.get("partition_keys")
        if not provider or not model_name or not reasoning_effort or project_id <= 0 or not project_name:
            continue

        normalized_partition_keys = []
        if isinstance(partition_keys, list):
            normalized_partition_keys = [
                str(partition_key).strip()
                for partition_key in partition_keys
                if str(partition_key).strip()
            ]

        normalized_snapshots.append(
            {
                "project_id": project_id,
                "project_name": project_name,
                "partition_keys": normalized_partition_keys,
                "llm_provider": provider,
                "llm_model": model_name,
                "llm_reasoning_effort": reasoning_effort,
            }
        )

    return normalized_snapshots


def resolve_transport_ai_run_llm_snapshot_fields(run: TransportAIRun) -> dict[str, str]:
    runtime_projects = extract_transport_ai_run_llm_runtime_projects(run)
    if runtime_projects:
        unique_snapshots = {
            (
                snapshot["llm_provider"],
                snapshot["llm_model"],
                snapshot["llm_reasoning_effort"],
            )
            for snapshot in runtime_projects
        }
        if len(unique_snapshots) == 1:
            llm_provider, llm_model, llm_reasoning_effort = next(iter(unique_snapshots))
            return {
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "llm_reasoning_effort": llm_reasoning_effort,
                "openai_model": llm_model,
            }

        return {
            "llm_provider": "multiple",
            "llm_model": "multiple",
            "llm_reasoning_effort": "multiple",
            "openai_model": "multiple",
        }

    llm_model = str(run.llm_model or run.openai_model or "").strip()
    llm_provider = str(run.llm_provider or "").strip().lower()
    llm_reasoning_effort = str(run.llm_reasoning_effort or "").strip().lower()

    if not llm_provider:
        llm_provider = "openai" if llm_model else "unknown"
    if not llm_reasoning_effort:
        llm_reasoning_effort = "high" if llm_model else "unknown"

    return {
        "llm_provider": llm_provider,
        "llm_model": llm_model or "unknown",
        "llm_reasoning_effort": llm_reasoning_effort,
        "openai_model": llm_model or "unknown",
    }


def _parse_date(value: object, *, fallback: date | None = None) -> date | None:
    if value in {None, ""}:
        return fallback
    return date.fromisoformat(str(value))


def _parse_datetime(value: object, *, fallback: datetime | None = None) -> datetime | None:
    if value in {None, ""}:
        return fallback
    return datetime.fromisoformat(str(value))


def _serialize_transport_assignment(
    assignment: TransportAssignment,
    *,
    request_kind: str | None,
) -> dict[str, Any]:
    return {
        "id": assignment.id,
        "request_id": assignment.request_id,
        "request_kind": request_kind,
        "service_date": assignment.service_date.isoformat(),
        "route_kind": assignment.route_kind,
        "vehicle_id": assignment.vehicle_id,
        "status": assignment.status,
        "response_message": assignment.response_message,
        "boarding_time": assignment.boarding_time,
        "acknowledged_by_user": assignment.acknowledged_by_user,
        "acknowledged_at": assignment.acknowledged_at.isoformat() if assignment.acknowledged_at is not None else None,
        "assigned_by_admin_id": assignment.assigned_by_admin_id,
        "created_at": assignment.created_at.isoformat(),
        "updated_at": assignment.updated_at.isoformat(),
        "notified_at": assignment.notified_at.isoformat() if assignment.notified_at is not None else None,
    }


def _serialize_vehicle(vehicle: Vehicle) -> dict[str, Any]:
    return {
        "id": vehicle.id,
        "placa": vehicle.placa,
        "tipo": vehicle.tipo,
        "color": vehicle.color,
        "lugares": vehicle.lugares,
        "tolerance": vehicle.tolerance,
        "service_scope": vehicle.service_scope,
    }


def _serialize_transport_vehicle_schedule(schedule: TransportVehicleSchedule) -> dict[str, Any]:
    return {
        "id": schedule.id,
        "vehicle_id": schedule.vehicle_id,
        "service_scope": schedule.service_scope,
        "route_kind": schedule.route_kind,
        "recurrence_kind": schedule.recurrence_kind,
        "service_date": schedule.service_date.isoformat() if schedule.service_date is not None else None,
        "weekday": schedule.weekday,
        "departure_time": schedule.departure_time,
        "is_active": schedule.is_active,
        "created_at": schedule.created_at.isoformat(),
        "updated_at": schedule.updated_at.isoformat(),
    }


def _serialize_transport_vehicle_schedule_exception(
    schedule_exception: TransportVehicleScheduleException,
) -> dict[str, Any]:
    return {
        "id": schedule_exception.id,
        "vehicle_schedule_id": schedule_exception.vehicle_schedule_id,
        "service_date": schedule_exception.service_date.isoformat(),
        "created_at": schedule_exception.created_at.isoformat(),
    }


def _snapshot_request_rows(snapshot, *, request_rows_by_scope: dict[str, list[Any]] | None = None) -> list[Any]:
    effective_request_rows_by_scope = request_rows_by_scope or {
        "regular": list(snapshot.regular_requests),
        "weekend": list(snapshot.weekend_requests),
        "extra": list(snapshot.extra_requests),
    }
    return [
        *effective_request_rows_by_scope.get("regular", []),
        *effective_request_rows_by_scope.get("weekend", []),
        *effective_request_rows_by_scope.get("extra", []),
    ]


def ensure_transport_ai_actor_admin_user(
    db: Session,
    *,
    chave: str,
    nome_completo: str,
    ensured_at: datetime | None = None,
) -> AdminUser:
    timestamp = ensured_at or now_sgt()
    normalized_chave = str(chave or "").strip().upper()
    normalized_nome = " ".join(str(nome_completo or "").strip().split()) or normalized_chave

    admin_user = db.execute(select(AdminUser).where(AdminUser.chave == normalized_chave)).scalar_one_or_none()
    if admin_user is None:
        admin_user = AdminUser(
            chave=normalized_chave,
            nome_completo=normalized_nome,
            password_hash=None,
            requires_password_reset=False,
            approved_by_admin_id=None,
            approved_at=None,
            password_reset_requested_at=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(admin_user)
    elif admin_user.nome_completo != normalized_nome:
        admin_user.nome_completo = normalized_nome
        admin_user.updated_at = timestamp

    db.flush()
    return admin_user


def save_transport_ai_planning_input(
    transport_ai_run: TransportAIRun,
    *,
    planning_input: TransportAgentPlanningInput,
    saved_at: datetime | None = None,
) -> TransportAIRun:
    timestamp = saved_at or now_sgt()
    transport_ai_run.planning_input_json = _dump_json(planning_input.model_dump(mode="json"))
    transport_ai_run.planning_input_hash = planning_input.planning_input_hash
    transport_ai_run.price_currency_code = planning_input.settings.price_currency_code
    transport_ai_run.price_rate_unit = planning_input.settings.price_rate_unit
    transport_ai_run.preflight_issues_json = _dump_json(
        [issue.model_dump(mode="json") for issue in planning_input.preflight_issues]
    )
    transport_ai_run.updated_at = timestamp
    return transport_ai_run


def _collect_relevant_vehicle_ids(*, snapshot, assignments: list[TransportAssignment]) -> list[int]:
    vehicle_ids: set[int] = set()

    for vehicle_row in [
        *snapshot.regular_vehicles,
        *snapshot.weekend_vehicles,
        *snapshot.extra_vehicles,
    ]:
        vehicle_ids.add(vehicle_row.id)

    for management_row in [
        *snapshot.regular_vehicle_registry,
        *snapshot.weekend_vehicle_registry,
        *snapshot.extra_vehicle_registry,
    ]:
        vehicle_ids.add(management_row.vehicle_id)

    for request_row in _snapshot_request_rows(snapshot):
        if request_row.assigned_vehicle is not None:
            vehicle_ids.add(request_row.assigned_vehicle.id)

    for assignment in assignments:
        if assignment.vehicle_id is not None:
            vehicle_ids.add(assignment.vehicle_id)

    return sorted(vehicle_ids)


def capture_transport_ai_baseline(
    db: Session,
    *,
    service_date: date,
    route_kind: str,
    actor_user_id: int,
    dashboard_scope: TransportAgentDashboardScope | None = None,
    captured_at: datetime | None = None,
) -> TransportAIBaselineCapture:
    effective_captured_at = captured_at or now_sgt()
    snapshot = build_transport_operational_snapshot(
        db,
        service_date=service_date,
        route_kind=route_kind,
        captured_at=effective_captured_at,
    )
    effective_dashboard_scope = resolve_transport_operational_dashboard_scope(
        snapshot,
        dashboard_scope=dashboard_scope,
    )
    dashboard_scope_project_names = resolve_transport_operational_dashboard_scope_project_names(
        snapshot,
        dashboard_scope=effective_dashboard_scope,
    )
    scoped_request_rows_by_scope = build_transport_snapshot_request_scope_index(
        snapshot,
        dashboard_scope=dashboard_scope,
    )
    snapshot_request_rows = _snapshot_request_rows(
        snapshot,
        request_rows_by_scope=scoped_request_rows_by_scope,
    )
    request_kind_by_id = {
        request_row.id: request_row.request_kind
        for request_row in snapshot_request_rows
    }
    dashboard_scope_payload = (
        effective_dashboard_scope.model_dump(mode="json")
        if effective_dashboard_scope is not None
        else None
    )
    eligible_requests = [
        {
            "request_id": request_row.id,
            "request_kind": request_row.request_kind,
            "service_date": request_row.service_date.isoformat(),
            "user_id": request_row.user_id,
            "assignment_status": request_row.assignment_status,
        }
        for request_row in sorted(snapshot_request_rows, key=lambda row: (row.id, row.service_date, row.request_kind))
    ]
    request_ids = sorted(request_kind_by_id)

    assignments: list[TransportAssignment] = []
    if request_ids:
        assignments = db.execute(
            select(TransportAssignment)
            .where(
                TransportAssignment.request_id.in_(request_ids),
                TransportAssignment.service_date == service_date,
                TransportAssignment.route_kind.in_(TRANSPORT_AI_BASELINE_ROUTE_KINDS),
            )
            .order_by(
                TransportAssignment.request_id.asc(),
                TransportAssignment.service_date.asc(),
                TransportAssignment.route_kind.asc(),
                TransportAssignment.id.asc(),
            )
        ).scalars().all()

    relevant_vehicle_ids = _collect_relevant_vehicle_ids(snapshot=snapshot, assignments=assignments)
    vehicles: list[Vehicle] = []
    schedules: list[TransportVehicleSchedule] = []
    schedule_exceptions: list[TransportVehicleScheduleException] = []

    if relevant_vehicle_ids:
        vehicles = db.execute(
            select(Vehicle)
            .where(Vehicle.id.in_(relevant_vehicle_ids))
            .order_by(Vehicle.id.asc())
        ).scalars().all()
        schedules = db.execute(
            select(TransportVehicleSchedule)
            .where(TransportVehicleSchedule.vehicle_id.in_(relevant_vehicle_ids))
            .order_by(
                TransportVehicleSchedule.vehicle_id.asc(),
                TransportVehicleSchedule.route_kind.asc(),
                TransportVehicleSchedule.recurrence_kind.asc(),
                TransportVehicleSchedule.id.asc(),
            )
        ).scalars().all()

        schedule_ids = [schedule.id for schedule in schedules]
        if schedule_ids:
            schedule_exceptions = db.execute(
                select(TransportVehicleScheduleException)
                .where(
                    TransportVehicleScheduleException.vehicle_schedule_id.in_(schedule_ids),
                    TransportVehicleScheduleException.service_date == service_date,
                )
                .order_by(
                    TransportVehicleScheduleException.vehicle_schedule_id.asc(),
                    TransportVehicleScheduleException.service_date.asc(),
                    TransportVehicleScheduleException.id.asc(),
                )
            ).scalars().all()

    snapshot_payload = {
        "baseline_version": TRANSPORT_AI_BASELINE_VERSION,
        "captured_at": effective_captured_at.isoformat(),
        "service_date": service_date.isoformat(),
        "route_kind": route_kind,
        "actor_user_id": actor_user_id,
        "dashboard_scope": dashboard_scope_payload,
        "dashboard_scope_project_names": dashboard_scope_project_names,
        "settings": get_transport_settings_payload(db),
        "snapshot": snapshot.model_dump(mode="json"),
    }
    assignments_payload = {
        "baseline_version": TRANSPORT_AI_BASELINE_VERSION,
        "captured_at": effective_captured_at.isoformat(),
        "service_date": service_date.isoformat(),
        "route_kind": route_kind,
        "actor_user_id": actor_user_id,
        "dashboard_scope": dashboard_scope_payload,
        "dashboard_scope_project_names": dashboard_scope_project_names,
        "eligible_requests": eligible_requests,
        "assignments": [
            _serialize_transport_assignment(
                assignment,
                request_kind=request_kind_by_id.get(assignment.request_id),
            )
            for assignment in assignments
        ],
    }
    vehicle_state_payload = {
        "baseline_version": TRANSPORT_AI_BASELINE_VERSION,
        "captured_at": effective_captured_at.isoformat(),
        "service_date": service_date.isoformat(),
        "route_kind": route_kind,
        "actor_user_id": actor_user_id,
        "dashboard_scope": dashboard_scope_payload,
        "dashboard_scope_project_names": dashboard_scope_project_names,
        "relevant_vehicle_ids": relevant_vehicle_ids,
        "vehicles": [_serialize_vehicle(vehicle) for vehicle in vehicles],
        "schedules": [_serialize_transport_vehicle_schedule(schedule) for schedule in schedules],
        "schedule_exceptions": [
            _serialize_transport_vehicle_schedule_exception(schedule_exception)
            for schedule_exception in schedule_exceptions
        ],
    }

    baseline_hash = hashlib.sha256(
        _dump_json(
            {
                "snapshot": snapshot_payload,
                "assignments": assignments_payload,
                "vehicle_state": vehicle_state_payload,
            }
        ).encode("utf-8")
    ).hexdigest()

    snapshot_payload["baseline_hash"] = baseline_hash
    assignments_payload["baseline_hash"] = baseline_hash
    vehicle_state_payload["baseline_hash"] = baseline_hash

    return TransportAIBaselineCapture(
        baseline_hash=baseline_hash,
        snapshot_payload=snapshot_payload,
        assignments_payload=assignments_payload,
        vehicle_state_payload=vehicle_state_payload,
    )


def save_transport_ai_baseline(
    db: Session,
    *,
    run: TransportAIRun,
    baseline_capture: TransportAIBaselineCapture,
    saved_at: datetime | None = None,
) -> TransportAIRun:
    timestamp = saved_at or now_sgt()
    run.baseline_snapshot_json = _dump_json(baseline_capture.snapshot_payload)
    run.baseline_assignments_json = _dump_json(baseline_capture.assignments_payload)
    run.baseline_vehicle_state_json = _dump_json(baseline_capture.vehicle_state_payload)
    run.status = "baseline_saved"
    run.updated_at = timestamp
    db.flush()
    return run


def _issue_message(
    *,
    code: str,
    message: str,
    request_id: int | None = None,
    route_kind: str | None = None,
    vehicle_id: int | None = None,
) -> TransportAIBaselineRestoreIssue:
    return TransportAIBaselineRestoreIssue(
        code=code,
        message=message,
        blocking=True,
        request_id=request_id,
        route_kind=route_kind,
        vehicle_id=vehicle_id,
    )


def _load_baseline_restore_payloads(
    run: TransportAIRun,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, list[TransportAIBaselineRestoreIssue]]:
    issues: list[TransportAIBaselineRestoreIssue] = []

    def _load_payload(raw_value: str | None, *, field_name: str) -> dict[str, Any] | None:
        if raw_value is None:
            return None
        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError:
            issues.append(
                _issue_message(
                    code="baseline_payload_invalid",
                    message=f"{field_name} contains invalid JSON and cannot be restored.",
                )
            )
            return None
        if not isinstance(payload, dict):
            issues.append(
                _issue_message(
                    code="baseline_payload_invalid",
                    message=f"{field_name} must deserialize to an object payload.",
                )
            )
            return None
        return payload

    snapshot_payload = _load_payload(run.baseline_snapshot_json, field_name="baseline_snapshot_json")
    assignments_payload = _load_payload(run.baseline_assignments_json, field_name="baseline_assignments_json")
    vehicle_state_payload = _load_payload(run.baseline_vehicle_state_json, field_name="baseline_vehicle_state_json")

    if assignments_payload is None:
        issues.append(
            _issue_message(
                code="baseline_assignments_missing",
                message="The run does not have a restorable baseline_assignments_json payload.",
            )
        )
        return snapshot_payload, assignments_payload, vehicle_state_payload, issues

    baseline_version = assignments_payload.get("baseline_version")
    if baseline_version != TRANSPORT_AI_BASELINE_VERSION:
        issues.append(
            _issue_message(
                code="baseline_version_unsupported",
                message=(
                    f"Unsupported baseline version {baseline_version!r}; expected {TRANSPORT_AI_BASELINE_VERSION!r}."
                ),
            )
        )

    assignments_hash = assignments_payload.get("baseline_hash")
    for field_name, payload in (
        ("baseline_snapshot_json", snapshot_payload),
        ("baseline_vehicle_state_json", vehicle_state_payload),
    ):
        if payload is None:
            continue
        payload_hash = payload.get("baseline_hash")
        if assignments_hash is not None and payload_hash is not None and payload_hash != assignments_hash:
            issues.append(
                _issue_message(
                    code="baseline_hash_mismatch",
                    message=f"{field_name} does not match baseline_assignments_json and cannot be trusted.",
                )
            )

    payload_service_date = _parse_date(assignments_payload.get("service_date"), fallback=run.service_date)
    if payload_service_date != run.service_date:
        issues.append(
            _issue_message(
                code="baseline_service_date_mismatch",
                message="The baseline service_date does not match the current run and cannot be restored safely.",
            )
        )

    payload_route_kind = str(assignments_payload.get("route_kind") or run.route_kind)
    if payload_route_kind != run.route_kind:
        issues.append(
            _issue_message(
                code="baseline_route_kind_mismatch",
                message="The baseline route_kind does not match the current run and cannot be restored safely.",
            )
        )

    return snapshot_payload, assignments_payload, vehicle_state_payload, issues


def restore_transport_ai_baseline(
    db: Session,
    *,
    run: TransportAIRun,
    actor_user_id: int | None = None,
    restored_at: datetime | None = None,
) -> TransportAIBaselineRestoreResult:
    timestamp = restored_at or now_sgt()
    audit_entries: list[TransportAIBaselineRestoreAuditEntry] = []
    restored_assignment_ids: list[int] = []
    deleted_assignment_ids: list[int] = []

    _, assignments_payload, _, issues = _load_baseline_restore_payloads(run)
    if assignments_payload is None or issues:
        return TransportAIBaselineRestoreResult(
            restored_assignment_ids=restored_assignment_ids,
            deleted_assignment_ids=deleted_assignment_ids,
            issues=issues,
            audit_entries=audit_entries,
        )

    baseline_service_date = _parse_date(assignments_payload.get("service_date"), fallback=run.service_date)
    if baseline_service_date is None:
        issues.append(
            _issue_message(
                code="baseline_service_date_missing",
                message="The baseline service_date is missing and cannot be restored.",
            )
        )
        return TransportAIBaselineRestoreResult(
            restored_assignment_ids=restored_assignment_ids,
            deleted_assignment_ids=deleted_assignment_ids,
            issues=issues,
            audit_entries=audit_entries,
        )

    eligible_requests_payload = assignments_payload.get("eligible_requests") or []
    baseline_assignments_payload = assignments_payload.get("assignments") or []
    eligible_request_ids = sorted(
        {
            int(request_payload["request_id"])
            for request_payload in eligible_requests_payload
            if isinstance(request_payload, dict) and request_payload.get("request_id") is not None
        }
    )
    transport_requests_by_id = {
        transport_request.id: transport_request
        for transport_request in db.execute(
            select(TransportRequest)
            .where(TransportRequest.id.in_(eligible_request_ids))
            .order_by(TransportRequest.id.asc())
        ).scalars().all()
    } if eligible_request_ids else {}

    missing_request_ids = [
        request_id
        for request_id in eligible_request_ids
        if request_id not in transport_requests_by_id
    ]
    for request_id in missing_request_ids:
        issues.append(
            _issue_message(
                code="baseline_request_missing",
                message=f"Transport request {request_id} no longer exists and blocks baseline restore.",
                request_id=request_id,
            )
        )

    baseline_assignments_by_key: dict[tuple[int, str], dict[str, Any]] = {}
    for assignment_payload in baseline_assignments_payload:
        if not isinstance(assignment_payload, dict):
            issues.append(
                _issue_message(
                    code="baseline_assignment_invalid",
                    message="The baseline assignments payload contains a non-object assignment entry.",
                )
            )
            continue

        request_id = assignment_payload.get("request_id")
        route_kind = assignment_payload.get("route_kind")
        if request_id is None or route_kind is None:
            issues.append(
                _issue_message(
                    code="baseline_assignment_invalid",
                    message="The baseline assignments payload contains an entry without request_id or route_kind.",
                )
            )
            continue

        assignment_key = (int(request_id), str(route_kind))
        if assignment_key in baseline_assignments_by_key:
            issues.append(
                _issue_message(
                    code="baseline_assignment_duplicate",
                    message=(
                        f"The baseline assignments payload contains duplicated assignment key {assignment_key!r}."
                    ),
                    request_id=int(request_id),
                    route_kind=str(route_kind),
                )
            )
            continue
        baseline_assignments_by_key[assignment_key] = assignment_payload

    confirmed_vehicle_ids = sorted(
        {
            int(assignment_payload["vehicle_id"])
            for assignment_payload in baseline_assignments_by_key.values()
            if assignment_payload.get("status") == "confirmed" and assignment_payload.get("vehicle_id") is not None
        }
    )
    vehicles_by_id = {
        vehicle.id: vehicle
        for vehicle in db.execute(
            select(Vehicle)
            .where(Vehicle.id.in_(confirmed_vehicle_ids))
            .order_by(Vehicle.id.asc())
        ).scalars().all()
    } if confirmed_vehicle_ids else {}

    for assignment_key, assignment_payload in baseline_assignments_by_key.items():
        request_id, route_kind = assignment_key
        status = str(assignment_payload.get("status") or "").strip().lower()
        vehicle_id = assignment_payload.get("vehicle_id")

        if request_id not in transport_requests_by_id:
            continue
        if status == "confirmed" and vehicle_id is None:
            issues.append(
                _issue_message(
                    code="baseline_assignment_invalid",
                    message=(
                        f"Baseline assignment for request {request_id} and route {route_kind} is confirmed without vehicle_id."
                    ),
                    request_id=request_id,
                    route_kind=route_kind,
                )
            )
        if status == "confirmed" and vehicle_id is not None and int(vehicle_id) not in vehicles_by_id:
            issues.append(
                _issue_message(
                    code="baseline_vehicle_missing",
                    message=(
                        f"Vehicle {vehicle_id} from the baseline no longer exists and blocks restore for request {request_id}."
                    ),
                    request_id=request_id,
                    route_kind=route_kind,
                    vehicle_id=int(vehicle_id),
                )
            )

    if issues:
        return TransportAIBaselineRestoreResult(
            restored_assignment_ids=restored_assignment_ids,
            deleted_assignment_ids=deleted_assignment_ids,
            issues=issues,
            audit_entries=audit_entries,
        )

    current_assignments = db.execute(
        select(TransportAssignment)
        .where(
            TransportAssignment.request_id.in_(eligible_request_ids),
            TransportAssignment.service_date == baseline_service_date,
            TransportAssignment.route_kind.in_(TRANSPORT_AI_BASELINE_ROUTE_KINDS),
        )
        .order_by(
            TransportAssignment.request_id.asc(),
            TransportAssignment.route_kind.asc(),
            TransportAssignment.id.asc(),
        )
    ).scalars().all() if eligible_request_ids else []
    current_assignments_by_key = {
        (assignment.request_id, assignment.route_kind): assignment
        for assignment in current_assignments
    }

    for assignment_key, current_assignment in current_assignments_by_key.items():
        if assignment_key in baseline_assignments_by_key:
            continue
        deleted_assignment_ids.append(current_assignment.id)
        audit_entries.append(
            TransportAIBaselineRestoreAuditEntry(
                action="deleted",
                message=(
                    f"Deleted assignment {current_assignment.id} because it was not present in the captured baseline."
                ),
                request_id=current_assignment.request_id,
                route_kind=current_assignment.route_kind,
                assignment_id=current_assignment.id,
            )
        )
        db.delete(current_assignment)

    effective_actor_user_id = actor_user_id if actor_user_id is not None else run.actor_user_id

    for assignment_key in sorted(baseline_assignments_by_key):
        request_id, route_kind = assignment_key
        assignment_payload = baseline_assignments_by_key[assignment_key]
        existing_assignment = current_assignments_by_key.get(assignment_key)
        target_status = str(assignment_payload.get("status") or "pending").strip().lower()
        target_vehicle_id = assignment_payload.get("vehicle_id")
        target_assignment_id = existing_assignment.id if existing_assignment is not None else None
        target_vehicle = vehicles_by_id.get(int(target_vehicle_id)) if target_vehicle_id is not None else None
        target_created_at = _parse_datetime(assignment_payload.get("created_at"), fallback=timestamp) or timestamp
        target_updated_at = _parse_datetime(assignment_payload.get("updated_at"), fallback=timestamp) or timestamp
        target_acknowledged_at = _parse_datetime(assignment_payload.get("acknowledged_at"))
        target_notified_at = _parse_datetime(assignment_payload.get("notified_at"))
        target_assignment = existing_assignment
        if target_assignment is None:
            target_assignment = TransportAssignment(
                request_id=request_id,
                service_date=_parse_date(assignment_payload.get("service_date"), fallback=baseline_service_date) or baseline_service_date,
                route_kind=route_kind,
                vehicle_id=target_vehicle.id if target_vehicle is not None else None,
                status=target_status,
                response_message=assignment_payload.get("response_message"),
                boarding_time=assignment_payload.get("boarding_time"),
                acknowledged_by_user=bool(assignment_payload.get("acknowledged_by_user")),
                acknowledged_at=target_acknowledged_at,
                assigned_by_admin_id=assignment_payload.get("assigned_by_admin_id"),
                created_at=target_created_at,
                updated_at=target_updated_at,
                notified_at=target_notified_at,
            )
            db.add(target_assignment)
            db.flush()
            target_assignment_id = target_assignment.id
            audit_entries.append(
                TransportAIBaselineRestoreAuditEntry(
                    action="created",
                    message=(
                        f"Recreated assignment for request {request_id} and route {route_kind} from the captured baseline."
                    ),
                    request_id=request_id,
                    route_kind=route_kind,
                    assignment_id=target_assignment_id,
                )
            )
        else:
            target_assignment.service_date = _parse_date(
                assignment_payload.get("service_date"),
                fallback=baseline_service_date,
            ) or baseline_service_date
            target_assignment.route_kind = route_kind
            target_assignment.vehicle_id = target_vehicle.id if target_vehicle is not None else None
            target_assignment.status = target_status
            target_assignment.response_message = assignment_payload.get("response_message")
            target_assignment.boarding_time = assignment_payload.get("boarding_time")
            target_assignment.acknowledged_by_user = bool(assignment_payload.get("acknowledged_by_user"))
            target_assignment.acknowledged_at = target_acknowledged_at
            target_assignment.assigned_by_admin_id = assignment_payload.get("assigned_by_admin_id")
            target_assignment.created_at = target_created_at
            target_assignment.updated_at = target_updated_at
            target_assignment.notified_at = target_notified_at
            target_assignment_id = target_assignment.id
            audit_entries.append(
                TransportAIBaselineRestoreAuditEntry(
                    action="updated",
                    message=(
                        f"Restored assignment {target_assignment.id} for request {request_id} and route {route_kind}."
                    ),
                    request_id=request_id,
                    route_kind=route_kind,
                    assignment_id=target_assignment_id,
                )
            )

        if effective_actor_user_id is not None:
            target_assignment.assigned_by_admin_id = effective_actor_user_id
        restored_assignment_ids.append(target_assignment.id)

    db.flush()
    return TransportAIBaselineRestoreResult(
        restored_assignment_ids=restored_assignment_ids,
        deleted_assignment_ids=deleted_assignment_ids,
        issues=issues,
        audit_entries=audit_entries,
    )


def reset_transport_ai_requests_to_pending(
    db: Session,
    *,
    run: TransportAIRun,
    actor_user_id: int | None = None,
    reset_at: datetime | None = None,
) -> TransportAIResetToPendingResult:
    reset_started_at = perf_counter()
    timestamp = reset_at or now_sgt()
    _, assignments_payload, _, issues = _load_baseline_restore_payloads(run)
    if assignments_payload is None or issues:
        return TransportAIResetToPendingResult(
            reset_request_ids=[],
            reset_assignment_ids=[],
            issues=issues,
            duration_ms=_measure_transport_ai_run_elapsed_ms(reset_started_at),
        )

    baseline_service_date = _parse_date(assignments_payload.get("service_date"), fallback=run.service_date)
    if baseline_service_date is None:
        issues = [
            *issues,
            _issue_message(
                code="baseline_service_date_missing",
                message="The baseline service_date is missing and cannot be used to reset requests to pending.",
            ),
        ]
        return TransportAIResetToPendingResult(
            reset_request_ids=[],
            reset_assignment_ids=[],
            issues=issues,
            duration_ms=_measure_transport_ai_run_elapsed_ms(reset_started_at),
        )

    target_route_kind = str(assignments_payload.get("route_kind") or run.route_kind)
    eligible_requests_payload = assignments_payload.get("eligible_requests") or []
    if not isinstance(eligible_requests_payload, list):
        issues = [
            *issues,
            _issue_message(
                code="baseline_eligible_requests_invalid",
                message="The baseline eligible_requests payload is invalid and cannot drive the reset.",
            ),
        ]
        return TransportAIResetToPendingResult(
            reset_request_ids=[],
            reset_assignment_ids=[],
            issues=issues,
            duration_ms=_measure_transport_ai_run_elapsed_ms(reset_started_at),
        )

    reset_request_ids = sorted(
        {
            int(request_payload["request_id"])
            for request_payload in eligible_requests_payload
            if isinstance(request_payload, dict) and request_payload.get("request_id") is not None
        }
    )
    transport_requests_by_id = {
        transport_request.id: transport_request
        for transport_request in db.execute(
            select(TransportRequest)
            .where(TransportRequest.id.in_(reset_request_ids))
            .order_by(TransportRequest.id.asc())
        ).scalars().all()
    } if reset_request_ids else {}

    missing_request_ids = [
        request_id
        for request_id in reset_request_ids
        if request_id not in transport_requests_by_id
    ]
    for request_id in missing_request_ids:
        issues.append(
            _issue_message(
                code="baseline_request_missing",
                message=f"Transport request {request_id} no longer exists and blocks reset to pending.",
                request_id=request_id,
            )
        )
    if issues:
        return TransportAIResetToPendingResult(
            reset_request_ids=reset_request_ids,
            reset_assignment_ids=[],
            issues=issues,
            duration_ms=_measure_transport_ai_run_elapsed_ms(reset_started_at),
        )

    effective_actor_user_id = actor_user_id if actor_user_id is not None else run.actor_user_id
    reset_assignment_ids: list[int] = []
    savepoint = db.begin_nested()
    try:
        for request_id in reset_request_ids:
            assignment, _ = upsert_transport_assignment_with_persistence(
                db,
                transport_request=transport_requests_by_id[request_id],
                service_date=baseline_service_date,
                route_kind=target_route_kind,
                status="pending",
                vehicle=None,
                response_message="transport_ai_reset_to_pending",
                admin_user_id=effective_actor_user_id,
                pending_reset_scope="service_date_route",
            )
            reset_assignment_ids.append(assignment.id)

        run.status = "passengers_reset"
        run.updated_at = timestamp
        db.flush()
        record_transport_ai_lifecycle_transition(
            db,
            stage="passengers_reset",
            run=run,
            request_path="/api/transport/ai/route-calculations",
            extra_details={
                "reset_request_count": len(reset_request_ids),
                "reset_assignment_count": len(reset_assignment_ids),
                "reset_duration_ms": _measure_transport_ai_run_elapsed_ms(reset_started_at),
            },
        )
        emit_transport_reevaluation_event(
            event_type="transport_assignment_changed",
            reason="event",
            source="transport_admin",
            message="Transport AI reset eligible requests to pending for route calculation.",
            service_date=baseline_service_date,
            route_kind=target_route_kind,
        )
        savepoint.commit()
        return TransportAIResetToPendingResult(
            reset_request_ids=reset_request_ids,
            reset_assignment_ids=reset_assignment_ids,
            issues=[],
            event_emitted=True,
            duration_ms=_measure_transport_ai_run_elapsed_ms(reset_started_at),
        )
    except Exception as exc:
        savepoint.rollback()
        restore_result: TransportAIBaselineRestoreResult | None = None
        restore_error_message: str | None = None
        try:
            restore_result = restore_transport_ai_baseline(
                db,
                run=run,
                actor_user_id=effective_actor_user_id,
                restored_at=timestamp,
            )
        except Exception as restore_exc:
            restore_error_message = str(restore_exc)

        error_message = str(exc)
        if restore_error_message:
            error_message = f"{error_message} Baseline restore also failed: {restore_error_message}"
        return TransportAIResetToPendingResult(
            reset_request_ids=reset_request_ids,
            reset_assignment_ids=[],
            issues=[],
            restore_result=restore_result,
            event_emitted=False,
            error_message=error_message,
            duration_ms=_measure_transport_ai_run_elapsed_ms(reset_started_at),
        )


def _validate_transport_ai_suggestion_status(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if normalized not in TRANSPORT_AI_SUGGESTION_ALLOWED_STATUSES:
        raise ValueError(f"Unsupported transport AI suggestion status: {status!r}")
    return normalized


def create_transport_ai_suggestion(
    db: Session,
    *,
    run: TransportAIRun,
    suggestion_key: str,
    proposal_key: str | None,
    agent_plan_json: str,
    transport_proposal_json: str,
    vehicle_actions_json: str,
    assignment_actions_json: str,
    route_itineraries_json: str,
    change_summary_json: str,
    cost_summary_json: str,
    validation_issues_json: str,
    prompt_version: str,
    raw_model_response_json: str | None = None,
    status: str = "shown",
    created_at: datetime | None = None,
) -> TransportAISuggestion:
    timestamp = created_at or now_sgt()
    resolved_status = _validate_transport_ai_suggestion_status(status)
    suggestion = TransportAISuggestion(
        suggestion_key=suggestion_key,
        run_id=run.id,
        service_date=run.service_date,
        route_kind=run.route_kind,
        proposal_key=proposal_key,
        status=resolved_status,
        agent_plan_json=agent_plan_json,
        transport_proposal_json=transport_proposal_json,
        vehicle_actions_json=vehicle_actions_json,
        assignment_actions_json=assignment_actions_json,
        route_itineraries_json=route_itineraries_json,
        change_summary_json=change_summary_json,
        cost_summary_json=cost_summary_json,
        validation_issues_json=validation_issues_json,
        raw_model_response_json=raw_model_response_json,
        prompt_version=prompt_version,
        created_at=timestamp,
        updated_at=timestamp,
        saved_at=timestamp if resolved_status == "saved" else None,
        applied_at=timestamp if resolved_status == "applied" else None,
        discarded_at=timestamp if resolved_status == "discarded" else None,
    )
    db.add(suggestion)
    db.flush()
    return suggestion


def create_transport_ai_suggestion_from_plan(
    db: Session,
    *,
    run: TransportAIRun,
    plan: TransportAgentPlan,
    prompt_version: str,
    raw_model_response_json: str | None = None,
    suggestion_key: str | None = None,
    proposal_key: str | None = None,
    status: str = "shown",
    created_at: datetime | None = None,
) -> TransportAISuggestion:
    effective_timestamp = created_at or now_sgt()
    effective_suggestion_key = suggestion_key or f"transport-ai-suggestion:{uuid4().hex}"
    effective_proposal_key = proposal_key or f"transport-ai-proposal:{run.run_key}"
    validation_issues_payload = [issue.model_dump(mode="json") for issue in plan.validation_issues]
    assignment_actions_payload = [
        allocation.model_dump(mode="json")
        for allocation in plan.passenger_allocations
    ]
    transport_proposal_payload = {
        "proposal_key": effective_proposal_key,
        "proposal_origin": "agent",
        "service_date": run.service_date.isoformat(),
        "route_kind": run.route_kind,
        "decisions": assignment_actions_payload,
        "validation_issues": validation_issues_payload,
    }

    return create_transport_ai_suggestion(
        db,
        run=run,
        suggestion_key=effective_suggestion_key,
        proposal_key=effective_proposal_key,
        agent_plan_json=_dump_json(plan.model_dump(mode="json")),
        transport_proposal_json=_dump_json(transport_proposal_payload),
        vehicle_actions_json=_dump_json([action.model_dump(mode="json") for action in plan.vehicle_actions]),
        assignment_actions_json=_dump_json(assignment_actions_payload),
        route_itineraries_json=_dump_json([
            itinerary.model_dump(mode="json")
            for itinerary in plan.route_itineraries
        ]),
        change_summary_json=_dump_json(plan.change_summary.model_dump(mode="json")),
        cost_summary_json=_dump_json(plan.cost_summary.model_dump(mode="json")),
        validation_issues_json=_dump_json(validation_issues_payload),
        prompt_version=prompt_version,
        raw_model_response_json=raw_model_response_json,
        status=status,
        created_at=effective_timestamp,
    )


def set_transport_ai_suggestion_status(
    db: Session,
    *,
    suggestion: TransportAISuggestion,
    status: str,
    changed_at: datetime | None = None,
) -> TransportAISuggestion:
    timestamp = changed_at or now_sgt()
    resolved_status = _validate_transport_ai_suggestion_status(status)
    suggestion.status = resolved_status
    suggestion.updated_at = timestamp

    if resolved_status == "saved":
        suggestion.saved_at = timestamp
    elif resolved_status == "applied":
        suggestion.applied_at = timestamp
    elif resolved_status == "discarded":
        suggestion.discarded_at = timestamp

    db.flush()
    return suggestion


def get_latest_saved_transport_ai_suggestion(
    db: Session,
    *,
    service_date: date,
    route_kind: str,
) -> TransportAISuggestion | None:
    return db.execute(
        select(TransportAISuggestion)
        .where(
            TransportAISuggestion.service_date == service_date,
            TransportAISuggestion.route_kind == route_kind,
            TransportAISuggestion.status == "saved",
        )
        .order_by(TransportAISuggestion.saved_at.desc(), TransportAISuggestion.updated_at.desc(), TransportAISuggestion.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_latest_active_transport_ai_suggestion(
    db: Session,
    *,
    service_date: date,
    route_kind: str,
) -> TransportAISuggestion | None:
    return db.execute(
        select(TransportAISuggestion)
        .where(
            TransportAISuggestion.service_date == service_date,
            TransportAISuggestion.route_kind == route_kind,
            TransportAISuggestion.status.in_(TRANSPORT_AI_SUGGESTION_ACTIVE_STATUSES),
        )
        .order_by(TransportAISuggestion.updated_at.desc(), TransportAISuggestion.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_transport_ai_suggestion_by_key(
    db: Session,
    *,
    suggestion_key: str,
) -> TransportAISuggestion | None:
    return db.execute(
        select(TransportAISuggestion)
        .where(TransportAISuggestion.suggestion_key == suggestion_key)
        .limit(1)
    ).scalar_one_or_none()


def get_latest_transport_ai_suggestion_for_run(
    db: Session,
    *,
    run_id: int,
) -> TransportAISuggestion | None:
    return db.execute(
        select(TransportAISuggestion)
        .where(TransportAISuggestion.run_id == run_id)
        .order_by(TransportAISuggestion.updated_at.desc(), TransportAISuggestion.id.desc())
        .limit(1)
    ).scalar_one_or_none()