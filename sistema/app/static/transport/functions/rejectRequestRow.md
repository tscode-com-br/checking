# rejectRequestRow

- Nome da funcao: `rejectRequestRow`
- Arquivo gerado: `rejectRequestRow.md`
- Origem: `sistema/app/static/transport/app.js:3244`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: linha de solicitacao
- Categoria: API + state + date/time
- Responsabilidade: Rejeita uma solicitacao de transporte pela API usando o `request_id`, a `service_date` efetiva e a rota resolvida para a linha.
- Entradas: Recebe `requestRow` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getRouteKindForRequestRow`, `getValue`, `handleProtectedRequestError`, `loadDashboard`, `requestJson`, `setStatus`, `t`, `dateStore`
- Endpoints/rotas envolvidos: `POST /api/transport/requests/reject`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function rejectRequestRow(requestRow) {
      if (!requestRow || !requestRow.id || !requestRow.service_date) {
        setStatus(t("status.couldNotRejectSelectedRequest"), "error");
        return Promise.resolve();
      }

      return requestJson(`${TRANSPORT_API_PREFIX}/requests/reject`, {
        method: "POST",
        body: JSON.stringify({
          request_id: requestRow.id,
          service_date: requestRow.service_date,
          route_kind: getRouteKindForRequestRow(requestRow),
        }),
      }).then(function () {
        setStatus(t("status.requestRejected"), "success");
        return loadDashboard(dateStore.getValue(), { announce: false });
      }).catch(function (error) {
        if (handleProtectedRequestError(error, t("status.couldNotRejectSelectedRequest"))) {
          return null;
        }
        throw error;
      });
    }
```
