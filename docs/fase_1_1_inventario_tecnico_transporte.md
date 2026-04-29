# Inventário técnico inicial do módulo de transporte

## Objetivo deste artefato

Este documento materializa o início da fase 1.1 do plano de reorganização do transporte. O objetivo aqui é consolidar, por arquivo e por função, como o módulo está organizado hoje, quais responsabilidades já existem, onde estão os principais pontos de leitura e escrita, e em quais trechos o acoplamento atual é mais forte.

Este inventário não substitui o descritivo funcional do dashboard nem o catálogo operacional de ações. Ele funciona como uma linha de base técnica para as próximas fases de reorganização. Em outras palavras, este documento responde a quatro perguntas fundamentais: onde o transporte entra na aplicação, quais arquivos concentram cada parte do comportamento, quais funções controlam os fluxos principais e quais pontos hoje acumulam responsabilidades demais.

## Escopo mapeado nesta etapa

O mapeamento inicial desta fase cobre os arquivos e superfícies centrais do módulo de transporte:

- `sistema/app/main.py`
- `sistema/app/routers/transport.py`
- `sistema/app/services/transport.py`
- `sistema/app/schemas.py`
- `sistema/app/models.py`
- `sistema/app/static/transport/index.html`
- `sistema/app/static/transport/styles.css`
- `sistema/app/static/transport/app.js`
- `sistema/app/static/transport/i18n.js`
- `sistema/app/static/transport/functions/functions.md`
- `sistema/app/static/transport/functions/functions_by_capability.md`
- `docs/descritivo_transport.md`
- `docs/catalogo_acoes_transport.yaml`

## Panorama consolidado por arquivo

| Arquivo | Papel atual | Natureza predominante | Situação atual |
| --- | --- | --- | --- |
| `sistema/app/main.py` | Publicação da API e do site estático de transporte | Infraestrutura | Estável, com responsabilidade bem delimitada |
| `sistema/app/routers/transport.py` | Fronteira HTTP do transporte | Entrada de API | Relativamente enxuto, mas ainda reflete serviços muito concentrados |
| `sistema/app/services/transport.py` | Núcleo de regras de negócio do transporte | Misto: leitura, escrita, exportação e helpers | Principal hotspot de acoplamento atual |
| `sistema/app/schemas.py` | Contratos de entrada e saída do transporte | Contrato e validação | Bem estruturado, mas ainda sem contrato explícito de atualização de veículo |
| `sistema/app/models.py` | Persistência do domínio | Modelo de dados | Estrutura suficiente, mas com relacionamentos apoiados em chaves de negócio mutáveis |
| `sistema/app/static/transport/index.html` | Casca estrutural da interface | UI estática | Define a composição visual e os pontos de interação do dashboard |
| `sistema/app/static/transport/styles.css` | Layout, responsividade e comportamento visual | UI estática | Centraliza aparência e organização espacial da tela |
| `sistema/app/static/transport/app.js` | Controlador principal do frontend | UI + estado + integração com API | Grande, monolítico e com muitas responsabilidades |
| `sistema/app/static/transport/i18n.js` | Dicionários e configuração de idioma | Infraestrutura de frontend | Delimitado e reutilizado pelo `app.js` |
| `sistema/app/static/transport/functions/functions.md` | Inventário canônico das funções nomeadas do frontend | Documentação técnica | Já cobre 192 funções nomeadas |
| `sistema/app/static/transport/functions/functions_by_capability.md` | Agrupamento funcional das funções do frontend | Documentação técnica | Excelente ponto de entrada para navegar o `app.js` |
| `docs/descritivo_transport.md` | Visão funcional e arquitetural do dashboard | Documentação funcional | Base descritiva já consolidada |
| `docs/catalogo_acoes_transport.yaml` | Superfície declarativa para futuras automações | Documentação operacional | Base útil para ações futuras sem depender da UI |

## 1. Infraestrutura de publicação do módulo

### Arquivo: `sistema/app/main.py`

Responsabilidade atual: publicar o site estático de transporte em `/transport`, expor o roteador HTTP de transporte e garantir que o módulo participe do ciclo de vida geral da aplicação.

