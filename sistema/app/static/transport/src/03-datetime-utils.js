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
    return startOfLocalDay(referenceValue || new Date());
  }

  function setStoredTransportDate(value) {
    if (!globalScope.localStorage) {
      return;
    }

    try {
      globalScope.localStorage.removeItem(TRANSPORT_SELECTED_DATE_STORAGE_KEY);
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

    function setValue(value, options) {
      selectedDate = startOfLocalDay(value);
      if (!options || options.notify !== false) {
        notify();
      }
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

  function getDefaultVehiclePanelHeight(scope) {
    const normalizedScope = String(scope || "").trim().toLowerCase();
    const defaultHeight = DEFAULT_VEHICLE_PANEL_HEIGHTS[normalizedScope];
    return Math.max(
      1,
      Number.isFinite(defaultHeight) ? defaultHeight : DEFAULT_VEHICLE_PANEL_HEIGHT_FALLBACK
    );
  }

  function resolveVehiclePanelExplicitHeight(options) {
    const panelOptions = options || {};
    const minHeight = Math.max(
      1,
      Math.round(Number(panelOptions.minHeight) || RESIZE_DEFAULT_MIN_SIZE)
    );
    const defaultHeight = Math.max(minHeight, getDefaultVehiclePanelHeight(panelOptions.scope));
    const requestedHeight = Number(panelOptions.requestedHeight);

    if (!Number.isFinite(requestedHeight) || requestedHeight <= 0) {
      return defaultHeight;
    }

    return Math.max(minHeight, Math.round(requestedHeight));
  }

  function resolveVehiclePanelResizedHeight(options) {
    const panelOptions = options || {};
    const startHeight = Math.max(
      1,
      Number.isFinite(Number(panelOptions.startHeight))
        ? Math.round(Number(panelOptions.startHeight))
        : getDefaultVehiclePanelHeight(panelOptions.scope)
    );
    const pointerDelta = Number(panelOptions.pointerDelta) || 0;

    return resolveVehiclePanelExplicitHeight({
      scope: panelOptions.scope,
      requestedHeight: startHeight + pointerDelta,
      minHeight: panelOptions.minHeight,
    });
  }

  function resolveVehiclePanelScope(panelElement) {
    const vehicleGrid = panelElement && typeof panelElement.querySelector === "function"
      ? panelElement.querySelector("[data-vehicle-scope]")
      : null;
    return vehicleGrid ? String(vehicleGrid.dataset.vehicleScope || "").trim().toLowerCase() : "";
  }

  function resolveVehiclePanelElementFromResizeHandle(handleElement) {
    let candidateElement = handleElement || null;

    while (candidateElement) {
      if (
        candidateElement.classList
        && typeof candidateElement.classList.contains === "function"
        && candidateElement.classList.contains("transport-pane")
      ) {
        return candidateElement;
      }
      candidateElement = candidateElement.parentElement || null;
    }

    return null;
  }

  function syncVehiclePanelExplicitHeights(rootElement) {
    const scopeRoot = rootElement || (typeof document !== "undefined" ? document : null);
    if (!scopeRoot || typeof scopeRoot.querySelectorAll !== "function") {
      return;
    }

    const synchronizedPanels = new Set();
    scopeRoot.querySelectorAll("[data-panel-resize-handle]").forEach(function (handleElement) {
      const panelElement = resolveVehiclePanelElementFromResizeHandle(handleElement);
      if (!panelElement || synchronizedPanels.has(panelElement)) {
        return;
      }

      synchronizedPanels.add(panelElement);
      const scope = resolveVehiclePanelScope(panelElement);
      if (!scope) {
        return;
      }

      const nextHeight = resolveVehiclePanelExplicitHeight({
        scope,
        requestedHeight: parsePixelValue(panelElement.style.height, 0),
        minHeight: resolvePanelMinimumSize(panelElement, RESIZE_DEFAULT_MIN_SIZE),
      });
      panelElement.style.height = `${nextHeight}px`;
    });
  }

  function isVehiclePanelResizeEnabledForViewport(viewportWidth) {
    return Number(viewportWidth) > VEHICLE_PANEL_RESIZE_DISABLE_MAX_WIDTH;
  }

  function isVehiclePanelResizeEnabled() {
    if (typeof globalScope.matchMedia === "function") {
      return !globalScope.matchMedia(`(max-width: ${VEHICLE_PANEL_RESIZE_DISABLE_MAX_WIDTH}px)`).matches;
    }

    const fallbackViewportWidth = typeof document !== "undefined" && document.documentElement
      ? document.documentElement.clientWidth
      : 0;

    return isVehiclePanelResizeEnabledForViewport(globalScope.innerWidth || fallbackViewportWidth);
  }

  function syncVehiclePanelResizeHandleState(rootElement) {
    const scopeRoot = rootElement || (typeof document !== "undefined" ? document : null);
    if (!scopeRoot || typeof scopeRoot.querySelectorAll !== "function") {
      return;
    }

    const resizeEnabled = isVehiclePanelResizeEnabled();

    scopeRoot.querySelectorAll("[data-panel-resize-handle]").forEach(function (handleElement) {
      const panelElement = resolveVehiclePanelElementFromResizeHandle(handleElement);
      const scope = resolveVehiclePanelScope(panelElement);
      if (!scope) {
        return;
      }

      const label = t("layout.resizeVehiclePanel", { scope: mapScopeTitle(scope) });
      handleElement.setAttribute("aria-label", label);
      handleElement.title = resizeEnabled ? label : "";

      if (resizeEnabled) {
        handleElement.disabled = false;
        handleElement.removeAttribute("disabled");
        handleElement.removeAttribute("aria-hidden");
        return;
      }

      handleElement.disabled = true;
      handleElement.setAttribute("disabled", "");
      handleElement.setAttribute("aria-hidden", "true");
    });
  }

  function enableVehiclePanelResizeHandle(handleElement) {
    if (!handleElement || typeof handleElement.addEventListener !== "function") {
      return;
    }

    handleElement.addEventListener("pointerdown", function (event) {
      if (!isVehiclePanelResizeEnabled() || handleElement.disabled) {
        return;
      }

      if (event.pointerType !== "touch" && event.button !== 0) {
        return;
      }

      const panelElement = resolveVehiclePanelElementFromResizeHandle(handleElement);
      const scope = resolveVehiclePanelScope(panelElement);
      if (!panelElement || !scope) {
        return;
      }

      const startHeight = Math.round(panelElement.getBoundingClientRect().height)
        || getDefaultVehiclePanelHeight(scope);
      const startPointerY = Number.isFinite(event.clientY) ? event.clientY : 0;
      const minHeight = resolvePanelMinimumSize(panelElement, RESIZE_DEFAULT_MIN_SIZE);

      function applyResize(moveEvent) {
        const pointerY = Number.isFinite(moveEvent.clientY) ? moveEvent.clientY : startPointerY;
        const nextHeight = resolveVehiclePanelResizedHeight({
          scope,
          startHeight,
          pointerDelta: pointerY - startPointerY,
          minHeight,
        });

        panelElement.style.height = `${nextHeight}px`;
        updateVehicleGridLayouts(panelElement);
      }

      function stopResize() {
        globalScope.removeEventListener("pointermove", applyResize);
        globalScope.removeEventListener("pointerup", stopResize);
        globalScope.removeEventListener("pointercancel", stopResize);
        updateVehicleGridLayouts(panelElement);
        if (typeof handleElement.releasePointerCapture === "function" && event.pointerId !== undefined) {
          try {
            handleElement.releasePointerCapture(event.pointerId);
          } catch (error) {}
        }
        document.body.classList.remove("transport-is-resizing");
      }

      if (typeof handleElement.setPointerCapture === "function" && event.pointerId !== undefined) {
        try {
          handleElement.setPointerCapture(event.pointerId);
        } catch (error) {}
      }

      document.body.classList.add("transport-is-resizing");
      globalScope.addEventListener("pointermove", applyResize);
      globalScope.addEventListener("pointerup", stopResize, { once: true });
      globalScope.addEventListener("pointercancel", stopResize, { once: true });
      applyResize(event);
      event.preventDefault();
    });

    handleElement.addEventListener("keydown", function (event) {
      if (!isVehiclePanelResizeEnabled() || handleElement.disabled) {
        return;
      }

      const panelElement = resolveVehiclePanelElementFromResizeHandle(handleElement);
      const scope = resolveVehiclePanelScope(panelElement);
      if (!panelElement || !scope) {
        return;
      }

      let pointerDelta = 0;
      if (event.key === "ArrowUp") {
        pointerDelta = -(event.shiftKey ? VEHICLE_PANEL_KEYBOARD_RESIZE_LARGE_STEP : VEHICLE_PANEL_KEYBOARD_RESIZE_STEP);
      } else if (event.key === "ArrowDown") {
        pointerDelta = event.shiftKey ? VEHICLE_PANEL_KEYBOARD_RESIZE_LARGE_STEP : VEHICLE_PANEL_KEYBOARD_RESIZE_STEP;
      } else if (event.key === "PageUp") {
        pointerDelta = -VEHICLE_PANEL_KEYBOARD_RESIZE_LARGE_STEP;
      } else if (event.key === "PageDown") {
        pointerDelta = VEHICLE_PANEL_KEYBOARD_RESIZE_LARGE_STEP;
      } else {
        return;
      }

      const currentHeight = Math.round(panelElement.getBoundingClientRect().height)
        || parsePixelValue(panelElement.style.height, getDefaultVehiclePanelHeight(scope));
      const nextHeight = resolveVehiclePanelResizedHeight({
        scope,
        startHeight: currentHeight,
        pointerDelta,
        minHeight: resolvePanelMinimumSize(panelElement, RESIZE_DEFAULT_MIN_SIZE),
      });

      panelElement.style.height = `${nextHeight}px`;
      updateVehicleGridLayouts(panelElement);
      event.preventDefault();
    });
  }

  function resolveVehicleDetailsPosition(options) {
    const anchorRect = options.anchorRect || {};
    const viewportWidth = Math.max(0, Number(options.viewportWidth) || 0);
    const viewportHeight = Math.max(0, Number(options.viewportHeight) || 0);
    const panelWidth = Math.max(1, Number(options.panelWidth) || 0);
    const panelHeight = Math.max(1, Number(options.panelHeight) || 0);
    const offset = Math.max(0, Number(options.offset) || 0);
    const viewportMargin = Math.max(0, Number(options.viewportMargin) || 0);
    const anchorLeft = Number(anchorRect.left) || 0;
    const anchorTop = Number(anchorRect.top) || 0;
    const anchorRight = Number(anchorRect.right);
    const anchorBottom = Number(anchorRect.bottom);
    const anchorWidth = Math.max(
      0,
      Number(anchorRect.width)
      || (Number.isFinite(anchorRight) ? anchorRight - anchorLeft : 0)
    );
    const anchorHeight = Math.max(
      0,
      Number(anchorRect.height)
      || (Number.isFinite(anchorBottom) ? anchorBottom - anchorTop : 0)
    );
    const maxLeft = Math.max(viewportMargin, viewportWidth - panelWidth - viewportMargin);
    const maxTop = Math.max(viewportMargin, viewportHeight - panelHeight - viewportMargin);
    let left = (Number.isFinite(anchorRight) ? anchorRight : anchorLeft + anchorWidth) + offset;
    let horizontalDirection = "right";

    if (left + panelWidth + viewportMargin > viewportWidth) {
      left = anchorLeft - panelWidth - offset;
      horizontalDirection = "left";
    }

    if (left < viewportMargin) {
      left = anchorLeft + ((anchorWidth - panelWidth) / 2);
      horizontalDirection = "center";
    }

    return {
      left: Math.round(clampValue(left, viewportMargin, maxLeft)),
      top: Math.round(
        clampValue(
          anchorTop + ((anchorHeight - panelHeight) / 2),
          viewportMargin,
          maxTop
        )
      ),
      horizontalDirection,
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

  function getWaitingLabel() {
    const waitingLabel = t("misc.waiting");
    return waitingLabel === "misc.waiting" ? "Waiting" : waitingLabel;
  }

  function getWaitingAriaLabel() {
    const waitingAriaLabel = t("misc.waitingAria");
    return waitingAriaLabel === "misc.waitingAria" ? "Vehicle field pending completion" : waitingAriaLabel;
  }

  function isPendingVehicleField(value) {
    if (value === null || value === undefined) {
      return true;
    }

    if (typeof value === "string") {
      return !value.trim();
    }

    return false;
  }

  function formatPendingVehicleField(value, formatter) {
    if (isPendingVehicleField(value)) {
      return getWaitingLabel();
    }

    if (typeof formatter === "function") {
      return formatter(value);
    }

    return String(value);
  }

  function createWaitingNode(tagName, className) {
    const waitingNode = createNode(tagName || "span", className, getWaitingLabel());
    waitingNode.classList.add("transport-pending-value");
    waitingNode.setAttribute("aria-label", getWaitingAriaLabel());
    return waitingNode;
  }

  function createPendingVehicleFieldNode(tagName, className, value, formatter) {
    if (isPendingVehicleField(value)) {
      return createWaitingNode(tagName, className);
    }

    return createNode(tagName, className, formatPendingVehicleField(value, formatter));
  }

  function isVehicleReadyForAllocation(vehicle) {
    if (!vehicle || typeof vehicle !== "object") {
      return false;
    }

    if (typeof vehicle.is_ready_for_allocation === "boolean") {
      return vehicle.is_ready_for_allocation;
    }

    return !isPendingVehicleField(vehicle.tipo)
      && !isPendingVehicleField(vehicle.lugares)
      && !isPendingVehicleField(vehicle.tolerance);
  }

  function getVehiclePendingAllocationMessage(vehicle) {
    if (isVehicleReadyForAllocation(vehicle)) {
      return "";
    }

    const pendingAllocationMessage = t("warnings.vehiclePendingAllocation");
    return pendingAllocationMessage === "warnings.vehiclePendingAllocation"
      ? "This vehicle is still missing required allocation data."
      : pendingAllocationMessage;
  }

