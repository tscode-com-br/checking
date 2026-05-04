# Plano detalhado para corrigir o check-in no refresh manual apos sair da Zona de CheckOut

## 1. Objetivo deste plano

Este plano existe para corrigir, com o menor risco possivel, a falha descrita na Situacao 7 da Checking Web.

Regra alvo:

1. a ultima atividade do usuario foi um check-out;
2. a aplicacao web esta em primeiro plano;
3. o usuario pressiona apenas o botao `Atualizar` para renovar a coordenada GPS;
4. a localizacao anterior relevante era `Zona de CheckOut`;
5. a nova localizacao nao e `Zona de CheckOut`;
6. a nova localizacao pode ser uma localizacao cadastrada na API ou uma localizacao nao cadastrada, desde que o usuario nao esteja a mais de 2000 metros de uma localizacao cadastrada, desconsiderando `Zona de CheckOut` nessa verificacao;
7. a aplicacao deve fazer check-in imediatamente apos a atualizacao da localizacao.

Este plano foi desenhado para preservar o comportamento que ja esta correto nas Situacoes 1 a 6 e para evitar refatoracoes amplas em uma superficie que hoje ja funciona bem.

## 2. Estado confirmado no repositorio antes da correcao

Leitura objetiva do codigo atual:

1. `docs/regras_checkin_checkout_webapp.txt` documenta hoje apenas as Situacoes 1 a 6.
2. `sistema/app/static/check/app.js` possui a funcao `runManualLocationRefreshSequence()`.
3. Nessa funcao, o botao `Atualizar` chama `resolveCurrentLocation()` com `measurementTrigger: 'manual_refresh'`.
4. Depois de obter `locationPayload`, o fluxo atual do repositorio chama `runAutomaticActivitiesIfNeeded(locationPayload)`.
5. `sistema/app/static/check/app.js` tambem usa a mesma rotina automatica no fluxo de ciclo de vida da pagina, por meio de `runLifecycleUpdateSequence()`.
6. `sistema/app/static/check/automatic-activities.js` concentra a decisao de check-in e check-out automaticos.
7. Nesse arquivo ja existem duas decisoes importantes:
8. `shouldAttemptAutomaticLocationEvent()` cobre localizacao cadastrada, inclusive check-out na `Zona de CheckOut` e check-in quando a ultima acao foi check-out.
9. `shouldAttemptAutomaticNearbyWorkplaceCheckIn()` cobre o caso em que a localizacao nao bate exatamente com um local cadastrado, mas o backend devolve `status = not_in_known_location`, indicando que o usuario ainda esta proximo do local de trabalho.
10. O repositorio ja possui um teste de controller para o refresh manual em `tests/check_user_location_ui.test.js`, mas esse teste cobre explicitamente a Situacao 6, nao a Situacao 7.
11. O repositorio ja possui testes de decisao em `tests/web_automatic_activities.test.js` para check-in apos check-out em local conhecido e para check-in apos check-out em localizacao nao cadastrada proxima do trabalho.

Conclusao pratica:

1. o caminho de orquestracao necessario para a Situacao 7 aparentemente ja existe no codigo fonte local;
2. a lacuna mais provavel esta em um destes pontos:
3. o artefato publicado em producao nao corresponde ao codigo atual do repositorio;
4. existe um edge case real no estado remoto retornado pela API durante o refresh manual;
5. existe um gap de cobertura entre a regra desejada e os testes do botao `Atualizar`.

## 3. Hipotese local e checagem discriminante

Hipotese local de trabalho:

1. o comportamento quebrado esta concentrado no caminho do refresh manual quando o usuario sai da `Zona de CheckOut` apos um ultimo evento de check-out;
2. a forma mais segura de confirmar isso e testar o botao `Atualizar` com o estado remoto `checkout` e com dois tipos de payload de localizacao:
3. um payload de localizacao cadastrada fora da `Zona de CheckOut`;
4. um payload de localizacao nao cadastrada, mas ainda dentro do raio permitido pelo backend.

Checagem discriminante mais barata:

1. adicionar e executar dois testes focados no caminho `runManualLocationRefreshSequence()`;
2. se esses testes falharem localmente, a falha esta no codigo do frontend e a correcao deve ser minima e local;
3. se esses testes passarem localmente, a primeira suspeita deve passar a ser deploy, cache ou divergencia entre bundle publicado e fonte atual.

## 4. Principios obrigatorios da correcao

1. nao criar um segundo caminho de submit automatico paralelo ao atual;
2. reutilizar ao maximo a rotina ja existente `runAutomaticActivitiesIfNeeded()`;
3. manter `automatic-activities.js` como fonte de verdade da decisao de check-in e check-out automaticos;
4. nao recalcular distancia no frontend quando o backend ja devolve `status`, `matched`, `resolved_local` e os demais sinais necessarios;
5. nao mexer na logica de permissao de geolocalizacao, fallback manual por baixa precisao ou bloqueio por app travada, a menos que a investigacao prove que o problema esta ali;
6. nao alterar os fluxos de `startup`, `visibility`, `focus` e `pageshow` sem necessidade;
7. nao alterar a semantica das Situacoes 1 a 6;
8. nao introduzir regressao em check-out automatico na `Zona de CheckOut`;
9. tratar a Situação 7 como extensao do comportamento ja esperado e nao como um fluxo novo de produto.

