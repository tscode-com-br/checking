# Contexto do Website Administrativo

## 1. Objetivo deste documento

Este documento consolida o contexto tecnico do website administrativo do projeto Checking.

Ele serve para:

- onboarding de desenvolvimento do painel web;
- manutencao do frontend administrativo em HTML, CSS e JavaScript puro;
- entendimento dos contratos entre a interface, a API FastAPI e o banco;
- depuracao de login, sessao, atualizacao em tempo real e operacoes de cadastro;
- reduzir retrabalho ao modificar abas, modais, autenticacao ou fluxos operacionais do admin.

## 2. Visao geral do website

O website administrativo nao e um projeto separado do backend. Ele e uma SPA estatica simples, servida pelo proprio FastAPI.

Caracteristicas principais:

- a interface e entregue em `/`;
- a URL legada `/admin` apenas redireciona para `/`;
- os arquivos do painel ficam em `sistema/app/static/admin`;
- nao existe build step, bundler, framework JS ou pipeline propria de frontend;
- toda a comunicacao com o backend ocorre no mesmo dominio, usando `fetch()` e `EventSource`.

Em outras palavras: API e painel administrativo sobem juntos, fazem parte do mesmo deploy e compartilham o mesmo repositorio principal.

## 3. Arquivos centrais do website administrativo

### 3.1 Frontend

- `sistema/app/static/admin/index.html`: estrutura da SPA, abas, modais e shell de autenticacao;
- `sistema/app/static/admin/app.js`: estado em memoria, chamadas HTTP, SSE, renderizacao das tabelas e eventos da interface;
- `sistema/app/static/admin/styles.css`: layout, responsividade, modais, tabelas, estados visuais e identidade do painel.

### 3.2 Backend que sustenta o website

- `sistema/app/main.py`: monta `SessionMiddleware`, registra routers e serve os arquivos estaticos;
- `sistema/app/routers/admin.py`: contratos HTTP do admin, CRUD, autenticacao, SSE e arquivos de eventos;
- `sistema/app/services/admin_auth.py`: sessao admin, seed do admin bootstrap, hash e verificacao de senha;
- `sistema/app/services/admin_updates.py`: broker de atualizacao em tempo real usado pelo SSE;
- `sistema/app/core/config.py`: configuracoes de sessao e credenciais bootstrap.

## 4. Como o website e servido

O backend monta o painel assim:

- `app.mount("/", StaticFiles(directory=static_dir / "admin", html=True), name="admin")`;
- `app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")` para favicon, logo e imagens compartilhadas;
- `/admin` e `/admin/{path}` redirecionam para a raiz por compatibilidade.

Consequencias praticas:

- qualquer alteracao no painel admin vai junto com o deploy da API;
- nao existe hospedagem separada para o frontend administrativo;
- o painel depende diretamente da disponibilidade da API para carregar estado, autenticar e atualizar dados.

## 5. Estrutura visual e shells da pagina

O `index.html` tem dois estados principais de interface:

### 5.1 `authShell`

E a tela inicial de autenticacao administrativa.

Elementos principais:

- campo `Chave` com 4 caracteres;
- campo `Senha`;
- botao `Entrar`;
- botao `Solicitar Admin`;
- botao `Recadastrar Senha`;
- area `authStatus` para feedback de erro ou sucesso.

### 5.2 `adminShell`

So fica visivel quando existe sessao valida.

Elementos principais:

- barra superior com marca `Checking`;
- `sessionBar` com nome completo e chave do admin autenticado;
- botao `Sair`;
- navegacao por abas;
- `statusLine` para mensagens operacionais do painel.

## 6. Abas e modais existentes

### 6.1 Abas atuais

O painel atualmente exibe 4 abas:

- `Check-In`
- `Check-Out`
- `Cadastro`
- `Eventos`

Observacao importante:

- a API ainda possui a rota `GET /api/admin/inactive`, mas a interface atual nao possui mais uma aba dedicada de `Inativos`.
- a documentacao antiga citava 5 abas, porem a implementacao atual visivel no `index.html` tem apenas 4.

### 6.2 Modais atuais

- `requestAdminModal`: solicitacao de acesso administrativo;
- `eventDetailsModal`: exibicao do campo `details` de um evento;
- `eventArchivesModal`: listagem, filtro, paginacao, download e exclusao dos CSVs arquivados.

