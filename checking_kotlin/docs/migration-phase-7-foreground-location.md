# Migração Kotlin - Fase 7 Localização Em Foreground

Atualizado em: 2026-04-19

## Objetivo

Ligar o app Kotlin à localização nativa em primeiro plano, mantendo a automação
de background para a Fase 8.

## Entregue

- `play-services-location` já estava presente e passou a ser usado pela
  `MainActivity` via `FusedLocationProviderClient`.
- Ao habilitar a busca por localização, o app solicita uma leitura imediata com
  `getCurrentLocation`.
- Enquanto o app está em foreground e a busca está ativa, a Activity mantém uma
  stream com `requestLocationUpdates`.
- A stream é interrompida no `onPause`, preservando o limite desta fase.
- `CheckingLocationSample` representa uma leitura nativa independente da API do
  Google Play Services.
- `CheckingController.processForegroundLocationUpdate` aplica a leitura ao
  estado da UI.
- Leituras com precisão pior que `locationAccuracyThresholdMeters` são
  descartadas.
- Leituras repetidas dentro de 1 segundo e mesma coordenada são deduplicadas.
- O controller atualiza:
  - `lastDetectedLocation`
  - `lastMatchedLocation`
  - `lastLocationUpdateAt`
  - `locationFetchHistory`, limitada às últimas 10 posições
- Labels especiais mantidos:
  - `Zona de Check-Out`
  - `Fora do Ambiente de Trabalho`
  - `Localização não Cadastrada`

## Limites Desta Fase

- O serviço foreground/background nativo ainda não executa automação; isso é
  Fase 8.
- Eventos automáticos de check-in/check-out ainda não são disparados por esta
  stream foreground.
- Validação real de GPS em aparelho físico continua obrigatória na Fase 10.

## Validação

Executado em 2026-04-19:

```powershell
.\gradlew.bat testDebugUnitTest --rerun-tasks
.\gradlew.bat assembleDebug
.\gradlew.bat lintDebug
```

Resultado: todos passaram.
