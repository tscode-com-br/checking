# Plano detalhado para restringir a visualizacao do horario das atividades no Admin

## 1. Objetivo

Implementar uma restricao de visualizacao de horario no Website do Administrador para que apenas usuarios com perfil `9` possam ver a informacao de horario exata das atividades de check-in e check-out.

Os demais perfis que consigam acessar alguma parte do Admin devem continuar usando o painel normalmente, mas sem acesso ao horario preciso das atividades.

## 2. Regra funcional consolidada

Regra central:

- Apenas perfil `9` pode visualizar horario exato de atividade.
- Perfis `0`, `1`, `2` e quaisquer outros diferentes de `9` nao podem visualizar horario exato.
- A regra passa a ser global por perfil: qualquer usuario cujo perfil nao seja `9` nao deve visualizar horario exato nas superficies que exponham esse dado.
- Nesta entrega, as superficies confirmadas, mapeadas e priorizadas continuam sendo as do Website do Administrador.
- O acesso as abas, rotas e demais funcionalidades do Admin deve permanecer como esta hoje; a mudanca e apenas de exposicao de dado sensivel.

Aplicacao da regra por area:

1. `Check-In` e `Check-Out`
   - Perfil `9`: continua vendo data + horario na coluna inicial.
   - Demais perfis: veem apenas a data, sem horario.

2. `Forms`
   - Perfil `9`: continua vendo a coluna `Hora`.
   - Demais perfis com acesso a aba: nao veem a coluna `Hora`.

3. `Relatorios`
   - Perfil `9`: continua vendo a coluna `Horario` nas tabelas de resultado.
   - Demais perfis com acesso a aba: nao veem a coluna `Horario`.

4. `Exportar` e `Exportar Tudo` em `Relatorios`
   - Perfil `9`: continua recebendo a planilha com a coluna `Horario`.
   - Demais perfis com acesso a aba: recebem a planilha sem essa coluna.

5. `Eventos`
   - Perfil `9`: continua vendo data + horario na coluna `Horario`.
   - Demais perfis com acesso a aba: veem apenas a data, sem horario.

Observacao importante:

- O requisito de `Relatorios` foi listado duas vezes no pedido. Considerar como uma unica frente funcional, cobrindo a visualizacao na tela e os dois tipos de exportacao.

## 3. Estado atual do sistema e pontos impactados

### 3.1. Frontend Admin

O Admin e uma SPA estatica em:

- `sistema/app/static/admin/index.html`
- `sistema/app/static/admin/app.js`
- `sistema/app/static/admin/styles.css`

Pontos ja identificados:

- `index.html` define cabecalhos fixos para as tabelas `Check-In`, `Check-Out`, `Forms` e `Eventos`.
- `app.js` busca os dados nas rotas `/api/admin/*` e monta as linhas das tabelas.
- `app.js` recebe a sessao em `/api/admin/auth/session` e ja conhece `perfil`, `access_scope` e `allowed_tabs`.
- `Check-In` e `Check-Out` agora consomem campos seguros de exibicao (`activity_date_label`, `activity_time_label`, `activity_day_key`), ajustam o label da coluna principal conforme `admin.can_view_activity_time`, renderizam a primeira celula em duas linhas apenas quando o horario sensivel esta disponivel e mantem filtros/sort com fallback seguro por `activity_day_key` quando `time = null`.
- `Forms` agora consome campos seguros de exibicao para `Recebimento` (`recebimento_date_label`, `recebimento_time_label`), oculta estruturalmente a coluna `Hora` para perfis sem acesso ao horario sensivel, usa variante `forms-table--without-time` e ajusta o `colspan` do empty state para 8 ou 9 colunas conforme a permissao.
- `Relatorios` agora monta a tabela de resultados com coluna `Horario` apenas para perfil `9`, usa variante `reports-results-table--without-time` para os demais e preserva agrupamento por `event_date`, `reportsHasLoadedResult` e `reportsExportQueryString` sem alteracao funcional.
- `Eventos` agora ancora o cabecalho sensivel da primeira coluna, troca o label visual entre `Horario` e `Data` conforme `admin.can_view_activity_time` e usa `event_date_label`/`event_time_label` sem depender do horario bruto para perfis nao `9`, preservando detalhes, totais e `updateDashboardSummary()`.

### 3.2. Backend Admin

Os principais pontos no backend estao em:

- `sistema/app/routers/admin.py`
- `sistema/app/services/admin_auth.py`
- `sistema/app/schemas.py`

Pontos ja confirmados:

- `/api/admin/auth/session` devolve `admin.perfil`.
- `/api/admin/auth/session` agora tambem devolve `admin.can_view_activity_time`.
- `build_admin_identity()` monta a identidade da sessao.
- `require_admin_session` protege `checkin` e `checkout`.
- `require_full_admin_session` protege `forms`, `relatorios` e `eventos`.
- `build_presence_rows()` agora devolve `UserRow.activity_date_label`, `UserRow.activity_time_label` e `UserRow.activity_day_key` para `Check-In` e `Check-Out`, mantendo `UserRow.time` apenas para perfis autorizados a ver horario sensivel.
- `build_provider_forms_rows()` agora devolve `ProviderFormRow.recebimento_date_label`, `ProviderFormRow.recebimento_time_label`, `ProviderFormRow.data` e `ProviderFormRow.hora`, mantendo `recebimento` bruto e `hora` apenas para perfis autorizados a ver horario sensivel.
- `build_report_events_response()` devolve `ReportEventRow.event_date` e `ReportEventRow.event_time_label`.
- `build_report_events_export()` e `build_all_report_events_export()` agora montam o XLSX com estrutura condicional: perfil `9` mantem a coluna `Horario`; demais perfis recebem a planilha sem essa coluna.
- `build_event_row_payload()` agora devolve `EventRow.event_date_label` e `EventRow.event_time_label`, mantendo `EventRow.event_time` bruto apenas para perfis autorizados a ver horario sensivel na aba `Eventos`.

### 3.3. Testes existentes afetados

Ja existem testes que assumem a presenca fixa de colunas de horario e hora, principalmente em:

- `tests/check_admin_presence_forms_layout.test.js`
- `tests/check_admin_project_timezone_ui.test.js`
- `tests/check_admin_reports_ui.test.js`
- `tests/test_api_flow.py`

