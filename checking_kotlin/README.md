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

- Fase 9 concluída: UI Compose final alinhada ao Flutter
- Fase 8 concluída: foreground service nativo com automação de localização em background
- Fase 7 concluída: captura real de localização em foreground com Fused Location Provider
- Fase 6 concluída: permissões runtime Android e configurações de background
- Fase 5 concluída: API, fluxos manuais e UI Compose funcional
- scaffold Android nativo criado
- tela inicial de bootstrap removida
- tela principal funcional em Compose conectada ao controller
- DI, banco local e preferências já conectados
- manifest com permissões Android sensíveis declaradas
- receivers nativos de boot, notificações e ações preparados
- foreground service de localização conectado com notification channel, wake lock e restart por boot/update
- Room versionado sem destructive migration
- cache DataStore para catálogo de localizações
- controller nativo com sync de histórico, refresh de catálogo e envio manual
- ViewModel funcional conectado à UI Compose
- permissões runtime conectadas para localização precisa, localização em segundo plano, notificações Android 13+, bateria e Auto-Start OEM
- stream foreground conectado ao Fused Location Provider quando a busca por localização está ativa
- resolução de local capturado, match de local monitorado, filtro de precisão e deduplicação de leituras
- automação em background para check-in, check-out em zona de checkout, check-out fora de range e check-in próximo ao trabalho
- pausa noturna configurada e modo noturno pós-checkout até 06:00 de Singapura
- snapshots do serviço sincronizados com a UI por `CheckingBackgroundSnapshotRepository`
- splash/presentation de 2s com logo e nomes, usando os assets PNG reais do Flutter
- tela principal Compose com header, botões GPS/settings, histórico, status, chave, grupos de rádio e botão registrar
- bottom sheets de automação/configurações com controles, wheels de frequência/horário e histórico de localizações
- lint reduzido de 18 para 2 warnings restantes de Hilt/AGP
- baseline da migração documentado em `docs/migration-phase-0-baseline.md`
- decisão de identidade documentada em `docs/migration-phase-1-identity.md`
- fundação Android documentada em `docs/migration-phase-2-android-foundation.md`
- persistência documentada em `docs/migration-phase-3-persistence.md`
- controller documentado em `docs/migration-phase-4-controller.md`
- UI Compose documentada em `docs/migration-phase-5-compose-ui.md`
- permissões Android documentadas em `docs/migration-phase-6-permissions.md`
- localização foreground documentada em `docs/migration-phase-7-foreground-location.md`
- automação background documentada em `docs/migration-phase-8-background-automation.md`
- UI Compose final documentada em `docs/migration-phase-9-compose-final.md`

## Comandos

```powershell
.\gradlew.bat assembleDebug
.\gradlew.bat testDebugUnitTest
```

## Próximos passos

1. Portar os cenários restantes dos testes Flutter para Kotlin.
2. Adicionar testes instrumentados/screenshot para a UI Compose final.
3. Validar permissões/background/localização em dispositivo físico Android 13, 14 e 15+.
