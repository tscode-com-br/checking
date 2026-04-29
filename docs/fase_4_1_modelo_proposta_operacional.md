# Fase 4.1 - Modelo de proposta operacional para um dia de transporte

## Objetivo

Esta etapa introduz o conceito formal de proposta operacional como uma estrutura de domínio separada da persistência final de assignments. O objetivo é permitir que o backend represente uma sugestão de distribuição e atendimento sobre um snapshot estável do dia, sem aplicar imediatamente essa decisão no estado operacional.

## O que foi implementado

1. O arquivo `sistema/app/schemas.py` passou a expor os contratos `TransportOperationalSnapshot`, `TransportProposalDecision`, `TransportOperationalProposalSummary` e `TransportOperationalProposal`.
2. O novo módulo `sistema/app/services/transport_proposals.py` passou a materializar um snapshot operacional explícito a partir da leitura estável do dashboard, por meio de `build_transport_operational_snapshot`.
3. O mesmo módulo passou a construir propostas em rascunho com `build_transport_operational_proposal`, mantendo origem, vínculo com o snapshot capturado, ciclo de vida inicial em `draft` e coleção de decisões sugeridas ainda não aplicadas.
4. O resumo da proposta passou a contar requests e veículos presentes no snapshot, além da quantidade de decisões confirmadas, rejeitadas ou devolvidas para `pending`.

## Definição mínima do modelo

O modelo formalizado nesta fase contém os seguintes blocos mínimos:

1. **Snapshot operacional**: data, rota, instante de captura, horário efetivo de `work_to_home`, requests, veículos, registries, projetos e workplaces visíveis no recorte considerado.
2. **Decisão sugerida**: request alvo, tipo do request, data, rota, status sugerido, veículo sugerido quando houver confirmação, resposta opcional e justificativa opcional.
3. **Proposta operacional**: chave da proposta, origem (`manual`, `system` ou `agent`), status de ciclo de vida (`draft`, `approved`, `rejected`, `applied`, `expired`), snapshot associado, decisões e resumo agregado.

## Impacto estrutural

Com esta mudança, o domínio passa a ter uma fronteira explícita entre:

1. a leitura estável do dia de transporte; e
2. a decisão sugerida sobre esse recorte.

Isso reduz a dependência conceitual do dashboard como único lugar onde a situação operacional pode ser entendida e prepara o backend para as próximas fases de validação, aprovação e aplicação de propostas.

## Validação executada

Foi validado um slice focado que:

1. materializa um snapshot operacional real a partir do banco de teste;
2. monta uma proposta `draft` com decisão sugerida de confirmação; e
3. comprova que a proposta representa a decisão sem persistir assignments automaticamente.

## Limite desta fase

Esta fase não introduz endpoints de proposal, persistência em banco, fluxo de aprovação nem aplicação da decisão sugerida. Esses passos ficam reservados para as fases 4.2 e 4.3.