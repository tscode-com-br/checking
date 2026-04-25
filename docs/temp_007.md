# Plano Robusto para Ajustar a Janela de Captura GPS e Exibir a Margem de Erro em Tempo Real na Web Application `sistema/app/static/check`

Data: 2026-04-25

## Introducao

Este documento define um plano tecnico robusto, seguro e rastreavel para ajustar dois comportamentos da aplicacao web localizada em `sistema/app/static/check`:

1. alterar a janela de captura GPS usada nos gatilhos de ciclo de vida do navegador para que a sessao dure somente o necessario para atingir a margem de erro maxima configurada no administrador, sem ultrapassar `5000 ms`;
2. durante essa captura, substituir temporariamente o texto final de precisao por exibicao em tempo real da margem de erro corrente no mesmo slot visual da UI.

O objetivo deste plano nao e reabrir backend, contratos HTTP, fluxo administrativo ou layout amplo. O objetivo e ajustar a politica de captura GPS e a apresentacao visual do progresso de precisao no frontend web, preservando o contrato administrativo ja existente e o comportamento funcional consolidado da SPA.

## 1. Objetivo

Implementar na SPA `sistema/app/static/check` o seguinte comportamento:

- quando a URL da aplicacao for carregada pela primeira vez;
- quando o usuario der refresh no navegador;
- quando o navegador voltar para primeiro plano com a aba da aplicacao aberta;
- quando a aba da aplicacao voltar a ser a aba selecionada;

a captura GPS deve:

- iniciar imediatamente a tentativa de obter coordenadas com `accuracy_meters <= location_accuracy_threshold_meters`;
- encerrar antes de `5000 ms` somente se esse limite administrativo for atingido;
- encerrar obrigatoriamente em `5000 ms` se o limite nao for atingido antes;
- durante a captura, exibir no campo visual de precisao a margem de erro corrente em tempo real no lugar do texto final `Precisao X / Limite Y`;
- ao final da captura, restaurar o texto final normal com os valores considerados para o resultado da sessao.

## 2. Diagnostico Consolidado do Estado Atual

### 2.1. O limite administrativo ja existe e ja e a referencia funcional correta

Hoje o website administrativo em `sistema/app/static/admin` ja expoe o campo:

- `Erro maximo para considerar a coordenada do usuario:`

Esse campo alimenta `location_accuracy_threshold_meters`, que ja e usado no contrato atual da aplicacao web e do backend.

Conclusao tecnica:

- nao ha necessidade de criar novo parametro administrativo;
- o valor fonte de verdade continua sendo `location_accuracy_threshold_meters`.

### 2.2. O frontend web ja conhece esse limite antes e depois do matching

Na SPA atual:

- `loadManualLocations()` ja recebe `location_accuracy_threshold_meters` do endpoint de locais e popula `locationAccuracyThresholdMeters`;
- `applyLocationMatch()` ja recebe `accuracy_threshold_meters` do backend e atualiza o mesmo estado local;
- `buildLocationCapturePlan()` ja usa `locationAccuracyThresholdMeters` como `targetAccuracyMeters`.

Conclusao tecnica:

- a infraestrutura para comparar a precisao capturada com o limite administrativo ja existe no frontend;
- a demanda e majoritariamente de politica temporal e de UX, nao de contrato.

### 2.3. A politica atual nao atende ao comportamento pedido

Hoje o fluxo principal de captura usa `watch_window` com:

- `minimumWindowMs = 3000`;
- `maxWindowMs = 7000`.

Na pratica, isso significa:

- a sessao nunca pode encerrar antes de `3000 ms`, mesmo se a precisao suficiente chegar antes;
- a sessao pode durar ate `7000 ms`, o que excede o teto agora solicitado de `5000 ms`.

Conclusao tecnica:

- a politica atual conflita diretamente com a nova regra de negocio solicitada;
- sera necessario remover a janela minima obrigatoria para os gatilhos cobertos por esta demanda e reduzir o teto maximo para `5000 ms`.

### 2.4. Os gatilhos relevantes ja estao mapeados no codigo

Hoje os eventos relevantes ja passam por `runLifecycleUpdateSequence()` com `triggerSource` explicito:

- `startup`;
- `visibility`;
- `focus`;
- `pageshow`.

Esses gatilhos sao a traducao tecnica mais proxima de:

- carregar a URL;
- refresh do navegador;
- trazer o navegador para primeiro plano com a aba aberta;
- selecionar novamente a aba da aplicacao.

Conclusao tecnica:

- o recorte pedido pode ser implementado sem inventar novos listeners de navegador;
- a mudanca deve se concentrar no plano de captura associado a esses `triggerSource`.

### 2.5. A UI atual mostra a melhor precisao observada, nao necessariamente a precisao corrente

Hoje o helper `updateLocationCaptureProgress()`:

- chama `setLocationPresentation('Buscando melhor precisao...', ..., buildAccuracyText(...))`;
- so e acionado quando a nova amostra e melhor que `bestPosition`;
- portanto, o campo `locationAccuracy` exibe a melhor amostra conhecida ate aquele ponto, e nao a amostra corrente recebida em tempo real.

Conclusao tecnica:

- a segunda parte da demanda nao e apenas trocar microcopy;
- sera necessario separar semanticamente `current_accuracy_meters` de `best_accuracy_meters` durante a sessao de captura.

### 2.6. O comportamento desejado nao deve ser confundido com o botao manual de atualizar localizacao

A demanda do usuario fala em:

- carregar URL;
- refresh do navegador;
- navegador em primeiro plano;
- aba selecionada.

Isso se refere ao ciclo de vida do navegador, e nao necessariamente ao botao `Atualizar localizacao` da propria tela.

Conclusao tecnica:

- o recorte primario desta demanda deve incidir sobre `startup`, `visibility`, `focus` e `pageshow`;
- qualquer alinhamento opcional do botao manual `refreshLocationButton` deve ser tratado como decisao explicita, nao como efeito colateral inevitavel.

## 3. Escopo Exato da Mudanca

### 3.1. O que entra no escopo

- reconfigurar a politica de captura GPS para os gatilhos `startup`, `visibility`, `focus` e `pageshow`;
- permitir encerramento antecipado assim que `accuracy_meters <= location_accuracy_threshold_meters`;
- limitar a sessao a no maximo `5000 ms`;
- exibir a margem de erro corrente em tempo real durante a captura no campo visual `locationAccuracy`;
- restaurar o texto final normal de precisao quando a sessao terminar;
- atualizar testes focados no fluxo de localizacao;
- registrar homologacao da nova regra em aparelho real e/ou instrumentacao local.

### 3.2. O que fica fora do escopo

- criar novo campo no administrador;
- alterar backend, payload ou endpoint de `POST /api/web/check/location`;
- alterar o significado do campo administrativo atual;
- abrir escopo para `/api/mobile/*` ou qualquer contrato alternativo;
- redesenhar a UI de localizacao fora da troca do texto de progresso;
- alterar automaticamente o comportamento do botao manual `Atualizar localizacao` sem decisao explicita;
- reabrir layout de retrato/paisagem/desktop fora do que for estritamente necessario para a leitura do texto de precisao.

## 4. Premissas Imutaveis

- `location_accuracy_threshold_meters` continua sendo a unica fonte de verdade do limite administrativo aceitavel;
- a captura nao pode ultrapassar `5000 ms` nos gatilhos cobertos por esta demanda;
- se o limite administrativo for atingido antes, a captura pode encerrar imediatamente;
- se o limite nao for atingido ate `5000 ms`, a sessao termina mesmo assim;
- a melhor amostra continua sendo a candidata preferencial para envio final ao backend quando a sessao expirar sem atingir o limite;
- durante a captura, o slot `locationAccuracy` deve mostrar a precisao corrente em tempo real, nao a melhor precisao observada;
- ao final da captura, a UI volta a exibir o texto final normal no formato vigente da aplicacao;
- os bloqueios atuais contra concorrencia e repeticao de gatilhos devem ser preservados (`locationRequestPromise`, `lifecycleRefreshInProgress`, `lifecycleTriggerCooldownMs`);
- a aplicacao continua respeitando permissao, HTTPS e suporte do navegador exatamente como hoje.

## 5. Resultado Desejado por Comportamento

### 5.1. Carregamento inicial da URL e refresh do navegador

Quando a aplicacao for carregada ou recarregada:

- a captura deve iniciar sem janela minima artificial de `3000 ms`;
- se uma amostra atingir o limite administrativo em `1.2 s`, `2.1 s` ou qualquer valor inferior a `5000 ms`, a sessao pode terminar naquele momento;
- se nenhuma amostra atingir o limite, a sessao deve terminar em `5000 ms` com fallback controlado para a melhor amostra observada.

