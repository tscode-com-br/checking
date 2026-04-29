from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from ..models import TransportRequest, Vehicle
from ..schemas import (
    TransportOperationalAppliedAssignment,
    TransportOperationalProposal,
    TransportOperationalProposalSummary,
    TransportOperationalSnapshot,
    TransportIdentity,
    TransportProposalAuditContext,
    TransportProposalAuditEntry,
    TransportProposalAuditResult,
    TransportProposalDecision,
    TransportProposalValidationIssue,
)
from .time_utils import now_sgt
from .transport_assignment_operations import upsert_transport_assignment_with_persistence
from .transport_dashboard_queries import build_transport_dashboard


def _count_snapshot_requests(snapshot: TransportOperationalSnapshot) -> int:
    return len(snapshot.regular_requests) + len(snapshot.weekend_requests) + len(snapshot.extra_requests)


def _count_snapshot_vehicles(snapshot: TransportOperationalSnapshot) -> int:
    return len(snapshot.regular_vehicles) + len(snapshot.weekend_vehicles) + len(snapshot.extra_vehicles)


def _snapshot_request_index(snapshot: TransportOperationalSnapshot) -> dict[int, object]:
    rows = snapshot.regular_requests + snapshot.weekend_requests + snapshot.extra_requests
    return {row.id: row for row in rows}


def _snapshot_vehicle_registry_index(snapshot: TransportOperationalSnapshot) -> dict[int, object]:
    rows = (
        snapshot.regular_vehicle_registry
        + snapshot.weekend_vehicle_registry
        + snapshot.extra_vehicle_registry
    )
    return {row.vehicle_id: row for row in rows}


def _build_validation_issue(
    *,
    code: str,
    message: str,
    request_id: int | None = None,
    vehicle_id: int | None = None,
) -> TransportProposalValidationIssue:
    return TransportProposalValidationIssue(
        code=code,
        message=message,
        blocking=True,
        request_id=request_id,
        vehicle_id=vehicle_id,
    )


def _build_audit_entry(
    *,
    action: str,
    outcome: str,
    actor: TransportIdentity,
    occurred_at: datetime,
    message: str,
    proposal: TransportOperationalProposal,
    evaluation_snapshot: TransportOperationalSnapshot | None = None,
    issues: list[TransportProposalValidationIssue] | None = None,
    applied_assignments: list[TransportOperationalAppliedAssignment] | None = None,
    proposal_status: str | None = None,
) -> TransportProposalAuditEntry:
    effective_issues = list(issues or [])
    effective_applied_assignments = list(applied_assignments or [])
    return TransportProposalAuditEntry(
        audit_entry_key=f"transport-proposal-audit:{uuid4().hex}",
        action=action,
        outcome=outcome,
        actor=actor,
        occurred_at=occurred_at,
        message=message,
        context=_build_audit_context(
            proposal,
            evaluation_snapshot=evaluation_snapshot,
        ),
        result=_build_audit_result(
            proposal,
            issues=effective_issues,
            applied_assignments=effective_applied_assignments,
            proposal_status=proposal_status,
        ),
    )


def _build_audit_context(
    proposal: TransportOperationalProposal,
    *,
    evaluation_snapshot: TransportOperationalSnapshot | None = None,
) -> TransportProposalAuditContext:
    return TransportProposalAuditContext(
        proposal_key=proposal.proposal_key,
        proposal_origin=proposal.origin,
        proposal_snapshot_key=proposal.snapshot.snapshot_key,
        evaluation_snapshot_key=(evaluation_snapshot.snapshot_key if evaluation_snapshot is not None else proposal.snapshot.snapshot_key),
        service_date=proposal.snapshot.service_date,
        route_kind=proposal.snapshot.route_kind,
        total_decisions=proposal.summary.total_decisions,
        confirmed_decisions=proposal.summary.confirmed_decisions,
        rejected_decisions=proposal.summary.rejected_decisions,
        pending_decisions=proposal.summary.pending_decisions,
        decision_request_ids=sorted({decision.request_id for decision in proposal.decisions}),
        decision_vehicle_ids=sorted({decision.vehicle_id for decision in proposal.decisions if decision.vehicle_id is not None}),
        replaces_proposal_key=proposal.replaces_proposal_key,
    )


