# Plano para Escopo de Projetos por Administrador no painel Admin

Data: 2026-04-25

## Objetivo

Adicionar, na aba `Cadastro`, planilha `Administradores`, um campo `Projetos` por administrador com checkboxes para definir quais projetos ele monitora.

Essas selecoes devem ser usadas para filtrar os dados exibidos em:

1. `Usuarios em Check-In`;
2. `Usuarios em Check-Out`;
3. `Usuarios Inativos`.

Exemplo esperado:

- se um administrador estiver com apenas `P80` marcado, ele deve enxergar somente linhas cujo projeto seja `P80` nessas tres tabelas.

## Leitura do estado atual

### 1. Onde os administradores sao mantidos hoje

- administradores ativos sao linhas da tabela `users`, controladas por `users.perfil`;
- a grade `Administradores` do frontend usa `GET /api/admin/administrators`;
- a edicao atual salva apenas o `perfil` via `POST /api/admin/administrators/{admin_id}/profile`.

Arquivos principais ja identificados:

- `sistema/app/models.py`
- `sistema/app/schemas.py`
- `sistema/app/routers/admin.py`
- `sistema/app/static/admin/index.html`
- `sistema/app/static/admin/app.js`

### 2. Como as tabelas de presenca sao montadas hoje

- `list_checkin()` chama `build_presence_rows(..., action="checkin")`;
- `list_checkout()` chama `build_presence_rows(..., action="checkout")`;
- `list_inactive()` chama `build_inactive_rows(...)`;
- hoje esses builders iteram todos os usuarios e nao filtram pelo administrador autenticado.

### 3. Ponto de atencao de UX no frontend

- `loadAdministrators()` roda antes de `loadProjects()` em `refreshAllTables()`;
- como o novo campo usara o catalogo de projetos para montar checkboxes, essa ordem precisa ser revista.

## Decisao de desenho recomendada

### 1. Reaproveitar o padrao de lista JSON ja usado em localizacoes

Implementar um novo campo textual na tabela `users`, por exemplo:

- `admin_monitored_projects_json: Text | null`

Motivo:

- o projeto ja usa listas de projetos serializadas em JSON em `locations.projects_json`;
- isso reduz escopo em comparacao com criar tabela relacional nova agora;
- o comportamento desejado e pequeno, administrativo e de baixa cardinalidade.

### 2. Semantica do valor salvo

Usar a seguinte regra:

- `null` ou vazio = administrador monitora todos os projetos;
- lista JSON preenchida = administrador monitora apenas os projetos listados.

Essa decisao evita dois problemas:

1. administradores antigos nao perdem visibilidade apos o deploy;
2. novos projetos criados depois continuam visiveis para administradores em modo `todos`, sem precisar regravar a selecao.

### 3. Escopo funcional da primeira entrega

Aplicar a filtragem apenas a:

1. `Check-In`;
2. `Check-Out`;
3. `Inativos`.

Fora do escopo inicial:

- `Forms`;
- `Relatorios`;
- `Eventos`;
- `Banco de Dados`;
- `Missing Checkout`.

Observacao:

- `Missing Checkout` pode ser alinhado depois por consistencia, mas nao precisa entrar nesta primeira rodada porque o pedido do usuario nomeou apenas tres tabelas.

### 4. Escopo de quem recebe configuracao

Nesta primeira entrega, o campo de checkboxes deve valer para administradores reais exibidos na grade `Administradores`.

Consequencia pratica:

- linhas `request` de solicitacao pendente nao precisam editar projetos monitorados ainda;
- no momento da aprovacao de um novo administrador, o valor inicial recomendado e `null`, ou seja, monitoramento total;
- depois disso, um admin pleno pode restringir os projetos pela propria grade.

## Plano tecnico detalhado

### Etapa 1. Modelo de dados e migration

Status: implementada em 2026-04-25.

Arquivos alvo:

- `sistema/app/models.py`
- `alembic/versions/...`

Passos:

1. Adicionar `admin_monitored_projects_json` em `User` como `Text`, nullable.
2. Criar migration Alembic para adicionar a coluna.
3. Nao preencher a coluna com listas fixas na migration.

Regra recomendada:

- deixar `NULL` para todos os administradores existentes, preservando comportamento de `ve tudo` por compatibilidade.

Motivo:

- se a migration gravar uma lista explicita de projetos atuais, administradores antigos deixarao de ver projetos novos no futuro sem perceber.

### Etapa 2. Helpers de serializacao e leitura do escopo monitorado

Status: implementada em 2026-04-25.

Criar helper novo, por exemplo:

- `sistema/app/services/admin_project_scope.py`

Responsabilidades recomendadas:

1. normalizar nomes de projeto usando `normalize_project_name(...)`;
2. serializar lista unica e ordenada para JSON;
3. desserializar JSON invalido com fallback seguro;
4. resolver o conjunto efetivo de projetos monitorados para um admin autenticado;
5. responder se um admin pode monitorar um projeto especifico.

API sugerida do helper:

- `normalize_admin_monitored_project_names(project_names)`
- `dump_admin_monitored_projects(project_names)`
- `extract_admin_monitored_projects(user)`
- `resolve_effective_admin_monitored_projects(user, all_project_names)`
- `admin_monitors_project(user, project_name, all_project_names)`

Semantica importante:

- se o campo estiver vazio, o helper deve devolver `None` ou um marcador equivalente a `todos`;
- a camada chamadora nao deve precisar reimplementar essa regra.

### Etapa 3. Schemas e contratos do admin

Status: implementada em 2026-04-25.

Arquivos alvo:

- `sistema/app/schemas.py`

Mudancas recomendadas:

1. estender `AdminManagementRow` com `monitored_projects: list[str]`;
2. criar um schema novo para update da configuracao do administrador, por exemplo:
   - `AdminProjectScopeUpdateRequest`
   - ou ampliar `AdminProfileUpdateRequest` com `monitored_projects: list[str] | None`.

Recomendacao:

- manter `perfil` e `monitored_projects` no mesmo payload do save da linha de administrador, para evitar dois botoes e dois fluxos concorrentes na mesma tabela.

Validacoes:

1. cada projeto deve existir no catalogo;
2. duplicatas devem ser descartadas;
3. lista vazia nao deve ser aceita quando o operador estiver explicitamente restringindo a visibilidade.

Regra pratica de persistencia:

- se todos os projetos estiverem marcados, persistir `null` em vez de uma lista completa;
- se apenas alguns estiverem marcados, persistir a lista explicita.

### Etapa 4. Backend de administradores

Arquivos alvo:

- `sistema/app/routers/admin.py`

Mudancas em `list_admin_rows()`:

1. carregar o catalogo atual de projetos;
2. devolver `monitored_projects` ja resolvido para cada admin;
3. para admins com `admin_monitored_projects_json` vazio, devolver a lista completa atual na resposta, para que o frontend mostre todos os checkboxes marcados.

Mudancas em `update_administrator_profile()`:

1. aceitar `perfil` + `monitored_projects` no mesmo request;
2. salvar `admin_monitored_projects_json` usando a regra `null = todos`;
3. ampliar auditoria com antes/depois de perfil e antes/depois do escopo monitorado;
4. ajustar a mensagem de retorno para algo mais amplo que `Perfil do administrador atualizado com sucesso.`

Mensagem recomendada:

- `Configuracoes do administrador atualizadas com sucesso.`

Mudancas em `approve_administrator_request()`:

1. ao criar ou promover um administrador, iniciar `admin_monitored_projects_json = null`;
2. isso garante visibilidade total por padrao apos aprovacao.

Mudancas em `remove_admin_project()`:

1. ao remover um projeto, revisar tambem o escopo monitorado dos administradores;
2. se o admin estiver em modo `todos` (`null`), nao fazer nada;
3. se o admin tiver lista explicita, remover o projeto apagado;
4. se a lista explicita ficar vazia, voltar para `null` ou substituir por todos os projetos remanescentes.

Recomendacao:

- voltar para `null`, porque isso representa melhor `sem restricao manual`.

### Etapa 5. Filtragem das tabelas Check-In / Check-Out / Inativos

Arquivos alvo:

- `sistema/app/routers/admin.py`
- possivelmente `sistema/app/services/admin_project_scope.py`

Mudancas de assinatura:

1. `list_checkin()` deve receber `current_admin: User = Depends(require_admin_session)`;
2. `list_checkout()` deve receber `current_admin: User = Depends(require_admin_session)`;
3. `list_inactive()` deve receber `current_admin: User = Depends(require_full_admin_session)`.

Mudancas nos builders:

1. `build_presence_rows()` deve aceitar `current_admin`;
2. `build_inactive_rows()` deve aceitar `current_admin`;
3. ambos devem pular usuarios cujo `user.projeto` nao esteja dentro do escopo monitorado do admin autenticado.

Ponto de implementacao recomendado:

- filtrar logo no inicio do loop, antes de calcular `latest_activity` e `timezone_context`, para evitar custo inutil.

Comportamento esperado:

- admin sem restricao (`null`) ve tudo;
- admin com lista explicita ve somente usuarios cujo `user.projeto` esteja nessa lista.

### Etapa 6. Frontend da grade Administradores

Arquivos alvo:

- `sistema/app/static/admin/index.html`
- `sistema/app/static/admin/app.js`
- `sistema/app/static/admin/styles.css`

Mudancas na tabela:

1. adicionar uma nova coluna `Projetos` na grade `Administradores`;
2. renderizar checkboxes por linha com base em `projectCatalog`;
3. manter todas marcadas quando o backend devolver a lista completa;
4. manter requests pendentes sem editor de projetos, com texto auxiliar simples.

Recomendacao visual:

- reutilizar o padrao de checkboxes ja existente na tela de localizacoes, evitando widget novo.

Mudancas no JS:

1. `makeAdministratorRow()` deve montar o bloco de checkboxes por projeto;
2. o clique em `Salvar Perfil` deve passar a enviar tambem `monitored_projects`;
3. o frontend deve impedir save com zero checkbox marcada;
4. `loadAdministrators()` passa a depender do catalogo de projetos.

### Etapa 7. Ordem de carregamento no bootstrap da aba Cadastro

Arquivo alvo:

- `sistema/app/static/admin/app.js`

Problema atual:

- `refreshAllTables()` chama `loadAdministrators()` antes de `loadProjects()`.

Mudanca recomendada:

1. em `cadastro`, carregar primeiro `loadProjects()`;
2. so depois carregar `loadAdministrators()`, `loadPending()`, `loadRegisteredUsers()` e `loadLocations()`.

Alternativa aceitavel:

- manter as chamadas separadas, mas rerenderizar administradores depois que `projectCatalog` estiver pronto.

Recomendacao principal:

- inverter a ordem, porque o catalogo de projetos ja e fonte de verdade da tela inteira.

### Etapa 8. Atualizacao do botao manual `Atualizar` de Administradores

Arquivo alvo:

- `sistema/app/static/admin/app.js`

Mudanca recomendada:

- o refresh da grade de administradores deve garantir que `projectCatalog` esteja atualizado antes de renderizar checkboxes.

Forma simples:

- trocar o handler para `Promise.all([loadProjects(), loadAdministrators()])` ou, preferencialmente, `await loadProjects(); await loadAdministrators();`.

## Regras de compatibilidade e edge cases

### 1. Admins existentes

- continuam vendo tudo apos o deploy, porque `admin_monitored_projects_json = null` significa `todos`.

### 2. Novo projeto criado depois

- admins em modo `todos` passam a ver o novo projeto automaticamente;
- admins com lista explicita continuam restritos ao subconjunto escolhido.

### 3. Projeto removido

- se o admin estiver em modo `todos`, nada muda;
- se o projeto removido estiver em lista explicita, ele deve ser retirado no backend.

### 4. Nenhum projeto marcado na UI

- bloquear save e exibir erro claro.

Mensagem sugerida:

