# Plano da Modificacao 4 - Widget Ajustes, cadastro automatico e manual completo do Checking Web

## Objetivo

Reorganizar o fluxo de autenticacao e configuracoes do `Checking Web` para que:

1. o botao ao lado do campo `Senha` deixe de existir na tela principal;
2. no lugar dele apareca um icone de engrenagem baseado em `assets/icons/config.webp`;
3. esse icone abra um novo widget `Ajustes`;
4. o widget `Ajustes` concentre:
   - troca de idioma;
   - acao de resetar/alterar senha;
   - reacesso a permissao de localizacao;
   - suporte via WhatsApp;
   - abertura do manual completo da aplicacao;
5. quando a chave nao existir no banco, o cadastro de usuario abra automaticamente;
6. quando a chave existir mas ainda nao tiver senha, o cadastro de senha abra automaticamente;
7. o comportamento atual de alteracao de senha seja preservado, mudando apenas o ponto de entrada;
8. seja criado um manual completo, com snapshots reais da aplicacao, acessivel a partir da propria interface web.


## Confirmacoes tecnicas ja validadas

1. O arquivo `assets/icons/config.webp` existe no repositorio.
2. O backend monta `/assets` a partir da pasta raiz `assets`, portanto o icone pode ser servido no navegador por ` /assets/icons/config.webp `.
3. O `Checking Web` atual ja usa o shell estatico em `sistema/app/static/check` e ja possui estrutura de dialogs reaproveitavel.
4. O modulo `transport` ja possui uma base de i18n e um modal de settings que podem servir como referencia de arquitetura para o `Checking Web`.


## Estado atual confirmado

1. Tela principal:
   - a linha de autenticacao fica em `sistema/app/static/check/index.html`;
   - o botao principal da area de senha e `#passwordActionButton`;
   - sua label muda dinamicamente entre `Senha`, `Senha?`, `Chave?`, `Verificando...` e `Aguarde`.

2. Fluxo de chave nao encontrada:
   - o frontend consulta `GET /api/web/auth/status`;
   - quando `found = false`, o botao vira `Chave?`;
   - ao clicar, abre o dialogo de cadastro de usuario.

3. Fluxo de usuario sem senha:
   - quando `found = true` e `has_password = false`, o botao vira `Senha?`;
   - ao clicar, abre o dialogo de senha em modo de cadastro.

4. Fluxo de alteracao de senha:
   - usa o mesmo dialogo visual de senha;
   - em modo `change`, envia `chave`, `senha_antiga` e `nova_senha` para `/api/web/auth/change-password`.

5. Localizacao:
   - o frontend ja consulta o estado da permissao com `navigator.permissions.query({ name: 'geolocation' })` quando disponivel;
   - existe estado local `gpsLocationPermissionGranted`;
   - existem flags em `localStorage` para lembrar tentativa e concessao de permissao.

6. Idioma:
   - o `Checking Web` ainda nao possui camada propria de i18n;
   - o dashboard `transport` ja possui lista de idiomas e dicionarios reutilizaveis como referencia.

7. Manual:
   - ainda nao existe manual dedicado do `Checking Web` acessivel pela propria UI;
   - tambem nao existe pacote de snapshots curados para o usuario final.


## Resultado funcional desejado

### 1. Shell principal

1. Remover a funcao de CTA do antigo botao ao lado de `Senha`.
2. Inserir um botao visual de configuracao com icone de engrenagem.
3. O novo botao deve manter a mesma altura visual que o botao antigo, preservando o alinhamento da linha de autenticacao.
4. O novo botao nao deve mais exibir `Senha?` nem `Chave?`.

### 2. Widget Ajustes

O widget deve abrir a partir do icone de engrenagem e conter:

1. `Idioma`
   - dropdown de selecao;
   - persistencia local do idioma escolhido;
   - aplicacao imediata dos textos sem recarregar a pagina, se possivel.

2. `Resetar Senha`
   - acao que abre o fluxo existente de alteracao de senha;
   - manter o mesmo formulario de 3 campos:
     - senha antiga;
     - nova senha;
     - confirma senha.

3. `Permitir localizacao`
   - acao que tenta disparar novamente a solicitacao de permissao de geolocalizacao precisa;
   - se a permissao ja estiver concedida e a localizacao estiver compartilhada, o botao fica desabilitado.

