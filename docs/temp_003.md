# Plano detalhado para flexibilizacao segura do cadastro de veiculos e extensao de Dashboard Settings

## 1. Escopo deste plano

Este documento descreve um plano minucioso para implementar, com seguranca, tres grupos de mudancas no dashboard `Transport`:

1. Permitir criacao de veiculos incompletos na `EXTRA TRANSPORT LIST`, exigindo apenas `Departure Date`, `Departure Time` e `Route`.
2. Permitir criacao de veiculos incompletos na `WEEKEND TRANSPORT LIST` e `REGULAR TRANSPORT LIST`, exigindo ao menos uma checkbox de persistencia marcada.
3. Estender `Dashboard Settings` para suportar variaveis de preco, moeda e custo padrao por tipo de veiculo.

O objetivo nao e apenas "fazer funcionar". O objetivo e executar as mudancas sem quebrar:

- criacao e edicao de veiculos ja existentes;
- regras atuais de persistencia `extra`, `weekend` e `regular`;
- renderizacao do dashboard;
- fluxo de `Dashboard Settings` e autosave atual;
- compatibilidade entre frontend, API, banco e testes.

## 2. Estado atual confirmado

### 2.1 Frontend do modal de veiculo

O formulario em `sistema/app/static/transport/index.html` hoje marca como obrigatorios:

- `Type`
- `Plate`
- `Color`
- `Places`
- `Tolerance`

Ja os campos especificos de `extra` (`Departure Date`, `Departure Time`, `Route`) sao exibidos condicionalmente.

As checkboxes de persistencia existem para `weekend` e `regular`.

### 2.2 Frontend de payload e validacao

Em `sistema/app/static/transport/app.js`:

- `buildVehicleCreatePayload(...)` sempre envia `tipo`, `placa`, `color`, `lugares` e `tolerance`.
- `resolveVehicleCreateValidationError(...)` hoje ja bloqueia:
  - `extra` sem `service_date`;
  - `extra` sem `departure_time`;
  - `weekend` sem `every_saturday` e `every_sunday`;
  - `regular` sem nenhum dia util selecionado.

Ou seja: a regra de persistencia minima ja existe, mas o restante do stack ainda pressupoe veiculo completo.

### 2.3 Backend de contrato

Em `sistema/app/schemas.py`:

- `TransportVehicleBaseData` exige:
  - `placa`
  - `tipo`
  - `color`
  - `lugares`
  - `tolerance`
- `TransportVehicleCreate` herda essa obrigatoriedade.
- `TransportVehicleUpdate` tambem herda essa obrigatoriedade.

Consequencia direta: mesmo que o frontend pare de exigir os campos, a API continuara recusando payloads incompletos.

### 2.4 Backend de persistencia

Em `sistema/app/models.py`, a tabela `vehicles` hoje exige:

- `placa` nao nula e unica;
- `tipo` nao nulo;
- `lugares` nao nulo com `1 <= lugares <= 99`;
- `tolerance` nao nulo com `0 <= tolerance <= 240`;
- `color` ja e nullable no banco.

Em `sistema/app/services/transport_vehicle_operations.py`:

- a criacao tenta reutilizar ou bloquear por `placa`;
- a identidade operacional ainda depende fortemente de `placa` quando presente.

Consequencia direta: permitir `placa` em branco sem redesenho controlado quebra unicidade, reuso e conflitos de cadastro.

### 2.5 Renderizacao atual de veiculos

Em `sistema/app/static/transport/app.js`:

- `createVehicleTile(...)` usa `vehicle.placa` diretamente no tile;
- `createVehicleManagementTable(...)` usa `rowData.placa` diretamente na tabela de gerenciamento;
- nao existe helper central para exibir placeholders localizados como `Waiting`.

### 2.6 Dashboard Settings atual

Hoje o contrato `/api/transport/settings` cobre apenas:

- `work_to_home_time`
- `last_update_time`
- `default_*_seats`
- `default_tolerance_minutes`

Isso esta distribuido entre:

- `sistema/app/schemas.py`
- `sistema/app/routers/transport.py`
- `sistema/app/services/location_settings.py`
- `MobileAppSettings` em `sistema/app/models.py`
- markup e autosave em `sistema/app/static/transport/index.html` e `app.js`

Hoje nao existe qualquer suporte a:

- moeda selecionada;
- unidade de cobranca (`hour`, `day`, `week`, `month`);
- custo por tipo de veiculo;
- catalogo dinamico de moedas.

## 3. Principios de seguranca obrigatorios

1. Nao persistir a string localizada `Waiting` no banco.
2. Nao usar "gambiarras" como salvar `WAITING` em `placa`, `color` ou `tipo` como se fossem dados reais.
3. Nao permitir que um veiculo com dados operacionais incompletos seja alocavel sem uma regra explicita.
4. Fazer rollout em ordem compativel: banco e backend primeiro, frontend permissivo depois.
5. Manter validacao server-side mesmo que o frontend valide antes.
6. Tratar `Waiting` como representacao de exibicao, nao como valor de dominio.

