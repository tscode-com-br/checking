# temp005 — Inconsistência da coluna "Forms" (CY22 mostra "Não Realizado" apesar do Forms ter sido enviado)

> **Status:** diagnóstico concluído (2026-06-22). Causa-raiz identificada e confirmada com dados de
> produção (read-only). Este documento contém **prompts completos e autossuficientes** para um agente de
> IA aplicar a correção. **Nenhum código foi alterado ainda.**
>
> **Regra geral para todos os prompts:** alterar **apenas o que for necessário**. A correção é de
> **leitura/exibição** (read-side). **Não** há migração de banco, **não** há backfill de dados e **não**
> há mudança no caminho de escrita (a deduplicação do Forms está funcionando como projetado).

---

## 1. Sumário executivo (o que está acontecendo)

Na aba **Check-In** do admin (`/checking/admin`, SPA em `sistema/app/static/admin2`), a tabela
**"Usuários em Check-In"** tem uma coluna **"Forms"**. Para o usuário **Rafael Mota Moreira** (`chave=CY22`,
`user_id=46`, projeto único **P80**) essa coluna mostra **"Não Realizado"**, embora o Forms tenha sido
**enviado com sucesso** (evento `21068` na aba Eventos: *"Form submitted successfully"*, `display_status=sent`).

**A causa não é perda de dado.** O Forms FOI enviado e o banco registra isso corretamente. O defeito está
em **como a coluna escolhe qual `FormsSubmission` exibir**: ela exibe o `display_status` de **uma única**
submissão — a vinculada ao `source_request_id` da atividade **mais recente** do usuário. Quando o usuário
faz um **duplo check-in** (toca/clica duas vezes no mesmo segundo), a segunda submissão é **corretamente
deduplicada** (`repeated_same_action_same_day`) e gravada como `display_status='not_realized'`. Como essa
segunda submissão tem `event_time` mais novo, ela vira a "atividade mais recente" e a coluna passa a
exibir o `not_realized` do **duplicado descartado**, em vez do `sent` da submissão real.

---

## 2. Evidência de produção (read-only, coletada em 2026-06-22)

Acesso conforme `docs/Instrucoes/instrucoes_acesso_Digital_Ocean.md` (SSH via WSL → `docker exec
checkcheck-db-1 psql -U postgres -d checking`). Banco: `checking`. Container: `checkcheck-db-1`.

**Usuário:** `users.id=46`, `chave=CY22`, `nome="Rafael Mota Moreira"`, `projeto=P80`, `rfid` vazio
(usuário web), `checkin=true`, `time=2026-06-21 23:34:32.118+00` (= **2026-06-22 07:34 em Asia/Singapore**).

**Duas submissões de check-in no mesmo dia-projeto, com ~64 ms de diferença** (duplo check-in):

| FormsSubmission | request_id | event_time (UTC) | status | display_status | last_error |
|---|---|---|---|---|---|
| `id=5393` | `web-check-1782084872054-kbfnef7r` | `…32.054` | **success** | **sent** | (vazio) |
| `id=5394` | `web-check-1782084872118-01g1l812` | `…32.118` | **skipped** | **not_realized** | `repeated_same_action_same_day` |

**Eventos correspondentes (`check_events`):**

| id | source | status | message | idempotency_key |
|---|---|---|---|---|
| `21064` | web | queued | Web check event accepted and queued for Forms submission | `web_forms:web-check-1782084872054-kbfnef7r` |
| `21065` | web | updated | Web check event accepted without new Forms submission | `web_forms:web-check-1782084872118-01g1l812` |
| **`21068`** | **forms** | **success** | **Form submitted successfully** (`display_status=sent`) | `web-check-1782084872054-kbfnef7r:result` |

> Observação: os eventos `21066`/`21069` que aparecem no intervalo pertencem a **outro** usuário
> (`chave=ESRH`), não ao CY22. O Rafael fez exatamente **duas** submissões hoje.

**`user_sync_events` do `user_id=46` (as duas candidatas a "mais recente"):**

