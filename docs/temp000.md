# Plano de Implementação — Botão 'Acidente Reportado' / Modo Acidente

Fonte do requisito: [docs/descritivos/funcionamento_botao_acidente_reportado.txt](descritivos/funcionamento_botao_acidente_reportado.txt)

## 0. Visão Geral, Princípios e Arquitetura

### 0.1 Áreas afetadas

- **API FastAPI** ([sistema/app/](../sistema/app/)) — novos modelos, schemas, services, routers e infraestrutura de e-mail e armazenamento de vídeos.
- **Website do administrador** ([sistema/app/static/admin/](../sistema/app/static/admin/)) — botão de gatilho, aba 'Acidente', tabela 'Situação de Pessoal', tabela 'Acidentes' (Cadastro), tema 'modo acidente'.
- **Aplicação Web 'Checking Web'** ([sistema/app/static/check/](../sistema/app/static/check/)) — botão 'Reportar Acidente', wizard, container 'Estou em:', confirmações, notificação, tema 'modo acidente', captura de vídeo, ajuste de permissões.
- **Dashboard de Transporte** — explicitamente **NÃO** afetado nesta entrega (item 1 do descritivo, após correção).

### 0.2 Princípios não-funcionais

1. **Tempo real, sempre.** Quando um acidente é aberto/encerrado, ou quando qualquer usuário envia status, *todas* as instâncias abertas (admin e Checking Web) devem refletir a mudança em <2s, sem ação manual do usuário.
2. **Multi-worker / multi-instância.** A API roda em múltiplos workers (Uvicorn/Gunicorn). Reaproveitar o padrão Postgres `LISTEN/NOTIFY` já existente em [sistema/app/services/admin_updates.py](../sistema/app/services/admin_updates.py) (classe `AdminUpdatesBroker`) para garantir fan-out cross-worker.
3. **Idempotência.** Abertura, encerramento, status e upload precisam tolerar retries do cliente sem duplicar eventos.
4. **Estado canônico no banco.** O "Modo Acidente" não é uma flag de processo em memória — é um registro em `accidents` com `closed_at IS NULL`. Qualquer worker derruba o estado a partir do banco.
5. **Tema vermelho como overlay puramente CSS.** Não duplicar componentes; aplicar uma classe `accident-mode` no `<body>` (admin) e na raiz do shell (check) e usar variáveis CSS já existentes.
6. **Sem regressão funcional.** Tabelas 'Usuários em Check-in', 'Usuários em Check-out', 'Forms', 'Inativos', 'Relatórios', 'Eventos' continuam funcionando normalmente durante o modo acidente.
7. **Recuperação.** Cliente que abre a página durante um acidente em curso recebe o estado completo na primeira request `/state`.

### 0.3 Fontes da verdade no descritivo

| Item descritivo | Mecanismo no plano |
|---|---|
| 3.1 / 3.2 — botão | Phases 8.1, 9.1 |
| 4.1 / 4.2 — wizard | Phases 8.2, 9.2 |
| 5.1.1 — aba Acidente + tabela Situação de Pessoal | Phase 8.3 |
| 5.1.1 — prioridades 1–5 / cores piscantes | Phase 8.4 |
| 5.1.2 — Checking Web 'Estou em:' / Situações 1, 2, 3 | Phase 9.3 |
| 5.2 Ação 1 — modo acidente disparado pelo usuário | Phases 3, 4 |
| 5.2 Ação 2 — primeiro registro = autor | Phase 3 |
| 5.2 Ação 3 — e-mail SMTP | Phase 6 |
| 5.2 Ação 4 — Audio & Video / Reportar Novo Acidente | Phase 9.4 + Phase 7 |
| 6 — encerramento + tabela Acidentes + ZIP/XLSX | Phases 4, 8.5, 10 |

### 0.4 Numeração do acidente

- Sequência global de 4 dígitos zero-padded começando em **0000** (item 6 do descritivo).
- Implementada via tabela `accidents` com coluna `accident_number` (inteiro), gerada como `coalesce(max(accident_number), -1) + 1` dentro de uma transação `SERIALIZABLE` ou `SELECT ... FOR UPDATE` numa linha-âncora.
- Renderização para exibição/arquivo XLSX: `f"{accident_number:04d}"`.

---

## Phase 1 — Migrações de banco e modelos SQLAlchemy

Arquivo a editar: [sistema/app/models.py](../sistema/app/models.py).
Arquivo a editar: [sistema/app/schemas.py](../sistema/app/schemas.py).

### 1.1 Novo modelo `Accident`