def _build_audit_result(
    proposal: TransportOperationalProposal,
    *,
    issues: list[TransportProposalValidationIssue] | None = None,
    applied_assignments: list[TransportOperationalAppliedAssignment] | None = None,
    proposal_status: str | None = None,
) -> TransportProposalAuditResult:
    effective_issues = list(issues or [])
    effective_applied_assignments = list(applied_assignments or [])
    return TransportProposalAuditResult(
        proposal_status=proposal_status or proposal.proposal_status,
        validation_issue_count=len(effective_issues),
        validation_issue_codes=[issue.code for issue in effective_issues],
        applied_assignment_count=len(effective_applied_assignments),
        applied_assignment_ids=[assignment.assignment_id for assignment in effective_applied_assignments],
    )


def proposal_has_blocking_issues(proposal: TransportOperationalProposal) -> bool:
    return any(issue.blocking for issue in proposal.validation_issues)


def _collect_proposal_validation_issues(
    *,
    proposal: TransportOperationalProposal,
    current_snapshot: TransportOperationalSnapshot,
) -> list[TransportProposalValidationIssue]:
    issues: list[TransportProposalValidationIssue] = []
    seen_request_ids: set[int] = set()
    proposed_confirmations: Counter[int] = Counter()

    proposal_request_index = _snapshot_request_index(proposal.snapshot)
    current_request_index = _snapshot_request_index(current_snapshot)
    proposal_vehicle_registry = _snapshot_vehicle_registry_index(proposal.snapshot)
    current_vehicle_registry = _snapshot_vehicle_registry_index(current_snapshot)

    if proposal.proposal_status == "applied":
        issues.append(
            _build_validation_issue(
                code="proposal_already_applied",
                message="Applied proposals cannot be validated or approved again.",
            )
        )

    for decision in proposal.decisions:
        if decision.request_id in seen_request_ids:
            issues.append(
                _build_validation_issue(
                    code="duplicate_request_decision",
                    message=f"Request {decision.request_id} appears more than once in the proposal.",
                    request_id=decision.request_id,
                )
            )
            continue

        seen_request_ids.add(decision.request_id)

        if decision.service_date != proposal.snapshot.service_date:
            issues.append(
                _build_validation_issue(
                    code="decision_service_date_mismatch",
                    message=(
                        f"Request {decision.request_id} targets {decision.service_date.isoformat()}, but the proposal "
                        f"snapshot is for {proposal.snapshot.service_date.isoformat()}."
                    ),
                    request_id=decision.request_id,
                )
            )

        if decision.route_kind != proposal.snapshot.route_kind:
            issues.append(
                _build_validation_issue(
                    code="decision_route_mismatch",
                    message=(
                        f"Request {decision.request_id} targets route {decision.route_kind}, but the proposal "
                        f"snapshot is for {proposal.snapshot.route_kind}."
                    ),
                    request_id=decision.request_id,
                )
            )

        proposal_request = proposal_request_index.get(decision.request_id)
        if proposal_request is None:
            issues.append(
                _build_validation_issue(
                    code="request_missing_from_snapshot",
                    message=f"Request {decision.request_id} is not present in the proposal snapshot.",
                    request_id=decision.request_id,
                )
            )
        elif proposal_request.request_kind != decision.request_kind:
            issues.append(
                _build_validation_issue(
                    code="request_kind_mismatch",
                    message=(
                        f"Request {decision.request_id} is {proposal_request.request_kind} in the snapshot, "
                        f"but the decision declares {decision.request_kind}."
                    ),
                    request_id=decision.request_id,
                )
            )

        current_request = current_request_index.get(decision.request_id)
        if current_request is None:
            issues.append(
                _build_validation_issue(
                    code="request_no_longer_available",
                    message=(
                        f"Request {decision.request_id} is no longer available for "
                        f"{proposal.snapshot.service_date.isoformat()} {proposal.snapshot.route_kind}."
                    ),
                    request_id=decision.request_id,
                )
            )
        else:
            if current_request.request_kind != decision.request_kind:
                issues.append(
                    _build_validation_issue(
                        code="current_request_kind_mismatch",
                        message=(
                            f"Request {decision.request_id} is currently classified as {current_request.request_kind}, "
                            f"not {decision.request_kind}."
                        ),
                        request_id=decision.request_id,
                    )
                )

            if current_request.assignment_status != "pending":
                issues.append(
                    _build_validation_issue(
                        code="request_not_pending",
                        message=(
                            f"Request {decision.request_id} is currently {current_request.assignment_status} and can no "
                            f"longer be approved from this proposal."
                        ),
                        request_id=decision.request_id,
                    )
                )

        if decision.suggested_status != "confirmed":
            continue

        if decision.vehicle_id not in proposal_vehicle_registry:
            issues.append(
                _build_validation_issue(
                    code="vehicle_missing_from_snapshot",
                    message=(
                        f"Vehicle {decision.vehicle_id} is not present in the proposal snapshot for "
                        f"{proposal.snapshot.route_kind}."
                    ),
                    request_id=decision.request_id,
                    vehicle_id=decision.vehicle_id,
                )
            )

        current_vehicle = current_vehicle_registry.get(decision.vehicle_id)
        if current_vehicle is None:
            issues.append(
                _build_validation_issue(
                    code="vehicle_unavailable",
                    message=(
                        f"Vehicle {decision.vehicle_id} is not currently available for "
                        f"{proposal.snapshot.service_date.isoformat()} {proposal.snapshot.route_kind}."
                    ),
                    request_id=decision.request_id,
                    vehicle_id=decision.vehicle_id,
                )
            )
            continue

        if not current_vehicle.is_ready_for_allocation:
            issues.append(
                _build_validation_issue(
                    code="vehicle_not_ready_for_allocation",
                    message=(
                        f"Vehicle {decision.vehicle_id} is missing operational data and is not ready for allocation."
                    ),
                    request_id=decision.request_id,
                    vehicle_id=decision.vehicle_id,
                )
            )
            continue

        proposed_confirmations[decision.vehicle_id] += 1

    for vehicle_id, proposed_count in proposed_confirmations.items():
        current_vehicle = current_vehicle_registry.get(vehicle_id)
        if current_vehicle is None:
            continue

        projected_assignment_count = current_vehicle.assigned_count + proposed_count
        if projected_assignment_count > current_vehicle.lugares:
            issues.append(
                _build_validation_issue(
                    code="vehicle_capacity_exceeded",
                    message=(
                        f"Vehicle {vehicle_id} would reach {projected_assignment_count} passengers, exceeding its "
                        f"capacity of {current_vehicle.lugares}."
                    ),
                    vehicle_id=vehicle_id,
                )
            )

    return issues


