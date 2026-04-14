# Contexto consolidado: website admin, API FastAPI e app Flutter

## 1. Objetivo deste documento

Este documento consolida o contexto tecnico atual de tres partes do projeto Checking:

- website administrativo;
- API em Python/FastAPI;
- aplicativo Flutter em `checking_android_new`.

O foco aqui e registrar o estado real implementado no codigo, incluindo integracoes, limites, contratos, dependencias e pontos que ainda estao incompletos ou locais ao frontend.

## 2. Escopo, repositorios e deploy

### 2.1 Monorepo atual

Este repositorio concentra hoje:

- a API FastAPI;
- o website administrativo servido pela propria API;
- o firmware ESP32;
- o app Android antigo em Tauri (`checking_android`);
- o app Android novo em Flutter (`checking_android_new`).

### 2.2 O que este contexto cobre

Este documento cobre somente:

- `sistema/app`;
- `sistema/app/static/admin`;
- `checking_android_new`.

O app antigo em Tauri aparece apenas como contexto historico e de transicao.

### 2.3 Relacao com repositorios externos

- API + website admin usam o repositorio principal e sao parte do fluxo de deploy automatico para a Digital Ocean.
- O app Android antigo em `checking_android` possui repositorio proprio, compartilhado com `dsschmidt`.
- O app Flutter em `checking_android_new` ainda nao possui repositorio proprio. Ele continua dentro do monorepo.

### 2.4 Impacto pratico de deploy

Push em `main` no repositorio principal atualiza a API e o website admin no ambiente da Digital Ocean.

O app Flutter nao entra nesse deploy automatico. Ele tem ciclo de build/publicacao proprio, via `flutter build` e geracao de APK/AAB.

## 3. Visao geral da arquitetura

### 3.1 Como os blocos se relacionam

Hoje a arquitetura operacional relevante e esta:

1. ESP32 envia RFID e heartbeat para a API.
2. App Flutter envia eventos mobile e consulta estado do usuario na API.
3. API atualiza banco, escreve trilha de auditoria e enfileira submissao ao Microsoft Forms quando necessario.
4. Website admin le os dados da API, autentica por sessao cookie e acompanha mudancas em tempo real por SSE.

### 3.2 Fonte de verdade

A fonte de verdade operacional atual nao e uma unica tabela isolada. O sistema depende principalmente de:

- `users`: estado atual do usuario;
- `user_sync_events`: historico canonico usado para reconciliar origem RFID/mobile;
- `check_events`: auditoria detalhada do sistema;
- `forms_submissions`: fila persistida para envio ao Microsoft Forms.

## 4. API em Python/FastAPI

### 4.1 Arquivos centrais

- `sistema/app/main.py`: bootstrap, middleware, rotas e montagem dos arquivos estaticos.
- `sistema/app/core/config.py`: configuracao central por `pydantic-settings`.
- `sistema/app/models.py`: modelos SQLAlchemy.
- `sistema/app/routers/device.py`: endpoints da ESP32.
- `sistema/app/routers/mobile.py`: endpoints do app mobile.
- `sistema/app/routers/admin.py`: autenticacao admin, CRUD, eventos e arquivos CSV.

### 4.2 Startup e lifecycle

No lifespan da aplicacao, a API faz quatro coisas importantes:

1. garante a existencia do diretorio de arquivos arquivados de eventos;
2. executa `Base.metadata.create_all()` somente em `development`;
3. cria idempotentemente o admin bootstrap;
4. inicia o worker da fila do Microsoft Forms quando `FORMS_QUEUE_ENABLED=true`.

No shutdown, o worker da fila e encerrado.

### 4.3 Middleware e exposicao HTTP

O backend usa:

- `CORSMiddleware` para origens locais (`localhost`, `127.0.0.1`, `tauri.localhost`);
- `SessionMiddleware` para autenticar o painel admin por cookie assinado.

Montagens relevantes:

