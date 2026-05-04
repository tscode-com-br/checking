# Baseline Tecnico do Modulo Transport Antes da IA

## 1. Escopo deste baseline

Este documento registra o estado atual confirmado do modulo `transport` antes de qualquer implementacao funcional do fluxo de IA de roteirizacao.

Objetivos desta linha de base:

1. listar os endpoints ja existentes que podem ser reutilizados;
2. registrar o shape atual confirmado de `/api/transport/settings`;
3. registrar o shape atual confirmado de `/api/transport/operational-snapshot`;
4. descrever o comportamento real do frontend `transport`, com foco no menu `IA`;
5. consolidar riscos atuais e invariantes que nao podem quebrar.

Este baseline foi montado a partir de leitura de codigo e testes existentes, principalmente em:

1. `sistema/app/routers/transport.py`;
2. `sistema/app/schemas.py`;
3. `sistema/app/services/transport_dashboard_queries.py`;
4. `sistema/app/services/transport_proposals.py`;
5. `sistema/app/services/location_settings.py`;
6. `sistema/app/static/transport/index.html`;
7. `sistema/app/static/transport/app.js`;
8. `sistema/app/static/transport/i18n.js`;
9. `tests/test_api_flow.py`;
10. `tests/transport_page_date.test.js`.

## 2. Endpoints de transporte ja existentes

### 2.1 Sessao e atualizacao em tempo real

1. `GET /api/transport/auth/session`
2. `POST /api/transport/auth/verify`
3. `POST /api/transport/auth/logout`
4. `GET /api/transport/stream`

### 2.2 Leitura operacional do dashboard

1. `GET /api/transport/dashboard`
2. `GET /api/transport/projects`
3. `GET /api/transport/operational-snapshot`
4. `GET /api/transport/reevaluation-events`
5. `GET /api/transport/work-to-home-time-policy`
6. `GET /api/transport/workplaces`

### 2.3 Proposal operacional de assignments

1. `POST /api/transport/proposals/build`
2. `POST /api/transport/proposals/validate`
3. `POST /api/transport/proposals/approve`
4. `POST /api/transport/proposals/reject`
5. `POST /api/transport/proposals/apply`

### 2.4 Exportacao

1. `GET /api/transport/exports/transport-list`
2. `POST /api/transport/exports/operational-plan`

### 2.5 Settings e catalogos auxiliares

1. `GET /api/transport/settings`
2. `PUT /api/transport/settings`
3. `POST /api/transport/settings/currencies`
4. `PUT /api/transport/date-settings`

### 2.6 Contexto operacional editavel

1. `POST /api/transport/workplaces`
2. `PUT /api/transport/workplaces/{workplace_id}`
3. `POST /api/transport/vehicles`
4. `DELETE /api/transport/vehicles/{schedule_id}`
5. `PUT /api/transport/vehicles/{vehicle_id}`
6. `PUT /api/transport/vehicle-schedules/{schedule_id}`
7. `POST /api/transport/assignments`
8. `POST /api/transport/requests/reject`

## 3. Contrato real de `/api/transport/settings`

### 3.1 Shape atual

O endpoint devolve hoje um objeto unico com:

1. `work_to_home_time`
2. `last_update_time`
3. `default_car_seats`
4. `default_minivan_seats`
5. `default_van_seats`
6. `default_bus_seats`
7. `default_tolerance_minutes`
8. `price_currency_code`
9. `price_rate_unit`
10. `default_car_price`
11. `default_minivan_price`
12. `default_van_price`
13. `default_bus_price`
14. `available_currencies`

### 3.2 Defaults atuais confirmados

Quando nao ha configuracao persistida, os defaults confirmados hoje sao:

1. `work_to_home_time = "16:45"`
2. `last_update_time = "16:00"`
3. `default_car_seats = 3`
4. `default_minivan_seats = 6`
5. `default_van_seats = 10`
6. `default_bus_seats = 40`
7. `default_tolerance_minutes = 5`
8. `price_currency_code = null`
9. `price_rate_unit = "day"`
10. `default_*_price = null`
11. `available_currencies = []`

Esses valores saem de `location_settings.py` e ja estao cobertos por teste de API.

### 3.3 Exemplo anonizado de payload atual

