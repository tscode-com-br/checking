            let reloadDate = resolveVehicleSaveReloadDate(payload, currentDashboardDate);

            closeVehicleModal();
            const structuredVehicleSavedMessage = resolveTransportApiStructuredMessage(response)
              || String(response && response.message || "").trim();
            const vehicleSavedMessage = structuredVehicleSavedMessage || t("status.vehicleSaved");
            const vehicleSavedOptions = resolveTransportApiStructuredMessageOptions(response)
              || (structuredVehicleSavedMessage ? undefined : { key: "status.vehicleSaved" });
            setStatus(vehicleSavedMessage, "success", vehicleSavedOptions);
            if (formatIsoDate(reloadDate) !== formatIsoDate(currentDashboardDate)) {
              reloadDate = setDashboardDateForSilentReload(reloadDate);
            }
            return loadDashboard(reloadDate, { announce: false });
          })
          .catch(function (error) {
            setVehicleModalFeedback(
              resolveTransportApiStructuredMessage(error && error.payload)
                || localizeTransportApiMessage(error && error.message)
                || t("status.couldNotSaveVehicle"),
              "error"
            );
            handleProtectedRequestError(error, t("status.couldNotSaveVehicle"));
          })
          .finally(function () {
            if (submitButton) {
              submitButton.disabled = false;
            }
          });
      });
    }

    function cloneTransportMessageValues(values) {
      return values && typeof values === "object" && !Array.isArray(values)
        ? Object.assign({}, values)
        : null;
    }

    function syncStatusMessageCopy(overrideDescriptor) {
      if (!statusMessage) {
        return;
      }

      const descriptor = overrideDescriptor || {};
      const statusKey = String(
        descriptor.key !== undefined ? descriptor.key : state.statusMessageKey
      ).trim();
      const statusValues = cloneTransportMessageValues(
        descriptor.values !== undefined ? descriptor.values : state.statusMessageValues
      );
      const fallbackMessage = String(
        descriptor.message !== undefined ? descriptor.message : state.statusMessageText
      ).trim();
      const statusTone = String(
        descriptor.tone !== undefined ? descriptor.tone : state.statusMessageTone
      ).trim() || "info";

      let resolvedMessage = "";
      if (statusKey) {
        const translatedStatus = t(statusKey, statusValues || undefined);
        if (translatedStatus && translatedStatus !== statusKey) {
          resolvedMessage = translatedStatus;
        } else if (fallbackMessage) {
          resolvedMessage = fallbackMessage;
        } else {
          resolvedMessage = translatedStatus;
        }
      } else {
        resolvedMessage = fallbackMessage;
      }

      if (!String(resolvedMessage || "").trim()) {
        resolvedMessage = getDefaultStatusMessage();
      }

      const normalizedDefaultStatusMessage = String(getDefaultStatusMessage() || "").trim();
      if (
        statusKey === DEFAULT_STATUS_MESSAGE_KEY
        || (!statusKey && String(resolvedMessage || "").trim() === normalizedDefaultStatusMessage)
      ) {
        statusMessage.setAttribute("data-i18n-text", DEFAULT_STATUS_MESSAGE_KEY);
      } else {
        statusMessage.removeAttribute("data-i18n-text");
      }

      statusMessage.textContent = resolvedMessage;
      statusMessage.dataset.tone = statusTone;
    }

    function setStatus(message, tone, options) {
      const statusOptions = options || {};
      const descriptor = {
        key: String(statusOptions.key || "").trim(),
        values: cloneTransportMessageValues(statusOptions.values),
        message: String(message || "").trim(),
        tone: tone || "info",
      };

      if (statusOptions.preserveState === true) {
        syncStatusMessageCopy(descriptor);
        return;
      }

      state.statusMessageKey = descriptor.key;
      state.statusMessageValues = descriptor.values;
      state.statusMessageText = descriptor.message;
      state.statusMessageTone = descriptor.tone;
      syncStatusMessageCopy();
    }

    function setVehicleModalFeedback(message, tone) {
      if (!vehicleModalFeedback) {
        return;
      }

      const nextMessage = String(message || "").trim();
      if (!nextMessage) {
        vehicleModalFeedback.hidden = true;
        vehicleModalFeedback.textContent = "";
        vehicleModalFeedback.dataset.tone = tone || "error";
        return;
      }

      vehicleModalFeedback.hidden = false;
      vehicleModalFeedback.dataset.tone = tone || "error";
      vehicleModalFeedback.textContent = nextMessage;
    }

    function clearVehicleModalFeedback() {
      setVehicleModalFeedback("", "error");
    }

    function setAiAgentFeedback(message, tone, options) {
      const feedbackOptions = options || {};
      state.aiAgentFeedbackKey = String(feedbackOptions.key || "").trim();
      state.aiAgentFeedbackValues = feedbackOptions.values && typeof feedbackOptions.values === "object"
        ? Object.assign({}, feedbackOptions.values)
        : null;
      state.aiAgentFeedbackMessage = String(message || "").trim();
      state.aiAgentFeedbackTone = tone || "info";
      syncAiAgentSettingsControls({ preserveInputs: true });
    }

    function clearAiAgentFeedback() {
      setAiAgentFeedback("", "info");
    }

    function setAiSettingsFeedback(message, tone, options) {
      const feedbackOptions = options || {};
      state.aiSettingsFeedbackKey = String(feedbackOptions.key || "").trim();
      state.aiSettingsFeedbackValues = feedbackOptions.values && typeof feedbackOptions.values === "object"
        ? Object.assign({}, feedbackOptions.values)
        : null;
      state.aiSettingsFeedbackMessage = String(message || "").trim();
      state.aiSettingsFeedbackTone = tone || "info";
      syncAiSettingsControls({ preserveInputs: true });
    }

    function clearAiSettingsFeedback() {
      setAiSettingsFeedback("", "info");
    }

    function setAiChangesSummary(message, tone, options) {
      const summaryOptions = options || {};
      state.aiChangesSummaryKey = String(summaryOptions.key || "").trim();
      state.aiChangesSummaryValues = summaryOptions.values && typeof summaryOptions.values === "object"
        ? Object.assign({}, summaryOptions.values)
        : null;
      state.aiChangesSummaryMessage = String(message || "").trim();
      state.aiChangesSummaryTone = tone || "success";
      syncAiChangesSummaryCopy();
    }

    function clearAiChangesSummary() {
      setAiChangesSummary("", "success");
    }

    function runAiSuggestionCommand(actionName) {
      const normalizedAction = String(actionName || "").trim().toLowerCase();
      const actionCopy = getAiChangesActionCopy(normalizedAction);
      if (!actionCopy) {
        return Promise.resolve(null);
      }

      if (!state.isAuthenticated) {
        setAiChangesSummary("", "warning", { key: "status.locked" });
        setStatus("", "warning", { key: "status.locked" });
        syncAiChangesControls();
        return Promise.resolve(null);
      }

      const commandState = resolveAiChangesCommandState(
        state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion },
        {
          isAuthenticated: state.isAuthenticated,
          isPending: state.aiChangesCommandPending,
          pendingAction: state.aiChangesPendingAction,
        }
      );
      const isCommandAvailable = normalizedAction === "cancel"
        ? commandState.canCancel
        : normalizedAction === "save"
          ? commandState.canSave
          : commandState.canApply;
      if (!commandState.suggestionKey || !isCommandAvailable) {
        return Promise.resolve(null);
      }

      state.aiChangesCommandPending = true;
      state.aiChangesPendingAction = normalizedAction;
      setAiChangesSummary("", "info", { key: actionCopy.busyKey });
      syncAiChangesControls();

      return requestJson(
        buildTransportAiSuggestionCommandUrl(TRANSPORT_API_PREFIX, commandState.suggestionKey, normalizedAction),
        { method: "POST" }
      )
        .then(function (response) {
          state.aiRouteRunKey = response && response.run_key
            ? response.run_key
            : state.aiRouteRunKey;
          state.aiRouteRunStatus = response || null;
          state.aiRouteSuggestion = response && response.suggestion ? response.suggestion : null;

          const structuredCommandMessage = resolveTransportApiStructuredMessage(response)
            || String(response && response.message || "").trim();
          const successMessage = structuredCommandMessage || t(actionCopy.successKey);
          const successStatusOptions = resolveTransportApiStructuredMessageOptions(response)
            || (structuredCommandMessage ? undefined : { key: actionCopy.successKey });

          closeAiChangesModal({ force: true });
          setStatus(successMessage, "success", successStatusOptions);
          if (shouldRefreshDashboardAfterAiSuggestionCommand(normalizedAction)) {
            requestDashboardRefresh({ announce: false });
          }
          return response || null;
        })
        .catch(function (error) {
          if (error && error.payload && typeof error.payload === "object") {
            state.aiRouteRunKey = error.payload.run_key || state.aiRouteRunKey;
            state.aiRouteRunStatus = error.payload;
            state.aiRouteSuggestion = error.payload.suggestion ? error.payload.suggestion : state.aiRouteSuggestion;
          }

          const resolvedMessage = resolveTransportApiStructuredMessage(error && error.payload)
            || localizeTransportApiMessage(error && error.message)
            || String(
              (error && error.payload && error.payload.message)
              || (error && error.message)
              || ""
            ).trim();
          const commandErrorOptions = resolveTransportApiStructuredMessageOptions(error && error.payload);
          setAiChangesSummary(
            resolvedMessage,
            "error",
            commandErrorOptions || (resolvedMessage ? undefined : { key: actionCopy.errorKey })
          );
          handleProtectedRequestError(error, resolvedMessage || t(actionCopy.errorKey));
          return null;
        })
        .finally(function () {
          state.aiChangesCommandPending = false;
          state.aiChangesPendingAction = "";
          syncAiChangesControls();
        });
    }

    function cancelAiSuggestion() {
      return runAiSuggestionCommand("cancel");
    }

    function saveAiSuggestion() {
      return runAiSuggestionCommand("save");
    }

    function applyAiSuggestion() {
      return runAiSuggestionCommand("apply");
    }

    function openSettingsModal() {
      if (!settingsModal) {
        return;
      }
      closeAiMenu();
      closeAiSettingsModal({ force: true });
      closeAiChangesModal();
      closeAiAgentSettingsModal();
      closeExpandedVehicleDetails({ render: false });
      if (state.isAuthenticated && !state.settingsLoaded) {
        void loadTransportSettings({ silent: true });
      }
      syncSettingsControls();
      settingsModal.hidden = false;
      if (settingsTrigger) {
        settingsTrigger.setAttribute("aria-expanded", "true");
      }
    }

    function closeSettingsModal() {
      if (!settingsModal) {
        return;
      }
      closeCurrencyCreatePanel();
      settingsModal.hidden = true;
      if (settingsTrigger) {
        settingsTrigger.setAttribute("aria-expanded", "false");
        if (typeof settingsTrigger.focus === "function") {
          settingsTrigger.focus();
        }
      }
    }

    function loadTransportAiSettingsProjectCatalog(options) {
      const loadOptions = options || {};
      const preferredProjectId = normalizeTransportAiSettingsProjectId(loadOptions.preferredProjectId, null);
      const cachedProjects = normalizeTransportAiSettingsProjectRows(state.aiSettingsProjects);
      if (
        !loadOptions.forceRefresh
        && getTransportAiSettingsProjectCatalogStatus() === AI_SETTINGS_PROJECT_CATALOG_STATUS.ready
        && cachedProjects.length
      ) {
        applyTransportAiSettingsProjects(cachedProjects, preferredProjectId);
        return Promise.resolve(cachedProjects);
      }

      const bootstrapProjects = normalizeTransportAiSettingsProjectRows(getTransportAiSettingsProjectRows());
      if (bootstrapProjects.length) {
        applyTransportAiSettingsProjects(bootstrapProjects, preferredProjectId);
      } else {
        clearTransportAiSettingsProjectSelection();
      }
      setTransportAiSettingsProjectCatalogStatus(AI_SETTINGS_PROJECT_CATALOG_STATUS.loading);

      return requestJson(`${TRANSPORT_API_PREFIX}/projects`)
        .then(function (projectRows) {
          const normalizedProjects = normalizeTransportAiSettingsProjectRows(projectRows);
          applyTransportAiSettingsProjects(normalizedProjects, preferredProjectId);
          setTransportAiSettingsProjectCatalogStatus(
            normalizedProjects.length
              ? AI_SETTINGS_PROJECT_CATALOG_STATUS.ready
              : AI_SETTINGS_PROJECT_CATALOG_STATUS.empty
          );
          return normalizedProjects;
        })
        .catch(function (error) {
          const handledProtectedError = handleProtectedRequestError(error, t("ai.settingsProjectLoadFailed"));
          const resolvedMessage = resolveTransportApiStructuredMessage(error && error.payload)
            || localizeTransportApiMessage(error && error.message)
            || (handledProtectedError ? getTransportSessionExpiredMessage() : t("ai.settingsProjectLoadFailed"));
          const fallbackProjects = normalizeTransportAiSettingsProjectRows(state.aiSettingsProjects);
          const projectCatalogErrorOptions = resolveTransportApiStructuredMessageOptions(error && error.payload)
            || (resolvedMessage ? undefined : { key: "ai.settingsProjectLoadFailed" });
          setAiSettingsFeedback(resolvedMessage, handledProtectedError ? "warning" : "error", projectCatalogErrorOptions);
          if (fallbackProjects.length) {
            applyTransportAiSettingsProjects(fallbackProjects, preferredProjectId);
          } else {
            clearTransportAiSettingsProjectSelection();
            state.aiSettingsProjects = [];
          }
          setTransportAiSettingsProjectCatalogStatus(AI_SETTINGS_PROJECT_CATALOG_STATUS.error);
          return null;
        });
    }

    function loadTransportAiSettings(options) {
      const loadOptions = options || {};
      if (!state.isAuthenticated) {
        clearTransportAiSettingsProjectSelection();
        setTransportAiSettingsProjectCatalogStatus(AI_SETTINGS_PROJECT_CATALOG_STATUS.idle);
        setAiSettingsFeedback("", "warning", { key: "status.locked" });
        syncAiSettingsControls();
        return Promise.resolve(null);
      }

      const loadRequestSequence = ++aiSettingsLoadRequestSequence;
      state.aiSettingsLoading = true;
      setAiSettingsFeedback("", "info", { key: "ai.settingsLoading" });
      syncAiSettingsControls({ preserveInputs: true });
      return loadTransportAiSettingsProjectCatalog({
        preferredProjectId: state.aiSettingsSelectedProjectId,
        forceRefresh: loadOptions.forceProjectCatalogRefresh === true,
      })
        .then(function (projectRows) {
          if (loadRequestSequence !== aiSettingsLoadRequestSequence || projectRows === null) {
            return null;
          }

          if (getTransportAiSettingsProjectCatalogStatus() === AI_SETTINGS_PROJECT_CATALOG_STATUS.error) {
            return null;
          }

          const selectedProject = getSelectedTransportAiSettingsProject();
          if (!selectedProject) {
            const requestedProjectId = normalizeTransportAiSettingsProjectId(state.aiSettingsSelectedProjectId, null);
            clearTransportAiSettingsProjectSelection();
            if (getTransportAiSettingsProjectCatalogStatus() === AI_SETTINGS_PROJECT_CATALOG_STATUS.empty) {
              setAiSettingsFeedback("", "warning", { key: "ai.settingsNoProjectsAvailable" });
            } else if (requestedProjectId) {
              setAiSettingsFeedback("", "warning", { key: "ai.settingsProjectMissing" });
            }
            return null;
          }

          state.aiSettingsDraft = readTransportAiSettingsDraft(
            {
              projectId: selectedProject.id,
              provider: DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER,
              apiKey: "",
              mapsApiKey: "",
            },
            getDefaultTransportAiSettingsDraft()
          );
          state.aiSettingsLoadedProvider = DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER;
          state.aiSettingsHasApiKey = false;
          state.aiSettingsApiKeyHint = "";
          state.aiSettingsHasMapsApiKey = false;
          state.aiSettingsMapsApiKeyHint = "";
          syncAiSettingsControls();
          return requestJson(buildTransportAiSettingsUrl(selectedProject.id));
        })
        .then(function (response) {
          if (loadRequestSequence !== aiSettingsLoadRequestSequence || !response) {
            return response || null;
          }

          const selectedProject = getSelectedTransportAiSettingsProject();
          if (!selectedProject) {
            return null;
          }

          const normalizedProvider = normalizeTransportAiSettingsProvider(
            response && response.provider,
            DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER
          );
          state.aiSettingsDraft = readTransportAiSettingsDraft(
            {
              projectId: selectedProject.id,
              provider: normalizedProvider,
              apiKey: "",
              mapsApiKey: "",
            },
            getDefaultTransportAiSettingsDraft()
          );
          state.aiSettingsLoadedProvider = normalizedProvider;
          state.aiSettingsHasApiKey = Boolean(response && response.has_api_key);
          state.aiSettingsApiKeyHint = String(response && response.api_key_hint || "").trim();
          state.aiSettingsHasMapsApiKey = Boolean(response && response.has_here_api_key);
          state.aiSettingsMapsApiKeyHint = String(response && response.here_api_key_hint || "").trim();
          clearAiSettingsFeedback();
          return response || null;
        })
        .catch(function (error) {
          if (loadRequestSequence !== aiSettingsLoadRequestSequence) {
            return null;
          }
          const handledProtectedError = handleProtectedRequestError(error, t("ai.settingsLoadFailed"));
          const errorState = resolveTransportAiSettingsApiErrorState(error, {
            projectId: state.aiSettingsSelectedProjectId,
            projectRows: state.aiSettingsProjects,
          });
          if (errorState.markCatalogAsError) {
            setTransportAiSettingsProjectCatalogStatus(AI_SETTINGS_PROJECT_CATALOG_STATUS.error);
          }
          if (errorState.clearProjectSelection) {
            clearTransportAiSettingsProjectSelection();
          }
          const resolvedMessage = errorState.message
            || (handledProtectedError ? getTransportSessionExpiredMessage() : t("ai.settingsLoadFailed"));
          const aiSettingsLoadErrorOptions = resolveTransportApiStructuredMessageOptions(error && error.payload)
            || (resolvedMessage ? undefined : { key: "ai.settingsLoadFailed" });
          setAiSettingsFeedback(resolvedMessage, handledProtectedError ? "warning" : "error", aiSettingsLoadErrorOptions);
          return null;
        })
        .finally(function () {
          if (loadRequestSequence !== aiSettingsLoadRequestSequence) {
            return;
          }
          state.aiSettingsLoading = false;
          syncAiSettingsControls();
        });
    }

    function saveTransportAiSettings() {
      if (!state.isAuthenticated) {
        setAiSettingsFeedback("", "warning", { key: "status.locked" });
        setStatus("", "warning", { key: "status.locked" });
        syncAiSettingsControls({ preserveInputs: true });
        return Promise.resolve(null);
      }

      if (getTransportAiSettingsProjectCatalogStatus() !== AI_SETTINGS_PROJECT_CATALOG_STATUS.ready) {
        setAiSettingsFeedback("", "warning", { key: "ai.settingsProjectLoadFailed" });
        syncAiSettingsControls({ preserveInputs: true });
        return Promise.resolve(null);
      }

      const draft = readTransportAiSettingsDraft(
        {
          projectInput: aiSettingsProjectInput,
          providerInput: aiSettingsProviderInput,
          apiKeyInput: aiSettingsApiKeyInput,
          mapsApiKeyInput: aiSettingsMapsApiKeyInput,
        },
        state.aiSettingsDraft || getDefaultTransportAiSettingsDraft()
      );
      const hasValidProjectSelection = hasValidTransportAiSettingsProjectSelection(
        draft.projectId,
        state.aiSettingsProjects
      );
      if (!draft.projectId) {
        setAiSettingsFeedback("", "warning", { key: "ai.settingsProjectRequired" });
        syncAiSettingsControls({ preserveInputs: true });
        return Promise.resolve(null);
      }
      if (!hasValidProjectSelection) {
        state.aiSettingsSelectedProjectId = null;
        state.aiSettingsDraft = readTransportAiSettingsDraft(
          {
            projectId: null,
            provider: draft.provider,
            apiKey: draft.apiKey,
            mapsApiKey: draft.mapsApiKey,
          },
          getDefaultTransportAiSettingsDraft()
        );
        setAiSettingsFeedback("", "warning", { key: "ai.settingsProjectMissing" });
        syncAiSettingsControls({ preserveInputs: true });
        return Promise.resolve(null);
      }
      state.aiSettingsDraft = draft;
      state.aiSettingsSelectedProjectId = draft.projectId;
      state.aiSettingsSaving = true;
      setAiSettingsFeedback("", "info", { key: "ai.settingsSaving" });
      syncAiSettingsControls({ preserveInputs: true });

      return requestJson(`${TRANSPORT_API_PREFIX}/ai/settings`, {
        method: "PUT",
        body: JSON.stringify(buildTransportAiSettingsUpdatePayload(draft)),
      })
        .then(function (response) {
          state.aiSettingsDraft = getDefaultTransportAiSettingsDraft();
          state.aiSettingsSelectedProjectId = normalizeTransportAiSettingsProjectId(
            response && response.project_id,
            draft.projectId
          );
          state.aiSettingsLoadedProvider = normalizeTransportAiSettingsProvider(
            response && response.provider,
            draft.provider
          );
          state.aiSettingsHasApiKey = Boolean(response && response.has_api_key);
          state.aiSettingsApiKeyHint = String(response && response.api_key_hint || "").trim();
          state.aiSettingsHasMapsApiKey = Boolean(response && response.has_here_api_key);
          state.aiSettingsMapsApiKeyHint = String(response && response.here_api_key_hint || "").trim();
          clearAiSettingsFeedback();
          const structuredAiSettingsSavedMessage = resolveTransportApiStructuredMessage(response)
            || String(response && response.message || "").trim();
          const aiSettingsSavedMessage = structuredAiSettingsSavedMessage || t("ai.settingsSaved");
          const aiSettingsSavedOptions = resolveTransportApiStructuredMessageOptions(response)
            || (structuredAiSettingsSavedMessage ? undefined : { key: "ai.settingsSaved" });
          setStatus(aiSettingsSavedMessage, "success", aiSettingsSavedOptions);
          closeAiSettingsModal({ force: true, restoreFocus: true });
          return response || null;
        })
        .catch(function (error) {
          const handledProtectedError = handleProtectedRequestError(error, t("ai.settingsSaveFailed"));
          const errorState = resolveTransportAiSettingsApiErrorState(error, {
            projectId: draft.projectId,
            projectRows: state.aiSettingsProjects,
          });
          if (errorState.markCatalogAsError) {
            setTransportAiSettingsProjectCatalogStatus(AI_SETTINGS_PROJECT_CATALOG_STATUS.error);
          }
          if (errorState.clearProjectSelection) {
            clearTransportAiSettingsProjectSelection();
          }
          const resolvedMessage = errorState.message
            || (handledProtectedError ? getTransportSessionExpiredMessage() : t("ai.settingsSaveFailed"));
          const aiSettingsSaveErrorOptions = resolveTransportApiStructuredMessageOptions(error && error.payload)
            || (resolvedMessage ? undefined : { key: "ai.settingsSaveFailed" });
          setAiSettingsFeedback(resolvedMessage, handledProtectedError ? "warning" : "error", aiSettingsSaveErrorOptions);
          return null;
        })
        .finally(function () {
          state.aiSettingsSaving = false;
          syncAiSettingsControls({ preserveInputs: true });
        });
    }

    function openAiSettingsModal() {
      if (!aiSettingsModal) {
        return;
      }
      closeAiMenu();
      closeAiChangesModal({ force: true });
      closeAiAgentSettingsModal({ force: true });
      closeExpandedVehicleDetails({ render: false });
      const selectedProject = applyTransportAiSettingsProjects(
        getTransportAiSettingsProjectRows(),
        state.aiSettingsSelectedProjectId
      );
      setTransportAiSettingsProjectCatalogStatus(AI_SETTINGS_PROJECT_CATALOG_STATUS.loading);
      state.aiSettingsDraft = readTransportAiSettingsDraft(
        {
          projectId: selectedProject ? selectedProject.id : null,
          provider: DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER,
          apiKey: "",
          mapsApiKey: "",
        },
        getDefaultTransportAiSettingsDraft()
      );
      state.aiSettingsLoadedProvider = DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER;
      state.aiSettingsHasApiKey = false;
      state.aiSettingsApiKeyHint = "";
      state.aiSettingsHasMapsApiKey = false;
      state.aiSettingsMapsApiKeyHint = "";
      clearAiSettingsFeedback();
      applyStaticTranslations();
      syncAiSettingsControls();
      aiSettingsModal.hidden = false;
      if (aiSettingsProjectInput && typeof aiSettingsProjectInput.focus === "function") {
        aiSettingsProjectInput.focus();
      } else if (aiSettingsProviderInput && typeof aiSettingsProviderInput.focus === "function") {
        aiSettingsProviderInput.focus();
      }
      void loadTransportAiSettings({ forceProjectCatalogRefresh: true });
    }

    function closeAiSettingsModal(options) {
      if (!aiSettingsModal) {
        return;
      }
      const closeOptions = options || {};
      if (!closeOptions.force && state.aiSettingsSaving) {
        return;
      }

      state.aiSettingsDraft = getDefaultTransportAiSettingsDraft();
      state.aiSettingsLoadedProvider = DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER;
      state.aiSettingsHasApiKey = false;
      state.aiSettingsApiKeyHint = "";
      state.aiSettingsHasMapsApiKey = false;
      state.aiSettingsMapsApiKeyHint = "";
      clearAiSettingsFeedback();
      aiSettingsModal.hidden = true;
      if (
        closeOptions.restoreFocus
        && aiMenuTrigger
        && typeof aiMenuTrigger.focus === "function"
      ) {
        aiMenuTrigger.focus();
      }
    }

    function focusAiAgentSettingsField(fieldName) {
      const fieldElement = fieldName === "arrivalAtWorkTime"
        ? aiAgentArrivalAtWorkInput
        : fieldName === "requestKinds"
          ? aiAgentRequestKindInputs[0]
          : aiAgentEarliestBoardingInput;
      if (fieldElement && typeof fieldElement.focus === "function") {
        fieldElement.focus();
      }
    }

    function openAiChangesModal(runStatusResponse) {
      state.aiRouteRunStatus = runStatusResponse || state.aiRouteRunStatus;
      state.aiRouteRunKey = runStatusResponse && runStatusResponse.run_key
        ? runStatusResponse.run_key
        : state.aiRouteRunKey;
      state.aiRouteSuggestion = runStatusResponse && runStatusResponse.suggestion
        ? runStatusResponse.suggestion
        : state.aiRouteSuggestion;
      state.aiChangesCommandPending = false;
      state.aiChangesPendingAction = "";

      const readyMessage = resolveTransportApiStructuredMessage(runStatusResponse)
        || String(runStatusResponse && runStatusResponse.message || "").trim();
      const readyMessageOptions = resolveTransportApiStructuredMessageOptions(runStatusResponse);

      closeAiSettingsModal({ force: true });
      closeAiAgentSettingsModal({ force: true });
      setAiChangesSummary(
        readyMessage,
        "success",
        readyMessageOptions || (readyMessage ? undefined : { key: "ai.agentSettingsReadyForReview" })
      );
      if (aiChangesModal) {
        applyStaticTranslations();
        aiChangesModal.hidden = false;
        const closeButton = aiChangesModal.querySelector("[data-close-ai-changes-modal]");
        if (closeButton && typeof closeButton.focus === "function") {
          closeButton.focus();
        }
      }
      const readyStatusMessage = readyMessage || t("ai.agentSettingsReadyForReview");
      setStatus(
        readyStatusMessage,
        "success",
        readyMessageOptions || (readyMessage ? undefined : { key: "ai.agentSettingsReadyForReview" })
      );
    }

    function closeAiChangesModal(options) {
      if (!aiChangesModal) {
        return;
      }
      const closeOptions = options || {};
      if (!closeOptions.force && state.aiChangesCommandPending) {
        return;
      }
      aiChangesModal.hidden = true;
      clearAiChangesSummary();
      if (
        closeOptions.restoreFocus
        && aiMenuTrigger
        && typeof aiMenuTrigger.focus === "function"
      ) {
        aiMenuTrigger.focus();
      }
    }

    function loadLatestAiSuggestion() {
      closeAiMenu();

      if (!state.isAuthenticated) {
        setStatus("", "warning", { key: "status.locked" });
        syncAiMenuControls();
        return Promise.resolve(null);
      }

      const latestSuggestionUrl = buildTransportAiLatestSuggestionUrl(
        TRANSPORT_API_PREFIX,
        getCurrentServiceDateIso(),
        getSelectedRouteKind()
      );
      if (!latestSuggestionUrl) {
        setStatus("", "error", { key: "ai.loadLatestSuggestionFailed" });
        return Promise.resolve(null);
      }

      state.aiLatestSuggestionLoading = true;
      syncAiMenuControls();

      return requestJson(latestSuggestionUrl)
        .then(function (response) {
          state.aiRouteRunKey = response && response.run_key ? response.run_key : state.aiRouteRunKey;
          state.aiRouteRunStatus = response || null;
          state.aiRouteSuggestion = response && response.suggestion ? response.suggestion : null;
          openAiChangesModal(response);
          return response || null;
        })
        .catch(function (error) {
          if (error && Number(error.status) === 404) {
            setStatus("", "info", { key: "ai.noSavedSuggestion" });
            return null;
          }

          handleProtectedRequestError(
            error,
            resolveTransportApiStructuredMessage(error && error.payload)
              || localizeTransportApiMessage(error && error.message)
              || t("ai.loadLatestSuggestionFailed")
          );
          return null;
        })
        .finally(function () {
          state.aiLatestSuggestionLoading = false;
          syncAiMenuControls();
        });
    }

    function queueAiRouteRunPoll(runKey, delayMs) {
      clearPendingAiRoutePolling();
      if (!runKey) {
        resetAiRoutePollingBackoff();
        syncAiAgentSettingsControls({ preserveInputs: true });
        return;
      }

      if (isTransportPageHidden()) {
        syncAiAgentSettingsControls({ preserveInputs: true });
        return;
      }

      const normalizedDelayMs = Math.max(0, Number(delayMs) || 0);
      if (normalizedDelayMs <= 0) {
        resetAiRoutePollingBackoff();
      }

      state.aiRoutePollingTimer = globalScope.setTimeout(function () {
        state.aiRoutePollingTimer = null;
        void pollAiRouteRun(runKey);
      }, normalizedDelayMs);
      syncAiAgentSettingsControls({ preserveInputs: true });
    }

    function pollAiRouteRun(runKey) {
      const normalizedRunKey = String(runKey || "").trim();
      if (!normalizedRunKey) {
        resetAiRoutePollingBackoff();
        return Promise.resolve(null);
      }

      if (isTransportPageHidden()) {
        syncAiAgentSettingsControls({ preserveInputs: true });
        return Promise.resolve(null);
      }

      clearPendingAiRoutePolling();
      return requestJson(`${TRANSPORT_API_PREFIX}/ai/route-calculations/${encodeURIComponent(normalizedRunKey)}`)
        .then(function (response) {
          state.aiRouteRunKey = response && response.run_key ? response.run_key : normalizedRunKey;
          state.aiRouteRunStatus = response || null;
          state.aiRouteSuggestion = response && response.suggestion ? response.suggestion : null;

          const responseMessage = resolveTransportApiStructuredMessage(response)
            || String(response && response.message || "").trim();
          const responseMessageOptions = resolveTransportApiStructuredMessageOptions(response);
          if (hasRenderableTransportAiReview(response)) {
            resetAiRoutePollingBackoff();
            state.aiRouteInBackground = false;
            setAiAgentFeedback(
              responseMessage,
              "success",
              responseMessageOptions || (responseMessage ? undefined : { key: "ai.agentSettingsReadyForReview" })
            );
            requestDashboardRefresh({ announce: false });
            if (!aiAgentModal || aiAgentModal.hidden) {
              // Modal foi fechado (modo background) — não abrir automaticamente, só exibir botão verde
              syncAiMenuControls();
            } else {
              openAiChangesModal(response);
            }
            return response;
          }

          if (!response || response.ok === false || String(response.status || "").trim().toLowerCase() === "failed") {
            resetAiRoutePollingBackoff();
            state.aiRouteInBackground = false;
            const errorMessage = resolveTransportAiStructuredMessage(response);
            const baselineComplement = resolveTransportAiBaselineComplement(response);
            const displayMessage = baselineComplement ? errorMessage + " " + baselineComplement : errorMessage;
            setAiAgentFeedback(
              displayMessage,
              "error",
              responseMessageOptions || (displayMessage ? undefined : { key: "ai.routeCalculationFailed" })
            );
            return response || null;
          }

          const isPolling = shouldContinuePollingAiRouteRun(response);
          const pollingDisplayMessage = isPolling
            ? getAiRoutePollingStatusLabel(response && response.status)
            : responseMessage;
          if (!state.aiRouteInBackground) {
            setAiAgentFeedback(
              pollingDisplayMessage,
              isPolling ? "warning" : "success",
              isPolling ? undefined : (responseMessageOptions || (responseMessage ? undefined : { key: "ai.agentSettingsSubmitting" }))
            );
          }
          if (isPolling) {
            queueAiRouteRunPoll(state.aiRouteRunKey, getNextAiRoutePollDelay());
          } else {
            resetAiRoutePollingBackoff();
          }
          return response;
        })
        .catch(function (error) {
          resetAiRoutePollingBackoff();
          state.aiRouteInBackground = false;
          const fallbackErrorMessage = t("ai.routeCalculationFailed");
          const resolvedMessage = resolveTransportApiStructuredMessage(error && error.payload)
            || localizeTransportApiMessage(error && error.message)
            || String(error && error.message || "").trim();
          const pollErrorOptions = resolveTransportApiStructuredMessageOptions(error && error.payload);
          setAiAgentFeedback(
            resolvedMessage,
            "error",
            pollErrorOptions || (resolvedMessage ? undefined : { key: "ai.routeCalculationFailed" })
          );
          handleProtectedRequestError(error, resolvedMessage || fallbackErrorMessage);
          return null;
        })
        .finally(function () {
          syncAiAgentSettingsControls({ preserveInputs: true });
        });
    }

    function requestAiRoutes() {
      if (!state.isAuthenticated) {
        setAiAgentFeedback("", "warning", { key: "status.locked" });
        setStatus("", "warning", { key: "status.locked" });
        syncAiAgentSettingsControls({ preserveInputs: true });
        return Promise.resolve(null);
      }

      const draft = readAiAgentSettingsDraft(
        {
          earliestBoardingInput: aiAgentEarliestBoardingInput,
          arrivalAtWorkInput: aiAgentArrivalAtWorkInput,
          requestKindInputs: aiAgentRequestKindInputs,
          minOccInputs: aiAgentMinOccInputs,
        },
        state.aiAgentSettingsDraft || getDefaultAiAgentSettings()
      );
      state.aiAgentSettingsDraft = draft;

      const validation = validateAiAgentSettingsDraft(draft);
      if (!validation.ok) {
        setAiAgentFeedback("", "error", { key: validation.messageKey });
        focusAiAgentSettingsField(validation.field);
        return Promise.resolve(null);
      }

      const dashboardScope = buildTransportAiDashboardScope(
        getProjectRows(),
        state.projectVisibility,
        validation.draft.requestKinds
      );
      if (dashboardScope && Array.isArray(dashboardScope.project_ids) && !dashboardScope.project_ids.length) {
        setAiAgentFeedback("", "error", { key: "ai.agentSettingsNoProjectsSelected" });
        setStatus("", "error", { key: "ai.agentSettingsNoProjectsSelected" });
        syncAiAgentSettingsControls({ preserveInputs: true });
        return Promise.resolve(null);
      }

      state.aiAgentSettingsDraft = validation.draft;
      state.aiRouteRunKey = null;
      state.aiRouteRunStatus = null;
      state.aiRouteSuggestion = null;
      resetAiRoutePollingBackoff();
      state.aiRouteRequestPending = true;
      clearPendingAiRoutePolling();
      setAiAgentFeedback("", "info", buildAiAgentSubmittingFeedbackOptions(validation.draft.requestKinds));
      syncAiAgentSettingsControls({ preserveInputs: true });

      const payload = buildTransportAiRouteCalculationPayload(
        getCurrentServiceDateIso(),
        getSelectedRouteKind(),
        validation.draft,
        dashboardScope
      );

      return requestJson(`${TRANSPORT_API_PREFIX}/ai/route-calculations`, {
        method: "POST",
        body: JSON.stringify(payload),
      })
        .then(function (response) {
          state.aiRouteRunKey = response && response.run_key ? response.run_key : null;
          state.aiRouteRunStatus = response || null;
          state.aiRouteSuggestion = null;

          if (state.aiRouteRunKey) {
            // 202 response: fire-and-poll mode — calculation runs in background
            state.aiRouteInBackground = true;
            setAiAgentFeedback(
              "As rotas ser\u00e3o calculadas em segundo plano. Clique em 'IA \u203a Implementar Modifica\u00e7\u00f5es' para ver os resultados quando o bot\u00e3o 'IA' estiver verde.",
              "info"
            );
            syncAiAgentSettingsControls({ preserveInputs: true });
            syncAiMenuControls();
            return pollAiRouteRun(state.aiRouteRunKey);
          }

          const responseMessage = resolveTransportApiStructuredMessage(response)
            || String(response && response.message || "").trim();
          const responseMessageOptions = resolveTransportApiStructuredMessageOptions(response);
          setAiAgentFeedback(
            responseMessage,
            response && response.suggestion_ready ? "success" : "warning",
            responseMessageOptions || (responseMessage ? undefined : { key: "ai.agentSettingsSubmitting" })
          );
          return response || null;
        })
        .catch(function (error) {
          const fallbackErrorMessage = t("ai.routeCalculationFailed");
          state.aiRouteRunKey = error && error.payload && error.payload.run_key
            ? error.payload.run_key
            : null;
          state.aiRouteRunStatus = error && error.payload ? error.payload : null;
          state.aiRouteSuggestion = null;
          const errorPayload = error && error.payload ? error.payload : null;
          const structuredStartMessage = errorPayload
            ? resolveTransportAiStructuredMessage(errorPayload)
            : (resolveTransportApiStructuredMessage(error && error.payload)
               || localizeTransportApiMessage(error && error.message)
               || String(error && error.message || "").trim());
          const startBaselineComplement = errorPayload ? resolveTransportAiBaselineComplement(errorPayload) : null;
          const resolvedMessage = startBaselineComplement
            ? structuredStartMessage + " " + startBaselineComplement
            : structuredStartMessage;
          const routeStartErrorOptions = resolveTransportApiStructuredMessageOptions(error && error.payload);
          setAiAgentFeedback(
            resolvedMessage,
            "error",
            routeStartErrorOptions || (resolvedMessage ? undefined : { key: "ai.routeCalculationFailed" })
          );
          handleProtectedRequestError(error, resolvedMessage || fallbackErrorMessage);
          return null;
        })
