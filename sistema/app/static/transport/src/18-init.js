
  function initTransportPage() {
    if (typeof document === "undefined") {
      return;
    }

    const dateStore = createTransportDateStore(resolveStoredTransportDate(new Date()));
    document.querySelectorAll("[data-date-panel]").forEach(function (panelElement) {
      createDatePanelController(panelElement, dateStore);
    });
    document.querySelectorAll("[data-resize]").forEach(enableResizableDivider);
    document.querySelectorAll("[data-panel-resize-handle]").forEach(enableVehiclePanelResizeHandle);
    const vehiclePanelsRoot = document.getElementById("tela01main_dir");
    if (vehiclePanelsRoot) {
      syncVehiclePanelExplicitHeights(vehiclePanelsRoot);
      updateVehicleGridLayouts(vehiclePanelsRoot);
      syncVehiclePanelResizeHandleState(vehiclePanelsRoot);
    }
    const pageController = createTransportPageController(dateStore);
    globalScope.CheckingTransportPageController = pageController;
    globalScope.addEventListener("resize", function () {
      pageController.refreshVehicleGridLayouts();
    });
    document.addEventListener("visibilitychange", function () {
      pageController.handlePageVisibilityChange();
    });
    dateStore.subscribe(function (selectedDate) {
      setStoredTransportDate(selectedDate);
      pageController.closeRouteTimePopover();
      pageController.loadDashboard(selectedDate);
    });
    pageController.bootstrapTransportSession();
  }

  const transportPageApi = {
    buildVehicleCreatePayload,
    clampValue,
    createTransportDateStore,
    extractApiMessage,
    extractStructuredTransportApiPayload,
    formatApiErrorMessage,
    formatTransportDate,
    formatIsoDate,
    formatExtraVehicleReferenceLabel,
    getEffectiveWorkToHomeDepartureTime,
    getExtraVehicleDepartureFieldKey,
    getTransportDateState,
    getDefaultAiAgentSettings,
    getVehicleDepartureTime,
    getVehicleReferenceLabel,
    getRoutineVehicleReferenceMode,
    getVehiclePendingAllocationMessage,
    getOrdinalSuffix,
    localizeTransportApiMessage,
    resolveTransportApiStructuredMessage,
    isPendingVehicleField,
    isVehicleReadyForAllocation,
    isValidTransportTimeValue,
    formatPendingVehicleField,
    formatVehicleOccupancyLabel,
    formatVehicleOccupancyCount,
    getDefaultVehicleFormValues,
    getDefaultVehicleSeatCount,
    getDefaultVehicleToleranceMinutes,
    formatTransportCurrencyOptionLabel,
    formatTransportCurrencyAmount,
    formatTransportPriceInputValue,
    normalizeTransportCurrencyCode,
    normalizeTransportPriceRateUnit,
    applyTransportVehicleToleranceDefault,
    resolveTransportCurrencyOptions,
    resolveTransportVehiclePriceDefaults,
    getActiveTransportLanguageCode: getActiveLanguageCode,
    setActiveTransportLanguageCode: setActiveLanguageCode,
    translateTransportText: t,
    buildVehicleBasePayload,
    resolveVehicleEditFocusField,
    syncVehicleTypeDependentDefaults,
    buildVehiclePassengerAwarenessRows,
    getPassengerAwarenessState,
    parseStoredTransportDate,
    resolveStoredTransportDate,
    setStoredTransportDate,
    shouldHighlightRequestName,
    mapVehicleIconPath,
    buildVehiclePassengerPreviewRows,
    groupAssignedRequestsByVehicleForDate,
    canRequestBeDroppedOnVehicle,
    resolveVehicleModalOpenState,
    resolveVehicleCreateValidationError,
    resolveVehicleSaveReloadDate,
    readAiAgentSettingsDraft,
    validateAiAgentSettingsDraft,
    getAiAgentRequestKindLabel,
    buildAiAgentSubmittingFeedbackOptions,
    buildTransportAiSettingsUpdatePayload,
    buildTransportAiDashboardScope,
    buildTransportAiRouteCalculationPayload,
    shouldContinuePollingAiRouteRun,
    hasRenderableTransportAiReview,
    resolveTransportAiStructuredMessage,
    resolveTransportAiBaselineComplement,
    getTransportAiSuggestionKey,
    buildTransportAiLatestSuggestionUrl,
    buildTransportAiSuggestionCommandUrl,
    getDefaultTransportAiSettingsDraft,
    normalizeTransportAiSettingsProvider,
    getTransportAiBidirectionalPlanContract,
    getTransportAiReviewTargetContract,
    readTransportAiSettingsDraft,
    resolveTransportAiSettingsProviderDefaults,
    shouldRefreshDashboardAfterAiSuggestionCommand,
    resolveAiChangesCommandState,
    renderAiChangesSummary,
    renderAiVehicleChanges,
    renderAiPassengerAllocations,
    renderAiRouteItineraries,
    renderAiChangesAudit,
    createTransportReferenceClock,
    parsePositiveNumber,
    parseTransportTimeToMinutes,
    formatRoutineVehicleReferenceLabel,
    resolveVehiclePassengerOperationalTime,
    resolveVehicleReferenceMode,
    getDefaultVehiclePanelHeight,
    getRoutineVehicleReferenceLabel,
    isVehiclePanelResizeEnabledForViewport,
    resolveTransportReferenceNow,
    resolveRoutineVehicleReferenceMode,
    resolveNextRoutineVehicleReferenceDelayMs,
    resolveVehiclePanelExplicitHeight,
    resolveVehiclePanelResizedHeight,
    resolvePanelSizes,
    resolveResizeConfig,
    updateVehicleGridLayout,
    updateVehicleGridLayouts,
    resolveVehicleDetailsPosition,
    startOfLocalDay,
    shiftLocalDay,
  };

  if (typeof document !== "undefined") {
    applyInitialDeclarativeTranslations();
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initTransportPage, { once: true });
    } else {
      initTransportPage();
    }
  }

  globalScope.CheckingTransportPage = transportPageApi;

  if (typeof module !== "undefined" && module.exports) {
    module.exports = Object.assign({}, transportPageApi, {
      __testCreateVehicleDetailsPanel: function () {
        const pageController = globalScope.CheckingTransportPageController;
        if (!pageController || typeof pageController.__testCreateVehicleDetailsPanel !== "function") {
          throw new Error("Transport page controller test helper is unavailable.");
        }
        return pageController.__testCreateVehicleDetailsPanel.apply(pageController, arguments);
      },
    });
  }
