# Fase 6.3 - Auditabilidade completa das decisoes automatizadas ou semiautomatizadas

## Objetivo

Esta fase completa a preparacao do dominio para automacao futura ao tornar a trilha de auditoria da proposal suficientemente explicita para explicar, depois, o que foi decidido, por quem, com base em qual contexto operacional e com qual resultado. O foco nao foi apenas registrar mensagens livres, mas estruturar a auditoria para consumo confiavel por operadores, exportacoes, revisoes futuras e integracoes automatizadas.

## O que foi implementado

1. `TransportProposalAuditEntry` foi ampliado em `sistema/app/schemas.py` para incluir `audit_entry_key`, `context` e `result`.
2. Foram adicionados os contratos `TransportProposalAuditContext` e `TransportProposalAuditResult`, que carregam o contexto operacional utilizado e o resultado objetivo produzido por cada acao auditada.
3. O fluxo contratual de build passou a registrar formalmente a acao `generated`, permitindo rastrear a geracao inicial da proposal no backend.
4. Os fluxos de `validate`, `approve`, `reject` e `apply` passaram a registrar auditoria estruturada com snapshot de avaliacao, origem da proposal, requests e veiculos envolvidos, codigos de inconsistencias e ids das assignments realmente aplicadas.
5. A proposal passou a aceitar `replaces_proposal_key`, permitindo rastrear quando uma nova proposal substitui uma proposta anterior no fluxo de revisao.

## Dados auditados em cada etapa

Cada entrada da trilha agora pode registrar:

1. origem da proposal (`manual`, `system` ou `agent`);
2. chave da proposal e snapshot originalmente associado;
3. snapshot efetivamente usado na avaliacao da etapa, quando houver revalidacao;
4. data operacional, rota, volume e ids das decisoes envolvidas;
5. operador responsavel pela acao;
6. status final observado na proposal naquele ponto;
7. codigos de bloqueio ou inconsistencias encontrados; e
8. ids e quantidade de assignments aplicadas com sucesso, quando houver persistencia.

## Resultado estrutural

Com isso, a trilha de auditoria deixa de ser apenas sequencial e textual. Ela passa a ser tambem explicativa e estruturada, permitindo responder perguntas como:

1. qual snapshot serviu de base para a decisao original;
2. se a proposal foi reavaliada sobre um snapshot mais recente antes de aprovar ou aplicar;
3. quais requests e veiculos estavam no escopo da decisao;
4. quais inconsistencias bloquearam a acao; e
5. quais assignments efetivamente foram persistidas quando a proposal foi aplicada.

## Validacao executada

Foi validado que:

1. o build contract registra a geracao da proposal com contexto e resultado estruturados;
2. aprovacoes bloqueadas passam a carregar os codigos de inconsistencia tambem no resultado auditado;
3. aplicacoes bem-sucedidas registram ids e quantidade de assignments aplicadas; e
4. rejeicoes passam a registrar contexto operacional suficiente para rastrear o escopo da decisao.