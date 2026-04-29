# toggleVehicleDetails

- Nome da funcao: `toggleVehicleDetails`
- Arquivo gerado: `toggleVehicleDetails.md`
- Origem: `sistema/app/static/transport/app.js:2797`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: detalhes do veiculo
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `scope`, `vehicleId` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getPendingAssignmentPreview`, `getVehicleDetailsKey`, `renderVehiclePanels`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function toggleVehicleDetails(scope, vehicleId) {
      const vehicleKey = getVehicleDetailsKey(scope, vehicleId);
      const pendingPreview = getPendingAssignmentPreview();
      if (
        pendingPreview
        && pendingPreview.scope === scope
        && Number(pendingPreview.vehicle.id) === Number(vehicleId)
      ) {
        state.expandedVehicleKey = vehicleKey;
        renderVehiclePanels();
        return;
      }
      state.expandedVehicleKey = state.expandedVehicleKey === vehicleKey ? null : vehicleKey;
      renderVehiclePanels();
    }
```
