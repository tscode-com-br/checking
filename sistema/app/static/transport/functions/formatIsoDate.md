# formatIsoDate

- Nome da funcao: `formatIsoDate`
- Arquivo gerado: `formatIsoDate.md`
- Origem: `sistema/app/static/transport/app.js:215`
- Escopo original: topo do modulo
- Tema funcional: ISO data
- Categoria: date/time
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a ISO data, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `startOfLocalDay`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function formatIsoDate(value) {
    const date = startOfLocalDay(value);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  }
```
