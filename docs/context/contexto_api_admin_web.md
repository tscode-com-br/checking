# Contexto da API e do Website Administrativo

## 1. Objetivo deste documento

Este documento consolida o contexto técnico da API FastAPI e do website administrativo do projeto Checking.

Ele serve para:

- onboarding de novos desenvolvedores;
- manutenção do backend e do painel admin;
- entendimento rápido dos contratos entre frontend, backend, app Android e ESP32;
- depuração de problemas operacionais e de autenticação.

## 2. Visão geral da arquitetura

O projeto possui um único backend FastAPI que acumula três responsabilidades principais:

1. expor a API operacional usada pela ESP32 e pelo aplicativo Android;
2. servir o website administrativo estático;
3. coordenar persistência, auditoria, fila de envio ao Microsoft Forms e atualização em tempo real do painel admin.

Na prática, a API e o site administrativo não são sistemas separados. Ambos rodam no mesmo serviço Python.

Arquivos-chave:

- `sistema/app/main.py`: bootstrap da aplicação, middlewares, routers e montagem dos arquivos estáticos;
- `sistema/app/routers/device.py`: endpoints consumidos pela ESP32;
- `sistema/app/routers/mobile.py`: endpoints consumidos pelo app Android;
- `sistema/app/routers/admin.py`: autenticação admin, listagens, CRUD e logs;
- `sistema/app/static/admin/index.html`: casca HTML da SPA administrativa;
- `sistema/app/static/admin/app.js`: lógica do frontend admin em JavaScript puro;
- `sistema/app/static/admin/styles.css`: estilos do painel.

## 3. Ciclo de vida da aplicação

No startup da aplicação, o backend executa estes passos:

1. garante a existência do diretório de arquivos CSV arquivados de eventos;
2. cria as tabelas automaticamente apenas em ambiente `development`;
3. faz seed idempotente do administrador bootstrap;
4. inicia o worker da fila do Microsoft Forms quando `FORMS_QUEUE_ENABLED=true`.

No shutdown, o worker da fila é encerrado.

Esse comportamento está centralizado no lifespan definido em `sistema/app/main.py`.

## 4. Configuração central

As configurações ficam em `sistema/app/core/config.py`, carregadas por `pydantic-settings` a partir do arquivo `.env`.

Configurações mais relevantes para API e admin:

- `DATABASE_URL`: banco local ou de produção;
- `DEVICE_SHARED_KEY`: segredo compartilhado da ESP32;
- `MOBILE_APP_SHARED_KEY`: segredo compartilhado do app Android;
- `ADMIN_SESSION_SECRET`: segredo usado para assinar a sessão administrativa;
- `ADMIN_SESSION_MAX_AGE_SECONDS`: duração da sessão admin;
- `BOOTSTRAP_ADMIN_KEY`, `BOOTSTRAP_ADMIN_NAME`, `BOOTSTRAP_ADMIN_PASSWORD`: credenciais seed do primeiro administrador;
- `FORMS_QUEUE_ENABLED`: liga ou desliga o processamento assíncrono da fila do Microsoft Forms;
- `EVENT_ARCHIVES_DIR`: diretório onde os CSV de eventos arquivados são armazenados.

Padrões atuais importantes:

- banco local padrão: SQLite em `./checking.db`;
- timezone operacional: `Asia/Singapore`;
- diretório padrão de arquivos arquivados: `/app/data/event_archives`.

## 5. Estrutura de exposição HTTP

### 5.1 API pública e sem sessão admin

Rotas públicas disponíveis sem autenticação por sessão:

- `GET /api/health`: health check da aplicação;
- `POST /api/device/heartbeat`: presença da ESP32;
- `POST /api/scan`: eventos RFID de check-in e check-out;
- `GET /api/mobile/state`: consulta de estado consolidado do usuário pelo app Android;
- `POST /api/mobile/events/sync`: sincronização de eventos mobile com o backend.

Observação: essas rotas públicas continuam protegidas por segredos específicos do dispositivo ou do app mobile, quando aplicável.

### 5.2 Website admin e área autenticada

O website administrativo é servido pelo próprio FastAPI:

- `/`: entrega a SPA administrativa;
- `/admin`: redireciona para `/` por compatibilidade legada;
- `/assets/*`: arquivos compartilhados montados a partir da pasta `assets`.

Rotas protegidas por sessão cookie ficam sob o prefixo `/api/admin`.

## 6. Modelo de autenticação administrativa

### 6.1 Estratégia atual

O admin usa autenticação por sessão baseada em cookie, assinada por `SessionMiddleware` do Starlette.

