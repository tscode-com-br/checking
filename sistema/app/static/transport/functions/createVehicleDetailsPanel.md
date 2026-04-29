# createVehicleDetailsPanel

- Nome da funcao: `createVehicleDetailsPanel`
- Arquivo gerado: `createVehicleDetailsPanel.md`
- Origem: `sistema/app/static/transport/app.js:2951`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: detalhes do veiculo painel
- Categoria: UI + state + date/time
- Responsabilidade: Factory/builder do controller da pagina que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `vehicle`, `assignedRows`, `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `buildVehiclePassengerAwarenessRows`, `buildVehiclePassengerPreviewRows`, `createNode`, `createPassengerRemoveButton`, `getRouteKindForVehicle`, `removeVehicleFromRoute`, `renderRequestTables`, `renderVehiclePanels`, `submitAssignment`, `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function createVehicleDetailsPanel(vehicle, assignedRows, options) {
      const detailOptions = options || {};
      const previewRequestRow = detailOptions.previewRequestRow || null;
      const detailsPanel = createNode("div", "transport-vehicle-details");
      const passengerTableShell = createNode("div", "transport-vehicle-passenger-table-shell");
      const passengerTable = createNode("table", "transport-vehicle-passenger-table");
      const tableBody = createNode("tbody");
      const passengerSourceRows = buildVehiclePassengerPreviewRows(assignedRows, previewRequestRow);

      buildVehiclePassengerAwarenessRows(
        passengerSourceRows,
        VEHICLE_DETAILS_MAX_ROWS
      ).forEach(function (row, index) {
        const tableRow = createNode("tr", "transport-vehicle-passenger-row");
        const nameCell = createNode("td", "transport-vehicle-passenger-name", row.name);
        const statusCell = createNode("td", "transport-vehicle-passenger-status");
        const sourceRequestRow = passengerSourceRows[index] || null;
        const isPreviewRow = Boolean(
          previewRequestRow
          && sourceRequestRow
          && Number(sourceRequestRow.id) === Number(previewRequestRow.id)
        );

        if (!row.name) {
          nameCell.innerHTML = "&nbsp;";
        }

        if (sourceRequestRow && !isPreviewRow) {
          statusCell.appendChild(createPassengerRemoveButton(sourceRequestRow, detailOptions.routeKind));
        } else {
          statusCell.innerHTML = "&nbsp;";
        }
        tableRow.appendChild(nameCell);
        tableRow.appendChild(statusCell);
        tableBody.appendChild(tableRow);
      });

      passengerTable.appendChild(tableBody);
      passengerTableShell.appendChild(passengerTable);
      detailsPanel.appendChild(passengerTableShell);

      if (previewRequestRow) {
        const previewActions = createNode("div", "transport-vehicle-preview-actions");
        const cancelButton = createNode("button", "transport-secondary-button", t("modal.actions.cancel"));
        const confirmButton = createNode("button", "transport-primary-button", t("misc.confirm"));

        cancelButton.type = "button";
        confirmButton.type = "button";

        cancelButton.addEventListener("click", function (event) {
          event.preventDefault();
          event.stopPropagation();
          state.pendingAssignmentPreview = null;
          renderRequestTables();
          renderVehiclePanels();
        });

        confirmButton.addEventListener("click", function (event) {
          event.preventDefault();
          event.stopPropagation();
          if (!state.dashboard) {
            return;
          }

          submitAssignment({
            request_id: previewRequestRow.id,
            service_date: state.dashboard.selected_date,
            route_kind: detailOptions.routeKind || getRouteKindForVehicle(vehicle.service_scope, vehicle),
            status: "confirmed",
            vehicle_id: vehicle.id,
          })
            .then(function (result) {
              if (result === null) {
                return;
              }
              state.pendingAssignmentPreview = null;
              renderRequestTables();
              renderVehiclePanels();
            })
            .catch(function () {});
        });

        previewActions.appendChild(cancelButton);
        previewActions.appendChild(confirmButton);
        detailsPanel.appendChild(previewActions);
        return detailsPanel;
      }

      const deleteButton = createNode("button", "transport-vehicle-delete-button", t("misc.delete"));
      deleteButton.type = "button";
      deleteButton.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        removeVehicleFromRoute(vehicle);
      });
      detailsPanel.insertBefore(deleteButton, passengerTableShell);
      return detailsPanel;
    }
```
