# Inventario de Textos Administrativos - Modificacao 13

Inventario resultante do Prompt 1. Classifica cada texto por origem e propriedade antes que qualquer traducao em massa seja realizada.

Convencoes de classificacao:
- **UI key** — copy de interface; pertence ao catalogo `i18n.js`, resolvido via `t()`.
- **backend key** — mensagem estruturada do backend (`message_key + message_params`); o frontend resolve a copy no idioma ativo.
- **dominio** — valor persistido do negocio; nao deve ser traduzido.
- `✓` = ja coberto pela trilha atual (text mapeado em `applyStaticTranslations()` ou `t()`).
- `✗` = hard-coded ou fora da trilha i18n; precisa ser migrado.
- `⚠` = mapeado, mas via acesso fragil (indice posicional ou ordem de querySelectorAll).

---

## Exclusoes congeladas de dominio

Os textos abaixo nunca devem ser traduzidos. Sao valores persistidos do negocio ou identificadores tecnicos.

| Categoria | Exemplos |
|---|---|
| Nomes de usuario | Dados vindos do banco; renderizados diretamente |
| Nomes de projeto | Dados vindos do banco; renderizados diretamente |
| Placas de veiculos | Campos `placa`; renderizados diretamente |
| Nomes de providers de IA | `OpenAI`, `DeepSeek` — marcas, nao copy de interface |
| Identificadores de modelo | `gpt-5.4-2026-03-05`, `deepseek-reasoner` — IDs tecnicos |
| IDs de request | Valores internos; renderizados como referencia, nao como copy |
| Valores monetarios formatados | Numeros com moeda; o label ("Cost") e UI key, o valor nao |
| Codigos de moeda | `BRL`, `USD` — codigos ISO, nao labels |
| Valores de data/hora | Timestamps e intervalos formatados; os labels sao UI keys |
| Chaves de API | Campos de senha; nunca exibidos como texto |

---

## Grupo A — HTML estatico (`index.html`)

### A.1 Topbar e navegacao principal

| Elemento | Texto atual | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| Brand kicker | `Checking Transport` | UI key | `topbar.brand` | ✓ |
| Brand title | `Allocation board` | UI key | `topbar.allocationBoard` | ✓ |
| Settings link | `Dashboard Settings` | UI key | `settings.dashboardLink` | ✓ |
| AI trigger label | `IA` | UI key | `ai.triggerLabel` ou inline | ✗ — hard-coded no HTML, applyStaticTranslations nao cobre este span |
| AI menu: Calculate Routes | `Calculate Routes` | UI key | `ai.calculateRoutes` | ✓ |
| AI menu: Implement Modifications | `Implement Modifications` | UI key | `ai.implementModifications` | ✓ |
| AI menu: AI Settings | `AI Settings` | UI key | `ai.settingsMenuLabel` | ✓ |
| Route time label | `Work to Home Time:` | UI key | `settings.workToHomeTime` | ✓ |
| System support kicker | `System Support` | UI key | `topbar.systemSupport` | ✓ |
| Support name | `Tamer Salmem (HR70)` | dominio | — excluir da traducao | ✗ — hard-coded; nao deve ser traduzido, mas deveria vir da API |

### A.2 Paineis de requests e veiculos

| Elemento | Texto atual | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| Project list toggle | `Project List` | UI key | `panes.projectList` | ✓ |
| User list title | `User List` | UI key | `panes.userList` | ✓ |
| Extra section title | `EXTRA` | UI key | `requests.labels.extra` | ⚠ indice `[0]` |
| Weekend section title | `WEEKEND` | UI key | `requests.labels.weekend` | ⚠ indice `[1]` |
| Regular section title | `REGULAR` | UI key | `requests.labels.regular` | ⚠ indice `[2]` |
| Extra vehicle pane title | `Extra Transport List` | UI key | `vehicles.lists.extra` | ⚠ indice `[0]` |
| Weekend vehicle pane title | `Weekend Transport List` | UI key | `vehicles.lists.weekend` | ⚠ indice `[1]` |
| Regular vehicle pane title (implicito) | `Regular Transport List` | UI key | `vehicles.lists.regular` | ⚠ indice `[2]` |

### A.3 Auth

| Elemento | Texto atual | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| Auth key label | `key` | UI key | `auth.key` | ⚠ indice `authLabels[0]` |
| Auth pass label | `pass` | UI key | `auth.pass` | ⚠ indice `authLabels[1]` |

### A.4 Footer de status

| Elemento | Texto atual | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| Default status text | `Transport dashboard ready.` | UI key | `status.ready` | ⚠ coberto via `getDefaultStatusMessage()` mas apenas quando `setStatus()` e chamado; o HTML tem o texto hard-coded como placeholder inicial |

### A.5 Modal de veiculo