### 5.2. Retorno ao primeiro plano e reselecao da aba

Quando o navegador ou a aba voltar a ficar visivel:

- o mesmo comportamento temporal deve valer para `visibility`, `focus` e `pageshow`;
- nao deve haver sessoes duplicadas para a mesma intencao de refresh de foreground;
- o usuario nao deve ver respostas instantaneas artificiais so porque o fluxo caiu em `single_attempt` por engano.

### 5.3. Texto de precisao durante a captura

Durante a sessao ativa:

- `locationValue` pode continuar em estado de busca, por exemplo `Buscando precisao suficiente...`;
- `locationAccuracy` deve mostrar a margem de erro corrente da amostra recebida naquele instante, reaproveitando o mesmo espaco visual da UI;
- o limite administrativo deve continuar visivel no mesmo texto sempre que estiver disponivel.

Direcao recomendada de copy:

- `Precisao atual 18 m / Limite 30 m`
- `Precisao atual 42 m / Limite 30 m`

### 5.4. Texto de precisao ao final da captura

Quando a sessao terminar:

- a UI nao deve permanecer em modo de progresso;
- o campo `locationAccuracy` deve voltar ao formato final normal (`Precisao X / Limite Y` ou equivalente atual);
- a mensagem final deve refletir o resultado real do backend ou o erro do navegador, sem contradicao com a leitura mostrada durante a captura.

## 6. Estrategia Tecnica Recomendada

### 6.1. Direcao geral

A estrategia mais segura e:

1. preservar a arquitetura atual baseada em `buildLocationCapturePlan()` e `requestCurrentPositionForPlan()`;
2. trocar somente a politica temporal dos gatilhos de ciclo de vida cobertos pela demanda;
3. separar internamente a nocao de `current_accuracy_meters` da nocao de `best_accuracy_meters`;
4. manter `bestPosition` como criterio de fallback tecnico e `currentPosition` como criterio de exibicao em tempo real;
5. preservar backend, admin e contrato HTTP intactos.

### 6.2. Reconfiguracao recomendada da janela de captura

O plano recomendado e adotar, para `startup`, `visibility`, `focus` e `pageshow`:

- `strategy = watch_window`;
- `minimumWindowMs = 0`;
- `maxWindowMs = 5000`.

Direcao de implementacao:

- evitar alterar o fallback `single_attempt` de gatilhos nao cobertos por esta demanda;
- tratar `refresh` do navegador como o mesmo caminho tecnico de `startup`;
- preservar `manual_refresh`, `submit_guard` e gatilhos de automacao congelados ate decisao explicita, para nao ampliar escopo silenciosamente.

### 6.3. Encerramento antecipado

`shouldStopLocationWatch()` deve passar a obedecer a seguinte regra para os gatilhos cobertos:

- se `best_accuracy_meters <= targetAccuracyMeters`, encerrar imediatamente;
- nao exigir permanencia minima de `3000 ms`;
- manter o encerramento forcoso ao atingir `5000 ms`.

Importante:

- o criterio de parada continua podendo usar a melhor amostra valida, porque se uma amostra corrente entrar abaixo do limite ela tambem sera, por definicao, a melhor amostra ate aquele momento;
- o criterio de exibicao em tempo real, porem, nao deve continuar preso apenas a essa melhor amostra.

### 6.4. Exibicao da margem de erro em tempo real

O plano recomendado e introduzir uma diferenciacao explicita entre:

- `currentAccuracyMeters`: precisao da amostra corrente recebida naquele callback do GPS;
- `bestAccuracyMeters`: melhor precisao observada na sessao ate aquele ponto.

Direcao de implementacao:

- `updateLocationCaptureProgress()` deve ser chamado em toda amostra valida recebida, nao apenas quando houver melhora;
- a copy de progresso deve refletir a amostra corrente, por exemplo `Precisao atual X / Limite Y`;
- `bestPosition` continua sendo atualizado apenas quando a nova amostra for realmente melhor.

### 6.5. Dependencia do limite administrativo no frontend

Como o encerramento antecipado depende de `targetAccuracyMeters`, o plano deve verificar explicitamente:

- se `locationAccuracyThresholdMeters` ja esta hidratado antes de iniciar a sessao dos gatilhos cobertos;
- se houver casos em que esse valor ainda esteja `null`, a sessao deve continuar ate `5000 ms` sem encerramento antecipado, exibindo a precisao corrente com o limite conhecido apenas quando disponivel.

