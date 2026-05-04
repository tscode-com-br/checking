# Plano detalhado para reestruturar a página do administrador em dispositivos móveis

## 1. Objetivo deste plano

Este plano existe para orientar a revisão completa da interface administrativa em `sistema/app/static/admin`, com foco em legibilidade, priorização visual e comportamento consistente entre desktop e dispositivos móveis.

O resultado esperado desta entrega é:

1. No desktop, quando o painel for acessado por um perfil `9`, o campo principal das tabelas `Usuários em Check-In` e `Usuários em Check-Out` deve mostrar a data e o horário na mesma linha, com o horário à direita da data.
2. No mobile, quando o painel for acessado por um perfil `0`, o usuário deve enxergar apenas as planilhas `Usuários em Check-In` e `Usuários em Check-Out`.
3. No mobile, para o perfil `0`, essas duas planilhas devem exibir apenas as colunas `Data`, `Nome do Usuário` e `Local`.
4. No mobile, o layout geral do website deve se tornar legível e utilizável para todos os perfis, não apenas para o perfil `0`.

## 2. Estado confirmado no repositório

Leitura objetiva da implementação atual:

1. A página administrativa é uma SPA estática servida a partir de `sistema/app/static/admin/index.html`, com comportamento em `sistema/app/static/admin/app.js` e estilos em `sistema/app/static/admin/styles.css`.
2. O backend já devolve, na sessão administrativa, os campos `perfil`, `can_view_activity_time`, `access_scope` e `allowed_tabs`.
3. O perfil `0` já entra no painel com escopo `limited`, e o frontend já sabe esconder abas proibidas por meio de `allowed_tabs`.
4. Hoje, o escopo `limited` já restringe o painel às abas `checkin` e `checkout`, o que significa que a regra de acesso reduzido já existe parcialmente.
5. As linhas de presença já chegam do backend com a data e a hora separadas em `activity_date_label` e `activity_time_label`, além de `activity_day_key`.
6. O helper `makeEventDateTimeCellFromParts(...)`, reutilizado pelo frontend, renderiza data e hora em linhas separadas, empilhadas verticalmente.
7. O CSS móvel atual, em `@media (max-width: 800px)`, converte todas as tabelas para um formato genérico de “cartão por linha”, usando `td::before` e um recuo fixo grande no conteúdo.
8. Esse padrão genérico mantém praticamente todas as colunas visíveis no mobile, o que gera excesso de informação, pouco espaço útil e baixa legibilidade.
9. O JavaScript atual não possui um estado explícito de viewport para decidir renderizações diferentes entre desktop e mobile; a adaptação é quase toda feita apenas por CSS.
10. Os filtros de presença continuam extensos no mobile, com muitos campos para pouco espaço, o que aumenta a altura inicial de cada aba e dificulta a leitura das linhas principais.

Conclusão prática:

1. O ajuste da data com horário na mesma linha, para o perfil `9` no desktop, pode ser resolvido no frontend sem mudança obrigatória de contrato da API.
2. A restrição de abas do perfil `0` já existe; o novo trabalho móvel deve se concentrar em poda de colunas, priorização visual e layout responsivo.
3. O problema principal do mobile não é autenticação, e sim a falta de uma estratégia de apresentação específica para telas pequenas.

## 3. Diretrizes de implementação recomendadas

### 3.1 Manter o backend estável na primeira onda

Recomendação principal:

1. Não alterar a API de `checkin`, `checkout` ou `auth/session` na primeira onda desta entrega.
2. Aproveitar os campos já existentes do payload, especialmente `activity_date_label`, `activity_time_label`, `can_view_activity_time`, `access_scope` e `allowed_tabs`.
3. Concentrar a primeira implementação em `index.html`, `app.js` e `styles.css`.

Justificativa:

1. O backend já entrega praticamente tudo o que o frontend precisa para resolver o requisito.
2. Mudar o contrato agora aumentaria o risco sem necessidade imediata.
3. O problema descrito é de layout e leitura, não de falta de dados.

Observação importante:

1. Se o time decidir, no futuro, que o perfil `0` no mobile não deve sequer receber colunas extras pelo payload, isso pode virar uma segunda etapa de endurecimento do contrato.
2. Essa segunda etapa deve ser tratada como melhoria de minimização de dados, não como pré-requisito para a correção visual inicial.

### 3.2 Introduzir um modo responsivo explícito no JavaScript

Recomendação:

1. Criar um helper central, por exemplo `isMobileAdminViewport()`, baseado em `window.matchMedia("(max-width: 800px)")`.
2. Criar também um helper derivado, por exemplo `isLimitedMobileAdminView()`, que combine:
   - viewport móvel;
   - `access_scope === "limited"`.
3. Passar a usar esse estado de viewport para decidir:
   - quais colunas renderizar;
   - quais filtros exibir;
   - qual estrutura visual cada aba deve usar.

Justificativa:

1. Hoje o frontend só troca a aparência da tabela via CSS, mas não troca a intenção da interface.
2. Para os requisitos novos, o layout precisa saber quando está em mobile para renderizar menos informação e reorganizar melhor o conteúdo.

### 3.3 Separar “responsividade genérica” de “responsividade por superfície”

Recomendação:

1. Não continuar dependendo apenas da regra genérica `.responsive-table td::before` para todas as tabelas do painel.
2. Tratar as superfícies com estratégias diferentes:
   - `Check-In` e `Check-Out`: layout móvel dedicado, com priorização clara de data, nome e local.
   - `Inativos`, `Forms` e `Eventos`: cartões resumidos com mais contexto e, quando necessário, detalhes secundários.
   - `Cadastro`, `Projetos`, `Localizações` e tabelas editáveis: blocos móveis com grupos de campos e ações em largura total.

Justificativa:

1. Tabelas operacionais de leitura rápida não têm o mesmo comportamento de tabelas de manutenção com edição.
2. Uma única solução genérica tende a ficar ruim para todo mundo, como acontece hoje.

### 3.4 Preservar as fronteiras já existentes de autorização

Recomendação:

1. Não mexer na distinção já existente entre acesso `limited` e acesso `full`.
2. Continuar usando o contrato atual da sessão administrativa para esconder abas e evitar carregamento de rotas proibidas.
3. Não ampliar permissões do perfil `0` durante a revisão visual.

Justificativa:

1. Essa separação já está documentada e já existe no código.
2. Misturar revisão visual com mudança de permissão aumentaria o risco de regressão.

## 4. Plano detalhado por fases

## Fase 0 - Congelar a linha de base visual e funcional

Objetivo:

1. Registrar o comportamento atual antes de qualquer alteração.

Ações:

1. Capturar telas do estado atual nas resoluções de referência:
   - `390 x 844`;
   - `430 x 932`;
   - `768 x 1024`;
   - desktop largo.
2. Validar a experiência com três perfis de teste:
   - perfil `0`;
   - perfil `1`;
   - perfil `9`.
3. Registrar, por aba, os problemas visuais mais evidentes no mobile:
   - excesso de colunas;
   - labels longas demais;
   - ações espremidas;
   - filtros ocupando muito espaço vertical;
   - navegação por abas pouco clara.
4. Confirmar, no desktop, que o problema da quebra de linha ocorre nas tabelas `Usuários em Check-In` e `Usuários em Check-Out` para o perfil `9`.

Saída esperada:

1. Uma referência objetiva para comparar o antes e o depois.

## Fase 1 - Corrigir data e horário na mesma linha para o perfil `9` no desktop

Objetivo:

1. Resolver o problema pontual de data e horário quebrando linha nas tabelas de presença.

Superfície principal:

1. `sistema/app/static/admin/app.js`
2. `sistema/app/static/admin/styles.css`

Ações:

1. Refatorar o helper que monta a célula de data e hora para aceitar uma variante de renderização específica para as tabelas de presença.
2. Manter o comportamento atual nas superfícies que ainda dependem de data e hora em duas linhas, como `Forms` e `Eventos`, caso isso ainda faça sentido visualmente.
3. Aplicar a variante “em linha” somente quando:
   - a tabela for `checkin` ou `checkout`;
   - o usuário puder ver horário;
   - a viewport não for móvel.
4. Garantir que o resultado final fique visualmente assim:
   - `04/05/2026 13:42:18`
   - ou, se houver indicação de dias passados, manter tudo em linha sem quebrar o horário para baixo.
5. Preservar o comportamento atual do perfil que não pode ver horário, mantendo apenas a data.

Resultado esperado:

1. O perfil `9` vê data e horário na mesma linha, com leitura mais natural no desktop.
2. O ajuste não altera a renderização das outras tabelas por acidente.

## Fase 2 - Criar uma base responsiva nova para o shell móvel

Objetivo:

1. Melhorar navegação, cabeçalho, respiro visual e hierarquia das informações no mobile.

Superfície principal:

1. `sistema/app/static/admin/index.html`
2. `sistema/app/static/admin/styles.css`
3. `sistema/app/static/admin/app.js`

