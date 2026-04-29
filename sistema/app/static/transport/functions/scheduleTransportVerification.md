# scheduleTransportVerification

- Nome da funcao: `scheduleTransportVerification`
- Arquivo gerado: `scheduleTransportVerification.md`
- Origem: `sistema/app/static/transport/app.js:2270`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte verificacao
- Categoria: state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearPendingAuthVerification`, `getTransportLockedMessage`, `normalizeAuthKeyValue`, `setAuthenticationState`, `setStatus`, `verifyTransportCredentials`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Agenda ou cancela trabalho assincrono no navegador.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function scheduleTransportVerification() {
      clearPendingAuthVerification();
      const chave = normalizeAuthKeyValue();
      const senha = authPasswordInput ? String(authPasswordInput.value || "") : "";
      if (chave.length !== 4 || !senha) {
        state.authVerifyToken += 1;
        setAuthenticationState(false, null, {});
        setStatus(getTransportLockedMessage(), "warning");
        return;
      }

      state.authVerifyToken += 1;
      const requestToken = state.authVerifyToken;
      state.authVerifyTimer = globalScope.setTimeout(function () {
        state.authVerifyTimer = null;
        verifyTransportCredentials(requestToken);
      }, TRANSPORT_AUTH_VERIFY_DELAY_MS);
    }
```
