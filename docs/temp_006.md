# Plano Completo para Destravar Paisagem, Ajustar Layout em Paisagem/Desktop e Alterar a Label do Botão de Transporte

Data: 2026-04-25

## Introdução

Este documento define um plano técnico completo, seguro e rastreável para realizar quatro alterações específicas na aplicação web localizada em `sistema/app/static/check`:

1. permitir a visualização e o uso do webapp em modo paisagem no dispositivo móvel;
2. preparar um layout realmente ajustado para o uso em paisagem no celular/tablet;
3. preparar uma apresentação visual bonita, organizada e proporcional para acesso via computador, preservando a identidade visual já existente do webapp;
4. alterar a label do botão `Em breve` para `Em Teste`.

O objetivo deste plano não é redesenhar o produto, nem abrir escopo em backend, regras de negócio ou contratos HTTP. O objetivo é destravar e reorganizar a apresentação visual do frontend, preservando o comportamento funcional já consolidado.

## 1. Objetivo

Executar uma revisão controlada do frontend web em `sistema/app/static/check` para que a aplicação:

- deixe de bloquear o uso em paisagem;
- permaneça confortável e legível em paisagem mobile;
- tenha apresentação equilibrada em desktop sem ocupar largura exagerada nem introduzir quebras visuais ruins;
- preserve a identidade atual do produto;
- mantenha a mesma semântica funcional da SPA;
- apenas troque o texto visível do botão de transporte de `Em breve` para `Em Teste`.

## 2. Diagnóstico Consolidado do Estado Atual

### 2.1. O bloqueio de paisagem existe hoje de forma explícita

A aplicação atual não está apenas “mal ajustada” para paisagem. Ela está deliberadamente bloqueada para paisagem por três camadas coordenadas:

- em `sistema/app/static/check/index.html`, existe o overlay `orientationLockScreen` com a mensagem `Use o aparelho em retrato`;
- em `sistema/app/static/check/styles.css`, a classe `body.portrait-lock-active` oculta `header` e `.check-shell`, bloqueando interação com a interface principal enquanto o overlay está ativo;
- em `sistema/app/static/check/app.js`, a função `syncPortraitLockState()` detecta paisagem, alterna a classe `portrait-lock-active`, exibe o overlay e ainda tenta aplicar `screen.orientation.lock('portrait')` como melhoria progressiva.

Conclusão técnica:

- para destravar paisagem, não basta mexer em CSS de espaçamento;
- será necessário remover ou neutralizar esse fluxo de bloqueio em HTML, CSS, JavaScript e testes.

### 2.2. O layout atual foi otimizado principalmente para retrato mobile

Pelo CSS atual:

- a shell usa viewport dinâmico e medição de header para acomodar melhor navegadores mobile;
- a largura máxima principal hoje parte de `680px`, sobe para `760px` em `min-width: 640px` e chega a `920px` em `min-width: 1024px`;
- existe um ajuste específico para `@media (orientation: landscape) and (max-height: 540px)`, mas ele só reduz header, padding e altura de controles, sem preparar um layout de uso real em paisagem;
- o formulário principal continua essencialmente empilhado como coluna única.

Conclusão técnica:

- a base responsiva atual ajuda, mas não resolve a organização da interface em paisagem nem em desktop;
- será necessário introduzir regras de composição mais explícitas para esses cenários.

### 2.3. O desktop atual tambem e bloqueado pelo mesmo fluxo de paisagem

A leitura inicial do CSS mostra que a aplicacao possui expansao progressiva de largura em telas maiores, mas a baseline executada na Fase 0 confirmou um ponto mais importante: em desktop com viewport horizontal, a interface atual tambem cai no mesmo bloqueio de orientacao usado no mobile em paisagem.

Isso acontece porque:

- `syncPortraitLockState()` trata qualquer viewport `landscape` como estado bloqueado;
- o overlay `orientationLockScreen` continua sendo exibido;
- `header` e `.check-shell` ficam ocultos por `body.portrait-lock-active`.

Conclusão técnica:

- antes de discutir refinamento visual para computador, a aplicacao precisa deixar de ser bloqueada por esse fluxo retrato-only;
- depois do desbloqueio, ainda sera necessario tratar melhor distribuicao interna, largura maxima e quebras de linha no desktop.

### 2.4. A label `Em breve` está literal no HTML

O texto atual do botão de transporte está em `sistema/app/static/check/index.html`, dentro de `#transportButton`.

