# isProjectVisible

- Nome da funcao: `isProjectVisible`
- Arquivo gerado: `isProjectVisible.md`
- Origem: `sistema/app/static/transport/app.js:2684`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: projeto visivel
- Categoria: state
- Responsabilidade: Predicate do controller da pagina que inspeciona os dados disponiveis e devolve a decisao booleana usada para permitir, negar ou destacar um comportamento.
- Entradas: Recebe `projectName` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor booleano usado para gating de UI, validacao ou destaque de estado.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function isProjectVisible(projectName) {
      const normalizedProjectName = String(projectName || "").trim();
      if (!normalizedProjectName) {
        return true;
      }
      if (!(normalizedProjectName in state.projectVisibility)) {
        return true;
      }
      return state.projectVisibility[normalizedProjectName] !== false;
    }
```
