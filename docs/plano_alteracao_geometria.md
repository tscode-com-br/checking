# Plano de Alteração de Geometria no Webapp

## Estado Atual do Webapp

Hoje o webapp da rota `/checking/user`, localizado em `sistema/app/static/check`, funciona da seguinte forma no bloco `Local`:

- O card de localização mostra o título `Local`, a precisão atual e um texto principal com o nome da localização resolvida para o usuário.
- O valor exibido em `Local` é renderizado como texto simples, sem comportamento de clique.
- A atualização da localização usa `navigator.geolocation.getCurrentPosition(...)` no frontend.
- O frontend envia para o backend apenas `latitude`, `longitude` e `accuracy_meters`.
- O endpoint `/api/web/check/location` responde com um payload resumido de match, contendo apenas:
  - `matched`
  - `resolved_local`
  - `label`
  - `status`
  - `message`
  - `accuracy_meters`
  - `accuracy_threshold_meters`
  - `nearest_workplace_distance_meters`
- Quando o match é positivo, o frontend guarda somente esse payload resumido em memória local da tela.
- O nome da localização exibido no card não carrega o identificador da localização escolhida, nem os vértices do polígono, nem a geometria expandida pelo offset, nem o ponto usado para representar o usuário.

No backend, a lógica de geometria já existe e está madura:

- As localizações poligonais são construídas em memória com `base_polygon` e `expanded_polygon`.
- O sistema já calcula o ponto do usuário e o círculo de precisão do GPS.
- O match atual considera a interseção entre o círculo de precisão do usuário e o polígono expandido pela tolerância.
- Já existe infraestrutura útil para montar um preview geométrico, incluindo conversão entre coordenadas geográficas e o sistema projetado usado nos cálculos.

Também já existe no frontend um padrão de widget/modal que pode ser reaproveitado:

- O webapp possui um widget de detalhes de solicitação de transporte com backdrop, título, conteúdo dinâmico e botão de fechar.
- Esse padrão reduz o esforço de implementação da nova visualização geométrica, porque a parte estrutural do diálogo já está pronta no projeto.

## Como o Webapp Ficará Após as Modificações

Depois das alterações, o card `Local` continuará com a mesma aparência geral, mas o nome da localização passará a funcionar como um link visualmente discreto:

- O texto da localização continuará com o mesmo tamanho, peso visual e cor do estado atual.
- O texto não terá sublinhado permanente.
- O clique ou toque no nome da localização abrirá um widget de visualização geométrica.
- Se não houver uma localização resolvida no momento, o texto continuará sem abrir o widget.

O novo widget mostrará o contexto geométrico do match atual:

- Nome da localização encontrada.
- Indicação da precisão capturada no momento da consulta.
- Desenho do polígono considerado para a decisão.
- Desenho do offset aplicado à localização, quando houver tolerância maior que zero.
- Um ponto vermelho indicando a posição central do usuário no instante em que a localização foi resolvida.
- Ajuste automático de enquadramento para manter toda a geometria visível.
- Ação clara para fechar o widget.

Funcionalmente, o comportamento esperado será:

- O usuário atualiza a localização normalmente, como já faz hoje.
- O backend resolve o match da localização.
- O frontend armazena os dados mínimos necessários para abrir o preview geométrico da última leitura válida.
- Ao tocar em `Local`, o frontend solicita ou reutiliza o payload geométrico detalhado da localização resolvida.
- O widget é aberto com a geometria correta daquela resolução, sem depender apenas do nome textual da localização.

Para manter fidelidade com a regra de negócio atual, o desenho exibido deve refletir a geometria realmente usada pelo sistema:

- O polígono base cadastrado.
- O polígono expandido pela tolerância, que é o que efetivamente participa da detecção.
- O ponto do usuário.

Observações importantes para o desenho final:

- Como o sistema já permite nomes duplicados de localização, a abertura do preview não deve depender apenas do `label` ou do `resolved_local`.
- O ideal é trabalhar com `location_id` ou outro identificador estável da localização efetivamente escolhida no match.
- O endpoint público atual de match não deve ser quebrado, porque há teste contratual congelando exatamente as chaves da resposta.
- O preview geométrico deve nascer em um contrato novo, separado do endpoint atual, ou como opcional muito bem controlado com atualização explícita dos testes de contrato.

## Funcionalidades Previstas

### 1. Link de abertura no campo `Local`

- O nome da localização resolvida será clicável.
- O estilo visual será preservado.
- O comportamento de teclado também deve funcionar, com foco e acionamento por Enter ou Space, quando aplicável.

### 2. Widget de preview geométrico

- O widget será aberto sobre a tela atual.
- O widget terá título, área visual central, legenda curta e ação de fechamento.
- O fechamento poderá ocorrer pelo botão, pelo backdrop e pelo fluxo de foco apropriado.

### 3. Visualização da geometria da localização

- O polígono base será desenhado como a área cadastrada.
- A área expandida pelo offset será desenhada de forma separada, para o usuário entender a área adicional considerada na detecção.
- O ponto vermelho mostrará a posição central capturada do aparelho.

### 4. Reaproveitamento da última localização válida

- O preview será relativo à última resolução positiva obtida pelo frontend.
- O widget não deve tentar desenhar geometria para estados como `Precisão insuficiente`, `Localização não cadastrada` ou `Fora do Ambiente de Trabalho`.

### 5. Tratamento de casos de borda

- Localização sem match válido: não abre o widget.
- Payload geométrico indisponível: mostra mensagem de falha controlada no widget.
- Nome duplicado de localização: resolução via identificador, nunca apenas por texto.
- Tolerância zero: deve haver decisão explícita se o preview mostrará apenas o polígono base ou se a camada de área expandida será omitida.

## Plano Detalhado Dividido em Fases

## Fase 1 - Congelar o escopo funcional e o contrato da feature

Objetivo:
Definir com precisão o que o usuário verá no widget e qual será a fonte oficial de dados do preview.

Alterações previstas:

- Definir se o preview será carregado por novo endpoint dedicado ou por extensão controlada do fluxo atual.
- Definir o contrato de resposta do preview geométrico.
- Incluir identificador da localização resolvida no fluxo da feature.
- Definir como o frontend vai armazenar a última consulta válida para abertura do widget.
- Definir a regra oficial para tolerância zero no contexto de geometria expandida.

Entregáveis da fase:

- Especificação do payload de preview.
- Decisão sobre `location_id` como referência primária.
- Lista de estados em que o widget pode ou não pode abrir.

## Fase 2 - Preparar o backend para expor a geometria de preview

Objetivo:
Criar no backend uma resposta capaz de representar a geometria efetivamente usada no match sem quebrar o contrato atual do endpoint `/api/web/check/location`.

Alterações previstas:

- Criar schema novo para o preview geométrico.
- Criar endpoint novo, por exemplo `POST /api/web/check/location-preview` ou equivalente.
- Receber `location_id`, `latitude`, `longitude` e `accuracy_meters`, ou receber um payload que permita recomputar o preview com segurança.
- Reutilizar os helpers existentes de geometria para montar:
  - vértices do polígono base
  - vértices do polígono expandido
  - ponto do usuário
  - metadados de tolerância e precisão
  - bounds recomendados para o enquadramento
- Garantir filtragem por projeto e por autenticação igual ao restante do webapp.
- Ajustar o tratamento de tolerância zero, se necessário, para não invalidar o preview.

Entregáveis da fase:

- Endpoint de preview respondendo com sucesso para localizações válidas.
- Cobertura de casos sem match, sem permissão, localização inválida e tolerância zero.

## Fase 3 - Adaptar o frontend para armazenar o contexto da última resolução válida

Objetivo:
Guardar no cliente os dados mínimos para abrir o preview corretamente.

