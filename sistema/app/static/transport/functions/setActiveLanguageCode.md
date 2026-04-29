# setActiveLanguageCode

- Nome da funcao: `setActiveLanguageCode`
- Arquivo gerado: `setActiveLanguageCode.md`
- Origem: `sistema/app/static/transport/app.js:109`
- Escopo original: topo do modulo
- Tema funcional: codigo de idioma ativo
- Categoria: i18n
- Responsabilidade: Rotina de sincronizacao do dashboard de transporte que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `languageCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `resolveLanguageCode`, `setStoredLanguageCode`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function setActiveLanguageCode(languageCode) {
    const resolvedCode = resolveLanguageCode(languageCode);
    transportLanguageState.currentCode = resolvedCode;
    setStoredLanguageCode(resolvedCode);
    return resolvedCode;
  }
```
