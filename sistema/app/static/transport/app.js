(function (globalScope) {
  const RESIZE_DEFAULT_MIN_SIZE = 96;
  const REQUEST_SECTION_ORDER = ["extra", "weekend", "regular"];
  const VEHICLE_SCOPE_ORDER = ["extra", "weekend", "regular"];
  const REQUEST_TITLES = {
    regular: "Regular Car Requests",
    weekend: "Weekend Car Requests",
    extra: "Extra Car Requests",
  };
  const REQUEST_LABELS = {
    regular: "REGULAR",
    weekend: "WEEKEND",
    extra: "EXTRA",
  };
  const VEHICLE_ICON_PATHS = {
    carro: "icons/car.svg",
    minivan: "icons/minivan.svg",
    van: "icons/van.svg",
    onibus: "icons/bus.svg",
  };
  const ROUTE_KIND_LABELS = {
    home_to_work: "Home to Work",
    work_to_home: "Work to Home",
  };
  const MODAL_SCOPE_NOTES = {
    extra: "Extra vehicles are created only for the selected route and selected date.",
    weekend:
      "Weekend vehicles must be persistent. Select Every Saturday, Every Sunday, or both. If you need a one-date weekend vehicle, create it in Extra Transport List.",
    regular: "Regular vehicles are created for both routes and remain active from Monday to Friday.",
  };
  const DEFAULT_STATUS_MESSAGE = "Transport dashboard ready.";
  const TRANSPORT_LOCKED_MESSAGE = "Enter key and password to unlock the transport dashboard.";
  const TRANSPORT_SESSION_EXPIRED_MESSAGE = "Transport session expired. Enter key and password again.";
  const TRANSPORT_AUTH_VERIFY_DELAY_MS = 140;
  const TRANSPORT_REALTIME_DEBOUNCE_MS = 180;
  const VEHICLE_DETAILS_MAX_ROWS = 5;
  const VEHICLE_GRID_FALLBACK_ITEM_WIDTH = 104;
  const VEHICLE_GRID_FALLBACK_ITEM_HEIGHT = 96;
  const weekdayFormatter = new Intl.DateTimeFormat("en-US", { weekday: "long" });
  const monthFormatter = new Intl.DateTimeFormat("en-US", { month: "long" });

  function startOfLocalDay(value) {
    const date = value instanceof Date ? new Date(value) : new Date(value);
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  function getOrdinalSuffix(day) {
    const normalizedDay = Math.abs(Number(day));
    const remainder = normalizedDay % 100;
    if (remainder >= 11 && remainder <= 13) {
      return "th";
    }

    switch (normalizedDay % 10) {
      case 1:
        return "st";
      case 2:
        return "nd";
      case 3:
        return "rd";
      default:
        return "th";
    }
  }

  function formatTransportDate(value) {
    const date = startOfLocalDay(value);
    return `${weekdayFormatter.format(date)}, ${monthFormatter.format(date)} ${date.getDate()}${getOrdinalSuffix(date.getDate())}, ${date.getFullYear()}`;
  }

  function shiftLocalDay(value, amount) {
    const nextDate = startOfLocalDay(value);
    nextDate.setDate(nextDate.getDate() + amount);
    return nextDate;
  }

  function formatIsoDate(value) {
    const date = startOfLocalDay(value);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  }

  function getTransportDateState(value, referenceValue) {
    const selectedDate = startOfLocalDay(value);
    const referenceDate = startOfLocalDay(referenceValue || new Date());

    if (selectedDate.getTime() === referenceDate.getTime()) {
      return "today";
    }

    return selectedDate.getTime() > referenceDate.getTime() ? "future" : "past";
  }

  function isWeekendDate(value) {
    const date = startOfLocalDay(value);
    return date.getDay() === 0 || date.getDay() === 6;
  }

  function createTransportDateStore(initialValue) {
    const subscribers = new Set();
    let selectedDate = startOfLocalDay(initialValue || new Date());

    function getValue() {
      return new Date(selectedDate);
    }

    function notify() {
      const nextValue = getValue();
      subscribers.forEach(function (subscriber) {
        subscriber(nextValue);
      });
    }

    function setValue(value) {
      selectedDate = startOfLocalDay(value);
      notify();
      return getValue();
    }

    function shiftValue(amount) {
      return setValue(shiftLocalDay(selectedDate, amount));
    }

    function subscribe(subscriber) {
      if (typeof subscriber !== "function") {
        return function () {};
      }

      subscribers.add(subscriber);
      subscriber(getValue());

      return function unsubscribe() {
        subscribers.delete(subscriber);
      };
    }

    return {
      getValue,
      setValue,
      shiftValue,
      subscribe,
    };
  }

  function clampValue(value, minValue, maxValue) {
    return Math.min(Math.max(value, minValue), maxValue);
  }

  function parsePositiveNumber(value, fallbackValue) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed < 0) {
      return fallbackValue;
    }
    return parsed;
  }

  function parsePixelValue(value, fallbackValue) {
    const parsed = parseFloat(value);
    if (!Number.isFinite(parsed) || parsed < 0) {
      return fallbackValue;
    }
    return parsed;
  }

  function resolvePanelSizes(options) {
    const containerSize = Math.max(0, Number(options.containerSize) || 0);
    const dividerSize = Math.max(0, Number(options.dividerSize) || 0);
    const availableSize = Math.max(0, containerSize - dividerSize);
    const minFirstSize = Math.min(
      parsePositiveNumber(options.minFirstSize, RESIZE_DEFAULT_MIN_SIZE),
      availableSize
    );
    const minSecondSize = Math.min(
      parsePositiveNumber(options.minSecondSize, RESIZE_DEFAULT_MIN_SIZE),
      availableSize
    );
    const maxFirstSize = Math.max(minFirstSize, availableSize - minSecondSize);
    const firstSize = clampValue(Number(options.pointerOffset) || 0, minFirstSize, maxFirstSize);
    return {
      firstSize: Math.round(firstSize),
      secondSize: Math.round(Math.max(0, availableSize - firstSize)),
    };
  }

  function resolveResizeConfig(orientation) {
    return orientation === "vertical"
      ? {
          gridProperty: "gridTemplateColumns",
          sizeProperty: "width",
          startProperty: "left",
        }
      : {
          gridProperty: "gridTemplateRows",
          sizeProperty: "height",
          startProperty: "top",
        };
  }

  function getVehicleGridItemMetrics(gridElement) {
    const sampleButton = gridElement && gridElement.querySelector(".transport-vehicle-button");
    if (!sampleButton) {
      return {
        width: VEHICLE_GRID_FALLBACK_ITEM_WIDTH,
        height: VEHICLE_GRID_FALLBACK_ITEM_HEIGHT,
      };
    }

    const buttonRect = sampleButton.getBoundingClientRect();
    return {
      width: Math.max(1, Math.round(buttonRect.width)),
      height: Math.max(1, Math.round(buttonRect.height)),
    };
  }

  function updateVehicleGridLayout(gridElement) {
    if (!gridElement) {
      return;
    }

    if (gridElement.dataset.vehicleView === "table" || gridElement.classList.contains("is-management-table")) {
      gridElement.style.removeProperty("grid-template-rows");
      gridElement.style.removeProperty("grid-auto-columns");
      return;
    }

    const itemElements = gridElement.querySelectorAll(".transport-vehicle-button");
    if (!itemElements.length) {
      gridElement.style.removeProperty("grid-template-rows");
      gridElement.style.removeProperty("grid-auto-columns");
      return;
    }

    const gridStyle = globalScope.getComputedStyle(gridElement);
    const rowGap = parsePixelValue(gridStyle.rowGap || gridStyle.gap, 0);
    const metrics = getVehicleGridItemMetrics(gridElement);
    const availableHeight = Math.max(metrics.height, Math.floor(gridElement.clientHeight));
    const computedRowCount = Math.floor((availableHeight + rowGap) / (metrics.height + rowGap));
    const rowCount = Math.max(1, Math.min(itemElements.length, computedRowCount));

    gridElement.style.gridAutoColumns = `${metrics.width}px`;
    gridElement.style.gridTemplateRows = `repeat(${rowCount}, ${metrics.height}px)`;
  }

  function updateVehicleGridLayouts(rootElement) {
    const scopeRoot = rootElement || document;
    scopeRoot.querySelectorAll("[data-vehicle-scope]").forEach(function (gridElement) {
      updateVehicleGridLayout(gridElement);
    });
  }

  function resolvePanelMinimumSize(panelElement, fallbackValue) {
    if (!panelElement) {
      return fallbackValue;
    }

    const vehicleGrid = panelElement.querySelector(".transport-vehicle-grid");
    if (!vehicleGrid) {
      return fallbackValue;
    }

    const panelStyle = globalScope.getComputedStyle(panelElement);
    const panelGap = parsePixelValue(panelStyle.rowGap || panelStyle.gap, 0);
    const paddingTop = parsePixelValue(panelStyle.paddingTop, 0);
    const paddingBottom = parsePixelValue(panelStyle.paddingBottom, 0);
    const headElement = panelElement.querySelector(".transport-pane-head");
    const headHeight = headElement ? Math.ceil(headElement.getBoundingClientRect().height) : 0;
    const gridItemHeight = getVehicleGridItemMetrics(vehicleGrid).height;

    return Math.max(
      fallbackValue,
      Math.ceil(paddingTop + headHeight + panelGap + gridItemHeight + paddingBottom)
    );
  }

  function enableResizableDivider(dividerElement) {
    const orientation = dividerElement.dataset.resize;
    if (!orientation) {
      return;
    }

    const containerElement = dividerElement.parentElement;
    const firstPanelElement = dividerElement.previousElementSibling;
    const secondPanelElement = dividerElement.nextElementSibling;
    if (!containerElement || !firstPanelElement || !secondPanelElement) {
      return;
    }

    const resizeConfig = resolveResizeConfig(orientation);

    dividerElement.addEventListener("pointerdown", function (event) {
      if (event.pointerType !== "touch" && event.button !== 0) {
        return;
      }

      const childElements = Array.from(containerElement.children);
      const dividerIndex = childElements.indexOf(dividerElement);
      const firstPanelIndex = dividerIndex - 1;
      const secondPanelIndex = dividerIndex + 1;
      if (dividerIndex < 0 || firstPanelIndex < 0 || secondPanelIndex >= childElements.length) {
        return;
      }

      const containerRect = containerElement.getBoundingClientRect();
      const trackSizes = childElements.map(function (element) {
        return Math.round(element.getBoundingClientRect()[resizeConfig.sizeProperty]);
      });
      const dividerSize = trackSizes[dividerIndex];
      const resizeGroupSize =
        trackSizes[firstPanelIndex] + dividerSize + trackSizes[secondPanelIndex];
      const groupOffset = trackSizes.slice(0, firstPanelIndex).reduce(function (sum, size) {
        return sum + size;
      }, 0);
      const minFirstSize = resolvePanelMinimumSize(
        firstPanelElement,
        parsePositiveNumber(dividerElement.dataset.minFirst, RESIZE_DEFAULT_MIN_SIZE)
      );
      const minSecondSize = resolvePanelMinimumSize(
        secondPanelElement,
        parsePositiveNumber(dividerElement.dataset.minSecond, RESIZE_DEFAULT_MIN_SIZE)
      );

      function applyResize(moveEvent) {
        const pointerOffset = moveEvent[
          orientation === "vertical" ? "clientX" : "clientY"
        ] - containerRect[resizeConfig.startProperty] - groupOffset;
        const nextSizes = resolvePanelSizes({
          containerSize: resizeGroupSize,
          dividerSize,
          pointerOffset,
          minFirstSize,
          minSecondSize,
        });
        const nextTrackSizes = trackSizes.slice();
        nextTrackSizes[firstPanelIndex] = nextSizes.firstSize;
        nextTrackSizes[dividerIndex] = Math.round(dividerSize);
        nextTrackSizes[secondPanelIndex] = nextSizes.secondSize;
        containerElement.style[resizeConfig.gridProperty] = nextTrackSizes
          .map(function (size) {
            return `${Math.round(size)}px`;
          })
          .join(" ");
        updateVehicleGridLayouts(containerElement);
      }

      function stopResize() {
        globalScope.removeEventListener("pointermove", applyResize);
        globalScope.removeEventListener("pointerup", stopResize);
        globalScope.removeEventListener("pointercancel", stopResize);
        document.body.classList.remove("transport-is-resizing");
      }

      document.body.classList.add("transport-is-resizing");
      globalScope.addEventListener("pointermove", applyResize);
      globalScope.addEventListener("pointerup", stopResize, { once: true });
      globalScope.addEventListener("pointercancel", stopResize, { once: true });
      applyResize(event);
      event.preventDefault();
    });
  }

  function createDatePanelController(rootElement, dateStore) {
    const labelElement = rootElement.querySelector("[data-date-label]");
    const dateLink = rootElement.querySelector("[data-date-link]");
    const previousButton = rootElement.querySelector('[data-date-shift="-1"]');
    const nextButton = rootElement.querySelector('[data-date-shift="1"]');

    function render(selectedDate) {
      if (labelElement) {
        labelElement.textContent = formatTransportDate(selectedDate);
        labelElement.dataset.dateState = getTransportDateState(selectedDate);
      }
    }

    if (previousButton) {
      previousButton.addEventListener("click", function () {
        dateStore.shiftValue(-1);
      });
    }

    if (nextButton) {
      nextButton.addEventListener("click", function () {
        dateStore.shiftValue(1);
      });
    }

    if (dateLink) {
      dateLink.addEventListener("click", function (event) {
        event.preventDefault();
        dateStore.setValue(new Date());
      });
    }

    dateStore.subscribe(render);
  }

  function clearElement(element) {
    if (!element) {
      return;
    }
    while (element.firstChild) {
      element.removeChild(element.firstChild);
    }
  }

  function createNode(tagName, className, textContent) {
    const element = document.createElement(tagName);
    if (className) {
      element.className = className;
    }
    if (textContent !== undefined && textContent !== null) {
      element.textContent = textContent;
    }
    return element;
  }

  function requestJson(url, options) {
    const requestOptions = Object.assign(
      {
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
        },
      },
      options || {}
    );

    if (requestOptions.body && !requestOptions.headers["Content-Type"]) {
      requestOptions.headers["Content-Type"] = "application/json";
    }

    return fetch(url, requestOptions).then(function (response) {
      return response.text().then(function (text) {
        let payload = null;
        if (text) {
          try {
            payload = JSON.parse(text);
          } catch (error) {
            payload = null;
          }
        }

        if (!response.ok) {
          const error = new Error(formatApiErrorMessage(payload, response.status));
          error.status = response.status;
          error.payload = payload;
          throw error;
        }

        return payload;
      });
    });
  }

  function extractApiMessage(value) {
    if (typeof value === "string") {
      return value.trim();
    }

    if (Array.isArray(value)) {
      return value
        .map(function (item) {
          return extractApiMessage(item);
        })
        .filter(Boolean)
        .join(" ");
    }

    if (value && typeof value === "object") {
      if (typeof value.msg === "string" && value.msg.trim()) {
        return value.msg.trim();
      }
      if (typeof value.message === "string" && value.message.trim()) {
        return value.message.trim();
      }
      if (typeof value.detail === "string" && value.detail.trim()) {
        return value.detail.trim();
      }
    }

    return "";
  }

  function formatApiErrorMessage(payload, statusCode) {
    const message = extractApiMessage(payload && (payload.detail !== undefined ? payload.detail : payload && payload.message));
    return message || `HTTP ${statusCode}`;
  }

  function buildVehicleCreatePayload(formData, serviceDate, selectedRouteKind) {
    const serviceScope = String(formData.get("service_scope") || "regular");
    const payload = {
      service_scope: serviceScope,
      service_date: String(serviceDate || ""),
      tipo: String(formData.get("tipo") || "carro"),
      placa: String(formData.get("placa") || ""),
      color: String(formData.get("color") || ""),
      lugares: Number(formData.get("lugares") || 0),
      tolerance: Number(formData.get("tolerance") || 0),
    };

    if (serviceScope === "extra") {
      payload.route_kind = String(formData.get("route_kind") || selectedRouteKind || "home_to_work");
      return payload;
    }

    if (serviceScope === "weekend") {
      payload.every_saturday = Boolean(formData.get("every_saturday"));
      payload.every_sunday = Boolean(formData.get("every_sunday"));
    }

    return payload;
  }

  function mapVehicleTypeLabel(value) {
    switch (value) {
      case "carro":
        return "Car";
      case "minivan":
        return "Mini-Van";
      case "van":
        return "Van";
      case "onibus":
        return "Bus";
      default:
        return value;
    }
  }

  function formatVehicleTypeTableValue(value) {
    switch (value) {
      case "carro":
        return "car";
      case "minivan":
        return "minivan";
      case "van":
        return "van";
      case "onibus":
        return "bus";
      default:
        return String(value || "").toLowerCase();
    }
  }

  function formatRouteTableValue(routeKind) {
    return getRouteKindLabel(routeKind).toLowerCase();
  }

  function mapVehicleIconPath(value) {
    return VEHICLE_ICON_PATHS[value] || VEHICLE_ICON_PATHS.carro;
  }

  function formatVehicleOccupancyLabel(vehicle, assignedCount) {
    const occupiedSeats = Math.max(0, Number(assignedCount) || 0);
    const totalSeats = Math.max(0, Number(vehicle && vehicle.lugares) || 0);
    return `${vehicle.placa} (${occupiedSeats}/${totalSeats})`;
  }

  function formatVehicleOccupancyCount(vehicle, assignedCount) {
    const occupiedSeats = Math.max(0, Number(assignedCount) || 0);
    const totalSeats = Math.max(0, Number(vehicle && vehicle.lugares) || 0);
    return `${occupiedSeats}/${totalSeats}`;
  }

  function shouldHighlightRequestName(assignmentStatus) {
    return assignmentStatus === "pending" || assignmentStatus === "rejected" || assignmentStatus === "cancelled";
  }

  function getPassengerAwarenessState(requestRow) {
    return requestRow && requestRow.awareness_status === "aware" ? "aware" : "pending";
  }

  function buildVehiclePassengerAwarenessRows(assignedRows, maxRows) {
    const normalizedMaxRows = Math.max(1, Number(maxRows) || VEHICLE_DETAILS_MAX_ROWS);
    const rows = Array.isArray(assignedRows)
      ? assignedRows.slice(0, normalizedMaxRows).map(function (requestRow) {
          return {
            name: String((requestRow && requestRow.nome) || ""),
            awarenessState: getPassengerAwarenessState(requestRow),
          };
        })
      : [];

    while (rows.length < normalizedMaxRows) {
      rows.push({
        name: "",
        awarenessState: null,
      });
    }

    return rows;
  }

  function mapScopeTitle(scope) {
    if (scope === "regular") {
      return "Regular";
    }
    if (scope === "weekend") {
      return "Weekend";
    }
    return "Extra";
  }

  function getRouteKindLabel(routeKind) {
    return ROUTE_KIND_LABELS[routeKind] || routeKind;
  }

  function getModalScopeNote(scope) {
    return MODAL_SCOPE_NOTES[scope] || MODAL_SCOPE_NOTES.regular;
  }

  function createEmptyState(message) {
    const wrapper = createNode("div", "transport-empty-state");
    wrapper.appendChild(createNode("strong", "transport-empty-title", message));
    return wrapper;
  }

  function createTransportPageController(dateStore) {
    const requestContainers = {};
    const vehicleContainers = {};
    const state = {
      dashboard: null,
      selectedRequestId: null,
      isLoading: false,
      selectedRouteKind: "home_to_work",
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
    };
    const statusMessage = document.querySelector("[data-status-message]");
    const selectionBanner = document.querySelector("[data-selection-banner]");
    const selectionText = document.querySelector("[data-selection-text]");
    const clearSelectionButton = document.querySelector("[data-clear-selection]");
    const rejectSelectionButton = document.querySelector("[data-reject-selection]");
    const vehicleModal = document.querySelector("[data-vehicle-modal]");
    const vehicleForm = document.querySelector("[data-vehicle-form]");
    const modalScopeLabel = document.querySelector("[data-modal-scope-label]");
    const modalScopeNote = document.querySelector("[data-modal-scope-note]");
    const vehicleModalFeedback = document.querySelector("[data-vehicle-modal-feedback]");
    const extraRouteField = document.querySelector("[data-extra-route-field]");
    const weekendPersistenceFields = Array.from(document.querySelectorAll("[data-weekend-persistence-field]"));
    const routeInputs = Array.from(document.querySelectorAll("[data-route-kind]"));
    const authKeyInput = document.querySelector("[data-transport-auth-key]");
    const authPasswordInput = document.querySelector("[data-transport-auth-password]");
    const authKeyShell = document.querySelector('[data-transport-auth-shell="key"]');
    const authPasswordShell = document.querySelector('[data-transport-auth-shell="password"]');
    const requestUserButton = document.querySelector("[data-request-user-link]");
    const vehicleViewToggleLinks = {};

    document.querySelectorAll("[data-request-kind]").forEach(function (element) {
      requestContainers[element.dataset.requestKind] = element;
    });
    document.querySelectorAll("[data-vehicle-scope]").forEach(function (element) {
      vehicleContainers[element.dataset.vehicleScope] = element;
    });
    document.querySelectorAll("[data-toggle-vehicle-view]").forEach(function (element) {
      vehicleViewToggleLinks[element.dataset.toggleVehicleView] = element;
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

      state.realtimeEventStream = new globalScope.EventSource("/api/transport/stream");
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
        state.selectedRequestId = null;
        state.expandedVehicleKey = null;
        clearDashboard();
      }
    }

    function clearTransportSession(message) {
      state.authVerifyToken += 1;
      clearPendingAuthVerification();
      setAuthenticationState(false, null, { resetInputs: true, clearDashboard: true });
      requestJson("/api/transport/auth/logout", { method: "POST" }).catch(function () {});
      setStatus(message || TRANSPORT_LOCKED_MESSAGE, "warning");
    }

    function handleProtectedRequestError(error, fallbackMessage) {
      if (error && Number(error.status) === 401) {
        clearTransportSession(TRANSPORT_SESSION_EXPIRED_MESSAGE);
        return true;
      }
      setStatus((error && error.message) || fallbackMessage, "error");
      if (error && (Number(error.status) === 404 || Number(error.status) === 409)) {
        requestDashboardRefresh({ announce: false });
      }
      return false;
    }

    function openUserCreationRequest() {
      if (typeof globalScope.open === "function") {
        globalScope.open("../admin", "_blank", "noopener");
      }
      setStatus("Open the admin page to request a user creation.", "info");
    }

    function verifyTransportCredentials(requestToken) {
      const chave = normalizeAuthKeyValue();
      const senha = authPasswordInput ? String(authPasswordInput.value || "") : "";
      if (chave.length !== 4 || !senha) {
        return Promise.resolve(null);
      }

      return requestJson("/api/transport/auth/verify", {
        method: "POST",
        body: JSON.stringify({ chave: chave, senha: senha }),
      })
        .then(function (response) {
          if (requestToken !== state.authVerifyToken) {
            return null;
          }

          if (response && response.authenticated && response.user) {
            setAuthenticationState(true, response.user, {});
            setStatus(response.message || "Transport access granted.", "success");
            return loadDashboard(dateStore.getValue(), { announce: false });
          }

          setAuthenticationState(false, null, {});
          setStatus((response && response.message) || TRANSPORT_LOCKED_MESSAGE, "warning");
          return null;
        })
        .catch(function (error) {
          if (requestToken !== state.authVerifyToken) {
            return null;
          }
          setStatus((error && error.message) || "Could not verify transport access.", "error");
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
        setStatus(TRANSPORT_LOCKED_MESSAGE, "warning");
        return;
      }

      state.authVerifyToken += 1;
      const requestToken = state.authVerifyToken;
      state.authVerifyTimer = globalScope.setTimeout(function () {
        state.authVerifyTimer = null;
        verifyTransportCredentials(requestToken);
      }, TRANSPORT_AUTH_VERIFY_DELAY_MS);
    }

    function resetAuthenticatedTransportField(event) {
      if (!state.isAuthenticated) {
        return;
      }
      event.preventDefault();
      clearTransportSession("Transport access reset.");
      const fieldElement = event.currentTarget;
      globalScope.setTimeout(function () {
        if (fieldElement && typeof fieldElement.focus === "function") {
          fieldElement.focus();
        }
      }, 0);
    }

    function bootstrapTransportSession() {
      return requestJson("/api/transport/auth/session")
        .then(function (response) {
          if (response && response.authenticated && response.user) {
            setAuthenticationState(true, response.user, { fillKey: true });
            setStatus(DEFAULT_STATUS_MESSAGE, "info");
            return loadDashboard(dateStore.getValue(), { announce: false });
          }

          setAuthenticationState(false, null, { resetInputs: true, clearDashboard: true });
          setStatus(TRANSPORT_LOCKED_MESSAGE, "warning");
          return null;
        })
        .catch(function () {
          setAuthenticationState(false, null, { resetInputs: true, clearDashboard: true });
          setStatus(TRANSPORT_LOCKED_MESSAGE, "warning");
          return null;
        });
    }

    if (authKeyInput) {
      authKeyInput.addEventListener("input", scheduleTransportVerification);
      authKeyInput.addEventListener("pointerdown", resetAuthenticatedTransportField);
    }

    if (authPasswordInput) {
      authPasswordInput.addEventListener("input", scheduleTransportVerification);
      authPasswordInput.addEventListener("pointerdown", resetAuthenticatedTransportField);
    }

    if (requestUserButton) {
      requestUserButton.addEventListener("click", openUserCreationRequest);
    }

    routeInputs.forEach(function (inputElement) {
      if (inputElement.checked) {
        state.selectedRouteKind = inputElement.value || state.selectedRouteKind;
      }
      inputElement.addEventListener("change", function () {
        if (!inputElement.checked) {
          return;
        }
        state.selectedRouteKind = inputElement.value || "home_to_work";
        loadDashboard(dateStore.getValue());
      });
    });

    if (clearSelectionButton) {
      clearSelectionButton.addEventListener("click", function () {
        state.selectedRequestId = null;
        renderSelectionBanner();
        renderVehiclePanels();
        renderRequestTables();
      });
    }

    if (rejectSelectionButton) {
      rejectSelectionButton.addEventListener("click", function () {
        const selectedRequest = getSelectedRequest();
        if (!selectedRequest || !state.dashboard) {
          return;
        }

        submitAssignment({
          request_id: selectedRequest.id,
          service_date: state.dashboard.selected_date,
          route_kind: getSelectedRouteKind(),
          status: "rejected",
        }).catch(function (error) {
          handleProtectedRequestError(error, "Could not reject the selected request.");
        });
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
      vehicleForm.addEventListener("submit", function (event) {
        event.preventDefault();
        const formData = new FormData(vehicleForm);
        const payload = buildVehicleCreatePayload(formData, getCurrentServiceDateIso(), getSelectedRouteKind());
        const submitButton = vehicleForm.querySelector('button[type="submit"]');

        clearVehicleModalFeedback();
        if (payload.service_scope === "weekend" && !payload.every_saturday && !payload.every_sunday) {
          setVehicleModalFeedback(
            "Weekend vehicles must be persistent. Select Every Saturday and/or Every Sunday, or create the vehicle in Extra Transport List.",
            "error"
          );
          return;
        }
        if (submitButton) {
          submitButton.disabled = true;
        }

        requestJson("/api/transport/vehicles", {
          method: "POST",
          body: JSON.stringify(payload),
        })
          .then(function () {
            closeVehicleModal();
            setStatus("Vehicle saved successfully.", "success");
            return loadDashboard(dateStore.getValue(), { announce: false });
          })
          .catch(function (error) {
            setVehicleModalFeedback((error && error.message) || "Could not save vehicle.", "error");
            handleProtectedRequestError(error, "Could not save vehicle.");
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

      statusMessage.textContent = message || DEFAULT_STATUS_MESSAGE;
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

    function syncRouteInputs() {
      routeInputs.forEach(function (inputElement) {
        inputElement.checked = inputElement.value === state.selectedRouteKind;
      });
    }

    function getSelectedRouteKind() {
      return state.selectedRouteKind || "home_to_work";
    }

    function getCurrentServiceDateIso() {
      return formatIsoDate(dateStore.getValue());
    }

    function canOpenVehicleModal(scope) {
      if (!state.isAuthenticated) {
        setStatus(TRANSPORT_LOCKED_MESSAGE, "warning");
        return false;
      }
      const selectedDate = dateStore.getValue();
      if (scope === "regular" && isWeekendDate(selectedDate)) {
        setStatus("Regular vehicles can only be created from Monday to Friday.", "warning");
        return false;
      }
      if (scope === "weekend" && !isWeekendDate(selectedDate)) {
        setStatus("Weekend vehicles can only be created on Saturdays or Sundays.", "warning");
        return false;
      }
      return true;
    }

    function syncVehicleModalFields(scope) {
      if (!vehicleForm) {
        return;
      }

      if (modalScopeLabel) {
        modalScopeLabel.textContent = mapScopeTitle(scope);
      }
      if (modalScopeNote) {
        modalScopeNote.textContent = getModalScopeNote(scope);
      }
      if (extraRouteField) {
        extraRouteField.hidden = scope !== "extra";
      }
      weekendPersistenceFields.forEach(function (fieldElement) {
        fieldElement.hidden = scope !== "weekend";
      });
      if (vehicleForm.elements.route_kind) {
        vehicleForm.elements.route_kind.value = getSelectedRouteKind();
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
      if (!canOpenVehicleModal(scope)) {
        return;
      }
      vehicleModal.hidden = false;
      vehicleModal.dataset.scope = scope;
      vehicleForm.reset();
      clearVehicleModalFeedback();
      vehicleForm.elements.service_scope.value = scope;
      vehicleForm.elements.lugares.value = "4";
      vehicleForm.elements.tolerance.value = "10";
      syncVehicleModalFields(scope);
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

    function getSelectedRequest() {
      if (state.selectedRequestId === null) {
        return null;
      }
      return (
        getAllRequests().find(function (row) {
          return Number(row.id) === Number(state.selectedRequestId);
        }) || null
      );
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
      state.expandedVehicleKey = state.expandedVehicleKey === vehicleKey ? null : vehicleKey;
      renderVehiclePanels();
    }

    function ensureSelectedRequestStillExists() {
      const selectedRequest = getSelectedRequest();
      if (!selectedRequest) {
        state.selectedRequestId = null;
      }
    }

    function createAwarenessIndicator(awarenessState) {
      const indicator = createNode("span", "transport-awareness-indicator");
      if (!awarenessState) {
        indicator.classList.add("is-empty");
        indicator.setAttribute("aria-hidden", "true");
        return indicator;
      }

      indicator.classList.add(`is-${awarenessState}`);
      if (awarenessState === "aware") {
        indicator.textContent = "✓";
        indicator.setAttribute("aria-label", "Passenger acknowledged transport confirmation");
        return indicator;
      }

      indicator.textContent = "◷";
      indicator.setAttribute("aria-label", "Awaiting passenger acknowledgement");
      return indicator;
    }

    function createVehicleDetailsPanel(vehicle, assignedRows) {
      const detailsPanel = createNode("div", "transport-vehicle-details");
      const deleteButton = createNode("button", "transport-vehicle-delete-button", "Delete");
      const passengerTable = createNode("table", "transport-vehicle-passenger-table");
      const tableBody = createNode("tbody");

      deleteButton.type = "button";
      deleteButton.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        removeVehicleFromRoute(vehicle);
      });

      buildVehiclePassengerAwarenessRows(assignedRows, VEHICLE_DETAILS_MAX_ROWS).forEach(function (row) {
        const tableRow = createNode("tr", "transport-vehicle-passenger-row");
        const nameCell = createNode("td", "transport-vehicle-passenger-name", row.name);
        const statusCell = createNode("td", "transport-vehicle-passenger-status");

        if (!row.name) {
          nameCell.innerHTML = "&nbsp;";
        }

        statusCell.appendChild(createAwarenessIndicator(row.awarenessState));
        tableRow.appendChild(nameCell);
        tableRow.appendChild(statusCell);
        tableBody.appendChild(tableRow);
      });

      passengerTable.appendChild(tableBody);
      detailsPanel.appendChild(deleteButton);
      detailsPanel.appendChild(passengerTable);
      return detailsPanel;
    }

    function renderSelectionBanner() {
      const selectedRequest = getSelectedRequest();
      if (!selectionBanner || !selectionText) {
        return;
      }

      if (!selectedRequest) {
        selectionBanner.hidden = true;
        selectionText.textContent = "--";
        if (rejectSelectionButton) {
          rejectSelectionButton.disabled = true;
        }
        return;
      }

      selectionBanner.hidden = false;
      selectionText.textContent = `${REQUEST_LABELS[selectedRequest.request_kind]} ${selectedRequest.requested_time} - ${selectedRequest.nome}`;
      if (rejectSelectionButton) {
        rejectSelectionButton.disabled = selectedRequest.assignment_status === "rejected";
      }
    }

    function createRequestMetaLine(requestRow) {
      const metaParts = [];
      if (requestRow.assigned_vehicle) {
        metaParts.push(`Assigned to ${requestRow.assigned_vehicle.placa}`);
      }
      if (requestRow.response_message) {
        metaParts.push(requestRow.response_message);
      }
      return metaParts.join(" | ");
    }

    function renderRequestTables() {
      REQUEST_SECTION_ORDER.forEach(function (kind) {
        const container = requestContainers[kind];
        const requestRows = getRequestsForKind(kind);
        clearElement(container);
        if (!container) {
          return;
        }

        if (!requestRows.length) {
          container.appendChild(createEmptyState(`No rows in ${REQUEST_TITLES[kind]}.`));
          return;
        }

        requestRows.forEach(function (requestRow) {
          const rowButton = createNode("button", `transport-request-row is-${requestRow.assignment_status}`);
          rowButton.type = "button";
          rowButton.dataset.requestId = String(requestRow.id);
          if (Number(state.selectedRequestId) === Number(requestRow.id)) {
            rowButton.classList.add("is-selected");
          }

          const timeCell = createNode("span", "transport-request-time", requestRow.requested_time);
          const nameCell = createNode("span", "transport-request-primary", requestRow.nome);
          const addressCell = createNode("span", "transport-request-secondary", requestRow.end_rua || "Address pending");
          const zipCell = createNode("span", "transport-request-secondary", requestRow.zip || "ZIP pending");
          const metaText = createRequestMetaLine(requestRow);

          if (shouldHighlightRequestName(requestRow.assignment_status)) {
            nameCell.classList.add("is-attention");
          }

          if (metaText) {
            const metaLine = createNode("small", "transport-request-meta", metaText);
            nameCell.appendChild(document.createElement("br"));
            nameCell.appendChild(metaLine);
          }

          rowButton.appendChild(timeCell);
          rowButton.appendChild(nameCell);
          rowButton.appendChild(addressCell);
          rowButton.appendChild(zipCell);
          rowButton.addEventListener("click", function () {
            state.selectedRequestId = requestRow.id;
            renderSelectionBanner();
            renderRequestTables();
            renderVehiclePanels();
          });

          container.appendChild(rowButton);
        });
      });
    }

    function groupAssignedRequestsByVehicle(scope) {
      return getRequestsForKind(scope).reduce(function (grouped, requestRow) {
        if (
          requestRow.assignment_status === "confirmed" &&
          requestRow.assigned_vehicle &&
          requestRow.assigned_vehicle.id !== undefined
        ) {
          const vehicleId = String(requestRow.assigned_vehicle.id);
          if (!grouped[vehicleId]) {
            grouped[vehicleId] = [];
          }
          grouped[vehicleId].push(requestRow);
        }
        return grouped;
      }, {});
    }

    function submitAssignment(payload) {
      return requestJson("/api/transport/assignments", {
        method: "POST",
        body: JSON.stringify(payload),
      }).then(function () {
        setStatus("Transport allocation updated.", "success");
        return loadDashboard(dateStore.getValue(), { announce: false });
      }).catch(function (error) {
        if (handleProtectedRequestError(error, "Could not update the transport allocation.")) {
          return null;
        }
        throw error;
      });
    }

    function removeVehicleFromRoute(vehicle) {
      if (!vehicle || vehicle.schedule_id === null || vehicle.schedule_id === undefined) {
        setStatus("This vehicle cannot be removed from the selected route.", "error");
        return Promise.resolve();
      }

      const deleteServiceDate = vehicle.service_date || getCurrentServiceDateIso();

      return requestJson(
        `/api/transport/vehicles/${encodeURIComponent(String(vehicle.schedule_id))}?service_date=${encodeURIComponent(deleteServiceDate)}`,
        {
          method: "DELETE",
        }
      )
        .then(function () {
          setStatus("Vehicle deleted from the database.", "success");
          return loadDashboard(dateStore.getValue(), { announce: false });
        })
        .catch(function (error) {
          handleProtectedRequestError(error, "Could not delete the selected vehicle.");
        });
    }

    function createVehicleIconButton(scope, vehicle, assignedRows, selectedRequest) {
      const tileElement = createNode("div", "transport-vehicle-tile");
      const vehicleButton = createNode("button", "transport-vehicle-button");
      const assignedCount = assignedRows.length;
      const isRouteCompatible =
        scope !== "extra" || !vehicle.route_kind || vehicle.route_kind === getSelectedRouteKind();
      const isSelectable = !!selectedRequest && selectedRequest.request_kind === scope && isRouteCompatible;
      const isAssignedToSelection =
        !!selectedRequest &&
        !!selectedRequest.assigned_vehicle &&
        Number(selectedRequest.assigned_vehicle.id) === Number(vehicle.id);
      const vehicleDetailsKey = getVehicleDetailsKey(scope, vehicle.id);
      const isExpanded = state.expandedVehicleKey === vehicleDetailsKey;

      vehicleButton.type = "button";
      vehicleButton.dataset.vehicleId = String(vehicle.id);
      vehicleButton.dataset.vehicleScope = scope;
      vehicleButton.title = `${mapVehicleTypeLabel(vehicle.tipo)} ${formatVehicleOccupancyLabel(vehicle, assignedCount)}`;
      vehicleButton.setAttribute("aria-label", vehicleButton.title);
      vehicleButton.classList.toggle("is-selectable", isSelectable);
      vehicleButton.classList.toggle("is-assigned", isAssignedToSelection);
      vehicleButton.classList.toggle("is-details-open", isExpanded);
      tileElement.classList.toggle("is-expanded", isExpanded);
      if (!isSelectable) {
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
      const routeLabel = vehicle.route_kind
        ? createNode("span", "transport-vehicle-route", getRouteKindLabel(vehicle.route_kind))
        : null;

      if (vehicle.route_kind) {
        vehicleButton.title = `${vehicleButton.title} | ${getRouteKindLabel(vehicle.route_kind)}`;
      }
      vehicleButton.appendChild(plateLabel);
      vehicleButton.appendChild(iconImage);
      vehicleButton.appendChild(occupancyLabel);
      if (routeLabel) {
        vehicleButton.appendChild(routeLabel);
      }
      vehicleButton.addEventListener("click", function () {
        if (!selectedRequest || selectedRequest.request_kind !== scope || isAssignedToSelection || !isRouteCompatible) {
          toggleVehicleDetails(scope, vehicle.id);
          return;
        }

        state.expandedVehicleKey = vehicleDetailsKey;
        submitAssignment({
          request_id: selectedRequest.id,
          service_date: state.dashboard.selected_date,
          route_kind: getSelectedRouteKind(),
          status: "confirmed",
          vehicle_id: vehicle.id,
        }).catch(function (error) {
          handleProtectedRequestError(error, "Could not confirm the selected request.");
        });
      });

      tileElement.appendChild(vehicleButton);
      if (isExpanded) {
        tileElement.appendChild(createVehicleDetailsPanel(vehicle, assignedRows));
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
        const deleteButton = createNode(
          "button",
          "transport-vehicle-delete-button transport-vehicle-management-delete",
          "Delete"
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
      table.setAttribute("aria-label", `${mapScopeTitle(scope)} vehicles`);
      return table;
    }

    function renderVehiclePanels() {
      const selectedRequest = getSelectedRequest();

      syncVehicleViewToggleState();

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
            container.appendChild(createEmptyState(`No vehicles in ${mapScopeTitle(scope)} list.`));
            return;
          }
          container.appendChild(createVehicleManagementTable(scope, registryRows));
          return;
        }

        if (!vehicles.length) {
          container.appendChild(createEmptyState(`No vehicles in ${mapScopeTitle(scope)} list.`));
          return;
        }

        vehicles.forEach(function (vehicle) {
          const assignedRows = assignedRowsByVehicle[String(vehicle.id)] || [];
          container.appendChild(createVehicleIconButton(scope, vehicle, assignedRows, selectedRequest));
        });

        updateVehicleGridLayout(container);
      });
    }

    function renderDashboard() {
      ensureSelectedRequestStillExists();
      ensureExpandedVehicleStillExists();
      renderSelectionBanner();
      renderRequestTables();
      renderVehiclePanels();
    }

    function clearDashboard() {
      REQUEST_SECTION_ORDER.forEach(function (kind) {
        const container = requestContainers[kind];
        clearElement(container);
        if (container) {
          container.appendChild(createEmptyState(`No rows in ${REQUEST_TITLES[kind]}.`));
        }
      });
      VEHICLE_SCOPE_ORDER.forEach(function (scope) {
        const container = vehicleContainers[scope];
        clearElement(container);
        if (container) {
          setVehicleContainerViewMode(container, scope);
          container.appendChild(createEmptyState(`No vehicles in ${mapScopeTitle(scope)} list.`));
          container.style.removeProperty("grid-template-rows");
          container.style.removeProperty("grid-auto-columns");
        }
      });
      state.expandedVehicleKey = null;
      syncVehicleViewToggleState();
      renderSelectionBanner();
    }

    function loadDashboard(selectedDate, options) {
      const loadOptions = options || {};
      const shouldAnnounce = loadOptions.announce !== false;
      if (!state.isAuthenticated) {
        state.dashboard = null;
        state.selectedRequestId = null;
        clearDashboard();
        setStatus(TRANSPORT_LOCKED_MESSAGE, "warning");
        return Promise.resolve(null);
      }

      state.isLoading = true;
      const serviceDate = formatIsoDate(selectedDate);
      const routeKind = getSelectedRouteKind();
      if (shouldAnnounce) {
        setStatus(`Loading ${getRouteKindLabel(routeKind)} dashboard.`, "info");
      }
      return requestJson(
        `/api/transport/dashboard?service_date=${encodeURIComponent(serviceDate)}&route_kind=${encodeURIComponent(routeKind)}`
      )
        .then(function (dashboard) {
          state.dashboard = dashboard || null;
          state.selectedRouteKind = (dashboard && dashboard.selected_route) || routeKind;
          syncRouteInputs();
          if (shouldAnnounce) {
            setStatus(`${getRouteKindLabel(getSelectedRouteKind())} dashboard updated.`, "info");
          }
          renderDashboard();
        })
        .catch(function (error) {
          state.dashboard = null;
          state.selectedRequestId = null;
          clearDashboard();
          if (error && Number(error.status) === 401) {
            clearTransportSession(TRANSPORT_SESSION_EXPIRED_MESSAGE);
            return;
          }
          setStatus((error && error.message) || "Could not load the transport dashboard.", "error");
        })
        .finally(function () {
          state.isLoading = false;
        });
    }

    return {
      bootstrapTransportSession,
      loadDashboard,
      refreshVehicleGridLayouts: function () {
        updateVehicleGridLayouts(document);
      },
    };
  }

  function initTransportPage() {
    if (typeof document === "undefined") {
      return;
    }

    const dateStore = createTransportDateStore(new Date());
    document.querySelectorAll("[data-date-panel]").forEach(function (panelElement) {
      createDatePanelController(panelElement, dateStore);
    });
    document.querySelectorAll("[data-resize]").forEach(enableResizableDivider);
    const pageController = createTransportPageController(dateStore);
    globalScope.CheckingTransportPageController = pageController;
    globalScope.addEventListener("resize", function () {
      pageController.refreshVehicleGridLayouts();
    });
    dateStore.subscribe(function (selectedDate) {
      pageController.loadDashboard(selectedDate);
    });
    pageController.bootstrapTransportSession();
  }

  const transportPageApi = {
    buildVehicleCreatePayload,
    clampValue,
    createTransportDateStore,
    extractApiMessage,
    formatApiErrorMessage,
    formatTransportDate,
    formatIsoDate,
    getTransportDateState,
    getOrdinalSuffix,
    formatVehicleOccupancyLabel,
    formatVehicleOccupancyCount,
    buildVehiclePassengerAwarenessRows,
    getPassengerAwarenessState,
    shouldHighlightRequestName,
    mapVehicleIconPath,
    parsePositiveNumber,
    resolvePanelSizes,
    resolveResizeConfig,
    startOfLocalDay,
    shiftLocalDay,
  };

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initTransportPage, { once: true });
    } else {
      initTransportPage();
    }
  }

  globalScope.CheckingTransportPage = transportPageApi;

  if (typeof module !== "undefined" && module.exports) {
    module.exports = transportPageApi;
  }
})(typeof window !== "undefined" ? window : globalThis);
