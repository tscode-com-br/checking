# To-Do List da Correcao - Hotfix para impedir persistencia de `Localizacao nao Cadastrada` na Web

## Como usar este arquivo

Cada item abaixo foi escrito como um prompt operacional para um agente de IA implementar a correcao no codigo.

Regras globais para qualquer agente que execute um item desta lista:

1. trate esta correcao como hotfix isolado;
2. nao misture esta entrega com Modificacao 6, memberships multi-projeto, migracoes de banco ou mudancas de geometria;
3. nao altere dados de producao;
4. nao altere tolerancias, thresholds ou o catalogo de localizacoes;
5. nao reescreva a logica de poligonos em `sistema/app/services/location_matching.py`, salvo se o item mandar explicitamente;
6. preserve os fluxos validos:
   - `check-in` automatico quando `matched = true` e existe `resolved_local` valido;
   - `check-out` automatico quando `status = "outside_workplace"` e as regras existentes permitirem;
   - fluxo manual com local cadastrado;
7. a correcao deve impedir apenas que estados sinteticos de falha, especialmente `Localizacao nao Cadastrada`, virem `local` persistido pela Web;
8. todo codigo novo deve vir com testes de regressao proporcionais ao risco;
9. o pacote final deve ter raio minimo de impacto;
10. sempre que houver duvida entre uma mudanca menor e uma mudanca mais ampla, escolha a menor.


## Fase 0 - Preparacao e congelamento do contexto

### [x] Item 0.1 - Mapear o hotfix minimo e congelar a baseline

Implementacao desta etapa concluida apenas como mapeamento e congelamento de contexto, sem alterar comportamento da aplicacao e sem alterar testes.

O que foi inspecionado nesta fase:

- `docs/temp_002.md`, para alinhar a causa raiz, os invariantes e o escopo recomendado do hotfix;
- `sistema/app/static/check/automatic-activities.js`;
- `sistema/app/static/check/app.js`;
- `sistema/app/routers/web_check.py`;
- `sistema/app/services/location_matching.py`;
- `tests/test_api_flow.py`;
- `tests/test_location_geometry.py`;
- `tests/test_location_polygon_matching.py`;
- arquivos adicionais descobertos durante o rastreamento real do fluxo automatico:
  - `tests/web_automatic_activities.test.js`;
  - `tests/check_user_location_ui.test.js`;
  - `sistema/app/services/forms_submit.py`;
  - `sistema/app/schemas.py`;
  - `sistema/app/models.py`.

Mapeamento funcional confirmado no workspace:

1. Decisao do fluxo automatico Web:
   - `shouldAttemptAutomaticLocationEvent()` em `sistema/app/static/check/automatic-activities.js` decide os casos automaticos com `resolved_local` valido.
   - `shouldAttemptAutomaticOutOfRangeCheckout()` em `sistema/app/static/check/automatic-activities.js` decide o `check-out` automatico para `status = "outside_workplace"`.
   - `shouldAttemptAutomaticNearbyWorkplaceCheckIn()` em `sistema/app/static/check/automatic-activities.js` e o ponto exato que hoje aprova `check-in` automatico para `status = "not_in_known_location"` quando a ultima acao remota foi `checkout`.

2. Resolucao do `local` automatico:
   - `resolveAutomaticCheckInLocation()` em `sistema/app/static/check/automatic-activities.js` hoje usa esta cascata:
     - `resolved_local`;
     - `label`;
     - fallback final `AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION`.
   - Essa funcao hoje permite que um rótulo sintetico de falha vire `local` operacional.

3. Resolucao do valor final enviado para `submitEndpoint`:
   - `submitAutomaticActivity()` em `sistema/app/static/check/app.js` monta o payload final automatico e envia `local` sem validacao adicional.
   - `runAutomaticActivitiesIfNeeded()` em `sistema/app/static/check/app.js` escolhe qual caminho automatico sera executado.
   - No ramo problematico, `runAutomaticActivitiesIfNeeded()` chama `resolveAutomaticCheckInLocation()` e depois repassa esse valor diretamente para `submitAutomaticActivity()`.
   - `resolveSubmittedLocationValue()` em `sistema/app/static/check/app.js` resolve apenas o submit manual ou semi-manual do formulario principal. Pela logica atual, ele usa `manualLocationSelect.value` quando a selecao manual e permitida e `currentLocationMatch.resolved_local` quando ha match real.

4. Origem de `status = "not_in_known_location"` e do label textual:
   - `match_web_check_location()` em `sistema/app/routers/web_check.py` retorna `status = "not_in_known_location"` quando `matched_location is None` e nao existe classificacao de `outside_workplace`.
   - Nesse mesmo ramo, o backend devolve `label = captured_label or "Localizacao nao Cadastrada"` como texto de interface.
   - O backend tambem retorna `status = "outside_workplace"` quando `resolve_captured_location_label()` classifica o ponto como fora do ambiente, preservando o fluxo automatico de `check-out`.

5. Confirmacao de que o matching poligonal nao e a causa raiz:
   - `resolve_location_match()` em `sistema/app/services/location_matching.py` continua sendo o motor de matching.
   - `resolve_captured_location_label()` em `sistema/app/services/location_matching.py` so distingue entre label de checkout, label de fora do ambiente e ausencia de match.
   - `resolve_submission_local()` em `sistema/app/services/location_matching.py` so normaliza localizacao reconhecida; quando nao ha match, retorna `None`.
   - Os testes em `tests/test_location_geometry.py`, `tests/test_location_polygon_matching.py` e a cobertura de `tests/test_api_flow.py` para `web/check/location` confirmam que a geometria, os tie-breakers e a distincao entre `matched`, `not_in_known_location` e `outside_workplace` ja estao estabilizados.

Leitura tecnica da causa raiz, congelada nesta baseline:

- o backend de localizacao Web nao persiste `Localizacao nao Cadastrada`; ele apenas devolve esse label como estado de interface;
- `setResolvedLocation()` em `sistema/app/static/check/app.js` guarda `currentLocationMatch` somente quando `matchPayload.matched` e verdadeiro, o que confirma que o submit manual comum nao nasce desse label sintetico;
- o bug nasce no ramo automatico da Web:
  - `shouldAttemptAutomaticNearbyWorkplaceCheckIn()` aceita `status = "not_in_known_location"`;
  - `resolveAutomaticCheckInLocation()` cai para `label` ou para o fallback sintetico;
  - `submitAutomaticActivity()` envia esse valor como `local`;
  - `submit_web_check()` recebe o payload e repassa `payload.local` para `submit_forms_event()`;
  - `submit_forms_event()` persiste `local` sem reinterpretar semantica de negocio, usando `local or channel.default_local`.

Arquivos-alvo confirmados para a correcao funcional minima:

- `sistema/app/static/check/automatic-activities.js`
- `sistema/app/static/check/app.js`

Arquivos provaveis para regressao automatizada do hotfix:

- `tests/web_automatic_activities.test.js`
- `tests/check_user_location_ui.test.js`

Arquivos que participaram da analise, mas ficaram explicitamente fora do hotfix minimo desta trilha:

- `sistema/app/routers/web_check.py`
  - permanece apenas como origem legitima de `status` e `label`; nao ha necessidade de mudar contrato de API nesta etapa;
- `sistema/app/services/location_matching.py`
  - fora do hotfix porque a logica de poligonos, tie-breaker e classificacao de distancia ja esta coerente com o diagnostico;
- `tests/test_location_geometry.py`
  - mantido como prova de nao regressao geometrica, sem mudanca prevista;
- `tests/test_location_polygon_matching.py`
  - mantido como prova de nao regressao do matching, sem mudanca prevista;
- `tests/test_api_flow.py`
  - nesta fase fica como cobertura de contrato/backend ja existente; nao e o ponto primario para a correcao funcional minima do emissor Web;
- `sistema/app/services/forms_submit.py`
  - inspecionado apenas para confirmar a persistencia atual e provar que nao e necessario mexer em fila, banco ou sincronizacao para bloquear o bug na origem;
- `sistema/app/schemas.py` e `sistema/app/models.py`
  - inspecionados apenas para confirmar contrato e persistencia existentes, sem necessidade de schema change;
- migrations, CRUD de localizacoes, thresholds, catalogo de locais e qualquer pacote de memberships multi-projeto.

Confirmacoes de baseline exigidas pela fase:

1. Hotfix sem migration e sem alteracao de schema:
   - confirmado.
   - `WebCheckSubmitRequest` reutiliza o contrato ja existente.
   - `forms_submissions.local` e `check_events.local` ja suportam o valor que o frontend envia.
   - o problema e semantico no emissor Web, nao estrutural no banco.

2. Logica de poligonos nao precisa ser tocada:
   - confirmado.
   - o backend ja distingue corretamente:
     - `matched` com `resolved_local`;
     - `outside_workplace`;
     - `not_in_known_location`.
   - a evidencia atual aponta para persistencia indevida apos a resposta, nao para erro de matching.

3. Dependencia oculta de multi-projeto ou banco:
   - nao foi encontrada dependencia oculta que obrigue ampliar o hotfix nesta fase.
   - foi confirmada, porem, uma dependencia explicita e preexistente do workspace com uniao de projetos do usuario em `web_check.py` via `list_user_project_names()` e `filter_locations_for_projects()`.
   - isso nao precisa ser tocado para corrigir o bug, mas aumenta o cuidado de rollout para nao arrastar divergencias maiores entre workspace e producao.

Estrategia de diff minimo congelada para as proximas fases:

1. alterar de forma cirurgica a regra de `shouldAttemptAutomaticNearbyWorkplaceCheckIn()` para que `status = "not_in_known_location"` deixe de aprovar `check-in` automatico;
2. endurecer `resolveAutomaticCheckInLocation()` e, se necessario, o chamador em `app.js`, para que placeholder sintetico de falha nunca mais seja tratado como `local` operacional automatico;
3. preservar sem mudanca os fluxos validos:
   - `check-in` automatico com `matched = true` e `resolved_local` valido;
   - `check-out` automatico com `status = "outside_workplace"`;
   - submit manual com local cadastrado;
4. evitar qualquer mudanca em backend, schema, geometria, thresholds, CRUD de localizacoes ou memberships multi-projeto, salvo se uma fase posterior aprovar explicitamente um guard rail adicional.

Resumo executivo desta fase:

- arquivos-alvo confirmados: `sistema/app/static/check/automatic-activities.js` e `sistema/app/static/check/app.js`;
- arquivos explicitamente fora do hotfix minimo: `sistema/app/routers/web_check.py`, `sistema/app/services/location_matching.py`, `tests/test_location_geometry.py`, `tests/test_location_polygon_matching.py`, `sistema/app/services/forms_submit.py`, `sistema/app/schemas.py`, `sistema/app/models.py` e qualquer migration ou pacote de multi-projeto;
- risco principal do rollout: arrastar para producao divergencias maiores do workspace na area de projetos/memberships ao tentar corrigir um bug que, no diagnostico atual, pode e deve ser resolvido somente no frontend Web.


### [x] Item 0.2 - Verificar a divergencia entre workspace e producao apenas na area do hotfix

Implementacao desta etapa concluida apenas como analise operacional de rollout. Nenhuma alteracao funcional foi aplicada no codigo da Web, nenhum teste foi alterado e nenhum deploy foi executado.

Metodo usado nesta comparacao:

1. releitura de `docs/temp_002.md` e do baseline registrado no Item 0.1;
2. inspecao do workspace atual em:
   - `sistema/app/static/check/index.html`
   - `sistema/app/static/check/app.js`
   - `sistema/app/static/check/automatic-activities.js`
   - `sistema/app/routers/web_check.py`
3. verificacao da superficie publicada em producao por meio dos assets publicos:
   - `https://tscode.com.br/checking/user`
   - `https://tscode.com.br/checking/user/app.js`
   - `https://tscode.com.br/checking/user/automatic-activities.js`
4. consulta ao historico Git local para encontrar um backend Web anterior ao rollout de memberships, em especial o commit `737a321` na trilha de `web_check.py`.

Observacao metodologica importante:

- nao existe neste workspace uma branch nomeada explicitamente como `production` ou `release` para diff direto;
- `main` local e `origin/main` apontam hoje para o mesmo commit visivel no repo, o que nao prova que este e o mesmo commit efetivamente implantado na URL publica;
- por isso, a comparacao com producao foi feita por triangulacao entre:
  - assets realmente servidos em `https://tscode.com.br/checking/user`;
  - evidencia registrada em `docs/temp_002.md`;
  - historico Git do repositorio.

