(function (globalScope) {
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
  }

  const transportPageApi = {
    formatTransportDate,
    getOrdinalSuffix,
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