| id | source | action | event_time (UTC) | source_request_id |
|---|---|---|---|---|
| **`9968`** | web_forms | checkin | **`…32.118`** | `web-check-1782084872118-01g1l812` → submissão **skipped/not_realized** |
| `9967` | web_forms | checkin | `…32.054` | `web-check-1782084872054-kbfnef7r` → submissão **success/sent** |

Como `9968.event_time (.118) > 9967.event_time (.054)`, a atividade "mais recente" é a `9968`, que aponta
para a submissão **descartada** → coluna mostra **"Não Realizado"**.

**Padrão recorrente:** o mesmo par `sent`+`not_realized` aparece para este usuário em 2026-06-17, 06-18 e
06-19. Não é evento único — é um bug sistemático sempre que há duplo check-in/checkout no mesmo dia.

---

## 3. Causa-raiz no código

**Arquivo:** `sistema/app/routers/admin.py` — função `build_presence_rows` (≈ linhas 980–1063).

A coluna "Forms" (`schemas.UserRow.forms_status`) é resolvida assim:

1. `latest_activities = resolve_latest_user_activities(db, users=rows)` — escolhe **uma** atividade
   (check-in/out) "mais recente" por usuário. O desempate entre eventos de sync do mesmo dia e mesma
   fonte é `(event_time, prioridade_da_fonte, id)` **decrescente** → vence o de **`event_time` maior**
   (ver `select_preferred_sync_event_from_events` em `services/user_sync.py`).
2. Constrói um mapa só com os request_ids dessas atividades:

   ```python
   forms_status_by_request_id = {
       request_id: display_status
       for request_id, display_status in db.execute(
           select(FormsSubmission.request_id, FormsSubmission.display_status).where(
               FormsSubmission.request_id.in_(sorted(presence_request_ids))
           )
       ).all()
       if request_id and display_status
   } if presence_request_ids else {}
   ```
3. No loop, atribui: `forms_status=forms_status_by_request_id.get(latest_activity.source_request_id)`.

**O bug:** o passo (1) seleciona o sync event mais novo, que no duplo check-in é o **duplicado
deduplicado** (`skipped`, `not_realized`). O passo (3) então exibe `not_realized` mesmo existindo uma
submissão **irmã** (mesmo `chave` + mesma `action` + mesmo dia-projeto) que de fato foi **`sent`**.

**Por que a submissão duplicada existe e é `not_realized` (comportamento correto a ser preservado):**
em `services/forms_submit.py` → `submit_forms_event`, quando `should_enqueue_forms_for_action` retorna
`False` (motivo `repeated_same_action_same_day` / `repeated_checkout`), chama-se
`record_forms_submission_skip(...)` que grava `status='skipped'`, `display_status='not_realized'`. Isso é
**proposital** — evita reenviar o Forms. O defeito é **só** na exibição (read-side), não na escrita.

**Escopo do `forms_status`:** o campo só é produzido em `build_presence_rows` e só é consumido pela tabela
de presença do admin (`schemas.py` `UserRow.forms_status`; `static/admin2/app.js` `formatFormsStatus`).
Logo, a correção é **localizada** a `build_presence_rows` (+ um helper) e **não** afeta o Check Web nem o
caminho de escrita.

---

## 4. Decisão de design da correção (resumo para contexto dos prompts)

**Princípio:** quando a submissão vinculada à atividade mais recente for um **skip** (`status='skipped'`),
não exibir cegamente o `not_realized`. Em vez disso, resolver o status **efetivo** a partir da submissão
**real** do mesmo check-in lógico: mesma `chave`, mesma `action`, no **mesmo dia-projeto** do `event_time`
da atividade mais recente. Entre as irmãs, escolher a de maior prioridade de ciclo de vida e exibir o
`display_status` dela. Se **não** existir irmã não-skip (ex.: Forms desabilitado para o projeto, ou um
duplicado solitário), **manter `not_realized`** (preservando o teste existente).

