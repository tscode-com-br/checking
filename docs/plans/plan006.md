# plan006 — Homologação integral do Checking-Swift no macOS

> **Status:** pronto para execução no macOS.
> **Escopo exclusivo:** repositório `checking-swift`, aplicativo iOS em Swift.
> **Candidata atual esperada:** versão `1.6.6`, build `2`, bundle de produção
> `br.com.tscode.checking`.
> **Objetivo:** testar todas as correções realizadas neste ciclo antes de distribuir uma nova
> candidata pelo TestFlight, com atenção especial ao iPhone 17 Pro Max/iOS 26.5.2.

---

## 0. Regra de ouro

O aplicativo já está operacional. Os ensaios devem usar contas, projetos, locais e acidentes
exclusivamente de teste. Nenhum teste deve:

- registrar presença de um usuário real;
- alterar configurações de um projeto produtivo;
- criar um acidente real ou acionar chamada de emergência;
- versionar ou capturar senha, cookie, token APNs, chave de usuário ou coordenadas;
- concluir que um atraso de `BGAppRefresh` é defeito sem considerar que o agendamento em background
  é discricionário no iOS;
- promover a build para testadores externos antes de todos os gates P0/P1 estarem aprovados.

Kotlin, web e backend não fazem parte do produto sob teste neste plano. A API aparece somente como
dependência controlada e oráculo para confirmar o comportamento do cliente Swift.

Qualquer crash, atividade incorreta/duplicada, associação ao projeto errado ou exposição de dado
sensível interrompe imediatamente a homologação.

---

## 1. O que precisa ser validado

### 1.1 Projetos do usuário

- `GET /api/web/user-projects` é a fonte autoritativa no login e no retorno ao foreground.
- Cada mudança nas checkboxes envia ao servidor a lista completa desejada.
- Toques rápidos e mudanças durante um `PUT` são serializados sem perder seleção.
- A resposta do servidor prevalece sobre o estado otimista local.
- É permitido desmarcar todos os projetos. O contrato esperado é HTTP `200` com:

```json
{
  "projects": [],
  "active_project": ""
}
```

- Sem projeto, check-in/check-out manual e automático ficam bloqueados e a mensagem exibida deve ser:
  `O usuário não está cadastrado em nenhum projeto.`
- Respostas tardias de outra chave/conta não podem alterar a conta atual.
- Mudança real do projeto ativo deve invalidar geofences, retry de precisão e pausa pertencentes ao
  contexto anterior.

> O documento antigo `docs/endpoints/put_web_user_projects.md` ainda descreve `projects: []` como
> inválido. Para este plano, o código e os testes atuais são o contrato: a lista vazia é válida.

### 1.2 Baixa precisão do GPS

- `accuracyTooLow`, timeout de localização e falta de permissão continuam sendo estados distintos.
- A primeira leitura de baixa precisão abre um único episódio durável.
- A repetição ocorre a cada 180 segundos enquanto a precisão continuar insuficiente.
- Leituras ruins adicionais não deslocam o prazo original.
- A notificação aparece uma única vez por episódio e usa identificador estável.
- Textos esperados em português:
  - `Check-in - Falha!`, quando a próxima ação conhecida for check-in;
  - `Check-out - Falha!`, quando a próxima ação conhecida for check-out;
  - `Atividade automática - Falha!`, quando a ação ainda for ambígua;
  - corpo: `Baixa Precisão. Tentará novamente.`
- O retry não pode depender de novo movimento, nova transição de geofence ou retorno ao foreground.
- O episódio sobrevive à recriação do processo e é encerrado por resultado definitivo, perda de
  permissão, atividades automáticas OFF, pausa ativa, troca de conta/projeto ou submit confirmado.

### 1.3 Pausa Programada condicionada ao checkout

- Checkout anterior à ocorrência ou histórico vazio confirmado inicia a pausa normalmente.
- Check-in como última atividade impede o início da pausa.
- O motor continua apto a realizar o checkout enquanto a pausa está aguardando.
- Após checkout confirmado, a pausa só começa depois de 10 segundos ancorados em
  `lastCheckoutAt`.
- Antes de ativar, o app faz leitura fresca da API.
- Check-in novo durante a carência cancela a ativação.
- Checkout mais recente vindo de outro cliente reancora os 10 segundos.
- Falha da API nunca equivale a “sem histórico”.
- Se não couberem 10 segundos antes do fim da janela, a ocorrência termina sem notificação enganosa.
- Runtime, carência e deadlines sobrevivem à recriação do processo.
- Troca de chave/projeto, automação OFF ou fim da janela limpam apenas o contexto correspondente.
- Replay offline publica ao orquestrador somente o estado final confirmado após drenar toda a fila.

