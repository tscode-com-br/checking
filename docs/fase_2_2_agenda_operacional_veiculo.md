# Fase 2.2: definicao formal da agenda operacional do veiculo

## Objetivo da etapa

Esta etapa formaliza quais dados representam disponibilidade operacional do veiculo e quais regras controlam coexistencia, recorrencia, conflito e reaproveitamento de agenda. O objetivo e impedir que cadastro-base e presenca operacional continuem misturados no mesmo contrato mental.

## Definicao consolidada da agenda operacional

A agenda operacional do veiculo passa a ser representada explicitamente pelo contrato `TransportVehicleScheduleDefinition`, em `sistema/app/schemas.py`.

Campos da agenda operacional:

- `service_scope`
- `route_kind`
- `recurrence_kind`
- `service_date`
- `weekday`
- `departure_time`
- `is_active`

Esses campos nao pertencem ao cadastro-base. Eles representam quando, em qual lista e em qual trajeto o veiculo pode operar.

## Regras formalizadas

- agendas `extra` exigem `recurrence_kind = single_date` e `departure_time` obrigatorio;
- agendas `regular` e `weekend` nao aceitam `departure_time`;
- agendas `single_date` exigem `service_date` e nao aceitam `weekday`;
- agendas `matching_weekday` exigem `weekday`;
- reaproveitamento de placa com agenda antiga continua permitido apenas quando restam agendas `single_date` passadas ou explicitamente excepcionadas;
- conflitos continuam sendo calculados por agenda ativa, e nao por atributos cadastrais do veiculo.

## Implementacao realizada

- `TransportVehicleScheduleDefinition` foi introduzido em `sistema/app/schemas.py`.
- `sistema/app/services/transport_vehicle_schedule.py` passou a centralizar a definicao operacional: expansao do payload em agendas, validacao de recorrencia, criacao de modelos, deteccao de conflito, reaproveitamento e busca de disponibilidade.
- `sistema/app/services/transport_vehicle_operations.py` agora consome a agenda operacional formalizada, em vez de construir dicionarios soltos para representar disponibilidade.

## Resultado da fase 2.2

Ao final desta etapa, a agenda operacional do veiculo virou um agregado explicito no codigo. A distincao entre configuracao permanente do veiculo e disponibilidade operacional ficou documentada, validada e reutilizavel.