## 5. Plano detalhado por fases

## Fase 0 - Congelar o comportamento esperado

Objetivo:

1. transformar a Situacao 7 em criterio executavel de aceite antes de tocar no comportamento.

Acoes:

1. registrar formalmente a Situacao 7 no documento de regras da web app;
2. quebrar a Situacao 7 em duas variantes obrigatorias:
3. variante 7A: o refresh manual sai da `Zona de CheckOut` e passa para um local cadastrado na API;
4. variante 7B: o refresh manual sai da `Zona de CheckOut`, nao casa com nenhum local exato, mas continua dentro do raio permitido pelo backend e deve gerar check-in com `Localizacao nao Cadastrada`;
5. registrar tambem dois controles negativos para a mesma superficie:
6. controle negativo 1: refresh manual permanece na `Zona de CheckOut` apos ultimo check-out e nao deve gerar nova atividade;
7. controle negativo 2: refresh manual sai da `Zona de CheckOut`, mas o backend devolve `outside_workplace`, e portanto nao deve gerar check-in.

Saida esperada:

1. o time passa a ter um contrato textual claro para o bug report e para a regressao.

## Fase 1 - Reproducao minima e isolamento do problema

Objetivo:

1. descobrir se a falha esta no codigo atual ou no ambiente publicado.

Acoes:

1. montar uma harness focada no botao `Atualizar` em `tests/check_user_location_ui.test.js`;
2. simular `runManualLocationRefreshSequence()` com a aplicacao destravada, atividades automaticas habilitadas e permissao de GPS valida;
3. fixar o estado remoto retornado por `fetchWebState(chave)` com ultima acao `checkout` e `current_local = 'Zona de CheckOut'`;
4. executar a variante 7A com `locationPayload = { matched: true, resolved_local: 'Escritorio Principal', status: 'matched' }`;
5. executar a variante 7B com `locationPayload = { matched: false, status: 'not_in_known_location', label: 'Localizacao nao Cadastrada', nearest_workplace_distance_meters: 180 }`;
6. verificar se o controller sempre chama `runAutomaticActivitiesIfNeeded(locationPayload)` depois do refresh manual;
7. verificar se o helper de decisao retorna `true` para ambos os casos quando a ultima atividade e `checkout`;
8. verificar se o helper continua retornando `false` quando a nova localizacao ainda e `Zona de CheckOut`.

Saida esperada:

1. um resultado binario claro:
2. falha local reprodutivel, que aponta para correcao de codigo;
3. ou comportamento local correto, que desloca a investigacao para deploy e bundle publicado.

## Fase 2 - Diagnostico do slice exato que decide a regra

Objetivo:

1. identificar o menor ponto de alteracao, caso os testes da Fase 1 falhem.

Roteiro de diagnostico:

1. se o controller do refresh manual nao chamar `runAutomaticActivitiesIfNeeded(locationPayload)` em todos os casos de payload valido, corrigir somente `runManualLocationRefreshSequence()` em `sistema/app/static/check/app.js`;
2. se o controller chamar corretamente, mas a acao automatica nao ocorrer para local conhecido, revisar apenas `shouldAttemptAutomaticLocationEvent()` em `sistema/app/static/check/automatic-activities.js`;
3. se o controller chamar corretamente, mas a acao automatica nao ocorrer para localizacao nao cadastrada proxima do trabalho, revisar apenas `shouldAttemptAutomaticNearbyWorkplaceCheckIn()`;
4. se ambos os helpers funcionarem isoladamente, revisar a ordem entre `fetchWebState()`, `applyHistoryState()` e a leitura de `current_local`, para confirmar se o estado remoto esta chegando coerente durante o refresh manual;
5. confirmar se o frontend continua confiando no `status` devolvido por `/api/web/check/location` e nao esta inferindo distancia por conta propria;
6. confirmar se a logica nao esta sendo interrompida por algum guard de desbloqueio, permissao, `chave` invalida ou desabilitacao de atividades automaticas.

Saida esperada:

1. um unico ponto de decisao identificado para correcao;
2. ou evidencias suficientes de que o codigo local ja esta correto e o problema e de deploy/publicacao.

## Fase 3 - Correcao minima e reversivel

Objetivo:

1. aplicar a menor mudanca possivel para fechar a Situação 7 sem tocar em fluxos estaveis.

Diretrizes de implementacao:

1. preferir reaproveitar a orquestracao atual do refresh manual;
2. evitar criar novas funcoes de submit automatico;
3. evitar duplicar regras entre `app.js` e `automatic-activities.js`;
4. se a correcao estiver no controller, limitar a mudanca a `runManualLocationRefreshSequence()`;
5. se a correcao estiver na decisao, limitar a mudanca a um helper de `automatic-activities.js`;
6. nao alterar contratos do backend nem payloads de `/api/web/check/location` se o bug puder ser resolvido apenas no frontend;
7. se a investigacao provar que o backend esta devolvendo um `status` errado para o caso de usuario proximo do trabalho, abrir uma segunda trilha separada de correcao e nao misturar isso com a primeira entrega do bug.

Resultado esperado:

1. o refresh manual passa a gerar check-in quando o usuario deixa a `Zona de CheckOut` apos ultimo check-out e cai em local conhecido ou proximo do trabalho;
2. as demais regras continuam identicas.

## Fase 4 - Regressao automatizada da matriz completa

Objetivo:

1. provar que a Situacao 7 foi corrigida sem quebrar as Situacoes 1 a 6.

Cobertura automatizada minima recomendada:

1. `tests/web_automatic_activities.test.js` deve cobrir a camada de decisao pura;
2. `tests/check_user_location_ui.test.js` deve cobrir a camada de orquestracao do botao `Atualizar`.

Casos obrigatorios da matriz:

1. Situacao 1: ultima atividade `checkin` + localizacao `Zona de CheckOut` ou `outside_workplace` -> check-out automatico;
2. Situacao 2: ultima atividade `checkout` + localizacao `Zona de CheckOut` ou `outside_workplace` -> nenhuma acao;
3. Situacao 3: ultima atividade `checkout` + local conhecido fora da `Zona de CheckOut` ou local nao cadastrado proximo do trabalho -> check-in automatico;
4. Situacao 4: ultima atividade `checkin` + mudanca de local conhecido -> novo check-in para atualizar localizacao;
5. Situacao 5: ultima atividade `checkin` + local nao cadastrado, mas ainda proximo do trabalho -> nenhuma acao, apenas exibicao de `Localizacao nao Cadastrada`;
6. Situacao 6: app em primeiro plano + ultimo evento `checkin` + botao `Atualizar` + mudanca de localizacao -> novo check-in de atualizacao;
7. Situacao 7A: app em primeiro plano + ultimo evento `checkout` + local anterior relevante `Zona de CheckOut` + botao `Atualizar` + novo local cadastrado fora da `Zona de CheckOut` -> check-in imediato;
8. Situacao 7B: app em primeiro plano + ultimo evento `checkout` + local anterior relevante `Zona de CheckOut` + botao `Atualizar` + novo local nao cadastrado, mas proximo do trabalho -> check-in imediato com `Localizacao nao Cadastrada`.

Controles negativos adicionais:

1. refresh manual com app travada nao deve acionar atividade automatica;
2. refresh manual com atividades automaticas desabilitadas nao deve acionar atividade automatica;
3. refresh manual com `chave` invalida nao deve acionar atividade automatica;
4. refresh manual que continua em `Zona de CheckOut` apos ultimo `checkout` nao deve acionar atividade automatica;
5. refresh manual que sai da `Zona de CheckOut`, mas cai em `outside_workplace`, nao deve acionar check-in.

Saida esperada:

1. um recorte de testes pequeno, rapido e diretamente ligado a regra quebrada.

## Fase 5 - Validacao de deploy e producao

Objetivo:

1. garantir que a correcao realmente chega a `https://www.tscode.com.br/checking/user`.

Checklist de deploy:

1. confirmar qual processo gera e publica os arquivos servidos em `checking/user`;
2. confirmar se o servidor serve diretamente `sistema/app/static/check` ou se existe etapa intermediaria de build/copia;
3. confirmar se o arquivo servido em producao corresponde ao `app.js` atualizado do repositorio;
4. invalidar cache de navegador, proxy reverso e qualquer CDN usada na frente do site;
5. confirmar se o deploy substitui de fato os assets antigos e nao preserva um bundle obsoleto;
6. repetir manualmente a Situacao 7 logo apos o deploy e comparar com o comportamento local esperado;
7. se o codigo local passar e producao continuar falhando, inspecionar especificamente divergencia entre artefato publicado e fonte versionada.

Saida esperada:

1. evidencia de que o comportamento corrigido esta em producao, e nao apenas no repositorio.

## 6. Arquivos provaveis de alteracao

Arquivos com maior probabilidade de toque, em ordem de prioridade:

1. `sistema/app/static/check/app.js`;
2. `sistema/app/static/check/automatic-activities.js`;
3. `tests/check_user_location_ui.test.js`;
4. `tests/web_automatic_activities.test.js`;
5. `docs/regras_checkin_checkout_webapp.txt`.

Arquivos que nao devem ser tocados sem evidencia concreta:

1. `sistema/app/static/check/web-client-state.js`;
2. endpoints de autenticacao web;
3. logica de formulario manual;
4. CSS e HTML da Checking Web;
5. calculo administrativo da distancia maxima, a menos que a investigacao mostre `status` incorreto vindo da API.

## 7. Riscos que o plano precisa evitar

1. quebrar o refresh manual da Situacao 6, que hoje ja tem comportamento esperado;
2. repetir check-out desnecessariamente quando o usuario continua na `Zona de CheckOut` apos ultimo `checkout`;
3. gerar check-in quando o backend devolve `outside_workplace`;
4. alterar a regra de `Localizacao nao Cadastrada` para casos da Situacao 5, que devem continuar sem check-out e sem check-in adicional;
5. introduzir caminhos diferentes para refresh manual e ciclo de vida da pagina, o que aumentaria a manutencao e o risco de divergencia futura;
6. mascarar um problema real de deploy com uma mudanca desnecessaria de codigo.

## 8. Criterios de aceite da correcao

A tarefa so deve ser considerada concluida quando todos os itens abaixo forem verdadeiros:

1. a Situacao 7 esta documentada no arquivo de regras;
2. existe cobertura automatizada para a variante 7A;
3. existe cobertura automatizada para a variante 7B;
4. as Situacoes 1 a 6 continuam cobertas e verdes;
5. o refresh manual continua usando a mesma orquestracao automatica ja existente;
6. a aplicacao faz check-in imediatamente quando o usuario deixa a `Zona de CheckOut` apos um ultimo `checkout`, tanto para local conhecido quanto para localizacao nao cadastrada proxima do trabalho;
7. a aplicacao continua sem agir quando o usuario permanece em `Zona de CheckOut` apos um ultimo `checkout`;
8. a aplicacao continua sem agir quando o backend diz que o usuario esta fora do ambiente de trabalho;
9. o comportamento validado localmente tambem e confirmado no ambiente publicado.

## 9. To-do list detalhada para implementar o plano

## Fase 1 - Diagnostico controlado

Resumo detalhado do que foi alterado nesta etapa: a regra textual da Situação 7 em `docs/regras_checkin_checkout_webapp.txt` foi refinada para separar explicitamente os dois ramos que a correção precisa preservar e testar. A descrição agora distingue a Variante 7A, em que o refresh manual sai da `Zona de CheckOut` para um local cadastrado diferente, e a Variante 7B, em que o refresh manual sai da `Zona de CheckOut`, não encontra um local exato, mas permanece dentro da faixa de proximidade do local de trabalho, o que deve resultar em check-in com `Localização não Cadastrada`. Essa alteração fecha a ambiguidade original da regra e transforma a Situação 7 em um contrato textual mais preciso para testes e deploy.

Também foi feito o diagnóstico direto do fluxo real em `sistema/app/static/check/app.js`. A revisão confirmou que `runManualLocationRefreshSequence()` continua resolvendo a posição atual com `measurementTrigger: 'manual_refresh'` e, quando recebe um `locationPayload` válido, chama `runAutomaticActivitiesIfNeeded(locationPayload)` imediatamente no mesmo caminho do botão `Atualizar`. Isso é importante porque elimina, nesta fase, a hipótese de que o refresh manual esteja completamente desconectado da rotina automática no código-fonte atual do repositório. O diagnóstico reforça que a investigação futura deve se concentrar em um edge case da decisão automática, no estado remoto retornado pela API ou em divergência entre o artefato publicado e a fonte atual.

Na camada de decisão, foi revisado `sistema/app/static/check/automatic-activities.js`. O comportamento confirmado foi o seguinte: `shouldAttemptAutomaticLocationEvent()` retorna `true` para local conhecido fora da `Zona de CheckOut` quando a última atividade registrada não é `checkin`, desde que a nova localização não seja igual à `current_local` remota; e `shouldAttemptAutomaticNearbyWorkplaceCheckIn()` retorna `true` quando `matched = false`, `status = 'not_in_known_location'`, a última atividade registrada é `checkout` e a localização automática derivada difere da `current_local` remota. Em outras palavras, a lógica local já contempla, em tese, tanto a saída da `Zona de CheckOut` para local conhecido quanto a saída para uma localização não cadastrada, mas ainda próxima do trabalho.

Para apoiar a próxima fase, foi consolidado o mapeamento mínimo dos sinais de `locationPayload` que controlam a Situação 7:

| Sinal | Papel no diagnóstico da Situação 7 |
| --- | --- |
| `matched` | Distingue o ramo de local conhecido (`true`) do ramo sem correspondência exata (`false`). |
| `status` | Diferencia `matched`, `not_in_known_location` e `outside_workplace`, que levam a decisões automáticas diferentes. |
| `resolved_local` | Identifica o local conhecido resolvido e permite detectar saída da `Zona de CheckOut`. |
| `label` | Fornece o rótulo usado no check-in automático quando não há correspondência exata, normalmente `Localização não Cadastrada`. |
| `nearest_workplace_distance_meters` | Funciona como evidência complementar do ramo “próximo do trabalho”, ainda que a decisão do frontend dependa principalmente de `status`. |

