# resolveTransportVehicleSeatDefaults

- Nome da funcao: `resolveTransportVehicleSeatDefaults`
- Arquivo gerado: `resolveTransportVehicleSeatDefaults.md`
- Origem: `sistema/app/static/transport/app.js:748`
- Escopo original: topo do modulo
- Tema funcional: transporte veiculo assento defaults
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `source`, `fallbackValues` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `normalizeVehicleSeatCountSetting`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function resolveTransportVehicleSeatDefaults(source, fallbackValues) {
    const fallbackSeatDefaults = fallbackValues || DEFAULT_VEHICLE_SEAT_COUNT;
    return {
      carro: normalizeVehicleSeatCountSetting(
        source && (source.carro !== undefined ? source.carro : source.default_car_seats),
        fallbackSeatDefaults.carro
      ),
      minivan: normalizeVehicleSeatCountSetting(
        source && (source.minivan !== undefined ? source.minivan : source.default_minivan_seats),
        fallbackSeatDefaults.minivan
      ),
      van: normalizeVehicleSeatCountSetting(
        source && (source.van !== undefined ? source.van : source.default_van_seats),
        fallbackSeatDefaults.van
      ),
      onibus: normalizeVehicleSeatCountSetting(
        source && (source.onibus !== undefined ? source.onibus : source.default_bus_seats),
        fallbackSeatDefaults.onibus
      ),
    };
  }
```
