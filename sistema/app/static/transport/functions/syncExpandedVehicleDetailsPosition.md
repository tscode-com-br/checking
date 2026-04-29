# syncExpandedVehicleDetailsPosition

- Nome da funcao: `syncExpandedVehicleDetailsPosition`
- Arquivo gerado: `syncExpandedVehicleDetailsPosition.md`
- Origem: `sistema/app/static/transport/app.js:2870`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: expandido detalhes do veiculo posicao
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `clearElement`, `findExpandedVehicleDetailsElements`, `parsePixelValue`, `resolveVehicleDetailsPosition`, `document`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function syncExpandedVehicleDetailsPosition() {
      const expandedElements = findExpandedVehicleDetailsElements();
      if (!expandedElements) {
        clearElement(vehicleDetailsOverlayHost);
        vehicleDetailsOverlayHost.classList.remove("is-active");
        return;
      }

      const anchorRect = expandedElements.anchorButton.getBoundingClientRect();
      const detailsStyles = typeof globalScope.getComputedStyle === "function"
        ? globalScope.getComputedStyle(expandedElements.detailsPanel)
        : null;
      const panelWidth = Math.max(
        1,
        expandedElements.detailsPanel.offsetWidth
        || parsePixelValue(detailsStyles ? detailsStyles.width : "", 264)
      );
      const panelHeight = Math.max(
        1,
        expandedElements.detailsPanel.offsetHeight
        || parsePixelValue(detailsStyles ? detailsStyles.height : "", 248)
      );
      const viewportWidth = Math.max(
        0,
        globalScope.innerWidth
        || (document.documentElement ? document.documentElement.clientWidth : 0)
      );
      const viewportHeight = Math.max(
        0,
        globalScope.innerHeight
        || (document.documentElement ? document.documentElement.clientHeight : 0)
      );
      const nextPosition = resolveVehicleDetailsPosition({
        anchorRect,
        panelWidth,
        panelHeight,
        viewportWidth,
        viewportHeight,
        offset: VEHICLE_DETAILS_PANEL_OFFSET,
        viewportMargin: VEHICLE_DETAILS_VIEWPORT_MARGIN,
      });

      expandedElements.detailsPanel.style.left = `${nextPosition.left}px`;
      expandedElements.detailsPanel.style.top = `${nextPosition.top}px`;
      expandedElements.detailsPanel.dataset.horizontalDirection = nextPosition.horizontalDirection;
      expandedElements.detailsPanel.classList.add("is-positioned");
    }
```
