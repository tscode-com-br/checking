# Contexto Detalhado da API Checking

## 1. Objetivo deste documento

Este documento consolida o estado real da API do projeto Checking com base no código atual do repositório, validado em **17/04/2026**.

O foco é servir como base para:

- manutenção do backend FastAPI;
- entendimento dos contratos consumidos por ESP32, app Flutter e webpage pública;
- evolução de novas webpages, incluindo a futura `https://www.tscode.com.br/checking/transport`.

Este contexto é mais confiável que os documentos antigos quando houver divergência, porque foi montado a partir de:

- `sistema/app/main.py`
- `sistema/app/models.py`
- `sistema/app/schemas.py`
- `sistema/app/routers/*.py`
- `sistema/app/services/*.py`
- `tests/test_api_flow.py`

## 2. Visão geral da API atual

Hoje o backend é um único serviço FastAPI que faz ao mesmo tempo:

1. expõe a API operacional em `/api/*`;
2. serve a webpage administrativa em `/admin`;
3. serve a webpage pública de usuário em `/user`;
4. coordena banco, auditoria, fila do Microsoft Forms e atualizações em tempo real do admin.

### 2.1 Estado real das páginas servidas pelo FastAPI

No código atual:

- a página administrativa é servida em `/admin`;
- a página pública de usuário é servida em `/user`;
- os assets compartilhados ficam em `/assets`;
- não existe ainda uma montagem de página em `/transport`.

### 2.2 Inferência de produção

Inferência a partir das URLs informadas no projeto:

- `https://www.tscode.com.br/checking/admin/`
- `https://www.tscode.com.br/checking/user/`

Em produção, o FastAPI provavelmente está publicado atrás de um proxy reverso com prefixo `/checking`. No código Python, porém, as rotas nativas continuam sendo `/admin`, `/user` e `/api/*`.

### 2.3 Routers atualmente registrados

Em `sistema/app/main.py`, a aplicação inclui estes routers:

- `health`
- `device`
- `mobile`
- `web_check`
- `admin`

Ou seja, a API já está organizada em cinco domínios funcionais:

- saúde da aplicação;
- dispositivo RFID;
- app mobile;
- web pública;
- administração.

## 3. Arquivos mais importantes para entender a API

- `sistema/app/main.py`: bootstrap, middlewares, routers e montagem das páginas estáticas.
- `sistema/app/core/config.py`: configuração central carregada via `.env`.
- `sistema/app/database.py`: engine SQLAlchemy, `SessionLocal` e dependência `get_db()`.
- `sistema/app/models.py`: tabelas principais.
- `sistema/app/schemas.py`: contratos de entrada e saída.
- `sistema/app/routers/device.py`: endpoints do ESP32.
- `sistema/app/routers/mobile.py`: endpoints do app Flutter/Android.
- `sistema/app/routers/web_check.py`: endpoints da webpage pública atual (`/user`).
- `sistema/app/routers/admin.py`: autenticação admin, CRUD, listagens, eventos e SSE.
- `sistema/app/services/user_sync.py`: reconciliação de estado entre canais.
- `sistema/app/services/forms_submit.py`: lógica compartilhada para canais que atualizam estado e também enfileiram Forms.
- `sistema/app/services/forms_queue.py`: fila persistente e worker em thread.
- `sistema/app/services/forms_worker.py`: automação real do Microsoft Forms via Playwright.

## 4. Configuração central da API

As configurações estão em `sistema/app/core/config.py` e usam `pydantic-settings`.

Parâmetros mais importantes:

- `APP_ENV`: por padrão `development`.
- `DATABASE_URL`: por padrão `sqlite:///./checking.db`.
- `TZ_NAME`: por padrão `Asia/Singapore`.
- `DEVICE_SHARED_KEY`: chave do canal ESP32.
- `MOBILE_APP_SHARED_KEY`: chave do canal mobile.
- `ADMIN_SESSION_SECRET`: segredo de assinatura da sessão administrativa.
- `ADMIN_SESSION_MAX_AGE_SECONDS`: duração da sessão admin.
- `BOOTSTRAP_ADMIN_KEY`, `BOOTSTRAP_ADMIN_NAME`, `BOOTSTRAP_ADMIN_PASSWORD`: seed do primeiro administrador.
- `FORMS_URL`: URL do Microsoft Forms.
- `FORMS_TIMEOUT_SECONDS`: timeout de navegação/interação.
- `FORMS_MAX_RETRIES`: número máximo de tentativas do worker do Forms.
- `FORMS_QUEUE_ENABLED`: habilita ou não o worker assíncrono da fila.
- `EVENT_ARCHIVES_DIR`: diretório dos CSVs arquivados.

### 4.1 Timezone operacional

A API trabalha no timezone definido por `TZ_NAME`, hoje `Asia/Singapore`.

Isso impacta diretamente:

- normalização de `event_time`;
- comparação de ações no mesmo dia;
- cálculo de inatividade;
- regras de reenvio ou não para o Forms.

## 5. Lifecycle da aplicação

No `lifespan` do FastAPI, o backend:

1. garante a existência do diretório de arquivos arquivados de eventos;
2. executa `Base.metadata.create_all()` apenas em `development`;
3. cria o admin bootstrap de forma idempotente;
4. inicia o worker da fila do Forms quando `FORMS_QUEUE_ENABLED=true`.

No shutdown:

- o worker da fila é encerrado.

## 6. Middlewares e exposição HTTP

### 6.1 CORS

O backend usa `CORSMiddleware` com `allow_origin_regex` para origens locais:

- `localhost`
- `127.0.0.1`
- `tauri.localhost`

`allow_credentials=False`, o que é compatível com a maior parte dos fluxos atuais porque:

- admin roda no mesmo domínio do backend;
- mobile usa header próprio, não cookies de navegador.

### 6.2 Sessão administrativa

O backend usa `SessionMiddleware` do Starlette.

Configuração atual relevante:

- cookie assinado por `ADMIN_SESSION_SECRET`;
- `same_site="lax"`;
- `https_only=False`.

Observação importante:

- no código atual o cookie admin não está marcado com `Secure` por padrão.

## 7. Modelo de dados principal

### 7.1 `users`

Tabela de estado operacional atual do funcionário.

Campos mais relevantes:

- `id`
- `rfid` único e anulável
- `chave` única, 4 caracteres alfanuméricos
- `nome`
- `projeto`
- `local`
- `checkin`
- `time`
- `last_active_at`
- `inactivity_days`

Ponto importante:

- `rfid` pode ser `NULL`, permitindo que mobile ou web criem o usuário antes do vínculo do cartão.

### 7.2 `pending_registrations`

Armazena RFIDs lidos e ainda não cadastrados.

Campos:

- `rfid` único
- `first_seen_at`
- `last_seen_at`
- `attempts`

### 7.3 `check_events`

É a trilha de auditoria do sistema.

Campos relevantes:

- `idempotency_key` única
- `source`
- `action`
- `status`
- `message`
- `details`
- `project`
- `device_id`
- `local`
- `request_path`
- `http_status`
- `ontime`
- `event_time`
- `submitted_at`
- `retry_count`

Essa tabela registra eventos de:

- device
- mobile
- web
- forms
- admin

### 7.4 `device_heartbeats`

Registra heartbeat do dispositivo.

Ponto importante:

- o código atual grava um novo registro a cada heartbeat; não há upsert por `device_id`.

### 7.5 `forms_submissions`

Fila persistente para envio assíncrono ao Microsoft Forms.

Campos relevantes:

- `request_id` único
- `rfid`
- `action`
- `chave`
- `projeto`
- `device_id`
- `local`
- `ontime`
- `status`
- `retry_count`
- `last_error`
- `created_at`
- `updated_at`
- `processed_at`

### 7.6 `locations`

Catálogo administrativo de localizações monitoradas.

