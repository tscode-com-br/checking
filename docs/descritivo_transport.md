# Descritivo do Dashboard de Transporte

## 1. Visão geral

O dashboard de transporte é uma aplicação estática servida pela API FastAPI na rota `/transport`, publicada em produção sob o prefixo `/checking/transport`, resultando na URL:

`https://www.tscode.com.br/checking/transport`

Ele foi implementado sem framework frontend. A tela é composta por três arquivos principais em `sistema/app/static/transport`:

- `index.html`: estrutura da interface.
- `styles.css`: layout, responsividade e aparência.
- `app.js`: estado global, integração com a API, renderização, drag and drop, SSE e regras de interação.
- `i18n.js`: dicionários e configuração de idiomas.

No backend, a integração passa principalmente por:

- `sistema/app/main.py`: monta o site estático em `/transport`.
- `sistema/app/routers/transport.py`: expõe os endpoints `/api/transport/*`.
- `sistema/app/services/transport.py`: concentra a lógica de negócio do dashboard.
- `sistema/app/schemas.py`: define os contratos de entrada e saída.

O dashboard não é uma SPA com roteamento interno. Trata-se de uma única página estática, cujo comportamento é controlado inteiramente pelo `app.js`.

## 2. Artefatos auxiliares para agentes

Para facilitar consumo por agentes e automações, agora existem dois artefatos complementares ao descritivo principal:

- `docs/catalogo_acoes_transport.yaml`: catálogo declarativo de ações operacionais do dashboard, com propósito, endpoint, entradas, pré-condições, efeitos colaterais e resultado esperado.
- `sistema/app/static/transport/functions/functions_by_capability.md`: índice navegável das 192 funções nomeadas agrupadas por capacidade funcional, em vez de apenas por ordem de aparição no código.

Esses dois arquivos não substituem este descritivo. O YAML serve como superfície operacional mais estável para agentes; o índice por capacidades serve como mapa de navegação para aprofundamento técnico e rastreamento das implementações reais.

## 3. Como a página é servida

Em `sistema/app/main.py`, a aplicação inclui o roteador de transporte e monta o diretório estático em `/transport`.

Resumo do fluxo de entrega:

1. A API FastAPI sobe com `SessionMiddleware` habilitado.
2. O roteador `transport.py` expõe os endpoints `/api/transport/*`.
3. O diretório `sistema/app/static/transport` é montado como site estático em `/transport`.
4. Em produção, o reverse proxy publica esse conjunto sob o prefixo `/checking`.

Há um detalhe importante de implantação: o frontend usa `<base href="./transport/">` no HTML e, no JavaScript, usa o prefixo relativo `../api/transport` para falar com a API. Isso foi claramente pensado para funcionar corretamente sob prefixos como `/checking`.

## 4. Arquitetura do frontend

### 4.1. Estrutura visual

O `index.html` organiza a tela em quatro regiões principais:

1. Barra superior (`transport-topbar`)
   - Branding do dashboard.
   - Link para o modal de configurações.
   - Navegação de data anterior/atual/próxima.
   - Campo inline de horário `Work to Home Time`, visível somente com sessão autenticada.
   - Campos de autenticação (`key` e `pass`).
   - Botão `+` para abrir a página administrativa quando ainda não há sessão autenticada.

2. Coluna esquerda
   - Botão para abrir a lista de projetos.
   - Filtro por projeto, controlado no cliente.
   - Três listas de solicitações: `EXTRA`, `WEEKEND` e `REGULAR`.

3. Coluna direita
   - Três painéis de veículos: `Extra Transport List`, `Weekend Transport List` e `Regular Transport List`.
   - Cada painel possui botão `+` para criação de veículo.
   - Cada painel pode alternar entre visualização em grade e visualização de gerenciamento em tabela.

4. Área de status no rodapé
   - Exibe mensagens operacionais, de erro, sucesso ou aviso.

Além disso, a tela possui divisores redimensionáveis horizontais e verticais, controlados por JavaScript.

### 4.2. Modais

Existem dois modais principais:

- Modal de veículo
  - Cria veículos `regular`, `weekend` ou `extra`.
  - Exibe campos adicionais conforme o escopo selecionado.
  - Para `extra`, exige data, horário de saída e trajeto.
  - Para `weekend`, exige persistência em sábado, domingo ou ambos.
  - Para `regular`, permite definir os dias úteis persistentes.

