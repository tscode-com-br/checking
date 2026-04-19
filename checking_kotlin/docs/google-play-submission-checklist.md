# Google Play Submission Checklist - Kotlin

Use este checklist para publicar a versão Kotlin `1.4.1+16` com menos risco.

## 1) Artefato de release

- [ ] `keystore.properties` existe com valores reais, sem `change-me`.
- [ ] Upload keystore existe no caminho configurado, por padrão `keys/checking-upload-keystore.jks`.
- [ ] `testDebugUnitTest --rerun-tasks` passou.
- [ ] `lintDebug` passou.
- [ ] `assembleDebugAndroidTest` passou.
- [ ] Testes instrumentados foram executados em Android 13, 14 e 15+.
- [ ] AAB assinado gerado em `app/build/outputs/bundle/release/app-release.aab`.
- [ ] `mapping.txt` do R8 arquivado em `build/release-artifacts/1.4.1+16/r8-mapping/mapping.txt`.

Comando sugerido:

```powershell
pwsh ./scripts/play-release-preflight.ps1 -BuildName 1.4.1 -BuildNumber 16 -RunConnectedTests
```

## 2) Identidade e versão

- [ ] Package name confirmado: `com.br.checkingnative`.
- [ ] Versão confirmada: `versionName=1.4.1`, `versionCode=16`.
- [ ] Decisão de coexistência revisada antes de upload.

Se o Kotlin substituir o Flutter publicado, não publique como `com.br.checkingnative`; primeiro mude para `com.br.checking`, use a upload key correta e rode teste de upgrade real.

## 3) Release notes

Template pt-BR:

```text
Nova versão nativa Kotlin do Checking para registro de Check-In e Check-Out.
Inclui envio manual, sincronização de histórico, automação por localização e melhorias de estabilidade.
```

Template en-US opcional:

```text
New native Kotlin version of Checking for Check-In and Check-Out workflows.
Includes manual submission, history sync, location automation and stability improvements.
```

## 4) Store listing

- [ ] Ícone 512x512.
- [ ] Feature graphic 1024x500.
- [ ] Pelo menos 2 screenshots de telefone.
- [ ] Screenshot da tela principal.
- [ ] Screenshot do painel de automação/localização.
- [ ] Descrição curta.
- [ ] Descrição completa.
- [ ] Email de suporte.
- [ ] URL pública de política de privacidade.

## 5) Privacidade e Data Safety

Mapear no Play Console:

- Dados de localização: usados para detectar presença operacional e automação de check-in/check-out quando habilitada.
- Identificador operacional/chave de usuário: usado para sincronizar histórico e enviar eventos para a API.
- Dados enviados por rede: eventos de check-in/check-out, projeto, tipo de registro, informe, local operacional quando aplicável e timestamps.
- Criptografia em trânsito: HTTPS obrigatório; cleartext desabilitado.
- Compartilhamento de dados: responder conforme política real do backend/empresa.
- Exclusão de dados: documentar canal de suporte e procedimento real.

## 6) Permissões sensíveis

- [ ] Declaração de background location preenchida.
- [ ] Justificativa do uso em segundo plano: automação operacional mesmo com app fora da tela.
- [ ] Instruções de teste para revisor:

```text
1. Abra o app e informe uma chave de usuário válida.
2. Abra o painel de automação por localização.
3. Ative busca por localização e automação.
4. Conceda localização precisa, localização em segundo plano e notificações.
5. Mova o aparelho para dentro/fora de uma área cadastrada e valide os eventos.
```

## 7) Validação em dispositivo

- [ ] Android 13: notificações e background location.
- [ ] Android 14: foreground service location e permissões.
- [ ] Android 15+: restrições atuais de background/FGS.
- [ ] App fechado: serviço permanece de acordo com configuração.
- [ ] Reboot: receiver restaura serviço quando habilitado.
- [ ] Bateria/OEM: Xiaomi/HyperOS, Samsung e Motorola revisados quando disponível.

## 8) Fluxo Play Console

1. Criar release em Internal testing.
2. Subir `app-release.aab`.
3. Subir `mapping.txt` correspondente.
4. Adicionar release notes.
5. Resolver avisos de pre-launch report.
6. Validar com testers internos.
7. Promover gradualmente quando os fluxos críticos estiverem estáveis.