4. `Suporte`
   - abre conversa no WhatsApp para `+5521992174446`;
   - mensagem pre-preenchida:
     - `Preciso de ajuda com a aplicacao Web. Minha chave e <chave do usuario>.`

5. `Sobre`
   - abre o manual completo da aplicacao web;
   - esse manual deve ser novo e conter snapshots reais.

### 3. Autoabertura dos fluxos de cadastro

1. Chave inexistente:
   - ao resolver o status da chave, o frontend deve abrir automaticamente o cadastro de usuario;
   - nao deve mais depender da label `Chave?`.

2. Usuario sem senha:
   - ao resolver o status da chave, o frontend deve abrir automaticamente o cadastro de senha;
   - nao deve mais depender da label `Senha?`.


## Decisoes de implementacao recomendadas

### 1. Reutilizar a infraestrutura de dialog existente

Recomendacao:

1. Manter o dialog de senha atual como container unico para:
   - cadastrar senha;
   - alterar senha.
2. Manter o dialog de cadastro de usuario atual.
3. Criar um novo dialog `Ajustes` seguindo o mesmo padrao visual de backdrop + card + formulario/acoes.

Motivo:

1. minimiza regressao visual;
2. aproveita a logica de foco, `Escape`, backdrop e `syncFormControlStates`;
3. reduz custo de manutencao.

### 2. Tratar o icone de engrenagem como substituto visual do antigo botao

Recomendacao:

1. manter o container `auth-field-button`;
2. trocar o `#passwordActionButton` por um `#settingsButton` com imagem `config.webp`;
3. preservar `min-height: var(--control-height)`.

Motivo:

1. evita quebrar o grid da linha de autenticacao;
2. facilita responsividade;
3. atende o requisito de mesma altura do botao anterior.

### 3. Separar nitidamente tres responsabilidades que hoje estao misturadas

Hoje o botao principal cumpre tres papeis:

1. abrir cadastro de usuario;
2. abrir cadastro de senha;
3. abrir alteracao de senha.

Depois da mudanca, a responsabilidade deve ficar assim:

1. `status da chave` decide autoabrir cadastro de usuario;
2. `status da chave` decide autoabrir cadastro de senha;
3. `Ajustes > Resetar Senha` abre apenas alteracao de senha.

Motivo:

1. reduz ambiguidade;
2. melhora previsibilidade da UX;
3. simplifica o estado do botao principal.

### 4. Reutilizar a base de i18n do modulo transport como padrao, nao como copia cega

Recomendacao:

1. criar um `i18n.js` proprio do `Checking Web`;
2. usar a mesma lista inicial de idiomas ja disponivel no `transport`:
   - `pt`;
   - `en`;
   - `zh`;
   - `ms`;
   - `tl`.
3. adaptar o modelo de dicionario, `resolveLanguageCode`, persistencia local e `switchLanguage`.

Motivo:

1. unifica experiencia entre superficies web do sistema;
2. reduz invencao paralela;
3. evita acoplamento desnecessario entre `check` e `transport`.

### 5. Manual completo deve ser pagina dedicada, nao um bloco gigante dentro do app principal

Recomendacao:

1. criar uma pagina estatica dedicada do manual em `sistema/app/static/check`;
2. abrir essa pagina a partir do item `Sobre`;
3. usar snapshots reais armazenados junto dos assets do manual.

Motivo:

1. manual com snapshots tende a ficar extenso;
2. uma pagina dedicada e melhor para leitura, manutencao e compartilhamento;
3. evita sobrecarregar o bundle principal do app.


## Escopo por arquivo e por camada

## 1. Frontend - estrutura HTML

### Arquivo principal

`sistema/app/static/check/index.html`

### Mudancas planejadas

1. Substituir o botao visual de autenticacao por um botao de ajustes com icone.
2. Criar a estrutura HTML do novo widget `Ajustes`.
3. Incluir:
   - label e `select` de idioma;
   - botao `Resetar Senha`;
   - botao `Permitir localizacao`;
   - botao `Suporte`;
   - botao `Sobre`;
   - botao de fechar/voltar.
4. Garantir atributos de acessibilidade:
   - `role="dialog"`;
   - `aria-modal="true"`;
   - `aria-labelledby`;
   - `aria-controls` no botao de abertura;
   - `aria-expanded` no botao de abertura.
