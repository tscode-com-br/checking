# To-Do List — Implementação do Modo Acidente (prompts para agentes de IA)

Documento companheiro do plano: [docs/temp000.md](temp000.md). Cada item abaixo é um **prompt autossuficiente** projetado para ser entregue a um agente de IA. Cada prompt inclui:

- **Contexto** — o que já foi feito, o que ainda precisa, e por quê.
- **Arquivos** — paths absolutos a criar/editar.
- **Especificação** — comportamento exato, schemas, assinaturas, snippets.
- **Critérios de aceitação** — como saber que a tarefa terminou.
- **Testes** — testes obrigatórios para considerar a tarefa concluída.

**Convenções globais para todos os prompts:**
- O projeto está em [c:/dev/projetos/checkcheck/](../). Toda referência relativa parte daí.
- O descritivo canônico é [docs/descritivos/funcionamento_botao_acidente_reportado.txt](descritivos/funcionamento_botao_acidente_reportado.txt). Em caso de dúvida funcional, **ele é a fonte da verdade**.
- O plano de arquitetura é [docs/temp000.md](temp000.md). Sempre que um prompt mencionar "Phase X.Y", a referência é nesse plano.
- O banco em desenvolvimento é SQLite ([sistema/app/database.py](../sistema/app/database.py)); em produção é Postgres. Toda DDL deve funcionar em ambos.
- Brokers de tempo real estão em [sistema/app/services/admin_updates.py](../sistema/app/services/admin_updates.py).
- Testes seguem o padrão `tests/<area>/test_<modulo>.py` (pytest).
- **Nunca quebre features existentes.** Antes de submeter cada tarefa, rodar `pytest -q` e checar que tudo ainda passa.
- **Nunca crie comentários redundantes** (vide regra do CLAUDE.md / instruções globais).
- Após cada tarefa, atualizar este `temp000A.md` marcando o item como `[x]`.

---

## Bloco A — Fundação do backend (modelos, schemas, migração)

### [ ] Task A1 — Adicionar modelos SQLAlchemy do Modo Acidente

