# Modo Acidente — Arquitetura e Fluxos

Documento de referência para o Modo Acidente do sistema Checking.
Legível em fonte monospace.

---

## 1. Diagrama de Arquitetura (fluxo de dados)

```
╔══════════════════════════════════════════════════════════════════════════╗
║  CLIENTES                                                                ║
║                                                                          ║
║   ┌─────────────────┐          ┌──────────────────────┐                 ║
║   │  Admin SPA      │          │  Check Web SPA       │                 ║
║   │  (Painel Admin) │          │  (Webapp do Usuário) │                 ║
║   └────────┬────────┘          └──────────┬───────────┘                 ║
╚════════════╪══════════════════════════════╪════════════════════════════╝
             │                              │
             │  cookie de sessão admin      │  cookie de sessão web
             ▼                              ▼
╔══════════════════════════════════════════════════════════════════════════╗
║  FASTAPI ROUTERS                                                         ║
║                                                                          ║
║   sistema/app/routers/admin.py            sistema/app/routers/web_check.py
║   ─────────────────────────────           ────────────────────────────── ║
║   GET  /admin/accidents/active            GET  /check/accident/state     ║
║   POST /admin/accidents/open              POST /check/accident/open      ║
║   POST /admin/accidents/close             POST /check/accident/report    ║
║   GET  /admin/accidents                   POST /check/accident/video     ║
║   GET  /admin/accidents/{id}/archive                                     ║
║   DELETE /admin/accidents/{id}                                           ║
╚═══════════════╪══════════════════════════════╪════════════════════════╝
                │                              │
                ▼                              ▼
╔══════════════════════════════════════════════════════════════════════════╗
║  SERVICES (camada de lógica)                                             ║
║                                                                          ║
║   accident_lifecycle.py          accident_archive_builder.py            ║
║   ─────────────────────          ─────────────────────────              ║
║   open_accident()                build_and_attach_archive_for_accident() ║
║   close_accident()                                                       ║
║   upsert_user_safety_report()    accident_situation_table.py            ║
║   attach_video_upload()          ─────────────────────────              ║
║                                  render_situation_table_html()          ║
║   email_sender.py                                                        ║
║   ─────────────                                                          ║
║   deliver_pending_emails()                                               ║
╚═══════════════╪══════════════════════════════════════════════════════╝
                │
                ▼
╔══════════════════════════════════════════════════════════════════════════╗
║  BANCO DE DADOS (PostgreSQL prod / SQLite dev)                           ║
║                                                                          ║
║   accidents                  accident_user_reports                      ║
║   accident_video_uploads     accident_archives                           ║
║   email_delivery_logs        check_events  (audit log)                  ║
╚═══════════════╪══════════════════════════════════════════════════════╝
                │
                ▼
╔══════════════════════════════════════════════════════════════════════════╗
║  POSTGRES NOTIFY BROKERS  (sistema/app/services/admin_updates.py)        ║
║                                                                          ║
║   checking_admin_updates          checking_web_check_updates            ║
║   (atualiza painel admin SSE)     (atualiza check web SSE)              ║
╚═══════════════╪════════════════════════╪════════════════════════════╝
                │                        │
                ▼                        ▼
╔══════════════════════════════════════════════════════════════════════════╗
║  SSE STREAMS                                                             ║
║                                                                          ║
║   GET /admin/stream               GET /check/stream                     ║
║   (Admin SPA recebe push)         (Check Web SPA recebe push)           ║
╚══════════════════════════════════════════════════════════════════════════╝
                │                        │
                ▼                        ▼
          Admin SPA                 Check Web SPA
          (atualiza UI)             (atualiza UI)


Dependências externas:
  ┌──────────────────────────────────────────────────────────┐
  │  SMTP (email_sender.py)   DigitalOcean Spaces (object_storage.py)  │
  │  → e-mails de socorro     → upload de vídeos + ZIPs de arquivo     │
  └──────────────────────────────────────────────────────────┘
```

---

## 2. Diagrama de Estados do Acidente

```
                        ┌────────────────────────────────────────────────┐
                        │  NOTA: só um acidente pode estar ABERTO        │
                        │  ao mesmo tempo (índice único parcial sobre     │
                        │  closed_at IS NULL na tabela accidents).        │
                        └────────────────────────────────────────────────┘

  ╔══════╗    admin POST /accidents/open     ╔════════╗
  ║      ║   ─────────────────────────────►  ║        ║
  ║ NULL ║     OU                            ║ ABERTO ║
  ║      ║   web POST /check/accident/open   ║        ║
  ╚══════╝   ─────────────────────────────►  ╚════╤═══╝
                                                  │
                              admin POST /accidents/close
                              (gera arquivo ZIP em background)
                                                  │
                                                  ▼
                                          ╔═══════════╗
                                          ║           ║
                                          ║ ENCERRADO ║
                                          ║           ║
                                          ╚═════╤═════╝
                                                │
                                  admin DELETE /accidents/{id}
                                  (somente perfil=9, super-admin)
                                                │
                                                ▼
                                         ╔═══════════╗
                                         ║           ║
                                         ║  REMOVIDO ║
                                         ║  (hard    ║
                                         ║  delete)  ║
                                         ╚═══════════╝

Campos que controlam o estado na tabela accidents:
  opened_at   → NOT NULL sempre (definido ao abrir)
  closed_at   → NULL = aberto;  NOT NULL = encerrado
  (remoção)   → DELETE físico da linha (sem soft-delete)
```

