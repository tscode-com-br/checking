# Fase 1.2 - Relação priorizada dos acoplamentos críticos do transporte

## Objetivo desta etapa

Esta etapa aprofunda o diagnóstico iniciado na fase 1.1 e transforma os hotspots já mapeados em uma relação priorizada de acoplamentos críticos, com foco explícito nas interdependências entre dashboard, veículo, agenda e alocação. O objetivo não é apenas dizer que o módulo está acoplado, mas explicar exatamente onde o acoplamento acontece, por que ele é perigoso, qual o efeito prático de mantê-lo como está e em que ordem vale a pena atacar cada extração.

Este documento também serve como ponte entre o inventário técnico da fase 1.1 e as extrações estruturais que começam nas etapas seguintes. A partir dele, a reorganização deixa de ser guiada por impressões gerais e passa a ser guiada por uma fila de problemas concretos, priorizados por risco técnico, impacto operacional e dependência entre extrações.

## Critérios usados para priorização

Os acoplamentos foram priorizados com base nos critérios abaixo:

- centralidade no fluxo atual do módulo;
- risco de regressão em comportamentos já usados pelo dashboard;
- impacto operacional direto para quem administra transporte no dia a dia;
- bloqueio que o acoplamento impõe à edição completa de veículo;
- bloqueio que o acoplamento impõe à futura camada de proposta, aprovação e automação.

Convenção de prioridade:

- `P0`: acoplamento estrutural prioritário. Deve ser atacado antes das extrações dependentes.
- `P1`: acoplamento importante, mas cuja extração fica mais segura depois dos `P0`.
- `P2`: acoplamento relevante para consolidação e manutenção, mas não deve ser o primeiro alvo.

## Visão executiva

O módulo de transporte hoje tem quatro pontos de amarração mais perigosos. O primeiro é a leitura agregada do dashboard, que conhece o estado de requests, alocações, agendas, veículos e regras temporais de uma vez só. O segundo é o fluxo de veículo, que ainda mistura cadastro-base e agenda operacional. O terceiro é a remoção de veículo, que opera com semântica destrutiva ampla a partir de `schedule_id`. O quarto é a persistência de alocações recorrentes, que mistura decisão do dia com propagação futura.

Esses quatro pontos formam o núcleo do problema atual. Enquanto eles permanecerem juntos, qualquer tentativa de introduzir edição completa de veículo, proposta operacional, exportação mais rica ou integração futura com IA continuará apoiada em bases frágeis. Por isso, a fase 1.2 recomenda começar pelo desacoplamento do backend, não do frontend.

## Matriz priorizada de acoplamentos críticos

