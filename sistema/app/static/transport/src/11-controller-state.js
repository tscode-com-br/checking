  function createTransportPageController(dateStore) {
    const requestContainers = {};
    const vehicleContainers = {};
    const state = {
      dashboard: null,
      dashboardLoadPromise: null,
      queuedDashboardLoad: null,
      pendingAssignmentPreview: null,
      dragRequestId: null,
      isLoading: false,
      selectedRouteKind: "home_to_work",
      projectVisibility: {},
      projectListOpen: false,
      expandedVehicleKey: null,
      vehicleViewModes: {
        extra: "grid",
        weekend: "grid",
        regular: "grid",
      },
      isAuthenticated: false,
      authenticatedUser: null,
      sessionBootstrapPending: true,
      authVerifyToken: 0,
      authVerifySignature: "",
      lastVerifiedAuthSignature: "",
      authVerifyTimer: null,
      authVerifyRequestController: null,
      realtimeConnected: false,
      realtimeEventStream: null,
      realtimeRefreshTimer: null,
      realtimeReconnectTimer: null,
      realtimeReconnectAttempt: 0,
      realtimeReconnectPending: false,
      deferredDashboardLoad: null,
      settingsLoaded: false,
      settingsLoading: false,
      settingsSaving: false,
      languageLoading: false,
      statusMessageKey: DEFAULT_STATUS_MESSAGE_KEY,
      statusMessageValues: null,
      statusMessageText: "",
      statusMessageTone: "info",
      vehicleModalMode: "create",
      vehicleModalVehicleId: null,
      arriveAtWorkTime: DEFAULT_ARRIVE_AT_WORK_TIME,
      workToHomeTime: DEFAULT_WORK_TO_HOME_TIME,
      dashboardGeneratedAt: "",
      vehicleReferenceClock: null,
      vehicleReferenceModeTimer: null,
      lastUpdateTime: DEFAULT_LAST_UPDATE_TIME,
      extraCarToleranceMinutes: DEFAULT_EXTRA_CAR_TOLERANCE_MINUTES,
      vehicleSeatDefaults: Object.assign({}, DEFAULT_VEHICLE_SEAT_COUNT),
      vehiclePriceDefaults: Object.assign({}, DEFAULT_VEHICLE_PRICE_DEFAULTS),
      vehicleToleranceDefaultMinutes: DEFAULT_VEHICLE_TOLERANCE_MINUTES,
      priceCurrencyCode: "",
      priceRateUnit: DEFAULT_TRANSPORT_PRICE_RATE_UNIT,
      availableCurrencies: [],
      currencyCreateOpen: false,
      currencyCreateSaving: false,
      routeTimeSaving: false,
      aiRouteRunKey: null,
      aiRouteRunStatus: null,
      aiRouteSuggestion: null,
      aiRoutePollingTimer: null,
      aiRoutePollingAttempt: 0,
      aiRouteRequestPending: false,
      aiRouteInBackground: false,
      aiLatestSuggestionLoading: false,
      aiChangesCommandPending: false,
      aiChangesPendingAction: "",
      aiAgentSettingsDraft: getDefaultAiAgentSettings(),
      aiAgentFeedbackMessage: "",
      aiAgentFeedbackKey: "",
      aiAgentFeedbackValues: null,
      aiAgentFeedbackTone: "info",
      aiSettingsDraft: getDefaultTransportAiSettingsDraft(),
      aiSettingsLoading: false,
      aiSettingsSaving: false,
      aiSettingsProjects: [],
      aiSettingsProjectCatalogStatus: AI_SETTINGS_PROJECT_CATALOG_STATUS.idle,
      aiSettingsSelectedProjectId: null,
      aiSettingsLoadedProvider: DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER,
      aiSettingsHasApiKey: false,
      aiSettingsApiKeyHint: "",
      aiSettingsHasMapsApiKey: false,
      aiSettingsMapsApiKeyHint: "",
      aiSettingsFeedbackMessage: "",
      aiSettingsFeedbackKey: "",
      aiSettingsFeedbackValues: null,
      aiSettingsFeedbackTone: "info",
      aiChangesSummaryMessage: "",
      aiChangesSummaryKey: "",
      aiChangesSummaryValues: null,
      aiChangesSummaryTone: "success",
      aiMenuOpen: false,
      expandedVehiclePositionFrame: null,
      requestSectionCollapsedByKind: {
        extra: false,
        weekend: false,
        regular: false,
      },
      requestRowCollapseOverrides: {},
    };
    const vehicleDetailsOverlayHost = document.querySelector("[data-vehicle-details-layer]")
      || createNode("div", "transport-vehicle-details-layer");
    const statusMessage = document.querySelector("[data-status-message]");
    const transportTopbar = document.querySelector("[data-transport-topbar]");
    const projectListToggle = document.querySelector("[data-project-list-toggle]");
    const projectListPanel = document.querySelector("[data-project-list-panel]");
    const projectListContainer = document.querySelector("[data-project-list]");
    const settingsTrigger = document.querySelector("[data-open-settings-modal]");
    const settingsModal = document.querySelector("[data-settings-modal]");
    const aiSettingsModal = document.querySelector("[data-ai-settings-modal]");
    const aiSettingsProjectInput = document.querySelector("[data-ai-settings-project]");
    const aiSettingsProviderInput = document.querySelector("[data-ai-settings-provider]");
    const aiSettingsProviderNote = document.querySelector("[data-ai-settings-provider-note]");
    const aiSettingsApiKeyInput = document.querySelector("[data-ai-settings-api-key]");
    const aiSettingsApiKeyHint = document.querySelector("[data-ai-settings-api-key-hint]");
    const aiSettingsMapsApiKeyInput = document.querySelector("[data-ai-settings-maps-api-key]");
    const aiSettingsMapsApiKeyHint = document.querySelector("[data-ai-settings-maps-api-key-hint]");
    const aiSettingsFeedback = document.querySelector("[data-ai-settings-feedback]");
    const aiAgentModal = document.querySelector("[data-ai-agent-modal]");
    const aiAgentModalNote = document.querySelector("[data-ai-agent-modal-note]");
    const aiAgentRequestKindInputs = Array.from(document.querySelectorAll("[data-ai-agent-request-kind]"));
    const aiAgentEarliestBoardingInput = document.querySelector("[data-ai-agent-earliest-boarding]");
    const aiAgentArrivalAtWorkInput = document.querySelector("[data-ai-agent-arrival-at-work]");
    const aiAgentMinOccInputs = {
      carro: document.querySelector('[data-ai-agent-min-occ="carro"]'),
      minivan: document.querySelector('[data-ai-agent-min-occ="minivan"]'),
      van: document.querySelector('[data-ai-agent-min-occ="van"]'),
      onibus: document.querySelector('[data-ai-agent-min-occ="onibus"]'),
    };
    const aiAgentMaxSeatsLabels = {
      carro: document.querySelector('[data-ai-agent-max-seats="carro"]'),
      minivan: document.querySelector('[data-ai-agent-max-seats="minivan"]'),
      van: document.querySelector('[data-ai-agent-max-seats="van"]'),
      onibus: document.querySelector('[data-ai-agent-max-seats="onibus"]'),
    };
    const aiAgentFeedback = document.querySelector("[data-ai-agent-feedback]");
    const aiChangesModal = document.querySelector("[data-ai-changes-modal]");
    const aiChangesSummary = document.querySelector("[data-ai-changes-status]")
      || document.querySelector("[data-ai-changes-summary]");
    const aiChangesSummaryGrid = document.querySelector("[data-ai-changes-summary-grid]");
    const aiChangesSummaryPanel = document.querySelector("[data-ai-changes-summary-panel]");
    const aiChangesVehiclesPanel = document.querySelector("[data-ai-changes-vehicles]");
    const aiChangesPassengersPanel = document.querySelector("[data-ai-changes-passengers]");
    const aiChangesRoutesPanel = document.querySelector("[data-ai-changes-routes]");
    const aiChangesAuditPanel = document.querySelector("[data-ai-changes-audit]");
    const aiChangesCancelButton = document.querySelector("[data-ai-changes-cancel]");
    const aiChangesDiscardButton = document.querySelector("[data-ai-changes-discard]");
    const aiChangesApplyButton = document.querySelector("[data-ai-changes-apply]");
    const settingsLanguageSelect = document.querySelector("[data-settings-language-select]");
    const settingsArriveAtWorkInput = document.querySelector("[data-settings-arrive-at-work-time]");
    let aiSettingsLoadRequestSequence = 0;
    const settingsTimeInput = document.querySelector("[data-settings-work-to-home-time]");
    const settingsExtraCarToleranceInput = document.querySelector("[data-settings-extra-car-tolerance]");
    const settingsLastUpdateInput = document.querySelector("[data-settings-last-update-time]");
    const settingsPriceCurrencySelect = document.querySelector("[data-settings-price-currency]");
    const settingsPriceRateUnitSelect = document.querySelector("[data-settings-price-rate-unit]");
    const settingsAddCurrencyButton = document.querySelector("[data-settings-add-currency-button]");
    const settingsAddCurrencyPanel = document.querySelector("[data-settings-add-currency-panel]");
    const settingsNewCurrencyCodeInput = document.querySelector("[data-settings-new-currency-code]");
    const settingsNewCurrencyLabelInput = document.querySelector("[data-settings-new-currency-label]");
    const settingsCancelCurrencyButton = document.querySelector("[data-settings-cancel-currency-button]");
    const settingsSaveCurrencyButton = document.querySelector("[data-settings-save-currency-button]");
    const settingsDefaultToleranceInput = document.querySelector("[data-settings-default-tolerance]");
    const settingsDefaultSeatLabels = {
      carro: document.querySelector('[data-settings-default-seat-label="carro"]'),
      minivan: document.querySelector('[data-settings-default-seat-label="minivan"]'),
      van: document.querySelector('[data-settings-default-seat-label="van"]'),
      onibus: document.querySelector('[data-settings-default-seat-label="onibus"]'),
    };
    const settingsDefaultSeatInputs = {
      carro: document.querySelector('[data-settings-default-seat="carro"]'),
      minivan: document.querySelector('[data-settings-default-seat="minivan"]'),
      van: document.querySelector('[data-settings-default-seat="van"]'),
      onibus: document.querySelector('[data-settings-default-seat="onibus"]'),
    };
    const settingsDefaultPriceLabels = {
      carro: document.querySelector('[data-settings-default-price-label="carro"]'),
      minivan: document.querySelector('[data-settings-default-price-label="minivan"]'),
      van: document.querySelector('[data-settings-default-price-label="van"]'),
      onibus: document.querySelector('[data-settings-default-price-label="onibus"]'),
    };
    const settingsDefaultPriceInputs = {
      carro: document.querySelector('[data-settings-default-price="carro"]'),
      minivan: document.querySelector('[data-settings-default-price="minivan"]'),
      van: document.querySelector('[data-settings-default-price="van"]'),
      onibus: document.querySelector('[data-settings-default-price="onibus"]'),
    };
    const vehicleModal = document.querySelector("[data-vehicle-modal]");
    const extraVehicleSection = document.querySelector("[data-extra-vehicle-section]");
    const weekendPersistenceGroup = document.querySelector("[data-weekend-persistence-group]");
    const regularPersistenceGroup = document.querySelector("[data-regular-persistence-group]");
    const vehicleForm = document.querySelector("[data-vehicle-form]");
    const vehicleModalTitle = document.getElementById("transport-vehicle-modal-title");
    const vehicleModalSubmitButton = vehicleForm ? vehicleForm.querySelector('button[type="submit"]') : null;
    const modalScopeLabel = document.querySelector("[data-modal-scope-label]");
    const modalScopeNote = document.querySelector("[data-modal-scope-note]");
    const vehicleModalFeedback = document.querySelector("[data-vehicle-modal-feedback]");
    const extraServiceDateField = document.querySelector("[data-extra-service-date-field]");
    const extraDepartureField = document.querySelector("[data-extra-departure-field]");
    const extraDepartureFieldLabel = document.querySelector("[data-extra-departure-label]");
    const extraRouteField = document.querySelector("[data-extra-route-field]");
    const weekendPersistenceFields = Array.from(document.querySelectorAll("[data-weekend-persistence-field]"));
    const regularPersistenceFields = Array.from(document.querySelectorAll("[data-regular-persistence-field]"));
    const routeTimePopover = document.querySelector("[data-route-time-popover]");
    const routeTimeInput = document.querySelector("[data-route-time-input]");
    const aiMenuShell = document.querySelector("[data-ai-menu-shell]");
    const aiMenuTrigger = document.querySelector("[data-ai-menu-trigger]");
    const aiMenu = document.querySelector("[data-ai-menu]");
    const aiCalculateRoutesButton = document.querySelector('[data-ai-menu-action="calculate-routes"]');
    const aiImplementModificationsButton = document.querySelector('[data-ai-menu-action="implement-modifications"]');
    const aiSettingsMenuButton = document.querySelector('[data-ai-menu-action="settings"]');
    const authKeyInput = document.querySelector("[data-transport-auth-key]");
    const authPasswordInput = document.querySelector("[data-transport-auth-password]");
    const authKeyShell = document.querySelector('[data-transport-auth-shell="key"]');
    const authPasswordShell = document.querySelector('[data-transport-auth-shell="password"]');
    const requestUserButton = document.querySelector("[data-request-user-link]");
    const requestSectionToggleLinks = {};
    const vehicleViewToggleLinks = {};

    vehicleDetailsOverlayHost.dataset.vehicleDetailsLayer = "true";
    if (!vehicleDetailsOverlayHost.parentNode && document.body) {
      document.body.appendChild(vehicleDetailsOverlayHost);
    }
    vehicleDetailsOverlayHost.addEventListener("click", function (event) {
      if (event.target !== vehicleDetailsOverlayHost) {
        return;
      }
      closeExpandedVehicleDetails({ restoreFocus: true });
    });

    document.querySelectorAll("[data-request-kind]").forEach(function (element) {
      requestContainers[element.dataset.requestKind] = element;
    });
    document.querySelectorAll("[data-toggle-request-section]").forEach(function (element) {
      requestSectionToggleLinks[element.dataset.toggleRequestSection] = element;
    });
    document.querySelectorAll("[data-vehicle-scope]").forEach(function (element) {
      vehicleContainers[element.dataset.vehicleScope] = element;
    });
    document.querySelectorAll("[data-toggle-vehicle-view]").forEach(function (element) {
      vehicleViewToggleLinks[element.dataset.toggleVehicleView] = element;
    });

    Object.keys(requestSectionToggleLinks).forEach(function (scope) {
      const toggleLink = requestSectionToggleLinks[scope];
      if (!toggleLink) {
        return;
      }
      toggleLink.addEventListener("click", function (event) {
        event.preventDefault();
        toggleRequestSectionCollapsed(scope);
      });
    });

    Object.keys(vehicleViewToggleLinks).forEach(function (scope) {
      const toggleLink = vehicleViewToggleLinks[scope];
      if (!toggleLink) {
        return;
      }
      toggleLink.addEventListener("click", function (event) {
        event.preventDefault();
        toggleVehicleViewMode(scope);
      });
    });

    globalScope.addEventListener("scroll", function () {
      scheduleExpandedVehicleDetailsPositionSync();
    }, true);
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") {
        return;
      }
      if (state.aiMenuOpen) {
        closeAiMenu({ restoreFocus: true });
        return;
      }
      if (aiSettingsModal && !aiSettingsModal.hidden) {
        closeAiSettingsModal({ restoreFocus: true });
        return;
      }
      if (aiAgentModal && !aiAgentModal.hidden) {
        closeAiAgentSettingsModal({ restoreFocus: true });
        return;
      }
      if (aiChangesModal && !aiChangesModal.hidden) {
        closeAiChangesModal({ restoreFocus: true });
        return;
      }
      if (!state.expandedVehicleKey && !state.pendingAssignmentPreview) {
        return;
      }
      if ((settingsModal && !settingsModal.hidden) || (vehicleModal && !vehicleModal.hidden)) {
        return;
      }
      closeExpandedVehicleDetails({ restoreFocus: true });
    });

    if (projectListToggle) {
      projectListToggle.addEventListener("click", function () {
        state.projectListOpen = !state.projectListOpen;
        renderProjectList();
      });
    }

    function refreshDatePanelLabels() {
      const selectedDate = dateStore.getValue();
      document.querySelectorAll("[data-date-label]").forEach(function (labelElement) {
        labelElement.textContent = formatTransportDate(selectedDate);
        labelElement.dataset.dateState = getTransportDateState(selectedDate);
      });
    }

    function setDashboardDateForSilentReload(nextDate) {
      const selectedDate = dateStore.setValue(nextDate, { notify: false });
      setStoredTransportDate(selectedDate);
      refreshDatePanelLabels();
      closeRouteTimePopover();
      return selectedDate;
    }

    function focusVehicleFormField(fieldName) {
      if (!vehicleForm || !fieldName || !vehicleForm.elements || !vehicleForm.elements[fieldName]) {
        return false;
      }

      const fieldElement = vehicleForm.elements[fieldName];
      if (typeof fieldElement.focus !== "function") {
        return false;
      }

      fieldElement.focus();
      return true;
    }

    function getVehicleModalMode() {
      return state.vehicleModalMode === "edit" ? "edit" : "create";
    }

    function isVehicleModalEditMode() {
      return getVehicleModalMode() === "edit";
    }

    function setVehicleModalContext(context) {
      const nextContext = context || {};
      const nextMode = nextContext.mode === "edit" ? "edit" : "create";
      const nextScope = normalizeVehicleScope(
        nextContext.scope
        || (vehicleModal && vehicleModal.dataset.scope ? vehicleModal.dataset.scope : "regular")
      );
      const nextVehicleId = nextMode === "edit" && Number.isFinite(Number(nextContext.vehicleId))
        ? Number(nextContext.vehicleId)
        : null;

      state.vehicleModalMode = nextMode;
      state.vehicleModalVehicleId = nextVehicleId;

      if (vehicleModal) {
        vehicleModal.dataset.mode = nextMode;
        vehicleModal.dataset.scope = nextScope;
        if (nextVehicleId === null) {
          delete vehicleModal.dataset.vehicleId;
        } else {
          vehicleModal.dataset.vehicleId = String(nextVehicleId);
        }
      }

      return nextScope;
    }

    function getActiveVehicleModalRouteKind(scope) {
      const normalizedScope = normalizeVehicleScope(scope || (vehicleModal && vehicleModal.dataset.scope));
      if (normalizedScope !== "extra") {
        return "";
      }

      if (vehicleForm && vehicleForm.elements.route_kind) {
        const currentRouteKind = String(vehicleForm.elements.route_kind.value || "").trim();
        if (Object.prototype.hasOwnProperty.call(ROUTE_KIND_KEYS, currentRouteKind)) {
          return currentRouteKind;
        }
      }

      const selectedRouteKind = getSelectedRouteKind();
      return Object.prototype.hasOwnProperty.call(ROUTE_KIND_KEYS, selectedRouteKind)
        ? selectedRouteKind
        : "";
    }

    function syncExtraVehicleDepartureFieldCopy(scope) {
      const normalizedScope = normalizeVehicleScope(scope || (vehicleModal && vehicleModal.dataset.scope));
      const fieldKey = normalizedScope === "extra"
        ? getExtraVehicleDepartureFieldKey(getActiveVehicleModalRouteKind(normalizedScope))
        : "modal.fields.departureTime";
      const labelText = t(fieldKey);

      if (extraDepartureFieldLabel) {
        extraDepartureFieldLabel.textContent = labelText;
      }
      if (
        vehicleForm
        && vehicleForm.elements.departure_time
        && typeof vehicleForm.elements.departure_time.setAttribute === "function"
      ) {
        vehicleForm.elements.departure_time.setAttribute("aria-label", labelText);
      }
    }

    function syncVehicleModalCopy(scope) {
      const normalizedScope = normalizeVehicleScope(scope || (vehicleModal && vehicleModal.dataset.scope));
      const currentRouteKind = normalizedScope === "extra"
        ? getActiveVehicleModalRouteKind(normalizedScope)
        : "";

      if (modalScopeLabel) {
        modalScopeLabel.textContent = mapScopeTitle(normalizedScope);
      }
      if (modalScopeNote) {
        modalScopeNote.textContent = isVehicleModalEditMode()
          ? t("modal.notes.edit")
          : getModalScopeNote(normalizedScope, currentRouteKind);
      }
      if (vehicleModalTitle) {
        vehicleModalTitle.textContent = isVehicleModalEditMode()
          ? t("modal.editTitle")
          : t("modal.title");
      }
      if (vehicleModalSubmitButton) {
        vehicleModalSubmitButton.textContent = isVehicleModalEditMode()
          ? t("modal.actions.update")
          : t("modal.actions.save");
      }
    }

    function formatVehicleFormFieldValue(value) {
      return value === null || value === undefined ? "" : String(value);
    }

    function populateVehicleFormBaseFields(vehicle) {
      const resolvedVehicle = vehicle || {};

      if (!vehicleForm) {
        return;
      }

      if (vehicleForm.elements.tipo) {
        vehicleForm.elements.tipo.value = formatVehicleFormFieldValue(resolvedVehicle.tipo).trim().toLowerCase();
      }
      if (vehicleForm.elements.placa) {
        vehicleForm.elements.placa.value = formatVehicleFormFieldValue(resolvedVehicle.placa);
      }
      if (vehicleForm.elements.color) {
        vehicleForm.elements.color.value = formatVehicleFormFieldValue(resolvedVehicle.color);
      }
      if (vehicleForm.elements.lugares) {
        vehicleForm.elements.lugares.value = formatVehicleFormFieldValue(resolvedVehicle.lugares);
      }
      if (vehicleForm.elements.tolerance) {
        vehicleForm.elements.tolerance.value = formatVehicleFormFieldValue(resolvedVehicle.tolerance);
      }
    }

    function applyStaticTranslations() {
      if (typeof document === "undefined") {
        return;
      }

      applyDocumentLanguageMetadata();
      applyDeclarativeTranslations(document);
      syncStatusMessageCopy();

      if (aiAgentModalNote) {
        const projectCount = getProjectRows().filter(function (projectRow) {
          return projectRow && projectRow.name;
        }).length;
        aiAgentModalNote.textContent = projectCount
          ? t("ai.agentSettingsNoteReady", { count: projectCount })
          : t("ai.agentSettingsNotePending");
      }
      syncAiSettingsControls({ preserveInputs: true });
      syncAiAgentSettingsControls({ preserveInputs: true });
      syncAiChangesSummaryCopy();
      syncAiChangesSummaryRender();
      syncAiVehicleChangesRender();
      syncAiPassengerAllocationsRender();
      syncAiRouteItinerariesRender();
      syncAiChangesAuditRender();
      syncAiChangesControls();

      syncVehicleModalCopy(vehicleModal && vehicleModal.dataset.scope ? vehicleModal.dataset.scope : "regular");
      if (settingsArriveAtWorkInput) {
        settingsArriveAtWorkInput.placeholder = DEFAULT_ARRIVE_AT_WORK_TIME;
      }
      if (settingsExtraCarToleranceInput) {
        settingsExtraCarToleranceInput.placeholder = String(DEFAULT_EXTRA_CAR_TOLERANCE_MINUTES);
      }
      if (settingsDefaultSeatLabels.carro) {
        settingsDefaultSeatLabels.carro.textContent = t("settings.defaultPlacesLabel", {
          type: mapVehicleTypeLabel("carro"),
        });
      }
      if (settingsDefaultSeatLabels.minivan) {
        settingsDefaultSeatLabels.minivan.textContent = t("settings.defaultPlacesLabel", {
          type: mapVehicleTypeLabel("minivan"),
        });
      }
      if (settingsDefaultSeatLabels.van) {
        settingsDefaultSeatLabels.van.textContent = t("settings.defaultPlacesLabel", {
          type: mapVehicleTypeLabel("van"),
        });
      }
      if (settingsDefaultSeatLabels.onibus) {
        settingsDefaultSeatLabels.onibus.textContent = t("settings.defaultPlacesLabel", {
          type: mapVehicleTypeLabel("onibus"),
        });
      }
      if (settingsDefaultPriceLabels.carro) {
        settingsDefaultPriceLabels.carro.textContent = t("settings.defaultPriceLabel", {
          type: mapVehicleTypeLabel("carro"),
        });
      }
      if (settingsDefaultPriceLabels.minivan) {
        settingsDefaultPriceLabels.minivan.textContent = t("settings.defaultPriceLabel", {
          type: mapVehicleTypeLabel("minivan"),
        });
      }
      if (settingsDefaultPriceLabels.van) {
        settingsDefaultPriceLabels.van.textContent = t("settings.defaultPriceLabel", {
          type: mapVehicleTypeLabel("van"),
        });
      }
      if (settingsDefaultPriceLabels.onibus) {
        settingsDefaultPriceLabels.onibus.textContent = t("settings.defaultPriceLabel", {
          type: mapVehicleTypeLabel("onibus"),
        });
      }
      populateTransportCurrencyOptions();

      const carPanels = document.getElementById("tela01main_dir");
      syncVehiclePanelResizeHandleState(carPanels || document);

      refreshDatePanelLabels();
      syncVehicleModalFields(vehicleModal && vehicleModal.dataset.scope ? vehicleModal.dataset.scope : "regular");
    }

    function clearRequestCollapseOverridesForKind(kind) {
      getRequestsForKind(kind).forEach(function (requestRow) {
        delete state.requestRowCollapseOverrides[String(requestRow.id)];
      });
    }

    function getRequestSectionCollapsedState(kind) {
      return Boolean(state.requestSectionCollapsedByKind[kind]);
    }

    function getRequestRowCollapsedState(requestRow) {
      if (!requestRow || requestRow.id === undefined || requestRow.id === null) {
        return false;
      }

      const requestIdKey = String(requestRow.id);
      if (Object.prototype.hasOwnProperty.call(state.requestRowCollapseOverrides, requestIdKey)) {
        return Boolean(state.requestRowCollapseOverrides[requestIdKey]);
      }

      return getRequestSectionCollapsedState(requestRow.request_kind);
    }

    function setRequestRowCollapsedState(requestRow, collapsed) {
      if (!requestRow || requestRow.id === undefined || requestRow.id === null) {
        return;
      }

      const requestIdKey = String(requestRow.id);
      const defaultCollapsed = getRequestSectionCollapsedState(requestRow.request_kind);
      if (collapsed === defaultCollapsed) {
        delete state.requestRowCollapseOverrides[requestIdKey];
        return;
      }

      state.requestRowCollapseOverrides[requestIdKey] = Boolean(collapsed);
    }

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

    function preserveRequestSectionScrollPosition(kind, callback) {
      const container = requestContainers[kind];
      const previousScrollTop = container ? container.scrollTop : 0;
      if (typeof callback === "function") {
        callback(container);
      }
      if (container) {
        container.scrollTop = previousScrollTop;
      }
    }

    function syncRequestSectionCollapsedRowsInDom(kind) {
      const container = requestContainers[kind];
      if (!container) {
        return;
      }

      getVisibleRequestsForKind(kind).forEach(function (requestRow) {
        const rowButton = container.querySelector(`.transport-request-row[data-request-id="${String(requestRow.id)}"]`);
        applyRequestRowCollapsedVisualState(rowButton, getRequestRowCollapsedState(requestRow));
      });
    }

    function toggleRequestRowCollapsed(requestRow, rowButton) {
      if (!requestRow || !rowButton) {
        return;
      }

      setRequestRowCollapsedState(requestRow, !getRequestRowCollapsedState(requestRow));
      preserveRequestSectionScrollPosition(requestRow.request_kind, function () {
        applyRequestRowCollapsedVisualState(rowButton, getRequestRowCollapsedState(requestRow));
      });
    }

    function syncRequestSectionToggleState() {
      Object.keys(requestSectionToggleLinks).forEach(function (kind) {
        const toggleLink = requestSectionToggleLinks[kind];
        if (!toggleLink) {
          return;
        }

        const isExpanded = !getRequestSectionCollapsedState(kind);
        toggleLink.setAttribute("aria-expanded", String(isExpanded));
        toggleLink.classList.toggle("is-collapsed", !isExpanded);
      });
    }

    function toggleRequestSectionCollapsed(kind) {
      state.requestSectionCollapsedByKind[kind] = !getRequestSectionCollapsedState(kind);
      clearRequestCollapseOverridesForKind(kind);
      preserveRequestSectionScrollPosition(kind, function () {
        syncRequestSectionCollapsedRowsInDom(kind);
        syncRequestSectionToggleState();
      });
    }

    function populateLanguageOptions() {
      if (!settingsLanguageSelect) {
        return;
      }

      clearElement(settingsLanguageSelect);
      transportLanguages.forEach(function (languageItem) {
        const optionElement = document.createElement("option");
        optionElement.value = languageItem.code;
        optionElement.textContent = languageItem.label;
        settingsLanguageSelect.appendChild(optionElement);
      });
    }

    function populateTransportCurrencyOptions() {
      if (!settingsPriceCurrencySelect) {
        return;
      }

      clearElement(settingsPriceCurrencySelect);

      const blankOption = document.createElement("option");
      blankOption.value = "";
      blankOption.textContent = t("settings.selectCurrency");
      settingsPriceCurrencySelect.appendChild(blankOption);

      resolveTransportCurrencyOptions(state.availableCurrencies).forEach(function (currencyOption) {
        const optionElement = document.createElement("option");
        optionElement.value = currencyOption.code;
        optionElement.textContent = formatTransportCurrencyOptionLabel(currencyOption);
        settingsPriceCurrencySelect.appendChild(optionElement);
      });
    }

    function closeCurrencyCreatePanel(options) {
      const nextOptions = options || {};
      state.currencyCreateOpen = false;

      if (!nextOptions.preserveDraft) {
        if (settingsNewCurrencyCodeInput) {
          settingsNewCurrencyCodeInput.value = "";
        }
        if (settingsNewCurrencyLabelInput) {
          settingsNewCurrencyLabelInput.value = "";
        }
      }

      syncSettingsControls();
    }

    function openCurrencyCreatePanel() {
      state.currencyCreateOpen = true;
      syncSettingsControls();

      if (settingsNewCurrencyCodeInput && typeof settingsNewCurrencyCodeInput.focus === "function") {
        settingsNewCurrencyCodeInput.focus();
      }
    }

    function syncSettingsControls() {
      const settingsControlsDisabled = !state.isAuthenticated || state.settingsLoading || state.settingsSaving;

      if (settingsLanguageSelect) {
        settingsLanguageSelect.value = getActiveLanguageCode();
        settingsLanguageSelect.disabled = state.languageLoading;
      }
      if (settingsArriveAtWorkInput) {
        settingsArriveAtWorkInput.value = normalizeTransportTimeValue(
          state.arriveAtWorkTime,
          DEFAULT_ARRIVE_AT_WORK_TIME
        );
        settingsArriveAtWorkInput.title = settingsArriveAtWorkInput.value;
        settingsArriveAtWorkInput.disabled = settingsControlsDisabled;
      }
      if (settingsTimeInput) {
        settingsTimeInput.value = normalizeTransportTimeValue(state.workToHomeTime, DEFAULT_WORK_TO_HOME_TIME);
        settingsTimeInput.disabled = settingsControlsDisabled;
      }
      if (settingsExtraCarToleranceInput) {
        settingsExtraCarToleranceInput.value = String(
          normalizeVehicleToleranceSetting(
            state.extraCarToleranceMinutes,
            DEFAULT_EXTRA_CAR_TOLERANCE_MINUTES
          )
        );
        settingsExtraCarToleranceInput.title = settingsExtraCarToleranceInput.value;
        settingsExtraCarToleranceInput.disabled = settingsControlsDisabled;
      }
      if (settingsLastUpdateInput) {
        settingsLastUpdateInput.value = normalizeTransportTimeValue(state.lastUpdateTime, DEFAULT_LAST_UPDATE_TIME);
        settingsLastUpdateInput.disabled = settingsControlsDisabled;
      }
      Object.keys(settingsDefaultSeatInputs).forEach(function (vehicleType) {
        const seatInput = settingsDefaultSeatInputs[vehicleType];
        if (!seatInput) {
          return;
        }
        seatInput.value = String(getDefaultVehicleSeatCount(vehicleType));
        seatInput.disabled = settingsControlsDisabled;
      });
      Object.keys(settingsDefaultPriceInputs).forEach(function (vehicleType) {
        const priceInput = settingsDefaultPriceInputs[vehicleType];
        if (!priceInput) {
          return;
        }
        priceInput.value = formatTransportPriceInputValue(state.vehiclePriceDefaults[vehicleType]);
        priceInput.disabled = settingsControlsDisabled;
      });
      if (settingsDefaultToleranceInput) {
        settingsDefaultToleranceInput.value = String(getDefaultVehicleToleranceMinutes());
        settingsDefaultToleranceInput.disabled = settingsControlsDisabled;
      }
      state.availableCurrencies = resolveTransportCurrencyOptions(state.availableCurrencies);
      populateTransportCurrencyOptions();
      if (settingsPriceCurrencySelect) {
        const selectedCurrencyCode = normalizeTransportCurrencyCode(state.priceCurrencyCode);
        settingsPriceCurrencySelect.value = state.availableCurrencies.some(function (currencyOption) {
          return currencyOption.code === selectedCurrencyCode;
        })
          ? selectedCurrencyCode
          : "";
        settingsPriceCurrencySelect.disabled = settingsControlsDisabled || state.currencyCreateSaving;
      }
      if (settingsPriceRateUnitSelect) {
        settingsPriceRateUnitSelect.value = normalizeTransportPriceRateUnit(
          state.priceRateUnit,
          DEFAULT_TRANSPORT_PRICE_RATE_UNIT
        );
        settingsPriceRateUnitSelect.disabled = settingsControlsDisabled || state.currencyCreateSaving;
      }
      if (settingsAddCurrencyButton) {
        settingsAddCurrencyButton.disabled = settingsControlsDisabled || state.currencyCreateSaving;
        settingsAddCurrencyButton.setAttribute("aria-expanded", String(state.currencyCreateOpen));
      }
      if (settingsAddCurrencyPanel) {
        settingsAddCurrencyPanel.hidden = !state.currencyCreateOpen;
      }
      if (settingsNewCurrencyCodeInput) {
        settingsNewCurrencyCodeInput.disabled = settingsControlsDisabled || state.currencyCreateSaving;
      }
      if (settingsNewCurrencyLabelInput) {
        settingsNewCurrencyLabelInput.disabled = settingsControlsDisabled || state.currencyCreateSaving;
      }
      if (settingsCancelCurrencyButton) {
        settingsCancelCurrencyButton.disabled = state.currencyCreateSaving;
      }
      if (settingsSaveCurrencyButton) {
        settingsSaveCurrencyButton.disabled = settingsControlsDisabled || state.currencyCreateSaving;
      }
    }

    function syncAiAgentSettingsControls(options) {
      const syncOptions = options || {};
      const hasActiveRun = state.aiRouteRequestPending
        || state.aiRoutePollingTimer !== null
        || shouldContinuePollingAiRouteRun(state.aiRouteRunStatus);
      const activeDraft = readAiAgentSettingsDraft(undefined, state.aiAgentSettingsDraft || getDefaultAiAgentSettings());

      if (!syncOptions.preserveInputs) {
        if (aiAgentEarliestBoardingInput) {
          aiAgentEarliestBoardingInput.value = activeDraft.earliestBoardingTime;
        }
        if (aiAgentArrivalAtWorkInput) {
          aiAgentArrivalAtWorkInput.value = activeDraft.arrivalAtWorkTime;
        }
        aiAgentRequestKindInputs.forEach(function (inputElement) {
          const requestKind = String(
            inputElement.getAttribute("data-ai-agent-request-kind")
            || inputElement.value
            || ""
          ).trim().toLowerCase();
          inputElement.checked = activeDraft.requestKinds.includes(requestKind);
        });
        ["carro", "minivan", "van", "onibus"].forEach(function (vt) {
          if (aiAgentMinOccInputs[vt]) {
            const draftOcc = activeDraft.minOccupancy && activeDraft.minOccupancy[vt];
            aiAgentMinOccInputs[vt].value = draftOcc != null ? draftOcc : DEFAULT_AI_AGENT_SETTINGS.minOccupancy[vt];
          }
        });
      }

      // Update max-seats labels from current vehicle seat defaults
      ["carro", "minivan", "van", "onibus"].forEach(function (vt) {
        if (aiAgentMaxSeatsLabels[vt]) {
          const maxSeats = state.vehicleSeatDefaults && state.vehicleSeatDefaults[vt] != null
            ? state.vehicleSeatDefaults[vt]
            : DEFAULT_VEHICLE_SEAT_COUNT[vt];
          const labelText = t("ai.agentSettingsMinOccMaxSeats", { count: maxSeats });
          aiAgentMaxSeatsLabels[vt].textContent = labelText || "(" + maxSeats + ")";
        }
      });

      if (aiAgentEarliestBoardingInput) {
        aiAgentEarliestBoardingInput.disabled = hasActiveRun;
      }
      if (aiAgentArrivalAtWorkInput) {
        aiAgentArrivalAtWorkInput.disabled = hasActiveRun;
      }
      aiAgentRequestKindInputs.forEach(function (inputElement) {
        inputElement.disabled = hasActiveRun;
      });
      ["carro", "minivan", "van", "onibus"].forEach(function (vt) {
        if (aiAgentMinOccInputs[vt]) {
          aiAgentMinOccInputs[vt].disabled = hasActiveRun;
        }
      });

      document.querySelectorAll("[data-ai-agent-cancel]").forEach(function (buttonElement) {
        buttonElement.disabled = hasActiveRun && !state.aiRouteInBackground;
        buttonElement.textContent = state.aiRouteInBackground ? "Fechar" : t("ai.agentSettingsCancel");
      });
      document.querySelectorAll("[data-ai-agent-submit]").forEach(function (buttonElement) {
        buttonElement.disabled = !state.isAuthenticated || hasActiveRun;
        buttonElement.textContent = hasActiveRun
          ? t("ai.agentSettingsSubmitting")
          : t("ai.agentSettingsSubmit");
      });

      if (aiAgentModal) {
        aiAgentModal.setAttribute("aria-busy", hasActiveRun ? "true" : "false");
      }

      if (!aiAgentFeedback) {
        return;
      }

      let feedbackMessage = "";
      if (state.aiAgentFeedbackKey) {
        const translatedFeedback = t(state.aiAgentFeedbackKey, state.aiAgentFeedbackValues || undefined);
        feedbackMessage = translatedFeedback && translatedFeedback !== state.aiAgentFeedbackKey
          ? translatedFeedback
          : String(state.aiAgentFeedbackMessage || "").trim() || translatedFeedback;
      } else {
        feedbackMessage = String(state.aiAgentFeedbackMessage || "").trim();
      }
      if (!feedbackMessage) {
        aiAgentFeedback.hidden = true;
        aiAgentFeedback.textContent = "";
        aiAgentFeedback.dataset.tone = state.aiAgentFeedbackTone || "info";
        return;
      }

      aiAgentFeedback.hidden = false;
      aiAgentFeedback.textContent = feedbackMessage;
      aiAgentFeedback.dataset.tone = state.aiAgentFeedbackTone || "info";
      syncAiMenuControls();
    }

    function getTransportAiSettingsProjectCatalogStatus() {
      const normalizedStatus = String(state.aiSettingsProjectCatalogStatus || "").trim().toLowerCase();
      return Object.prototype.hasOwnProperty.call(AI_SETTINGS_PROJECT_CATALOG_STATUS, normalizedStatus)
        ? AI_SETTINGS_PROJECT_CATALOG_STATUS[normalizedStatus]
        : AI_SETTINGS_PROJECT_CATALOG_STATUS.idle;
    }

    function setTransportAiSettingsProjectCatalogStatus(status) {
      state.aiSettingsProjectCatalogStatus = Object.prototype.hasOwnProperty.call(AI_SETTINGS_PROJECT_CATALOG_STATUS, status)
        ? AI_SETTINGS_PROJECT_CATALOG_STATUS[status]
        : AI_SETTINGS_PROJECT_CATALOG_STATUS.idle;
    }

    function clearTransportAiSettingsProjectSelection() {
      state.aiSettingsSelectedProjectId = null;
      state.aiSettingsDraft = getDefaultTransportAiSettingsDraft();
      state.aiSettingsLoadedProvider = DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER;
      state.aiSettingsHasApiKey = false;
      state.aiSettingsApiKeyHint = "";
      state.aiSettingsHasMapsApiKey = false;
      state.aiSettingsMapsApiKeyHint = "";
    }

    function getTransportAiSettingsProjectRows() {
      const normalizedCatalogProjects = normalizeTransportAiSettingsProjectRows(state.aiSettingsProjects);
      if (normalizedCatalogProjects.length) {
        return normalizedCatalogProjects;
      }
      return normalizeTransportAiSettingsProjectRows(getProjectRows());
    }

    function hasValidTransportAiSettingsProjectSelection(projectId, projectRows) {
      const normalizedProjectId = normalizeTransportAiSettingsProjectId(projectId, null);
      if (!normalizedProjectId) {
        return false;
      }

      return normalizeTransportAiSettingsProjectRows(projectRows).some(function (projectRow) {
        return projectRow.id === normalizedProjectId;
      });
    }