---

## 3. Sequência do Ciclo de Pedido de Ajuda (status = 'help')

```
  Check Web SPA          web_check.py            accident_lifecycle.py
       │                      │                         │
       │  POST /check/         │                         │
       │  accident/report      │                         │
       │  {zone:"accident",    │                         │
       │   status:"help"}      │                         │
       │──────────────────────►│                         │
       │                       │  upsert_user_safety_    │
       │                       │  report(db, ...)        │
       │                       │────────────────────────►│
       │                       │                         │ INSERT/UPDATE
       │                       │                         │ accident_user_reports
       │                       │                         │ (zone="accident",
       │                       │                         │  status="help")
       │                       │◄────────────────────────│
       │                       │  retorna report         │
       │                       │                         │
       │                       │  cria EmailDeliveryLog  │
       │                       │  (delivery_status=      │
       │                       │   "queued") para admins │
       │                       │  notifyBroker()         │
       │                       │  (web+admin channels)   │
       │◄──────────────────────│                         │
       │  200 OK               │                         │
       │                       │                         │
                               │
                        email_sender.py (background task)
                               │
                               │  deliver_pending_emails()
                               │  ─────────────────────
                               │  busca EmailDeliveryLog
                               │  onde status="queued"
                               │
                               │  para cada destinatário:
                               │  ┌─────────────────────────────┐
                               │  │  SMTP send (smtplib)        │
                               │  │  → e-mail com tabela HTML   │
                               │  │    da situação do acidente  │
                               │  │  → generated by             │
                               │  │    accident_situation_table │
                               │  └─────────────────────────────┘
                               │
                               │  UPDATE email_delivery_logs
                               │  SET status="sent"|"failed"
                               │
                               │  log_event(...,
                               │    action="accident_email",
                               │    details="recipient_count=N
                               │             sent=N failed=N")
                               │
                        Admin e-mail inbox ◄─────────────
                        (recebe alerta de socorro)
```

---

## 4. Mapa de Privilégios Admin por Endpoint

```
┌──────────────────────────────────────────────────┬──────────────────────────────┬────────────────────────────────────┐
│ Endpoint                                         │ Autenticação                 │ Requisito de perfil                │
├──────────────────────────────────────────────────┼──────────────────────────────┼────────────────────────────────────┤
│ GET  /admin/accidents/active                     │ require_admin_session        │ Qualquer admin autenticado         │
│                                                  │                              │ (perfil=0, 1, 9, 12, etc.)        │
├──────────────────────────────────────────────────┼──────────────────────────────┼────────────────────────────────────┤
│ POST /admin/accidents/open                       │ require_full_admin_session   │ Precisa ter dígito "1" OU "9"     │
│ POST /admin/accidents/close                      │                              │ no perfil (full admin ou super)    │
│ GET  /admin/accidents                            │                              │ Ex.: perfil=1, 9, 12, 19          │
│ GET  /admin/accidents/{id}/archive               │                              │                                    │
│ GET  /admin/accidents/wizard/projects            │                              │                                    │
│ GET  /admin/accidents/wizard/locations           │                              │                                    │
├──────────────────────────────────────────────────┼──────────────────────────────┼────────────────────────────────────┤
│ DELETE /admin/accidents/{id}                     │ require_full_admin_session   │ APENAS perfil=9 (super-admin)      │
│                                                  │ + verificação interna        │ Outros perfis recebem HTTP 403     │
├──────────────────────────────────────────────────┼──────────────────────────────┼────────────────────────────────────┤
│ GET  /check/accident/state                       │ sessão web do usuário        │ Usuário com check-in ativo         │
│ POST /check/accident/open                        │                              │ no projeto correto                 │
│ POST /check/accident/report                      │                              │                                    │
│ POST /check/accident/video                       │                              │                                    │
└──────────────────────────────────────────────────┴──────────────────────────────┴────────────────────────────────────┘

Sistema de perfil (dígitos compostos):
  perfil=0   → Acesso limitado (somente checkin/checkout)
  perfil=1   → Full admin (dígito "1")
  perfil=2   → Transport access (dígito "2")
  perfil=9   → Super-admin: FULL_ACCESS_DIGIT, passa todas as verificações
  perfil=12  → Full admin + Transport
  perfil=9   → Super-admin (passa require_full_admin_session implicitamente)

  Regra: user_profile_has_access(perfil, "X") retorna True se:
    • dígito "9" (FULL_ACCESS_DIGIT) está em str(perfil), OU
    • dígito "X" está em str(perfil)
```

---

## 5. Mapa de Arquivos por Função

