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

- Fase 6 concluída: permissões runtime Android e configurações de background
- Fase 5 concluída: API, fluxos manuais e UI Compose funcional
- scaffold Android nativo criado
- tela inicial de bootstrap removida
- tela principal funcional em Compose conectada ao controller
- DI, banco local e preferências já conectados
- manifest com permissões Android sensíveis declaradas
- receivers nativos de boot, notificações e ações preparados
- service placeholder de localização em foreground declarado
- Room versionado sem destructive migration
- cache DataStore para catálogo de localizações
- controller nativo com sync de histórico, refresh de catálogo e envio manual
- ViewModel funcional conectado à UI Compose
- permissões runtime conectadas para localização precisa, localização em segundo plano, notificações Android 13+, bateria e Auto-Start OEM
- lint reduzido de 18 para 2 warnings restantes de Hilt/AGP
- baseline da migração documentado em `docs/migration-phase-0-baseline.md`
- decisão de identidade documentada em `docs/migration-phase-1-identity.md`
- fundação Android documentada em `docs/migration-phase-2-android-foundation.md`
- persistência documentada em `docs/migration-phase-3-persistence.md`
- controller documentado em `docs/migration-phase-4-controller.md`
- UI Compose documentada em `docs/migration-phase-5-compose-ui.md`
- permissões Android documentadas em `docs/migration-phase-6-permissions.md`

## Comandos

```powershell
.\gradlew.bat assembleDebug
.\gradlew.bat testDebugUnitTest
```

## Próximos passos

1. Implementar captura real de localização em foreground.
2. Conectar automação de localização ao foreground service.
3. Validar permissões/background em dispositivo físico Android 13, 14 e 15+.
