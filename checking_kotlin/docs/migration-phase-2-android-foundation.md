# Migracao Kotlin - Fase 2 Fundacao Android

Atualizado em: 2026-04-19

## Objetivo

Preparar o app Kotlin separado para receber os fluxos Android nativos que o
Flutter ja usa: permissoes sensiveis, receivers, notificacoes, intent de acao
e service de localizacao em foreground.

Esta fase nao implementa ainda a captura real de GPS nem a automacao em
background. Esses comportamentos ficam para as fases seguintes.

## Manifest

Permissoes declaradas em `app/src/main/AndroidManifest.xml`:

- `INTERNET`
- `ACCESS_NETWORK_STATE`
- `ACCESS_COARSE_LOCATION`
- `ACCESS_FINE_LOCATION`
- `ACCESS_BACKGROUND_LOCATION`
- `POST_NOTIFICATIONS`
- `FOREGROUND_SERVICE`
- `FOREGROUND_SERVICE_LOCATION`
- `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`
- `WAKE_LOCK`
- `RECEIVE_BOOT_COMPLETED`

Configuracoes de application:

- `applicationId` permanece `com.br.checkingnative`
- `namespace` permanece `com.br.checkingnative`
- `usesCleartextTraffic="false"`
- `allowBackup="false"`
- backup/cloud transfer desabilitados por `backup_rules.xml` e `data_extraction_rules.xml`

Componentes declarados:

- `CheckingLocationForegroundService`
- `NotificationActionReceiver`
- `ScheduledNotificationReceiver`
- `BootCompletedReceiver`
- `MainActivity` com `launchMode="singleTask"`

## Codigo Nativo Adicionado

Arquivos adicionados:

- `GeoActionContract.kt`
- `NotificationActionReceiver.kt`
- `BootCompletedReceiver.kt`
- `ScheduledNotificationReceiver.kt`
- `CheckingLocationForegroundService.kt`

Arquivos atualizados:

- `MainActivity.kt`
- `app/build.gradle.kts`
- `BootstrapUiState.kt`
- `BootstrapViewModel.kt`

## Dependencia Android

Foi adicionada a dependencia:

```kotlin
implementation("com.google.android.gms:play-services-location:21.3.0")
```

Ela prepara o projeto para a fase de localizacao nativa, mantendo a versao ja
usada como referencia no projeto Android do Flutter.

## Limites Desta Fase

Ainda nao implementado:

- request runtime de permissoes
- stream foreground de localizacao
- foreground service funcional com notificacao persistente
- restart automatico de monitoramento apos boot/update
- automacao de Check-In/Check-Out por localizacao
- ViewModel funcional equivalente ao `CheckingController`

O service `CheckingLocationForegroundService` e propositalmente um placeholder
compilavel. Ele esta declarado no manifest para estabilizar a fundacao Android,
mas a logica real de execucao sera adicionada na fase de localizacao/background.

## Criterio De Saida

Fase 2 e considerada concluida quando:

- manifest Kotlin contem as permissoes Android equivalentes ao Flutter
- componentes nativos base existem e compilam
- `applicationId` separado continua preservado
- build/testes Kotlin passam
- documentacao da fase registra o que foi e o que nao foi implementado

Status atual:

- manifest atualizado
- componentes nativos adicionados
- dependencia de localizacao adicionada
- `testDebugUnitTest`, `assembleDebug` e `lintDebug` validados
- lint permanece com 0 erros e 18 warnings conhecidos
- pronto para Fase 3
