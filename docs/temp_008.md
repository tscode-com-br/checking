# Plano para Ajustar o Fallback Manual de `Precisao insuficiente` na Web Application `sistema/app/static/check`

Data: 2026-04-25

## Objetivo

Definir um plano tecnico detalhado para ajustar o comportamento da SPA web em `sistema/app/static/check` quando a captura GPS terminar com `status = accuracy_too_low`, sem reabrir por engano o fluxo em que o usuario ainda nao concedeu permissao de geolocalizacao.

As novas regras pedidas sao:

1. ao desmarcar `Atividades Automaticas`, se o campo de localizacao mostrar `Precisao insuficiente`, habilitar `Projeto` e `Local` para escolha manual do check-in/check-out;
2. ao marcar `Atividades Automaticas`, se o campo de localizacao mostrar `Precisao insuficiente`, habilitar `Projeto` e `Local` para escolha manual do check-in/check-out;
3. se o usuario nao concedeu permissao de GPS ao navegador, manter o comportamento atual: o usuario escolhe `Local` apenas entre as opcoes cadastradas na API.

Regra adicional obrigatoria:

- a dropdown `Local` deve preferir `Escritorio Principal` como valor padrao;
- se o projeto atual nao tiver uma localizacao cadastrada chamada `Escritorio Principal`, o sistema deve considerar um valor sintetico de fallback e permitir o envio da atividade com esse valor.

## Diagnostico consolidado do estado atual

### 1. O frontend ja distingue `accuracy_too_low`, mas so parcialmente

Hoje o estado local da SPA ja guarda:

- `currentLocationResolutionStatus`;
- `gpsLocationPermissionGranted`.

E o helper:

- `shouldAllowManualLocationSelection()`

ja devolve `true` quando:

- o GPS nao tem permissao; ou
- o ultimo resultado terminou em `accuracy_too_low`.

Conclusao:

- a SPA ja tem um ponto central para diferenciar `sem permissao` de `precisao insuficiente`;
- porem esse helper ainda nao governa todas as regras de visibilidade e habilitacao da tela.

### 2. A visibilidade do campo `Local` ja foi parcialmente adaptada

Hoje `syncProjectVisibility()` usa:

- `const hideLocationField = isAutomaticActivitiesEnabled() || !shouldAllowManualLocationSelection();`

Isso significa:

- se `accuracy_too_low` estiver ativo e `Atividades Automaticas` estiver desligado, o campo `Local` pode reaparecer;
- se `Atividades Automaticas` estiver ligado, o campo continua escondido, mesmo em `accuracy_too_low`.

Conclusao:

- a regra nova exige transformar `accuracy_too_low` em uma excecao explicita tambem para o modo automatico.

### 3. A habilitacao dos controles ainda segue a regra antiga

Hoje `syncFormControlStates()` ainda faz:

- `projectSelect.disabled = ... || isAutomaticActivitiesEnabled();`
- `actionInputs.disabled = ... || automaticActivitiesEnabled;`
- `submitButton.disabled = ... || automaticActivitiesEnabled;`
- `manualLocationSelect.disabled = ... || gpsLocationPermissionGranted || availableLocations.length === 0;`

Consequencias praticas:

1. `Projeto` continua bloqueado sempre que `Atividades Automaticas` esta ligada;
2. os radios de `Check-In` e `Check-Out` continuam bloqueados sempre que `Atividades Automaticas` esta ligada;
3. o botao `Registrar` continua bloqueado sempre que `Atividades Automaticas` esta ligada;
4. mesmo quando o campo `Local` reaparece por `accuracy_too_low`, a select ainda pode permanecer desabilitada so porque o GPS foi concedido.

Conclusao:

- o fluxo atual atende apenas uma parte da ideia de fallback manual;
- para cumprir a nova regra, sera necessario criar uma excecao consistente de habilitacao, nao apenas de exibicao.

### 4. O valor padrao de `Local` hoje nao segue a nova preferencia pedida

Hoje `getDefaultManualLocation()` faz:

1. se `Escritorio Principal` estiver em `availableLocations`, usa esse valor;
2. caso contrario, usa o primeiro item do catalogo retornado pela API.

Conclusao:

- isso ainda nao cobre o novo requisito de fallback sintetico quando o projeto nao possui `Escritorio Principal`.

### 5. O fluxo sem permissao de GPS ja esta correto e deve ser preservado

