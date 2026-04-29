# Transport Dashboard Functions By Capability

Indice operacional para navegar pelas 192 funcoes nomeadas do dashboard por capacidade funcional, em vez de por ordem de aparicao no codigo.

Resumo:
- Total de funcoes agrupadas: 192
- Total de capacidades: 11
- Cada funcao aparece uma unica vez, no grupo de melhor encaixe operacional.
- O indice canonical por ordem/origem continua sendo `functions.md`.

## 1. Autenticacao e acesso (12)

Login, sessao, permissao de uso do dashboard e sincronizacao da casca autenticada.

- [bootstrapTransportSession.md](bootstrapTransportSession.md): `bootstrapTransportSession` | categoria `API + state + date/time` | tema `transporte sessao` | origem `sistema/app/static/transport/app.js:2289`
- [clearPendingAuthVerification.md](clearPendingAuthVerification.md): `clearPendingAuthVerification` | categoria `state` | tema `pending autenticacao verificacao` | origem `sistema/app/static/transport/app.js:1943`
- [clearTransportSession.md](clearTransportSession.md): `clearTransportSession` | categoria `API + state` | tema `transporte sessao` | origem `sistema/app/static/transport/app.js:2035`
- [getTransportLockedMessage.md](getTransportLockedMessage.md): `getTransportLockedMessage` | categoria `utility` | tema `transporte bloqueio mensagem` | origem `sistema/app/static/transport/app.js:156`
- [getTransportSessionExpiredMessage.md](getTransportSessionExpiredMessage.md): `getTransportSessionExpiredMessage` | categoria `utility` | tema `transporte sessao expirada mensagem` | origem `sistema/app/static/transport/app.js:160`
- [normalizeAuthKeyValue.md](normalizeAuthKeyValue.md): `normalizeAuthKeyValue` | categoria `state` | tema `autenticacao chave valor` | origem `sistema/app/static/transport/app.js:1929`
- [openUserCreationRequest.md](openUserCreationRequest.md): `openUserCreationRequest` | categoria `state` | tema `usuario criacao solicitacao` | origem `sistema/app/static/transport/app.js:2055`
- [scheduleTransportVerification.md](scheduleTransportVerification.md): `scheduleTransportVerification` | categoria `state` | tema `transporte verificacao` | origem `sistema/app/static/transport/app.js:2270`
- [setAuthenticationState.md](setAuthenticationState.md): `setAuthenticationState` | categoria `state` | tema `authentication state` | origem `sistema/app/static/transport/app.js:1998`
- [setAuthShellState.md](setAuthShellState.md): `setAuthShellState` | categoria `UI + state` | tema `autenticacao shell state` | origem `sistema/app/static/transport/app.js:1911`
- [updateAuthControls.md](updateAuthControls.md): `updateAuthControls` | categoria `state` | tema `autenticacao controles` | origem `sistema/app/static/transport/app.js:1919`
- [verifyTransportCredentials.md](verifyTransportCredentials.md): `verifyTransportCredentials` | categoria `API + state + date/time` | tema `transporte credenciais` | origem `sistema/app/static/transport/app.js:2232`

## 2. Dashboard e tempo real (9)

Carga principal do dashboard, bootstrap da pagina, refresh incremental e stream SSE.

- [clearDashboard.md](clearDashboard.md): `clearDashboard` | categoria `UI + state` | tema `dashboard` | origem `sistema/app/static/transport/app.js:3571`
- [clearPendingRealtimeRefresh.md](clearPendingRealtimeRefresh.md): `clearPendingRealtimeRefresh` | categoria `state` | tema `pending tempo real atualizacao` | origem `sistema/app/static/transport/app.js:1950`
- [createTransportPageController.md](createTransportPageController.md): `createTransportPageController` | categoria `API + UI + state + date/time` | tema `transporte pagina controller` | origem `sistema/app/static/transport/app.js:1164`
- [initTransportPage.md](initTransportPage.md): `initTransportPage` | categoria `UI + date/time` | tema `transporte pagina` | origem `sistema/app/static/transport/app.js:3659`
- [loadDashboard.md](loadDashboard.md): `loadDashboard` | categoria `API + state + date/time` | tema `dashboard` | origem `sistema/app/static/transport/app.js:3600`
- [renderDashboard.md](renderDashboard.md): `renderDashboard` | categoria `state` | tema `dashboard` | origem `sistema/app/static/transport/app.js:3563`
- [requestDashboardRefresh.md](requestDashboardRefresh.md): `requestDashboardRefresh` | categoria `state + date/time` | tema `dashboard atualizacao` | origem `sistema/app/static/transport/app.js:1966`
- [startRealtimeUpdates.md](startRealtimeUpdates.md): `startRealtimeUpdates` | categoria `API + state` | tema `tempo real updates` | origem `sistema/app/static/transport/app.js:1979`
- [stopRealtimeUpdates.md](stopRealtimeUpdates.md): `stopRealtimeUpdates` | categoria `state` | tema `tempo real updates` | origem `sistema/app/static/transport/app.js:1957`

## 3. Configuracoes e preferencias (17)

Preferencias persistidas, horario base e defaults usados pela operacao.