```json
{
  "work_to_home_time": "16:45",
  "last_update_time": "16:00",
  "default_car_seats": 3,
  "default_minivan_seats": 6,
  "default_van_seats": 10,
  "default_bus_seats": 40,
  "default_tolerance_minutes": 5,
  "price_currency_code": null,
  "price_rate_unit": "day",
  "default_car_price": null,
  "default_minivan_price": null,
  "default_van_price": null,
  "default_bus_price": null,
  "available_currencies": []
}
```

### 3.4 Exemplo anonizado de payload apos configuracao

```json
{
  "work_to_home_time": "18:10",
  "last_update_time": "16:20",
  "default_car_seats": 4,
  "default_minivan_seats": 7,
  "default_van_seats": 11,
  "default_bus_seats": 44,
  "default_tolerance_minutes": 9,
  "price_currency_code": "SGD",
  "price_rate_unit": "week",
  "default_car_price": 120.5,
  "default_minivan_price": 150.75,
  "default_van_price": 230.0,
  "default_bus_price": 510.25,
  "available_currencies": [
    {
      "code": "SGD",
      "display_label": "Singapore Dollar"
    }
  ]
}
```

## 4. Contrato real de `/api/transport/operational-snapshot`

### 4.1 Estrutura raiz atual

O snapshot operacional atual e uma fotografia enriquecida do dashboard, com os campos:

1. `snapshot_key`
2. `service_date`
3. `route_kind`
4. `captured_at`
5. `work_to_home_departure_time`
6. `projects`
7. `regular_requests`
8. `weekend_requests`
9. `extra_requests`
10. `regular_vehicles`
11. `weekend_vehicles`
12. `extra_vehicles`
13. `regular_vehicle_registry`
14. `weekend_vehicle_registry`
15. `extra_vehicle_registry`
16. `workplaces`

### 4.2 Shape atual de `projects`

Cada projeto no snapshot carrega hoje:

1. `id`
2. `name`
3. `country_code`
4. `country_name`
5. `timezone_name`
6. `timezone_label`
7. `address`
8. `zip_code`

Isso e relevante porque o agente pode usar `projects` como fonte de verdade para destino, pais e timezone, sem depender do DOM.

### 4.3 Shape atual de `regular_requests`, `weekend_requests` e `extra_requests`

Cada linha de request no snapshot carrega hoje:

1. `id`
2. `request_kind`
3. `requested_time`
4. `service_date`
5. `user_id`
6. `chave`
7. `nome`
8. `projeto`
9. `workplace`
10. `end_rua`
11. `zip`
12. `assignment_status`
13. `awareness_status`
14. `assigned_vehicle`
15. `response_message`

`assignment_status` hoje pode ser:

1. `pending`
2. `confirmed`
3. `rejected`
4. `cancelled`

### 4.4 Shape atual de `assigned_vehicle`

Quando um request esta alocado, `assigned_vehicle` carrega:

1. `id`
2. `placa`
3. `tipo`
4. `color`
5. `lugares`
6. `tolerance`
7. `pending_fields`
8. `is_ready_for_allocation`
9. `schedule_id`
10. `service_scope`
11. `route_kind`
12. `departure_time`

### 4.5 Shape atual de `*_vehicle_registry`

As listas de registry sao importantes porque expõem contexto operacional que o agente precisara preservar:

1. `vehicle_id`
2. `schedule_id`
3. `placa`
4. `tipo`
5. `lugares`
6. `assigned_count`
7. `service_date`
8. `route_kind`
9. `departure_time`
10. `pending_fields`
11. `is_ready_for_allocation`

### 4.6 Shape atual de `workplaces`

Cada workplace carrega hoje:

1. `id`
2. `workplace`
3. `address`
4. `zip`
5. `country`
6. `transport_group`
7. `boarding_point`
8. `transport_window_start`
9. `transport_window_end`
10. `service_restrictions`
11. `transport_work_to_home_time`

### 4.7 Exemplo anonizado de snapshot atual

Exemplo reduzido, mantendo o shape real e omitindo listas vazias repetitivas:

```json
{
  "snapshot_key": "transport-snapshot:2026-04-17:home_to_work:2026-04-16T21:00:00+08:00",
  "service_date": "2026-04-17",
  "route_kind": "home_to_work",
  "captured_at": "2026-04-16T21:00:00+08:00",
  "work_to_home_departure_time": "18:10",
  "projects": [
    {
      "id": 66,
      "name": "P66",
      "country_code": "SG",
      "country_name": "Singapura",
      "timezone_name": "Asia/Singapore",
      "timezone_label": "Singapura (+8)",
      "address": "66 Contract Lane",
      "zip_code": "941661"
    }
  ],
  "regular_requests": [
    {
      "id": 701,
      "request_kind": "regular",
      "requested_time": "07:10",
      "service_date": "2026-04-17",
      "user_id": 8801,
      "chave": "SN66",
      "nome": "Snapshot Rider",
      "projeto": "P66",
      "workplace": "Snapshot Contract Hub",
      "end_rua": "66 Snapshot Avenue",
      "zip": "941662",
      "assignment_status": "pending",
      "awareness_status": "pending",
      "assigned_vehicle": null,
      "response_message": null
    }
  ],
  "regular_vehicles": [
    {
      "id": 501,
      "placa": "SNP6601",
      "tipo": "van",
      "color": "White",
      "lugares": 10,
      "tolerance": 8,
      "pending_fields": [],
      "is_ready_for_allocation": true,
      "schedule_id": 9901,
      "service_scope": "regular",
      "route_kind": null,
      "departure_time": null
    }
  ],
  "regular_vehicle_registry": [
    {
      "vehicle_id": 501,
      "schedule_id": 9901,
      "placa": "SNP6601",
      "tipo": "van",
      "lugares": 10,
      "assigned_count": 0,
      "service_date": null,
      "route_kind": null,
      "departure_time": null,
      "pending_fields": [],
      "is_ready_for_allocation": true
    }
  ],
  "workplaces": [
    {
      "id": 301,
      "workplace": "Snapshot Contract Hub",
      "address": "66 Contract Lane",
      "zip": "941661",
      "country": "Singapore",
      "transport_group": null,
      "boarding_point": null,
      "transport_window_start": null,
      "transport_window_end": null,
      "service_restrictions": null,
      "transport_work_to_home_time": null
    }
  ]
}
```

## 5. Comportamento atual confirmado do frontend `transport`

### 5.1 Estrutura visivel do dashboard

O frontend atual ja entrega:

1. topbar com data selecionada, autenticacao e link `Dashboard Settings`;
2. menu suspenso `IA`;
3. tres listas de passageiros: `EXTRA`, `WEEKEND` e `REGULAR`;
4. tres painéis de veiculos: `Extra Transport List`, `Weekend Transport List` e `Regular Transport List`;
5. modal de veiculo;
6. modal de settings;
7. modal de ajustes do agente de IA.

### 5.2 Comportamento atual do menu `IA`

O menu `IA` hoje tem duas acoes visiveis:

1. `Calculate Routes`
2. `Implement Modifications`

Estado funcional atual:

1. `Calculate Routes` abre o modal `Ajustes para o Agente de IA`.
2. `Implement Modifications` apenas fecha o menu.
3. Nao existe chamada a endpoint `ai/*`.
4. Nao existe polling.
5. Nao existe abertura de uma janela de diff/revisao.

### 5.3 Comportamento atual do modal `Ajustes para o Agente de IA`

O modal ja existe no HTML e no JS, mas seu comportamento atual e minimo:

1. titulo presente;
2. nota informativa baseada na quantidade de projetos carregados;
3. input `data-ai-agent-earliest-boarding`;
4. input `data-ai-agent-arrival-at-work`;
5. botao de fechar no canto superior;
6. unico botao no rodape: `Fechar`.

### 5.4 O que o modal ainda nao faz hoje

1. nao preenche `06:50` e `07:45` por padrao;
2. nao tem botao `Cancelar` distinto;
3. nao tem botao `Solicitar Rotas`;
4. nao faz validacao local de horarios;
5. nao dispara request para backend;
6. nao mostra feedback de carregamento, progresso ou erro;
7. nao persiste draft do formulario;
8. nao abre qualquer janela de `Alteracoes`.

### 5.5 Cobertura de teste atual do frontend

Ja existe cobertura para:

1. render do `/transport`;
2. helpers de data;
3. helpers de settings, moedas, precos e tolerancia;
4. layout e CSS dos modais existentes;
5. listas e painéis de veiculos;
6. caminhos base-relativos `../api/transport` e `../assets`.

Nao ha, neste momento, cobertura de teste especifica para:

1. submit do modal da IA;
2. fetch de sugestao salva;
3. progresso de run;
4. janela `Alteracoes`;
5. save/apply/cancel de sugestoes de IA.

## 6. Lacunas confirmadas para o fluxo de IA

### 6.1 Backend

1. nao existe router `transport_ai.py`;
2. nao existe tabela de run, suggestion, baseline, cache de geocode ou cache de matrix;
3. nao existe endpoint unificado de `Solicitar Rotas`;
4. nao existe endpoint de `Implementar Modifications`;
5. proposal operacional atual cobre assignments, nao acoes de frota;
6. `TransportProposalDecision` aceita apenas `vehicle_id` existente;
7. nao existe schema de itinerario detalhado por veiculo;
8. nao existe integracao server-side com provider de mapas;
9. nao existe integracao com OpenAI/LangChain;
10. nao existe restore de baseline.

### 6.2 Frontend

1. o menu `IA` ainda e majoritariamente estrutural;
2. o modal do agente ainda e informativo, nao operacional;
3. `Implement Modifications` ainda e um stub;
4. nao existe tela de diff de custo/frota/passageiros;
5. nao existe estado de progresso;
6. nao existe render de issues de planejamento.

## 7. Riscos atuais encontrados

1. o menu `IA` cria expectativa funcional no usuario, mas hoje nao executa fluxo real;
2. os campos do modal do agente estao sem defaults, o que abre margem para wiring futuro incompleto;
3. a proposal atual valida/aplica apenas assignments e reusa `vehicle_id` existente, o que bloqueia criacao de veiculo no apply sem extensao de contrato;
4. nao ha persistencia historica do estado pre-IA, entao qualquer reset futuro sem baseline seria destrutivo;
5. nao ha preflight server-side para custo, enderecos, pais ou limites de execucao;
6. nao ha protecao de frontend para reabrir sugestoes salvas, porque ainda nao existe esse conceito;
7. nao ha testes existentes para o fluxo de IA propriamente dito, apenas para superficies preparatorias.

## 8. Invariantes que nao podem quebrar

1. o frontend `transport` usa caminhos relativos `../api/transport` e `../assets`; a implementacao da IA deve preservar esse padrao;
2. a autenticacao do modulo continua sendo por sessao de transporte ja existente;
3. o snapshot operacional continua sendo a fonte canonica do estado do dia e da rota selecionada;
4. requests continuam separados por `regular`, `weekend` e `extra`;
5. veiculos continuam separados por `regular`, `weekend` e `extra`;
6. `extra` continua sendo route-aware via `route_kind` e `service_date`;
7. settings de assentos, tolerancia e preco continuam centralizados em `/api/transport/settings`;
8. `projects` no snapshot e no endpoint dedicado continuam carregando `address`, `zip_code`, `country_code`, `country_name` e `timezone_name`;
9. proposals existentes nao devem mudar semanticamente para acomodar IA; a extensao deve acontecer por novos endpoints e novos contratos;
10. eventos de reevaluacao e refresh do dashboard continuam sendo parte do fluxo oficial de sincronizacao.

## 9. Validacoes previstas para esta fase

Comandos definidos na to-do list desta fase:

1. `pytest tests/test_api_flow.py -k transport`
2. `node --test tests/transport_page_date.test.js`

Objetivos dessas validacoes:

1. confirmar que o baseline do modulo ainda esta verde antes da implementacao da IA;
2. registrar o comportamento atual como linha de base executavel;
3. evitar que a fase de IA comece sobre uma superficie ja quebrada.

## 10. Observacoes de controle desta etapa

1. este documento nao grava segredos reais;
2. os payloads acima foram anonimizados e reduzidos para documentar contrato, nao dados sensiveis;
3. a etapa de baseline nao exige alteracao funcional de codigo;
4. quaisquer mudancas funcionais de backend/frontend para IA devem partir desta linha de base, nao de inferencia sobre o DOM.