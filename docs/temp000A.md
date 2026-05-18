# Task A1 — Resumo detalhado da implementação concluída

A implementação do **Bloco A / Task A1** foi concluída com foco na fundação do backend do Modo Acidente em SQLAlchemy, cobrindo modelos, constraints, índices e testes de persistência/validação.

## 1) Modelos SQLAlchemy adicionados

Arquivo modificado: `sistema/app/models.py`

Foram adicionadas, ao final do arquivo (após `EndpointApiKey`), as cinco entidades solicitadas:

1. `Accident` (`accidents`)
2. `AccidentUserReport` (`accident_user_reports`)
3. `AccidentVideoUpload` (`accident_video_uploads`)
4. `AccidentArchive` (`accident_archives`)
5. `EmailDeliveryLog` (`email_delivery_logs`)

Também foram mantidos campos de snapshot/JSON serializado em `Text` (sem migração para `JSON`), em linha com o padrão já usado no projeto.

## 2) Constraints e regras de integridade implementadas

Arquivo modificado: `sistema/app/models.py`

Foram implementadas as constraints obrigatórias com os nomes especificados:

- `ck_accidents_origin_allowed`
- `ck_accidents_number_non_negative`
- `ck_accident_user_reports_zone_allowed`
- `ck_accident_user_reports_status_allowed`
- `ck_email_delivery_logs_status_allowed`

Além disso:

- `Accident` recebeu `UniqueConstraint` para `accident_number`.
- `AccidentUserReport` recebeu `UniqueConstraint` para `(accident_id, user_id)`.
- `AccidentVideoUpload` recebeu `UniqueConstraint` para `idempotency_key`.
- `AccidentArchive` recebeu `UniqueConstraint` para `accident_id`.
- `Accident` recebeu check adicional para garantir ator de abertura válido (`opened_by_admin_id` XOR `opened_by_user_id`), reforçando a regra “um deles preenchido”.

## 3) Índices implementados

Arquivo modificado: `sistema/app/models.py`

Foram adicionados os índices solicitados:

- `ix_accidents_single_active` (índice parcial único conforme especificação enviada)
- `ix_accident_video_uploads_accident_user` (`accident_id`, `user_id`)
- `ix_email_delivery_logs_accident` (`accident_id`)

Também foi adicionado um índice parcial único complementar:

- `ix_accidents_single_active_guard`

Esse índice complementar existe para garantir efetivamente, em SQLite/Postgres, a unicidade de acidente ativo (`closed_at IS NULL`) no nível de banco, já que a unicidade somente em coluna anulável não bloqueia múltiplos `NULL` em alguns cenários.

## 4) Testes obrigatórios criados

Arquivo criado: `tests/models/test_accident_models.py`

Foram implementados os 9 testes solicitados:

1. `test_accident_columns_match_spec`
2. `test_accident_origin_constraint`
3. `test_accident_number_non_negative_constraint`
4. `test_single_active_accident_partial_index`
5. `test_accident_user_report_zone_status_constraints`
6. `test_accident_user_report_unique_per_user_per_accident`
7. `test_accident_video_upload_idempotency_key_unique`
8. `test_accident_archive_unique_per_accident`
9. `test_email_delivery_log_status_constraint`

Os testes usam SQLite local por arquivo temporário e validam `flush()`/`IntegrityError` nas violações de constraints e unicidade.

## 5) Verificações executadas

1. Import direto dos modelos:
   - comando: `python -c "from sistema.app.models import Accident, AccidentUserReport, AccidentVideoUpload, AccidentArchive, EmailDeliveryLog"`
   - resultado: OK

2. Criação de schema via `Base.metadata.create_all(engine)` em SQLite:
   - verificada presença das 5 tabelas novas e do índice parcial `ix_accidents_single_active`
   - resultado: OK

3. Testes do novo módulo:
   - comando: `python -m pytest -q tests\models\test_accident_models.py`
   - resultado: **9 passed**

## 6) Arquivos alterados nesta tarefa

- `sistema/app/models.py` (edição)
- `tests/models/test_accident_models.py` (novo)
- `docs/temp000A.md` (novo, contendo este resumo)

---

# Task A2 — Resumo detalhado da implementação concluída

A implementação do **Bloco A / Task A2** foi concluída adicionando os schemas Pydantic para os fluxos do Modo Acidente ao arquivo `sistema/app/schemas.py`.

## 1) Seção adicionada

Arquivo modificado: `sistema/app/schemas.py`

Foi adicionada ao **final** do arquivo a seção `# ---- Modo Acidente ----`, com os seguintes schemas (linhas 4293–4430 aproximadamente):

| Schema | Tipo | Descrição |
|---|---|---|
| `AccidentProjectOption` | Response | Opção de projeto para seleção no wizard |
| `AccidentLocationOption` | Response | Opção de local, com flag `registered` |
| `AccidentVideoLink` | Response | Link de vídeo anexado ao relatório |
| `SituacaoPessoalRow` | Response | Linha da tabela "Situação de Pessoal" no admin |
| `AccidentSummary` | Response | Resumo de um acidente (usado em lista e estado ativo) |
| `AdminAccidentStateResponse` | Response | Estado completo para o painel admin |
| `AdminAccidentOpenRequest` | Request | Admin abrindo acidente (projeto + local) |
| `WebAccidentUserReport` | Response/Embedded | Relatório do usuário (zone/status/reported_at) |
| `WebAccidentStateResponse` | Response | Estado do acidente para o usuário web |
| `WebAccidentOpenRequest` | Request | Usuário web abrindo acidente via wizard |
| `WebAccidentReportRequest` | Request | Usuário web atualizando zone/status |
| `AccidentVideoUploadResponse` | Response | Confirmação de upload de vídeo |
| `AccidentClosedRow` | Response | Linha de acidente encerrado (tabela Cadastro) |
| `AccidentClosedListResponse` | Response | Lista paginada de acidentes encerrados |

## 2) Validadores implementados

- **`AdminAccidentOpenRequest.check_location_xor`** (`@model_validator(mode="after")`):
  - Rejeita se `location_id` e `custom_location_name` forem ambos fornecidos.
  - Rejeita se nenhum dos dois for fornecido.

- **`WebAccidentOpenRequest.normalize_chave`** (`@field_validator("chave", mode="before")`):
  - Converte a chave para uppercase e valida que tem exatamente 4 caracteres alfanuméricos (`[A-Z0-9]{4}`).

- **`WebAccidentOpenRequest.check_location_xor`** (`@model_validator(mode="after")`):
  - Mesma lógica XOR do `AdminAccidentOpenRequest`.

## 3) Padrão de Literals

- `SituacaoPessoalRow.zone`: `Literal["Aguardando", "Segurança", "Acidente"]` (em português — corresponde ao display no frontend).
- `SituacaoPessoalRow.status`: `Literal["Aguardando", "OK", "AJUDA"]`.
- `SituacaoPessoalRow.row_color`: `Literal["white", "blinking-red", "yellow", "turquoise", "light-green", "light-gray"]` (inclui `"light-gray"` além das 5 cores originais, para usuário em espera sem interação).
- `AccidentSummary.origin`: `Literal["admin", "web"]`.
- Campos de request web usam inglês interno: `zone: Literal["safety", "accident"]`, `status: Literal["ok", "help"]`.

## 4) Testes obrigatórios criados

Arquivo criado: `tests/schemas/test_accident_schemas.py`

Foram implementados os testes solicitados (10 no total, cobrindo todos os 5 critérios obrigatórios):

1. `test_admin_open_request_requires_location_or_custom`
2. `test_admin_open_request_rejects_both_location_and_custom`
3. `test_admin_open_request_accepts_only_location_id`
4. `test_admin_open_request_accepts_only_custom_location`
5. `test_web_open_request_normalizes_chave`
6. `test_web_open_request_rejects_short_chave`
7. `test_web_open_request_rejects_no_location`
8. `test_web_open_request_rejects_both_locations`
9. `test_situacao_pessoal_row_zone_status_literal_enforced`
10. `test_accident_summary_label_format`

## 5) Verificações executadas

1. Import direto dos schemas:
   - comando: `python -c "from sistema.app.schemas import AdminAccidentStateResponse, WebAccidentOpenRequest, SituacaoPessoalRow"`
   - resultado: OK

2. Testes do novo módulo:
   - comando: `python -m pytest -q tests\schemas\test_accident_schemas.py`
   - resultado: **10 passed**

## 6) Arquivos alterados nesta tarefa

- `sistema/app/schemas.py` (edição — seção `# ---- Modo Acidente ----` adicionada ao final)
- `tests/schemas/test_accident_schemas.py` (novo)
- `tests/schemas/__init__.py` (novo — para reconhecimento como pacote)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task A3 — Resumo detalhado da implementação concluída

A implementação do **Bloco A / Task A3** foi concluída com a criação do script de migração SQL para Postgres.

## 1) Script de migração criado

Arquivo criado: `sistema/scripts/migrate_accidents_v1.sql`

O script é completamente idempotente (`IF NOT EXISTS` em todas as instruções) e cria as 5 tabelas do Modo Acidente em Postgres de produção (Digital Ocean).

### Tabelas criadas:

| Tabela | Descrição |
|---|---|
| `accidents` | Registro central de cada acidente, com snapshots e actor de abertura/encerramento |
| `accident_user_reports` | Última resposta de cada usuário a um acidente específico |
| `accident_video_uploads` | Vídeos capturados pelos usuários durante o acidente |
| `accident_archives` | Snapshot final, XLSX e ZIP gerados ao encerrar o acidente |
| `email_delivery_logs` | Log de todos os e-mails enviados com rastreio de status |

### Constraints incluídas (correspondem 1:1 com os modelos SQLAlchemy):

- `uq_accidents_accident_number` — número de acidente único global
- `ck_accidents_origin_allowed` — `origin IN ('admin', 'web')`
- `ck_accidents_number_non_negative` — `accident_number >= 0`
- `ck_accidents_opened_by_actor_required` — exatamente um dos dois (admin ou user) preenchido
- `uq_accident_user_reports_accident_id_user_id` — par `(accident_id, user_id)` único
- `ck_accident_user_reports_zone_allowed` — `zone IN ('waiting', 'safety', 'accident')`
- `ck_accident_user_reports_status_allowed` — `status IN ('waiting', 'ok', 'help')`
- `uq_accident_video_uploads_idempotency_key` — chave de idempotência única
- `uq_accident_archives_accident_id` — um archive por acidente
- `ck_email_delivery_logs_status_allowed` — `delivery_status IN ('queued', 'sent', 'failed')`

### FKs e ON DELETE semântico:

- `accident_user_reports.accident_id` → `accidents(id)` **ON DELETE CASCADE**
- `accident_video_uploads.accident_id` → `accidents(id)` **ON DELETE CASCADE**
- `accident_archives.accident_id` → `accidents(id)` **ON DELETE CASCADE**
- `email_delivery_logs.accident_id` → `accidents(id)` **ON DELETE SET NULL** (preserva log histórico)

### Índices criados:

- `ix_accidents_single_active` — índice parcial único em `closed_at WHERE closed_at IS NULL` (somente um acidente ativo)
- `ix_accidents_single_active_guard` — índice parcial único em constante `(1)` `WHERE closed_at IS NULL` (redundância para garantir unicidade mesmo em edge cases do planner do Postgres)
- `ix_accident_video_uploads_accident_user` — índice composto `(accident_id, user_id)` para queries de vídeos por usuário/acidente
- `ix_email_delivery_logs_accident` — índice em `accident_id` para queries de e-mails por acidente

## 2) Verificações executadas

1. Validação dos conteúdos do SQL via script Python:
   - Todas as 5 tabelas: **OK**
   - Todas as 10 constraints: **OK**
   - Todos os 4 índices: **OK**
   - `IF NOT EXISTS` em 9 instruções DDL + 1 no cabeçalho comentado: **OK**
   - `ON DELETE CASCADE` em 3 tabelas: **OK**
   - `ON DELETE SET NULL` em 1 tabela: **OK**

2. Docker não disponível no ambiente de desenvolvimento — testes manuais com `docker run postgres:15` são realizados conforme descrito na seção "Testes manuais" da tarefa:
   ```bash
   docker run -d --name pg-test -e POSTGRES_PASSWORD=test postgres:15
   docker exec -i pg-test psql -U postgres < sistema/scripts/migrate_accidents_v1.sql
   docker exec -i pg-test psql -U postgres -c "\dt"
   docker exec -i pg-test psql -U postgres -c "\d accidents"
   docker rm -f pg-test
   ```

## 3) Alembic

Verificado que não há configuração de Alembic convencional (sem `versions/` com migrações auto-geradas). O padrão do projeto é `Base.metadata.create_all` em dev e SQL manual em produção. O script gerado segue esse padrão.

## 4) Arquivos alterados nesta tarefa

- `sistema/scripts/migrate_accidents_v1.sql` (novo)
- `sistema/scripts/` (diretório criado)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task B1 — Resumo detalhado da implementação concluída

A implementação do **Bloco B / Task B1** adicionou o terceiro broker de tempo real (`web_check_updates_broker`) ao serviço de atualizações em tempo real.

## 1) Alterações em `sistema/app/services/admin_updates.py`

### Novo broker (linha 275):
```python
web_check_updates_broker = AdminUpdatesBroker("checking_web_check_updates")
```

### `start_realtime_brokers()` — adicionado:
```python
web_check_updates_broker.start()
```

### `stop_realtime_brokers()` — adicionado:
```python
web_check_updates_broker.stop()
```

### Novo helper `notify_web_check_data_changed` (linha 298):
```python
def notify_web_check_data_changed(reason: str = "refresh", *, metadata: dict[str, object] | None = None) -> None:
    web_check_updates_broker.publish(reason=reason, metadata=metadata)
```

## 2) Contexto de arquitetura

Os três brokers são instâncias independentes de `AdminUpdatesBroker`, cada um com seu próprio canal Postgres LISTEN/NOTIFY:

| Broker | Canal Postgres | Consumidor |
|---|---|---|
| `admin_updates_broker` | `checking_admin_updates` | Painel admin |
| `transport_updates_broker` | `checking_transport_updates` | Dashboard de transporte |
| `web_check_updates_broker` | `checking_web_check_updates` | Checking Web (usuários) |

Em dev (SQLite), os brokers operam apenas com fan-out em memória (sem Postgres LISTEN/NOTIFY), tornando `start()`/`stop()` no-ops seguros.

## 3) Testes obrigatórios criados

Arquivo criado: `tests/services/test_admin_updates_brokers.py`

5 testes implementados (3 obrigatórios + 2 extras de cobertura):

1. `test_web_check_broker_publish_fanout` — subscribe + publish + assert payload com `reason` e `metadata`
2. `test_web_check_broker_isolated_from_admin` — publish em `admin_updates_broker` não chega ao `web_check_updates_broker`
3. `test_start_stop_all_brokers` — `start_realtime_brokers()` e `stop_realtime_brokers()` sem erro
4. `test_three_brokers_are_distinct_instances` — os 3 objetos são instâncias distintas
5. `test_web_check_broker_channel_name` — canal interno está correto

## 4) Verificações executadas

1. Import direto:
   - `from sistema.app.services.admin_updates import web_check_updates_broker, notify_web_check_data_changed`
   - resultado: **OK**

2. Testes:
   - `python -m pytest -q tests\services\test_admin_updates_brokers.py`
   - resultado: **5 passed**

## 5) Arquivos alterados nesta tarefa

- `sistema/app/services/admin_updates.py` (edição)
- `tests/services/test_admin_updates_brokers.py` (novo)
- `tests/services/__init__.py` (novo)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task B2 — Resumo detalhado da implementação concluída

A implementação do **Bloco B / Task B2** adicionou o endpoint SSE `/api/web/check/stream` ao roteador da Checking Web.

## 1) Alterações em `sistema/app/routers/web_check.py`

### Bloco de imports atualizado (próximo da linha 37–41):

```python
from ..services.admin_updates import (
    notify_admin_data_changed,
    notify_transport_data_changed,
    notify_web_check_data_changed,
    transport_updates_broker,
    web_check_updates_broker,
)
```

### Novo endpoint `stream_web_check_updates` (adicionado após `stream_web_transport_updates`):

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

## 2) Comportamento e segurança

- **Autenticação**: usa o guard `_require_matching_authenticated_web_user(request, db, chave)`, idêntico ao endpoint de transporte. A sessão web deve ter `web_user_chave` correspondendo ao parâmetro `chave`, e o usuário deve ter `senha` definida — caso contrário retorna HTTP 401.
- **Primeiro evento**: ao conectar, o cliente recebe imediatamente `data: {"reason": "connected"}`.
- **Keep-alive**: a cada 15 segundos sem mensagens, o servidor envia `: keep-alive` (comentário SSE) para manter a conexão aberta.
- **Desconexão limpa**: o `finally` chama `web_check_updates_broker.unsubscribe(subscriber_id)`, liberando a fila interna.
- **Publicação**: qualquer chamada a `notify_web_check_data_changed(reason=..., metadata=...)` entrega a mensagem a todos os subscribers deste endpoint.

## 3) Testes obrigatórios criados

Arquivo criado: `tests/routers/test_web_check_stream.py`

Os 4 testes foram implementados com `@pytest.mark.anyio` (asyncio), chamando o endpoint diretamente (sem HTTP) para contornar limitação fundamental do `httpx.ASGITransport` que bufferiza toda a resposta antes de entregá-la (impossibilitando testes de streaming infinito via HTTP in-process):

1. `test_stream_requires_session` — mock request sem sessão web → `HTTPException` 401
2. `test_stream_initial_connected_event` — conecta com user válido → primeiro chunk contém `"connected"`
3. `test_stream_receives_published_payload` — publica `notify_web_check_data_changed(reason="test")` concorrentemente → chunk com `"reason": "test"` entregue
4. `test_stream_keepalive_after_15s` — substitui `asyncio.wait_for` por versão que sempre lança `TimeoutError` → chunk `: keep-alive` entregue

### Padrão dos testes:

```python
@pytest.mark.anyio
async def test_stream_initial_connected_event(db_session):
    user = _ensure_test_user(db_session)
    mock_req = _make_mock_request(disconnect_after=1)
    response = await stream_web_check_updates(
        request=mock_req, chave=TEST_CHAVE, db=db_session
    )
    chunks = await _collect_events(response.body_iterator)
    assert any("connected" in c for c in chunks)
```

### Helper `_make_mock_request`:

```python
def _make_mock_request(disconnect_after: int = 2):
    mock_req = MagicMock()
    mock_req.session = {"web_user_chave": TEST_CHAVE}
    call_count = 0
    async def is_disconnected():
        nonlocal call_count
        call_count += 1
        return call_count > disconnect_after
    mock_req.is_disconnected = is_disconnected
    return mock_req
```

## 4) Limitação técnica descoberta (`httpx.ASGITransport`)

O `httpx.ASGITransport.handle_async_request` coleta TODOS os chunks de `http.response.body` numa lista e só retorna quando `more_body=False` (i.e., o gerador é exaurido). Para geradores SSE infinitos, isso nunca acontece — a conexão fica pendurada indefinidamente. Esta é uma limitação fundamental do design do httpx para transporte ASGI, não um bug do endpoint.

A solução adotada (chamar o endpoint diretamente e iterar `StreamingResponse.body_iterator`) é a abordagem correta para testar streaming SSE em FastAPI.

## 5) Verificações executadas

1. Import direto:
   - `from sistema.app.routers.web_check import stream_web_check_updates`
   - resultado: **OK**

2. Testes:
   - `python -m pytest -q tests/routers/test_web_check_stream.py`
   - resultado: **4 passed** (asyncio)

3. Suite completa dos novos testes:
   - `python -m pytest tests/models/ tests/schemas/ tests/services/ tests/routers/ -v`
   - resultado: **28 passed** (A1: 9, A2: 10, B1: 5, B2: 4)

