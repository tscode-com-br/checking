# syncRequestSectionCollapsedRowsInDom

- Nome da funcao: `syncRequestSectionCollapsedRowsInDom`
- Arquivo gerado: `syncRequestSectionCollapsedRowsInDom.md`
- Origem: `sistema/app/static/transport/app.js:1714`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: solicitacao secao collapsed linhas in dom
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `kind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `applyRequestRowCollapsedVisualState`, `getRequestRowCollapsedState`, `getVisibleRequestsForKind`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function syncRequestSectionCollapsedRowsInDom(kind) {
      const container = requestContainers[kind];
      if (!container) {
        return;
      }

      getVisibleRequestsForKind(kind).forEach(function (requestRow) {
        const rowButton = container.querySelector(`.transport-request-row[data-request-id="${String(requestRow.id)}"]`);
        applyRequestRowCollapsedVisualState(rowButton, getRequestRowCollapsedState(requestRow));
      });
    }
```
