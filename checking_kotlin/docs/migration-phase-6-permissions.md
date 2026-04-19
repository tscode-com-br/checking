# Migração Kotlin - Fase 6 Permissões E Configurações

Atualizado em: 2026-04-19

## Objetivo

Implementar os fluxos Android runtime necessários antes da captura real de
localização: localização precisa, localização em segundo plano, notificações,
otimização de bateria e orientação OEM.

## Entregue

- `MainActivity` registra launchers de permissão runtime e settings do Android.
- O switch `Compartilhar Localização` solicita localização precisa, acesso em
  2º plano, notificações e otimização de bateria antes de habilitar o estado.
- A sheet de configurações passou a acionar:
  - `Acesso em 2º plano`
  - `Permitir notificações`
  - `Sem restrições de bateria`
  - `Ativar Auto-Start`
- `CheckingPermissionSnapshot` centraliza o retrato das permissões Android.
- `CheckingPermissionSettingsState` agora é alimentado por permissões reais.
- `canEnableLocationSharing` é derivado de serviço de localização, permissão
  precisa, acesso em 2º plano e notificações.
- Ao voltar do foreground, permissões são relidas e switches dependentes voltam
  para off se permissões forem revogadas.
- O helper OEM foi portado para Xiaomi/Redmi/Poco/HyperOS, Samsung e Motorola.

## Limites Desta Fase

- A fase 6 não captura GPS nem inicia stream de localização; isso começa na
  Fase 7.
- A automação real em foreground service continua para a Fase 8.
- Validação em dispositivo físico Android 13, 14 e 15+ permanece no escopo da
  Fase 10.

## Validação

Executado em 2026-04-19:

```powershell
.\gradlew.bat testDebugUnitTest --rerun-tasks
.\gradlew.bat assembleDebug
.\gradlew.bat lintDebug
```

Resultado: todos passaram.
