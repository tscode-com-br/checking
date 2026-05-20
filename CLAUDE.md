# CLAUDE.md — Guia de contexto para agentes de IA

Este arquivo descreve convenções, arquitetura e pontos críticos do projeto **Checking**
para uso por agentes de IA (Claude, Copilot, etc.) ao assistir no desenvolvimento.

## Visão geral do projeto

Sistema de check-in/check-out baseado em RFID com:
- **Backend**: FastAPI + SQLAlchemy (SQLite em dev, PostgreSQL em produção)
- **Frontend admin**: SPA em `/admin` (JS vanilla, SSE para atualizações em tempo real)
- **Frontend check web**: SPA em `/check` (JS vanilla, SSE, i18n pt/en/zh/ms/id/tl)
- **Firmware**: ESP32-S3 com 2 leitores RFID-RC522
- **Deploy**: Docker Compose + GitHub Actions → DigitalOcean Droplet

## Estrutura de diretórios relevante

```
sistema/app/
  main.py              # Ponto de entrada FastAPI; create_all em dev
  models.py            # Todos os modelos SQLAlchemy
  schemas.py           # Pydantic schemas (request/response)
  database.py          # SessionLocal, engine
  core/config.py       # Settings via pydantic-settings (.env)
  routers/
    admin.py           # Endpoints /api/admin/*
    web_check.py       # Endpoints /api/web/check/*
    device.py          # Endpoints ESP32 /api/device/*
    transport.py       # Endpoints /api/transport/*
  services/
    event_logger.py    # log_event() — grava CheckEvent
    admin_updates.py   # Brokers SSE (admin + web_check)
    accident_lifecycle.py       # Lógica de estado do acidente
    accident_situation_table.py # Render da tabela de situação
    accident_archive_builder.py # Geração de ZIP + XLSX
    accident_numbering.py       # Sequência de accident_number
    email_sender.py             # Entrega SMTP de emails de emergência
    email_templates.py          # Templates HTML dos emails
    object_storage.py           # Upload/download DO Spaces (S3)
  static/
    admin/             # HTML/CSS/JS do painel admin
    check/             # HTML/CSS/JS do Check Web
      i18n-dictionaries.js   # Dicionários pt/en/zh/ms/id/tl
      i18n.js                # Função t() com fallback para pt
      accident.js            # Lógica JS do Modo Acidente
      accident-camera.js     # Captura de vídeo (getUserMedia)
```

## Convenções de código

- **Modelos**: `mapped_column` + `Mapped[T]` (SQLAlchemy 2.x). JSON serializado em `Text` (não `Column(JSON)`), consistente com `admin_monitored_projects_json`.
- **Schemas**: Pydantic v2. Request bodies são classes separadas das response models.
- **Eventos de log**: `log_event(db, source, action, status, message, ...)` — campo `action` é `String(16)`; manter ≤ 16 caracteres.
- **Notificações SSE**: chamar `notify_admin_data_changed()` e/ou `notify_web_check_data_changed()` após qualquer mutação que deva refletir na UI em tempo real.
- **Testes**: pytest com SQLite em memória ou arquivo temporário. Fixture padrão: `SessionLocal` apontando para `test_checking.db` ou factory isolada por `tmp_path`.

---

## Identidade de admin (duas tabelas, uma ponte)

O sistema tem **duas tabelas de identidade** que coexistem e são pareadas pela `chave` (4 caracteres alfanuméricos):

| Tabela | Papel | FKs que apontam para esta tabela |
|---|---|---|
| `users` | Pessoa: RFID, perfil, login, senha. Identidade operacional. | Quase tudo: `check_events.user_id`, `opened_by_user_id`, `triggered_by_user_id`, etc. |
| `admin_users` | Identidade de **auditoria de admin** (com `password_hash` próprio, legado). | Colunas `*_by_admin_id` e `actor_user_id` em tabelas de auditoria. |

A sessão administrativa no cookie guarda `users.id` (apesar de a chave de sessão se chamar `admin_user_id` — nome enganoso, mantido por compatibilidade). `require_full_admin_session` retorna um `User`, **não** um `AdminUser`.

### Regra de ouro

> **Qualquer coluna FK → `admin_users.id` (nomes terminados em `_by_admin_id` ou `actor_user_id`) DEVE receber o ID via `services.admin_identity`, nunca `User.id` direto.**

Em produção (Postgres) a FK é enforçada. Em dev (SQLite) costuma estar desligada — bugs desse tipo passam em dev e quebram em prod com `ForeignKeyViolation`. Foi exatamente esse o bug que impedia o admin de abrir um acidente.

### Helpers e dependência

