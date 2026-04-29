# Fase 6.1 - Catalogo de eventos internos para reavaliacao operacional

## Objetivo

Esta fase introduz um catalogo explicito de eventos internos que devem disparar reavaliacao operacional no dominio de transporte. O foco nao foi implementar o modo automatico, mas deixar claro quais mutacoes do sistema representam gatilhos legitimos para recomputar snapshot, revalidar restricoes, refazer proposta, regenerar exportacao ou atualizar estado operacional.

## O que foi implementado

1. Foi criado o modulo `sistema/app/services/transport_reevaluation_events.py`, que centraliza o catalogo de gatilhos, um historico recente em memoria e a emissao de eventos tipados.
2. O backend passou a expor `GET /api/transport/reevaluation-events`, retornando o catalogo dos tipos suportados e os eventos recentes emitidos no processo atual.
3. O broker de atualizacoes de transporte em `sistema/app/services/admin_updates.py` passou a aceitar metadados adicionais, permitindo que os eventos de realtime continuem compatveis com o frontend atual e, ao mesmo tempo, carreguem `event_type`, escopo e acoes recomendadas.

## Catalogo inicial de gatilhos

Nesta fase, o catalogo inicial passou a incluir pelo menos os seguintes tipos:

1. `transport_request_changed`
2. `transport_user_context_changed`
3. `transport_vehicle_supply_changed`
4. `transport_vehicle_schedule_changed`
5. `transport_assignment_changed`
6. `transport_timing_policy_changed`
7. `transport_workplace_context_changed`
8. `transport_operational_review_changed`

Cada tipo agora declara explicitamente quais acoes downstream sao recomendadas, escolhidas entre:

1. `refresh_snapshot`
2. `revalidate_constraints`
3. `rebuild_proposal`
4. `regenerate_export`
5. `refresh_transport_state`

## Pontos do dominio conectados ao catalogo

Os eventos passaram a ser emitidos em pontos reais do fluxo operacional, incluindo:

1. criacao ou cancelamento de solicitacao web de transporte;
2. alteracao de endereco do usuario no fluxo web;
3. atualizacao de horarios globais e por data;
4. criacao e atualizacao de workplace com contexto operacional;
5. criacao, atualizacao e remocao de veiculos ou agendas;
6. gravacao manual de assignment ou rejeicao administrativa de request; e
7. validacao, aprovacao ou rejeicao de propostas operacionais.

## Resultado estrutural

Com isso, o modulo deixa de depender apenas de sinais genericos de refresh e passa a ter um vocabulário interno mais preciso para automacao futura. O sistema agora consegue dizer nao apenas que “algo mudou”, mas qual classe de mudanca ocorreu e quais passos deveriam ser reconsiderados a partir dela.

## Limite desta fase

Esta fase ainda nao implementa consumidores automaticos desses eventos. O catalogo e o historico recente servem como preparacao para a fase 6.2, em que snapshots, propostas e aplicacao passarao a se apoiar nesses gatilhos de forma mais estruturada.

## Validacao executada

Foi validado que:

1. uma nova solicitacao web de transporte gera evento `transport_request_changed` visivel no catalogo recente; e
2. a aprovacao de proposal gera evento `transport_operational_review_changed` com escopo do dia revisado.

Tambem foi confirmada a compatibilidade do realtime web existente com o payload enriquecido do broker.