# setDashboardDateForSilentReload

- Nome da funcao: `setDashboardDateForSilentReload`
- Arquivo gerado: `setDashboardDateForSilentReload.md`
- Origem: `sistema/app/static/transport/app.js:1337`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: dashboard data para silent reload
- Categoria: state + date/time
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Recebe `nextDate` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `closeRouteTimePopover`, `refreshDatePanelLabels`, `setStoredTransportDate`, `setValue`, `dateStore`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Nenhum efeito colateral relevante; a funcao atua como utilitario de calculo, leitura ou transformacao.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function setDashboardDateForSilentReload(nextDate) {
      const selectedDate = dateStore.setValue(nextDate, { notify: false });
      setStoredTransportDate(selectedDate);
      refreshDatePanelLabels();
      closeRouteTimePopover();
      return selectedDate;
    }
```
