# Contexto da API e do Website Administrativo

## 1. Objetivo deste documento

Este documento consolida o contexto tecnico da API FastAPI e do website administrativo do projeto Checking.

Ele serve para:

- onboarding de novos desenvolvedores;
- manutencao do backend e do painel admin;
- entendimento rapido dos contratos entre frontend, backend, app Android e ESP32;
- depuracao de problemas operacionais e de autenticacao.

## 2. Visao geral da arquitetura

O projeto possui um unico backend FastAPI que acumula tres responsabilidades principais:

1. expor a API operacional usada pela ESP32 e pelo aplicativo Android;
2. servir o website administrativo estatico;
3. coordenar persistencia, auditoria, fila de envio ao Microsoft Forms e atualizacao em tempo real do painel admin.

Na pratica, a API e o site administrativo nao sao sistemas separados. Ambos rodam no mesmo servico Python.

Arquivos-chave:

- `sistema/app/main.py`: bootstrap da aplicacao, middlewares, routers e montagem dos arquivos estaticos;
- `sistema/app/routers/device.py`: endpoints consumidos pela ESP32;
- `sistema/app/routers/mobile.py`: endpoints consumidos pelo app Android;
- `sistema/app/routers/admin.py`: autenticacao admin, listagens, CRUD e logs;
- `sistema/app/static/admin/index.html`: casca HTML da SPA administrativa;
- `sistema/app/static/admin/app.js`: logica do frontend admin em JavaScript puro;
- `sistema/app/static/admin/styles.css`: estilos do painel.

## 3. Ciclo de vida da aplicacao

No startup da aplicacao, o backend executa estes passos:

1. garante a existencia do diretorio de arquivos CSV arquivados de eventos;
2. cria as tabelas automaticamente apenas em ambiente `development`;
3. faz seed idempotente do administrador bootstrap;
4. inicia o worker da fila do Microsoft Forms quando `FORMS_QUEUE_ENABLED=true`.

No shutdown, o worker da fila e encerrado.

Esse comportamento esta centralizado no lifespan definido em `sistema/app/main.py`.

## 4. Configuracao central

As configuracoes ficam em `sistema/app/core/config.py`, carregadas por `pydantic-settings` a partir do arquivo `.env`.

Configuracoes mais relevantes para API e admin:

- `DATABASE_URL`: banco local ou de producao;
- `DEVICE_SHARED_KEY`: segredo compartilhado da ESP32;
- `MOBILE_APP_SHARED_KEY`: segredo compartilhado do app Android;
- `ADMIN_SESSION_SECRET`: segredo usado para assinar a sessao administrativa;
- `ADMIN_SESSION_MAX_AGE_SECONDS`: duracao da sessao admin;
- `BOOTSTRAP_ADMIN_KEY`, `BOOTSTRAP_ADMIN_NAME`, `BOOTSTRAP_ADMIN_PASSWORD`: credenciais seed do primeiro administrador;
- `FORMS_QUEUE_ENABLED`: liga ou desliga o processamento assincrono da fila do Microsoft Forms;
- `EVENT_ARCHIVES_DIR`: diretorio onde os CSV de eventos arquivados sao armazenados.

Padroes atuais importantes:

- banco local padrao: SQLite em `./checking.db`;
- timezone operacional: `Asia/Singapore`;
- diretorio padrao de arquivos arquivados: `/app/data/event_archives`.

## 5. Estrutura de exposicao HTTP

### 5.1 API publica e sem sessao admin

Rotas publicas disponiveis sem autenticacao por sessao:

- `GET /api/health`: health check da aplicacao;
- `POST /api/device/heartbeat`: presenca da ESP32;
- `POST /api/scan`: eventos RFID de check-in e check-out;
- `GET /api/mobile/state`: consulta de estado consolidado do usuario pelo app Android;
- `POST /api/mobile/events/sync`: sincronizacao de eventos mobile com o backend.

Observacao: essas rotas publicas continuam protegidas por segredos especificos do dispositivo ou do app mobile quando aplicavel.

### 5.2 Website admin e area autenticada

O website administrativo e servido pelo proprio FastAPI:

