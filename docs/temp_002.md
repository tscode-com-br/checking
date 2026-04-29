# Plano de reorganização do transporte para suporte futuro a agente de IA

## Objetivo do plano

Este plano tem como objetivo reorganizar o módulo de transporte para que, no futuro, um agente de IA integrado via LangChain consiga operar sobre contratos estáveis de backend, e não sobre comportamentos implícitos do dashboard web. O foco deste documento não é implementar o agente agora, mas preparar a arquitetura, o modelo de dados e a superfície de APIs para que a automação futura possa consultar informações, montar propostas, gerar artefatos de aprovação e aplicar mudanças de forma previsível, auditável e segura.

A reorganização precisa atender a dois cenários ao mesmo tempo. O primeiro é a operação humana atual, que já depende do dashboard e das rotinas administrativas existentes. O segundo é a automação futura, que deverá executar ações de alto impacto sem depender de cliques, do estado do DOM ou de interpretações frágeis da interface. Para isso, o sistema precisa deixar de concentrar a lógica do domínio em fluxos amplos e implícitos, passando a expor comandos claros, consultas especializadas, validações explícitas e regras de negócio separadas por responsabilidade.

Hoje, a base já oferece parte importante desse domínio, como o dashboard de transporte, o cadastro de workplaces, o cadastro e a remoção de veículos, a persistência de pedidos e alocações, e a exportação de uma planilha simples. No entanto, esses elementos ainda estão muito próximos entre si. A leitura agregada do dashboard, a gestão operacional de veículos, a criação de agendas, a exportação em XLSX e as alocações por data ainda convivem em uma mesma superfície de serviço. Isso dificulta a evolução para um modelo em que humanos e automações utilizem os mesmos contratos do servidor com segurança e rastreabilidade.

Há ainda um requisito funcional que precisa entrar desde já no desenho estrutural: depois que um veículo for cadastrado, todas as suas características devem poder ser alteradas sem exigir exclusão e novo cadastro. Isso inclui, no mínimo, placa, tipo, cor, quantidade de lugares, tolerância e escopo de serviço. Essa mudança não deve ser tratada como ajuste cosmético de interface, porque hoje o domínio de veículo está acoplado à criação e à reutilização de agendas operacionais. Enquanto esse acoplamento permanecer, qualquer automação futura continuará herdando um fluxo destrutivo, sujeito a efeitos colaterais e difícil de auditar.

O plano também precisa preparar o terreno para três capacidades futuras, sem implementá-las agora. A primeira é a geração de propostas de distribuição de passageiros e roteirização. A segunda é a produção de planilhas de aprovação mais ricas do que a exportação atual, capazes de sustentar revisão operacional e tomada de decisão. A terceira é um modo automático capaz de reagir a novos pedidos ou mudanças relevantes no transporte. Nenhuma dessas capacidades deve nascer diretamente sobre a interface atual. Todas precisam se apoiar em um backend reorganizado em torno de entidades bem separadas, regras explícitas, identificadores estáveis e comandos auditáveis.

## Plano de reorganização

### 1. Separar leitura operacional de comandos com efeito colateral

O primeiro passo é separar claramente o que é consulta do que é comando. A montagem do dashboard deve ser tratada como uma camada de leitura especializada, responsável por compor dados para visualização sem carregar consigo decisões de escrita, reaproveitamento implícito ou efeitos operacionais. Em paralelo, as ações que alteram o estado do sistema, como editar veículo, alterar agenda, alocar passageiro, rejeitar solicitação, gerar proposta ou aprovar lote, devem ser expostas como comandos explícitos e independentes.

Essa separação é necessária para que o sistema deixe de depender de um único fluxo agregador para leitura e mutação. Para um agente futuro, isso é decisivo: a automação deve consultar um retrato consistente do domínio e, em seguida, acionar comandos específicos, com regras e validações próprias, em vez de inferir comportamento a partir da estrutura do dashboard.

### 2. Separar o cadastro-base do veículo da agenda operacional do veículo

O domínio atual precisa deixar mais explícita a diferença entre o veículo como entidade cadastral e a agenda do veículo como disponibilidade operacional. O cadastro-base deve concentrar a identidade e a configuração do veículo, como placa, tipo, cor, lotação e tolerância. A agenda deve concentrar quando, em que contexto e em qual trajeto o veículo está disponível para atendimento.

Essa separação é importante porque a edição do veículo não pode continuar sendo tratada como um efeito colateral do fluxo de criação de agendas. Quando a identidade do veículo e sua disponibilidade operacional ficam misturadas, mudanças simples de cadastro passam a carregar risco de desativar agendas, conflitar com reutilizações internas ou afetar alocações de maneira pouco transparente.

### 3. Introduzir edição completa de veículo sem exclusão e recriação

O sistema deve ganhar um fluxo explícito de edição de veículo baseado em identificador estável, e não em exclusão seguida de novo cadastro. Esse fluxo precisa permitir a alteração de todas as características do veículo já cadastrado, inclusive placa, tipo, cor, lugares, tolerância e escopo de serviço, com validações claras sobre o que pode ser mudado livremente e o que exige tratamento adicional por impactar agendas e alocações existentes.

Esse ponto é central para o objetivo do plano. Sem ele, a operação humana continuará sujeita a retrabalho e perda de contexto, e a automação futura ficará presa a um processo destrutivo. A regra correta é que editar um veículo atualize o veículo; editar uma agenda atualize a agenda; e qualquer impacto sobre alocações seja tratado de forma explícita, com validação e rastreabilidade.

### 4. Migrar relacionamentos hoje baseados em chaves mutáveis para identificadores estáveis

Há relacionamentos do domínio que ainda dependem de valores de negócio mutáveis, como nome textual e placa, em vez de depender de identificadores internos estáveis. Isso é especialmente sensível em qualquer cenário que exija edição posterior, porque alterar um atributo que também funciona como chave de relacionamento amplia o risco de inconsistência, efeitos colaterais silenciosos e custos desnecessários de manutenção.

O plano deve prever a migração gradual desses vínculos para chaves técnicas estáveis, preservando os valores de negócio apenas como atributos editáveis. Essa mudança é necessária tanto para a edição completa de veículos quanto para a futura automação, que precisa operar sobre referências imutáveis e semanticamente claras.

### 5. Redefinir de forma inequívoca onde vivem as regras de escopo e disponibilidade

O sistema precisa definir com clareza se o escopo de serviço pertence ao veículo, à agenda do veículo ou a ambos sob regras bem delimitadas. Enquanto a mesma informação operacional ficar espalhada entre camadas ou entidades com significado parcialmente sobreposto, qualquer mudança de cadastro ou de disponibilidade continuará sujeita a interpretações ambíguas.