## 6) Arquivos alterados nesta tarefa

- `sistema/app/routers/web_check.py` (edição — import e endpoint adicionados)
- `tests/routers/test_web_check_stream.py` (novo)
- `tests/routers/__init__.py` (novo)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task C1 — Resumo detalhado da implementação concluída

A implementação do **Bloco C / Task C1** criou o serviço de numeração sequencial de acidentes.

## 1) Arquivo criado: `sistema/app/services/accident_numbering.py`

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

### Comportamento

- `next_accident_number(db)` usa `COALESCE(MAX(accident_number), -1) + 1`: quando não há acidentes, `MAX` retorna `NULL` → `COALESCE` retorna `-1` → resultado é `0` (primeiro acidente = 0000).
- Compatível com SQLite (dev) e Postgres (produção) — usa SQL padrão.
- `format_accident_number` usa f-string `{n:04d}` para zero-pad; aceita valores maiores que 9999 sem truncar (ex: 10000 → "10000").

## 2) Testes obrigatórios criados

Arquivo criado: `tests/services/test_accident_numbering.py`

4 testes implementados (todos passam):

1. `test_next_accident_number_starts_at_zero` — banco vazio → resultado 0
2. `test_next_accident_number_increments` — insere acidente com `accident_number=42` → resultado 43
3. `test_format_accident_number_pads_to_4_digits` — 0→"0000", 42→"0042", 9999→"9999", 1→"0001"
4. `test_format_accident_number_handles_large_values` — 10000→"10000", 99999→"99999"

Os testes usam SQLite in-file (via `tmp_path`) e criam `Project` + `AdminUser` + `Accident` diretamente.

## 3) Verificações executadas

1. Import:
   - `from sistema.app.services.accident_numbering import next_accident_number, format_accident_number`
   - resultado: **OK**

2. Testes:
   - `python -m pytest -v tests/services/test_accident_numbering.py`
   - resultado: **4 passed**

## 4) Arquivos alterados nesta tarefa

- `sistema/app/services/accident_numbering.py` (novo)
- `tests/services/test_accident_numbering.py` (novo)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task C2 — Resumo detalhado da implementação concluída

A implementação do **Bloco C / Task C2** criou o service principal do ciclo de vida de acidentes.

## 1) Arquivo criado: `sistema/app/services/accident_lifecycle.py`

### Exceções customizadas

`python
class AccidentAlreadyActiveError(RuntimeError): pass
class NoActiveAccidentError(RuntimeError): pass
class InvalidAccidentLocationError(ValueError): pass
`

### Funções implementadas

| Função | Descrição |
|---|---|
| `open_accident(db, *, origin, project_id, ...)` | Valida, cria acidente, pré-popula relatórios, publica em ambos os brokers |
| `list_active_accident(db)` | Retorna o acidente com `closed_at IS NULL` ou `None` |
| `close_accident(db, *, accident, closed_by_admin_id)` | Marca encerramento, publica em ambos os brokers |

## 2) Fluxo de `open_accident`

1. **Verificação de acidente ativo**: SELECT em `accidents WHERE closed_at IS NULL`. Se encontrar → `AccidentAlreadyActiveError`.
2. **Resolver projeto**: `db.get(Project, project_id)`. Se None → `ValueError`.
3. **Resolver local**:
   - `location_id` fornecido → carrega `ManagedLocation`. Se origin="admin" e projeto não está no `projects_json` → `InvalidAccidentLocationError`. Se origin="web" → aceita mesmo assim.
   - Sem `location_id` → usa `custom_location_name.strip()`.
4. **Criar `Accident`** com `next_accident_number(db)`, `flush()` para obter ID.
5. **Pré-popular `AccidentUserReport`** para todos os `User.checkin == True`.
6. **Tratar autor web**: se `origin="web"`, atualizar zone/status na linha do autor (se estava checked-in) ou criar linha nova (se não estava).
7. **`db.commit()`** e publicar `"accident_opened"` em `notify_admin_data_changed` e `notify_web_check_data_changed`.

## 3) Compatibilidade SQLite/Postgres

O `FOR UPDATE` da spec original não é suportado em SQLite. A implementação usa SELECT simples — a proteção real é o índice parcial único `ix_accidents_single_active_guard`. Em Postgres produção, o índice parcial torna o segundo INSERT atômico.

## 4) Testes obrigatórios criados

Arquivo criado: `tests/services/test_accident_lifecycle.py`

12 testes implementados (11 obrigatórios + 1 extra):

1. `test_open_accident_creates_with_number_zero`
2. `test_open_accident_raises_when_already_active`
3. `test_close_accident_marks_closed_at_and_admin`
4. `test_close_then_open_increments_number`
5. `test_open_admin_validates_location_belongs_to_project`
6. `test_open_web_accepts_location_from_other_project`
7. `test_open_prepopulates_user_reports_for_checked_in_users`
8. `test_open_web_sets_reporter_zone_status_for_author`
9. `test_open_web_creates_report_for_non_checkedin_author` *(extra)*
10. `test_close_raises_when_not_active`
11. `test_open_publishes_to_both_brokers`
12. `test_close_publishes_to_both_brokers`

## 5) Verificações executadas

- `python -m pytest -v tests/services/test_accident_lifecycle.py` → **12 passed**

## 6) Arquivos alterados nesta tarefa

- `sistema/app/services/accident_lifecycle.py` (novo)
- `tests/services/test_accident_lifecycle.py` (novo)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task C3 — Resumo detalhado da implementação concluída

A implementação do **Bloco C / Task C3** estendeu o service `accident_lifecycle.py` com três novas funções de suporte ao ciclo de vida de acidentes.

## 1) Arquivo alterado: `sistema/app/services/accident_lifecycle.py`

### Novos imports

- `from datetime import datetime` (para tipagem do parâmetro `event_time`)
- `AccidentVideoUpload` adicionado ao import de `..models`

### Funções implementadas

| Função | Descrição |
|---|---|
| `upsert_user_safety_report(db, *, accident, user, zone, status)` | Cria ou atualiza `AccidentUserReport`, detecta transição para `help`, publica em ambos os brokers |
| `attach_video_upload(db, *, accident, user, object_key, public_url, content_type, size_bytes, duration_seconds, idempotency_key, captured_at=None)` | Idempotente por `idempotency_key`; cria `AccidentVideoUpload`, publica em ambos os brokers |
| `update_accident_membership_for_check_event(db, *, accident, user, action, event_time)` | Cria ou carrega `AccidentUserReport`, atualiza `last_checkin_action`/`last_action_at`, publica em ambos os brokers |

## 2) Detalhe de `upsert_user_safety_report`

1. SELECT por `(accident_id, user_id)`. Se não existe, cria com snapshots + `zone/status="waiting"` + flush.
2. Captura `previous_status = report.status` antes de atualizar.
3. Atualiza `zone`, `status`, `reported_at`, `updated_at`.
4. `db.commit()`.
5. `fired_help_now = (status == "help" and previous_status != "help")`.
6. Publica `"accident_user_report"` em `notify_admin_data_changed` e `notify_web_check_data_changed`.
7. Retorna `(report, fired_help_now)`.

## 3) Detalhe de `attach_video_upload`

1. SELECT por `idempotency_key`. Se já existe → retorna linha existente (idempotência pura).
2. Cria `AccidentVideoUpload` com `captured_at = captured_at or now_sgt()`, `created_at = now_sgt()`.
3. `db.add(upload); db.commit()`.
4. Publica `"accident_video_uploaded"` em ambos os brokers com `metadata={"accident_id": ..., "user_id": ...}`.
5. Retorna `upload`.

## 4) Detalhe de `update_accident_membership_for_check_event`

1. SELECT por `(accident_id, user_id)`. Se não existe, cria com snapshots + `zone="waiting"` + `status="waiting"` + flush.
2. Atualiza `last_checkin_action=action`, `last_action_at=event_time`, `updated_at=now_sgt()`.
3. `db.commit()`.
4. Publica `"accident_user_report"` em ambos os brokers.
5. Retorna `report`.

## 5) Testes adicionados

Arquivo: `tests/services/test_accident_lifecycle.py` (8 novos testes, total passa de 12 para 20)

1. `test_upsert_creates_when_missing`
2. `test_upsert_updates_when_existing_and_preserves_created_at`
3. `test_upsert_fires_help_only_on_transition`
4. `test_upsert_does_not_fire_help_on_consecutive_help`
5. `test_attach_video_inserts_first_time`
6. `test_attach_video_idempotent_by_key`
7. `test_check_event_hook_creates_waiting_row_for_new_user`
8. `test_check_event_hook_preserves_zone_status_when_user_already_reported`

**Nota sobre SQLite:** a comparação de `last_action_at` no teste usa `.replace(tzinfo=None)` para neutralizar o descarte de timezone que SQLite faz ao persistir datetimes.

## 6) Verificações executadas

- `python -m pytest -v tests/services/test_accident_lifecycle.py` → **20 passed**
- `python -m pytest tests/models tests/schemas tests/services -q` → **48 passed**

## 7) Arquivos alterados nesta tarefa

- `sistema/app/services/accident_lifecycle.py` (editado — 3 novas funções + imports)
- `tests/services/test_accident_lifecycle.py` (editado — 8 novos testes C3 adicionados ao final)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task C4 — Resumo detalhado da implementação concluída

A implementação do **Bloco C / Task C4** criou o service `accident_situation_table.py` que constrói as linhas da aba "Situação de Pessoal" do admin.

## 1) Arquivo criado: `sistema/app/services/accident_situation_table.py`

### Funções implementadas

| Função | Descrição |
|---|---|
| `_derive_display(report, opened_at)` | Privada; mapeia zone/status para (zone_display, status_display, row_color, priority) |
| `build_situation_rows(db, *, accident)` | Pública; carrega reports + vídeos, monta lista de `SituacaoPessoalRow` ordenada |

### Lógica de prioridade (`_derive_display`)

| Prioridade | Condição | Cor |
|---|---|---|
| 1 | `zone=accident` + `status=help` | `blinking-red` |
| 2 | `zone=accident` + `status=ok` | `yellow` |
| 3 | `zone=waiting` | `turquoise` |
| 4 | `zone=safety` + `status=ok` | `light-green` |
| 5 | `last_checkin_action=check-out` e `last_action_at >= opened_at` | `light-gray` |
| 3 | fallback | `white` |

A prioridade 5 (check-out durante o acidente) é verificada antes das demais por ser uma regra de override.

### Detalhes de `build_situation_rows`

1. SELECT em `AccidentUserReport` filtrando `accident_id`.
2. Para cada report: query `AccidentVideoUpload` filtrado por `(accident_id, user_id)` ordenado por `captured_at ASC`.
3. Monta `AccidentVideoLink` para cada vídeo.
4. `event_time = report.reported_at or report.last_action_at or report.created_at`.
5. Chama `_derive_display(report, accident.opened_at)`.
6. Cria `SituacaoPessoalRow` com todos os campos.
7. Ordena lista por `(priority ASC, event_time DESC)` — `event_time.timestamp()` negado para descending.

### Compatibilidade SQLite/Postgres

A comparação de `last_action_at >= opened_at` usa `opened_at.replace(tzinfo=None)` quando `opened_at` tem timezone, neutralizando a diferença de aware vs naive que SQLite gera.

## 2) Testes criados

Arquivo criado: `tests/services/test_accident_situation_table.py`

8 testes (todos obrigatórios):

1. `test_priority_1_help_blinking_red`
2. `test_priority_2_accident_ok_yellow`
3. `test_priority_3_waiting_turquoise`
4. `test_priority_4_safety_ok_light_green`
5. `test_priority_5_checked_out_after_open_light_gray`
6. `test_within_same_priority_more_recent_first`
7. `test_videos_included_per_user`
8. `test_videos_ordered_by_captured_at_asc`

## 3) Verificações executadas

- `python -m pytest -v tests/services/test_accident_situation_table.py` → **8 passed**
- `python -m pytest tests/models tests/schemas tests/services -q` → **56 passed**

## 4) Arquivos alterados nesta tarefa

- `sistema/app/services/accident_situation_table.py` (novo)
- `tests/services/test_accident_situation_table.py` (novo)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task C5 — Resumo detalhado da implementação concluída

A implementação do **Bloco C / Task C5** integrou o hook de check-in/check-out ao modo acidente, garantindo que qualquer evento de ponto registrado durante um acidente em aberto reflita automaticamente na tabela `AccidentUserReport`.

## 1) Arquivo alterado: `sistema/app/services/accident_lifecycle.py`

### Novos imports

- `import logging` e `_logger = logging.getLogger(__name__)`

### Função adicionada

`fire_accident_hook_for_check_event(db, *, user, action, event_time)`

- Recebe `action` nos formatos `"checkin"/"checkout"` (sem hífen) ou `"check-in"/"check-out"` (com hífen) e normaliza para `"check-in"/"check-out"`.
- Ações desconhecidas retornam silenciosamente.
- Chama `list_active_accident(db)` — se não há acidente ativo, retorna (noop).
- Chama `update_accident_membership_for_check_event(...)` para atualizar ou criar o `AccidentUserReport`.
- Todo o corpo é envolvido em `try/except Exception` com `_logger.warning(..., exc_info=True)`, garantindo que **jamais** propaga exceção para o fluxo de check-in.

## 2) Arquivo alterado: `sistema/app/services/forms_submit.py`

- Import adicionado: `from .accident_lifecycle import fire_accident_hook_for_check_event`
- Hook inserido logo após `notify_admin_data_changed(action)` em **ambas** as branches de sucesso de `submit_forms_event`:
  - Branch "not-queued" (evento aceito sem Forms)
  - Branch "queued" (evento aceito e enfileirado para Forms)
- Variável `event_time` usada: `normalized_event_time` (já com timezone normalizado).

## 3) Arquivo alterado: `sistema/app/routers/device.py`

- Import adicionado: `from ..services.accident_lifecycle import fire_accident_hook_for_check_event`
- Hook inserido após `notify_admin_data_changed(action)` em **dois** pontos de sucesso:
  - Path local (não enfileirado)
  - Path enfileirado
- **Não** inserido no path de `checkout bloqueado` (linha ~182) — o check-out não foi concluído, estado do usuário não mudou.
- Variável `event_time` usada: `activity_time` (= `now_sgt()`).

## 4) Arquivo alterado: `sistema/app/routers/mobile.py`

- Import adicionado: `from ..services.accident_lifecycle import fire_accident_hook_for_check_event`
- Hook inserido após `notify_admin_data_changed(payload.action)` em **três** pontos:
  - Submit path not-queued (endpoint `/events/submit`)
  - Submit path queued (endpoint `/events/submit`)
  - Sync path (endpoint `/events/sync`)
- Variável `event_time` usada: `event_time` (normalizado via `normalize_event_time` em todos os casos).

## 5) Arquivo criado: `tests/services/test_accident_check_event_hook.py`

6 testes (5 unitários + 1 integração):

| Teste | Tipo | Descrição |
|---|---|---|
| `test_hook_skips_when_no_active_accident` | Unit | Sem acidente ativo → noop, nenhum report criado |
| `test_hook_creates_waiting_report_for_new_user_check_in` | Unit | Acidente ativo + usuário novo → report criado com zone/status="waiting" |
| `test_hook_updates_last_action_for_existing_user_check_out` | Unit | Report existente + checkout → `last_checkin_action`="check-out", zone/status preservados |
| `test_hook_swallows_exceptions` | Unit | Mock levanta RuntimeError → nenhuma exceção propaga |
| `test_hook_ignores_unknown_action` | Unit | Action desconhecida → silenciosa, nenhum report criado |
| `test_web_check_post_calls_hook` | Integration | POST `/api/web/check` → mock `fire_accident_hook_for_check_event` verificado chamado |

**Nota:** Testes unitários usam `tmp_path` com SQLite isolado. Teste de integração usa `test_checking.db` (banco compartilhado) e configura `UserProjectMembership` explicitamente para garantir isolamento de dados legados.

## 6) Verificações executadas

- `python -m pytest tests/services/test_accident_check_event_hook.py -v` → **6 passed**
- `python -m pytest tests/models tests/schemas tests/services -q` → **62 passed**

## 7) Arquivos alterados nesta tarefa

- `sistema/app/services/accident_lifecycle.py` (editado — `fire_accident_hook_for_check_event` + logging)
- `sistema/app/services/forms_submit.py` (editado — 2 hook calls)
- `sistema/app/routers/device.py` (editado — 2 hook calls)
- `sistema/app/routers/mobile.py` (editado — 3 hook calls)
- `tests/services/test_accident_check_event_hook.py` (novo — 6 testes)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task D1 — Resumo detalhado da implementação concluída

A implementação do **Bloco D / Task D1** adicionou o endpoint `GET /api/admin/accidents/active` ao router admin, expondo o estado atual do modo acidente (incluindo a tabela Situação de Pessoal) para a UI admin.

## 1) Arquivo alterado: `sistema/app/routers/admin.py`

### Novos imports

Modelos adicionados ao bloco `from ..models import (...)`:
- `Accident`
- `AdminUser`

Schemas adicionados ao bloco `from ..schemas import (...)`:
- `AccidentSummary`
- `AdminAccidentStateResponse`

Serviços adicionados (após o import existente de `user_sync`):
```python
from ..services.accident_lifecycle import list_active_accident
from ..services.accident_numbering import format_accident_number
from ..services.accident_situation_table import build_situation_rows
```

### Helper privado adicionado

`_accident_summary(db: Session, accident: Accident) -> AccidentSummary`

- Inserido logo após o bloco de fechamento do endpoint `/stream` (linha ~1968).
- Resolve `opened_by_label`:
  - Se `opened_by_admin_id` → busca `AdminUser` por PK → usa `admin.nome_completo`.
  - Else se `opened_by_user_id` → busca `User` por PK → usa `user.nome`.
  - Fallback: `"—"`.
- Retorna `AccidentSummary` completo com `accident_number_label` formatado via `format_accident_number`.

### Endpoint adicionado

```python
@router.get("/accidents/active", response_model=AdminAccidentStateResponse,
            dependencies=[Depends(require_admin_session)])
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

- Caminho: `GET /api/admin/accidents/active`
- Requer sessão admin de qualquer perfil (`require_admin_session`).
- Sem acidente ativo → `{"is_active": false, "accident": null, "situation_rows": []}`.
- Com acidente ativo → payload completo com `situation_rows` ordenadas por prioridade (delegado a `build_situation_rows`).

## 2) Arquivo criado: `tests/routers/test_admin_accidents.py`

3 testes obrigatórios:

| Teste | Descrição |
|---|---|
| `test_active_requires_session` | Sem cookie de sessão admin → 401 |
| `test_active_returns_empty_when_none` | Nenhum acidente ativo → `is_active=False`, `accident=null`, `situation_rows=[]` |
| `test_active_returns_accident_and_rows` | Acidente ativo criado → `is_active=True`, todos os campos de `accident` verificados |

### Detalhes da infraestrutura de teste

- Admin user criado com `perfil=19` (dígitos "1" e "9" → `user_has_admin_access=True`).
- Login via `POST /api/admin/auth/login` usando `TestClient` com cookies persistentes.
- Acidentes abertos via inserção direta no banco (criando `AdminUser` row na tabela `admin_users` associada ao `User` admin).
- Limpeza explícita via `_close_all_accidents(db)` antes de cada teste para evitar conflito do índice parcial único.
- Valores de objetos SQLAlchemy capturados antes de fechar a sessão para evitar `DetachedInstanceError`.

## 3) Verificações executadas

- `python -c "from sistema.app.routers.admin import get_active_accident_state, _accident_summary; print('imports OK')"` → **imports OK**
- `python -m pytest tests/routers/test_admin_accidents.py -v` → **3 passed**
- `python -m pytest tests/models tests/schemas tests/services tests/routers -q` → **69 passed**

## 4) Arquivos alterados nesta tarefa

- `sistema/app/routers/admin.py` (editado — imports + helper + endpoint)
- `tests/routers/test_admin_accidents.py` (novo — 3 testes)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task D2 — Resumo detalhado da implementação concluída

A implementação do **Bloco D / Task D2** adicionou o endpoint `POST /api/admin/accidents/open` ao router admin, permitindo ao administrador abrir o modo acidente a partir da UI administrativa.

## 1) Arquivo alterado: `sistema/app/routers/admin.py`

### Novos imports

Modelos e schemas adicionados:
- Schema: `AdminAccidentOpenRequest`
- Serviços de lifecycle: `AccidentAlreadyActiveError`, `InvalidAccidentLocationError`, `open_accident`

### Endpoint adicionado

```python
@router.post("/accidents/open", response_model=AdminAccidentStateResponse,
             dependencies=[Depends(require_full_admin_session)])
