# bootstrapTransportSession

- Nome da funcao: `bootstrapTransportSession`
- Arquivo gerado: `bootstrapTransportSession.md`
- Origem: `sistema/app/static/transport/app.js:2289`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte sessao
- Categoria: API + state + date/time
- Responsabilidade: Restaura uma sessao ja autenticada a partir do backend no carregamento inicial, decidindo entre liberar ou bloquear a experiencia do dashboard.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getDefaultStatusMessage`, `getTransportLockedMessage`, `getValue`, `loadDashboard`, `loadTransportSettings`, `requestJson`, `setAuthenticationState`, `setStatus`, `dateStore`
- Endpoints/rotas envolvidos: `GET /api/transport/auth/session`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function bootstrapTransportSession() {
      return requestJson(`${TRANSPORT_API_PREFIX}/auth/session`)
        .then(function (response) {
          if (response && response.authenticated && response.user) {
            setAuthenticationState(true, response.user, { fillKey: true });
            setStatus(getDefaultStatusMessage(), "info");
            return Promise.all([
              loadDashboard(dateStore.getValue(), { announce: false }),
              loadTransportSettings({ silent: true }),
            ]);
          }

          setAuthenticationState(false, null, { resetInputs: true, clearDashboard: true });
          setStatus(getTransportLockedMessage(), "warning");
          return null;
        })
        .catch(function () {
          setAuthenticationState(false, null, { resetInputs: true, clearDashboard: true });
          setStatus(getTransportLockedMessage(), "warning");
          return null;
        });
    }
```
