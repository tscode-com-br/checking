# Plano cauteloso para corrigir a dropdown de projetos do IA Settings, garantir persistencia por projeto e validar OpenAI

## 0. Objetivo deste plano

Este documento define um plano de trabalho cuidadoso para tratar tres necessidades relacionadas ao dashboard `transport` em `sistema/app/static/transport`:

1. corrigir de forma robusta a nova dropdown box de projetos do widget `IA SETTINGS`, que hoje aparece vazia em pelo menos um fluxo real;
2. garantir que a chave de API seja gravada e lida por `project_id`, com persistencia criptografada no banco;
3. executar testes cautelosos com o provedor OpenAI usando a chave temporaria fornecida pelo operador, sem gravar o segredo bruto no repositório.

Este plano assume que a base do suporte por `project_id` ja existe no codigo e que o trabalho agora precisa fechar o comportamento de ponta a ponta com consistencia operacional.

## 1. Nota de seguranca obrigatoria

O operador forneceu uma chave temporaria da OpenAI na conversa. Este documento NAO reproduz a chave bruta e NAO deve persistir o segredo em:

- arquivos do repositório;
- fixtures de teste commitados;
- markdown de docs;
- screenshots;
- logs estruturados;
- `print()` de depuracao;
- mensagens de erro;
- snapshots de testes.

Neste plano, a chave temporaria sera referida apenas como `TEMP_OPENAI_PROJECT_KEY`.

Regra operacional:

1. injetar a chave temporaria apenas via ambiente local, terminal atual, segredo do host ou prompt interativo;
2. nunca commitar a chave em `*.py`, `*.js`, `*.json`, `*.md`, `*.env.example` ou artefatos de teste;
3. mascarar sempre o hint e nunca serializar o segredo bruto em auditoria ou snapshot;
4. depois da validacao, remover a chave do ambiente e encerrar a sessao/preview usado no teste.

## 2. Evidencias ja confirmadas no codigo atual

### 2.1 Frontend `transport`

O modal de `IA Settings` no source atual ja contem seletor de projeto em `sistema/app/static/transport/index.html`:

- `data-ai-settings-project`;
- `Project:` como label;
- `Provider:`;
- `API Key:`.

O frontend atual tambem ja tenta:

- ler projetos do dashboard via `state.dashboard.projects`;
- normalizar a lista com `normalizeTransportAiSettingsProjectRows()`;
- fazer fallback para `GET ../api/transport/projects` em `loadTransportAiSettingsProjectCatalog()`;
- enviar `project_id`, `provider` e `api_key` no save.

### 2.2 Backend `transport` / `transport_ai`

O backend atual ja expoe:

- `GET /api/transport/projects` com `response_model=list[ProjectRow]`;
- `GET /api/transport/ai/settings?project_id=<id>`;
- `PUT /api/transport/ai/settings` com `project_id`, `provider`, `api_key`.

O schema `ProjectRow` ja contem `id` e `name`, e `TransportDashboardResponse.projects` tambem ja e `list[ProjectRow]`.

### 2.3 Persistencia por projeto

O modelo `transport_ai_project_llm_settings` ja existe e usa:

- `project_id` com foreign key para `projects.id`;
- `UNIQUE(project_id)`;
- `api_key_ciphertext`;
- `api_key_last4`;
- `provider`, `model_name`, `reasoning_effort`.

O servico de IA Settings atual ja opera por `project_id` para save/load/runtime.

### 2.4 Risco plausivel adicional ja observado

O frontend estatico do `transport` e servido por assets fixos (`index.html`, `styles.css`, `i18n.js`, `app.js`). Quando o contrato do frontend muda de forma incompatível com o backend, browsers podem manter `app.js` antigo e continuar enviando payloads incompletos.

Logo, a dropdown vazia pode resultar de mais de uma causa simultanea:

1. lista de projetos vazia ou nao normalizada;
2. falha de autenticacao ou fallback em `/api/transport/projects`;
3. shape de projeto inconsistente entre dashboard e endpoint dedicado;
4. assets antigos em cache, mostrando uma UI desatualizada ou enviando payload legado;
5. estado local do modal sendo limpo cedo demais.

## 3. Resultado esperado

Ao final deste trabalho, o comportamento aceito deve ser este:

1. ao abrir `IA SETTINGS`, o usuario ve uma lista de projetos confiavel, nao vazia quando houver projetos cadastrados e sessao valida;
2. o projeto selecionado e sempre um `project_id` valido, nunca um nome livre;
3. o save de OpenAI grava uma linha criptografada para aquele projeto no banco;
4. outro projeto nao herda hint, provider, draft ou chave por engano;
5. o runtime da IA usa a configuracao do projeto correto;
6. erros de catalogo, sessao e projeto ausente sao diagnosticados com mensagens controladas;
7. testes automatizados cobrem o contrato de dropdown, persistencia por projeto e smoke OpenAI opt-in;
8. nenhum teste commitado depende da chave real da OpenAI para passar no CI padrao.

## 4. Principios de implementacao

1. tratar o endpoint dedicado `/api/transport/projects` como fonte autoritativa para a dropdown do modal;
2. usar `state.dashboard.projects` e cache local apenas como bootstrap visual e fallback temporario, nao como unica fonte de verdade;
3. nunca permitir que o fluxo de save dependa implicitamente de estado anterior nao confirmado;
4. exigir `project_id` em todos os saves e tratar sua ausencia como erro funcional explicito;
5. nao colocar o segredo OpenAI em fixtures permanentes;
6. diferenciar testes automatizados de contrato dos testes de smoke com provedor real;
7. validar cada fase com o recorte mais estreito possivel antes de ampliar escopo.

## 5. Plano de trabalho detalhado

## Fase 0 - Diagnostico fechado da dropdown vazia

### Objetivo

Descobrir exatamente por que a lista aparece vazia em runtime, em vez de assumir que o problema esta apenas no HTML ou apenas no backend.

### Arquivos principais a inspecionar

- `sistema/app/static/transport/app.js`
- `sistema/app/static/transport/index.html`
- `sistema/app/static/transport/i18n.js`
- `sistema/app/routers/transport.py`
- `sistema/app/schemas.py`
- `tests/transport_page_date.test.js`

### Hipoteses que precisam ser discriminadas

1. `state.dashboard.projects` esta vindo vazio do dashboard em fluxos reais.
2. `/api/transport/projects` esta falhando por sessao expirada, prefixo incorreto, cache, ou diferenca de deploy.
3. `normalizeTransportAiSettingsProjectRows()` esta descartando itens validos por shape inesperado.
4. a pagina em producao/homologacao esta servindo `app.js` antigo e, por isso, a UI real nao corresponde ao source atual.
5. o modal abre antes da lista autoritativa estar pronta e depois nao reconcilia corretamente.

### Checagens obrigatorias

1. capturar o payload real de `GET /api/transport/dashboard` e verificar se `projects` existe, quantos itens traz e se cada item contem ao menos `id` e `name`.
2. capturar o payload real de `GET /api/transport/projects` na mesma sessao.
3. comparar os dois payloads e identificar divergencias de shape, ordenacao, filtros ou auth.
4. confirmar no HTML servido em runtime se o modal contem `data-ai-settings-project`.
5. confirmar se `index.html` servido em runtime referencia `styles.css`, `i18n.js` e `app.js` na versao esperada.
6. reproduzir a abertura do modal com logging temporario local ou depuracao de rede, verificando a transicao de:
   - `state.aiSettingsProjects`
   - `state.aiSettingsSelectedProjectId`
   - `state.aiSettingsDraft.projectId`
7. confirmar se o usuario esta autenticado e se `require_transport_session` esta passando tanto no dashboard quanto em `/projects`.

### Saida esperada da fase

1. causa primaria da dropdown vazia identificada com evidencia;
2. causa secundaria registrada, se houver combinacao de cache + dados + sessao;
3. decisao clara sobre qual sera a fonte autoritativa do catalogo de projetos.

## Fase 1 - Tornar a carga da dropdown robusta e consistente

### Objetivo

Fazer a dropdown de projetos depender de um fluxo previsivel, resiliente a cache antigo, shape inconsistente e ordem de carregamento.

### Recomendacao de implementacao

Adotar o seguinte contrato de frontend para o modal `IA SETTINGS`:

1. ao abrir o modal, renderizar imediatamente projetos do cache local/dashboard apenas como estado inicial, se existirem;
2. em paralelo, sempre disparar um refresh autoritativo para `GET /api/transport/projects`;
3. somente apos esse refresh marcar o catalogo como `ready`;
4. preservar `selectedProjectId` se o projeto ainda existir na resposta autoritativa;
5. se o projeto selecionado nao existir mais, limpar hint e draft e selecionar o primeiro projeto valido ou exibir estado vazio controlado;
6. se o endpoint falhar, mostrar feedback explicito de carga de projetos, sem confundir com erro de provider;
7. nao deixar o botao `Save` habilitado enquanto o catalogo estiver em estado inconsistente (`loading` sem selecao valida, ou sem projeto valido);
8. manter `project_id` como valor canonical do formulario, nunca derivado de texto livre.

