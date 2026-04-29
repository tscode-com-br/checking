# updateAuthControls

- Nome da funcao: `updateAuthControls`
- Arquivo gerado: `updateAuthControls.md`
- Origem: `sistema/app/static/transport/app.js:1919`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: autenticacao controles
- Categoria: state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `setAuthShellState`, `syncRouteTimeControls`, `syncSettingsControls`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function updateAuthControls() {
      setAuthShellState(authKeyShell, state.isAuthenticated);
      setAuthShellState(authPasswordShell, state.isAuthenticated);
      if (requestUserButton) {
        requestUserButton.hidden = state.isAuthenticated;
      }
      syncSettingsControls();
      syncRouteTimeControls();
    }
```