def open_admin_accident(
    payload: AdminAccidentOpenRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_full_admin_session),
) -> AdminAccidentStateResponse:
```

- Caminho: `POST /api/admin/accidents/open`
- Requer sessão admin com perfil completo (`require_full_admin_session` — dígito "1" ou "9" no `perfil`).
- Sem sessão → 401; sem permissão completa → 403.
- `AccidentAlreadyActiveError` → 409 `"Ja existe um acidente em curso."`.
- `InvalidAccidentLocationError` → 422 `"O local selecionado nao pertence ao projeto."`.
- Body inválido (validação Pydantic/FastAPI) → 422.
- Sucesso → 200 com `AdminAccidentStateResponse` completo.
- Loga evento via `log_event(db, source="admin", action="accident_open", ...)`.
- `open_accident()` publica internamente `"accident_opened"` nos dois brokers SSE (`notify_admin_data_changed` e `notify_web_check_data_changed`).

### Bug fix

Durante a edição de D1, o decorator `@router.get("/administrators", ...)` havia sido perdido acidentalmente. Corrigido nesta tarefa.

## 2) Arquivo alterado: `tests/routers/test_admin_accidents.py`

5 testes D2 adicionados ao arquivo criado em D1:

| Teste | Descrição |
|---|---|
| `test_open_requires_full_admin` | Usuário com `perfil=0` (painel admin, sem acesso completo) → 403 |
| `test_open_creates_when_none` | Sem acidente ativo, payload válido → 200 com `is_active=True` |
| `test_open_returns_conflict_when_active` | Acidente já aberto → 409 |
| `test_open_validates_payload` | `project_id` ausente ou `location_id + custom_location_name` juntos → 422 |
| `test_open_publishes_brokers` | Ambos os brokers chamados com `"accident_opened"` após abertura bem-sucedida |

### Detalhes da infraestrutura de teste

- Segundo usuário de teste criado: `_LIMITED_CHAVE = "D2LM"`, `perfil=0` (acesso apenas ao painel admin).
- Helper `_ensure_limited_admin_user(db)` cria/reutiliza o usuário limitado.
- Helper `_logged_in_limited_client()` autentica o usuário limitado via `POST /api/admin/auth/login`.
- Brokers mockados via `unittest.mock.patch` nas funções em `sistema.app.services.accident_lifecycle`.
- `_close_all_accidents(db)` chamado antes de cada teste que abre acidente para evitar conflito do índice parcial.

## 3) Verificações executadas

- `python -m pytest tests/routers/test_admin_accidents.py -v` → **8 passed** (3 D1 + 5 D2)
- `python -m pytest tests/models tests/schemas tests/services tests/routers -q` → **74 passed**

## 4) Arquivos alterados nesta tarefa

- `sistema/app/routers/admin.py` (editado — novos imports + endpoint POST + bug fix no decorator)
- `tests/routers/test_admin_accidents.py` (editado — 5 testes D2 adicionados)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task D3 — Resumo detalhado da implementação concluída

A implementação do **Bloco D / Task D3** adicionou o endpoint `POST /api/admin/accidents/close` ao router admin, permitindo ao administrador encerrar o acidente ativo e disparar a geração do arquivo em background.

## 1) Arquivo alterado: `sistema/app/routers/admin.py`

### Novos imports

- `BackgroundTasks` adicionado ao import de `fastapi`
- `close_accident`, `NoActiveAccidentError` adicionados ao bloco `from ..services.accident_lifecycle import (...)`

### Stub adicionado

```python
def build_and_attach_archive_for_accident(accident_id: int) -> None:
    # TODO Task F2: build XLSX + ZIP, upload to Spaces, update accident.archive_object_key,
    # publish accident_closed again with ready=True.
    pass
```

Inserido logo antes do endpoint `/accidents/close`. Será substituído pela implementação real na Task F2 (Phase 10).

### Endpoint adicionado

```python
@router.post("/accidents/close", response_model=AdminAccidentStateResponse,
             dependencies=[Depends(require_full_admin_session)])
def close_admin_accident(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_full_admin_session),
) -> AdminAccidentStateResponse:
```

- Caminho: `POST /api/admin/accidents/close`
- Requer sessão admin com perfil completo (`require_full_admin_session`).
- Sem sessão → 401; sem permissão → 403.
- Sem acidente ativo → 409 `"Nenhum acidente em curso."`.
- Acidente ativo → encerra via `close_accident()`, agenda `build_and_attach_archive_for_accident` como BackgroundTask, loga evento, retorna `AdminAccidentStateResponse(is_active=False)`.
- `close_accident()` publica internamente `"accident_closed"` nos dois brokers SSE.

## 2) Arquivo alterado: `tests/routers/test_admin_accidents.py`

4 testes D3 adicionados (total do arquivo: 12 testes):

| Teste | Descrição |
|---|---|
| `test_close_requires_full_admin` | Usuário com `perfil=0` → 403 |
| `test_close_conflict_when_none_active` | Sem acidente ativo → 409 |
| `test_close_marks_closed_and_publishes` | Encerramento → 200 `is_active=False`, `accident_closed` publicado em ambos os brokers |
| `test_close_schedules_archive_build` | `build_and_attach_archive_for_accident` chamado como BackgroundTask com `accident_id` correto |

**Nota:** `TestClient` do Starlette/FastAPI executa `BackgroundTasks` sincronamente, permitindo verificar diretamente o mock após o request.

## 3) Verificações executadas

- `python -m pytest tests/routers/test_admin_accidents.py -v` → **12 passed** (3 D1 + 5 D2 + 4 D3)
- `python -m pytest tests/models tests/schemas tests/services tests/routers -q` → **78 passed**

## 4) Arquivos alterados nesta tarefa

- `sistema/app/routers/admin.py` (editado — `BackgroundTasks` import + lifecycle imports + stub + endpoint)
- `tests/routers/test_admin_accidents.py` (editado — 4 testes D3 adicionados)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task D4 — Resumo detalhado da implementação concluída

A implementação do **Bloco D / Task D4** adicionou os endpoints `GET /api/admin/accidents` e `GET /api/admin/accidents/{id}/archive` ao router admin, permitindo listar acidentes encerrados e fazer download do arquivo comprimido.

## 1) Arquivo alterado: `sistema/app/routers/admin.py`

### Novos imports

- `AccidentArchive` adicionado ao bloco `from ..models import (...)`
- `AccidentClosedListResponse`, `AccidentClosedRow` adicionados ao bloco `from ..schemas import (...)`
- `RedirectResponse` adicionado ao `from fastapi.responses import (...)`

### Stub adicionado

```python
def generate_presigned_url(object_key: str, expires_in_seconds: int = 300) -> str:
    # TODO Task E2: generate a real pre-signed URL from the object storage provider.
    raise NotImplementedError("generate_presigned_url not yet implemented (Task E2)")
```

Inserido antes do endpoint `GET /accidents`. Será substituído pela implementação real na Task E2.

### Endpoint `GET /accidents` adicionado

```python
@router.get("/accidents", response_model=AccidentClosedListResponse,
            dependencies=[Depends(require_full_admin_session)])
def list_closed_accidents_endpoint(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_full_admin_session),
) -> AccidentClosedListResponse:
```

- Filtra apenas `closed_at IS NOT NULL`, ordenado por `accident_number DESC`.
- Para cada acidente: verifica existência de `AccidentArchive` → `download_ready`.
- `can_delete = (current_admin.perfil == 9)`.
- `opened_by_label` resolvido inline (mesmo padrão do helper `_accident_summary`).
- `download_url = f"/api/admin/accidents/{accident.id}/archive"`.

### Endpoint `GET /accidents/{accident_id}/archive` adicionado

- Busca `AccidentArchive` pelo `accident_id`.
- 404 se não existe: `"Arquivo do acidente ainda nao esta pronto."`.
- Chama `generate_presigned_url(archive.zip_object_key, expires_in_seconds=300)`.
- Retorna `RedirectResponse(url=presigned_url, status_code=307)`.

## 2) Arquivo alterado: `tests/routers/test_admin_accidents.py`

5 testes D4 adicionados (total do arquivo: 17 testes):

| Teste | Descrição |
|---|---|
| `test_list_returns_only_closed` | Acidente ativo excluído da lista; acidente fechado incluído |
| `test_list_ordered_desc` | Resultados em ordem decrescente por `accident_number` |
| `test_can_delete_true_only_for_perfil_9` | `can_delete=True` apenas quando `perfil==9`; `perfil=19` retorna `False` |
| `test_download_returns_307_when_ready` | Com archive → 307 redirect para URL mockada |
| `test_download_returns_404_when_archive_missing` | Sem archive → 404 |

### Helpers de suporte adicionados

- `_insert_closed_accident(db, proj, admin_user, number_override)` — insere acidente já fechado com `number_override` opcional para controlar ordenação.
- `_insert_archive(db, accident)` — insere `AccidentArchive` fake para o acidente.
- `_make_archive_url(accident_id)` — gera a URL do endpoint de download.

## 3) Verificações executadas

- `python -m pytest tests/routers/test_admin_accidents.py -v` → **17 passed** (3 D1 + 5 D2 + 4 D3 + 5 D4)
- `python -m pytest tests/models tests/schemas tests/services tests/routers -q` → **83 passed**

## 4) Arquivos alterados nesta tarefa

- `sistema/app/routers/admin.py` (editado — novos imports + stub `generate_presigned_url` + 2 novos endpoints)
- `tests/routers/test_admin_accidents.py` (editado — 5 testes D4 + helpers adicionados)
- `docs/temp000A.md` (atualizado com este resumo)


# Task D5 — Resumo detalhado da implementação concluída

A implementação do **Bloco D / Task D5** adicionou o endpoint DELETE /api/admin/accidents/{id} restrito a admins com perfil=9, e corrigiu dois bugs de isolamento de testes que faziam 500s aparecerem nos testes de abertura de acidente.

## 1) Arquivo alterado: sistema/app/routers/admin.py

### Novos imports

- 
otify_web_check_data_changed adicionado ao import de ..services.admin_updates

### Novo stub

- delete_prefix(prefix: str) -> None — stub vazio com TODO Task E2, para futuramente deletar objetos do armazenamento de objeto (Spaces/S3) pelo prefixo.

### Novo endpoint

`
DELETE /api/admin/accidents/{accident_id}
`

- Requer sessão admin completa (equire_full_admin_session).
- **403** se current_admin.perfil != 9.
- **404** se o acidente não existir.
- **409** se o acidente ainda estiver ativo (closed_at IS NULL).
- **200** com {"ok": true, "message": "Acidente removido com sucesso."} em caso de sucesso.
- Cascata: db.delete(accident) remove o acidente; graças aos relacionamentos ORM (cascade="all, delete-orphan") adicionados ao modelo, todas as linhas filhas (AccidentUserReport, AccidentVideoUpload, AccidentArchive) também são removidas automaticamente.
- Chama delete_prefix(f"accidents/{format_accident_number(accident_number)}/") para limpar objetos no Spaces.
- Registra evento via log_event(...) e dispara 
otify_admin_data_changed + 
otify_web_check_data_changed.

## 2) Arquivo alterado: sistema/app/models.py

### Relacionamentos ORM com cascade adicionados ao Accident

- rom sqlalchemy.orm import Mapped, mapped_column, relationship — elationship adicionado ao import existente.
- Três relacionamentos adicionados à classe Accident:
  `python
  user_reports = relationship("AccidentUserReport", cascade="all, delete-orphan")
  video_uploads = relationship("AccidentVideoUpload", cascade="all, delete-orphan")
  archive = relationship("AccidentArchive", cascade="all, delete-orphan", uselist=False)
  `
  Esses relacionamentos garantem que, ao chamar db.delete(accident) no ORM, as linhas filhas sejam deletadas mesmo em SQLite sem PRAGMA foreign_keys=ON (que não é habilitado pelo database.py do projeto).

## 3) Arquivo criado: 	ests/conftest.py

**Bug raiz corrigido:** sem conftest.py, o engine SQLAlchemy era criado com a URL padrão sqlite:///./checking.db sempre que arquivos de teste de serviços/modelos (como 	est_accident_lifecycle.py) eram importados primeiro pelo pytest — antes de 	est_admin_accidents.py ter a chance de setar DATABASE_URL. Isso fazia os testes de router rodarem contra o banco de desenvolvimento em vez do banco de testes.

O 	ests/conftest.py (novo arquivo) seta todas as variáveis de ambiente necessárias com os.environ.setdefault(...) **antes** que qualquer módulo da aplicação seja importado, pois o pytest processa conftest.py antes de coletar/importar os módulos de teste.

## 4) Arquivo alterado: 	ests/routers/test_admin_accidents.py

### Correções de bugs

- **aise_server_exceptions**: Revertido de True para False em _logged_in_client() (linha que criava TestClient) — estava True como artefato de debugging, causando propagação de exceções internas em vez de retorno de HTTP 500.
- **Import lazy removido**: rom sistema.app.models import AccidentArchive dentro de _insert_archive() removido; AccidentArchive agora importado no topo junto com os demais modelos.
- **_close_all_accidents() estendida**: Além de fechar acidentes abertos, agora também deleta todas as linhas de AccidentArchive, AccidentVideoUpload e AccidentUserReport. Isso previne acúmulo de linhas órfãs entre execuções de testes, que causava UNIQUE constraint failed: accident_user_reports.accident_id, accident_user_reports.user_id quando um acidente com ID reutilizado tentava inserir relatórios para usuários já presentes.

### Import adicionado ao topo

`python
from sistema.app.models import Accident, AccidentArchive, AccidentUserReport, AccidentVideoUpload, AdminUser, Project, User
`

### 5 testes D5 adicionados

| Teste | Descrição |
|---|---|
| 	est_delete_forbidden_for_non_perfil_9 | Admin perfil=19 → 403 |
| 	est_delete_404_when_unknown | ID inexistente → 404 |
| 	est_delete_409_when_active | Acidente ativo (sem closed_at) → 409 |
| 	est_delete_removes_cascade | 200 + acidente removido do banco confirmado |
| 	est_delete_calls_delete_prefix | delete_prefix chamado com prefixo contendo o número formatado do acidente (ex.: "0042") |

### Helpers de suporte adicionados

- _delete_accident_url(accident_id) — monta a URL do endpoint DELETE.
- _logged_in_perfil9_client() — cria/reusa usuário D4P9 com perfil=9 e retorna TestClient autenticado.

## 5) Arquivo deletado

- 	ests/debug_failure.py — script temporário de debugging removido.

## 6) Verificações executadas

- Combinação antes falha 	est_open_accident_creates_with_number_zero + 	est_open_creates_when_none + 	est_open_publishes_brokers → **3 passed**
- python -m pytest tests/models tests/schemas tests/services tests/routers -q → **88 passed** (era 83 antes do D5)

## 7) Arquivos alterados nesta tarefa

- sistema/app/routers/admin.py (editado — import 
otify_web_check_data_changed + stub delete_prefix + endpoint DELETE)
- sistema/app/models.py (editado — import elationship + 3 relacionamentos cascade em Accident)
- 	ests/conftest.py (novo — bootstrap de variáveis de ambiente de teste)
- 	ests/routers/test_admin_accidents.py (editado — correções de bugs + 5 testes D5)
- 	ests/debug_failure.py (deletado)
- docs/temp000A.md (atualizado com este resumo)

---

# Task D6 — Resumo detalhado da implementação concluída

A implementação do **Bloco D / Task D6** adicionou dois endpoints auxiliares para o wizard de abertura do Modo Acidente, retornando a lista de projetos e as localizações filtradas por projeto.

## 1) Arquivo alterado: `sistema/app/routers/admin.py`

### Novos imports de schema

Adicionados à linha de import de schemas:
- `AccidentProjectOption`
- `AccidentLocationOption`

### Novo import de modelo

Adicionado `ManagedLocation` ao import de modelos.

### Endpoint GET /accidents/wizard/projects (linha ~2146)

```python
@router.get("/accidents/wizard/projects", response_model=list[AccidentProjectOption], dependencies=[Depends(require_full_admin_session)])
def list_accident_wizard_projects(db: Session = Depends(get_db)) -> list[AccidentProjectOption]:
    return [AccidentProjectOption(id=p.id, name=p.name) for p in list_projects(db)]
```

- Requer sessão admin completa (`require_full_admin_session`).
- Retorna todos os projetos via helper `list_projects(db)` já existente no router.
- Mapeia cada projeto para `AccidentProjectOption(id, name)`.

### Endpoint GET /accidents/wizard/locations (linha ~2151)

```python
@router.get("/accidents/wizard/locations", response_model=list[AccidentLocationOption], dependencies=[Depends(require_full_admin_session)])
def list_accident_wizard_locations(project_id: int = Query(...), db: Session = Depends(get_db)) -> list[AccidentLocationOption]:
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

- Requer parâmetro de query `project_id`.
- 404 se projeto não existir.
- Filtra `ManagedLocation` pelo campo `projects_json` (array JSON de nomes de projetos) comparando `project.name in projects`.
- Retorna `AccidentLocationOption(id, name, registered=True)` para cada localização correspondente.

### Posicionamento no arquivo

Os dois endpoints foram inseridos **antes** do stub `delete_prefix` e do endpoint `DELETE /accidents/{accident_id}`, garantindo que rotas estáticas (`/wizard/projects`, `/wizard/locations`) precedam a rota parametrizada (`/{accident_id}`) na ordem de declaração do router.

## 2) Arquivo alterado: `tests/routers/test_admin_accidents.py`

### Import adicionado

```python
from sistema.app.models import Accident, AccidentArchive, AccidentUserReport, AccidentVideoUpload, AdminUser, ManagedLocation, Project, User
```

`ManagedLocation` adicionado para o helper de criação de localizações gerenciadas.

### Constantes de URL adicionadas

```python
WIZARD_PROJECTS_URL = "/api/admin/accidents/wizard/projects"
WIZARD_LOCATIONS_URL = "/api/admin/accidents/wizard/locations"
```

### Helper adicionado: `_insert_managed_location(db, name, projects)`

Insere um `ManagedLocation` no banco com `projects_json` serializado, para uso nos testes D6.

### 3 testes D6 adicionados

| Teste | Descrição |
|---|---|
| `test_wizard_lists_all_projects` | GET /wizard/projects → lista inclui o projeto criado via `_ensure_project` |
| `test_wizard_locations_filtered_by_project` | GET /wizard/locations?project_id=X → inclui locais vinculados e exclui não-vinculados; `registered=True` |
| `test_wizard_locations_404_for_unknown_project` | project_id=999999999 → 404 |

## 3) Schemas utilizados (já existentes em `sistema/app/schemas.py`)

- `AccidentProjectOption` (linha ~4298): `id: int`, `name: str`
- `AccidentLocationOption` (linha ~4303): `id: int`, `name: str`, `registered: bool`

## 4) Verificações executadas