- `/` serve a SPA administrativa;
- `/admin` e `/admin/{path}` redirecionam para `/` por compatibilidade legada;
- `/assets` expoe arquivos compartilhados do repositorio.

Na pratica, API e website admin sao o mesmo servico Python.

### 4.4 Configuracao central

Configuracoes mais importantes em `core/config.py`:

- `DATABASE_URL`: SQLite local por padrao (`sqlite:///./checking.db`);
- `TZ_NAME`: timezone operacional (`Asia/Singapore`);
- `DEVICE_SHARED_KEY`: segredo do canal ESP32;
- `MOBILE_APP_SHARED_KEY`: segredo do canal mobile;
- `ADMIN_SESSION_SECRET`: assinatura da sessao admin;
- `ADMIN_SESSION_MAX_AGE_SECONDS`: expiracao da sessao;
- `BOOTSTRAP_ADMIN_KEY`, `BOOTSTRAP_ADMIN_NAME`, `BOOTSTRAP_ADMIN_PASSWORD`: seed do primeiro admin;
- `FORMS_QUEUE_ENABLED`: liga ou desliga a fila assicrona do Forms;
- `EVENT_ARCHIVES_DIR`: onde os CSV arquivados ficam salvos.

### 4.5 Superficie de rotas

#### Rotas publicas ou autenticadas por chave compartilhada

- `GET /api/health`
- `POST /api/device/heartbeat`
- `POST /api/scan`
- `GET /api/mobile/state`
- `POST /api/mobile/events/sync`
- `POST /api/mobile/events/submit`
- `POST /api/mobile/events/forms-submit`
- `GET /api/mobile/locations`

#### Rotas protegidas por sessao admin

Prefixo `/api/admin`:

- autenticacao e sessao;
- SSE de atualizacao;
- listagens de check-in, check-out, pendencias, usuarios, administradores e eventos;
- CRUD de usuarios e pendencias;
- CRUD de localizacoes;
- aprovacao/rejeicao/revogacao de administradores;
- recadastro de senha admin;
- arquivamento, listagem, download e exclusao de arquivos CSV de eventos.

### 4.6 Modelo de dados principal

#### `users`

Representa o estado operacional atual de cada funcionario:

- `id` inteiro autoincremental;
- `rfid` unico e anulavel;
- `chave` unica de 4 caracteres;
- `nome`, `projeto`, `local`;
- `checkin` e `time` para o estado atual;
- `last_active_at` e `inactivity_days` para controle de inatividade.

O fato de `rfid` ser anulavel e deliberado: permite que um usuario seja criado primeiro pelo app mobile e receba cartao depois.

#### `pending_registrations`

RFIDs desconhecidos lidos pela ESP32 ficam aqui ate cadastro administrativo.

#### `check_events`

Auditoria ampla do sistema. Registra operacoes de device, mobile, forms e admin. Tambem concentra chaves de idempotencia e metadados operacionais.

#### `forms_submissions`

Fila persistida de submissao ao Microsoft Forms. O endpoint aceita o evento primeiro e o worker processa depois.

#### `locations`

Catalogo administrativo de localizacoes com:

- nome logico (`local`);
- latitude;
- longitude;
- tolerancia em metros.

Esse catalogo e a base usada pelo app Flutter para sincronizar o banco local de localizacoes e avaliar se o usuario entrou no range de um ponto cadastrado.

#### `user_sync_events`

Historico canonico de eventos vindos de RFID e mobile. A unicidade por `source + source_request_id` protege o canal contra duplicidade.

#### `admin_users` e `admin_access_requests`

Tabelas proprias de governanca do painel admin. Nao reutilizam `users` para login administrativo.

### 4.7 Fluxo RFID da ESP32

O endpoint operacional principal e `POST /api/scan`.

Sequencia real do fluxo:

1. valida `DEVICE_SHARED_KEY`;
2. rejeita duplicidade por `request_id` em `check_events`;
3. grava auditoria de recebimento;
4. tenta localizar usuario por RFID;
5. se RFID nao existe, cria ou atualiza `pending_registrations` e retorna `pending_registration`;
6. se houver usuario conhecido, atualiza `local` e aplica regras de negocio;
7. em sucesso, enfileira `forms_submissions`;
8. grava `user_sync_events` com `source="rfid"`;
9. notifica o painel admin;
10. retorna resposta imediata ao dispositivo, sem esperar o Forms concluir.

Regras de negocio importantes:

- `checkin` repetido para quem ja esta em check-in nao reenfileira Forms; apenas atualiza `local` e o horario atual;
- `checkout` sem check-in ativo retorna bloqueio;
- RFID desconhecido nao falha duro; vira pendencia de cadastro.

### 4.8 Heartbeat do dispositivo

`POST /api/device/heartbeat` valida a chave compartilhada do dispositivo e grava `device_heartbeats`.

### 4.9 Fluxo mobile

O canal mobile usa header `x-mobile-shared-key` e nao depende da sessao admin.

#### `GET /api/mobile/state`

Retorna estado consolidado do usuario por `chave`, incluindo:

- usuario encontrado ou nao;
- nome;
- projeto;
- acao atual;
- horario atual;
- ultimo check-in;
- ultimo check-out.

Esse estado e montado a partir de `users`, `user_sync_events` e, quando preciso, fallback para `check_events` ligados ao RFID.

#### `POST /api/mobile/events/sync`

Sincroniza evento mobile diretamente no banco, sem reenfileirar Forms.

E util como contrato de sincronizacao simples e e protegido por idempotencia via `client_event_id`.

No estado atual, esse endpoint existe para sincronizacao leve do backend, mas o app Flutter nao o usa no fluxo principal.

#### `POST /api/mobile/events/submit`

Aplica o evento ao usuario e enfileira uma submissao ao Forms com `source="android"`.

#### `POST /api/mobile/events/forms-submit`

E o endpoint mais alinhado ao app Flutter atual. Ele:

- aceita `informe` (`normal` ou `retroativo`);
- converte isso em `ontime=true/false`;
- aplica o estado no usuario;
- enfileira Forms;
- grava `user_sync_events` com `source="android_forms"`;
- retorna estado atualizado do usuario.

O payload agora tambem aceita `local` opcional.

Regras atuais:

- se `local` vier preenchido, esse valor atualiza `users.local`, `user_sync_events.local`, `forms_submissions.local` e a trilha de auditoria;
- se `local` nao vier, o backend assume `Aplicativo`;
- essa informacao nao e usada para preencher o Microsoft Forms.

#### `GET /api/mobile/locations`

Retorna o catalogo de localizacoes administrativas para o app Flutter atualizar seu banco local.

Esse endpoint existe especificamente para o sincronismo do app e usa somente a chave compartilhada mobile.

#### Usuarios criados pelo app

Se a `chave` ainda nao existir em `users`, o backend cria automaticamente um usuario placeholder com nome `Oriundo do Aplicativo`.

Isso permite iniciar o uso do app antes do vinculo do RFID.

### 4.10 Fila do Microsoft Forms

O processamento assicrono esta centralizado em `services/forms_queue.py`.

Comportamento:

- a API grava primeiro em `forms_submissions` com `status="pending"`;
- um worker em thread faz polling a cada `0.25s`, reserva o proximo item e troca para `processing`;
- `FormsWorker` tenta submeter o formulario usando os assets/XPaths do projeto;
- ao final, a fila marca `success` ou `failed`;
- a API registra um evento de auditoria `source="forms"`;
- o painel admin recebe notificacao para atualizar.

Cada ciclo do worker processa ate `10` itens antes de voltar ao polling.

Isso reduz o tempo de resposta do endpoint operacional e separa o estado local da automacao externa.

### 4.11 Inatividade e reconciliacao de estado

`services/user_activity.py` recalcula `inactivity_days` usando `last_active_at` e a data atual.

Ja `services/user_sync.py` faz a parte critica de reconciliar fontes:

- busca usuario por `rfid` ou `chave`;
- cria usuarios mobile quando necessario;
- escreve `user_sync_events`;
- resolve a atividade mais recente combinando `users`, `user_sync_events` e `check_events`.

Essa camada e a ponte mais importante entre RFID, mobile e painel.

## 5. Website administrativo

### 5.1 Stack e arquivos

O website admin nao e um projeto separado. Ele e uma SPA estatica em JavaScript puro servida pelo FastAPI.

Arquivos principais:

- `sistema/app/static/admin/index.html`
- `sistema/app/static/admin/app.js`
- `sistema/app/static/admin/styles.css`

Nao existe bundler, framework JS nem pipeline de build dedicada.

### 5.2 Estrutura geral da interface

O HTML e dividido em dois shells:

- `authShell`: tela de login admin;
- `adminShell`: painel principal apos autenticacao.

Abas atuais do painel:

- Check-In
- Check-Out
- Cadastro
- Eventos

Modais atuais:

- solicitar admin;
- detalhes de evento;
- arquivos CSV arquivados.

### 5.3 Autenticacao administrativa

O admin usa cookie de sessao assinado pelo `SessionMiddleware` do Starlette.

Fluxo:

1. frontend chama `GET /api/admin/auth/session` no bootstrap;
2. sem sessao valida, fica em `authShell`;
3. com sessao valida, mostra o painel, inicia SSE e carrega tabelas;
4. qualquer `401` derruba o usuario de volta para a tela de login.

Rotas de autenticacao usadas pelo frontend:

- `POST /api/admin/auth/login`
- `POST /api/admin/auth/logout`
- `GET /api/admin/auth/session`
- `POST /api/admin/auth/request-access`
- `POST /api/admin/auth/request-password-reset`

### 5.4 Realtime e polling

O painel tenta trabalhar em tempo real por `EventSource` em `GET /api/admin/stream`.

Detalhes:

- recebe evento inicial `connected`;
- recebe keep-alive a cada `15s` quando nao ha eventos;
- o broker interno usa uma fila em memoria por assinante com `maxsize=20`;
- debounce de atualizacao em `250ms`;
- fallback para polling a cada `5s` quando o realtime nao esta conectado.

### 5.5 Como o frontend carrega dados

`refreshAllTables()` busca em paralelo:

- check-in;
- check-out;
- eventos;
- administradores;
- pendencias e usuarios, quando nao existe edicao inline em andamento.

Esse cuidado evita que o refresh sobrescreva uma linha em edicao no cadastro.

### 5.6 Check-In e Check-Out

As abas de presenca usam principalmente:

- `GET /api/admin/checkin`
- `GET /api/admin/checkout`

O backend monta essas listas usando `resolve_latest_user_activity()`, em vez de depender apenas dos campos crus de `users`.

### 5.7 Como a UI trata inatividade

Existe uma rota backend `GET /api/admin/inactive`, mas a UI atual nao depende dela para renderizar as secoes de inativos.

No frontend atual, a inatividade e calculada localmente a partir de `row.time`, comparando o dia do evento com o dia corrente em `Asia/Singapore`.

Consequencias:

- usuarios antigos sao movidos para a secao `Usuarios Inativos` dentro das abas de Check-In e Check-Out;
- a aba Check-Out ainda destaca `Usuarios sem Check-Out`, construida a partir de usuarios que permaneceram em check-in em dia anterior.

### 5.8 Cadastro

A aba `Cadastro` agrega quatro areas:

- RFIDs pendentes;
- Localizacoes;
- Administradores;
- Usuarios cadastrados.

#### RFIDs pendentes

Usa `GET /api/admin/pending`, `POST /api/admin/users` e `DELETE /api/admin/pending/{id}`.

#### Usuarios cadastrados

Usa `GET /api/admin/users`, `POST /api/admin/users` e `DELETE /api/admin/users/{user_id}`.

O `upsert` admin tem uma regra importante: se ja existe usuario com a mesma `chave` e `rfid=NULL`, o cadastro pode reaproveitar esse usuario para vincular o cartao fisico em vez de criar duplicado.