| ID | Acoplamento | Componentes principais | Evidência prática | Risco técnico | Impacto operacional | Prioridade |
| --- | --- | --- | --- | --- | --- | --- |
| CT-01 | Dashboard agregado demais | `build_transport_dashboard`, `_build_vehicle_rows_for_dashboard`, `_build_transport_vehicle_registry_rows`, `_build_recurring_assignment_template_index`, `_list_transport_assignments_for_requests` | A mesma leitura monta requests, alocações, templates recorrentes, veículos e agendas no mesmo fluxo | Mudança local em leitura pode quebrar múltiplos subdomínios ao mesmo tempo | Dashboard fica sensível a qualquer ajuste de disponibilidade, recorrência ou composição de veículos | `P0` |
| CT-02 | Cadastro de veículo misturado com agenda operacional | `create_transport_vehicle_registration`, `_build_schedule_specs_from_payload`, `_classify_vehicle_schedules_for_reuse`, `_vehicle_has_active_schedule_for_spec` | O cadastro já decide se reutiliza veículo existente, desativa agendas antigas e cria novas agendas no mesmo comando | Impossibilita separar edição cadastral de alteração operacional | Administrador não consegue alterar veículo com segurança sem herdar efeitos laterais de agenda | `P0` |
| CT-03 | Remoção destrutiva de veículo acoplada a assignments e exceções | `delete_transport_vehicle_registration`, `_purge_foreign_key_dependencies`, `TransportAssignment`, `TransportVehicleScheduleException`, `TransportVehicleSchedule` | A remoção parte de `schedule_id`, mas apaga o conjunto operacional do veículo | Alto risco de efeitos cascata amplos e custo alto de manutenção | Remover um item visual da lista pode significar perder contexto operacional maior do que o operador imagina | `P0` |
| CT-04 | Comando do dia acoplado à persistência recorrente | `upsert_transport_assignment_with_persistence`, `_propagate_confirmed_recurring_assignment`, `_materialize_recurring_assignments_for_date`, `_reset_transport_request_assignments_to_pending` | Confirmar ou devolver uma alocação pode mexer no comportamento recorrente do pedido | Dificulta introduzir preview, proposta, aprovação e reprocessamento controlado | Operações aparentemente pontuais alteram desfechos futuros e ampliam risco de surpresa operacional | `P0` |
| CT-05 | Contrato HTTP de veículo preso à semântica atual de criação e remoção | `create_transport_vehicle`, `delete_transport_vehicle_for_route`, `TransportVehicleCreate`, ausência de schema de update | A API só oferece criação e remoção, mas não representa edição explícita do cadastro | Mantém a semântica do domínio incompleta e empurra clientes para fluxos destrutivos | Operadores e futuros consumidores não conseguem alterar veículo com rastreabilidade adequada | `P1` |
| CT-06 | Integridade relacional apoiada em chaves de negócio mutáveis | `User.workplace`, `Workplace.workplace`, `User.placa`, `Vehicle.placa` | Workplace e placa ainda funcionam como eixo de vínculo entre entidades | Alterações cadastrais importantes tendem a ser caras, frágeis ou bloqueadas | Editar placa ou workplace pode trazer impacto estrutural maior do que o operador espera | `P1` |
| CT-07 | Consumidores administrativos e web no mesmo serviço monolítico | `build_transport_dashboard`, `build_web_transport_state`, `_build_web_transport_request_items` | O mesmo arquivo concentra leitura para dashboard administrativo e estado web do usuário | Mudança para um consumidor pode alterar comportamento de outro sem intenção | Fica mais difícil evoluir transporte administrativo sem interferir no fluxo do usuário final | `P1` |
| CT-08 | Frontend monolítico dependente de detalhes internos do backend atual | `app.js`, `loadDashboard`, `submitAssignment`, `removeVehicleFromRoute`, `openVehicleModal`, `renderDashboard` | A UI concentra integração, renderização, estado e operação em um único arquivo | A manutenção da interface continua cara e pouco modular | A interface permanece difícil de alinhar às novas fronteiras do domínio | `P2` |

## Análise detalhada por acoplamento

### CT-01. Dashboard agregado demais

Onde aparece: no fluxo de `build_transport_dashboard`, que lê projetos, workplaces, requests, assignments, schedules, vehicles, templates recorrentes e estados derivados antes de montar uma única resposta para a UI.

Por que é crítico: esta função não é apenas uma consulta. Ela já embute interpretação de regra de negócio, seleção de assignment explícita versus recorrente, fallback de veículo, cache de agenda e composição final do payload visual. Isso significa que qualquer extração futura de agenda, alocação ou recorrência ficará mais arriscada enquanto o dashboard continuar centralizando todas essas decisões.

Risco técnico específico: regressões em cadeia. Um ajuste simples em disponibilidade de veículo pode quebrar a forma como o dashboard monta status de pedido, occupancy visual ou associação de vehicle row.

Impacto operacional específico: a tela administrativa é o principal ponto de operação. Quando a montagem do dashboard é frágil, o operador perde confiança no retrato do dia justamente no lugar onde precisa enxergar requests, veículos e pendências.

Extração recomendada: criar uma camada de consulta do dashboard com fronteiras menores, separando leitura de requests, leitura de vehicles/schedules, leitura de assignments e composição final do payload.

### CT-02. Cadastro de veículo misturado com agenda operacional

Onde aparece: em `create_transport_vehicle_registration`, que procura veículo por placa, decide se o cadastro pode ser reaproveitado, desativa agendas reutilizáveis, altera dados do cadastro-base e cria novas agendas operacionais a partir do payload.

Por que é crítico: este fluxo faz o sistema tratar uma mesma operação como atualização cadastral, reaproveitamento estrutural e criação de disponibilidade operacional ao mesmo tempo. O resultado é que o conceito de veículo fica semanticamente borrado.

Risco técnico específico: o sistema não consegue evoluir para um contrato limpo de edição de veículo enquanto a atualização de dados-base depender do mesmo fluxo que cria ou substitui agenda.

Impacto operacional específico: o operador não tem uma distinção segura entre “editar o veículo” e “mudar quando esse veículo atende”. Isso torna qualquer futura edição completa sujeita a efeitos não esperados.

Extração recomendada: criar dois serviços separados, um para cadastro-base do veículo e outro para agenda operacional do veículo, com contratos distintos e regras próprias.

