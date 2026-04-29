# Fase 7.2 - Migração incremental sem interrupção da operação administrativa

## Objetivo

Esta fase formaliza um roteiro de implantação progressiva para a reorganização do módulo de transporte sem exigir corte brusco da operação atual. O foco aqui não é criar novos contratos de domínio, mas definir como ativar, observar, reverter e consolidar as mudanças já implementadas nas fases anteriores, preservando o uso contínuo do dashboard administrativo e dos fluxos manuais enquanto as superfícies novas entram em produção de modo controlado.

## Premissas operacionais já verificadas

1. A superfície nova de transporte já convive com a superfície antiga no backend. O módulo ainda expõe `GET /api/transport/dashboard`, `POST /api/transport/assignments`, `POST /api/transport/requests/reject` e `GET /api/transport/exports/transport-list`, ao mesmo tempo em que expõe `GET /api/transport/operational-snapshot`, `POST /api/transport/proposals/build`, `POST /api/transport/proposals/validate`, `POST /api/transport/proposals/approve`, `POST /api/transport/proposals/reject`, `POST /api/transport/proposals/apply`, `POST /api/transport/exports/operational-plan` e `GET /api/transport/reevaluation-events`.
2. O deploy atual do sistema principal pode ser feito por alvo isolado usando `python scripts/deploy_launcher.py`, com ações separadas para `API`, `TRANSPORT`, `ADMIN`, `CHECK` e fallback global.
3. O deploy produtivo relevante para essa migração pertence apenas ao repositório principal `checkcheck`; os repositórios móveis aninhados não fazem parte do rollout do backend/web.
4. As mudanças estruturais realizadas até aqui foram compatíveis por adição e convivência, não por substituição destrutiva imediata. Isso permite ativação progressiva por uso operacional, sem exigir remoção simultânea dos caminhos legados.

## Princípios obrigatórios da migração

1. Toda alteração estrutural deve entrar primeiro de forma compatível, preservando leitura e comando antigos durante pelo menos um ciclo operacional completo.
2. O deploy da API vem antes de qualquer deploy de interface que passe a consumir contratos novos.
3. A migração de uso deve acontecer por adoção controlada do fluxo novo, não por remoção imediata do fluxo antigo.
4. O rollback preferencial deve ser por reimplantação de imagem anterior e retorno temporário ao fluxo manual legado, não por rollback agressivo de banco.
5. Limpeza de compatibilidade, remoção de wrappers e retirada de endpoints antigos só podem acontecer em release posterior, nunca no mesmo rollout em que o comportamento novo é ativado.

## Padrão de migração para mudanças futuras no transporte

Toda mudança futura no domínio de transporte deve seguir a ordem abaixo:

1. release aditiva: novas colunas, novos contratos, novos endpoints e novas trilhas de auditoria entram sem remover a superfície anterior;
2. release de compatibilidade: backend passa a ler e aceitar os dois caminhos enquanto operadores continuam usando o fluxo atual;
3. release de adoção controlada: um subconjunto do fluxo operacional passa a usar o contrato novo com validação e observabilidade reforçadas;
4. release de consolidação: depois de ciclos estáveis, o fluxo novo vira padrão operacional;
5. release de limpeza: somente então as peças de compatibilidade antigas podem ser removidas.

Esse padrão é especialmente importante para migrações de schema. Em banco, a regra segura é adição -> backfill -> dupla leitura ou leitura compatível -> mudança de uso -> limpeza posterior. Também permanece obrigatório manter novos revision IDs do Alembic com 32 caracteres ou menos.

## Roteiro incremental recomendado

### Marco 0. Pré-flight local e homologação

Objetivo: garantir que o release candidato ainda preserva os fluxos manuais e os contratos novos antes de tocar produção.

Checklist:

1. validar que o working tree do repositório principal está limpo ou conscientemente controlado;
2. executar os testes focados da fase 7.1 e os testes dirigidos ao trecho alterado no release candidato;
3. confirmar que as migrations do release são aditivas ou compatíveis;
4. verificar que `GET /api/health` responde normalmente no ambiente alvo;
5. confirmar autenticação admin e sessão de transporte;
6. confirmar que o dashboard antigo e os contratos novos respondem no mesmo build.

Critério para seguir: nenhum bloqueio de health, autenticação, dashboard legado ou contratos novos essenciais.

### Marco 1. Deploy isolado de backend compatível

Objetivo: publicar primeiro a API com a nova estrutura, sem obrigar a interface a mudar de comportamento naquele mesmo instante.

Ordem segura:

1. usar o launcher com a ação `API` quando a mudança estiver restrita ao backend de transporte;
2. usar `Fallback Global` somente quando a mudança exigir atualização coordenada do app principal ou de ativos compartilhados;
3. não fazer deploy de `TRANSPORT` antes de a API nova estar saudável.

Smoke checks mínimos após deploy da API:

1. `GET /api/health`;
2. `GET /api/transport/dashboard` com sessão válida;
3. `POST /api/transport/assignments` em cenário controlado ou validação manual equivalente em homologação;
4. `GET /api/transport/operational-snapshot`;
5. `POST /api/transport/proposals/build`;
6. `GET /api/transport/reevaluation-events`.

Critério para seguir: a superfície antiga continua funcional e os contratos novos respondem sem degradar a operação corrente.

### Marco 2. Operação em modo sombra

Objetivo: introduzir a nova camada de proposal e exportação operacional sem deslocar ainda o operador do fluxo manual como fonte primária de decisão.

Uso esperado nesse marco:

1. operadores continuam podendo usar dashboard, assignments e rejeição manual como caminho principal;
2. snapshot operacional, build de proposal, validação, approval e exportação operacional são usados em paralelo para revisão e comparação;
3. eventos de reavaliação e trilha de auditoria passam a ser observados como instrumentos de inspeção, não ainda como automação obrigatória.

Sinais a acompanhar:

1. divergência entre `dashboard` e `operational-snapshot`;
2. proposals bloqueadas por drift ou inconsistência inesperada;
3. trilha de auditoria incompleta ou pouco explicativa;
4. exportação operacional gerada a partir de proposal contratual.

Critério para seguir: pelo menos um ciclo operacional completo sem regressão funcional no fluxo manual e com leitura consistente dos contratos novos.

### Marco 3. Ativação assistida do fluxo novo

Objetivo: passar a usar proposal approval/apply em escopo controlado, mantendo fallback operacional imediato para o fluxo manual antigo.

Forma recomendada de ativação:

1. limitar inicialmente por rota, data operacional ou pequeno conjunto de operadores responsáveis;
2. continuar preservando `POST /api/transport/assignments` e `POST /api/transport/requests/reject` como fallback manual explícito;
3. usar `POST /api/transport/proposals/apply` apenas quando a proposal já tiver sido validada e aprovada;
4. monitorar `transport_assignment_changed` com `source="transport_proposal"` como evidência de aplicação controlada.

Critério para rollback imediato nesse marco:

1. bloqueios repetidos por drift que o operador não consiga contornar com segurança;
2. divergência entre assignments persistidas e expectativa operacional do dia;
3. qualquer regressão que impeça o operador de concluir o atendimento do dia com previsibilidade.

### Marco 4. Alinhamento de interface e cutover controlado

Objetivo: só depois de a API compatível estar estável e o fluxo novo validado em uso assistido, permitir que interfaces passem a depender diretamente dos contratos novos.

Ordem segura:

1. API já estabilizada em produção;
2. deploy isolado `TRANSPORT` apenas se a interface realmente passar a consumir contracts novos;
3. `ADMIN` e `CHECK` permanecem fora do escopo, exceto se o release os afetar diretamente.

Regra importante: interface nova só pode ser publicada quando o operador ainda tiver fallback operacional no backend antigo. O frontend não pode ser o ponto único de ativação do novo comportamento.

### Marco 5. Consolidação e limpeza posterior

Objetivo: encerrar a convivência de compatibilidade apenas depois de evidência operacional suficiente.

Pré-condições para limpeza futura:

1. pelo menos um ciclo estável usando snapshot/proposal/apply sem necessidade recorrente de fallback manual;
2. exportação operacional adotada como artefato de revisão principal quando aplicável;
3. trilha de auditoria demonstrando explicabilidade adequada de geração, aprovação, rejeição e aplicação;
4. ausência de dependência real do caminho legado em operadores ou integrações ativas.

Itens que não devem ser removidos na mesma release de ativação:

1. endpoint `dashboard`;
2. endpoint `assignments`;
3. endpoint `requests/reject`;
4. exportação legada `transport-list`;
5. qualquer fallback de leitura compatível ainda usado por testes ou operadores.

## Estratégia de rollback

### Rollback de API

Se o problema estiver restrito ao backend:

1. reimplantar a imagem anterior pelo launcher `API` usando uma tag publicada anteriormente via `CHECKCHECK_DEPLOY_IMAGE_TAG`;
2. manter o frontend atual inalterado;
3. retornar temporariamente ao fluxo manual legado de dashboard + assignment se necessário.

### Rollback de interface de transporte

Se o problema estiver no site de transporte, mas a API estiver estável:

1. reimplantar apenas `TRANSPORT` com a imagem anterior;
2. preservar a API nova se ela continuar compatível com o fluxo antigo;
3. usar a coexistência dos endpoints legados como amortecedor operacional.

### Rollback funcional sem rollback de imagem

Se a regressão estiver no uso do fluxo novo, mas não no deploy em si:

1. suspender imediatamente o uso de `proposals/apply` naquele ciclo operacional;
2. retornar ao uso explícito de `assignments` e `requests/reject`;
3. manter coleta de auditoria e eventos para análise posterior;
4. só retomar a ativação assistida depois de corrigir e revalidar o desvio.

### Rollback de banco

Rollback de banco deve ser exceção. Para as mudanças desta reorganização, o caminho seguro é rollback por imagem e retorno ao fluxo compatível. Reversão de migration só deve ocorrer diante de corrupção real, falha de startup sem saída compatível ou bug estrutural que não possa ser contornado pelo binário anterior.

## Sinais objetivos para avançar ou parar

Avançar quando:

1. health check estiver estável;
2. dashboard legado continuar íntegro;
3. contratos novos responderem com consistência;
4. apply aprovado produzir assignments auditáveis e previsíveis;
5. exportação operacional refletir proposal e auditoria corretamente.

Parar ou reverter quando:

1. houver falha de sessão ou degradação do dashboard administrativo;
2. a proposal aprovada não puder mais ser explicada ou rastreada adequadamente;
3. o fluxo novo impedir a conclusão segura do atendimento do dia;
4. o deploy isolado do alvo afetado não recuperar o comportamento esperado em janela curta.

## Resultado esperado da fase

Ao final desta fase, a reorganização deixa de ser apenas uma coleção de peças compatíveis e passa a ter um plano explícito de implantação progressiva. O sistema pode evoluir por backend compatível, observação em sombra, ativação assistida, alinhamento de interface e limpeza posterior, sempre com fallback operacional claro e sem exigir interrupção abrupta da operação administrativa.