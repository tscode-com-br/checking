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
