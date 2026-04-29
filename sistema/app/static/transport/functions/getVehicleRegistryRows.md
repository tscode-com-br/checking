# getVehicleRegistryRows

- Nome da funcao: `getVehicleRegistryRows`
- Arquivo gerado: `getVehicleRegistryRows.md`
- Origem: `sistema/app/static/transport/app.js:2710`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo registry linhas
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a veiculo registry linhas, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getVehicleRegistryRows(scope) {
      if (!state.dashboard) {
        return [];
      }
      return Array.isArray(state.dashboard[`${scope}_vehicle_registry`])
        ? state.dashboard[`${scope}_vehicle_registry`]
        : [];
    }
```
