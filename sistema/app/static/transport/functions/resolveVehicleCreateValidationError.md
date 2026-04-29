# resolveVehicleCreateValidationError

- Nome da funcao: `resolveVehicleCreateValidationError`
- Arquivo gerado: `resolveVehicleCreateValidationError.md`
- Origem: `sistema/app/static/transport/app.js:925`
- Escopo original: topo do modulo
- Tema funcional: veiculo create validacao erro
- Categoria: date/time
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `payload` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function resolveVehicleCreateValidationError(payload) {
    if (!payload || typeof payload !== "object") {
      return null;
    }

    if (payload.service_scope === "extra" && !String(payload.service_date || "").trim()) {
      return {
        messageKey: "warnings.extraServiceDateRequired",
        focusField: "service_date",
      };
    }

    if (payload.service_scope === "extra" && !String(payload.departure_time || "").trim()) {
      return {
        messageKey: "warnings.extraDepartureRequired",
        focusField: "departure_time",
      };
    }

    if (payload.service_scope === "weekend" && !payload.every_saturday && !payload.every_sunday) {
      return {
        messageKey: "warnings.weekendPersistence",
        focusField: null,
      };
    }

    if (
      payload.service_scope === "regular"
      && !payload.every_monday
      && !payload.every_tuesday
      && !payload.every_wednesday
      && !payload.every_thursday
      && !payload.every_friday
    ) {
      return {
        messageKey: "warnings.regularPersistence",
        focusField: null,
      };
    }

    return null;
  }
```
