# requestDashboardRefresh

- Nome da funcao: `requestDashboardRefresh`
- Arquivo gerado: `requestDashboardRefresh.md`
- Origem: `sistema/app/static/transport/app.js:1966`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: dashboard atualizacao
- Categoria: state + date/time
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearPendingRealtimeRefresh`, `getValue`, `loadDashboard`, `dateStore`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Agenda ou cancela trabalho assincrono no navegador.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function requestDashboardRefresh(options) {
      const refreshOptions = options || {};
      if (!state.isAuthenticated) {
        return;
      }

      clearPendingRealtimeRefresh();
      state.realtimeRefreshTimer = globalScope.setTimeout(function () {
        state.realtimeRefreshTimer = null;
        loadDashboard(dateStore.getValue(), Object.assign({ announce: false }, refreshOptions));
      }, TRANSPORT_REALTIME_DEBOUNCE_MS);
    }
```