- `Selecione ao menos um projeto para o administrador.`

### 5. Solicitacao pendente de administrador

- nao precisa editar projetos na propria linha de request;
- ao aprovar, o novo admin nasce em modo `todos`.

### 6. Usuarios com projeto vazio ou legacy

- se existirem linhas legadas com `user.projeto` inconsistente, o filtro deve falhar de forma segura e esconder o que nao possa ser mapeado com clareza.

## Estrategia de testes

### 1. Frontend estatico

Arquivos provaveis:

- `tests/check_admin_*.test.js`

Cobrir pelo menos:

1. nova coluna `Projetos` na tabela `Administradores`;
2. renderizacao de checkboxes por projeto na linha do admin;
3. save da linha enviando `perfil` + `monitored_projects`;
4. bloqueio de save com zero checkbox marcada;
5. carga de `Administradores` dependente de `Projetos`.

### 2. Backend/API

Arquivo principal:

- `tests/test_api_flow.py`

Cobrir pelo menos:

1. `GET /api/admin/administrators` devolve `monitored_projects`;
2. `POST /api/admin/administrators/{id}/profile` atualiza perfil e projetos monitorados;
3. admin com escopo `P80` ve apenas P80 em `/api/admin/checkin`;
4. admin com escopo `P80` ve apenas P80 em `/api/admin/checkout`;
5. admin com escopo `P80` ve apenas P80 em `/api/admin/inactive`;
6. admin sem escopo explicito continua vendo todos os projetos;
7. aprovacao de novo admin cria escopo `todos`;
8. remocao de projeto limpa ou recalcula listas explicitas sem deixar admin sem cobertura.

### 3. Validacao manual recomendada

1. marcar apenas `P80` para um admin e confirmar filtragem nas tres tabelas;
2. marcar `P80` + `P83` e confirmar visibilidade conjunta;
3. deixar todos os projetos marcados e confirmar que nada some;
4. criar projeto novo e validar comportamento para admin `todos` e admin restrito;
5. remover projeto e confirmar que o admin continua com configuracao coerente.

## Arquivos provaveis de impacto

### Backend

- `sistema/app/models.py`
- `sistema/app/schemas.py`
- `sistema/app/routers/admin.py`
- `sistema/app/services/admin_project_scope.py` (novo)
- `alembic/versions/<nova_migration>.py`

### Frontend

- `sistema/app/static/admin/index.html`
- `sistema/app/static/admin/app.js`
- `sistema/app/static/admin/styles.css`

### Testes

- `tests/check_admin_*.test.js`
- `tests/test_api_flow.py`

## Sequencia recomendada de execucao

1. criar coluna + migration;
2. criar helper de escopo monitorado;
3. estender schemas e `list_admin_rows()`;
4. atualizar rota de save do administrador;
5. filtrar `checkin`, `checkout` e `inactive` pelo admin autenticado;
6. adaptar UI da grade `Administradores`;
7. corrigir ordem de `loadProjects()` e `loadAdministrators()`;
8. cobrir com testes focados;
9. validar manualmente com administradores de escopo total e escopo parcial.

## Resultado esperado ao final

Ao concluir esse plano:

1. cada administrador ativo tera um escopo claro de projetos monitorados na propria grade `Administradores`;
2. `Check-In`, `Check-Out` e `Inativos` deixarao de mostrar dados fora desse escopo;
3. administradores antigos nao sofrerao regressao apos o deploy;
4. o sistema continuara coerente quando projetos forem criados ou removidos.

## To-do List Completa de Execucao

### 1. Preparacao e alinhamento de escopo

- [ ] Confirmar que o filtro por projetos monitorados sera aplicado apenas a `Usuarios em Check-In`, `Usuarios em Check-Out` e `Usuarios Inativos` nesta primeira entrega.
- [ ] Confirmar que linhas de `solicitacao pendente` na grade `Administradores` nao terao editor de projetos nesta rodada.
- [ ] Confirmar que o comportamento padrao para administradores existentes e novos sera `ve todos os projetos` quando o campo estiver vazio.
- [ ] Confirmar a semantica final de persistencia: `NULL` ou vazio representa `todos os projetos`.
- [ ] Confirmar a regra de UX para `nenhum projeto marcado`: bloquear o save e exibir erro.
- [ ] Confirmar se a coluna nova na grade `Administradores` se chamara `Projetos`.
- [ ] Confirmar se o botao atual `Salvar Perfil` sera reaproveitado para salvar perfil e projetos monitorados em conjunto.

