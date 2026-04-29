# getVehicleDepartureTime

- Nome da funcao: `getVehicleDepartureTime`
- Arquivo gerado: `getVehicleDepartureTime.md`
- Origem: `sistema/app/static/transport/app.js:1028`
- Escopo original: topo do modulo
- Tema funcional: veiculo saida horario
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `vehicle`, `fallbackTime`, `scopeOverride` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo saida horario, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `isValidTransportTimeValue`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getVehicleDepartureTime(vehicle, fallbackTime, scopeOverride) {
    const departureTime = String(vehicle && vehicle.departure_time || "").trim();
    if (isValidTransportTimeValue(departureTime)) {
      return departureTime;
    }

    const resolvedScope = String(vehicle && vehicle.service_scope || scopeOverride || "").trim();
    if (resolvedScope !== "regular" && resolvedScope !== "weekend") {
      return "";
    }

    return isValidTransportTimeValue(fallbackTime) ? String(fallbackTime).trim() : "";
  }
```