Também foi verificada a topologia de publicação da URL `https://www.tscode.com.br/checking/user`. Dentro da aplicação Python, `sistema/app/main.py` ainda consegue servir a Checking Web diretamente em `/user` a partir de `sistema/app/static/check` via `StaticFiles` quando a flag `serve_user_site_in_api` está habilitada. Porém, a rota pública de produção passa pelo reverse proxy definido em `deploy/nginx/checking-edge-routes.conf`, que publica `/checking/user` e encaminha o tráfego para o serviço `user-web` na porta `18082`. Esse serviço está definido em `docker-compose.websites.yml` e usa `deploy/docker/Dockerfile.user-web`, que simplesmente copia `sistema/app/static/check/` para `/usr/share/nginx/html/`. Portanto, existe uma etapa intermediária de empacotamento por imagem Docker e publicação via Nginx, mas não existe um build de frontend com transpile ou bundle separado: o conteúdo servido em produção é uma cópia estática direta do diretório `sistema/app/static/check` incluída na imagem do `user-web`.

Por fim, a revisão da cobertura atual confirmou que já existe um teste de controller em `tests/check_user_location_ui.test.js` garantindo que o refresh manual chama `runAutomaticActivitiesIfNeeded(locationPayload)` para o cenário equivalente à Situação 6, mas ainda não há cobertura específica para a Situação 7. Isso fecha a implementação desta fase com três conclusões objetivas: a regra textual foi esclarecida, o caminho de orquestração do botão `Atualizar` permanece ligado à rotina automática no código local e a topologia de deploy mostra que uma divergência entre repositório e site publicado continua sendo uma hipótese real para a falha observada em produção.

## Fase 2 - Testes focados da Situacao 7

Resumo detalhado do que foi alterado nesta etapa: a cobertura da Situação 7 foi transformada em testes executáveis nos dois níveis do slice que realmente controlam esse comportamento. Em `tests/check_user_location_ui.test.js`, foi adicionado um harness mais forte para o caminho do botão `Atualizar`, extraindo do `app.js` não apenas `runManualLocationRefreshSequence()`, mas também a rotina real `runAutomaticActivitiesIfNeeded()`. Esse harness fixa um estado remoto de referência com última ação `checkout` e `current_local = 'Zona de CheckOut'`, reaproveita a lógica real de `automatic-activities.js` para decidir quando agir e intercepta `submitAutomaticActivity()` para permitir afirmar, no teste, se houve check-in automático ou nenhuma ação.

Com esse harness, foram adicionados quatro cenários focados na orquestração do refresh manual. O primeiro cobre a Variante 7A, em que o refresh sai da `Zona de CheckOut` para um local conhecido e confirma um `checkin` automático imediato para o local resolvido. O segundo cobre a Variante 7B, em que o refresh sai da `Zona de CheckOut`, recebe `status = 'not_in_known_location'` e confirma um `checkin` automático com `Localização não Cadastrada`. Os dois controles negativos também foram adicionados no mesmo arquivo: permanência em `Zona de CheckOut` após último `checkout`, que deve resultar em nenhuma submissão automática, e transição para `outside_workplace`, que também deve manter o refresh sem nova atividade.

Na camada de decisão pura, `tests/web_automatic_activities.test.js` passou a explicitar o caso de saída da `Zona de CheckOut` para local conhecido após último `checkout`, verificando que `shouldAttemptAutomaticLocationEvent()` retorna `true` quando `current_local` remoto ainda é `Zona de CheckOut` e a nova localização conhecida é diferente. O caso de localização não cadastrada próxima do trabalho já existia em essência, mas foi mantido e renomeado para deixar explícito que ele representa precisamente a saída da `Zona de CheckOut` para o ramo `not_in_known_location`, com `current_local = 'Zona de CheckOut'`, o que fecha a leitura da Variante 7B também na camada de decisão.

Depois da implementação, foi executada a validação focada com `node --test tests/check_user_location_ui.test.js tests/web_automatic_activities.test.js`, e os 32 testes ficaram verdes. O resultado prático desta fase é importante: a base local agora tem cobertura explícita para a Situação 7A, para a Situação 7B e para os dois controles negativos do refresh manual, e essa cobertura confirma que o comportamento esperado já está representado corretamente no código atual do repositório. Com isso, a próxima fase deixa de ser uma correção presumida no escuro e passa a depender de eventual falha reproduzida por instrumentação adicional, divergência de estado remoto em produção ou diferença entre o artefato publicado e a fonte versionada.

## Fase 3 - Correcao minima de codigo, se os testes falharem

