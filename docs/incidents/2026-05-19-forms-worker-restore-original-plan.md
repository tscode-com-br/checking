# Plano de remediação do Forms — to-do list de prompts para agente de IA

> **Contexto único, leia antes de qualquer prompt abaixo.**
>
> O sistema **Checking** (FastAPI + SQLAlchemy + Postgres + ESP32 + SPAs `/admin` e `/check`) tem um módulo que automatiza o preenchimento de um Microsoft Forms gerencial a cada check-in/check-out. O fluxo é assíncrono:
>
> 1. Endpoints `POST /api/scan` ([sistema/app/routers/device.py](../sistema/app/routers/device.py)), `POST /api/web/check` ([sistema/app/routers/web_check.py](../sistema/app/routers/web_check.py)), `POST /api/mobile/events/submit` e `POST /api/mobile/events/forms-submit` ([sistema/app/routers/mobile.py](../sistema/app/routers/mobile.py)) recebem o evento.
> 2. `enqueue_forms_submission(...)` ([sistema/app/services/forms_queue.py](../sistema/app/services/forms_queue.py)) grava em `forms_submissions` com `status='pending'` e responde 202 imediatamente.
> 3. Um processo separado (`python -m sistema.app.forms_worker_main`, imagem `forms-worker-runtime` do [Dockerfile](../Dockerfile)) abre Chromium headless via Playwright, navega até `settings.forms_url`, preenche os campos com base nos XPaths em `assets/xpath/*.txt` e marca o item como `success` ou `failed`. Lógica em [sistema/app/services/forms_worker.py](../sistema/app/services/forms_worker.py) e [sistema/app/services/forms_queue.py](../sistema/app/services/forms_queue.py).
>
> **Diagnóstico atual ([docs/temp001A.md](temp001A.md) — investigação original):**
>
> - **Causa raiz:** o deploy de produção usa [.github/workflows/deploy-oceandrive-api-only.yml](../.github/workflows/deploy-oceandrive-api-only.yml), que sobe somente [docker-compose.api.yml](../docker-compose.api.yml). Esse compose **não declara o serviço `forms-worker`**. O único compose que o declara é [docker-compose.yml](../docker-compose.yml) (uso local/full-stack). Resultado: todo evento é enfileirado e nunca consumido. A fila `forms_submissions` cresce sem parar com `status='pending'`, o Microsoft Forms nunca é preenchido e o dashboard gerencial nunca recebe nada.
> - O healthcheck `python -m sistema.app.forms_worker_healthcheck` em prod retorna `{"reason":"forms worker not running","status":"unhealthy"}` (reproduzido localmente).
> - Fragilidades secundárias que vão estourar assim que o worker voltar:
>   - XPaths absolutos por posição (`assets/xpath/*.txt`) — quebram com qualquer redesign do MS Forms.
>   - `submit_with_retries` não retenta `FormsStepTimeoutError`/`FormsStepValidationError` ([sistema/app/services/forms_worker.py:202](../sistema/app/services/forms_worker.py#L202)).
>   - Sem autenticação Microsoft — se a privacidade do Form for "people in my org only", a primeira XPath cai no login wall.
>   - `enqueue_forms_submission` não consulta `settings.forms_queue_enabled`; a API enfileira mesmo com worker desligado e ainda responde "queued".
>   - Sem DLQ, sem TTL, sem alarme operacional.
>
> **Objetivo geral deste plano:** restabelecer o consumo da fila em produção, expor o sucesso/erro do envio do Forms na tabela `users` e na tabela `checkinghistory`, refletir essa informação no Check Web (rótulos nos containers "Último Check-In" e "Último Check-Out") e no painel admin (nova coluna "Forms" antes da coluna "Local" nas tabelas "Usuários em Check-In" e "Usuários em Check-Out"), e tornar a integração com o Forms robusta a mudanças de DOM.
>
> **Regras de execução para todo agente que assumir um prompt:**
>
> - Siga as convenções do [CLAUDE.md](../CLAUDE.md) (modelos `Mapped[T]`, `CheckEvent.action` ≤ 16 chars, notificar SSE com `notify_admin_data_changed()` / `notify_web_check_data_changed()`).
> - **Sempre rode os testes existentes antes de qualquer alteração** para ter baseline verde; depois rode novamente após a alteração.
> - **Não edite código em produção sem antes rodar o plano de testes do prompt correspondente.**
> - Para UI: subir `uvicorn sistema.app.main:app --reload` e validar manualmente no browser; tipo-checagem não substitui teste de UX.
> - Para mudanças de schema: usar Alembic (`alembic revision -m "..."` + `alembic upgrade head`). Nunca alterar `Base.metadata.create_all` sem migração equivalente.
> - **Não amende commits — sempre criar commits novos.** Não usar `--no-verify`.
> - Após cada prompt, parar e devolver um relatório curto (≤ 200 palavras) com: o que mudou, quais arquivos, quais testes passaram, quais ficaram para o próximo prompt.

---

## Fase 0 — Confirmação operacional em produção (sem alterar código)

### Prompt 0.1 — Snapshot do estado real da fila e do worker em produção

> **Tarefa:** SSH na droplet e provar o diagnóstico antes de qualquer mudança.
>
> **Contexto:** Suspeitamos que `forms_submissions.status='pending'` cresceu sem ser consumido desde a Fase 2 do incidente 504 ([docs/incidents/2026-05-04-504-phase2-forms-flow-summary.md](incidents/2026-05-04-504-phase2-forms-flow-summary.md)). Precisamos do número real (idade do mais antigo, contagem por status) para escolher entre apenas restabelecer o worker (rodar o backlog) ou expurgar e reiniciar.
>
> **Passos:**
> 1. SSH na droplet (`OCEAN_HOST` / `OCEAN_USER` do GitHub Secrets).
> 2. `cd` para o diretório do deploy (mesmo que o workflow `deploy-oceandrive-api-only.yml` usa).
> 3. Rodar e capturar a saída de:
>    - `docker compose -f docker-compose.api.yml ps` — provar ausência do container `forms-worker`.
>    - `docker compose -f docker-compose.api.yml exec -T db psql -U postgres -d checking -c "select status, count(*) from forms_submissions group by status order by 1;"`
>    - `docker compose -f docker-compose.api.yml exec -T db psql -U postgres -d checking -c "select min(created_at), max(created_at) from forms_submissions where status='pending';"`
>    - `docker compose -f docker-compose.api.yml exec -T db psql -U postgres -d checking -c "select count(*) from forms_submissions where status='pending' and created_at < now() - interval '24 hours';"`
>    - `curl -sS http://127.0.0.1:18080/api/health | python -m json.tool` — confirmar `forms_worker.status=degraded` ou `unknown`.
>    - `docker logs checkcheck-api-1 --tail 200 | grep -i forms` — procurar logs de enqueue recentes.
> 4. Persistir tudo em `docs/temp002_phase0_snapshot.md` (criar o arquivo) com data/hora UTC + SGT.
>
> **Não alterar nada**, apenas observar. Devolver: backlog total, idade do mais antigo, último timestamp `success`/`failed`. Essa baseline alimenta os prompts 1.x.

### Prompt 0.2 — Verificar comportamento real da URL do Forms

> **Tarefa:** Confirmar se o Microsoft Forms aceita envios anônimos ou exige login Microsoft, e capturar o DOM "vivo" para alimentar a refatoração de XPaths (Fase 6).
>
> **Contexto:** A URL configurada em `settings.forms_url` ([sistema/app/core/config.py:29](../sistema/app/core/config.py#L29)) é `https://forms.office.com/Pages/ResponsePage.aspx?id=QWJvW1ea5EuOUB36cueaV-4C0XpFTa1LmJM_FjZpp4pUOTFGR1QwSk00Vk5KQ0ExNUMzQldRSkpHWCQlQCN0PWcu&origin=QRCode`. Se a configuração do form for "pessoas da minha organização", o Playwright headless sem cookies vai cair no login wall e a primeira XPath (`digitar_chave`) vai dar timeout.
>
> **Passos:**
> 1. Abrir a URL acima em uma janela anônima do Chrome (sem login Microsoft) e em uma janela normal autenticada na conta corporativa. Comparar:
>    - O form carrega na janela anônima? Ou exige login?
>    - Quantos campos visíveis? Em que ordem?
>    - Quais textos das opções? (Normal / Retroativo, Check-in / Check-out, lista de projetos)
> 2. Inspecionar o DOM (DevTools → Elements) e capturar para cada campo:
>    - `id` (se existir), `name`, `data-automation-id`, `aria-label`, `role`, classe.
>    - HTML mínimo do elemento + 1 nível de ancestral.
> 3. Repetir o teste com `playwright open --device "Desktop Chrome" https://forms.office.com/...` (Playwright headed mode) e comparar.
> 4. Tirar 4 screenshots: form vazio, form preenchido, momento do clique em Enviar, tela de sucesso após envio.
> 5. Documentar em `docs/temp002_phase0_forms_inspection.md`:
>    - Resposta a: o form é público ou requer SSO?
>    - Estrutura de DOM observada (com seletores estáveis sugeridos — preferir `data-automation-id`, `aria-label`, `role`, `name`; evitar XPath posicional).
>    - Texto exato da tela de sucesso (palavras + idioma — afeta `assets/xpath/sucesso.txt`).
>
> **Saída:** o arquivo `.md` acima + 4 PNGs em `docs/temp002_phase0_screenshots/`. Não altera código nesta etapa.

---

## Fase 1 — Restabelecer o consumo da fila em produção

### Prompt 1.1 — Adicionar serviço `forms-worker` ao `docker-compose.api.yml`

> **Tarefa:** Tornar o compose de produção idêntico, em termos de serviços rodando, ao [docker-compose.yml](../docker-compose.yml) no que diz respeito ao Forms.
>
> **Contexto:** O alvo é manter o deploy "API-only" tal como está (o time já decidiu separar `app` web do worker), mas adicionar um container irmão `forms-worker` no mesmo compose, compartilhando o volume `event_archives` (onde o worker escreve `forms_worker_health.json` lido pelo `/api/health` da API).
>
> **Arquivos a inspecionar:**
> - [docker-compose.yml](../docker-compose.yml) (linhas 97-129 — bloco `forms-worker` existente)
> - [docker-compose.api.yml](../docker-compose.api.yml) (estado atual sem worker)
> - [Dockerfile](../Dockerfile) (target `forms-worker-runtime`, linhas 22-27)
> - [deploy/docker/Dockerfile.api](../deploy/docker/Dockerfile.api) (referenciado pelo `docker-compose.api.yml`)
> - [sistema/app/forms_worker_main.py](../sistema/app/forms_worker_main.py) (entrypoint)
> - [sistema/app/services/forms_queue.py:598-670](../sistema/app/services/forms_queue.py#L598-L670) (supervisor)
>
> **O que fazer:**
> 1. **Decidir a imagem** do worker. Duas opções:
>    - **(A) recomendado)** Criar `deploy/docker/Dockerfile.forms-worker` espelhando `deploy/docker/Dockerfile.api`, mas com `CMD ["python", "-m", "sistema.app.forms_worker_main"]` e mantendo `playwright install --with-deps --only-shell chromium`. Vantagem: separação clara, possibilidade de tag/build distinto.
>    - **(B)** Reusar `deploy/docker/Dockerfile.api` (que já instala Playwright) e sobrescrever o `command:` no compose para `python -m sistema.app.forms_worker_main`. Vantagem: uma imagem só, build mais curto.
>    - Use **(B)** se o time prioriza simplicidade de pipeline; **(A)** se prioriza isolar dependências futuras. Se o agente não tiver autorização para escolher, pergunte ao usuário antes de editar.
> 2. Adicionar bloco `forms-worker:` em [docker-compose.api.yml](../docker-compose.api.yml) replicando o bloco de [docker-compose.yml:97-129](../docker-compose.yml#L97-L129), porém:
>    - `image: ${CHECKCHECK_FORMS_WORKER_IMAGE:-checkcheck-forms-worker:local}` (mesmo padrão da api).
>    - `build:` apontando para o Dockerfile escolhido em (A) ou (B).
>    - `depends_on: db: { condition: service_healthy }`.
>    - Compartilhar o mesmo `event_archives` volume já definido.
>    - Healthcheck: `python -m sistema.app.forms_worker_healthcheck`, interval 15s, retries 3.
>    - Mesma `DATABASE_URL`, `FORMS_URL`, `TZ_NAME`, `FORMS_TIMEOUT_SECONDS`, `FORMS_MAX_RETRIES`, `FORMS_WORKER_HEALTH_*` da api.
>    - `FORMS_QUEUE_ENABLED: ${FORMS_QUEUE_ENABLED:-true}`.
>    - Pool de DB menor: `DATABASE_POOL_SIZE=2`, `DATABASE_MAX_OVERFLOW=1`.
> 3. **Não** remover/alterar o bloco da `api`; o flag `FORMS_QUEUE_ENABLED` no container da api só governa o snapshot reportado em `/api/health` (a api não consome a fila desde a Fase 2).
>
> **Validação local antes de commitar:**
> - `docker compose -f docker-compose.api.yml config` → valida sintaxe.
> - `docker compose -f docker-compose.api.yml build forms-worker` → build da imagem nova.
> - `docker compose -f docker-compose.api.yml up -d db migrate api forms-worker` → tudo sobe.
> - `docker compose -f docker-compose.api.yml exec forms-worker python -m sistema.app.forms_worker_healthcheck` → exit 0, `running=true`.
> - `curl http://127.0.0.1:18080/api/health` → `forms_worker.status=ok`.
>
> **Commit:** `feat(deploy): provision forms-worker in api-only compose stack` mais um parágrafo explicando o motivo (regressão da Fase 2).

### Prompt 1.2 — Atualizar o workflow GitHub Actions de deploy da API

> **Tarefa:** Garantir que o CI faz pull/build/up do novo serviço.
>
> **Arquivos a alterar:**
> - [.github/workflows/deploy-oceandrive-api-only.yml](../.github/workflows/deploy-oceandrive-api-only.yml) (linhas 144-173 — step "Pull and restart API services")
> - [.github/workflows/deploy-oceandrive.yml](../.github/workflows/deploy-oceandrive.yml) (se houver step equivalente).
>
> **O que fazer:**
> 1. No script do `appleboy/ssh-action`, adicionar (após o pull da api):
>    - `CHECKCHECK_FORMS_WORKER_IMAGE="$FORMS_WORKER_IMAGE" docker compose -f docker-compose.api.yml pull forms-worker` (apenas se a imagem for separada — opção A do prompt 1.1).
>    - `CHECKCHECK_FORMS_WORKER_IMAGE="$FORMS_WORKER_IMAGE" docker compose -f docker-compose.api.yml up -d --no-build --force-recreate forms-worker`.
> 2. Se a imagem do worker for separada (opção A), adicionar um job `build-and-push-forms-worker` espelhando o que já existe para a api, registrando em `ghcr.io/tscode-com-br/checkcheck-forms-worker:${{ github.sha }}`. Verificar [.github/workflows/deploy-oceandrive.yml](../.github/workflows/deploy-oceandrive.yml) para descobrir o padrão exato de build/push.
> 3. Estender o step "Validate API health" para também verificar:
>    - `docker compose -f docker-compose.api.yml exec -T forms-worker python -m sistema.app.forms_worker_healthcheck`
>    - JSON deve trazer `status=ok`. Falhar o deploy se vier `unhealthy`.
> 4. Atualizar [deploy/smoke/validate_target.sh](../deploy/smoke/validate_target.sh) se for usado para o novo serviço.
>
> **Testes:**
> - Rodar `act` (ou simular localmente o script bash) para garantir que o pull/up não quebra a sintaxe.
> - Disparar o workflow em uma branch de homologação **antes** de mergear na main. Validar que: api fica up, forms-worker fica up, `/api/health` reporta `forms_worker.status=ok`.

### Prompt 1.3 — Defesa em profundidade: bloquear enqueue quando o consumidor está parado

> **Tarefa:** Adicionar verificação preventiva para que a API não sigília enfileirando quando o worker está reconhecidamente down. Hoje [enqueue_forms_submission](../sistema/app/services/forms_queue.py#L303-L338) sempre persiste, e os endpoints sempre respondem "queued for Forms submission" mesmo quando o worker está desligado — foi o que mascarou o incidente.
>
> **Arquivos:**
> - [sistema/app/services/forms_queue.py](../sistema/app/services/forms_queue.py) (`enqueue_forms_submission`, `get_forms_worker_observed_snapshot`)
> - [sistema/app/services/forms_submit.py](../sistema/app/services/forms_submit.py)
> - [sistema/app/routers/device.py](../sistema/app/routers/device.py) (resposta `queued`)
> - [sistema/app/routers/mobile.py](../sistema/app/routers/mobile.py)
> - [sistema/app/schemas.py](../sistema/app/schemas.py) (`MobileSubmitResponse`)
>
> **Decisão de design:** **NÃO** bloquear o enqueue (o histórico precisa ser preservado mesmo se o worker estiver fora). Em vez disso:
> 1. Após `enqueue_forms_submission`, ler o snapshot do worker com `get_forms_worker_observed_snapshot()`.
> 2. Se `running=false` ou `stale=true` por mais de `forms_worker_health_stale_seconds`, gravar um `CheckEvent` com `source="system"`, `action="forms_warn"` (≤ 16 chars), `status="warning"`, `message="Forms enqueued while worker is down"` e `details=` com `backlog_count` atual.
> 3. Adicionar campo opcional `worker_healthy: bool` em `MobileSubmitResponse`. Default `True`. Quando o worker está down, retornar `False`. O front-end pode usar isso para mostrar aviso (não é obrigatório nesta fase).
>
> **Testes:**
> - Unitário: simular snapshot com `running=false` e provar que o CheckEvent de warning é gravado.
> - Unitário: simular snapshot saudável e provar que o CheckEvent **não** é gravado.
> - Garantir que a verificação não adiciona mais que ~5ms ao path crítico (medir com `time.perf_counter`).

---

## Fase 2 — Schema: campo `forms` em `users` e `checkinghistory`

### Prompt 2.1 — Migração Alembic do campo `forms`

> **Tarefa:** Adicionar coluna `forms` (BOOLEAN, NULLABLE) nas tabelas `users` e `checkinghistory`.
>
> **Motivação:** O Check Web e o admin precisam diferenciar três estados por evento:
> - `True` — o worker preencheu o Forms e o XPath de sucesso (`assets/xpath/sucesso.txt`) apareceu.
> - `False` — o worker tentou e falhou (timeout/validação/erro).
> - `NULL` — ainda pendente ou não-aplicável (ex.: eventos legados anteriores à migração).
>
> **Arquivos:**
> - Criar `alembic/versions/0062_add_forms_flag_to_users_and_checkinghistory.py`.
> - Atualizar [sistema/app/models.py](../sistema/app/models.py): `User` (linha 61) e `CheckingHistory` (linha 675) recebem `forms: Mapped[bool | None] = mapped_column(Boolean, nullable=True)`.
>
> **Migração — siga este esqueleto:**
>
> ```python
> revision = "0062_add_forms_flag"
> down_revision = "0061_add_accident_tables"
>
> def upgrade() -> None:
>     op.add_column("users", sa.Column("forms", sa.Boolean(), nullable=True))
>     op.add_column("checkinghistory", sa.Column("forms", sa.Boolean(), nullable=True))
>
> def downgrade() -> None:
>     op.drop_column("checkinghistory", "forms")
>     op.drop_column("users", "forms")
> ```
>
> **Atenção:** verificar com `alembic heads` qual é o head atual antes de fixar `down_revision`. Se `0061_add_accident_tables` não for o head, ajustar.
>
> **Testes:**
> - `alembic upgrade head` em SQLite (`test_checking.db`) — checar `PRAGMA table_info(users)` e `PRAGMA table_info(checkinghistory)`.
> - `alembic downgrade -1` e `alembic upgrade head` — round-trip.
> - Rodar `pytest tests/services/test_forms_submit_resilience.py` para garantir que os testes existentes seguem verdes com o novo campo (nullable).

---

## Fase 3 — Backend: gravar o resultado do Forms em `users` e `checkinghistory`

### Prompt 3.1 — Persistir o resultado em `users.forms`

> **Tarefa:** Quando o worker finaliza uma submissão, atualizar `users.forms` do usuário correspondente (porque `users` armazena a "última atividade").
>
> **Arquivos:**
> - [sistema/app/services/forms_queue.py](../sistema/app/services/forms_queue.py) — função `_process_submission` (linha 396-470).
> - [sistema/app/services/user_sync.py](../sistema/app/services/user_sync.py) — `apply_user_state` (verificar onde `user.checkin`/`user.time` são atualizados).
>
> **Lógica:**
> - Após decidir `submission.status = "success"` ou `"failed"`, **se** esse evento ainda é o mais recente do usuário (comparar com `User.time`), atualizar `user.forms = (status == "success")`.
> - Critério de "mais recente": carregar o `User` por `chave=submission.chave`. Se `user.time` é igual ao `event_time` do enqueue ou se `user.checkin == (submission.action == "checkin")` e `user.time` está dentro de uma janela curta (ex.: igual ao timestamp do enqueue), considerar que o evento ainda é o vigente.
> - **Cuidado com race conditions:** entre o enqueue e o processamento, o usuário pode ter feito outro check. Nesse caso, **não** sobrescrever `user.forms`. O valor atual de `user.forms` deve refletir sempre a última ação registrada em `users`.
>
> **Implementação sugerida (pseudocódigo):**
> ```python
> user = db.execute(select(User).where(User.chave == submission.chave)).scalar_one_or_none()
> if user and user.time and submission.created_at and \
>    abs((user.time - submission.created_at).total_seconds()) < 5 and \
>    user.checkin == (submission.action == "checkin"):
>     user.forms = (submission.status == "success")
> ```
>
> Discutir com o usuário se a janela de 5s é adequada ou se devemos ter um vínculo explícito (ex.: armazenar `users.last_forms_request_id` para correlação determinística — mais correto, custa 1 coluna a mais).
>
> **Testes:**
> - Unit: enqueue → processar com `success` → `user.forms == True`.
> - Unit: enqueue → processar com `failed` → `user.forms == False`.
> - Unit: enqueue → usuário faz novo check-in antes do worker terminar → `user.forms` reflete o evento mais recente, não o antigo.

### Prompt 3.2 — Persistir o resultado em `checkinghistory.forms`

> **Tarefa:** Atualizar a linha correspondente de `checkinghistory` com o resultado da submissão.
>
> **Arquivos:**
> - [sistema/app/services/forms_queue.py](../sistema/app/services/forms_queue.py) (`_process_submission`)
> - [sistema/app/services/checking_history.py](../sistema/app/services/checking_history.py) (ver função que escreve `CheckingHistory`)
> - [sistema/app/models.py](../sistema/app/models.py) (`CheckingHistory` — `__table_args__` linha 677 tem `UniqueConstraint("chave", "atividade", "projeto", "time", "informe")`)
>
> **Lógica:**
> - O `UniqueConstraint` acima dá a chave natural para localizar a linha: `(chave, atividade, projeto, time, informe)`. O worker já tem `submission.chave`, `submission.action` (mapear `"checkin"→"check-in"`, `"checkout"→"check-out"`), `submission.projeto`, `submission.ontime` (mapear `True→"normal"`, `False→"retroativo"`). Falta `time` — capturar no momento do enqueue e persistir em `forms_submissions` (já há `created_at` mas pode não bater com `event_time`).
> - Decisão recomendada: adicionar coluna `event_time` em `forms_submissions` (migração separada — incluir no prompt 2.1 se preferir um único deploy).
>
> **Implementação:**
> ```python
> stmt = (
>     update(CheckingHistory)
>     .where(
>         CheckingHistory.chave == submission.chave,
>         CheckingHistory.atividade == ("check-in" if submission.action == "checkin" else "check-out"),
>         CheckingHistory.projeto == submission.projeto,
>         CheckingHistory.time == submission.event_time,
>         CheckingHistory.informe == ("normal" if submission.ontime else "retroativo"),
>     )
>     .values(forms=(submission.status == "success"))
> )
> db.execute(stmt)
> ```
>
> **Testes:**
> - Unit: simular enqueue de check-in normal → executar `_process_submission` com sucesso → confirmar `CheckingHistory.forms == True`.
> - Unit: idem para falha → `forms == False`.
> - Unit: enqueue para um evento que **não tem** linha em `checkinghistory` (caso edge) → não levantar exceção, gravar log de warning.

### Prompt 3.3 — Expor `forms` em respostas e SSE

> **Tarefa:** Refletir o flag nas APIs já consumidas pelas SPAs.
>
> **Arquivos:**
> - [sistema/app/schemas.py](../sistema/app/schemas.py) — `MobileSyncStateResponse` (o que o Check Web consome), schemas de presença usados pelo admin.
> - [sistema/app/routers/web_check.py](../sistema/app/routers/web_check.py) — endpoint que retorna estado do usuário.
> - [sistema/app/routers/admin.py](../sistema/app/routers/admin.py) — endpoint que serve a tabela "Usuários em Check-In/Check-Out".
> - [sistema/app/services/admin_updates.py](../sistema/app/services/admin_updates.py) — broker SSE: notificar quando `forms` muda.
> - [sistema/app/services/user_activity.py](../sistema/app/services/user_activity.py) (ou onde a query do admin é montada).
>
> **O que adicionar:**
> 1. Campo `forms: bool | None` em todos os schemas que devolvem o "último check" — `MobileSyncStateResponse.last_checkin`, `.last_checkout`, e as linhas de presença do admin.
> 2. Para o admin: a linha vem de `users` se for "a atividade vigente", e de `checkinghistory` para o "lado oposto" (ex.: usuário fez check-out; a linha em `users` mostra o check-out vigente, e a linha em `checkinghistory` mostra o último check-in). Isso reproduz a regra descrita pelo usuário.
> 3. Após `_process_submission` commitar, chamar `notify_admin_data_changed(submission.action)` (já existe na linha 470) **e** `notify_web_check_data_changed()` (novo) para forçar refresh do Check Web do usuário afetado.
>
> **Testes:**
> - Unit: chamar o endpoint de estado do Check Web depois de um processamento `success` → response inclui `last_checkin.forms == True`.
> - Unit: idem para o endpoint do admin.
> - Integration: subscrever ao SSE do Check Web e provar que recebe evento após o worker terminar.

---

## Fase 4 — Front-end Check Web: rótulos "Forms: enviado!" / "Forms: erro!"

### Prompt 4.1 — Marcação HTML + i18n

> **Tarefa:** Adicionar as linhas em branco + rótulo em cada um dos containers "Último Check-In" e "Último Check-Out" no Check Web, com suporte i18n.
>
> **Arquivos:**
> - [sistema/app/static/check/index.html](../sistema/app/static/check/index.html) (linhas ~58-68 contêm os blocos `history-item`)
> - [sistema/app/static/check/i18n-dictionaries.js](../sistema/app/static/check/i18n-dictionaries.js) (novas chaves em `pt/en/zh/ms/id/tl`)
> - [sistema/app/static/check/app.js](../sistema/app/static/check/app.js) (atualizar render do `lastCheckinValue`/`lastCheckoutValue`)
> - [sistema/app/static/check/web-client-state.js](../sistema/app/static/check/web-client-state.js) (consumir o novo campo `forms`)
> - CSS: provavelmente [sistema/app/static/check/](../sistema/app/static/check/) — encontrar o arquivo onde `history-label`/`history-value` são estilizados.
>
> **Estrutura HTML alvo por container (mantendo o `history-item` existente):**
> ```html
> <div class="history-item">
>   <p id="historyTitle" class="history-label">Último Check-In</p>
>   <p id="lastCheckinValue" class="history-value">--</p>
>   <p id="lastCheckinFormsStatus" class="history-forms-status" hidden>
>     <span class="forms-label">Forms:</span>
>     <span class="forms-state" data-state="">--</span>
>   </p>
> </div>
> ```
> (idem para `lastCheckout*`)
>
> **CSS necessário (novo arquivo ou bloco):**
> ```css
> .history-forms-status {
>   margin-top: 0.5rem;          /* "Linha 6 em branco" */
>   font-size: 0.8em;            /* menor que .history-label */
>   font-weight: normal;
> }
> .history-forms-status .forms-label { color: #000; font-weight: normal; }
> .history-forms-status .forms-state[data-state="ok"]    { color: #001f5b; font-weight: bold; }  /* azul-marinho */
> .history-forms-status .forms-state[data-state="error"] { color: #c10000; font-weight: bold; }
> ```
>
> **i18n — adicionar em todas as 6 línguas:**
> ```js
> accident: { ... },
> checkHistory: {
>   formsLabel: "Forms:",
>   formsSent: "enviado!",
>   formsError: "erro!",
> }
> ```
> (traduções: en `sent!/error!`, zh `已发送!/错误!`, ms `dihantar!/ralat!`, id `terkirim!/galat!`, tl `naipadala!/error!`)
>
> **Lógica JS:**
> - Quando `state.last_checkin.forms === true` → mostrar com `data-state="ok"` e texto `t('checkHistory.formsSent')`.
> - Quando `=== false` → `data-state="error"` + `t('checkHistory.formsError')`.
> - Quando `null`/`undefined` → ocultar (`hidden` attr).
>
> **Validação visual obrigatória:**
> 1. `uvicorn sistema.app.main:app --reload --port 8000`.
> 2. Abrir `http://localhost:8000/check`, autenticar com uma chave de teste.
> 3. Simular sucesso (worker processa OK) → ver "Forms: **enviado!**" (azul-marinho).
> 4. Simular falha → ver "Forms: **erro!**" (vermelho).
> 5. Trocar idioma (se houver seletor) → verificar todas as 6 línguas.
> 6. Tirar 3 screenshots e anexar no PR.

### Prompt 4.2 — Cobertura de testes do Check Web

> **Tarefa:** Adicionar testes para o novo rótulo.
>
> **Arquivos:** `tests/static/test_check_web_forms_label.py` (criar). Se já houver harness para o Check Web, reaproveitar.
>
> **Cenários:**
> 1. `forms === true` → DOM contém `data-state="ok"` e texto traduzido.
> 2. `forms === false` → `data-state="error"`.
> 3. `forms === null` → `<p hidden>`.
> 4. Trocar `lang` global → texto atualiza.
> 5. Snapshot CSS (computed style) → `color: rgb(0, 31, 91)` para ok, `rgb(193, 0, 0)` para erro. (Pode ser feito via Playwright pegando `getComputedStyle`.)
>
> **Se o projeto não tiver harness JS:** usar Playwright Python (já está nas deps) para abrir o `/check`, injetar estado via `page.evaluate`, e validar o DOM.

---

## Fase 5 — Painel admin: coluna "Forms" antes de "Local"

### Prompt 5.1 — HTML + JS de render das tabelas de presença

> **Tarefa:** Inserir nova coluna `<th>Forms</th>` antes de `<th>Local</th>` nas tabelas "Usuários em Check-In" e "Usuários em Check-Out". O conteúdo de cada linha deve ser `Enviado` (azul-marinho, negrito) ou `Erro` (vermelho, negrito), ou `--` (cinza, normal) quando `forms` é null.
>
> **Arquivos:**
> - [sistema/app/static/admin/index.html](../sistema/app/static/admin/index.html) (linhas 230-241 e o bloco equivalente do check-out — ~270-285)
> - [sistema/app/static/admin/app.js](../sistema/app/static/admin/app.js) (função que renderiza `#checkinBody` e `#checkoutBody`; procurar por `presence-users-table` ou `checkinBody`)
> - CSS do admin — adicionar regras `.presence-forms-state[data-state]`.
>
> **HTML — adicionar no `<thead>` antes do `<th data-sort-key="local">`:**
> ```html
> <th><button type="button" class="sortable-header" data-sort-table="checkin" data-sort-key="forms"><span>Forms</span><span class="sort-indicator" aria-hidden="true"></span></button></th>
> ```
>
> **Render JS por linha — antes da célula `local`:**
> ```js
> const formsState = row.forms === true ? "ok" : row.forms === false ? "error" : "none";
> const formsLabel = row.forms === true ? "Enviado" : row.forms === false ? "Erro" : "--";
> td.innerHTML = `<span class="presence-forms-state" data-state="${formsState}">${formsLabel}</span>`;
> ```
>
> **Não esquecer:**
> - Atualizar o filtro de coluna se houver (`presence-controls`).
> - Adicionar suporte a ordenação por essa coluna (`data-sort-key="forms"`).
> - Garantir que o SSE atualiza a linha quando o worker termina o processamento.
>
> **Validação visual:**
> 1. Logar como admin → aba Check-In → ver coluna "Forms" antes de "Local".
> 2. Disparar um check-in real (ou via curl) → linha aparece com "Forms: --" enquanto pendente.
> 3. Aguardar worker processar → linha atualiza para "Enviado" ou "Erro" via SSE (sem F5).
> 4. Clicar no header "Forms" → ordena.

### Prompt 5.2 — Testes do admin

> **Tarefa:** Cobrir a nova coluna no admin.
>
> **Arquivos:** `tests/routers/test_admin_presence_forms_column.py` (criar).
>
> **Cenários:**
> 1. GET `/api/admin/presence/checkin` → response inclui `forms` por linha.
> 2. Render: snapshot HTML/DOM via Playwright valida posição da coluna (antes de "Local").
> 3. SSE: subscrever ao broker do admin, processar uma submissão, ver evento de update com `forms` mudado.

---

## Fase 6 — XPaths robustos + inspeção/atualização da URL do Forms

### Prompt 6.1 — Coletar DOM real do Microsoft Forms

> **Tarefa:** Auditar **todos** os 11 XPaths em [assets/xpath/](../assets/xpath/) contra o DOM real atual, e propor seletores resistentes a redesign.
>
> **Pré-requisito:** Prompt 0.2 deve ter sido executado.
>
> **Arquivos:**
> - `assets/xpath/botao_checkin.txt`
> - `assets/xpath/botao_checkout.txt`
> - `assets/xpath/botao_enviar.txt`
> - `assets/xpath/botao_normal.txt`
> - `assets/xpath/botao_projeto_P80.txt`
> - `assets/xpath/botao_projeto_P82.txt`
> - `assets/xpath/botao_projeto_P83.txt`
> - `assets/xpath/botao_retroativo.txt`
> - `assets/xpath/confirmar_chave.txt`
> - `assets/xpath/digitar_chave.txt`
> - `assets/xpath/sucesso.txt`
>
> **Estratégia recomendada — preferir seletores estáveis nesta ordem:**
> 1. `data-automation-id` (Microsoft Forms usa `textInput`, `submitButton`, `radioOption`, `checkboxOption`).
> 2. `role` + `aria-label` (ex.: `//*[@role="textbox" and contains(@aria-label, "chave")]`).
> 3. `name` ou `aria-labelledby`.
> 4. Texto visível normalizado (ex.: `//label[normalize-space(text())="Normal"]//input`).
> 5. Posição relativa a um label conhecido (ex.: `//*[contains(text(),"Digite a chave")]/following::input[1]`).
> 6. **Último recurso:** posição absoluta (o que está hoje).
>
> **Para cada XPath, produzir:**
> - XPath antigo (posicional).
> - XPath proposto (semântico, com fallback se possível).
> - Justificativa.
>
> **Exemplos prováveis (a verificar contra o DOM real coletado no Prompt 0.2):**
> - `digitar_chave.txt`: era `//*[@id="question-list"]/div[1]/div[2]/div/span/input` → propor `(//input[@data-automation-id="textInput"])[1]` ou `//div[@data-automation-id="questionItem"][.//*[contains(.,"chave")]][1]//input[@data-automation-id="textInput"]`.
> - `confirmar_chave.txt`: similar → `(//input[@data-automation-id="textInput"])[2]`.
> - `botao_enviar.txt`: era `//*[@id="form-main-content1"]/div/div/div[2]/div[3]/div/button` → propor `//button[@data-automation-id="submitButton"]` ou `//button[normalize-space(.)="Enviar"]`.
> - `sucesso.txt`: era `//*[@id="form-main-content1"]/div/div/div[2]/div[1]/div[2]/div[2]/span` → propor `//*[@role="heading" and (contains(., "Sua resposta foi enviada") or contains(., "Your response was submitted") or contains(., "obrigad"))]`.
> - `botao_normal.txt`: era `//*[@id="question-list"]/div[3]/div[2]/div/div/div[1]/div/label/span[1]/input` → propor `//label[normalize-space(.)="Normal"]//input[@type="radio"]`.
> - Projetos: `//label[normalize-space(.)="P80"]//input` etc.
>
> **Validação contra o form vivo:**
> 1. Script `scripts/forms_validate_xpaths.py` (criar): abre Playwright headed, navega para `settings.forms_url`, e para cada arquivo em `assets/xpath/` faz `page.locator(f"xpath={xpath}").count()`. Deve dar `1` para todos. Se der `0` ou `>1`, marca como falha. Imprime relatório.
> 2. Rodar o script localmente; só committar os novos XPaths se o script reportar 11 sucessos.
>
> **Documento de saída:** `docs/temp002_phase6_xpath_audit.md` com a tabela antes/depois.

### Prompt 6.2 — Suporte a fallback de seletores no `FormsWorker`

> **Tarefa:** Permitir que cada step tenha múltiplos XPaths candidatos, e o worker tente cada um na ordem.
>
> **Arquivos:**
> - [sistema/app/services/forms_worker.py](../sistema/app/services/forms_worker.py) (`load_xpath`, `_wait_for_step`)
> - `assets/xpath/*.txt` (formato muda de "uma linha = um xpath" para "uma linha por candidato; primeira que casar vence")
>
> **Mudança em `load_xpath`:**
> ```python
> def load_xpath_candidates(self, name: str) -> list[str]:
>     raw = (self.assets_dir / "xpath" / name).read_text(encoding="utf-8")
>     return [line.strip() for line in raw.splitlines() if line.strip() and not line.startswith("#")]
> ```
>
> **Mudança em `_wait_for_step`** (e `_is_step_visible`): aceitar uma lista de XPaths; em cada iteração do polling, testar cada candidato; o primeiro que ficar visível vence. Em caso de timeout, mensagem deve indicar todos os candidatos tentados.
>
> **Formato novo dos arquivos** (exemplo `digitar_chave.txt`):
> ```
> # Preferido: data-automation-id (estável em todas as versões observadas do MS Forms)
> (//input[@data-automation-id="textInput"])[1]
> # Fallback 1: por proximidade do label
> //div[@data-automation-id="questionItem"][.//*[contains(.,"Digite a chave")]][1]//input
> # Fallback 2: legado (posicional — manter por segurança até observar duas semanas estáveis com os novos)
> //*[@id="question-list"]/div[1]/div[2]/div/span/input
> ```
>
> **Testes:**
> - Unit: arquivo com 3 candidatos; mock do `page.locator` que só retorna match para o terceiro → worker usa o terceiro.
> - Unit: arquivo com candidatos onde o primeiro casa imediatamente → worker para no primeiro.
> - Unit: nenhum candidato casa → `FormsStepTimeoutError` com mensagem contendo todos os candidatos.

### Prompt 6.3 — Suporte a autenticação Microsoft (se Prompt 0.2 confirmar SSO obrigatório)

> **Tarefa:** Se o Forms exigir login Microsoft, plugar fluxo de autenticação no Playwright.
>
> **Arquivos:**
> - [sistema/app/services/forms_worker.py](../sistema/app/services/forms_worker.py)
> - [sistema/app/core/config.py](../sistema/app/core/config.py) — novas vars: `FORMS_AUTH_USER`, `FORMS_AUTH_PASSWORD`, `FORMS_STORAGE_STATE_PATH`.
> - [docker-compose.api.yml](../docker-compose.api.yml) — passar as vars ao container.
>
> **Estratégia:** **NÃO** automatizar o login interativo (Microsoft tem MFA, captcha, é frágil). Em vez disso:
> 1. **Setup manual único:** o admin executa `playwright codegen` localmente, faz login, exporta `storage_state.json`.
> 2. O arquivo é montado como secret no container.
> 3. `_submit_once` passa a usar `browser.new_context(storage_state=settings.forms_storage_state_path)`.
> 4. Rotina de health adicional: ao iniciar, o worker abre o form 1× e valida que o campo `digitar_chave` aparece. Se o `storage_state` expirou, falha imediatamente com mensagem clara.
>
> **Alternativa:** mudar a configuração do Form para "anyone with the link can respond" (decisão do dono do form — pode quebrar políticas de compliance).
>
> Pular este prompt se 0.2 confirmar que o form aceita acesso anônimo.

### Prompt 6.4 — Resiliência: retry em `FormsStepTimeoutError`

> **Tarefa:** Permitir retry quando o erro é "elemento não encontrado a tempo", já que o MS Forms às vezes carrega lentamente.
>
> **Arquivos:** [sistema/app/services/forms_worker.py:202-260](../sistema/app/services/forms_worker.py#L202-L260) (`submit_with_retries`).
>
> **Hoje:** apenas `PlaywrightTimeoutError` é retried.
> **Mudança:** retry também em `FormsStepTimeoutError` (mas **não** em `FormsStepValidationError`, que indica problema lógico que o retry não resolve).
> Manter o cap em `settings.forms_max_retries` (default 3) e adicionar back-off exponencial entre tentativas (1s, 2s, 4s).
>
> **Testes:**
> - Mock que dispara `FormsStepTimeoutError` 2× e sucesso na 3ª → worker reporta `success` com `retry_count=2`.
> - Mock que dispara 4× → reporta `failed` com `retry_count=3`.

---

## Fase 7 — Guardrails operacionais

### Prompt 7.1 — Alarme de backlog na fila

> **Tarefa:** Emitir alarme (CheckEvent + telemetria) quando o backlog do Forms passar de thresholds claros.
>
> **Arquivos:**
> - [sistema/app/services/forms_queue.py](../sistema/app/services/forms_queue.py) (`get_forms_queue_diagnostics`)
> - [sistema/app/routers/admin.py:2863](../sistema/app/routers/admin.py#L2863) (`get_forms_queue_diagnostics_view`)
> - Novo: [sistema/app/services/forms_alerts.py] — função `check_and_emit_backlog_alerts(db)` rodando periodicamente.
> - [sistema/app/core/config.py](../sistema/app/core/config.py) — `forms_backlog_warn_count: int = 50`, `forms_backlog_critical_count: int = 200`, `forms_backlog_max_age_seconds: int = 600`.
>
> **Regras:**
> - Warn quando `backlog_count > forms_backlog_warn_count` ou `oldest_pending_age_seconds > 300`.
> - Critical quando `> forms_backlog_critical_count` ou `> forms_backlog_max_age_seconds`.
> - Cada alarme: 1 `CheckEvent` (`source="system"`, `action="forms_alert"`, `status="warning"|"critical"`).
> - Debounce: não emitir o mesmo alarme mais de 1× a cada 5 minutos.
>
> **Onde rodar:** dentro do supervisor do worker ([sistema/app/services/forms_queue.py:598](../sistema/app/services/forms_queue.py#L598) `run_forms_submission_worker_forever`), uma vez a cada heartbeat.

### Prompt 7.2 — Tile "Forms" no painel admin

> **Tarefa:** Adicionar um card no dashboard admin mostrando: backlog atual, idade do mais antigo pending, taxa de sucesso nas últimas 24h, status do worker.
>
> **Arquivos:**
> - [sistema/app/static/admin/index.html](../sistema/app/static/admin/index.html) (nova seção)
> - [sistema/app/static/admin/app.js](../sistema/app/static/admin/app.js) (poller que chama `/api/admin/forms-queue/diagnostics`)
> - Endpoint já existe em [sistema/app/routers/admin.py:2863](../sistema/app/routers/admin.py#L2863).
>
> **UX mínimo:** 4 números + indicador de cor (verde/amarelo/vermelho) baseado em thresholds da Fase 7.1.

---

## Fase 8 — Plano de testes (DETALHADO)

> O objetivo é que **nenhum prompt anterior seja considerado "done" sem rodar o conjunto de testes abaixo aplicável a ele**. Crie ou estenda os arquivos indicados.

### Prompt 8.1 — Unit tests da fila e do worker (mocked)

> **Arquivos:** `tests/services/test_forms_queue.py` (criar se não existir), `tests/services/test_forms_worker.py` (criar).
>
> **Cenários obrigatórios — `forms_queue.py`:**
> 1. `enqueue_forms_submission` cria linha com `status='pending'`, todos os campos preenchidos corretamente.
> 2. `enqueue_forms_submission` com mesmo `request_id` levanta `IntegrityError`.
> 3. `_reserve_next_submission_id` retorna `None` quando não há `pending`.
> 4. `_reserve_next_submission_id` reserva atomicamente um item (status muda para `processing`).
> 5. Dois callers concorrentes (`threading.Thread`) chamando `_reserve_next_submission_id` no mesmo banco: cada um pega um item diferente, nenhum é duplo-processado.
> 6. `_process_submission` com resultado `success` → grava `status='success'`, `processed_at` preenchido, `last_error=None`.
> 7. `_process_submission` com falha → `status='failed'`, `last_error` truncado em 1000 chars.
> 8. `_process_submission` atualiza `User.forms` quando o evento ainda é o vigente (Prompt 3.1).
> 9. `_process_submission` **não** atualiza `User.forms` quando o usuário fez novo check depois.
> 10. `_process_submission` atualiza `CheckingHistory.forms` na linha certa (Prompt 3.2).
> 11. `get_forms_queue_diagnostics` retorna contagem correta por status.
> 12. `get_forms_worker_observed_snapshot` lê health file quando existe.
> 13. `get_forms_worker_observed_snapshot` fallback para `forms_submission_worker.snapshot()` quando não existe.
> 14. `FormsSubmissionWorker.start/stop` é idempotente.
>
> **Cenários obrigatórios — `forms_worker.py`:**
> 15. `load_xpath_candidates` retorna lista, ignora linhas vazias e comentários (`#`).
> 16. `_wait_for_step` com mock retornando match no 1º candidato → para no 1º.
> 17. `_wait_for_step` com match apenas no 3º → para no 3º.
> 18. `_wait_for_step` sem nenhum match → `FormsStepTimeoutError` listando candidatos.
> 19. `submit_with_retries` retenta `FormsStepTimeoutError` até `forms_max_retries`.
> 20. `submit_with_retries` **não** retenta `FormsStepValidationError`.
> 21. `submit_with_retries` faz back-off exponencial (verificar com `time.monotonic` mockado).
> 22. `_submit_once` chama os 8 steps na ordem correta (mocks de `page.locator`).
> 23. `_submit_once` para check-in chama `botao_checkin` + projeto; para check-out chama só `botao_checkout`.
> 24. `_submit_once` falha se `sucesso` aparece antes do clique em `botao_enviar`.

### Prompt 8.2 — Integration tests com Playwright + HTML estático (sem MS Forms real)

> **Tarefa:** Criar uma página HTML local que mimetiza a estrutura do MS Forms para testar o worker fim-a-fim sem dependência externa.
>
> **Arquivos a criar:**
> - `tests/fixtures/forms_html/form.html` — réplica simplificada do MS Forms (mesmos `data-automation-id`).
> - `tests/fixtures/forms_html/success.html` — página de "sua resposta foi enviada".
> - `tests/integration/test_forms_worker_end_to_end.py`.
>
> **Cenários:**
> 1. Worker abre o HTML local, preenche, clica enviar, vê sucesso → reporta `success`.
> 2. Worker abre HTML local com submit button removido → reporta `failed` com `failed_step="botao_enviar"`.
> 3. Worker com `sucesso` já visível antes do envio → reporta `failed` com mensagem específica.
> 4. Worker com XPath obsoleto + fallback novo → fallback funciona.
> 5. Worker em página com loading artificial (delay JS) → completa após delay.

### Prompt 8.3 — Smoke test contra o MS Forms real (gated por env)

> **Tarefa:** Teste E2E que **realmente envia** uma resposta de teste ao Forms produtivo.
>
> **Arquivos:** `tests/smoke/test_forms_live_submission.py`.
>
> **Proteção:** o teste só roda se `RUN_LIVE_FORMS_SMOKE=1`. Default skip. Usar uma `chave` de teste reservada (combinar com o dono do form para filtrar essas linhas nos relatórios).
>
> **Cenário único:** abrir Playwright, navegar até `settings.forms_url`, preencher com chave "TEST", projeto "P80", clicar enviar, esperar XPath de sucesso. Falhar se não chegar lá em 60s.
>
> **Rodar manualmente após:** cada mudança nos XPaths, cada mudança na `forms_url`, cada deploy de produção do worker.

### Prompt 8.4 — Integration test do fluxo completo API→Queue→Worker→DB

> **Arquivo:** `tests/integration/test_forms_flow_full_loop.py`.
>
> **Cenários:**
> 1. POST `/api/scan` (com mock do worker que apenas marca `success` sem abrir browser) → 200 → `forms_submissions` tem 1 linha `success` → `users.forms=True` → `checkinghistory.forms=True` → SSE do admin emitiu evento → SSE do Check Web emitiu evento.
> 2. POST `/api/web/check` com worker mockado para falhar → idem com `False`.
> 3. POST do mesmo `request_id` 2× → segunda chamada é idempotente.
> 4. Sequência: check-in (success) → check-out (success) → segundo check-in (success). `users.forms` reflete sempre o último.

### Prompt 8.5 — Load test do worker

> **Arquivo:** `tests/load/test_forms_worker_throughput.py`.
>
> **Cenário:** enfileirar 100 submissões em rajada; medir tempo até backlog = 0 com worker mockado de 200ms/item. Validar throughput ≥ 4 itens/s e nenhuma duplicação.

### Prompt 8.6 — Healthcheck regression test

> **Arquivo:** `tests/services/test_forms_worker_healthcheck.py`.
>
> **Cenários:**
> 1. Health file ausente + `FORMS_QUEUE_ENABLED=false` → exit 1, reason "forms worker disabled".
> 2. Health file ausente + `FORMS_QUEUE_ENABLED=true` (estado pré-fix da prod) → exit 1, "forms worker not running".
> 3. Health file presente com `last_heartbeat_at` recente → exit 0.
> 4. Health file presente mas `last_heartbeat_at` velho (>20s) → exit 1, "stale".
> 5. Health file presente com `consecutive_error_count >= 3` → exit 1.

### Prompt 8.7 — Front-end (Check Web)

> **Arquivo:** `tests/static/test_check_web_forms_label.py` (criar — usar Playwright Python).
>
> **Cenários:**
> 1. Estado `forms=true` → label "Forms: **enviado!**", cor azul-marinho.
> 2. `forms=false` → "Forms: **erro!**", vermelho.
> 3. `forms=null` → elemento oculto.
> 4. Trocar i18n → texto atualiza em pt/en/zh/ms/id/tl (6 asserts).
> 5. SSE entrega novo `forms` → label atualiza sem reload.

### Prompt 8.8 — Painel admin (coluna "Forms")

> **Arquivo:** `tests/static/test_admin_presence_forms_column.py`.
>
> **Cenários:**
> 1. Tabela "Usuários em Check-In" tem coluna "Forms" entre "Local" e a coluna anterior (snapshot DOM).
> 2. Linha com `forms=true` mostra "Enviado" azul-marinho negrito.
> 3. Linha com `forms=false` mostra "Erro" vermelho negrito.
> 4. Linha com `forms=null` mostra "--".
> 5. Ordenação por "Forms" funciona.
> 6. Filtro por "Forms" (se implementado) funciona.

### Prompt 8.9 — Migração + downgrade

> **Arquivo:** `tests/migrations/test_0062_forms_flag.py`.
>
> **Cenários:**
> 1. Upgrade adiciona coluna `forms` em ambas as tabelas.
> 2. Downgrade remove a coluna.
> 3. Upgrade + insert + downgrade + upgrade preserva dados (forçar `forms=NULL` no segundo upgrade).
> 4. Dados legados (linhas antes da migração) ficam com `forms IS NULL`.

### Prompt 8.10 — XPath validation contra o form vivo

> **Arquivo:** `scripts/forms_validate_xpaths.py` (criar) + `tests/smoke/test_xpath_live_validation.py` (gated por env).
>
> **Cenário:** para cada arquivo em `assets/xpath/`, Playwright abre o form e verifica que pelo menos um candidato dá `count() == 1`. Falhar (com nome do arquivo) se zero candidatos casarem.
>
> **Cadência sugerida:** rodar manualmente uma vez por semana e antes de cada deploy do worker.

---

## Fase 9 — Rollout & validação em produção

### Prompt 9.1 — Pré-deploy checklist

> **Tarefa:** Garantir que estes itens estão verdes antes do merge para `main`:
> - [ ] Backup do banco (`pg_dump` da droplet) salvo em S3/Spaces.
> - [ ] Toda a Fase 8 roda com `pytest` localmente verde.
> - [ ] `pytest tests/smoke/test_forms_live_submission.py` rodado manualmente com `RUN_LIVE_FORMS_SMOKE=1` → sucesso.
> - [ ] `scripts/forms_validate_xpaths.py` reporta 11 OK.
> - [ ] Migração `0062` rodada em staging (se houver) ou em snapshot do banco prod.
> - [ ] `docker compose -f docker-compose.api.yml config` sem warning.

### Prompt 9.2 — Deploy & validação pós-deploy

> **Tarefa:** Pull request mergeado dispara o workflow `deploy-oceandrive-api-only.yml`. Após o deploy, em ≤ 5 min:
> 1. `docker compose -f docker-compose.api.yml ps` mostra `forms-worker` UP.
> 2. `docker compose -f docker-compose.api.yml exec forms-worker python -m sistema.app.forms_worker_healthcheck` → exit 0.
> 3. `curl https://<host>/api/health | jq .forms_worker` → `status=ok`.
> 4. `psql -c "select status, count(*) from forms_submissions group by status;"` — observar `pending` cair, `success` subir.
> 5. Logar como user de teste no Check Web → fazer um check-in → ver "Forms: **enviado!**" em ≤ 60s.
> 6. Logar como admin → ver coluna "Forms" populada.
> 7. Verificar o dashboard gerencial do Microsoft Forms — o teste apareceu lá?
>
> **Se falhar:** rollback via `docker compose -f docker-compose.api.yml stop forms-worker` (a fila volta a apenas acumular, sem perder dados), abrir issue com os logs.

### Prompt 9.3 — Limpeza do backlog histórico

> **Tarefa:** Decidir o que fazer com as N submissões `pending` antigas (saída do Prompt 0.1).
>
> **Opções, perguntar ao usuário antes de executar:**
> - **(A) Replay completo:** deixar o worker processar tudo. Risco: floodar o MS Forms com eventos antigos que vão para o dashboard como se fossem novos.
> - **(B) Replay seletivo:** marcar como `status='skipped'` tudo anterior a uma data (ex.: data do incidente). Documentar a decisão e o critério.
> - **(C) Replay com flag de retroatividade:** atualizar `ontime=False` em todas as pendentes antes do worker subir, para que o form sinalize "retroativo".
>
> Sem ação automática — esperar decisão.

---

## Apêndice A — Mapa de arquivos por área

| Área | Arquivos críticos |
|---|---|
| Fila e worker | [sistema/app/services/forms_queue.py](../sistema/app/services/forms_queue.py), [sistema/app/services/forms_worker.py](../sistema/app/services/forms_worker.py), [sistema/app/services/forms_submit.py](../sistema/app/services/forms_submit.py), [sistema/app/forms_worker_main.py](../sistema/app/forms_worker_main.py), [sistema/app/forms_worker_healthcheck.py](../sistema/app/forms_worker_healthcheck.py) |
| Endpoints que enfileiram | [sistema/app/routers/device.py](../sistema/app/routers/device.py), [sistema/app/routers/web_check.py](../sistema/app/routers/web_check.py), [sistema/app/routers/mobile.py](../sistema/app/routers/mobile.py) |
| Modelos | [sistema/app/models.py](../sistema/app/models.py) (`User`, `CheckingHistory`, `FormsSubmission`, `CheckEvent`) |
| XPaths | [assets/xpath/](../assets/xpath/) |
| Deploy | [docker-compose.api.yml](../docker-compose.api.yml), [docker-compose.yml](../docker-compose.yml), [Dockerfile](../Dockerfile), [deploy/docker/Dockerfile.api](../deploy/docker/Dockerfile.api), [.github/workflows/deploy-oceandrive-api-only.yml](../.github/workflows/deploy-oceandrive-api-only.yml) |
| Admin UI | [sistema/app/static/admin/index.html](../sistema/app/static/admin/index.html), [sistema/app/static/admin/app.js](../sistema/app/static/admin/app.js) |
| Check Web UI | [sistema/app/static/check/index.html](../sistema/app/static/check/index.html), [sistema/app/static/check/app.js](../sistema/app/static/check/app.js), [sistema/app/static/check/web-client-state.js](../sistema/app/static/check/web-client-state.js), [sistema/app/static/check/i18n-dictionaries.js](../sistema/app/static/check/i18n-dictionaries.js) |

## Apêndice B — Convenções do projeto a observar (extraídas de [CLAUDE.md](../CLAUDE.md))

- `CheckEvent.action` é `String(16)` — manter nomes de novas actions ≤ 16 chars (`forms_warn`, `forms_alert` cabem).
- Mutações persistidas devem chamar `notify_admin_data_changed()` e/ou `notify_web_check_data_changed()` para refletir via SSE.
- Schemas Pydantic v2 separam request/response.
- Modelos SQLAlchemy 2.x usam `Mapped[T]` + `mapped_column`.
- JSON serializado em `Text` (não `Column(JSON)`).
- Migrações vão em `alembic/versions/NNNN_descricao.py`.

## Apêndice C — Ordem de execução sugerida

```
0.1 → 0.2          (snapshot + inspeção URL — sem código)
1.1 → 1.2          (worker em prod)
1.3                (defesa em profundidade)
9.1 (parcial: validar)  → 9.2  (deploy "minimum viable" só com worker restabelecido)
2.1                (migração)
3.1 → 3.2 → 3.3    (backend wiring)
6.1 → 6.2          (XPaths robustos)
6.3                (se necessário)
6.4                (retry)
4.1 → 4.2          (Check Web)
5.1 → 5.2          (Admin)
7.1 → 7.2          (guardrails)
8.x ao longo de cada fase
9.1 → 9.2 → 9.3    (deploy final)
```

> **Estratégia de menor risco:** dividir em dois deploys.
> **Deploy A** = Fases 0, 1, 9.1/9.2 (parcial). Restaura processamento da fila imediatamente.
> **Deploy B** = Fases 2, 3, 4, 5, 6, 7, 9.1/9.2/9.3. Entrega features de UX + robustez.