| Elemento | Texto atual | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| Scope label | `Regular` | UI key | `modal.scopeLabel.regular` / dinamico | ✗ hard-coded no HTML |
| Modal title | `Create Vehicle` | UI key | `modal.title.create` | ✓ via `syncVehicleModalCopy()` |
| Scope note (regular) | `Regular vehicles are created for both routes…` | UI key | `modal.notes.regular` | ✓ via `syncVehicleModalCopy()` |
| Field: Type | `Type` | UI key | `modal.fields.type` | ⚠ indice `modalFieldLabels[0]` |
| Field: Plate | `Plate` | UI key | `modal.fields.plate` | ⚠ indice `[1]` |
| Field: Color | `Color` | UI key | `modal.fields.color` | ⚠ indice `[2]` |
| Field: Places | `Places` | UI key | `modal.fields.places` | ⚠ indice `[3]` |
| Field: Tolerance | `Tolerance (minutes)` | UI key | `modal.fields.tolerance` | ⚠ indice `[4]` |
| Field: Departure Date | `Departure Date` | UI key | `modal.fields.departureDate` | ⚠ indice `[5]` |
| Field: Departure Time | `Departure Time` | UI key | `modal.fields.departureTime` | ⚠ indice `[6]` |
| Field: Route | `Route` | UI key | `modal.fields.route` | ⚠ indice `[7]` |
| Option: Home to Work | `Home to Work` | UI key | `requests.routeKindLabel.homeToWork` | ⚠ indice `routeOptions[0]` |
| Option: Work to Home | `Work to Home` | UI key | `requests.routeKindLabel.workToHome` | ⚠ indice `routeOptions[1]` |
| Checkbox: Every Saturday | `Every Saturday` | UI key | `modal.fields.everySaturday` | ⚠ indice `weekendLabels[0]` |
| Checkbox: Every Sunday | `Every Sunday` | UI key | `modal.fields.everySunday` | ⚠ indice `weekendLabels[1]` |
| Checkbox: Every Monday | `Every Monday` | UI key | `modal.fields.everyMonday` | ⚠ indice `regularLabels[0]` |
| Checkbox: Every Tuesday | `Every Tuesday` | UI key | `modal.fields.everyTuesday` | ⚠ indice `[1]` |
| Checkbox: Every Wednesday | `Every Wednesday` | UI key | `modal.fields.everyWednesday` | ⚠ indice `[2]` |
| Checkbox: Every Thursday | `Every Thursday` | UI key | `modal.fields.everyThursday` | ⚠ indice `[3]` |
| Checkbox: Every Friday | `Every Friday` | UI key | `modal.fields.everyFriday` | ⚠ indice `[4]` |
| Button: Cancel | `Cancel` | UI key | `modal.actions.cancel` | ✓ |
| Button: Save Vehicle | `Save Vehicle` | UI key | `modal.actions.saveVehicle` | ✓ |
| Option: Car | `Car` | UI key | `modal.options.car` | ⚠ indice |
| Option: Minivan | `Minivan` | UI key | `modal.options.minivan` | ⚠ indice |
| Option: Van | `Van` | UI key | `modal.options.van` | ⚠ indice |
| Option: Bus | `Bus` | UI key | `modal.options.bus` | ⚠ indice |

### A.6 Modal do Agente de IA (atualmente em Portugues)

Estes textos estao hard-coded em Portugues no HTML. `applyStaticTranslations()` ja possui codigo para sobrescreve-los, mas o HTML inicial exibe Portugues antes do JS inicializar — flash de idioma errado.

| Elemento | Texto atual (PT) | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| Modal title | `Ajustes para o Agente de IA` | UI key | `ai.agentSettingsTitle` | ✗ PT no HTML |
| Close button aria-label | `Fechar ajustes do agente de IA` | UI key | `ai.agentSettingsCloseAria` | ✗ PT no HTML |
| Modal note | `Quando os projetos forem carregados, a IA usará…` | UI key | `ai.agentSettingsNotePending` | ✗ PT no HTML |
| Earliest boarding label | `Embarque Mais Cedo:` | UI key | `ai.agentSettingsEarliestBoarding` | ✗ PT no HTML |
| Arrival label | `Horário de Chegada no Trabalho:` | UI key | `ai.agentSettingsArrivalAtWork` | ✗ PT no HTML |
| Request kinds legend | `Listas para Calcular` | UI key | `ai.agentSettingsRequestKindsLegend` | ✗ PT no HTML |
| Cancel button | `Cancelar` | UI key | `ai.agentSettingsCancel` | ✗ PT no HTML |
| Submit button | `Solicitar Rotas` | UI key | `ai.agentSettingsSubmit` | ✗ PT no HTML |

### A.7 Modal de Alteracoes da IA (atualmente em Portugues)

