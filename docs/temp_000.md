# Plano completo para implementar o agente de IA de roteirizacao do Transport

## 1. Objetivo deste documento

Este documento define um plano minucioso para implementar, no backend Python existente, um agente de IA com LangChain capaz de reorganizar veiculos, tipos de veiculo e alocacao de passageiros no dashboard `Transport`, usando tempo real de rota por API externa, respeitando janelas de horario e minimizando custo de transporte.

O plano foi escrito depois de estudar:

1. O website `transport` em `sistema/app/static/transport`.
2. O estado atual do backend de transporte em `sistema/app/routers/transport.py`, `sistema/app/schemas.py`, `sistema/app/models.py` e services relacionados.
3. O documento `docs/temp_002.md`, que registra a reorganizacao ja feita para preparar o backend para automacao por agente.
4. O estado real observado no codigo atual, incluindo as mudancas posteriores ja presentes no repo: suporte a veiculos parcialmente cadastrados, precos padrao por tipo, moeda/unidade de preco e placeholders `Waiting`.

O objetivo nao e implementar neste documento. O objetivo e deixar um roteiro completo, robusto e executavel para a proxima etapa de desenvolvimento.

## 2. Decisoes principais

### 2.1 O agente vai rodar no backend Python, junto com a API

O agente deve viver dentro da aplicacao FastAPI existente, no mesmo deploy da API na Digital Ocean. O frontend `transport` nunca deve chamar OpenAI, Mapbox ou qualquer provider externo diretamente.

Motivos:

1. As chaves de API precisam ficar no servidor.
2. O agente precisa operar sobre contratos de dominio, nao sobre DOM.
3. O backend ja possui contratos importantes: snapshot operacional, proposal, validacao, aprovacao e aplicacao.
4. O backend ja centraliza sessao, auditoria, events e notificacoes de refresh.

### 2.2 A chave OpenAI nao deve ser gravada no repositorio

A chave informada na conversa deve ser tratada como segredo vazado. Ela nao deve entrar em `docs/temp_000.md`, `.env.example`, codigo, migration, teste, fixture ou log.

Acao obrigatoria antes de producao:

1. Rotacionar a chave exposta.
2. Configurar `OPENAI_API_KEY` apenas como variavel de ambiente no servidor Digital Ocean.
3. Usar `.env.example` com placeholder, nunca com valor real.
4. Garantir que logs do agente nao imprimam headers, request body completo de OpenAI nem variaveis de ambiente.

### 2.3 Modelo OpenAI

Usar o modelo solicitado pelo administrador como configuracao de ambiente:

```env
OPENAI_MODEL=gpt-5-2025-08-07
```

Temperatura:

1. Configurar o menor valor suportado pelo wrapper usado.
2. Para `ChatOpenAI`, usar `temperature=0` quando aceito.
3. Se o modelo/endpoint recusar `temperature`, omitir o parametro e compensar com structured output, validacao deterministica e prompt fechado.

O resultado do agente nao deve depender apenas de texto livre do modelo. A resposta precisa ser validada por schemas Pydantic e por validadores deterministicos antes de qualquer salvamento/aplicacao.

### 2.4 API de mapas escolhida

Escolha recomendada: Mapbox.

Uso planejado:

1. Mapbox Geocoding/Search para transformar endereco + ZIP + pais em coordenadas.
2. Mapbox Matrix API para obter tempos e distancias entre pares de pontos.
3. Mapbox Directions API para reconstruir a geometria e os detalhes finais das rotas aprovadas, quando necessario para exibicao ou auditoria.

Motivos:

1. A Matrix API foi desenhada para retornar duracoes/distancias entre muitos pontos, que e exatamente a base do solver.
2. A Directions API retorna rotas finais, geometria e detalhes de percurso.
3. O limite documentado da Matrix API exige chunking, o que e simples de controlar no backend.
4. A integracao pode ficar toda server-side, sem expor token no navegador.

Configuracoes:

```env
MAPBOX_ACCESS_TOKEN=...
MAPBOX_MATRIX_PROFILE=mapbox/driving-traffic
MAPBOX_DIRECTIONS_PROFILE=mapbox/driving-traffic
MAPBOX_GEOCODING_PERMANENT=false
```

Observacao: se `mapbox/driving-traffic` nao estiver disponivel para a conta, usar fallback configuravel para `mapbox/driving`.

### 2.5 O agente nao deve ser o otimizador matematico principal

O LangChain deve orquestrar o fluxo, gerar justificativas e produzir uma resposta estruturada. A otimizacao de custo/capacidade/tempo deve ser feita por algoritmo deterministico em Python.

Recomendacao:

1. Usar OR-Tools para VRP/CVRP/VRPTW quando o volume de passageiros justificar.
2. Manter fallback heuristico proprio para casos pequenos ou quando OR-Tools nao encontrar solucao rapidamente.
3. O LLM nao deve "inventar" tempos de deslocamento, coordenadas, custos, veiculos ou capacidades.
4. O LLM so pode escolher entre dados e resultados fornecidos por tools deterministicas.

## 3. Estado atual confirmado no codigo

### 3.1 Frontend `transport`

Arquivos estudados:

1. `sistema/app/static/transport/index.html`
2. `sistema/app/static/transport/app.js`
3. `sistema/app/static/transport/i18n.js`
4. `sistema/app/static/transport/styles.css`
5. `sistema/app/static/transport/functions/functions.md`
6. `sistema/app/static/transport/functions/functions_by_capability.md`

O dashboard ja possui:

1. Menu `IA` na topbar.
2. Opcao `Calcular rotas`.
3. Opcao `Implementar Modifications`.
4. Modal `Ajustes para o Agente de IA`.
5. Inputs:
   - `data-ai-agent-earliest-boarding`
   - `data-ai-agent-arrival-at-work`
6. Dicionario i18n com chaves `ai.*` para varios idiomas.
7. Modal `Dashboard Settings` com:
   - assentos padrao por tipo;
   - preco padrao por tipo;
   - moeda;
   - unidade de cobranca.

Gaps no frontend:

1. O modal `Ajustes para o Agente de IA` ainda nao tem `Cancelar` e `Solicitar Rotas`.
2. Os inputs do modal ainda nao sao preenchidos automaticamente com `06:50` e `07:45`.
3. A opcao `Implementar Modifications` apenas fecha o menu; ainda nao busca sugestao salva.
4. Nao existe janela `Alteracoes`.
5. Nao existe UI de progresso do agente.
6. Nao existe renderizacao de diff de frota/rotas/custo.
7. Nao existe client-side call para endpoint de agente.

### 3.2 Backend de transporte

O backend ja possui uma base excelente para automacao, conforme `docs/temp_002.md`:

1. `GET /api/transport/operational-snapshot`
2. `POST /api/transport/proposals/build`
3. `POST /api/transport/proposals/validate`
4. `POST /api/transport/proposals/approve`
5. `POST /api/transport/proposals/reject`
6. `POST /api/transport/proposals/apply`
7. `POST /api/transport/exports/operational-plan`
8. `GET /api/transport/reevaluation-events`
9. Auditoria estruturada em `TransportProposalAuditEntry`.
10. Revalidacao server-side antes de aprovar/aplicar proposal.

Gaps no backend para esta demanda:

1. A proposal atual cobre assignments, mas nao cobre alteracoes de frota.
2. `TransportProposalDecision` referencia `vehicle_id` existente; ele nao consegue apontar para um veiculo que sera criado no momento do apply.
3. As proposals existem como payload transitado pela API, mas ainda nao ha persistencia historica de sugestoes salvas pelo agente.
4. Nao ha tabela de `agent_run`, baseline salvo, snapshot anterior ou restore do estado original.
5. Nao ha geocoding, matrix cache, route cache ou provider de mapas.
6. Nao ha schema de itinerario por veiculo com passageiros, ordem de embarque, horarios previstos e custo.
7. Nao ha endpoint unico para `Solicitar Rotas`.
8. Nao ha endpoint para `Implementar Modificacoes`.

### 3.3 Cadastro de Projetos e enderecos

O projeto ja tem `Project` com:

1. `name`
2. `country_code`
3. `country_name`
4. `timezone_name`
5. `address`
6. `zip_code`

O `TransportRequestRow` ja carrega dados do passageiro:

1. `user_id`
2. `nome`
3. `projeto`
4. `workplace`
5. `end_rua`
6. `zip`

O agente deve cruzar:

1. Passageiro -> `projeto`
2. `projeto` -> pais, endereco do trabalho, ZIP do trabalho e timezone
3. Passageiro -> `end_rua` + `zip`
4. Pais do passageiro = pais do projeto do passageiro, conforme requisito

### 3.4 Settings de preco e assentos

O contrato `/api/transport/settings` ja possui:

1. `default_car_seats`
2. `default_minivan_seats`
3. `default_van_seats`
4. `default_bus_seats`
5. `default_car_price`
6. `default_minivan_price`
7. `default_van_price`
8. `default_bus_price`
9. `price_currency_code`
10. `price_rate_unit`

O agente deve usar esses campos como fonte de verdade para:

1. Capacidade padrao de veiculos novos.
2. Capacidade sugerida quando alterar tipo de um veiculo.
3. Custo por veiculo utilizado.
4. Resumo financeiro da sugestao.

Para veiculos existentes, a capacidade real deve vir de `vehicle.lugares` quando preenchida. Os assentos padrao so devem ser usados para veiculos criados ou para edicoes de tipo sugeridas pelo agente.

## 4. Premissas funcionais

### 4.1 Escopo inicial da roteirizacao

Assumir que a primeira entrega do agente roteiriza o trajeto `home_to_work`.

Justificativa:

1. O requisito fala em horario de embarque mais cedo.
2. O requisito fala em horario de chegada no local de trabalho.
3. O requisito diz que todos os veiculos devem chegar ao local de trabalho.

O design deve manter `route_kind` no contrato para evoluir depois para `work_to_home`, mas o botao `IA > Calcular Rotas` deve iniciar com `route_kind="home_to_work"`.

### 4.2 Data de servico

Usar a data selecionada no dashboard como `service_date`.

O agente deve considerar apenas requests que se aplicam a essa data, respeitando as regras existentes de:

1. `extra`
2. `weekend`
3. `regular`

### 4.3 Tipos de lista

Os passageiros devem ser alocados em veiculos do mesmo tipo de solicitacao:

1. Passageiros `EXTRA` em veiculos da `EXTRA TRANSPORT LIST`.
2. Passageiros `WEEKEND` em veiculos da `WEEKEND TRANSPORT LIST`.
3. Passageiros `REGULAR` em veiculos da `REGULAR TRANSPORT LIST`.

Nao misturar passageiros entre listas, mesmo que isso reduza custo, salvo se uma regra futura permitir explicitamente.

### 4.4 Projetos e paises

O pais do passageiro deve ser derivado do projeto em que ele esta alocado.

Regra:

1. Se o passageiro esta no projeto `P80`, usar o pais de `P80`.
2. Se esta em `P82`, usar o pais de `P82`.
3. Se esta em `P83`, usar o pais de `P83`.
4. Se o projeto nao tiver pais/endereco/ZIP suficientes, bloquear a roteirizacao para aquele passageiro e exibir issue clara.

### 4.5 Destinos

O destino de trabalho deve ser obtido da tabela `projects`.

Regra recomendada:

1. Criar particoes por `request_kind + project`.
2. Nao colocar no mesmo veiculo passageiros de projetos com destino diferente, salvo quando os destinos geocodificados forem o mesmo ponto operacional ou estiverem explicitamente marcados como agrupaveis.
3. Nunca misturar passageiros de paises diferentes no mesmo problema de roteirizacao.

### 4.6 Horarios

Valores padrao do modal:

1. Horario de embarque mais cedo: `06:50`
2. Horario de chegada no local de trabalho: `07:45`

Regras:

1. Todos os veiculos da proposta devem chegar ao destino ate `07:45`.
2. O primeiro embarque de cada veiculo nao pode ser antes de `06:50`.
3. A tolerancia de atraso deve ser completamente ignorada pelo agente.
4. `requested_time` dos requests deve ser carregado para auditoria, mas nao deve virar hard constraint nesta primeira entrega, porque o requisito define somente embarque minimo e chegada ao trabalho.
5. O horario de cada parada deve ser calculado de tras para frente, partindo do horario de chegada.

### 4.7 Minimizacao de custo

Objetivo primario:

1. Minimizar o custo total dos veiculos usados.

Objetivos secundarios, em ordem:

1. Minimizar numero de veiculos.
2. Minimizar duracao total de deslocamento.
3. Minimizar distancia total.
4. Minimizar quantidade de mudancas destrutivas em relacao ao dashboard atual.
5. Maximizar folga de tempo entre primeiro embarque e horario minimo.
6. Preservar veiculos existentes quando custo e eficiencia empatarem.

### 4.8 Precos ausentes

Se qualquer preco padrao necessario estiver ausente, o agente nao deve inventar custo.

Regra de preflight:

1. Se todos os precos estiverem ausentes, bloquear `Solicitar Rotas`.
2. Se um tipo nao tiver preco, esse tipo nao deve ser considerado como candidato, a menos que ja exista veiculo daquele tipo e o administrador confirme no futuro.
3. A janela deve mostrar erro claro: "Defina o preco padrao dos tipos de veiculo em Dashboard Settings antes de solicitar rotas por IA."

## 5. Arquitetura proposta

### 5.1 Novos modulos Python

Criar os seguintes modulos:

1. `sistema/app/services/transport_ai_agent.py`
   - Orquestracao LangChain.
   - Prompt.
   - Tools.
   - Execucao do agente.
   - Conversao de structured response para plano interno.

2. `sistema/app/services/transport_ai_planning.py`
   - Montagem do input canonico de planejamento.
   - Validacoes preflight.
   - Particionamento por lista/projeto/pais.
   - Normalizacao de custos e capacidades.

3. `sistema/app/services/transport_route_provider.py`
   - Cliente Mapbox.
   - Geocoding.
   - Matrix.
   - Directions final.
   - Retentativas, timeouts e rate-limit local.

4. `sistema/app/services/transport_route_cache.py`
   - Cache de geocoding.
   - Cache de matriz.
   - Hash de enderecos e coordenadas.
   - Politica de expiracao.

5. `sistema/app/services/transport_route_optimizer.py`
   - OR-Tools ou fallback heuristico.
   - Geracao de combinacoes de frota.
   - Validacao de capacidade e janela de horario.
   - Calculo de custo.

6. `sistema/app/services/transport_ai_runs.py`
   - Persistencia de execucoes.
   - Baseline antes da IA.
   - Restore/cancelamento.
   - Salvamento de sugestoes.
   - Busca da ultima sugestao salva.

7. `sistema/app/routers/transport_ai.py`
   - Endpoints dedicados a IA.
   - Separado de `transport.py` para nao aumentar ainda mais o router atual.

### 5.2 Dependencias novas

Adicionar em `requirements.txt`:

```txt
langchain
langchain-openai
ortools
httpx
```

Notas:

1. `httpx` deve ser usado para Mapbox com timeout controlado.
2. Se `ortools` aumentar demais a imagem Docker, avaliar fase intermediaria com heuristica propria e adicionar OR-Tools depois.
3. Versionar dependencias fixando versoes apos testar localmente.

### 5.3 Configuracoes novas

Adicionar em `sistema/app/core/config.py`:

```python
openai_api_key: str | None = None
openai_model: str = "gpt-5-2025-08-07"
openai_temperature: float | None = 0
openai_timeout_seconds: int = 120
openai_max_retries: int = 2

mapbox_access_token: str | None = None
mapbox_matrix_profile: str = "mapbox/driving-traffic"
mapbox_directions_profile: str = "mapbox/driving-traffic"
mapbox_timeout_seconds: int = 20
mapbox_max_retries: int = 2
mapbox_geocoding_permanent: bool = False

transport_ai_enabled: bool = False
transport_ai_max_passengers_per_run: int = 80
transport_ai_max_runtime_seconds: int = 180
transport_ai_route_cache_ttl_seconds: int = 3600
transport_ai_geocode_cache_ttl_days: int = 30
```

No servidor:

```env
TRANSPORT_AI_ENABLED=true
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5-2025-08-07
MAPBOX_ACCESS_TOKEN=...
```

## 6. Modelo de dados novo

### 6.1 Tabela `transport_ai_runs`

Finalidade: registrar cada clique em `Solicitar Rotas`.

Campos recomendados:

1. `id`
2. `run_key` unico, string
3. `service_date`
4. `route_kind`
5. `status`
   - `requested`
   - `baseline_saved`
   - `passengers_reset`
   - `running`
   - `proposed`
   - `saved`
   - `applied`
   - `cancelled`
   - `failed`
6. `actor_user_id`
7. `earliest_boarding_time`
8. `arrival_at_work_time`
9. `openai_model`
10. `route_provider`
11. `price_currency_code`
12. `price_rate_unit`
13. `baseline_snapshot_json`
14. `baseline_assignments_json`
15. `baseline_vehicle_state_json`
16. `planning_input_json`
17. `planning_input_hash`
18. `preflight_issues_json`
19. `error_code`
20. `error_message`
21. `created_at`
22. `updated_at`
23. `completed_at`

Observacoes:

1. `baseline_assignments_json` deve guardar assignments existentes antes de resetar passageiros para pending.
2. `baseline_vehicle_state_json` deve guardar veiculos, schedules e dados base que poderiam ser alterados pelo apply.
3. O baseline deve ser suficiente para restaurar o dashboard se o admin cancelar a janela `Alteracoes`.

### 6.2 Tabela `transport_ai_suggestions`

Finalidade: salvar a sugestao gerada pelo agente, independentemente de aplicar.

Campos recomendados:

1. `id`
2. `suggestion_key` unico
3. `run_id`
4. `proposal_key`
5. `status`
   - `draft`
   - `shown`
   - `saved`
   - `discarded`
   - `applied`
   - `expired`
6. `agent_plan_json`
7. `transport_proposal_json`
8. `vehicle_actions_json`
9. `assignment_actions_json`
10. `route_itineraries_json`
11. `change_summary_json`
12. `cost_summary_json`
13. `validation_issues_json`
14. `raw_model_response_json`
15. `prompt_version`
16. `created_at`
17. `updated_at`
18. `saved_at`
19. `applied_at`
20. `discarded_at`

### 6.3 Tabela `transport_ai_route_points`

Finalidade: registrar enderecos normalizados e coordenadas usadas pela IA.

Campos recomendados:

1. `id`
2. `point_key`
3. `point_type`
   - `passenger_origin`
   - `project_destination`
4. `source_id`
   - `user_id` para passageiro
   - `project_id` para destino
5. `address`
6. `zip_code`
7. `country_code`
8. `country_name`
9. `normalized_query`
10. `longitude`
11. `latitude`
12. `provider`
13. `provider_place_id`
14. `confidence`
15. `raw_response_json`
16. `created_at`
17. `updated_at`
18. `expires_at`

Politica de cache:

1. Se `MAPBOX_GEOCODING_PERMANENT=false`, nao persistir resposta bruta nem cache duradouro sem revisar os termos do plano contratado.
2. Persistir apenas coordenadas confirmadas operacionalmente ou cache temporario permitido.
3. Se for contratada permissao de geocoding permanente, permitir cache persistente com origem/auditoria.

### 6.4 Tabela `transport_ai_route_matrices`

Finalidade: evitar chamadas repetidas a Matrix API durante uma mesma janela operacional.

Campos recomendados:

1. `id`
2. `matrix_key`
3. `provider`
4. `profile`
5. `depart_at`
6. `coordinate_hash`
7. `sources_json`
8. `destinations_json`
9. `durations_json`
10. `distances_json`
11. `created_at`
12. `expires_at`

### 6.5 Tabela `transport_ai_applied_route_stops`

Finalidade: depois de aplicar, permitir que o dashboard mostre a rota calculada e os horarios de embarque.

Campos recomendados:

1. `id`
2. `suggestion_id`
3. `service_date`
4. `route_kind`
5. `vehicle_id`
6. `vehicle_client_key`
7. `stop_order`
8. `stop_type`
   - `pickup`
   - `destination`
9. `request_id`
10. `user_id`
11. `project_name`
12. `address`
13. `zip_code`
14. `country_code`
15. `longitude`
16. `latitude`
17. `scheduled_time`
18. `duration_from_previous_seconds`
19. `distance_from_previous_meters`
20. `created_at`

## 7. Novos schemas Pydantic

### 7.1 Request de calculo

Criar `TransportAgentRouteRequest`:

```python
class TransportAgentRouteRequest(BaseModel):
    service_date: date
    route_kind: Literal["home_to_work"] = "home_to_work"
    earliest_boarding_time: str
    arrival_at_work_time: str
```

Validacoes:

1. Horarios `HH:MM`.
2. `earliest_boarding_time < arrival_at_work_time`.
3. `route_kind == "home_to_work"` na primeira entrega.

### 7.2 Resposta de start

Criar `TransportAgentRunStartResponse`:

```python
class TransportAgentRunStartResponse(BaseModel):
    ok: bool
    run_key: str
    status: str
    message: str
```

### 7.3 Sugestao de veiculo

Criar `TransportAgentVehicleAction`:

```python
class TransportAgentVehicleAction(BaseModel):
    action_key: str
    action_type: Literal["keep", "create", "update", "remove_from_day"]
    service_scope: Literal["extra", "weekend", "regular"]
    vehicle_id: int | None = None
    schedule_id: int | None = None
    client_vehicle_key: str
    before: dict[str, object] | None = None
    after: dict[str, object]
    rationale: str
    cost_delta: float | None = None
```

Notas:

1. `create` usa `client_vehicle_key` ate virar `vehicle_id` real no apply.
2. `remove_from_day` deve ser preferido a delete destrutivo para `regular` e `weekend`.
3. Para `extra`, pode desativar/remover schedule single-date com seguranca.

### 7.4 Alocacao planejada

Criar `TransportAgentPassengerAllocation`:

```python
class TransportAgentPassengerAllocation(BaseModel):
    request_id: int
    request_kind: Literal["extra", "weekend", "regular"]
    service_date: date
    route_kind: Literal["home_to_work"]
    vehicle_ref: str
    pickup_order: int
    scheduled_pickup_time: str
    projected_arrival_time: str
    rationale: str
```

`vehicle_ref` pode ser:

1. `existing:{vehicle_id}`
2. `new:{client_vehicle_key}`

### 7.5 Itinerario

Criar `TransportAgentRouteStop`:

```python
class TransportAgentRouteStop(BaseModel):
    stop_order: int
    stop_type: Literal["pickup", "destination"]
    request_id: int | None = None
    user_id: int | None = None
    passenger_name: str | None = None
    project_name: str
    address: str
    zip_code: str
    country_code: str
    longitude: float
    latitude: float
    scheduled_time: str
    duration_from_previous_seconds: int | None = None
    distance_from_previous_meters: int | None = None
```

### 7.6 Plano completo do agente

Criar `TransportAgentPlan`:

```python
class TransportAgentPlan(BaseModel):
    plan_key: str
    service_date: date
    route_kind: Literal["home_to_work"]
    earliest_boarding_time: str
    arrival_at_work_time: str
    objective_summary: str
    vehicle_actions: list[TransportAgentVehicleAction]
    passenger_allocations: list[TransportAgentPassengerAllocation]
    route_itineraries: list[TransportAgentVehicleItinerary]
    cost_summary: TransportAgentCostSummary
    change_summary: TransportAgentChangeSummary
    validation_issues: list[TransportProposalValidationIssue]
```

### 7.7 Janela `Alteracoes`

Criar response `TransportAgentSuggestionResponse` com:

1. `run`
2. `suggestion`
3. `plan`
4. `dashboard_baseline_summary`
5. `can_apply`
6. `can_save`
7. `can_cancel_restore`
8. `issues`

## 8. Endpoints novos

### 8.1 Solicitar rotas

Endpoint:

```http
POST /api/transport/ai/route-calculations
```

Responsabilidades:

1. Exigir sessao de transporte.
2. Validar `transport_ai_enabled`.
3. Validar horarios.
4. Criar `transport_ai_run`.
5. Capturar baseline completo.
6. Resetar passageiros aplicaveis para suas user lists.
7. Disparar job do agente.
8. Retornar `run_key`.

Importante:

1. O reset para pending deve ocorrer depois de salvar baseline.
2. Os veiculos nao devem ser removidos nesta etapa.
3. Se preflight basico falhar, nao resetar nada.
4. Se resetar e o job falhar, manter baseline disponivel para restauracao.

### 8.2 Consultar run

Endpoint:

```http
GET /api/transport/ai/route-calculations/{run_key}
```

Retorna:

1. Status.
2. Mensagem atual.
3. Issues.
4. Sugestao se ja estiver pronta.

### 8.3 Buscar ultima sugestao salva

Endpoint:

```http
GET /api/transport/ai/suggestions/latest?service_date=YYYY-MM-DD&route_kind=home_to_work
```

Usado por:

1. Menu `IA > Implementar Modifications`.
2. Reabertura da janela `Alteracoes`.

Regra:

1. Retornar a sugestao mais recente com status `saved` ou `shown` e ainda nao aplicada/descartada.
2. Se nao houver, retornar 404 com mensagem localizada no frontend.

### 8.4 Salvar sugestao

Endpoint:

```http
POST /api/transport/ai/suggestions/{suggestion_key}/save
```

Comportamento:

1. Marca sugestao como `saved`.
2. Nao altera veiculos.
3. Nao aplica assignments.
4. Mantem baseline e plan para aplicacao futura.
5. Emite evento de review para refresh leve.

### 8.5 Cancelar sugestao e restaurar baseline

Endpoint:

```http
POST /api/transport/ai/suggestions/{suggestion_key}/cancel
```

Comportamento:

1. Marca sugestao como `discarded`.
2. Restaura assignments do baseline.
3. Restaura qualquer alteracao feita pela fase de reset.
4. Nao remove veiculos existentes, porque eles nao foram removidos ainda.
5. Emite refresh do dashboard.

Observacao: como `Solicitar Rotas` ja devolve usuarios para user lists, o `Cancelar` da janela `Alteracoes` deve desfazer esse efeito e restaurar a situacao anterior ao clique em `Solicitar Rotas`.

### 8.6 Aplicar sugestao

Endpoint:

```http
POST /api/transport/ai/suggestions/{suggestion_key}/apply
```

Comportamento:

1. Recarrega sugestao do banco.
2. Revalida contra o estado atual.
3. Aplica acoes de veiculo em transacao.
4. Resolve `client_vehicle_key` para `vehicle_id`.
5. Converte alocacoes planejadas em `TransportProposalDecision`.
6. Chama fluxo existente de proposal:
   - build/validate/approve/apply ou funcao interna equivalente.
7. Persiste stops/itinerarios aplicados.
8. Marca sugestao e run como `applied`.
9. Emite eventos `transport_vehicle_supply_changed` e `transport_assignment_changed`.
10. Recarrega dashboard no frontend.

Se qualquer etapa falhar:

1. Fazer rollback da transacao.
2. Manter sugestao nao aplicada.
3. Registrar issue/audit.
4. Mostrar erro na janela `Alteracoes`.

## 9. Fluxo completo do usuario

### 9.1 Clique em `IA > Calcular Rotas`

Frontend:

1. Fechar menu `IA`.
2. Abrir modal `Ajustes para o Agente de IA`.
3. Preencher:
   - `06:50` em `Horário de embarque mais cedo`.
   - `07:45` em `Horário de chegada no local de trabalho`.
4. Rodape do modal:
   - `Cancelar`
   - `Solicitar Rotas`

