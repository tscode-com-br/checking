# ensureExpandedVehicleStillExists

- Nome da funcao: `ensureExpandedVehicleStillExists`
- Arquivo gerado: `ensureExpandedVehicleStillExists.md`
- Origem: `sistema/app/static/transport/app.js:2781`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: expandido veiculo still exists
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getVehicleDetailsKey`, `getVehiclesForScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function ensureExpandedVehicleStillExists() {
      if (!state.expandedVehicleKey) {
        return;
      }

      const hasVehicle = VEHICLE_SCOPE_ORDER.some(function (scope) {
        return getVehiclesForScope(scope).some(function (vehicle) {
          return getVehicleDetailsKey(scope, vehicle.id) === state.expandedVehicleKey;
        });
      });

      if (!hasVehicle) {
        state.expandedVehicleKey = null;
      }
    }
```