## 4. Decisao de desenho recomendada

### 4.1 Estrategia recomendada

Para suportar cadastro incompleto com seguranca, a recomendacao e:

- permitir campos de base nulos ou ausentes no dominio do veiculo;
- derivar o estado "pendente" a partir desses campos nulos;
- renderizar `Waiting` somente na UI;
- bloquear a alocacao de veiculos incompletos ate que os dados minimos operacionais sejam preenchidos.

### 4.2 Estrategias que nao devem ser adotadas

Nao adotar estas abordagens:

- salvar `Waiting` literalmente no banco;
- gerar `placa = WAITING-123` como dado definitivo;
- manter `lugares = 1` ou `tolerance = 0` apenas para satisfazer constraint e fingir que o valor existe;
- traduzir `Waiting` no backend e persistir a traducao.

Essas solucoes parecem simples, mas criam ambiguidade, risco operacional e regressao em validacoes futuras.

### 4.3 Regra operacional recomendada para veiculos incompletos

Recomendacao de seguranca:

- o veiculo pode ser cadastrado e editado mesmo incompleto;
- o veiculo aparece na lista com `Waiting` nos campos ausentes;
- o veiculo nao pode receber alocacoes enquanto faltar qualquer dado operacional critico.

Definicao recomendada de "pronto para alocacao":

- `tipo` preenchido;
- `placa` preenchida;
- `lugares` preenchido;
- `tolerance` preenchido;
- para `extra`, os campos especificos de agenda (`service_date`, `departure_time`, `route_kind`) ja continuarao obrigatorios.

`color` pode ser tratada como dado visual nao bloqueante, se o produto quiser permitir alocacao mesmo com cor pendente. Se a operacao exigir cor, entao ela tambem deve entrar no gate de prontidao.

## 5. Plano de execucao detalhado

## 5.1 Fase 0 - Baseline e congelamento de comportamento atual

Resumo do que foi executado na fase 0:

1. Foi feito o mapeamento dos pontos de controle reais do dashboard no codigo atual:
   - autenticacao e sessao em `/api/transport/auth/session` e `/api/transport/auth/verify`;
   - criacao de veiculo via `POST /api/transport/vehicles`;
   - leitura e autosave de configuracoes via `GET /api/transport/settings` e `PUT /api/transport/settings`;
   - alternancia entre tiles e management table no frontend de `/transport`.

2. O preview local foi validado com a stack atual em SQLite de homologacao local, sem alteracoes de codigo:
   - o dashboard abriu corretamente em `/transport`;
   - a autenticacao de transporte foi confirmada com o usuario bootstrap presente no ambiente local;
   - apos autenticar, o campo inline `Work to Home Time` foi habilitado e o dashboard carregou sem erro.

3. O fluxo atual de `Dashboard Settings` foi validado manualmente no browser:
   - o modal carrega `Languages`, `Work to Home Time`, `Last Update Time`, `Car/Minivan/Van/Bus default places` e `Standard Tolerance`;
   - o `GET /api/transport/settings` retornou o shape atual sem campos de moeda ou preco;
   - o autosave em `change` foi confirmado alterando `Last Update Time` de `16:00` para `16:05` e depois revertendo para `16:00`.

4. Os payloads reais de `PUT /api/transport/settings` foram capturados no browser. O shape observado hoje e:

```json
{
  "work_to_home_time": "16:45",
  "last_update_time": "16:00",
  "default_car_seats": 3,
  "default_minivan_seats": 6,
  "default_van_seats": 10,
  "default_bus_seats": 40,
  "default_tolerance_minutes": 5
}
```

5. O fluxo atual de criacao completa de veiculos foi validado manualmente nos tres escopos, com captura de payload real no browser:
   - `extra` abre com `tipo=carro`, `lugares=3`, `tolerance=5`, `service_date` predefinida para a data selecionada, `route_kind=home_to_work` e `departure_time` vazio;
   - `weekend` abre com `tipo=carro`, `lugares=3`, `tolerance=5` e ambas as checkboxes de persistencia desmarcadas;
   - `regular` abre com `tipo=carro`, `lugares=3`, `tolerance=5` e segunda a sexta marcados por padrao.

6. Os payloads reais atuais de `POST /api/transport/vehicles` foram capturados e congelados como baseline:

```json
{
  "service_scope": "extra",
  "service_date": "2026-04-29",
  "tipo": "carro",
  "placa": "PH0EX1",
  "color": "Black",
  "lugares": 3,
  "tolerance": 5,
  "route_kind": "home_to_work",
  "departure_time": "17:20"
}
```

