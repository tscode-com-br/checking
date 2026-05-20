# Plano de remediação do Forms — v2 (revisado pós-Fase 0)

> **Postmortem do restabelecimento do `forms-worker` em produção.** O incidente original (worker ausente após Fase 2 do incidente 504, em 2026-05-06) e a remediação (Deploy A, em 2026-05-19) estão documentados aqui de ponta a ponta. Artefatos relacionados:
>
> - [Plano original (temp002)](2026-05-19-forms-worker-restore-original-plan.md) — proposta inicial antes da Fase 0; superada por este documento.
> - [Phase 0 — snapshot da produção](2026-05-19-forms-worker-restore-phase0-snapshot.md) — estado da fila em 2026-05-19 12:59 UTC, antes do Deploy A.
> - [Phase 0 — inspeção do MS Forms](2026-05-19-forms-worker-restore-phase0-forms-inspection.md) — confirmou que o form aceita anônimo e os 11 XPaths atuais ainda casam.
> - [Phase 0 — screenshots](2026-05-19-forms-worker-restore-phase0-screenshots/) — 3 capturas do form (vazio, pós-checkin, pós-checkout).

## 0. Status atual — Deploy A concluído em prod

| Item | Estado | Evidência (última leitura: 2026-05-19 16:01 UTC) |
|---|---|---|
| **Deploy A** | ✅ **CONCLUÍDO** | PR #1 mergeado como commit `880b893` em 2026-05-19 14:23 UTC; workflow `Deploy OceanDrive` concluiu success em 5m40s |
| Container `forms-worker` em prod | ✅ UP, healthy | Imagem `ghcr.io/.../checkcheck-forms-worker:880b8937…`, status `idle`, heartbeat 0s |
| `/api/health` `forms_worker.status` | ✅ `"ok"` (era `"disabled"`) | `{"status":"ok","detail":"forms worker healthy"}` |
| Backlog expurgado | ✅ 1289 itens → `skipped` | Pré-merge `UPDATE forms_submissions SET status='skipped' WHERE status IN ('pending','processing')` |
| Submissões processadas pós-deploy | ✅ 2 sucessos / 0 falhas | id 2468 (HR70 checkin P80) 14:46:53 UTC; id 2469 (HR70 checkout P80) 15:35:41 UTC |
| Flag `success_xpath_visible` | ✅ `true` em ambas | XPath `sucesso.txt` detectado; `success_text="Your response was submitted."`; latência Enviar→Sucesso 642–690 ms |
| Branching condicional check-in vs check-out | ✅ comprovado | Check-IN logou `botao_projeto_P80:clicked+verified`; check-OUT não logou `botao_projeto_*` |
| Fila atual (`forms_submissions`) | ✅ saudável | `failed=1, skipped=1289, success=1179` (1177 históricos + 2 novos) |
| Defesa A.5 (`forms_warn`) ainda inativa? | ✅ correto | `0` CheckEvents com `action='forms_warn'` (worker permaneceu saudável; defesa nunca precisou ser acionada) |
| Modificação local em `forms_worker.py` (sleep 0.02) | ⚠️ ainda uncommitted | Existia antes da Fase 0; deixada na working tree para decisão posterior |

**Conclusão:** o problema central que motivou este plano (worker ausente, fila crescendo) está resolvido. O ciclo end-to-end (API → fila → worker → MS Forms → dashboard) volta a funcionar, comprovado por 2 submissões reais. Plano restante: Deploy B (opcional, UX) e itens diferidos.

---

## 1. Sumário do que mudou após a Fase 0

