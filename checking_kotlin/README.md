# Checking Kotlin

Projeto Android nativo em Kotlin criado para coexistir com o app Flutter atual.

## Decisões da Fase 0

- modo de coexistência: app separado
- pasta de trabalho: `checking_kotlin`
- application id: `com.br.checkingnative`
- namespace: `com.br.checkingnative`
- stack base:
  - Jetpack Compose
  - Hilt
  - Room
  - DataStore

## Estado atual

- Fase 1 iniciada
- scaffold Android nativo criado
- tela inicial de bootstrap pronta
- DI, banco local e preferências já conectados em modo placeholder

## Comandos

```powershell
.\gradlew.bat assembleDebug
.\gradlew.bat testDebugUnitTest
```

## Próximos passos

1. Portar os modelos do Flutter para Kotlin.
2. Implementar migração do estado legado.
3. Reescrever a camada de domínio e localização.