Características:

- o frontend não envia `x-admin-key`;
- o backend guarda `admin_user_id` em `request.session` após login bem-sucedido;
- as rotas admin dependem de `require_admin_session()`;
- o stream SSE também exige sessão válida via `require_admin_stream_session()`;
- o frontend usa `fetch(..., { credentials: "same-origin" })` em todas as chamadas autenticadas.

### 6.2 Tabelas de autenticação admin

As entidades administrativas são separadas do cadastro operacional de funcionários:

- `admin_users`: administradores ativos ou com recadastro de senha pendente;
- `admin_access_requests`: solicitações pendentes para se tornar administrador.

Isso evita misturar identidade administrativa com a tabela operacional `users`.

### 6.3 Bootstrap admin

Ao subir a aplicação, o backend garante um administrador bootstrap com base nas variáveis de ambiente.

Esse seed é idempotente:

- se a `chave` bootstrap já existir em `admin_users`, nada novo é criado;
- se não existir, o registro é criado com senha hash PBKDF2-SHA256.

### 6.4 Fluxos de autenticação admin

Rotas de autenticação:

- `POST /api/admin/auth/login`
- `POST /api/admin/auth/logout`
- `GET /api/admin/auth/session`
- `POST /api/admin/auth/request-access`
- `POST /api/admin/auth/request-password-reset`

Fluxos implementados:

1. Login normal:
   - valida `chave` e `senha`;
   - rejeita admin inexistente;
   - rejeita senha inválida;
   - bloqueia login se houver recadastro pendente de senha;
   - grava `admin_user_id` na sessão.

2. Solicitação de acesso admin:
   - qualquer pessoa com `chave`, `nome_completo` e `senha` pode gerar pedido pendente;
   - o pedido fica em `admin_access_requests`;
   - outro administrador aprova ou rejeita pelo painel.

3. Recadastro de senha:
   - o próprio administrador informa a chave;
   - a senha atual é apagada;
   - `requires_password_reset` passa para `true`;
   - outro administrador deve cadastrar nova senha.

4. Sessão expirada:
   - o frontend trata `401` de forma centralizada;
   - o painel volta para a tela de login.

## 7. Modelo de dados relevante para a API e o admin

### 7.1 `users`

Representa o cadastro operacional e o estado atual de presença do funcionário.

Campos relevantes:

- `id`: inteiro autoincremental;
- `rfid`: único, pode ser `NULL`;
- `chave`: única, 4 caracteres alfanuméricos;
- `nome`;
- `projeto`: hoje limitado a `P80`, `P82`, `P83` nos schemas;
- `local`: último local conhecido;
- `checkin`: `true`, `false` ou `NULL`;
- `time`: timestamp do último evento aplicado ao estado atual;
- `last_active_at` e `inactivity_days`: base para o controle de inatividade no backend.

Ponto importante: `rfid` pode ser `NULL` para suportar usuários criados primeiro pelo app Android e vinculados ao cartão somente depois.

### 7.2 `pending_registrations`

Armazena RFIDs ainda não reconhecidos pelo sistema.

Campos:

- `id`
- `rfid` único
- `first_seen_at`
- `last_seen_at`
- `attempts`

Essa tabela alimenta a área de cadastro do admin.

### 7.3 `check_events`

É a trilha de auditoria operacional do sistema.

Registra:

- recebimento de scan;
- bloqueios e duplicidades;
- operações administrativas;
- login/logout e gestão de admins;
- sincronização mobile;
- criação/download/exclusão de arquivos de eventos.

Possui `idempotency_key` única para evitar duplicidade de alguns fluxos.

### 7.4 `forms_submissions`

Fila persistida para envio assíncrono ao Microsoft Forms.

Ela desacopla a resposta ao ESP32 do processamento do Forms.

### 7.5 `user_sync_events`

Histórico canônico dos eventos aplicados ao usuário, vindos de RFID ou Android.

Restrição importante:

- unicidade por `source` + `source_request_id`.

Isso permite idempotência do canal mobile e rastreabilidade entre fontes.

### 7.6 `admin_users` e `admin_access_requests`

Suportam governança do acesso administrativo sem reaproveitar a tabela operacional de usuários.

## 8. Contratos da API por domínio

### 8.1 Health

`GET /api/health`

Retorna estado simples da aplicação para monitoramento e para a pipeline de deploy.

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
- em caso de chave inválida, registra evento de falha e devolve resposta simples ao dispositivo.

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
- `led`: instruções de padrão visual para a ESP32;
- `message`: mensagem operacional.

