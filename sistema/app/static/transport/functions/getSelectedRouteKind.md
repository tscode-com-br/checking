# getSelectedRouteKind

- Nome da funcao: `getSelectedRouteKind`
- Arquivo gerado: `getSelectedRouteKind.md`
- Origem: `sistema/app/static/transport/app.js:2521`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: selecionado tipo de rota
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a selecionado tipo de rota, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getSelectedRouteKind() {
      return state.selectedRouteKind || "home_to_work";
    }
```