Esses testes ja foram atualizados para refletir comportamento condicional por perfil, preservando cobertura para perfil `9`, para pelo menos um perfil nao `9` em cada superficie sensivel e para os fluxos nao relacionados que nao deveriam sofrer relaxamento.

## 4. Principio tecnico recomendado

Para evitar vazamento de horario por inspecao de rede, DevTools ou consumo direto da API, a implementacao nao deve depender apenas de esconder coluna no frontend.

A regra precisa ser aplicada em duas camadas:

1. Backend
   - Sanitiza a resposta e a exportacao conforme o perfil da sessao.

2. Frontend
   - Ajusta colunas, labels, colgroup, `colspan`, filtros e renderizacao conforme a permissao.

Principio de seguranca:

- Se um usuario nao pode ver o horario, a API tambem nao deve devolver o horario exato para aquele usuario.

## 5. Decisao de autorizacao que precisa ficar centralizada

Hoje o projeto usa semantica de digitos de perfil para acessos amplos (`1`, `2`, `9`).

Para este requisito especifico, a recomendacao e criar uma capacidade explicita, centralizada e unica, por exemplo:

- `can_admin_view_activity_time(user)`

Implementacao recomendada dessa capacidade:

- Basear na regra funcional definida pelo produto para horario sensivel.
- Como o pedido foi explicito sobre `apenas perfil 9`, a recomendacao e tratar `9` como a referencia oficial para esta visualizacao sensivel.

Ponto de atencao obrigatorio antes de subir a implementacao:

- Auditar se existem registros legados com perfis como `19`, `29`, `99` ou `999` que hoje sejam tratados como acesso total.
- Se existirem, decidir formalmente se eles tambem devem ver horario por representarem acesso total legado, ou se sera necessario normalizar esses perfis antes da entrega.

Status atual de implementacao:

- A base do codigo agora possui um helper dedicado para esta regra sensivel: `profile_can_view_activity_time()` em `sistema/app/services/admin_auth.py`.
- Neste momento, o helper considera autorizado apenas o perfil normalizado exatamente igual a `9`.
- Perfis legados como `999` permanecem com acesso total amplo nas regras antigas, mas nao foram incluidos automaticamente na nova regra sensivel.
- Essa separacao foi introduzida de forma isolada para permitir evolucao segura da implementacao sem alterar o modelo atual de acesso geral do Admin.

Decisoes formais consolidadas na Fase 0:

- Apenas perfil normalizado exatamente igual a `9` pode visualizar todas as informacoes de horario das atividades.
- Perfis legados como `19`, `29`, `99` e `999` nao herdam a visualizacao de horario.
- A regra deixa de ser uma excecao apenas do shell do Admin e passa a ser uma politica global por perfil para qualquer superficie que exponha esse dado sensivel.
- Para esta entrega, as superficies confirmadas e mapeadas permanecem: `Check-In`, `Check-Out`, `Forms`, `Relatorios`, `Exportar`, `Exportar Tudo` e `Eventos` no Admin.

### 5.1. Mapeamento minucioso atual de perfil e sessao

Base central de semantica de perfil em `sistema/app/services/admin_auth.py`:

- `normalize_user_profile()` normaliza o valor bruto de `perfil` para inteiro nao negativo.
- `get_user_profile_digits()` e `user_profile_has_access()` sustentam a regra antiga de acesso amplo por digito (`1`, `2`, `9`).
- `user_has_admin_access()` decide se um usuario tem acesso administrativo amplo.
- `user_can_access_admin_panel()` decide se o usuario pode entrar no shell do Admin; hoje permite perfis com acesso admin amplo e tambem `perfil = 0` em modo limitado.
- `get_admin_access_scope()` deriva `limited` ou `full`.
- `get_admin_allowed_tabs()` deriva as abas autorizadas a partir do escopo.
- `profile_can_view_activity_time()` e `user_can_view_activity_time()` formam a nova base isolada da regra sensivel de horario e nao reutilizam a semantica antiga por digito.
- `get_authenticated_admin_from_session()`, `require_admin_session()`, `require_full_admin_session()` e `require_admin_stream_session()` recompõem a permissao a partir de `request.session["admin_user_id"]`.

Contrato de sessao do Admin em `sistema/app/routers/admin.py`:

- `build_admin_identity()` serializa `perfil`, `can_view_activity_time`, `access_scope` e `allowed_tabs` para o frontend.
- `/api/admin/auth/login` usa `user_can_access_admin_panel()` para aceitar ou bloquear a entrada no painel e grava `request.session["admin_user_id"]`.
- `/api/admin/auth/session` reconstroi a sessao via `get_authenticated_admin_from_session()` e `build_admin_identity()`.

Pontos de backend que derivam permissao a partir de perfil no fluxo administrativo:

- `get_admin_request_access_status()` usa `user_has_admin_access()` para decidir se uma chave ja pertence a um administrador.
- `request_admin_access_self_service()` impede nova solicitacao quando a chave ja estiver ligada a um admin.
- `list_admin_rows()` filtra `User.perfil != 0`, reaplica `user_has_admin_access()` e monta `status_label` com `describe_user_profile()`.
- `approve_administrator_request()` usa `normalize_administrator_profile()` e `merge_user_profile_values()` para compor o `perfil` final aprovado.
- `update_administrator_profile()` le `administrator.perfil`, calcula `previous_profile` e grava `next_profile`.
- `revoke_administrator()` remove o digito admin com `remove_profile_access()` e protege contra remocao do ultimo admin ativo.
- `remove_admin_project()` reaproveita `user_has_admin_access()` ao recalcular escopos de projetos monitorados de administradores.

Pontos de backend que expõem ou mutam `perfil` de usuarios no cadastro geral:

- `/api/admin/users` lista `perfil` bruto para toda a grade de usuarios via `AdminUserListRow`.
- `upsert_user()` le `payload.perfil`, normaliza com `normalize_user_profile()` e usa `user_has_admin_access()` mais `user_profile_has_access()` para evitar remover o ultimo admin ativo por edicao indireta.
- Esses fluxos sao hotspots importantes porque continuam editando perfis numericos gerais e nao devem receber a nova regra sensivel de horario por duplicacao local.

Pontos de frontend que derivam permissao da sessao do Admin em `sistema/app/static/admin/app.js`:

- `DEFAULT_ADMIN_ALLOWED_TABS` e `LIMITED_ADMIN_ALLOWED_TABS` codificam as abas permitidas por escopo.
- `normalizeAllowedAdminTabs()` e `setAdminAccessState()` transformam `access_scope`, `allowed_tabs` e `can_view_activity_time` da sessao em visibilidade real de abas e variantes seguras de renderizacao.
- O bootstrap em `fetchJson("/api/admin/auth/session")` e `showAdminShell(session.admin)` e o ponto unico de entrada do contrato de sessao no frontend.
- O frontend ja consome `can_view_activity_time` via `adminCanViewActivityTime`; `showAdminShell()` alimenta esse estado, `showAuthShell()` o reseta, e `canCurrentAdminViewActivityTime()` centraliza a consulta para os pontos que ja adotaram variantes seguras.

Pontos de frontend que leem ou editam perfis numericos no Admin:

- `makeRegisteredUserRow()` renderiza o campo `user-perfil` na tabela de usuarios.
- `makeAdministratorRow()` renderiza o campo `admin-profile-input` na tabela de administradores.
- `readAdministratorProfileValue()` valida o numero digitado para administradores.
- `saveRegisteredUser()`, `approveAdministrator()` e `saveAdministratorProfile()` enviam `perfil` explicitamente para o backend.
- Esses pontos devem continuar tratando `perfil` como dado administrativo bruto, sem recriar a regra sensivel de horario na camada de UI.

Pontos de frontend estatico adjacentes ao shell do Admin:

- `sistema/app/static/admin/index.html` ainda comunica a regra antiga de acesso amplo ao painel na copy da tela de login (`perfil 0` limitado; `1` ou `9` com acesso completo).
- Essa copy nao deve ser usada como fonte da nova regra sensivel; quando a Fase 2 expor a capacidade na sessao, a comunicacao visual precisara separar acesso ao painel de visibilidade de horario.

Pontos adjacentes fora do Admin mapeados cautelosamente:

- `sistema/app/routers/transport.py` possui sessao propria em `/api/transport/auth/session` e expõe `perfil` em `TransportIdentity`.
- `sistema/app/static/transport/app.js` consome essa sessao separada.
- Nenhum desses pontos deve ser alterado agora por inferencia; so entram no escopo se tambem passarem a expor o mesmo dado sensivel de horario abrangido por esta regra global.

Hotspots de teste ja identificados:

- `tests/test_api_flow.py` possui construcao recorrente de usuarios com perfis `0`, `1`, `2`, `9`, `12`, `999` e testes que dependem da semantica antiga de acesso amplo.
- Os testes novos `test_profile_can_view_activity_time_requires_exact_profile_nine()` e `test_user_can_view_activity_time_requires_exact_profile_nine()` documentam a nova regra sensivel estrita.
- O teste `test_admin_perfil_zero_session_is_limited_to_checkin_and_checkout()` continua sendo referencia importante para garantir que a nova regra nao altere o escopo atual do painel.

A validacao funcional inicial desta fase foi concluida. Qualquer excecao futura deve ser introduzida explicitamente sobre a nova capacidade sensivel, sem reaproveitar implicitamente a semantica antiga de acesso por digitos.

## 6. Plano detalhado de implementacao

### Etapa 1. Criar a capacidade de visualizacao sensivel no backend

Arquivos principais:

- `sistema/app/services/admin_auth.py`
- `sistema/app/schemas.py`
- `sistema/app/routers/admin.py`

Passos:

1. Criar um helper unico para decidir se a sessao atual pode ver horario sensivel.
2. Evitar espalhar comparacoes diretas de perfil pelo codigo.
3. Expor essa capacidade na sessao do Admin, preferencialmente adicionando um campo booleano em `AdminIdentity`, por exemplo:
   - `can_view_activity_time: bool`
4. Preencher esse campo em `build_admin_identity()`.
5. Manter `access_scope` e `allowed_tabs` exatamente como ja funcionam hoje.

Motivo:

- O perfil continua definindo acesso ao painel, mas a exposicao do horario passa a usar uma capacidade especifica e reutilizavel.

### Etapa 2. Ajustar o contrato de dados para `Check-In` e `Check-Out`

Arquivos principais:

- `sistema/app/schemas.py`
- `sistema/app/routers/admin.py`
- `sistema/app/static/admin/app.js`
- `sistema/app/static/admin/index.html`

Situacao atual:

- A rota devolve `UserRow.time` como `datetime` bruto.
- O frontend usa `formatDateTime(row.time, row.timezone_name)` e renderiza data + horario.
- Os filtros e a ordenacao da coluna inicial tambem dependem desse valor.

Risco atual:

- Mesmo escondendo o horario na tela, o timestamp bruto continuaria disponivel na API para perfis nao autorizados.

Plano recomendado:

1. Refatorar o contrato da linha de presenca para usar campos de exibicao seguros.
2. Evitar depender do `datetime` bruto no frontend para mostrar a primeira coluna.
3. Introduzir campos especificos de exibicao, por exemplo:
   - `activity_date_label`
   - `activity_time_label` ou `null`
4. Para perfil `9`:
   - preencher data e horario.
5. Para demais perfis:
   - preencher somente a data.
   - deixar o horario nulo ou ausente no contrato de exibicao.
6. Manter a ordenacao do backend pelo timestamp real antes da sanitizacao.
7. No frontend, fazer a coluna inicial usar apenas os campos seguros.
8. Atualizar a primeira coluna para exibir:
   - perfil `9`: duas linhas, data e horario.
   - demais perfis: apenas a linha de data.
9. Tornar dinamicos os labels ligados a essa coluna:
   - cabecalho `Horario` para perfil `9`
   - cabecalho `Data` para demais perfis
   - filtro `Filtrar Horario` para perfil `9`
   - filtro `Filtrar Data` para demais perfis
10. Atualizar `getPresenceRowDisplayValue()` e `getPresenceFilterOptions()` para usar a versao segura do valor exibido.
11. Atualizar a logica de ordenacao do frontend para nao depender de horario oculto em perfis nao autorizados.

Observacao importante:

- Se for necessario manter ordenacao de precisao por horario apenas para perfil `9`, nao enviar horario escondido para perfis nao `9` apenas para sustentar o `sort` do navegador.
- Para perfis nao autorizados, a ordenacao da coluna inicial deve ser feita com base em data ou na ordem ja entregue pelo backend.

### Etapa 3. Ajustar a aba `Forms`

Arquivos principais:

- `sistema/app/routers/admin.py`
- `sistema/app/schemas.py`
- `sistema/app/static/admin/index.html`
- `sistema/app/static/admin/app.js`
- `sistema/app/static/admin/styles.css`