**Por que gatilhar só no caso `skipped`:** é a mudança de comportamento mais estreita possível. Para linhas
normais (submissão única, não-skip) o resultado é **idêntico** ao atual. (Na prática, a deduplicação
garante no máximo **uma** submissão não-skip por `(chave, action, dia-projeto)`, então não há ambiguidade
entre duas submissões reais.)

**Prioridade de ciclo de vida (`FormsSubmission.status`) para escolher a irmã:**
`success (4) > failed (3) > processing (2) > pending (1) > skipped (0)`; desempate por `processed_at`
(depois `event_time`, depois `id`) mais recente. Use o `display_status` da irmã escolhida. Se a melhor
irmã ainda for `skipped` → `not_realized`.

Resultados esperados:
- Duplo check-in (irmã `success/sent` + duplicado `skipped/not_realized`) → **`sent`** ("Enviado"). ✅ (corrige CY22)
- Submissão única `filling` → **`filling`**. ✅ (inalterado)
- Skip solitário sem irmã real (Forms desabilitado / duplicado isolado) → **`not_realized`**. ✅ (inalterado, teste existente preservado)
- Irmã `failed/aborted` + duplicado `skipped` → **`aborted`** (verdade exibida, não escondida). ✅

**Helpers disponíveis:** `is_same_project_day(first, second, *, timezone_name=...)` em
`services/user_sync.py`; o timezone do projeto por linha já está em `timezone_context.timezone_name`
dentro do loop de `build_presence_rows`. Os rótulos de exibição estão em
`services/forms_queue.py` (`FORMS_DISPLAY_STATUS_BY_LABEL`) e no front em `formatFormsStatus`.

---

## 5. PROMPT 1 (NECESSÁRIO) — Corrigir a resolução do `forms_status` no admin + testes (TDD)

> **✅ EXECUTADO 2026-06-22 (sem deploy).** Backend corrigido:
> - `sistema/app/services/forms_queue.py`: helper puro `resolve_effective_skipped_display_status` +
>   `FORMS_SUBMISSION_STATUS_PRIORITY` + namedtuple `FormsSiblingCandidate`.
> - `sistema/app/routers/admin.py` → `build_presence_rows`: quando a submissão vinculada é `skipped`,
>   resolve o status efetivo a partir das irmãs (mesma chave/action/dia-projeto), em LOTE (sem N+1).
> - Testes: `tests/test_admin_presence_forms_status.py` (4 novos de integração; o teste do skip solitário
>   foi preservado) + `tests/test_forms_effective_display_status.py` (8 unit do helper). **14/14 verdes.**
> - Suíte completa: 619 passaram; 33 falhas são **pré-existentes/ambientais** (Windows: boot do app em
>   subprocesso + transport-AI + migração 0061), comprovado via `git stash` (falham idênticas sem o fix).
>   `tests/test_api_flow.py` não coleta no Windows (conftest_accident trava o sqlite) — rodar no Linux/CI.
> - **Pendente:** PROMPT 2 (verificação completa + deploy humano-gated).

> Cole o bloco abaixo como tarefa para o agente de implementação. Ele é autossuficiente.