- `/`: entrega a SPA administrativa;
- `/admin`: redireciona para `/` por compatibilidade legada;
- `/assets/*`: arquivos compartilhados montados a partir da pasta `assets`.

Rotas protegidas por sessao cookie ficam sob o prefixo `/api/admin`.

## 6. Modelo de autenticacao administrativa

### 6.1 Estrategia atual

O admin usa autenticacao por sessao baseada em cookie assinada por `SessionMiddleware` do Starlette.

Caracteristicas:

- o frontend nao envia `x-admin-key`;
- o backend guarda `admin_user_id` em `request.session` apos login bem-sucedido;
- as rotas admin dependem de `require_admin_session()`;
- o stream SSE tambem exige sessao valida via `require_admin_stream_session()`;
- o frontend usa `fetch(..., { credentials: "same-origin" })` em todas as chamadas autenticadas.

### 6.2 Tabelas de autenticacao admin

As entidades administrativas sao separadas do cadastro operacional de funcionarios:

- `admin_users`: administradores ativos ou com recadastro de senha pendente;
- `admin_access_requests`: solicitacoes pendentes para se tornar administrador.

Isso evita misturar identidade administrativa com a tabela operacional `users`.

### 6.3 Bootstrap admin

Ao subir a aplicacao, o backend garante um administrador bootstrap com base nas variaveis de ambiente.

Esse seed e idempotente:

- se a `chave` bootstrap ja existir em `admin_users`, nada novo e criado;
- se nao existir, o registro e criado com senha hash PBKDF2-SHA256.

### 6.4 Fluxos de autenticacao admin

Rotas de autenticacao:

- `POST /api/admin/auth/login`
- `POST /api/admin/auth/logout`
- `GET /api/admin/auth/session`
- `POST /api/admin/auth/request-access`
- `POST /api/admin/auth/request-password-reset`

Fluxos implementados:

1. Login normal:
   - valida `chave` e `senha`;
   - rejeita admin inexistente;
   - rejeita senha invalida;
   - bloqueia login se houver recadastro pendente de senha;
   - grava `admin_user_id` na sessao.

2. Solicitacao de acesso admin:
   - qualquer pessoa com `chave`, `nome_completo` e `senha` pode gerar pedido pendente;
   - o pedido fica em `admin_access_requests`;
   - outro administrador aprova ou rejeita pelo painel.

3. Recadastro de senha:
   - o proprio administrador informa a chave;
   - a senha atual e apagada;
   - `requires_password_reset` passa para `true`;
   - outro administrador deve cadastrar nova senha.

4. Sessao expirada:
   - o frontend trata `401` de forma centralizada;
   - o painel volta para a tela de login.

## 7. Modelo de dados relevante para a API e o admin

### 7.1 `users`

Representa o cadastro operacional e o estado atual de presenca do funcionario.

Campos relevantes:

- `id`: inteiro autoincremental;
- `rfid`: unico, pode ser `NULL`;
- `chave`: unica, 4 caracteres alfanumericos;
- `nome`;
- `projeto`: hoje limitado a `P80`, `P82`, `P83` nos schemas;
- `local`: ultimo local conhecido;
- `checkin`: `true`, `false` ou `NULL`;
- `time`: timestamp do ultimo evento aplicado ao estado atual;
- `last_active_at` e `inactivity_days`: base para o controle de inatividade no backend.

Ponto importante: `rfid` pode ser `NULL` para suportar usuarios criados primeiro pelo app Android e vinculados ao cartao somente depois.

### 7.2 `pending_registrations`

Armazena RFIDs ainda nao reconhecidos pelo sistema.

Campos:

- `id`
- `rfid` unico
- `first_seen_at`
- `last_seen_at`
- `attempts`

Essa tabela alimenta a area de cadastro do admin.

### 7.3 `check_events`

E a trilha de auditoria operacional do sistema.

Registra:

- recebimento de scan;
- bloqueios e duplicidades;
- operacoes administrativas;
- login/logout e gestao de admins;
- sincronizacao mobile;
- criacao/download/exclusao de arquivos de eventos.