#### Administradores

Usa:

- `GET /api/admin/administrators`
- `POST /api/admin/administrators/requests/{id}/approve`
- `POST /api/admin/administrators/requests/{id}/reject`
- `POST /api/admin/administrators/{id}/revoke`
- `POST /api/admin/administrators/{id}/set-password`

Regras relevantes:

- nao pode revogar o proprio acesso;
- nao pode remover o ultimo admin ativo;
- nova senha so pode ser cadastrada quando `requires_password_reset=true`.

#### Localizacoes

A secao de localizacoes agora e persistida no backend.

Rotas usadas:

- `GET /api/admin/locations`
- `POST /api/admin/locations`
- `DELETE /api/admin/locations/{location_id}`

Cada localizacao guarda nome, coordenadas e tolerancia em metros.

Esses registros sao reutilizados pelo app Flutter para a automacao de check-in e check-out por proximidade.

### 5.9 Eventos e arquivos CSV

Eventos correntes usam `GET /api/admin/events`.

O painel mostra, por linha:

- horario;
- origem;
- acao;
- status;
- device;
- local;
- RFID;
- projeto;
- `ontime`;
- HTTP;
- rota;
- tentativas;
- mensagem;
- detalhes.

Arquivos de eventos usam:

- `POST /api/admin/events/archive`
- `GET /api/admin/events/archives`
- `GET /api/admin/events/archives/{file_name}`
- `GET /api/admin/events/archives/download-all`
- `DELETE /api/admin/events/archives/{file_name}`

O fluxo de limpar eventos arquiva antes, depois permite consulta, download e exclusao dos CSVs.

## 6. Aplicativo Flutter em `checking_android_new`

### 6.1 Escopo atual

O app Flutter e hoje o candidato a substituir o app Android antigo em Tauri no medio prazo, mas ainda vive dentro do monorepo.

Ele faz principalmente:

- envio manual de check-in/check-out para a API;
- consulta do ultimo check-in e check-out do usuario;
- sincronizacao do catalogo de localizacoes da API para um banco local SQLite;
- compartilhamento de localizacao com monitoramento em segundo plano no Android via `geolocator`;
- check-in e check-out automaticos por proximidade ou por afastamento das areas monitoradas;
- agendamento local por notificacoes Android;
- reentrada no app por acao nativa para disparar envio automatico.

No bootstrap visual, o app ainda mostra uma tela de apresentacao de `2s` antes de abrir a tela principal.

### 6.2 Stack e dependencias

Dados relevantes do projeto:

- Flutter/Dart com `sdk: ^3.11.0`;
- versao do app: `1.1.0+3`;
- sem framework extra de estado; o app usa `ChangeNotifier` + `AnimatedBuilder`;
- `http` para API;
- `shared_preferences` para estado local comum;
- `flutter_secure_storage` para a chave compartilhada da API;
- `sqflite` para o banco local de localizacoes;
- `path` para resolver o caminho do SQLite local;
- `geolocator` para leitura de localizacao, foreground notification e calculo de distancia;
- `permission_handler` para o fluxo de permissoes de localizacao;
- `intl` para formatacao de datas/horas.

### 6.3 Estrutura do codigo

Arquivos centrais:

- `lib/main.dart`
- `lib/src/app/checking_app.dart`
- `lib/src/core/theme/app_theme.dart`
- `lib/src/features/checking/models/*`
- `lib/src/features/checking/services/checking_services.dart`
- `lib/src/features/checking/services/checking_android_bridge.dart`
- `lib/src/features/checking/services/location_catalog_service.dart`
- `lib/src/features/checking/controller/checking_controller.dart`
- `lib/src/features/checking/view/checking_screen.dart`

Arquitetura interna atual:

- `CheckingApp`: monta o tema e o gate de apresentacao inicial;
- `CheckingScreen`: UI principal;
- `CheckingController`: regra de negocio, lifecycle, sincronizacao, automacao e persistencia;
- `CheckingStorageService`: persistencia local em `SharedPreferences` + `FlutterSecureStorage`;
- `CheckingApiService`: cliente HTTP com validacao de HTTPS e fallback de dominio;
- `LocationCatalogService`: banco SQLite local das localizacoes;
- `CheckingAndroidBridge`: ponte com Android nativo para agendamentos e acoes pendentes.

### 6.4 Estado persistido

O app persiste localmente:

- `chave`;
- configuracoes especificas de check-in e check-out;
- `registro` sugerido na UI;
- projeto usado no check-in;
- horarios e dias de agendamento;
- flags de agendamento;
- `locationSharingEnabled`, `autoCheckInEnabled` e `autoCheckOutEnabled`;
- `lastMatchedLocation`, `lastDetectedLocation`, `lastLocationUpdateAt` e `lastCheckInLocation`.

Separadamente, o catalogo de localizacoes fica em SQLite local.

Detalhes importantes:

- a chave compartilhada da API vai para `FlutterSecureStorage`;
- o restante fica em `SharedPreferences`;
- `lastCheckIn` e `lastCheckOut` nao sao persistidos; sao recarregados pela API;
- o estado inicial usa `CheckingPresetConfig` para URL base e chave compartilhada;
- nao existe fila offline local nem retry persistente para envios que falham.

### 6.5 Configuracao embutida

`CheckingPresetConfig` aponta hoje para:

- endpoint principal: `https://tscode.com.br`;
- fallback: `https://www.tscode.com.br`;
- chave compartilhada placeholder: `change-mobile-app-shared-key`.

O app tambem exige HTTPS ao validar a URL base.

Na UI atual, essa configuracao e tratada como configuracao interna do aplicativo. O usuario final ve a informacao na tela de ajustes, mas nao a edita por formulario, embora o controller tenha setters para isso.

### 6.6 Fluxo funcional da UI

Na tela principal, o usuario consegue:

- informar `Chave Petrobras`;
- escolher `Check-In` ou `Check-Out`;
- escolher `Informe` (`Normal` ou `Retroativo`);
- escolher projeto em caso de check-in (`P80`, `P82`, `P83`);
- disparar `REGISTRAR`;
- abrir o painel de agendamento;
- abrir a folha de automatizacao por localizacao;
- sincronizar historico manualmente.

O historico exibido no topo mostra:

- ultimo check-in;
- ultimo check-out.

O controller tambem ajusta automaticamente a sugestao de proxima acao com base nesses dois horarios.

Nos ajustes, o app exibe:

- dias da semana e horarios de notificacao;
- switches de agendamento para check-in e check-out;
- preview dos dados usados em cada acao;
- card de integracao com a API;
- botao de sincronizacao manual.

Na folha de localizacao, o app exibe:

- switch `Compartilhar Localizacao`;
- switch `Check-In Automatico`;
- switch `Check-Out Automatico`;
- ultima atualizacao recebida;
- tabela das localizacoes monitoradas.

### 6.7 Como o app conversa com a API

#### Consulta de estado

`CheckingApiService.fetchState()` chama:

- `GET /api/mobile/state?chave=...`

com header `x-mobile-shared-key`.

#### Catalogo de localizacoes

`CheckingApiService.fetchLocations()` chama:

- `GET /api/mobile/locations`

com o mesmo header de autenticacao mobile.

#### Envio de evento

`CheckingApiService.submitEvent()` chama hoje:

- `POST /api/mobile/events/forms-submit`

com payload contendo:

- `chave`;
- `projeto`;
- `action`;
- `informe`;
- `client_event_id`;
- `event_time` convertido para UTC no cliente HTTP;
- `local` opcional.

Isso significa que, no estado atual, o app Flutter nao usa `events/sync` nem `events/submit` no fluxo principal. Ele usa o endpoint que atualiza estado e tambem enfileira a submissao ao Forms.

### 6.8 Controle e sincronizacao no app

`CheckingController` faz o seguinte:

