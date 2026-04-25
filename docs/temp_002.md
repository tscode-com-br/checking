# Plano para elevar a precisao da captura GPS no web check

## 1. Objetivo

Definir uma estrategia tecnica, incremental e verificavel para reduzir a frequencia com que a aplicacao web em `sistema/app/static/check` recebe coordenadas com precisao insuficiente no momento em que:

- a pagina e aberta;
- a pagina volta para primeiro plano;
- o usuario pressiona o botao `Atualizar localizacao`.

O objetivo **nao** e afrouxar a regra de negocio. O objetivo e aumentar a chance de a aplicacao obter uma leitura GPS boa o suficiente para passar pelo limite configurado no admin em `Erro maximo para considerar a coordenada do usuario`.

## 2. Diagnostico do estado atual

### 2.1 Fluxo atual no frontend web

Pelo codigo atual em `sistema/app/static/check/app.js`:

- a captura usa `navigator.geolocation.getCurrentPosition(...)`;
- as opcoes atuais sao:
  - `enableHighAccuracy: true`
  - `maximumAge: 0`
  - `timeout: 20000`
- a funcao `resolveCurrentLocation()` faz **uma unica tentativa de leitura** por ciclo de captura;
- quando a pagina volta para foco, o fluxo passa por `runLifecycleUpdateSequence()`;
- quando o usuario clica no botao de refresh, o fluxo passa por `runManualLocationRefreshSequence()`;
- depois que o navegador entrega uma posicao, o frontend envia `latitude`, `longitude` e `accuracy_meters` para `POST /api/web/check/location`.

### 2.2 Fluxo atual no backend

Pelo codigo atual em `sistema/app/routers/web_check.py`:

- o backend le o limite global via `get_location_accuracy_threshold_meters(db)`;
- se `accuracy_meters` vier `null` ou acima do limite configurado, o backend retorna:
  - `status = accuracy_too_low`
  - `label = Precisao insuficiente`
- so depois de passar por esse filtro de qualidade a geometria de matching e avaliada.

Isso esta coerente com a especificacao existente: o limite administrativo continua obrigatorio e o matching nao deve ser executado quando a leitura GPS for ruim demais.

### 2.3 Conclusao tecnica do diagnostico

O problema principal, no estado atual, **nao parece estar no matching**. O problema parece estar na **estrategia de aquisicao da posicao no navegador**.

Hoje a aplicacao aceita a primeira leitura que o navegador entregar para aquela tentativa. Em cenarios reais, especialmente em ambiente interno, transicao recente de rede, aparelho frio ou GPS ainda convergindo, a primeira leitura pode chegar rapidamente, mas com `accuracy_meters` acima do necessario.

## 3. Hipotese principal

Hipotese de trabalho:

> a aplicacao web esta encerrando a captura cedo demais, aceitando uma leitura inicial ainda imprecisa, quando seria melhor manter uma janela curta e controlada de aquisicao para aguardar amostras melhores antes de decidir qual coordenada enviar ao backend.

Observacao importante:

- aumentar apenas o `timeout` de `getCurrentPosition()` **nao garante** melhora real;
- em muitos navegadores, `getCurrentPosition()` resolve assim que a primeira posicao aceitavel e obtida, mesmo que poucos segundos depois fosse possivel receber uma posicao melhor;
- portanto, a ideia de "esperar um pouco mais" faz sentido, mas provavelmente deve ser implementada como **janela de aquisicao com selecao da melhor amostra**, e nao apenas como aumento cego de timeout.

## 4. Diretrizes da solucao

Para resolver o problema sem quebrar comportamento homologado, a solucao deve seguir estas diretrizes:

1. Preservar o contrato atual da API de matching web.
2. Preservar o papel do limite administrativo `location_accuracy_threshold_meters`.
3. Melhorar apenas a forma como o frontend escolhe **qual** leitura GPS enviar.
4. Evitar rajadas de chamadas ao backend durante uma mesma captura.
5. Manter experiencia silenciosa nos gatilhos automaticos e experiencia mais orientada no refresh manual.
6. Nao degradar atividades automaticas que dependem da localizacao final resolvida.

## 5. Opcoes de abordagem

### 5.1 Aumentar somente o timeout atual

**Descricao**

- manter `getCurrentPosition()` como esta;
- aumentar `timeout` de 20 s para um valor maior.

**Vantagens**

- mudanca pequena;
- baixo risco estrutural.

**Desvantagens**

- baixa chance de resolver a causa real;
- o navegador pode continuar entregando uma primeira leitura ruim cedo demais;
- piora a espera nos casos de timeout sem garantir leitura melhor.

**Recomendacao**

- nao adotar como solucao principal.

### 5.2 Repetir `getCurrentPosition()` em loop controlado

**Descricao**

- fazer tentativas sucessivas por janela limitada;
- guardar a melhor `accuracy_meters` encontrada;
- ao final, enviar ao backend apenas a melhor leitura.

**Vantagens**

- mais simples de encaixar no desenho atual;
- reduz dependencia de comportamento especifico de `watchPosition()`.

**Desvantagens**

- pode ficar mais verboso e menos elegante;
- pode repetir overhead desnecessario entre chamadas;
- tende a ser inferior a uma sessao de observacao continua.

**Recomendacao**

- manter como fallback tecnico caso `watchPosition()` se mostre instavel na homologacao.

### 5.3 Sessao limitada com `watchPosition()` e selecao da melhor amostra

**Descricao**

- iniciar uma sessao de captura por tempo limitado;
- acompanhar varias amostras durante uma janela curta;
- manter sempre a melhor leitura observada;
- encerrar cedo quando a precisao ficar dentro do limite exigido;
- enviar ao backend apenas a melhor leitura final daquela sessao.

**Vantagens**

- ataca diretamente a causa mais provavel;
- melhora a chance de convergencia do GPS;
- permite equilibrio entre rapidez e qualidade.

**Desvantagens**

- requer refatoracao maior no frontend;
- exige cuidado com cancelamento, foco, concorrencia e UX.

**Recomendacao**

- **abordagem principal recomendada**.

### 5.4 Relaxar o limite administrativo de precisao

**Descricao**

- aumentar o valor configurado no admin para reduzir rejeicoes por `accuracy_too_low`.

**Vantagens**

- efeito imediato;
- zero mudanca tecnica no frontend.

**Desvantagens**