Hoje, quando o navegador retorna erro de permissao (`error.code === 1`):

- `setLocationWithoutPermission()` limpa o match atual;
- `gpsLocationPermissionGranted` volta para `false`;
- a UI entra no modo manual tradicional.

Esse comportamento ja atende a regra 3 do pedido.

Conclusao:

- o plano deve isolar a nova logica ao caso `accuracy_too_low`;
- nao deve mexer no fluxo `sem permissao` alem de manter a cobertura de regressao.

### 6. O backend ja aceita um `local` sintetico sem exigir catalogo

O endpoint `POST /api/web/check` recebe `WebCheckSubmitRequest`, que herda `local: str | None` de `MobileFormsSubmitRequest`.

Hoje a validacao do schema:

- apenas normaliza whitespace;
- aceita qualquer texto de ate 40 caracteres.

E `submit_web_check()` repassa `payload.local` para `submit_forms_event(...)`, que usa o valor diretamente como `resolved_local`.

Conclusao:

- nao ha bloqueio estrutural atual para enviar um valor sintetico como `Precisao Insuficiente`;
- a primeira entrega pode ficar majoritariamente no frontend;
- ainda assim vale adicionar cobertura automatizada para garantir que esse valor especial nao seja rejeitado futuramente.

## Decisao de desenho recomendada

### 1. Introduzir um estado explicito de `fallback manual por precisao`

Em vez de espalhar `currentLocationResolutionStatus === 'accuracy_too_low'` por varios pontos, criar um helper semantico unico, por exemplo:

- `isAccuracyTooLowManualFallbackActive()`

Semantica recomendada:

- `true` somente quando o navegador tem permissao de GPS e a ultima resolucao terminou em `accuracy_too_low`;
- `false` nos casos `matched`, `outside_workplace`, `not_in_known_location`, `no_known_locations` e `sem permissao`.

Motivo:

- `sem permissao` deve continuar no fluxo manual tradicional;
- `accuracy_too_low` precisa virar um modo especial com mais excecoes de UI.

### 2. Tratar `accuracy_too_low` como excecao de override manual, independente da toggle

Quando `isAccuracyTooLowManualFallbackActive()` for `true`, a recomendacao e permitir override manual mesmo que `Atividades Automaticas` esteja ligada.

Isso implica habilitar:

- `Projeto`;
- `Local`;
- radios de `Check-In` e `Check-Out`;
- botao `Registrar`.

Regra recomendada:

- `Atividades Automaticas` pode permanecer marcada como preferencia do usuario;
- porem, enquanto o estado atual for `accuracy_too_low`, a tela entra em um modo excepcional de submissao manual assistida.

Motivo:

- isso atende os itens 1 e 2 sem obrigar o usuario a desligar a toggle para conseguir registrar a atividade.

### 3. Padronizar a resolucao do valor inicial da dropdown `Local`

Criar um helper especifico para o valor inicial do local manual quando o fallback estiver ativo, por exemplo:

- `resolveManualLocationDefaultForCurrentProject()`

Regra recomendada:

1. se `availableLocations` contem `Escritorio Principal`, selecionar `Escritorio Principal`;
2. caso contrario, usar um valor sintetico canonico, recomendado como `Precisao Insuficiente`;
3. esse valor sintetico deve aparecer como opcao selecionada apenas no modo de fallback por precisao, e nao no fluxo normal sem permissao de GPS.

Observacao importante:

- para evitar divergencia futura, escolher um unico literal canonico para o fallback manual e reutiliza-lo em UI, submit e testes;
- recomendacao pragmatica: usar `Precisao Insuficiente` como valor de persistencia da atividade manual.

### 4. Manter o fluxo `sem permissao` exatamente como esta

Quando `gpsLocationPermissionGranted === false` por negacao de permissao no navegador:

- nao injetar `Precisao Insuficiente` como opcao sintetica;
- manter apenas as opcoes cadastradas pela API no projeto atual;
- manter o comportamento atual de manual fallback classico.

## Arquivos provaveis de impacto

### Frontend principal

- `sistema/app/static/check/app.js`

### Testes frontend

- `tests/check_user_location_ui.test.js`

### Testes backend opcionais, mas recomendados

- `tests/test_api_flow.py`

## Plano tecnico detalhado

### Etapa 1. Consolidar o estado semantico do fallback por precisao

Objetivo:

- separar claramente `sem permissao` de `precisao insuficiente`.

Passos:

1. criar um helper dedicado, por exemplo `isAccuracyTooLowManualFallbackActive()`;
2. manter `shouldAllowManualLocationSelection()` como helper mais amplo, se continuar util, ou substitui-lo por duas funcoes mais explicitas;
3. revisar `setResolvedLocation()` e `setLocationWithoutPermission()` para garantir que o estado de fallback seja limpo e rearmado de forma previsivel.

Resultado esperado:

- toda a tela passa a decidir excecoes de UI com base em um estado unico e semantico.

### Etapa 2. Ajustar exibicao e habilitacao de `Projeto` e `Local`

Objetivo:

- tornar a regra nova consistente para toggle ligada e desligada.

Passos em `syncProjectVisibility()`:

1. deixar `Projeto` visivel quando o fallback por precisao estiver ativo, mesmo com `Atividades Automaticas` ligada;
2. deixar `Local` visivel quando o fallback por precisao estiver ativo, mesmo com `Atividades Automaticas` ligada;
3. manter o comportamento atual para todos os demais estados.

Passos em `syncFormControlStates()`:

1. habilitar `projectSelect` quando `isAccuracyTooLowManualFallbackActive()` for `true`, mesmo se a toggle estiver marcada;
2. habilitar `manualLocationSelect` quando `isAccuracyTooLowManualFallbackActive()` for `true` e houver opcoes disponiveis;
3. habilitar radios de `Check-In` e `Check-Out` nesse mesmo modo excepcional;
4. habilitar `submitButton` nesse mesmo modo excepcional;
5. manter `informe` como esta hoje, salvo se durante a implementacao surgir dependencia obrigatoria nao prevista.

Resultado esperado:

- o usuario consegue de fato escolher `Projeto`, `Local`, a acao e registrar a atividade quando o GPS falha por precisao insuficiente.

### Etapa 3. Construir a regra do valor padrao da dropdown `Local`

Objetivo:

- aplicar a preferencia `Escritorio Principal`, com fallback sintetico quando necessario.

Passos:

1. criar um helper para resolver o valor inicial manual do local no projeto atual;
2. se o catalogo do projeto contiver `Escritorio Principal`, preselecionar esse valor;
3. se o catalogo do projeto nao contiver `Escritorio Principal`, adicionar temporariamente a opcao `Precisao Insuficiente` ao conjunto apresentado na select;
4. garantir que essa opcao sintetica exista apenas no modo `accuracy_too_low`;
5. se o usuario trocar o projeto durante o fallback ativo, recalcular imediatamente a lista e o valor padrao do `Local`.

Ponto de implementacao recomendado:

- concentrar essa montagem em torno de `getDefaultManualLocation()`, `setLocationSelectOptions()` e `syncManualLocationControl()`, em vez de duplicar a regra em varios listeners.

Resultado esperado:

- a dropdown `Local` abre com `Escritorio Principal` quando possivel;
- quando isso nao for possivel, o proprio valor padrao ja sera `Precisao Insuficiente`.

### Etapa 4. Ajustar o submit para respeitar o override manual em `accuracy_too_low`

Objetivo:

- garantir que o valor enviado em `local` siga a escolha manual nessas duas regras novas.

Passos:

1. criar um helper de decisao do `local` efetivamente enviado, por exemplo `resolveSubmittedLocationValue()`;
2. quando o fallback por precisao estiver ativo, enviar `manualLocationSelect.value` mesmo se `gpsLocationPermissionGranted === true`;
3. quando o fallback por precisao nao estiver ativo, manter a logica atual de usar `currentLocationMatch.resolved_local` para GPS bem-sucedido;
4. preservar o fluxo atual de `sem permissao`, que ja depende do valor manual escolhido.

Resultado esperado:

- o envio manual com `Escritorio Principal` ou `Precisao Insuficiente` passa a ser deterministico.

### Etapa 5. Ajustar o comportamento ao marcar e desmarcar `Atividades Automaticas`

Objetivo:

- cobrir explicitamente os itens 1 e 2 do pedido.

Passos:

1. ao marcar a toggle, manter o fluxo atual de tentativa automatica por GPS;
2. se essa tentativa terminar em `accuracy_too_low`, entrar no modo excepcional de override manual sem exigir que a toggle seja desligada;
3. ao desmarcar a toggle, se o estado atual ainda for `accuracy_too_low`, manter `Projeto` e `Local` habilitados para escolha manual;
4. ao sair do estado `accuracy_too_low` por uma nova captura bem-sucedida, restaurar o comportamento atual de acordo com a toggle.

Resultado esperado:

- a diferenca entre toggle ligada e desligada deixa de bloquear o usuario justamente no caso especial pedido.

### Etapa 6. Garantir que a troca de projeto recompute o fallback

Objetivo:

- impedir que o local selecionado fique incoerente apos mudar o projeto.

Passos:

1. manter `updateCurrentUserProjectSelection()` como ponto principal de troca de projeto;
2. apos recarregar `availableLocations` para o novo projeto, recomputar o valor padrao de `Local` conforme a nova regra;
3. se o novo projeto nao tiver `Escritorio Principal`, selecionar automaticamente `Precisao Insuficiente`;
4. se tiver `Escritorio Principal`, substituir qualquer fallback sintetico anterior por esse valor real.

Resultado esperado:

- o fallback manual acompanha corretamente o projeto ativo.

### Etapa 7. Testes automatizados recomendados

#### 7.1. Frontend estatico/harness

Arquivo principal:

- `tests/check_user_location_ui.test.js`

Cobrir pelo menos:

1. `accuracy_too_low` com toggle desligada habilita `Projeto`, `Local`, radios e `Registrar`;
2. `accuracy_too_low` com toggle ligada tambem habilita `Projeto`, `Local`, radios e `Registrar`;
3. `sem permissao` continua usando apenas opcoes cadastradas pela API, sem inserir `Precisao Insuficiente`;
4. `Escritorio Principal` vira default quando existir no catalogo;
5. `Precisao Insuficiente` vira default sintetico quando `Escritorio Principal` nao existir;
6. o submit usa `manualLocationSelect.value` no modo de fallback por precisao, mesmo com GPS concedido;
7. ao trocar o projeto durante o fallback ativo, o default do `Local` e recalculado corretamente.

#### 7.2. Backend/API opcional, mas recomendado

Arquivo principal:

- `tests/test_api_flow.py`

Cobrir pelo menos:

1. `POST /api/web/check` aceita `local="Precisao Insuficiente"`;
2. o estado sincronizado resultante preserva esse valor como `current_local` quando o envio manual usa o fallback sintetico.

Motivo:

- o backend ja aceita texto livre, mas um teste explicito evita regressao futura quando alguem endurecer a validacao de `local`.

## Validacao manual recomendada

### Cenario A. Toggle desligada + `accuracy_too_low` + projeto com `Escritorio Principal`

Esperado:

1. `Projeto` visivel e habilitado;
2. `Local` visivel e habilitado;
3. `Local` preselecionado como `Escritorio Principal`;
4. usuario consegue registrar `Check-In` ou `Check-Out` manualmente.

### Cenario B. Toggle desligada + `accuracy_too_low` + projeto sem `Escritorio Principal`

Esperado:

1. `Local` preselecionado como `Precisao Insuficiente`;
2. o envio manual registra a atividade com esse valor.

### Cenario C. Toggle ligada + `accuracy_too_low` + projeto com `Escritorio Principal`

Esperado:

1. a toggle permanece marcada;
2. a UI entra em modo excepcional de override manual;
3. `Projeto`, `Local`, radios e `Registrar` ficam utilizaveis;
4. o envio manual usa `Escritorio Principal` por padrao.

### Cenario D. Toggle ligada + `accuracy_too_low` + projeto sem `Escritorio Principal`

Esperado:

1. o valor default de `Local` passa a ser `Precisao Insuficiente`;
2. o envio manual com esse valor e aceito.

### Cenario E. GPS sem permissao

Esperado:

1. o comportamento atual permanece intacto;
2. a select `Local` mostra apenas opcoes reais cadastradas na API;
3. nenhuma opcao sintetica de `Precisao Insuficiente` e injetada.

## Riscos e pontos de atencao

### 1. Os testes atuais de UI estao permissivos demais em alguns trechos

Hoje parte da suite usa regex muito amplas sobre `app.js`, o que pode deixar passar incoerencias entre visibilidade e habilitacao.

Recomendacao:

- fortalecer a suite com harness mais semantico para o estado `accuracy_too_low`, em vez de depender apenas de regex dispersas.

