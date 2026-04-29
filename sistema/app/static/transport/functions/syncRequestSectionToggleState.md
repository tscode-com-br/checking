# syncRequestSectionToggleState

- Nome da funcao: `syncRequestSectionToggleState`
- Arquivo gerado: `syncRequestSectionToggleState.md`
- Origem: `sistema/app/static/transport/app.js:1737`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: solicitacao secao alternancia state
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `getRequestSectionCollapsedState`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function syncRequestSectionToggleState() {
      Object.keys(requestSectionToggleLinks).forEach(function (kind) {
        const toggleLink = requestSectionToggleLinks[kind];
        if (!toggleLink) {
          return;
        }

        const isExpanded = !getRequestSectionCollapsedState(kind);
        toggleLink.setAttribute("aria-expanded", String(isExpanded));
        toggleLink.classList.toggle("is-collapsed", !isExpanded);
      });
    }
```