### 2. Modelo de dados e migration

- [x] Adicionar `admin_monitored_projects_json` ao model `User` em `sistema/app/models.py`.
- [x] Garantir que o tipo escolhido seja `Text` nullable.
- [x] Criar nova migration Alembic para adicionar a coluna em `users`.
- [x] Garantir que a migration nao preencha a coluna com listas explicitas de projetos atuais.
- [x] Garantir que administradores existentes permaneçam com `NULL` para preservar o modo `todos`.
- [x] Revisar o downgrade da migration para remover a coluna com seguranca.

### 3. Helper de escopo monitorado

- [x] Criar `sistema/app/services/admin_project_scope.py`.
- [x] Implementar normalizacao de nomes de projeto reaproveitando `normalize_project_name(...)`.
- [x] Implementar serializacao JSON deterministica da lista de projetos monitorados.
- [x] Implementar leitura segura do JSON com fallback para `todos` quando vazio ou invalido.
- [x] Implementar funcao para resolver o escopo efetivo de um admin autenticado.
- [x] Implementar funcao para responder se um admin monitora um projeto especifico.
- [x] Cobrir comportamento de duplicatas e ordenacao consistente na lista normalizada.

### 4. Contratos e schemas do admin

- [x] Estender `AdminManagementRow` em `sistema/app/schemas.py` com `monitored_projects: list[str]`.
- [x] Estender `AdminProfileUpdateRequest` ou criar schema dedicado para aceitar `perfil` + `monitored_projects`.
- [x] Validar que todos os projetos enviados existem no catalogo atual.
- [x] Validar que duplicatas sejam descartadas.
- [x] Validar que lista vazia explicita nao seja aceita.
- [x] Garantir compatibilidade com requests antigos durante a implementacao, se necessario.

### 5. Backend da grade Administradores

- [x] Atualizar `list_admin_rows()` em `sistema/app/routers/admin.py` para carregar o catalogo de projetos.
- [x] Devolver `monitored_projects` resolvido para cada administrador ativo.
- [x] Para admins em modo `todos`, devolver a lista completa atual na resposta, para manter todos os checkboxes marcados no frontend.
- [x] Manter requests pendentes sem lista de projetos editavel.
- [x] Atualizar `update_administrator_profile()` para aceitar `perfil` + `monitored_projects`.
- [x] Persistir `admin_monitored_projects_json = NULL` quando todos os projetos estiverem selecionados.
- [x] Persistir lista explicita apenas quando houver restricao real.
- [x] Ampliar a auditoria com antes/depois do perfil.
- [x] Ampliar a auditoria com antes/depois do escopo de projetos monitorados.
- [x] Ajustar a mensagem de sucesso para refletir configuracao completa do administrador.

### 6. Fluxo de aprovacao e ciclo de vida de administradores

- [x] Ajustar `approve_administrator_request()` para criar ou promover administradores com escopo `todos` por padrao.
- [x] Garantir que o campo novo nao interfira na regra atual de senha pendente.
- [x] Garantir que revogacao de admin nao dependa do novo campo.
- [x] Revisar se bootstrap admin tambem deve nascer implicitamente em modo `todos` sem qualquer valor gravado.

### 7. Filtragem das tabelas de presenca pelo admin autenticado