def _clone_proposal_with_review_state(
    proposal: TransportOperationalProposal,
    *,
    validation_issues: list[TransportProposalValidationIssue] | None = None,
    audit_entry: TransportProposalAuditEntry | None = None,
    proposal_status: str | None = None,
) -> TransportOperationalProposal:
    updated_audit_trail = list(proposal.audit_trail)
    if audit_entry is not None:
        updated_audit_trail.append(audit_entry)

    return proposal.model_copy(
        update={
            "proposal_status": proposal_status or proposal.proposal_status,
            "validation_issues": list(proposal.validation_issues if validation_issues is None else validation_issues),
            "audit_trail": updated_audit_trail,
        },
        deep=True,
    )


def build_transport_operational_snapshot(
    db: Session,
    *,
    service_date: date,
    route_kind: str,
    captured_at: datetime | None = None,
) -> TransportOperationalSnapshot:
    dashboard = build_transport_dashboard(
        db,
        service_date=service_date,
        route_kind=route_kind,
    )
    effective_captured_at = captured_at or now_sgt()
    dashboard_data = dashboard.model_dump(exclude={"selected_date", "selected_route"})
    return TransportOperationalSnapshot(
        snapshot_key=(
            f"transport-snapshot:{dashboard.selected_date.isoformat()}:{dashboard.selected_route}:"
            f"{effective_captured_at.isoformat()}"
        ),
        service_date=dashboard.selected_date,
        route_kind=dashboard.selected_route,
        captured_at=effective_captured_at,
        **dashboard_data,
    )