- `python -m pytest tests/routers/test_admin_accidents.py -v -k "wizard"` → **3 passed**
- `python -m pytest tests/models tests/schemas tests/services tests/routers -q` → **91 passed**

## 5) Arquivos alterados nesta tarefa

- `sistema/app/routers/admin.py` (editado — imports + 2 endpoints wizard)
- `tests/routers/test_admin_accidents.py` (editado — import ManagedLocation + helper + 3 testes D6)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task E1 — Resumo detalhado da implementação concluída

A implementação do **Bloco E / Task E1** adicionou dois endpoints ao router `web_check` para que o usuário web possa consultar o estado do Modo Acidente e abri-lo diretamente pelo portal web.

## 1) Arquivo alterado: `sistema/app/routers/web_check.py`

### Novos imports de modelo

```python
from ..models import Accident, AccidentUserReport, AdminAccessRequest, ...
```

`Accident` e `AccidentUserReport` adicionados ao import de modelos (linha 10).

### Novos imports de schema

```python
WebAccidentOpenRequest,
WebAccidentStateResponse,
WebAccidentUserReport,
```

Adicionados ao bloco `from ..schemas import (...)`.

### Novos imports de serviço

```python
from ..services.accident_lifecycle import (
    AccidentAlreadyActiveError,
    list_active_accident,
    open_accident,
)
from ..services.accident_numbering import format_accident_number
```

Adicionados após o bloco `from ..services.admin_updates import (...)`.

### Endpoint GET /check/accident/state (linha ~877)

```python
@router.get("/check/accident/state", response_model=WebAccidentStateResponse)
def get_web_accident_state(request, chave, db) -> WebAccidentStateResponse
```

- Requer sessão web autenticada + chave correspondente (via `_require_matching_authenticated_web_user`).
- Sem acidente ativo → `{"is_active": false}`.
- Com acidente ativo → retorna `accident_number_label`, `project_name`, `location_name` e `current_user_report` com `zone`/`status`/`reported_at` do relatório do usuário atual (se existir).

### Endpoint POST /check/accident/open (linha ~910)

```python
@router.post("/check/accident/open", response_model=WebAccidentStateResponse)
def open_web_accident(payload, request, db) -> WebAccidentStateResponse
```

- Requer sessão web autenticada + chave correspondente no payload.
- Chama `open_accident(..., origin="web", opened_by_user_id=user.id, reporter_zone, reporter_status)`.
- `AccidentAlreadyActiveError` → 409 "Outro usuario ja reportou um acidente."
- Em caso de sucesso, delega a `get_web_accident_state` para retornar o estado atualizado.

## 2) Arquivo criado: `tests/routers/test_web_accidents.py`

6 testes obrigatórios:

| Teste | Descrição |
|---|---|
| `test_state_requires_session` | Sem sessão web → 401 |
| `test_state_returns_inactive_when_none` | Sem acidente ativo → `is_active=False`, sem campos extras |
| `test_state_returns_user_report_when_active` | Acidente aberto via `/open` → state retorna `is_active=True`, `current_user_report.zone="safety"`, `current_user_report.status="ok"` |
| `test_open_creates_with_origin_web` | Acidente criado com `origin="web"` e `opened_by_user_id` preenchido no banco |
| `test_open_returns_409_when_active` | Segundo `/open` com acidente já ativo → 409 |
| `test_open_publishes_brokers` | `notify_admin_data_changed` e `notify_web_check_data_changed` chamados uma vez cada |

### Infraestrutura de teste

- Usuário web criado com `chave="E1WB"`, `senha="WebE1Test!"`, `checkin=True`, `perfil=1`.
- Login via `POST /api/web/auth/login` com cookies persistentes no `TestClient`.
- `_close_all_accidents(db)` limpa acidentes + filhos antes de cada teste.
- Brokers mockados via `patch("sistema.app.services.accident_lifecycle.notify_*")`.

## 3) Verificações executadas

- `python -m pytest tests/routers/test_web_accidents.py -v` → **6 passed**
- `python -m pytest tests/models tests/schemas tests/services tests/routers -q` → **97 passed**

## 4) Arquivos alterados nesta tarefa

- `sistema/app/routers/web_check.py` (editado — imports + 2 endpoints E1)
- `tests/routers/test_web_accidents.py` (novo — 6 testes E1)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task E2 — Resumo detalhado da implementação concluída

A implementação do **Bloco E / Task E2** adicionou o endpoint `POST /api/web/check/accident/report` ao router `web_check`, permitindo ao usuário web enviar seu status (zona/condição) durante um acidente ativo.

## 1) Arquivo alterado: `sistema/app/routers/web_check.py`

### Imports adicionados

- `BackgroundTasks` adicionado ao import de `fastapi` (linha 4).
- `WebAccidentReportRequest` adicionado ao bloco `from ..schemas import (...)`.
- `upsert_user_safety_report` adicionado ao bloco `from ..services.accident_lifecycle import (...)`.

### Stub `queue_help_request_emails` (linha ~927)

```python
def queue_help_request_emails(accident_id: int, requester_user_id: int) -> None:
    # TODO Task G3: send help-request notification emails to admins.
    pass
```

Stub adicionado antes do endpoint, pois a implementação real virá na Task G3.

### Endpoint POST /check/accident/report (linha ~934)

```python
@router.post("/check/accident/report", response_model=WebAccidentStateResponse)
def report_web_accident_status(payload, request, background_tasks, db) -> WebAccidentStateResponse
```

- Requer sessão web autenticada com chave correspondente.
- 409 se não há acidente ativo.
- Chama `upsert_user_safety_report(db, accident=active, user=user, zone=payload.zone, status=payload.status)`.
- O segundo valor de retorno (`fired_help`) indica se houve transição de non-help → help.
- Se `fired_help=True`, agenda `queue_help_request_emails` via `background_tasks.add_task(...)`.
- Retorna estado atualizado via `get_web_accident_state`.

## 2) Arquivo alterado: `tests/routers/test_web_accidents.py`

Helper adicionado: `_open_accident_via_api(client, proj_id)` — abre acidente via `/open` com brokers mockados.

4 testes E2 adicionados:

| Teste | Descrição |
|---|---|
| `test_report_409_when_no_active` | Sem acidente ativo → 409 |
| `test_report_upserts` | Dois reports → segundo atualiza zone/status do `current_user_report` |
| `test_report_schedules_email_on_help_transition` | Transição ok→help → `queue_help_request_emails` chamada uma vez |
| `test_report_does_not_schedule_email_on_repeat_help` | help→help → `queue_help_request_emails` NOT called |

## 3) Verificações executadas

- `python -m pytest tests/routers/test_web_accidents.py -v` → **10 passed** (6 E1 + 4 E2)
- `python -m pytest tests/models tests/schemas tests/services tests/routers -q` → **101 passed**

## 4) Arquivos alterados nesta tarefa

- `sistema/app/routers/web_check.py` (editado — imports + stub + endpoint E2)
- `tests/routers/test_web_accidents.py` (editado — helper + 4 testes E2)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task E3 — Resumo detalhado da implementação concluída

A implementação do **Bloco E / Task E3** adicionou o endpoint `POST /api/web/check/accident/video` ao router `web_check`, permitindo ao usuário web enviar um vídeo gravado durante um acidente ativo. O endpoint é assíncrono (usa `async def`) por necessidade de `await` no upload.

## 1) Arquivo alterado: `sistema/app/routers/web_check.py`

### Imports adicionados

- `File`, `Form`, `UploadFile` adicionados ao import de `fastapi` (linha 4).
- `AccidentVideoUploadResponse` adicionado ao bloco `from ..schemas import (...)`.
- `attach_video_upload` adicionado ao bloco `from ..services.accident_lifecycle import (...)`.
- `format_accident_number` adicionado ao import de `from ..services.accident_numbering import (...)`.

### Constantes adicionadas (~linha 107)

```python
MAX_VIDEO_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_VIDEO_TYPES = {"video/webm", "video/mp4", "video/quicktime"}
```

### Stub `stream_upload_to_storage` (~linha 956)

```python
async def stream_upload_to_storage(
    object_key: str,
    upload_file: UploadFile,
    content_type: str,
    max_bytes: int,
) -> tuple[int, str]:
    # TODO Task F1: stream to object storage (Spaces/S3).
    data = await upload_file.read()
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="Video excede o tamanho maximo permitido.")
    public_url = f"http://localhost/dev-storage/{object_key}"
    return len(data), public_url
```

Grava em memória (modo dev). Retorna `(size_bytes, public_url)`. Lança 413 se arquivo exceder o limite. Será substituído pela implementação real na Task F1.

### Endpoint POST /check/accident/video (~linha 974)

```python
@router.post("/check/accident/video", response_model=AccidentVideoUploadResponse)
async def upload_accident_video(
    request: Request,
    chave: str = Form(...),
    idempotency_key: str = Form(..., min_length=8, max_length=80),
    duration_seconds: int | None = Form(None),
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> AccidentVideoUploadResponse:
```

- Requer sessão web autenticada com chave correspondente.
- 409 se não há acidente ativo.
- 415 se `video.content_type` não está em `ALLOWED_VIDEO_TYPES` (`video/webm`, `video/mp4`, `video/quicktime`).
- `accident_label` gerado via `format_accident_number(active.accident_number)`.
- `object_key = f"accidents/{accident_label}/{user.chave}/{safe_key}.{ext}"` onde `safe_key` substitui `/` e espaços por `_`.
- Upload via `await stream_upload_to_storage(...)` (stub dev por ora).
- Chama `attach_video_upload(db, ...)` — idempotente por `idempotency_key`; retorna row existente se já houver.
- Retorna `AccidentVideoUploadResponse(video_id, public_url, captured_at)`.

## 2) Arquivo alterado: `tests/routers/test_web_accidents.py`

Helpers adicionados:
- `_make_video_form(chave, idempotency_key, content, content_type, duration_seconds)` — monta dict de multipart para `client.post(files=...)`.
- `_open_and_get_client(db)` — fecha acidentes existentes, abre novo, retorna `(client, chave)`.

Constante adicionada: `VIDEO_URL = "/api/web/check/accident/video"`.

5 testes E3 adicionados:

| Teste | Descrição |
|---|---|
| `test_video_requires_active_accident` | Sem acidente ativo → 409 |
| `test_video_rejects_unsupported_type` | `content_type="image/png"` → 415 |
| `test_video_rejects_oversized` | Arquivo de 50 MB + 1 byte → 413 |
| `test_video_upload_success` | Upload válido → 200 com `video_id`, `public_url`, `captured_at` |
| `test_video_upload_idempotent` | Mesmo `idempotency_key` → segundo POST retorna mesmo `video_id` |

## 3) Dependência adicionada: `requirements.txt`

- `python-multipart>=0.0.18` adicionado (necessário para FastAPI processar `Form` e `File` parameters).

## 4) Verificações executadas

- `python -m pytest tests/routers/test_web_accidents.py -v -k "video"` → **5 passed**
- `python -m pytest tests/models tests/schemas tests/services tests/routers -q` → **106 passed**

## 5) Arquivos alterados nesta tarefa

- `sistema/app/routers/web_check.py` (editado — imports + constantes + stub `stream_upload_to_storage` + endpoint E3)
- `tests/routers/test_web_accidents.py` (editado — helpers + constante + 5 testes E3)
- `requirements.txt` (editado — `python-multipart` adicionado)
- `docs/temp000A.md` (atualizado com este resumo)

---

# Task E4 — Resumo detalhado da implementação concluída

A implementação do **Bloco E / Task E4** adicionou dois endpoints auxiliares para o wizard do usuário web: listagem de projetos e localizações filtradas por projeto.

## 1) Arquivo alterado: `sistema/app/routers/web_check.py`

### Novos imports de schema

Adicionados ao bloco `from ..schemas import (...)`:
- `AccidentLocationOption`
- `AccidentProjectOption`

(Modelos `ManagedLocation`, `Project`, função `list_projects`, `select` e `json` já estavam importados.)

### Endpoint GET /check/accident/wizard/projects

```python
@router.get("/check/accident/wizard/projects", response_model=list[AccidentProjectOption])
def list_web_accident_projects(
    request: Request,
    chave: str = Query(...),
    db: Session = Depends(get_db),
) -> list[AccidentProjectOption]:
```

- Requer sessão web autenticada com chave correspondente (`_require_matching_authenticated_web_user`).
- Retorna todos os projetos via `list_projects(db)`.
- Mapeia cada projeto para `AccidentProjectOption(id, name)`.

### Endpoint GET /check/accident/wizard/locations

```python
@router.get("/check/accident/wizard/locations", response_model=list[AccidentLocationOption])
def list_web_accident_locations(
    request: Request,
    chave: str = Query(...),
    project_id: int = Query(...),
    db: Session = Depends(get_db),
) -> list[AccidentLocationOption]:
```

- Requer parâmetro de query `project_id`.
- 404 se projeto não existir.
- Itera todos os `ManagedLocation`, parseia `projects_json`, inclui apenas os que contêm `project.name`.
- Retorna `AccidentLocationOption(id, name, registered=True)` para cada localização correspondente.

## 2) Arquivo alterado: `tests/routers/test_web_accidents.py`

### Import adicionado

`ManagedLocation` adicionado ao import de modelos.

### Constantes adicionadas

```python
WEB_WIZARD_PROJECTS_URL = "/api/web/check/accident/wizard/projects"
WEB_WIZARD_LOCATIONS_URL = "/api/web/check/accident/wizard/locations"
```

### Helpers adicionados

- `_ensure_e4_project(db)` — cria/reutiliza projeto `E4PROJ`.
- `_ensure_e4_managed_location(db, name, linked_project)` — cria/atualiza `ManagedLocation` com campos obrigatórios (`latitude=1.0`, `longitude=103.0`, `tolerance_meters=50`, timestamps) e `projects_json` configurado.

### 3 testes E4 adicionados

| Teste | Descrição |
|---|---|
| `test_web_wizard_projects_requires_session` | Sem sessão → 401 |
| `test_web_wizard_projects_returns_all` | Usuário autenticado → lista inclui projeto `E4PROJ` |
| `test_web_wizard_locations_filtered_by_project` | Localização vinculada ao projeto → incluída; não-vinculada → excluída; `registered=True` verificado |

## 3) Verificações executadas

- `python -m pytest tests/routers/test_web_accidents.py -v -k "wizard"` → **3 passed**
- `python -m pytest tests/models tests/schemas tests/services tests/routers -q` → **109 passed** (era 106 antes do E4)

## 4) Arquivos alterados nesta tarefa

- `sistema/app/routers/web_check.py` (editado — imports + 2 endpoints wizard)
- `tests/routers/test_web_accidents.py` (editado — import + helpers + constantes + 3 testes E4)
- `docs/temp000A.md` (atualizado com este resumo)


---

# Task F1 — Resumo detalhado da implementação concluída

A implementação do **Bloco F / Task F1** criou o serviço `object_storage.py` com suporte a DigitalOcean Spaces (via boto3) e fallback local para desenvolvimento.

## 1) Arquivo editado: `sistema/app/core/config.py`

6 novos campos opcionais adicionados à classe `Settings`: `do_spaces_endpoint_url`, `do_spaces_region`, `do_spaces_bucket`, `do_spaces_access_key`, `do_spaces_secret_key`, `do_spaces_public_base_url`. Todos com default `None`.

## 2) Arquivo criado: `sistema/app/services/object_storage.py`

- `_use_remote()` — retorna `True` se bucket + credenciais configurados
- `_make_boto3_client()` — cria cliente boto3 com credenciais DO Spaces (lazy import)
- `upload_stream(...)` — upload de stream `IO[bytes]`; retorna URL pública (remota ou `/api/admin/accidents/local-asset/...` em dev)
- `generate_presigned_url(...)` — URL assinada (remoto) ou local-asset URL (dev)
- `delete_object(...)` — remove objeto único
- `delete_prefix(...)` — remove recursivamente todos objetos com prefixo; retorna contagem de arquivos removidos
- `stream_upload_to_storage(...)` — `async`; lê `UploadFile` em chunks de 1 MB, lança HTTP 413 se exceder `max_bytes`, faz upload via `upload_stream`

## 3) Arquivo editado: `sistema/app/routers/admin.py`

- Stub `generate_presigned_url` substituído por delegação real para `object_storage.generate_presigned_url`.
- Stub `delete_prefix` substituído por delegação real para `object_storage.delete_prefix`.
- Novo endpoint `GET /accidents/local-asset/{path:path}` (dev-only): serve arquivos do disco local via `FileResponse`; retorna 404 em produção quando `_use_remote() == True`.

## 4) Arquivo editado: `sistema/app/routers/web_check.py`

- Stub local `stream_upload_to_storage` substituído por delegação para `object_storage.stream_upload_to_storage`.

## 5) Arquivo editado: `requirements.txt`

- `boto3>=1.34` adicionado.

## 6) Arquivo criado: `tests/services/test_object_storage.py`

6 testes obrigatórios:

| Teste | Descrição |
|---|---|
| `test_upload_local_writes_file` | `upload_stream` grava bytes corretos no disco |
| `test_upload_local_returns_path_url` | URL retornada é `/api/admin/accidents/local-asset/...` |
| `test_delete_prefix_removes_all` | `delete_prefix` apaga 3 arquivos e retorna contagem=3 |
| `test_stream_upload_rejects_oversized` | Arquivo >max_bytes levanta HTTP 413 |
| `test_generate_presigned_url_local_falls_back_to_path` | Sem credenciais → URL local retornada |
| `test_remote_mode_uses_boto3_mock` | Com credenciais mockadas → `upload_fileobj` chamado; URL correta |

Todos os testes usam `unittest.mock.patch` para isolar `settings` por teste via `tmp_path`; sem dependência de moto.

## 7) Verificações executadas

- `python -m pytest tests/services/test_object_storage.py -v` → **6 passed**
- `python -m pytest tests/models tests/schemas tests/services tests/routers -q` → **115 passed** (era 109 antes do F1)

## 8) Arquivos alterados nesta tarefa

- `sistema/app/core/config.py` (editado — 6 novos campos DO Spaces)
- `sistema/app/services/object_storage.py` (novo — serviço completo)
- `sistema/app/routers/admin.py` (editado — stubs substituídos + endpoint local-asset)
- `sistema/app/routers/web_check.py` (editado — stub `stream_upload_to_storage` substituído)
- `requirements.txt` (editado — `boto3>=1.34` adicionado)
- `tests/services/test_object_storage.py` (novo — 6 testes)
- `docs/temp000A.md` (atualizado com este resumo)


---

# Task F2 — Resumo detalhado da implementação concluída

A implementação do **Bloco F / Task F2** criou o serviço `accident_archive_builder.py`, responsável por gerar o arquivo XLSX com a tabela "Situação de Pessoal" e o ZIP com vídeos, fazer upload ao storage, e persistir o `AccidentArchive`.

## 1) Arquivo criado: `sistema/app/services/accident_archive_builder.py`

### Constantes
- `COLUMN_ORDER` — lista de 9 cabeçalhos do XLSX: Horário, Nome, Chave, Projetos, Local, Zona de, Situação, Contato, Registros.

### Funções internas
- `_slugify(value)` — sanitiza strings para nomes de arquivo seguros (alfanumérico + `_-`, máx 60 chars).
- `_build_xlsx(snapshot_rows, video_files_by_user)` — gera BytesIO com workbook openpyxl:
  - Título da planilha: `"Situacao de Pessoal"`.
  - Header row com `COLUMN_ORDER`.
  - Uma linha por `SituacaoPessoalRow`; coluna Registros com caminhos `Registros/<filename>`, `wrap_text=True`, hyperlink para o primeiro vídeo.
- `_read_video_bytes(object_key)` — lê bytes brutos de um vídeo via storage (boto3 em produção, disco local em dev).

