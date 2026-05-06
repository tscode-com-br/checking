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
- Painel web administrativo em /admin com login por sessao

## Estrutura
- assets/xpath: seletores XPath do formulario
- sistema/app: backend FastAPI
- docs/descritivo_sistema.md: descritivo funcional e tecnico
- docs/context/contexto_geral_projeto.md: contexto consolidado da arquitetura e operacao do projeto
- docs/context/contexto_api_admin_web.md: contexto detalhado da API FastAPI e do website administrativo
- docs/esp32_firmware_troubleshooting.md: troubleshooting operacional do firmware da ESP32 e dos estados de LED
- docs/esquematico_esp32_rc522_duplo.md: guia de montagem eletrica para 2x RC522
- docs/esp32-com5-specs.md: identificacao tecnica da placa conectada na COM5
- firmware/esp32_checking/esp32_checking.ino: firmware da ESP32
- checking_android_new: aplicativo Android em Flutter
- alembic: migracoes de banco
- tests/test_api_flow.py: testes E2E basicos

## Documentacao do firmware ESP32
- Estados oficiais do LED interno: ver `docs/descritivo_sistema.md`, secao `6.1.2 Tabela oficial de estados do LED interno`.
- Troubleshooting do firmware e operacao em campo: `docs/esp32_firmware_troubleshooting.md`.
- Identificacao tecnica da placa conectada na COM5: `docs/esp32-com5-specs.md`.

## Executar localmente (fase inicial)
1. Criar .env a partir de .env.example
2. Instalar dependencias Python de runtime:
   pip install -r requirements.txt
3. Para desenvolvimento e testes, instalar tambem as dependencias dev:
   pip install -r requirements-dev.txt
4. Aplicar migracoes:
   alembic upgrade head
5. Subir API:
   uvicorn sistema.app.main:app --reload --host 0.0.0.0 --port 8000
6. Abrir painel admin:
   http://127.0.0.1:8000/admin

### Chave de criptografia do Transport AI
`TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY` e obrigatoria para abrir e salvar `IA Settings` do Transport. Gere uma chave Fernet uma unica vez e mantenha esse valor estavel no `.env` local e no ambiente de deploy:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Sem essa variavel, o backend passa a bloquear `GET/PUT /api/transport/ai/settings` com erro controlado de criptografia indisponivel, em vez de deixar o problema aparecer apenas no momento do save.

Em homologacao e producao, manter `TRANSPORT_AI_ENABLED=false` por padrao. Se a feature for habilitada em uma janela controlada, preencher `TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE` e `TRANSPORT_AI_MAX_CONCURRENT_RUNS` no mesmo deploy; sem esses gates, o backend passa a bloquear novas execucoes da IA e o readiness fica `unready` por desenho.

### Contrato operacional do modal IA Settings
- O catalogo de projetos do modal deve ser recarregado do endpoint autoritativo `GET /api/transport/projects`.
- `state.dashboard.projects` continua servindo apenas como bootstrap visual local enquanto o catalogo autoritativo carrega.
- `PUT /api/transport/ai/settings` exige `project_id`; a UI deve manter `Save` desabilitado sem projeto valido e sem catalogo `ready`.
- Quando o contrato estatico do modal mudar de forma incompatível, atualize o versionamento de `styles.css`, `i18n.js` e `app.js` em `sistema/app/static/transport/index.html`. A versao coordenada atual do `transport` e `20260506b`.
- O caminho legado global continua apenas para consulta e rollback controlado. Nao reintroduza fallback global implicito para gravacao ou runtime.

### Smoke OpenAI opt-in
- Chaves OpenAI reais so podem ser usadas fora do CI e apenas via `TRANSPORT_AI_TEST_OPENAI_API_KEY`.
- O smoke opt-in fica em `tests/test_transport_ai_openai_smoke.py` e pula automaticamente quando a variavel nao estiver definida.
- Execucao manual:

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_openai_smoke.py -q
```

- Depois do smoke, remova a variavel do ambiente atual e descarte qualquer preview temporario usado na validacao.
- Runbook detalhado: `docs/context/transport_ai_project_rollout.md`.

### Preview local rapido do Transport fora do Compose
Se o `.env` atual estiver apontando `DATABASE_URL` para `postgresql+psycopg://...@db:5432/...`, esse host `db` so existe dentro da rede Docker Compose e o boot local falhara com `getaddrinfo failed`.