Ações:

1. Revisar o cabeçalho para mobile, reduzindo o peso visual da marca e deixando a barra de sessão mais compacta.
2. Transformar a navegação por abas em uma faixa horizontal rolável ou em chips horizontais, em vez do grid de duas colunas atual.
3. Garantir que a aba ativa tenha contraste mais evidente e leitura imediata.
4. Tornar o bloco de filtros recolhível no mobile, com um gatilho claro, por exemplo `Mostrar filtros` e `Ocultar filtros`.
5. Fazer com que títulos de seção, contadores e botões de ação não disputem o mesmo espaço horizontal em telas pequenas.
6. Ajustar paddings, altura mínima de botões, espaçamento entre blocos e hierarquia tipográfica para leitura em toque.
7. Evitar depender de margens e recuos muito grandes, porque eles comprimem o conteúdo útil da linha.

Resultado esperado:

1. O painel passa a ter uma estrutura móvel clara antes mesmo de entrar nas tabelas.
2. O usuário consegue identificar a aba atual, o título e a ação principal sem esforço.

## Fase 3 - Reestruturar `Check-In` e `Check-Out` para mobile

Objetivo:

1. Resolver a parte mais crítica da experiência móvel do painel.

Superfície principal:

1. `sistema/app/static/admin/app.js`
2. `sistema/app/static/admin/index.html`
3. `sistema/app/static/admin/styles.css`

Decisão recomendada:

1. Criar uma renderização móvel dedicada para as tabelas de presença, em vez de confiar apenas na transformação genérica de tabela para cartão.

Ações:

1. Introduzir uma configuração de colunas visíveis por contexto, por exemplo:
   - desktop completo;
   - mobile completo;
   - mobile limitado.
2. Para `mobile limitado`, usar exatamente estas colunas na renderização de `checkin` e `checkout`:
   - `Data`;
   - `Nome do Usuário`;
   - `Local`.
3. Para `mobile limitado`, esconder completamente da interface:
   - `Chave`;
   - `Projeto`;
   - `Fuso horário`;
   - `Assiduidade`;
   - qualquer metadado secundário adicional.
4. Para `mobile completo`, reduzir a poluição visual das tabelas de presença, mas sem necessariamente remover todo o contexto operacional dos perfis `1` e `9`.
5. Recomenda-se, para `mobile completo`, um cartão com a seguinte hierarquia:
   - linha principal: data ou data/horário;
   - destaque central: nome do usuário;
   - linha de contexto: local;
   - metadados secundários em chips ou linha auxiliar: chave, projeto, assiduidade e fuso horário, apenas se forem realmente úteis.
6. Ajustar os rótulos para que o requisito seja respeitado literalmente no perfil `0` móvel, inclusive com o texto `Nome do Usuário` em vez de apenas `Nome`.
7. Revisar os filtros de `checkin` e `checkout` no mobile:
   - no perfil `0` móvel, exibir apenas os filtros que façam sentido com as colunas visíveis;
   - evitar filtros de colunas que o usuário não enxerga.
8. Garantir que o estado da ordenação continue coerente após a troca entre desktop e mobile.
9. Garantir que o redimensionamento de viewport recalcule a renderização sem exigir recarga da página.

Resultado esperado:

1. O perfil `0`, no mobile, vê apenas `Check-In` e `Check-Out`, com apenas `Data`, `Nome do Usuário` e `Local`.
2. Os perfis `1` e `9`, no mobile, passam a ver uma versão compacta e legível das tabelas de presença.

## Fase 4 - Revisar as demais abas para torná-las legíveis no mobile

Objetivo:

1. Fechar a revisão visual do painel como um todo, não apenas das tabelas de presença.

### 4.1 Aba `Inativos`

Objetivo:

1. Tornar a leitura de inatividade rápida e clara em tela pequena.

Ações:

1. Renderizar cada usuário inativo como cartão com:
   - nome;
   - chave;
   - projeto;
   - última atividade;
   - inatividade;
   - ação de remover em largura total, se aplicável.
2. Evitar que a coluna de ações fique comprimida no rodapé do cartão.

### 4.2 Aba `Forms`

Objetivo:

1. Reduzir a sensação de planilha larga demais no mobile.

Ações:

1. Priorizar no cartão móvel:
   - recebimento;
   - nome;
   - atividade;
   - projeto;
   - data e hora, quando o perfil puder ver horário.
2. Colocar `Informe` como bloco secundário, com quebra de linha controlada.
3. Evitar cabeçalhos longos e colunas estreitas demais.

