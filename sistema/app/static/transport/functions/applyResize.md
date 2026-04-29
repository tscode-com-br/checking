# applyResize

- Nome da funcao: `applyResize`
- Arquivo gerado: `applyResize.md`
- Origem: `sistema/app/static/transport/app.js:550`
- Escopo original: interna de `enableResizableDivider`
- Tema funcional: redimensionamento
- Categoria: utility
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `moveEvent` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `resolvePanelSizes`, `updateVehicleGridLayouts`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
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
```
