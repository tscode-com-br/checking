# Especificacao da Fase 0 - localizacao poligonal no webapp

## 1. Objetivo

Este documento fecha as decisoes de produto e de comportamento da Fase 0 para a mudanca da localizacao do website publico `/user`.

Escopo desta fase:

- backend FastAPI;
- website administrativo em `sistema/app/static/admin`;
- website publico em `sistema/app/static/check`.

Fora de escopo desta fase:

- coluna `Visualizacao` com botao `Mapa`;
- alteracoes no layout do admin alem do estritamente necessario nas fases futuras;
- adaptacao do aplicativo Kotlin;
- qualquer referencia operacional ao Flutter legado.

Importante: este documento define o comportamento alvo para as proximas fases. Ele nao altera, por si so, o comportamento atual do codigo.

## 2. Glossario operacional

- `poligono base`: poligono fechado formado pela lista ordenada de coordenadas cadastradas para uma localizacao.
- `poligono expandido`: resultado do deslocamento uniforme para fora do `poligono base`, em metros, usando a tolerancia global da localizacao.
- `ponto bruto do usuario`: latitude e longitude originais recebidas do navegador, sem aplicar tolerancia.
- `circulo do usuario`: area provavel do usuario, centrada no `ponto bruto do usuario`, com raio igual a `accuracy_meters` informada pelo navegador.
- `local elegivel`: localizacao do mesmo projeto do usuario autenticado e apta a participar do matching.
- `local de trabalho`: qualquer local elegivel que nao seja uma `Zona de CheckOut`.

## 3. Decisoes fechadas da Fase 0

### 3.1 Item 0.1 - Cada localizacao sera um poligono fechado

Decisao fechada:

- cada localizacao sera interpretada como uma area fechada;
- a area sera formada pela sequencia ordenada de vertices cadastrados;
- o backend fechara implicitamente a geometria ligando o ultimo vertice ao primeiro.

Consequencia pratica:

- a localizacao deixa de ser tratada como um conjunto de pontos independentes com um unico raio de proximidade.

### 3.2 Item 0.2 - Minimo de coordenadas por localizacao

Decisao fechada:

- toda localizacao nova ou editada devera ter no minimo 3 coordenadas validas;
- localizacao com menos de 3 coordenadas sera considerada invalida para cadastro e para edicao.

Consequencia pratica:

- o backend devera rejeitar persistencia com menos de 3 vertices;
- o frontend admin devera impedir salvamento com menos de 3 vertices.

### 3.3 Item 0.3 - Tolerancia global por localizacao

Decisao fechada:

- a tolerancia continuara global por localizacao, exatamente como o modelo de dados atual ja suporta;
- essa tolerancia, em metros, deixara de significar um raio de proximidade em torno da coordenada mais proxima;
- a nova semantica sera: a tolerancia define o buffer uniforme externo do `poligono base`;
- todas as arestas do poligono serao deslocadas para fora pelo mesmo valor de tolerancia.

Consequencia pratica:

- nao existira tolerancia individual por coordenada;
- nao sera necessario introduzir novo campo de tolerancia por vertice para cumprir esta fase.

### 3.4 Item 0.4 - Limite global de precisao do GPS permanece obrigatorio

Decisao fechada:

- o campo administrativo `location_accuracy_threshold_meters` continua existindo;
- esse campo continua sendo um filtro de qualidade da leitura GPS;
- nenhuma geometria de matching sera avaliada se `accuracy_meters` vier nulo ou acima do limite global aceito.

Motivacao:

- evitar falso positivo causado por leituras imprecisas demais.

### 3.5 Item 0.5 - O usuario sera tratado como circulo de incerteza

Decisao fechada:

- o navegador continuara enviando `latitude`, `longitude` e `accuracy_meters`;
- o backend usara `latitude` e `longitude` como centro do `circulo do usuario`;
- o backend usara `accuracy_meters` como raio do `circulo do usuario`.

Consequencia pratica:

- o matching deixa de usar apenas um ponto pontual do usuario e passa a usar a area provavel indicada pela precisao do GPS.

### 3.6 Item 0.6 - Regra de intersecao valida

Decisao fechada:

- havera match geometrico quando o `circulo do usuario` interceptar o `poligono expandido` de pelo menos um local elegivel;
- tangencia conta como intersecao valida;
- sobreposicao parcial tambem conta como intersecao valida.

Consequencia pratica:

- o usuario sera considerado dentro do local mesmo quando a borda do circulo apenas tocar a borda do poligono expandido.

### 3.7 Item 0.7 - Filtro por projeto antes da geometria

Decisao fechada:

- somente localizacoes do projeto do usuario autenticado participarao do matching;
- esse filtro continuara ocorrendo antes de qualquer calculo geometrico.

Consequencia pratica:

- um poligono de outro projeto nunca podera ganhar match, desempate ou calculo de distancia residual.

### 3.8 Item 0.8 - Desempate entre multiplos poligonos

Decisao fechada:

- se o `circulo do usuario` interceptar mais de um `poligono expandido`, o desempate sera feito pela menor distancia entre o `ponto bruto do usuario` e a coordenada original cadastrada mais proxima de cada localizacao candidata;
- o calculo de desempate desconsidera o buffer e desconsidera o circulo do usuario;
- o calculo usa apenas as coordenadas originais cadastradas para cada localizacao elegivel candidata.

Motivacao:

- preservar o criterio solicitado pelo usuario e manter desempate simples, deterministico e auditavel.