5. Decidir se o botao `Resetar Senha` ficara:
   - sempre visivel, mas desabilitado quando nao houver sessao liberada;
   - ou visivel apenas quando `authState.hasPassword = true`.

### Recomendacao de UX

Adotar a primeira opcao:

1. item sempre visivel no `Ajustes`;
2. desabilitado quando nao houver sessao apta;
3. texto explicativo curto no widget quando a acao nao estiver disponivel.


## 2. Frontend - estilos

### Arquivo principal

`sistema/app/static/check/styles.css`

### Mudancas planejadas

1. Criar estilo do novo `settingsButton`:
   - mesma altura do antigo botao;
   - largura apropriada para um botao quadrado ou quase quadrado;
   - foco visivel;
   - estados `hover`, `active`, `disabled`.
2. Criar estilo do icone `config.webp`:
   - controlar altura interna com `object-fit: contain`;
   - evitar distorcao;
   - garantir contraste do botao.
3. Criar os estilos do dialog `Ajustes`:
   - card;
   - grid/lista de opcoes;
   - linha com label + controle;
   - botoes de acao.
4. Prever responsividade em viewport baixa:
   - scroll interno;
   - espacos reduzidos;
   - controles clicaveis.
5. Estilizar estados desabilitados:
   - `Permitir localizacao` quando a permissao ja estiver concedida;
   - `Resetar Senha` quando a sessao nao permitir alteracao.


## 3. Frontend - logica de UI e estado

### Arquivo principal

`sistema/app/static/check/app.js`

### Frentes de alteracao

#### 3.1. Substituicao do antigo botao principal

1. Remover o papel de `passwordActionButton` da tela principal.
2. Introduzir referencias DOM novas:
   - `settingsButton`;
   - `settingsDialog`;
   - `settingsDialogBackdrop`;
   - `settingsLanguageSelect`;
   - `settingsResetPasswordButton`;
   - `settingsLocationPermissionButton`;
   - `settingsSupportButton`;
   - `settingsAboutButton`;
   - `settingsBackButton`;
   - opcionalmente um elemento de status interno do widget.
3. Atualizar arrays de controle:
   - `authControls`;
   - `processControls`;
   - colecoes de controles por dialog.
4. Atualizar `syncFormControlStates()` para controlar:
   - habilitacao do botao de ajustes;
   - habilitacao individual dos itens do widget;
   - fechamento seguro de painel quando estado global travar.

#### 3.2. Novo fluxo de abertura do widget Ajustes

1. Criar helpers:
   - `isSettingsDialogOpen`;
   - `openSettingsDialog`;
   - `closeSettingsDialog`;
   - `syncSettingsDialogState`.
2. Integrar com:
   - `isAnyDialogOpen`;
   - tecla `Escape`;
   - clique no backdrop;
   - restauracao de foco para o botao de engrenagem ao fechar.

#### 3.3. Remocao do comportamento `Chave?` e `Senha?`

1. Remover a troca de label do botao principal para `Chave?` e `Senha?`.
2. Simplificar a logica de `resolvePasswordActionButtonLabel`, ou remover essa funcao se ela deixar de fazer sentido.
3. Revisar todos os pontos que hoje fazem:
   - `isMissingUserRegistrationState()`;
   - `isMissingPasswordRegistrationState()`;
   - `isPasswordActionAssistanceModeActive()`.
4. O comportamento novo deve ser:
   - ao concluir `refreshAuthenticationStatus`, se `found = false`, abrir automaticamente `openRegistrationDialog()`;
   - se `found = true` e `has_password = false`, abrir automaticamente `openPasswordDialog()` em modo `register`.

#### 3.4. Protecao contra autoabertura repetitiva

Esse ponto e critico.

Sem cuidado, o app pode reabrir o modal em loop sempre que:

1. o usuario fechar manualmente;
2. o status for reconsultado;
3. a chave continuar inexistente;
4. ou a senha continuar ausente.

Recomendacao:

1. criar flags por chave para a sessao corrente, por exemplo:
   - `lastAutoOpenedRegistrationChave`;
   - `lastAutoOpenedPasswordRegistrationChave`;
   - ou um mapa mais generico de `autoPromptState`.