def build_transport_operational_proposal_summary(
    *,
    snapshot: TransportOperationalSnapshot,
    decisions: list[TransportProposalDecision],
) -> TransportOperationalProposalSummary:
    decision_counts = Counter(decision.suggested_status for decision in decisions)
    return TransportOperationalProposalSummary(
        total_snapshot_requests=_count_snapshot_requests(snapshot),
        total_snapshot_vehicles=_count_snapshot_vehicles(snapshot),
        total_decisions=len(decisions),
        confirmed_decisions=decision_counts.get("confirmed", 0),
        rejected_decisions=decision_counts.get("rejected", 0),
        pending_decisions=decision_counts.get("pending", 0),
    )


def build_transport_operational_proposal(
    *,
    snapshot: TransportOperationalSnapshot,
    origin: str,
    replaces_proposal_key: str | None = None,
    decisions: list[TransportProposalDecision] | None = None,
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
    proposal_status: str = "draft",
    proposal_key: str | None = None,
) -> TransportOperationalProposal:
    effective_decisions = list(decisions or [])
    effective_created_at = created_at or now_sgt()
    return TransportOperationalProposal(
        proposal_key=proposal_key or f"transport-proposal:{uuid4().hex}",
        proposal_status=proposal_status,
        origin=origin,
        replaces_proposal_key=replaces_proposal_key,
        created_at=effective_created_at,
        expires_at=expires_at,
        snapshot=snapshot,
        decisions=effective_decisions,
        summary=build_transport_operational_proposal_summary(
            snapshot=snapshot,
            decisions=effective_decisions,
        ),
    )


