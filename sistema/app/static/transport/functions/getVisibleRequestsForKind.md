# getVisibleRequestsForKind

- Nome da funcao: `getVisibleRequestsForKind`
- Arquivo gerado: `getVisibleRequestsForKind.md`
- Origem: `sistema/app/static/transport/app.js:2695`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: visivel solicitacoes para tipo
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `kind` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a visivel solicitacoes para tipo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getRequestsForKind`, `isProjectVisible`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getVisibleRequestsForKind(kind) {
      return getRequestsForKind(kind).filter(function (requestRow) {
        return isProjectVisible(requestRow.projeto);
      });
    }
```