```
CONTEXTO DO PROJETO
- Repositório "checkcheck" (monólito FastAPI + SQLAlchemy 2.x; SQLite em dev, PostgreSQL em prod).
- Idioma do projeto: português nos comentários/docs; identificadores em inglês. SQLAlchemy 2.x usa
  `Mapped[...]` + `mapped_column`. Pydantic v2.
- Convenções relevantes (ver CLAUDE.md): `CheckEvent.action` é String(16); notificar SSE após mutações.
  ESTA tarefa é apenas read-side: NÃO há mutação, NÃO chame brokers SSE, NÃO crie migração.

PROBLEMA A CORRIGIR (causa-raiz já diagnosticada — confie nela, mas confirme lendo o código)
- Na tabela "Usuários em Check-In" do admin (aba Check-In), a coluna "Forms" mostra "Não Realizado"
  para um usuário cujo Forms foi de fato ENVIADO. Causa: a coluna exibe o `display_status` de UMA única
  `FormsSubmission` — a vinculada ao `source_request_id` da atividade mais recente do usuário. Quando o
  usuário faz um duplo check-in no mesmo dia, a 2ª submissão é deduplicada (motivo
  `repeated_same_action_same_day`) e gravada como `status='skipped'`, `display_status='not_realized'`.
  Como ela tem `event_time` mais novo, vira a "atividade mais recente" e a coluna mostra `not_realized`,
  ignorando a submissão IRMÃ (mesma chave/action/dia) que foi `status='success'`, `display_status='sent'`.
- O dado está CORRETO (o Forms foi enviado; o skip é um registro correto do duplicado descartado). O
  defeito é SÓ na exibição.

EVIDÊNCIA DE PRODUÇÃO (para você modelar os testes fielmente)
- Usuário CY22 (user_id=46, projeto único P80). Duas submissões de check-in no mesmo dia, ~64ms de gap:
  * FormsSubmission request_id="web-check-1782084872054-kbfnef7r", event_time=…32.054,
    status="success", display_status="sent".
  * FormsSubmission request_id="web-check-1782084872118-01g1l812", event_time=…32.118 (mais novo),
    status="skipped", display_status="not_realized", last_error="repeated_same_action_same_day".
- Dois UserSyncEvent (source="web_forms", action="checkin"): id=9968 event_time=…32.118
  source_request_id="…872118…" (vence o desempate por event_time) e id=9967 event_time=…32.054
  source_request_id="…872054…".
- Resultado atual (bug): coluna mostra "Não Realizado". Resultado esperado (após fix): "Enviado".

ARQUIVO PRINCIPAL
- sistema/app/routers/admin.py → função `build_presence_rows` (≈ linhas 980–1063). É lá que
  `forms_status` é resolvido. O bloco atual:
      presence_request_ids = { la.source_request_id for la in latest_activities.values()
                               if la is not None and la.source_request_id }
      forms_status_by_request_id = { request_id: display_status
          for request_id, display_status in db.execute(
              select(FormsSubmission.request_id, FormsSubmission.display_status)
              .where(FormsSubmission.request_id.in_(sorted(presence_request_ids)))
          ).all() if request_id and display_status } if presence_request_ids else {}
      ...
      forms_status=forms_status_by_request_id.get(latest_activity.source_request_id),

COMPORTAMENTO ALVO (mude APENAS o necessário)
1. Mantenha o comportamento atual para o caso normal: se a submissão vinculada à atividade mais recente
   NÃO for `status='skipped'`, o `forms_status` continua sendo o `display_status` dela.
2. Quando a submissão vinculada for `status='skipped'`, resolva o status EFETIVO a partir das submissões
   IRMÃS do mesmo check-in lógico: mesma `chave` (a do usuário da linha), mesma `action`
   (== latest_activity.action), no MESMO dia-projeto do `event_time` da atividade mais recente — use
   `is_same_project_day(submission.event_time, latest_activity.event_time, timezone_name=<tz do projeto>)`,
   onde o tz é o `timezone_context.timezone_name` já calculado para a linha.
   - Entre as irmãs, escolha por prioridade de ciclo de vida de `FormsSubmission.status`:
     success(4) > failed(3) > processing(2) > pending(1) > skipped(0); desempate por `processed_at`,
     depois `event_time`, depois `id` (mais recente vence). Use o `display_status` da irmã escolhida.
   - Se a melhor irmã ainda for `skipped` (ou seja, NÃO existe irmã não-skip), mantenha `not_realized`.
3. Eficiência: NÃO faça query por linha (evite N+1). Busque em lote. Sugestão:
   - Primeiro, busque as submissões vinculadas trazendo TAMBÉM o `status` (não só `display_status`),
     para identificar quais atividades mais recentes apontam para um `skipped`.
   - Para o conjunto de `chave`s cujas vinculadas são `skipped`, faça UMA query trazendo
     (chave, action, event_time, processed_at, id, status, display_status) e agrupe em memória por chave.
     No loop, filtre por action == latest_activity.action e mesmo dia-projeto, e aplique a prioridade.
   - Para linhas cuja vinculada NÃO é skip, não faça trabalho extra.
4. Coloque a lógica pura de escolha (a função que, dada uma lista de candidatas, devolve o display_status
   efetivo) em um helper testável. Sugestão de local: `sistema/app/services/forms_queue.py` (que já é o
   dono dos rótulos/estados de display do Forms) — ex.: uma constante de prioridade e uma função pura
   `resolve_effective_skipped_display_status(candidates) -> str | None`. A montagem do dia-projeto/tz fica
   em admin.py. Não refatore além disso (o projeto valoriza não mexer no que funciona).

RESTRIÇÕES
- NÃO altere `schemas.UserRow` (mantenha `forms_status: str | None`).
- NÃO altere o caminho de escrita (forms_submit.py / forms_queue.py enqueue/skip). A deduplicação está
  correta.
- NÃO crie migração Alembic. NÃO faça backfill. NÃO mexa no Check Web nem no front admin (a correção é
  100% backend e o front já traduz `sent` → "Enviado").
- Mantenha read-only: nenhum commit de dados, nenhuma notificação SSE nova.

TESTES (TDD — escreva primeiro, veja falhar, depois implemente)
- Arquivo existente: tests/test_admin_presence_forms_status.py. Estude os dois testes atuais; eles usam
  `build_presence_rows(db, action="checkin", current_admin=None, reference_time=event_time)` com SQLite
  via `SessionLocal`/`engine` e `Base.metadata.create_all/drop_all`. Siga EXATAMENTE esse padrão.
- PRESERVE o teste `test_presence_rows_include_not_realized_forms_status_for_skipped_forms` (skip solitário
  sem irmã real DEVE continuar retornando "not_realized"). Se sua implementação quebrá-lo, está errada.
- ADICIONE testes novos:
  a) Duplo check-in (replica CY22): crie Project P80; um User; DOIS UserSyncEvent action="checkin"
     (event_times .054 e .118, o .118 mais novo) com source_request_ids distintos; DUAS FormsSubmission:
     a do .054 com status="success"/display_status="sent", a do .118 com status="skipped"/
     display_status="not_realized"/last_error="repeated_same_action_same_day". Asserir forms_status == "sent".
  b) Variante checkout: mesma ideia com action="checkout" e last_error="repeated_checkout"; irmã
     status="success"/display_status="sent" → asserir "sent". (Chame build_presence_rows com action="checkout".)
  c) Irmã que falhou: irmã status="failed"/display_status="aborted" + duplicado skipped → asserir "aborted".
  d) (Opcional) Irmã ainda em andamento: irmã status="processing"/display_status="filling" + duplicado
     skipped → asserir "filling".
- Adicione também testes unitários para o helper puro (sem DB), cobrindo a tabela de prioridades e o
  fallback para None/not_realized quando só há skipped.

COMO RODAR
- Ative o venv do repo (.venv). Rode os testes-alvo primeiro e depois a suíte de presença:
    python -m pytest tests/test_admin_presence_forms_status.py -q
- Em seguida rode a suíte completa do backend (pule testes de produção se houver marcador) para garantir
  zero regressão:
    python -m pytest -q
- Entregue: diff mínimo em admin.py (+ helper no forms_queue.py) e os testes novos, todos verdes,
  test existente preservado. Explique no resumo final por que o caso "skip solitário" continua
  retornando not_realized.
```

