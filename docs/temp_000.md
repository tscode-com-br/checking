# Planejamento Detalhado da Alteração do Admin e da Persistência de Eventos

Data: 2026-04-25

## Objetivo

Executar uma alteração coordenada no backend e no painel admin para:

1. esvaziar a tabela `check_events` uma única vez;
2. garantir que as atividades de `check-in` e `check-out` dos usuários continuem sendo auditadas em `check_events`;
3. impedir que eventos originados do endpoint `POST /api/provider/updaterecords` sejam gravados em `check_events`;
4. adicionar a nova aba `Relatórios` no admin, entre `Cadastro` e `Eventos`;
5. permitir busca por pessoa via `chave` ou `nome`, com bloqueio mútuo entre os campos;
6. listar o histórico encontrado em ordem decrescente de data, com a data mais recente aparecendo primeiro.

## Estado Atual Confirmado no Código

Os pontos abaixo foram verificados diretamente no código atual:

- `check_events` é a tabela modelada por `CheckEvent` em `sistema/app/models.py`.
- O logger genérico de auditoria é `log_event(...)` em `sistema/app/services/event_logger.py`.
- Os fluxos de RFID/leitor (`sistema/app/routers/device.py`), mobile (`sistema/app/routers/mobile.py`) e web (`sistema/app/services/forms_submit.py` via `sistema/app/routers/web_check.py`) já gravam atividades em `check_events`.
- O endpoint `POST /api/provider/updaterecords` em `sistema/app/routers/provider.py` também grava hoje em `check_events`, o que entra em conflito com a nova regra solicitada.
- A aba `Forms` do admin hoje depende diretamente de registros `source="provider"` dentro de `check_events`, via `build_provider_forms_rows(...)` e `delete_provider_forms_rows(...)` em `sistema/app/routers/admin.py`.
- O admin web é uma SPA estática em `sistema/app/static/admin/index.html`, `sistema/app/static/admin/app.js` e `sistema/app/static/admin/styles.css`.
- As abas atuais do admin são `Check-In`, `Check-Out`, `Forms`, `Inativos`, `Cadastro` e `Eventos`.
- A visibilidade das abas é controlada em `sistema/app/static/admin/app.js` por `TAB_LABELS`, `DEFAULT_ADMIN_ALLOWED_TABS`, `LIMITED_ADMIN_ALLOWED_TABS` e `applyAdminTabVisibility()`.
- A sessão admin com acesso limitado só pode ver `checkin` e `checkout`; novas áreas devem, por padrão, ficar restritas a admin pleno.
- O campo `action` de `check_events` é truncado para 16 caracteres em `log_event(...)`, então nomes novos de ação precisam ser curtos.

## Conclusões Técnicas que Impactam o Planejamento

### 1. Conflito direto entre a nova regra do `updaterecords` e a aba `Forms`

Hoje a aba `Forms` usa `check_events` como fonte. Se `updaterecords` deixar de gravar nessa tabela, a aba `Forms` perde sua fonte atual de dados.

Isso significa que a implementação não pode tratar o item 3 como uma simples remoção de `log_event(...)` sem decidir o futuro da aba `Forms`.

### 2. A nova aba `Relatórios` não deve, por padrão, consumir os logs brutos de `check_events`

`check_events` é uma trilha de auditoria técnica. Em um único fluxo de RFID, por exemplo, podem existir múltiplas linhas para a mesma operação lógica do usuário, como `received`, `queued`, `updated`, `blocked` ou `duplicate`.

Para um relatório orientado a pessoa, isso tende a gerar duplicidade visual e confusão.

O melhor desenho funcional é:

- manter `check_events` como trilha de auditoria técnica;
- usar uma fonte canônica de atividades humanas para a aba `Relatórios`, preferencialmente `user_sync_events`;
- decidir explicitamente se eventos vindos de `provider/updaterecords` devem ou não aparecer no relatório.

### 3. Busca por nome precisa tratar ambiguidade

`chave` é o identificador operacional mais estável do sistema. `nome` não é uma chave única.

Portanto, a busca por nome precisa prever este comportamento:

- nenhum usuário encontrado: retornar `404`;
- exatamente um usuário encontrado: retornar o histórico;
- mais de um usuário com o mesmo nome normalizado: retornar `409` orientando o administrador a usar a `chave`.

Sem esse tratamento, o sistema corre o risco de misturar eventos de pessoas diferentes, exatamente o cenário que o item 7 quer evitar.

## Decisões Fechadas na Etapa 1

As decisões bloqueadoras foram fechadas com a direção abaixo, para evitar ambiguidade nas próximas etapas.

### 1. Escopo funcional da aba `Relatórios`

- A aba `Relatórios` deve listar todos os eventos humanos consolidados da pessoa, inclusive os oriundos de `POST /api/provider/updaterecords`.
- A fonte primária do relatório deve ser `user_sync_events`, e não `check_events`.
- `check_events` continua como trilha técnica de auditoria, mas deixa de ser a fonte correta do relatório por pessoa.

### 2. Destino funcional da aba `Forms`

- A aba `Forms` deve continuar existindo no admin.
- Ela deve ser desacoplada de `check_events`.
- O comportamento alvo passa a ser de visão operacional do que veio do provider, reconstruída a partir de `user_sync_events` e dados de `users`, com campos derivados de `action`, `ontime`, `event_time`, `created_at`, `chave`, `nome` e `projeto`.
- O botão `Limpar` atual não pode manter a semântica de apagar histórico canônico; ele deverá ser removido, desabilitado ou substituído por ação não destrutiva na etapa própria da aba `Forms`.

