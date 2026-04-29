# createDatePanelController

- Nome da funcao: `createDatePanelController`
- Arquivo gerado: `createDatePanelController.md`
- Origem: `sistema/app/static/transport/app.js:589`
- Escopo original: topo do modulo
- Tema funcional: data painel controller
- Categoria: UI + date/time
- Responsabilidade: Factory/builder do dashboard de transporte que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `rootElement`, `dateStore` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: `render`
- Dependencias observadas: `formatTransportDate`, `getTransportDateState`, `setValue`, `shiftValue`, `subscribe`, `dateStore`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function createDatePanelController(rootElement, dateStore) {
    const labelElement = rootElement.querySelector("[data-date-label]");
    const dateLink = rootElement.querySelector("[data-date-link]");
    const previousButton = rootElement.querySelector('[data-date-shift="-1"]');
    const nextButton = rootElement.querySelector('[data-date-shift="1"]');

    function render(selectedDate) {
      if (labelElement) {
        labelElement.textContent = formatTransportDate(selectedDate);
        labelElement.dataset.dateState = getTransportDateState(selectedDate);
      }
    }

    if (previousButton) {
      previousButton.addEventListener("click", function () {
        dateStore.shiftValue(-1);
      });
    }

    if (nextButton) {
      nextButton.addEventListener("click", function () {
        dateStore.shiftValue(1);
      });
    }

    if (dateLink) {
      dateLink.addEventListener("click", function (event) {
        event.preventDefault();
        dateStore.setValue(new Date());
      });
    }

    dateStore.subscribe(render);
  }
```