### CT-03. Remoção destrutiva de veículo acoplada a assignments e exceções

Onde aparece: em `delete_transport_vehicle_registration`, que recebe `schedule_id`, resolve o veículo correspondente e então apaga assignments, schedules e exceptions associados, com apoio de `_purge_foreign_key_dependencies`.

Por que é crítico: o identificador de entrada sugere uma operação localizada em agenda, mas o efeito real é amplo e estrutural. O sistema ainda trata o conjunto do veículo como algo que só pode ser removido limpando múltiplas dependências em cascata.

Risco técnico específico: a semântica de remoção fica opaca e perigosa. Isso dificulta a introdução de desativação lógica, aposentadoria de agenda, arquivamento e trilha de auditoria mais precisa.

Impacto operacional específico: uma exclusão executada a partir do contexto da tela pode eliminar mais estado do que o operador imagina, o que é especialmente problemático quando houver necessidade de revisar decisões passadas.

Extração recomendada: separar claramente remoção de agenda, desativação operacional e eventual exclusão do cadastro-base, cada uma com seu próprio contrato e impacto explícito.

### CT-04. Comando do dia acoplado à persistência recorrente

Onde aparece: em `upsert_transport_assignment_with_persistence`, que, para requests `regular` e `weekend`, não trata a confirmação como um evento apenas da data atual. Em vez disso, ele chama `_propagate_confirmed_recurring_assignment` e interfere na lógica recorrente.

Por que é crítico: o módulo ainda mistura “decisão operacional desta data” com “template recorrente do pedido”. Isso impede a existência de um estágio intermediário de proposta, revisão ou simulação.

Risco técnico específico: toda mudança na lógica de confirmação carrega risco de alterar comportamento futuro sem que o ponto de entrada deixe isso claro.

Impacto operacional específico: uma confirmação feita pelo administrador pode repercutir para outros dias de forma implícita, o que aumenta o risco de alocação inesperada ou de dificuldade para entender por que determinado pedido apareceu confirmado depois.

Extração recomendada: separar comando pontual do dia, template recorrente e materialização futura. Esses três conceitos hoje ainda estão próximos demais.

### CT-05. Contrato HTTP de veículo preso à semântica atual de criação e remoção

Onde aparece: no roteador de transporte e nos schemas atuais, que expõem `TransportVehicleCreate`, criação e remoção, mas não expõem atualização explícita de veículo nem atualização explícita de agenda.

Por que é relevante: mesmo que o backend interno seja melhorado, o cliente continuará preso a fluxos assimétricos se a superfície HTTP continuar modelando apenas criar e apagar.

Risco técnico específico: qualquer consumidor novo do módulo tenderá a reproduzir o acoplamento atual, porque a API ainda o incentiva.

Impacto operacional específico: o operador continua sem semântica clara para alterar cadastro e agenda como operações separadas.

Extração recomendada: introduzir contratos independentes para atualizar veículo e atualizar agenda, alinhados às fronteiras do domínio reorganizado.

### CT-06. Integridade relacional apoiada em chaves de negócio mutáveis

Onde aparece: na modelagem em que `User.workplace` se liga a `Workplace.workplace` e `User.placa` se liga a `Vehicle.placa`.

Por que é relevante: esses campos precisam continuar editáveis no negócio, mas ainda exercem papel estrutural demais no modelo atual.

Risco técnico específico: qualquer edição posterior em placa ou workplace tende a exigir estratégias frágeis de atualização em cascata ou bloqueios artificiais de edição.

Impacto operacional específico: editar um dado aparentemente simples pode ter custo estrutural alto e inesperado.

Extração recomendada: migrar o eixo relacional para identificadores estáveis e manter placa e workplace como atributos de negócio, não como pivôs de integridade.

### CT-07. Consumidores administrativos e web no mesmo serviço monolítico

Onde aparece: no mesmo arquivo de serviços, que abriga tanto a leitura administrativa do dashboard quanto a montagem de estado para consumo web do usuário final.

Por que é relevante: embora os dados sejam correlatos, os consumidores têm objetivos diferentes. O administrativo precisa de visão operacional agregada; o web precisa de estado orientado ao pedido e ao usuário.

Risco técnico específico: ajustes de regra para um consumidor podem vazar para outro por compartilharem o mesmo serviço monolítico.

Impacto operacional específico: manutenção mais lenta e mais propensa a regressão cruzada entre fluxo administrativo e fluxo web.