### Função principal
`build_and_attach_archive_for_accident(accident_id)`:
1. Abre sessão via `SessionLocal()`.
2. Carrega `Accident` e todos os `AccidentVideoUpload` do acidente.
3. Mapeia `user_id → [filenames]` e baixa bytes de cada vídeo via `_read_video_bytes`.
4. Gera XLSX via `_build_xlsx`.
5. Constrói ZIP com `zipfile.ZIP_DEFLATED`: `<NNNN>.xlsx` na raiz + `Registros/<filename>` para cada vídeo.
6. Faz upload do XLSX e do ZIP via `upload_stream`.
7. Cria registro `AccidentArchive` com `snapshot_json`, chaves de objeto, `size_bytes`, `generated_at`.
8. Atualiza `accident.archive_object_key = zip_key`.
9. Publica `notify_admin_data_changed("accident_closed", metadata={"accident_id": ..., "archive_ready": True})`.

Chaves de objeto seguem o padrão `accidents/<NNNN>/archive/<NNNN>.xlsx` / `.zip`.

## 2) Arquivo editado: `sistema/app/routers/admin.py`

Stub `build_and_attach_archive_for_accident` substituído por delegação real:
```python
def build_and_attach_archive_for_accident(accident_id: int) -> None:
    from ..services.accident_archive_builder import (
        build_and_attach_archive_for_accident as _build,
    )
    _build(accident_id)
```

## 3) Arquivo criado: `tests/services/test_accident_archive_builder.py`

7 testes:

| Teste | Descrição |
|---|---|
| `test_archive_zip_contains_xlsx` | ZIP gerado contém `<NNNN>.xlsx` na raiz |
| `test_archive_zip_contains_videos_subfolder` | ZIP contém `Registros/<user_id>-<slug>.mp4` |
| `test_xlsx_columns_match_spec` | Header row do XLSX bate exatamente com `COLUMN_ORDER` |
| `test_xlsx_handles_zero_videos` | XLSX sem vídeos tem célula Registros vazia |
| `test_xlsx_filename_uses_4_digit_format` | Nome do XLSX usa número zero-padded de 4 dígitos |
| `test_archive_record_persists` | `AccidentArchive` criado no banco; `accident.archive_object_key` atualizado |
| `test_archive_publishes_ready_event` | `notify_admin_data_changed` chamado com `archive_ready=True` |

Infraestrutura de mock:
- `SessionLocal` mockado com `_CommitOnlySession` (commit sem close) nos testes que precisam inspecionar o banco após a função.
- `_use_remote` mockado para forçar modo local.
- `object_storage.settings` mockado via `MagicMock` com `tmp_path`.

## 4) Verificações executadas

- `python -m pytest tests/services/test_accident_archive_builder.py -v` → **7 passed**
- `python -m pytest tests/models tests/schemas tests/services tests/routers -q` → **122 passed** (era 115 antes do F2)

## 5) Arquivos alterados nesta tarefa

- `sistema/app/services/accident_archive_builder.py` (novo)
- `sistema/app/routers/admin.py` (editado — stub substituído)
- `tests/services/test_accident_archive_builder.py` (novo — 7 testes)
- `docs/temp000A.md` (atualizado)


---

## ✅ Task F3 — Concluído

### Resumo detalhado

**Objetivo:** Substituir o stub local de `build_and_attach_archive_for_accident` no router admin pelo import real da Task F2.

### Arquivo alterado: `sistema/app/routers/admin.py`

- Removida a função stub local de 5 linhas que fazia lazy-import de `accident_archive_builder` internamente:
  ```python
  # removido:
  def build_and_attach_archive_for_accident(accident_id: int) -> None:
      from ..services.accident_archive_builder import build_and_attach_archive_for_accident as _impl
      _impl(accident_id)
  ```
- Adicionado import top-level junto aos demais imports de services:
  ```python
  from ..services.accident_archive_builder import build_and_attach_archive_for_accident
  ```
- O endpoint `POST /accidents/close` continua chamando `background_tasks.add_task(build_and_attach_archive_for_accident, closed.id)` sem alteração — apenas o símbolo agora é o real.
- O teste existente `test_close_schedules_archive_build` (que usa `patch("sistema.app.routers.admin.build_and_attach_archive_for_accident")`) continua funcionando porque `patch` substitui o nome no namespace do módulo de qualquer forma.

### Arquivo alterado: `tests/routers/test_admin_accidents.py`

Adicionado ao final do arquivo:

- **`test_close_admin_accident_calls_real_archive_builder(tmp_path)`** — teste de integração que:
  1. Abre um acidente via `_open_accident`.
  2. Faz `client.post("/api/admin/accidents/close")` sem mock de `build_and_attach_archive_for_accident` (builder real executado).
  3. Mocka apenas:
     - `sistema.app.services.accident_lifecycle.notify_admin_data_changed` e `notify_web_check_data_changed` (evita threads SSE)
     - `sistema.app.services.accident_archive_builder.notify_admin_data_changed` (idem)
     - `sistema.app.services.object_storage.settings` com `MagicMock` apontando `event_archives_dir=tmp_path` (sem disco real do sistema)
     - `sistema.app.services.accident_archive_builder._use_remote` retornando `False` (sem chamadas ao DO Spaces)
  4. Após o response 200, consulta o DB e verifica:
     - `AccidentArchive` row existe para o `accident_id`
     - `zip_object_key` não é `None`
     - `xlsx_object_key` não é `None`
     - `size_bytes > 0`
  - Como `BackgroundTasks` executa sincronamente no `TestClient`, o arquivo já foi criado quando o response chega.

### Resultado de testes

- `tests/routers/test_admin_accidents.py`: **26 passed** (era 25 + novo teste)
- `tests/models/ + tests/services/ + tests/routers/test_admin_accidents.py + tests/routers/test_web_accidents.py`: **109 passed**
- Falhas no suite completo são em `test_transport_ai_*` — pré-existentes, não relacionadas a este bloco.

### Commit

`feat: Promote build_and_attach_archive_for_accident to top-level import in admin router (Task F3)`


---

# Task G1 — Resumo detalhado da implementação concluída

A implementação do **Bloco G / Task G1** adicionou 11 settings SMTP ao módulo de configuração central.

## 1) Arquivo alterado: `sistema/app/core/config.py`

Adicionado bloco de 11 campos ao final da classe `Settings`, após a seção DO Spaces:

```python
# SMTP e-mail delivery
smtp_host: str | None = None
smtp_port: int = 587
smtp_user: str | None = None
smtp_password: str | None = None
smtp_from_email: str | None = None
smtp_from_name: str = "CheckCheck"
smtp_use_tls: bool = False
smtp_use_starttls: bool = True
smtp_timeout_seconds: int = 30
smtp_max_retries: int = 3
smtp_accident_notify_email: str | None = None
```

- `smtp_host` é `None` por default — indica SMTP desabilitado.
- Variáveis de ambiente (maiúsculas) são lidas automaticamente pelo `pydantic-settings` (ex: `SMTP_HOST`, `SMTP_PORT`).
- `smtp_use_tls=False` + `smtp_use_starttls=True` é o padrão seguro para porta 587 (STARTTLS).
- `smtp_accident_notify_email` é o endereço de destino para notificações de acidente (usado na Task G3).

## 2) Arquivo criado: `tests/core/__init__.py`

Arquivo vazio para tornar `tests/core/` um pacote Python.

## 3) Arquivo criado: `tests/core/test_smtp_settings.py`

Dois testes:

| Teste | Descrição |
|---|---|
| `test_smtp_defaults_to_disabled` | Instancia `Settings()` sem env vars e verifica todos os 11 campos com seus defaults (`smtp_host=None`, `smtp_port=587`, `smtp_use_tls=False`, `smtp_use_starttls=True`, etc.) |
| `test_smtp_env_overrides` | Usa `monkeypatch.setenv` para definir os 11 `SMTP_*` vars e instancia `Settings(_env_file=None)` — verifica que todos os valores são lidos corretamente |

## 4) Verificações executadas

- `python -c "from sistema.app.core.config import settings; print(settings.smtp_host)"` → `None`
- `python -m pytest tests/core/test_smtp_settings.py -v` → **2 passed**

## 5) Commit

`feat: Add SMTP configuration settings to config.py (Task G1)`


---

# Task G2 — Resumo detalhado da implementação concluída

A implementação do **Bloco G / Task G2** criou o módulo de templates de e-mail.

## 1) Arquivo criado: `sistema/app/services/email_templates.py`

Função única exportada:

```python
def render_help_request_email(
    *,
    recipient_name: str,
    requester_name: str,
    requester_chave: str,
    project_name: str,
    location_name: str,
) -> tuple[str, str]:
```

- Retorna `(subject, body)` como strings puras (sem HTML).
- `subject` fixo: `"(CHECKING) PEDIDO DE SOCORRO"`.
- `body` segue exatamente o texto especificado no descritivo item 5.2 Ação 3.

## 2) Arquivo criado: `tests/services/test_email_templates.py`

4 testes:

| Teste | Descrição |
|---|---|
| `test_subject_matches_spec` | `subject == "(CHECKING) PEDIDO DE SOCORRO"` |
| `test_body_includes_recipient_name` | `"Prezado Admin Silva,"` presente no body |
| `test_body_includes_project_and_location` | `project_name`, `location_name`, `chave` e `requester_name` presentes |
| `test_body_confirms_help` | `"AJUDA IMEDIATA"`, `"CONFIRMADO"` e `"Checking App"` presentes |

## 3) Verificações executadas

- `python -m pytest tests/services/test_email_templates.py -v` → **4 passed**

## 4) Commit

`feat: Add email_templates service with render_help_request_email (Task G2)`


---

# Task G3 — Resumo detalhado da implementação concluída

A implementação do **Bloco G / Task G3** criou o serviço de fila e entrega de e-mails SMTP.

## 1) Arquivo criado: `sistema/app/services/email_sender.py`

Três funções exportadas:

### `queue_help_request_emails(*, accident_id, requester_user_id)`
- Abre `SessionLocal` e carrega `Accident` + `User` (requester).
- Busca todos os `User` que possuem `UserProjectMembership` no projeto cujo `name` bate com `accident.project_name_snapshot`.
- Para cada destinatário:
  - Chama `render_help_request_email(...)` para gerar subject + body.
  - Sem e-mail: persiste `EmailDeliveryLog` com `delivery_status="failed"`, `error_message="Missing recipient email"`.
  - Com e-mail: persiste `EmailDeliveryLog` com `delivery_status="queued"`, coleta `log.id`.
- Chama `deliver_pending_emails(log_ids)` para entrega imediata.

### `deliver_pending_emails(log_ids)`
- Se `settings.smtp_host is None`: retorna sem fazer nada (SMTP desabilitado).
- Para cada log_id: carrega `EmailDeliveryLog`, tenta `_send_via_smtp` até `smtp_max_retries` vezes.
- Sucesso: `delivery_status="sent"`, `sent_at=now_sgt()`.
- Falha após todas tentativas: `delivery_status="failed"`, `retry_count=N`, `error_message=str(exc)[:1000]`.

### `_send_via_smtp(log)`
- Monta `EmailMessage` com subject, from (via `smtp_from_name` + `smtp_from_email`), to, body.
- `smtp_use_tls=True`: usa `smtplib.SMTP_SSL` (porta 465, SSL wrapping).
- `smtp_use_tls=False, smtp_use_starttls=True`: usa `smtplib.SMTP` + `server.starttls()`.
- Login opcional via `smtp_user` + `smtp_password`.

**Nota:** Os nomes de campo usados (`smtp_from_name`, `smtp_from_email`, `smtp_user`, `smtp_use_tls`, `smtp_use_starttls`, `smtp_timeout_seconds`) correspondem ao que foi implementado na Task G1, não ao stub do spec (que usava `smtp_sender_name`, `smtp_username`, etc.).

## 2) Arquivo editado: `sistema/app/routers/web_check.py`

- Adicionado import top-level: `from ..services.email_sender import queue_help_request_emails`
- Removida a função stub local de 3 linhas (`def queue_help_request_emails(...): pass`).
- O endpoint `/check/accident/report` continua chamando `background_tasks.add_task(queue_help_request_emails, ...)` sem alteração.

## 3) Arquivo criado: `tests/services/test_email_help_request.py`

8 testes, todos usando SQLite `tmp_path` + `_CommitOnlySession` para injetar sessão no service:

| Teste | Descrição |
|---|---|
| `test_queue_creates_log_per_recipient` | 3 membros com email → 3 logs `queued` |
| `test_queue_logs_missing_email_as_failed` | User sem email → log `failed` + `"Missing recipient email"` |
| `test_queue_idempotent_by_status_transition` | 2 chamadas → 2 conjuntos de logs; sem erro |
| `test_send_smtp_disabled_keeps_queued` | `smtp_host=None` → row permanece `queued` |
| `test_send_smtp_success_marks_sent` | Mock SMTP sem erro → `delivery_status="sent"`, `sent_at` preenchido |
| `test_send_smtp_failure_retries_and_fails` | `send_message` raises → `retry_count=3`, `delivery_status="failed"` |
| `test_send_uses_ssl_when_configured` | `smtp_use_tls=True` → `smtplib.SMTP_SSL` chamado; `smtplib.SMTP` não |
| `test_send_uses_starttls_when_configured` | `smtp_use_starttls=True` → `server.starttls()` chamado; `SMTP_SSL` não |

## 4) Verificações executadas

- `python -m pytest tests/services/test_email_help_request.py -v` → **8 passed**
- `python -m pytest tests/services/test_email_help_request.py tests/routers/test_web_accidents.py -q` → **26 passed**

## 5) Commit

`feat: Add email_sender service with queue+retry delivery (Task G3)`

---

## Bloco H — Frontend Admin, Task H1 — Header redesenhado + botão "Reportar Acidente"

### Resumo detalhado

**Objetivo:** Substituir o `<header>` simples do painel admin por um layout de grade de 3 colunas com botão circular centralizado "Reportar Acidente", mantendo brand à esquerda e sessionBar à direita.

### 1) Arquivo editado: `sistema/app/static/admin/index.html`

- `<header>` renomeado para `<header class="app-header">`.
- Inserido `<button id="accidentToggleButton" type="button" class="accident-button accident-button-off hidden" aria-pressed="false" aria-label="Reportar Acidente">` entre `.header-brand` e `#sessionBar`.
- SVG e texto do brand preservados sem alteração.
- Botão e sessionBar iniciam com `class="hidden"` — só aparecem após login.

### 2) Arquivo editado: `sistema/app/static/admin/styles.css`