### 1.4 Alteração imediata da pausa no domingo

- Desmarcar domingo durante pausa ativa encerra a pausa e envia `Checking em atividade.`
  imediatamente.
- Marcar domingo novamente, ainda dentro da ocorrência e com checkout confirmado, inicia a pausa e
  envia `Checking em pausa.` imediatamente.
- Nenhuma das transições pode depender de minimizar e restaurar o aplicativo.
- Uma alteração de configuração não pode ser perdida por outra avaliação em andamento.
- Mudanças rápidas devem convergir para a última configuração persistida e produzir uma única
  reconciliação efetiva.

### 1.5 Retry de confirmação da Pausa Programada

- Falhas transitórias elegíveis: rede, HTTP 408, 429 e 5xx.
- Primeira repetição transitória: 10 segundos.
- Falhas transitórias seguintes: 180 segundos.
- Um gatilho externo não adia um retry já armado.
- `Unauthorized`, conflito, demais 4xx e erro desconhecido não criam loop próprio.
- `Unauthorized` usa o fluxo de reautenticação silenciosa e respeita o cooldown da notificação.
- Recuperação inicia a pausa sem exigir foreground.
- O retry nunca ultrapassa o fim da ocorrência.

### 1.6 Crash ao tocar uma notificação de Acidente

O incidente de referência ocorreu no TestFlight `1.6.6 (1)`, hardware `iPhone18,2`
(iPhone 17 Pro Max), iOS `26.5.2`, em
`_updateStateRestorationArchiveForBackgroundEvent`.

A candidata nova:

- usa o delegate Objective-C com `completionHandler`;
- reconhece ação e payload fora do isolamento da UI;
- transfere a intenção para a `MainActor`;
- conclui o callback inclusive quando a notificação é ignorada;
- só publica a rota de Acidente quando o app está ativo e após a janela de estabilização;
- não abre Acidente ao dispensar a notificação ou tocar notificações comuns.

### 1.7 Áreas adjacentes alteradas

- scheduler compartilhado de `BGAppRefresh`;
- prioridade entre transição de pausa, ativação/confirmação, retry de precisão e timer;
- fila offline e publicação do último estado confirmado;
- notificações e traduções PT, EN, ZH, MS, ID e TL;
- invalidação de contexto, geofences e mudança significativa de localização;
- versão `1.6.6 (2)`.

---

## 2. Estado exato do código que deverá chegar ao Mac

No momento da elaboração deste plano:

- `HEAD` do `checking-swift`: `dc383d30ca46db1f0207ecdddc799ca275c4df28`;
- existem correções posteriores ainda não incorporadas a esse commit em 10 arquivos do working tree;
- essas correções incluem o crash da notificação, domingo OFF→ON e o backoff da confirmação.

Portanto, um clone apenas de `origin/main` no estado acima **não contém todas as correções deste
plano**. Antes de testar, confirmar que o conteúdo importado inclui, por commit ou por cópia integral,
as alterações equivalentes nestes arquivos:

```text
Checking/App/AppDelegate.swift
Checking/Features/Check/CheckViewModel.swift
Checking/Features/Check/CheckViewModelSeams.swift
Checking/Platform/Background/BackgroundCheckOrchestrator.swift
CheckingTests/Auth/CheckMainViewModelTests.swift
CheckingTests/Auth/CheckViewModelFakes.swift
CheckingTests/DecisionEngine/UseCaseFakes.swift
CheckingTests/Notifications/AutoActivityNotificationsLiveTests.swift
CheckingTests/Orchestrator/ScheduledPauseDeferralTests.swift
Config/Shared.xcconfig
```

Registrar antes da execução:

```bash
git rev-parse HEAD
git status --short
git diff --stat
git diff --check
xcodebuild -version
sw_vers
```

Se as correções já tiverem sido commitadas, registrar o novo SHA e exigir working tree limpo. Se forem
importadas ainda como alterações locais, guardar `git diff --binary` em local privado como evidência
de qual código foi testado.

---

## 3. Ambiente e dados de teste

### 3.1 Matriz mínima de dispositivos

