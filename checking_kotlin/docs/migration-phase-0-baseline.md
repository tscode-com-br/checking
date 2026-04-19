# Migracao Kotlin - Fase 0 Baseline

Atualizado em: 2026-04-19

Este documento congela o estado de referencia do app Flutter em
`checking_android_new` e o estado atual do app Kotlin em `checking_kotlin`.
Ele deve ser usado como ponto de controle antes de executar a Fase 1.

## Objetivo Da Fase 0

Estabelecer uma referencia verificavel para que a conversao Kotlin avance sem
perder comportamento do aplicativo Flutter.

Saida esperada desta fase:

- app Flutter atual identificado como fonte de verdade funcional
- app Kotlin atual identificado como base tecnica parcial
- comandos de qualidade registrados
- divergencias de versao, identidade e release registradas
- decisoes que bloqueiam a Fase 1 explicitadas
- criterios de paridade definidos

## Referencia Flutter

Projeto fonte:

- pasta: `checking_android_new`
- nome do app: `Checking`
- applicationId Android: `com.br.checking`
- namespace Android: `com.br.checking`
- versao em `pubspec.yaml`: `1.4.1+16`
- stack: Flutter, Dart, Android nativo via Kotlin para receivers/bridge

Arquivos principais:

- `lib/main.dart`
- `lib/src/app/checking_app.dart`
- `lib/src/features/checking/controller/checking_controller.dart`
- `lib/src/features/checking/view/checking_screen.dart`
- `lib/src/features/checking/services/checking_services.dart`
- `lib/src/features/checking/services/location_catalog_service.dart`
- `lib/src/features/checking/services/checking_location_logic.dart`
- `lib/src/features/checking/services/checking_background_service.dart`
- `lib/src/features/checking/services/checking_android_bridge.dart`
- `android/app/src/main/AndroidManifest.xml`
- `android/app/src/main/kotlin/com/br/checking/*.kt`

Comportamentos que o Kotlin precisa preservar:

- splash/presentation screen com logo e nomes
- tela principal de registro de Check-In/Check-Out
- chave Petrobras com 4 caracteres alfanumericos, uppercase e limpeza ao toque
- selecao de registro, informe e projeto
- envio manual para `POST /api/mobile/events/forms-submit`
- consulta de historico via `GET /api/mobile/state`
- sincronizacao de catalogo via `GET /api/mobile/locations`
- armazenamento de estado local
- armazenamento da shared key com fallback operacional para background
- banco local `checking_locations.db`, tabela `locations`
- fallback de cache do catalogo quando SQLite falha
- busca de localizacao foreground
- foreground service Android para monitoramento em background
- notificacao de servico em background
- permissoes de localizacao precisa, background e notificacoes
- fluxo de ignorar otimizacao de bateria
- orientacoes OEM para Xiaomi/HyperOS, Samsung e Motorola
- automacao de Check-In ao entrar em local monitorado
- automacao de Check-Out em zona de checkout
- automacao de Check-Out fora de todas as areas por mais de 2 km
- automacao de Check-In perto do ambiente de trabalho sem match exato
- pausa por periodo noturno configurado
- modo noturno pos-checkout ate 06:00 no horario de Singapura
- historico das ultimas 10 capturas de localizacao
- labels especiais de localizacao capturada
- sincronizacao de snapshots do background com a UI
- persistencia sequencial para nao perder alteracoes rapidas
- release Android assinado sem fallback debug

## Estado Kotlin Atual

Projeto destino:

- pasta: `checking_kotlin`
- applicationId atual: `com.br.checkingnative`
- namespace atual: `com.br.checkingnative`
- versao atual: `0.1.0`, versionCode `1`
- stack: Android nativo, Kotlin, Jetpack Compose, Hilt, Room, DataStore

Ja existe:

- scaffold Android nativo compilando
- tela de bootstrap em Compose
- Hilt configurado
- DataStore configurado
- Room configurado para catalogo de locais
- modelos principais portados
- cliente API basico portado
- logica pura de automacao/localizacao portadas em grande parte
- testes unitarios de dominio, modelos e API

Ainda nao existe ou esta incompleto:

- UI funcional equivalente ao Flutter
- ViewModel/controller equivalente ao `CheckingController`
- manifest com todas as permissoes sensiveis do Flutter
- foreground location stream
- foreground service de localizacao em background
- receivers de boot/update e notificacao
- fluxo completo de permissoes
- fluxo de bateria/OEM
- migracao real de dados internos do Flutter
- importacao dos assets reais do app
- release assinado e scripts de preflight Kotlin
- cobertura de testes equivalente aos 74 testes Flutter

## Validacoes Executadas

Comandos executados com sucesso em 2026-04-19:

Flutter:

```powershell
flutter analyze
flutter test
```

Resultado:

- `flutter analyze`: sem issues
- `flutter test`: 74 testes passaram

