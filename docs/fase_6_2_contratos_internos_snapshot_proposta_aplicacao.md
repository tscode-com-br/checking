# Fase 6.2 - Contratos internos seguros para snapshot, proposta e aplicacao

## Objetivo

Esta fase formaliza uma superficie interna estavel para planejamento operacional de transporte sem depender da montagem do dashboard nem de comandos manuais de assignment. O objetivo foi permitir que componentes futuros, inclusive automacao assistida por agente, consumam tres contratos claros: leitura do snapshot do dia, construcao de proposal a partir desse snapshot e aplicacao segura de uma proposal aprovada.

## O que foi implementado

1. O backend passou a expor `GET /api/transport/operational-snapshot`, que devolve um `TransportOperationalSnapshot` diretamente a partir do dominio, sem passar pela resposta agregada do dashboard administrativo.
2. O backend passou a expor `POST /api/transport/proposals/build`, que recebe `TransportOperationalProposalBuildRequest` e devolve uma `TransportOperationalProposal` em estado `draft`, com snapshot atual reconstruido no servidor.
3. O backend passou a expor `POST /api/transport/proposals/apply`, que recebe `TransportOperationalProposalApplyRequest`, revalida a proposal, exige status `approved` e somente entao persiste assignments.

## Novos contratos principais

Em `sistema/app/schemas.py`, a fase adicionou os seguintes contratos:

1. `TransportOperationalProposalBuildRequest`
2. `TransportOperationalProposalApplyRequest`
3. `TransportOperationalAppliedAssignment`
4. `TransportOperationalProposalApplyResult`

Tambem foi ampliado `TransportProposalAuditEntry` para aceitar a acao `applied`, permitindo que a trilha da proposal passe a registrar validacao, aprovacao, rejeicao e aplicacao em um unico fluxo coerente.

## Servico interno consolidado

Em `sistema/app/services/transport_proposals.py`, a fase introduziu duas funcoes centrais:

1. `build_transport_operational_proposal_contract`, que recompõe snapshot e proposal em um unico passo server-side; e
2. `apply_transport_operational_proposal`, que reusa a validacao existente e so aplica assignments quando a proposal continua consistente e aprovada.

Essa aplicacao nao criou um segundo motor de assignment. Ela reaproveita `upsert_transport_assignment_with_persistence`, preservando as mesmas regras operacionais do fluxo manual atual, inclusive propagacao recorrente onde isso ja fazia parte do comportamento do dominio.

## Garantias de seguranca introduzidas

O contrato de aplicacao agora impõe algumas garantias minimas importantes:

1. uma proposal em `draft` nao pode ser aplicada;
2. a proposal e revalidada no momento da aplicacao, para reduzir risco de drift entre aprovacao e persistencia;
3. request e vehicle referenciados pela proposal precisam continuar carregaveis no momento da aplicacao; e
4. a proposal aplicada registra auditoria explicita com acao `applied`.

## Integracao com eventos internos

Quando uma proposal aprovada e aplicada, o backend emite o gatilho `transport_assignment_changed` com `source="transport_proposal"`, conectando a nova superficie contratual ao catalogo de reavaliacao operacional criado na fase 6.1.

## Resultado estrutural

Com isso, o modulo deixa de exigir que um consumidor externo reconstrua manualmente uma proposal a partir do dashboard ou invoque endpoints administrativos de assignment item a item. O fluxo contratual passa a ser:

1. obter snapshot operacional explicito;
2. construir proposal server-side sobre esse snapshot;
3. validar e aprovar a proposal; e
4. aplicar a proposal aprovada por um comando unico e auditavel.

## Validacao executada

Foi validado que:

1. `POST /api/transport/proposals/build` gera uma proposal `draft` com snapshot atual do dia;
2. `POST /api/transport/proposals/apply` persiste assignments e marca a proposal como `applied` quando ela ja foi aprovada; e
3. o mesmo endpoint bloqueia proposals ainda em `draft`, sem persistir assignments.