Funções mapeadas:

- `should_serve_static_site`: decide se o site estático de transporte será servido com base na configuração da aplicação.
- `build_static_index_handler`: cria o handler que entrega o `index.html` do site estático.
- `build_static_trailing_slash_handler`: normaliza o acesso à rota estática com barra final.
- `mount_static_site`: monta o diretório estático em uma rota da aplicação FastAPI.
- `lifespan`: participa do ciclo de vida global da API; não é específico de transporte, mas afeta o contexto em que o módulo roda.

Leitura ou comando: infraestrutura, sem regra específica de negócio do transporte.

Observação importante: este arquivo não é o problema arquitetural do transporte. Ele apenas revela que o módulo hoje é composto de duas superfícies coordenadas: a API `/api/transport/*` e o site estático `/transport`.

## 2. Fronteira HTTP do transporte

### Arquivo: `sistema/app/routers/transport.py`

Responsabilidade atual: receber requisições HTTP, aplicar autenticação de sessão, validar payloads e delegar a execução para os serviços do domínio.

Funções de apoio interno:

- `build_transport_identity`: monta a identidade exposta pela sessão autenticada de transporte.
- `encode_sse`: empacota o payload textual enviado no stream SSE.

Funções de autenticação e sessão:

- `transport_session`: verifica se há sessão de transporte já estabelecida e devolve o estado autenticado.
- `verify_transport_access`: valida `chave` e `senha`, autoriza o acesso ao dashboard e grava a sessão.
- `transport_logout`: encerra a sessão atual do transporte.

Funções de leitura operacional:

- `get_transport_dashboard`: entrega o payload principal consumido pelo dashboard na data selecionada.
- `export_transport_list`: expõe a exportação atual em XLSX.
- `get_transport_settings`: lê configurações globais do módulo.
- `get_transport_workplaces`: lista workplaces cadastrados.

Funções de comando operacional:

- `update_transport_settings`: altera configurações globais do transporte.
- `update_transport_date_settings`: altera o horário por data específica.
- `create_transport_workplace`: cria workplace no backend.
- `create_transport_vehicle`: cadastra veículo e delega a criação das agendas correspondentes.
- `delete_transport_vehicle_for_route`: remove veículo a partir de um `schedule_id`, com efeito destrutivo maior do que o nome da rota sugere.
- `save_transport_assignment`: confirma, altera ou devolve alocação para pendência.
- `reject_transport_request`: rejeita solicitação e delega o tratamento de suas alocações.

Classificação atual: o roteador está razoavelmente fino, mas ele evidencia algumas limitações estruturais do domínio.

Principais achados desta fase:

- A superfície HTTP já distingue leitura de alguns comandos, mas ainda não expõe um fluxo explícito de atualização de veículo.
- O contrato disponível para veículo é assimétrico: hoje existe criação e remoção, mas não atualização formal.
- A remoção usa `schedule_id`, o que mostra que o conceito operacional de agenda ainda interfere diretamente na gestão do veículo como cadastro.

## 3. Núcleo de serviços e regras de negócio

### Arquivo: `sistema/app/services/transport.py`

Responsabilidade atual: concentrar praticamente toda a lógica de negócio do transporte. Este arquivo hoje acumula leitura agregada do dashboard, exportação, manipulação de veículos, cálculo de disponibilidade, persistência de pedidos, propagação de recorrência, construção de estado para consumo web e diversas funções auxiliares.

Este é o principal arquivo da fase 1.1 porque ele mostra onde o módulo está mais acoplado.

### 3.1 Grupo funcional: exportação e leitura agregada

Funções mapeadas:

- `_build_project_row`
- `_build_transport_export_file_name`
- `_resolve_transport_export_path`
- `build_transport_list_export`
- `_resolve_web_transport_route_order`
- `build_transport_dashboard`
- `list_workplaces`

Responsabilidade atual do grupo: montar respostas prontas para consumo direto da interface ou para geração de planilhas. A função mais importante desse bloco é `build_transport_dashboard`, que lê projetos, workplaces, veículos, agendas, alocações e solicitações para devolver um único payload agregado ao frontend.