```python
class Accident(Base):
    __tablename__ = "accidents"
    __table_args__ = (
        UniqueConstraint("accident_number", name="uq_accidents_accident_number"),
        Index("ix_accidents_open", "closed_at"),  # NULL == aberto
        CheckConstraint("accident_number >= 0", name="ck_accidents_number_non_negative"),
        CheckConstraint("origin IN ('admin', 'web')", name="ck_accidents_origin_allowed"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    accident_number: Mapped[int] = mapped_column(Integer, nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    project_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    location_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    location_is_registered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    origin: Mapped[str] = mapped_column(String(16), nullable=False)  # 'admin' | 'web'
    opened_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    opened_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archive_object_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

Invariante única que precisa ser garantida pela aplicação (e por um teste explícito): **no máximo um `Accident` com `closed_at IS NULL`**. Usar índice parcial:

```sql
CREATE UNIQUE INDEX ix_accidents_single_active ON accidents (1) WHERE closed_at IS NULL;
```

Adicionar como `Index` nomeado `ix_accidents_single_active` com `postgresql_where=text("closed_at IS NULL")` e `sqlite_where` equivalente (literal `1` não funciona em SQLite — usar a coluna `closed_at` e o `where`).

### 1.2 Novo modelo `AccidentUserReport`

Representa **a última resposta** de cada usuário àquele acidente. Substituível (upsert por `(accident_id, user_id)`).

```python
class AccidentUserReport(Base):
    __tablename__ = "accident_user_reports"
    __table_args__ = (
        UniqueConstraint("accident_id", "user_id", name="uq_accident_user_reports_accident_user"),
        CheckConstraint("zone IN ('waiting', 'safety', 'accident')", name="ck_accident_user_reports_zone_allowed"),
        CheckConstraint("status IN ('waiting', 'ok', 'help')", name="ck_accident_user_reports_status_allowed"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    accident_id: Mapped[int] = mapped_column(ForeignKey("accidents.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user_chave_snapshot: Mapped[str] = mapped_column(String(4), nullable=False)
    user_name_snapshot: Mapped[str] = mapped_column(String(180), nullable=False)
    user_phone_snapshot: Mapped[str | None] = mapped_column(String(40), nullable=True)
    user_projects_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    user_local_snapshot: Mapped[str | None] = mapped_column(String(40), nullable=True)
    zone: Mapped[str] = mapped_column(String(16), nullable=False, default="waiting")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="waiting")
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checkin_action: Mapped[str | None] = mapped_column(String(16), nullable=True)  # 'check-in' / 'check-out'
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

Mapeamento situação → `(zone, status)`:

| Resposta do usuário | `zone` | `status` |
|---|---|---|
| (não respondeu) | `waiting` | `waiting` |
| Zona de Segurança | `safety` | `ok` |
| Zona de Acidente + Estou bem | `accident` | `ok` |
| Zona de Acidente + Preciso de Ajuda | `accident` | `help` |

A coluna `user_phone_snapshot` — **não existe** ainda telefone na tabela `users` (ver [sistema/app/models.py:61-83](../sistema/app/models.py#L61-L83)). Decisão: no carregamento da `Situação de Pessoal` o telefone fica **vazio** por enquanto. Quando o cadastro de telefone for adicionado posteriormente, o snapshot já estará pronto.

### 1.3 Novo modelo `AccidentVideoUpload`

```python
class AccidentVideoUpload(Base):
    __tablename__ = "accident_video_uploads"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_accident_video_uploads_idempotency_key"),
        Index("ix_accident_video_uploads_accident_user", "accident_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    accident_id: Mapped[int] = mapped_column(ForeignKey("accidents.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    object_key: Mapped[str] = mapped_column(String(255), nullable=False)  # caminho no DO Spaces
    public_url: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

### 1.4 Novo modelo `AccidentArchive`

Registra o ZIP gerado no momento do encerramento (snapshot congelado da tabela 'Situação de Pessoal', conforme item 6 do descritivo).

```python
class AccidentArchive(Base):
    __tablename__ = "accident_archives"
    __table_args__ = (UniqueConstraint("accident_id", name="uq_accident_archives_accident_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    accident_id: Mapped[int] = mapped_column(ForeignKey("accidents.id", ondelete="CASCADE"), nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)  # tabela congelada
    xlsx_object_key: Mapped[str] = mapped_column(String(255), nullable=False)
    zip_object_key: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

### 1.5 Novo modelo `EmailDeliveryLog`

Auditoria das mensagens enviadas (não é cache, é log forense — necessário porque é o único registro fora do servidor SMTP de que o e-mail saiu).

```python
class EmailDeliveryLog(Base):
    __tablename__ = "email_delivery_logs"
    __table_args__ = (
        CheckConstraint("delivery_status IN ('queued', 'sent', 'failed')", name="ck_email_delivery_logs_status_allowed"),
        Index("ix_email_delivery_logs_accident", "accident_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    accident_id: Mapped[int | None] = mapped_column(ForeignKey("accidents.id", ondelete="SET NULL"), nullable=True)
    triggered_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_chave: Mapped[str | None] = mapped_column(String(4), nullable=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
```

### 1.6 Pydantic schemas a adicionar em [sistema/app/schemas.py](../sistema/app/schemas.py)

- `AdminAccidentOpenRequest` (`project_id: int`, `location_id: int | None`, `custom_location_name: str | None`).
- `WebAccidentOpenRequest` (mesmos campos + `chave`, `zone`, `status` do reporter).
- `AccidentLocationOption` (id, nome, registered).
- `AccidentProjectOption` (id, nome).
- `AdminAccidentStateResponse`:
  - `is_active: bool`
  - `accident: AccidentSummary | None`
  - `situation_rows: list[SituacaoPessoalRow]` — array sempre presente quando `is_active=True`
- `WebAccidentStateResponse`:
  - `is_active: bool`
  - `project_name: str | None`
  - `location_name: str | None`
  - `current_user_report: WebAccidentUserReport | None`
- `WebAccidentReportRequest` (`chave: str`, `zone: 'safety'|'accident'`, `status: 'ok'|'help'`).
- `AccidentVideoUploadResponse` (`video_id`, `public_url`, `created_at`).
- `AccidentClosedRow` (linha da tabela 'Acidentes' do Cadastro).
- `SituacaoPessoalRow`:
  - `event_time: datetime`
  - `name: str`
  - `chave: str`
  - `projects: list[str]`
  - `local: str | None`
  - `zone: str`  *(`Aguardando` / `Segurança` / `Acidente`)*
  - `status: str`  *(`Aguardando` / `OK` / `AJUDA`)*
  - `phone: str | None`
  - `videos: list[AccidentVideoLink]`
  - `priority: int`  *(1–5 conforme descritivo)*
  - `row_color: Literal['white','blinking-red','yellow','turquoise','light-green']`

### 1.7 Estratégia de criação de tabelas

Hoje [sistema/app/main.py:230-233](../sistema/app/main.py#L230-L233) chama `Base.metadata.create_all` apenas em `app_env == "development"`. Não há Alembic configurado.

Manter o padrão: novas tabelas surgem automaticamente em dev. Para produção (Digital Ocean), gerar o DDL manualmente uma única vez e aplicá-lo via psql. Adicionar um script utilitário `sistema/scripts/migrate_accidents_v1.sql` com:

- `CREATE TABLE accidents ...`
- `CREATE TABLE accident_user_reports ...`
- `CREATE TABLE accident_video_uploads ...`
- `CREATE TABLE accident_archives ...`
- `CREATE TABLE email_delivery_logs ...`
- O índice parcial `ix_accidents_single_active`.

### 1.8 Testes desta fase

`tests/models/test_accident_models.py`:
- Cria dois `Accident` com `closed_at IS NULL` na mesma transação → segundo `INSERT` falha (índice parcial).
- Encerra um e abre outro → permitido.
- `AccidentUserReport` com `zone` inválido → falha.
- Upsert de `AccidentUserReport` mantém `created_at` original e atualiza `updated_at`.

---

## Phase 2 — Infraestrutura de tempo real (broker estendido + SSE da Checking Web)

Arquivo a editar: [sistema/app/services/admin_updates.py](../sistema/app/services/admin_updates.py).
Arquivo a editar: [sistema/app/main.py](../sistema/app/main.py).
Arquivo a editar: [sistema/app/routers/web_check.py](../sistema/app/routers/web_check.py).

### 2.1 Novo broker `web_check_updates_broker`

Hoje existem dois brokers: `admin_updates_broker` (canal `checking_admin_updates`) e `transport_updates_broker` (canal `checking_transport_updates`).
A Checking Web ainda **não tem** stream geral — só assina o de transporte. Para o modo acidente precisar atingir todos os usuários web, criar um terceiro:

```python
web_check_updates_broker = AdminUpdatesBroker("checking_web_check_updates")
```

`start_realtime_brokers()` e `stop_realtime_brokers()` passam a iniciar/parar também esse broker. Adicionar helper:

```python
def notify_web_check_data_changed(reason: str = "refresh", *, metadata: dict[str, object] | None = None) -> None:
    web_check_updates_broker.publish(reason=reason, metadata=metadata)
```

### 2.2 Razões (reasons) novas

Padronizar os `reason` que serão publicados em **ambos** os brokers (`admin` e `web_check`) durante a feature:

| `reason` | Disparada quando |
|---|---|
| `accident_opened` | Acidente acaba de ser criado (origem admin ou web). |
| `accident_closed` | Admin confirmou encerramento. |
| `accident_user_report` | Qualquer `AccidentUserReport` foi inserido/atualizado. |
| `accident_video_uploaded` | Novo vídeo foi anexado. |

`metadata` pode conter `{"accident_id": ..., "accident_number": ..., "project_name": ...}` para que o cliente abra/atualize o estado correto sem refetch desnecessário.

### 2.3 Novo endpoint `/api/web/check/stream`

Arquivo: [sistema/app/routers/web_check.py](../sistema/app/routers/web_check.py).
- Espelha o padrão de `/api/web/transport/stream` ([sistema/app/routers/web_check.py:553-585](../sistema/app/routers/web_check.py#L553-L585)).
- Autenticação: sessão web (`_require_matching_authenticated_web_user`).
- Subscribe em `web_check_updates_broker`, keep-alive a cada 15s.
- Emitir `data: {"reason": "connected"}` na conexão.

### 2.4 Publicar em ambos os brokers

Cada serviço que abrir/encerrar acidente ou registrar status precisa chamar:

```python
notify_admin_data_changed("accident_opened", metadata={...})
notify_web_check_data_changed("accident_opened", metadata={...})
```

A duplicação é intencional — admin e checking-web são consumidores independentes; um payload publicado em `admin` não chega ao broker `web_check` (canais Postgres distintos).

### 2.5 Throttle no cliente

Replicar o `requestRefreshAllTables` debounce de 250ms (existe em [sistema/app/static/admin/app.js:5445-5453](../sistema/app/static/admin/app.js#L5445-L5453)) tanto na Checking Web quanto no admin — evita storm de refetch quando 50 usuários reportam status em 2s.

### 2.6 Testes desta fase

`tests/services/test_admin_updates_brokers.py`:
- Subscribe em `web_check_updates_broker`, publish, verificar payload entregue.
- Garantir que `start_realtime_brokers()` inicia os 3 (admin, transport, web_check).

---

## Phase 3 — Service layer: ciclo de vida do acidente

Arquivos novos:
- `sistema/app/services/accident_lifecycle.py`
- `sistema/app/services/accident_situation_table.py`
- `sistema/app/services/accident_numbering.py`

### 3.1 `accident_numbering.py`

Função única `next_accident_number(db: Session) -> int`. Implementação:

```python
def next_accident_number(db: Session) -> int:
    row = db.execute(
        text("SELECT COALESCE(MAX(accident_number), -1) + 1 FROM accidents")
    ).scalar_one()
    return int(row)
```

Chamar **dentro** da mesma transação que faz o `INSERT INTO accidents` e dependendo do banco usar `SELECT ... FOR UPDATE` numa âncora ou `SERIALIZABLE`. Como o índice parcial `ix_accidents_single_active` já impede dois acidentes ativos simultâneos, a corrida prática é nula — mas o teste deve cobrir.

### 3.2 `accident_lifecycle.py`

API pública do módulo:

```python
def open_accident(
    db: Session,
    *,
    origin: Literal["admin", "web"],
    project_id: int,
    location_id: int | None,
    custom_location_name: str | None,
    opened_by_admin_id: int | None,
    opened_by_user_id: int | None,
    reporter_zone: Literal["safety", "accident"] | None = None,
    reporter_status: Literal["ok", "help"] | None = None,
) -> Accident: ...
```

Comportamento:
1. Lock `SELECT ... FOR UPDATE` na tabela `accidents WHERE closed_at IS NULL` — se houver, retornar erro `AccidentAlreadyActiveError`.
2. Resolver `project_name_snapshot` a partir de `project_id`.
3. Resolver `location_name_snapshot`:
   - Se `location_id` fornecido → ler de `ManagedLocation.local`, `location_is_registered=True`.
   - Senão → usar `custom_location_name` validado/normalizado, `location_is_registered=False`.
4. Validação cruzada: o `ManagedLocation` precisa ter o projeto na sua coluna `projects_json` (item 4.1 do descritivo — o local apresentado pertence ao projeto). Se o usuário web reportar um local pertencente a outro projeto (item 4.2: o usuário pode transitar em áreas de outros projetos), aceitar mesmo assim quando origem = `web`.
5. `accident_number = next_accident_number(db)`.
6. `INSERT INTO accidents`.
7. **Pré-popular `accident_user_reports`** com `zone='waiting', status='waiting'` para *todos* os usuários cuja última atividade foi `check-in` na data de hoje (consulta a `CheckingHistory` ou `User.checkin = TRUE`). Tomar snapshots de nome, chave, projetos, local, telefone.
8. Se `origin='web'`: aplicar a Ação 2 do descritivo — atualizar o `AccidentUserReport` do `opened_by_user_id` para o `(zone, status)` informados pelo usuário. Se status = `help`, agendar e-mail (Phase 6) somente após confirmação (já confirmada implicitamente pelo fluxo de wizard).
9. `db.commit()`.
10. Publicar `accident_opened` em ambos os brokers.
11. Retornar o objeto `Accident`.

```python
def close_accident(
    db: Session,
    *,
    accident: Accident,
    closed_by_admin_id: int,
) -> AccidentArchive: ...
```

Comportamento:
1. Carregar snapshot completo da Situação de Pessoal (Phase 3.3) — congelar.
2. Gerar XLSX + ZIP via Phase 10 e fazer upload em DO Spaces; obter `object_key`s.
3. `INSERT INTO accident_archives`.
4. `UPDATE accidents SET closed_at = NOW(), closed_by_admin_id = ?, archive_object_key = ?`.
5. `db.commit()`.
6. Publicar `accident_closed` em ambos os brokers.
7. Retornar `AccidentArchive`.

```python
def upsert_user_safety_report(
    db: Session,
    *,
    accident: Accident,
    user: User,
    zone: Literal["safety", "accident"],
    status: Literal["ok", "help"],
) -> AccidentUserReport: ...
```

Comportamento:
1. Lock no row `accident_user_reports WHERE accident_id=? AND user_id=?`.
2. Atualizar `zone`, `status`, `reported_at=NOW()`, `updated_at=NOW()`. Se a linha não existir (caso usuário fez check-in depois do acidente abrir), criar.
3. `db.commit()`.
4. Se `status='help'` E o status anterior não era `help`, agendar envio de e-mail (Phase 6) — único disparo por usuário/acidente, evita reenvio se o usuário oscilar.
5. Publicar `accident_user_report` em ambos os brokers.

```python
def attach_video_upload(
    db: Session,
    *,
    accident: Accident,
    user: User,
    object_key: str,
    public_url: str,
    content_type: str,
    size_bytes: int,
    duration_seconds: int | None,
    idempotency_key: str,
) -> AccidentVideoUpload: ...
```

Comportamento:
1. `INSERT OR IGNORE` por `idempotency_key`.
2. Publicar `accident_video_uploaded` em ambos os brokers com `metadata={"accident_id": ..., "user_id": ...}`.

```python
def list_active_accident(db: Session) -> Accident | None: ...
def list_closed_accidents(db: Session) -> list[Accident]: ...
def get_accident(db: Session, accident_id: int) -> Accident: ...
def delete_accident(db: Session, *, accident: Accident) -> None: ...  # cascade
```

### 3.3 `accident_situation_table.py`

Função principal:

```python
def build_situation_rows(db: Session, *, accident: Accident) -> list[SituacaoPessoalRow]: ...
```

Comportamento (item 5.1.1 do descritivo):
1. Selecionar todos os `AccidentUserReport` de `accident.id` (LEFT JOIN com `User` para obter telefone/email atuais — mas a coluna 'telefone' não existe ainda, deixar vazio).
2. Selecionar todos os `AccidentVideoUpload` agrupados por `(accident_id, user_id)`.
3. Para cada `AccidentUserReport`, montar `SituacaoPessoalRow`:
   - `event_time`: `reported_at` se existir; senão `last_action_at`; senão `created_at`.
   - `priority` baseada no mapa abaixo (não em flag manual — derivada de `zone`+`status`):

| `zone` | `status` | `priority` | `row_color` |
|---|---|---|---|
| `accident` | `help` | 1 | `blinking-red` |
| `accident` | `ok` | 2 | `yellow` |
| `waiting` | `waiting` | 3 | `turquoise` |
| `safety` | `ok` | 4 | `light-green` |
| (check-out feito durante acidente) | 5 | `light-gray` |

Para discriminar prioridade 5: usar `last_checkin_action='check-out' AND last_action_at >= accident.opened_at`.

4. Ordenar por `(priority ASC, event_time DESC)`.
5. Renderizar campos para o frontend:
   - `zone` no payload: `"Aguardando"` | `"Segurança"` | `"Acidente"`.
   - `status` no payload: `"Aguardando"` | `"OK"` | `"AJUDA"`.

### 3.4 Hook em check-in / check-out durante modo acidente

Quando `CheckEvent` ou `CheckingHistory` é gravado e existe acidente ativo:
- Se for `check-in` de usuário ainda **não** presente em `accident_user_reports` → inserir linha em `waiting` (item 5.1.1 — usuários que fizeram check-in durante o modo acidente entram automaticamente).
- Se for `check-out` → manter linha existente (não remover), só atualizar `last_checkin_action='check-out'` e `last_action_at=NOW()`.

Ponto de chamada: serviço `forms_submit.py` ([sistema/app/services/forms_submit.py](../sistema/app/services/forms_submit.py)) — função que grava `CheckingHistory`. Acrescentar:

```python
active_accident = list_active_accident(db)
if active_accident is not None:
    update_accident_membership_for_check_event(db, accident=active_accident, user=user, action=action)
```

`update_accident_membership_for_check_event` vive em `accident_lifecycle.py` e publica `accident_user_report` no broker.

### 3.5 Testes desta fase

`tests/services/test_accident_lifecycle.py`:
- `open_accident` sem acidente ativo → cria com numeração 0000.
- `open_accident` com acidente ativo → `AccidentAlreadyActiveError`.
- `open_accident` pré-popula reports de quem está em check-in.
- `upsert_user_safety_report` de `help` agenda e-mail; de `ok` não.
- `close_accident` cria archive, marca `closed_at`, libera para novo acidente (próximo será 0001).
- `delete_accident` remove em cascata.
- `build_situation_rows` respeita ordem de prioridade.
- Hook check-in durante modo acidente cria report `waiting`.
- Hook check-out durante modo acidente mantém o report e atualiza `last_action_at`.

---

## Phase 4 — Endpoints — Admin

Arquivo a editar: [sistema/app/routers/admin.py](../sistema/app/routers/admin.py).

### 4.1 GET `/api/admin/accidents/active`

- Dependência: `require_admin_session` (qualquer admin autenticado, perfil 0/1/9).
- Retorna `AdminAccidentStateResponse`.
- `is_active=False` se não houver acidente em curso → `accident=None`, `situation_rows=[]`.

### 4.2 POST `/api/admin/accidents/open`

- Dependência: `require_full_admin_session` (perfil 1 ou 9).
- Body: `AdminAccidentOpenRequest`.
- Validações:
  - Projeto existe.
  - Pelo menos um entre `location_id` e `custom_location_name`.
- Chama `accident_lifecycle.open_accident(origin="admin", ...)`.
- Resposta: `AdminAccidentStateResponse` atualizado.

### 4.3 POST `/api/admin/accidents/close`

- Dependência: `require_full_admin_session`.
- Body: `{}` (somente confirma).
- Carrega `list_active_accident(db)`. Se `None` → 409 `Nenhum acidente em curso`.
- Chama `close_accident(...)` → resposta `AdminAccidentStateResponse` com `is_active=False` e a nova entrada em `closed_accidents`.

### 4.4 GET `/api/admin/accidents`

- Dependência: `require_full_admin_session`.
- Retorna `list[AccidentClosedRow]` com:
  - `accident_number_label` (zero-padded `0000`)
  - `project_name`
  - `author_label` (nome do admin ou do usuário que abriu)
  - `opened_at`, `closed_at`
  - `download_url` (= `/api/admin/accidents/{id}/archive`)
  - `can_delete: bool` — `True` se admin atual tem `perfil=9`.

### 4.5 DELETE `/api/admin/accidents/{accident_id}`

- Dependência: `require_full_admin_session` + checagem manual `current_admin.perfil == 9`.
- Falha com 403 caso contrário ("Apenas perfil 9 pode remover acidentes.").
- Falha com 409 caso `accident.closed_at IS NULL` ("Não é possível remover um acidente em curso. Encerre o Modo Acidente primeiro.").
- Remove o acidente (cascade deleta reports/videos/archive). Os arquivos em DO Spaces ficam preservados ou são apagados? **Decisão**: apagar do Spaces também via helper Phase 7.4.
- Publica `accident_closed` (para refresh da tabela 'Acidentes').

### 4.6 GET `/api/admin/accidents/{accident_id}/archive`

- Dependência: `require_full_admin_session`.
- Carrega `AccidentArchive`, gera URL pré-assinada do DO Spaces (validade 5 min) e retorna `RedirectResponse(307)` para ela.
- Alternativa: streaming via FastAPI usando boto3 `get_object` + `StreamingResponse`. **Decisão**: pré-assinatura é mais simples e barata em banda. Manter o redirect.

### 4.7 Wizard auxiliar — GET `/api/admin/accidents/wizard/projects`

- Retorna `list[AccidentProjectOption]` — todos os projetos cadastrados (item 4.1).
- Dependência: `require_full_admin_session`.

### 4.8 Wizard auxiliar — GET `/api/admin/accidents/wizard/locations`

- Query: `project_id: int`.
- Retorna `list[AccidentLocationOption]` — locais cadastrados cujo `projects_json` contém o projeto.
- Dependência: `require_full_admin_session`.

### 4.9 Notificação de eventos

Cada handler acima publica `accident_*` nos dois brokers (Phase 2.4). Cuidado: já há chamadas a `notify_admin_data_changed` ligadas a check-in/check-out — manter como estão. Adicionar `notify_web_check_data_changed` paralelamente para garantir refresh da Checking Web também durante o acidente.

### 4.10 Testes desta fase

`tests/routers/test_admin_accidents.py`:
- POST `/open` sem permissão → 401/403.
- POST `/open` cria; segundo POST → 409.
- POST `/close` sem acidente ativo → 409.
- POST `/close` gera archive e libera novo.
- DELETE por admin perfil 1 → 403.
- DELETE por admin perfil 9 → 204.
- GET `/active` reflete estado.
- GET `/wizard/projects` lista projetos.
- GET `/wizard/locations?project_id=X` filtra corretamente.

---

## Phase 5 — Endpoints — Checking Web

Arquivo a editar: [sistema/app/routers/web_check.py](../sistema/app/routers/web_check.py).

### 5.1 GET `/api/web/check/accident/state`

- Query: `chave`.
- Dependência: `_require_matching_authenticated_web_user(request, db, chave)`.
- Retorna `WebAccidentStateResponse`:
  - `is_active`
  - `accident_number_label` (zero-padded) e `project_name`, `location_name` (snapshots) quando ativo.
  - `current_user_report` — `{zone, status, reported_at}` ou `null`.

### 5.2 POST `/api/web/check/accident/open`

- Body: `WebAccidentOpenRequest`.
- Validações:
  - Usuário autenticado; `chave` confere.
  - Projeto existe (qualquer projeto do sistema — item 4.2, usuário pode reportar em projeto fora do seu).
  - Locação válida (do projeto escolhido) **ou** `custom_location_name`.
  - `zone`/`status` válidos.
- Chama `open_accident(origin="web", opened_by_user_id=..., reporter_zone=..., reporter_status=...)`.
- Resposta: `WebAccidentStateResponse` atualizado.

### 5.3 POST `/api/web/check/accident/report`

- Body: `WebAccidentReportRequest`.
- Carrega acidente ativo. Se nenhum → 409.
- Chama `upsert_user_safety_report(...)`.
- Resposta: `WebAccidentStateResponse` atualizado.

### 5.4 POST `/api/web/check/accident/video`

- `multipart/form-data`:
  - `chave: str`
  - `idempotency_key: str`
  - `video: UploadFile`
  - `duration_seconds: int | None`
- Validações:
  - Acidente ativo.
  - Usuário autenticado.
  - `content_type` na lista permitida (`video/webm`, `video/mp4`, `video/quicktime`).
  - `size_bytes` ≤ 50 MB (configurável).
- Sequência:
  1. Streaming do upload direto para DO Spaces (Phase 7.2). Não materializar no disco local.
  2. Calcular `object_key` no padrão `accidents/{accident_number:04d}/{user_chave}/{idempotency_key}.{ext}`.
  3. `attach_video_upload(...)` no service.
- Resposta: `AccidentVideoUploadResponse`.

### 5.5 GET `/api/web/check/accident/situation`

- Apenas leitura, exclusiva para a Checking Web (para o admin já há `/active`).
- **Decisão de privacidade**: este endpoint **não** retorna a tabela completa de Situação de Pessoal para a Checking Web (o descritivo nunca pede isso para o usuário comum). Pular.

### 5.6 SSE em `/api/web/check/stream`

Já definido em Phase 2.3 — o frontend usa esse stream para detectar `accident_opened`/`accident_closed`/`accident_user_report` e refazer chamadas a `/accident/state`.

### 5.7 Wizard auxiliares (mesma forma do admin)

- GET `/api/web/check/accident/wizard/projects` (todos os projetos).
- GET `/api/web/check/accident/wizard/locations?project_id=X` (locais do projeto).

### 5.8 Testes desta fase

`tests/routers/test_web_accidents.py`:
- POST `/open` cria + admin recebe broker event.
- POST `/report` upserta corretamente.
- POST `/video` rejeita tamanho > 50MB.
- POST `/video` idempotente (mesmo `idempotency_key` 2x → 1 registro).
- SSE recebe `accident_opened` quando outro cliente abre.

---

## Phase 6 — Serviço de e-mail (SMTP)

Arquivos novos:
- `sistema/app/services/email_settings.py` — leitura segura de config.
- `sistema/app/services/email_smtp_client.py` — wrapper síncrono em `aiosmtplib` ou `smtplib`.
- `sistema/app/services/email_sender.py` — fila e envio.
- `sistema/app/services/email_templates.py` — montagem do corpo.

### 6.1 Configuração

Adicionar em [sistema/app/core/config.py](../sistema/app/core/config.py):

```python
smtp_host: str | None = None
smtp_port: int = 587
smtp_username: str | None = None
smtp_password: str | None = None
smtp_use_tls: bool = True  # STARTTLS
smtp_use_ssl: bool = False  # SMTPS direto
smtp_sender_email: str | None = None
smtp_sender_name: str = "Checking App"
smtp_connect_timeout_seconds: int = 15
smtp_send_timeout_seconds: int = 30
smtp_max_retries: int = 3
```

Em produção esses valores virão do `.env` no Digital Ocean. Em dev, default `None` desabilita o envio (modo dry-run) e apenas grava `EmailDeliveryLog` com `delivery_status='queued'` e nota `SMTP disabled`.

### 6.2 Template "(CHECKING) PEDIDO DE SOCORRO"

Texto exato do descritivo (item 5.2 Ação 3):

```
Prezado <nome do destinatário>,

O usuário <nome>, chave <chave>, pede AJUDA IMEDIATA, ao reportar um acidente
ocorrido no projeto <projeto>, local <local>.

Esta mensagem foi disparada após o pedido de ajuda ter sido CONFIRMADO.

Atenciosamente,
Checking App
```

Em `email_templates.py`:

```python
def render_help_request_email(
    *,
    recipient_name: str,
    requester_name: str,
    requester_chave: str,
    project_name: str,
    location_name: str,
) -> tuple[str, str]:
    subject = "(CHECKING) PEDIDO DE SOCORRO"
    body = f"""Prezado {recipient_name},

O usuário {requester_name}, chave {requester_chave}, pede AJUDA IMEDIATA, ao reportar um acidente ocorrido no projeto {project_name}, local {location_name}.

Esta mensagem foi disparada após o pedido de ajuda ter sido CONFIRMADO.

Atenciosamente,
Checking App
"""
    return subject, body
```

### 6.3 Lista de destinatários

Pelo descritivo: "todos os usuários que estão cadastrados no projeto em que o usuário solicitou ajuda".

Query:

```sql
SELECT u.id, u.nome, u.chave, u.email
FROM users u
JOIN user_project_memberships m ON m.user_id = u.id
JOIN projects p ON p.id = m.project_id
WHERE p.name = :project_name
  AND u.email IS NOT NULL
  AND u.email != ''
```

Considera apenas usuários com e-mail cadastrado. Os sem e-mail são pulados (gravar `EmailDeliveryLog` com nota `Missing email` para auditoria).

### 6.4 Trigger

Em `accident_lifecycle.upsert_user_safety_report`, quando `status='help'` E `previous_status != 'help'`:

```python
queue_help_request_emails(
    db,
    accident=accident,
    requester=user,
)
```

`queue_help_request_emails` enfileira no `EmailDeliveryLog` (status `queued`) e dispara um background task FastAPI (`BackgroundTasks` injetado no router). Como a função roda dentro de um service, o trigger fica no router que chama o service.

### 6.5 Mecanismo de envio

Decisão: enviar inline via `BackgroundTasks` do FastAPI (simples e suficiente). Não precisa de Celery/RQ para o volume esperado.

Pseudocódigo:

```python
async def deliver_pending_emails(accident_id: int, email_log_ids: list[int]):
    async with smtp_connect() as client:
        for log_id in email_log_ids:
            log = db.get(EmailDeliveryLog, log_id)
            try:
                await client.send(...)
                log.delivery_status = "sent"
                log.sent_at = now_utc()
            except Exception as exc:
                log.delivery_status = "failed"
                log.error_message = str(exc)[:1000]
                log.retry_count += 1
            db.commit()
```

### 6.6 UI no admin (opcional mas recomendado)

Em "Cadastro", criar painel "Configuração de E-mail" (visível apenas para perfil 9). Atualmente as `endpoint_api_keys` já tem padrão de chave secreta — replicar para SMTP. **Escopo mínimo**: nesta entrega, o admin pode apenas **testar** a conexão (botão "Enviar e-mail de teste"). A configuração persiste no `.env`. Em release posterior pode-se migrar para uma tabela `smtp_settings` (`api_key_ciphertext` style, ver `TransportAILlmSettings`).

### 6.7 Testes desta fase

`tests/services/test_email_help_request.py`:
- Template renderiza com placeholders corretos.
- `queue_help_request_emails` cria N logs `queued`.
- Quando SMTP desabilitado, fica `queued` e não tenta enviar.
- Quando SMTP configurado (usar `aiosmtpd` mock em-memória), envia e marca `sent`.
- Retry counta certo em falha.
- Usuários sem e-mail são pulados, mas registrados com nota.
- Não dispara mais de uma vez para o mesmo usuário/acidente (idempotência via `status='help'` anterior).

---

## Phase 7 — Integração com Digital Ocean Spaces (vídeos + arquivos ZIP)

Arquivos novos:
- `sistema/app/services/object_storage.py`

### 7.1 Dependência

Adicionar `boto3` em `requirements.txt` (já é trivial; o `pyproject.toml`/`requirements.txt` é o local; verificar conforme estrutura do repo) e variáveis de configuração em [sistema/app/core/config.py](../sistema/app/core/config.py):

```python
do_spaces_endpoint_url: str | None = None  # ex.: "https://sgp1.digitaloceanspaces.com"
do_spaces_region: str = "sgp1"
do_spaces_bucket: str | None = None
do_spaces_access_key: str | None = None
do_spaces_secret_key: str | None = None
do_spaces_public_base_url: str | None = None
```

### 7.2 API do módulo

```python
def upload_stream(
    *,
    object_key: str,
    stream: IO[bytes],
    content_type: str,
    cache_control: str = "private, max-age=0",
) -> str:
    """Faz upload streaming para o bucket. Retorna a URL pública (sem assinatura)."""

def generate_presigned_url(*, object_key: str, expires_in_seconds: int = 300) -> str: ...
def delete_object(*, object_key: str) -> None: ...
def delete_prefix(*, prefix: str) -> int: ...
```

### 7.3 Padrão de `object_key`

- Vídeos: `accidents/{accident_number:04d}/{user_chave}/{idempotency_key}.{ext}`
- XLSX (snapshot): `accidents/{accident_number:04d}/archive/{accident_number:04d}.xlsx`
- ZIP final: `accidents/{accident_number:04d}/archive/{accident_number:04d}.zip`

### 7.4 Limpeza no DELETE de acidente

Quando `delete_accident` é executado:
1. `delete_prefix(prefix=f"accidents/{accident_number:04d}/")` apaga vídeos + archive de uma vez.
2. Linhas em `accident_video_uploads`, `accident_archives` caem por cascade.

### 7.5 Modo de desenvolvimento

Se `do_spaces_bucket is None`, usar storage local em `event_archives_dir + "/accidents"`. O `public_url` aponta para um endpoint estático servido pela própria API:

- Novo router `GET /api/admin/accidents/local-asset/{path:path}` (apenas em dev) lê do disco.

Isto evita que o sistema dependa de credenciais DO em CI/local.

### 7.6 Testes desta fase

`tests/services/test_object_storage.py`:
- `upload_stream` em modo local salva no disco.
- `generate_presigned_url` em modo S3 produz URL com assinatura válida (mock botocore).
- `delete_prefix` apaga várias chaves.

---

## Phase 8 — Frontend admin — botão, tema, wizard, aba, tabelas

Arquivos a editar:
- [sistema/app/static/admin/index.html](../sistema/app/static/admin/index.html)
- [sistema/app/static/admin/styles.css](../sistema/app/static/admin/styles.css)
- [sistema/app/static/admin/app.js](../sistema/app/static/admin/app.js)

### 8.1 Botão 'Reportar Acidente' no header

HTML (no `<header>`, ao lado de `.header-brand`):

```html
<button
  id="accidentToggleButton"
  type="button"
  class="accident-button"
  aria-pressed="false"
  aria-label="Reportar Acidente"
>
  <span class="accident-button-label">Reportar Acidente</span>
</button>
```

CSS (em `styles.css`):
- `.accident-button`: redondo (`border-radius:50%`), diâmetro responsivo (≥72px desktop, ≥56px mobile), fundo vermelho (`#c8222a` ou variável já usada em `--danger`), bordas pretas 3px, texto branco, sombra leve.
- Centralizado horizontalmente: o `<header>` hoje usa flex; criar layout 3-col (`logo | botão | sessionBar`) com `grid-template-columns: 1fr auto 1fr`.
- Estado pressionado (`[aria-pressed="true"]`): label `Acidente Reportado`, bordas vermelhas brilhantes (`box-shadow: 0 0 0 3px #ff4d57, 0 0 18px #ff4d57`), efeito `transform: scale(0.97)` para "pressionado".

JS (em `app.js`):
- `let accidentState = { isActive: false, accident: null, situationRows: [] };`
- `function fetchAccidentState()` → `GET /api/admin/accidents/active`. Atualiza `accidentState`, redesenha botão + aba + tema.
- Listener do botão:
  - Se `isActive=false`: abre o wizard (Phase 8.2).
  - Se `isActive=true`: abre o modal de encerramento (Phase 8.5).
- No `startRealtimeUpdates()` ([sistema/app/static/admin/app.js:5455](../sistema/app/static/admin/app.js#L5455)), no handler `onmessage`, fazer parse do payload e, se `reason` ∈ {`accident_opened`,`accident_closed`,`accident_user_report`,`accident_video_uploaded`} → chamar `fetchAccidentState()` (com debounce ≥250ms).

### 8.2 Wizard "Reportar Acidente" (admin)

Três modais sequenciais, padrão visual igual aos modais já existentes (`modal-backdrop` + `modal-card`). HTML:

```html
<!-- Modal 1: Selecione o Projeto -->
<div id="accidentWizardProjectModal" class="modal-backdrop hidden">
  <div class="modal-card" role="dialog">
    <div class="modal-header"><h2>Selecione o Projeto</h2></div>
    <div id="accidentWizardProjectOptions" class="accident-wizard-options"></div>
    <div class="modal-footer">
      <button id="accidentWizardProjectCancel" class="secondary-button">Cancelar</button>
      <button id="accidentWizardProjectAdvance" disabled>Avançar</button>
    </div>
  </div>
</div>

<!-- Modal 2: Local do Acidente -->
<div id="accidentWizardLocationModal" class="modal-backdrop hidden">
  <div class="modal-card">
    <div class="modal-header"><h2>Local do Acidente</h2></div>
    <div id="accidentWizardLocationOptions" class="accident-wizard-options"></div>
    <div class="accident-wizard-custom-location">
      <label class="accident-wizard-option">
        <input type="radio" name="accidentLocationChoice" value="__custom__" />
        <span>Outro local:</span>
        <input id="accidentWizardCustomLocation" type="text" maxlength="120" placeholder="Descreva o local" disabled />
      </label>
    </div>
    <div class="modal-footer">
      <button id="accidentWizardLocationCancel" class="secondary-button">Cancelar</button>
      <button id="accidentWizardLocationAdvance" disabled>Avançar</button>
    </div>
  </div>
</div>

<!-- Modal 3: Confirmação -->
<div id="accidentWizardConfirmModal" class="modal-backdrop hidden">
  <div class="modal-card">
    <div class="modal-header"><h2>Confirmação de Acidente</h2></div>
    <p id="accidentWizardConfirmText" class="accident-wizard-confirm-text"></p>
    <p>Você confirma esta ação?</p>
    <div class="modal-footer">
      <button id="accidentWizardConfirmCancel" class="secondary-button">Cancelar</button>
      <button id="accidentWizardConfirmSubmit">Confirmar</button>
    </div>
  </div>
</div>
```

Fluxo JS:
1. Ao abrir o wizard, fetch `GET /api/admin/accidents/wizard/projects` → render radios.
2. "Avançar": fetch `GET /api/admin/accidents/wizard/locations?project_id=X` → render radios + opção custom.
3. "Avançar": preencher `accidentWizardConfirmText` com `Você está prestes a reportar um acidente na localização ${locationName} do projeto ${projectName}.`
4. "Confirmar": `POST /api/admin/accidents/open`. Sucesso → fecha modais, dispara `fetchAccidentState()`. Erro 409 → mensagem "Já há um acidente em curso" e fecha.

Cancelamento em qualquer passo: fecha todos os modais e retorna à tela inicial (item 4.1).

### 8.2.1 Wizard reativo a mudanças remotas

Se o admin estiver no wizard e o servidor publicar `accident_opened` por outro caminho (outro admin ou usuário web abriu primeiro):
- Fechar wizard.
- `fetchAccidentState()` aplica tema + abre aba "Acidente".
- Mensagem efêmera "Outro usuário acaba de reportar um acidente."

Se publicar `accident_closed` enquanto o admin estiver no encerramento (improvável mas possível em multi-admin):
- Fechar modal.
- Mensagem "Acidente já foi encerrado por outro administrador."

### 8.2.2 Polling fallback (defensivo)

Mesmo padrão da Checking Web (Phase 9.7.1): `setInterval` de 30s chamando `fetchAccidentState()` para o caso de SSE cair.

### 8.3 Tema 'Modo Acidente'

CSS:
- Definir variáveis no `:root`: já existem cores verdes. Criar `:root.accident-mode { ...; --primary: var(--danger); --primary-hover: #8c1a20; --accent-bg-soft: #fde7e9; --accent-stripe: #b7141c; }`.
- A faixa verde do header (`.header-brand` + background) usa hoje uma cor primária. Garantir que todas as cores derivam de variáveis CSS — fazer pass pelo `styles.css` para parametrizar.
- Sobreposição de regras pontuais: títulos de seção, abas, botões primários, indicadores de status conectado.
- **Não** alterar: bordas dos campos `chave` e `senha` (não se aplica ao admin — esses campos são da Checking Web. No admin não há regra de exceção, então tudo verde vira vermelho).

JS:
- `function applyAccidentTheme(isActive)`: `document.documentElement.classList.toggle('accident-mode', isActive)`.
- Chamada dentro de `fetchAccidentState()`.

### 8.4 Aba 'Acidente' + tabela 'Situação de Pessoal'

HTML (em `<nav class="tabs">` adicionar como **primeira** aba):

```html
<button data-tab="acidente" id="accidentTabButton" class="hidden">Acidente</button>
```

Esta aba aparece **somente** quando `accidentState.isActive=true`. Quando aparecer, é destacada com bordas vermelho-brilhantes (CSS: classe `tab-accident` no botão).

Section `<main>` correspondente:

```html
<section id="tab-acidente" class="tab">
  <div class="section-header">
    <div class="section-title-block">
      <h2 id="accidentSectionTitle">Acidente — Projeto X, Local Y</h2>
      <p id="accidentSectionMeta" class="section-header-copy"></p>
    </div>
  </div>
  <div class="table-wrap">
    <table class="responsive-table situacao-pessoal-table">
      <thead>
        <tr>
          <th>Horário</th>
          <th>Nome</th>
          <th>Chave</th>
          <th>Projetos</th>
          <th>Local</th>
          <th>Zona de</th>
          <th>Situação</th>
          <th>Contato</th>
          <th>Registros</th>
        </tr>
      </thead>
      <tbody id="situacaoPessoalBody"></tbody>
    </table>
  </div>
</section>
```

JS — função `renderSituacaoPessoal(rows)`:
- Limpa `tbody`.
- Para cada `row`, cria `<tr class="situacao-row situacao-row-{rowColor}">`:
  - "Horário": `event_time` formatado **com data e hora** (descritivo item 5.1.1 deixa claro que esta tabela mostra data+hora para todos os perfis, diferente das outras).
  - "Nome": `name`.
  - "Chave": `chave`.
  - "Projetos": `projects.join(', ')`.
  - "Local": `local || '—'`.
  - "Zona de": `zone` (já vem `Aguardando`/`Segurança`/`Acidente`).
  - "Situação": `status`.
  - "Contato": `phone || ''`.
  - "Registros": `<div class="registros-scroll">` com `<a>` para cada vídeo (target=`_blank`). Se >5 vídeos, CSS define `max-height` + `overflow-y:auto`.
- Sort/ordem: já vem do backend, manter ordem.

CSS (linhas):
- `.situacao-row-blinking-red` — `background: rgba(255,80,90,0.18); animation: situacao-blink 1s steps(2, end) infinite;`. Keyframe alterna `background`.
- `.situacao-row-yellow` — `background: rgba(255,234,120,0.45);`.
- `.situacao-row-turquoise` — `background: rgba(120,220,220,0.4);`.
- `.situacao-row-light-green` — `background: rgba(160,230,160,0.4);`.
- `.situacao-row-white` — fundo branco padrão.
- `.situacao-row-light-gray` — para prioridade 5 (check-out durante acidente).

Periodicamente (a cada 30s, defensivo) buscar `/api/admin/accidents/active` mesmo sem evento SSE — fallback para conexão SSE caída.

### 8.5 Modal de encerramento

HTML:

```html
<div id="accidentEndModal" class="modal-backdrop hidden">
  <div class="modal-card">
    <div class="modal-header"><h2>Encerramento do Modo Acidente</h2></div>
    <p>Tem certeza que deseja finalizar o 'Modo Acidente'?</p>
    <div class="modal-footer">
      <button id="accidentEndBack" class="secondary-button">Voltar</button>
      <button id="accidentEndConfirm">Confirmar</button>
    </div>
  </div>
</div>
```

JS:
- "Voltar": fecha modal, mantém modo acidente ativo.
- "Confirmar": `POST /api/admin/accidents/close`. Sucesso → `fetchAccidentState()` (que vai limpar tema, esconder aba, atualizar tabela 'Acidentes' do Cadastro).

### 8.6 Tabela 'Acidentes' no Cadastro

HTML (em `tab-cadastro`, imediatamente após `cadastro-section-panel--pending`):

```html
<article class="cadastro-section-panel cadastro-section-panel--accidents" data-cadastro-section="acidentes">
  <div class="section-header">
    <h2>Acidentes</h2>
    <button id="refreshAccidentsButton" type="button" class="secondary-button">Atualizar</button>
  </div>
  <div class="table-wrap cadastro-grid-wrap">
    <table class="responsive-table cadastro-table cadastro-accidents-table">
      <thead>
        <tr><th>Número</th><th>Projeto</th><th>Autor</th><th>Aberto em</th><th>Encerrado em</th><th>Download</th><th>Ações</th></tr>
      </thead>
      <tbody id="accidentsBody"></tbody>
    </table>
  </div>
</article>
```

JS:
- `fetchAccidentsHistory()` → `GET /api/admin/accidents` → render.
- "Download" → `<a href="/api/admin/accidents/{id}/archive">Baixar</a>` (server faz 307 para presigned URL).
- "Remover" botão visível somente se `row.can_delete === true`. Click → confirm dialog ("Tem certeza que deseja excluir o acidente 0042?") → `DELETE /api/admin/accidents/{id}`.

### 8.7 Acessibilidade

- Todos os modais com `role="dialog"` `aria-modal="true"` `aria-labelledby="..."`.
- Botão do acidente com `aria-live="polite"` para anunciar mudança de label.
- Wizards bloqueiam ESC só após confirmação? **Decisão**: ESC equivale a "Cancelar" no wizard, mas no modal de confirmação final ESC equivale a "Cancelar" também (não envia).

### 8.8 Testes desta fase

`tests/static/admin/test_accident_button.test.js` (smoke):
- Renderiza botão.
- Click sem acidente abre wizard.
- Click com acidente abre modal de encerramento.

E manual no navegador (já existe a infra `tests/transport_page_date.test.js`).

---

## Phase 9 — Frontend Checking Web — botão, tema, wizard, container 'Estou em:', vídeo, ajustes

Arquivos a editar:
- [sistema/app/static/check/index.html](../sistema/app/static/check/index.html)
- [sistema/app/static/check/styles.css](../sistema/app/static/check/styles.css)
- [sistema/app/static/check/app.js](../sistema/app/static/check/app.js)
- Novos: `sistema/app/static/check/accident.js`, `sistema/app/static/check/accident-camera.js`

### 9.1 Botão 'Reportar Acidente' (abaixo do 'Registrar')

HTML (após `<button id="submitButton" ...>Registrar</button>` na linha [229](../sistema/app/static/check/index.html#L229)):

```html
<button
  id="accidentReportButton"
  type="button"
  class="accident-report-button"
  aria-pressed="false"
>
  <span class="accident-report-button-label">Reportar Acidente</span>
</button>
```

CSS:
- Mesmo formato/tamanho do `.submit-button`. Cor vermelha (`background: var(--danger)`), label branco.
- Estado pressionado quando `[aria-pressed="true"]`: bordas vermelho brilhante, label "Acidente Reportado", efeito de pressionado.

JS (`accident.js`):
- `state = { isActive: false, accident: null, currentUserReport: null }`.
- Listener do botão:
  - Se `isActive=false`: abre wizard (Phase 9.2).
  - Se `isActive=true`: abre widget "Audio & Video / Reportar Novo Acidente" (Phase 9.4).

### 9.2 Wizard de abertura (Checking Web)

Quatro modais sequenciais, no estilo `password-dialog` (já existe nesse static). HTML:

1. **Selecione o Projeto** — radios com todos os projetos cadastrados (item 4.2: "para cada projeto cadastrado" — todos os projetos do sistema, incluindo fora dos do usuário).
2. **Local do Acidente** — radios dos locais do projeto + opção `__custom__` com input.
3. **Sua Situação:** — três radios:
   - "Estou em Zona de Segurança"
   - "Estou em Zona de Acidente, mas estou bem"
   - "Estou em Zona de Acidente, e preciso de ajuda"

   Rodapé: "Cancelar" e "Confirmar Acidente".
4. **Confirmação de Acidente** — texto:
   ```
   Você está prestes a reportar um acidente na localização <local> do projeto <projeto>.
   Sua situação: <situação selecionada>
   Você confirma esta ação?
   ```
   Botões "Cancelar" / "Confirmar".

JS:
- "Confirmar" no 4º modal: `POST /api/web/check/accident/open` com `{project_id, location_id|custom_location_name, zone, status, chave}`.
- Sucesso → fechar todos os modais + entrar em modo acidente (Phase 9.3).
- 409 (outro usuário já abriu) → fechar modais; o evento SSE seguinte vai sincronizar o estado em tempo real e mostrar a tela do "modo acidente" automaticamente.

### 9.3 Modo Acidente — alterações na tela principal

**Tema**: classe `accident-mode` na raiz do `<main>` ou `<body>`. CSS: trocar todas as variáveis derivadas de verde → vermelho, **exceto** as bordas de `#chaveInput` e `#passwordInput` que possuem regras de cor próprias por estado de autenticação (item 5.1.2 do descritivo) — usar seletores específicos para preservar.

**Barra de notificações** (já existe `#notificationLinePrimary`): definir texto vermelho/negrito com `Acidente Reportado no projeto <nome>!` enquanto o modo estiver ativo. Implementar como propriedade exclusiva — não conflitar com mensagens transitórias normais (priorizar a mensagem de acidente; mensagens normais ficam fila/atrasadas? **Decisão**: enquanto o modo acidente está ativo, o `lineSecondary` herda o uso normal e o `linePrimary` fica reservado ao banner do acidente).

**Container 'Estou em:'**: substituir visualmente os containers `Último Check-In` e `Último Check-Out` (linhas 60-67 do HTML).

```html
<section id="accidentInquiryCard" class="history-card accident-inquiry-card is-hidden">
  <p id="accidentInquiryTitle" class="history-label">Estou em:</p>
  <div class="accident-inquiry-grid">
    <button id="accidentZoneSafetyButton" type="button" class="accident-inquiry-button">Zona de Segurança</button>
    <button id="accidentZoneAccidentButton" type="button" class="accident-inquiry-button">Zona de Acidente</button>
  </div>
</section>
```

JS:
- Quando `state.isActive=true`, esconder `.history-card` original e mostrar `#accidentInquiryCard`.
- Click em "Zona de Segurança" → abre modal de confirmação (Situação 1).
- Click em "Zona de Acidente" → muda título para "Sua Situação" e botões para "Estou bem." / "Preciso de Ajuda!".
- Click em "Estou bem." → modal de confirmação (Situação 2).
- Click em "Preciso de Ajuda!" → modal de confirmação (Situação 3).

Cada modal de confirmação:

```html
<section id="accidentReportConfirmDialog" class="password-dialog is-hidden" role="dialog">
  <div class="password-dialog-card">
    <h2>Confirmação</h2>
    <p id="accidentReportConfirmText"></p>
    <div class="password-dialog-actions">
      <button id="accidentReportConfirmCancel" class="secondary-button">Cancelar</button>
      <button id="accidentReportConfirmSubmit" class="submit-button">Confirmar</button>
    </div>
  </div>
</section>
```

Textos:
- Situação 1 (safety/ok): "Você confirma que está fora de perigo?"
- Situação 2 (accident/ok): "Você confirma que está na zona do acidente e que está fora de perigo?"
- Situação 3 (accident/help): "Você confirma que está na zona do acidente e que precisa de ajuda?"

"Confirmar" → `POST /api/web/check/accident/report` com `{chave, zone, status}`. "Cancelar" → fecha modal, mantém estado "Estou em" para nova tentativa.

Após confirmação bem-sucedida:
- Atualizar `state.currentUserReport`.
- A tela volta ao estado "normal" com tema vermelho mantido (item 5.1.2: "A aplicação web 'Checking Web' retorna ao estado normal, porém, com o tema vermelho").
- O container 'Último Check-In/Out' volta a aparecer (já que o usuário cumpriu seu reporte). **Decisão**: ainda assim manter o `accidentInquiryCard` visível para permitir mudar o status caso o usuário queira (ex.: passou de "Zona de Segurança" para "Preciso de Ajuda"). O título então fica "Estou em (atual: Segurança)".

### 9.4 Widget "Audio & Video / Reportar Novo Acidente"

Quando `state.isActive=true` E o usuário clica no botão "Reportar Acidente" (que agora exibe "Acidente Reportado"), abrir:

```html
<section id="accidentActionsDialog" class="password-dialog is-hidden" role="dialog">
  <div class="password-dialog-card">
    <h2>Ações de Emergência</h2>
    <div class="accident-actions-grid">
      <button id="accidentActionAudioVideoButton" class="submit-button">Audio &amp; Video</button>
      <button id="accidentActionReportNewButton" class="secondary-button" disabled>Reportar Novo Acidente</button>
    </div>
    <div class="password-dialog-actions">
      <button id="accidentActionDialogBackButton" class="secondary-button">Voltar</button>
    </div>
  </div>
</section>
```

"Reportar Novo Acidente" fica `disabled` por enquanto (item 5.2 Ação 4 do descritivo).

"Audio & Video" → fluxo de captura de vídeo (`accident-camera.js`):

1. `navigator.mediaDevices.getUserMedia({video: {facingMode: {ideal: 'environment'}}, audio: true})` — câmera traseira preferencial.
2. Mostrar `<video autoplay muted>` em fullscreen no modal de gravação.
3. `MediaRecorder` com mimeType priorizando `video/webm;codecs=vp9,opus` → fallback `video/webm` → fallback `video/mp4`.
4. Botão "Encerrar" para parar `MediaRecorder.stop()`.
5. No `ondataavailable`, montar Blob → `FormData` → `POST /api/web/check/accident/video` com `idempotency_key=crypto.randomUUID()`.
6. Liberar o stream (`track.stop()` em cada track).
7. Mostrar status "Vídeo enviado" → fechar modal de captura.

Erros tratados:
- Permissão negada → mensagem "Sem permissão de câmera/microfone. Habilite em Ajustes → Permitir Audio & Video".
- Sem `MediaRecorder` (browsers muito antigos) → mensagem "Seu dispositivo não suporta gravação de vídeo".

### 9.5 Botão "Permitir Audio & Video" em Ajustes

Em [sistema/app/static/check/index.html:428-434](../sistema/app/static/check/index.html#L428-L434), adicionar uma nova `settings-option-row` logo após o "Permitir localização":

```html
<div class="settings-option-row settings-option-row-action">
  <button id="settingsAudioVideoPermissionButton" type="button" class="secondary-button settings-option-action">Permitir Audio &amp; Video</button>
</div>
```

JS:
- Click → `navigator.mediaDevices.getUserMedia({video: true, audio: true})` → para o stream imediatamente após autorização (`track.stop()`) para que a permissão fique "concedida" sem manter câmera ligada.
- Feedback: alterar label do botão para "Audio & Video permitido" e desabilitar.

### 9.6 SSE — atualização em tempo real

Em `app.js` (Checking Web):

```js
let accidentEventSource = null;
function startAccidentRealtime(chave) {
  stopAccidentRealtime();
  accidentEventSource = new EventSource(`/api/web/check/stream?chave=${encodeURIComponent(chave)}`);
  accidentEventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.reason && data.reason.startsWith('accident_')) {
      refreshAccidentState();
    }
  };
}
```

`refreshAccidentState()` → `GET /api/web/check/accident/state` → reaplica tema + UI conforme estado retornado.

### 9.7 Detecção inicial ao carregar a página

Após login bem-sucedido (handler atual já carrega `/state`), invocar `refreshAccidentState()`. Se `isActive=true`, aplicar tema + abrir container "Estou em:" automaticamente — usuário entrou num momento em que o acidente já estava em curso.

### 9.7.1 Polling fallback (defensivo)

Em caso de falha na conexão SSE (proxy, browser inactivo, mobile background), manter um `setInterval` de 30s chamando `refreshAccidentState()`. O custo é desprezível (1 GET com payload pequeno) e elimina qualquer cenário de UI ficar dessincronizada do servidor.

### 9.7.2 Comportamento do wizard durante mudanças remotas de estado

Se o usuário estiver no wizard de abertura (`Selecione o Projeto` / `Local` / `Sua Situação` / `Confirmação`) e o servidor publicar `accident_opened` (outro admin/usuário abriu primeiro):
- Fechar todos os modais do wizard.
- Aplicar tema vermelho.
- Mostrar mensagem efêmera "Outro usuário acaba de reportar um acidente. Por favor, confirme sua situação." e abrir o container "Estou em:".

Se o usuário estiver respondendo "Sua Situação" e o servidor publicar `accident_closed` (outro admin encerrou):
- Fechar modal de confirmação.
- Reverter tema verde.
- Mostrar mensagem "O Modo Acidente foi encerrado".

O mesmo princípio vale para o wizard do admin (Phase 8.2.1 a seguir).

### 9.8 Internacionalização

Existe `i18n-dictionaries.js` no [check static/](../sistema/app/static/check/i18n-dictionaries.js). Adicionar **somente** chaves novas em pt-BR nesta entrega (idiomas adicionais ficam vazios → fallback pt-BR no `i18n.js`). Chaves:
- `accident.button.report`, `accident.button.reported`
- `accident.wizard.selectProject`, `.selectLocation`, `.yourSituation`, `.confirmTitle`, `.confirmText`
- `accident.notification.bannerTemplate`
- `accident.inquiry.title`, `.titleAfterAccident`, `.safetyZone`, `.accidentZone`, `.imOk`, `.needHelp`
- `accident.confirm.safety`, `.accidentOk`, `.help`
- `accident.actions.title`, `.audioVideo`, `.reportNew`, `.back`
- `accident.settings.permitAudioVideo`, `.permitted`

### 9.9 Testes desta fase

`tests/static/check/test_accident_button.test.js`:
- Botão renderiza.
- Click abre wizard.
- Recebe SSE `accident_opened` e ativa tema.
- Confirma Situação 1 e mostra container.

E teste de browser manual (com câmera) para Phase 9.4.

---

## Phase 10 — Geração do arquivo ZIP de encerramento

Arquivos novos:
- `sistema/app/services/accident_archive_builder.py`

### 10.1 Estrutura do ZIP

```
0042.zip
├─ 0042.xlsx
└─ Registros/
   ├─ HR70-uuid1.webm
   ├─ HR70-uuid2.webm
   └─ XY13-uuid1.mp4
```

### 10.2 XLSX

Usar `openpyxl` (já comum em projetos FastAPI; conferir/instalar).

Conteúdo: tabela `Situação de Pessoal` congelada no momento do encerramento, mesmas colunas que a aba 'Acidente' do admin (Phase 8.4).

Coluna "Registros": para cada vídeo, criar **um hyperlink** apontando para `Registros/<filename>` (path relativo dentro do ZIP). O Excel resolve esses links como arquivos relativos ao arquivo XLSX, então abrir o ZIP num explorador (descompactado) ou via o Excel mais novo (que entende paths relativos dentro de ZIPs) preserva a funcionalidade (item 6 do descritivo: "links … de forma que a funcionalidade dos links dos registros esteja preservada").

Se houver múltiplos vídeos por usuário, a célula contém múltiplas linhas separadas por `\n` (alinhamento "wrap text"), com hyperlinks individuais quando o cliente Excel suportar — fallback: lista textual com paths.

### 10.3 Algoritmo de construção

```python
def build_archive_zip(
    db: Session,
    *,
    accident: Accident,
    snapshot_rows: list[SituacaoPessoalRow],
    video_uploads: list[AccidentVideoUpload],
) -> tuple[BytesIO, dict]:
    # 1. monta xlsx em BytesIO
    # 2. baixa cada vídeo do Spaces (boto3 get_object → bytes) para BytesIO interno
    # 3. monta ZIP em BytesIO com xlsx + Registros/<filename>
    # 4. retorna (zip_buffer, metadata)
```

`metadata` inclui `size_bytes` e mapping `{video_id: filename_in_zip}` (filename = `{user_chave}-{idempotency_key_short}.{ext}`).

### 10.4 Onde rodar

Chamada de `accident_lifecycle.close_accident`. O ZIP é grande (potencialmente centenas de MB se houver muitos vídeos) — fazer upload diretamente em DO Spaces como `multipart_upload` ou simples `put_object` em streaming.

Para evitar travar o request HTTP, o `close_accident` pode:
1. Marcar `closed_at=NOW()` imediatamente (libera UI).
2. Enfileirar o build do archive via `BackgroundTasks`.
3. Quando pronto, atualizar `accident.archive_object_key` e publicar `accident_closed` (segundo evento) — admin atualiza linha da tabela 'Acidentes' com o botão "Baixar" agora habilitado.

A linha aparece imediatamente sem download enquanto o archive é construído (campo "Download" mostra "Preparando..."). Quando o link fica pronto, o stream notifica e o botão troca para "Baixar".

### 10.5 Testes

`tests/services/test_accident_archive_builder.py`:
- ZIP contém arquivo XLSX no nome `0000.xlsx`.
- ZIP contém pasta `Registros/` com todos os vídeos.
- XLSX abre via `openpyxl.load_workbook` e tem as colunas exatas.
- Hyperlinks na coluna "Registros" estão presentes.
- Geração de archive a partir de acidente sem vídeos cria ZIP só com XLSX e pasta `Registros/` vazia (ou sem ela).

---

## Phase 11 — Hook de check-in/check-out durante acidente

Já descrito em Phase 3.4. Resumindo o ponto de toque concreto:

Arquivo a editar: [sistema/app/services/forms_submit.py](../sistema/app/services/forms_submit.py).

Hoje a função que processa um `Web check event` grava em `CheckingHistory`. Identificar essa função (`submit_forms_event` ou função análoga), e logo após o commit chamar:

```python
active_accident = accident_lifecycle.list_active_accident(db)
if active_accident is not None:
    accident_lifecycle.handle_check_event_during_accident(
        db,
        accident=active_accident,
        user=user,
        action=action,  # 'check-in' ou 'check-out'
        event_time=event_time,
    )
```

`handle_check_event_during_accident`:
- Upsert em `accident_user_reports` mantendo `zone='waiting'` se for novo `check-in` (priority 3 inicial).
- Atualiza `last_checkin_action` e `last_action_at` para refletir.
- Publica `accident_user_report` em ambos os brokers.

Igual hook em [sistema/app/routers/device.py](../sistema/app/routers/device.py) (catraca/RFID) e [sistema/app/routers/mobile.py](../sistema/app/routers/mobile.py) (app mobile) para que entradas via outros canais também sejam refletidas.

### 11.1 Testes

`tests/services/test_accident_check_event_hook.py`:
- Usuário não-presente no acidente, faz check-in → vira `waiting`.
- Usuário já reportado `safety/ok`, faz check-out → permanece `safety/ok`, atualiza `last_action_at`.
- Usuário se reportou `accident/help`, faz check-out durante acidente → fica visível como prioridade 5 (regra: `last_checkin_action='check-out' AND last_action_at >= opened_at`).

---

## Phase 12 — Telemetria / observabilidade

Arquivos a editar:
- [sistema/app/services/event_logger.py](../sistema/app/services/event_logger.py) — caso suporte tipos de evento extras, adicionar.

### 12.1 Eventos a logar

Cada operação grava em `check_events` (via `log_event`):
- `action="accident_open"` — campo `details={accident_id, accident_number, project, local, origin}`.
- `action="accident_close"` — `details={accident_id, accident_number, archive_size_bytes}`.
- `action="accident_user_report"` — `details={accident_id, user_id, zone, status}`.
- `action="accident_video_upload"` — `details={accident_id, user_id, video_id, size_bytes, duration_seconds}`.
- `action="accident_email_help"` — `details={recipient_count, sent_count, failed_count}`.
- `action="accident_delete"` — `details={accident_id, by_admin}`.

### 12.2 Métricas no log estruturado

Os endpoints já passam pelo `RequestLoggingMiddleware` e ganham `path`, `latency_ms`, `client_surface`. Não há mudança de infra de logs necessária.

### 12.3 Testes

Não há teste dedicado — vai junto com os testes funcionais dos endpoints (assertir que `log_event` foi chamado).

---

## Phase 13 — Documentação

Arquivos a editar:
- [docs/estrutura_banco_dados.md](estrutura_banco_dados.md) (ressuscitar do `git show HEAD --` se já foi deletado e re-adicioná-lo com as novas tabelas)
- [docs/endpoints/](endpoints/) — adicionar `post_accidents_open.md`, `post_accidents_close.md`, `get_accidents_active.md`, `post_accident_report.md`, `post_accident_video.md`, etc.
- [CLAUDE.md](../CLAUDE.md) — adicionar seção "Modo Acidente" com visão geral do funcionamento, modelos, endpoints, real-time brokers e fluxos de UI.
- README/operação: explicar variáveis SMTP e DO Spaces necessárias no `.env` produção.

### 13.1 Conteúdo mínimo de cada doc

Cada doc de endpoint segue o padrão dos existentes:
- Cabeçalho (método + path + autenticação).
- Request body schema.
- Response body schema.
- Códigos de erro.
- Exemplos cURL.
- Side effects (eventos publicados em brokers, e-mails disparados, etc.).

### 13.2 Diagrama de fluxo

Adicionar um diagrama ASCII em `docs/descritivos/funcionamento_botao_acidente_reportado.txt` (ao fim do arquivo) ou em um novo doc `docs/descritivos/modo_acidente_arquitetura.md`. Conteúdo: sequência

```
admin/check → POST open → service → DB → broker.publish(accident_opened)
                                       ↓
                  ┌────────────────────┴──────────────────┐
                  ↓                                       ↓
            admin SSE clients                  web check SSE clients
                  ↓                                       ↓
            fetchAccidentState                     refreshAccidentState
                  ↓                                       ↓
              UI atualiza                           UI atualiza
```

---

## Phase 14 — Roteiro de testes E2E manuais (com 2 navegadores)

Validar em ambiente local com dois navegadores abertos (admin e Checking Web logados como usuários distintos):

1. **Abertura via admin**:
   - Admin clica "Reportar Acidente" → escolhe projeto P84 → escolhe local Lobby → confirma.
   - Em <2s a Checking Web do usuário (outro browser) recebe banner vermelho, tema vermelho, container "Estou em:".
2. **Reporte do usuário**:
   - Usuário clica "Zona de Segurança" → confirma. Admin vê linha verde-clara aparecer na tabela 'Situação de Pessoal' em <2s.
3. **Pedido de ajuda**:
   - Outro usuário clica "Zona de Acidente" → "Preciso de Ajuda" → confirma. Admin vê linha vermelha piscante em <2s. Caixa SMTP do destinatário recebe e-mail "(CHECKING) PEDIDO DE SOCORRO".
4. **Vídeo**:
   - Usuário clica botão "Acidente Reportado" → "Audio & Video" → permite câmera → grava 5s → "Encerrar". Admin vê link em "Registros" em <5s, conseguiu reproduzir.
5. **Check-in durante acidente**:
   - Terceiro usuário faz check-in pela mobile/catraca. Admin vê nova linha turquesa na tabela.
6. **Encerramento**:
   - Admin clica "Acidente Reportado" → "Confirmar". Tema verde retorna em ambos os clientes. Aba 'Acidente' desaparece. Linha aparece em Cadastro → Acidentes com botão "Baixar".
7. **Download**:
   - Admin clica "Baixar" → recebe ZIP 0000.zip contendo 0000.xlsx + Registros/. Abrir XLSX: tabela completa, hyperlinks navegáveis.
8. **Exclusão**:
   - Admin perfil 1 vê tabela mas botão "Remover" oculto.
   - Admin perfil 9 vê botão, clica, confirma. Linha some. ZIP/vídeos no DO Spaces apagados.
9. **Abertura via Checking Web**:
   - Modo normal, usuário clica "Reportar Acidente" → wizard completo → confirma.
   - Admin recebe notificação em <2s; tema vermelho; aba "Acidente"; primeiro registro é o autor (Ação 2).
10. **Persistência via reload**:
    - Recarregar admin no meio do acidente — tema, aba e tabela são restaurados a partir do `/state` (não dependem de estado em memória).

Cada cenário tem checklist no roteiro com pass/fail e screenshot.

---

## Phase 15 — Critérios de aceitação finais

Esta lista é o "Definition of Done" da feature. Cada item refere-se a um requisito explícito do descritivo corrigido.

- [ ] Botão redondo, grande, vermelho, bordas pretas, centralizado horizontalmente no header do admin, label "Reportar Acidente" branco.
- [ ] Botão on/off no admin alterna label para "Acidente Reportado", bordas ficam vermelhas e brilhantes, efeito pressionado.
- [ ] Tabela "Acidentes" criada na aba "Cadastro" imediatamente abaixo de "Pendências".
- [ ] Botão "Reportar Acidente" abaixo do "Registrar" na Checking Web com mesmo formato e tamanho.
- [ ] Botão on/off na Checking Web altera label para "Acidente Reportado", bordas brilhantes, pressionado.
- [ ] Botão "Permitir Audio & Video" no widget Ajustes da Checking Web.
- [ ] Wizard admin: "Selecione o Projeto" → "Local do Acidente" (com opção custom) → "Confirmação de Acidente" → "Cancelar" / "Confirmar".
- [ ] Wizard Checking Web: "Selecione o Projeto" → "Local do Acidente" (com opção custom) → "Sua Situação" → "Confirmação de Acidente".
- [ ] Tema vermelho aplicado em todo o admin durante modo acidente.
- [ ] Aba "Acidente" antes da aba "Check-in", cor vermelha com bordas brilhantes.
- [ ] Tabela "Situação de Pessoal" com colunas: Horário (data+hora), Nome, Chave, Projetos, Local, Zona de, Situação, Contato, Registros.
- [ ] Coluna "Zona de" mostra "Aguardando" / "Segurança" / "Acidente" com cores de linha correspondentes.
- [ ] Coluna "Registros" tem links de vídeo, scrolla se >5.
- [ ] Tabela ordenada por prioridade: AJUDA (vermelho piscante) → Acidente OK (amarelo) → Aguardando (turquesa) → Segurança (verde claro) → Check-out durante acidente.
- [ ] Linhas "Aguardando" iniciam com fundo branco.
- [ ] Usuários que fizeram check-out **antes** do modo acidente não aparecem.
- [ ] Usuários que fazem check-in durante o modo acidente são incluídos.
- [ ] Usuários que fazem check-out durante o modo acidente permanecem na tabela.
- [ ] Nenhum usuário é removido até o encerramento do modo acidente.
- [ ] Tema vermelho aplicado em toda a Checking Web durante modo acidente, **exceto** bordas dos campos `chave` e `senha`.
- [ ] Banner: `Acidente Reportado no projeto <nome>!` em vermelho/negrito.
- [ ] Container "Estou em:" com botões "Zona de Segurança" e "Zona de Acidente" no lugar dos containers "Último Check-In/Out".
- [ ] Clicar "Zona de Acidente" troca título para "Sua Situação" e botões para "Estou bem." / "Preciso de Ajuda!".
- [ ] Cada situação (1, 2, 3) tem widget de Confirmação com "Cancelar" / "Confirmar". Em todas, "Cancelar" não envia nada.
- [ ] Situação 3 (Preciso de Ajuda): confirmação obrigatória; e-mail SMTP só dispara após "Confirmar".
- [ ] E-mail "(CHECKING) PEDIDO DE SOCORRO" enviado para todos os usuários cadastrados no projeto do acidente (com e-mail).
- [ ] Ação 4: botão "Reportar Acidente" durante modo acidente abre widget "Audio & Video" / "Reportar Novo Acidente" (segundo desabilitado).
- [ ] "Audio & Video": pede permissão se necessário; grava com câmera traseira; envia para API; aparece na tabela "Situação de Pessoal".
- [ ] Vídeos armazenados em pasta específica do Digital Ocean Spaces.
- [ ] Encerramento via admin: widget "Encerramento do Modo Acidente" com botões "Voltar" / "Confirmar".
- [ ] "Confirmar" no encerramento: tema verde retorna em ambos; aba "Acidente" desaparece.
- [ ] Tabela "Acidentes" recebe nova linha após encerramento.
- [ ] Número do Acidente em 4 dígitos zero-padded, primeiro = 0000.
- [ ] Download produz ZIP com `<num>.xlsx` na raiz + subpasta `Registros/`.
- [ ] XLSX é cópia da tabela "Situação de Pessoal" congelada no momento do encerramento, com hyperlinks funcionais na coluna Registros.
- [ ] Botão "Remover" só aparece para admin perfil 9.
- [ ] Atualizações em tempo real (<2s) entre admin e Checking Web nos eventos: abertura, encerramento, reporte de usuário, upload de vídeo, check-in/check-out durante acidente.

---

## Sequenciamento sugerido

| Sprint | Fases |
|---|---|
| 1 | Phase 0 (planejamento), Phase 1 (migrações/modelos), Phase 2 (broker SSE) |
| 2 | Phase 3 (lifecycle service), Phase 4 (endpoints admin), Phase 5 (endpoints web) |
| 3 | Phase 6 (SMTP), Phase 7 (DO Spaces), Phase 11 (hook check-in) |
| 4 | Phase 8 (frontend admin) |
| 5 | Phase 9 (frontend Checking Web) |
| 6 | Phase 10 (archive ZIP), Phase 12 (telemetria), Phase 13 (docs), Phase 14 (E2E manual) |

Cada fase deve ser implementada em PR independente, com testes próprios, sem quebrar o sistema existente.

---

## Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Postgres `LISTEN/NOTIFY` cai em produção (psycopg desconectado) | Já existe reconexão exponencial em `admin_updates.py`; cliente já tem polling fallback (30s) — manter ambos. |
| Upload de vídeo grande trava o worker | Streaming direto para DO Spaces; limite de 50MB; tempo limite de gravação no cliente (ex.: 90s). |
| Excel não resolver hyperlinks relativos no ZIP | Texto cell mostra path + filename; admin pode descompactar e abrir manualmente. |
| SMTP indisponível no momento de "Preciso de Ajuda" | E-mail fica `queued`; retry exponencial (max 3) via BackgroundTasks; admin tem visibilidade no `EmailDeliveryLog`. |
| Dois admins tentam abrir simultaneamente | Índice parcial `ix_accidents_single_active` + `SELECT FOR UPDATE` no service; segunda chamada falha com 409. |
| Usuário sem e-mail cadastrado | Pular (gravar `EmailDeliveryLog` com nota), não bloquear o disparo dos demais. |
| Modo acidente abre/fecha enquanto cliente está offline (Checking Web fechada) | Quando reabrir, primeiro fetch `/state` traz `is_active=true/false` real — UI sincroniza imediatamente sem depender de evento perdido. |
| Câmera não disponível (desktop sem webcam) | Mostrar mensagem clara; permitir prosseguir sem vídeo (vídeo é opcional, não bloqueia status). |
| Permissão de câmera negada permanentemente | Botão "Permitir Audio & Video" em Ajustes; instruir usuário a habilitar nas configurações do browser. |

---

## Apêndice A — Mapa de arquivos novos/editados

### Novos arquivos

```
sistema/app/services/accident_lifecycle.py
sistema/app/services/accident_situation_table.py
sistema/app/services/accident_numbering.py
sistema/app/services/accident_archive_builder.py
sistema/app/services/email_settings.py
sistema/app/services/email_smtp_client.py
sistema/app/services/email_sender.py
sistema/app/services/email_templates.py
sistema/app/services/object_storage.py
sistema/scripts/migrate_accidents_v1.sql
sistema/app/static/check/accident.js
sistema/app/static/check/accident-camera.js
tests/models/test_accident_models.py
tests/services/test_accident_lifecycle.py
tests/services/test_accident_archive_builder.py
tests/services/test_accident_check_event_hook.py
tests/services/test_admin_updates_brokers.py
tests/services/test_email_help_request.py
tests/services/test_object_storage.py
tests/routers/test_admin_accidents.py
tests/routers/test_web_accidents.py
tests/static/admin/test_accident_button.test.js
tests/static/check/test_accident_button.test.js
docs/endpoints/post_accidents_open.md
docs/endpoints/post_accidents_close.md
docs/endpoints/get_accidents_active.md
docs/endpoints/get_accidents_list.md
docs/endpoints/delete_accident.md
docs/endpoints/get_accident_archive.md
docs/endpoints/post_web_accident_open.md
docs/endpoints/post_web_accident_report.md
docs/endpoints/post_web_accident_video.md
docs/descritivos/modo_acidente_arquitetura.md
```

### Arquivos a editar

```
sistema/app/models.py                                # +5 modelos
sistema/app/schemas.py                               # +~12 schemas
sistema/app/core/config.py                          # +SMTP +DO Spaces
sistema/app/services/admin_updates.py               # +web_check broker
sistema/app/services/forms_submit.py                # +hook check-in/out
sistema/app/routers/__init__.py                      # (sem alteração)
sistema/app/routers/admin.py                         # +6 endpoints
sistema/app/routers/web_check.py                     # +5 endpoints + SSE
sistema/app/routers/device.py                        # +hook accident
sistema/app/routers/mobile.py                        # +hook accident
sistema/app/main.py                                  # start_brokers já cobre
sistema/app/static/admin/index.html                  # +botão, +wizard, +aba, +tabela
sistema/app/static/admin/styles.css                  # +tema, +tabela
sistema/app/static/admin/app.js                      # +lógica acidente
sistema/app/static/check/index.html                  # +botão, +wizard, +settings option, +containers
sistema/app/static/check/styles.css                  # +tema, +cards
sistema/app/static/check/app.js                      # +wiring acidente + SSE
sistema/app/static/check/i18n-dictionaries.js        # +chaves
CLAUDE.md                                            # +seção Modo Acidente
docs/estrutura_banco_dados.md                        # +tabelas
```

---

## Apêndice B — Variáveis de ambiente novas

```
# SMTP
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=...
SMTP_USE_TLS=true
SMTP_USE_SSL=false
SMTP_SENDER_EMAIL=noreply@checking.app
SMTP_SENDER_NAME=Checking App
SMTP_CONNECT_TIMEOUT_SECONDS=15
SMTP_SEND_TIMEOUT_SECONDS=30
SMTP_MAX_RETRIES=3

# Digital Ocean Spaces
DO_SPACES_ENDPOINT_URL=https://sgp1.digitaloceanspaces.com
DO_SPACES_REGION=sgp1
DO_SPACES_BUCKET=checking-accidents
DO_SPACES_ACCESS_KEY=...
DO_SPACES_SECRET_KEY=...
DO_SPACES_PUBLIC_BASE_URL=https://checking-accidents.sgp1.cdn.digitaloceanspaces.com
```

---

## Apêndice C — Glossário de estados

| Termo | Definição |
|---|---|
| Modo Acidente | Estado global do sistema enquanto existe um `Accident` com `closed_at IS NULL`. |
| Aguardando | Usuário visto no acidente mas que ainda não respondeu (zone=`waiting`). |
| Segurança | Usuário reportou estar fora da zona de risco (zone=`safety`, status=`ok`). |
| Acidente / OK | Usuário está na zona, mas bem (zone=`accident`, status=`ok`). |
| Acidente / Ajuda | Usuário está na zona e pede socorro (zone=`accident`, status=`help`). Dispara e-mail. |
| Prioridade 5 | Usuário fez check-out durante o modo acidente (permanece na tabela com destaque distinto). |
| Acidente Reportado | Label do botão quando o modo acidente está ATIVO. |
| Reportar Acidente | Label do botão quando o modo acidente está INATIVO. |
