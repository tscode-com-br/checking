# Fase 7.1 - Cobertura de testes focada nos novos contratos de dominio

## Objetivo

Esta fase consolida a protecao automatizada dos contratos de dominio introduzidos nas fases anteriores, com foco especial em pontos que um consumidor automatizado ou um operador futuro vao usar diretamente: snapshot operacional, proposal build/apply, revalidacao de drift, exportacao operacional e eventos derivados da aplicacao.

## O que foi reforcado na suite

Foram adicionados ou ampliados testes focados em `tests/test_api_flow.py` para cobrir:

1. `GET /api/transport/operational-snapshot` como contrato explicito de leitura do dia e da rota selecionados;
2. `POST /api/transport/proposals/apply` no caminho feliz, incluindo persistencia de assignments e emissao de evento `transport_assignment_changed` com `source="transport_proposal"`;
3. revalidacao do apply apos drift operacional, garantindo bloqueio quando a disponibilidade muda depois da aprovacao;
4. bloqueio de apply em proposal ainda `draft`, preservando a exigencia de aprovacao formal; e
5. `POST /api/transport/exports/operational-plan` consumindo uma proposal criada pelo proprio build contract, com preservacao da trilha de auditoria completa no XLSX.

## Resultado pratico

Com essa cobertura, a suite deixa de validar apenas comportamentos internos isolados e passa a proteger explicitamente as fronteiras novas do dominio. Isso reduz o risco de regressao justamente nos contratos backend que sustentarao a automacao futura, sem depender do dashboard como intermediario de teste.

## Validacao executada

Foi executado um lote focado com sucesso para os testes:

1. `test_transport_operational_snapshot_endpoint_returns_contract_for_selected_date_and_route`
2. `test_transport_proposal_apply_contract_persists_assignments_after_approval`
3. `test_transport_proposal_apply_contract_revalidates_after_operational_drift`
4. `test_transport_proposal_apply_contract_blocks_draft_proposal`
5. `test_transport_operational_plan_export_supports_contract_built_proposal_audit_trail`