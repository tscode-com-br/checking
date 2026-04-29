# clearDashboard

- Nome da funcao: `clearDashboard`
- Arquivo gerado: `clearDashboard.md`
- Origem: `sistema/app/static/transport/app.js:3571`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: dashboard
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearElement`, `createEmptyState`, `getRequestTitle`, `mapScopeTitle`, `renderProjectList`, `setVehicleContainerViewMode`, `syncRequestSectionToggleState`, `syncRouteTimeControls`, `syncVehicleViewToggleState`, `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function clearDashboard() {
      renderProjectList();
      REQUEST_SECTION_ORDER.forEach(function (kind) {
        const container = requestContainers[kind];
        clearElement(container);
        if (container) {
          container.appendChild(createEmptyState(t("empty.noRows", { title: getRequestTitle(kind) })));
        }
      });
      VEHICLE_SCOPE_ORDER.forEach(function (scope) {
        const container = vehicleContainers[scope];
        clearElement(container);
        if (container) {
          setVehicleContainerViewMode(container, scope);
          container.appendChild(createEmptyState(t("empty.noVehicles", { scope: mapScopeTitle(scope) })));
          container.style.removeProperty("grid-template-rows");
          container.style.removeProperty("grid-auto-columns");
        }
      });
      clearElement(vehicleDetailsOverlayHost);
      vehicleDetailsOverlayHost.classList.remove("is-active");
      state.expandedVehicleKey = null;
      state.pendingAssignmentPreview = null;
      state.dragRequestId = null;
      syncVehicleViewToggleState();
      syncRequestSectionToggleState();
      syncRouteTimeControls();
    }
```