Direcao recomendada:

- nao inventar novo fetch so para esta demanda se `loadManualLocations()` ja estiver cobrindo o caso;
- documentar claramente que sem `targetAccuracyMeters` conhecido nao existe criterio seguro para encerrar antes de `5000 ms`.

### 6.6. Protecao contra duplicidade de gatilhos

Como `visibility`, `focus` e `pageshow` podem disparar em sequencia para o mesmo retorno ao foreground, a implementacao deve preservar integralmente:

- `locationRequestPromise`;
- `lifecycleRefreshInProgress`;
- `lifecycleTriggerCooldownMs`;
- encaminhamento correto de `settings` para `updateLocationForLifecycleSequence(settings)`.

Direcao recomendada:

- a nova regra de `0-5000 ms` nao deve reabrir o bug antigo em que os gatilhos de ciclo de vida caiam silenciosamente em `single_attempt` por perda do `triggerSource`.

## 7. Arquivos Mais Provaveis de Alteracao

### Frontend principal

- `sistema/app/static/check/app.js`

### Testes focados

- `tests/check_user_location_ui.test.js`

### Documentacao de apoio

- `docs/temp_002.md` se a execucao vier a alterar o plano GPS anterior;
- `docs/temp_007.md` como plano desta nova demanda.

## 8. Plano de Execucao por Fases

## Fase 0. Congelamento do recorte e alinhamento com o comportamento atual

Objetivo:

- transformar a demanda do usuario em recorte tecnico preciso, sem ampliar escopo para gatilhos nao pedidos.

Atividades:

- confirmar que `startup`, `visibility`, `focus` e `pageshow` sao os gatilhos realmente cobertos pela demanda;
- registrar explicitamente que o `refresh` citado e o refresh do navegador, nao o botao manual de localizacao;
- registrar o estado atual da janela compartilhada `3000-7000 ms` como baseline a ser substituida neste recorte;
- registrar que a UI atual mostra a melhor precisao observada, e nao a precisao corrente.

Critero de conclusao:

- o time sabe exatamente quais gatilhos mudarao, quais permanecerao congelados e qual diferenca comportamental sera perseguida.

Execucao registrada em 2026-04-25:

1. Foi confirmado por leitura direta de `sistema/app/static/check/app.js` e pela baseline ja registrada em memoria do repositorio que a demanda permanece restrita ao frontend web em `sistema/app/static/check`, sem necessidade de alterar backend, endpoint, payload ou regra administrativa nesta fase.
2. Ficou congelado como recorte tecnico obrigatorio da demanda que os gatilhos pedidos pelo usuario correspondem a `startup`, `visibility`, `focus` e `pageshow`: o carregamento inicial e o refresh do navegador convergem para `runLifecycleUpdateSequence({ ignoreCooldown: true, triggerSource: 'startup' })`, enquanto retorno ao primeiro plano e reselecao da aba continuam vindo dos listeners de `visibilitychange`, `focus` e `pageshow`.
3. Ficou registrado como baseline vigente que o frontend atual ainda usa uma `watch_window` compartilhada de `3000-7000 ms` para `startup`, `submit_guard`, `manual_refresh`, `automatic_activities_enable`, `automatic_activities_disable`, `visibility`, `focus` e `pageshow`, com fallback `single_attempt` apenas para gatilhos desconhecidos; por isso, as fases seguintes terao de reduzir o recorte para os gatilhos pedidos, e nao alterar cegamente toda a matriz de captura.
4. Foi confirmado no fluxo de `requestWatchedCurrentPosition()` que `updateLocationCaptureProgress()` so e chamado quando `isLocationSampleBetter(position, bestPosition)` promove a nova amostra a `bestPosition`; isso congela como fato verificado que a UI atual mostra a melhor precisao observada, e nao a precisao corrente em tempo real.
5. Foi congelado como baseline funcional que o limite administrativo continua vindo de `location_accuracy_threshold_meters`, reaproveitado em `loadManualLocations()`, `buildLocationCapturePlan()` e `applyLocationMatch()`, o que mantem esta demanda fora de escopo de configuracao administrativa nova.
6. Tambem ficou documentado nesta fase que o botao manual `refreshLocationButton` nao faz parte do escopo obrigatorio desta alteracao: a implementacao futura podera optar por alinhamento posterior, mas a obrigacao imediata continua restrita aos gatilhos de ciclo de vida explicitamente pedidos.

