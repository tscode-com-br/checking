# startRealtimeUpdates

- Nome da funcao: `startRealtimeUpdates`
- Arquivo gerado: `startRealtimeUpdates.md`
- Origem: `sistema/app/static/transport/app.js:1979`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: tempo real updates
- Categoria: API + state
- Responsabilidade: Orquestra um fluxo operacional do controller da pagina, ligando validacao local, integracao externa, feedback visual e recarga de dados quando necessario.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `requestDashboardRefresh`, `stopRealtimeUpdates`, `globalScope`
- Endpoints/rotas envolvidos: `SSE /api/transport/stream`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Abre, fecha ou administra o canal SSE de atualizacoes em tempo real.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function startRealtimeUpdates() {
      stopRealtimeUpdates();
      if (typeof globalScope.EventSource !== "function") {
        return;
      }

      state.realtimeEventStream = new globalScope.EventSource(`${TRANSPORT_API_PREFIX}/stream`);
      state.realtimeEventStream.onopen = function () {
        state.realtimeConnected = true;
      };
      state.realtimeEventStream.onmessage = function () {
        state.realtimeConnected = true;
        requestDashboardRefresh({ announce: false });
      };
      state.realtimeEventStream.onerror = function () {
        state.realtimeConnected = false;
      };
    }
```