### 3. Escopo da remoção em `check_events`

- Nenhuma chamada originada de `POST /api/provider/updaterecords` deve persistir linhas em `check_events`.
- Isso inclui autenticação inválida, duplicidade e processamento bem-sucedido.
- Se algum rastreamento adicional for necessário para esse endpoint, ele deve ficar em logs de aplicação ou no histórico canônico, não em `check_events`.

### 4. Regras complementares já fixadas

1. A aba `Relatórios` deve ser acessível apenas por admin pleno.
2. A busca deve aceitar exatamente um critério por vez: `chave` ou `nome`.
3. O backend também deve validar essa exclusividade, não apenas o frontend.
4. O relatório deve ordenar por `event_time desc, id desc`.
5. A limpeza total de `check_events` deve ser uma ação de rollout/migração operacional, e não uma exclusão automática em startup.

## Arquivos Potencialmente Afetados

- `sistema/app/routers/provider.py`
- `sistema/app/routers/admin.py`
- `sistema/app/schemas.py`
- `sistema/app/services/event_logger.py` ou eventual helper de política de auditoria
- `sistema/app/static/admin/index.html`
- `sistema/app/static/admin/app.js`
- `sistema/app/static/admin/styles.css`
- `tests/test_api_flow.py`
- testes JS do admin em `tests/*.test.js`

## Planejamento Descritivo por Fases

## Fase 0. Definição funcional concluída

As decisões de produto que bloqueavam a implementação já foram fechadas:

1. O relatório deve incluir eventos do `updaterecords`, mas sem depender de `check_events`.
2. A aba `Forms` deve continuar existindo, porém com nova fonte fora de `check_events`.
3. `check_events` deve deixar de receber qualquer linha oriunda de `POST /api/provider/updaterecords`.

## Fase 1. Ajuste da política de gravação em `check_events`

Objetivo desta fase:

- manter a gravação de eventos de usuário nos fluxos já corretos;
- remover a gravação originada do `updaterecords`.

Passos previstos:

1. Revisar todos os pontos que criam `UserSyncEvent` e confirmar se cada origem relevante tem ou não um `log_event(...)` correspondente.
2. Manter os logs atuais de RFID, mobile e web.
3. Remover de `sistema/app/routers/provider.py` as gravações em `check_events` vinculadas ao `PROVIDER_REQUEST_PATH`.
4. Garantir que a remoção não quebre atualização de estado do usuário, `user_sync_events`, `checkinghistory` e notificações do admin.
5. Remover também de `check_events` os erros de autenticação e duplicidade ligados ao `updaterecords`, mantendo esse endpoint totalmente fora dessa tabela.

Interpretação recomendada para o item 3 da solicitação:

- qualquer evento cujo fato de negócio venha do endpoint `POST /api/provider/updaterecords` não deve ser persistido em `check_events`.

## Fase 2. Tratamento explícito da dependência da aba `Forms`

Esta fase é obrigatória porque o item 3 cria impacto colateral real.

Situação atual:

- `GET /api/admin/forms` lê `CheckEvent` com `source="provider"`;
- `DELETE /api/admin/forms` apaga essas linhas em `check_events`.

Como `updaterecords` deixará de escrever ali, o caminho fechado na Etapa 1 é manter a aba `Forms`, porém reconstruí-la fora de `check_events`.

Diretrizes desta fase:

1. `GET /api/admin/forms` deve passar a ler a trilha canônica de provider em `user_sync_events`, enriquecendo os dados com `users`.
2. Os campos de exibição hoje lidos de `CheckEvent.details` devem ser recalculados a partir de dados persistidos e derivados, sem depender do payload bruto salvo em `check_events`.
3. A aba `Forms` deve se tornar uma visão operacional de leitura, e não um painel de exclusão de histórico.
4. `DELETE /api/admin/forms` deve ser removido, desabilitado ou redefinido como ação não destrutiva.

Observação importante:

- usar `user_sync_events` como fonte da aba `Forms` é viável para leitura;
- apagar `user_sync_events` para “limpar a aba” é inadequado, porque essa tabela é histórica e canônica.

## Fase 3. Limpeza total de `check_events`

O item 1 deve ser tratado como ação operacional controlada.

Implementação recomendada:

- preparar instrução SQL ou script de manutenção para executar `DELETE FROM check_events;` uma única vez no rollout.

Justificativa:

- não é seguro colocar exclusão automática no startup;
- isso apagaria a trilha toda a cada deploy ou reinício;
- a ação precisa ser executada uma vez, em janela controlada.

Cuidados de rollout:

1. aplicar o novo código primeiro;
2. confirmar que o tráfego está estável;
3. executar a limpeza;
4. validar que novos eventos corretos voltam a entrar após a limpeza.

Observação técnica:

- o fluxo de RFID usa `check_events` como parte da idempotência por `request_id`;
- portanto, a limpeza deve ocorrer com ciência de que o histórico antigo dessa proteção será descartado.

## Fase 4. Criação da API da aba `Relatórios`

Objetivo desta fase:

- disponibilizar uma rota do admin para buscar uma pessoa e devolver o histórico solicitado.

Desenho recomendado da rota:

- `GET /api/admin/reports/events`

Parâmetros esperados:

- `chave` opcional
- `nome` opcional

Validações obrigatórias:

1. um dos dois parâmetros é obrigatório;
2. os dois não podem ser enviados ao mesmo tempo;
3. strings vazias ou compostas apenas por espaços devem ser tratadas como ausentes;
4. `chave` deve ser normalizada para caixa alta;
5. `nome` deve ser normalizado para comparação case-insensitive.

