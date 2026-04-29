# toggleRequestRowCollapsed

- Nome da funcao: `toggleRequestRowCollapsed`
- Arquivo gerado: `toggleRequestRowCollapsed.md`
- Origem: `sistema/app/static/transport/app.js:1726`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: linha de solicitacao collapsed
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `requestRow`, `rowButton` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `applyRequestRowCollapsedVisualState`, `getRequestRowCollapsedState`, `preserveRequestSectionScrollPosition`, `setRequestRowCollapsedState`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function toggleRequestRowCollapsed(requestRow, rowButton) {
      if (!requestRow || !rowButton) {
        return;
      }

      setRequestRowCollapsedState(requestRow, !getRequestRowCollapsedState(requestRow));
      preserveRequestSectionScrollPosition(requestRow.request_kind, function () {
        applyRequestRowCollapsedVisualState(rowButton, getRequestRowCollapsedState(requestRow));
      });
    }
```