| Prioridade | Dispositivo | Sistema | Finalidade |
|---|---|---|---|
| Obrigatória | iPhone 17 Pro Max físico (`iPhone18,2`) | iOS 26.5.2, se ainda instalado | Regressão exata do crash |
| Obrigatória | iPhone 17 Pro Max Simulator | Runtime 26.5 ou mais próximo disponível | XCTest, UI e APNs simulado |
| Obrigatória | Um iPhone físico de tela menor | iOS atual suportado | Layout, permissões e background |
| Obrigatória | Simulator compatível com o mínimo | iOS 17 | Compatibilidade mínima |
| Recomendada | Segundo iPhone físico | Versão diferente do iOS | Concorrência entre clientes e upgrade |

Para cada dispositivo registrar: modelo, versão do iOS, estado da bateria, Modo Pouca Energia,
Atualização em 2º Plano, permissões e origem da instalação.

### 3.2 Contas e projetos

Preparar, sem usar dados reais:

- conta `A`, inicialmente sem projeto;
- conta `B`, usada para troca de chave durante requests;
- projetos `P-A` e `P-B`;
- ao menos um local exclusivo por projeto;
- um projeto isolado para ensaios de baixa precisão;
- uma forma segura de consultar o estado final da API;
- possibilidade de introduzir latência/falhas somente no ambiente de teste.

O oráculo de memberships é o `GET /api/web/user-projects`. Se for consultado fora do app, usar cookie
de sessão somente em memória e nunca imprimi-lo ou salvá-lo na evidência.

### 3.3 Como provocar baixa precisão de forma determinística

Não usar apenas a opção “Localização Precisa” desligada: isso pode exercitar falta de permissão em vez
de `accuracyTooLow`.

No projeto dedicado de teste:

1. registrar a precisão normalmente observada;
2. configurar temporariamente o limite permitido abaixo dessa precisão;
3. executar o cenário;
4. restaurar o limite original imediatamente após a rodada.

Não fazer essa alteração em projeto produtivo.

### 3.4 Estados de execução obrigatórios

Repetir os cenários críticos, quando aplicável, com:

- aplicativo em foreground;
- background ainda executável;
- processo suspenso;
- tela bloqueada;
- relançamento após encerramento pelo sistema/simulador;
- reinicialização do aparelho e primeiro desbloqueio;
- atualização da build 1 para a build 2.

Force-quit deliberado pelo usuário deve ser anotado separadamente: o iOS pode bloquear relançamentos e
trabalho em background nessa condição.

---

## 4. Preparação do projeto no macOS

Na raiz de `checking-swift`:

```bash
brew install xcodegen
xcodegen generate
xcodebuild -project Checking.xcodeproj -scheme Checking -showdestinations
```

O projeto é gerado nessa própria pasta. A instrução antiga de entrar em `ios/` não se aplica a este
repositório.

Escolher um UDID de Simulator disponível e criar uma pasta nova para cada execução:

```bash
mkdir -p .build/plan006
```

Confirmar versão e build efetivas:

```bash
xcodebuild \
  -project Checking.xcodeproj \
  -scheme Checking \
  -configuration Release \
  -showBuildSettings \
  | grep -E 'MARKETING_VERSION|CURRENT_PROJECT_VERSION|PRODUCT_BUNDLE_IDENTIFIER'
```

Resultado esperado para a candidata:

```text
MARKETING_VERSION = 1.6.6
CURRENT_PROJECT_VERSION = 2
PRODUCT_BUNDLE_IDENTIFIER = br.com.tscode.checking
```

O bundle Debug pode ser `br.com.tscode.checking.debug`; seus dados, Keychain e permissões são
independentes do TestFlight.

---

## 5. Gates automatizados

Cada comando deve usar um `-resultBundlePath` novo. Não sobrescrever um `.xcresult` anterior.

### 5.1 Build limpo

```bash
xcodebuild \
  -project Checking.xcodeproj \
  -scheme Checking \
  -configuration Debug \
  -destination 'platform=iOS Simulator,id=<UDID>' \
  clean build
```

```bash
xcodebuild \
  -project Checking.xcodeproj \
  -scheme Checking \
  -configuration Release \
  -destination 'generic/platform=iOS Simulator' \
  CODE_SIGNING_ALLOWED=NO \
  build
```

Critério: zero erro de compilação e zero novo warning de concorrência Swift relacionado aos arquivos
alterados.

### 5.2 Suites direcionadas

Rodar, no mínimo:

```bash
xcodebuild \
  -project Checking.xcodeproj \
  -scheme Checking \
  -configuration Debug \
  -destination 'platform=iOS Simulator,id=<UDID>' \
  -only-testing:CheckingTests/CheckMainViewModelTests \
  -only-testing:CheckingTests/AutomaticActivitiesActivationTests \
  -only-testing:CheckingTests/AutoActivitiesUseCaseTests \
  -only-testing:CheckingTests/AccuracyRetryEpisodeTests \
  -only-testing:CheckingTests/ScheduledPauseTests \
  -only-testing:CheckingTests/ScheduledPauseDeferralTests \
  -only-testing:CheckingTests/BGTaskAppRefreshSchedulerTests \
  -only-testing:CheckingTests/PendingCheckReplayerTests \
  -only-testing:CheckingTests/ProjectDTOCodingTests \
  -only-testing:CheckingTests/ProjectsApiLiveTests \
  -only-testing:CheckingTests/AutoActivityNotificationsLiveTests \
  -only-testing:CheckingTests/LocalizationTests \
  -resultBundlePath .build/plan006/targeted-<timestamp>.xcresult \
  test
```

Critério: zero falha, zero teste inesperadamente ignorado.

### 5.3 Suíte unitária completa

```bash
xcodebuild \
  -project Checking.xcodeproj \
  -scheme Checking \
  -configuration Debug \
  -destination 'platform=iOS Simulator,id=<UDID>' \
  -only-testing:CheckingTests \
  -resultBundlePath .build/plan006/unit-full-<timestamp>.xcresult \
  test
```

Há atualmente cerca de 662 métodos unitários por contagem textual, mas a contagem oficial deve ser
extraída do `.xcresult`. Não reutilizar o baseline antigo de 564.

### 5.4 Testes de UI

Executar com Simulator limpo e, depois, repetir o smoke autenticado:

```bash
xcodebuild \
  -project Checking.xcodeproj \
  -scheme Checking \
  -configuration Debug \
  -destination 'platform=iOS Simulator,id=<UDID>' \
  -only-testing:CheckingUITests \
  -resultBundlePath .build/plan006/ui-full-<timestamp>.xcresult \
  test
```

Há atualmente cerca de 28 métodos de UI por contagem textual. Registrar a contagem real.

### 5.5 Thread Sanitizer

Rodar as suites com maior concorrência separadamente:

```bash
xcodebuild \
  -project Checking.xcodeproj \
  -scheme Checking \
  -configuration Debug \
  -destination 'platform=iOS Simulator,id=<UDID>' \
  -enableThreadSanitizer YES \
  -only-testing:CheckingTests/CheckMainViewModelTests \
  -only-testing:CheckingTests/AccuracyRetryEpisodeTests \
  -only-testing:CheckingTests/ScheduledPauseDeferralTests \
  -only-testing:CheckingTests/AutoActivityNotificationsLiveTests \
  -resultBundlePath .build/plan006/tsan-<timestamp>.xcresult \
  test
```

Critério: zero data race e zero falha. Rodar TSan separadamente de outros sanitizers.

### 5.6 Harness de background

```bash
./scripts/validate_background_simulator.sh <UDID>
```

Conferir o relatório JSON e os eventos de:

- launch;
- permissões;
- geofence ENTER/EXIT;
- mudança de foreground/background;
- registro e execução de `BGTask`;
- APNs de validação.

---

## 6. Matriz manual — projetos

| ID | Preparação e ação | Resultado obrigatório |
|---|---|---|
| PRJ-01 | Autenticar a conta A sem memberships. | Checkboxes vazias; mensagem específica; submit manual/automático bloqueado; nenhum projeto local fantasma. |
| PRJ-02 | Marcar `P-A`; aguardar confirmação; consultar novamente a API. | UI e `GET` contêm somente `P-A`; projeto ativo válido; locais/geofences de `P-A`. |
| PRJ-03 | A partir de vazio, marcar `P-A` e `P-B` quase simultaneamente. | Um estado final contendo ambos; nenhuma seleção perdida; nenhum PUT antigo pisa na UI. |
| PRJ-04 | Com ambos marcados, desmarcá-los rapidamente até ficar vazio. | `PUT` aceita `projects: []`; `GET` retorna lista e projeto ativo vazios; mensagem específica; automação desligada/bloqueada com segurança. |
| PRJ-05 | Aplicar latência; alternar uma checkbox durante um PUT ainda em voo. | PUTs ordenados; submit permanece desabilitado durante sincronização; estado final corresponde ao último toque. |
| PRJ-06 | Fazer o PUT falhar; depois restaurar a rede e repetir. | Rollback para o estado autoritativo, erro visível; sucesso posterior remove o erro antigo. |
| PRJ-07 | Iniciar PUT na conta A e trocar imediatamente para a conta B. | Resposta tardia da conta A é ignorada; nenhuma membership, local, geofence ou retry vaza para B. |
| PRJ-08 | Alterar memberships pelo web/outro cliente; trazer o Swift ao foreground. | GET atualiza a UI e remove memberships obsoletas antes de qualquer avaliação automática. |
| PRJ-09 | Encerrar e relançar após estados com 0, 1 e 2 projetos. | Estado restaurado converge com a API; nenhum projeto errado recebe atividade. |
| PRJ-10 | Forçar conflito 409 de submit após remover memberships no servidor. | App atualiza memberships e mostra “O usuário não está cadastrado em nenhum projeto.”, não mensagem genérica. |