2. abrir automaticamente apenas quando:
   - a chave acabou de ser resolvida;
   - e ainda nao houve autoabertura para aquele estado/chave desde a ultima mudanca relevante.
3. resetar essas flags quando:
   - a chave mudar;
   - o cadastro for concluido;
   - a senha for criada com sucesso;
   - o status passar para outro estado.

#### 3.5. Acao "Resetar Senha" dentro de Ajustes

1. O item deve chamar o mesmo dialog de senha ja existente.
2. Quando o usuario clicar em `Resetar Senha`:
   - fechar `Ajustes`;
   - abrir `openPasswordDialog()` em modo `change`.
3. Manter a validacao atual de:
   - tamanho da senha antiga;
   - tamanho da nova senha;
   - confirmacao igual;
   - envio para `/api/web/auth/change-password`.
4. Remover quaisquer dependencias antigas do clique no botao principal.

#### 3.6. Acao "Permitir localizacao"

1. Reaproveitar a infraestrutura existente de permissao e captura.
2. Criar uma funcao especifica, por exemplo:
   - `requestPreciseLocationPermissionFromSettings()`.
3. O fluxo recomendado:
   - se o navegador nao suportar `geolocation`, mostrar mensagem clara;
   - se o contexto nao for seguro (`https`), mostrar mensagem clara;
   - se a permissao ja estiver concedida, manter o botao desabilitado;
   - se a permissao ainda nao estiver concedida, disparar `resolveCurrentLocation({ interactive: true, forceRefresh: true, showDetectingState: true })`;
   - se o browser permitir, reconsultar `queryLocationPermissionState()` ao fim;
   - sincronizar `gpsLocationPermissionGranted`, `locationPermissionGrantedKey` e a UI.
4. Atualizar o texto do widget para indicar:
   - `Localizacao ja permitida`;
   - ou `Solicitar permissao`.

#### 3.7. Acao "Suporte" via WhatsApp

1. Montar o link com `https://wa.me/5521992174446?text=...`.
2. Encodar a mensagem com `encodeURIComponent`.
3. A mensagem base recomendada:
   - `Preciso de ajuda com a aplicacao Web. Minha chave e <CHAVE>.`
4. Obter a chave do contexto por prioridade:
   - chave autenticada atual;
   - senao chave digitada no campo principal, se tiver 4 caracteres;
   - senao string vazia ou placeholder neutro.
5. Recomendacao de UX:
   - manter o botao habilitado apenas se houver chave com 4 caracteres;
   - ou, se preferir nao desabilitar, usar fallback:
     - `Preciso de ajuda com a aplicacao Web. Minha chave ainda nao foi informada.`

Recomendacao principal:

1. habilitar o botao somente quando houver chave valida;
2. assim o requisito da mensagem com chave fica consistente.

#### 3.8. Acao "Sobre" e abertura do manual

1. Criar helper:
   - `openCheckingWebManual()`.
2. Abrir a pagina dedicada do manual:
   - na mesma aba;
   - ou em nova aba.

Recomendacao:

1. abrir em nova aba com `noopener`;
2. manter o app principal intacto;
3. permitir ao usuario consultar o manual sem perder o estado do formulario.

#### 3.9. Idioma e i18n

1. Criar suporte de idioma proprio do `Checking Web`.
2. Extrair textos fixos do app para dicionarios.
3. Garantir traducao de:
   - labels da tela principal;
   - mensagens de status;
   - dialogs de cadastro/senha;
   - widget `Ajustes`;
   - pagina do manual.
4. Persistir idioma em `localStorage`.
5. Aplicar idioma inicial por ordem:
   - idioma salvo;
   - idioma do navegador;
   - fallback `pt`.


## 4. Frontend - estado reutilizavel

### Arquivo principal

`sistema/app/static/check/web-client-state.js`

### Mudancas planejadas

1. Adicionar helpers de idioma, se a estrategia escolhida for concentrar parte da logica nesse modulo.
2. Opcionalmente incluir helpers para:
   - normalizar codigo de idioma;
   - resolver idioma padrao pelo navegador;
   - decidir se o botao de localizacao deve ser considerado concluido/desabilitado.
3. Nao mover para esse arquivo regras muito acopladas ao DOM; manter nele apenas regras puras.


## 5. Frontend - novo modulo de i18n

### Arquivos recomendados