Resumo detalhado do que foi alterado nesta etapa: a premissa condicional desta fase foi reavaliada diretamente contra o estado atual do repositório depois da Fase 2. Como os testes focados da Situação 7 já haviam passado e o reread do slice confirmou que `runManualLocationRefreshSequence()` continua chamando `runAutomaticActivitiesIfNeeded(locationPayload)` no caminho do botão `Atualizar`, não houve evidência local que justificasse uma correção mínima em `sistema/app/static/check/app.js`. A implementação desta fase, portanto, consistiu em confirmar explicitamente que o controller já está alinhado com a regra esperada e que alterar esse ponto sem uma falha reproduzível introduziria risco desnecessário sobre um fluxo que hoje está correto no código-fonte local.

Na camada de decisão, a mesma revisão foi repetida sobre `sistema/app/static/check/automatic-activities.js`. O comportamento atual continua coerente com os cenários exercitados na Fase 2: `shouldAttemptAutomaticLocationEvent()` mantém o check-in para saída da `Zona de CheckOut` quando a última ação relevante foi `checkout` e a nova localização conhecida difere de `current_local`; `shouldAttemptAutomaticNearbyWorkplaceCheckIn()` continua cobrindo o ramo `matched = false` com `status = 'not_in_known_location'`; e o caminho negativo de permanência na `Zona de CheckOut` ou transição para `outside_workplace` segue bloqueando nova atividade. Com isso, esta fase foi concluída sem alterações em `automatic-activities.js`, porque a menor mudança correta, neste momento, é justamente não alterar a regra local enquanto não houver um teste vermelho ou uma reprodução concreta apontando defeito nesse helper.

Essa decisão também preserva os princípios de mínimo risco definidos no plano. Nenhum novo caminho de submit automático foi criado, nenhuma regra foi duplicada entre controller e helper, e nenhum fluxo adjacente de `startup`, `visibility`, `focus`, `pageshow`, fallback manual ou permissões de GPS foi tocado. Em vez de introduzir uma correção especulativa, a implementação desta etapa consolidou que o estado atual do repositório já representa a correção pretendida para a Situação 7 no frontend local, e que a próxima investigação útil deve migrar do código para instrumentação adicional, conferência do estado remoto retornado pela API ou divergência entre artefato publicado e fonte versionada.

Como validação final desta fase, a cobertura focada foi executada novamente com `node --test tests/check_user_location_ui.test.js tests/web_automatic_activities.test.js`, mantendo verdes os cenários adicionados para a Variante 7A, Variante 7B e os controles negativos. O resultado objetivo desta etapa é que nenhuma mudança de código foi necessária em `app.js` ou `automatic-activities.js`, e essa ausência de alteração passou a ser uma conclusão documentada e verificada, não uma suposição. Assim, a Fase 3 fecha o diagnóstico local afirmando que a correção mínima de código não se aplica ao estado atual do repositório e que qualquer próxima ação corretiva deverá partir de evidência nova fora desse slice já validado.

## Fase 4 - Regressao completa das Situacoes 1 a 7

Resumo detalhado do que foi alterado nesta etapa: a implementação da Fase 4 fechou as lacunas restantes da matriz regressiva das Situações 1 a 7 usando exatamente os dois níveis de teste definidos no plano: decisão pura em `tests/web_automatic_activities.test.js` e orquestração do botão `Atualizar` em `tests/check_user_location_ui.test.js`. Como as fases anteriores já haviam comprovado a Situação 7 no refresh manual e já existia cobertura parcial para checkout automático, check-in após checkout e não repetição de localização, esta etapa se concentrou em tornar a matriz explícita e completa, sem introduzir mudanças especulativas no código de produção.

Na suíte de decisão pura, foram adicionados os cenários que ainda faltavam para completar a leitura formal das Situações 4 e 5. O primeiro novo teste passou a afirmar que `shouldAttemptAutomaticLocationEvent()` retorna `true` quando o usuário já está em `checkin` e muda para outro local conhecido, cobrindo de forma explícita a Situação 4 como atualização legítima de localização. O segundo novo teste passou a afirmar que `shouldAttemptAutomaticNearbyWorkplaceCheckIn()` retorna `false` quando o usuário continua em estado de `checkin` e o backend devolve `not_in_known_location`, fechando o controle negativo da Situação 5, em que a aplicação deve apenas manter a exibição de proximidade ao trabalho sem disparar nova atividade. Com os testes que já existiam antes desta fase, a camada pura fica agora com cobertura explícita para: checkout automático em `Zona de CheckOut` e `outside_workplace` após `checkin` (Situação 1), ausência de ação quando o último estado já é `checkout` (Situação 2), check-in após `checkout` em local conhecido ou em localização próxima não cadastrada (Situação 3), atualização de local conhecido após `checkin` (Situação 4), ausência de nova ação em proximidade sem local exato durante `checkin` (Situação 5) e os ramos decisórios centrais da Situação 7.