```json
{
  "service_scope": "weekend",
  "service_date": "2026-04-29",
  "tipo": "carro",
  "placa": "PH0WE1",
  "color": "Blue",
  "lugares": 3,
  "tolerance": 5,
  "every_saturday": true,
  "every_sunday": false
}
```

```json
{
  "service_scope": "regular",
  "service_date": "2026-04-29",
  "tipo": "carro",
  "placa": "PH0RG1",
  "color": "White",
  "lugares": 3,
  "tolerance": 5,
  "every_monday": true,
  "every_tuesday": true,
  "every_wednesday": true,
  "every_thursday": true,
  "every_friday": true
}
```

7. A renderizacao baseline foi confirmada no dashboard atual:
   - em modo tile, `extra` mostra placa, ocupacao, horario de saida e rota;
   - em modo tile, `regular` mostra placa, ocupacao e o horario efetivo derivado de `Work to Home Time`;
   - a management table e aberta clicando no titulo da lista, e hoje mostra:
     - para `extra`: tipo, placa, horario, ocupacao, `service_date`, rota e acao de excluir;
     - para `regular`: tipo, placa, horario, ocupacao e acao de excluir.

8. Foi confirmada uma nuance importante do comportamento atual: um veiculo `weekend` criado com sucesso em uma quarta-feira entra no registry retornado por `/api/transport/dashboard`, mas nao aparece na lista visual de `Weekend Transport List` para a data selecionada de quarta-feira. Esse comportamento foi observado e deve ser tratado como baseline de regressao.

9. Ao final da validacao, o estado temporario de homologacao foi restaurado:
   - os veiculos de teste criados para capturar os payloads foram removidos via `DELETE /api/transport/vehicles/{schedule_id}`;
   - `Last Update Time` foi revertido para `16:00`;
   - o dashboard foi recarregado e voltou ao estado limpo, sem veiculos de teste residuais.

10. Invariantes congelados para as proximas fases:
   - hoje o frontend envia todos os campos base de veiculo sempre preenchidos;
   - hoje a API exige todos os campos base de veiculo;
   - `extra` exige `service_date`, `departure_time` e `route_kind`;
   - `weekend` exige pelo menos uma checkbox de fim de semana;
   - `regular` abre com segunda a sexta marcados por padrao;
   - `Dashboard Settings` usa autosave por `change` e ainda nao conhece moeda, unidade nem preco.

## 5.2 Fase 1 - Tornar o dominio do veiculo compativel com cadastro parcial

Resumo do que foi executado na fase 1:

1. Banco e ORM:
   - `Vehicle` passou a aceitar `placa`, `tipo`, `lugares` e `tolerance` nulos em `sistema/app/models.py`.
   - Foi criada a migration `0043_allow_partial_transport_vehicle_base.py` para alinhar o banco real com o novo dominio.
   - A unicidade de `placa` deixou de ser global e passou a valer apenas quando a placa estiver preenchida, usando indice parcial.
   - Os `CHECK CONSTRAINTS` de `tipo`, `lugares` e `tolerance` foram ajustados para aceitar `NULL` e validar faixa apenas quando houver valor.

2. Contratos Pydantic:
   - `TransportVehicleBaseData`, `TransportVehicleCreate` e `TransportVehicleUpdate` passaram a aceitar base parcial.
   - Os rows retornados pela API agora aceitam campos nulos em `placa`, `tipo`, `lugares` e `tolerance`.
   - Foram adicionados os campos derivados `pending_fields` e `is_ready_for_allocation` em `TransportVehicleBaseRow`, `TransportVehicleRow` e `TransportVehicleManagementRow`.
   - `color` passou a entrar em `pending_fields`, mas a regra de prontidao operacional ficou restrita a `tipo`, `placa`, `lugares` e `tolerance`.

3. Servicos de veiculo:
   - O backend passou a normalizar campos vazios para `None` no fluxo de base do veiculo.
   - `create_transport_vehicle_registration(...)` so tenta localizar/reutilizar veiculo por placa quando `placa` vier preenchida.
   - Cadastros sem placa agora sempre geram um novo `Vehicle`, em vez de correr risco de reaproveitamento indevido.
   - `list_users_linked_to_vehicle(...)` deixou de casar usuarios por `placa = NULL`, evitando links falsos entre veiculos incompletos.
   - `update_transport_vehicle_base(...)` so verifica conflito de unicidade quando a nova placa vier preenchida.
   - O update agora bloqueia a degradacao de um veiculo pronto para um estado incompleto quando existirem assignments futuros confirmados.
   - A trava anterior de reducao de capacidade com assignments futuros confirmados foi preservada.

4. Consumers do dashboard, export e proposal:
   - Os builders de dashboard e management registry passaram a expor `pending_fields` e `is_ready_for_allocation`.
   - As ordenacoes Python do dashboard foram ajustadas para tolerar `placa = None`.
   - O export passou a calcular `remaining` como `None` quando `lugares` estiver ausente, em vez de quebrar em aritmetica.
   - A validacao de proposals agora rejeita veiculos que ainda nao estao prontos para alocacao.