Comportamento recomendado:

1. resolver a pessoa procurada primeiro;
2. se a busca for por nome e houver mais de uma pessoa compatível, retornar `409` com mensagem clara;
3. buscar o histórico já ordenado do mais recente para o mais antigo;
4. devolver também metadados da pessoa encontrada para renderização do cabeçalho do relatório.

Fonte de dados recomendada para o relatório:

- `user_sync_events`, porque fornece uma linha por atividade humana e evita duplicidade de logs técnicos.

Estrutura mínima sugerida do payload:

- dados da pessoa: `id`, `nome`, `chave`, `rfid`, `projeto`
- lista de eventos: `source`, `action`, `local`, `ontime`, `event_time`, `timezone_name`, `timezone_label`
- campo derivado de data para agrupamento visual

Se a decisão funcional for usar `check_events` como fonte do relatório, então será necessário filtrar apenas estados finais de atividade, para evitar que uma única ação do usuário gere várias linhas no relatório.

## Fase 5. Inclusão da aba `Relatórios` na SPA do admin

Objetivo desta fase:

- inserir a nova aba sem quebrar navegação, permissões e layout.

Passos previstos:

1. em `sistema/app/static/admin/index.html`, inserir o botão `Relatórios` entre `Cadastro` e `Eventos`.
2. criar a seção `tab-relatorios` com:
   - label `Busca por Chave:` e input ao lado;
   - abaixo, label `Busca por Nome:` e input ao lado;
   - abaixo do campo `Nome`, botão `Buscar`.
3. criar uma área de resultado abaixo do formulário, com estado vazio, estado de erro e estado com dados.
4. atualizar `TAB_LABELS` em `sistema/app/static/admin/app.js`.
5. adicionar `relatorios` em `DEFAULT_ADMIN_ALLOWED_TABS`.
6. manter `LIMITED_ADMIN_ALLOWED_TABS` sem `relatorios`.
7. garantir que `applyAdminTabVisibility()` trate a nova aba como qualquer outra aba protegida.

## Fase 6. Padronização da largura das abas

Solicitação explícita do usuário:

- todas as abas devem ter a mesma largura.

Implementação mais simples e segura:

1. manter o container `.tabs` com layout flexível ou grid;
2. aplicar crescimento uniforme aos botões visíveis, por exemplo com `flex: 1 1 0`;
3. confiar no atributo `hidden`, que já retira abas não permitidas do layout, para que apenas as abas visíveis dividam o espaço igualmente.

Isso evita cálculo manual de largura e funciona tanto para admin pleno quanto para admin limitado.

## Fase 7. Regra de bloqueio mútuo entre `chave` e `nome`

Objetivo desta fase:

- evitar combinação de dados de pessoas diferentes.

Comportamento exigido no frontend:

1. se o input `chave` tiver um ou mais caracteres, o input `nome` deve ficar desabilitado;
2. se o input `nome` tiver um ou mais caracteres, o input `chave` deve ficar desabilitado;
3. se o campo preenchido voltar a ficar vazio, o outro campo deve ser reabilitado.

Comportamento obrigatório no backend:

1. rejeitar requisições com `chave` e `nome` simultaneamente;
2. rejeitar requisições sem nenhum dos dois;
3. não confiar apenas na desativação visual do frontend.

## Fase 8. Renderização do relatório ordenado por data

Objetivo desta fase:

- exibir o histórico de forma compreensível para o administrador.

Estratégia recomendada:

1. o backend devolve eventos em ordem `desc`;
2. o frontend agrupa visualmente por data do evento;
3. a data mais recente aparece primeiro;
4. dentro da data, os eventos também ficam em ordem decrescente de horário.

Renderização sugerida:

- cabeçalho da pessoa encontrada;
- separadores de data;
- linhas contendo horário, ação, origem, local, projeto e assiduidade;
- mensagem amigável quando a pessoa não tiver eventos.

## Fase 9. Cobertura de testes

Esta mudança exige teste de backend e frontend.

### Backend

Adicionar ou ajustar testes em `tests/test_api_flow.py` para cobrir:

1. `updaterecords` não grava mais em `check_events`;
2. RFID continua gravando eventos em `check_events`;
3. mobile continua gravando eventos em `check_events`;
4. web continua gravando eventos em `check_events`;
5. busca de relatório por `chave` retorna a pessoa correta;
6. busca de relatório por `nome` retorna a pessoa correta quando houver correspondência única;
7. busca por `nome` retorna `409` quando houver ambiguidade;
8. busca sem critério retorna `400`;
9. busca com `chave` e `nome` simultâneos retorna `400`;
10. ordenação do relatório vem do mais recente para o mais antigo.

### Frontend

Adicionar novo teste JS e ajustar os existentes para cobrir:

1. a aba `Relatórios` existe entre `Cadastro` e `Eventos`;
2. as abas usam largura uniforme;
3. os labels e inputs da nova aba existem;
4. o botão `Buscar` existe;
5. o JavaScript implementa o bloqueio mútuo entre os inputs;
6. a nova aba entra no conjunto de abas permitidas para admin pleno;
7. a nova aba não entra no conjunto limitado.

Também será necessário revisar testes existentes que hoje assumem a estrutura atual das abas ou a permanência de dados de `provider` em `check_events`.

## Fase 10. Validação manual e rollout

Após os testes automatizados passarem:

1. abrir o admin localmente;
2. validar que a nova aba aparece na posição correta;
3. validar que todas as abas visíveis têm a mesma largura;
4. validar a desativação entre os campos `chave` e `nome`;
5. validar busca bem-sucedida por `chave`;
6. validar busca bem-sucedida por `nome`;
7. validar retorno de erro quando o nome for ambíguo;
8. validar que `updaterecords` continua atualizando estado local do usuário sem criar linhas em `check_events`;
9. validar que eventos de RFID, mobile e web continuam aparecendo em `Eventos`;
10. executar a limpeza total de `check_events` e confirmar que novos eventos entram corretamente depois da limpeza.

## To-do Completo de Execução

### Etapa 1. Decisões bloqueadoras e alinhamento funcional

Objetivo: fechar as definições que impactam backend, frontend e comportamento operacional antes de alterar código.

- [x] Fechar a regra funcional do relatório: incluir eventos oriundos de `updaterecords`, usando `user_sync_events` como fonte primária em vez de `check_events`.
- [x] Fechar o destino funcional da aba `Forms`: mantê-la no admin, mas desacoplada de `check_events` e sem limpeza destrutiva do histórico canônico.

### Etapa 1A. Checklist de preparação para a Etapa 2

Objetivo: validar o corte do diff mínimo antes de alterar backend e testes, reduzindo o risco de abrir escopo sem necessidade.

- [x] Confirmar que a execução da Etapa 2 ficará restrita a `sistema/app/routers/provider.py` e `tests/test_api_flow.py`.
- [x] Confirmar que `admin.py`, `schemas.py` e a SPA do admin não entrarão no primeiro diff da Etapa 2.
- [x] Confirmar que o endpoint `POST /api/provider/updaterecords` deve ficar totalmente fora de `check_events`, incluindo `401`, duplicidade e sucesso.
- [x] Confirmar que `users`, `user_sync_events` e `checkinghistory` devem permanecer intactos após a remoção dos logs de provider em `check_events`.
- [x] Confirmar que `notify_admin_data_changed("event")` será removido do fluxo de provider, mas os avisos funcionais de `action` e `register` permanecem candidatos a seguir ativos.
- [x] Separar os testes que mudam agora dos testes que ficam para a Etapa 3, especialmente a aba `Forms`.
- [x] Definir a validação mínima pós-edit da Etapa 2: rodar apenas os testes focados de provider e confirmar ausência de linhas `source="provider"` em `check_events`.

Resultado consolidado da Etapa 1A:

1. O primeiro diff da Etapa 2 deve ficar limitado a `sistema/app/routers/provider.py` e `tests/test_api_flow.py`.
2. O fluxo atual de provider grava em `check_events` em tres pontos distintos: `401` por shared key invalida, duplicidade e sucesso; os tres devem sair da tabela.
3. A persistencia funcional que precisa permanecer vem de `create_user_sync_event(...)`, que continua gravando `UserSyncEvent` e `checkinghistory` independentemente de `check_events`, enquanto `provider.py` continua responsável por atualizar `users` quando aplicavel.
4. `notify_admin_data_changed("event")` deve sair do fluxo de provider por estar acoplado ao log tecnico; `notify_admin_data_changed(action)` e `notify_admin_data_changed("register")` ainda fazem sentido porque o painel reage genericamente ao stream e o provider continua podendo alterar estado atual e cadastro/projeto.
5. Testes que entram agora na Etapa 2:
   - `test_provider_endpoint_requires_valid_shared_key()`
   - `test_provider_endpoint_never_enqueues_forms_even_for_multiple_events()`
   - novo teste focado para garantir ausencia de `CheckEvent` de provider em `401`, duplicidade e sucesso
6. Testes que devem ficar para a Etapa 3, por dependerem da aba `Forms` ou de seu contrato atual:
   - `test_admin_can_clear_forms_rows_without_archiving()`
   - `test_admin_provider_forms_rows_include_timezone_metadata_for_non_singapore_project()`
   - `test_provider_same_day_events_do_not_override_web_state_and_are_reported_in_forms()`
7. Validacao minima pos-edit da Etapa 2:
   - rodar apenas os testes focados de provider em `tests/test_api_flow.py`
   - confirmar ausencia de linhas `CheckEvent` com `source="provider"` ou `request_path="/api/provider/updaterecords"`
   - confirmar que `users`, `UserSyncEvent` e `CheckingHistory` seguem corretos

### Etapa 2. Ajuste da persistência e da trilha de auditoria

Objetivo: garantir que `check_events` continue refletindo os eventos corretos e deixe de receber dados do `updaterecords`.

- [x] Revisar todos os call sites de `log_event(...)` ligados a atividades de usuário.
- [x] Remover em `provider.py` a persistência de eventos do `updaterecords` em `check_events`.
- [x] Garantir que `provider.py` continue atualizando `users`, `user_sync_events` e `checkinghistory`.
- [x] Ajustar notificações do admin para não dependerem exclusivamente da gravação em `check_events`.

Resultado consolidado da Etapa 2:

1. O diff aplicado permaneceu dentro do corte aprovado: apenas `sistema/app/routers/provider.py` e `tests/test_api_flow.py` foram alterados.
2. O fluxo `POST /api/provider/updaterecords` deixou de gravar em `check_events` nos tres cenarios relevantes da etapa:
   - autenticacao invalida (`401`)
   - duplicidade
   - processamento bem-sucedido
3. A persistencia funcional permaneceu intacta porque `create_user_sync_event(...)` continua gravando em `UserSyncEvent` e `checkinghistory`, enquanto `provider.py` continua atualizando `users` quando o evento provider vence ou ajusta cadastro/projeto.
4. As notificacoes do admin foram ajustadas para remover a dependencia do log tecnico de provider em `check_events`:
   - `notify_admin_data_changed("event")` saiu do fluxo provider
   - `notify_admin_data_changed(action)` permaneceu para refletir alteracoes funcionais de estado
   - `notify_admin_data_changed("register")` permaneceu para refletir criacao de usuario ou mudanca de projeto
