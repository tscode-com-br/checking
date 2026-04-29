# buildVehiclePassengerPreviewRows

- Nome da funcao: `buildVehiclePassengerPreviewRows`
- Arquivo gerado: `buildVehiclePassengerPreviewRows.md`
- Origem: `sistema/app/static/transport/app.js:1096`
- Escopo original: topo do modulo
- Tema funcional: veiculo passageiro previsualizacao linhas
- Categoria: utility
- Responsabilidade: Factory/builder do dashboard de transporte que monta a estrutura, o payload ou a composicao visual representada por esta rotina.
- Entradas: Recebe `assignedRows`, `previewRequestRow`, `maxRows` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna a estrutura criada pela funcao, normalmente um objeto, elemento DOM, payload ou colecao montada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function buildVehiclePassengerPreviewRows(assignedRows, previewRequestRow, maxRows) {
    const rows = Array.isArray(assignedRows)
      ? assignedRows.filter(function (requestRow) {
          return !previewRequestRow || Number(requestRow.id) !== Number(previewRequestRow.id);
        })
      : [];

    const previewRows = previewRequestRow ? [previewRequestRow].concat(rows) : rows;
    const normalizedMaxRows = Number.isFinite(Number(maxRows)) && Number(maxRows) > 0
      ? Math.max(1, Number(maxRows))
      : null;

    if (normalizedMaxRows === null) {
      return previewRows;
    }

    return previewRows.slice(0, normalizedMaxRows);
  }
```
