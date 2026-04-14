# Contexto detalhado do website administrativo (Checking)

## 1. Objetivo deste contexto

Este documento consolida o estado atual (codigo vigente) do website do administrador do sistema Checking.

Ele foi preparado para acelerar:

- onboarding tecnico;
- manutencao do frontend admin e das rotas de suporte;
- depuracao de login/sessao/realtime;
- evolucao de UX sem quebrar contratos da API.

## 2. Escopo funcional do website admin

O website administrativo permite:

- autenticar administrador por chave + senha (sessao cookie);
- acompanhar usuarios em check-in e check-out;
- identificar e tratar usuarios inativos (separados visualmente);
- cadastrar RFIDs pendentes e editar/remover usuarios cadastrados;
- aprovar/rejeitar solicitacoes de novos administradores;
- revogar acesso de administradores e cadastrar nova senha quando houver reset pendente;
- consultar eventos operacionais recentes;
- arquivar eventos atuais em CSV, listar arquivos, baixar (individual/todos) e excluir arquivos.

## 3. Arquitetura e entrega do frontend

### 3.1 Onde o frontend mora

O frontend admin nao e um projeto separado. Ele e estatico e servido pelo proprio FastAPI.

Arquivos centrais:

- `sistema/app/static/admin/index.html`
- `sistema/app/static/admin/app.js`
- `sistema/app/static/admin/styles.css`

### 3.2 Como e servido

Em `sistema/app/main.py`:

- `/` monta `StaticFiles(..., html=True)` para `static/admin`;
- `/admin` e `/admin/{path}` redirecionam para raiz por compatibilidade;
- `/assets` expoe os assets compartilhados do repositorio.

Implicacao: deploy da API e do website admin acontece junto.

### 3.3 Stack

- HTML + CSS + JavaScript puro;
- sem framework frontend;
- sem bundler/build pipeline de frontend;
- chamadas HTTP com `fetch`;
- atualizacao em tempo real com SSE (`EventSource`).

## 4. Estrutura de interface (index.html)

## 4.1 Shells principais

- `authShell`: tela de acesso administrativo.
- `adminShell`: painel principal exibido somente com sessao valida.

## 4.2 Tela de autenticacao

Componentes:

- `loginChave` (4 chars);
- `loginSenha` (3-20 chars);
- botao `Entrar`;
- botao `Solicitar Admin`;
- botao `Recadastrar Senha`;
- area `authStatus` para mensagens.

## 4.3 Barra de sessao

Com sessao valida, a barra superior mostra:

- nome completo + chave do admin (`sessionUserLabel`);
- botao `Sair`.

## 4.4 Abas existentes

Abas renderizadas:

- Check-In
- Check-Out
- Cadastro
- Eventos

Observacoes:

- as secoes de inatividade ficam dentro das abas de presenca (check-in e check-out), nao como aba separada;
- a aba Check-Out possui uma secao adicional chamada `Usuarios sem Check-Out`, renderizada abaixo da tabela principal de check-out.

## 4.5 Modais

- `requestAdminModal`: solicitar acesso admin;
- `eventDetailsModal`: abrir detalhes completos de evento;
- `eventArchivesModal`: gerenciar logs CSV arquivados.

## 5. Estado e bootstrap do frontend (app.js)

## 5.1 Estado em memoria

Variaveis globais relevantes:

- `activeTab`;
- timers de auto refresh e debounce de realtime;
- status da conexao realtime;
- status de autenticacao;
- estado da paginacao/filtro de arquivos de evento;
- total de usuarios cadastrados (usado nos titulos de check-in/check-out).

Nao ha persistencia funcional em localStorage para auth/estado do painel.

## 5.2 Sequencia de bootstrap

1. `bindActions()` registra listeners.
2. `bootstrapAdmin()` chama `GET /api/admin/auth/session`.
3. Sem sessao: mostra `authShell`.
4. Com sessao:
   - mostra `adminShell`;
   - inicia fallback de auto refresh (5s);
   - inicia SSE em `/api/admin/stream`;
   - carrega tabelas com `refreshAllTables()`.

## 5.3 Carregamento de dados

`refreshAllTables()` busca em paralelo:

- check-in;
- check-out;
- eventos;
- administradores;
- pendencias e usuarios (quando nao ha edicao inline ativa).

