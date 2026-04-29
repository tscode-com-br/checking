# removeVehicleFromRoute

- Nome da funcao: `removeVehicleFromRoute`
- Arquivo gerado: `removeVehicleFromRoute.md`
- Origem: `sistema/app/static/transport/app.js:3290`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo from rota
- Categoria: API + state + date/time
- Responsabilidade: Remove um veiculo da agenda/rota atual pela API usando o `schedule_id` e a `service_date`, com feedback visual e recarga do dashboard.
- Entradas: Recebe `vehicle` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getCurrentServiceDateIso`, `getValue`, `handleProtectedRequestError`, `loadDashboard`, `requestJson`, `setStatus`, `t`, `dateStore`
- Endpoints/rotas envolvidos: `DELETE /api/transport/vehicles/{schedule_id}?service_date=...`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function removeVehicleFromRoute(vehicle) {
      if (!vehicle || vehicle.schedule_id === null || vehicle.schedule_id === undefined) {
        setStatus(t("warnings.vehicleCannotBeRemoved"), "error");
        return Promise.resolve();
      }

      const deleteServiceDate = vehicle.service_date || getCurrentServiceDateIso();

      return requestJson(
        `${TRANSPORT_API_PREFIX}/vehicles/${encodeURIComponent(String(vehicle.schedule_id))}?service_date=${encodeURIComponent(deleteServiceDate)}`,
        {
          method: "DELETE",
        }
      )
        .then(function () {
          setStatus(t("status.vehicleDeleted"), "success");
          return loadDashboard(dateStore.getValue(), { announce: false });
        })
        .catch(function (error) {
          handleProtectedRequestError(error, t("status.couldNotDeleteVehicle"));
        });
    }
```
