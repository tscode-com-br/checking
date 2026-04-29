# Fase 2.1: definicao formal do cadastro-base do veiculo

## Objetivo da etapa

Esta etapa formaliza, no codigo e na documentacao tecnica, quais atributos pertencem ao cadastro-base do veiculo e quais atributos pertencem ao contexto operacional de agenda. O objetivo e impedir que a aplicacao continue tratando `service_scope` como se ele fosse parte da identidade permanente do veiculo, quando a disponibilidade real ja e representada por `TransportVehicleSchedule`.

## Definicao consolidada do agregado-base

O cadastro-base do veiculo passa a ser representado explicitamente pelo contrato `TransportVehicleBaseData`, em `sistema/app/schemas.py`.

Campos que pertencem ao cadastro-base:

- `placa`
- `tipo`
- `color`
- `lugares`
- `tolerance`

Esses campos definem a configuracao persistente e editavel do veiculo. Eles nao expressam, por si so, em qual lista o veiculo opera nem em quais datas, trajetos ou recorrencias ele esta disponivel.

## Separacao em relacao ao contexto operacional

Continuam pertencendo ao contexto operacional, e nao ao cadastro-base:

- `service_scope`
- `service_date`
- `route_kind`
- `departure_time`
- recorrencia semanal e de fim de semana
- ativacao e excecoes de agenda

Nesta fase, `Vehicle.service_scope` foi mantido apenas como espelho legado de compatibilidade. As decisoes operacionais introduzidas nesta implementacao passam a preferir os dados de agenda quando eles ja estao disponiveis.

## Implementacao realizada

Foram introduzidos os seguintes pontos:

- `TransportVehicleBaseData` e `TransportVehicleBaseRow` em `sistema/app/schemas.py`, tornando explicito o contrato do cadastro-base.
- `sistema/app/services/transport_vehicle_base.py`, com helpers para montar, aplicar e comparar apenas os campos do cadastro-base.
- `create_transport_vehicle_registration`, em `sistema/app/services/transport_vehicle_operations.py`, agora compara configuracao-base separadamente do escopo operacional e sincroniza `Vehicle.service_scope` apenas como compatibilidade.
- `find_transport_vehicle_schedule` ganhou filtro opcional por `service_scope`, permitindo validacoes de alocacao baseadas em agenda real.
- Leituras de dashboard e templates recorrentes passaram a privilegiar `schedule.service_scope` quando a agenda ja responde melhor do que o espelho legado no veiculo.

## Resultado da fase 2.1

Ao final desta etapa, existe uma definicao oficial e reutilizavel do que e o cadastro-base do veiculo. A aplicacao continua compativel com o comportamento atual, mas a fronteira conceitual ficou mais explicita: dados cadastrais do veiculo e disponibilidade operacional deixam de ser tratados como a mesma coisa.