```
Função                          Arquivo principal
──────────────────────────────  ──────────────────────────────────────────────────────
Estado do acidente (CRUD)       sistema/app/services/accident_lifecycle.py
Renderização da tabela HTML     sistema/app/services/accident_situation_table.py
Geração de ZIP/XLSX de arquivo  sistema/app/services/accident_archive_builder.py
Envio de e-mails de socorro     sistema/app/services/email_sender.py
Storage de objetos (vídeo/ZIP)  sistema/app/services/object_storage.py
Endpoints admin                 sistema/app/routers/admin.py  (linhas ~2008–2216)
Endpoints web check             sistema/app/routers/web_check.py  (linhas ~883–1080)
Modelos de banco                sistema/app/models.py  (classes Accident*)
Schemas Pydantic                sistema/app/schemas.py  (AccidentRequest*, AccidentState*)
Notificações SSE                sistema/app/services/admin_updates.py
Autenticação admin              sistema/app/services/admin_auth.py
Log de eventos                  sistema/app/services/event_logger.py  → tabela check_events
```

---

## 6. Tabelas do Banco de Dados

```
accidents
  id                       INTEGER PK
  accident_number          INTEGER ≥ 0  (sequência global, não reutilizado)
  project_id               FK → projects
  project_name_snapshot    TEXT         (snapshot no momento da abertura)
  location_name_snapshot   TEXT
  location_is_registered   BOOLEAN
  origin                   TEXT  CHECK IN ('admin','web')
  opened_by_admin_id       FK → users (nullable)
  opened_by_user_id        FK → users (nullable)
  opened_at                TIMESTAMP
  closed_by_admin_id       FK → users (nullable)
  closed_at                TIMESTAMP  (NULL = aberto)
  archive_object_key       TEXT  (nullable, preenchido após fechar)
  ──────────────────────────────────────────────────────────
  CONSTRAINT ck_accidents_origin_allowed CHECK origin IN (...)
  CONSTRAINT ck_accidents_number_non_negative CHECK accident_number >= 0
  INDEX ix_accidents_single_active UNIQUE WHERE closed_at IS NULL
    → garante no máximo 1 acidente aberto ao mesmo tempo

accident_user_reports
  id                       INTEGER PK
  accident_id              FK → accidents CASCADE
  user_id                  FK → users
  user_chave_snapshot      TEXT
  user_name_snapshot       TEXT
  user_phone_snapshot      TEXT  (nullable)
  user_projects_snapshot   TEXT  (JSON serializado)
  user_local_snapshot      TEXT
  zone                     TEXT  CHECK IN ('waiting','safety','accident')
  status                   TEXT  CHECK IN ('waiting','ok','help')
  reported_at              TIMESTAMP  (nullable)
  last_checkin_action      TEXT  CHECK IN ('check-in','check-out',NULL)
  last_action_at           TIMESTAMP  (nullable)
  UNIQUE (accident_id, user_id)

accident_video_uploads
  id                       INTEGER PK
  idempotency_key          TEXT  UNIQUE
  accident_id              FK → accidents CASCADE
  user_id                  FK → users
  object_key               TEXT
  public_url               TEXT
  content_type             TEXT
  size_bytes               INTEGER
  duration_seconds         FLOAT  (nullable)
  captured_at              TIMESTAMP
  created_at               TIMESTAMP
  INDEX ix_accident_video_uploads_accident_user (accident_id, user_id)

accident_archives
  id                       INTEGER PK
  accident_id              FK → accidents CASCADE  UNIQUE
  snapshot_json            TEXT
  xlsx_object_key          TEXT
  zip_object_key           TEXT
  size_bytes               INTEGER
  generated_at             TIMESTAMP

email_delivery_logs
  id                       INTEGER PK
  accident_id              FK → accidents SET NULL  (nullable)
  triggered_by_user_id     FK → users  (nullable)
  recipient_email          TEXT
  recipient_chave          TEXT  (nullable)
  subject                  TEXT
  body_snapshot            TEXT
  delivery_status          TEXT  CHECK IN ('queued','sent','failed')
  error_message            TEXT  (nullable)
  queued_at                TIMESTAMP
  sent_at                  TIMESTAMP  (nullable)
  retry_count              INTEGER  DEFAULT 0
  INDEX ix_email_delivery_logs_accident (accident_id)
```

---

## 7. Eventos de Log (`check_events`)

| `action` (≤16 chars)  | Quando é gerado                                      | `source`      |
|-----------------------|------------------------------------------------------|---------------|
| `accident_open`       | Abertura do acidente (admin ou web)                  | `admin`/`web` |
| `accident_close`      | Encerramento do acidente (admin)                     | `admin`       |
| `accident_delete`     | Remoção do acidente (admin perfil=9)                 | `admin`       |
| `accident_report`     | Usuário reporta zona/status via check web            | `web`         |
| `accident_video`      | Upload de vídeo pelo usuário via check web           | `web`         |
| `accident_email`      | Lote de e-mails de socorro processado                | `web`/`admin` |

Todos visíveis na aba **"Eventos"** do painel admin (`/admin/#eventos`).