1. `sistema/app/static/check/i18n.js`
2. opcionalmente `sistema/app/static/check/manual-i18n.js` se o manual ficar grande o bastante para justificar separacao.

### Conteudo esperado

1. lista de idiomas;
2. dicionarios;
3. helpers:
   - `getDictionary`;
   - `resolveLanguageCode`;
   - `getStoredLanguageCode`;
   - `setStoredLanguageCode`;
   - `t`.

### Estrategia recomendada

1. reaproveitar o desenho tecnico do `transport`;
2. evitar importar diretamente o JS do transporte;
3. manter independencia entre bundles.


## 6. Manual completo do Checking Web

### Estrutura recomendada

Criar uma pequena superficie estatica propria do manual, por exemplo:

1. `sistema/app/static/check/manual.html`
2. `sistema/app/static/check/manual.css`
3. `sistema/app/static/check/manual.js`
4. `sistema/app/static/check/manual-assets/`

### Conteudo minimo do manual

1. Visao geral da aplicacao.
2. Como informar a chave.
3. Como funciona o cadastro automatico de usuario.
4. Como funciona o cadastro automatico de senha.
5. Como fazer login.
6. Como registrar `Check-In` e `Check-Out`.
7. Como selecionar projetos.
8. Como funciona localizacao:
   - permissao;
   - localizacao indisponivel;
   - precisao baixa;
   - atividades automaticas.
9. Como usar o modulo de transporte.
10. Como alterar senha.
11. Como usar `Ajustes`.
12. Como acionar `Suporte`.
13. Perguntas frequentes e mensagens comuns de erro.

### Snapshots necessarios

Recomendacao de lista minima:

1. tela inicial com chave e senha;
2. cadastro automatico de usuario;
3. cadastro automatico de senha;
4. widget `Ajustes`;
5. dialog de alteracao de senha;
6. estado de localizacao concedida;
7. estado de localizacao negada;
8. tela com projetos selecionados;
9. fluxo de transporte;
10. exemplo de status de sucesso apos `Check-In` ou `Check-Out`.

### Estrategia de captura dos snapshots

1. Implementar primeiro a UI final.
2. Preparar dados previsiveis para captura:
   - chave de exemplo;
   - projetos de exemplo;
   - estado autenticado;
   - estado sem permissao de localizacao;
   - estado com permissao;
   - dialogos abertos.
3. Capturar snapshots em viewport mobile realista e, se necessario, um conjunto adicional desktop.
4. Curar as imagens:
   - remover ruido desnecessario;
   - garantir legibilidade;
   - revisar se ha dados sensiveis.
5. Exportar os assets finais para `manual-assets`.

### Observacao importante

O requisito fala em snapshots reais, entao o plano deve considerar:

1. capturas de tela da interface implementada;
2. nao apenas mockups estaticos;
3. revisao final de consistencia entre texto do manual e app real.


## 7. Backend

### Mudancas obrigatorias

Nenhuma mudanca de contrato de API e estritamente necessaria para cumprir o requisito principal, porque:

1. `GET /api/web/auth/status` ja informa `found` e `has_password`;
2. `POST /api/web/auth/register-user` ja cria usuario e autentica;
3. `POST /api/web/auth/register-password` ja cria senha para usuario existente;
4. `POST /api/web/auth/change-password` ja troca senha;
5. a localizacao ja usa endpoints existentes.

### Mudancas opcionais recomendadas

1. Se o manual ganhar URL amigavel, considerar rota dedicada para `manual`:
   - opcional apenas se a estrategia com `manual.html` nao for suficiente.
2. Se o suporte por WhatsApp precisar ser auditado no futuro, considerar endpoint de telemetria, mas isso esta fora do requisito atual.


## 8. Acessibilidade

### Requisitos de implementacao

1. O botao de engrenagem precisa de `aria-label` claro:
   - `Abrir ajustes`.
2. O dialog `Ajustes` deve:
   - prender o foco enquanto aberto, se possivel;
   - fechar com `Escape`;
   - devolver foco ao disparador.
3. O icone nao pode ser a unica forma de entendimento:
   - usar `aria-label` e, se necessario, texto oculto.
4. Os botoes desabilitados devem ter motivo perceptivel:
   - por exemplo, descricao curta ou mensagem de status.
5. O manual deve manter boa hierarquia semantica:
   - `h1`, `h2`, listas e imagens com `alt`.


