# handleVehicleDrop

- Nome da funcao: `handleVehicleDrop`
- Arquivo gerado: `handleVehicleDrop.md`
- Origem: `sistema/app/static/transport/app.js:3395`
- Escopo original: interna de `createVehicleIconButton`
- Tema funcional: veiculo drop
- Categoria: state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `event` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `canRequestBeDroppedOnVehicle`, `getRequestById`, `getRouteKindForVehicle`, `getSelectedRouteKind`, `renderRequestTables`, `renderVehiclePanels`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function handleVehicleDrop(event) {
        const droppedRequestId = Number(
          state.dragRequestId !== null
            ? state.dragRequestId
            : event.dataTransfer
              ? event.dataTransfer.getData("text/plain")
              : ""
        );
        const droppedRequest = getRequestById(droppedRequestId);
        if (!canRequestBeDroppedOnVehicle(droppedRequest, scope, vehicle, getSelectedRouteKind())) {
          state.dragRequestId = null;
          renderRequestTables();
          renderVehiclePanels();
          return;
        }

        event.preventDefault();
        state.expandedVehicleKey = vehicleDetailsKey;
        state.pendingAssignmentPreview = {
          requestId: droppedRequest.id,
          vehicleId: vehicle.id,
          scope,
          routeKind: getRouteKindForVehicle(scope, vehicle),
        };
        state.dragRequestId = null;
        renderRequestTables();
        renderVehiclePanels();
      }
```