Para cada caso, guardar estado antes/depois do `GET`, ordem/horário dos `PUTs`, screenshot das checkboxes e
log de Atividades. Nunca registrar o cookie.

---

## 7. Matriz manual — baixa precisão

| ID | Preparação e ação | Resultado obrigatório |
|---|---|---|
| GPS-01 | Última atividade checkout; provocar baixa precisão na entrada do local. | Uma notificação `Check-in - Falha!`; corpo correto; nenhum submit com coordenada rejeitada. |
| GPS-02 | Última atividade check-in; provocar baixa precisão durante condição de saída. | Título `Check-out - Falha!` quando a ação for conhecida, ou título genérico apenas quando a matriz ainda não puder decidir. |
| GPS-03 | Manter baixa precisão por duas repetições. | Tentativas em aproximadamente 180 s; nenhuma notificação duplicada; prazo não é reiniciado por novas leituras. |
| GPS-04 | Sem mudar de geofence nem voltar ao foreground, tornar o fix aceitável. | Retry seguinte conclui a atividade; episódio, deadline e notificação são removidos. |
| GPS-05 | Disparar timer/geofence enquanto o retry está devido e outra avaliação está em voo. | Uma única execução efetiva é drenada; sem perda e sem submit duplicado. |
| GPS-06 | Encerrar o processo no Simulator após abrir o episódio; relançar antes/depois do prazo. | Estado durável é restaurado; notificação não duplica; retry continua com o mesmo contexto. |
| GPS-07 | Durante episódio, desligar automação, trocar projeto e trocar chave, em rodadas separadas. | Cada ação cancela episódio, deadline e notificação do contexto antigo. |
| GPS-08 | Durante episódio, retirar permissão de localização. | Episódio termina; nenhum loop; UI/diagnóstico reflete falta de permissão. |
| GPS-09 | Produzir timeout sem uma leitura explicitamente baixa. | Timeout isolado não cria episódio nem notificação de baixa precisão. |
| GPS-10 | Confirmar manualmente uma atividade durante o episódio. | Cancelamento ocorre somente após confirmação do servidor; falha de submit mantém o episódio. |
| GPS-11 | Colocar app em background/tela bloqueada durante o episódio. | Sem hammering; tentativa ocorre quando o iOS concede execução; foreground posterior reconcilia sem exigir movimento. |

Tolerância: com processo vivo, medir 180 s com pequena variação de agendamento. Em processo suspenso, não
exigir pontualidade do `BGAppRefresh`; exigir ausência de tentativas antecipadas/repetitivas e convergência no
próximo wake permitido.

---

## 8. Matriz manual — Pausa Programada

| ID | Preparação e ação | Resultado obrigatório |
|---|---|---|
| PAU-01 | Último estado checkout anterior à ocorrência; alcançar o início. | Pausa e notificação iniciam normalmente. |
| PAU-02 | Histórico confirmado vazio; alcançar o início. | Pausa imediata, sem criar check-in. |
| PAU-03 | Último estado check-in; alcançar o início ainda dentro do local. | Pausa não inicia; motor continua apto a satisfazer checkout. |
| PAU-04 | Satisfazer checkout automático e confirmar na API. | Pausa nunca antes de `lastCheckoutAt + 10 s`; inicia depois da confirmação fresca. |
| PAU-05 | Fazer checkout manual durante a espera. | Mesmo comportamento de 10 s, sem dupla ativação. |
| PAU-06 | Criar novo check-in, por outro cliente, durante os 10 s. | Ativação é cancelada e volta a aguardar checkout. |
| PAU-07 | Produzir checkout mais novo em outro cliente antes da confirmação. | Carência é reancorada no checkout mais recente. |
| PAU-08 | Falhar o primeiro GET por rede e recuperar antes do retry. | Retry em aproximadamente 10 s e ativação sem novo foreground. |
| PAU-09 | Responder 500 duas vezes e depois 200. | Primeiro intervalo ~10 s; próximo ~180 s; zero loop de 10 s; recuperação converge. |
| PAU-10 | Responder 408 e 429 em rodadas separadas. | Classificados como transitórios e sujeitos ao mesmo backoff. |
| PAU-11 | Responder 400/422/conflito/erro desconhecido. | Nenhum ciclo próprio; nenhuma pausa baseada em estado desconhecido. |
| PAU-12 | Expirar sessão com senha salva válida. | Uma reautenticação silenciosa; se bem-sucedida, uma nova leitura e convergência. |
| PAU-13 | Expirar sessão e impedir relogin. | Uma notificação de autenticação respeitando cooldown; zero requests a cada 10 s. |
| PAU-14 | Encerrar/recriar processo durante espera, carência e backoff. | Runtime e deadline restaurados; sem antecipação ou duplicação. |
| PAU-15 | Fazer checkout quando faltarem menos de 10 s para o fim. | Ocorrência termina sem iniciar/avisar pausa; não reabre. |
| PAU-16 | Testar janela no mesmo dia, atravessando meia-noite, fim de semana sobreposto e mudança DST. | Uma ocorrência estável; início e fim corretos. |
| PAU-17 | Trocar conta/projeto e desligar automação durante espera. | Flag, runtime e deadlines antigos removidos; contexto novo intacto. |
| PAU-18 | Enfileirar checkout offline e reconectar. | Pausa considera apenas o estado final após replay completo; evento intermediário não ativa cedo. |