Leitura ou comando: predominantemente leitura.

Ponto de atenção: `build_transport_dashboard` é um agregador grande demais. Ele hoje conhece muitas regras operacionais ao mesmo tempo e, por isso, se tornou um dos principais candidatos a extração na fase 1.3.

### 3.2 Grupo funcional: datas, recorrência e regras temporais

Funções mapeadas:

- `_normalize_request_selected_weekdays`
- `_resolve_request_selected_weekdays`
- `_serialize_request_selected_weekdays`
- `_parse_request_selected_weekdays`
- `get_transport_request_selected_weekdays`
- `_find_next_request_service_date`
- `resolve_transport_request_dashboard_service_date`
- `_resolve_web_transport_boarding_time`
- `_resolve_web_transport_confirmation_deadline_time`
- `_resolve_web_transport_request_item_boarding_time`
- `_parse_transport_clock_time`
- `_is_web_transport_request_realized`
- `request_applies_to_date`
- `request_is_visible_on_service_date`

Responsabilidade atual do grupo: resolver como pedidos recorrentes e pedidos avulsos aparecem em uma data específica, como horários derivados são calculados e como o dashboard decide visibilidade e contexto temporal.

Leitura ou comando: leitura e cálculo derivado.

Ponto de atenção: essas regras temporais são centrais para qualquer reorganização futura. Elas já representam lógica de domínio real e não devem ficar enterradas como helpers genéricos de um único serviço monolítico.

### 3.3 Grupo funcional: veículos, disponibilidade e agendas

Funções mapeadas:

- `_resolve_vehicle_departure_time`
- `_resolve_regular_vehicle_selected_weekdays`
- `vehicle_schedule_applies_to_date`
- `create_transport_vehicle_registration`
- `delete_transport_vehicle_registration`
- `_build_schedule_specs_from_payload`
- `_classify_vehicle_schedules_for_reuse`
- `_build_vehicle_schedule_conflict_details`
- `_format_vehicle_schedule_conflict_entry`
- `_vehicle_has_active_schedule_for_spec`
- `_vehicle_has_active_schedule_on_date`
- `find_transport_vehicle_schedule`
- `get_paired_route_kind`
- `_list_active_transport_schedule_rows`
- `_load_active_schedules_by_vehicle_id`
- `_build_vehicle_row`
- `_build_vehicle_row_for_schedule`
- `_build_vehicle_rows_for_dashboard`
- `_build_transport_vehicle_registry_rows`

Responsabilidade atual do grupo: administrar o conceito combinado de veículo cadastral e presença operacional do veículo nas listas de transporte.

Leitura ou comando: misto.

Pontos de atenção:

- `create_transport_vehicle_registration` é hoje um hotspot estrutural porque mistura criação ou atualização do cadastro-base do veículo com criação, reaproveitamento ou invalidação de agendas.
- `delete_transport_vehicle_registration` tem comportamento destrutivo em cascata e mostra que o sistema ainda trata o conjunto veículo mais agenda como uma unidade operacional difícil de desmontar com segurança.
- `find_transport_vehicle_schedule` é uma função de domínio importante e já sugere que a disponibilidade operacional deveria ter uma camada própria.

### 3.4 Grupo funcional: ciclo de vida de solicitações

Funções mapeadas:

- `upsert_transport_request`
- `get_latest_active_transport_request`
- `cancel_transport_requests`
- `_close_transport_request`
- `_resolve_transport_assignment`
- `_close_transport_request_assignments`
- `cancel_transport_request_and_assignments`
- `reject_transport_request_and_assignments`
- `acknowledge_transport_assignments`
- `_resolve_transport_request_reference_service_date`
- `_build_web_transport_request_items`
- `build_web_transport_state`

Responsabilidade atual do grupo: manter o ciclo de vida dos pedidos de transporte, seus fechamentos, rejeições, confirmações derivadas e o estado disponibilizado para consumo de outros fluxos web.

Leitura ou comando: misto, com forte presença de escrita.

Ponto de atenção: a existência de `build_web_transport_state` no mesmo arquivo que monta o dashboard administrativo mostra que ainda há múltiplos consumidores do mesmo domínio acoplados no mesmo serviço.

