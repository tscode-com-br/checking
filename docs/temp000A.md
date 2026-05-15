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