| Elemento | Texto atual (PT) | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| Modal title | `Alterações` | UI key | `ai.changesTitle` | ✗ PT no HTML |
| Close button aria-label | `Fechar alterações` | UI key | `ai.changesCloseAria` | ✗ PT no HTML |

### A.8 Review contract e summary cards (nao cobertos por applyStaticTranslations)

| Elemento | Texto atual | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| AI Review kicker | `AI Review` | UI key | `ai.review.kicker` | ✗ hard-coded |
| Summary heading | `Summary` | UI key | `ai.review.summaryHeading` | ✗ hard-coded |
| Summary card: Cost | `Cost` | UI key | `ai.review.summary.cost` | ✗ hard-coded |
| Summary card: Vehicles | `Vehicles` | UI key | `ai.review.summary.vehicles` | ✗ hard-coded |
| Summary card: Passengers | `Passengers` | UI key | `ai.review.summary.passengers` | ✗ hard-coded |
| Review Contract heading | `Review Contract` | UI key | `ai.review.contract.heading` | ✗ hard-coded |
| Contract: Vehicle Tables title | `Vehicle Tables` | UI key | `ai.review.contract.vehicleTables.title` | ✗ hard-coded |
| Contract: Vehicle Tables body | `The primary review surface is…` | UI key | `ai.review.contract.vehicleTables.body` | ✗ hard-coded |
| Contract: Management Table title | `Management Table` | UI key | `ai.review.contract.managementTable.title` | ✗ hard-coded |
| Contract: Management Table body | `The final surface ends with…` | UI key | `ai.review.contract.managementTable.body` | ✗ hard-coded |
| Contract: Exceptions title | `Exceptions / Not Routed` | UI key | `ai.review.contract.exceptions.title` | ✗ hard-coded |
| Contract: Exceptions body | `Unallocated requests and…` | UI key | `ai.review.contract.exceptions.body` | ✗ hard-coded |
| Contract: Canonical Row title | `Canonical Row Contract` | UI key | `ai.review.contract.canonicalRow.title` | ✗ hard-coded |
| Row field: request_id | `Internal request_id` | UI key + dominio | `ai.review.contract.canonicalRow.requestId` | ✗ hard-coded |
| Row field: user_name | `Nome do Usuario` (PT!) | UI key | `ai.review.contract.canonicalRow.userName` | ✗ PT hard-coded |
| Row field: user_address | `Endereco do Usuario` (PT!) | UI key | `ai.review.contract.canonicalRow.userAddress` | ✗ PT hard-coded |
| Row field: home_to_work | `Home to Work - Embarque` (PT!) | UI key | `ai.review.contract.canonicalRow.homeToWork` | ✗ PT hard-coded |
| Row field: work_to_home | `Work to Home - Desembarque` (PT!) | UI key | `ai.review.contract.canonicalRow.workToHome` | ✗ PT hard-coded |
| Row field: pickup_order | `Internal pickup_order` | UI key + dominio | `ai.review.contract.canonicalRow.pickupOrder` | ✗ hard-coded |
| Contract: Canonical Row note | `Ordering uses pickup_order from…` | UI key | `ai.review.contract.canonicalRow.note` | ✗ hard-coded |

### A.9 Abas e paineis do review

| Elemento | Texto atual | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| Tab: Review | `Review` | UI key | `ai.review.tabs.review` | ✗ hard-coded |
| Tab: Vehicles | `Vehicles` | UI key | `ai.review.tabs.vehicles` | ✗ hard-coded |
| Tab: Passengers | `Passengers` | UI key | `ai.review.tabs.passengers` | ✗ hard-coded |
| Tab: Routes | `Routes` | UI key | `ai.review.tabs.routes` | ✗ hard-coded |
| Tab: Audit | `Audit` | UI key | `ai.review.tabs.audit` | ✗ hard-coded |
| Panel heading: Review Plan | `Review Plan` | UI key | `ai.review.panels.reviewPlan` | ✗ hard-coded |
| Panel: Review empty state | `Consolidated per-vehicle tables render here…` | UI key | `ai.review.panels.reviewEmptyState` | ✗ hard-coded |
| Panel: Exceptions placeholder title | `Exceptions / Not Routed` | UI key | `ai.review.exceptions.title` | ✗ hard-coded (duplica dinamico) |
| Panel: Exceptions placeholder body | `Requests without a vehicle assignment…` | UI key | `ai.review.panels.exceptionsPlaceholder` | ✗ hard-coded |
| Panel: Management placeholder title | `Management Table` | UI key | `ai.review.managementTitle` | ✗ hard-coded (duplica dinamico) |
| Panel: Management placeholder body | `Management metrics stay at the end…` | UI key | `ai.review.panels.managementPlaceholder` | ✗ hard-coded |
| Panel heading: Supporting Vehicle Details | `Supporting Vehicle Details` | UI key | `ai.review.panels.vehicleDetails` | ✗ hard-coded |
| Panel: Vehicles empty state | `Vehicle actions stay available here…` | UI key | `ai.review.panels.vehiclesEmptyState` | ✗ hard-coded |
| Panel heading: Supporting Passenger Details | `Supporting Passenger Details` | UI key | `ai.review.panels.passengerDetails` | ✗ hard-coded |
| Panel: Passengers empty state | `Passenger-level allocation details remain…` | UI key | `ai.review.panels.passengersEmptyState` | ✗ hard-coded |
| Panel heading: Supporting Route Details | `Supporting Route Details` | UI key | `ai.review.panels.routeDetails` | ✗ hard-coded |
| Panel: Routes empty state | `Ordered route stops remain available…` | UI key | `ai.review.panels.routesEmptyState` | ✗ hard-coded |
| Panel heading: Audit | `Audit` | UI key | `ai.review.panels.audit` | ✗ hard-coded |
| Panel: Audit empty state | `Prompt version, provider details, hashes…` | UI key | `ai.review.panels.auditEmptyState` | ✗ hard-coded |

