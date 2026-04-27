# Plano para corrigir a Situação 6 da Checking Web

## Contexto

- A regra da Situação 6 está definida em `docs/regras_checkin_checkout_webapp.txt`.
- A Checking Web fica em `sistema/app/static/check`.
- A aplicação já está em produção e funcionando corretamente; o objetivo é corrigir apenas a falha específica do botão `Atualizar` com o menor risco possível.

## Diagnóstico resumido

- A regra de negócio para decidir um novo check-in automático quando a última atividade foi um check-in e a localização mudou já existe no front-end.
- O módulo `sistema/app/static/check/automatic-activities.js` já contém a lógica que compara a localização atual com a localização registrada anteriormente.
- O problema está no fluxo acionado pelo botão `Atualizar`.
- Hoje, o caminho manual de atualização resolve a nova localização e atualiza a interface, mas não reaproveita a mesma orquestração de atividades automáticas usada quando:
  - a aplicação é aberta;
  - a página é recarregada;
  - a aplicação volta do segundo plano para o primeiro plano.
- Por isso, na Situação 6, a localização exibida muda, mas o novo check-in não é realizado.

## Objetivo da correção

Garantir que, ao clicar no botão `Atualizar`, se todas as condições da Situação 6 forem verdadeiras, a aplicação realize automaticamente um novo check-in apenas para atualizar a localização do usuário na API.

## Diretrizes da alteração

1. Corrigir apenas o fluxo da aplicação web `Checking Web`.
2. Evitar alterações desnecessárias em backend, banco de dados, payloads e contratos da API.
3. Reaproveitar a lógica já consolidada de atividades automáticas, em vez de duplicar regras em outro ponto do código.
4. Preservar o comportamento atual dos demais gatilhos automáticos já funcionais.
5. Fazer uma alteração mínima, reversível e com cobertura de teste específica para a regressão.

## Plano de alteração

### 1. Confirmar e isolar o ponto exato da falha

- Revisar o fluxo do botão `Atualizar` em `sistema/app/static/check/app.js`.
- Confirmar que ele chama apenas a atualização da localização e não executa a rotina que avalia check-in/check-out automáticos.
- Confirmar que os fluxos de startup, reload e retorno ao primeiro plano já chamam essa rotina após atualizar a localização.

### 2. Reutilizar a orquestração já existente

- Fazer o fluxo manual do botão `Atualizar` passar pela mesma avaliação automática usada nos demais gatilhos de ciclo de vida.
- Evitar reimplementar a regra da Situação 6 em um novo trecho isolado.
- Se necessário, extrair um helper pequeno e local apenas para reduzir duplicação entre fluxos muito parecidos.

### 3. Preservar a experiência atual do usuário

- Manter o bloqueio de interação e o estado de loading do botão durante a atualização.
- Preservar a atualização da localização na interface mesmo quando nenhuma atividade automática for executada.
- Ajustar a mensagem final apenas se isso for necessário para refletir corretamente quando houve check-in automático após o refresh manual.

### 4. Cobrir a correção com testes de regressão

- Adicionar teste específico para o caminho do botão `Atualizar`.
- Garantir que esse teste cubra a Situação 6 com foco no comportamento observado pelo usuário.
- Evitar criar testes amplos demais; a cobertura deve ser focada no fluxo manual recém-corrigido.

### 5. Validar que não houve regressão

- Executar os testes atuais do módulo de atividades automáticas.
- Executar os testes da UI de localização da Checking Web.
- Verificar manualmente os cenários essenciais antes de homologar.

## To-do list cautelosa e minuciosa

## Fase 1 - Preparação e confirmação do escopo

Status: concluída em 2026-04-27.

- [x] Confirmar novamente a regra funcional da Situação 6 no arquivo `docs/regras_checkin_checkout_webapp.txt`.
- [x] Confirmar no código que a regra de decisão automática já existe e não precisa ser recriada.
- [x] Confirmar no código que o botão `Atualizar` segue um fluxo diferente dos gatilhos de startup/foreground.
- [x] Delimitar o escopo da correção ao front-end da Checking Web.
- [x] Evitar qualquer alteração em backend ou contratos de API nesta fase.

Critério de saída da fase:
O defeito deve estar claramente isolado como uma falha de integração do fluxo manual de atualização.

