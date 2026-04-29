# resolvePanelSizes

- Nome da funcao: `resolvePanelSizes`
- Arquivo gerado: `resolvePanelSizes.md`
- Origem: `sistema/app/static/transport/app.js:343`
- Escopo original: topo do modulo
- Tema funcional: painel sizes
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `clampValue`, `parsePositiveNumber`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function resolvePanelSizes(options) {
    const containerSize = Math.max(0, Number(options.containerSize) || 0);
    const dividerSize = Math.max(0, Number(options.dividerSize) || 0);
    const availableSize = Math.max(0, containerSize - dividerSize);
    const minFirstSize = Math.min(
      parsePositiveNumber(options.minFirstSize, RESIZE_DEFAULT_MIN_SIZE),
      availableSize
    );
    const minSecondSize = Math.min(
      parsePositiveNumber(options.minSecondSize, RESIZE_DEFAULT_MIN_SIZE),
      availableSize
    );
    const maxFirstSize = Math.max(minFirstSize, availableSize - minSecondSize);
    const firstSize = clampValue(Number(options.pointerOffset) || 0, minFirstSize, maxFirstSize);
    return {
      firstSize: Math.round(firstSize),
      secondSize: Math.round(Math.max(0, availableSize - firstSize)),
    };
  }
```