- [applyTransportVehicleSeatDefaults.md](applyTransportVehicleSeatDefaults.md): `applyTransportVehicleSeatDefaults` | categoria `utility` | tema `transporte veiculo assento defaults` | origem `sistema/app/static/transport/app.js:770`
- [applyTransportVehicleToleranceDefault.md](applyTransportVehicleToleranceDefault.md): `applyTransportVehicleToleranceDefault` | categoria `utility` | tema `transporte veiculo tolerancia padrao` | origem `sistema/app/static/transport/app.js:783`
- [applyVehicleFormDefaults.md](applyVehicleFormDefaults.md): `applyVehicleFormDefaults` | categoria `utility` | tema `veiculo formulario defaults` | origem `sistema/app/static/transport/app.js:862`
- [applyVehicleSeatDefault.md](applyVehicleSeatDefault.md): `applyVehicleSeatDefault` | categoria `utility` | tema `veiculo assento padrao` | origem `sistema/app/static/transport/app.js:833`
- [closeSettingsModal.md](closeSettingsModal.md): `closeSettingsModal` | categoria `state` | tema `configuracoes modal` | origem `sistema/app/static/transport/app.js:2506`
- [getDefaultStatusMessage.md](getDefaultStatusMessage.md): `getDefaultStatusMessage` | categoria `utility` | tema `padrao mensagem de status` | origem `sistema/app/static/transport/app.js:164`
- [getDefaultVehicleFormValues.md](getDefaultVehicleFormValues.md): `getDefaultVehicleFormValues` | categoria `utility` | tema `padrao veiculo formulario valores` | origem `sistema/app/static/transport/app.js:796`
- [getDefaultVehicleSeatCount.md](getDefaultVehicleSeatCount.md): `getDefaultVehicleSeatCount` | categoria `utility` | tema `padrao veiculo assento quantidade` | origem `sistema/app/static/transport/app.js:788`
- [getDefaultVehicleToleranceMinutes.md](getDefaultVehicleToleranceMinutes.md): `getDefaultVehicleToleranceMinutes` | categoria `utility` | tema `padrao veiculo tolerancia minutes` | origem `sistema/app/static/transport/app.js:792`
- [loadTransportSettings.md](loadTransportSettings.md): `loadTransportSettings` | categoria `API + state` | tema `transporte configuracoes` | origem `sistema/app/static/transport/app.js:2062`
- [normalizeVehicleToleranceSetting.md](normalizeVehicleToleranceSetting.md): `normalizeVehicleToleranceSetting` | categoria `utility` | tema `veiculo tolerancia setting` | origem `sistema/app/static/transport/app.js:775`
- [openSettingsModal.md](openSettingsModal.md): `openSettingsModal` | categoria `state` | tema `configuracoes modal` | origem `sistema/app/static/transport/app.js:2491`
- [readTransportSettingsDraft.md](readTransportSettingsDraft.md): `readTransportSettingsDraft` | categoria `state` | tema `transporte configuracoes rascunho` | origem `sistema/app/static/transport/app.js:1800`
- [resolveTransportVehicleSeatDefaults.md](resolveTransportVehicleSeatDefaults.md): `resolveTransportVehicleSeatDefaults` | categoria `utility` | tema `transporte veiculo assento defaults` | origem `sistema/app/static/transport/app.js:748`
- [saveTransportSettings.md](saveTransportSettings.md): `saveTransportSettings` | categoria `API + state + date/time` | tema `transporte configuracoes` | origem `sistema/app/static/transport/app.js:2106`
- [syncSettingsControls.md](syncSettingsControls.md): `syncSettingsControls` | categoria `state` | tema `configuracoes controles` | origem `sistema/app/static/transport/app.js:1773`
- [syncVehicleTypeDependentDefaults.md](syncVehicleTypeDependentDefaults.md): `syncVehicleTypeDependentDefaults` | categoria `utility` | tema `veiculo type dependent defaults` | origem `sistema/app/static/transport/app.js:841`

## 4. Idioma e i18n (15)

Dicionarios, traducao e troca do idioma ativo.

