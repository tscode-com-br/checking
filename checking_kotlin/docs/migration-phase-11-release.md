# Fase 11 - Release

## Objetivo

Preparar o projeto Kotlin para gerar artefatos de release com o mesmo rigor do app Flutter: versionamento definido, AAB assinado, R8/minify, shrink de recursos, arquivamento de mapping e preflight antes de publicação.

## Decisões aplicadas

- Versão alvo local: `1.4.1+16`, alinhada ao `pubspec.yaml` atual do Flutter de referência.
- Identidade mantida conforme Fase 1: `applicationId` e namespace continuam como `com.br.checkingnative`.
- Release Play Store exige upload key real via `keystore.properties`; não há fallback para assinatura debug.
- `release` agora usa `minifyEnabled=true`, `shrinkResources=true` e `proguard-android-optimize.txt`.
- O AAB final deve arquivar o `mapping.txt` do R8 em `build/release-artifacts/<versionName>+<versionCode>/`.

## Arquivos adicionados

- `keystore.properties.example`
- `scripts/create-upload-keystore.ps1`
- `scripts/build-play-aab.ps1`
- `scripts/play-release-preflight.ps1`
- `scripts/release-artifact-utils.ps1`
- `docs/google-play-submission-checklist.md`
- `docs/google-play-console-content.md`

## Fluxo de release

1. Copiar `keystore.properties.example` para `keystore.properties`.
2. Preencher `storePassword`, `keyAlias` e `keyPassword` com valores reais.
3. Garantir que `storeFile` aponta para a upload key real, por padrão `keys/checking-upload-keystore.jks`.
4. Rodar o preflight:

```powershell
pwsh ./scripts/play-release-preflight.ps1 -BuildName 1.4.1 -BuildNumber 16
```

5. Para gerar somente o AAB depois de checks já feitos:

```powershell
pwsh ./scripts/build-play-aab.ps1 -BuildName 1.4.1 -BuildNumber 16 -SkipQualityChecks
```

## Validações obrigatórias fora do build local

- Executar `connectedDebugAndroidTest` em Android 13, 14 e 15+:

```powershell
pwsh ./scripts/play-release-preflight.ps1 -BuildName 1.4.1 -BuildNumber 16 -RunConnectedTests
```

- Validar manualmente:
  - fresh install
  - fluxo de chave/API
  - permissões de localização precisa, background e notificações
  - serviço em foreground com tela bloqueada
  - reinício após reboot/update
  - automação de check-in/check-out em campo

## Observações de upgrade

O Kotlin continua como app separado (`com.br.checkingnative`). Assim, não existe upgrade in-place real sobre o Flutter publicado (`com.br.checking`) nesta configuração.

Se a decisão mudar para substituir o Flutter publicado:

1. Trocar `applicationId` e namespace para `com.br.checking`.
2. Usar a mesma upload key do app publicado.
3. Instalar uma build Flutter antiga e atualizar por cima com o Kotlin.
4. Validar migração de banco/prefs reais, permissões e persistência de estado.

## Estado local em 2026-04-19

- Infraestrutura de release implementada.
- `testDebugUnitTest --rerun-tasks`: passou.
- `assembleDebug`: passou.
- `assembleDebugAndroidTest`: passou.
- `lintDebug`: passou.
- `:app:minifyReleaseWithR8`: passou, validando R8/shrink de release.
- `bundleRelease`: bloqueou corretamente sem `keystore.properties`, com erro de `storeFile` ausente.
- Geração do AAB assinado depende de `keystore.properties` e upload key real, que não devem ser versionados.
