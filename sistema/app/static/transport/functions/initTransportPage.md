# initTransportPage

- Nome da funcao: `initTransportPage`
- Arquivo gerado: `initTransportPage.md`
- Origem: `sistema/app/static/transport/app.js:3659`
- Escopo original: topo do modulo
- Tema funcional: transporte pagina
- Categoria: UI + date/time
- Responsabilidade: Inicializa a pagina de transporte, cria o store de data, conecta paineis, divisores redimensionaveis, controller principal e listeners globais.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `bootstrapTransportSession`, `closeRouteTimePopover`, `createDatePanelController`, `createTransportDateStore`, `createTransportPageController`, `loadDashboard`, `resolveStoredTransportDate`, `setStoredTransportDate`, `subscribe`, `dateStore`, `document`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function initTransportPage() {
    if (typeof document === "undefined") {
      return;
    }

    const dateStore = createTransportDateStore(resolveStoredTransportDate(new Date()));
    document.querySelectorAll("[data-date-panel]").forEach(function (panelElement) {
      createDatePanelController(panelElement, dateStore);
    });
    document.querySelectorAll("[data-resize]").forEach(enableResizableDivider);
    const pageController = createTransportPageController(dateStore);
    globalScope.CheckingTransportPageController = pageController;
    globalScope.addEventListener("resize", function () {
      pageController.refreshVehicleGridLayouts();
    });
    dateStore.subscribe(function (selectedDate) {
      setStoredTransportDate(selectedDate);
      pageController.closeRouteTimePopover();
      pageController.loadDashboard(selectedDate);
    });
    pageController.bootstrapTransportSession();
  }
```
