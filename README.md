# Checking

Implementacao inicial do sistema de check-in/check-out com:
- FastAPI + SQLite (local) ou PostgreSQL (producao)
- ESP32-S3 com 2 leitores RFID-RC522 v133
- Sensor 1 dedicado a check-in e sensor 2 dedicado a check-out
- Fluxo de pendencia para RFID nao cadastrado
- Integracao Android <-> API para refletir ultimo check-in/check-out por chave unica do usuario
- Documentacao tecnica completa e esquematico de montagem
- Automacao real de Microsoft Forms via Playwright
- Fila persistida para envio assíncrono ao Microsoft Forms apos resposta rapida ao ESP32
- Migracoes com Alembic
- Painel web administrativo em / com login por sessao

## Estrutura
- assets/xpath: seletores XPath do formulario
- sistema/app: backend FastAPI
- docs/descritivo_sistema.md: descritivo funcional e tecnico
- docs/esp32_firmware_troubleshooting.md: troubleshooting operacional do firmware da ESP32 e dos estados de LED
- docs/esquematico_esp32_rc522_duplo.md: guia de montagem eletrica para 2x RC522
- docs/esp32-com5-specs.md: identificacao tecnica da placa conectada na COM5
- firmware/esp32_checking/esp32_checking.ino: firmware da ESP32
- alembic: migracoes de banco
- tests/test_api_flow.py: testes E2E basicos

## Documentacao do firmware ESP32
- Estados oficiais do LED interno: ver `docs/descritivo_sistema.md`, secao `6.1.2 Tabela oficial de estados do LED interno`.
- Troubleshooting do firmware e operacao em campo: `docs/esp32_firmware_troubleshooting.md`.
- Identificacao tecnica da placa conectada na COM5: `docs/esp32-com5-specs.md`.

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

## Repositorio e deploy automatico
- Repositorio principal: `git@github.com:tscode-com-br/checking.git`
- Repositorio alternativo por HTTPS: `https://github.com/tscode-com-br/checking.git`
- Todo push em `main` dispara o workflow `.github/workflows/deploy-oceandrive.yml`.
- O workflow sincroniza o codigo com a OceanDrive, cria o diretorio remoto se necessario, sobe o banco antes da aplicacao, executa `docker compose up -d --build --remove-orphans` e valida `GET /api/health` no servidor.
- O arquivo `.env` de producao permanece somente no servidor e nao e enviado pelo GitHub Actions.
- O remoto `origin` pode apontar para SSH ou HTTPS. Se a maquina local nao tiver chave SSH autorizada no GitHub, use HTTPS para o push.

Observacao:
- O padrao local agora usa SQLite (`DATABASE_URL=sqlite:///./checking.db`), evitando travamento quando o Postgres nao estiver ativo.
- Para usar Postgres, altere `DATABASE_URL` no `.env` e rode novamente.

## Endpoints iniciais
- GET /api/health
- POST /api/device/heartbeat
- POST /api/scan
- GET /api/mobile/state
- POST /api/mobile/events/sync
- GET /api/admin/checkin
- GET /api/admin/checkout
- GET /api/admin/pending
- POST /api/admin/users
- GET /api/admin/events

## Integracao mobile
- O aplicativo Android continua preenchendo o Microsoft Forms localmente.
- O app Android carrega defaults embutidos em `checking_android/src/app-config.js`, evitando configuracao manual pelo usuario final para URL da API e chave compartilhada movel.
- Apos retorno confirmado do Forms (`forms=submitted`), o app sincroniza o evento com a API usando `POST /api/mobile/events/sync`.
- A API autentica o canal mobile via header `x-mobile-shared-key`, controlado pela configuracao `MOBILE_APP_SHARED_KEY`.
- Se a `chave` ainda nao existir em `users`, a API cria automaticamente o usuario com nome `Oriundo do Aplicativo`.
- O app consulta `GET /api/mobile/state?chave=...` para manter `Ultimo Check-In` e `Ultimo Check-Out` alinhados com eventos vindos tanto do app quanto da ESP32.

Antes de gerar uma release mobile, garanta que `checking_android/src/app-config.js` e `MOBILE_APP_SHARED_KEY` no backend estejam alinhados com o ambiente real.

Exemplo de sincronizacao mobile:

```json
{
   "chave": "SRG1",
   "projeto": "P82",
   "action": "checkin",
   "event_time": "2026-04-06T08:00:00+08:00",
   "client_event_id": "android-1234567890"
}
```

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