Botao `Cancelar`:

1. Fecha o modal.
2. Nao chama API.
3. Nao altera dashboard.
4. Retorna foco para o botao `IA`.

Botao `Solicitar Rotas`:

1. Valida horarios localmente.
2. Desabilita botoes.
3. Mostra estado `Solicitando rotas...`.
4. Chama `POST /api/transport/ai/route-calculations`.
5. Comeca polling ou escuta SSE ate sugestao ficar pronta.

### 9.2 Depois de `Solicitar Rotas`

Backend:

1. Salva o estado atual.
2. Retorna todos os usuarios aplicaveis para suas user lists.
3. Mantem veiculos cadastrados visiveis.
4. Roda o agente em background.

Frontend:

1. Fecha ou troca o modal para estado de progresso.
2. Recarrega dashboard quando receber evento de reset.
3. Ao concluir, abre `Alteracoes`.

### 9.3 Janela `Alteracoes`

Criar novo modal/backdrop em `index.html`:

```html
<div class="transport-modal-backdrop" data-ai-changes-modal hidden>
  ...
</div>
```

Conteudo recomendado:

1. Cabecalho:
   - Titulo `Alterações`
   - Data
   - Rota
   - Horarios usados
   - Status da sugestao

2. Resumo executivo:
   - Custo atual estimado
   - Custo sugerido
   - Economia estimada
   - Veiculos atuais
   - Veiculos sugeridos
   - Passageiros alocados
   - Passageiros com issue

3. Aba `Veiculos`:
   - `Manter`
   - `Adicionar`
   - `Editar`
   - `Remover do dia`
   - Antes/depois de tipo, placa, assentos, custo e lista.

4. Aba `Passageiros`:
   - Passageiro
   - Projeto
   - Tipo da solicitacao
   - Veiculo sugerido
   - Ordem de embarque
   - Horario de embarque
   - Chegada prevista

5. Aba `Rotas`:
   - Um bloco por veiculo.
   - Sequencia de paradas.
   - Duracao total.
   - Distancia total.
   - Primeiro embarque.
   - Chegada ao trabalho.
   - Avisos de geocoding/rota.

6. Aba `Auditoria`:
   - Prompt version
   - Provider de mapa
   - Modelo usado
   - Data/hora da geracao
   - Issues de validacao
   - Hash do input

Rodape:

1. `Cancelar`
2. `Salvar`
3. `Aplicar`

Comportamentos:

1. `Cancelar`: descarta sugestao e restaura baseline.
2. `Salvar`: salva sugestao para uso futuro e fecha modal sem aplicar veiculos/assignments.
3. `Aplicar`: aplica sugestao e atualiza dashboard.

### 9.4 Clique em `IA > Implementar Modifications`

Frontend:

1. Chama `GET /api/transport/ai/suggestions/latest`.
2. Se existir sugestao salva, abre `Alteracoes`.
3. Se nao existir, mostra status: `Nenhuma sugestão de IA salva para esta data.`

## 10. Preparacao de dados para o agente

### 10.1 Snapshot operacional

Usar `build_transport_operational_snapshot` como base, mas criar uma camada enriquecida:

`TransportAgentPlanningInput`

Campos:

1. `service_date`
2. `route_kind`
3. `earliest_boarding_time`
4. `arrival_at_work_time`
5. `settings`
6. `projects_by_name`
7. `requests_by_scope`
8. `vehicles_by_scope`
9. `current_assignments`
10. `baseline_cost`
11. `route_points`
12. `constraints`

### 10.2 Passageiros elegiveis

Incluir apenas requests:

1. `status="active"`.
2. Aplicaveis a `service_date`.
3. `assignment_status` em estado `pending` apos reset.
4. Com `end_rua` e `zip` preenchidos.
5. Com projeto conhecido.
6. Com projeto contendo endereco/zip/pais.

Se faltar dado:

1. Nao inventar endereco.
2. Registrar issue bloqueante.
3. Mostrar passageiro na janela `Alteracoes` como `Nao roteado`.

### 10.3 Veiculos candidatos

Para cada lista (`extra`, `weekend`, `regular`):

1. Ler veiculos existentes no snapshot.
2. Separar veiculos prontos e pendentes.
3. Considerar acoes possiveis:
   - manter existente;
   - editar tipo/capacidade;
   - remover do dia;
   - criar novo.

Regras:

1. Veiculo existente usa `lugares` real se preenchido.
2. Veiculo novo usa assentos padrao do tipo.
3. Se o agente alterar o tipo de um veiculo existente, sugerir tambem a capacidade padrao daquele tipo, salvo se houver justificativa para manter capacidade manual.
4. Veiculo sem dados obrigatorios so pode ser usado se a proposta tambem preencher os dados faltantes.

### 10.4 Geocoding

Para cada passageiro:

Query canonica:

```text
{end_rua}, {zip}, {country_name}
```

Para cada destino de projeto:

```text
{project.address}, {project.zip_code}, {project.country_name}
```

Validacoes:

1. Coordenada deve estar no pais esperado quando o provider devolver pais.
2. Resultado com baixa confianca deve virar issue.
3. Enderecos duplicados devem reutilizar coordenada.
4. Coordenadas impossiveis ou sem rota devem bloquear o passageiro/projeto.

### 10.5 Matriz de tempos

Por particao de planejamento:

1. Montar lista de pontos:
   - origens dos passageiros;
   - destino do projeto.
2. Chamar Matrix API com chunking:
   - maximo 25 coordenadas para `driving`;
   - maximo 10 coordenadas para `driving-traffic`.
3. Pedir `duration,distance`.
4. Usar `depart_at` quando disponivel e permitido.
5. Se alguma celula retornar `null`, registrar issue e excluir combinacao inviavel.

## 11. Otimizacao

### 11.1 Particionamento

Rodar o solver separadamente por:

1. `request_kind`
2. `project`
3. `country_code`

Isso evita misturar listas, paises ou destinos diferentes de forma indevida.

### 11.2 Frota candidata

Para cada particao:

1. Criar pool de veiculos existentes da lista.
2. Criar veiculos virtuais por tipo:
   - carro
   - minivan
   - van
   - onibus
3. Definir custo de cada candidato:
   - preco padrao do tipo;
   - se existente, custo do tipo atual;
   - se editado, custo do tipo sugerido.
4. Definir capacidade:
   - existente: `lugares`;
   - novo/editado: default do tipo.

### 11.3 Restricoes duras

1. Capacidade do veiculo nao pode ser excedida.
2. Primeiro pickup >= `earliest_boarding_time`.
3. Chegada ao destino <= `arrival_at_work_time`.
4. Passageiros de listas diferentes nao se misturam.
5. Passageiros de paises diferentes nao se misturam.
6. Passageiros com destino de projeto diferente nao se misturam na primeira entrega.
7. Tolerancia de atraso nao entra no calculo.
8. Nenhuma coordenada ou tempo pode ser inventado.

### 11.4 Funcao objetivo

Pontuacao recomendada:

```text
score =
  total_vehicle_cost * 1_000_000
  + used_vehicle_count * 10_000
  + total_duration_seconds
  + total_distance_meters / 100
  + change_penalty
```

`change_penalty`:

1. Manter veiculo: 0
2. Criar veiculo: 50
3. Editar veiculo: 100
4. Remover veiculo existente do dia: 150
5. Alterar tipo de veiculo persistente: 300

Esses pesos garantem que custo venha primeiro, mas evita mudancas desnecessarias quando o custo empata.

### 11.5 Calculo de horarios

Para cada rota:

1. Solver define ordem de pickup.
2. Somar tempos de deslocamento ate o destino.
3. Fixar chegada em `arrival_at_work_time`.
4. Calcular horarios anteriores de tras para frente.
5. Validar que o primeiro pickup nao ficou antes de `earliest_boarding_time`.

Exemplo:

```text
Chegada ao trabalho: 07:45
Trecho passageiro 3 -> destino: 12 min
Trecho passageiro 2 -> passageiro 3: 8 min
Trecho passageiro 1 -> passageiro 2: 10 min

Passageiro 3: 07:33
Passageiro 2: 07:25
Passageiro 1: 07:15
```

### 11.6 Fallback heuristico

Se OR-Tools falhar:

1. Ordenar passageiros por proximidade ao destino e entre si.
2. Gerar clusters com limite de capacidade por tipo.
3. Avaliar combinacoes de tipos por custo.
4. Aplicar 2-opt simples dentro de cada rota.
5. Validar horarios.
6. Marcar no audit que fallback foi usado.

## 12. LangChain e prompt

### 12.1 Ferramentas do agente

Tools LangChain recomendadas:

1. `load_planning_input`
   - Retorna input canonico ja validado.

2. `geocode_route_points`
   - Executa geocoding ou recupera cache.

3. `build_route_matrices`
   - Chama Mapbox Matrix.

4. `solve_transport_plan`
   - Executa OR-Tools/fallback.

5. `validate_transport_plan`
   - Revalida custo, capacidade, horarios, enderecos e ids.

6. `build_change_summary`
   - Monta diff amigavel para o admin.

O agente nao deve ter tool direta para aplicar mudancas. Aplicacao e sempre endpoint separado, acionado pelo botao `Aplicar`.

### 12.2 Structured output

O agente deve retornar `TransportAgentPlan` como structured output.

Usar:

1. Pydantic models.
2. `response_format=TransportAgentPlan` quando o LangChain/modelo suportar.
3. Retry automatico se a validacao Pydantic falhar.
4. Se falhar apos retries, marcar run como `failed`.

### 12.3 Prompt robusto

Criar prompt versionado, por exemplo:

`sistema/app/prompts/transport_ai_route_planner_v1.md`

Conteudo base:

```text
You are a transport planning agent for the Checking Transport backend.

You must produce only a validated structured transport plan using the schema supplied by the application.

Hard rules:
- Never invent addresses, coordinates, prices, vehicles, passenger ids, request ids, project ids, or travel times.
- Use only data returned by tools.
- The route kind for this run is home_to_work.
- Passengers must stay in their own request kind: EXTRA, WEEKEND, or REGULAR.
- Passengers must stay in their project/country partition unless the deterministic planner explicitly marks destinations as mergeable.
- Ignore vehicle tolerance minutes completely.
- Every suggested vehicle route must arrive at the work destination no later than the configured arrival_at_work_time.
- The first pickup in every suggested vehicle route must not be earlier than earliest_boarding_time.
- Vehicle capacity must never be exceeded.
- Minimize total vehicle cost first.
- Use number of vehicles, route duration, route distance, and number of operational changes only as tie breakers.
- If required data is missing, return a blocking validation issue instead of guessing.

Workflow:
1. Load the planning input.
2. Geocode every passenger origin and project destination.
3. Build route matrices using the configured map provider.
4. Call the deterministic optimizer.
5. Validate the optimizer result.
6. Return the structured plan with vehicle actions, passenger allocations, route itineraries, costs, and human-readable rationales.

Output:
- Return no markdown.
- Return no prose outside the structured response.
- Every vehicle action must explain why it exists.
- Every unallocated passenger must have a blocking issue with a clear reason.
```

### 12.4 O que nao colocar no prompt

Nao incluir:

1. API keys.
2. Tokens Mapbox.
3. Senhas.
4. Dados brutos desnecessarios de usuarios.
5. Logs de requests externos.

Incluir somente:

1. IDs tecnicos necessarios.
2. Nome do passageiro se for usado na janela de alteracoes.
3. Enderecos necessarios para roteirizacao.
4. Custos, capacidades e horarios.

## 13. Aplicacao das alteracoes

### 13.1 Ordem de apply

O endpoint `apply` deve executar em uma transacao:

1. Bloquear run/sugestao para evitar apply duplo.
2. Revalidar estado atual.
3. Aplicar remocoes do dia.
4. Aplicar edicoes de veiculos existentes.
5. Criar veiculos novos.
6. Resolver `vehicle_ref` para `vehicle_id`.
7. Criar proposal interna de assignments.
8. Validar/approve/apply assignments.
9. Persistir route stops.
10. Atualizar status da sugestao.
11. Commit.
12. Emitir eventos.

### 13.2 Remocao de veiculos

Nao usar delete destrutivo como primeira opcao para o agente.

Regra recomendada:

1. `extra`: pode desativar/remover o schedule single-date se ele so existe para aquela data.
2. `regular` e `weekend`: preferir "remover do dia" via excecao de schedule ou status inativo date-scoped, para nao destruir recorrencia futura.
3. Se for necessario delete permanente, exigir uma action distinta `delete_permanently`, fora da primeira entrega.

### 13.3 Edicao de tipo de veiculo

Editar tipo de um veiculo existente pode afetar outros dias.

Regra recomendada:

1. Permitir na proposal.
2. Mostrar destaque na janela `Alteracoes`.
3. Revalidar assignments futuros antes de aplicar.
4. Se houver impacto futuro bloqueante, impedir apply.

### 13.4 Criacao de veiculos

Veiculos criados pelo agente:

1. Devem ter `service_scope` da lista correta.
2. Devem ter tipo definido.
3. Devem ter `lugares` definido.
4. Devem receber placa placeholder operacional somente se o produto permitir.
5. Melhor alternativa: permitir placa vazia, usando o suporte ja existente a veiculo parcial, mas marcar como pendente se a placa for obrigatoria para operacao real.

Como o agente precisa alocar passageiros, o veiculo criado precisa estar pronto para alocacao. Portanto, se placa for obrigatoria para `is_ready_for_allocation`, ha duas opcoes:

1. Criar uma convencao de placa temporaria controlada, como `AI-YYYYMMDD-001`, marcada como temporaria em novo campo.
2. Alterar a regra de prontidao para permitir veiculo criado por IA sem placa real, desde que tenha `temporary_identifier`.

Recomendacao: criar campo novo `temporary_label` ou `operational_code` para veiculos planejados, sem gravar `Waiting` em `placa`.

## 14. Mudancas no frontend

### 14.1 `index.html`

Alterar modal `Ajustes para o Agente de IA`:

1. Preencher `value="06:50"` no input de embarque.
2. Preencher `value="07:45"` no input de chegada.
3. Trocar rodape atual de um botao `Fechar` por:
   - `Cancelar`
   - `Solicitar Rotas`
4. Adicionar atributos:
   - `data-ai-agent-cancel`
   - `data-ai-agent-submit`
   - `data-ai-agent-feedback`

Adicionar modal `Alteracoes`:

1. `data-ai-changes-modal`
2. `data-ai-changes-summary`
3. `data-ai-changes-tabs`
4. `data-ai-changes-vehicles`
5. `data-ai-changes-passengers`
6. `data-ai-changes-routes`
7. `data-ai-changes-audit`
8. `data-ai-changes-cancel`
9. `data-ai-changes-save`
10. `data-ai-changes-apply`

### 14.2 `app.js`

Adicionar estado:

```js
aiRouteRunKey: null,
aiRouteRunStatus: null,
aiRouteSuggestion: null,
aiRoutePollingTimer: null,
aiChangesModalOpen: false,
aiChangesSaving: false,
aiChangesApplying: false,
```

Adicionar funcoes:

1. `getDefaultAiAgentSettings()`
2. `syncAiAgentSettingsControls()`
3. `readAiAgentSettingsDraft()`
4. `validateAiAgentSettingsDraft()`
5. `requestAiRoutes()`
6. `pollAiRouteRun()`
7. `openAiChangesModal()`
8. `closeAiChangesModal()`
9. `renderAiChangesSummary()`
10. `renderAiVehicleChanges()`
11. `renderAiPassengerAllocations()`
12. `renderAiRouteItineraries()`
13. `saveAiSuggestion()`
14. `cancelAiSuggestion()`
15. `applyAiSuggestion()`
16. `loadLatestAiSuggestion()`

Atualizar listeners:

1. `aiCalculateRoutesButton`: abre modal settings com defaults.
2. `data-ai-agent-cancel`: fecha sem API.
3. `data-ai-agent-submit`: chama `requestAiRoutes`.
4. `aiImplementModificationsButton`: chama `loadLatestAiSuggestion`.
5. Botoes da janela `Alteracoes`: cancel/save/apply.

### 14.3 `i18n.js`

Adicionar chaves em todos os idiomas:

1. `ai.agentSettingsCancel`
2. `ai.agentSettingsSubmit`
3. `ai.agentSettingsSubmitting`
4. `ai.agentSettingsInvalidTimes`
5. `ai.changesTitle`
6. `ai.changesSummary`
7. `ai.changesVehicles`
8. `ai.changesPassengers`
9. `ai.changesRoutes`
10. `ai.changesAudit`
11. `ai.changesCancel`
12. `ai.changesSave`
13. `ai.changesApply`
14. `ai.noSavedSuggestion`
15. `ai.suggestionSaved`
16. `ai.suggestionApplied`
17. `ai.suggestionCancelled`
18. `ai.routeCalculationFailed`
19. `ai.missingPrices`
20. `ai.unallocatedPassenger`

### 14.4 `styles.css`

Adicionar estilos para:

1. Modal `Alteracoes` com largura maior.
2. Tabs compactas.
3. Tabelas densas de diff.
4. Badges:
   - `Adicionar`
   - `Editar`
   - `Remover`
   - `Manter`
5. Destaque de economia/custo.
6. Lista de paradas por veiculo.
7. Estado loading.
8. Estado erro.
9. Responsividade mobile.

## 15. Integracao com contracts existentes

### 15.1 Reutilizar snapshot

Nao criar outra leitura paralela do dashboard. O agente deve usar `build_transport_operational_snapshot` e enriquecer o resultado.

### 15.2 Reutilizar proposal de assignments

Depois que as acoes de veiculo forem aplicadas, converter alocacoes do agente em `TransportProposalDecision` e usar o fluxo atual:

1. `validate_transport_operational_proposal`
2. `approve_transport_operational_proposal`
3. `apply_transport_operational_proposal`

### 15.3 Extender sem quebrar

Nao alterar semanticamente os endpoints existentes. Criar endpoints `ai/*` para o fluxo novo.

### 15.4 Auditoria

Toda sugestao deve registrar:

1. Quem solicitou.
2. Quando solicitou.
3. Quais horarios foram usados.
4. Qual modelo foi usado.
5. Qual provider de mapa foi usado.
6. Qual snapshot original foi usado.
7. Quais passengers/vehicles entraram no plano.
8. Quais mudancas foram sugeridas.
9. Quais mudancas foram aplicadas.
10. Quais issues bloquearam ou alertaram.

## 16. Validacoes obrigatorias

### 16.1 Preflight antes de resetar passageiros

Validar:

1. IA habilitada.
2. Sessao autenticada.
3. Horarios validos.
4. Precos suficientes.
5. Assentos padrao suficientes.
6. Projetos carregados.
7. Ha requests elegiveis.
8. Limite de passageiros nao excedido.
9. Mapbox token configurado.
10. OpenAI key configurada.

Se falhar aqui: nao resetar passageiros.

### 16.2 Depois de resetar passageiros

Validar:

1. Baseline salvo.
2. Todos requests elegiveis estao pending.
3. Veiculos continuam cadastrados.

Se falhar: restaurar baseline automaticamente.

### 16.3 Depois do agente

Validar:

1. Todos os passageiros elegiveis foram alocados ou possuem issue.
2. Toda alocacao aponta para veiculo existente ou planejado.
3. Capacidade nao excedida.
4. Primeiro pickup >= earliest.
5. Chegada <= arrival.
6. Custo calculado bate com os tipos usados.
7. Veiculos removidos nao possuem passageiros alocados.
8. Veiculos criados possuem dados suficientes.
9. Nenhuma action cruza listas indevidamente.

### 16.4 Antes de aplicar

Revalidar contra banco atual:

1. Requests ainda existem e estao ativos.
2. Requests ainda se aplicam a data.
3. Requests ainda estao pending ou em estado permitido.
4. Veiculos existentes ainda existem.
5. Schedules ainda existem.
6. Precos/capacidades nao mudaram de forma que invalidem o plano.
7. Coordenadas ainda sao as mesmas ou o plano aceita drift.

## 17. Testes

### 17.1 Backend unitario

Adicionar testes para:

1. `TransportAgentRouteRequest` valida horarios.
2. Preflight bloqueia preco ausente.
3. Preflight bloqueia projeto sem endereco.
4. Preflight bloqueia passageiro sem endereco.
5. Geocoding normaliza query corretamente.
6. Matrix chunking respeita limites do provider.
7. Solver respeita capacidade.
8. Solver respeita earliest boarding.
9. Solver respeita arrival at work.
10. Solver minimiza custo antes de distancia.
11. Conversao de plano para vehicle actions.
12. Conversao de plano para proposal decisions.

### 17.2 Backend integracao

Adicionar em `tests/test_api_flow.py` ou arquivo novo:

1. `POST /api/transport/ai/route-calculations` salva baseline.
2. O mesmo endpoint reseta assignments para pending.
3. Run com passageiros sem endereco falha sem aplicar sugestao.
4. Run com provider fake gera sugestao.
5. `save` persiste sugestao sem aplicar assignments.
6. `latest` recupera sugestao salva.
7. `cancel` restaura baseline.
8. `apply` cria veiculo novo e aplica assignments.
9. `apply` edita tipo de veiculo existente.
10. `apply` remove veiculo do dia sem deletar recorrencia futura.
11. `apply` bloqueia se request mudou depois da sugestao.
12. `apply` bloqueia se capacidade ficou invalida.

### 17.3 Provider fake

Criar fake deterministico para Mapbox:

1. Geocoding retorna coordenadas fixas por endereco.
2. Matrix retorna duracoes previsiveis.
3. Directions retorna geometria simples.

Nunca depender de chamadas reais a Mapbox nos testes automatizados.

### 17.4 Frontend Node tests

Estender `tests/transport_page_date.test.js` para:

1. Defaults `06:50` e `07:45`.
2. Validacao local de horarios.
3. Botao Cancelar nao chama API.
4. `Solicitar Rotas` monta payload correto.
5. `Implementar Modifications` chama endpoint latest.
6. Render de resumo de custo.
7. Render de vehicle actions.
8. Render de passenger allocations.
9. Botoes Save/Apply/Cancel chamam endpoints corretos.

### 17.5 Playwright/manual

Validar manualmente:

1. Abrir `/transport`.
2. Autenticar.
3. Abrir `IA > Calcular Rotas`.
4. Conferir defaults.
5. Cancelar e verificar nenhuma chamada.
6. Solicitar rotas com provider fake/local.
7. Ver usuarios voltarem para listas.
8. Conferir janela `Alteracoes`.
9. Salvar sugestao.
10. Reabrir por `IA > Implementar Modifications`.
11. Aplicar.
12. Ver dashboard com veiculos e passageiros sugeridos.
13. Cancelar sugestao em outro run e confirmar restore.

## 18. Sequencia de implementacao

### Fase 0 - Confirmacao e baseline

1. Rodar testes atuais.
2. Registrar shape atual de `/api/transport/settings`.
3. Registrar shape atual de `/api/transport/operational-snapshot`.
4. Criar fixtures de passageiros/projetos/veiculos para roteirizacao.

Conclusao: baseline verde e fixtures prontas.

### Fase 1 - Configuracao e dependencias

1. Adicionar dependencias.
2. Atualizar `config.py`.
3. Atualizar Dockerfile se necessario.
4. Criar `.env.example` sem segredos reais.
5. Adicionar health/preflight interno para IA.

Conclusao: API sobe sem IA habilitada e nao quebra ambiente atual.

### Fase 2 - Persistencia de runs e suggestions

1. Criar migration.
2. Criar models.
3. Criar schemas.
4. Criar service `transport_ai_runs.py`.
5. Testar salvar baseline.
6. Testar restaurar baseline.

Conclusao: estado atual pode ser salvo e restaurado.

### Fase 3 - Reset seguro para pending

1. Criar comando backend para resetar requests elegiveis.
2. Reutilizar `upsert_transport_assignment_with_persistence` com `status="pending"`.
3. Garantir que regular/weekend limpam recorrencias relevantes.
4. Emitir evento de refresh.
5. Testar restore.

Conclusao: `Solicitar Rotas` consegue devolver usuarios as listas sem perder baseline.

### Fase 4 - Route provider

1. Implementar Mapbox client.
2. Implementar geocoding.
3. Implementar matrix.
4. Implementar directions final.
5. Implementar chunking e retry.
6. Implementar fake provider para testes.

Conclusao: tempos/distancias chegam ao solver de forma deterministica em testes.

### Fase 5 - Planning input

1. Enriquecer snapshot com projetos, destinos e settings.
2. Validar enderecos e precos.
3. Criar particoes por lista/projeto/pais.
4. Criar route points.
5. Criar cost baseline.

Conclusao: input canonico pronto para solver/agente.

### Fase 6 - Solver deterministico

1. Implementar OR-Tools/fallback.
2. Gerar frota candidata.
3. Minimizar custo.
4. Validar horarios.
5. Gerar itinerarios.
6. Gerar vehicle actions.
7. Gerar passenger allocations.

Conclusao: solver gera plano sem LangChain.

### Fase 7 - LangChain agent

1. Criar prompt versionado.
2. Criar tools.
3. Criar structured output.
4. Integrar `ChatOpenAI`.
5. Registrar raw response sanitizada.
6. Fazer retries controlados.

Conclusao: agente orquestra e retorna plano validado.

### Fase 8 - Endpoints AI

1. Criar router `transport_ai.py`.
2. Registrar router em `main.py`.
3. Implementar start/poll/latest/save/cancel/apply.
4. Integrar eventos de refresh.
5. Testar fluxo completo com fake provider.

Conclusao: backend exposto para frontend.

### Fase 9 - Frontend settings modal

1. Ajustar modal `Ajustes`.
2. Defaults `06:50` e `07:45`.
3. Botao `Cancelar`.
4. Botao `Solicitar Rotas`.
5. Feedback de loading/erro.

Conclusao: usuario consegue iniciar run.

### Fase 10 - Frontend janela `Alteracoes`

1. Criar markup.
2. Criar estilos.
3. Renderizar resumo.
4. Renderizar veiculos.
5. Renderizar passageiros.
6. Renderizar rotas.
7. Renderizar auditoria.
8. Implementar Save/Apply/Cancel.

Conclusao: admin entende e controla sugestao.

### Fase 11 - Aplicacao real e auditoria

1. Aplicar vehicle actions.
2. Aplicar assignments via proposal existente.
3. Persistir route stops.
4. Revalidar drift.
5. Emitir eventos.
6. Atualizar export operacional se necessario.

Conclusao: sugestao aplicada aparece no dashboard.

### Fase 12 - Testes finais e deploy

1. Rodar pytest focado.
2. Rodar node tests.
3. Rodar Playwright/manual.
4. Testar Docker build.
5. Deploy em Digital Ocean com IA desabilitada.
6. Habilitar IA em janela controlada.
7. Monitorar logs e custos.

Conclusao: rollout seguro.

## 19. Riscos e mitigacoes

### 19.1 Custo de Mapbox

Risco: Matrix API pode gerar muitas celulas.

Mitigacao:

1. Limitar passageiros por run.
2. Chunking.
3. Cache.
4. Agrupar por projeto/lista/pais.
5. Mostrar estimativa de chamadas no audit.

### 19.2 LLM sugerir plano invalido

Risco: modelo retorna algo inconsistente.

Mitigacao:

1. Structured output.
2. Pydantic.
3. Solver deterministico.
4. Revalidacao pre-apply.
5. Apply transacional.

### 19.3 Remocao destrutiva de veiculos

Risco: remover veiculo recorrente pode afetar dias futuros.

Mitigacao:

1. `remove_from_day` por padrao.
2. Baseline salvo.
3. Restore no cancelamento.
4. Delete permanente fora da primeira entrega.

### 19.4 Enderecos ruins

Risco: passageiro sem endereco ou geocode errado.

Mitigacao:

1. Issues bloqueantes.
2. Confianca minima.
3. Mostrar enderecos problemáticos.
4. Nao inventar coordenadas.

### 19.5 Aplicacao depois de drift

Risco: dashboard muda entre salvar e aplicar.

Mitigacao:

1. Revalidar no apply.
2. Bloquear se request/vehicle/schedule mudou.
3. Permitir gerar nova sugestao substituindo `replaces_proposal_key`.

## 20. Checklist de aceite

Entrega so deve ser considerada concluida quando:

1. `IA > Calcular Rotas` abre modal com `06:50` e `07:45`.
2. `Cancelar` no modal de ajustes nao chama backend.
3. `Solicitar Rotas` salva baseline antes de qualquer mudanca.
4. Passageiros voltam para suas user lists.
5. Veiculos existentes permanecem cadastrados durante o calculo.
6. Agente le precos padrao por tipo.
7. Agente le assentos por tipo e assentos reais de veiculos existentes.
8. Agente ignora tolerancia.
9. Agente respeita primeiro embarque >= horario minimo.
10. Agente respeita chegada ao trabalho <= horario definido.
11. Agente usa enderecos dos passageiros e projeto/pais corretos.
12. Agente consulta Mapbox ou fake provider nos testes.
13. Agente sugere numero/tipo de veiculos.
14. Agente sugere adicionar, editar e remover veiculos do dia quando necessario.
15. Agente aloca passageiros por lista correta.
16. Janela `Alteracoes` mostra resumo facil de entender.
17. `Cancelar` na janela `Alteracoes` descarta sugestao e restaura baseline.
18. `Salvar` persiste sugestao sem aplicar.
19. `IA > Implementar Modifications` reabre sugestao salva.
20. `Aplicar` aplica veiculos e assignments.
21. Apply e transacional e revalidado.
22. Testes backend e frontend passam.
23. Nenhuma chave real e gravada em arquivo versionado.

## 21. Referencias tecnicas consultadas

1. LangChain ChatOpenAI: https://docs.langchain.com/oss/python/integrations/chat/openai
2. LangChain structured output: https://docs.langchain.com/oss/python/langchain/structured-output
3. OpenAI structured outputs: https://platform.openai.com/docs/guides/structured-outputs
4. OpenAI GPT-5 snapshots: https://platform.openai.com/docs/models/gpt-5
5. OpenAI API key safety: https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety
6. Mapbox Matrix API: https://docs.mapbox.com/api/navigation/matrix/
7. Mapbox Directions API: https://docs.mapbox.com/api/navigation/directions/
8. Mapbox Geocoding API: https://docs.mapbox.com/api/search/geocoding/
9. Google OR-Tools VRP: https://developers.google.com/optimization/routing/vrp

## 22. To-do list detalhada para implementacao

Esta to-do list foi organizada para poder ser executada por fases independentes, com checkpoints claros. Cada item esta escrito como um prompt operacional para um agente de IA ou desenvolvedor implementar sem precisar reinterpretar o plano inteiro. Nenhum item deve gravar segredos reais no repositorio.

### Fase 0 - Baseline, inventario e protecao inicial

#### 0.1 Criar baseline tecnico antes da implementacao

Resumo detalhado do que foi alterado nesta etapa: foi criado o documento `docs/fase_ai_0_baseline_transport.md`, consolidando o estado atual do modulo `transport` antes de qualquer implementacao da IA. O baseline passou a registrar os endpoints ja disponiveis no router `transport`, agrupados por sessao, leitura operacional, proposal, exportacao, settings e mutacoes operacionais. Tambem ficou documentado o shape real confirmado de `/api/transport/settings`, incluindo campos de horario, assentos, tolerancia, moeda, unidade de cobranca, precos por tipo e lista de moedas, com exemplo anonizado do payload default atual e de um payload configurado. Alem disso, o documento registra o shape real de `/api/transport/operational-snapshot`, cobrindo raiz do contrato, projetos, requests, `assigned_vehicle`, `vehicle_registry` e `workplaces`, com um exemplo anonizado reduzido baseado no contrato atual e nos testes ja existentes.

O baseline tambem passou a descrever o estado atual do frontend `transport` com foco no fluxo de IA: topbar, menu `IA`, listas de passageiros, listas de veiculos, modal `Ajustes para o Agente de IA` e comportamento efetivo das acoes `Calculate Routes` e `Implement Modifications`. Ficou explicitamente registrado que o modal da IA ja existe, mas ainda e apenas estrutural: possui os campos `data-ai-agent-earliest-boarding` e `data-ai-agent-arrival-at-work`, fecha por botao, backdrop e `Escape`, mas ainda nao preenche defaults, nao valida horarios, nao chama backend, nao faz polling e nao abre qualquer janela de alteracoes. Tambem foram consolidadas as lacunas confirmadas para o fluxo de IA, separando backend e frontend, alem dos riscos imediatos e dos invariantes que a proxima implementacao nao pode quebrar, como o uso de sessao existente, caminhos relativos `../api/transport`, separacao por listas `extra/weekend/regular`, reaproveitamento do snapshot operacional e preservacao do contrato atual de proposals.

As validacoes previstas para esta fase foram executadas com sucesso. O comando `pytest tests/test_api_flow.py -k transport` passou com `80 passed, 176 deselected`, confirmando que a superficie atual de backend do modulo `transport` esta verde dentro do recorte solicitado. O comando `node --test tests/transport_page_date.test.js` tambem passou com `62` testes aprovados, confirmando o baseline atual do frontend `transport`, incluindo helpers, layout, settings e preparacao estrutural do menu/modal da IA. Nesta etapa, as alteracoes feitas ficaram restritas a documentacao e nao introduziram segredos em `docs/`.

#### 0.2 Criar fixtures de planejamento para testes futuros

Resumo detalhado do que foi alterado nesta etapa: foram adicionados helpers reutilizaveis diretamente em `tests/test_api_flow.py` para montar cenarios de planejamento de transporte sem dependencia de Mapbox, OpenAI ou dados reais. A suite passou a contar com `create_transport_planning_project` para criar projetos com `address`, `zip_code`, `country_code` e `country_name`; `create_transport_planning_user_with_request` para criar usuarios com `end_rua`, `zip`, `projeto` e request de transporte nos formatos `regular`, `weekend` e `extra`; `create_transport_planning_vehicle_with_schedules` para registrar veiculos e schedules por escopo operacional; e `configure_transport_planning_settings` para configurar horarios, assentos padrao, tolerancia, moeda, unidade e precos por tipo. Tambem foram adicionados `make_test_project_name`, `clone_transport_settings_payload` e `restore_transport_planning_settings` para reutilizacao segura em testes futuros.

Foi criada ainda uma fixture composta, `create_transport_planning_fixture_bundle`, que monta um dia operacional pequeno e determinista com tres projetos distintos, tres passageiros com endereco residencial e ZIP, tres requests cobrindo os escopos `regular`, `weekend` e `extra`, tres veiculos com seus schedules e uma configuracao completa de pricing e assentos. Como `tests/test_api_flow.py` usa um banco SQLite compartilhado ao longo do arquivo, a etapa tambem passou a incluir `cleanup_transport_planning_fixture_bundle`, que restaura os settings anteriores e remove requests, schedules, usuarios, veiculos, projetos e moeda de teste criados pela fixture, evitando vazamento de estado para outros cenarios.

As validacoes previstas para a fase foram implementadas no teste `test_transport_planning_fixture_bundle_supports_snapshot_and_settings_contracts`. Esse teste monta a fixture completa, chama `GET /api/transport/operational-snapshot` com `route_kind=home_to_work`, chama `GET /api/transport/settings` e valida por identidade dos registros criados que o snapshot retorna os projetos com `address`, `zip_code`, `country_code` e `country_name`; que as listas `regular_requests`, `weekend_requests` e `extra_requests` carregam `end_rua`, `zip` e `projeto` dos passageiros criados; e que o payload de settings reflete os assentos e precos configurados para a fixture. A validacao executada para esta etapa foi `pytest tests/test_api_flow.py -k transport_planning_fixture_bundle_supports_snapshot_and_settings_contracts`, concluida com `1 passed, 256 deselected`.

### Fase 1 - Configuracao, dependencias e seguranca de segredos

#### 1.1 Adicionar dependencias de IA, mapas e otimizacao

Resumo detalhado do que foi alterado nesta etapa: `requirements.txt` passou a incluir e fixar as dependencias de runtime necessarias para a primeira entrega do agente de IA do modulo `transport`, com `httpx==0.28.1`, `langchain==1.2.15`, `langchain-openai==1.2.1` e `ortools==9.15.6755`. Com isso, o projeto agora tem pinning explicito para o cliente HTTP que sera usado pelo provider de mapas, para a orquestracao via LangChain, para a integracao com OpenAI dentro do ecossistema LangChain e para o solver deterministico de otimizacao. Como `httpx` deixou de ser apenas dependencia de desenvolvimento, ele foi removido de `requirements-dev.txt`, evitando redundancia e mantendo o ambiente dev alinhado ao runtime por meio do `-r requirements.txt`.

Tambem foi criado o documento `docs/fase_ai_1_dependencias.md`, registrando as versoes escolhidas, a justificativa tecnica de cada pacote e as observacoes operacionais da fase. O documento deixa explicito que o `Dockerfile` ja consome `requirements.txt`, entao a imagem local/produtiva passa a herdar automaticamente os mesmos pins introduzidos aqui. Ele tambem registra que o OR-Tools instalou corretamente no `venv` local, portanto nao foi necessario ativar nesta etapa uma flag temporaria para desabilitar o solver; o fallback heuristico continua apenas como estrategia planejada caso custo ou tamanho de imagem se tornem um problema mais adiante.

As validacoes previstas para a fase foram executadas com sucesso. O comando `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pip install --disable-pip-version-check -r requirements.txt` confirmou a resolucao do ambiente com os novos pins. O comando `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -c "import langchain; import langchain_openai; import httpx; import ortools"` validou os imports das dependencias novas. Em seguida, `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k transport` passou com `81 passed, 176 deselected`, confirmando que a superficie atual de backend do modulo `transport` continua integra apos a entrada dessas bibliotecas. Durante o import em Python `3.14.3`, o `langchain_core` emitiu um aviso nao bloqueante sobre caminhos legados de Pydantic V1 em Python `3.14+`; a validacao permaneceu verde e o runtime principal da imagem segue baseado em `python:3.12-slim`.

#### 1.2 Adicionar configuracoes server-side para IA e Mapbox

Resumo detalhado do que foi alterado nesta etapa: `sistema/app/core/config.py` passou a expor a superficie server-side inicial para IA e Mapbox por meio de novos campos em `Settings`, todos com defaults seguros para manter a aplicacao funcional antes da ativacao da feature. Foram adicionados `openai_api_key`, `openai_model`, `openai_temperature`, `openai_timeout_seconds`, `openai_max_retries`, `mapbox_access_token`, `mapbox_matrix_profile`, `mapbox_directions_profile`, `mapbox_timeout_seconds`, `mapbox_max_retries`, `mapbox_geocoding_permanent`, `transport_ai_enabled`, `transport_ai_max_passengers_per_run`, `transport_ai_max_runtime_seconds`, `transport_ai_route_cache_ttl_seconds` e `transport_ai_geocode_cache_ttl_days`. Os novos segredos ficaram opcionais (`str | None`) e a flag `transport_ai_enabled` foi introduzida com default `False`, para que a app continue subindo normalmente mesmo sem `OPENAI_API_KEY` e `MAPBOX_ACCESS_TOKEN` configurados.

O arquivo `.env.example` tambem foi atualizado com placeholders e defaults nao sensiveis para essa nova superficie de configuracao. Foram adicionadas entradas para `TRANSPORT_AI_ENABLED=false`, `OPENAI_API_KEY=`, `OPENAI_MODEL=gpt-5-2025-08-07`, `OPENAI_TEMPERATURE=0`, `OPENAI_TIMEOUT_SECONDS=120`, `OPENAI_MAX_RETRIES=2`, `MAPBOX_ACCESS_TOKEN=`, `MAPBOX_MATRIX_PROFILE=mapbox/driving-traffic`, `MAPBOX_DIRECTIONS_PROFILE=mapbox/driving-traffic`, `MAPBOX_TIMEOUT_SECONDS=20`, `MAPBOX_MAX_RETRIES=2`, `MAPBOX_GEOCODING_PERMANENT=false`, `TRANSPORT_AI_MAX_PASSENGERS_PER_RUN=80`, `TRANSPORT_AI_MAX_RUNTIME_SECONDS=180`, `TRANSPORT_AI_ROUTE_CACHE_TTL_SECONDS=3600` e `TRANSPORT_AI_GEOCODE_CACHE_TTL_DAYS=30`. Nesta fase nao foi introduzido nenhum valor real de OpenAI ou Mapbox no repositorio; os placeholders ficaram vazios ou com valores operacionais nao secretos.

Para validar o comportamento defensivo com IA desabilitada, foi criado o arquivo `tests/test_transport_ai_config.py`. A suite nova cobre dois pontos: a primeira verificacao instancia `Settings(_env_file=None)` e confirma que todos os novos defaults server-side sao carregados com os valores esperados e sem exigir segredos; a segunda executa um subprocesso Python isolado, com `TRANSPORT_AI_ENABLED=false`, `OPENAI_API_KEY` ausente, `MAPBOX_ACCESS_TOKEN` ausente e `DATABASE_URL` apontando para SQLite temporario, e valida que a aplicacao sobe com `TestClient(app)` e responde `200` em `/api/health`. A validacao executada foi `pytest tests/test_transport_ai_config.py`, concluida com `2 passed`. Tambem foi feita uma busca focada no repositorio por `sk-`, `sk-proj` e `MAPBOX_ACCESS_TOKEN=` em `sistema/`, `docs/`, `tests/`, `scripts/` e `.env.example`; as ocorrencias relevantes encontradas permaneceram apenas como placeholders documentais (`...`), texto de validacao ou checagens de codigo, sem valor real versionado. Nenhum endpoint novo de preflight foi criado nesta etapa; a checagem operacional explicita de disponibilidade da IA ficou reservada para a secao `1.3`.

#### 1.3 Criar checagem de disponibilidade da IA

Resumo detalhado do que foi alterado nesta etapa: foi criado o modulo `sistema/app/services/transport_ai_runtime.py`, que passa a concentrar a checagem reutilizavel de disponibilidade server-side da IA por meio da funcao `validate_transport_ai_runtime_configuration`. Essa funcao recebe uma sessao de banco e usa os `Settings` atuais para validar, em um unico ponto, se a IA esta habilitada (`transport_ai_enabled`), se existe modelo OpenAI configurado, se `openai_api_key` foi informado, se `mapbox_access_token` esta presente, se existe ao menos um preco de transporte configurado em `MobileAppSettings` e se os limites `transport_ai_max_passengers_per_run` e `transport_ai_max_runtime_seconds` sao maiores que zero. A funcao foi desenhada para ser reutilizada futuramente pelo endpoint `Solicitar Rotas` antes de salvar baseline ou resetar passageiros.

Para sustentar essa checagem com um contrato proprio de preflight, `sistema/app/schemas.py` passou a expor `TransportAIPreflightIssue` e `TransportAIPreflightCheckResult`. O novo schema de issue reutiliza o padrao de `code`, `message` e `blocking`, acrescentando `setting_name` para apontar qual configuracao motivou a falha. O resultado de preflight passa a ser um objeto com `ok` e `issues`, o que deixa a superficie pronta para reuso tanto por services quanto por futuros endpoints. Nesta etapa, os codigos bloqueantes adicionados foram `transport_ai_disabled`, `openai_model_missing`, `openai_api_key_missing`, `mapbox_access_token_missing`, `transport_ai_pricing_missing`, `transport_ai_max_passengers_per_run_invalid` e `transport_ai_max_runtime_seconds_invalid`.

Os testes desta fase foram implementados em `tests/test_transport_ai_runtime.py`. A nova suite cobre os cenarios exigidos de configuracao incompleta e completa: IA desabilitada retornando `transport_ai_disabled`; ausencia de chave OpenAI retornando `openai_api_key_missing`; ausencia de token Mapbox retornando `mapbox_access_token_missing`; ausencia de precos retornando `transport_ai_pricing_missing`; limites invalidos retornando issues especificas de runtime; e configuracao completa retornando `ok=True` sem issues bloqueantes. A validacao executada para esta etapa foi `pytest tests/test_transport_ai_runtime.py`, concluida com `6 passed`. Nenhum endpoint novo foi criado aqui; esta fase ficou restrita ao contrato reutilizavel de preflight, ao service de validacao e aos testes focados que comprovam o comportamento esperado.

### Fase 2 - Persistencia de runs, sugestoes e cache

#### 2.1 Criar migration e models para runs de IA

Resumo detalhado do que foi alterado nesta etapa: foi adicionado o model `TransportAIRun` em `sistema/app/models.py`, representando cada execucao iniciada por `Solicitar Rotas`. O model passou a persistir `run_key`, `service_date`, `route_kind`, `status`, `actor_user_id`, `earliest_boarding_time`, `arrival_at_work_time`, `openai_model`, `route_provider`, `price_currency_code`, `price_rate_unit`, os blobs `baseline_snapshot_json`, `baseline_assignments_json`, `baseline_vehicle_state_json`, `planning_input_json`, `planning_input_hash`, `preflight_issues_json`, alem de `error_code`, `error_message`, `created_at`, `updated_at` e `completed_at`. Os payloads estruturados ficaram armazenados em `Text`, mantendo compatibilidade com SQLite/Postgres sem depender de JSONB. O model tambem passou a expor as constraints `ck_transport_ai_runs_status_allowed` e `ck_transport_ai_runs_route_kind_allowed`, um indice unico `ix_transport_ai_runs_run_key` e um indice composto `ix_transport_ai_runs_service_date_route_kind_created_at`.

Para materializar esse schema no banco, foi criada a migration `alembic/versions/0046_add_transport_ai_runs.py`, encadeada a partir de `0045_add_project_address_and_zip_code`. A migration cria a tabela `transport_ai_runs` com `ForeignKey` para `admin_users.id`, preserva idempotencia basica ao nao recriar a tabela se ela ja existir e garante a criacao dos dois indices exigidos pela etapa. A validacao desta fase foi consolidada em `tests/test_transport_ai_runs_model.py`: a suite sobe um SQLite temporario com `alembic upgrade head`, verifica a presenca da tabela e dos indices, cria uma run com status `requested`, confirma que status invalido dispara `IntegrityError` pela check constraint e busca a run persistida por `run_key`. O comando executado foi `pytest tests/test_transport_ai_runs_model.py -q`, concluido com `4 passed`. Nenhum endpoint ou service de execucao foi introduzido aqui; esta etapa ficou restrita a persistencia inicial das runs de IA, pronta para sustentar baseline, polling e sugestoes nas proximas secoes.

#### 2.2 Criar migration e models para sugestoes da IA

Resumo detalhado do que foi alterado nesta etapa: foi adicionado o model `TransportAISuggestion` em `sistema/app/models.py`, cobrindo a persistencia da sugestao gerada pela IA para que ela possa sobreviver a reload do dashboard e ser reaberta futuramente por `IA > Implementar Modifications`. O model passou a persistir `suggestion_key`, `run_id`, `service_date`, `route_kind`, `proposal_key`, `status`, os blobs `agent_plan_json`, `transport_proposal_json`, `vehicle_actions_json`, `assignment_actions_json`, `route_itineraries_json`, `change_summary_json`, `cost_summary_json`, `validation_issues_json`, alem de `raw_model_response_json`, `prompt_version`, `created_at`, `updated_at`, `saved_at`, `applied_at` e `discarded_at`. Assim como em `transport_ai_runs`, os payloads estruturados foram armazenados em `Text`, preservando compatibilidade entre SQLite e Postgres sem exigir JSONB. O model tambem passou a expor a check constraint `ck_transport_ai_suggestions_status_allowed` para os status `draft`, `shown`, `saved`, `discarded`, `applied` e `expired`, a check constraint `ck_transport_ai_suggestions_route_kind_allowed` e os indices `ix_transport_ai_suggestions_suggestion_key` e `ix_transport_ai_suggestions_service_date_route_kind_status_updated_at`. Nesta implementacao, `service_date` e `route_kind` ficaram duplicados na propria sugestao para viabilizar lookup direto por data/rota da janela atual sem depender de join tardio com a run.

Para materializar o schema, foi criada a migration `alembic/versions/0047_add_transport_ai_suggestions.py`, encadeada a partir de `0046_add_transport_ai_runs`. A migration cria a tabela `transport_ai_suggestions` com `ForeignKey` para `transport_ai_runs.id`, reaplica de forma idempotente os indices necessarios se a tabela ja existir e deixa pronta a base para salvar sugestoes `shown`, `saved`, `applied`, `discarded` e `expired`. Alem do model e da migration, foi criado o modulo `sistema/app/services/transport_ai_runs.py` com helpers focados nesta fase: `create_transport_ai_suggestion` para persistir uma sugestao vinculada a uma `TransportAIRun`; `set_transport_ai_suggestion_status` para transicionar a sugestao e preencher os timestamps de `saved`, `applied` ou `discarded`; `get_latest_saved_transport_ai_suggestion` para recuperar a ultima sugestao salva por `service_date` e `route_kind`; e `get_latest_active_transport_ai_suggestion` para recuperar apenas sugestoes ainda ativas, filtrando por `shown` e `saved` e excluindo implicitamente `applied`, `discarded` e `expired`.

As validacoes desta etapa foram implementadas em `tests/test_transport_ai_suggestions_model.py`. A suite sobe um SQLite temporario com `alembic upgrade head`, verifica a existencia da tabela e dos indices, cria uma sugestao com status `shown`, confirma a transicao para `saved`, valida a busca da ultima sugestao salva por data/rota e garante que sugestoes marcadas como `applied` ou `discarded` nao retornam no lookup da latest ativa. O comando executado foi `pytest tests/test_transport_ai_suggestions_model.py -q`, concluido com `4 passed`. Nenhum endpoint de IA foi introduzido nesta fase; esta entrega ficou restrita ao armazenamento das sugestoes, aos metadados minimos de reload/reabertura e aos helpers de consulta que as proximas secoes poderao reutilizar.

#### 2.3 Criar tabelas de cache de geocoding e matrix

Esta etapa adicionou persistencia dedicada para o cache de geocoding e matrix usado pelo fluxo de IA de transporte. Em `sistema/app/models.py` foram criados os models `TransportAIRoutePoint` e `TransportAIRouteMatrix`, ambos com chaves de cache dedicadas (`point_key` e `matrix_key`), colunas `expires_at` para controle de TTL e campos suficientes para reabrir resultados sem depender de estruturas JSON tipadas por banco. O model de route points passou a guardar endereco normalizado, pais, coordenadas, provider, `provider_place_id`, confianca e a resposta bruta opcional; o model de matrizes passou a guardar `provider`, `profile`, `depart_at`, `coordinate_hash`, listas serializadas de `sources` e `destinations`, alem de `durations` e `distances` em `Text` para manter compatibilidade entre SQLite e Postgres.

No banco, a migration `alembic/versions/0048_add_transport_ai_route_cache_tables.py` foi adicionada com `down_revision = "0047_add_transport_ai_suggestions"`. Ela cria as tabelas `transport_ai_route_points` e `transport_ai_route_matrices`, aplica os `CheckConstraint` de tipo/faixa numerica do cache de geocoding e registra os indices unicos `ix_transport_ai_route_points_point_key` e `ix_transport_ai_route_matrices_matrix_key`. A migration segue o mesmo padrao defensivo das fases anteriores, verificando existencia das tabelas e dos indices antes de criar ou remover cada estrutura.

Tambem foi criado `sistema/app/services/transport_route_cache.py`, concentrando os helpers de hash e de persistencia desta fase. O arquivo introduz a normalizacao de query de endereco, o hash deterministico de `point_key`, a canonicalizacao e o hash de coordenadas para `coordinate_hash`, o builder de `matrix_key` e as funcoes `get_cached_transport_ai_route_point`, `upsert_transport_ai_route_point`, `get_cached_transport_ai_route_matrix` e `upsert_transport_ai_route_matrix`. O cache de geocoding usa `transport_ai_geocode_cache_ttl_days`, o cache de matrix usa `transport_ai_route_cache_ttl_seconds` e a regra `MAPBOX_GEOCODING_PERMANENT=false` passou a ser respeitada diretamente no write path: quando a configuracao esta desabilitada, `raw_response_json` nao e armazenado, mesmo que o provider retorne payload bruto.

As validacoes focadas desta entrega ficaram em `tests/test_transport_ai_route_cache.py`. A suite sobe um SQLite temporario com `alembic upgrade head`, verifica a existencia das duas tabelas e dos indices, confirma cache hit para o mesmo endereco apos normalizacao, garante cache miss para endereco diferente, valida que uma matrix expirada deixa de ser reutilizada, cobre hit de matrix para o mesmo conjunto de coordenadas/perfil e assegura que `raw_response_json` permanece nulo quando `mapbox_geocoding_permanent` esta falso. O comando executado foi `pytest tests/test_transport_ai_route_cache.py -q`, concluido com `6 passed`.

#### 2.4 Criar tabela de paradas aplicadas

Esta etapa adicionou a persistencia das paradas efetivamente aplicadas pelo fluxo de IA para que a rota comunicada ao administrador possa ser reaberta e auditada depois do apply. Em `sistema/app/models.py` foi criado o model `TransportAIAppliedRouteStop`, ligado a `transport_ai_suggestions` por `suggestion_id` e com colunas para `vehicle_id`, `stop_order`, `stop_type`, `request_id`, `user_id`, `passenger_name`, `project_name`, `address`, `zip_code`, `country_code`, `longitude`, `latitude`, `scheduled_time`, `duration_from_previous_seconds`, `distance_from_previous_meters` e `created_at`. O schema tambem passou a impor unicidade por `suggestion_id + vehicle_id + stop_order`, validacao de `stop_type` (`pickup` ou `destination`), validacoes de faixa para latitude/longitude e garantias de nao negatividade para duracao e distancia, mantendo a tabela pronta para servir tanto a exibicao futura por veiculo quanto a trilha de auditoria da sugestao aplicada.

Para materializar esse contrato no banco, foi criada a migration `alembic/versions/0049_add_transport_ai_applied_route_stops.py`, encadeada a partir de `0048_add_transport_ai_route_cache_tables`. A migration cria a tabela `transport_ai_applied_route_stops` com `ForeignKey` para `transport_ai_suggestions.id`, replica todas as `CheckConstraint` e a `UniqueConstraint` usadas pelo model e segue o padrao defensivo desta fase, verificando primeiro se a tabela ja existe antes de tentar criacao ou remocao. Com isso, a cadeia de revisions do backend passou a ter uma estrutura dedicada para armazenar, apos o apply, a sequencia de pickups e destino que o admin aprovou.

Tambem foi criado o modulo `sistema/app/services/transport_ai_applied_route_stops.py`, concentrando o service desta entrega. O arquivo introduz o DTO `TransportAIAppliedRouteStopInput`, a funcao `persist_transport_ai_applied_route_stops` e a funcao `list_transport_ai_applied_route_stops`. O write path recebe uma `TransportAISuggestion` aplicada e uma sequencia de stops, normaliza campos textuais, ordena os registros por `vehicle_id` e `stop_order`, remove qualquer snapshot anterior da mesma sugestao e persiste a nova lista em uma unica transacao controlada pela camada chamadora, sem executar `commit` interno. Isso deixa a persistencia segura para o fluxo de apply real: se qualquer etapa posterior falhar, basta o rollback externo para que a tabela nao retenha stops orfaos.

