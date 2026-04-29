# groupAssignedRequestsByVehicle

- Nome da funcao: `groupAssignedRequestsByVehicle`
- Arquivo gerado: `groupAssignedRequestsByVehicle.md`
- Origem: `sistema/app/static/transport/app.js:3222`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: alocada solicitacoes by veiculo
- Categoria: state + date/time
- Responsabilidade: Organiza colecoes do controller da pagina em uma estrutura intermediaria pronta para renderizacao, filtro ou tomada de decisao.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getRequestsForKind`, `groupAssignedRequestsByVehicleForDate`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function groupAssignedRequestsByVehicle(scope) {
      return groupAssignedRequestsByVehicleForDate(
        getRequestsForKind(scope),
        state.dashboard ? state.dashboard.selected_date : ""
      );
    }
```