### Mudancas concretas a planejar no frontend

1. Introduzir estado explicito do catalogo de projetos do modal, por exemplo:
   - `idle`
   - `loading`
   - `ready`
   - `empty`
   - `error`
2. Garantir que a dropdown sempre tenha um placeholder consistente (`Selecione um projeto`) e que `Save` permaneça desabilitado sem um `projectId` valido.
3. Garantir que `loadTransportAiSettingsProjectCatalog()` nao trate `dashboard.projects` como resposta final silenciosa.
4. Encapsular a reconciliacao do catalogo em uma funcao unica, para evitar que `applyTransportAiSettingsProjects()` seja chamada com listas parcialmente normalizadas em pontos diferentes.
5. Adicionar cache-busting/versionamento dos assets do `transport` sempre que o contrato do modal mudar de forma incompatível com clientes antigos.
6. Melhorar a mensagem local do erro 422 para apontar `projeto obrigatorio` quando o backend reclamar de `project_id` ausente, evitando o genérico `Field required`.

### Decisao de UX recomendada

1. se houver projetos validos e o autoritativo ainda estiver carregando, mostrar dropdown populada + feedback discreto de carregamento;
2. se o autoritativo falhar e nao houver nenhum projeto local valido, mostrar estado vazio com erro controlado;
3. se o autoritativo falhar mas houver projetos locais validos, manter a lista visivel, mas registrar no plano se o `Save` ficara bloqueado ou nao nessa condicao.

Recomendacao cautelosa: bloquear `Save` enquanto o catalogo nao estiver `ready`, para evitar gravacao com estado potencialmente obsoleto.

## Fase 2 - Confirmar e endurecer a gravacao por projeto no banco

### Objetivo

Assegurar que o save do modal realmente grava uma configuracao OpenAI distinta por projeto, com criptografia e isolamento corretos.

### Observacao importante

A base de persistencia por `project_id` ja existe. Logo, esta fase deve priorizar verificacao, endurecimento e correcoes pequenas, nao redesenho amplo.

### Checagens obrigatorias

1. confirmar que `PUT /api/transport/ai/settings` recebe sempre:
   - `project_id`
   - `provider`
   - `api_key`
2. confirmar que `upsert_transport_ai_llm_settings()` esta sendo chamado com o `project_id` esperado;
3. confirmar que o banco persiste em `transport_ai_project_llm_settings` e nao no singleton legado;
4. confirmar que `api_key_ciphertext` difere do segredo bruto;
5. confirmar que `api_key_last4` e preenchido;
6. confirmar que o `GET /api/transport/ai/settings?project_id=...` retorna apenas hint mascarado e metadados do projeto;
7. confirmar que trocar o provider exige nova chave e nao reaproveita segredo de outro projeto;
8. confirmar que projeto A e projeto B permanecem isolados apos saves sucessivos.

### Ajustes de backend a considerar, se o diagnostico apontar lacuna

1. tornar mensagens 404/409/422 mais especificas para projeto ausente, projeto nao selecionado, projeto sem configuracao e projeto removido;
2. reforcar logs de auditoria com `project_id` e `project_name` em sucesso e falha;
3. reforcar sanitizacao em qualquer nova superficie tocada na investigacao;
4. reforcar rollback de sessao antes de auditoria de falha, caso seja encontrada qualquer regressao nesse ponto.

## Fase 3 - Ajustar a leitura de runtime para ficar coerente com o save

### Objetivo

Garantir que a configuracao salva para cada projeto seja a mesma efetivamente usada pela IA no runtime.

### Checagens obrigatorias

1. confirmar que o runtime resolve `project_id` por particao/projeto na execucao;
2. confirmar que projetos diferentes nao compartilham segredo por acidente;
3. confirmar que, se houver conflito de runtime entre projetos, a run falha em preflight com mensagem clara;
4. confirmar que `llm_runtime_projects` continua refletindo o projeto correto, sem `api_key` ou `api_key_ciphertext`;
5. confirmar que historico e diagnostico nao mentem quando houver mais de um projeto na mesma run.

### Arquivos a revalidar