Resultado da comparacao orientada por ponto:

1. Filtro de localizacoes Web por projeto

Workspace atual:

- `sistema/app/routers/web_check.py` usa `list_user_project_names(db, user)` e depois aplica `filter_locations_for_projects(...)`;
- o endpoint de localizacao e o endpoint de lista de locais trabalham com a uniao de projetos do usuario autenticado;
- o frontend do workspace tambem ja esta preparado para isso:
  - `index.html` expõe `data-user-projects-endpoint="/api/web/user-projects"`;
  - a UI usa `projectMembershipButton`, `projectMembershipPanel` e `projectMembershipOptions` em vez de um `select` singular de projeto;
  - o submit usa `resolveCommittedProjectValue()` para enviar o projeto operacional ativo.

Producao publicada:

- o HTML publico de `https://tscode.com.br/checking/user` nao expõe `data-user-projects-endpoint`;
- o HTML publico expõe `data-project-update-endpoint="/api/web/project"` e um `select` singular com `id="projectSelect"`;
- essa superficie publicada e coerente com o modelo legado de projeto singular;
- o commit historico `737a321` confirma esse modelo legado no backend:
  - `get_web_check_locations()` filtrava com `filter_locations_for_project(rows, user.projeto)`;
  - `match_web_check_location()` filtrava com `filter_locations_for_project(all_locations, user.projeto)`.

Leitura operacional:

- a producao esta atrasada em relacao ao workspace neste ponto;
- a divergencia nao e a causa raiz do bug de `Localizacao nao Cadastrada`, mas e a principal fonte de risco de rollout se o hotfix for levado por merge amplo.

2. Funcao `shouldAttemptAutomaticNearbyWorkplaceCheckIn`

Workspace atual:

- `sistema/app/static/check/automatic-activities.js` continua aceitando `status = "not_in_known_location"` como gatilho para `check-in` automatico quando a ultima acao remota foi `checkout`.

Producao publicada:

- o asset publico `https://tscode.com.br/checking/user/automatic-activities.js` tambem continua contendo a mesma regra funcional:
  - rejeita quando `locationPayload` nao existe;
  - rejeita quando `matched` e verdadeiro;
  - exige `status === "not_in_known_location"`;
  - exige ultima acao remota `checkout`;
  - compara o local resolvido com o local corrente antes de aprovar o submit.

Leitura operacional:

- neste ponto, producao e workspace estao funcionalmente alinhados;
- o bug esta presente em ambos;
- a correcao principal do hotfix pode ser portada de forma cirurgica neste ponto sem depender da camada de multi-projeto.

3. Funcao `resolveAutomaticCheckInLocation`

Workspace atual:

- a funcao ainda resolve o local automatico com esta cascata:
  - `resolved_local`;
  - `label`;
  - `AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION`.

Producao publicada:

- o asset publico `https://tscode.com.br/checking/user/automatic-activities.js` continua com a mesma estrategia funcional;
- portanto, a producao ainda aceita que um label sintetico de falha vire `local` operacional no fluxo automatico.

Leitura operacional:

- tambem aqui producao e workspace estao funcionalmente alinhados no defeito;
- a segunda parte do hotfix, de endurecimento do `local` automatico, pode ser carregada como patch pequeno e isolado.

4. Submit automatico e submit manual na Web

Pontos alinhados entre workspace e producao:

- ambos continuam usando `resolveSubmittedLocationValue()` para o `local` do submit manual;
- em ambos, `resolveSubmittedLocationValue()` segue a mesma ideia funcional:
  - usar `manualLocationSelect.value` quando a selecao manual e permitida;
  - usar `currentLocationMatch.resolved_local` quando ha match real;
- o caminho automatico tambem continua conceitualmente igual:
  - `runAutomaticActivitiesIfNeeded()` consulta o estado remoto;
  - chama `shouldAttemptAutomaticNearbyWorkplaceCheckIn(...)`;
  - resolve `automaticLocal`;
  - envia esse valor para `submitAutomaticActivity(...)`.

Divergencia relevante entre workspace e producao:

- na producao publicada, o projeto enviado no payload sai de `projectSelect.value`;
- no workspace atual, o projeto enviado no payload sai de `resolveCommittedProjectValue()`;
- na producao publicada, a UI ainda depende de `/api/web/project` e de um seletor singular de projeto;
- no workspace atual, a UI depende de `/api/web/user-projects` e de uma camada de memberships no frontend.

Leitura operacional:

- a semantica de `local` no submit ainda esta alinhada o bastante para o hotfix do incidente;
- a semantica de `projeto` ja divergiu materialmente entre producao e workspace;
- isso aumenta o risco de levar `app.js` do workspace inteiro para producao sem recorte cirurgico.

Resumo de atraso/adiantamento por tema:

1. Filtro de localizacoes por projeto:
   - workspace adiantado;
   - producao atrasada;
   - divergencia real e relevante para rollout.
2. `shouldAttemptAutomaticNearbyWorkplaceCheckIn`:
   - funcionalmente alinhado entre workspace e producao;
   - bug presente em ambos.
3. `resolveAutomaticCheckInLocation`:
   - funcionalmente alinhado entre workspace e producao;
   - bug presente em ambos.
4. Submit automatico e manual:
   - alinhamento funcional no campo `local`;
   - divergencia real no campo `projeto` e na UI de selecao de projeto;
   - workspace adiantado na camada de memberships.

Risco operacional confirmado nesta etapa:

- o risco nao esta em o hotfix exigir mudanca de banco ou de geometria;
- o risco esta em arrastar, junto com a correcao do bug, a evolucao inteira do fluxo Web de projeto ativo e memberships por usuario;
- como `app.js`, `index.html` e `web_check.py` do workspace atual ja refletem uma camada mais nova de projeto/memberships do que a publicada em producao, um merge amplo do workspace pode misturar:
  - hotfix legitimo do `local`;
  - mudancas nao relacionadas de projeto ativo;
  - dependencia indireta de `user_project_memberships`.

Conclusao operacional congelada para deploy futuro:

- esta analise nao faz parte da correcao funcional do bug;
- ela serve apenas para decidir a estrategia de transporte do patch;
- dado o que foi observado, a recomendacao objetiva mais segura e:
  - `cherry-pick do hotfix para uma branch proxima da producao`.

Justificativa da recomendacao:

1. a producao publicada nao esta na mesma superficie de projeto/submit do workspace atual;
2. o defeito principal do incidente continua visivel tanto no workspace quanto no frontend publicado, o que permite um patch pequeno e cirurgico;
3. esse patch pode ser reaplicado na base proxima da producao sem carregar todo o pacote de memberships/multi-projeto;
4. portanto, para este incidente, `sincronizar tudo` seria uma estrategia de maior risco e menor previsibilidade do que portar apenas o hotfix da automacao/local.


## Fase 1 - Testes de regressao antes da mudanca

### [x] Item 1.1 - Criar testes que reproduzem a persistencia indevida no fluxo automatico

Implementacao desta etapa concluida como congelamento de regressao antes da mudanca funcional. Nenhum comportamento da Web foi corrigido ainda nesta fase; o foco foi escrever testes que denunciem, de forma objetiva, a tentativa de persistir `Localizacao nao Cadastrada` no fluxo automatico.

Decisao de arquitetura de teste adotada nesta etapa:

1. `tests/test_api_flow.py` foi inspecionado como candidato, mas nao foi escolhido como area principal da regressao;
2. a razao e que esse arquivo cobre melhor o backend HTTP depois que um payload ja chegou ao servidor, enquanto o bug nasce antes disso, na decisao automatica do frontend Web;
3. a melhor area encontrada para reproduzir a trilha real foi `tests/check_user_location_ui.test.js`, porque esse arquivo ja possui harnesses maduros para:
   - estado autenticado da Web;
   - localizacao resolvida pela UI;
   - automacao habilitada;
   - consulta ao estado remoto;
   - observacao direta de `submitAutomaticActivity(...)`;
4. como reforco da regra de decisao pura, tambem foi ajustada a cobertura de `tests/web_automatic_activities.test.js`, que isola a politica de automacao sem criar harness paralelo novo.

Arquivos efetivamente alterados nesta etapa:

- `tests/check_user_location_ui.test.js`
- `tests/web_automatic_activities.test.js`

O que foi feito em `tests/check_user_location_ui.test.js`:

1. foi reaproveitado o harness existente `createManualRefreshAutomaticActivityHarness()`, sem criar infraestrutura paralela;
2. foi atualizado o cenario de controller que chama `runAutomaticActivitiesIfNeeded(...)` com precondicoes equivalentes ao incidente:
   - usuario Web autenticado no harness;
   - automacao habilitada no fluxo coberto pelo helper;
   - permissao de localizacao tratada como concedida no contexto do controller;
   - ultima acao remota em `checkout`;
   - local remoto anterior em `Zona Mista`;
   - payload de localizacao com `matched: false`, `status: "not_in_known_location"`, `label: "Localizacao nao Cadastrada"` e proximidade elegivel;
3. o nome do teste passou a deixar explicito o comportamento esperado:
   - `check controller does not submit automatic check-in for a nearby unregistered location after checkout`;
4. esse teste agora verifica o efeito operacional correto:
   - o retorno de `runAutomaticActivitiesIfNeeded(...)` deve ser `{ performed: false, action: null, local: null }`;
   - `fetchWebState` continua ocorrendo para consultar o estado remoto;
   - `submitAutomaticActivity` deve permanecer vazio, provando que o submit automatico foi bloqueado;
5. foi atualizado tambem o cenario de refresh manual que usa a trilha real `runManualLocationRefreshSequence()`:
   - novo nome: `manual refresh should not submit automatic check-in for a nearby unregistered location after checkout`;
   - a assercao principal exige `snapshot.submitAutomaticActivity = []`;
   - a assercao complementar confirma que a sequencia real executou consulta de estado remoto antes de decidir.

O que foi feito em `tests/web_automatic_activities.test.js`:

1. foi ajustado o teste de regra mista para deixar claro que a excecao de saida da `Zona Mista` continua valida apenas para local conhecido;
2. a expectativa de `shouldAttemptAutomaticNearbyWorkplaceCheckIn(...)` foi invertida para `false` quando o payload esta em `not_in_known_location`;
3. foi ajustado o teste dedicado de saida da `Zona de CheckOut` sem match para afirmar explicitamente que esse caminho nao deve mais disparar `check-in` automatico;
4. os nomes dos testes foram atualizados para deixar inequívoco que `Localizacao nao Cadastrada` nao e um `local` operacional valido.

Resultado da execucao da regressao nesta etapa:

1. comando executado:
   - `node --test tests/web_automatic_activities.test.js tests/check_user_location_ui.test.js`
2. resultado observado no estado atual do codigo:
   - os testes novos/ajustados falharam, como esperado para uma fase de regressao antes do hotfix;
3. falhas confirmadas pela execucao:
   - `check controller does not submit automatic check-in for a nearby unregistered location after checkout`
   - `manual refresh should not submit automatic check-in for a nearby unregistered location after checkout`
   - `mixed zone exit exceptions keep automatic check-in immediate after a mixed-zone checkout only for known locations`
   - `automatic nearby-workplace check-in does not run after checkout when leaving checkout zone without a matched location`
4. evidencia concreta capturada pelos testes:
   - o controller hoje ainda retorna `performed: true`, `action: "checkin"` e `local: "Localizacao nao Cadastrada"` nesse caminho;
   - o snapshot de UI mostra tentativa real de submit automatico com esse `local`, o que confirma que a persistencia indevida nasce no frontend Web antes de qualquer protecao de backend.

Conclusao desta etapa:

- a regressao foi escrita no ponto certo da aplicacao, usando a mesma trilha real da Web em vez de um teste superficial de texto;
- o bug agora esta protegido por testes que falham no estado atual;
- quando o hotfix de `automatic-activities.js` e `app.js` for aplicado, estes testes deverao passar sem exigir alteracao de schema, migration ou ajuste de geometria.


### [x] Item 1.2 - Proteger os fluxos validos para evitar regressao colateral

Implementacao desta etapa concluida como reforco de nao regressao da automacao Web antes da mudanca funcional. Nenhuma regra de negocio foi alterada aqui; o trabalho ficou restrito a ampliar e completar a cobertura de testes para os caminhos que devem continuar funcionando depois do hotfix.

Estrategia adotada nesta etapa:

1. reaproveitar a bateria criada e ajustada no Item 1.1;
2. evitar clonar cenarios ja bons;
3. fortalecer testes existentes com assertivas mais operacionais;
4. acrescentar apenas a cobertura que ainda faltava para `accuracy_too_low`.

Arquivos efetivamente alterados nesta etapa:

- `tests/check_user_location_ui.test.js`
- `tests/web_automatic_activities.test.js`

O que foi reforcado em `tests/check_user_location_ui.test.js`:

1. o teste de fluxo valido com local reconhecido apos `checkout` em `Zona Mista` foi mantido como cenario principal de integracao real:
   - nome preservado: `check controller keeps automatic check-in immediate when leaving mixed zone for a known location after checkout`;
   - alem do snapshot de submit, o teste agora tambem valida o retorno operacional de `runAutomaticActivitiesIfNeeded(...)`;
   - a assercao passou a exigir explicitamente `{ performed: true, action: "checkin", local: "Escritório Principal" }`;
2. o teste de `outside_workplace` apos `checkin` em `Zona Mista` tambem foi reforcado:
   - nome preservado: `check controller keeps outside_workplace forcing automatic checkout after a mixed-zone check-in`;
   - o teste continua verificando o submit automatico com `local = "Fora do Local de Trabalho"`;
   - alem disso, agora tambem valida o retorno estrutural `{ performed: true, action: "checkout", local: "Fora do Local de Trabalho" }`;
3. foi adicionado um cenario novo e pequeno para `accuracy_too_low` no mesmo helper de integracao:
   - nome: `check controller does not submit automatic check-in when accuracy is too low after checkout`;
   - precondicoes:
     - ultima acao remota em `checkout`;
     - local remoto anterior em `Zona Mista`;
     - payload com `matched: false`, `status: "accuracy_too_low"`, `label: "Precisão insuficiente"` e sem `resolved_local`;
   - assercoes:
     - retorno `{ performed: false, action: null, local: null }`;
     - `fetchWebState` ainda acontece;
     - `submitAutomaticActivity` permanece vazio;
4. o teste ja existente de refresh manual com local conhecido foi mantido como prova complementar da trilha indireta real:
   - `manual refresh should submit automatic check-in after checkout when leaving checkout zone for a known location`;
   - esse teste continua demonstrando que o caminho de `runManualLocationRefreshSequence()` nao foi prejudicado para `resolved_local` valido.

O que foi reforcado em `tests/web_automatic_activities.test.js`:

1. a suite especifica de `automatic-activities.js` foi mantida como camada de unidade alem da integracao, conforme exigido;
2. os cenarios validos ja existentes continuaram sendo usados como ancora principal:
   - `automatic check-in runs for a known location after checkout when leaving checkout zone`;
   - `automatic out-of-range checkout follows backend outside_workplace status after check-in`;
3. foi adicionado um teste de unidade novo e cirurgico para o estado de baixa precisao:
   - `automatic nearby-workplace check-in does not run when GPS accuracy is too low after checkout`;
   - ele prova que `shouldAttemptAutomaticNearbyWorkplaceCheckIn(...)` nao deve abrir caminho para `check-in` automatico quando o backend sinaliza `accuracy_too_low`.

Separacao final dos quatro grupos de comportamento apos este reforco:

1. automacao valida por local reconhecido:
   - permanece coberta na unidade e na integracao;
   - continua exigindo `resolved_local` real;
2. automacao valida por `outside_workplace`:
   - permanece coberta na unidade e na integracao;
   - continua produzindo `check-out` com `Fora do Local de Trabalho`;
3. automacao proibida por `not_in_known_location`:
   - continua coberta pelos testes abertos no Item 1.1;
   - permanece falhando no estado atual porque o bug ainda existe;
4. automacao proibida por `accuracy_too_low`:
   - agora ficou coberta de forma explicita na unidade e na integracao;
   - o teste demonstra que a unica saida esperada e `no activity`.

Resultado da execucao de testes nesta etapa:

1. comandos executados:
   - `node --test tests/check_user_location_ui.test.js`
   - `node --test tests/web_automatic_activities.test.js`
2. resultado observado em `tests/check_user_location_ui.test.js`:
   - 55 testes passaram;
   - 2 testes falharam;
   - as unicas falhas foram as regressões ja abertas do Item 1.1 para `not_in_known_location`;
   - o novo teste de `accuracy_too_low` passou;
   - os testes reforcados de local conhecido e `outside_workplace` passaram;
3. resultado observado em `tests/web_automatic_activities.test.js`:
   - 20 testes passaram;
   - 2 testes falharam;
   - novamente, as unicas falhas remanescentes foram as regressões do Item 1.1 contra `not_in_known_location`;
   - o novo teste unitario de `accuracy_too_low` passou;
   - os cenarios validos de local conhecido e `outside_workplace` continuaram passando.

Conclusao desta etapa:

- a bateria permaneceu pequena e legivel;
- os fluxos legitimos de automacao que o hotfix precisa preservar ficaram protegidos sem duplicacao desnecessaria;
- `accuracy_too_low` deixou de depender de inferencia indireta e agora tem prova dedicada;
- o estado da suite mostra com clareza que o que ainda quebra nao e a automacao valida, e sim apenas o defeito funcional ja isolado em `not_in_known_location`.


### [x] Item 1.3 - Reforcar a cobertura do matching poligonal sem alterar a geometria

Implementacao desta etapa concluida como blindagem de escopo do hotfix. Nenhuma alteracao foi feita em `sistema/app/services/location_matching.py`, nenhuma regra geometrica foi reescrita e nenhuma suite extensa nova foi criada. O trabalho ficou limitado a revisar a cobertura existente e completar apenas a prova que ainda faltava de forma explicita.

Revisao realizada nesta etapa:

1. `tests/test_location_geometry.py`
   - foi conferido que a suite ja cobre a base geometrica correta;
   - em especial, `test_distance_to_polygon_is_zero_inside_and_positive_outside` ja prova que um ponto interno ao poligono tem distancia `0` para a area e que um ponto externo continua positivo;
   - isso sustenta o comportamento de "estar dentro do poligono" sem exigir qualquer alteracao em funcoes de producao;
2. `tests/test_location_polygon_matching.py`
   - foi verificado que a suite ja cobre intersecao com poligono expandido, desempate por vertice mais proximo, desempate por menor `id`, ignorar geometrias invalidas e retorno `None` quando nao ha intersecao;
   - essa camada ja demonstrava que o resolvedor poligonal em si continua funcional e deterministico;
3. `tests/test_api_flow.py` na area de `web_location_match`
   - foi revisada a bateria que cobre:
     - match conhecido com boa acuracia;
     - bloqueio por `accuracy_too_low`;
     - retorno `not_in_known_location`;
     - retorno `outside_workplace`;
     - uso de matching poligonal;
     - desempate poligonal por vertice mais proximo;
   - aqui apareceu a lacuna real desta etapa:
     - havia prova de matching poligonal por intersecao/buffer;
     - faltava uma prova explicita, no endpoint Web, de que um ponto realmente interno ao poligono retorna `resolved_local` correto.

Mudanca aplicada:

1. foi alterado somente `tests/test_api_flow.py`;
2. dentro do teste existente `test_web_location_match_uses_polygon_matching_when_location_has_valid_polygon`, foi adicionada uma segunda verificacao pequena e explicita antes do cenario de borda expandida;
3. essa nova verificacao envia para `/api/web/check/location` um ponto inequivocamente interno ao poligono configurado:
   - `latitude = 1.255950`
   - `longitude = 103.611200`
   - `accuracy_meters = 8`
4. as assercoes novas exigem que o endpoint continue respondendo:
   - `matched = true`
   - `resolved_local = "Area Poligonal P80"`
   - `label = "Area Poligonal P80"`
   - `status = "matched"`
   - `accuracy_threshold_meters = 25`
5. o cenario ja existente de ponto proximo da borda com intersecao via buffer foi preservado no mesmo teste;
6. com isso, o teste passou a provar as duas coisas que interessam ao hotfix:
   - um ponto interno ao poligono continua sendo reconhecido corretamente;
   - o comportamento extra de tolerancia/expansao poligonal tambem continua coberto.

Arquivos alterados nesta etapa:

- `tests/test_api_flow.py`

Arquivos revisados e mantidos sem alteracao:

- `tests/test_location_geometry.py`
- `tests/test_location_polygon_matching.py`
- `sistema/app/services/location_matching.py`

Resultado da validacao executada:

1. comandos usados no ambiente do projeto:
   - `.\.venv\Scripts\python.exe -m pytest tests/test_location_geometry.py tests/test_location_polygon_matching.py -q`
   - `.\.venv\Scripts\python.exe -m pytest tests/test_api_flow.py -k "web_location_match" -q`
2. resultado observado:
   - `tests/test_location_geometry.py` + `tests/test_location_polygon_matching.py`: `19 passed in 2.35s`
   - recorte `web_location_match` de `tests/test_api_flow.py`: `11 passed, 303 deselected in 17.32s`

Conclusao desta etapa:

- o hotfix continua explicitamente ancorado no frontend Web automatico, nao na geometria;
- a cobertura agora prova de forma direta que ponto interno ao poligono continua retornando `resolved_local` correto no endpoint real;
- a mudanca foi minima, localizada em teste, e suficiente para impedir que alguem tente "resolver" o incidente mexendo no algoritmo errado.


## Fase 2 - Correcao principal no fluxo automatico da Web

### [x] Item 2.1 - Desativar o `check-in` automatico quando o status for `not_in_known_location`

Implementacao desta etapa concluida como correcao principal do incidente no frontend Web automatico. O objetivo aqui foi remover exatamente o caminho funcional que promovia `status = "not_in_known_location"` a `check-in` automatico, sem redesenhar a maquina de estados nem abrir escopo de API, UX ou backend.

Diagnostico aplicado no codigo antes da mudanca:

1. a funcao decisora do caminho de "proximidade" estava em `sistema/app/static/check/automatic-activities.js`, no helper `shouldAttemptAutomaticNearbyWorkplaceCheckIn(locationPayload, remoteState)`;
2. o `app.js` nao continha uma regra concorrente propria para esse caso;
3. em `sistema/app/static/check/app.js`, o controller apenas delegava a decisao para o modulo `automaticActivities` por meio do wrapper `shouldAttemptAutomaticNearbyWorkplaceCheckIn(...)`;
4. isso confirmou que o ponto certo do hotfix era a regra central do modulo compartilhado, e nao uma reescrita em `runAutomaticActivitiesIfNeeded(...)`.

Mudanca aplicada:

1. foi alterado somente `sistema/app/static/check/automatic-activities.js`;
2. dentro de `shouldAttemptAutomaticNearbyWorkplaceCheckIn(...)`, foi mantida a porta de entrada atual para identificar o caso `not_in_known_location`;
3. logo em seguida, a funcao passou a retornar `false` de forma explicita para esse estado;
4. foi adicionado comentario curto no proprio codigo deixando a intencao legivel:
   - `not_in_known_location` continua podendo informar a UI;
   - esse estado nao e mais um alvo valido para `check-in` automatico;
5. nenhuma alteracao foi necessaria em `sistema/app/static/check/app.js`, porque o controller ja consome a decisao do modulo corrigido;
6. nenhum contrato de API, payload de backend, markup, estilo ou logica poligonal foi alterado nesta etapa.

Efeito funcional obtido:

1. o ramo automatico que antes aceitava `matched = false` com `status = "not_in_known_location"` deixou de existir na pratica;
2. `runAutomaticActivitiesIfNeeded(...)` continua:
   - aceitando `matched = true` para `check-in` ou `check-out` automatico conforme as regras existentes;
   - aceitando `outside_workplace` para `check-out` automatico;
   - recusando `accuracy_too_low` para `check-in` automatico;
3. o comportamento proibido foi removido no ponto decisor, antes da construcao do submit.

Arquivos alterados nesta etapa:

- `sistema/app/static/check/automatic-activities.js`

Arquivos revisados e mantidos sem alteracao funcional:

- `sistema/app/static/check/app.js`

Resultado da validacao executada:

1. suite Web de automacao e controller:
   - comando: `node --test tests/web_automatic_activities.test.js tests/check_user_location_ui.test.js`
   - resultado: `79 pass, 0 fail`
2. suites da Fase 1 que blindam geometria e `web_location_match`:
   - comando: `.\.venv\Scripts\python.exe -m pytest tests/test_location_geometry.py tests/test_location_polygon_matching.py -q`
   - resultado: `19 passed in 1.80s`
   - comando: `.\.venv\Scripts\python.exe -m pytest tests/test_api_flow.py -k "web_location_match" -q`
   - resultado: `11 passed, 303 deselected in 11.85s`