O objetivo desta etapa é eliminar duplicidade semântica. O backend deve ter uma única fonte de verdade para cada regra operacional relevante, deixando explícito o que define a natureza do veículo e o que define sua disponibilidade em determinada data, recorrência ou trajeto. Essa definição é indispensável para viabilizar edição segura, proposta automatizada e auditoria posterior.

### 6. Criar uma camada de proposta e aprovação antes de qualquer automação inteligente

Antes de introduzir um agente de IA, o sistema deve ganhar uma camada intermediária de proposta operacional. Em vez de transformar uma sugestão de distribuição em confirmação imediata, o backend deve ser capaz de gerar uma proposta baseada em um retrato consistente do dia, validar restrições, apontar conflitos, registrar justificativas e somente depois permitir aprovação, rejeição ou aplicação.

Essa camada é o ponto de controle que falta para unir operação humana e automação futura. Com ela, o mesmo domínio pode sustentar sugestões manuais, simulações internas e, mais adiante, recomendações geradas por IA, sem abrir mão de governança, previsibilidade e revisão operacional.

### 7. Redesenhar a exportação em XLSX como artefato de aprovação e operação

A exportação atual deve evoluir de uma simples lista final para um artefato operacional mais completo. O objetivo não é apenas exportar o que já foi confirmado, mas permitir que a planilha sirva como base de revisão, aprovação e comunicação operacional. Isso exige um desenho mais rico, com separação entre resumo, alocações propostas ou aprovadas, pendências, rejeições, lotação por veículo, conflitos e metadados de geração.

Ao transformar a exportação em um artefato de processo, o sistema deixa de tratar o XLSX como reflexo tardio da tela e passa a tratá-lo como saída formal de uma etapa de decisão. Essa mudança é importante para o fluxo humano atual e será ainda mais importante quando houver geração automatizada de propostas no futuro.

### 8. Enriquecer a modelagem de workplace, horários e restrições operacionais

Se o sistema precisará sustentar planejamento mais sofisticado, ele não pode depender apenas de campos mínimos de workplace e de um único horário geral para retorno. O plano deve prever a evolução gradual da modelagem operacional para contemplar melhor os pontos de embarque e destino, as regras de horário, janelas de atendimento e demais atributos que impactam o planejamento de transporte.

Essa etapa não exige implementar um otimizador agora. O objetivo é garantir que, quando houver necessidade de distribuir passageiros, priorizar atendimentos, reagrupar veículos ou produzir propostas mais inteligentes, o domínio já esteja representando as informações certas de forma consistente e reutilizável.

### 9. Preparar o backend para um modo automático orientado a eventos, sem implementar o agente agora

O futuro modo automático não deve nascer como uma extensão da interface web. Ele deve ser acionado a partir de eventos internos relevantes, como criação de pedido, alteração de solicitação, mudança de disponibilidade de veículo ou revisão operacional de um determinado dia. A função do plano, neste momento, é apenas preparar esses pontos de entrada e os contratos internos que eles acionarão depois.

Isso significa estruturar o domínio para que eventos relevantes possam disparar geração de snapshot, validação de regras, montagem de proposta, exportação e eventual aplicação, sempre de forma controlada. O agente de IA, quando existir, deverá atuar sobre essa camada já estável, e não sobre detalhes acidentais do dashboard.

### 10. Preservar auditabilidade, previsibilidade e reversibilidade

Toda reorganização proposta aqui deve ser guiada por três critérios permanentes. O primeiro é auditabilidade: o sistema precisa deixar claro quem gerou, aprovou, alterou ou aplicou determinada decisão operacional. O segundo é previsibilidade: cada comando deve ter entradas, validações e resultados explícitos. O terceiro é reversibilidade: operações relevantes devem poder ser refeitas, invalidadas ou reaplicadas com segurança, sem depender de reconstrução manual do contexto.

Esses critérios são importantes independentemente da existência futura de um agente. No entanto, tornam-se obrigatórios quando se pretende permitir que decisões operacionais passem a ser sugeridas ou executadas com apoio de automação.

## Sequência recomendada de execução

### Fase 1. Isolar responsabilidades sem alterar comportamento

O primeiro movimento deve ser reorganizar o código existente em serviços menores e mais específicos, preservando o comportamento atual. O objetivo é reduzir o acoplamento entre leitura do dashboard, regras de veículo, agendas, alocações e exportação, criando uma base mais legível e segura para mudanças posteriores.

### Fase 2. Introduzir edição explícita de veículo e separar agenda de cadastro

Na sequência, o sistema deve ganhar um contrato explícito de atualização de veículo por identificador estável, separado da gestão de agenda. Essa fase deve consolidar o princípio de que mudanças cadastrais não exigem exclusão e recriação, e de que impactos operacionais precisam ser tratados de forma deliberada.

### Fase 3. Normalizar relacionamentos e consolidar regras operacionais

Depois disso, o foco deve ser migrar dependências de chaves mutáveis para identificadores estáveis e definir de forma inequívoca a fonte de verdade das regras de escopo, recorrência e disponibilidade. Essa fase reduz risco estrutural e prepara o terreno para fluxos mais sofisticados.

### Fase 4. Criar a camada de proposta, aprovação e exportação operacional

Com a base reorganizada, o sistema já pode ganhar uma camada formal de proposta operacional, revisão e exportação enriquecida. Esse é o ponto em que a operação humana passa a utilizar um fluxo que também servirá de fundação para a automação futura.

### Fase 5. Preparar a entrada por eventos para o modo automático futuro

Somente depois das fases anteriores faz sentido estruturar os gatilhos internos que permitirão a um agente de IA atuar no domínio. Nessa etapa, o sistema já estará organizado em torno de contratos estáveis, regras explícitas e superfícies seguras para automação.

## Resultado esperado

Ao final dessa reorganização, o módulo de transporte deverá estar preparado para evoluir de um dashboard operacional centrado em interface para uma plataforma de decisões operacionais com contratos estáveis. A operação humana continuará atendida, mas deixará de depender de fluxos implícitos e frágeis. O backend passará a oferecer uma base mais adequada para propostas, aprovação, exportação e automação futura.

O requisito de edição completa de veículos sem exclusão e recriação deverá estar incorporado à arquitetura como regra estrutural, e não como ajuste isolado. Com isso, o sistema reduzirá retrabalho operacional, ganhará consistência semântica e ficará apto para receber, em momento posterior, um agente de IA construído sobre comandos auditáveis e dados confiáveis.

## To-do list detalhada por fases

### Fase 1. Diagnóstico técnico e isolamento de responsabilidades

#### 1.1 Mapear, por arquivo e por função, as responsabilidades atuais do módulo de transporte

