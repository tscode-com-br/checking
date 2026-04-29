# resolveStoredLanguageCode

- Nome da funcao: `resolveStoredLanguageCode`
- Arquivo gerado: `resolveStoredLanguageCode.md`
- Origem: `sistema/app/static/transport/app.js:70`
- Escopo original: topo do modulo
- Tema funcional: codigo de idioma persistido
- Categoria: i18n
- Responsabilidade: Helper utilitario do dashboard de transporte que le, normaliza, formata ou resolve valores consumidos pelas etapas seguintes do fluxo.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: Retorna um valor derivado relacionado a codigo de idioma persistido, pronto para ser consumido pela chamada seguinte.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `globalScope`, `localStorage`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Interage com `localStorage` para persistencia local do navegador.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function resolveStoredLanguageCode() {
    if (!globalScope.localStorage) {
      return TRANSPORT_DEFAULT_LANGUAGE;
    }

    try {
      const storedValue = String(globalScope.localStorage.getItem(TRANSPORT_LANGUAGE_STORAGE_KEY) || "").trim();
      return transportLanguages.some(function (item) {
        return item.code === storedValue;
      }) ? storedValue : TRANSPORT_DEFAULT_LANGUAGE;
    } catch (error) {
      return TRANSPORT_DEFAULT_LANGUAGE;
    }
  }
```
