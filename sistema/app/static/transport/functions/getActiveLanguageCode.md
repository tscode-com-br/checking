# getActiveLanguageCode

- Nome da funcao: `getActiveLanguageCode`
- Arquivo gerado: `getActiveLanguageCode.md`
- Origem: `sistema/app/static/transport/app.js:105`
- Escopo original: topo do modulo
- Tema funcional: codigo de idioma ativo
- Categoria: i18n
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a codigo de idioma ativo, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `resolveLanguageCode`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getActiveLanguageCode() {
    return resolveLanguageCode(transportLanguageState.currentCode);
  }
```