def build_transport_operational_proposal_contract(
    db: Session,
    *,
    service_date: date,
    route_kind: str,
    origin: str,
    actor: TransportIdentity,
    replaces_proposal_key: str | None = None,
    decisions: list[TransportProposalDecision] | None = None,
    captured_at: datetime | None = None,
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> TransportOperationalProposal:
    snapshot = build_transport_operational_snapshot(
        db,
        service_date=service_date,
        route_kind=route_kind,
        captured_at=captured_at,
    )
    proposal = build_transport_operational_proposal(
        snapshot=snapshot,
        origin=origin,
        replaces_proposal_key=replaces_proposal_key,
        decisions=decisions,
        created_at=created_at,
        expires_at=expires_at,
    )
    return proposal.model_copy(
        update={
            "audit_trail": [
                _build_audit_entry(
                    action="generated",
                    outcome="generated",
                    actor=actor,
                    occurred_at=proposal.created_at,
                    message=(
                        "Proposal regenerated from a previous proposal context."
                        if replaces_proposal_key
                        else "Proposal generated from an operational snapshot."
                    ),
                    proposal=proposal,
                    evaluation_snapshot=snapshot,
                    proposal_status="draft",
                )
            ]
        },
        deep=True,
    )


def _validate_transport_operational_proposal_with_snapshot(
    db: Session,
    *,
    proposal: TransportOperationalProposal,
    actor: TransportIdentity,
    validated_at: datetime,
) -> tuple[TransportOperationalProposal, TransportOperationalSnapshot]:
    current_snapshot = build_transport_operational_snapshot(
        db,
        service_date=proposal.snapshot.service_date,
        route_kind=proposal.snapshot.route_kind,
        captured_at=validated_at,
    )
    issues = _collect_proposal_validation_issues(proposal=proposal, current_snapshot=current_snapshot)
    message = (
        f"Proposal validation found {len(issues)} blocking issue(s)."
        if issues
        else "Proposal validation passed without blocking issues."
    )
    return (
        _clone_proposal_with_review_state(
            proposal,
            validation_issues=issues,
            audit_entry=_build_audit_entry(
                action="validated",
                outcome="blocked" if issues else "passed",
                actor=actor,
                occurred_at=validated_at,
                message=message,
                proposal=proposal,
                evaluation_snapshot=current_snapshot,
                issues=issues,
                proposal_status=proposal.proposal_status,
            ),
        ),
        current_snapshot,
    )


def validate_transport_operational_proposal(
    db: Session,
    *,
    proposal: TransportOperationalProposal,
    actor: TransportIdentity,
    validated_at: datetime | None = None,
) -> TransportOperationalProposal:
    effective_validated_at = validated_at or now_sgt()
    validated_proposal, _ = _validate_transport_operational_proposal_with_snapshot(
        db,
        proposal=proposal,
        actor=actor,
        validated_at=effective_validated_at,
    )
    return validated_proposal


def approve_transport_operational_proposal(
    db: Session,
    *,
    proposal: TransportOperationalProposal,
    actor: TransportIdentity,
    approved_at: datetime | None = None,
) -> TransportOperationalProposal:
    effective_approved_at = approved_at or now_sgt()
    validated_proposal, current_snapshot = _validate_transport_operational_proposal_with_snapshot(
        db,
        proposal=proposal,
        actor=actor,
        validated_at=effective_approved_at,
    )

    issues = list(validated_proposal.validation_issues)
    if validated_proposal.proposal_status != "draft":
        issues.append(
            _build_validation_issue(
                code="proposal_not_draft",
                message=(
                    f"Only draft proposals can be approved. Current status is "
                    f"{validated_proposal.proposal_status}."
                ),
            )
        )
        validated_proposal = validated_proposal.model_copy(
            update={"validation_issues": issues},
            deep=True,
        )

    if issues:
        return _clone_proposal_with_review_state(
            validated_proposal,
            audit_entry=_build_audit_entry(
                action="approved",
                outcome="blocked",
                actor=actor,
                occurred_at=effective_approved_at,
                message="Proposal approval was blocked by validation issues.",
                proposal=validated_proposal,
                evaluation_snapshot=current_snapshot,
                issues=issues,
                proposal_status=validated_proposal.proposal_status,
            ),
        )

    return _clone_proposal_with_review_state(
        validated_proposal,
        proposal_status="approved",
        audit_entry=_build_audit_entry(
            action="approved",
            outcome="approved",
            actor=actor,
            occurred_at=effective_approved_at,
            message="Proposal approved without applying transport assignments.",
            proposal=validated_proposal,
            evaluation_snapshot=current_snapshot,
            proposal_status="approved",
        ),
    )


def reject_transport_operational_proposal(
    *,
    proposal: TransportOperationalProposal,
    actor: TransportIdentity,
    message: str | None = None,
    rejected_at: datetime | None = None,
) -> TransportOperationalProposal:
    effective_rejected_at = rejected_at or now_sgt()
    return _clone_proposal_with_review_state(
        proposal,
        proposal_status="rejected",
        audit_entry=_build_audit_entry(
            action="rejected",
            outcome="rejected",
            actor=actor,
            occurred_at=effective_rejected_at,
            message=message or "Proposal rejected before assignment application.",
            proposal=proposal,
            proposal_status="rejected",
        ),
    )


def _block_transport_operational_proposal_application(
    proposal: TransportOperationalProposal,
    *,
    issues: list[TransportProposalValidationIssue],
    actor: TransportIdentity,
    applied_at: datetime,
    message: str,
    evaluation_snapshot: TransportOperationalSnapshot,
) -> TransportOperationalProposal:
    proposal_with_issues = proposal.model_copy(
        update={"validation_issues": issues},
        deep=True,
    )
    return _clone_proposal_with_review_state(
        proposal_with_issues,
        audit_entry=_build_audit_entry(
            action="applied",
            outcome="blocked",
            actor=actor,
            occurred_at=applied_at,
            message=message,
            proposal=proposal_with_issues,
            evaluation_snapshot=evaluation_snapshot,
            issues=issues,
            proposal_status=proposal_with_issues.proposal_status,
        ),
    )


def apply_transport_operational_proposal(
    db: Session,
    *,
    proposal: TransportOperationalProposal,
    actor: TransportIdentity,
    applied_at: datetime | None = None,
) -> tuple[TransportOperationalProposal, list[TransportOperationalAppliedAssignment]]:
    effective_applied_at = applied_at or now_sgt()
    validated_proposal, current_snapshot = _validate_transport_operational_proposal_with_snapshot(
        db,
        proposal=proposal,
        actor=actor,
        validated_at=effective_applied_at,
    )

    issues = list(validated_proposal.validation_issues)
    if validated_proposal.proposal_status != "approved":
        issues.append(
            _build_validation_issue(
                code="proposal_not_approved_for_application",
                message="Only approved proposals can be applied to transport assignments.",
            )
        )

    prepared_decisions: list[tuple[TransportProposalDecision, TransportRequest, Vehicle | None]] = []
    for decision in validated_proposal.decisions:
        transport_request = db.get(TransportRequest, decision.request_id)
        if transport_request is None:
            issues.append(
                _build_validation_issue(
                    code="request_missing_during_application",
                    message=f"Request {decision.request_id} could not be loaded for proposal application.",
                    request_id=decision.request_id,
                    vehicle_id=decision.vehicle_id,
                )
            )
            continue

        vehicle = None
        if decision.vehicle_id is not None:
            vehicle = db.get(Vehicle, decision.vehicle_id)
            if vehicle is None:
                issues.append(
                    _build_validation_issue(
                        code="vehicle_missing_during_application",
                        message=f"Vehicle {decision.vehicle_id} could not be loaded for proposal application.",
                        request_id=decision.request_id,
                        vehicle_id=decision.vehicle_id,
                    )
                )
                continue

        prepared_decisions.append((decision, transport_request, vehicle))

    if issues:
        return (
            _block_transport_operational_proposal_application(
                validated_proposal,
                issues=issues,
                actor=actor,
                applied_at=effective_applied_at,
                message="Proposal application was blocked by validation issues.",
                evaluation_snapshot=current_snapshot,
            ),
            [],
        )

    applied_assignments: list[TransportOperationalAppliedAssignment] = []
    for decision, transport_request, vehicle in prepared_decisions:
        assignment, is_update = upsert_transport_assignment_with_persistence(
            db,
            transport_request=transport_request,
            service_date=decision.service_date,
            route_kind=decision.route_kind,
            status=decision.suggested_status,
            vehicle=vehicle,
            response_message=decision.response_message,
            admin_user_id=actor.id,
        )
        applied_assignments.append(
            TransportOperationalAppliedAssignment(
                assignment_id=assignment.id,
                request_id=assignment.request_id,
                service_date=assignment.service_date,
                route_kind=assignment.route_kind,
                status=assignment.status,
                vehicle_id=assignment.vehicle_id,
                was_update=is_update,
            )
        )

    applied_proposal = _clone_proposal_with_review_state(
        validated_proposal,
        proposal_status="applied",
        audit_entry=_build_audit_entry(
            action="applied",
            outcome="applied",
            actor=actor,
            occurred_at=effective_applied_at,
            message=f"Proposal applied to {len(applied_assignments)} transport assignment(s).",
            proposal=validated_proposal,
            evaluation_snapshot=current_snapshot,
            applied_assignments=applied_assignments,
            proposal_status="applied",
        ),
    )
    return applied_proposal, applied_assignments