**Contexto.** O sistema ainda não tem nenhum modelo para acidentes. Precisamos das 5 tabelas descritas na Phase 1 do plano. As tabelas precisam funcionar tanto em SQLite (dev) quanto em Postgres (produção). A criação automática é feita em [sistema/app/main.py:228-240](../sistema/app/main.py#L228-L240) via `Base.metadata.create_all` (`app_env == "development"`), então basta declarar os modelos.

**Arquivos.**
- Editar: [sistema/app/models.py](../sistema/app/models.py)

**Especificação.**
1. Importar `JSON` se ainda não estiver importado (para colunas JSON em vez de Text, se aplicável — manter `Text` para compatibilidade ampla; usar JSON apenas se houver helper compatível).
2. Adicionar ao **final** do arquivo (após a classe `EndpointApiKey`) os modelos:
   - `Accident` — sequência única `accident_number` (int ≥ 0), `project_id` (FK), `project_name_snapshot`, `location_name_snapshot`, `location_is_registered` (bool), `origin` (`'admin'`/`'web'`), `opened_by_admin_id` / `opened_by_user_id` (um deles preenchido), `opened_at`, `closed_by_admin_id`, `closed_at` (nullable), `archive_object_key` (nullable), timestamps.
   - `AccidentUserReport` — `(accident_id, user_id)` único, `user_chave_snapshot`, `user_name_snapshot`, `user_phone_snapshot` (nullable), `user_projects_snapshot` (Text JSON), `user_local_snapshot`, `zone` (`'waiting'|'safety'|'accident'`), `status` (`'waiting'|'ok'|'help'`), `reported_at` (nullable), `last_checkin_action` (`'check-in'|'check-out'` nullable), `last_action_at` (nullable), timestamps.
   - `AccidentVideoUpload` — `idempotency_key` único, `accident_id` FK CASCADE, `user_id` FK, `object_key`, `public_url`, `content_type`, `size_bytes`, `duration_seconds` (nullable), `captured_at`, `created_at`.
   - `AccidentArchive` — `accident_id` único FK CASCADE, `snapshot_json` (Text), `xlsx_object_key`, `zip_object_key`, `size_bytes`, `generated_at`.
   - `EmailDeliveryLog` — `accident_id` FK SET NULL nullable, `triggered_by_user_id` FK nullable, `recipient_email`, `recipient_chave` nullable, `subject`, `body_snapshot`, `delivery_status` (`'queued'|'sent'|'failed'`), `error_message` nullable, `queued_at`, `sent_at` nullable, `retry_count` default 0.
3. Constraints obrigatórias (replicar exatamente como na Phase 1 do plano):
   - `ck_accidents_origin_allowed` IN ('admin','web')
   - `ck_accidents_number_non_negative`
   - `ck_accident_user_reports_zone_allowed`
   - `ck_accident_user_reports_status_allowed`
   - `ck_email_delivery_logs_status_allowed`
4. Índice parcial **único** `ix_accidents_single_active`:
   ```python
   Index(
       "ix_accidents_single_active",
       "closed_at",
       unique=True,
       postgresql_where=text("closed_at IS NULL"),
       sqlite_where=text("closed_at IS NULL"),
   )
   ```
   Confirmar que `text` está importado de `sqlalchemy` (já está na linha 4 atual).
5. Adicionar `Index("ix_accident_video_uploads_accident_user", "accident_id", "user_id")`.
6. Adicionar `Index("ix_email_delivery_logs_accident", "accident_id")`.
7. **Não** adicionar `JSON` se não houver suporte — usar `Text` para JSON serializado (consistente com o restante do arquivo, vide `admin_monitored_projects_json` em [sistema/app/models.py:69](../sistema/app/models.py#L69)).

**Critérios de aceitação.**
- `python -c "from sistema.app.models import Accident, AccidentUserReport, AccidentVideoUpload, AccidentArchive, EmailDeliveryLog"` retorna sem erro.
- `Base.metadata.create_all(engine)` em SQLite cria as 5 tabelas + índice parcial sem warning.
- `pytest -q` continua passando (não quebrou nada).

**Testes obrigatórios** (criar `tests/models/test_accident_models.py`):
- `test_accident_columns_match_spec` — instanciar `Accident` com todos os campos e fazer flush.
- `test_accident_origin_constraint` — inserir `origin='invalid'` → `IntegrityError`.
- `test_accident_number_non_negative_constraint` — inserir `accident_number=-1` → `IntegrityError`.
- `test_single_active_accident_partial_index` — inserir 2 acidentes com `closed_at=None` → segundo INSERT deve falhar. Fechar primeiro (`closed_at=NOW()`) e abrir outro → permitido.
- `test_accident_user_report_zone_status_constraints` — `zone='invalid'` e `status='invalid'` → falham.
- `test_accident_user_report_unique_per_user_per_accident` — duplo INSERT `(accident_id, user_id)` → falha.
- `test_accident_video_upload_idempotency_key_unique` — duplo `idempotency_key` → falha.
- `test_accident_archive_unique_per_accident` — duas archives no mesmo acidente → falha.
- `test_email_delivery_log_status_constraint` — `delivery_status='invalid'` → falha.

---

### [ ] Task A2 — Adicionar Pydantic schemas para o Modo Acidente

**Contexto.** O arquivo [sistema/app/schemas.py](../sistema/app/schemas.py) tem ~4290 linhas e segue o padrão `class XxxResponse(BaseModel)` / `class XxxRequest(BaseModel)`. Vamos adicionar ~15 schemas para os fluxos do acidente.

**Arquivos.**
- Editar: [sistema/app/schemas.py](../sistema/app/schemas.py)

**Especificação.**
1. Adicionar ao **final** do arquivo a seção `# ---- Modo Acidente ----`.
2. Schemas a criar (referência Phase 1.6 do plano):
   - `AccidentProjectOption(BaseModel)`: `id: int`, `name: str`.
   - `AccidentLocationOption(BaseModel)`: `id: int`, `name: str`, `registered: bool`.
   - `AccidentVideoLink(BaseModel)`: `video_id: int`, `public_url: str`, `captured_at: datetime`, `content_type: str`, `size_bytes: int`.
   - `SituacaoPessoalRow(BaseModel)`:
     - `user_id: int`
     - `event_time: datetime`
     - `name: str`
     - `chave: str`
     - `projects: list[str]`
     - `local: str | None`
     - `zone: Literal["Aguardando","Segurança","Acidente"]`
     - `status: Literal["Aguardando","OK","AJUDA"]`
     - `phone: str | None`
     - `videos: list[AccidentVideoLink]`
     - `priority: int`  # 1..5
     - `row_color: Literal["white","blinking-red","yellow","turquoise","light-green","light-gray"]`
   - `AccidentSummary(BaseModel)`:
     - `id: int`, `accident_number: int`, `accident_number_label: str` (formato 4 dígitos)
     - `project_name: str`, `location_name: str`, `location_is_registered: bool`
     - `origin: Literal["admin","web"]`
     - `opened_by_label: str`, `opened_at: datetime`
     - `closed_at: datetime | None`
   - `AdminAccidentStateResponse(BaseModel)`:
     - `is_active: bool`
     - `accident: AccidentSummary | None = None`
     - `situation_rows: list[SituacaoPessoalRow] = []`
   - `AdminAccidentOpenRequest(BaseModel)`:
     - `project_id: int`
     - `location_id: int | None = None`
     - `custom_location_name: str | None = None`
     - Validador: pelo menos um entre `location_id` e `custom_location_name` precisa existir (e não os dois ao mesmo tempo).
   - `WebAccidentUserReport(BaseModel)`:
     - `zone: Literal["safety","accident"] | None`
     - `status: Literal["ok","help"] | None`
     - `reported_at: datetime | None`
   - `WebAccidentStateResponse(BaseModel)`:
     - `is_active: bool`
     - `accident_number_label: str | None = None`
     - `project_name: str | None = None`
     - `location_name: str | None = None`
     - `current_user_report: WebAccidentUserReport | None = None`
   - `WebAccidentOpenRequest(BaseModel)`:
     - `chave: str` (4 alfa-num)
     - `project_id: int`
     - `location_id: int | None`
     - `custom_location_name: str | None`
     - `zone: Literal["safety","accident"]`
     - `status: Literal["ok","help"]`
     - Mesmo validador `location_id` xor `custom_location_name`.
   - `WebAccidentReportRequest(BaseModel)`:
     - `chave: str`
     - `zone: Literal["safety","accident"]`
     - `status: Literal["ok","help"]`
   - `AccidentVideoUploadResponse(BaseModel)`:
     - `video_id: int`
     - `public_url: str`
     - `captured_at: datetime`
   - `AccidentClosedRow(BaseModel)`:
     - `id: int`
     - `accident_number_label: str`
     - `project_name: str`
     - `author_label: str`
     - `opened_at: datetime`
     - `closed_at: datetime`
     - `download_url: str`
     - `download_ready: bool`  # False enquanto archive ainda está em build
     - `can_delete: bool`
   - `AccidentClosedListResponse(BaseModel)`:
     - `rows: list[AccidentClosedRow]`
3. Validadores Pydantic (usar `@field_validator` ou `@model_validator`):
   - `AdminAccidentOpenRequest.check_location_xor` e `WebAccidentOpenRequest.check_location_xor`.
   - `WebAccidentOpenRequest.chave` precisa ser uppercase de 4 alfa-num.

**Critérios de aceitação.**
- `from sistema.app.schemas import AdminAccidentStateResponse, WebAccidentOpenRequest, SituacaoPessoalRow` funciona.
- Validador rejeita request sem `location_id` nem `custom_location_name`.
- Validador rejeita request com os dois.

**Testes obrigatórios** (criar `tests/schemas/test_accident_schemas.py`):
- `test_admin_open_request_requires_location_or_custom`
- `test_admin_open_request_rejects_both_location_and_custom`
- `test_web_open_request_normalizes_chave`
- `test_situacao_pessoal_row_zone_status_literal_enforced`
- `test_accident_summary_label_format` (gerado pelo service depois, mas o schema aceita string `"0042"`).

---

### [ ] Task A3 — Script de migração SQL para Postgres

**Contexto.** O sistema produção rodando em Digital Ocean usa Postgres. Não há Alembic configurado, então geramos o DDL manualmente. A operação tem que aplicá-lo via `psql` antes do deploy.

**Arquivos.**
- Criar: `sistema/scripts/migrate_accidents_v1.sql`

**Especificação.**
1. Cabeçalho com comentário:
   ```sql
   -- Migration: accidents v1
   -- Apply via: psql $DATABASE_URL -f migrate_accidents_v1.sql
   -- Idempotent: uses IF NOT EXISTS where possible.
   ```
2. `CREATE TABLE IF NOT EXISTS accidents (...)` com todas as colunas, constraints, FK para `projects`, `users`, `admin_users`.
3. Idem para `accident_user_reports`, `accident_video_uploads`, `accident_archives`, `email_delivery_logs`.
4. Índices:
   ```sql
   CREATE UNIQUE INDEX IF NOT EXISTS ix_accidents_single_active
     ON accidents (closed_at)
     WHERE closed_at IS NULL;

   CREATE INDEX IF NOT EXISTS ix_accident_video_uploads_accident_user
     ON accident_video_uploads (accident_id, user_id);

   CREATE INDEX IF NOT EXISTS ix_email_delivery_logs_accident
     ON email_delivery_logs (accident_id);
   ```
5. Comentário final com instruções de rollback:
   ```sql
   -- Rollback (use with caution):
   -- DROP TABLE accident_archives, accident_video_uploads, accident_user_reports,
   --   email_delivery_logs, accidents CASCADE;
   ```

**Critérios de aceitação.**
- Aplicar o SQL num Postgres vazio (CI ou container local) cria todas as tabelas.
- Aplicar duas vezes não dá erro (idempotência via `IF NOT EXISTS`).
- DDL bate **byte a byte** com o que o `Base.metadata.create_all` produziria.

**Testes manuais** (não automatizados — comando):
```bash
docker run -d --name pg-test -e POSTGRES_PASSWORD=test postgres:15
docker exec -i pg-test psql -U postgres < sistema/scripts/migrate_accidents_v1.sql
docker exec -i pg-test psql -U postgres -c "\dt"  # lista tabelas
docker exec -i pg-test psql -U postgres -c "\d accidents"  # mostra schema
docker rm -f pg-test
```

---

## Bloco B — Real-time (broker + SSE Checking Web)

### [ ] Task B1 — Adicionar broker `web_check_updates_broker`

**Contexto.** Hoje existem dois brokers em [sistema/app/services/admin_updates.py](../sistema/app/services/admin_updates.py) (linhas 273-274): `admin_updates_broker` (canal Postgres `checking_admin_updates`) e `transport_updates_broker` (canal `checking_transport_updates`). A Checking Web atualmente só escuta o broker de transporte. Precisamos de um terceiro broker para que eventos de acidente possam ser empurrados a todos os clientes web sem precisar dependerem do canal de transporte.

**Arquivos.**
- Editar: [sistema/app/services/admin_updates.py](../sistema/app/services/admin_updates.py)

**Especificação.**
1. Logo após a linha 274 (`transport_updates_broker = AdminUpdatesBroker(...)`), adicionar:
   ```python
   web_check_updates_broker = AdminUpdatesBroker("checking_web_check_updates")
   ```
2. Em `start_realtime_brokers()` (linhas 277-279), adicionar:
   ```python
   web_check_updates_broker.start()
   ```
3. Em `stop_realtime_brokers()` (linhas 282-284), adicionar:
   ```python
   web_check_updates_broker.stop()
   ```
4. Adicionar helper logo após `notify_transport_data_changed` (linha 291):
   ```python
   def notify_web_check_data_changed(reason: str = "refresh", *, metadata: dict[str, object] | None = None) -> None:
       web_check_updates_broker.publish(reason=reason, metadata=metadata)
   ```

**Critérios de aceitação.**
- `from sistema.app.services.admin_updates import web_check_updates_broker, notify_web_check_data_changed` funciona.
- `start_realtime_brokers()` / `stop_realtime_brokers()` iniciam e param os 3 brokers.

**Testes obrigatórios** (criar `tests/services/test_admin_updates_brokers.py`):
- `test_web_check_broker_publish_fanout` — subscribe, publish, assert payload entregue.
- `test_web_check_broker_isolated_from_admin` — publish em `admin_updates_broker` não chega ao `web_check_updates_broker` (canais diferentes).
- `test_start_stop_all_brokers` — chamar `start_realtime_brokers()` e `stop_realtime_brokers()` sem erro.

---

### [ ] Task B2 — Adicionar endpoint SSE `/api/web/check/stream`

**Contexto.** A Checking Web ainda não tem um stream SSE geral — só o de transporte ([sistema/app/routers/web_check.py:553-585](../sistema/app/routers/web_check.py#L553-L585)). Precisamos espelhar esse padrão para `web_check_updates_broker`, autenticando o cliente pela sessão web (mesmo guard de `chave`).

**Arquivos.**
- Editar: [sistema/app/routers/web_check.py](../sistema/app/routers/web_check.py)

**Especificação.**
1. No bloco de imports (próximo da linha 41), adicionar `web_check_updates_broker` ao import:
   ```python
   from ..services.admin_updates import (
       notify_admin_data_changed,
       notify_transport_data_changed,
       notify_web_check_data_changed,
       transport_updates_broker,
       web_check_updates_broker,
   )
   ```
2. Adicionar o endpoint logo após `stream_web_transport_updates` (após a linha 585):
   ```python
   @router.get("/check/stream")
   async def stream_web_check_updates(
       request: Request,
       chave: str = Query(min_length=4, max_length=4),
       db: Session = Depends(get_db),
   ) -> StreamingResponse:
       _require_matching_authenticated_web_user(request, db, chave)
       subscriber_id, queue = web_check_updates_broker.subscribe()

       async def event_generator():
           try:
               yield _encode_sse({"reason": "connected"})
               while True:
                   if await request.is_disconnected():
                       break

                   try:
                       payload = await asyncio.wait_for(queue.get(), timeout=15)
                       yield f"data: {payload}\n\n"
                   except asyncio.TimeoutError:
                       yield ": keep-alive\n\n"
           finally:
               web_check_updates_broker.unsubscribe(subscriber_id)

       return StreamingResponse(
           event_generator(),
           media_type="text/event-stream",
           headers={
               "Cache-Control": "no-cache",
               "Connection": "keep-alive",
               "X-Accel-Buffering": "no",
           },
       )
   ```

**Critérios de aceitação.**
- `GET /api/web/check/stream?chave=XXXX` com sessão web válida retorna `text/event-stream` e a primeira linha é `data: {"reason": "connected"}`.
- Sem sessão → 401 (vem do `_require_matching_authenticated_web_user`).
- Mensagens publicadas via `notify_web_check_data_changed` chegam ao cliente.

**Testes obrigatórios** (adicionar em `tests/routers/test_web_check_stream.py`):
- `test_stream_requires_session`
- `test_stream_initial_connected_event`
- `test_stream_receives_published_payload`
- `test_stream_keepalive_after_15s` (usar `freeze_time` ou config timeout=0.1s para teste rápido).

---

## Bloco C — Service layer (lifecycle, numbering, situação table)

### [ ] Task C1 — Criar `accident_numbering.py`

**Contexto.** O descritivo (item 6) diz "O primeiro acidente deve ser o 0000". Precisamos de uma função pura para gerar o próximo número.

**Arquivos.**
- Criar: [sistema/app/services/accident_numbering.py](../sistema/app/services/accident_numbering.py)

**Especificação.**
```python
from sqlalchemy import text
from sqlalchemy.orm import Session


def next_accident_number(db: Session) -> int:
    """Devolve o próximo número sequencial (>=0). Primeiro acidente = 0."""
    row = db.execute(
        text("SELECT COALESCE(MAX(accident_number), -1) + 1 FROM accidents")
    ).scalar_one()
    return int(row)


def format_accident_number(number: int) -> str:
    """Formata como 4 dígitos zero-padded ('0000', '0001', ...)."""
    return f"{int(number):04d}"
```

**Critérios de aceitação.**
- Sem nenhum acidente: `next_accident_number(db) == 0`.
- Com `accident_number=42` no banco: `next_accident_number(db) == 43`.
- `format_accident_number(0) == "0000"`, `format_accident_number(42) == "0042"`, `format_accident_number(9999) == "9999"`.

**Testes obrigatórios** (criar `tests/services/test_accident_numbering.py`):
- `test_next_accident_number_starts_at_zero`
- `test_next_accident_number_increments`
- `test_format_accident_number_pads_to_4_digits`
- `test_format_accident_number_handles_large_values`

---

### [ ] Task C2 — Criar `accident_lifecycle.py` — funções `open_accident` e `close_accident`

**Contexto.** Service principal do ciclo de vida. Phase 3.2 do plano.

**Arquivos.**
- Criar: [sistema/app/services/accident_lifecycle.py](../sistema/app/services/accident_lifecycle.py)

**Especificação.**
1. Imports necessários: `datetime`, `json`, `Literal`, `User`, `Accident`, `AccidentUserReport`, `AccidentArchive`, `CheckingHistory`, `ManagedLocation`, `Project`, `UserProjectMembership`, `now_sgt` (de `time_utils`), `next_accident_number` / `format_accident_number`, `notify_admin_data_changed` / `notify_web_check_data_changed`.

2. Exceções customizadas:
   ```python
   class AccidentAlreadyActiveError(RuntimeError): pass
   class NoActiveAccidentError(RuntimeError): pass
   class InvalidAccidentLocationError(ValueError): pass
   ```

3. `open_accident(db, *, origin, project_id, location_id, custom_location_name, opened_by_admin_id, opened_by_user_id, reporter_zone=None, reporter_status=None) -> Accident`:
   - Lock advisory: `db.execute(text("SELECT id FROM accidents WHERE closed_at IS NULL FOR UPDATE"))`. Se retornar linha → `raise AccidentAlreadyActiveError`. (Em SQLite o `FOR UPDATE` é noop, mas o índice parcial evita a corrida.)
   - Resolver `project = db.get(Project, project_id)`. Se `None` → `ValueError("Projeto não encontrado")`.
   - Resolver `location_name`:
     - Se `location_id` → carregar `ManagedLocation`, `location_is_registered=True`. Validação cruzada: se `origin == "admin"` e o `projects_json` do `ManagedLocation` não inclui `project.name` → `raise InvalidAccidentLocationError`. Se `origin == "web"`, aceitar mesmo assim (item 4.2 do descritivo permite usuário reportar local de outro projeto).
     - Senão → usar `custom_location_name.strip()`, `location_is_registered=False`.
   - `number = next_accident_number(db)`.
   - Criar `Accident(...)` com `opened_at=now_sgt()`, `created_at=now_sgt()`, `updated_at=now_sgt()`.
   - `db.add(accident); db.flush()` (para ter `accident.id`).
   - **Pré-popular `accident_user_reports`** para todos os usuários cujo `User.checkin == True` ou cuja última atividade tenha sido check-in. Query:
     ```python
     candidates = db.execute(
         select(User).where(User.checkin == True)
     ).scalars().all()
     ```
     Para cada `user`:
     - `projects = list_user_project_names(db, user)` (helper já existe em `user_projects.py`).
     - `report = AccidentUserReport(accident_id=accident.id, user_id=user.id, user_chave_snapshot=user.chave, user_name_snapshot=user.nome, user_phone_snapshot=None, user_projects_snapshot=json.dumps(projects), user_local_snapshot=user.local, zone="waiting", status="waiting", last_checkin_action="check-in", last_action_at=user.time, created_at=now_sgt(), updated_at=now_sgt())`
     - `db.add(report)`.
   - Se `origin == "web"` e `opened_by_user_id` está em `candidates` (e tem `reporter_zone`/`reporter_status`), atualizar **essa** linha com `zone=reporter_zone`, `status=reporter_status`, `reported_at=now_sgt()`.
   - Se `origin == "web"` e `opened_by_user_id` **não** está em `candidates` (usuário não fez check-in hoje), criar a linha mesmo assim com `zone=reporter_zone`, `status=reporter_status`.
   - `db.commit()`.
   - Publicar broker em ambos:
     ```python
     metadata = {
         "accident_id": accident.id,
         "accident_number_label": format_accident_number(accident.accident_number),
         "project_name": accident.project_name_snapshot,
     }
     notify_admin_data_changed("accident_opened", metadata=metadata)
     notify_web_check_data_changed("accident_opened", metadata=metadata)
     ```
   - Retornar `accident`.

4. `list_active_accident(db) -> Accident | None`:
   ```python
   return db.execute(
       select(Accident).where(Accident.closed_at.is_(None))
   ).scalar_one_or_none()
   ```

5. `close_accident(db, *, accident, closed_by_admin_id) -> Accident`:
   - Se `accident.closed_at is not None` → `raise NoActiveAccidentError`.
   - `accident.closed_at = now_sgt()`
   - `accident.closed_by_admin_id = closed_by_admin_id`
   - `accident.updated_at = now_sgt()`
   - `db.commit()`
   - Publicar broker `accident_closed` com mesmo `metadata`.
   - **NOTA**: a criação do `AccidentArchive` (ZIP) é Task F2 e é chamada **separadamente** via `BackgroundTasks` para não bloquear o request (Phase 10.4 do plano).
   - Retornar `accident`.

**Critérios de aceitação.**
- `open_accident` sem outro ativo → cria com `accident_number=0` na primeira vez.
- Segundo `open_accident` simultâneo → `AccidentAlreadyActiveError`.
- Após `close_accident`, novo `open_accident` aceita e cria `accident_number=1`.
- Pré-população cria 1 `AccidentUserReport` por usuário com `checkin=True`.
- Se `origin="web"`, a linha do autor tem `zone`/`status` já preenchidos.
- Broker publica em **ambos** os canais.

**Testes obrigatórios** (criar `tests/services/test_accident_lifecycle.py`):
- `test_open_accident_creates_with_number_zero`
- `test_open_accident_raises_when_already_active`
- `test_close_accident_marks_closed_at_and_admin`
- `test_close_then_open_increments_number`
- `test_open_admin_validates_location_belongs_to_project`
- `test_open_web_accepts_location_from_other_project`
- `test_open_prepopulates_user_reports_for_checked_in_users`
- `test_open_web_sets_reporter_zone_status_for_author`
- `test_close_raises_when_not_active`
- `test_open_publishes_to_both_brokers`
- `test_close_publishes_to_both_brokers`

---

### [ ] Task C3 — Estender `accident_lifecycle.py` — `upsert_user_safety_report` e `attach_video_upload`

**Contexto.** Continuação do service. Phase 3.2 (funções 3 e 4).

**Arquivos.**
- Editar: [sistema/app/services/accident_lifecycle.py](../sistema/app/services/accident_lifecycle.py) (criado em Task C2)

**Especificação.**
1. `upsert_user_safety_report(db, *, accident, user, zone, status) -> tuple[AccidentUserReport, bool]`:
   - Retorna `(report, fired_help_now)`. `fired_help_now=True` se status mudou para `help` nesta chamada (anterior não era `help`).
   - Carregar/criar `AccidentUserReport(accident_id, user_id)`. Se novo, capturar snapshots.
   - Capturar `previous_status = report.status` antes do update.
   - `report.zone = zone`; `report.status = status`; `report.reported_at = now_sgt()`; `report.updated_at = now_sgt()`.
   - `db.commit()`.
   - `fired_help_now = (status == "help" and previous_status != "help")`.
   - Publicar `accident_user_report` em ambos os brokers.
   - Retornar `(report, fired_help_now)`.

2. `attach_video_upload(db, *, accident, user, object_key, public_url, content_type, size_bytes, duration_seconds, idempotency_key, captured_at=None) -> AccidentVideoUpload`:
   - Query por `idempotency_key`. Se já existe, retornar a linha existente (idempotência).
   - `upload = AccidentVideoUpload(...)` com `captured_at=captured_at or now_sgt()`, `created_at=now_sgt()`.
   - `db.add(upload); db.commit()`.
   - Publicar `accident_video_uploaded` em ambos os brokers com `metadata={"accident_id": ..., "user_id": ...}`.
   - Retornar `upload`.

3. `update_accident_membership_for_check_event(db, *, accident, user, action: Literal["check-in","check-out"], event_time)`:
   - Carregar (ou criar) `AccidentUserReport(accident_id, user_id)`.
   - Se criar: snapshots + `zone="waiting"`, `status="waiting"`.
   - Atualizar `last_checkin_action=action`, `last_action_at=event_time`, `updated_at=now_sgt()`.
   - `db.commit()`.
   - Publicar `accident_user_report` em ambos os brokers.

**Critérios de aceitação.**
- Upsert mantém `created_at` quando atualizando linha existente.
- `fired_help_now=True` somente na transição non-help → help.
- `attach_video_upload` é idempotente por `idempotency_key`.

**Testes obrigatórios** (mesmo arquivo de teste da Task C2):
- `test_upsert_creates_when_missing`
- `test_upsert_updates_when_existing_and_preserves_created_at`
- `test_upsert_fires_help_only_on_transition`
- `test_upsert_does_not_fire_help_on_consecutive_help`
- `test_attach_video_inserts_first_time`
- `test_attach_video_idempotent_by_key`
- `test_check_event_hook_creates_waiting_row_for_new_user`
- `test_check_event_hook_preserves_zone_status_when_user_already_reported`

---

### [ ] Task C4 — Criar `accident_situation_table.py`

**Contexto.** Constrói as linhas que vão para a aba 'Situação de Pessoal' do admin. Phase 3.3.

**Arquivos.**
- Criar: [sistema/app/services/accident_situation_table.py](../sistema/app/services/accident_situation_table.py)

**Especificação.**
1. `build_situation_rows(db, *, accident) -> list[SituacaoPessoalRow]`:
   - Query: `select(AccidentUserReport).where(AccidentUserReport.accident_id == accident.id)` + `LEFT JOIN AccidentVideoUpload` agrupado por `user_id`.
   - Mapping zone/status → display + cor + prioridade:
     ```python
     def derive_display(report: AccidentUserReport, opened_at: datetime) -> tuple[str, str, str, int]:
         """Retorna (zone_display, status_display, row_color, priority)."""
         # Regra Prioridade 5: usuário fez check-out durante o modo acidente
         if (
             report.last_checkin_action == "check-out"
             and report.last_action_at is not None
             and report.last_action_at >= opened_at
         ):
             zone_display = "Segurança" if report.zone == "safety" else ("Acidente" if report.zone == "accident" else "Aguardando")
             status_display = "OK" if report.status == "ok" else ("AJUDA" if report.status == "help" else "Aguardando")
             return zone_display, status_display, "light-gray", 5

         if report.zone == "accident" and report.status == "help":
             return "Acidente", "AJUDA", "blinking-red", 1
         if report.zone == "accident" and report.status == "ok":
             return "Acidente", "OK", "yellow", 2
         if report.zone == "waiting":
             return "Aguardando", "Aguardando", "turquoise", 3
         if report.zone == "safety" and report.status == "ok":
             return "Segurança", "OK", "light-green", 4
         return "Aguardando", "Aguardando", "white", 3
     ```
   - Para cada report:
     - `event_time = report.reported_at or report.last_action_at or report.created_at`.
     - `projects = json.loads(report.user_projects_snapshot or "[]")`.
     - `videos = [AccidentVideoLink(...)]` ordenados por `captured_at ASC`.
     - `zone_display, status_display, row_color, priority = derive_display(report, accident.opened_at)`.
   - Ordenar lista por `(priority ASC, event_time DESC)`.
   - Retornar `list[SituacaoPessoalRow]`.

**Critérios de aceitação.**
- Linhas com `accident/help` vêm primeiro (prioridade 1) com cor `blinking-red`.
- Linhas com check-out após `accident.opened_at` ficam em prioridade 5 com cor `light-gray`.
- Dentro de cada prioridade, mais recente primeiro.

**Testes obrigatórios** (criar `tests/services/test_accident_situation_table.py`):
- `test_priority_1_help_blinking_red`
- `test_priority_2_accident_ok_yellow`
- `test_priority_3_waiting_turquoise`
- `test_priority_4_safety_ok_light_green`
- `test_priority_5_checked_out_after_open_light_gray`
- `test_within_same_priority_more_recent_first`
- `test_videos_included_per_user`
- `test_videos_ordered_by_captured_at_asc`

---

### [ ] Task C5 — Hook de check-in/check-out durante modo acidente

**Contexto.** Phase 11 do plano. Quando há acidente em curso e um usuário faz check-in/check-out, o `AccidentUserReport` precisa refletir. Pontos de chamada: [sistema/app/services/forms_submit.py](../sistema/app/services/forms_submit.py), [sistema/app/routers/device.py](../sistema/app/routers/device.py), [sistema/app/routers/mobile.py](../sistema/app/routers/mobile.py).

**Arquivos.**
- Editar: [sistema/app/services/forms_submit.py](../sistema/app/services/forms_submit.py)
- Editar: [sistema/app/routers/device.py](../sistema/app/routers/device.py)
- Editar: [sistema/app/routers/mobile.py](../sistema/app/routers/mobile.py)

**Especificação.**
1. Em cada ponto onde um `CheckEvent`/`CheckingHistory` é gravado com sucesso e `db.commit()` foi feito, adicionar:
   ```python
   from ..services.accident_lifecycle import list_active_accident, update_accident_membership_for_check_event

   active = list_active_accident(db)
   if active is not None:
       update_accident_membership_for_check_event(
           db,
           accident=active,
           user=user,
           action=action,         # 'check-in' ou 'check-out'
           event_time=event_time,
       )
   ```
2. Identificar os pontos exatos:
   - `forms_submit.py` — função `submit_forms_event` (consultar arquivo para localizar logo após o commit do histórico).
   - `device.py` — handler do endpoint `/api/scan` ou similar, após `notify_admin_data_changed(action)` ([sistema/app/routers/device.py:226](../sistema/app/routers/device.py#L226), [sistema/app/routers/device.py:301](../sistema/app/routers/device.py#L301)).
   - `mobile.py` — handlers após `notify_admin_data_changed(payload.action)` ([sistema/app/routers/mobile.py:175](../sistema/app/routers/mobile.py#L175), [sistema/app/routers/mobile.py:233](../sistema/app/routers/mobile.py#L233), [sistema/app/routers/mobile.py:312](../sistema/app/routers/mobile.py#L312)).
3. O hook **não deve** levantar exceção que afete o fluxo de check-in. Envolver em try/except logando warning, jamais propagando para o cliente.

**Critérios de aceitação.**
- Check-in durante acidente cria linha `waiting` no `AccidentUserReport`.
- Check-out durante acidente atualiza `last_checkin_action` e `last_action_at`, mantendo `zone`/`status`.
- Se acidente não ativo, o hook é noop.
- Falha do hook não falha o check-in.

**Testes obrigatórios** (criar `tests/services/test_accident_check_event_hook.py`):
- `test_hook_skips_when_no_active_accident`
- `test_hook_creates_waiting_report_for_new_user_check_in`
- `test_hook_updates_last_action_for_existing_user_check_out`
- `test_hook_swallows_exceptions` (mockar `update_accident_membership_for_check_event` para levantar; verificar que o flow de submit não falha).
- E um integration test do endpoint `/api/web/check` (POST) verificando que o hook foi chamado.

---

## Bloco D — Endpoints Admin

### [ ] Task D1 — Endpoint `GET /api/admin/accidents/active`

**Contexto.** Phase 4.1. Retorna o estado atual do modo acidente, incluindo a tabela `Situação de Pessoal` se ativo. É chamado pela UI admin para popular a aba 'Acidente'.

**Arquivos.**
- Editar: [sistema/app/routers/admin.py](../sistema/app/routers/admin.py)

**Especificação.**
1. Local sugerido: logo após o endpoint `/stream` (após linha 1960).
2. Helper para `AccidentSummary` a partir de `Accident`:
   ```python
   def _accident_summary(db: Session, accident: Accident) -> AccidentSummary:
       opened_by_label = "—"
       if accident.opened_by_admin_id:
           admin = db.get(AdminUser, accident.opened_by_admin_id)
           if admin: opened_by_label = admin.nome_completo
       elif accident.opened_by_user_id:
           user = db.get(User, accident.opened_by_user_id)
           if user: opened_by_label = user.nome
       return AccidentSummary(
           id=accident.id,
           accident_number=accident.accident_number,
           accident_number_label=format_accident_number(accident.accident_number),
           project_name=accident.project_name_snapshot,
           location_name=accident.location_name_snapshot,
           location_is_registered=accident.location_is_registered,
           origin=accident.origin,
           opened_by_label=opened_by_label,
           opened_at=accident.opened_at,
           closed_at=accident.closed_at,
       )
   ```
3. Endpoint:
   ```python
   @router.get("/accidents/active", response_model=AdminAccidentStateResponse, dependencies=[Depends(require_admin_session)])
   def get_active_accident_state(db: Session = Depends(get_db)) -> AdminAccidentStateResponse:
       active = list_active_accident(db)
       if active is None:
           return AdminAccidentStateResponse(is_active=False)
       return AdminAccidentStateResponse(
           is_active=True,
           accident=_accident_summary(db, active),
           situation_rows=build_situation_rows(db, accident=active),
       )
   ```

**Critérios de aceitação.**
- Sem acidente ativo: `{"is_active": false, "accident": null, "situation_rows": []}`.
- Com acidente ativo: payload completo, com `situation_rows` na ordem por prioridade.
- Endpoint requer sessão admin (qualquer perfil, 0/1/9).

**Testes obrigatórios** (criar `tests/routers/test_admin_accidents.py`):
- `test_active_returns_empty_when_none`
- `test_active_returns_accident_and_rows`
- `test_active_requires_session`

---

### [ ] Task D2 — Endpoint `POST /api/admin/accidents/open`

**Contexto.** Phase 4.2. Abre o modo acidente a partir do admin.

**Arquivos.**
- Editar: [sistema/app/routers/admin.py](../sistema/app/routers/admin.py)

**Especificação.**
```python
@router.post("/accidents/open", response_model=AdminAccidentStateResponse, dependencies=[Depends(require_full_admin_session)])
def open_admin_accident(
    payload: AdminAccidentOpenRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_full_admin_session),
) -> AdminAccidentStateResponse:
    try:
        accident = open_accident(
            db,
            origin="admin",
            project_id=payload.project_id,
            location_id=payload.location_id,
            custom_location_name=payload.custom_location_name,
            opened_by_admin_id=current_admin.id,
            opened_by_user_id=None,
        )
    except AccidentAlreadyActiveError:
        raise HTTPException(status_code=409, detail="Ja existe um acidente em curso.")
    except InvalidAccidentLocationError:
        raise HTTPException(status_code=422, detail="O local selecionado nao pertence ao projeto.")

    return AdminAccidentStateResponse(
        is_active=True,
        accident=_accident_summary(db, accident),
        situation_rows=build_situation_rows(db, accident=accident),
    )
```

Loga via `log_event(db, source="admin", action="accident_open", ...)`.

**Critérios de aceitação.**
- 401 sem sessão admin.
- 403 sem perfil 1+.
- 409 se já há acidente.
- 422 se body inválido (validador de schema) ou local inválido.
- 200 com estado atualizado.
- `accident_opened` foi publicado em ambos os brokers.

**Testes obrigatórios** (no mesmo arquivo de Task D1):
- `test_open_requires_full_admin`
- `test_open_creates_when_none`
- `test_open_returns_conflict_when_active`
- `test_open_validates_payload`
- `test_open_publishes_brokers`

---

### [ ] Task D3 — Endpoint `POST /api/admin/accidents/close`

**Contexto.** Phase 4.3. Encerra o acidente ativo. Dispara geração do ZIP em background.

**Arquivos.**
- Editar: [sistema/app/routers/admin.py](../sistema/app/routers/admin.py)

**Especificação.**
```python
from fastapi import BackgroundTasks

@router.post("/accidents/close", response_model=AdminAccidentStateResponse, dependencies=[Depends(require_full_admin_session)])
def close_admin_accident(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_full_admin_session),
) -> AdminAccidentStateResponse:
    active = list_active_accident(db)
    if active is None:
        raise HTTPException(status_code=409, detail="Nenhum acidente em curso.")

    closed = close_accident(db, accident=active, closed_by_admin_id=current_admin.id)
    background_tasks.add_task(build_and_attach_archive_for_accident, closed.id)
    return AdminAccidentStateResponse(is_active=False)
```

`build_and_attach_archive_for_accident` virá da Task F2 (Phase 10). Por enquanto, criar um stub:
```python
def build_and_attach_archive_for_accident(accident_id: int) -> None:
    # TODO Task F2: build XLSX + ZIP, upload to Spaces, update accident.archive_object_key,
    # publish accident_closed again with ready=True.
    pass
```

**Critérios de aceitação.**
- 409 sem acidente ativo.
- 200 com `is_active=False` no payload.
- BackgroundTask agendada.
- `accident_closed` publicado.

**Testes obrigatórios:**
- `test_close_requires_full_admin`
- `test_close_conflict_when_none_active`
- `test_close_marks_closed_and_publishes`
- `test_close_schedules_archive_build`

---

### [ ] Task D4 — Endpoints `GET /api/admin/accidents` e `GET /api/admin/accidents/{id}/archive`

**Contexto.** Phase 4.4 e 4.6. Lista acidentes fechados (para a tabela "Acidentes" do Cadastro) e devolve URL pré-assinada para download.

**Arquivos.**
- Editar: [sistema/app/routers/admin.py](../sistema/app/routers/admin.py)

**Especificação.**

1. `GET /accidents`:
```python
@router.get("/accidents", response_model=AccidentClosedListResponse, dependencies=[Depends(require_full_admin_session)])
def list_closed_accidents_endpoint(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_full_admin_session),
) -> AccidentClosedListResponse:
    rows = []
    accidents = db.execute(
        select(Accident).where(Accident.closed_at.is_not(None)).order_by(Accident.accident_number.desc())
    ).scalars().all()
    for accident in accidents:
        archive = db.execute(select(AccidentArchive).where(AccidentArchive.accident_id == accident.id)).scalar_one_or_none()
        opened_by_label = ...  # mesmo helper de _accident_summary
        rows.append(AccidentClosedRow(
            id=accident.id,
            accident_number_label=format_accident_number(accident.accident_number),
            project_name=accident.project_name_snapshot,
            author_label=opened_by_label,
            opened_at=accident.opened_at,
            closed_at=accident.closed_at,
            download_url=f"/api/admin/accidents/{accident.id}/archive",
            download_ready=archive is not None,
            can_delete=(current_admin.perfil == 9),
        ))
    return AccidentClosedListResponse(rows=rows)
```

2. `GET /accidents/{accident_id}/archive`:
```python
@router.get("/accidents/{accident_id}/archive", dependencies=[Depends(require_full_admin_session)])
def download_accident_archive(
    accident_id: int,
    db: Session = Depends(get_db),
) -> Response:
    archive = db.execute(select(AccidentArchive).where(AccidentArchive.accident_id == accident_id)).scalar_one_or_none()
    if archive is None:
        raise HTTPException(status_code=404, detail="Arquivo do acidente ainda nao esta pronto.")
    presigned_url = generate_presigned_url(object_key=archive.zip_object_key, expires_in_seconds=300)
    return RedirectResponse(url=presigned_url, status_code=307)
```

(`generate_presigned_url` vem da Task E2.)

**Critérios de aceitação.**
- Lista vem ordenada por `accident_number DESC`.
- `download_ready=False` enquanto archive não existe; `True` quando existir.
- `can_delete` reflete `perfil == 9`.
- Download retorna 307 redirect para URL pré-assinada.
- 404 se archive ainda não foi gerado.

**Testes obrigatórios:**
- `test_list_returns_only_closed`
- `test_list_ordered_desc`
- `test_can_delete_true_only_for_perfil_9`
- `test_download_returns_307_when_ready`
- `test_download_returns_404_when_archive_missing`

---

### [ ] Task D5 — Endpoint `DELETE /api/admin/accidents/{id}` (perfil 9 only)

**Contexto.** Phase 4.5. Permite exclusão completa de um acidente fechado por admin perfil 9.

**Arquivos.**
- Editar: [sistema/app/routers/admin.py](../sistema/app/routers/admin.py)

**Especificação.**
```python
@router.delete("/accidents/{accident_id}", response_model=AdminActionResponse, dependencies=[Depends(require_full_admin_session)])
def delete_accident_endpoint(
    accident_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_full_admin_session),
) -> AdminActionResponse:
    if current_admin.perfil != 9:
        raise HTTPException(status_code=403, detail="Apenas perfil 9 pode remover acidentes.")
    accident = db.get(Accident, accident_id)
    if accident is None:
        raise HTTPException(status_code=404, detail="Acidente nao encontrado.")
    if accident.closed_at is None:
        raise HTTPException(status_code=409, detail="Nao e possivel remover um acidente em curso. Encerre o Modo Acidente primeiro.")

    archive = db.execute(select(AccidentArchive).where(AccidentArchive.accident_id == accident.id)).scalar_one_or_none()
    accident_number = accident.accident_number
    db.delete(accident)  # cascade
    db.commit()

    delete_prefix(prefix=f"accidents/{format_accident_number(accident_number)}/")
    log_event(db, source="admin", action="accident_delete", status="done", message=f"Accident {accident_number} deleted", details=f"by admin={current_admin.chave}")
    db.commit()

    notify_admin_data_changed("accident_closed", metadata={"deleted_accident_id": accident_id})
    notify_web_check_data_changed("accident_closed", metadata={"deleted_accident_id": accident_id})

    return AdminActionResponse(ok=True, message="Acidente removido com sucesso.")
```

**Critérios de aceitação.**
- 403 se perfil != 9.
- 404 se id não existe.
- 409 se acidente ainda ativo.
- 200 com sucesso e cascata removendo reports/videos/archive.
- `delete_prefix` no Spaces apaga vídeos + archive.

**Testes obrigatórios:**
- `test_delete_forbidden_for_non_perfil_9`
- `test_delete_404_when_unknown`
- `test_delete_409_when_active`
- `test_delete_removes_cascade`
- `test_delete_calls_delete_prefix`

---

### [ ] Task D6 — Endpoints auxiliares do wizard (projects + locations)

**Contexto.** Phase 4.7 e 4.8.

**Arquivos.**
- Editar: [sistema/app/routers/admin.py](../sistema/app/routers/admin.py)

**Especificação.**
```python
@router.get("/accidents/wizard/projects", response_model=list[AccidentProjectOption], dependencies=[Depends(require_full_admin_session)])
def list_accident_wizard_projects(db: Session = Depends(get_db)) -> list[AccidentProjectOption]:
    return [AccidentProjectOption(id=p.id, name=p.name) for p in list_projects(db)]


@router.get("/accidents/wizard/locations", response_model=list[AccidentLocationOption], dependencies=[Depends(require_full_admin_session)])
def list_accident_wizard_locations(
    project_id: int = Query(...),
    db: Session = Depends(get_db),
) -> list[AccidentLocationOption]:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto nao encontrado.")
    options = []
    for loc in db.execute(select(ManagedLocation)).scalars().all():
        projects = []
        try:
            projects = json.loads(loc.projects_json or "[]")
        except Exception:
            projects = []
        if project.name in projects:
            options.append(AccidentLocationOption(id=loc.id, name=loc.local, registered=True))
    return options
```

**Critérios de aceitação.**
- Retorna projetos cadastrados.
- Filtra locations pelo `projects_json` do `ManagedLocation`.

**Testes obrigatórios:**
- `test_wizard_lists_all_projects`
- `test_wizard_locations_filtered_by_project`
- `test_wizard_locations_404_for_unknown_project`

---

## Bloco E — Endpoints Checking Web

### [ ] Task E1 — Endpoints `/api/web/check/accident/state` e `/api/web/check/accident/open`

**Contexto.** Phase 5.1 e 5.2.

**Arquivos.**
- Editar: [sistema/app/routers/web_check.py](../sistema/app/routers/web_check.py)

**Especificação.**
```python
@router.get("/check/accident/state", response_model=WebAccidentStateResponse)
def get_web_accident_state(
    request: Request,
    chave: str = Query(min_length=4, max_length=4),
    db: Session = Depends(get_db),
) -> WebAccidentStateResponse:
    user = _require_matching_authenticated_web_user(request, db, chave)
    active = list_active_accident(db)
    if active is None:
        return WebAccidentStateResponse(is_active=False)
    report = db.execute(
        select(AccidentUserReport).where(AccidentUserReport.accident_id == active.id, AccidentUserReport.user_id == user.id)
    ).scalar_one_or_none()
    return WebAccidentStateResponse(
        is_active=True,
        accident_number_label=format_accident_number(active.accident_number),
        project_name=active.project_name_snapshot,
        location_name=active.location_name_snapshot,
        current_user_report=WebAccidentUserReport(
            zone=("safety" if report and report.zone == "safety" else "accident" if report and report.zone == "accident" else None),
            status=("ok" if report and report.status == "ok" else "help" if report and report.status == "help" else None),
            reported_at=report.reported_at if report else None,
        ) if report else None,
    )


@router.post("/check/accident/open", response_model=WebAccidentStateResponse)
def open_web_accident(
    payload: WebAccidentOpenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WebAccidentStateResponse:
    user = _require_matching_authenticated_web_user(request, db, payload.chave)
    try:
        accident = open_accident(
            db,
            origin="web",
            project_id=payload.project_id,
            location_id=payload.location_id,
            custom_location_name=payload.custom_location_name,
            opened_by_admin_id=None,
            opened_by_user_id=user.id,
            reporter_zone=payload.zone,
            reporter_status=payload.status,
        )
    except AccidentAlreadyActiveError:
        raise HTTPException(status_code=409, detail="Outro usuario ja reportou um acidente.")
    # Reaproveitar helper get_web_accident_state-like inline
    return get_web_accident_state(request=request, chave=payload.chave, db=db)
```

**Critérios de aceitação.**
- `/state` sem sessão → 401.
- `/state` com acidente ativo retorna labels e `current_user_report`.
- `/open` cria acidente com origin=`web`, ação 2 do descritivo (primeiro registro é o autor).

**Testes obrigatórios** (criar `tests/routers/test_web_accidents.py`):
- `test_state_requires_session`
- `test_state_returns_inactive_when_none`
- `test_state_returns_user_report_when_active`
- `test_open_creates_with_origin_web`
- `test_open_returns_409_when_active`
- `test_open_publishes_brokers`

---

### [ ] Task E2 — Endpoint `POST /api/web/check/accident/report`

**Contexto.** Phase 5.3. Usuário envia seu status para um acidente em curso.

**Arquivos.**
- Editar: [sistema/app/routers/web_check.py](../sistema/app/routers/web_check.py)

**Especificação.**
```python
@router.post("/check/accident/report", response_model=WebAccidentStateResponse)
def report_web_accident_status(
    payload: WebAccidentReportRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> WebAccidentStateResponse:
    user = _require_matching_authenticated_web_user(request, db, payload.chave)
    active = list_active_accident(db)
    if active is None:
        raise HTTPException(status_code=409, detail="Nenhum acidente em curso.")
    _, fired_help = upsert_user_safety_report(db, accident=active, user=user, zone=payload.zone, status=payload.status)
    if fired_help:
        background_tasks.add_task(queue_help_request_emails, accident_id=active.id, requester_user_id=user.id)
    return get_web_accident_state(request=request, chave=payload.chave, db=db)
```

(`queue_help_request_emails` virá da Task G3.)

**Critérios de aceitação.**
- 409 se sem acidente ativo.
- Upsert do report.
- E-mail só agendado na transição non-help → help.

**Testes obrigatórios:**
- `test_report_409_when_no_active`
- `test_report_upserts`
- `test_report_schedules_email_on_help_transition`
- `test_report_does_not_schedule_email_on_repeat_help`

---

### [ ] Task E3 — Endpoint `POST /api/web/check/accident/video` (multipart)

**Contexto.** Phase 5.4. Upload de vídeo gravado durante acidente.

**Arquivos.**
- Editar: [sistema/app/routers/web_check.py](../sistema/app/routers/web_check.py)

**Especificação.**
```python
from fastapi import File, Form, UploadFile

MAX_VIDEO_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_VIDEO_TYPES = {"video/webm", "video/mp4", "video/quicktime"}


@router.post("/check/accident/video", response_model=AccidentVideoUploadResponse)
async def upload_accident_video(
    request: Request,
    chave: str = Form(...),
    idempotency_key: str = Form(..., min_length=8, max_length=80),
    duration_seconds: int | None = Form(None),
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> AccidentVideoUploadResponse:
    user = _require_matching_authenticated_web_user(request, db, chave)
    active = list_active_accident(db)
    if active is None:
        raise HTTPException(status_code=409, detail="Nenhum acidente em curso.")
    if video.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=415, detail="Tipo de video nao suportado.")

    accident_label = format_accident_number(active.accident_number)
    ext_map = {"video/webm": "webm", "video/mp4": "mp4", "video/quicktime": "mov"}
    ext = ext_map[video.content_type]
    safe_key = idempotency_key.replace("/", "_").replace(" ", "_")
    object_key = f"accidents/{accident_label}/{user.chave}/{safe_key}.{ext}"

    size_bytes, public_url = await stream_upload_to_storage(
        object_key=object_key,
        upload_file=video,
        content_type=video.content_type,
        max_bytes=MAX_VIDEO_BYTES,
    )

    upload = attach_video_upload(
        db,
        accident=active,
        user=user,
        object_key=object_key,
        public_url=public_url,
        content_type=video.content_type,
        size_bytes=size_bytes,
        duration_seconds=duration_seconds,
        idempotency_key=idempotency_key,
    )
    return AccidentVideoUploadResponse(
        video_id=upload.id,
        public_url=upload.public_url,
        captured_at=upload.captured_at,
    )
```

`stream_upload_to_storage` virá da Task F1. Para esta task, criar stub que apenas grava em disco local (modo dev).

**Critérios de aceitação.**
- 415 para content-type não permitido.
- 413 se size > 50MB (lançar HTTPException da função stream).
- 200 com `public_url`.
- Reenvio com mesma `idempotency_key` retorna o mesmo registro.

**Testes obrigatórios:**
- `test_video_rejects_unsupported_type`
- `test_video_rejects_oversized`
- `test_video_upload_success`
- `test_video_upload_idempotent`
- `test_video_requires_active_accident`

---

### [ ] Task E4 — Endpoints auxiliares wizard Checking Web (projects + locations)

**Contexto.** Phase 5.7. Para o wizard do usuário web.

**Arquivos.**
- Editar: [sistema/app/routers/web_check.py](../sistema/app/routers/web_check.py)

**Especificação.**
```python
@router.get("/check/accident/wizard/projects", response_model=list[AccidentProjectOption])
def list_web_accident_projects(
    request: Request,
    chave: str = Query(...),
    db: Session = Depends(get_db),
) -> list[AccidentProjectOption]:
    _require_matching_authenticated_web_user(request, db, chave)
    return [AccidentProjectOption(id=p.id, name=p.name) for p in list_projects(db)]


@router.get("/check/accident/wizard/locations", response_model=list[AccidentLocationOption])
def list_web_accident_locations(
    request: Request,
    chave: str = Query(...),
    project_id: int = Query(...),
    db: Session = Depends(get_db),
) -> list[AccidentLocationOption]:
    _require_matching_authenticated_web_user(request, db, chave)
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto nao encontrado.")
    options = []
    for loc in db.execute(select(ManagedLocation)).scalars().all():
        try:
            projects = json.loads(loc.projects_json or "[]")
        except Exception:
            projects = []
        if project.name in projects:
            options.append(AccidentLocationOption(id=loc.id, name=loc.local, registered=True))
    return options
```

**Critérios de aceitação.**
- Sem sessão → 401.
- Lista todos os projetos (item 4.2 — usuário vê todos).
- Locations filtradas por projeto.

**Testes obrigatórios:**
- `test_web_wizard_projects_requires_session`
- `test_web_wizard_projects_returns_all`
- `test_web_wizard_locations_filtered_by_project`

---

## Bloco F — Object Storage (DO Spaces) e Archive Builder

### [ ] Task F1 — Service `object_storage.py` (DO Spaces + fallback local)

**Contexto.** Phase 7. Não há integração Spaces no projeto hoje. Em dev usa disco local; em produção usa boto3.

**Arquivos.**
- Editar: [sistema/app/core/config.py](../sistema/app/core/config.py) — adicionar DO Spaces settings.
- Criar: [sistema/app/services/object_storage.py](../sistema/app/services/object_storage.py)
- Atualizar `requirements.txt` (ou equivalente) com `boto3>=1.34`.

**Especificação.**

1. `config.py`: adicionar `do_spaces_endpoint_url`, `do_spaces_region`, `do_spaces_bucket`, `do_spaces_access_key`, `do_spaces_secret_key`, `do_spaces_public_base_url`. Defaults `None`.

2. `object_storage.py`:
```python
from pathlib import Path
import shutil
from typing import IO

from ..core.config import settings


class ObjectStorageError(RuntimeError): pass


def _use_remote() -> bool:
    return bool(settings.do_spaces_bucket and settings.do_spaces_access_key and settings.do_spaces_secret_key)


def _local_root() -> Path:
    root = Path(settings.event_archives_dir) / "accidents_local_storage"
    root.mkdir(parents=True, exist_ok=True)
    return root


def upload_stream(*, object_key: str, stream: IO[bytes], content_type: str, cache_control: str = "private, max-age=0") -> str:
    if _use_remote():
        import boto3
        client = boto3.client(
            "s3",
            endpoint_url=settings.do_spaces_endpoint_url,
            region_name=settings.do_spaces_region,
            aws_access_key_id=settings.do_spaces_access_key,
            aws_secret_access_key=settings.do_spaces_secret_key,
        )
        client.upload_fileobj(
            Fileobj=stream,
            Bucket=settings.do_spaces_bucket,
            Key=object_key,
            ExtraArgs={"ContentType": content_type, "CacheControl": cache_control, "ACL": "private"},
        )
        base = (settings.do_spaces_public_base_url or settings.do_spaces_endpoint_url).rstrip("/")
        return f"{base}/{object_key}"

    # Local fallback
    target = _local_root() / object_key
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as f:
        shutil.copyfileobj(stream, f)
    return f"/api/admin/accidents/local-asset/{object_key}"


def generate_presigned_url(*, object_key: str, expires_in_seconds: int = 300) -> str:
    if _use_remote():
        import boto3
        client = boto3.client(
            "s3",
            endpoint_url=settings.do_spaces_endpoint_url,
            region_name=settings.do_spaces_region,
            aws_access_key_id=settings.do_spaces_access_key,
            aws_secret_access_key=settings.do_spaces_secret_key,
        )
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.do_spaces_bucket, "Key": object_key},
            ExpiresIn=expires_in_seconds,
        )
    return f"/api/admin/accidents/local-asset/{object_key}"


def delete_object(*, object_key: str) -> None:
    if _use_remote():
        import boto3
        client = boto3.client(...)  # mesmo
        client.delete_object(Bucket=settings.do_spaces_bucket, Key=object_key)
        return
    target = _local_root() / object_key
    if target.exists(): target.unlink()


def delete_prefix(*, prefix: str) -> int:
    """Apaga todas as chaves sob o prefixo. Retorna número de chaves apagadas."""
    if _use_remote():
        import boto3
        client = boto3.client(...)
        deleted = 0
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=settings.do_spaces_bucket, Prefix=prefix):
            objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
            if not objects: continue
            client.delete_objects(Bucket=settings.do_spaces_bucket, Delete={"Objects": objects})
            deleted += len(objects)
        return deleted

    root = _local_root() / prefix
    if not root.exists(): return 0
    count = sum(1 for _ in root.rglob("*") if _.is_file())
    shutil.rmtree(root, ignore_errors=True)
    return count


async def stream_upload_to_storage(*, object_key: str, upload_file, content_type: str, max_bytes: int) -> tuple[int, str]:
    """Lê o UploadFile em chunks até max_bytes, faz upload e retorna (size, public_url)."""
    from io import BytesIO
    buffer = BytesIO()
    total = 0
    chunk_size = 1024 * 1024
    while True:
        chunk = await upload_file.read(chunk_size)
        if not chunk: break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail="Video maior que o limite permitido.")
        buffer.write(chunk)
    buffer.seek(0)
    public_url = upload_stream(object_key=object_key, stream=buffer, content_type=content_type)
    return total, public_url
```

3. Adicionar endpoint dev `/api/admin/accidents/local-asset/{path:path}` em [sistema/app/routers/admin.py](../sistema/app/routers/admin.py) que serve do disco local **apenas** quando `_use_remote() == False`. Em produção retorna 404. Útil para que vídeos sejam visualizáveis nos testes locais.

**Critérios de aceitação.**
- Em dev (sem credenciais), `upload_stream` grava em disco e devolve URL `/api/admin/accidents/local-asset/...`.
- `delete_prefix` apaga recursivamente local.
- Em produção (com `do_spaces_bucket` definido) usa boto3.
- `stream_upload_to_storage` rejeita >max_bytes com 413.

**Testes obrigatórios** (criar `tests/services/test_object_storage.py`):
- `test_upload_local_writes_file`
- `test_upload_local_returns_path_url`
- `test_delete_prefix_removes_all`
- `test_stream_upload_rejects_oversized`
- `test_remote_mode_uses_boto3_mock` (usar `moto` ou mock manual em `unittest.mock`).
- `test_generate_presigned_url_local_falls_back_to_path`

---

### [ ] Task F2 — Archive builder (XLSX + ZIP)

**Contexto.** Phase 10. Gera o arquivo .xlsx com a tabela 'Situação de Pessoal' congelada + os vídeos como subpasta `Registros/`.

**Arquivos.**
- Criar: [sistema/app/services/accident_archive_builder.py](../sistema/app/services/accident_archive_builder.py)
- Atualizar `requirements.txt` com `openpyxl>=3.1`.

**Especificação.**
```python
from io import BytesIO
import json
import re
import zipfile

from openpyxl import Workbook
from openpyxl.styles import Alignment

from ..database import SessionLocal
from .accident_lifecycle import list_active_accident
from .accident_numbering import format_accident_number
from .accident_situation_table import build_situation_rows
from .object_storage import upload_stream, generate_presigned_url
from ..models import Accident, AccidentVideoUpload, AccidentArchive
from ..services.time_utils import now_sgt


COLUMN_ORDER = ["Horário", "Nome", "Chave", "Projetos", "Local", "Zona de", "Situação", "Contato", "Registros"]


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value)[:60]


def _build_xlsx(snapshot_rows, video_files_by_user) -> BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Situacao de Pessoal"
    ws.append(COLUMN_ORDER)
    for row in snapshot_rows:
        videos = video_files_by_user.get(row.user_id, [])
        registros_text = "\n".join(f"Registros/{filename}" for filename in videos)
        ws.append([
            row.event_time.isoformat(),
            row.name,
            row.chave,
            ", ".join(row.projects),
            row.local or "",
            row.zone,
            row.status,
            row.phone or "",
            registros_text,
        ])
        cell = ws.cell(row=ws.max_row, column=9)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        if videos:
            # Hyperlink no primeiro video (Excel não aceita múltiplos hyperlinks numa célula).
            cell.hyperlink = f"Registros/{videos[0]}"
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def build_and_attach_archive_for_accident(accident_id: int) -> None:
    with SessionLocal() as db:
        accident = db.get(Accident, accident_id)
        if accident is None:
            return
        snapshot_rows = build_situation_rows(db, accident=accident)
        videos = db.execute(select(AccidentVideoUpload).where(AccidentVideoUpload.accident_id == accident.id)).scalars().all()

        # Map user_id -> [filename, ...] e baixar conteúdo
        video_files_by_user: dict[int, list[str]] = {}
        video_payloads: dict[str, bytes] = {}
        for video in videos:
            ext = video.content_type.split("/")[-1]
            if ext == "quicktime": ext = "mov"
            filename = f"{video.user_id}-{_slugify(video.idempotency_key)}.{ext}"
            video_files_by_user.setdefault(video.user_id, []).append(filename)
            # baixar bytes via storage (presigned URL ou disco local)
            payload = _read_video_bytes(video.object_key)
            video_payloads[filename] = payload

        xlsx_bytes = _build_xlsx(snapshot_rows, video_files_by_user)

        # Construir ZIP
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            xlsx_name = f"{format_accident_number(accident.accident_number)}.xlsx"
            zf.writestr(xlsx_name, xlsx_bytes.getvalue())
            for filename, payload in video_payloads.items():
                zf.writestr(f"Registros/{filename}", payload)
        zip_buffer.seek(0)

        # Subir XLSX e ZIP no storage
        xlsx_key = f"accidents/{format_accident_number(accident.accident_number)}/archive/{xlsx_name}"
        zip_key = f"accidents/{format_accident_number(accident.accident_number)}/archive/{format_accident_number(accident.accident_number)}.zip"
        upload_stream(object_key=xlsx_key, stream=BytesIO(xlsx_bytes.getvalue()), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        upload_stream(object_key=zip_key, stream=zip_buffer, content_type="application/zip")

        size_bytes = zip_buffer.getbuffer().nbytes
        archive = AccidentArchive(
            accident_id=accident.id,
            snapshot_json=json.dumps([row.model_dump() for row in snapshot_rows], default=str),
            xlsx_object_key=xlsx_key,
            zip_object_key=zip_key,
            size_bytes=size_bytes,
            generated_at=now_sgt(),
        )
        accident.archive_object_key = zip_key
        db.add(archive)
        db.commit()

    # Publicar de novo para refrescar UI com download_ready=True
    from .admin_updates import notify_admin_data_changed, notify_web_check_data_changed
    notify_admin_data_changed("accident_closed", metadata={"accident_id": accident_id, "archive_ready": True})


def _read_video_bytes(object_key: str) -> bytes:
    from .object_storage import _use_remote, _local_root
    if _use_remote():
        import boto3
        client = boto3.client(...)  # mesmas credenciais
        result = client.get_object(Bucket=settings.do_spaces_bucket, Key=object_key)
        return result["Body"].read()
    target = _local_root() / object_key
    return target.read_bytes() if target.exists() else b""
```

**Critérios de aceitação.**
- ZIP gerado contém `<NNNN>.xlsx` na raiz.
- ZIP contém `Registros/` com arquivos por usuário.
- XLSX abre via openpyxl com header correto.
- Coluna `Registros` tem paths relativos `Registros/<filename>`.
- `accident.archive_object_key` atualizado no banco.
- `AccidentArchive` criado.
- Broker republicado `accident_closed` com `archive_ready=True`.

**Testes obrigatórios** (criar `tests/services/test_accident_archive_builder.py`):
- `test_archive_zip_contains_xlsx`
- `test_archive_zip_contains_videos_subfolder`
- `test_xlsx_columns_match_spec`
- `test_xlsx_handles_zero_videos`
- `test_xlsx_filename_uses_4_digit_format`
- `test_archive_record_persists`
- `test_archive_publishes_ready_event`

---

### [ ] Task F3 — Substituir o stub de `build_and_attach_archive_for_accident` no `close_admin_accident`

**Contexto.** A Task D3 criou um stub para `build_and_attach_archive_for_accident`. Agora Task F2 forneceu a implementação real. Garantir o import no router admin.

**Arquivos.**
- Editar: [sistema/app/routers/admin.py](../sistema/app/routers/admin.py)

**Especificação.**
- Substituir o stub por:
```python
from ..services.accident_archive_builder import build_and_attach_archive_for_accident
```
- Remover o stub local.

**Testes obrigatórios:**
- `test_close_admin_accident_calls_real_archive_builder` (integração — POST `/close`, esperar até `AccidentArchive` ser criado num pytest com `BackgroundTasks` em modo síncrono).

---

## Bloco G — E-mail SMTP

### [ ] Task G1 — Configuração SMTP em `config.py`

**Contexto.** Phase 6.1.

**Arquivos.**
- Editar: [sistema/app/core/config.py](../sistema/app/core/config.py)

**Especificação.** Adicionar 11 settings SMTP listadas na Phase 6.1 do plano. Defaults `None`/seguros.

**Critérios de aceitação.**
- `from sistema.app.core.config import settings; settings.smtp_host` é `None` por default.
- `.env` com `SMTP_HOST=smtp.example.com` é lido corretamente.

**Testes obrigatórios** (criar `tests/core/test_smtp_settings.py`):
- `test_smtp_defaults_to_disabled`
- `test_smtp_env_overrides`

---

### [ ] Task G2 — Template e renderização do e-mail "PEDIDO DE SOCORRO"

**Contexto.** Phase 6.2. Texto exato do descritivo item 5.2 Ação 3.

**Arquivos.**
- Criar: [sistema/app/services/email_templates.py](../sistema/app/services/email_templates.py)

**Especificação.**
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
    body = (
        f"Prezado {recipient_name},\n\n"
        f"O usuário {requester_name}, chave {requester_chave}, pede AJUDA IMEDIATA, "
        f"ao reportar um acidente ocorrido no projeto {project_name}, local {location_name}.\n\n"
        "Esta mensagem foi disparada após o pedido de ajuda ter sido CONFIRMADO.\n\n"
        "Atenciosamente,\n"
        "Checking App\n"
    )
    return subject, body
```

**Critérios de aceitação.**
- Texto bate **exatamente** com o descritivo.
- `subject == "(CHECKING) PEDIDO DE SOCORRO"`.

**Testes obrigatórios** (criar `tests/services/test_email_templates.py`):
- `test_subject_matches_spec`
- `test_body_includes_recipient_name`
- `test_body_includes_project_and_location`
- `test_body_confirms_help`

---

### [ ] Task G3 — Service `email_sender.py` — fila + envio com retry

**Contexto.** Phase 6.3, 6.4, 6.5.

**Arquivos.**
- Criar: [sistema/app/services/email_sender.py](../sistema/app/services/email_sender.py)

**Especificação.**
```python
import smtplib
import ssl
from email.message import EmailMessage

from ..core.config import settings
from ..database import SessionLocal
from ..models import Accident, EmailDeliveryLog, User, UserProjectMembership, Project
from .email_templates import render_help_request_email
from .time_utils import now_sgt


def queue_help_request_emails(*, accident_id: int, requester_user_id: int) -> None:
    """Enfileira (persiste em EmailDeliveryLog) e dispara entrega imediata."""
    with SessionLocal() as db:
        accident = db.get(Accident, accident_id)
        requester = db.get(User, requester_user_id)
        if accident is None or requester is None:
            return

        recipients = db.execute(
            select(User)
            .join(UserProjectMembership, UserProjectMembership.user_id == User.id)
            .join(Project, Project.id == UserProjectMembership.project_id)
            .where(Project.name == accident.project_name_snapshot)
        ).scalars().unique().all()

        log_ids = []
        for recipient in recipients:
            subject, body = render_help_request_email(
                recipient_name=recipient.nome,
                requester_name=requester.nome,
                requester_chave=requester.chave,
                project_name=accident.project_name_snapshot,
                location_name=accident.location_name_snapshot,
            )
            if not recipient.email:
                # Log sem e-mail, mas registrar para auditoria
                log = EmailDeliveryLog(
                    accident_id=accident.id,
                    triggered_by_user_id=requester.id,
                    recipient_email="",
                    recipient_chave=recipient.chave,
                    subject=subject,
                    body_snapshot=body,
                    delivery_status="failed",
                    error_message="Missing recipient email",
                    queued_at=now_sgt(),
                )
                db.add(log)
                continue
            log = EmailDeliveryLog(
                accident_id=accident.id,
                triggered_by_user_id=requester.id,
                recipient_email=recipient.email,
                recipient_chave=recipient.chave,
                subject=subject,
                body_snapshot=body,
                delivery_status="queued",
                queued_at=now_sgt(),
            )
            db.add(log)
            db.flush()
            log_ids.append(log.id)
        db.commit()

    deliver_pending_emails(log_ids)


def deliver_pending_emails(log_ids: list[int]) -> None:
    if not settings.smtp_host:
        # SMTP disabled — keep queued
        return
    with SessionLocal() as db:
        for log_id in log_ids:
            log = db.get(EmailDeliveryLog, log_id)
            if log is None or log.delivery_status != "queued":
                continue
            for attempt in range(settings.smtp_max_retries):
                try:
                    _send_via_smtp(log)
                    log.delivery_status = "sent"
                    log.sent_at = now_sgt()
                    break
                except Exception as exc:
                    log.retry_count = attempt + 1
                    log.error_message = str(exc)[:1000]
                    if attempt == settings.smtp_max_retries - 1:
                        log.delivery_status = "failed"
            db.commit()


def _send_via_smtp(log: EmailDeliveryLog) -> None:
    msg = EmailMessage()
    msg["Subject"] = log.subject
    msg["From"] = f"{settings.smtp_sender_name} <{settings.smtp_sender_email}>"
    msg["To"] = log.recipient_email
    msg.set_content(log.body_snapshot)

    if settings.smtp_use_ssl:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_send_timeout_seconds, context=ctx) as server:
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_send_timeout_seconds) as server:
            if settings.smtp_use_tls:
                server.starttls(context=ssl.create_default_context())
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
```

**Critérios de aceitação.**
- `queue_help_request_emails` enfileira 1 log por destinatário com e-mail.
- Sem e-mail: log com status `failed` + `"Missing recipient email"`.
- SMTP desabilitado: logs ficam `queued`.
- SMTP ok: logs viram `sent`.
- Falha SMTP: retry até `smtp_max_retries`, depois `failed`.

**Testes obrigatórios** (criar `tests/services/test_email_help_request.py`):
- `test_queue_creates_log_per_recipient`
- `test_queue_logs_missing_email_as_failed`
- `test_queue_idempotent_by_status_transition` (somente chamada quando há transição non-help → help, garantido pelo upstream)
- `test_send_smtp_disabled_keeps_queued` (usar `monkeypatch` de `settings.smtp_host=None`)
- `test_send_smtp_success_marks_sent` (usar mock `smtplib.SMTP`)
- `test_send_smtp_failure_retries_and_fails` (mock `SMTP.send_message` para `raise`)
- `test_send_uses_ssl_when_configured`
- `test_send_uses_starttls_when_configured`

---

## Bloco H — Frontend Admin

### [ ] Task H1 — Header redesenhado + botão "Reportar Acidente"

**Contexto.** Phase 8.1. O header atual ([sistema/app/static/admin/index.html:14-35](../sistema/app/static/admin/index.html#L14-L35)) tem `header-brand` à esquerda e `sessionBar` à direita. Precisa virar grid de 3 colunas com o botão centralizado.

**Arquivos.**
- Editar: [sistema/app/static/admin/index.html](../sistema/app/static/admin/index.html)
- Editar: [sistema/app/static/admin/styles.css](../sistema/app/static/admin/styles.css)

**Especificação.**

1. HTML — substituir o `<header>` por:
```html
<header class="app-header">
  <div class="header-brand" role="img" aria-label="Checking">
    <!-- (svg + texto preservados) -->
  </div>
  <button
    id="accidentToggleButton"
    type="button"
    class="accident-button accident-button-off hidden"
    aria-pressed="false"
    aria-label="Reportar Acidente"
  >
    <span class="accident-button-label">Reportar Acidente</span>
  </button>
  <div id="sessionBar" class="session-bar hidden">
    <span id="sessionUserLabel" class="session-user-label"></span>
    <button id="logoutButton" type="button" class="secondary-button">Sair</button>
  </div>
</header>
```
- `class="hidden"` inicial — só aparece quando o usuário está autenticado (após login bem-sucedido).

2. CSS — `styles.css`:
```css
.app-header {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  /* manter cores existentes do header */
}
.app-header .session-bar { justify-self: end; }

.accident-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 84px;
  height: 84px;
  border-radius: 50%;
  background: #c8222a;
  color: #fff;
  border: 3px solid #000;
  font-weight: 700;
  font-size: 0.95rem;
  text-align: center;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.1s;
  line-height: 1.1;
  padding: 0 8px;
}
.accident-button-label { display: block; }
.accident-button:hover { transform: scale(1.03); }
.accident-button[aria-pressed="true"] {
  border-color: #ff4d57;
  box-shadow: 0 0 0 3px #ff4d57, 0 0 18px #ff4d57;
  transform: scale(0.97);
}
@media (max-width: 700px) {
  .accident-button { width: 64px; height: 64px; font-size: 0.8rem; border-width: 2px; }
}
.accident-button.hidden { display: none; }
```

3. Garantir que o login flow desbloqueia o botão (mostra) após `loginSuccess()`. Localizar em [sistema/app/static/admin/app.js](../sistema/app/static/admin/app.js) onde `sessionBar.classList.remove("hidden")` e fazer o mesmo para `#accidentToggleButton`.

**Critérios de aceitação.**
- Botão visível e centralizado horizontalmente após login.
- Botão escondido na tela de login.
- Bordas mudam ao alternar `aria-pressed`.
- Acessível: `aria-label`, `aria-pressed`.

**Testes obrigatórios** (manual no navegador):
- Login → botão visível.
- Logout → botão escondido.
- DOM inspect mostra `aria-pressed` mudando ao clicar (ainda sem handler até Task H6).

---

### [ ] Task H2 — Modais do wizard de abertura (admin)

**Contexto.** Phase 8.2. Três modais sequenciais: Selecione Projeto → Local → Confirmação.

**Arquivos.**
- Editar: [sistema/app/static/admin/index.html](../sistema/app/static/admin/index.html)
- Editar: [sistema/app/static/admin/styles.css](../sistema/app/static/admin/styles.css)

**Especificação.**

1. Adicionar os 3 modais imediatamente após `#eventArchivesModal` (linha ~668):
```html
<div id="accidentWizardProjectModal" class="modal-backdrop hidden" aria-hidden="true">
  <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="accidentWizardProjectTitle">
    <div class="section-header modal-header"><h2 id="accidentWizardProjectTitle">Selecione o Projeto</h2></div>
    <div id="accidentWizardProjectOptions" class="accident-wizard-options"></div>
    <p id="accidentWizardProjectError" class="auth-status"></p>
    <div class="modal-footer">
      <button id="accidentWizardProjectCancel" type="button" class="secondary-button">Cancelar</button>
      <button id="accidentWizardProjectAdvance" type="button" disabled>Avançar</button>
    </div>
  </div>
</div>

<div id="accidentWizardLocationModal" class="modal-backdrop hidden" aria-hidden="true">
  <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="accidentWizardLocationTitle">
    <div class="section-header modal-header"><h2 id="accidentWizardLocationTitle">Local do Acidente</h2></div>
    <div id="accidentWizardLocationOptions" class="accident-wizard-options"></div>
    <label class="accident-wizard-custom">
      <input type="radio" name="accidentLocationChoice" value="__custom__" />
      <span>Outro local:</span>
      <input id="accidentWizardCustomLocation" type="text" maxlength="120" placeholder="Descreva o local" disabled />
    </label>
    <p id="accidentWizardLocationError" class="auth-status"></p>
    <div class="modal-footer">
      <button id="accidentWizardLocationCancel" type="button" class="secondary-button">Cancelar</button>
      <button id="accidentWizardLocationAdvance" type="button" disabled>Avançar</button>
    </div>
  </div>
</div>

<div id="accidentWizardConfirmModal" class="modal-backdrop hidden" aria-hidden="true">
  <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="accidentWizardConfirmTitle">
    <div class="section-header modal-header"><h2 id="accidentWizardConfirmTitle">Confirmação de Acidente</h2></div>
    <p id="accidentWizardConfirmText" class="accident-wizard-confirm-text"></p>
    <p>Você confirma esta ação?</p>
    <p id="accidentWizardConfirmError" class="auth-status"></p>
    <div class="modal-footer">
      <button id="accidentWizardConfirmCancel" type="button" class="secondary-button">Cancelar</button>
      <button id="accidentWizardConfirmSubmit" type="button">Confirmar</button>
    </div>
  </div>
</div>
```

2. CSS:
```css
.accident-wizard-options { display: flex; flex-direction: column; gap: 6px; max-height: 320px; overflow-y: auto; }
.accident-wizard-options label { display: flex; align-items: center; gap: 8px; padding: 8px; border-radius: 8px; cursor: pointer; }
.accident-wizard-options label:hover { background: rgba(0,0,0,0.04); }
.accident-wizard-custom { display: flex; align-items: center; gap: 8px; padding-top: 12px; }
.accident-wizard-custom input[type="text"] { flex: 1; }
.accident-wizard-confirm-text { font-weight: 600; }
```

3. **Sem JS por enquanto** — a lógica vem na Task H6. Por ora apenas a estrutura.

**Critérios de aceitação.**
- Modais existem no DOM, estão `hidden` por padrão.
- Estrutura corresponde à Phase 8.2 do plano.

---

### [ ] Task H3 — Tema "Modo Acidente" (CSS admin)

**Contexto.** Phase 8.3. Aplicar tema vermelho via classe na raiz `<html>`.

**Arquivos.**
- Editar: [sistema/app/static/admin/styles.css](../sistema/app/static/admin/styles.css)

**Especificação.**
1. No início do `:root`, identificar as variáveis de cor primária (verde) atualmente em uso. Se não houver, definir agora:
   ```css
   :root {
     --primary: #2d8c4a; /* exemplo — ajustar para a cor verde atual */
     --primary-hover: #1f7038;
     --accent-bg-soft: #e6f6ec;
     --danger: #c8222a;
   }
   ```
2. Sobrescrita no modo acidente:
   ```css
   :root.accident-mode {
     --primary: #c8222a;
     --primary-hover: #8c1a20;
     --accent-bg-soft: #fde7e9;
   }
   :root.accident-mode .app-header { background: #c8222a; }
   :root.accident-mode .tabs { border-bottom-color: #c8222a; }
   :root.accident-mode .tabs button.active { color: #c8222a; border-bottom-color: #c8222a; }
   ```
3. Refatorar regras que usam hardcoded de verde para usar `var(--primary)` quando descobertas. Isso pode exigir um sweep no styles.css; identificar pelo grep de cores hex verdes.

**Critérios de aceitação.**
- `document.documentElement.classList.add('accident-mode')` muda o header para vermelho e botões primários para vermelho.
- Remover a classe restaura ao verde original sem refresh.

**Testes manuais (no navegador):**
- Console: `document.documentElement.classList.add('accident-mode')` → tema vira vermelho.
- `document.documentElement.classList.remove('accident-mode')` → volta verde.

---

### [ ] Task H4 — Aba "Acidente" + tabela "Situação de Pessoal"

**Contexto.** Phase 8.4. Aba antes de "Check-In", aparece somente em modo acidente.

**Arquivos.**
- Editar: [sistema/app/static/admin/index.html](../sistema/app/static/admin/index.html)
- Editar: [sistema/app/static/admin/styles.css](../sistema/app/static/admin/styles.css)

**Especificação.**

1. HTML — adicionar **antes** do botão de Check-In na `<nav class="tabs">` (linha ~117):
```html
<button data-tab="acidente" id="accidentTabButton" class="tab-accident hidden">Acidente</button>
```

2. Adicionar a section correspondente, **antes** de `#tab-checkin` (linha ~128):
```html
<section id="tab-acidente" class="tab">
  <div class="section-header">
    <div class="section-title-block">
      <h2 id="accidentSectionTitle">Acidente em curso</h2>
      <p id="accidentSectionMeta" class="section-header-copy"></p>
    </div>
    <div class="section-header-actions">
      <span id="accidentSectionCount" class="auth-status">0 registros</span>
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

3. CSS:
```css
.tab-accident { color: #fff; background: #c8222a; border-color: #ff4d57; box-shadow: 0 0 6px #ff4d57; }
.tab-accident.active { background: #b7141c; }

.situacao-pessoal-table td { vertical-align: top; }
.situacao-pessoal-table .registros-cell { max-height: 140px; overflow-y: auto; }
.situacao-pessoal-table .registros-cell a { display: block; }

.situacao-row-white { background: #fff; }
.situacao-row-light-green { background: rgba(160,230,160,0.4); }
.situacao-row-turquoise { background: rgba(120,220,220,0.4); }
.situacao-row-yellow { background: rgba(255,234,120,0.45); }
.situacao-row-blinking-red {
  background: rgba(255,80,90,0.18);
  animation: situacao-blink 1s steps(2, end) infinite;
}
.situacao-row-light-gray { background: rgba(0,0,0,0.06); color: #555; }
@keyframes situacao-blink {
  0%, 100% { background: rgba(255,80,90,0.18); }
  50% { background: rgba(255,80,90,0.45); }
}
```

**Critérios de aceitação.**
- Aba existe no DOM, `hidden` por default.
- CSS aplicado com cores corretas.
- Animação `blink` funcional via DevTools (forçar classe).

---

### [ ] Task H5 — Modal de encerramento + tabela "Acidentes" no Cadastro

**Contexto.** Phase 8.5 + 8.6.

**Arquivos.**
- Editar: [sistema/app/static/admin/index.html](../sistema/app/static/admin/index.html)
- Editar: [sistema/app/static/admin/styles.css](../sistema/app/static/admin/styles.css)

**Especificação.**

1. Modal de encerramento, junto dos demais modais (após `#accidentWizardConfirmModal`):
```html
<div id="accidentEndModal" class="modal-backdrop hidden" aria-hidden="true">
  <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="accidentEndTitle">
    <div class="section-header modal-header"><h2 id="accidentEndTitle">Encerramento do Modo Acidente</h2></div>
    <p>Tem certeza que deseja finalizar o 'Modo Acidente'?</p>
    <p id="accidentEndError" class="auth-status"></p>
    <div class="modal-footer">
      <button id="accidentEndBack" type="button" class="secondary-button">Voltar</button>
      <button id="accidentEndConfirm" type="button">Confirmar</button>
    </div>
  </div>
</div>
```

2. Tabela "Acidentes" — adicionar em `tab-cadastro` **imediatamente após** `cadastro-section-panel--pending` (após linha ~388):
```html
<article class="cadastro-section-panel cadastro-section-panel--accidents" data-cadastro-section="acidentes">
  <div class="section-header">
    <h2>Acidentes</h2>
    <button id="refreshAccidentsButton" type="button" class="secondary-button">Atualizar</button>
  </div>
  <div class="table-wrap cadastro-grid-wrap">
    <table class="responsive-table cadastro-table cadastro-accidents-table">
      <thead>
        <tr>
          <th>Número</th>
          <th>Projeto</th>
          <th>Autor</th>
          <th>Aberto em</th>
          <th>Encerrado em</th>
          <th>Download</th>
          <th>Ações</th>
        </tr>
      </thead>
      <tbody id="accidentsBody"></tbody>
    </table>
  </div>
</article>
```

3. CSS:
```css
.cadastro-accidents-table .download-pending { color: #888; font-style: italic; }
.cadastro-accidents-table .delete-button { background: #c8222a; color: #fff; }
```

**Critérios de aceitação.**
- Modal de encerramento existe e está `hidden`.
- Tabela "Acidentes" aparece logo após "Pendências".

---

### [ ] Task H6 — JS admin: estado, fetch, render, SSE, wiring de botões

**Contexto.** Phase 8.1 (wiring) + 8.2 (wizard) + 8.4 (render) + 8.5 (encerramento) + 8.6 (acidentes) + 8.2.1/8.2.2 (reativo + polling fallback). Esta é a maior tarefa frontend admin.

**Arquivos.**
- Editar: [sistema/app/static/admin/app.js](../sistema/app/static/admin/app.js)

**Especificação.**

1. Adicionar bloco de estado e helpers próximo ao topo do arquivo (após outras `let` globals):
```js
let accidentState = { isActive: false, accident: null, situationRows: [] };
let accidentWizardData = { projectId: null, projectName: null, locationId: null, locationName: null, locationRegistered: null };
let accidentRefreshDebounceTimer = null;
let accidentPollingHandle = null;
const ACCIDENT_POLL_INTERVAL_MS = 30000;
```

2. Função `fetchAccidentState()`:
```js
async function fetchAccidentState() {
  try {
    const response = await fetch("/api/admin/accidents/active", { credentials: "include" });
    if (!response.ok) return;
    accidentState = await response.json();
    applyAccidentTheme(accidentState.isActive);
    renderAccidentTab(accidentState);
    updateAccidentButton(accidentState);
  } catch (err) {
    console.warn("fetchAccidentState failed", err);
  }
}

function applyAccidentTheme(isActive) {
  document.documentElement.classList.toggle("accident-mode", !!isActive);
}

function updateAccidentButton(state) {
  const btn = document.getElementById("accidentToggleButton");
  if (!btn) return;
  btn.classList.remove("hidden");
  btn.setAttribute("aria-pressed", state.isActive ? "true" : "false");
  btn.querySelector(".accident-button-label").textContent = state.isActive ? "Acidente Reportado" : "Reportar Acidente";
}

function renderAccidentTab(state) {
  const tabBtn = document.getElementById("accidentTabButton");
  const tabSection = document.getElementById("tab-acidente");
  if (state.isActive) {
    tabBtn.classList.remove("hidden");
    document.getElementById("accidentSectionTitle").textContent = `Acidente ${state.accident.accident_number_label}`;
    document.getElementById("accidentSectionMeta").textContent =
      `Projeto ${state.accident.project_name} — Local ${state.accident.location_name} — Aberto por ${state.accident.opened_by_label} em ${new Date(state.accident.opened_at).toLocaleString()}`;
    renderSituacaoPessoal(state.situationRows);
  } else {
    tabBtn.classList.add("hidden");
    if (tabBtn.classList.contains("active")) {
      switchTab("checkin");
    }
  }
}

function renderSituacaoPessoal(rows) {
  const tbody = document.getElementById("situacaoPessoalBody");
  tbody.innerHTML = "";
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.className = `situacao-row situacao-row-${row.row_color}`;
    tr.appendChild(td(formatDateTime(row.event_time)));
    tr.appendChild(td(row.name));
    tr.appendChild(td(row.chave));
    tr.appendChild(td(row.projects.join(", ")));
    tr.appendChild(td(row.local || ""));
    tr.appendChild(td(row.zone));
    tr.appendChild(td(row.status));
    tr.appendChild(td(row.phone || ""));
    tr.appendChild(tdVideos(row.videos));
    tbody.appendChild(tr);
  });
  document.getElementById("accidentSectionCount").textContent = `${rows.length} registros`;
}

function td(text) { const c = document.createElement("td"); c.textContent = text; return c; }
function tdVideos(videos) {
  const c = document.createElement("td");
  if (!videos.length) { c.textContent = ""; return c; }
  const wrapper = document.createElement("div");
  wrapper.className = "registros-cell";
  videos.forEach((v) => {
    const a = document.createElement("a");
    a.href = v.public_url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = `Vídeo ${formatDateTime(v.captured_at)}`;
    wrapper.appendChild(a);
  });
  c.appendChild(wrapper);
  return c;
}
```

3. Wizard JS:
```js
async function openAccidentWizard() {
  // Modal 1: projetos
  const projects = await (await fetch("/api/admin/accidents/wizard/projects")).json();
  renderProjectRadios(projects);
  show("accidentWizardProjectModal");
}
function renderProjectRadios(projects) {
  const container = document.getElementById("accidentWizardProjectOptions");
  container.innerHTML = "";
  projects.forEach((p) => {
    const label = document.createElement("label");
    label.innerHTML = `<input type="radio" name="accidentProjectChoice" value="${p.id}" /> <span>${p.name}</span>`;
    container.appendChild(label);
  });
  container.querySelectorAll("input").forEach((inp) => {
    inp.addEventListener("change", () => {
      document.getElementById("accidentWizardProjectAdvance").disabled = false;
      accidentWizardData.projectId = parseInt(inp.value, 10);
      accidentWizardData.projectName = projects.find(p => p.id === accidentWizardData.projectId).name;
    });
  });
}
// Análogo para locations (Modal 2) — fetch /wizard/locations?project_id=X
// Modal 3 monta texto e POST /open
```

4. Wiring dos botões — handler do `accidentToggleButton`:
```js
document.getElementById("accidentToggleButton").addEventListener("click", () => {
  if (accidentState.isActive) {
    show("accidentEndModal");
  } else {
    openAccidentWizard();
  }
});
```

5. SSE integration — modificar `startRealtimeUpdates` (linha 5455 atual):
```js
eventStream.onmessage = (event) => {
  realtimeConnected = true;
  updateOperationalChrome();
  try {
    const data = JSON.parse(event.data);
    if (data.reason && data.reason.startsWith("accident_")) {
      scheduleAccidentRefresh();
    } else {
      requestRefreshAllTables();
    }
  } catch {
    requestRefreshAllTables();
  }
};

function scheduleAccidentRefresh() {
  if (accidentRefreshDebounceTimer !== null) clearTimeout(accidentRefreshDebounceTimer);
  accidentRefreshDebounceTimer = setTimeout(() => {
    fetchAccidentState();
    if (accidentState.isActive === false) fetchAccidentsHistory(); // refresh Cadastro
    accidentRefreshDebounceTimer = null;
  }, 250);
}

function startAccidentPolling() {
  stopAccidentPolling();
  accidentPollingHandle = setInterval(fetchAccidentState, ACCIDENT_POLL_INTERVAL_MS);
}
function stopAccidentPolling() {
  if (accidentPollingHandle) { clearInterval(accidentPollingHandle); accidentPollingHandle = null; }
}
```

6. Após login bem-sucedido, chamar `fetchAccidentState()` e `startAccidentPolling()`.

7. Modal de encerramento — handler `accidentEndConfirm` → POST `/api/admin/accidents/close` → fechar modal + `fetchAccidentState()` + `fetchAccidentsHistory()`.

8. Tabela Acidentes (Cadastro):
```js
async function fetchAccidentsHistory() {
  const response = await fetch("/api/admin/accidents");
  if (!response.ok) return;
  const { rows } = await response.json();
  renderAccidentsHistory(rows);
}
function renderAccidentsHistory(rows) {
  const tbody = document.getElementById("accidentsBody");
  tbody.innerHTML = "";
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.appendChild(td(row.accident_number_label));
    tr.appendChild(td(row.project_name));
    tr.appendChild(td(row.author_label));
    tr.appendChild(td(formatDateTime(row.opened_at)));
    tr.appendChild(td(formatDateTime(row.closed_at)));
    const dl = document.createElement("td");
    if (row.download_ready) {
      const a = document.createElement("a");
      a.href = row.download_url;
      a.textContent = "Baixar";
      dl.appendChild(a);
    } else {
      dl.innerHTML = '<span class="download-pending">Preparando...</span>';
    }
    tr.appendChild(dl);
    const actions = document.createElement("td");
    if (row.can_delete) {
      const btn = document.createElement("button");
      btn.className = "secondary-button delete-button";
      btn.textContent = "Remover";
      btn.addEventListener("click", async () => {
        if (!confirm(`Tem certeza que deseja excluir o acidente ${row.accident_number_label}?`)) return;
        await fetch(`/api/admin/accidents/${row.id}`, { method: "DELETE" });
        fetchAccidentsHistory();
      });
      actions.appendChild(btn);
    }
    tr.appendChild(actions);
    tbody.appendChild(tr);
  });
}
document.getElementById("refreshAccidentsButton").addEventListener("click", fetchAccidentsHistory);
```

9. Reactive wizard (Phase 8.2.1) — em `scheduleAccidentRefresh`, se algum modal do wizard estiver aberto e o novo estado é `isActive=true` (e o usuário não foi quem abriu), fechar todos os modais e mostrar mensagem efêmera.

**Critérios de aceitação.**
- Login mostra botão.
- Click → wizard abre.
- Wizard completo → POST → broker → outros admins recebem e atualizam.
- Tab "Acidente" aparece, mostra registros.
- Modal de encerramento funciona.
- Tabela Acidentes atualiza após encerramento.
- Polling 30s ativo.
- Aba some quando acidente encerra.

**Testes obrigatórios** (criar `tests/static/admin/test_accident_button.test.js` — usar a infra atual de testes JS do repo):
- `test_accident_button_visible_after_login`
- `test_accident_button_label_changes_on_state`
- `test_wizard_advances_after_project_selection`
- `test_wizard_advances_after_location_selection`
- `test_confirm_text_includes_project_and_location`
- `test_situacao_table_renders_rows_in_order`
- `test_accidents_table_renders_history`
- `test_delete_button_only_for_perfil_9`

---

## Bloco I — Frontend Checking Web

### [ ] Task I1 — Botão "Reportar Acidente" + CSS

**Contexto.** Phase 9.1. Botão abaixo do `#submitButton` (linha 229).

**Arquivos.**
- Editar: [sistema/app/static/check/index.html](../sistema/app/static/check/index.html)
- Editar: [sistema/app/static/check/styles.css](../sistema/app/static/check/styles.css)

**Especificação.**

1. HTML — adicionar **após** `<button id="submitButton" ...>Registrar</button>` (linha 229):
```html
<button
  id="accidentReportButton"
  type="button"
  class="accident-report-button"
  aria-pressed="false"
  hidden
>
  <span class="accident-report-button-label">Reportar Acidente</span>
</button>
```

2. CSS:
```css
.accident-report-button {
  /* mesmo tamanho/format do .submit-button */
  display: block;
  width: 100%;
  margin-top: 8px;
  padding: 14px 16px;
  background: #c8222a;
  color: #fff;
  border: 2px solid transparent;
  border-radius: 12px;
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.1s;
}
.accident-report-button[aria-pressed="true"] {
  border-color: #ff4d57;
  box-shadow: 0 0 0 3px #ff4d57, 0 0 18px #ff4d57;
  transform: scale(0.98);
}
```

3. Visibilidade controlada por JS após login: o botão fica `hidden` enquanto o usuário não está autenticado.

**Critérios de aceitação.**
- Botão aparece após login.
- Após confirmação do modo acidente, label muda para "Acidente Reportado" e bordas brilham.

---

### [ ] Task I2 — Modais do wizard de abertura (Checking Web)

**Contexto.** Phase 9.2. Quatro modais sequenciais: Projeto → Local → Sua Situação → Confirmação.

**Arquivos.**
- Editar: [sistema/app/static/check/index.html](../sistema/app/static/check/index.html)
- Editar: [sistema/app/static/check/styles.css](../sistema/app/static/check/styles.css)

**Especificação.**

1. HTML — adicionar antes do `</section>` que fecha `.check-card` (próximo da linha 598). Replicar estrutura `password-dialog`. Padrão de cada modal:
```html
<div id="accidentReportProjectBackdrop" class="password-dialog-backdrop is-hidden" hidden></div>
<section id="accidentReportProjectDialog" class="password-dialog is-hidden" role="dialog" aria-modal="true" hidden>
  <div class="password-dialog-card">
    <h2>Selecione o Projeto</h2>
    <div id="accidentReportProjectOptions" class="accident-report-options"></div>
    <p id="accidentReportProjectError" class="check-error"></p>
    <div class="password-dialog-actions">
      <button id="accidentReportProjectCancel" type="button" class="secondary-button">Cancelar</button>
      <button id="accidentReportProjectAdvance" type="button" class="submit-button" disabled>Avançar</button>
    </div>
  </div>
</section>
```
Repetir para `Location`, `Situation` e `Confirm` modais com IDs análogos.

2. CSS:
```css
.accident-report-options { display: flex; flex-direction: column; gap: 6px; max-height: 320px; overflow-y: auto; }
.accident-report-options label { display: flex; align-items: center; gap: 8px; padding: 8px; border-radius: 8px; }
```

**Critérios de aceitação.**
- 4 modais existem.
- Cada um tem botões Cancelar/Avançar (ou Cancelar/Confirmar no último).
- Modal "Sua Situação" tem 3 radios com os textos exatos do descritivo.

---

### [ ] Task I3 — Tema "Modo Acidente" (CSS Checking Web)

**Contexto.** Phase 9.3. Tema vermelho com exceção para bordas de `chave`/`senha`.

**Arquivos.**
- Editar: [sistema/app/static/check/styles.css](../sistema/app/static/check/styles.css)

**Especificação.**
```css
:root.accident-mode {
  --primary: #c8222a;
  --primary-hover: #8c1a20;
  --accent-bg-soft: #fde7e9;
}
:root.accident-mode header { background: #c8222a; }
:root.accident-mode .submit-button { background: #c8222a; }
:root.accident-mode .submit-button:hover { background: #8c1a20; }

/* Não tocar nas bordas de chave e senha (preservar regras de cor de auth status) */
:root.accident-mode #chaveInput,
:root.accident-mode #passwordInput {
  /* explicitamente preservar border-color sem override */
}
```

**Critérios de aceitação.**
- Theme switch funcional via `documentElement.classList`.
- Bordas dos campos chave/senha **não mudam** em modo acidente.

---

### [ ] Task I4 — Container "Estou em:" + widgets de confirmação por situação

**Contexto.** Phase 9.3. Substitui visualmente os containers de Last Check-In/Out durante modo acidente.

**Arquivos.**
- Editar: [sistema/app/static/check/index.html](../sistema/app/static/check/index.html)
- Editar: [sistema/app/static/check/styles.css](../sistema/app/static/check/styles.css)

**Especificação.**

1. HTML — **após** o `<section class="history-card">` (linha 58-69):
```html
<section id="accidentInquiryCard" class="history-card accident-inquiry-card is-hidden" hidden>
  <p id="accidentInquiryTitle" class="history-label">Estou em:</p>
  <div class="accident-inquiry-grid">
    <button id="accidentZoneSafetyButton" type="button" class="accident-inquiry-button">Zona de Segurança</button>
    <button id="accidentZoneAccidentButton" type="button" class="accident-inquiry-button">Zona de Acidente</button>
  </div>
</section>
```

2. Modal de confirmação (compartilhado pelas 3 situações):
```html
<div id="accidentReportConfirmBackdrop" class="password-dialog-backdrop is-hidden" hidden></div>
<section id="accidentReportConfirmDialog" class="password-dialog is-hidden" role="dialog" aria-modal="true" hidden>
  <div class="password-dialog-card">
    <h2>Confirmação</h2>
    <p id="accidentReportConfirmText"></p>
    <p id="accidentReportConfirmError" class="check-error"></p>
    <div class="password-dialog-actions">
      <button id="accidentReportConfirmCancel" type="button" class="secondary-button">Cancelar</button>
      <button id="accidentReportConfirmSubmit" type="button" class="submit-button">Confirmar</button>
    </div>
  </div>
</section>
```

3. CSS:
```css
.accident-inquiry-card { background: rgba(255,80,90,0.1); border: 2px solid #c8222a; }
.accident-inquiry-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.accident-inquiry-button {
  padding: 14px;
  background: #fff;
  border: 2px solid #c8222a;
  color: #c8222a;
  font-weight: 700;
  border-radius: 8px;
  cursor: pointer;
}
.accident-inquiry-button:hover { background: #fde7e9; }
```

**Critérios de aceitação.**
- Container existe, `hidden` por padrão.
- Modal de confirmação único reaproveitável para as 3 situações.

---

### [ ] Task I5 — Banner de notificação + botão "Permitir Audio & Video" em Ajustes

**Contexto.** Phase 9.3 (banner) + Phase 9.5 (settings).

**Arquivos.**
- Editar: [sistema/app/static/check/index.html](../sistema/app/static/check/index.html)
- Editar: [sistema/app/static/check/styles.css](../sistema/app/static/check/styles.css)

**Especificação.**

1. O banner reaproveita `#notificationLinePrimary` (linha 72-74). Apenas precisa de CSS:
```css
:root.accident-mode #notificationLinePrimary {
  color: #c8222a;
  font-weight: 700;
}
```

2. Botão "Permitir Audio & Video" — adicionar em `#settingsDialog` logo após a opção "Permitir localização" (linha 428-430):
```html
<div class="settings-option-row settings-option-row-action">
  <button id="settingsAudioVideoPermissionButton" type="button" class="secondary-button settings-option-action">Permitir Audio &amp; Video</button>
</div>
```

**Critérios de aceitação.**
- Banner fica vermelho/negrito em modo acidente.
- Botão em Ajustes existe.

---

### [ ] Task I6 — Camera capture (`accident-camera.js`)

**Contexto.** Phase 9.4. Captura de vídeo com câmera traseira + upload.

**Arquivos.**
- Criar: [sistema/app/static/check/accident-camera.js](../sistema/app/static/check/accident-camera.js)
- Editar: [sistema/app/static/check/index.html](../sistema/app/static/check/index.html) — adicionar `<script src="accident-camera.js"></script>` antes de `app.js`.

**Especificação.**
```js
(function () {
  const RecordingState = { stream: null, recorder: null, chunks: [], dialog: null };

  function getMimeType() {
    const candidates = ["video/webm;codecs=vp9,opus", "video/webm", "video/mp4"];
    for (const m of candidates) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported(m)) return m;
    }
    return "";
  }

  async function startRecording(chave) {
    try {
      RecordingState.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: true,
      });
    } catch (err) {
      alert("Sem permissão para câmera/microfone. Habilite em Ajustes → Permitir Audio & Video.");
      return false;
    }
    showRecordingDialog();
    RecordingState.chunks = [];
    const mime = getMimeType();
    try {
      RecordingState.recorder = new MediaRecorder(RecordingState.stream, mime ? { mimeType: mime } : {});
    } catch (err) {
      cleanup();
      alert("Seu dispositivo não suporta gravação de vídeo.");
      return false;
    }
    RecordingState.recorder.ondataavailable = (e) => { if (e.data && e.data.size) RecordingState.chunks.push(e.data); };
    RecordingState.recorder.onstop = () => uploadRecording(chave, mime);
    RecordingState.recorder.start();
    return true;
  }

  function stopRecording() {
    if (RecordingState.recorder && RecordingState.recorder.state !== "inactive") {
      RecordingState.recorder.stop();
    }
  }

  async function uploadRecording(chave, mime) {
    const blob = new Blob(RecordingState.chunks, { type: mime || "video/webm" });
    const fd = new FormData();
    fd.append("chave", chave);
    fd.append("idempotency_key", (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2)));
    fd.append("video", blob, `recording.${mime.includes("mp4") ? "mp4" : "webm"}`);
    try {
      const resp = await fetch("/api/web/check/accident/video", { method: "POST", body: fd, credentials: "include" });
      if (!resp.ok) throw new Error("upload failed");
      setStatus("Vídeo enviado.");
    } catch (err) {
      setStatus("Falha ao enviar vídeo: " + err.message);
    } finally {
      cleanup();
    }
  }

  function showRecordingDialog() { /* abre overlay com <video>, botão Encerrar, status */ }
  function setStatus(msg) { /* atualiza status no overlay */ }
  function cleanup() {
    if (RecordingState.stream) RecordingState.stream.getTracks().forEach(t => t.stop());
    RecordingState.stream = null; RecordingState.recorder = null; RecordingState.chunks = [];
    hideRecordingDialog();
  }
  function hideRecordingDialog() { /* fecha overlay */ }

  window.AccidentCamera = { startRecording, stopRecording };
})();
```

**Critérios de aceitação.**
- Inicia câmera traseira preferida (`facingMode: environment`).
- Botão "Encerrar" para gravação.
- Upload com `idempotency_key`.
- Libera stream após upload.
- Mensagens claras de erro (sem permissão / sem suporte).

**Testes obrigatórios** (manuais — requer browser real):
- Em Chrome desktop com webcam: gravar 5s → enviar → ver em /api/admin/accidents/active.
- Em mobile (real): câmera traseira deve ser default.
- Negar permissão → mensagem clara.

---

### [ ] Task I7 — JS principal Checking Web: wiring + SSE + polling

**Contexto.** Phase 9.6 + 9.7 + 9.7.1. Conecta tudo.

**Arquivos.**
- Editar: [sistema/app/static/check/app.js](../sistema/app/static/check/app.js)
- Criar: [sistema/app/static/check/accident.js](../sistema/app/static/check/accident.js) e referenciar via `<script>` em `index.html`.

**Especificação.**

Em `accident.js`:
```js
(function () {
  let state = { isActive: false, accident: null, currentUserReport: null };
  let eventSource = null;
  let pollingHandle = null;
  let refreshDebounce = null;

  async function refreshState() {
    const chave = getCurrentChave();
    if (!chave) return;
    const resp = await fetch(`/api/web/check/accident/state?chave=${encodeURIComponent(chave)}`, { credentials: "include" });
    if (!resp.ok) return;
    state = await resp.json();
    applyTheme(state.isActive);
    renderBanner(state);
    renderInquiryCard(state);
    updateReportButton(state);
  }

  function applyTheme(isActive) { document.documentElement.classList.toggle("accident-mode", !!isActive); }
  function renderBanner(s) {
    const line = document.getElementById("notificationLinePrimary");
    if (s.isActive) {
      line.textContent = `Acidente Reportado no projeto ${s.project_name}!`;
    } else {
      if (line.textContent.startsWith("Acidente Reportado")) line.textContent = "";
    }
  }
  function renderInquiryCard(s) {
    const card = document.getElementById("accidentInquiryCard");
    const history = document.querySelector(".history-card:not(.accident-inquiry-card)");
    if (s.isActive) {
      card.hidden = false; card.classList.remove("is-hidden");
      // Mostrar também os containers normais se já reportou (item 5.1.2: retorna ao normal com tema vermelho).
      if (s.current_user_report) history.hidden = false;
      else history.hidden = true;
    } else {
      card.hidden = true; card.classList.add("is-hidden");
      history.hidden = false;
    }
  }
  function updateReportButton(s) {
    const btn = document.getElementById("accidentReportButton");
    btn.hidden = false;
    btn.setAttribute("aria-pressed", s.isActive ? "true" : "false");
    btn.querySelector(".accident-report-button-label").textContent = s.isActive ? "Acidente Reportado" : "Reportar Acidente";
  }

  function startEventSource() {
    stopEventSource();
    const chave = getCurrentChave();
    if (!chave) return;
    eventSource = new EventSource(`/api/web/check/stream?chave=${encodeURIComponent(chave)}`);
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.reason && data.reason.startsWith("accident_")) {
          scheduleRefresh();
        }
      } catch (_) {}
    };
    eventSource.onerror = () => { /* manter aberto; polling cobre */ };
  }
  function stopEventSource() { if (eventSource) { eventSource.close(); eventSource = null; } }
  function scheduleRefresh() {
    if (refreshDebounce !== null) clearTimeout(refreshDebounce);
    refreshDebounce = setTimeout(() => { refreshDebounce = null; refreshState(); }, 250);
  }
  function startPolling() { stopPolling(); pollingHandle = setInterval(refreshState, 30000); }
  function stopPolling() { if (pollingHandle) { clearInterval(pollingHandle); pollingHandle = null; } }

  // Botão principal
  document.getElementById("accidentReportButton").addEventListener("click", () => {
    if (state.isActive) openAccidentActionsDialog();
    else openAccidentWizard();
  });

  // Botões "Estou em:" — 3 caminhos para os 3 confirms
  document.getElementById("accidentZoneSafetyButton").addEventListener("click", () => askConfirm("safety", "ok"));
  document.getElementById("accidentZoneAccidentButton").addEventListener("click", () => {
    // Trocar título + labels para a fase "Sua Situação"
    document.getElementById("accidentInquiryTitle").textContent = "Sua Situação";
    document.getElementById("accidentZoneSafetyButton").textContent = "Estou bem.";
    document.getElementById("accidentZoneSafetyButton").onclick = () => askConfirm("accident", "ok");
    document.getElementById("accidentZoneAccidentButton").textContent = "Preciso de Ajuda!";
    document.getElementById("accidentZoneAccidentButton").onclick = () => askConfirm("accident", "help");
  });

  function askConfirm(zone, status) {
    const dialog = document.getElementById("accidentReportConfirmDialog");
    const text = document.getElementById("accidentReportConfirmText");
    const textMap = {
      "safety/ok": "Você confirma que está fora de perigo?",
      "accident/ok": "Você confirma que está na zona do acidente e que está fora de perigo?",
      "accident/help": "Você confirma que está na zona do acidente e que precisa de ajuda?",
    };
    text.textContent = textMap[`${zone}/${status}`];
    showDialog(dialog);
    document.getElementById("accidentReportConfirmCancel").onclick = () => hideDialog(dialog);
    document.getElementById("accidentReportConfirmSubmit").onclick = async () => {
      hideDialog(dialog);
      await fetch("/api/web/check/accident/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ chave: getCurrentChave(), zone, status }),
      });
      refreshState();
    };
  }

  function openAccidentWizard() { /* sequência dos 4 modais (Projeto → Local → Situação → Confirmação) */ }
  function openAccidentActionsDialog() {
    // Dialog "Ações de Emergência" com Audio & Video / Reportar Novo Acidente
    // 'Audio & Video' → window.AccidentCamera.startRecording(getCurrentChave())
    // 'Reportar Novo Acidente' → disabled
  }

  // Settings → "Permitir Audio & Video"
  document.getElementById("settingsAudioVideoPermissionButton").addEventListener("click", async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      stream.getTracks().forEach(t => t.stop());
      document.getElementById("settingsAudioVideoPermissionButton").textContent = "Audio & Video permitido";
      document.getElementById("settingsAudioVideoPermissionButton").disabled = true;
    } catch {
      alert("Permissão negada.");
    }
  });

  // Bootstrap após login (chamar em app.js após login)
  window.AccidentMode = {
    onLogin: () => { refreshState(); startEventSource(); startPolling(); },
    onLogout: () => { stopEventSource(); stopPolling(); applyTheme(false); },
  };

  function getCurrentChave() { /* ler do input #chaveInput se autenticado */ }
  function showDialog(el) { el.hidden = false; el.classList.remove("is-hidden"); }
  function hideDialog(el) { el.hidden = true; el.classList.add("is-hidden"); }
})();
```

Em `app.js`, identificar o handler de login bem-sucedido e chamar `window.AccidentMode.onLogin()`. No logout, `onLogout()`.

**Critérios de aceitação.**
- Login → SSE + polling iniciam.
- Logout → SSE + polling param.
- Click no botão sem acidente → wizard.
- Click no botão com acidente → dialog Ações.
- Click em "Zona de Segurança" → confirm → POST → linha aparece no admin.
- Wizard completo → POST /open → modo acidente ativo em ambos navegadores.

**Testes obrigatórios** (criar `tests/static/check/test_accident_button.test.js`):
- `test_button_renders_after_login`
- `test_wizard_opens_when_inactive`
- `test_dialog_opens_when_active`
- `test_sse_message_triggers_refresh`
- `test_confirm_submits_report`
- `test_zone_accident_changes_button_labels`
- `test_audio_video_permission_button_in_settings`

---

### [ ] Task I8 — i18n: chaves para Modo Acidente em pt-BR

**Contexto.** Phase 9.8.

**Arquivos.**
- Editar: [sistema/app/static/check/i18n-dictionaries.js](../sistema/app/static/check/i18n-dictionaries.js)

**Especificação.**

Adicionar ao dicionário pt-BR:
```
accident.button.report = "Reportar Acidente"
accident.button.reported = "Acidente Reportado"
accident.wizard.selectProject = "Selecione o Projeto"
accident.wizard.selectLocation = "Local do Acidente"
accident.wizard.yourSituation = "Sua Situação:"
accident.wizard.confirmTitle = "Confirmação de Acidente"
accident.wizard.confirmTextTemplate = "Você está prestes a reportar um acidente na localização {location} do projeto {project}."
accident.notification.bannerTemplate = "Acidente Reportado no projeto {project}!"
accident.inquiry.title = "Estou em:"
accident.inquiry.titleAfter = "Sua Situação"
accident.inquiry.safetyZone = "Zona de Segurança"
accident.inquiry.accidentZone = "Zona de Acidente"
accident.inquiry.imOk = "Estou bem."
accident.inquiry.needHelp = "Preciso de Ajuda!"
accident.confirm.safety = "Você confirma que está fora de perigo?"
accident.confirm.accidentOk = "Você confirma que está na zona do acidente e que está fora de perigo?"
accident.confirm.help = "Você confirma que está na zona do acidente e que precisa de ajuda?"
accident.actions.title = "Ações de Emergência"
accident.actions.audioVideo = "Audio & Video"
accident.actions.reportNew = "Reportar Novo Acidente"
accident.actions.back = "Voltar"
accident.settings.permitAudioVideo = "Permitir Audio & Video"
accident.settings.permitted = "Audio & Video permitido"
```

Para outros idiomas, deixar fallback para pt-BR.

**Critérios de aceitação.**
- Chaves resolvem em pt-BR.
- Fallback funciona em outros idiomas.

---

## Bloco J — Telemetria e Logging

### [ ] Task J1 — Eventos de log para fluxo do acidente

**Contexto.** Phase 12.

**Arquivos.**
- Editar: services e routers relevantes (todos os pontos do Bloco D, E onde a operação muda estado).

**Especificação.** Em cada operação acidente-relevante adicionar:
- `open_accident` (admin/web): `log_event(db, source=origin, action="accident_open", status="done", message=..., details=...)` com `chave` do autor.
- `close_accident`: `action="accident_close"`.
- `upsert_user_safety_report`: `action="accident_user_report"`.
- `attach_video_upload`: `action="accident_video_upload"`.
- `delete_accident_endpoint`: já adicionado na Task D5.
- `deliver_pending_emails`: `action="accident_email_help"` resumindo `recipient_count`/`sent_count`/`failed_count`.

**Critérios de aceitação.**
- Aba "Eventos" do admin mostra todos os passos do ciclo.

**Testes:** verificar em pytest que `log_event` foi chamado nos pontos relevantes (já fica coberto se tests do Bloco D fizerem queries em `check_events` após cada operação).

---

## Bloco K — Documentação

### [ ] Task K1 — Atualizar CLAUDE.md

**Contexto.** Phase 13.1.

**Arquivos.**
- Editar: [CLAUDE.md](../CLAUDE.md)

**Especificação.**
Adicionar uma seção "## Modo Acidente" com:
- Visão geral do fluxo (admin pode abrir, web pode abrir, encerramento só pelo admin).
- Tabelas envolvidas: `accidents`, `accident_user_reports`, `accident_video_uploads`, `accident_archives`, `email_delivery_logs`.
- Endpoints principais (admin e web).
- Brokers Postgres (`checking_admin_updates`, `checking_web_check_updates`).
- Dependências externas (SMTP, DO Spaces).
- Onde mexer: `accident_lifecycle.py` (estado), `accident_situation_table.py` (render), `accident_archive_builder.py` (ZIP).

**Critérios de aceitação.**
- Seção legível, sem repetir o descritivo.

---

### [ ] Task K2 — Criar docs de endpoint (um arquivo por endpoint)

**Contexto.** Phase 13.

**Arquivos.**
- Criar: `docs/endpoints/get_accidents_active.md`
- Criar: `docs/endpoints/post_accidents_open.md`
- Criar: `docs/endpoints/post_accidents_close.md`
- Criar: `docs/endpoints/get_accidents_list.md`
- Criar: `docs/endpoints/get_accident_archive.md`
- Criar: `docs/endpoints/delete_accident.md`
- Criar: `docs/endpoints/post_web_accident_open.md`
- Criar: `docs/endpoints/post_web_accident_report.md`
- Criar: `docs/endpoints/post_web_accident_video.md`
- Criar: `docs/endpoints/get_web_accident_state.md`

**Especificação.** Para cada endpoint, seguir o template de [docs/endpoints/get_checkinginfo.md](endpoints/get_checkinginfo.md) e [docs/endpoints/post_updaterecords.md](endpoints/post_updaterecords.md):
- Método + path
- Autenticação
- Request body / query params
- Response schema (com exemplo JSON)
- Códigos de erro
- Side effects (brokers, e-mails)
- Exemplo cURL

**Critérios de aceitação.**
- 10 arquivos criados.
- cURL examples funcionam contra ambiente local.

---

### [ ] Task K3 — Diagrama de arquitetura

**Contexto.** Phase 13.2.

**Arquivos.**
- Criar: `docs/descritivos/modo_acidente_arquitetura.md`

**Especificação.** Documento com:
- Diagrama ASCII mostrando: cliente → endpoint → service → DB → broker → SSE → outros clientes.
- Diagrama de estados do `Accident` (`null` → `aberto` → `encerrado` → `removido`).
- Sequência do ciclo de pedido de ajuda (`help` → e-mail).
- Mapa do nível de privilégio admin (perfil 0/1/9) por endpoint.

**Critérios de aceitação.**
- Documento auto-contido, legível em monospace.

---

## Bloco L — Testes integrados / E2E

### [ ] Task L1 — Fixtures pytest para acidente

**Contexto.** Reuso entre testes.

**Arquivos.**
- Criar: `tests/conftest_accident.py` ou estender `tests/conftest.py`.

**Especificação.**
Fixtures:
- `accident_project` — cria 1 `Project` "P-Test".
- `accident_location` — cria 1 `ManagedLocation` ligado a "P-Test".
- `user_in_project` — cria `User(perfil=0, checkin=True)` em "P-Test" com e-mail.
- `admin_perfil_1` / `admin_perfil_9` — admins com sessão pré-criada.
- `open_accident_fixture` — yield acidente aberto + fecha no teardown.
- `mock_smtp` — patch `smtplib.SMTP` para coletar mensagens.
- `mock_storage` — patch `object_storage.upload_stream` para no-op + retornar URL.

**Critérios de aceitação.**
- Imports funcionam em qualquer test_*.py do projeto.

---

### [ ] Task L2 — Teste de integração: fluxo completo admin

**Contexto.** Cobertura E2E lado backend.

**Arquivos.**
- Criar: `tests/integration/test_accident_admin_flow.py`

**Especificação.** Cenário:
1. POST `/api/admin/login` perfil 1 → cookie.
2. GET `/api/admin/accidents/active` → `is_active=False`.
3. POST `/api/admin/accidents/open` `{project_id, location_id}` → 200.
4. GET `/api/admin/accidents/active` → `is_active=True`, contagem de rows > 0.
5. Outro test client (perfil 9) → POST `/api/admin/accidents/close` → 200.
6. GET `/api/admin/accidents` → 1 row.
7. (Tempo de espera por BackgroundTask) → archive_ready=True.
8. GET `/api/admin/accidents/{id}/archive` → 307 ou conteúdo de arquivo válido.
9. Não-perfil-9 tenta DELETE → 403.
10. Perfil 9 → DELETE → 200, then GET vazio.

**Critérios de aceitação.**
- Teste passa.
- Cobre toda a sequência sem falhar.

---

### [ ] Task L3 — Teste de integração: fluxo completo Checking Web

**Contexto.** Lado web.

**Arquivos.**
- Criar: `tests/integration/test_accident_web_flow.py`

**Especificação.** Cenário:
1. POST `/api/web/auth/login` → cookie.
2. GET `/api/web/check/accident/state` → inactive.
3. POST `/api/web/check/accident/open` `{project_id, custom_location_name, zone: "accident", status: "help"}` → 200.
4. SMTP mock recebeu N mensagens com subject correto.
5. POST `/api/web/check/accident/video` (multipart) → 200.
6. Outro web client (diferente usuário) → GET `/state` → inactive=False, vê acidente.
7. POST `/api/web/check/accident/report` `{zone: "safety", status: "ok"}` → 200.
8. Admin GET `/api/admin/accidents/active` → vê os 2 usuários na situation_rows.

**Critérios de aceitação.**
- Teste passa.

---

### [ ] Task L4 — Teste de tempo real (multi-cliente)

**Contexto.** Validar que o broker entrega eventos.

**Arquivos.**
- Criar: `tests/integration/test_accident_realtime.py`

**Especificação.**
1. Abrir 2 SSE clients: 1 admin `/api/admin/stream` + 1 web `/api/web/check/stream`.
2. Esperar mensagem `connected` em cada um.
3. Disparar `notify_admin_data_changed("accident_opened")` e `notify_web_check_data_changed("accident_opened")`.
4. Cada client recebe o respectivo evento dentro de 2 segundos.

**Critérios de aceitação.**
- Teste passa.
- Asserts via `asyncio.wait_for(queue.get(), timeout=2)`.

---

### [ ] Task L5 — Teste de carga leve (50 usuários reportando)

**Contexto.** Validar que o broker não engasga.

**Arquivos.**
- Criar: `tests/integration/test_accident_load.py`

**Especificação.**
1. Criar 50 `User(checkin=True)`.
2. Abrir acidente.
3. Em paralelo (asyncio.gather), 50 POSTs `/report` com status=`ok`.
4. Verificar: todos os 50 reports persistidos; admin `/active` retorna lista completa; broker entregou ≥50 eventos.
5. Tempo total < 30s em CI.

**Critérios de aceitação.**
- Sem race conditions.
- Sem deadlock no índice parcial.

---

### [ ] Task L6 — Teste E2E manual (checklist)

**Contexto.** Phase 14 do plano.

**Arquivos.**
- Criar: `docs/descritivos/e2e_modo_acidente_checklist.md`

**Especificação.** Documento de teste manual com 10 cenários:
1. Admin abre acidente; Checking Web (outro browser) reage em <2s.
2. Usuário reporta safety; admin vê linha verde.
3. Usuário reporta help; admin vê vermelho piscante; e-mail chega.
4. Usuário grava vídeo 5s; admin vê link.
5. Terceiro usuário check-in via mobile; admin vê linha turquesa.
6. Admin encerra; tema verde retorna em ambos.
7. Admin perfil 1 vê tabela Acidentes mas sem botão Remover.
8. Admin perfil 9 remove acidente; linha some.
9. Web inicia acidente; admin vê em <2s, primeiro registro é o autor.
10. Reload da página durante acidente preserva o estado.

Cada cenário com checkboxes Pass/Fail + campo Notas.

**Critérios de aceitação.**
- Documento publicado.
- Executado **antes** do deploy em produção.

---

## Bloco M — Validação pré-deploy

### [ ] Task M1 — Checklist de critérios de aceitação

**Contexto.** Phase 15. Garantir que cada item do descritivo foi atendido.

**Arquivos.**
- Criar/atualizar: `docs/descritivos/aceitacao_modo_acidente.md` — copiar a Phase 15 do plano e marcar cada item.

**Especificação.**
- Cada item da Phase 15 vira uma linha com `[ ]` / `[x]`.
- Antes do deploy, todos devem estar `[x]`.

---

### [ ] Task M2 — Smoke test em staging

**Contexto.** Validar que deploy não quebrou nada.

**Especificação.**
1. Deploy em ambiente staging (Digital Ocean Spaces e SMTP reais).
2. Executar checklist da Task L6 inteiro.
3. Verificar `EmailDeliveryLog`: nenhum `failed` por configuração.
4. Verificar `AccidentArchive`: ZIP gerado e baixável.

**Critérios de aceitação.**
- Todos os 10 cenários passam em staging.
- Logs sem erros 500.

---

### [ ] Task M3 — Migração SQL aplicada em produção

**Contexto.** Pré-deploy obrigatório.

**Especificação.**
1. Backup completo do banco de produção.
2. Aplicar `sistema/scripts/migrate_accidents_v1.sql` via psql.
3. Verificar `\dt` mostra as 5 novas tabelas.
4. Verificar `\d accidents` mostra constraints + índice parcial.
5. Rollback plan documentado.

**Critérios de aceitação.**
- Backup confirmado.
- Migration aplicada.
- Verificação de schema completa.

---

### [ ] Task M4 — Variáveis de ambiente em produção

**Contexto.** Apêndice B do plano.

**Especificação.**
- SMTP (`SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, etc.).
- DO Spaces (`DO_SPACES_*`).
- Atualizar `.env.production` na DO.
- Restart da API.

**Critérios de aceitação.**
- `curl /api/admin/accidents/active` em produção retorna 401 (não 500).
- Logs mostram brokers iniciados, SMTP test.

---

### [ ] Task M5 — Monitoramento pós-deploy

**Contexto.** Acompanhamento da feature em produção.

**Especificação.**
- Configurar alerta para `EmailDeliveryLog.delivery_status='failed'` > 5%.
- Configurar alerta para `Accident.closed_at IS NULL` por > 24h (acidente esquecido).
- Configurar alerta para tamanho do ZIP > 200 MB (sinaliza muitos vídeos).
- Documentar em `docs/operacoes/monitoramento_modo_acidente.md`.

**Critérios de aceitação.**
- Alertas configurados.
- Documento existe.

---

## Bloco N — Tarefas finais de qualidade

### [ ] Task N1 — Code review interno

**Contexto.** Garantir qualidade antes do merge.

**Especificação.**
- Rodar `pytest -q` localmente: 100% passing.
- Rodar `pytest --cov=sistema/app --cov-report=term-missing` — cobertura ≥ 85% no código de acidente.
- Revisar diffs grandes (admin/app.js, check/app.js) com olhar humano.
- Verificar não há `console.log` ou `print` deixados no código.
- Verificar não há TODO sem owner.

**Critérios de aceitação.**
- CI verde.
- Cobertura atendida.
- Sem código morto.

---

### [ ] Task N2 — Testes em browsers reais

**Contexto.** Compatibilidade.

**Especificação.**
- Chrome desktop (Win/Mac/Linux): funcionalidade completa, incluindo gravação.
- Firefox desktop: idem.
- Safari (Mac): gravação com `video/mp4` (não webm).
- Chrome Android: câmera traseira.
- Safari iOS: gravação + upload (iOS pode ter quirks com MediaRecorder).
- Testar em conexão lenta (Network throttling "Slow 3G"): SSE + polling cobrem.

**Critérios de aceitação.**
- Tabela de compatibilidade preenchida em `docs/operacoes/compatibilidade_navegadores.md`.

---

### [ ] Task N3 — Pen test mínimo (autorização)

**Contexto.** Garantir guards.

**Especificação.**
- Tentar abrir acidente sem sessão → 401.
- Tentar abrir com perfil 0 → 403.
- Tentar deletar com perfil 1 → 403.
- Tentar acessar `/state` de outro usuário (mismatch chave/session) → 403.
- Tentar upload com chave que não é a sua → 403.
- Tentar SQL injection em `custom_location_name` → sanitizado.

**Critérios de aceitação.**
- Todos os guards funcionam.
- Sem leak de informação em mensagens de erro.

---

### [ ] Task N4 — Documentação final no descritivo principal

**Contexto.** Marcar a feature como "implementada".

**Arquivos.**
- Editar: [docs/descritivos/funcionamento_botao_acidente_reportado.txt](descritivos/funcionamento_botao_acidente_reportado.txt)

**Especificação.**
Adicionar no fim:
```
---

Status de implementação: IMPLEMENTADO em <data>.
Plano de arquitetura: docs/temp000.md
To-do de execução: docs/temp000A.md
Checklist de aceitação: docs/descritivos/aceitacao_modo_acidente.md
Arquitetura detalhada: docs/descritivos/modo_acidente_arquitetura.md
```

**Critérios de aceitação.**
- Linha adicionada.

---

## Sequenciamento sugerido das tarefas

| Sprint | Bloco | Tarefas |
|---|---|---|
| 1 | A + B | A1, A2, A3, B1, B2 |
| 2 | C | C1, C2, C3, C4, C5 |
| 3 | D + E | D1–D6, E1–E4 |
| 4 | F + G | F1, F2, F3, G1, G2, G3 |
| 5 | H | H1–H6 |
| 6 | I | I1–I8 |
| 7 | J + K | J1, K1, K2, K3 |
| 8 | L | L1–L6 |
| 9 | M + N | M1–M5, N1–N4 |

Total: **9 sprints estimadas** (1 sprint = ~3-5 dias de trabalho).

---

## Como utilizar este documento

1. Antes de iniciar cada tarefa, leia a **Phase correspondente do plano** [docs/temp000.md](temp000.md).
2. Leia também os **trechos do descritivo** [docs/descritivos/funcionamento_botao_acidente_reportado.txt](descritivos/funcionamento_botao_acidente_reportado.txt) que a tarefa cita.
3. Implemente o código.
4. Rode os testes obrigatórios listados na tarefa.
5. Rode `pytest -q` para garantir que nada quebrou.
6. Marque a tarefa como `[x]` aqui.
7. Faça commit com mensagem `feat(accident): Task <ID> — <título>`.

**Regra fundamental:** Não passe para a próxima tarefa enquanto a anterior não estiver com seus testes `[x]` e `pytest -q` 100% verde.
