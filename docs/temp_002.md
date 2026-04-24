# Planejamento técnico - data de partida no cadastro de veículo extra do transporte

## Status deste documento

- Objetivo: planejar a alteração, não executar a alteração.
- Escopo: página `https://www.tscode.com.br/checking/transport`, com foco no cadastro de veículos da lista `EXTRA TRANSPORT LIST`.
- Base do plano: comportamento atual confirmado no frontend estático em `sistema/app/static/transport`, no backend FastAPI de transporte e nos testes automatizados existentes.

## Objetivo funcional

Implementar o seguinte comportamento no fluxo de cadastro de veículos extra:

1. No modal de cadastro aberto pelo `+` da `EXTRA TRANSPORT LIST`, inserir um campo de data imediatamente antes do campo `Departure Time`.
2. O administrador deve conseguir escolher explicitamente a data de partida do veículo extra, sem depender da data atualmente aberta no dashboard.
3. Ao clicar em `Save Vehicle`, o veículo extra deve ser criado apenas para a data escolhida no modal.
4. O veículo não deve aparecer em outras datas, mantendo a semântica atual de agenda `single_date`.
5. O fluxo de rota (`Home to Work` ou `Work to Home`) e horário de partida deve continuar funcionando exatamente como hoje.
6. O feedback visual da tela deve deixar claro que o cadastro foi salvo para a data escolhida, mesmo quando ela for diferente da data que estava aberta antes do modal.

## Estado atual confirmado no código

### Frontend do transporte

- O modal de cadastro de veículo em `sistema/app/static/transport/index.html` hoje mostra os campos `Type`, `Plate`, `Color`, `Places`, `Tolerance`, `Departure Time` e `Route` para `extra`, mas não possui campo de data editável para esse escopo.
- Em `sistema/app/static/transport/app.js`, a função `buildVehicleCreatePayload(formData, serviceDate, selectedRouteKind)` sempre injeta `service_date` a partir da data atual do dashboard, recebida pelo parâmetro `serviceDate`.
- Para `extra`, essa mesma função apenas acrescenta `route_kind` e `departure_time`; ela não lê nenhuma data do formulário porque esse campo ainda não existe.
- No submit do modal, o frontend envia `POST /api/transport/vehicles` e, em caso de sucesso, recarrega o dashboard com `loadDashboard(dateStore.getValue(), { announce: false })`, isto é, continua na data que estava aberta antes do submit.
- Ao abrir o modal `extra`, o código atual limpa o formulário com `form.reset()`, reaplica defaults de tipo, lugares e tolerância e coloca foco em `departure_time`.
- A memória do repositório já registra um gotcha importante desse modal: como `form.reset()` é usado, qualquer valor default visível precisa ser reposto de forma consistente no HTML e no JS ao abrir o modal.

### Backend já suporta a semântica de data única

- O schema `TransportVehicleCreate` em `sistema/app/schemas.py` já possui o campo `service_date: date`.
- Para `service_scope == "extra"`, o backend já exige `route_kind` e `departure_time` e usa `service_date` como parte do contrato.
- Em `sistema/app/services/transport.py`, a criação do cadastro transforma um veículo `extra` em uma agenda com:
  - `recurrence_kind = "single_date"`
  - `service_date = payload.service_date`
  - `route_kind = payload.route_kind`
  - `departure_time = payload.departure_time`
- A função `vehicle_schedule_applies_to_date()` compara agendas `single_date` por igualdade exata de data, então um veículo extra já aparece somente na data gravada.
- O builder do dashboard também respeita essa regra: veículos extra só entram na resposta quando a data solicitada no dashboard bate exatamente com `schedule.service_date`.
- O registry de veículos extra já expõe `service_date` e `route_kind`, o que confirma que a estrutura atual já sabe lidar com um veículo extra datado.

### Testes existentes que já travam o contrato atual

