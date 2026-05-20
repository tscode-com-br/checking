"""Identidade de admin para colunas de auditoria (FK -> admin_users).

A aplicacao tem duas tabelas de identidade:

- ``users``: pessoa (chave RFID, perfil, login Check Web / Admin). FK em
  colunas operacionais como ``opened_by_user_id`` ou ``check_events.user_id``.
- ``admin_users``: identidade de auditoria de admin (chave unica, com
  ``password_hash`` proprio). FK em colunas ``*_by_admin_id`` e
  ``actor_user_id`` que registram quem executou uma acao administrativa.

Uma mesma pessoa tem ambas as linhas, pareadas pela ``chave``. Este
modulo e a ponte unica entre as duas: dada uma linha de ``users`` (ou
apenas a ``chave``), retorna - criando se necessario - a linha
correspondente de ``admin_users``.

Regra:
    Qualquer codigo que grave em uma coluna FK -> ``admin_users.id``
    DEVE obter o ID atraves de ``resolve_admin_user_for_user`` ou
    ``ensure_admin_user_by_chave``. Nunca passar ``User.id`` diretamente
    para essas colunas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AdminUser, User
from .time_utils import now_sgt


@dataclass(frozen=True)
class AdminActorIdentity:
    """Par (``User``, ``AdminUser``) representando o admin autenticado.

    - ``identity.user.id`` para FK em colunas que referenciam ``users.id``.
    - ``identity.admin_user.id`` para FK em colunas que referenciam
      ``admin_users.id`` (qualquer coluna ``*_by_admin_id`` ou
      ``actor_user_id``).

    O nome carrega "Actor" para evitar conflito com ``schemas.AdminIdentity``,
    que e o Pydantic publico devolvido ao frontend pela sessao admin.
    """

    user: User
    admin_user: AdminUser


def ensure_admin_user_by_chave(
    db: Session,
    *,
    chave: str,
    nome_completo: str,
    ensured_at: datetime | None = None,
) -> AdminUser:
    """Garante a existencia de uma linha em ``admin_users`` para ``chave``.

    Upsert idempotente: se existe, atualiza ``nome_completo`` quando
    mudou; se nao existe, cria com ``password_hash=None``. Sempre da
    ``flush()`` antes de retornar para garantir ``admin_user.id``
    populado.
    """
    timestamp = ensured_at or now_sgt()
    normalized_chave = str(chave or "").strip().upper()
    normalized_nome = " ".join(str(nome_completo or "").strip().split()) or normalized_chave

    admin_user = db.execute(
        select(AdminUser).where(AdminUser.chave == normalized_chave)
    ).scalar_one_or_none()
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


def resolve_admin_user_for_user(
    db: Session,
    user: User,
    *,
    ensured_at: datetime | None = None,
) -> AdminUser:
    """Retorna o ``AdminUser`` pareado com o ``User`` dado (cria se ausente).

    Usado quando o codigo ja tem um ``User`` autenticado (de uma sessao
    admin ou transport) e precisa do ``admin_users.id`` correspondente
    para gravar em um FK de auditoria.
    """
    return ensure_admin_user_by_chave(
        db,
        chave=user.chave,
        nome_completo=user.nome,
        ensured_at=ensured_at,
    )