- [applyStaticTranslations.md](applyStaticTranslations.md): `applyStaticTranslations` | categoria `i18n + UI + state + date/time` | tema `estatica translations` | origem `sistema/app/static/transport/app.js:1359`
- [getActiveLanguageCode.md](getActiveLanguageCode.md): `getActiveLanguageCode` | categoria `i18n` | tema `codigo de idioma ativo` | origem `sistema/app/static/transport/app.js:105`
- [getDictionary.md](getDictionary.md): `getDictionary` | categoria `i18n` | tema `dicionario` | origem `sistema/app/static/transport/i18n.js:971`
- [getDictionaryForLanguage.md](getDictionaryForLanguage.md): `getDictionaryForLanguage` | categoria `i18n` | tema `dicionario do idioma` | origem `sistema/app/static/transport/app.js:58`
- [getLanguage.md](getLanguage.md): `getLanguage` | categoria `i18n` | tema `idioma` | origem `sistema/app/static/transport/i18n.js:975`
- [getLanguageConfig.md](getLanguageConfig.md): `getLanguageConfig` | categoria `i18n` | tema `configuracao de idioma` | origem `sistema/app/static/transport/app.js:116`
- [interpolateTranslation.md](interpolateTranslation.md): `interpolateTranslation` | categoria `i18n` | tema `traducao` | origem `sistema/app/static/transport/app.js:135`
- [populateLanguageOptions.md](populateLanguageOptions.md): `populateLanguageOptions` | categoria `i18n + UI + state` | tema `idioma options` | origem `sistema/app/static/transport/app.js:1759`
- [readTranslationValue.md](readTranslationValue.md): `readTranslationValue` | categoria `i18n` | tema `traducao valor` | origem `sistema/app/static/transport/app.js:124`
- [resolveLanguageCode.md](resolveLanguageCode.md): `resolveLanguageCode` | categoria `i18n` | tema `codigo de idioma` | origem `sistema/app/static/transport/app.js:99`
- [resolveStoredLanguageCode.md](resolveStoredLanguageCode.md): `resolveStoredLanguageCode` | categoria `i18n` | tema `codigo de idioma persistido` | origem `sistema/app/static/transport/app.js:70`
- [setActiveLanguageCode.md](setActiveLanguageCode.md): `setActiveLanguageCode` | categoria `i18n` | tema `codigo de idioma ativo` | origem `sistema/app/static/transport/app.js:109`
- [setStoredLanguageCode.md](setStoredLanguageCode.md): `setStoredLanguageCode` | categoria `i18n` | tema `codigo de idioma persistido` | origem `sistema/app/static/transport/app.js:89`
- [switchTransportLanguage.md](switchTransportLanguage.md): `switchTransportLanguage` | categoria `i18n + state` | tema `transporte idioma` | origem `sistema/app/static/transport/app.js:2197`
- [t.md](t.md): `t` | categoria `utility` | tema `t` | origem `sistema/app/static/transport/app.js:148`

## 5. Datas e tempo (43)

Store de data selecionada, formatacao e regras temporais locais.

