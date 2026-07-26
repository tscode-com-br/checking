"""LGPD art. 18, VI (eliminação) — user-initiated self-deletion of a Check-Web account.

A worker can remove their own account + personal data from the app ("Remover Cadastro"). This is a
SUPERSET of the admin ``remove_user`` (which only clears a few tables and would raise a Postgres
ForeignKeyViolation for any user who ever touched an accident/email/call): every ``users.id`` FK on the
accident/email/call/transport/sync tables was created with NO ondelete (NO ACTION in Postgres), so the
children must be removed/anonymized FIRST, in order, or ``DELETE FROM users`` blocks. Dev is SQLite with
foreign_keys off, so this passes in dev and would explode in prod — the exact trap CLAUDE.md documents;
``tests/services/test_account_deletion.py`` runs with FKs ON to catch it.

Scope decisions (see [assert_user_can_self_delete]): admins, users who OPENED an accident, and users in
an OPEN accident are NOT self-deletable in-app — they are routed to the privacy channel (art. 18, §4 lets
the controller state a reason preventing immediate action). Accidents are shared, retained safety records
(a CHECK forbids nulling the opener), so a single user leaving must never tear one down.
"""
from __future__ import annotations

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from ..models import (
    Accident,
    AccidentCallLog,
    AccidentCallNotification,
    AccidentUserReport,
    AccidentVideoUpload,
    AdminAccessRequest,
    AdminUser,
    CheckEvent,
    CheckingHistory,
    EmailDeliveryLog,
    FormsSubmission,
    PendingRegistration,
    PendingUserRegistration,
    TransportAIAppliedRouteStop,
    TransportAIRoutePoint,
    TransportAssignment,
    TransportRequest,
    User,
    UserSyncEvent,
)
from .admin_auth import user_has_admin_access

PRIVACY_CHANNEL_EMAIL = "tscode.com.br@gmail.com"


