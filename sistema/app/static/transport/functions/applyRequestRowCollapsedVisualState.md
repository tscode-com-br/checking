# applyRequestRowCollapsedVisualState

- Nome da funcao: `applyRequestRowCollapsedVisualState`
- Arquivo gerado: `applyRequestRowCollapsedVisualState.md`
- Origem: `sistema/app/static/transport/app.js:1690`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: linha de solicitacao collapsed visual state
- Categoria: UI + state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `rowButton`, `collapsed` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: Nenhuma dependencia nomeada relevante foi detectada alem de primitivas da linguagem.
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function applyRequestRowCollapsedVisualState(rowButton, collapsed) {
      if (!rowButton) {
        return;
      }

      const rowShell = rowButton.parentElement;
      rowButton.classList.toggle("is-collapsed", Boolean(collapsed));
      rowButton.setAttribute("aria-expanded", String(!collapsed));
      if (rowShell) {
        rowShell.classList.toggle("is-collapsed", Boolean(collapsed));
      }
    }
```