- reduz o rigor da regra de negocio;
- pode aumentar falso positivo;
- nao corrige a causa operacional da captura ruim.

**Recomendacao**

- tratar apenas como contingencia operacional temporaria, nunca como correcao principal.

## 6. Estrategia recomendada

### 6.1 Resumo executivo

Implementar no frontend uma **sessao de aquisicao GPS com janela limitada**, preferencialmente baseada em `watchPosition()`, com estes principios:

- uma sessao por gatilho de captura;
- varias amostras do navegador durante poucos segundos;
- selecao da melhor amostra pela menor `accuracy_meters` valida;
- encerramento antecipado assim que a amostra atingir o limite administrativo;
- envio de apenas uma chamada final ao backend de matching.

### 6.2 Comportamento recomendado por tipo de gatilho

#### Abertura da aplicacao e retorno ao primeiro plano

- usar modo silencioso;
- abrir uma janela curta de captura;
- nao exibir mensagens excessivas enquanto a pagina apenas retomou foco;
- se surgir amostra suficiente cedo, encerrar cedo;
- se a melhor amostra ainda ficar ruim ao final da janela, manter o comportamento de alerta atual, mas com mensagem mais informativa.

#### Botao `Atualizar localizacao`

- usar modo interativo;
- permitir uma janela um pouco maior do que a silenciosa;
- mostrar que a aplicacao esta buscando uma leitura mais precisa, e nao apenas consultando uma unica vez;
- exibir a melhor precisao obtida ate o momento;
- quando a sessao terminar sem atingir o limite, informar qual foi a melhor precisao encontrada e qual era o limite exigido.

### 6.3 Regra de selecao da melhor amostra

Cada amostra recebida do navegador deve ser avaliada assim:

1. descartar amostras sem latitude/longitude validas;
2. descartar amostras com `accuracy` ausente, negativa ou nao numerica;
3. considerar melhor amostra a de menor `accuracy_meters`;
4. em empate tecnico, preferir a mais recente;
5. se alguma amostra atingir `accuracy_meters <= threshold`, encerrar imediatamente com sucesso tecnico da captura.

### 6.4 Regra de encerramento da sessao

A sessao deve terminar quando ocorrer qualquer um destes eventos:

1. a precisao atingir o limite administrativo;
2. a janela maxima de captura expirar;
3. ocorrer erro irrecuperavel do navegador;
4. a sessao for cancelada por novo gatilho concorrente;
5. a pagina deixar de estar em contexto valido para continuar aquela tentativa.

### 6.5 Janela de captura sugerida

Os valores exatos devem ser calibrados em homologacao, mas o plano recomenda partir de algo nesta linha:

- modo silencioso de ciclo de vida: 6 a 10 segundos;
- modo interativo do botao manual: 12 a 20 segundos;
- encerramento antecipado imediato quando `accuracy_meters <= threshold`.

Esses numeros sao **ponto de partida**, nao decisao final. O ajuste deve ser guiado por testes reais em aparelho e por observacao de quantas capturas melhoram significativamente apos os primeiros segundos.

## 7. Arquitetura proposta para a implementacao futura

### 7.1 Novo conceito no frontend: sessao de aquisicao

Introduzir uma abstracao explicita para a captura, por exemplo um controlador interno com estas responsabilidades:

- iniciar a sessao;
- registrar timestamp de inicio;
- acompanhar amostras recebidas;
- guardar melhor amostra;
- encerrar/cancelar sessao;
- devolver um resultado padronizado para `resolveCurrentLocation()`.

### 7.2 Resultado padronizado da sessao

Mesmo que a API publica permaneça igual, internamente o frontend deve passar a diferenciar:

- erro do navegador sem nenhuma amostra;
- sessao encerrada com melhor amostra abaixo do limite;
- sessao encerrada com melhor amostra acima do limite;
- sessao cancelada por concorrencia ou perda de contexto.

Isso facilita UX, telemetria e testes.

### 7.3 Compatibilidade com o fluxo existente

`resolveCurrentLocation()` pode continuar como fachada principal, mas deixando de depender de uma chamada unica a `getCurrentPosition()`.

O ideal e que:

- `runLifecycleUpdateSequence()` continue chamando uma atualizacao silenciosa;
- `runManualLocationRefreshSequence()` continue chamando uma atualizacao interativa;
- `runAutomaticActivitiesEnableSequence()` continue recebendo apenas a localizacao final resolvida, nunca amostras intermediarias.

### 7.4 Concorrencia e cancelamento

Como o app ja possui mecanismos como `locationRequestPromise`, `lifecycleRefreshInProgress` e cooldown de gatilhos, a futura implementacao deve manter ou reforcar estas garantias:

- nao abrir duas sessoes de captura em paralelo;
- cancelar observador anterior ao iniciar um novo refresh forcado;
- impedir que `visibilitychange`, `focus` e `pageshow` criem captura duplicada em cascata;
- impedir envio duplicado de `POST /api/web/check/location` para uma mesma intencao de refresh.

## 8. Observabilidade e diagnostico

Antes ou junto da mudanca de comportamento, vale incluir observabilidade suficiente para comprovar que a solucao realmente melhorou a taxa de sucesso.

### 8.1 Dados que interessam medir

Por sessao de captura:

- origem do gatilho: `startup`, `visibility`, `focus`, `pageshow`, `manual_refresh`, `automatic_activities_enable`;
- tempo total de captura em ms;
- quantidade de amostras recebidas;
- melhor `accuracy_meters` observado;
- `accuracy_meters` enviado ao backend;
- `threshold` vigente;
- resultado final do matching: `matched`, `accuracy_too_low`, `not_in_known_location`, `outside_workplace`, `no_known_locations`;
- existencia de cancelamento ou timeout.

### 8.2 Forma de coletar

Fase inicial sugerida:

- diagnostico em memoria e `console` durante homologacao controlada;
- sem alterar contrato de resposta da API.

Fase posterior opcional:

- enviar telemetria controlada para logs de servidor ou endpoint diagnostico dedicado, se houver necessidade operacional real.

## 9. UX recomendada

### 9.1 Mensagens durante captura manual

O refresh manual deve deixar claro que o sistema esta tentando obter **melhor precisao**, e nao apenas "rodando de novo".

Sugestao de semantica de mensagens:

- inicio: "Buscando uma leitura GPS mais precisa...";
- progresso: "Melhor precisao ate agora: X m. Limite exigido: Y m.";
- sucesso tecnico de captura: "Precisao suficiente atingida. Validando localizacao...";
- encerramento sem atingir limite: "A melhor leitura obtida foi X m, acima do limite de Y m.".

### 9.2 Mensagens para gatilhos automaticos

Nos gatilhos silenciosos, a UX deve continuar discreta:

- evitar poluir o usuario com mensagens transitorias a cada retorno de foco;
- manter feedback visivel apenas quando o resultado final realmente importa;
- preservar o botao manual como acao explicita de nova tentativa.

### 9.3 O que nao fazer na UX

- nao prometer "GPS exato";
- nao manter spinner infinito;
- nao disparar mensagens repetitivas em sequencia por `focus` e `visibilitychange`;
- nao esconder do usuario qual foi a melhor precisao obtida quando houver falha por baixa precisao.

## 10. Impactos no backend e no contrato

### 10.1 O que deve permanecer igual

- `POST /api/web/check/location` continua recebendo `latitude`, `longitude` e `accuracy_meters`;
- o backend continua devolvendo `accuracy_too_low` quando a leitura estiver acima do limite;
- o campo administrativo `location_accuracy_threshold_meters` continua sendo a referencia unica de qualidade minima;
- a semantica homologada do matching nao muda.

### 10.2 O que pode mudar sem quebrar contrato

- o frontend passa a escolher melhor a amostra antes de enviar;
- a mensagem local apresentada ao usuario pode ficar mais descritiva;
- a telemetria interna pode registrar estatisticas da sessao de captura.

### 10.3 O que deve ser evitado nesta etapa

- mudar o significado do limite administrativo;
- alterar a estrutura do response de `POST /api/web/check/location` sem necessidade;
- misturar esta correcao com mudancas de geometria, tolerancia ou regra de projeto.

## 11. Plano de execucao por fases

### Fase 1 - Medicao e desenho detalhado

Objetivo:

- confirmar, em aparelho e navegador reais, quanto a precisao melhora apos os primeiros segundos.

Entregas:

- tabela de cenarios de campo;
- amostras de tempos de convergencia;
- decisao final entre `watchPosition()` principal e loop de `getCurrentPosition()` como fallback.

#### 11.1 Premissas obrigatorias da medicao

- medir primeiro o comportamento atual de leitura unica como baseline, antes de comparar qualquer estrategia nova;
- manter o mesmo `location_accuracy_threshold_meters` durante cada bateria comparativa;
- executar a comparacao dentro de um local conhecido com margem confortavel para dentro da area, evitando borda geometrica, tangencia exata e locais com tolerancia zero como base principal da decisao;
- registrar dispositivo, navegador, versao do navegador, tipo de conexao, nivel de bateria aproximado e horario de cada sessao;
- considerar uma sessao encerrada apenas quando a UI estabilizar o resultado final ou quando a janela maxima expirar.

#### 11.2 Roteiro objetivo de medicao em campo

1. Escolher um projeto e um local conhecido que permitam medicao dentro da area com folga operacional, sem depender de match em borda.
2. Registrar o threshold administrativo vigente antes da primeira repeticao e nao altera-lo ate o fim daquela bateria.
3. Executar a estrategia atual de leitura unica para formar o baseline comparativo.
4. Executar a candidata com `watchPosition()` sob os mesmos cenarios, aparelho e navegador.
5. Executar a candidata com loop controlado de `getCurrentPosition()` apenas se a bateria com `watchPosition()` mostrar instabilidade, baixa quantidade de amostras ou ganho inconclusivo.
6. Consolidar os resultados por cenario, por gatilho e por combinacao aparelho+navegador antes de escolher a estrategia principal.

#### 11.3 Matriz minima de cenarios e repeticoes

| Bloco | Condicao de campo | Gatilho | Repeticoes validas minimas | Objetivo da celula |
| --- | --- | --- | --- | --- |
| A1 | Area aberta, aparelho parado, dentro de local conhecido | `startup` | 3 | medir limite superior de captura e tempo de convergencia sem degradacao ambiental |
| A2 | Area aberta, aparelho parado, dentro de local conhecido | `manual_refresh` | 3 | medir o melhor caso do fluxo interativo |
| B1 | Area interna, GPS degradado mas recuperavel, dentro de local conhecido | `startup` | 5 | medir se a estrategia melhora a primeira carga em ambiente dificil |
| B2 | Area interna, GPS degradado mas recuperavel, dentro de local conhecido | `manual_refresh` | 5 | medir se a estrategia melhora a acao explicita do usuario |
| B3 | Area interna, GPS degradado mas recuperavel, dentro de local conhecido | `foreground_resume` | 5 | medir estabilidade de retorno ao primeiro plano |
| C1 | Movimento leve, ainda dentro de local conhecido ou em aproximacao clara | `manual_refresh` | 3 | medir comportamento com pequena variacao de radio e coordenada |
| C2 | Movimento leve, ainda dentro de local conhecido ou em aproximacao clara | `foreground_resume` | 3 | medir sensibilidade da retomada com aparelho em deslocamento leve |

Regra pratica para `foreground_resume`:

- carregar a pagina autenticada;
- enviar a aba para segundo plano por 15 a 30 segundos;
- retornar ao app e medir apenas a sessao iniciada pelo retorno ao primeiro plano.

#### 11.4 Ficha minima de coleta por sessao

Cada repeticao deve registrar, no minimo, estas colunas:

| Campo | Descricao |
| --- | --- |
| `session_id` | identificador unico da repeticao |
| `strategy` | `single_attempt`, `watch_position` ou `loop_get_current_position` |
| `device` | modelo do aparelho |
| `browser` | navegador e versao |
| `scenario` | celula da matriz (`A1`, `A2`, `B1`, etc.) |
| `trigger` | `startup`, `manual_refresh` ou `foreground_resume` |
| `threshold_meters` | limite vigente no admin durante a sessao |
| `time_to_first_sample_ms` | tempo ate a primeira amostra valida |
| `samples_received` | quantidade total de amostras validas observadas |
| `best_accuracy_meters` | menor `accuracy_meters` observada na sessao |
| `time_to_best_sample_ms` | tempo ate a melhor amostra |
| `final_accuracy_sent_meters` | precisao efetivamente enviada ao backend |
| `final_status` | `matched`, `accuracy_too_low`, `not_in_known_location`, `outside_workplace` ou `no_known_locations` |
| `timed_out` | se a sessao terminou por prazo maximo |
| `cancelled` | se a sessao foi cancelada por outro gatilho |
| `duplicate_post` | se houve mais de um `POST /api/web/check/location` para a mesma sessao |
| `ui_stuck` | se houve loading preso, spinner preso ou status final ausente |
| `notes` | observacoes livres relevantes |

