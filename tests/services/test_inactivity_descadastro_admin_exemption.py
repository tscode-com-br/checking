"""apply_inactivity_descadastro NÃO deve descadastrar admins por inatividade (2026-07-07).

A membership de um admin (perfil 1/9) é o seu ESCOPO de gestão de projeto, não um indicador de
presença em campo. Um admin que não faz check-in não deve perder o vínculo de projeto (senão passa a
não enxergar ninguém nas telas de presença). Workers (perfil 0) continuam sendo descadastrados
normalmente ao exceder o threshold de inatividade do projeto.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import Project, User, UserProjectMembership
from sistema.app.services.user_activity import apply_inactivity_descadastro
from sistema.app.services.user_projects import replace_user_project_memberships


def _make_session(tmp_path: Path) -> Session:
    engine = sa.create_engine(f"sqlite+pysqlite:///{(tmp_path / 'test_descad.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)()


def _make_project(db: Session, name: str, threshold: int) -> Project:
    proj = Project(
        name=name, country_code="SG", country_name="Singapore", timezone_name="Asia/Singapore",
        address="1 Rd", zip_code="099999", inactivity_days_threshold=threshold,
    )
    db.add(proj)
    db.flush()
    return proj


def _make_user(db: Session, *, chave, nome, perfil, inactivity_days) -> User:
    user = User(rfid=None, chave=chave, nome=nome, perfil=perfil,
                last_active_at=datetime(2026, 1, 1, tzinfo=timezone.utc), inactivity_days=inactivity_days)
    db.add(user)
    db.flush()
    return user


def test_admin_membership_preserved_despite_inactivity(tmp_path: Path):
    db = _make_session(tmp_path)
    try:
        _make_project(db, "PADM", threshold=45)
        admin = _make_user(db, chave="AD01", nome="Admin Inativo", perfil=1, inactivity_days=70)
        replace_user_project_memberships(db, admin, ["PADM"])
        db.commit()

        changed = apply_inactivity_descadastro(db)
        db.commit()

        remaining = db.query(UserProjectMembership).filter(UserProjectMembership.user_id == admin.id).count()
        assert remaining == 1, "admin não pode ser descadastrado por inatividade"
        assert changed is False, "nenhuma remoção deve ocorrer só por conta de um admin inativo"
    finally:
        db.close()


def test_full_admin_membership_preserved_despite_inactivity(tmp_path: Path):
    db = _make_session(tmp_path)
    try:
        _make_project(db, "PADM9", threshold=45)
        admin = _make_user(db, chave="AD09", nome="Admin9 Inativo", perfil=9, inactivity_days=99)
        replace_user_project_memberships(db, admin, ["PADM9"])
        db.commit()

        apply_inactivity_descadastro(db)
        db.commit()

        remaining = db.query(UserProjectMembership).filter(UserProjectMembership.user_id == admin.id).count()
        assert remaining == 1
    finally:
        db.close()


def test_worker_still_descadastrado_by_inactivity(tmp_path: Path):
    db = _make_session(tmp_path)
    try:
        _make_project(db, "PWRK", threshold=45)
        worker = _make_user(db, chave="WK01", nome="Worker Inativo", perfil=0, inactivity_days=70)
        replace_user_project_memberships(db, worker, ["PWRK"])
        db.commit()

        changed = apply_inactivity_descadastro(db)
        db.commit()

        remaining = db.query(UserProjectMembership).filter(UserProjectMembership.user_id == worker.id).count()
        assert remaining == 0, "worker inativo acima do threshold deve ser descadastrado"
        assert changed is True
    finally:
        db.close()
