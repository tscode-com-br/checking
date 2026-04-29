# Fase 2.3: fluxo explicito de edicao completa de veiculo

## Objetivo da etapa

Esta etapa introduz um comando dedicado para editar o veiculo por identificador estavel, sem exclusao e recriacao. O objetivo e permitir alteracao de placa, tipo, cor, lugares e tolerancia sem destruir agendas, assignments ou historico vinculado ao `vehicle.id`.

## Contrato implementado

- endpoint: `PUT /api/transport/vehicles/{vehicle_id}`
- schema de entrada: `TransportVehicleUpdate`
- alvo da operacao: apenas o cadastro-base do veiculo

O endpoint nao altera agendas operacionais. Escopo, recorrencia, data, trajeto, horario e ativacao continuam pertencendo a comandos de agenda, nao a comandos de cadastro-base.

## Regras implementadas

- o update identifica o veiculo por `vehicle_id`;
- a placa pode ser alterada, desde que nao conflite com outro veiculo existente;
- agendas existentes permanecem vinculadas ao mesmo `vehicle.id`;
- assignments existentes permanecem vinculados ao mesmo `vehicle.id`;
- referencias legadas em `User.placa` sao sincronizadas quando a placa muda;
- o campo legado `Vehicle.service_scope` nao e alterado por este endpoint, pois ele nao representa cadastro-base.

## Implementacao realizada

- `TransportVehicleUpdate` foi adicionado em `sistema/app/schemas.py`.
- `update_transport_vehicle_base`, em `sistema/app/services/transport_vehicle_base.py`, centraliza a regra de update do cadastro-base e a sincronizacao de referencias legadas por placa.
- o router de transporte expoe `PUT /api/transport/vehicles/{vehicle_id}` em `sistema/app/routers/transport.py`.

## Resultado da fase 2.3

Ao final desta etapa, editar veiculo passou a significar atualizar o registro original do veiculo, e nao apagar a agenda ou recriar entidades. Isso reduz risco operacional e prepara o terreno para a fase posterior de edicao explicita de agendas.