#### 11.5 Definicoes objetivas para a comparacao

Para a Fase 1, usar estas definicoes:

- `captura bem-sucedida`: sessao que produz pelo menos uma amostra valida e atinge `best_accuracy_meters <= threshold_meters` dentro da janela prevista;
- `encerramento sem sucesso`: sessao que termina por timeout, cancelamento ou erro sem nenhuma amostra valida suficiente, ou que termina com `best_accuracy_meters > threshold_meters`;
- `ganho util de precisao`: diferenca positiva entre a taxa de `captura bem-sucedida` de uma estrategia candidata e a taxa observada na estrategia de comparacao;
- `anomalia operacional`: qualquer sessao com `duplicate_post = true`, `ui_stuck = true`, cancelamento incorreto ou ausencia de finalizacao finita.

#### 11.6 Critérios objetivos para escolher entre `watchPosition()` e fallback

Escolher `watchPosition()` como estrategia principal somente se todos os criterios abaixo forem atendidos:

1. Em pelo menos 80% das sessoes dos blocos `B1`, `B2` e `B3`, a estrategia produzir duas ou mais amostras validas, provando que existe beneficio real de observacao continua.
2. A taxa de `captura bem-sucedida` de `watchPosition()` nos blocos internos degradados (`B1`, `B2`, `B3`) for pelo menos 10 pontos percentuais maior que a do fallback, ou empatar nessa taxa com mediana de `time_to_best_sample_ms` pelo menos 20% menor.
3. Nos blocos de area aberta (`A1`, `A2`), `watchPosition()` nao piorar a mediana de `time_to_first_sample_ms` em mais de 20% nem introduzir anomalia operacional.
4. Nao houver `duplicate_post`, sessao sem finalizacao finita ou loading preso em nenhuma repeticao valida.
5. Nao houver navegador-alvo critico em que `watchPosition()` apresente falha recorrente de amostragem, timeout dominante ou comportamento inconsistente.

Escolher o loop controlado de `getCurrentPosition()` como estrategia principal se ocorrer qualquer uma destas situacoes:

1. `watchPosition()` nao atingir o criterio minimo de duas ou mais amostras validas em 80% das sessoes internas degradadas.
2. O ganho util de precisao de `watchPosition()` ficar abaixo de 10 pontos percentuais e a vantagem de tempo tambem nao compensar com pelo menos 20% de melhora na mediana.
3. `watchPosition()` introduzir anomalia operacional em qualquer cenario critico.
4. O resultado de `watchPosition()` for significativamente instavel entre navegadores-alvo e essa instabilidade nao puder ser isolada com um ponto unico de decisao e fallback seguro.

Regra de desempate para producao:

- se `watchPosition()` e fallback entregarem praticamente a mesma taxa de sucesso, com diferenca menor que 5 pontos percentuais e sem vantagem clara de tempo, preferir o fallback por menor complexidade operacional.

#### 11.7 Gate de saida da Fase 1

A Fase 1 so deve ser considerada concluida quando existir:

1. planilha ou tabela preenchida para todas as celulas obrigatorias da matriz minima;
2. consolidado por aparelho+navegador;
3. decisao escrita e rastreavel entre `watchPosition()` principal ou fallback principal;
4. janelas iniciais de captura definidas para a Fase 2;
5. lista curta de riscos observados que precisarao de protecao na implementacao.

#### 11.8 Instrumentacao local minima para a bateria baseline

Para viabilizar a bateria baseline sem alterar contrato HTTP, payload nem resposta da API, a Fase 1 passa a contar com uma instrumentacao local opt-in em `sistema/app/static/check/app.js`, com estes objetivos:

- registrar sessoes de captura em memoria, sempre com `strategy = single_attempt` enquanto a estrategia atual continuar ativa;
- espelhar no `console` apenas o inicio e o encerramento das sessoes, deixando o detalhamento completo disponivel em memoria;
- distinguir pelo menos os gatilhos `startup`, `manual_refresh`, `visibility`, `focus`, `pageshow` e `automatic_activities_enable`;
- registrar, sem mudar o contrato do backend, `session_id`, `trigger`, `samples_received`, `best_accuracy_meters`, `final_accuracy_sent_meters`, `threshold_meters`, `final_status`, `termination_reason`, `timed_out`, `duplicate_post` e `duration_ms`.

Uso local sugerido para homologacao controlada:

1. abrir a pagina do web check em ambiente de teste;
2. habilitar a instrumentacao com `window.CheckingWebLocationMeasurement.enable()`;
3. limpar sessoes anteriores com `window.CheckingWebLocationMeasurement.clear()` antes de cada bateria;
4. executar as repeticoes do baseline nas celulas `A1`, `A2`, `B1`, `B2` e `B3`;
5. coletar os registros com `window.CheckingWebLocationMeasurement.getSessions()` ao final de cada bloco;
6. desabilitar a instrumentacao com `window.CheckingWebLocationMeasurement.disable()` quando a bateria terminar.

Restricoes desta instrumentacao:

- nao altera `POST /api/web/check/location`;
- nao altera mensagens de UX por si so;
- nao muda a estrategia atual de captura;
- nao substitui a medicao em aparelho, navegador e ambiente reais.

#### 11.9 Consolidacao objetiva por gatilho

Para viabilizar a segunda sugestao sem depender de consolidacao manual pesada, a instrumentacao local passa a expor tambem estes comandos no navegador:

- `window.CheckingWebLocationMeasurement.summarize()` para o consolidado geral da bateria atual;
- `window.CheckingWebLocationMeasurement.summarizeByTrigger()` para o consolidado por gatilho;
- `window.CheckingWebLocationMeasurement.buildReport({ ...metadados })` para gerar um relatorio unico com `overall`, `by_trigger` e `sessions`;
- `window.CheckingWebLocationMeasurement.printReport({ ...metadados })` para imprimir o relatorio completo no `console`.

Metadados minimos recomendados para cada bateria:

1. `scenario`, por exemplo `A1`, `A2`, `B1`, `B2` ou `B3`;
2. `device_model`;
3. `browser` e versao;
4. `environment`, por exemplo `aberto`, `interno`, `degradado`;
5. `operator` ou identificador da rodada, se necessario.

Sequencia operacional recomendada para cada bloco de medicao:

1. `window.CheckingWebLocationMeasurement.enable()`;
2. `window.CheckingWebLocationMeasurement.clear()`;
3. executar as repeticoes planejadas do bloco;
4. `window.CheckingWebLocationMeasurement.printReport({ scenario: 'A1', device_model: '...', browser: '...', environment: '...' })`;
5. copiar o objeto retornado e salvar junto da planilha da Fase 1;
6. repetir para o proximo bloco;
7. ao final da bateria, revisar `summarizeByTrigger()` para comparar `startup`, `manual_refresh`, `visibility`, `focus`, `pageshow` e demais gatilhos capturados.

Interpretacao minima esperada para a decisao da estrategia principal:

- se `manual_refresh` mostrar ganho material de precisao apos pequenas janelas adicionais e os gatilhos silenciosos permanecerem ruins, a ativacao progressiva deve continuar pelo refresh manual primeiro;
- se `visibility`, `focus` e `pageshow` apresentarem comportamento equivalente e previsivel, eles podem compartilhar a mesma estrategia na Fase 3;
- se algum gatilho concentrar `timeout`, `browser_position_unavailable` ou `accuracy_too_low` de forma desproporcional, ele deve ser tratado como caso especial na escolha entre `watchPosition()` e fallback.

Leitura de campo ja observada em validacao online de 2026-04-25:

- ao carregar ou recarregar o link, a aplicacao convergiu para precisao excelente, com relato de aproximadamente `3 m`, o que indica que o caminho de `startup` nao deve ser mexido nesta rodada;
- ao acionar `Atualizar localizacao`, a atualizacao continuou acontecendo rapido demais, o que manteve o problema exatamente no gatilho interativo que queremos corrigir;
- ao mandar a pagina para segundo plano e trazê-la de volta, os gatilhos `visibility`, `focus` e `pageshow` tambem continuaram resolvendo rapido demais, com o mesmo perfil de defeito;
- a conclusao operacional foi estreitar a proxima implementacao para `manual_refresh` e retorno ao primeiro plano, preservando `startup`, `submit_guard` e automacoes no caminho anterior ate nova validacao.

### Fase 2 - Refatoracao da captura no frontend

Objetivo:

- trocar a logica de captura de tentativa unica por sessao limitada de aquisicao.

Arquivos mais provaveis:

- `sistema/app/static/check/app.js`
- possivelmente `sistema/app/static/check/index.html`
- possivelmente `sistema/app/static/check/styles.css`

Entregas:

- controlador de sessao de aquisicao;
- selecao da melhor amostra;
- cancelamento limpo;
- integracao com refresh manual e gatilhos de ciclo de vida.

### Fase 3 - Ajuste de UX

Objetivo:

- tornar a espera compreensivel e reduzir percepcao de falha arbitraria.

Entregas:

- novos textos de progresso;
- exibicao mais clara da melhor precisao obtida;
- finalizacao consistente em sucesso, timeout, cancelamento e baixa precisao.

### Fase 4 - Testes automatizados e checks de regressao

Objetivo:

- garantir que a melhora de captura nao quebre contratos e fluxos vizinhos.

Cobertura minima desejada:

- selecao da melhor amostra por menor `accuracy_meters`;
- encerramento antecipado quando atinge o limite;
- timeout com reaproveitamento da melhor amostra observada;
- cancelamento da sessao anterior em refresh forcado;
- ausencia de multiplos `POST /api/web/check/location` por uma mesma sessao;
- preservacao do comportamento `accuracy_too_low` no backend.

Checks de regressao importantes:

- refresh manual de localizacao;
- atualizacao ao voltar para primeiro plano;
- habilitacao de atividades automaticas;
- submissao manual quando a localizacao foi resolvida apos sessao mais longa;
- fallback para localizacao manual quando permissao GPS nao existe.

### Fase 5 - Homologacao real em campo

Objetivo:

- validar que houve melhora concreta em ambiente operacional.

Cenarios minimos:

- area aberta com GPS bom;
- area interna com GPS degradado, mas recuperavel;
- aparelho parado apos abrir a pagina;
- pagina enviada para segundo plano e trazida de volta;
- clique manual em `Atualizar localizacao` logo apos abrir;
- aparelho em movimento leve;
- repeticao em pelo menos dois modelos de aparelho e mais de um navegador, se suportado pelo negocio.

## 12. Criterios de aceite

Uma futura implementacao deve ser considerada aprovada somente se atender, no minimo, a estes criterios:

1. O contrato atual de `POST /api/web/check/location` continua funcional.
2. O limite administrativo de precisao continua sendo respeitado sem flexibilizacao oculta.
3. O numero de casos `accuracy_too_low` cai de forma perceptivel na homologacao comparativa.
4. O refresh manual passa a ter comportamento explicavel e previsivel para o usuario.
5. O app nao dispara capturas paralelas nem chamadas duplicadas ao backend.
6. Fluxos de atividades automaticas e de historico continuam funcionando sem regressao.
7. A sessao sempre termina de forma finita, sem spinner preso.

## 13. Riscos e mitigacoes

### Risco 1 - `watchPosition()` variar entre navegadores

Mitigacao:

- homologar em navegadores reais antes de fechar a estrategia;
- manter plano de fallback com loop controlado de `getCurrentPosition()`.

### Risco 2 - espera maior piorar UX

Mitigacao:

- usar janelas curtas e encerramento antecipado por sucesso;
- separar modo silencioso e modo interativo.

### Risco 3 - consumo maior de bateria ou radio

Mitigacao:

- sessao curta, limitada e cancelavel;
- nenhuma observacao continua em background fora da janela necessaria.

### Risco 4 - regressao em atividades automaticas

Mitigacao:

- tratar `resolveCurrentLocation()` como contrato interno central;
- validar explicitamente fluxo de auto check-in/check-out na homologacao.

## 14. Recomendacao final

O caminho mais solido e:

1. **nao mexer no limite administrativo como resposta principal**;
2. **nao confiar apenas em aumento de timeout**;
3. **implementar uma sessao limitada de captura GPS com selecao da melhor amostra**;
4. **preservar o backend e o contrato atual, mudando principalmente a estrategia do frontend**;
5. **homologar com telemetria comparativa antes de declarar o problema resolvido**.

Em resumo: a sugestao de "esperar um pouco mais" esta tecnicamente bem direcionada, mas a forma correta de aplicar isso, muito provavelmente, e manter a captura aberta por uma janela controlada e escolher a melhor leitura disponivel, em vez de aceitar a primeira leitura que aparecer.

## 15. To-do list completa de execução

### Fase 0. Guard rails obrigatórios para produção

- [x] Tratar o comportamento atual em produção como baseline intocável: qualquer diferença fora do problema de aquisição GPS deve ser considerada regressão.
- [x] Confirmar que a implementação será frontend-only em primeira e segunda intenção, concentrada em `sistema/app/static/check/app.js`.
- [x] Não abrir diffs em `sistema/app/routers/web_check.py`, `sistema/app/schemas.py`, `sistema/app/static/admin/**`, migrations, banco ou contratos HTTP, salvo se um teste de contrato provar de forma inequívoca que o problema não pode ser resolvido 100% no frontend.
- [x] Não alterar autenticação, histórico, projeto, localização manual, transporte, regras de negócio de check-in/check-out automático nem layout já consolidado, salvo no ponto estritamente necessário para a nova estratégia de captura.
- [x] Não tocar em `index.html` e `styles.css` por padrão; só abrir esse escopo se uma revisão visual demonstrar que o feedback mínimo necessário não cabe na UI atual.
- [x] Isolar a nova lógica de aquisição em um helper ou controlador único, mantendo o caminho atual de leitura única facilmente restaurável.
- [x] Definir um fallback explícito para a estratégia atual de `getCurrentPosition()` em um único ponto de decisão, para rollback rápido se a nova abordagem falhar.
- [x] Confirmar que a primeira validação da nova estratégia ocorrerá fora de produção ou, no mínimo, sem ativação ampla dos gatilhos mais sensíveis.
- [x] Registrar como critério de aceite técnico que a solução precisa melhorar a aquisição sem alterar o contrato de `POST /api/web/check/location`.

Execução registrada em 2026-04-25:

1. Foi confirmado em `sistema/app/static/check/app.js` que a captura GPS atual está centralizada em `geolocationOptions`, `requestCurrentPosition()`, `resolveCurrentLocation()`, `runLifecycleUpdateSequence()` e `runManualLocationRefreshSequence()`, o que fecha a Fase 0 com escopo inicial concentrado no frontend e, por padrão, em um único arquivo.
2. Foi confirmado em `tests/test_api_flow.py` que o contrato de `POST /api/web/check/location` já protege `status = accuracy_too_low`, `label = Precisao insuficiente` e `accuracy_threshold_meters`, então backend e contrato HTTP ficam congelados por padrão nesta demanda.
3. Foi confirmado em `tests/check_user_location_ui.test.js` que já existem guardas de regressão para a visibilidade do campo de localização manual e para o sincronismo com permissão de GPS e `Atividades Automáticas`, o que sustenta a decisão de não abrir `index.html` nem `styles.css` nesta fase.
4. Ficou definido que o ponto único de decisão da futura estratégia de captura continuará passando por `resolveCurrentLocation()`, enquanto o caminho atual de leitura única via `requestCurrentPosition()` deverá permanecer disponível como fallback explícito e de rollback rápido.
5. Ficou definido que a primeira ativação da nova estratégia deverá começar fora de produção ou, no mínimo, sem habilitação ampla dos gatilhos mais sensíveis, iniciando pelo refresh manual antes de qualquer expansão para gatilhos automáticos ou de ciclo de vida.

### Fase 1. Medição e desenho final da estratégia de captura

- [x] Definir um roteiro objetivo de medição em campo com sequência, cenários mínimos, número de repetições e ficha de coleta.
- [x] Definir critérios objetivos para escolher entre `watchPosition()` principal e loop controlado de `getCurrentPosition()` como fallback.
- [x] Preparar instrumentação local mínima em memória e `console`, com ativação opt-in e sem alterar o contrato HTTP.
- [x] Preparar um consolidado local por gatilho para reduzir trabalho manual na análise comparativa da bateria baseline.
- [ ] Executar a bateria baseline da estratégia atual nas células `A1`, `A2`, `B1`, `B2` e `B3` com a instrumentação local habilitada.
- [ ] Medir, em navegador e aparelho reais, quanto a precisão melhora entre a primeira amostra e as amostras subsequentes em abertura de página, retorno ao primeiro plano e refresh manual.
- [ ] Registrar tempos de convergência típicos para cenário aberto, cenário interno e cenário de GPS degradado, para calibrar as janelas de captura.
- [ ] Validar se `watchPosition()` entrega amostras sucessivas confiáveis nos navegadores-alvo do projeto.
- [ ] Validar se há necessidade real de fallback com loop controlado de `getCurrentPosition()` para algum navegador ou aparelho específico.
- [ ] Fechar os valores iniciais de janela silenciosa, janela interativa, prazo máximo da sessão, tolerância de encerramento antecipado e comportamento de cancelamento.
- [x] Registrar o critério objetivo de “captura bem-sucedida”: melhor amostra válida com `accuracy_meters <= location_accuracy_threshold_meters`.
- [x] Registrar o critério objetivo de “encerramento sem sucesso”: janela encerrada com melhor amostra ainda acima do limite, sem quebrar o contrato atual do backend.
- [ ] Fechar os textos de progresso, sucesso e falha da captura manual, com a ortografia final aprovada.

Execução registrada em 2026-04-25:

1. Foi definido um roteiro objetivo de medição em campo com ordem de execução, matriz mínima de cenários, quantidade mínima de repetições e ficha de coleta por sessão.
2. Foi definido que a comparação deve usar a estratégia atual como baseline e evitar cenários de borda geométrica, tangência exata e tolerância zero como base principal da decisão, para não contaminar a escolha da estratégia de captura.
3. Foram registrados os critérios objetivos de `captura bem-sucedida`, `encerramento sem sucesso`, `ganho útil de precisão` e `anomalia operacional`.
4. Foram definidos critérios numéricos para escolher entre `watchPosition()` e loop controlado de `getCurrentPosition()`, incluindo regra explícita de desempate pró-fallback quando o ganho for marginal.
5. Foi preparada uma instrumentação local mínima, opt-in, em memória e `console`, para registrar a bateria baseline da estratégia atual sem alterar o contrato do backend nem a UX consolidada.
6. Foi preparado um consolidado local por gatilho, com resumo geral, resumo por gatilho e relatório único exportável em memória, para apoiar a decisão entre `watchPosition()` e fallback sem depender de tabulação manual bruta no navegador.
7. A bateria baseline real nas células `A1`, `A2`, `B1`, `B2` e `B3` continua dependente de execução manual em aparelho, navegador e ambiente físicos compatíveis com a homologação de campo.