---

## 6. PROMPT 2 (NECESSÁRIO) — Verificação completa e (deploy humano-gated) confirmação em produção

> **✅ EXECUTADO 2026-06-22 (deploy aprovado pelo humano).**
> - Passo 1: alvo 14/14 verdes; suíte completa 619 passaram / 33 falhas pré-existentes (provadas via
>   `git stash`) / 12 skipped.
> - Passo 2: dado de prod do CY22 inalterado (5394 skipped/not_realized + 5393 success/sent).
> - Passo 3: commit `71fa182` → push em `main` → **Deploy OceanDrive** run `27926082312`
>   `conclusion=success`, `--log-failed` vazio (anotação "exit code 1" = ruído pós-passo, Seção 6.2).
> - Passo 4: imagem em prod = `checkcheck-app:71fa1829…` (= commit), health `ok`/db ok/forms_worker ok.
>   A linha do CY22 passa a renderizar **"Enviado"** (código corrigido servindo + dado inalterado +
>   teste de integração que espelha o CY22). Confirmação visual final no admin fica a cargo do operador.

> O deploy de produção é **humano-gated** (ver `docs/Instrucoes/instrucoes_acesso_Digital_Ocean.md`,
> Seção 6.3: monitorar **Deploy OceanDrive** no repo `checking`). Não faça deploy sem aprovação explícita.