Descrição: levantar de forma objetiva quais trechos do backend hoje são responsáveis por leitura do dashboard, cadastro de veículo, gestão de agenda, alocação, exportação, autenticação e notificações de atualização. O objetivo desta tarefa é transformar o estado atual em um inventário técnico claro, para que a reorganização posterior não quebre comportamentos silenciosos nem deixe regras órfãs.

Implementação inicial desta etapa: ver `docs/fase_1_1_inventario_tecnico_transporte.md`, que consolida o mapa técnico inicial por arquivo, grupos funcionais, hotspots de acoplamento, matriz explícita de criticidade e prioridade recomendada de extração.

Entregável esperado: uma lista consolidada de serviços, rotas, schemas e modelos envolvidos em transporte, com indicação do que é leitura, do que é comando e do que hoje acumula mais de uma responsabilidade.

Critério de conclusão: existir um mapa técnico suficiente para decidir com segurança quais extrações podem ocorrer sem alteração comportamental.

#### 1.2 Identificar os pontos de maior acoplamento entre dashboard, veículo, agenda e alocação

Descrição: registrar onde o mesmo fluxo manipula simultaneamente dados de naturezas diferentes, principalmente nos pontos em que o sistema reutiliza entidades existentes, desativa agendas, recalcula disponibilidade ou interfere em alocações ao atender uma operação aparentemente simples. Esta tarefa é importante porque o sucesso da reorganização depende de atacar primeiro os acoplamentos que hoje tornam o domínio difícil de evoluir.

Implementação inicial desta etapa: ver `docs/fase_1_2_acoplamentos_criticos_transporte.md`, que organiza os acoplamentos críticos por prioridade, risco técnico, impacto operacional, dependências entre extrações e ordem recomendada de ataque.

Entregável esperado: uma relação priorizada dos acoplamentos críticos, com indicação do risco técnico de cada um e do impacto operacional caso eles permaneçam inalterados.

Critério de conclusão: estar claro quais trechos precisam ser extraídos primeiro e quais dependências não podem mais continuar implícitas.

#### 1.3 Extrair a montagem do dashboard para uma camada de consulta dedicada

Descrição: reorganizar a leitura do dashboard para que ela fique concentrada em um serviço de consulta explicitamente voltado à composição de dados para visualização. O objetivo não é alterar o que o dashboard mostra nesta fase, mas separar a leitura das regras que alteram estado, reduzindo a mistura entre consulta e mutação.

Implementação inicial desta etapa: ver `docs/fase_1_3_extracao_dashboard_queries.md`. Nesta fase, a montagem do dashboard foi extraída para `sistema/app/services/transport_dashboard_queries.py`, mantendo wrappers compatíveis em `sistema/app/services/transport.py` e validando a preservação de comportamento com testes focados do endpoint de dashboard.

Entregável esperado: uma camada de leitura mais nítida, isolada dos comandos operacionais, com interfaces internas mais fáceis de entender, testar e evoluir.

Critério de conclusão: a geração do dashboard ocorrer sem depender de funções que também executam escrita, reaproveitamento destrutivo ou mutações laterais.

#### 1.4 Separar exportação, cadastro de veículo e alocação em serviços internos distintos

Descrição: reorganizar o módulo para que exportação, operações de veículo e persistência de alocação não permaneçam misturadas na mesma superfície lógica. Esta tarefa prepara o terreno para comandos mais explícitos e para uma futura camada de propostas, além de reduzir o risco de regressões em operações administrativas.

Implementação inicial desta etapa: ver `docs/fase_1_4_separacao_servicos_operacionais.md`. Nesta fase, a exportação foi extraída para `sistema/app/services/transport_exports.py`, as operações de veículo e agenda foram extraídas para `sistema/app/services/transport_vehicle_operations.py`, e a persistência de alocação e recorrência foi extraída para `sistema/app/services/transport_assignment_operations.py`, mantendo wrappers compatíveis em `sistema/app/services/transport.py` e validando a preservação de comportamento com testes focados.

Entregável esperado: fronteiras internas mais claras entre leitura operacional, gestão de ativos de transporte, agendas, alocações e geração de artefatos.

Critério de conclusão: cada grupo principal de comportamento do domínio estar localizado em um serviço ou conjunto de serviços coerentes, com baixa sobreposição de responsabilidade.

### Resumo do que foi implementado na Fase 1

Na fase 1.1, foi produzido o inventário técnico detalhado do módulo de transporte, com mapeamento dos arquivos, funções, hotspots e dependências mais sensíveis do backend e da interface administrativa.

Na fase 1.2, esse inventário foi transformado em uma matriz explícita de acoplamentos críticos e em uma ordem recomendada de extração, deixando claro quais blocos do domínio deveriam ser separados primeiro e por quê.

Na fase 1.3, a montagem do dashboard administrativo foi extraída para uma camada de consulta dedicada em `sistema/app/services/transport_dashboard_queries.py`, reduzindo a mistura entre leitura agregada e comandos operacionais sem alterar a superfície pública existente.

Na fase 1.4, os principais blocos operacionais remanescentes foram separados em serviços internos coerentes: exportação em `sistema/app/services/transport_exports.py`, operações de veículo e agenda em `sistema/app/services/transport_vehicle_operations.py`, e persistência de alocação e recorrência em `sistema/app/services/transport_assignment_operations.py`, com wrappers compatíveis mantidos no serviço principal.

Com isso, a Fase 1 termina com o backend de transporte menos monolítico, com fronteiras internas mais visíveis entre consulta, exportação, veículo, agenda e assignment. O fluxo explícito de edição completa de veículo sem exclusão e recriação ainda pertence às próximas fases, mas a base estrutural necessária para implementá-lo com menos risco foi estabelecida.

### Fase 2. Reestruturação do domínio de veículos e agendas

#### 2.1 Definir formalmente o que pertence ao cadastro-base do veículo

Descrição: consolidar quais atributos fazem parte da identidade e da configuração persistente do veículo, como placa, tipo, cor, lugares e tolerância, distinguindo-os claramente dos atributos que representam disponibilidade operacional. Esta definição é necessária para que edições de cadastro não sejam confundidas com alterações de agenda.

Entregável esperado: uma definição oficial do agregado de veículo e de seus campos editáveis, com regras básicas de validação e de unicidade.

Critério de conclusão: não haver ambiguidade sobre quais atributos são permanentes do veículo e quais pertencem ao contexto operacional.