As validacoes focadas da etapa foram implementadas em `tests/test_transport_ai_applied_route_stops.py`. A suite sobe um SQLite temporario com `alembic upgrade head`, verifica a existencia da tabela e da constraint de unicidade, persiste uma rota com dois passageiros e destino, confirma a ordenacao por `vehicle_id` e `stop_order`, garante que rows de sugestoes distintas nao se misturam e valida que um erro disparado apos a persistencia e antes do commit deixa a tabela vazia depois do rollback. O comando executado foi `pytest tests/test_transport_ai_applied_route_stops.py -q`, concluido com `5 passed`.

### Fase 3 - Services de baseline, restore e reset seguro

#### 3.1 Implementar captura completa de baseline

Esta etapa implementou a captura completa do baseline em `sistema/app/services/transport_ai_runs.py`. O modulo passou a expor a dataclass `TransportAIBaselineCapture`, a funcao `capture_transport_ai_baseline` e o helper `save_transport_ai_baseline`. A captura agora reaproveita `build_transport_operational_snapshot` como fonte canonica do estado visivel no dashboard, registra o ator (`actor_user_id`), a data/rota, o `captured_at`, os settings de transporte usados naquele momento e organiza tudo em tres payloads separados para os campos ja existentes em `transport_ai_runs`: `snapshot_payload`, `assignments_payload` e `vehicle_state_payload`. Tambem foi introduzida a constante de versionamento `TRANSPORT_AI_BASELINE_VERSION = "transport_ai_baseline_v1"`, deixando o baseline autodescritivo para as proximas fases de restore e reset.

O `snapshot_payload` passou a guardar o snapshot operacional completo em modo JSON, junto com os settings retornados por `get_transport_settings_payload`, preservando o shape real do dashboard na data/rota capturada. O `assignments_payload` passou a registrar todos os requests elegiveis presentes no snapshot e todas as `transport_assignments` desses `request_ids` para a `service_date` alvo nas duas direcoes (`home_to_work` e `work_to_home`), incluindo status, veiculo, mensagem, auditoria minima e timestamps. Isso cobre tanto requests com assignment confirmado/rejeitado/pending quanto o caso em que um request elegivel precise ser restaurado para “sem assignment explicito” em fases seguintes. O `vehicle_state_payload` passou a reunir os veiculos relevantes derivados do snapshot e das assignments capturadas, bem como seus schedules e excecoes de schedule para a data do servico, garantindo que o baseline contenha material suficiente para restaurar ou auditar alteracoes futuras de frota.

Para tornar a captura rastreavel e deterministica, os tres payloads sao montados como JSON serializavel com ordenacao canonica e depois assinados por um hash SHA-256 comum (`baseline_hash`). Esse hash passou a ser inserido dentro dos tres blocos do baseline, o que permite verificar consistencia entre `baseline_snapshot_json`, `baseline_assignments_json` e `baseline_vehicle_state_json` mesmo quando eles forem persistidos em colunas separadas. O helper `save_transport_ai_baseline` foi adicionado para gravar esses tres payloads diretamente em uma `TransportAIRun`, atualizar `updated_at` e mover a run para o status `baseline_saved`, preparando o fluxo para a fase seguinte sem exigir que o endpoint monte esses blobs manualmente.

As validacoes focadas desta etapa foram implementadas em `tests/test_transport_ai_baseline_capture.py`. A suite sobe um SQLite temporario com `alembic upgrade head`, cria um cenario deterministico com requests `extra`, assignments `confirmed`, `rejected` e `pending`, veiculos e schedules em `home_to_work` e `work_to_home`, e verifica que o baseline inclui todos os requests elegiveis, que captura assignments das duas rotas quando existirem, que incorpora o estado relevante de veiculos e schedules mesmo quando parte dele so aparece via assignment, que o `baseline_hash` muda quando o estado capturado muda e que os payloads podem ser gravados em `transport_ai_runs.baseline_snapshot_json`, `baseline_assignments_json` e `baseline_vehicle_state_json` por meio do helper de save. O comando executado foi `pytest tests/test_transport_ai_baseline_capture.py -q`, concluido com `3 passed`.

#### 3.2 Implementar restore de baseline

Esta etapa adicionou o restore transacional do baseline no mesmo modulo `sistema/app/services/transport_ai_runs.py`. O arquivo passou a expor `TransportAIBaselineRestoreIssue`, `TransportAIBaselineRestoreAuditEntry`, `TransportAIBaselineRestoreResult` e a funcao `restore_transport_ai_baseline`. O restore foi desenhado para consumir diretamente os blobs gravados na fase 3.1 em `baseline_assignments_json`, reaproveitando `TransportAIRun` como fonte de verdade do rollback e sem introduzir tabelas auxiliares novas. O contrato de retorno agora inclui os `assignment_ids` restaurados, os `assignment_ids` removidos, uma trilha de auditoria com acoes `created`, `updated` e `deleted` e uma lista estruturada de issues bloqueantes quando o baseline nao puder ser reaplicado com seguranca.

O fluxo de restore passou a validar o baseline antes de mutar qualquer dado. A implementacao carrega e valida os payloads persistidos, confere `baseline_version`, verifica consistencia de `baseline_hash` entre os blobs disponiveis e bloqueia o restore se houver corrupcao de JSON, divergencia entre `service_date`/`route_kind` do baseline e da run, requests elegiveis que ja nao existem ou assignments `confirmed` apontando para veiculos ausentes. Se qualquer uma dessas condicoes falhar, a funcao retorna `issues` bloqueantes e nao altera `transport_assignments`. Isso atende o requisito de “issues quando o restore encontrar drift impossivel” sem deixar o banco em estado parcial.

Quando o baseline e valido, `restore_transport_ai_baseline` restaura exatamente o conjunto de assignments explicitos capturado para os requests elegiveis e para a data alvo. Assignments atuais que existem no banco mas nao existiam no baseline sao removidos, cobrindo explicitamente o caso de `pending` criado pelo reset quando antes nao havia assignment explicito. Assignments presentes no baseline sao recriados ou atualizados conforme necessario, preservando `status`, `vehicle_id`, `response_message`, flags de acknowledgement e metadados do payload capturado. Como o algoritmo trabalha por chave `(request_id, route_kind)` e nao toca na tabela `vehicles`, o restore torna-se idempotente e nao remove veiculos manuais criados depois da captura do baseline; ele apenas desfaz o estado de assignments do recorte elegivel.

As validacoes desta etapa foram adicionadas ao arquivo `tests/test_transport_ai_baseline_capture.py`, estendendo a suite focada do baseline. Os novos testes comprovam que o restore devolve assignment `confirmed` ao veiculo original e assignment `rejected` ao estado rejeitado, remove `pending` criado apos a captura quando antes nao havia assignment explicito, permanece idempotente em chamadas repetidas, nao remove veiculo manual criado depois da captura e retorna issue bloqueante sem mutar o banco quando o baseline aponta para um veiculo confirmado que nao existe mais. O comando executado foi `pytest tests/test_transport_ai_baseline_capture.py -q`, concluido com `7 passed`.

#### 3.3 Implementar reset dos passageiros para pending

Esta etapa adicionou o reset seguro de passageiros para `pending` em `sistema/app/services/transport_ai_runs.py` por meio da dataclass `TransportAIResetToPendingResult` e da funcao `reset_transport_ai_requests_to_pending`. O novo fluxo usa o baseline salvo na fase 3.1 como fonte de verdade para descobrir os `eligible_requests` da run, valida a consistencia minima do payload antes de mutar dados e passa a retornar um resultado estruturado com `reset_request_ids`, `reset_assignment_ids`, `issues`, indicacao de emissao de evento e, quando necessario, o resultado do restore automatico disparado em caso de falha. Em caso de sucesso, a funcao atualiza a `TransportAIRun` para `status="passengers_reset"` e grava `updated_at` com o timestamp do reset.

Para cumprir o requisito de reutilizar o motor existente de assignments sem quebrar recorrencias futuras, o write path em `sistema/app/services/transport_assignment_operations.py` foi ajustado para aceitar um escopo explicito de reset pendente. `upsert_transport_assignment_with_persistence` e `_reset_transport_request_assignments_to_pending` agora suportam `pending_reset_scope="service_date_route"`, o que permite ao fluxo da IA colocar o request em `pending` apenas na data/rota alvo da run, em vez de zerar todos os templates explicitos do request. Com isso, requests `regular` e `weekend` continuam preservando materializacao recorrente futura quando existe template confirmado valido, enquanto o dia/rota que acabou de entrar no fluxo da IA volta corretamente para a user list do dashboard atual. Os wrappers equivalentes em `sistema/app/services/transport.py` tambem foram atualizados para espelhar essa nova assinatura.

O reset passou a ser transacional no nivel do service. A implementacao usa `savepoint` interno para aplicar o retorno a `pending` request por request, sem remover veiculos do banco nem alterar supply do dashboard. Se qualquer excecao ocorrer durante esse processo, o savepoint e revertido e `restore_transport_ai_baseline` e chamado automaticamente com o baseline ja salvo, garantindo que o estado de assignments volte ao ponto anterior ao reset antes de o erro subir para a camada chamadora. No caminho de sucesso, o service emite `emit_transport_reevaluation_event` com `event_type="transport_assignment_changed"`, permitindo que o dashboard invalide snapshot e releia a situacao do dia apos o reset.

As validacoes desta etapa foram incorporadas a `tests/test_transport_ai_baseline_capture.py`, que passou a cobrir tambem o fluxo de reset. Os testes novos comprovam que request `extra` confirmado volta para `pending` na rota/data alvo sem remover o veiculo do dashboard, que request `regular` confirmado volta para `pending` sem quebrar a materializacao confirmada de um dia futuro coberto por template recorrente, que request `weekend` confirmado tambem volta para `pending`, e que uma falha no meio do reset dispara restore automatico do baseline e impede emissao do evento de reavaliacao. O comando executado foi `pytest tests/test_transport_ai_baseline_capture.py -q`, concluido com `11 passed`.

### Fase 4 - Provider de mapas e fake provider

#### 4.1 Implementar interface abstrata de provider de rotas

Esta etapa criou o modulo `sistema/app/services/transport_route_provider.py`, que passa a definir a interface interna base do provider de rotas sem acoplamento direto com Mapbox. O arquivo introduziu a classe abstrata `TransportRouteProvider`, com os tres contratos que o restante do sistema podera consumir de forma independente do provider concreto: `geocode`, `get_matrix` e `get_directions`. A interface tambem passou a expor `provider_name`/`provider` como identidade canonica do backend de rotas, preparando a proxima fase para encaixar uma implementacao Mapbox real sem espalhar detalhes de provider por outros services.

No mesmo modulo foram adicionados os DTOs Pydantic que passam a definir o contrato validado entre caller e provider: `TransportRouteCoordinate`, `GeocodeRequest`, `GeocodeResult`, `MatrixRequest`, `MatrixResult`, `DirectionsRequest`, `DirectionsLeg` e `DirectionsResult`. Esses modelos validam coordenadas, textos obrigatorios, profiles, limites simples de listas e o shape das matrizes de duracao/distancia, garantindo que qualquer implementacao concreta entregue objetos coerentes antes de tocar planning, cache ou solver. O contrato tambem ganhou helpers pequenos como `normalized_query`, `as_pair`, `source_pairs`, `destination_pairs` e `coordinate_pairs`, facilitando o reuso futuro pelo cache e pelos providers concretos sem duplicar normalizacao em cada call site.

Esta fase tambem introduziu a hierarquia de erros tipados do provider: `TransportRouteProviderError` como base comum e as subclasses `TransportRouteProviderAuthError`, `TransportRouteProviderTimeoutError`, `TransportRouteProviderInvalidResponseError`, `TransportRouteProviderNoRouteError` e `TransportRouteProviderNoResultError`. Todos esses erros agora carregam `provider`, `operation` e `status_code` opcional, deixando o contrato pronto para distinguir falha de autenticacao, timeout, resposta invalida, ausencia de rota e ausencia de resultado de geocode de forma tratavel pelo fluxo de IA e pela futura camada de observabilidade.

As validacoes desta etapa foram implementadas em `tests/test_transport_route_provider.py`. A suite criou um fake provider local que herda `TransportRouteProvider` e comprovou o contrato abstrato ponta a ponta para geocode, matrix e directions, validou serializacao e round-trip Pydantic dos DTOs com payloads aninhados e confirmou que geocode sem resultado levanta `TransportRouteProviderNoResultError` com `provider` e `operation` tipados corretamente. O comando executado foi `pytest tests/test_transport_route_provider.py -q`, concluido com `3 passed`.

#### 4.2 Implementar Mapbox provider

Esta etapa expandiu `sistema/app/services/transport_route_provider.py` com a implementacao concreta `MapboxTransportRouteProvider`, mantendo o contrato abstrato criado na fase 4.1 e reutilizando o `Settings` ja existente em `sistema/app/core/config.py`. O provider passou a aceitar `httpx.Client` injetavel para testes e, quando nao recebe um cliente externo, cria um cliente proprio com `base_url` da API Mapbox e timeout baseado em `mapbox_timeout_seconds`. O fluxo de autenticacao ficou centralizado em um guard local que exige `mapbox_access_token` antes de qualquer request HTTP, de forma que token ausente falha imediatamente com `TransportRouteProviderAuthError` e sem tocar a rede.

O metodo `geocode` foi ligado ao endpoint `/geocoding/v5/mapbox.places/...` com query composta por endereco, ZIP e pais, incluindo `country`, `language`, `limit`, `autocomplete=false` e `permanent` conforme configuracao. O retorno e convertido para `GeocodeResult` usando coordenadas de `center` ou `geometry.coordinates`, preservando `provider_place_id`, `confidence` por `relevance` e o payload bruto em `raw_response_json`. O provider tambem passou a implementar `get_directions` contra `/directions/v5/...`, validando `routes`, `legs`, distancia, duracao e geometria antes de montar `DirectionsResult` tipado.

O metodo `get_matrix` foi implementado sobre `/directions-matrix/v1/...` com chunking por perfil. A regra ficou centralizada em helpers locais que limitam `mapbox/driving-traffic` a 10 coordenadas e os demais perfis `driving` a 25 coordenadas por request, escolhendo automaticamente tamanhos de blocos de origem e destino que minimizam o numero total de chamadas sem ultrapassar o teto de coordenadas. Cada tile retornado pela Matrix API e remontado em uma unica `MatrixResult` final. Respostas com `code="NoRoute"` ou com qualquer celula `null` em `durations` ou `distances` agora levantam `TransportRouteProviderNoRouteError`, deixando o caller livre para transformar isso em issue de planejamento na fase seguinte sem aceitar matriz parcial silenciosamente.

O tratamento de erros HTTP ficou sanitizado no proprio provider: nenhuma mensagem de excecao inclui URL completa ou `access_token`, evitando vazamento do token em logs ou traces. `401/403` sao mapeados para `TransportRouteProviderAuthError`, timeouts do `httpx` sao convertidos para `TransportRouteProviderTimeoutError` respeitando `mapbox_max_retries`, erros de transporte sem resposta ou payloads JSON invalidos/fora do shape esperado viram `TransportRouteProviderInvalidResponseError`, e ausencia de features no geocoding continua gerando `TransportRouteProviderNoResultError`.

As validacoes desta etapa foram adicionadas a `tests/test_transport_route_provider.py`, que passou a cobrir o provider Mapbox com `httpx.MockTransport`. A suite agora valida geocoding bem-sucedido, matrix bem-sucedida com chunking real para `mapbox/driving-traffic`, falha controlada quando a matrix retorna celula `null`, ausencia de token sem qualquer chamada HTTP e timeout convertido para erro tipado apos retry configurado. O comando executado foi `pytest tests/test_transport_route_provider.py -q`, concluido com `8 passed`.

#### 4.3 Implementar fake provider deterministico

Esta etapa expandiu `sistema/app/services/transport_route_provider.py` com a implementacao concreta `FakeTransportRouteProvider`, pensada para testes automatizados e uso local sem custo externo ou dependencia de rede. O provider passou a suportar geocode, matrix e directions dentro do mesmo contrato abstrato da fase 4.1, sem usar `httpx` nem qualquer chamada real de API. Para isso, o modulo ganhou tambem o model `FakeTransportRouteCatalogEntry` e o catalogo publico `DEFAULT_FAKE_TRANSPORT_ROUTE_CATALOG`, contendo enderecos de fixture ja usados pelo repositorio, como `10 Bayfront Avenue`, `25 Raffles Place`, `80 Robinson Road` e `1 Marina Boulevard`, todos com coordenadas fixas, `provider_place_id` fake e confianca deterministica.

O comportamento de geocoding do fake provider ficou dividido em dois caminhos. Quando o endereco normalizado existe no catalogo, o provider retorna sempre a mesma coordenada fixa, garantindo repetibilidade real para fixtures conhecidas. Quando o endereco nao existe no catalogo e `allow_synthetic_geocode=True`, o provider gera uma coordenada sintetica mas deterministica a partir de hash SHA-256 da query normalizada, ancorando o ponto em coordenadas base por pais (`SG`, `MY`, `BR`, `CN`, `CL`) para evitar resultados aleatorios globais. Quando `allow_synthetic_geocode=False`, o fake provider passa a reproduzir o contrato de ausencia de resultado levantando `TransportRouteProviderNoResultError`, o que manteve a suite abstrata de 4.1 valida mesmo com a chegada do provider fake real.

O calculo de matrix e directions passou a ser deterministicamente derivado das coordenadas de entrada, sem qualquer dependencia de provider externo. A matrix usa uma formula simples e reproduzivel baseada em delta absoluto de longitude/latitude para calcular `distance_meters`, e converte isso em `duration_seconds` com velocidades diferentes para perfis `driving` e `driving-traffic`. O provider tambem passou a suportar matrix simetrica ou assimetrica: quando `transport_ai_fake_matrix_asymmetric=false`, `A -> B` e `B -> A` retornam os mesmos valores; quando a flag fica `true`, um bias direcional pequeno e previsivel e aplicado ao calculo, produzindo resultados diferentes por sentido. Em directions, o provider soma deterministicamente as pernas consecutivas, devolve `DirectionsLeg` tipados e produz geometria simples em `geojson`, `polyline` ou `polyline6` em formato fake, suficiente para testes sem depender da codificacao real do Mapbox.

Para permitir uso local por configuracao, `sistema/app/core/config.py` passou a expor `transport_ai_route_provider` com default seguro `"mapbox"` e `transport_ai_fake_matrix_asymmetric` com default `False`, enquanto `.env.example` recebeu os placeholders `TRANSPORT_AI_ROUTE_PROVIDER=mapbox` e `TRANSPORT_AI_FAKE_MATRIX_ASYMMETRIC=false`. No mesmo modulo de provider foi criado o factory `build_transport_route_provider`, que resolve por config se a execucao deve instanciar `MapboxTransportRouteProvider` ou `FakeTransportRouteProvider`. Isso deixa o backend pronto para usar o fake provider em ambiente local apenas trocando configuracao, sem esperar as fases posteriores de orchestration.

As validacoes desta etapa foram incorporadas a `tests/test_transport_route_provider.py`, que deixou de usar um fake local ad hoc e passou a exercitar o provider fake real. A suite agora valida o contrato ponta a ponta com `FakeTransportRouteProvider`, garante que um mesmo endereco sintetico retorna sempre a mesma coordenada, confirma distancias e duracoes esperadas para matrix e directions deterministicas, verifica matrix assimetrica quando o fake e habilitado por configuracao via `build_transport_route_provider` e comprova que enderecos de fixture do catalogo retornam as coordenadas fixas previstas. `tests/test_transport_ai_config.py` tambem foi atualizado para cobrir os defaults server-side dos novos campos de configuracao. O comando executado foi `pytest tests/test_transport_route_provider.py tests/test_transport_ai_config.py -q`, concluido com `14 passed`.

### Fase 5 - Input canonico de planejamento

#### 5.1 Implementar preflight operacional de dados

Esta etapa criou o modulo `sistema/app/services/transport_ai_planning.py` e introduziu a funcao `build_transport_ai_preflight_issues`, que passa a montar o preflight operacional imediatamente antes das fases de geocode, matrix e solver. A implementacao usa `build_transport_operational_snapshot` e `get_transport_settings_payload` como fontes canonicas, valida coerencia entre `service_date`/`route_kind` solicitados e o snapshot carregado, separa os requests por `regular`, `weekend` e `extra`, e considera elegiveis apenas passageiros com `assignment_status="pending"`. Quando nao ha passageiros pendentes aplicaveis para a data e rota selecionadas, o fluxo retorna a issue estavel `no_eligible_requests` com `blocking=false`, permitindo ao frontend informar a situacao sem tratar isso como falha operacional.

O preflight novo passou a validar dados obrigatorios no nivel certo de granularidade. Para passageiros elegiveis, ele gera issues bloqueantes por passageiro quando faltam `projeto`, `end_rua` ou `zip`, com codigos estaveis como `request_project_missing`, `request_origin_address_missing` e `request_origin_zip_missing`. Para destinos, ele agrega requests por projeto e valida se o projeto existe no snapshot e se possui `address`, `zip_code` e `country_code`, produzindo issues bloqueantes como `project_missing`, `project_destination_address_missing`, `project_destination_zip_missing` e `project_country_missing`, com mensagens legiveis que ja informam o projeto afetado e quantos passageiros elegiveis foram bloqueados.

As validacoes de custo e capacidade ficaram limitadas aos tipos de veiculo realmente candidatos no escopo em uso. O algoritmo inspeciona apenas veiculos `is_ready_for_allocation=true` das listas que possuem requests pendentes e, para cada tipo encontrado (`carro`, `minivan`, `van`, `onibus`), exige configuracao valida de `default_*_seats` e `default_*_price` em `get_transport_settings_payload`. Isso introduziu codigos estaveis como `default_car_price_missing` e `default_car_seats_invalid`, evitando bloquear por tipos que nem entram como candidatos no recorte atual, mas impedindo a roteirizacao quando um tipo pronto para alocacao nao tem custo ou capacidade default coerentes.

As validacoes desta etapa foram adicionadas em `tests/test_transport_ai_planning.py`. A suite cobre exatamente os cenarios pedidos para a fase: ausencia de preco de carro quando existe `carro` candidato, projeto sem endereco de destino, passageiro sem `end_rua`, passageiro sem `zip` e data sem requests elegiveis retornando issue informativa. O comando executado foi `pytest tests/test_transport_ai_planning.py -q`, concluido com `5 passed`.

#### 5.2 Montar `TransportAgentPlanningInput`

Esta etapa expandiu `sistema/app/schemas.py` com o contrato canonico de planejamento que sera reutilizado pelas proximas fases. Foram adicionados `TransportAgentPlanningInput`, `TransportAgentPlanningLimits`, `TransportAgentPlanningSettings`, `TransportAgentPlanningVehicleTypeConfig`, `TransportAgentPlanningRequest`, `TransportAgentPlanningVehicle` e `TransportAgentPlanningPartition`. O schema agora materializa, de forma validada por Pydantic, a data e rota da execucao, o `snapshot_key`/`captured_at` de origem, os limites operacionais (`earliest_boarding_time`, `arrival_at_work_time`, `max_passengers_per_run`, `max_runtime_seconds`), as configuracoes de custo/capacidade por tipo de veiculo e os subconjuntos estruturados de requests, veiculos candidatos e particoes de planejamento. O contrato tambem passou a carregar `preflight_issues`, `total_requests`, `total_candidate_vehicles` e um `planning_input_hash` deterministico em hexadecimal, preparado para auditoria e persistencia em `transport_ai_runs`.

No service `sistema/app/services/transport_ai_planning.py` foi implementado o builder `build_transport_agent_planning_input`. O fluxo reaproveita `build_transport_operational_snapshot`, `get_transport_settings_payload` e o preflight da fase 5.1 para montar o input a partir de fontes canonicas do backend, sem reconsultas paralelas ou contratos ad hoc. O builder passou a filtrar apenas requests `pending` cuja `service_date` real coincide com a data selecionada, o que corrige um detalhe importante do dashboard: requests recorrentes visiveis podem aparecer no snapshot com `service_date` futura para efeito de UI, mas nao devem entrar no problema de roteirizacao do dia atual. Depois desse filtro, o input agrupa requests validos por escopo (`regular`, `weekend`, `extra`), cria particoes por `request_kind + project + country_code`, referencia o projeto de destino de cada particao e indexa apenas veiculos `is_ready_for_allocation=true` como candidatos por lista.

O builder tambem passou a normalizar custo e capacidade no proprio input. Para cada tipo suportado (`carro`, `minivan`, `van`, `onibus`), o payload de settings agora carrega `default_capacity`, `default_price` e os nomes das configuracoes fonte (`default_*_seats`, `default_*_price`). Para veiculos existentes candidatos, o input registra tanto a capacidade real (`effective_capacity`, vinda de `vehicle.lugares`) quanto o contexto default do tipo (`default_capacity` e `default_price`), alem de `assigned_count`, `schedule_id`, `departure_time`, `pending_fields` e `service_scope`. Isso deixa o solver deterministico da fase 6 com todos os dados essenciais para comparar manter veiculos atuais versus criar alternativas novas, sem precisar recalcular ou reinterpretar settings.

O hash deterministico do input foi implementado no mesmo modulo por meio de serializacao JSON canonica com `sort_keys=True` e SHA-256 sobre o payload Pydantic sem o proprio campo `planning_input_hash`. Com isso, alteracoes em endereco, preco ou horarios operacionais passam a modificar o digest de forma previsivel. Para completar o requisito de persistencia, `sistema/app/services/transport_ai_runs.py` recebeu o helper `save_transport_ai_planning_input`, que grava `planning_input_json` e `planning_input_hash` diretamente em `TransportAIRun`, atualiza `price_currency_code`, `price_rate_unit` e `updated_at`, e deixa a run pronta para polling, auditoria e aplicacao futura sem exigir que o endpoint monte esses campos manualmente.

As validacoes desta etapa foram incorporadas a `tests/test_transport_ai_planning.py`. A suite nova comprova que o input inclui apenas requests aplicaveis a data real, separa corretamente `regular`, `weekend` e `extra`, cria particoes distintas para projetos diferentes, embute preco e capacidade por tipo no payload de settings e nos veiculos candidatos, altera o hash quando endereco, preco ou horario mudam e persiste o JSON/hash da estrutura em `transport_ai_runs` por meio do helper novo. O comando executado foi `pytest tests/test_transport_ai_planning.py -q`, concluido com `10 passed`.

#### 5.3 Resolver e validar route points

Foi implementado em `sistema/app/services/transport_ai_planning.py` o fluxo `resolve_transport_ai_route_points`, que recebe o `TransportAgentPlanningInput`, resolve geocoding de origem de passageiros e destino de projeto por particao e devolve um resultado estruturado com os pontos resolvidos e as issues produzidas nessa etapa. O contrato retornado foi formalizado em `sistema/app/schemas.py` por meio dos novos modelos `TransportAgentResolvedRoutePoint`, `TransportAgentResolvedRoutePointsPartition` e `TransportAgentResolvedRoutePointsResult`, mantendo o hash do planning input, a lista de particoes resolvidas e o total de pontos validos gerados para as fases seguintes.