Situacao atual:

- A rota `/api/admin/forms` usa `dependencies=[Depends(require_full_admin_session)]`.
- O handler nao recebe o usuario atual explicitamente.
- O payload devolve `data` e `hora`.
- O HTML tem 9 colunas fixas.
- O JS sempre monta a celula `Hora`.

Plano recomendado:

1. Alterar a assinatura da rota para receber `current_admin: User = Depends(require_full_admin_session)` em vez de usar apenas a dependencia na lista.
2. Passar a capacidade de visualizacao sensivel para `build_provider_forms_rows()`.
3. Tornar `ProviderFormRow.hora` anulavel no schema, ou criar um schema seguro equivalente.
4. Para perfil `9`:
   - manter `hora` preenchida.
5. Para demais perfis:
   - devolver `hora = null` ou omitir a informacao equivalente.
6. No frontend, esconder completamente a coluna `Hora` para quem nao puder ve-la.
7. Tornar dinamicos:
   - o cabecalho da tabela
   - a criacao das linhas
   - o `colspan` do empty state
   - as larguras CSS da tabela
8. Criar uma classe especifica para a tabela sem hora, por exemplo:
   - `forms-table--without-time`
9. Adicionar regras CSS proprias para a tabela com 8 colunas, sem alterar o layout dos demais casos.

Objetivo dessa etapa:

- O usuario com perfil `1` continua acessando `Forms`, mas sem ver a coluna `Hora` e sem receber horario pela API.

### Etapa 4. Ajustar a aba `Relatorios` na tela

Arquivos principais:

- `sistema/app/routers/admin.py`
- `sistema/app/schemas.py`
- `sistema/app/static/admin/app.js`
- `sistema/app/static/admin/styles.css`

Situacao atual:

- `build_report_events_response()` devolve `event_date` e `event_time_label`.
- `renderReportsResults()` sempre monta a coluna `Horario`.
- O `colgroup` da tabela presume a coluna de horario.

Plano recomendado:

1. Alterar a rota `/api/admin/reports/events` para receber o `current_admin` explicitamente.
2. Passar a capacidade de visualizacao para `build_report_events_response()`.
3. Tornar `event_time_label` anulavel, ou criar um schema de exibicao seguro equivalente.
4. Para perfil `9`:
   - manter `event_time_label` preenchido.
5. Para demais perfis:
   - devolver `event_time_label = null`.
6. Manter `event_date` sempre preenchido, porque ele continuara sendo usado para agrupamento por data.
7. No frontend, fazer `renderReportsResults()` montar duas variantes de tabela:
   - com coluna `Horario` para perfil `9`
   - sem coluna `Horario` para os demais
8. Ajustar o `colgroup` e as classes CSS para ambas as variantes.
9. Garantir que os grupos por data continuem identicos ao comportamento atual.
10. Garantir que `Origem`, `Local`, `Projeto`, `Fuso horario` e `Assiduidade` permaneçam inalterados.

### Etapa 5. Ajustar `Exportar` e `Exportar Tudo` em `Relatorios`

Arquivos principais:

- `sistema/app/routers/admin.py`
- `tests/test_api_flow.py`

Situacao atual:

- A exportacao individual usa `REPORT_EXPORT_COLUMNS` fixo com `Horario`.
- A exportacao completa herda essa estrutura e hoje coloca `Horario` na coluna `C`.

Plano recomendado:

1. Alterar as rotas de exportacao para receber `current_admin` explicitamente:
   - `/api/admin/reports/events/export`
   - `/api/admin/reports/events/export-all`
2. Substituir o uso de colunas fixas por builders dinamicos, por exemplo:
   - `build_report_export_columns(can_view_activity_time)`
   - `build_report_event_export_values(row, can_view_activity_time)`
   - equivalente para exportacao completa
3. Para perfil `9`, manter exatamente o layout atual das planilhas.
4. Para os demais perfis, remover a coluna `Horario` da planilha.
5. Ajustar automaticamente:
   - cabecalho das colunas
   - quantidade de colunas usada no `merge_cells`
   - posicao dos dados em cada linha
6. Preservar o nome do arquivo, a aba `Relatorio` e as linhas de metadados ja existentes.
7. Atualizar os testes para validar dois cenarios:
   - perfil `9`: coluna `Horario` presente
   - perfil nao `9`: coluna `Horario` ausente

Observacao funcional importante:

- Quando a coluna `Horario` for removida para perfis nao `9`, a antiga coluna `D` passara a ocupar a coluna `C` e assim por diante.
- Isso e esperado e deve ser refletido conscientemente nos testes.

### Etapa 6. Ajustar a aba `Eventos`

Arquivos principais:

- `sistema/app/routers/admin.py`
- `sistema/app/schemas.py`
- `sistema/app/static/admin/index.html`
- `sistema/app/static/admin/app.js`

Situacao atual:

- O backend devolve `EventRow.event_time` bruto.
- O frontend usa `makeEventDateTimeCell(row.event_time, row.timezone_name)`.
- A tabela `Eventos` hoje mostra duas linhas na primeira coluna: data e horario.

Plano recomendado:

1. Alterar a rota `/api/admin/events` para receber o `current_admin` explicitamente.
2. Criar campos seguros de exibicao para a data/horario do evento, por exemplo:
   - `event_date_label`
   - `event_time_label` ou `null`
3. Para perfil `9`:
   - manter data + horario.
4. Para demais perfis:
   - manter apenas a data.
5. No frontend, fazer a primeira coluna da tabela `Eventos` usar os campos seguros.
6. Atualizar o titulo visual da coluna para manter coerencia:
   - `Horario` para perfil `9`
   - `Data` para demais perfis, se a decisao de UX for tornar o texto coerente com o conteudo.
7. Nao alterar nenhuma das outras colunas da tabela `Eventos`.

### Etapa 7. Ajustar o estado global do frontend com a nova capacidade

Arquivo principal:

- `sistema/app/static/admin/app.js`

Plano recomendado:

1. Criar um estado global simples, por exemplo:
   - `adminCanViewActivityTime`
2. Alimentar esse estado em `showAdminShell(admin)` a partir da sessao.
3. Resetar esse estado em logout ou quando a sessao expirar.
4. Centralizar a verificacao em um helper unico no frontend para evitar repeticao.

Beneficio:

- A SPA passa a ter uma unica fonte de verdade para saber se deve renderizar colunas e labels sensiveis.

### Etapa 8. Preparar o HTML para mutacoes seguras e de baixo risco

Arquivo principal:

- `sistema/app/static/admin/index.html`

Como o HTML atual tem cabecalhos fixos, a recomendacao e adicionar pontos de ancoragem claros para manipulacao do DOM, por exemplo:

- `id` ou `data-*` no cabecalho sensivel de `Check-In`
- `id` ou `data-*` no cabecalho sensivel de `Check-Out`
- `id` ou `data-*` no cabecalho sensivel de `Forms`
- `id` ou `data-*` no cabecalho sensivel de `Eventos`
- `data-*` nos labels de filtros que hoje dizem `Filtrar Horario`

Objetivo:

- Permitir alterar label, ocultar coluna e aplicar classes CSS sem mexer em trechos nao relacionados.

### Etapa 9. Ajustar CSS somente onde houver mudanca estrutural real

Arquivo principal:

- `sistema/app/static/admin/styles.css`

Recomendacoes:

1. Nao reformatar CSS de tabelas nao impactadas.
2. Criar classes especificas para as variantes sem horario.
3. Atualizar apenas os seletores necessarios para:
   - `Forms` com 8 colunas
   - `Relatorios` sem coluna `Horario`
4. Manter a tabela `Check-In`, `Check-Out` e `Eventos` com a mesma quantidade de colunas, mudando apenas o conteudo da primeira coluna quando necessario.
5. Verificar responsividade e os `labels` gerados por `applyResponsiveLabels()`.

## 7. Sequencia de implementacao recomendada

Para reduzir risco e facilitar rollback local, a ordem recomendada e:

1. Criar helper de permissao sensivel no backend.
2. Expor a capacidade na sessao (`/api/admin/auth/session`).
3. Refatorar o backend das rotas afetadas para nao devolver horario a perfis nao autorizados.
4. Ajustar exportacoes XLSX.
5. Ajustar frontend para usar a nova capacidade.
6. Ajustar HTML e CSS das colunas dinamicas.
7. Atualizar testes backend.
8. Atualizar testes estaticos do frontend.
9. Executar smoke tests manuais com perfis diferentes.

Essa ordem e importante porque o maior risco de seguranca esta no backend, nao na camada visual.

## 8. Plano de testes detalhado

### 8.1. Testes de backend

Adicionar ou ajustar testes em `tests/test_api_flow.py` para cobrir pelo menos estes cenarios:

1. Sessao Admin
   - perfil `9` recebe `can_view_activity_time = true`
   - perfil `1` recebe `can_view_activity_time = false`
   - perfil `0` recebe `can_view_activity_time = false`

2. `Check-In` e `Check-Out`
   - perfil `9` recebe data + horario
   - perfil `0` recebe apenas data
   - validar que o horario bruto nao fica acessivel para perfil nao autorizado

3. `Forms`
   - perfil `9` recebe `hora`
   - perfil `1` recebe `hora = null` ou payload equivalente sem valor
   - rota continua retornando `200` para perfil `1`

4. `Relatorios`
   - perfil `9` recebe `event_time_label`
   - perfil `1` nao recebe horario utilizavel
   - agrupamento por `event_date` continua correto

5. `Exportar`
   - perfil `9` gera planilha com coluna `Horario`
   - perfil `1` gera planilha sem coluna `Horario`

6. `Exportar Tudo`
   - perfil `9` gera planilha com `Horario` na coluna `C`
   - perfil `1` gera planilha sem a coluna `Horario`

7. `Eventos`
   - perfil `9` recebe data + horario
   - perfil `1` recebe apenas data
   - nenhum horario bruto fica acessivel para perfil nao autorizado

### 8.2. Testes estaticos de frontend

Arquivos provaveis de ajuste:

- `tests/check_admin_presence_forms_layout.test.js`
- `tests/check_admin_project_timezone_ui.test.js`
- `tests/check_admin_reports_ui.test.js`

Estrutura recomendada de validacao:

1. Parar de assumir que a coluna de horario esta sempre fixa no HTML em todos os contextos.
2. Passar a validar que o frontend possui suporte a renderizacao condicional.
3. Validar a existencia de:
   - hooks de DOM para colunas sensiveis
   - helper de permissao no frontend
   - variantes de montagem com e sem horario
   - classes CSS alternativas para tabelas que perdem coluna

### 8.3. Smoke tests manuais obrigatorios

Executar pelo menos estes cenarios no ambiente local:

1. Login com perfil `9`
   - `Check-In`: mostra data + horario
   - `Check-Out`: mostra data + horario
   - `Forms`: mostra coluna `Hora`
   - `Relatorios`: mostra coluna `Horario`
   - `Exportar`: XLSX com `Horario`
   - `Exportar Tudo`: XLSX com `Horario`
   - `Eventos`: mostra data + horario

2. Login com perfil `1`
   - continua acessando as mesmas abas que ja acessa hoje
   - `Check-In`: mostra apenas data
   - `Check-Out`: mostra apenas data
   - `Forms`: nao mostra coluna `Hora`
   - `Relatorios`: nao mostra coluna `Horario`
   - `Exportar`: XLSX sem `Horario`
   - `Exportar Tudo`: XLSX sem `Horario`
   - `Eventos`: mostra apenas data

3. Login com perfil `0`
   - continua acessando apenas o escopo limitado atual
   - `Check-In` e `Check-Out`: apenas data
   - sem regressao nas restricoes de abas

4. Verificacao de rede
   - inspecionar respostas JSON das rotas afetadas para confirmar ausencia de horario exato em perfis nao `9`

## 9. Riscos principais e mitigacoes

### Risco 1. Esconder na UI, mas continuar vazando no JSON

Mitigacao:

- Fazer a sanitizacao no backend antes da serializacao.

### Risco 2. Quebrar layout das tabelas por mudanca no numero de colunas

Mitigacao:

- Usar classes CSS dedicadas para as variantes sem horario.
- Ajustar `colspan`, `colgroup` e `applyResponsiveLabels()` conscientemente.

### Risco 3. Quebrar ordenacao e filtros em `Check-In` e `Check-Out`

Mitigacao:

- Atualizar `getPresenceRowDisplayValue()`, `getPresenceFilterOptions()` e a logica de sort para usar dados seguros.

### Risco 4. Quebrar exportacao XLSX por manter contagem fixa de colunas

