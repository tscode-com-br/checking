# Checking

Implementacao inicial do sistema de check-in/check-out com:
- FastAPI + SQLite (local) ou PostgreSQL (producao)
- Leitor RFID unico com alternancia automatica check-in/check-out pelo campo `users.checkin`
- Fluxo de pendencia para RFID nao cadastrado
- Documentacao tecnica completa e esquematico de montagem
- Automacao real de Microsoft Forms via Playwright
- Migracoes com Alembic
- Painel web administrativo em /admin

## Estrutura
- assets/xpath: seletores XPath do formulario
- sistema/app: backend FastAPI
- docs/descritivo_sistema.md: descritivo funcional e tecnico
- docs/esquematico_esp32_pn532.md: guia de montagem eletrica
- firmware/esp32_checking/esp32_checking.ino: firmware da ESP32
- alembic: migracoes de banco
- tests/test_api_flow.py: testes E2E basicos

## Executar localmente (fase inicial)
1. Criar .env a partir de .env.example
2. Instalar dependencias Python:
   pip install -r requirements.txt
3. Aplicar migracoes:
   alembic upgrade head
4. Subir API:
   uvicorn sistema.app.main:app --reload --host 0.0.0.0 --port 8000
5. Abrir painel admin:
   http://127.0.0.1:8000/admin

Observacao:
- O padrao local agora usa SQLite (`DATABASE_URL=sqlite:///./checking.db`), evitando travamento quando o Postgres nao estiver ativo.
- Para usar Postgres, altere `DATABASE_URL` no `.env` e rode novamente.

## Endpoints iniciais
- GET /api/health
- POST /api/device/heartbeat
- POST /api/scan
- GET /api/admin/checkin
- GET /api/admin/checkout
- GET /api/admin/pending
- POST /api/admin/users
- GET /api/admin/events

## Testes
- Executar suite:
   pytest -q
