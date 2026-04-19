# Migração Kotlin - Fase 9 UI Compose Final

Atualizado em: 2026-04-19

## Objetivo

Recriar a experiência visual do Flutter em Compose, mantendo os fluxos já
validados nas fases de API, permissões e localização.

## Entregue

- `CheckingApp` ganhou a apresentação inicial de 2 segundos com logo, nome do
  app e créditos, como no Flutter.
- Os assets reais `app_icon.png` e `app_icon_3x.png` foram importados em
  `res/drawable-nodpi`.
- A tela principal foi alinhada ao Flutter:
  - logo superior
  - header `Checking` e subtítulo
  - botões GPS e settings
  - histórico de último check-in/check-out
  - status colorido por tom
  - campo `Chave Petrobras`
  - grupos de rádio para registro, informe e projeto
  - botão `REGISTRAR` com loading
- O campo de chave agora:
  - limpa ao tocar quando já há valor
  - aceita apenas 4 caracteres alfanuméricos
  - converte para uppercase
  - fecha foco/teclado ao completar 4 caracteres
- A sheet de automação por localização foi ajustada com handle, switch,
  histórico de localizações, última atualização, frequência e local capturado.
- A sheet de configurações foi ajustada com permissões, switches e seletores.
- A frequência e os horários noturnos agora usam seletores tipo wheel em vez de
  slider/stepper.
- O diálogo de últimas localizações preserva tabela de data, hora e coordenada.
- As cores globais foram aproximadas do `AppTheme` Flutter:
  - primary `#007AFF`
  - surface `#FFFFFF`
  - text/soft/border/success/warning/error equivalentes
- Snackbars, botões desabilitados e spinners foram mantidos em Compose.

## Limites Desta Fase

- A validação visual por screenshot/golden fica para a Fase 10.
- A checagem em aparelhos reais de tamanhos variados também fica para a Fase 10.
- Os fluxos de background permanecem dependentes de validação física com Android
  13, 14 e 15+.

## Validação

Executado em 2026-04-19:

```powershell
.\gradlew.bat testDebugUnitTest --rerun-tasks
.\gradlew.bat assembleDebug
.\gradlew.bat lintDebug
```

Resultado: todos passaram.