### 8.1 Regressão literal de domingo

O XCTest usa domingo fixo e é obrigatório. Para teste manual, se o dia real não for domingo, há duas opções
seguras:

1. usar a janela diária equivalente para validar a reconciliação imediata; e
2. em aparelho/conta exclusivamente de teste, desligar temporariamente “Data e Hora automáticas” e usar um
   domingo, restaurando a opção ao terminar.

| ID | Ação | Resultado obrigatório |
|---|---|---|
| DOM-01 | Com domingo marcado e pausa ativa, desmarcar a checkbox. | `Checking em atividade.` imediatamente; flag/runtime ativos limpos. |
| DOM-02 | Aguardar 10 minutos com app em foreground e remarcar domingo, último estado checkout. | `Checking em pausa.` imediatamente; não minimizar o app. |
| DOM-03 | Remarcar domingo com último estado check-in. | Não pausa; aguarda checkout confirmado +10 s. |
| DOM-04 | Alterar a checkbox enquanto outra avaliação está suspensa em I/O. | Pedido é drenado ao final; não depende de geofence/foreground futuro. |
| DOM-05 | Fazer vários toggles/horários rápidos. | Persistência final corresponde à UI; sem runs ou notificações duplicadas. |
| DOM-06 | Desativar o toggle interno de notificações de pausa e repetir. | Lógica/flag da pausa continua correta, mas transições ficam silenciosas. |

---

## 9. Regressão do crash de notificação de Acidente

### 9.1 Simulator — payload seguro

Criar o arquivo fora do repositório, por exemplo
`/tmp/checking-accident-test.apns`:

```json
{
  "aps": {
    "alert": {
      "title": "Checking — teste",
      "body": "Teste seguro de abertura"
    },
    "sound": "default",
    "category": "CHECKING_ACCIDENT"
  },
  "checking_event": "accident-test"
}
```

Com o Debug instalado, aberto ao menos uma vez e autorizado para notificações:

```bash
xcrun simctl push <UDID> br.com.tscode.checking.debug /tmp/checking-accident-test.apns
```

Esse payload testa a abertura, mas não cria um acidente no backend.

### 9.2 Casos obrigatórios

| ID | Ação | Resultado obrigatório |
|---|---|---|
| CRH-01 | Tocar o corpo da notificação com app em foreground. | App permanece estável e abre a rota uma vez, depois de ativo. |
| CRH-02 | Tocar a ação `Abrir Checking` em foreground. | Mesmo resultado, sem navegação duplicada. |
| CRH-03 | Repetir corpo e ação com app em background. | Zero SIGABRT/freeze; conclusão do callback; rota após ativação. |
| CRH-04 | Repetir durante desbloqueio/transição de tela bloqueada no aparelho físico. | Zero `_updateStateRestorationArchiveForBackgroundEvent` e zero snapshot inconsistente. |
| CRH-05 | Repetir após suspensão e cold launch. | App inicia normalmente; intenção não é perdida nem entregue duas vezes. |
| CRH-06 | Fazer 10 toques no corpo e 10 na ação, gerando uma notificação por rodada. | Zero crash/hang; exatamente uma abertura por notificação. |
| CRH-07 | Dispensar a notificação. | Completion ocorre e Acidente não abre. |
| CRH-08 | Tocar notificações de check-in, checkout, baixa precisão, pausa e reauth. | Nenhuma abre Acidente. |
| CRH-09 | Tocar payload sem categoria e sem marcador de acidente. | Ignorado com segurança. |
| CRH-10 | Repetir na build TestFlight `1.6.6 (2)` no iPhone 17 Pro Max do incidente. | Nenhum `.ips`, crash ou encerramento nas horas seguintes. |