### A.10 Acoes do modal de alteracoes

| Elemento | Texto atual | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| Button: Cancel | `Cancel` | UI key | `modal.actions.cancel` | ✗ hard-coded (nao coberto) |
| Button: Save | `Save` | UI key | `ai.changes.actions.save` | ✗ hard-coded |
| Button: Apply | `Apply` | UI key | `ai.changes.actions.apply` | ✗ hard-coded |

### A.11 Modal de settings de IA

| Elemento | Texto atual | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| Modal title | `AI Settings` | UI key | `ai.settingsTitle` | ✓ |
| Project label | `Project:` | UI key | `ai.settingsProject` | ✓ |
| Provider label | `Provider:` | UI key | `ai.settingsProvider` | ✓ |
| Option: OpenAI | `OpenAI` | dominio (marca) | — excluir da traducao | ✗ hard-coded; nao traduzir |
| Option: DeepSeek | `DeepSeek` | dominio (marca) | — excluir da traducao | ✗ hard-coded; nao traduzir |
| Provider note | `OpenAI -> gpt-5.4-2026-03-05 …` | dominio (ID tecnico) | — excluir da traducao | ✗ hard-coded; nao traduzir |
| API Key label | `API Key:` | UI key | `ai.settingsApiKey` | ✓ |
| API Key placeholder | `Paste API key` | UI key | `ai.settingsApiKeyPlaceholder` | ✓ |
| Button: Cancel | `Cancel` | UI key | `ai.settingsCancel` | ✓ |
| Button: Save | `Save` | UI key | `ai.settingsSave` | ✓ |

### A.12 Modal de settings do dashboard

| Elemento | Texto atual | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| Modal title | `SETTINGS` | UI key | `settings.title` | ✓ |
| Section: Preferences | `Preferences` | UI key | `settings.preferences` | ✓ |
| Label: Languages | `Languages:` | UI key | `settings.languages` | ✓ |
| Label: Arrive at Work | `Arrive at Work:` | UI key | `settings.arriveAtWorkTime` | ✓ |
| Label: Work to Home Time | `Work to Home Time:` | UI key | `settings.workToHomeTime` | ✓ |
| Label: Extra Car Tolerance | `Extra Car Tolerance:` | UI key | `settings.extraCarTolerance` | ✓ |
| Label: Last Update Time | `Last Update Time:` | UI key | `settings.lastUpdateTime` | ✓ |
| Label: Standard Tolerance | `Standard Tolerance:` | UI key | `settings.standardTolerance` | ✓ |
| Section: Vehicle Form Defaults | `Vehicle Form Defaults` | UI key | `settings.vehicleDefaults` | ✓ |
| Label: Price Variables | `Price Variables:` | UI key | `settings.priceVariables` | ✓ |
| Label: Currency | `Currency` | UI key | `settings.currency` | ✓ |
| Label: Billing Unit | `Billing Unit` | UI key | `settings.billingUnit` | ✓ |
| Option: Per hour | `Per hour` | UI key | `settings.perHour` | ✓ |
| Option: Per day | `Per day` | UI key | `settings.perDay` | ✓ |
| Option: Per week | `Per week` | UI key | `settings.perWeek` | ✓ |
| Option: Per month | `Per month` | UI key | `settings.perMonth` | ✓ |
| Button: Add currency | `Add currency` | UI key | `settings.addCurrency` | ✓ |
| Label: Currency code | `Currency code` | UI key | `settings.currencyCode` | ✓ |
| Label: Currency label | `Currency label` | UI key | `settings.currencyLabel` | ✓ |
| Button: Cancel (currency) | `Cancel` | UI key | `modal.actions.cancel` | ✓ |
| Button: Save currency | `Save currency` | UI key | `settings.saveCurrency` | ✓ |
| Label: Car default places | `Car default places:` | UI key | `settings.defaultPlacesLabel` + params | ✓ |
| Label: Car default price | `Car default price:` | UI key | `settings.defaultPriceLabel` + params | ✓ |
| Label: Minivan default places | `Minivan default places:` | UI key | `settings.defaultPlacesLabel` + params | ✓ |
| Label: Minivan default price | `Minivan default price:` | UI key | `settings.defaultPriceLabel` + params | ✓ |
| Label: Van default places | `Van default places:` | UI key | `settings.defaultPlacesLabel` + params | ✓ |
| Label: Van default price | `Van default price:` | UI key | `settings.defaultPriceLabel` + params | ✓ |
| Label: Bus default places | `Bus default places:` | UI key | `settings.defaultPlacesLabel` + params | ✓ |
| Label: Bus default price | `Bus default price:` | UI key | `settings.defaultPriceLabel` + params | ✓ |
| Button: Close | `Close` | UI key | `settings.close` | ✓ |