Resultado da execução da Fase 1:

- A regra funcional da Situação 6 foi confirmada em `docs/regras_checkin_checkout_webapp.txt`: se a aplicação já estiver em primeiro plano, a última atividade for um check-in, `Atividades Automáticas` estiver marcada e a nova localização for diferente da localização do check-in anterior, a aplicação deve realizar um novo check-in apenas para atualizar a localização.
- A regra de decisão automática já existe no front-end em `sistema/app/static/check/automatic-activities.js`, na função `shouldAttemptAutomaticLocationEvent`, que compara a localização resolvida com a localização registrada anteriormente e evita repetição desnecessária no mesmo local.
- Os gatilhos já funcionais de atualização da aplicação passam por `runLifecycleUpdateSequence` em `sistema/app/static/check/app.js`, que atualiza histórico, atualiza localização e, se `Atividades Automáticas` estiver habilitada, chama `runAutomaticActivitiesIfNeeded`.
- O botão `Atualizar` segue um fluxo diferente em `sistema/app/static/check/app.js`: o clique chama `runManualLocationRefreshSequence`, e esse fluxo atualmente executa apenas `resolveCurrentLocation`, sem chamar `runAutomaticActivitiesIfNeeded` depois da nova localização.
- O envio da atividade automática já usa os endpoints existentes da aplicação web em `sistema/app/static/check/app.js`, com `submitEndpoint = /api/web/check` e `stateEndpoint = /api/web/check/state`; portanto, nesta fase, não há evidência de necessidade de mudança em backend, banco de dados ou contratos de API.
- O escopo da correção fica delimitado, neste momento, ao front-end da Checking Web, com foco principal em `sistema/app/static/check/app.js` e, no máximo, testes associados ao fluxo manual de atualização.
- Conclusão da Fase 1: o critério de saída foi atendido. O defeito está isolado como uma falha de integração no fluxo manual do botão `Atualizar`, e não como ausência de regra de negócio ou limitação de backend.

## Fase 2 - Blindagem por teste antes da correção

Status: concluída em 2026-04-27 para a blindagem inicial da falha principal.

1. Identificar o melhor arquivo de teste para cobrir o fluxo manual do botão `Atualizar`.
2. Criar um teste de regressão que represente a Situação 6.
3. Garantir que o teste cubra, no mínimo, este cenário principal:
   - última atividade = check-in;
   - atividades automáticas habilitadas;
   - atualização manual de localização;
   - localização nova diferente da anterior;
   - novo check-in automático disparado.
4. Cobrir também cenários negativos próximos para reduzir risco de regressão:
   - mesma localização nao deve gerar novo check-in;
   - atividades automáticas desligadas nao devem gerar novo check-in;
   - ausência de localização válida nao deve gerar submissão automática;
   - cenários já existentes de checkout automático nao devem ser impactados.
5. Confirmar que o teste novo falha antes da correção, quando isso for tecnicamente viável no harness existente.

Critério de saída da fase:
Existe pelo menos um teste de regressão focado que protege exatamente a falha reportada.

Resultado da execução da Fase 2:

- O melhor arquivo de teste para cobrir a falha foi identificado como `tests/check_user_location_ui.test.js`, porque o defeito está no caminho de orquestração do botão `Atualizar` dentro da UI da Checking Web, e não na regra pura isolada.
- Foi mantido como referência que a regra pura de atividades automáticas já possui cobertura dedicada em `tests/web_automatic_activities.test.js`, inclusive com cenários negativos relevantes como mudança de localização obrigatória e não repetição de check-in no mesmo local.
- Foi adicionado ao arquivo `tests/check_user_location_ui.test.js` um harness mínimo para o fluxo `runManualLocationRefreshSequence` e o teste de regressão `manual refresh should evaluate automatic activities after a changed location during an active check-in`.
- Esse teste representa a Situação 6 no ponto exato da falha: o refresh manual atualiza a localização para um local diferente durante um contexto em que deveria haver avaliação automática subsequente.
- A validação pré-correção foi executada com `node --test tests/check_user_location_ui.test.js`.
- Resultado da validação pré-correção: 18 testes passaram e 1 falhou.
- A falha observada foi a esperada para esta fase: o array de chamadas de `runAutomaticActivitiesIfNeeded` permaneceu vazio, confirmando que o fluxo manual atual não chama a orquestração automática após resolver a nova localização.
- A cobertura negativa mais próxima do núcleo da regra já está presente em `tests/web_automatic_activities.test.js`; a expansão de cenários negativos específicos do caminho manual de refresh será mais útil na Fase 3, porque antes da correção qualquer asserção adicional sobre "não disparar" nesse fluxo seria vacuamente verdadeira enquanto nenhuma avaliação automática é chamada.
- Conclusão da Fase 2: o critério de saída foi atendido. Já existe pelo menos um teste de regressão focado, localizado no ponto correto da aplicação, e sua falha antes da correção foi confirmada com execução real.

