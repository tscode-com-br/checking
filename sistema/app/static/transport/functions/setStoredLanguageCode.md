# setStoredLanguageCode

- Nome da funcao: `setStoredLanguageCode`
- Arquivo gerado: `setStoredLanguageCode.md`
- Origem: `sistema/app/static/transport/app.js:89`
- Escopo original: topo do modulo
- Tema funcional: codigo de idioma persistido
- Categoria: i18n
- Responsabilidade: Rotina de sincronizacao do dashboard de transporte que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `languageCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `globalScope`, `localStorage`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Interage com `localStorage` para persistencia local do navegador.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function setStoredLanguageCode(languageCode) {
    if (!globalScope.localStorage) {
      return;
    }

    try {
      globalScope.localStorage.setItem(TRANSPORT_LANGUAGE_STORAGE_KEY, languageCode);
    } catch (error) {}
  }
```
