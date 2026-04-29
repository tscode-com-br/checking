# createTransportPageController

- Nome da funcao: `createTransportPageController`
- Arquivo gerado: `createTransportPageController.md`
- Origem: `sistema/app/static/transport/app.js:1164`
- Escopo original: topo do modulo
- Tema funcional: transporte pagina controller
- Categoria: API + UI + state + date/time
- Responsabilidade: Monta o controller principal do dashboard de transporte, encapsulando estado, autenticacao, tempo real, modais, renderizacao, drag and drop e os fluxos que conversam com a API.
- Entradas: Recebe `dateStore` como contexto imediato para calcular, sincronizar ou executar o fluxo encapsulado.
- Saidas: Retorna um objeto composto, normalmente usado como API local, controller, configuracao calculada ou estrutura intermediaria.
- Funcoes nomeadas internas: `refreshDatePanelLabels`, `setDashboardDateForSilentReload`, `focusVehicleFormField`, `applyStaticTranslations`, `clearRequestCollapseOverridesForKind`, `getRequestSectionCollapsedState`, `getRequestRowCollapsedState`, `setRequestRowCollapsedState`, `applyRequestRowCollapsedVisualState`, `preserveRequestSectionScrollPosition`, `syncRequestSectionCollapsedRowsInDom`, `toggleRequestRowCollapsed`, ... (+82 filhas nomeadas)
- Dependencias observadas: `state`, `applyTransportVehicleSeatDefaults`, `applyTransportVehicleToleranceDefault`, `applyVehicleFormDefaults`, `buildVehicleCreatePayload`, `buildVehiclePassengerAwarenessRows`, `buildVehiclePassengerPreviewRows`, `canRequestBeDroppedOnVehicle`, `clearElement`, `createEmptyState`, `createNode`, `formatIsoDate`
- Endpoints/rotas envolvidos: `GET /api/transport/auth/session`, `POST /api/transport/auth/verify`, `POST /api/transport/auth/logout`, `SSE /api/transport/stream`, `GET /api/transport/dashboard`, `GET /api/transport/settings`, `PUT /api/transport/settings`, `PUT /api/transport/date-settings`, `POST /api/transport/vehicles`, `DELETE /api/transport/vehicles/{schedule_id}?service_date=...`, `POST /api/transport/requests/reject`, `POST /api/transport/assignments`
- Efeitos colaterais:
- Aciona integracao de rede diretamente nesta funcao ou em chamada generica disparada por ela.
- Le e/ou altera `state`, o estado interno do controller da pagina.
- Manipula DOM, atributos, classes CSS ou elementos renderizados da interface.
- Agenda ou cancela trabalho assincrono no navegador.
- Observacao para agentes: Esta funcao foi extraida para consulta e indexacao. Se o escopo original for interno, a execucao real depende do fechamento e das referencias disponiveis no arquivo fonte.

## Codigo