Alterações previstas:

- Estender o estado do frontend para registrar a última resolução válida com identificador da localização.
- Separar claramente:
  - texto exibido no card
  - dados mínimos para abrir preview
  - dados completos do widget, quando já carregados
- Garantir limpeza do estado quando a localização deixar de ser válida.
- Evitar que um estado antigo de preview permaneça clicável depois de uma nova leitura negativa.

Entregáveis da fase:

- Estado do frontend preparado para abrir o widget apenas quando houver contexto válido.

## Fase 4 - Transformar o valor de `Local` em acionador do preview

Objetivo:
Converter o campo textual atual em um elemento interativo sem alterar a identidade visual do card.

Alterações previstas:

- Substituir o texto simples por um elemento acionável acessível.
- Preservar tipografia, cor e dimensões do componente atual.
- Remover sublinhado permanente.
- Adicionar foco visível e comportamento por teclado.
- Manter o elemento desabilitado ou inerte quando não houver preview disponível.

Entregáveis da fase:

- Campo `Local` clicável apenas nos estados válidos.
- Nenhuma regressão visual no card de localização.

## Fase 5 - Implementar o widget de visualização geométrica

Objetivo:
Mostrar ao usuário a geometria do match em um widget claro, compacto e coerente com o estilo atual do webapp.

Alterações previstas:

- Reaproveitar o padrão estrutural do widget de detalhes já existente.
- Adicionar markup específico para o preview geométrico.
- Criar renderização do desenho com a tecnologia escolhida para o projeto.
- Mostrar:
  - polígono base
  - polígono expandido
  - ponto vermelho do usuário
  - informações resumidas de precisão e tolerância
- Ajustar responsividade para mobile.
- Tratar estados de carregamento e erro do preview.

Entregáveis da fase:

- Widget funcional em desktop e mobile.
- Renderização correta da geometria no caso feliz e nos casos degradados.

## Fase 6 - Validar comportamento, contrato e regressão

Objetivo:
Garantir que a nova funcionalidade não quebre o fluxo atual de localização nem os contratos já congelados.

Alterações previstas:

- Adicionar testes do novo endpoint de preview.
- Preservar ou atualizar conscientemente o teste contratual existente do endpoint `/api/web/check/location`.
- Adicionar teste frontend para o comportamento clicável do `Local`.
- Adicionar teste frontend para abertura e fechamento do widget.
- Adicionar teste para nomes duplicados de localização.
- Adicionar teste para tolerância zero.
- Executar a bateria mínima de regressão do webapp e do backend.

Entregáveis da fase:

- Suíte de testes cobrindo contrato, UI e casos de borda.
- Confiança suficiente para liberar a feature sem regressão oculta.

## Lista de Tarefas por Fase de Implementação

## Fase 1 - Escopo e contrato

- Definir a experiência final do widget de preview.
- Confirmar que o endpoint atual de match não será reutilizado como payload completo de geometria.
- Definir o schema do preview geométrico.
- Definir o identificador oficial da localização no fluxo.
- Definir a regra de tolerância zero para preview.

## Fase 2 - Backend

- Criar schema Pydantic do preview geométrico.
- Criar endpoint dedicado para carregar o preview.
- Reutilizar `build_location_geometry()` para montar o polígono base e o expandido.
- Converter os vértices calculados para coordenadas WGS84 de resposta.
- Incluir no payload o ponto do usuário e os bounds sugeridos.
- Garantir filtro por projeto e autenticação.
- Tratar localização não encontrada, localização fora do projeto e geometria inválida.

## Fase 3 - Estado do frontend

- Criar estrutura de estado para preview da última localização válida.
- Persistir no estado o identificador da localização resolvida.
- Limpar o estado de preview quando o match falhar.
- Preparar a chamada do novo endpoint de preview.

## Fase 4 - Campo `Local` interativo