- Modal de configurações
  - Define idioma.
  - Define horário base `Work to Home Time`.
  - Define `Last Update Time`.
  - Define quantidade padrão de assentos por tipo de veículo.
  - Define tolerância padrão em minutos.

### 4.3. Estado do frontend

O `app.js` centraliza quase tudo em um controlador criado por `createTransportPageController(dateStore)`. Esse controlador mantém um estado global com, entre outros, os seguintes campos:

- `isAuthenticated`
- `authenticatedUser`
- `dashboard`
- `settingsLoaded`, `settingsLoading`, `settingsSaving`
- `routeTimeSaving`
- `languageLoading`
- `selectedRouteKind`
- `projectVisibility`
- `vehicleViewModes`
- `dragRequestId`
- `pendingAssignmentPreview`
- `expandedVehicleKey`
- `realtimeEventStream`

O arquivo é grande e monolítico. Não há separação por módulos, componentes ou camadas formais no frontend.

## 5. Ciclo de inicialização da página

Quando o DOM fica pronto, `initTransportPage()` executa este fluxo:

1. Cria um `dateStore` com a data atual.
2. Inicializa os painéis de data.
3. Ativa os divisores redimensionáveis.
4. Cria o controlador principal da página.
5. Inscreve a data selecionada para recarregar o dashboard a cada mudança.
6. Chama `bootstrapTransportSession()` para descobrir se já existe sessão de transporte em cookie.

Comportamentos importantes desse ciclo:

- A data selecionada não é restaurada do `localStorage` no carregamento.
- A cada reload da página, a tela volta para a data atual.
- O idioma, por outro lado, é persistido em `localStorage`.
- Se a sessão já existir, o frontend carrega o dashboard e as configurações em paralelo.
- Se não existir sessão, o dashboard é mantido bloqueado.

## 5. Como a integração com a API funciona

### 5.1. Padrão de requisição HTTP

O frontend usa uma função utilitária `requestJson(url, options)` que:

- sempre envia `credentials: "same-origin"`;
- adiciona `Accept: application/json`;
- adiciona `Content-Type: application/json` quando há corpo;
- tenta converter a resposta para JSON;
- levanta erro JavaScript com `status` e `payload` quando a resposta não é `2xx`.

Esse detalhe é importante porque a autenticação do dashboard depende de sessão cookie, não de token bearer.

### 5.2. Autenticação

O dashboard possui autenticação própria de transporte, baseada em:

- `chave` do usuário;
- `senha` do usuário;
- permissão validada no backend por `user_has_transport_access(...)`.

Fluxo observado:

1. Ao digitar nos campos `key` e `pass`, o frontend agenda uma verificação com debounce de 140 ms.
2. O backend valida a chave, a senha e a permissão de transporte.
3. Em caso de sucesso, grava `request.session["transport_user_id"]`.
4. O frontend passa a tratar a sessão como autenticada, carrega o dashboard, carrega as configurações e abre o canal SSE.
5. Em caso de `401`, o frontend derruba a sessão local, chama `POST /api/transport/auth/logout` e volta a bloquear a tela.

### 5.3. Atualização em tempo real

Após autenticar, o frontend abre um `EventSource` para `/api/transport/stream`.

Características relevantes:

- O backend usa `StreamingResponse` com `text/event-stream`.
- O broker usado é o `admin_updates_broker`.
- O frontend não interpreta o conteúdo do evento; qualquer mensagem recebida dispara apenas um refresh do dashboard com debounce de 180 ms.
- Isso significa que o frontend opera em modelo de revalidação completa, e não em aplicação incremental de patches.

### 5.4. Carregamento do dashboard

O eixo central da tela é a função `loadDashboard(selectedDate, options)`.

Ela:

1. Calcula `service_date` no formato ISO.
2. Obtém `route_kind` via `getSelectedRouteKind()`.
3. Chama `GET /api/transport/dashboard`.
4. Atualiza `state.dashboard`.
5. Reconcilia a visibilidade dos projetos.
6. Atualiza o horário efetivo `work_to_home_departure_time`.
7. Re-renderiza listas de solicitações, listas de veículos e filtros.

Observação importante: a API ainda aceita `route_kind`, mas a tela atual não expõe mais um seletor visual de rota. Na prática, o JavaScript mantém `home_to_work` como padrão. A infraestrutura de rota ainda existe no contrato, mas a UI atual não a torna configurável pelo operador.

