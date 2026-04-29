# Fase 5.2 - Politica explicita de horarios global, por data e por contexto

## Objetivo

Esta fase reorganiza a camada de horarios do transporte para deixar explicita a precedencia entre configuracao global, sobrescrita por data e sobrescrita contextual por workplace. O foco aqui foi tirar essa decisao do campo implicito de configuracao unica e transformá-la em uma politica de resolucao auditavel e reutilizavel.

## O que foi implementado

1. O modulo `sistema/app/services/location_settings.py` passou a expor `resolve_transport_work_to_home_time_policy` e `get_transport_work_to_home_time_for_context`.
2. A resolucao do horario de retorno passou a seguir a politica explicita:
   - `date_override`
   - `workplace_context`
   - `global`
3. O endpoint `GET /api/transport/work-to-home-time-policy` foi adicionado para inspecionar o horario efetivo e a origem da decisao para uma data e, opcionalmente, um workplace.
4. O fluxo web de transporte passou a usar o workplace do usuario quando resolve `boarding_time` para requests `regular` e `weekend` em `work_to_home`.

## Politica de precedencia

O backend agora distingue explicitamente tres camadas:

1. horario global de retorno, configurado em `MobileAppSettings`;
2. horario excepcional por data, configurado em `TransportDailySetting`; e
3. horario contextual por workplace, armazenado no proprio `Workplace`.

Na implementacao atual, a precedencia formalizada e:

1. se existir override por data, ele vence;
2. se nao existir override por data, mas existir horario contextual do workplace, ele vence;
3. caso contrario, o sistema recorre ao horario global.

## Resultado operacional

Essa mudanca permite que dois workplaces compartilhem o mesmo dia operacional com horarios contextuais distintos sem perder a capacidade de aplicar um override geral por data quando necessario. Ao mesmo tempo, o fluxo antigo baseado em um unico horario global continua disponivel como fallback explicito.

## Limite atual

Nesta fase, a resolucao contextual foi aplicada ao `work_to_home_time`, que era o principal horario operacional ambiguo do modulo atual. Variacoes futuras por tipo de atendimento ou outras familias de horario continuam abertas para fases posteriores, mas agora ja contam com uma politica de precedencia definida e um ponto unico de resolucao.

## Validacao executada

Foram validados:

1. a precedencia entre global, workplace e date override via endpoint dedicado; e
2. a aplicacao dessa politica no `boarding_time` do fluxo web do usuario.