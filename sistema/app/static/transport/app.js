(function (globalScope) {
  const RESIZE_DEFAULT_MIN_SIZE = 96;
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

  function createDatePanelController(rootElement) {
    const labelElement = rootElement.querySelector("[data-date-label]");
    const previousButton = rootElement.querySelector('[data-date-shift="-1"]');
    const nextButton = rootElement.querySelector('[data-date-shift="1"]');
    const todayButton = rootElement.querySelector("[data-date-today]");
    let selectedDate = startOfLocalDay(new Date());

    function render() {
      if (labelElement) {
        labelElement.textContent = formatTransportDate(selectedDate);
      }
    }

    if (previousButton) {
      previousButton.addEventListener("click", function () {
        selectedDate = shiftLocalDay(selectedDate, -1);
        render();
      });
    }

    if (nextButton) {
      nextButton.addEventListener("click", function () {
        selectedDate = shiftLocalDay(selectedDate, 1);
        render();
      });
    }

    if (todayButton) {
      todayButton.addEventListener("click", function () {
        selectedDate = startOfLocalDay(new Date());
        render();
      });
    }

    render();
  }

  function initTransportPage() {
    if (typeof document === "undefined") {
      return;
    }

    document.querySelectorAll("[data-date-panel]").forEach(createDatePanelController);
    document.querySelectorAll("[data-resize]").forEach(enableResizableDivider);
  }

  const transportPageApi = {
    clampValue,
    formatTransportDate,
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
