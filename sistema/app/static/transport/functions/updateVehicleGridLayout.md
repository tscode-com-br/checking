# updateVehicleGridLayout

- Nome da funcao: `updateVehicleGridLayout`
- Arquivo gerado: `updateVehicleGridLayout.md`
- Origem: `sistema/app/static/transport/app.js:443`
- Escopo original: topo do modulo
- Tema funcional: grade de veiculos layout
- Categoria: UI
- Responsabilidade: Encapsula uma responsabilidade interna do dashboard de transporte, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `gridElement` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getVehicleGridItemMetrics`, `parsePixelValue`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function updateVehicleGridLayout(gridElement) {
    if (!gridElement) {
      return;
    }

    if (gridElement.dataset.vehicleView === "table" || gridElement.classList.contains("is-management-table")) {
      gridElement.style.removeProperty("grid-template-rows");
      gridElement.style.removeProperty("grid-auto-columns");
      return;
    }

    const itemElements = gridElement.querySelectorAll(".transport-vehicle-button");
    if (!itemElements.length) {
      gridElement.style.removeProperty("grid-template-rows");
      gridElement.style.removeProperty("grid-auto-columns");
      return;
    }

    const gridStyle = globalScope.getComputedStyle(gridElement);
    const rowGap = parsePixelValue(gridStyle.rowGap || gridStyle.gap, 0);
    const metrics = getVehicleGridItemMetrics(gridElement);
    const availableHeight = Math.max(metrics.height, Math.floor(gridElement.clientHeight));
    const computedRowCount = Math.floor((availableHeight + rowGap) / (metrics.height + rowGap));
    const rowCount = Math.max(1, Math.min(itemElements.length, computedRowCount));

    gridElement.style.gridAutoColumns = `${metrics.width}px`;
    gridElement.style.gridTemplateRows = `repeat(${rowCount}, ${metrics.height}px)`;
  }
```
