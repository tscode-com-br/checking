(function (globalScope) {
  const RESIZE_DEFAULT_MIN_SIZE = 96;
  const REQUEST_SECTION_ORDER = ["extra", "weekend", "regular"];
  const VEHICLE_SCOPE_ORDER = ["regular", "weekend", "extra"];
  const REQUEST_TITLES = {
    regular: "Regular Car Requests",
    weekend: "Weekend Car Requests",
    extra: "Extra Car Requests",
  };
  const REQUEST_LABELS = {
    regular: "REGULAR",
    weekend: "FIM DE SEMANA",
    extra: "EXTRA",
  };
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

      const containerRect = containerElement.getBoundingClientRect();
      const dividerRect = dividerElement.getBoundingClientRect();
      const containerSize = containerRect[resizeConfig.sizeProperty];
      const dividerSize = dividerRect[resizeConfig.sizeProperty];
      const minFirstSize = parsePositiveNumber(
        dividerElement.dataset.minFirst,
        RESIZE_DEFAULT_MIN_SIZE
      );
      const minSecondSize = parsePositiveNumber(
        dividerElement.dataset.minSecond,
        RESIZE_DEFAULT_MIN_SIZE
      );

      function applyResize(moveEvent) {
        const pointerOffset = moveEvent[
          orientation === "vertical" ? "clientX" : "clientY"
        ] - containerRect[resizeConfig.startProperty];
        const nextSizes = resolvePanelSizes({
          containerSize,
          dividerSize,
          pointerOffset,
          minFirstSize,
          minSecondSize,
        });
        containerElement.style[resizeConfig.gridProperty] = `${nextSizes.firstSize}px ${Math.round(dividerSize)}px ${nextSizes.secondSize}px`;
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
          const error = new Error(
            (payload && (payload.detail || payload.message)) || `HTTP ${response.status}`
          );
          error.status = response.status;
          error.payload = payload;
          throw error;
        }

        return payload;
      });
    });
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

  function mapScopeTitle(scope) {
    if (scope === "regular") {
      return "Regular";
    }
    if (scope === "weekend") {
      return "Weekend";
    }
    return "Extra";
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
    };
    const statusMessage = document.querySelector("[data-status-message]");
    const selectionBanner = document.querySelector("[data-selection-banner]");
    const selectionText = document.querySelector("[data-selection-text]");
    const clearSelectionButton = document.querySelector("[data-clear-selection]");
    const vehicleModal = document.querySelector("[data-vehicle-modal]");
    const vehicleForm = document.querySelector("[data-vehicle-form]");
    const modalScopeLabel = document.querySelector("[data-modal-scope-label]");

    document.querySelectorAll("[data-request-kind]").forEach(function (element) {
      requestContainers[element.dataset.requestKind] = element;
    });
    document.querySelectorAll("[data-vehicle-scope]").forEach(function (element) {
      vehicleContainers[element.dataset.vehicleScope] = element;
    });

    if (clearSelectionButton) {
      clearSelectionButton.addEventListener("click", function () {
        state.selectedRequestId = null;
        renderSelectionBanner();
        renderVehiclePanels();
        renderRequestTables();
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
        const payload = {
          service_scope: String(formData.get("service_scope") || "regular"),
          tipo: String(formData.get("tipo") || "carro"),
          placa: String(formData.get("placa") || ""),
          color: String(formData.get("color") || ""),
          lugares: Number(formData.get("lugares") || 0),
          tolerance: Number(formData.get("tolerance") || 0),
        };

        requestJson("/api/transport/vehicles", {
          method: "POST",
          body: JSON.stringify(payload),
        })
          .then(function () {
            closeVehicleModal();
            setStatus("Vehicle saved successfully.", "success");
            return loadDashboard(dateStore.getValue());
          })
          .catch(function (error) {
            setStatus(error.message || "Could not save vehicle.", "error");
          });
      });
    }

    function setStatus(message, tone) {
      if (!statusMessage) {
        return;
      }

      if (!message) {
        statusMessage.hidden = true;
        statusMessage.textContent = "";
        statusMessage.removeAttribute("data-tone");
        return;
      }

      statusMessage.hidden = false;
      statusMessage.textContent = message;
      statusMessage.dataset.tone = tone || "info";
    }

    function openVehicleModal(scope) {
      if (!vehicleModal || !vehicleForm) {
        return;
      }
      vehicleModal.hidden = false;
      vehicleModal.dataset.scope = scope;
      vehicleForm.reset();
      vehicleForm.elements.service_scope.value = scope;
      vehicleForm.elements.lugares.value = "4";
      vehicleForm.elements.tolerance.value = "10";
      if (modalScopeLabel) {
        modalScopeLabel.textContent = mapScopeTitle(scope);
      }
    }

    function closeVehicleModal() {
      if (!vehicleModal || !vehicleForm) {
        return;
      }
      vehicleModal.hidden = true;
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

    function ensureSelectedRequestStillExists() {
      const selectedRequest = getSelectedRequest();
      if (!selectedRequest) {
        state.selectedRequestId = null;
      }
    }

    function renderSelectionBanner() {
      const selectedRequest = getSelectedRequest();
      if (!selectionBanner || !selectionText) {
        return;
      }

      if (!selectedRequest) {
        selectionBanner.hidden = true;
        selectionText.textContent = "--";
        return;
      }

      selectionBanner.hidden = false;
      selectionText.textContent = `${REQUEST_LABELS[selectedRequest.request_kind]} ${selectedRequest.requested_time} - ${selectedRequest.nome}`;
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
        return loadDashboard(dateStore.getValue());
      });
    }

    function createVehicleActions(scope, vehicle, selectedRequest) {
      const actionBar = createNode("div", "transport-card-actions");
      const confirmButton = createNode("button", "transport-primary-button", "Confirm Selected");
      const rejectButton = createNode("button", "transport-secondary-button", "Reject Selected");

      if (!selectedRequest || selectedRequest.request_kind !== scope) {
        confirmButton.disabled = true;
        rejectButton.disabled = true;
      }

      if (
        selectedRequest &&
        selectedRequest.assigned_vehicle &&
        Number(selectedRequest.assigned_vehicle.id) === Number(vehicle.id)
      ) {
        confirmButton.textContent = "Already Confirmed";
      }

      confirmButton.addEventListener("click", function () {
        if (!selectedRequest || selectedRequest.request_kind !== scope) {
          return;
        }
        submitAssignment({
          request_id: selectedRequest.id,
          service_date: state.dashboard.selected_date,
          status: "confirmed",
          vehicle_id: vehicle.id,
        }).catch(function (error) {
          setStatus(error.message || "Could not confirm the selected request.", "error");
        });
      });

      rejectButton.addEventListener("click", function () {
        if (!selectedRequest || selectedRequest.request_kind !== scope) {
          return;
        }
        submitAssignment({
          request_id: selectedRequest.id,
          service_date: state.dashboard.selected_date,
          status: "rejected",
        }).catch(function (error) {
          setStatus(error.message || "Could not reject the selected request.", "error");
        });
      });

      actionBar.appendChild(confirmButton);
      actionBar.appendChild(rejectButton);
      return actionBar;
    }

    function renderVehiclePanels() {
      const selectedRequest = getSelectedRequest();

      VEHICLE_SCOPE_ORDER.forEach(function (scope) {
        const container = vehicleContainers[scope];
        const vehicles = getVehiclesForScope(scope);
        const assignedRowsByVehicle = groupAssignedRequestsByVehicle(scope);
        clearElement(container);
        if (!container) {
          return;
        }

        if (!vehicles.length) {
          container.appendChild(createEmptyState(`No vehicles in ${mapScopeTitle(scope)} list.`));
          return;
        }

        vehicles.forEach(function (vehicle) {
          const vehicleCard = createNode("article", "transport-vehicle-card");
          const cardHead = createNode("div", "transport-card-head");
          const identity = createNode("div", "transport-card-identity");
          const plate = createNode("strong", "transport-card-plate", vehicle.placa);
          const badge = createNode("span", "transport-card-badge", mapVehicleTypeLabel(vehicle.tipo));
          identity.appendChild(plate);
          identity.appendChild(badge);
          cardHead.appendChild(identity);
          cardHead.appendChild(createNode("span", "transport-card-tolerance", `${vehicle.tolerance} min`));

          const metaGrid = createNode("div", "transport-card-meta-grid");
          metaGrid.appendChild(createNode("span", "transport-card-meta", `Color: ${vehicle.color || "-"}`));
          metaGrid.appendChild(createNode("span", "transport-card-meta", `Places: ${vehicle.lugares}`));

          const assignedList = createNode("div", "transport-assigned-list");
          const assignedRows = assignedRowsByVehicle[String(vehicle.id)] || [];
          if (assignedRows.length) {
            assignedList.appendChild(createNode("span", "transport-assigned-title", "Allocated today"));
            assignedRows.forEach(function (requestRow) {
              const assignedRow = createNode("div", "transport-assigned-row");
              assignedRow.appendChild(createNode("strong", null, requestRow.requested_time));
              assignedRow.appendChild(createNode("span", null, requestRow.nome));
              assignedList.appendChild(assignedRow);
            });
          } else {
            assignedList.appendChild(createNode("span", "transport-assigned-empty", "No allocations yet"));
          }

          vehicleCard.appendChild(cardHead);
          vehicleCard.appendChild(metaGrid);
          vehicleCard.appendChild(assignedList);
          vehicleCard.appendChild(createVehicleActions(scope, vehicle, selectedRequest));
          container.appendChild(vehicleCard);
        });
      });
    }

    function renderDashboard() {
      ensureSelectedRequestStillExists();
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
          container.appendChild(createEmptyState(`No vehicles in ${mapScopeTitle(scope)} list.`));
        }
      });
      renderSelectionBanner();
    }

    function loadDashboard(selectedDate) {
      state.isLoading = true;
      const serviceDate = formatIsoDate(selectedDate);
      return requestJson(`/api/transport/dashboard?service_date=${encodeURIComponent(serviceDate)}`)
        .then(function (dashboard) {
          state.dashboard = dashboard || null;
          setStatus("", "info");
          renderDashboard();
        })
        .catch(function (error) {
          state.dashboard = null;
          state.selectedRequestId = null;
          clearDashboard();
          if (error && Number(error.status) === 401) {
            setStatus("Administrative login is required to use the transport dashboard.", "error");
            return;
          }
          setStatus((error && error.message) || "Could not load the transport dashboard.", "error");
        })
        .finally(function () {
          state.isLoading = false;
        });
    }

    return {
      loadDashboard,
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
    dateStore.subscribe(function (selectedDate) {
      pageController.loadDashboard(selectedDate);
    });
  }

  const transportPageApi = {
    clampValue,
    createTransportDateStore,
    formatTransportDate,
    formatIsoDate,
    getTransportDateState,
    getOrdinalSuffix,
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