1. carrega estado local;
2. carrega o catalogo de localizacoes salvo em SQLite;
3. inicializa a ponte Android nativa;
4. sincroniza agendamentos nativos;
5. se houver configuracao de API, baixa `GET /api/mobile/locations` e atualiza o SQLite local;
6. se houver chave valida e configuracao de API, busca historico remoto;
7. inicia refresh automatico do historico a cada `5s`;
8. se o compartilhamento de localizacao estiver ativo, tenta reativar o monitoramento na proxima abertura do app.

Ao enviar um evento:

- valida `chave` e configuracao de API;
- gera `client_event_id` com prefixo `flutter-` ou `flutter-auto`;
- chama a API;
- aplica o estado remoto retornado;
- atualiza a mensagem de status.

### 6.9 Integracao Android nativa

O app tem um `MethodChannel` chamado `checking/android`.

Hoje essa ponte serve principalmente para agendamento/notificacao:

- Flutter envia `syncSchedules`;
- Android salva configuracao de agenda em `SharedPreferences` nativo;
- `ScheduledNotificationReceiver` agenda alarmes com `AlarmManager`;
- quando chega o horario, o Android mostra uma notificacao com acao `Sim` / `Nao`;
- ao tocar `Sim`, o app abre e entrega uma acao nativa pendente para o Flutter (`Check-In` ou `Check-Out`);
- o controller consome essa acao e chama o mesmo fluxo de envio pela API.

Tambem existe `BootCompletedReceiver` para restaurar alarmes apos reboot ou update do pacote.

Importante: nao existe hoje um servico Kotlin proprio de geofence ou de stream de localizacao. A automacao por localizacao roda no Flutter, usando `geolocator`, e o nativo fica concentrado em notificacoes/agendamentos e entrega de intents ao app.

### 6.10 Automacao por localizacao

O app Flutter tambem faz automacao baseada em proximidade e afastamento.

Fluxo atual:

1. o usuario abre o painel de localizacao pelo icone na tela principal;
2. ativa `Compartilhar Localizacao`;
3. o app exige localizacao precisa, permissao foreground e permissao background;
4. com permissoes concedidas, o controller inicia `Geolocator.getPositionStream(...)`;
5. no Android, o stream usa `AndroidSettings` com `intervalDuration=1 minuto` e `ForegroundNotificationConfig` para manter a coleta;
6. leituras com precisao pior que `30m` sao ignoradas;
7. cada leitura e comparada com o catalogo SQLite de localizacoes;
8. ao entrar em uma area valida, o app busca o estado remoto e decide a proxima acao automatica;
9. ao sair de todas as areas monitoradas, o app pode disparar checkout automatico por afastamento.

Regras importantes:

- o calculo de range e circular, com centro em `latitude/longitude` e raio em `tolerance_meters`;
- nomes `Zona de Checkout 1` ate `Zona de Checkout 5` sao tratados como zonas logicas de checkout;
- qualquer outra localizacao cadastrada e tratada como area de check-in;
- se o usuario ja esta em check-in e entra em outra area de check-in diferente da ultima registrada, o app pode reenviar check-in para atualizar o local;
- se o usuario estiver fora do range de todas as areas e a distancia minima passar de `1000m`, o app pode enviar checkout automatico;
- eventos automaticos usam o mesmo endpoint mobile e podem carregar `local=<nome da localizacao>`.

### 6.11 Limites e cuidados reais do app Flutter

Alguns pontos precisam ficar claros porque a nomenclatura pode sugerir algo maior do que o codigo atual entrega:

- nao existe geofence nativa por cerca persistente no sistema operacional;
- nao existe fila offline persistente para reenviar eventos que falharam;
- o catalogo de localizacoes e comum; a separacao entre entrada e saida depende do nome logico da localizacao e do estado remoto atual do usuario;
- a frequencia de `1 minuto` e configurada no stream Android, mas ainda depende das restricoes de bateria e politicas do sistema;
- a configuracao de API mostrada na tela e somente informativa na UI atual.

Portanto, a automacao atual combina dois modos:

