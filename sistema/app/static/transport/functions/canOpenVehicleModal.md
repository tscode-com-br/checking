# canOpenVehicleModal

- Nome da funcao: `canOpenVehicleModal`
- Arquivo gerado: `canOpenVehicleModal.md`
- Origem: `sistema/app/static/transport/app.js:2548`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: open veiculo modal
- Categoria: state
- Responsabilidade: Predicate do controller da pagina que inspeciona os dados disponiveis e devolve a decisao booleana usada para permitir, negar ou destacar um comportamento.
- Entradas: Recebe `scope` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor booleano usado para gating de UI, validacao ou destaque de estado.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getTransportLockedMessage`, `setStatus`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function canOpenVehicleModal(scope) {
      if (!state.isAuthenticated) {
        setStatus(getTransportLockedMessage(), "warning");
        return false;
      }
      return true;
    }
```