```js
function createTransportPageController(dateStore) {
    const requestContainers = {};
    const vehicleContainers = {};
    const state = {
      dashboard: null,
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
      authVerifyToken: 0,
      authVerifyTimer: null,
      realtimeConnected: false,
      realtimeEventStream: null,
      realtimeRefreshTimer: null,
      settingsLoaded: false,
      settingsLoading: false,
      settingsSaving: false,
      languageLoading: false,
      workToHomeTime: DEFAULT_WORK_TO_HOME_TIME,
      lastUpdateTime: DEFAULT_LAST_UPDATE_TIME,
      vehicleSeatDefaults: Object.assign({}, DEFAULT_VEHICLE_SEAT_COUNT),
      vehicleToleranceDefaultMinutes: DEFAULT_VEHICLE_TOLERANCE_MINUTES,
      routeTimeSaving: false,
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
    const settingsPreferencesTitle = document.querySelector("[data-settings-preferences-title]");
    const settingsVehicleDefaultsTitle = document.querySelector("[data-settings-vehicle-defaults-title]");
    const settingsLanguageLabel = document.querySelector("[data-settings-language-label]");
    const settingsLanguageSelect = document.querySelector("[data-settings-language-select]");
    const settingsTimeLabel = document.querySelector("[data-settings-time-label]");
    const settingsTimeInput = document.querySelector("[data-settings-work-to-home-time]");
    const settingsLastUpdateLabel = document.querySelector("[data-settings-last-update-label]");
    const settingsLastUpdateInput = document.querySelector("[data-settings-last-update-time]");
    const settingsTimeNote = document.querySelector("[data-settings-time-note]");
    const settingsVehicleDefaultsNote = document.querySelector("[data-settings-vehicle-defaults-note]");
    const settingsDefaultToleranceLabel = document.querySelector("[data-settings-default-tolerance-label]");
    const settingsDefaultToleranceInput = document.querySelector("[data-settings-default-tolerance]");
    const settingsCloseButton = document.querySelector("[data-settings-close-button]");
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
    const vehicleModal = document.querySelector("[data-vehicle-modal]");
    const vehicleForm = document.querySelector("[data-vehicle-form]");
    const modalScopeLabel = document.querySelector("[data-modal-scope-label]");
    const modalScopeNote = document.querySelector("[data-modal-scope-note]");
    const vehicleModalFeedback = document.querySelector("[data-vehicle-modal-feedback]");
    const extraServiceDateField = document.querySelector("[data-extra-service-date-field]");
    const extraDepartureField = document.querySelector("[data-extra-departure-field]");
    const extraRouteField = document.querySelector("[data-extra-route-field]");
    const weekendPersistenceFields = Array.from(document.querySelectorAll("[data-weekend-persistence-field]"));
    const regularPersistenceFields = Array.from(document.querySelectorAll("[data-regular-persistence-field]"));
    const routeTimePopover = document.querySelector("[data-route-time-popover]");
    const routeTimeLabel = document.querySelector("[data-route-time-label]");
    const routeTimeInput = document.querySelector("[data-route-time-input]");
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

    function applyStaticTranslations() {
      if (typeof document === "undefined") {
        return;
      }

      document.documentElement.lang = getActiveLanguageCode();
      document.title = t("document.title");

      const brandKicker = document.querySelector(".transport-topbar-brand .transport-topbar-kicker");
      const brandTitle = document.querySelector(".transport-topbar-brand .transport-topbar-title");
      const supportKicker = document.querySelector(".transport-topbar-support .transport-topbar-kicker");
      const authLabels = document.querySelectorAll(".transport-auth-label");
      const requestSectionTitles = document.querySelectorAll(".transport-request-section .transport-section-title-link");
      const paneLinks = document.querySelectorAll(".transport-pane-title-link");
      const addVehicleButtons = document.querySelectorAll("[data-open-vehicle-modal]");
      const modalFieldLabels = vehicleForm ? vehicleForm.querySelectorAll(".transport-field > span") : [];
      const weekendLabels = weekendPersistenceFields.map(function (fieldElement) {
        return fieldElement.querySelector("span");
      });
      const regularLabels = regularPersistenceFields.map(function (fieldElement) {
        return fieldElement.querySelector("span");
      });
      const modalActionButtons = vehicleForm ? vehicleForm.querySelectorAll(".transport-modal-actions button") : [];
      const typeOptions = vehicleForm && vehicleForm.elements.tipo ? Array.from(vehicleForm.elements.tipo.options) : [];
      const routeOptions = vehicleForm && vehicleForm.elements.route_kind ? Array.from(vehicleForm.elements.route_kind.options) : [];

      if (brandKicker) {
        brandKicker.textContent = t("topbar.brand");
      }
      if (brandTitle) {
        brandTitle.textContent = t("topbar.allocationBoard");
      }
      if (supportKicker) {
        supportKicker.textContent = t("topbar.systemSupport");
      }
      if (routeTimeLabel) {
        routeTimeLabel.textContent = t("settings.workToHomeTime");
      }
      if (authLabels[0]) {
        authLabels[0].textContent = t("auth.key");
      }
      if (authLabels[1]) {
        authLabels[1].textContent = t("auth.pass");
      }

      const projectListTitle = document.querySelector("[data-project-list-toggle]");
      const userListTitle = document.querySelector("[data-user-list-title]");
      if (projectListTitle) {
        projectListTitle.textContent = t("panes.projectList");
      }
      if (userListTitle) {
        userListTitle.textContent = t("panes.userList");
      }
      if (requestSectionTitles[0]) {
        requestSectionTitles[0].textContent = getRequestTitle("extra");
      }
      if (requestSectionTitles[1]) {
        requestSectionTitles[1].textContent = getRequestTitle("weekend");
      }
      if (requestSectionTitles[2]) {
        requestSectionTitles[2].textContent = getRequestTitle("regular");
      }
      if (paneLinks[0]) {
        paneLinks[0].textContent = t("vehicles.lists.extra");
      }
      if (paneLinks[1]) {
        paneLinks[1].textContent = t("vehicles.lists.weekend");
      }
      if (paneLinks[2]) {
        paneLinks[2].textContent = t("vehicles.lists.regular");
      }
      addVehicleButtons.forEach(function (buttonElement) {
        const scope = buttonElement.dataset.openVehicleModal;
        if (!scope) {
          return;
        }
        buttonElement.setAttribute("aria-label", t(`vehicles.addAria.${scope}`));
      });
      if (settingsTrigger) {
        settingsTrigger.textContent = t("settings.dashboardLink");
        settingsTrigger.setAttribute("aria-label", t("settings.openAria"));
      }

      if (modalScopeLabel) {
        modalScopeLabel.textContent = mapScopeTitle(vehicleModal && vehicleModal.dataset.scope ? vehicleModal.dataset.scope : "regular");
      }
      const modalTitle = document.getElementById("transport-vehicle-modal-title");
      if (modalTitle) {
        modalTitle.textContent = t("modal.title");
      }
      document.querySelectorAll("[data-close-vehicle-modal]").forEach(function (buttonElement) {
        if (buttonElement.classList.contains("transport-modal-close")) {
          buttonElement.setAttribute("aria-label", t("modal.closeVehicleAria"));
          return;
        }
        buttonElement.textContent = t("modal.actions.cancel");
      });
      if (modalFieldLabels[0]) {
        modalFieldLabels[0].textContent = t("modal.fields.type");
      }
      if (modalFieldLabels[1]) {
        modalFieldLabels[1].textContent = t("modal.fields.plate");
      }
      if (modalFieldLabels[2]) {
        modalFieldLabels[2].textContent = t("modal.fields.color");
      }
      if (modalFieldLabels[3]) {
        modalFieldLabels[3].textContent = t("modal.fields.places");
      }
      if (modalFieldLabels[4]) {
        modalFieldLabels[4].textContent = t("modal.fields.tolerance");
      }
      if (modalFieldLabels[5]) {
        modalFieldLabels[5].textContent = t("modal.fields.departureDate");
      }
      if (modalFieldLabels[6]) {
        modalFieldLabels[6].textContent = t("modal.fields.departureTime");
      }
      if (modalFieldLabels[7]) {
        modalFieldLabels[7].textContent = t("modal.fields.route");
      }
      if (typeOptions[0]) {
        typeOptions[0].text = t("modal.options.car");
      }
      if (typeOptions[1]) {
        typeOptions[1].text = t("modal.options.minivan");
      }
      if (typeOptions[2]) {
        typeOptions[2].text = t("modal.options.van");
      }
      if (typeOptions[3]) {
        typeOptions[3].text = t("modal.options.bus");
      }
      if (routeOptions[0]) {
        routeOptions[0].text = getRouteKindLabel("home_to_work");
      }
      if (routeOptions[1]) {
        routeOptions[1].text = getRouteKindLabel("work_to_home");
      }
      if (weekendLabels[0]) {
        weekendLabels[0].textContent = t("modal.fields.everySaturday");
      }
      if (weekendLabels[1]) {
        weekendLabels[1].textContent = t("modal.fields.everySunday");
      }
      if (regularLabels[0]) {
        regularLabels[0].textContent = t("modal.fields.everyMonday");
      }
      if (regularLabels[1]) {
        regularLabels[1].textContent = t("modal.fields.everyTuesday");
      }
      if (regularLabels[2]) {
        regularLabels[2].textContent = t("modal.fields.everyWednesday");
      }
      if (regularLabels[3]) {
        regularLabels[3].textContent = t("modal.fields.everyThursday");
      }
      if (regularLabels[4]) {
        regularLabels[4].textContent = t("modal.fields.everyFriday");
      }
      if (modalActionButtons[1]) {
        modalActionButtons[1].textContent = t("modal.actions.save");
      }

      const settingsTitle = document.getElementById("transport-settings-modal-title");
      if (settingsTitle) {
        settingsTitle.textContent = t("settings.title");
      }
      document.querySelectorAll("[data-close-settings-modal]").forEach(function (buttonElement) {
        if (buttonElement.classList.contains("transport-modal-close")) {
          buttonElement.setAttribute("aria-label", t("settings.closeAria"));
          return;
        }
        buttonElement.textContent = t("settings.close");
      });
      if (settingsPreferencesTitle) {
        settingsPreferencesTitle.textContent = t("settings.preferences");
      }
      if (settingsVehicleDefaultsTitle) {
        settingsVehicleDefaultsTitle.textContent = t("settings.vehicleDefaults");
      }
      if (settingsLanguageLabel) {
        settingsLanguageLabel.textContent = t("settings.languages");
      }
      if (settingsTimeLabel) {
        settingsTimeLabel.textContent = t("settings.workToHomeTime");
      }
      if (settingsLastUpdateLabel) {
        settingsLastUpdateLabel.textContent = t("settings.lastUpdateTime");
      }
      if (settingsTimeNote) {
        settingsTimeNote.textContent = t("settings.workToHomeNote");
      }
      if (settingsVehicleDefaultsNote) {
        settingsVehicleDefaultsNote.textContent = t("settings.vehicleDefaultsNote");
      }
      if (settingsDefaultToleranceLabel) {
        settingsDefaultToleranceLabel.textContent = t("settings.standardTolerance");
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
      if (settingsCloseButton) {
        settingsCloseButton.textContent = t("settings.close");
      }

      const transportLayout = document.getElementById("tela01");
      if (transportLayout) {
        transportLayout.setAttribute("aria-label", t("layout.transportLayout"));
      }
      if (transportTopbar) {
        transportTopbar.setAttribute("aria-label", t("layout.quickActions"));
      }
      const datePanel = document.querySelector("[data-date-panel]");
      if (datePanel) {
        datePanel.setAttribute("aria-label", t("layout.selectedServiceDate"));
      }
      const previousDateButton = document.querySelector('[data-date-shift="-1"]');
      if (previousDateButton) {
        previousDateButton.setAttribute("aria-label", t("layout.previousServiceDate"));
      }
      const nextDateButton = document.querySelector('[data-date-shift="1"]');
      if (nextDateButton) {
        nextDateButton.setAttribute("aria-label", t("layout.nextServiceDate"));
      }
      const dateLink = document.querySelector("[data-date-link]");
      if (dateLink) {
        dateLink.setAttribute("aria-label", t("layout.returnServiceDateToToday"));
      }
      const authArea = document.querySelector(".transport-topbar-auth");
      if (authArea) {
        authArea.setAttribute("aria-label", t("layout.transportAccessFields"));
      }
      if (requestUserButton) {
        requestUserButton.setAttribute("aria-label", t("layout.requestUserCreation"));
      }
      const layoutDividers = document.querySelectorAll("[data-resize]");
      if (layoutDividers[0]) {
        layoutDividers[0].setAttribute("aria-label", t("layout.resizeMenuMain"));
      }
      const mainPanels = document.getElementById("tela01principal");
      if (mainPanels) {
        mainPanels.setAttribute("aria-label", t("layout.transportMainPanels"));
      }
      const requestSections = document.querySelectorAll(".transport-request-section");
      if (requestSections[0]) {
        requestSections[0].setAttribute("aria-label", t("layout.extraCarRequests"));
      }
      if (requestSections[1]) {
        requestSections[1].setAttribute("aria-label", t("layout.weekendCarRequests"));
      }
      if (requestSections[2]) {
        requestSections[2].setAttribute("aria-label", t("layout.regularCarRequests"));
      }
      if (layoutDividers[1]) {
        layoutDividers[1].setAttribute("aria-label", t("layout.resizeColumns"));
      }
      const carPanels = document.getElementById("tela01main_dir");
      if (carPanels) {
        carPanels.setAttribute("aria-label", t("layout.transportCarPanels"));
      }
      if (layoutDividers[2]) {
        layoutDividers[2].setAttribute("aria-label", t("layout.resizeExtraWeekend"));
      }
      if (layoutDividers[3]) {
        layoutDividers[3].setAttribute("aria-label", t("layout.resizeWeekendRegular"));
      }
      const footer = document.querySelector(".transport-footer-status");
      if (footer) {
        footer.setAttribute("aria-label", t("layout.transportNotifications"));
      }

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

    function readTransportSettingsDraft() {
      return {
        workToHomeTime: settingsTimeInput ? settingsTimeInput.value : state.workToHomeTime,
        lastUpdateTime: settingsLastUpdateInput ? settingsLastUpdateInput.value : state.lastUpdateTime,
        defaultCarSeats: settingsDefaultSeatInputs.carro ? settingsDefaultSeatInputs.carro.value : state.vehicleSeatDefaults.carro,
        defaultMinivanSeats: settingsDefaultSeatInputs.minivan ? settingsDefaultSeatInputs.minivan.value : state.vehicleSeatDefaults.minivan,
        defaultVanSeats: settingsDefaultSeatInputs.van ? settingsDefaultSeatInputs.van.value : state.vehicleSeatDefaults.van,
        defaultBusSeats: settingsDefaultSeatInputs.onibus ? settingsDefaultSeatInputs.onibus.value : state.vehicleSeatDefaults.onibus,
        defaultToleranceMinutes: settingsDefaultToleranceInput ? settingsDefaultToleranceInput.value : state.vehicleToleranceDefaultMinutes,
      };
    }

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
        setStatus(getTransportLockedMessage(), "warning");
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
            setStatus(t("status.settingsSaved"), "success");
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

    function clearPendingRealtimeRefresh() {
      if (state.realtimeRefreshTimer !== null) {
        globalScope.clearTimeout(state.realtimeRefreshTimer);
        state.realtimeRefreshTimer = null;
      }
    }

    function stopRealtimeUpdates() {
      clearPendingRealtimeRefresh();
      if (state.realtimeEventStream) {
        state.realtimeEventStream.close();
        state.realtimeEventStream = null;
      }
      state.realtimeConnected = false;
    }

    function requestDashboardRefresh(options) {
      const refreshOptions = options || {};
      if (!state.isAuthenticated) {
        return;
      }

      clearPendingRealtimeRefresh();
      state.realtimeRefreshTimer = globalScope.setTimeout(function () {
        state.realtimeRefreshTimer = null;
        loadDashboard(dateStore.getValue(), Object.assign({ announce: false }, refreshOptions));
      }, TRANSPORT_REALTIME_DEBOUNCE_MS);
    }

    function startRealtimeUpdates() {
      stopRealtimeUpdates();
      if (typeof globalScope.EventSource !== "function") {
        return;
      }

      state.realtimeEventStream = new globalScope.EventSource(`${TRANSPORT_API_PREFIX}/stream`);
      state.realtimeEventStream.onopen = function () {
        state.realtimeConnected = true;
      };
      state.realtimeEventStream.onmessage = function () {
        state.realtimeConnected = true;
        requestDashboardRefresh({ announce: false });
      };
      state.realtimeEventStream.onerror = function () {
        state.realtimeConnected = false;
      };
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
        stopRealtimeUpdates();
      }

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
      clearPendingAuthVerification();
      setAuthenticationState(false, null, { resetInputs: true, clearDashboard: true });
      requestJson(`${TRANSPORT_API_PREFIX}/auth/logout`, { method: "POST" }).catch(function () {});
      setStatus(message || getTransportLockedMessage(), "warning");
    }

    function handleProtectedRequestError(error, fallbackMessage) {
      if (error && Number(error.status) === 401) {
        clearTransportSession(getTransportSessionExpiredMessage());
        return true;
      }
      setStatus(localizeTransportApiMessage(error && error.message) || fallbackMessage, "error");
      if (error && (Number(error.status) === 404 || Number(error.status) === 409)) {
        requestDashboardRefresh({ announce: false });
      }
      return false;
    }

    function openUserCreationRequest() {
      if (typeof globalScope.open === "function") {
        globalScope.open("../admin", "_blank", "noopener");
      }
      setStatus(t("status.openAdminToRequestUser"), "info");
    }

    function loadTransportSettings(options) {
      const nextOptions = options || {};
      if (!state.isAuthenticated) {
        state.workToHomeTime = state.workToHomeTime || DEFAULT_WORK_TO_HOME_TIME;
        state.lastUpdateTime = state.lastUpdateTime || DEFAULT_LAST_UPDATE_TIME;
        state.vehicleSeatDefaults = applyTransportVehicleSeatDefaults(state.vehicleSeatDefaults);
        state.vehicleToleranceDefaultMinutes = applyTransportVehicleToleranceDefault(state.vehicleToleranceDefaultMinutes);
        syncSettingsControls();
        return Promise.resolve(null);
      }

      state.settingsLoading = true;
      syncSettingsControls();
      return requestJson(`${TRANSPORT_API_PREFIX}/settings`)
        .then(function (response) {
          state.settingsLoaded = true;
          state.workToHomeTime = String(
            response && response.work_to_home_time ? response.work_to_home_time : DEFAULT_WORK_TO_HOME_TIME
          );
          state.lastUpdateTime = String(
            response && response.last_update_time ? response.last_update_time : DEFAULT_LAST_UPDATE_TIME
          );
          state.vehicleSeatDefaults = applyTransportVehicleSeatDefaults(response);
          state.vehicleToleranceDefaultMinutes = applyTransportVehicleToleranceDefault(
            response && response.default_tolerance_minutes !== undefined
              ? response.default_tolerance_minutes
              : state.vehicleToleranceDefaultMinutes
          );
          return response;
        })
        .catch(function (error) {
          handleProtectedRequestError(error, t("status.couldNotLoadSettings"));
          if (nextOptions.silent) {
            return null;
          }
          return null;
        })
        .finally(function () {
          state.settingsLoading = false;
          syncSettingsControls();
          syncRouteTimeControls();
        });
    }

    function saveTransportSettings(nextValues) {
      const previousWorkToHomeTime = state.workToHomeTime;
      const previousLastUpdateTime = state.lastUpdateTime;
      const previousVehicleSeatDefaults = Object.assign({}, state.vehicleSeatDefaults);
      const previousVehicleToleranceDefaultMinutes = state.vehicleToleranceDefaultMinutes;
      const normalizedTime = normalizeTransportTimeValue(
        nextValues && nextValues.workToHomeTime,
        normalizeTransportTimeValue(state.workToHomeTime, DEFAULT_WORK_TO_HOME_TIME)
      );
      const normalizedLastUpdateTime = normalizeTransportTimeValue(
        nextValues && nextValues.lastUpdateTime,
        normalizeTransportTimeValue(state.lastUpdateTime, DEFAULT_LAST_UPDATE_TIME)
      );
      const normalizedSeatDefaults = resolveTransportVehicleSeatDefaults(
        {
          default_car_seats: nextValues && nextValues.defaultCarSeats,
          default_minivan_seats: nextValues && nextValues.defaultMinivanSeats,
          default_van_seats: nextValues && nextValues.defaultVanSeats,
          default_bus_seats: nextValues && nextValues.defaultBusSeats,
        },
        state.vehicleSeatDefaults
      );
      const normalizedToleranceDefault = normalizeVehicleToleranceSetting(
        nextValues && nextValues.defaultToleranceMinutes,
        state.vehicleToleranceDefaultMinutes
      );
      if (!isValidTransportTimeValue(normalizedTime) || !isValidTransportTimeValue(normalizedLastUpdateTime)) {
        syncSettingsControls();
        return Promise.resolve(null);
      }
      if (!state.isAuthenticated) {
        setStatus(getTransportLockedMessage(), "warning");
        syncSettingsControls();
        return Promise.resolve(null);
      }

      state.workToHomeTime = normalizedTime;
      state.lastUpdateTime = normalizedLastUpdateTime;
      state.vehicleSeatDefaults = Object.assign({}, normalizedSeatDefaults);
      state.vehicleToleranceDefaultMinutes = normalizedToleranceDefault;
      applyTransportVehicleSeatDefaults(state.vehicleSeatDefaults);
      applyTransportVehicleToleranceDefault(state.vehicleToleranceDefaultMinutes);
      state.settingsSaving = true;
      syncSettingsControls();
      return requestJson(`${TRANSPORT_API_PREFIX}/settings`, {
        method: "PUT",
        body: JSON.stringify({
          work_to_home_time: normalizedTime,
          last_update_time: normalizedLastUpdateTime,
          default_car_seats: normalizedSeatDefaults.carro,
          default_minivan_seats: normalizedSeatDefaults.minivan,
          default_van_seats: normalizedSeatDefaults.van,
          default_bus_seats: normalizedSeatDefaults.onibus,
          default_tolerance_minutes: normalizedToleranceDefault,
        }),
      })
        .then(function (response) {
          state.settingsLoaded = true;
          state.workToHomeTime = String(
            response && response.work_to_home_time ? response.work_to_home_time : normalizedTime
          );
          state.lastUpdateTime = String(
            response && response.last_update_time ? response.last_update_time : normalizedLastUpdateTime
          );
          state.vehicleSeatDefaults = applyTransportVehicleSeatDefaults(response);
          state.vehicleToleranceDefaultMinutes = applyTransportVehicleToleranceDefault(
            response && response.default_tolerance_minutes !== undefined
              ? response.default_tolerance_minutes
              : normalizedToleranceDefault
          );
          return loadDashboard(dateStore.getValue(), { announce: false }).then(function () {
            setStatus(t("status.settingsSaved"), "success");
            return response;
          });
        })
        .catch(function (error) {
          state.workToHomeTime = previousWorkToHomeTime;
          state.lastUpdateTime = previousLastUpdateTime;
          state.vehicleSeatDefaults = previousVehicleSeatDefaults;
          state.vehicleToleranceDefaultMinutes = previousVehicleToleranceDefaultMinutes;
          applyTransportVehicleSeatDefaults(previousVehicleSeatDefaults);
          applyTransportVehicleToleranceDefault(previousVehicleToleranceDefaultMinutes);
          handleProtectedRequestError(error, t("status.couldNotSaveSettings"));
          return null;
        })
        .finally(function () {
          state.settingsSaving = false;
          syncSettingsControls();
        });
    }

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

    function verifyTransportCredentials(requestToken) {
      const chave = normalizeAuthKeyValue();
      const senha = authPasswordInput ? String(authPasswordInput.value || "") : "";
      if (chave.length !== 4 || !senha) {
        return Promise.resolve(null);
      }

      return requestJson(`${TRANSPORT_API_PREFIX}/auth/verify`, {
        method: "POST",
        body: JSON.stringify({ chave: chave, senha: senha }),
      })
        .then(function (response) {
          if (requestToken !== state.authVerifyToken) {
            return null;
          }

          if (response && response.authenticated && response.user) {
            setAuthenticationState(true, response.user, {});
            setStatus(localizeTransportApiMessage(response.message) || t("status.accessGranted"), "success");
            return Promise.all([
              loadDashboard(dateStore.getValue(), { announce: false }),
              loadTransportSettings({ silent: true }),
            ]);
          }

          setAuthenticationState(false, null, {});
          setStatus(localizeTransportApiMessage(response && response.message) || getTransportLockedMessage(), "warning");
          return null;
        })
        .catch(function (error) {
          if (requestToken !== state.authVerifyToken) {
            return null;
          }
          setStatus(localizeTransportApiMessage(error && error.message) || t("status.couldNotVerify"), "error");
          return null;
        });
    }

    function scheduleTransportVerification() {
      clearPendingAuthVerification();
      const chave = normalizeAuthKeyValue();
      const senha = authPasswordInput ? String(authPasswordInput.value || "") : "";
      if (chave.length !== 4 || !senha) {
        state.authVerifyToken += 1;
        setAuthenticationState(false, null, {});
        setStatus(getTransportLockedMessage(), "warning");
        return;
      }

      state.authVerifyToken += 1;
      const requestToken = state.authVerifyToken;
      state.authVerifyTimer = globalScope.setTimeout(function () {
        state.authVerifyTimer = null;
        verifyTransportCredentials(requestToken);
      }, TRANSPORT_AUTH_VERIFY_DELAY_MS);
    }

    function bootstrapTransportSession() {
      return requestJson(`${TRANSPORT_API_PREFIX}/auth/session`)
        .then(function (response) {
          if (response && response.authenticated && response.user) {
            setAuthenticationState(true, response.user, { fillKey: true });
            setStatus(getDefaultStatusMessage(), "info");
            return Promise.all([
              loadDashboard(dateStore.getValue(), { announce: false }),
              loadTransportSettings({ silent: true }),
            ]);
          }

          setAuthenticationState(false, null, { resetInputs: true, clearDashboard: true });
          setStatus(getTransportLockedMessage(), "warning");
          return null;
        })
        .catch(function () {
          setAuthenticationState(false, null, { resetInputs: true, clearDashboard: true });
          setStatus(getTransportLockedMessage(), "warning");
          return null;
        });
    }

    if (authKeyInput) {
      authKeyInput.addEventListener("input", scheduleTransportVerification);
    }

    if (authPasswordInput) {
      authPasswordInput.addEventListener("input", scheduleTransportVerification);
    }

    if (requestUserButton) {
      requestUserButton.addEventListener("click", openUserCreationRequest);
    }

    if (settingsLanguageSelect) {
      settingsLanguageSelect.addEventListener("change", function () {
        void switchTransportLanguage(settingsLanguageSelect.value);
      });
    }

    if (settingsTimeInput) {
      settingsTimeInput.addEventListener("change", function () {
        void saveTransportSettings(readTransportSettingsDraft());
      });
    }

    if (settingsLastUpdateInput) {
      settingsLastUpdateInput.addEventListener("change", function () {
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

    if (settingsDefaultToleranceInput) {
      settingsDefaultToleranceInput.addEventListener("change", function () {
        void saveTransportSettings(readTransportSettingsDraft());
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

    if (settingsTrigger) {
      settingsTrigger.addEventListener("click", function (event) {
        event.preventDefault();
        openSettingsModal();
      });
    }

    document.querySelectorAll("[data-close-settings-modal]").forEach(function (buttonElement) {
      buttonElement.addEventListener("click", closeSettingsModal);
    });

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
          syncVehicleTypeDependentDefaults(String(vehicleForm.elements.tipo.value || "carro"), vehicleForm);
          });
          vehicleForm.elements.tipo.addEventListener("input", function () {
          syncVehicleTypeDependentDefaults(String(vehicleForm.elements.tipo.value || "carro"), vehicleForm);
        });
      }

      vehicleForm.addEventListener("submit", function (event) {
        event.preventDefault();
        const formData = new FormData(vehicleForm);
        const payload = buildVehicleCreatePayload(formData, getCurrentServiceDateIso(), getSelectedRouteKind());
        const submitButton = vehicleForm.querySelector('button[type="submit"]');
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
          .then(function () {
            const currentDashboardDate = dateStore.getValue();
            let reloadDate = resolveVehicleSaveReloadDate(payload, currentDashboardDate);

            closeVehicleModal();
            setStatus(t("status.vehicleSaved"), "success");
            if (formatIsoDate(reloadDate) !== formatIsoDate(currentDashboardDate)) {
              reloadDate = setDashboardDateForSilentReload(reloadDate);
            }
            return loadDashboard(reloadDate, { announce: false });
          })
          .catch(function (error) {
            setVehicleModalFeedback(localizeTransportApiMessage(error && error.message) || t("status.couldNotSaveVehicle"), "error");
            handleProtectedRequestError(error, t("status.couldNotSaveVehicle"));
          })
          .finally(function () {
            if (submitButton) {
              submitButton.disabled = false;
            }
          });
      });
    }

    function setStatus(message, tone) {
      if (!statusMessage) {
        return;
      }

      statusMessage.textContent = message || getDefaultStatusMessage();
      statusMessage.dataset.tone = tone || "info";
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

    function openSettingsModal() {
      if (!settingsModal) {
        return;
      }
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
      settingsModal.hidden = true;
      if (settingsTrigger) {
        settingsTrigger.setAttribute("aria-expanded", "false");
        if (typeof settingsTrigger.focus === "function") {
          settingsTrigger.focus();
        }
      }
    }

    function syncRouteInputs() {}

    function getSelectedRouteKind() {
      return state.selectedRouteKind || "home_to_work";
    }

    function getRouteKindForVehicle(scope, vehicle) {
      if (scope === "extra" && vehicle && vehicle.route_kind) {
        return vehicle.route_kind;
      }
      return getSelectedRouteKind();
    }

    function getRouteKindForRequestRow(requestRow, fallbackRouteKind) {
      if (
        requestRow
        && requestRow.request_kind === "extra"
        && requestRow.assigned_vehicle
        && requestRow.assigned_vehicle.route_kind
      ) {
        return requestRow.assigned_vehicle.route_kind;
      }
      return fallbackRouteKind || getSelectedRouteKind();
    }

    function getCurrentServiceDateIso() {
      return formatIsoDate(dateStore.getValue());
    }

    function canOpenVehicleModal(scope) {
      if (!state.isAuthenticated) {
        setStatus(getTransportLockedMessage(), "warning");
        return false;
      }
      return true;
    }

    function syncVehicleModalFields(scope) {
      if (!vehicleForm) {
        return;
      }

      const normalizedScope = normalizeVehicleScope(scope);

      if (modalScopeLabel) {
        modalScopeLabel.textContent = mapScopeTitle(normalizedScope);
      }
      if (modalScopeNote) {
        modalScopeNote.textContent = getModalScopeNote(normalizedScope);
      }
      if (extraServiceDateField) {
        extraServiceDateField.hidden = normalizedScope !== "extra";
      }
      if (extraDepartureField) {
        extraDepartureField.hidden = normalizedScope !== "extra";
      }
      if (extraRouteField) {
        extraRouteField.hidden = normalizedScope !== "extra";
      }
      weekendPersistenceFields.forEach(function (fieldElement) {
        fieldElement.hidden = normalizedScope !== "weekend";
      });
      regularPersistenceFields.forEach(function (fieldElement) {
        fieldElement.hidden = normalizedScope !== "regular";
      });
      if (vehicleForm.elements.route_kind) {
        vehicleForm.elements.route_kind.value = getSelectedRouteKind();
        vehicleForm.elements.route_kind.disabled = normalizedScope !== "extra";
      }
      if (vehicleForm.elements.service_date) {
        vehicleForm.elements.service_date.required = normalizedScope === "extra";
        vehicleForm.elements.service_date.disabled = normalizedScope !== "extra";
      }
      if (vehicleForm.elements.service_date && normalizedScope !== "extra") {
        vehicleForm.elements.service_date.value = "";
      }
      if (vehicleForm.elements.departure_time) {
        vehicleForm.elements.departure_time.required = normalizedScope === "extra";
        vehicleForm.elements.departure_time.disabled = normalizedScope !== "extra";
      }
      if (vehicleForm.elements.departure_time && normalizedScope !== "extra") {
        vehicleForm.elements.departure_time.value = "";
      }
      if (vehicleForm.elements.every_saturday) {
        vehicleForm.elements.every_saturday.checked = false;
      }
      if (vehicleForm.elements.every_sunday) {
        vehicleForm.elements.every_sunday.checked = false;
      }
    }

    function openVehicleModal(scope) {
      if (!vehicleModal || !vehicleForm) {
        return;
      }
      const normalizedScope = normalizeVehicleScope(scope);
      if (!canOpenVehicleModal(normalizedScope)) {
        return;
      }
      closeExpandedVehicleDetails({ render: false });
      vehicleModal.hidden = false;
      vehicleModal.dataset.scope = normalizedScope;
      vehicleForm.reset();
      clearVehicleModalFeedback();
      vehicleForm.elements.service_scope.value = normalizedScope;
      applyVehicleFormDefaults("carro", vehicleForm);
      const modalOpenState = resolveVehicleModalOpenState(normalizedScope, getCurrentServiceDateIso());
      if (vehicleForm.elements.service_date) {
        vehicleForm.elements.service_date.value = modalOpenState.serviceDateValue;
      }
      if (vehicleForm.elements.departure_time) {
        vehicleForm.elements.departure_time.value = modalOpenState.departureTimeValue;
      }
      syncVehicleModalFields(normalizedScope);
      if (!focusVehicleFormField(modalOpenState.initialFocusField)) {
        focusVehicleFormField(modalOpenState.fallbackFocusField);
      }
    }

    function closeVehicleModal() {
      if (!vehicleModal || !vehicleForm) {
        return;
      }
      vehicleModal.hidden = true;
      clearVehicleModalFeedback();
      vehicleForm.reset();
    }

    function getRequestsForKind(kind) {
      if (!state.dashboard) {
        return [];
      }
      return Array.isArray(state.dashboard[`${kind}_requests`])
        ? state.dashboard[`${kind}_requests`]
        : [];
    }

    function getProjectRows() {
      if (!state.dashboard) {
        return [];
      }
      return Array.isArray(state.dashboard.projects) ? state.dashboard.projects : [];
    }

    function reconcileProjectVisibility() {
      const nextVisibility = {};
      getProjectRows().forEach(function (projectRow) {
        if (!projectRow || !projectRow.name) {
          return;
        }
        nextVisibility[projectRow.name] = state.projectVisibility[projectRow.name] !== false;
      });
      state.projectVisibility = nextVisibility;
    }

    function hasAnyVisibleProject() {
      const projectNames = Object.keys(state.projectVisibility);
      if (!projectNames.length) {
        return true;
      }
      return projectNames.some(function (projectName) {
        return state.projectVisibility[projectName] !== false;
      });
    }

    function isProjectVisible(projectName) {
      const normalizedProjectName = String(projectName || "").trim();
      if (!normalizedProjectName) {
        return true;
      }
      if (!(normalizedProjectName in state.projectVisibility)) {
        return true;
      }
      return state.projectVisibility[normalizedProjectName] !== false;
    }

    function getVisibleRequestsForKind(kind) {
      return getRequestsForKind(kind).filter(function (requestRow) {
        return isProjectVisible(requestRow.projeto);
      });
    }

    function getVehiclesForScope(scope) {
      if (!state.dashboard) {
        return [];
      }
      return Array.isArray(state.dashboard[`${scope}_vehicles`])
        ? state.dashboard[`${scope}_vehicles`]
        : [];
    }

    function getVehicleRegistryRows(scope) {
      if (!state.dashboard) {
        return [];
      }
      return Array.isArray(state.dashboard[`${scope}_vehicle_registry`])
        ? state.dashboard[`${scope}_vehicle_registry`]
        : [];
    }

    function getAllRequests() {
      return REQUEST_SECTION_ORDER.reduce(function (rows, kind) {
        return rows.concat(getRequestsForKind(kind));
      }, []);
    }

    function getAllVisibleRequests() {
      return REQUEST_SECTION_ORDER.reduce(function (rows, kind) {
        return rows.concat(getVisibleRequestsForKind(kind));
      }, []);
    }

    function getRequestById(requestId) {
      return (
        getAllRequests().find(function (row) {
          return Number(row.id) === Number(requestId);
        }) || null
      );
    }

    function getDraggedRequest() {
      if (state.dragRequestId === null) {
        return null;
      }
      return getRequestById(state.dragRequestId);
    }

    function getVehicleByScopeAndId(scope, vehicleId) {
      return (
        getVehiclesForScope(scope).find(function (vehicle) {
          return Number(vehicle.id) === Number(vehicleId);
        }) || null
      );
    }

    function getPendingAssignmentPreview() {
      if (!state.pendingAssignmentPreview) {
        return null;
      }

      const requestRow = getRequestById(state.pendingAssignmentPreview.requestId);
      const vehicle = getVehicleByScopeAndId(
        state.pendingAssignmentPreview.scope,
        state.pendingAssignmentPreview.vehicleId
      );

      if (!requestRow || !vehicle) {
        return null;
      }

      return {
        requestRow,
        vehicle,
        scope: state.pendingAssignmentPreview.scope,
        routeKind: state.pendingAssignmentPreview.routeKind,
      };
    }

    function getVehicleDetailsKey(scope, vehicleId) {
      return `${scope}:${vehicleId}`;
    }

    function ensureExpandedVehicleStillExists() {
      if (!state.expandedVehicleKey) {
        return;
      }

      const hasVehicle = VEHICLE_SCOPE_ORDER.some(function (scope) {
        return getVehiclesForScope(scope).some(function (vehicle) {
          return getVehicleDetailsKey(scope, vehicle.id) === state.expandedVehicleKey;
        });
      });

      if (!hasVehicle) {
        state.expandedVehicleKey = null;
      }
    }

    function toggleVehicleDetails(scope, vehicleId) {
      const vehicleKey = getVehicleDetailsKey(scope, vehicleId);
      const pendingPreview = getPendingAssignmentPreview();
      if (
        pendingPreview
        && pendingPreview.scope === scope
        && Number(pendingPreview.vehicle.id) === Number(vehicleId)
      ) {
        state.expandedVehicleKey = vehicleKey;
        renderVehiclePanels();
        return;
      }
      state.expandedVehicleKey = state.expandedVehicleKey === vehicleKey ? null : vehicleKey;
      renderVehiclePanels();
    }

    function closeExpandedVehicleDetails(options) {
      const closeOptions = options || {};
      const expandedElements = closeOptions.restoreFocus ? findExpandedVehicleDetailsElements() : null;

      if (!state.expandedVehicleKey && !state.pendingAssignmentPreview) {
        clearElement(vehicleDetailsOverlayHost);
        vehicleDetailsOverlayHost.classList.remove("is-active");
        return;
      }

      state.expandedVehicleKey = null;
      state.pendingAssignmentPreview = null;
      clearElement(vehicleDetailsOverlayHost);
      vehicleDetailsOverlayHost.classList.remove("is-active");

      if (closeOptions.render !== false) {
        renderVehiclePanels();
      }

      if (
        closeOptions.restoreFocus
        && expandedElements
        && expandedElements.anchorButton
        && typeof expandedElements.anchorButton.focus === "function"
      ) {
        if (typeof globalScope.requestAnimationFrame === "function") {
          globalScope.requestAnimationFrame(function () {
            expandedElements.anchorButton.focus();
          });
        } else {
          expandedElements.anchorButton.focus();
        }
      }
    }

    function findExpandedVehicleDetailsElements() {
      if (!state.expandedVehicleKey) {
        return null;
      }

      const anchorButton = document.querySelector(
        `[data-vehicle-details-anchor-key="${state.expandedVehicleKey}"]`
      );
      const detailsPanel = vehicleDetailsOverlayHost.querySelector(
        `[data-vehicle-details-panel-key="${state.expandedVehicleKey}"]`
      );

      if (!anchorButton || !detailsPanel) {
        return null;
      }

      return {
        anchorButton,
        detailsPanel,
      };
    }

    function syncExpandedVehicleDetailsPosition() {
      const expandedElements = findExpandedVehicleDetailsElements();
      if (!expandedElements) {
        clearElement(vehicleDetailsOverlayHost);
        vehicleDetailsOverlayHost.classList.remove("is-active");
        return;
      }

      const anchorRect = expandedElements.anchorButton.getBoundingClientRect();
      const detailsStyles = typeof globalScope.getComputedStyle === "function"
        ? globalScope.getComputedStyle(expandedElements.detailsPanel)
        : null;
      const panelWidth = Math.max(
        1,
        expandedElements.detailsPanel.offsetWidth
        || parsePixelValue(detailsStyles ? detailsStyles.width : "", 264)
      );
      const panelHeight = Math.max(
        1,
        expandedElements.detailsPanel.offsetHeight
        || parsePixelValue(detailsStyles ? detailsStyles.height : "", 248)
      );
      const viewportWidth = Math.max(
        0,
        globalScope.innerWidth
        || (document.documentElement ? document.documentElement.clientWidth : 0)
      );
      const viewportHeight = Math.max(
        0,
        globalScope.innerHeight
        || (document.documentElement ? document.documentElement.clientHeight : 0)
      );
      const nextPosition = resolveVehicleDetailsPosition({
        anchorRect,
        panelWidth,
        panelHeight,
        viewportWidth,
        viewportHeight,
        offset: VEHICLE_DETAILS_PANEL_OFFSET,
        viewportMargin: VEHICLE_DETAILS_VIEWPORT_MARGIN,
      });

      expandedElements.detailsPanel.style.left = `${nextPosition.left}px`;
      expandedElements.detailsPanel.style.top = `${nextPosition.top}px`;
      expandedElements.detailsPanel.dataset.horizontalDirection = nextPosition.horizontalDirection;
      expandedElements.detailsPanel.classList.add("is-positioned");
    }

    function scheduleExpandedVehicleDetailsPositionSync() {
      if (state.expandedVehiclePositionFrame !== null && typeof globalScope.cancelAnimationFrame === "function") {
        globalScope.cancelAnimationFrame(state.expandedVehiclePositionFrame);
        state.expandedVehiclePositionFrame = null;
      }

      if (typeof globalScope.requestAnimationFrame !== "function") {
        syncExpandedVehicleDetailsPosition();
        return;
      }

      state.expandedVehiclePositionFrame = globalScope.requestAnimationFrame(function () {
        state.expandedVehiclePositionFrame = null;
        syncExpandedVehicleDetailsPosition();
      });
    }

    function createPassengerRemoveButton(requestRow, routeKind) {
      const removeButton = createNode("button", "transport-passenger-remove-button", "×");
      const normalizedRouteKind = getRouteKindForRequestRow(requestRow, routeKind);
      const removeLabel = t("misc.removeFromVehicle", { name: String(requestRow && requestRow.nome || "") });

      removeButton.type = "button";
      removeButton.setAttribute("aria-label", removeLabel);
      removeButton.title = removeLabel;
      removeButton.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        void returnRequestRowToPending(requestRow, normalizedRouteKind);
      });
      return removeButton;
    }

    function createVehicleDetailsPanel(vehicle, assignedRows, options) {
      const detailOptions = options || {};
      const previewRequestRow = detailOptions.previewRequestRow || null;
      const detailsPanel = createNode("div", "transport-vehicle-details");
      const passengerTableShell = createNode("div", "transport-vehicle-passenger-table-shell");
      const passengerTable = createNode("table", "transport-vehicle-passenger-table");
      const tableBody = createNode("tbody");
      const passengerSourceRows = buildVehiclePassengerPreviewRows(assignedRows, previewRequestRow);

      buildVehiclePassengerAwarenessRows(
        passengerSourceRows,
        VEHICLE_DETAILS_MAX_ROWS
      ).forEach(function (row, index) {
        const tableRow = createNode("tr", "transport-vehicle-passenger-row");
        const nameCell = createNode("td", "transport-vehicle-passenger-name", row.name);
        const statusCell = createNode("td", "transport-vehicle-passenger-status");
        const sourceRequestRow = passengerSourceRows[index] || null;
        const isPreviewRow = Boolean(
          previewRequestRow
          && sourceRequestRow
          && Number(sourceRequestRow.id) === Number(previewRequestRow.id)
        );

        if (!row.name) {
          nameCell.innerHTML = "&nbsp;";
        }

        if (sourceRequestRow && !isPreviewRow) {
          statusCell.appendChild(createPassengerRemoveButton(sourceRequestRow, detailOptions.routeKind));
        } else {
          statusCell.innerHTML = "&nbsp;";
        }
        tableRow.appendChild(nameCell);
        tableRow.appendChild(statusCell);
        tableBody.appendChild(tableRow);
      });

      passengerTable.appendChild(tableBody);
      passengerTableShell.appendChild(passengerTable);
      detailsPanel.appendChild(passengerTableShell);

      if (previewRequestRow) {
        const previewActions = createNode("div", "transport-vehicle-preview-actions");
        const cancelButton = createNode("button", "transport-secondary-button", t("modal.actions.cancel"));
        const confirmButton = createNode("button", "transport-primary-button", t("misc.confirm"));

        cancelButton.type = "button";
        confirmButton.type = "button";

        cancelButton.addEventListener("click", function (event) {
          event.preventDefault();
          event.stopPropagation();
          state.pendingAssignmentPreview = null;
          renderRequestTables();
          renderVehiclePanels();
        });

        confirmButton.addEventListener("click", function (event) {
          event.preventDefault();
          event.stopPropagation();
          if (!state.dashboard) {
            return;
          }

          submitAssignment({
            request_id: previewRequestRow.id,
            service_date: state.dashboard.selected_date,
            route_kind: detailOptions.routeKind || getRouteKindForVehicle(vehicle.service_scope, vehicle),
            status: "confirmed",
            vehicle_id: vehicle.id,
          })
            .then(function (result) {
              if (result === null) {
                return;
              }
              state.pendingAssignmentPreview = null;
              renderRequestTables();
              renderVehiclePanels();
            })
            .catch(function () {});
        });

        previewActions.appendChild(cancelButton);
        previewActions.appendChild(confirmButton);
        detailsPanel.appendChild(previewActions);
        return detailsPanel;
      }

      const deleteButton = createNode("button", "transport-vehicle-delete-button", t("misc.delete"));
      deleteButton.type = "button";
      deleteButton.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        removeVehicleFromRoute(vehicle);
      });
      detailsPanel.insertBefore(deleteButton, passengerTableShell);
      return detailsPanel;
    }

    function renderProjectList() {
      if (projectListPanel) {
        projectListPanel.hidden = !state.projectListOpen;
      }
      if (projectListToggle) {
        projectListToggle.setAttribute("aria-expanded", String(state.projectListOpen));
      }
      if (!projectListContainer) {
        return;
      }

      clearElement(projectListContainer);
      const projectRows = getProjectRows();
      if (!projectRows.length) {
        projectListContainer.appendChild(createEmptyState(t("empty.noProjectsAvailable")));
        return;
      }

      projectRows.forEach(function (projectRow) {
        const label = createNode("label", "transport-project-chip");
        const checkbox = document.createElement("input");
        const text = createNode("span", "transport-project-chip-label", projectRow.name);

        checkbox.type = "checkbox";
        checkbox.checked = state.projectVisibility[projectRow.name] !== false;
        label.classList.toggle("is-selected", checkbox.checked);
        checkbox.addEventListener("change", function () {
          state.projectVisibility[projectRow.name] = checkbox.checked;
          renderDashboard();
        });

        label.appendChild(checkbox);
        label.appendChild(text);
        projectListContainer.appendChild(label);
      });
    }

    function createRequestMetaLine(requestRow) {
      const metaParts = [];
      if (requestRow.service_date) {
        const parsedServiceDate = parseStoredTransportDate(requestRow.service_date);
        metaParts.push(parsedServiceDate ? formatTransportDate(parsedServiceDate) : String(requestRow.service_date));
      }
      if (requestRow.requested_time) {
        metaParts.push(String(requestRow.requested_time));
      }
      if (requestRow.assigned_vehicle) {
        metaParts.push(t("misc.assignedTo", { plate: requestRow.assigned_vehicle.placa }));
      }
      if (requestRow.response_message) {
        metaParts.push(requestRow.response_message);
      }
      return metaParts.join(" | ");
    }

    function clearRequestRowStateClass(className) {
      Object.values(requestContainers).forEach(function (container) {
        if (!container) {
          return;
        }

        container.querySelectorAll(`.transport-request-row.${className}`).forEach(function (rowElement) {
          rowElement.classList.remove(className);
        });
      });
    }

    function renderRequestTables() {
      REQUEST_SECTION_ORDER.forEach(function (kind) {
        const container = requestContainers[kind];
        const requestRows = getVisibleRequestsForKind(kind);
        clearElement(container);
        if (!container) {
          return;
        }

        if (!hasAnyVisibleProject()) {
          container.appendChild(createEmptyState(t("empty.noProjectsSelected")));
          return;
        }

        if (!requestRows.length) {
          container.appendChild(createEmptyState(t("empty.noRows", { title: getRequestTitle(kind) })));
          return;
        }

        requestRows.forEach(function (requestRow) {
          const rowShell = createNode("div", "transport-request-row-shell");
          const rowButton = createNode("div", `transport-request-row is-${requestRow.assignment_status}`);
          const rejectButton = createNode("button", "transport-request-reject-button", "X");
          const requestMatchesSelectedDate = !state.dashboard
            || String(requestRow.service_date || "") === String(state.dashboard.selected_date || "");
          const metaLine = createRequestMetaLine(requestRow);
          rowButton.draggable = requestMatchesSelectedDate;
          rowButton.dataset.requestId = String(requestRow.id);
          rowButton.classList.toggle("is-readonly", !requestMatchesSelectedDate);
          rowButton.classList.toggle("is-dragging", Number(state.dragRequestId) === Number(requestRow.id));
          rowButton.classList.toggle(
            "is-previewing",
            !!state.pendingAssignmentPreview && Number(state.pendingAssignmentPreview.requestId) === Number(requestRow.id)
          );
          rowButton.classList.toggle("is-collapsed", getRequestRowCollapsedState(requestRow));
          rowButton.tabIndex = 0;
          rowButton.setAttribute("role", "button");
          rowButton.setAttribute("aria-expanded", String(!getRequestRowCollapsedState(requestRow)));
          rowShell.classList.toggle("is-collapsed", getRequestRowCollapsedState(requestRow));

          const nameCell = createNode("span", "transport-request-primary", requestRow.nome);
          const addressCell = createNode("span", "transport-request-secondary", requestRow.end_rua || t("misc.addressPending"));
          const zipCell = createNode("span", "transport-request-secondary transport-request-zip", requestRow.zip || t("misc.zipPending"));

          if (shouldHighlightRequestName(requestRow.assignment_status)) {
            nameCell.classList.add("is-attention");
          }

          rowButton.appendChild(nameCell);
          rowButton.appendChild(addressCell);
          rowButton.appendChild(zipCell);
          if (metaLine) {
            rowButton.appendChild(createNode("span", "transport-request-meta", metaLine));
          }

          rejectButton.type = "button";
          rejectButton.setAttribute("aria-label", t("misc.reject"));
          rejectButton.title = t("misc.reject");
          rejectButton.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            void rejectRequestRow(requestRow);
          });

          rowButton.addEventListener("dragstart", function (event) {
            state.pendingAssignmentPreview = null;
            clearRequestRowStateClass("is-previewing");
            clearRequestRowStateClass("is-dragging");
            state.dragRequestId = requestRow.id;
            rowButton.classList.add("is-dragging");
            if (event.dataTransfer) {
              event.dataTransfer.effectAllowed = "move";
              event.dataTransfer.setData("text/plain", String(requestRow.id));
            }
            renderVehiclePanels();
          });

          rowButton.addEventListener("dragend", function () {
            rowButton.classList.remove("is-dragging");
            state.dragRequestId = null;
            renderRequestTables();
            renderVehiclePanels();
          });

          rowButton.addEventListener("click", function () {
            toggleRequestRowCollapsed(requestRow, rowButton);
          });

          rowButton.addEventListener("keydown", function (event) {
            if (event.key !== "Enter" && event.key !== " ") {
              return;
            }
            event.preventDefault();
            toggleRequestRowCollapsed(requestRow, rowButton);
          });

          rowShell.appendChild(rowButton);
          rowShell.appendChild(rejectButton);
          container.appendChild(rowShell);
        });
      });

      syncRequestSectionToggleState();
    }

    function groupAssignedRequestsByVehicle(scope) {
      return groupAssignedRequestsByVehicleForDate(
        getRequestsForKind(scope),
        state.dashboard ? state.dashboard.selected_date : ""
      );
    }

    function submitAssignment(payload) {
      return requestJson(`${TRANSPORT_API_PREFIX}/assignments`, {
        method: "POST",
        body: JSON.stringify(payload),
      }).then(function () {
        setStatus(t("status.allocationUpdated"), "success");
        return loadDashboard(dateStore.getValue(), { announce: false });
      }).catch(function (error) {
        if (handleProtectedRequestError(error, t("status.couldNotUpdateAllocation"))) {
          return null;
        }
        throw error;
      });
    }

    function rejectRequestRow(requestRow) {
      if (!requestRow || !requestRow.id || !requestRow.service_date) {
        setStatus(t("status.couldNotRejectSelectedRequest"), "error");
        return Promise.resolve();
      }

      return requestJson(`${TRANSPORT_API_PREFIX}/requests/reject`, {
        method: "POST",
        body: JSON.stringify({
          request_id: requestRow.id,
          service_date: requestRow.service_date,
          route_kind: getRouteKindForRequestRow(requestRow),
        }),
      }).then(function () {
        setStatus(t("status.requestRejected"), "success");
        return loadDashboard(dateStore.getValue(), { announce: false });
      }).catch(function (error) {
        if (handleProtectedRequestError(error, t("status.couldNotRejectSelectedRequest"))) {
          return null;
        }
        throw error;
      });
    }

    function returnRequestRowToPending(requestRow, routeKind) {
      if (!requestRow || !requestRow.id || !requestRow.service_date) {
        setStatus(t("status.couldNotUpdateAllocation"), "error");
        return Promise.resolve();
      }

      return submitAssignment({
        request_id: requestRow.id,
        service_date: requestRow.service_date,
        route_kind: routeKind || getSelectedRouteKind(),
        status: "pending",
      }).then(function (result) {
        if (result === null) {
          return null;
        }
        state.pendingAssignmentPreview = null;
        renderRequestTables();
        renderVehiclePanels();
        return result;
      }).catch(function () {});
    }

    function removeVehicleFromRoute(vehicle) {
      if (!vehicle || vehicle.schedule_id === null || vehicle.schedule_id === undefined) {
        setStatus(t("warnings.vehicleCannotBeRemoved"), "error");
        return Promise.resolve();
      }

      const deleteServiceDate = vehicle.service_date || getCurrentServiceDateIso();

      return requestJson(
        `${TRANSPORT_API_PREFIX}/vehicles/${encodeURIComponent(String(vehicle.schedule_id))}?service_date=${encodeURIComponent(deleteServiceDate)}`,
        {
          method: "DELETE",
        }
      )
        .then(function () {
          setStatus(t("status.vehicleDeleted"), "success");
          return loadDashboard(dateStore.getValue(), { announce: false });
        })
        .catch(function (error) {
          handleProtectedRequestError(error, t("status.couldNotDeleteVehicle"));
        });
    }

    function createVehicleIconButton(scope, vehicle, assignedRows) {
      const tileElement = createNode("div", "transport-vehicle-tile");
      const vehicleButton = createNode("button", "transport-vehicle-button");
      const assignedCount = assignedRows.length;
      const effectiveDepartureTime = getEffectiveWorkToHomeDepartureTime(state.dashboard, state.workToHomeTime);
      const departureTime = getVehicleDepartureTime(vehicle, effectiveDepartureTime, scope);
      const vehicleDetailsKey = getVehicleDetailsKey(scope, vehicle.id);
      const draggedRequest = getDraggedRequest();
      const pendingPreview = getPendingAssignmentPreview();
      const previewRequestRow = pendingPreview
        && pendingPreview.scope === scope
        && Number(pendingPreview.vehicle.id) === Number(vehicle.id)
        ? pendingPreview.requestRow
        : null;
      const isDropTarget = canRequestBeDroppedOnVehicle(draggedRequest, scope, vehicle, getSelectedRouteKind());
      const isExpanded = state.expandedVehicleKey === vehicleDetailsKey;

      vehicleButton.type = "button";
      vehicleButton.dataset.vehicleId = String(vehicle.id);
      vehicleButton.dataset.vehicleScope = scope;
      vehicleButton.dataset.vehicleDetailsAnchorKey = vehicleDetailsKey;
      vehicleButton.title = t("misc.vehicleButtonTitle", {
        type: mapVehicleTypeLabel(vehicle.tipo),
        occupancy: formatVehicleOccupancyLabel(vehicle, assignedCount),
      });
      vehicleButton.setAttribute("aria-label", vehicleButton.title);
      vehicleButton.classList.toggle("is-selectable", isDropTarget);
      vehicleButton.classList.toggle("is-preview-target", !!previewRequestRow);
      vehicleButton.classList.toggle("is-details-open", isExpanded);
      tileElement.classList.toggle("is-expanded", isExpanded);
      if (!isDropTarget && !previewRequestRow) {
        vehicleButton.classList.add("is-idle");
      }

      const iconImage = document.createElement("img");
      iconImage.className = "transport-vehicle-icon";
      iconImage.src = mapVehicleIconPath(vehicle.tipo);
      iconImage.alt = "";

      const plateLabel = createNode("span", "transport-vehicle-plate", vehicle.placa);
      const occupancyLabel = createNode(
        "span",
        "transport-vehicle-occupancy",
        formatVehicleOccupancyCount(vehicle, assignedCount)
      );
      const departureLabel = departureTime
        ? createNode("span", "transport-vehicle-departure", departureTime)
        : null;
      const routeLabel = scope === "extra" && vehicle.route_kind
        ? createNode("span", "transport-vehicle-route", getRouteKindLabel(vehicle.route_kind))
        : null;

      if (scope === "extra" && vehicle.route_kind) {
        vehicleButton.title = `${vehicleButton.title} | ${getRouteKindLabel(vehicle.route_kind)}`;
      }
      if (departureLabel) {
        departureLabel.setAttribute("aria-label", departureTime);
        vehicleButton.title = `${vehicleButton.title} | ${departureTime}`;
      }
      vehicleButton.appendChild(plateLabel);
      vehicleButton.appendChild(iconImage);
      vehicleButton.appendChild(occupancyLabel);
      if (departureLabel) {
        vehicleButton.appendChild(departureLabel);
      }
      if (routeLabel) {
        vehicleButton.appendChild(routeLabel);
      }
      vehicleButton.addEventListener("click", function () {
        toggleVehicleDetails(scope, vehicle.id);
      });

      function handleVehicleDragOver(event) {
        if (!canRequestBeDroppedOnVehicle(getDraggedRequest(), scope, vehicle, getSelectedRouteKind())) {
          return;
        }
        event.preventDefault();
        if (event.dataTransfer) {
          event.dataTransfer.dropEffect = "move";
        }
      }

      function handleVehicleDrop(event) {
        const droppedRequestId = Number(
          state.dragRequestId !== null
            ? state.dragRequestId
            : event.dataTransfer
              ? event.dataTransfer.getData("text/plain")
              : ""
        );
        const droppedRequest = getRequestById(droppedRequestId);
        if (!canRequestBeDroppedOnVehicle(droppedRequest, scope, vehicle, getSelectedRouteKind())) {
          state.dragRequestId = null;
          renderRequestTables();
          renderVehiclePanels();
          return;
        }

        event.preventDefault();
        state.expandedVehicleKey = vehicleDetailsKey;
        state.pendingAssignmentPreview = {
          requestId: droppedRequest.id,
          vehicleId: vehicle.id,
          scope,
          routeKind: getRouteKindForVehicle(scope, vehicle),
        };
        state.dragRequestId = null;
        renderRequestTables();
        renderVehiclePanels();
      }

      function handleVehicleDragEnter(event) {
        if (!canRequestBeDroppedOnVehicle(getDraggedRequest(), scope, vehicle, getSelectedRouteKind())) {
          return;
        }
        event.preventDefault();
      }

      tileElement.addEventListener("dragover", handleVehicleDragOver);
      tileElement.addEventListener("drop", handleVehicleDrop);
      tileElement.addEventListener("dragenter", handleVehicleDragEnter);

      tileElement.appendChild(vehicleButton);
      if (isExpanded) {
        tileElement.expandedDetailsPanel = createVehicleDetailsPanel(vehicle, assignedRows, {
          previewRequestRow,
          routeKind: pendingPreview ? pendingPreview.routeKind : getRouteKindForVehicle(scope, vehicle),
        });
        tileElement.expandedDetailsPanel.dataset.vehicleDetailsPanelKey = vehicleDetailsKey;
      }
      return tileElement;
    }

    function createVehicleManagementTable(scope, registryRows) {
      const table = createNode("table", "transport-vehicle-management-table");
      const tableBody = document.createElement("tbody");

      registryRows.forEach(function (rowData) {
        const row = createNode("tr", "transport-vehicle-management-row");
        const typeCell = createNode(
          "td",
          "transport-vehicle-management-type",
          formatVehicleTypeTableValue(rowData.tipo)
        );
        const plateCell = createNode("td", "transport-vehicle-management-plate-cell");
        const occupancyCell = createNode(
          "td",
          "transport-vehicle-management-occupancy",
          formatVehicleOccupancyCount(rowData, rowData.assigned_count)
        );
        const actionsCell = createNode("td", "transport-vehicle-management-actions");
        const vehiclePlate = createNode("strong", "transport-vehicle-management-plate", rowData.placa);
        const effectiveDepartureTime = getEffectiveWorkToHomeDepartureTime(state.dashboard, state.workToHomeTime);
        const departureTime = getVehicleDepartureTime(rowData, effectiveDepartureTime, scope);
        const deleteButton = createNode(
          "button",
          "transport-vehicle-delete-button transport-vehicle-management-delete",
          t("misc.delete")
        );

        occupancyCell.classList.toggle("is-occupied", Number(rowData.assigned_count) > 0);
        deleteButton.type = "button";
        deleteButton.disabled = rowData.schedule_id === null || rowData.schedule_id === undefined;
        deleteButton.addEventListener("click", function (event) {
          event.preventDefault();
          event.stopPropagation();
          removeVehicleFromRoute(rowData);
        });

        plateCell.appendChild(vehiclePlate);
        row.appendChild(typeCell);
        row.appendChild(plateCell);
        if (departureTime) {
          row.appendChild(createNode("td", "transport-vehicle-management-time", departureTime));
        }
        actionsCell.appendChild(deleteButton);
        row.appendChild(occupancyCell);

        if (scope === "extra") {
          row.appendChild(
            createNode("td", "transport-vehicle-management-date", rowData.service_date || "")
          );
          row.appendChild(
            createNode(
              "td",
              "transport-vehicle-management-route-value",
              rowData.route_kind ? formatRouteTableValue(rowData.route_kind) : ""
            )
          );
        }

        row.appendChild(actionsCell);
        tableBody.appendChild(row);
      });

      table.appendChild(tableBody);
      table.setAttribute("aria-label", t("misc.vehiclesAria", { scope: mapScopeTitle(scope) }));
      return table;
    }

    function renderVehiclePanels() {
      syncVehicleViewToggleState();
      clearElement(vehicleDetailsOverlayHost);
      vehicleDetailsOverlayHost.classList.remove("is-active");
      let hasExpandedDetailsPanel = false;

      VEHICLE_SCOPE_ORDER.forEach(function (scope) {
        const container = vehicleContainers[scope];
        const vehicles = getVehiclesForScope(scope);
        const registryRows = getVehicleRegistryRows(scope);
        const assignedRowsByVehicle = groupAssignedRequestsByVehicle(scope);
        clearElement(container);
        if (!container) {
          return;
        }

        setVehicleContainerViewMode(container, scope);

        if (getVehicleViewMode(scope) === "table") {
          if (!registryRows.length) {
            container.appendChild(createEmptyState(t("empty.noVehicles", { scope: mapScopeTitle(scope) })));
            return;
          }
          container.appendChild(createVehicleManagementTable(scope, registryRows));
          return;
        }

        if (!vehicles.length) {
          container.appendChild(createEmptyState(t("empty.noVehicles", { scope: mapScopeTitle(scope) })));
          return;
        }

        vehicles.forEach(function (vehicle) {
          const assignedRows = assignedRowsByVehicle[String(vehicle.id)] || [];
          const tileElement = createVehicleIconButton(scope, vehicle, assignedRows);
          container.appendChild(tileElement);
          if (tileElement.expandedDetailsPanel) {
            vehicleDetailsOverlayHost.appendChild(tileElement.expandedDetailsPanel);
            hasExpandedDetailsPanel = true;
          }
        });

        updateVehicleGridLayout(container);
      });

      vehicleDetailsOverlayHost.classList.toggle("is-active", hasExpandedDetailsPanel);

      scheduleExpandedVehicleDetailsPositionSync();
    }

    function renderDashboard() {
      ensureExpandedVehicleStillExists();
      renderProjectList();
      renderRequestTables();
      renderVehiclePanels();
      syncRequestSectionToggleState();
    }

    function clearDashboard() {
      renderProjectList();
      REQUEST_SECTION_ORDER.forEach(function (kind) {
        const container = requestContainers[kind];
        clearElement(container);
        if (container) {
          container.appendChild(createEmptyState(t("empty.noRows", { title: getRequestTitle(kind) })));
        }
      });
      VEHICLE_SCOPE_ORDER.forEach(function (scope) {
        const container = vehicleContainers[scope];
        clearElement(container);
        if (container) {
          setVehicleContainerViewMode(container, scope);
          container.appendChild(createEmptyState(t("empty.noVehicles", { scope: mapScopeTitle(scope) })));
          container.style.removeProperty("grid-template-rows");
          container.style.removeProperty("grid-auto-columns");
        }
      });
      clearElement(vehicleDetailsOverlayHost);
      vehicleDetailsOverlayHost.classList.remove("is-active");
      state.expandedVehicleKey = null;
      state.pendingAssignmentPreview = null;
      state.dragRequestId = null;
      syncVehicleViewToggleState();
      syncRequestSectionToggleState();
      syncRouteTimeControls();
    }

    function loadDashboard(selectedDate, options) {
      const loadOptions = options || {};
      const shouldAnnounce = loadOptions.announce !== false;
      if (!state.isAuthenticated) {
        state.dashboard = null;
        clearDashboard();
        setStatus(getTransportLockedMessage(), "warning");
        return Promise.resolve(null);
      }

      state.pendingAssignmentPreview = null;
      state.dragRequestId = null;
      state.isLoading = true;
      syncRouteTimeControls();
      const serviceDate = formatIsoDate(selectedDate);
      const routeKind = getSelectedRouteKind();
      if (shouldAnnounce) {
        setStatus(t("status.loadingDashboard"), "info");
      }
      return requestJson(
        `${TRANSPORT_API_PREFIX}/dashboard?service_date=${encodeURIComponent(serviceDate)}&route_kind=${encodeURIComponent(routeKind)}`
      )
        .then(function (dashboard) {
          state.dashboard = dashboard || null;
          reconcileProjectVisibility();
          state.selectedRouteKind = (dashboard && dashboard.selected_route) || routeKind;
          syncRouteInputs();
          syncRouteTimeControls();
          if (shouldAnnounce) {
            setStatus(t("status.dashboardUpdated"), "info");
          }
          renderDashboard();
        })
        .catch(function (error) {
          state.dashboard = null;
          clearDashboard();
          if (error && Number(error.status) === 401) {
            clearTransportSession(getTransportSessionExpiredMessage());
            return;
          }
          setStatus(localizeTransportApiMessage(error && error.message) || t("status.couldNotLoadDashboard"), "error");
        })
        .finally(function () {
          state.isLoading = false;
          syncRouteTimeControls();
        });
    }

    return {
      bootstrapTransportSession,
      closeRouteTimePopover,
      loadDashboard,
      refreshVehicleGridLayouts: function () {
        updateVehicleGridLayouts(document);
        scheduleExpandedVehicleDetailsPositionSync();
      },
    };
  }
```