## Fase 1. Reconfiguracao da janela de captura para os gatilhos pedidos

Objetivo:

- trocar a politica `3000-7000 ms` pela politica `0-5000 ms` nos gatilhos de ciclo de vida cobertos por esta demanda.

Atividades:

- revisar `locationCapturePlansByTrigger`;
- criar ou ajustar o plano de captura usado por `startup`, `visibility`, `focus` e `pageshow` para `minimumWindowMs = 0` e `maxWindowMs = 5000`;
- preservar o fallback `single_attempt` para gatilhos fora do recorte, se isso for a decisao escolhida;
- revisar `shouldStopLocationWatch()` para remover a espera minima artificial nesses gatilhos.

Critero de conclusao:

- os gatilhos cobertos podem encerrar imediatamente ao atingir o limite administrativo e nunca excedem `5000 ms`.

Execucao registrada em 2026-04-25:

1. `sistema/app/static/check/app.js` passou a declarar um plano dedicado `lifecycleLocationCapturePlan` com `strategy = watch_window`, `minimumWindowMs = 0` e `maxWindowMs = 5000`, isolando a nova politica temporal pedida para os gatilhos de ciclo de vida do navegador.
2. O mapa `locationCapturePlansByTrigger` foi ajustado para usar esse novo plano apenas em `startup`, `visibility`, `focus` e `pageshow`, enquanto `submit_guard`, `manual_refresh`, `automatic_activities_enable` e `automatic_activities_disable` permaneceram presos ao `enforcedLocationCapturePlan` de `3000-7000 ms`, preservando o escopo congelado na Fase 0.
3. `shouldStopLocationWatch()` nao precisou de reescrita estrutural: como a regra de parada ja depende de `capturePlan.minimumWindowMs`, os gatilhos cobertos agora podem encerrar imediatamente ao atingir `targetAccuracyMeters`, enquanto os gatilhos fora do recorte continuam respeitando a janela minima antiga.
4. `tests/check_user_location_ui.test.js` foi endurecido para proteger exatamente essa divisao de politica temporal, deixando de aceitar implicitamente que todos os gatilhos compartilham a mesma janela.
5. A validacao focada da fase foi concluida com `node --test tests/check_user_location_ui.test.js`, cobrindo o fluxo de configuracao dos planos de captura e preservando os asserts de integracao ja existentes para `buildLocationCapturePlan()`, `requestCurrentPositionForPlan()` e encaminhamento de `settings`.

## Fase 2. Exibicao da margem de erro corrente em tempo real

Objetivo:

- fazer a UI refletir a margem de erro corrente durante a sessao, sem destruir a logica de melhor amostra final.

Atividades:

- revisar `updateLocationCaptureProgress()`;
- passar a chamar o helper em toda amostra valida, nao apenas quando houver melhora;
- introduzir copy especifica de progresso (`Precisao atual X / Limite Y`) no mesmo slot `locationAccuracy`;
- preservar `bestPosition` apenas como criterio de decisao tecnica e fallback final;
- garantir que ao terminar a sessao a UI volte ao texto final normal montado por `buildAccuracyText()`.

Critero de conclusao:

- durante a busca, o usuario ve a margem de erro corrente em tempo real; ao final, a UI volta ao estado final coerente.

Execucao registrada em 2026-04-25:

1. `sistema/app/static/check/app.js` passou a declarar o helper `buildLocationCaptureProgressAccuracyText()`, reaproveitando `buildAccuracyText()` para manter o formato final vigente e trocar apenas o prefixo de progresso para `Precisao atual ...` no mesmo slot visual `locationAccuracy`.
2. `updateLocationCaptureProgress()` deixou de anunciar `Buscando melhor precisao...` e passou a publicar `Buscando precisao suficiente...`, usando a precisao corrente da amostra recebida naquele callback, com guarda explicita para ignorar leituras sem `accuracy` numerica valida.
3. O callback de `navigator.geolocation.watchPosition()` em `requestWatchedCurrentPosition()` passou a chamar `updateLocationCaptureProgress(position, capturePlan, progressOptions)` em toda amostra valida recebida, antes da promocao opcional para `bestPosition`; com isso, `bestPosition` permanece restrito ao criterio tecnico de parada e fallback final, sem controlar mais a UX de progresso em tempo real.
4. A validacao focada da fase foi concluida com `node --test tests/check_user_location_ui.test.js`, e o teste de localizacao foi ajustado apenas o suficiente para proteger a nova semantica de `Precisao atual ...` e a desvinculacao entre progresso visual e `isLocationSampleBetter()`, sem declarar a Fase 3 encerrada por completo.

