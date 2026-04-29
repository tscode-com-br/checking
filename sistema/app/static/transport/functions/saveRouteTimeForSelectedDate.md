# saveRouteTimeForSelectedDate

- Nome da funcao: `saveRouteTimeForSelectedDate`
- Arquivo gerado: `saveRouteTimeForSelectedDate.md`
- Origem: `sistema/app/static/transport/app.js:1836`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: rota horario para selecionado data
- Categoria: API + state + date/time
- Responsabilidade: Grava o horario `work_to_home` da data selecionada, protege o fluxo contra usuario sem autenticacao e reabre a tela com os dados atualizados.
- Entradas: Recebe `nextWorkToHomeTime` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getCurrentServiceDateIso`, `getTransportLockedMessage`, `getValue`, `handleProtectedRequestError`, `loadDashboard`, `requestJson`, `setStatus`, `syncRouteTimeControls`, `t`, `dateStore`
- Endpoints/rotas envolvidos: `PUT /api/transport/date-settings`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function saveRouteTimeForSelectedDate(nextWorkToHomeTime) {
      const normalizedTime = String(nextWorkToHomeTime || "").trim();
      if (!/^\d{2}:\d{2}$/.test(normalizedTime)) {
        syncRouteTimeControls();
        return Promise.resolve(null);
      }
      if (!state.isAuthenticated) {
        setStatus(getTransportLockedMessage(), "warning");
        syncRouteTimeControls();
        return Promise.resolve(null);
      }

      state.routeTimeSaving = true;
      syncRouteTimeControls();
      return requestJson(`${TRANSPORT_API_PREFIX}/date-settings`, {
        method: "PUT",
        body: JSON.stringify({
          service_date: getCurrentServiceDateIso(),
          work_to_home_time: normalizedTime,
        }),
      })
        .then(function (response) {
          if (state.dashboard) {
            state.dashboard = Object.assign({}, state.dashboard, {
              work_to_home_departure_time:
                response && response.work_to_home_time ? response.work_to_home_time : normalizedTime,
            });
          }
          return loadDashboard(dateStore.getValue(), { announce: false }).then(function () {
            setStatus(t("status.settingsSaved"), "success");
            return response;
          });
        })
        .catch(function (error) {
          handleProtectedRequestError(error, t("status.couldNotSaveSettings"));
          return null;
        })
        .finally(function () {
          state.routeTimeSaving = false;
          syncRouteTimeControls();
        });
    }
```
