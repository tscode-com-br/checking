# createPassengerRemoveButton

- Nome da funcao: `createPassengerRemoveButton`
- Arquivo gerado: `createPassengerRemoveButton.md`
- Origem: `sistema/app/static/transport/app.js:2935`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: passageiro remocao button
- Categoria: UI + state
- Responsabilidade: Factory/builder do controller da pagina que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `requestRow`, `routeKind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `createNode`, `getRouteKindForRequestRow`, `returnRequestRowToPending`, `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function createPassengerRemoveButton(requestRow, routeKind) {
      const removeButton = createNode("button", "transport-passenger-remove-button", "×");
      const normalizedRouteKind = getRouteKindForRequestRow(requestRow, routeKind);
      const removeLabel = t("misc.removeFromVehicle", { name: String(requestRow && requestRow.nome || "") });

      removeButton.type = "button";
      removeButton.setAttribute("aria-label", removeLabel);
      removeButton.title = removeLabel;
      removeButton.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        void returnRequestRowToPending(requestRow, normalizedRouteKind);
      });
      return removeButton;
    }
```