- `tests/test_api_flow.py` já valida que o cadastro de veículo `extra` cria agenda `single_date` com `service_date` persistido.
- `tests/test_api_flow.py` também já valida que veículos extra aparecem apenas nas datas corretas do dashboard e do registry.
- `tests/transport_page_date.test.js` atualmente valida que `buildVehicleCreatePayload()` envia `service_date` para `extra`, mas esse valor vem do parâmetro da data selecionada no dashboard, não de um campo do formulário.
- Não existe hoje teste de frontend cobrindo um campo editável de data dentro do modal `extra`.

## Diagnóstico técnico

O banco e a API já têm a semântica necessária para suportar a funcionalidade pedida. O gargalo real está no frontend:

1. a UI não expõe um campo de data para o cadastro `extra`
2. o payload ainda acopla `service_date` à data corrente do dashboard
3. o reload após salvar continua preso à data antiga da tela, o que faria um veículo salvo para outra data parecer "sumir"

Por isso, esta alteração não pede uma migration nova nem uma mudança estrutural de backend. O principal trabalho está em HTML, JS, i18n e testes de regressão.

## Decisão técnica recomendada

### Fonte de verdade

Manter a fonte de verdade atual:

- `payload.service_date` na API
- `transport_vehicle_schedules.service_date` no banco

Não criar nova coluna, não duplicar data em outro campo e não alterar a modelagem das agendas de transporte.

### UX recomendada para o modal `extra`

1. Inserir um novo campo `Departure Date` imediatamente antes de `Departure Time`.
2. Esse campo deve ficar visível apenas quando `service_scope === "extra"`.
3. Ao abrir o modal `extra`, preencher `Departure Date` com a data atual do dashboard.
4. Ao abrir o modal `extra`, o foco inicial deve ir para `Departure Date`, porque ela passa a ser a primeira decisão específica desse fluxo.
5. Se o administrador alterar a data e salvar com sucesso, o dashboard deve navegar automaticamente para a data escolhida antes de recarregar os dados, para que o veículo recém-criado apareça imediatamente.

### Regra de envio do payload

- Para `extra`, `service_date` deve vir do novo input do formulário.
- Para `regular` e `weekend`, `service_date` continua vindo da data selecionada no dashboard, preservando a semântica atual de data-base de início.

### Regra de validação

Para `extra`:

1. `Departure Date` obrigatória no frontend.
2. `Departure Time` obrigatório no frontend.
3. `Route` continua obrigatória no frontend.
4. O backend continua como guard-rail com o contrato atual; não é necessário mudar schema nem tabela para suportar essa entrega.

### Regra de visibilidade após salvar

Se o veículo extra for salvo para uma data diferente da data aberta no dashboard, o frontend deve trocar `dateStore` para a data escolhida e então chamar `loadDashboard()` nessa nova data.

Motivo dessa decisão:

- evita a percepção de falha no salvamento
- confirma visualmente a alocação na data correta
- reduz suporte manual e retrabalho do administrador

## Escopo detalhado por camada

## 1. Frontend - estrutura visual do modal

### Alteração principal em `index.html`

Adicionar um novo bloco de campo extra-only no modal de cadastro, imediatamente antes do bloco atual de `Departure Time`.

Recomendação de markup:

- `label.transport-field`
- atributo marcador dedicado, por exemplo `data-extra-service-date-field`
- `input type="date"`
- `name="service_date"`

Regras desse campo:

- hidden quando o modal não estiver em `extra`
- required apenas em `extra`
- disabled fora de `extra`
- valor inicial sincronizado pelo JS ao abrir o modal

### Impacto visual esperado

- A altura do modal aumenta um pouco.
- Em princípio, os estilos genéricos de `.transport-field` já devem acomodar o novo input sem nova folha de estilo.
- Ainda assim, será necessário validar manualmente responsividade e overflow em telas menores, porque a combinação `Departure Date + Departure Time + Route` aumenta a densidade do bloco extra.

## 2. Frontend - comportamento em `app.js`

### Refatoração do builder do payload

Hoje `buildVehicleCreatePayload()` recebe a data do dashboard por parâmetro e a usa para todos os escopos. O plano recomendado é:

1. Manter a data do dashboard como fallback geral.
2. Para `extra`, ler `formData.get("service_date")`.
3. Se esse valor estiver preenchido, usar esse valor como `payload.service_date`.
4. Se estiver vazio por algum motivo, bloquear o submit com mensagem amigável e foco no campo.

Isso pode ser implementado com uma pequena função auxiliar, por exemplo:

- resolver a data efetiva do cadastro por escopo
- manter a lógica de `regular` e `weekend` intacta
- evitar espalhar condições extras no submit

### Ajustes no ciclo de vida do modal

`syncVehicleModalFields(scope)` precisa passar a controlar também o novo campo de data:

1. mostrar e esconder o bloco da data
2. marcar `required` somente em `extra`
3. habilitar e desabilitar somente em `extra`
4. limpar o valor quando sair de `extra`, para não vazar estado entre escopos

`openVehicleModal(scope)` precisa:

1. preencher `service_date` com `getCurrentServiceDateIso()` quando `scope === "extra"`
2. manter os defaults atuais de tipo, lugares e tolerância
3. trocar o foco inicial de `departure_time` para `service_date`

### Ajustes no submit do modal

O submit deve ganhar uma validação local adicional para `extra`:

1. se `service_date` estiver vazia, exibir mensagem dedicada
2. focar o input de data
3. não enviar request

Depois do `POST` com sucesso:

1. se `payload.service_scope === "extra"`, atualizar a data selecionada do dashboard para `payload.service_date`
2. recarregar o dashboard nessa data
3. só depois anunciar status de sucesso, evitando reload visual incoerente

### Ponto de atenção com `form.reset()`

Como o modal usa `form.reset()`, o novo campo de data não pode depender apenas do valor digitado anteriormente. Ele precisa ser sempre reposto ao abrir o modal `extra`, senão o usuário pode reabrir o formulário e encontrar o campo vazio ou com um valor residual incorreto.

## 3. i18n - textos e mensagens

### Novos textos necessários em `i18n.js`

Adicionar, em todos os idiomas já suportados pelo transporte:

1. novo label de campo: `Departure Date`
2. nova mensagem de validação: `Departure Date is required for extra vehicles.`
3. ajuste da nota do modal `extra` para explicitar que o veículo é criado para a rota selecionada e para a data de partida escolhida no formulário

### Idiomas que precisam ser atualizados juntos

O arquivo de i18n do transporte hoje carrega pelo menos estes blocos de tradução:

- inglês
- português
- chinês
- malaio
- filipino

O planejamento deve tratar todos esses blocos na mesma alteração para evitar chaves faltantes e regressão visual de localização.

## 4. Backend - impacto esperado

### O que precisa permanecer igual

- `TransportVehicleCreate` continua usando `service_date`.
- `create_transport_vehicle_registration()` continua criando agenda `single_date` para `extra`.
- `vehicle_schedule_applies_to_date()` continua exigindo igualdade exata para `single_date`.
- O endpoint `POST /api/transport/vehicles` continua sem mudança de rota nem de formato principal.

### O que provavelmente não precisa mudar

- nenhuma migration nova
- nenhuma coluna nova em `transport_vehicle_schedules`
- nenhuma alteração de model SQLAlchemy
- nenhuma alteração obrigatória em `routers/transport.py`

### Ajuste opcional, não obrigatório

Se durante a implementação o time quiser fortalecer o guard-rail de UX também no servidor, pode adicionar uma mensagem mais explícita para `service_date` ausente em `extra`. Mas isso não é requisito técnico para atender à funcionalidade, porque o campo já faz parte do contrato e o frontend pode resolver a experiência principal.

## 5. Testes automatizados

### Frontend JS

Atualizar `tests/transport_page_date.test.js` para refletir o novo contrato do modal:

1. `buildVehicleCreatePayload()` deve usar o valor do campo `service_date` para `extra`, mesmo quando a data atual do dashboard for outra.
2. `buildVehicleCreatePayload()` deve continuar usando a data passada por parâmetro para `regular` e `weekend`.
3. Adicionar cobertura para a abertura do modal `extra` preencher `service_date` com a data atual do dashboard.
4. Adicionar cobertura para a validação que bloqueia submit de `extra` sem data.