Mitigacao:

- Tornar o cabecalho e as linhas da planilha totalmente dinamicos com base na permissao.

### Risco 5. Regressao em perfis limitados

Mitigacao:

- Testar explicitamente perfil `0` em `checkin` e `checkout`, porque esse perfil continua entrando no painel com escopo limitado.

## 10. Critérios de aceite

O trabalho pode ser considerado concluido quando todos os pontos abaixo forem verdadeiros ao mesmo tempo:

1. Apenas perfil `9` ve horario exato nas areas solicitadas.
2. Perfis nao `9` continuam usando o Admin sem perder funcionalidades que nao fazem parte deste requisito.
3. A API nao entrega horario exato para perfis nao autorizados nas rotas afetadas.
4. As exportacoes XLSX respeitam a mesma regra da UI.
5. Os testes automatizados atualizados passam.
6. Os smoke tests manuais com perfis `9`, `1` e `0` passam.

## 11. Recomendacao final de implementacao

A melhor abordagem para preservar o Admin que ja esta funcionando e:

- nao mudar as regras de acesso das abas
- nao criar excecoes espalhadas no frontend
- nao confiar em ocultacao visual isolada
- centralizar a permissao de horario sensivel no backend
- usar contratos de exibicao seguros para cada tabela
- ajustar o frontend apenas para refletir a permissao que a sessao ja informou

Assim, a alteracao fica localizada, auditavel, testavel e com menor risco de regressao sobre o restante do Website do Administrador.

## 12. To-do list detalhada por fases

### Fase 0. Fechamento funcional e preparacao

- [x] Confirmar formalmente que a regra de visibilidade sensivel sera `apenas perfil 9`.
- [x] Validar com o responsavel de produto se perfis legados como `19`, `29`, `99` ou `999` devem ou nao herdar a visualizacao de horario.
- [x] Consolidar que a regra e global por perfil e nao deve ser relaxada em outras interfaces que exponham o mesmo dado sensivel.
- [x] Confirmar que `Check-In`, `Check-Out`, `Forms`, `Relatorios`, exportacoes e `Eventos` sao todas as superficies que expoem horario sensivel no Admin.
- [x] Mapear no codigo todos os pontos que hoje leem `admin.perfil` ou derivam permissao da sessao para evitar criacao de regra duplicada.
- [x] Registrar a decisao final sobre perfis legados no proprio documento antes de iniciar implementacao.

### Fase 1. Centralizacao da permissao sensivel no backend

- [x] Criar helper unico de autorizacao para horario sensivel em `sistema/app/services/admin_auth.py`.
- [x] Garantir que o helper fique desacoplado de `access_scope` e `allowed_tabs`.
- [x] Aplicar a igualdade estrita com `9` aprovada na Fase 0 na nova capacidade sensivel.
- [x] Adicionar teste unitario ou de integracao cobrindo o helper novo para perfil `9`.
- [x] Adicionar teste cobrindo perfil `1` sem acesso ao horario.
- [x] Adicionar teste cobrindo perfil `0` sem acesso ao horario.
- [x] Adicionar teste cobrindo o caso legado decidido na Fase 0 (`999` nao herda visibilidade de horario).

### Fase 2. Exposicao da nova capacidade na sessao do Admin

- [x] Atualizar `AdminIdentity` em `sistema/app/schemas.py` para expor um booleano explicito, por exemplo `can_view_activity_time`.
- [x] Atualizar `build_admin_identity()` em `sistema/app/routers/admin.py` para preencher esse campo.
- [x] Confirmar que `/api/admin/auth/session` continua retornando `access_scope` e `allowed_tabs` sem regressao.
- [x] Garantir que a autenticacao de perfil `0` continue funcionando no painel com escopo limitado.
- [x] Adicionar teste para `/api/admin/auth/session` validando `can_view_activity_time = true` para perfil `9`.
- [x] Adicionar teste para `/api/admin/auth/session` validando `can_view_activity_time = false` para perfil `1`.
- [x] Adicionar teste para `/api/admin/auth/session` validando `can_view_activity_time = false` para perfil `0`.

### Fase 3. Sanitizacao backend de `Check-In` e `Check-Out`

- [x] Revisar o contrato atual de `UserRow` em `sistema/app/schemas.py`.
- [x] Definir se a linha de presenca passara a expor campos seguros novos ou um schema alternativo para exibicao.
- [x] Preservar a ordenacao de backend por timestamp real antes da sanitizacao.
- [x] Ajustar `build_presence_rows()` para preencher data e horario apenas quando permitido.
- [x] Garantir que perfis nao autorizados recebam somente a data de exibicao.
- [x] Garantir que perfis nao autorizados nao recebam horario bruto serializado em campos auxiliares.
- [x] Revisar se `time` pode continuar existindo no schema ou se deve ser substituido por campos de display seguros.
- [x] Ajustar as rotas `/api/admin/checkin` e `/api/admin/checkout` para usar a nova representacao segura sem afetar o controle de acesso atual.
- [x] Adicionar teste para `/api/admin/checkin` com perfil `9` validando data + horario.
- [x] Adicionar teste para `/api/admin/checkin` com perfil `0` validando apenas data.
- [x] Adicionar teste para `/api/admin/checkout` com perfil `9` validando data + horario.
- [x] Adicionar teste para `/api/admin/checkout` com perfil `0` validando apenas data.

### Fase 4. Sanitizacao backend da aba `Forms`

- [x] Alterar a rota `/api/admin/forms` para receber `current_admin: User = Depends(require_full_admin_session)` explicitamente.
- [x] Passar a permissao sensivel para `build_provider_forms_rows()`.
- [x] Tornar `ProviderFormRow.hora` anulavel ou criar contrato seguro equivalente.
- [x] Garantir que perfil `9` continue recebendo `hora` normalmente.
- [x] Garantir que perfil `1` nao receba horario utilizavel em `hora`.
- [x] Confirmar que `data`, `recebimento`, `atividade`, `informe`, `projeto` e `timezone_label` continuam corretos.
- [x] Verificar se `recebimento` tambem precisa ser sanitizado na API ou apenas a coluna dedicada `Hora` faz parte da restricao aprovada.
- [x] Adicionar teste de API para `/api/admin/forms` com perfil `9`.
- [x] Adicionar teste de API para `/api/admin/forms` com perfil `1` sem horario.
- [x] Confirmar que a funcionalidade `Limpar` de `Forms` continua intacta.