`sistema/app/services/admin_identity.py`:

| Símbolo | Uso |
|---|---|
| `AdminActorIdentity(user, admin_user)` | Dataclass que carrega o par. `identity.user.id` para FK→`users.id`; `identity.admin_user.id` para FK→`admin_users.id`. |
| `ensure_admin_user_by_chave(db, chave, nome_completo)` | Upsert idempotente do `AdminUser` por `chave`. Cria se ausente, atualiza `nome_completo` se mudou. |
| `resolve_admin_user_for_user(db, user)` | Atalho: dado um `User`, devolve o `AdminUser` pareado (criando se necessário). |

`sistema/app/services/admin_auth.py`:

| Dependência FastAPI | Retorna | Quando usar |
|---|---|---|
| `require_full_admin_session` | `User` | Endpoints que só precisam validar acesso admin e ler dados. |
| `require_admin_identity` | `AdminActorIdentity` | Endpoints que **escrevem** em colunas FK→`admin_users.id`. |

### Padrões corretos vs. armadilhas

**Correto — endpoint que grava em FK→admin_users:**

```python
@router.post("/accidents/open")
def open_admin_accident(
    payload: AdminAccidentOpenRequest,
    db: Session = Depends(get_db),
    identity: AdminActorIdentity = Depends(require_admin_identity),
):
    accident = open_accident(
        db, ...,
        opened_by_admin_id=identity.admin_user.id,  # admin_users.id
    )
```

**Armadilha — passar `users.id` para coluna `*_by_admin_id`:**

```python
# NÃO FAZER. Em Postgres isso explode com FK violation.
opened_by_admin_id=current_admin.id  # current_admin é um User → users.id
```

Quando o caller tem um `User` que não veio de `require_admin_identity` (ex.: rotas de transporte que usam `require_transport_session`), resolver explicitamente antes de gravar:

```python
actor_admin_user = resolve_admin_user_for_user(db, transport_user)
update_transport_assignment_boarding_time(
    db, ..., admin_user_id=actor_admin_user.id,
)
```

### Backfill em produção

A migração `0062_backfill_admin_users_for_existing_admins` cria a linha `admin_users` para cada `users` com perfil de admin (`1` ou `9`) que ainda não tenha espelho. Idempotente. Também emite um relatório (warning logger) de qualquer FK→admin_users órfã encontrada nas tabelas: `transport_assignments`, `transport_ai_llm_settings`, `transport_ai_project_llm_settings`, `transport_ai_runs`, `accidents`.

A migração é cinto e suspensórios: o upsert lento em `resolve_admin_user_for_user` já garante a linha no momento da escrita, mas a migração fecha a janela em hosts já implantados antes deste fix.

### Testes que blindam contra regressão

- `tests/test_admin_identity.py` — unit: `ensure_admin_user_by_chave` idempotente, `resolve_admin_user_for_user` cria par.
- `tests/test_admin_accident_endpoints.py` — integração HTTP: abrir/fechar acidente como admin, sem `admin_users` pré-existente, valida que a FK aponta para uma linha real. **Esse teste teria pegado o bug original.**
- `tests/test_admin_users_backfill_migration.py` — exercita a migração `0062` em SQLite limpo.

---

## Modo Acidente

### Visão geral do fluxo

O Modo Acidente é uma funcionalidade de segurança que permite registrar e coordenar a
resposta a acidentes em campo.

1. **Abertura**: pode ser iniciada pelo **admin** (via painel web) ou por qualquer **usuário autenticado** no Check Web. Apenas um acidente pode estar ativo por vez (índice parcial único `ix_accidents_single_active` em `closed_at IS NULL`).
2. **Relatório de situação**: enquanto o acidente está ativo, usuários informam sua zona (`waiting`/`safety`/`accident`) e status (`ok`/`help`). O sistema envia emails de alerta para usuários que reportam `status='help'`.
3. **Encerramento**: **somente o admin** pode encerrar um acidente. Ao encerrar, o sistema gera automaticamente um arquivo ZIP contendo XLSX de situação + vídeos capturados, e o disponibiliza para download.
4. **Histórico**: acidentes encerrados ficam listados com link para download do archive.

### Tabelas envolvidas

| Tabela | Descrição |
|---|---|
| `accidents` | Registro principal do acidente (número, projeto, abertura, encerramento) |
| `accident_user_reports` | Situação de cada usuário no acidente (zona + status) |
| `accident_video_uploads` | Vídeos enviados por usuários durante o acidente |
| `accident_archives` | Metadata do ZIP/XLSX gerado ao encerrar |
| `email_delivery_logs` | Fila e histórico de emails de emergência enviados |