Campos:

- `local`
- `latitude`
- `longitude`
- `coordinates_json`
- `tolerance_meters`

Ponto importante:

- o modelo suporta múltiplas coordenadas por local via `coordinates_json`;
- `latitude` e `longitude` continuam existindo como coordenada principal para compatibilidade.

### 7.7 `mobile_app_settings`

Tabela de configuração global relacionada a localização.

Campos:

- `location_update_interval_seconds`
- `location_accuracy_threshold_meters`
- `coordinate_update_frequency_json`

Ponto importante:

- no código atual, a API usa ativamente apenas `location_accuracy_threshold_meters`;
- os outros campos existem no banco, mas ainda não são expostos de forma funcional pelas rotas atuais.

### 7.8 `user_sync_events`

Histórico canônico dos eventos aplicados ao usuário.

Campos relevantes:

- `user_id`
- `chave`
- `rfid`
- `source`
- `action`
- `projeto`
- `local`
- `ontime`
- `event_time`
- `source_request_id`
- `device_id`

Restrição importante:

- unicidade por `source + source_request_id`.

### 7.9 `admin_users`

Tabela de administradores aprovados.

Campos relevantes:

- `chave`
- `nome_completo`
- `password_hash`
- `requires_password_reset`
- `approved_by_admin_id`
- `approved_at`
- `password_reset_requested_at`

### 7.10 `admin_access_requests`

Tabela de solicitações pendentes para virar administrador.

## 8. Serviços transversais da API

### 8.1 `time_utils.py`

Fornece `now_sgt()` e sempre usa o timezone operacional configurado.

### 8.2 `event_logger.py`

Padroniza a escrita em `check_events`.

Detalhes importantes:

- se `source="device"` e `action` for `checkin` ou `checkout`, `ontime` vira `True` por default;
- `commit=True` já persiste no banco e publica atualização SSE com motivo `event`;
- os textos são truncados para caber nas colunas.

### 8.3 `admin_updates.py`

Mantém o broker de SSE do admin.

Comportamento:

- cada assinante ganha uma `asyncio.Queue(maxsize=20)`;
- se a fila encher, o item mais antigo é descartado;
- o payload publicado contém `reason` e `emitted_at`.

### 8.4 `user_sync.py`

É um dos serviços mais importantes da aplicação.

Responsabilidades:

- normalizar chave do usuário;
- normalizar `event_time` para o timezone operacional;
- criar usuários placeholder oriundos do app ou da web;
- aplicar estado atual em `users`;
- criar `user_sync_events`;
- reconstruir o estado consolidado do usuário;
- decidir se uma nova ação deve ou não reenfileirar o Forms.

#### 8.4.1 Nomes placeholder já usados pela API

- app mobile: `Oriundo do Aplicativo`
- web pública: `Oriundo da Web`

#### 8.4.2 Regra de reenvio ao Forms

`should_enqueue_forms_for_action()` retorna `False` quando:

- a ação nova é igual à última ação;
- e ambas caem no mesmo dia de Singapura.

Nesses casos a API atualiza o estado, mas não cria novo envio ao Forms.

#### 8.4.3 Resolução do estado mais recente

`resolve_latest_user_activity()` considera três fontes:

1. `user_sync_events`
2. `users`
3. fallback em `check_events`

Na prática:

- o evento mais recente vence;
- em empate de horário, `user_sync_events` ganha prioridade sobre `users`, e `users` ganha prioridade sobre `check_events`.

### 8.5 `forms_submit.py`

Encapsula um padrão reutilizável para canais que:

1. recebem um evento;
2. atualizam estado do usuário;
3. gravam `user_sync_events`;
4. enfileiram Forms quando necessário;
5. retornam o estado consolidado.

Hoje esse padrão já é usado por:

- `/api/mobile/events/forms-submit`
- `/api/web/check`

O serviço usa a estrutura `FormsSubmitChannel`, que define:

- rótulo do evento;
- nome da origem em `user_sync_events`;
- origem do log;
- `request_path`;
- `device_id`;
- `default_local`.

Isso é uma excelente base para futuras webpages, inclusive `transport`.

### 8.6 `forms_queue.py`

Implementa a fila assíncrona do Forms.

Comportamento atual:

- grava submissões com `status="pending"`;
- worker reserva o próximo item e marca `processing`;
- processa até 10 itens por ciclo;
- se nada foi processado, espera `0.25s`;
- atualiza o item para `success` ou `failed`;
- escreve auditoria em `check_events` com `source="forms"`.

### 8.7 `forms_worker.py`

Executa o Microsoft Forms com Playwright.

Fluxo de alto nível:

1. abre a URL do Forms;
2. digita e confirma a chave;
3. marca `normal` ou `retroativo`;
4. marca `checkin` ou `checkout`;
5. em `checkin`, escolhe o projeto;
6. envia;
7. espera o XPath de sucesso.

Erros tratados explicitamente:

- timeout de etapa específica;
- falha de validação da etapa;
- erro de validação de projeto;
- erro runtime do Playwright.

### 8.8 `location_matching.py`

Concentra a lógica de geolocalização da webpage pública.

Regras importantes:

- usa distância haversine;
- considera múltiplas coordenadas por local;
- separa locais normais de zonas de checkout;
- reconhece nomes de checkout por regex `^zona de checkout(?: \\d+)?$`, case-insensitive;
- quando o local é zona de checkout, o `resolved_local` final vira `Zona de CheckOut`;
- quando o usuário fica a mais de `2000m` do local de trabalho mais próximo, o status vira `outside_workplace`.

### 8.9 `location_settings.py`

Hoje expõe na prática apenas:

- leitura do `location_accuracy_threshold_meters`;
- atualização desse valor pelo admin.

### 8.10 `event_archives.py`

Gera CSVs com os eventos correntes, lista arquivos, baixa individualmente, compacta todos em ZIP e remove arquivos arquivados.

## 9. Superfície HTTP atual da API

### 9.1 Health

#### `GET /api/health`

Sem autenticação.

Resposta:

```json
{
  "status": "ok",
  "app": "checking-sistema"
}
```

### 9.2 Canal do dispositivo RFID

#### 9.2.1 `POST /api/device/heartbeat`

Payload:

```json
{
  "device_id": "ESP32-S3-01",
  "shared_key": "..."
}
```

Comportamento:

- valida `DEVICE_SHARED_KEY`;
- se a chave estiver errada, registra auditoria e retorna JSON de erro;
- se a chave estiver correta, grava uma linha em `device_heartbeats`.

Resposta típica de sucesso:

```json
{
  "ok": true,
  "led": "white"
}
```

Observação importante:

- mesmo com chave inválida, o endpoint não lança `401`; ele retorna JSON com `ok: false`.

#### 9.2.2 `POST /api/scan`

Payload:

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

Resposta (`ScanResponse`):

- `outcome`
- `led`
- `message`

Valores possíveis de `outcome`:

- `submitted`
- `pending_registration`
- `invalid_key`
- `duplicate`
- `failed`
- `local_updated`

Fluxo real:

1. valida a chave compartilhada do dispositivo;
2. verifica duplicidade por `request_id` em `check_events`;
3. registra o recebimento do scan;
4. procura usuário por RFID;
5. se não encontrar, cria ou atualiza `pending_registrations`;
6. se encontrar, resolve a atividade atual do usuário;
7. se for `checkout` sem atividade anterior, bloqueia;
8. se for repetição da mesma ação no mesmo dia, atualiza apenas o estado/local;
9. caso contrário, atualiza estado e enfileira Forms;
10. grava `user_sync_events` com `source="rfid"`;
11. publica atualização para o admin.

Regras importantes:

- RFID desconhecido não cria usuário automaticamente;
- `checkout` sem atividade anterior retorna `failed` com LED `red_2s`;
- repetição da mesma ação no mesmo dia retorna `local_updated`;
- duplicidade por `request_id` retorna `duplicate`;
- a resposta ao ESP32 sai antes do processamento do Forms terminar.

### 9.3 Canal mobile

Autenticação:

- header obrigatório `x-mobile-shared-key`;
- valor deve bater com `MOBILE_APP_SHARED_KEY`.

Em caso de falha:

- a API registra auditoria e responde `401`.

#### 9.3.1 `GET /api/mobile/state?chave=...`

Retorna o estado consolidado do usuário:

- `found`
- `chave`
- `nome`
- `projeto`
- `current_action`
- `current_event_time`
- `current_local`
- `last_checkin_at`
- `last_checkout_at`

Esse endpoint é consumido pelo app Flutter para sincronizar a visão atual do usuário.

#### 9.3.2 `GET /api/mobile/locations`

Retorna:

- lista de localizações monitoradas;
- múltiplas coordenadas por local;
- `location_accuracy_threshold_meters`;
- `synced_at`.

Esse endpoint não retorna hoje:

- `location_update_interval_seconds`;
- `coordinate_update_frequency_json`.

#### 9.3.3 `POST /api/mobile/events/sync`

Objetivo:

- sincronizar estado com o backend sem passar pelo fluxo genérico de Forms compartilhado.

Comportamento:

- idempotência por `UserSyncEvent(source="android", source_request_id=client_event_id)`;
- cria usuário placeholder se necessário;
- aplica estado no usuário;
- grava `user_sync_events`;
- registra auditoria;
- notifica o admin.

#### 9.3.4 `POST /api/mobile/events/submit`

Objetivo:

- aplicar estado e enfileirar Forms quando necessário.

Diferenças para `events/forms-submit`:

- recebe `action`, `projeto`, `local`, `event_time`, `client_event_id`;
- não recebe `informe`;
- `ontime` fica implícito como `True`.

#### 9.3.5 `POST /api/mobile/events/forms-submit`

É o endpoint mais importante para o app Flutter atual.

Payload:

```json
{
  "chave": "SRG1",
  "projeto": "P82",
  "action": "checkin",
  "local": "Base P80",
  "informe": "normal",
  "event_time": "2026-04-06T08:00:00+08:00",
  "client_event_id": "flutter-1234567890"
}
```

Comportamento:

- usa a infraestrutura compartilhada de `submit_forms_event()`;
- cria usuário placeholder `Oriundo do Aplicativo` se necessário;
- converte `informe` em `ontime`;
- aplica estado;
- decide se reenfileira ou não o Forms;
- grava `user_sync_events` com `source="android_forms"`;
- retorna o estado consolidado.

Regra importante de local:

- se `local` vier vazio, o default é `Aplicativo`.

### 9.4 Canal web público atual

O domínio público atual está em `sistema/app/routers/web_check.py` e abastece a webpage servida em `/user`.

Essas rotas são públicas:

- não usam sessão admin;
- não usam header compartilhado mobile;
- hoje não possuem autenticação adicional.

#### 9.4.1 `GET /api/web/check/state?chave=...`

Retorna histórico público resumido:

- `found`
- `chave`
- `projeto`
- `current_action`
- `current_local`
- `last_checkin_at`
- `last_checkout_at`

Diferença para o endpoint mobile:

- não retorna `nome`.

#### 9.4.2 `GET /api/web/check/locations`

Retorna apenas uma lista de nomes de localizações:

```json
{
  "items": [
    "Escritório Principal",
    "Zona de Checkout 1"
  ]
}
```

Esse endpoint existe para o fallback manual de local no frontend da página `/user`.

#### 9.4.3 `POST /api/web/check/location`

Payload:

```json
{
  "latitude": 1.255936,
  "longitude": 103.611066,
  "accuracy_meters": 8
}
```

Resposta:

- `matched`
- `resolved_local`
- `label`
- `status`
- `message`
- `accuracy_meters`
- `accuracy_threshold_meters`
- `nearest_workplace_distance_meters`

