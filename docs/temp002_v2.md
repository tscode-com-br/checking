# Plano de remediação do Forms — v2 (revisado pós-Fase 0)

> Este documento substitui o plano original em [temp002.md](temp002.md). Os achados da Fase 0 ([snapshot](temp002_phase0_snapshot.md) + [inspeção](temp002_phase0_forms_inspection.md)) mudaram significativamente o entendimento do problema. Esta versão é mais curta, menos arriscada, e prioritiza restaurar produção antes de qualquer melhoria.

## 1. Sumário do que mudou após a Fase 0

| Item | Plano original supunha | Fase 0 provou que |
|---|---|---|
| Worker code | Pode estar com bugs latentes | **Está correto.** [`_submit_once`](../sistema/app/services/forms_worker.py#L137) já trata branching condicional (check-in → 5 perguntas com projeto; check-out → 4 perguntas sem projeto). |
| XPaths | Podem ter quebrado por redesign do MS Forms | **Todos os 11 ainda casam** quando o fluxo correto é seguido. Re-inspeção interativa confirmou. |
| Resolução `chave → projeto` | Pode estar incorreta para usuários multi-projeto | **Já está correta:** Check Web usa escolha explícita do usuário (`_require_known_user_membership_project`); device usa `user.projeto` (active project). Cada `forms_submissions.projeto` em prod já tem o valor certo. |
| Login Microsoft | Possivelmente exigido | **Não.** Forms aceita anônimo (`is_login_wall: false`). |
| Único bloqueador real | Múltiplos (worker, XPaths, branching, projeto) | **Um só:** o container `forms-worker` não existe no `docker-compose.api.yml` de produção. |

**Consequência:** o caminho crítico para restaurar produção é **muito menor** do que o plano original sugeria. A maior parte do trabalho original continua válida, mas deixa de ser bloqueante — vira melhoria progressiva.

## 2. Estado atual da produção (em 2026-05-19 12:59 UTC)

- 1287 submissions `pending` + 2 `processing` travados (ids 934 e 1131, de 04-05/05/2026).
- Último `success`: 2026-05-06 00:36 UTC. **13 dias e ~12 h** sem processamento.
- Tráfego: ~100 submissões/dia. Backlog cresce.
- Dashboard gerencial do Microsoft Forms está vazio desde 2026-05-06.
- API saudável (`/api/health` reporta `forms_worker.status=disabled`). Usuários conseguem fazer check-in/check-out normalmente — a quebra é invisível para eles.
- Comorbidade: `sqlalchemy.exc.TimeoutError: QueuePool limit of size 6 overflow 2 reached` aparecendo nos logs do `app`. Não causa a falha do worker, mas pode piorar quando o worker subir. **Rastreado separadamente (Fase 4 deste plano).**

## 3. Estratégia em 2 deploys

### Deploy A — restaurar produção (escopo mínimo)

**Objetivo:** worker volta a processar a fila. Dashboard gerencial volta a receber dados. Nada mais.

**Escopo:**

1. Adicionar serviço `forms-worker` no [docker-compose.api.yml](../docker-compose.api.yml).
2. Decidir destino dos 1287 pendings + 2 stuck (replay vs. expurgo).
3. Defesa: API não deve enfileirar silenciosamente se o worker estiver morto.
4. Workflow de deploy passa a fazer pull/up/healthcheck do worker.

**Não muda:** código do worker, XPaths, schema do banco, UI do admin/check.

**Tempo estimado:** 1 dia de trabalho + janela de validação.

### Deploy B — melhorias de observabilidade

**Objetivo:** mostrar para usuário e admin se o Forms foi preenchido com sucesso.

**Escopo:**

5. Schema: coluna `forms` (BOOLEAN nullable) em `users` e `checkinghistory`.
6. Worker grava o resultado em `users.forms` e `checkinghistory.forms`.
7. API expõe `forms` em respostas e SSE.
8. Check Web mostra "Forms: enviado!" / "Forms: erro!" nos containers de histórico.
9. Admin mostra coluna "Forms" antes de "Local" nas tabelas de presença.
10. (Opcional) Tile de saúde da fila no dashboard admin.

**Não muda:** worker logic, XPaths, deploy infra.

**Tempo estimado:** 2-3 dias.

### Deferred — robustez defensiva (sem urgência)

11. Refatorar XPaths para semânticos (`data-automation-id`) com fallback posicional — Fase 6 do plano original. Deixa de ser bloqueante; vira defesa contra futuros redesigns do MS Forms.
12. Retry em `FormsStepTimeoutError` com backoff exponencial.
13. Alarmes de backlog (Fase 7 do plano original).
14. Testes de carga / smoke gated.

Esses itens entram numa Deploy C ou se diluem em commits subsequentes. Não devem competir por bandwidth com os Deploys A/B.

---

## 4. Deploy A — prompts detalhados

> Antes de qualquer mudança, rodar `pytest` localmente para baseline verde. Após cada prompt: rodar testes novamente, devolver relatório curto com SHA do commit e arquivos alterados.

### Prompt A.1 — Provisionar `forms-worker` em `docker-compose.api.yml`

**Tarefa:** adicionar o serviço `forms-worker` no `docker-compose.api.yml` espelhando o que [docker-compose.yml:97-129](../docker-compose.yml) já faz.

**Decisão de imagem:** reusar `deploy/docker/Dockerfile.api` (que já instala Playwright + Chromium via `playwright install --with-deps --only-shell chromium`) e sobrescrever o `command` no compose para `python -m sistema.app.forms_worker_main`. Justificativa: pipeline de build atual já produz `ghcr.io/tscode-com-br/checkcheck-api:<sha>` (ou `checkcheck-app`, ver §A.1.5 abaixo); criar uma segunda imagem dobra o tempo do CI sem ganho concreto. Se mais tarde houver necessidade de divergir deps, podemos extrair para `Dockerfile.forms-worker` num PR separado.

**Bloco a adicionar (depois do serviço `api`/`app` em `docker-compose.api.yml`):**

```yaml
  forms-worker:
    image: ${CHECKCHECK_API_IMAGE:-checkcheck-api:local}
    command: ["python", "-m", "sistema.app.forms_worker_main"]
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+psycopg2://postgres:postgres@db:5432/checking
      FORMS_URL: ${FORMS_URL}
      FORMS_TIMEOUT_SECONDS: ${FORMS_TIMEOUT_SECONDS:-30}
      FORMS_MAX_RETRIES: ${FORMS_MAX_RETRIES:-3}
      FORMS_QUEUE_ENABLED: "true"
      TZ_NAME: ${TZ_NAME:-Asia/Singapore}
      DATABASE_POOL_SIZE: "2"
      DATABASE_MAX_OVERFLOW: "1"
      FORMS_WORKER_HEALTH_PATH: /var/lib/checking/event_archives/forms_worker_health.json
    volumes:
      - event_archives:/var/lib/checking/event_archives
    healthcheck:
      test: ["CMD", "python", "-m", "sistema.app.forms_worker_healthcheck"]
      interval: 15s
      timeout: 10s
      retries: 3
      start_period: 30s
    restart: unless-stopped
```

**Atenção:**

- Confirmar que o `event_archives` volume já está declarado no topo do `docker-compose.api.yml`. Se não, adicionar.
- `FORMS_QUEUE_ENABLED=true` no worker é mandatório para o `forms_worker_main` iniciar o supervisor.
- **A flag continua `false` no container `api`** (não muda nada lá) — apenas para garantir que o `app` não tente ele próprio rodar um supervisor in-process; deixar isso só com o worker dedicado.
- `DATABASE_POOL_SIZE: "2"` para o worker é proposital — o worker só processa 1 item por vez. Limitar o pool evita contender com o `app` (que tem o problema de QueuePool documentado em [phase0_snapshot.md §7](temp002_phase0_snapshot.md)).

**Drift observado em prod (confirmar antes de PR):** o `docker compose ps` da Fase 0 mostrou:

- nome de serviço `app` (não `api`)
- imagem `ghcr.io/tscode-com-br/checkcheck-app:<sha>` (não `checkcheck-api`)
- porta `8000:8000` (não `18080`)

Mas o repo tem [docker-compose.api.yml](../docker-compose.api.yml) com nomes potencialmente diferentes. **Primeiro passo do prompt:** rodar `ssh root@157.230.35.21 'cat /root/checkcheck/docker-compose.api.yml'` e comparar com o que está no repo. Se o host estiver com uma versão "patched" do compose, há um item de auditoria adicional. Sem confirmar isso, o PR vai aplicar um compose que não bate com o que está rodando.

**Validação local antes de abrir PR:**

```powershell
docker compose -f docker-compose.api.yml config
docker compose -f docker-compose.api.yml up -d db migrate api forms-worker
docker compose -f docker-compose.api.yml exec forms-worker python -m sistema.app.forms_worker_healthcheck
curl http://127.0.0.1:8000/api/health | python -m json.tool
# esperado: components.forms_worker.status="ok"
```

**Commit:** `feat(deploy): provision forms-worker in api-only compose stack`. Descrever no body: que a regressão veio do `deploy-oceandrive-api-only.yml` ter sido usado em vez do `deploy-oceandrive.yml` em 2026-05-06; o worker desapareceu junto.

### Prompt A.2 — (Fundido em A.3 após a decisão D)

Os 2 itens travados em `processing` (ids 934 e 1131) agora são tratados junto com o expurgo do backlog em A.3 — o `UPDATE` cobre `status IN ('pending', 'processing')`. Não há ação separada.

### Prompt A.3 — Expurgo do backlog (DECISÃO TOMADA: Opção D)

**Decisão registrada em 2026-05-19:** descartar todo o backlog. O dashboard gerencial perde os 13 dias do gap. Aceita-se essa perda e o pipeline normaliza a partir do deploy.

**Tarefa:** **imediatamente antes** de fazer merge do PR do Deploy A (e portanto imediatamente antes do worker subir), rodar contra a base de produção:

```sql
-- Confirmar o estado atual antes de mexer
SELECT status, COUNT(*) FROM forms_submissions GROUP BY status ORDER BY 1;
-- Esperado (snapshot de 2026-05-19 12:59 UTC):
--   failed:     1
--   pending:    1287   <- vai virar skipped
--   processing: 2      <- vai virar skipped (inclui itens 934 e 1131, antes Prompt A.2)
--   success:    1177

-- Expurgo do backlog
UPDATE forms_submissions
SET status = 'skipped',
    last_error = COALESCE(last_error, '') || ' [discarded 2026-05-19 after 13-day worker outage]'
WHERE status IN ('pending', 'processing');

-- Confirmar
SELECT status, COUNT(*) FROM forms_submissions GROUP BY status ORDER BY 1;
-- Esperado:
--   failed:   1
--   skipped:  1289
--   success:  1177
```

**Atenção sobre o valor `'skipped'`:**

- O modelo [`FormsSubmission`](../sistema/app/models.py) usa `status: Mapped[str]` (não Enum). Tecnicamente aceita qualquer string.
- Mas pode haver `CHECK CONSTRAINT` no schema postgres limitando valores. **Primeira ação do prompt:** rodar `\d forms_submissions` no psql e inspecionar. Se houver constraint, ou trocamos para `'failed'` (perde a semântica "nunca tentamos") ou rodamos um `ALTER TABLE ... DROP CONSTRAINT ...` antes.
- O método [`_reserve_next_submission_id`](../sistema/app/services/forms_queue.py) filtra `WHERE status='pending'`. Qualquer outro valor é invisível ao worker. Então `'skipped'`, `'failed'` ou qualquer outro funciona para o objetivo de "fora da fila".

**Substitui o Prompt A.2 (reset dos 2 stuck):** o UPDATE acima já trata os 2 `processing` junto, no mesmo statement. Não há mais 2 ações separadas — vira 1.

**Ordem de execução (mandatória):**

1. PR do A.1 + A.4 + A.5 aprovado e pronto para merge.
2. SSH na droplet, abrir psql, rodar o `SELECT` de verificação atual.
3. Rodar o `UPDATE` de expurgo.
4. Conferir contagens (`failed: 1, skipped: 1289, success: 1177`).
5. **Só agora:** merge no main → workflow dispara → forms-worker sobe → vê fila vazia (de `pending`) → fica idle.
6. Novos eventos (check-ins/check-outs de usuários reais) começam a chegar → worker processa cada um normalmente.

**Justificativa do ordering:** se rodarmos o UPDATE depois do worker subir, há uma janela em que o worker tenta processar parte do backlog antes que o UPDATE chegue. Se rodarmos muito antes, novos enqueues de usuários reais podem ser atingidos pelo UPDATE — eles entram como `pending` e seriam corretamente preservados se o UPDATE for transacional (filtra `WHERE status IN ('pending','processing')` no momento exato do UPDATE).

**Risco residual:** entre passo 2 e passo 5, novos check-ins podem entrar como `pending`. Esses **não** serão atingidos pelo UPDATE (porque rodamos o UPDATE em um ponto no tempo, não como condição contínua). Eles ficam corretamente em `pending` e o worker novo vai processá-los. **Isso é o comportamento desejado.**

**Recomendação operacional:** rodar o passo 2-4 numa janela de baixo tráfego (≥ 10s sem novos pendings na cauda), só para evitar confusão na conferência de contagens. Não é estritamente necessário; é cosmético.

### Prompt A.4 — Atualizar workflow GitHub Actions

**Tarefa:** estender [.github/workflows/deploy-oceandrive-api-only.yml](../.github/workflows/deploy-oceandrive-api-only.yml) para pull/up/health do `forms-worker`.

**Mudanças no step "Pull and restart API services" (linhas ~144-173):**

```bash
# antes do step de "up api", adicionar:
CHECKCHECK_API_IMAGE="$API_IMAGE" docker compose -f docker-compose.api.yml pull forms-worker
CHECKCHECK_API_IMAGE="$API_IMAGE" docker compose -f docker-compose.api.yml up -d --no-build --force-recreate forms-worker
```

**Mudança no step "Validate API health":**

Estender [deploy/smoke/validate_target.sh](../deploy/smoke/validate_target.sh) ou adicionar um step novo:

```bash
docker compose -f docker-compose.api.yml exec -T forms-worker \
  python -m sistema.app.forms_worker_healthcheck
# exit 0 obrigatório; falhar o deploy se exit != 0.

# /api/health passa a ter forms_worker.status="ok" — assert isso.
curl -fsS http://127.0.0.1:8000/api/health \
  | python3 -c "import sys, json; d = json.load(sys.stdin); \
      assert d['components']['forms_worker']['status'] == 'ok', d['components']['forms_worker']"
```

**Atenção:** o plano original (Prompt 1.2) previa que o health do worker passaria de `unhealthy → ok`. Realidade da Fase 0: passa de `disabled → ok`. Ajustar o assert.

**Testes:**

- `act -W .github/workflows/deploy-oceandrive-api-only.yml` localmente (se disponível), ou disparar em branch de homologação.
- Validar que api permanece up enquanto forms-worker sobe.

### Prompt A.5 — Defesa em profundidade: enqueue com worker down

**Tarefa:** instrumentar o caminho de enqueue para deixar rastro quando o worker está fora — sem bloquear o enqueue (o histórico precisa ser preservado).

**Arquivos:**

- [sistema/app/services/forms_queue.py](../sistema/app/services/forms_queue.py) — função `enqueue_forms_submission` (linhas 303-…).
- [sistema/app/services/forms_submit.py](../sistema/app/services/forms_submit.py)
- [sistema/app/schemas.py](../sistema/app/schemas.py) — `MobileSubmitResponse` e equivalentes.

**Lógica:**

1. Depois do INSERT em `forms_submissions`, ler `get_forms_worker_observed_snapshot()`.
2. Se `running=false` OR (`stale=true` por mais de `forms_worker_health_stale_seconds`):
   - Gravar `CheckEvent` com `source="system"`, `action="forms_warn"` (16 chars), `status="warning"`, `message="Forms enqueued while worker is down"`, `details=f"backlog_count={N}"`.
   - **Debounce:** não gravar essa CheckEvent mais que 1× a cada 5 min. Estado em memória do processo (não precisa persistir entre restarts da api).
3. Adicionar campo `worker_healthy: bool` (default `True`) em `MobileSubmitResponse`. Quando worker está down, retornar `False`.

**Cuidado de performance:** o call de `get_forms_worker_observed_snapshot()` envolve leitura de um arquivo. Medir com `time.perf_counter`; se passar de 5 ms no path crítico, mover para background thread.

**Testes (unit):**

- Snapshot `running=false` → CheckEvent gravado.
- Snapshot `running=true` → nenhum CheckEvent.
- 5 enqueues em sequência com `running=false` → apenas 1 CheckEvent (debounce).
- `MobileSubmitResponse.worker_healthy` reflete o snapshot.

**Não fazer:** bloquear o enqueue. Isso quebraria o histórico do Check Web e dispararia 5xx no app caso o worker oscile.

### Prompt A.6 — Validação pós-deploy (manual, mas obrigatória)

Após merge → deploy automático, em ≤ 5 min:

```powershell
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 "cd /root/checkcheck && docker compose -f docker-compose.api.yml ps"
# esperado: 3 containers UP — db, app/api, forms-worker

ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 "cd /root/checkcheck && docker compose -f docker-compose.api.yml exec -T forms-worker python -m sistema.app.forms_worker_healthcheck"
# exit 0; running=true

ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 "curl -fsS http://127.0.0.1:8000/api/health | python3 -m json.tool"
# components.forms_worker.status="ok"

# acompanhar o consumo:
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 "cd /root/checkcheck && docker compose -f docker-compose.api.yml exec -T db psql -U postgres -d checking -c \"select status, count(*) from forms_submissions group by status;\""
# repetir a cada 10 min; pending deve descer, success deve subir.
```

**Validação funcional:** combinar uma chave de teste (ex.: "TEST") com o dono do Forms para identificar uma resposta de teste real. Fazer 1 check-in via `/api/web/check` no Check Web e confirmar que aparece no dashboard gerencial em ≤ 60s.

**Rollback (se necessário):**

```powershell
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 "cd /root/checkcheck && docker compose -f docker-compose.api.yml stop forms-worker"
```

A fila volta a apenas acumular (estado de antes do deploy). Nada perdido. Em seguida abrir issue com os logs do worker e diagnosticar.

---

## 5. Deploy B — observabilidade na UI

> Só iniciar **depois** que Deploy A esteja estável em prod por ≥ 24 h.

### Prompt B.1 — Migração Alembic do campo `forms`

(Idêntico ao Prompt 2.1 do plano original.) Adicionar `forms BOOLEAN NULLABLE` em `users` e `checkinghistory`. Migração `0062_add_forms_flag_to_users_and_checkinghistory.py`. `down_revision = "0061_add_accident_tables"` — confirmar com `alembic heads`.

### Prompt B.2 — Worker grava `forms` em `users` e `checkinghistory`

(Combinação dos Prompts 3.1 + 3.2 do plano original.) Após `_process_submission` decidir `success`/`failed`:

1. Atualizar `users.forms` se o evento ainda é o vigente. Critério: comparar `submission.created_at` com `user.time` ± 5s + match em `user.checkin == (action=='checkin')`. Se houver mudança subsequente, **não sobrescrever**.

   **Alternativa mais segura:** adicionar coluna `forms_submission_id` em `users` (FK para `forms_submissions.id`) registrada no enqueue. Worker só atualiza `users.forms` se `user.forms_submission_id == submission.id`. Determinística, sem janela arbitrária. Vale ~1 migração extra, recomendado.

2. Atualizar `checkinghistory.forms` na linha cuja chave natural casa:
   `(chave, atividade, projeto, time, informe)`. Precisa de `submission.event_time` na fila (adicionar coluna na mesma migração B.1).

**Race conditions:** ambas as updates devem rodar dentro da mesma transação do `_process_submission`. Em SQLite (testes), usar `db.flush()` + `db.refresh()`. Em Postgres (prod), o ROW LOCK natural já basta.

**Testes (unit):**

- Sucesso → `user.forms=True`, `checkinghistory.forms=True` na linha certa.
- Falha → `False`.
- Usuário fez novo check-in entre enqueue e processo → `user.forms` reflete o evento mais recente, NÃO o antigo.
- Submissão sem linha correspondente em `checkinghistory` → log warning, não levantar.

### Prompt B.3 — Expor `forms` em respostas e SSE

(Idêntico ao Prompt 3.3 do plano original.) Adicionar `forms: bool | None` em:

- `MobileSyncStateResponse.last_checkin`, `.last_checkout`.
- Linhas de presença do admin.

Chamar `notify_admin_data_changed()` + `notify_web_check_data_changed()` após `_process_submission` commitar.

### Prompt B.4 — Check Web: rótulo "Forms: enviado!" / "Forms: erro!"

(Idêntico ao Prompt 4.1 do plano original.) HTML em [static/check/index.html](../sistema/app/static/check/index.html), i18n em todas as 6 línguas, CSS com cor azul-marinho `#001f5b` (ok) e vermelho `#c10000` (erro).

**Validação visual obrigatória:** subir `uvicorn` local, simular sucesso e falha, validar em 6 idiomas, anexar screenshots no PR.

### Prompt B.5 — Admin: coluna "Forms" antes de "Local"

(Idêntico ao Prompt 5.1 do plano original.) Tabela "Usuários em Check-In" e "Usuários em Check-Out". Renderizar "Enviado" / "Erro" / "--". Suporte a ordenação. SSE atualiza linha quando worker termina.

### Prompt B.6 — (Opcional) Tile de saúde da fila

(Idêntico ao Prompt 7.2 do plano original.) 4 números no dashboard admin: backlog, idade do mais antigo, taxa de sucesso 24h, status do worker. Endpoint `/api/admin/forms-queue/diagnostics` já existe.

---

## 6. Deferred — robustez (sem urgência)

Estes ficam para depois do Deploy B estar estável. Não bloqueiam nada. Documentados aqui apenas para não serem esquecidos.

### D.1 — Refatorar XPaths para semânticos

Fase 6 do plano original (Prompts 6.1, 6.2, 6.4). Trocar XPaths posicionais por seletores baseados em `data-automation-id` + `data-automation-value`, mantendo o XPath antigo como fallback. Beneficia futuros redesigns do MS Forms.

**Seletores propostos** (validados na re-inspeção interativa — todos retornam count=1):

| Arquivo atual | XPath atual | XPath semântico proposto |
|---|---|---|
| `digitar_chave.txt` | `//*[@id="question-list"]/div[1]/div[2]/div/span/input` | `(//input[@data-automation-id="textInput"])[1]` |
| `confirmar_chave.txt` | `//*[@id="question-list"]/div[2]/div[2]/div/span/input` | `(//input[@data-automation-id="textInput"])[2]` |
| `botao_normal.txt` | `//*[@id="question-list"]/div[3]/.../input` | `//span[@data-automation-value="Normal"]//input` |
| `botao_retroativo.txt` | idem | `//span[@data-automation-value="Retroativo"]//input` |
| `botao_checkin.txt` | idem | `//span[@data-automation-value="Check-In"]//input` |
| `botao_checkout.txt` | idem | `//span[@data-automation-value="Check-Out"]//input` |
| `botao_projeto_P80.txt` | `//*[@id="question-list"]/div[5]/.../input` | `//span[@data-automation-value="P80"]//input` |
| `botao_projeto_P82.txt` | idem | `//span[@data-automation-value="P82"]//input` |
| `botao_projeto_P83.txt` | idem | `//span[@data-automation-value="P83"]//input` |
| `botao_enviar.txt` | `//*[@id="form-main-content1"]/.../button` | `//button[@data-automation-id="submitButton"]` |
| `sucesso.txt` | `//*[@id="form-main-content1"]/.../span` | `//*[@role="heading" and (contains(., "Sua resposta foi enviada") or contains(., "Your response was submitted") or contains(., "obrigad"))]` |

Worker passa a ler arquivos como lista de candidatos (formato: 1 linha por candidato; primeira que casar vence). Implementação: alterar `load_xpath` para `load_xpath_candidates`; `_wait_for_step` itera nos candidatos.

### D.2 — Retry em `FormsStepTimeoutError`

Prompt 6.4 original. Hoje `submit_with_retries` só retenta `PlaywrightTimeoutError`. Estender para também retentar `FormsStepTimeoutError` (mas NÃO `FormsStepValidationError`). Backoff exponencial 1s/2s/4s.

### D.3 — Alarme de backlog + tile de saúde

Prompts 7.1 e 7.2 originais. Não urgente se Deploy B.6 (tile) for implementado.

### D.4 — Smoke test contra Forms real

Prompt 8.3 original. Teste gated por `RUN_LIVE_FORMS_SMOKE=1`. Combinar com dono do form para reservar uma chave de teste (ex.: "TEST") e filtrar respostas dela do dashboard real.

### D.5 — Investigar `QueuePool` exhaustion no `app`

Não é parte do plano original — descoberto na Fase 0. Erros `QueuePool limit of size 6 overflow 2 reached` aparecem nos logs do app em prod. Pode causar 5xx esporádicos. Soluções possíveis: aumentar `DATABASE_POOL_SIZE` no `app` (compose env var), revisar transações longas, ou identificar caminho que segura conexões mais do que deveria.

**Não bloqueia o Deploy A**, mas pode interagir mal quando o worker subir e começar a abrir conexões no mesmo db.

---

## 7. Plano de testes condensado

> Cada Prompt acima precisa rodar os testes aplicáveis antes do PR. Lista canônica abaixo.

### Antes do Deploy A

- `pytest tests/services/test_forms_queue.py` — baseline verde (provavelmente já está).
- `pytest tests/services/test_forms_worker.py` — idem.
- `pytest tests/services/test_forms_worker_healthcheck.py` — idem. Se não existir, criar com os 5 cenários do Prompt 8.6 do plano original.
- Local: `docker compose -f docker-compose.api.yml up -d` com worker, verificar que processa fila local sem erros.

### Antes do Deploy B

- Adicionar testes da Fase 8.1 original: 24 cenários cobrindo `_process_submission`, race condition entre enqueue e novo check, `users.forms` update determinístico via `forms_submission_id` FK.
- Migração: `tests/migrations/test_0062_forms_flag.py` (upgrade + downgrade + round-trip).
- Front-end Check Web: `tests/static/test_check_web_forms_label.py` (Playwright Python).
- Front-end admin: `tests/static/test_admin_presence_forms_column.py`.
- Integration: `tests/integration/test_forms_flow_full_loop.py` — API → queue → worker mockado → DB → SSE.

### Smoke gated (Deferred)

- `tests/smoke/test_forms_live_submission.py` (RUN_LIVE_FORMS_SMOKE=1). Roda manualmente após cada mudança em XPaths ou `forms_url`.
- `scripts/forms_validate_xpaths.py` — script que abre o form e valida que cada XPath casa. Cadência: semanal + antes de cada deploy do worker.

---

## 8. Apêndice — checklist pré-merge para Deploy A

- [ ] `pytest` local 100% verde.
- [ ] `docker compose -f docker-compose.api.yml config` sem warning.
- [ ] `docker compose -f docker-compose.api.yml up -d forms-worker` local: worker processa 1 evento de teste com sucesso.
- [ ] Workflow de deploy testado em branch de homologação (não direto em main).
- [ ] Backup do `pg_dump` da droplet salvo em DO Spaces.
- [ ] **Decisão A.3 = Opção D (descartar todo o backlog).** Locked em 2026-05-19.
- [ ] `UPDATE forms_submissions SET status='skipped' ...` executado em prod **imediatamente antes** do merge do PR (mesmo dia, mesma janela operacional).
- [ ] Conferência das contagens pós-UPDATE: `failed: 1, skipped: 1289, success: 1177`.
- [ ] Chave de teste combinada com o dono do form para validação pós-deploy (1 check-in real para conferir que aparece no dashboard).

## 9. Apêndice — o que removemos do plano original e por quê

| Item original | Status no v2 | Motivo |
|---|---|---|
| Prompt 0.1 (snapshot prod) | **Executado** | [docs/temp002_phase0_snapshot.md](temp002_phase0_snapshot.md) |
| Prompt 0.2 (inspeção Forms) | **Executado e ampliado** | [docs/temp002_phase0_forms_inspection.md](temp002_phase0_forms_inspection.md) + screenshots em `temp002_phase0_screenshots/`. Re-inspeção interativa validou branching condicional. |
| Prompt 1.1 (provisionar worker) | **Mantido** como A.1, simplificado | Decisão de imagem resolvida (opção B do original) |
| Prompt 1.2 (workflow) | **Mantido** como A.4 | Ajuste no assert de health (disabled→ok, não unhealthy→ok) |
| Prompt 1.3 (defesa) | **Mantido** como A.5, com debounce | Plus o campo `worker_healthy` na response |
| Fase 2 (schema) | **Mantida** como B.1 + adição de `forms_submission_id` FK | Tornar a correlação determinística |
| Fase 3 (backend wiring) | **Mantida** como B.2/B.3 | |
| Fase 4 (Check Web UI) | **Mantida** como B.4 | |
| Fase 5 (Admin UI) | **Mantida** como B.5 | |
| Fase 6 (XPaths robustos) | **Movida para Deferred D.1** | Phase 0 provou que XPaths atuais ainda funcionam. Refatoração vira melhoria progressiva, não bloqueador. |
| Prompt 6.3 (SSO Microsoft) | **REMOVIDO** | Phase 0 provou que o form aceita anônimo. |
| Prompt 6.4 (retry timeout) | **Movido para Deferred D.2** | |
| Fase 7 (alarmes/tile) | **Movida para B.6 (opcional) + D.3** | |
| Fase 8 (testes) | **Mantida**, condensada na §7 | |
| Fase 9 (rollout) | **Mantida** como Prompts A.6 e checklist §8 | |
| QueuePool exhaustion | **NOVO**, Deferred D.5 | Descoberto na Fase 0 |
| Reset dos 2 stuck `processing` | **NOVO**, Prompt A.2 | Necessário antes de subir worker |

## 10. Próximo passo imediato

Decisão A.3 **tomada**: Opção D — descartar todo o backlog.

Caminho desbloqueado:

1. **Agora:** começar A.1 (provisionar `forms-worker` no `docker-compose.api.yml`), em uma **branch de feature** (não `main`). Sem efeito em prod até o merge.
2. **Em sequência:** A.4 (workflow Actions) e A.5 (defesa enqueue) no mesmo PR ou PRs separados.
3. **Quando o PR estiver aprovado:**
   a. SSH na droplet, abrir psql, conferir contagens atuais.
   b. Rodar o UPDATE do A.3 (expurgo).
   c. Conferir contagens pós-UPDATE.
   d. Merge → workflow → worker sobe → fila `pending` vazia → idle.
4. **A.6:** validação pós-deploy (~5-10 min).
5. **24h depois:** se estável, planejar Deploy B.

Esperando seu "pode começar A.1" para abrir uma branch de feature e tocar o arquivo do compose.