Esse cuidado evita sobrescrever campos durante edicao pelo usuario.

## 6. Modelo de autenticacao do admin

## 6.1 Estrategia atual

Sessao por cookie assinada via `SessionMiddleware` (Starlette):

- `secret_key = settings.admin_session_secret`
- `max_age = settings.admin_session_max_age_seconds`
- `same_site = "lax"`
- `https_only = False` (estado atual de codigo)

Login bem-sucedido grava `request.session["admin_user_id"]`.

## 6.2 Guardas de autenticacao

No backend (`services/admin_auth.py`):

- `require_admin_session` para rotas protegidas;
- `require_admin_stream_session` para SSE;
- sessoes invalidas/expiradas retornam `401`.

No frontend:

- todas as requisicoes usam `credentials: "same-origin"`;
- ao receber `401`, o frontend volta ao `authShell` e informa expiracao/invalidade da sessao.

## 6.3 Entidades de autenticacao

- `admin_users`: administradores aprovados (ou com reset de senha pendente);
- `admin_access_requests`: solicitacoes pendentes.

Nao reutiliza `users` operacionais para login admin.

## 6.4 Seed bootstrap

No startup da API, `seed_default_admin()` garante idempotentemente o admin bootstrap baseado no `.env`:

- `BOOTSTRAP_ADMIN_KEY`
- `BOOTSTRAP_ADMIN_NAME`
- `BOOTSTRAP_ADMIN_PASSWORD`

## 6.5 Hash de senha

PBKDF2-HMAC-SHA256, formato:

`pbkdf2_sha256$iteracoes$salt_hex$digest_hex`

## 7. Contratos HTTP usados pelo website admin

Prefixo: `/api/admin`