- [x] Atualizar `list_checkin()` para receber `current_admin: User = Depends(require_admin_session)`.
- [x] Atualizar `list_checkout()` para receber `current_admin: User = Depends(require_admin_session)`.
- [x] Atualizar `list_inactive()` para receber `current_admin: User = Depends(require_full_admin_session)`.
- [x] Atualizar `build_presence_rows()` para aceitar `current_admin`.
- [x] Atualizar `build_inactive_rows()` para aceitar `current_admin`.
- [x] Filtrar usuarios logo no inicio do loop pelo projeto monitorado do admin autenticado.
- [x] Garantir que admins em modo `todos` continuem vendo tudo.
- [x] Garantir que admins com lista explicita vejam apenas os projetos configurados.
- [x] Garantir que o filtro nao quebre calculo de timezone, assiduidade e ordenacao existentes.

### 8. Impacto de remocao e criacao de projetos

- [x] Atualizar `remove_admin_project()` para revisar escopos explicitos de administradores quando um projeto for removido.
- [x] Remover o projeto apagado das listas explicitas que o referenciem.
- [x] Se uma lista explicita ficar vazia apos a remocao, voltar o admin para modo `todos` (`NULL`).
- [x] Garantir que admins em modo `todos` nao precisem de qualquer ajuste ao remover um projeto.
- [x] Garantir que novos projetos continuem visiveis automaticamente para admins em modo `todos`.

### 9. Frontend da aba Cadastro, planilha Administradores

- [x] Adicionar a nova coluna `Projetos` em `sistema/app/static/admin/index.html`.
- [x] Ajustar `makeAdministratorRow()` em `sistema/app/static/admin/app.js` para renderizar checkboxes por projeto.
- [x] Reaproveitar o catalogo carregado por `loadProjects()` como fonte de verdade das checkboxes.
- [x] Marcar todos os checkboxes quando o backend devolver lista completa.
- [x] Exibir estado simples e nao editavel para linhas `request`.
- [x] Atualizar `saveAdministratorProfile()` para enviar `perfil` + `monitored_projects`.
- [x] Bloquear save com zero checkbox marcada.
- [x] Exibir mensagem de erro clara quando nenhuma checkbox estiver marcada.
- [x] Garantir que o layout continue utilizavel em desktop e mobile.
- [x] Ajustar estilos em `sistema/app/static/admin/styles.css` para comportar os checkboxes sem quebrar a tabela.

### 10. Ordem de carregamento e refresh da aba Cadastro

- [x] Corrigir `refreshAllTables()` para carregar `loadProjects()` antes de `loadAdministrators()`.
- [x] Garantir que `loadAdministrators()` rode com `projectCatalog` pronto.
- [x] Ajustar o botao `Atualizar` da grade `Administradores` para atualizar tambem o catalogo de projetos antes de renderizar a tabela.
- [x] Revisar se `refreshAutomaticTables()` precisa de algum ajuste adicional para nao rerenderizar administradores com catalogo obsoleto.

### 11. Testes automatizados de frontend

- [x] Criar ou atualizar teste estatico cobrindo a nova coluna `Projetos` na grade `Administradores`.
- [x] Cobrir a renderizacao dos checkboxes por projeto.
- [x] Cobrir o envio de `perfil` + `monitored_projects` no save da linha.
- [x] Cobrir o bloqueio de save com zero checkbox marcada.
- [x] Cobrir a dependencia de `loadProjects()` antes de `loadAdministrators()`.
- [x] Cobrir o comportamento visual das linhas `request` sem editor de projetos.

### 12. Testes automatizados de backend

- [x] Atualizar `tests/test_api_flow.py` para validar que `GET /api/admin/administrators` devolve `monitored_projects`.
- [x] Cobrir update de perfil + projetos monitorados em `POST /api/admin/administrators/{id}/profile`.
- [x] Cobrir admin com escopo apenas `P80` enxergando somente `P80` em `/api/admin/checkin`.
- [x] Cobrir admin com escopo apenas `P80` enxergando somente `P80` em `/api/admin/checkout`.
- [x] Cobrir admin com escopo apenas `P80` enxergando somente `P80` em `/api/admin/inactive`.
- [x] Cobrir admin sem escopo explicito continuando a enxergar todos os projetos.
- [x] Cobrir aprovacao de novo administrador iniciando em modo `todos`.
- [x] Cobrir remocao de projeto limpando listas explicitas sem deixar o admin em estado invalido.
- [x] Cobrir eventual fallback seguro para `admin_monitored_projects_json` invalido ou legado.