Para a rodada física/TestFlight, gerar a notificação por mecanismo controlado do projeto de teste
(notificação local de acidente sintético ou infraestrutura APNs de teste). Não usar “Reportar Acidente” de
produção e não acionar emergência.

Após cada bloco:

- abrir Devices and Simulators/Console e procurar `SIGABRT`, `EXC_CRASH`, assertion e watchdog;
- verificar Organizer e TestFlight Crashes;
- guardar `.ips` integral somente se não contiver dado sensível;
- confirmar que o app continua respondendo e que a tela anterior pode ser retomada.

---

## 10. Regressão funcional adjacente

| ID | Cenário | Resultado obrigatório |
|---|---|---|
| REG-01 | Login, logout, relogin silencioso e troca de chave. | Sessões isoladas; nenhum estado da conta anterior. |
| REG-02 | Check-in e checkout manuais, incluindo retroativo. | Um evento por ação; histórico e estado da API coerentes. |
| REG-03 | Checkout manual sem local selecionado, quando permitido. | Contrato atual preservado; sem crash. |
| REG-04 | Automação ON/OFF. | Monitores/geofences iniciam e param corretamente; OFF durável antes da invalidação. |
| REG-05 | ENTER/EXIT de geofence nos locais de `P-A` e `P-B`. | Somente locais do projeto ativo; sem duplicata. |
| REG-06 | Zona Mista, Escritório Principal e Localização não cadastrada. | Matriz de decisão e cooldown atuais preservados. |
| REG-07 | Perda/retorno de rede com eventos decididos e crus na fila offline. | Ordem, ID e timestamp originais; retry transitório; último estado publicado somente ao fim. |
| REG-08 | SSE/retorno ao foreground após alteração por outro cliente. | Histórico, memberships e estado final convergem sem atividade indevida. |
| REG-09 | Notificações autorizadas, negadas e provisionais. | Sem crash; comportamento coerente com permissão e toggles internos. |
| REG-10 | Localização Sempre, Durante o Uso, negada e Precisão Exata OFF. | Saúde/permissões corretas; nenhuma atividade sem autorização adequada. |
| REG-11 | Background App Refresh OFF e Modo Pouca Energia ON, separadamente. | Degradação explícita; sem loop, crash ou promessa de timing impossível. |
| REG-12 | Instalação limpa. | Prompts, login, projetos e defaults corretos. |
| REG-13 | Atualização sobre `1.6.6 (1)` para `1.6.6 (2)`. | Sessão/configuração preservadas; runtimes antigos decodificados; sem crash. |
| REG-14 | PT, EN, ZH, MS, ID e TL. | Novas mensagens presentes, sem chave crua, truncamento crítico ou idioma misturado. |
| REG-15 | Histórico, Atividades, Ajustes, Privacidade, Instruções e Sobre. | Navegação e conteúdo básico preservados. |
| REG-16 | Exclusão local e exclusão de conta, sucesso/conflito. | Filas, monitoramento e dados seguem os contratos existentes. |

---

## 11. Scheduler, background e energia

Validar que o único request de `BGAppRefresh` conserva o menor deadline entre:

1. transição de início/fim de pausa;
2. ativação/carência/confirmação de pausa;
3. retry de precisão;
4. refresh regular de 15 minutos.

Quando mais de um estiver vencido, a prioridade esperada é:

```text
pauseTransition > pauseActivation > accuracyRetry > timer
```

Limpar um deadline não pode apagar os demais.

### 11.1 Ensaio prolongado

Executar inicialmente 8 horas; se aprovado, ampliar para 24 horas:

- conta e projeto exclusivamente de teste;
- ao menos uma entrada e uma saída;
- um episódio de baixa precisão;
- uma pausa iniciada após checkout;
- períodos com tela bloqueada;
- uma perda curta de rede;
- sem force-quit.

Registrar bateria inicial/final, número de wakes, chamadas de estado, submits, notificações e qualquer
atividade inesperada. Critérios:

- zero atividade duplicada ou no projeto errado;
- zero consulta em intervalos apertados;
- no máximo uma notificação por episódio de baixa precisão;
- nenhuma pausa antes do checkout +10 s;
- nenhum crash/watchdog;
- consumo compatível com o baseline anterior, justificando qualquer aumento.

---

## 12. Archive e TestFlight

Somente depois dos gates automatizados e do smoke físico:

1. selecionar equipe e assinatura corretas no Xcode;
2. criar archive Release para dispositivo genérico;
3. confirmar `1.6.6 (2)`, bundle `br.com.tscode.checking`, arm64 e iOS mínimo;
4. executar **Validate App**;
5. guardar relatório de validação;
6. distribuir primeiro ao grupo interno;
7. instalar como atualização sobre a build 1;
8. repetir `CRH-03`, `CRH-04`, `CRH-06`, `PRJ-04`, `GPS-04`, `PAU-04` e `DOM-02`;
9. observar crashes e métricas por pelo menos algumas horas antes de ampliar o grupo.

O documento `checking-swift/docs/testflight_pilot.md` ainda cita a candidata antiga `1.6.5 (25)`.
Não reutilizar esse número de archive neste ciclo.

---

## 13. Evidências

Para cada ID, preencher:

| Campo | Conteúdo |
|---|---|
| ID | Ex.: `PAU-09` |
| Resultado | PASS, FAIL, BLOCKED ou NOT RUN |
| Código | SHA e indicação de working tree limpo/diff controlado |
| Build | Debug/TestFlight, versão e build |
| Ambiente | Xcode, macOS, dispositivo, iOS |
| Estado inicial | Projetos anonimizados, última ação, permissões, rede e estado do app |
| Horários | Hora civil e, quando possível, intervalo monotônico |
| Resultado esperado/real | Descrição objetiva |
| API | Estado antes/depois e sequência de status, sem credenciais |
| Notificações | Título, corpo, quantidade e horário |
| Arquivos | Screenshot/vídeo, `.xcresult`, Console ou `.ips` |
| Defeito | ID, severidade e passos mínimos de reprodução |

Organização sugerida, fora de commits públicos quando houver dados operacionais:

```text
plan006-evidence/
  baseline/
  automated/
  projects/
  gps/
  pause/
  accident-notification/
  regression/
  soak/
  final-report.md
```

Redigir screenshots, logs e vídeos antes de compartilhar.

---

## 14. Severidade e critérios de parada

### P0 — stop-ship imediato

- crash, freeze, corrupção ou perda de dados;
- atividade enviada ao usuário/projeto errado;
- check-in/check-out duplicado ou não autorizado;
- vazamento de credencial, token, cookie, chave ou coordenada;
- Acidente real ou emergência acionados durante teste.

### P1 — não distribuir

- checkbox diverge da API;
- não é possível remover todos os projetos;
- mensagem “sem projeto” ausente/incorreta;
- pausa começa antes de checkout confirmado +10 s;
- domingo ON depende de foreground posterior;
- segundo erro de confirmação continua repetindo a cada 10 s;
- 401/403 entra em hammering;
- retry de precisão é perdido, duplica alerta ou exige movimento;
- estado de conta/projeto anterior sobrevive à troca.

### P2 — corrigir antes da expansão

- atraso além do esperado com app vivo;
- notificação fantasma ou texto/localização incorretos;
- regressão de layout/acessibilidade relevante;
- consumo de bateria significativamente acima do baseline.

### P3 — melhoria/documentação

- detalhe cosmético sem impacto funcional;
- evidência ou roteiro que precisa ser esclarecido.

Não continuar para archive/TestFlight com P0/P1 aberto.

---

## 15. Definition of Done

O ciclo estará aprovado somente quando:

- o conteúdo testado inclui todas as correções locais posteriores a `dc383d3`;
- versão/build confirmadas como `1.6.6 (2)`;
- build Debug e Release aprovados;
- suites direcionadas, unitárias completas e UI com zero falha;
- TSan sem data race;
- harness de background aprovado;
- todos os casos PRJ, GPS, PAU, DOM e CRH obrigatórios executados;
- regressão física aprovada no iPhone 17 Pro Max/iOS 26.5.2 ou a indisponibilidade formalmente
  documentada com o aparelho/versão substituto;
- instalação limpa e atualização da build 1 para a build 2 aprovadas;
- nenhuma tentativa apertada de API observada;
- soak mínimo de 8 horas aprovado antes da expansão;
- zero P0/P1 aberto;
- relatório final contém SHA, `.xcresult`, dispositivos, evidências e limitações;
- configurações temporárias de relógio, precisão, rede, memberships e projeto de teste foram
  restauradas.
