# Fase 14.3 - Validacao manual em preview local

## Objetivo

Executar uma validacao manual real do fluxo de IA de transporte em preview local, usando banco SQLite isolado, provider fake e modo deterministico, para confirmar o comportamento visivel de `Ajustes`, `Alteracoes`, `Salvar`, `Implement Modifications`, `Aplicar` e `Cancelar` sem depender apenas da suite automatizada.

## Ambiente validado

Data da validacao manual: 2026-05-04.

URL validada: `http://127.0.0.1:8011/transport`.

Banco isolado usado no preview: `preview_transport_ai_validation.db`.

Configuracao efetiva usada para o preview:

1. `TRANSPORT_AI_ENABLED=true`
2. `TRANSPORT_AI_AGENT_MODE=deterministic`
3. `TRANSPORT_AI_ROUTE_PROVIDER=fake`
4. `FORMS_QUEUE_ENABLED=false`
5. `BOOTSTRAP_ADMIN_KEY=HR70`
6. `BOOTSTRAP_ADMIN_PASSWORD=eAcacdLe2`
7. `MAPBOX_ACCESS_TOKEN=test-mapbox-token`
8. `OPENAI_API_KEY=sk-test-openai-token`

Para tornar o preview reproduzivel, foi adicionado `scripts/seed_transport_ai_preview_validation.py`, que prepara dois cenarios pequenos de validacao manual:

1. `2026-05-04` com passageiro `A14A`, projeto `AI14 Preview Apply` e veiculo `AI14AP1`, iniciando em baseline `pending` para validar `save/reopen/apply`.
2. `2026-05-05` com passageiro `A14C`, projeto `AI14 Preview Cancel` e veiculo `AI14CN1`, iniciando em baseline `confirmed` para exercitar o caminho de restore.

Os comandos usados para preparar e subir o preview foram estes:

```powershell
if (Test-Path .\preview_transport_ai_validation.db) { Remove-Item .\preview_transport_ai_validation.db -Force }
$env:DATABASE_URL='sqlite+pysqlite:///./preview_transport_ai_validation.db'
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m alembic upgrade head
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/seed_transport_ai_preview_validation.py
```

```powershell
$env:TRANSPORT_AI_ENABLED='true'
$env:TRANSPORT_AI_AGENT_MODE='deterministic'
$env:TRANSPORT_AI_ROUTE_PROVIDER='fake'
$env:MAPBOX_ACCESS_TOKEN='test-mapbox-token'
$env:OPENAI_API_KEY='sk-test-openai-token'
$env:FORMS_QUEUE_ENABLED='false'
$env:BOOTSTRAP_ADMIN_KEY='HR70'
$env:BOOTSTRAP_ADMIN_NAME='Transport AI Preview Admin'
$env:BOOTSTRAP_ADMIN_PASSWORD='eAcacdLe2'
./scripts/start_local_preview_api.ps1 -Port 8011 -DatabaseFile preview_transport_ai_validation.db
```

## Credenciais usadas

Login no `/transport`: `HR70 / eAcacdLe2`.

## Estados principais observados

### 1. Dashboard autenticado com dados seeded

Depois do login, o dashboard foi desbloqueado com o status `Transport access granted.`. No dia `2026-05-04`, a lista `EXTRA` mostrou o passageiro `AI Preview Apply Rider` e a frota mostrou o veiculo `AI14AP1` com ocupacao `0/4`. Isso confirmou que o preview local estava lendo o banco isolado correto.

### 2. Modal `Ajustes` abriu com os defaults esperados

Ao acionar `IA > Calculate Routes`, o modal `AI Agent Settings` abriu com os campos:

1. `Earliest Boarding = 06:50`
2. `Arrival Time at Work = 07:45`

O rodape exibiu `Cancel` e `Request Routes`, e o estado inicial do modal estava consistente com o HTML/testes automatizados da fase 11.

### 3. `Solicitar Rotas` gerou suggestion e abriu `Alteracoes`

No dia `2026-05-04`, o clique em `Request Routes` retornou com sucesso e abriu a janela `Changes`. O handoff visual observado foi:

1. feedback de sucesso `Transport AI suggestion is ready for review.`;
2. painel `Summary` com custo sugerido `SGD 15.00`, frota `1 -> 1`, `1 allocated` e janela `06:50 -> 07:45`;
3. painel `Vehicles` mostrando `Keep` para `AI14AP1`;
4. painel `Passengers` mostrando `AI Preview Apply Rider` alocado em `AI14AP1` com pickup `07:42`;
5. painel `Routes` mostrando a sequencia `Pickup -> Destination` ate `1 Marina Boulevard`.

