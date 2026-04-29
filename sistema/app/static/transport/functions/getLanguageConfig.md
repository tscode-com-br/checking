# getLanguageConfig

- Nome da funcao: `getLanguageConfig`
- Arquivo gerado: `getLanguageConfig.md`
- Origem: `sistema/app/static/transport/app.js:116`
- Escopo original: topo do modulo
- Tema funcional: configuracao de idioma
- Categoria: i18n
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Recebe `languageCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um valor derivado relacionado a configuracao de idioma, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `resolveLanguageCode`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function getLanguageConfig(languageCode) {
    const resolvedCode = resolveLanguageCode(languageCode);
    const matchedLanguage = transportLanguages.find(function (item) {
      return item.code === resolvedCode;
    });
    return matchedLanguage || transportLanguages[0];
  }
```