- Trocar o elemento textual por um elemento acionável.
- Preservar o estilo visual atual.
- Adicionar suporte a foco, clique e teclado.
- Desabilitar a ação quando não houver preview disponível.

## Fase 5 - Widget de geometria

- Criar a estrutura HTML do widget.
- Reaproveitar a lógica de abertura e fechamento do padrão existente.
- Implementar a renderização da geometria.
- Desenhar polígono base, área expandida e ponto vermelho do usuário.
- Exibir tolerância, precisão e nome da localização.
- Ajustar layout para mobile.
- Tratar carregamento e erro.

## Fase 6 - Testes e validação

- Adicionar testes do endpoint novo.
- Validar que o endpoint atual de match continua com o mesmo contrato, se essa for a decisão final.
- Adicionar testes do clique no campo `Local`.
- Adicionar testes do widget aberto e fechado.
- Adicionar testes de nomes duplicados.
- Adicionar testes de tolerância zero.
- Executar a bateria mínima de regressão do webapp e do backend.

## Resultado Esperado ao Final

Ao final das fases acima, o webapp terá um fluxo completo de inspeção visual da localização detectada:

- O usuário verá o nome da localização normalmente no card `Local`.
- Esse nome poderá ser tocado sem mudar a identidade visual atual.
- O sistema abrirá um widget com a geometria considerada no match.
- O usuário verá com clareza onde está a área da localização e onde estava seu ponto capturado.
- O contrato público atual de match poderá continuar estável, reduzindo risco de regressão no restante do sistema.
# Plano de Alteracao de Geometria no Webapp

## Estado Atual do Webapp

Hoje o webapp da rota `/checking/user`, localizado em `sistema/app/static/check`, funciona da seguinte forma no bloco `Local`:

- O card de localizacao mostra o titulo `Local`, a precisao atual e um texto principal com o nome da localizacao resolvida para o usuario.
- O valor exibido em `Local` e renderizado como texto simples, sem comportamento de clique.
- A atualizacao da localizacao usa `navigator.geolocation.getCurrentPosition(...)` no frontend.
- O frontend envia para o backend apenas `latitude`, `longitude` e `accuracy_meters`.
- O endpoint `/api/web/check/location` responde com um payload resumido de match, contendo apenas:
  - `matched`
  - `resolved_local`
  - `label`
  - `status`
  - `message`
  - `accuracy_meters`
  - `accuracy_threshold_meters`
  - `nearest_workplace_distance_meters`
- Quando o match e positivo, o frontend guarda somente esse payload resumido em memoria local da tela.
- O nome da localizacao exibido no card nao carrega o identificador da localizacao escolhida, nem os vertices do poligono, nem a geometria expandida pelo offset, nem o ponto usado para representar o usuario.

No backend, a logica de geometria ja existe e esta madura:

- As localizacoes poligonais sao construidas em memoria com `base_polygon` e `expanded_polygon`.
- O sistema ja calcula o ponto do usuario e o circulo de precisao do GPS.
- O match atual considera a intersecao entre o circulo de precisao do usuario e o poligono expandido pela tolerancia.
- Ja existe infraestrutura util para montar um preview geométrico, incluindo conversao entre coordenadas geograficas e o sistema projetado usado nos calculos.

Tambem ja existe no frontend um padrao de widget/modal que pode ser reaproveitado:

- O webapp possui um widget de detalhes de solicitacao de transporte com backdrop, titulo, conteudo dinamico e botao de fechar.
- Esse padrao reduz o esforco de implementacao da nova visualizacao geometrica, porque a parte estrutural do dialogo ja esta pronta no projeto.

## Como o Webapp Ficara Apos as Modificacoes

Depois das alteracoes, o card `Local` continuara com a mesma aparencia geral, mas o nome da localizacao passara a funcionar como um link visualmente discreto:

- O texto da localizacao continuara com o mesmo tamanho, peso visual e cor do estado atual.
- O texto nao tera sublinhado permanente.
- O clique ou toque no nome da localizacao abrira um widget de visualizacao geometrica.
- Se nao houver uma localizacao resolvida no momento, o texto continuara sem abrir o widget.

O novo widget mostrara o contexto geometrico do match atual:

- Nome da localizacao encontrada.
- Indicacao da precisao capturada no momento da consulta.
- Desenho do poligono considerado para a decisao.
- Desenho do offset aplicado a localizacao, quando houver tolerancia maior que zero.
- Um ponto vermelho indicando a posicao central do usuario no instante em que a localizacao foi resolvida.
- Ajuste automatico de enquadramento para manter toda a geometria visivel.
- Acao clara para fechar o widget.

Funcionalmente, o comportamento esperado sera:

- O usuario atualiza a localizacao normalmente, como ja faz hoje.
- O backend resolve o match da localizacao.
- O frontend armazena os dados minimos necessarios para abrir o preview geometrico da ultima leitura valida.
- Ao tocar em `Local`, o frontend solicita ou reutiliza o payload geometrico detalhado da localizacao resolvida.
- O widget e aberto com a geometria correta daquela resolucao, sem depender apenas do nome textual da localizacao.

Para manter fidelidade com a regra de negocio atual, o desenho exibido deve refletir a geometria realmente usada pelo sistema:

- O poligono base cadastrado.
- O poligono expandido pela tolerancia, que e o que efetivamente participa da deteccao.
- O ponto do usuario.

Observacoes importantes para o desenho final:

- Como o sistema ja permite nomes duplicados de localizacao, a abertura do preview nao deve depender apenas do `label` ou do `resolved_local`.
- O ideal e trabalhar com `location_id` ou outro identificador estavel da localizacao efetivamente escolhida no match.
- O endpoint publico atual de match nao deve ser quebrado, porque ha teste contratual congelando exatamente as chaves da resposta.
- O preview geometrico deve nascer em um contrato novo, separado do endpoint atual, ou como opcional muito bem controlado com atualizacao explicita dos testes de contrato.

## Funcionalidades Previstas

### 1. Link de abertura no campo `Local`

- O nome da localizacao resolvida sera clicavel.
- O estilo visual sera preservado.
- O comportamento de teclado tambem deve funcionar, com foco e acionamento por Enter ou Space, quando aplicavel.

### 2. Widget de preview geometrico

- O widget sera aberto sobre a tela atual.
- O widget tera titulo, area visual central, legenda curta e acao de fechamento.
# Plano de Alteração de Geometria no Webapp

## Estado Atual do Webapp

Hoje o webapp da rota `/checking/user`, localizado em `sistema/app/static/check`, funciona da seguinte forma no bloco `Local`:

- O card de localização mostra o título `Local`, a precisão atual e um texto principal com o nome da localização resolvida para o usuário.
- O valor exibido em `Local` é renderizado como texto simples, sem comportamento de clique.
- A atualização da localização usa `navigator.geolocation.getCurrentPosition(...)` no frontend.
- O frontend envia para o backend apenas `latitude`, `longitude` e `accuracy_meters`.
- O endpoint `/api/web/check/location` responde com um payload resumido de match, contendo apenas:
  - `matched`
  - `resolved_local`
  - `label`
  - `status`
  - `message`
  - `accuracy_meters`
  - `accuracy_threshold_meters`
  - `nearest_workplace_distance_meters`
- Quando o match é positivo, o frontend guarda somente esse payload resumido em memória local da tela.
- O nome da localização exibido no card não carrega o identificador da localização escolhida, nem os vértices do polígono, nem a geometria expandida pelo offset, nem o ponto usado para representar o usuário.

No backend, a lógica de geometria já existe e está madura:

- As localizações poligonais são construídas em memória com `base_polygon` e `expanded_polygon`.
- O sistema já calcula o ponto do usuário e o círculo de precisão do GPS.
- O match atual considera a interseção entre o círculo de precisão do usuário e o polígono expandido pela tolerância.
- Já existe infraestrutura útil para montar um preview geométrico, incluindo conversão entre coordenadas geográficas e o sistema projetado usado nos cálculos.

Também já existe no frontend um padrão de widget/modal que pode ser reaproveitado:

- O webapp possui um widget de detalhes de solicitação de transporte com backdrop, título, conteúdo dinâmico e botão de fechar.
- Esse padrão reduz o esforço de implementação da nova visualização geométrica, porque a parte estrutural do diálogo já está pronta no projeto.

## Como o Webapp Ficará Após as Modificações

Depois das alterações, o card `Local` continuará com a mesma aparência geral, mas o nome da localização passará a funcionar como um link visualmente discreto:

- O texto da localização continuará com o mesmo tamanho, peso visual e cor do estado atual.
- O texto não terá sublinhado permanente.
- O clique ou toque no nome da localização abrirá um widget de visualização geométrica.
- Se não houver uma localização resolvida no momento, o texto continuará sem abrir o widget.

O novo widget mostrará o contexto geométrico do match atual:

- Nome da localização encontrada.
- Indicação da precisão capturada no momento da consulta.
- Desenho do polígono considerado para a decisão.
- Desenho do offset aplicado à localização, quando houver tolerância maior que zero.
- Um ponto vermelho indicando a posição central do usuário no instante em que a localização foi resolvida.
- Ajuste automático de enquadramento para manter toda a geometria visível.
- Ação clara para fechar o widget.

Funcionalmente, o comportamento esperado será:

- O usuário atualiza a localização normalmente, como já faz hoje.
- O backend resolve o match da localização.
- O frontend armazena os dados mínimos necessários para abrir o preview geométrico da última leitura válida.
- Ao tocar em `Local`, o frontend solicita ou reutiliza o payload geométrico detalhado da localização resolvida.
- O widget é aberto com a geometria correta daquela resolução, sem depender apenas do nome textual da localização.

Para manter fidelidade com a regra de negócio atual, o desenho exibido deve refletir a geometria realmente usada pelo sistema:

- O polígono base cadastrado.
- O polígono expandido pela tolerância, que é o que efetivamente participa da detecção.
- O ponto do usuário.

Observações importantes para o desenho final:

- Como o sistema já permite nomes duplicados de localização, a abertura do preview não deve depender apenas do `label` ou do `resolved_local`.
- O ideal é trabalhar com `location_id` ou outro identificador estável da localização efetivamente escolhida no match.
- O endpoint público atual de match não deve ser quebrado, porque há teste contratual congelando exatamente as chaves da resposta.
- O preview geométrico deve nascer em um contrato novo, separado do endpoint atual, ou como opcional muito bem controlado com atualização explícita dos testes de contrato.

## Funcionalidades Previstas

### 1. Link de abertura no campo `Local`

- O nome da localização resolvida será clicável.
- O estilo visual será preservado.
- O comportamento de teclado também deve funcionar, com foco e acionamento por Enter ou Space, quando aplicável.

### 2. Widget de preview geométrico

- O widget será aberto sobre a tela atual.
- O widget terá título, área visual central, legenda curta e ação de fechamento.
- O fechamento poderá ocorrer pelo botão, pelo backdrop e pelo fluxo de foco apropriado.

### 3. Visualização da geometria da localização

- O polígono base será desenhado como a área cadastrada.
- A área expandida pelo offset será desenhada de forma separada, para o usuário entender a área adicional considerada na detecção.
- O ponto vermelho mostrará a posição central capturada do aparelho.

### 4. Reaproveitamento da última localização válida

- O preview será relativo à última resolução positiva obtida pelo frontend.
- O widget não deve tentar desenhar geometria para estados como `Precisão insuficiente`, `Localização não cadastrada` ou `Fora do Ambiente de Trabalho`.

