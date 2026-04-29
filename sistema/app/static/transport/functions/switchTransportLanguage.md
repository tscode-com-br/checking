# switchTransportLanguage

- Nome da funcao: `switchTransportLanguage`
- Arquivo gerado: `switchTransportLanguage.md`
- Origem: `sistema/app/static/transport/app.js:2197`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: transporte idioma
- Categoria: i18n + state
- Responsabilidade: Orquestra um fluxo operacional do controller da pagina, ligando validacao local, integracao externa, feedback visual e recarga de dados quando necessario.
- Entradas: Recebe `nextLanguageCode` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna uma `Promise`; em geral resolve com dados/resultado da operacao ou `null` quando o fluxo e encerrado de forma tratada.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `applyStaticTranslations`, `clearDashboard`, `getTransportLockedMessage`, `renderDashboard`, `resolveLanguageCode`, `setActiveLanguageCode`, `setStatus`, `syncRouteTimeControls`, `syncSettingsControls`, `t`, `globalScope`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Agenda ou cancela trabalho assincrono no navegador.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function switchTransportLanguage(nextLanguageCode) {
      const resolvedCode = resolveLanguageCode(nextLanguageCode);
      state.languageLoading = true;
      syncSettingsControls();
      setStatus(t("status.switchingLanguage"), "info");

      return new Promise(function (resolve) {
        const finishSwitch = function () {
          setActiveLanguageCode(resolvedCode);
          applyStaticTranslations();
          if (state.dashboard) {
            renderDashboard();
          } else {
            clearDashboard();
          }
          state.languageLoading = false;
          syncSettingsControls();
          syncRouteTimeControls();
          if (state.isAuthenticated) {
            setStatus(t("status.dashboardUpdated"), "info");
          } else {
            setStatus(getTransportLockedMessage(), "warning");
          }
          resolve();
        };

        if (typeof globalScope.requestAnimationFrame === "function") {
          globalScope.requestAnimationFrame(finishSwitch);
          return;
        }

        finishSwitch();
      });
    }
```