Implementação inicial desta etapa: ver `docs/fase_2_1_agregado_base_veiculo.md`. Nesta fase, o contrato do cadastro-base foi formalizado em `sistema/app/schemas.py` com `TransportVehicleBaseData` e `TransportVehicleBaseRow`, o helper dedicado `sistema/app/services/transport_vehicle_base.py` passou a centralizar montagem, comparação e aplicação dos campos permanentes do veículo, e pontos operacionais sensíveis passaram a preferir a agenda real em vez de inferir disponibilidade apenas por `Vehicle.service_scope`, mantendo compatibilidade com o modelo atual.

#### 2.2 Definir formalmente o que pertence à agenda operacional do veículo

Descrição: consolidar quais atributos representam presença operacional do veículo em determinado contexto, como escopo, recorrência, data, trajeto, horário de saída e ativação. Esta separação precisa deixar claro que disponibilidade não é sinônimo de cadastro, e que alterações de agenda devem seguir regras próprias.

Entregável esperado: uma definição oficial do agregado de agenda de veículo, incluindo regras sobre recorrência, ativação, conflito e coexistência entre agendas.

Critério de conclusão: a equipe conseguir explicar, sem contradição, quando uma alteração deve mexer no veículo e quando deve mexer na agenda.

Implementação inicial desta etapa: ver `docs/fase_2_2_agenda_operacional_veiculo.md`. Nesta fase, a agenda operacional foi formalizada em `sistema/app/schemas.py` com `TransportVehicleScheduleDefinition`, e o novo módulo `sistema/app/services/transport_vehicle_schedule.py` passou a concentrar expansão de payload, validação de recorrência, criação de agenda, conflito, reaproveitamento e busca de disponibilidade, reduzindo a mistura entre cadastro-base e disponibilidade operacional.

#### 2.3 Criar o fluxo explícito de edição completa de veículo sem exclusão e recriação

Descrição: implementar, em fase posterior de código, um contrato dedicado para editar veículos por identificador estável, permitindo alterar todas as características cadastrais sem apagar o registro original. Esta tarefa precisa contemplar especialmente a alteração de placa, pois ela costuma carregar impacto estrutural maior do que campos puramente descritivos.

Entregável esperado: definição de endpoint, schema, regras de validação, mensagens de erro e política de tratamento para conflitos de unicidade ou impacto operacional.

Critério de conclusão: existir um fluxo completo em que editar veículo signifique realmente atualizar o veículo já existente, preservando histórico e relações válidas.

Implementação inicial desta etapa: ver `docs/fase_2_3_edicao_explicita_veiculo.md`. Nesta fase, foi criado o contrato `TransportVehicleUpdate`, o endpoint `PUT /api/transport/vehicles/{vehicle_id}` e a rotina `update_transport_vehicle_base`, que atualiza o cadastro-base por identificador estável, sincroniza referências legadas por placa em `User.placa` e preserva agendas e assignments vinculados ao mesmo `vehicle.id`.

#### 2.4 Criar o fluxo explícito de edição de agenda sem interferir no cadastro-base

Descrição: separar a edição de disponibilidade operacional em comandos próprios, capazes de alterar recorrência, datas, horários, rota e ativação sem descaracterizar a entidade do veículo. Essa tarefa é essencial para impedir que ajustes operacionais passem a ser implementados como recriação disfarçada.

Entregável esperado: contrato claro para alterar agendas, com validação de conflito, consistência temporal e impacto sobre alocações existentes.

Critério de conclusão: a agenda poder ser modificada de forma independente, com semântica própria e comportamento previsível.

Implementação inicial desta etapa: ver `docs/fase_2_4_edicao_explicita_agenda.md`. Nesta fase, foi criado o contrato `TransportVehicleScheduleUpdate`, o endpoint `PUT /api/transport/vehicle-schedules/{schedule_id}` e a rotina `update_transport_vehicle_schedule`, que altera apenas a agenda operacional, valida conflito com outras agendas ativas do mesmo veículo, bloqueia mudanças que deixariam assignments confirmados futuros sem cobertura e limpa exceções legadas da agenda editada para evitar reaproveitamento implícito de regras antigas.

### Resumo do que foi implementado na Fase 2

Na fase 2.1, o cadastro-base do veículo foi formalizado com contratos próprios para os campos permanentes do veículo, separando explicitamente identidade e configuração cadastral da disponibilidade operacional. O módulo `sistema/app/services/transport_vehicle_base.py` passou a concentrar a montagem, comparação e aplicação desses atributos, enquanto trechos operacionais sensíveis deixaram de depender exclusivamente de `Vehicle.service_scope` quando a agenda já estava disponível.

Na fase 2.2, a agenda operacional do veículo foi formalizada como agregado explícito em `TransportVehicleScheduleDefinition`, e o módulo `sistema/app/services/transport_vehicle_schedule.py` passou a concentrar expansão de payload, validação de recorrência, criação de agenda, busca de disponibilidade, reaproveitamento e detecção de conflitos operacionais.

Na fase 2.3, foi introduzido o fluxo explícito de edição completa do cadastro-base do veículo por identificador estável, por meio do contrato `TransportVehicleUpdate` e do endpoint `PUT /api/transport/vehicles/{vehicle_id}`. Com isso, placa, tipo, cor, lugares e tolerância passaram a poder ser alterados sem recriar o veículo, preservando agendas, assignments e sincronizando referências legadas por placa em `User.placa`.

Na fase 2.4, foi introduzido o fluxo explícito de edição de agenda por `schedule_id`, por meio do contrato `TransportVehicleScheduleUpdate` e do endpoint `PUT /api/transport/vehicle-schedules/{schedule_id}`. Com isso, alterações de rota, recorrência, data, horário, escopo e ativação passaram a ocorrer sobre a agenda operacional, com validação explícita de conflito, de coerência de lista e de impacto sobre assignments confirmados futuros, sem interferir no cadastro-base do veículo.

Com isso, a Fase 2 termina com a separação operacional entre cadastro-base e agenda consolidada no backend. O veículo passa a ter fluxo explícito de atualização por `vehicle.id`, a agenda passa a ter fluxo explícito de atualização por `schedule_id`, e a distinção entre mudança cadastral e mudança de disponibilidade deixa de depender de recriação implícita ou interpretação do dashboard.

### Fase 3. Normalização de relacionamentos e regras estruturais

#### 3.1 Migrar vínculos baseados em chaves mutáveis para identificadores estáveis

Descrição: substituir, gradualmente, relacionamentos que hoje dependem de valores de negócio editáveis por vínculos internos baseados em identificadores estáveis. Esta tarefa deve tratar com especial cuidado as referências que hoje dependem de placa e de nome textual, porque esses campos precisam continuar editáveis sem romper o domínio.

Entregável esperado: plano de migração de banco, adaptação de modelos, atualização de queries e compatibilização temporária com dados legados, quando necessário.

