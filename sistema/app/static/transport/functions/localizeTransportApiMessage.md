# localizeTransportApiMessage

- Nome da funcao: `localizeTransportApiMessage`
- Arquivo gerado: `localizeTransportApiMessage.md`
- Origem: `sistema/app/static/transport/app.js:716`
- Escopo original: topo do modulo
- Tema funcional: transporte mensagem de API
- Categoria: utility
- Responsabilidade: Encapsula uma responsabilidade interna do dashboard de transporte, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Recebe `message` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `t`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function localizeTransportApiMessage(message) {
    const normalizedMessage = String(message || "").trim();
    if (!normalizedMessage) {
      return "";
    }

    const messageKey = {
      "Invalid key or password.": "auth.invalidCredentials",
      "This user does not have transport access.": "auth.noAccess",
      "Transport access granted.": "status.accessGranted",
      "Vehicle saved successfully.": "status.vehicleSaved",
      "Vehicle deleted from the database.": "status.vehicleDeleted",
      "Transport request rejected successfully.": "status.requestRejected",
      "departure_time is required for extra vehicles": "warnings.extraDepartureRequired",
      "Weekend vehicles must be persistent. Select Every Saturday and/or Every Sunday, or create the vehicle in Extra Transport List.": "warnings.weekendPersistence",
      "Regular vehicles must be persistent. Select at least one weekday": "warnings.regularPersistence",
      "Regular vehicles can only be created from Monday to Friday.": "warnings.regularWeekdayOnly",
      "Weekend vehicles can only be created on Saturdays or Sundays.": "warnings.weekendWeekendOnly",
      "This vehicle cannot be removed from the selected route.": "warnings.vehicleCannotBeRemoved",
    }[normalizedMessage];

    return messageKey ? t(messageKey) : normalizedMessage;
  }
```
