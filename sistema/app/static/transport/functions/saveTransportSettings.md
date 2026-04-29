# saveTransportSettings

- Nome da funcao: `saveTransportSettings`
- Arquivo gerado: `saveTransportSettings.md`
- Origem: `sistema/app/static/transport/app.js:2106`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte configuracoes
- Categoria: API + state + date/time
- Responsabilidade: Persiste as configuracoes do dashboard, normaliza horarios e defaults de veiculos, atualiza o estado local e recarrega a tela apos confirmacao do backend.
- Entradas: Recebe `nextValues` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `applyTransportVehicleSeatDefaults`, `applyTransportVehicleToleranceDefault`, `getTransportLockedMessage`, `getValue`, `handleProtectedRequestError`, `isValidTransportTimeValue`, `loadDashboard`, `normalizeTransportTimeValue`, `normalizeVehicleToleranceSetting`, `requestJson`, `resolveTransportVehicleSeatDefaults`
- Endpoints/rotas envolvidos: `PUT /api/transport/settings`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function saveTransportSettings(nextValues) {
      const previousWorkToHomeTime = state.workToHomeTime;
      const previousLastUpdateTime = state.lastUpdateTime;
      const previousVehicleSeatDefaults = Object.assign({}, state.vehicleSeatDefaults);
      const previousVehicleToleranceDefaultMinutes = state.vehicleToleranceDefaultMinutes;
      const normalizedTime = normalizeTransportTimeValue(
        nextValues && nextValues.workToHomeTime,
        normalizeTransportTimeValue(state.workToHomeTime, DEFAULT_WORK_TO_HOME_TIME)
      );
      const normalizedLastUpdateTime = normalizeTransportTimeValue(
        nextValues && nextValues.lastUpdateTime,
        normalizeTransportTimeValue(state.lastUpdateTime, DEFAULT_LAST_UPDATE_TIME)
      );
      const normalizedSeatDefaults = resolveTransportVehicleSeatDefaults(
        {
          default_car_seats: nextValues && nextValues.defaultCarSeats,
          default_minivan_seats: nextValues && nextValues.defaultMinivanSeats,
          default_van_seats: nextValues && nextValues.defaultVanSeats,
          default_bus_seats: nextValues && nextValues.defaultBusSeats,
        },
        state.vehicleSeatDefaults
      );
      const normalizedToleranceDefault = normalizeVehicleToleranceSetting(
        nextValues && nextValues.defaultToleranceMinutes,
        state.vehicleToleranceDefaultMinutes
      );
      if (!isValidTransportTimeValue(normalizedTime) || !isValidTransportTimeValue(normalizedLastUpdateTime)) {
        syncSettingsControls();
        return Promise.resolve(null);
      }
      if (!state.isAuthenticated) {
        setStatus(getTransportLockedMessage(), "warning");
        syncSettingsControls();
        return Promise.resolve(null);
      }

      state.workToHomeTime = normalizedTime;
      state.lastUpdateTime = normalizedLastUpdateTime;
      state.vehicleSeatDefaults = Object.assign({}, normalizedSeatDefaults);
      state.vehicleToleranceDefaultMinutes = normalizedToleranceDefault;
      applyTransportVehicleSeatDefaults(state.vehicleSeatDefaults);
      applyTransportVehicleToleranceDefault(state.vehicleToleranceDefaultMinutes);
      state.settingsSaving = true;
      syncSettingsControls();
      return requestJson(`${TRANSPORT_API_PREFIX}/settings`, {
        method: "PUT",
        body: JSON.stringify({
          work_to_home_time: normalizedTime,
          last_update_time: normalizedLastUpdateTime,
          default_car_seats: normalizedSeatDefaults.carro,
          default_minivan_seats: normalizedSeatDefaults.minivan,
          default_van_seats: normalizedSeatDefaults.van,
          default_bus_seats: normalizedSeatDefaults.onibus,
          default_tolerance_minutes: normalizedToleranceDefault,
        }),
      })
        .then(function (response) {
          state.settingsLoaded = true;
          state.workToHomeTime = String(
            response && response.work_to_home_time ? response.work_to_home_time : normalizedTime
          );
          state.lastUpdateTime = String(
            response && response.last_update_time ? response.last_update_time : normalizedLastUpdateTime
          );
          state.vehicleSeatDefaults = applyTransportVehicleSeatDefaults(response);
          state.vehicleToleranceDefaultMinutes = applyTransportVehicleToleranceDefault(
            response && response.default_tolerance_minutes !== undefined
              ? response.default_tolerance_minutes
              : normalizedToleranceDefault
          );
          return loadDashboard(dateStore.getValue(), { announce: false }).then(function () {
            setStatus(t("status.settingsSaved"), "success");
            return response;
          });
        })
        .catch(function (error) {
          state.workToHomeTime = previousWorkToHomeTime;
          state.lastUpdateTime = previousLastUpdateTime;
          state.vehicleSeatDefaults = previousVehicleSeatDefaults;
          state.vehicleToleranceDefaultMinutes = previousVehicleToleranceDefaultMinutes;
          applyTransportVehicleSeatDefaults(previousVehicleSeatDefaults);
          applyTransportVehicleToleranceDefault(previousVehicleToleranceDefaultMinutes);
          handleProtectedRequestError(error, t("status.couldNotSaveSettings"));
          return null;
        })
        .finally(function () {
          state.settingsSaving = false;
          syncSettingsControls();
        });
    }
```