### 3.5 Grupo funcional: alocações e persistência recorrente

Funções mapeadas:

- `update_transport_assignment`
- `_reset_transport_request_assignments_to_pending`
- `upsert_transport_assignment_with_persistence`
- `_propagate_confirmed_recurring_assignment`
- `_materialize_recurring_assignments_for_date`
- `_list_transport_assignments_for_requests`
- `_resolve_assignment_template_weekdays`
- `_build_recurring_assignment_template_index`
- `_transport_dashboard_assignment_priority`

Responsabilidade atual do grupo: aplicar, propagar, materializar e reavaliar alocações explícitas e recorrentes ao longo do tempo.

Leitura ou comando: misto, com forte peso de escrita operacional.

Pontos de atenção:

- `upsert_transport_assignment_with_persistence` é outro hotspot importante porque combina decisão operacional do dia com propagação de recorrência.
- `_propagate_confirmed_recurring_assignment` e `_materialize_recurring_assignments_for_date` tornam explícito que o módulo já possui comportamento de derivação temporal relevante, algo que no futuro deverá dialogar com a camada de propostas e aprovação.

### 3.6 Grupo funcional: infraestrutura de suporte

Funções mapeadas:

- `_purge_foreign_key_dependencies`

Responsabilidade atual do grupo: apagar dependências relacionais antes de remoções destrutivas.

Leitura ou comando: infraestrutura de escrita.

Ponto de atenção: a presença dessa função reforça que o fluxo atual de remoção tem impacto amplo no banco e que parte do custo operacional da modelagem atual vem da necessidade de deletar em cascata por ausência de separação mais explícita entre entidades.

## 4. Contratos de entrada e saída

### Arquivo: `sistema/app/schemas.py`

Responsabilidade atual: definir os contratos HTTP e os modelos de validação usados pelo transporte.

#### 4.1 Autenticação e sessão

- `TransportIdentity`
- `TransportAuthVerifyRequest`
- `TransportSessionResponse`

Papel atual: modelar quem está autenticado, como as credenciais são recebidas e qual resposta de sessão a UI consome.

#### 4.2 Workplaces e cadastro operacional

- `TransportWorkplaceUpsert`
- `WorkplaceRow`

Papel atual: definir criação e leitura de workplaces.

#### 4.3 Veículos

- `TransportVehicleCreate`
- `TransportVehicleRow`
- `TransportVehicleManagementRow`

Papel atual: modelar criação de veículo e leitura de veículos para o dashboard e para o modo de gerenciamento.

Achado importante da fase 1.1: não há um `TransportVehicleUpdate` ou equivalente. Isso confirma que a atualização explícita de veículo ainda não existe como contrato de primeira classe.

#### 4.4 Solicitações e alocações

- `TransportRequestCreate`
- `TransportAssignmentUpsert`
- `TransportRequestReject`
- `TransportRequestRow`

Papel atual: modelar pedidos de transporte, mudanças de alocação e rejeições.

#### 4.5 Dashboard e configurações

- `TransportDashboardResponse`
- `TransportSettingsResponse`
- `TransportSettingsUpdateRequest`
- `TransportDateSettingsResponse`
- `TransportDateSettingsUpdateRequest`

Papel atual: modelar o payload agregado do dashboard e as configurações globais e por data.

Conclusão desta seção: a camada de schemas está relativamente organizada, mas já mostra um vazio contratual relevante na ausência de atualização explícita de veículo.

## 5. Modelos persistidos e dependências do domínio

### Arquivo: `sistema/app/models.py`

Responsabilidade atual: representar as entidades persistidas usadas direta ou indiretamente pelo transporte.

Modelos diretamente relevantes:

- `Project`: fornece a lista de projetos usada no dashboard e em filtros operacionais.
- `Workplace`: cadastro de workplaces usados pelo módulo de transporte.
- `User`: entidade transversal que participa do transporte por meio de projeto, workplace, endereço, placa e identidade operacional.
- `Vehicle`: cadastro-base do veículo.
- `TransportVehicleSchedule`: agenda operacional do veículo.
- `TransportVehicleScheduleException`: exceções pontuais da agenda.
- `TransportDailySetting`: configuração diária do horário operacional.
- `TransportRequest`: pedido de transporte do usuário.
- `TransportAssignment`: alocação do pedido em um veículo e em uma data.

