# groupAssignedRequestsByVehicleForDate

- Nome da funcao: `groupAssignedRequestsByVehicleForDate`
- Arquivo gerado: `groupAssignedRequestsByVehicleForDate.md`
- Origem: `sistema/app/static/transport/app.js:1059`
- Escopo original: topo do modulo
- Tema funcional: alocada solicitacoes by veiculo para data
- Categoria: date/time
- Responsabilidade: Organiza colecoes do dashboard de transporte em uma estrutura intermediaria pronta para renderizacao, filtro ou tomada de decisao.
- Entradas: Recebe `requestRows`, `selectedDate` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function groupAssignedRequestsByVehicleForDate(requestRows, selectedDate) {
    const normalizedSelectedDate = String(selectedDate || "");
    return (Array.isArray(requestRows) ? requestRows : []).reduce(function (grouped, requestRow) {
      if (
        !requestRow
        || requestRow.assignment_status !== "confirmed"
        || !requestRow.assigned_vehicle
        || requestRow.assigned_vehicle.id === undefined
      ) {
        return grouped;
      }

      if (normalizedSelectedDate && String(requestRow.service_date || "") !== normalizedSelectedDate) {
        return grouped;
      }

      const vehicleId = String(requestRow.assigned_vehicle.id);
      if (!grouped[vehicleId]) {
        grouped[vehicleId] = [];
      }
      grouped[vehicleId].push(requestRow);
      return grouped;
    }, {});
  }
```