A implementacao passou a integrar diretamente com o cache existente de route points. Antes de chamar o provider, o resolver consulta `get_cached_transport_ai_route_point`; quando nao encontra entrada valida, faz `geocode` com o provider configurado e persiste apenas resultados aprovados via `upsert_transport_ai_route_point`. Para evitar chamadas repetidas e sobrescritas desnecessarias do cache no mesmo ciclo, a rotina introduziu memoizacao in-memory por `provider + country_code + normalized_query`, reaproveitando lookup positivo ou negativo para enderecos duplicados dentro da mesma execucao.

As validacoes desta fase tambem foram centralizadas nesse resolver. Resultados sem geocode geram issue bloqueante `*_geocode_missing`, geocodes com confianca abaixo do limiar operacional (`0.85`) geram issue bloqueante `*_geocode_low_confidence`, e divergencias entre o pais esperado do planejamento e o pais devolvido pelo provider geram issue bloqueante `*_country_mismatch`. Em todos esses cenarios, o passageiro ou destino invalido fica fora da lista de pontos resolvidos, impedindo que coordenadas nao confiaveis avancem para a montagem de matrizes.

Os testes foram adicionados em `tests/test_transport_ai_planning.py` cobrindo os cenarios previstos e um caso extra de baixa confianca: passageiro com endereco valido recebendo coordenada, destino do projeto resolvido, deduplicacao de origem com uma unica chamada ao provider e dois registros reutilizando o cache, pais divergente gerando bloqueio, ausencia de resultado de geocode impedindo a alocacao do passageiro e geocode sintetico de baixa confianca sendo rejeitado. A validacao focada foi executada com `pytest tests/test_transport_ai_planning.py -q -k route_points`, concluindo com `6 passed, 10 deselected`.

#### 5.4 Construir matrizes por particao

Foi implementado em `sistema/app/services/transport_ai_planning.py` o builder `build_transport_ai_route_matrices`, que recebe o resultado de `resolve_transport_ai_route_points`, monta uma matriz all-to-all por particao e devolve um contrato estruturado pronto para o solver das proximas fases. O retorno foi formalizado em `sistema/app/schemas.py` pelos novos modelos `TransportAgentRouteMatrixPartition` e `TransportAgentRouteMatricesResult`, que preservam o `planning_input_hash`, o provider/perfil usados, a lista ordenada de pontos da matriz e as matrizes normalizadas de duracao e distancia por particao.

A implementacao passou a usar diretamente o cache de matrix ja existente em `sistema/app/services/transport_route_cache.py`. Para cada particao com ao menos um passageiro roteavel e um destino valido, o service monta a lista ordenada `passenger_points + destination_point`, consulta `get_cached_transport_ai_route_matrix` com esse conjunto de coordenadas como `sources` e `destinations`, e so chama `provider.get_matrix` quando nao existe cache valido. Quando a resposta vem completa, `upsert_transport_ai_route_matrix` persiste a matriz para reuso futuro. Isso garante que a fase 5.4 respeite o cache por conjunto ordenado de pontos sem duplicar chamada ao provider na mesma combinacao.

As matrizes passaram a ser normalizadas no proprio service para inteiros em segundos e metros, usando arredondamento consistente sobre os valores do provider. O contrato por particao tambem fixa `destination_index` apontando para o ultimo ponto da lista, deixando explicito para as fases seguintes que o destino do projeto participa da matriz e ocupa uma posicao estavel. Para cenarios em que o provider retorna uma matriz com celulas nulas, o builder registra issues bloqueantes `route_matrix_pair_no_route` identificando o par origem/destino sem rota. Para casos em que o provider rejeita a matriz inteira como nao roteavel, o service registra a issue bloqueante `route_matrix_partition_no_route` e devolve uma matriz sentinela com diagonal zero e pares externos nulos, impedindo que o solver trate o particionamento como valido.

Os testes desta etapa foram adicionados em `tests/test_transport_ai_planning.py`. A suite nova comprova que uma particao pequena produz matriz quadrada com valores normalizados, que uma particao acima do limite do profile `mapbox/driving-traffic` continua funcionando por meio do chunking interno do `MapboxTransportRouteProvider`, que uma celula sem rota gera issue bloqueante, que o cache evita uma segunda chamada ao provider para o mesmo conjunto de coordenadas e que o destino de trabalho entra explicitamente como ultimo ponto da matriz. A validacao focada foi executada com `pytest tests/test_transport_ai_planning.py -q -k route_matrices`, concluindo com `5 passed, 16 deselected`.

### Fase 6 - Solver deterministico

#### 6.1 Criar candidatos de frota por particao

Descricao para implementacao: para cada particao, gere candidatos usando veiculos existentes e veiculos virtuais por tipo. Calcule custo, capacidade, penalidade de mudanca e dados necessarios para criar/editar/remover veiculos. Nao misture listas ou projetos.

Entregaveis:

Foi implementado em `sistema/app/schemas.py` o contrato tipado desta fase por meio dos modelos `TransportAgentVehicleCandidatePenaltyConfig`, `TransportAgentVehicleCandidate`, `TransportAgentVehicleCandidatesPartition` e `TransportAgentVehicleCandidatesResult`. Esses schemas passaram a registrar, de forma validada por Pydantic, o `planning_input_hash` da execucao, as penalidades configuraveis da fase 6, a lista de candidatos por particao e, para cada candidato, os campos essenciais para as proximas etapas: origem (`existing` ou `virtual`), `vehicle_id`/`schedule_id` quando existentes, `client_vehicle_key` deterministico para candidatos virtuais, `service_scope`, `route_kind`, tipo do veiculo, capacidade efetiva, capacidade default, custo estimado, penalidades de mudanca e a lista de acoes disponiveis (`keep`, `create`, `update`, `remove_from_day`).

Em `sistema/app/services/transport_ai_planning.py` foi criada a funcao `build_transport_ai_vehicle_candidates`, que recebe o `TransportAgentPlanningInput` da fase 5.2 e devolve um resultado estruturado por particao. A implementacao reutiliza diretamente `partition.candidate_vehicles` para gerar candidatos existentes e `planning_input.settings.vehicle_type_configs` para gerar candidatos virtuais por tipo, sempre restritos ao `request_kind` e ao escopo da particao atual. Para candidatos existentes, a capacidade prioriza `effective_capacity` e so cai para o default do tipo quando necessario; para candidatos virtuais, a capacidade e sempre derivada do default do tipo. Em ambos os casos, o custo estimado vem do preco default configurado para o tipo correspondente.

As penalidades desta fase tambem passaram a ser configuraveis no proprio builder por meio de `TransportAgentVehicleCandidatePenaltyConfig`, com defaults alinhados ao plano funcional: `keep_existing=0`, `create_virtual=50`, `update_existing=100`, `remove_existing_from_day=150` e `change_existing_type=300`. O resultado retornado por `build_transport_ai_vehicle_candidates` preserva essas penalidades no payload final, o que deixa o solver da fase 6.2 pronto para ponderar custo total antes de quantidade de veiculos, duracao, distancia e mudancas operacionais.

O builder foi implementado de forma defensiva para nao promover tipos inviaveis a candidatos. Se um tipo nao tiver `default_price` configurado, ele nao entra nem como candidato virtual nem como candidato existente daquele tipo; se nao houver capacidade positiva valida, o candidato tambem e descartado. Isso garante que o solver seguinte receba apenas uma frota candidata financeiramente e operacionalmente consistente, sem misturar listas ou projetos diferentes e sem carregar tipos que o preflight ja marcou como insuficientes para roteirizacao.

Os testes desta etapa foram adicionados em `tests/test_transport_ai_planning.py`. A suite nova valida que veiculo existente usa `effective_capacity` real, que veiculo virtual usa a capacidade padrao do tipo, que tipo sem preco nao vira candidato, que o candidato existente mantido tem penalidade menor que o candidato virtual criado e que os candidatos de cada particao preservam o `request_kind`/`service_scope` correto sem misturar `extra` e `regular`. A validacao focada foi executada com `pytest tests/test_transport_ai_planning.py -q -k vehicle_candidates`, concluindo com `5 passed, 21 deselected`.

#### 6.2 Implementar solver de custo, capacidade e janela de horario

Foi implementado em `sistema/app/schemas.py` o contrato tipado do resultado do solver desta fase por meio dos modelos `TransportAgentSolvedRoutePassenger`, `TransportAgentSolvedRoute` e `TransportAgentPartitionSolveResult`. Esses schemas passaram a representar, para uma unica particao de planejamento, o algoritmo efetivamente usado (`ortools` ou `heuristic`), as rotas escolhidas, os passageiros em ordem de pickup, os identificadores do candidato/veiculo/unidade utilizados, os custos e penalidades agregados e a lista de `issues` ou `unallocated_request_ids` quando a janela de horario e a capacidade nao permitem uma solucao completa. Com isso, a fase 6.2 passou a devolver um resultado estruturado e validavel por Pydantic, pronto para alimentar as proximas fases de horario retroativo e montagem do plano consolidado.

Em `sistema/app/services/transport_ai_planning.py` foi criada a funcao `solve_transport_ai_partition`, que recebe o `TransportAgentPlanningInput`, a matriz da particao e os candidatos de frota gerados na fase 6.1. A implementacao resolve o problema em duas camadas. Para particoes pequenas, o service constroi subconjuntos viaveis de passageiros, calcula a melhor ordem de pickup por subconjunto, transforma esses subconjuntos em opcoes de rota por veiculo e tenta selecionar a combinacao global com OR-Tools CP-SAT. Quando OR-Tools nao esta disponivel ou nao fecha uma resposta viavel no tempo configurado, o fluxo faz fallback para um solver heuristico deterministico, mantendo o mesmo contrato de saida. O campo `algorithm_used` do resultado registra qual caminho foi usado em cada execucao.

O solver desta fase tambem passou a tratar quantidade de veiculos virtuais como decisao operacional real, e nao apenas como um unico placeholder por tipo. Para isso, os candidatos virtuais da fase 6.1 sao expandidos internamente em unidades temporarias por particao, com `client_vehicle_key` derivado da chave base e sufixos estaveis. Isso permite ao algoritmo comparar corretamente cenarios como “uma minivan” versus “dois carros” e tambem dividir um conjunto de passageiros em mais de um veiculo quando a janela `earliest_boarding_time -> arrival_at_work_time` nao suporta uma unica rota. Veiculos existentes continuam limitados a uma unica utilizacao por particao, enquanto candidatos virtuais podem aparecer em mais de uma unidade temporaria quando o particionamento exigir.

As restricoes duras desta fase foram aplicadas diretamente no solver. Nenhuma rota e considerada viavel se exceder a capacidade do candidato, se algum par da matriz tiver `duration/distance` nulos ou se a duracao total da sequencia de pickups ate o destino ultrapassar a janela disponivel entre `earliest_boarding_time` e `arrival_at_work_time`. A tolerancia operacional do veiculo ou dos settings continua explicitamente fora da funcao objetivo e fora da checagem de viabilidade, conforme o plano funcional. Entre as solucoes viaveis, o algoritmo compara custo total primeiro, depois quantidade de veiculos, depois duracao total, depois distancia total e, por ultimo, penalidade de mudanca operacional, preservando a prioridade de custo definida no documento sem permitir que uma rota barata viole capacidade ou horario.

Os testes desta etapa foram adicionados em `tests/test_transport_ai_planning.py` e cobrem exatamente os cenarios previstos para a secao 6.2. A suite valida que tres passageiros escolhem `carro` quando cabem e o custo e menor, que seis passageiros escolhem `minivan` quando ela e mais barata que dois carros, que o solver divide passageiros em mais de um veiculo quando uma unica rota estoura a janela de horario, que um cenario sem combinacao viavel retorna issue bloqueante `transport_ai_partition_no_solution` e que a tolerancia configurada nao altera a decisao do solver. A validacao focada foi executada com `pytest tests/test_transport_ai_planning.py -q -k solve_transport_ai_partition`, concluindo com `5 passed, 26 deselected`.

#### 6.3 Calcular horarios de pickup de tras para frente

Foi implementado em `sistema/app/schemas.py` o enriquecimento tipado do resultado do solver para suportar horarios operacionais calculados. O modelo `TransportAgentSolvedRoutePassenger` passou a expor o campo opcional `scheduled_pickup_time`, e `TransportAgentSolvedRoute` passou a expor `projected_arrival_time`, ambos normalizados no mesmo formato `HH:MM` usado pelo restante do dominio de transporte. Com isso, a saida da fase 6.2 deixou de carregar apenas ordem de pickup e custo e passou a transportar tambem os horarios que serao exibidos e auditados nas fases seguintes.

Em `sistema/app/services/transport_ai_planning.py` foi criada a funcao `schedule_transport_ai_route_times`, responsavel por receber o `TransportAgentPlanningInput`, a matriz da particao e o `TransportAgentPartitionSolveResult` da fase 6.2 e devolver um resultado atualizado com os horarios da rota calculados de tras para frente. A implementacao fixa a chegada em `arrival_at_work_time`, percorre a ordem de pickup no sentido reverso, soma as duracoes por trecho ate o destino e converte essas duracoes acumuladas em horarios concretos de embarque para cada passageiro. O campo `projected_arrival_time` fica ancorado no horario de chegada escolhido, enquanto cada passageiro passa a carregar o seu `scheduled_pickup_time` correspondente.

O calculo desta fase tambem passou a aplicar arredondamento operacional consistente sobre duracoes em segundos. Em vez de truncar os offsets, o service arredonda cada duracao acumulada para cima no minuto cheio mais proximo antes de converter para `HH:MM`, o que produz horarios conservadores e evita que a exibicao do dashboard prometa pickups mais tarde do que o tempo real suportaria. A mesma funcao tambem recalcula `total_duration_seconds` e `total_distance_meters` da rota a partir da matriz usada no agendamento, mantendo o payload final coerente com os tempos efetivamente usados para derivar os horarios.

As validacoes duras desta fase foram adicionadas diretamente no agendador retroativo. Se algum request da rota nao tiver ponto correspondente na matriz ou se algum trecho da sequencia de pickup tiver `duration/distance` ausente, a funcao registra issue bloqueante de scheduling. Se o primeiro pickup calculado cair antes de `earliest_boarding_time`, a funcao registra a issue bloqueante `transport_ai_route_first_pickup_before_earliest`. Se o caller tentar ancorar a chegada depois do limite configurado, a funcao registra `transport_ai_route_arrival_after_limit`. Em todos esses casos, o resultado final e marcado como inviavel (`is_feasible=False`) sem perder a trilha estruturada das rotas e dos horarios calculados ate o ponto da falha.

Os testes desta etapa foram adicionados em `tests/test_transport_ai_planning.py`. A suite nova valida que uma rota simples calcula os horarios esperados de pickup a partir da chegada fixa, que o primeiro pickup exatamente em `06:50` e aceito, que um pickup calculado para antes de `06:50` gera bloqueio, que uma chegada ancorada apos `07:45` tambem bloqueia e que duracoes em segundos sao arredondadas de forma consistente ao serem convertidas para `HH:MM`. A validacao focada foi executada com `pytest tests/test_transport_ai_planning.py -q -k schedule_transport_ai_route_times`, concluindo com `5 passed, 31 deselected`.

#### 6.4 Montar plano consolidado

Foi implementado em `sistema/app/schemas.py` o contrato consolidado da fase 6.4 por meio dos novos modelos `TransportAgentVehicleAction`, `TransportAgentPassengerAllocation`, `TransportAgentRouteStop`, `TransportAgentVehicleItinerary`, `TransportAgentCostSummary`, `TransportAgentChangeSummaryByVehicleType`, `TransportAgentChangeSummary` e `TransportAgentPlan`. Esses schemas passaram a representar, de forma Pydantic-validavel e serializavel, as acoes de frota sugeridas (`keep` e `create` nesta fase), as alocacoes planejadas de passageiros, os itinerarios completos por veiculo com paradas ordenadas, o resumo de custo atual versus sugerido, o resumo de mudancas agrupado por tipo de veiculo e a lista de `validation_issues` no contrato ja usado pelo fluxo de proposals (`TransportProposalValidationIssue`). A serializacao do plano tambem passou a ser deterministica por meio de `plan_key` derivado de hash do payload consolidado.

Em `sistema/app/services/transport_ai_planning.py` foi criada a funcao `build_transport_agent_plan_from_solver_result`, posicionada logo apos a fase de agendamento retroativo. O builder consome apenas `TransportAgentPlanningInput`, `TransportAgentRouteMatricesResult` e os `TransportAgentPartitionSolveResult` ja enriquecidos pela fase 6.3, sem recalcular solver ou scheduling. A implementacao consolida resultados por particao em quatro saidas principais: `vehicle_actions`, `passenger_allocations`, `route_itineraries` e `validation_issues`. Para a frota, o builder gera uma acao unica por `vehicle_ref`, preservando `vehicle_id` para veiculos existentes e `client_vehicle_key` para veiculos novos. Para passageiros, cada request alocado recebe `vehicle_ref`, ordem de embarque, horario de pickup, horario de chegada e rationale. Para itinerarios, cada rota passa a terminar explicitamente em um stop `destination`, com duracao e distancia acumuladas a partir da matriz da particao.

O resumo financeiro desta etapa tambem foi implementado de forma deterministica no proprio builder. O `current_total_estimated_cost` usa os veiculos existentes candidatos do recorte atual, deduplicados por `vehicle_id` entre particoes que compartilham a mesma lista operacional, enquanto o `suggested_total_estimated_cost` e calculado a partir das acoes de veiculo realmente usadas no plano final. O `change_summary` agrega contagens totais por tipo de acao e tambem uma quebra por `vehicle_type`, o que prepara diretamente a janela `Alteracoes` para exibir o antes/depois de frota. Alem disso, o consolidator passou a emitir issues estruturadas para requests nao alocados, particoes sem resultado, segmentos de matriz ausentes, horarios faltantes e reutilizacao invalida do mesmo veiculo existente em mais de uma rota consolidada.

Os testes desta etapa foram adicionados em `tests/test_transport_ai_planning.py`. A suite nova valida que o plano consolidado cobre todos os passageiros elegiveis em allocations ou issues, que `vehicle_actions` preservam referencias a `vehicle_id` existente ou `client_vehicle_key`, que o resumo de custo atual versus sugerido bate com os veiculos usados, que todos os itinerarios terminam no destino do projeto e que `TransportAgentPlan` serializa e deserializa sem perda. Tambem foi coberto o caminho de falha em que um request inviavel vira `validation_issue` bloqueante por `request_id`. A validacao focada foi executada com `pytest tests/test_transport_ai_planning.py -q -k build_transport_agent_plan_from_solver_result`, concluindo com `2 passed, 36 deselected`. Em seguida, a suite completa de planejamento foi rerodada com `pytest tests/test_transport_ai_planning.py -q`, concluindo com `38 passed`.

### Fase 7 - LangChain e prompt robusto

#### 7.1 Criar prompt versionado do agente

Foi criado o prompt versionado `sistema/app/static/transport/transport_ai_route_planner_v1.md`, atendendo ao pedido de manter o arquivo em uma pasta facilmente editavel pelo time operacional em vez de escondido em uma arvore exclusiva de backend. O texto foi escrito em ingles e estruturado no estilo de um system prompt de `ChatPromptTemplate`, com placeholders explicitos para `prompt_version`, `service_date`, `route_kind`, `earliest_boarding_time`, `arrival_at_work_time`, provider/perfis Mapbox e hash do input. O prompt cobre papel do agente, objetivo primario de custo, tie-breakers operacionais, workflow esperado, contrato de saida, regras de seguranca e proibicao expressa de invencao de dados. Tambem passou a registrar de forma explicita duas regras duras desta entrega: `requested_time` e apenas auditoria nesta fase inicial e a tolerancia do veiculo deve ser completamente ignorada pelo agente.

Em `sistema/app/services/transport_ai_agent.py` foi criada a superficie inicial da fase 7.1. O modulo agora centraliza `TRANSPORT_AI_PROMPT_VERSION = "transport_ai_route_planner_v1"`, a lista canônica de variaveis do template, o caminho do arquivo versionado em `static/transport`, o loader `load_transport_ai_route_planner_prompt`, o builder `build_transport_ai_route_planner_prompt_template` baseado em `langchain_core.prompts.ChatPromptTemplate` e o helper `resolve_transport_ai_model_temperature`, que fixa `0.0` como temperatura preferencial desta integracao. Isso deixa a fase 7.3 preparada para consumir exatamente o mesmo prompt versionado sem duplicar strings, caminhos ou configuracao de temperatura.

Os testes desta etapa foram adicionados em `tests/test_transport_ai_agent_prompt.py` e tambem houve ajuste fino nos testes de persistencia que ja carregavam `prompt_version`. A nova suite garante que o arquivo do prompt existe, que o loader retorna conteudo valido, que o prompt menciona explicitamente a regra de ignorar tolerancia e as janelas de tempo, que o texto nao contem `OPENAI_API_KEY`, `MAPBOX_ACCESS_TOKEN` ou prefixos `sk-`, que o template LangChain compila com as variaveis esperadas e que a configuracao de temperatura permanece em `0.0`. Alem disso, `tests/test_transport_ai_suggestions_model.py` e `tests/test_transport_ai_applied_route_stops.py` deixaram de hardcodear a string da versao e passaram a importar `TRANSPORT_AI_PROMPT_VERSION`, garantindo que a versao persistida no fluxo de sugestoes fique alinhada ao prompt versionado real. A validacao focada foi executada com `pytest tests/test_transport_ai_agent_prompt.py tests/test_transport_ai_suggestions_model.py tests/test_transport_ai_applied_route_stops.py -q`, concluindo com `13 passed`.

#### 7.2 Implementar tools LangChain

Em `sistema/app/services/transport_ai_agent.py` foi expandida a superficie iniciada na fase 7.1 para incluir um toolkit completo de LangChain orientado ao pipeline deterministico ja implementado no backend. O modulo agora expoe `build_transport_ai_langchain_tools`, que monta exatamente as seis tools previstas nesta fase: `load_planning_input`, `geocode_route_points`, `build_route_matrices`, `solve_transport_plan`, `validate_transport_plan` e `build_change_summary`. Para sustentar esse fluxo, tambem foram adicionados `TransportAILangChainToolContext` e `TransportAILangChainToolState`, que mantem em memoria o estado da run atual (`planning_input`, pontos resolvidos, matrizes, resultados por particao e plano consolidado), permitindo que as tools troquem referencias pequenas como `planning_input_hash` e `plan_key` em vez de retransportar matrizes ou snapshots completos entre chamadas.

As tools desta fase foram implementadas como `StructuredTool` do `langchain_core.tools`, cada uma com descricao curta de input/output diretamente no builder para servir como documentacao operacional da superficie. `load_planning_input` encapsula `build_transport_agent_planning_input` e devolve hash, totais e resumo de particoes. `geocode_route_points` encapsula `resolve_transport_ai_route_points`. `build_route_matrices` encapsula `build_transport_ai_route_matrices`. `solve_transport_plan` orquestra `build_transport_ai_vehicle_candidates`, `solve_transport_ai_partition`, `schedule_transport_ai_route_times` e `build_transport_agent_plan_from_solver_result`, devolvendo o `TransportAgentPlan` consolidado junto com um resumo por particao do algoritmo usado. `validate_transport_plan` executa uma validacao deterministica extra sobre o plano em memoria, cobrindo coerencia de `service_date`/`route_kind`, cobertura de requests, duplicidade de allocations, referencias de veiculo e presenca do stop final `destination` em cada itinerario. `build_change_summary` devolve um payload compacto derivado do plano com `objective_summary`, `cost_summary`, `change_summary` e um preview pequeno das acoes de veiculo.

Um detalhe importante desta entrega foi garantir que as tools nao persistam mudancas no banco enquanto servem apenas como superficie de raciocinio para o agente. Para isso, as etapas que normalmente alimentariam caches (`resolve_transport_ai_route_points` e `build_transport_ai_route_matrices`) passaram a ser executadas pelas tools dentro de um `savepoint` descartado ao final (`_transport_ai_tool_read_only_scope`), preservando o resultado em memoria mas revertendo qualquer `upsert` de cache antes de a chamada terminar. Alem disso, os caminhos de erro das tools foram padronizados para sempre retornar `issues` estruturadas (`TransportAILangChainToolIssue`) em vez de deixar excecoes soltas para o agente, cobrindo estado ausente, `planning_input_hash` divergente, `plan_key` divergente e falhas inesperadas de execucao.

Os testes desta etapa foram adicionados em `tests/test_transport_ai_agent_tools.py`. A nova suite valida que o factory retorna exatamente as seis tools esperadas, que `load_planning_input` devolve hash estavel dentro do mesmo contexto carregado, que `geocode_route_points` usa `FakeTransportRouteProvider` e nao persiste `TransportAIRoutePoint`, que `build_route_matrices` monta matriz compacta sem persistir `TransportAIRouteMatrix`, que `solve_transport_plan` devolve um plano deterministico e nao chama `apply_transport_operational_proposal`, que `validate_transport_plan` e `build_change_summary` retornam os resumos esperados a partir do plano consolidado e que chamadas fora de ordem viram `issues` estruturadas com codigos estaveis. A validacao focada foi executada com `pytest tests/test_transport_ai_agent_tools.py -q`, concluindo com `6 passed`.

#### 7.3 Integrar ChatOpenAI com structured output

Implementado o runner `run_transport_ai_agent` em `sistema/app/services/transport_ai_agent.py` como a primeira execucao completa do agente LangChain/OpenAI sobre o pipeline deterministico ja existente. A funcao agora recebe `TransportAIRun`, monta `TransportAILangChainToolContext`, reaproveita os tools da etapa 7.2 para carregar planning input, geocodificar, montar matrizes, resolver o plano e gerar os resumos compactos que entram no prompt. O runner atualiza a `run` para `running` no inicio, sincroniza `planning_input_json`, `planning_input_hash` e `preflight_issues_json` com o estado efetivamente usado, e conclui a execucao marcando `proposed` quando o plano final passa na validacao deterministica ou `failed` quando esgota tentativas ou ocorre erro de execucao.

A integracao com modelo foi implementada com `ChatOpenAI` e structured output Pydantic usando `TransportAgentPlan` via `with_structured_output(..., method="function_calling", include_raw=True)`. Foi adicionada a factory `build_transport_ai_chat_model`, junto de um resultado tipado `TransportAIAgentRunResult`, para permitir injecao de modelo fake em teste e uso do modelo real em runtime. O fluxo agora tenta usar a temperatura preferida resolvida por `resolve_transport_ai_model_temperature`; se a invocacao falhar com erro caracteristico de incompatibilidade com `temperature`, o runner recria o modelo sem temperatura, registra `warning` no logger e grava no payload auditavel que a temperatura foi omitida, sem derrubar a execucao por isso.