Conclusão técnica:

- a troca para `Em Teste` é simples, localizada e de baixo risco;
- o risco principal está apenas em garantir que nenhum teste ou screenshot baseline continue esperando o texto antigo.

### 2.5. Os testes atuais protegem explicitamente o modo retrato-only

Hoje existem guardas automatizadas que assumem o bloqueio de paisagem como comportamento correto, especialmente em:

- `tests/check_portrait_lock.test.js`
- `tests/check_responsive_layout.test.js`

Conclusão técnica:

- a implementação precisará atualizar ou substituir esses testes;
- caso contrário, a mudança correta quebrará a suíte por conflito de expectativa antiga.

## 3. Escopo Exato da Mudança

### 3.1. O que entra no escopo

- destravar o uso em paisagem no mobile;
- reorganizar a shell principal para paisagem mobile;
- reorganizar a shell principal para desktop;
- refinar grid, largura, gaps, empilhamento e alinhamento de blocos visuais;
- ajustar o modo de apresentação de dialogs e overlays caso o novo layout exija;
- trocar `Em breve` por `Em Teste`.

### 3.2. O que não entra no escopo

- qualquer alteração de backend;
- qualquer novo endpoint;
- qualquer mudança nas regras de check-in/check-out;
- qualquer mudança nas regras de localização, transporte, autenticação ou persistência;
- qualquer reescrita estética ampla que descaracterize o visual atual;
- qualquer conversão da SPA para design “desktop-first” ou layout full width.

## 4. Premissas Imutáveis

As seguintes regras devem orientar toda a implementação:

- a identidade visual atual deve ser preservada: cabeçalho verde, fundo com gradiente claro, marca d'água, card central, tipografia e paleta semântica;
- o layout desktop deve continuar centralizado e contido, sem ocupar a largura total da tela;
- paisagem mobile deve continuar priorizando leitura, toque e scroll, sem transformar tudo em miniaturas apertadas;
- não deve haver introdução de `overflow: hidden`, `position: fixed` global ou listeners que prejudiquem scroll vertical natural;
- o comportamento em retrato não pode piorar;
- o modo desktop deve ser um refinamento do layout, não um produto paralelo;
- a label `Em Teste` deve aparecer de forma consistente no botão e em qualquer cobertura automatizada relacionada.

## 5. Resultado Desejado por Cenário

### 5.1. Retrato mobile

O comportamento em retrato deve permanecer como referência principal:

- shell centralizada;
- espaçamentos atuais preservados ou apenas refinados;
- nenhum bloqueio novo;
- nenhuma regressão visual.

### 5.2. Paisagem mobile

Ao girar o aparelho em 90 graus:

- o overlay de bloqueio não deve mais esconder a aplicação;
- o header deve permanecer visível e proporcionalmente mais compacto;
- o card principal deve continuar centralizado e utilizável;
- o formulário deve se reorganizar para aproveitar a largura extra e a altura menor;
- o scroll vertical deve continuar disponível;
- grupos críticos não devem quebrar de forma feia ou gerar linhas desnecessárias.

### 5.3. Desktop

Ao abrir o link em notebook ou computador:

- a aplicação deve continuar claramente sendo a mesma SPA;
- o conteúdo deve ficar bonito, contido e centralizado;
- o card principal pode ficar mais largo, mas sem exagero;
- seções informativas e seções de ação devem ficar melhor distribuídas;
- não deve haver linhas muito compridas, buracos visuais ou espaçamentos exagerados.

### 5.4. Botão de transporte

O botão atualmente rotulado `Em breve` deve passar a exibir `Em Teste`, sem alteração de semântica funcional além da microcopy.

## 6. Estratégia Técnica Recomendada

### 6.1. Direção geral

A solução recomendada é:

1. remover o bloqueio funcional de paisagem;
2. preservar a infraestrutura atual de viewport dinâmica e medição do header;
3. introduzir layout por breakpoints mais claros para:
   - retrato mobile;
   - paisagem mobile/baixa altura;
   - desktop;
4. usar CSS como mecanismo principal de reorganização visual;
5. usar HTML mínimo adicional apenas para ganchos de layout mais estáveis quando necessário;
6. manter JavaScript apenas no que continuar sendo útil para métricas de viewport, sem manter a lógica de bloqueio retrato-only.

### 6.2. Hipótese principal de implementação

A hipótese de trabalho mais sólida é:

- o destravamento de paisagem pode ser resolvido principalmente pela remoção do fluxo `portrait-lock-active` e do overlay correspondente;
- o ajuste fino de paisagem e desktop pode ser resolvido majoritariamente por CSS Grid/Flex, sem reescrever a lógica funcional;
- pequenas marcações extras no HTML podem ser desejáveis para nomear melhor regiões do formulário e evitar seletores frágeis no CSS.

### 6.3. Direção de layout recomendada

#### Paisagem mobile

A recomendação é não manter a mesma coluna vertical exata do retrato. Em paisagem, o plano recomenda:

- reduzir altura visual do header;
- reduzir paddings e gaps verticais;
- reorganizar blocos superiores em composição mais horizontal;
- manter a área de localização visível e compacta;
- permitir que blocos de histórico/notificação/localização ocupem região mais resumida;
- reorganizar a área de autenticação, grupos e seletores para aproveitar largura adicional;
- manter o botão `Registrar` claramente visível sem exigir zoom.

#### Desktop

A recomendação é adotar um modo de composição contida, com largura máxima maior que a atual, mas ainda centralizada, por exemplo:

- shell principal mais larga do que `920px`, porém ainda limitada;
- organização interna em duas regiões balanceadas:
  - região informativa/resumo;
  - região operacional/formulário;
- preservação do card único ou, se necessário, subdivisão interna em painéis visuais coesos sem romper a identidade atual.

## 7. Arquivos Mais Prováveis de Alteração

### Frontend principal

- `sistema/app/static/check/index.html`
- `sistema/app/static/check/styles.css`
- `sistema/app/static/check/app.js`

### Testes

- `tests/check_portrait_lock.test.js`
- `tests/check_responsive_layout.test.js`
- possivelmente `tests/check_auth_transport_ui.test.js`
- possivelmente um novo teste focado em layout de paisagem/desktop, se a cobertura atual ficar ambígua.

## 8. Plano de Execução por Fases

## Fase 0. Congelamento do comportamento atual e guard rails

Objetivo:

- delimitar a mudança como revisão de apresentação e de affordance de orientação, sem tocar em regra de negócio.

Atividades:

- confirmar que backend, endpoints e fluxos funcionais permanecem congelados;
- registrar screenshots baseline em retrato, paisagem bloqueada atual e desktop atual;
- registrar quais testes hoje assumem portrait-only;
- registrar a largura máxima atual e os breakpoints existentes como baseline técnico.

Critério de conclusão:

- o time sabe exatamente o que será alterado visualmente e o que não poderá ser alterado funcionalmente.

Execucao registrada em 2026-04-25:

1. Foi confirmado por leitura direta de `sistema/app/static/check/index.html`, `sistema/app/static/check/styles.css` e `sistema/app/static/check/app.js` que a demanda permanece 100% frontend-only, sem necessidade de alterar backend, endpoints, payloads ou regras de negocio.
2. Foi confirmado que o bloqueio atual de paisagem depende explicitamente do trio `orientationLockScreen` + `body.portrait-lock-active` + `syncPortraitLockState()`, o que delimita com precisao o ponto de remocao da politica retrato-only.
3. Foram registrados os artefatos baseline desta fase em `docs/temp_006_baseline/`:
  - `01-portrait-current.png`
  - `02-landscape-current.png`
  - `03-desktop-current.png`
4. A baseline visual confirmou que o estado atual em paisagem continua bloqueado pelo overlay e que o desktop atual tambem cai nesse mesmo bloqueio quando aberto em viewport horizontal, o que elevou esse comportamento de risco potencial para fato verificado.
5. Ficou registrado que `tests/check_portrait_lock.test.js` assume explicitamente o comportamento portrait-only atual, enquanto `tests/check_responsive_layout.test.js` protege os breakpoints e tokens atuais de responsividade que serao impactados pelas fases seguintes.
6. Ficou registrado como baseline tecnico de layout que `styles.css` parte de `--card-max-width: 680px`, sobe para `760px` em `@media (min-width: 640px)` e para `920px` em `@media (min-width: 1024px)`, alem de possuir apenas um ajuste compacto em `@media (orientation: landscape) and (max-height: 540px)`.

## Fase 1. Destravar a aplicação para paisagem

Objetivo:

- remover a política de bloqueio retrato-only e liberar a interface principal em paisagem.

Atividades:

- remover ou neutralizar o overlay `orientationLockScreen` em `index.html`;
- remover ou neutralizar o CSS associado a `.orientation-lock-screen`, `.orientation-lock-card` e `body.portrait-lock-active`;
- revisar `app.js` para:
  - retirar a lógica que alterna `portrait-lock-active`;
  - retirar a exibição do overlay em paisagem;
  - descontinuar `requestPortraitOrientationLock()` como parte do fluxo normal;
  - preservar somente a infraestrutura útil de métricas de viewport e realinhamento;
- revisar atributos `aria-hidden` hoje usados para esconder header/shell enquanto o overlay está ativo.

Arquivos alvo principais:

- `sistema/app/static/check/index.html`
- `sistema/app/static/check/styles.css`
- `sistema/app/static/check/app.js`

Critério de conclusão:

- rotacionar o dispositivo para paisagem não esconde mais a aplicação nem exibe overlay de bloqueio.

Execucao registrada em 2026-04-25:

1. Foi adotada a estrategia de remocao definitiva, e nao apenas neutralizacao, do fluxo retrato-only desta SPA: o bloco `orientationLockScreen` saiu de `index.html`, o CSS dedicado ao overlay e a `body.portrait-lock-active` saiu de `styles.css`, e o encadeamento `syncPortraitLockState()`/`requestPortraitOrientationLock()` saiu de `app.js`.
2. A infraestrutura util de viewport foi preservada: a aplicacao continua sincronizando `--app-viewport-width`, `--app-viewport-height` e `--app-header-height` via `scheduleViewportLayoutMetricsSync()`, bem como continua reagindo a `resize`, `orientationchange` e `visualViewport.resize` para realinhamento da shell.
3. Os listeners de `visibilitychange`, `focus` e `pageshow` foram mantidos para atualizar metricas, autenticação silenciosa e ciclos de vida da aplicacao, mas sem voltar a aplicar qualquer bloqueio de orientacao.
4. `tests/check_portrait_lock.test.js` foi reescrito para proteger o novo comportamento: ausencia do overlay retrato-only, ausencia da classe `portrait-lock-active` e preservacao da sincronizacao de viewport sem tentativa de forcar `portrait`.
5. Esta fase remove apenas o bloqueio funcional de paisagem. O refinamento do layout em paisagem mobile e a composicao adequada para desktop continuam reservados para as fases seguintes, evitando misturar desbloqueio com redesign no mesmo passo.

## Fase 2. Preparar layout realmente utilizável para paisagem mobile

Objetivo:

- reorganizar a SPA para paisagem sem sacrificar legibilidade, toque e scroll.

Atividades:

- definir breakpoint principal para paisagem de baixa altura, por exemplo combinando `orientation: landscape` com limites de altura úteis;
- reduzir header, paddings, section gaps e alturas de controles onde necessário;
- reorganizar a estrutura do formulário para paisagem, avaliando uma destas abordagens:
  - grid com áreas nomeadas para blocos principais;
  - grid de duas colunas internas com blocos informativos de um lado e blocos operacionais do outro;
  - empilhamento híbrido em que apenas alguns blocos passam a ficar lado a lado;
- garantir que a linha de autenticação não estoure altura desnecessariamente;
- garantir que a linha `Projeto` + `Local` não gere cortes, saltos de altura ou overflow;
- revisar a área de grupos `Registro` e `Informe` para evitar quebra ruim de labels e cartões;
- garantir que o botão `Registrar` continue visualmente prioritário e acessível;
- revisar dialogs e overlays para não saírem da área útil em paisagem;
- manter scroll vertical natural em toda a tela.

Decisões recomendadas:

- evitar transformar paisagem em layout “apertado”; preferir densidade moderada com hierarquia clara;
- evitar esconder informações para caber na tela; preferir reorganizar;
- manter `overflow-y: auto` e evitar soluções que congelem scroll.

Critério de conclusão:

- a tela em paisagem pode ser usada integralmente, sem overlay, sem cortes e sem sensação de improviso.

Execucao registrada em 2026-04-25:

1. A Fase 2 foi implementada sem reabrir escopo em JavaScript: a reorganizacao de paisagem mobile ficou concentrada em `styles.css`, com apenas um gancho estrutural minimo no HTML (`id="registrationField"`) para nomear com clareza a area do grupo `Registro`.
2. Foi consolidado como breakpoint operacional de paisagem mobile o recorte `@media (orientation: landscape) and (max-height: 540px)`, reaproveitando o ponto de entrada responsivo que ja existia e ampliando-o de ajuste cosmetico para composicao real de uso.
3. Dentro desse breakpoint, a `.check-form` passou a usar uma grade de duas colunas com areas nomeadas: a coluna esquerda concentra `history`, `notification` e `location`, enquanto a coluna direita concentra `auth`, `registration`, `informe`, `project` e `submit`, preservando leitura, toque e scroll sem exigir redesign do fluxo funcional.
4. O header, os paddings, os gaps e a densidade visual dos cards foram reduzidos de forma controlada para telas baixas; ao mesmo tempo, `align-self: start` na `.check-card` e a ausencia de novos bloqueios de overflow mantiveram o scroll vertical natural da pagina.
5. A linha de autenticacao, os grupos `Registro` e `Informe`, a linha `Projeto` + `Local` e o botao `Registrar` receberam acomodacao especifica para paisagem, incluindo distribuicao horizontal, espacamentos menores e protecao adicional contra estrangulamento da legenda `Atividades Automáticas` com `flex-wrap`.
6. Dialogs e a tela de transporte tambem foram ajustados para paisagem baixa: `password-dialog` e `transport-screen` passaram a alinhar pelo topo util, e o card de transporte ganhou largura util maior nesse contexto para reduzir sensacao de aperto.
7. A cobertura estatica foi atualizada em `tests/check_responsive_layout.test.js` para proteger a nova grade de paisagem e garantir que a reorganizacao nao reintroduza bloqueios de scroll ou regressoes na sincronizacao de viewport.
8. Esta fase continua restrita ao uso confortavel em paisagem mobile. O refinamento visual contido para notebook e desktop permanece reservado para a Fase 3, e a homologacao visual/manual ampla permanece concentrada na Fase 6.

## Fase 3. Preparar modo desktop bonito, contido e organizado

Objetivo:

- entregar uma apresentação elegante em computador, preservando a identidade do webapp.

Atividades:

- definir breakpoints de desktop distintos do mobile landscape;
- revisar a largura máxima da shell principal para um valor mais equilibrado no desktop, sem full width;
- reorganizar o interior do card principal para melhor distribuição horizontal;
- reduzir quebras de linha indevidas em:
  - card de localização;
  - autenticação;
  - grupos de escolha;
  - linha de projeto/local;
  - notificações;
- revisar alinhamento, paddings internos e respiro entre blocos;
- garantir que o fundo, a marca d'água e o cabeçalho continuem elegantes em telas amplas;
- revisar a tela de transporte e seus overlays/dialogs para largura e altura úteis em desktop;
- evitar excesso de espaço vazio acima, abaixo ou nas laterais.

Direção visual recomendada:

- card principal centralizado;
- largura controlada e visualmente premium;
- uso inteligente da largura extra para reduzir empilhamento e não para espalhar elementos.

Critério de conclusão:

- a aplicação fica claramente melhor em notebook/desktop sem perder o DNA visual do mobile webapp.

Execucao registrada em 2026-04-25:

1. A Fase 3 foi implementada integralmente em `styles.css`, sem alterar regras funcionais da SPA: o desktop passou a ter uma trilha responsiva propria, separada do ajuste de paisagem baixa feito na Fase 2.
2. Foi criado um nivel desktop base em `@media (min-width: 1024px)`, que amplia a shell de forma contida, eleva `--card-max-width` para `1040px`, melhora os paddings internos do card principal e alarga dialogs/paineis de transporte para um uso mais confortavel em notebook.
3. Foi criado um nivel desktop de composicao em `@media (min-width: 1180px)`, no qual a `.check-form` passa a usar uma grade de duas regioes bem definidas: `history/notification/location` de um lado e `auth/registration/informe/project/submit` do outro, reduzindo empilhamento desnecessario sem virar layout full width.
4. A linha `Projeto` + `Local` recebeu refinamento proprio para desktop com ampliacao de `check-field-compact`, evitando que o seletor de projeto continue excessivamente estreito num contexto em que ha largura sobrando.
5. O refinamento visual em desktop tambem alcancou a tela de transporte: o card principal foi alargado de forma controlada, os botoes de opcao passaram a se distribuir em tres colunas, o builder ficou menos comprimido, o historico passou a aproveitar a largura extra com duas colunas, e o detalhe da solicitacao ganhou card mais largo.
6. Dialogs de senha/cadastro tambem foram revistos para notebook/desktop, com larguras maiores e ainda contidas, preservando a identidade visual e evitando sensacao de painel estreito demais no centro da tela.
7. `tests/check_responsive_layout.test.js` foi atualizado para proteger tanto a nova escalada de largura do card principal quanto a composicao desktop da shell e das superficies de transporte; a validacao focada passou sem regressao nas guardas de orientacao e de transporte.
8. Esta fase conclui o refinamento estrutural para desktop, mas a homologacao visual/manual real em notebook e desktop amplo continua pertencendo a Fase 6, onde sera possivel aprovar proporcao, respiro e leitura em tela real.