Critério de conclusão: valores editáveis deixarem de ser usados como eixo principal de integridade relacional.

Implementação inicial desta etapa: ver `docs/fase_3_1_relacionamentos_estaveis_veiculo_usuario.md`. Nesta fase, `User` passou a ter o vínculo técnico `vehicle_id` com `Vehicle.id`, a migration `alembic/versions/0041_add_user_vehicle_id_link.py` passou a preencher esse campo a partir das placas já existentes e a remover o FK legado em `User.placa`, e os fluxos de admin, edição de veículo e remoção de veículo passaram a sincronizar `vehicle_id` como referência principal e `placa` apenas como espelho compatível para a superfície atual.

#### 3.2 Consolidar a fonte de verdade para escopo e disponibilidade

Descrição: decidir e formalizar onde vivem as regras de escopo de serviço, de forma que não haja duplicidade conceitual entre veículo e agenda. Esta etapa deve resolver ambiguidades semânticas e impedir que o sistema continue exigindo leitura cruzada de múltiplos lugares para entender uma única regra operacional.

Entregável esperado: definição arquitetural das fontes de verdade e atualização do domínio para refletir essa decisão com clareza.

Critério de conclusão: qualquer desenvolvedor conseguir localizar, com segurança, onde determinada regra operacional está representada.

Implementação inicial desta etapa: ver `docs/fase_3_2_fonte_verdade_escopo_disponibilidade.md`. Nesta fase, `TransportVehicleSchedule.service_scope` foi formalizado como fonte de verdade operacional sempre que existir agenda ativa, `Vehicle.service_scope` foi mantido apenas como espelho legado e fallback para cenários sem agenda, e os principais caminhos de leitura em `sistema/app/services/transport.py` passaram a usar os helpers centrais `resolve_transport_vehicle_operational_scope` e `vehicle_supports_transport_service_scope`, inclusive no estado web e na indexação de assignments recorrentes.

#### 3.3 Revisar o impacto das alterações de veículo e agenda sobre alocações já existentes

Descrição: estabelecer as regras que determinam quando uma alteração é inofensiva, quando exige revalidação e quando deve bloquear a operação por risco de inconsistência. Alterações em lotação, escopo, disponibilidade e placa podem ter efeitos diferentes, e isso precisa ser modelado antes de qualquer automação futura.

Entregável esperado: matriz de impacto operacional por tipo de alteração, com política de bloqueio, reprocessamento, aviso ou preservação.

Critério de conclusão: alterações sensíveis deixarem de depender de interpretação manual do desenvolvedor ou do operador.

Implementação inicial desta etapa: ver `docs/fase_3_3_impacto_alteracoes_assignments.md`. Nesta fase, o backend passou a formalizar a matriz de impacto entre alterações de veículo ou agenda e assignments existentes, mantendo como zona de preservação as mudanças cadastrais que não removem cobertura nem excedem capacidade, e como zona de bloqueio as mudanças que causariam overbooking futuro ou perda de cobertura operacional. O fluxo `PUT /api/transport/vehicles/{vehicle_id}` passou a rejeitar reduções de lotação que deixariam assignments confirmados futuros acima da nova capacidade, enquanto o fluxo `PUT /api/transport/vehicle-schedules/{schedule_id}` foi consolidado como o ponto que bloqueia alterações operacionais que removeriam cobertura de assignments confirmados.

### Resumo do que foi implementado na Fase 3.3

Na fase 3.3, foi formalizada a matriz de impacto operacional das alterações de veículo e agenda sobre assignments já existentes, deixando explícito o que o backend preserva, o que bloqueia e o que permanece adiado para uma futura camada de proposta.

No cadastro-base do veículo, placa, tipo, cor e tolerância permaneceram classificados como alterações preserváveis, porque não rompem a identidade técnica do veículo nem invalidam assignments vinculados por `vehicle.id`. A principal nova regra operacional desta fase foi o bloqueio de redução de lotação quando a nova capacidade ficaria abaixo da quantidade de assignments confirmados futuros para a mesma combinação de data e rota.

Na disponibilidade operacional, a fase consolidou o papel do update de agenda como mecanismo de bloqueio para mudanças que removeriam cobertura de assignments futuros já confirmados. Com isso, alterações de escopo, rota, recorrência, data, horário ou ativação continuam permitidas apenas quando a cobertura permanece garantida pela própria agenda editada ou por outra agenda ativa equivalente do mesmo veículo.

Ao final da fase 3.3, o backend de transporte passa a distinguir explicitamente entre mudança preservável e mudança bloqueada por risco operacional, reduzindo a chance de aceitar estados inconsistentes de capacidade ou disponibilidade antes das fases futuras de proposta, aprovação e automação.

### Fase 4. Formalização da camada de proposta, aprovação e exportação

#### 4.1 Definir o modelo de proposta operacional para um dia de transporte

Descrição: introduzir o conceito formal de proposta como uma entidade ou estrutura de domínio que represente uma sugestão de distribuição e atendimento sobre um snapshot estável. O objetivo é quebrar a lógica atual, em que parte da decisão operacional se confunde diretamente com a persistência final de alocações.

Entregável esperado: definição dos campos mínimos da proposta, sua origem, seu vínculo com o snapshot utilizado e seu ciclo de vida até aprovação, rejeição ou expiração.

Critério de conclusão: o domínio conseguir representar uma decisão sugerida sem precisar aplicá-la imediatamente.

Implementação inicial desta etapa: ver `docs/fase_4_1_modelo_proposta_operacional.md`. Nesta fase, o backend ganhou os contratos `TransportOperationalSnapshot`, `TransportProposalDecision`, `TransportOperationalProposalSummary` e `TransportOperationalProposal` em `sistema/app/schemas.py`, além do novo módulo `sistema/app/services/transport_proposals.py`, que materializa um snapshot operacional estável do dia com `build_transport_operational_snapshot` e monta uma proposta em rascunho com `build_transport_operational_proposal`, vinculando decisões sugeridas ao snapshot sem aplicar assignments automaticamente.

#### 4.2 Criar o fluxo de validação e aprovação de propostas

Descrição: estabelecer como uma proposta será revisada, validada, aprovada, recusada ou reaplicada. Esta tarefa deve considerar conflito de capacidade, indisponibilidade de veículo, pedido pendente, inconsistência de dados e qualquer outra restrição relevante para evitar que a automação futura atue sem governança.

Entregável esperado: comandos explícitos para validar e aprovar propostas, com resultados auditáveis e mensagens claras de inconsistência.

Critério de conclusão: o sistema passar a ter um estágio formal entre sugerir e aplicar uma decisão operacional.