## Fase 3 - Implementação mínima da correção

Status: concluída em 2026-04-27.

1. Alterar o fluxo manual do botão `Atualizar` em `sistema/app/static/check/app.js`.
2. Fazer esse fluxo reutilizar a rotina já existente de avaliação de atividades automáticas após a atualização da localização.
3. Garantir que a checagem continue respeitando as guardas existentes:
   - aplicação desbloqueada;
   - chave válida;
   - permissão de localização concedida;
   - checkbox de atividades automáticas marcada.
4. Evitar duplicação de chamada ao endpoint de registro.
5. Garantir que o fluxo continue realizando apenas uma ação automática por atualização manual.
6. Preservar os estados de loading, bloqueio e mensagens do formulário.
7. Ajustar a mensagem final somente se necessário para não ocultar um check-in automático efetivamente realizado.

Critério de saída da fase:
O botão `Atualizar` passa a disparar o novo check-in automático na Situação 6, sem alterar o comportamento dos demais fluxos.

Resultado da execução da Fase 3:

- O fluxo manual do botão `Atualizar` foi alterado em `sistema/app/static/check/app.js`, na função `runManualLocationRefreshSequence`.
- A função passou a capturar o `locationPayload` retornado por `resolveCurrentLocation` e, quando houver payload válido, passou a chamar `runAutomaticActivitiesIfNeeded(locationPayload)` logo em seguida.
- A correção reaproveita integralmente a orquestração automática já existente, sem duplicar regra de negócio nem criar um fluxo alternativo de submissão.
- As guardas existentes foram preservadas: o fluxo manual continua retornando imediatamente quando a aplicação está bloqueada por interação ou quando não está desbloqueada; além disso, a própria rotina `runAutomaticActivitiesIfNeeded` continua aplicando as guardas internas de `Atividades Automáticas`, permissão de GPS, sessão desbloqueada e chave válida.
- Não houve duplicação de chamada ao endpoint de registro: a submissão automática continua centralizada em `submitAutomaticActivity`, que usa o endpoint já existente `/api/web/check`.
- O fluxo continua limitado a no máximo uma atividade automática por atualização manual, porque `runAutomaticActivitiesIfNeeded` retorna assim que executa a primeira ação aplicável.
- Os estados de loading e bloqueio do formulário foram preservados, porque a correção manteve o uso de `runWithLockedUserInteraction` e não alterou o controle de `locationRefreshLoading` dentro de `resolveCurrentLocation`.
- A estratégia de mensagem final foi mantida com alteração mínima: quando não houver atividade automática, permanece a mensagem de conclusão da atualização de localização; quando houver atividade automática, a própria submissão automática pode sobrescrever a mensagem final com o status já existente de check-in/check-out automático.
- A regressão criada na Fase 2 passou após a correção.
- Validação focal executada após a implementação:
   - `node --test tests/check_user_location_ui.test.js` -> 19 testes passaram.
   - `node --test tests/web_automatic_activities.test.js` -> 8 testes passaram.
- Conclusão da Fase 3: o critério de saída foi atendido. O botão `Atualizar` agora reaproveita a mesma orquestração automática necessária para cobrir a Situação 6, sem mudar a fonte de verdade da regra nem ampliar o escopo para backend.

## Fase 4 - Validação técnica local

Status: concluída em 2026-04-27.

1. Executar os testes do módulo `web_automatic_activities`.
2. Executar os testes da UI de localização da Checking Web.
3. Confirmar que o teste novo da Situação 6 passa.
4. Revisar o diff final para garantir que a alteração foi pequena e restrita ao problema.