Status possíveis:

- `matched`
- `accuracy_too_low`
- `not_in_known_location`
- `outside_workplace`
- `no_known_locations`

Regras importantes:

- se a precisão estiver acima do limite configurado, a API bloqueia antes do matching;
- se não houver local conhecido dentro do raio, mas o usuário ainda estiver a até `2000m` do local de trabalho mais próximo, o status é `not_in_known_location`;
- se estiver a mais de `2000m`, o status vira `outside_workplace`;
- zonas de checkout são reconhecidas pelo nome e devolvem `resolved_local="Zona de CheckOut"`.

#### 9.4.4 `POST /api/web/check`

Payload:

```json
{
  "chave": "WB11",
  "projeto": "P82",
  "action": "checkin",
  "local": "Web Match P80",
  "informe": "normal",
  "event_time": "2026-04-17T08:00:00+08:00",
  "client_event_id": "web-check-1234567890"
}
```

Comportamento:

- usa `submit_forms_event()` como o canal mobile Forms;
- cria usuário placeholder `Oriundo da Web` se necessário;
- grava `user_sync_events` com `source="web_forms"`;
- usa `default_local="Web"` quando `local` não é informado;
- decide automaticamente se o evento reenfileira ou não o Forms.

### 9.5 Canal administrativo

Autenticação:

- sessão por cookie;
- `admin_user_id` guardado em `request.session`.

#### 9.5.1 Rotas de sessão e autenticação

- `POST /api/admin/auth/login`
- `POST /api/admin/auth/logout`
- `GET /api/admin/auth/session`
- `POST /api/admin/auth/request-access`
- `POST /api/admin/auth/request-password-reset`

Regras importantes:

- login usa `chave + senha`;
- se o admin estiver com recadastro pendente, o login é bloqueado;
- pedidos de acesso viram linha em `admin_access_requests`;
- pedido de recadastro remove a senha atual e exige que outro admin defina uma nova.

#### 9.5.2 `GET /api/admin/stream`

SSE protegido por sessão.

Comportamento:

- envia `{"reason":"connected"}` na conexão;
- envia keep-alive a cada 15 segundos quando não houver eventos;
- recebe publicações do broker em memória.

#### 9.5.3 Rotas de gestão de administradores

- `GET /api/admin/administrators`
- `POST /api/admin/administrators/requests/{request_id}/approve`
- `POST /api/admin/administrators/requests/{request_id}/reject`
- `POST /api/admin/administrators/{admin_id}/revoke`
- `POST /api/admin/administrators/{admin_id}/set-password`

Regras importantes:

- não é permitido revogar o próprio acesso;
- não é permitido remover o último admin ativo;
- `set-password` só funciona se `requires_password_reset=true`.

#### 9.5.4 Rotas de presença e operação

- `GET /api/admin/checkin`
- `GET /api/admin/checkout`
- `GET /api/admin/missing-checkout`
- `GET /api/admin/inactive`
- `GET /api/admin/pending`
- `GET /api/admin/users`

Comportamentos importantes:

- `checkin` e `checkout` mostram apenas usuários não inativos;
- `missing-checkout` mostra usuários cujo último evento ativo foi `checkin` e já virou o dia em Singapura;
- `inactive` usa inatividade por dias úteis, com limiar atual de 3 dias úteis;
- antes dessas listagens, a API sincroniza `inactivity_days` em `users`.

#### 9.5.5 CRUD de localizações

- `GET /api/admin/locations`
- `POST /api/admin/locations`
- `POST /api/admin/locations/settings`
- `DELETE /api/admin/locations/{location_id}`

Regras importantes:

- nome de local é único;
- cada local precisa ter ao menos uma coordenada;
- múltiplas coordenadas são persistidas em `coordinates_json`;
- o ajuste atual exposto em `locations/settings` é apenas `location_accuracy_threshold_meters`.

#### 9.5.6 CRUD de usuários e pendências