5. Validacao executada:
   - Foram adicionados testes focados para cadastro parcial em `regular`, para garantir que cadastros sem placa nao reaproveitam veiculos existentes e para bloquear degradacao de veiculo pronto com assignments futuros.
   - O corte de regressao `pytest tests/test_api_flow.py -k 'transport_vehicle and (registration or update or dashboard or proposal)'` foi executado apos as mudancas, com `13 passed`.

## 5.3 Fase 2 - Regras de criacao para `EXTRA TRANSPORT LIST`

Resumo do que foi executado na fase 2:

1. Modal e markup:
   - Em `sistema/app/static/transport/index.html`, `Type`, `Plate`, `Color`, `Places` e `Tolerance` deixaram de ser campos HTML obrigatorios no formulario de criacao de veiculo.
   - O `select` de `Type` passou a incluir uma opcao vazia real, permitindo cadastro parcial sem reintroduzir automaticamente `carro`.
   - Os valores padrao visuais de `lugares=3` e `tolerance=5` foram preservados para manter o fluxo atual de preenchimento rapido quando o usuario quiser completar o cadastro.

2. Serializacao e comportamento do frontend:
   - Em `sistema/app/static/transport/app.js`, `buildVehicleCreatePayload(...)` passou a serializar campos base vazios como `null`, em vez de forcar `"carro"`, `""` ou `0`.
   - `syncVehicleTypeDependentDefaults(...)` deixou de converter tipo vazio para `carro`, o que permite ao usuario limpar o campo e mantê-lo realmente em branco.
   - A validacao de frontend para `extra` continuou restrita aos campos especificos do escopo (`service_date`, `departure_time` e `route_kind`), sem voltar a bloquear base parcial.

3. Traducao da nova opcao vazia:
   - Em `sistema/app/static/transport/i18n.js`, foi adicionada a chave `modal.options.blankType` nos idiomas ja suportados.
   - Em `applyStaticTranslations(...)`, a traducao das opcoes de tipo deixou de depender da posicao fixa no `select` e passou a usar o `value` de cada opcao, evitando quebra por causa da nova opcao vazia.

4. Backend e regressao:
   - O backend nao precisou de nova mudanca estrutural nesta fase porque a compatibilidade de dominio e contrato ja havia sido entregue na fase 1.
   - Foi adicionado teste de API em `tests/test_api_flow.py` cobrindo `POST /api/transport/vehicles` com `service_scope=extra` e base parcial, validando persistencia com campos nulos e retorno no dashboard com `pending_fields` e `is_ready_for_allocation = false`.

5. Validacao executada:
   - `node --test tests/transport_page_date.test.js` executado com sucesso (`50 passed`).
   - `pytest tests/test_api_flow.py -k "transport_extra_vehicle_registration"` executado com sucesso (`2 passed`).

## 5.4 Fase 3 - Regras de criacao para `WEEKEND` e `REGULAR`

Resumo do que foi executado na fase 3:

1. Confirmacao de compatibilidade no runtime:
   - Nao foi necessaria nova mudanca estrutural no modal ou no serializer, porque a flexibilizacao aplicada na fase 2 ja passou a valer tambem para `weekend` e `regular`.
   - Em `sistema/app/static/transport/app.js`, `buildVehicleCreatePayload(...)` ja estava serializando campos base vazios como `null` para todos os escopos, preservando apenas as checkboxes de persistencia de `weekend` e `regular`.
   - Em `resolveVehicleCreateValidationError(...)`, as regras de frontend permaneceram restritas a persistencia minima: `weekend` exige `every_saturday` e/ou `every_sunday`; `regular` exige ao menos um dia util marcado.

2. Backend validado sem reabrir dominio:
   - O backend ja estava compativel com base parcial desde a fase 1, entao nao houve nova alteracao em modelos, schemas ou services para esta fase.
   - A regra server-side de `weekend` continuou exigindo ao menos uma checkbox de fim de semana.
   - A regra server-side de `regular` continuou exigindo persistencia quando os campos de weekday sao enviados explicitamente pelo frontend, preservando a protecao atual sem remover o autofill legado para payloads que omitem esses campos.

3. Cobertura automatizada adicionada:
   - Em `tests/transport_page_date.test.js`, foram adicionados testes para garantir que `weekend` e `regular` tambem serializam base vazia como `null` sem perder as checkboxes selecionadas.
   - Na mesma suite frontend, foi adicionada cobertura para `resolveVehicleCreateValidationError(...)` confirmar que `weekend` e `regular` bloqueiam apenas ausencia de persistencia, e nao campos base vazios.
   - Em `tests/test_api_flow.py`, foi adicionado teste para cadastro parcial de veiculo `weekend` com retorno de `pending_fields` e `is_ready_for_allocation = false`.
   - Em `tests/test_api_flow.py`, foi adicionada cobertura para garantir que `regular` continua rejeitando payload com todos os weekdays explicitamente desmarcados.

