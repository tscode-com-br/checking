# syncVehicleViewToggleState

- Nome da funcao: `syncVehicleViewToggleState`
- Arquivo gerado: `syncVehicleViewToggleState.md`
- Origem: `sistema/app/static/transport/app.js:1893`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: veiculo visualizacao alternancia state
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getVehicleViewMode`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function syncVehicleViewToggleState() {
      VEHICLE_SCOPE_ORDER.forEach(function (scope) {
        const toggleLink = vehicleViewToggleLinks[scope];
        const isTableView = getVehicleViewMode(scope) === "table";
        if (!toggleLink) {
          return;
        }

        toggleLink.classList.toggle("is-management-open", isTableView);
        toggleLink.setAttribute("aria-expanded", String(isTableView));
      });
    }
```