- `POST /api/admin/users`
- `DELETE /api/admin/pending/{pending_id}`
- `DELETE /api/admin/users/{user_id}`

Regras importantes do `POST /api/admin/users`:

- cria novo usuário por RFID;
- edita usuário existente por `user_id`;
- pode vincular RFID a um usuário já criado por mobile/web quando a mesma `chave` existir com `rfid=NULL`;
- impede conflito de `chave`;
- impede trocar arbitrariamente o RFID de um usuário que já tenha outro cartão;
- remove a pendência correspondente do RFID quando existir.

#### 9.5.7 Eventos e arquivamento

- `GET /api/admin/events`
- `POST /api/admin/events/archive`
- `GET /api/admin/events/archives`
- `GET /api/admin/events/archives/download-all`
- `GET /api/admin/events/archives/{file_name}`
- `DELETE /api/admin/events/archives/{file_name}`

Detalhes importantes:

- `GET /api/admin/events` oculta os eventos com `action="event_archive"`;
- o limite atual é de 200 eventos;
- o arquivamento gera CSV, limpa a tabela ativa e depois registra o próprio evento de arquivamento;
- a listagem de arquivos aceita filtro textual `q` e paginação (`page`, `page_size`).

## 10. Regras de negócio mais importantes

### 10.1 Normalização de chave

Sempre que a API normaliza `chave`, ela:

- faz `strip()`;
- converte para maiúsculas.

### 10.2 Idempotência por canal

#### Device

- duplicidade por `request_id` em `check_events`.

#### Mobile sync

- duplicidade por `UserSyncEvent(source="android", source_request_id=client_event_id)`.

#### Mobile submit / web check

- duplicidade primeiro por `UserSyncEvent(source específico, source_request_id=client_event_id)`;
- e também por `FormsSubmission.request_id` ao tentar enfileirar.

### 10.3 Placeholder users

Usuários podem ser criados sem RFID em dois cenários:

- mobile cria `Oriundo do Aplicativo`;
- web cria `Oriundo da Web`.

Depois o admin pode completar o cadastro e vincular o RFID.

### 10.4 Repetição da mesma ação no mesmo dia

Se a última ação e a nova ação forem iguais e estiverem no mesmo dia de Singapura:

- a API atualiza o estado;
- grava `user_sync_events`;
- não cria nova submissão ao Forms.

Isso vale hoje para:

- device
- mobile submit
- mobile forms-submit
- web check

### 10.5 Checkout sem atividade anterior

No canal RFID, um `checkout` é bloqueado quando `resolve_latest_user_activity()` retorna `None`.

### 10.6 `ontime` versus `retroativo`

Para canais que usam `informe`:

- `normal` => `ontime=True`
- `retroativo` => `ontime=False`

Esse valor aparece em:

- `user_sync_events`
- `forms_submissions`
- `check_events`
- respostas do admin

### 10.7 Inatividade

A inatividade é calculada por dias úteis, não por dias corridos.

Limiar atual:

- 3 dias úteis (`INACTIVE_AFTER_BUSINESS_DAYS = 3`)

## 11. Exemplos de contratos importantes

### 11.1 Resposta duplicada do mobile/web

```json
{
  "ok": true,
  "duplicate": true,
  "queued_forms": false,
  "message": "Web check event already submitted",
  "state": {
    "found": true,
    "chave": "WB11",
    "nome": "Oriundo da Web",
    "projeto": "P82",
    "current_action": "checkin",
    "current_event_time": "2026-04-17T08:00:00",
    "current_local": "Web",
    "last_checkin_at": "2026-04-17T08:00:00",
    "last_checkout_at": null
  }
}
```

### 11.2 Resposta de matching de localização

```json
{
  "matched": false,
  "resolved_local": null,
  "label": "Fora do Ambiente de Trabalho",
  "status": "outside_workplace",
  "message": "",
  "accuracy_meters": 8,
  "accuracy_threshold_meters": 25,
  "nearest_workplace_distance_meters": 2150.4
}
```