## 6. Endpoints efetivamente usados pelo dashboard

Os endpoints abaixo são os que o frontend estático em `sistema/app/static/transport/app.js` realmente consome hoje.

| Método | Endpoint | Uso na tela | Requer sessão |
| --- | --- | --- | --- |
| `GET` | `/api/transport/auth/session` | Descobrir se já existe sessão válida ao abrir a página. | Não |
| `POST` | `/api/transport/auth/verify` | Validar `chave` + `senha` digitadas no topo da tela. | Não |
| `POST` | `/api/transport/auth/logout` | Encerrar sessão ao perder autenticação ou expirar a sessão. | Não |
| `GET` | `/api/transport/stream` | Receber eventos SSE e disparar refresh do dashboard. | Sim |
| `GET` | `/api/transport/dashboard` | Carregar todo o estado operacional da tela para a data selecionada. | Sim |
| `GET` | `/api/transport/settings` | Ler as configurações globais do modal de settings. | Sim |
| `PUT` | `/api/transport/settings` | Salvar configurações globais do modal de settings. | Sim |
| `PUT` | `/api/transport/date-settings` | Salvar o horário `Work to Home Time` apenas para a data selecionada. | Sim |
| `POST` | `/api/transport/vehicles` | Criar veículo e respectivas agendas persistentes ou avulsas. | Sim |
| `DELETE` | `/api/transport/vehicles/{schedule_id}?service_date=YYYY-MM-DD` | Excluir veículo a partir do `schedule_id` selecionado na UI. | Sim |
| `POST` | `/api/transport/assignments` | Confirmar alocação ou devolver solicitação para `pending`. | Sim |
| `POST` | `/api/transport/requests/reject` | Rejeitar uma solicitação a partir do dashboard. | Sim |

### 6.1. Endpoints existentes no módulo, mas não usados pela tela estática atual

O roteador de transporte expõe alguns endpoints que não são chamados pelo dashboard estático atual:

| Método | Endpoint | Situação atual |
| --- | --- | --- |
| `GET` | `/api/transport/exports/transport-list` | Existe no backend, mas o frontend estático atual não chama esse endpoint. |
| `GET` | `/api/transport/workplaces` | Existe no backend, mas o frontend estático atual não faz chamada dedicada para essa rota. |
| `POST` | `/api/transport/workplaces` | Existe no backend, mas não há formulário nem ação na página para criar workplace. |

Apesar disso, o payload de `GET /api/transport/dashboard` já inclui `workplaces`. O JavaScript atual, porém, não usa esse trecho do retorno para renderização visível.

## 7. Contrato central: `GET /api/transport/dashboard`

Esse endpoint é o coração do dashboard. O retorno segue o modelo `TransportDashboardResponse`.

Estrutura resumida:

```json
{
  "selected_date": "2026-04-28",
  "selected_route": "home_to_work",
  "work_to_home_departure_time": "16:45",
  "projects": [
    {
      "id": 1,
      "name": "P80",
      "country_code": "SG",
      "country_name": "Singapore",
      "timezone_name": "Asia/Singapore",
      "timezone_label": "Singapore (Asia/Singapore)"
    }
  ],
  "regular_requests": [],
  "weekend_requests": [],
  "extra_requests": [],
  "regular_vehicles": [],
  "weekend_vehicles": [],
  "extra_vehicles": [],
  "regular_vehicle_registry": [],
  "weekend_vehicle_registry": [],
  "extra_vehicle_registry": [],
  "workplaces": []
}
```

### 7.1. Listas de solicitações

Cada item de `regular_requests`, `weekend_requests` e `extra_requests` traz:

- `id`
- `request_kind`
- `requested_time`
- `service_date`
- `user_id`
- `chave`
- `nome`
- `projeto`
- `workplace`
- `end_rua`
- `zip`
- `assignment_status` (`pending`, `confirmed`, `rejected`, `cancelled`)
- `awareness_status` (`pending`, `aware`)
- `assigned_vehicle`
- `response_message`

Esses objetos alimentam diretamente a renderização das listas da coluna esquerda.

### 7.2. Listas de veículos

Cada item de `regular_vehicles`, `weekend_vehicles` e `extra_vehicles` traz:

