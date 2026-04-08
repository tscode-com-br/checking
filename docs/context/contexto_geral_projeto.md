# Contexto Geral do Projeto Checking

## 1. Visao do sistema

O Checking e um sistema de controle de presenca de funcionarios com dois canais de entrada:

1. RFID fisico (ESP32 + 2 leitores RC522)
2. Aplicativo Android (Tauri)

Os dois canais atualizam o mesmo backend FastAPI, que persiste dados no banco e entrega o painel administrativo web.

## 2. Componentes principais

### 2.1 Backend + painel web admin

- Stack: Python, FastAPI, SQLAlchemy, Alembic, Playwright.
- Pasta principal: `sistema/app`.
- Painel admin servido pelo proprio backend em `/` (`sistema/app/static/admin`).
- Banco:
  - Local: SQLite (`DATABASE_URL=sqlite:///./checking.db`)
  - Producao: PostgreSQL (via Docker Compose)

### 2.2 Firmware dispositivo (RFID)

- Stack: Arduino/C++ para ESP32-S3.
- Pasta: `firmware/esp32_checking`.
- Hardware:
  - RC522 #1 envia `action=checkin`
  - RC522 #2 envia `action=checkout`
- Comunicacao com API:
  - `POST /api/device/heartbeat`
  - `POST /api/scan`

### 2.3 App Android

- Projeto Tauri 2 (frontend JS + backend Rust + camada Android Kotlin).
- Pasta local atual: `checking_android`.
- Fluxo: app executa automacao do Microsoft Forms e depois sincroniza o evento com a API.
- Endpoints usados na API:
  - `GET /api/mobile/state`
  - `POST /api/mobile/events/sync`

### 2.4 Automacao Microsoft Forms

- No backend: worker com Playwright usando XPaths em `assets/xpath`.
- No Android: comando Rust `preencher_forms` no projeto Tauri.
- Objetivo: manter compatibilidade com processo operacional baseado em Forms.

## 3. Repositorios e deploy

- Repo principal (API + painel web + firmware + docs): `tscode-com-br/checking`.
- Pipeline CI/CD: `.github/workflows/deploy-oceandrive.yml`.
- Regra atual: push em `main` dispara deploy automatico no servidor DigitalOcean.
- Processo do workflow:
  1. valida secrets
  2. sincroniza codigo por SSH/rsync
  3. sobe `db` e atualiza containers com `docker compose up -d --build --remove-orphans`
  4. valida `GET /api/health`

Observacao informada pelo projeto:
- O app Android tem repositorio proprio, compartilhado com `dsschmidt`.

## 4. Fluxos de negocio ponta a ponta

### 4.1 Fluxo RFID (ESP32 -> API)

1. ESP32 autentica com `shared_key` do dispositivo.
2. Envia heartbeat periodico para indicar disponibilidade.
3. Ao ler cartao:
   - Sensor 1 -> `checkin`
   - Sensor 2 -> `checkout`
4. API aplica regras:
   - RFID nao cadastrado -> pendencia (`pending_registrations`)
   - checkout sem checkin ativo -> bloqueia
   - checkin repetido com usuario ja ativo -> atualiza apenas `local`
   - operacao valida -> atualiza estado do usuario e enfileira envio ao Forms
5. API responde `outcome` + `led`, e a ESP32 mostra o padrao visual correspondente.

### 4.2 Fluxo Android (App -> API)

1. Usuario executa check-in/check-out (manual, notificacao ou geofence).
2. App roda automacao de envio no Forms.
3. Quando Forms confirma envio, app sincroniza evento na API com chave compartilhada mobile.
4. API faz upsert do estado do usuario e cria trilha em `user_sync_events`.
5. App consulta estado consolidado com `GET /api/mobile/state`.

### 4.3 Fluxo administrativo (Web)

1. Admin autentica por sessao (cookie HttpOnly, SessionMiddleware).
2. Painel mostra abas:
   - Check-In
   - Check-Out
   - Cadastro (pendencias, usuarios, administradores)
   - Eventos
3. Atualizacao em tempo real por SSE em `/api/admin/stream`.
4. Logs podem ser arquivados em CSV e baixados (individual ou zip).

## 5. Modelo de dados (alto nivel)

Tabelas centrais:

- `users`: cadastro operacional, estado atual (checkin/checkout), local e atividade.
- `pending_registrations`: RFIDs ainda nao cadastrados.
- `check_events`: trilha de auditoria operacional.
- `device_heartbeats`: sinais de vida do ESP32.
- `forms_submissions`: fila persistente de envio ao Forms.
- `user_sync_events`: historico de sincronizacao entre fontes RFID/Android.
- `admin_users` e `admin_access_requests`: governanca de acesso administrativo.

## 6. Seguranca e autenticacao

- Dispositivo: `DEVICE_SHARED_KEY`.
- Mobile: header `x-mobile-shared-key` com `MOBILE_APP_SHARED_KEY`.
- Admin web: sessao assinada por `ADMIN_SESSION_SECRET`.
- Bootstrap de admin inicial no startup via variaveis:
  - `BOOTSTRAP_ADMIN_KEY`
  - `BOOTSTRAP_ADMIN_PASSWORD`
  - `BOOTSTRAP_ADMIN_NAME`

## 7. Estrutura de pastas relevante

- `sistema/app` -> API FastAPI, modelos, rotas e servicos
- `sistema/app/static/admin` -> frontend administrativo
- `firmware/esp32_checking` -> firmware ESP32
- `checking_android` -> app Android (Tauri)
- `assets/xpath` -> seletores da automacao Forms
- `alembic` -> migracoes de banco
- `tests` -> testes de fluxo API/admin/mobile/forms queue
- `docs` -> documentacao tecnica e operacional

## 8. Operacao e observabilidade

- Health check: `GET /api/health`
- Eventos operacionais centralizados em `check_events`
- Admin recebe atualizacoes em tempo real via SSE
- Arquivamento de logs em CSV para retencao operacional
- Firmware possui diagnostico serial para Wi-Fi, API, sensores e resposta de scan

## 9. Decisoes arquiteturais importantes

1. API e painel web estao no mesmo servico FastAPI.
2. O envio ao Forms no backend e assincrono (fila + worker), reduzindo latencia para ESP32.
3. App Android usa sincronizacao API por eventos para manter estado unico com RFID.
4. Controle de acesso admin migrou de chave estatica para sessao autenticada.
5. Deploy de producao e orientado a container (`docker-compose.yml`) no DigitalOcean.

## 10. Guia rapido para novos desenvolvedores

1. Ler `README.md` (visao geral e comandos basicos).
2. Ler `docs/descritivo_sistema.md` (regras de negocio e LED).
3. Ler `docs/android-context.md` (arquitetura mobile).
4. Rodar migracoes (`alembic upgrade head`) e subir API local.
5. Validar fluxo minimo:
   - `/api/health`
   - login admin
   - cadastro de usuario
   - `POST /api/scan` com payload de teste
   - consulta de eventos no painel

## 11. Estado atual consolidado

O projeto ja possui:

- backend funcional com autenticao admin por sessao
- painel web administrativo completo
- suporte a ESP32 com dois leitores RC522 (checkin/checkout explicitos)
- sincronizacao mobile com endpoint dedicado
- fila persistente para envio ao Forms
- deploy automatico por push na branch `main`

Esse contexto serve como base unica para manutencao, onboarding e evolucao do sistema.
