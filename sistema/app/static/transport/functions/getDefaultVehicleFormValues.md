# getDefaultVehicleFormValues

- Nome da funcao: `getDefaultVehicleFormValues`
- Arquivo gerado: `getDefaultVehicleFormValues.md`
- Origem: `sistema/app/static/transport/app.js:796`
- Escopo original: topo do modulo
- Tema funcional: padrao veiculo formulario valores
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `vehicleType` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getDefaultVehicleSeatCount`, `getDefaultVehicleToleranceMinutes`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getDefaultVehicleFormValues(vehicleType) {
    const normalizedVehicleType = Object.prototype.hasOwnProperty.call(DEFAULT_VEHICLE_SEAT_COUNT, vehicleType)
      ? vehicleType
      : "carro";

    return {
      tipo: normalizedVehicleType,
      lugares: getDefaultVehicleSeatCount(normalizedVehicleType),
      tolerance: getDefaultVehicleToleranceMinutes(),
    };
  }
```
