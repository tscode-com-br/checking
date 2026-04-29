# createVehicleIconButton

- Nome da funcao: `createVehicleIconButton`
- Arquivo gerado: `createVehicleIconButton.md`
- Origem: `sistema/app/static/transport/app.js:3313`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo icone button
- Categoria: UI + state
- Responsabilidade: Factory/builder do controller da pagina que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `scope`, `vehicle`, `assignedRows` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: `handleVehicleDragOver`, `handleVehicleDrop`, `handleVehicleDragEnter`
- Dependencias observadas: `state`, `canRequestBeDroppedOnVehicle`, `createNode`, `createVehicleDetailsPanel`, `formatVehicleOccupancyCount`, `formatVehicleOccupancyLabel`, `getDraggedRequest`, `getEffectiveWorkToHomeDepartureTime`, `getPendingAssignmentPreview`, `getRequestById`, `getRouteKindForVehicle`, `getRouteKindLabel`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function createVehicleIconButton(scope, vehicle, assignedRows) {
      const tileElement = createNode("div", "transport-vehicle-tile");
      const vehicleButton = createNode("button", "transport-vehicle-button");
      const assignedCount = assignedRows.length;
      const effectiveDepartureTime = getEffectiveWorkToHomeDepartureTime(state.dashboard, state.workToHomeTime);
      const departureTime = getVehicleDepartureTime(vehicle, effectiveDepartureTime, scope);
      const vehicleDetailsKey = getVehicleDetailsKey(scope, vehicle.id);
      const draggedRequest = getDraggedRequest();
      const pendingPreview = getPendingAssignmentPreview();
      const previewRequestRow = pendingPreview
        && pendingPreview.scope === scope
        && Number(pendingPreview.vehicle.id) === Number(vehicle.id)
        ? pendingPreview.requestRow
        : null;
      const isDropTarget = canRequestBeDroppedOnVehicle(draggedRequest, scope, vehicle, getSelectedRouteKind());
      const isExpanded = state.expandedVehicleKey === vehicleDetailsKey;

      vehicleButton.type = "button";
      vehicleButton.dataset.vehicleId = String(vehicle.id);
      vehicleButton.dataset.vehicleScope = scope;
      vehicleButton.dataset.vehicleDetailsAnchorKey = vehicleDetailsKey;
      vehicleButton.title = t("misc.vehicleButtonTitle", {
        type: mapVehicleTypeLabel(vehicle.tipo),
        occupancy: formatVehicleOccupancyLabel(vehicle, assignedCount),
      });
      vehicleButton.setAttribute("aria-label", vehicleButton.title);
      vehicleButton.classList.toggle("is-selectable", isDropTarget);
      vehicleButton.classList.toggle("is-preview-target", !!previewRequestRow);
      vehicleButton.classList.toggle("is-details-open", isExpanded);
      tileElement.classList.toggle("is-expanded", isExpanded);
      if (!isDropTarget && !previewRequestRow) {
        vehicleButton.classList.add("is-idle");
      }

      const iconImage = document.createElement("img");
      iconImage.className = "transport-vehicle-icon";
      iconImage.src = mapVehicleIconPath(vehicle.tipo);
      iconImage.alt = "";

      const plateLabel = createNode("span", "transport-vehicle-plate", vehicle.placa);
      const occupancyLabel = createNode(
        "span",
        "transport-vehicle-occupancy",
        formatVehicleOccupancyCount(vehicle, assignedCount)
      );
      const departureLabel = departureTime
        ? createNode("span", "transport-vehicle-departure", departureTime)
        : null;
      const routeLabel = scope === "extra" && vehicle.route_kind
        ? createNode("span", "transport-vehicle-route", getRouteKindLabel(vehicle.route_kind))
        : null;

      if (scope === "extra" && vehicle.route_kind) {
        vehicleButton.title = `${vehicleButton.title} | ${getRouteKindLabel(vehicle.route_kind)}`;
      }
      if (departureLabel) {
        departureLabel.setAttribute("aria-label", departureTime);
        vehicleButton.title = `${vehicleButton.title} | ${departureTime}`;
      }
      vehicleButton.appendChild(plateLabel);
      vehicleButton.appendChild(iconImage);
      vehicleButton.appendChild(occupancyLabel);
      if (departureLabel) {
        vehicleButton.appendChild(departureLabel);
      }
      if (routeLabel) {
        vehicleButton.appendChild(routeLabel);
      }
      vehicleButton.addEventListener("click", function () {
        toggleVehicleDetails(scope, vehicle.id);
      });

      function handleVehicleDragOver(event) {
        if (!canRequestBeDroppedOnVehicle(getDraggedRequest(), scope, vehicle, getSelectedRouteKind())) {
          return;
        }
        event.preventDefault();
        if (event.dataTransfer) {
          event.dataTransfer.dropEffect = "move";
        }
      }

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

      function handleVehicleDragEnter(event) {
        if (!canRequestBeDroppedOnVehicle(getDraggedRequest(), scope, vehicle, getSelectedRouteKind())) {
          return;
        }
        event.preventDefault();
      }

      tileElement.addEventListener("dragover", handleVehicleDragOver);
      tileElement.addEventListener("drop", handleVehicleDrop);
      tileElement.addEventListener("dragenter", handleVehicleDragEnter);

      tileElement.appendChild(vehicleButton);
      if (isExpanded) {
        tileElement.expandedDetailsPanel = createVehicleDetailsPanel(vehicle, assignedRows, {
          previewRequestRow,
          routeKind: pendingPreview ? pendingPreview.routeKind : getRouteKindForVehicle(scope, vehicle),
        });
        tileElement.expandedDetailsPanel.dataset.vehicleDetailsPanelKey = vehicleDetailsKey;
      }
      return tileElement;
    }
```
