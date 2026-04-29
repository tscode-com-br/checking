# syncVehicleModalFields

- Nome da funcao: `syncVehicleModalFields`
- Arquivo gerado: `syncVehicleModalFields.md`
- Origem: `sistema/app/static/transport/app.js:2556`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo modal fields
- Categoria: UI + state + date/time
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getModalScopeNote`, `getSelectedRouteKind`, `mapScopeTitle`, `normalizeVehicleScope`, `vehicleForm`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function syncVehicleModalFields(scope) {
      if (!vehicleForm) {
        return;
      }

      const normalizedScope = normalizeVehicleScope(scope);

      if (modalScopeLabel) {
        modalScopeLabel.textContent = mapScopeTitle(normalizedScope);
      }
      if (modalScopeNote) {
        modalScopeNote.textContent = getModalScopeNote(normalizedScope);
      }
      if (extraServiceDateField) {
        extraServiceDateField.hidden = normalizedScope !== "extra";
      }
      if (extraDepartureField) {
        extraDepartureField.hidden = normalizedScope !== "extra";
      }
      if (extraRouteField) {
        extraRouteField.hidden = normalizedScope !== "extra";
      }
      weekendPersistenceFields.forEach(function (fieldElement) {
        fieldElement.hidden = normalizedScope !== "weekend";
      });
      regularPersistenceFields.forEach(function (fieldElement) {
        fieldElement.hidden = normalizedScope !== "regular";
      });
      if (vehicleForm.elements.route_kind) {
        vehicleForm.elements.route_kind.value = getSelectedRouteKind();
        vehicleForm.elements.route_kind.disabled = normalizedScope !== "extra";
      }
      if (vehicleForm.elements.service_date) {
        vehicleForm.elements.service_date.required = normalizedScope === "extra";
        vehicleForm.elements.service_date.disabled = normalizedScope !== "extra";
      }
      if (vehicleForm.elements.service_date && normalizedScope !== "extra") {
        vehicleForm.elements.service_date.value = "";
      }
      if (vehicleForm.elements.departure_time) {
        vehicleForm.elements.departure_time.required = normalizedScope === "extra";
        vehicleForm.elements.departure_time.disabled = normalizedScope !== "extra";
      }
      if (vehicleForm.elements.departure_time && normalizedScope !== "extra") {
        vehicleForm.elements.departure_time.value = "";
      }
      if (vehicleForm.elements.every_saturday) {
        vehicleForm.elements.every_saturday.checked = false;
      }
      if (vehicleForm.elements.every_sunday) {
        vehicleForm.elements.every_sunday.checked = false;
      }
    }
```
