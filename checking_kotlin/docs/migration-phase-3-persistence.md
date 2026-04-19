# Migracao Kotlin - Fase 3 Persistencia

Atualizado em: 2026-04-19

## Objetivo

Endurecer a persistencia local do app Kotlin separado antes de implementar
ViewModel funcional, UI final, localizacao e background service.

Esta fase respeita a decisao da Fase 1:

- o app Kotlin continua em `com.br.checkingnative`
- o app Flutter continua em `com.br.checking`
- nao ha leitura automatica do sandbox Flutter
- onboarding manual continua sendo o caminho esperado

## Estado Local Do App

`CheckingStateRepository` continua responsavel pelo estado em DataStore.

Comportamentos preservados:

- estado inicial e semeado quando nao ha estado salvo
- `apiSharedKey` fica fora do JSON persistido de `CheckingState`
- `lastCheckIn` e `lastCheckOut` continuam fora do JSON persistido
- status de onboarding/migracao fica persistido separadamente
- flag de setup Android inicial continua persistida separadamente

Foi adicionado teste cobrindo:

- seed inicial sem `isLoading`
- shared key fora do JSON de estado
- persistencia do status `MANUAL_ONBOARDING_REQUIRED`

## Status De Onboarding Manual

Foi adicionado o status:

```kotlin
MANUAL_ONBOARDING_REQUIRED
```

Ele representa o estado esperado para o app Kotlin separado quando o Flutter
existe ou quando a importacao automatica nao deve ser prometida.

Compatibilidade:

- o valor antigo `automatic_import_blocked` continua sendo aceito na leitura
- ao ler `automatic_import_blocked`, o app normaliza para
  `MANUAL_ONBOARDING_REQUIRED`
- novas gravacoes usam `manual_onboarding_required`

## Banco De Localizacoes

O banco `checking_locations.db` do Kotlin agora usa schema version `2`, alinhado
ao schema logico do Flutter que inclui `coordinates_json`.

Mudancas:

- `CheckingDatabase` passou de version `1` para version `2`
- `fallbackToDestructiveMigration` foi removido
- foi adicionada migracao `1 -> 2`
- a migracao adiciona `coordinates_json` somente se a coluna ainda nao existir

Como o app Kotlin e separado, isso nao migra o banco interno do Flutter. A
vantagem e evitar destruicao desnecessaria do cache proprio do Kotlin quando o
schema evoluir.

## Cache Do Catalogo

Foi criado `ManagedLocationCacheRepository`.

Ele usa DataStore para manter uma copia JSON do catalogo de localizacoes, com a
mesma chave logica herdada do Flutter:

```text
checking_locations_catalog_cache_v1
```

Formato persistido:

- `id`
- `local`
- `latitude`
- `longitude`
- `coordinates_json`
- `tolerance_meters`
- `updated_at`

Comportamento:

- `ManagedLocationRepository.loadLocations(preferCache = true)` retorna cache
  primeiro quando houver cache
- `loadLocations(preferCache = false)` tenta Room primeiro
- se Room falhar, `loadLocations` usa o cache DataStore
- `replaceAll` grava cache e Room
- se Room falhar mas o cache for salvo, a operacao nao perde o catalogo
- se cache e Room falharem juntos, a falha e propagada

Esse comportamento reproduz a robustez do Flutter, que usava SQLite como fonte
principal e SharedPreferences como fallback operacional.

## Arquivos Alterados

Persistencia:

- `CheckingStateRepository.kt`
- `LegacyFlutterMigrationStatus.kt`
- `LegacyFlutterMigrationCoordinator.kt`
- `ManagedLocationCacheRepository.kt`
- `ManagedLocationRepository.kt`

Room:

- `CheckingDatabase.kt`
- `ManagedLocationDao.kt`
- `AppModule.kt`

Testes:

- `CheckingStateRepositoryTest.kt`
- `LegacyFlutterMigrationStatusTest.kt`
- `ManagedLocationCacheRepositoryTest.kt`
- `ManagedLocationRepositoryTest.kt`

Bootstrap/documentacao:

- `BootstrapUiState.kt`
- `BootstrapViewModel.kt`
- `README.md`

## Limites Desta Fase

Ainda nao implementado:

- secure storage nativo para shared key
- request runtime de permissoes Android
- ViewModel/controller funcional equivalente ao Flutter
- sincronizacao real do catalogo pela API via fluxo de UI
- foreground/background location
- UI Compose final

## Criterio De Saida

Fase 3 e considerada concluida quando:

- Room nao usa mais destructive migration
- schema local de localizacoes esta em version `2`
- cache DataStore de localizacoes existe
- repositório de localizacoes consegue cair para cache quando Room falha
- status de onboarding manual esta modelado e testado
- testes/build/lint passam

Status atual:

- Room versionado para `2`
- migracao `1 -> 2` adicionada
- cache de catalogo em DataStore adicionado
- persistencia de estado e status de onboarding testados
- `testDebugUnitTest`, `assembleDebug` e `lintDebug` validados
- lint permanece com 0 erros e 18 warnings conhecidos
- pronto para Fase 4