## Fase 3. Protecao de regressao automatizada

Objetivo:

- atualizar as guardas automatizadas para a nova regra sem abrir falso positivo com o comportamento antigo.

Atividades:

- atualizar `tests/check_user_location_ui.test.js` para refletir `minimumWindowMs = 0` e `maxWindowMs = 5000` no recorte coberto;
- remover a expectativa antiga de bloqueio minimo de `3000 ms`;
- adicionar assert para confirmar que `updateLocationCaptureProgress()` deixa de depender exclusivamente de `isLocationSampleBetter()` para ser chamado;
- adicionar assert para confirmar que o texto de progresso deixa de proteger `Buscando melhor precisao...` como unica copy obrigatoria e passa a proteger a nocao de precisao corrente;
- preservar os asserts sobre encaminhamento correto de `settings` e uso de `runLifecycleUpdateSequence()`.

Critero de conclusao:

- a suite deixa de proteger a janela `3000-7000 ms` e passa a proteger a regra `0-5000 ms` com exibicao de precisao corrente.

Execucao registrada em 2026-04-25:

1. `tests/check_user_location_ui.test.js` deixou de depender apenas de regexes amplos sobre `app.js` e passou a compilar, via `vm`, um harness executavel com os helpers reais da captura GPS extraidos do source, endurecendo a protecao de regressao sem precisar carregar a SPA inteira no ambiente de teste Node.
2. A suite passou a validar de forma comportamental que `buildLocationCapturePlan()` aplica `0-5000 ms` apenas a `startup`, `visibility` e `pageshow` no recorte coberto pelo teste, preservando `3000-7000 ms` para `manual_refresh` e `submit_guard`, alem do fallback `single_attempt` fora do mapa conhecido.
3. A regra de parada ficou protegida por execucao direta de `shouldStopLocationWatch()`, cobrindo o encerramento imediato dos gatilhos com `minimumWindowMs = 0`, a manutencao da janela minima nos gatilhos congelados e o comportamento seguro quando `targetAccuracyMeters` ainda nao esta disponivel.
4. A UX da Fase 2 passou a ficar guardada por execucao direta de `buildLocationCaptureProgressAccuracyText()`, `updateLocationCaptureProgress()` e `requestWatchedCurrentPosition()`, incluindo a copy `Precisao atual ...`, a atualizacao do progresso em toda amostra valida e a manutencao de `bestPosition` apenas como fallback final quando a janela expira.
5. Os guards de integracao que ainda fazem sentido permaneceram no arquivo para proteger o handoff de `settings` no fluxo de ciclo de vida, e a validacao focada da fase foi concluida com `node --test tests/check_user_location_ui.test.js`, agora com `8/8` testes aprovados.

## Fase 4. Homologacao tecnica em aparelho e navegador real

Objetivo:

- validar que a regra teorica realmente se comporta como esperado nos gatilhos do navegador.

Cenarios minimos:

1. carregar a URL da aplicacao com sessao desbloqueada;
2. dar refresh no navegador com sessao desbloqueada;
3. deixar a aba em segundo plano e trazela novamente ao primeiro plano;
4. alternar para outra aba e voltar para a aba da aplicacao;
5. validar cenario em que a precisao fica suficiente antes de `5000 ms`;
6. validar cenario em que a precisao nao fica suficiente antes de `5000 ms`;
7. validar que o campo visual de precisao muda em tempo real durante a sessao;
8. validar que o valor final volta ao formato normal ao terminar a sessao.

Critero de conclusao:

- os gatilhos cobertos respeitam a nova janela temporal e a UI de progresso fica compreensivel em aparelho real.

Execucao registrada em 2026-04-25:

