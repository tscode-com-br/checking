(function (globalScope) {
  const RESIZE_DEFAULT_MIN_SIZE = 96;
  const REQUEST_SECTION_ORDER = ["extra", "weekend", "regular"];
  const VEHICLE_SCOPE_ORDER = ["extra", "weekend", "regular"];
  const REQUEST_TITLE_KEYS = {
    regular: "requests.titles.regular",
    weekend: "requests.titles.weekend",
    extra: "requests.titles.extra",
  };
  const REQUEST_LABEL_KEYS = {
    regular: "requests.labels.regular",
    weekend: "requests.labels.weekend",
    extra: "requests.labels.extra",
  };
  const VEHICLE_ICON_PATHS = {
    carro: "icons/car.svg",
    minivan: "icons/minivan.svg",
    van: "icons/van.svg",
    onibus: "icons/bus.svg",
  };
  const ROUTE_KIND_KEYS = {
    home_to_work: "routes.home_to_work",
    work_to_home: "routes.work_to_home",
  };
  const MODAL_SCOPE_NOTE_KEYS = {
    extra: "modal.notes.extra",
    weekend: "modal.notes.weekend",
    regular: "modal.notes.regular",
  };
  const TRANSPORT_LANGUAGE_STORAGE_KEY = "checking.transport.dashboard.language";
  const TRANSPORT_SELECTED_DATE_STORAGE_KEY = "checking.transport.dashboard.selectedDate";
  const transportI18n = globalScope.CheckingTransportI18n || {};
  const TRANSPORT_DEFAULT_LANGUAGE = transportI18n.defaultLanguage || "en";
  const DEFAULT_WORK_TO_HOME_TIME = "16:45";
  const DEFAULT_LAST_UPDATE_TIME = "16:00";
  const VEHICLE_DEFAULT_TOLERANCE_MINUTES = 5;
  const VEHICLE_DEFAULT_SEAT_COUNT = {
    carro: 3,
    minivan: 6,
    van: 10,
    onibus: 40,
  };
  const transportLanguages = Array.isArray(transportI18n.languages) && transportI18n.languages.length
    ? transportI18n.languages.slice()
    : [{ code: "en", label: "English", locale: "en-US" }];
  const TRANSPORT_AUTH_VERIFY_DELAY_MS = 140;
  const TRANSPORT_REALTIME_DEBOUNCE_MS = 180;
  const VEHICLE_DETAILS_MAX_ROWS = 5;
  const VEHICLE_GRID_FALLBACK_ITEM_WIDTH = 104;
  const VEHICLE_GRID_FALLBACK_ITEM_HEIGHT = 96;

  function getDictionaryForLanguage(languageCode) {
    if (transportI18n && typeof transportI18n.getDictionary === "function") {
      return transportI18n.getDictionary(languageCode);
    }

    if (transportI18n && transportI18n.dictionaries && transportI18n.dictionaries[languageCode]) {
      return transportI18n.dictionaries[languageCode];
    }

    return (transportI18n && transportI18n.dictionaries && transportI18n.dictionaries[TRANSPORT_DEFAULT_LANGUAGE]) || {};
  }

  function resolveStoredLanguageCode() {
    if (!globalScope.localStorage) {
      return TRANSPORT_DEFAULT_LANGUAGE;
    }

    try {
      const storedValue = String(globalScope.localStorage.getItem(TRANSPORT_LANGUAGE_STORAGE_KEY) || "").trim();
      return transportLanguages.some(function (item) {
        return item.code === storedValue;
      }) ? storedValue : TRANSPORT_DEFAULT_LANGUAGE;
    } catch (error) {
      return TRANSPORT_DEFAULT_LANGUAGE;
    }
  }

  const transportLanguageState = {
    currentCode: resolveStoredLanguageCode(),
  };

  function setStoredLanguageCode(languageCode) {
    if (!globalScope.localStorage) {
      return;
    }

    try {
      globalScope.localStorage.setItem(TRANSPORT_LANGUAGE_STORAGE_KEY, languageCode);
    } catch (error) {}
  }

  function resolveLanguageCode(languageCode) {
    return transportLanguages.some(function (item) {
      return item.code === languageCode;
    }) ? languageCode : TRANSPORT_DEFAULT_LANGUAGE;
  }

  function getActiveLanguageCode() {
    return resolveLanguageCode(transportLanguageState.currentCode);
  }

  function setActiveLanguageCode(languageCode) {
    const resolvedCode = resolveLanguageCode(languageCode);
    transportLanguageState.currentCode = resolvedCode;
    setStoredLanguageCode(resolvedCode);
    return resolvedCode;
  }

  function getLanguageConfig(languageCode) {
    const resolvedCode = resolveLanguageCode(languageCode);
    const matchedLanguage = transportLanguages.find(function (item) {
      return item.code === resolvedCode;
    });
    return matchedLanguage || transportLanguages[0];
  }

  function readTranslationValue(dictionary, keyPath) {
    return String(keyPath || "")
      .split(".")
      .reduce(function (currentValue, segment) {
        if (!currentValue || typeof currentValue !== "object") {
          return undefined;
        }
        return currentValue[segment];
      }, dictionary);
  }

  function interpolateTranslation(template, values) {
    if (typeof template !== "string") {
      return "";
    }

    return template.replace(/\{(\w+)\}/g, function (_, token) {
      if (!values || values[token] === undefined || values[token] === null) {
        return "";
      }
      return String(values[token]);
    });
  }

  function t(keyPath, values, languageCode) {
    const dictionary = getDictionaryForLanguage(resolveLanguageCode(languageCode || getActiveLanguageCode()));
    const fallbackDictionary = getDictionaryForLanguage(TRANSPORT_DEFAULT_LANGUAGE);
    const template = readTranslationValue(dictionary, keyPath);
    const fallbackTemplate = readTranslationValue(fallbackDictionary, keyPath);
    return interpolateTranslation(template !== undefined ? template : fallbackTemplate !== undefined ? fallbackTemplate : keyPath, values);
  }

  function getTransportLockedMessage() {
    return t("status.locked");
  }

  function getTransportSessionExpiredMessage() {
    return t("status.sessionExpired");
  }

  function getDefaultStatusMessage() {
    return t("status.ready");
  }

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
    const activeLocale = getLanguageConfig(getActiveLanguageCode()).locale || "en-US";
    if (String(activeLocale).toLowerCase().startsWith("en")) {
      const weekdayFormatter = new Intl.DateTimeFormat(activeLocale, { weekday: "long" });
      const monthFormatter = new Intl.DateTimeFormat(activeLocale, { month: "long" });
      return `${weekdayFormatter.format(date)}, ${monthFormatter.format(date)} ${date.getDate()}${getOrdinalSuffix(date.getDate())}, ${date.getFullYear()}`;
    }

    return new Intl.DateTimeFormat(activeLocale, {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    }).format(date);
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

  function parseStoredTransportDate(value) {
    const rawValue = String(value || "").trim();
    const match = rawValue.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) {
      return null;
    }

    const year = Number(match[1]);
    const monthIndex = Number(match[2]) - 1;
    const dayOfMonth = Number(match[3]);
    const parsedDate = new Date(year, monthIndex, dayOfMonth);
    if (
      Number.isNaN(parsedDate.getTime())
      || parsedDate.getFullYear() !== year
      || parsedDate.getMonth() !== monthIndex
      || parsedDate.getDate() !== dayOfMonth
    ) {
      return null;
    }

    return startOfLocalDay(parsedDate);
  }

  function resolveStoredTransportDate(referenceValue) {
    const fallbackDate = startOfLocalDay(referenceValue || new Date());
    if (!globalScope.localStorage) {
      return fallbackDate;
    }

    try {
      const storedValue = globalScope.localStorage.getItem(TRANSPORT_SELECTED_DATE_STORAGE_KEY);
      return parseStoredTransportDate(storedValue) || fallbackDate;
    } catch (error) {
      return fallbackDate;
    }
  }

  function setStoredTransportDate(value) {
    if (!globalScope.localStorage) {
      return;
    }

    try {
      globalScope.localStorage.setItem(TRANSPORT_SELECTED_DATE_STORAGE_KEY, formatIsoDate(value));
    } catch (error) {
      // Ignore storage failures so the dashboard remains usable in restricted browsers.
    }
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

  function localizeTransportApiMessage(message) {
    const normalizedMessage = String(message || "").trim();
    if (!normalizedMessage) {
      return "";
    }

    const messageKey = {
      "Invalid key or password.": "auth.invalidCredentials",
      "This user does not have transport access.": "auth.noAccess",
      "Transport access granted.": "status.accessGranted",
      "Vehicle saved successfully.": "status.vehicleSaved",
      "Vehicle deleted from the database.": "status.vehicleDeleted",
      "Transport request rejected successfully.": "status.requestRejected",
      "departure_time is required for extra vehicles": "warnings.extraDepartureRequired",
      "Weekend vehicles must be persistent. Select Every Saturday and/or Every Sunday, or create the vehicle in Extra Transport List.": "warnings.weekendPersistence",
      "Regular vehicles can only be created from Monday to Friday.": "warnings.regularWeekdayOnly",
      "Weekend vehicles can only be created on Saturdays or Sundays.": "warnings.weekendWeekendOnly",
      "This vehicle cannot be removed from the selected route.": "warnings.vehicleCannotBeRemoved",
    }[normalizedMessage];

    return messageKey ? t(messageKey) : normalizedMessage;
  }

  function getDefaultVehicleSeatCount(vehicleType) {
    return VEHICLE_DEFAULT_SEAT_COUNT[vehicleType] || VEHICLE_DEFAULT_SEAT_COUNT.carro;
  }

  function getDefaultVehicleToleranceMinutes() {
    return VEHICLE_DEFAULT_TOLERANCE_MINUTES;
  }

  function getDefaultVehicleFormValues(vehicleType) {
    const normalizedVehicleType = Object.prototype.hasOwnProperty.call(VEHICLE_DEFAULT_SEAT_COUNT, vehicleType)
      ? vehicleType
      : "carro";

    return {
      tipo: normalizedVehicleType,
      lugares: getDefaultVehicleSeatCount(normalizedVehicleType),
      tolerance: getDefaultVehicleToleranceMinutes(),
    };
  }

  function normalizeVehicleScope(scope) {
    const normalizedScope = String(scope || "").trim().toLowerCase();
    if (normalizedScope === "regular" || normalizedScope === "weekend" || normalizedScope === "extra") {
      return normalizedScope;
    }
    return "regular";
  }

  function resolveVehicleForm(formElement) {
    if (formElement && formElement.elements) {
      return formElement;
    }

    if (typeof document === "undefined") {
      return null;
    }

    const resolvedForm = document.querySelector("[data-vehicle-form]");
    if (!resolvedForm || !resolvedForm.elements) {
      return null;
    }

    return resolvedForm;
  }

  function applyVehicleSeatDefault(vehicleType, formElement) {
    const resolvedForm = resolveVehicleForm(formElement);
    if (!resolvedForm || !resolvedForm.elements.lugares) {
      return;
    }
    resolvedForm.elements.lugares.value = String(getDefaultVehicleSeatCount(vehicleType));
  }

  function syncVehicleTypeDependentDefaults(vehicleType, formElement) {
    const resolvedForm = resolveVehicleForm(formElement);
    if (!resolvedForm) {
      return;
    }

    const normalizedVehicleType = Object.prototype.hasOwnProperty.call(VEHICLE_DEFAULT_SEAT_COUNT, vehicleType)
      ? vehicleType
      : "carro";

    if (resolvedForm.elements.tipo) {
      resolvedForm.elements.tipo.value = normalizedVehicleType;
    }

    applyVehicleSeatDefault(normalizedVehicleType, resolvedForm);

    if (resolvedForm.elements.tolerance) {
      resolvedForm.elements.tolerance.value = String(getDefaultVehicleToleranceMinutes());
    }
  }

  function applyVehicleFormDefaults(vehicleType, formElement) {
    const resolvedForm = resolveVehicleForm(formElement);
    if (!resolvedForm) {
      return;
    }

    const defaults = getDefaultVehicleFormValues(vehicleType);

    if (resolvedForm.elements.tipo) {
      resolvedForm.elements.tipo.value = defaults.tipo;
    }
    if (resolvedForm.elements.lugares) {
      resolvedForm.elements.lugares.value = String(defaults.lugares);
    }
    if (resolvedForm.elements.tolerance) {
      resolvedForm.elements.tolerance.value = String(defaults.tolerance);
    }
  }

  function buildVehicleCreatePayload(formData, serviceDate, selectedRouteKind) {
    const serviceScope = normalizeVehicleScope(formData.get("service_scope") || "regular");
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
      payload.departure_time = String(formData.get("departure_time") || "").trim();
      return payload;
    }

    if (serviceScope === "weekend") {
      payload.every_saturday = Boolean(formData.get("every_saturday"));
      payload.every_sunday = Boolean(formData.get("every_sunday"));
    }

    return payload;
  }

  function mapVehicleTypeLabel(value) {
    const normalizedValue = String(value || "").trim();
    const translatedValue = t(`vehicleTypes.${normalizedValue}`);
    return translatedValue === `vehicleTypes.${normalizedValue}` ? normalizedValue : translatedValue;
  }

  function formatVehicleTypeTableValue(value) {
    return String(mapVehicleTypeLabel(value) || value || "").toLowerCase();
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

  function isValidTransportTimeValue(value) {
    return /^\d{2}:\d{2}$/.test(String(value || "").trim());
  }

  function normalizeTransportTimeValue(value, fallbackValue) {
    return isValidTransportTimeValue(value) ? String(value || "").trim() : fallbackValue;
  }

  function getEffectiveWorkToHomeDepartureTime(dashboard, fallbackTime) {
    const dashboardTime = String(dashboard && dashboard.work_to_home_departure_time || "").trim();
    if (isValidTransportTimeValue(dashboardTime)) {
      return dashboardTime;
    }

    return normalizeTransportTimeValue(fallbackTime, DEFAULT_WORK_TO_HOME_TIME);
  }

  function getVehicleDepartureTime(vehicle) {
    const departureTime = String(vehicle && vehicle.departure_time || "").trim();
    return isValidTransportTimeValue(departureTime) ? departureTime : "";
  }

  function shouldHighlightRequestName(assignmentStatus) {
    return assignmentStatus === "pending" || assignmentStatus === "rejected" || assignmentStatus === "cancelled";
  }

  function getPassengerAwarenessState(requestRow) {
    return requestRow && requestRow.awareness_status === "aware" ? "aware" : "pending";
  }

  function isRequestAssignedToVehicle(requestRow, vehicle) {
    return Boolean(
      requestRow
      && requestRow.assigned_vehicle
      && vehicle
      && Number(requestRow.assigned_vehicle.id) === Number(vehicle.id)
    );
  }

  function canRequestBeDroppedOnVehicle(requestRow, scope, vehicle, routeKind) {
    if (!requestRow || !vehicle || requestRow.request_kind !== scope) {
      return false;
    }

    if (isRequestAssignedToVehicle(requestRow, vehicle)) {
      return false;
    }

    return scope !== "extra" || !vehicle.route_kind || vehicle.route_kind === routeKind;
  }

  function buildVehiclePassengerPreviewRows(assignedRows, previewRequestRow, maxRows) {
    const rows = Array.isArray(assignedRows)
      ? assignedRows.filter(function (requestRow) {
          return !previewRequestRow || Number(requestRow.id) !== Number(previewRequestRow.id);
        })
      : [];

    const previewRows = previewRequestRow ? [previewRequestRow].concat(rows) : rows;
    const normalizedMaxRows = Number.isFinite(Number(maxRows)) && Number(maxRows) > 0
      ? Math.max(1, Number(maxRows))
      : null;

    if (normalizedMaxRows === null) {
      return previewRows;
    }

    return previewRows.slice(0, normalizedMaxRows);
  }

  function buildVehiclePassengerAwarenessRows(assignedRows, maxRows) {
    const normalizedMaxRows = Math.max(1, Number(maxRows) || VEHICLE_DETAILS_MAX_ROWS);
    const rows = Array.isArray(assignedRows)
      ? assignedRows.map(function (requestRow) {
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
    return t(`modal.scope.${scope === "regular" || scope === "weekend" ? scope : "extra"}`);
  }

  function getRouteKindLabel(routeKind) {
    const routeKey = ROUTE_KIND_KEYS[routeKind];
    return routeKey ? t(routeKey) : routeKind;
  }

  function getModalScopeNote(scope) {
    const noteKey = MODAL_SCOPE_NOTE_KEYS[scope] || MODAL_SCOPE_NOTE_KEYS.regular;
    return t(noteKey);
  }

  function getRequestTitle(kind) {
    return t(REQUEST_TITLE_KEYS[kind] || REQUEST_TITLE_KEYS.regular);
  }

  function getRequestLabel(kind) {
    return t(REQUEST_LABEL_KEYS[kind] || REQUEST_LABEL_KEYS.regular);
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
      routeTimeSaving: false,
      requestSectionCollapsedByKind: {
        extra: false,
        weekend: false,
        regular: false,
      },
      requestRowCollapseOverrides: {},
    };
    const statusMessage = document.querySelector("[data-status-message]");
    const projectListToggle = document.querySelector("[data-project-list-toggle]");
    const projectListPanel = document.querySelector("[data-project-list-panel]");
    const projectListContainer = document.querySelector("[data-project-list]");
    const transportTopbar = document.querySelector("[data-transport-topbar]");
    const settingsTrigger = document.querySelector("[data-open-settings-modal]");
    const settingsTitleAnchor = document.querySelector("[data-settings-title-anchor]");
    const settingsRouteAnchor = document.querySelector("[data-settings-route-anchor]");
    const settingsModal = document.querySelector("[data-settings-modal]");
    const settingsPreferencesTitle = document.querySelector("[data-settings-preferences-title]");
    const settingsLanguageLabel = document.querySelector("[data-settings-language-label]");
    const settingsLanguageSelect = document.querySelector("[data-settings-language-select]");
    const settingsTimeLabel = document.querySelector("[data-settings-time-label]");
    const settingsTimeInput = document.querySelector("[data-settings-work-to-home-time]");
    const settingsLastUpdateLabel = document.querySelector("[data-settings-last-update-label]");
    const settingsLastUpdateInput = document.querySelector("[data-settings-last-update-time]");
    const settingsTimeNote = document.querySelector("[data-settings-time-note]");
    const settingsCloseButton = document.querySelector("[data-settings-close-button]");
    const vehicleModal = document.querySelector("[data-vehicle-modal]");
    const vehicleForm = document.querySelector("[data-vehicle-form]");
    const modalScopeLabel = document.querySelector("[data-modal-scope-label]");
    const modalScopeNote = document.querySelector("[data-modal-scope-note]");
    const vehicleModalFeedback = document.querySelector("[data-vehicle-modal-feedback]");
    const extraDepartureField = document.querySelector("[data-extra-departure-field]");
    const extraRouteField = document.querySelector("[data-extra-route-field]");
    const weekendPersistenceFields = Array.from(document.querySelectorAll("[data-weekend-persistence-field]"));
    const routeSelect = document.querySelector("[data-route-select]");
    const routeTimePopover = document.querySelector("[data-route-time-popover]");
    const routeTimeInput = document.querySelector("[data-route-time-input]");
    const authKeyInput = document.querySelector("[data-transport-auth-key]");
    const authPasswordInput = document.querySelector("[data-transport-auth-password]");
    const authKeyShell = document.querySelector('[data-transport-auth-shell="key"]');
    const authPasswordShell = document.querySelector('[data-transport-auth-shell="password"]');
    const requestUserButton = document.querySelector("[data-request-user-link]");
    const requestSectionToggleLinks = {};
    const vehicleViewToggleLinks = {};

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

    function applyStaticTranslations() {
      if (typeof document === "undefined") {
        return;
      }

      document.documentElement.lang = getActiveLanguageCode();
      document.title = t("document.title");

      const brandKicker = document.querySelector(".transport-topbar-brand .transport-topbar-kicker");
      const brandTitle = document.querySelector(".transport-topbar-brand .transport-topbar-title");
      const supportKicker = document.querySelector(".transport-topbar-support .transport-topbar-kicker");
      const topbarRouteOptions = routeSelect ? Array.from(routeSelect.options) : [];
      const authLabels = document.querySelectorAll(".transport-auth-label");
      const requestSectionTitles = document.querySelectorAll(".transport-request-section .transport-section-title-link");
      const paneLinks = document.querySelectorAll(".transport-pane-title-link");
      const addVehicleButtons = document.querySelectorAll("[data-open-vehicle-modal]");
      const modalFieldLabels = vehicleForm ? vehicleForm.querySelectorAll(".transport-field > span") : [];
      const weekendLabels = weekendPersistenceFields.map(function (fieldElement) {
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
      if (topbarRouteOptions[0]) {
        topbarRouteOptions[0].text = getRouteKindLabel("home_to_work");
      }
      if (topbarRouteOptions[1]) {
        topbarRouteOptions[1].text = getRouteKindLabel("work_to_home");
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
        modalFieldLabels[5].textContent = t("modal.fields.departureTime");
      }
      if (modalFieldLabels[6]) {
        modalFieldLabels[6].textContent = t("modal.fields.route");
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
      if (modalActionButtons[1]) {
        modalActionButtons[1].textContent = t("modal.actions.save");
      }

      if (settingsTrigger) {
        settingsTrigger.setAttribute("aria-label", t("settings.openAria"));
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
      if (routeSelect) {
        routeSelect.setAttribute("aria-label", t("layout.selectedTransportRoute"));
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
    }

    function syncRouteTimeControls() {
      const isWorkToHomeSelected = getSelectedRouteKind() === "work_to_home";
      const canEditRouteTime = state.isAuthenticated && isWorkToHomeSelected;
      const shouldShowRouteTime = isWorkToHomeSelected && state.isAuthenticated;
      const effectiveDepartureTime = getEffectiveWorkToHomeDepartureTime(state.dashboard, state.workToHomeTime);

      if (routeSelect) {
        routeSelect.value = getSelectedRouteKind();
        routeSelect.disabled = state.isLoading;
      }

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
      return requestJson("/api/transport/date-settings", {
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
      requestJson("/api/transport/auth/logout", { method: "POST" }).catch(function () {});
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
        syncSettingsControls();
        return Promise.resolve(null);
      }

      state.settingsLoading = true;
      syncSettingsControls();
      return requestJson("/api/transport/settings")
        .then(function (response) {
          state.settingsLoaded = true;
          state.workToHomeTime = String(
            response && response.work_to_home_time ? response.work_to_home_time : DEFAULT_WORK_TO_HOME_TIME
          );
          state.lastUpdateTime = String(
            response && response.last_update_time ? response.last_update_time : DEFAULT_LAST_UPDATE_TIME
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
      const normalizedTime = normalizeTransportTimeValue(
        nextValues && nextValues.workToHomeTime,
        normalizeTransportTimeValue(state.workToHomeTime, DEFAULT_WORK_TO_HOME_TIME)
      );
      const normalizedLastUpdateTime = normalizeTransportTimeValue(
        nextValues && nextValues.lastUpdateTime,
        normalizeTransportTimeValue(state.lastUpdateTime, DEFAULT_LAST_UPDATE_TIME)
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
      state.settingsSaving = true;
      syncSettingsControls();
      return requestJson("/api/transport/settings", {
        method: "PUT",
        body: JSON.stringify({
          work_to_home_time: normalizedTime,
          last_update_time: normalizedLastUpdateTime,
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
          return loadDashboard(dateStore.getValue(), { announce: false }).then(function () {
            setStatus(t("status.settingsSaved"), "success");
            return response;
          });
        })
        .catch(function (error) {
          state.workToHomeTime = previousWorkToHomeTime;
          state.lastUpdateTime = previousLastUpdateTime;
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
          scheduleSettingsTriggerPositionSync();
          if (state.isAuthenticated) {
            setStatus(t("status.dashboardUpdated", { route: getRouteKindLabel(getSelectedRouteKind()) }), "info");
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

    function resetAuthenticatedTransportField(event) {
      if (!state.isAuthenticated) {
        return;
      }
      event.preventDefault();
      clearTransportSession(t("status.accessReset"));
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
      authKeyInput.addEventListener("pointerdown", resetAuthenticatedTransportField);
    }

    if (authPasswordInput) {
      authPasswordInput.addEventListener("input", scheduleTransportVerification);
      authPasswordInput.addEventListener("pointerdown", resetAuthenticatedTransportField);
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
        void saveTransportSettings({
          workToHomeTime: settingsTimeInput.value,
          lastUpdateTime: settingsLastUpdateInput ? settingsLastUpdateInput.value : state.lastUpdateTime,
        });
      });
    }

    if (settingsLastUpdateInput) {
      settingsLastUpdateInput.addEventListener("change", function () {
        void saveTransportSettings({
          workToHomeTime: settingsTimeInput ? settingsTimeInput.value : state.workToHomeTime,
          lastUpdateTime: settingsLastUpdateInput.value,
        });
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

    if (routeSelect) {
      if (routeSelect.value) {
        state.selectedRouteKind = routeSelect.value || state.selectedRouteKind;
      }
      routeSelect.addEventListener("change", function () {
        closeRouteTimePopover();
        state.selectedRouteKind = routeSelect.value || "home_to_work";
        syncRouteTimeControls();
        loadDashboard(dateStore.getValue());
      });
    }

    if (settingsTrigger) {
      settingsTrigger.addEventListener("click", openSettingsModal);
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

        clearVehicleModalFeedback();
        if (payload.service_scope === "extra" && !String(payload.departure_time || "").trim()) {
          setVehicleModalFeedback(t("warnings.extraDepartureRequired"), "error");
          if (vehicleForm.elements.departure_time && typeof vehicleForm.elements.departure_time.focus === "function") {
            vehicleForm.elements.departure_time.focus();
          }
          return;
        }
        if (payload.service_scope === "weekend" && !payload.every_saturday && !payload.every_sunday) {
          setVehicleModalFeedback(
            t("warnings.weekendPersistence"),
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
            setStatus(t("status.vehicleSaved"), "success");
            return loadDashboard(dateStore.getValue(), { announce: false });
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

    scheduleSettingsTriggerPositionSync();

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

    function syncSettingsTriggerPosition() {
      if (!settingsTrigger || !transportTopbar || !settingsTitleAnchor || !settingsRouteAnchor) {
        return;
      }

      if (typeof globalScope.matchMedia === "function" && globalScope.matchMedia("(max-width: 860px)").matches) {
        settingsTrigger.style.left = "";
        settingsTrigger.style.top = "";
        return;
      }

      const topbarRect = transportTopbar.getBoundingClientRect();
      const titleRect = settingsTitleAnchor.getBoundingClientRect();
      const routeRect = settingsRouteAnchor.getBoundingClientRect();
      const triggerWidth = settingsTrigger.offsetWidth || 42;
      const triggerHeight = settingsTrigger.offsetHeight || 42;
      const left = (titleRect.right + routeRect.left) / 2 - topbarRect.left - triggerWidth / 2;
      const top = (routeRect.top + routeRect.bottom) / 2 - topbarRect.top - triggerHeight / 2;

      settingsTrigger.style.left = `${Math.max(0, left)}px`;
      settingsTrigger.style.top = `${Math.max(0, top)}px`;
    }

    function scheduleSettingsTriggerPositionSync() {
      if (typeof globalScope.requestAnimationFrame === "function") {
        globalScope.requestAnimationFrame(syncSettingsTriggerPosition);
        return;
      }
      syncSettingsTriggerPosition();
    }

    function openSettingsModal() {
      if (!settingsModal) {
        return;
      }
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

    function syncRouteInputs() {
      if (routeSelect) {
        routeSelect.value = getSelectedRouteKind();
      }
    }

    function getSelectedRouteKind() {
      return state.selectedRouteKind || "home_to_work";
    }

    function getCurrentServiceDateIso() {
      return formatIsoDate(dateStore.getValue());
    }

    function canOpenVehicleModal(scope) {
      if (!state.isAuthenticated) {
        setStatus(getTransportLockedMessage(), "warning");
        return false;
      }
      const selectedDate = dateStore.getValue();
      if (scope === "regular" && isWeekendDate(selectedDate)) {
        setStatus(t("warnings.regularWeekdayOnly"), "warning");
        return false;
      }
      if (scope === "weekend" && !isWeekendDate(selectedDate)) {
        setStatus(t("warnings.weekendWeekendOnly"), "warning");
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
      if (extraDepartureField) {
        extraDepartureField.hidden = normalizedScope !== "extra";
      }
      if (extraRouteField) {
        extraRouteField.hidden = normalizedScope !== "extra";
      }
      weekendPersistenceFields.forEach(function (fieldElement) {
        fieldElement.hidden = normalizedScope !== "weekend";
      });
      if (vehicleForm.elements.route_kind) {
        vehicleForm.elements.route_kind.value = getSelectedRouteKind();
        vehicleForm.elements.route_kind.disabled = normalizedScope !== "extra";
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
      vehicleModal.hidden = false;
      vehicleModal.dataset.scope = normalizedScope;
      vehicleForm.reset();
      clearVehicleModalFeedback();
      vehicleForm.elements.service_scope.value = normalizedScope;
      applyVehicleFormDefaults("carro", vehicleForm);
      if (vehicleForm.elements.departure_time) {
        vehicleForm.elements.departure_time.value = "";
      }
      syncVehicleModalFields(normalizedScope);
      if (
        normalizedScope === "extra"
        && vehicleForm.elements.departure_time
        && typeof vehicleForm.elements.departure_time.focus === "function"
      ) {
        vehicleForm.elements.departure_time.focus();
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

    function createPassengerRemoveButton(requestRow, routeKind) {
      const removeButton = createNode("button", "transport-passenger-remove-button", "×");
      const normalizedRouteKind = routeKind || getSelectedRouteKind();
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
            route_kind: detailOptions.routeKind || getSelectedRouteKind(),
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

      return requestJson("/api/transport/requests/reject", {
        method: "POST",
        body: JSON.stringify({
          request_id: requestRow.id,
          service_date: requestRow.service_date,
          route_kind: getSelectedRouteKind(),
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
        `/api/transport/vehicles/${encodeURIComponent(String(vehicle.schedule_id))}?service_date=${encodeURIComponent(deleteServiceDate)}`,
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
      const departureTime = getVehicleDepartureTime(vehicle);
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
      const routeLabel = vehicle.route_kind
        ? createNode("span", "transport-vehicle-route", getRouteKindLabel(vehicle.route_kind))
        : null;

      if (vehicle.route_kind) {
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
          routeKind: getSelectedRouteKind(),
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
        tileElement.appendChild(createVehicleDetailsPanel(vehicle, assignedRows, {
          previewRequestRow,
          routeKind: pendingPreview ? pendingPreview.routeKind : getSelectedRouteKind(),
        }));
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
        const departureTime = getVehicleDepartureTime(rowData);
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
          container.appendChild(createVehicleIconButton(scope, vehicle, assignedRows));
        });

        updateVehicleGridLayout(container);
      });
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
        setStatus(t("status.loadingDashboard", { route: getRouteKindLabel(routeKind) }), "info");
      }
      return requestJson(
        `/api/transport/dashboard?service_date=${encodeURIComponent(serviceDate)}&route_kind=${encodeURIComponent(routeKind)}`
      )
        .then(function (dashboard) {
          state.dashboard = dashboard || null;
          reconcileProjectVisibility();
          state.selectedRouteKind = (dashboard && dashboard.selected_route) || routeKind;
          syncRouteInputs();
          syncRouteTimeControls();
          if (shouldAnnounce) {
            setStatus(t("status.dashboardUpdated", { route: getRouteKindLabel(getSelectedRouteKind()) }), "info");
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
        scheduleSettingsTriggerPositionSync();
      },
    };
  }

  function initTransportPage() {
    if (typeof document === "undefined") {
      return;
    }

    const dateStore = createTransportDateStore(resolveStoredTransportDate(new Date()));
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
    formatApiErrorMessage,
    formatTransportDate,
    formatIsoDate,
    getEffectiveWorkToHomeDepartureTime,
    getTransportDateState,
    getVehicleDepartureTime,
    getOrdinalSuffix,
    formatVehicleOccupancyLabel,
    formatVehicleOccupancyCount,
    getDefaultVehicleFormValues,
    getDefaultVehicleSeatCount,
    getDefaultVehicleToleranceMinutes,
    syncVehicleTypeDependentDefaults,
    buildVehiclePassengerAwarenessRows,
    getPassengerAwarenessState,
    parseStoredTransportDate,
    resolveStoredTransportDate,
    setStoredTransportDate,
    shouldHighlightRequestName,
    mapVehicleIconPath,
    buildVehiclePassengerPreviewRows,
    canRequestBeDroppedOnVehicle,
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
