# Fase 7.3 - Validacao da prontidao para integracao futura com agente sem depender da interface

## Objetivo

Esta fase fecha a reorganizacao do transporte com um checkpoint arquitetural: validar se o backend agora oferece leitura, comando, revalidacao, auditoria e observabilidade suficientes para que uma futura automacao assistida por IA opere sobre o dominio sem depender do dashboard como camada intermediaria. O objetivo aqui nao e implementar um agente, e sim verificar se a base tecnica ficou adequada para isso.

## Pergunta central desta validacao

Um agente futuro conseguiria:

1. descobrir o estado operacional do transporte por contratos backend estaveis;
2. montar ou solicitar propostas operacionais sem reconstruir a logica do dashboard;
3. submeter comandos auditaveis e revalidaveis antes de persistir mudancas; e
4. entender o que aconteceu depois de cada decisao sem depender de parsing da interface?

## Evidencias concretas de prontidao encontradas

### 1. Leitura operacional explicita no backend

O backend ja expõe leitura dedicada do dominio sem depender da resposta agregada do dashboard:

1. `GET /api/transport/operational-snapshot` devolve o estado operacional do dia e da rota em contrato proprio;
2. `GET /api/transport/reevaluation-events` expõe catalogo e eventos recentes de reavaliacao;
3. `GET /api/transport/work-to-home-time-policy` expõe a resolucao da politica temporal por contexto;
4. `GET /api/transport/dashboard` continua existindo, mas deixou de ser a unica porta de leitura relevante.

Conclusao: a automacao futura nao precisa mais inferir o estado do dominio a partir da montagem incidental da UI.

### 2. Comandos principais ja existem como contratos de backend

O backend ja oferece uma superficie de comandos e transicoes que nao depende de interacao visual:

1. `PUT /api/transport/vehicles/{vehicle_id}` para atualizar cadastro-base por identificador estavel;
2. `PUT /api/transport/vehicle-schedules/{schedule_id}` para atualizar agenda operacional;
3. `POST /api/transport/proposals/build` para construir proposal server-side a partir do snapshot atual;
4. `POST /api/transport/proposals/validate`, `approve`, `reject` e `apply` para tratar a proposal como ciclo operacional explicito;
5. `POST /api/transport/assignments` e `POST /api/transport/requests/reject` como fallback manual ainda disponivel;
6. `POST /api/transport/exports/operational-plan` para materializar a proposta em artefato exportavel.

Conclusao: a futura camada de agente pode operar sobre contratos backend e nao sobre cliques, drag and drop ou montagem local do dashboard.

### 3. Aplicacao de decisao nao depende de confianca cega no cliente

O ponto mais importante para automacao segura ja esta presente: `POST /api/transport/proposals/apply` nao apenas recebe uma proposal, mas exige status `approved`, revalida o snapshot corrente e so entao persiste assignments usando o mesmo motor operacional do fluxo humano.

Conclusao: a automacao futura nao precisara ter permissao para escrever diretamente no estado sem validacao. O backend ja age como guardrail real, e nao apenas como receptor passivo de decisoes externas.

### 4. Auditoria estruturada ficou adequada para consumo por automacao

Os contratos da proposal ja carregam trilha auditavel com estrutura suficiente para consumo por agentes e revisores humanos:

1. `TransportProposalAuditEntry` agora inclui `audit_entry_key`, `context` e `result`;
2. `TransportProposalAuditContext` registra o contexto operacional usado na decisao;
3. `TransportProposalAuditResult` registra status, bloqueios e efeitos resultantes;
4. a proposal aceita `replaces_proposal_key`, permitindo encadear revisoes sucessivas;
5. exportacao operacional ja consome a proposal e sua trilha.

Conclusao: o sistema agora deixa rastros estruturados suficientes para explicar geracao, validacao, aprovacao, rejeicao e aplicacao de decisoes sem depender de memoria da sessao da UI.

### 5. Observabilidade e reacao a mudancas tambem existem fora da UI

O modulo agora emite eventos de reavaliacao e eventos de alteracao de assignment com tipagem explicita, incluindo `transport_request_changed`, `transport_vehicle_schedule_changed`, `transport_timing_policy_changed`, `transport_operational_review_changed` e `transport_assignment_changed`.

Conclusao: um integrador futuro nao precisa observar apenas refresh visual ou SSE generico; ja existe vocabulario de eventos do dominio para reacao operacional e sincronizacao.

### 6. Ja existe artefato declarativo pensado para agentes

Mesmo sem implementar LangChain, o repositorio ja contem um ponto de partida orientado a automacao:

1. `docs/catalogo_acoes_transport.yaml` organiza acoes operacionais em superficie declarativa com endpoint, entradas, pre-condicoes, efeitos colaterais e resultado esperado;
2. `sistema/app/static/transport/functions/functions_by_capability.md` permite rastrear o comportamento do dashboard por capacidade, sem varredura cega do `app.js`.

Conclusao: a base ja nao obriga um agente futuro a descobrir tudo por leitura livre do frontend; ha documentacao intermediaria mais estavel para navegacao e orquestracao.

## O que esta efetivamente pronto para uma futura integracao por agente

Considerando as evidencias acima, a base atual ja esta pronta nos seguintes aspectos:

1. leitura de estado operacional do transporte sem scraping de interface;
2. construcao, validacao, aprovacao, rejeicao e aplicacao de proposals por contratos dedicados;
3. atualizacao de veiculo e agenda por identificadores estaveis;
4. rastreabilidade de decisoes operacionais por trilha de auditoria estruturada;
5. observabilidade por eventos de reavaliacao e eventos de assignment;
6. exportacao de plano operacional a partir da propria proposal.

## Lacunas remanescentes para uma integracao futura ainda mais limpa

Esta validacao tambem identifica o que ainda nao esta ideal para uma integracao por agente, embora ja nao bloqueie a arquitetura:

1. autenticacao ainda esta centrada em sessao HTTP de transporte, adequada ao dashboard, mas ainda nao foi formalizado um modo de credencial tecnica ou service principal para automacao externa controlada;
2. o catalogo declarativo atual ainda nasceu do dashboard e mistura `api`, `composed-api` e `local-ui`; para agentes puramente backend, uma versao futura mais enxuta deveria listar apenas capacidades server-side canonicas;
3. a aprovacao de proposal continua representando um gate de revisao operacional, mas a politica institucional de quando um agente pode apenas sugerir, quando pode aprovar e quando pode aplicar ainda precisa ser definida fora do codigo;
4. a exportacao operacional ainda renderiza a trilha de auditoria em formato tabular resumido, sem espelhar todo o enriquecimento estrutural disponivel nos contratos internos.

## Parecer final da fase

O parecer desta fase e positivo. A reorganizacao deixou o modulo de transporte substancialmente mais preparado para integracao futura com agente sem depender da interface. O backend ja oferece contratos explicitos de leitura, build, validacao, aprovacao, aplicacao e auditoria, com revalidacao server-side e eventos de dominio. A interface deixou de ser o lugar onde a regra realmente existe e passou a ser apenas um dos consumidores possiveis dessas capacidades.

Em outras palavras: a base ainda nao implementa o agente, mas ja nao exige que um agente futuro opere por scraping do dashboard ou por reconstrucoes ad hoc do comportamento visual. A preparacao arquitetural prevista no plano pode ser considerada atendida.