1. A Fase 4 foi homologada por instrumentacao local em Chromium real via Playwright, usando o script `scripts/homologate_temp_007_phase4.py`, um backend preview local em `sqlite:///./preview_phase4_homologation.db` e o artefato gerado em `docs/temp_007_phase4_report.json`; a execucao nao dependeu de backend remoto nem de fixture manual no browser.
2. Durante a primeira rodada da homologacao, o fluxo real revelou que `updateLocationForLifecycleSequence()` ainda propagava `showDetectingState` como `false` por padrao; `sistema/app/static/check/app.js` foi corrigido para usar `settings.showDetectingState !== false`, e `tests/check_user_location_ui.test.js` recebeu uma guarda explicita para esse handoff.
3. A mesma homologacao tambem revelou que `/api/web/check/locations` ainda nao devolvia `location_accuracy_threshold_meters`, apesar de `loadManualLocations()` ja esperar esse campo para popular `locationAccuracyThresholdMeters`; isso impedia a parada antecipada confiavel nos gatilhos de ciclo de vida. O contrato foi corrigido em `sistema/app/schemas.py` e `sistema/app/routers/web_check.py`, e `tests/test_api_flow.py` passou a proteger esse payload.
4. Com esses ajustes aplicados, a rodada final da homologacao validou os cenarios de `startup`, refresh do navegador, `visibility`, `focus` e `pageshow` no navegador local instrumentado. O `startup` concluiu em `1131 ms` com `watch_window_completed -> target_accuracy_reached`, progresso `Precisao atual 42 m / Limite 30 m` seguido de `Precisao atual 18 m / Limite 30 m` e restauracao final para `Precisao 18 m / Limite 30 m`.
5. O refresh do navegador foi homologado com uma sequencia controlada que nao atingiu o limite administrativo antes do teto, produzindo `duration_ms = 5019`, `best_accuracy_meters = 35`, `watch_window_completed -> acquisition_window_elapsed`, final `accuracy_too_low` e restauracao final para `Precisao 35 m / Limite 30 m`.
6. Os gatilhos `visibility`, `focus` e `pageshow` tambem foram homologados individualmente na mesma SPA carregada, com duracoes de `192 ms`, `196 ms` e `203 ms`, respectivamente, sempre terminando com `target_accuracy_reached` no `watch_window_completed`, `final_status = matched` e progresso visivel `Precisao atual 15 m / Limite 30 m` antes do retorno ao texto final normal.
7. A validacao tecnica final da fase ficou registrada em tres frentes executaveis: `node --test tests/check_user_location_ui.test.js` com `8/8` testes aprovados, `python -m pytest tests/test_api_flow.py -k web_locations_catalog_includes_accuracy_threshold_for_lifecycle_capture` aprovado e a homologacao integral do browser local aprovada via `python scripts/homologate_temp_007_phase4.py`.

## 9. Criterios Tecnicos de Aceite

A implementacao futura so deve ser considerada aprovada se atender simultaneamente a todos os pontos abaixo:

1. A captura dos gatilhos `startup`, `visibility`, `focus` e `pageshow` nao exige mais espera minima artificial de `3000 ms`.
2. A captura desses gatilhos nao dura mais do que `5000 ms`.
3. Se a margem de erro administrativa for atingida antes de `5000 ms`, a sessao termina antes desse teto.
4. Se a margem de erro administrativa nao for atingida, a sessao termina em `5000 ms` com fallback controlado.
5. Durante a captura, `locationAccuracy` mostra a precisao corrente em tempo real no mesmo slot visual da UI.
6. Ao final da captura, o campo volta ao texto final normal de precisao.
7. O limite administrativo continua vindo de `location_accuracy_threshold_meters`, sem campo novo e sem backend novo.
8. Nao ha regressao no controle de concorrencia dos gatilhos de ciclo de vida.
9. Os testes focados deixam de proteger a janela `3000-7000 ms` e passam a proteger a regra `0-5000 ms`.

## 10. Riscos e Mitigacoes

### Risco 1. A mudanca atingir gatilhos nao pedidos por acidente

Mitigacao:

- limitar explicitamente a nova politica aos gatilhos `startup`, `visibility`, `focus` e `pageshow`;
- manter `manual_refresh`, `submit_guard` e automacao congelados ate decisao explicita.

### Risco 2. Encerramento antecipado deixar de funcionar porque o limite administrativo ainda nao foi hidratado

Mitigacao:

- verificar e documentar a disponibilidade de `locationAccuracyThresholdMeters` antes da sessao;
- se ele estiver `null`, permitir a sessao completa ate `5000 ms` sem encerrar cedo por chute.

### Risco 3. A UI continuar mostrando a melhor amostra, e nao a amostra corrente

