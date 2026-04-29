# resolveVehicleDetailsPosition

- Nome da funcao: `resolveVehicleDetailsPosition`
- Arquivo gerado: `resolveVehicleDetailsPosition.md`
- Origem: `sistema/app/static/transport/app.js:377`
- Escopo original: topo do modulo
- Tema funcional: detalhes do veiculo posicao
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `clampValue`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function resolveVehicleDetailsPosition(options) {
    const anchorRect = options.anchorRect || {};
    const viewportWidth = Math.max(0, Number(options.viewportWidth) || 0);
    const viewportHeight = Math.max(0, Number(options.viewportHeight) || 0);
    const panelWidth = Math.max(1, Number(options.panelWidth) || 0);
    const panelHeight = Math.max(1, Number(options.panelHeight) || 0);
    const offset = Math.max(0, Number(options.offset) || 0);
    const viewportMargin = Math.max(0, Number(options.viewportMargin) || 0);
    const anchorLeft = Number(anchorRect.left) || 0;
    const anchorTop = Number(anchorRect.top) || 0;
    const anchorRight = Number(anchorRect.right);
    const anchorBottom = Number(anchorRect.bottom);
    const anchorWidth = Math.max(
      0,
      Number(anchorRect.width)
      || (Number.isFinite(anchorRight) ? anchorRight - anchorLeft : 0)
    );
    const anchorHeight = Math.max(
      0,
      Number(anchorRect.height)
      || (Number.isFinite(anchorBottom) ? anchorBottom - anchorTop : 0)
    );
    const maxLeft = Math.max(viewportMargin, viewportWidth - panelWidth - viewportMargin);
    const maxTop = Math.max(viewportMargin, viewportHeight - panelHeight - viewportMargin);
    let left = (Number.isFinite(anchorRight) ? anchorRight : anchorLeft + anchorWidth) + offset;
    let horizontalDirection = "right";

    if (left + panelWidth + viewportMargin > viewportWidth) {
      left = anchorLeft - panelWidth - offset;
      horizontalDirection = "left";
    }

    if (left < viewportMargin) {
      left = anchorLeft + ((anchorWidth - panelWidth) / 2);
      horizontalDirection = "center";
    }

    return {
      left: Math.round(clampValue(left, viewportMargin, maxLeft)),
      top: Math.round(
        clampValue(
          anchorTop + ((anchorHeight - panelHeight) / 2),
          viewportMargin,
          maxTop
        )
      ),
      horizontalDirection,
    };
  }
```