- `sistema/app/services/transport_ai_llm_settings.py`
- `sistema/app/services/transport_ai_runtime.py`
- `sistema/app/services/transport_ai_agent.py`
- `sistema/app/services/transport_ai_runs.py`
- `sistema/app/routers/transport_ai.py`

## Fase 4 - Estrategia de testes automatizados

### Objetivo

Proteger o novo contrato da dropdown e do save por projeto sem depender da chave real no CI padrao.

### 4.1 Testes frontend obrigatorios

Arquivo principal:

- `tests/transport_page_date.test.js`

Adicionar ou revisar casos para cobrir:

1. dropdown popula corretamente com `dashboard.projects` quando o dashboard traz itens validos;
2. dropdown faz refresh autoritativo com `GET /projects` ao abrir o modal;
3. se `dashboard.projects` vier vazio e `/projects` vier preenchido, a lista deixa de ficar vazia;
4. se `/projects` vier vazio, a UI mostra estado controlado de `sem projetos`;
5. se `/projects` falhar, a UI mostra erro especifico de catalogo, nao erro de provider;
6. `Save` fica bloqueado quando nao ha `projectId` valido;
7. quando o backend retorna 422 por `project_id` ausente, a mensagem fica clara e nao generica;
8. troca de projeto continua isolando `provider`, `api_key_hint` e draft;
9. a ordem do mock de `fetch` continua tratando `/ai/settings` antes de `/settings`, para os testes nao ficarem enganosos;
10. o HTML do `transport` referencia assets versionados quando o contrato do modal mudar.

### 4.2 Testes backend obrigatorios

Arquivos principais:

- `tests/test_transport_ai_llm_settings.py`
- `tests/test_transport_ai_router.py`
- `tests/test_transport_ai_runtime.py`
- `tests/test_transport_ai_agent_runtime.py`

Cobrir especificamente:

1. save OpenAI para projeto A persiste `provider=openai`, `api_key_ciphertext` nao vazio e `api_key_last4` correto;
2. save OpenAI para projeto B nao altera projeto A;
3. `GET /ai/settings?project_id=A` retorna hint mascarado apenas de A;
4. `PUT /ai/settings` sem `project_id` retorna erro controlado e message clara;
5. projeto inexistente retorna 404 controlado;
6. provider change exige nova chave;
7. falhas nao vazam segredo bruto nem ciphertext;
8. runtime e snapshots continuam sem `api_key` e sem `api_key_ciphertext`.

### 4.3 Testes de smoke opt-in com OpenAI real

Esses testes NAO devem rodar por padrao no CI.

Recomendacao:

1. criar um smoke manual ou teste opt-in que so roda quando uma variavel de ambiente estiver presente, por exemplo:
   - `TRANSPORT_AI_TEST_OPENAI_API_KEY`
2. esse smoke deve usar a chave temporaria fornecida pelo operador apenas via ambiente local;
3. o teste deve ser pulado automaticamente quando a variavel estiver ausente;
4. nenhum assert deve imprimir o segredo bruto em caso de falha.

Casos do smoke OpenAI real:

1. abrir preview isolado com DB dedicado;
2. autenticar no `/transport`;
3. garantir existencia de pelo menos um projeto de teste;
4. salvar `provider=openai` para projeto A usando `TRANSPORT_AI_TEST_OPENAI_API_KEY`;
5. confirmar hint mascarado no GET subsequente;
6. validar no banco que ha linha criptografada para o `project_id` correto;
7. executar `Calculate Routes` em um request do projeto A;
8. confirmar que a run chega ao menos ate `suggestion ready` sem erro de configuracao;
9. opcionalmente aplicar a sugestao se o ambiente de preview estiver preparado para isso.

## Fase 5 - Plano de validacao manual com a chave temporaria OpenAI

### Objetivo

Usar a chave temporaria fornecida pelo operador para validar o fluxo real de OpenAI por projeto, sem contaminar o repositório.

### Preparacao

1. escolher uma instancia preview isolada ou subir um preview local dedicado ao teste;
2. garantir `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY` valida no ambiente;
3. garantir sessao `transport` autenticada;
4. escolher dois projetos de teste:
   - projeto A para OpenAI;
   - projeto B para controle negativo ou outro provider.

### Procedimento manual recomendado