### Backend/API

Atualizar ou adicionar cenários em `tests/test_api_flow.py` para registrar explicitamente o comportamento pedido:

1. criar veículo `extra` com `service_date` diferente da data inicialmente aberta pelo dashboard
2. validar que a agenda criada tem `recurrence_kind == "single_date"`
3. validar que o veículo aparece no dashboard da data escolhida
4. validar que o mesmo veículo não aparece no dashboard de outra data
5. validar que o `extra_vehicle_registry` também mostra a data correta

### O que não deve ser quebrado

- criação de `regular`
- criação de `weekend`
- validação atual de `departure_time` obrigatória para `extra`
- filtros por rota para `extra`
- visibilidade por data já existente no dashboard e no registry

## 6. Riscos de regressão que o plano precisa cobrir

1. Se o campo de data for mostrado, mas `buildVehicleCreatePayload()` continuar usando apenas a data do dashboard, a UI dará a impressão de aceitar a escolha do usuário sem realmente persistí-la.
2. Se o submit salvar o veículo em outra data, mas o dashboard continuar recarregando a data antiga, o administrador pode interpretar o fluxo como erro de gravação.
3. Se o novo `service_date` do formulário vazar para `regular` ou `weekend`, o sistema pode alterar sem querer a semântica atual dessas listas.
4. Se o novo campo não for limpo ou refeito corretamente após `form.reset()`, o modal pode reabrir com valor residual incorreto.
5. Se os textos de i18n não forem atualizados em todos os idiomas, a UI pode mostrar labels quebrados ou mensagens em branco.
6. Se os testes cobrirem apenas backend e ignorarem o builder do payload no frontend, a regressão principal pode escapar mesmo com a API funcionando.

## 7. Estratégia de implementação recomendada

### Fase 1 - UI do modal

1. Inserir o campo `Departure Date` no HTML, imediatamente antes de `Departure Time`.
2. Atualizar i18n para label, nota e mensagem de validação.
3. Ajustar `syncVehicleModalFields()` para controlar visibilidade e obrigatoriedade do novo campo.

### Fase 2 - Lógica de submit

1. Refatorar `buildVehicleCreatePayload()` para `extra` usar a data do formulário.
2. Adicionar validação de `Departure Date` no submit.
3. Ajustar `openVehicleModal()` para preencher a data automaticamente e focar o novo campo.

### Fase 3 - Feedback e navegação

1. Ajustar o fluxo de sucesso para mudar o dashboard para a data escolhida quando o escopo for `extra`.
2. Confirmar que o status de sucesso continua sendo exibido depois do reload.
3. Confirmar que o comportamento de `regular` e `weekend` não muda.

### Fase 4 - Testes

1. Atualizar testes JS do modal e do payload.
2. Atualizar ou adicionar testes Python de API e dashboard.
3. Rodar os testes afetados antes de considerar a entrega concluída.

## 8. Arquivos mais prováveis de alteração

### Frontend

- `sistema/app/static/transport/index.html`
- `sistema/app/static/transport/app.js`
- `sistema/app/static/transport/i18n.js`
- `sistema/app/static/transport/styles.css` apenas se a validação visual mostrar necessidade real

### Testes

- `tests/transport_page_date.test.js`
- `tests/test_api_flow.py`

### Backend

Nenhum arquivo Python parece exigir alteração obrigatória para a funcionalidade principal, porque o contrato de `service_date` para `extra` já existe e já é respeitado na persistência e no dashboard.

## 9. Validações obrigatórias após a implementação

1. Abrir o dashboard em uma data A, cadastrar um veículo `extra` escolhendo uma data B diferente de A e confirmar que o sistema navega para B após salvar.
2. Confirmar que o veículo aparece na `EXTRA TRANSPORT LIST` da data B.
3. Voltar para a data A e confirmar que o veículo não aparece lá.
4. Confirmar que `Departure Time` e `Route` continuam sendo gravados corretamente.
5. Confirmar que o registry de veículos extra mostra a data correta do cadastro.
6. Confirmar que `regular` e `weekend` continuam usando a data do dashboard como referência de início.
7. Confirmar que o modal bloqueia submit sem `Departure Date` e sem `Departure Time` para `extra`.
8. Confirmar que a tela continua funcional em todos os idiomas suportados pelo transporte.

