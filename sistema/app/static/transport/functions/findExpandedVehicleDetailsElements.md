# findExpandedVehicleDetailsElements

- Nome da funcao: `findExpandedVehicleDetailsElements`
- Arquivo gerado: `findExpandedVehicleDetailsElements.md`
- Origem: `sistema/app/static/transport/app.js:2848`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: expandido detalhes do veiculo elements
- Categoria: UI + state
- Responsabilidade: Encapsula uma responsabilidade interna do controller da pagina, preservando detalhes de implementacao perto do ponto em que sao usados.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `document`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function findExpandedVehicleDetailsElements() {
      if (!state.expandedVehicleKey) {
        return null;
      }

      const anchorButton = document.querySelector(
        `[data-vehicle-details-anchor-key="${state.expandedVehicleKey}"]`
      );
      const detailsPanel = vehicleDetailsOverlayHost.querySelector(
        `[data-vehicle-details-panel-key="${state.expandedVehicleKey}"]`
      );

      if (!anchorButton || !detailsPanel) {
        return null;
      }

      return {
        anchorButton,
        detailsPanel,
      };
    }
```