4. Validacao executada:
   - `node --test tests/transport_page_date.test.js` executado com sucesso (`52 passed`).
   - `pytest tests/test_api_flow.py -k "partial_regular_vehicle or partial_weekend_vehicle or explicit_weekday_selection"` executado com sucesso (`3 passed`).

## 5.5 Fase 4 - Exibicao localizada de `Waiting`

Resumo do que foi executado na fase 4:

1. Helper central de placeholder no frontend:
   - Em `sistema/app/static/transport/app.js`, foram adicionados os helpers `isPendingVehicleField(...)`, `formatPendingVehicleField(...)` e `createWaitingNode(...)` para centralizar a deteccao e a exibicao de campos ausentes.
   - O helper passou a resolver `Waiting` no proprio frontend em tempo de renderizacao, com fallback seguro para o ambiente de testes em Node quando o dicionario de i18n nao estiver carregado.

2. Superficies atualizadas:
   - No tile principal do veiculo, `placa` ausente agora aparece como `Waiting` em vermelho, e a ocupacao deixa de cair em `0/0` quando `lugares` estiver ausente, passando a mostrar `assigned/Waiting`.
   - Na management table, `tipo`, `placa` e ocupacao tambem passaram a usar o placeholder localizado, com destaque visual dedicado para campos pendentes.
   - Em titulos e meta linhas montados com dados ausentes, o frontend deixou de concatenar valores nulos crus e passou a usar o mesmo helper, inclusive em `Assigned to {plate}` e no `vehicleButtonTitle`.
   - O painel de detalhes atual nao exibe hoje campos base de veiculo como `tipo`, `placa`, `color`, `lugares` ou `tolerance`; por isso, nesta fase nao houve nova regra visual especifica a aplicar dentro dele.

3. I18n e estilo:
   - Em `sistema/app/static/transport/i18n.js`, foram adicionadas as chaves `misc.waiting` e `misc.waitingAria` para todos os idiomas suportados.
   - Em `sistema/app/static/transport/styles.css`, foi criada a classe `.transport-pending-value`, usando `var(--transport-danger)` para destacar o placeholder em vermelho sem alterar o layout existente.

4. Cobertura e validacao:
   - Em `tests/transport_page_date.test.js`, foram adicionados testes para os helpers de campo pendente, para `formatVehicleOccupancyLabel(...)` e `formatVehicleOccupancyCount(...)` com `lugares` ausente, e para a presenca das novas chaves/estilo de placeholder.
   - `node --test tests/transport_page_date.test.js` executado com sucesso apos a implementacao (`54 passed`).

## 5.6 Fase 5 - Gate de seguranca para alocacao de veiculos pendentes

Fase 5 concluida. A alocacao operacional de veiculos pendentes passou a ser bloqueada no frontend e no backend usando a prontidao `is_ready_for_allocation` como fonte de verdade.

- `sistema/app/static/transport/app.js` ganhou os helpers `isVehicleReadyForAllocation(...)` e `getVehiclePendingAllocationMessage(...)`, passou a impedir drag and drop para veiculos incompletos, adicionou aviso no tooltip do tile e desabilitou a confirmacao manual no painel de detalhes quando houver pendencias.
- `sistema/app/static/transport/i18n.js` recebeu a mensagem `warnings.vehiclePendingAllocation` para os idiomas suportados, e o frontend tambem passou a localizar a resposta do backend `The selected vehicle is not ready for allocation.`.
- `sistema/app/services/transport_assignment_operations.py` passou a rejeitar alocacoes `confirmed` para veiculos sem os campos obrigatorios, reutilizando `is_transport_vehicle_ready_for_allocation(...)`; `sistema/app/routers/transport.py` converte essa rejeicao em HTTP 409 no endpoint `POST /api/transport/assignments`.
- Foram adicionadas regressoes em `tests/transport_page_date.test.js` e `tests/test_api_flow.py`, ambas aprovadas, cobrindo o bloqueio no helper de drop e a rejeicao da alocacao direta pela API.

## 5.7 Fase 6 - Extensao de `Dashboard Settings` para preco e moeda

Fase 6 concluida. `Dashboard Settings` passou a suportar moeda, unidade de cobranca e precos padrao por tipo de veiculo no backend e no frontend, preservando o autosave existente para o endpoint principal e isolando o cadastro de moeda em um endpoint proprio.

