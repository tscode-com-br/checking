"""Escopo de projeto por perfil nas telas de presença do admin (requisito reconfirmado 2026-07-07).

Requisito do produto (revisão do usuário): apenas admins FULL (perfil com dígito 9) enxergam TODOS
os projetos. Admins perfil 1 são ESCOPADOS às suas memberships de projeto — veem apenas usuários dos
seus próprios projetos em check-in/check-out. Admins perfil 0 (limitados) permanecem escopados.

Isto REVERTE a variação anterior "perfil 1 vê tudo" (bug UTO9): o UTO9 tem membership de P80, logo
escopar mostra os usuários de P80 (não vazio). Um perfil 1 SEM memberships passa a ver vazio — o
conserto para esse caso é conceder memberships, não torná-lo irrestrito.
"""
from __future__ import annotations

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

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from sistema.app.database import Base, SessionLocal, engine  # noqa: E402
from sistema.app.main import app  # noqa: E402
from sistema.app.models import Project, User, UserProjectMembership  # noqa: E402
from sistema.app.services.passwords import hash_password  # noqa: E402
from sistema.app.services.time_utils import now_sgt  # noqa: E402
from sistema.app.services.user_projects import replace_user_project_memberships  # noqa: E402

Base.metadata.create_all(bind=engine)

# Projetos exclusivos deste teste (evita colidir com o estado acumulado do test_checking.db).
_PA = "SCOPEPA"
_PB = "SCOPEPB"
_TEST_CHAVES = ("SC1A", "SC1N", "SC9A", "SWA0", "SWB0", "SWA1", "SWA9", "SWB9")


@pytest.fixture(autouse=True)
def _reset_test_rows():
    """test_checking.db é persistente e compartilhado; limpa as linhas deste teste antes de cada caso
    para tornar as criações idempotentes."""
    _cleanup()
    yield
    _cleanup()


def _cleanup():
    with SessionLocal() as db:
        user_ids = [
            row[0] for row in db.execute(
                User.__table__.select().with_only_columns(User.id).where(User.chave.in_(_TEST_CHAVES))
            ).all()
        ]
        if user_ids:
            db.execute(UserProjectMembership.__table__.delete().where(UserProjectMembership.user_id.in_(user_ids)))
            db.execute(User.__table__.delete().where(User.id.in_(user_ids)))
        db.commit()


def _ensure_project(db, name: str) -> None:
    if db.query(Project).filter(Project.name == name).first() is None:
        db.add(Project(
            name=name, country_code="SG", country_name="Singapore",
            timezone_name="Asia/Singapore", address="1 Scope Rd", zip_code="099999",
        ))
        db.flush()


def _make_worker(db, *, chave, rfid, nome, projeto, now) -> User:
    user = User(rfid=rfid, chave=chave, nome=nome, projeto=projeto, checkin=True,
                local="Web", time=now, last_active_at=now, inactivity_days=0)
    db.add(user)
    db.flush()
    replace_user_project_memberships(db, user, [projeto])
    return user


def _make_admin(db, *, chave, nome, perfil, memberships, now) -> User:
    admin = User(rfid=None, chave=chave, nome=nome, projeto=None,
                 senha=hash_password("adm123"), perfil=perfil, last_active_at=now, inactivity_days=0)
    db.add(admin)
    db.flush()
    if memberships:
        replace_user_project_memberships(db, admin, memberships)
    return admin


def _login(client, chave):
    return client.post("/api/admin/auth/login", json={"chave": chave, "senha": "adm123"})


def _checkin_names(client):
    resp = client.get("/api/admin/checkin")
    assert resp.status_code == 200, resp.text
    return {row["nome"] for row in resp.json()}


def test_perfil_one_admin_scoped_to_own_project_sees_only_that_project():
    """UTO9-like: perfil 1 com membership só em SCOPEPA vê os usuários de SCOPEPA e NÃO os de SCOPEPB."""
    now = now_sgt()
    with SessionLocal() as db:
        _ensure_project(db, _PA)
        _ensure_project(db, _PB)
        _make_admin(db, chave="SC1A", nome="Scope P1 A", perfil=1, memberships=[_PA], now=now)
        _make_worker(db, chave="SWA0", rfid="SCWA0", nome="Worker SCOPEPA one", projeto=_PA, now=now)
        _make_worker(db, chave="SWB0", rfid="SCWB0", nome="Worker SCOPEPB one", projeto=_PB, now=now)
        db.commit()

    with TestClient(app) as client:
        assert _login(client, "SC1A").status_code == 200
        names = _checkin_names(client)
    assert "Worker SCOPEPA one" in names
    assert "Worker SCOPEPB one" not in names  # escopado: não vê o outro projeto


def test_perfil_one_admin_without_memberships_sees_empty():
    """perfil 1 SEM memberships fica escopado a nenhum projeto -> não enxerga ninguém."""
    now = now_sgt()
    with SessionLocal() as db:
        _ensure_project(db, _PA)
        _make_admin(db, chave="SC1N", nome="Scope P1 None", perfil=1, memberships=[], now=now)
        _make_worker(db, chave="SWA1", rfid="SCWA1", nome="Worker SCOPEPA none", projeto=_PA, now=now)
        db.commit()

    with TestClient(app) as client:
        assert _login(client, "SC1N").status_code == 200
        names = _checkin_names(client)
    assert "Worker SCOPEPA none" not in names


def test_perfil_nine_full_admin_sees_all_projects():
    """perfil 9 (FULL) é irrestrito: vê usuários de qualquer projeto, sem depender de membership."""
    now = now_sgt()
    with SessionLocal() as db:
        _ensure_project(db, _PA)
        _ensure_project(db, _PB)
        _make_admin(db, chave="SC9A", nome="Scope P9 A", perfil=9, memberships=[], now=now)
        _make_worker(db, chave="SWA9", rfid="SCWA9", nome="Worker SCOPEPA nine", projeto=_PA, now=now)
        _make_worker(db, chave="SWB9", rfid="SCWB9", nome="Worker SCOPEPB nine", projeto=_PB, now=now)
        db.commit()

    with TestClient(app) as client:
        assert _login(client, "SC9A").status_code == 200
        names = _checkin_names(client)
    assert "Worker SCOPEPA nine" in names
    assert "Worker SCOPEPB nine" in names