- [buildVehicleCreatePayload.md](buildVehicleCreatePayload.md): `buildVehicleCreatePayload` | categoria `date/time` | tema `veiculo create payload` | origem `sistema/app/static/transport/app.js:881`
- [closeRouteTimePopover.md](closeRouteTimePopover.md): `closeRouteTimePopover` | categoria `state` | tema `rota horario popover` | origem `sistema/app/static/transport/app.js:1832`
- [createDatePanelController.md](createDatePanelController.md): `createDatePanelController` | categoria `UI + date/time` | tema `data painel controller` | origem `sistema/app/static/transport/app.js:589`
- [createRequestMetaLine.md](createRequestMetaLine.md): `createRequestMetaLine` | categoria `state + date/time` | tema `solicitacao meta line` | origem `sistema/app/static/transport/app.js:3087`
- [createTransportDateStore.md](createTransportDateStore.md): `createTransportDateStore` | categoria `date/time` | tema `transporte data store` | origem `sistema/app/static/transport/app.js:275`
- [createVehicleDetailsPanel.md](createVehicleDetailsPanel.md): `createVehicleDetailsPanel` | categoria `UI + state + date/time` | tema `detalhes do veiculo painel` | origem `sistema/app/static/transport/app.js:2951`
- [createVehicleManagementTable.md](createVehicleManagementTable.md): `createVehicleManagementTable` | categoria `UI + state + date/time` | tema `veiculo gerenciamento table` | origem `sistema/app/static/transport/app.js:3446`
- [formatIsoDate.md](formatIsoDate.md): `formatIsoDate` | categoria `date/time` | tema `ISO data` | origem `sistema/app/static/transport/app.js:215`
- [formatTransportDate.md](formatTransportDate.md): `formatTransportDate` | categoria `date/time` | tema `transporte data` | origem `sistema/app/static/transport/app.js:192`
- [getCurrentServiceDateIso.md](getCurrentServiceDateIso.md): `getCurrentServiceDateIso` | categoria `state + date/time` | tema `atual servico data ISO` | origem `sistema/app/static/transport/app.js:2544`
- [getEffectiveWorkToHomeDepartureTime.md](getEffectiveWorkToHomeDepartureTime.md): `getEffectiveWorkToHomeDepartureTime` | categoria `utility` | tema `efetivo rota trabalho para casa saida horario` | origem `sistema/app/static/transport/app.js:1019`
- [getTransportDateState.md](getTransportDateState.md): `getTransportDateState` | categoria `date/time` | tema `transporte data state` | origem `sistema/app/static/transport/app.js:259`
- [getValue.md](getValue.md): `getValue` | categoria `date/time` | tema `valor` | origem `sistema/app/static/transport/app.js:279`
- [getVehicleDepartureTime.md](getVehicleDepartureTime.md): `getVehicleDepartureTime` | categoria `utility` | tema `veiculo saida horario` | origem `sistema/app/static/transport/app.js:1028`
- [groupAssignedRequestsByVehicle.md](groupAssignedRequestsByVehicle.md): `groupAssignedRequestsByVehicle` | categoria `state + date/time` | tema `alocada solicitacoes by veiculo` | origem `sistema/app/static/transport/app.js:3222`
- [groupAssignedRequestsByVehicleForDate.md](groupAssignedRequestsByVehicleForDate.md): `groupAssignedRequestsByVehicleForDate` | categoria `date/time` | tema `alocada solicitacoes by veiculo para data` | origem `sistema/app/static/transport/app.js:1059`
- [isValidTransportTimeValue.md](isValidTransportTimeValue.md): `isValidTransportTimeValue` | categoria `utility` | tema `valid transporte horario valor` | origem `sistema/app/static/transport/app.js:1011`
- [isWeekendDate.md](isWeekendDate.md): `isWeekendDate` | categoria `utility` | tema `fim de semana data` | origem `sistema/app/static/transport/app.js:270`
- [normalizeTransportTimeValue.md](normalizeTransportTimeValue.md): `normalizeTransportTimeValue` | categoria `utility` | tema `transporte horario valor` | origem `sistema/app/static/transport/app.js:1015`
- [openVehicleModal.md](openVehicleModal.md): `openVehicleModal` | categoria `state + date/time` | tema `veiculo modal` | origem `sistema/app/static/transport/app.js:2610`
- [parseStoredTransportDate.md](parseStoredTransportDate.md): `parseStoredTransportDate` | categoria `date/time` | tema `persistido transporte data` | origem `sistema/app/static/transport/app.js:220`
- [refreshDatePanelLabels.md](refreshDatePanelLabels.md): `refreshDatePanelLabels` | categoria `UI + state + date/time` | tema `data painel labels` | origem `sistema/app/static/transport/app.js:1329`
- [rejectRequestRow.md](rejectRequestRow.md): `rejectRequestRow` | categoria `API + state + date/time` | tema `linha de solicitacao` | origem `sistema/app/static/transport/app.js:3244`
- [removeVehicleFromRoute.md](removeVehicleFromRoute.md): `removeVehicleFromRoute` | categoria `API + state + date/time` | tema `veiculo from rota` | origem `sistema/app/static/transport/app.js:3290`
- [render.md](render.md): `render` | categoria `UI + date/time` | tema `render` | origem `sistema/app/static/transport/app.js:595`
- [renderRequestTables.md](renderRequestTables.md): `renderRequestTables` | categoria `UI + state + date/time` | tema `solicitacao tables` | origem `sistema/app/static/transport/app.js:3117`
- [resolveStoredTransportDate.md](resolveStoredTransportDate.md): `resolveStoredTransportDate` | categoria `date/time` | tema `persistido transporte data` | origem `sistema/app/static/transport/app.js:243`
- [resolveVehicleCreateValidationError.md](resolveVehicleCreateValidationError.md): `resolveVehicleCreateValidationError` | categoria `date/time` | tema `veiculo create validacao erro` | origem `sistema/app/static/transport/app.js:925`
- [resolveVehicleModalOpenState.md](resolveVehicleModalOpenState.md): `resolveVehicleModalOpenState` | categoria `date/time` | tema `veiculo modal open state` | origem `sistema/app/static/transport/app.js:915`
- [resolveVehicleSaveReloadDate.md](resolveVehicleSaveReloadDate.md): `resolveVehicleSaveReloadDate` | categoria `date/time` | tema `veiculo save reload data` | origem `sistema/app/static/transport/app.js:968`
- [returnRequestRowToPending.md](returnRequestRowToPending.md): `returnRequestRowToPending` | categoria `state + date/time` | tema `linha de solicitacao para pending` | origem `sistema/app/static/transport/app.js:3268`
- [saveRouteTimeForSelectedDate.md](saveRouteTimeForSelectedDate.md): `saveRouteTimeForSelectedDate` | categoria `API + state + date/time` | tema `rota horario para selecionado data` | origem `sistema/app/static/transport/app.js:1836`
- [setDashboardDateForSilentReload.md](setDashboardDateForSilentReload.md): `setDashboardDateForSilentReload` | categoria `state + date/time` | tema `dashboard data para silent reload` | origem `sistema/app/static/transport/app.js:1337`
- [setStoredTransportDate.md](setStoredTransportDate.md): `setStoredTransportDate` | categoria `utility` | tema `persistido transporte data` | origem `sistema/app/static/transport/app.js:247`
- [setValue.md](setValue.md): `setValue` | categoria `date/time` | tema `valor` | origem `sistema/app/static/transport/app.js:290`
- [shiftLocalDay.md](shiftLocalDay.md): `shiftLocalDay` | categoria `date/time` | tema `local dia` | origem `sistema/app/static/transport/app.js:209`
- [shiftValue.md](shiftValue.md): `shiftValue` | categoria `date/time` | tema `valor` | origem `sistema/app/static/transport/app.js:298`
- [startOfLocalDay.md](startOfLocalDay.md): `startOfLocalDay` | categoria `date/time` | tema `de local dia` | origem `sistema/app/static/transport/app.js:168`
- [submitAssignment.md](submitAssignment.md): `submitAssignment` | categoria `API + state + date/time` | tema `assignment` | origem `sistema/app/static/transport/app.js:3229`
- [syncRouteTimeControls.md](syncRouteTimeControls.md): `syncRouteTimeControls` | categoria `state + date/time` | tema `rota horario controles` | origem `sistema/app/static/transport/app.js:1812`
- [syncVehicleModalFields.md](syncVehicleModalFields.md): `syncVehicleModalFields` | categoria `UI + state + date/time` | tema `veiculo modal fields` | origem `sistema/app/static/transport/app.js:2556`
- [updateVehicleGridLayout.md](updateVehicleGridLayout.md): `updateVehicleGridLayout` | categoria `UI` | tema `grade de veiculos layout` | origem `sistema/app/static/transport/app.js:443`
- [updateVehicleGridLayouts.md](updateVehicleGridLayouts.md): `updateVehicleGridLayouts` | categoria `UI` | tema `grade de veiculos layouts` | origem `sistema/app/static/transport/app.js:472`

