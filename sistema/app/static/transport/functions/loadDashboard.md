# loadDashboard

- Nome da funcao: `loadDashboard`
- Arquivo gerado: `loadDashboard.md`
- Origem: `sistema/app/static/transport/app.js:3600`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: dashboard
- Categoria: API + state + date/time
- Responsabilidade: Carrega o dashboard para a data selecionada, sincroniza o estado local, recalcula visibilidade de projetos e dispara a renderizacao completa das listas e dos paineis de veiculos.
- Entradas: Recebe `selectedDate`, `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearDashboard`, `clearTransportSession`, `formatIsoDate`, `getSelectedRouteKind`, `getTransportLockedMessage`, `getTransportSessionExpiredMessage`, `localizeTransportApiMessage`, `reconcileProjectVisibility`, `renderDashboard`, `requestJson`, `setStatus`
- Endpoints/rotas envolvidos: `GET /api/transport/dashboard`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function loadDashboard(selectedDate, options) {
      const loadOptions = options || {};
      const shouldAnnounce = loadOptions.announce !== false;
      if (!state.isAuthenticated) {
        state.dashboard = null;
        clearDashboard();
        setStatus(getTransportLockedMessage(), "warning");
        return Promise.resolve(null);
      }

      state.pendingAssignmentPreview = null;
      state.dragRequestId = null;
      state.isLoading = true;
      syncRouteTimeControls();
      const serviceDate = formatIsoDate(selectedDate);
      const routeKind = getSelectedRouteKind();
      if (shouldAnnounce) {
        setStatus(t("status.loadingDashboard"), "info");
      }
      return requestJson(
        `${TRANSPORT_API_PREFIX}/dashboard?service_date=${encodeURIComponent(serviceDate)}&route_kind=${encodeURIComponent(routeKind)}`
      )
        .then(function (dashboard) {
          state.dashboard = dashboard || null;
          reconcileProjectVisibility();
          state.selectedRouteKind = (dashboard && dashboard.selected_route) || routeKind;
          syncRouteInputs();
          syncRouteTimeControls();
          if (shouldAnnounce) {
            setStatus(t("status.dashboardUpdated"), "info");
          }
          renderDashboard();
        })
        .catch(function (error) {
          state.dashboard = null;
          clearDashboard();
          if (error && Number(error.status) === 401) {
            clearTransportSession(getTransportSessionExpiredMessage());
            return;
          }
          setStatus(localizeTransportApiMessage(error && error.message) || t("status.couldNotLoadDashboard"), "error");
        })
        .finally(function () {
          state.isLoading = false;
          syncRouteTimeControls();
        });
    }
```
