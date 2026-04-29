# closeExpandedVehicleDetails

- Nome da funcao: `closeExpandedVehicleDetails`
- Arquivo gerado: `closeExpandedVehicleDetails.md`
- Origem: `sistema/app/static/transport/app.js:2813`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: expandido detalhes do veiculo
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `options` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `clearElement`, `findExpandedVehicleDetailsElements`, `renderVehiclePanels`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Agenda ou cancela trabalho assincrono no navegador.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function closeExpandedVehicleDetails(options) {
      const closeOptions = options || {};
      const expandedElements = closeOptions.restoreFocus ? findExpandedVehicleDetailsElements() : null;

      if (!state.expandedVehicleKey && !state.pendingAssignmentPreview) {
        clearElement(vehicleDetailsOverlayHost);
        vehicleDetailsOverlayHost.classList.remove("is-active");
        return;
      }

      state.expandedVehicleKey = null;
      state.pendingAssignmentPreview = null;
      clearElement(vehicleDetailsOverlayHost);
      vehicleDetailsOverlayHost.classList.remove("is-active");

      if (closeOptions.render !== false) {
        renderVehiclePanels();
      }

      if (
        closeOptions.restoreFocus
        && expandedElements
        && expandedElements.anchorButton
        && typeof expandedElements.anchorButton.focus === "function"
      ) {
        if (typeof globalScope.requestAnimationFrame === "function") {
          globalScope.requestAnimationFrame(function () {
            expandedElements.anchorButton.focus();
          });
        } else {
          expandedElements.anchorButton.focus();
        }
      }
    }
```
