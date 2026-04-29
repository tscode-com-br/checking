# getPendingAssignmentPreview

- Nome da funcao: `getPendingAssignmentPreview`
- Arquivo gerado: `getPendingAssignmentPreview.md`
- Origem: `sistema/app/static/transport/app.js:2754`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: pending assignment previsualizacao
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getRequestById`, `getVehicleByScopeAndId`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getPendingAssignmentPreview() {
      if (!state.pendingAssignmentPreview) {
        return null;
      }

      const requestRow = getRequestById(state.pendingAssignmentPreview.requestId);
      const vehicle = getVehicleByScopeAndId(
        state.pendingAssignmentPreview.scope,
        state.pendingAssignmentPreview.vehicleId
      );

      if (!requestRow || !vehicle) {
        return null;
      }

      return {
        requestRow,
        vehicle,
        scope: state.pendingAssignmentPreview.scope,
        routeKind: state.pendingAssignmentPreview.routeKind,
      };
    }
```