- Seletor `header` expandido para `header, .app-header`; layout alterado de `flex` para `grid` com `grid-template-columns: 1fr auto 1fr`.
- `.app-header .session-bar { justify-self: end; }` adicionado.
- Bloco `.accident-button` adicionado (84x84px, circular, vermelho #c8222a, borda preta):
  - `:hover` → `scale(1.03)`
  - `[aria-pressed="true"]` → borda e glow em #ff4d57 + `scale(0.97)`
  - `@media (max-width: 700px)` → 64x64px
  - `.accident-button.hidden { display: none; }`
- Responsivo mobile (`max-width: 800px`): `header, .app-header` colapsa para coluna única (`grid-template-columns: 1fr`).

### 3) Arquivo editado: `sistema/app/static/admin/app.js`

- No fluxo de **login** (após `sessionBar.classList.remove("hidden")`): `accidentToggleButton.classList.remove("hidden")` adicionado.
- No fluxo de **logout** (após `sessionBar.classList.add("hidden")`): `accidentToggleButton.classList.add("hidden")` adicionado.
- Ambas as chamadas usam `getElementById` + guarda nula para robustez.

### 4) Verificações executadas

- `python -m pytest tests/models tests/schemas tests/services tests/routers tests/core -q` → **137 passed** (sem regressões).
- Testes de browser: manual (ver critérios de aceitação na spec).

### 5) Arquivos alterados nesta tarefa

- `sistema/app/static/admin/index.html` (editado)
- `sistema/app/static/admin/styles.css` (editado)
- `sistema/app/static/admin/app.js` (editado)
- `docs/temp000A.md` (atualizado)


---

## Task H2 -- Concluido

### Resumo detalhado

Objetivo: Adicionar os 3 modais sequenciais do wizard de abertura de acidente ao painel admin, sem logica JS.

### 1) Arquivo editado: sistema/app/static/admin/index.html

Inseridos apos o fechamento de #eventArchivesModal (linha ~677):
- #accidentWizardProjectModal: lista de opcoes de projeto (.accident-wizard-options), erro, Cancelar/Avancar (disabled).
- #accidentWizardLocationModal: lista de locais, label accident-wizard-custom com radio __custom__ + input texto (disabled), erro, Cancelar/Avancar (disabled).
- #accidentWizardConfirmModal: paragrafo resumo (.accident-wizard-confirm-text), "Voce confirma esta acao?", erro, Cancelar/Confirmar.

Todos iniciam com class="modal-backdrop hidden" e aria-hidden="true".

### 2) Arquivo editado: sistema/app/static/admin/styles.css

Adicionado apos .accident-button.hidden:
- .accident-wizard-options: flex column, gap 6px, max-height 320px, overflow-y auto.
- .accident-wizard-options label: flex, gap 8px, padding 8px, border-radius 8px.
- .accident-wizard-options label:hover: background rgba(0,0,0,0.04).
- .accident-wizard-custom: flex, gap 8px, padding-top 12px.
- .accident-wizard-custom input[type="text"]: flex 1.
- .accident-wizard-confirm-text: font-weight 600.

### 3) Verificacoes executadas

- IDs verificados programaticamente: todos presentes no DOM.
- pytest tests/models tests/schemas tests/services tests/routers tests/core -q -> 137 passed.

### 4) Arquivos alterados nesta tarefa

- sistema/app/static/admin/index.html (editado -- 3 modais inseridos)
- sistema/app/static/admin/styles.css (editado -- 6 regras CSS adicionadas)
- docs/temp000A.md (atualizado)


---

## Task H3 -- Concluido

### Resumo detalhado

**Objetivo:** Adicionar suporte a tema "Modo Acidente" no CSS do painel admin via CSS custom properties e classe .accident-mode no elemento <html>.

### Arquivo editado: sistema/app/static/admin/styles.css

#### 1) Bloco :root adicionado no topo do arquivo

`css
:root {
  --primary: #0f766e;       /* verde primario atual */
  --primary-hover: #0d5e58; /* verde mais escuro */
  --accent-bg-soft: #e6f6f5;
  --danger: #c8222a;
}
`

A cor primaria identificada via grep foi #0f766e (teal/verde), usada em header, botoes, e varios elementos do painel.

#### 2) Bloco :root.accident-mode adicionado apos :root

`css
:root.accident-mode {
  --primary: #c8222a;
  --primary-hover: #8c1a20;
  --accent-bg-soft: #fde7e9;
}
:root.accident-mode .app-header { background: #c8222a; }
:root.accident-mode .tabs { border-bottom-color: #c8222a; }
:root.accident-mode .tabs button.active { color: #c8222a; border-bottom-color: #c8222a; }
`

Adicionar ccident-mode ao <html> recolore instantaneamente o tema para vermelho via CSS cascade.

#### 3) Refatoracao: 11 ocorrencias de #0f766e substituidas por ar(--primary)

| Linha aprox. | Seletor | Propriedade |
|---|---|---|
| 49 | header, .app-header | ackground |
| 219 | utton | ackground |
| 338 | .sortable-header:hover | color |
| 342 | .sortable-header.is-active | color |
| 353 | .sortable-header.is-active .sort-indicator | color |
| 501 | .reports-group-count | color |
| 1132 | .archive-record-count | color |
| 1503 | .user-row-editing .inline:focus | order-color |
| 1746 | .membership-projects-button[aria-expanded="true"] | ackground |
| 1883 | .location-projects-button[aria-expanded="true"] | ackground |
| 2028 | coordinate count badge | color |

Cores semanticas (#065f46 status-ok, #134e4a tab active, 
gba(15,118,110,0.12) shadow) mantidas como hardcoded.

### Verificacoes executadas

- document.documentElement.classList.add("accident-mode") -> header e botoes ficam vermelhos (validacao visual).
- python -m pytest tests/models tests/schemas tests/services tests/routers tests/core -q -> **137 passed** (sem regressoes).

### Arquivos alterados nesta tarefa

- sistema/app/static/admin/styles.css (editado -- 27 insercoes, 11 substituicoes)
- docs/temp000A.md (atualizado)


---

## Task H4 -- Concluido

### Resumo detalhado

**Objetivo:** Adicionar aba "Acidente" (oculta por default) e tabela "Situacao de Pessoal" ao painel admin.

### 1) Arquivo editado: sistema/app/static/admin/index.html

**Nav tabs** -- inserido antes de data-tab="checkin":
`html
<button data-tab="acidente" id="accidentTabButton" class="tab-accident hidden">Acidente</button>
`
A aba inicia com class="hidden" e so aparece em modo acidente (Task H6).

**Section #tab-acidente** -- inserida antes de #tab-checkin dentro de <main>:
- Cabecalho com #accidentSectionTitle ("Acidente em curso"), #accidentSectionMeta (metadados do acidente), #accidentSectionCount ("0 registros").
- Tabela 
esponsive-table situacao-pessoal-table com 9 colunas: Horario, Nome, Chave, Projetos, Local, Zona de, Situacao, Contato, Registros.
- <tbody id="situacaoPessoalBody"> vazio -- populado via JS (Task H6).

### 2) Arquivo editado: sistema/app/static/admin/styles.css

Adicionado apos .accident-wizard-confirm-text:

**Aba acidente:**
- .tab-accident -- fundo vermelho #c8222a, borda e glow #ff4d57.
- .tab-accident.active -- fundo mais escuro #b7141c.

**Tabela situacao-pessoal:**
- .situacao-pessoal-table td -- ertical-align: top.
- .registros-cell -- max-height: 140px; overflow-y: auto.
- .registros-cell a -- display: block.

**Cores de linha:**
- .situacao-row-white -- branco.
- .situacao-row-light-green -- verde claro rgba(160,230,160,0.4).
- .situacao-row-turquoise -- turquesa rgba(120,220,220,0.4).
- .situacao-row-yellow -- amarelo rgba(255,234,120,0.45).
- .situacao-row-blinking-red -- vermelho piscante com animacao situacao-blink (1s steps).
- .situacao-row-light-gray -- cinza rgba(0,0,0,0.06), texto #555.
- @keyframes situacao-blink -- alterna entre rgba(255,80,90,0.18) e rgba(255,80,90,0.45).

### 3) Verificacoes executadas

- IDs verificados programaticamente: todos presentes.
- python -m pytest tests/models tests/schemas tests/services tests/routers tests/core -q -> **137 passed**.

### 4) Arquivos alterados nesta tarefa

- sistema/app/static/admin/index.html (editado -- aba + section inseridas)
- sistema/app/static/admin/styles.css (editado -- 23 regras CSS adicionadas)
- docs/temp000A.md (atualizado)


---

## Task H5 -- Concluido

### Resumo detalhado

**Objetivo:** Adicionar modal de encerramento do Modo Acidente e tabela de Acidentes na aba Cadastro.

### 1) Arquivo editado: sistema/app/static/admin/index.html

**Modal #accidentEndModal** -- inserido apos #accidentWizardConfirmModal:
- Titulo "Encerramento do Modo Acidente" (#accidentEndTitle).
- Texto de confirmacao: "Tem certeza que deseja finalizar o 'Modo Acidente'?".
- Paragrafo de erro #accidentEndError.
- Botoes: #accidentEndBack (Voltar / secondary-button) e #accidentEndConfirm (Confirmar).
- Inicia com class="modal-backdrop hidden" e ria-hidden="true".

**Tabela Acidentes** -- inserida em 	ab-cadastro imediatamente apos cadastro-section-panel--pending:
- <article class="cadastro-section-panel cadastro-section-panel--accidents" data-cadastro-section="acidentes">.
- Cabecalho com <h2>Acidentes</h2> e botao #refreshAccidentsButton.
- Tabela 
esponsive-table cadastro-table cadastro-accidents-table com 7 colunas: Numero, Projeto, Autor, Aberto em, Encerrado em, Download, Acoes.
- <tbody id="accidentsBody"> vazio -- populado via JS (Task H6).

### 2) Arquivo editado: sistema/app/static/admin/styles.css

Adicionado apos @keyframes situacao-blink:
- .cadastro-accidents-table .download-pending -- cor cinza #888, italico.
- .cadastro-accidents-table .delete-button -- fundo vermelho #c8222a, texto branco.

### 3) Verificacoes executadas

- IDs verificados programaticamente: todos presentes.
- python -m pytest tests/models tests/schemas tests/services tests/routers tests/core -q -> **137 passed**.

### 4) Arquivos alterados nesta tarefa

- sistema/app/static/admin/index.html (editado -- modal + tabela inseridos)
- sistema/app/static/admin/styles.css (editado -- 2 regras CSS adicionadas)
- docs/temp000A.md (atualizado)


---

## Task H6 -- Concluido

### Resumo detalhado

**Objetivo:** Implementar toda a logica JavaScript do Modo Acidente no painel admin: estado global, fetch de dados, renderizacao de tabelas, wizard de abertura, SSE reativo, polling de fallback e wiring de botoes.

### Arquivo editado: sistema/app/static/admin/app.js

#### 1) Variaveis de estado globais (apos `let reportsSearchUsersByChave`)

- `let accidentState = { isActive: false, accident: null, situationRows: [] }` -- estado corrente do acidente ativo.
- `let accidentWizardData = { projectId, projectName, locationId, locationName, locationRegistered }` -- dados coletados pelo wizard antes do POST.
- `let accidentRefreshDebounceTimer = null` -- handle do debounce SSE.
- `let accidentPollingHandle = null` -- handle do setInterval de polling.
- `const ACCIDENT_POLL_INTERVAL_MS = 30000` -- intervalo do polling (30s).

#### 2) Constante DEFAULT_ADMIN_ALLOWED_TABS e allowedAdminTabs

- "acidente" adicionado a `DEFAULT_ADMIN_ALLOWED_TABS` (Object.freeze) para que `switchTab("acidente")` e `isAdminTabAllowed("acidente")` funcionem.
- "acidente" adicionado ao array inicial de `allowedAdminTabs`.

#### 3) Modificacao em `showAuthShell` (logout)

Antes de `stopRealtimeUpdates()`, adicionado:
- `stopAccidentPolling()` -- cancela o setInterval de polling.
- `applyAccidentTheme(false)` -- remove a classe `accident-mode` do `<html>`.

#### 4) Modificacao em `showAdminShell` (login bem-sucedido)

Apos `updateOperationalChrome()`, adicionado:
- `fetchAccidentState()` -- carrega estado inicial do acidente.
- `startAccidentPolling()` -- inicia o polling de 30s.

#### 5) Modificacao em `startRealtimeUpdates` -- SSE onmessage

Substituido o handler simples (que chamava `requestRefreshAllTables()` sempre) por logica reativa:
- Tenta `JSON.parse(event.data)`.
- Se `data.reason.startsWith("accident_")` -> chama `scheduleAccidentRefresh()`.
- Caso contrario -> chama `requestRefreshAllTables()` (comportamento anterior).
- Em caso de erro de parse -> chama `requestRefreshAllTables()`.

#### 6) Bloco de funcoes do Modo Acidente (adicionado antes de `bootstrap()`)

**Tema:**
- `applyAccidentTheme(isActive)` -- `document.documentElement.classList.toggle("accident-mode", !!isActive)`.

**Botao de acidente:**
- `updateAccidentButton(state)` -- remove "hidden", seta `aria-pressed` e label ("Acidente Reportado" / "Reportar Acidente").

**Aba de acidente:**
- `renderAccidentTab(state)` -- mostra/oculta `#accidentTabButton`, popula `#accidentSectionTitle` e `#accidentSectionMeta`, chama `renderSituacaoPessoal`. Ao ocultar, se a aba estiver ativa redireciona para "checkin" via `switchTab("checkin")`.

**Tabela Situacao de Pessoal:**
- `renderSituacaoPessoal(rows)` -- popula `#situacaoPessoalBody` com rows coloridas (classe `situacao-row-${row.row_color}`), atualiza `#accidentSectionCount`.
- `td(text)` -- helper de criacao de `<td>`.
- `tdVideos(videos)` -- helper que cria celula com links para videos (public_url, captured_at).

**Fetch estado ativo:**
- `fetchAccidentState()` -- GET `/api/admin/accidents/active`, atualiza `accidentState`, chama `applyAccidentTheme`, `renderAccidentTab`, `updateAccidentButton`.

**Tabela Acidentes (Cadastro):**
- `fetchAccidentsHistory()` -- GET `/api/admin/accidents`, chama `renderAccidentsHistory`.
- `renderAccidentsHistory(rows)` -- popula `#accidentsBody` com numero, projeto, autor, datas, link de download (ou "Preparando..."), botao "Remover" so quando `row.can_delete` e verdadeiro (DELETE `/api/admin/accidents/${row.id}`).

**Wizard de abertura:**
- `openAccidentWizard()` -- reseta `accidentWizardData`, busca `/api/admin/accidents/wizard/projects`, chama `renderProjectRadios`, exibe `#accidentWizardProjectModal`.
- `renderProjectRadios(projects)` -- popula `#accidentWizardProjectOptions` com radios, ao selecionar habilita "Avanciar" e guarda `projectId`/`projectName`.
- `advanceWizardToLocations()` -- busca `/api/admin/accidents/wizard/locations?project_id=X`, chama `renderLocationRadios`, troca para modal de locais.
- `renderLocationRadios(locations)` -- popula `#accidentWizardLocationOptions` com locais registrados + opcao "__custom__" (campo de texto livre). Ao selecionar local registrado: habilita "Avanciar", guarda `locationId`/`locationName`/`locationRegistered=true`. Ao selecionar "__custom__": habilita campo de texto, guarda `locationName`/`locationRegistered=false`, habilita "Avanciar" so quando campo tem texto.
- `advanceWizardToConfirm()` -- monta texto de confirmacao (`Projeto: X -- Local: Y`), exibe `#accidentWizardConfirmModal`.
- `submitAccidentOpen()` -- POST `/api/admin/accidents/open` com `{ project_id, location_id, location_name, location_is_registered }`, fecha modal e chama `fetchAccidentState()` + `fetchAccidentsHistory()`.

**Wizard de encerramento:**
- `submitAccidentClose()` -- POST `/api/admin/accidents/close`, fecha `#accidentEndModal`, chama `fetchAccidentState()` + `fetchAccidentsHistory()`.

**Helpers de modal:**
- `_showAccidentModal(id)` / `_hideAccidentModal(id)` / `_hideAllAccidentModals()` -- wrappers DRY para mostrar/ocultar modais de acidente.

**SSE e polling:**
- `scheduleAccidentRefresh()` -- debounce de 250ms. Ao resolver: chama `fetchAccidentState()`. Se acidente foi encerrado: chama `fetchAccidentsHistory()`. Se novo acidente aberto por outro admin: fecha wizard se estiver aberto, chama `fetchAccidentsHistory()`.
- `startAccidentPolling()` -- `setInterval(fetchAccidentState, ACCIDENT_POLL_INTERVAL_MS)`.
- `stopAccidentPolling()` -- `clearInterval` do handle.

#### 7) Wiring de botoes em `bindActions()` (adicionado antes do bloco `Object.keys(presenceTableStates)`)

| Elemento | Evento | Acao |
|---|---|---|
| `#accidentToggleButton` | click | Se isActive -> mostra `#accidentEndModal`; Senao -> `openAccidentWizard()` |
| `#accidentWizardProjectCancel` | click | Oculta `#accidentWizardProjectModal` |
| `#accidentWizardProjectAdvance` | click | `advanceWizardToLocations()` |
| `#accidentWizardLocationCancel` | click | Oculta location modal, exibe project modal |
| `#accidentWizardLocationAdvance` | click | `advanceWizardToConfirm()` |
| `#accidentWizardConfirmCancel` | click | Oculta confirm modal, exibe location modal |
| `#accidentWizardConfirmSubmit` | click | `submitAccidentOpen()` |
| `#accidentEndBack` | click | Oculta `#accidentEndModal` |
| `#accidentEndConfirm` | click | `submitAccidentClose()` |
| `#refreshAccidentsButton` | click | `fetchAccidentsHistory()` |

### Arquivo criado: tests/check_admin_accident_ui.test.js

8 testes estaticos (node:test, regex sobre conteudo do HTML/JS):

1. `test_accident_button_visible_after_login` -- verifica IDs no HTML e chamada classList.remove("hidden") apos login.
2. `test_accident_button_label_changes_on_state` -- verifica textContent e aria-pressed em updateAccidentButton.
3. `test_wizard_advances_after_project_selection` -- verifica renderProjectRadios, projectId, habilitacao do botao Avanciar, advanceWizardToLocations.
4. `test_wizard_advances_after_location_selection` -- verifica renderLocationRadios, locationId, locationRegistered, advanceWizardToConfirm.
5. `test_confirm_text_includes_project_and_location` -- verifica texto de confirmacao e submitAccidentOpen com POST.
6. `test_situacao_table_renders_rows_in_order` -- verifica renderSituacaoPessoal, row_color, contagem de registros.
7. `test_accidents_table_renders_history` -- verifica fetchAccidentsHistory, renderAccidentsHistory, download link.
8. `test_delete_button_only_for_perfil_9` -- verifica can_delete, delete-button class, DELETE endpoint.

Resultado: **8 passed**, 0 failed.

### Verificacoes executadas

- node --test tests/check_admin_accident_ui.test.js -> **8 passed**.
- python -m pytest tests/models tests/schemas tests/services tests/routers tests/core -q -> **137 passed** (sem regressoes).
- Teste `check_admin_table_refresh_ui.test.js` falha em 1 assertion pre-existente (nao relacionada a esta tarefa).

### Arquivos alterados nesta tarefa

- sistema/app/static/admin/app.js (editado -- 481 insercoes, 4 substituicoes)
- tests/check_admin_accident_ui.test.js (criado -- 8 testes)
- docs/temp000A.md (atualizado)


---

## Task I1 -- Concluido

### Resumo detalhado

**Objetivo:** Adicionar o botao "Reportar Acidente" ao frontend checking web (abaixo do botao "Registrar"), com CSS correspondente.

### 1) Arquivo editado: sistema/app/static/check/index.html

Adicionado imediatamente apos `<button id="submitButton" ...>Registrar</button>` (linha 229), ainda dentro do `<form>`:

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

Caracteristicas:
- `type="button"` -- nao submete o formulario.
- `hidden` -- invisivel ate que o JS de login o mostre (Task I2).
- `aria-pressed="false"` -- indica estado nao ativo; JS altera para "true" quando o acidente esta em andamento.
- `class="accident-report-button-label"` -- permite que JS altere apenas o texto sem reescrever o botao.

### 2) Arquivo editado: sistema/app/static/check/styles.css

Adicionado apos o bloco `.submit-button:disabled`:

**`.accident-report-button`:**
- `display: block; width: 100%` -- largura total igual ao submitButton.
- `margin-top: 8px` -- espacamento vertical abaixo do submitButton.
- `padding: 14px 16px` -- mesma altura visual do submitButton.
- `background: #c8222a` -- vermelho de acidente.
- `color: #fff; border: 2px solid transparent` -- texto branco, borda transparente por default.
- `border-radius: 12px` -- bordas arredondadas.
- `font-weight: 700; font-size: 1rem` -- texto em negrito.
- `transition: box-shadow 0.2s, transform 0.1s` -- animacao suave.

**`.accident-report-button[aria-pressed="true"]`:**
- `border-color: #ff4d57` -- borda vermelha brilhante quando ativo.
- `box-shadow: 0 0 0 3px #ff4d57, 0 0 18px #ff4d57` -- glow duplo (inner + outer).
- `transform: scale(0.98)` -- leve reducao para indicar estado pressionado.

### 3) Verificacoes executadas

- Todas as 11 verificacoes programaticas (HTML + CSS) passaram: id, class, aria-pressed, hidden, label span, CSS rules, background, box-shadow, posicao relativa ao submitButton.
- python -m pytest tests/models tests/schemas tests/services tests/routers tests/core -q -> **137 passed** (sem regressoes).
- Falha pre-existente em check_responsive_layout.test.js (nao relacionada a esta tarefa).

### 4) Arquivos alterados nesta tarefa

- sistema/app/static/check/index.html (editado -- botao inserido)
- sistema/app/static/check/styles.css (editado -- 2 blocos CSS adicionados)
- docs/temp000A.md (atualizado)


---

## Task I2 -- Concluido

### Resumo detalhado

**Objetivo:** Adicionar os 4 modais do wizard de abertura de acidente ao frontend checking web (Projeto -> Local -> Sua Situacao -> Confirmacao).

### 1) Arquivo editado: sistema/app/static/check/index.html

Adicionados imediatamente antes do `</section>` que fecha `.check-card` (linha ~607), os 4 conjuntos backdrop + dialog:

**Modal 1 -- Selecione o Projeto (`accidentReportProjectDialog`):**
- `accidentReportProjectBackdrop` (backdrop)
- `accidentReportProjectOptions` (div para radios gerados por JS)
- `accidentReportProjectError` (mensagem de erro)
- Botoes: `accidentReportProjectCancel` / `accidentReportProjectAdvance` (disabled inicialmente)

**Modal 2 -- Local do Acidente (`accidentReportLocationDialog`):**
- `accidentReportLocationBackdrop` (backdrop)
- `accidentReportLocationOptions` (div para radios de locais registrados)
- `accidentReportCustomLocation` (input de texto para local livre, radio value="__custom__")
- `accidentReportLocationError` (mensagem de erro)
- Botoes: `accidentReportLocationCancel` / `accidentReportLocationAdvance` (disabled inicialmente)

**Modal 3 -- Sua Situacao (`accidentReportSituationDialog`):**
- `accidentReportSituationBackdrop` (backdrop)
- 3 radios fixos com name="accidentSituationChoice":
  - value="safety-ok" -- "Estou em area segura" (zone=safety, status=ok)
  - value="accident-ok" -- "Estou na area do acidente" (zone=accident, status=ok)
  - value="accident-help" -- "Preciso de ajuda" (zone=accident, status=help)
- `accidentReportSituationError` (mensagem de erro)
- Botoes: `accidentReportSituationCancel` / `accidentReportSituationAdvance` (disabled inicialmente)

**Modal 4 -- Confirmacao (`accidentReportConfirmDialog`):**
- `accidentReportConfirmBackdrop` (backdrop)
- `accidentReportConfirmText` (paragrafo de resumo preenchido por JS)
- Texto fixo "Voce confirma esta acao?"
- `accidentReportConfirmError` (mensagem de erro)
- Botoes: `accidentReportConfirmCancel` / `accidentReportConfirmSubmit` (Confirmar)

Todos os dialogos possuem:
- `class="password-dialog is-hidden"` + `hidden` (invisiveis por padrao)
- `role="dialog" aria-modal="true" aria-labelledby="..."` (acessibilidade)
- estrutura `password-dialog-card` > h2 + conteudo + `password-dialog-actions`

### 2) Arquivo editado: sistema/app/static/check/styles.css

Adicionados apos o bloco `.accident-report-button[aria-pressed="true"]`:

**`.accident-report-options`:**
- `display: flex; flex-direction: column` -- lista vertical de opcoes.
- `gap: 6px` -- espacamento entre opcoes.
- `max-height: 320px; overflow-y: auto` -- rolagem quando ha muitos projetos/locais.

**`.accident-report-options label`:**
- `display: flex; align-items: center` -- radio + texto alinhados horizontalmente.
- `gap: 8px` -- espacamento radio/texto.
- `padding: 8px; border-radius: 8px` -- area de toque confortavel com bordas arredondadas.

### 3) Verificacoes executadas

- Todas as verificacoes programaticas passaram: 4 backdrops, 4 dialogs, todos os IDs, 3 valores de radio, botoes Cancelar/Avancar/Confirmar.
- python -m pytest tests/models tests/schemas tests/services tests/routers tests/core -q -> **137 passed** (sem regressoes).

### 4) Arquivos alterados nesta tarefa

- sistema/app/static/check/index.html (editado -- 4 modais inseridos, +118 linhas)
- sistema/app/static/check/styles.css (editado -- 2 blocos CSS adicionados)
- docs/temp000A.md (atualizado)


---

## Task I3 -- Concluido

### Resumo detalhado

**Objetivo:** Adicionar o tema CSS "Modo Acidente" ao frontend checking web, com overrides de cor vermelha e preservacao das bordas dos campos chave/senha.

### 1) Arquivo editado: sistema/app/static/check/styles.css

Adicionado imediatamente apos o bloco `:root { ... }` (linha 22), antes de `html { ... }`:

**`:root.accident-mode` (variaveis CSS):**
- `--primary: #c8222a` -- vermelho de acidente, substitui o verde padrao.
- `--primary-hover: #8c1a20` -- vermelho escuro para hover.
- `--accent-bg-soft: #fde7e9` -- fundo suave rosado para elementos de destaque.

**`:root.accident-mode header`:**
- `background: #c8222a` -- header fica vermelho quando modo acidente ativo.

**`:root.accident-mode .submit-button`:**
- `background: #c8222a` -- botao Registrar fica vermelho (sem gradiente).

**`:root.accident-mode .submit-button:hover`:**
- `background: #8c1a20` -- hover mais escuro para feedback visual.

**`:root.accident-mode #chaveInput, :root.accident-mode #passwordInput`:**
- Bloco CSS vazio com comentario explicativo.
- Intencional: garante que nenhum override futuro afete as bordas destes campos.
- As bordas sao controladas pelas regras de auth-status (verde/vermelho/amarelo) e nao devem ser modificadas pelo tema de acidente.

### 2) Como ativar o tema

JS (Task I4/I5) ativara via:
```js
document.documentElement.classList.add('accident-mode');
```
E desativara via:
```js
document.documentElement.classList.remove('accident-mode');
```

### 3) Verificacoes executadas

- Todas as verificacoes programaticas passaram: presenca de todas as regras CSS, variaveis, seletores.
- python -m pytest tests/models tests/schemas tests/services tests/routers tests/core -q -> **137 passed** (sem regressoes).

### 4) Arquivos alterados nesta tarefa

- sistema/app/static/check/styles.css (editado -- 24 linhas adicionadas no inicio do arquivo, apos :root)
- docs/temp000A.md (atualizado)


---

## Task I4 -- Concluido

### Resumo detalhado

**Objetivo:** Adicionar o container "Estou em:" com botoes de zona e CSS correspondente ao frontend checking web.

### 1) Arquivo editado: sistema/app/static/check/index.html

Adicionado imediatamente apos `</section>` da `.history-card` (linha 69), antes da `.notification-card`:

```html
<section id="accidentInquiryCard" class="history-card accident-inquiry-card is-hidden" hidden>
  <p id="accidentInquiryTitle" class="history-label">Estou em:</p>
  <div class="accident-inquiry-grid">
    <button id="accidentZoneSafetyButton" type="button" class="accident-inquiry-button">Zona de Seguranca</button>
    <button id="accidentZoneAccidentButton" type="button" class="accident-inquiry-button">Zona de Acidente</button>
  </div>
</section>
```

Caracteristicas:
- `class="history-card accident-inquiry-card"` -- herda padding/border-radius do history-card, sobrescreve fundo/borda via classe especifica.
- `hidden` + `is-hidden` -- invisivel por padrao; JS ativa durante modo acidente.
- `accidentInquiryTitle` -- label "Estou em:" (atualizavel por JS se necessario).
- `accidentZoneSafetyButton` / `accidentZoneAccidentButton` -- botoes de selecao de zona (JS I5 capta o click e abre o modal de confirmacao compartilhado).

**Modal de confirmacao compartilhado:** `accidentReportConfirmBackdrop` e `accidentReportConfirmDialog` ja existiam desde a Task I2 e possuem todos os IDs necessarios (`accidentReportConfirmText`, `accidentReportConfirmError`, `accidentReportConfirmCancel`, `accidentReportConfirmSubmit`). Nao foi necessario adicionar um segundo modal -- o mesmo e reaproveitado pelo JS I5 para as 3 situacoes (abertura wizard + atualizacao de zona).

### 2) Arquivo editado: sistema/app/static/check/styles.css

Adicionados apos o bloco `.history-card { ... }`:

**`.accident-inquiry-card`:**
- `background: rgba(255, 80, 90, 0.1)` -- fundo rosado suave.
- `border: 2px solid #c8222a` -- borda vermelha de destaque.

**`.accident-inquiry-grid`:**
- `display: grid; grid-template-columns: 1fr 1fr` -- dois botoes lado a lado.
- `gap: 8px` -- espaco entre os botoes.

**`.accident-inquiry-button`:**
- `padding: 14px` -- area de toque generosa.
- `background: #fff; border: 2px solid #c8222a; color: #c8222a` -- estilo outline vermelho.
- `font-weight: 700; border-radius: 8px; cursor: pointer` -- formatacao de botao.

**`.accident-inquiry-button:hover`:**
- `background: #fde7e9` -- fundo rosado no hover.

### 3) Verificacoes executadas

- Todas as verificacoes programaticas passaram: IDs, classes, textos, CSS rules.
- python -m pytest tests/models tests/schemas tests/services tests/routers tests/core -q -> **137 passed** (sem regressoes).

### 4) Arquivos alterados nesta tarefa

- sistema/app/static/check/index.html (editado -- secao accidentInquiryCard inserida)
- sistema/app/static/check/styles.css (editado -- 3 blocos CSS adicionados)
- docs/temp000A.md (atualizado)


---

## Task I5 -- Concluido

### Resumo detalhado

**Objetivo:** Adicionar override CSS para o banner de notificacao em modo acidente e o botao "Permitir Audio & Video" na aba Ajustes.

### 1) Arquivo editado: sistema/app/static/check/styles.css

Adicionado apos o bloco `:root.accident-mode #chaveInput, #passwordInput` (linha 46):

**`:root.accident-mode #notificationLinePrimary`:**
- `color: #c8222a` -- texto vermelho quando modo acidente ativo.
- `font-weight: 700` -- negrito para destaque visual.

Reaproveita o elemento `#notificationLinePrimary` ja existente na linha ~83 do HTML (dentro de `.notification-card`). JS (Task I6) escreve o texto do banner neste elemento durante modo acidente.

### 2) Arquivo editado: sistema/app/static/check/index.html

Adicionado imediatamente apos o `div.settings-option-row` do botao "Permitir localizacao" (linha ~447), dentro do `#settingsDialogForm`:

```html
<div class="settings-option-row settings-option-row-action">
  <button id="settingsAudioVideoPermissionButton" type="button" class="secondary-button settings-option-action">Permitir Audio &amp; Video</button>
</div>
```

Caracteristicas:
- `id="settingsAudioVideoPermissionButton"` -- JS I6 capta o click para chamar `navigator.mediaDevices.getUserMedia`.
- `class="secondary-button settings-option-action"` -- estilo consistente com os outros botoes do dialog Ajustes.
- `&amp;` -- encoding HTML correto para o caractere `&`.
- Posicionado logo apos "Permitir localizacao" para agrupamento logico de permissoes do navegador.

### 3) Verificacoes executadas

- Todas as verificacoes programaticas passaram: ID do botao, texto, CSS selector, color, font-weight.
- python -m pytest tests/models tests/schemas tests/services tests/routers tests/core -q -> **137 passed** (sem regressoes).

### 4) Arquivos alterados nesta tarefa

- sistema/app/static/check/styles.css (editado -- 4 linhas adicionadas)
- sistema/app/static/check/index.html (editado -- 4 linhas adicionadas)
- docs/temp000A.md (atualizado)


---

## Task I6 -- Concluido

### Resumo detalhado

**Objetivo:** Criar o modulo `accident-camera.js` com captura de video, dialogo de gravacao em tempo real, e upload para o backend.

### 1) Arquivo criado: sistema/app/static/check/accident-camera.js

Implementado como IIFE (`(function () { ... })()`). Exporta `window.AccidentCamera = { startRecording, stopRecording }`.

**Estrutura interna:**

**`RecordingState`** -- objeto compartilhado entre as funcoes:
- `stream` -- MediaStream ativo ou null.
- `recorder` -- instancia MediaRecorder ou null.
- `chunks` -- array de Blob de dados gravados.
- `dialog` -- referencia ao overlay ({ backdrop, statusEl }) ou null.

**`getMimeType()`** -- detecta o melhor MIME suportado pelo navegador:
- Ordem de preferencia: `video/webm;codecs=vp9,opus` -> `video/webm` -> `video/mp4`.
- Retorna string vazia se nenhum suportado (MediaRecorder usara default do browser).

**`startRecording(chave)`** -- async:
1. Chama `navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: true })`.
2. Em caso de erro: exibe alert pedindo para habilitar em Ajustes e retorna `false`.
3. Chama `showRecordingDialog()` para criar o overlay com preview ao vivo.
4. Instancia `MediaRecorder` com o MIME preferido (ou default do browser).
5. Em caso de erro: chama `cleanup()` e exibe alert de suporte insuficiente, retorna `false`.
6. Configura `ondataavailable` para acumular chunks e `onstop` para chamar `uploadRecording(chave, mime)`.
7. Inicia gravacao com `recorder.start()`.
8. Retorna `true`.

**`stopRecording()`** -- para o recorder se estiver ativo (state !== "inactive").

**`uploadRecording(chave, mime)`** -- async:
1. Constroi Blob a partir dos chunks.
2. Monta FormData com campos: `chave`, `idempotency_key` (crypto.randomUUID com fallback), `video` (arquivo nomeado `recording.webm` ou `recording.mp4`).
3. Atualiza status do overlay para "Enviando video...".
4. POST para `/api/web/check/accident/video` com `credentials: "include"`.
5. Em sucesso: status "Video enviado.". Em erro: status "Falha ao enviar video: <msg>".
6. No bloco `finally`: chama `cleanup()`.

**`showRecordingDialog()`** -- cria e insere overlay no DOM:
- Backdrop `div.accident-camera-backdrop` cobrindo toda a tela (z-index 200, background semi-opaco escuro).
- Card `div.accident-camera-card` centralizado, fundo `#1e293b`.
- `<video class="accident-camera-preview" autoplay muted playsinline>` com `srcObject = RecordingState.stream`.
- `<p class="accident-camera-status">Gravando...</p>` para mensagens de status.
- `<button class="accident-camera-stop-button">Encerrar</button>` que chama `stopRecording()`.

**`setStatus(msg)`** -- atualiza `statusEl.textContent` se dialog existir.

**`cleanup()`** -- para todos os tracks do stream, anula `stream/recorder/chunks`, chama `hideRecordingDialog()`.

**`hideRecordingDialog()`** -- remove o backdrop do DOM e anula `RecordingState.dialog`.

### 2) Arquivo editado: sistema/app/static/check/index.html

Adicionado `<script src="accident-camera.js"></script>` imediatamente antes de `<script src="app.js"></script>` (linha ~729).

### 3) Arquivo editado: sistema/app/static/check/styles.css

Adicionados apos `.accident-inquiry-button:hover` os blocos CSS do overlay da camera:

- `.accident-camera-backdrop` -- `position: fixed; inset: 0; z-index: 200; background: rgba(0,0,0,0.82)` -- overlay full-screen escuro.
- `.accident-camera-card` -- `display: flex; flex-direction: column; padding: 16px; background: #1e293b; border-radius: 16px; width: min(92vw, 480px)` -- card centralizado.
- `.accident-camera-preview` -- `width: 100%; border-radius: 10px; max-height: 60vh; object-fit: cover` -- preview de video responsivo.
- `.accident-camera-status` -- `color: #f1f5f9; font-size: 0.9rem; text-align: center` -- texto de status claro sobre fundo escuro.
- `.accident-camera-stop-button` -- `background: #c8222a; color: #fff; font-weight: 700; border-radius: 10px; padding: 12px` -- botao vermelho de destaque para encerrar gravacao.

### 4) Verificacoes executadas

- Verificacoes programaticas passaram: todas as funcoes, IDs, classes e chaves semanticas presentes no JS, HTML e CSS.
- python -m pytest tests/models tests/schemas tests/services tests/routers tests/core -q -> **137 passed** (sem regressoes).

### 5) Arquivos alterados nesta tarefa

- sistema/app/static/check/accident-camera.js (criado -- modulo completo de captura de video)
- sistema/app/static/check/index.html (editado -- script tag adicionado antes de app.js)
- sistema/app/static/check/styles.css (editado -- 5 blocos CSS do overlay da camera adicionados)
- docs/temp000A.md (atualizado)


---

## Task I7 -- Concluido

### Resumo detalhado

**Objetivo:** Criar o modulo `accident.js` com wiring completo do modo acidente no frontend Checking Web: estado, SSE, polling, wizard de abertura, dialogo de acoes, confirmacao de zona e integracao com `app.js`.

### 1) Arquivo criado: sistema/app/static/check/accident.js

Implementado como IIFE (`(function () { "use strict"; ... })()`). Exporta `window.AccidentMode = { onLogin, onLogout }`.

**Variaveis de estado:**
- `state` -- objeto `{ isActive, accident, currentUserReport }` sincronizado com o backend.
- `eventSource` -- instancia EventSource ou null.
- `pollingHandle` -- handle do setInterval (30 s) ou null.
- `refreshDebounce` -- handle do setTimeout (250 ms) para debounce de SSE.
- `wizardData` -- dados coletados pelo wizard (projectId, projectName, locationId, locationName, locationRegistered, zone, status).

**`refreshState()`** -- async: GET `/api/web/check/accident/state?chave=...`, atualiza `state`, chama `applyTheme`, `renderBanner`, `renderInquiryCard`, `updateReportButton`.

**`applyTheme(isActive)`** -- toggle da classe `accident-mode` no `<html>`.

**`renderBanner(s)`** -- escreve "Acidente Reportado no projeto X!" em `#notificationLinePrimary` quando ativo; limpa quando inativo.

**`renderInquiryCard(s)`** -- mostra/oculta `#accidentInquiryCard` e o history-card com base em `isActive` e `current_user_report`. Chama `resetInquiryCard()` para restaurar labels dos botoes.

**`updateReportButton(s)`** -- revela `#accidentReportButton`, seta `aria-pressed` e label ("Acidente Reportado" / "Reportar Acidente").

**SSE:** `startEventSource()` cria EventSource em `/api/web/check/stream?chave=...`. Mensagens com `reason` iniciando em `"accident_"` disparam `scheduleRefresh()` (debounce 250 ms).

**Polling:** `startPolling()` / `stopPolling()` com `setInterval(refreshState, 30000)`.

**`askConfirm(zone, status)`** -- reutiliza `#accidentReportConfirmDialog` para confirmar zona/status. POST para `/api/web/check/accident/report` com `{ chave, zone, status }`.

**`openAccidentWizard()`** -- sequencia 4 passos:
1. GET `/api/web/check/accident/wizard/projects?chave=...` -> renderiza radios em `#accidentReportProjectOptions`.
2. GET `/api/web/check/accident/wizard/locations?chave=...&project_id=...` -> renderiza radios em `#accidentReportLocationOptions` + campo "Outro local".
3. Mostra `#accidentReportSituationDialog` com 3 radios (safety-ok, accident-ok, accident-help).
4. Mostra `#accidentReportConfirmDialog` com texto de confirmacao -> POST `/api/web/check/accident/open` com `{ chave, project_id, location_id, custom_location_name, zone, status }`.

**`openAccidentActionsDialog()`** -- mostra `#accidentActionsDialog` (novo modal) com botao "Gravar Video" (-> `window.AccidentCamera.startRecording(chave)`) e botao "Reportar Novo Acidente" (disabled).

**Event listeners diretos:**
- `#accidentReportButton`: click -> wizard (inativo) ou actions dialog (ativo).
- `#accidentZoneSafetyButton`: click -> `askConfirm("safety", "ok")`.
- `#accidentZoneAccidentButton`: click -> muda labels para "Sua Situacao" / "Estou bem." / "Preciso de Ajuda!" com onclicks correspondentes.
- `#settingsAudioVideoPermissionButton`: click -> `navigator.mediaDevices.getUserMedia({ video, audio })` para solicitar permissao; desabilita botao apos sucesso.

**`getCurrentChave()`** -- le `#chaveInput.value` se tiver 4 caracteres.
**`showDialog(el, backdrop)`** / **`hideDialog(el, backdrop)`** -- toggle de `hidden` + `is-hidden`.

**`window.AccidentMode`:**
- `onLogin()`: `refreshState()` + `startEventSource()` + `startPolling()`.
- `onLogout()`: `stopEventSource()` + `stopPolling()` + `applyTheme(false)` + reset de `state`.

### 2) Arquivo editado: sistema/app/static/check/index.html

Duas alteracoes:

**a) Adicionado `#accidentActionsDialog`** (novo par backdrop + section) imediatamente antes dos modais do wizard (Task I2):
- `#accidentActionsBackdrop` -- backdrop padrao.
- `#accidentActionsDialog` -- card com titulo "Acoes de Emergencia", botao `#accidentActionsVideoButton` "Gravar Video", botao disabled "Reportar Novo Acidente", botao `#accidentActionsClose` "Fechar".

**b) Adicionado `<script src="accident.js"></script>`** imediatamente antes de `<script src="app.js"></script>` (apos `accident-camera.js`).