Para subir a API localmente no Windows sem depender do Postgres do Compose, use o helper abaixo, que sobrescreve `DATABASE_URL` para um SQLite de preview, aplica as migracoes e sobe o FastAPI:

```powershell
./scripts/start_local_preview_api.ps1 -Reload
```

Por padrao ele sobe em `http://127.0.0.1:8010`. Para manter a porta `8000`, rode:

```powershell
./scripts/start_local_preview_api.ps1 -Port 8000 -Reload
```

## Repositorio e deploy automatico
- Repositorio principal: `git@github.com:tscode-com-br/checking.git`
- Repositorio alternativo por HTTPS: `https://github.com/tscode-com-br/checking.git`
- O workspace tambem contem `checking_android_new` com `.git` proprio, mas o procedimento oficial de commit/push usa somente o repositorio principal.
- Nao usar `git subtree` nem push do repositorio Flutter como parte da operacao normal do projeto.
- Procedimento oficial consolidado: `docs/context/procedimento_oficial_repositorios.md`.
- Todo push em `main` dispara o workflow `.github/workflows/deploy-oceandrive.yml`.
- O workflow agora compila a imagem da aplicacao no GitHub Actions, publica no GHCR e faz o droplet apenas sincronizar o codigo operacional e executar `docker compose pull` seguido de `docker compose up -d --no-build --force-recreate`. Isso reduz o crescimento recorrente de SSD causado por builds completos dentro do servidor. Depois do rollout, o deploy valida `GET /api/health`, reinstala a automacao periodica de limpeza de SSD e remove cache Docker e temporarios antigos remanescentes.
- O arquivo `.env` de producao nao deve ser commitado no repositório. Por padrao ele permanece somente no servidor; opcionalmente o GitHub Actions pode materializa-lo no host a partir do secret `OCEAN_APP_ENV_B64`.
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
- O aplicativo Android atual fica em `checking_android_new` e usa Flutter.
- O app Android carrega defaults embutidos em `checking_android_new/lib/src/features/checking/checking_preset_config.dart`, evitando configuracao manual pelo usuario final para URL da API e chave compartilhada movel.
- O app sincroniza historico com `GET /api/mobile/state`, localizacoes com `GET /api/mobile/locations` e envia eventos por `POST /api/mobile/events/forms-submit`.
- O envio ao Microsoft Forms foi centralizado na API; o app nao executa mais automacao local do Forms.
- A API autentica o canal mobile via header `x-mobile-shared-key`, controlado pela configuracao `MOBILE_APP_SHARED_KEY`.
- Se a `chave` ainda nao existir em `users`, a API cria automaticamente o usuario com nome `Oriundo do Aplicativo`.
- O app consulta `GET /api/mobile/state?chave=...` para manter `Ultimo Check-In` e `Ultimo Check-Out` alinhados com eventos vindos tanto do app quanto da ESP32.

Antes de gerar uma release mobile, garanta que `checking_android_new/lib/src/features/checking/checking_preset_config.dart` e `MOBILE_APP_SHARED_KEY` no backend estejam alinhados com o ambiente real.

Exemplo de envio mobile:

```json
{
   "chave": "SRG1",
   "projeto": "P82",
   "action": "checkin",
   "informe": "normal",
   "event_time": "2026-04-06T00:00:00Z",
   "client_event_id": "flutter-1234567890",
   "local": "Aplicativo"
}
```

## Testes
- Executar suite:
   pytest -q
- Se o ambiente foi criado apenas com runtime, instalar antes `pip install -r requirements-dev.txt`.

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