### Fase 5. Sanitizacao backend da aba `Relatorios`

- [x] Alterar a rota `/api/admin/reports/events` para receber `current_admin` explicitamente.
- [x] Passar a permissao sensivel para `build_report_events_response()`.
- [x] Tornar `ReportEventRow.event_time_label` anulavel ou criar contrato seguro equivalente.
- [x] Sanitizar tambem `ReportEventRow.event_time` bruto para perfis nao `9`.
- [x] Manter `event_date` sempre preenchido.
- [x] Garantir que perfil `9` continue recebendo `event_time_label`.
- [x] Garantir que perfil `1` nao receba horario utilizavel em `event_time_label`.
- [x] Confirmar que `source_label`, `action_label`, `local_label`, `projeto`, `timezone_label` e `assiduidade` continuam inalterados.
- [x] Confirmar que o agrupamento por data continua correto mesmo sem horario visivel.
- [x] Adicionar teste de API para `/api/admin/reports/events` com perfil `9`.
- [x] Adicionar teste de API para `/api/admin/reports/events` com perfil `1` sem horario.
- [x] Registrar compatibilidade da UI atual: `renderReportsResults()` continua agrupando por `event_date` e tolera `event_time = null` / `event_time_label = null` sem quebrar a tabela.

### Fase 6. Sanitizacao backend das exportacoes de `Relatorios`

- [x] Alterar a rota `/api/admin/reports/events/export` para receber `current_admin` explicitamente.
- [x] Alterar a rota `/api/admin/reports/events/export-all` para receber `current_admin` explicitamente.
- [x] Refatorar `REPORT_EXPORT_COLUMNS` para uma estrutura dinamica baseada na permissao.
- [x] Criar builder para colunas da exportacao individual com e sem `Horario`.
- [x] Criar builder para colunas da exportacao completa com e sem `Horario`.
- [x] Ajustar `build_report_event_export_values()` para respeitar a nova estrutura.
- [x] Ajustar `build_report_events_export()` para recalcular `merge_cells` conforme a quantidade real de colunas.
- [x] Ajustar `build_all_report_events_export()` para remover `Horario` da coluna `C` quando o perfil nao puder ver essa informacao.
- [x] Garantir que nomes de arquivo, titulo da aba e metadados do topo permaneçam identicos ao comportamento atual.
- [x] Adicionar teste da exportacao individual com perfil `9` mantendo `Horario`.
- [x] Adicionar teste da exportacao individual com perfil `1` sem `Horario`.
- [x] Adicionar teste da exportacao completa com perfil `9` mantendo `Horario`.
- [x] Adicionar teste da exportacao completa com perfil `1` sem `Horario`.
- [x] Confirmar que `perfil 0` continua bloqueado nas duas rotas de exportacao de `Relatorios`.

### Fase 7. Sanitizacao backend da aba `Eventos`

- [x] Alterar a rota `/api/admin/events` para receber `current_admin` explicitamente.
- [x] Revisar o schema `EventRow` para expor campos seguros de data e horario, ou criar contrato alternativo de exibicao.
- [x] Ajustar `build_event_row_payload()` para preencher data + horario apenas quando permitido.
- [x] Garantir que perfis nao autorizados recebam apenas a data de exibicao.
- [x] Garantir que `event_time` bruto nao permaneça exposto para perfis nao `9`, caso esse campo participe da resposta final.
- [x] Confirmar que as demais colunas da aba `Eventos` nao sofram qualquer alteracao funcional.
- [x] Adicionar teste de API para `/api/admin/events` com perfil `9`.
- [x] Adicionar teste de API para `/api/admin/events` com perfil `1` sem horario.
- [x] Registrar a compatibilidade minima da UI atual: `loadEvents()` passou a priorizar `event_date_label` e `event_time_label`, sem ainda alterar o cabecalho fixo `Horario`.

### Fase 8. Estado global e helpers do frontend

- [x] Criar estado global em `sistema/app/static/admin/app.js`, por exemplo `adminCanViewActivityTime`.
- [x] Alimentar esse estado em `showAdminShell(admin)` a partir de `session.admin.can_view_activity_time`.
- [x] Resetar esse estado em logout, expiracao de sessao e retorno para `authShell`.
- [x] Criar helper unico no frontend para consultar a permissao e evitar condicionais dispersas.
- [x] Revisar as chamadas de renderizacao que hoje assumem horario por padrao.
- [x] Garantir que a nova permissao nao afete `allowedAdminTabs` nem preload de abas.

### Fase 9. Ajustes de frontend em `Check-In` e `Check-Out`

- [x] Atualizar o cabecalho da primeira coluna para variar entre `Horario` e `Data` conforme a permissao.
- [x] Atualizar os labels de filtro `Filtrar Horario` para `Filtrar Data` quando necessario.
- [x] Refatorar `buildPresenceRow()` para renderizar duas linhas apenas para perfil `9`.
- [x] Refatorar `getPresenceRowDisplayValue()` para usar o valor seguro da coluna inicial.
- [x] Refatorar `getPresenceFilterOptions()` para gerar opcoes coerentes com o valor efetivamente exibido.
- [x] Revisar `sortPresenceRows()` e `getPresenceRowSortValue()` para nao depender de horario oculto no frontend.
- [x] Garantir que `renderEmptyStateRow()` mantenha `colspan` correto.
- [x] Validar que os totais `Usuários em Check-In` e `Usuários em Check-Out` continuam corretos.
- [x] Validar que `applyResponsiveLabels()` continua coerente no mobile com a coluna alterada.

### Fase 10. Ajustes de frontend em `Forms`

- [x] Adicionar ancoragem no HTML para o cabecalho da coluna `Hora`.
- [x] Criar logica para ocultar completamente a coluna `Hora` quando `adminCanViewActivityTime` for falso.
- [x] Ajustar `loadForms()` para montar 9 colunas com perfil `9` e 8 colunas para os demais.
- [x] Ajustar `renderEmptyStateRow("formsBody", ...)` para usar `colspan` dinamico.
- [x] Adicionar ou aplicar classe de variante, como `forms-table--without-time`, quando a coluna nao existir.
- [x] Ajustar CSS da tabela `Forms` sem alterar a variante atual com `Hora`.
- [x] Confirmar que os botoes `Atualizar` e `Limpar` continuam funcionando sem dependencia da coluna removida.
- [x] Validar responsividade da tabela `Forms` nas duas variantes.