Leitura final do diff desta etapa:

1. a mudanca foi cirurgica;
2. o hotfix foi aplicado exatamente na funcao que tomava a decisao errada;
3. a remocao do caminho automatico para `not_in_known_location` ficou explicita no codigo e comprovada pelos testes que antes falhavam e agora passam.


### [x] Item 2.2 - Endurecer a resolucao do `local` automatico para bloquear placeholders sinteticos

Implementacao desta etapa concluida como segunda linha de defesa do hotfix. Depois do corte principal do gatilho em `not_in_known_location` feito no Item 2.1, esta etapa endureceu a resolucao do `local` automatico para impedir que um placeholder diagnostico volte a ser tratado como valor operacional em um ajuste futuro.

Diagnostico aplicado antes da mudanca:

1. a funcao que resolvia o `local` automatico continuava em `sistema/app/static/check/automatic-activities.js`, no helper `resolveAutomaticCheckInLocation(locationPayload)`;
2. antes desta etapa, essa funcao ainda aceitava a cascata:
   - `resolved_local`;
   - `label`;
   - fallback sintetico `AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION`;
3. isso significava que, mesmo com o gatilho de `not_in_known_location` desligado no Item 2.1, ainda existia risco estrutural de um caminho futuro voltar a reaproveitar `label` ou o fallback sintetico como `local` de submit;
4. em `sistema/app/static/check/app.js`, o controller ainda assumia que o retorno de `resolveAutomaticCheckInLocation(...)` era submetivel e nao fazia uma verificacao propria de operacionalidade.

Mudancas aplicadas em `sistema/app/static/check/automatic-activities.js`:

1. `resolveAutomaticCheckInLocation(locationPayload)` foi endurecida para aceitar apenas `resolved_local` valido;
2. a semantica nova da funcao passou a ser:
   - retornar `resolved_local` trimado quando existir;
   - retornar `null` quando nao existir `resolved_local`;
3. com isso, `label` deixou de ser candidato a `local` automatico;
4. o fallback sintetico `AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION` deixou de ser retornado por essa funcao como valor operacional;
5. foi criado tambem um helper explicito novo:
   - `isOperationalAutomaticCheckInLocation(locationPayload, automaticLocal)`;
6. esse helper verifica se o valor candidato submetivel coincide com um `resolved_local` real e nao vazio;
7. o helper foi exportado junto com o restante do modulo para permitir reutilizacao clara e cobertura de testes dedicada.

Mudancas aplicadas em `sistema/app/static/check/app.js`:

1. foi adicionado o wrapper local `isOperationalAutomaticCheckInLocation(...)`, delegando ao modulo `automaticActivities`;
2. em `runAutomaticActivitiesIfNeeded(...)`, no ramo do `check-in` automatico por proximidade, foi incluido um guard rail adicional logo apos a resolucao de `automaticLocal`;
3. a regra nova do controller passou a ser:
   - resolver `automaticLocal`;
   - abortar o submit e retornar `noActivityResult` quando esse valor nao for operacional segundo `isOperationalAutomaticCheckInLocation(...)`;
4. esse guard protege tanto:
   - o caso real de `label` ou fallback sintetico;
   - quanto uma regressao futura em que `shouldAttemptAutomaticNearbyWorkplaceCheckIn(...)` volte a abrir indevidamente o ramo.

Tratamento dos placeholders nesta etapa:

1. `Localizacao nao Cadastrada`
   - continua existindo como texto diagnostico e constante de UI;
   - deixou de ser retornado por `resolveAutomaticCheckInLocation(...)` como `local` operacional;
   - passou a ser bloqueado novamente no controller se algum caminho regressivo tentar usa-lo;
2. `Precisao insuficiente`
   - tambem deixou de poder entrar pela rota de `label`, porque a resolucao automatica agora ignora qualquer valor sem `resolved_local`;
   - isso manteve o escopo pequeno e ao mesmo tempo eliminou placeholder equivalente sem precisar refatorar a UX.

Arquivos alterados nesta etapa:

- `sistema/app/static/check/automatic-activities.js`
- `sistema/app/static/check/app.js`
- `tests/web_automatic_activities.test.js`
- `tests/check_user_location_ui.test.js`

Cobertura adicionada/ajustada para capturar a blindagem:

1. em `tests/web_automatic_activities.test.js` foram adicionados testes de unidade para provar que:
   - `resolveAutomaticCheckInLocation(...)` devolve `Escritório Principal` quando existe `resolved_local` real;
   - `resolveAutomaticCheckInLocation(...)` devolve `null` quando o payload traz apenas `label = "Localização não Cadastrada"`;
   - `resolveAutomaticCheckInLocation(...)` devolve `null` quando o payload traz apenas `label = "Precisão insuficiente"`;
   - `isOperationalAutomaticCheckInLocation(...)` aceita apenas valor coincidente com `resolved_local` real e rejeita placeholders;
2. em `tests/check_user_location_ui.test.js` foi adicionado um teste de controller de defesa em profundidade:
   - `check controller refuses placeholder automatic locals even if the nearby-workplace gate regresses open`;
   - esse teste força artificialmente a abertura do ramo `nearby-workplace` e força `resolveAutomaticCheckInLocation()` a devolver `Localização não Cadastrada`;
   - a assercao exige que, mesmo assim, `runAutomaticActivitiesIfNeeded(...)` retorne `{ performed: false, action: null, local: null }` e nao chame `submitAutomaticActivity`.

Resultado da validacao executada:

1. suite Web de automacao e controller:
   - comando: `node --test tests/web_automatic_activities.test.js tests/check_user_location_ui.test.js`
   - resultado: `82 pass, 0 fail`
2. suites da Fase 1 mantidas como blindagem de escopo:
   - comando: `.\.venv\Scripts\python.exe -m pytest tests/test_location_geometry.py tests/test_location_polygon_matching.py -q`
   - resultado: `19 passed in 1.17s`
   - comando: `.\.venv\Scripts\python.exe -m pytest tests/test_api_flow.py -k "web_location_match" -q`
   - resultado: `11 passed, 303 deselected in 6.94s`

Conclusao desta etapa:

1. o fluxo automatico nao consegue mais construir `payload` com `local = "Localizacao nao Cadastrada"` a partir da resolucao normal;
2. mesmo se um ajuste futuro reabrir indevidamente o ramo decisor, o controller agora possui uma segunda validacao que impede submit de placeholder;
3. a UI continua livre para usar os textos diagnosticos, mas esses textos deixaram de ter semantica operacional no submit automatico.


### [x] Item 2.3 - Garantir que a aplicacao continue exibindo o estado de falha sem persisti-lo

Implementacao desta etapa concluida como ajuste de clareza semantica entre apresentacao e submit. O foco aqui nao foi mudar a tela nem a i18n de forma ampla, e sim deixar explicito no codigo que uma coisa e o texto diagnostico mostrado ao usuario e outra, diferente, e o valor operacional que pode ser enviado ao backend.

Revisao funcional realizada nesta etapa:

1. a exibicao dos estados de localizacao continua centralizada no fluxo:
   - `applyLocationMatch(payload, options)`;
   - `setLocationPresentation(label, message, tone, accuracyText, options)`;
2. nesse caminho, a UI continua apresentando normalmente os labels diagnosticos de falha:
   - `Localizacao nao Cadastrada`;
   - `Precisao insuficiente`;
   - `Fora do Local de Trabalho`;
3. o submit manual continua saindo de `resolveSubmittedLocationValue()`;
4. o submit automatico continua saindo de `runAutomaticActivitiesIfNeeded(...)`;
5. antes desta etapa, a separacao entre "label de exibicao" e "local operacional reconhecido" ja existia parcialmente na pratica, mas seguia implicita demais.

Mudancas aplicadas em `sistema/app/static/check/app.js`:

1. foi criado o helper `resolveDisplayedLocationLabel(matchPayload)`:
   - responsabilidade: resolver apenas o label exibido na UI a partir de `payload.label`;
   - esse helper usa `localizeKnownLocationLabel(...)` e deixa claro que o papel dele e exclusivamente de apresentacao;
2. foi criado o helper `resolveMatchedOperationalLocation(matchPayload)`:
   - responsabilidade: resolver apenas o `resolved_local` operacional quando o payload representa match real;
   - regra:
     - se `matched` nao for verdadeiro, retorna `null`;
     - se `resolved_local` nao existir ou vier vazio, retorna `null`;
     - se houver `resolved_local` valido, retorna esse valor trimado;
3. `setResolvedLocation(matchPayload)` foi ajustada para guardar em `currentLocationMatch` somente um payload que tenha local operacional realmente reconhecido;
4. `resolveSubmittedLocationValue()` foi ajustada para ficar semanticamente explicita:
   - no fluxo manual permitido, continua usando `manualLocationSelect.value`;
   - fora disso, passa a usar `resolveMatchedOperationalLocation(currentLocationMatch)` em vez de depender implicitamente de `currentLocationMatch.resolved_local`;
5. `applyLocationMatch(payload, options)` foi ajustada para usar `resolveDisplayedLocationLabel(payload)` ao montar a apresentacao da UI.

Efeito funcional consolidado apos a mudanca:

1. `not_in_known_location`
   - continua aparecendo ao usuario como estado diagnostico;
   - nao vira `currentLocationMatch`;
   - nao fornece `resolved_local` submetivel;
   - nao volta a alimentar automacao nem submit comum por leitura implicita do label;
2. `outside_workplace`
   - continua aparecendo ao usuario como estado diagnostico;
   - continua podendo sustentar `check-out` automatico pela regra propria desse fluxo;
   - nao vira `resolved_local` de submit manual comum;
3. `accuracy_too_low`
   - continua aparecendo ao usuario como estado diagnostico;
   - continua habilitando o fluxo manual/fallback ja existente;
   - a separacao nova deixa explicito que esse estado de tela nao entra no ramo de `currentLocationMatch`.

Arquivos alterados nesta etapa:

- `sistema/app/static/check/app.js`
- `tests/check_user_location_ui.test.js`

Cobertura adicionada e ajustada:

1. em `tests/check_user_location_ui.test.js`, o teste de leitura estrutural foi atualizado para exigir que `resolveSubmittedLocationValue()` use `resolveMatchedOperationalLocation(currentLocationMatch)` no ramo nao manual;
2. o teste `check controller resolves the submitted local from manual fallback and matched GPS states` foi ampliado para provar que:
   - `Localização não Cadastrada` nao vira `local` submetivel;
   - `Fora do Local de Trabalho` nao vira `local` submetivel;
   - um match real continua retornando `Guarita` normalmente;
3. foi adicionado o teste `check controller keeps failure labels in presentation without turning them into matched operational locations`, cobrindo:
   - `not_in_known_location`;
   - `accuracy_too_low`;
   - `outside_workplace`;
4. esse novo teste valida simultaneamente que:
   - o label continua indo para a camada de apresentacao;
   - o tom visual por status continua correto;
   - `currentLocationMatch` permanece `null` nos estados de falha;
   - `currentLocationResolutionStatus` continua preservado para a UX.

Resultado da validacao executada:

1. suite Web de automacao e controller:
   - comando: `node --test tests/web_automatic_activities.test.js tests/check_user_location_ui.test.js`
   - resultado: `83 pass, 0 fail`
2. suites da Fase 1 mantidas como blindagem de escopo:
   - comando: `.\.venv\Scripts\python.exe -m pytest tests/test_location_geometry.py tests/test_location_polygon_matching.py -q`
   - resultado: `19 passed in 1.48s`
   - comando: `.\.venv\Scripts\python.exe -m pytest tests/test_api_flow.py -k "web_location_match" -q`
   - resultado: `11 passed, 303 deselected in 11.17s`

Conclusao desta etapa:

1. a aplicacao continua exibindo ao usuario os estados diagnosticos de falha;
2. esses estados ficaram mais claramente separados de `resolved_local` e de `local` submetivel;
3. o fluxo automatico ja corrigido continua sem usar esses textos como `local`;
4. o submit manual nao passa a reaproveitar `Localizacao nao Cadastrada` nem `Fora do Local de Trabalho` por leitura implicita do label de exibicao.


## Fase 3 - Guard rails adicionais no submit da Web

### [x] Item 3.1 - Adicionar validacao de ultimo momento no frontend antes do submit

Implementacao executada nesta etapa:

1. o ponto exato de montagem final do payload foi confirmado em dois lugares do frontend Web:
   - `submitAutomaticActivity({ action, local, suppressStatus })`, que envia o submit automatico;
   - o listener principal de `form.addEventListener('submit', ...)`, que envia o submit manual/semi-manual para `submitEndpoint`;
2. a decisao da etapa foi adicionar um guard rail compartilhado e de escopo estreito no proprio `app.js`, sem depender de backend novo e sem criar heuristica ampla baseada em palavras soltas;
3. a protecao foi desenhada para bloquear apenas placeholders sinteticos de falha que ja existem no fluxo atual, preservando nomes operacionais legitimos.

Mudancas aplicadas em `sistema/app/static/check/app.js`:

1. foi adicionada `isSyntheticFailureLocationValue(local)` para centralizar a deteccao de valores que nao podem ser persistidos como `local` operacional;
2. essa validacao foi mantida propositalmente estreita e explicita:
   - bloqueia `automaticActivities.AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION`, isto e, o placeholder de `Localizacao nao Cadastrada`;
   - bloqueia `accuracyFallbackManualLocationLabel`, isto e, o placeholder de `Precisao Insuficiente`;
   - nao tenta inferir por substring, prefixo ou heuristica aberta se um nome real de localizacao seria invalido;
3. foi adicionada `resolveFinalSubmittableLocationValue(local)` como ultima etapa de normalizacao antes do envio:
   - faz `trim`;
   - retorna `null` quando o valor vier vazio;
   - retorna `null` quando o valor vier como placeholder sintetico de falha;
   - retorna o texto normalizado quando o valor for operacional;
4. `submitAutomaticActivity(...)` foi alterada para usar essa resolucao final antes de `fetch(submitEndpoint, ...)`;
5. quando `resolveFinalSubmittableLocationValue(local)` retorna `null`, `submitAutomaticActivity(...)` agora aborta silenciosamente o envio e retorna `null`, impedindo que o payload Web seja emitido com `local` invalido;
6. o corpo do request automatico passou a usar `submittedLocal` em vez do valor bruto recebido pelo chamador, garantindo que o payload enviado ao backend sempre passe pela validacao final;
7. `runAutomaticActivitiesIfNeeded(...)` foi ajustada para tratar esse aborto explicitamente:
   - se `submitAutomaticActivity(...)` retornar `null`, o resultado volta a ser `noActivityResult`;
   - isso evita reportar uma automacao como executada quando o guard rail bloqueou o envio no ultimo momento;
8. o listener de submit manual do formulario tambem passou a aplicar o mesmo guard rail imediatamente antes do `fetch(submitEndpoint, ...)`;
9. no submit manual:
   - o codigo resolve `submittedLocal` a partir de `resolveSubmittedLocationValue()`;
   - aplica `resolveFinalSubmittableLocationValue(...)`;
   - se o resultado for `null`, aborta o envio antes do request;
   - reaproveita a mensagem de erro de selecao de local e devolve foco ao seletor manual quando esse seletor estiver habilitado;
10. o endpoint, o contrato de payload e o comportamento visual geral foram preservados; a mudanca ficou restrita ao emissor Web.

Garantias funcionais obtidas com essa camada final:

1. mesmo que algum fluxo interno futuro volte a montar `Localizacao nao Cadastrada` como candidato a `local`, o payload final nao e enviado;
2. `Precisao Insuficiente` tambem deixa de ser persistivel como `local`, reforcando a regra para outro placeholder sintetico que tambem nao representa local operacional;
3. locais operacionais validos continuam aptos ao submit, inclusive:
   - `Escritorio Principal`;
   - `Zona de CheckOut`;
   - `Zona Mista`;
   - `Fora do Local de Trabalho`;
   - qualquer `resolved_local` real vindo do matching;
4. o submit manual de local cadastrado continua permitido quando o usuario seleciona explicitamente um valor operacional valido;
5. a protecao continua frontend-only e nao cria efeito colateral em mobile nem em outros canais.

Arquivos alterados nesta etapa:

- `sistema/app/static/check/app.js`
- `tests/check_user_location_ui.test.js`

Cobertura adicionada e ajustada:

1. em `tests/check_user_location_ui.test.js`, o harness de leitura de submit foi atualizado para expor tambem `resolveFinalSubmittableLocationValue(...)`, permitindo testar a camada final em conjunto com `resolveSubmittedLocationValue()`;
2. o teste `check controller resolves the submitted local from manual fallback and matched GPS states` foi ampliado para provar que:
   - `Precisao Insuficiente` resolve para `null` na ultima camada submetivel;
   - `Localização não Cadastrada` resolve para `null` na ultima camada submetivel;
   - `Portaria`, `Fora do Local de Trabalho` e `Guarita` continuam elegiveis quando operacionais;
3. foi criado um harness especifico para `submitAutomaticActivity(...)`, isolando a montagem final do payload automatico sem criar harness paralelo fora da trilha real do controller;
4. foi adicionado o teste `check controller blocks placeholder locals at final automatic submit assembly without calling fetch`, que prova que:
   - `submitAutomaticActivity(...)` retorna `null` para `Localização não Cadastrada`;
   - `fetch` nao e chamado;
   - `applyHistoryState` nao e chamado;
   - `setStatus` nao e chamado;
5. foi adicionado o teste `check controller keeps valid automatic submit locals eligible at final payload assembly`, que prova que:
   - um valor operacional valido como `Fora do Local de Trabalho` continua sendo enviado;
   - o payload final usa o `local` validado;
   - o estado retornado pelo backend continua sendo aplicado normalmente;
6. a assercao estrutural do arquivo tambem foi atualizada para exigir que o submit manual passe por `resolveFinalSubmittableLocationValue(resolveSubmittedLocationValue())` antes do `fetch`.

Resultado da validacao executada:

1. suite Web de controller e automacao:
   - comando: `node --test tests/web_automatic_activities.test.js tests/check_user_location_ui.test.js`
   - resultado: `85 pass, 0 fail`
2. suites de geometria/poligono mantidas como blindagem de escopo:
   - comando: `.\.venv\Scripts\python.exe -m pytest tests/test_location_geometry.py tests/test_location_polygon_matching.py -q`
   - resultado: `19 passed in 2.11s`
3. recorte de integracao backend usado para confirmar que o matching Web nao foi impactado:
   - comando: `.\.venv\Scripts\python.exe -m pytest tests/test_api_flow.py -k "web_location_match" -q`
   - resultado: `11 passed, 303 deselected in 12.79s`

Conclusao desta etapa:

1. o frontend Web agora tem uma validacao de ultimo momento imediatamente antes do submit automatico e do submit manual;
2. essa validacao bloqueia a persistencia de placeholders sinteticos sem alterar a UX diagnostica ja existente;
3. a regra ficou estreita o suficiente para nao barrar locais operacionais legitimos;
4. o hotfix ganhou uma camada extra de `defense in depth` no proprio emissor, mesmo se algum fluxo interno voltar a reconstruir um `local` invalido no futuro.


### [x] Item 3.2 - Avaliar e, somente se seguro, adicionar guard rail opcional no backend Web

Implementacao desta etapa concluida com decisao favoravel ao guard rail server-side, mas apenas porque a analise mostrou um ponto de aplicacao suficientemente estreito e de baixo risco: o proprio endpoint `/api/web/check`.

Analise de contrato e de risco realizada antes da mudanca:

1. `submit_web_check()` em `sistema/app/routers/web_check.py` recebe `WebCheckSubmitRequest`, valida a sessao Web autenticada, valida o projeto ativo do usuario e depois repassa `payload.local` para `submit_forms_event(...)`;
2. `WebCheckSubmitRequest` herda de `MobileFormsSubmitRequest`, e `submit_forms_event(...)` e um servico compartilhado entre canais;
3. isso significa que qualquer bloqueio colocado no schema-base ou no servico compartilhado teria risco real de afetar outros emissores alem da Web;
4. os dados historicos e o proprio plano desta correcao ja registravam que `Localizacao nao Cadastrada` apareceu tambem fora da Web, inclusive no canal `mobile`;
5. por isso, a conclusao da analise foi:
   - bloquear genericamente em `schemas.py` seria amplo demais;
   - bloquear genericamente em `submit_forms_event(...)` seria amplo demais;
   - bloquear apenas em `submit_web_check()` era a unica forma de ganhar `defense in depth` sem abrir regressao intercanal.

Decisao tecnica tomada:

1. implementar o guard rail no backend Web;
2. limitar a regra ao endpoint `/api/web/check`;
3. bloquear apenas o placeholder exato do incidente, `Localização não Cadastrada`;
4. nao expandir a regra para `mobile`, `provider`, schemas compartilhados ou servicos comuns;
5. nao bloquear `Precisao Insuficiente` nesta etapa, porque:
   - esse nao foi o valor confirmado como causa raiz do incidente;
   - existe cobertura historica especifica no backend aceitando esse valor no submit Web;
   - aumentar a lista de proibicoes no backend nesta fase ampliaria o escopo alem do necessario.

Mudancas aplicadas em `sistema/app/routers/web_check.py`:

1. foi introduzido `WEB_NON_OPERATIONAL_SUBMIT_LOCALS` como conjunto explicito de valores nao operacionais rejeitados pelo endpoint Web;
2. neste hotfix, o conjunto contem apenas `Localização não Cadastrada`;
3. foi adicionada `_reject_non_operational_web_submit_local(local)`, responsavel por:
   - normalizar whitespace do valor recebido;
   - verificar se ele esta no conjunto de placeholders proibidos para submit Web;
   - levantar `HTTPException(status_code=422)` com mensagem clara quando o valor nao for operacional;
4. `submit_web_check()` agora chama `_reject_non_operational_web_submit_local(payload.local)` depois da validacao de autenticacao/sessao e do escopo de projeto, mas antes de qualquer chamada a `submit_forms_event(...)`;
5. com isso, a rejeicao ocorre antes de qualquer side effect em:
   - `forms_submissions`;
   - `user_sync_events`;
   - `user.local`;
   - historico de presenca derivado do submit.

Por que a implementacao foi considerada segura para este hotfix:

1. o endpoint ja e Web-only por natureza:
   - prefixo `/api/web`;
   - sessao autenticada via password Web;
   - `WEB_CHECK_CHANNEL` dedicado;
2. a regra ficou delimitada ao valor exato do incidente em vez de usar heuristica aberta por substring ou padrao;
3. o mobile continua fora do escopo porque nao passa por `submit_web_check()`;
4. `submit_forms_event(...)` e `MobileFormsSubmitRequest` permaneceram intactos, evitando arrastar alteracoes estruturais para os outros canais;
5. o frontend ja tinha sido corrigido nas etapas anteriores, entao este backend guard rail entra apenas como camada complementar de `defense in depth`.

Arquivos alterados nesta etapa:

- `sistema/app/routers/web_check.py`
- `tests/test_api_flow.py`

Cobertura adicionada e preservada:

1. foi adicionado `test_web_check_rejects_unregistered_location_placeholder_for_web_submit`, cobrindo o caso exato do incidente no backend Web;
2. esse teste prova que, ao receber `local = "Localização não Cadastrada"` em `/api/web/check`, o backend:
   - responde `422`;
   - devolve mensagem clara de local nao operacional para submit Web;
   - nao grava `FormsSubmission`;
   - nao grava `UserSyncEvent` com `source = "web_forms"`;
   - nao atualiza `user.local`;
3. foi mantido o teste existente `test_web_check_accepts_synthetic_accuracy_fallback_local`, que continua passando e prova que a mudanca nao virou um bloqueio amplo contra qualquer valor sintetico;
4. com isso, a suite deixa explicito que:
   - o bloqueio e cirurgico para o placeholder do incidente;
   - o contrato historico do backend para outros valores nao foi quebrado sem necessidade.

Resultado da validacao executada:

1. recorte backend diretamente ligado ao guard rail e ao matching Web:
   - comando: `.\.venv\Scripts\python.exe -m pytest tests/test_api_flow.py -k "web_check_rejects_unregistered_location_placeholder_for_web_submit or web_check_accepts_synthetic_accuracy_fallback_local or web_location_match" -q`
   - resultado: `13 passed, 302 deselected in 16.36s`
2. suite frontend relevante do hotfix, rerrodada como blindagem do comportamento ja corrigido no emissor:
   - comando: `node --test tests/web_automatic_activities.test.js tests/check_user_location_ui.test.js`
   - resultado: `85 pass, 0 fail`

Conclusao desta etapa:

1. a avaliacao concluiu que o frontend-only ja era suficiente para corrigir o incidente, mas que um guard rail backend adicional tambem era seguro desde que ficasse restrito ao endpoint Web;
2. por isso, o hotfix passou a ter uma ultima barreira server-side contra `Localização não Cadastrada` sem tocar mobile nem os componentes compartilhados;
3. a implementacao ficou deliberadamente estreita para evitar transformar este ajuste em refactor amplo de validacao;
4. o backend agora rejeita o placeholder do incidente apenas quando ele entra pelo canal Web, reforcando o patch sem criar efeito colateral intercanal.


## Fase 4 - Validacao completa do hotfix no workspace

### [x] Item 4.1 - Executar a bateria de testes automatizados do hotfix e registrar o resultado

Execucao desta etapa concluida como validacao automatizada consolidada do hotfix. O objetivo aqui foi sair da validacao incremental das fases anteriores e fechar uma bateria unica, rastreavel e suficiente para o escopo real da correcao antes da homologacao manual da Fase 4.2.

Critério adotado para montar a bateria:

1. incluir obrigatoriamente os testes que sustentam os quatro eixos tocados pelo hotfix:
   - matching geometrico/poligonal;
   - API Web de localizacao (`/api/web/check/location`);
   - API Web de submit (`/api/web/check`) nos cenarios diretamente afetados;
   - automacao Web no frontend e seus guard rails finais;
2. evitar anunciar como “bateria do hotfix” a suite total do repositorio, porque isso incluiria modulos fora do incidente:
   - transporte;
   - admin em areas nao relacionadas;
   - mobile fora do contrato Web;
   - outras trilhas sem relacao causal com `Localizacao nao Cadastrada`.

Comandos efetivamente executados nesta etapa:

1. geometria e matching poligonal:
   - `.\.venv\Scripts\python.exe -m pytest tests/test_location_geometry.py tests/test_location_polygon_matching.py -q`
2. API Web de localizacao e submit no recorte relevante do hotfix:
   - `.\.venv\Scripts\python.exe -m pytest tests/test_api_flow.py -k "web_location_match or web_check_updates_user_local_when_location_is_provided or web_check_rejects_unregistered_location_placeholder_for_web_submit or web_check_accepts_synthetic_accuracy_fallback_local" -q`
3. automacao Web e controller do frontend:
   - `node --test tests/web_automatic_activities.test.js tests/check_user_location_ui.test.js`

Resultados observados:

1. geometria e poligonos:
   - resultado: `19 passed in 2.46s`
   - esse recorte confirma que o hotfix nao mexeu nem degradou:
     - geometria basica;
     - matching poligonal;
     - regras de ponto interno e comportamento associado;
2. API Web de localizacao e submit:
   - resultado: `14 passed, 301 deselected in 16.43s`
   - o recorte cobre explicitamente:
     - toda a familia `web_location_match`;
     - submit Web valido com local reconhecido;
     - rejeicao backend de `Localização não Cadastrada` no canal Web;
     - preservacao do contrato historico que ainda aceita `Precisao Insuficiente` no backend Web;
3. automacao Web e guard rails do frontend:
   - resultado: `85 pass, 0 fail`
   - esse recorte inclui:
     - regressao de `not_in_known_location` sem `check-in` automatico;
     - preservacao de `matched` e `outside_workplace`;
     - bloqueio final de placeholders sinteticos no submit automatico;
     - separacao entre label de UI e `local` operacional no controller.

Confirmacao explicita da regressao criada:

1. a regressao aberta nas Fases 1 e 2 foi executada dentro da suite Node acima;
2. isso inclui os cenarios que provam que:
   - `Localização não Cadastrada` nao volta a acionar `check-in` automatico;
   - `Localização não Cadastrada` nao volta a ser montada como `local` submetivel;
   - o submit automatico e o submit final do controller abortam quando recebem placeholder sintetico;
3. como toda a suite relevante passou, nao houve necessidade de correcao adicional antes de seguir para homologacao manual.

Por que o recorte executado foi considerado suficiente para este hotfix:

1. o hotfix nao alterou schema, migration, CRUD geral de localizacoes ou algoritmo poligonal;
2. as mudancas reais ficaram concentradas em:
   - `sistema/app/static/check/automatic-activities.js`;
   - `sistema/app/static/check/app.js`;
   - `sistema/app/routers/web_check.py`;
   - `tests` diretamente ligados a essas trilhas;
3. por isso, a evidencia tecnicamente suficiente e a que cobre:
   - matching/localizacao;
   - submit Web;
   - automacao Web;
   - persistencia proibida do placeholder do incidente.

Limitacoes residuais registradas:

1. a suite total do repositorio nao foi executada nesta etapa;
2. isso foi uma escolha deliberada de escopo, nao uma falha de execucao;
3. o motivo e que a Fase 4.1 pede a bateria relevante do hotfix, e nao uma certificacao global de todo o sistema;
4. areas nao exercitadas aqui continuam dependendo de suas proprias suites e nao fazem parte da evidência minima desta correcao;
5. a homologacao manual/preview ainda permanece pendente para a Fase 4.2.

Conclusao desta etapa:

1. a bateria automatizada relevante do hotfix foi executada por completo;
2. todos os recortes obrigatorios passaram:
   - `19 passed` em geometria/poligono;
   - `14 passed` no recorte de API Web;
   - `85 pass, 0 fail` na automacao Web/frontend;
3. a regressao criada contra a persistencia de `Localizacao nao Cadastrada` foi efetivamente rodada e aprovada;
4. o workspace ficou tecnicamente apto para seguir para homologacao manual dirigida na proxima etapa.


### [x] Item 4.2 - Homologar em banco/preview com cenarios dirigidos

Homologacao dirigida executada no ambiente efetivamente disponivel no workspace: banco local de teste usado pela stack de `pytest` (`test_checking.db`) combinado com os harnesses reutilizaveis do controller Web em `tests/check_user_location_ui.test.js`. O workspace nao expunha um preview browser separado pronto para uso, entao a validacao funcional foi montada na trilha mais proxima do uso real que estava imediatamente acessivel sem tocar em dados de producao:

1. `FastAPI TestClient` para os cenarios de `/api/web/check/location`;
2. harnesses reais do controller Web para os cenarios de automacao e apresentacao da UI;
3. recorte pequeno e dirigido, sem expandir para uma suite e2e extensa.

Comandos executados para esta homologacao:

1. API Web de localizacao, cobrindo os quatro estados dirigidos:
   - `.\.venv\Scripts\python.exe -m pytest tests/test_api_flow.py -k "test_web_location_match_returns_known_location_when_accuracy_is_good or test_web_location_match_returns_unregistered_location_without_message_within_two_km or test_web_location_match_returns_outside_workplace_without_message or test_web_location_match_blocks_low_accuracy_before_matching" -q`
   - resultado: `4 passed, 311 deselected in 9.34s`
2. controller Web reaproveitado como harness de homologacao funcional:
   - `node --test tests/check_user_location_ui.test.js --test-name-pattern "check controller keeps failure labels in presentation without turning them into matched operational locations|manual refresh should submit automatic check-in after checkout when leaving checkout zone for a known location|manual refresh should not submit automatic check-in for a nearby unregistered location after checkout|check controller keeps outside_workplace forcing automatic checkout after a mixed-zone check-in|check controller does not submit automatic check-in when accuracy is too low after checkout"`
   - resultado observado pelo runner: `61 pass, 0 fail`
   - dentro desse recorte passaram os cenarios de homologacao focados abaixo, apoiados pelo mesmo arquivo/harness do controller.

Resumo por cenario homologado:

1. cenario: usuario dentro do poligono de `Escritorio Principal` com precisao boa
   - setup usado:
     - API: `test_web_location_match_returns_known_location_when_accuracy_is_good`
     - cria localizacao poligonal `Web Match P80`;
     - configura threshold de precisao em `25m`;
     - envia ponto interno ao poligono com `accuracy_meters = 8`;
     - controller: `manual refresh should submit automatic check-in after checkout when leaving checkout zone for a known location`
     - simula estado remoto elegivel a automacao e payload com `matched = true`, `resolved_local = "Escritório Principal"` e `status = "matched"`;
   - comportamento observado:
     - a API respondeu `matched = true`, `resolved_local = "Web Match P80"`, `label = "Web Match P80"` e `status = "matched"`;
     - o controller, na trilha de refresh/manual lifecycle, chamou `submitAutomaticActivity` com `action = "checkin"` e `local = "Escritório Principal"`;
   - esperado vs observado:
     - esperado: local reconhecido corretamente e automacao valida com local real;
     - observado: exatamente alinhado ao esperado.

2. cenario: usuario em local nao reconhecido, sem caracterizar `outside_workplace`
   - setup usado:
     - API: `test_web_location_match_returns_unregistered_location_without_message_within_two_km`
     - cria localizacao conhecida em `P80`;
     - envia ponto fora do poligono, mas ainda a menos de `2km` da localizacao conhecida;
     - controller: `manual refresh should not submit automatic check-in for a nearby unregistered location after checkout`
     - payload com `matched = false`, `status = "not_in_known_location"`, `label = "Localização não Cadastrada"` e `nearest_workplace_distance_meters = 180`;
     - apresentacao de UI: `check controller keeps failure labels in presentation without turning them into matched operational locations`;
   - comportamento observado:
     - a API respondeu `matched = false`, `resolved_local = null`, `label = "Localização não Cadastrada"`, `status = "not_in_known_location"` e `message = ""`;
     - a camada de apresentacao continuou exibindo o label da falha, com `currentLocationMatch = null` e `currentLocationResolutionStatus = "not_in_known_location"`;
     - o controller buscou o estado remoto, mas nao chamou `submitAutomaticActivity`;
   - esperado vs observado:
     - esperado: a UI pode informar `Localizacao nao Cadastrada`, mas nao deve haver submit automatico com esse valor;
     - observado: exatamente alinhado ao esperado.

3. cenario: usuario em `outside_workplace`
   - setup usado:
     - API: `test_web_location_match_returns_outside_workplace_without_message`
     - cria localizacao conhecida em `P80`;
     - envia ponto suficientemente distante para ultrapassar o threshold de checkout;
     - controller: `check controller keeps outside_workplace forcing automatic checkout after a mixed-zone check-in`
     - simula estado remoto com ultimo estado em `Zona Mista` e payload com `matched = false`, `status = "outside_workplace"` e `minimum_checkout_distance_meters = 2500`;
     - apresentacao de UI: `check controller keeps failure labels in presentation without turning them into matched operational locations`;
   - comportamento observado:
     - a API respondeu `matched = false`, `resolved_local = null`, `label = "Fora do Ambiente de Trabalho"` e `status = "outside_workplace"`;
     - o controller interpretou corretamente esse estado como elegivel para `check-out` automatico e chamou `submitAutomaticActivity` com `action = "checkout"` e `local = "Fora do Local de Trabalho"`;
     - a apresentacao de UI continuou separada do `local` operacional;
   - esperado vs observado:
     - esperado: `outside_workplace` continua permitindo `check-out` automatico quando a regra se aplica;
     - observado: exatamente alinhado ao esperado, inclusive mantendo a separacao entre label diagnostico de API e `local` operacional de checkout.

4. cenario: usuario com `accuracy_too_low`
   - setup usado:
     - API: `test_web_location_match_blocks_low_accuracy_before_matching`
     - cria localizacao conhecida em `P80`;
     - configura threshold de precisao em `15m`;
     - envia ponto com `accuracy_meters = 44`;
     - controller: `check controller does not submit automatic check-in when accuracy is too low after checkout`
     - payload com `matched = false`, `status = "accuracy_too_low"`, `label = "Precisão insuficiente"` e `resolved_local = null`;
     - apresentacao de UI: `check controller keeps failure labels in presentation without turning them into matched operational locations`;
   - comportamento observado:
     - a API respondeu `matched = false`, `resolved_local = null`, `label = "Precisao insuficiente"` e `status = "accuracy_too_low"`;
     - a apresentacao manteve o estado de falha em tom de aviso sem criar `currentLocationMatch`;
     - o controller buscou o estado remoto, mas nao chamou `submitAutomaticActivity`;
   - esperado vs observado:
     - esperado: nao deve ocorrer `check-in` automatico;
     - observado: exatamente alinhado ao esperado.

Observacoes operacionais da homologacao:

1. nenhum dado de producao foi alterado;
2. a validacao foi propositalmente curta e dirigida, sem virar suite e2e ampla;
3. a homologacao reutilizou infraestrutura ja existente no repositorio em vez de montar harness paralelo:
   - `TestClient` e banco local de teste para a API;
   - `createManualRefreshAutomaticActivityHarness()` e `createLocationMatchPresentationHarness()` no controller Web;
4. o cenario 2 confirmou o efeito funcional central do hotfix:
   - `Localizacao nao Cadastrada` continua existindo como estado de interface;
   - nao vira submit automatico;
   - nao volta a ser tratada como `local` operacional pela trilha principal da Web.

Conclusao desta etapa:

1. os quatro cenarios obrigatorios foram homologados com resultado aderente ao esperado;
2. o comportamento observado confirma que o hotfix removeu a persistencia indevida sem quebrar:
   - reconhecimento de local valido;
   - `check-out` automatico por `outside_workplace`;
   - tratamento de `accuracy_too_low`;
3. o workspace ficou apto para seguir para a preparacao final de rollout do hotfix.


## Fase 5 - Preparacao para rollout futuro

### [x] Item 5.1 - Preparar o pacote final de codigo como hotfix de diff minimo

Revisao final do pacote concluida com foco em rollout futuro. O resultado principal desta etapa foi separar com clareza:

1. o que faz parte do hotfix do incidente;
2. o que existe como drift amplo do workspace e nao deve ser levado junto por acidente.

Inspecao executada nesta etapa:

1. revisao de `git status --short` para mapear o estado real do workspace;
2. revisao de `git diff --stat` do repositorio inteiro para medir o risco de merge amplo;
3. revisao orientada dos arquivos realmente ligados ao hotfix:
   - `sistema/app/static/check/automatic-activities.js`
   - `sistema/app/static/check/app.js`
   - `sistema/app/routers/web_check.py`
   - `tests/web_automatic_activities.test.js`
   - `tests/check_user_location_ui.test.js`
   - `tests/test_api_flow.py`
4. verificacao explicita dos caminhos que nao deveriam entrar no pacote:
   - migrations em `alembic/versions/`;
   - `sistema/app/services/location_matching.py`;
   - CRUD/servicos amplos de localizacao;
   - camadas de multi-projeto e membership fora do estritamente necessario;
   - arquivos de admin, transport e outras trilhas do workspace.

Diagnostico operacional do diff atual do workspace:

1. o workspace como um todo esta muito maior do que o hotfix:
   - ha alteracoes extensas em admin, transport, docs, static assets, schemas e outros servicos;
   - existem migrations novas no workspace;
   - existem trilhas grandes de memberships/multi-projeto em paralelo;
2. isso confirma que o rollout futuro nao deve ser feito por merge amplo da branch/workspace atual;
3. a forma segura de empacotar este hotfix continua sendo:
   - `cherry-pick` de commits/hunks minimos; ou
   - reaplicacao manual dos trechos do hotfix em uma branch mais proxima da producao.

Arquivos que compoem o hotfix de codigo:

1. `sistema/app/static/check/automatic-activities.js`
   - razao:
     - remove o `check-in` automatico para `status = "not_in_known_location"`;
     - endurece `resolveAutomaticCheckInLocation(...)`;
     - adiciona a verificacao de local operacional antes de considerar submit automatico;
   - este arquivo e o nucleo funcional minimo do incidente no lado da automacao Web.
2. `sistema/app/static/check/app.js`
   - razao:
     - separa melhor `display label` de `local` operacional;
     - adiciona validacao final de `local` antes do submit automatico e do submit manual;
     - impede que placeholders sinteticos cheguem ao `fetch(submitEndpoint, ...)`;
   - este arquivo e a segunda camada obrigatoria do hotfix no frontend Web.
3. `sistema/app/routers/web_check.py`
   - razao:
     - implementa guard rail backend opcional e de baixo risco;
     - rejeita `Localização não Cadastrada` apenas no endpoint Web `/api/web/check`;
   - observacao importante:
     - o arquivo do workspace carrega tambem drift amplo de memberships/multi-projeto;
     - portanto, para rollout, deve entrar apenas o hunk do guard rail, nao o arquivo inteiro.
4. `tests/web_automatic_activities.test.js`
   - razao:
     - congela a politica de automacao para `matched`, `outside_workplace`, `not_in_known_location` e `accuracy_too_low`;
     - prova que o caminho automatico proibido nao reabre.
5. `tests/check_user_location_ui.test.js`
   - razao:
     - cobre a trilha real do controller Web;
     - prova a nao persistencia de placeholders no submit automatico e no submit final;
     - prova a separacao entre label de UI e `local` operacional.
6. `tests/test_api_flow.py`
   - razao:
     - cobre o contrato de `/api/web/check/location`;
     - cobre a rejeicao backend de `Localização não Cadastrada` no canal Web;
     - cobre a preservacao do submit valido e do contrato historico necessario.

Arquivos revisados e confirmados como fora do hotfix minimo:

1. `sistema/app/services/location_matching.py`
   - nenhuma alteracao entrou;
   - o algoritmo poligonal continua fora do pacote.
2. migrations em `alembic/versions/`
   - existem no workspace, mas nao pertencem a esta correcao;
   - devem ficar fora do rollout do hotfix.
3. `sistema/app/models.py`, `sistema/app/schemas.py`, `sistema/app/services/managed_locations.py`, `sistema/app/services/user_projects.py`
   - ha drift do workspace nessas areas;
   - nao sao necessarios para corrigir o incidente;
   - devem ficar fora do pacote de producao deste hotfix.
4. CRUD de localizacoes, thresholds e catalogo
   - nenhuma mudanca funcional dessas areas e necessaria para o incidente;
   - devem permanecer fora do rollout.
5. admin, transport, mobile e demais assets/docs do workspace
   - explicitamente fora do escopo do patch.

Reducao do diff e decisao final de empacotamento:

1. nao foi identificada necessidade de reduzir mais os hunks do hotfix em `automatic-activities.js` e `app.js`;
2. o que estava maior do que o necessario nao era o hotfix em si, e sim o estado geral do workspace;
3. por isso, a reducao correta para rollout nao e reescrever novamente os arquivos do hotfix, e sim limitar o pacote enviado a producao aos trechos abaixo:
   - frontend obrigatorio:
     - hunk de `shouldAttemptAutomaticNearbyWorkplaceCheckIn(...)` em `automatic-activities.js`;
     - hunk de `resolveAutomaticCheckInLocation(...)` e `isOperationalAutomaticCheckInLocation(...)` em `automatic-activities.js`;
     - hunk de `submitAutomaticActivity(...)`, `runAutomaticActivitiesIfNeeded(...)`, `resolveDisplayedLocationLabel(...)`, `resolveMatchedOperationalLocation(...)`, `resolveSubmittedLocationValue(...)`, `isSyntheticFailureLocationValue(...)`, `resolveFinalSubmittableLocationValue(...)` e listener de submit em `app.js`;
   - backend opcional de baixo risco:
     - `WEB_NON_OPERATIONAL_SUBMIT_LOCALS`;
     - `_reject_non_operational_web_submit_local(local)`;
     - chamada dessa validacao dentro de `submit_web_check()`;
   - testes de suporte correspondentes.

Resumo final do diff recomendado para o hotfix:

1. pacote minimo obrigatorio de codigo:
   - `sistema/app/static/check/automatic-activities.js`
   - `sistema/app/static/check/app.js`
   - `tests/web_automatic_activities.test.js`
   - `tests/check_user_location_ui.test.js`
2. extensao opcional de `defense in depth`:
   - hunk pequeno em `sistema/app/routers/web_check.py`
   - hunk de teste correspondente em `tests/test_api_flow.py`
3. documentacao de acompanhamento:
   - `docs/temp_002_todo.md` fica apenas como rastreabilidade do trabalho, nao como parte do pacote de deploy.

Por que o pacote continua sendo hotfix minimo:

1. a causa raiz corrigida continua concentrada no fluxo automatico da Web;
2. a geometria poligonal nao foi alterada;
3. nao ha migration nem mudanca de schema obrigatoria;
4. nao ha mudanca de CRUD de localizacoes;
5. nao ha dependencia de rollout de multi-projeto para a correcao funcional principal;
6. o unico ponto backend aprovado ficou isolado no endpoint Web e pode ser levado como hunk pequeno, sem contaminar o pacote com o resto do drift do arquivo;
7. a recomendacao operacional final permanece:
   - preparar o rollout por `cherry-pick`/patch minimo em branch proxima da producao;
   - nao promover o workspace inteiro como se ele fosse o hotfix.


### [x] Item 5.2 - Escrever checklist de validacao pos-deploy para producao

Implementacao desta etapa concluida como material operacional curto para as primeiras horas apos o deploy. O foco foi transformar a investigacao do incidente em uma verificacao reproduzivel, sem virar runbook longo e sem depender de contexto tacito de quem acompanhou toda a analise.

Base usada para montar a checklist:

1. o plano em `docs/temp_002.md`, especialmente a janela de validacao apos deploy e o criterio de sucesso em producao;
2. o diagnostico ja congelado no `todo`, que confirmou:
   - a causa raiz no fluxo automatico Web;
   - a manutencao de `Localizacao nao Cadastrada` apenas como estado informativo;
   - a necessidade de preservar eventos normais em locais reais e o `check-out` automatico.

Checklist operacional proposta para producao:

1. marcar o horario exato do deploy e usar esse timestamp como corte da verificacao inicial
   - usar como janela minima de observacao as primeiras `1` a `3` horas apos o deploy;
   - toda consulta deve considerar apenas registros novos apos esse marco;
   - objetivo: nao misturar ruido historico com comportamento do patch.
2. verificar novos registros Web em `check_events.local`
   - filtrar eventos do canal Web, preferencialmente por `request_path = "/api/web/check"` e/ou criterio operacional equivalente disponivel no ambiente;
   - confirmar que continuam surgindo eventos novos apos o deploy;
   - observar os valores de `local` que aparecerem nessa janela;
   - esperado: surgirem apenas valores operacionais validos ou esperados pela regra atual.
3. verificar novos registros Web em `forms_submissions.local`
   - filtrar submissões originadas da Web na mesma janela pos-deploy;
   - confirmar que a fila/gravacao continua recebendo eventos Web normais;
   - observar os valores de `local` que efetivamente foram persistidos;
   - esperado: persistencia apenas de locais operacionais validos.
4. confirmar ausencia de novos eventos Web com `Localizacao nao Cadastrada`
   - fazer a busca explicitamente em:
     - `check_events.local`;
     - `forms_submissions.local`;
   - considerar apenas registros novos apos o deploy;
   - esperado: zero novos casos Web com `local = "Localizacao nao Cadastrada"`.
5. confirmar continuidade de eventos normais em locais reais
   - procurar evidencias de continuidade em pelo menos estes valores:
     - `Escritorio Principal`;
     - `Zona de CheckOut`;
     - `Fora do Local de Trabalho`;
     - pelo menos mais um local operacional real usado pela operacao do projeto monitorado;
   - objetivo: provar que o patch nao “silenciou” a automacao valida nem quebrou o submit normal.
6. verificar se o comportamento operacional parece equilibrado, e nao apenas “sem placeholder”
   - se houver novos eventos Web, verificar se eles ainda se distribuem entre:
     - matches reais reconhecidos;
     - `check-out` automatico quando cabivel;
     - submits manuais legitimos quando o fluxo exigir;
   - objetivo: evitar interpretar ausencia de `Localizacao nao Cadastrada` como sucesso se a Web tiver parado de registrar eventos.
7. verificar rapidamente sinais de erro de submit ou regressao perceptivel
   - se o ambiente tiver log/apm/painel de erro, procurar aumento anormal de:
     - `422` inesperado em `/api/web/check`;
     - falhas de submit Web;
     - queda brusca no volume de eventos Web;
   - objetivo: diferenciar “placeholder bloqueado com sucesso” de “submit Web degradado”.

Leitura rapida de resultado nas primeiras horas:

1. considerar **sucesso inicial** quando, simultaneamente:
   - houver novos registros Web apos o deploy;
   - nao houver novos casos Web com `Localizacao nao Cadastrada`;
   - continuarem aparecendo locais reais como `Escritorio Principal`, `Zona de CheckOut`, `Fora do Local de Trabalho` e pelo menos mais um local operacional real;
   - nao houver aumento anormal de erros de submit ou sinais de quebra de UX.