Critério de saída da fase:
Todos os testes relevantes passam e o diff permanece pequeno, localizado e coerente.

Resultado da execução da Fase 4:

- A suíte `tests/web_automatic_activities.test.js` foi executada novamente com `node --test tests/web_automatic_activities.test.js`.
- Resultado: 8 testes passaram e 0 falharam.
- A suíte `tests/check_user_location_ui.test.js` foi executada novamente com `node --test tests/check_user_location_ui.test.js`.
- Resultado: 19 testes passaram e 0 falharam.
- O teste novo da Situação 6 passou dentro da suíte da UI, confirmando que o caminho manual do botão `Atualizar` agora chama a avaliação automática após resolver a nova localização.
- O diff de código final foi revisado apenas nos arquivos diretamente ligados à correção.
- O arquivo `sistema/app/static/check/app.js` recebeu uma alteração pequena e localizada: o refresh manual passou a guardar o `locationPayload` retornado e a chamar `runAutomaticActivitiesIfNeeded(locationPayload)` quando houver payload válido.
- O arquivo `tests/check_user_location_ui.test.js` recebeu apenas o harness mínimo e o teste de regressão focado no fluxo manual da Situação 6.
- O arquivo `docs/temp_002.md` permanece como arquivo novo de acompanhamento do plano e das fases executadas.
- A checagem de status final dos arquivos envolvidos confirmou o seguinte escopo:
   - `M sistema/app/static/check/app.js`
   - `M tests/check_user_location_ui.test.js`
   - `?? docs/temp_002.md`
- Conclusão da Fase 4: o critério de saída foi atendido. Todos os testes relevantes passaram, o teste novo da Situação 6 está verde, e a alteração permaneceu pequena, localizada e coerente com o problema original.

## Fase 5 - Validação funcional manual

Status: concluída em 2026-04-27 com homologação local controlada em navegador real via Playwright.

1. Testar manualmente a Situação 6 com um usuário real de homologação.
2. Validar que a localização na tela muda e que um novo check-in é realmente enviado quando o local muda.
3. Validar que o mesmo local nao gera check-in duplicado.
4. Validar que zona de checkout continua produzindo checkout automático quando aplicável.
5. Validar que localização não cadastrada próxima ao local de trabalho continua obedecendo as regras atuais.
6. Validar que ausência de permissão de GPS e precisão insuficiente continuam com o comportamento atual.

Critério de saída da fase:
O cenário corrigido funciona na prática e não há regressão visível nos comportamentos já estabilizados.

Resultado da execução da Fase 5:

- A validação funcional foi concluída em ambiente local controlado com navegador real via Playwright, porque não havia credenciais de um usuário real de homologação em produção disponíveis nesta sessão.
- Para validar especificamente a Situação 6 e os cenários adjacentes do botão `Atualizar`, foi criado e executado o script `scripts/homologate_temp_009_phase5_manual_refresh.py`.
- O script gerou o relatório `docs/temp_009_phase5_manual_refresh_report.json` e validou com sucesso os quatro cenários abaixo em uma instância preview local da Checking Web:
   - mudança de localização após check-in ativo gera novo check-in automático;
   - mesma localização após refresh manual não gera check-in duplicado;
   - zona de checkout continua gerando checkout automático;
   - localização próxima, não cadastrada e fora da tolerância do local não altera indevidamente o check-in ativo.
- Resultado observado no cenário principal da Situação 6:
   - estado inicial: `current_local = Phase5 Sit6 Base` e `last_checkin_at = 2026-04-27T12:36:21.582818`;
   - estado final após `Atualizar`: `current_local = Phase5 Sit6 Portaria` e `last_checkin_at = 2026-04-27T12:36:30.490000`;
   - estado visual: `locationValue = Phase5 Sit6 Portaria` e mensagem `Check-In automático concluído.`.
- Resultado observado no cenário negativo de mesma localização:
   - `current_local` permaneceu `Phase5 Sit6 Base`;
   - `last_checkin_at` permaneceu inalterado;
   - não houve duplicação de check-in.
