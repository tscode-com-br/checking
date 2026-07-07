"""Throttle do bookkeeping de inatividade (checkin/checkout/inactive/missing-checkout).

Contrato protegido:
1. Fora de produção (dev/testes) o gate SEMPRE libera — preserva o efeito imediato de que os testes
   de integração dependem (descadastro/inactivity_days aplicados no mesmo request).
2. Em produção o gate é leading-edge: libera uma vez, depois bloqueia enquanto a janela não expira,
   e volta a liberar quando o último disparo fica mais antigo que a janela.

Testa o gate puro (_should_run_inactivity_bookkeeping_now) — sem DB, sem relógio real — resetando o
estado global do módulo entre asserts.
"""
from __future__ import annotations

import time

import pytest

from sistema.app.core.config import settings as app_settings
from sistema.app.routers import admin


@pytest.fixture(autouse=True)
def _reset_throttle_state():
    admin._last_inactivity_bookkeeping_monotonic = None
    yield
    admin._last_inactivity_bookkeeping_monotonic = None


def test_gate_always_runs_outside_production(monkeypatch):
    monkeypatch.setattr(app_settings, "app_env", "development")
    # Mesmo chamado em sequência sem intervalo, nunca bloqueia fora de produção.
    assert all(admin._should_run_inactivity_bookkeeping_now() for _ in range(5))


def test_gate_leading_edge_in_production(monkeypatch):
    monkeypatch.setattr(app_settings, "app_env", "production")
    # 1º disparo passa; disparos subsequentes dentro da janela são bloqueados.
    assert admin._should_run_inactivity_bookkeeping_now() is True
    assert admin._should_run_inactivity_bookkeeping_now() is False
    assert admin._should_run_inactivity_bookkeeping_now() is False


def test_gate_reopens_after_window_elapses_in_production(monkeypatch):
    monkeypatch.setattr(app_settings, "app_env", "production")
    assert admin._should_run_inactivity_bookkeeping_now() is True
    # Simula o último disparo tendo ocorrido mais de uma janela atrás (sem sleep real).
    admin._last_inactivity_bookkeeping_monotonic = (
        time.monotonic() - admin._INACTIVITY_BOOKKEEPING_MIN_INTERVAL_SECONDS - 1.0
    )
    assert admin._should_run_inactivity_bookkeeping_now() is True
    # E logo em seguida volta a bloquear dentro da nova janela.
    assert admin._should_run_inactivity_bookkeeping_now() is False