5. A revisao dos call sites confirmou que os logs tecnicos de atividades de usuario continuam nos fluxos que ainda devem usar `check_events`, principalmente RFID/leitor, mobile e web; a remocao desta etapa ficou restrita ao provider.
6. Validacao executada com sucesso no ambiente local:
   - `python -m pytest tests/test_api_flow.py -k "test_provider_endpoint_requires_valid_shared_key or test_provider_endpoint_never_writes_check_events_for_failed_duplicate_or_successful_requests or test_provider_endpoint_creates_user_and_history_with_normalized_name or test_provider_endpoint_never_enqueues_forms_even_for_multiple_events or test_provider_endpoint_updates_project_but_keeps_existing_name or test_provider_endpoint_keeps_newer_current_user_state_while_recording_older_history"`
   - resultado: `6 passed`

#### Diff mínimo sugerido para executar a Etapa 2

Objetivo do diff mínimo: remover o `updaterecords` de `check_events` sem antecipar a Etapa 3 e sem abrir mudanças no admin web.

Arquivos que entram no diff mínimo:

1. `sistema/app/routers/provider.py`
2. `tests/test_api_flow.py`

Arquivos que ficam explicitamente fora deste diff mínimo:

1. `sistema/app/routers/admin.py`
2. `sistema/app/schemas.py`
3. `sistema/app/static/admin/index.html`
4. `sistema/app/static/admin/app.js`
5. `sistema/app/static/admin/styles.css`
6. qualquer refatoração da aba `Forms`
7. qualquer implementação da aba `Relatórios`

Escopo exato em `sistema/app/routers/provider.py`:

1. Remover a dependência de `log_event(...)` de todo o fluxo `POST /api/provider/updaterecords`.
2. Remover o log de autenticação inválida em `require_provider_shared_key(...)`, deixando o endpoint responder `401` sem gravar em `check_events`.
3. Remover o log de duplicidade no branch `existing_event is not None`.
4. Remover o log de sucesso no branch principal após `create_user_sync_event(...)`.
5. Remover os imports que ficarem mortos após essa limpeza, principalmente `log_event` e `now_sgt` se não restar uso.
6. Manter intactos:
   - criação/atualização de `User`;
   - gravação em `UserSyncEvent`;
   - gravação em `checkinghistory` via `create_user_sync_event(...)`;
   - lógica de precedência para estado atual do usuário;
   - `db.commit()` dos branches que ainda precisarem persistir mudanças em `users` ou `user_sync_events`;
   - notificações `notify_admin_data_changed(action)` e `notify_admin_data_changed("register")` quando ainda fizerem sentido funcionalmente.
7. Remover apenas `notify_admin_data_changed("event")`, porque ele hoje está acoplado à escrita em `check_events` e essa escrita deixará de existir para provider.

Escopo exato em `tests/test_api_flow.py`:

1. Ajustar o teste `test_provider_endpoint_never_enqueues_forms_even_for_multiple_events()` para deixar de esperar `provider_log_rows` em `check_events`.
2. Trocar essa expectativa por verificação negativa, por exemplo confirmando que não existem linhas `CheckEvent` com `source="provider"` para o cenário exercitado.
3. Adicionar um teste focado para garantir que autenticação inválida em `POST /api/provider/updaterecords` também não grava nada em `check_events`.
4. Não mexer ainda no teste `test_admin_can_clear_forms_rows_without_archiving()`, porque ele prepara dados manualmente para a aba `Forms` e pertence à Etapa 3.

Critério de corte para manter o diff mínimo:

1. Se a mudança exigir tocar em `admin.py`, ela não pertence mais à Etapa 2 mínima.
2. Se a mudança exigir redefinir contrato JSON de resposta, ela não pertence mais à Etapa 2 mínima.
3. Se a mudança exigir mudar a renderização da aba `Forms`, ela deve ser adiada para a Etapa 3.

Primeira validação recomendada após o primeiro edit real da Etapa 2:

1. Executar apenas os testes de provider afetados em `tests/test_api_flow.py`.
2. Confirmar que sucesso, duplicidade e `401` do `updaterecords` não geram linhas em `check_events`.
3. Confirmar que `users`, `user_sync_events` e `checkinghistory` continuam sendo atualizados normalmente.

### Etapa 3. Tratamento da aba `Forms`

Objetivo: eliminar a dependência implícita entre a aba `Forms` e os logs do provider dentro de `check_events`.

Impacto visível confirmado antes da implementação da etapa:

1. Novos eventos de `POST /api/provider/updaterecords` deixaram de aparecer na aba `Forms`, porque `GET /api/admin/forms` ainda lê `CheckEvent` com `source="provider"`.
2. A mensagem de estado vazio atual passa a induzir erro operacional, porque a UI informa "Nenhum registro recebido do endpoint updaterecords." quando, na prática, o endpoint pode estar recebendo e persistindo em `user_sync_events`, mas a aba continua consultando a fonte antiga.
3. O botão `Limpar` permanece visível e funcional, embora sua ação ainda esteja acoplada à exclusão de linhas legadas em `check_events` e não ao novo histórico canônico.
4. Dois testes que representam impacto visível do admin já falham após a Etapa 2:
   - `test_admin_provider_forms_rows_include_timezone_metadata_for_non_singapore_project()`
   - `test_provider_same_day_events_do_not_override_web_state_and_are_reported_in_forms()`