Achados estruturais importantes:

- `User` ainda se relaciona com `Workplace` por valor textual, não por identificador estável.
- `User` também referencia veículo por `placa`, o que reforça o acoplamento com uma chave de negócio editável.
- A modelagem já separa `Vehicle` e `TransportVehicleSchedule`, mas os fluxos de serviço ainda não exploram plenamente essa separação como agregados independentes.

## 6. Frontend estático do dashboard

### Arquivo: `sistema/app/static/transport/index.html`

Responsabilidade atual: definir a estrutura visual fixa do dashboard, incluindo topbar, listas de solicitações, painéis de veículos, modal de veículo, modal de configurações e área de status.

Função no inventário da fase 1.1: mostrar que o frontend do transporte é uma página estática única, sem roteamento interno, totalmente controlada por JavaScript.

### Arquivo: `sistema/app/static/transport/styles.css`

Responsabilidade atual: definir aparência, responsividade, modos de visualização, distribuição espacial dos painéis e detalhes visuais do dashboard.

Função no inventário da fase 1.1: registrar que parte importante da experiência operacional está amarrada à composição da tela, embora a lógica de domínio esteja fora do CSS.

### Arquivo: `sistema/app/static/transport/app.js`

Responsabilidade atual: atuar como controlador principal da interface, concentrando estado global, integração HTTP, SSE, renderização, autenticação, datas, drag and drop, modais, preferências e leitura do dashboard.

Este arquivo é o principal hotspot do frontend. Ele já possui inventário por função e por capacidade funcional, o que permite iniciar a fase 1.1 sem duplicar manualmente as 192 entradas já documentadas.

Resumo documental já existente:

- `functions.md`: inventário canônico das 192 funções nomeadas do frontend.
- `functions_by_capability.md`: agrupamento operacional dessas 192 funções em 11 capacidades.

Capacidades funcionais já mapeadas no frontend:

1. Autenticação e acesso: 12 funções.
2. Dashboard e tempo real: 9 funções.
3. Configurações e preferências: 17 funções.
4. Idioma e i18n: 15 funções.
5. Datas e tempo: 43 funções.
6. Projetos e filtros: 5 funções.
7. Solicitações: 23 funções.
8. Atribuições e rotas: 9 funções.
9. Veículos: 35 funções.
10. Layout e renderização: 8 funções.
11. Infraestrutura compartilhada: 16 funções.

Funções-orquestradoras mais relevantes para entendimento do frontend atual:

- `createTransportPageController`: concentra o estado principal da página.
- `initTransportPage`: faz o bootstrap do dashboard quando o DOM fica pronto.
- `loadDashboard`: puxa o payload central do backend e atualiza o estado local.
- `renderDashboard`: dispara a reconstrução visual da tela com base no estado carregado.
- `startRealtimeUpdates` e `stopRealtimeUpdates`: gerenciam o ciclo do SSE.
- `verifyTransportCredentials`: controla autenticação baseada em sessão.
- `saveTransportSettings` e `saveRouteTimeForSelectedDate`: persistem configuração global e configuração por data.
- `submitAssignment`, `rejectRequestRow` e `returnRequestRowToPending`: operam o ciclo de decisão sobre solicitações.
- `removeVehicleFromRoute` e `openVehicleModal`: operam o ciclo principal de gestão visual de veículos.
- `renderRequestTables`, `renderVehiclePanels` e `renderProjectList`: concentram a materialização visual do estado carregado.

Conclusão desta seção: no frontend, a responsabilidade por função já está documentada em profundidade. O principal achado da fase 1.1 não é falta de informação, mas excesso de concentração em um arquivo único, o `app.js`.

### Arquivo: `sistema/app/static/transport/i18n.js`

Responsabilidade atual: armazenar os dicionários de idioma e expor funções utilitárias de leitura, como `getDictionary` e `getLanguage`.

