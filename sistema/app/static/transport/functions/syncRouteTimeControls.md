# syncRouteTimeControls

- Nome da funcao: `syncRouteTimeControls`
- Arquivo gerado: `syncRouteTimeControls.md`
- Origem: `sistema/app/static/transport/app.js:1812`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: rota horario controles
- Categoria: state + date/time
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `formatTransportDate`, `getEffectiveWorkToHomeDepartureTime`, `getValue`, `t`, `dateStore`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function syncRouteTimeControls() {
      const canEditRouteTime = state.isAuthenticated;
      const shouldShowRouteTime = state.isAuthenticated;
      const effectiveDepartureTime = getEffectiveWorkToHomeDepartureTime(state.dashboard, state.workToHomeTime);

      if (routeTimeInput) {
        routeTimeInput.value = effectiveDepartureTime;
        routeTimeInput.disabled = !canEditRouteTime || state.routeTimeSaving || state.isLoading;
        routeTimeInput.setAttribute(
          "aria-label",
          `${t("settings.workToHomeTime")} ${formatTransportDate(dateStore.getValue())}`.trim()
        );
        routeTimeInput.title = effectiveDepartureTime;
      }

      if (routeTimePopover) {
        routeTimePopover.hidden = !shouldShowRouteTime;
      }
    }
```