Checklist refinada da Etapa 3:

- [x] Redefinir formalmente a aba `Forms` como visão operacional de eventos provider baseada em `user_sync_events` + `users` + metadados de `Project`.
- [x] Ajustar `GET /api/admin/forms` para deixar de ler `CheckEvent` e passar a reconstruir a lista a partir de `UserSyncEvent.source == "provider"`.
- [x] Garantir que a nova implementação preserve todas as colunas já expostas na tabela: `Recebimento`, `Chave`, `Nome`, `Projeto`, `Fuso horário`, `Atividade`, `Informe`, `Data` e `Hora`.
- [x] Garantir que a aba `Forms` continue mostrando eventos provider mesmo quando eles não vencem a precedência do estado atual em `users`.
- [x] Garantir que projetos fora de Singapura continuem exibindo `timezone_name` e `timezone_label` corretos na aba `Forms`.
- [x] Remover, desabilitar ou redefinir `DELETE /api/admin/forms` para uma ação não destrutiva; a rota agora responde `405` e a aba ficou somente leitura.
- [x] Remover ou desabilitar o botão `Limpar` em `index.html` e `app.js` se a rota de exclusão deixar de existir.
- [x] Ajustar a mensagem de estado vazio em `loadForms()` para refletir a nova fonte de dados e evitar a impressão falsa de que o endpoint não recebeu nada.
- [x] Atualizar os testes de backend afetados que dependiam de `check_events` como fonte da aba `Forms`.
- [x] Fazer os testes `test_admin_provider_forms_rows_include_timezone_metadata_for_non_singapore_project()` e `test_provider_same_day_events_do_not_override_web_state_and_are_reported_in_forms()` voltarem a passar com a nova fonte.

Resultado consolidado da Etapa 3:

1. `GET /api/admin/forms` passou a montar a aba `Forms` diretamente de `user_sync_events` com `source="provider"`, usando `users` para nome/chave e `Project` para fuso.
2. A composição da tabela preserva o contrato visual existente, inclusive `Recebimento`, `Atividade`, `Informe`, `Data`, `Hora`, `timezone_name` e `timezone_label`.
3. A aba continua exibindo eventos provider mesmo quando eles nao vencem a precedencia do estado atual em `users`.
4. `DELETE /api/admin/forms` deixou de apagar dados legados e agora responde `405`, tornando explicito que a aba e somente leitura.
5. O botao `Limpar` foi removido do frontend e a mensagem vazia da aba `Forms` foi atualizada para refletir o historico sincronizado.
6. Validacao executada com sucesso em `tests/test_api_flow.py` para os cenarios de timezone, eventos provider sem precedencia, provider vencedor do estado atual e rota de limpeza desabilitada.

### Etapa 4. Nova API da aba `Relatórios`

Objetivo: disponibilizar uma rota segura e consistente para localizar a pessoa e devolver seu histórico ordenado.

- [x] Criar schema de resposta da nova API de relatório em `schemas.py`.
- [x] Criar rota protegida de relatório em `admin.py` com `require_full_admin_session`.
- [x] Implementar validação backend para exigir exatamente um critério de busca.
- [x] Implementar resolução de usuário por `chave`.
- [x] Implementar resolução de usuário por `nome` com tratamento de ambiguidade.
- [x] Implementar consulta ordenada do histórico para o relatório.
- [x] Incluir metadados da pessoa no payload de resposta.

Resultado consolidado da Etapa 4:

1. Foi criada a rota `GET /api/admin/reports/events`, protegida por `require_full_admin_session`, para buscar o histórico consolidado de uma pessoa.
2. A nova API usa `user_sync_events` como fonte canônica do relatório e ordena por `event_time desc, id desc`.
3. O payload de resposta passou a incluir:
   - metadados da pessoa (`id`, `nome`, `chave`, `rfid`, `projeto`, `timezone_name`, `timezone_label`)
   - lista de eventos com `source`, `action`, `projeto`, `local`, `ontime`, `assiduidade`, `event_time`, `timezone_name`, `timezone_label` e `event_date`
4. A busca por `chave` normaliza para caixa alta e retorna `404` quando a pessoa nao existe.
5. A busca por `nome` usa comparacao case-insensitive com normalizacao de espacos, retorna `404` quando nao ha correspondencia e `409` quando ha ambiguidade, orientando o admin a usar a `chave`.
6. A API rejeita os dois cenarios invalidos de consulta:
   - nenhum criterio informado (`400`)
   - `chave` e `nome` enviados simultaneamente (`400`)
7. A rota ficou restrita a admin pleno; usuarios com acesso limitado recebem `403`.
8. Validacao executada com sucesso no ambiente local:
   - `python -m pytest tests/test_api_flow.py -k "test_admin_reports_events_returns_history_by_chave_in_desc_order or test_admin_reports_events_returns_history_by_unique_nome or test_admin_reports_events_rejects_ambiguous_nome or test_admin_reports_events_require_exactly_one_search_criterion or test_admin_reports_events_route_is_restricted_to_full_admin"`
   - resultado: `5 passed`

### Etapa 5. Estrutura e comportamento do frontend do admin

Objetivo: inserir a nova aba no fluxo existente, preservar permissões e aplicar as regras de busca sem ambiguidade.

