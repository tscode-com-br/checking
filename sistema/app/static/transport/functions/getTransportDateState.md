# getTransportDateState

- Nome da funcao: `getTransportDateState`
- Arquivo gerado: `getTransportDateState.md`
- Origem: `sistema/app/static/transport/app.js:259`
- Escopo original: topo do modulo
- Tema funcional: transporte data state
- Categoria: date/time
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value`, `referenceValue` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a transporte data state, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `startOfLocalDay`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getTransportDateState(value, referenceValue) {
    const selectedDate = startOfLocalDay(value);
    const referenceDate = startOfLocalDay(referenceValue || new Date());

    if (selectedDate.getTime() === referenceDate.getTime()) {
      return "today";
    }

    return selectedDate.getTime() > referenceDate.getTime() ? "future" : "past";
  }
```
