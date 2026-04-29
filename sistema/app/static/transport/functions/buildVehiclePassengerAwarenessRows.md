# buildVehiclePassengerAwarenessRows

- Nome da funcao: `buildVehiclePassengerAwarenessRows`
- Arquivo gerado: `buildVehiclePassengerAwarenessRows.md`
- Origem: `sistema/app/static/transport/app.js:1115`
- Escopo original: topo do modulo
- Tema funcional: veiculo passageiro ciencia linhas
- Categoria: utility
- Responsabilidade: Factory/builder do dashboard de transporte que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `assignedRows`, `maxRows` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getPassengerAwarenessState`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function buildVehiclePassengerAwarenessRows(assignedRows, maxRows) {
    const normalizedMaxRows = Math.max(1, Number(maxRows) || VEHICLE_DETAILS_MAX_ROWS);
    const rows = Array.isArray(assignedRows)
      ? assignedRows.map(function (requestRow) {
          return {
            name: String((requestRow && requestRow.nome) || ""),
            awarenessState: getPassengerAwarenessState(requestRow),
          };
        })
      : [];

    while (rows.length < normalizedMaxRows) {
      rows.push({
        name: "",
        awarenessState: null,
      });
    }

    return rows;
  }
```