- [x] Adicionar a aba `Relatórios` em `index.html` entre `Cadastro` e `Eventos`.
- [x] Criar o markup dos campos `Busca por Chave`, `Busca por Nome` e botão `Buscar`.
- [x] Criar a área de listagem dos resultados do relatório.
- [x] Atualizar `TAB_LABELS` e `DEFAULT_ADMIN_ALLOWED_TABS` em `app.js`.
- [x] Garantir que `LIMITED_ADMIN_ALLOWED_TABS` permaneça sem a aba `Relatórios`.
- [x] Implementar o estado JS da nova aba em `app.js`.
- [x] Implementar a regra de desabilitação mútua entre os inputs.
- [x] Implementar a chamada da API ao clicar em `Buscar`.
- [x] Implementar renderização agrupada por data, em ordem decrescente.
- [x] Implementar estados de vazio, erro e resultado encontrado.

Resultado consolidado da Etapa 5:

1. A aba `Relatórios` foi adicionada ao nav do admin entre `Cadastro` e `Eventos`, com a nova seção `tab-relatorios` no frontend.
2. O markup da aba passou a incluir:
   - input `Busca por Chave`
   - input `Busca por Nome`
   - botão `Buscar`
   - área de resultado com cabeçalho da pessoa encontrada e corpo para o histórico agrupado
3. O estado JS da aba foi implementado em `app.js`, incluindo:
   - normalização da `chave`
   - normalização do `nome` para a busca
   - estados de vazio, erro e resultado encontrado
   - renderização agrupada por `event_date` em ordem decrescente
4. A busca passou a chamar `GET /api/admin/reports/events` ao clicar em `Buscar` ou pressionar `Enter` nos campos.
5. A regra de desabilitação mútua foi implementada no frontend:
   - ao preencher `chave`, o campo `nome` é desabilitado
   - ao preencher `nome`, o campo `chave` é desabilitado
   - ao limpar o campo preenchido, o outro volta a ser habilitado
6. Para a aba realmente aparecer para admin pleno, foi necessário alinhar tambem o contrato de permissao no backend:
   - `FULL_ADMIN_TABS` passou a incluir `relatorios`
   - o schema `AdminIdentity.allowed_tabs` passou a aceitar `relatorios`
7. A lista limitada permaneceu sem `relatorios`, preservando a restricao da aba a admin pleno.
8. Validacao executada com sucesso no ambiente local:
   - `node --test tests/check_admin_reports_ui.test.js tests/check_admin_table_refresh_ui.test.js tests/check_admin_auth_ui.test.js`
   - resultado: `8 passed`
   - `python -m pytest tests/test_api_flow.py -k "test_admin_login_session_and_logout_flow or test_admin_perfil_zero_session_is_limited_to_checkin_and_checkout"`
   - resultado: `2 passed`

### Etapa 6. Ajustes visuais e consistência de navegação

Objetivo: manter a navegação do painel visualmente uniforme após a inclusão da nova aba.

- [x] Ajustar o CSS das abas para largura uniforme entre os botões visíveis.
- [x] Ajustar o CSS da nova aba para alinhamento dos labels, inputs e botão.

Resultado consolidado da Etapa 6:

1. A navegação principal do admin deixou de usar distribuicao livre por `flex` e passou a usar grid com colunas equivalentes, garantindo largura uniforme entre as abas visiveis.
2. Em telas menores, o nav passou a quebrar em duas colunas ainda com largura uniforme, preservando a legibilidade da nova aba `Relatorios` junto das abas existentes.
3. A aba `Relatórios` recebeu classes e regras CSS especificas para acabamento visual do formulario e da area de resultados.
4. O formulario da aba `Relatórios` passou a ter alinhamento consistente entre labels, inputs e botao `Buscar`, com quebra responsiva para uma coluna em telas menores.
5. A area de resultados do relatório passou a ter espaco e agrupamento visual coerentes com os blocos ja existentes do admin.
6. Validacao executada com sucesso no ambiente local:
   - `node --test tests/check_admin_reports_ui.test.js tests/check_admin_table_refresh_ui.test.js tests/check_admin_auth_ui.test.js`
   - resultado: `9 passed`

### Etapa 7. Testes e prevenção de regressão

Objetivo: validar o novo comportamento e capturar impactos colaterais, principalmente na área de eventos e no admin web.

- [x] Criar testes backend para `updaterecords` fora de `check_events`.
- [x] Criar testes backend para busca por `chave`.
- [x] Criar testes backend para busca por `nome`.
- [x] Criar testes backend para erro de ambiguidade por nome.
- [x] Criar testes backend para erro quando ambos os campos forem enviados.
- [x] Criar testes frontend para presença e posição da aba `Relatórios`.
- [x] Criar testes frontend para largura uniforme das abas.
- [x] Criar testes frontend para bloqueio mútuo entre os campos.
- [x] Revisar testes antigos que dependem de provider dentro de `check_events`.

Resultado consolidado da Etapa 7:

1. Os testes backend adicionados nas etapas anteriores continuam cobrindo a regra principal de regressao: `POST /api/provider/updaterecords` nao grava linhas em `check_events`, inclusive em falha de autenticacao, duplicidade e sucesso.
2. Os testes frontend da aba `Relatórios` cobrem a presenca/ordem da aba, a largura uniforme das tabs e o bloqueio mutuo entre `chave` e `nome`.
3. A revisao dos testes antigos confirmou que nao restou dependencia do fluxo atual de provider escrevendo em `check_events`.
4. O unico uso remanescente de evento `provider` em `CheckEvent` dentro da suite e um seed legado intencional no teste de preservacao de auditoria antiga da rota read-only de `Forms`, usado para garantir compatibilidade historica e nao para validar a persistencia atual do endpoint `updaterecords`.
5. Validacao executada com sucesso no ambiente local:
   - `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k "test_provider_endpoint_never_writes_check_events_for_failed_duplicate_or_successful_requests or test_provider_endpoint_never_enqueues_forms_even_for_multiple_events or test_admin_forms_clear_route_is_disabled_and_keeps_legacy_audit_rows"`
   - resultado: `3 passed`