---

## Grupo B — DOM dinamico (`app.js`)

### B.1 Badges de custo do review

| Texto | Contexto | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| `Cost Pending` | Badge de custo pendente | UI key | `ai.review.badges.costPending` | ✗ literal (linha 2653) |
| `Savings` (label) | Label do badge de economia | UI key | `ai.review.badges.savings` | ✗ literal (linha 2662) |
| `` `Savings ${savingsText}` `` | Badge de economia com valor | UI key + parametro | `ai.review.badges.savingsAmount` com `{amount}` | ✗ literal (linha 2664) |
| `Increase` (label) | Label do badge de aumento | UI key | `ai.review.badges.increase` | ✗ literal (linha 2673) |
| `` `Increase ${increaseText}` `` | Badge de aumento com valor | UI key + parametro | `ai.review.badges.increaseAmount` com `{amount}` | ✗ literal (linha 2675) |
| `No Cost Change` | Badge sem mudanca de custo | UI key | `ai.review.badges.noCostChange` | ✗ literal (linha 2685) |
| `Sensitive Change` | Badge de mudanca sensivel | UI key | `ai.review.badges.sensitive` | ✓ via `translateTransportAiReviewText` |

### B.2 ETA/ETD no detalhe de veiculo

| Texto | Contexto | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| `` `ETA ${etaTime}h` `` | ETA na linha de veiculo | UI key + horario | `ai.review.etaLabel` com `{time}` | ✗ literal (linha 1933) |
| `` `ETD ${etdTime}h` `` | ETD na linha de veiculo | UI key + horario | `ai.review.etdLabel` com `{time}` | ✗ literal (linha 1937) |
| `ETA` (cabecalho de coluna) | Cabecalho na tabela de rotas | UI key | `ai.review.columns.eta` | ✗ literal (linha 4122) |
| `ETD` (cabecalho de coluna) | Cabecalho na tabela de rotas | UI key | `ai.review.columns.etd` | ✗ literal (linha 4125) |
| `` `ETA ${normalizedReferenceTime}h` `` | ETA no itinerario de rota | UI key + horario | `ai.review.etaLabel` com `{time}` | ✗ literal (linha 4895) |
| `` `ETD ${normalizedReferenceTime}h` `` | ETD no itinerario de rota | UI key + horario | `ai.review.etdLabel` com `{time}` | ✗ literal (linha 4898) |

### B.3 Clusters temporais extras

| Texto | Contexto | Classificacao | Chave i18n alvo | Status |
|---|---|---|---|---|
| `Extra Temporal Clusters` | Heading de secao | UI key | `ai.review.extraTemporalClusters` | ✗ literal (linha 4780) |
| `` `Anchors ${extraClusterAnchorText}` `` | Nota de ancora | UI key + valor | `ai.review.anchorsLabel` com `{anchors}` | ✗ literal (linha 3219) |

### B.4 Colunas e labels do review (ja cobertos)

| Texto | Chave alvo | Status |
|---|---|---|
| User Name | `ai.review.columns.userName` | ✓ via `translateTransportAiReviewText` |
| User Address | `ai.review.columns.userAddress` | ✓ |
| Home to Work - Boarding | `ai.review.columns.homeToWorkBoarding` | ✓ |
| Work to Home - Dropoff | `ai.review.columns.workToHomeDropoff` | ✓ |
| Action, Type, Seats, Cost, List, Route (meta labels) | `ai.review.meta.*` | ✓ |
| Request (exceptions) | `ai.review.exceptions.labels.request` | ✓ |
| Exceptions / Not Routed (heading dinamico) | `ai.review.exceptions.title` | ✓ |
| Blocking, Needs Review, Not Routed (badges) | `ai.review.exceptions.badges.*` | ✓ |
| Management Table (heading dinamico) | `ai.review.managementTitle` | ✓ |
| Metric, Current, Suggested, Delta (colunas) | `ai.review.management.columns.*` | ✓ |
| Create, Update, Remove, Currency, Rate, Route Provider, Prompt Version, Model, Blocking (notas) | `ai.review.management.notes.*` | ✓ |