Extração recomendada: separar consultas por consumidor, mantendo núcleo de regra reutilizável apenas onde ele fizer sentido.

### CT-08. Frontend monolítico dependente de detalhes internos do backend atual

Onde aparece: no `app.js`, que concentra autenticação, SSE, renderização, datas, operações de request, operações de veículo, modais, filtros e sincronização visual.

Por que é relevante: o frontend já possui documentação adequada, mas ainda continua sustentado por um arquivo único que espelha a concentração do backend.

Risco técnico específico: modularizar cedo demais, antes do backend, gera reorganização visual sem ganho estrutural real.

Impacto operacional específico: a UI continua cara de manter, mas esse custo ainda é secundário em comparação ao núcleo do backend.

Extração recomendada: deixar a modularização do frontend para depois das primeiras separações de backend.

## Fila recomendada de ataque

### Ordem 1. Separar a leitura do dashboard

Justificativa: esta extração reduz acoplamento sem mexer primeiro nas regras destrutivas de escrita. Ela cria a primeira fronteira de leitura estável e prepara o terreno para reorganizar veículo, agenda e alocação com menos risco de contaminar a visão administrativa.

### Ordem 2. Separar cadastro-base de veículo e agenda operacional

Justificativa: este é o ponto mais diretamente ligado ao requisito de editar o veículo sem remover e recriar. Sem essa separação, qualquer contrato futuro de update continuará apoiado em semântica confusa.

### Ordem 3. Reescrever a semântica de remoção

Justificativa: a operação de remoção precisa deixar de ser um atalho destrutivo baseado em `schedule_id`. Isso é essencial para segurança operacional e para futura auditabilidade.

### Ordem 4. Isolar comando do dia da persistência recorrente

Justificativa: a futura camada de proposta e aprovação depende de conseguir representar decisões sem aplicá-las automaticamente à recorrência. Enquanto isso não for separado, o módulo continuará sem espaço seguro para preview e aprovação.

### Ordem 5. Consolidar contratos HTTP coerentes com o domínio reorganizado

Justificativa: depois que os limites internos estiverem mais claros, a API pode finalmente refletir o negócio real, com atualização de veículo e atualização de agenda como operações distintas.

### Ordem 6. Migrar dependências de chaves mutáveis

Justificativa: essa mudança é estrutural e importante, mas fica mais segura depois que o domínio já estiver semanticamente mais limpo. Ela deve entrar cedo no roadmap, mas não antes das primeiras separações essenciais.

### Ordem 7. Modularizar o frontend em cima das novas fronteiras

Justificativa: só depois de o backend deixar claro o que é leitura, o que é comando, o que é veículo e o que é agenda vale modularizar a interface com ganho real.

## Dependências entre extrações

As relações abaixo ajudam a evitar iniciar uma extração no momento errado:

- A extração de update explícito de veículo depende da separação entre cadastro-base e agenda operacional.
- A redução da destrutividade do fluxo de remoção depende de explicitar o que é agenda e o que é cadastro-base.
- A futura camada de proposta depende do desacoplamento entre comando do dia e recorrência.
- A migração de chaves mutáveis fica mais segura depois que os contratos do domínio estiverem semanticamente separados.
- A modularização do frontend rende mais depois que a API e os serviços internos já estiverem mais claros.

## O que não deve ser feito primeiro

Para esta fase, também é importante registrar o que não deve ser atacado antes do núcleo do problema:

- Não começar pela modularização do `app.js` como se ela resolvesse o acoplamento principal do domínio.
- Não introduzir um endpoint de update de veículo sem antes separar claramente veículo e agenda.
- Não migrar imediatamente todas as chaves mutáveis sem antes reduzir a ambiguidade semântica do backend.
- Não tentar construir proposta operacional ou automação em cima do fluxo atual de confirmação recorrente.

## Resultado esperado desta fase 1.2

Com a execução desta etapa, a reorganização passa a ter uma relação priorizada de acoplamentos críticos, com justificativa técnica e impacto operacional explícitos. Isso permite decidir com mais segurança quais extrações devem ocorrer primeiro e quais mudanças ainda precisam esperar uma base estrutural melhor.

Na prática, a fase 1.2 conclui três coisas. Primeiro, que o núcleo do problema está no backend, e não na camada visual. Segundo, que o requisito de editar veículos sem exclusão depende de separar cadastro-base, agenda e remoção. Terceiro, que a futura camada de proposta e aprovação só será segura quando a decisão do dia deixar de estar acoplada à persistência recorrente.