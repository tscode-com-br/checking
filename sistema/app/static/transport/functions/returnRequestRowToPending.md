# returnRequestRowToPending

- Nome da funcao: `returnRequestRowToPending`
- Arquivo gerado: `returnRequestRowToPending.md`
- Origem: `sistema/app/static/transport/app.js:3268`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: linha de solicitacao para pending
- Categoria: state + date/time
- Responsabilidade: Devolve uma solicitacao ao estado pendente, limpando a previsualizacao local e sincronizando as tabelas e os paineis depois da resposta.
- Entradas: Recebe `requestRow`, `routeKind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getSelectedRouteKind`, `renderRequestTables`, `renderVehiclePanels`, `setStatus`, `submitAssignment`, `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function returnRequestRowToPending(requestRow, routeKind) {
      if (!requestRow || !requestRow.id || !requestRow.service_date) {
        setStatus(t("status.couldNotUpdateAllocation"), "error");
        return Promise.resolve();
      }

      return submitAssignment({
        request_id: requestRow.id,
        service_date: requestRow.service_date,
        route_kind: routeKind || getSelectedRouteKind(),
        status: "pending",
      }).then(function (result) {
        if (result === null) {
          return null;
        }
        state.pendingAssignmentPreview = null;
        renderRequestTables();
        renderVehiclePanels();
        return result;
      }).catch(function () {});
    }
```