- Banco e modelos: `sistema/app/models.py` recebeu os campos `transport_price_currency_code`, `transport_price_rate_unit`, `transport_default_*_price` em `MobileAppSettings`, foi criado o modelo `TransportCurrencyOption`, e a migration `0044_add_transport_pricing_settings_and_currency_options.py` alinhou o schema real com essa estrutura.
- Contratos e services: `sistema/app/schemas.py` passou a expor `price_currency_code`, `price_rate_unit`, `default_*_price` e `available_currencies` em `TransportSettingsResponse` e `TransportSettingsUpdateRequest`, e ganhou `TransportCurrencyCreateRequest`/`TransportCurrencyOptionRow`; em `sistema/app/services/location_settings.py` foram adicionados helpers separados para leitura do snapshot completo, gravacao dos precos/unidade/moeda e criacao do catalogo de moedas com bloqueio de duplicidade.
- API: `sistema/app/routers/transport.py` manteve `GET /api/transport/settings` e `PUT /api/transport/settings` como contrato principal de autosave, agora com os novos campos de preco/moeda, e adicionou `POST /api/transport/settings/currencies` para cadastro dedicado de moeda; selecao de moeda inexistente e moeda duplicada passam a retornar HTTP 409 com mensagens controladas.
- Frontend: `sistema/app/static/transport/index.html` ganhou a linha `Price Variables`, select de moeda, select de unidade, botao sutil de adicionar moeda, painel inline para cadastro do codigo/rotulo e uma segunda coluna de inputs de preco ao lado dos campos de lugares; `sistema/app/static/transport/styles.css` recebeu o layout e responsividade desses novos controles.
- Comportamento no browser: `sistema/app/static/transport/app.js` passou a manter no estado local a moeda selecionada, a unidade de cobranca, os precos padrao e o catalogo carregado pela API; `syncSettingsControls()`, `readTransportSettingsDraft()`, `loadTransportSettings()` e `saveTransportSettings()` foram estendidos para o novo payload, e foi criado um fluxo dedicado para adicionar moeda e em seguida persistir a selecao no autosave normal.
- I18n e erros: `sistema/app/static/transport/i18n.js` recebeu labels novas para `Price Variables`, `Currency`, `Billing Unit`, `Per hour/day/week/month`, `Add currency`, `Save currency` e mensagens de erro para moeda invalida, duplicada ou indisponivel; `app.js` passou a localizar as respostas controladas do backend para esse fluxo.
- Validacao executada: `pytest tests/test_api_flow.py -k "transport_settings_endpoint_updates_work_to_home_boarding_time"` passou com o novo contrato de settings e com o endpoint de moedas; `node --test tests/transport_page_date.test.js` passou com os novos testes estaticos e de helper do modal; a checagem de erros dos arquivos alterados nao apontou problemas.

## 5.8 Fase 7 - Ajustes de UX e compatibilidade

Fase 7 concluida. Os ajustes finais de UX e compatibilidade passaram a separar o fluxo de criacao do fluxo de reabertura/edicao de veiculo pendente, mantendo os defaults apenas onde fazem sentido e acomodando melhor o modal de settings em larguras intermediarias e mobile.

- Modal de veiculo: `sistema/app/static/transport/app.js` passou a manter contexto explicito de `create` vs `edit`, com `vehicleModalMode` e `vehicleModalVehicleId`; o submit do modal agora usa `POST /api/transport/vehicles` para criacao e `PUT /api/transport/vehicles/{id}` para edicao de campos base, sem misturar agenda/persistencia nessa reabertura.
- Defaults do formulario: o prefill inicial de `Places` e `Tolerance` foi preservado apenas para o fluxo de criacao de veiculo novo; na reabertura de veiculo pendente, `tipo`, `placa`, `color`, `lugares` e `tolerance` passam a ser preenchidos exatamente com o snapshot salvo, mantendo vazios reais quando o dado ainda esta ausente. A troca de tipo continua podendo aplicar defaults, mas agora isso acontece apenas no `change` final do select, evitando reintroducao ruidosa durante digitacao/input intermediario.
- Reabertura de pendente: o painel de detalhes do veiculo ganhou um botao `Edit` apenas para veiculos com `pending_fields`; ao abrir esse fluxo, o modal mostra somente a edicao dos campos base, foca no primeiro campo pendente relevante e deixa regras de agenda/persistencia inalteradas para nao gerar expectativa de update parcial fora do contrato existente.
- Compatibilidade visual: `sistema/app/static/transport/styles.css` ampliou o `transport-settings-modal` para desktop, adicionou quebra antecipada em `@media (max-width: 960px)` para as linhas duplas de lugares/precos e para os controles inline de moeda, e fez o botao de adicionar moeda ocupar a largura disponivel nas larguras menores para evitar overflow lateral.
- I18n e copy: `sistema/app/static/transport/i18n.js` recebeu textos novos para `Edit Vehicle`, `Save Changes`, nota de edicao do modal, status de atualizacao e uma descricao mais precisa de `Vehicle Form Defaults`, esclarecendo que o prefill vale para novos veiculos e que a edicao preserva campos ausentes em branco.
- Validacao executada: `node --test tests/transport_page_date.test.js` passou com `60 passed`, incluindo novas regressoes para `buildVehicleBasePayload(...)`, `resolveVehicleEditFocusField(...)`, acao de `Edit` para veiculo pendente e colapso responsivo antecipado do modal de settings.