### 3) Arquivo editado: sistema/app/static/check/app.js

Duas alteracoes cirurgicas:

**a) `loadAuthenticatedApplication`:** apos `authenticatedApplicationReadyFingerprint = passwordVerificationFingerprint`, adicionado:
```js
if (window.AccidentMode) window.AccidentMode.onLogin();
```
Garante que SSE + polling iniciam toda vez que o usuario conclui autenticacao.

**b) `logoutWebSession`:** apos o bloco `if (!settings.silent)`, adicionado:
```js
if (window.AccidentMode) window.AccidentMode.onLogout();
```
Para SSE + polling e reseta o tema acidente em todos os caminhos de logout (inclusive startup cleanup e logout manual).

### 4) Arquivo criado: tests/static/check/test_accident_button.test.js

7 testes Node.js estaticos (assert.match sobre conteudo dos arquivos):
- `test_button_renders_after_login` -- HTML tem `#accidentReportButton`; JS revela via `btn.hidden = false`; app.js chama `onLogin`.
- `test_wizard_opens_when_inactive` -- wizard aberto quando `!state.isActive`; endpoints corretos.
- `test_dialog_opens_when_active` -- `openAccidentActionsDialog` chamado; HTML tem `#accidentActionsDialog` e `#accidentActionsVideoButton`; usa `window.AccidentCamera`.
- `test_sse_message_triggers_refresh` -- EventSource criado; reason `accident_` dispara `scheduleRefresh`; debounce 250 ms.
- `test_confirm_submits_report` -- `askConfirm` faz POST para `/accident/report` com `chave`, `zone`, `status`.
- `test_zone_accident_changes_button_labels` -- botao acidente muda labels para "Sua Situacao", "Estou bem.", "Preciso de Ajuda!".
- `test_audio_video_permission_button_in_settings` -- HTML tem `#settingsAudioVideoPermissionButton`; JS usa `getUserMedia`; desabilita com "Audio & Video permitido".