Papel no módulo atual: servir como repositório relativamente isolado de internacionalização, reutilizado pelo `app.js`.

## 7. Artefatos documentais já disponíveis e como se encaixam na fase 1.1

### Arquivo: `docs/descritivo_transport.md`

Papel atual: oferecer a visão funcional do dashboard, sua arquitetura, os endpoints efetivamente usados e a forma como a interface conversa com a API.

Valor para a fase 1.1: serve como referência narrativa e arquitetural de alto nível.

### Arquivo: `docs/catalogo_acoes_transport.yaml`

Papel atual: oferecer uma superfície declarativa de ações operacionais, menos dependente dos detalhes internos da UI.

Valor para a fase 1.1: ajuda a separar, conceitualmente, ações de negócio do espelhamento literal do frontend, o que já prepara o raciocínio para as fases futuras.

## 8. Hotspots de acoplamento identificados já no início da fase 1.1

Os pontos abaixo já aparecem como focos prioritários de reorganização estrutural:

- `build_transport_dashboard`: concentra leitura agregada demais em um único fluxo.
- `create_transport_vehicle_registration`: mistura cadastro-base do veículo com agenda operacional.
- `delete_transport_vehicle_registration`: revela remoção destrutiva com dependências amplas.
- `upsert_transport_assignment_with_persistence`: mistura comando do dia com persistência recorrente.
- `app.js`: concentra estado, integração com API, renderização e grande parte da lógica operacional da UI em um único arquivo.
- Ausência de contrato explícito de atualização de veículo: o backend ainda opera com criação e remoção, mas não com edição formal do cadastro já existente.
- Dependência de chaves mutáveis no modelo: workplace textual e placa ainda aparecem como eixo relacional em pontos críticos.

## 8.1 Matriz explícita de acoplamentos críticos

Para aprofundar a fase 1.1, a tabela abaixo transforma os hotspots identificados em uma matriz objetiva de acoplamento. O propósito desta matriz é deixar claro o que está acoplado, por que isso é um problema, qual o risco de manter esse acoplamento e em que ordem vale a pena atacar cada extração.

Convenção de prioridade:

- `P0`: extração estrutural imediata, necessária para reduzir risco sistêmico e abrir caminho para as próximas fases.
- `P1`: extração importante, mas dependente da estabilização inicial dos hotspots mais centrais.
- `P2`: extração recomendada para consolidação, legibilidade e desacoplamento de consumidores, após os limites principais do domínio estarem mais claros.

