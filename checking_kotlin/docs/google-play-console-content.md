# Google Play Console Content - Kotlin

Use este texto como ponto de partida. Ajuste URLs, contatos e termos conforme a política real da empresa antes do envio.

## Descrição curta

```text
Registro de Check-In e Check-Out com histórico e automação por localização.
```

## Descrição completa

```text
Checking é um aplicativo operacional para registrar Check-In e Check-Out com rapidez.

Recursos principais:
- registro manual de Check-In e Check-Out
- sincronização do histórico do usuário com a API
- atualização de catálogo de locais de trabalho
- automação por localização quando habilitada
- suporte a monitoramento em segundo plano para rotinas operacionais

O aplicativo foi projetado para uso corporativo em rotinas de presença e operação.

Importante:
- recursos de localização dependem da autorização do usuário
- a localização em segundo plano é usada somente quando a automação operacional está habilitada
- o usuário pode desativar a busca por localização no próprio aplicativo
```

## Notas ao revisor

```text
This app supports operational attendance workflows.

Background location is used only when the operator enables location search and Check-In/Check-Out automation. It is required so the app can detect operational area transitions while the app is not visible.

How to test:
1. Open the app and enter a valid 4-character user key.
2. Open the location automation panel.
3. Enable location search and automatic Check-In/Check-Out.
4. Grant precise location, background location and notification permissions.
5. Move into or out of a configured work area and verify the event/status change.

The feature can be disabled from the same location automation panel.
```

## Release notes

```text
Nova versão nativa Kotlin do Checking para registro de Check-In e Check-Out.
Inclui envio manual, sincronização de histórico, automação por localização e melhorias de estabilidade.
```

## Contatos

Preencher no Play Console:

1. Email de suporte
2. URL pública da política de privacidade
3. URL de suporte ou website, se houver