Na suíte de controller/UI, a regressão foi fortalecida para o caminho completo do refresh manual. Foi adicionado um teste com o harness forte de `runManualLocationRefreshSequence()` mais `runAutomaticActivitiesIfNeeded()` que verifica a Situação 6 com submissão real: usuário já em `checkin`, mudança para outro local conhecido e confirmação de `submitAutomaticActivity({ action: 'checkin', local: ... })` no mesmo fluxo do botão `Atualizar`. Além disso, foram acrescentados os três controles negativos adicionais previstos no plano para a superfície do refresh manual: aplicação travada, em que o refresh sequer inicia a sequência; atividades automáticas desabilitadas, em que a medição pode ocorrer mas nenhuma atividade é enviada; e chave inválida, em que o fluxo não consulta o estado remoto nem tenta submeter nova atividade. Esses novos cenários se somam aos testes já existentes para a Variante 7A, Variante 7B, permanência em `Zona de CheckOut` e transição para `outside_workplace`, formando uma cobertura de orquestração mais completa e diretamente aderente à matriz das Situações 6 e 7.

Depois de completar essa matriz, a validação executável da fase foi rodada novamente com `node --test tests/check_user_location_ui.test.js tests/web_automatic_activities.test.js`. O resultado final ficou em 38 testes verdes, sem falhas, o que confirma que o slice atualmente coberto mantém compatibilidade com as Situações 1 a 7 dentro da superfície prevista para o frontend local. Também é relevante registrar que esta fase não exigiu alterações em `sistema/app/static/check/app.js` nem em `sistema/app/static/check/automatic-activities.js`: o trabalho foi inteiramente de regressão e explicitação da cobertura, o que reduz risco e torna mais claro que qualquer divergência residual passa a estar mais provavelmente em estado remoto, publicação ou artefato servido em produção, e não em ausência de testes para a regra local.

## Fase 5 - Validacao operacional e deploy

Resumo detalhado do que foi alterado nesta etapa: a Fase 5 foi usada para transformar a validação de deploy em evidência objetiva sobre o artefato realmente servido em `https://www.tscode.com.br/checking/user`, sem introduzir publicação desnecessária nem mutar estado real de produção sem credenciais operacionais apropriadas para esse fluxo. O primeiro passo executado foi rerodar a suíte focada do slice com `node --test tests/check_user_location_ui.test.js tests/web_automatic_activities.test.js`, mantendo 38 testes verdes. Isso preserva a base local validada antes de qualquer checagem operacional externa e confirma que o comportamento esperado das Situações 6 e 7 continua verde no repositório.

Em seguida, a implementação desta fase verificou diretamente o artefato público. A página `https://www.tscode.com.br/checking/user` foi consultada e respondeu com a superfície esperada da Checking Web, incluindo o formulário `id="checkForm"`, o que é coerente com o smoke público previsto em `deploy/nginx/verify_checking_edge_cutover.sh`. Depois disso, o arquivo `https://www.tscode.com.br/checking/user/app.js` foi baixado e comparado com `sistema/app/static/check/app.js`, e o mesmo foi feito com `https://www.tscode.com.br/checking/user/automatic-activities.js` versus `sistema/app/static/check/automatic-activities.js`. A comparação literal inicial acusou diferença de tamanho, mas a discrepância foi isolada como diferença de quebra de linha entre LF e CRLF. Após normalização de newline, os dois pares de arquivos bateram exatamente. Isso muda materialmente o diagnóstico operacional: a publicação atual do site público contém o mesmo conteúdo-fonte relevante do repositório para o slice do refresh manual e das decisões automáticas, o que enfraquece a hipótese de bundle antigo ou asset divergente em produção para este caso específico.

Também foi relido o caminho formal de deploy do site de check para registrar o estado operacional desta etapa. Em `scripts/deploy_launcher.py`, a ação `CHECK` continua definindo o redeploy do `user-web` via `docker compose -f docker-compose.websites.yml up -d --no-build --force-recreate user-web`, com smoke local em `http://127.0.0.1:18082/` procurando `id="checkForm"`. Em paralelo, `deploy/nginx/verify_checking_edge_cutover.sh` continua validando a presença pública da página em `/checking/user`. Como os assets públicos já coincidem com o conteúdo atual do repositório após normalização de newline, não houve necessidade técnica de disparar um novo deploy apenas para esta fase, e nenhuma invalidação de cache foi executada porque não apareceu evidência de cache servindo um asset antigo.

O ponto que permaneceu bloqueado nesta fase foi a validação manual ao vivo das Situações 6 e 7 em ambiente autenticado de produção. A partir deste workspace foi possível confirmar a disponibilidade da rota pública e a equivalência do asset publicado com o código local, mas não houve execução segura de um fluxo real com usuário autenticado, senha válida, permissão de geolocalização e deslocamento físico ou coordenadas homologadas em produção. Uma tentativa de smoke interativo controlado no browser integrado não se mostrou confiável o suficiente para substituir essa validação manual real, especialmente por limitações do ambiente quanto à simulação robusta de geolocalização e autenticação na própria superfície publicada. Por isso, esta fase registra um resultado operacional parcial e útil: o deploy público já está alinhado ao código local do slice investigado, porém a confirmação manual final em produção das Situações 6 e 7 continua pendente de execução em ambiente autorizado, com credenciais e contexto de localização apropriados.