Possui `idempotency_key` unica para evitar duplicidade de alguns fluxos.

### 7.4 `forms_submissions`

Fila persistida para envio assincrono ao Microsoft Forms.

Ela desacopla a resposta ao ESP32 do processamento do Forms.

### 7.5 `user_sync_events`

Historico canonico dos eventos aplicados ao usuario, vindos de RFID ou Android.

Restricao importante:

- unicidade por `source` + `source_request_id`.

Isso permite idempotencia do canal mobile e rastreabilidade entre fontes.

### 7.6 `admin_users` e `admin_access_requests`

Suportam governanca do acesso administrativo sem reaproveitar a tabela operacional de usuarios.

## 8. Contratos da API por dominio

### 8.1 Health

`GET /api/health`

Retorna estado simples da aplicacao para monitoramento e para a pipeline de deploy.

### 8.2 Canal do dispositivo ESP32

#### `POST /api/device/heartbeat`

Payload:

```json
{
  "device_id": "ESP32-S3-01",
  "shared_key": "..."
}
```

Comportamento:

- valida `DEVICE_SHARED_KEY`;
- grava sinal de vida em `device_heartbeats`;
- em caso de chave invalida, registra evento de falha e devolve resposta simples ao dispositivo.

#### `POST /api/scan`

Payload esperado:

```json
{
  "rfid": "A1B2C3D4",
  "local": "main",
  "action": "checkin",
  "device_id": "ESP32-S3-01",
  "request_id": "ESP32-S3-01-checkin-123456-A1B2C3D4",
  "shared_key": "..."
}
```

Resposta tipada (`ScanResponse`):

- `outcome`: `submitted`, `pending_registration`, `invalid_key`, `duplicate`, `failed`, `local_updated`;
- `led`: instrucoes de padrao visual para a ESP32;
- `message`: mensagem operacional.

Ordem de processamento:

1. valida a `shared_key` do dispositivo;
2. verifica idempotencia por `request_id` em `check_events`;
3. registra recebimento do scan em auditoria;
4. tenta localizar usuario por RFID;
5. se o RFID for desconhecido, cria ou atualiza pendencia;
6. se o usuario ja estiver em check-in e ocorrer novo `checkin`, atualiza apenas o `local` e o timestamp, sem enfileirar Forms;
7. se ocorrer `checkout` sem check-in ativo, bloqueia a operacao;
8. para operacao valida, atualiza o estado atual do usuario;
9. enfileira envio ao Forms em `forms_submissions`;
10. grava `user_sync_events` como fonte `rfid`;
11. publica atualizacao para o painel admin.

Regras de negocio importantes:

- RFID desconhecido nao cria usuario automaticamente; cria pendencia;
- `checkin` repetido com usuario ja ativo vira apenas atualizacao de local;
- `checkout` sem `checkin` ativo retorna erro de negocio;
- a resposta ao dispositivo sai antes da conclusao do Forms.

### 8.3 Canal mobile Android

O canal mobile usa header `x-mobile-shared-key`.

#### `GET /api/mobile/state?chave=...`

Retorna estado consolidado do usuario:

- se existe ou nao;
- nome e projeto;
- acao atual;
- horario do estado atual;
- ultimo check-in;
- ultimo check-out.

#### `POST /api/mobile/events/sync`

Payload:

```json
{
  "chave": "SRG1",
  "projeto": "P82",
  "action": "checkin",
  "event_time": "2026-04-06T08:00:00+08:00",
  "client_event_id": "android-1234567890"
}
```

Comportamento:

- exige `x-mobile-shared-key` valido;
- e idempotente por `client_event_id`;
- pode criar usuario placeholder se a `chave` ainda nao existir;
- normaliza o horario do evento;
- aplica o estado atual em `users`;
- grava `user_sync_events` com `source="android"`;
- publica atualizacao para o painel admin.

Diferenca importante em relacao ao canal RFID:

- o mobile nao passa pela fila do Microsoft Forms dentro desta API;
- ele sincroniza apenas o estado consolidado no backend apos o fluxo do app.

## 9. Rotas protegidas do admin

### 9.1 Sessao e autenticacao

