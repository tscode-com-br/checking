# enableResizableDivider

- Nome da funcao: `enableResizableDivider`
- Arquivo gerado: `enableResizableDivider.md`
- Origem: `sistema/app/static/transport/app.js:503`
- Escopo original: topo do modulo
- Tema funcional: resizable divisor
- Categoria: UI
- Responsabilidade: Encapsula uma responsabilidade interna do dashboard de transporte, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `dividerElement` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: `applyResize`, `stopResize`
- Dependencias observadas: `parsePositiveNumber`, `resolvePanelMinimumSize`, `resolvePanelSizes`, `resolveResizeConfig`, `updateVehicleGridLayouts`, `document`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function enableResizableDivider(dividerElement) {
    const orientation = dividerElement.dataset.resize;
    if (!orientation) {
      return;
    }

    const containerElement = dividerElement.parentElement;
    const firstPanelElement = dividerElement.previousElementSibling;
    const secondPanelElement = dividerElement.nextElementSibling;
    if (!containerElement || !firstPanelElement || !secondPanelElement) {
      return;
    }

    const resizeConfig = resolveResizeConfig(orientation);

    dividerElement.addEventListener("pointerdown", function (event) {
      if (event.pointerType !== "touch" && event.button !== 0) {
        return;
      }

      const childElements = Array.from(containerElement.children);
      const dividerIndex = childElements.indexOf(dividerElement);
      const firstPanelIndex = dividerIndex - 1;
      const secondPanelIndex = dividerIndex + 1;
      if (dividerIndex < 0 || firstPanelIndex < 0 || secondPanelIndex >= childElements.length) {
        return;
      }

      const containerRect = containerElement.getBoundingClientRect();
      const trackSizes = childElements.map(function (element) {
        return Math.round(element.getBoundingClientRect()[resizeConfig.sizeProperty]);
      });
      const dividerSize = trackSizes[dividerIndex];
      const resizeGroupSize =
        trackSizes[firstPanelIndex] + dividerSize + trackSizes[secondPanelIndex];
      const groupOffset = trackSizes.slice(0, firstPanelIndex).reduce(function (sum, size) {
        return sum + size;
      }, 0);
      const minFirstSize = resolvePanelMinimumSize(
        firstPanelElement,
        parsePositiveNumber(dividerElement.dataset.minFirst, RESIZE_DEFAULT_MIN_SIZE)
      );
      const minSecondSize = resolvePanelMinimumSize(
        secondPanelElement,
        parsePositiveNumber(dividerElement.dataset.minSecond, RESIZE_DEFAULT_MIN_SIZE)
      );

      function applyResize(moveEvent) {
        const pointerOffset = moveEvent[
          orientation === "vertical" ? "clientX" : "clientY"
        ] - containerRect[resizeConfig.startProperty] - groupOffset;
        const nextSizes = resolvePanelSizes({
          containerSize: resizeGroupSize,
          dividerSize,
          pointerOffset,
          minFirstSize,
          minSecondSize,
        });
        const nextTrackSizes = trackSizes.slice();
        nextTrackSizes[firstPanelIndex] = nextSizes.firstSize;
        nextTrackSizes[dividerIndex] = Math.round(dividerSize);
        nextTrackSizes[secondPanelIndex] = nextSizes.secondSize;
        containerElement.style[resizeConfig.gridProperty] = nextTrackSizes
          .map(function (size) {
            return `${Math.round(size)}px`;
          })
          .join(" ");
        updateVehicleGridLayouts(containerElement);
      }

      function stopResize() {
        globalScope.removeEventListener("pointermove", applyResize);
        globalScope.removeEventListener("pointerup", stopResize);
        globalScope.removeEventListener("pointercancel", stopResize);
        document.body.classList.remove("transport-is-resizing");
      }

      document.body.classList.add("transport-is-resizing");
      globalScope.addEventListener("pointermove", applyResize);
      globalScope.addEventListener("pointerup", stopResize, { once: true });
      globalScope.addEventListener("pointercancel", stopResize, { once: true });
      applyResize(event);
      event.preventDefault();
    });
  }
```