Tambem foram adicionados retries controlados especificamente para respostas invalidadas pelo structured output ou pela validacao deterministica posterior. Cada tentativa gera uma mensagem adicional curta explicando ao modelo o motivo do retry. A resposta bruta retornada pelo LangChain passou a ser capturada com serializacao sanitizada em `raw_model_response_json`, removendo chaves e tokens sensiveis conhecidos (`openai_api_key`, `mapbox_access_token`, segredos de sessao/shared keys, `Bearer ...`, padroes `sk-...` e campos com nomes de segredo/token/password`). O ultimo payload bruto sanitizado e retornado mesmo em falha, o que preserva trilha de auditoria sem vazar credenciais.

Foi criada a suite `tests/test_transport_ai_agent_runtime.py` cobrindo exatamente os cenarios pedidos para a etapa: modelo fake retornando plano valido, retry apos resposta invalida, marcacao de `TransportAIRun` como `failed` apos esgotar retries e sanitizacao da resposta bruta. Depois disso, a validacao executada foi `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_agent_runtime.py -q`, com `4 passed`, e em seguida a regressao curta do slice foi confirmada com `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_agent_prompt.py tests/test_transport_ai_agent_tools.py tests/test_transport_ai_agent_runtime.py tests/test_transport_ai_suggestions_model.py tests/test_transport_ai_applied_route_stops.py -q`, com `23 passed`.

#### 7.4 Permitir execucao sem OpenAI para modo deterministico

Foi adicionada a configuracao `transport_ai_agent_mode` ao backend, com default seguro `agent`, exposta em `sistema/app/core/config.py` e documentada em `.env.example` como `TRANSPORT_AI_AGENT_MODE=agent`. A normalizacao do valor ficou centralizada em helper proprio, aceitando apenas `agent` e `deterministic`, o que deixou a feature pronta para fallback operacional sem depender de inferencia espalhada pelo codigo. Com isso, a superficie server-side agora distingue explicitamente o caminho que precisa de OpenAI daquele que deve rodar apenas com o pipeline deterministico interno.

Em `sistema/app/services/transport_ai_agent.py`, o runner `run_transport_ai_agent` passou a resolver o modo configurado antes de construir qualquer modelo OpenAI. Quando `transport_ai_agent_mode=deterministic`, o fluxo nao instancia `ChatOpenAI`, nao monta mensagens LangChain e nao usa structured output do LLM; ele chama diretamente o pipeline deterministico ja existente por meio das rotinas internas de load/geocode/matrix/solve/validate e devolve o mesmo contrato final `TransportAgentPlan`, com o mesmo `TransportAIAgentRunResult`, o mesmo sincronismo de `planning_input_json`/`planning_input_hash` na `TransportAIRun` e a mesma transicao final para `proposed` ou `failed`. Nesse caminho, `raw_model_response_json` permanece `null`, os campos de temperatura ficam vazios e a validacao final continua sendo a mesma `_validate_transport_ai_plan_deterministically`, preservando o contrato operacional da fase 7.3 sem exigir OpenAI.

O preflight server-side tambem foi ajustado em `sistema/app/services/transport_ai_runtime.py` para respeitar o modo configurado. Em `agent`, o comportamento continua exigindo `openai_model` e `openai_api_key`; em `deterministic`, a checagem deixa de bloquear por falta de chave OpenAI, mas continua exigindo provider de rotas, pricing e limites operacionais validos. Isso fecha a correção na raiz: o fallback deterministico nao fica apenas disponivel no runner, ele tambem deixa de ser barrado indevidamente pela validacao de runtime que sera reaproveitada pelos endpoints da fase 8.

Os testes foram atualizados para cobrir exatamente os cenarios prometidos pela secao. `tests/test_transport_ai_config.py` agora valida o default de `transport_ai_agent_mode="agent"`. `tests/test_transport_ai_runtime.py` continua cobrindo que `agent` exige `openai_api_key` e ganhou a verificacao de que `deterministic` aceita configuracao completa sem chave OpenAI. `tests/test_transport_ai_agent_runtime.py` passou a cobrir os dois caminhos do runner: modo `agent` com modelo fake retornando plano valido, modo `deterministic` produzindo `TransportAgentPlan` valido sem chave OpenAI e sem resposta crua de modelo, e modo `agent` falhando explicitamente quando a chave nao esta configurada. A validacao executada para esta etapa foi `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_config.py tests/test_transport_ai_runtime.py tests/test_transport_ai_agent_runtime.py -q`, concluida com `15 passed`, seguida da regressao curta `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_config.py tests/test_transport_ai_runtime.py tests/test_transport_ai_agent_prompt.py tests/test_transport_ai_agent_tools.py tests/test_transport_ai_agent_runtime.py tests/test_transport_ai_suggestions_model.py tests/test_transport_ai_applied_route_stops.py -q`, concluida com `34 passed`.

### Fase 8 - Endpoints backend de IA

#### 8.1 Criar router `transport_ai.py`

Foi criado `sistema/app/routers/transport_ai.py` como um router dedicado para IA com prefixo `/api/transport/ai`, separado do router principal de transporte e protegido no nivel do proprio router por `dependencies=[Depends(require_transport_session)]`, de modo que toda a superficie nova ja nasce exigindo sessao valida de transporte sem repetir a regra em cada endpoint. A primeira operacao exposta nesta fase e `GET /api/transport/ai/preflight`, que reutiliza `validate_transport_ai_runtime_configuration` e responde com o schema Pydantic `TransportAIPreflightCheckResult`, fazendo o OpenAPI publicar tambem `TransportAIPreflightIssue` como contrato formal da verificacao inicial da IA.

`sistema/app/main.py` passou a registrar esse router novo explicitamente, preservando a separacao entre os endpoints de IA e o router legado `transport.py`. A cobertura focada foi adicionada em `tests/test_transport_ai_router.py` com um teste de integracao isolado em subprocesso para evitar acoplamento com o estado global do app em memoria: ele valida que `GET /api/transport/ai/preflight` retorna `401` sem sessao, que o endpoint passa a responder `200` apos autenticacao via `POST /api/transport/auth/verify`, e que `/openapi.json` inclui tanto o path novo quanto os schemas `TransportAIPreflightCheckResult` e `TransportAIPreflightIssue`. A validacao executada para esta etapa foi `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_router.py -q`, concluida com `1 passed`, seguida da regressao curta `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_config.py tests/test_transport_ai_runtime.py tests/test_transport_ai_agent_prompt.py tests/test_transport_ai_agent_tools.py tests/test_transport_ai_agent_runtime.py tests/test_transport_ai_suggestions_model.py tests/test_transport_ai_applied_route_stops.py tests/test_transport_ai_router.py -q`, concluida com `35 passed`.

#### 8.2 Implementar `POST /api/transport/ai/route-calculations`

Foi implementado `POST /api/transport/ai/route-calculations` em `sistema/app/routers/transport_ai.py` como a primeira operacao efetiva de `Solicitar Rotas`, mantendo o fluxo em execucao sincrona controlada nesta fase. O endpoint agora exige sessao de transporte, valida o preflight de runtime antes de qualquer mutacao, cria a `TransportAIRun` com `run_key` proprio, garante um ator persistivel em `admin_users` por meio do helper `ensure_transport_ai_actor_admin_user`, captura e salva o baseline completo com `capture_transport_ai_baseline`/`save_transport_ai_baseline`, reseta os requests elegiveis para `pending` com `reset_transport_ai_requests_to_pending`, reconstrói o `TransportAgentPlanningInput` ja no estado pos-reset, persiste esse input em `planning_input_json`/`planning_input_hash` e, quando o planejamento fica valido, executa `run_transport_ai_agent`. Ao final, quando o agente produz um plano valido, o backend passa a persistir a primeira sugestao real da IA por meio do helper novo `create_transport_ai_suggestion_from_plan`, que serializa `TransportAgentPlan`, actions, itinerarios, resumo financeiro e issues para `transport_ai_suggestions` e devolve `suggestion_key` junto do `run_key` no `TransportAgentRunStartResponse`.

Para sustentar o endpoint, `sistema/app/schemas.py` ganhou `TransportAgentRouteRequest` com validacao de horario `HH:MM`, obrigatoriedade temporaria de `route_kind="home_to_work"` e regra `earliest_boarding_time < arrival_at_work_time`, alem de `TransportAgentRunStartResponse`, que padroniza sucesso e falha com `run_key`, `suggestion_key`, `status`, `issues`, `can_cancel_restore` e `suggestion_ready`. Em `sistema/app/services/transport_ai_runs.py` foram adicionados os helpers `ensure_transport_ai_actor_admin_user` e `create_transport_ai_suggestion_from_plan`, resolvendo respectivamente o acoplamento entre sessao de transporte (`users`) e o FK de auditoria em `transport_ai_runs.actor_user_id`/`assigned_by_admin_id` (`admin_users`), e a persistencia consistente da sugestao gerada no fim da execucao. O lifecycle completo previsto para a fase passou a existir de fato no start endpoint: `requested -> baseline_saved -> passengers_reset -> running -> proposed` em sucesso, e `requested -> baseline_saved -> passengers_reset -> failed` em falha. A superficie tambem passou a emitir os eventos de refresh exigidos: o reset continua emitindo `transport_assignment_changed`, e a sugestao pronta agora emite `transport_operational_review_changed`; quando ha erro depois do reset e o baseline e restaurado automaticamente, o backend emite um novo `transport_assignment_changed` informando o restore.

As validacoes desta etapa foram adicionadas em `tests/test_transport_ai_route_calculations.py`. A nova suite cobre que preflight de runtime falho retorna `409` sem criar `TransportAIRun` e sem mexer no assignment confirmado; que a execucao bem-sucedida salva os tres blobs de baseline na run, deixa o assignment do passageiro em `pending`, cria `TransportAISuggestion` com `suggestion_key` real e emite eventos de reset e review; e que uma falha sintetica depois do reset marca a run como `failed`, nao cria sugestao e restaura automaticamente o baseline, recolocando o assignment confirmado no veiculo original. A validacao executada para esta etapa foi `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_route_calculations.py -q`, concluida com `3 passed`, seguida da regressao curta `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_config.py tests/test_transport_ai_runtime.py tests/test_transport_ai_agent_prompt.py tests/test_transport_ai_agent_tools.py tests/test_transport_ai_agent_runtime.py tests/test_transport_ai_suggestions_model.py tests/test_transport_ai_applied_route_stops.py tests/test_transport_ai_router.py tests/test_transport_ai_route_calculations.py -q`, concluida com `38 passed`.

#### 8.3 Implementar polling de run

Foi implementado `GET /api/transport/ai/route-calculations/{run_key}` em `sistema/app/routers/transport_ai.py` como o endpoint de polling do run iniciado pela fase 8.2. O endpoint agora localiza a `TransportAIRun` por `run_key`, retorna `404` quando ela nao existe e, quando a run e encontrada, agrega o estado persistido da execucao com a ultima sugestao associada a esse `run_id` por meio do helper novo `get_latest_transport_ai_suggestion_for_run`, adicionado em `sistema/app/services/transport_ai_runs.py`. O response passa a desserializar `agent_plan_json` para `TransportAgentPlan` quando ha sugestao persistida, combinar as issues de `preflight_issues_json` da run com as `validation_issues` do plano salvo e calcular as flags de acao que o frontend vai usar na janela de progresso/review: `suggestion_ready`, `can_save`, `can_apply` e `can_cancel_restore`. Tambem foram adicionadas mensagens de status estaveis por lifecycle (`requested`, `baseline_saved`, `passengers_reset`, `running`, `proposed`, `saved`, `applied`, `cancelled`, `failed`), com reaproveitamento de `error_message` em falhas reais e fallback especifico quando a sugestao existe mas o payload salvo nao pode ser desserializado.

Para sustentar esse polling com contrato proprio, `sistema/app/schemas.py` passou a expor `TransportAgentRunIssue`, `TransportAgentRunSuggestion` e `TransportAgentRunStatusResponse`. O novo response inclui `run_key`, `service_date`, `route_kind`, `status`, `message`, `issues`, timestamps da run, `suggestion_key`, o objeto `suggestion` quando disponivel e as flags operacionais citadas acima. As issues de polling deixaram de depender apenas de falhas imediatas do endpoint: o helper `save_transport_ai_planning_input`, em `sistema/app/services/transport_ai_runs.py`, agora tambem persiste `planning_input.preflight_issues` em `transport_ai_runs.preflight_issues_json`, o que permite ao polling reexibir warnings e bloqueios que surgiram durante a preparacao do run, mesmo depois do retorno inicial do `POST /route-calculations`.

As validacoes desta etapa foram adicionadas em `tests/test_transport_ai_router.py`, mantendo a estrategia de subprocesso isolado para nao herdar estado global do app entre arquivos de teste. A suite agora cobre cinco pontos do router: `GET /preflight` continua exigindo sessao e o OpenAPI publica os novos schemas; `GET /route-calculations/{run_key}` retorna `404` para run inexistente; uma run em `running` responde sem sugestao e com flags de acao desligadas; uma run em `proposed` devolve a sugestao desserializada, agrega a issue de preflight com a issue de validacao do plano e liga `can_save`, `can_apply` e `can_cancel_restore`; e uma run em `failed` retorna `ok=false` com mensagem de erro controlada sem expor stack trace. A validacao focada executada para esta etapa foi `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_router.py -q`, concluida com `4 passed`.

#### 8.4 Implementar latest/save/cancel/apply

Foi implementado o ciclo completo de review da sugestao em `sistema/app/routers/transport_ai.py` com quatro endpoints novos: `GET /api/transport/ai/suggestions/latest`, `POST /api/transport/ai/suggestions/{suggestion_key}/save`, `POST /api/transport/ai/suggestions/{suggestion_key}/cancel` e `POST /api/transport/ai/suggestions/{suggestion_key}/apply`. Em vez de inventar um contrato paralelo, os quatro endpoints passaram a reaproveitar `TransportAgentRunStatusResponse`, retornando o mesmo estado agregado usado no polling por `run_key`. Para sustentar esse fluxo, `sistema/app/services/transport_ai_runs.py` ganhou o helper `get_transport_ai_suggestion_by_key`, enquanto o agregador de status do router foi refinado para expor como “ativa” apenas sugestoes em `shown` ou `saved` e para desligar `can_save` e `can_apply` quando houver qualquer issue bloqueante persistida no plano ou no preflight da run.

O `GET /suggestions/latest` agora busca a ultima sugestao ativa por `service_date` e `route_kind`, ignorando naturalmente sugestoes `discarded` e `applied` porque o lookup usa apenas os estados ativos persistidos. O `POST /save` foi implementado como transicao idempotente de `shown -> saved`: se a sugestao ja estiver salva, o endpoint devolve o estado atual sem duplicar efeito; se o payload persistido estiver invalido ou se a sugestao ja tiver saido do lifecycle ativo, o endpoint responde `409` com o mesmo shape de status agregado e mensagem clara. O save atualiza `TransportAISuggestion.status`, `saved_at`, `TransportAIRun.status`, `updated_at`, persiste a transicao com commit proprio e emite `transport_operational_review_changed`, sem alterar assignments nem restaurar baseline.

O `POST /cancel` passou a restaurar o baseline capturado na fase 8.2 de forma transacional, reutilizando `restore_transport_ai_baseline` e o mesmo `AdminUser` shadow criado via `ensure_transport_ai_actor_admin_user` para manter a integridade dos FKs de auditoria. Quando a restauracao e valida, a sugestao e marcada como `discarded`, a run vai para `cancelled`, a resposta volta no formato agregado do polling e o backend emite `transport_assignment_changed` e `transport_operational_review_changed` para forcar refresh do dashboard e da review. Quando a restauracao encontra problemas, o endpoint nao consome a sugestao nem avanca o estado: ele responde `409` com as issues convertidas para o contrato de run status. O cancel tambem foi deixado idempotente para o caso `discarded/cancelled`, retornando o estado final sem repetir mutacoes.

O `POST /apply` foi conectado ao pipeline operacional existente em vez de criar um caminho paralelo de escrita. O endpoint desserializa o `TransportAgentPlan` salvo, valida o payload persistido e, dentro de um `savepoint`, materializa os `vehicle_actions` suportados para a fase atual. `keep` reaproveita o `vehicle_id` existente; `create` passa a gerar um `Vehicle` real com placa temporaria deterministica no formato `AI...`, `tipo` e `lugares` vindos do plano, `tolerance` padrao das configuracoes de transporte e um `TransportVehicleSchedule` `single_date` para a data da sugestao. Com o mapa `vehicle_ref -> vehicle_id` resolvido, o endpoint converte `passenger_allocations` em `TransportProposalDecision`, chama `build_transport_operational_proposal_contract`, `approve_transport_operational_proposal` e `apply_transport_operational_proposal`, e so confirma a transacao quando a proposta chega a `applied` sem issues bloqueantes. Em seguida, persiste os stops aplicados via `persist_transport_ai_applied_route_stops`, atualiza `transport_proposal_json` da sugestao com a proposta aplicada, marca sugestao e run como `applied` e emite `transport_vehicle_supply_changed`, `transport_assignment_changed` e `transport_operational_review_changed`. Se qualquer etapa falhar, o `savepoint` faz rollback completo, evitando veiculos, schedules ou assignments orfaos; `apply` repetido em uma sugestao ja aplicada devolve o estado atual de forma idempotente.

As validacoes desta etapa foram adicionadas em `tests/test_transport_ai_suggestion_commands.py`, novamente em subprocessos isolados para evitar reuse indevido de modulos ja importados pelo app. A suite cobre: `latest` retornando `404` sem sugestao ativa; `save` persistindo a sugestao e permitindo reconsulta por `latest`; `cancel` restaurando o baseline confirmado e sendo idempotente na segunda chamada; e `apply` criando um veiculo novo a partir de uma sugestao com `create`, aplicando o assignment, persistindo `transport_ai_applied_route_stops` e ocultando a sugestao de `latest` depois da aplicacao. Depois da implementacao, a validacao focada `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_suggestion_commands.py -q` concluiu com `4 passed`, e a regressao ampliada `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_config.py tests/test_transport_ai_runtime.py tests/test_transport_ai_planning.py tests/test_transport_ai_agent_prompt.py tests/test_transport_ai_agent_tools.py tests/test_transport_ai_agent_runtime.py tests/test_transport_ai_suggestions_model.py tests/test_transport_ai_applied_route_stops.py tests/test_transport_ai_router.py tests/test_transport_ai_route_calculations.py tests/test_transport_ai_suggestion_commands.py -q` concluiu com `83 passed, 10 warnings`.

### Fase 9 - Aplicacao de vehicle actions

#### 9.1 Implementar apply de criacao de veiculos

Foi implementada em `sistema/app/routers/transport_ai.py` a funcao `apply_transport_ai_vehicle_create_actions`, separando a materializacao de `vehicle_actions` do restante do fluxo de `POST /api/transport/ai/suggestions/{suggestion_key}/apply`. O endpoint deixou de criar `Vehicle` e `TransportVehicleSchedule` manualmente com um `single_date` fixo para todos os casos e passou a resolver cada action `create` por meio do contrato oficial `TransportVehicleCreate` e do service existente `create_transport_vehicle_registration`, que ja concentra as regras de expansao de schedules e validacao operacional usadas pelo cadastro manual do dashboard. Com isso, o apply agora produz o mapa real `client_vehicle_key/new:{client_vehicle_key} -> vehicle_id` antes de converter allocations em `TransportProposalDecision`, mantendo o restante do fluxo de proposal exatamente sobre ids persistidos e nao mais sobre referencias temporarias.

O payload de criacao passou a ser montado por `_build_transport_ai_vehicle_create_payload`, que usa `vehicle_type`, `capacity`, `color` e `plate` salvos em `TransportAgentVehicleAction.after`, aplica placa temporaria deterministica `AI...` quando o plano nao traz uma placa explicita e garante `tolerance` padrao do dashboard para que o veiculo ja nasca alocavel. Para `extra`, o helper continua criando schedule `single_date` com `route_kind` da run e `departure_time` derivado do primeiro horario do itinerario. Para `regular` e `weekend`, como o plano consolidado ainda nao carrega recorrencia completa de longo prazo, foi adotada uma regra explicita e minimamente invasiva: quando a action nao traz flags `every_*`, o apply infere apenas o weekday correspondente a `run.service_date` e cria schedules persistentes `matching_weekday` para os dois sentidos (`home_to_work` e `work_to_home`). Isso substitui o comportamento anterior de forcar `single_date` e, ao mesmo tempo, evita expandir artificialmente um veiculo novo para todos os weekdays ou para todo o fim de semana sem informacao suficiente no plano salvo.

Tambem foi adicionada auditoria explicita das criacoes. Cada veiculo criado agora gera uma entrada serializada em `TransportAISuggestion.change_summary_json` sob `apply_vehicle_create_audit`, contendo `action_key`, `vehicle_ref`, `client_vehicle_key`, `vehicle_id`, placa final, tipo, capacidade, `TransportVehicleCreate` efetivamente aplicado e os schedules realmente persistidos com `route_kind`, `recurrence_kind`, `service_date`, `weekday` e `departure_time`. Isso deixa rastreavel exatamente como a action `create` da sugestao foi transformada em entidade real do backend, sem introduzir migration nova nesta fase e sem misturar essa trilha com a auditoria do proposal de assignments.

As validacoes focadas desta etapa foram implementadas em `tests/test_transport_ai_suggestion_commands.py`. A suite passou a cobrir: `extra` criando veiculo com schedule `single_date`, assignment confirmado, route stops persistidos, auditoria de criacao e presenca do veiculo no dashboard; `regular` criando veiculo com dois schedules `matching_weekday` ancorados no weekday da `service_date`, visivel apenas no dia correspondente do dashboard; `weekend` criando veiculo com schedules `matching_weekday` para o sabado/domingo da run, tambem validando aparicao correta no dashboard; e falha sintetica logo apos `create_transport_vehicle_registration`, comprovando rollback total do `savepoint`, sem veiculo AI persistido, sem schedules criados, sem applied route stops e sem assignment confirmado indevido. Depois da implementacao, a validacao executada foi `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_suggestion_commands.py -q`, concluida com `7 passed`.

#### 9.2 Implementar apply de edicao de veiculos

Foi implementado em `sistema/app/routers/transport_ai.py` o apply de `vehicle_actions` do tipo `update`, sem abrir um caminho de escrita paralelo ao cadastro manual de veiculos. A nova funcao `apply_transport_ai_vehicle_update_actions` percorre as actions persistidas do plano, resolve o `vehicle_id` de cada referencia existente, monta um `TransportVehicleUpdate` a partir de `before/after` do `TransportAgentVehicleAction` e delega a alteracao para o service oficial `update_transport_vehicle_base`. O helper `_materialize_transport_ai_vehicle_actions` deixou de tratar `update` como unsupported e passou a executar essas alteracoes antes da materializacao de `create`, mantendo o restante do apply ancorado no mesmo `savepoint` usado para proposal, assignments e applied route stops.

O payload de update foi centralizado em helpers especificos para evitar mutacao ad hoc de ORM e para manter a semantica igual a do dashboard. `_build_transport_ai_vehicle_update_payload` traduz mudancas sugeridas de `vehicle_type`, `capacity`, `plate`, `color` e `tolerance` para o contrato do service, enquanto `_resolve_transport_ai_default_vehicle_capacity` reaproveita `MobileAppSettings` para preencher `lugares` automaticamente quando o agente muda o tipo do veiculo sem informar capacidade explicita. Tambem foi adicionada auditoria de apply de edicao em `TransportAISuggestion.change_summary_json`, com `apply_vehicle_update_count` e `apply_vehicle_update_audit` registrando `action_key`, `vehicle_id`, `before`, `after`, payload efetivamente aplicado e `changed_fields`, deixando rastreavel como a sugestao salva virou alteracao real na frota.

Os conflitos operacionais passaram a ser tratados como estado esperado de negocio, e nao como erro interno do endpoint. Quando `update_transport_vehicle_base` recusa a alteracao por placa duplicada, tentativa de tornar o veiculo incompleto com uso futuro ou reducao de capacidade abaixo da demanda confirmada, o apply captura o `ValueError`, converte o motivo em `TransportAgentRunIssue` bloqueante com codigo `transport_ai_vehicle_update_conflict` e devolve `409` preservando run/sugestao em estado `proposed/shown`. Como todo o fluxo continua protegido pelo `savepoint`, qualquer falha posterior ao update tambem faz rollback completo do veiculo editado, dos assignments e dos applied route stops, evitando estado parcial mesmo quando a mutacao da base ja ocorreu antes da excecao.

As validacoes desta etapa foram adicionadas em `tests/test_transport_ai_suggestion_commands.py` por meio de fixtures que reescrevem a sugestao persistida para simular `vehicle_actions` `update`, ja que o planner ainda nao emite esse tipo de action automaticamente. A suite agora cobre: atualizacao bem-sucedida de tipo/capacidade/campos base sem recriar schedules; aplicacao de capacidade padrao quando o tipo muda sem `capacity` explicita; bloqueio com `409` quando uma reducao de capacidade conflita com assignments futuros confirmados; e rollback total quando uma etapa posterior ao update falha depois da mutacao do veiculo. Depois da implementacao, a validacao focada `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_suggestion_commands.py -q` concluiu com `11 passed`, e a regressao ampliada `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests -k "transport_ai or transport_vehicle_update" -q` concluiu com `116 passed, 296 deselected, 30 warnings`.

#### 9.3 Implementar remocao do dia

Foi implementado em `sistema/app/routers/transport_ai.py` o fluxo `apply_transport_ai_vehicle_remove_from_day_actions`, integrado ao `POST /api/transport/ai/suggestions/{suggestion_key}/apply` antes das etapas de `update` e `create`, alinhando a ordem efetiva do apply com a politica definida para vehicle actions. A nova materializacao resolve o `vehicle_id` de cada action `remove_from_day`, revalida se o veiculo ainda possui disponibilidade ativa na `service_date` da run e trata drift operacional como issue bloqueante `transport_ai_vehicle_remove_from_day_unavailable` quando o cadastro ja nao pode mais ser removido daquele dia. O helper `_materialize_transport_ai_vehicle_actions` deixou de classificar `remove_from_day` como unsupported e passou a executar a remocao do dia dentro do mesmo `savepoint` que protege proposal, assignments e route stops, garantindo rollback integral se qualquer passo posterior falhar.

A remocao do dia passou a respeitar a semantica correta de cada tipo de schedule sem usar delete destrutivo de registro inteiro. Para schedules recorrentes (`regular`/`weekend`) que ainda se aplicam a `run.service_date`, o apply cria `TransportVehicleScheduleException` por schedule afetado, preservando a recorrencia futura do veiculo e removendo apenas aquela data da disponibilidade operacional. Para schedules `single_date` de `extra`, o apply desativa o schedule (`is_active=False` e `updated_at` atualizado) em vez de apagar o veiculo ou toda a registration, o que remove o veiculo da lista do dia sem destruir historico ou outras estruturas do cadastro. Como actions `remove_from_day` nao alimentam o mapa `vehicle_ref -> vehicle_id` usado na conversao de allocations, qualquer sugestao inconsistente que tente manter passageiros no veiculo removido passa a falhar na fase de materializacao/proposal, impedindo que um veiculo retirado do dia receba assignments por engano.

Tambem foi adicionada auditoria explicita da remocao em `TransportAISuggestion.change_summary_json`. O apply agora grava `apply_vehicle_remove_from_day_count` e `apply_vehicle_remove_from_day_audit`, registrando `action_key`, `vehicle_id`, `service_date`, estado base do veiculo, snapshot dos schedules afetados antes/depois e a lista de `applied_changes` com `change_kind` (`add_exception` para recorrentes e `deactivate_single_date` para extras), inclusive com `exception_id` quando uma excecao de schedule foi criada. Isso deixa rastreavel se a remocao do dia foi realizada por excecao recorrente ou por desativacao de schedule pontual, sem misturar essa trilha com a auditoria de `create`, `update` ou com o proposal de assignments.

As validacoes desta etapa foram adicionadas em `tests/test_transport_ai_suggestion_commands.py` com helpers de fixture que reescrevem a sugestao persistida para simular `vehicle_actions` `remove_from_day`, ja que o planner ainda nao emite esse tipo de action automaticamente. A suite agora cobre: remocao de veiculo `regular` no dia selecionado sem apagar a disponibilidade de um dia futuro; remocao de veiculo `weekend` no sabado atual preservando a recorrencia do sabado seguinte; remocao de veiculo `extra` da data com desativacao do schedule e confirmacao de que o assignment aplicado vai para outro veiculo; e rollback completo quando uma falha posterior ao `remove_from_day` acontece depois da mutacao local, restaurando a disponibilidade do veiculo no dashboard e removendo as excecoes que tinham sido criadas. Depois da implementacao, a validacao focada `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_suggestion_commands.py -q` concluiu com `15 passed`, e a regressao ampliada `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests -k "transport_ai or transport_vehicle_update" -q` concluiu com `120 passed, 296 deselected, 30 warnings`.

### Fase 10 - Conversao e aplicacao de assignments

#### 10.1 Converter plano em proposal decisions

Foi criada em `sistema/app/services/transport_ai_planning.py` a funcao `build_transport_proposal_from_agent_plan`, extraindo do router a responsabilidade de converter `TransportAgentPlan` em `TransportProposalDecision`. A conversao agora resolve `vehicle_ref` com base no mapa `vehicle_id_by_ref` produzido na materializacao das actions de veiculo, cobrindo tanto refs `existing:*` quanto refs `new:*` apos a criacao efetiva dos novos veiculos. O helper tambem passou a detectar allocations duplicadas por `request_id` e refs de veiculo nao resolvidas, retornando `TransportProposalValidationIssue` estruturadas para que o router continue bloqueando o apply antes da fase de proposal quando a sugestao persistida estiver inconsistente.

A conversao deixou de confirmar cegamente qualquer passageiro alocado. Sempre que o plano carrega `validation_issues` bloqueantes vinculadas a um `request_id`, a decisao correspondente passa a ser gerada com `suggested_status="pending"`, sem `vehicle_id`, usando a mensagem da issue como `response_message` e uma `rationale` explicita indicando que o request foi mantido pendente por validacao do plano. Alem disso, quando existe issue bloqueante para um request que nem chegou a aparecer em `passenger_allocations`, a funcao busca o `TransportRequest` no banco para ainda assim emitir uma decision `pending`, garantindo que o proposal reflita corretamente requests problematicos e que o resumo de decisions continue coerente. O router `sistema/app/routers/transport_ai.py` foi ajustado para reutilizar essa funcao durante o apply, convertendo as issues estruturadas de volta para `TransportAgentRunIssue`, enquanto o proposal segue sendo construido com `origin="agent"` no fluxo ja existente.

Foram adicionados testes unitarios em `tests/test_transport_ai_planning.py` cobrindo os cenarios pedidos desta fase: allocation com veiculo existente resolvendo para `vehicle_id`; allocation com veiculo novo usando o id materializado no mapa; request com issue bloqueante sendo convertido para decision `pending` em vez de `confirmed`; e request com issue sem allocation ainda entrando na proposal para que `build_transport_operational_proposal` produza `summary` com contagens corretas e `origin="agent"`. A validacao focada `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_planning.py -k "proposal_from_agent_plan" -q` concluiu com `3 passed, 38 deselected`, e a regressao combinada `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_planning.py tests/test_transport_ai_suggestion_commands.py -q` concluiu com `56 passed`.

#### 10.2 Reutilizar validacao/aprovacao/aplicacao existente

O fluxo de `POST /api/transport/ai/suggestions/{suggestion_key}/apply` em `sistema/app/routers/transport_ai.py` passou a reutilizar de forma explicita o pipeline operacional existente de proposals em tres etapas separadas: `validate_transport_operational_proposal`, `approve_transport_operational_proposal` e `apply_transport_operational_proposal`. Antes desta etapa, o endpoint ja construia e aprovava uma proposal no apply, mas ainda nao chamava a validacao de forma explicita nem persistia na sugestao o estado intermediario real da proposal com seu audit trail completo. Agora, depois de materializar vehicle actions e converter allocations em decisions, o router primeiro cria a proposal com `build_transport_operational_proposal_contract(origin="agent")`, depois executa `validate`, em seguida `approve` e, por fim, `apply`, sempre dentro do mesmo `savepoint` transacional que tambem protege vehicle actions e route stops.

O backend tambem passou a persistir na propria `TransportAISuggestion` o `TransportOperationalProposal` real devolvido por cada etapa do pipeline, em vez de manter apenas o placeholder inicial salvo quando a sugestao e criada. Foi adicionado o carregamento seguro do proposal persistido anterior para usar `replaces_proposal_key` apenas quando a sugestao ja carrega uma proposal operacional real de uma tentativa anterior, evitando tratar o identificador placeholder `transport-ai-proposal:{run_key}` como se fosse uma proposal aplicada de verdade. Quando a validacao bloqueia por drift atual do banco, ou quando a aprovacao/aplicacao falham, o endpoint grava `transport_proposal_json` com a proposal bloqueada e seu `audit_trail` real antes de responder `409`; quando o apply conclui com sucesso, `suggestion.proposal_key` passa a receber a chave real da proposal aplicada e `transport_proposal_json` fica sincronizado com `proposal_status="applied"`, `origin="agent"` e o audit trail completo `generated/validated/approved/applied`.

A etapa tambem consolidou o contrato de review para garantir que sugestao salva ainda nao persiste assignments. Os testes existentes de `save/latest` agora verificam explicitamente que, apos salvar, a suggestion fica em `saved` enquanto o assignment do request continua `pending` e sem `vehicle_id`, provando que a aprovacao e a aplicacao so acontecem quando o admin clica em `Aplicar`. Em `sistema/app/schemas.py`, `TransportAgentRunIssue.source` foi expandido para aceitar `proposal_validation` e `proposal_apply`, permitindo que bloqueios vindos do pipeline de proposal retornem no mesmo contrato de polling/review sem quebrar a resposta do endpoint.

Foram ampliados os testes de `tests/test_transport_ai_suggestion_commands.py` para cobrir os cenarios centrais desta fase. O cenario feliz de apply agora instrumenta o router para provar a ordem `validate -> approve -> apply`, verifica que a proposal persistida na suggestion tem `origin="agent"`, chave real de proposal e audit trail contendo `generated`, `validated`, `approved` e `applied`. Foi adicionado um cenario de drift de request em que o request deixa de estar `pending` antes do apply, bloqueando na validacao com `request_not_pending` e deixando a suggestion em `shown/proposed` com proposal bloqueada persistida. Tambem foi adicionado um cenario de drift de veiculo em que o veiculo existente referenciado pela suggestion deixa de aparecer no snapshot atual, bloqueando com `vehicle_missing_from_snapshot` pelo mesmo pipeline de proposal. Depois dessas alteracoes, a validacao focada `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_suggestion_commands.py -k "save_and_latest or apply_creates_vehicle_assignments_and_route_stops or request_state_drifts or vehicle_availability_drifts" -q` concluiu com `4 passed, 13 deselected`, e a regressao do slice de backend IA `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_route_calculations.py tests/test_transport_ai_router.py tests/test_transport_ai_suggestion_commands.py -q` concluiu com `24 passed`.

#### 10.3 Persistir route stops aplicados

Implementacao concluida reaproveitando a persistencia transacional ja conectada ao fluxo de apply do agente. O endpoint `apply_transport_ai_suggestion` continua montando os registros por meio de `_build_transport_ai_applied_route_stop_inputs`, resolvendo `vehicle_ref` para `vehicle_id` real e copiando `stop_order`, `stop_type`, `request_id`, `user_id`, `passenger_name`, `project_name`, `address`, `zip_code`, `country_code`, `longitude`, `latitude`, `scheduled_time`, `duration_from_previous_seconds` e `distance_from_previous_meters` para `TransportAIAppliedRouteStopInput`. Em seguida, `persist_transport_ai_applied_route_stops` grava esses stops vinculados a `suggestion_id` antes do `savepoint.commit`, mantendo os itinerarios aplicados na mesma transacao de aprovacao/aplicacao da proposta e deixando os dados prontos para exibicao futura.

Nesta etapa o ajuste concreto ficou concentrado na cobertura do fluxo real de apply em `tests/test_transport_ai_suggestion_commands.py`. O cenario feliz passou a validar que os registros persistidos em `transport_ai_applied_route_stops` espelham exatamente os stops do itinerario retornado pela suggestion, incluindo ordem, tipo, endereco, horario, coordenadas, request/user linkage, duracao e distancia. Tambem foi adicionado um teste de rollback que injeta uma falha depois da chamada de persistencia, no passo `set_transport_ai_suggestion_status`, para provar que nenhum stop aplicado, veiculo criado, schedule extra ou assignment confirmado sobrevive quando a mesma transacao do apply e revertida.

Validacoes executadas nesta secao:

1. `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_suggestion_commands.py -k "apply_creates_vehicle_assignments_and_route_stops or rolls_back_applied_route_stops_when_later_step_fails" -q` -> 2 passed.
2. `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_applied_route_stops.py tests/test_transport_ai_suggestion_commands.py -q` -> 23 passed.

### Fase 11 - Frontend do modal de ajustes

#### 11.1 Atualizar markup do modal `Ajustes para o Agente de IA`

Implementacao concluida com a atualizacao do modal em `sistema/app/static/transport/index.html`. O dialogo passou a declarar `aria-describedby` apontando para a nota e para a nova area de feedback, preservando acessibilidade para leitores de tela. Os dois campos de horario agora ja nascem no HTML com `value="06:50"` em `data-ai-agent-earliest-boarding` e `value="07:45"` em `data-ai-agent-arrival-at-work`, o texto explicativo recebeu `id` proprio para ser referenciado pelo dialogo, e foi adicionada uma regiao dedicada `data-ai-agent-feedback` com `role="status"`, `aria-live="polite"` e `hidden` inicial para suportar os estados de erro/progresso da proxima etapa sem precisar redesenhar o markup.

O rodape do modal tambem foi convertido do antigo botao unico `Fechar` para a dupla de acoes prevista nesta fase: um botao `Cancelar` com `data-ai-agent-cancel` e reaproveitamento do hook atual de fechamento do modal, e um botao primario `Solicitar Rotas` com `data-ai-agent-submit`. Para nao quebrar a traducao existente do modal ao introduzir esses novos elementos, `sistema/app/static/transport/app.js` passou a distinguir o botao de cancelar do botao de fechar em `data-close-ai-agent-modal`, enquanto `sistema/app/static/transport/i18n.js` recebeu as novas chaves minimas `ai.agentSettingsCancel` e `ai.agentSettingsSubmit` em todos os idiomas ja suportados. Isso manteve titulo, labels, aria label do botao `×` e novo rodape traduziveis sem ainda entrar na logica de request/polling da secao 11.2.

As validacoes automatizadas desta secao foram adicionadas em `tests/transport_page_date.test.js`. A suite agora verifica que o HTML do modal contem os defaults `06:50` e `07:45`, a nova area `data-ai-agent-feedback`, os botoes `data-ai-agent-cancel` e `data-ai-agent-submit`, e que o JS/I18N expõem hooks dedicados para os novos textos do rodape. A validacao executada foi `node --test tests/transport_page_date.test.js`, concluida com `64 passed`. A verificacao visual manual do modal permaneceu pendente nesta etapa.

#### 11.2 Implementar estado e chamadas de `Solicitar Rotas`

Implementacao concluida concentrando a logica do fluxo em `sistema/app/static/transport/app.js`. O modal de ajustes passou a ter estado proprio para draft, feedback e ciclo da run (`aiRouteRunKey`, `aiRouteRunStatus`, `aiRouteSuggestion`, `aiRoutePollingTimer`, `aiRouteRequestPending` e `aiAgentSettingsDraft`), alem dos helpers `getDefaultAiAgentSettings`, `readAiAgentSettingsDraft`, `validateAiAgentSettingsDraft`, `buildTransportAiRouteCalculationPayload` e `shouldContinuePollingAiRouteRun`. Com isso, os horarios digitados sao sempre lidos do DOM sem perder edicoes parciais, a validacao bloqueia formatos invalidos e janelas onde o embarque mais cedo nao e anterior ao horario de chegada, e o payload enviado ao backend fica alinhado ao contrato de `TransportAgentRouteRequest` com `service_date`, `route_kind`, `earliest_boarding_time` e `arrival_at_work_time`.

`requestAiRoutes` agora faz a submissao real para `POST /api/transport/ai/route-calculations`, marca o modal como ocupado, desabilita os botoes durante a requisicao, reaproveita `requestJson` e `handleProtectedRequestError`, e mostra progresso/erro diretamente em `data-ai-agent-feedback`. Quando o backend devolve `run_key`, o frontend inicia `pollAiRouteRun`, que consulta `GET /api/transport/ai/route-calculations/{run_key}`, reaproveita o mesmo feedback para estados intermediarios, agenda novas consultas por `TRANSPORT_AI_ROUTE_POLL_INTERVAL_MS` enquanto a run ainda estiver ativa e interrompe o ciclo em erro, falha ou sugestao pronta. O fechamento do modal por `Cancelar`, clique no backdrop ou `Escape` continua permitido quando nao ha run ativa, mas passa a ser bloqueado durante request/polling para evitar que o usuario perca o estado no meio da execucao.

O handoff de sucesso tambem foi preparado nesta secao. `sistema/app/static/transport/index.html` ganhou um shell minimo da janela `Alteracoes` (`data-ai-changes-modal`), e `openAiChangesModal` deixou de ser stub: ele fecha o modal de ajustes com `force`, persiste `aiRouteRunStatus/aiRouteSuggestion`, abre a nova janela leve e exibe um resumo de sucesso enquanto a fase 12 ainda nao entrega a UI completa de review/aplicacao. Para suportar os novos estados visuais, `sistema/app/static/transport/styles.css` ganhou o tom `info` em `.transport-modal-feedback[data-tone="info"]`, e `sistema/app/static/transport/i18n.js` recebeu as chaves `ai.agentSettingsSubmitting`, `ai.agentSettingsInvalidTimes`, `ai.changesTitle` e `ai.changesCloseAria` em todos os idiomas suportados.

As validacoes desta secao foram adicionadas e executadas em `tests/transport_page_date.test.js`. A suite cobre defaults e leitura do draft, bloqueio de horarios invalidos, montagem do payload enviado ao start endpoint, regra de continuidade do polling, wiring do submit/cancel, exibicao do feedback e presenca da janela leve de `Alteracoes` no handoff de sucesso. A execucao `node --test tests/transport_page_date.test.js` foi rodada apos as alteracoes e concluiu com `69 passed`.

#### 11.3 Atualizar i18n do fluxo de ajustes

Implementacao concluida consolidando o i18n do fluxo de ajustes em `sistema/app/static/transport/i18n.js` e `sistema/app/static/transport/app.js`. As chaves do modal de ajustes que ja tinham sido introduzidas na 11.1/11.2 (`ai.agentSettingsCancel`, `ai.agentSettingsSubmit`, `ai.agentSettingsSubmitting` e `ai.agentSettingsInvalidTimes`) foram mantidas e verificadas em todos os idiomas suportados, e o fluxo ganhou tambem as mensagens locais que ainda estavam hardcoded em ingles: `ai.agentSettingsReadyForReview` para o handoff de sucesso e `ai.routeCalculationFailed` para o fallback de erro quando o backend nao devolve texto localizado. Essas novas chaves foram adicionadas nas cinco linguas ja suportadas (`en`, `pt`, `zh`, `ms` e `tl`), mantendo o comportamento consistente tanto no modal de ajustes quanto na janela leve de `Alteracoes` aberta ao fim do polling.

No `app.js`, o ajuste principal foi corrigir a raiz do problema de sincronizacao de idioma. O feedback do modal de ajustes e o resumo de sucesso da janela leve de `Alteracoes` deixaram de armazenar apenas strings ja traduzidas em `state` e passaram a aceitar tambem `translation key + values`, por meio dos novos campos `aiAgentFeedbackKey/aiAgentFeedbackValues` e `aiChangesSummaryKey/aiChangesSummaryValues`. Com isso, `syncAiAgentSettingsControls` e `syncAiChangesSummaryCopy` reconstroem o texto ativo com `t(...)` a cada `applyStaticTranslations`, o que faz com que loading, validacao local, fallbacks de sucesso/erro e o resumo inicial do modal de `Alteracoes` acompanhem corretamente a troca de idioma sem exigir nova chamada ao backend. Os caminhos do fluxo `requestAiRoutes` e `pollAiRouteRun` tambem deixaram de depender de fallbacks em ingles e passaram a usar essas chaves locais sempre que nao houver mensagem vinda da API.

Para sustentar a validacao automatizada desta fase, `tests/transport_page_date.test.js` ganhou um loader isolado que inicializa `CheckingTransportI18n` antes de importar `app.js`, evitando o gotcha dos testes Node sem runtime de i18n. A suite agora prova tres pontos pedidos nesta secao: que todas as chaves do fluxo de ajustes existem em todos os idiomas suportados, que a troca de idioma ativo altera de fato os textos de `Cancelar`/`Solicitar Rotas` e demais fallbacks do fluxo, e que o fallback continua seguro quando uma chave inexistente e consultada. O mesmo arquivo tambem verifica estaticamente que `applyStaticTranslations`/`syncAiAgentSettingsControls` continuam conectando os botoes e feedbacks do modal a `t(...)`. Depois dessas alteracoes, a execucao `node --test tests/transport_page_date.test.js` foi rerodada e concluiu com `71 passed`.

### Fase 12 - Frontend da janela `Alteracoes`

#### 12.1 Criar markup e layout da janela `Alteracoes`

Implementacao concluida expandindo o shell minimo da janela `Alteracoes` em `sistema/app/static/transport/index.html` para um modal de review realmente pronto para as proximas fases. O bloco `data-ai-changes-modal` passou a incluir uma hero area de resumo com o feedback/status inicial da sugestao, uma grade de summary cards, uma side note operacional, uma barra de abas com `Summary`, `Vehicles`, `Passengers`, `Routes` e `Audit`, cinco paineis dedicados com `data-ai-changes-vehicles`, `data-ai-changes-passengers`, `data-ai-changes-routes` e `data-ai-changes-audit`, alem do rodape com os botoes `data-ai-changes-cancel`, `data-ai-changes-save` e `data-ai-changes-apply`. A estrutura foi montada para servir como scaffold de renderizacao nas secoes 12.2 a 12.6, sem depender ainda da logica final de troca de abas ou de preenchimento dos dados da suggestion.

O layout responsivo dessa janela foi implementado em `sistema/app/static/transport/styles.css`. A nova classe `.transport-ai-changes-modal` passou a usar largura desktop maior e um corpo em grid, enquanto `.transport-ai-changes-hero`, `.transport-ai-changes-tabs`, `.transport-ai-changes-panels` e `.transport-ai-changes-actions` definem a composicao principal da review. Os paineis usam secoes planas dentro do modal, evitando o padrao de “cards dentro de cards” pedido no documento, e os breakpoints existentes da pagina agora refluem a hero area e os paines para uma unica coluna em telas menores. A barra de abas tambem recebeu `overflow-x: auto` e os botoes de acao passam para coluna unica em mobile, reduzindo o risco de overflow horizontal.

Houve tambem um ajuste local em `sistema/app/static/transport/app.js` para manter compatibilidade entre a janela nova e o handoff de sucesso entregue na fase 11.2. O codigo que atualiza a mensagem inicial do modal deixou de depender exclusivamente de `data-ai-changes-summary` e passou a priorizar `data-ai-changes-status`, com fallback para o seletor antigo. Isso liberou `data-ai-changes-summary` para funcionar como area estrutural do resumo executivo sem quebrar a abertura atual do modal quando a sugestao fica pronta.

As validacoes desta secao foram incorporadas a `tests/transport_page_date.test.js`. A suite agora verifica que o HTML contem os novos `data-*` da janela `Alteracoes` (abas, paineis, areas de conteudo e acoes) e que o CSS expõe os hooks responsivos principais para desktop e mobile, incluindo a largura maior do modal, a grade de paineis em duas colunas no desktop, o colapso para uma coluna em telas menores e o tratamento de overflow horizontal das abas. A execucao `node --test tests/transport_page_date.test.js` foi rerodada apos essas alteracoes e concluiu com `72 passed`. As capturas Playwright desta fase permaneceram pendentes para uma validacao visual posterior.

#### 12.2 Renderizar resumo executivo

Implementacao concluida com a introducao do render executivo real da janela `Alteracoes` no frontend `transport`. Em `sistema/app/static/transport/app.js` foi criado `renderAiChangesSummary`, sustentado por helpers locais para normalizar o payload da suggestion, formatar moeda com `Intl.NumberFormat` respeitando `price_currency_code`, montar comparativos `antes -> depois`, classificar badges de status e transformar `estimated_cost_delta` em estados claros de `Savings`, `Increase` ou `No Change`. O resumo agora consome diretamente `runStatusResponse.suggestion.plan.cost_summary`, `change_summary`, `passenger_allocations`, `route_itineraries` e `validation_issues`, sem reler nem recalcular dados a partir do dashboard atual. Quando `route_provider`, `openai_model`, `prompt_version` ou qualquer outro campo esperado nao vierem no payload, o render passa a expor o placeholder controlado `--` em vez de inventar valores.

O scaffold criado na 12.1 tambem foi completado para receber esse resumo. Em `sistema/app/static/transport/index.html`, o painel `Summary` ganhou o target `data-ai-changes-summary-panel`, e o `app.js` passou a preencher tanto a grade superior `data-ai-changes-summary-grid` quanto o corpo detalhado do painel com objetivo da sugestao, custo atual, custo sugerido, delta de custo, quantidade de veiculos antes/depois, passageiros alocados, issues, janela `earliest_boarding_time -> arrival_at_work_time`, provider/modelo/prompt version e badges para status da run, status da suggestion, route kind e bloqueios. O render tambem foi conectado a `applyStaticTranslations`, de forma que a janela reconstroi esse resumo a partir do estado salvo quando o idioma ativo muda enquanto a suggestion continua carregada.

Para sustentar visualmente esse resumo executivo, `sistema/app/static/transport/styles.css` recebeu estilos novos para notas dos summary cards, objetivo textual do plano, linha de badges, grade executiva de detalhe e estados visuais `success`, `info`, `warning`, `error` e `neutral`. Os textos-chave do resumo passaram a usar `overflow-wrap: anywhere`, e a nova grade executiva colapsa para uma unica coluna em telas menores, reduzindo risco de estouro horizontal em nomes longos, valores monetarios e identificadores de prompt/modelo.

As validacoes desta secao foram adicionadas em `tests/transport_page_date.test.js`. A suite agora cobre um cenario de economia positiva carregado direto da suggestion, um cenario de aumento de custo, o comportamento de placeholders controlados para campos ausentes e a presenca dos hooks estaticos do novo painel de resumo com protecao de wrap no CSS. Depois dessas alteracoes, `node --test tests/transport_page_date.test.js` foi rerodado e concluiu com `75 passed`.

#### 12.3 Renderizar mudancas de veiculos

Implementacao concluida com a criacao de `renderAiVehicleChanges` em `sistema/app/static/transport/app.js`, sustentado por helpers locais para normalizar `runStatusResponse.suggestion.plan.vehicle_actions`, mapear `action_type` para badges (`Add`, `Update`, `Keep`, `Remove From Day`), humanizar `service_scope` e `vehicle_type`, e montar pares `antes -> depois` sem depender do estado atual do dashboard. O renderer agora consome diretamente o payload persistido da suggestion, trata campos ausentes com o placeholder controlado `--`, preserva o baseline de custo em `create` usando `cost_delta` e `estimated_cost`, e gera linhas padronizadas para `Type`, `Seats`, `Identifier`, `List` e `Cost`.

O mesmo renderer tambem passou a classificar mudancas sensiveis. Em vez de destacar apenas remocoes, o frontend agora marca como sensivel qualquer `remove_from_day` e tambem updates estruturais que alteram tipo, capacidade, identificador ou lista operacional do veiculo. Cada item do painel ganhou badges de acao, escopo e `Sensitive Change`, alem de rationale, chave da acao e tom visual coerente com o tipo da mudanca (`success` para create, `warning` para update, `error` para remove e `neutral` para keep). Quando `document` nao existe, `renderAiVehicleChanges` retorna um view model puro, o que permite validacao direta na suite Node sem depender do DOM.

O modal `Alteracoes` foi integrado a esse renderer reaproveitando o target existente `data-ai-changes-vehicles`. Ainda em `sistema/app/static/transport/app.js`, o controlador passou a capturar esse painel, expor `syncAiVehicleChangesRender` e rerenderizar o conteudo salvo sempre que `applyStaticTranslations` reconstrui a janela. Isso mantem o painel `Vehicles` sincronizado com a suggestion atual durante trocas de idioma, assim como ja acontece com o resumo executivo.

Em `sistema/app/static/transport/styles.css`, o painel `Vehicles` ganhou layout proprio com lista densa, cards com cabecalho flexivel, grade interna de campos, destaque visual para mudancas sensiveis e colapso responsivo para uma unica coluna em telas menores. Os novos estilos tambem protegem identificadores, notas e rationale com `overflow-wrap: anywhere`, reduzindo risco de estouro horizontal em placas, chaves temporarias e mensagens longas de justificativa.

As validacoes desta secao foram adicionadas em `tests/transport_page_date.test.js`. A suite agora cobre um `create` renderizado como `Add` com before/after explicito, um `update` exibindo diff de tipo e capacidade, um `remove_from_day` destacado como alteracao sensivel, um `keep` neutro sem aparencia de erro, e ainda verifica os hooks estaticos do novo painel e o colapso responsivo do CSS. Depois dessas alteracoes, `node --test tests/transport_page_date.test.js` foi rerodado e concluiu com `78 passed`.

#### 12.4 Renderizar passageiros e rotas

Implementacao concluida com a criacao de `renderAiPassengerAllocations` e `renderAiRouteItineraries` em `sistema/app/static/transport/app.js`, ambos consumindo diretamente o payload persistido em `runStatusResponse.suggestion.plan` sem recalcular alocacoes a partir do dashboard atual. O renderer de passageiros agora normaliza `passenger_allocations`, cruza cada allocation com `route_itineraries` para resolver identificador do veiculo e contexto da rota, ordena os cards por `pickup_order` e exibe passageiro, projeto, request kind, veiculo, ordem de embarque, horario de embarque e chegada prevista com fallback controlado `--` para campos ausentes. Quando `document` nao existe, o helper retorna um view model puro, preservando a capacidade de validar a logica direto na suite Node.

O mesmo fluxo passou a tratar explicitamente passageiros nao roteados. Em vez de depender de estado transitorio do frontend, o painel `Passengers` deriva essa lista de `validation_issues`, filtrando `request_id` que ainda nao aparecem em `passenger_allocations` e renderizando uma secao separada `Not Routed` com badge de bloqueio ou revisao. Isso cobre o caso pedido no documento em que a suggestion persiste issues de roteamento, mas nao gera alocacao final para determinados requests.

Para as rotas, `renderAiRouteItineraries` agora renderiza cada itinerario persistido por veiculo com cabecalho proprio, campos de projeto/arrival/duration/cost e uma lista ordenada de paradas baseada em `stop_order`. Cada stop exibe horario em `HH:MM`, tipo da parada, titulo, endereco resumido, metadados de projeto/pais e o deslocamento desde a parada anterior. O destino final fica explicitamente marcado com badge e estado visual proprio, garantindo que o ultimo item da rota represente o encerramento do trajeto em vez de uma parada intermediaria qualquer.

O modal `Alteracoes` foi integrado a esses dois renderers com os novos hooks `data-ai-changes-passengers` e `data-ai-changes-routes`, alem de `syncAiPassengerAllocationsRender` e `syncAiRouteItinerariesRender`, que rerenderizam o conteudo salvo sempre que `applyStaticTranslations` reconstrui a janela. Em `sistema/app/static/transport/styles.css`, os paineis `Passengers` e `Routes` receberam listas densas, grids internas para os campos, destaque visual para requests nao roteados, timeline compacta das paradas e colapso responsivo para uma unica coluna em telas menores, reduzindo risco de overflow em nomes, enderecos e identificadores longos.

As validacoes desta secao foram adicionadas em `tests/transport_page_date.test.js`. A suite agora cobre a ordenacao correta por `pickup_order`, a exposicao de requests com issue como `Not Routed`, a preservacao da ordem das paradas do itinerario e a garantia de que cada rota termina no destino. Depois da revisao pos-reinicio, `node --test tests/transport_page_date.test.js` foi rerodado e concluiu com `81 passed`.

#### 12.5 Implementar Cancelar, Salvar e Aplicar

Implementacao concluida em `sistema/app/static/transport/app.js` com a introducao do fluxo completo de comandos da janela `Alteracoes`. O frontend passou a expor os helpers `getTransportAiSuggestionKey`, `buildTransportAiSuggestionCommandUrl`, `shouldRefreshDashboardAfterAiSuggestionCommand` e `resolveAiChangesCommandState`, que resolvem a `suggestion_key` ativa, montam os endpoints `POST /ai/suggestions/{suggestion_key}/save|cancel|apply` e traduzem os flags persistidos do backend (`can_save`, `can_apply`, `can_cancel_restore`) em estado concreto de UI. Sobre essa base foi implementado `runAiSuggestionCommand`, com wrappers explicitos `cancelAiSuggestion`, `saveAiSuggestion` e `applyAiSuggestion`, todos reutilizando `requestJson` e o contrato existente de `TransportAgentRunStatusResponse` em vez de criar um caminho paralelo para a review.

O modal `Alteracoes` passou a ter estado proprio para loading de comandos, por meio de `aiChangesCommandPending` e `aiChangesPendingAction`. Foi criado `syncAiChangesControls`, que desabilita `Cancelar`, `Salvar` e `Aplicar` enquanto uma acao esta em andamento, respeita os flags vindos do backend quando a sugestao pode ou nao pode mais ser salva/aplicada/cancelada, atualiza os rotulos dos botoes para estados como `Saving...` e `Applying...`, e marca o modal com `aria-busy`. O mesmo mecanismo tambem passou a desabilitar o botao `×` e impedir fechamento por `Escape`, clique no backdrop ou chamadas normais de `closeAiChangesModal` enquanto um comando esta pendente, evitando que o usuario esconda a janela no meio de um `save`, `cancel` ou `apply` em voo.

O comportamento final dos tres comandos foi alinhado ao plano funcional. `saveAiSuggestion` chama o endpoint de save, atualiza o estado persistido da suggestion/run e fecha a janela sem disparar refresh do dashboard. `cancelAiSuggestion` e `applyAiSuggestion` fecham a janela e agendam `requestDashboardRefresh({ announce: false })`, o que faz o dashboard recarregar apos restauracao do baseline ou aplicacao da proposta. Em caso de erro, especialmente nos conflitos de apply/cancel devolvidos como `409` com payload estruturado, o frontend agora preserva a janela aberta, atualiza `state.aiRouteRunStatus`/`state.aiRouteSuggestion` com o payload retornado, mostra a mensagem de erro dentro da propria area `data-ai-changes-status` e so usa o footer global como espelho secundario via `handleProtectedRequestError`.

Tambem foram atualizados o i18n e a localizacao de mensagens server-side para esse novo ciclo de review. `sistema/app/static/transport/i18n.js` recebeu, em todos os idiomas suportados, as chaves `changesCancel`, `changesSave`, `changesApply`, `changesCancelling`, `changesSaving`, `changesApplying`, `changesSaved`, `changesCancelled`, `changesApplied`, `changesSaveFailed`, `changesCancelFailed` e `changesApplyFailed`. Em `app.js`, `localizeTransportApiMessage` passou a reconhecer as mensagens principais do backend para suggestion pronta, salva, cancelada e aplicada, evitando que o modal e o footer dependam de strings fixas em ingles quando o backend retorna os textos padrao do router de IA.

As validacoes desta secao foram adicionadas em `tests/transport_page_date.test.js`. A suite agora cobre os novos helpers puros de `suggestion_key`, URL e refresh, verifica estaticamente que os botoes `Cancelar`, `Salvar` e `Aplicar` estao ligados a handlers dedicados com `POST` para os endpoints corretos, confirma que `syncAiChangesControls` realmente usa os flags do backend para desabilitar os botoes e valida que erros de comando continuam ancorados na janela por meio do summary/status do modal. Depois dessas alteracoes, `node --test tests/transport_page_date.test.js` foi rerodado e concluiu com `83 passed`.

#### 12.6 Implementar `IA > Implementar Modifications`

Implementacao concluida em `sistema/app/static/transport/app.js` com a adicao do helper puro `buildTransportAiLatestSuggestionUrl` e do fluxo `loadLatestAiSuggestion`. O novo caminho monta `GET /api/transport/ai/suggestions/latest` a partir da data atualmente selecionada no dashboard (`getCurrentServiceDateIso()`) e do `route_kind` ativo (`getSelectedRouteKind()`), reaproveitando `requestJson` em vez de abrir um canal paralelo para review. Com isso, a opcao `IA > Implementar Modifications` passou a buscar exatamente a ultima suggestion salva do contexto atual de data e rota.

O listener existente do botao `implement-modifications` foi trocado para chamar `loadLatestAiSuggestion`, e o menu de IA continua fechando imediatamente no clique por meio de `closeAiMenu()`. Quando a API devolve uma suggestion valida, o frontend atualiza `state.aiRouteRunKey`, `state.aiRouteRunStatus` e `state.aiRouteSuggestion` com o payload persistido e reabre o modal `Alteracoes` via `openAiChangesModal(response)`, reaproveitando todo o renderer e os controles implementados nas etapas anteriores. Para evitar cliques duplicados enquanto a requisicao esta em voo, o controlador tambem passou a manter `aiLatestSuggestionLoading` e a desabilitar temporariamente esse item do menu em `syncAiMenuControls`.

O caso sem suggestion salva foi tratado explicitamente como um fluxo amigavel de UI, sem transformar `404` em falha genérica. Quando o endpoint `latest` responde `404`, o frontend agora mostra no footer status uma mensagem localizada por `t("ai.noSavedSuggestion")` e nao abre o modal. Para erros reais de carregamento, foi adicionado um fallback dedicado `ai.loadLatestSuggestionFailed`, novamente integrado ao i18n existente em `sistema/app/static/transport/i18n.js` para todos os idiomas suportados.

As validacoes desta secao foram adicionadas em `tests/transport_page_date.test.js`. A suite agora cobre o helper puro que monta a URL do endpoint `latest`, verifica estaticamente que `loadLatestAiSuggestion` fecha o menu, chama `requestJson(latestSuggestionUrl)`, abre `Alteracoes` em caso de sucesso, trata `404` com `ai.noSavedSuggestion` no footer e desabilita o item do menu enquanto o carregamento estiver pendente. Depois dessas alteracoes, `node --test tests/transport_page_date.test.js` foi rerodado e concluiu com `85 passed`.

### Fase 13 - Observabilidade, auditoria e export

#### 13.1 Adicionar logs sanitizados e eventos de dominio

Implementacao concluida com a introducao de uma camada dedicada de observabilidade para o lifecycle da IA de transporte. Foi criado `sistema/app/services/transport_ai_sanitization.py`, que centraliza a sanitizacao de strings e payloads usados pela IA, redigindo segredos conhecidos (`OPENAI_API_KEY`, `MAPBOX_ACCESS_TOKEN`, shared keys, passwords e tokens em formatos como `sk-*` e `Bearer ...`) antes que qualquer texto seja persistido ou serializado. O `transport_ai_agent.py` deixou de manter essa logica isolada no proprio modulo e passou a reutilizar esse service compartilhado, eliminando a duplicacao e garantindo que a mesma regra de redacao valha tanto para `raw_model_response_json` quanto para a nova trilha de auditoria da fase 13.1.

Sobre essa base foi criado `sistema/app/services/transport_ai_observability.py`, que passa a concentrar a instrumentacao do lifecycle em um unico helper: `record_transport_ai_lifecycle_transition`. Esse helper gera mensagens curtas e auditaveis contendo `run_key` e `suggestion_key`, serializa detalhes estruturados em JSON sanitizado e grava a trilha persistente via `log_event` com `source="transport_ai"` e actions curtas o suficiente para respeitar o limite real de 16 caracteres de `CheckEvent.action` (`run_create`, `baseline_save`, `requests_reset`, `suggestion_gen`, `suggestion_save`, `suggestion_drop` e `suggestion_apply`). O mesmo helper tambem passou a emitir o novo evento de dominio `transport_ai_route_calculation_changed`, agora registrado no catalogo de `sistema/app/services/transport_reevaluation_events.py` com `downstream_actions=["refresh_transport_state"]`.

O lifecycle da IA foi ligado a essa nova observabilidade nos pontos que realmente mudam estado. Em `sistema/app/routers/transport_ai.py`, o start do run agora registra audit/event para `run_created`, `baseline_saved` e `suggestion_generated`, enquanto os comandos de review passaram a registrar `suggestion_saved`, `suggestion_discarded` e `suggestion_applied`. Em `sistema/app/services/transport_ai_runs.py`, o reset de passageiros para `pending` passou a registrar `passengers_reset` no mesmo savepoint da mutacao, mantendo a trilha coerente com o que de fato foi confirmado na transacao. Nos caminhos de `POST /api/transport/ai/route-calculations`, tambem foi adicionado `notify_admin_data_changed("event")` apos os commits relevantes para que a nova auditoria persistida fique visivel para os consumidores administrativos do feed de eventos.

As validacoes desta secao foram adicionadas aos testes backend ja existentes em `tests/test_transport_ai_route_calculations.py` e `tests/test_transport_ai_suggestion_commands.py`. A suite agora cobre que o novo evento `transport_ai_route_calculation_changed` e emitido com reasons especificos para `run_created`, `baseline_saved`, `passengers_reset`, `suggestion_generated`, `suggestion_saved`, `suggestion_discarded` e `suggestion_applied`; verifica que os registros persistidos em `CheckEvent` contem `run_key` e `suggestion_key` nos textos/detalhes; e confirma que os segredos de ambiente injetados nos fixtures (`sk-test-openai-token` e `test-mapbox-token`) nao aparecem na trilha auditada. Depois dessas alteracoes, a validacao focada `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_route_calculations.py tests/test_transport_ai_suggestion_commands.py -q` foi rerodada e concluiu com `21 passed`.

#### 13.2 Estender export operacional com sugestao de IA

Implementacao concluida com extensao localizada de `sistema/app/services/transport_exports.py`. O builder `build_transport_operational_plan_export` passou a detectar, apenas quando a proposal exportada tem `origin="agent"`, a `TransportAISuggestion` persistida com a mesma `proposal_key`. A partir desse vinculo foram adicionados helpers pequenos para desserializar com tolerancia os JSONs ja salvos na suggestion (`agent_plan_json`, `vehicle_actions_json`, `route_itineraries_json`, `change_summary_json`, `cost_summary_json` e `validation_issues_json`) sem alterar a assinatura publica do endpoint nem recalcular dados da IA no momento do export.

Quando essa suggestion existe, o workbook agora recebe quatro abas opcionais novas ao final do conjunto legado: `AI Summary`, `AI Vehicle Actions`, `AI Itineraries` e `AI Issues`. A aba `AI Summary` resume metadados da suggestion (chave, status, prompt version e timestamps), objetivo do plano e agregados de custo/mudanca/quantidade de itinerarios e issues. `AI Vehicle Actions` expande cada acao de veiculo com tipo, escopo, referencias e snapshots `before`/`after`. `AI Itineraries` materializa os itinerarios sugeridos em nivel de stop, incluindo `route_key`, `vehicle_ref`, placa, `stop_order`, `stop_type`, passageiro, endereco, horario e metricas de deslocamento. `AI Issues` lista as validacoes originadas pela IA com `code`, `blocking`, `request_id`, `vehicle_id` e mensagem. Para proposals manuais ou sistemicas, e tambem para proposals agent sem suggestion persistida correspondente, o workbook continua exatamente com o shape anterior, preservando a compatibilidade do export legado.

A cobertura foi adicionada em `tests/test_api_flow.py` com um novo teste de integracao que cria uma `proposal` aprovada com `origin="agent"`, persiste uma `TransportAIRun` e uma `TransportAISuggestion` com a mesma `proposal_key`, e valida que o download de `/api/transport/exports/operational-plan` inclui as quatro abas novas e popula corretamente resumo, vehicle action, route stops e issues. Os testes legados de export sem IA permaneceram intactos e continuam fixando o contrato antigo, inclusive a lista exata de abas para proposal manual. A validacao focada executada ao final foi `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k "test_transport_export_endpoint_builds_xlsx_download_and_saves_server_copy or test_transport_operational_plan_export_includes_proposal_review_tabs or test_transport_operational_plan_export_includes_ai_suggestion_tabs_for_agent_proposal or test_transport_operational_plan_export_supports_contract_built_proposal_audit_trail" -q`, com resultado `4 passed`.

#### 13.3 Criar endpoint de diagnostico administrativo da IA

Implementacao concluida com a exposicao de `GET /api/transport/ai/runs` em `sistema/app/routers/transport_ai.py`, reaproveitando a protecao ja existente do router (`dependencies=[Depends(require_transport_session)]`) para manter a superficie acessivel apenas a sessao de transporte/autorizada. O endpoint lista as runs mais recentes ordenadas por `created_at desc`, aceita filtro exato por `service_date`, filtro repetivel por `status` e limite configuravel (`limit`, ate 100), e responde com um contrato proprio em `sistema/app/schemas.py` por meio de `TransportAIRunDiagnosticsEntry` e `TransportAIRunDiagnosticsResponse`. O resumo por run ficou deliberadamente estreito: `run_key`, data, rota, status, timestamps, duracao em segundos, modelo OpenAI, route provider, suggestion associada, `prompt_version`, codigos de issues de preflight/validacao e erro sanitizado. Nenhum blob bruto de `planning_input_json`, `baseline_*`, `agent_plan_json`, `transport_proposal_json` ou `raw_model_response_json` passa a ser exposto pelo endpoint.

Para cobrir o requisito de custo aproximado sem inventar pricing nova no backend, o router ganhou helpers locais que inspecionam a `raw_model_response_json` ja sanitizada da suggestion e extraem apenas hints seguros de uso/custo quando eles realmente existem no payload persistido, como `prompt_tokens`, `completion_tokens`, `total_tokens` e chaves de custo do tipo `estimated_cost_usd`. Esses dados passam a aparecer no diagnostico como `approximate_model_call_cost`, `approximate_model_call_cost_currency` e contadores de tokens, mas o endpoint retorna `null` quando a resposta crua nao carrega esse metadata. A mesma camada tambem sanitiza `error_message` com `sanitize_transport_ai_string` antes de serializar a resposta, garantindo que segredos como `sk-*` e `Bearer ...` nao vazem em mensagens de falha, e reduz a observabilidade exposta a codigos/contagens de issues em vez de prompts ou textos completos com potencial de conter dados pessoais.

A cobertura foi ampliada em `tests/test_transport_ai_router.py`. O smoke test do router/OpenAPI passou a verificar que `/api/transport/ai/runs` esta publicado e que os schemas novos do diagnostico entram no `components.schemas`. Alem disso, foi adicionado um teste de integracao em subprocesso que semeia runs e suggestion persistidas, valida que o endpoint exige autenticacao, lista as runs recentes na ordem esperada, filtra corretamente por `status` e `service_date`, extrai custo/tokens quando a `raw_model_response_json` traz metadata de uso e confirma que a resposta nao devolve `raw_model_response_json` nem segredos/token strings presentes nos dados semeados. A validacao focada executada ao final foi `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_router.py -q`, concluida com `5 passed`.

### Fase 14 - Regressao completa, deploy e rollout

#### 14.1 Ampliar suite automatizada de backend

Implementacao concluida em `tests/test_api_flow.py` com a ampliacao da matriz backend no ponto em que ainda faltava cobertura integrada: o fluxo fim a fim da IA de transporte convivendo com a suite ja existente de `transport_proposal` e `transport_vehicle`. Em vez de criar outro arquivo paralelo, a secao foi fechada no mesmo arquivo que a validacao da fase 14.1 ja exigia, o que permitiu exercitar o contrato real da API com o mesmo banco SQLite compartilhado e com o mesmo app FastAPI usado pelas regressões operacionais anteriores.

Para documentar e estabilizar os fixtures dessa matriz, o arquivo recebeu um conjunto pequeno de helpers dedicados: `_transport_ai_api_regression_timestamp`, `_configure_transport_ai_api_regression_runtime`, `_create_transport_ai_api_regression_vehicle_candidate`, `_create_transport_ai_api_regression_fixture`, `_cleanup_transport_ai_api_regression_fixture`, `_isolate_transport_ai_api_regression_requests` e `_start_transport_ai_api_regression_run`. Esses helpers deixam explicito no proprio teste que a execucao ocorre com `transport_ai_enabled=True`, `transport_ai_agent_mode="deterministic"`, `transport_ai_route_provider="fake"` e `mapbox_access_token` sintético, sem rede externa nem chaves reais. O fixture tambem passa a semear `MobileAppSettings`, projeto, usuario, `TransportRequest` e, quando necessario, uma assignment confirmada de baseline; na limpeza, remove runs, suggestions, applied route stops, veiculos/schedules criados no apply e restaura as configuracoes de transporte.

Sobre essa base foram adicionados tres testes de API que cobrem exatamente os fluxos pedidos pela secao: `test_transport_ai_api_flow_start_suggestion_save_latest_apply`, `test_transport_ai_api_flow_start_suggestion_cancel_restore` e `test_transport_ai_api_flow_apply_blocks_when_request_drifts`. O primeiro valida o ciclo completo `start -> suggestion -> save -> latest -> apply`, incluindo a persistencia final de assignment confirmada, suggestion aplicada e route stops persistidos. O segundo cobre `start -> suggestion -> cancel -> restore`, verificando que o baseline restaurado devolve a assignment original e descarta a suggestion ativa. O terceiro força drift de estado antes do apply e confirma o bloqueio com `409`, mantendo a run em `proposed` e a suggestion em `shown`. Para evitar regressao espuria no `test_api_flow.py`, onde o banco e compartilhado pelo arquivo inteiro, o helper de isolamento passou a cancelar requests ativos nao relacionados antes do start da IA, impedindo que requests recorrentes deixados por testes anteriores contaminem o planning input da run atual.

Com isso, a secao passou a consolidar a camada de API da matriz backend em cima dos testes focados de services e migrations que ja existiam nas fases anteriores, sem duplicar suites paralelas. As validacoes executadas ao final foram `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k "test_transport_ai_api_flow_start_suggestion_save_latest_apply or test_transport_ai_api_flow_start_suggestion_cancel_restore or test_transport_ai_api_flow_apply_blocks_when_request_drifts" -q`, concluida com `3 passed`, e `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k "transport_ai or transport_proposal or transport_vehicle" -q`, concluida com `32 passed`.

#### 14.2 Ampliar suite automatizada de frontend

Implementacao concluida integralmente em `tests/transport_page_date.test.js`, sem alterar o codigo de producao do frontend. A secao foi fechada ampliando a suite Node ja existente com cobertura comportamental do fluxo de IA no dashboard estatico, porque os helpers puros, a validacao estatica de markup/CSS e a verificacao de i18n ja estavam presentes no arquivo e o gap real desta fase era a ausencia de smoke dinamico para inicializacao, abertura dos modais e comandos de revisao. Para isso, o proprio teste passou a incluir um harness local de DOM/fetch/timers com `FakeDocument`, `FakeElement`, `FakeEventTarget`, `createFetchMock`, `createImmediateTimerHarness` e `withTransportPageHarness`, suficiente para carregar `i18n.js` antes de `app.js`, disparar `DOMContentLoaded`, simular `fetch` em `auth/session`, `settings`, `dashboard`, `latest suggestion` e comandos `save/apply/cancel`, e verificar o comportamento real do controller sem depender de `jsdom` nem de browser externo.

Sobre esse harness foram adicionados cinco testes de regressao focados no fluxo novo. O primeiro, `transport ai dashboard bootstrap keeps the new ai elements wired and opens the settings modal with default values`, garante que o dashboard continua inicializando com os elementos de IA presentes e que o modal Ajustes abre com os defaults `06:50` e `07:45`. O segundo, `transport ai implement modifications renders the latest suggestion into the review modal panels`, cobre a abertura da janela Alteracoes a partir do botao `Implement Modifications`, validando render real de resumo, veiculos, passageiros e rotas com payload mockado. Os tres testes restantes, `transport ai save command posts the saved review action without refreshing the dashboard`, `transport ai apply command posts the apply action and refreshes the dashboard` e `transport ai cancel command posts the cancel action and refreshes the dashboard`, exercitam os handlers `Save`, `Apply` e `Cancel` com `fetch` mockado, validando as URLs `POST`, o fechamento do modal, a mensagem de status e o refresh de dashboard apenas nos comandos que realmente devem recarregar a tela.

Com isso, a secao passou a cobrir os requisitos dinamicos pedidos sobre o mesmo arquivo Node exigido pelo plano, preservando tambem a cobertura estatica e de i18n que ja existia para os textos e scaffolds dos modais de IA. O smoke Playwright opcional nao foi adicionado porque o repositorio nao possui configuracao Playwright ativa nem specs existentes para reaproveitamento, e a busca previa nesta fase confirmou essa ausencia; em vez de inventar uma stack paralela so para esta secao, a ampliacao foi mantida no runner Node oficial ja usado pelo projeto. A validacao final executada foi `node --test tests/transport_page_date.test.js`, concluida com `90 passed`.

#### 14.3 Executar validacao manual em preview local

Resumo da implementacao realizada:

1. Foi adicionado o seed reprodutivel `scripts/seed_transport_ai_preview_validation.py` para preparar um banco SQLite isolado com admin bootstrap `HR70`, configuracao minima de transporte e dois cenarios manuais pequenos: um cenario `pending` em `2026-05-04` para validar `save/reopen/apply` e um cenario `confirmed` em `2026-05-05` para exercitar o caminho de restore.
2. O preview local foi executado com `preview_transport_ai_validation.db`, API em `http://127.0.0.1:8011`, `TRANSPORT_AI_ENABLED=true`, `TRANSPORT_AI_AGENT_MODE=deterministic`, `TRANSPORT_AI_ROUTE_PROVIDER=fake`, `FORMS_QUEUE_ENABLED=false` e tokens de teste para Mapbox/OpenAI apenas para satisfazer a inicializacao do runtime.
3. A autenticacao manual em `/transport` foi concluida com `HR70 / eAcacdLe2`, e o fluxo principal foi exercitado no browser real: abertura do modal `AI Agent Settings` com defaults `06:50` e `07:45`, geracao da suggestion, revisao da janela `Changes`, persistencia com `Save`, reabertura via `Implement Modifications` e aplicacao efetiva do plano.
4. O estado operacional apos `Apply` foi confirmado visualmente no dashboard: o request `AI Preview Apply Rider` passou a exibir `Assigned to AI14AP1 | Transport AI suggestion applied.` e o veiculo `AI14AP1` mudou de `0/4` para `1/4`.
5. A validacao manual de `cancel restores baseline` foi concluida com um segundo run no mesmo dia `2026-05-04`, agora partindo do baseline confirmado apos o apply. Durante a review, o dashboard voltou temporariamente para `transport_ai_reset_to_pending` e a ocupacao caiu para `0/4`; ao clicar em `Cancel`, o dashboard retornou para `Assigned to AI14AP1 | Transport AI suggestion applied.` e `AI14AP1 (1/4)`, confirmando o restore do baseline capturado pela run.
6. O artefato de fechamento `docs/fase_ai_14_validacao_manual.md` foi criado com os comandos usados, variaveis de ambiente, cenarios seeded, descricao textual dos estados principais e o checklist manual concluido.
7. Dois problemas apareceram durante a execucao manual e ficaram registrados no documento: o primeiro era do fixture local, porque as chaves `AI14APPLY` e `AI14CANCEL` excediam o limite de 4 caracteres do schema e precisaram ser reduzidas para `A14A` e `A14C`; o segundo foi um erro de plano invalido no cenario secundario de `2026-05-05`, documentado como observacao da validacao, enquanto o fechamento bem-sucedido do `cancel/restore` foi concluido no rerun do baseline confirmado de `2026-05-04`.

#### 14.4 Preparar deploy com feature flag desligada

Descricao para implementacao: prepare o deploy em Digital Ocean com migrations e codigo, mas mantenha `TRANSPORT_AI_ENABLED=false` inicialmente. Valide que o dashboard atual continua funcionando sem chaves de IA. Depois, habilite em janela controlada com chaves reais configuradas no ambiente.

Entregaveis:

1. Checklist de deploy.
2. Migrations aplicadas.
3. Feature flag documentada.
4. Plano de rollback.

Testes e validacoes:

1. Deploy com IA desligada nao quebra `/transport`.
2. Endpoints IA retornam erro controlado quando desligados.
3. Habilitar IA nao exige rebuild de imagem.
4. Rollback remove uso do fluxo IA sem resetar banco.

#### 14.5 Monitorar primeira execucao real

Descricao para implementacao: acompanhe a primeira execucao real em producao com logs e dashboard. Meça tempo de geocoding, tempo de matrix, tempo de solver, tempo do modelo, custo estimado, quantidade de issues e resultado aplicado. Registre ajustes necessarios.

Entregaveis:

1. Relatorio de primeira execucao.
2. Lista de ajustes de prompt/solver.
3. Confirmacao de ausencia de segredos em logs.

Testes e validacoes:

1. Run real conclui ou falha com mensagem clara.
2. Nenhum token aparece em logs.
3. Custos e quantidade de chamadas estao dentro do esperado.
4. Admin consegue cancelar ou aplicar com seguranca.

## 23. Matriz final de conclusao

Antes de considerar a implementacao completa, valide esta matriz:

1. Banco: migrations sobem em SQLite local e Postgres de homologacao.
2. Config: app sobe com IA desligada e sem chaves.
3. Seguranca: nenhum segredo real esta versionado.
4. Preflight: erros de dados aparecem antes de resetar passageiros.
5. Baseline: estado anterior e salvo antes de qualquer alteracao.
6. Restore: cancelar volta assignments ao estado anterior.
7. Provider: testes nao usam rede real.
8. Solver: custo minimo e prioridade antes de distancia.
9. Horarios: primeiro pickup e chegada respeitam limites.
10. Tolerancia: nao influencia calculo.
11. Frota: agente pode sugerir manter, criar, editar e remover do dia.
12. Assignments: apply usa proposal/revalidacao existente.
13. Frontend: Ajustes e Alteracoes funcionam em desktop e mobile.
14. Persistencia: sugestao salva reabre por `Implementar Modifications`.
15. Auditoria: run, suggestion, prompt version, modelo e provider ficam registrados.
16. Rollback: feature flag desliga fluxo IA sem afetar dashboard manual.