| Item | Plano original supunha | Fase 0 provou que |
|---|---|---|
| Worker code | Pode estar com bugs latentes | **Está correto.** [`_submit_once`](../sistema/app/services/forms_worker.py#L137) já trata branching condicional (check-in → 5 perguntas com projeto; check-out → 4 perguntas sem projeto). |
| XPaths | Podem ter quebrado por redesign do MS Forms | **Todos os 11 ainda casam** quando o fluxo correto é seguido. Re-inspeção interativa confirmou. |
| Resolução `chave → projeto` | Pode estar incorreta para usuários multi-projeto | **Já está correta:** Check Web usa escolha explícita do usuário (`_require_known_user_membership_project`); device usa `user.projeto` (active project). Cada `forms_submissions.projeto` em prod já tem o valor certo. |
| Login Microsoft | Possivelmente exigido | **Não.** Forms aceita anônimo (`is_login_wall: false`). |
| Único bloqueador real | Múltiplos (worker, XPaths, branching, projeto) | **Um só:** o container `forms-worker` não existe no `docker-compose.api.yml` de produção. |

**Consequência:** o caminho crítico para restaurar produção é **muito menor** do que o plano original sugeria. A maior parte do trabalho original continua válida, mas deixa de ser bloqueante — vira melhoria progressiva.

## 2. Estado da produção ANTES do Deploy A (snapshot histórico — em 2026-05-19 12:59 UTC)

> Mantido como registro do estado de partida. Para o estado **atual**, ver §0 acima.

- 1287 submissions `pending` + 2 `processing` travados (ids 934 e 1131, de 04-05/05/2026).
- Último `success`: 2026-05-06 00:36 UTC. **13 dias e ~12 h** sem processamento.
- Tráfego: ~100 submissões/dia. Backlog cresce.
- Dashboard gerencial do Microsoft Forms está vazio desde 2026-05-06.
- API saudável (`/api/health` reporta `forms_worker.status=disabled`). Usuários conseguem fazer check-in/check-out normalmente — a quebra é invisível para eles.
- Comorbidade: `sqlalchemy.exc.TimeoutError: QueuePool limit of size 6 overflow 2 reached` aparecendo nos logs do `app`. Não causa a falha do worker, mas pode piorar quando o worker subir. **Continua aberto** após Deploy A — virou item Deferred D.5.

## 3. Estratégia em 2 deploys

### ✅ Deploy A — restaurar produção (CONCLUÍDO em 2026-05-19)

**Objetivo:** worker volta a processar a fila. Dashboard gerencial volta a receber dados. Nada mais.

**Escopo executado:**

1. ✅ `forms-worker` provisionado: `deploy/maintenance/run_app_rollout.sh` agora dá `docker compose up -d app forms-worker`; CI builda/empurra imagem `checkcheck-forms-worker`; `docker-compose.api.yml` ganhou paridade com `docker-compose.yml`.
2. ✅ Backlog expurgado: 1287 pending + 2 processing → `skipped` (Opção D do §4 abaixo).
3. ✅ Defesa A.5 instrumentada: `enqueue_forms_submission` emite `CheckEvent(action='forms_warn')` debounce 5 min/processo quando o worker está down; `MobileSubmitResponse` ganhou `worker_healthy: bool`.
4. ✅ Workflow `Deploy OceanDrive` ajustado: build/push do `forms-worker-runtime`, pull no host, health-poll do worker (até 90s).

**Não mudou** (como planejado): código do worker, XPaths, schema do banco, UI do admin/check.

**Tempo real gasto:** ~6h (fase 0 + implementação + testes + PR + merge + validação).

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

### ✅ Prompt A.1 — Provisionar `forms-worker` no compose de produção (DONE)

> **Achado importante durante a execução:** o `docker-compose.api.yml` **não era** o compose efetivo em prod. O workflow `deploy-oceandrive.yml` (não `deploy-oceandrive-api-only.yml`) usa o `docker-compose.yml` principal, que já tinha `forms-worker` declarado nas linhas 97-129. O bug real estava em [`deploy/maintenance/run_app_rollout.sh:108`](../deploy/maintenance/run_app_rollout.sh#L108): `docker compose up -d ... --remove-orphans app` só subia `app` e removia explicitamente qualquer worker.
>
> **O que foi feito de fato:**
> - `run_app_rollout.sh:108`: passou a fazer `up -d ... app forms-worker`; nova função de health-poll do worker (até 90 s, intervalo 6 s).
> - `.github/workflows/deploy-oceandrive.yml`: nova etapa de build/push da imagem `ghcr.io/tscode-com-br/checkcheck-forms-worker:<sha>` (target `forms-worker-runtime` do `Dockerfile` raiz que já instala Playwright + Chromium); pull no host; `export CHECKCHECK_FORMS_WORKER_IMAGE` para o `docker compose` resolver.
> - `.github/workflows/deploy-oceandrive-api-only.yml`: as mesmas mudanças por simetria (fallback consistency).
> - `docker-compose.api.yml`: serviço `forms-worker` adicionado (paridade com o `docker-compose.yml` principal).

### ✅ Prompt A.2 — Fundido em A.3 (DONE)

Os 2 itens travados em `processing` (ids 934 e 1131) foram tratados junto com o expurgo do backlog em A.3 — o `UPDATE` cobriu `status IN ('pending', 'processing')`. Total: `UPDATE 1289`.

### ✅ Prompt A.3 — Expurgo do backlog (DONE — Opção D executada)

> **Executado em 2026-05-19 14:22 UTC** (~1 min antes do merge do PR #1).
>
> - SELECT pré-expurgo: `failed=1, pending=1287, processing=2, success=1177` (total 2467).
> - `UPDATE 1289` (todos os pending + os 2 stuck).
> - SELECT pós-expurgo: `failed=1, skipped=1289, success=1177` (total 2467 — preservado).
> - Não houve `CHECK CONSTRAINT` na coluna `status` (auditado via `pg_get_constraintdef`), portanto `'skipped'` foi aceito sem ajuste de schema.
> - `last_error` recebeu sufixo ` [discarded 2026-05-19 after 13-day worker outage]` para rastreabilidade.
>
> **Como reverter caso necessário:** `UPDATE forms_submissions SET status='pending', last_error=NULL WHERE status='skipped' AND last_error LIKE '%discarded 2026-05-19%';` — o worker reassume da fila do ponto onde está.

### ✅ Prompt A.4 — Atualizar workflow GitHub Actions (DONE)

> **Executado:** ambos os workflows (`deploy-oceandrive.yml` e `deploy-oceandrive-api-only.yml`) ganharam:
> - Build/push da nova imagem `ghcr.io/tscode-com-br/checkcheck-forms-worker:<sha>` (target `forms-worker-runtime` do `Dockerfile` raiz).
> - Pull da imagem no host com `CHECKCHECK_FORMS_WORKER_IMAGE` exportado para o `docker compose`.
> - Health-poll do worker até 90 s (intervalo 6 s) na fase `validate-local` — falha o deploy se o worker não ficar healthy.
>
> Run real disparado pelo merge do PR #1 (run id `26103468810`): **success em 5m40s**, todos os passos verdes (incluindo o novo `Build and push forms-worker image`).

### ✅ Prompt A.5 — Defesa em profundidade: enqueue com worker down (DONE)

> **Implementado:**
> - `sistema/app/services/forms_queue.py`: novos helpers `is_forms_worker_healthy_now()`, `_maybe_emit_worker_down_warning()`, com estado de debounce em memória (`_worker_down_warn_lock`/`_worker_down_warn_state`) — janela de 300 s (`_WORKER_DOWN_WARN_DEBOUNCE_SECONDS`).
> - `enqueue_forms_submission` invoca o helper após o `db.flush()` bem-sucedido. CheckEvent emitido tem `source='system'`, `action='forms_warn'`, `status='warning'`, com `request_id`, `last_heartbeat_at` e estados `running`/`stale` no `details`.
> - `sistema/app/schemas.py`: `MobileSubmitResponse.worker_healthy: bool = True` (default mantém clientes existentes funcionando).
> - `sistema/app/services/forms_submit.py` e `sistema/app/routers/mobile.py`: setam `worker_healthy=is_forms_worker_healthy_now()` apenas nos response paths pós-enqueue de sucesso.
>
> **7 testes novos** em [`tests/services/test_forms_queue_worker_down_warning.py`](../tests/services/test_forms_queue_worker_down_warning.py), todos verdes:
> - `is_forms_worker_healthy_now` retorna True para snapshot saudável.
> - Retorna False quando `enabled=False`.
> - Retorna False quando `stale=True`.
> - Emite warning único quando worker down.
> - **Não** emite quando worker healthy.
> - Debounce: 5 enqueues seguidos com worker down → 1 só warning.
> - Após `_WORKER_DOWN_WARN_DEBOUNCE_SECONDS` + 1 → novo warning.
>
> Verificação em prod (2026-05-19 16:01 UTC): `0` CheckEvents com `action='forms_warn'` desde o deploy — esperado, porque o worker permaneceu saudável.

### ✅ Prompt A.6 — Validação pós-deploy (DONE)

> **Executado em 2026-05-19 14:28-15:35 UTC:**
>
> | Verificação | Resultado |
> |---|---|
> | `docker compose ps` na droplet | 3 containers UP: `checkcheck-db-1`, `checkcheck-app-1` (image `880b8937`), `checkcheck-forms-worker-1` (image `880b8937`) |
> | `python -m sistema.app.forms_worker_healthcheck` no container | exit 0, `{"status":"ok","worker":{"running":true,"stale":false,"status":"idle","heartbeat_age_seconds":3,"consecutive_error_count":0,"restart_count":0}}` |
> | `/api/health` `forms_worker` | `{"status":"ok","detail":"forms worker healthy"}` (era `"disabled"`) |
> | Fila `forms_submissions` | `failed=1, skipped=1289, success=1177` imediatamente pós-deploy |
> | **Submissão real (validação funcional):** HR70 check-in via Check Web | id 2468 (P80) processed_at 14:46:53 UTC → `success`, latência Enviar→Sucesso 642ms, `success_text="Your response was submitted."` |
> | **Submissão real:** HR70 check-out via Check Web | id 2469 (P80) processed_at 15:35:41 UTC → `success`, latência 690ms |
> | Branching condicional verificado em logs do CheckEvent | Check-IN logou `botao_projeto_P80:clicked+verified`; check-OUT **não logou** projeto — comportamento esperado |
>
> **Não houve necessidade de rollback.**
>
> **Rollback caso seja necessário no futuro:** `ssh ... docker compose stop forms-worker` — para o worker, fila volta a acumular, nada perdido. Reverter com `docker compose start forms-worker`.

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

## 8. Apêndice — checklist pré-merge para Deploy A (HISTÓRICO — todos os itens ✅ concluídos em 2026-05-19)

- [x] `pytest` local 100% verde — baseline 124 testes; final 151 (com 7 novos de A.5), nenhuma regressão.
- [x] Validação de YAML dos composes — via `python -c "import yaml; yaml.safe_load(...)"` (docker não disponível na workstation; CI fez o `docker compose config` implícito no build).
- [ ] ~~`docker compose -f docker-compose.api.yml up -d forms-worker` local~~ — pulado por ausência de Docker na workstation; substituído pela validação no CI + health-poll no rollout.
- [ ] ~~Workflow de deploy testado em branch de homologação~~ — pulado; o repo não possui branch de homologação separada. Mitigado pelo rollback fácil (`docker compose stop forms-worker`).
- [ ] ~~Backup do `pg_dump` da droplet salvo em DO Spaces~~ — pulado; o expurgo é seguro (não deleta linhas, só muda status) e reversível com UPDATE inverso.
- [x] **Decisão A.3 = Opção D (descartar todo o backlog).** Locked em 2026-05-19.
- [x] `UPDATE forms_submissions SET status='skipped' ...` executado em prod 14:22 UTC, ~1 min antes do merge do PR. `UPDATE 1289`.
- [x] Conferência das contagens pós-UPDATE: `failed=1, skipped=1289, success=1177`.
- [x] Chave de teste para validação pós-deploy: HR70 (admin). 2 check-ins/check-outs reais validados em 14:46 e 15:35 UTC.

## 9. Apêndice — o que removemos do plano original e por quê

| Item original | Status no v2 | Motivo |
|---|---|---|
| Prompt 0.1 (snapshot prod) | **Executado** | [phase0-snapshot.md](2026-05-19-forms-worker-restore-phase0-snapshot.md) |
| Prompt 0.2 (inspeção Forms) | **Executado e ampliado** | [phase0-forms-inspection.md](2026-05-19-forms-worker-restore-phase0-forms-inspection.md) + screenshots em [phase0-screenshots/](2026-05-19-forms-worker-restore-phase0-screenshots/). Re-inspeção interativa validou branching condicional. |
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

**Deploy A finalizado.** O caminho crítico (worker restaurado, fila funcionando, dashboard gerencial recebendo) está completo. Os itens abaixo são opcionais e podem entrar em qualquer ordem (ou nenhuma).

### 10.1 Recomendação de prioridade

Ordenados por relação risco/benefício, **na minha opinião**:

| # | Item | Por quê primeiro/depois | Recomendação |
|---|---|---|---|
| 1 | **Janela de observação 24-48h** | Só 2 submissões reais foram processadas pós-deploy. Quero ver pelo menos 1 turno operacional inteiro (uma manhã ou tarde) confirmando que o worker aguenta tráfego real (≈100 submissões/dia). Se aparecer alguma falha, fica visível agora que estamos atentos. | **Fazer primeiro.** Custo zero, só esperar e checar `select status, count(*) from forms_submissions group by status` periodicamente. |
| 2 | **Deferred D.5 — investigar `QueuePool` exhaustion no `app`** | Pré-existe ao Deploy A (não foi introduzido por ele). Continua aparecendo nos logs. Não derruba a aplicação, mas pode causar 5xx esporádicos em horários de pico. Tem potencial de piorar agora que o worker abre mais conexões no mesmo `db`. | **Segundo.** Subir `APP_DATABASE_POOL_SIZE` no `.env` da droplet de 6 para 10 ou 12 é um quick win sem código. Ou investigar transação long-running antes. |
| 3 | **Deploy B — observabilidade na UI** | Não tem urgência operacional. Hoje os usuários não sabem se o Forms foi preenchido (sempre foi assim — não há regressão). Admin tem que abrir o psql para auditar. Útil mas não bloqueador. | **Terceiro.** Quando houver bandwidth de desenvolvimento. Estimativa 2-3 dias. |
| 4 | **Deferred D.4 — smoke test live gated** | Boa proteção para futuras mudanças de XPath ou imagem do worker. Sem urgência se nada está mudando ali. | **Antes de qualquer mexida em XPaths ou worker.** |
| 5 | **Deferred D.1 — XPaths semânticos** | Defesa contra futuros redesigns do MS Forms (que acontecem 2-4 vezes/ano). Atual funciona em ~650 ms. Sem urgência. | **Quando der.** |
| 6 | **Deferred D.2 — retry em `FormsStepTimeoutError`** | Pequena melhoria de robustez. Hoje o worker já tem retry para `PlaywrightTimeoutError`. | **Quando der.** |
| 7 | **Deferred D.3 — alarmes de backlog** | Útil para detectar a próxima fila descontrolada. A defesa A.5 (warning na primeira enqueue com worker down) já cobre o caso "worker morre"; D.3 cobre "worker está lento e fila cresce". | **Quando der.** |

### 10.2 Itens não-resolvidos do plano original que merecem registro

- **`success_text` em inglês:** o Chromium headless da droplet captura `"Your response was submitted."` em vez de `"Sua resposta foi enviada."`. O XPath atual `sucesso.txt` é posicional, então não depende do idioma. Mas o XPath semântico proposto em D.1 deve cobrir os 3 idiomas (PT/EN/+obrigad genérico).
- **Modificação local em [`sistema/app/services/forms_worker.py`](../sistema/app/services/forms_worker.py)** (`sleep(0.02)` no `_wait_for_step_confirmation`): continua uncommitted na sua working tree. Otimização benigna de CPU. Pode ser comitada em qualquer PR futuro (ou descartada).
- **Drift entre o repo e o `.env` da droplet:** o `.env` em prod **não** tem `FORMS_QUEUE_ENABLED` definido. O container `app` recebe `false` (default do compose). O container `forms-worker` recebe `true` (default do compose). Está funcionando, mas se alguém editar o `.env` adicionando `FORMS_QUEUE_ENABLED=false`, o worker para de operar silenciosamente. Considerar documentar isso em `docs/descritivos/acesso_Digital_Ocean.md`.

### 10.3 Comandos de monitoramento manual (próximas 24-48h)

```powershell
# Snapshot rápido da fila (pode rodar a qualquer momento)
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 `
  "cd /root/checkcheck && docker compose exec -T db psql -U postgres -d checking -c \"select status, count(*) from forms_submissions group by status order by 1;\""

# Sanity check do worker
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 `
  "cd /root/checkcheck && docker compose exec -T forms-worker python -m sistema.app.forms_worker_healthcheck"

# Quaisquer falhas pós-deploy?
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 `
  "cd /root/checkcheck && docker compose exec -T db psql -U postgres -d checking -c \"select id, chave, action, last_error, processed_at from forms_submissions where status='failed' and processed_at > '2026-05-19 14:22:00+00' order by processed_at desc;\""

# Algum forms_warn foi emitido? (deveria ser 0 enquanto worker está saudável)
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 `
  "cd /root/checkcheck && docker compose exec -T db psql -U postgres -d checking -c \"select event_time, details from check_events where action='forms_warn' order by event_time desc limit 5;\""

# Públicamente: API ainda saudável?
Invoke-WebRequest https://tscode.com.br/api/health -UseBasicParsing | Select-Object -ExpandProperty Content
```

### 10.4 Quando voltar para este plano

- **Imediatamente:** se aparecer qualquer `failed` em `forms_submissions` nas próximas 48h, investigar antes de qualquer outra mudança. Ver `last_error` e logs do worker (`docker compose logs --tail 200 forms-worker`).
- **Em 1-2 semanas:** decidir se quer Deploy B (UX) ou priorizar Deferred D.5 (QueuePool).
- **Antes de qualquer mexida em XPaths ou na imagem do worker:** rodar D.4 (smoke test live) antes e depois.
