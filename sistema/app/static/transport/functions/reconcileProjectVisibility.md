# reconcileProjectVisibility

- Nome da funcao: `reconcileProjectVisibility`
- Arquivo gerado: `reconcileProjectVisibility.md`
- Origem: `sistema/app/static/transport/app.js:2663`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: projeto visibility
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna o resultado imediato do fluxo encapsulado, conforme o caminho seguido pela implementacao.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getProjectRows`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function reconcileProjectVisibility() {
      const nextVisibility = {};
      getProjectRows().forEach(function (projectRow) {
        if (!projectRow || !projectRow.name) {
          return;
        }
        nextVisibility[projectRow.name] = state.projectVisibility[projectRow.name] !== false;
      });
      state.projectVisibility = nextVisibility;
    }
```