## 7. Fluxo de bootstrap do frontend

O bootstrap do website acontece no `app.js` por meio da funcao `bootstrap()`.

Sequencia real:

1. `bindActions()` registra todos os listeners da pagina.
2. `bootstrapAdmin()` chama `GET /api/admin/auth/session`.
3. Se nao houver sessao valida, o painel exibe `authShell`.
4. Se houver sessao valida:
   - exibe `adminShell`;
   - mostra o nome do administrador logado no topo;
   - inicia polling de fallback;
   - inicia SSE em `/api/admin/stream`;
   - carrega todas as tabelas do painel.

O frontend nao persiste estado funcional em `localStorage`. O estado principal vive em memoria no navegador e e reconstruido a cada carregamento de pagina.

## 8. Modelo de autenticacao do website

### 8.1 Estrategia atual

O website usa autenticacao por sessao cookie, assinada pelo `SessionMiddleware` do Starlette.

Parametros atualmente configurados:

- `secret_key = settings.admin_session_secret`
- `max_age = settings.admin_session_max_age_seconds`
- `same_site = "lax"`
- `https_only = False`

Valor padrao atual relevante:

- `admin_session_max_age_seconds = 28800` (8 horas).

### 8.2 Como a sessao funciona

- no login bem-sucedido, o backend grava `request.session["admin_user_id"] = admin.id`;
- as rotas administrativas usam `require_admin_session()`;
- o stream SSE usa `require_admin_stream_session()`;
- o frontend sempre envia `credentials: "same-origin"`;
- se o admin for removido ou entrar em estado de recadastro de senha pendente, a sessao deixa de ser valida;
- respostas `401` fazem o frontend voltar para a tela de login.

### 8.3 Entidades de autenticacao

O website administrativo usa tabelas separadas do cadastro operacional:

- `admin_users`: administradores ativos ou aguardando definicao de nova senha;
- `admin_access_requests`: solicitacoes pendentes de aprovacao.

A tabela `users` continua reservada aos funcionarios do sistema, nao aos administradores.

### 8.4 Admin bootstrap

No startup da aplicacao, o backend garante um admin bootstrap idempotente com valores vindos de ambiente:

- `BOOTSTRAP_ADMIN_KEY`
- `BOOTSTRAP_ADMIN_NAME`
- `BOOTSTRAP_ADMIN_PASSWORD`

Defaults atuais no codigo:

- chave: `HR70`
- nome: `Tamer Salmem`
- senha: `eAcacdLe2`

### 8.5 Hash de senha

O backend usa PBKDF2-HMAC-SHA256 com 200000 iteracoes e salt aleatorio por senha.

Formato persistido:

- `pbkdf2_sha256$iteracoes$salt_hex$digest_hex`

## 9. Fluxos de autenticacao expostos no website

### 9.1 Login

Endpoint:

- `POST /api/admin/auth/login`

Regras:

- `chave` deve ter 4 caracteres alfanumericos;
- `senha` deve ter entre 3 e 20 caracteres;
- logins invalidos retornam `401`;
- admins com `requires_password_reset = true` recebem bloqueio `403`;
- o sucesso cria a sessao e libera o painel.

### 9.2 Logout

Endpoint:

- `POST /api/admin/auth/logout`

Comportamento:

- limpa a sessao;
- registra auditoria de logout quando havia admin autenticado;
- o frontend volta para a tela de autenticacao.

### 9.3 Verificacao de sessao

Endpoint:

- `GET /api/admin/auth/session`

Uso no frontend:

- e a primeira chamada feita ao carregar a pagina;
- define se o usuario ve a tela de login ou o painel carregado.

### 9.4 Solicitar acesso administrativo

Endpoint:

- `POST /api/admin/auth/request-access`

Fluxo:

- o usuario informa `chave`, `nome_completo` e `senha` no modal;
- o backend cria um registro em `admin_access_requests`;
- outro administrador precisa aprovar ou rejeitar na area `Cadastro`.

### 9.5 Solicitar recadastro de senha

Endpoint:

- `POST /api/admin/auth/request-password-reset`

Fluxo:

- o proprio admin informa apenas a chave na tela inicial;
- o backend apaga a senha atual e marca `requires_password_reset = true`;
- outro administrador precisa cadastrar uma nova senha na tabela de administradores.

