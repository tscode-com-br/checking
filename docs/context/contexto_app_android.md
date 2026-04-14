# Contexto do Aplicativo Android

## 1. Escopo

Este documento descreve apenas o aplicativo Android do projeto Checking.

- Pasta do app: `checking_android`
- Tipo de projeto: Tauri 2 para Android
- Identificador do app: `com.br.checkincheckout`
- Versao atual observada: `0.6.0`

O app Android nao e apenas uma interface web empacotada. Ele combina tres camadas:

1. frontend em HTML, CSS e JavaScript executado em WebView;
2. backend em Rust exposto por comandos Tauri;
3. camada Android nativa em Kotlin para notificacoes, permissoes e geolocalizacao em background.

## 2. Objetivo funcional do app

O aplicativo executa o fluxo de Check-In e Check-Out operacional para o usuario final. Ele suporta tres formas de disparo:

1. acao manual pelo botao na interface;
2. notificacoes agendadas;
3. geolocalizacao com automacao assistida ou automatica.

O envio operacional principal continua baseado na automacao do Microsoft Forms. Depois da confirmacao do envio, o app tambem sincroniza o evento com a API do sistema.

## 3. Arquitetura do app

### 3.1 Frontend WebView

Arquivos principais:

- `checking_android/src/index.html`
- `checking_android/src/styles.css`
- `checking_android/src/main.js`
- `checking_android/src/app-config.js`

Responsabilidades do frontend:

- renderizar a interface;
- persistir estado local no `localStorage`;
- validar dados antes da automacao;
- disparar os comandos Tauri;
- integrar com a bridge Android quando ela existir;
- sincronizar historico com a API mobile.

Pontos relevantes no codigo:

- estado principal salvo em `petro_state_v4`;
- fila local de sync da API em `checking_api_sync_queue_v1`;
- pendencia de sync de retorno do Forms em `checking_forms_pending_sync_v1`;
- entrada principal da automacao em `executarAutomacao(...)`;
- bridge Android resolvida por `obterBridgeAndroid()`;
- notificacoes nativas sincronizadas por `sincronizarAgendamentosNativos(...)`.

### 3.2 Backend Rust via Tauri

Arquivos principais:

- `checking_android/src-tauri/src/lib.rs`
- `checking_android/src-tauri/src/main.rs`
- `checking_android/src-tauri/tauri.conf.json`

Responsabilidades do Rust:

- expor o comando `preencher_forms` ao frontend;
- abrir e controlar a navegacao do WebView para o Microsoft Forms;
- injetar o script de preenchimento e envio;
- devolver o app para a home com resultado em query string, como `forms=submitted` ou `forms=timeout`.

O frontend nao envia diretamente o formulario. Ele monta o payload e delega o envio ao comando Rust.

### 3.3 Camada Android nativa

Arquivos principais:

- `checking_android/src-tauri/gen/android/app/src/main/java/com/br/checkincheckout/MainActivity.kt`
- `checking_android/src-tauri/gen/android/app/src/main/java/com/br/checkincheckout/BackgroundLocationService.kt`
- `checking_android/src-tauri/gen/android/app/src/main/java/com/br/checkincheckout/ScheduledNotificationReceiver.kt`
- `checking_android/src-tauri/gen/android/app/src/main/java/com/br/checkincheckout/NotificationActionReceiver.kt`
- `checking_android/src-tauri/gen/android/app/src/main/java/com/br/checkincheckout/GeoActionContract.kt`

Responsabilidades do Android nativo:

- hospedar o WebView Tauri;
- solicitar permissoes do Android;
- expor a `AndroidBridge` ao JavaScript;
- manter monitoramento de localizacao em foreground service;
- agendar notificacoes exatas com `AlarmManager`;
- reenviar a acao para o JavaScript quando o app for reaberto por notificacao ou evento de geo.

## 4. Pipeline central de Check-In e Check-Out

Todo fluxo converge para o mesmo pipeline:

1. um gatilho define a acao final, `Check-In` ou `Check-Out`;
2. o frontend chama `executarAutomacao(registroForcado, metadata)`;
3. o frontend valida chave, estado e trava anti-duplicidade;
4. o frontend invoca `preencher_forms` via Tauri;
5. o backend Rust abre o Forms, injeta o script e tenta o envio;
6. o app retorna para a home com status do resultado;
7. o frontend atualiza historico local e processa a sincronizacao com a API.

Esse ponto e importante: Android nativo nao faz a automacao do Forms sozinho. Ele entrega o gatilho e o frontend continua sendo a autoridade do fluxo funcional.

## 5. Gatilhos suportados

### 5.1 Manual

O usuario preenche os dados na tela e aciona o botao de registrar. O frontend escolhe o tipo de registro atual e chama `executarAutomacao(...)`.

### 5.2 Notificacao agendada

Quando a bridge Android existe, o frontend agenda notificacoes nativas. O fluxo normal e:

1. a UI salva horario e dias;
2. o frontend sincroniza os agendamentos com Android;
3. o Android agenda alarmes exatos;
4. no horario correto, uma notificacao e mostrada;
5. a confirmacao do usuario reabre a `MainActivity`;
6. a activity repassa a acao ao JavaScript;
7. o JavaScript executa a automacao.

Sem bridge Android, o app usa o plugin `@tauri-apps/plugin-notification` como fallback.

### 5.3 Geolocalizacao

Quando a bridge Android esta disponivel, o app trata o Android como autoridade da geolocalizacao. O frontend ainda pode manter geo para UI e fallback, mas a decisao operacional fica no servico nativo.

Comportamento implementado no Android:

- monitoramento em foreground service;
- buffer de leituras;
- confirmacao por leituras consecutivas;
- histerese para entrada e saida;
- descarte de leitura com baixa precisao;
- cooldown entre transicoes automaticas.

Quando o app esta em background, a estrategia preferencial e transformar a transicao em notificacao interativa para evitar depender de abertura silenciosa da activity.

## 6. Persistencia local e configuracao

O aplicativo salva o estado no `localStorage`. Entre os campos persistidos estao:

- chave do usuario;
- informe;
- projeto;
- tipo de registro selecionado;
- horarios agendados e dias permitidos;
- configuracao de geolocalizacao;
- URL base da API;
- chave compartilhada mobile;
- historico local de ultimo Check-In e ultimo Check-Out.

Arquivo de preset:

- `checking_android/src/app-config.js`

Configuracao observada no preset atual:

- `apiBaseUrl` padrao apontando para `https://tscode.com.br`;
- lista de fallbacks para dominio alternativo e IPs do servidor;
- `apiSharedKey` inicial placeholder, esperado para substituicao por valor real.

## 7. Integracao do app com a API

O app Android nao depende apenas do Forms. Ele tambem conversa com a API Python para sincronizar o estado consolidado do usuario.

Contratos usados pelo app:

- `GET /api/mobile/state`
- `POST /api/mobile/events/sync`

Comportamento esperado:

1. o app executa a automacao do Forms;
2. ao confirmar envio bem-sucedido, enfileira ou envia a sincronizacao para a API;
3. usa `client_event_id` para evitar duplicidade;
4. mantem fila local de retry se a API estiver indisponivel;
5. consulta o estado remoto para atualizar `Ultimo Check-In` e `Ultimo Check-Out`.

Essa integracao usa `apiBaseUrl` e `apiSharedKey` configurados no proprio aplicativo.

## 8. Build e execucao

Arquivo de configuracao Tauri:

- `checking_android/src-tauri/tauri.conf.json`

Caracteristicas observadas:

- `productName`: `checkincheckout`
- `identifier`: `com.br.checkincheckout`
- `frontendDist`: `../src`
- bundle ativo com icones em `checking_android/src-tauri/icons`

Dependencias JavaScript do app:

- `@tauri-apps/api`
- `@tauri-apps/plugin-notification`
- `@tauri-apps/cli` como dependencia de desenvolvimento

Fluxo usual de execucao a partir de `checking_android`:

```bash
npm run tauri -- android dev
```

Fluxo usual de build:

```bash
npm run tauri -- android build
```

No workspace atual, tambem existe a task VS Code `Run Checking Android App`, que sobe o emulador e executa `npx tauri android dev`.

## 9. Estrutura Android gerada

O codigo Android nativo esta em:

- `checking_android/src-tauri/gen/android`

Pontos importantes:

- esse diretorio faz parte do fluxo mobile do Tauri;
- ha arquivos gerados e arquivos customizados misturados no projeto Android;
- alteracoes em Kotlin, Manifest e Gradle sao possiveis, mas devem ser feitas com cautela porque parte da estrutura vem do pipeline gerado pelo Tauri.

Configuracao Android observada na documentacao existente do app:

- `minSdk = 24`
- `compileSdk = 36`
- `targetSdk = 36`
- uso de `play-services-location` para geolocalizacao nativa

## 10. Permissoes e recursos nativos

O app depende de permissoes Android para entregar o comportamento esperado:

- notificacoes;
- localizacao fina e aproximada;
- localizacao em background;
- foreground service de localizacao;
- alarmes exatos;
- wake lock.

Sem essas permissoes, os sintomas mais provaveis sao:

- notificacoes nao disparando;
- geolocalizacao sem transicoes em segundo plano;
- falhas em agendamentos exatos;
- automacao dependente apenas de uso manual.

## 11. Arquivos mais importantes para manutencao

Se a manutencao for apenas no app Android, estes sao os arquivos que merecem leitura primeiro:

1. `checking_android/src/main.js` para regras de negocio, estado local, bridge Android e sync com API.
2. `checking_android/src/app-config.js` para preset de endpoints e chave mobile.
3. `checking_android/src-tauri/src/lib.rs` para a automacao do Forms.
4. `checking_android/src-tauri/gen/android/app/src/main/java/com/br/checkincheckout/MainActivity.kt` para ciclo de vida, intents e entrega da acao ao JavaScript.
5. `checking_android/src-tauri/gen/android/app/src/main/java/com/br/checkincheckout/BackgroundLocationService.kt` para geofence, confirmacao e cooldown.
6. `checking_android/src-tauri/gen/android/app/src/main/java/com/br/checkincheckout/ScheduledNotificationReceiver.kt` para alarmes e notificacoes agendadas.

## 12. Riscos e cuidados tecnicos

Os principais pontos de atencao neste app sao:

1. o envio depende da compatibilidade do Microsoft Forms com o script injetado pelo Rust;
2. alteracoes no frontend podem quebrar o contrato esperado pela bridge Android;
3. alteracoes na camada Android podem afetar reentrega de eventos quando a activity e reaberta;
4. permissoes e politicas de background do Android influenciam diretamente geolocalizacao e notificacoes;
5. a integracao com a API deve preservar idempotencia por `client_event_id` e comportamento offline com fila local.

## 13. Referencias internas do proprio app

Para aprofundar somente no aplicativo Android, os documentos mais uteis dentro de `checking_android/docs` sao:

- `checking_android/docs/android-context.md`
- `checking_android/docs/fluxos-checkin.md`

Este arquivo existe para fornecer um contexto isolado do app Android dentro da pasta central de contextos do repositorio.