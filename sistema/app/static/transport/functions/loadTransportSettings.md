# loadTransportSettings

- Nome da funcao: `loadTransportSettings`
- Arquivo gerado: `loadTransportSettings.md`
- Origem: `sistema/app/static/transport/app.js:2062`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte configuracoes
- Categoria: API + state
- Responsabilidade: Orquestra um fluxo operacional do controller da pagina, ligando validacao local, integracao externa, feedback visual e recarga de dados quando necessario.
- Entradas: Recebe `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `applyTransportVehicleSeatDefaults`, `applyTransportVehicleToleranceDefault`, `handleProtectedRequestError`, `requestJson`, `syncRouteTimeControls`, `syncSettingsControls`, `t`
- Endpoints/rotas envolvidos: `GET /api/transport/settings`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function loadTransportSettings(options) {
      const nextOptions = options || {};
      if (!state.isAuthenticated) {
        state.workToHomeTime = state.workToHomeTime || DEFAULT_WORK_TO_HOME_TIME;
        state.lastUpdateTime = state.lastUpdateTime || DEFAULT_LAST_UPDATE_TIME;
        state.vehicleSeatDefaults = applyTransportVehicleSeatDefaults(state.vehicleSeatDefaults);
        state.vehicleToleranceDefaultMinutes = applyTransportVehicleToleranceDefault(state.vehicleToleranceDefaultMinutes);
        syncSettingsControls();
        return Promise.resolve(null);
      }

      state.settingsLoading = true;
      syncSettingsControls();
      return requestJson(`${TRANSPORT_API_PREFIX}/settings`)
        .then(function (response) {
          state.settingsLoaded = true;
          state.workToHomeTime = String(
            response && response.work_to_home_time ? response.work_to_home_time : DEFAULT_WORK_TO_HOME_TIME
          );
          state.lastUpdateTime = String(
            response && response.last_update_time ? response.last_update_time : DEFAULT_LAST_UPDATE_TIME
          );
          state.vehicleSeatDefaults = applyTransportVehicleSeatDefaults(response);
          state.vehicleToleranceDefaultMinutes = applyTransportVehicleToleranceDefault(
            response && response.default_tolerance_minutes !== undefined
              ? response.default_tolerance_minutes
              : state.vehicleToleranceDefaultMinutes
          );
          return response;
        })
        .catch(function (error) {
          handleProtectedRequestError(error, t("status.couldNotLoadSettings"));
          if (nextOptions.silent) {
            return null;
          }
          return null;
        })
        .finally(function () {
          state.settingsLoading = false;
          syncSettingsControls();
          syncRouteTimeControls();
        });
    }
```