### 5. Tratamento de casos de borda

- Localização sem match válido: não abre o widget.
- Payload geométrico indisponível: mostra mensagem de falha controlada no widget.
- Nome duplicado de localização: resolução via identificador, nunca apenas por texto.
- Tolerância zero: deve haver decisão explícita se o preview mostrará apenas o polígono base ou se a camada de área expandida será omitida.

## Plano Detalhado Dividido em Fases

## Fase 1 - Congelar o escopo funcional e o contrato da feature

Objetivo:
Definir com precisão o que o usuário verá no widget e qual será a fonte oficial de dados do preview.

Alterações previstas:

- Definir se o preview será carregado por novo endpoint dedicado ou por extensão controlada do fluxo atual.
- Definir o contrato de resposta do preview geométrico.
- Incluir identificador da localização resolvida no fluxo da feature.
- Definir como o frontend vai armazenar a última consulta válida para abertura do widget.
- Definir a regra oficial para tolerância zero no contexto de geometria expandida.

Entregáveis da fase:

- Especificação do payload de preview.
- Decisão sobre `location_id` como referência primária.
- Lista de estados em que o widget pode ou não pode abrir.

## Fase 2 - Preparar o backend para expor a geometria de preview

Objetivo:
Criar no backend uma resposta capaz de representar a geometria efetivamente usada no match sem quebrar o contrato atual do endpoint `/api/web/check/location`.

Alterações previstas:

- Criar schema novo para o preview geométrico.
- Criar endpoint novo, por exemplo `POST /api/web/check/location-preview` ou equivalente.
- Receber `location_id`, `latitude`, `longitude` e `accuracy_meters`, ou receber um payload que permita recomputar o preview com segurança.
- Reutilizar os helpers existentes de geometria para montar:
  - vértices do polígono base
  - vértices do polígono expandido
  - ponto do usuário
  - metadados de tolerância e precisão
  - bounds recomendados para o enquadramento
- Garantir filtragem por projeto e por autenticação igual ao restante do webapp.
- Ajustar o tratamento de tolerância zero, se necessário, para não invalidar o preview.

Entregáveis da fase:

- Endpoint de preview respondendo com sucesso para localizações válidas.
- Cobertura de casos sem match, sem permissão, localização inválida e tolerância zero.

## Fase 3 - Adaptar o frontend para armazenar o contexto da última resolução válida

Objetivo:
Guardar no cliente os dados mínimos para abrir o preview corretamente.

Alterações previstas:

- Estender o estado do frontend para registrar a última resolução válida com identificador da localização.
- Separar claramente:
  - texto exibido no card
  - dados mínimos para abrir preview
  - dados completos do widget, quando já carregados
- Garantir limpeza do estado quando a localização deixar de ser válida.
- Evitar que um estado antigo de preview permaneça clicável depois de uma nova leitura negativa.

Entregáveis da fase:

- Estado do frontend preparado para abrir o widget apenas quando houver contexto válido.

## Fase 4 - Transformar o valor de `Local` em acionador do preview

Objetivo:
Converter o campo textual atual em um elemento interativo sem alterar a identidade visual do card.

Alterações previstas:

- Substituir o texto simples por um elemento acionável acessível.
- Preservar tipografia, cor e dimensões do componente atual.
- Remover sublinhado permanente.
- Adicionar foco visível e comportamento por teclado.
- Manter o elemento desabilitado ou inerte quando não houver preview disponível.

Entregáveis da fase:

- Campo `Local` clicável apenas nos estados válidos.
- Nenhuma regressão visual no card de localização.

## Fase 5 - Implementar o widget de visualização geométrica

Objetivo:
Mostrar ao usuário a geometria do match em um widget claro, compacto e coerente com o estilo atual do webapp.

Alterações previstas:

- Reaproveitar o padrão estrutural do widget de detalhes já existente.
- Adicionar markup específico para o preview geométrico.
- Criar renderização do desenho com a tecnologia escolhida para o projeto.
- Mostrar:
  - polígono base
  - polígono expandido
  - ponto vermelho do usuário
  - informações resumidas de precisão e tolerância
- Ajustar responsividade para mobile.
- Tratar estados de carregamento e erro do preview.

Entregáveis da fase:

- Widget funcional em desktop e mobile.
- Renderização correta da geometria no caso feliz e nos casos degradados.

## Fase 6 - Validar comportamento, contrato e regressão

Objetivo:
Garantir que a nova funcionalidade não quebre o fluxo atual de localização nem os contratos já congelados.

Alterações previstas:

- Adicionar testes do novo endpoint de preview.
- Preservar ou atualizar conscientemente o teste contratual existente do endpoint `/api/web/check/location`.
- Adicionar teste frontend para o comportamento clicável do `Local`.
- Adicionar teste frontend para abertura e fechamento do widget.
- Adicionar teste para nomes duplicados de localização.
- Adicionar teste para tolerância zero.
- Executar a bateria mínima de regressão do webapp e do backend.

Entregáveis da fase:

- Suíte de testes cobrindo contrato, UI e casos de borda.
- Confiança suficiente para liberar a feature sem regressão oculta.

## Lista de Tarefas por Fase de Implementação

## Fase 1 - Escopo e contrato

- Definir a experiência final do widget de preview.
- Confirmar que o endpoint atual de match não será reutilizado como payload completo de geometria.
- Definir o schema do preview geométrico.
- Definir o identificador oficial da localização no fluxo.
- Definir a regra de tolerância zero para preview.

## Fase 2 - Backend

- Criar schema Pydantic do preview geométrico.
- Criar endpoint dedicado para carregar o preview.
- Reutilizar `build_location_geometry()` para montar o polígono base e o expandido.
- Converter os vértices calculados para coordenadas WGS84 de resposta.
- Incluir no payload o ponto do usuário e os bounds sugeridos.
- Garantir filtro por projeto e autenticação.
- Tratar localização não encontrada, localização fora do projeto e geometria inválida.

## Fase 3 - Estado do frontend

- Criar estrutura de estado para preview da última localização válida.
- Persistir no estado o identificador da localização resolvida.
- Limpar o estado de preview quando o match falhar.
- Preparar a chamada do novo endpoint de preview.

## Fase 4 - Campo `Local` interativo

- Trocar o elemento textual por um elemento acionável.
- Preservar o estilo visual atual.
- Adicionar suporte a foco, clique e teclado.
- Desabilitar a ação quando não houver preview disponível.

## Fase 5 - Widget de geometria

- Criar a estrutura HTML do widget.
- Reaproveitar a lógica de abertura e fechamento do padrão existente.
- Implementar a renderização da geometria.
- Desenhar polígono base, área expandida e ponto vermelho do usuário.
- Exibir tolerância, precisão e nome da localização.
- Ajustar layout para mobile.
- Tratar carregamento e erro.

## Fase 6 - Testes e validação

- Adicionar testes do endpoint novo.
- Validar que o endpoint atual de match continua com o mesmo contrato, se essa for a decisão final.
- Adicionar testes do clique no campo `Local`.
- Adicionar testes do widget aberto e fechado.
- Adicionar testes de nomes duplicados.
- Adicionar testes de tolerância zero.
- Executar a bateria mínima de regressão do webapp e do backend.

## Resultado Esperado ao Final

Ao final das fases acima, o webapp terá um fluxo completo de inspeção visual da localização detectada:

- O usuário verá o nome da localização normalmente no card `Local`.
- Esse nome poderá ser tocado sem mudar a identidade visual atual.
- O sistema abrirá um widget com a geometria considerada no match.
- O usuário verá com clareza onde está a área da localização e onde estava seu ponto capturado.
- O contrato público atual de match poderá continuar estável, reduzindo risco de regressão no restante do sistema.