## 10. Lista to-do completa para execução futura

### Preparação

- [x] Revisar o modal atual de `EXTRA TRANSPORT LIST` em `sistema/app/static/transport/index.html` e identificar o ponto exato de inserção do novo campo imediatamente antes de `Departure Time`.
- [x] Revisar `buildVehicleCreatePayload()`, `syncVehicleModalFields()` e `openVehicleModal()` em `sistema/app/static/transport/app.js` antes da edição para manter o escopo da alteração restrito ao fluxo `extra`.
- [x] Revisar os blocos de tradução de `sistema/app/static/transport/i18n.js` para adicionar as novas chaves em todos os idiomas no mesmo commit.

Observações confirmadas nesta execução:

1. Em `sistema/app/static/transport/index.html`, o ponto exato de inserção do novo campo é entre o label de `Tolerance (minutes)` e o label já existente com `data-extra-departure-field`, preservando a sequência `Tolerance -> Departure Date -> Departure Time -> Route`.
2. Em `sistema/app/static/transport/app.js`, `buildVehicleCreatePayload()` ainda define `service_date` diretamente a partir do parâmetro `serviceDate`, então o novo campo precisará sobrescrever esse valor apenas no escopo `extra`.
3. Em `sistema/app/static/transport/app.js`, `syncVehicleModalFields()` hoje só controla visibilidade, obrigatoriedade e limpeza para `departure_time` e `route_kind` no fluxo `extra`; o novo campo de data deverá seguir exatamente esse mesmo padrão de controle.
4. Em `sistema/app/static/transport/app.js`, `openVehicleModal()` executa `form.reset()`, reaplica defaults com `applyVehicleFormDefaults("carro", vehicleForm)`, limpa `departure_time` e foca esse campo quando o escopo é `extra`; a nova data precisará ser preenchida após o reset e antes da troca de foco.
5. No submit atual do modal, a validação específica de `extra` cobre apenas `departure_time`; ainda não existe validação dedicada para `service_date` no frontend.
6. Em `sistema/app/static/transport/i18n.js`, o bloco do modal de veículos aparece em cinco idiomas já ativos no transporte: inglês, português, chinês, malaio e filipino. As novas chaves de label, nota e validação precisam entrar em todos esses blocos no mesmo commit para evitar inconsistência de localização.

### HTML do modal

- [x] Adicionar um novo campo `Departure Date` no modal de cadastro de veículo.
- [x] Posicionar esse campo imediatamente antes de `Departure Time`.
- [x] Marcar o novo campo com um seletor de controle específico para o escopo `extra`.
- [x] Definir `type="date"` e `name="service_date"` no novo input.
- [x] Garantir que o campo inicie hidden no markup, assim como os demais campos específicos de `extra`.

### Comportamento do modal em JS

- [x] Atualizar `syncVehicleModalFields()` para mostrar e esconder o novo campo de data apenas no escopo `extra`.
- [x] Atualizar `syncVehicleModalFields()` para tornar o campo obrigatório e habilitado apenas no escopo `extra`.
- [x] Limpar o valor do campo ao sair do escopo `extra`, evitando vazamento de estado entre formulários.
- [x] Atualizar `openVehicleModal()` para preencher `service_date` com `getCurrentServiceDateIso()` ao abrir `extra`.
- [x] Alterar o foco inicial do modal `extra` para o novo campo `service_date`.
- [x] Confirmar que `form.reset()` não apaga os defaults necessários de tipo, lugares e tolerância.

### Payload e submit