- `POST /api/admin/auth/login`
- `POST /api/admin/auth/logout`
- `GET /api/admin/auth/session`
- `POST /api/admin/auth/request-access`
- `POST /api/admin/auth/request-password-reset`

### 9.2 Atualizacao em tempo real

- `GET /api/admin/stream`

Entrega Server-Sent Events com payload JSON contendo pelo menos:

- `reason`
- `emitted_at`

O broker interno usa filas por assinante e descarta o item mais antigo quando a fila lota.

Razoes publicadas com mais frequencia:

- `checkin`
- `checkout`
- `pending`
- `register`
- `admin`
- `event`

### 9.3 Gestao de administradores

- `GET /api/admin/administrators`
- `POST /api/admin/administrators/requests/{request_id}/approve`
- `POST /api/admin/administrators/requests/{request_id}/reject`
- `POST /api/admin/administrators/{admin_id}/revoke`
- `POST /api/admin/administrators/{admin_id}/set-password`

Regras de negocio importantes:

- nao permite revogar o proprio acesso;
- nao permite remover o ultimo administrador ativo;
- cadastro de nova senha so e permitido quando ha recadastro pendente.

### 9.4 Listagens operacionais

- `GET /api/admin/checkin`
- `GET /api/admin/checkout`
- `GET /api/admin/inactive`
- `GET /api/admin/pending`
- `GET /api/admin/users`
- `GET /api/admin/events`

Caracteristicas:

- `checkin` e `checkout` exibem usuarios com estado atual definido, inclusive aqueles sem atividade ha mais de 24 horas;
- `inactive` devolve `id`, `rfid`, `nome`, `chave`, `projeto`, `inactivity_days`;
- `events` retorna ate 200 eventos correntes, ordenados do mais recente para o mais antigo, ocultando os logs internos de `event_archive` da tabela principal.

### 9.5 CRUD operacional do admin

- `POST /api/admin/users`: cria ou atualiza usuario;
- `DELETE /api/admin/pending/{pending_id}`: remove pendencia RFID;
- `DELETE /api/admin/users/{user_id}`: remove usuario e apaga `user_sync_events` vinculados.

Regras importantes do `POST /api/admin/users`:

- pode criar usuario novo por `rfid`;
- pode editar usuario existente por `user_id`;
- pode vincular um RFID novo a um usuario ja criado pelo mobile quando a `chave` coincide e `rfid` ainda e `NULL`;
- bloqueia conflito de `chave` ja cadastrada;
- bloqueia substituicao arbitraria de RFID quando o usuario ja tem outro cartao vinculado;
- remove pendencia correspondente ao RFID apos cadastro.

### 9.6 Arquivamento de eventos

- `POST /api/admin/events/archive`
- `GET /api/admin/events/archives`
- `GET /api/admin/events/archives/download-all`
- `GET /api/admin/events/archives/{file_name}`
- `DELETE /api/admin/events/archives/{file_name}`

Fluxo:

1. seleciona os eventos correntes visiveis para arquivamento em CSV;
2. gera CSV com periodo no nome do arquivo;
3. limpa toda a tabela ativa de eventos, inclusive residuos antigos de auditoria de arquivamento;
4. registra o proprio ato de arquivamento em auditoria tecnica;
5. mantem os arquivos salvos disponiveis para download individual, download em lote zipado e exclusao.

## 10. Website administrativo: arquitetura e comportamento

### 10.1 Stack do frontend

O painel admin e uma SPA minimalista sem framework, composta por:

- HTML estatico em `index.html`;
- CSS puro em `styles.css`;
- JavaScript puro em `app.js`.

Nao existe React, Vue, build step frontend, bundler ou roteamento client-side complexo.

### 10.2 Estrutura visual

O HTML separa dois shells principais:

- `authShell`: tela de login e acoes de solicitacao admin/recadastro de senha;
- `adminShell`: painel principal exibido apenas quando ha sessao valida.

Abas do painel:

- Check-In
- Check-Out
- Cadastro
- Eventos

A aba Cadastro agrega tres blocos:

- pendencias RFID;
- administradores;
- usuarios cadastrados.

Modais existentes:

- detalhes de evento;
- logs salvos/arquivos de eventos;
- solicitacao de administrador.

### 10.3 Bootstrap da SPA

Ao carregar a pagina, o frontend executa `bootstrapAdmin()`.

Fluxo:

1. consulta `GET /api/admin/auth/session`;
2. se nao houver sessao, exibe o `authShell`;
3. se houver sessao, exibe o `adminShell`;
4. inicia atualizacao periodica por polling;
5. inicia SSE em `/api/admin/stream`;
6. carrega todas as tabelas.

### 10.4 Atualizacao de dados

O frontend combina duas estrategias:

1. SSE em tempo real como caminho preferencial;
2. polling a cada 5 segundos como fallback.

Detalhes:

- `AUTO_REFRESH_MS = 5000`;
- `REALTIME_DEBOUNCE_MS = 250` para reduzir recargas em rajadas de eventos;
- se a aba do navegador estiver oculta, o comportamento reduz atualizacoes desnecessarias;
- quando o SSE falha, o polling continua cobrindo o refresh.

### 10.5 Mapeamento das abas para a API

#### Check-In

- fonte: `GET /api/admin/checkin`
- colunas: horario, nome, chave, projeto, local, acoes
- quando o ultimo evento ultrapassa 24 horas, a data recebe sufixo `ha X dias`, a linha fica vermelha/negrito e o admin pode remover o usuario diretamente dessa tabela

#### Check-Out

- fonte: `GET /api/admin/checkout`
- colunas: horario, nome, chave, projeto, local, acoes
- quando o ultimo evento ultrapassa 24 horas, a data recebe sufixo `ha X dias`, a linha fica vermelha/negrito e o admin pode remover o usuario diretamente dessa tabela

#### Cadastro / Pendencias

- fonte: `GET /api/admin/pending`
- acoes: editar, remover, salvar cadastro
- persistencia: `POST /api/admin/users` e `DELETE /api/admin/pending/{id}`

#### Cadastro / Administradores

- fonte: `GET /api/admin/administrators`
- acoes condicionais por linha:
  - aprovar pedido;
  - rejeitar pedido;
  - revogar acesso;
  - cadastrar nova senha.

#### Cadastro / Usuarios cadastrados

- fonte: `GET /api/admin/users`
- acoes: editar, salvar, remover

#### Eventos

- fonte: `GET /api/admin/events`
- acao principal: `Limpar`, que arquiva os eventos correntes em CSV, limpa a tabela exibida e nao mostra os logs internos de `event_archive`

### 10.6 Tratamento de erros no frontend

O frontend centraliza chamadas em helpers como `fetchJson`, `postJson` e `deleteJson`.

Comportamentos importantes:

- erros `401` redirecionam o usuario de volta para o login;
- erros de validacao do backend sao convertidos em mensagens legiveis;
- algumas acoes confirmatorias usam `window.confirm()` antes de revogar, apagar ou excluir arquivos.

### 10.7 Convencoes do frontend

Algumas convencoes relevantes observadas em `app.js`:

- datas sao formatadas em timezone `Asia/Singapore`;
- `local` recebe labels amigaveis como `Escritorio Principal` e `A bordo da P83`;
- IDs usados para remocao sao validados como inteiros antes de chamadas destrutivas;
- quando ha edicao em andamento no cadastro, o frontend evita refresh automatico dessas tabelas para nao sobrescrever o formulario em uso.

## 11. Fluxos ponta a ponta mais importantes

### 11.1 RFID desconhecido

1. ESP32 envia `POST /api/scan`.
2. Backend nao encontra `users.rfid`.
3. Backend cria ou atualiza `pending_registrations`.
4. Backend registra evento de auditoria.
5. Painel admin recebe atualizacao e mostra a nova pendencia.
6. Um administrador cadastra o usuario a partir da aba Cadastro.

### 11.2 Check-in RFID valido

1. ESP32 envia scan com `action=checkin`.
2. Backend valida segredo e idempotencia.
3. Atualiza `users.checkin=true`, `time`, `local` e atividade.
4. Enfileira `forms_submissions`.
5. Registra `user_sync_events` como fonte `rfid`.
6. Notifica o painel admin.
7. Worker do Forms processa a fila fora do caminho sincrono.