### 11.3 Resposta de scan RFID válido

```json
{
  "outcome": "submitted",
  "led": "green_1s",
  "message": "Operation accepted and queued for Forms submission"
}
```

### 11.4 Resposta de scan repetido no mesmo dia

```json
{
  "outcome": "local_updated",
  "led": "green_blink_3x_1s",
  "message": "Operation accepted without new Forms submission"
}
```

## 12. Pontos de extensão já prontos para a futura webpage `transport`

Hoje a API já oferece um padrão reaproveitável para criar uma nova webpage pública:

1. uma rota de estado público, similar a `/api/web/check/state`;
2. uma rota principal de submissão baseada em `submit_forms_event()`;
3. criação automática de usuários placeholder quando isso fizer sentido;
4. regras prontas de idempotência e reconciliação de estado;
5. matching de localização já implementado e reutilizável;
6. catálogo administrativo de localizações já pronto e persistido no backend.

### 12.1 Peças mais reaproveitáveis

- `FormsSubmitChannel`
- `submit_forms_event()`
- `ensure_web_user()` ou uma variante nova
- `build_mobile_sync_state()` / `build_web_check_history_state()`
- `resolve_location_match()`
- `resolve_submission_local()`
- `AdminUpdatesBroker` se a nova página também precisar refletir algo no admin

### 12.2 Decisões que ainda precisarão ser definidas para `transport`

- se a página será pública como `/user` ou protegida;
- se vai usar geolocalização;
- se vai usar catálogo de locais existente ou uma regra própria;
- se o usuário criado automaticamente deve ter nome placeholder específico;
- se o canal deve gravar uma origem nova em `user_sync_events`, por exemplo `transport_forms`;
- se a nova página deve ou não enfileirar Microsoft Forms.

## 13. Pontos de atenção do estado atual

### 13.1 Alguns contextos antigos do projeto ficaram desatualizados

Exemplos já verificados no código:

- o admin atual é servido em `/admin`, não em `/`;
- a webpage pública atual existe em `/user`;
- há um router `web_check.py` que não aparece em alguns documentos antigos;
- o backend atual já tem `missing-checkout` e CRUD de localizações com múltiplas coordenadas.

### 13.2 Logs do worker do Forms podem confundir a origem real

No `forms_queue.py`, os eventos finais do worker são gravados com:

- `source="forms"`
- `request_path="/api/scan"`

Isso acontece mesmo quando a submissão veio de mobile ou web. Para depuração futura, esse detalhe é importante.

### 13.3 O canal web público atual não possui autenticação própria

Hoje `/api/web/*` é público. Se `transport` precisar de controle de acesso, isso terá de ser implementado explicitamente.

### 13.4 `mobile_app_settings` já prevê mais configurações do que a API usa hoje

O banco já possui campos para:

- intervalo de atualização;
- frequência por janela de tempo.

Mas o runtime atual só usa de forma prática o limite de precisão da localização.

### 13.5 Timestamps em ambiente local podem aparecer sem offset explícito

Nos testes com SQLite, parte das respostas serializadas aparece sem offset explícito no timestamp. Ainda assim, a lógica da API continua baseada no timezone operacional configurado.

## 14. Resumo executivo

A API atual do Checking já está preparada para operar quatro canais de entrada:

- RFID via ESP32;
- app Android/Flutter;
- webpage pública atual `/user`;
- painel administrativo `/admin`.

Ela centraliza:

- estado atual do usuário;
- histórico canônico por `user_sync_events`;
- auditoria em `check_events`;
- fila assíncrona do Microsoft Forms;
- catálogo persistente de localizações.

Para a futura webpage `transport`, o projeto já possui uma base forte de reaproveitamento no backend. O caminho mais natural é seguir o mesmo padrão hoje usado em `/api/web/check`, criando um novo canal com identidade própria, mas reutilizando a infraestrutura de estado, idempotência, fila e localização já existente.
