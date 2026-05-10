# Plano da Correcao - Persistencia indevida de `Localizacao nao Cadastrada` no fluxo automatico da Web

## Objetivo

Resolver com seguranca o problema observado em producao no qual a aplicacao Web pode registrar `check-in` com `local = "Localizacao nao Cadastrada"` mesmo quando o sistema de poligonos esta operacional e a plataforma, no restante, funciona corretamente.

A intencao deste plano e:

1. corrigir o comportamento no workspace com o menor raio de impacto possivel;
2. validar a correcao com regressao automatizada e homologacao dirigida;
3. preparar um deploy futuro para producao sem misturar esta correcao com mudancas maiores e nao relacionadas.


## Diagnostico confirmado

### 1. O algoritmo poligonal nao apareceu como causa raiz

As validacoes feitas mostraram que:

- a logica de matching poligonal em `sistema/app/services/location_matching.py` esta operacional;
- no ambiente de producao, o poligono de `Escritorio Principal` existe, esta salvo com lista valida de vertices e foi reconhecido corretamente em testes dirigidos com pontos internos;
- a propria producao possui varios eventos Web recentes com `local = "Escritorio Principal"`, provando que o fluxo de reconhecimento funciona em casos reais.

Conclusao:

- nao ha evidencia, neste incidente, de defeito estrutural na regra "qualquer ponto dentro do poligono deve identificar a localizacao".

### 2. O problema real encontrado esta no fluxo automatico da Web

Foi identificado um caminho de codigo no frontend Web em que:

1. a API de localizacao responde `matched = false` com `status = "not_in_known_location"`;
2. as atividades automaticas continuam aptas a executar um `check-in` automatico;
3. a resolucao do `local` automatico cai no fallback textual `Localizacao nao Cadastrada`;
4. esse valor e entao submetido para `/api/web/check`.

Em termos praticos, o problema confirmado e:

- o sistema nao esta necessariamente "errando o poligono";
- o sistema esta permitindo persistir um `local` sintetico de falha de reconhecimento como se fosse um local operacional valido.

### 3. Evidencia adicional relevante de producao

A analise dos dados reais mostrou que:

- `Localizacao nao Cadastrada` aparece tanto em eventos `web` quanto em eventos `mobile`;
- no recorte recente inspecionado, o volume de matches corretos para `Escritorio Principal` e muito maior do que o volume de casos `Localizacao nao Cadastrada`;
- ha pares operacionais do tipo:
  - `checkout` em `Fora do Local de Trabalho` ou `Aplicativo`;
  - poucos segundos depois, `checkin` em `Localizacao nao Cadastrada`;
- esse padrao e altamente compativel com reacao automatica, nao com submissao manual consciente do usuario.


## Causa raiz recomendada para tratar

### Causa raiz principal

O fluxo automatico da Web esta aceitando `status = "not_in_known_location"` como gatilho para um `check-in` automatico "por proximidade", e a funcao que resolve o `local` automatico permite cair em:

- `resolved_local`, quando ha match valido;
- `label`, quando nao ha `resolved_local`;
- `AUTOMATIC_UNREGISTERED_CHECKIN_LOCATION`, quando nao ha nenhum dos dois.

Essa cadeia permite que um rótulo de falha de localizacao vire valor persistido em `forms_submissions.local` e `check_events.local`.

### Causa secundaria de risco operacional

O workspace atual esta mais avancado do que a producao no fluxo de projetos da Web:

- no workspace, o backend de localizacao Web ja usa a ideia de uniao de projetos;
- em producao, o `web_check.py` ainda filtra localizacoes apenas por `user.projeto` no singular;
- em producao, o banco ainda nao possui `user_project_memberships`.

Isto nao apareceu como causa raiz do caso do `Escritorio Principal`, porque essa localizacao em producao ja esta ligada a `P80`, `P82` e `P83`.

Mesmo assim, essa divergencia e importante para rollout:

- ela aumenta o risco de um deploy "arrastar" mudancas nao relacionadas;
- ela exige que esta correcao seja tratada como hotfix isolado, e nao como parte de um pacote maior.


## Invariantes que a correcao precisa respeitar

1. `Localizacao nao Cadastrada` pode continuar existindo como mensagem de interface ou estado diagnostico.

2. `Localizacao nao Cadastrada` nao deve mais ser persistida como `local` operacional via fluxo automatico da Web.

3. O matching poligonal nao deve ser reescrito nem afrouxado neste hotfix, porque ele ja foi validado e esta funcionando.

4. O `check-out` automatico por `outside_workplace` deve continuar funcionando.

5. O `check-in` automatico para localizacao realmente reconhecida deve continuar funcionando.

6. O fluxo manual com selecao explicita de um local cadastrado deve continuar funcionando.

7. O hotfix nao deve depender de mudanca de schema de banco, nem de migracao de dados.

8. O hotfix nao deve se misturar com a Modificacao 6 ou com rollout de memberships multi-projeto.


## Escopo recomendado

### Em escopo

1. Corrigir a decisao das atividades automaticas da Web para impedir `check-in` automatico quando o status de localizacao for `not_in_known_location`.

2. Blindar a resolucao do `local` automatico para nunca usar rótulos sinteticos de falha como valor operacional submetido.

3. Adicionar regressao automatizada para provar que:
   - localizacao reconhecida continua gerando `check-in` automatico;
   - `outside_workplace` continua podendo gerar `check-out` automatico;
   - `not_in_known_location` nao gera mais `check-in` automatico;
   - `Localizacao nao Cadastrada` nao volta a ser gravada pela Web como `local`.

4. Fazer homologacao dirigida com cenarios de geolocalizacao internos ao poligono e cenarios sem match.

### Fora de escopo para este hotfix

1. Reescrever a geometria de poligonos.

2. Alterar tolerancias, thresholds ou catalogo de localizacoes em producao.

3. Introduzir migracoes de memberships multi-projeto no mesmo pacote.

4. Corrigir o app mobile nativo no mesmo commit, salvo se a equipe decidir abrir um segundo pacote dedicado e isolado.

5. Redesenhar a UX de localizacao da Web alem do necessario para remover a persistencia indevida.


## Estrategia recomendada

### Direcao principal

Aplicar um hotfix de baixo risco no frontend Web para que o sistema automatico so submeta `check-in` quando houver localizacao operacional valida.

### Regra funcional desejada apos a correcao

1. Se `locationPayload.matched === true` e houver `resolved_local` valido:
   - o fluxo automatico pode continuar executando `check-in` ou `check-out` conforme as regras existentes.

2. Se `locationPayload.status === "outside_workplace"`:
   - o `check-out` automatico continua permitido conforme a regra atual.

3. Se `locationPayload.status === "not_in_known_location"`:
   - o sistema pode continuar mostrando o estado ao usuario;
   - o sistema nao deve mais transformar esse estado em `check-in` automatico.

4. Se a aplicacao precisar no futuro de uma semantica de "proximo ao ambiente de trabalho":
   - isso deve nascer como conceito novo e explicito;
   - nao deve reutilizar `Localizacao nao Cadastrada` como `local` de negocio.


## Plano detalhado de execucao

### Fase 0 - Isolar o hotfix antes de qualquer implementacao

1. Confirmar qual base de codigo sera usada como ponto de partida para a correcao.

Recomendacao:

- criar a correcao em branch de hotfix isolada;
- evitar misturar esse trabalho com qualquer branch em andamento de multi-projeto, transporte ou rollout maior.

2. Fazer um diff orientado entre workspace atual e producao apenas nas areas abaixo:

- `sistema/app/static/check/app.js`;
- `sistema/app/static/check/automatic-activities.js`;
- `sistema/app/routers/web_check.py`;
- `sistema/app/services/location_matching.py`.

Objetivo:

- garantir que o deploy futuro nao arraste, sem querer, diferencas de producao nao relacionadas a este incidente.

