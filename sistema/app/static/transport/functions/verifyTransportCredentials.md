# verifyTransportCredentials

- Nome da funcao: `verifyTransportCredentials`
- Arquivo gerado: `verifyTransportCredentials.md`
- Origem: `sistema/app/static/transport/app.js:2232`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte credenciais
- Categoria: API + state + date/time
- Responsabilidade: Valida as credenciais digitadas na barra superior, atualiza o estado de autenticacao e, em caso de sucesso, carrega dashboard e configuracoes.
- Entradas: Recebe `requestToken` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getTransportLockedMessage`, `getValue`, `loadDashboard`, `loadTransportSettings`, `localizeTransportApiMessage`, `normalizeAuthKeyValue`, `requestJson`, `setAuthenticationState`, `setStatus`, `t`, `dateStore`
- Endpoints/rotas envolvidos: `POST /api/transport/auth/verify`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function verifyTransportCredentials(requestToken) {
      const chave = normalizeAuthKeyValue();
      const senha = authPasswordInput ? String(authPasswordInput.value || "") : "";
      if (chave.length !== 4 || !senha) {
        return Promise.resolve(null);
      }

      return requestJson(`${TRANSPORT_API_PREFIX}/auth/verify`, {
        method: "POST",
        body: JSON.stringify({ chave: chave, senha: senha }),
      })
        .then(function (response) {
          if (requestToken !== state.authVerifyToken) {
            return null;
          }

          if (response && response.authenticated && response.user) {
            setAuthenticationState(true, response.user, {});
            setStatus(localizeTransportApiMessage(response.message) || t("status.accessGranted"), "success");
            return Promise.all([
              loadDashboard(dateStore.getValue(), { announce: false }),
              loadTransportSettings({ silent: true }),
            ]);
          }

          setAuthenticationState(false, null, {});
          setStatus(localizeTransportApiMessage(response && response.message) || getTransportLockedMessage(), "warning");
          return null;
        })
        .catch(function (error) {
          if (requestToken !== state.authVerifyToken) {
            return null;
          }
          setStatus(localizeTransportApiMessage(error && error.message) || t("status.couldNotVerify"), "error");
          return null;
        });
    }
```