Com isso, a janela `Alteracoes` ficou legivel e suficiente para revisão manual do plano sugerido.

### 4. `Salvar` e `Implement Modifications` funcionaram

Ainda no dia `2026-05-04`, o clique em `Save` fechou a janela e exibiu o status `Transport AI suggestion was saved and is ready to be applied.`. Em seguida, `IA > Implement Modifications` reabriu a mesma suggestion salva, agora com badges `Run Saved` e `Suggestion Saved`, e com o botao `Save` corretamente desabilitado. Isso validou o caminho completo de persistencia e reabertura da suggestion pelo menu do dashboard.

### 5. `Aplicar` alterou o dashboard

No mesmo fluxo salvo, o clique em `Apply` devolveu `Transport AI suggestion was applied.` e o dashboard foi recarregado. O estado visivel apos o refresh confirmou a alteracao operacional:

1. o passageiro `AI Preview Apply Rider` passou a aparecer como `Assigned to AI14AP1 | Transport AI suggestion applied.`;
2. o veiculo `AI14AP1` mudou de `0/4` para `1/4`;
3. a linha do request deixou de indicar estado `transport_ai_reset_to_pending` e voltou ao estado confirmado no veiculo.

### 6. `Cancelar` restaurou o baseline

Para validar o restore de baseline de forma manual, um segundo run foi executado no proprio dia `2026-05-04`, agora partindo do baseline confirmado criado pelo apply anterior. Esse segundo run abriu a suggestion normalmente, a lista do dashboard voltou temporariamente para `transport_ai_reset_to_pending` e a ocupacao do veiculo caiu para `0/4` enquanto a suggestion estava em review. Ao clicar em `Cancel`, o dashboard exibiu `Transport AI suggestion was cancelled and the baseline was restored.` e o estado operacional retornou ao baseline confirmado:

1. o passageiro voltou a aparecer como `Assigned to AI14AP1 | Transport AI suggestion applied.`;
2. o veiculo `AI14AP1` voltou para ocupacao `1/4`.

Esse passo confirmou manualmente que `cancel` desfaz o reset intermediario e recoloca o dashboard no estado capturado como baseline da run.

## Resultado do checklist manual

1. Modal `Ajustes` abre com defaults: validado.
2. `Solicitar Rotas` gera suggestion: validado.
3. Janela `Alteracoes` e compreensivel: validado.
4. `Salvar` e reabrir funciona: validado.
5. `Aplicar` altera dashboard: validado.
6. `Cancelar` restaura baseline: validado.

## Problemas encontrados durante a validacao

### Problema 1. Fixture inicial de preview usava `chave` longa demais

Na primeira tentativa manual, o preview seeded usava chaves `AI14APPLY` e `AI14CANCEL`, o que quebrou `POST /api/transport/ai/route-calculations` com o erro `TransportAgentPlanningRequest chave String should have at most 4 characters`. Esse problema foi resolvido dentro desta fase com a atualizacao do seed reprodutivel para usar `A14A` e `A14C`, respeitando a restricao do schema e permitindo a execucao manual real do fluxo.

### Problema 2. O cenario secundario de `2026-05-05` retornou plano invalido no start

Ao tentar validar `cancel/restore` diretamente no cenario seeded de `2026-05-05`, o backend respondeu com `Deterministic transport AI execution produced an invalid plan: Partition 'extra:AI14 Preview Cancel:SG' is missing a consolidated solver result for request '2'. Baseline restored.`. Como o objetivo desta fase era fechar a validacao manual em preview local, e nao abrir uma correcao funcional nova do planner, o fechamento manual foi concluido usando o baseline confirmado do proprio dia `2026-05-04` apos o apply bem-sucedido. Nesse caminho, `cancel/restore` foi validado de ponta a ponta com sucesso.

## Artefatos produzidos nesta fase

1. `scripts/seed_transport_ai_preview_validation.py` para preparar o banco de preview com cenarios reprodutiveis.
2. Este documento `docs/fase_ai_14_validacao_manual.md` com comandos, ambiente, estados observados e problemas encontrados.

## Parecer final

Com o banco isolado, provider fake e runner deterministico, o fluxo manual principal do agente de IA no `/transport` foi exercitado de ponta a ponta em preview local. O dashboard abriu corretamente, a suggestion foi gerada e revisada, `save/reopen` funcionou, `apply` alterou o estado operacional visivel e `cancel` restaurou o baseline confirmado no rerun manual do mesmo dia. A fase 14.3 pode ser considerada atendida para fechamento manual em preview local.