class AccountDeletionBlocked(Exception):
    """A self-deletion cannot proceed for a documented reason. ``code`` is machine-readable; ``message``
    is a user-facing pt-BR explanation the endpoint returns as HTTP 409 detail."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def assert_user_can_self_delete(db: Session, user: User) -> None:
    """Raise [AccountDeletionBlocked] if this user must not self-delete in-app. Call BEFORE any write."""
    # 1) Admins: an admin has an admin_users mirror + *_by_admin_id / actor_user_id audit FKs (several NOT
    #    NULL) and is subject to the "only remaining admin" guard. Out of scope for in-app self-service.
    if user_has_admin_access(user):
        raise AccountDeletionBlocked(
            "admin",
            "Contas com acesso administrativo não podem ser removidas pelo aplicativo. "
            f"Solicite a remoção pelo canal de privacidade ({PRIVACY_CHANNEL_EMAIL}).",
        )

    # 2) Live emergency: never tear down (or partially erase) a user who is part of an OPEN accident — the
    #    admin's live situation table/archive depends on it (art. 18, §4 — legitimate reason to defer).
    active = db.execute(
        select(Accident.id)
        .where(Accident.closed_at.is_(None))
        .where(
            or_(
                Accident.opened_by_user_id == user.id,
                Accident.id.in_(
                    select(AccidentUserReport.accident_id).where(AccidentUserReport.user_id == user.id)
                ),
                # A user may participate in a live accident via a video upload WITHOUT a report row
                # (attach_video_upload doesn't create one) — never erase that mid-emergency either.
                Accident.id.in_(
                    select(AccidentVideoUpload.accident_id).where(AccidentVideoUpload.user_id == user.id)
                ),
            )
        )
        .limit(1)
    ).first()
    if active is not None:
        raise AccountDeletionBlocked(
            "active_accident",
            "Há um acidente em aberto envolvendo sua conta. A remoção ficará disponível "
            "após o encerramento do acidente.",
        )

    # 3) Opener of ANY accident (open or closed): CHECK ck_accidents_opened_by_actor_required forbids
    #    nulling the opener, and the accident (+ its archive) is a retained legal/safety record shared by
    #    many users — it must not be deleted just because the opener leaves. Route to the privacy channel.
    opened = db.execute(
        select(Accident.id).where(Accident.opened_by_user_id == user.id).limit(1)
    ).first()
    if opened is not None:
        raise AccountDeletionBlocked(
            "accident_opener",
            "Sua conta consta como responsável pela abertura de um registro de acidente, mantido por "
            f"obrigação legal. Solicite a remoção pelo canal de privacidade ({PRIVACY_CHANNEL_EMAIL}).",
        )


def delete_user_account(db: Session, user: User) -> list[str]:
    """Delete all of ``user``'s personal data, in FK-safe order. Does NOT commit — the caller owns the
    transaction. Call [assert_user_can_self_delete] first. Returns the object-storage keys of the user's
    accident videos so the caller can delete them AFTER a successful commit (deleting objects mid-txn
    would leave dangling media if the transaction later rolls back).

    Known residuals (not reached by a user-id/chave/rfid delete): the transport-AI planning snapshots
    (transport_ai_runs / transport_ai_suggestions JSON blobs) aggregate MANY passengers, so a single
    leaver's name/address embedded there is not deleted here (deleting the shared record would erase other
    passengers' data); transport_ai_route_matrices is a hash-keyed, TTL-expiring coordinate cache. These
    are handled via the privacy channel on request (art. 18, §4). The accident row + its archive are
    likewise retained as a shared safety record. Everything directly keyed to the user IS erased below.
    """
    uid = user.id
    rfid = user.rfid
    chave = user.chave

    # --- Transport chain (children first — transport_requests.user_id is NO ACTION) ---
    request_ids = db.execute(
        select(TransportRequest.id).where(TransportRequest.user_id == uid)
    ).scalars().all()
    if request_ids:
        db.execute(delete(TransportAssignment).where(TransportAssignment.request_id.in_(request_ids)))
        db.execute(delete(TransportRequest).where(TransportRequest.user_id == uid))
    # Home-address-level PII keyed by a bare user_id (no FK, won't block, but nothing cascades it):
    # the applied route stops and the geocode cache point for this passenger's home origin.
    db.execute(delete(TransportAIAppliedRouteStop).where(TransportAIAppliedRouteStop.user_id == uid))
    db.execute(
        delete(TransportAIRoutePoint).where(
            TransportAIRoutePoint.point_type == "passenger_origin",
            TransportAIRoutePoint.source_id == uid,
        )
    )

    # --- Accident participation in CLOSED accidents (active + opener already guarded) ---
    # Capture the video object keys to delete from storage AFTER commit; the accident row + its frozen
    # archive survive as the retained emergency record.
    video_object_keys = [
        key
        for key in db.execute(
            select(AccidentVideoUpload.object_key).where(AccidentVideoUpload.user_id == uid)
        ).scalars().all()
        if key
    ]
    db.execute(delete(AccidentVideoUpload).where(AccidentVideoUpload.user_id == uid))
    db.execute(delete(AccidentUserReport).where(AccidentUserReport.user_id == uid))

    # --- Emergency audit trail: anonymize, don't delete (retain the incident record; drop the user link
    #     AND scrub the free-text body/recipient that carries the user's name + chave). triggered_by_user_id
    #     is NO ACTION → must be nulled to unblock the users delete. ---
    db.execute(
        update(EmailDeliveryLog)
        .where(EmailDeliveryLog.triggered_by_user_id == uid)
        .values(triggered_by_user_id=None, body_snapshot="")
    )
    db.execute(
        update(EmailDeliveryLog)
        .where(EmailDeliveryLog.recipient_chave == chave)
        .values(recipient_chave=None, recipient_email="", body_snapshot="")
    )
    # AccidentCallNotification holds a rendered pt-BR sentence that embeds the
    # triggering user's name and chave (twilio_caller._format_notification_message_pt).
    # Nulling triggered_by_user_id below does not reach it, so the name kept showing
    # in the admin's notification feed after the account was erased. Scrub the text,
    # keep the row: same rule already applied to EmailDeliveryLog.body_snapshot.
    # Must run BEFORE the update that clears triggered_by_user_id.
    user_call_log_ids = db.execute(
        select(AccidentCallLog.id).where(AccidentCallLog.triggered_by_user_id == uid)
    ).scalars().all()
    if user_call_log_ids:
        db.execute(
            update(AccidentCallNotification)
            .where(AccidentCallNotification.call_log_id.in_(user_call_log_ids))
            .values(message_pt="(dados do solicitante removidos a pedido do titular)")
        )
    db.execute(
        update(AccidentCallLog)
        .where(AccidentCallLog.triggered_by_user_id == uid)
        .values(triggered_by_user_id=None)
    )

    # --- Sync events (user_sync_events.user_id is NO ACTION → delete before users) ---
    db.execute(delete(UserSyncEvent).where(UserSyncEvent.user_id == uid))

    # --- No-FK PII tables (won't block, but no cascade reaches them; keyed by rfid/chave, captured above) ---
    # CheckEvent.rfid holds the card id for device flows but the user's *chave* for
    # every web flow — including all accident endpoints (web_check.py logs
    # rfid=user.chave). Deleting by rfid alone left the entire web trail behind, and
    # web-created users have rfid = NULL, so for them nothing was deleted at all.
    check_event_keys = {key for key in (rfid, chave) if key}
    if check_event_keys:
        db.execute(delete(CheckEvent).where(CheckEvent.rfid.in_(check_event_keys)))
    if rfid:
        db.execute(delete(PendingRegistration).where(PendingRegistration.rfid == rfid))
        db.execute(delete(FormsSubmission).where(or_(FormsSubmission.chave == chave, FormsSubmission.rfid == rfid)))
    else:
        db.execute(delete(FormsSubmission).where(FormsSubmission.chave == chave))
    db.execute(delete(CheckingHistory).where(CheckingHistory.chave == chave))
    db.execute(delete(PendingUserRegistration).where(PendingUserRegistration.chave == chave))
    db.execute(delete(AdminAccessRequest).where(AdminAccessRequest.chave == chave))

    # --- Admin mirror: a non-admin user should have none; if one exists, ANONYMIZE (NOT NULL audit FKs
    #     forbid a hard delete). Scrub the name; the row itself stays to satisfy references. ---
    mirror = db.execute(select(AdminUser).where(AdminUser.chave == chave)).scalar_one_or_none()
    if mirror is not None:
        mirror.nome_completo = ""

    # --- Finally the user row (fires ON DELETE CASCADE for user_project_memberships) ---
    db.delete(user)
    return video_object_keys
