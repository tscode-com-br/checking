# Plano De Conversao Do App Flutter Para Kotlin

Atualizado em: 2026-04-24

## Contexto

- App fonte: `checking_android_new`
- App destino: `checking_kotlin`
- Referencias consultadas para este plano:
  - `checking_android_new/pubspec.yaml`
  - `checking_android_new/README.md`
  - `checking_android_new/lib/main.dart`
  - `checking_kotlin/README.md`
  - `checking_kotlin/fases.txt`
  - `checking_kotlin/docs/migration-phase-0-baseline.md`
  - `checking_kotlin/docs/migration-phase-11-release.md`
- Diagnostico atual do repositorio: `checking_kotlin` nao esta mais em estado embrionario. O projeto ja possui stack base definida, fases `0` a `11` documentadas e indicios de implementacao local para arquitetura, persistencia, permissao, localizacao, automacao em background, testes e release.

## Objetivo

Converter o aplicativo Flutter/Dart em `checking_android_new` para um aplicativo Android nativo em Kotlin em `checking_kotlin`, preservando o comportamento operacional critico, fechando as decisoes de identidade e rollout, e deixando o app apto para homologacao de campo e publicacao.

## Leitura Operacional Do Estado Atual

- O app Flutter continua sendo a fonte de verdade funcional.
- O app Kotlin ja esta organizado como projeto Android nativo com Jetpack Compose, Hilt, Room e DataStore.
- A conversao, portanto, deve ser tratada como um processo de consolidacao e validacao de paridade, e nao como um bootstrap do zero.
- O maior ponto de decisao ainda e a identidade do app:
  - manter `com.br.checkingnative` como app separado; ou
  - migrar para `com.br.checking` e substituir o Flutter publicado.
- Essa decisao controla onboarding de usuarios, estrategia de dados, uso da upload key e viabilidade de upgrade in-place.

## Escopo Funcional Minimo A Preservar

- tela inicial e fluxo principal de registro
- armazenamento local de configuracoes e estado
- armazenamento seguro da chave compartilhada e credenciais operacionais
- sincronizacao de historico e catalogo com a API
- banco local para catalogo de localizacoes
- monitoramento de localizacao em foreground
- foreground service para automacao em background
- notificacao persistente do servico
- permissoes sensiveis de localizacao, background e notificacoes
- orientacoes para bateria e restricoes OEM
- regras de automacao de check-in e check-out
- pausa noturna e modo noturno pos-checkout
- sincronizacao de snapshots do background com a UI
- pipeline de release Android assinado sem fallback debug

## Riscos Criticos

- `checking_android_new` e `checking_kotlin` hoje usam identidades de app diferentes.
- Se o Kotlin continuar separado, nao existe migracao automatica do sandbox interno do Flutter; o onboarding sera manual.
- Fluxos de localizacao em background continuam sujeitos a restricoes do Android e de OEMs como Samsung, Motorola e Xiaomi/HyperOS.
- O repositorio mostra divergencia de versao entre documentos do Flutter; a fonte de verdade precisa ser fechada antes do release final.
- Se o background do Kotlin depender apenas de sessao web por cookie, o fluxo funciona com o contrato atual, mas segue menos robusto do que um token nativo dedicado.

## Plano Detalhado

### Fase 0 - Governanca E Decisao De Identidade

Objetivo: fechar a decisao que define se o app Kotlin coexistira com o Flutter ou o substituira.

Atividades:

- confirmar se o package final permanece `com.br.checkingnative` ou muda para `com.br.checking`
- definir se a publicacao sera app separado ou upgrade do app Flutter ja publicado
- confirmar qual upload key sera usada no release Kotlin
- reconciliar a versao alvo entre `pubspec.yaml`, `README.md` e documentos de release

Saida esperada:

- decisao formal de identidade e estrategia de rollout
- versao alvo unica e aprovada
- criterio claro para onboarding manual ou upgrade in-place

Base ja existente no repositorio:

- `checking_kotlin/docs/migration-phase-0-baseline.md`
- `checking_kotlin/docs/migration-phase-1-identity.md`

### Fase 1 - Congelar A Referencia Funcional Do Flutter

Objetivo: garantir que nenhuma funcionalidade critica do Flutter seja perdida durante o fechamento da migracao.

Atividades:

- montar matriz funcional do Flutter por fluxo, tela, regra e integracao
- registrar contratos usados pelo app Flutter com a API
- catalogar comportamentos especiais de localizacao, automacao, historico, persistencia e notificacoes
- usar testes e documentos do Flutter como evidencia de comportamento esperado

Saida esperada:

- matriz de paridade Flutter -> Kotlin validada
- lista de comportamentos obrigatorios, opcionais e divergencias aceitas

Base ja existente no repositorio:

- `checking_android_new/README.md`
- `checking_kotlin/docs/migration-phase-0-baseline.md`

### Fase 2 - Consolidar A Fundacao Android Nativa

Objetivo: garantir que a base tecnica do projeto Kotlin suporta toda a migracao sem retrabalho estrutural.

Atividades:

- confirmar a organizacao do projeto Android nativo
- validar Compose, Hilt, Room, DataStore e configuracao de modulos
- validar namespace, flavors se existirem, build types e assinatura
- revisar manifest, receivers e servicos base

Saida esperada:

- fundacao Android validada como base unica da migracao
- estrutura pronta para suportar UI, runtime Android e background

Base ja existente no repositorio:

- `checking_kotlin/docs/migration-phase-2-android-foundation.md`

### Fase 3 - Portar Persistencia, Seguranca E Dados Locais

Objetivo: substituir as dependencias Flutter de persistencia e armazenamento seguro por equivalentes nativos em Kotlin.

Atividades:

- mapear tudo o que o Flutter grava em `SharedPreferences`, `flutter_secure_storage` e SQLite
- validar equivalencia em DataStore, storage seguro e Room
- definir tratamento para dados que nao podem migrar automaticamente se o app continuar separado
- confirmar cache do catalogo, historico local e snapshots de background

Saida esperada:

- persistencia Kotlin cobre os dados operacionais criticos
- regra de migracao de dados fica explicitada: manual, assistida ou in-place

Base ja existente no repositorio:

- `checking_kotlin/docs/migration-phase-3-persistence.md`

### Fase 4 - Portar Contratos De API, Regras De Controller E Autenticacao

Objetivo: garantir que o app Kotlin fala com a API correta e reproduz as regras centrais do app Flutter.

Atividades:

- listar endpoints, headers, payloads, retries e criterios de erro
- validar estrategia de autenticacao para uso em foreground e background
- conferir regras de controller para envio manual, sincronizacao de historico e refresh de catalogo
- validar idempotencia, consistencia de estado e mensagens de erro ao usuario

Saida esperada:

- servicos Kotlin cobrem os fluxos manuais e automaticos sem regressao de contrato
- comportamento do controller fica alinhado ao Flutter ou divergencias ficam documentadas

Base ja existente no repositorio:

- `checking_kotlin/docs/migration-phase-4-controller.md`

### Fase 5 - Portar Runtime Android Sensivel

Objetivo: fechar tudo o que depende do sistema Android fora da UI comum.

Atividades:

- validar fluxo de permissoes de localizacao precisa, background e notificacoes
- validar orientacoes de bateria, auto-start e restricoes OEM
- confirmar receivers de boot, update e retomada do servico
- verificar restricoes por versao do Android para foreground service de localizacao

Saida esperada:

- app Kotlin consegue orientar e manter o monitoramento conforme as restricoes reais do Android
- lacunas especificas de OEM ficam conhecidas e testaveis

Base ja existente no repositorio:

- `checking_kotlin/docs/migration-phase-6-permissions.md`

### Fase 6 - Portar Localizacao Foreground

Objetivo: garantir que a captura de coordenadas em primeiro plano no Kotlin reproduz o comportamento do Flutter.

Atividades:

- validar Fused Location Provider, frequencia, precisao minima e filtros
- confirmar atualizacao da UI com ultima coordenada, ultimo refresh e historico de capturas
- validar refresh de catalogo associado ao monitoramento ativo

Saida esperada:

- localizacao foreground esta funcional, observavel e coerente com a tela principal

Base ja existente no repositorio:

- `checking_kotlin/docs/migration-phase-7-foreground-location.md`

### Fase 7 - Portar Automacao E Background Service

Objetivo: concluir a parte mais critica da migracao, que e a automacao nativa em segundo plano.

Atividades:

- validar o foreground service de localizacao com notificacao persistente
- confirmar regras de check-in/check-out automatico, inclusive zona de checkout e saida acima do limite de distancia
- validar pausa noturna, modo noturno pos-checkout e retomada apos reboot/update
- validar backoff, tratamento de erro e sincronizacao de snapshots com a UI

Saida esperada:

- o servico Kotlin sustenta o comportamento operacional que justifica a migracao para nativo
- as regras automaticas ficam reproduzidas e observaveis por log, estado e UI

Base ja existente no repositorio:

- `checking_kotlin/docs/migration-phase-8-background-automation.md`

### Fase 8 - Fechar A UI Final Em Compose

Objetivo: concluir a experiencia do usuario no app Kotlin com paridade funcional e visual suficiente para troca operacional.

Atividades:

- validar splash, tela principal, historico, configuracoes, estados vazios e estados de erro
- confirmar controles de chave, projeto, tipo de registro, automacao e monitoramento
- validar consistencia visual com o app Flutter onde a identidade precisar ser preservada
- garantir que a UI reflita o estado real do background service e das permissoes

Saida esperada:

- UI Compose cobre os fluxos criticos do Flutter e expande apenas o que for necessario para o Android nativo

Base ja existente no repositorio:

- `checking_kotlin/docs/migration-phase-5-compose-ui.md`
- `checking_kotlin/docs/migration-phase-9-compose-final.md`

### Fase 9 - Executar Paridade De Testes

Objetivo: trocar conviccao subjetiva por evidencia objetiva de migracao bem-sucedida.

Atividades:

- mapear os testes Flutter relevantes para suites unitarias e instrumentadas no Kotlin
- validar dominio, controller, persistencia, Room, permissoes, lifecycle do servico e UI Compose
- rodar `assembleDebug`, `testDebugUnitTest`, `assembleDebugAndroidTest` e `lintDebug`

Saida esperada:

- suite automatizada cobre os comportamentos mais sensiveis do app
- regressao funcional passa a ser detectavel antes da homologacao manual

Base ja existente no repositorio:

- `checking_kotlin/docs/migration-phase-10-parity-tests.md`

### Fase 10 - Preparar Release E Publicacao

Objetivo: deixar o app Kotlin publicavel com o mesmo rigor operacional do Flutter.

Atividades:

- fechar versionamento final
- validar assinatura obrigatoria com upload key correta
- gerar AAB assinado, mapping do R8 e artefatos de release
- revisar checklist de Play Console, Data Safety, politica de privacidade e declaracoes de background location

Saida esperada:

- artefato de release pronto para submissao
- evidencias de build, signing e checklist de publicacao completas

Base ja existente no repositorio:

- `checking_kotlin/docs/migration-phase-11-release.md`
- `checking_kotlin/docs/google-play-submission-checklist.md`

### Fase 11 - Homologacao Em Campo E Decisao De Cutover

Objetivo: validar o comportamento do app em ambiente real antes de qualquer troca operacional.

Atividades:

- executar testes manuais em Android 13, 14 e 15+
- validar campo com app aberto, minimizado, tela bloqueada, sem internet e apos reboot
- testar em fabricantes com historico de restricao de background
- aprovar estrategia final de coexistencia ou substituicao do Flutter

Saida esperada:

- relatorio de homologacao com aprovacao ou pendencias objetivas
- decisao final de entrada em producao

## Ordem De Execucao Recomendada

1. fechar identidade e versao
2. congelar referencia funcional do Flutter
3. validar fundacao, persistencia e contratos de API
4. validar runtime Android, foreground e background
5. fechar UI Compose e testes de paridade
6. executar release, homologacao e decisao de cutover

## To-Do List Executiva

| ID | Item | Resultado esperado |
| --- | --- | --- |
| T01 | Confirmar a identidade final do app Kotlin (`com.br.checkingnative` ou `com.br.checking`). | Estrategia de coexistencia ou substituicao aprovada e sem ambiguidade para build, assinatura e rollout. |
| T02 | Fechar a versao alvo unica entre Flutter, Kotlin e documentos de release. | `versionName` e `versionCode` definidos como fonte de verdade unica para publicacao. |
| T03 | Consolidar a matriz funcional do Flutter como referencia oficial de paridade. | Documento de referencia com fluxos, regras e integracoes obrigatorias do app fonte. |
| T04 | Validar que a fundacao Android do `checking_kotlin` cobre Compose, Hilt, Room, DataStore, manifest, receivers e servicos. | Base tecnica aprovada para seguir sem retrabalho estrutural. |
| T05 | Auditar persistencia local, storage seguro e regra de migracao de dados do Flutter para o Kotlin. | Regra fechada para onboarding manual, migracao assistida ou upgrade in-place, sem lacuna de dados operacionais. |
| T06 | Validar os contratos de API e autenticacao usados em foreground e background. | Endpoints, headers, payloads, retry e politica de sessao aprovados para operacao real. |
| T07 | Validar o fluxo de permissoes, bateria, notificacoes e restricoes OEM. | App consegue orientar o usuario e operar dentro das restricoes reais do Android alvo. |
| T08 | Homologar a captura de localizacao em foreground com frequencia, precisao e reflexo na UI. | Coordenadas e status de monitoramento aparecem corretamente na tela e no estado interno. |
| T09 | Homologar o foreground service e as regras de automacao de check-in/check-out em background. | Automacao nativa executa os cenarios principais com notificacao persistente, retomada apos reboot e tratamento de erro. |
| T10 | Fechar a UI final em Compose com paridade dos fluxos criticos do Flutter. | Tela principal, estados de erro, configuracoes e historico ficam completos para uso operacional. |
| T11 | Ampliar e executar a suite automatizada de paridade no Kotlin. | Suites unitarias, instrumentadas e de lint passam com cobertura suficiente para bloquear regressao critica. |
| T12 | Executar homologacao manual em Android 13, 14 e 15+, incluindo Samsung, Motorola e Xiaomi/HyperOS. | Relatorio de campo com aprovacao objetiva do comportamento em foreground, background, reboot e perda de internet. |
| T13 | Gerar AAB assinado, arquivar `mapping.txt` e concluir o checklist de Play Console. | Pacote de release pronto para submissao com evidencias tecnicas e operacionais completas. |
| T14 | Aprovar o plano de cutover para producao. | Decisao final de publicar app separado ou substituir o Flutter, com impacto operacional conhecido. |

## Observacao Final

Pelo estado atual do repositorio, o caminho mais eficiente nao e reabrir a migracao desde o inicio, e sim usar `checking_android_new` como referencia funcional e `checking_kotlin` como base tecnica ja avancada, fechando agora os pontos de decisao, paridade real, homologacao de campo e estrategia de publicacao.