3. Definir explicitamente o criterio de "patch minima":

- sem migration;
- sem alterar contrato do endpoint de localizacao;
- sem tocar no algoritmo poligonal;
- sem alterar CRUD de localizacoes;
- sem alterar dados de producao.


### Fase 1 - Congelar o comportamento atual com testes de regressao

Antes de mudar o codigo, criar protecao automatizada para o comportamento desejado.

#### 1.1 Testes de comportamento automatico da Web

Adicionar cobertura para estes cenarios:

1. `matched = true` com `resolved_local = "Escritorio Principal"`:
   - quando o usuario esta apto para automacao e a ultima acao permite `check-in`, o `check-in` automatico continua acontecendo;
   - o `local` persistido continua sendo o `resolved_local` reconhecido.

2. `status = "outside_workplace"`:
   - quando a ultima acao registrada for `checkin`, o `check-out` automatico continua acontecendo;
   - o `local` persistido continua sendo o local automatico de checkout ja previsto pelo sistema.

3. `status = "not_in_known_location"`:
   - o sistema nao deve executar `check-in` automatico;
   - o sistema nao deve submeter `Localizacao nao Cadastrada`;
   - o usuario pode continuar vendo a mensagem de interface, mas nao deve haver persistencia indevida.

4. `status = "accuracy_too_low"`:
   - nao deve existir `check-in` automatico;
   - o fluxo manual/fallback continua sendo a unica alternativa.

#### 1.2 Testes de nao regressao do matching poligonal

Manter ou reforcar os cenarios ja existentes para:

1. ponto interno ao poligono de `Escritorio Principal`;
2. `resolved_local` correto quando o ponto esta dentro da area;
3. `not_in_known_location` apenas quando realmente nao houve match;
4. `outside_workplace` apenas quando a distancia excede o threshold de checkout.

#### 1.3 Teste de persistencia proibida

Adicionar um teste de integracao com criterio explicito:

- apos a correcao, o fluxo Web automatico nao pode produzir `forms_submissions.local = "Localizacao nao Cadastrada"`.

Essa assercao e importante porque ela protege exatamente o incidente encontrado em producao.


### Fase 2 - Corrigir a decisao de automacao

Esta e a fase principal do hotfix.

#### 2.1 Remover o `check-in` automatico para `not_in_known_location`

Regra recomendada:

- `shouldAttemptAutomaticNearbyWorkplaceCheckIn()` deve deixar de aprovar `check-in` automatico quando `locationPayload.status === "not_in_known_location"`.

Decisao preferencial:

- desativar por completo esse caminho automatico na Web neste hotfix.

Motivo:

- e o comportamento confirmado como gerador do erro;
- e a menor mudanca com melhor relacao risco/beneficio;
- preserva todo o resto do fluxo automatico ja comprovado.

#### 2.2 Impedir fallback de rótulo sintetico como local operacional

Mesmo depois da mudanca anterior, a funcao que resolve o local automatico deve ser endurecida.

Regra recomendada:

- `resolveAutomaticCheckInLocation()` nao deve aceitar `label` generico de falha como valor apto para submit automatico;
- se nao houver `resolved_local` operacional valido, a funcao deve retornar estado nao submetivel;
- o chamador deve abortar o submit automatico.

Observacao:

- esta blindagem e "defense in depth";
- ela evita que um ajuste futuro reabra o mesmo bug por outro caminho.

#### 2.3 Manter a UX de leitura, nao de persistencia

O estado `Localizacao nao Cadastrada` pode continuar sendo usado para:

- texto exibido na UI;
- diagnostico do usuario;
- decisao de permitir ou nao fluxo manual.

Mas nao deve mais ser usado para:

- `local` em `submitEndpoint`;
- `local` em atividades automaticas;
- valor operacional em historico de presenca.


### Fase 3 - Blindar o submit da Web contra valores sinteticos

