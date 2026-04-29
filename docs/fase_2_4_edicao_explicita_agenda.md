# Fase 2.4: fluxo explicito de edicao de agenda

## Objetivo da etapa

Esta etapa introduz um comando dedicado para editar a disponibilidade operacional de uma agenda sem descaracterizar o cadastro-base do veiculo. O objetivo e impedir que ajustes de rota, recorrencia, data, horario ou ativacao continuem sendo tratados como exclusao seguida de recriacao.

## Contrato implementado

- endpoint: `PUT /api/transport/vehicle-schedules/{schedule_id}`
- schema de entrada: `TransportVehicleScheduleUpdate`
- alvo da operacao: apenas a agenda operacional representada por `TransportVehicleSchedule`

O contrato de agenda permite alterar:

- `service_scope`
- `route_kind`
- `recurrence_kind`
- `service_date`
- `weekday`
- `departure_time`
- `is_active`

## Regras implementadas

- a agenda e identificada por `schedule_id`, sem alterar o `vehicle_id` nem o cadastro-base do veiculo;
- a validacao operacional continua centralizada em `TransportVehicleScheduleDefinition`;
- o update bloqueia conflito com outra agenda ativa equivalente do mesmo veiculo;
- o update bloqueia combinacao simultanea de agendas ativas em listas diferentes para o mesmo veiculo;
- o update bloqueia alteracoes que fariam assignments confirmados futuros perderem cobertura operacional;
- as excecoes da agenda editada sao removidas no update, para evitar que excecoes antigas continuem semantica e operacionalmente acopladas a uma agenda que mudou.

## Implementacao realizada

- `TransportVehicleScheduleUpdate` foi adicionado em `sistema/app/schemas.py`.
- `sistema/app/services/transport_vehicle_schedule.py` recebeu a rotina `update_transport_vehicle_schedule`, junto com helpers para montar definicao a partir do modelo, avaliar cobertura por data, validar conflito e identificar impacto sobre assignments confirmados.
- `sistema/app/services/transport.py` passou a expor wrapper compativel para o novo comando.
- `sistema/app/routers/transport.py` passou a expor `PUT /api/transport/vehicle-schedules/{schedule_id}`.

## Resultado da fase 2.4

Ao final desta etapa, a agenda operacional pode ser modificada diretamente e de forma independente do cadastro-base do veiculo. Alteracoes de disponibilidade deixam de exigir recriacao disfarcada, e passam a obedecer regras explicitas de conflito, cobertura operacional e impacto sobre alocacoes confirmadas.