- [x] Refatorar `buildVehicleCreatePayload()` para que `extra` leia `service_date` do formulário.
- [x] Manter `regular` e `weekend` usando a data atual do dashboard recebida por parâmetro.
- [x] Adicionar validação de frontend para bloquear submit de `extra` sem `service_date`.
- [x] Adicionar mensagem de erro dedicada para data ausente em `extra`.
- [x] Focar o input `service_date` quando essa validação falhar.
- [x] Preservar a validação atual de `departure_time` obrigatória para `extra`.
- [x] Garantir que `route_kind` continue sendo enviado apenas para `extra`.

### Feedback após salvar

- [x] Ajustar o fluxo de sucesso para que `extra` troque a data selecionada do dashboard para `payload.service_date` antes do reload.
- [x] Garantir que o reload após salvar use a nova data quando o cadastro for `extra`.
- [x] Garantir que o fluxo de sucesso de `regular` e `weekend` continue recarregando a data atual do dashboard.
- [x] Validar se a mensagem `Vehicle saved successfully.` continua visível no timing correto depois da troca de data.

### i18n

- [x] Adicionar a chave de label para `Departure Date` em todos os idiomas do transporte.
- [x] Adicionar a chave de erro para `Departure Date is required for extra vehicles.` em todos os idiomas do transporte.
- [x] Atualizar a nota do modal `extra` para refletir que a data vem do formulário, não implicitamente da tela.
- [x] Revisar consistência terminológica entre `Departure Date`, `Departure Time` e `Route` em todas as línguas.

### CSS e responsividade

- [x] Verificar se o novo campo cabe no modal sem regressão visual em desktop.
- [x] Verificar se o novo campo cabe no modal sem regressão visual em mobile.
- [x] Alterar `styles.css` somente se a validação visual mostrar necessidade real de espaçamento, overflow ou alinhamento.

### Testes frontend

- [x] Atualizar o teste de `buildVehicleCreatePayload()` em `tests/transport_page_date.test.js` para esperar `service_date` vindo do formulário no escopo `extra`.
- [x] Manter a cobertura que garante `service_date` vindo da data do dashboard para `regular` e `weekend`.
- [x] Adicionar teste cobrindo o prefill automático de `service_date` ao abrir o modal `extra`.
- [x] Adicionar teste cobrindo o bloqueio de submit quando `service_date` estiver vazia em `extra`.
- [x] Adicionar teste cobrindo a troca de foco para o campo de data no modal `extra`.

### Testes backend/API

- [x] Adicionar ou ajustar teste em `tests/test_api_flow.py` para criar veículo `extra` com uma data explícita escolhida no payload.
- [x] Validar por teste que a agenda criada continua sendo `single_date`.
- [x] Validar por teste que o veículo aparece apenas na data escolhida e não em outra data do dashboard.
- [x] Validar por teste que o `extra_vehicle_registry` devolve `service_date` correta após a criação.
- [x] Confirmar por teste que `regular` e `weekend` não sofreram regressão no uso da data-base de início.

### Validação manual final

- [x] Testar o cadastro de um veículo `extra` escolhendo a mesma data atual do dashboard.
- [x] Testar o cadastro de um veículo `extra` escolhendo uma data futura diferente da data atual do dashboard.
- [x] Testar submit inválido sem `Departure Date`.
- [x] Testar submit inválido sem `Departure Time`.
- [x] Testar se a rota escolhida continua refletida corretamente no dashboard e no registry.
- [x] Testar se o cadastro de `regular` continua usando dias úteis e ambos os trajetos.
- [x] Testar se o cadastro de `weekend` continua usando persistência por sábado e domingo.

## Encerramento

Este plano parte de um ponto importante: a regra de persistência por data já existe no backend de transporte. A entrega pedida consiste principalmente em tornar essa data editável no modal de `EXTRA TRANSPORT LIST`, ajustar o fluxo de submit para respeitar a escolha do administrador e alinhar o feedback visual da tela com a nova possibilidade de cadastro em uma data diferente da data atualmente aberta no dashboard.

Seguindo a estratégia acima, a alteração fica pequena, local, coerente com a arquitetura atual do transporte e com baixo risco de regressão fora do escopo `extra`.