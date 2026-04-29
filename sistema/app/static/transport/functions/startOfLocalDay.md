# startOfLocalDay

- Nome da funcao: `startOfLocalDay`
- Arquivo gerado: `startOfLocalDay.md`
- Origem: `sistema/app/static/transport/app.js:168`
- Escopo original: topo do modulo
- Tema funcional: de local dia
- Categoria: date/time
- Responsabilidade: Orquestra um fluxo operacional do dashboard de transporte, ligando validacao local, integracao externa, feedback visual e recarga de dados quando necessario.
- Entradas: Recebe `value` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function startOfLocalDay(value) {
    const date = value instanceof Date ? new Date(value) : new Date(value);
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }
```
