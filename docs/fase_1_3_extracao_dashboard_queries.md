# Fase 1.3 - Extração da montagem do dashboard para uma camada de consulta dedicada

## Objetivo desta etapa

Esta etapa executa a primeira extração estrutural recomendada nas fases 1.1 e 1.2: separar a montagem do dashboard de transporte em uma camada de consulta dedicada, sem alterar o comportamento observado pela interface e sem modificar a superfície pública atual do módulo.

O foco desta fase não foi redesenhar o domínio inteiro nem introduzir novos contratos HTTP. O objetivo foi mais preciso: retirar a implementação da leitura agregada do dashboard do núcleo monolítico de `sistema/app/services/transport.py` e colocá-la em um módulo explicitamente voltado à composição de leitura, reduzindo a mistura entre consulta e escrita.

## Implementação realizada

Foi criado o arquivo `sistema/app/services/transport_dashboard_queries.py` como nova camada dedicada à leitura do dashboard.

Essa nova camada passou a concentrar:

- `build_transport_dashboard`
- `list_workplaces`
- `_build_project_row`

O arquivo original `sistema/app/services/transport.py` foi preservado como ponto de compatibilidade para o restante do sistema. Em vez de manter a implementação completa da leitura agregada nele, o módulo agora expõe wrappers finos para:

- `build_transport_dashboard`
- `list_workplaces`

Com isso, o roteador e os demais consumidores não precisaram mudar de contrato nesta fase. A extração foi feita sem alterar a assinatura pública das funções já utilizadas pelo módulo.

## Resultado estrutural obtido

Antes desta etapa, a leitura administrativa do dashboard dividia o mesmo corpo principal de serviço com exportação, cadastro de veículo, agenda, alocação, recorrência e outras regras operacionais. Depois desta extração, a montagem do dashboard passou a ter uma casa própria, explicitamente orientada a leitura.

Isso produz três ganhos imediatos:

1. A leitura do dashboard deixa de disputar espaço conceitual com os comandos operacionais mais destrutivos do módulo.
2. O ponto de entrada da futura camada de consulta fica materializado em um arquivo próprio, o que facilita novas extrações internas.
3. O restante do sistema continua funcionando com a mesma superfície pública, reduzindo o risco de regressão nesta etapa.

## O que permaneceu fora desta extração

Esta fase não encerra o desacoplamento do dashboard. Ela abre a fronteira correta, mas ainda há dependências importantes mantidas no serviço principal, especialmente helpers e regras que continuam sendo usados também por outros fluxos do domínio.

Continuam fora da nova camada dedicada, por enquanto:

- regras temporais compartilhadas com outros fluxos;
- helpers de agenda e disponibilidade reutilizados por comandos operacionais;
- lógica de recorrência e materialização de assignments;
- construção de estado web do usuário final;
- fluxos de cadastro, remoção e persistência operacional.

Essa decisão foi intencional. Nesta fase, o objetivo era criar a fronteira da consulta com o menor risco possível. Extrair tudo de uma vez aumentaria demais a chance de regressão e abriria uma refatoração lateral maior do que o necessário para o estágio atual do plano.

## Arquivos alterados

- `sistema/app/services/transport_dashboard_queries.py` - novo módulo de consulta dedicado ao dashboard.
- `sistema/app/services/transport.py` - simplificado para delegar a leitura agregada do dashboard e a listagem de workplaces ao novo módulo.

## Validação executada

Após a extração, foram executados testes focados do endpoint de dashboard para validar que a leitura extraída preservou o comportamento esperado.

Casos validados:

- agrupamento de requests por data selecionada e status de assignment;
- exposição de assignment `extra` independentemente da rota de origem;
- retorno de assignment para estado `pending` refletido corretamente no dashboard e no estado web.

Resultado: todos os testes focados executados nesta etapa passaram com sucesso.

## Relação desta etapa com as próximas fases

Esta fase cria a primeira separação estrutural concreta do backend de transporte. Ela prepara o terreno para as próximas extrações mais delicadas, especialmente:

- separação entre cadastro-base de veículo e agenda operacional;
- revisão da semântica destrutiva de remoção;
- isolamento entre comando pontual do dia e persistência recorrente;
- consolidação de contratos mais explícitos para update de veículo e de agenda.

Em outras palavras, a fase 1.3 não resolve sozinha o acoplamento central do módulo, mas entrega a primeira extração correta na ordem recomendada pela fase 1.2.