## Fase 4. Ajuste de microcopy do botão de transporte

Objetivo:

- trocar a label `Em breve` para `Em Teste`.

Atividades:

- alterar o texto visível no `#transportButton` em `index.html`;
- revisar se há textos derivados, labels acessíveis, snapshots ou asserts que mencionem o texto antigo;
- garantir consistência visual do novo texto no botão em mobile, paisagem e desktop.

Critério de conclusão:

- o botão passa a exibir `Em Teste` sem regressão visual nem quebra de cobertura automatizada.

Execucao registrada em 2026-04-25:

1. O texto visivel do `#transportButton` em `index.html` foi alterado de `Em breve` para `Em Teste`, sem qualquer mudanca de semantica funcional, classes CSS, listeners ou fluxo de bloqueio do botao.
2. A revisao de impacto confirmou que o rótulo antigo nao era usado por `app.js` nem por asserts automatizados existentes; o botao continua identificado tecnicamente por `id="transportButton"` e pelas classes `choice-card transport-choice-button`.
3. Foi adicionada cobertura focada em `tests/check_auth_transport_ui.test.js` para proteger explicitamente a nova microcopy do botao principal de entrada do transporte e evitar regressao silenciosa para `Em breve`.
4. Como a troca manteve o mesmo contexto visual, a mesma hierarquia HTML e uma extensao textual equivalente, nao houve necessidade de ajuste adicional de layout em retrato, paisagem ou desktop nesta fase; a homologacao visual/manual ampla continua pertencendo a Fase 6.

## Fase 5. Testes automatizados e atualização das guardas de regressão

Objetivo:

- substituir as expectativas de retrato-only por guardas coerentes com o novo comportamento.

Atividades:

- revisar `tests/check_portrait_lock.test.js` e decidir entre:
  - reescrever o arquivo para validar paisagem suportada;
  - ou substituir por um novo teste semanticamente alinhado, por exemplo de `landscape layout`;
- atualizar `tests/check_responsive_layout.test.js` para refletir:
  - novos breakpoints;
  - nova largura máxima;
  - nova composição em paisagem e desktop;
- incluir asserts para confirmar que o app já não depende de `portrait-lock-active`;
- incluir asserts para o novo texto `Em Teste`, se isso não estiver coberto por outro teste;
- adicionar proteção para scroll/layout em telas baixas e em desktop, quando possível.

Critério de conclusão:

- a suíte deixa de proteger o comportamento antigo e passa a proteger o comportamento novo desejado.

## Fase 6. Homologação manual orientada por cenário

Objetivo:

- validar a qualidade real do layout nos cenários que motivaram a mudança.

Cenários mínimos:

1. celular em retrato;
2. celular em paisagem;
3. celular em paisagem com teclado aberto nos campos de autenticação;
4. tablet ou viewport intermediária em paisagem;
5. notebook comum;
6. desktop amplo;
7. tela principal com histórico, notificações e localização preenchidos;
8. dialogs de senha e cadastro;
9. tela de transporte.

Pontos obrigatórios de validação:

- nenhuma seção crítica fica escondida ou ilegível;
- nenhum bloco apresenta espaçamentos exagerados;
- nenhum bloco sofre quebra de linha ruim sem necessidade;
- a largura percebida em desktop é elegante e contida;
- a experiência em retrato continua estável.

Critério de conclusão:

- os três modos de uso relevantes, retrato mobile, paisagem mobile e desktop, ficam aprovados com a mesma base visual do produto atual.

Execucao registrada em 2026-04-25:

1. A homologacao da Fase 6 foi executada localmente, sem deploy e sem depender da URL pública, por meio do harness dedicado `scripts/capture_temp_006_homologation.mjs`, que monta a propria SPA do workspace com dados mockados e gera artefatos em `docs/temp_006_homologation/`.
2. Foram registrados os seguintes cenarios visuais para inspecao direta: retrato mobile, paisagem mobile, paisagem mobile com viewport reduzido e foco na senha como proxy de teclado aberto, viewport intermediaria em paisagem, notebook comum, desktop amplo, dialog de senha, dialog de cadastro, tela de transporte e detalhe de solicitacao de transporte.
3. A inspeção visual confirmou que o retrato permaneceu estavel, que a paisagem mobile foi destravada sem overlay de bloqueio, que o layout intermediario/tablet e o layout desktop permaneceram contidos, e que a microcopy `Em Teste` aparece corretamente no shell principal durante a homologacao.
4. O item “teclado aberto” foi validado localmente por proxy documentado: em navegador headless nao ha renderizacao do teclado virtual do sistema operacional, entao o cenario foi homologado com viewport reduzido e foco no campo de senha para simular a perda de altura util e observar a continuidade da leitura sem corte critico.
5. Durante a inspeção foi identificado um excesso de espaço vazio na tela base de transporte em notebook; a correção foi feita no mesmo fluxo da Fase 6, ajustando a altura do `transport-screen-card` para `auto` no breakpoint desktop e regenerando os artefatos antes de concluir a homologacao.
6. Os artefatos finais da homologacao ficaram registrados em `docs/temp_006_homologation/README.md`, `docs/temp_006_homologation/manifest.json` e na pasta `docs/temp_006_homologation/screenshots/`, formando a evidência local desta fase sem commit, push ou deploy.
7. Com base nessa homologacao local assistida por screenshots, os cenarios previstos na Fase 6 foram aprovados para este recorte de trabalho, mantendo como ressalva apenas a natureza de proxy do caso “teclado aberto”, explicitamente documentada nos artefatos.

## 9. Critérios Técnicos de Aceite

A implementação futura só deve ser considerada aprovada se atender simultaneamente a todos os critérios abaixo:

1. A aplicação deixa de bloquear paisagem no mobile.
2. O overlay de retrato-only não aparece mais como bloqueio de uso.
3. O layout em paisagem continua legível, tocável e com scroll funcional.
4. O layout desktop fica centralizado, bonito e sem largura exagerada.
5. Não há regressão visual relevante em retrato.
6. Não há regressão funcional em autenticação, localização, check manual, automação ou transporte.
7. O botão de transporte passa a exibir `Em Teste`.
8. A suíte de testes deixa de assumir portrait-only e passa a refletir o novo comportamento.

## 10. Riscos e Mitigações

### Risco 1. Remover o bloqueio de paisagem expor um layout quebrado em telas baixas

Mitigação:

- tratar o desbloqueio e o novo layout como a mesma frente de trabalho;
- homologar especificamente em paisagem de baixa altura;
- manter scroll vertical liberado.

### Risco 2. O desktop ficar “solto” demais ou vazio demais

Mitigação:

- manter largura máxima controlada;
- usar melhor distribuição interna em vez de simplesmente aumentar largura;
- validar em notebook real, não só em viewport muito grande.

### Risco 3. Regressão em retrato mobile

Mitigação:

- preservar tokens e estrutura base já consolidados;
- aplicar mudanças condicionais por breakpoint;
- testar retrato como cenário obrigatório de aceite.

### Risco 4. Seletores de CSS ficarem frágeis para reorganização dos blocos

Mitigação:

- introduzir IDs ou classes auxiliares explícitas no HTML quando necessário;
- evitar depender de seletores implícitos ou de ordem frágil entre fieldsets.

### Risco 5. Testes antigos travarem a mudança correta

Mitigação:

- revisar `check_portrait_lock.test.js` antes da implementação principal;
- alinhar a cobertura automatizada ao comportamento desejado final.

## 11. Recomendação Final

A recomendação mais sólida é tratar esta demanda como uma revisão coordenada de apresentação da shell principal, e não como um ajuste isolado de CSS.

Em termos práticos, o melhor caminho é:

1. remover a política retrato-only no HTML/CSS/JS;
2. preparar um modo paisagem mobile de verdade;
3. preparar um modo desktop contido e elegante, sem full width;
4. trocar `Em breve` por `Em Teste`;
5. atualizar testes e homologar nos três cenários principais: retrato, paisagem e desktop.

## 12. To-do List Completa de Execução

### Fase 0. Escopo, baseline e congelamento funcional