Todas declaradas em `sistema/app/models.py`.

### Endpoints principais

**Admin** (prefixo `/api/admin`, requerem sessão admin):

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/accidents/active` | Estado atual (acidente ativo + tabela de situação) |
| `POST` | `/accidents/open` | Abre acidente (origin=`admin`) |
| `POST` | `/accidents/close` | Encerra acidente ativo; dispara geração de archive |
| `GET` | `/accidents` | Lista acidentes encerrados |
| `GET` | `/accidents/{id}/archive` | Download do ZIP do archive |
| `DELETE` | `/accidents/{id}` | Remove acidente (somente encerrado) |
| `GET` | `/accidents/wizard/projects` | Projetos disponíveis para o wizard |
| `GET` | `/accidents/wizard/locations` | Locais do projeto selecionado |

**Check Web** (prefixo `/api/web/check`, requerem chave válida):

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/check/accident/state` | Estado do acidente do ponto de vista do usuário |
| `POST` | `/check/accident/open` | Abre acidente (origin=`web`) |
| `POST` | `/check/accident/report` | Atualiza zona/status do usuário |
| `POST` | `/check/accident/video` | Upload de vídeo (multipart) |
| `GET` | `/check/accident/wizard/projects` | Projetos para o wizard web |
| `GET` | `/check/accident/wizard/locations` | Locais para o wizard web |

### Brokers SSE (tempo real)

Definidos em `sistema/app/services/admin_updates.py`:

- `checking_admin_updates` → notifica o painel admin (via `notify_admin_data_changed()`)
- `checking_web_check_updates` → notifica o Check Web (via `notify_web_check_data_changed()`)

Toda operação que muda estado do acidente deve chamar ambos os brokers para manter as UIs sincronizadas.

### Dependências externas

| Dependência | Uso | Configuração (.env) |
|---|---|---|
| **SMTP** | Envio de emails de alerta (`status='help'`) | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` |
| **DO Spaces** (S3) | Armazenamento de vídeos e archives ZIP | `DO_SPACES_KEY`, `DO_SPACES_SECRET`, `DO_SPACES_ENDPOINT`, `DO_SPACES_BUCKET` |

Em desenvolvimento (`app_env == "development"`), `object_storage.py` usa armazenamento local em `_local_root` quando as credenciais S3 não estão configuradas.

### Onde mexer

| Arquivo | Responsabilidade |
|---|---|
| `services/accident_lifecycle.py` | **Estado**: `open_accident`, `close_accident`, `upsert_user_safety_report`, `attach_video_upload`, `update_accident_membership_for_check_event`, `fire_accident_hook_for_check_event` |
| `services/accident_situation_table.py` | **Render**: `build_situation_rows()` — monta a lista de usuários com zona/status para exibição no admin e no response de estado |
| `services/accident_archive_builder.py` | **Archive**: `build_and_attach_archive_for_accident()` — gera XLSX + ZIP com vídeos e persiste o `AccidentArchive`; usa `object_storage` para upload remoto |
| `services/accident_numbering.py` | **Sequência**: geração do `accident_number` único e incremental |
| `services/email_sender.py` | **Email**: `deliver_pending_emails(log_ids)` — processa a fila `email_delivery_logs` e envia via SMTP |
| `services/email_templates.py` | **Templates**: HTML dos emails de alerta enviados a usuários com `status='help'` |
| `routers/admin.py` | Endpoints admin do acidente (linhas ~2008–2210) |
| `routers/web_check.py` | Endpoints web do acidente (linhas ~883–1080) |
| `static/check/accident.js` | Lógica JS do Modo Acidente no Check Web (SSE, polling, wizard, dialogs) |
| `static/check/accident-camera.js` | Captura de vídeo via `getUserMedia` + upload |
| `static/check/i18n-dictionaries.js` | Chaves i18n do Modo Acidente na seção `accident` do dicionário `pt` |

### Eventos de log gerados

Todos gravados via `log_event()` em `check_events` (visíveis na aba "Eventos" do admin):

| `action` | `source` | Momento |
|---|---|---|
| `accident_open` | `admin` ou `web` | Ao abrir acidente |
| `accident_close` | `admin` | Ao encerrar acidente |
| `accident_delete` | `admin` | Ao deletar acidente encerrado |
| `accident_report` | `web` | Ao atualizar zona/status do usuário |
| `accident_video` | `web` | Ao fazer upload de vídeo |
| `accident_email` | `system` | Após batch de entrega de emails |

> **Atenção**: `CheckEvent.action` é `String(16)`. Manter nomes de action com ≤ 16 caracteres.
