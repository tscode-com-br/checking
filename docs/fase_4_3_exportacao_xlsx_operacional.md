# Fase 4.3 - Exportacao XLSX operacional para proposta e aprovacao

## Objetivo

Esta fase evolui a exportacao de transporte de uma listagem simples para um artefato operacional capaz de apoiar revisao, aprovacao e comunicacao. O foco deixa de ser apenas listar assignments confirmados e passa a incluir o contexto do snapshot, a proposta em revisao, as pendencias, os conflitos e a trilha de auditoria que explica o estado exportado.

## O que foi implementado

1. O modulo `sistema/app/services/transport_exports.py` passou a concentrar um novo builder rico, `build_transport_operational_plan_export`, mantendo `build_transport_list_export` como wrapper compativel.
2. O endpoint existente `GET /api/transport/exports/transport-list` continuou disponivel e passou a gerar um workbook mais rico sem quebrar a aba principal `Transport List`.
3. Foi criado o novo endpoint `POST /api/transport/exports/operational-plan`, que recebe uma `TransportOperationalProposal` e gera uma planilha operacional baseada no snapshot e na proposta revisada.

## Estrutura do workbook

Quando a exportacao operacional e gerada, o XLSX passa a poder conter as seguintes abas:

1. `Transport List`: lista atual de assignments confirmados, preservada como superficie compativel para a operacao atual.
2. `Executive Summary`: resumo executivo com modo do export, data, rota, horario relevante, totais de requests, totais de veiculos, status da proposta, quantidade de decisoes, quantidade de issues e quantidade de eventos de auditoria.
3. `Vehicle Load`: lotacao atual e lotacao projetada por veiculo, incluindo saldo restante por placa.
4. `Snapshot Requests`: retrato completo dos requests visiveis no snapshot usado para a exportacao.
5. `Proposed Decisions`: distribuicao sugerida pela proposta, com request, passageiro, status sugerido, veiculo e justificativa.
6. `Exceptions`: pendencias, rejeicoes e issues de validacao relevantes para a revisao operacional.
7. `Audit Trail`: historico de validacao, aprovacao ou rejeicao associado a proposta exportada.

## Decisao de compatibilidade

A primeira aba continua sendo `Transport List`, preservando a leitura operacional ja conhecida. A mudanca da fase 4.3 foi feita de forma aditiva: a exportacao antiga continua funcional, mas o workbook deixa de ser um artefato plano e passa a incorporar contexto suficiente para processo de aprovacao.

## Resultado operacional

Com essa etapa, a exportacao em XLSX deixa de refletir apenas o estado final confirmado e passa a representar tambem:

1. o snapshot usado para decidir;
2. a proposta em revisao ou ja aprovada;
3. a diferenca entre estado atual e distribuicao sugerida;
4. as pendencias e inconsistencias que impedem aprovacao; e
5. os eventos de auditoria associados ao ciclo de revisao.

## Validacao executada

Foi validado um fluxo focado de ponta a ponta em que:

1. uma proposta e montada e aprovada sem aplicar assignments;
2. o endpoint `POST /api/transport/exports/operational-plan` gera o XLSX correspondente; e
3. o workbook resultante contem todas as abas esperadas e os principais dados de resumo, proposta, excecoes e auditoria.

## Limite desta fase

Esta fase ainda nao aplica assignments aprovados, nao persiste versoes historicas do arquivo em banco e nao implementa distribuicao automatica. O objetivo aqui foi transformar a exportacao em artefato de decisao operacional, alinhado ao fluxo de proposta e aprovacao da Fase 4.