## 10. Detalhamento por aba

### 10.1 Aba `Check-In`

Fonte de dados:

- `GET /api/admin/checkin`

O que exibe:

- horario do ultimo evento consolidado;
- nome;
- chave;
- projeto;
- local formatado para legenda amigavel;
- acao de remocao quando o usuario esta antigo.

Observacoes tecnicas:

- a lista e montada a partir de `resolve_latest_user_activity()`, nao apenas dos campos crus de `users`;
- o titulo mostra `Usuarios em Check-In (quantidade_visivel/quantidade_total_cadastrada)`;
- se o ultimo evento estiver com mais de 1 dia, a linha recebe destaque visual em vermelho e o botao `Remover` fica disponivel.

### 10.2 Aba `Check-Out`

Fonte de dados:

- `GET /api/admin/checkout`

Comportamento:

- segue a mesma logica de renderizacao da aba de check-in;
- tambem mostra remocao apenas para usuarios considerados antigos;
- o contador do titulo usa o total de usuarios cadastrados no sistema.

### 10.3 Aba `Cadastro`

Essa aba concentra 3 areas diferentes.

#### a) Cadastro de Pendencias

Fonte de dados:

- `GET /api/admin/pending`

Acoes:

- `Editar`: habilita campos de nome, chave e projeto;
- `Salvar`: envia `POST /api/admin/users` com `rfid`, `nome`, `chave`, `projeto`;
- `Remover`: envia `DELETE /api/admin/pending/{id}`.

Detalhes importantes:

- a pendencia nasce de RFID desconhecido detectado pela ESP32;
- ao salvar, a pendencia correspondente e removida;
- se ja existir um usuario com a mesma `chave` e `rfid = NULL`, o backend pode vincular o RFID ao cadastro existente em vez de criar outro usuario.

#### b) Administradores

Fonte de dados:

- `GET /api/admin/administrators`

A tabela mistura:

- administradores ativos;
- solicitacoes pendentes;
- administradores com recadastro de senha pendente.

Acoes possiveis por linha:

- `Aprovar`: `POST /api/admin/administrators/requests/{request_id}/approve`;
- `Rejeitar`: `POST /api/admin/administrators/requests/{request_id}/reject`;
- `Revogar`: `POST /api/admin/administrators/{admin_id}/revoke`;
- `Cadastrar Senha`: abre editor inline e envia `POST /api/admin/administrators/{admin_id}/set-password`.

Regras relevantes:

- um admin nao pode revogar o proprio acesso;
- o sistema nao permite remover o ultimo admin ativo;
- a nova senha deve ter entre 3 e 20 caracteres.

#### c) Usuarios Cadastrados

Fonte de dados:

- `GET /api/admin/users`

Acoes:

- `Editar`: habilita campos inline;
- `Salvar`: envia `POST /api/admin/users` com `user_id`;
- `Remover`: envia `DELETE /api/admin/users/{id}`.

Regras relevantes do backend:

- `chave` e unica;
- o usuario pode existir sem RFID, principalmente quando veio primeiro do app Android;
- nao e permitido sobrescrever um RFID diferente em um usuario que ja possui RFID vinculado;
- ao remover usuario, o backend tambem remove `UserSyncEvent` relacionados e a pendencia com o mesmo RFID, se existir.

### 10.4 Aba `Eventos`

Fonte de dados:

- `GET /api/admin/events`

O que exibe:

- ID;
- horario;
- origem;
- acao;
- status;
- dispositivo;
- local;
- RFID;
- projeto;
- status HTTP;
- rota;
- tentativas;
- mensagem;
- botao `Detalhes`.

Comportamento:

- a API retorna os 200 eventos mais recentes;
- eventos com `action = event_archive` ficam de fora dessa listagem principal;
- o campo `details` abre em modal para leitura completa;
- a tabela usa largura fixa grande e scroll horizontal.

## 11. Arquivamento de eventos no website

O botao `Limpar` da aba `Eventos` nao apenas apaga a grade atual. Ele primeiro tenta arquivar os eventos correntes em CSV.

Endpoint principal:

- `POST /api/admin/events/archive`

Fluxo:

1. o frontend pede confirmacao ao usuario;
2. o backend gera um CSV com os eventos atuais, excluindo linhas com `action = event_archive`;
3. se havia eventos correntes, eles sao removidos da tabela `check_events`;
4. o frontend abre o modal `Logs Salvos`;
5. a lista principal de eventos e recarregada.

Operacoes suportadas no modal de arquivos:

- listar arquivos: `GET /api/admin/events/archives?q=&page=&page_size=`;
- baixar um CSV: `GET /api/admin/events/archives/{file_name}`;
- baixar tudo zipado: `GET /api/admin/events/archives/download-all`;
- excluir um arquivo: `DELETE /api/admin/events/archives/{file_name}`.

Detalhes de UX implementados:

- filtro por texto sobre o periodo do log;
- paginacao com tamanho padrao de 8 itens por pagina;
- resumo de quantidade total;
- resumo de armazenamento total consumido;
- desabilitacao do botao de download geral quando nao existem arquivos.

## 12. Atualizacao em tempo real e fallback

### 12.1 SSE

O website abre um `EventSource("/api/admin/stream")` quando o admin esta autenticado.

Comportamento:

- conexao autenticada por cookie de sessao;
- ao abrir, o frontend marca `realtimeConnected = true`;
- a cada mensagem recebida, o frontend faz debounce e recarrega todas as tabelas;
- o backend envia `keep-alive` a cada 15 segundos quando necessario.

### 12.2 Broker de atualizacao

O backend publica mudancas por meio do `admin_updates_broker`.

Razoes de notificacao usadas no projeto incluem:

- `checkin`
- `checkout`
- `pending`
- `register`
- `admin`
- `event`

### 12.3 Polling de fallback

Mesmo com SSE, o frontend tambem inicia polling por seguranca.

Regras do polling:

- intervalo padrao de 5 segundos;
- nao roda quando a aba do navegador esta oculta;
- nao roda quando o SSE esta conectado;
- nao roda sem autenticacao.

### 12.4 Debounce de refresh

Mensagens de SSE sao agrupadas com debounce de 250 ms para evitar excesso de recarga de tabelas.

### 12.5 Protecao contra perda de edicao

Quando existe edicao pendente em `Cadastro`, o frontend evita recarregar automaticamente as listas de pendencias e usuarios cadastrados. Isso impede perder alteracoes locais nao salvas.

## 13. Formatacoes e regras de interface relevantes

### 13.1 Horarios

O frontend formata datas com `Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Singapore" })`.

Consequencia:

- a exibicao segue o timezone operacional do sistema;
- o formato visual fica proximo de `YYYY-MM-DD HH:mm:ss`.

### 13.2 Locais conhecidos

O frontend traduz alguns codigos de local para labels amigaveis:

- `main` -> `Escritorio Principal`
- `co80` -> `Escritorio Avancado P80`
- `un80` -> `A bordo da P80`
- `co83` -> `Escritorio Avancado P83`
- `un83` -> `A bordo da P83`

Valores nao mapeados sao exibidos como vieram da API.

### 13.3 Acoes de evento

Algumas acoes sao traduzidas para labels mais legiveis:

- `checkin` -> `Check-In`
- `checkout` -> `Check-Out`
- `register` -> `Cadastro`
- `admin_request` -> `Solicitacao Admin`
- `admin_access` -> `Admin`
- `password` -> `Senha`
- `event_archive` -> `Arquivo Eventos`

### 13.4 Layout responsivo

O CSS aplica responsividade por meio de:

- wrappers com scroll horizontal para tabelas largas;
- `data-label` nas celulas, preenchido em runtime pelo JS;
- modais centralizados e adaptativos;
- destaque visual para linhas antigas;
- pagina com fundo em gradiente e watermark da logomarca compartilhada em `/assets/img/petrobras_logotype.png`.

## 14. Tratamento de erros no frontend

O frontend centraliza os erros em `fetchJson()` e `parseErrorResponse()`.

Comportamentos importantes:

- `401` dispara retorno para a tela de login;
- erros de validacao vindos da API sao compactados em uma mensagem unica quando possivel;
- downloads via `fetchBlob()` tambem tratam `401` e mensagens JSON de erro;
- remocoes e salvamentos usam mensagens na `statusLine` para feedback do operador.

Validacoes locais antes de chamar a API:

- `chave`: 4 caracteres alfanumericos;
- `senha`: entre 3 e 20 caracteres;
- `nome`: minimo de 3 caracteres em cadastro admin;
- IDs de usuario precisam ser inteiros antes de acionar remocao.

## 15. Regras de negocio do website que dependem do backend

### 15.1 Lista de presenca nao depende so de `users.checkin`

As abas `Check-In` e `Check-Out` sao derivadas do ultimo evento consolidado por usuario, usando `resolve_latest_user_activity()`.

Isso importa porque:

- corrige cenarios em que o historico canonico e mais confiavel que um campo cru na tabela `users`;
- permite refletir eventos vindos tanto da ESP32 quanto do app Android.

### 15.2 Cadastro pode vincular RFID a usuario ja existente

Quando o app Android cria antes um usuario sem RFID, o painel pode reaproveitar esse cadastro ao salvar uma pendencia com a mesma `chave`.

### 15.3 Remocao visual de usuarios antigos

O botao `Remover` em `Check-In` e `Check-Out` nao aparece para todos. Ele so e exibido quando o ultimo evento tem pelo menos 1 dia de idade.

### 15.4 Limpeza de eventos gera auditoria propria

O arquivamento de eventos registra novos eventos administrativos de `event_archive`, mas esses registros nao voltam para a grade principal de eventos correntes.

## 16. Pontos de manutencao rapida

Para mudancas futuras, os pontos de entrada mais importantes sao:

- estrutura da interface: `sistema/app/static/admin/index.html`;
- logica do painel: `sistema/app/static/admin/app.js`;
- visual e responsividade: `sistema/app/static/admin/styles.css`;
- contratos HTTP e regras do admin: `sistema/app/routers/admin.py`;
- sessao, seed e senha: `sistema/app/services/admin_auth.py`;
- configuracao de sessao e bootstrap: `sistema/app/core/config.py` e `sistema/app/main.py`.

## 17. Checklist mental para depuracao

### 17.1 Problemas de login

Normalmente passam por:

- tabela `admin_users`;
- `ADMIN_SESSION_SECRET` inconsistente;
- admin com `requires_password_reset = true`;
- cookie de sessao nao persistindo no dominio esperado.

### 17.2 Painel nao atualiza em tempo real

Verificar:

- endpoint `/api/admin/stream`;
- se a sessao ainda esta valida;
- se `notify_admin_data_changed()` esta sendo chamado no backend que alterou os dados;
- se o frontend caiu para polling de fallback.

### 17.3 Erros de cadastro

Os principais pontos sao:

- conflito de `chave` unica;
- tentativa de vincular RFID diferente a usuario ja vinculado;
- tentativa de criar usuario novo sem RFID;
- pendencia nao encontrada ou ja removida.

### 17.4 Erros com arquivos de eventos

Os principais pontos sao:

- inexistencia de arquivos arquivados para download total;
- nome de arquivo inexistente em download unitario;
- exclusao concorrente de arquivo ja removido.

## 18. Estado atual e observacoes de arquitetura

O website administrativo atual e pequeno, direto e funcional. Ele privilegia simplicidade operacional:

- frontend sem framework;
- backend unico servindo API e SPA;
- autenticacao por sessao em cookie;
- atualizacao em tempo real por SSE com fallback em polling;
- CRUD e auditoria centralizados no router admin.

Ao mesmo tempo, existem alguns pontos de atencao para quem for evoluir o sistema:

- a documentacao mais antiga ainda pode citar a aba `Inativos`, hoje ausente na UI;
- o frontend concentra muita logica em um unico `app.js`, o que facilita alteracoes pequenas, mas tende a crescer rapido;
- o `https_only=False` da sessao e aceitavel em ambiente local, mas merece revisao cuidadosa em producao atras de HTTPS;
- como a SPA e servida pela API, qualquer indisponibilidade do backend derruba tambem o admin web.

## 19. Resumo objetivo

Se for preciso explicar o website administrativo em uma frase tecnica:

> O admin web do Checking e uma SPA estatica servida pelo FastAPI em `/`, autenticada por sessao cookie, com tabelas de operacao e cadastro alimentadas por `/api/admin/*`, atualizacao em tempo real via SSE e fallback em polling, sem framework de frontend nem deploy separado.