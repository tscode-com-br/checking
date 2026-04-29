# getDictionaryForLanguage

- Nome da funcao: `getDictionaryForLanguage`
- Arquivo gerado: `getDictionaryForLanguage.md`
- Origem: `sistema/app/static/transport/app.js:58`
- Escopo original: topo do modulo
- Tema funcional: dicionario do idioma
- Categoria: i18n
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `languageCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a dicionario do idioma, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getDictionary`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getDictionaryForLanguage(languageCode) {
    if (transportI18n && typeof transportI18n.getDictionary === "function") {
      return transportI18n.getDictionary(languageCode);
    }

    if (transportI18n && transportI18n.dictionaries && transportI18n.dictionaries[languageCode]) {
      return transportI18n.dictionaries[languageCode];
    }

    return (transportI18n && transportI18n.dictionaries && transportI18n.dictionaries[TRANSPORT_DEFAULT_LANGUAGE]) || {};
  }
```