| ID | Acoplamento crítico | Pontos envolvidos | Sintoma atual | Risco principal | Extração recomendada | Prioridade |
| --- | --- | --- | --- | --- | --- | --- |
| AC-01 | Leitura agregada do dashboard acoplada a múltiplos subdomínios | `build_transport_dashboard`, `_build_vehicle_rows_for_dashboard`, `_build_transport_vehicle_registry_rows`, `_build_recurring_assignment_template_index`, `_list_transport_assignments_for_requests`, `list_workplaces` | Um único fluxo conhece pedidos, alocações, agendas, veículos, projetos, workplaces e regras temporais ao mesmo tempo | Qualquer ajuste de leitura do dashboard tende a tocar regras de disponibilidade, recorrência e composição operacional em cascata | Extrair uma camada de consulta dedicada ao dashboard, com consultas auxiliares separadas para requests, veículos, agendas e alocações | `P0` |
| AC-02 | Cadastro-base do veículo acoplado ao ciclo de vida da agenda operacional | `create_transport_vehicle_registration`, `_build_schedule_specs_from_payload`, `_classify_vehicle_schedules_for_reuse`, `_vehicle_has_active_schedule_for_spec`, `Vehicle`, `TransportVehicleSchedule` | Cadastrar ou reutilizar veículo já implica criar, reaproveitar, desativar ou bloquear agendas no mesmo fluxo | Impede evolução segura para edição completa de veículo e torna efeitos colaterais difíceis de prever | Separar serviço de cadastro-base de veículo do serviço de criação e manutenção de agendas | `P0` |
| AC-03 | Remoção de veículo acoplada a limpeza destrutiva de dependências | `delete_transport_vehicle_registration`, `_purge_foreign_key_dependencies`, `TransportAssignment`, `TransportVehicleScheduleException`, `TransportVehicleSchedule` | A remoção opera com cascata ampla a partir de `schedule_id`, apagando vínculos relacionais e operacionais | Alto risco de perda de contexto, comportamento destrutivo excessivo e dificuldade para futuras políticas de desativação lógica | Separar remoção de agenda, desativação operacional e eventual aposentadoria do cadastro do veículo | `P0` |
| AC-04 | Comando do dia acoplado à persistência recorrente de alocações | `upsert_transport_assignment_with_persistence`, `_propagate_confirmed_recurring_assignment`, `_materialize_recurring_assignments_for_date`, `_reset_transport_request_assignments_to_pending` | Uma decisão operacional aparentemente pontual altera estado futuro e recorrente no mesmo fluxo | Regressões difíceis de detectar e incapacidade de introduzir proposta, aprovação ou simulação antes da aplicação | Extrair um serviço de comando do dia e um serviço separado de propagação recorrente, com fronteira explícita entre ambos | `P0` |
| AC-05 | Estado administrativo e estado web do usuário acoplados no mesmo serviço de domínio | `build_transport_dashboard`, `build_web_transport_state`, `_build_web_transport_request_items`, regras temporais compartilhadas | Consumidores diferentes dependem do mesmo arquivo monolítico para compor estados com objetivos distintos | Evolução de um consumidor pode distorcer o outro, especialmente em regras de visibilidade e materialização temporal | Separar consultas por consumidor: leitura administrativa, leitura web e, no futuro, leitura para propostas | `P1` |
| AC-06 | Integridade relacional acoplada a chaves de negócio mutáveis | `User.workplace -> Workplace.workplace`, `User.placa -> Vehicle.placa`, modelos em `models.py` | Campos que deveriam ser editáveis continuam funcionando como eixo de integridade entre entidades | Alterar placa ou workplace amplia risco de inconsistência e bloqueia contratos seguros de atualização | Planejar migração para identificadores estáveis e manter os campos de negócio apenas como atributos editáveis | `P1` |
| AC-07 | Contrato HTTP de veículo acoplado ao fluxo destrutivo atual da UI | `create_transport_vehicle`, `delete_transport_vehicle_for_route`, `TransportVehicleCreate`, ausência de `TransportVehicleUpdate` | A API suporta criação e remoção, mas não atualização explícita de veículo | O frontend e futuros consumidores ficam presos a recriação e remoção como mecanismo de mudança cadastral | Introduzir contratos separados para update de veículo e update de agenda, preservando semântica própria | `P1` |
| AC-08 | Frontend monolítico acoplado a autenticação, estado, renderização e comandos | `app.js`, `createTransportPageController`, `loadDashboard`, `renderDashboard`, `submitAssignment`, `removeVehicleFromRoute`, `openVehicleModal` | Um único arquivo concentra estado local, chamadas HTTP, SSE, modais, renderização e operação do dashboard | Alto custo de manutenção da UI e dificuldade para alinhar o frontend a futuras fronteiras mais limpas do backend | Extrair cliente de API, store de estado, renderização e comandos visuais em módulos distintos, depois da estabilização do backend | `P2` |

## 8.2 Prioridade de extração recomendada

Além da classificação por `P0`, `P1` e `P2`, a fase 1.1 fica mais útil quando a ordem sugerida de extração também é explícita. A sequência abaixo considera dependência técnica entre os hotspots, risco de regressão e necessidade de abrir caminho para a edição completa de veículo e para a futura camada de propostas.

### Ordem 1. Extrair a leitura agregada do dashboard

Motivo: `build_transport_dashboard` é hoje a principal superfície de leitura do módulo e também a melhor porta de entrada para isolar responsabilidades sem alterar comportamento. Separar essa leitura primeiro reduz o risco de que futuras mudanças em veículo, agenda ou alocação continuem viciadas pelo mesmo agregador monolítico.

Resultado esperado: uma camada de consulta dedicada ao dashboard, com subconsultas ou montadores especializados por tipo de dado.