### Fase 2. Implementação isolada e reversível da nova aquisição

- [x] Introduzir, em `sistema/app/static/check/app.js`, constantes ou configuração interna para janela silenciosa, janela interativa, prazo máximo da sessão, regra de encerramento antecipado e escolha do caminho de fallback.
- [x] Criar a abstração interna da sessão de aquisição com responsabilidades explícitas de iniciar, receber amostras, comparar precisão, encerrar, cancelar e devolver um resultado padronizado.
- [x] Garantir que a melhor amostra seja definida pela menor `accuracy_meters` válida e, em empate, pela amostra mais recente.
- [x] Garantir que amostras sem latitude, sem longitude ou sem `accuracy` numérica válida sejam descartadas.
- [x] Implementar encerramento antecipado quando alguma amostra atingir o limite administrativo vigente.
- [x] Implementar encerramento por prazo máximo reaproveitando a melhor amostra observada até aquele momento.
- [ ] Implementar cancelamento limpo da sessão anterior quando um refresh manual forçado substituir uma captura em andamento.
- [x] Preservar e reforçar os bloqueios já existentes por `locationRequestPromise`, `lifecycleRefreshInProgress` e `lifecycleTriggerCooldownMs`.
- [x] Garantir que apenas uma chamada final de `POST /api/web/check/location` seja enviada ao backend por sessão de captura.
- [x] Preservar integralmente o payload atual enviado ao backend: `latitude`, `longitude` e `accuracy_meters`.
- [x] Preservar integralmente o tratamento atual do backend para `matched`, `accuracy_too_low`, `outside_workplace`, `not_in_known_location` e `no_known_locations`.
- [x] Garantir que a lógica de permissão continue respeitando `navigator.permissions`, `locationPromptAttemptedKey` e `locationPermissionGrantedKey`.
- [x] Garantir que a captura continue falhando de forma finita quando o navegador negar permissão, devolver erro irrecuperável ou não produzir amostras válidas.
- [x] Garantir que a nova lógica possa ser desligada rapidamente, restaurando o comportamento atual sem refatoração ampla.

Execucao registrada em 2026-04-25:

1. O frontend passou a expor um plano interno unico de captura com `strategy = watch_window`, `minimumWindowMs = 3000` e `maxWindowMs = 7000` para os gatilhos `startup`, `submit_guard`, `manual_refresh`, `automatic_activities_enable`, `automatic_activities_disable`, `visibility`, `focus` e `pageshow`.
2. O helper `shouldStopLocationWatch()` passou a bloquear encerramento antecipado antes de `3000 ms`, mesmo quando a primeira amostra ja vier com boa precisao, e a sessao so encerra antes de `7000 ms` quando a melhor amostra ficar dentro do limite administrativo apos a janela minima.
3. O limite administrativo continua sendo reutilizado pelo proprio frontend quando disponivel, e a melhor amostra valida continua sendo enviada uma unica vez ao backend apenas no encerramento da sessao.
4. O caminho antigo de leitura unica foi preservado como fallback centralizado em `requestCurrentPositionForPlan()` para gatilhos nao mapeados, o que mantem rollback rapido sem abrir escopo em backend ou UI.
5. Em revisao corretiva da mesma data, foi identificado que `runLifecycleUpdateSequence()` nao estava repassando seus `settings` para `updateLocationForLifecycleSequence()`, o que fazia `startup`, `visibility`, `focus` e `pageshow` cairem silenciosamente no fallback `single_attempt` apesar do mapa de gatilhos ja apontar para `watch_window`.
6. A correcao efetiva foi repassar `settings` nessa chamada, restaurando a aplicacao real da janela `3000-7000 ms` aos gatilhos de ciclo de vida, com teste focado atualizado e redeploy validado em `https://tscode.com.br`.

### Fase 3. Ativação progressiva por gatilho

- [x] Integrar a nova sessão primeiro apenas a `runManualLocationRefreshSequence()`, mantendo abertura de página, retorno ao primeiro plano e fluxos automáticos na estratégia atual até validação explícita.
- [x] Validar o refresh manual isoladamente antes de ampliar o escopo para outros gatilhos.
- [x] Só depois da validação do refresh manual, integrar a nova sessão a `ensureLocationReadyForSubmit()`, se ainda for necessário para a submissão manual.
- [x] Só depois da validação do refresh manual, integrar a nova sessão a `runLifecycleUpdateSequence()` para os gatilhos `visibilitychange`, `focus` e `pageshow`.
- [x] Garantir que `visibilitychange`, `focus` e `pageshow` não disparem múltiplas sessões concorrentes para a mesma intenção de atualização.
- [x] Só depois da validação dos gatilhos de ciclo de vida, integrar a nova sessão a `runAutomaticActivitiesEnableSequence()` e aos pontos de automação que realmente precisarem dela.
- [ ] Manter, em cada etapa, os gatilhos ainda não migrados no comportamento antigo até a etapa anterior ficar comprovadamente estável.

Execucao registrada em 2026-04-25:

1. A ativacao progressiva comecou pelo `manual_refresh`, depois foi expandida para os gatilhos de retorno ao primeiro plano e, por fim, para os demais gatilhos atuais que dependem da mesma resolucao centralizada de localizacao.
2. A reclamacao de que a aplicacao ainda respondia rapido demais expôs uma causa raiz diferente da janela em si: os gatilhos de ciclo de vida continuavam entrando em `single_attempt` porque `runLifecycleUpdateSequence()` chamava `updateLocationForLifecycleSequence()` sem repassar `triggerSource` nem os demais `settings`.
3. Depois do ajuste dessa chamada para `updateLocationForLifecycleSequence(settings)`, os gatilhos `startup`, `visibility`, `focus` e `pageshow` passaram a usar de fato o mesmo plano `watch_window` ja configurado no mapa de gatilhos.
4. A validacao local foi refeita com `node --test tests/check_user_location_ui.test.js`, incluindo uma assercao dedicada ao encaminhamento de `settings`, e o deploy publico foi refeito diretamente no `app` principal da DigitalOcean.
5. O proximo checkpoint obrigatorio continua sendo homologacao em aparelho fisico com a instrumentacao local habilitada, para confirmar `duration_ms`, `termination_reason`, `samples_received` e `final_status` nos cenarios reais que ainda apresentarem duvida.