1. injetar `TEMP_OPENAI_PROJECT_KEY` apenas no terminal atual ou por prompt manual;
2. abrir `IA SETTINGS`;
3. confirmar que a dropdown lista projeto A e projeto B;
4. selecionar projeto A;
5. salvar `provider=OpenAI` e a chave temporaria;
6. confirmar `api_key_hint` mascarado no reload do modal;
7. consultar diretamente a tabela `transport_ai_project_llm_settings` e confirmar:
   - linha para `project_id` de A;
   - `provider=openai`;
   - `api_key_ciphertext` preenchido;
   - nenhum segredo bruto persistido em texto claro;
8. selecionar projeto B e confirmar que o hint nao foi herdado de A;
9. executar o fluxo de IA para um request do projeto A;
10. revisar logs/auditoria e confirmar que nao houve vazamento do segredo;
11. remover a chave do ambiente e encerrar o preview apos a validacao.

### Evidencias a coletar

1. payload HTTP sanitizado do save (sem segredo bruto);
2. resposta HTTP do GET com `api_key_hint` mascarado;
3. linha do banco validando `project_id` correto e ciphertext preenchido;
4. status da run/sugestao confirmando que o runtime leu a configuracao do projeto certo.

## Fase 6 - Mudancas de documentacao e operacao

### Objetivo

Deixar a equipe com um fluxo operacional claro para nao reintroduzir a dropdown vazia e para usar OpenAI por projeto com seguranca.

### Atualizacoes recomendadas

1. documentar que o catalogo de projetos do modal deve ser carregado do endpoint autoritativo `/api/transport/projects`;
2. documentar que `project_id` e obrigatorio no save de `IA Settings`;
3. documentar que chaves OpenAI reais so podem ser usadas em smoke opt-in e nunca em testes commitados;
4. documentar como versionar assets do `transport` quando houver mudanca de contrato do frontend;
5. documentar que o caminho legado global continua apenas para consulta/rollback ate sua remocao definitiva;
6. documentar o procedimento de limpeza da chave temporaria apos a validacao.

## 6. Ordem recomendada de execucao

1. fechar o diagnostico da dropdown vazia com captura de payloads reais;
2. decidir e implementar a fonte autoritativa do catalogo de projetos;
3. corrigir eventuais problemas de reconciliacao de `selectedProjectId`;
4. validar que o save continua chegando com `project_id` e gravando no banco por projeto;
5. ampliar os testes frontend e backend;
6. executar smoke OpenAI opt-in com `TEMP_OPENAI_PROJECT_KEY` em preview isolado;
7. revisar logs, auditoria e tabela do banco;
8. atualizar docs/runbook.

## 7. Criterios de aceite deste trabalho

Considerar a entrega concluida apenas quando todos os itens abaixo forem verdadeiros:

1. a dropdown de projetos do modal `IA SETTINGS` nao fica vazia quando ha projetos cadastrados e sessao valida;
2. o catalogo de projetos do modal passa por uma carga autoritativa consistente e diagnosticavel;
3. o `Save` nao dispara sem `project_id` valido;
4. um save OpenAI para projeto A persiste apenas em `transport_ai_project_llm_settings` do projeto A;
5. projeto B nao herda provider, hint ou chave do projeto A;
6. o runtime da IA usa a configuracao certa do projeto salvo;
7. testes automatizados de frontend e backend protegem a dropdown, o payload e a persistencia por projeto;
8. o smoke OpenAI opt-in com `TEMP_OPENAI_PROJECT_KEY` foi executado sem gravar o segredo no repositório;
9. a equipe ficou com runbook claro para repetir o processo sem improviso.

## 8. Rollback planejado

Se alguma mudanca desta rodada introduzir regressao, fazer rollback apenas da menor superficie necessaria:

1. se a regressao estiver na dropdown, reverter apenas a logica de catalogo do modal mantendo o backend por `project_id` intacto;
2. se a regressao estiver no save, reverter apenas a mudanca do fluxo de formulario mantendo a persistencia por projeto;
3. se a regressao estiver no smoke OpenAI real, remover a validacao opt-in sem tocar nos testes de contrato;
4. nunca fazer rollback que reintroduza chave global implicita sem decisao explicita.

## 9. Recomendacao final

A recomendacao mais consistente e tratar este trabalho como um fechamento de ponta a ponta do fluxo ja iniciado em `temp_009.md`:

1. primeiro estabilizar a dropdown com fonte autoritativa clara e cache-control de assets;
2. depois confirmar persistencia real por `project_id` no banco;
3. por fim, validar OpenAI real com smoke opt-in usando a chave temporaria fora do repositório.

Essa ordem reduz risco, evita diagnosticos falsos e impede que um problema de UI esconda um problema de persistencia, ou vice-versa.