### Ordem 2. Separar cadastro-base de veículo da agenda operacional

Motivo: este é o acoplamento que mais diretamente bloqueia o requisito de editar um veículo sem exclusão e recriação. Enquanto criação de veículo e gestão de agenda permanecerem no mesmo fluxo, o sistema continuará confundindo mudança cadastral com alteração operacional.

Resultado esperado: fronteiras claras entre serviço de veículo e serviço de agenda, com regras independentes e efeitos colaterais controlados.

### Ordem 3. Separar remoção destrutiva de desativação operacional

Motivo: não faz sentido introduzir edição e contratos mais ricos de veículo se a remoção continuar sendo um fluxo cascata baseado em `schedule_id`. Esta etapa reduz risco estrutural e prepara o terreno para políticas mais seguras de desativação, arquivamento ou exclusão controlada.

Resultado esperado: remoção mais explícita, com semântica distinta para agenda, cadastro-base e dependências operacionais.

### Ordem 4. Desacoplar comando do dia da persistência recorrente

Motivo: o futuro fluxo de proposta e aprovação depende de conseguir representar uma decisão do dia sem, automaticamente, contaminar a recorrência. Separar essa fronteira cedo evita que a automação futura fique presa ao mesmo efeito colateral atual.

Resultado esperado: um serviço para operação pontual do dia e outro para propagação recorrente, com decisão explícita de quando um deve chamar o outro.

### Ordem 5. Separar leituras por consumidor e consolidar contratos de update

Motivo: com os limites centrais do backend mais claros, passa a fazer sentido separar leitura administrativa, leitura web e, futuramente, leitura para proposta. Nesse mesmo estágio, também vale introduzir os contratos formais de atualização de veículo e agenda, porque o domínio já estará menos misturado.

Resultado esperado: superfícies mais nítidas para cada consumidor do domínio e contratos HTTP alinhados à semântica real do negócio.

### Ordem 6. Migrar dependências de chaves mutáveis para identificadores estáveis

Motivo: esta etapa é estrutural e importante, mas tende a ficar mais segura depois que as fronteiras do backend já estiverem menos ambíguas. Fazer essa migração cedo demais, sem antes separar responsabilidades, aumentaria o custo de retrabalho.

Resultado esperado: integridade relacional mais robusta, suporte seguro à edição de placa e workplace e base melhor para automação futura.

### Ordem 7. Modularizar o frontend de transporte em torno das novas fronteiras

Motivo: o `app.js` está, de fato, muito concentrado, mas o melhor desacoplamento do frontend depende de o backend já ter contratos internos e HTTP mais claros. Modularizar a interface antes disso reduziria legibilidade local, sem resolver a fonte principal do acoplamento.

Resultado esperado: UI mais sustentável, alinhada a um backend com leitura, comandos e contratos mais explícitos.

## 8.3 Leitura prática da matriz

O que a matriz mostra, em termos práticos, é que a reorganização não deve começar pelo frontend nem pela modelagem relacional isoladamente. O maior retorno inicial está em extrair os acoplamentos centrais do backend que hoje misturam leitura agregada, veículo, agenda, alocação e recorrência. Esses são os pontos que sustentam a maior parte dos comportamentos difíceis de evoluir.

Também fica explícito que a edição completa de veículo não depende apenas de adicionar um endpoint novo. Ela depende de três extrações anteriores ou correlatas: separar o cadastro-base da agenda, reduzir a destrutividade do fluxo de remoção e parar de usar chaves de negócio mutáveis como eixo de integridade. Sem esse trio, o contrato de atualização corre o risco de virar apenas uma fachada em cima de um fluxo ainda acoplado.

## 9. Resultado desta implementação inicial da fase 1.1

Com este inventário, a fase 1.1 passa a ter uma linha de base concreta. O módulo de transporte já está mapeado em suas superfícies principais, seus arquivos centrais foram classificados por responsabilidade, os hotspots de acoplamento mais importantes ficaram explícitos e a ordem recomendada de extração já está priorizada.

Isso permite que a próxima etapa da reorganização deixe de partir de hipóteses genéricas e passe a se apoiar em um mapa técnico verificável do estado atual do módulo.