## 6. Projetos e filtros (5)

Lista de projetos, visibilidade client-side e filtros de requests.

- [getProjectRows.md](getProjectRows.md): `getProjectRows` | categoria `state` | tema `projeto linhas` | origem `sistema/app/static/transport/app.js:2656`
- [hasAnyVisibleProject.md](hasAnyVisibleProject.md): `hasAnyVisibleProject` | categoria `state` | tema `algum visivel projeto` | origem `sistema/app/static/transport/app.js:2674`
- [isProjectVisible.md](isProjectVisible.md): `isProjectVisible` | categoria `state` | tema `projeto visivel` | origem `sistema/app/static/transport/app.js:2684`
- [reconcileProjectVisibility.md](reconcileProjectVisibility.md): `reconcileProjectVisibility` | categoria `state` | tema `projeto visibility` | origem `sistema/app/static/transport/app.js:2663`
- [renderProjectList.md](renderProjectList.md): `renderProjectList` | categoria `UI + state` | tema `projeto list` | origem `sistema/app/static/transport/app.js:3050`

## 7. Solicitacoes (23)

Filas de requests, colapso visual, metadados e rejeicao operacional.

- [applyRequestRowCollapsedVisualState.md](applyRequestRowCollapsedVisualState.md): `applyRequestRowCollapsedVisualState` | categoria `UI + state` | tema `linha de solicitacao collapsed visual state` | origem `sistema/app/static/transport/app.js:1690`
- [canRequestBeDroppedOnVehicle.md](canRequestBeDroppedOnVehicle.md): `canRequestBeDroppedOnVehicle` | categoria `utility` | tema `solicitacao be dropped on veiculo` | origem `sistema/app/static/transport/app.js:1084`
- [clearRequestCollapseOverridesForKind.md](clearRequestCollapseOverridesForKind.md): `clearRequestCollapseOverridesForKind` | categoria `state` | tema `solicitacao colapso overrides para tipo` | origem `sistema/app/static/transport/app.js:1652`
- [clearRequestRowStateClass.md](clearRequestRowStateClass.md): `clearRequestRowStateClass` | categoria `UI + state` | tema `linha de solicitacao state class` | origem `sistema/app/static/transport/app.js:3105`
- [getAllRequests.md](getAllRequests.md): `getAllRequests` | categoria `state` | tema `todas solicitacoes` | origem `sistema/app/static/transport/app.js:2719`
- [getAllVisibleRequests.md](getAllVisibleRequests.md): `getAllVisibleRequests` | categoria `state` | tema `todas visivel solicitacoes` | origem `sistema/app/static/transport/app.js:2725`
- [getDraggedRequest.md](getDraggedRequest.md): `getDraggedRequest` | categoria `state` | tema `arrastada solicitacao` | origem `sistema/app/static/transport/app.js:2739`
- [getRequestById.md](getRequestById.md): `getRequestById` | categoria `state` | tema `solicitacao by id` | origem `sistema/app/static/transport/app.js:2731`
- [getRequestLabel.md](getRequestLabel.md): `getRequestLabel` | categoria `utility` | tema `solicitacao rotulo` | origem `sistema/app/static/transport/app.js:1154`
- [getRequestRowCollapsedState.md](getRequestRowCollapsedState.md): `getRequestRowCollapsedState` | categoria `state` | tema `linha de solicitacao collapsed state` | origem `sistema/app/static/transport/app.js:1662`
- [getRequestSectionCollapsedState.md](getRequestSectionCollapsedState.md): `getRequestSectionCollapsedState` | categoria `state` | tema `solicitacao secao collapsed state` | origem `sistema/app/static/transport/app.js:1658`
- [getRequestsForKind.md](getRequestsForKind.md): `getRequestsForKind` | categoria `state` | tema `solicitacoes para tipo` | origem `sistema/app/static/transport/app.js:2647`
- [getRequestTitle.md](getRequestTitle.md): `getRequestTitle` | categoria `utility` | tema `solicitacao titulo` | origem `sistema/app/static/transport/app.js:1150`
- [getRouteKindForRequestRow.md](getRouteKindForRequestRow.md): `getRouteKindForRequestRow` | categoria `state` | tema `tipo de rota para linha de solicitacao` | origem `sistema/app/static/transport/app.js:2532`
- [getVisibleRequestsForKind.md](getVisibleRequestsForKind.md): `getVisibleRequestsForKind` | categoria `state` | tema `visivel solicitacoes para tipo` | origem `sistema/app/static/transport/app.js:2695`
- [isRequestAssignedToVehicle.md](isRequestAssignedToVehicle.md): `isRequestAssignedToVehicle` | categoria `utility` | tema `solicitacao alocada para veiculo` | origem `sistema/app/static/transport/app.js:1050`
- [preserveRequestSectionScrollPosition.md](preserveRequestSectionScrollPosition.md): `preserveRequestSectionScrollPosition` | categoria `state` | tema `solicitacao secao scroll posicao` | origem `sistema/app/static/transport/app.js:1703`
- [setRequestRowCollapsedState.md](setRequestRowCollapsedState.md): `setRequestRowCollapsedState` | categoria `state` | tema `linha de solicitacao collapsed state` | origem `sistema/app/static/transport/app.js:1675`
- [shouldHighlightRequestName.md](shouldHighlightRequestName.md): `shouldHighlightRequestName` | categoria `utility` | tema `destaque solicitacao name` | origem `sistema/app/static/transport/app.js:1042`
- [syncRequestSectionCollapsedRowsInDom.md](syncRequestSectionCollapsedRowsInDom.md): `syncRequestSectionCollapsedRowsInDom` | categoria `UI + state` | tema `solicitacao secao collapsed linhas in dom` | origem `sistema/app/static/transport/app.js:1714`
- [syncRequestSectionToggleState.md](syncRequestSectionToggleState.md): `syncRequestSectionToggleState` | categoria `UI + state` | tema `solicitacao secao alternancia state` | origem `sistema/app/static/transport/app.js:1737`
- [toggleRequestRowCollapsed.md](toggleRequestRowCollapsed.md): `toggleRequestRowCollapsed` | categoria `state` | tema `linha de solicitacao collapsed` | origem `sistema/app/static/transport/app.js:1726`
- [toggleRequestSectionCollapsed.md](toggleRequestSectionCollapsed.md): `toggleRequestSectionCollapsed` | categoria `state` | tema `solicitacao secao collapsed` | origem `sistema/app/static/transport/app.js:1750`