### B.5 Textos de status dinamico (parcialmente cobertos)

| Texto / funcao | Chave alvo | Status |
|---|---|---|
| `getDefaultStatusMessage()` | `status.ready` | ✓ via `t()` |
| Mensagens de polling da IA | Resolvidas via `resolveTransportAiStructuredMessage()` (Mod 12) | ✓ |
| Textos de loading / empty state em tabelas | varios | ✗ — a verificar por superfície |

---

## Grupo C — Mensagens da API (backend)

Nenhuma rota administrativa usa `message_key + message_params` ainda. Todas as mensagens sao strings literais em ingles. A Modificacao 13 Prompt 5 precisa estruturar essas rotas.

### C.1 `transport.py` — autenticacao

| Mensagem atual | Chave alvo | Tipo |
|---|---|---|
| `Invalid key or password.` | `auth.invalidCredentials` | backend key |
| `This user does not have transport access.` | `auth.noAccess` | backend key |
| `Transport access granted.` | `auth.granted` | backend key |
| `Transport session closed.` | `auth.sessionClosed` | backend key |

### C.2 `transport.py` — CRUD de veiculos

| Mensagem atual | Chave alvo | Tipo |
|---|---|---|
| `Vehicle saved successfully.` | `vehicles.saved` | backend key |
| `Vehicle deleted from the database.` | `vehicles.deleted` | backend key |
| `Vehicle updated successfully.` | `vehicles.updated` | backend key |
| `Vehicle schedule updated successfully.` | `vehicles.scheduleUpdated` | backend key |

### C.3 `transport.py` — assignments e requests

| Mensagem atual | Chave alvo | Tipo |
|---|---|---|
| `Transport assignment saved successfully.` | `assignments.saved` | backend key |
| `Transport boarding time saved successfully.` | `assignments.boardingTimeSaved` | backend key |
| `Transport request rejected successfully.` | `assignments.requestRejected` | backend key |

### C.4 `transport.py` — settings e timing

| Mensagem atual | Chave alvo | Tipo |
|---|---|---|
| `The global transport timing policy was updated.` | `settings.timingPolicyUpdated` | backend key |
| `A date-specific transport timing override was updated.` | `settings.timingOverrideUpdated` | backend key |

### C.5 `transport.py` — erros HTTP (detail)

| Mensagem atual | Chave alvo | Tipo |
|---|---|---|
| `Vehicle not found.` | `errors.vehicleNotFound` | backend key |
| `Transport request not found.` | `errors.requestNotFound` | backend key |
| `The transport request does not apply to the selected date.` | `errors.requestDateMismatch` | backend key |
| `The selected vehicle belongs to a different list.` | `errors.vehicleScopeMismatch` | backend key |
| `The selected vehicle is not available for this date and route.` | `errors.vehicleUnavailable` | backend key |
| `Workplace not found for the provided policy context.` | `errors.workplaceNotFound` | backend key |
| `A workplace with this name already exists.` | `errors.workplaceNameConflict` | backend key |
| `Workplace not found.` | `errors.workplaceNotFound` | backend key |

### C.6 `transport.py` — mensagens de auditoria interna

As mensagens abaixo sao mensagens de log de auditoria interna (registradas no sistema para rastreabilidade operacional), nao copy de UI exibida ao administrador. Podem manter texto literal em ingles.

| Mensagem (auditoria interna) |
|---|
| `A transport proposal was validated for operational review.` |
| `A transport proposal approval outcome was recorded.` |
| `A transport proposal was rejected during operational review.` |
| `An approved transport proposal was applied to transport assignments.` |
| `A vehicle registration changed the available transport supply.` |
| `A vehicle schedule was removed from operational availability.` |
| `A vehicle configuration changed the transport supply context.` |
| `A vehicle schedule changed the operational availability for transport planning.` |
| `A transport assignment decision changed the operational state of the day.` |
| `A manual boarding time update changed the transport assignment state.` |
| `A transport request rejection changed the operational state of the day.` |
| `A workplace operational context was created.` |
| `A workplace operational context was updated.` |

### C.7 `transport_ai.py` — descricoes de status

Estas strings sao retornadas pelo backend e consumidas pelo frontend via `localizeTransportApiMessage()` (mapeamento fragil). A Modificacao 12 ja substituiu o caminho principal por `failure_category` e `message_key`. O Prompt 5 da 13 precisa estruturar essas descricoes de status como `message_key`.

