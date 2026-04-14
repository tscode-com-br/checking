# Contexto Geral do Projeto Checking

## 1. Visão do sistema

O Checking é um sistema de controle de presença de funcionários com dois canais de entrada:

1. RFID físico (ESP32 + 2 leitores RC522)
2. Aplicativo Android (Flutter)

Os dois canais atualizam o mesmo backend FastAPI, que persiste dados no banco e entrega o painel administrativo web.

## 2. Componentes principais

### 2.1 Backend + painel web admin

- Stack: Python, FastAPI, SQLAlchemy, Alembic, Playwright.
- Pasta principal: `sistema/app`.
- Painel admin servido pelo próprio backend em `/` (`sistema/app/static/admin`).
- Banco:
  - Local: SQLite (`DATABASE_URL=sqlite:///./checking.db`)
  - Produção: PostgreSQL (via Docker Compose)

### 2.2 Firmware do dispositivo (RFID)

- Stack: Arduino/C++ para ESP32-S3.
- Pasta: `firmware/esp32_checking`.
- Hardware:
  - RC522 #1 envia `action=checkin`
  - RC522 #2 envia `action=checkout`
- Comunicação com a API:
  - `POST /api/device/heartbeat`
  - `POST /api/scan`

### 2.3 App Android

- Projeto Flutter para Android.
- Pasta local atual: `checking_android_new`.
- Fluxo: o app envia check-in/check-out para a API, consulta estado remoto e sincroniza o catálogo de localizações.
- Endpoints usados na API:
  - `GET /api/mobile/state`
  - `GET /api/mobile/locations`
  - `POST /api/mobile/events/forms-submit`

### 2.4 Automação Microsoft Forms

- No backend: worker com Playwright usando XPaths em `assets/xpath`.
- Objetivo: manter compatibilidade com o processo operacional baseado em Forms, com envio centralizado na API.

## 3. Repositórios e deploy

- Repo principal (API + painel web + firmware + docs): `tscode-com-br/checking`.
- Pipeline CI/CD: `.github/workflows/deploy-oceandrive.yml`.
- Regra atual: push em `main` dispara deploy automático no servidor DigitalOcean.
- Processo do workflow:
  1. valida secrets
  2. sincroniza código por SSH/rsync
  3. sobe `db` e atualiza containers com `docker compose up -d --build --remove-orphans`
  4. valida `GET /api/health`

Observação informada pelo projeto:
- O app Android atual permanece em `checking_android_new` dentro do monorepo e pode ser publicado separadamente via `git subtree`.

## 4. Fluxos de negócio ponta a ponta

### 4.1 Fluxo RFID (ESP32 -> API)

1. ESP32 autentica com `shared_key` do dispositivo.
2. Envia heartbeat periódico para indicar disponibilidade.
3. Ao ler cartão:
   - Sensor 1 -> `checkin`
   - Sensor 2 -> `checkout`
4. A API aplica regras:
   - RFID não cadastrado -> pendência (`pending_registrations`)
   - checkout sem checkin ativo -> bloqueia
   - checkin repetido com usuário já ativo -> atualiza apenas `local`
   - operação válida -> atualiza o estado do usuário e enfileira envio ao Forms
5. A API responde `outcome` + `led`, e a ESP32 mostra o padrão visual correspondente.

### 4.2 Fluxo Android (App -> API)

1. O usuário executa check-in/check-out (manual, notificação ou geofence).
2. O app envia o evento para `POST /api/mobile/events/forms-submit` com chave compartilhada mobile.
3. A API faz upsert do estado do usuário, cria trilha em `user_sync_events` e enfileira o envio ao Forms.
4. O app consulta o estado consolidado com `GET /api/mobile/state`.
5. O app sincroniza o catálogo de localizações com `GET /api/mobile/locations`.

### 4.3 Fluxo administrativo (Web)

1. O admin autentica por sessão (cookie HttpOnly, SessionMiddleware).
2. O painel mostra as abas:
   - Check-In
   - Check-Out
   - Cadastro (pendências, usuários, administradores)
   - Eventos
3. Atualização em tempo real por SSE em `/api/admin/stream`.
4. Logs podem ser arquivados em CSV e baixados (individualmente ou em ZIP).

## 5. Modelo de dados (alto nível)

Tabelas centrais:

- `users`: cadastro operacional, estado atual (checkin/checkout), local e atividade.
- `pending_registrations`: RFIDs ainda não cadastrados.
- `check_events`: trilha de auditoria operacional.
- `device_heartbeats`: sinais de vida do ESP32.
- `forms_submissions`: fila persistente de envio ao Forms.
- `user_sync_events`: histórico de sincronização entre fontes RFID/Android.
- `admin_users` e `admin_access_requests`: governança de acesso administrativo.

## 6. Segurança e autenticação

- Dispositivo: `DEVICE_SHARED_KEY`.
- Mobile: header `x-mobile-shared-key` com `MOBILE_APP_SHARED_KEY`.
- Admin web: sessão assinada por `ADMIN_SESSION_SECRET`.
- Bootstrap de admin inicial no startup via variáveis:
  - `BOOTSTRAP_ADMIN_KEY`
  - `BOOTSTRAP_ADMIN_PASSWORD`
  - `BOOTSTRAP_ADMIN_NAME`

## 7. Estrutura de pastas relevante

- `sistema/app` -> API FastAPI, modelos, rotas e serviços
- `sistema/app/static/admin` -> frontend administrativo
- `firmware/esp32_checking` -> firmware ESP32
- `checking_android_new` -> app Android (Flutter)
- `assets/xpath` -> seletores da automação Forms
- `alembic` -> migrações de banco
- `tests` -> testes de fluxo API/admin/mobile/forms queue
- `docs` -> documentação técnica e operacional

## 8. Operação e observabilidade

- Health check: `GET /api/health`
- Eventos operacionais centralizados em `check_events`
- Admin recebe atualizações em tempo real via SSE
- Arquivamento de logs em CSV para retenção operacional
- Firmware possui diagnóstico serial para Wi-Fi, API, sensores e resposta de scan

## 9. Decisões arquiteturais importantes

1. API e painel web estão no mesmo serviço FastAPI.
2. O envio ao Forms no backend é assíncrono (fila + worker), reduzindo a latência para a ESP32.
3. O app Android usa a API para manter estado único com RFID, enquanto o envio ao Forms fica centralizado no backend.
4. O controle de acesso admin migrou de chave estática para sessão autenticada.
5. O deploy de produção é orientado a container (`docker-compose.yml`) no DigitalOcean.

## 10. Guia rápido para novos desenvolvedores

1. Ler `README.md` (visão geral e comandos básicos).
2. Ler `docs/context/descritivo_sistema.md` (regras de negócio e LED).
3. Ler `checking_android_new/README.md` (arquitetura e operação do app mobile).
4. Rodar migrações (`alembic upgrade head`) e subir a API local.
5. Validar o fluxo mínimo:
   - `/api/health`
   - login admin
   - cadastro de usuário
   - `POST /api/scan` com payload de teste
   - consulta de eventos no painel

## 11. Estado atual consolidado

O projeto já possui:

- backend funcional com autenticação admin por sessão
- painel web administrativo completo
- suporte a ESP32 com dois leitores RC522 (checkin/checkout explícitos)
- sincronização mobile com endpoint dedicado
- fila persistente para envio ao Forms
- deploy automático por push na branch `main`

Esse contexto serve como base única para manutenção, onboarding e evolução do sistema.