## 8. Atribuicoes e rotas (9)

Alocacao de requests em veiculos, rota selecionada e retornos para pendencia.

- [formatRouteTableValue.md](formatRouteTableValue.md): `formatRouteTableValue` | categoria `utility` | tema `rota table valor` | origem `sistema/app/static/transport/app.js:991`
- [getPendingAssignmentPreview.md](getPendingAssignmentPreview.md): `getPendingAssignmentPreview` | categoria `state` | tema `pending assignment previsualizacao` | origem `sistema/app/static/transport/app.js:2754`
- [getRouteKindForVehicle.md](getRouteKindForVehicle.md): `getRouteKindForVehicle` | categoria `state` | tema `tipo de rota para veiculo` | origem `sistema/app/static/transport/app.js:2525`
- [getRouteKindLabel.md](getRouteKindLabel.md): `getRouteKindLabel` | categoria `utility` | tema `tipo de rota rotulo` | origem `sistema/app/static/transport/app.js:1140`
- [getSelectedRouteKind.md](getSelectedRouteKind.md): `getSelectedRouteKind` | categoria `state` | tema `selecionado tipo de rota` | origem `sistema/app/static/transport/app.js:2521`
- [handleVehicleDragEnter.md](handleVehicleDragEnter.md): `handleVehicleDragEnter` | categoria `utility` | tema `veiculo arraste enter` | origem `sistema/app/static/transport/app.js:3424`
- [handleVehicleDragOver.md](handleVehicleDragOver.md): `handleVehicleDragOver` | categoria `utility` | tema `veiculo arraste over` | origem `sistema/app/static/transport/app.js:3385`
- [handleVehicleDrop.md](handleVehicleDrop.md): `handleVehicleDrop` | categoria `state` | tema `veiculo drop` | origem `sistema/app/static/transport/app.js:3395`
- [syncRouteInputs.md](syncRouteInputs.md): `syncRouteInputs` | categoria `state` | tema `rota inputs` | origem `sistema/app/static/transport/app.js:2519`

## 9. Veiculos (35)

Cadastro, remocao, detalhes, modos de exibicao e interacao com os paineis.

