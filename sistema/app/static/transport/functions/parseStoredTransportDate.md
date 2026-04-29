# parseStoredTransportDate

- Nome da funcao: `parseStoredTransportDate`
- Arquivo gerado: `parseStoredTransportDate.md`
- Origem: `sistema/app/static/transport/app.js:220`
- Escopo original: topo do modulo
- Tema funcional: persistido transporte data
- Categoria: date/time
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a persistido transporte data, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `startOfLocalDay`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function parseStoredTransportDate(value) {
    const rawValue = String(value || "").trim();
    const match = rawValue.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) {
      return null;
    }

    const year = Number(match[1]);
    const monthIndex = Number(match[2]) - 1;
    const dayOfMonth = Number(match[3]);
    const parsedDate = new Date(year, monthIndex, dayOfMonth);
    if (
      Number.isNaN(parsedDate.getTime())
      || parsedDate.getFullYear() !== year
      || parsedDate.getMonth() !== monthIndex
      || parsedDate.getDate() !== dayOfMonth
    ) {
      return null;
    }

    return startOfLocalDay(parsedDate);
  }
```
