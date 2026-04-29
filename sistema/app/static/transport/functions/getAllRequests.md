# getAllRequests

- Nome da funcao: `getAllRequests`
- Arquivo gerado: `getAllRequests.md`
- Origem: `sistema/app/static/transport/app.js:2719`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: todas solicitacoes
- Categoria: state
- Responsabilidade: Helper utilitario do controller da pagina que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a todas solicitacoes, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getRequestsForKind`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getAllRequests() {
      return REQUEST_SECTION_ORDER.reduce(function (rows, kind) {
        return rows.concat(getRequestsForKind(kind));
      }, []);
    }
```