Mitigacao:

- separar claramente `currentAccuracyMeters` e `bestAccuracyMeters`;
- chamar o helper visual em todas as amostras validas, e nao apenas quando a amostra for melhor.

### Risco 4. `visibility`, `focus` e `pageshow` abrirem sessoes concorrentes

Mitigacao:

- preservar e retestar os guard rails atuais de ciclo de vida;
- nao tocar nesses bloqueios fora do necessario.

### Risco 5. A mensagem final contradizer o que o usuario viu durante a captura

Mitigacao:

- reservar o texto de progresso apenas para a fase ativa da sessao;
- ao terminar, restaurar o texto final baseado no payload resolvido ou no erro do navegador.

## 11. Recomendacao Final

A recomendacao mais segura e tratar esta demanda como uma correcao pontual da politica de captura GPS e da UX de progresso, e nao como uma reabertura geral do plano de localizacao.

Em termos praticos, o melhor caminho e:

1. limitar o recorte aos gatilhos `startup`, `visibility`, `focus` e `pageshow`;
2. substituir a regra atual `3000-7000 ms` por `0-5000 ms` nesses gatilhos;
3. mostrar a precisao corrente em tempo real durante a captura;
4. manter `bestPosition` apenas como decisao tecnica de fallback e envio final;
5. atualizar os testes focados e homologar em navegador/aparelho real.

## 12. To-do List Completa de Execucao

### Fase 0. Escopo e baseline

- [x] Confirmar que a demanda cobre `startup`, `visibility`, `focus` e `pageshow`.
- [x] Confirmar que `refresh` do requisito significa refresh do navegador, e nao `refreshLocationButton`.
- [x] Registrar a politica atual `3000-7000 ms` como baseline desta nova demanda.
- [x] Registrar que a UI atual mostra melhor precisao observada, e nao precisao corrente.

### Fase 1. Janela temporal

- [x] Revisar `locationCapturePlansByTrigger`.
- [x] Ajustar `startup` para `minimumWindowMs = 0` e `maxWindowMs = 5000`.
- [x] Ajustar `visibility` para `minimumWindowMs = 0` e `maxWindowMs = 5000`.
- [x] Ajustar `focus` para `minimumWindowMs = 0` e `maxWindowMs = 5000`.
- [x] Ajustar `pageshow` para `minimumWindowMs = 0` e `maxWindowMs = 5000`.
- [x] Revisar `shouldStopLocationWatch()` para permitir encerramento imediato quando o limite administrativo for atingido.
- [x] Preservar fallback e gatilhos fora do recorte, se essa for a decisao final.

### Fase 2. UX da precisao em tempo real

- [x] Revisar `updateLocationCaptureProgress()`.
- [x] Passar a atualizar o campo de precisao em toda amostra valida.
- [x] Diferenciar `currentAccuracyMeters` de `bestAccuracyMeters`.
- [x] Exibir a precisao corrente em tempo real no slot `locationAccuracy`.
- [x] Restaurar o texto final normal quando a sessao terminar.

### Fase 3. Testes

- [x] Atualizar `tests/check_user_location_ui.test.js`.
- [x] Remover expectativa antiga de `minimumWindowMs = 3000`.
- [x] Adicionar expectativa de `maxWindowMs = 5000` no recorte correto.
- [x] Adicionar expectativa de exibicao de precisao corrente durante a captura.
- [x] Preservar as guardas de `settings` e dos gatilhos de ciclo de vida.
- [x] Executar os testes focados de localizacao antes de qualquer validacao ampla.

### Fase 4. Homologacao

- [x] Homologar carregamento inicial da URL.
- [x] Homologar refresh do navegador.
- [x] Homologar retorno do navegador ao primeiro plano.
- [x] Homologar reselecao da aba da aplicacao.
- [x] Homologar encerramento antes de `5000 ms` quando o limite for atingido.
- [x] Homologar encerramento em `5000 ms` quando o limite nao for atingido.
- [x] Homologar exibicao da margem de erro em tempo real durante a captura.
- [x] Confirmar restauracao do texto final normal ao encerrar.

## 13. Estado Desta Entrega

Este arquivo registra o plano da modificacao, a execucao documental da Fase 0, as implementacoes validadas das Fases 1, 2 e 3 e a homologacao tecnica concluida da Fase 4.

Todas as fases previstas neste plano foram concluidas.