## Fase 6 - Fechamento tecnico

Resumo detalhado do que foi alterado nesta etapa: a Fase 6 consolidou o fechamento tecnico do slice da Situacao 7 com uma reconciliacao final entre a documentacao de regras, a cobertura automatizada adicionada e o estado real dos arquivos tocados no repositorio. O primeiro passo foi conferir novamente `docs/regras_checkin_checkout_webapp.txt` contra o comportamento hoje exercitado pelos testes e pelo helper de decisao. Essa revisao confirmou que a regra textual permanece alinhada ao comportamento entregue: a Situacao 7 continua separada em Variante 7A, para saida da `Zona de CheckOut` rumo a um local cadastrado, e Variante 7B, para saida da `Zona de CheckOut` rumo ao ramo `not_in_known_location`, com check-in em `Localizacao nao Cadastrada`; os dois controles negativos do refresh manual tambem continuam documentados, cobrindo permanencia em `Zona de CheckOut` e transicao para `outside_workplace`. Em outras palavras, o contrato textual agora corresponde exatamente ao que a cobertura executavel protege no frontend local.

Na validacao executavel desta fase, a suite focada do slice foi rerodada com `node --test tests/check_user_location_ui.test.js tests/web_automatic_activities.test.js` e permaneceu verde com 38 testes aprovados. Para responder explicitamente ao item de fechamento sobre a qualidade da cobertura nova, esta etapa nao ficou apenas na passagem da suite com o codigo atual: foram executados dois ensaios de mutacao em copias temporarias dos arquivos relevantes, fora da worktree do repositorio. No primeiro probe, o ramo de `shouldAttemptAutomaticLocationEvent()` que hoje permite check-in automatico apos `checkout` em local conhecido foi forçado artificialmente a retornar `false`; com isso, falharam imediatamente tanto o teste puro `automatic check-in runs for a known location after checkout when leaving checkout zone` quanto o teste de orquestracao `manual refresh should submit automatic check-in after checkout when leaving checkout zone for a known location`. No segundo probe, o ramo de `shouldAttemptAutomaticNearbyWorkplaceCheckIn()` foi neutralizado para o caso `status = 'not_in_known_location'`; com isso, falharam o teste puro da Variante 7B e o teste de refresh manual para localizacao proxima nao cadastrada. Esses dois probes confirmam de forma objetiva que a cobertura adicionada nao esta apenas refletindo o estado atual do codigo: ela realmente detecta regressao quando os dois ramos centrais da Situacao 7 sao removidos e volta a passar com o codigo real do repositorio.

Tambem foi feita a conferencia final do escopo por meio de `git status` restrito aos caminhos do slice. Nessa superficie, os arquivos diretamente ligados ao trabalho permaneceram limitados a `docs/regras_checkin_checkout_webapp.txt`, `tests/check_user_location_ui.test.js`, `tests/web_automatic_activities.test.js` e este proprio `docs/temp_004.md`. `sistema/app/static/check/app.js` nao entrou no slice nesta fase de fechamento. `sistema/app/static/check/automatic-activities.js` apareceu marcado na worktree local, mas `git diff -- sistema/app/static/check/automatic-activities.js` nao retornou diff textual neste ambiente, de modo que esta etapa nao confirmou nenhuma nova alteracao produtiva adicional alem da superficie ja estabelecida nas fases anteriores. Assim, o fechamento tecnico registra que a correcao local permaneceu concentrada em documentacao e cobertura regressiva, sem expansao para mudancas secundarias fora do recorte necessario.

Por fim, o pequeno gotcha operacional registrado no fechamento e que a comparacao bruta entre asset publico e arquivo local pode gerar falso positivo de divergencia por causa de newline LF versus CRLF. Nesta investigacao, `app.js` e `automatic-activities.js` pareceram diferentes em uma checagem literal inicial por tamanho e comparacao direta, mas bateram exatamente depois da normalizacao de quebra de linha. Portanto, antes de concluir que producao esta servindo um bundle antigo, a verificacao correta precisa normalizar newline e so depois comparar o conteudo. Com isso, a Fase 6 fecha o slice com tres conclusoes tecnicas: a regra textual esta alinhada ao comportamento coberto, a cobertura adicionada realmente derruba quando as variantes 7A e 7B sao regressadas artificialmente, e a hipotese remanescente fora do codigo local continua sendo a validacao operacional autenticada em producao, nao ausencia de protecao automatizada ou falta de aderencia entre documentacao e comportamento local.