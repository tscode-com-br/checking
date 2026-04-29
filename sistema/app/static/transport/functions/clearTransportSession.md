# clearTransportSession

- Nome da funcao: `clearTransportSession`
- Arquivo gerado: `clearTransportSession.md`
- Origem: `sistema/app/static/transport/app.js:2035`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte sessao
- Categoria: API + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `message` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearPendingAuthVerification`, `getTransportLockedMessage`, `requestJson`, `setAuthenticationState`, `setStatus`
- Endpoints/rotas envolvidos: `POST /api/transport/auth/logout`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function clearTransportSession(message) {
      state.authVerifyToken += 1;
      clearPendingAuthVerification();
      setAuthenticationState(false, null, { resetInputs: true, clearDashboard: true });
      requestJson(`${TRANSPORT_API_PREFIX}/auth/logout`, { method: "POST" }).catch(function () {});
      setStatus(message || getTransportLockedMessage(), "warning");
    }
```