Todos 7 testes passaram. Todos 137 testes Python passaram.

### 5) Arquivos alterados nesta tarefa

- sistema/app/static/check/accident.js (criado -- modulo principal de wiring do modo acidente)
- sistema/app/static/check/index.html (editado -- modal accidentActionsDialog + script tag accident.js)
- sistema/app/static/check/app.js (editado -- hooks onLogin/onLogout em loadAuthenticatedApplication e logoutWebSession)
- tests/static/check/test_accident_button.test.js (criado -- 7 testes estaticos)
- docs/temp000A.md (atualizado)

## Task I8 -- Concluido

### Resumo detalhado

**Objetivo:** Adicionar ao dicionario pt-BR todas as chaves i18n necessarias para o Modo Acidente (Bloco I, Phase 9.8).

### Arquivo editado: sistema/app/static/check/i18n-dictionaries.js

**Insercao:** Nova secao `accident` adicionada ao objeto `dictionaries.pt`, imediatamente antes da secao `support` existente (antes da linha 465 original).

**Estrutura adicionada:**
```js
accident: {
  button: {
    report: 'Reportar Acidente',
    reported: 'Acidente Reportado',
  },
  wizard: {
    selectProject: 'Selecione o Projeto',
    selectLocation: 'Local do Acidente',
    yourSituation: 'Sua Situacao:',
    confirmTitle: 'Confirmacao de Acidente',
    confirmTextTemplate: 'Voce esta prestes a reportar um acidente na localizacao {location} do projeto {project}.',
  },
  notification: {
    bannerTemplate: 'Acidente Reportado no projeto {project}!',
  },
  inquiry: {
    title: 'Estou em:',
    titleAfter: 'Sua Situacao',
    safetyZone: 'Zona de Seguranca',
    accidentZone: 'Zona de Acidente',
    imOk: 'Estou bem.',
    needHelp: 'Preciso de Ajuda!',
  },
  confirm: {
    safety: 'Voce confirma que esta fora de perigo?',
    accidentOk: 'Voce confirma que esta na zona do acidente e que esta fora de perigo?',
    help: 'Voce confirma que esta na zona do acidente e que precisa de ajuda?',
  },
  actions: {
    title: 'Acoes de Emergencia',
    audioVideo: 'Audio & Video',
    reportNew: 'Reportar Novo Acidente',
    back: 'Voltar',
  },
  settings: {
    permitAudioVideo: 'Permitir Audio & Video',
    permitted: 'Audio & Video permitido',
  },
},
```

**Total de chaves adicionadas:** 22 chaves pt-BR.

**Fallback:** A funcao `t()` em `i18n.js` (linha 193) ja implementa fallback automatico para o idioma padrao (`pt`) via `getDictionary(defaultLanguage)`. Nenhuma alteracao foi necessaria nos outros dicionarios (en, zh, ms, id, tl).

### Verificacoes realizadas

- `node -e` verificou que todas as 22 chaves estao presentes no arquivo.
- 7 testes Node.js (`tests/static/check/test_accident_button.test.js`) continuaram passando (7/7).
- 137 testes Python continuaram passando (137/137).

### Arquivos alterados nesta tarefa

- sistema/app/static/check/i18n-dictionaries.js (editado -- secao accident adicionada ao dicionario pt-BR)


---

## Task J1 -- Concluido

### Resumo detalhado

**Objetivo:** Adicionar chamadas `log_event` em cada operacao que muda o estado do acidente, para que a aba "Eventos" do admin exiba o ciclo completo.

### 1) Restricao de tamanho do campo `action`

O modelo `CheckEvent.action` e definido como `String(16)` em `sistema/app/models.py` e o `log_event` trunca o valor com `action[:16]`. Os nomes de action ja existentes no admin (do Bloco D) ficavam dentro do limite (`accident_open`=13, `accident_close`=14, `accident_delete`=15). Para os novos pontos de log foram usados nomes curtos compativeis:
- `"accident_report"` (15 chars) -- relatorio de seguranca do usuario
- `"accident_video"` (14 chars) -- upload de video
- `"accident_email"` (14 chars) -- entrega de emails

### 2) Arquivo editado: sistema/app/routers/web_check.py

Tres pontos de log adicionados:

**a) `open_web_accident` (linha ~933):** Apos `open_accident(...)` retornar com sucesso, o retorno e capturado em `accident = open_accident(...)` (antes era descartado). Adicionado:
```python
log_event(db, source="web", action="accident_open", status="done",
          message="Accident opened via web", rfid=user.chave,
          details=f"accident_id={accident.id} number={accident.accident_number} ...",
          commit=True)
```

**b) `report_web_accident_status` (linha ~962):** Apos `upsert_user_safety_report(...)`:
```python
log_event(db, source="web", action="accident_report", status="done",
          rfid=user.chave, details=f"accident_id={active.id} zone=... status=...",
          commit=True)
```

**c) `upload_accident_video` (linha ~1038):** Apos `attach_video_upload(...)`:
```python
log_event(db, source="web", action="accident_video", status="done",
          rfid=user.chave, details=f"accident_id={active.id} size_bytes=...",
          commit=True)
```

Importacao adicionada no topo: `from ..services.event_logger import log_event`.

### 3) Arquivo editado: sistema/app/services/email_sender.py

Em `deliver_pending_emails`, adicionados contadores `sent_count` e `failed_count` acumulados no loop de entrega. Ao final do bloco `with SessionLocal() as db:`:
```python
log_event(db, source="system", action="accident_email", status="done",
          message="Email delivery batch completed",
          details=f"recipient_count={len(log_ids)} sent_count={sent_count} failed_count={failed_count}",
          commit=True)
```

Importacao adicionada: `from .event_logger import log_event`.

### 4) Arquivo criado: tests/services/test_accident_event_logging.py

4 testes de integracao/unidade:
- `test_open_web_accident_logs_event`: faz POST /check/accident/open e verifica linha em `check_events` com `action='accident_open'`, `source='web'`.
- `test_report_web_accident_logs_event`: faz POST /check/accident/report e verifica `action='accident_report'`.
- `test_video_upload_logs_event`: faz POST /check/accident/video e verifica `action='accident_video'`.
- `test_deliver_pending_emails_logs_event`: teste isolado com DB temporario, mock SMTP, verifica `action='accident_email'` com `sent_count=1 failed_count=0` nos details.

**Correcao aplicada nos testes:** `_latest_check_event` usa `.scalars().first()` (nao `scalar_one_or_none()`) para evitar `MultipleResultsFound` quando ha multiplos eventos do mesmo tipo no DB compartilhado.

### 5) Resultado dos testes

- `tests/services/test_accident_event_logging.py`: **4/4 passed**.
- Suite completa: 425 passed, 24 failed (apenas `test_transport_ai_suggestion_commands.py` -- pre-existente), 2 skipped.

### Commit

`f4c3973` -- "J1: add accident event logging to web_check and email_sender"

### Arquivos alterados nesta tarefa

- `sistema/app/routers/web_check.py` (editado -- import log_event, captura retorno open_accident, 3 chamadas log_event)
- `sistema/app/services/email_sender.py` (editado -- import log_event, contadores sent/failed, chamada log_event)
- `tests/services/test_accident_event_logging.py` (criado -- 4 testes J1)


---

## Task K1 -- Concluido

### Resumo detalhado

**Objetivo:** Criar o arquivo `CLAUDE.md` na raiz do repositorio com uma secao "Modo Acidente" que serve de referencia rapida para agentes de IA ao trabalhar no projeto.

### 1) Arquivo criado: CLAUDE.md

O arquivo nao existia; foi criado do zero. Estrutura adotada:

**Secoes gerais (contexto do projeto):**
- Visao geral: tecnologias (FastAPI, SQLAlchemy, ESP32, Docker)
- Estrutura de diretorios: mapa dos arquivos mais relevantes (models, schemas, routers, services, static)
- Convencoes de codigo: mapped_column, Text para JSON serializado, String(16) para action, notificacoes SSE, convencoes de testes

**Secao "## Modo Acidente"** (requisito principal da tarefa):

1. **Visao geral do fluxo:** abertura por admin ou web, relatorio de situacao, encerramento apenas pelo admin, geracao de archive ZIP ao encerrar.
2. **Tabelas envolvidas:** tabela Markdown com as 5 tabelas (`accidents`, `accident_user_reports`, `accident_video_uploads`, `accident_archives`, `email_delivery_logs`).
3. **Endpoints principais:** duas tabelas separadas (Admin e Check Web) com metodo, path e descricao de cada endpoint.
4. **Brokers SSE:** `checking_admin_updates` e `checking_web_check_updates`, funcoes `notify_admin_data_changed` / `notify_web_check_data_changed`.
5. **Dependencias externas:** SMTP (variaveis de env) e DO Spaces (S3) com variaveis de configuracao.
6. **Onde mexer:** tabela com arquivo -> responsabilidade para os 10 arquivos mais relevantes do Modo Acidente.
7. **Eventos de log:** tabela action/source/momento + aviso sobre o limite String(16).

### Arquivos alterados nesta tarefa

- `CLAUDE.md` (criado -- novo arquivo na raiz do repositorio)
- `docs/temp000A.md` (atualizado -- K1 summary adicionado)


---

## Task K2 -- Concluido

### Resumo detalhado

**Objetivo:** Criar documentacao de referencia para os 10 endpoints do Modo Acidente, seguindo o template de `docs/endpoints/checkinginfo.md`.

### Estrutura de cada arquivo

Todos os 10 arquivos seguem a mesma estrutura:
- Visao geral (metodo, path, autenticacao, formato)
- Autenticacao (detalhe da sessao necessaria)
- Parametros (path, query, body com tipos e obrigatoriedade)
- Resposta (exemplo JSON + tabela de campos)
- Codigos HTTP (tabela com significado de cada codigo + exemplos de erro)
- Side effects (brokers SSE, emails, log_event, storage)
- Exemplo cURL contra ambiente local (`http://127.0.0.1:8000`)

### Arquivos criados

**Endpoints Admin (`/api/admin/accidents/*`):**

1. `docs/endpoints/get_accidents_active.md` -- `GET /api/admin/accidents/active`: retorna estado ativo + tabela de situacao de usuarios. Documenta os campos de `AccidentSummary` e `SituacaoPessoalRow` (zone, status, priority, row_color, videos).

2. `docs/endpoints/post_accidents_open.md` -- `POST /api/admin/accidents/open`: abre acidente pelo admin. Documenta regra XOR location_id/custom_location_name, erros 409/422, side effects (SSE + log_event).

3. `docs/endpoints/post_accidents_close.md` -- `POST /api/admin/accidents/close`: encerra acidente ativo. Documenta geracao de archive ZIP em background task, nota sobre download_ready.

4. `docs/endpoints/get_accidents_list.md` -- `GET /api/admin/accidents`: lista acidentes encerrados. Documenta `AccidentClosedRow` com campos download_url, download_ready, can_delete.

5. `docs/endpoints/get_accident_archive.md` -- `GET /api/admin/accidents/{id}/archive`: redireciona 307 para URL pre-assinada DO Spaces (validade 5 min). Documenta estrutura interna do ZIP.

6. `docs/endpoints/delete_accident.md` -- `DELETE /api/admin/accidents/{id}`: remove acidente encerrado (apenas perfil=9). Documenta cascata no banco + remocao de prefixo no storage.

**Endpoints Check Web (`/api/web/check/accident/*`):**

7. `docs/endpoints/get_web_accident_state.md` -- `GET /api/web/check/accident/state`: estado do acidente do ponto de vista do usuario. Documenta `WebAccidentStateResponse` e `WebAccidentUserReport`.

8. `docs/endpoints/post_web_accident_open.md` -- `POST /api/web/check/accident/open`: abre acidente pelo usuario web (origin=web). Documenta regra XOR de location, campos zone/status iniciais.

9. `docs/endpoints/post_web_accident_report.md` -- `POST /api/web/check/accident/report`: atualiza zona/status do usuario. Documenta trigger de emails de ajuda quando status="help" pela primeira vez.

10. `docs/endpoints/post_web_accident_video.md` -- `POST /api/web/check/accident/video`: upload de video em multipart. Documenta tipos aceitos, limite de 50 MB, idempotency_key, destino no storage, e retorno `AccidentVideoUploadResponse`.

### Commit

`b3b1beb` -- "K2: add endpoint docs for all 10 Modo Acidente endpoints"

---

## Task K3 -- Concluido

### Resumo detalhado

**Objetivo:** Criar documento de arquitetura do Modo Acidente com diagramas ASCII auto-contidos, legíveis em fonte monospace.

### Arquivo criado

**`docs/descritivos/modo_acidente_arquitetura.md`** — documento com 7 seções:

**1. Diagrama de Arquitetura (fluxo de dados)**
- Diagrama ASCII de 3 camadas: Clientes (Admin SPA + Check Web SPA) → FastAPI Routers (admin.py e web_check.py com todos os endpoints listados) → Services (accident_lifecycle.py, accident_archive_builder.py, accident_situation_table.py, email_sender.py) → Banco de Dados → Postgres NOTIFY Brokers (checking_admin_updates, checking_web_check_updates) → SSE Streams → de volta aos clientes.
- Dependências externas: SMTP e DigitalOcean Spaces.

**2. Diagrama de Estados do Acidente**
- NULL → ABERTO (admin POST /accidents/open OU web POST /check/accident/open).
- ABERTO → ENCERRADO (admin POST /accidents/close, gera ZIP em background).
- ENCERRADO → REMOVIDO (admin DELETE /accidents/{id}, somente perfil=9, hard delete).
- Nota sobre o índice único parcial `ix_accidents_single_active` que garante no máximo 1 acidente aberto.
- Descrição dos campos `opened_at` / `closed_at` que codificam o estado.

**3. Sequência do Ciclo de Pedido de Ajuda**
- Diagrama de sequência mostrando: Check Web SPA → POST /check/accident/report {status:"help"} → web_check.py → accident_lifecycle.py → INSERT accident_user_reports → cria EmailDeliveryLog (queued) → notifyBroker → email_sender.py (background) → SMTP → caixas de e-mail dos admins.
- Detalhe de que a tabela HTML no e-mail é gerada por `accident_situation_table.py`.

**4. Mapa de Privilégios Admin por Endpoint**
- Tabela com 3 colunas: Endpoint / Autenticação / Requisito de perfil.
- GET /accidents/active: require_admin_session → qualquer admin (perfil 0, 1, 9...).
- POST open/close, GET list/archive, wizard/projects, wizard/locations: require_full_admin_session → dígito "1" OU "9" no perfil.
- DELETE /accidents/{id}: require_full_admin_session + verificação interna → APENAS perfil=9.
- Web endpoints: sessão web do usuário.
- Explicação do sistema de dígitos compostos (0=limitado, 1=full admin, 2=transport, 9=super-admin).

**5. Mapa de Arquivos por Função**
- Tabela texto com função → arquivo principal para: estado, renderização, arquivo ZIP, e-mails, storage, endpoints admin/web, modelos, schemas, SSE, auth, log.

**6. Tabelas do Banco de Dados**
- Descrição esquemática de todas as 5 tabelas do Modo Acidente com campos, tipos, FKs, constraints e índices.

**7. Eventos de Log (`check_events`)**
- Tabela com os 6 action names usados (≤16 chars), quando são gerados e qual o source.

### Arquivos alterados nesta tarefa

- `docs/descritivos/modo_acidente_arquitetura.md` (criado — documento de arquitetura)

---

## Task L1 -- Concluido

### Resumo detalhado

**Objetivo:** Criar fixtures pytest reutilizáveis para os testes do Modo Acidente, disponíveis automaticamente em qualquer `test_*.py` do projeto.

### Abordagem

Criado `tests/conftest_accident.py` como arquivo de plugin pytest, registrado via `pytest_plugins = ["tests.conftest_accident"]` no `tests/conftest.py` existente. Isso garante que todas as fixtures são descobertas automaticamente por pytest sem nenhuma importação manual nos arquivos de teste.

### Fixtures implementadas

**`accident_project`**
- Escopo: `function`
- Cria (ou reutiliza) `Project(name="P-Test", country_code="SG", ...)` no shared test DB.
- Usa `SessionLocal` + lógica `upsert` idempotente (create_or_reuse) para evitar conflitos entre execuções.

**`accident_location`**
- Escopo: `function`
- Depende de `accident_project`.
- Cria (ou reutiliza) `ManagedLocation(local="L-Test", latitude=1.3521, longitude=103.8198, projects_json='["P-Test"]', tolerance_meters=50)`.

**`user_in_project`**
- Escopo: `function`
- Depende de `accident_project`.
- Cria (ou reutiliza) `User(chave="LTST", perfil=0, checkin=True, email="l1user@test.example.com", projeto="P-Test")`.
- Senha setada via `hash_password` para suportar login via TestClient se necessário.

**`admin_perfil_1`**
- Escopo: `function`
- Cria (ou reutiliza) `User(chave="LA01", perfil=1)` — full admin (dígito "1" no perfil).
- Realiza login via `POST /api/admin/auth/login` com TestClient.
- Retorna `AdminSession(user, client)` — NamedTuple com o objeto User e o TestClient autenticado.

**`admin_perfil_9`**
- Escopo: `function`
- Cria (ou reutiliza) `User(chave="LA09", perfil=9)` — super-admin (FULL_ACCESS_DIGIT).
- Retorna `AdminSession(user, client)` da mesma forma.

**`open_accident_fixture`**
- Escopo: `function`
- Depende de `accident_project` e `admin_perfil_1`.
- Setup: fecha qualquer acidente aberto existente e deleta rows filhas (archive, video, reports), depois chama `open_accident(origin="admin", custom_location_name="Fixture Zone")`.
- Yield: o objeto `Accident` aberto.
- Teardown: chama `close_accident` se o acidente ainda estiver ativo. Ambos `notify_admin_data_changed` e `notify_web_check_data_changed` são patchados durante setup e teardown para evitar dependência de Postgres.
- Helper privado `_wipe_accident_rows(db)` e `_ensure_admin_row(db, user)` são usados tanto no setup quanto no teardown.

**`mock_smtp`**
- Escopo: `function`
- Patcha `smtplib.SMTP` e `smtplib.SMTP_SSL` com um único `MagicMock`.
- O mock suporta context manager (`__enter__`/`__exit__`).
- `mock_smtp.sent_messages` (lista) acumula todos os objetos `email.message.Message` passados para `send_message()`.
- Yield: o MagicMock configurado.

**`mock_storage`**
- Escopo: `function`
- Patcha `sistema.app.services.object_storage.upload_stream` com uma função fake que retorna `"https://fake-storage.example.com/{object_key}"`.
- Yield: o objeto `patch` para inspeção de `call_count`, `call_args`, etc.

### Tipo auxiliar

`AdminSession` — `NamedTuple` com campos `(user: User, client: TestClient)`. Permite que fixtures e testes desconstruam naturalmente: `user, client = admin_perfil_1`.

### Integração com conftest.py

`tests/conftest.py` recebeu a linha:
```python
pytest_plugins = ["tests.conftest_accident"]
```
Isso registra o arquivo como plugin pytest, tornando todas as 8 fixtures disponíveis globalmente sem nenhuma importação explícita nos arquivos de teste.

### Verificação

- `python -c "from tests.conftest_accident import ..."` — importa sem erro.
- `pytest tests/routers/test_admin_accidents.py::test_active_requires_session` — passa (conftest plugin carregado corretamente).
- `pytest tests/services/test_accident_lifecycle.py tests/services/test_accident_event_logging.py tests/models/test_accident_models.py` — 33 testes passam.

### Arquivos alterados nesta tarefa

- `tests/conftest_accident.py` (criado — 8 fixtures + NamedTuple AdminSession)
- `tests/conftest.py` (editado — adicionado `pytest_plugins = ["tests.conftest_accident"]`)