## 9. Responsividade

### Ponto de atencao

O `Checking Web` ja e fortemente orientado a mobile. O widget `Ajustes` nao pode:

1. quebrar a largura da linha de autenticacao;
2. criar targets pequenos demais;
3. ficar maior que a viewport sem scroll interno;
4. competir visualmente com dialogs de senha/cadastro.

### Recomendacao

1. usar o mesmo padrao dos dialogs existentes;
2. manter o card com largura proxima do dialog de senha;
3. adotar lista vertical simples, sem layout sofisticado demais;
4. no mobile, usar botoes em largura total para as acoes internas.


## 10. Telemetria e comportamento de estado

### Recomendacoes

1. Registrar em medicao local ou eventos diagnosticos:
   - troca de idioma;
   - abertura automatica do cadastro de usuario;
   - abertura automatica do cadastro de senha;
   - tentativa de re-solicitar permissao de localizacao;
   - clique em suporte;
   - clique em sobre/manual.
2. Isso ajuda a diferenciar:
   - fluxo automatico disparado corretamente;
   - fluxo fechado pelo usuario;
   - falhas de permissao no navegador.

Essa parte pode ser leve, mas deve ser considerada no desenho.


## 11. Impacto esperado nos testes

### Testes de frontend existentes que precisarao ser atualizados

1. testes que hoje procuram labels `Chave?` e `Senha?` no botao principal;
2. testes que ainda validam a existencia funcional do `passwordActionButton`;
3. testes de HTML/CSS do widget de cadastro;
4. testes de UX relacionados a dialogs.

### Novos testes recomendados

#### 11.1. Estrutura HTML

1. existe `settingsButton`;
2. `settingsButton` aponta para `/assets/icons/config.webp`;
3. existe `settingsDialog`;
4. existem os controles:
   - idioma;
   - resetar senha;
   - permitir localizacao;
   - suporte;
   - sobre.

#### 11.2. Comportamento da chave

1. chave inexistente abre cadastro de usuario automaticamente;
2. chave existente sem senha abre cadastro de senha automaticamente;
3. o frontend nao fica reabrindo dialogo em loop apos fechamento manual;
4. chave alterada reseta corretamente o estado de autoabertura.

#### 11.3. Ajustes

1. clique no icone abre `Ajustes`;
2. `Escape` fecha `Ajustes`;
3. item `Resetar Senha` abre o dialog de alteracao de senha;
4. item `Permitir localizacao` fica desabilitado quando a permissao ja estiver concedida;
5. item `Suporte` monta o link correto com a chave;
6. item `Sobre` abre a URL correta do manual.

#### 11.4. Idioma

1. dropdown popula idiomas esperados;
2. troca de idioma atualiza labels principais;
3. idioma persiste em `localStorage`;
4. recarregamento restaura idioma salvo.

#### 11.5. Manual

1. pagina do manual carrega;
2. snapshots referenciados existem;
3. manual possui secoes minimas obrigatorias.

### Testes de API

Provavelmente os contratos principais permanecem os mesmos, mas vale manter ou reforcar:

1. `auth/status`;
2. `register-user`;
3. `register-password`;
4. `change-password`.


## 12. Riscos principais

### 1. Autoabertura em loop

Risco:

1. o frontend ficar reabrindo cadastro de usuario/senha sempre que o usuario tentar fechar.

Mitigacao:

1. flags por chave e por estado de autoabertura;
2. reset controlado apenas quando houver mudanca real do estado.

### 2. Regressao na troca de senha

Risco:

1. mover a entrada da acao quebrar o fluxo de alteracao existente.

Mitigacao:

1. manter o dialog e o submit atuais;
2. mudar apenas o ponto de disparo;
3. criar testes de regressao especificos.

### 3. Requisicao de permissao de localizacao nao disparar em todos os navegadores

Risco:

1. alguns browsers nao reabrem prompt se o usuario negou permanentemente.

Mitigacao:

1. tratar explicitamente estados:
   - `granted`;
   - `prompt`;
   - `denied`;
   - `unsupported`.
2. quando nao for possivel reabrir o prompt, orientar o usuario a usar configuracoes do navegador.

### 4. Crescimento grande do escopo por causa de i18n

Risco:

1. a mudanca de idioma puxar revisao de quase todo o texto da aplicacao.

