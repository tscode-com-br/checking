# createVehicleManagementTable

- Nome da funcao: `createVehicleManagementTable`
- Arquivo gerado: `createVehicleManagementTable.md`
- Origem: `sistema/app/static/transport/app.js:3446`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo gerenciamento table
- Categoria: UI + state + date/time
- Responsabilidade: Factory/builder do controller da pagina que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `scope`, `registryRows` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `createNode`, `formatRouteTableValue`, `formatVehicleOccupancyCount`, `formatVehicleTypeTableValue`, `getEffectiveWorkToHomeDepartureTime`, `getVehicleDepartureTime`, `mapScopeTitle`, `removeVehicleFromRoute`, `t`, `document`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function createVehicleManagementTable(scope, registryRows) {
      const table = createNode("table", "transport-vehicle-management-table");
      const tableBody = document.createElement("tbody");

      registryRows.forEach(function (rowData) {
        const row = createNode("tr", "transport-vehicle-management-row");
        const typeCell = createNode(
          "td",
          "transport-vehicle-management-type",
          formatVehicleTypeTableValue(rowData.tipo)
        );
        const plateCell = createNode("td", "transport-vehicle-management-plate-cell");
        const occupancyCell = createNode(
          "td",
          "transport-vehicle-management-occupancy",
          formatVehicleOccupancyCount(rowData, rowData.assigned_count)
        );
        const actionsCell = createNode("td", "transport-vehicle-management-actions");
        const vehiclePlate = createNode("strong", "transport-vehicle-management-plate", rowData.placa);
        const effectiveDepartureTime = getEffectiveWorkToHomeDepartureTime(state.dashboard, state.workToHomeTime);
        const departureTime = getVehicleDepartureTime(rowData, effectiveDepartureTime, scope);
        const deleteButton = createNode(
          "button",
          "transport-vehicle-delete-button transport-vehicle-management-delete",
          t("misc.delete")
        );

        occupancyCell.classList.toggle("is-occupied", Number(rowData.assigned_count) > 0);
        deleteButton.type = "button";
        deleteButton.disabled = rowData.schedule_id === null || rowData.schedule_id === undefined;
        deleteButton.addEventListener("click", function (event) {
          event.preventDefault();
          event.stopPropagation();
          removeVehicleFromRoute(rowData);
        });

        plateCell.appendChild(vehiclePlate);
        row.appendChild(typeCell);
        row.appendChild(plateCell);
        if (departureTime) {
          row.appendChild(createNode("td", "transport-vehicle-management-time", departureTime));
        }
        actionsCell.appendChild(deleteButton);
        row.appendChild(occupancyCell);

        if (scope === "extra") {
          row.appendChild(
            createNode("td", "transport-vehicle-management-date", rowData.service_date || "")
          );
          row.appendChild(
            createNode(
              "td",
              "transport-vehicle-management-route-value",
              rowData.route_kind ? formatRouteTableValue(rowData.route_kind) : ""
            )
          );
        }

        row.appendChild(actionsCell);
        tableBody.appendChild(row);
      });

      table.appendChild(tableBody);
      table.setAttribute("aria-label", t("misc.vehiclesAria", { scope: mapScopeTitle(scope) }));
      return table;
    }
```
