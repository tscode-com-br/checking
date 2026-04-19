# Migração Kotlin - Fase 8 Automação Background

Atualizado em: 2026-04-19

## Objetivo

Substituir o stub de serviço por um foreground service nativo capaz de manter a
automação de presença viva em segundo plano, preservando as regras do Flutter.

## Entregue

- `CheckingLocationForegroundService` agora é um service Hilt real, com
  notification channel `Checking em segundo plano`.
- O serviço usa `FusedLocationProviderClient` para stream periódica e captura
  pontual de localização.
- O manifest já mantinha `stopWithTask=false`; o service agora também usa wake
  lock parcial enquanto está ativo.
- `BootCompletedReceiver` reinicia o service em boot, locked boot e update do
  pacote. Se a automação estiver desligada, o próprio service encerra.
- A Activity inicia o service quando busca por localização e automação estão
  ativas, e desliga o stream foreground para evitar leitura duplicada.
- A pausa por período noturno configurado foi aplicada ao tracking nativo.
- O modo noturno pós-checkout pausa o tracking até 06:00 de Singapura e publica
  a mesma mensagem do Flutter.
- A automação em background cobre:
  - check-in ao entrar em local monitorado
  - check-out em zona de checkout
  - check-out fora do range maior que 2 km
  - check-in perto do trabalho sem match exato
- A regra de evitar evento duplicado no mesmo local usa o estado remoto e
  `lastCheckInLocation`, como no Flutter.
- O estado remoto fica em cache por 45 segundos para evitar fetches redundantes.
- `CheckingBackgroundSnapshotRepository` entrega snapshots do service para o
  controller/UI por `SharedFlow`.

## Limites Desta Fase

- A validação real de sobrevivência do service com tela bloqueada ainda precisa
  ser feita em dispositivo físico na Fase 10.
- A UI visual ainda não foi finalizada conforme o Flutter; isso continua na
  Fase 9.
- Testes instrumentados de lifecycle do service ficam para a fase de paridade.

## Validação

Executado em 2026-04-19:

```powershell
.\gradlew.bat testDebugUnitTest --rerun-tasks
.\gradlew.bat assembleDebug
.\gradlew.bat lintDebug
```

Resultado: todos passaram.