Implementação desta etapa: ver `docs/fase_4_2_fluxo_validacao_aprovacao_propostas.md`. O backend passou a expor comandos explícitos de revisão em `POST /api/transport/proposals/validate`, `POST /api/transport/proposals/approve` e `POST /api/transport/proposals/reject`, usando o snapshot da proposta como base e revalidando contra o estado operacional atual antes de aprovar. A proposta agora carrega `validation_issues` e `audit_trail`, permitindo resultados auditáveis, mensagens claras de inconsistência e bloqueio formal de aprovações quando houver request duplicado, request não mais pendente, veículo indisponível ou excesso de capacidade.

#### 4.3 Redesenhar a exportação em XLSX para refletir proposta e aprovação

Descrição: evoluir a planilha atual para um artefato operacional completo, capaz de representar não apenas o estado final confirmado, mas também resumo executivo, distribuição proposta, exceções, pendências, rejeições e dados de auditoria. O objetivo é que a exportação deixe de ser uma simples listagem e se torne um documento útil para análise e aprovação.

Entregável esperado: especificação de abas, colunas, ordenações, agrupamentos e metadados que o novo XLSX deverá conter.

Critério de conclusão: existir um desenho de exportação compatível com fluxo de decisão, e não apenas com visualização de resultado final.

Implementação desta etapa: ver `docs/fase_4_3_exportacao_xlsx_operacional.md`. A exportação de transporte foi evoluída em `sistema/app/services/transport_exports.py` para um builder operacional mais rico, `build_transport_operational_plan_export`, preservando `Transport List` como aba principal compatível e adicionando abas de resumo executivo, lotação por veículo, requests do snapshot, decisões propostas, exceções e trilha de auditoria. Além disso, o backend passou a expor `POST /api/transport/exports/operational-plan`, que recebe uma `TransportOperationalProposal` e gera um XLSX coerente com o fluxo de revisão e aprovação introduzido na fase 4.2.

### Resumo do que foi implementado na Fase 4

Na fase 4.1, o backend passou a representar formalmente um snapshot operacional e uma proposta de transporte desacoplada da aplicação imediata de assignments. Isso foi consolidado com os contratos `TransportOperationalSnapshot`, `TransportProposalDecision`, `TransportOperationalProposalSummary` e `TransportOperationalProposal`, além do serviço `sistema/app/services/transport_proposals.py` para materializar snapshots estáveis do dia e montar propostas em estado `draft`.

Na fase 4.2, foi introduzido o estágio formal de revisão entre sugerir e aplicar. A proposta passou a carregar `validation_issues` e `audit_trail`, o serviço de proposals ganhou comandos explícitos de validação, aprovação e rejeição, e o router de transporte passou a expor `POST /api/transport/proposals/validate`, `POST /api/transport/proposals/approve` e `POST /api/transport/proposals/reject`, sempre revalidando o snapshot antes de aprovar e bloqueando inconsistências operacionais como request não mais pendente, veículo indisponível e excesso de capacidade.

Na fase 4.3, a exportação XLSX deixou de ser apenas uma listagem final e passou a funcionar como artefato operacional do fluxo de proposta e aprovação. O workbook foi redesenhado para preservar a aba compatível `Transport List`, mas agora também incluir resumo executivo, carga por veículo, snapshot de requests, decisões propostas, exceções e auditoria, com suporte explícito ao novo endpoint `POST /api/transport/exports/operational-plan`.

Ao final da Fase 4, o módulo de transporte passa a ter uma camada formal de proposta, revisão e exportação operacional, com separação clara entre snapshot, decisão sugerida, aprovação governada e artefato de comunicação. O sistema ainda não aplica automaticamente assignments aprovados, mas já possui a base de domínio e de exportação necessária para que essa etapa futura ocorra sobre contratos auditáveis e previsíveis.

### Fase 5. Evolução da modelagem operacional para suportar planejamento melhor

#### 5.1 Enriquecer a modelagem de workplace e restrições de atendimento

Descrição: ampliar a representação de workplace e de contexto operacional para contemplar melhor informações que influenciam a organização do transporte, como localização operacional, janelas de horário, agrupamentos relevantes e restrições específicas de atendimento. O foco desta etapa é garantir que o domínio passe a carregar informações úteis para decisão, mesmo antes de existir qualquer otimizador automatizado.

Entregável esperado: modelo mais rico para workplace e restrições relacionadas, com impacto controlado sobre cadastros e consultas existentes.

Critério de conclusão: o sistema possuir dados suficientes para suportar decisões operacionais mais sofisticadas sem depender de interpretação externa.

Implementação desta etapa: ver `docs/fase_5_1_modelagem_workplace_contexto_operacional.md`. O modelo `Workplace` foi enriquecido em `sistema/app/models.py` com campos opcionais de contexto operacional (`transport_group`, `boarding_point`, `transport_window_start`, `transport_window_end`, `service_restrictions` e `transport_work_to_home_time`), os contratos `TransportWorkplaceUpsert`, `TransportWorkplaceUpdate` e `WorkplaceRow` passaram a refletir esses dados em `sistema/app/schemas.py`, e o backend ganhou `PUT /api/transport/workplaces/{workplace_id}` para atualizar workplaces existentes sem recriar o cadastro. A listagem de workplaces usada pelo dashboard e pelos snapshots passou a devolver esse contexto enriquecido.

#### 5.2 Revisar o tratamento de horários globais, horários por data e horários por contexto

Descrição: reorganizar a camada de horários para separar claramente aquilo que é configuração global, aquilo que vale por data específica e aquilo que, no futuro, poderá variar por contexto operacional, workplace ou tipo de atendimento. Essa tarefa evita que uma única configuração genérica continue acumulando responsabilidades que tendem a crescer.

Entregável esperado: modelo conceitual de horários mais claro, com política definida para precedência, sobrescrita e fallback.

Critério de conclusão: o sistema deixar explícito qual horário vale em cada situação e de onde ele foi derivado.

Implementação desta etapa: ver `docs/fase_5_2_politica_horarios_global_data_contexto.md`. A camada de horários passou a usar uma política formal de precedência em `sistema/app/services/location_settings.py`, por meio de `resolve_transport_work_to_home_time_policy` e `get_transport_work_to_home_time_for_context`, com a ordem `date_override > workplace_context > global`. O backend também passou a expor `GET /api/transport/work-to-home-time-policy`, permitindo inspecionar o horário efetivo, sua origem e o contexto operacional do workplace, e o fluxo web de transporte passou a usar o workplace do usuário ao resolver `boarding_time` para `work_to_home`.

### Resumo do que foi implementado na Fase 5