### Fase 11. Ajustes de frontend em `Relatorios`

- [x] Refatorar `renderReportsResults()` para montar tabela com `Horario` apenas para perfil `9`.
- [x] Criar variante da tabela de `Relatorios` sem a coluna `Horario`.
- [x] Ajustar o `colgroup` da tabela para as duas variantes.
- [x] Confirmar que o agrupamento visual por data continua identico ao atual.
- [x] Garantir que `reportsHasLoadedResult` e `reportsExportQueryString` continuem funcionando igual.
- [x] Garantir que os botoes `Exportar` e `Exportar Tudo` continuem aparecendo nos cenarios corretos.
- [x] Ajustar CSS de `reports-results-table` sem afetar alinhamento das demais colunas.
- [x] Validar comportamento responsivo da tabela com e sem coluna de horario.

### Fase 12. Ajustes de frontend em `Eventos`

- [x] Adicionar ancoragem no HTML para o cabecalho sensivel da primeira coluna de `Eventos`.
- [x] Decidir se o titulo visual permanece `Horario` ou muda para `Data` para perfis nao `9`.
- [x] Refatorar `loadEvents()` para usar campos seguros de exibicao em vez de timestamp bruto.
- [x] Ajustar `makeEventDateTimeCell()` ou criar variante que renderize apenas data quando necessario.
- [x] Garantir que a abertura de detalhes do evento continue igual.
- [x] Confirmar que ordenacao, totais e `updateDashboardSummary()` nao sofram regressao.
- [x] Validar responsividade da tabela `Eventos` com a nova representacao da primeira coluna.

### Fase 13. Ajustes estruturais de HTML e CSS

- [x] Inserir `id` ou `data-*` nos cabecalhos sensiveis de `Check-In`, `Check-Out`, `Forms` e `Eventos`.
- [x] Inserir `data-*` nos labels de filtro relacionados a horario/data.
- [x] Revisar se alguma tabela precisa de classes variantes adicionais alem de `Forms` e `Relatorios`.
- [x] Criar somente os seletores CSS necessarios para as variantes sem horario.
- [x] Evitar reformatacao global de `styles.css`.
- [x] Conferir se `event-cell`, `event-datetime-cell` e `event-datetime-line` continuam corretos nas duas apresentacoes.

### Fase 14. Atualizacao dos testes automatizados

- [x] Atualizar `tests/check_admin_presence_forms_layout.test.js` para refletir suporte condicional a coluna `Hora`.
- [x] Atualizar `tests/check_admin_project_timezone_ui.test.js` para parar de assumir horario fixo em toda renderizacao.
- [x] Atualizar `tests/check_admin_reports_ui.test.js` para validar estrutura condicional nas tabelas de `Relatorios`.
- [x] Adicionar ou ajustar testes em `tests/test_api_flow.py` para cada rota afetada.
- [x] Garantir cobertura para perfil `9` e para pelo menos um perfil nao `9` em todas as superficies sensiveis.
- [x] Garantir que os testes atuais de funcionalidades nao relacionadas nao precisem ser relaxados desnecessariamente.

### Fase 15. Validacao manual e fechamento

- [x] Executar smoke test manual com perfil `9` em todas as abas afetadas.
- [x] Executar smoke test manual com perfil `1` em todas as abas afetadas.
- [x] Executar smoke test manual com perfil `0` em `Check-In` e `Check-Out`.
- [x] Inspecionar respostas de rede para confirmar ausencia de horario em perfis nao autorizados.
- [x] Validar exportacao XLSX gerada para perfil `9`.
- [x] Validar exportacao XLSX gerada para perfil `1`.
- [x] Revisar se nenhuma outra funcionalidade do Admin foi alterada acidentalmente.
- [x] Confirmar que os criterios de aceite da secao 10 foram todos atendidos.
- [x] Atualizar o documento com status final, decisoes tomadas e eventuais excecoes aprovadas.

## 13. Encerramento final

Status final desta frente:

- Todas as fases de `0` a `15` foram concluidas.
- A regra funcional final permanece estrita: apenas perfil normalizado exatamente igual a `9` pode visualizar horario sensivel.
- Nenhuma excecao adicional foi aprovada para perfis legados como `19`, `29`, `99` ou `999`.

Validacoes executadas no fechamento em `27/04/2026`:

1. Smoke final do Admin em navegador headless contra servidor HTTP local, cobrindo login e navegacao real no `/admin` para tres perfis:
   - perfil `9`: `Check-In`, `Check-Out`, `Forms`, `Relatorios` e `Eventos` mantiveram labels e colunas com horario.
   - perfil `1`: as mesmas abas permaneceram acessiveis, mas com horario oculto em UI, JSON e exportacoes.
   - perfil `0`: o shell permaneceu limitado a `Check-In` e `Check-Out`, sem acesso a `Forms`, `Relatorios` e `Eventos`.
2. Inspecao autenticada das respostas JSON de sessao e das rotas sensiveis:
   - `/api/admin/auth/session`
   - `/api/admin/checkin`
   - `/api/admin/checkout`
   - `/api/admin/forms`
   - `/api/admin/reports/events`
   - `/api/admin/events`
   - bloqueios `403` esperados para perfil `0` nas areas fora do escopo limitado.
3. Validacao das exportacoes XLSX de `Relatorios` com leitura estrutural do arquivo gerado:
   - perfil `9`: `Horário` permaneceu presente em `/api/admin/reports/events/export` e `/api/admin/reports/events/export-all`.
   - perfil `1`: a coluna `Horário` permaneceu ausente nas duas exportacoes.
4. Confirmacao de ausencia de regressao acidental por meio das validacoes automatizadas ja executadas ao fim das fases anteriores, incluindo regressao estatica do frontend e subconjunto focado de `pytest` nas superficies sensiveis.

Critérios de aceite da secao `10`:

- `1.` Atendido.
- `2.` Atendido.
- `3.` Atendido.
- `4.` Atendido.
- `5.` Atendido.
- `6.` Atendido.

Conclusao:

- Esta entrega foi encerrada sem pendencias abertas dentro do escopo aprovado do Admin.
- O comportamento final ficou coerente entre backend, frontend, exportacoes e shell administrativo.
- Eventuais evolucoes futuras devem partir desta linha de base, sem reabrir a regra de visibilidade sensivel por digitos legados sem nova decisao formal.