```
TAREFA: validar a correção do PROMPT 1 e confirmar a inconsistência resolvida — sem alterar código.

CONTEXTO
- Foi corrigido o read-side da coluna "Forms" da tabela "Usuários em Check-In" (admin, aba Check-In).
  Antes: usuário CY22 (Rafael Mota Moreira, projeto P80) mostrava "Não Realizado" apesar de o Forms ter
  sido enviado (evento 21068, display_status=sent). Causa: a coluna exibia o duplicado deduplicado
  (status=skipped, not_realized) por ele ter event_time mais novo, em vez da submissão irmã sent.
- A correção é 100% backend (sistema/app/routers/admin.py + helper). Não há migração nem mudança de dados.

PASSO 1 — Verificação local (obrigatório)
- Ative o .venv. Rode:
    python -m pytest tests/test_admin_presence_forms_status.py -q
    python -m pytest -q     # suíte completa; 0 falhas; contagem >= baseline + testes novos
- Confirme que o teste "skip solitário → not_realized" segue verde e que o novo "duplo check-in → sent"
  passa.

PASSO 2 — Verificação de produção ANTES do deploy (read-only, opcional mas recomendado)
- Acesso conforme docs/Instrucoes/instrucoes_acesso_Digital_Ocean.md (SSH via WSL → docker exec
  checkcheck-db-1 psql -U postgres -d checking). É READ-ONLY: somente SELECT.
- Reconfirme o estado dos dados do CY22 (deve continuar: submissão …872054… = success/sent e
  …872118… = skipped/not_realized). O dado NÃO deve mudar — a correção é de exibição.
    SELECT id, request_id, status, display_status, last_error, event_time
      FROM forms_submissions WHERE chave='CY22' ORDER BY id DESC LIMIT 6;

PASSO 3 — Deploy (SOMENTE com aprovação humana explícita)
- Caminho canônico do monólito: repo root `checking`, push em `main` dispara o workflow
  "Deploy OceanDrive". NÃO use o sub-repo admin2 (este fix é backend do monólito, não do front admin).
- Monitore conforme Seção 6.3 das instruções:
    $run = gh run list --repo tscode-com-br/checking --workflow "Deploy OceanDrive" --limit 1 --json databaseId --jq ".[0].databaseId"
    gh run watch $run --repo tscode-com-br/checking --exit-status
    gh run view $run --repo tscode-com-br/checking --json status,conclusion --jq '{status,conclusion}'
- Anotação "exit code 1" pode ser ruído de pós-passo (Seção 6.2). Confirme conclusion=success e
  --log-failed vazio.

PASSO 4 — Confirmação pós-deploy (read-only)
- Abra a aba Check-In do admin (https://tscode.com.br/checking/admin) ou chame o endpoint de presença e
  confirme que a linha do CY22 agora mostra "Enviado" (forms_status="sent"), com os mesmos dados de banco.
- Se ainda mostrar "Não Realizado": confirme que a imagem do app em prod corresponde ao commit do fix
  (docker inspect checkcheck-app-1 --format '{{.Config.Image}}') e que o deploy foi pelo caminho certo
  (root/oceandrive), não pelo sub-repo.

ENTREGÁVEL: relatório curto com (a) contagem de testes antes/depois, (b) saída do SELECT de prod,
(c) screenshot/registro da linha do CY22 mostrando "Enviado" após deploy (se o deploy for autorizado).
```