### 2. A grafia do fallback sintetico precisa virar fonte de verdade unica

Hoje o backend de matching devolve `label="Precisao insuficiente"` para `accuracy_too_low`.

Se a atividade manual passar a persistir `Precisao Insuficiente`, convem decidir uma forma canonica unica para:

- label exibido na UI;
- valor sintetico persistido no `local` do submit;
- expectativas dos testes.

Recomendacao:

- fechar esse literal antes da implementacao e reaproveita-lo em helper unico no frontend.

### 3. Nao confundir fallback manual com automatismo real

Mesmo com `Atividades Automaticas` ligada, o modo `accuracy_too_low` deve ser entendido como excecao de override manual, e nao como autorizacao para o sistema auto-registrar `Precisao Insuficiente` sem acao explicita do usuario.

## Sequencia recomendada de execucao

1. criar helper explicito de fallback por precisao em `app.js`;
2. alinhar `syncProjectVisibility()` e `syncFormControlStates()` a esse helper;
3. implementar resolucao do default `Escritorio Principal` / `Precisao Insuficiente`;
4. ajustar o payload do submit para usar o valor manual no fallback por precisao;
5. adaptar a troca de projeto durante fallback ativo;
6. cobrir com testes focados de frontend;
7. adicionar teste de API para `local="Precisao Insuficiente"`, se desejado;
8. validar manualmente os cinco cenarios acima.

## Resultado esperado ao final

Ao concluir este plano:

1. `Precisao insuficiente` deixa de ser um beco sem saida para o usuario;
2. `Projeto` e `Local` ficam utilizaveis tanto com a toggle ligada quanto desligada nesse caso especial;
3. `Escritorio Principal` vira o default preferencial da escolha manual;
4. quando esse local nao existir no projeto, `Precisao Insuficiente` passa a ser um fallback sintetico valido para registro manual;
5. o fluxo sem permissao de GPS permanece exatamente como esta hoje.

## To-do list por fases

### Fase 1. Consolidar o estado semantico do fallback por precisao

- [x] Introduzir um helper explicito para o modo `accuracy_too_low` em `app.js`.
- [x] Fazer o helper amplo de selecao manual delegar para esse estado semantico sem alterar o fluxo `sem permissao`.
- [x] Cobrir esse estado novo em `tests/check_user_location_ui.test.js`.

### Fase 2. Alinhar visibilidade e habilitacao da UI

- [x] Ajustar `syncProjectVisibility()` para tratar `accuracy_too_low` como excecao mesmo com `Atividades Automaticas` ligada.
- [x] Ajustar `syncFormControlStates()` para liberar `Projeto`, `Local`, radios e `Registrar` no fallback por precisao.
- [x] Preservar o bloqueio atual para todos os estados fora do fallback por precisao.

### Fase 3. Resolver o default manual de `Local`

- [x] Centralizar a resolucao do valor inicial da select `Local` em um helper dedicado.
- [x] Preferir `Escritorio Principal` quando existir no catalogo do projeto.
- [x] Injetar `Precisao Insuficiente` apenas no modo `accuracy_too_low` quando `Escritorio Principal` nao existir.

### Fase 4. Ajustar o payload de submit

- [x] Criar um helper para decidir o `local` efetivamente enviado no submit.
- [x] Enviar `manualLocationSelect.value` quando o fallback por precisao estiver ativo, mesmo com GPS concedido.
- [x] Manter o comportamento atual para `matched` e para o fluxo classico `sem permissao`.

### Fase 5. Fechar interacoes de toggle e troca de projeto

- [x] Garantir que ligar/desligar `Atividades Automaticas` preserve o override manual somente durante `accuracy_too_low`.
- [x] Recalcular a lista e o default de `Local` ao trocar o projeto durante o fallback ativo.
- [x] Restaurar automaticamente o comportamento normal quando uma nova captura sair de `accuracy_too_low`.

### Fase 6. Regressao e homologacao

- [x] Ampliar os testes de frontend para toggle ligada/desligada, projeto com/sem `Escritorio Principal` e troca de projeto.
- [x] Adicionar cobertura opcional de API para `local="Precisao Insuficiente"`.
- [x] Validar manualmente os cenarios A-E descritos neste documento.

### Fase 7. Ajuste visual complementar

- [x] Incluir ao lado da logomarca o titulo `Checking Weblink`, em negrito e na cor branca.