- `id`
- `schedule_id`
- `placa`
- `tipo`
- `color`
- `lugares`
- `tolerance`
- `service_scope`
- `route_kind`
- `departure_time`

Esses itens alimentam a renderização em grade dos veículos.

### 7.3. Registro de veículos

Cada item de `regular_vehicle_registry`, `weekend_vehicle_registry` e `extra_vehicle_registry` traz:

- `vehicle_id`
- `schedule_id`
- `placa`
- `tipo`
- `lugares`
- `assigned_count`
- `service_date`
- `route_kind`
- `departure_time`

Esses itens são usados pela visualização em tabela de gerenciamento.

### 7.4. Projetos e workplaces

- `projects` é usado pela UI para montar o filtro de projeto.
- `workplaces` é retornado pelo backend, mas não é consumido visualmente pelo JavaScript atual.

## 8. Fluxos funcionais observados

### 8.1. Fluxo de autenticação

1. A página abre e chama `GET /api/transport/auth/session`.
2. Se já houver cookie válido, a sessão é reaproveitada.
3. Caso contrário, a tela fica bloqueada aguardando `key` e `pass`.
4. O operador digita os campos.
5. O frontend chama `POST /api/transport/auth/verify`.
6. Em caso de sucesso, carrega dashboard e settings.
7. Em caso de falha, mostra mensagem localizada.

### 8.2. Fluxo de refresh

O refresh do dashboard acontece em três situações principais:

- mudança manual de data;
- autenticação concluída com sucesso;
- chegada de evento SSE.

O padrão adotado é sempre recarregar o payload inteiro de `/api/transport/dashboard`.

### 8.3. Fluxo de configuração global

O modal de configurações usa:

- `GET /api/transport/settings` para carregar os valores atuais;
- `PUT /api/transport/settings` para persistir alterações globais.

Após salvar, o frontend também faz refresh do dashboard para refletir o novo horário e os novos defaults.

### 8.4. Fluxo de configuração por data

O horário inline do topo (`Work to Home Time`) usa `PUT /api/transport/date-settings`.

Esse endpoint é distinto do settings global e serve exclusivamente para sobrescrever o horário da data atualmente selecionada.

### 8.5. Fluxo de criação de veículo

Ao abrir o modal e salvar, o frontend monta um payload com base no escopo:

- `extra`
  - cria um único agendamento com `service_date`, `route_kind` e `departure_time`.

- `weekend`
  - cria agendas persistentes para sábado, domingo ou ambos;
  - o backend gera schedules para os dois trajetos.

- `regular`
  - cria agendas persistentes por dias úteis selecionados;
  - o backend também gera schedules para os dois trajetos.

Após salvar, a tela recarrega o dashboard. Se o veículo criado estiver em outra data efetiva, o frontend ajusta silenciosamente a data antes do reload.

### 8.6. Fluxo de alocação

O dashboard usa drag and drop:

1. O operador arrasta uma solicitação.
2. O veículo compatível vira alvo de drop.
3. Ao soltar, a UI não confirma imediatamente.
4. Primeiro ela abre um preview no detalhe do veículo.
5. Só ao clicar em `Confirm` é feito `POST /api/transport/assignments` com `status: "confirmed"`.

Há também o fluxo inverso, ao clicar no botão de remoção do passageiro dentro do painel de detalhes do veículo. Nesse caso, o frontend chama `POST /api/transport/assignments` com `status: "pending"`.

### 8.7. Fluxo de rejeição

Ao clicar em `X` em uma solicitação, o frontend chama `POST /api/transport/requests/reject`.

O endpoint foi mantido separado de `/assignments`, embora o schema de `/assignments` aceite outros status. Na UI atual, a rejeição usa sempre o endpoint dedicado.

### 8.8. Fluxo de exclusão de veículo

Ao excluir, a UI envia `DELETE /api/transport/vehicles/{schedule_id}` com `service_date` em query string.

No backend, a operação é forte: ela remove schedules, dependências relacionadas, assignments ligados ao veículo e limpa referências de placa em usuários que ainda apontem para esse veículo.

## 9. Regras de negócio importantes já embutidas no backend

Estas regras impactam diretamente qualquer alteração profunda no dashboard.

### 9.1. Resolução de `service_date` por tipo de solicitação

O backend não devolve simplesmente “as solicitações do dia”. Ele resolve uma `service_date` por linha de dashboard.

