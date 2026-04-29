# Fase 3.3 - Impacto de alterações de veículo e agenda sobre assignments existentes

## Objetivo

Esta etapa formaliza como o backend deve tratar alterações cadastrais e operacionais quando já existem assignments confirmados ligados ao mesmo veículo. O foco é deixar explícito quais mudanças podem ser preservadas sem risco, quais devem ser bloqueadas e quais ficam reservadas para futura política de reprocessamento na camada de proposta.

## Matriz de impacto operacional

| Tipo de alteração | Fonte de verdade | Política nesta fase | Regra aplicada |
| --- | --- | --- | --- |
| Placa do veículo | `Vehicle.placa` com vínculo técnico por `vehicle.id` | Preservar | A alteração continua permitida; assignments permanecem válidos por `vehicle.id`, e `users.vehicle_id` / `users.placa` são sincronizados para compatibilidade. |
| Tipo, cor e tolerância do veículo | Cadastro-base do veículo | Preservar | A alteração não invalida disponibilidade nem assignments já confirmados. |
| Aumento de lotação (`lugares`) | Cadastro-base do veículo | Preservar | A alteração amplia capacidade sem remover cobertura operacional existente. |
| Redução de lotação (`lugares`) sem exceder a ocupação futura já confirmada | Cadastro-base do veículo | Preservar | A alteração continua permitida quando nenhuma combinação futura de data + rota ultrapassa a nova capacidade. |
| Redução de lotação (`lugares`) abaixo da ocupação futura já confirmada | Cadastro-base do veículo | Bloquear | O update é rejeitado quando assignments confirmados futuros para a mesma data e rota excederiam a nova lotação. |
| Alteração de escopo, rota, recorrência, data, horário ou ativação da agenda que mantém cobertura para assignments futuros | `TransportVehicleSchedule` | Preservar | O update continua permitido quando a agenda editada ou outra agenda ativa do mesmo veículo mantém cobertura para os assignments já confirmados. |
| Alteração de escopo, rota, recorrência, data, horário ou ativação da agenda que removeria cobertura para assignments futuros | `TransportVehicleSchedule` | Bloquear | O update é rejeitado quando assignments confirmados futuros ficariam sem agenda compatível. |
| Reprocessamento automático de assignments após mudança válida | Camada de proposta futura | Adiar | Esta fase não reatribui nem recalcula assignments automaticamente; ela apenas preserva ou bloqueia mudanças conforme risco estrutural. |
| Avisos não bloqueantes para revisão manual | Camada de proposta futura | Adiar | Esta fase ainda não expõe warnings operacionais; esse papel fica para a futura camada de proposta e aprovação. |

## O que foi implementado

1. O fluxo `PUT /api/transport/vehicles/{vehicle_id}` passou a bloquear redução de lotação que deixaria assignments confirmados futuros acima da nova capacidade.
2. A verificação de capacidade foi centralizada em `sistema/app/services/transport_vehicle_base.py`, agrupando assignments confirmados futuros por data e rota antes de aceitar a mudança de `lugares`.
3. O fluxo `PUT /api/transport/vehicle-schedules/{schedule_id}`, já introduzido na fase 2.4, passa a compor explicitamente a matriz desta fase como o caminho responsável por bloquear mudanças operacionais que removeriam cobertura de assignments confirmados.
4. O plano de reorganização agora registra de forma inequívoca que placa, tipo, cor e tolerância pertencem à zona de preservação, enquanto lotação e disponibilidade entram na zona de bloqueio quando ameaçam assignments futuros já confirmados.

## Impacto estrutural

Com esta mudança, alterações sensíveis deixam de depender de interpretação implícita do operador ou do desenvolvedor. O backend passa a distinguir entre:

1. mudanças cadastrais que preservam assignments porque a identidade técnica do veículo continua a mesma; e
2. mudanças que precisam ser bloqueadas por risco de overbooking ou perda de cobertura operacional futura.

Isso reduz a chance de o sistema aceitar estados inconsistentes logo antes da futura camada de proposta, aprovação e reprocessamento.

## Validação executada

Foram validados slices focados cobrindo:

1. bloqueio de update de veículo quando a nova lotação ficaria abaixo da quantidade de assignments confirmados futuros para a mesma data e rota;
2. preservação do fluxo normal de atualização de veículo em cenários que não violam capacidade;
3. bloqueio já existente de update de agenda quando assignments confirmados futuros perderiam cobertura.

## Limite desta fase

Esta fase não introduz reatribuição automática, warnings não bloqueantes nem recalculo de proposal/assignment. Esses comportamentos ficam reservados para a futura camada de proposta e aprovação das fases seguintes.