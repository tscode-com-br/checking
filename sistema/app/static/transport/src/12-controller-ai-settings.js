  function resolveTransportAiSettingsApiErrorState(error, options) {
    const resolvedOptions = options || {};
    const structuredPayload = extractStructuredTransportApiPayload(error && error.payload);
    const normalizedMessageKey = String(structuredPayload && structuredPayload.message_key || "").trim();
    const normalizedErrorCode = String(structuredPayload && structuredPayload.error_code || "").trim();
    const normalizedMessage = String(
      (structuredPayload && structuredPayload.message)
      || (error && error.message)
      || ""
    ).trim();
      const projectId = normalizeTransportAiSettingsProjectId(
        resolvedOptions.projectId,
        state.aiSettingsSelectedProjectId
      );
      const projectRows = normalizeTransportAiSettingsProjectRows(
        resolvedOptions.projectRows !== undefined
          ? resolvedOptions.projectRows
          : state.aiSettingsProjects
      );
      const hasProjectInCatalog = hasValidTransportAiSettingsProjectSelection(projectId, projectRows);

    if (
      normalizedErrorCode === "transport_ai_settings_project_required"
      || normalizedMessageKey === "ai.settingsProjectRequired"
      || isTransportAiProjectRequiredErrorPayload(error && error.payload)
      || normalizedMessage === "Transport AI project is required."
    ) {
      return {
        message: t("ai.settingsProjectRequired"),
        clearProjectSelection: false,
        markCatalogAsError: false,
      };
    }

    if (
      normalizedErrorCode === "transport_ai_settings_project_not_found"
      || normalizedMessageKey === "ai.settingsProjectMissing"
      || normalizedMessage === "Transport AI project does not exist."
    ) {
      return {
        message: t(hasProjectInCatalog ? "ai.settingsProjectRemoved" : "ai.settingsProjectMissing"),
        clearProjectSelection: true,
        markCatalogAsError: true,
      };
    }

    return {
      message: resolveTransportApiStructuredMessage(error && error.payload)
        || localizeTransportApiMessage(normalizedMessage),
      clearProjectSelection: false,
      markCatalogAsError: false,
    };
  }

    function getSelectedTransportAiSettingsProject() {
      const selectedProjectId = normalizeTransportAiSettingsProjectId(state.aiSettingsSelectedProjectId, null);
      if (!selectedProjectId) {
        return null;
      }
      return getTransportAiSettingsProjectRows().find(function (projectRow) {
        return projectRow.id === selectedProjectId;
      }) || null;
    }

    function applyTransportAiSettingsProjects(projectRows, preferredProjectId) {
      const normalizedProjects = normalizeTransportAiSettingsProjectRows(projectRows);
      const activeDraft = readTransportAiSettingsDraft(undefined, state.aiSettingsDraft || getDefaultTransportAiSettingsDraft());
      const previousSelectedProjectId = normalizeTransportAiSettingsProjectId(
        state.aiSettingsSelectedProjectId,
        null
      );
      state.aiSettingsProjects = normalizedProjects;
      const selectedProjectId = normalizeTransportAiSettingsProjectId(
        preferredProjectId,
        previousSelectedProjectId
      );
      const matchedProject = normalizedProjects.find(function (projectRow) {
        return projectRow.id === selectedProjectId;
      }) || normalizedProjects[0] || null;
      state.aiSettingsSelectedProjectId = matchedProject ? matchedProject.id : null;

      if (!matchedProject) {
        clearTransportAiSettingsProjectSelection();
        return null;
      }

      const activeDraftProjectId = normalizeTransportAiSettingsProjectId(activeDraft.projectId, null);
      if (previousSelectedProjectId === matchedProject.id && activeDraftProjectId === matchedProject.id) {
        state.aiSettingsDraft = activeDraft;
        return matchedProject;
      }

      state.aiSettingsDraft = readTransportAiSettingsDraft(
        {
          projectId: matchedProject.id,
          provider: DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER,
          apiKey: "",
        },
        getDefaultTransportAiSettingsDraft()
      );
      return matchedProject;
    }

    function syncAiSettingsControls(options) {
      const syncOptions = options || {};
      const activeDraft = readTransportAiSettingsDraft(undefined, state.aiSettingsDraft || getDefaultTransportAiSettingsDraft());
      const availableProjects = Array.isArray(state.aiSettingsProjects) ? state.aiSettingsProjects : [];
      const projectCatalogStatus = getTransportAiSettingsProjectCatalogStatus();
      const projectCatalogReady = projectCatalogStatus === AI_SETTINGS_PROJECT_CATALOG_STATUS.ready;
      const projectCatalogLoading = projectCatalogStatus === AI_SETTINGS_PROJECT_CATALOG_STATUS.loading;
      const selectedProjectId = normalizeTransportAiSettingsProjectId(
        state.aiSettingsSelectedProjectId,
        activeDraft.projectId
      );
      const hasSelectedProject = hasValidTransportAiSettingsProjectSelection(selectedProjectId, availableProjects);
      const selectedProvider = normalizeTransportAiSettingsProvider(
        activeDraft.provider,
        state.aiSettingsLoadedProvider || DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER
      );
      const controlsDisabled = !state.isAuthenticated || state.aiSettingsLoading || state.aiSettingsSaving;
      const projectControlsDisabled = controlsDisabled || projectCatalogLoading || !availableProjects.length;
      const fieldControlsDisabled = controlsDisabled || !hasSelectedProject || !projectCatalogReady;
      const apiKeyValue = String(activeDraft.apiKey || "").trim();

      if (aiSettingsProjectInput) {
        clearElement(aiSettingsProjectInput);
        if (!availableProjects.length) {
          const emptyOption = document.createElement("option");
          emptyOption.value = "";
          emptyOption.textContent = projectCatalogLoading
            ? t("ai.settingsLoading")
            : t("ai.settingsNoProjectsAvailable");
          aiSettingsProjectInput.appendChild(emptyOption);
        } else {
          const placeholderOption = document.createElement("option");
          placeholderOption.value = "";
          placeholderOption.textContent = t("ai.settingsSelectProject");
          aiSettingsProjectInput.appendChild(placeholderOption);

          availableProjects.forEach(function (projectRow) {
            const optionElement = document.createElement("option");
            optionElement.value = String(projectRow.id);
            optionElement.textContent = projectRow.name;
            aiSettingsProjectInput.appendChild(optionElement);
          });
        }
        aiSettingsProjectInput.value = hasSelectedProject ? String(selectedProjectId) : "";
        aiSettingsProjectInput.disabled = projectControlsDisabled;
      }

      if (!syncOptions.preserveInputs) {
        if (aiSettingsProviderInput) {
          aiSettingsProviderInput.value = selectedProvider;
        }
        if (aiSettingsApiKeyInput) {
          aiSettingsApiKeyInput.value = activeDraft.apiKey;
        }
      }

      if (aiSettingsProviderInput) {
        aiSettingsProviderInput.disabled = fieldControlsDisabled;
      }
      if (aiSettingsApiKeyInput) {
        aiSettingsApiKeyInput.disabled = fieldControlsDisabled;
      }
      if (aiSettingsMapsApiKeyInput) {
        if (!syncOptions.preserveInputs) {
          aiSettingsMapsApiKeyInput.value = activeDraft.mapsApiKey;
        }
        aiSettingsMapsApiKeyInput.disabled = controlsDisabled;
      }
      if (aiSettingsProviderNote) {
        if (projectCatalogLoading) {
          aiSettingsProviderNote.textContent = t("ai.settingsLoading");
        } else if (!availableProjects.length) {
          aiSettingsProviderNote.textContent = t("ai.settingsNoProjectsAvailable");
        } else if (!hasSelectedProject) {
          aiSettingsProviderNote.textContent = t("ai.settingsSelectProject");
        } else if (!projectCatalogReady) {
          aiSettingsProviderNote.textContent = t("ai.settingsProjectLoadFailed");
        } else {
          aiSettingsProviderNote.textContent = buildTransportAiSettingsProviderNote(selectedProvider);
        }
      }
      if (aiSettingsApiKeyHint) {
        let hintMessage = "";
        let hintTone = "info";
        if (projectCatalogLoading) {
          hintMessage = "";
        } else if (!projectCatalogReady && hasSelectedProject) {
          hintMessage = t("ai.settingsProjectLoadFailed");
          hintTone = "warning";
        } else if (!hasSelectedProject && availableProjects.length) {
          hintMessage = t("ai.settingsSelectProject");
        } else if (!apiKeyValue) {
          if (state.aiSettingsHasApiKey && selectedProvider === state.aiSettingsLoadedProvider && state.aiSettingsApiKeyHint) {
            hintMessage = t("ai.settingsApiKeyHint", { hint: state.aiSettingsApiKeyHint });
          } else if (state.aiSettingsHasApiKey && selectedProvider !== state.aiSettingsLoadedProvider) {
            hintMessage = t("ai.settingsProviderChangeRequiresKey");
            hintTone = "warning";
          } else if (!state.aiSettingsHasApiKey) {
            hintMessage = t("ai.settingsApiKeyMissing");
          }
        }

        aiSettingsApiKeyHint.hidden = !hintMessage;
        aiSettingsApiKeyHint.textContent = hintMessage;
        aiSettingsApiKeyHint.dataset.tone = hintTone;
      }

      if (aiSettingsMapsApiKeyHint) {
        const mapsApiKeyValue = String(activeDraft.mapsApiKey || "").trim();
        let mapsHintMessage = "";
        let mapsHintTone = "info";
        if (!mapsApiKeyValue) {
          if (state.aiSettingsHasMapsApiKey && state.aiSettingsMapsApiKeyHint) {
            mapsHintMessage = t("ai.settingsMapsApiKeyHint", { hint: state.aiSettingsMapsApiKeyHint });
          } else if (!state.aiSettingsHasMapsApiKey) {
            mapsHintMessage = t("ai.settingsMapsApiKeyMissing");
          }
        }
        aiSettingsMapsApiKeyHint.hidden = !mapsHintMessage;
        aiSettingsMapsApiKeyHint.textContent = mapsHintMessage;
        aiSettingsMapsApiKeyHint.dataset.tone = mapsHintTone;
      }

      document.querySelectorAll("[data-close-ai-settings-modal]").forEach(function (buttonElement) {
        buttonElement.disabled = state.aiSettingsSaving;
      });
      document.querySelectorAll("[data-ai-settings-save]").forEach(function (buttonElement) {
        buttonElement.disabled = fieldControlsDisabled;
      });

      if (aiSettingsModal) {
        aiSettingsModal.setAttribute(
          "aria-busy",
          state.aiSettingsLoading || state.aiSettingsSaving ? "true" : "false"
        );
      }

      if (!aiSettingsFeedback) {
        return;
      }

      let feedbackMessage = "";
      if (state.aiSettingsFeedbackKey) {
        const translatedFeedback = t(state.aiSettingsFeedbackKey, state.aiSettingsFeedbackValues || undefined);
        feedbackMessage = translatedFeedback && translatedFeedback !== state.aiSettingsFeedbackKey
          ? translatedFeedback
          : String(state.aiSettingsFeedbackMessage || "").trim() || translatedFeedback;
      } else {
        feedbackMessage = String(state.aiSettingsFeedbackMessage || "").trim();
      }
      if (!feedbackMessage) {
        aiSettingsFeedback.hidden = true;
        aiSettingsFeedback.textContent = "";
        aiSettingsFeedback.dataset.tone = state.aiSettingsFeedbackTone || "info";
        return;
      }

      aiSettingsFeedback.hidden = false;
      aiSettingsFeedback.textContent = feedbackMessage;
      aiSettingsFeedback.dataset.tone = state.aiSettingsFeedbackTone || "info";
    }

    function syncAiChangesControls() {
      const commandState = resolveAiChangesCommandState(
        state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion },
        {
          isAuthenticated: state.isAuthenticated,
          isPending: state.aiChangesCommandPending,
          pendingAction: state.aiChangesPendingAction,
        }
      );

      if (aiChangesCancelButton) {
        aiChangesCancelButton.disabled = commandState.isPending;
        aiChangesCancelButton.textContent = t("ai.changesCancel");
      }
      if (aiChangesDiscardButton) {
        aiChangesDiscardButton.disabled = !commandState.canCancel;
        aiChangesDiscardButton.textContent = t(
          commandState.isPending && commandState.pendingAction === "cancel"
            ? "ai.changesDiscarding"
            : "ai.changesDiscard"
        );
      }
      if (aiChangesApplyButton) {
        aiChangesApplyButton.disabled = !commandState.canApply;
        aiChangesApplyButton.textContent = t(
          commandState.isPending && commandState.pendingAction === "apply"
            ? "ai.changesApplying"
            : "ai.changesApply"
        );
      }

      document.querySelectorAll("[data-close-ai-changes-modal]").forEach(function (buttonElement) {
        buttonElement.disabled = commandState.isPending;
      });

      if (aiChangesModal) {
        aiChangesModal.setAttribute("aria-busy", commandState.isPending ? "true" : "false");
      }
    }

    function syncAiChangesSummaryCopy() {
      if (!aiChangesSummary) {
        return;
      }

      let summaryMessage = "";
      if (state.aiChangesSummaryKey) {
        const translatedSummary = t(state.aiChangesSummaryKey, state.aiChangesSummaryValues || undefined);
        summaryMessage = translatedSummary && translatedSummary !== state.aiChangesSummaryKey
          ? translatedSummary
          : String(state.aiChangesSummaryMessage || "").trim() || translatedSummary;
      } else {
        summaryMessage = String(state.aiChangesSummaryMessage || "").trim();
      }
      if (!summaryMessage) {
        aiChangesSummary.hidden = true;
        aiChangesSummary.textContent = "";
        aiChangesSummary.dataset.tone = state.aiChangesSummaryTone || "success";
        return;
      }

      aiChangesSummary.hidden = false;
      aiChangesSummary.textContent = summaryMessage;
      aiChangesSummary.dataset.tone = state.aiChangesSummaryTone || "success";
    }

    function syncAiChangesSummaryRender() {
      if ((!aiChangesSummaryGrid && !aiChangesSummaryPanel) || (!state.aiRouteRunStatus && !state.aiRouteSuggestion)) {
        return;
      }

      renderAiChangesSummary({
        runStatusResponse: state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion },
        fallbackCurrencyCode: state.priceCurrencyCode,
        summaryGridElement: aiChangesSummaryGrid,
        summaryPanelElement: aiChangesSummaryPanel,
      });
    }

    function syncAiVehicleChangesRender() {
      if (!aiChangesVehiclesPanel || (!state.aiRouteRunStatus && !state.aiRouteSuggestion)) {
        return;
      }

      renderAiVehicleChanges({
        runStatusResponse: state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion },
        fallbackCurrencyCode: state.priceCurrencyCode,
        vehiclesPanelElement: aiChangesVehiclesPanel,
      });
    }

    function syncAiPassengerAllocationsRender() {
      if (!aiChangesPassengersPanel || (!state.aiRouteRunStatus && !state.aiRouteSuggestion)) {
        return;
      }

      renderAiPassengerAllocations({
        runStatusResponse: state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion },
        passengersPanelElement: aiChangesPassengersPanel,
      });
    }

    function syncAiRouteItinerariesRender() {
      if (!aiChangesRoutesPanel || (!state.aiRouteRunStatus && !state.aiRouteSuggestion)) {
        return;
      }

      renderAiRouteItineraries({
        runStatusResponse: state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion },
        fallbackCurrencyCode: state.priceCurrencyCode,
        routesPanelElement: aiChangesRoutesPanel,
      });
    }

    function syncAiChangesAuditRender() {
      if (!aiChangesAuditPanel || (!state.aiRouteRunStatus && !state.aiRouteSuggestion)) {
        return;
      }

      renderAiChangesAudit({
        runStatusResponse: state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion },
        auditPanelElement: aiChangesAuditPanel,
      });
    }

    function readTransportSettingsDraft() {
      return {
        arriveAtWorkTime: settingsArriveAtWorkInput ? settingsArriveAtWorkInput.value : state.arriveAtWorkTime,
        workToHomeTime: settingsTimeInput ? settingsTimeInput.value : state.workToHomeTime,
        extraCarToleranceMinutes: settingsExtraCarToleranceInput
          ? settingsExtraCarToleranceInput.value
          : state.extraCarToleranceMinutes,
        lastUpdateTime: settingsLastUpdateInput ? settingsLastUpdateInput.value : state.lastUpdateTime,
        priceCurrencyCode: settingsPriceCurrencySelect ? settingsPriceCurrencySelect.value : state.priceCurrencyCode,
        priceRateUnit: settingsPriceRateUnitSelect ? settingsPriceRateUnitSelect.value : state.priceRateUnit,
        defaultCarSeats: settingsDefaultSeatInputs.carro ? settingsDefaultSeatInputs.carro.value : state.vehicleSeatDefaults.carro,
        defaultMinivanSeats: settingsDefaultSeatInputs.minivan ? settingsDefaultSeatInputs.minivan.value : state.vehicleSeatDefaults.minivan,
        defaultVanSeats: settingsDefaultSeatInputs.van ? settingsDefaultSeatInputs.van.value : state.vehicleSeatDefaults.van,
        defaultBusSeats: settingsDefaultSeatInputs.onibus ? settingsDefaultSeatInputs.onibus.value : state.vehicleSeatDefaults.onibus,
        defaultCarPrice: settingsDefaultPriceInputs.carro ? settingsDefaultPriceInputs.carro.value : state.vehiclePriceDefaults.carro,
        defaultMinivanPrice: settingsDefaultPriceInputs.minivan ? settingsDefaultPriceInputs.minivan.value : state.vehiclePriceDefaults.minivan,
        defaultVanPrice: settingsDefaultPriceInputs.van ? settingsDefaultPriceInputs.van.value : state.vehiclePriceDefaults.van,
        defaultBusPrice: settingsDefaultPriceInputs.onibus ? settingsDefaultPriceInputs.onibus.value : state.vehiclePriceDefaults.onibus,
        defaultToleranceMinutes: settingsDefaultToleranceInput ? settingsDefaultToleranceInput.value : state.vehicleToleranceDefaultMinutes,
      };
    }

    function syncRouteTimeControls() {
      const canEditRouteTime = state.isAuthenticated;
      const shouldShowRouteTime = true;
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

      syncAiButtonPlacement();
    }

    function syncAiButtonPlacement() {
      if (!aiMenuShell || !transportTopbar) {
        return;
      }

      if (globalScope.matchMedia && globalScope.matchMedia("(max-width: 860px)").matches) {
        aiMenuShell.style.removeProperty("--transport-ai-anchor-x");
        return;
      }

      const allocationBoardTitle = document.querySelector(".transport-topbar-brand .transport-topbar-title");
      if (!allocationBoardTitle || !routeTimePopover || routeTimePopover.hidden) {
        aiMenuShell.style.removeProperty("--transport-ai-anchor-x");
        return;
      }

      const topbarRect = transportTopbar.getBoundingClientRect();
      const titleRect = allocationBoardTitle.getBoundingClientRect();
      const routeTimeRect = routeTimePopover.getBoundingClientRect();
      const aiShellRect = aiMenuShell.getBoundingClientRect();
      if (!topbarRect.width || !titleRect.width || !routeTimeRect.width || !aiShellRect.width) {
        return;
      }

      const desiredCenter = ((titleRect.right + routeTimeRect.left) / 2) - topbarRect.left;
      const minCenter = aiShellRect.width / 2 + 8;
      const maxCenter = topbarRect.width - aiShellRect.width / 2 - 8;
      const clampedCenter = Math.min(maxCenter, Math.max(minCenter, desiredCenter));
      aiMenuShell.style.setProperty("--transport-ai-anchor-x", `${clampedCenter}px`);
    }

    function syncAiMenuControls() {
      const hasActiveRun = state.aiRouteRequestPending
        || state.aiRoutePollingTimer !== null
        || shouldContinuePollingAiRouteRun(state.aiRouteRunStatus);
      const hasSuggestionReady = hasRenderableTransportAiReview(
        state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion }
      );
      if (aiMenuShell) {
        aiMenuShell.classList.toggle("is-open", state.aiMenuOpen);
        aiMenuShell.classList.toggle("is-calculating", hasActiveRun);
        aiMenuShell.classList.toggle("is-suggestion-ready", !hasActiveRun && hasSuggestionReady);
      }
      if (aiMenuTrigger) {
        aiMenuTrigger.setAttribute("aria-expanded", String(state.aiMenuOpen));
            syncAiButtonPlacement();
      }
      if (aiMenu) {
        aiMenu.hidden = !state.aiMenuOpen;
      }
      if (aiImplementModificationsButton) {
        aiImplementModificationsButton.disabled = !state.isAuthenticated || state.aiLatestSuggestionLoading;
      }
    }

    function closeAiMenu(options) {
      const closeOptions = options || {};
      state.aiMenuOpen = false;
      syncAiMenuControls();

      if (
        closeOptions.restoreFocus
        && aiMenuTrigger
        && typeof aiMenuTrigger.focus === "function"
      ) {
        aiMenuTrigger.focus();
      }
    }

    function openAiMenu() {
      state.aiMenuOpen = true;
      syncAiMenuControls();
      syncAiChangesSummaryRender();
    }

    function toggleAiMenu() {
      if (state.aiMenuOpen) {
        closeAiMenu();
        return;
      }
      openAiMenu();
    }

    function closeRouteTimePopover() {
      syncRouteTimeControls();
    }

    function saveRouteTimeForSelectedDate(nextWorkToHomeTime) {
      const normalizedTime = String(nextWorkToHomeTime || "").trim();
      if (!/^\d{2}:\d{2}$/.test(normalizedTime)) {
        syncRouteTimeControls();
        return Promise.resolve(null);
      }
      if (!state.isAuthenticated) {
        setStatus("", "warning", { key: "status.locked" });
        syncRouteTimeControls();
        return Promise.resolve(null);
      }

      state.routeTimeSaving = true;
      syncRouteTimeControls();
      return requestJson(`${TRANSPORT_API_PREFIX}/date-settings`, {
        method: "PUT",
        body: JSON.stringify({
          service_date: getCurrentServiceDateIso(),
          work_to_home_time: normalizedTime,
        }),
      })
        .then(function (response) {
          if (state.dashboard) {
            state.dashboard = Object.assign({}, state.dashboard, {
              work_to_home_departure_time:
                response && response.work_to_home_time ? response.work_to_home_time : normalizedTime,
            });
          }
          return loadDashboard(dateStore.getValue(), { announce: false }).then(function () {
            setStatus("", "success", { key: "status.settingsSaved" });
            return response;
          });
        })
        .catch(function (error) {
          handleProtectedRequestError(error, t("status.couldNotSaveSettings"));
          return null;
        })
        .finally(function () {
          state.routeTimeSaving = false;
          syncRouteTimeControls();
        });
    }

    function getVehicleViewMode(scope) {
      return state.vehicleViewModes[scope] || "grid";
    }

    function setVehicleContainerViewMode(container, scope) {
      if (!container) {
        return;
      }

      const viewMode = getVehicleViewMode(scope);
      container.dataset.vehicleView = viewMode;
      container.classList.toggle("is-management-table", viewMode === "table");
    }

    function syncVehicleViewToggleState() {
      VEHICLE_SCOPE_ORDER.forEach(function (scope) {
        const toggleLink = vehicleViewToggleLinks[scope];
        const isTableView = getVehicleViewMode(scope) === "table";
        if (!toggleLink) {
          return;
        }

        toggleLink.classList.toggle("is-management-open", isTableView);
        toggleLink.setAttribute("aria-expanded", String(isTableView));
      });
    }

    function toggleVehicleViewMode(scope) {
      state.vehicleViewModes[scope] = getVehicleViewMode(scope) === "table" ? "grid" : "table";
      renderVehiclePanels();
    }

    function setAuthShellState(shellElement, authenticated) {
      if (!shellElement) {
        return;
      }
      shellElement.classList.toggle("is-authenticated", authenticated);
      shellElement.classList.toggle("is-logged-out", !authenticated);
    }

    function updateAuthControls() {
      setAuthShellState(authKeyShell, state.isAuthenticated);
      setAuthShellState(authPasswordShell, state.isAuthenticated);
      if (requestUserButton) {
        requestUserButton.hidden = state.isAuthenticated;
      }
      syncSettingsControls();
      syncAiAgentSettingsControls({ preserveInputs: true });
      syncRouteTimeControls();
    }

    function normalizeAuthKeyValue() {
      if (!authKeyInput) {
        return "";
      }
      const normalizedValue = String(authKeyInput.value || "")
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, "")
        .slice(0, 4);
      if (authKeyInput.value !== normalizedValue) {
        authKeyInput.value = normalizedValue;
      }
      return normalizedValue;
    }

    function clearPendingAuthVerification() {
      if (state.authVerifyTimer !== null) {
        globalScope.clearTimeout(state.authVerifyTimer);
        state.authVerifyTimer = null;
      }
    }

    function clearActiveAuthVerificationRequest() {
      if (
        state.authVerifyRequestController
        && typeof state.authVerifyRequestController.abort === "function"
      ) {
        state.authVerifyRequestController.abort();
      }
      state.authVerifyRequestController = null;
    }

    function clearPendingRealtimeRefresh() {
      if (state.realtimeRefreshTimer !== null) {
        globalScope.clearTimeout(state.realtimeRefreshTimer);
        state.realtimeRefreshTimer = null;
      }
    }

    function clearPendingRealtimeReconnect() {
      if (state.realtimeReconnectTimer !== null) {
        globalScope.clearTimeout(state.realtimeReconnectTimer);
        state.realtimeReconnectTimer = null;
      }
    }

    function queueDashboardLoad(selectedDate, options) {
      const normalizedDate = startOfLocalDay(selectedDate || dateStore.getValue());
      state.queuedDashboardLoad = {
        selectedDate: normalizedDate,
        options: Object.assign({}, state.queuedDashboardLoad ? state.queuedDashboardLoad.options : {}, options || {}),
      };
    }

    function queueDeferredDashboardLoad(selectedDate, options) {
      const normalizedDate = startOfLocalDay(selectedDate || dateStore.getValue());
      state.deferredDashboardLoad = {
        selectedDate: normalizedDate,
        options: Object.assign({}, state.deferredDashboardLoad ? state.deferredDashboardLoad.options : {}, options || {}),
      };
    }

    function clearPendingAiRoutePolling() {
      if (state.aiRoutePollingTimer !== null) {
        globalScope.clearTimeout(state.aiRoutePollingTimer);
        state.aiRoutePollingTimer = null;
      }
    }

    function resetAiRoutePollingBackoff() {
      state.aiRoutePollingAttempt = 0;
    }

    function getNextAiRoutePollDelay() {
      const delayMs = Math.min(
        TRANSPORT_AI_ROUTE_POLL_MAX_MS,
        TRANSPORT_AI_ROUTE_POLL_INTERVAL_MS * Math.pow(2, Math.max(0, state.aiRoutePollingAttempt))
      );
      state.aiRoutePollingAttempt += 1;
      return delayMs;
    }

    function isTransportPageHidden() {
      return Boolean(
        globalScope.document
        && typeof globalScope.document.visibilityState === "string"
        && globalScope.document.visibilityState === "hidden"
      );
    }

    function getTransportAuthInputSnapshot() {
      return `${authKeyInput ? String(authKeyInput.value || "") : ""}\n${authPasswordInput ? String(authPasswordInput.value || "") : ""}`;
    }

    function readTransportAuthCredentials() {
      const chave = normalizeAuthKeyValue();
      const senha = authPasswordInput ? String(authPasswordInput.value || "") : "";
      return {
        chave,
        senha,
        signature: chave.length === 4 && senha ? `${chave}\n${senha}` : "",
      };
    }

    function hasRoutineVehicleReferenceRows(dashboard) {
      return Boolean(
        dashboard
        && (
          (Array.isArray(dashboard.regular_vehicles) && dashboard.regular_vehicles.length)
          || (Array.isArray(dashboard.weekend_vehicles) && dashboard.weekend_vehicles.length)
          || (Array.isArray(dashboard.regular_vehicle_registry) && dashboard.regular_vehicle_registry.length)
          || (Array.isArray(dashboard.weekend_vehicle_registry) && dashboard.weekend_vehicle_registry.length)
        )
      );
    }

    function clearVehicleReferenceModeTimer() {
      if (state.vehicleReferenceModeTimer) {
        globalScope.clearTimeout(state.vehicleReferenceModeTimer);
        state.vehicleReferenceModeTimer = null;
      }
    }

    function clearVehicleReferenceClock() {
      clearVehicleReferenceModeTimer();
      state.dashboardGeneratedAt = "";
      state.vehicleReferenceClock = null;
    }

    function syncTransportReferenceClock(dashboard) {
      state.arriveAtWorkTime = normalizeTransportTimeValue(
        dashboard && dashboard.arrive_at_work_time,
        normalizeTransportTimeValue(state.arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME)
      );
      state.dashboardGeneratedAt = dashboard && dashboard.dashboard_generated_at
        ? String(dashboard.dashboard_generated_at)
        : "";
      state.vehicleReferenceClock = createTransportReferenceClock(state.dashboardGeneratedAt);
    }

    function scheduleVehicleReferenceModeTimer() {
      clearVehicleReferenceModeTimer();
      if (!state.dashboard || isTransportPageHidden() || !hasRoutineVehicleReferenceRows(state.dashboard)) {
        return;
      }

      const effectiveDepartureTime = getEffectiveWorkToHomeDepartureTime(state.dashboard, state.workToHomeTime);
      const delayMs = resolveNextRoutineVehicleReferenceDelayMs(
        state.vehicleReferenceClock,
        normalizeTransportTimeValue(state.arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME),
        effectiveDepartureTime
      );
      if (delayMs === null) {
        return;
      }

      state.vehicleReferenceModeTimer = globalScope.setTimeout(function () {
        state.vehicleReferenceModeTimer = null;
        if (isTransportPageHidden() || !state.dashboard) {
          return;
        }
        renderVehiclePanels();
        scheduleVehicleReferenceModeTimer();
      }, delayMs);
    }

    function closeRealtimeEventStream() {
      if (state.realtimeEventStream) {
        state.realtimeEventStream.close();
        state.realtimeEventStream = null;
      }
      state.realtimeConnected = false;
    }

    function flushDeferredDashboardLoad() {
      if (!state.deferredDashboardLoad || !state.isAuthenticated || isTransportPageHidden()) {
        return Promise.resolve(null);
      }

      const deferredLoad = state.deferredDashboardLoad;
      state.deferredDashboardLoad = null;
      return loadDashboard(deferredLoad.selectedDate, deferredLoad.options);
    }

    function scheduleRealtimeReconnect() {
      if (!state.isAuthenticated) {
        return;
      }

      state.realtimeReconnectPending = true;
      if (isTransportPageHidden()) {
        return;
      }

      clearPendingRealtimeReconnect();
      const delayMs = Math.min(
        TRANSPORT_REALTIME_RECONNECT_MAX_MS,
        TRANSPORT_REALTIME_RECONNECT_BASE_MS * Math.pow(2, Math.max(0, state.realtimeReconnectAttempt))
      );
      state.realtimeReconnectAttempt += 1;
      state.realtimeReconnectTimer = globalScope.setTimeout(function () {
        state.realtimeReconnectTimer = null;
        if (!state.isAuthenticated) {
          return;
        }
        if (isTransportPageHidden()) {
          state.realtimeReconnectPending = true;
          return;
        }
        startRealtimeUpdates();
      }, delayMs);
    }

    function stopRealtimeUpdates() {
      clearPendingRealtimeRefresh();
      clearPendingRealtimeReconnect();
      closeRealtimeEventStream();
      state.realtimeReconnectAttempt = 0;
      state.realtimeReconnectPending = false;
    }

    function requestDashboardRefresh(options) {
      const refreshOptions = options || {};
      if (!state.isAuthenticated) {
        return;
      }

      if (state.dashboardLoadPromise) {
        queueDashboardLoad(dateStore.getValue(), Object.assign({ announce: false }, refreshOptions));
        return;
      }

      if (isTransportPageHidden()) {
        queueDeferredDashboardLoad(dateStore.getValue(), Object.assign({ announce: false }, refreshOptions));
        return;
      }

      clearPendingRealtimeRefresh();
      state.realtimeRefreshTimer = globalScope.setTimeout(function () {
        state.realtimeRefreshTimer = null;
        if (state.dashboardLoadPromise) {
          queueDashboardLoad(dateStore.getValue(), Object.assign({ announce: false }, refreshOptions));
          return;
        }
        if (isTransportPageHidden()) {
          queueDeferredDashboardLoad(dateStore.getValue(), Object.assign({ announce: false }, refreshOptions));
          return;
        }
        loadDashboard(dateStore.getValue(), Object.assign({ announce: false }, refreshOptions));
      }, TRANSPORT_REALTIME_DEBOUNCE_MS);
    }

    function startRealtimeUpdates() {
      clearPendingRealtimeReconnect();
      clearPendingRealtimeRefresh();
      closeRealtimeEventStream();
      if (!state.isAuthenticated || typeof globalScope.EventSource !== "function") {
        return;
      }
      if (isTransportPageHidden()) {
        state.realtimeReconnectPending = true;
        return;
      }

      state.realtimeReconnectPending = false;
      const realtimeEventStream = new globalScope.EventSource(`${TRANSPORT_API_PREFIX}/stream`);
      state.realtimeEventStream = realtimeEventStream;
      realtimeEventStream.onopen = function () {
        if (state.realtimeEventStream !== realtimeEventStream) {
          return;
        }
        state.realtimeConnected = true;
        state.realtimeReconnectAttempt = 0;
      };
      realtimeEventStream.onmessage = function () {
        if (state.realtimeEventStream !== realtimeEventStream) {
          return;
        }
        state.realtimeConnected = true;
        requestDashboardRefresh({ announce: false });
      };
      realtimeEventStream.onerror = function () {
        if (state.realtimeEventStream !== realtimeEventStream) {
          return;
        }
        closeRealtimeEventStream();
        scheduleRealtimeReconnect();
      };
    }

    function handlePageVisibilityChange() {
      if (isTransportPageHidden()) {
        clearVehicleReferenceModeTimer();
        clearPendingRealtimeRefresh();
        clearPendingRealtimeReconnect();
        clearPendingAiRoutePolling();
        closeRealtimeEventStream();
        state.realtimeReconnectPending = state.isAuthenticated;
        return;
      }

      if (!state.isAuthenticated) {
        return;
      }

      if (state.realtimeReconnectPending || !state.realtimeEventStream) {
        startRealtimeUpdates();
      }
      if (state.dashboard) {
        renderVehiclePanels();
        scheduleVehicleReferenceModeTimer();
      }
      void flushDeferredDashboardLoad();
      if (shouldContinuePollingAiRouteRun(state.aiRouteRunStatus)) {
        queueAiRouteRunPoll(state.aiRouteRunKey, 0);
      }
    }

    function setAuthenticationState(authenticated, user, options) {
      const nextOptions = options || {};
      const wasAuthenticated = state.isAuthenticated;
      state.isAuthenticated = Boolean(authenticated);
      state.authenticatedUser = state.isAuthenticated ? user || null : null;
      updateAuthControls();

      if (state.isAuthenticated) {
        if (!wasAuthenticated || !state.realtimeEventStream) {
          startRealtimeUpdates();
        }
      } else {
        clearVehicleReferenceClock();
        state.arriveAtWorkTime = DEFAULT_ARRIVE_AT_WORK_TIME;
        stopRealtimeUpdates();
        clearPendingAiRoutePolling();
        resetAiRoutePollingBackoff();
        state.aiRouteRequestPending = false;
        state.aiRouteInBackground = false;
        state.aiRouteRunStatus = null;
        state.aiRouteRunKey = null;
        state.aiRouteSuggestion = null;
        state.deferredDashboardLoad = null;
      }

      syncAiAgentSettingsControls({ preserveInputs: true });

      if (authKeyInput) {
        if (nextOptions.resetInputs) {
          authKeyInput.value = "";
        } else if (nextOptions.fillKey && user && user.chave) {
          authKeyInput.value = user.chave;
        }
      }
      if (authPasswordInput && nextOptions.resetInputs) {
        authPasswordInput.value = "";
      }

      if (nextOptions.clearDashboard) {
        state.dashboard = null;
        state.pendingAssignmentPreview = null;
        state.dragRequestId = null;
        state.expandedVehicleKey = null;
        clearDashboard();
      }

      syncSettingsControls();
    }

    function clearTransportSession(message) {
      state.authVerifyToken += 1;
      state.authVerifySignature = "";
      state.lastVerifiedAuthSignature = "";
      clearPendingAuthVerification();
      clearActiveAuthVerificationRequest();
      state.sessionBootstrapPending = false;
      setAuthenticationState(false, null, { resetInputs: true, clearDashboard: true });
      requestJson(`${TRANSPORT_API_PREFIX}/auth/logout`, { method: "POST" }).catch(function () {});
      const normalizedMessage = String(message || "").trim();
      const sessionExpiredMessage = String(getTransportSessionExpiredMessage() || "").trim();
      const statusKey = !normalizedMessage
        ? "status.locked"
        : normalizedMessage === sessionExpiredMessage
          ? "status.sessionExpired"
          : "";
      setStatus(normalizedMessage || getTransportLockedMessage(), "warning", { key: statusKey });
    }

