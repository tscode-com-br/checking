# renderVehiclePanels

- Nome da funcao: `renderVehiclePanels`
- Arquivo gerado: `renderVehiclePanels.md`
- Origem: `sistema/app/static/transport/app.js:3513`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo panels
- Categoria: UI + state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `clearElement`, `createEmptyState`, `createVehicleIconButton`, `createVehicleManagementTable`, `getVehicleRegistryRows`, `getVehicleViewMode`, `getVehiclesForScope`, `groupAssignedRequestsByVehicle`, `mapScopeTitle`, `scheduleExpandedVehicleDetailsPositionSync`, `setVehicleContainerViewMode`, `syncVehicleViewToggleState`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function renderVehiclePanels() {
      syncVehicleViewToggleState();
      clearElement(vehicleDetailsOverlayHost);
      vehicleDetailsOverlayHost.classList.remove("is-active");
      let hasExpandedDetailsPanel = false;

      VEHICLE_SCOPE_ORDER.forEach(function (scope) {
        const container = vehicleContainers[scope];
        const vehicles = getVehiclesForScope(scope);
        const registryRows = getVehicleRegistryRows(scope);
        const assignedRowsByVehicle = groupAssignedRequestsByVehicle(scope);
        clearElement(container);
        if (!container) {
          return;
        }

        setVehicleContainerViewMode(container, scope);

        if (getVehicleViewMode(scope) === "table") {
          if (!registryRows.length) {
            container.appendChild(createEmptyState(t("empty.noVehicles", { scope: mapScopeTitle(scope) })));
            return;
          }
          container.appendChild(createVehicleManagementTable(scope, registryRows));
          return;
        }

        if (!vehicles.length) {
          container.appendChild(createEmptyState(t("empty.noVehicles", { scope: mapScopeTitle(scope) })));
          return;
        }

        vehicles.forEach(function (vehicle) {
          const assignedRows = assignedRowsByVehicle[String(vehicle.id)] || [];
          const tileElement = createVehicleIconButton(scope, vehicle, assignedRows);
          container.appendChild(tileElement);
          if (tileElement.expandedDetailsPanel) {
            vehicleDetailsOverlayHost.appendChild(tileElement.expandedDetailsPanel);
            hasExpandedDetailsPanel = true;
          }
        });

        updateVehicleGridLayout(container);
      });

      vehicleDetailsOverlayHost.classList.toggle("is-active", hasExpandedDetailsPanel);

      scheduleExpandedVehicleDetailsPositionSync();
    }
```
