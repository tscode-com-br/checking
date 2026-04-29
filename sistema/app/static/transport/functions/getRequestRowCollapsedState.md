# getRequestRowCollapsedState

- Nome da funcao: `getRequestRowCollapsedState`
- Arquivo gerado: `getRequestRowCollapsedState.md`
- Origem: `sistema/app/static/transport/app.js:1662`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: linha de solicitacao collapsed state
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `requestRow` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a linha de solicitacao collapsed state, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getRequestSectionCollapsedState`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getRequestRowCollapsedState(requestRow) {
      if (!requestRow || requestRow.id === undefined || requestRow.id === null) {
        return false;
      }

      const requestIdKey = String(requestRow.id);
      if (Object.prototype.hasOwnProperty.call(state.requestRowCollapseOverrides, requestIdKey)) {
        return Boolean(state.requestRowCollapseOverrides[requestIdKey]);
      }

      return getRequestSectionCollapsedState(requestRow.request_kind);
    }
```
