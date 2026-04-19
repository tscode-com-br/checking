# Checking Kotlin

Projeto Android nativo em Kotlin criado para coexistir com o app Flutter atual.

## Decisões

- modo de coexistência: app separado
- pasta de trabalho: `checking_kotlin`
- application id: `com.br.checkingnative`
- namespace: `com.br.checkingnative`
- migração a partir do Flutter: onboarding manual
- stack base:
  - Jetpack Compose
  - Hilt
  - Room
  - DataStore

## Estado atual

- Fase 3 concluída: persistência, cache local e onboarding manual endurecidos
- scaffold Android nativo criado
- tela inicial de bootstrap pronta
- DI, banco local e preferências já conectados
- manifest com permissões Android sensíveis declaradas
- receivers nativos de boot, notificações e ações preparados
- service placeholder de localização em foreground declarado
- Room versionado sem destructive migration
- cache DataStore para catálogo de localizações
- baseline da migração documentado em `docs/migration-phase-0-baseline.md`
- decisão de identidade documentada em `docs/migration-phase-1-identity.md`
- fundação Android documentada em `docs/migration-phase-2-android-foundation.md`
- persistência documentada em `docs/migration-phase-3-persistence.md`

## Comandos

```powershell
.\gradlew.bat assembleDebug
.\gradlew.bat testDebugUnitTest
```

## Próximos passos

1. Implementar ViewModel/controller funcional equivalente ao Flutter.
2. Conectar envio manual, sync de histórico e sync de catálogo à API.
3. Substituir a UI de bootstrap pela tela funcional em Compose.