## 7.1 Sessao e autenticacao

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/session`
- `POST /auth/request-access`
- `POST /auth/request-password-reset`

Regras de entrada principais:

- chave admin: 4 alfanumericos;
- senha: 3 a 20 caracteres;
- login bloqueado com `403` se admin estiver com `requires_password_reset=true`;
- erros de credencial retornam `401`.

## 7.2 Realtime

- `GET /stream` (SSE)

Comportamento:

- envia evento inicial `connected`;
- keep-alive a cada timeout;
- payload principal contem `reason` e `emitted_at`;
- broker com fila por assinante (`maxsize=20`) e descarte do item mais antigo quando lota.

## 7.3 Listagens para abas

- `GET /checkin`
- `GET /checkout`
- `GET /pending`
- `GET /users`
- `GET /administrators`
- `GET /events`

Observacoes:

- `checkin/checkout` sao construidos por atividade mais recente (servico `resolve_latest_user_activity`), nao apenas por campos brutos;
- a separacao visual de inatividade usa virada de dia em Singapura (`Asia/Singapore`): se o ultimo evento nao pertence ao dia atual em Singapura, a linha e tratada como inativa;
- `events` traz no maximo 200 e exclui `action=event_archive` da grade principal.

## 7.4 Acoes de cadastro e administracao

- `POST /users` (cria/atualiza usuario)
- `DELETE /users/{user_id}`
- `DELETE /pending/{pending_id}`
- `POST /administrators/requests/{request_id}/approve`
- `POST /administrators/requests/{request_id}/reject`
- `POST /administrators/{admin_id}/revoke`
- `POST /administrators/{admin_id}/set-password`

Regras de negocio relevantes:

- `chave` de usuario e unica;
- usuario pode existir sem RFID (ex.: originado no app Android);
- nao permite substituir RFID por outro se usuario ja tiver RFID diferente vinculado;
- ao remover usuario, remove tambem `UserSyncEvent` associados e pendencia do mesmo RFID (se existir);
- admin nao pode revogar o proprio acesso;
- nao permite remover o ultimo admin ativo;
- nova senha admin so pode ser cadastrada quando ha reset pendente.

## 7.5 Arquivos de eventos (CSV)

- `POST /events/archive`
- `GET /events/archives?q=&page=&page_size=`
- `GET /events/archives/{file_name}`
- `GET /events/archives/download-all`
- `DELETE /events/archives/{file_name}`

Fluxo do botao Limpar na aba Eventos:

1. confirma com o usuario;
2. arquiva eventos atuais em CSV (quando houver);
3. limpa tabela corrente `check_events`;
4. abre modal de logs salvos;
5. recarrega grade de eventos.

## 8. Comportamento por aba

## 8.1 Check-In

- titulos mostram `visiveis/total_cadastrados`;
- conversao de local para legenda amigavel (`main`, `co80`, `un80`, `co83`, `un83`);
- apos a meia-noite de Singapura, todos os usuarios cujo ultimo check-in foi no dia anterior passam para a tabela `Usuarios Inativos`;
- a inatividade nao espera 24 horas corridas; ela segue mudanca de data calendario em Singapura;
- linhas inativas ficam com destaque e acao `Remover`;
- secao inativa separada por tabela dentro da aba.

## 8.2 Check-Out

- a tabela principal `Usuarios em Check-Out` continua mostrando usuarios cujo ultimo evento consolidado e checkout;
- abaixo dela existe a tabela `Usuarios sem Check-Out`;
- essa tabela recebe usuarios cujo ultimo evento consolidado e check-in e que cruzaram a meia-noite de Singapura sem registrar checkout;
- as colunas sao: `Horario`, `Nome`, `Chave`, `Projeto`, `Local`, `Acoes`.

## 8.3 Cadastro

Tres blocos:

1. Pendencias RFID
- editar campos nome/chave/projeto;
- salvar com `POST /api/admin/users`;
- remover pendencia com `DELETE /api/admin/pending/{id}`.

2. Administradores
- lista admins ativos + pedidos pendentes + reset pendente;
- acoes dinamicas por permissao de linha (`can_*`).

3. Usuarios cadastrados
- edicao inline de nome/chave/projeto;
- salvamento via `POST /api/admin/users` com `user_id`;
- remocao via `DELETE /api/admin/users/{id}`.

## 8.4 Eventos

- tabela detalhada com colunas operacionais e botao de detalhes;
- campo `details` passa por limpeza de ruido (`final_url=`) antes de mostrar modal;
- acao `Limpar` executa arquivamento e limpeza logica, nao apenas limpeza visual.

## 9. Observabilidade, auditoria e consistencia

## 9.1 Auditoria

Acoes administrativas relevantes geram registros em `check_events` (`source=admin`), incluindo:

- login/logout;
- aprovacoes/rejeicoes/revogacoes admin;
- solicitacao e cadastro de senha;
- cadastro/remocao de usuarios;
- operacoes de arquivos de eventos.

## 9.2 Atualizacao em tempo real + fallback

- Realtime primario via SSE.
- Fallback por polling a cada 5s quando realtime estiver desconectado ou indisponivel.
- Debounce de 250ms evita tempestade de refresh em sequencias rapidas de eventos.

## 10. Dependencias de dados no backend

Tabelas mais usadas pelo website admin:

- `users`
- `pending_registrations`
- `check_events`
- `user_sync_events`
- `admin_users`
- `admin_access_requests`

## 11. Riscos e pontos de atencao para evolucao

- `https_only=False` em sessao: para producao publica, avaliar migracao para `True` com TLS garantido.
- Frontend sem framework e sem camada de estado estruturada: mudancas grandes exigem disciplina para evitar regressao em listeners/event delegation.
- Grade de eventos limita em 200 itens por consulta: suficiente para operacao diaria, mas nao substitui trilha historica longa (usar arquivos arquivados para historico).
- SSE depende de sessao valida e conectividade estavel; manter fallback de polling e essencial.

## 12. Checklist rapido para manutencao

Ao alterar website admin, validar:

1. Login, logout e expurgo de sessao expirada (`401`).
2. Renderizacao correta das abas e modais.
3. Regra de virada de dia em Singapura para `Usuarios Inativos` na aba Check-In.
4. Populacao da tabela `Usuarios sem Check-Out` na aba Check-Out.
5. Bloqueio de refresh durante edicao inline.
6. Fluxos de aprovacao/rejeicao/revogacao admin.
7. Fluxo de reset e cadastro de senha admin.
8. Fluxo de arquivamento/download/exclusao de CSV de eventos.
9. Realtime (SSE) + fallback polling.
10. Responsividade basica das tabelas (labels `data-label` aplicados em mobile).