- [buildVehiclePassengerAwarenessRows.md](buildVehiclePassengerAwarenessRows.md): `buildVehiclePassengerAwarenessRows` | categoria `utility` | tema `veiculo passageiro ciencia linhas` | origem `sistema/app/static/transport/app.js:1115`
- [buildVehiclePassengerPreviewRows.md](buildVehiclePassengerPreviewRows.md): `buildVehiclePassengerPreviewRows` | categoria `utility` | tema `veiculo passageiro previsualizacao linhas` | origem `sistema/app/static/transport/app.js:1096`
- [canOpenVehicleModal.md](canOpenVehicleModal.md): `canOpenVehicleModal` | categoria `state` | tema `open veiculo modal` | origem `sistema/app/static/transport/app.js:2548`
- [clearVehicleModalFeedback.md](clearVehicleModalFeedback.md): `clearVehicleModalFeedback` | categoria `state` | tema `veiculo modal feedback` | origem `sistema/app/static/transport/app.js:2487`
- [closeExpandedVehicleDetails.md](closeExpandedVehicleDetails.md): `closeExpandedVehicleDetails` | categoria `UI + state` | tema `expandido detalhes do veiculo` | origem `sistema/app/static/transport/app.js:2813`
- [closeVehicleModal.md](closeVehicleModal.md): `closeVehicleModal` | categoria `state` | tema `veiculo modal` | origem `sistema/app/static/transport/app.js:2638`
- [createPassengerRemoveButton.md](createPassengerRemoveButton.md): `createPassengerRemoveButton` | categoria `UI + state` | tema `passageiro remocao button` | origem `sistema/app/static/transport/app.js:2935`
- [createVehicleIconButton.md](createVehicleIconButton.md): `createVehicleIconButton` | categoria `UI + state` | tema `veiculo icone button` | origem `sistema/app/static/transport/app.js:3313`
- [ensureExpandedVehicleStillExists.md](ensureExpandedVehicleStillExists.md): `ensureExpandedVehicleStillExists` | categoria `state` | tema `expandido veiculo still exists` | origem `sistema/app/static/transport/app.js:2781`
- [findExpandedVehicleDetailsElements.md](findExpandedVehicleDetailsElements.md): `findExpandedVehicleDetailsElements` | categoria `UI + state` | tema `expandido detalhes do veiculo elements` | origem `sistema/app/static/transport/app.js:2848`
- [focusVehicleFormField.md](focusVehicleFormField.md): `focusVehicleFormField` | categoria `state` | tema `veiculo formulario field` | origem `sistema/app/static/transport/app.js:1345`
- [formatVehicleOccupancyCount.md](formatVehicleOccupancyCount.md): `formatVehicleOccupancyCount` | categoria `utility` | tema `veiculo ocupacao quantidade` | origem `sistema/app/static/transport/app.js:1005`
- [formatVehicleOccupancyLabel.md](formatVehicleOccupancyLabel.md): `formatVehicleOccupancyLabel` | categoria `utility` | tema `veiculo ocupacao rotulo` | origem `sistema/app/static/transport/app.js:999`
- [formatVehicleTypeTableValue.md](formatVehicleTypeTableValue.md): `formatVehicleTypeTableValue` | categoria `utility` | tema `veiculo type table valor` | origem `sistema/app/static/transport/app.js:987`
- [getPassengerAwarenessState.md](getPassengerAwarenessState.md): `getPassengerAwarenessState` | categoria `utility` | tema `passageiro ciencia state` | origem `sistema/app/static/transport/app.js:1046`
- [getVehicleByScopeAndId.md](getVehicleByScopeAndId.md): `getVehicleByScopeAndId` | categoria `state` | tema `veiculo by escopo and id` | origem `sistema/app/static/transport/app.js:2746`
- [getVehicleDetailsKey.md](getVehicleDetailsKey.md): `getVehicleDetailsKey` | categoria `state` | tema `detalhes do veiculo chave` | origem `sistema/app/static/transport/app.js:2777`
- [getVehicleGridItemMetrics.md](getVehicleGridItemMetrics.md): `getVehicleGridItemMetrics` | categoria `UI` | tema `grade de veiculos item metricas` | origem `sistema/app/static/transport/app.js:427`
- [getVehicleRegistryRows.md](getVehicleRegistryRows.md): `getVehicleRegistryRows` | categoria `state` | tema `veiculo registry linhas` | origem `sistema/app/static/transport/app.js:2710`
- [getVehiclesForScope.md](getVehiclesForScope.md): `getVehiclesForScope` | categoria `state` | tema `vehicles para escopo` | origem `sistema/app/static/transport/app.js:2701`
- [getVehicleViewMode.md](getVehicleViewMode.md): `getVehicleViewMode` | categoria `state` | tema `veiculo visualizacao modo` | origem `sistema/app/static/transport/app.js:1879`
- [mapVehicleIconPath.md](mapVehicleIconPath.md): `mapVehicleIconPath` | categoria `utility` | tema `veiculo icone path` | origem `sistema/app/static/transport/app.js:995`
- [mapVehicleTypeLabel.md](mapVehicleTypeLabel.md): `mapVehicleTypeLabel` | categoria `utility` | tema `veiculo type rotulo` | origem `sistema/app/static/transport/app.js:981`
- [normalizeVehicleScope.md](normalizeVehicleScope.md): `normalizeVehicleScope` | categoria `utility` | tema `veiculo escopo` | origem `sistema/app/static/transport/app.js:808`
- [normalizeVehicleSeatCountSetting.md](normalizeVehicleSeatCountSetting.md): `normalizeVehicleSeatCountSetting` | categoria `utility` | tema `veiculo assento quantidade setting` | origem `sistema/app/static/transport/app.js:740`
- [renderVehiclePanels.md](renderVehiclePanels.md): `renderVehiclePanels` | categoria `UI + state` | tema `veiculo panels` | origem `sistema/app/static/transport/app.js:3513`
- [resolveVehicleDetailsPosition.md](resolveVehicleDetailsPosition.md): `resolveVehicleDetailsPosition` | categoria `utility` | tema `detalhes do veiculo posicao` | origem `sistema/app/static/transport/app.js:377`
- [resolveVehicleForm.md](resolveVehicleForm.md): `resolveVehicleForm` | categoria `UI` | tema `veiculo formulario` | origem `sistema/app/static/transport/app.js:816`
- [scheduleExpandedVehicleDetailsPositionSync.md](scheduleExpandedVehicleDetailsPositionSync.md): `scheduleExpandedVehicleDetailsPositionSync` | categoria `state` | tema `expandido detalhes do veiculo posicao sync` | origem `sistema/app/static/transport/app.js:2918`
- [setVehicleContainerViewMode.md](setVehicleContainerViewMode.md): `setVehicleContainerViewMode` | categoria `UI + state` | tema `veiculo container visualizacao modo` | origem `sistema/app/static/transport/app.js:1883`
- [setVehicleModalFeedback.md](setVehicleModalFeedback.md): `setVehicleModalFeedback` | categoria `UI + state` | tema `veiculo modal feedback` | origem `sistema/app/static/transport/app.js:2469`
- [syncExpandedVehicleDetailsPosition.md](syncExpandedVehicleDetailsPosition.md): `syncExpandedVehicleDetailsPosition` | categoria `UI + state` | tema `expandido detalhes do veiculo posicao` | origem `sistema/app/static/transport/app.js:2870`
- [syncVehicleViewToggleState.md](syncVehicleViewToggleState.md): `syncVehicleViewToggleState` | categoria `UI + state` | tema `veiculo visualizacao alternancia state` | origem `sistema/app/static/transport/app.js:1893`
- [toggleVehicleDetails.md](toggleVehicleDetails.md): `toggleVehicleDetails` | categoria `state` | tema `detalhes do veiculo` | origem `sistema/app/static/transport/app.js:2797`
- [toggleVehicleViewMode.md](toggleVehicleViewMode.md): `toggleVehicleViewMode` | categoria `state` | tema `veiculo visualizacao modo` | origem `sistema/app/static/transport/app.js:1906`

