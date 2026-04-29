# stopResize

- Nome da funcao: `stopResize`
- Arquivo gerado: `stopResize.md`
- Origem: `sistema/app/static/transport/app.js:573`
- Escopo original: interna de `enableResizableDivider`
- Tema funcional: redimensionamento
- Categoria: UI
- Responsabilidade: Orquestra um fluxo operacional do controller da pagina, ligando validacao local, integracao externa, feedback visual e recarga de dados quando necessario.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `document`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function stopResize() {
        globalScope.removeEventListener("pointermove", applyResize);
        globalScope.removeEventListener("pointerup", stopResize);
        globalScope.removeEventListener("pointercancel", stopResize);
        document.body.classList.remove("transport-is-resizing");
      }
```