### Fase 4. UX e observabilidade com impacto mínimo

- [ ] Diferenciar com clareza o modo silencioso do modo interativo apenas onde isso trouxer ganho real de compreensão para o usuário.
- [ ] Atualizar os textos do refresh manual para explicar que o sistema está buscando uma leitura GPS mais precisa, e não apenas repetindo a consulta.
- [x] Exibir, no fluxo manual, a melhor precisão já obtida e o limite administrativo correspondente durante a captura, sem poluir os gatilhos silenciosos.
- [ ] Ajustar a mensagem final de sucesso técnico para informar quando a precisão suficiente for atingida antes do fim da janela.
- [ ] Ajustar a mensagem final de falha para informar a melhor precisão obtida quando ela continuar acima do limite.
- [ ] Garantir que o botão `Atualizar localização` mantenha estados corretos de `loading`, `aria-busy`, `aria-label` e `title` durante toda a sessão.
- [ ] Preservar o comportamento de `setLocationPresentation()` e `setStatus()` sem criar mensagens duplicadas ou contraditórias.
- [ ] Manter qualquer diagnóstico apenas no escopo local de homologação, com logs discretos e facilmente removíveis ou desativáveis.
- [ ] Não introduzir telemetria nova de servidor, novo endpoint de diagnóstico nem alteração de payload nesta demanda.
- [ ] Só abrir escopo em `index.html` ou `styles.css` se uma revisão visual controlada provar que a UX mínima aprovada não cabe no layout atual.

Execucao registrada em 2026-04-25:

1. O fluxo com `watch_window` passou a atualizar o card de localizacao em tempo real sempre que surgir uma amostra melhor, mantendo o label `Buscando melhor precisão...` e exibindo no proprio card a melhor `Precisão X m / Limite Y m` observada ate aquele instante.
2. A atualizacao incremental foi limitada aos fluxos que ja exibem estado de deteccao (`showDetectingState = true`), evitando poluir os gatilhos silenciosos de ciclo de vida com mensagens intermediarias.
3. O contrato HTTP permaneceu intacto: as coordenadas continuam sendo enviadas ao backend apenas uma vez, no encerramento da janela, mas a UX manual agora deixa claro que novas amostras GPS estao sendo recebidas durante a espera.

### Fase 5. Testes automatizados e proteção de contrato

- [x] Ampliar `tests/check_user_location_ui.test.js` para cobrir a nova estratégia de captura, os novos textos de progresso e a preservação das regras de visibilidade do campo de localização manual.
- [ ] Ampliar `tests/check_automatic_activities_layout.test.js` para garantir que a nova captura não quebre a disponibilidade de `Atividades Automáticas` nem o sincronismo com permissão de GPS.
- [ ] Criar ou ampliar testes JavaScript focados na sessão de aquisição para validar seleção da melhor amostra, descarte de leituras inválidas, encerramento antecipado, reaproveitamento da melhor amostra e cancelamento por refresh forçado.
- [ ] Usar `tests/test_api_flow.py` como guarda de contrato para `accuracy_too_low`, `label`, `status` e `accuracy_threshold_meters`, sem abrir diff em backend por padrão.
- [ ] Só editar testes Python se faltar guarda suficiente para proteger o contrato atual; a expectativa padrão desta demanda é não tocar backend nem seu contrato.
- [ ] Adicionar testes de regressão que confirmem que o frontend continua enviando apenas uma amostra final ao backend por sessão.
- [ ] Adicionar testes de regressão separados para: refresh manual, gatilhos de abertura/retorno ao primeiro plano, `ensureLocationReadyForSubmit()` e habilitação de `Atividades Automáticas`.
- [ ] Executar primeiro os testes JavaScript diretamente tocados pela mudança.
- [ ] Executar, como guarda final, os testes de contrato e smoke tests relacionados ao fluxo web já existente.
- [ ] Revisar os diffs e corrigir qualquer regressão textual, de acessibilidade, concorrência ou comportamento lateral antes da homologação manual.

### Fase 6. Homologação segura, rollout progressivo e rollback

- [ ] Homologar a nova captura em área aberta com GPS bom.
- [ ] Homologar a nova captura em área interna com GPS degradado, mas recuperável.
- [ ] Homologar o fluxo de refresh manual imediatamente após a abertura da página.
- [ ] Homologar o fluxo de refresh manual após uma captura anterior com `accuracy_too_low`.
- [ ] Só depois disso homologar os gatilhos ao abrir a página já autenticada, ao enviar a página para segundo plano e ao trazê-la de volta.
- [ ] Só depois disso homologar o fluxo de submissão manual com localização resolvida após sessão longa de aquisição.
- [ ] Só depois disso homologar o fluxo de `Atividades Automáticas` para garantir ausência de regressão em check-in e check-out automáticos.
- [ ] Homologar em pelo menos dois aparelhos ou perfis de navegador representativos do uso real.
- [ ] Confirmar que a sessão sempre termina de forma finita, sem spinner preso e sem requisições duplicadas.
- [ ] Confirmar que a solução final não alterou o limite administrativo nem afrouxou a regra de negócio.
- [ ] Confirmar que a solução final melhorou a aquisição no frontend preservando o contrato atual do backend.
- [ ] Planejar o rollout em produção de forma progressiva: primeiro com o novo comportamento restrito ao refresh manual, depois aos gatilhos de ciclo de vida e, por último, aos fluxos automáticos.
- [ ] Manter pronto o rollback para a estratégia atual de leitura única por meio do ponto único de fallback definido na Fase 0.
- [ ] Comparar a taxa de `accuracy_too_low` antes e depois da mudança, usando os mesmos cenários de validação.
- [ ] Registrar os resultados da homologação, a calibração final das janelas de captura e a decisão de ativação de cada gatilho antes do encerramento da demanda.