### 4.3 Aba `Relatórios`

Objetivo:

1. Melhorar busca e leitura do histórico no mobile.

Ações:

1. Manter os filtros em uma coluna única no mobile.
2. Garantir botões em largura total e ordem visual clara.
3. Transformar os grupos de resultados em blocos com títulos, contadores e cartões de evento mais legíveis.

### 4.4 Aba `Eventos`

Objetivo:

1. Melhorar a leitura de auditoria em telas pequenas sem tentar encaixar a grade inteira na largura do celular.

Ações:

1. Transformar cada evento em um cartão resumido com os campos principais.
2. Manter os detalhes extensos em um botão `Detalhes` ou em uma seção expandível.
3. Garantir que data, ação, origem, status e local fiquem visíveis sem rolagem horizontal.

### 4.5 Aba `Cadastro`

Objetivo:

1. Tornar as superfícies de manutenção utilizáveis no mobile sem depender de uma grade apertada.

Ações:

1. Separar as subseções em blocos bem delimitados.
2. Para tabelas editáveis, reorganizar cada linha como cartão ou bloco de campos.
3. Colocar ações primárias e secundárias em largura total, com espaçamento adequado para toque.
4. Tratar `Localizações`, `Projetos`, `Administradores` e `Usuários Cadastrados` como superfícies de formulário móvel, e não como simples tabelas empilhadas.

Resultado esperado da fase 4:

1. O painel inteiro deixa de depender de uma única técnica genérica de responsividade.
2. Cada aba passa a ter uma solução móvel compatível com sua natureza de uso.

## Fase 5 - Validação funcional, visual e de regressão

Objetivo:

1. Garantir que a revisão visual não quebre regras já existentes de acesso, ordenação e atualização em tempo real.

Matriz mínima de validação:

1. Perfil `0` no mobile.
2. Perfil `1` no mobile.
3. Perfil `9` no mobile.
4. Perfil `9` no desktop.
5. Troca de orientação no tablet ou celular.
6. Redimensionamento de janela entre desktop e mobile.

Checklist funcional obrigatório:

1. O perfil `9` no desktop vê data e horário na mesma linha nas tabelas `Check-In` e `Check-Out`.
2. O perfil `0` no mobile vê apenas as abas `Check-In` e `Check-Out`.
3. O perfil `0` no mobile vê apenas as colunas `Data`, `Nome do Usuário` e `Local` nas duas planilhas.
4. O perfil `0` no mobile não vê filtros de colunas inexistentes na interface.
5. Os perfis `1` e `9` continuam com acesso completo às abas permitidas.
6. O perfil sem permissão de horário continua vendo apenas data onde essa regra já se aplica.
7. A ordenação das tabelas continua funcionando após alternar viewport.
8. O painel continua atualizando por SSE ou polling sem perder consistência visual.
9. Não surgem erros no console relacionados a renderização, `resize`, troca de aba ou reaplicação de filtros.

Checklist visual obrigatório:

1. Não existe rolagem horizontal na área útil principal das telas móveis de presença.
2. Os textos críticos cabem com leitura confortável em `390 px` de largura.
3. Botões de ação têm área de toque adequada.
4. Título, filtros, tabela e ações não ficam visualmente misturados.

## 5. Mudanças recomendadas por arquivo

### 5.1 `sistema/app/static/admin/index.html`

Mudanças recomendadas:

1. Adicionar classes e atributos específicos para diferenciar superfícies móveis das tabelas genéricas.
2. Introduzir gatilhos de recolhimento de filtros nas abas mais densas.
3. Preparar a navegação por abas para um layout horizontal rolável no mobile.
4. Ajustar rótulos visuais necessários para o contexto móvel do perfil `0`, especialmente `Nome do Usuário`.

### 5.2 `sistema/app/static/admin/app.js`

Mudanças recomendadas:

1. Criar estado explícito de viewport móvel.
2. Criar helpers para decidir variantes de renderização por tabela.
3. Refatorar a construção das linhas de `checkin` e `checkout` para aceitar:
   - desktop com data/hora em linha;
   - mobile completo;
   - mobile limitado.
4. Recalcular layout em `login`, `bootstrap`, `resize` e troca de orientação.
5. Ajustar filtros e rótulos conforme o modo de renderização ativo.
6. Garantir que tabelas que ainda dependem de detalhes completos possam usar uma estratégia móvel própria, sem contaminar todas as outras.

### 5.3 `sistema/app/static/admin/styles.css`

Mudanças recomendadas:

1. Criar estilos dedicados para os cartões móveis de presença.
2. Criar uma variante visual em linha para a célula de data/hora das tabelas de presença no desktop.
3. Revisar cabeçalho, barra de sessão, tabs, botões, filtros e espaçamentos para telas pequenas.
4. Reduzir dependência do padrão genérico `td::before` nas superfícies críticas.
5. Definir regras específicas por aba em vez de uma única regra global para tudo.

### 5.4 `sistema/app/routers/admin.py`, `sistema/app/schemas.py` e `sistema/app/services/admin_auth.py`

Mudança obrigatória nesta entrega:

1. Nenhuma, a princípio.

Uso previsto nesta entrega:

1. Reaproveitar os contratos e regras já existentes.
2. Validar, durante os testes, que `allowed_tabs`, `access_scope` e `can_view_activity_time` continuam sendo respeitados pelo frontend.

Mudança opcional futura:

1. Se o time quiser endurecer o contrato para o perfil `0` no mobile, pode-se discutir uma segunda etapa para reduzir também os campos enviados pela API em contexto móvel limitado.

## 6. Critérios de aceite finais

Esta entrega deve ser considerada concluída apenas quando todos os itens abaixo forem verdadeiros:

1. O perfil `9` no desktop visualiza data e horário na mesma linha, com o horário à direita da data, em `Usuários em Check-In` e `Usuários em Check-Out`.
2. O perfil `0` no mobile visualiza somente as abas `Check-In` e `Check-Out`.
3. O perfil `0` no mobile visualiza somente `Data`, `Nome do Usuário` e `Local` nessas duas planilhas.
4. O mobile deixa de apresentar tabelas principais com leitura espremida, labels gigantes e excesso de colunas simultâneas.
5. Os perfis `1` e `9` continuam com acesso completo ao que já tinham antes, agora com layout móvel mais legível.
6. O desktop não sofre regressão visual relevante nas tabelas do painel.
7. O frontend continua compatível com os contratos atuais da API.

## 7. Riscos e mitigação

### Risco 1 - Alteração global demais no helper de data e hora

Risco:

1. Uma mudança direta em `makeEventDateTimeCellFromParts(...)` pode afetar `Forms`, `Eventos` e outras telas sem querer.

Mitigação:

1. Criar uma variante opt-in para presença, em vez de mudar o helper global sem contexto.

### Risco 2 - Regressão em tabelas que compartilham `.responsive-table`

Risco:

1. Alterar a regra genérica de responsividade pode piorar tabelas que hoje já estão aceitáveis.

Mitigação:

1. Introduzir classes específicas por superfície crítica e reduzir a dependência da regra global.

### Risco 3 - Layout inconsistente após `resize`

Risco:

1. O usuário pode logar no desktop, reduzir a janela e ficar com metade do layout antigo e metade do novo.

Mitigação:

1. Centralizar um fluxo de sincronização visual executado em `bootstrap`, `showAdminShell`, `resize` e mudança de orientação.

### Risco 4 - Perfil `0` ainda receber dados extras no payload

Risco:

1. Mesmo com a interface simplificada, o frontend ainda pode receber campos extras do backend.

Mitigação:

1. Aceitar isso na primeira onda, por ser uma correção de UI.
2. Se houver exigência de minimização de dados, abrir uma segunda etapa específica de endurecimento de contrato.

## 8. Ordem recomendada de implementação

Sequência sugerida para reduzir risco:

1. Corrigir primeiro a célula de data e horário do desktop para o perfil `9`.
2. Implementar a infraestrutura de viewport móvel e a nova navegação por abas.
3. Reestruturar `Check-In` e `Check-Out` no mobile, incluindo a poda de colunas do perfil `0`.
4. Estender o padrão móvel para `Inativos`, `Forms`, `Relatórios`, `Eventos` e `Cadastro`.
5. Executar a matriz de validação final.

## 9. Estratégia sugerida de entrega em PRs

Para manter a implementação controlável, recomenda-se dividir a execução em três PRs:

1. PR 1:
   - data e horário em linha no desktop para o perfil `9`;
   - infraestrutura de viewport móvel;
   - nova navegação por abas no mobile.
2. PR 2:
   - reestruturação móvel de `Check-In` e `Check-Out`;
   - restrição exata de colunas para o perfil `0` no mobile.
3. PR 3:
   - revisão das demais abas;
   - refinamento visual;
   - regressão final e homologação.

Essa divisão mantém o problema principal sob controle sem abrir uma frente grande demais de uma só vez.