Ordem de processamento:

1. valida a `shared_key` do dispositivo;
2. verifica idempotência por `request_id` em `check_events`;
3. registra recebimento do scan em auditoria;
4. tenta localizar usuário por RFID;
5. se o RFID for desconhecido, cria ou atualiza pendência;
6. se o usuário já estiver em check-in e ocorrer novo `checkin`, atualiza apenas o `local` e o timestamp, sem enfileirar Forms;
7. se ocorrer `checkout` sem check-in ativo, bloqueia a operação;
8. para operação válida, atualiza o estado atual do usuário;
9. enfileira envio ao Forms em `forms_submissions`;
10. grava `user_sync_events` como fonte `rfid`;
11. publica atualização para o painel admin.

Regras de negócio importantes:

- RFID desconhecido não cria usuário automaticamente; cria pendência;
- `checkin` repetido com usuário já ativo vira apenas atualização de local;
- `checkout` sem `checkin` ativo retorna erro de negócio;
- a resposta ao dispositivo sai antes da conclusão do Forms.

### 8.3 Canal mobile Android

O canal mobile usa o header `x-mobile-shared-key`.

#### `GET /api/mobile/state?chave=...`

Retorna estado consolidado do usuário:

- se existe ou não;
- nome e projeto;
- ação atual;
- horário do estado atual;
- último check-in;
- último check-out.

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

- exige `x-mobile-shared-key` válido;
- é idempotente por `client_event_id`;
- pode criar usuário placeholder se a `chave` ainda não existir;
- normaliza o horário do evento;
- aplica o estado atual em `users`;
- grava `user_sync_events` com `source="android"`;
- publica atualização para o painel admin.

Diferença importante em relação ao canal RFID:

- o mobile não passa pela fila do Microsoft Forms dentro desta API;
- ele sincroniza apenas o estado consolidado no backend após o fluxo do app.

## 9. Rotas protegidas do admin

### 9.1 Sessão e autenticação

- `POST /api/admin/auth/login`
- `POST /api/admin/auth/logout`
- `GET /api/admin/auth/session`
- `POST /api/admin/auth/request-access`
- `POST /api/admin/auth/request-password-reset`

### 9.2 Atualização em tempo real

- `GET /api/admin/stream`

Entrega Server-Sent Events com payload JSON contendo pelo menos:

- `reason`
- `emitted_at`

O broker interno usa filas por assinante e descarta o item mais antigo quando a fila lota.

Razões publicadas com mais frequência:

- `checkin`
- `checkout`
- `pending`
- `register`
- `admin`
- `event`

### 9.3 Gestão de administradores

- `GET /api/admin/administrators`
- `POST /api/admin/administrators/requests/{request_id}/approve`
- `POST /api/admin/administrators/requests/{request_id}/reject`
- `POST /api/admin/administrators/{admin_id}/revoke`
- `POST /api/admin/administrators/{admin_id}/set-password`

Regras de negócio importantes:

- não permite revogar o próprio acesso;
- não permite remover o último administrador ativo;
- cadastro de nova senha só é permitido quando há recadastro pendente.

### 9.4 Listagens operacionais

- `GET /api/admin/checkin`
- `GET /api/admin/checkout`
- `GET /api/admin/inactive`
- `GET /api/admin/pending`
- `GET /api/admin/users`
- `GET /api/admin/events`

Características:

- `checkin` e `checkout` exibem usuários com estado atual definido, inclusive aqueles sem atividade há mais de 24 horas;
- `inactive` devolve `id`, `rfid`, `nome`, `chave`, `projeto`, `inactivity_days`;
- `events` retorna até 200 eventos correntes, ordenados do mais recente para o mais antigo, ocultando os logs internos de `event_archive` da tabela principal.

### 9.5 CRUD operacional do admin

- `POST /api/admin/users`: cria ou atualiza usuário;
- `DELETE /api/admin/pending/{pending_id}`: remove pendência RFID;
- `DELETE /api/admin/users/{user_id}`: remove usuário e apaga `user_sync_events` vinculados.

Regras importantes do `POST /api/admin/users`:

- pode criar usuário novo por `rfid`;
- pode editar usuário existente por `user_id`;
- pode vincular um RFID novo a um usuário já criado pelo mobile quando a `chave` coincide e `rfid` ainda é `NULL`;
- bloqueia conflito de `chave` já cadastrada;
- bloqueia substituição arbitrária de RFID quando o usuário já tem outro cartão vinculado;
- remove pendência correspondente ao RFID após cadastro.