## 10. Layout e renderizacao (8)

Helpers de DOM, grade, divisores, posicionamento e renderizacao visual.

- [applyResize.md](applyResize.md): `applyResize` | categoria `utility` | tema `redimensionamento` | origem `sistema/app/static/transport/app.js:550`
- [clearElement.md](clearElement.md): `clearElement` | categoria `utility` | tema `element` | origem `sistema/app/static/transport/app.js:624`
- [createEmptyState.md](createEmptyState.md): `createEmptyState` | categoria `UI` | tema `vazio state` | origem `sistema/app/static/transport/app.js:1158`
- [createNode.md](createNode.md): `createNode` | categoria `UI` | tema `node` | origem `sistema/app/static/transport/app.js:633`
- [resolvePanelMinimumSize.md](resolvePanelMinimumSize.md): `resolvePanelMinimumSize` | categoria `UI` | tema `painel minimo tamanho` | origem `sistema/app/static/transport/app.js:479`
- [resolvePanelSizes.md](resolvePanelSizes.md): `resolvePanelSizes` | categoria `utility` | tema `painel sizes` | origem `sistema/app/static/transport/app.js:343`
- [resolveResizeConfig.md](resolveResizeConfig.md): `resolveResizeConfig` | categoria `utility` | tema `redimensionamento configuracao` | origem `sistema/app/static/transport/app.js:363`
- [stopResize.md](stopResize.md): `stopResize` | categoria `UI` | tema `redimensionamento` | origem `sistema/app/static/transport/app.js:573`

## 11. Infraestrutura compartilhada (16)

Wrappers de API, tratamento de erro e utilitarios transversais.

- [clampValue.md](clampValue.md): `clampValue` | categoria `utility` | tema `valor` | origem `sistema/app/static/transport/app.js:323`
- [enableResizableDivider.md](enableResizableDivider.md): `enableResizableDivider` | categoria `UI` | tema `resizable divisor` | origem `sistema/app/static/transport/app.js:503`
- [extractApiMessage.md](extractApiMessage.md): `extractApiMessage` | categoria `utility` | tema `mensagem de API` | origem `sistema/app/static/transport/app.js:682`
- [formatApiErrorMessage.md](formatApiErrorMessage.md): `formatApiErrorMessage` | categoria `utility` | tema `API erro mensagem` | origem `sistema/app/static/transport/app.js:711`
- [getModalScopeNote.md](getModalScopeNote.md): `getModalScopeNote` | categoria `utility` | tema `modal escopo note` | origem `sistema/app/static/transport/app.js:1145`
- [getOrdinalSuffix.md](getOrdinalSuffix.md): `getOrdinalSuffix` | categoria `utility` | tema `ordinal sufixo` | origem `sistema/app/static/transport/app.js:173`
- [handleProtectedRequestError.md](handleProtectedRequestError.md): `handleProtectedRequestError` | categoria `state` | tema `protegida solicitacao erro` | origem `sistema/app/static/transport/app.js:2043`
- [localizeTransportApiMessage.md](localizeTransportApiMessage.md): `localizeTransportApiMessage` | categoria `utility` | tema `transporte mensagem de API` | origem `sistema/app/static/transport/app.js:716`
- [mapScopeTitle.md](mapScopeTitle.md): `mapScopeTitle` | categoria `utility` | tema `escopo titulo` | origem `sistema/app/static/transport/app.js:1136`
- [notify.md](notify.md): `notify` | categoria `utility` | tema `notify` | origem `sistema/app/static/transport/app.js:283`
- [parsePixelValue.md](parsePixelValue.md): `parsePixelValue` | categoria `utility` | tema `pixel valor` | origem `sistema/app/static/transport/app.js:335`
- [parsePositiveNumber.md](parsePositiveNumber.md): `parsePositiveNumber` | categoria `utility` | tema `positivo number` | origem `sistema/app/static/transport/app.js:327`
- [requestJson.md](requestJson.md): `requestJson` | categoria `API` | tema `JSON` | origem `sistema/app/static/transport/app.js:644`
- [setStatus.md](setStatus.md): `setStatus` | categoria `UI + state` | tema `status` | origem `sistema/app/static/transport/app.js:2460`
- [subscribe.md](subscribe.md): `subscribe` | categoria `utility` | tema `subscribe` | origem `sistema/app/static/transport/app.js:302`
- [unsubscribe.md](unsubscribe.md): `unsubscribe` | categoria `utility` | tema `unsubscribe` | origem `sistema/app/static/transport/app.js:310`
