    function bootstrapTransportSession() {
      const initialAuthInputSnapshot = getTransportAuthInputSnapshot();
      state.sessionBootstrapPending = true;
      return requestJson(`${TRANSPORT_API_PREFIX}/auth/session`)
        .then(function (response) {
          const authDraftChanged = getTransportAuthInputSnapshot() !== initialAuthInputSnapshot;
          if (response && response.authenticated && response.user) {
            setAuthenticationState(true, response.user, { fillKey: !authDraftChanged });
            setStatus("", "info", { key: DEFAULT_STATUS_MESSAGE_KEY });
            return Promise.all([
              loadDashboard(dateStore.getValue(), { announce: false }),
              loadTransportSettings({ silent: true }),
            ]);
          }

          setAuthenticationState(false, null, { resetInputs: !authDraftChanged, clearDashboard: true });
          setStatus("", "warning", { key: "status.locked" });
          return null;
        })
        .catch(function () {
          const authDraftChanged = getTransportAuthInputSnapshot() !== initialAuthInputSnapshot;
          setAuthenticationState(false, null, { resetInputs: !authDraftChanged, clearDashboard: true });
          setStatus("", "warning", { key: "status.locked" });
          return null;
        })
        .finally(function () {
          state.sessionBootstrapPending = false;
          scheduleTransportVerification({ source: "bootstrap" });
        });
    }

    if (authKeyInput) {
      authKeyInput.addEventListener("input", function () {
        scheduleTransportVerification({ source: "input" });
      });
      authKeyInput.addEventListener("change", function () {
        scheduleTransportVerification({ source: "change", immediate: true });
      });
      authKeyInput.addEventListener("blur", function () {
        scheduleTransportVerification({ source: "blur", immediate: true });
      });
      authKeyInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          scheduleTransportVerification({ source: "enter", immediate: true });
        }
      });
    }

    if (authPasswordInput) {
      authPasswordInput.addEventListener("input", function () {
        scheduleTransportVerification({ source: "input" });
      });
      authPasswordInput.addEventListener("change", function () {
        scheduleTransportVerification({ source: "change", immediate: true });
      });
      authPasswordInput.addEventListener("blur", function () {
        scheduleTransportVerification({ source: "blur", immediate: true });
      });
      authPasswordInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          scheduleTransportVerification({ source: "enter", immediate: true });
        }
      });
    }

    if (globalScope.document && typeof globalScope.document.addEventListener === "function") {
      globalScope.document.addEventListener("visibilitychange", function () {
        if (isTransportPageHidden()) {
          clearPendingRealtimeRefresh();
          clearPendingAiRoutePolling();
          return;
        }

        if (state.aiRouteRunKey && shouldContinuePollingAiRouteRun(state.aiRouteRunStatus)) {
          queueAiRouteRunPoll(state.aiRouteRunKey, 0);
        }
        requestDashboardRefresh({ announce: false });
      });
    }

    if (requestUserButton) {
      requestUserButton.addEventListener("click", openUserCreationRequest);
    }

    if (settingsLanguageSelect) {
      settingsLanguageSelect.addEventListener("change", function () {
        void switchTransportLanguage(settingsLanguageSelect.value);
      });
    }

    if (settingsArriveAtWorkInput) {
      settingsArriveAtWorkInput.addEventListener("change", function () {
        void saveTransportSettings(readTransportSettingsDraft());
      });
    }

    if (settingsTimeInput) {
      settingsTimeInput.addEventListener("change", function () {
        void saveTransportSettings(readTransportSettingsDraft());
      });
    }

    if (settingsExtraCarToleranceInput) {
      settingsExtraCarToleranceInput.addEventListener("change", function () {
        void saveTransportSettings(readTransportSettingsDraft());
      });
    }

    if (settingsLastUpdateInput) {
      settingsLastUpdateInput.addEventListener("change", function () {
        void saveTransportSettings(readTransportSettingsDraft());
      });
    }

    if (settingsPriceCurrencySelect) {
      settingsPriceCurrencySelect.addEventListener("change", function () {
        void saveTransportSettings(readTransportSettingsDraft());
      });
    }

    if (settingsPriceRateUnitSelect) {
      settingsPriceRateUnitSelect.addEventListener("change", function () {
        void saveTransportSettings(readTransportSettingsDraft());
      });
    }

    Object.keys(settingsDefaultSeatInputs).forEach(function (vehicleType) {
      const seatInput = settingsDefaultSeatInputs[vehicleType];
      if (!seatInput) {
        return;
      }
      seatInput.addEventListener("change", function () {
        void saveTransportSettings(readTransportSettingsDraft());
      });
    });

    Object.keys(settingsDefaultPriceInputs).forEach(function (vehicleType) {
      const priceInput = settingsDefaultPriceInputs[vehicleType];
      if (!priceInput) {
        return;
      }
      priceInput.addEventListener("change", function () {
        void saveTransportSettings(readTransportSettingsDraft());
      });
    });

    if (settingsDefaultToleranceInput) {
      settingsDefaultToleranceInput.addEventListener("change", function () {
        void saveTransportSettings(readTransportSettingsDraft());
      });
    }

    if (settingsAddCurrencyButton) {
      settingsAddCurrencyButton.addEventListener("click", function () {
        if (state.currencyCreateOpen) {
          closeCurrencyCreatePanel();
          return;
        }
        openCurrencyCreatePanel();
      });
    }

    if (settingsCancelCurrencyButton) {
      settingsCancelCurrencyButton.addEventListener("click", function () {
        closeCurrencyCreatePanel();
      });
    }

    if (settingsSaveCurrencyButton) {
      settingsSaveCurrencyButton.addEventListener("click", function () {
        void saveTransportCurrencyOption();
      });
    }

    if (routeTimeInput) {
      routeTimeInput.addEventListener("change", function () {
        void saveRouteTimeForSelectedDate(routeTimeInput.value);
      });
    }

    populateLanguageOptions();
    applyStaticTranslations();
    syncSettingsControls();
    syncRouteTimeControls();
    syncAiMenuControls();

    if (aiMenuShell) {
      aiMenuShell.addEventListener("click", function (event) {
        event.stopPropagation();
      });
    }

    if (aiMenuTrigger) {
      aiMenuTrigger.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        toggleAiMenu();
      });
    }

    if (aiCalculateRoutesButton) {
      aiCalculateRoutesButton.addEventListener("click", function (event) {
        event.preventDefault();
        openAiAgentSettingsModal();
      });
    }

    if (aiImplementModificationsButton) {
      aiImplementModificationsButton.addEventListener("click", function (event) {
        event.preventDefault();
        void loadLatestAiSuggestion();
      });
    }

    if (aiSettingsMenuButton) {
      aiSettingsMenuButton.addEventListener("click", function (event) {
        event.preventDefault();
        openAiSettingsModal();
      });
    }

    document.addEventListener("click", function (event) {
      if (!state.aiMenuOpen || !aiMenuShell) {
        return;
      }
      if (aiMenuShell.contains(event.target)) {
        return;
      }
      closeAiMenu();
    });

    if (settingsTrigger) {
      settingsTrigger.addEventListener("click", function (event) {
        event.preventDefault();
        openSettingsModal();
      });
    }

    document.querySelectorAll("[data-close-settings-modal]").forEach(function (buttonElement) {
      buttonElement.addEventListener("click", closeSettingsModal);
    });

    document.querySelectorAll("[data-close-ai-settings-modal]").forEach(function (buttonElement) {
      buttonElement.addEventListener("click", closeAiSettingsModal);
    });
    document.querySelectorAll("[data-ai-settings-save]").forEach(function (buttonElement) {
      buttonElement.addEventListener("click", function () {
        void saveTransportAiSettings();
      });
    });

    document.querySelectorAll("[data-close-ai-agent-modal]").forEach(function (buttonElement) {
      buttonElement.addEventListener("click", closeAiAgentSettingsModal);
    });
    document.querySelectorAll("[data-close-ai-changes-modal]").forEach(function (buttonElement) {
      buttonElement.addEventListener("click", closeAiChangesModal);
    });
    document.querySelectorAll("[data-ai-changes-cancel]").forEach(function (buttonElement) {
      buttonElement.addEventListener("click", function () {
        closeAiChangesModal({ restoreFocus: true });
      });
    });
    document.querySelectorAll("[data-ai-changes-discard]").forEach(function (buttonElement) {
      buttonElement.addEventListener("click", function () {
        void cancelAiSuggestion();
      });
    });
    document.querySelectorAll("[data-ai-changes-save]").forEach(function (buttonElement) {
      buttonElement.addEventListener("click", function () {
        void saveAiSuggestion();
      });
    });
    document.querySelectorAll("[data-ai-changes-apply]").forEach(function (buttonElement) {
      buttonElement.addEventListener("click", function () {
        void applyAiSuggestion();
      });
    });
    document.querySelectorAll("[data-ai-agent-submit]").forEach(function (buttonElement) {
      buttonElement.addEventListener("click", function () {
        void requestAiRoutes();
      });
    });

    [aiAgentEarliestBoardingInput, aiAgentArrivalAtWorkInput].forEach(function (inputElement) {
      if (!inputElement) {
        return;
      }
      inputElement.addEventListener("input", function () {
        state.aiAgentSettingsDraft = readAiAgentSettingsDraft(
          {
            earliestBoardingInput: aiAgentEarliestBoardingInput,
            arrivalAtWorkInput: aiAgentArrivalAtWorkInput,
            requestKindInputs: aiAgentRequestKindInputs,
            minOccInputs: aiAgentMinOccInputs,
          },
          state.aiAgentSettingsDraft || getDefaultAiAgentSettings()
        );
        if (state.aiAgentFeedbackMessage) {
          clearAiAgentFeedback();
          return;
        }
        syncAiAgentSettingsControls({ preserveInputs: true });
      });
    });

    aiAgentRequestKindInputs.forEach(function (inputElement) {
      if (!inputElement) {
        return;
      }
      inputElement.addEventListener("change", function () {
        state.aiAgentSettingsDraft = readAiAgentSettingsDraft(
          {
            earliestBoardingInput: aiAgentEarliestBoardingInput,
            arrivalAtWorkInput: aiAgentArrivalAtWorkInput,
            requestKindInputs: aiAgentRequestKindInputs,
            minOccInputs: aiAgentMinOccInputs,
          },
          state.aiAgentSettingsDraft || getDefaultAiAgentSettings()
        );
        if (state.aiAgentFeedbackMessage) {
          clearAiAgentFeedback();
          return;
        }
        syncAiAgentSettingsControls({ preserveInputs: true });
      });
    });

    ["carro", "minivan", "van", "onibus"].forEach(function (vt) {
      const inputElement = aiAgentMinOccInputs[vt];
      if (!inputElement) {
        return;
      }
      inputElement.addEventListener("input", function () {
        state.aiAgentSettingsDraft = readAiAgentSettingsDraft(
          {
            earliestBoardingInput: aiAgentEarliestBoardingInput,
            arrivalAtWorkInput: aiAgentArrivalAtWorkInput,
            requestKindInputs: aiAgentRequestKindInputs,
            minOccInputs: aiAgentMinOccInputs,
          },
          state.aiAgentSettingsDraft || getDefaultAiAgentSettings()
        );
        syncAiAgentSettingsControls({ preserveInputs: true });
      });
    });

    if (aiSettingsProviderInput) {
      aiSettingsProviderInput.addEventListener("change", function () {
        state.aiSettingsDraft = readTransportAiSettingsDraft(
          {
            projectInput: aiSettingsProjectInput,
            providerInput: aiSettingsProviderInput,
            apiKeyInput: aiSettingsApiKeyInput,
          },
          state.aiSettingsDraft || getDefaultTransportAiSettingsDraft()
        );
        if (state.aiSettingsFeedbackMessage || state.aiSettingsFeedbackKey) {
          clearAiSettingsFeedback();
          return;
        }
        syncAiSettingsControls({ preserveInputs: true });
      });
    }

    if (aiSettingsApiKeyInput) {
      aiSettingsApiKeyInput.addEventListener("input", function () {
        state.aiSettingsDraft = readTransportAiSettingsDraft(
          {
            projectInput: aiSettingsProjectInput,
            providerInput: aiSettingsProviderInput,
            apiKeyInput: aiSettingsApiKeyInput,
          },
          state.aiSettingsDraft || getDefaultTransportAiSettingsDraft()
        );
        if (state.aiSettingsFeedbackMessage || state.aiSettingsFeedbackKey) {
          clearAiSettingsFeedback();
          return;
        }
        syncAiSettingsControls({ preserveInputs: true });
      });
    }

    if (aiSettingsProjectInput) {
      aiSettingsProjectInput.addEventListener("change", function () {
        const nextProjectId = normalizeTransportAiSettingsProjectId(aiSettingsProjectInput.value, null);
        state.aiSettingsSelectedProjectId = nextProjectId;
        state.aiSettingsDraft = readTransportAiSettingsDraft(
          {
            projectInput: aiSettingsProjectInput,
            provider: DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER,
            apiKey: "",
          },
          getDefaultTransportAiSettingsDraft()
        );
        state.aiSettingsLoadedProvider = DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER;
        state.aiSettingsHasApiKey = false;
        state.aiSettingsApiKeyHint = "";
        clearAiSettingsFeedback();
        syncAiSettingsControls();
        if (nextProjectId) {
          void loadTransportAiSettings({
            forceProjectCatalogRefresh: getTransportAiSettingsProjectCatalogStatus() !== AI_SETTINGS_PROJECT_CATALOG_STATUS.ready,
          });
        }
      });
    }

    if (aiSettingsModal) {
      aiSettingsModal.addEventListener("click", function (event) {
        if (event.target === aiSettingsModal) {
          closeAiSettingsModal();
        }
      });
    }

    if (aiAgentModal) {
      aiAgentModal.addEventListener("click", function (event) {
        if (event.target === aiAgentModal) {
          closeAiAgentSettingsModal();
        }
      });
    }

    if (aiChangesModal) {
      aiChangesModal.addEventListener("click", function (event) {
        if (event.target === aiChangesModal) {
          closeAiChangesModal();
        }
      });
    }

    if (settingsModal) {
      settingsModal.addEventListener("click", function (event) {
        if (event.target === settingsModal) {
          closeSettingsModal();
        }
      });
    }

    document.querySelectorAll("[data-open-vehicle-modal]").forEach(function (buttonElement) {
      buttonElement.addEventListener("click", function () {
        openVehicleModal(buttonElement.dataset.openVehicleModal || "regular");
      });
    });

    document.querySelectorAll("[data-close-vehicle-modal]").forEach(function (buttonElement) {
      buttonElement.addEventListener("click", closeVehicleModal);
    });

    if (vehicleModal) {
      vehicleModal.addEventListener("click", function (event) {
        if (event.target === vehicleModal) {
          closeVehicleModal();
        }
      });
    }

    if (vehicleForm) {
      if (vehicleForm.elements.tipo) {
        vehicleForm.elements.tipo.addEventListener("change", function () {
          syncVehicleTypeDependentDefaults(vehicleForm.elements.tipo.value, vehicleForm);
        });
      }
      if (vehicleForm.elements.route_kind) {
        vehicleForm.elements.route_kind.addEventListener("change", function () {
          syncVehicleModalFields(vehicleModal && vehicleModal.dataset.scope ? vehicleModal.dataset.scope : "extra");
        });
      }

      vehicleForm.addEventListener("submit", function (event) {
        event.preventDefault();
        const formData = new FormData(vehicleForm);
        const submitButton = vehicleForm.querySelector('button[type="submit"]');
        const isEditMode = isVehicleModalEditMode();

        if (isEditMode) {
          const vehicleId = state.vehicleModalVehicleId;
          if (!Number.isFinite(vehicleId)) {
            setVehicleModalFeedback(t("status.couldNotUpdateVehicle"), "error");
            return;
          }

          clearVehicleModalFeedback();
          if (submitButton) {
            submitButton.disabled = true;
          }

          requestJson(`${TRANSPORT_API_PREFIX}/vehicles/${encodeURIComponent(String(vehicleId))}`, {
            method: "PUT",
            body: JSON.stringify(buildVehicleBasePayload(formData)),
          })
            .then(function (response) {
              closeVehicleModal();
              const structuredVehicleUpdatedMessage = resolveTransportApiStructuredMessage(response)
                || String(response && response.message || "").trim();
              const vehicleUpdatedMessage = structuredVehicleUpdatedMessage || t("status.vehicleUpdated");
              const vehicleUpdatedOptions = resolveTransportApiStructuredMessageOptions(response)
                || (structuredVehicleUpdatedMessage ? undefined : { key: "status.vehicleUpdated" });
              setStatus(vehicleUpdatedMessage, "success", vehicleUpdatedOptions);
              return loadDashboard(dateStore.getValue(), { announce: false });
            })
            .catch(function (error) {
              setVehicleModalFeedback(
                resolveTransportApiStructuredMessage(error && error.payload)
                  || localizeTransportApiMessage(error && error.message)
                  || t("status.couldNotUpdateVehicle"),
                "error"
              );
              handleProtectedRequestError(error, t("status.couldNotUpdateVehicle"));
            })
            .finally(function () {
              if (submitButton) {
                submitButton.disabled = false;
              }
            });
          return;
        }

        const payload = buildVehicleCreatePayload(formData, getCurrentServiceDateIso(), getSelectedRouteKind());
        const validationError = resolveVehicleCreateValidationError(payload);

        clearVehicleModalFeedback();
        if (validationError) {
          setVehicleModalFeedback(t(validationError.messageKey), "error");
          focusVehicleFormField(validationError.focusField);
          return;
        }
        if (submitButton) {
          submitButton.disabled = true;
        }

        requestJson(`${TRANSPORT_API_PREFIX}/vehicles`, {
          method: "POST",
          body: JSON.stringify(payload),
        })
          .then(function (response) {
            const currentDashboardDate = dateStore.getValue();
