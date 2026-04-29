# getProjectRows

- Nome da funcao: `getProjectRows`
- Arquivo gerado: `getProjectRows.md`
- Origem: `sistema/app/static/transport/app.js:2656`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: projeto linhas
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a projeto linhas, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getProjectRows() {
      if (!state.dashboard) {
        return [];
      }
      return Array.isArray(state.dashboard.projects) ? state.dashboard.projects : [];
    }
```
