# Fase 4.2 - Fluxo de validacao e aprovacao de propostas operacionais

## Objetivo

Esta fase introduz um estagio formal entre a sugestao de uma proposta operacional e a futura aplicacao efetiva de assignments. O foco aqui e garantir governanca: a proposta pode ser revisada, validada, aprovada ou recusada sem que o backend grave imediatamente a distribuicao operacional final.

## O que foi implementado

1. O contrato `TransportOperationalProposal` passou a carregar `validation_issues` e `audit_trail`, transformando a proposta em um artefato auditavel.
2. Foram adicionados os modelos `TransportProposalValidationIssue`, `TransportProposalAuditEntry`, `TransportOperationalProposalCommandResult` e `TransportOperationalProposalRejectRequest` em `sistema/app/schemas.py`.
3. O modulo `sistema/app/services/transport_proposals.py` ganhou tres comandos explicitos:
   - `validate_transport_operational_proposal`
   - `approve_transport_operational_proposal`
   - `reject_transport_operational_proposal`
4. O router `sistema/app/routers/transport.py` passou a expor os endpoints:
   - `POST /api/transport/proposals/validate`
   - `POST /api/transport/proposals/approve`
   - `POST /api/transport/proposals/reject`

## Regras de validacao aplicadas

As validacoes desta fase operam sobre um recorte atual do dia e da rota da proposta, reconstruido a partir do dashboard operacional. A aprovacao passa a ser bloqueada quando ocorre qualquer uma das inconsistencias abaixo:

1. request duplicado dentro da mesma proposta;
2. request ausente do snapshot da propria proposta;
3. divergencia entre `service_date` ou `route_kind` da decisao e do snapshot;
4. divergencia de `request_kind` entre a decisao e o estado real do request;
5. request que deixou de estar pendente;
6. veiculo ausente do snapshot da proposta;
7. veiculo que nao esta mais disponivel para a data e rota em questao;
8. excesso de capacidade considerando ocupacao atual mais as confirmacoes sugeridas.

## Resultado operacional

Com isso, a proposta deixa de ser apenas um rascunho estrutural e passa a ter comportamento governado:

1. `validate` recalcula o estado do dia, registra o resultado no `audit_trail` e devolve issues claras quando houver bloqueios.
2. `approve` sempre revalida antes de aprovar, impedindo promocao de uma proposta que ficou inconsistente depois da captura do snapshot.
3. `reject` marca explicitamente a proposta como recusada, tambem sem aplicar assignments.

Nenhum desses comandos persiste `TransportAssignment`. A aplicacao efetiva continua reservada para a fase 4.3/4.4 do fluxo futuro.

## Estrutura de auditoria

Cada comando relevante passa a anexar um evento ao `audit_trail`, contendo:

1. acao executada (`validated`, `approved` ou `rejected`);
2. resultado (`passed`, `blocked`, `approved` ou `rejected`);
3. ator autenticado na sessao de transporte;
4. instante da execucao; e
5. mensagem resumindo o desfecho.

Esse registro torna o processo observavel mesmo antes de existir persistencia definitiva de propostas em banco.

## Validacao executada

Foram executados dois slices focados:

1. aprovacao valida, com auditoria registrada e nenhuma criacao de assignment;
2. aprovacao bloqueada por indisponibilidade operacional superveniente do veiculo.

Os cenarios estao cobertos em `tests/test_api_flow.py`.

## Limite desta fase

Esta fase ainda nao persiste propostas, nao aplica assignments aprovados e nao exporta o fluxo revisado para XLSX. O objetivo aqui foi fechar o estagio formal entre sugerir e aplicar.