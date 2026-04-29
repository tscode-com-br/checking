# getEffectiveWorkToHomeDepartureTime

- Nome da funcao: `getEffectiveWorkToHomeDepartureTime`
- Arquivo gerado: `getEffectiveWorkToHomeDepartureTime.md`
- Origem: `sistema/app/static/transport/app.js:1019`
- Escopo original: topo do modulo
- Tema funcional: efetivo rota trabalho para casa saida horario
- Categoria: utility
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `dashboard`, `fallbackTime` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a efetivo rota trabalho para casa saida horario, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `isValidTransportTimeValue`, `normalizeTransportTimeValue`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getEffectiveWorkToHomeDepartureTime(dashboard, fallbackTime) {
    const dashboardTime = String(dashboard && dashboard.work_to_home_departure_time || "").trim();
    if (isValidTransportTimeValue(dashboardTime)) {
      return dashboardTime;
    }

    return normalizeTransportTimeValue(fallbackTime, DEFAULT_WORK_TO_HOME_TIME);
  }
```