2. considerar **alerta para investigacao imediata** quando ocorrer qualquer um dos pontos abaixo:
   - aparecer ao menos um novo evento Web com `Localizacao nao Cadastrada`;
   - desaparecer totalmente o fluxo Web novo sem justificativa operacional;
   - deixarem de aparecer locais reais que antes surgiam normalmente, sugerindo regressao ampla da automacao ou do submit;
   - crescerem erros de submit Web logo apos o deploy.
3. considerar **rollback candidate** quando houver evidencias consistentes de uma das situacoes abaixo:
   - novos registros Web continuam persistindo `Localizacao nao Cadastrada`;
   - eventos Web deixam de ser gerados em volume material, indicando que o patch bloqueou mais do que deveria;
   - `check-out` automatico por `Fora do Local de Trabalho` ou fluxos normais em locais reais deixam de acontecer e isso se repete apos rechecagem;
   - o ambiente apresenta aumento claro de falhas operacionais de submit relacionadas ao patch.

Forma recomendada de uso desta checklist:

1. executar a checagem uma primeira vez logo apos o deploy estabilizar;
2. repetir ao menos uma segunda leitura dentro da mesma janela inicial;
3. registrar em um comentario curto ou ticket operacional:
   - horario da leitura;
   - volume aproximado de registros Web vistos;
   - presenca ou ausencia de `Localizacao nao Cadastrada`;
   - exemplos de locais reais observados;
   - decisao do momento: `sucesso inicial`, `monitorar`, ou `rollback candidate`.

Conclusao desta etapa:

1. a checklist foi reduzida ao minimo operacional necessario para as primeiras horas apos o deploy;
2. ela cobre exatamente os sinais que importam para este incidente:
   - ausencia do placeholder proibido;
   - continuidade de eventos Web reais;
   - deteccao rapida de regressao;
3. o material ficou curto o bastante para uso real de operacao, sem depender de lembrar toda a investigacao anterior.


## Fase 6 - Follow-up opcional, fora do hotfix

### [x] Item 6.1 - Abrir trilha separada para o canal mobile

Analise desta etapa concluida sem qualquer alteracao no canal mobile e sem ampliar o escopo do hotfix Web. O objetivo aqui foi apenas registrar o que a evidencia ja mostra, localizar a trilha tecnica do `local` no mobile e deixar uma recomendacao objetiva para trabalho futuro separado.

Evidencia registrada para o canal mobile:

1. o proprio plano desta correcao ja congelava que `Localizacao nao Cadastrada` apareceu em producao tanto em eventos `web` quanto em eventos `mobile`;
2. isso significa que, embora a causa raiz tratada neste hotfix tenha sido confirmada no frontend Web automatico, existe indicio real de problema semelhante ou semanticamente relacionado no canal mobile;
3. por esse motivo, a ausencia de acao sobre mobile neste pacote nao deve ser lida como “problema inexistente”, e sim como separacao deliberada de escopo.

Trilha tecnica identificada para o `local` no mobile dentro deste workspace:

1. o codigo nativo do aplicativo mobile nao esta presente neste repositorio;
2. portanto, o ponto mais confiavel e observavel no workspace nao e a funcao de UI do app que monta o campo, e sim a fronteira de API por onde o app envia `local` ao backend;
3. essa fronteira esta em `sistema/app/routers/mobile.py`, por tres entradas:
   - `POST /api/mobile/events/submit` em `submit_mobile_event(payload: MobileSubmitRequest)`;
   - `POST /api/mobile/events/forms-submit` em `submit_mobile_forms_event(payload: MobileFormsSubmitRequest)`;
   - `POST /api/mobile/events/sync` em `sync_mobile_event(payload: MobileSyncRequest)`;
4. nos endpoints `/events/submit` e `/events/sync`, o backend resolve o local por:
   - `resolved_local = payload.local or DEFAULT_MOBILE_LOCAL`;
   - `DEFAULT_MOBILE_LOCAL = "Aplicativo"`;
5. no endpoint `/events/forms-submit`, o backend repassa `payload.local` para `submit_forms_event(...)` com `MOBILE_FORMS_SUBMIT_CHANNEL`, cujo `default_local` tambem e `"Aplicativo"`;
6. em `sistema/app/schemas.py`, os schemas `MobileSubmitRequest`, `MobileFormsSubmitRequest` e `MobileSyncRequest` apenas normalizam `local` por `_normalize_optional_local(...)`;
7. isso confirma que, no contrato atual, o backend mobile trata `local` como valor textual vindo do cliente, com normalizacao de formato, mas sem regra de negocio equivalente ao bloqueio Web deste hotfix.

Cobertura existente que ajuda a interpretar esse contrato:

1. `tests/test_api_flow.py` possui varios cenarios do mobile aceitando `local` customizado enviado pelo cliente;
2. o teste `test_mobile_forms_submit_uses_default_and_custom_local` prova explicitamente que:
   - sem `local`, o sistema persiste `"Aplicativo"`;
   - com `local`, o sistema persiste o valor customizado informado, como `"Base P80"`;
3. outros testes de mobile em `tests/test_api_flow.py` tambem usam valores arbitrarios como `"Area A"`, `"Area B"`, `"Area C"` e `Area Tokyo ...`, reforcando que hoje a semantica do mobile e “texto operacional enviado pelo app”, nao “local derivado por matching interno do backend”.

Conclusao sobre compartilhamento de regra entre Web e mobile:

1. a regra de negocio de alto nivel deveria, sim, ser compartilhada semanticamente entre canais:
   - placeholders diagnosticos de falha nao deveriam virar `local` operacional persistido;
2. porem, a implementacao nao deve ser compartilhada de forma cega neste momento:
   - o Web tinha causa raiz confirmada em automacao/browser;
   - o mobile tem contrato diferente e hoje aceita `local` arbitrario do cliente;
   - `submit_forms_event(...)` e compartilhado, entao um bloqueio generico ali pode quebrar fluxos legitimos do mobile sem antes mapear quais valores o app realmente usa em producao.

Proposta objetiva de encaminhamento:

Merece **novo hotfix separado** se a operacao confirmar recorrencia atual de `Localizacao nao Cadastrada` no canal mobile com impacto real de dados; caso contrario, deve virar **task de backlog prioritaria** para mapear o payload do app nativo e levantar a lista de valores sinteticos realmente usados pelo mobile, deixando a **unificacao posterior no backend** apenas para depois desse mapeamento, idealmente por regra compartilhada mas sensivel ao canal e aos placeholders permitidos/proibidos de cada emissor.


### [x] Item 6.2 - Abrir trilha separada para placeholders sinteticos de localizacao

Analise desta etapa concluida como follow-up leve, sem ampliar o hotfix principal e sem implementar nova blindagem ampla. O trabalho ficou restrito a inventariar os textos conhecidos ligados ao campo de localizacao no Web e, quando facil de observar pelo backend, no mobile, para registrar quais nomes merecem futura auditoria de persistencia operacional.

Arquivos inspecionados para esta analise:

1. `sistema/app/static/check/app.js`
2. `sistema/app/static/check/automatic-activities.js`
3. `sistema/app/static/check/i18n-dictionaries.js`
4. `sistema/app/routers/mobile.py`
5. `sistema/app/routers/web_check.py`
6. `tests/test_api_flow.py`

Premissa operacional usada na classificacao:

1. nem todo texto exibido na area de localizacao e um candidato real a vazamento para persistencia;
2. os nomes de maior risco sao aqueles que:
   - ja aparecem como `label` de API;
   - ja entram em fallback de automacao;
   - ja entram em `manualLocationSelect`;
   - ou ja sao aceitos como `local` textual por algum endpoint;
3. textos puramente visuais de status so merecem blindagem se algum fluxo passar a reutiliza-los como valor de negocio.

Inventario encontrado no frontend Web:

1. placeholders puramente visuais ou de interface, sem papel operacional legitimo atual:
   - `Aguardando localização.`
   - `Sem localizações cadastradas`
   - `Localização indisponível`
   - `Sem Permissão`
   - `Tempo esgotado`
   - `Detectando...`
2. valores operacionais validos, que nao devem ser bloqueados por heuristica ampla:
   - `Escritório Principal`
   - qualquer `resolved_local` real vindo do matching
   - `Fora do Local de Trabalho`
   - `Zona Mista`
   - `Zona de CheckOut` / `Zona de checkout`
3. estados de erro/diagnostico ou placeholders sinteticos que exigem cuidado:
   - `Localização não Cadastrada`
   - `Precisao Insuficiente`
   - `Precisão insuficiente`
   - `Fora do Ambiente de Trabalho`

Leitura de cada grupo no contexto atual do Web:

1. `Localização não Cadastrada`
   - era o placeholder sintetico central do incidente;
   - ja recebeu blindagem no hotfix;
   - permanece na watchlist permanente porque qualquer refactor que volte a usar `label` como `local` pode reabrir o bug.
2. `Precisao Insuficiente` / `Precisão insuficiente`
   - hoje aparece em dois planos semanticos:
     - como label diagnostico de API (`Precisao insuficiente`);
     - como fallback/manual option no controller (`Precisao Insuficiente`);
   - ja recebeu bloqueio no frontend final da Web;
   - merece seguimento prioritario porque e o placeholder sintetico mais proximo do incidente em termos de risco de vazar para persistencia se algum fluxo manual/automatico for reaberto.
3. `Fora do Ambiente de Trabalho`
   - hoje e um label diagnostico de API para `outside_workplace`;
   - nao e o mesmo valor operacional usado para submit automatico, que e `Fora do Local de Trabalho`;
   - merece entrar na watchlist para evitar futura confusao entre label de leitura e `local` operacional.
4. `Fora do Local de Trabalho`
   - apesar de soar como mensagem, e valor operacional legitimo do fluxo automatico;
   - nao deve entrar em bloqueio generico de placeholder.
5. `Zona Mista` e `Zona de CheckOut`
   - sao valores de negocio do fluxo de automacao e de historico;
   - nao devem entrar em bloqueio de placeholder.
6. `Escritório Principal`
   - apesar de aparecer como constante de default manual no frontend, nao e placeholder sintetico;
   - e valor operacional valido quando existe nas localizacoes do projeto.

Observacao adicional sobre o mobile, no limite do que o workspace permite afirmar:

1. o codigo nativo do app nao esta neste repositorio;
2. pela fronteira observavel do backend mobile, o unico valor default claramente sintetico e `Aplicativo`, em `DEFAULT_MOBILE_LOCAL`;
3. esse valor, porem, e tratado hoje como local operacional legitimo do canal mobile e possui cobertura de teste em `test_mobile_forms_submit_uses_default_and_custom_local`;
4. por isso, `Aplicativo` nao entra na mesma categoria de `Localização não Cadastrada`;
5. fora isso, o contrato atual do mobile aceita `local` arbitrario enviado pelo cliente, entao nao foi possivel listar com seguranca placeholders diagnosticos adicionais especificos do app nativo a partir deste repo.

Placeholders/labels que merecem blindagem futura explicita:

1. `Localização não Cadastrada`
   - manter como caso obrigatorio em qualquer auditoria futura.
2. `Precisao Insuficiente` / `Precisão insuficiente`
   - priorizar como segundo caso obrigatorio de auditoria.
3. `Fora do Ambiente de Trabalho`
   - incluir como caso de confusao semantica entre label de API e `local` operacional.

Textos que ficam apenas como watchlist secundaria, sem urgencia de blindagem propria agora:

1. `Aguardando localização.`
2. `Sem localizações cadastradas`
3. `Localização indisponível`
4. `Sem Permissão`
5. `Tempo esgotado`
6. `Detectando...`

Motivo da prioridade secundaria:

1. esses textos sao hoje visuais e nao aparecem na trilha normal de `local` submetivel;
2. eles so virariam risco real se algum refactor passasse a reutilizar texto bruto de apresentacao como valor de negocio, exatamente o tipo de anti-pattern que o hotfix atual ja ajudou a deixar mais explicito.

Recomendacao de proximo passo, fora deste hotfix:

Abrir uma task de backlog pequena e separada para auditar todos os pontos em que o Web e, depois, o mobile aceitam ou derivam `local`, usando uma lista de allowlist/denylist semantica por canal: a allowlist deve preservar valores operacionais como `resolved_local`, `Fora do Local de Trabalho`, `Zona Mista`, `Zona de CheckOut` e defaults legitimos de canal como `Aplicativo`, enquanto a denylist inicial deve incluir `Localização não Cadastrada`, `Precisao Insuficiente` e o label diagnostico `Fora do Ambiente de Trabalho`, deixando os demais textos puramente visuais apenas em observacao ate que exista evidencia de que possam entrar na trilha de persistencia.