Na fase 5.1, o domínio de `Workplace` deixou de ser apenas cadastral e passou a carregar contexto operacional útil para planejamento. Foram adicionados agrupamento operacional, ponto de embarque ou encontro, janela de atendimento, restrições específicas e um horário contextual de retorno, além de um fluxo explícito para atualizar esses dados em workplaces já existentes.

Na fase 5.2, a camada de horários foi reorganizada para distinguir explicitamente o que é global, o que é override por data e o que é override por contexto de workplace. Essa política foi centralizada em um resolvedor único, passou a ser observável por endpoint dedicado e foi ligada ao fluxo web para que o `boarding_time` do usuário respeite o contexto do workplace quando não houver sobrescrita mais forte por data.

Ao final da Fase 5, o backend de transporte passa a carregar mais contexto operacional para decisão e a resolver o principal horário ambíguo do domínio com uma política formal de precedência. O módulo ainda não implementa um planejador automático nem variações completas por tipo de atendimento, mas já dispõe de uma base de contexto e de timing muito mais clara para as próximas fases.

### Fase 6. Preparação para automação futura orientada a eventos

#### 6.1 Identificar os eventos internos que devem disparar reavaliação operacional

Descrição: definir quais acontecimentos do domínio deverão ser tratados como gatilhos legítimos para recomputação futura, como criação de pedido, alteração de agenda, mudança de configuração de veículo, cancelamento ou revisão administrativa. O objetivo é criar uma base de automação orientada a eventos de negócio reais, e não a reações improvisadas da interface.

Entregável esperado: catálogo de eventos relevantes, com indicação do que cada evento deverá disparar em termos de leitura, validação, proposta, exportação ou atualização de estado.

Critério de conclusão: existir um conjunto de gatilhos internos que represente adequadamente o ciclo operacional do transporte.

Implementação desta etapa: ver `docs/fase_6_1_eventos_reavaliacao_operacional.md`. O backend ganhou o módulo `sistema/app/services/transport_reevaluation_events.py`, que formaliza um catálogo inicial de gatilhos internos de reavaliação operacional, mantém histórico recente em memória e emite eventos tipados com ações downstream recomendadas. Também foi adicionado `GET /api/transport/reevaluation-events`, permitindo inspecionar o catálogo e os eventos recentes, e os principais mutadores do transporte passaram a emitir eventos explícitos como `transport_request_changed`, `transport_vehicle_schedule_changed`, `transport_timing_policy_changed` e `transport_operational_review_changed`, em vez de depender apenas de sinais genéricos de refresh.

#### 6.2 Definir contratos internos seguros para snapshot, proposta e aplicação

Descrição: preparar os contratos internos que serão usados no futuro por qualquer componente de automação, incluindo snapshots do dia, validação de restrições, geração de proposta e eventual aplicação aprovada. O objetivo é impedir que um agente futuro precise interagir com a lógica do dashboard ou com detalhes acidentais do fluxo web.

Entregável esperado: interfaces internas estáveis, capazes de servir tanto para operação humana assistida quanto para automação posterior.

Critério de conclusão: a futura automação conseguir ser acoplada ao domínio por contratos explícitos e auditáveis.

Implementação desta etapa: ver `docs/fase_6_2_contratos_internos_snapshot_proposta_aplicacao.md`. O backend passou a expor uma superfície contratual explícita para planejamento operacional, com `GET /api/transport/operational-snapshot`, `POST /api/transport/proposals/build` e `POST /api/transport/proposals/apply`. Em `sistema/app/schemas.py`, foram adicionados contratos próprios de build e apply, e `TransportProposalAuditEntry` passou a aceitar a ação `applied`. Em `sistema/app/services/transport_proposals.py`, a nova função `build_transport_operational_proposal_contract` passou a recompor snapshot e proposal no servidor, enquanto `apply_transport_operational_proposal` passou a exigir proposal aprovada, revalidar o estado corrente do domínio e só então persistir assignments usando o mesmo motor operacional do fluxo manual. Com isso, snapshot, proposal e aplicação deixam de depender da lógica incidental do dashboard e passam a existir como contratos backend explícitos e auditáveis.

#### 6.3 Garantir auditabilidade completa das decisões automatizadas ou semiautomatizadas

Descrição: estabelecer desde já quais dados de rastreabilidade deverão ser gravados quando uma proposta for gerada, validada, aprovada, recusada, aplicada ou refeita. Esta tarefa é essencial para que a automação futura possa ser confiável, inspecionável e contestável quando necessário.

Entregável esperado: definição dos registros de auditoria mínimos, incluindo origem da decisão, contexto usado, operador envolvido, instante da ação e resultado produzido.

Critério de conclusão: toda decisão operacional relevante poder ser explicada posteriormente com base em evidências registradas.

Implementação desta etapa: ver `docs/fase_6_3_auditabilidade_decisoes_operacionais.md`. A trilha de auditoria da proposal foi enriquecida em `sistema/app/schemas.py` com `TransportProposalAuditContext` e `TransportProposalAuditResult`, e `TransportProposalAuditEntry` passou a registrar chave própria, contexto operacional usado e resultado estruturado da ação. Em `sistema/app/services/transport_proposals.py`, o build contract passou a registrar formalmente a ação `generated`, e os fluxos de `validate`, `approve`, `reject` e `apply` passaram a gravar snapshot avaliado, origem da proposal, requests e veículos envolvidos, códigos de bloqueio e ids de assignments aplicadas. A proposal também passou a aceitar `replaces_proposal_key`, permitindo rastrear proposals refeitas ou substituídas por uma nova versão.

### Resumo do que foi implementado na Fase 6

Na fase 6.1, o módulo passou a tratar reavaliação operacional como um conjunto explícito de eventos de negócio, com catálogo próprio, histórico recente em memória e gatilhos conectados aos mutadores mais importantes do transporte. Com isso, criação ou cancelamento de request, alteração de veículo, agenda, assignment, workplace, timing policy e revisão operacional deixaram de depender apenas de sinais genéricos de refresh.

Na fase 6.2, o backend ganhou contratos internos explícitos para snapshot, build de proposal e aplicação de proposal aprovada. O sistema passou a expor `GET /api/transport/operational-snapshot`, `POST /api/transport/proposals/build` e `POST /api/transport/proposals/apply`, permitindo que o ciclo snapshot -> proposal -> apply exista no backend sem depender da leitura do dashboard nem de chamadas manuais item a item para assignments.

Na fase 6.3, a trilha de proposal foi tornada auditável de forma estrutural, registrando não apenas a ação executada, mas também contexto operacional e resultado produzido. A auditoria agora consegue explicar quem gerou, validou, aprovou, rejeitou ou aplicou uma proposal, qual snapshot foi usado, quais inconsistências apareceram e quais assignments foram efetivamente persistidas.