- `regular`
  - se a solicitação se aplica ao dia selecionado, usa esse dia;
  - se o dia selecionado for fim de semana, a solicitação regular continua visível;
  - se o dia útil selecionado não fizer parte dos dias escolhidos da solicitação, o backend devolve a próxima data aplicável.

- `weekend`
  - quando o dia selecionado não bate com sábado ou domingo válidos da solicitação, o backend devolve o próximo fim de semana aplicável.

- `extra`
  - sempre usa a data avulsa da própria solicitação.

### 9.2. Linhas somente leitura quando a data não coincide

No frontend, o drag and drop só é habilitado quando:

`requestRow.service_date === dashboard.selected_date`

Quando a solicitação aparece por antecipação, como no caso de `regular` ou `weekend`, a linha fica visível, mas em modo somente leitura.

### 9.3. Veículos `extra` aparecem independentemente da rota pedida no query string

Na composição do dashboard:

- `regular` e `weekend` são filtrados pelo `route_kind` solicitado;
- `extra` não é filtrado dessa forma e mantém `route_kind` explícito na própria linha.

Isso explica por que a UI ainda consegue exibir veículos extras de ambas as rotas, mesmo sem seletor global visível.

### 9.4. Confirmação recorrente propaga alocações

Para solicitações `regular` e `weekend`, confirmar uma alocação não afeta apenas a combinação pontual de data e rota.

O backend propaga a confirmação:

- para os dias persistentes compatíveis;
- para os dois trajetos (`home_to_work` e `work_to_home`) quando o schedule do veículo permitir.

Isso é uma regra estrutural importante do sistema atual.

### 9.5. Retornar para `pending` reseta recorrência

Quando a UI devolve uma solicitação recorrente (`regular` ou `weekend`) para `pending`, o backend não limpa apenas a rota clicada.

Ele reseta as assignments existentes da solicitação inteira para `pending`, de modo que o dashboard e o webapp do usuário voltem ao estado pendente.

### 9.6. Rejeição fecha a solicitação no contexto operacional

Ao rejeitar, o backend fecha as assignments relacionadas e, se necessário, materializa explicitamente uma assignment `rejected` para a combinação de data e rota alvo.

### 9.7. Contagem de ocupação considera apenas a data efetiva

Os registries de veículos calculam `assigned_count` levando em conta apenas os pedidos efetivamente aplicáveis à data selecionada.

Isso evita que uma solicitação recorrente visível fora da sua data de execução aparente ocupar vaga indevida.

### 9.8. Horário `Work to Home` por data sobrescreve o horário global

O horário exibido no topo e usado para veículos `regular` e `weekend` em `work_to_home` respeita esta precedência:

1. configuração específica da data selecionada;
2. configuração global;
3. fallback padrão do frontend.

### 9.9. Filtro de projeto é somente cliente

O backend envia todos os projetos e solicitações elegíveis. A ocultação por projeto é feita somente no navegador, via `state.projectVisibility`.

### 9.10. Botão de criação de usuário não usa API de transporte

O botão `+` ao lado do campo `key`, quando não autenticado, apenas abre `../admin` em nova aba. Não existe endpoint específico de “criar usuário” consumido por esse dashboard.

## 10. Endpoints em detalhe

### 10.1. `GET /api/transport/auth/session`

Retorna um `TransportSessionResponse` com:

- `authenticated`
- `user`
- `message`

É usado exclusivamente para bootstrap da sessão ao abrir a página.

### 10.2. `POST /api/transport/auth/verify`

Payload:

```json
{
  "chave": "HR70",
  "senha": "..."
}
```

Se a autenticação for aceita, o backend grava `transport_user_id` na sessão.

### 10.3. `GET /api/transport/dashboard`

Parâmetros usados pelo frontend:

- `service_date=YYYY-MM-DD`
- `route_kind=home_to_work`

Embora o contrato aceite `work_to_home`, a UI atual não oferece seletor global para alternar esse valor.

### 10.4. `GET /api/transport/settings`

Retorna:

- `work_to_home_time`
- `last_update_time`
- `default_car_seats`
- `default_minivan_seats`
- `default_van_seats`
- `default_bus_seats`
- `default_tolerance_minutes`

### 10.5. `PUT /api/transport/settings`

Atualiza exatamente o mesmo conjunto acima. A UI usa esse endpoint tanto para horários quanto para defaults de lugares e tolerância.

