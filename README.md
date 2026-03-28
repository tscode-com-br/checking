# Checking

Implementacao inicial do sistema de check-in/check-out com:
- FastAPI + SQLite (local) ou PostgreSQL (producao)
- ESP32-S3 com 2 leitores RFID-RC522 v133
- Sensor 1 dedicado a check-in e sensor 2 dedicado a check-out
- Fluxo de pendencia para RFID nao cadastrado
- Documentacao tecnica completa e esquematico de montagem
- Automacao real de Microsoft Forms via Playwright
- Migracoes com Alembic
- Painel web administrativo em /

## Estrutura
- assets/xpath: seletores XPath do formulario
- sistema/app: backend FastAPI
- docs/descritivo_sistema.md: descritivo funcional e tecnico
- docs/esquematico_esp32_rc522_duplo.md: guia de montagem eletrica para 2x RC522
- docs/esp32-com5-specs.md: identificacao tecnica da placa conectada na COM5
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
   http://127.0.0.1:8000/

Compatibilidade:
- A URL antiga `/admin` redireciona para `/`.

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

## Payload de scan
O firmware envia para `POST /api/scan`:

```json
{
   "rfid": "A1B2C3D4",
   "action": "checkin",
   "device_id": "ESP32-S3-01",
   "request_id": "ESP32-S3-01-checkin-123456-A1B2C3D4",
   "shared_key": "..."
}
```

Regras:
- `action=checkin`: leitura originada no sensor 1.
- `action=checkout`: leitura originada no sensor 2.