- horario/notificacao para agendamentos;
- localizacao precisa para automacao por proximidade e afastamento.

## 7. Relacao entre API, admin e app Flutter

### 7.1 Ponto de integracao principal

O elo entre os tres blocos e o conjunto `users` + `user_sync_events` + `check_events`.

- a API grava e reconcilia esses dados;
- o website admin le e administra esses dados;
- o app Flutter consulta e altera esses dados via `/api/mobile/*`.

### 7.2 Como o admin reflete eventos do app Flutter

Sempre que o canal mobile aceita um evento relevante, o backend chama `notify_admin_data_changed(...)`.

Isso alimenta o SSE do painel, que por sua vez dispara novo carregamento das tabelas.

O mesmo mecanismo e usado pelas mudancas administrativas de localizacao, entao o painel reflete tanto eventos mobile quanto alteracoes do catalogo consumido pelo app Flutter.

### 7.3 Caso tipico de usuario criado pelo app antes do RFID

Fluxo suportado hoje:

1. usuario usa o app com uma `chave` ainda sem RFID cadastrado;
2. backend cria usuario placeholder com `rfid=NULL`;
3. painel admin passa a enxergar esse usuario na lista de usuarios cadastrados;
4. um admin pode depois vincular o RFID ao mesmo cadastro, reaproveitando a `chave` unica.

Esse e um caso importante de interoperabilidade entre mobile e operacao com cartao.

## 8. Arquivos mais importantes para manutencao

### 8.1 API

- `sistema/app/main.py`
- `sistema/app/core/config.py`
- `sistema/app/models.py`
- `sistema/app/routers/device.py`
- `sistema/app/routers/mobile.py`
- `sistema/app/routers/admin.py`
- `sistema/app/services/user_sync.py`
- `sistema/app/services/forms_queue.py`

### 8.2 Website admin

- `sistema/app/static/admin/index.html`
- `sistema/app/static/admin/app.js`
- `sistema/app/static/admin/styles.css`

### 8.3 App Flutter

- `checking_android_new/pubspec.yaml`
- `checking_android_new/lib/src/app/checking_app.dart`
- `checking_android_new/lib/src/features/checking/checking_preset_config.dart`
- `checking_android_new/lib/src/features/checking/controller/checking_controller.dart`
- `checking_android_new/lib/src/features/checking/models/managed_location.dart`
- `checking_android_new/lib/src/features/checking/services/checking_services.dart`
- `checking_android_new/lib/src/features/checking/services/checking_android_bridge.dart`
- `checking_android_new/lib/src/features/checking/services/location_catalog_service.dart`
- `checking_android_new/lib/src/features/checking/view/checking_screen.dart`
- `checking_android_new/android/app/src/main/AndroidManifest.xml`
- `checking_android_new/android/app/src/main/kotlin/com/br/checking/BootCompletedReceiver.kt`
- `checking_android_new/android/app/src/main/kotlin/com/br/checking/GeoActionContract.kt`
- `checking_android_new/android/app/src/main/kotlin/com/br/checking/MainActivity.kt`
- `checking_android_new/android/app/src/main/kotlin/com/br/checking/ScheduledNotificationReceiver.kt`

## 9. Resumo operacional

Em termos praticos:

- a API e o website admin formam um unico backend deployado automaticamente;
- o website admin ja cobre autenticacao, cadastro, localizacoes, auditoria e arquivos de eventos;
- o app Flutter ja fala com a API e usa principalmente `/api/mobile/state`, `/api/mobile/locations` e `/api/mobile/events/forms-submit`;
- a automacao do app Flutter hoje combina horario/notificacao e localizacao por proximidade/afastamento, mas sem geofence nativa do sistema;
- o app Flutter ainda nao tem fila offline persistente para retry de envio;
- a secao de localizacoes do painel admin agora persiste no backend e abastece um banco SQLite local no app Flutter.

Esse e o estado atual mais importante para qualquer manutencao, integracao futura ou separacao do app Flutter para um repositorio proprio.