| Mensagem atual | Chave alvo proposta | Tipo |
|---|---|---|
| `Transport AI route calculation was requested.` | `ai.status.requested` | backend key |
| `Transport AI saved the dashboard baseline and is preparing the route calculation.` | `ai.status.savingBaseline` | backend key |
| `Transport AI reset eligible passengers to pending and is preparing the route calculation.` | `ai.status.resettingPassengers` | backend key |
| `Transport AI route calculation is running.` | `ai.status.running` | backend key |
| `Transport AI suggestion is ready for review.` | `ai.status.readyForReview` | backend key |
| `Transport AI finished, but the persisted suggestion payload is unavailable.` | `ai.status.payloadUnavailable` | backend key |
| `Transport AI finished, but no persisted suggestion is available yet.` | `ai.status.noSuggestion` | backend key |
| `Transport AI suggestion was saved and is ready to be applied.` | `ai.status.saved` | backend key |
| `Transport AI suggestion was applied.` | `ai.status.applied` | backend key |
| `Transport AI suggestion was cancelled and the baseline was restored.` | `ai.status.cancelled` | backend key |
| `Transport AI route calculation status is unavailable.` | `ai.status.unavailable` | backend key |

### C.8 `transport_ai.py` — erros e resultados operacionais

| Mensagem atual | Chave alvo proposta | Tipo |
|---|---|---|
| `Transport AI route calculation failed.` | Coberto por `failure_category` (Mod 12) | backend key (estruturado) |
| `The stored transport AI suggestion payload is unavailable.` | `ai.errors.payloadUnavailable` | backend key |
| `The transport AI suggestion can no longer be saved.` | `ai.save.notAllowed` | backend key |
| `The transport AI suggestion cannot be saved because its payload is invalid.` | `ai.save.invalidPayload` | backend key |
| `The transport AI suggestion was already applied and cannot be cancelled.` | `ai.cancel.alreadyApplied` | backend key |
| `The transport AI suggestion can no longer be cancelled.` | `ai.cancel.notAllowed` | backend key |
| `Transport AI baseline restore requires manual review.` | `ai.errors.baselineRestoreError` | backend key (Mod 12) |
| `The transport AI suggestion can no longer be applied.` | `ai.apply.notAllowed` | backend key |
| `The transport AI suggestion cannot be applied because its payload is invalid.` | `ai.apply.invalidPayload` | backend key |
| `The transport AI suggestion could not be materialized for apply.` | `ai.apply.materializeFailed` | backend key |
| `The transport AI suggestion could not be validated against the current operational snapshot.` | `ai.apply.validationFailed` | backend key |
| `The transport AI suggestion could not be approved against the current operational snapshot.` | `ai.apply.approvalFailed` | backend key |
| `The transport AI suggestion could not be applied because the operational state changed.` | `ai.apply.stateChanged` | backend key |
| `Transport AI runtime preflight failed.` | `ai.preflight.failed` | backend key |
| `Transport AI runtime admission is blocked by the concurrency limit.` | `ai.preflight.concurrencyBlocked` | backend key |

---

## Grupo D — Atributos de acessibilidade (`aria-label`, `title`, `placeholder`)

### D.1 Cobertos por applyStaticTranslations() (com acesso declarativo ou por seletor unico)