### 9.6 Arquivamento de eventos

- `POST /api/admin/events/archive`
- `GET /api/admin/events/archives`
- `GET /api/admin/events/archives/download-all`
- `GET /api/admin/events/archives/{file_name}`
- `DELETE /api/admin/events/archives/{file_name}`

Fluxo:

1. seleciona os eventos correntes visíveis para arquivamento em CSV;
2. gera CSV com período no nome do arquivo;
3. limpa toda a tabela ativa de eventos, inclusive resíduos antigos de auditoria de arquivamento;
4. registra o próprio ato de arquivamento em auditoria técnica;
5. mantém os arquivos salvos disponíveis para download individual, download em lote zipado e exclusão.

## 10. Website administrativo: arquitetura e comportamento

### 10.1 Stack do frontend

O painel admin é uma SPA minimalista sem framework, composta por:

- HTML estático em `index.html`;
- CSS puro em `styles.css`;
- JavaScript puro em `app.js`.

Não existe React, Vue, build step frontend, bundler ou roteamento client-side complexo.

### 10.2 Estrutura visual

O HTML separa dois shells principais:

- `authShell`: tela de login e ações de solicitação admin/recadastro de senha;
- `adminShell`: painel principal exibido apenas quando há sessão válida.

Abas do painel:

- Check-In
- Check-Out
- Cadastro
- Eventos

A aba Cadastro agrega três blocos:

- pendências RFID;
- administradores;
- usuários cadastrados.

Modais existentes:

- detalhes de evento;
- logs salvos/arquivos de eventos;
- solicitação de administrador.

### 10.3 Bootstrap da SPA

Ao carregar a página, o frontend executa `bootstrapAdmin()`.

Fluxo:

1. consulta `GET /api/admin/auth/session`;
2. se não houver sessão, exibe o `authShell`;
3. se houver sessão, exibe o `adminShell`;
4. inicia atualização periódica por polling;
5. inicia SSE em `/api/admin/stream`;
6. carrega todas as tabelas.

### 10.4 Atualização de dados

O frontend combina duas estratégias:

1. SSE em tempo real como caminho preferencial;
2. polling a cada 5 segundos como fallback.

Detalhes:

- `AUTO_REFRESH_MS = 5000`;
- `REALTIME_DEBOUNCE_MS = 250` para reduzir recargas em rajadas de eventos;
- se a aba do navegador estiver oculta, o comportamento reduz atualizações desnecessárias;
- quando o SSE falha, o polling continua cobrindo o refresh.

### 10.5 Mapeamento das abas para a API

#### Check-In

- fonte: `GET /api/admin/checkin`
- colunas: horário, nome, chave, projeto, local, ações
- quando o último evento ultrapassa 24 horas, a data recebe sufixo `há X dias`, a linha fica vermelha/negrito e o admin pode remover o usuário diretamente dessa tabela

#### Check-Out

- fonte: `GET /api/admin/checkout`
- colunas: horário, nome, chave, projeto, local, ações
- quando o último evento ultrapassa 24 horas, a data recebe sufixo `há X dias`, a linha fica vermelha/negrito e o admin pode remover o usuário diretamente dessa tabela

#### Cadastro / Pendências

- fonte: `GET /api/admin/pending`
- ações: editar, remover, salvar cadastro
- persistência: `POST /api/admin/users` e `DELETE /api/admin/pending/{id}`

#### Cadastro / Administradores

- fonte: `GET /api/admin/administrators`
- ações condicionais por linha:
  - aprovar pedido;
  - rejeitar pedido;
  - revogar acesso;
  - cadastrar nova senha.

#### Cadastro / Usuários cadastrados

- fonte: `GET /api/admin/users`
- ações: editar, salvar, remover

#### Eventos

- fonte: `GET /api/admin/events`
- ação principal: `Limpar`, que arquiva os eventos correntes em CSV, limpa a tabela exibida e não mostra os logs internos de `event_archive`

### 10.6 Tratamento de erros no frontend

O frontend centraliza chamadas em helpers como `fetchJson`, `postJson` e `deleteJson`.

Comportamentos importantes:

- erros `401` redirecionam o usuário de volta para o login;
- erros de validação do backend são convertidos em mensagens legíveis;
- algumas ações confirmatórias usam `window.confirm()` antes de revogar, apagar ou excluir arquivos.

### 10.7 Convenções do frontend

Algumas convenções relevantes observadas em `app.js`:

- datas são formatadas no timezone `Asia/Singapore`;
- `local` recebe labels amigáveis como `Escritorio Principal` e `A bordo da P83`;
- IDs usados para remoção são validados como inteiros antes de chamadas destrutivas;
- quando há edição em andamento no cadastro, o frontend evita refresh automático dessas tabelas para não sobrescrever o formulário em uso.

## 11. Fluxos ponta a ponta mais importantes

### 11.1 RFID desconhecido

1. ESP32 envia `POST /api/scan`.
2. O backend não encontra `users.rfid`.
3. O backend cria ou atualiza `pending_registrations`.
4. O backend registra evento de auditoria.
5. O painel admin recebe atualização e mostra a nova pendência.
6. Um administrador cadastra o usuário a partir da aba Cadastro.

### 11.2 Check-in RFID válido

1. ESP32 envia scan com `action=checkin`.
2. O backend valida segredo e idempotência.
3. Atualiza `users.checkin=true`, `time`, `local` e atividade.
4. Enfileira `forms_submissions`.
5. Registra `user_sync_events` como fonte `rfid`.
6. Notifica o painel admin.
7. O worker do Forms processa a fila fora do caminho síncrono.

### 11.3 Check-in repetido com usuário já ativo

1. Novo `checkin` chega para um usuário já em check-in.
2. O backend atualiza apenas `local` e `time`.
3. Não reenfileira o Forms.
4. Registra evento de `local_updated`.

### 11.4 Checkout sem check-in ativo

1. ESP32 envia `action=checkout`.
2. O backend detecta ausência de check-in ativo.
3. Responde falha de negócio ao dispositivo.
4. Registra auditoria com status `blocked`.

### 11.5 Usuário criado pelo app antes do RFID

1. Android sincroniza evento com `POST /api/mobile/events/sync`.
2. O backend cria ou reaproveita usuário por `chave`, com `rfid=NULL` se necessário.
3. Mais tarde, no painel admin, um cadastro RFID pode ser vinculado ao mesmo usuário usando a mesma `chave`.

## 12. Auditoria, observabilidade e retenção

### 12.1 Trilhas de auditoria

`check_events` é a fonte principal para investigar:

- tentativas de login e logout;
- pedidos de admin e alterações administrativas;
- scans RFID recebidos, bloqueados ou duplicados;
- sincronização mobile;
- operações de arquivamento de logs.

### 12.2 Atualização em tempo real

O painel depende do broker de atualizações administrativas para refletir mudanças rapidamente.

Quando uma operação relevante acontece, o backend chama `notify_admin_data_changed(reason)`.

### 12.3 Arquivos de eventos

Os eventos podem ser exportados para CSV e retirados da tabela ativa, reduzindo o tamanho da lista corrente sem perder histórico operacional.

## 13. Riscos e pontos de atenção para manutenção

### 13.1 API e frontend estão fortemente acoplados por contrato JSON

O painel é simples, mas depende bastante do formato exato das respostas. Mudanças de schema nos endpoints admin tendem a quebrar a UI imediatamente.

### 13.2 Sessão admin depende de segredo estável

Alterar `ADMIN_SESSION_SECRET` invalida todas as sessões existentes.

### 13.3 Bootstrap admin deve ser tratado com cuidado em produção

As credenciais bootstrap são úteis para seed e troubleshooting controlado, mas exigem gestão cuidadosa de ambiente e segredos.

### 13.4 Remoção de usuários é destrutiva

`DELETE /api/admin/users/{user_id}` remove o usuário operacional e também apaga os `user_sync_events` associados. Isso tem impacto direto no histórico disponível para reconciliação.

### 13.5 Fila do Forms pode divergir do estado síncrono

O scan pode ter sido aceito e refletido no admin enquanto o processamento posterior do Forms falha. Nesses casos, a depuração deve olhar também para `forms_submissions`, o worker e os eventos de origem `forms`.

## 14. Guia rápido de leitura do código

Se a necessidade for entender rapidamente o sistema, a ordem mais produtiva é:

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

Hoje, a API e o website administrativo do Checking formam um único sistema coeso com estas características:

- backend FastAPI servindo API e SPA admin no mesmo processo;
- autenticação admin por sessão cookie, sem header legado no runtime;
- painel administrativo em JavaScript puro, com SSE e polling;
- fluxos separados para ESP32 e Android, mas convergindo no mesmo estado de usuário;
- auditoria centralizada em `check_events`;
- fila persistida para o Microsoft Forms;
- suporte a arquivamento de logs em CSV;
- deploy orientado a container e health check.

Esse é o contexto técnico essencial para evoluir o backend, ajustar contratos do admin ou investigar o comportamento operacional do sistema.