- [x] Confirmar que a demanda é frontend-only.
- [x] Confirmar que não haverá alteração de backend, endpoints ou regras de negócio.
- [x] Registrar screenshots baseline de retrato, paisagem bloqueada atual e desktop atual.
- [x] Registrar os testes atuais que assumem portrait-only.
- [x] Registrar a largura máxima e os breakpoints atuais como baseline técnico.

### Fase 1. Desbloqueio de paisagem

- [x] Revisar o markup de `orientationLockScreen` em `index.html`.
- [x] Decidir entre remoção definitiva ou neutralização controlada do overlay de bloqueio.
- [x] Remover ou neutralizar o CSS de `.orientation-lock-screen`.
- [x] Remover ou neutralizar o CSS de `body.portrait-lock-active`.
- [x] Remover a ocultação de `header` e `.check-shell` em paisagem.
- [x] Remover do `app.js` a alternância de `portrait-lock-active`.
- [x] Remover do `app.js` a exibição do overlay em paisagem.
- [x] Remover do `app.js` a tentativa de `screen.orientation.lock('portrait')` do fluxo normal.
- [x] Preservar apenas a infraestrutura útil de viewport e realinhamento.

### Fase 2. Layout de paisagem mobile

- [x] Definir breakpoint principal para paisagem mobile.
- [x] Reduzir altura visual do header em paisagem.
- [x] Reduzir paddings e gaps verticais em paisagem.
- [x] Reorganizar blocos principais da shell para melhor uso da largura.
- [x] Revisar a composição de histórico, notificação e localização em paisagem.
- [x] Revisar a linha de autenticação em paisagem.
- [x] Revisar o grupo `Registro` em paisagem.
- [x] Revisar o grupo `Informe` em paisagem.
- [x] Revisar a linha `Projeto` + `Local` em paisagem.
- [x] Garantir visibilidade confortável do botão `Registrar`.
- [x] Garantir scroll vertical funcional em paisagem.
- [x] Revisar dialogs para uso em paisagem.

### Fase 3. Layout desktop

- [x] Definir breakpoint(s) específicos de desktop.
- [x] Revisar a largura máxima do card/shell principal para desktop.
- [x] Manter o layout centralizado e contido.
- [x] Reorganizar a distribuição interna das seções no desktop.
- [x] Eliminar quebras de linha indevidas em campos e títulos.
- [x] Ajustar gaps, paddings e alinhamentos para notebook/desktop.
- [x] Revisar a apresentação da tela de transporte em desktop.
- [x] Revisar dialogs e overlays em desktop.
- [x] Garantir que não haja sensação de espaço vazio exagerado.

### Fase 4. Microcopy do botão

- [x] Alterar a label de `Em breve` para `Em Teste` em `#transportButton`.
- [x] Revisar se existem asserts, snapshots ou textos auxiliares esperando o texto antigo.
- [x] Validar visualmente o novo texto em retrato, paisagem e desktop.

### Fase 5. Testes automatizados

- [x] Atualizar ou substituir `tests/check_portrait_lock.test.js`.
- [x] Atualizar `tests/check_responsive_layout.test.js`.
- [x] Adicionar cobertura para paisagem suportada.
- [x] Adicionar cobertura para layout desktop refinado.
- [x] Adicionar cobertura para a label `Em Teste`, se necessário.
- [x] Executar primeiro os testes JavaScript diretamente tocados.
- [x] Revisar e corrigir qualquer expectativa antiga de portrait-only.

### Fase 6. Homologação manual

- [x] Homologar em retrato mobile.
- [x] Homologar em paisagem mobile.
- [x] Homologar em paisagem mobile com teclado aberto.
- [x] Homologar em viewport intermediária.
- [x] Homologar em notebook.
- [x] Homologar em desktop amplo.
- [x] Homologar dialogs de senha e cadastro.
- [x] Homologar a tela de transporte.
- [x] Confirmar ausência de cortes, overflow e quebras ruins.
- [x] Confirmar ausência de espaçamentos exagerados em desktop.
- [x] Confirmar que o retrato não regrediu.

## 13. Encerramento

Se este plano for seguido com disciplina, a aplicação continuará visualmente reconhecível, mas deixará de ser retrato-only e passará a ter apresentação coerente tanto em paisagem quanto em desktop. O ganho esperado não é apenas “abrir sem bloquear”: o ganho esperado é tornar a SPA realmente utilizável e agradável nesses contextos, sem abrir escopo desnecessário fora do frontend.