Ao final da Fase 6, o módulo de transporte passa a ter três blocos fundamentais já preparados para automação futura: gatilhos internos de reavaliação, contratos backend explícitos para snapshot/proposal/apply e rastreabilidade suficiente para revisar e contestar decisões sem depender da interface web como fonte de verdade.

### Fase 7. Estabilização, validação e preparação para implantação gradual

#### 7.1 Criar cobertura de testes focada nos novos contratos de domínio

Descrição: ampliar a proteção automatizada do sistema para cobrir edição de veículo, edição de agenda, revalidação de alocação, geração de proposta, exportação operacional e regras de impacto. Esta tarefa é necessária para que a reorganização avance sem transformar o módulo de transporte em uma área de regressões frequentes.

Entregável esperado: suíte de testes alinhada às novas fronteiras de domínio e capaz de validar tanto comportamento esperado quanto cenários de conflito.

Critério de conclusão: mudanças estruturais deixarem de depender principalmente de validação manual em ambiente visual.

Implementação desta etapa: ver `docs/fase_7_1_cobertura_testes_contratos_dominio.md`. A suíte `tests/test_api_flow.py` foi ampliada para proteger explicitamente os contratos de domínio mais novos, incluindo `GET /api/transport/operational-snapshot`, o caminho feliz de `POST /api/transport/proposals/apply`, o bloqueio de apply após drift operacional, o bloqueio de apply em proposal ainda `draft` e a exportação operacional consumindo uma proposal construída pelo próprio build contract. Com isso, snapshot, apply, revalidação, evento derivado de aplicação e exportação operacional passaram a ter cobertura automatizada alinhada às fronteiras contratuais criadas nas fases 6.1, 6.2 e 6.3.

#### 7.2 Planejar migração incremental sem interrupção da operação administrativa

Descrição: organizar a transição das peças antigas para as novas estruturas de modo controlado, preservando a operação atual enquanto as novas camadas são introduzidas. Esta tarefa deve contemplar compatibilidade temporária, janelas de migração, estratégia de fallback e redução de risco de indisponibilidade.

Entregável esperado: roteiro de migração incremental com marcos claros, dependências, rollback previsto e ordem segura de ativação.

Critério de conclusão: a reorganização poder ser implantada progressivamente sem exigir corte brusco de funcionamento.

Implementação desta etapa: ver `docs/fase_7_2_migracao_incremental_sem_interrupcao.md`. A fase foi materializada como um roteiro operacional explícito de migração incremental, ancorado na convivência já existente entre superfícies antigas e novas do transporte e no deploy por alvo isolado suportado por `scripts/deploy_launcher.py`. O plano agora define premissas reais de rollout, ordem segura de ativação (`API` antes de `TRANSPORT`), marcos de operação em sombra e ativação assistida, smoke checks mínimos, critérios objetivos de avanço e uma estratégia de rollback por imagem e retorno temporário ao fluxo manual legado, evitando que a reorganização dependa de um cutover brusco ou de rollback agressivo de banco.

#### 7.3 Validar se a base ficou pronta para integração futura com agente de IA sem depender da interface

Descrição: ao final da reorganização, revisar se o backend realmente passou a expor comandos claros, leituras estáveis, contratos auditáveis e dados adequados para automação. Esta tarefa é um checkpoint arquitetural, não uma implementação do agente. O objetivo é confirmar que, quando chegar a hora de integrar LangChain, o sistema já estará preparado para isso com segurança.

Entregável esperado: avaliação final de prontidão arquitetural, indicando lacunas remanescentes e itens já estabilizados.

Critério de conclusão: existir evidência concreta de que o domínio pode ser consumido por automação futura sem depender do dashboard como camada intermediária.

Implementação desta etapa: ver `docs/fase_7_3_validacao_prontidao_integracao_agente_sem_interface.md`. A validação final concluiu que a base ficou arquiteturalmente pronta para integração futura com agente sem depender da interface, porque o backend já expõe leitura operacional explícita (`GET /api/transport/operational-snapshot`, `GET /api/transport/reevaluation-events`, `GET /api/transport/work-to-home-time-policy`), comandos estáveis por identificadores e proposals (`PUT /api/transport/vehicles/{vehicle_id}`, `PUT /api/transport/vehicle-schedules/{schedule_id}`, `POST /api/transport/proposals/build`, `validate`, `approve`, `reject` e `apply`), trilha auditável estruturada com contexto e resultado, além de eventos de domínio e exportação operacional baseados na própria proposal. A avaliação também registrou as lacunas remanescentes: autenticação ainda centrada em sessão HTTP, catálogo declarativo ainda parcialmente orientado ao dashboard e ausência de política institucional explícita sobre até onde uma futura automação poderá aprovar ou aplicar decisões. Ainda assim, o parecer da fase é positivo: a UI deixou de ser a camada onde a regra realmente vive e passou a ser apenas um consumidor possível da superfície contratual do backend.

### Resumo do que foi implementado na Fase 7

Na fase 7.1, a suíte automatizada foi reforçada para proteger os contratos de domínio introduzidos nas fases anteriores, cobrindo leitura de snapshot operacional, caminho feliz de aplicação de proposal, bloqueios por drift e por proposal ainda em `draft`, além da exportação operacional derivada de uma proposal construída pelo próprio backend. Com isso, a reorganização deixou de depender principalmente de validação manual para os pontos mais sensíveis do novo fluxo contratual.

Na fase 7.2, a reorganização ganhou um roteiro operacional explícito de implantação incremental sem interrupção brusca da operação administrativa. O plano passou a definir ordem segura de rollout, uso de deploy isolado por alvo, marcos de operação em sombra e ativação assistida, smoke checks mínimos, critérios objetivos de avanço e rollback por imagem com retorno temporário ao fluxo legado, consolidando uma estratégia de adoção gradual das novas superfícies do transporte.

Na fase 7.3, a base foi validada como arquiteturalmente pronta para futura integração com agente sem depender da interface. O backend agora oferece leituras de domínio próprias, comandos estáveis, ciclo explícito de proposal com revalidação server-side, trilha auditável estruturada, eventos de reavaliação e artefatos declarativos de apoio à automação. Também ficaram registradas as lacunas remanescentes para uma futura etapa dedicada de integração, especialmente em autenticação técnica, catálogo puramente backend e governança de aprovação/aplicação por automação.

Com isso, a Fase 7 termina com três resultados complementares: cobertura automatizada das novas fronteiras contratuais, estratégia concreta de rollout incremental em produção e validação explícita de que o domínio reorganizado já pode ser consumido por automação futura sem depender da UI administrativa como camada intermediária.