---

## 7. PROMPT 3 (OPCIONAL — hardening, NÃO necessário para corrigir a inconsistência)

> **Leia antes de executar:** este prompt é **opcional** e **não** é necessário para resolver a
> inconsistência relatada. A deduplicação do servidor **já** impede o reenvio duplicado do Forms; o duplo
> check-in não causa dano de dado. Mexer no Check Web é **maior risco** e contraria o princípio "alterar
> apenas o necessário". Só execute se o time decidir explicitamente reduzir os cliques/toques duplicados
> na origem. Caso contrário, **ignore este prompt.**

```
TAREFA (OPCIONAL): reduzir o duplo-envio de check-in/checkout na origem (Check Web), de forma defensiva.

CONTEXTO
- Usuários disparam dois check-ins idênticos em ~64ms (duplo toque/clique ou retry), gerando uma 2ª
  submissão que o servidor corretamente deduplica (repeated_same_action_same_day). Isso é inofensivo no
  dado, mas polui eventos e foi o gatilho do bug de exibição (já corrigido no read-side pelo PROMPT 1).
- Objetivo aqui: evitar que o mesmo gesto envie duas requisições, SEM mudar contratos de API nem o
  servidor.

ESCOPO E RESTRIÇÕES
- Apenas front do Check Web: sistema/app/static/check/ (provável app.js / automatic-activities.js).
  IMPORTANTE: confirme qual handler envia o check-in manual antes de tocar.
- Atenção (memória do projeto): o Check Web público é servido pelo MONÓLITO (deploy via root/oceandrive),
  e existe um espelho admin2 (não confundir). Aqui é o CHECK WEB, não o admin.
- Mudança mínima: desabilitar o botão de check-in/checkout durante o envio (estado "enviando…") e
  reabilitar no retorno; e/ou um debounce/guarda de idempotência por gesto. NÃO altere a geração do
  client_event_id de forma que quebre o replay offline/idempotência existente.
- Preserve i18n (pt/en/zh/ms/id/tl) se adicionar qualquer texto de estado.
- Não altere endpoints, schemas, nem o caminho de escrita do servidor.

TESTES/VALIDAÇÃO
- Se houver suíte de front/unit para o Check Web, adicione um teste de que cliques repetidos durante o
  envio não disparam duas chamadas. Caso contrário, valide manualmente e descreva o teste manual.
- Confirme que um único check-in continua funcionando (sem regressão no fluxo normal e no replay offline).

ENTREGÁVEL: diff mínimo no front do Check Web, com descrição do teste (automatizado ou manual) e nota
de que o servidor permanece intocado.
```

---

## 8. Checklist de não-regressão / armadilhas

- [ ] O teste existente `test_presence_rows_include_not_realized_forms_status_for_skipped_forms` continua
      verde (skip **solitário** sem irmã real → `not_realized`). Se quebrar, a correção está errada.
- [ ] Caso normal (submissão única, não-skip) → `forms_status` idêntico ao atual (sem mudança).
- [ ] Sem N+1: a busca das irmãs é em lote.
- [ ] Sem migração, sem backfill, sem escrita, sem SSE novo. Read-side puro.
- [ ] `schemas.UserRow.forms_status` inalterado.
- [ ] Deploy (se autorizado) pelo repo root `checking` → workflow **Deploy OceanDrive** (monólito), **não**
      pelo sub-repo admin2.
- [ ] Timezone correto no `is_same_project_day`: usar o tz do projeto da linha (`timezone_context.timezone_name`),
      não o tz do sistema, para o agrupamento por dia-projeto.
```