Esta fase e recomendada como reforco adicional, desde que seja implementada com cuidado para nao quebrar fluxos validos.

#### 3.1 Reforco no frontend Web

Antes de submeter automaticamente ou manualmente:

- validar que o `local` resultante nao e um placeholder sintetico de falha;
- se for placeholder, abortar o submit e manter apenas a mensagem de interface.

#### 3.2 Reforco opcional no backend Web

Opcao a avaliar com cautela:

- adicionar guard rail no endpoint Web de submit para rejeitar `local = "Localizacao nao Cadastrada"` quando a origem for Web.

Recomendacao:

- tratar isso como opcional neste hotfix;
- so aplicar se a equipe conseguir garantir que nao ha integracoes legitimas dependentes desse valor.

Motivo da cautela:

- os dados de producao mostram o mesmo valor tambem no canal `mobile`;
- um bloqueio agressivo no backend pode introduzir regressao de canal cruzado se nao for delimitado corretamente.

Preferencia operacional:

- primeiro corrigir o emissor Web;
- depois decidir se vale adicionar guard rail de backend em patch separado ou no mesmo pacote, dependendo do nivel de confianca.


### Fase 4 - Validacao funcional em workspace e homologacao

#### 4.1 Validacao automatizada local

Executar, no minimo:

1. testes de matching poligonal;
2. testes de API Web de localizacao;
3. regressao especifica do fluxo automatico;
4. qualquer script/harness existente de geolocalizacao Web que ajude a simular:
   - ponto dentro do poligono;
   - `not_in_known_location`;
   - `outside_workplace`.

#### 4.2 Homologacao dirigida em banco de preview

Montar uma bateria pequena e objetiva com usuarios de teste:

1. usuario em `P80` dentro do poligono do `Escritorio Principal`;
2. usuario em `P83` dentro do mesmo poligono compartilhado;
3. usuario fora de qualquer localizacao conhecida, mas abaixo do threshold de "fora do ambiente";
4. usuario fora do ambiente, acima do threshold de checkout automatico.

Esperado:

1. os casos 1 e 2 continuam reconhecendo `Escritorio Principal`;
2. o caso 3 nao gera `check-in` automatico nem persiste `Localizacao nao Cadastrada`;
3. o caso 4 continua podendo gerar `check-out` automatico.

#### 4.3 Verificacao manual focada

Fazer smoke manual apenas nos pontos abaixo:

1. abrir a Web com permissao de localizacao e automacao ligada;
2. confirmar que um match valido continua registrando o local correto;
3. simular ou provocar um `not_in_known_location`;
4. confirmar que o usuario ve o estado, mas nao ocorre submit automatico com local sintetico;
5. confirmar que o submit manual com local cadastrado continua possivel quando o fluxo exigir selecao manual.


### Fase 5 - Plano de rollout para producao

#### 5.1 Preparacao de deploy

1. Revisar o diff final e confirmar que ele toca apenas:
   - frontend Web de localizacao/automacao;
   - testes diretamente relacionados;
   - eventuais logs auxiliares estritamente necessarios.

2. Evitar incluir no mesmo deploy:
   - rollout de memberships multi-projeto;
   - alteracoes de schema;
   - mudancas no CRUD de localizacoes;
   - alteracoes de thresholds.

3. Se a branch principal do workspace estiver muito a frente da producao:
   - considerar cherry-pick do hotfix para uma branch de release mais proxima do codigo que esta no ar.

Essa precaucao e importante porque a producao atual nao esta no mesmo ponto do workspace na parte de `user_project_memberships` e filtro por projeto.

#### 5.2 Janela de validacao apos deploy

Nas primeiras horas apos o deploy, monitorar:

1. novos registros `web` em `check_events.local`;
2. novos registros `web` em `forms_submissions.local`;
3. presenca ou ausencia de novos casos com `local = "Localizacao nao Cadastrada"`;
4. continuidade de eventos normais em:
   - `Escritorio Principal`;
   - `Zona de CheckOut`;
   - `Fora do Local de Trabalho`;
   - outros locais reais usados pela operacao.