| Atributo | Elemento | Chave atual | Status |
|---|---|---|---|
| `aria-label` | `#tela01` (layout) | `layout.transportLayout` | ✓ |
| `aria-label` | `[data-transport-topbar]` | `layout.quickActions` | ✓ |
| `aria-label` | `[data-ai-menu-trigger]` | `ai.openMenuAria` | ✓ |
| `aria-label` | `[data-ai-menu]` | `ai.menuAria` | ✓ |
| `aria-label` | `[data-date-panel]` | `layout.selectedServiceDate` | ✓ |
| `aria-label` | `[data-date-shift="-1"]` | `layout.previousServiceDate` | ✓ |
| `aria-label` | `[data-date-link]` | `layout.returnServiceDateToToday` | ✓ |
| `aria-label` | `[data-date-shift="1"]` | `layout.nextServiceDate` | ✓ |
| `aria-label` | `.transport-topbar-auth` | `layout.transportAccessFields` | ✓ |
| `aria-label` | `[data-request-user-link]` | `layout.requestUserCreation` | ✓ |
| `aria-label` | `[data-resize="horizontal"]` | `layout.resizeMenuMain` | ✓ |
| `aria-label` | `#tela01principal` | `layout.transportMainPanels` | ✓ |
| `aria-label` | `.transport-request-section` (extra) | `layout.extraCarRequests` | ⚠ indice `[0]` |
| `aria-label` | `.transport-request-section` (weekend) | `layout.weekendCarRequests` | ⚠ indice `[1]` |
| `aria-label` | `.transport-request-section` (regular) | `layout.regularCarRequests` | ⚠ indice `[2]` |
| `aria-label` | `[data-resize="vertical"]` | `layout.resizeColumns` | ✓ |
| `aria-label` | `#tela01main_dir` | `layout.transportCarPanels` | ✓ |
| `aria-label` | `[data-open-vehicle-modal="extra"]` | `vehicles.addAria.extra` | ✓ via forEach |
| `aria-label` | `[data-open-vehicle-modal="weekend"]` | `vehicles.addAria.weekend` | ✓ via forEach |
| `aria-label` | `[data-open-vehicle-modal="regular"]` | `vehicles.addAria.regular` | ✓ via forEach |
| `aria-label` | `[data-open-settings-modal]` | `settings.openAria` | ✓ |
| `aria-label` | `[data-close-settings-modal].transport-modal-close` | `settings.closeAria` | ✓ |
| `aria-label` | `[data-close-vehicle-modal].transport-modal-close` | `modal.closeVehicleAria` | ✓ |
| `aria-label` | `[data-close-ai-settings-modal].transport-modal-close` | `ai.settingsCloseAria` | ✓ |
| `aria-label` | `[data-close-ai-agent-modal].transport-modal-close` | `ai.agentSettingsCloseAria` | ✓ via applyStaticTranslations mas PT no HTML |
| `aria-label` | `[data-close-ai-changes-modal].transport-modal-close` | `ai.changesCloseAria` | ✓ via applyStaticTranslations mas PT no HTML |
| `aria-label` | `.transport-footer-status` | `layout.transportNotifications` | ✓ |
| `placeholder` | `[data-ai-settings-api-key]` | `ai.settingsApiKeyPlaceholder` | ✓ |
| `aria-label` | `[data-settings-arrive-at-work-time]` | `settings.arriveAtWorkTime` | ✓ |
| `aria-label` | `[data-settings-extra-car-tolerance]` | `settings.extraCarTolerance` | ✓ |
| `aria-label` | `[data-route-time-input]` | cobertura a verificar | ⚠ |

### D.2 Nao cobertos por applyStaticTranslations()

| Atributo | Elemento | Chave alvo | Status |
|---|---|---|---|
| `aria-label` | `[data-ai-changes-side-note]` (Review surface note) | `ai.review.surfaceNoteAria` | ✗ hard-coded |
| `aria-label` | `[data-ai-changes-tabs]` (AI suggestion sections) | `ai.review.tabsAria` | ✗ hard-coded |

---

## Resumo de gaps por superficie

| Superficie | Gap principal | Prompt alvo |
|---|---|---|
| HTML inicial com PT | AI Agent modal, AI Changes modal em Portugues antes do JS | Prompt 3 |
| HTML nao coberto | Review contract, summary cards, tabs, panel headings, empty states | Prompt 3 |
| Acesso fragil | `modalFieldLabels[0..7]`, `requestSectionTitles[0..2]`, `paneLinks[0..2]`, `authLabels[0..1]`, etc. | Prompt 3 |
| DOM dinamico | Badges de custo, ETA/ETD, Extra Temporal Clusters, Anchors | Prompt 4 |
| Backend | Todos os `message` em `transport.py` e `transport_ai.py` | Prompt 5 |
| Acessibilidade descoberta | 2 aria-labels nao cobertos no review | Prompt 3 |
| Acessibilidade PT no HTML | 2 aria-labels em Portugues (Fechar ajustes, Fechar alterações) | Prompt 3 |

---

## Guia para os proximos prompts

**Prompt 2 (catalogo i18n):** reorganizar namespaces. Chaves novas de maior prioridade: `ai.review.badges.*`, `ai.review.etaLabel`, `ai.review.etdLabel`, `ai.review.extraTemporalClusters`, `ai.review.anchorsLabel`, `ai.review.contract.*`, `ai.review.panels.*`, `ai.review.tabs.*`, `ai.review.summary.*`.

**Prompt 3 (HTML estatico declarativo):** substituir acesso por indice em `applyStaticTranslations()` por `data-i18n-text`, `data-i18n-aria-label`, `data-i18n-placeholder`; corrigir PT hard-coded no HTML (AI Agent modal, AI Changes modal, canonical row contract).

**Prompt 4 (DOM dinamico):** migrar literais do Grupo B para `t()` — badges de custo, ETA/ETD, clusters, anchors.

**Prompt 5 (backend):** estruturar rotas de `transport.py` e `transport_ai.py` com `message_key + message_params` usando as chaves do Grupo C.

**Fronteira critica entre copy e dominio:** `OpenAI` e `DeepSeek` sao marcas, nao labels. Identificadores de modelo (`gpt-5.4-*`) e codigos de moeda nunca entram no catalogo de traducao. Nomes de projeto, usuario e placa renderizados diretamente da API nunca sao traduzidos.