### Etapa 8. Rollout operacional e validação final

Objetivo: aplicar a mudança de forma controlada e confirmar que o sistema permanece íntegro após a limpeza da tabela.

- [x] Preparar a instrução de limpeza total de `check_events` para rollout.
- [x] Executar validação manual no admin após a implementação.
- [x] Executar a limpeza controlada de `check_events` em ambiente apropriado.
- [x] Validar novamente o fluxo após a limpeza, confirmando que novos eventos entram corretamente.

Resultado consolidado da Etapa 8:

1. Foi criado o helper operacional `deploy/maintenance/clear_check_events_remote.ps1` para conduzir o rollout de limpeza com `dry-run` por padrao e `-Execute` apenas quando o ambiente publicado estiver apto.
2. O helper executa preflight publico antes de qualquer tentativa de limpeza:
   - valida `https://tscode.com.br/api/health`
   - valida `https://tscode.com.br/checking/admin`
   - verifica a presenca dos marcadores `data-tab="relatorios"` e `id="reportsSearchChave"` no admin publicado
3. O helper tambem executa preflight remoto so leitura no droplet:
   - valida `http://127.0.0.1:8000/api/health`
   - mostra `docker compose ps`
   - consulta a contagem atual de `check_events`
4. Validacao executada com sucesso no ambiente local para o modo seguro:
   - `pwsh -NoProfile -ExecutionPolicy Bypass -File .\deploy\maintenance\clear_check_events_remote.ps1`
   - resultado: preflight publico e remoto concluido, `check_events_before = 202`, `cleanup_mode=dry-run`
5. Validacao executada com sucesso para o guard rail destrutivo:
   - `pwsh -NoProfile -ExecutionPolicy Bypass -File .\deploy\maintenance\clear_check_events_remote.ps1 -Execute`
   - resultado: execucao bloqueada de forma intencional porque o admin publico ainda nao exibe a aba `Relatórios`
6. O codigo desta demanda foi publicado no droplet por sincronizacao controlada do working tree atual e rebuild do servico `app` com `docker compose up -d --build --force-recreate --remove-orphans app`.
7. A validacao do admin publicado foi concluida com sucesso no ambiente alvo:
   - `https://tscode.com.br/checking/admin` passou a expor `data-tab="relatorios"` e `id="reportsSearchChave"`
   - `https://tscode.com.br/api/admin/auth/session` autenticado como admin pleno passou a devolver `allowed_tabs` com `relatorios`
   - `GET /api/admin/reports/events` publicado respondeu `400` sem criterio, como esperado pelo contrato
8. A limpeza controlada de `check_events` foi executada com sucesso no ambiente alvo:
   - `pwsh -NoProfile -ExecutionPolicy Bypass -File .\deploy\maintenance\clear_check_events_remote.ps1 -Execute`
   - resultado: `check_events_before = 203`, `DELETE 203`, `check_events_after = 0`, `cleanup_mode=executed`
9. A validacao operacional pos-limpeza foi concluida com um fluxo sintetico controlado:
   - um usuario web temporario (`ZB11`) foi autocadastrado e autenticado no ambiente publicado
   - um `POST /api/web/check` sintetico voltou a popular `check_events`, com o contador de `request_path='/api/web/check'` subindo de `0` para `1`
   - o relatorio admin publicado retornou `1` evento para a `chave` sintetica apos o check web
   - um `POST /api/provider/updaterecords` para a mesma `chave` nao alterou `check_events`, mantendo o contador de `request_path='/api/provider/updaterecords'` em `0`
   - o relatorio admin passou a refletir o evento provider no historico canonico, subindo de `1` para `2` eventos para a pessoa validada
   - o usuario sintetico foi removido do cadastro ao final da validacao para evitar sujeira operacional permanente
   - snapshot final apos a limpeza e a validacao: `check_events_total = 4`, `check_events_web = 1`, `check_events_provider = 0`

## Critérios de Aceite

- `check_events` fica vazio após a ação operacional de limpeza.
- Após a limpeza, novos eventos válidos continuam sendo gravados normalmente.
- O endpoint `POST /api/provider/updaterecords` não cria novas linhas em `check_events`.
- Os fluxos de RFID, mobile e web continuam registrando eventos de atividade do usuário em `check_events`.
- A aba `Relatórios` aparece entre `Cadastro` e `Eventos`.
- Todas as abas visíveis do admin têm a mesma largura.
- Quando `chave` é preenchida, `nome` fica desabilitado.
- Quando `nome` é preenchido, `chave` fica desabilitado.
- A API rejeita envio simultâneo de `chave` e `nome`.
- O relatório devolve os eventos da pessoa ordenados do mais recente para o mais antigo.
- Busca por nome ambíguo não mistura pessoas diferentes.

## Observação Final de Planejamento

O maior ponto de atenção desta demanda não é a criação visual da aba `Relatórios`, e sim a mudança de papel de `check_events` em relação ao `updaterecords`.

Se essa dependência da aba `Forms` não for tratada explicitamente, a alteração parecerá correta no backend, mas produzirá regressão funcional silenciosa no admin.

Por isso, a execução deve seguir exatamente a ordem do planejamento acima: primeiro resolver a política de persistência e as dependências, depois expor a nova API, depois ajustar o frontend, depois testar e só então executar a limpeza total da tabela.