## 5.9 Fase 8 - Compatibilidade de UX, reabertura e defaults

Fase 8 concluida. O comportamento planejado para compatibilidade de UX e reabertura de veiculo pendente ja estava entregue pela implementacao da fase 7; nesta fase foi feito o fechamento dedicado com validacao automatizada e passada manual no preview isolado.

- Confirmacao de defaults: o fluxo de criacao de veiculo novo continua abrindo com `Type=Car`, `Places=3` e `Tolerance=5`, preservando o preenchimento rapido esperado para novos cadastros.
- Confirmacao de base parcial real: no preview manual, um veiculo `regular` foi criado com `Type`, `Plate`, `Places` e `Tolerance` vazios; o frontend persistiu esse estado sem reintroduzir defaults no payload salvo e o tile voltou a renderizar `Waiting` no dashboard como esperado.
- Confirmacao de reabertura: o painel de detalhes do veiculo pendente expôs a acao `Edit`, e a reabertura ocorreu em modo de edicao, com titulo/copy corretos e todos os campos base ainda ausentes preservados em branco no modal, sem voltar para os defaults de criacao.
- Confirmacao de responsividade/compatibilidade: a suite estatica de frontend foi reexecutada sem regressao, cobrindo `buildVehicleBasePayload(...)`, `resolveVehicleEditFocusField(...)`, a exposicao do botao `Edit` para pendentes e o comportamento responsivo do modal de settings.
- Validacao executada: `node --test tests/transport_page_date.test.js` passou novamente com `60 passed`; no preview local em `http://127.0.0.1:8010/transport`, o dashboard foi desbloqueado com o admin seedado e o fluxo de criar/reabrir um veiculo regular pendente foi confirmado manualmente.

## 5.10 Fase 9 - Testes, regressao e fechamento seguro

Fase 9 concluida. O fechamento final ganhou as regressoes backend que ainda faltavam para o contrato atual e uma rodada dedicada de validacao cobrindo cadastro parcial, bloqueios operacionais, settings e regressao de veiculos completos.

- Regressoes backend adicionadas: `tests/test_api_flow.py` recebeu `test_transport_vehicle_update_can_complete_pending_vehicle_and_expose_readiness_metadata`, cobrindo a edicao de um veiculo pendente ate o estado pronto sem recriar agendas, e `test_transport_settings_currency_endpoint_rejects_duplicate_currency_code`, cobrindo o `409` do endpoint dedicado de moedas em caso de duplicidade.
- Matriz automatizada executada: foi rodado um corte focado de `pytest` cobrindo cadastro parcial `extra`/`regular`/`weekend`, bloqueio de alocacao para veiculo nao pronto, update de campos base, conclusao de veiculo pendente, `Dashboard Settings`, cadastro duplicado de moeda e regressao de fluxo completo legado, com `10 passed`.
- Validacao frontend preservada: a suite `node --test tests/transport_page_date.test.js` permaneceu verde com `60 passed`, sustentando os contratos estaticos e de helper da fase 8.
- Preview isolado para regressao manual: como o ambiente local padrao continua apontando para Postgres em `@db`, foi usado um banco SQLite isolado (`preview_checking.db`) com `alembic upgrade head` e `APP_ENV=production` para validar manualmente `/api/health` e `/transport` em `:8010`, sem depender da stack Compose ou do processo travado em `:8000`.
- Fechamento seguro: com isso, os fluxos novos de veiculo parcial, o gate operacional de prontidao, o update de veiculo pendente e o contrato estendido de settings/moedas ficaram cobertos por teste e por uma passada manual real de carregamento do dashboard.

## 6. Matriz de testes recomendada

## 6.1 Backend/API

Adicionar cobertura em `tests/test_api_flow.py` ou arquivo novo equivalente para:

1. criar `extra` com apenas `service_date`, `departure_time` e `route_kind`;
2. criar `extra` sem `departure_time` e receber erro;
3. criar `weekend` com checkbox marcada e base incompleta;
4. criar `weekend` sem checkboxes e receber erro;
5. criar `regular` com ao menos um dia e base incompleta;
6. criar `regular` sem dias e receber erro;
7. editar veiculo pendente e preencher campos faltantes;
8. tentar apagar `placa` ou `lugares` de veiculo com assignments futuros e receber erro;
9. obter `/settings` com campos novos;
10. salvar `/settings` com moeda, unidade e precos;
11. cadastrar moeda duplicada e receber erro controlado;
12. confirmar que veiculos completos antigos continuam funcionando sem migracao manual de dados.

## 6.2 Frontend

Cobrir pelo menos:

1. `buildVehicleCreatePayload(...)` serializando `null` para campos vazios;
2. `resolveVehicleCreateValidationError(...)` mantendo regras por escopo;
3. renderizacao de `Waiting` traduzido ao trocar idioma;
4. CSS de placeholder vermelho;
5. bloqueio de drag and drop em veiculo pendente;
6. leitura e escrita dos novos campos de settings;
7. fluxo de adicionar nova moeda.

## 6.3 Regressao manual obrigatoria

Executar manualmente:

1. criar veiculo completo `extra`;
2. criar veiculo completo `weekend`;
3. criar veiculo completo `regular`;
4. editar veiculo completo existente;
5. abrir e salvar `Dashboard Settings` sem tocar em preco/moeda;
6. trocar idioma e verificar `Waiting` em todas as superficies;
7. confirmar que a pagina `/transport` continua carregando sem erro de inicializacao.

## 7. Ordem segura de implementacao e rollout

Ordem recomendada:

1. migration de banco para `vehicles` e `MobileAppSettings`;
2. modelos ORM e schemas Pydantic;
3. servicos de criacao/edicao de veiculo;
4. contratos `/settings` e endpoint de moedas;
5. frontend do modal de veiculo;
6. frontend de `Waiting` e gate de alocacao;
7. frontend de `Dashboard Settings`;
8. testes automatizados;
9. validacao manual no preview local;
10. deploy primeiro do backend, depois do frontend, se houver janela de incompatibilidade.

## 8. Checklist de aceite final

Considerar a entrega concluida apenas quando tudo abaixo for verdadeiro:

1. `EXTRA` permite cadastro com apenas `Departure Date`, `Departure Time` e `Route`.
2. `WEEKEND` exige pelo menos `Saturday` ou `Sunday`.
3. `REGULAR` exige pelo menos um dia util.
4. Campos base vazios nao impedem cadastro nos tres escopos.
5. Campos ausentes aparecem como `Waiting` em vermelho, traduzidos conforme idioma ativo.
6. Veiculos pendentes nao entram em alocacao enquanto faltarem dados operacionais criticos.
7. `Dashboard Settings` exibe variaveis de preco, moeda e unidade.
8. E possivel cadastrar nova moeda pelo botao dedicado.
9. Os quatro tipos de veiculo possuem campo de preco padrao persistido.
10. O autosave de settings continua funcional.
11. Nenhum fluxo antigo de veiculo completo foi quebrado.

## 9. Observacao final

O maior risco desta demanda nao esta no placeholder `Waiting`. O maior risco esta em desacoplar, com seguranca, o conceito de "veiculo cadastrado" do conceito de "veiculo operacionalmente pronto". Se esse desacoplamento for bem implementado, os tres pedidos passam a conviver com o dashboard atual sem introduzir dados falsos nem comportamento ambiguo.

## 10. Lista de verificacao por fases de implementacao

Use esta lista para conferir rapidamente o que ja foi implementado e o que ainda falta.

### Fase 0 - Baseline e congelamento de comportamento atual

- [x] O comportamento atual do dashboard `/transport` foi mapeado antes das alteracoes.
- [x] O fluxo atual de criacao de veiculos `extra`, `weekend` e `regular` foi validado e documentado.
- [x] O fluxo de leitura e escrita de `Dashboard Settings` foi validado e documentado.
- [x] A renderizacao baseline dos tiles e da management table foi validada e documentada.
- [x] Foram registrados comportamento atual confirmado, constraints reais do banco, validacoes frontend/backend existentes, pontos de risco para rollout e invariantes que nao poderiam quebrar.
- [x] A totalidade da Fase 0 foi implementada e consolidada no resumo da secao 5.1.

### Fase 1 - Banco, ORM e contratos para veiculo parcial

- [x] Fase 1 implementada e resumida na secao 5.2.

### Fase 2 - Criacao parcial para `EXTRA TRANSPORT LIST`

- [x] Fase 2 implementada e resumida na secao 5.3.

### Fase 3 - Criacao parcial para `WEEKEND` e `REGULAR`

- [x] Fase 3 implementada e resumida na secao 5.4.

### Fase 4 - Exibicao localizada de `Waiting`

- [x] Fase 4 implementada e resumida na secao 5.5.

### Fase 5 - Gate de seguranca para alocacao de veiculo pendente

- [x] Fase 5 implementada e resumida na secao 5.6.

### Fase 6 - Backend de `Dashboard Settings` para moeda e precos

- [x] Fase 6 implementada e resumida na secao 5.7.

### Fase 7 - Frontend de `Dashboard Settings` para moeda e precos

- [x] Fase 7 implementada e resumida na secao 5.8.

### Fase 8 - Compatibilidade de UX, reabertura e defaults

- [x] Fase 8 implementada e resumida na secao 5.9.

### Fase 9 - Testes, regressao e fechamento seguro

- [x] Fase 9 implementada e resumida na secao 5.10.