Mitigacao:

1. separar em fase dedicada;
2. comecar pelos textos do shell principal e dos novos widgets;
3. expandir cobertura de mensagens progressivamente, com dicionarios centralizados.

### 5. Manual desatualizar rapido

Risco:

1. o manual ficar desalinhado da interface apos pequenas mudancas futuras.

Mitigacao:

1. manual em arquivos dedicados;
2. snapshots versionados;
3. checklist final de consistencia antes da entrega;
4. idealmente incluir o manual nos testes de existencia de assets.


## 13. Sequencia recomendada de implementacao

### Fase 1 - Preparacao e base

1. Criar branch/escopo da modificacao.
2. Mapear todos os seletores atuais ligados a `passwordActionButton`.
3. Criar inventario dos textos que passarao por i18n.
4. Definir estrutura final dos novos arquivos do manual.

### Fase 2 - Estrutura HTML do novo Ajustes

1. Inserir `settingsButton` no lugar visual do botao atual.
2. Inserir o dialog `Ajustes` em `index.html`.
3. Inserir `select` de idioma e botoes internos.

### Fase 3 - CSS do botao de engrenagem e do dialog

1. Estilizar o novo botao com o icone `config.webp`.
2. Garantir mesma altura do botao anterior.
3. Estilizar o dialog `Ajustes`.
4. Validar responsividade mobile.

### Fase 4 - Reorganizacao da logica de autenticacao

1. Remover dependencia funcional de `Chave?` e `Senha?`.
2. Implementar autoabertura do cadastro de usuario.
3. Implementar autoabertura do cadastro de senha.
4. Implementar protecao anti-loop.

### Fase 5 - Mover alteracao de senha para Ajustes

1. Fazer `Resetar Senha` abrir o dialog existente.
2. Revisar habilitacao/desabilitacao pelo estado autenticado.
3. Garantir que o submit atual continue igual.

### Fase 6 - Permissao de localizacao

1. Criar a acao de re-solicitar permissao.
2. Desabilitar quando localizacao ja estiver compartilhada.
3. Tratar navegadores sem suporte e contextos nao seguros.

### Fase 7 - Suporte via WhatsApp

1. Montar link com mensagem pre-preenchida.
2. Validar comportamento com chave autenticada e digitada.
3. Ajustar estado habilitado/desabilitado.

### Fase 8 - i18n do Checking Web

1. Criar `i18n.js`.
2. Migrar textos principais.
3. Integrar dropdown de idioma.
4. Persistir idioma e aplicar em runtime.

### Fase 9 - Manual e snapshots

1. Criar pagina do manual.
2. Escrever conteudo completo.
3. Capturar snapshots reais.
4. Referenciar snapshots finais.
5. Ligar `Sobre` ao manual.

### Fase 10 - Testes e consolidacao

1. Atualizar testes existentes.
2. Criar novos testes estruturais e comportamentais.
3. Rodar validacao visual mobile/desktop.
4. Revisar acessibilidade basica.
5. Revisar textos em todos os idiomas suportados.


## 14. Entregaveis finais esperados

1. Tela principal do `Checking Web` com botao de engrenagem no lugar do antigo botao de senha.
2. Widget `Ajustes` funcional com:
   - idioma;
   - resetar senha;
   - permitir localizacao;
   - suporte;
   - sobre.
3. Cadastro de usuario abrindo automaticamente quando a chave nao existir.
4. Cadastro de senha abrindo automaticamente quando o usuario existir sem senha.
5. Fluxo de alteracao de senha preservado dentro de `Ajustes`.
6. Pagina de manual completa com snapshots.
7. Suite de testes atualizada para o novo comportamento.


## 15. Recomendacao final de abordagem

Implementar esta modificacao em uma unica iniciativa funcional, mas com entrega interna em fases, nesta ordem:

1. nova entrada visual (`Ajustes`);
2. reorganizacao dos fluxos de autenticacao;
3. localizacao e suporte;
4. i18n;
5. manual com snapshots;
6. consolidacao de testes.

Essa ordem reduz risco porque:

1. primeiro estabiliza a navegacao e os gatilhos principais;
2. depois preserva e reaproveita os fluxos existentes de senha/cadastro;
3. por fim adiciona as camadas mais amplas e longas, como idioma e manual.