### 11.3 Check-in repetido com usuario ja ativo

1. Novo `checkin` chega para usuario ja em check-in.
2. Backend atualiza apenas `local` e `time`.
3. Nao reenfileira o Forms.
4. Registra evento de `local_updated`.

### 11.4 Checkout sem check-in ativo

1. ESP32 envia `action=checkout`.
2. Backend detecta ausencia de check-in ativo.
3. Responde falha de negocio ao dispositivo.
4. Registra auditoria com status `blocked`.

### 11.5 Usuario criado pelo app antes do RFID

1. Android sincroniza evento com `POST /api/mobile/events/sync`.
2. Backend cria ou reaproveita usuario por `chave`, com `rfid=NULL` se necessario.
3. Mais tarde, no painel admin, um cadastro RFID pode ser vinculado ao mesmo usuario usando a mesma `chave`.

## 12. Auditoria, observabilidade e retencao

### 12.1 Trilhas de auditoria

`check_events` e a fonte principal para investigar:

- tentativas de login e logout;
- pedidos de admin e alteracoes administrativas;
- scans RFID recebidos, bloqueados ou duplicados;
- sincronizacao mobile;
- operacoes de arquivamento de logs.

### 12.2 Atualizacao em tempo real

O painel depende do broker de atualizacoes administrativas para refletir mudancas rapidamente.

Quando uma operacao relevante acontece, o backend chama `notify_admin_data_changed(reason)`.

### 12.3 Arquivos de eventos

Os eventos podem ser exportados para CSV e retirados da tabela ativa, reduzindo o tamanho da lista corrente sem perder historico operacional.

## 13. Riscos e pontos de atencao para manutencao

### 13.1 API e frontend estao fortemente acoplados por contrato JSON

O painel e simples, mas depende bastante do formato exato das respostas. Mudancas de schema nos endpoints admin tendem a quebrar a UI imediatamente.

### 13.2 Sessao admin depende de segredo estavel

Alterar `ADMIN_SESSION_SECRET` invalida todas as sessoes existentes.

### 13.3 Bootstrap admin deve ser tratado com cuidado em producao

As credenciais bootstrap sao uteis para seed e troubleshooting controlado, mas exigem gestao cuidadosa de ambiente e segredos.

### 13.4 Remocao de usuarios e destrutiva

`DELETE /api/admin/users/{user_id}` remove o usuario operacional e tambem apaga os `user_sync_events` associados. Isso tem impacto direto no historico disponivel para reconciliacao.

### 13.5 Fila do Forms pode divergir do estado sincrono

O scan pode ter sido aceito e refletido no admin enquanto o processamento posterior do Forms falha. Nesses casos, a depuracao deve olhar tambem para `forms_submissions`, worker e eventos de origem `forms`.

## 14. Guia rapido de leitura do codigo

Se a necessidade for entender rapidamente o sistema, a ordem mais produtiva e:

1. `sistema/app/main.py`
2. `sistema/app/core/config.py`
3. `sistema/app/models.py`
4. `sistema/app/routers/device.py`
5. `sistema/app/routers/mobile.py`
6. `sistema/app/routers/admin.py`
7. `sistema/app/static/admin/index.html`
8. `sistema/app/static/admin/app.js`
9. `tests/test_api_flow.py`

## 15. Resumo executivo

Hoje, a API e o website administrativo do Checking formam um unico sistema coeso com estas caracteristicas:

- backend FastAPI servindo API e SPA admin no mesmo processo;
- autenticacao admin por sessao cookie, sem header legado no runtime;
- painel administrativo em JavaScript puro, com SSE e polling;
- fluxos separados para ESP32 e Android, mas convergindo no mesmo estado de usuario;
- auditoria centralizada em `check_events`;
- fila persistida para o Microsoft Forms;
- suporte a arquivamento de logs em CSV;
- deploy orientado a container e health check.

Esse e o contexto tecnico essencial para evoluir o backend, ajustar contratos do admin ou investigar comportamento operacional do sistema.