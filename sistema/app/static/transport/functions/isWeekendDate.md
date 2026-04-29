# isWeekendDate

- Nome da funcao: `isWeekendDate`
- Arquivo gerado: `isWeekendDate.md`
- Origem: `sistema/app/static/transport/app.js:270`
- Escopo original: topo do modulo
- Tema funcional: fim de semana data
- Categoria: utility
- Responsabilidade: Predicate do dashboard de transporte que inspeciona os dados disponiveis e devolve a decisao booleana usada para permitir, negar ou destacar um comportamento.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor booleano usado para gating de UI, validacao ou destaque de estado.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `startOfLocalDay`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function isWeekendDate(value) {
    const date = startOfLocalDay(value);
    return date.getDay() === 0 || date.getDay() === 6;
  }
```
