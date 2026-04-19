# Migracao Kotlin - Fase 4 Controller

Atualizado em: 2026-04-19

## Objetivo

Portar para Kotlin a camada funcional equivalente ao `CheckingController` do
Flutter para os fluxos manuais do aplicativo.

Esta fase continua respeitando as decisoes anteriores:

- o app Kotlin permanece separado em `com.br.checkingnative`
- onboarding manual permanece sendo o caminho esperado
- a tela principal ainda e o bootstrap tecnico
- localizacao real, permissoes runtime e service funcional ficam para fases
  posteriores

## Escopo Portado

Foi criado um controller nativo em:

```text
app/src/main/java/com/br/checkingnative/ui/checking/CheckingController.kt
```

Responsabilidades implementadas:

- inicializar estado salvo pelo repositório local
- carregar catalogo de localizacoes a partir de Room/cache
- normalizar chave Petrobras para 4 caracteres alfanumericos
- limpar historico corrente quando a chave muda
- atualizar registro, informe, projeto e configuracoes basicas
- sincronizar historico pela API mobile
- atualizar catalogo de localizacoes pela API mobile
- salvar catalogo atualizado em Room/cache
- enviar registro manual pela API mobile
- aplicar o estado remoto retornado pela API
- manter flags transientes de `isSyncing` e `isSubmitting`
- expor estado observavel por `StateFlow`

Tambem foi criado:

```text
app/src/main/java/com/br/checkingnative/ui/checking/CheckingUiState.kt
app/src/main/java/com/br/checkingnative/ui/checking/CheckingViewModel.kt
```

`CheckingViewModel` encapsula o controller para a futura UI Compose funcional.

## Abstracao De Estado

Foi adicionada a interface:

```text
CheckingStateStore
```

`CheckingStateRepository` continua sendo a implementacao real de producao,
baseada em DataStore.

Motivo:

- preservar a implementacao real da Fase 3
- permitir testes unitarios do controller sem depender de arquivo DataStore
- manter o controller desacoplado da tecnologia fisica de armazenamento

Hilt recebeu binding explicito em `AppModule`:

```kotlin
CheckingStateStore = CheckingStateRepository
```

## Compatibilidade Com O Flutter

Fluxos equivalentes implementados:

- `initialize`
- `updateChave`
- `updateInforme`
- `updateRegistro`
- `updateProjeto`
- `updateApiBaseUrl`
- `updateApiSharedKey`
- `syncHistory`
- `refreshLocationsCatalog`
- `submitCurrent`
- `refreshAfterEnteringForeground`, em versao sem captura real de localizacao

Regras preservadas:

- historico remoto define o proximo registro sugerido
- `lastCheckInLocation` e atualizado por estado remoto ou evento recente
- envio manual usa o informe escolhido pelo usuario
- envio automatico futuro sempre devera usar informe normal
- erros de API viram mensagens amigaveis no estado da tela
- `lastCheckIn` e `lastCheckOut` continuam sendo estado em memoria, nao
  persistencia definitiva

Diferença intencional:

- `client_event_id` passa a usar prefixo `kotlin` ou `kotlin-auto`, pois o app
  nativo separado deve identificar eventos gerados pelo novo cliente.

## Bootstrap

A tela de bootstrap continua existindo, mas agora mostra a Fase 4.

Foram adicionados indicadores para:

- controller Kotlin inicializado
- sync de historico conectado
- envio manual conectado
- catalogo conectado a API/cache
- estado atual de `isSyncing`
- estado atual de `isSubmitting`
- ultima mensagem operacional do controller

## Testes Adicionados

Arquivo:

```text
app/src/test/java/com/br/checkingnative/ui/checking/CheckingControllerTest.kt
```

Cobertura:

- inicializacao carrega estado persistido e locais
- alteracao de chave normaliza e limpa historico corrente
- `syncHistory` aplica estado remoto e sugere proxima acao
- `submitCurrent` envia payload manual correto e aplica retorno remoto
- `refreshLocationsCatalog` substitui catalogo local e atualiza tolerancia de
  precisao

Tambem foi mantida a cobertura das fases anteriores.

## Limites Desta Fase

Ainda nao implementado:

- tela Compose final equivalente ao Flutter
- snackbar/efeitos de UI para resultado de envio manual
- request runtime de permissoes Android
- captura real de localizacao foreground
- automacao real por localizacao
- foreground service funcional
- secure storage nativo para shared key
- tratamento de acoes vindas de notificacao/native action dentro do controller

## Criterio De Saida

Fase 4 e considerada concluida quando:

- controller Kotlin inicializa estado local
- controller expoe `StateFlow`
- ViewModel funcional existe para a futura UI Compose
- sync de historico pela API esta conectado
- envio manual pela API esta conectado
- refresh do catalogo pela API esta conectado ao cache/Room
- bootstrap indica Fase 4
- testes unitarios do controller passam
- `testDebugUnitTest`, `assembleDebug` e `lintDebug` passam

Status atual:

- controller implementado
- ViewModel funcional criado
- abstracao `CheckingStateStore` adicionada
- bootstrap atualizado para Fase 4
- testes especificos do controller validados
- `testDebugUnitTest`, `assembleDebug` e `lintDebug` validados
- lint permanece com 0 erros e 18 warnings conhecidos
- pronto para Fase 5
