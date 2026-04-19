# Fase 10 - Testes de Paridade

## Objetivo

Fortalecer a migração Flutter -> Kotlin com testes automatizados cobrindo os pontos de maior risco antes da etapa de release: estado legado, automação de localização, ViewModel, permissões Android, Room real e baseline visual Compose.

## Entregue

- Cenários unitários adicionais em `CheckingStateTest`, cobrindo restauração de JSON legado, flags de automação/OEM, histórico antigo sem coordenadas e regra de timestamps remotos não persistidos.
- Cenários unitários adicionais em `CheckingLocationLogicTest`, cobrindo reentrada em local monitorado, troca entre locais, checkout fora de range maior que 2 km, check-in próximo ao trabalho e limite de 10 entradas no histórico de localização.
- Cenários unitários adicionais em `CheckingRuntimeLogicTest`, cobrindo decisão de refresh após submit e interatividade dos toggles de automação.
- `CheckingViewModelTest` com `kotlinx-coroutines-test`, dispatcher principal controlado e `DataStore` fake em memória para validar inicialização, normalização/sync da chave, submissão manual e revogação de permissões.
- `CheckingManifestParityTest` instrumentado para validar permissões sensíveis, `foregroundServiceType=location`, `stopWithTask=false` e receiver de boot/update.
- `CheckingDatabaseInstrumentedTest` instrumentado com Room real para validar DAO e migração 1 -> 2 preservando rows legadas e adicionando `coordinates_json`.
- `CheckingComposeBaselineTest` instrumentado como baseline visual/semântico da splash, tela principal e sheet de automação.

## Limites conhecidos

- `assembleDebugAndroidTest` compila o APK de testes instrumentados, mas não executa os testes em aparelho.
- Ainda é obrigatório rodar `connectedDebugAndroidTest` em dispositivos físicos ou em uma matriz confiável com Android 13, 14 e 15+.
- A validação manual de localização em background continua indispensável, porque o comportamento real depende de fabricante, política de bateria, permissões e estado bloqueado/desbloqueado do aparelho.
- Como o Kotlin permanece com `applicationId` separado (`com.br.checkingnative`), upgrade in-place sobre o app Flutter publicado segue fora do caminho atual; a migração coberta é por simulação de banco/prefs e onboarding manual.

## Validação em 2026-04-19

```powershell
.\gradlew.bat testDebugUnitTest --rerun-tasks
.\gradlew.bat assembleDebugAndroidTest
.\gradlew.bat assembleDebug
.\gradlew.bat lintDebug
```

Resultado local:

- `testDebugUnitTest --rerun-tasks`: passou com 59 testes.
- `assembleDebugAndroidTest`: passou, compilando os testes instrumentados.
- `assembleDebug`: passou.
- `lintDebug`: passou.