### 13. Validacao manual segura

Status: homologada em 2026-04-25 com `scripts/homologate_temp_005_phase13.py`, usando preview SQLite local + servidor uvicorn local + Playwright headless.

Evidencia registrada em `docs/temp_005_phase13_report.json`.

- [x] Criar ou identificar ao menos dois projetos com usuarios ativos distintos para homologacao manual.
- [x] Configurar um admin de teste com apenas `P80` marcado.
- [x] Confirmar que esse admin enxerga apenas `P80` em `Usuarios em Check-In`.
- [x] Confirmar que esse admin enxerga apenas `P80` em `Usuarios em Check-Out`.
- [x] Confirmar que esse admin enxerga apenas `P80` em `Usuarios Inativos`.
- [x] Marcar `P80` + `P83` e confirmar que a visibilidade conjunta funciona nas tres tabelas.
- [x] Deixar todos os projetos marcados e confirmar que nada some indevidamente.
- [x] Criar um projeto novo e validar comportamento para admin em modo `todos`.
- [x] Remover um projeto e validar que escopos explicitos continuam coerentes.
- [x] Confirmar que requests pendentes continuam legiveis e sem controles quebrados.

### 14. Rollout e fechamento

Status: concluida em 2026-04-25.

Fechamento registrado:

- A revisao final do diff confirmou que o escopo de projetos monitorados permaneceu restrito a `Administradores`, `Usuarios em Check-In`, `Usuarios em Check-Out` e `Usuarios Inativos`; `Forms` recebeu apenas a alteracao deliberada do botao `Limpar`, sem estender o filtro de projetos para `Forms`, `Relatorios`, `Eventos` ou `Banco de Dados`.
- A migration `alembic/versions/0040_add_admin_monitored_projects.py` e apenas aditiva, cria `admin_monitored_projects_json` como coluna nullable e nao faz backfill; por isso pode ser aplicada sem carga manual de dados.
- A compatibilidade de rollout fica preservada porque `NULL` no campo novo significa `todos os projetos`; administradores existentes continuam vendo tudo imediatamente apos o deploy, e administradores em modo `todos` seguem herdando projetos criados no futuro.
- A auditoria do save em `/api/admin/administrators/{admin_id}/profile` registra `old_profile`, `new_profile`, `old_monitored_projects` e `new_monitored_projects`, alem do `updated_by`, cobrindo perfil e escopo monitorado no mesmo evento.
- Limitacao assumida para segunda fase: o filtro de projetos monitorados continua fora de `Missing Checkout`, `Forms` e `Relatorios`; nesta fase, a aba `Forms` ganhou apenas o botao `Limpar`, que remove exclusivamente os registros canonicos de `UserSyncEvent` com `source="provider"` que alimentam essa grade.
- Validacao final da fase concluida com `node --test tests/check_admin_presence_forms_layout.test.js` e `python -m pytest tests/test_api_flow.py -k "test_admin_forms_clear_route_removes_only_provider_sync_rows"`.

- [x] Revisar o diff final para garantir que o novo escopo nao atingiu `Forms`, `Relatorios`, `Eventos` ou `Banco de Dados` sem querer.
- [x] Confirmar que a migration pode ser aplicada sem necessidade de backfill manual.
- [x] Confirmar que admins existentes continuarao vendo tudo imediatamente apos o deploy.
- [x] Confirmar que logs/auditoria registram mudancas de perfil e de projetos monitorados.
- [x] Documentar no resumo final que `NULL` no campo novo significa `todos os projetos`.
- [x] Registrar, no fechamento da execucao, quaisquer limitacoes assumidas para uma segunda fase, como eventual extensao do filtro para `Missing Checkout`, `Forms` ou `Relatorios`.
- [x] Incluir um botao `Limpar` na aba `Forms`, ao lado de `Atualizar`, para remover todos os registros da tabela `Forms`, e nada mais.