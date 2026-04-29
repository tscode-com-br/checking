# submitAssignment

- Nome da funcao: `submitAssignment`
- Arquivo gerado: `submitAssignment.md`
- Origem: `sistema/app/static/transport/app.js:3229`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: assignment
- Categoria: API + state + date/time
- Responsabilidade: Envia uma alteracao de alocacao para a API, trata erros protegidos e recarrega o dashboard quando a operacao e aceita.
- Entradas: Recebe `payload` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getValue`, `handleProtectedRequestError`, `loadDashboard`, `requestJson`, `setStatus`, `t`, `dateStore`
- Endpoints/rotas envolvidos: `POST /api/transport/assignments`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function submitAssignment(payload) {
      return requestJson(`${TRANSPORT_API_PREFIX}/assignments`, {
        method: "POST",
        body: JSON.stringify(payload),
      }).then(function () {
        setStatus(t("status.allocationUpdated"), "success");
        return loadDashboard(dateStore.getValue(), { announce: false });
      }).catch(function (error) {
        if (handleProtectedRequestError(error, t("status.couldNotUpdateAllocation"))) {
          return null;
        }
        throw error;
      });
    }
```