### 10.6. `PUT /api/transport/date-settings`

Payload:

```json
{
  "service_date": "2026-04-28",
  "work_to_home_time": "18:10"
}
```

Esse endpoint é exclusivo do ajuste de horário da data selecionada.

### 10.7. `POST /api/transport/vehicles`

Payload varia conforme o escopo, mas sempre inclui:

- `placa`
- `tipo`
- `color`
- `lugares`
- `tolerance`
- `service_scope`
- `service_date`

E, dependendo do caso:

- `route_kind`
- `departure_time`
- `every_saturday`
- `every_sunday`
- `every_monday` até `every_friday`

### 10.8. `DELETE /api/transport/vehicles/{schedule_id}`

O frontend envia também `service_date` como query string, mas a implementação atual do backend localiza a exclusão pelo `schedule_id`.

Na prática, a UI apaga o veículo inteiro a partir da agenda selecionada.

### 10.9. `POST /api/transport/assignments`

Schema aceito:

```json
{
  "request_id": 123,
  "service_date": "2026-04-28",
  "route_kind": "home_to_work",
  "status": "confirmed",
  "vehicle_id": 45,
  "response_message": null
}
```

O schema aceita `confirmed`, `rejected`, `cancelled` e `pending`, mas a UI estática atual usa esse endpoint principalmente para:

- confirmar (`confirmed`);
- devolver para fila (`pending`).

### 10.10. `POST /api/transport/requests/reject`

Payload:

```json
{
  "request_id": 123,
  "service_date": "2026-04-28",
  "route_kind": "home_to_work",
  "response_message": null
}
```

É o endpoint usado pelo botão de rejeição da lista de solicitações.

## 11. Pontos de atenção para alterações profundas

Como você informou que o dashboard passará por mudanças profundas, estes são os pontos mais sensíveis do desenho atual:

1. O frontend depende fortemente do shape de `TransportDashboardResponse`.
   - Mudanças de nome de campo ou de agrupamento vão impactar renderização, drag and drop, preview de veículo e contagem de ocupação.

2. O arquivo `app.js` concentra responsabilidades demais.
   - Estado, renderização, integração HTTP, SSE, validação de modal, i18n e layout estão no mesmo arquivo.
   - Se a tela crescer muito, tende a ficar difícil manter sem modularização.

3. O contrato ainda preserva abstrações de rota, mas a UI não expõe mais essa escolha.
   - Se o seletor de rota voltar, a base já existe no backend.
   - Hoje, porém, a tela opera na prática com `home_to_work` como rota preferida.

4. O refresh em tempo real sempre recarrega tudo.
   - Isso simplifica consistência, mas aumenta custo de renderização.
   - Caso vocês queiram uma UX mais responsiva, uma evolução natural seria introduzir atualização incremental.

5. A exclusão de veículo é destrutiva do ponto de vista de dados vinculados.
   - Qualquer mudança na UX de exclusão deve considerar que o backend atualmente apaga schedules, assignments e dependências associadas.

6. O backend já codifica regras de recorrência, ocupação e visibilidade que não estão óbvias no HTML.
   - Se o redesign for apenas visual, é possível preservar esse contrato.
   - Se o redesign for também conceitual, será necessário rever `services/transport.py`, não apenas a camada estática.

## 12. Arquivos estudados para este descritivo

- `sistema/app/static/transport/index.html`
- `sistema/app/static/transport/styles.css`
- `sistema/app/static/transport/app.js`
- `sistema/app/static/transport/i18n.js`
- `sistema/app/main.py`
- `sistema/app/routers/transport.py`
- `sistema/app/services/transport.py`
- `sistema/app/schemas.py`
- `tests/transport_page_date.test.js`
- `tests/test_api_flow.py`

## 13. Resumo executivo

Hoje o dashboard de transporte é um frontend estático, grande e centralizado em `app.js`, que consome 12 endpoints do namespace `/api/transport` para autenticação, carregamento do quadro, configurações, SSE, cadastro de veículos, alocação, devolução para pendente e rejeição.

O ponto mais importante para qualquer alteração profunda é que o comportamento visível da tela depende muito mais da composição feita pelo backend em `build_transport_dashboard(...)` e das regras de persistência de assignments do que do HTML em si. Em outras palavras: mexer apenas na camada visual não basta se a intenção for mudar o modelo operacional do dashboard.