#### 5.3 Criterio de sucesso em producao

O deploy deve ser considerado bem-sucedido se, apos observacao inicial:

1. nao surgirem novos eventos Web com `local = "Localizacao nao Cadastrada"`;
2. continuarem surgindo eventos Web com locais reais reconhecidos;
3. o `check-out` automatico continuar funcionando;
4. nao houver aumento anormal de erros de submit ou falhas de UX relacionadas a localizacao.


## Criterios de aceite

1. Um ponto dentro do poligono de `Escritorio Principal` continua sendo reconhecido corretamente.

2. O fluxo automatico da Web nao grava mais `Localizacao nao Cadastrada` como `local`.

3. `Localizacao nao Cadastrada` continua, no maximo, como estado informativo de interface.

4. O fluxo manual com localizacao cadastrada continua operacional.

5. O `check-out` automatico por `outside_workplace` continua operacional.

6. O pacote nao exige migration de banco.

7. O pacote pode ser implantado sem depender do rollout de multi-projeto.


## Riscos e mitigacoes

### Risco 1 - Remover automacao demais

Se a equipe remover o caminho automatico errado de forma ampla, pode matar automacoes legitimas.

Mitigacao:

- limitar a mudanca ao caso `status = not_in_known_location`;
- preservar explicitamente os cenarios `matched` e `outside_workplace`;
- proteger com testes separados para cada caso.

### Risco 2 - Misturar este hotfix com divergencias maiores entre workspace e producao

O workspace atual ja carrega evolucoes de memberships e filtro por uniao de projetos que nao aparecem na producao atual.

Mitigacao:

- isolar a branch;
- fazer diff orientado por arquivo;
- revisar o pacote final como hotfix, nao como sincronizacao ampla.

### Risco 3 - Reabrir o bug no futuro por outro fallback textual

Mesmo se a regra principal for corrigida, algum refactor futuro pode voltar a usar `label` como `local` operacional.

Mitigacao:

- blindar a funcao que resolve o `local` automatico;
- adicionar teste de persistencia proibida para `Localizacao nao Cadastrada`.

### Risco 4 - Canal mobile continuar com o mesmo comportamento

Os dados de producao mostram ocorrencias semelhantes tambem no canal `mobile`.

Mitigacao:

- registrar explicitamente este ponto como follow-up operacional;
- nao misturar a correcao do canal mobile neste hotfix Web, a menos que a equipe decida atacar ambos com a mesma regra de negocio e cobertura adequada.


## Follow-up recomendado apos o hotfix

1. Abrir item separado para avaliar se o canal mobile deve obedecer a mesma regra de proibicao de persistir `Localizacao nao Cadastrada`.

2. Fazer auditoria leve de todos os valores sinteticos de localizacao usados em UI para garantir que nenhum deles possa vazar para persistencia operacional.

3. Revisar, em pacote proprio, a divergencia entre:
   - producao atual com filtro por `user.projeto` singular;
   - workspace atual com semantica de uniao de projetos.

4. Se o negocio ainda quiser um comportamento de "proximo ao ambiente de trabalho":
   - redesenhar a regra como conceito explicito;
   - nunca reutilizar `Localizacao nao Cadastrada` como local de negocio.


## Recomendacao final

A recomendacao mais segura e tratar este incidente como um hotfix pequeno, cirurgico e isolado:

1. nao tocar na geometria;
2. nao tocar no banco;
3. nao tocar no catalogo de localizacoes;
4. corrigir apenas o caminho de automacao que transforma falha de reconhecimento em local persistido;
5. provar por teste que `Localizacao nao Cadastrada` deixa de ser gravada pela Web;
6. levar para producao somente depois de homologacao focada e revisao de diff minima.

Essa abordagem preserva o que ja esta funcionando em producao e reduz bastante o risco de uma correcao pequena abrir regressao em areas que nao estao relacionadas ao incidente.
