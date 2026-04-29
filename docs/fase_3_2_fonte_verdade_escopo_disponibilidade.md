# Fase 3.2 - Consolidação da fonte de verdade para escopo e disponibilidade

## Objetivo

Esta etapa formaliza que o escopo operacional de um veículo passa a ser definido prioritariamente pela agenda ativa em `TransportVehicleSchedule`, e não pelo espelho legado `Vehicle.service_scope`. O campo em `Vehicle` permanece por compatibilidade e como fallback para cenários legados sem agenda ativa, mas deixa de ser a referência preferencial para leituras operacionais do domínio.

## Decisão arquitetural

1. `TransportVehicleSchedule.service_scope` é a fonte de verdade para escopo e disponibilidade sempre que houver agenda ativa aplicável ao veículo.
2. `Vehicle.service_scope` permanece apenas como espelho legado e fallback para registros antigos ou fluxos em que ainda não existe agenda ativa associada.
3. Regras operacionais que precisem responder se um veículo atende determinada lista, ou qual escopo deve ser exposto numa leitura, devem passar por helpers centrais e não mais recompor essa decisão localmente.

## O que foi implementado

1. O módulo `sistema/app/services/transport_vehicle_schedule.py` passou a expor os helpers `list_transport_vehicle_active_scopes`, `resolve_transport_vehicle_operational_scope` e `vehicle_supports_transport_service_scope`.
2. O módulo `sistema/app/services/transport.py` deixou de recalcular manualmente a precedência entre agenda e espelho legado em múltiplos pontos distintos.
3. O cálculo de `boarding_time` no estado web agora usa a agenda ativa do veículo quando ela está disponível, evitando que um `Vehicle.service_scope` defasado altere a regra de horário efetivo.
4. A indexação de assignments recorrentes passou a consultar a nova regra centralizada para decidir se um veículo realmente atende o `request_kind` considerado.
5. A montagem de `TransportVehicleRow` passou a expor o `service_scope` resolvido pela regra centralizada, mantendo a compatibilidade da resposta sem repetir a lógica em cada call site.

## Impacto estrutural

Com esta mudança, a semântica de escopo fica localizada no agregado de agenda e em helpers explícitos. O domínio deixa de depender de comparações ad hoc entre `Vehicle.service_scope` e coleções de schedules espalhadas em camadas de leitura. Isso reduz ambiguidade e torna mais claro onde localizar a regra correta quando houver futuras mudanças em disponibilidade, dashboard, proposal engine ou automação.

## Compatibilidade preservada

1. `Vehicle.service_scope` continua existindo e sendo sincronizado como espelho legado pelos fluxos de cadastro e edição já implementados.
2. As respostas atuais do dashboard e do estado web continuam expondo `service_scope` e `boarding_time` no mesmo formato.
3. Veículos legados sem agenda ativa continuam funcionando por fallback no espelho do `Vehicle`.

## Validação executada

Foram validados dois slices focados:

1. um teste unitário cobrindo que o helper de resolução prefere o `service_scope` da agenda ativa ao espelho legado do veículo;
2. um teste de API cobrindo que o estado web confirmado usa o horário efetivo de `work_to_home` a partir da agenda ativa mesmo quando `Vehicle.service_scope` está divergente.

## Limite desta fase

Esta fase consolida a regra de leitura e resolução do escopo. A análise sobre quando alterações de escopo, disponibilidade e lotação devem bloquear ou revalidar assignments existentes permanece para a Fase 3.3.