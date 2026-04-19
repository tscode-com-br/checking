# Migracao Kotlin - Fase 5 UI Compose

Atualizado em: 2026-04-19

## Objetivo

Substituir a tela tecnica de bootstrap pela primeira UI funcional em Jetpack
Compose, conectada ao controller Kotlin criado na Fase 4.

Esta fase entrega a experiencia principal para os fluxos manuais do app:

- visualizar ultimos check-in/check-out
- informar chave Petrobras
- escolher registro
- escolher informe
- escolher projeto no check-in
- enviar registro manual
- sincronizar historico
- atualizar catalogo de localizacoes
- acessar configuracoes basicas
- acessar painel de automacao por localizacao, ainda sem captura real nativa

## Tela Principal

Foi criada a tela:

```text
app/src/main/java/com/br/checkingnative/ui/checking/CheckingApp.kt
```

Ela substitui `BootstrapApp` na `MainActivity`.

Componentes implementados:

- topo com identidade visual do app
- cabecalho "Checking" com botoes de automacao e configuracoes
- bloco de historico com ultimo check-in e ultimo check-out
- mensagem de status com tom visual
- campo de chave Petrobras com normalizacao para 4 caracteres
- seletores segmentados para registro, informe e projeto
- botao principal `REGISTRAR`
- snackbar para retorno operacional
- indicador linear para carregamento/sync
- loading no botao durante envio

## Bottom Sheet De Automacao

A sheet de automacao por localizacao inclui:

- switch de check-in/check-out automaticos
- botao para ver ultimas localizacoes capturadas
- ultima atualizacao de localizacao
- intervalo de atualizacao configurado
- quantidade de locais monitorados
- local capturado

Limite intencional:

- esta fase nao habilita captura real de GPS nem automacao real; a sheet
  apenas conecta os estados e controles ja existentes.

## Bottom Sheet De Configuracoes

A sheet de configuracoes inclui:

- switch de compartilhamento de localizacao
- estados de permissao em segundo plano, notificacoes e bateria
- acoes manuais para sincronizar historico e catalogo
- slider de frequencia de atividades
- switch de modo noturno apos check-out
- switch de desativacao de atualizacao noturna
- steppers de horario de inicio/fim do periodo noturno

As permissoes Android aparecem como estado de leitura nesta fase. Os requests
runtime ficam para a proxima fase.

## Activity E Lifecycle

`MainActivity` agora usa:

```text
CheckingViewModel
CheckingApp
```

No primeiro carregamento, o `CheckingViewModel` inicializa o controller e
executa refresh equivalente a entrada em foreground.

Em resumes posteriores da Activity, `refreshAfterEnteringForeground` tambem e
acionado.

## Bootstrap Removido

Os arquivos de bootstrap foram removidos:

```text
BootstrapApp.kt
BootstrapUiState.kt
BootstrapViewModel.kt
```

Com isso, a entrada do app deixa de ser uma tela tecnica de diagnostico e passa
a ser a tela funcional do produto.

## Warnings Corrigidos

O lint tinha 18 warnings na Fase 4.

Foram corrigidos:

- dependencias AndroidX atualizaveis com AGP atual
- Gson
- recursos `black` e `white` nao usados
- `tools:targetApi` desnecessario no tema
- ausencia de icone monocromatico em adaptive icon
- uso depreciado de `kotlinOptions.jvmTarget`, migrado para
  `compilerOptions`

Saldo atual:

- 2 warnings restantes
- ambos sao de Hilt `2.57 -> 2.59.2`
- a atualizacao foi testada e recusada porque Hilt `2.59.2` exige AGP 9
- manter Hilt `2.57` e a escolha segura enquanto o projeto permanece em AGP
  `8.11.1`

## Limites Desta Fase

Ainda nao implementado:

- request runtime de permissoes Android
- abertura de settings do Android para permissao/bateria
- captura real de localizacao em foreground
- automacao real por geofence/localizacao
- foreground service funcional
- acoes de notificacao conectadas ao controller
- secure storage nativo para shared key

## Criterio De Saida

Fase 5 e considerada concluida quando:

- `MainActivity` abre a tela funcional Compose
- bootstrap tecnico nao e mais a entrada do app
- tela principal permite operar os fluxos manuais
- sheets de automacao/configuracao existem
- ViewModel emite mensagens de snackbar
- warnings corrigiveis do lint foram tratados
- `testDebugUnitTest`, `assembleDebug` e `lintDebug` passam

Status atual:

- tela funcional implementada
- bootstrap removido
- warnings reduzidos de 18 para 2
- `testDebugUnitTest`, `assembleDebug` e `lintDebug` validados
- lint permanece com 0 erros e 2 warnings residuais de Hilt/AGP
- `play-services-location` permanece em `21.3.0`, ultima versao publicada no
  Google Maven nesta validacao
- pronto para Fase 6