- Resultado observado no cenário de zona de checkout:
   - o estado foi de `checkin` em `Phase5 Checkout Base` para `checkout` em `Zona de CheckOut`;
   - a UI apresentou `Zona de Check-Out` e mensagem `Check-Out automático concluído.`.
- Resultado observado no cenário de localização não cadastrada próxima:
   - o estado permaneceu com `current_action = checkin` e `current_local = Phase5 Nearby Base`;
   - `last_checkin_at` e `last_checkout_at` permaneceram inalterados;
   - a UI apresentou `Localização não Cadastrada`, sem disparar evento automático indevido.
- Para complementar os itens 5 e 6 desta fase, também foi executado novamente o script já existente `scripts/homologate_temp_008_phase6.py`.
- Esse script gerou o relatório `docs/temp_008_phase6_report.json` e confirmou que os cenários de `Precisao insuficiente` e `Sem Permissão` continuam preservados, tanto com `Atividades Automáticas` desligada quanto ligada nos casos previstos pelo roteiro.
- Com isso, o critério de saída da Fase 5 foi atendido: o cenário corrigido funciona na prática no fluxo manual do botão `Atualizar`, e os comportamentos estabilizados mais próximos permaneceram sem regressão visível na homologação local controlada.

## Fase 6 - Homologação e liberação controlada

Status: concluída em 2026-04-27 com liberação preparada e retenção explícita da promoção para produção até autorização manual.

1. Homologar com cuidado em ambiente controlado.
2. Observar se cada clique em `Atualizar` gera no máximo uma atividade automática.
3. Confirmar se o histórico e a localização exibida permanecem consistentes após a atualização.
4. Só promover a alteração para produção após confirmação explícita da correção e ausência de regressões.

Critério de saída da fase:
A correção está homologada com segurança e pronta para liberação.

Resultado da execução da Fase 6:

- A homologação controlada foi consolidada a partir dos artefatos executados nas Fases 4 e 5, sem ampliar o escopo da correção nem introduzir alterações adicionais em backend, banco ou contratos.
- O comportamento de `um clique no botão Atualizar -> no máximo uma atividade automática` foi confirmado com evidência objetiva no banco preview `preview_phase5_manual_refresh.db`, usando os usuários do roteiro `T9A1`, `T9B2`, `T9C3` e `T9D4`.
- Resultado da contagem de eventos em `checkinghistory` após a execução do roteiro `scripts/homologate_temp_009_phase5_manual_refresh.py`:
   - `T9A1`: 2 eventos totais (`check-in -> check-in`), confirmando exatamente um novo check-in automático no cenário principal da Situação 6;
   - `T9B2`: 1 evento total (`check-in`), confirmando ausência de duplicação no cenário de mesma localização;
   - `T9C3`: 2 eventos totais (`check-in -> check-out`), confirmando exatamente um checkout automático no cenário de zona de checkout;
   - `T9D4`: 1 evento total (`check-in`), confirmando ausência de evento indevido no cenário de localização próxima não cadastrada.
- Essa evidência fecha o item mais crítico da fase: em todos os cenários homologados, cada refresh manual gerou no máximo uma atividade automática, e apenas quando a regra de negócio exigia isso.
- A consistência entre histórico e localização exibida também foi confirmada nos relatórios gerados:
   - `docs/temp_009_phase5_manual_refresh_report.json` mostrou alinhamento entre `current_local`, timestamps finais e `locationValue` da UI nos cenários de novo check-in, mesma localização, checkout zone e localização não cadastrada;
   - `docs/temp_008_phase6_report.json` confirmou preservação dos comportamentos estabilizados de `Precisao insuficiente` e `Sem Permissão`.
- A liberação permaneceu controlada: a alteração não foi promovida para produção nesta fase, porque o próprio critério do plano exige confirmação explícita antes da promoção e essa autorização não fazia parte desta execução.
- Com isso, o critério de saída da Fase 6 foi atendido: a correção está homologada com segurança em ambiente controlado, a mudança está pronta para liberação, e a promoção para produção fica corretamente retida até decisão explícita.

## Resultado esperado ao final

- A regra da Situação 6 passa a funcionar também no botão `Atualizar`.
- A correção permanece pequena e segura.
- A lógica de negócio continua centralizada.
- O risco de regressão fica reduzido por teste focado e validação manual objetiva.