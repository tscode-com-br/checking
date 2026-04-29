# syncSettingsControls

- Nome da funcao: `syncSettingsControls`
- Arquivo gerado: `syncSettingsControls.md`
- Origem: `sistema/app/static/transport/app.js:1773`
- Escopo original: interna de `createTransportPageController`
- Tema funcional: configuracoes controles
- Categoria: state
- Responsabilidade: Rotina de sincronizacao do controller da pagina que ajusta estado local, DOM e referencias auxiliares para manter a interface coerente.
- Entradas: Nao recebe parametros explicitos; opera sobre fechamento, estado local, seletores DOM ou constantes definidas no modulo.
- Saidas: O retorno nao e o foco principal; a utilidade real da rotina esta nos efeitos sobre estado, DOM ou ciclo de vida.
- Funcoes nomeadas internas: Nenhuma funcao nomeada interna registrada.
- Dependencias observadas: `state`, `getActiveLanguageCode`, `getDefaultVehicleSeatCount`, `getDefaultVehicleToleranceMinutes`, `normalizeTransportTimeValue`
- Endpoints/rotas envolvidos: Nenhum endpoint direto; qualquer integracao externa ocorre por delegacao a outras funcoes.
- Efeitos colaterais:
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function syncSettingsControls() {
      if (settingsLanguageSelect) {
        settingsLanguageSelect.value = getActiveLanguageCode();
        settingsLanguageSelect.disabled = state.languageLoading;
      }
      if (settingsTimeInput) {
        settingsTimeInput.value = normalizeTransportTimeValue(state.workToHomeTime, DEFAULT_WORK_TO_HOME_TIME);
        settingsTimeInput.disabled = !state.isAuthenticated || state.settingsLoading || state.settingsSaving;
      }
      if (settingsLastUpdateInput) {
        settingsLastUpdateInput.value = normalizeTransportTimeValue(state.lastUpdateTime, DEFAULT_LAST_UPDATE_TIME);
        settingsLastUpdateInput.disabled = !state.isAuthenticated || state.settingsLoading || state.settingsSaving;
      }
      Object.keys(settingsDefaultSeatInputs).forEach(function (vehicleType) {
        const seatInput = settingsDefaultSeatInputs[vehicleType];
        if (!seatInput) {
          return;
        }
        seatInput.value = String(getDefaultVehicleSeatCount(vehicleType));
        seatInput.disabled = !state.isAuthenticated || state.settingsLoading || state.settingsSaving;
      });
      if (settingsDefaultToleranceInput) {
        settingsDefaultToleranceInput.value = String(getDefaultVehicleToleranceMinutes());
        settingsDefaultToleranceInput.disabled = !state.isAuthenticated || state.settingsLoading || state.settingsSaving;
      }
    }
```