### 3.9 Item 0.9 - Empate absoluto de distancia

Decisao fechada:

- se duas localizacoes candidatas tiverem exatamente a mesma menor distancia no desempate, vence a localizacao de menor `id` no banco;
- esse criterio so entra em acao depois do empate de distancia, como ultimo desempate deterministico.

Motivacao:

- evitar resultados nao deterministas em casos geometricos raros.

### 3.10 Item 0.10 - Regra de `not_in_known_location`

Decisao fechada:

- se nao houver intersecao entre o `circulo do usuario` e qualquer `poligono expandido` elegivel;
- e se a menor distancia entre o `ponto bruto do usuario` e o `local de trabalho` elegivel mais proximo for menor ou igual a `2000m`;
- a resposta operacional sera `status = not_in_known_location`;
- o `label` operacional sera `Localizacao nao Cadastrada`.

### 3.11 Item 0.11 - Regra de `outside_workplace`

Decisao fechada:

- se nao houver intersecao entre o `circulo do usuario` e qualquer `poligono expandido` elegivel;
- e se a menor distancia entre o `ponto bruto do usuario` e o `local de trabalho` elegivel mais proximo for maior que `2000m`;
- a resposta operacional sera `status = outside_workplace`;
- o `label` operacional sera `Fora do Ambiente de Trabalho`.

### 3.12 Item 0.12 - Regra da distancia de 2 km

Decisao fechada:

- a distancia de `2000m` sera medida entre o `ponto bruto do usuario` e a geometria original do `poligono base` do local de trabalho mais proximo;
- essa distancia nao usara o `poligono expandido`;
- essa distancia nao usara o `circulo do usuario`;
- essa distancia nao sera medida apenas ate os vertices isolados, e sim ate a geometria base da area cadastrada;
- `Zona de CheckOut` sera excluida desse calculo.

Motivacao:

- essa regra representa melhor a nocao de proximidade ao local de trabalho quando a localizacao passa a ser uma area, e nao mais um conjunto de pontos.

### 3.13 Item 0.13 - Ordem dos vertices e significativa

Decisao fechada:

- a ordem das coordenadas informadas no cadastro sera preservada exatamente como o admin informar;
- o poligono sera construido usando essa ordem;
- o sistema nao tentara reordenar automaticamente vertices no backend para "corrigir" a geometria.

Consequencia pratica:

- o cadastro administrativo precisara deixar claro que a ordem dos vertices define o contorno da area.

### 3.14 Item 0.14 - Fechamento implicito do poligono

Decisao fechada:

- o primeiro vertice nao devera ser repetido no final da lista;
- o backend fechara o poligono automaticamente ao ligar o ultimo vertice ao primeiro.

Consequencia pratica:

- o payload administrativo continua mais simples;
- a validacao backend deve tratar a repeticao manual do primeiro ponto como redundancia indesejada ou normaliza-la de forma explicita na fase de implementacao.

### 3.15 Item 0.15 - Visualizacao em mapa fora da primeira entrega

Decisao fechada:

- a coluna `Visualizacao` e o botao `Mapa` ficam fora do escopo da primeira entrega;
- a Fase 0 nao cria endpoint de preview, modal, imagem estatica nem desenho em tiles.

Consequencia pratica:

- nenhuma alteracao visual obrigatoria entra nesta fase por causa de mapa.

### 3.16 Item 0.16 - Aplicativo Kotlin fora do escopo imediato

Decisao fechada:

- a Fase 0 nao depende de nenhuma alteracao em `checking_kotlin`;
- a mudanca sera especificada primeiro para backend + admin web + webapp publico;
- futuras adaptacoes do app Kotlin consumirao a semantica consolidada depois.

Consequencia pratica:

- a implementacao das fases seguintes nao precisa aguardar sincronizacao com o cliente mobile.

### 3.17 Item 0.17 - Este documento passa a ser a referencia normativa

Decisao fechada:

- este arquivo passa a ser a referencia normativa da migracao para localizacao poligonal no web;
- qualquer fase posterior deve seguir estas definicoes ate que um novo documento substitua formalmente esta especificacao.

## 4. Restricoes desta fase

- nenhuma alteracao de layout do admin e exigida nesta fase;
- nenhum contrato HTTP precisa ser alterado nesta fase;
- nenhum algoritmo runtime precisa ser alterado nesta fase;
- o objetivo desta fase e fechar regras e reduzir ambiguidade antes do codigo.

## 5. Impacto esperado nas proximas fases

- Fase 1: auditoria de localizacoes existentes e saneamento de dados;
- Fase 2: implementacao da engine geometrica com poligono base, buffer uniforme e circulo do usuario;
- Fase 3: endurecimento de validacoes e contratos do admin;
- Fase 4: troca do matching runtime do endpoint `/api/web/check/location`;
- Fase 5: ajustes de UX no cadastro administrativo sem descaracterizar o layout atual.

## 6. Criterios de aceite da Fase 0

- existe um documento unico que fecha a semantica da localizacao poligonal no web;
- o documento diferencia claramente comportamento alvo de comportamento atual;
- o documento fecha os pontos que estavam em aberto antes de iniciar codigo;
- o documento preserva o limite global de precisao do GPS;
- o documento preserva a tolerancia global por localizacao;
- o documento explicita o criterio de desempate;
- o documento explicita a regra dos 2 km;
- o documento deixa a visualizacao em mapa para fase posterior;
- nenhuma alteracao de layout do admin foi realizada nesta fase.