Kotlin:

```powershell
.\gradlew.bat testDebugUnitTest
.\gradlew.bat assembleDebug
.\gradlew.bat lintDebug
```

Resultado:

- `testDebugUnitTest`: sucesso
- `assembleDebug`: sucesso
- `lintDebug`: sucesso
- lint report: 0 erros, 18 warnings nao bloqueantes

Warnings Kotlin conhecidos:

- dependencias AndroidX/Hilt/Gson com versoes mais novas disponiveis
- `android:windowLightStatusBar` com `tools:targetApi="23"` obsoleto porque minSdk ja e 23
- `R.color.black` e `R.color.white` nao usados
- icone adaptativo sem tag monochrome

## Testes De Referencia

O Flutter possui 74 testes passando em `checking_android_new/test/widget_test.dart`.
Eles cobrem estes grupos funcionais:

- tema visual
- sugestao de proximo registro por historico
- sanitizacao e persistencia da chave
- restauracao de flags antigas e novas de automacao
- persistencia de configuracoes de localizacao e periodo noturno
- fallback de secure storage para preferences
- historico de capturas de localizacao
- parsing de catalogo e multiplas coordenadas
- deteccao de zona de checkout
- precisao minima de GPS
- regras de periodo noturno
- modo noturno pos-checkout
- servico background e permissoes Android
- fallback de catalogo quando banco falha
- refresh foreground
- envio manual e automatico
- travamento de UI durante operacoes
- campo de chave na UI
- cenarios de automacao 1 a 5
- checkout fora de range
- nao repeticao de check-in no mesmo local

O Kotlin possui testes unitarios passando para:

- `CheckingState`
- `ManagedLocation`
- `MobileStateResponse`
- `CheckingLocationLogic`
- `CheckingRuntimeLogic`
- `CheckingApiService`

Lacuna de teste atual:

- faltam testes de ViewModel/controller porque o controller funcional ainda nao existe
- faltam testes instrumentados de Room/DataStore real, permissoes e service lifecycle
- faltam testes/snapshots da UI Compose final
- faltam testes de migracao in-place do app Flutter para Kotlin

## Divergencias Encontradas

Identidade do app:

- Flutter publicado/real usa `com.br.checking`
- Kotlin atual usa `com.br.checkingnative`
- isto define se o Kotlin sera upgrade do Flutter ou app separado

Versao:

- `checking_android_new/pubspec.yaml` esta em `1.4.1+16`
- `checking_android_new/README.md` cita `1.2.2+9`
- docs de Play citam `1.0.0+1`
- Kotlin esta em `0.1.0`/`1`

Persistencia:

- Flutter usa `SharedPreferences` e `flutter_secure_storage`
- Kotlin usa `DataStore`
- app separado nao consegue ler sandbox interno do Flutter
- migracao automatica real so e viavel se o package/signature/upgrade forem planejados

Banco local:

- Flutter abre `checking_locations.db` na versao 2
- Kotlin usa Room version 1 no mesmo nome de arquivo
- Kotlin esta com `fallbackToDestructiveMigration(dropAllTables = true)`
- risco: destruir catalogo legado se tentar abrir banco existente sem estrategia de migracao

UI:

- Flutter tem UI final operacional
- Kotlin tem apenas tela de bootstrap/status

Android:

- Flutter declara permissoes, service e receivers
- Kotlin ainda nao declara essas permissoes e componentes

Dispositivo para screenshots:

- `flutter devices` encontrou apenas Windows desktop
- nenhum dispositivo/emulador Android foi detectado nesta execucao
- screenshots em Android real/emulador ficam como item externo antes de release

## Decisoes Resolvidas Na Fase 1

Decisao tomada em 2026-04-19:

- o Kotlin continuara como app separado
- `applicationId` e `namespace` permanecem `com.br.checkingnative`
- o app Flutter de referencia permanece `com.br.checking`
- migracao automatica do sandbox Flutter fica fora de escopo
- onboarding/migracao manual sera o caminho esperado

Detalhes da decisao estao em `docs/migration-phase-1-identity.md`.

Pendencias que continuam para fases futuras:

- definir versao alvo final do Kotlin
- reavaliar `fallbackToDestructiveMigration` antes de release
- decidir armazenamento seguro/fallback da shared key durante a fase de background service

## Criterio De Saida Da Fase 0

Fase 0 e considerada concluida quando:

- este documento existe e foi revisado
- comandos de qualidade foram executados e registrados
- estado Flutter e Kotlin foram comparados
- decisoes pendentes para Fase 1 foram listadas
- screenshots Android foram capturados ou explicitamente marcados como pendencia externa

Status atual:

- documento criado
- validacoes registradas
- divergencias registradas
- screenshots Android pendentes por ausencia de dispositivo/emulador Android
- Fase 1 concluida com a Opcao 2: app Kotlin separado, `com.br.checkingnative`
