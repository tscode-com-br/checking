(function (globalScope) {
  const RESIZE_DEFAULT_MIN_SIZE = 96;
  const VEHICLE_PANEL_RESIZE_DISABLE_MAX_WIDTH = 1180;
  const VEHICLE_PANEL_KEYBOARD_RESIZE_STEP = 24;
  const VEHICLE_PANEL_KEYBOARD_RESIZE_LARGE_STEP = 72;
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
  const TRANSPORT_ASSETS_PREFIX = "../assets";
  const TRANSPORT_API_PREFIX = "../api/transport";
  const VEHICLE_ICON_PATHS = {
    carro: `${TRANSPORT_ASSETS_PREFIX}/icons/car.svg`,
    minivan: `${TRANSPORT_ASSETS_PREFIX}/icons/minivan.svg`,
    van: `${TRANSPORT_ASSETS_PREFIX}/icons/van.svg`,
    onibus: `${TRANSPORT_ASSETS_PREFIX}/icons/bus.svg`,
  };
  const VEHICLE_TEMPORARY_ICON_PATHS = {
    carro: `${TRANSPORT_ASSETS_PREFIX}/icons/car-orange.svg`,
    minivan: `${TRANSPORT_ASSETS_PREFIX}/icons/minivan-orange.svg`,
    van: `${TRANSPORT_ASSETS_PREFIX}/icons/van-orange.svg`,
    onibus: `${TRANSPORT_ASSETS_PREFIX}/icons/bus-orange.svg`,
  };
  const VEHICLE_TEMPORARY_PLACEHOLDER_PATTERN = /^PLATE \d+$/;
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
  const DEFAULT_STATUS_MESSAGE_KEY = "status.ready";
  const transportI18n = globalScope.CheckingTransportI18n || {};
  const TRANSPORT_DEFAULT_LANGUAGE = transportI18n.defaultLanguage || "en";
  const DEFAULT_ARRIVE_AT_WORK_TIME = "07:45";
  const DEFAULT_WORK_TO_HOME_TIME = "16:45";
  const DEFAULT_LAST_UPDATE_TIME = "16:00";
  const DEFAULT_EXTRA_CAR_TOLERANCE_MINUTES = 30;
  const MINUTES_PER_DAY = 24 * 60;
  const DEFAULT_VEHICLE_TOLERANCE_MINUTES = 5;
  const DEFAULT_TRANSPORT_PRICE_RATE_UNIT = "day";
  const DEFAULT_AI_AGENT_REQUEST_KINDS = Object.freeze(["extra", "weekend", "regular"]);
  const DEFAULT_AI_AGENT_SETTINGS = {
    earliestBoardingTime: "06:50",
    arrivalAtWorkTime: "07:45",
    minOccupancy: { carro: 1, minivan: 3, van: 6, onibus: 30 },
  };
  const DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER = "openai";
  const AI_SETTINGS_PROJECT_CATALOG_STATUS = Object.freeze({
    idle: "idle",
    loading: "loading",
    ready: "ready",
    empty: "empty",
    error: "error",
  });
  const TRANSPORT_AI_SETTINGS_PROVIDER_DEFAULTS = Object.freeze({
    openai: Object.freeze({
      provider: "openai",
      label: "OpenAI",
      resolvedModel: "gpt-5.4-2026-03-05",
      reasoningEffort: "high",
    }),
    deepseek: Object.freeze({
      provider: "deepseek",
      label: "DeepSeek",
      resolvedModel: "deepseek-v4-pro",
      reasoningEffort: "high",
    }),
  });
  const TRANSPORT_AI_SUMMARY_PLACEHOLDER = "--";
  const TRANSPORT_AI_BIDIRECTIONAL_PLAN_CONTRACT = Object.freeze({
    regularWeekend: Object.freeze({
      outboundSourceOfTruth: "home_to_work",
      returnLegMode: "derived_from_outbound",
      sameVehicleRequired: true,
      samePassengersRequired: true,
      returnStopOrder: "reverse_outbound_stops",
      returnDurationStrategy: "recalculate_work_to_home",
    }),
    extra: Object.freeze({
      directionMode: "actual_request_direction",
      forbidProjectDestinationOnWorkToHome: true,
    }),
    fields: Object.freeze({
      canonicalReturnTime: "scheduled_dropoff_time",
      outboundBoardingTime: "boarding_time",
    }),
    review: Object.freeze({
      workToHomeSource: "backend_plan",
      forbidLocalReturnReconstruction: true,
    }),
    vehicleRef: Object.freeze({
      allowsMultipleRealLegs: true,
      groupingKey: "vehicle_ref",
    }),
  });
  const TRANSPORT_AI_REVIEW_TARGET_CONTRACT = Object.freeze({
    primaryPanelKey: "review",
    primarySurface: Object.freeze([
      "vehicle_tables",
      "management_table",
      "exceptions",
    ]),
    canonicalRow: Object.freeze({
      internalFields: Object.freeze(["request_id", "pickup_order"]),
      visibleFields: Object.freeze([
        "user_name",
        "user_address",
        "home_to_work_boarding",
        "work_to_home_dropoff",
      ]),
    }),
    ordering: Object.freeze({
      primaryRouteKind: "home_to_work",
      primaryField: "pickup_order",
      fallbackField: "scheduled_pickup_time",
    }),
    addressSource: Object.freeze({
      joinKey: "request_id",
      sourceCollection: "route_itineraries.stops",
      field: "address",
      forbidFormattedUiText: true,
    }),
    deferredPopulation: Object.freeze({
      work_to_home_dropoff: Object.freeze({
        allowPlaceholder: true,
        dependency: "modification_11",
      }),
    }),
    bidirectionalPlanning: TRANSPORT_AI_BIDIRECTIONAL_PLAN_CONTRACT,
    supportingPanels: Object.freeze(["vehicles", "passengers", "routes"]),
    auditPanelKey: "audit",
  });
  const TRANSPORT_AI_DYNAMIC_LABELS = Object.freeze({
    actions: Object.freeze({
      keep: Object.freeze({ keyPath: "ai.review.actions.keep", fallbackText: "Keep" }),
      create: Object.freeze({ keyPath: "ai.review.actions.create", fallbackText: "Add" }),
      update: Object.freeze({ keyPath: "ai.review.actions.update", fallbackText: "Update" }),
      remove_from_day: Object.freeze({
        keyPath: "ai.review.actions.removeFromDay",
        fallbackText: "Remove From Day",
      }),
    }),
    lists: Object.freeze({
      regular: Object.freeze({ keyPath: "ai.review.lists.regular", fallbackText: "Regular List" }),
      weekend: Object.freeze({ keyPath: "ai.review.lists.weekend", fallbackText: "Weekend List" }),
      extra: Object.freeze({ keyPath: "ai.review.lists.extra", fallbackText: "Extra List" }),
    }),
    stopTypes: Object.freeze({
      pickup: Object.freeze({ keyPath: "ai.review.stopTypes.pickup", fallbackText: "Pickup" }),
      destination: Object.freeze({ keyPath: "ai.review.stopTypes.destination", fallbackText: "Destination" }),
    }),
    topCards: Object.freeze({
      suggestedCost: Object.freeze({ keyPath: "ai.review.topCards.suggestedCost", fallbackText: "Suggested Cost" }),
      vehicles: Object.freeze({ keyPath: "ai.review.summary.vehicles", fallbackText: "Vehicles" }),
      passengers: Object.freeze({ keyPath: "ai.review.summary.passengers", fallbackText: "Passengers" }),
    }),
    detailItems: Object.freeze({
      currentCost: Object.freeze({ keyPath: "ai.review.detailItems.currentCost", fallbackText: "Current Cost" }),
      suggestedCost: Object.freeze({ keyPath: "ai.review.detailItems.suggestedCost", fallbackText: "Suggested Cost" }),
      costDelta: Object.freeze({ keyPath: "ai.review.detailItems.costDelta", fallbackText: "Cost Delta" }),
      vehicles: Object.freeze({ keyPath: "ai.review.summary.vehicles", fallbackText: "Vehicles" }),
      passengers: Object.freeze({ keyPath: "ai.review.summary.passengers", fallbackText: "Passengers" }),
      window: Object.freeze({ keyPath: "ai.review.detailItems.window", fallbackText: "Window" }),
      extraTolerance: Object.freeze({
        keyPath: "ai.review.detailItems.extraTolerance",
        fallbackText: "Extra Tolerance",
      }),
      planningInput: Object.freeze({ keyPath: "ai.review.detailItems.planningInput", fallbackText: "Planning Input" }),
      routeProvider: Object.freeze({
        keyPath: "ai.review.management.notes.routeProvider",
        fallbackText: "Route Provider",
      }),
      model: Object.freeze({ keyPath: "ai.review.management.notes.model", fallbackText: "Model" }),
    }),
    vehicleFields: Object.freeze({
      type: Object.freeze({ keyPath: "ai.review.meta.type", fallbackText: "Type" }),
      seats: Object.freeze({ keyPath: "ai.review.meta.seats", fallbackText: "Seats" }),
      identifier: Object.freeze({
        keyPath: "ai.review.vehicleChanges.fields.identifier",
        fallbackText: "Identifier",
      }),
      list: Object.freeze({ keyPath: "ai.review.meta.list", fallbackText: "List" }),
      cost: Object.freeze({ keyPath: "ai.review.meta.cost", fallbackText: "Cost" }),
      route: Object.freeze({ keyPath: "ai.review.meta.route", fallbackText: "Route" }),
    }),
    passengerFields: Object.freeze({
      project: Object.freeze({ keyPath: "ai.review.passengers.fields.project", fallbackText: "Project" }),
      requestKind: Object.freeze({
        keyPath: "ai.review.passengers.fields.requestKind",
        fallbackText: "Request Kind",
      }),
      vehicle: Object.freeze({ keyPath: "ai.review.passengers.fields.vehicle", fallbackText: "Vehicle" }),
      pickupOrder: Object.freeze({
        keyPath: "ai.review.passengers.fields.pickupOrder",
        fallbackText: "Pickup Order",
      }),
      pickup: Object.freeze({ keyPath: "ai.review.passengers.fields.pickup", fallbackText: "Pickup" }),
      arrival: Object.freeze({ keyPath: "ai.review.passengers.fields.arrival", fallbackText: "Arrival" }),
    }),
    routeFields: Object.freeze({
      project: Object.freeze({ keyPath: "ai.review.routes.fields.project", fallbackText: "Project" }),
      duration: Object.freeze({ keyPath: "ai.review.routes.fields.duration", fallbackText: "Duration" }),
      cost: Object.freeze({ keyPath: "ai.review.routes.fields.cost", fallbackText: "Cost" }),
      reference: Object.freeze({ keyPath: "ai.review.fields.reference", fallbackText: "Reference" }),
      arrival: Object.freeze({ keyPath: "ai.review.fields.arrival", fallbackText: "Arrival" }),
    }),
    auditFields: Object.freeze({
      promptVersion: Object.freeze({
        keyPath: "ai.review.audit.summary.promptVersion",
        fallbackText: "Prompt Version",
      }),
      routeProvider: Object.freeze({
        keyPath: "ai.review.audit.summary.routeProvider",
        fallbackText: "Route Provider",
      }),
      model: Object.freeze({ keyPath: "ai.review.audit.summary.model", fallbackText: "Model" }),
      planningInput: Object.freeze({
        keyPath: "ai.review.audit.summary.planningInput",
        fallbackText: "Planning Input",
      }),
    }),
  });
  const TRANSPORT_AI_DYNAMIC_TEXT = Object.freeze({
    noChange: Object.freeze({ keyPath: "ai.review.badges.noChange", fallbackText: "No Change" }),
    ready: Object.freeze({ keyPath: "ai.review.badges.ready", fallbackText: "Ready" }),
    pendingRequest: Object.freeze({
      keyPath: "ai.review.passengers.pendingRequest",
      fallbackText: "Pending Request",
    }),
    reviewTableAria: Object.freeze({
      keyPath: "ai.review.notes.reviewTableAria",
      fallbackText: "{vehicle} review table",
    }),
    vehicleId: Object.freeze({
      keyPath: "ai.review.notes.vehicleId",
      fallbackText: "Vehicle {id}",
    }),
    requestReference: Object.freeze({
      keyPath: "ai.review.notes.requestReference",
      fallbackText: "Request #{id}",
    }),
    runStatus: Object.freeze({
      keyPath: "ai.review.notes.runStatus",
      fallbackText: "Run {status}",
    }),
    suggestionStatus: Object.freeze({
      keyPath: "ai.review.notes.suggestionStatus",
      fallbackText: "Suggestion {status}",
    }),
    delta: Object.freeze({
      keyPath: "ai.review.notes.delta",
      fallbackText: "Delta {delta}",
    }),
    currentWithRate: Object.freeze({
      keyPath: "ai.review.notes.currentWithRate",
      fallbackText: "Current {current} | {rate}",
    }),
    routeCompletion: Object.freeze({
      keyPath: "ai.review.notes.routeCompletion",
      fallbackText: "{route} | Route completion {time}",
    }),
    fromPrevious: Object.freeze({
      keyPath: "ai.review.notes.fromPrevious",
      fallbackText: "From previous {segments}",
    }),
    noExtraTemporalClusters: Object.freeze({
      keyPath: "ai.review.notes.noExtraTemporalClusters",
      fallbackText: "No extra temporal clusters",
    }),
    extraClusters: Object.freeze({
      keyPath: "ai.review.notes.extraClusters",
      fallbackText: "Clusters {clusters}",
    }),
    routeCountInPlan: Object.freeze({
      keyPath: "ai.review.notes.routeCountInPlan",
      fallbackText: "{count} in plan",
    }),
    prompt: Object.freeze({
      keyPath: "ai.review.notes.prompt",
      fallbackText: "Prompt {prompt}",
    }),
    requestList: Object.freeze({
      keyPath: "ai.review.audit.requestList",
      fallbackText: "Requests {requests}",
    }),
    anchorBadge: Object.freeze({
      keyPath: "ai.review.audit.anchorBadge",
      fallbackText: "Anchor {time}",
    }),
    extraTolerance: Object.freeze({
      keyPath: "ai.review.audit.extraToleranceNote",
      fallbackText: "Extra tolerance {duration}",
    }),
    llm: Object.freeze({
      keyPath: "ai.review.audit.llmNote",
      fallbackText: "LLM {provider}",
    }),
    reasoning: Object.freeze({
      keyPath: "ai.review.audit.reasoningNote",
      fallbackText: "Reasoning {effort}",
    }),
    window: Object.freeze({
      keyPath: "ai.review.audit.windowNote",
      fallbackText: "Window {window}",
    }),
    vehicleChangesEmpty: Object.freeze({
      keyPath: "ai.review.vehicleChanges.empty",
      fallbackText: "Vehicle actions will appear in this panel once the review data is rendered.",
    }),
    passengerAllocationsEmpty: Object.freeze({
      keyPath: "ai.review.passengers.empty",
      fallbackText: "Passenger allocations will appear in this panel once the review data is rendered.",
    }),
    allocatedPassengersTitle: Object.freeze({
      keyPath: "ai.review.passengers.allocatedTitle",
      fallbackText: "Allocated Passengers",
    }),
    unallocatedPassengersTitle: Object.freeze({
      keyPath: "ai.review.passengers.unallocatedTitle",
      fallbackText: "Not Routed",
    }),
    routeItinerariesEmpty: Object.freeze({
      keyPath: "ai.review.routes.empty",
      fallbackText: "Route itineraries will appear in this panel once the review data is rendered.",
    }),
    routeStopsEmpty: Object.freeze({
      keyPath: "ai.review.routes.emptyStops",
      fallbackText: "No stops were generated for this route.",
    }),
    auditEmptyClusters: Object.freeze({
      keyPath: "ai.review.audit.emptyClusters",
      fallbackText: "No extra temporal clusters were captured for this suggestion.",
    }),
    removedFromDay: Object.freeze({
      keyPath: "ai.review.vehicleChanges.removedFromDay",
      fallbackText: "Removed from selected day",
    }),
  });
  const TRANSPORT_AI_STATUS_FALLBACKS = Object.freeze({
    proposed: "Proposed",
    shown: "Shown",
    saved: "Saved",
    applied: "Applied",
    requested: "Requested",
    baseline_saved: "Baseline Saved",
    passengers_reset: "Passengers Reset",
    running: "Running",
    cancelled: "Cancelled",
    discarded: "Discarded",
    expired: "Expired",
    failed: "Failed",
  });
  const TRANSPORT_AI_COUNT_LABELS = Object.freeze({
    action: Object.freeze({
      keyPathPrefix: "ai.review.counts.action",
      fallbackTextOne: "action",
      fallbackTextOther: "actions",
    }),
    vehicle: Object.freeze({
      keyPathPrefix: "ai.review.counts.vehicle",
      fallbackTextOne: "vehicle",
      fallbackTextOther: "vehicles",
    }),
    route: Object.freeze({
      keyPathPrefix: "ai.review.counts.route",
      fallbackTextOne: "route",
      fallbackTextOther: "routes",
    }),
    request: Object.freeze({
      keyPathPrefix: "ai.review.counts.request",
      fallbackTextOne: "request",
      fallbackTextOther: "requests",
    }),
    issue: Object.freeze({
      keyPathPrefix: "ai.review.counts.issue",
      fallbackTextOne: "issue",
      fallbackTextOther: "issues",
    }),
    blockingIssue: Object.freeze({
      keyPathPrefix: "ai.review.counts.blockingIssue",
      fallbackTextOne: "blocking issue",
      fallbackTextOther: "blocking issues",
    }),
    allocatedPassenger: Object.freeze({
      keyPathPrefix: "ai.review.counts.allocatedPassenger",
      fallbackTextOne: "allocated passenger",
      fallbackTextOther: "allocated passengers",
    }),
    create: Object.freeze({
      keyPathPrefix: "ai.review.counts.create",
      fallbackTextOne: "create",
      fallbackTextOther: "create",
    }),
    update: Object.freeze({
      keyPathPrefix: "ai.review.counts.update",
      fallbackTextOne: "update",
      fallbackTextOther: "update",
    }),
    remove: Object.freeze({
      keyPathPrefix: "ai.review.counts.remove",
      fallbackTextOne: "remove",
      fallbackTextOther: "remove",
    }),
    cluster: Object.freeze({
      keyPathPrefix: "ai.review.counts.cluster",
      fallbackTextOne: "cluster",
      fallbackTextOther: "clusters",
    }),
  });
  const TRANSPORT_AI_ROUTE_POLL_INTERVAL_MS = 1200;
  const TRANSPORT_AI_ROUTE_POLL_MAX_MS = 10000;
  const MAX_TRANSPORT_PRICE_VALUE = 9999999999.99;
  const TRANSPORT_CURRENCY_CODE_PATTERN = /^[A-Z0-9]{2,12}$/;
  const TRANSPORT_PRICE_RATE_UNITS = ["hour", "day", "week", "month"];
  const DEFAULT_VEHICLE_SEAT_COUNT = {
    carro: 3,
    minivan: 6,
    van: 10,
    onibus: 40,
  };
  const DEFAULT_VEHICLE_PRICE_DEFAULTS = {
    carro: null,
    minivan: null,
    van: null,
    onibus: null,
  };
  const VEHICLE_BASE_FIELD_ORDER = ["tipo", "placa", "color", "lugares", "tolerance"];
  let vehicleDefaultSeatCount = Object.assign({}, DEFAULT_VEHICLE_SEAT_COUNT);
  let vehicleDefaultToleranceMinutes = DEFAULT_VEHICLE_TOLERANCE_MINUTES;
  const transportLanguages = Array.isArray(transportI18n.languages) && transportI18n.languages.length
    ? transportI18n.languages.slice()
    : [{ code: "en", label: "English", locale: "en-US" }];
  const TRANSPORT_AUTH_VERIFY_DELAY_MS = 650;
  const TRANSPORT_REALTIME_DEBOUNCE_MS = 180;
  const TRANSPORT_REALTIME_RECONNECT_BASE_MS = 1000;
  const TRANSPORT_REALTIME_RECONNECT_MAX_MS = 15000;
  const VEHICLE_DETAILS_MAX_ROWS = 5;
  const VEHICLE_GRID_FALLBACK_ITEM_WIDTH = 104;
  const VEHICLE_GRID_FALLBACK_ITEM_HEIGHT = 96;
  const VEHICLE_DETAILS_VIEWPORT_MARGIN = 12;
  const VEHICLE_DETAILS_PANEL_OFFSET = 10;
  const DEFAULT_VEHICLE_PANEL_HEIGHTS = Object.freeze({
    extra: 288,
    weekend: 272,
    regular: 256,
  });
  const DEFAULT_VEHICLE_PANEL_HEIGHT_FALLBACK = 260;

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

  function getResolvedTranslationOrNull(keyPath, values, languageCode) {
    const normalizedKeyPath = String(keyPath || "").trim();
    if (!normalizedKeyPath) {
      return null;
    }

    const translatedValue = t(normalizedKeyPath, values, languageCode);
    return translatedValue === normalizedKeyPath ? null : translatedValue;
  }

  function applyTranslatedAttribute(element, attributeName, keyPath, values, languageCode) {
    if (!element || typeof element.setAttribute !== "function") {
      return;
    }

    const translatedValue = getResolvedTranslationOrNull(keyPath, values, languageCode);
    if (translatedValue === null) {
      return;
    }

    element.setAttribute(attributeName, translatedValue);
    if (attributeName in element) {
      element[attributeName] = translatedValue;
    }
  }

  function applyDeclarativeTranslations(rootElement, languageCode) {
    const translationRoot = rootElement || (typeof document !== "undefined" ? document : null);
    const resolvedLanguageCode = resolveLanguageCode(languageCode || getActiveLanguageCode());
    if (!translationRoot || typeof translationRoot.querySelectorAll !== "function") {
      return;
    }

    translationRoot.querySelectorAll("[data-i18n-text]").forEach(function (element) {
      const translatedValue = getResolvedTranslationOrNull(element.dataset.i18nText, undefined, resolvedLanguageCode);
      if (translatedValue === null) {
        return;
      }
      element.textContent = translatedValue;
    });

    translationRoot.querySelectorAll("[data-i18n-aria-label]").forEach(function (element) {
      applyTranslatedAttribute(
        element,
        "aria-label",
        element.dataset.i18nAriaLabel,
        undefined,
        resolvedLanguageCode
      );
    });

    translationRoot.querySelectorAll("[data-i18n-aria]").forEach(function (element) {
      applyTranslatedAttribute(
        element,
        "aria-label",
        element.dataset.i18nAria,
        undefined,
        resolvedLanguageCode
      );
    });

    translationRoot.querySelectorAll("[data-i18n-placeholder]").forEach(function (element) {
      applyTranslatedAttribute(
        element,
        "placeholder",
        element.dataset.i18nPlaceholder,
        undefined,
        resolvedLanguageCode
      );
    });

    translationRoot.querySelectorAll("[data-i18n-title]").forEach(function (element) {
      applyTranslatedAttribute(
        element,
        "title",
        element.dataset.i18nTitle,
        undefined,
        resolvedLanguageCode
      );
    });

    translationRoot.querySelectorAll("[data-i18n-option]").forEach(function (element) {
      const translatedValue = getResolvedTranslationOrNull(element.dataset.i18nOption, undefined, resolvedLanguageCode);
      if (translatedValue === null) {
        return;
      }
      element.textContent = translatedValue;
    });
  }

  function applyDocumentLanguageMetadata(languageCode) {
    if (typeof document === "undefined" || !document.documentElement) {
      return;
    }

    const resolvedLanguageCode = resolveLanguageCode(languageCode || getActiveLanguageCode());
    document.documentElement.lang = resolvedLanguageCode;
    if (typeof document.documentElement.setAttribute === "function") {
      document.documentElement.setAttribute("lang", resolvedLanguageCode);
    }
    const documentTitle = getResolvedTranslationOrNull("document.title", undefined, resolvedLanguageCode);
    if (documentTitle !== null) {
      document.title = documentTitle;
    }
  }

  function applyInitialDeclarativeTranslations() {
    if (typeof document === "undefined") {
      return;
    }

    applyDocumentLanguageMetadata();
    applyDeclarativeTranslations(document);
  }

  function getTransportLockedMessage() {
    return t("status.locked");
  }

  function getTransportSessionExpiredMessage() {
    return t("status.sessionExpired");
  }

  function getDefaultStatusMessage() {
    return t(DEFAULT_STATUS_MESSAGE_KEY);
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

  function isTransportAiProjectRequiredErrorPayload(payload) {
    if (!payload || !Array.isArray(payload.detail)) {
      return false;
    }

    return payload.detail.some(function (item) {
      if (!item || typeof item !== "object") {
        return false;
      }

      const location = Array.isArray(item.loc) ? item.loc : [];
      const message = String(item.msg || "").trim();
      return location.includes("project_id") && /^field required$/i.test(message);
    });
  }

  function extractStructuredTransportApiPayload(payload) {
    if (!payload || typeof payload !== "object") {
      return null;
    }

    const directPayload = payload;
    const detailPayload = payload.detail && typeof payload.detail === "object" && !Array.isArray(payload.detail)
      ? payload.detail
      : null;

    function isStructuredContract(value) {
      if (!value || typeof value !== "object" || Array.isArray(value)) {
        return false;
      }
      return Boolean(
        value.message_key
        || value.error_code
        || value.issues
        || value.technical_detail
        || value.message
      );
    }

    if (isStructuredContract(detailPayload)) {
      return detailPayload;
    }
    if (isStructuredContract(directPayload)) {
      return directPayload;
    }
    return null;
  }

  function resolveTransportApiStructuredMessageOptions(payload) {
    const structuredPayload = extractStructuredTransportApiPayload(payload);
    if (!structuredPayload) {
      return null;
    }

    const messageKey = String(structuredPayload.message_key || "").trim();
    if (!messageKey) {
      return null;
    }

    return {
      key: messageKey,
      values: structuredPayload.message_params && typeof structuredPayload.message_params === "object"
        ? Object.assign({}, structuredPayload.message_params)
        : null,
    };
  }

  function resolveTransportApiStructuredMessage(payload) {
    const structuredPayload = extractStructuredTransportApiPayload(payload);
    if (!structuredPayload) {
      return "";
    }

    const messageKey = String(structuredPayload.message_key || "").trim();
    if (messageKey) {
      const params = structuredPayload.message_params && typeof structuredPayload.message_params === "object"
        ? structuredPayload.message_params
        : {};
      const translated = t(messageKey, params);
      if (translated && translated !== messageKey) {
        return translated;
      }
    }

    const structuredMessage = localizeTransportApiMessage(structuredPayload.message);
    if (structuredMessage) {
      return structuredMessage;
    }

    return String(structuredPayload.message || "").trim();
  }

  function formatApiErrorMessage(payload, statusCode) {
    const structuredMessage = resolveTransportApiStructuredMessage(payload);
    if (structuredMessage) {
      return structuredMessage;
    }

    if (isTransportAiProjectRequiredErrorPayload(payload)) {
      return "Transport AI project is required.";
    }

    const message = extractApiMessage(payload && (payload.detail !== undefined ? payload.detail : payload && payload.message));
    return message || `HTTP ${statusCode}`;
  }

  function localizeConfirmedExtraOverrideConflictMessage(message) {
    const conflictMessagePrefix = "The user already has a confirmed extra transport override for this date and route";
    const normalizedMessage = String(message || "").trim();
    if (!normalizedMessage.startsWith(conflictMessagePrefix)) {
      return "";
    }

    const suffix = normalizedMessage.slice(conflictMessagePrefix.length).trim();
    if (!suffix || suffix === ".") {
      return t("warnings.extraOverrideConflictGeneric");
    }

    const normalizedRouteList = suffix.replace(/^:\s*/, "").replace(/\.$/, "");
    if (!normalizedRouteList) {
      return t("warnings.extraOverrideConflictGeneric");
    }

    const routeLabels = normalizedRouteList
      .split(",")
      .map(function (routeKind) {
        const normalizedRouteKind = String(routeKind || "").trim();
        const routeKey = ROUTE_KIND_KEYS[normalizedRouteKind];
        return routeKey ? t(routeKey) : normalizedRouteKind;
      })
      .filter(Boolean);

    return routeLabels.length
      ? t("warnings.extraOverrideConflict", { route: routeLabels.join(", ") })
      : t("warnings.extraOverrideConflictGeneric");
  }

  function localizeTransportApiMessage(message) {
    const normalizedMessage = String(message || "").trim();
    if (!normalizedMessage) {
      return "";
    }
    if (/^HTTP\s+\d+$/i.test(normalizedMessage)) {
      return "";
    }

    const confirmedExtraOverrideMessage = localizeConfirmedExtraOverrideConflictMessage(normalizedMessage);
    if (confirmedExtraOverrideMessage) {
      return confirmedExtraOverrideMessage;
    }

    const messageKey = {
      "Invalid key or password.": "auth.invalidCredentials",
      "This user does not have transport access.": "auth.noAccess",
      "Sessao de transporte invalida ou expirada": "status.sessionExpired",
      "Transport access granted.": "status.accessGranted",
      "Vehicle saved successfully.": "status.vehicleSaved",
      "Vehicle updated successfully.": "status.vehicleUpdated",
      "Vehicle deleted from the database.": "status.vehicleDeleted",
      "Transport request rejected successfully.": "status.requestRejected",
      "Transport boarding time saved successfully.": "status.boardingTimeSaved",
      "Transport AI suggestion is ready for review.": "ai.agentSettingsReadyForReview",
      "Transport AI suggestion was saved and is ready to be applied.": "ai.changesCancelled",
      "Transport AI suggestion was cancelled and the baseline was restored.": "ai.changesCancelled",
      "Transport AI suggestion was applied.": "ai.changesApplied",
      "The transport AI suggestion can no longer be saved.": "ai.changesCancelFailed",
      "The transport AI suggestion cannot be saved because its payload is invalid.": "ai.changesCancelFailed",
      "The transport AI suggestion was already applied and cannot be cancelled.": "ai.changesCancelFailed",
      "The transport AI suggestion can no longer be cancelled.": "ai.changesCancelFailed",
      "Transport AI baseline restore requires manual review.": "ai.changesCancelFailed",
      "The transport AI suggestion can no longer be applied.": "ai.changesApplyFailed",
      "The transport AI suggestion cannot be applied because its payload is invalid.": "ai.changesApplyFailed",
      "The transport AI suggestion could not be materialized for apply.": "ai.changesApplyFailed",
      "Transport AI settings encryption is unavailable.": "ai.settingsEncryptionUnavailable",
      "Transport AI project is required.": "ai.settingsProjectRequired",
      "Transport AI API key is required.": "ai.settingsKeyRequired",
      "Transport AI API key is required when creating LLM settings.": "ai.settingsKeyRequired",
      "Transport AI API key is required when changing the LLM provider.": "ai.settingsProviderKeyRequired",
      "Transport AI API key is required when no encrypted key has been stored yet.": "ai.settingsKeyRequired",
      "Transport AI project does not exist.": "ai.settingsProjectMissing",
      "The configured Transport AI LLM provider is no longer supported. Select OpenAI or DeepSeek and save the AI settings again.": "ai.settingsProviderUnsupported",
      "Currency code already exists.": "warnings.currencyAlreadyExists",
      "departure_time is required for extra vehicles": "warnings.extraDepartureRequired",
      "The selected currency is not available.": "warnings.currencyNotAvailable",
      "Weekend vehicles must be persistent. Select Every Saturday and/or Every Sunday, or create the vehicle in Extra Transport List.": "warnings.weekendPersistence",
      "Regular vehicles must be persistent. Select at least one weekday": "warnings.regularPersistence",
      "Regular vehicles can only be created from Monday to Friday.": "warnings.regularWeekdayOnly",
      "Weekend vehicles can only be created on Saturdays or Sundays.": "warnings.weekendWeekendOnly",
      "This vehicle cannot be removed from the selected route.": "warnings.vehicleCannotBeRemoved",
      "The selected vehicle is not ready for allocation.": "warnings.vehiclePendingAllocation",
      "A confirmed transport assignment is required to update boarding_time.": "warnings.boardingTimeRequiresConfirmedAssignment",
      "Manual boarding_time is only available for confirmed home_to_work assignments.": "warnings.boardingTimeEtaOnly",
    }[normalizedMessage];

    return messageKey ? t(messageKey) : normalizedMessage;
  }

  function normalizeVehicleSeatCountSetting(value, fallbackValue) {
    const parsed = Number.parseInt(String(value), 10);
    if (!Number.isFinite(parsed) || parsed < 1 || parsed > 99) {
      return fallbackValue;
    }
    return parsed;
  }

  function resolveTransportVehicleSeatDefaults(source, fallbackValues) {
    const fallbackSeatDefaults = fallbackValues || DEFAULT_VEHICLE_SEAT_COUNT;
    return {
      carro: normalizeVehicleSeatCountSetting(
        source && (source.carro !== undefined ? source.carro : source.default_car_seats),
        fallbackSeatDefaults.carro
      ),
      minivan: normalizeVehicleSeatCountSetting(
        source && (source.minivan !== undefined ? source.minivan : source.default_minivan_seats),
        fallbackSeatDefaults.minivan
      ),
      van: normalizeVehicleSeatCountSetting(
        source && (source.van !== undefined ? source.van : source.default_van_seats),
        fallbackSeatDefaults.van
      ),
      onibus: normalizeVehicleSeatCountSetting(
        source && (source.onibus !== undefined ? source.onibus : source.default_bus_seats),
        fallbackSeatDefaults.onibus
      ),
    };
  }

  function applyTransportVehicleSeatDefaults(nextValues) {
    vehicleDefaultSeatCount = resolveTransportVehicleSeatDefaults(nextValues, vehicleDefaultSeatCount);
    return Object.assign({}, vehicleDefaultSeatCount);
  }

  function normalizeTransportCurrencyCode(value) {
    return String(value || "")
      .toUpperCase()
      .replace(/\s+/g, "")
      .trim();
  }

  function isValidTransportCurrencyCode(value) {
    return TRANSPORT_CURRENCY_CODE_PATTERN.test(normalizeTransportCurrencyCode(value));
  }

  function normalizeTransportCurrencyLabel(value) {
    const normalizedValue = String(value || "").trim();
    return normalizedValue || "";
  }

  function resolveTransportCurrencyOptions(sourceOptions) {
    const rows = Array.isArray(sourceOptions) ? sourceOptions : [];
    const seenCodes = new Set();

    return rows.reduce(function (resolvedRows, row) {
      const code = normalizeTransportCurrencyCode(row && row.code);
      if (!code || !isValidTransportCurrencyCode(code) || seenCodes.has(code)) {
        return resolvedRows;
      }

      seenCodes.add(code);
      resolvedRows.push({
        code,
        display_label: normalizeTransportCurrencyLabel(row && row.display_label) || null,
      });
      return resolvedRows;
    }, []).sort(function (left, right) {
      return left.code.localeCompare(right.code);
    });
  }

  function formatTransportCurrencyOptionLabel(option) {
    if (!option) {
      return "";
    }
    return option.display_label ? `${option.code} - ${option.display_label}` : option.code;
  }

  function normalizeTransportPriceRateUnit(value, fallbackValue) {
    const normalizedValue = String(value || "").trim().toLowerCase();
    if (!TRANSPORT_PRICE_RATE_UNITS.includes(normalizedValue)) {
      return fallbackValue;
    }
    return normalizedValue;
  }

  function getTransportPriceRateUnitLabel(value, fallbackValue) {
    const normalizedUnit = normalizeTransportPriceRateUnit(value, "");
    if (!normalizedUnit) {
      return fallbackValue || "";
    }

    return {
      hour: translateTransportAiReviewText("settings.perHour", "Per hour"),
      day: translateTransportAiReviewText("settings.perDay", "Per day"),
      week: translateTransportAiReviewText("settings.perWeek", "Per week"),
      month: translateTransportAiReviewText("settings.perMonth", "Per month"),
    }[normalizedUnit] || fallbackValue || normalizedUnit;
  }

  function normalizeTransportPriceSetting(value, fallbackValue) {
    if (value === null || value === undefined) {
      return null;
    }

    const normalizedValue = String(value).trim();
    if (!normalizedValue) {
      return null;
    }

    const parsedValue = Number(normalizedValue);
    if (!Number.isFinite(parsedValue) || parsedValue < 0 || parsedValue > MAX_TRANSPORT_PRICE_VALUE) {
      return fallbackValue;
    }

    return Math.round(parsedValue * 100) / 100;
  }

  function resolveTransportVehiclePriceDefaults(source, fallbackValues) {
    const fallbackPriceDefaults = fallbackValues || DEFAULT_VEHICLE_PRICE_DEFAULTS;
    return {
      carro: normalizeTransportPriceSetting(
        source && (source.carro !== undefined ? source.carro : source.default_car_price),
        fallbackPriceDefaults.carro
      ),
      minivan: normalizeTransportPriceSetting(
        source && (source.minivan !== undefined ? source.minivan : source.default_minivan_price),
        fallbackPriceDefaults.minivan
      ),
      van: normalizeTransportPriceSetting(
        source && (source.van !== undefined ? source.van : source.default_van_price),
        fallbackPriceDefaults.van
      ),
      onibus: normalizeTransportPriceSetting(
        source && (source.onibus !== undefined ? source.onibus : source.default_bus_price),
        fallbackPriceDefaults.onibus
      ),
    };
  }

  function formatTransportPriceInputValue(value) {
    if (value === null || value === undefined || value === "") {
      return "";
    }

    const parsedValue = Number(value);
    if (!Number.isFinite(parsedValue)) {
      return "";
    }

    return parsedValue.toFixed(2);
  }

  function normalizeVehicleToleranceSetting(value, fallbackValue) {
    const parsed = Number.parseInt(String(value), 10);
    if (!Number.isFinite(parsed) || parsed < 0 || parsed > 240) {
      return fallbackValue;
    }
    return parsed;
  }

  function applyTransportVehicleToleranceDefault(nextValue) {
    vehicleDefaultToleranceMinutes = normalizeVehicleToleranceSetting(nextValue, vehicleDefaultToleranceMinutes);
    return vehicleDefaultToleranceMinutes;
  }

  function getDefaultVehicleSeatCount(vehicleType) {
    return vehicleDefaultSeatCount[vehicleType] || DEFAULT_VEHICLE_SEAT_COUNT.carro;
  }

  function getDefaultVehicleToleranceMinutes() {
    return vehicleDefaultToleranceMinutes;
  }

  function getDefaultVehicleFormValues(vehicleType) {
    const normalizedVehicleType = Object.prototype.hasOwnProperty.call(DEFAULT_VEHICLE_SEAT_COUNT, vehicleType)
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

  function normalizeOptionalVehicleFormTextValue(value) {
    const normalizedValue = String(value || '').trim();
    return normalizedValue || null;
  }

  function normalizeOptionalVehicleFormIntegerValue(value) {
    const normalizedValue = String(value || '').trim();
    if (!normalizedValue) {
      return null;
    }

    const parsedValue = Number(normalizedValue);
    return Number.isFinite(parsedValue) ? parsedValue : null;
  }

  function buildVehicleBasePayload(formData) {
    return {
      tipo: normalizeOptionalVehicleFormTextValue(formData.get("tipo")),
      placa: normalizeOptionalVehicleFormTextValue(formData.get("placa")),
      color: normalizeOptionalVehicleFormTextValue(formData.get("color")),
      lugares: normalizeOptionalVehicleFormIntegerValue(formData.get("lugares")),
      tolerance: normalizeOptionalVehicleFormIntegerValue(formData.get("tolerance")),
    };
  }

  function resolveVehicleEditFocusField(vehicle) {
    const resolvedVehicle = vehicle || {};
    const pendingFields = Array.isArray(resolvedVehicle.pending_fields) ? resolvedVehicle.pending_fields : [];
    const pendingField = VEHICLE_BASE_FIELD_ORDER.find(function (fieldName) {
      return pendingFields.includes(fieldName);
    });

    if (pendingField) {
      return pendingField;
    }

    const firstEmptyField = VEHICLE_BASE_FIELD_ORDER.find(function (fieldName) {
      const fieldValue = resolvedVehicle[fieldName];
      return fieldValue === null || fieldValue === undefined || String(fieldValue).trim() === "";
    });

    return firstEmptyField || "tipo";
  }

  function syncVehicleTypeDependentDefaults(vehicleType, formElement) {
    const resolvedForm = resolveVehicleForm(formElement);
    if (!resolvedForm) {
      return;
    }

    const normalizedVehicleType = String(vehicleType || '').trim().toLowerCase();

    if (!Object.prototype.hasOwnProperty.call(DEFAULT_VEHICLE_SEAT_COUNT, normalizedVehicleType)) {
      if (resolvedForm.elements.tipo) {
        resolvedForm.elements.tipo.value = '';
      }
      return;
    }

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
    const payload = Object.assign({
      service_scope: serviceScope,
      service_date: String(serviceDate || ""),
    }, buildVehicleBasePayload(formData));

    if (serviceScope === "extra") {
      payload.service_date = String(formData.get("service_date") || "").trim();
      payload.route_kind = String(formData.get("route_kind") || selectedRouteKind || "home_to_work");
      payload.departure_time = String(formData.get("departure_time") || "").trim();
      return payload;
    }

    if (serviceScope === "weekend") {
      payload.every_saturday = Boolean(formData.get("every_saturday"));
      payload.every_sunday = Boolean(formData.get("every_sunday"));
      return payload;
    }

    payload.every_monday = Boolean(formData.get("every_monday"));
    payload.every_tuesday = Boolean(formData.get("every_tuesday"));
    payload.every_wednesday = Boolean(formData.get("every_wednesday"));
    payload.every_thursday = Boolean(formData.get("every_thursday"));
    payload.every_friday = Boolean(formData.get("every_friday"));

    return payload;
  }

  function resolveVehicleModalOpenState(scope, currentServiceDate) {
    const normalizedScope = normalizeVehicleScope(scope);
    return {
      serviceDateValue: normalizedScope === "extra" ? String(currentServiceDate || "").trim() : "",
      departureTimeValue: "",
      initialFocusField: normalizedScope === "extra" ? "service_date" : null,
      fallbackFocusField: normalizedScope === "extra" ? "departure_time" : null,
    };
  }

  function resolveVehicleCreateValidationError(payload) {
    if (!payload || typeof payload !== "object") {
      return null;
    }

    if (payload.service_scope === "extra" && !String(payload.service_date || "").trim()) {
      return {
        messageKey: "warnings.extraServiceDateRequired",
        focusField: "service_date",
      };
    }

    if (payload.service_scope === "extra" && !String(payload.departure_time || "").trim()) {
      return {
        messageKey: "warnings.extraDepartureRequired",
        focusField: "departure_time",
      };
    }

    if (payload.service_scope === "weekend" && !payload.every_saturday && !payload.every_sunday) {
      return {
        messageKey: "warnings.weekendPersistence",
        focusField: null,
      };
    }

    if (
      payload.service_scope === "regular"
      && !payload.every_monday
      && !payload.every_tuesday
      && !payload.every_wednesday
      && !payload.every_thursday
      && !payload.every_friday
    ) {
      return {
        messageKey: "warnings.regularPersistence",
        focusField: null,
      };
    }

    return null;
  }

  function resolveVehicleSaveReloadDate(payload, fallbackDate) {
    const normalizedFallbackDate = fallbackDate instanceof Date
      ? startOfLocalDay(fallbackDate)
      : parseStoredTransportDate(fallbackDate);
    const resolvedFallbackDate = normalizedFallbackDate || startOfLocalDay(new Date());

    if (!payload || payload.service_scope !== "extra") {
      return resolvedFallbackDate;
    }

    return parseStoredTransportDate(payload.service_date) || resolvedFallbackDate;
  }

  function mapVehicleTypeLabel(value) {
    const normalizedValue = String(value || "").trim();
    const translatedValue = t(`vehicleTypes.${normalizedValue}`);
    return translatedValue === `vehicleTypes.${normalizedValue}` ? normalizedValue : translatedValue;
  }

  function formatVehicleTypeTableValue(value) {
    if (isPendingVehicleField(value)) {
      return getWaitingLabel();
    }

    return String(mapVehicleTypeLabel(value) || value || "").toLowerCase();
  }

  function formatRouteTableValue(routeKind) {
    return getRouteKindLabel(routeKind).toLowerCase();
  }

  function isTemporaryVehiclePlaceholderPlate(value) {
    const normalizedValue = String(value || "").trim().toUpperCase().replace(/\s+/g, " ");
    return VEHICLE_TEMPORARY_PLACEHOLDER_PATTERN.test(normalizedValue);
  }

  function hasVehicleAdministrativeIncompleteness(vehicle) {
    if (!vehicle || typeof vehicle !== "object" || Array.isArray(vehicle)) {
      return false;
    }

    const pendingFields = Array.isArray(vehicle.pending_fields) ? vehicle.pending_fields : [];
    return pendingFields.includes("placa")
      || pendingFields.includes("color")
      || isPendingVehicleField(vehicle.placa)
      || isPendingVehicleField(vehicle.color);
  }

  function shouldUseTemporaryVehicleIcon(vehicle) {
    if (!vehicle || typeof vehicle !== "object" || Array.isArray(vehicle)) {
      return false;
    }

    return isTemporaryVehiclePlaceholderPlate(vehicle.placa)
      || hasVehicleAdministrativeIncompleteness(vehicle);
  }

  function mapVehicleIconPath(value) {
    const vehicle = value && typeof value === "object" && !Array.isArray(value) ? value : null;
    const vehicleType = vehicle ? vehicle.tipo : value;
    const iconPaths = shouldUseTemporaryVehicleIcon(vehicle)
      ? VEHICLE_TEMPORARY_ICON_PATHS
      : VEHICLE_ICON_PATHS;
    return iconPaths[vehicleType] || iconPaths.carro;
  }

  function formatVehicleOccupancyLabel(vehicle, assignedCount) {
    const occupiedSeats = Math.max(0, Number(assignedCount) || 0);
    const totalSeats = isPendingVehicleField(vehicle && vehicle.lugares)
      ? getWaitingLabel()
      : Math.max(0, Number(vehicle && vehicle.lugares) || 0);
    return `${formatPendingVehicleField(vehicle && vehicle.placa)} (${occupiedSeats}/${totalSeats})`;
  }

  function formatVehicleOccupancyCount(vehicle, assignedCount) {
    const occupiedSeats = Math.max(0, Number(assignedCount) || 0);
    const totalSeats = isPendingVehicleField(vehicle && vehicle.lugares)
      ? getWaitingLabel()
      : Math.max(0, Number(vehicle && vehicle.lugares) || 0);
    return `${occupiedSeats}/${totalSeats}`;
  }

  function parseTransportTimeToMinutes(value) {
    const normalizedValue = String(value || "").trim();
    const match = normalizedValue.match(/^(\d{2}):(\d{2})$/);
    if (!match) {
      return null;
    }

    const hours = Number(match[1]);
    const minutes = Number(match[2]);
    if (
      !Number.isInteger(hours)
      || !Number.isInteger(minutes)
      || hours < 0
      || hours > 23
      || minutes < 0
      || minutes > 59
    ) {
      return null;
    }

    return (hours * 60) + minutes;
  }

  function isValidTransportTimeValue(value) {
    return parseTransportTimeToMinutes(value) !== null;
  }

  function normalizeTransportTimeValue(value, fallbackValue) {
    return isValidTransportTimeValue(value) ? String(value || "").trim() : fallbackValue;
  }

  function getTransportCurrentTimestampMs(options) {
    const explicitClientNowMs = Number(options && options.clientNowMs);
    if (Number.isFinite(explicitClientNowMs)) {
      return explicitClientNowMs;
    }

    if (globalScope.Date && typeof globalScope.Date.now === "function") {
      return globalScope.Date.now();
    }

    return new Date().getTime();
  }

  function parseTransportTimezoneOffsetMinutes(value) {
    const normalizedValue = String(value || "").trim();
    if (!normalizedValue) {
      return null;
    }

    if (/z$/i.test(normalizedValue)) {
      return 0;
    }

    const match = normalizedValue.match(/([+-])(\d{2}):(\d{2})$/);
    if (!match) {
      return null;
    }

    const sign = match[1] === "-" ? -1 : 1;
    const hours = Number(match[2]);
    const minutes = Number(match[3]);
    if (!Number.isInteger(hours) || !Number.isInteger(minutes)) {
      return null;
    }

    return sign * ((hours * 60) + minutes);
  }

  function createTransportReferenceClock(serverTimestamp, options) {
    const normalizedTimestamp = String(serverTimestamp || "").trim();
    if (!normalizedTimestamp) {
      return null;
    }

    const offsetMinutes = parseTransportTimezoneOffsetMinutes(normalizedTimestamp);
    const parsedTimestamp = new Date(normalizedTimestamp);
    if (offsetMinutes === null || Number.isNaN(parsedTimestamp.getTime())) {
      return null;
    }

    return {
      serverTimestamp: normalizedTimestamp,
      serverNowMs: parsedTimestamp.getTime(),
      clientNowMs: getTransportCurrentTimestampMs(options),
      offsetMinutes,
    };
  }

  function resolveTransportReferenceNow(clockState, options) {
    if (!clockState || !Number.isFinite(Number(clockState.serverNowMs))) {
      return null;
    }

    const clientNowMs = getTransportCurrentTimestampMs(options);
    const elapsedMs = Math.max(0, clientNowMs - Number(clockState.clientNowMs || 0));
    return Number(clockState.serverNowMs) + elapsedMs;
  }

  function resolveTransportReferenceNowContext(clockState, options) {
    const absoluteNowMs = resolveTransportReferenceNow(clockState, options);
    if (absoluteNowMs === null) {
      return null;
    }

    const offsetMinutes = Number(clockState.offsetMinutes || 0);
    const serverLocalDate = new Date(absoluteNowMs + (offsetMinutes * 60 * 1000));
    if (Number.isNaN(serverLocalDate.getTime())) {
      return null;
    }

    return {
      absoluteNowMs,
      offsetMinutes,
      serverLocalDate,
      currentMinutes: (serverLocalDate.getUTCHours() * 60) + serverLocalDate.getUTCMinutes(),
    };
  }

  function normalizeTransportMinutesOfDay(value) {
    const normalizedValue = Number(value);
    if (!Number.isFinite(normalizedValue)) {
      return null;
    }

    return ((normalizedValue % MINUTES_PER_DAY) + MINUTES_PER_DAY) % MINUTES_PER_DAY;
  }

  function resolveRoutineVehicleReferenceSwitchMinutes(arriveAtWorkTime, workToHomeTime) {
    const arriveAtWorkMinutes = parseTransportTimeToMinutes(arriveAtWorkTime);
    const workToHomeMinutes = parseTransportTimeToMinutes(workToHomeTime);
    if (arriveAtWorkMinutes === null || workToHomeMinutes === null) {
      return null;
    }

    return {
      switchToEtdMinutes: normalizeTransportMinutesOfDay(arriveAtWorkMinutes + 30),
      switchToEtaMinutes: normalizeTransportMinutesOfDay(workToHomeMinutes + 30),
    };
  }

  function isTransportMinuteWithinCircularRange(currentMinutes, startMinutes, endMinutes) {
    if (startMinutes === endMinutes) {
      return false;
    }

    if (startMinutes < endMinutes) {
      return currentMinutes >= startMinutes && currentMinutes < endMinutes;
    }

    return currentMinutes >= startMinutes || currentMinutes < endMinutes;
  }

  function resolveRoutineVehicleReferenceMode(currentMinutes, arriveAtWorkTime, workToHomeTime) {
    const normalizedCurrentMinutes = normalizeTransportMinutesOfDay(currentMinutes);
    const switchMinutes = resolveRoutineVehicleReferenceSwitchMinutes(arriveAtWorkTime, workToHomeTime);
    if (normalizedCurrentMinutes === null || !switchMinutes) {
      return null;
    }

    return isTransportMinuteWithinCircularRange(
      normalizedCurrentMinutes,
      switchMinutes.switchToEtdMinutes,
      switchMinutes.switchToEtaMinutes
    )
      ? "etd"
      : "eta";
  }

  function resolveNextRoutineVehicleReferenceDelayMs(clockState, arriveAtWorkTime, workToHomeTime, options) {
    const nowContext = resolveTransportReferenceNowContext(clockState, options);
    const switchMinutes = resolveRoutineVehicleReferenceSwitchMinutes(arriveAtWorkTime, workToHomeTime);
    if (!nowContext || !switchMinutes) {
      return null;
    }

    const year = nowContext.serverLocalDate.getUTCFullYear();
    const month = nowContext.serverLocalDate.getUTCMonth();
    const day = nowContext.serverLocalDate.getUTCDate();
    const candidateMoments = [switchMinutes.switchToEtdMinutes, switchMinutes.switchToEtaMinutes].map(function (minutes) {
      const hours = Math.floor(minutes / 60);
      const minuteOfHour = minutes % 60;
      let absoluteTargetMs = Date.UTC(year, month, day, hours, minuteOfHour, 0, 0)
        - (nowContext.offsetMinutes * 60 * 1000);
      if (absoluteTargetMs <= nowContext.absoluteNowMs) {
        absoluteTargetMs += MINUTES_PER_DAY * 60 * 1000;
      }
      return absoluteTargetMs;
    });
    const nextSwitchAtMs = Math.min.apply(null, candidateMoments);
    return Math.max(0, nextSwitchAtMs - nowContext.absoluteNowMs);
  }

  function isRoutineVehicleScope(scope) {
    const normalizedScope = String(scope || "").trim();
    return normalizedScope === "regular" || normalizedScope === "weekend";
  }

  function formatRoutineVehicleReferenceLabel(mode, arriveAtWorkTime, workToHomeTime) {
    const normalizedMode = String(mode || "").trim().toLowerCase();
    if (normalizedMode === "eta") {
      const etaTime = normalizeTransportTimeValue(arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME);
      return isValidTransportTimeValue(etaTime)
        ? translateTransportAiReviewText("ai.review.etaLabel", "ETA {time}h", { time: etaTime })
        : "";
    }
    if (normalizedMode === "etd") {
      const etdTime = normalizeTransportTimeValue(workToHomeTime, DEFAULT_WORK_TO_HOME_TIME);
      return isValidTransportTimeValue(etdTime)
        ? translateTransportAiReviewText("ai.review.etdLabel", "ETD {time}h", { time: etdTime })
        : "";
    }
    return "";
  }

  function resolveRoutineVehicleReferenceCurrentMinutes(nowRef, options) {
    const numericNow = Number(nowRef);
    if (Number.isFinite(numericNow)) {
      return normalizeTransportMinutesOfDay(numericNow);
    }

    const nowContext = resolveTransportReferenceNowContext(nowRef, options);
    if (nowContext) {
      return normalizeTransportMinutesOfDay(nowContext.currentMinutes);
    }

    const fallbackDate = new Date(getTransportCurrentTimestampMs(options));
    if (Number.isNaN(fallbackDate.getTime())) {
      return null;
    }

    return normalizeTransportMinutesOfDay((fallbackDate.getHours() * 60) + fallbackDate.getMinutes());
  }

  function getRoutineVehicleReferenceMode(dashboard, arriveAtWorkTime, nowRef, fallbackWorkToHomeTime, options) {
    const normalizedArriveAtWorkTime = normalizeTransportTimeValue(arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME);
    const effectiveWorkToHomeTime = getEffectiveWorkToHomeDepartureTime(dashboard, fallbackWorkToHomeTime);
    const currentMinutes = resolveRoutineVehicleReferenceCurrentMinutes(nowRef, options);
    if (currentMinutes === null) {
      return null;
    }

    return resolveRoutineVehicleReferenceMode(
      currentMinutes,
      normalizedArriveAtWorkTime,
      effectiveWorkToHomeTime
    );
  }

  function getRoutineVehicleReferenceLabel(dashboard, arriveAtWorkTime, nowRef, fallbackWorkToHomeTime, options) {
    const normalizedArriveAtWorkTime = normalizeTransportTimeValue(arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME);
    const effectiveWorkToHomeTime = getEffectiveWorkToHomeDepartureTime(dashboard, fallbackWorkToHomeTime);
    const referenceMode = getRoutineVehicleReferenceMode(
      dashboard,
      arriveAtWorkTime,
      nowRef,
      fallbackWorkToHomeTime,
      options
    );
    if (referenceMode === null) {
      return "";
    }

    return formatRoutineVehicleReferenceLabel(referenceMode, normalizedArriveAtWorkTime, effectiveWorkToHomeTime);
  }

  function getDefaultAiAgentSettings() {
    const def = DEFAULT_AI_AGENT_SETTINGS;
    return {
      earliestBoardingTime: def.earliestBoardingTime,
      arrivalAtWorkTime: def.arrivalAtWorkTime,
      requestKinds: Array.from(DEFAULT_AI_AGENT_REQUEST_KINDS),
      minOccupancy: { ...def.minOccupancy },
    };
  }

  function normalizeTransportAiSettingsProvider(value, fallbackValue) {
    const normalizedValue = String(value || "").trim().toLowerCase();
    if (normalizedValue && Object.prototype.hasOwnProperty.call(TRANSPORT_AI_SETTINGS_PROVIDER_DEFAULTS, normalizedValue)) {
      return normalizedValue;
    }

    const normalizedFallback = String(fallbackValue || DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER).trim().toLowerCase();
    if (Object.prototype.hasOwnProperty.call(TRANSPORT_AI_SETTINGS_PROVIDER_DEFAULTS, normalizedFallback)) {
      return normalizedFallback;
    }

    return DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER;
  }

  function resolveTransportAiSettingsProviderDefaults(provider) {
    return TRANSPORT_AI_SETTINGS_PROVIDER_DEFAULTS[
      normalizeTransportAiSettingsProvider(provider, DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER)
    ];
  }

  function getDefaultTransportAiSettingsDraft() {
    return {
      projectId: null,
      provider: DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER,
      apiKey: "",
      mapsApiKey: "",
    };
  }

  function normalizeTransportAiSettingsProjectId(value, fallbackValue) {
    const parsedProjectId = parsePositiveNumber(value, NaN);
    if (Number.isInteger(parsedProjectId) && parsedProjectId > 0) {
      return parsedProjectId;
    }

    const parsedFallbackId = parsePositiveNumber(fallbackValue, NaN);
    if (Number.isInteger(parsedFallbackId) && parsedFallbackId > 0) {
      return parsedFallbackId;
    }

    return null;
  }

  function normalizeTransportAiSettingsProjectRow(projectRow) {
    if (!projectRow || typeof projectRow !== "object") {
      return null;
    }

    const projectId = normalizeTransportAiSettingsProjectId(projectRow.id, null);
    const projectName = String(projectRow.name || "").trim();
    if (!projectId || !projectName) {
      return null;
    }

    return {
      id: projectId,
      name: projectName,
    };
  }

  function normalizeTransportAiSettingsProjectRows(projectRows) {
    if (!Array.isArray(projectRows)) {
      return [];
    }

    const seenProjectIds = new Set();
    return projectRows.reduce(function (rows, projectRow) {
      const normalizedProjectRow = normalizeTransportAiSettingsProjectRow(projectRow);
      if (!normalizedProjectRow || seenProjectIds.has(normalizedProjectRow.id)) {
        return rows;
      }
      seenProjectIds.add(normalizedProjectRow.id);
      rows.push(normalizedProjectRow);
      return rows;
    }, []);
  }

  function readAiAgentSettingsFieldValue(source, valueKey, inputKey, fallbackValue) {
    if (source && typeof source === "object") {
      if (Object.prototype.hasOwnProperty.call(source, valueKey)) {
        return String(source[valueKey] == null ? "" : source[valueKey]).trim();
      }

      if (Object.prototype.hasOwnProperty.call(source, inputKey) && source[inputKey] && typeof source[inputKey] === "object") {
        return String(source[inputKey].value == null ? "" : source[inputKey].value).trim();
      }
    }

    return String(fallbackValue == null ? "" : fallbackValue).trim();
  }

  function normalizeAiAgentRequestKind(value) {
    const normalizedValue = String(value || "").trim().toLowerCase();
    return DEFAULT_AI_AGENT_REQUEST_KINDS.includes(normalizedValue)
      ? normalizedValue
      : "";
  }

  function readAiAgentRequestKinds(source, fallbackValues) {
    const defaultRequestKinds = Array.isArray(fallbackValues) && fallbackValues.length
      ? fallbackValues
      : getDefaultAiAgentSettings().requestKinds;
    let rawRequestKinds = defaultRequestKinds;

    if (source && typeof source === "object") {
      if (Object.prototype.hasOwnProperty.call(source, "requestKinds")) {
        rawRequestKinds = source.requestKinds;
      } else if (Object.prototype.hasOwnProperty.call(source, "requestKindInputs")) {
        rawRequestKinds = Array.isArray(source.requestKindInputs)
          ? source.requestKindInputs
            .filter(function (inputElement) {
              return inputElement && inputElement.checked;
            })
            .map(function (inputElement) {
              return String(
                inputElement.getAttribute("data-ai-agent-request-kind")
                || inputElement.value
                || ""
              ).trim().toLowerCase();
            })
          : [];
      }
    }

    if (!Array.isArray(rawRequestKinds)) {
      rawRequestKinds = defaultRequestKinds;
    }

    const selectedRequestKinds = new Set();
    rawRequestKinds.forEach(function (requestKind) {
      const normalizedRequestKind = normalizeAiAgentRequestKind(requestKind);
      if (!normalizedRequestKind) {
        return;
      }
      selectedRequestKinds.add(normalizedRequestKind);
    });

    return DEFAULT_AI_AGENT_REQUEST_KINDS.filter(function (requestKind) {
      return selectedRequestKinds.has(requestKind);
    });
  }

  function getAiAgentRequestKindLabel(requestKind) {
    const normalizedRequestKind = normalizeAiAgentRequestKind(requestKind);
    const labelKey = REQUEST_LABEL_KEYS[normalizedRequestKind];
    return labelKey ? t(labelKey) : String(requestKind || "").trim();
  }

  function buildAiAgentSubmittingFeedbackOptions(requestKinds) {
    const normalizedRequestKinds = readAiAgentRequestKinds(
      { requestKinds },
      DEFAULT_AI_AGENT_REQUEST_KINDS
    );
    if (normalizedRequestKinds.length === 1) {
      return {
        key: "ai.agentSettingsSubmittingSingleRequestKind",
        values: {
          requestKind: getAiAgentRequestKindLabel(normalizedRequestKinds[0]),
        },
      };
    }
    return {
      key: "ai.agentSettingsSubmitting",
    };
  }

  function readAiAgentSettingsDraft(source, fallbackValues) {
    const defaults = Object.assign({}, getDefaultAiAgentSettings(), fallbackValues || {});
    const defaultMinOcc = defaults.minOccupancy || DEFAULT_AI_AGENT_SETTINGS.minOccupancy;

    // Read minOccupancy: from source.minOccupancy dict, or from source.minOccInputs DOM map, or fallback
    const minOccupancy = {};
    const vehicleTypes = ["carro", "minivan", "van", "onibus"];
    for (const vt of vehicleTypes) {
      let rawValue = defaultMinOcc[vt];
      if (source && typeof source === "object") {
        if (source.minOccupancy && typeof source.minOccupancy === "object") {
          rawValue = source.minOccupancy[vt] != null ? source.minOccupancy[vt] : rawValue;
        } else if (source.minOccInputs && source.minOccInputs[vt] && typeof source.minOccInputs[vt] === "object") {
          const parsed = parseInt(source.minOccInputs[vt].value, 10);
          rawValue = Number.isFinite(parsed) && parsed >= 1 ? parsed : rawValue;
        }
      }
      const parsed = parseInt(rawValue, 10);
      minOccupancy[vt] = Number.isFinite(parsed) && parsed >= 1 ? parsed : defaultMinOcc[vt];
    }

    return {
      earliestBoardingTime: readAiAgentSettingsFieldValue(
        source,
        "earliestBoardingTime",
        "earliestBoardingInput",
        defaults.earliestBoardingTime
      ),
      arrivalAtWorkTime: readAiAgentSettingsFieldValue(
        source,
        "arrivalAtWorkTime",
        "arrivalAtWorkInput",
        defaults.arrivalAtWorkTime
      ),
      requestKinds: readAiAgentRequestKinds(source, defaults.requestKinds),
      minOccupancy,
    };
  }

  function validateAiAgentSettingsDraft(draft) {
    const normalizedDraft = readAiAgentSettingsDraft(draft, getDefaultAiAgentSettings());
    const earliestBoardingMinutes = parseTransportTimeToMinutes(normalizedDraft.earliestBoardingTime);
    if (earliestBoardingMinutes === null) {
      return {
        ok: false,
        messageKey: "ai.agentSettingsInvalidTimes",
        field: "earliestBoardingTime",
        draft: normalizedDraft,
      };
    }

    const arrivalAtWorkMinutes = parseTransportTimeToMinutes(normalizedDraft.arrivalAtWorkTime);
    if (arrivalAtWorkMinutes === null || earliestBoardingMinutes >= arrivalAtWorkMinutes) {
      return {
        ok: false,
        messageKey: "ai.agentSettingsInvalidTimes",
        field: "arrivalAtWorkTime",
        draft: normalizedDraft,
      };
    }

    if (!normalizedDraft.requestKinds.length) {
      return {
        ok: false,
        messageKey: "ai.agentSettingsNoRequestKindsSelected",
        field: "requestKinds",
        draft: normalizedDraft,
      };
    }

    return {
      ok: true,
      messageKey: "",
      field: "",
      draft: normalizedDraft,
    };
  }

  function readTransportAiSettingsDraft(source, fallbackValues) {
    const defaults = Object.assign({}, getDefaultTransportAiSettingsDraft(), fallbackValues || {});
    return {
      projectId: normalizeTransportAiSettingsProjectId(
        readAiAgentSettingsFieldValue(source, "projectId", "projectInput", defaults.projectId),
        defaults.projectId
      ),
      provider: normalizeTransportAiSettingsProvider(
        readAiAgentSettingsFieldValue(source, "provider", "providerInput", defaults.provider),
        defaults.provider
      ),
      apiKey: readAiAgentSettingsFieldValue(source, "apiKey", "apiKeyInput", defaults.apiKey),
      mapsApiKey: readAiAgentSettingsFieldValue(source, "mapsApiKey", "mapsApiKeyInput", defaults.mapsApiKey),
    };
  }

  function buildTransportAiSettingsProviderNote(provider) {
    const providerDefaults = resolveTransportAiSettingsProviderDefaults(provider);
    return t("ai.settingsProviderNote", {
      provider: providerDefaults.label,
      model: providerDefaults.resolvedModel,
      reasoningEffort: providerDefaults.reasoningEffort,
    });
  }

  function buildTransportAiSettingsUpdatePayload(draft) {
    const normalizedDraft = readTransportAiSettingsDraft(draft, getDefaultTransportAiSettingsDraft());
    const normalizedApiKey = String(normalizedDraft.apiKey || "").trim();
    const normalizedMapsApiKey = String(normalizedDraft.mapsApiKey || "").trim();
    return {
      project_id: normalizedDraft.projectId,
      provider: normalizedDraft.provider,
      api_key: normalizedApiKey || null,
      here_api_key: normalizedMapsApiKey || null,
    };
  }

  function buildTransportAiSettingsUrl(projectId) {
    const normalizedProjectId = normalizeTransportAiSettingsProjectId(projectId, null);
    return `${TRANSPORT_API_PREFIX}/ai/settings?project_id=${encodeURIComponent(normalizedProjectId || "")}`;
  }

  function buildTransportAiDashboardScope(projectRows, projectVisibility, requestKinds) {
    const normalizedRequestKinds = readAiAgentRequestKinds({ requestKinds }, DEFAULT_AI_AGENT_REQUEST_KINDS);
    const normalizedProjectRows = Array.isArray(projectRows) ? projectRows : [];
    if (!normalizedProjectRows.length) {
      return {
        request_kinds: normalizedRequestKinds,
      };
    }

    const normalizedProjectVisibility = projectVisibility && typeof projectVisibility === "object"
      ? projectVisibility
      : {};
    const visibleProjectIds = normalizedProjectRows
      .filter(function (projectRow) {
        return projectRow && projectRow.id !== undefined && projectRow.id !== null && projectRow.name;
      })
      .filter(function (projectRow) {
        return normalizedProjectVisibility[String(projectRow.name).trim()] !== false;
      })
      .map(function (projectRow) {
        return Number.parseInt(String(projectRow.id), 10);
      })
      .filter(function (projectId) {
        return Number.isFinite(projectId) && projectId > 0;
      });

    return {
      project_ids: Array.from(new Set(visibleProjectIds)).sort(function (left, right) {
        return left - right;
      }),
      request_kinds: normalizedRequestKinds,
    };
  }

  function buildTransportAiRequestRouteKinds(routeKind, requestKinds) {
    const normalizedRouteKind = String(routeKind || "home_to_work").trim() || "home_to_work";
    const normalizedRequestKinds = readAiAgentRequestKinds({ requestKinds }, DEFAULT_AI_AGENT_REQUEST_KINDS);
    const routeKinds = {};

    normalizedRequestKinds.forEach(function (requestKind) {
      routeKinds[requestKind] = requestKind === "extra" ? normalizedRouteKind : "home_to_work";
    });

    return routeKinds;
  }

  function buildTransportAiRouteCalculationPayload(serviceDate, routeKind, draft, dashboardScope) {
    const normalizedDraft = readAiAgentSettingsDraft(draft, getDefaultAiAgentSettings());
    const normalizedRouteKind = String(routeKind || "home_to_work").trim() || "home_to_work";
    const resolvedRequestKinds = dashboardScope && typeof dashboardScope === "object" && !Array.isArray(dashboardScope)
      ? readAiAgentRequestKinds(
        { requestKinds: dashboardScope.request_kinds },
        normalizedDraft.requestKinds
      )
      : readAiAgentRequestKinds(
        { requestKinds: normalizedDraft.requestKinds },
        DEFAULT_AI_AGENT_REQUEST_KINDS
      );
    const payload = {
      service_date: String(serviceDate || "").trim(),
      route_kind: normalizedRouteKind,
      earliest_boarding_time: normalizedDraft.earliestBoardingTime,
      arrival_at_work_time: normalizedDraft.arrivalAtWorkTime,
      request_route_kinds: buildTransportAiRequestRouteKinds(normalizedRouteKind, resolvedRequestKinds),
    };

    if (dashboardScope !== undefined) {
      if (dashboardScope && typeof dashboardScope === "object" && !Array.isArray(dashboardScope)) {
        payload.dashboard_scope = Object.assign({}, dashboardScope, {
          request_kinds: resolvedRequestKinds,
        });
      } else {
        payload.dashboard_scope = dashboardScope;
      }
    }

    if (normalizedDraft.minOccupancy && typeof normalizedDraft.minOccupancy === "object") {
      payload.min_occupancy = {
        carro: normalizedDraft.minOccupancy.carro || 1,
        minivan: normalizedDraft.minOccupancy.minivan || 3,
        van: normalizedDraft.minOccupancy.van || 6,
        onibus: normalizedDraft.minOccupancy.onibus || 30,
      };
    }

    return payload;
  }

  function shouldContinuePollingAiRouteRun(runStatus) {
    const normalizedStatus = String(runStatus && runStatus.status || "").trim().toLowerCase();
    return Boolean(
      runStatus
      && runStatus.run_key
      && runStatus.ok !== false
      && !runStatus.suggestion_ready
      && ["requested", "baseline_saved", "passengers_reset", "running"].includes(normalizedStatus)
    );
  }

  function getAiRoutePollingStatusLabel(status) {
    const normalizedStatus = String(status || "").trim().toLowerCase();
    switch (normalizedStatus) {
      case "requested":
      case "baseline_saved":
        return "Preparando dados...";
      case "passengers_reset":
        return "Inicializando c\u00e1lculo...";
      case "running":
        return "Calculando rotas com IA...";
      default:
        return "Aguardando resultado...";
    }
  }

  function hasRenderableTransportAiReview(runStatusResponse) {
    const normalizedResponse = runStatusResponse && typeof runStatusResponse === "object"
      ? runStatusResponse
      : {};
    const normalizedReviewState = String(normalizedResponse.review_state || "").trim().toLowerCase();
    if (normalizedReviewState) {
      return normalizedReviewState === "review_ready" || normalizedReviewState === "review_with_exceptions";
    }
    return Boolean(normalizedResponse.suggestion_ready && normalizedResponse.suggestion);
  }

  function resolveTransportAiStructuredMessage(response) {
    const normalizedResponse = response && typeof response === "object" ? response : {};
    const structuredPayload = extractStructuredTransportApiPayload(normalizedResponse) || normalizedResponse;
    const messageKey = String(structuredPayload.message_key || "").trim();
    if (messageKey) {
      const params = structuredPayload.message_params && typeof structuredPayload.message_params === "object"
        ? structuredPayload.message_params
        : {};
      const translated = t(messageKey, params);
      if (translated && translated !== messageKey) {
        return translated;
      }
    }

    const failureCategory = String(normalizedResponse.failure_category || "").trim().toLowerCase();
    const categoryKeyMap = {
      configuration: "ai.errors.configurationError",
      empty_scope: "ai.errors.emptyScopeError",
      capacity: "ai.errors.capacityError",
      solver: "ai.errors.solverError",
      geocoding: "ai.errors.geocodingError",
      route_provider: "ai.errors.routeProviderError",
      llm_invoke: "ai.errors.llmInvokeError",
      llm_response: "ai.errors.llmResponseError",
      deterministic_validation: "ai.errors.deterministicValidationError",
      unexpected: "ai.errors.unexpectedError",
    };
    const categoryKey = categoryKeyMap[failureCategory];
    if (categoryKey) {
      const categoryMessage = t(categoryKey);
      if (categoryMessage && categoryMessage !== categoryKey) {
        return categoryMessage;
      }
    }

    const structuredMessage = resolveTransportApiStructuredMessage(normalizedResponse);
    if (structuredMessage) {
      return structuredMessage;
    }

    const rawMessage = String(normalizedResponse.message || "").trim();
    return rawMessage || t("ai.routeCalculationFailed");
  }

  function resolveTransportAiBaselineComplement(response) {
    const message = String(response && response.message || "").trim();
    if (!message) {
      return null;
    }
    if (/baseline\s+restored\b/i.test(message) && !/raised|requires/i.test(message)) {
      return t("ai.errors.baselineRestored");
    }
    if (/baseline\s+restore\s+(raised|requires)/i.test(message)) {
      return t("ai.errors.baselineRestoreError");
    }
    return null;
  }

  function getTransportAiSuggestionKey(runStatusResponse) {
    const normalizedResponse = runStatusResponse && typeof runStatusResponse === "object"
      ? runStatusResponse
      : {};
    const topLevelSuggestionKey = String(normalizedResponse.suggestion_key || "").trim();
    if (topLevelSuggestionKey) {
      return topLevelSuggestionKey;
    }

    const suggestion = normalizedResponse.suggestion && typeof normalizedResponse.suggestion === "object"
      ? normalizedResponse.suggestion
      : null;
    return suggestion ? String(suggestion.suggestion_key || "").trim() : "";
  }

  function buildTransportAiSuggestionCommandUrl(apiPrefix, suggestionKey, actionName) {
    const normalizedApiPrefix = String(apiPrefix || "").trim();
    const normalizedSuggestionKey = String(suggestionKey || "").trim();
    const normalizedAction = String(actionName || "").trim().toLowerCase();
    if (!normalizedApiPrefix || !normalizedSuggestionKey || !normalizedAction) {
      return "";
    }

    return `${normalizedApiPrefix}/ai/suggestions/${encodeURIComponent(normalizedSuggestionKey)}/${encodeURIComponent(normalizedAction)}`;
  }

  function buildTransportAiLatestSuggestionUrl(apiPrefix, serviceDate, routeKind) {
    const normalizedApiPrefix = String(apiPrefix || "").trim();
    const normalizedServiceDate = String(serviceDate || "").trim();
    const normalizedRouteKind = String(routeKind || "").trim() || "home_to_work";
    if (!normalizedApiPrefix || !normalizedServiceDate) {
      return "";
    }

    return `${normalizedApiPrefix}/ai/suggestions/latest?service_date=${encodeURIComponent(normalizedServiceDate)}&route_kind=${encodeURIComponent(normalizedRouteKind)}`;
  }

  function shouldRefreshDashboardAfterAiSuggestionCommand(actionName) {
    const normalizedAction = String(actionName || "").trim().toLowerCase();
    return normalizedAction === "cancel" || normalizedAction === "apply";
  }

  function resolveAiChangesCommandState(runStatusResponse, options) {
    const normalizedResponse = runStatusResponse && typeof runStatusResponse === "object"
      ? runStatusResponse
      : {};
    const resolvedOptions = options || {};
    const suggestionKey = getTransportAiSuggestionKey(normalizedResponse);
    const isPending = Boolean(resolvedOptions.isPending);
    const pendingAction = String(resolvedOptions.pendingAction || "").trim().toLowerCase();
    const isAuthenticated = resolvedOptions.isAuthenticated !== false;

    return {
      suggestionKey,
      isPending,
      pendingAction,
      canCancel: Boolean(isAuthenticated && suggestionKey && !isPending && normalizedResponse.can_cancel_restore === true),
      canSave: Boolean(isAuthenticated && suggestionKey && !isPending && normalizedResponse.can_save === true),
      canApply: Boolean(isAuthenticated && suggestionKey && !isPending && normalizedResponse.can_apply === true),
    };
  }

  function getAiChangesActionCopy(actionName) {
    const normalizedAction = String(actionName || "").trim().toLowerCase();
    if (normalizedAction === "cancel") {
      return {
        idleKey: "ai.changesDiscard",
        busyKey: "ai.changesDiscarding",
        successKey: "ai.changesCancelled",
        errorKey: "ai.changesCancelFailed",
      };
    }
    if (normalizedAction === "apply") {
      return {
        idleKey: "ai.changesApply",
        busyKey: "ai.changesApplying",
        successKey: "ai.changesApplied",
        errorKey: "ai.changesApplyFailed",
      };
    }
    return null;
  }

  function formatTransportCurrencyAmount(value, currencyCode, options) {
    const formatOptions = options || {};
    const placeholder = String(formatOptions.placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const parsedValue = Number(value);
    if (!Number.isFinite(parsedValue)) {
      return placeholder;
    }

    const resolvedLanguageCode = resolveLanguageCode(formatOptions.languageCode || getActiveLanguageCode());
    const locale = getLanguageConfig(resolvedLanguageCode).locale || "en-US";
    const normalizedCurrencyCode = normalizeTransportCurrencyCode(currencyCode);
    if (isValidTransportCurrencyCode(normalizedCurrencyCode)) {
      try {
        return new Intl.NumberFormat(locale, {
          style: "currency",
          currency: normalizedCurrencyCode,
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }).format(parsedValue);
      } catch (error) {}
    }

    const numericText = new Intl.NumberFormat(locale, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(parsedValue);
    return normalizedCurrencyCode ? `${numericText} ${normalizedCurrencyCode}` : numericText;
  }

  function formatTransportAiCompactText(value, fallbackValue) {
    const normalizedValue = String(value == null ? "" : value).trim();
    return normalizedValue || fallbackValue;
  }

  function translateTransportAiReviewText(keyPath, fallbackText, values, languageCode) {
    const translatedText = t(keyPath, values, languageCode);
    if (translatedText === keyPath) {
      return interpolateTranslation(fallbackText, values);
    }
    return translatedText;
  }

  function translateTransportAiDefinition(definition, values, languageCode) {
    if (!definition || !definition.keyPath) {
      return "";
    }

    return translateTransportAiReviewText(
      definition.keyPath,
      definition.fallbackText || definition.keyPath,
      values,
      languageCode
    );
  }

  function getTransportAiDynamicLabel(groupName, labelName, values, languageCode) {
    const group = TRANSPORT_AI_DYNAMIC_LABELS[groupName];
    if (!group || !Object.prototype.hasOwnProperty.call(group, labelName)) {
      return "";
    }
    return translateTransportAiDefinition(group[labelName], values, languageCode);
  }

  function getTransportAiCountLabel(unitKey, count, languageCode) {
    const definition = TRANSPORT_AI_COUNT_LABELS[unitKey];
    const normalizedCount = Number.isFinite(Number(count)) ? Math.max(0, Math.round(Number(count))) : 0;
    if (!definition) {
      return "";
    }

    const pluralCategory = normalizedCount === 1 ? "one" : "other";
    return translateTransportAiReviewText(
      `${definition.keyPathPrefix}.${pluralCategory}`,
      pluralCategory === "one" ? definition.fallbackTextOne : definition.fallbackTextOther,
      { count: normalizedCount },
      languageCode
    );
  }

  function formatTransportAiCountText(value, unitKey, fallbackValue) {
    if (!Number.isFinite(Number(value))) {
      return fallbackValue;
    }

    const normalizedCount = Math.max(0, Math.round(Number(value)));
    const label = getTransportAiCountLabel(unitKey, normalizedCount);
    return label ? `${normalizedCount} ${label}` : String(normalizedCount);
  }

  function formatTransportAiIntegerText(value, fallbackValue) {
    if (!Number.isFinite(Number(value))) {
      return fallbackValue;
    }

    return String(Math.max(0, Math.round(Number(value))));
  }

  function formatTransportAiSignedCountDeltaText(currentValue, nextValue, unitKey, fallbackValue) {
    if (!Number.isFinite(Number(currentValue)) || !Number.isFinite(Number(nextValue))) {
      return fallbackValue;
    }

    const normalizedCurrent = Math.max(0, Math.round(Number(currentValue)));
    const normalizedNext = Math.max(0, Math.round(Number(nextValue)));
    const delta = normalizedNext - normalizedCurrent;
    const absoluteDelta = Math.abs(delta);
    const label = getTransportAiCountLabel(unitKey, absoluteDelta);
    const prefix = delta > 0 ? "+" : delta < 0 ? "-" : "";
    return label ? `${prefix}${absoluteDelta} ${label}` : `${prefix}${absoluteDelta}`;
  }

  function formatTransportAiComparison(currentValue, nextValue, fallbackValue) {
    const placeholder = fallbackValue || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const currentText = Number.isFinite(Number(currentValue))
      ? String(Math.max(0, Math.round(Number(currentValue))))
      : placeholder;
    const nextText = Number.isFinite(Number(nextValue))
      ? String(Math.max(0, Math.round(Number(nextValue))))
      : placeholder;
    return `${currentText} -> ${nextText}`;
  }

  function formatTransportAiTimeWindow(earliestValue, arrivalValue, fallbackValue) {
    const placeholder = fallbackValue || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const earliestText = isValidTransportTimeValue(earliestValue) ? String(earliestValue).trim() : placeholder;
    const arrivalText = isValidTransportTimeValue(arrivalValue) ? String(arrivalValue).trim() : placeholder;
    return `${earliestText} -> ${arrivalText}`;
  }

  function humanizeTransportAiStatus(value, fallbackValue) {
    const normalizedValue = String(value || "").trim().toLowerCase();
    if (!normalizedValue) {
      return fallbackValue || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    }

    const translatedStatus = translateTransportAiReviewText(
      `ai.review.statuses.${normalizedValue}`,
      TRANSPORT_AI_STATUS_FALLBACKS[normalizedValue]
        || normalizedValue
          .split(/[_\s-]+/)
          .filter(Boolean)
          .map(function (token) {
            return token.charAt(0).toUpperCase() + token.slice(1);
          })
          .join(" ")
    );
    return translatedStatus
      || normalizedValue
      .split(/[_\s-]+/)
      .filter(Boolean)
      .map(function (token) {
        return token.charAt(0).toUpperCase() + token.slice(1);
      })
      .join(" ");
  }

  function formatTransportAiLabelValue(labelKeyPath, fallbackLabel, valueText, placeholder) {
    const normalizedPlaceholder = String(placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const normalizedValue = formatTransportAiCompactText(valueText, normalizedPlaceholder);
    if (normalizedValue === normalizedPlaceholder) {
      return "";
    }

    return `${translateTransportAiReviewText(labelKeyPath, fallbackLabel)} ${normalizedValue}`;
  }

  function joinTransportAiNoteParts(parts, placeholder) {
    const normalizedPlaceholder = String(placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const noteParts = (Array.isArray(parts) ? parts : []).filter(function (part) {
      const normalizedPart = String(part || "").trim();
      return normalizedPart && normalizedPart !== normalizedPlaceholder;
    });
    return noteParts.length ? noteParts.join(" | ") : normalizedPlaceholder;
  }

  function formatTransportAiMinutesText(value, placeholder) {
    const normalizedPlaceholder = String(placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    if (!Number.isFinite(Number(value))) {
      return normalizedPlaceholder;
    }

    return `${Math.max(0, Math.round(Number(value)))} ${translateTransportAiReviewText("ai.review.units.minuteShort", "min")}`;
  }

  function formatTransportAiRequestReference(requestId, fallbackValue) {
    if (!Number.isFinite(Number(requestId))) {
      return fallbackValue || "";
    }

    return translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.requestReference, {
      id: Math.max(0, Math.round(Number(requestId))),
    });
  }

  function formatTransportAiVehicleIdentifierLabel(vehicleId, fallbackValue) {
    if (!Number.isFinite(Number(vehicleId))) {
      return fallbackValue || "";
    }

    return translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.vehicleId, {
      id: Math.max(0, Math.round(Number(vehicleId))),
    });
  }

  function getTransportAiReviewTargetContract() {
    return TRANSPORT_AI_REVIEW_TARGET_CONTRACT;
  }

  function getTransportAiBidirectionalPlanContract() {
    return TRANSPORT_AI_BIDIRECTIONAL_PLAN_CONTRACT;
  }

  function resolveTransportAiStatusTone(status) {
    const normalizedStatus = String(status || "").trim().toLowerCase();
    if (["proposed", "shown", "saved", "applied"].includes(normalizedStatus)) {
      return "success";
    }
    if (["requested", "baseline_saved", "passengers_reset", "running"].includes(normalizedStatus)) {
      return "info";
    }
    if (["cancelled", "discarded", "expired"].includes(normalizedStatus)) {
      return "warning";
    }
    if (["failed"].includes(normalizedStatus)) {
      return "error";
    }
    return "neutral";
  }

  function normalizeAiChangesBadgeTone(value) {
    const normalizedValue = String(value || "").trim().toLowerCase();
    if (["success", "info", "warning", "error", "neutral"].includes(normalizedValue)) {
      return normalizedValue;
    }
    return resolveTransportAiStatusTone(normalizedValue);
  }

  function resolveAiChangesCostDeltaDetails(deltaValue, currencyCode, options) {
    const detailOptions = options || {};
    const placeholder = String(detailOptions.placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const parsedDelta = Number(deltaValue);
    if (!Number.isFinite(parsedDelta)) {
      return {
        valueText: placeholder,
        label: translateTransportAiReviewText("ai.review.badges.costPending", "Cost Pending"),
        direction: "neutral",
        badgeText: translateTransportAiReviewText("ai.review.badges.costPending", "Cost Pending"),
        tone: "neutral",
      };
    }

    if (parsedDelta < 0) {
      const savingsText = formatTransportCurrencyAmount(Math.abs(parsedDelta), currencyCode, { placeholder });
      return {
        valueText: savingsText,
        label: translateTransportAiReviewText("ai.review.badges.savings", "Savings"),
        direction: "savings",
        badgeText: translateTransportAiReviewText("ai.review.badges.savingsAmount", "Savings {amount}", {
          amount: savingsText,
        }),
        tone: "success",
      };
    }

    if (parsedDelta > 0) {
      const increaseText = formatTransportCurrencyAmount(parsedDelta, currencyCode, { placeholder });
      return {
        valueText: increaseText,
        label: translateTransportAiReviewText("ai.review.badges.increase", "Increase"),
        direction: "increase",
        badgeText: translateTransportAiReviewText("ai.review.badges.increaseAmount", "Increase {amount}", {
          amount: increaseText,
        }),
        tone: "warning",
      };
    }

    const unchangedText = formatTransportCurrencyAmount(0, currencyCode, { placeholder });
    return {
      valueText: unchangedText,
      label: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.noChange),
      direction: "neutral",
      badgeText: translateTransportAiReviewText("ai.review.badges.noCostChange", "No Cost Change"),
      tone: "neutral",
    };
  }

  function resolveTransportAiReviewVehicleRef(action) {
    const normalizedAction = action && typeof action === "object" ? action : {};
    const afterState = readTransportAiVehicleActionState(normalizedAction.after);
    const vehicleRefFromAfter = String(getTransportAiVehicleActionValue(afterState, "vehicle_ref") || "").trim();
    if (vehicleRefFromAfter) {
      return vehicleRefFromAfter;
    }
    if (Number.isFinite(Number(normalizedAction.vehicle_id))) {
      return `existing:${Math.max(0, Math.round(Number(normalizedAction.vehicle_id)))}`;
    }
    const clientVehicleKey = String(normalizedAction.client_vehicle_key || getTransportAiVehicleActionValue(afterState, "client_vehicle_key") || "").trim();
    if (!clientVehicleKey) {
      return "";
    }
    if (clientVehicleKey.startsWith("existing:") || clientVehicleKey.startsWith("new:")) {
      return clientVehicleKey;
    }
    return `new:${clientVehicleKey}`;
  }

  function buildTransportAiReviewActionLookup(vehicleActions) {
    return (Array.isArray(vehicleActions) ? vehicleActions : []).reduce(function (lookup, action) {
      const vehicleRef = resolveTransportAiReviewVehicleRef(action);
      if (!vehicleRef || Object.prototype.hasOwnProperty.call(lookup, vehicleRef)) {
        return lookup;
      }
      lookup[vehicleRef] = action;
      return lookup;
    }, {});
  }

  function resolveTransportAiReviewSensitivityBadge(action) {
    const normalizedAction = action && typeof action === "object" ? action : null;
    if (!normalizedAction) {
      return null;
    }

    const actionType = String(normalizedAction.action_type || "").trim().toLowerCase();
    const beforeState = readTransportAiVehicleActionState(normalizedAction.before);
    const afterState = readTransportAiVehicleActionState(normalizedAction.after);
    const sensitiveFieldNames = ["vehicle_type", "capacity", "plate", "service_scope"];
    const hasSensitiveDiff = actionType === "remove_from_day" || sensitiveFieldNames.some(function (fieldName) {
      const beforeValue = getTransportAiVehicleActionValue(beforeState, fieldName);
      const afterValue = hasTransportAiVehicleActionField(afterState, fieldName)
        ? getTransportAiVehicleActionValue(afterState, fieldName)
        : getTransportAiVehicleActionValue(beforeState, fieldName);
      return String(beforeValue == null ? "" : beforeValue).trim() !== String(afterValue == null ? "" : afterValue).trim();
    });

    if (!hasSensitiveDiff) {
      return null;
    }

    return {
      text: translateTransportAiReviewText("ai.review.badges.sensitive", "Sensitive Change"),
      tone: actionType === "remove_from_day" ? "error" : "warning",
    };
  }

  function dedupeTransportAiReviewBadges(badges) {
    const seenTexts = new Set();
    return (Array.isArray(badges) ? badges : []).filter(function (badge) {
      const badgeText = formatTransportAiCompactText(badge && badge.text, "").trim().toLowerCase();
      if (!badgeText || seenTexts.has(badgeText)) {
        return false;
      }
      seenTexts.add(badgeText);
      return true;
    });
  }

  function buildAiChangesReviewViewModel(runStatusResponse, fallbackCurrencyCode) {
    const placeholder = TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const response = runStatusResponse && typeof runStatusResponse === "object" ? runStatusResponse : {};
    const suggestion = response.suggestion && typeof response.suggestion === "object" ? response.suggestion : {};
    const plan = suggestion.plan && typeof suggestion.plan === "object" ? suggestion.plan : {};
    const costSummary = plan.cost_summary && typeof plan.cost_summary === "object" ? plan.cost_summary : {};
    const priceCurrencyCode = normalizeTransportCurrencyCode(costSummary.price_currency_code || fallbackCurrencyCode);
    const vehicleActions = Array.isArray(plan.vehicle_actions) ? plan.vehicle_actions.filter(Boolean) : [];
    const vehicleReviewTables = Array.isArray(plan.vehicle_review_tables) ? plan.vehicle_review_tables.filter(Boolean) : [];
    const requestIdsWithValidationIssues = (Array.isArray(plan.validation_issues) ? plan.validation_issues : []).reduce(function (requestIds, issue) {
      const requestId = Number(issue && issue.request_id);
      if (Number.isFinite(requestId)) {
        requestIds.add(Math.max(0, Math.round(requestId)));
      }
      return requestIds;
    }, new Set());
    const actionByVehicleRef = buildTransportAiReviewActionLookup(vehicleActions);
    const columns = {
      userName: translateTransportAiReviewText("ai.review.columns.userName", "User Name"),
      userAddress: translateTransportAiReviewText("ai.review.columns.userAddress", "User Address"),
      homeToWorkBoarding: translateTransportAiReviewText("ai.review.columns.homeToWorkBoarding", "Home to Work - Boarding"),
      workToHomeDropoff: translateTransportAiReviewText("ai.review.columns.workToHomeDropoff", "Work to Home - Dropoff"),
    };
    const items = vehicleReviewTables.map(function (table, tableIndex) {
      const normalizedTable = table && typeof table === "object" ? table : {};
      const vehicleRef = formatTransportAiCompactText(normalizedTable.vehicle_ref, "").trim();
      const matchingAction = vehicleRef ? actionByVehicleRef[vehicleRef] : null;
      const afterState = matchingAction ? readTransportAiVehicleActionState(matchingAction.after) : {};
      const capacityValue = parsePositiveNumber(
        getTransportAiVehicleActionValue(afterState, "capacity"),
        null
      );
      const subtitleParts = [];
      if (Number.isFinite(Number(normalizedTable.vehicle_id))) {
        subtitleParts.push(formatTransportAiVehicleIdentifierLabel(normalizedTable.vehicle_id));
      }
      if (vehicleRef) {
        subtitleParts.push(vehicleRef);
      }

      const metaItems = [];
      if (normalizedTable.action_type) {
        metaItems.push({
          label: translateTransportAiReviewText("ai.review.meta.action", "Action"),
          value: getTransportAiVehicleActionLabel(normalizedTable.action_type),
        });
      }
      if (normalizedTable.vehicle_type) {
        metaItems.push({
          label: translateTransportAiReviewText("ai.review.meta.type", "Type"),
          value: getTransportAiVehicleTypeLabel(normalizedTable.vehicle_type),
        });
      }
      if (capacityValue !== null) {
        metaItems.push({
          label: translateTransportAiReviewText("ai.review.meta.seats", "Seats"),
          value: String(Math.max(0, Math.round(capacityValue))),
        });
      }
      if (Number.isFinite(Number(normalizedTable.estimated_cost))) {
        metaItems.push({
          label: translateTransportAiReviewText("ai.review.meta.cost", "Cost"),
          value: formatTransportCurrencyAmount(normalizedTable.estimated_cost, priceCurrencyCode, { placeholder }),
        });
      }
      if (normalizedTable.service_scope) {
        metaItems.push({
          label: translateTransportAiReviewText("ai.review.meta.list", "List"),
          value: getTransportAiVehicleScopeLabel(normalizedTable.service_scope),
        });
      }
      if (normalizedTable.route_kind) {
        metaItems.push({
          label: translateTransportAiReviewText("ai.review.meta.route", "Route"),
          value: getRouteKindLabel(normalizedTable.route_kind),
        });
      }

      const badges = dedupeTransportAiReviewBadges(
        (Array.isArray(normalizedTable.header_badges) ? normalizedTable.header_badges : [])
          .concat(resolveTransportAiReviewSensitivityBadge(matchingAction) || [])
      );

      return {
        vehicleRef: vehicleRef || `review-table-${tableIndex + 1}`,
        titleText: formatTransportAiCompactText(normalizedTable.vehicle_label || normalizedTable.plate || vehicleRef, placeholder),
        subtitleText: subtitleParts.join(" | "),
        rationaleText: String(normalizedTable.action_rationale || "").trim(),
        badges,
        metaItems,
        isSensitive: badges.some(function (badge) {
          return normalizeAiChangesBadgeTone(badge && badge.tone) === "warning"
            || normalizeAiChangesBadgeTone(badge && badge.tone) === "error";
        }),
        rows: (Array.isArray(normalizedTable.rows) ? normalizedTable.rows : []).map(function (row) {
          const normalizedRow = row && typeof row === "object" ? row : {};
          const requestId = Number.isFinite(Number(normalizedRow.request_id))
            ? Math.max(0, Math.round(Number(normalizedRow.request_id)))
            : null;
          const hasHomeToWorkBoarding = String(normalizedRow.home_to_work_boarding || "").trim().length > 0;
          const shouldUseHomeToWorkPlaceholder = !hasHomeToWorkBoarding
            && normalizedRow.home_to_work_boarding_is_placeholder !== false;
          const hasWorkToHomeDropoff = String(normalizedRow.work_to_home_dropoff || "").trim().length > 0;
          const shouldUseWorkToHomePlaceholder = !hasWorkToHomeDropoff && normalizedRow.work_to_home_dropoff_is_placeholder !== false;
          const routeSegmentUnavailableText = translateTransportAiReviewText(
            "ai.review.placeholders.routeSegmentUnavailable",
            "Not planned for this route"
          );
          const shouldUseRouteSegmentPlaceholderForWorkToHome = shouldUseWorkToHomePlaceholder
            && normalizedTable.service_scope === "extra"
            && String(normalizedTable.route_kind || "").trim() === "home_to_work";
          const shouldUseExceptionsPlaceholderForWorkToHome = shouldUseWorkToHomePlaceholder
            && requestId !== null
            && requestIdsWithValidationIssues.has(requestId);
          return {
            requestId,
            userNameText: formatTransportAiCompactText(normalizedRow.user_name, placeholder),
            userAddressText: formatTransportAiCompactText(normalizedRow.user_address, placeholder),
            homeToWorkBoardingText: hasHomeToWorkBoarding
              ? formatTransportAiCompactText(normalizedRow.home_to_work_boarding, placeholder)
              : shouldUseHomeToWorkPlaceholder
                ? routeSegmentUnavailableText
                : placeholder,
            workToHomeDropoffText: hasWorkToHomeDropoff
              ? formatTransportAiCompactText(normalizedRow.work_to_home_dropoff, placeholder)
              : shouldUseWorkToHomePlaceholder
                ? shouldUseRouteSegmentPlaceholderForWorkToHome
                  ? routeSegmentUnavailableText
                  : shouldUseExceptionsPlaceholderForWorkToHome
                    ? translateTransportAiReviewText("ai.review.placeholders.reviewExceptions", "See exceptions")
                    : translateTransportAiReviewText("ai.review.placeholders.workToHomeDropoff", "Unavailable in this plan")
                : placeholder,
            homeToWorkBoardingIsPlaceholder: shouldUseHomeToWorkPlaceholder,
            workToHomeDropoffIsPlaceholder: shouldUseWorkToHomePlaceholder,
          };
        }),
      };
    });

    return {
      columns,
      items,
      emptyMessage: translateTransportAiReviewText(
        "ai.review.empty",
        "Per-vehicle review tables will appear here once the consolidated plan is available."
      ),
    };
  }

  function buildTransportAiAllocatedRequestIdSet(passengerAllocations) {
    return (Array.isArray(passengerAllocations) ? passengerAllocations : []).reduce(function (requestIds, allocation) {
      const requestId = Number(allocation && allocation.request_id);
      if (Number.isFinite(requestId)) {
        requestIds.add(Math.max(0, Math.round(requestId)));
      }
      return requestIds;
    }, new Set());
  }

  function buildAiChangesReviewExceptionsViewModel(runStatusResponse) {
    const placeholder = TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const response = runStatusResponse && typeof runStatusResponse === "object" ? runStatusResponse : {};
    const suggestion = response.suggestion && typeof response.suggestion === "object" ? response.suggestion : {};
    const plan = suggestion.plan && typeof suggestion.plan === "object" ? suggestion.plan : {};
    const passengerAllocations = Array.isArray(plan.passenger_allocations)
      ? plan.passenger_allocations.filter(Boolean)
      : [];
    const validationIssues = Array.isArray(plan.validation_issues)
      ? plan.validation_issues.filter(Boolean)
      : [];
    const allocatedRequestIds = buildTransportAiAllocatedRequestIdSet(passengerAllocations);
    const blockingTitleText = translateTransportAiReviewText(
      "ai.review.exceptions.labels.blockingIssue",
      "Blocking Issue"
    );
    const needsReviewTitleText = translateTransportAiReviewText(
      "ai.review.exceptions.labels.needsReview",
      "Needs Review"
    );
    const notRoutedBadgeText = translateTransportAiReviewText(
      "ai.review.exceptions.badges.notRouted",
      "Not Routed"
    );
    const blockingBadgeText = translateTransportAiReviewText(
      "ai.review.exceptions.badges.blocking",
      "Blocking Issue"
    );
    const needsReviewBadgeText = translateTransportAiReviewText(
      "ai.review.exceptions.badges.needsReview",
      "Needs Review"
    );
    const items = validationIssues.map(function (issue, issueIndex) {
      const normalizedIssue = issue && typeof issue === "object" ? issue : {};
      const requestId = Number.isFinite(Number(normalizedIssue.request_id))
        ? Math.max(0, Math.round(Number(normalizedIssue.request_id)))
        : null;
      const isBlocking = normalizedIssue.blocking !== false;
      const isNotRouted = requestId !== null && !allocatedRequestIds.has(requestId);
      const issueKind = isNotRouted ? "not_routed" : isBlocking ? "blocking" : "review";
      return {
        key: requestId !== null ? `request-${requestId}` : `issue-${issueIndex + 1}`,
        kind: issueKind,
        requestId,
        titleText: requestId !== null
          ? formatTransportAiRequestReference(requestId, placeholder)
          : (isBlocking ? blockingTitleText : needsReviewTitleText),
        subtitleText: formatTransportAiCompactText(normalizedIssue.code, ""),
        messageText: formatTransportAiCompactText(normalizedIssue.message, placeholder),
        badges: [{
          text: isNotRouted ? notRoutedBadgeText : (isBlocking ? blockingBadgeText : needsReviewBadgeText),
          tone: isNotRouted || isBlocking ? "error" : "warning",
        }],
      };
    }).sort(function (leftItem, rightItem) {
      const priorityByKind = {
        not_routed: 0,
        blocking: 1,
        review: 2,
      };
      const leftPriority = Object.prototype.hasOwnProperty.call(priorityByKind, leftItem.kind)
        ? priorityByKind[leftItem.kind]
        : 99;
      const rightPriority = Object.prototype.hasOwnProperty.call(priorityByKind, rightItem.kind)
        ? priorityByKind[rightItem.kind]
        : 99;
      if (leftPriority !== rightPriority) {
        return leftPriority - rightPriority;
      }
      if (leftItem.requestId !== null && rightItem.requestId !== null && leftItem.requestId !== rightItem.requestId) {
        return leftItem.requestId - rightItem.requestId;
      }
      return leftItem.key.localeCompare(rightItem.key);
    });

    return {
      titleText: translateTransportAiReviewText("ai.review.exceptions.title", "Exceptions / Not Routed"),
      summaryText: translateTransportAiReviewText(
        "ai.review.exceptions.summary",
        "Requests without a vehicle assignment and validation issues stay visible here without reopening a passenger-first layout."
      ),
      emptyMessage: translateTransportAiReviewText(
        "ai.review.exceptions.empty",
        "No review exceptions were raised for this plan."
      ),
      items,
    };
  }

  function buildTransportAiManagementByVehicleTypeText(byVehicleType, placeholder) {
    return (Array.isArray(byVehicleType) ? byVehicleType : []).reduce(function (parts, entry) {
      const normalizedEntry = entry && typeof entry === "object" ? entry : {};
      const vehicleTypeText = formatTransportAiCompactText(
        getTransportAiVehicleTypeLabel(normalizedEntry.vehicle_type),
        placeholder
      );
      const totalText = formatTransportAiIntegerText(normalizedEntry.total_count, placeholder);
      if (vehicleTypeText === placeholder && totalText === placeholder) {
        return parts;
      }

      parts.push(`${vehicleTypeText} ${totalText}`);
      return parts;
    }, []).join(" | ");
  }

  function buildAiChangesManagementViewModel(options) {
    const viewOptions = options || {};
    const placeholder = viewOptions.placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const changeSummary = viewOptions.changeSummary && typeof viewOptions.changeSummary === "object"
      ? viewOptions.changeSummary
      : {};
    const byVehicleTypeText = buildTransportAiManagementByVehicleTypeText(changeSummary.by_vehicle_type, placeholder);
    const byVehicleTypeLabel = translateTransportAiReviewText(
      "ai.review.management.notes.byVehicleType",
      "By Vehicle Type"
    );
    const createLabel = translateTransportAiReviewText("ai.review.management.notes.create", "Create");
    const updateLabel = translateTransportAiReviewText("ai.review.management.notes.update", "Update");
    const removeLabel = translateTransportAiReviewText("ai.review.management.notes.remove", "Remove");
    const currencyLabel = translateTransportAiReviewText("ai.review.management.notes.currency", "Currency");
    const rateLabel = translateTransportAiReviewText("ai.review.management.notes.rate", "Rate");
    const routeProviderLabel = translateTransportAiReviewText(
      "ai.review.management.notes.routeProvider",
      "Route Provider"
    );
    const promptVersionLabel = translateTransportAiReviewText(
      "ai.review.management.notes.promptVersion",
      "Prompt Version"
    );
    const modelLabel = translateTransportAiReviewText("ai.review.management.notes.model", "Model");
    const blockingLabel = translateTransportAiReviewText("ai.review.management.notes.blocking", "Blocking");
    const noBlockingIssuesText = translateTransportAiReviewText(
      "ai.review.management.notes.noBlockingIssues",
      "No blocking issues"
    );
    const actionNoteParts = [];
    if (Number.isFinite(Number(changeSummary.create_count)) && Number(changeSummary.create_count) > 0) {
      actionNoteParts.push(`${createLabel} ${formatTransportAiIntegerText(changeSummary.create_count, placeholder)}`);
    }
    if (Number.isFinite(Number(changeSummary.update_count)) && Number(changeSummary.update_count) > 0) {
      actionNoteParts.push(`${updateLabel} ${formatTransportAiIntegerText(changeSummary.update_count, placeholder)}`);
    }
    if (Number.isFinite(Number(changeSummary.remove_from_day_count)) && Number(changeSummary.remove_from_day_count) > 0) {
      actionNoteParts.push(`${removeLabel} ${formatTransportAiIntegerText(changeSummary.remove_from_day_count, placeholder)}`);
    }

    const vehicleNotesText = formatTransportAiLabelValue(
      "ai.review.management.notes.byVehicleType",
      "By Vehicle Type",
      byVehicleTypeText,
      placeholder
    ) || placeholder;
    const actionNotesText = joinTransportAiNoteParts(actionNoteParts, placeholder);
    const routeNotesText = joinTransportAiNoteParts([
      viewOptions.routeKindText,
      viewOptions.serviceDateText,
      formatTransportAiLabelValue(
        "ai.review.management.notes.routeProvider",
        "Route Provider",
        viewOptions.routeProviderText,
        placeholder
      ),
      formatTransportAiLabelValue(
        "ai.review.management.notes.promptVersion",
        "Prompt Version",
        viewOptions.promptVersionText,
        placeholder
      ),
      formatTransportAiLabelValue(
        "ai.review.management.notes.model",
        "Model",
        viewOptions.modelText,
        placeholder
      ),
    ], placeholder);

    return {
      titleText: translateTransportAiReviewText("ai.review.managementTitle", "Management Table"),
      columns: {
        metric: translateTransportAiReviewText("ai.review.management.columns.metric", "Metric"),
        current: translateTransportAiReviewText("ai.review.management.columns.current", "Current"),
        suggested: translateTransportAiReviewText("ai.review.management.columns.suggested", "Suggested"),
        delta: translateTransportAiReviewText("ai.review.management.columns.delta", "Delta"),
        notes: translateTransportAiReviewText("ai.review.management.columns.notes", "Notes"),
      },
      rows: [
        {
          key: "total_cost",
          metricText: translateTransportAiReviewText("ai.review.management.rows.totalCost", "Total Cost"),
          currentText: viewOptions.currentCostText,
          suggestedText: viewOptions.suggestedCostText,
          deltaText: viewOptions.deltaDetails.valueText,
          notesText: joinTransportAiNoteParts([
            viewOptions.deltaDetails.badgeText,
            formatTransportAiLabelValue(
              "ai.review.management.notes.currency",
              "Currency",
              viewOptions.priceCurrencyCode,
              placeholder
            ),
            formatTransportAiLabelValue(
              "ai.review.management.notes.rate",
              "Rate",
              viewOptions.priceRateUnitText,
              placeholder
            ),
          ], placeholder),
        },
        {
          key: "vehicles",
          metricText: translateTransportAiReviewText("ai.review.management.rows.vehicles", "Vehicles"),
          currentText: formatTransportAiIntegerText(viewOptions.currentVehicleCount, placeholder),
          suggestedText: formatTransportAiIntegerText(viewOptions.suggestedVehicleCount, placeholder),
          deltaText: formatTransportAiSignedCountDeltaText(
            viewOptions.currentVehicleCount,
            viewOptions.suggestedVehicleCount,
            "vehicle",
            placeholder
          ),
          notesText: vehicleNotesText,
        },
        {
          key: "actions",
          metricText: translateTransportAiReviewText("ai.review.management.rows.actions", "Total Actions"),
          currentText: placeholder,
          suggestedText: formatTransportAiIntegerText(viewOptions.totalVehicleActions, placeholder),
          deltaText: placeholder,
          notesText: actionNotesText,
        },
        {
          key: "passengers",
          metricText: translateTransportAiReviewText(
            "ai.review.management.rows.passengersAllocated",
            "Passengers Allocated"
          ),
          currentText: placeholder,
          suggestedText: formatTransportAiIntegerText(viewOptions.passengerAllocationCount, placeholder),
          deltaText: placeholder,
          notesText: viewOptions.timeWindowText,
        },
        {
          key: "routes",
          metricText: translateTransportAiReviewText("ai.review.management.rows.routes", "Total Routes"),
          currentText: placeholder,
          suggestedText: formatTransportAiIntegerText(viewOptions.routeCount, placeholder),
          deltaText: placeholder,
          notesText: routeNotesText,
        },
        {
          key: "issues",
          metricText: translateTransportAiReviewText(
            "ai.review.management.rows.issuesAndBlocking",
            "Issues / Blocking"
          ),
          currentText: placeholder,
          suggestedText: formatTransportAiIntegerText(viewOptions.validationIssueCount, placeholder),
          deltaText: formatTransportAiIntegerText(viewOptions.blockingIssueCount, placeholder),
          notesText: Number(viewOptions.blockingIssueCount) > 0
            ? formatTransportAiLabelValue(
              "ai.review.management.notes.blocking",
              "Blocking",
              formatTransportAiIntegerText(viewOptions.blockingIssueCount, placeholder),
              placeholder
            )
            : noBlockingIssuesText,
        },
      ],
    };
  }

  function buildAiChangesSummaryViewModel(runStatusResponse, fallbackCurrencyCode) {
    const placeholder = TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const response = runStatusResponse && typeof runStatusResponse === "object" ? runStatusResponse : {};
    const suggestion = response.suggestion && typeof response.suggestion === "object" ? response.suggestion : {};
    const plan = suggestion.plan && typeof suggestion.plan === "object" ? suggestion.plan : {};
    const audit = suggestion.audit && typeof suggestion.audit === "object" ? suggestion.audit : {};
    const costSummary = plan.cost_summary && typeof plan.cost_summary === "object" ? plan.cost_summary : {};
    const changeSummary = plan.change_summary && typeof plan.change_summary === "object" ? plan.change_summary : {};
    const passengerAllocations = Array.isArray(plan.passenger_allocations) ? plan.passenger_allocations.filter(Boolean) : [];
    const routeItineraries = Array.isArray(plan.route_itineraries) ? plan.route_itineraries.filter(Boolean) : [];
    const extraClusters = Array.isArray(audit.extra_clusters) ? audit.extra_clusters.filter(Boolean) : [];
    const validationIssues = Array.isArray(plan.validation_issues) ? plan.validation_issues.filter(Boolean) : [];
    const blockingIssueCount = validationIssues.reduce(function (count, issue) {
      return count + (issue && issue.blocking !== false ? 1 : 0);
    }, 0);
    const priceCurrencyCode = normalizeTransportCurrencyCode(costSummary.price_currency_code || fallbackCurrencyCode);
    const priceRateUnitText = getTransportPriceRateUnitLabel(costSummary.price_rate_unit, placeholder);
    const currentCostText = formatTransportCurrencyAmount(costSummary.current_total_estimated_cost, priceCurrencyCode, { placeholder });
    const suggestedCostText = formatTransportCurrencyAmount(costSummary.suggested_total_estimated_cost, priceCurrencyCode, { placeholder });
    const deltaDetails = resolveAiChangesCostDeltaDetails(costSummary.estimated_cost_delta, priceCurrencyCode, { placeholder });
    const vehicleComparisonText = formatTransportAiComparison(
      costSummary.current_vehicle_count,
      costSummary.suggested_vehicle_count,
      placeholder
    );
    const allocatedPassengersText = formatTransportAiCountText(passengerAllocations.length, "allocatedPassenger", placeholder);
    const issueCountText = formatTransportAiCountText(validationIssues.length, "issue", placeholder);
    const blockingIssueText = formatTransportAiCountText(blockingIssueCount, "blockingIssue", placeholder);
    const routeCountText = formatTransportAiCountText(routeItineraries.length, "route", placeholder);
    const totalVehicleActionsText = formatTransportAiCountText(changeSummary.total_vehicle_actions, "action", placeholder);
    const createCountText = Number.isFinite(Number(changeSummary.create_count)) && Number(changeSummary.create_count) > 0
      ? formatTransportAiCountText(changeSummary.create_count, "create", placeholder)
      : "";
    const updateCountText = Number.isFinite(Number(changeSummary.update_count)) && Number(changeSummary.update_count) > 0
      ? formatTransportAiCountText(changeSummary.update_count, "update", placeholder)
      : "";
    const removeCountText = Number.isFinite(Number(changeSummary.remove_from_day_count)) && Number(changeSummary.remove_from_day_count) > 0
      ? formatTransportAiCountText(changeSummary.remove_from_day_count, "remove", placeholder)
      : "";
    const currentRouteKind = response.route_kind || plan.route_kind || "";
    const routeKindText = currentRouteKind ? getRouteKindLabel(currentRouteKind) : placeholder;
    const serviceDateText = formatTransportAiCompactText(response.service_date || plan.service_date, placeholder);
    const timeWindowText = formatTransportAiTimeWindow(plan.earliest_boarding_time, plan.arrival_at_work_time, placeholder);
    const routeProviderText = formatTransportAiCompactText(response.route_provider || suggestion.route_provider, placeholder);
    const modelText = formatTransportAiCompactText(response.openai_model || suggestion.openai_model, placeholder);
    const promptVersionText = formatTransportAiCompactText(suggestion.prompt_version || plan.prompt_version, placeholder);
    const planningInputHashText = formatTransportAiCompactText(audit.planning_input_hash, placeholder);
    const extraToleranceNumber = Number(audit.extra_car_tolerance_minutes);
    const extraToleranceText = formatTransportAiMinutesText(extraToleranceNumber, placeholder);
    const extraClusterCountText = formatTransportAiCountText(extraClusters.length, "cluster", placeholder);
    const extraClusterAnchorText = formatTransportAiClusterAnchorSummary(extraClusters, placeholder);
    const extraClustersNote = extraClusters.length
      ? translateTransportAiReviewText("ai.review.anchorsLabel", "Anchors {anchors}", {
        anchors: extraClusterAnchorText,
      })
      : translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.noExtraTemporalClusters);
    const objectiveSummary = formatTransportAiCompactText(
      plan.objective_summary || localizeTransportApiMessage(response.message) || response.message,
      placeholder
    );
    const actionSummarySegments = [totalVehicleActionsText, createCountText, updateCountText, removeCountText].filter(Boolean);
    const actionSummaryText = joinTransportAiNoteParts(actionSummarySegments, placeholder);
    const statusBadges = [];
    if (response.status) {
      statusBadges.push({
        text: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.runStatus, {
          status: humanizeTransportAiStatus(response.status, placeholder),
        }),
        tone: resolveTransportAiStatusTone(response.status),
      });
    }
    if (suggestion.status) {
      statusBadges.push({
        text: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.suggestionStatus, {
          status: humanizeTransportAiStatus(suggestion.status, placeholder),
        }),
        tone: resolveTransportAiStatusTone(suggestion.status),
      });
    }
    if (currentRouteKind) {
      statusBadges.push({
        text: routeKindText,
        tone: "neutral",
      });
    }
    if (validationIssues.length) {
      statusBadges.push({
        text: issueCountText,
        tone: blockingIssueCount ? "warning" : "info",
      });
    }

    const reviewViewModel = buildAiChangesReviewViewModel(runStatusResponse, fallbackCurrencyCode);

    return {
      placeholder,
      objectiveSummary,
      cost: {
        currentText: currentCostText,
        suggestedText: suggestedCostText,
        deltaText: deltaDetails.valueText,
        deltaLabel: deltaDetails.label,
        deltaDirection: deltaDetails.direction,
        deltaBadgeText: deltaDetails.badgeText,
        deltaTone: deltaDetails.tone,
        rateUnitText: priceRateUnitText,
        currencyCode: priceCurrencyCode || placeholder,
      },
      vehicles: {
        comparisonText: vehicleComparisonText,
        actionSummaryText,
      },
      passengers: {
        allocatedText: allocatedPassengersText,
        issueText: issueCountText,
        blockingIssueText,
      },
      window: {
        displayText: timeWindowText,
        routeKindText,
        serviceDateText,
      },
      runtime: {
        routeProviderText,
        modelText,
        promptVersionText,
      },
      audit: {
        planningInputHashText,
        extraToleranceText,
        extraClusterCountText,
        extraClusterAnchorText,
      },
      review: Object.assign({}, reviewViewModel, {
        exceptions: buildAiChangesReviewExceptionsViewModel(runStatusResponse),
        management: buildAiChangesManagementViewModel({
          placeholder,
          changeSummary,
          currentCostText,
          suggestedCostText,
          deltaDetails,
          priceCurrencyCode,
          priceRateUnitText,
          currentVehicleCount: costSummary.current_vehicle_count,
          suggestedVehicleCount: costSummary.suggested_vehicle_count,
          totalVehicleActions: changeSummary.total_vehicle_actions,
          passengerAllocationCount: passengerAllocations.length,
          routeCount: routeItineraries.length,
          validationIssueCount: validationIssues.length,
          blockingIssueCount,
          timeWindowText,
          routeKindText,
          serviceDateText,
          routeProviderText,
          promptVersionText,
          modelText,
        }),
      }),
      statusBadges,
      topCards: [
        {
          label: getTransportAiDynamicLabel("topCards", "suggestedCost"),
          value: suggestedCostText,
          note: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.currentWithRate, {
            current: currentCostText,
            rate: priceRateUnitText,
          }),
          badges: [{ text: deltaDetails.badgeText, tone: deltaDetails.tone }],
        },
        {
          label: getTransportAiDynamicLabel("topCards", "vehicles"),
          value: vehicleComparisonText,
          note: actionSummaryText,
          badges: totalVehicleActionsText !== placeholder
            ? [{ text: totalVehicleActionsText, tone: "info" }]
            : [],
        },
        {
          label: getTransportAiDynamicLabel("topCards", "passengers"),
          value: allocatedPassengersText,
          note: joinTransportAiNoteParts([issueCountText, routeCountText], placeholder),
          badges: validationIssues.length
            ? [{
              text: blockingIssueCount
                ? blockingIssueText
                : translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.ready),
              tone: blockingIssueCount ? "warning" : "success",
            }]
            : [{ text: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.ready), tone: "success" }],
        },
      ],
      detailItems: [
        {
          label: getTransportAiDynamicLabel("detailItems", "currentCost"),
          value: currentCostText,
          note: joinTransportAiNoteParts([
            formatTransportAiLabelValue(
              "ai.review.management.notes.currency",
              "Currency",
              priceCurrencyCode,
              placeholder
            ),
            formatTransportAiLabelValue(
              "ai.review.management.notes.rate",
              "Rate",
              priceRateUnitText,
              placeholder
            ),
          ], placeholder),
        },
        {
          label: getTransportAiDynamicLabel("detailItems", "suggestedCost"),
          value: suggestedCostText,
          note: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.routeCountInPlan, {
            count: routeCountText,
          }),
        },
        {
          label: getTransportAiDynamicLabel("detailItems", "costDelta"),
          value: deltaDetails.valueText,
          note: deltaDetails.badgeText,
          badge: { text: deltaDetails.label, tone: deltaDetails.tone },
        },
        {
          label: getTransportAiDynamicLabel("detailItems", "vehicles"),
          value: vehicleComparisonText,
          note: actionSummaryText,
        },
        {
          label: getTransportAiDynamicLabel("detailItems", "passengers"),
          value: allocatedPassengersText,
          note: joinTransportAiNoteParts([issueCountText, blockingIssueText], placeholder),
        },
        {
          label: getTransportAiDynamicLabel("detailItems", "window"),
          value: timeWindowText,
          note: joinTransportAiNoteParts([routeKindText, serviceDateText], placeholder),
        },
        {
          label: getTransportAiDynamicLabel("detailItems", "extraTolerance"),
          value: extraToleranceText,
          note: joinTransportAiNoteParts([extraClusterCountText, extraClustersNote], placeholder),
        },
        {
          label: getTransportAiDynamicLabel("detailItems", "planningInput"),
          value: planningInputHashText,
          note: extraClusters.length
            ? translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.extraClusters, {
              clusters: extraClusterCountText,
            })
            : translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.noExtraTemporalClusters),
        },
        {
          label: getTransportAiDynamicLabel("detailItems", "routeProvider"),
          value: routeProviderText,
          note: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.prompt, {
            prompt: promptVersionText,
          }),
        },
        {
          label: getTransportAiDynamicLabel("detailItems", "model"),
          value: modelText,
          note: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.suggestionStatus, {
            status: humanizeTransportAiStatus(suggestion.status, placeholder),
          }),
        },
      ],
    };
  }

  function createTransportAiReviewTableElement(reviewItem, columnLabels) {
    const reviewSectionElement = createNode(
      "section",
      `transport-ai-review-vehicle-panel${reviewItem.isSensitive ? " is-sensitive" : ""}`
    );
    reviewSectionElement.dataset.aiReviewVehicleTable = reviewItem.vehicleRef;

    const headElement = createNode("div", "transport-ai-review-vehicle-head");
    const titleRowElement = createNode("div", "transport-ai-review-vehicle-title-row");
    const titleBlockElement = createNode("div", "transport-ai-review-vehicle-title-block");
    titleBlockElement.appendChild(createNode("h4", "transport-ai-review-vehicle-title", reviewItem.titleText));
    if (reviewItem.subtitleText) {
      titleBlockElement.appendChild(createNode("p", "transport-ai-review-vehicle-subtitle", reviewItem.subtitleText));
    }
    titleRowElement.appendChild(titleBlockElement);
    if (reviewItem.badges.length) {
      const badgeRowElement = createNode("div", "transport-ai-changes-badge-row");
      reviewItem.badges.forEach(function (badge) {
        badgeRowElement.appendChild(createAiChangesBadgeElement(badge));
      });
      titleRowElement.appendChild(badgeRowElement);
    }
    headElement.appendChild(titleRowElement);

    if (reviewItem.metaItems.length) {
      const metaGridElement = createNode("dl", "transport-ai-review-vehicle-meta-grid");
      reviewItem.metaItems.forEach(function (metaItem) {
        const metaItemElement = createNode("div", "transport-ai-review-vehicle-meta-item");
        metaItemElement.appendChild(createNode("dt", "transport-ai-review-vehicle-meta-label", metaItem.label));
        metaItemElement.appendChild(createNode("dd", "transport-ai-review-vehicle-meta-value", metaItem.value));
        metaGridElement.appendChild(metaItemElement);
      });
      headElement.appendChild(metaGridElement);
    }

    if (reviewItem.rationaleText) {
      headElement.appendChild(createNode("p", "transport-ai-review-vehicle-rationale", reviewItem.rationaleText));
    }

    reviewSectionElement.appendChild(headElement);

    const tableShellElement = createNode("div", "transport-ai-review-table-shell");
    const tableElement = createNode("table", "transport-ai-review-table");
    tableElement.setAttribute("aria-label", translateTransportAiDefinition(
      TRANSPORT_AI_DYNAMIC_TEXT.reviewTableAria,
      { vehicle: reviewItem.titleText }
    ));
    const tableHeadElement = document.createElement("thead");
    const headRowElement = document.createElement("tr");
    [
      columnLabels.userName,
      columnLabels.userAddress,
      columnLabels.homeToWorkBoarding,
      columnLabels.workToHomeDropoff,
    ].forEach(function (label) {
      headRowElement.appendChild(createNode("th", "transport-ai-review-table-heading", label));
    });
    tableHeadElement.appendChild(headRowElement);

    const tableBodyElement = document.createElement("tbody");
    reviewItem.rows.forEach(function (row) {
      const rowElement = document.createElement("tr");
      rowElement.className = "transport-ai-review-table-row";
      if (row.requestId !== null) {
        rowElement.dataset.aiReviewRequestId = String(row.requestId);
      }

      rowElement.appendChild(createNode("td", "transport-ai-review-table-cell transport-ai-review-table-cell-user", row.userNameText));
      rowElement.appendChild(createNode("td", "transport-ai-review-table-cell transport-ai-review-table-cell-address", row.userAddressText));
      const homeToWorkCellElement = createNode(
        "td",
        `transport-ai-review-table-cell transport-ai-review-table-cell-time${row.homeToWorkBoardingIsPlaceholder ? " is-placeholder" : ""}`,
        row.homeToWorkBoardingText
      );
      rowElement.appendChild(homeToWorkCellElement);
      const workToHomeCellElement = createNode(
        "td",
        `transport-ai-review-table-cell transport-ai-review-table-cell-time${row.workToHomeDropoffIsPlaceholder ? " is-placeholder" : ""}`,
        row.workToHomeDropoffText
      );
      rowElement.appendChild(workToHomeCellElement);
      tableBodyElement.appendChild(rowElement);
    });

    tableElement.appendChild(tableHeadElement);
    tableElement.appendChild(tableBodyElement);
    tableShellElement.appendChild(tableElement);
    reviewSectionElement.appendChild(tableShellElement);
    return reviewSectionElement;
  }

  function createTransportAiManagementTableElement(managementViewModel) {
    const managementSectionElement = createNode("section", "transport-ai-review-management-panel");
    managementSectionElement.dataset.aiReviewManagementTable = "";
    managementSectionElement.appendChild(
      createNode("h4", "transport-ai-review-section-title", managementViewModel.titleText)
    );

    const tableShellElement = createNode(
      "div",
      "transport-ai-review-table-shell transport-ai-review-management-table-shell"
    );
    const tableElement = createNode("table", "transport-ai-review-table transport-ai-review-management-table");
    tableElement.setAttribute("aria-label", managementViewModel.titleText);

    const tableHeadElement = document.createElement("thead");
    const headRowElement = document.createElement("tr");
    [
      managementViewModel.columns.metric,
      managementViewModel.columns.current,
      managementViewModel.columns.suggested,
      managementViewModel.columns.delta,
      managementViewModel.columns.notes,
    ].forEach(function (label) {
      headRowElement.appendChild(createNode("th", "transport-ai-review-table-heading", label));
    });
    tableHeadElement.appendChild(headRowElement);

    const tableBodyElement = document.createElement("tbody");
    managementViewModel.rows.forEach(function (row) {
      const rowElement = document.createElement("tr");
      rowElement.className = "transport-ai-review-table-row transport-ai-review-management-row";
      rowElement.dataset.aiReviewManagementMetric = row.key;

      rowElement.appendChild(
        createNode(
          "td",
          "transport-ai-review-table-cell transport-ai-review-management-cell transport-ai-review-management-cell-metric",
          row.metricText
        )
      );
      rowElement.appendChild(
        createNode(
          "td",
          "transport-ai-review-table-cell transport-ai-review-management-cell transport-ai-review-management-cell-value",
          row.currentText
        )
      );
      rowElement.appendChild(
        createNode(
          "td",
          "transport-ai-review-table-cell transport-ai-review-management-cell transport-ai-review-management-cell-value",
          row.suggestedText
        )
      );
      rowElement.appendChild(
        createNode(
          "td",
          "transport-ai-review-table-cell transport-ai-review-management-cell transport-ai-review-management-cell-value",
          row.deltaText
        )
      );
      rowElement.appendChild(
        createNode(
          "td",
          "transport-ai-review-table-cell transport-ai-review-management-cell transport-ai-review-management-cell-note",
          row.notesText
        )
      );
      tableBodyElement.appendChild(rowElement);
    });

    tableElement.appendChild(tableHeadElement);
    tableElement.appendChild(tableBodyElement);
    tableShellElement.appendChild(tableElement);
    managementSectionElement.appendChild(tableShellElement);
    return managementSectionElement;
  }

  function createTransportAiReviewExceptionsElement(exceptionsViewModel) {
    const exceptionsSectionElement = createNode("section", "transport-ai-review-exceptions-panel");
    exceptionsSectionElement.dataset.aiReviewExceptionsSection = "";
    exceptionsSectionElement.appendChild(
      createNode("h4", "transport-ai-review-section-title", exceptionsViewModel.titleText)
    );
    exceptionsSectionElement.appendChild(
      createNode("p", "transport-ai-review-exceptions-summary", exceptionsViewModel.summaryText)
    );

    if (!exceptionsViewModel.items.length) {
      exceptionsSectionElement.appendChild(
        createNode("p", "transport-ai-changes-empty-state", exceptionsViewModel.emptyMessage)
      );
      return exceptionsSectionElement;
    }

    const listElement = createNode("div", "transport-ai-review-exceptions-list");
    listElement.dataset.aiReviewExceptionsList = "";
    exceptionsViewModel.items.forEach(function (item) {
      const itemElement = createNode(
        "article",
        `transport-ai-review-exception-item is-${item.kind.replace(/_/g, "-")}`
      );
      itemElement.dataset.aiReviewExceptionItem = item.key;
      itemElement.dataset.aiReviewExceptionKind = item.kind;
      if (item.requestId !== null) {
        itemElement.dataset.aiReviewExceptionRequestId = String(item.requestId);
      }

      const headElement = createNode("div", "transport-ai-review-exception-head");
      const titleBlockElement = createNode("div", "transport-ai-review-exception-title-block");
      titleBlockElement.appendChild(
        createNode("h5", "transport-ai-review-exception-title", item.titleText)
      );
      if (item.subtitleText) {
        titleBlockElement.appendChild(
          createNode("p", "transport-ai-review-exception-subtitle", item.subtitleText)
        );
      }
      headElement.appendChild(titleBlockElement);

      if (item.badges.length) {
        const badgeRowElement = createNode("div", "transport-ai-changes-badge-row");
        item.badges.forEach(function (badge) {
          badgeRowElement.appendChild(createAiChangesBadgeElement(badge));
        });
        headElement.appendChild(badgeRowElement);
      }

      itemElement.appendChild(headElement);
      itemElement.appendChild(
        createNode("p", "transport-ai-review-exception-message", item.messageText)
      );
      listElement.appendChild(itemElement);
    });

    exceptionsSectionElement.appendChild(listElement);
    return exceptionsSectionElement;
  }

  function createAiChangesBadgeElement(badge) {
    const badgeConfig = badge && typeof badge === "object" ? badge : {};
    const badgeElement = createNode(
      "span",
      `transport-ai-changes-badge is-${normalizeAiChangesBadgeTone(badgeConfig.tone)}`,
      formatTransportAiCompactText(badgeConfig.text, TRANSPORT_AI_SUMMARY_PLACEHOLDER)
    );
    return badgeElement;
  }

  function getTransportAiVehicleActionLabel(actionType) {
    const normalizedActionType = String(actionType || "").trim().toLowerCase();
    if (Object.prototype.hasOwnProperty.call(TRANSPORT_AI_DYNAMIC_LABELS.actions, normalizedActionType)) {
      return getTransportAiDynamicLabel("actions", normalizedActionType);
    }
    return humanizeTransportAiStatus(normalizedActionType, TRANSPORT_AI_SUMMARY_PLACEHOLDER);
  }

  function resolveTransportAiVehicleActionTone(actionType) {
    const normalizedActionType = String(actionType || "").trim().toLowerCase();
    if (normalizedActionType === "create") {
      return "success";
    }
    if (normalizedActionType === "update") {
      return "warning";
    }
    if (normalizedActionType === "remove_from_day") {
      return "error";
    }
    return "neutral";
  }

  function getTransportAiVehicleTypeLabel(vehicleType) {
    const normalizedVehicleType = String(vehicleType || "").trim().toLowerCase();
    return {
      carro: translateTransportAiReviewText("vehicleTypes.carro", "Car"),
      minivan: translateTransportAiReviewText("vehicleTypes.minivan", "Minivan"),
      van: translateTransportAiReviewText("vehicleTypes.van", "Van"),
      onibus: translateTransportAiReviewText("vehicleTypes.onibus", "Bus"),
    }[normalizedVehicleType] || humanizeTransportAiStatus(normalizedVehicleType, TRANSPORT_AI_SUMMARY_PLACEHOLDER);
  }

  function getTransportAiVehicleScopeLabel(serviceScope) {
    const normalizedScope = String(serviceScope || "").trim().toLowerCase();
    if (Object.prototype.hasOwnProperty.call(TRANSPORT_AI_DYNAMIC_LABELS.lists, normalizedScope)) {
      return getTransportAiDynamicLabel("lists", normalizedScope);
    }
    return humanizeTransportAiStatus(normalizedScope, TRANSPORT_AI_SUMMARY_PLACEHOLDER);
  }

  function readTransportAiVehicleActionState(actionState) {
    return actionState && typeof actionState === "object" ? actionState : {};
  }

  function hasTransportAiVehicleActionField(actionState, fieldName) {
    return Boolean(
      actionState
      && typeof actionState === "object"
      && Object.prototype.hasOwnProperty.call(actionState, fieldName)
    );
  }

  function getTransportAiVehicleActionValue(actionState, fieldName) {
    const normalizedState = readTransportAiVehicleActionState(actionState);
    return hasTransportAiVehicleActionField(normalizedState, fieldName)
      ? normalizedState[fieldName]
      : undefined;
  }

  function formatTransportAiVehicleIdentifier(value, fallbackValue) {
    const normalizedValue = String(value == null ? "" : value).trim();
    return normalizedValue || fallbackValue || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
  }

  function formatTransportAiVehicleFieldText(fieldName, value, options) {
    const formatOptions = options || {};
    const placeholder = String(formatOptions.placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    if (value === undefined || value === null || (typeof value === "string" && !value.trim())) {
      return placeholder;
    }

    if (fieldName === "vehicle_type") {
      return getTransportAiVehicleTypeLabel(value);
    }
    if (fieldName === "service_scope") {
      return getTransportAiVehicleScopeLabel(value);
    }
    if (fieldName === "capacity") {
      return Number.isFinite(Number(value)) ? String(Math.max(0, Math.round(Number(value)))) : placeholder;
    }
    if (fieldName === "estimated_cost") {
      return formatTransportCurrencyAmount(value, formatOptions.currencyCode, { placeholder });
    }
    if (fieldName === "identifier") {
      return formatTransportAiVehicleIdentifier(value, placeholder);
    }

    return formatTransportAiCompactText(value, placeholder);
  }

  function buildTransportAiVehicleFieldDisplay(actionType, beforeText, afterText, options) {
    const displayOptions = options || {};
    const placeholder = String(displayOptions.placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const normalizedBeforeText = formatTransportAiCompactText(beforeText, placeholder);
    const normalizedAfterText = formatTransportAiCompactText(afterText, placeholder);

    if (actionType === "keep") {
      return {
        valueText: normalizedAfterText,
        changed: false,
      };
    }

    if (actionType === "create") {
      const createBeforeText = displayOptions.preserveBeforeForCreate && normalizedBeforeText !== placeholder
        ? normalizedBeforeText
        : placeholder;
      return {
        valueText: `${createBeforeText} -> ${normalizedAfterText}`,
        changed: normalizedAfterText !== placeholder || createBeforeText !== placeholder,
      };
    }

    if (actionType === "remove_from_day") {
      const removedText = String(
        displayOptions.removedText
        || translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.removedFromDay)
      ).trim() || translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.removedFromDay);
      return {
        valueText: `${normalizedBeforeText} -> ${removedText}`,
        changed: true,
      };
    }

    if (normalizedBeforeText !== normalizedAfterText) {
      return {
        valueText: `${normalizedBeforeText} -> ${normalizedAfterText}`,
        changed: true,
      };
    }

    return {
      valueText: normalizedAfterText,
      changed: false,
    };
  }

  function resolveTransportAiVehicleCostPair(action, currencyCode, placeholder) {
    const normalizedAction = action && typeof action === "object" ? action : {};
    const beforeState = readTransportAiVehicleActionState(normalizedAction.before);
    const afterState = readTransportAiVehicleActionState(normalizedAction.after);
    const costPlaceholder = placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const beforeCost = parsePositiveNumber(
      getTransportAiVehicleActionValue(beforeState, "estimated_cost"),
      null
    );
    const afterCostFromState = parsePositiveNumber(
      getTransportAiVehicleActionValue(afterState, "estimated_cost"),
      null
    );
    const costDelta = Number(normalizedAction.cost_delta);
    const hasCostDelta = Number.isFinite(costDelta);
    let resolvedBeforeCost = beforeCost;
    let resolvedAfterCost = afterCostFromState;
    const actionType = String(normalizedAction.action_type || "").trim().toLowerCase();

    if (actionType === "create") {
      if (resolvedBeforeCost === null) {
        resolvedBeforeCost = 0;
      }
      if (resolvedAfterCost === null && hasCostDelta) {
        resolvedAfterCost = Math.max(0, resolvedBeforeCost + costDelta);
      }
    }

    if (actionType === "remove_from_day") {
      if (resolvedAfterCost === null) {
        resolvedAfterCost = 0;
      }
      if (resolvedBeforeCost === null && hasCostDelta) {
        resolvedBeforeCost = Math.max(0, resolvedAfterCost - costDelta);
      }
    }

    if (resolvedBeforeCost === null && resolvedAfterCost !== null && hasCostDelta) {
      resolvedBeforeCost = Math.max(0, resolvedAfterCost - costDelta);
    }
    if (resolvedAfterCost === null && resolvedBeforeCost !== null && hasCostDelta) {
      resolvedAfterCost = Math.max(0, resolvedBeforeCost + costDelta);
    }
    if (resolvedBeforeCost === null && resolvedAfterCost === null && actionType === "keep") {
      resolvedBeforeCost = 0;
      resolvedAfterCost = 0;
    }

    return {
      beforeText: resolvedBeforeCost === null
        ? costPlaceholder
        : formatTransportCurrencyAmount(resolvedBeforeCost, currencyCode, { placeholder: costPlaceholder }),
      afterText: resolvedAfterCost === null
        ? costPlaceholder
        : formatTransportCurrencyAmount(resolvedAfterCost, currencyCode, { placeholder: costPlaceholder }),
      deltaText: hasCostDelta
        ? `${costDelta > 0 ? "+" : costDelta < 0 ? "-" : ""}${formatTransportCurrencyAmount(Math.abs(costDelta), currencyCode, { placeholder: costPlaceholder })}`
        : costPlaceholder,
    };
  }

  function buildAiVehicleChangesViewModel(runStatusResponse, fallbackCurrencyCode) {
    const placeholder = TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const response = runStatusResponse && typeof runStatusResponse === "object" ? runStatusResponse : {};
    const suggestion = response.suggestion && typeof response.suggestion === "object" ? response.suggestion : {};
    const plan = suggestion.plan && typeof suggestion.plan === "object" ? suggestion.plan : {};
    const vehicleActions = Array.isArray(plan.vehicle_actions) ? plan.vehicle_actions.filter(Boolean) : [];
    const routeItineraries = Array.isArray(plan.route_itineraries) ? plan.route_itineraries.filter(Boolean) : [];
    const fallbackRouteKind = String(response.route_kind || plan.route_kind || "").trim().toLowerCase();
    const priceCurrencyCode = normalizeTransportCurrencyCode(
      (plan.cost_summary && plan.cost_summary.price_currency_code)
      || fallbackCurrencyCode
    );
    const items = vehicleActions.map(function (action) {
      const beforeState = readTransportAiVehicleActionState(action.before);
      const afterState = readTransportAiVehicleActionState(action.after);
      const actionType = String(action.action_type || "").trim().toLowerCase();
      const itinerary = findTransportAiItineraryForVehicleAction(action, routeItineraries);
      const actionRouteKind = resolveTransportAiVehicleActionRouteKind(action, itinerary, fallbackRouteKind);
      const beforeRouteKind = hasTransportAiVehicleActionField(beforeState, "route_kind")
        ? String(getTransportAiVehicleActionValue(beforeState, "route_kind") || "").trim().toLowerCase()
        : actionRouteKind;
      const beforeReferenceTime = hasTransportAiVehicleActionField(beforeState, "departure_time")
        ? getTransportAiVehicleActionValue(beforeState, "departure_time")
        : undefined;
      const afterReferenceTime = hasTransportAiVehicleActionField(afterState, "departure_time")
        ? getTransportAiVehicleActionValue(afterState, "departure_time")
        : resolveTransportAiItineraryReferenceTime(itinerary);
      const vehicleId = Number.isFinite(Number(action.vehicle_id)) ? Math.max(0, Math.round(Number(action.vehicle_id))) : null;
      const identifierBefore = formatTransportAiVehicleIdentifier(
        getTransportAiVehicleActionValue(beforeState, "plate")
        || getTransportAiVehicleActionValue(beforeState, "vehicle_ref")
        || getTransportAiVehicleActionValue(beforeState, "client_vehicle_key"),
        placeholder
      );
      const identifierAfter = formatTransportAiVehicleIdentifier(
        getTransportAiVehicleActionValue(afterState, "plate")
        || getTransportAiVehicleActionValue(afterState, "vehicle_ref")
        || getTransportAiVehicleActionValue(afterState, "client_vehicle_key")
        || action.client_vehicle_key,
        placeholder
      );
      const titleText = actionType === "create"
        ? identifierAfter
        : identifierBefore !== placeholder
          ? identifierBefore
          : identifierAfter;
      const titleSuffix = vehicleId
        ? formatTransportAiVehicleIdentifierLabel(vehicleId, action.client_vehicle_key)
        : action.client_vehicle_key;
      const actionTone = resolveTransportAiVehicleActionTone(actionType);
      const costPair = resolveTransportAiVehicleCostPair(action, priceCurrencyCode, placeholder);
      const fieldRows = [
        {
          fieldKey: "type",
          label: getTransportAiDynamicLabel("vehicleFields", "type"),
          ...buildTransportAiVehicleFieldDisplay(
            actionType,
            formatTransportAiVehicleFieldText("vehicle_type", getTransportAiVehicleActionValue(beforeState, "vehicle_type"), { placeholder }),
            formatTransportAiVehicleFieldText(
              "vehicle_type",
              hasTransportAiVehicleActionField(afterState, "vehicle_type")
                ? getTransportAiVehicleActionValue(afterState, "vehicle_type")
                : getTransportAiVehicleActionValue(beforeState, "vehicle_type"),
              { placeholder }
            ),
            { placeholder }
          ),
        },
        {
          fieldKey: "seats",
          label: getTransportAiDynamicLabel("vehicleFields", "seats"),
          ...buildTransportAiVehicleFieldDisplay(
            actionType,
            formatTransportAiVehicleFieldText("capacity", getTransportAiVehicleActionValue(beforeState, "capacity"), { placeholder }),
            formatTransportAiVehicleFieldText(
              "capacity",
              hasTransportAiVehicleActionField(afterState, "capacity")
                ? getTransportAiVehicleActionValue(afterState, "capacity")
                : getTransportAiVehicleActionValue(beforeState, "capacity"),
              { placeholder }
            ),
            { placeholder }
          ),
        },
        {
          fieldKey: "identifier",
          label: getTransportAiDynamicLabel("vehicleFields", "identifier"),
          ...buildTransportAiVehicleFieldDisplay(actionType, identifierBefore, identifierAfter, { placeholder }),
        },
        {
          fieldKey: "list",
          label: getTransportAiDynamicLabel("vehicleFields", "list"),
          ...buildTransportAiVehicleFieldDisplay(
            actionType,
            formatTransportAiVehicleFieldText("service_scope", getTransportAiVehicleActionValue(beforeState, "service_scope") || action.service_scope, { placeholder }),
            formatTransportAiVehicleFieldText(
              "service_scope",
              hasTransportAiVehicleActionField(afterState, "service_scope")
                ? getTransportAiVehicleActionValue(afterState, "service_scope")
                : getTransportAiVehicleActionValue(beforeState, "service_scope") || action.service_scope,
              { placeholder }
            ),
            { placeholder }
          ),
        },
        {
          fieldKey: "cost",
          label: getTransportAiDynamicLabel("vehicleFields", "cost"),
          ...buildTransportAiVehicleFieldDisplay(actionType, costPair.beforeText, costPair.afterText, {
            placeholder,
            preserveBeforeForCreate: true,
          }),
          note: costPair.deltaText !== placeholder
            ? translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.delta, {
              delta: costPair.deltaText,
            })
            : placeholder,
        },
      ];
      if (String(action.service_scope || "").trim().toLowerCase() === "extra") {
        fieldRows.splice(
          4,
          0,
          {
            fieldKey: "route",
            label: getTransportAiDynamicLabel("vehicleFields", "route"),
            ...buildTransportAiVehicleFieldDisplay(
              actionType,
              beforeRouteKind ? getTransportAiRouteKindLabel(beforeRouteKind) : placeholder,
              actionRouteKind ? getTransportAiRouteKindLabel(actionRouteKind) : placeholder,
              { placeholder }
            ),
          },
          {
            fieldKey: "reference",
            label: getTransportAiReferenceFieldLabel("extra", actionRouteKind),
            ...buildTransportAiVehicleFieldDisplay(
              actionType,
              formatTransportAiReferenceValue("extra", beforeRouteKind, beforeReferenceTime, placeholder),
              formatTransportAiReferenceValue("extra", actionRouteKind, afterReferenceTime, placeholder),
              { placeholder }
            ),
            note: buildTransportAiReferenceFieldNote(
              "extra",
              actionRouteKind,
              itinerary && itinerary.projected_arrival_time,
              placeholder
            ),
          }
        );
      }
      const sensitiveChange = actionType === "remove_from_day"
        || fieldRows.some(function (fieldRow) {
          return fieldRow.changed && ["type", "seats", "identifier", "list"].includes(fieldRow.fieldKey);
        });
      const badges = [
        { text: getTransportAiVehicleActionLabel(actionType), tone: actionTone },
        { text: getTransportAiVehicleScopeLabel(action.service_scope), tone: "neutral" },
      ];
      if (sensitiveChange) {
        badges.push({
          text: translateTransportAiReviewText("ai.review.badges.sensitive", "Sensitive Change"),
          tone: actionType === "remove_from_day" ? "error" : "warning",
        });
      }

      return {
        actionKey: formatTransportAiCompactText(action.action_key, placeholder),
        actionType,
        actionLabel: getTransportAiVehicleActionLabel(actionType),
        actionTone,
        isSensitive: sensitiveChange,
        titleText: formatTransportAiCompactText(titleText, placeholder),
        subtitleText: formatTransportAiCompactText(titleSuffix, placeholder),
        rationaleText: formatTransportAiCompactText(action.rationale, placeholder),
        badges,
        fieldRows,
      };
    });

    return {
      placeholder,
      emptyMessage: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.vehicleChangesEmpty),
      items,
    };
  }

  function renderAiVehicleChanges(options) {
    const renderOptions = options || {};
    const viewModel = buildAiVehicleChangesViewModel(
      renderOptions.runStatusResponse,
      renderOptions.fallbackCurrencyCode
    );
    if (typeof document === "undefined") {
      return viewModel;
    }

    const vehiclesPanelElement = renderOptions.vehiclesPanelElement;
    if (!vehiclesPanelElement) {
      return viewModel;
    }

    clearElement(vehiclesPanelElement);
    if (!viewModel.items.length) {
      vehiclesPanelElement.appendChild(createNode("p", "transport-ai-changes-empty-state", viewModel.emptyMessage));
      return viewModel;
    }

    const listElement = createNode("div", "transport-ai-changes-vehicle-list");
    viewModel.items.forEach(function (item) {
      const itemElement = createNode(
        "article",
        `transport-ai-changes-vehicle-item${item.isSensitive ? " is-sensitive" : ""}`
      );
      const headElement = createNode("div", "transport-ai-changes-vehicle-head");
      const titleBlockElement = createNode("div", "transport-ai-changes-vehicle-title-block");
      titleBlockElement.appendChild(createNode("h4", "transport-ai-changes-vehicle-title", item.titleText));
      titleBlockElement.appendChild(createNode("p", "transport-ai-changes-vehicle-ref", item.subtitleText));
      headElement.appendChild(titleBlockElement);

      const badgeRowElement = createNode("div", "transport-ai-changes-badge-row");
      item.badges.forEach(function (badge) {
        badgeRowElement.appendChild(createAiChangesBadgeElement(badge));
      });
      headElement.appendChild(badgeRowElement);
      itemElement.appendChild(headElement);

      const gridElement = createNode("div", "transport-ai-changes-vehicle-grid");
      item.fieldRows.forEach(function (fieldRow) {
        const fieldElement = createNode("div", "transport-ai-changes-vehicle-field");
        fieldElement.appendChild(createNode("span", "transport-ai-changes-summary-label", fieldRow.label));
        fieldElement.appendChild(
          createNode(
            "strong",
            `transport-ai-changes-vehicle-field-value${fieldRow.changed ? " is-changed" : ""}`,
            fieldRow.valueText
          )
        );
        fieldElement.appendChild(createNode("p", "transport-ai-changes-vehicle-field-note", fieldRow.note || item.actionKey));
        gridElement.appendChild(fieldElement);
      });
      itemElement.appendChild(gridElement);
      itemElement.appendChild(createNode("p", "transport-ai-changes-vehicle-rationale", item.rationaleText));
      listElement.appendChild(itemElement);
    });
    vehiclesPanelElement.appendChild(listElement);
    return viewModel;
  }

  function getTransportAiPassengerRequestKindLabel(requestKind) {
    const normalizedRequestKind = String(requestKind || "").trim().toLowerCase();
    return {
      regular: translateTransportAiReviewText("modal.scope.regular", "Regular"),
      weekend: translateTransportAiReviewText("modal.scope.weekend", "Weekend"),
      extra: translateTransportAiReviewText("modal.scope.extra", "Extra"),
    }[normalizedRequestKind] || humanizeTransportAiStatus(normalizedRequestKind, TRANSPORT_AI_SUMMARY_PLACEHOLDER);
  }

  function getTransportAiRouteKindLabel(routeKind) {
    const normalizedRouteKind = String(routeKind || "").trim().toLowerCase();
    return {
      home_to_work: translateTransportAiReviewText("routes.home_to_work", "Home To Work"),
      work_to_home: translateTransportAiReviewText("routes.work_to_home", "Work To Home"),
    }[normalizedRouteKind] || humanizeTransportAiStatus(normalizedRouteKind, TRANSPORT_AI_SUMMARY_PLACEHOLDER);
  }

  function getTransportAiStopTypeLabel(stopType) {
    const normalizedStopType = String(stopType || "").trim().toLowerCase();
    if (Object.prototype.hasOwnProperty.call(TRANSPORT_AI_DYNAMIC_LABELS.stopTypes, normalizedStopType)) {
      return getTransportAiDynamicLabel("stopTypes", normalizedStopType);
    }
    return humanizeTransportAiStatus(normalizedStopType, TRANSPORT_AI_SUMMARY_PLACEHOLDER);
  }

  function resolveTransportAiReferenceTimeFromStops(stops) {
    const stopList = Array.isArray(stops) ? stops : [];
    const timedStop = stopList.find(function (stop) {
      return Boolean(String(stop && stop.scheduled_time || "").trim());
    });
    return timedStop ? String(timedStop.scheduled_time || "").trim() : "";
  }

  function resolveTransportAiItineraryReferenceTime(itinerary) {
    const normalizedItinerary = itinerary && typeof itinerary === "object" ? itinerary : {};
    const serviceScope = String(normalizedItinerary.service_scope || "").trim().toLowerCase();
    const routeKind = String(normalizedItinerary.route_kind || "").trim().toLowerCase();
    if (serviceScope === "extra") {
      if (routeKind === "home_to_work") {
        return String(normalizedItinerary.projected_arrival_time || "").trim();
      }
      if (routeKind === "work_to_home") {
        const firstTimedStop = resolveTransportAiReferenceTimeFromStops(normalizedItinerary.stops);
        return firstTimedStop || String(normalizedItinerary.projected_arrival_time || "").trim();
      }
    }
    return String(normalizedItinerary.projected_arrival_time || "").trim();
  }

  function getTransportAiReferenceFieldLabel(serviceScope, routeKind) {
    const normalizedScope = String(serviceScope || "").trim().toLowerCase();
    const normalizedRouteKind = String(routeKind || "").trim().toLowerCase();
    if (normalizedScope === "extra") {
      if (normalizedRouteKind === "home_to_work") {
        return translateTransportAiReviewText("ai.review.columns.eta", "ETA");
      }
      if (normalizedRouteKind === "work_to_home") {
        return translateTransportAiReviewText("ai.review.columns.etd", "ETD");
      }
      return getTransportAiDynamicLabel("routeFields", "reference");
    }
    return getTransportAiDynamicLabel("routeFields", "arrival");
  }

  function formatTransportAiReferenceValue(serviceScope, routeKind, referenceTime, placeholder) {
    const normalizedPlaceholder = String(placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const normalizedReferenceTime = normalizeTransportTimeValue(referenceTime, "");
    if (!isValidTransportTimeValue(normalizedReferenceTime)) {
      return normalizedPlaceholder;
    }
    if (String(serviceScope || "").trim().toLowerCase() === "extra") {
      return formatExtraVehicleReferenceLabel(routeKind, normalizedReferenceTime) || normalizedPlaceholder;
    }
    return normalizedReferenceTime;
  }

  function buildTransportAiReferenceFieldNote(serviceScope, routeKind, projectedArrivalTime, placeholder) {
    const normalizedScope = String(serviceScope || "").trim().toLowerCase();
    const normalizedRouteKind = String(routeKind || "").trim().toLowerCase();
    const routeKindLabel = getTransportAiRouteKindLabel(normalizedRouteKind);
    const completionText = formatTransportAiCompactText(projectedArrivalTime, placeholder);
    if (normalizedScope === "extra" && normalizedRouteKind === "work_to_home" && completionText !== placeholder) {
      return translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.routeCompletion, {
        route: routeKindLabel,
        time: completionText,
      });
    }
    return routeKindLabel;
  }

  function findTransportAiItineraryForVehicleAction(action, routeItineraries) {
    const normalizedAction = action && typeof action === "object" ? action : {};
    const normalizedRouteItineraries = Array.isArray(routeItineraries) ? routeItineraries : [];
    const clientVehicleKey = String(normalizedAction.client_vehicle_key || "").trim();
    const vehicleId = Number(normalizedAction.vehicle_id);
    return normalizedRouteItineraries.find(function (itinerary) {
      const itineraryVehicleRef = String(itinerary && itinerary.vehicle_ref || "").trim();
      const itineraryClientVehicleKey = String(itinerary && itinerary.client_vehicle_key || "").trim();
      if (clientVehicleKey && (itineraryVehicleRef === clientVehicleKey || itineraryClientVehicleKey === clientVehicleKey)) {
        return true;
      }
      return Number.isFinite(vehicleId) && Number(itinerary && itinerary.vehicle_id) === vehicleId;
    }) || null;
  }

  function resolveTransportAiVehicleActionRouteKind(action, itinerary, fallbackRouteKind) {
    const normalizedAction = action && typeof action === "object" ? action : {};
    const beforeState = readTransportAiVehicleActionState(normalizedAction.before);
    const afterState = readTransportAiVehicleActionState(normalizedAction.after);
    const candidates = [
      getTransportAiVehicleActionValue(afterState, "route_kind"),
      getTransportAiVehicleActionValue(beforeState, "route_kind"),
      itinerary && itinerary.route_kind,
      fallbackRouteKind,
    ];
    for (const candidate of candidates) {
      const normalizedCandidate = String(candidate || "").trim().toLowerCase();
      if (normalizedCandidate === "home_to_work" || normalizedCandidate === "work_to_home") {
        return normalizedCandidate;
      }
    }
    return "";
  }

  function formatTransportAiClusterAnchorSummary(extraClusters, placeholder) {
    const normalizedPlaceholder = String(placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const clusterList = Array.isArray(extraClusters) ? extraClusters : [];
    const anchorTimes = clusterList.map(function (cluster) {
      return formatTransportAiCompactText(cluster && cluster.anchor_requested_time, "");
    }).filter(Boolean);
    if (!anchorTimes.length) {
      return normalizedPlaceholder;
    }
    return anchorTimes.join(", ");
  }

  function buildTransportAiAuditClusterRequestText(requestIds, placeholder) {
    const normalizedPlaceholder = String(placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const requestIdList = Array.isArray(requestIds)
      ? requestIds.filter(function (requestId) {
        return Number.isFinite(Number(requestId)) && Number(requestId) > 0;
      }).map(function (requestId) {
        return `#${Math.max(1, Math.round(Number(requestId)))}`;
      })
      : [];
    if (!requestIdList.length) {
      return normalizedPlaceholder;
    }
    return translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.requestList, {
      requests: requestIdList.join(", "),
    });
  }

  function formatTransportAiDuration(durationSeconds, placeholder) {
    const normalizedPlaceholder = String(placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const totalSeconds = Number(durationSeconds);
    if (!Number.isFinite(totalSeconds) || totalSeconds < 0) {
      return normalizedPlaceholder;
    }

    const totalMinutes = Math.max(0, Math.round(totalSeconds / 60));
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    const hourLabel = translateTransportAiReviewText("ai.review.units.hourShort", "h");
    const minuteLabel = translateTransportAiReviewText("ai.review.units.minuteShort", "min");
    if (hours && minutes) {
      return `${hours}${hourLabel} ${minutes}${minuteLabel === "min" ? "" : " "}${minuteLabel}`;
    }
    if (hours) {
      return `${hours}${hourLabel}`;
    }
    return `${totalMinutes} ${minuteLabel}`;
  }

  function formatTransportAiDistance(distanceMeters, placeholder) {
    const normalizedPlaceholder = String(placeholder || TRANSPORT_AI_SUMMARY_PLACEHOLDER).trim() || TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const totalMeters = Number(distanceMeters);
    if (!Number.isFinite(totalMeters) || totalMeters < 0) {
      return normalizedPlaceholder;
    }

    const kilometerLabel = translateTransportAiReviewText("ai.review.units.kilometerShort", "km");
    const meterLabel = translateTransportAiReviewText("ai.review.units.meterShort", "m");
    if (totalMeters >= 1000) {
      const kilometers = totalMeters / 1000;
      return `${kilometers.toFixed(kilometers >= 10 ? 0 : 1)} ${kilometerLabel}`;
    }
    return `${Math.round(totalMeters)} ${meterLabel}`;
  }

  function buildTransportAiRouteStopTravelText(stop, placeholder) {
    const normalizedStop = stop && typeof stop === "object" ? stop : {};
    const travelParts = [];
    const durationText = formatTransportAiDuration(
      normalizedStop.duration_from_previous_seconds,
      placeholder
    );
    const distanceText = formatTransportAiDistance(
      normalizedStop.distance_from_previous_meters,
      placeholder
    );
    if (durationText !== placeholder) {
      travelParts.push(durationText);
    }
    if (distanceText !== placeholder) {
      travelParts.push(distanceText);
    }
    return travelParts.length
      ? translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.fromPrevious, {
        segments: travelParts.join(" · "),
      })
      : placeholder;
  }

  function buildAiPassengerAllocationsViewModel(runStatusResponse) {
    const placeholder = TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const response = runStatusResponse && typeof runStatusResponse === "object" ? runStatusResponse : {};
    const suggestion = response.suggestion && typeof response.suggestion === "object" ? response.suggestion : {};
    const plan = suggestion.plan && typeof suggestion.plan === "object" ? suggestion.plan : {};
    const passengerAllocations = Array.isArray(plan.passenger_allocations)
      ? plan.passenger_allocations.filter(Boolean)
      : [];
    const routeItineraries = Array.isArray(plan.route_itineraries)
      ? plan.route_itineraries.filter(Boolean)
      : [];
    const validationIssues = Array.isArray(plan.validation_issues)
      ? plan.validation_issues.filter(Boolean)
      : [];
    const itineraryByVehicleRef = routeItineraries.reduce(function (collection, itinerary) {
      const vehicleRef = String(itinerary && itinerary.vehicle_ref || "").trim();
      if (vehicleRef) {
        collection[vehicleRef] = itinerary;
      }
      return collection;
    }, {});
    const allocatedRequestIds = buildTransportAiAllocatedRequestIdSet(passengerAllocations);
    const passengerFieldLabels = {
      project: getTransportAiDynamicLabel("passengerFields", "project"),
      requestKind: getTransportAiDynamicLabel("passengerFields", "requestKind"),
      vehicle: getTransportAiDynamicLabel("passengerFields", "vehicle"),
      pickupOrder: getTransportAiDynamicLabel("passengerFields", "pickupOrder"),
      pickup: getTransportAiDynamicLabel("passengerFields", "pickup"),
      arrival: getTransportAiDynamicLabel("passengerFields", "arrival"),
    };
    const pendingRequestTitle = translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.pendingRequest);
    const needsReviewBadgeText = translateTransportAiReviewText(
      "ai.review.exceptions.badges.needsReview",
      "Needs Review"
    );
    const notRoutedBadgeText = translateTransportAiReviewText(
      "ai.review.exceptions.badges.notRouted",
      "Not Routed"
    );
    const items = passengerAllocations.slice().sort(function (leftItem, rightItem) {
      const leftPickupTime = String(leftItem && leftItem.scheduled_pickup_time || "").trim();
      const rightPickupTime = String(rightItem && rightItem.scheduled_pickup_time || "").trim();
      if (leftPickupTime !== rightPickupTime) {
        return leftPickupTime.localeCompare(rightPickupTime);
      }
      const leftPickupOrder = Number(leftItem && leftItem.pickup_order);
      const rightPickupOrder = Number(rightItem && rightItem.pickup_order);
      if (leftPickupOrder !== rightPickupOrder) {
        return leftPickupOrder - rightPickupOrder;
      }
      return Number(leftItem && leftItem.request_id) - Number(rightItem && rightItem.request_id);
    }).map(function (allocation) {
      const requestId = Number.isFinite(Number(allocation.request_id))
        ? Math.max(0, Math.round(Number(allocation.request_id)))
        : null;
      const itinerary = itineraryByVehicleRef[String(allocation.vehicle_ref || "").trim()] || null;
      const vehicleText = formatTransportAiVehicleIdentifier(
        itinerary && (itinerary.plate || itinerary.client_vehicle_key || itinerary.vehicle_ref)
          ? itinerary.plate || itinerary.client_vehicle_key || itinerary.vehicle_ref
          : allocation.vehicle_ref,
        placeholder
      );
      const projectName = formatTransportAiCompactText(allocation.project_name, placeholder);
      const requestKindLabel = getTransportAiPassengerRequestKindLabel(allocation.request_kind);
      const routeKindLabel = getTransportAiRouteKindLabel(allocation.route_kind);
      const pickupOrder = Number.isFinite(Number(allocation.pickup_order))
        ? Math.max(0, Math.round(Number(allocation.pickup_order))) + 1
        : null;

      return {
        requestId,
        titleText: formatTransportAiCompactText(allocation.nome, placeholder),
        subtitleText: formatTransportAiCompactText(
          [projectName, formatTransportAiCompactText(allocation.chave, "")].filter(Boolean).join(" · "),
          placeholder
        ),
        rationaleText: formatTransportAiCompactText(allocation.rationale, placeholder),
        badges: [
          { text: requestKindLabel, tone: "neutral" },
          { text: routeKindLabel, tone: "info" },
        ],
        fieldRows: [
          {
            label: passengerFieldLabels.project,
            valueText: projectName,
            note: formatTransportAiRequestReference(requestId, placeholder),
          },
          {
            label: passengerFieldLabels.requestKind,
            valueText: requestKindLabel,
            note: routeKindLabel,
          },
          {
            label: passengerFieldLabels.vehicle,
            valueText: vehicleText,
            note: formatTransportAiCompactText(allocation.vehicle_ref, placeholder),
          },
          {
            label: passengerFieldLabels.pickupOrder,
            valueText: pickupOrder === null ? placeholder : `#${pickupOrder}`,
            note: itinerary && itinerary.route_key
              ? formatTransportAiCompactText(itinerary.route_key, placeholder)
              : placeholder,
          },
          {
            label: passengerFieldLabels.pickup,
            valueText: formatTransportAiCompactText(allocation.scheduled_pickup_time, placeholder),
            note: formatTransportAiCompactText(allocation.service_date, placeholder),
          },
          {
            label: passengerFieldLabels.arrival,
            valueText: formatTransportAiCompactText(allocation.projected_arrival_time, placeholder),
            note: itinerary && itinerary.project_name
              ? formatTransportAiCompactText(itinerary.project_name, placeholder)
              : projectName,
          },
        ],
      };
    });

    const unallocatedItems = validationIssues.filter(function (issue) {
      const requestId = Number(issue && issue.request_id);
      return Number.isFinite(requestId) && !allocatedRequestIds.has(Math.max(0, Math.round(requestId)));
    }).map(function (issue) {
      const requestId = Number.isFinite(Number(issue.request_id))
        ? Math.max(0, Math.round(Number(issue.request_id)))
        : null;
      return {
        requestId,
        titleText: formatTransportAiRequestReference(requestId, pendingRequestTitle),
        subtitleText: formatTransportAiCompactText(issue.code, placeholder),
        messageText: formatTransportAiCompactText(issue.message, placeholder),
        badges: [
          {
            text: issue.blocking === false ? needsReviewBadgeText : notRoutedBadgeText,
            tone: issue.blocking === false ? "warning" : "error",
          },
        ],
      };
    });

    return {
      placeholder,
      emptyMessage: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.passengerAllocationsEmpty),
      allocatedTitle: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.allocatedPassengersTitle),
      unallocatedTitle: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.unallocatedPassengersTitle),
      items,
      unallocatedItems,
    };
  }

  function renderAiPassengerAllocations(options) {
    const renderOptions = options || {};
    const viewModel = buildAiPassengerAllocationsViewModel(renderOptions.runStatusResponse);
    if (typeof document === "undefined") {
      return viewModel;
    }

    const passengersPanelElement = renderOptions.passengersPanelElement;
    if (!passengersPanelElement) {
      return viewModel;
    }

    clearElement(passengersPanelElement);
    if (!viewModel.items.length && !viewModel.unallocatedItems.length) {
      passengersPanelElement.appendChild(createNode("p", "transport-ai-changes-empty-state", viewModel.emptyMessage));
      return viewModel;
    }

    const sectionListElement = createNode("div", "transport-ai-changes-passenger-sections");
    if (viewModel.items.length) {
      const allocatedSectionElement = createNode("section", "transport-ai-changes-passenger-section");
      allocatedSectionElement.appendChild(
        createNode("h4", "transport-ai-changes-panel-subtitle", viewModel.allocatedTitle)
      );
      const allocatedListElement = createNode("div", "transport-ai-changes-passenger-list");
      viewModel.items.forEach(function (item) {
        const itemElement = createNode("article", "transport-ai-changes-passenger-item");
        const headElement = createNode("div", "transport-ai-changes-passenger-head");
        const titleBlockElement = createNode("div", "transport-ai-changes-passenger-title-block");
        titleBlockElement.appendChild(createNode("h4", "transport-ai-changes-passenger-title", item.titleText));
        titleBlockElement.appendChild(createNode("p", "transport-ai-changes-passenger-ref", item.subtitleText));
        headElement.appendChild(titleBlockElement);

        const badgeRowElement = createNode("div", "transport-ai-changes-badge-row");
        item.badges.forEach(function (badge) {
          badgeRowElement.appendChild(createAiChangesBadgeElement(badge));
        });
        headElement.appendChild(badgeRowElement);
        itemElement.appendChild(headElement);

        const gridElement = createNode("div", "transport-ai-changes-passenger-grid");
        item.fieldRows.forEach(function (fieldRow) {
          const fieldElement = createNode("div", "transport-ai-changes-passenger-field");
          fieldElement.appendChild(createNode("span", "transport-ai-changes-summary-label", fieldRow.label));
          fieldElement.appendChild(createNode("strong", "transport-ai-changes-passenger-field-value", fieldRow.valueText));
          fieldElement.appendChild(createNode("p", "transport-ai-changes-passenger-field-note", fieldRow.note));
          gridElement.appendChild(fieldElement);
        });
        itemElement.appendChild(gridElement);
        itemElement.appendChild(createNode("p", "transport-ai-changes-passenger-rationale", item.rationaleText));
        allocatedListElement.appendChild(itemElement);
      });
      allocatedSectionElement.appendChild(allocatedListElement);
      sectionListElement.appendChild(allocatedSectionElement);
    }

    if (viewModel.unallocatedItems.length) {
      const unallocatedSectionElement = createNode("section", "transport-ai-changes-passenger-section");
      unallocatedSectionElement.appendChild(
        createNode("h4", "transport-ai-changes-panel-subtitle", viewModel.unallocatedTitle)
      );
      const unallocatedListElement = createNode("div", "transport-ai-changes-passenger-list");
      viewModel.unallocatedItems.forEach(function (item) {
        const itemElement = createNode("article", "transport-ai-changes-passenger-item is-unallocated");
        const headElement = createNode("div", "transport-ai-changes-passenger-head");
        const titleBlockElement = createNode("div", "transport-ai-changes-passenger-title-block");
        titleBlockElement.appendChild(createNode("h4", "transport-ai-changes-passenger-title", item.titleText));
        titleBlockElement.appendChild(createNode("p", "transport-ai-changes-passenger-ref", item.subtitleText));
        headElement.appendChild(titleBlockElement);

        const badgeRowElement = createNode("div", "transport-ai-changes-badge-row");
        item.badges.forEach(function (badge) {
          badgeRowElement.appendChild(createAiChangesBadgeElement(badge));
        });
        headElement.appendChild(badgeRowElement);
        itemElement.appendChild(headElement);
        itemElement.appendChild(createNode("p", "transport-ai-changes-passenger-rationale", item.messageText));
        unallocatedListElement.appendChild(itemElement);
      });
      unallocatedSectionElement.appendChild(unallocatedListElement);
      sectionListElement.appendChild(unallocatedSectionElement);
    }

    passengersPanelElement.appendChild(sectionListElement);
    return viewModel;
  }

  function buildAiRouteItinerariesViewModel(runStatusResponse, fallbackCurrencyCode) {
    const placeholder = TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const response = runStatusResponse && typeof runStatusResponse === "object" ? runStatusResponse : {};
    const suggestion = response.suggestion && typeof response.suggestion === "object" ? response.suggestion : {};
    const plan = suggestion.plan && typeof suggestion.plan === "object" ? suggestion.plan : {};
    const routeItineraries = Array.isArray(plan.route_itineraries)
      ? plan.route_itineraries.filter(Boolean)
      : [];
    const priceCurrencyCode = normalizeTransportCurrencyCode(
      (plan.cost_summary && plan.cost_summary.price_currency_code)
      || fallbackCurrencyCode
    );
    const routeFieldLabels = {
      project: getTransportAiDynamicLabel("routeFields", "project"),
      duration: getTransportAiDynamicLabel("routeFields", "duration"),
      cost: getTransportAiDynamicLabel("routeFields", "cost"),
    };
    const items = routeItineraries.slice().sort(function (leftItem, rightItem) {
      const leftArrival = String(leftItem && leftItem.projected_arrival_time || "").trim();
      const rightArrival = String(rightItem && rightItem.projected_arrival_time || "").trim();
      if (leftArrival !== rightArrival) {
        return leftArrival.localeCompare(rightArrival);
      }
      return String(leftItem && leftItem.route_key || "").localeCompare(String(rightItem && rightItem.route_key || ""));
    }).map(function (itinerary) {
      const vehicleTitle = formatTransportAiVehicleIdentifier(
        itinerary.plate || itinerary.client_vehicle_key || itinerary.vehicle_ref,
        placeholder
      );
      const referenceTime = resolveTransportAiItineraryReferenceTime(itinerary);
      const referenceLabel = getTransportAiReferenceFieldLabel(itinerary.service_scope, itinerary.route_kind);
      const referenceValueText = formatTransportAiReferenceValue(
        itinerary.service_scope,
        itinerary.route_kind,
        referenceTime,
        placeholder
      );
      const referenceNoteText = buildTransportAiReferenceFieldNote(
        itinerary.service_scope,
        itinerary.route_kind,
        itinerary.projected_arrival_time,
        placeholder
      );
      const stops = (Array.isArray(itinerary.stops) ? itinerary.stops : []).slice().sort(function (leftStop, rightStop) {
        return Number(leftStop && leftStop.stop_order) - Number(rightStop && rightStop.stop_order);
      }).map(function (stop) {
        const stopAddress = formatTransportAiCompactText(stop.address, placeholder);
        const stopZipCode = formatTransportAiCompactText(stop.zip_code, placeholder);
        return {
          stopOrder: Number.isFinite(Number(stop.stop_order)) ? Math.max(0, Math.round(Number(stop.stop_order))) : null,
          stopType: String(stop.stop_type || "").trim().toLowerCase(),
          stopTypeLabel: getTransportAiStopTypeLabel(stop.stop_type),
          scheduledTimeText: formatTransportAiCompactText(stop.scheduled_time, placeholder),
          titleText: formatTransportAiCompactText(
            stop.stop_type === "destination" ? stop.project_name : stop.passenger_name,
            placeholder
          ),
          subtitleText: formatTransportAiCompactText(`${stopAddress} · ${stopZipCode}`, placeholder),
          metaText: formatTransportAiCompactText(
            [stop.project_name, stop.country_code].filter(Boolean).join(" · "),
            placeholder
          ),
          travelText: buildTransportAiRouteStopTravelText(stop, placeholder),
          isDestination: String(stop.stop_type || "").trim().toLowerCase() === "destination",
        };
      });

      return {
        routeKey: formatTransportAiCompactText(itinerary.route_key, placeholder),
        titleText: vehicleTitle,
        subtitleText: formatTransportAiCompactText(
          [itinerary.project_name, itinerary.country_name || itinerary.country_code].filter(Boolean).join(" · "),
          placeholder
        ),
        badges: [
          { text: getTransportAiVehicleScopeLabel(itinerary.service_scope), tone: "neutral" },
          { text: getTransportAiVehicleTypeLabel(itinerary.vehicle_type), tone: "info" },
        ],
        fieldRows: [
          {
            label: routeFieldLabels.project,
            valueText: formatTransportAiCompactText(itinerary.project_name, placeholder),
            note: formatTransportAiCompactText(itinerary.partition_key, placeholder),
          },
          {
            label: referenceLabel,
            valueText: referenceValueText,
            note: referenceNoteText,
          },
          {
            label: routeFieldLabels.duration,
            valueText: formatTransportAiDuration(itinerary.total_duration_seconds, placeholder),
            note: formatTransportAiDistance(itinerary.total_distance_meters, placeholder),
          },
          {
            label: routeFieldLabels.cost,
            valueText: formatTransportCurrencyAmount(itinerary.estimated_cost, priceCurrencyCode, { placeholder }),
            note: formatTransportAiCompactText(itinerary.vehicle_ref, placeholder),
          },
        ],
        stopItems: stops,
      };
    });

    return {
      placeholder,
      emptyMessage: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.routeItinerariesEmpty),
      emptyStopsMessage: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.routeStopsEmpty),
      items,
    };
  }

  function renderAiRouteItineraries(options) {
    const renderOptions = options || {};
    const viewModel = buildAiRouteItinerariesViewModel(
      renderOptions.runStatusResponse,
      renderOptions.fallbackCurrencyCode
    );
    if (typeof document === "undefined") {
      return viewModel;
    }

    const routesPanelElement = renderOptions.routesPanelElement;
    if (!routesPanelElement) {
      return viewModel;
    }

    clearElement(routesPanelElement);
    if (!viewModel.items.length) {
      routesPanelElement.appendChild(createNode("p", "transport-ai-changes-empty-state", viewModel.emptyMessage));
      return viewModel;
    }

    const listElement = createNode("div", "transport-ai-changes-route-list");
    viewModel.items.forEach(function (item) {
      const itemElement = createNode("article", "transport-ai-changes-route-item");
      const headElement = createNode("div", "transport-ai-changes-route-head");
      const titleBlockElement = createNode("div", "transport-ai-changes-route-title-block");
      titleBlockElement.appendChild(createNode("h4", "transport-ai-changes-route-title", item.titleText));
      titleBlockElement.appendChild(createNode("p", "transport-ai-changes-route-ref", item.subtitleText));
      headElement.appendChild(titleBlockElement);

      const badgeRowElement = createNode("div", "transport-ai-changes-badge-row");
      item.badges.forEach(function (badge) {
        badgeRowElement.appendChild(createAiChangesBadgeElement(badge));
      });
      headElement.appendChild(badgeRowElement);
      itemElement.appendChild(headElement);

      const gridElement = createNode("div", "transport-ai-changes-route-grid");
      item.fieldRows.forEach(function (fieldRow) {
        const fieldElement = createNode("div", "transport-ai-changes-route-field");
        fieldElement.appendChild(createNode("span", "transport-ai-changes-summary-label", fieldRow.label));
        fieldElement.appendChild(createNode("strong", "transport-ai-changes-route-field-value", fieldRow.valueText));
        fieldElement.appendChild(createNode("p", "transport-ai-changes-route-field-note", fieldRow.note));
        gridElement.appendChild(fieldElement);
      });
      itemElement.appendChild(gridElement);

      if (!item.stopItems.length) {
        itemElement.appendChild(createNode("p", "transport-ai-changes-route-empty-stops", viewModel.emptyStopsMessage));
      } else {
        const stopListElement = createNode("ol", "transport-ai-changes-stop-list");
        item.stopItems.forEach(function (stopItem) {
          const stopElement = createNode(
            "li",
            `transport-ai-changes-stop-item${stopItem.isDestination ? " is-destination" : ""}`
          );
          stopElement.appendChild(createNode(
            "span",
            "transport-ai-changes-stop-order",
            stopItem.stopOrder === null ? "--" : String(stopItem.stopOrder + 1)
          ));

          const contentElement = createNode("div", "transport-ai-changes-stop-content");
          const topElement = createNode("div", "transport-ai-changes-stop-top");
          topElement.appendChild(createNode("strong", "transport-ai-changes-stop-time", stopItem.scheduledTimeText));
          topElement.appendChild(createAiChangesBadgeElement({
            text: stopItem.stopTypeLabel,
            tone: stopItem.isDestination ? "success" : "neutral",
          }));
          contentElement.appendChild(topElement);
          contentElement.appendChild(createNode("h5", "transport-ai-changes-stop-title", stopItem.titleText));
          contentElement.appendChild(createNode("p", "transport-ai-changes-stop-subtitle", stopItem.subtitleText));
          contentElement.appendChild(createNode("p", "transport-ai-changes-stop-meta", stopItem.metaText));
          contentElement.appendChild(createNode("p", "transport-ai-changes-stop-travel", stopItem.travelText));
          stopElement.appendChild(contentElement);
          stopListElement.appendChild(stopElement);
        });
        itemElement.appendChild(stopListElement);
      }

      listElement.appendChild(itemElement);
    });
    routesPanelElement.appendChild(listElement);
    return viewModel;
  }

  function buildAiChangesAuditViewModel(runStatusResponse) {
    const placeholder = TRANSPORT_AI_SUMMARY_PLACEHOLDER;
    const response = runStatusResponse && typeof runStatusResponse === "object" ? runStatusResponse : {};
    const suggestion = response.suggestion && typeof response.suggestion === "object" ? response.suggestion : {};
    const audit = suggestion.audit && typeof suggestion.audit === "object" ? suggestion.audit : {};
    const extraClusters = Array.isArray(audit.extra_clusters) ? audit.extra_clusters.filter(Boolean) : [];
    const extraToleranceNumber = Number(audit.extra_car_tolerance_minutes);
    const extraToleranceText = Number.isFinite(extraToleranceNumber) && extraToleranceNumber >= 0
      ? `${Math.round(extraToleranceNumber)} min`
      : placeholder;
    const planningInputHashText = formatTransportAiCompactText(audit.planning_input_hash, placeholder);
    const promptVersionText = formatTransportAiCompactText(suggestion.prompt_version, placeholder);
    const routeProviderText = formatTransportAiCompactText(response.route_provider || suggestion.route_provider, placeholder);
    const llmProviderText = formatTransportAiCompactText(response.llm_provider, placeholder);
    const modelText = formatTransportAiCompactText(response.openai_model || response.llm_model, placeholder);
    const reasoningText = formatTransportAiCompactText(response.llm_reasoning_effort, placeholder);
    const routeKindText = response.route_kind ? getRouteKindLabel(response.route_kind) : placeholder;
    const auditSummaryLabels = {
      promptVersion: getTransportAiDynamicLabel("auditFields", "promptVersion"),
      routeProvider: getTransportAiDynamicLabel("auditFields", "routeProvider"),
      model: getTransportAiDynamicLabel("auditFields", "model"),
      planningInput: getTransportAiDynamicLabel("auditFields", "planningInput"),
    };
    const clusterItems = extraClusters.map(function (cluster) {
      const requestIds = Array.isArray(cluster.request_ids) ? cluster.request_ids : [];
      const requestCount = Number.isFinite(Number(cluster.request_count)) && Number(cluster.request_count) > 0
        ? Math.max(1, Math.round(Number(cluster.request_count)))
        : requestIds.length;
      const anchorText = formatTransportAiCompactText(cluster.anchor_requested_time, placeholder);
      return {
        titleText: formatTransportAiCompactText(cluster.cluster_key, placeholder),
        subtitleText: formatTransportAiCompactText(cluster.partition_key, placeholder),
        badges: [
          {
            text: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.anchorBadge, {
              time: anchorText === placeholder ? placeholder : `${anchorText}h`,
            }),
            tone: "info",
          },
          {
            text: formatTransportAiCountText(requestCount, "request", placeholder),
            tone: "neutral",
          },
        ],
        windowText: formatTransportAiTimeWindow(
          cluster.earliest_requested_time,
          cluster.latest_requested_time,
          placeholder
        ),
        requestText: buildTransportAiAuditClusterRequestText(requestIds, placeholder),
      };
    });

    return {
      placeholder,
      summaryItems: [
        {
          label: auditSummaryLabels.promptVersion,
          valueText: promptVersionText,
          note: routeKindText,
        },
        {
          label: auditSummaryLabels.routeProvider,
          valueText: routeProviderText,
          note: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.llm, { provider: llmProviderText }),
        },
        {
          label: auditSummaryLabels.model,
          valueText: modelText,
          note: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.reasoning, { effort: reasoningText }),
        },
        {
          label: auditSummaryLabels.planningInput,
          valueText: planningInputHashText,
          note: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.extraTolerance, {
            duration: extraToleranceText,
          }),
        },
      ],
      clusterItems,
      emptyClusterMessage: translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.auditEmptyClusters),
    };
  }

  function renderAiChangesAudit(options) {
    const renderOptions = options || {};
    const viewModel = buildAiChangesAuditViewModel(renderOptions.runStatusResponse);
    if (typeof document === "undefined") {
      return viewModel;
    }

    const auditPanelElement = renderOptions.auditPanelElement;
    if (!auditPanelElement) {
      return viewModel;
    }

    clearElement(auditPanelElement);

    const sectionsElement = createNode("div", "transport-ai-changes-audit-sections");
    const summaryGridElement = createNode("div", "transport-ai-changes-executive-grid");
    viewModel.summaryItems.forEach(function (item) {
      const itemElement = createNode("article", "transport-ai-changes-executive-item");
      itemElement.appendChild(createNode("span", "transport-ai-changes-summary-label", item.label));
      itemElement.appendChild(createNode("strong", "transport-ai-changes-executive-value", item.valueText));
      itemElement.appendChild(createNode("p", "transport-ai-changes-executive-note", item.note));
      summaryGridElement.appendChild(itemElement);
    });
    sectionsElement.appendChild(summaryGridElement);

    const clusterSectionElement = createNode("section", "transport-ai-changes-audit-section");
    clusterSectionElement.appendChild(createNode(
      "h4",
      "transport-ai-changes-panel-subtitle",
      translateTransportAiReviewText("ai.review.extraTemporalClusters", "Extra Temporal Clusters")
    ));
    if (!viewModel.clusterItems.length) {
      clusterSectionElement.appendChild(createNode("p", "transport-ai-changes-empty-state", viewModel.emptyClusterMessage));
    } else {
      const clusterListElement = createNode("div", "transport-ai-changes-audit-cluster-list");
      viewModel.clusterItems.forEach(function (item) {
        const itemElement = createNode("article", "transport-ai-changes-audit-cluster");
        const headElement = createNode("div", "transport-ai-changes-audit-head");
        const titleBlockElement = createNode("div", "transport-ai-changes-route-title-block");
        titleBlockElement.appendChild(createNode("h5", "transport-ai-changes-route-title", item.titleText));
        titleBlockElement.appendChild(createNode("p", "transport-ai-changes-route-ref", item.subtitleText));
        headElement.appendChild(titleBlockElement);
        const badgeRowElement = createNode("div", "transport-ai-changes-badge-row");
        item.badges.forEach(function (badge) {
          badgeRowElement.appendChild(createAiChangesBadgeElement(badge));
        });
        headElement.appendChild(badgeRowElement);
        itemElement.appendChild(headElement);
        itemElement.appendChild(createNode(
          "p",
          "transport-ai-changes-audit-meta",
          translateTransportAiDefinition(TRANSPORT_AI_DYNAMIC_TEXT.window, { window: item.windowText })
        ));
        itemElement.appendChild(createNode("p", "transport-ai-changes-audit-meta", item.requestText));
        clusterListElement.appendChild(itemElement);
      });
      clusterSectionElement.appendChild(clusterListElement);
    }
    sectionsElement.appendChild(clusterSectionElement);

    auditPanelElement.appendChild(sectionsElement);
    return viewModel;
  }

  function renderAiChangesSummary(options) {
    const renderOptions = options || {};
    const viewModel = buildAiChangesSummaryViewModel(
      renderOptions.runStatusResponse,
      renderOptions.fallbackCurrencyCode
    );
    if (typeof document === "undefined") {
      return viewModel;
    }

    const summaryGridElement = renderOptions.summaryGridElement;
    const summaryPanelElement = renderOptions.summaryPanelElement;

    if (summaryGridElement) {
      clearElement(summaryGridElement);
      summaryGridElement.hidden = true;
    }

    if (summaryPanelElement) {
      clearElement(summaryPanelElement);
      summaryPanelElement.appendChild(createNode("p", "transport-ai-changes-objective-summary", viewModel.objectiveSummary));

      if (viewModel.statusBadges.length) {
        const badgeRowElement = createNode("div", "transport-ai-changes-badge-row");
        viewModel.statusBadges.forEach(function (badge) {
          badgeRowElement.appendChild(createAiChangesBadgeElement(badge));
        });
        summaryPanelElement.appendChild(badgeRowElement);
      }

      const reviewWorkspaceElement = createNode("div", "transport-ai-review-workspace");
      reviewWorkspaceElement.dataset.aiReviewWorkspace = "primary";

      const vehicleTableListElement = createNode("div", "transport-ai-review-vehicle-table-list");
      vehicleTableListElement.dataset.aiReviewVehicleTableList = "";
      if (!viewModel.review.items.length) {
        vehicleTableListElement.appendChild(createNode("p", "transport-ai-changes-empty-state", viewModel.review.emptyMessage));
      } else {
        viewModel.review.items.forEach(function (reviewItem) {
          vehicleTableListElement.appendChild(createTransportAiReviewTableElement(reviewItem, viewModel.review.columns));
        });
      }
      reviewWorkspaceElement.appendChild(vehicleTableListElement);

      if (viewModel.review.exceptions && viewModel.review.exceptions.items.length) {
        reviewWorkspaceElement.appendChild(createTransportAiReviewExceptionsElement(viewModel.review.exceptions));
      }

      reviewWorkspaceElement.appendChild(createTransportAiManagementTableElement(viewModel.review.management));
      summaryPanelElement.appendChild(reviewWorkspaceElement);
    }

    return viewModel;
  }

  function getEffectiveWorkToHomeDepartureTime(dashboard, fallbackTime) {
    const dashboardTime = String(dashboard && dashboard.work_to_home_departure_time || "").trim();
    if (isValidTransportTimeValue(dashboardTime)) {
      return dashboardTime;
    }

    return normalizeTransportTimeValue(fallbackTime, DEFAULT_WORK_TO_HOME_TIME);
  }

  function getVehicleDepartureTime(vehicle, fallbackTime, scopeOverride) {
    const departureTime = String(vehicle && vehicle.departure_time || "").trim();
    if (isValidTransportTimeValue(departureTime)) {
      return departureTime;
    }

    const resolvedScope = String(vehicle && vehicle.service_scope || scopeOverride || "").trim();
    if (resolvedScope !== "regular" && resolvedScope !== "weekend") {
      return "";
    }

    return isValidTransportTimeValue(fallbackTime) ? String(fallbackTime).trim() : "";
  }

  function formatExtraVehicleReferenceLabel(routeKind, referenceTime) {
    const normalizedReferenceTime = normalizeTransportTimeValue(referenceTime, "");
    if (!isValidTransportTimeValue(normalizedReferenceTime)) {
      return "";
    }

    if (routeKind === "home_to_work") {
      return translateTransportAiReviewText("ai.review.etaLabel", "ETA {time}h", {
        time: normalizedReferenceTime,
      });
    }
    if (routeKind === "work_to_home") {
      return translateTransportAiReviewText("ai.review.etdLabel", "ETD {time}h", {
        time: normalizedReferenceTime,
      });
    }

    return normalizedReferenceTime;
  }

  function resolveVehicleReferenceMode(scope, dashboard, arriveAtWorkTime, nowRef, fallbackWorkToHomeTime, routeKind, options) {
    const normalizedScope = String(scope || "").trim();
    if (isRoutineVehicleScope(normalizedScope)) {
      return getRoutineVehicleReferenceMode(
        dashboard,
        arriveAtWorkTime,
        nowRef,
        fallbackWorkToHomeTime,
        options
      );
    }

    if (normalizedScope === "extra") {
      if (routeKind === "home_to_work") {
        return "eta";
      }
      if (routeKind === "work_to_home") {
        return "etd";
      }
    }

    return null;
  }

  function getVehicleReferenceLabel(scope, vehicle, dashboard, arriveAtWorkTime, nowRef, fallbackWorkToHomeTime, routeKind, options) {
    const normalizedScope = String(scope || "").trim();
    const referenceMode = resolveVehicleReferenceMode(
      normalizedScope,
      dashboard,
      arriveAtWorkTime,
      nowRef,
      fallbackWorkToHomeTime,
      routeKind,
      options
    );
    if (isRoutineVehicleScope(normalizedScope)) {
      const normalizedArriveAtWorkTime = normalizeTransportTimeValue(arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME);
      const effectiveWorkToHomeTime = getEffectiveWorkToHomeDepartureTime(dashboard, fallbackWorkToHomeTime);
      return formatRoutineVehicleReferenceLabel(referenceMode, normalizedArriveAtWorkTime, effectiveWorkToHomeTime);
    }

    const effectiveDepartureTime = getEffectiveWorkToHomeDepartureTime(dashboard, fallbackWorkToHomeTime);
    const departureTime = getVehicleDepartureTime(vehicle, effectiveDepartureTime, normalizedScope);
    if (normalizedScope === "extra" && (referenceMode === "eta" || referenceMode === "etd")) {
      return formatExtraVehicleReferenceLabel(routeKind, departureTime);
    }

    return departureTime;
  }

  function resolveVehiclePassengerOperationalTime(
    scope,
    vehicle,
    requestRow,
    dashboard,
    arriveAtWorkTime,
    nowRef,
    fallbackWorkToHomeTime,
    routeKind,
    options
  ) {
    const normalizedScope = String(scope || "").trim();
    const referenceMode = resolveVehicleReferenceMode(
      normalizedScope,
      dashboard,
      arriveAtWorkTime,
      nowRef,
      fallbackWorkToHomeTime,
      routeKind,
      options
    );

    if (referenceMode === "etd") {
      const effectiveDepartureTime = getEffectiveWorkToHomeDepartureTime(dashboard, fallbackWorkToHomeTime);
      return {
        mode: "etd",
        time: getVehicleDepartureTime(vehicle, effectiveDepartureTime, normalizedScope),
        timeField: null,
      };
    }

    if (referenceMode === "eta") {
      // requested_time captures only the passenger's ask and can diverge from the operational pickup.
      const boardingTime = normalizeTransportTimeValue(requestRow && requestRow.boarding_time, "");
      return {
        mode: "eta",
        time: isValidTransportTimeValue(boardingTime) ? boardingTime : "",
        timeField: "boarding_time",
      };
    }

    return {
      mode: null,
      time: "",
      timeField: null,
    };
  }

  function getExtraVehicleDepartureFieldKey(routeKind) {
    if (routeKind === "home_to_work") {
      return "modal.fields.etaTime";
    }
    if (routeKind === "work_to_home") {
      return "modal.fields.etdTime";
    }
    return "modal.fields.departureTime";
  }

  function getExtraVehicleScopeNoteKey(routeKind) {
    if (routeKind === "home_to_work") {
      return "modal.notes.extraHomeToWork";
    }
    if (routeKind === "work_to_home") {
      return "modal.notes.extraWorkToHome";
    }
    return "modal.notes.extra";
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

  function groupAssignedRequestsByVehicleForDate(requestRows, selectedDate) {
    const normalizedSelectedDate = String(selectedDate || "");
    return (Array.isArray(requestRows) ? requestRows : []).reduce(function (grouped, requestRow) {
      if (
        !requestRow
        || requestRow.assignment_status !== "confirmed"
        || !requestRow.assigned_vehicle
        || requestRow.assigned_vehicle.id === undefined
      ) {
        return grouped;
      }

      if (normalizedSelectedDate && String(requestRow.service_date || "") !== normalizedSelectedDate) {
        return grouped;
      }

      const vehicleId = String(requestRow.assigned_vehicle.id);
      if (!grouped[vehicleId]) {
        grouped[vehicleId] = [];
      }
      grouped[vehicleId].push(requestRow);
      return grouped;
    }, {});
  }

  function canRequestBeDroppedOnVehicle(requestRow, scope, vehicle, routeKind) {
    if (!requestRow || !vehicle || requestRow.request_kind !== scope) {
      return false;
    }

    if (!isVehicleReadyForAllocation(vehicle)) {
      return false;
    }

    if (isRequestAssignedToVehicle(requestRow, vehicle)) {
      return false;
    }

    return scope !== "extra" || Boolean(vehicle.route_kind || routeKind);
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
    const normalizedMaxRows = Number.isFinite(Number(maxRows)) && Number(maxRows) > 0
      ? Math.max(1, Number(maxRows))
      : null;
    const rows = Array.isArray(assignedRows)
      ? assignedRows.map(function (requestRow) {
          return {
            name: String((requestRow && requestRow.nome) || ""),
            awarenessState: getPassengerAwarenessState(requestRow),
          };
        })
      : [];

    if (normalizedMaxRows === null) {
      return rows;
    }

    return rows.slice(0, normalizedMaxRows);
  }

  function mapScopeTitle(scope) {
    return t(`modal.scope.${scope === "regular" || scope === "weekend" ? scope : "extra"}`);
  }

  function getRouteKindLabel(routeKind) {
    const routeKey = ROUTE_KIND_KEYS[routeKind];
    return routeKey ? t(routeKey) : routeKind;
  }

  function getModalScopeNote(scope, routeKind) {
    if (scope === "extra") {
      return t(getExtraVehicleScopeNoteKey(routeKind));
    }
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

  function resolveTransportAiSettingsApiErrorState(error, options) {
    const resolvedOptions = options || {};
    const structuredPayload = extractStructuredTransportApiPayload(error && error.payload);
    const normalizedMessageKey = String(structuredPayload && structuredPayload.message_key || "").trim();
    const normalizedErrorCode = String(structuredPayload && structuredPayload.error_code || "").trim();
    const normalizedMessage = String(
      (structuredPayload && structuredPayload.message)
      || (error && error.message)
      || ""
    ).trim();
      const projectId = normalizeTransportAiSettingsProjectId(
        resolvedOptions.projectId,
        state.aiSettingsSelectedProjectId
      );
      const projectRows = normalizeTransportAiSettingsProjectRows(
        resolvedOptions.projectRows !== undefined
          ? resolvedOptions.projectRows
          : state.aiSettingsProjects
      );
      const hasProjectInCatalog = hasValidTransportAiSettingsProjectSelection(projectId, projectRows);

    if (
      normalizedErrorCode === "transport_ai_settings_project_required"
      || normalizedMessageKey === "ai.settingsProjectRequired"
      || isTransportAiProjectRequiredErrorPayload(error && error.payload)
      || normalizedMessage === "Transport AI project is required."
    ) {
      return {
        message: t("ai.settingsProjectRequired"),
        clearProjectSelection: false,
        markCatalogAsError: false,
      };
    }

    if (
      normalizedErrorCode === "transport_ai_settings_project_not_found"
      || normalizedMessageKey === "ai.settingsProjectMissing"
      || normalizedMessage === "Transport AI project does not exist."
    ) {
      return {
        message: t(hasProjectInCatalog ? "ai.settingsProjectRemoved" : "ai.settingsProjectMissing"),
        clearProjectSelection: true,
        markCatalogAsError: true,
      };
    }

    return {
      message: resolveTransportApiStructuredMessage(error && error.payload)
        || localizeTransportApiMessage(normalizedMessage),
      clearProjectSelection: false,
      markCatalogAsError: false,
    };
  }

    function getSelectedTransportAiSettingsProject() {
      const selectedProjectId = normalizeTransportAiSettingsProjectId(state.aiSettingsSelectedProjectId, null);
      if (!selectedProjectId) {
        return null;
      }
      return getTransportAiSettingsProjectRows().find(function (projectRow) {
        return projectRow.id === selectedProjectId;
      }) || null;
    }

    function applyTransportAiSettingsProjects(projectRows, preferredProjectId) {
      const normalizedProjects = normalizeTransportAiSettingsProjectRows(projectRows);
      const activeDraft = readTransportAiSettingsDraft(undefined, state.aiSettingsDraft || getDefaultTransportAiSettingsDraft());
      const previousSelectedProjectId = normalizeTransportAiSettingsProjectId(
        state.aiSettingsSelectedProjectId,
        null
      );
      state.aiSettingsProjects = normalizedProjects;
      const selectedProjectId = normalizeTransportAiSettingsProjectId(
        preferredProjectId,
        previousSelectedProjectId
      );
      const matchedProject = normalizedProjects.find(function (projectRow) {
        return projectRow.id === selectedProjectId;
      }) || normalizedProjects[0] || null;
      state.aiSettingsSelectedProjectId = matchedProject ? matchedProject.id : null;

      if (!matchedProject) {
        clearTransportAiSettingsProjectSelection();
        return null;
      }

      const activeDraftProjectId = normalizeTransportAiSettingsProjectId(activeDraft.projectId, null);
      if (previousSelectedProjectId === matchedProject.id && activeDraftProjectId === matchedProject.id) {
        state.aiSettingsDraft = activeDraft;
        return matchedProject;
      }

      state.aiSettingsDraft = readTransportAiSettingsDraft(
        {
          projectId: matchedProject.id,
          provider: DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER,
          apiKey: "",
        },
        getDefaultTransportAiSettingsDraft()
      );
      return matchedProject;
    }

    function syncAiSettingsControls(options) {
      const syncOptions = options || {};
      const activeDraft = readTransportAiSettingsDraft(undefined, state.aiSettingsDraft || getDefaultTransportAiSettingsDraft());
      const availableProjects = Array.isArray(state.aiSettingsProjects) ? state.aiSettingsProjects : [];
      const projectCatalogStatus = getTransportAiSettingsProjectCatalogStatus();
      const projectCatalogReady = projectCatalogStatus === AI_SETTINGS_PROJECT_CATALOG_STATUS.ready;
      const projectCatalogLoading = projectCatalogStatus === AI_SETTINGS_PROJECT_CATALOG_STATUS.loading;
      const selectedProjectId = normalizeTransportAiSettingsProjectId(
        state.aiSettingsSelectedProjectId,
        activeDraft.projectId
      );
      const hasSelectedProject = hasValidTransportAiSettingsProjectSelection(selectedProjectId, availableProjects);
      const selectedProvider = normalizeTransportAiSettingsProvider(
        activeDraft.provider,
        state.aiSettingsLoadedProvider || DEFAULT_TRANSPORT_AI_SETTINGS_PROVIDER
      );
      const controlsDisabled = !state.isAuthenticated || state.aiSettingsLoading || state.aiSettingsSaving;
      const projectControlsDisabled = controlsDisabled || projectCatalogLoading || !availableProjects.length;
      const fieldControlsDisabled = controlsDisabled || !hasSelectedProject || !projectCatalogReady;
      const apiKeyValue = String(activeDraft.apiKey || "").trim();

      if (aiSettingsProjectInput) {
        clearElement(aiSettingsProjectInput);
        if (!availableProjects.length) {
          const emptyOption = document.createElement("option");
          emptyOption.value = "";
          emptyOption.textContent = projectCatalogLoading
            ? t("ai.settingsLoading")
            : t("ai.settingsNoProjectsAvailable");
          aiSettingsProjectInput.appendChild(emptyOption);
        } else {
          const placeholderOption = document.createElement("option");
          placeholderOption.value = "";
          placeholderOption.textContent = t("ai.settingsSelectProject");
          aiSettingsProjectInput.appendChild(placeholderOption);

          availableProjects.forEach(function (projectRow) {
            const optionElement = document.createElement("option");
            optionElement.value = String(projectRow.id);
            optionElement.textContent = projectRow.name;
            aiSettingsProjectInput.appendChild(optionElement);
          });
        }
        aiSettingsProjectInput.value = hasSelectedProject ? String(selectedProjectId) : "";
        aiSettingsProjectInput.disabled = projectControlsDisabled;
      }

      if (!syncOptions.preserveInputs) {
        if (aiSettingsProviderInput) {
          aiSettingsProviderInput.value = selectedProvider;
        }
        if (aiSettingsApiKeyInput) {
          aiSettingsApiKeyInput.value = activeDraft.apiKey;
        }
      }

      if (aiSettingsProviderInput) {
        aiSettingsProviderInput.disabled = fieldControlsDisabled;
      }
      if (aiSettingsApiKeyInput) {
        aiSettingsApiKeyInput.disabled = fieldControlsDisabled;
      }
      if (aiSettingsMapsApiKeyInput) {
        if (!syncOptions.preserveInputs) {
          aiSettingsMapsApiKeyInput.value = activeDraft.mapsApiKey;
        }
        aiSettingsMapsApiKeyInput.disabled = controlsDisabled;
      }
      if (aiSettingsProviderNote) {
        if (projectCatalogLoading) {
          aiSettingsProviderNote.textContent = t("ai.settingsLoading");
        } else if (!availableProjects.length) {
          aiSettingsProviderNote.textContent = t("ai.settingsNoProjectsAvailable");
        } else if (!hasSelectedProject) {
          aiSettingsProviderNote.textContent = t("ai.settingsSelectProject");
        } else if (!projectCatalogReady) {
          aiSettingsProviderNote.textContent = t("ai.settingsProjectLoadFailed");
        } else {
          aiSettingsProviderNote.textContent = buildTransportAiSettingsProviderNote(selectedProvider);
        }
      }
      if (aiSettingsApiKeyHint) {
        let hintMessage = "";
        let hintTone = "info";
        if (projectCatalogLoading) {
          hintMessage = "";
        } else if (!projectCatalogReady && hasSelectedProject) {
          hintMessage = t("ai.settingsProjectLoadFailed");
          hintTone = "warning";
        } else if (!hasSelectedProject && availableProjects.length) {
          hintMessage = t("ai.settingsSelectProject");
        } else if (!apiKeyValue) {
          if (state.aiSettingsHasApiKey && selectedProvider === state.aiSettingsLoadedProvider && state.aiSettingsApiKeyHint) {
            hintMessage = t("ai.settingsApiKeyHint", { hint: state.aiSettingsApiKeyHint });
          } else if (state.aiSettingsHasApiKey && selectedProvider !== state.aiSettingsLoadedProvider) {
            hintMessage = t("ai.settingsProviderChangeRequiresKey");
            hintTone = "warning";
          } else if (!state.aiSettingsHasApiKey) {
            hintMessage = t("ai.settingsApiKeyMissing");
          }
        }

        aiSettingsApiKeyHint.hidden = !hintMessage;
        aiSettingsApiKeyHint.textContent = hintMessage;
        aiSettingsApiKeyHint.dataset.tone = hintTone;
      }

      if (aiSettingsMapsApiKeyHint) {
        const mapsApiKeyValue = String(activeDraft.mapsApiKey || "").trim();
        let mapsHintMessage = "";
        let mapsHintTone = "info";
        if (!mapsApiKeyValue) {
          if (state.aiSettingsHasMapsApiKey && state.aiSettingsMapsApiKeyHint) {
            mapsHintMessage = t("ai.settingsMapsApiKeyHint", { hint: state.aiSettingsMapsApiKeyHint });
          } else if (!state.aiSettingsHasMapsApiKey) {
            mapsHintMessage = t("ai.settingsMapsApiKeyMissing");
          }
        }
        aiSettingsMapsApiKeyHint.hidden = !mapsHintMessage;
        aiSettingsMapsApiKeyHint.textContent = mapsHintMessage;
        aiSettingsMapsApiKeyHint.dataset.tone = mapsHintTone;
      }

      document.querySelectorAll("[data-close-ai-settings-modal]").forEach(function (buttonElement) {
        buttonElement.disabled = state.aiSettingsSaving;
      });
      document.querySelectorAll("[data-ai-settings-save]").forEach(function (buttonElement) {
        buttonElement.disabled = fieldControlsDisabled;
      });

      if (aiSettingsModal) {
        aiSettingsModal.setAttribute(
          "aria-busy",
          state.aiSettingsLoading || state.aiSettingsSaving ? "true" : "false"
        );
      }

      if (!aiSettingsFeedback) {
        return;
      }

      let feedbackMessage = "";
      if (state.aiSettingsFeedbackKey) {
        const translatedFeedback = t(state.aiSettingsFeedbackKey, state.aiSettingsFeedbackValues || undefined);
        feedbackMessage = translatedFeedback && translatedFeedback !== state.aiSettingsFeedbackKey
          ? translatedFeedback
          : String(state.aiSettingsFeedbackMessage || "").trim() || translatedFeedback;
      } else {
        feedbackMessage = String(state.aiSettingsFeedbackMessage || "").trim();
      }
      if (!feedbackMessage) {
        aiSettingsFeedback.hidden = true;
        aiSettingsFeedback.textContent = "";
        aiSettingsFeedback.dataset.tone = state.aiSettingsFeedbackTone || "info";
        return;
      }

      aiSettingsFeedback.hidden = false;
      aiSettingsFeedback.textContent = feedbackMessage;
      aiSettingsFeedback.dataset.tone = state.aiSettingsFeedbackTone || "info";
    }

    function syncAiChangesControls() {
      const commandState = resolveAiChangesCommandState(
        state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion },
        {
          isAuthenticated: state.isAuthenticated,
          isPending: state.aiChangesCommandPending,
          pendingAction: state.aiChangesPendingAction,
        }
      );

      if (aiChangesCancelButton) {
        aiChangesCancelButton.disabled = commandState.isPending;
        aiChangesCancelButton.textContent = t("ai.changesCancel");
      }
      if (aiChangesDiscardButton) {
        aiChangesDiscardButton.disabled = !commandState.canCancel;
        aiChangesDiscardButton.textContent = t(
          commandState.isPending && commandState.pendingAction === "cancel"
            ? "ai.changesDiscarding"
            : "ai.changesDiscard"
        );
      }
      if (aiChangesApplyButton) {
        aiChangesApplyButton.disabled = !commandState.canApply;
        aiChangesApplyButton.textContent = t(
          commandState.isPending && commandState.pendingAction === "apply"
            ? "ai.changesApplying"
            : "ai.changesApply"
        );
      }

      document.querySelectorAll("[data-close-ai-changes-modal]").forEach(function (buttonElement) {
        buttonElement.disabled = commandState.isPending;
      });

      if (aiChangesModal) {
        aiChangesModal.setAttribute("aria-busy", commandState.isPending ? "true" : "false");
      }
    }

    function syncAiChangesSummaryCopy() {
      if (!aiChangesSummary) {
        return;
      }

      let summaryMessage = "";
      if (state.aiChangesSummaryKey) {
        const translatedSummary = t(state.aiChangesSummaryKey, state.aiChangesSummaryValues || undefined);
        summaryMessage = translatedSummary && translatedSummary !== state.aiChangesSummaryKey
          ? translatedSummary
          : String(state.aiChangesSummaryMessage || "").trim() || translatedSummary;
      } else {
        summaryMessage = String(state.aiChangesSummaryMessage || "").trim();
      }
      if (!summaryMessage) {
        aiChangesSummary.hidden = true;
        aiChangesSummary.textContent = "";
        aiChangesSummary.dataset.tone = state.aiChangesSummaryTone || "success";
        return;
      }

      aiChangesSummary.hidden = false;
      aiChangesSummary.textContent = summaryMessage;
      aiChangesSummary.dataset.tone = state.aiChangesSummaryTone || "success";
    }

    function syncAiChangesSummaryRender() {
      if ((!aiChangesSummaryGrid && !aiChangesSummaryPanel) || (!state.aiRouteRunStatus && !state.aiRouteSuggestion)) {
        return;
      }

      renderAiChangesSummary({
        runStatusResponse: state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion },
        fallbackCurrencyCode: state.priceCurrencyCode,
        summaryGridElement: aiChangesSummaryGrid,
        summaryPanelElement: aiChangesSummaryPanel,
      });
    }

    function syncAiVehicleChangesRender() {
      if (!aiChangesVehiclesPanel || (!state.aiRouteRunStatus && !state.aiRouteSuggestion)) {
        return;
      }

      renderAiVehicleChanges({
        runStatusResponse: state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion },
        fallbackCurrencyCode: state.priceCurrencyCode,
        vehiclesPanelElement: aiChangesVehiclesPanel,
      });
    }

    function syncAiPassengerAllocationsRender() {
      if (!aiChangesPassengersPanel || (!state.aiRouteRunStatus && !state.aiRouteSuggestion)) {
        return;
      }

      renderAiPassengerAllocations({
        runStatusResponse: state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion },
        passengersPanelElement: aiChangesPassengersPanel,
      });
    }

    function syncAiRouteItinerariesRender() {
      if (!aiChangesRoutesPanel || (!state.aiRouteRunStatus && !state.aiRouteSuggestion)) {
        return;
      }

      renderAiRouteItineraries({
        runStatusResponse: state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion },
        fallbackCurrencyCode: state.priceCurrencyCode,
        routesPanelElement: aiChangesRoutesPanel,
      });
    }

    function syncAiChangesAuditRender() {
      if (!aiChangesAuditPanel || (!state.aiRouteRunStatus && !state.aiRouteSuggestion)) {
        return;
      }

      renderAiChangesAudit({
        runStatusResponse: state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion },
        auditPanelElement: aiChangesAuditPanel,
      });
    }

    function readTransportSettingsDraft() {
      return {
        arriveAtWorkTime: settingsArriveAtWorkInput ? settingsArriveAtWorkInput.value : state.arriveAtWorkTime,
        workToHomeTime: settingsTimeInput ? settingsTimeInput.value : state.workToHomeTime,
        extraCarToleranceMinutes: settingsExtraCarToleranceInput
          ? settingsExtraCarToleranceInput.value
          : state.extraCarToleranceMinutes,
        lastUpdateTime: settingsLastUpdateInput ? settingsLastUpdateInput.value : state.lastUpdateTime,
        priceCurrencyCode: settingsPriceCurrencySelect ? settingsPriceCurrencySelect.value : state.priceCurrencyCode,
        priceRateUnit: settingsPriceRateUnitSelect ? settingsPriceRateUnitSelect.value : state.priceRateUnit,
        defaultCarSeats: settingsDefaultSeatInputs.carro ? settingsDefaultSeatInputs.carro.value : state.vehicleSeatDefaults.carro,
        defaultMinivanSeats: settingsDefaultSeatInputs.minivan ? settingsDefaultSeatInputs.minivan.value : state.vehicleSeatDefaults.minivan,
        defaultVanSeats: settingsDefaultSeatInputs.van ? settingsDefaultSeatInputs.van.value : state.vehicleSeatDefaults.van,
        defaultBusSeats: settingsDefaultSeatInputs.onibus ? settingsDefaultSeatInputs.onibus.value : state.vehicleSeatDefaults.onibus,
        defaultCarPrice: settingsDefaultPriceInputs.carro ? settingsDefaultPriceInputs.carro.value : state.vehiclePriceDefaults.carro,
        defaultMinivanPrice: settingsDefaultPriceInputs.minivan ? settingsDefaultPriceInputs.minivan.value : state.vehiclePriceDefaults.minivan,
        defaultVanPrice: settingsDefaultPriceInputs.van ? settingsDefaultPriceInputs.van.value : state.vehiclePriceDefaults.van,
        defaultBusPrice: settingsDefaultPriceInputs.onibus ? settingsDefaultPriceInputs.onibus.value : state.vehiclePriceDefaults.onibus,
        defaultToleranceMinutes: settingsDefaultToleranceInput ? settingsDefaultToleranceInput.value : state.vehicleToleranceDefaultMinutes,
      };
    }

    function syncRouteTimeControls() {
      const canEditRouteTime = state.isAuthenticated;
      const shouldShowRouteTime = true;
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

      syncAiButtonPlacement();
    }

    function syncAiButtonPlacement() {
      if (!aiMenuShell || !transportTopbar) {
        return;
      }

      if (globalScope.matchMedia && globalScope.matchMedia("(max-width: 860px)").matches) {
        aiMenuShell.style.removeProperty("--transport-ai-anchor-x");
        return;
      }

      const allocationBoardTitle = document.querySelector(".transport-topbar-brand .transport-topbar-title");
      if (!allocationBoardTitle || !routeTimePopover || routeTimePopover.hidden) {
        aiMenuShell.style.removeProperty("--transport-ai-anchor-x");
        return;
      }

      const topbarRect = transportTopbar.getBoundingClientRect();
      const titleRect = allocationBoardTitle.getBoundingClientRect();
      const routeTimeRect = routeTimePopover.getBoundingClientRect();
      const aiShellRect = aiMenuShell.getBoundingClientRect();
      if (!topbarRect.width || !titleRect.width || !routeTimeRect.width || !aiShellRect.width) {
        return;
      }

      const desiredCenter = ((titleRect.right + routeTimeRect.left) / 2) - topbarRect.left;
      const minCenter = aiShellRect.width / 2 + 8;
      const maxCenter = topbarRect.width - aiShellRect.width / 2 - 8;
      const clampedCenter = Math.min(maxCenter, Math.max(minCenter, desiredCenter));
      aiMenuShell.style.setProperty("--transport-ai-anchor-x", `${clampedCenter}px`);
    }

    function syncAiMenuControls() {
      const hasActiveRun = state.aiRouteRequestPending
        || state.aiRoutePollingTimer !== null
        || shouldContinuePollingAiRouteRun(state.aiRouteRunStatus);
      const hasSuggestionReady = hasRenderableTransportAiReview(
        state.aiRouteRunStatus || { suggestion: state.aiRouteSuggestion }
      );
      if (aiMenuShell) {
        aiMenuShell.classList.toggle("is-open", state.aiMenuOpen);
        aiMenuShell.classList.toggle("is-calculating", hasActiveRun);
        aiMenuShell.classList.toggle("is-suggestion-ready", !hasActiveRun && hasSuggestionReady);
      }
      if (aiMenuTrigger) {
        aiMenuTrigger.setAttribute("aria-expanded", String(state.aiMenuOpen));
            syncAiButtonPlacement();
      }
      if (aiMenu) {
        aiMenu.hidden = !state.aiMenuOpen;
      }
      if (aiImplementModificationsButton) {
        aiImplementModificationsButton.disabled = !state.isAuthenticated || state.aiLatestSuggestionLoading;
      }
    }

    function closeAiMenu(options) {
      const closeOptions = options || {};
      state.aiMenuOpen = false;
      syncAiMenuControls();

      if (
        closeOptions.restoreFocus
        && aiMenuTrigger
        && typeof aiMenuTrigger.focus === "function"
      ) {
        aiMenuTrigger.focus();
      }
    }

    function openAiMenu() {
      state.aiMenuOpen = true;
      syncAiMenuControls();
      syncAiChangesSummaryRender();
    }

    function toggleAiMenu() {
      if (state.aiMenuOpen) {
        closeAiMenu();
        return;
      }
      openAiMenu();
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
        setStatus("", "warning", { key: "status.locked" });
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
            setStatus("", "success", { key: "status.settingsSaved" });
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
      syncAiAgentSettingsControls({ preserveInputs: true });
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

    function clearActiveAuthVerificationRequest() {
      if (
        state.authVerifyRequestController
        && typeof state.authVerifyRequestController.abort === "function"
      ) {
        state.authVerifyRequestController.abort();
      }
      state.authVerifyRequestController = null;
    }

    function clearPendingRealtimeRefresh() {
      if (state.realtimeRefreshTimer !== null) {
        globalScope.clearTimeout(state.realtimeRefreshTimer);
        state.realtimeRefreshTimer = null;
      }
    }

    function clearPendingRealtimeReconnect() {
      if (state.realtimeReconnectTimer !== null) {
        globalScope.clearTimeout(state.realtimeReconnectTimer);
        state.realtimeReconnectTimer = null;
      }
    }

    function queueDashboardLoad(selectedDate, options) {
      const normalizedDate = startOfLocalDay(selectedDate || dateStore.getValue());
      state.queuedDashboardLoad = {
        selectedDate: normalizedDate,
        options: Object.assign({}, state.queuedDashboardLoad ? state.queuedDashboardLoad.options : {}, options || {}),
      };
    }

    function queueDeferredDashboardLoad(selectedDate, options) {
      const normalizedDate = startOfLocalDay(selectedDate || dateStore.getValue());
      state.deferredDashboardLoad = {
        selectedDate: normalizedDate,
        options: Object.assign({}, state.deferredDashboardLoad ? state.deferredDashboardLoad.options : {}, options || {}),
      };
    }

    function clearPendingAiRoutePolling() {
      if (state.aiRoutePollingTimer !== null) {
        globalScope.clearTimeout(state.aiRoutePollingTimer);
        state.aiRoutePollingTimer = null;
      }
    }

    function resetAiRoutePollingBackoff() {
      state.aiRoutePollingAttempt = 0;
    }

    function getNextAiRoutePollDelay() {
      const delayMs = Math.min(
        TRANSPORT_AI_ROUTE_POLL_MAX_MS,
        TRANSPORT_AI_ROUTE_POLL_INTERVAL_MS * Math.pow(2, Math.max(0, state.aiRoutePollingAttempt))
      );
      state.aiRoutePollingAttempt += 1;
      return delayMs;
    }

    function isTransportPageHidden() {
      return Boolean(
        globalScope.document
        && typeof globalScope.document.visibilityState === "string"
        && globalScope.document.visibilityState === "hidden"
      );
    }

    function getTransportAuthInputSnapshot() {
      return `${authKeyInput ? String(authKeyInput.value || "") : ""}\n${authPasswordInput ? String(authPasswordInput.value || "") : ""}`;
    }

    function readTransportAuthCredentials() {
      const chave = normalizeAuthKeyValue();
      const senha = authPasswordInput ? String(authPasswordInput.value || "") : "";
      return {
        chave,
        senha,
        signature: chave.length === 4 && senha ? `${chave}\n${senha}` : "",
      };
    }

    function hasRoutineVehicleReferenceRows(dashboard) {
      return Boolean(
        dashboard
        && (
          (Array.isArray(dashboard.regular_vehicles) && dashboard.regular_vehicles.length)
          || (Array.isArray(dashboard.weekend_vehicles) && dashboard.weekend_vehicles.length)
          || (Array.isArray(dashboard.regular_vehicle_registry) && dashboard.regular_vehicle_registry.length)
          || (Array.isArray(dashboard.weekend_vehicle_registry) && dashboard.weekend_vehicle_registry.length)
        )
      );
    }

    function clearVehicleReferenceModeTimer() {
      if (state.vehicleReferenceModeTimer) {
        globalScope.clearTimeout(state.vehicleReferenceModeTimer);
        state.vehicleReferenceModeTimer = null;
      }
    }

    function clearVehicleReferenceClock() {
      clearVehicleReferenceModeTimer();
      state.dashboardGeneratedAt = "";
      state.vehicleReferenceClock = null;
    }

    function syncTransportReferenceClock(dashboard) {
      state.arriveAtWorkTime = normalizeTransportTimeValue(
        dashboard && dashboard.arrive_at_work_time,
        normalizeTransportTimeValue(state.arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME)
      );
      state.dashboardGeneratedAt = dashboard && dashboard.dashboard_generated_at
        ? String(dashboard.dashboard_generated_at)
        : "";
      state.vehicleReferenceClock = createTransportReferenceClock(state.dashboardGeneratedAt);
    }

    function scheduleVehicleReferenceModeTimer() {
      clearVehicleReferenceModeTimer();
      if (!state.dashboard || isTransportPageHidden() || !hasRoutineVehicleReferenceRows(state.dashboard)) {
        return;
      }

      const effectiveDepartureTime = getEffectiveWorkToHomeDepartureTime(state.dashboard, state.workToHomeTime);
      const delayMs = resolveNextRoutineVehicleReferenceDelayMs(
        state.vehicleReferenceClock,
        normalizeTransportTimeValue(state.arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME),
        effectiveDepartureTime
      );
      if (delayMs === null) {
        return;
      }

      state.vehicleReferenceModeTimer = globalScope.setTimeout(function () {
        state.vehicleReferenceModeTimer = null;
        if (isTransportPageHidden() || !state.dashboard) {
          return;
        }
        renderVehiclePanels();
        scheduleVehicleReferenceModeTimer();
      }, delayMs);
    }

    function closeRealtimeEventStream() {
      if (state.realtimeEventStream) {
        state.realtimeEventStream.close();
        state.realtimeEventStream = null;
      }
      state.realtimeConnected = false;
    }

    function flushDeferredDashboardLoad() {
      if (!state.deferredDashboardLoad || !state.isAuthenticated || isTransportPageHidden()) {
        return Promise.resolve(null);
      }

      const deferredLoad = state.deferredDashboardLoad;
      state.deferredDashboardLoad = null;
      return loadDashboard(deferredLoad.selectedDate, deferredLoad.options);
    }

    function scheduleRealtimeReconnect() {
      if (!state.isAuthenticated) {
        return;
      }

      state.realtimeReconnectPending = true;
      if (isTransportPageHidden()) {
        return;
      }

      clearPendingRealtimeReconnect();
      const delayMs = Math.min(
        TRANSPORT_REALTIME_RECONNECT_MAX_MS,
        TRANSPORT_REALTIME_RECONNECT_BASE_MS * Math.pow(2, Math.max(0, state.realtimeReconnectAttempt))
      );
      state.realtimeReconnectAttempt += 1;
      state.realtimeReconnectTimer = globalScope.setTimeout(function () {
        state.realtimeReconnectTimer = null;
        if (!state.isAuthenticated) {
          return;
        }
        if (isTransportPageHidden()) {
          state.realtimeReconnectPending = true;
          return;
        }
        startRealtimeUpdates();
      }, delayMs);
    }

    function stopRealtimeUpdates() {
      clearPendingRealtimeRefresh();
      clearPendingRealtimeReconnect();
      closeRealtimeEventStream();
      state.realtimeReconnectAttempt = 0;
      state.realtimeReconnectPending = false;
    }

    function requestDashboardRefresh(options) {
      const refreshOptions = options || {};
      if (!state.isAuthenticated) {
        return;
      }

      if (state.dashboardLoadPromise) {
        queueDashboardLoad(dateStore.getValue(), Object.assign({ announce: false }, refreshOptions));
        return;
      }

      if (isTransportPageHidden()) {
        queueDeferredDashboardLoad(dateStore.getValue(), Object.assign({ announce: false }, refreshOptions));
        return;
      }

      clearPendingRealtimeRefresh();
      state.realtimeRefreshTimer = globalScope.setTimeout(function () {
        state.realtimeRefreshTimer = null;
        if (state.dashboardLoadPromise) {
          queueDashboardLoad(dateStore.getValue(), Object.assign({ announce: false }, refreshOptions));
          return;
        }
        if (isTransportPageHidden()) {
          queueDeferredDashboardLoad(dateStore.getValue(), Object.assign({ announce: false }, refreshOptions));
          return;
        }
        loadDashboard(dateStore.getValue(), Object.assign({ announce: false }, refreshOptions));
      }, TRANSPORT_REALTIME_DEBOUNCE_MS);
    }

    function startRealtimeUpdates() {
      clearPendingRealtimeReconnect();
      clearPendingRealtimeRefresh();
      closeRealtimeEventStream();
      if (!state.isAuthenticated || typeof globalScope.EventSource !== "function") {
        return;
      }
      if (isTransportPageHidden()) {
        state.realtimeReconnectPending = true;
        return;
      }

      state.realtimeReconnectPending = false;
      const realtimeEventStream = new globalScope.EventSource(`${TRANSPORT_API_PREFIX}/stream`);
      state.realtimeEventStream = realtimeEventStream;
      realtimeEventStream.onopen = function () {
        if (state.realtimeEventStream !== realtimeEventStream) {
          return;
        }
        state.realtimeConnected = true;
        state.realtimeReconnectAttempt = 0;
      };
      realtimeEventStream.onmessage = function () {
        if (state.realtimeEventStream !== realtimeEventStream) {
          return;
        }
        state.realtimeConnected = true;
        requestDashboardRefresh({ announce: false });
      };
      realtimeEventStream.onerror = function () {
        if (state.realtimeEventStream !== realtimeEventStream) {
          return;
        }
        closeRealtimeEventStream();
        scheduleRealtimeReconnect();
      };
    }

    function handlePageVisibilityChange() {
      if (isTransportPageHidden()) {
        clearVehicleReferenceModeTimer();
        clearPendingRealtimeRefresh();
        clearPendingRealtimeReconnect();
        clearPendingAiRoutePolling();
        closeRealtimeEventStream();
        state.realtimeReconnectPending = state.isAuthenticated;
        return;
      }

      if (!state.isAuthenticated) {
        return;
      }

      if (state.realtimeReconnectPending || !state.realtimeEventStream) {
        startRealtimeUpdates();
      }
      if (state.dashboard) {
        renderVehiclePanels();
        scheduleVehicleReferenceModeTimer();
      }
      void flushDeferredDashboardLoad();
      if (shouldContinuePollingAiRouteRun(state.aiRouteRunStatus)) {
        queueAiRouteRunPoll(state.aiRouteRunKey, 0);
      }
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
        clearVehicleReferenceClock();
        state.arriveAtWorkTime = DEFAULT_ARRIVE_AT_WORK_TIME;
        stopRealtimeUpdates();
        clearPendingAiRoutePolling();
        resetAiRoutePollingBackoff();
        state.aiRouteRequestPending = false;
        state.aiRouteInBackground = false;
        state.aiRouteRunStatus = null;
        state.aiRouteRunKey = null;
        state.aiRouteSuggestion = null;
        state.deferredDashboardLoad = null;
      }

      syncAiAgentSettingsControls({ preserveInputs: true });

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
      state.authVerifySignature = "";
      state.lastVerifiedAuthSignature = "";
      clearPendingAuthVerification();
      clearActiveAuthVerificationRequest();
      state.sessionBootstrapPending = false;
      setAuthenticationState(false, null, { resetInputs: true, clearDashboard: true });
      requestJson(`${TRANSPORT_API_PREFIX}/auth/logout`, { method: "POST" }).catch(function () {});
      const normalizedMessage = String(message || "").trim();
      const sessionExpiredMessage = String(getTransportSessionExpiredMessage() || "").trim();
      const statusKey = !normalizedMessage
        ? "status.locked"
        : normalizedMessage === sessionExpiredMessage
          ? "status.sessionExpired"
          : "";
      setStatus(normalizedMessage || getTransportLockedMessage(), "warning", { key: statusKey });
    }

  function handleProtectedRequestError(error, fallbackMessage) {
    if (error && Number(error.status) === 401) {
      clearTransportSession(getTransportSessionExpiredMessage());
      return true;
    }
    const resolvedErrorMessage = resolveTransportApiStructuredMessage(error && error.payload)
      || localizeTransportApiMessage(error && error.message)
      || fallbackMessage;
    setStatus(resolvedErrorMessage, "error", resolveTransportApiStructuredMessageOptions(error && error.payload));
    if (error && (Number(error.status) === 404 || Number(error.status) === 409)) {
      requestDashboardRefresh({ announce: false });
    }
    return false;
  }

    function openUserCreationRequest() {
      if (typeof globalScope.open === "function") {
        globalScope.open("../admin", "_blank", "noopener");
      }
      setStatus("", "info", { key: "status.openAdminToRequestUser" });
    }

    function loadTransportSettings(options) {
      const nextOptions = options || {};
      if (!state.isAuthenticated) {
        state.arriveAtWorkTime = normalizeTransportTimeValue(state.arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME);
        state.workToHomeTime = state.workToHomeTime || DEFAULT_WORK_TO_HOME_TIME;
        state.lastUpdateTime = state.lastUpdateTime || DEFAULT_LAST_UPDATE_TIME;
        state.extraCarToleranceMinutes = normalizeVehicleToleranceSetting(
          state.extraCarToleranceMinutes,
          DEFAULT_EXTRA_CAR_TOLERANCE_MINUTES
        );
        state.vehicleSeatDefaults = applyTransportVehicleSeatDefaults(state.vehicleSeatDefaults);
        state.vehiclePriceDefaults = resolveTransportVehiclePriceDefaults(
          state.vehiclePriceDefaults,
          DEFAULT_VEHICLE_PRICE_DEFAULTS
        );
        state.vehicleToleranceDefaultMinutes = applyTransportVehicleToleranceDefault(state.vehicleToleranceDefaultMinutes);
        state.priceCurrencyCode = normalizeTransportCurrencyCode(state.priceCurrencyCode);
        state.priceRateUnit = normalizeTransportPriceRateUnit(state.priceRateUnit, DEFAULT_TRANSPORT_PRICE_RATE_UNIT);
        state.availableCurrencies = resolveTransportCurrencyOptions(state.availableCurrencies);
        syncSettingsControls();
        return Promise.resolve(null);
      }

      state.settingsLoading = true;
      syncSettingsControls();
      return requestJson(`${TRANSPORT_API_PREFIX}/settings`)
        .then(function (response) {
          state.settingsLoaded = true;
          state.arriveAtWorkTime = normalizeTransportTimeValue(
            response && response.arrive_at_work_time,
            normalizeTransportTimeValue(state.arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME)
          );
          state.workToHomeTime = String(
            response && response.work_to_home_time ? response.work_to_home_time : DEFAULT_WORK_TO_HOME_TIME
          );
          state.lastUpdateTime = String(
            response && response.last_update_time ? response.last_update_time : DEFAULT_LAST_UPDATE_TIME
          );
          state.extraCarToleranceMinutes = normalizeVehicleToleranceSetting(
            response && response.extra_car_tolerance_minutes,
            normalizeVehicleToleranceSetting(
              state.extraCarToleranceMinutes,
              DEFAULT_EXTRA_CAR_TOLERANCE_MINUTES
            )
          );
          state.priceCurrencyCode = normalizeTransportCurrencyCode(response && response.price_currency_code);
          state.priceRateUnit = normalizeTransportPriceRateUnit(
            response && response.price_rate_unit,
            DEFAULT_TRANSPORT_PRICE_RATE_UNIT
          );
          state.availableCurrencies = resolveTransportCurrencyOptions(response && response.available_currencies);
          state.vehicleSeatDefaults = applyTransportVehicleSeatDefaults(response);
          state.vehiclePriceDefaults = resolveTransportVehiclePriceDefaults(
            response,
            state.vehiclePriceDefaults
          );
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
      const previousArriveAtWorkTime = state.arriveAtWorkTime;
      const previousWorkToHomeTime = state.workToHomeTime;
      const previousLastUpdateTime = state.lastUpdateTime;
      const previousExtraCarToleranceMinutes = state.extraCarToleranceMinutes;
      const previousPriceCurrencyCode = state.priceCurrencyCode;
      const previousPriceRateUnit = state.priceRateUnit;
      const previousVehicleSeatDefaults = Object.assign({}, state.vehicleSeatDefaults);
      const previousVehiclePriceDefaults = Object.assign({}, state.vehiclePriceDefaults);
      const previousAvailableCurrencies = resolveTransportCurrencyOptions(state.availableCurrencies);
      const previousVehicleToleranceDefaultMinutes = state.vehicleToleranceDefaultMinutes;
      const normalizedArriveAtWorkTime = normalizeTransportTimeValue(
        nextValues && nextValues.arriveAtWorkTime,
        normalizeTransportTimeValue(state.arriveAtWorkTime, DEFAULT_ARRIVE_AT_WORK_TIME)
      );
      const normalizedTime = normalizeTransportTimeValue(
        nextValues && nextValues.workToHomeTime,
        normalizeTransportTimeValue(state.workToHomeTime, DEFAULT_WORK_TO_HOME_TIME)
      );
      const normalizedLastUpdateTime = normalizeTransportTimeValue(
        nextValues && nextValues.lastUpdateTime,
        normalizeTransportTimeValue(state.lastUpdateTime, DEFAULT_LAST_UPDATE_TIME)
      );
      const normalizedExtraCarToleranceMinutes = normalizeVehicleToleranceSetting(
        nextValues && nextValues.extraCarToleranceMinutes,
        normalizeVehicleToleranceSetting(
          state.extraCarToleranceMinutes,
          DEFAULT_EXTRA_CAR_TOLERANCE_MINUTES
        )
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
      const normalizedPriceCurrencyCode = normalizeTransportCurrencyCode(nextValues && nextValues.priceCurrencyCode);
      const normalizedPriceRateUnit = normalizeTransportPriceRateUnit(
        nextValues && nextValues.priceRateUnit,
        state.priceRateUnit || DEFAULT_TRANSPORT_PRICE_RATE_UNIT
      );
      const normalizedPriceDefaults = resolveTransportVehiclePriceDefaults(
        {
          default_car_price: nextValues && nextValues.defaultCarPrice,
          default_minivan_price: nextValues && nextValues.defaultMinivanPrice,
          default_van_price: nextValues && nextValues.defaultVanPrice,
          default_bus_price: nextValues && nextValues.defaultBusPrice,
        },
        state.vehiclePriceDefaults
      );
      const normalizedToleranceDefault = normalizeVehicleToleranceSetting(
        nextValues && nextValues.defaultToleranceMinutes,
        state.vehicleToleranceDefaultMinutes
      );
      if (
        !isValidTransportTimeValue(normalizedArriveAtWorkTime)
        || !isValidTransportTimeValue(normalizedTime)
        || !isValidTransportTimeValue(normalizedLastUpdateTime)
      ) {
        syncSettingsControls();
        return Promise.resolve(null);
      }
      if (
        normalizedPriceCurrencyCode
        && !state.availableCurrencies.some(function (currencyOption) {
          return currencyOption.code === normalizedPriceCurrencyCode;
        })
      ) {
        setStatus("", "warning", { key: "warnings.currencyNotAvailable" });
        syncSettingsControls();
        return Promise.resolve(null);
      }
      if (!state.isAuthenticated) {
        setStatus("", "warning", { key: "status.locked" });
        syncSettingsControls();
        return Promise.resolve(null);
      }

      state.arriveAtWorkTime = normalizedArriveAtWorkTime;
      state.workToHomeTime = normalizedTime;
      state.lastUpdateTime = normalizedLastUpdateTime;
      state.extraCarToleranceMinutes = normalizedExtraCarToleranceMinutes;
      state.priceCurrencyCode = normalizedPriceCurrencyCode;
      state.priceRateUnit = normalizedPriceRateUnit;
      state.vehicleSeatDefaults = Object.assign({}, normalizedSeatDefaults);
      state.vehiclePriceDefaults = Object.assign({}, normalizedPriceDefaults);
      state.vehicleToleranceDefaultMinutes = normalizedToleranceDefault;
      state.availableCurrencies = previousAvailableCurrencies;
      applyTransportVehicleSeatDefaults(state.vehicleSeatDefaults);
      applyTransportVehicleToleranceDefault(state.vehicleToleranceDefaultMinutes);
      state.settingsSaving = true;
      syncSettingsControls();
      return requestJson(`${TRANSPORT_API_PREFIX}/settings`, {
        method: "PUT",
        body: JSON.stringify({
          arrive_at_work_time: normalizedArriveAtWorkTime,
          work_to_home_time: normalizedTime,
          last_update_time: normalizedLastUpdateTime,
          extra_car_tolerance_minutes: normalizedExtraCarToleranceMinutes,
          default_car_seats: normalizedSeatDefaults.carro,
          default_minivan_seats: normalizedSeatDefaults.minivan,
          default_van_seats: normalizedSeatDefaults.van,
          default_bus_seats: normalizedSeatDefaults.onibus,
          price_currency_code: normalizedPriceCurrencyCode || null,
          price_rate_unit: normalizedPriceRateUnit,
          default_car_price: normalizedPriceDefaults.carro,
          default_minivan_price: normalizedPriceDefaults.minivan,
          default_van_price: normalizedPriceDefaults.van,
          default_bus_price: normalizedPriceDefaults.onibus,
          default_tolerance_minutes: normalizedToleranceDefault,
        }),
      })
        .then(function (response) {
          state.settingsLoaded = true;
          state.arriveAtWorkTime = normalizeTransportTimeValue(
            response && response.arrive_at_work_time,
            normalizedArriveAtWorkTime
          );
          state.workToHomeTime = String(
            response && response.work_to_home_time ? response.work_to_home_time : normalizedTime
          );
          state.lastUpdateTime = String(
            response && response.last_update_time ? response.last_update_time : normalizedLastUpdateTime
          );
          state.extraCarToleranceMinutes = normalizeVehicleToleranceSetting(
            response && response.extra_car_tolerance_minutes,
            normalizedExtraCarToleranceMinutes
          );
          state.priceCurrencyCode = normalizeTransportCurrencyCode(response && response.price_currency_code);
          state.priceRateUnit = normalizeTransportPriceRateUnit(
            response && response.price_rate_unit,
            normalizedPriceRateUnit
          );
          state.availableCurrencies = resolveTransportCurrencyOptions(
            response && response.available_currencies
          );
          state.vehicleSeatDefaults = applyTransportVehicleSeatDefaults(response);
          state.vehiclePriceDefaults = resolveTransportVehiclePriceDefaults(
            response,
            normalizedPriceDefaults
          );
          state.vehicleToleranceDefaultMinutes = applyTransportVehicleToleranceDefault(
            response && response.default_tolerance_minutes !== undefined
              ? response.default_tolerance_minutes
              : normalizedToleranceDefault
          );
          return loadDashboard(dateStore.getValue(), { announce: false }).then(function () {
            setStatus("", "success", { key: "status.settingsSaved" });
            return response;
          });
        })
        .catch(function (error) {
          state.arriveAtWorkTime = previousArriveAtWorkTime;
          state.workToHomeTime = previousWorkToHomeTime;
          state.lastUpdateTime = previousLastUpdateTime;
          state.extraCarToleranceMinutes = previousExtraCarToleranceMinutes;
          state.priceCurrencyCode = previousPriceCurrencyCode;
          state.priceRateUnit = previousPriceRateUnit;
          state.vehicleSeatDefaults = previousVehicleSeatDefaults;
          state.vehiclePriceDefaults = previousVehiclePriceDefaults;
          state.availableCurrencies = previousAvailableCurrencies;
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

    function saveTransportCurrencyOption() {
      const normalizedCurrencyCode = normalizeTransportCurrencyCode(
        settingsNewCurrencyCodeInput ? settingsNewCurrencyCodeInput.value : ""
      );
      const normalizedCurrencyLabel = normalizeTransportCurrencyLabel(
        settingsNewCurrencyLabelInput ? settingsNewCurrencyLabelInput.value : ""
      );

      if (!state.isAuthenticated) {
        setStatus("", "warning", { key: "status.locked" });
        return Promise.resolve(null);
      }

      if (!isValidTransportCurrencyCode(normalizedCurrencyCode)) {
        setStatus("", "warning", { key: "warnings.invalidCurrencyCode" });
        if (settingsNewCurrencyCodeInput && typeof settingsNewCurrencyCodeInput.focus === "function") {
          settingsNewCurrencyCodeInput.focus();
        }
        return Promise.resolve(null);
      }

      state.currencyCreateSaving = true;
      syncSettingsControls();
      return requestJson(`${TRANSPORT_API_PREFIX}/settings/currencies`, {
        method: "POST",
        body: JSON.stringify({
          code: normalizedCurrencyCode,
          display_label: normalizedCurrencyLabel || null,
        }),
      })
        .then(function (response) {
          state.availableCurrencies = resolveTransportCurrencyOptions(
            state.availableCurrencies.concat([response || {}])
          );
          state.priceCurrencyCode = normalizeTransportCurrencyCode(response && response.code);
          closeCurrencyCreatePanel();
          return saveTransportSettings(
            Object.assign({}, readTransportSettingsDraft(), {
              priceCurrencyCode: state.priceCurrencyCode,
            })
          );
        })
        .catch(function (error) {
          handleProtectedRequestError(error, t("status.couldNotAddCurrency"));
          return null;
        })
        .finally(function () {
          state.currencyCreateSaving = false;
          syncSettingsControls();
        });
    }

    function switchTransportLanguage(nextLanguageCode) {
      const resolvedCode = resolveLanguageCode(nextLanguageCode);
      const previousStatusDescriptor = {
        key: state.statusMessageKey,
        values: state.statusMessageValues && typeof state.statusMessageValues === "object"
          ? Object.assign({}, state.statusMessageValues)
          : null,
        message: state.statusMessageText,
        tone: state.statusMessageTone,
      };
      state.languageLoading = true;
      syncSettingsControls();
      setStatus("", "info", { key: "status.switchingLanguage", preserveState: true });

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
          syncStatusMessageCopy(previousStatusDescriptor);
          resolve();
        };

        if (typeof globalScope.requestAnimationFrame === "function") {
          globalScope.requestAnimationFrame(finishSwitch);
          return;
        }

        finishSwitch();
      });
    }

    function verifyTransportCredentials(requestToken, signature) {
      const credentials = readTransportAuthCredentials();
      if (!credentials.signature) {
        return Promise.resolve(null);
      }

      const currentSignature = signature || credentials.signature;
      if (state.isAuthenticated && currentSignature === state.lastVerifiedAuthSignature) {
        return Promise.resolve(null);
      }

      const authVerifyRequestController = typeof globalScope.AbortController === "function"
        ? new globalScope.AbortController()
        : null;
      state.authVerifyRequestController = authVerifyRequestController;

      return requestJson(`${TRANSPORT_API_PREFIX}/auth/verify`, {
        method: "POST",
        body: JSON.stringify({ chave: credentials.chave, senha: credentials.senha }),
        signal: authVerifyRequestController ? authVerifyRequestController.signal : undefined,
      })
        .then(function (response) {
          if (requestToken !== state.authVerifyToken) {
            return null;
          }

          if (response && response.authenticated && response.user) {
            state.lastVerifiedAuthSignature = currentSignature;
            setAuthenticationState(true, response.user, {});
            const structuredAccessGrantedMessage = resolveTransportApiStructuredMessage(response)
              || String(response && response.message || "").trim();
            const accessGrantedMessage = structuredAccessGrantedMessage || t("status.accessGranted");
            const accessGrantedOptions = resolveTransportApiStructuredMessageOptions(response)
              || (structuredAccessGrantedMessage ? undefined : { key: "status.accessGranted" });
            setStatus(accessGrantedMessage, "success", accessGrantedOptions);
            return Promise.all([
              loadDashboard(dateStore.getValue(), { announce: false }),
              loadTransportSettings({ silent: true }),
            ]);
          }

          state.lastVerifiedAuthSignature = "";
          setAuthenticationState(false, null, {});
          const structuredLockedMessage = resolveTransportApiStructuredMessage(response)
            || String(response && response.message || "").trim();
          const lockedMessage = structuredLockedMessage || getTransportLockedMessage();
          const lockedOptions = resolveTransportApiStructuredMessageOptions(response)
            || (structuredLockedMessage ? undefined : { key: "status.locked" });
          setStatus(lockedMessage, "warning", lockedOptions);
          return null;
        })
        .catch(function (error) {
          if (requestToken !== state.authVerifyToken) {
            return null;
          }
          if (error && error.name === "AbortError") {
            return null;
          }
          const structuredVerifyErrorMessage = resolveTransportApiStructuredMessage(error && error.payload)
            || localizeTransportApiMessage(error && error.message);
          const verifyErrorMessage = structuredVerifyErrorMessage || t("status.couldNotVerify");
          const verifyErrorOptions = resolveTransportApiStructuredMessageOptions(error && error.payload)
            || (structuredVerifyErrorMessage ? undefined : { key: "status.couldNotVerify" });
          setStatus(verifyErrorMessage, "error", verifyErrorOptions);
          return null;
        })
        .finally(function () {
          if (state.authVerifyRequestController === authVerifyRequestController) {
            state.authVerifyRequestController = null;
          }
        });
    }

    function scheduleTransportVerification(options) {
      const nextOptions = options || {};
      const verifySource = String(nextOptions.source || "input").trim().toLowerCase();
      const shouldVerifyImmediately = nextOptions.immediate === true;
      clearPendingAuthVerification();
      clearActiveAuthVerificationRequest();
      const credentials = readTransportAuthCredentials();
      const signature = credentials.signature;
      const previousSignature = state.authVerifySignature;
      if (!signature) {
        state.authVerifyToken += 1;
        state.authVerifySignature = "";
        if (!state.isAuthenticated && !state.sessionBootstrapPending) {
          setAuthenticationState(false, null, {});
          setStatus("", "warning", { key: "status.locked" });
        }
        return;
      }

      if (state.isAuthenticated && signature === state.lastVerifiedAuthSignature) {
        state.authVerifySignature = signature;
        return;
      }

      state.authVerifySignature = signature;

      if (state.sessionBootstrapPending && verifySource !== "bootstrap") {
        return;
      }

      if (verifySource === "input" && state.isAuthenticated && !shouldVerifyImmediately) {
        return;
      }

      if (signature === previousSignature && !shouldVerifyImmediately) {
        return;
      }

      state.authVerifyToken += 1;
      const requestToken = state.authVerifyToken;
      state.authVerifyTimer = globalScope.setTimeout(function () {
        state.authVerifyTimer = null;
        verifyTransportCredentials(requestToken, signature);
      }, shouldVerifyImmediately ? 0 : TRANSPORT_AUTH_VERIFY_DELAY_MS);
    }

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
        .finally(function () {
          state.aiRouteRequestPending = false;
          syncAiAgentSettingsControls({ preserveInputs: true });
        });
    }

    function openAiAgentSettingsModal() {
      if (!aiAgentModal) {
        return;
      }
      closeAiMenu();
      closeAiChangesModal();
      closeAiSettingsModal({ force: true });
      closeExpandedVehicleDetails({ render: false });
      state.aiAgentSettingsDraft = getDefaultAiAgentSettings();
      clearAiAgentFeedback();
      applyStaticTranslations();
      syncAiAgentSettingsControls();
      aiAgentModal.hidden = false;
      if (aiAgentEarliestBoardingInput && typeof aiAgentEarliestBoardingInput.focus === "function") {
        aiAgentEarliestBoardingInput.focus();
        return;
      }
      if (aiAgentArrivalAtWorkInput && typeof aiAgentArrivalAtWorkInput.focus === "function") {
        aiAgentArrivalAtWorkInput.focus();
      }
    }

    function closeAiAgentSettingsModal(options) {
      if (!aiAgentModal) {
        return;
      }
      const closeOptions = options || {};
      const hasActiveRun = state.aiRouteRequestPending
        || state.aiRoutePollingTimer !== null
        || shouldContinuePollingAiRouteRun(state.aiRouteRunStatus);
      if (!closeOptions.force && hasActiveRun && !state.aiRouteInBackground) {
        return;
      }

      state.aiAgentSettingsDraft = getDefaultAiAgentSettings();
      clearAiAgentFeedback();
      aiAgentModal.hidden = true;
      if (
        closeOptions.restoreFocus
        && aiMenuTrigger
        && typeof aiMenuTrigger.focus === "function"
      ) {
        aiMenuTrigger.focus();
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
        setStatus("", "warning", { key: "status.locked" });
        return false;
      }
      return true;
    }

    function syncVehicleModalFields(scope) {
      if (!vehicleForm) {
        return;
      }

      const normalizedScope = normalizeVehicleScope(scope);
      const isEditMode = isVehicleModalEditMode();
      const showExtraFields = !isEditMode && normalizedScope === "extra";
      const showWeekendPersistence = !isEditMode && normalizedScope === "weekend";
      const showRegularPersistence = !isEditMode && normalizedScope === "regular";

      syncVehicleModalCopy(normalizedScope);
      if (extraVehicleSection) {
        extraVehicleSection.hidden = !showExtraFields;
      }
      if (weekendPersistenceGroup) {
        weekendPersistenceGroup.hidden = !showWeekendPersistence;
      }
      if (regularPersistenceGroup) {
        regularPersistenceGroup.hidden = !showRegularPersistence;
      }
      if (extraServiceDateField) {
        extraServiceDateField.hidden = !showExtraFields;
      }
      if (extraDepartureField) {
        extraDepartureField.hidden = !showExtraFields;
      }
      if (extraRouteField) {
        extraRouteField.hidden = !showExtraFields;
      }
      weekendPersistenceFields.forEach(function (fieldElement) {
        fieldElement.hidden = !showWeekendPersistence;
      });
      regularPersistenceFields.forEach(function (fieldElement) {
        fieldElement.hidden = !showRegularPersistence;
      });
      if (vehicleForm.elements.route_kind) {
        if (!isEditMode && normalizedScope === "extra") {
          const currentRouteKind = String(vehicleForm.elements.route_kind.value || "").trim();
          vehicleForm.elements.route_kind.value = Object.prototype.hasOwnProperty.call(ROUTE_KIND_KEYS, currentRouteKind)
            ? currentRouteKind
            : getSelectedRouteKind();
        }
        vehicleForm.elements.route_kind.disabled = isEditMode || normalizedScope !== "extra";
      }
      syncExtraVehicleDepartureFieldCopy(normalizedScope);
      if (vehicleForm.elements.service_date) {
        vehicleForm.elements.service_date.required = !isEditMode && normalizedScope === "extra";
        vehicleForm.elements.service_date.disabled = isEditMode || normalizedScope !== "extra";
      }
      if (vehicleForm.elements.service_date && !isEditMode && normalizedScope !== "extra") {
        vehicleForm.elements.service_date.value = "";
      }
      if (vehicleForm.elements.departure_time) {
        vehicleForm.elements.departure_time.required = !isEditMode && normalizedScope === "extra";
        vehicleForm.elements.departure_time.disabled = isEditMode || normalizedScope !== "extra";
      }
      if (vehicleForm.elements.departure_time && !isEditMode && normalizedScope !== "extra") {
        vehicleForm.elements.departure_time.value = "";
      }
      if (!isEditMode) {
        if (vehicleForm.elements.every_saturday) {
          vehicleForm.elements.every_saturday.checked = false;
        }
        if (vehicleForm.elements.every_sunday) {
          vehicleForm.elements.every_sunday.checked = false;
        }
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
      closeAiMenu();
      closeExpandedVehicleDetails({ render: false });
      setVehicleModalContext({ mode: "create", scope: normalizedScope, vehicleId: null });
      vehicleModal.hidden = false;
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

    function openVehicleEditModal(vehicle) {
      if (!vehicleModal || !vehicleForm || !vehicle || vehicle.id === null || vehicle.id === undefined) {
        return;
      }

      const normalizedScope = normalizeVehicleScope(vehicle.service_scope || "regular");
      if (!canOpenVehicleModal(normalizedScope)) {
        return;
      }

      closeAiMenu();
      closeExpandedVehicleDetails({ render: false });
      setVehicleModalContext({ mode: "edit", scope: normalizedScope, vehicleId: vehicle.id });
      vehicleModal.hidden = false;
      vehicleForm.reset();
      clearVehicleModalFeedback();
      vehicleForm.elements.service_scope.value = normalizedScope;
      populateVehicleFormBaseFields(vehicle);

      if (vehicleForm.elements.service_date) {
        vehicleForm.elements.service_date.value = formatVehicleFormFieldValue(vehicle.service_date);
      }
      if (vehicleForm.elements.departure_time) {
        vehicleForm.elements.departure_time.value = formatVehicleFormFieldValue(vehicle.departure_time);
      }
      if (vehicleForm.elements.route_kind) {
        vehicleForm.elements.route_kind.value = ROUTE_KIND_KEYS[vehicle.route_kind]
          ? vehicle.route_kind
          : getSelectedRouteKind();
      }

      syncVehicleModalFields(normalizedScope);
      if (!focusVehicleFormField(resolveVehicleEditFocusField(vehicle))) {
        focusVehicleFormField("tipo");
      }
    }

    function closeVehicleModal() {
      if (!vehicleModal || !vehicleForm) {
        return;
      }
      vehicleModal.hidden = true;
      clearVehicleModalFeedback();
      vehicleForm.reset();
      setVehicleModalContext({ mode: "create", scope: "regular", vehicleId: null });
      syncVehicleModalCopy("regular");
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

    function getRequestRowProjects(requestRow) {
      if (!requestRow || typeof requestRow !== "object") {
        return [];
      }

      const rawProjectNames = Array.isArray(requestRow.projects) && requestRow.projects.length
        ? requestRow.projects
        : [requestRow.projeto];
      const normalizedProjectNames = [];
      const seenProjectNames = new Set();

      rawProjectNames.forEach(function (projectName) {
        const normalizedProjectName = String(projectName || "").trim();
        if (!normalizedProjectName || seenProjectNames.has(normalizedProjectName)) {
          return;
        }
        seenProjectNames.add(normalizedProjectName);
        normalizedProjectNames.push(normalizedProjectName);
      });

      return normalizedProjectNames;
    }

    function isRequestVisibleForProjects(requestRow) {
      const requestProjectNames = getRequestRowProjects(requestRow);
      if (!requestProjectNames.length) {
        return true;
      }
      return requestProjectNames.some(function (projectName) {
        return isProjectVisible(projectName);
      });
    }

    function getVisibleRequestsForKind(kind) {
      return getRequestsForKind(kind).filter(function (requestRow) {
        return isRequestVisibleForProjects(requestRow);
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

    function saveRequestRowBoardingTime(requestRow, boardingTime, routeKind) {
      if (!requestRow || !requestRow.id || !requestRow.service_date) {
        setStatus("", "error", { key: "status.couldNotSaveBoardingTime" });
        return Promise.resolve(null);
      }

      return requestJson(`${TRANSPORT_API_PREFIX}/assignments/boarding-time`, {
        method: "PUT",
        body: JSON.stringify({
          request_id: requestRow.id,
          service_date: requestRow.service_date,
          route_kind: getRouteKindForRequestRow(requestRow, routeKind),
          boarding_time: boardingTime,
        }),
      }).then(function (response) {
        const structuredBoardingTimeMessage = resolveTransportApiStructuredMessage(response)
          || String(response && response.message || "").trim();
        const boardingTimeMessage = structuredBoardingTimeMessage || t("status.boardingTimeSaved");
        const boardingTimeOptions = resolveTransportApiStructuredMessageOptions(response)
          || (structuredBoardingTimeMessage ? undefined : { key: "status.boardingTimeSaved" });
        setStatus(boardingTimeMessage, "success", boardingTimeOptions);
        return loadDashboard(dateStore.getValue(), { announce: false });
      }).catch(function (error) {
        if (handleProtectedRequestError(error, t("status.couldNotSaveBoardingTime"))) {
          return null;
        }
        throw error;
      });
    }

    function resolveVehicleDetailsScope(vehicle, detailOptions) {
      const resolvedOptions = detailOptions || {};
      return String(
        resolvedOptions.scope !== undefined && resolvedOptions.scope !== null
          ? resolvedOptions.scope
          : vehicle && vehicle.service_scope
      ).trim();
    }

    function resolveVehicleDetailsRouteKind(vehicle, detailOptions) {
      const resolvedOptions = detailOptions || {};
      const scope = resolveVehicleDetailsScope(vehicle, resolvedOptions);
      return resolvedOptions.routeKind || getRouteKindForVehicle(scope, vehicle);
    }

    function resolveVehicleDetailsPassengerTime(vehicle, requestRow, detailOptions) {
      const resolvedOptions = detailOptions || {};
      const scope = resolveVehicleDetailsScope(vehicle, resolvedOptions);
      const routeKind = resolveVehicleDetailsRouteKind(vehicle, resolvedOptions);

      return resolveVehiclePassengerOperationalTime(
        scope,
        vehicle,
        requestRow,
        state.dashboard,
        state.arriveAtWorkTime,
        state.vehicleReferenceClock,
        state.workToHomeTime,
        routeKind
      );
    }

    function buildVehicleDetailsRowViewModels(vehicle, assignedRows, detailOptions) {
      const resolvedOptions = detailOptions || {};
      const previewRequestRow = resolvedOptions.previewRequestRow || null;
      const resolvedRouteKind = resolveVehicleDetailsRouteKind(vehicle, resolvedOptions);
      const scope = resolveVehicleDetailsScope(vehicle, resolvedOptions);
      const visiblePassengerRows = buildVehiclePassengerPreviewRows(
        assignedRows,
        previewRequestRow,
        VEHICLE_DETAILS_MAX_ROWS
      );

      const effectiveDepartureTime = getEffectiveWorkToHomeDepartureTime(state.dashboard, state.workToHomeTime);
      const vehicleW2hTime = normalizeTransportTimeValue(
        getVehicleDepartureTime(vehicle, effectiveDepartureTime, scope),
        ""
      );

      return visiblePassengerRows.map(function (requestRow) {
        const timeState = resolveVehicleDetailsPassengerTime(vehicle, requestRow, resolvedOptions);
        const normalizedTime = normalizeTransportTimeValue(timeState && timeState.time, "");
        const hasTime = isValidTransportTimeValue(normalizedTime);
        const isPreviewRow = Boolean(
          previewRequestRow
          && requestRow
          && Number(requestRow.id) === Number(previewRequestRow.id)
        );
        const isConfirmed = String(requestRow && requestRow.assignment_status || "").trim() === "confirmed";
        const routeKind = getRouteKindForRequestRow(requestRow, resolvedRouteKind);
        const h2wBoardingTime = normalizeTransportTimeValue(requestRow && requestRow.boarding_time, "");
        const hasH2wBoardingTime = isValidTransportTimeValue(h2wBoardingTime);

        return {
          requestRow,
          isPreviewRow,
          isConfirmed,
          routeKind,
          timeState,
          resolvedTime: hasH2wBoardingTime ? h2wBoardingTime : "",
          timeSortValue: hasTime
            ? String(parseTransportTimeToMinutes(normalizedTime)).padStart(4, "0")
            : "9999",
          h2wBoardingTime: hasH2wBoardingTime ? h2wBoardingTime : "",
          w2hTime: vehicleW2hTime,
          canEditBoardingTime: Boolean(
            requestRow
            && !isPreviewRow
            && isConfirmed
            && routeKind === "home_to_work"
          ),
        };
      }).sort(function (a, b) {
        if (a.timeSortValue < b.timeSortValue) return -1;
        if (a.timeSortValue > b.timeSortValue) return 1;
        return 0;
      });
    }

    function buildVehicleDetailsColumnDefinitions(vehicle, rowViewModels, detailOptions) {
      return [
        {
          key: "passenger",
          headerKey: "vehicleDetails.passengerHeader",
          headerClassName: "transport-vehicle-passenger-name-header",
          cellClassName: "transport-vehicle-passenger-name",
          getSortValue: function (rowViewModel) {
            return String(rowViewModel && rowViewModel.requestRow && rowViewModel.requestRow.nome || "").trim().toLowerCase();
          },
          renderCell: function (rowViewModel) {
            return createNode(
              "span",
              "transport-vehicle-passenger-name-value",
              String(rowViewModel && rowViewModel.requestRow && rowViewModel.requestRow.nome || "")
            );
          },
        },
        {
          key: "h2w-boarding",
          headerKey: "vehicleDetails.h2wBoardingHeader",
          headerClassName: "transport-vehicle-passenger-time-header",
          cellClassName: "transport-vehicle-passenger-time",
          getSortValue: function (rowViewModel) {
            return rowViewModel && rowViewModel.timeSortValue ? rowViewModel.timeSortValue : "9999";
          },
          renderCell: function (rowViewModel) {
            if (rowViewModel && rowViewModel.canEditBoardingTime) {
              return createVehiclePassengerTimeEditor(rowViewModel);
            }
            var bt = rowViewModel && rowViewModel.h2wBoardingTime || "";
            return createNode(
              "span",
              "transport-vehicle-passenger-time-value" + (bt ? "" : " is-placeholder"),
              bt || t("vehicleDetails.timeMissing")
            );
          },
        },
        {
          key: "w2h-time",
          headerKey: "vehicleDetails.w2hTimeHeader",
          headerClassName: "transport-vehicle-passenger-w2h-time-header",
          cellClassName: "transport-vehicle-passenger-w2h-time",
          renderCell: function (rowViewModel) {
            var wt = rowViewModel && rowViewModel.w2hTime || "";
            return createNode(
              "span",
              "transport-vehicle-passenger-time-value" + (wt ? "" : " is-placeholder"),
              wt || t("vehicleDetails.timeMissing")
            );
          },
        },
        {
          key: "action",
          headerKey: "vehicleDetails.actionHeader",
          headerClassName: "transport-vehicle-passenger-action-header",
          cellClassName: "transport-vehicle-passenger-status",
          renderCell: function (rowViewModel) {
            if (rowViewModel && rowViewModel.requestRow && !rowViewModel.isPreviewRow) {
              return createPassengerRemoveButton(rowViewModel.requestRow, rowViewModel.routeKind);
            }
            return null;
          },
        },
      ];
    }

    function createVehicleDetailsTableHead(columns) {
      const tableHead = createNode("thead", "transport-vehicle-passenger-table-head");
      const headerRow = createNode("tr", "transport-vehicle-passenger-header-row");

      columns.forEach(function (column) {
        const headerCell = createNode("th", column.headerClassName, t(column.headerKey));
        headerCell.setAttribute("scope", "col");
        headerCell.dataset.columnKey = column.key;
        headerRow.appendChild(headerCell);
      });

      tableHead.appendChild(headerRow);
      return tableHead;
    }

    function createVehicleDetailsTableRow(columns, rowViewModel) {
      const tableRow = createNode("tr", "transport-vehicle-passenger-row");

      tableRow.dataset.requestId = String(rowViewModel && rowViewModel.requestRow && rowViewModel.requestRow.id || "");
      tableRow.dataset.timeMode = String(rowViewModel && rowViewModel.timeState && rowViewModel.timeState.mode || "");

      columns.forEach(function (column) {
        const cell = createNode("td", column.cellClassName);
        const sortValue = typeof column.getSortValue === "function" ? column.getSortValue(rowViewModel) : "";
        const content = typeof column.renderCell === "function" ? column.renderCell(rowViewModel) : null;

        cell.dataset.columnKey = column.key;
        if (column.key === "operational-time") {
          cell.dataset.timeMode = String(rowViewModel && rowViewModel.timeState && rowViewModel.timeState.mode || "");
          cell.dataset.timeField = String(rowViewModel && rowViewModel.timeState && rowViewModel.timeState.timeField || "");
        }
        if (sortValue !== null && sortValue !== undefined && String(sortValue).trim()) {
          cell.dataset.sortValue = String(sortValue);
        }

        if (content) {
          cell.appendChild(content);
        } else {
          cell.innerHTML = "&nbsp;";
        }
        tableRow.appendChild(cell);
      });

      return tableRow;
    }

    function getVehicleDetailsTimeHeaderKey(timeState) {
      if (timeState && timeState.mode === "eta") {
        return "vehicleDetails.boardingHeader";
      }
      if (timeState && timeState.mode === "etd") {
        return "vehicleDetails.departureHeader";
      }
      return "vehicleDetails.timeHeader";
    }

    function createVehiclePassengerTimeValue(timeState) {
      const resolvedTime = normalizeTransportTimeValue(timeState && timeState.time, "");
      const hasTime = isValidTransportTimeValue(resolvedTime);
      return createNode(
        "span",
        `transport-vehicle-passenger-time-value${hasTime ? "" : " is-placeholder"}`,
        hasTime ? resolvedTime : t("vehicleDetails.timeMissing")
      );
    }

    function createVehiclePassengerTimeEditor(rowViewModel) {
      const editor = createNode("div", "transport-vehicle-passenger-time-editor");
      const input = document.createElement("input");
      const requestRow = rowViewModel && rowViewModel.requestRow;
      const routeKind = rowViewModel && rowViewModel.routeKind;
      const timeState = rowViewModel && rowViewModel.timeState;
      let committedValue = normalizeTransportTimeValue(rowViewModel && rowViewModel.resolvedTime, "");
      let isSaving = false;

      input.type = "text";
      input.value = committedValue;
      input.maxLength = 5;
      input.setAttribute("inputmode", "numeric");
      input.setAttribute("placeholder", t("vehicleDetails.boardingPlaceholder"));
      input.setAttribute("pattern", "[0-2][0-9]:[0-5][0-9]");
      input.setAttribute(
        "aria-label",
        t("vehicleDetails.boardingInputAria", { name: String(requestRow && requestRow.nome || "") })
      );
      input.className = "transport-vehicle-passenger-time-input";

      function syncEditorState() {
        const currentValue = String(input.value || "").trim();
        const resolvedValue = normalizeTransportTimeValue(currentValue, "");
        const hasValue = isValidTransportTimeValue(resolvedValue);
        editor.classList.toggle("is-placeholder", !hasValue);
        editor.classList.toggle("is-saving", isSaving);
        input.classList.toggle("is-placeholder", !hasValue);
        input.classList.toggle("is-saving", isSaving);
        input.disabled = isSaving;
        input.setAttribute("aria-busy", String(isSaving));
      }

      function restoreCommittedValue() {
        input.value = committedValue;
        syncEditorState();
      }

      function persistBoardingTime() {
        if (isSaving) {
          return Promise.resolve(null);
        }

        const rawValue = String(input.value || "").trim();
        if (rawValue && !isValidTransportTimeValue(rawValue)) {
          setStatus("", "warning", { key: "warnings.invalidBoardingTime" });
          restoreCommittedValue();
          return Promise.resolve(null);
        }

        const nextValue = rawValue || "";
        if (nextValue === committedValue) {
          syncEditorState();
          return Promise.resolve(null);
        }

        isSaving = true;
        syncEditorState();
        return saveRequestRowBoardingTime(requestRow, nextValue || null, routeKind)
          .then(function (result) {
            isSaving = false;
            if (result === null) {
              restoreCommittedValue();
              return null;
            }

            committedValue = nextValue;
            input.value = committedValue;
            syncEditorState();
            return result;
          })
          .catch(function () {
            isSaving = false;
            restoreCommittedValue();
            return null;
          });
      }

      input.addEventListener("input", function () {
        if (isSaving) {
          return;
        }
        syncEditorState();
      });

      input.addEventListener("blur", function () {
        void persistBoardingTime();
      });

      input.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault();
          void persistBoardingTime();
          return;
        }
        if (event.key === "Escape") {
          event.preventDefault();
          restoreCommittedValue();
        }
      });

      editor.appendChild(input);
      syncEditorState();
      return editor;
    }

    function createVehiclePassengerTimeContent(rowViewModel) {
      if (rowViewModel && rowViewModel.canEditBoardingTime) {
        return createVehiclePassengerTimeEditor(rowViewModel);
      }

      return createVehiclePassengerTimeValue(rowViewModel && rowViewModel.timeState);
    }

    function createVehicleDetailsPanel(vehicle, assignedRows, options) {
      const detailOptions = options || {};
      const previewRequestRow = detailOptions.previewRequestRow || null;
      const detailsPanel = createNode("div", "transport-vehicle-details");
      const passengerTableShell = createNode("div", "transport-vehicle-passenger-table-shell");
      const passengerTable = createNode("table", "transport-vehicle-passenger-table");
      const tableBody = createNode("tbody");
      const rowViewModels = buildVehicleDetailsRowViewModels(vehicle, assignedRows, detailOptions);
      const columns = buildVehicleDetailsColumnDefinitions(vehicle, rowViewModels, detailOptions);

      if (rowViewModels.length) {
        passengerTable.appendChild(createVehicleDetailsTableHead(columns));
        rowViewModels.forEach(function (rowViewModel) {
          tableBody.appendChild(createVehicleDetailsTableRow(columns, rowViewModel));
        });

        passengerTable.appendChild(tableBody);
        passengerTableShell.appendChild(passengerTable);
      } else {
        passengerTableShell.appendChild(
          createNode("p", "transport-vehicle-passenger-empty", t("empty.noPassengersAssigned"))
        );
      }

      detailsPanel.appendChild(passengerTableShell);

      if (previewRequestRow) {
        const previewActions = createNode("div", "transport-vehicle-preview-actions");
        const cancelButton = createNode("button", "transport-secondary-button", t("modal.actions.cancel"));
        const confirmButton = createNode("button", "transport-primary-button", t("misc.confirm"));
        const pendingAllocationMessage = getVehiclePendingAllocationMessage(vehicle);

        cancelButton.type = "button";
        confirmButton.type = "button";
        confirmButton.disabled = Boolean(pendingAllocationMessage);
        if (pendingAllocationMessage) {
          confirmButton.title = pendingAllocationMessage;
          confirmButton.setAttribute("aria-label", pendingAllocationMessage);
        }

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
          if (pendingAllocationMessage) {
            setStatus(pendingAllocationMessage, "warning");
            return;
          }
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

      const actionRow = createNode("div", "transport-vehicle-details-actions");
      const editButton = createNode("button", "transport-secondary-button transport-vehicle-edit-button", t("misc.edit"));

      editButton.type = "button";
      editButton.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        openVehicleEditModal(vehicle);
      });

      actionRow.appendChild(editButton);
      actionRow.appendChild(deleteButton);
      detailsPanel.insertBefore(actionRow, passengerTableShell);
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
        metaParts.push(t("misc.assignedTo", { plate: formatPendingVehicleField(requestRow.assigned_vehicle.placa) }));
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
    }).then(function (response) {
      const structuredAllocationUpdatedMessage = resolveTransportApiStructuredMessage(response)
        || String(response && response.message || "").trim();
      const allocationUpdatedMessage = structuredAllocationUpdatedMessage || t("status.allocationUpdated");
      const allocationUpdatedOptions = resolveTransportApiStructuredMessageOptions(response)
        || (structuredAllocationUpdatedMessage ? undefined : { key: "status.allocationUpdated" });
      setStatus(allocationUpdatedMessage, "success", allocationUpdatedOptions);
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
        setStatus("", "error", { key: "status.couldNotRejectSelectedRequest" });
        return Promise.resolve();
      }

      return requestJson(`${TRANSPORT_API_PREFIX}/requests/reject`, {
        method: "POST",
        body: JSON.stringify({
          request_id: requestRow.id,
          service_date: requestRow.service_date,
          route_kind: getRouteKindForRequestRow(requestRow),
        }),
      }).then(function (response) {
        const structuredRequestRejectedMessage = resolveTransportApiStructuredMessage(response)
          || String(response && response.message || "").trim();
        const requestRejectedMessage = structuredRequestRejectedMessage || t("status.requestRejected");
        const requestRejectedOptions = resolveTransportApiStructuredMessageOptions(response)
          || (structuredRequestRejectedMessage ? undefined : { key: "status.requestRejected" });
        setStatus(requestRejectedMessage, "success", requestRejectedOptions);
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
        setStatus("", "error", { key: "status.couldNotUpdateAllocation" });
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
        setStatus("", "error", { key: "warnings.vehicleCannotBeRemoved" });
        return Promise.resolve();
      }

      const deleteServiceDate = vehicle.service_date || getCurrentServiceDateIso();

      return requestJson(
        `${TRANSPORT_API_PREFIX}/vehicles/${encodeURIComponent(String(vehicle.schedule_id))}?service_date=${encodeURIComponent(deleteServiceDate)}`,
        {
          method: "DELETE",
        }
      )
        .then(function (response) {
          const structuredVehicleDeletedMessage = resolveTransportApiStructuredMessage(response)
            || String(response && response.message || "").trim();
          const vehicleDeletedMessage = structuredVehicleDeletedMessage || t("status.vehicleDeleted");
          const vehicleDeletedOptions = resolveTransportApiStructuredMessageOptions(response)
            || (structuredVehicleDeletedMessage ? undefined : { key: "status.vehicleDeleted" });
          setStatus(vehicleDeletedMessage, "success", vehicleDeletedOptions);
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
      const departureTime = getVehicleReferenceLabel(
        scope,
        vehicle,
        state.dashboard,
        state.arriveAtWorkTime,
        state.vehicleReferenceClock,
        state.workToHomeTime,
        vehicle && vehicle.route_kind
      );
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
      const pendingAllocationMessage = getVehiclePendingAllocationMessage(vehicle);

      vehicleButton.type = "button";
      vehicleButton.dataset.vehicleId = String(vehicle.id);
      vehicleButton.dataset.vehicleScope = scope;
      vehicleButton.dataset.vehicleDetailsAnchorKey = vehicleDetailsKey;
      vehicleButton.title = t("misc.vehicleButtonTitle", {
        type: formatPendingVehicleField(vehicle.tipo, mapVehicleTypeLabel),
        occupancy: formatVehicleOccupancyLabel(vehicle, assignedCount),
      });
      vehicleButton.classList.toggle("is-selectable", isDropTarget);
      vehicleButton.classList.toggle("is-preview-target", !!previewRequestRow);
      vehicleButton.classList.toggle("is-details-open", isExpanded);
      vehicleButton.classList.toggle("is-pending-allocation", !!pendingAllocationMessage);
      tileElement.classList.toggle("is-expanded", isExpanded);
      if (!isDropTarget && !previewRequestRow) {
        vehicleButton.classList.add("is-idle");
      }

      const iconImage = document.createElement("img");
      iconImage.className = "transport-vehicle-icon";
      iconImage.src = mapVehicleIconPath(vehicle);
      iconImage.alt = "";

      const plateLabel = createPendingVehicleFieldNode("span", "transport-vehicle-plate", vehicle.placa);
      const occupancyLabel = createNode(
        "span",
        "transport-vehicle-occupancy",
        formatVehicleOccupancyCount(vehicle, assignedCount)
      );
      if (isPendingVehicleField(vehicle.lugares)) {
        occupancyLabel.classList.add("transport-pending-value");
      }
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
      if (pendingAllocationMessage) {
        vehicleButton.title = `${vehicleButton.title} | ${pendingAllocationMessage}`;
      }
      vehicleButton.setAttribute("aria-label", vehicleButton.title);
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
          scope,
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
        const typeCell = createNode("td", "transport-vehicle-management-type");
        const plateCell = createNode("td", "transport-vehicle-management-plate-cell");
        const occupancyCell = createNode("td", "transport-vehicle-management-occupancy");
        const actionsCell = createNode("td", "transport-vehicle-management-actions");
        const vehicleType = createPendingVehicleFieldNode(
          "span",
          "transport-vehicle-management-type-value",
          rowData.tipo,
          formatVehicleTypeTableValue
        );
        const vehiclePlate = createPendingVehicleFieldNode("strong", "transport-vehicle-management-plate", rowData.placa);
        const occupancyValue = createNode(
          "span",
          "transport-vehicle-management-occupancy-value",
          formatVehicleOccupancyCount(rowData, rowData.assigned_count)
        );
        const departureTime = getVehicleReferenceLabel(
          scope,
          rowData,
          state.dashboard,
          state.arriveAtWorkTime,
          state.vehicleReferenceClock,
          state.workToHomeTime,
          rowData && rowData.route_kind
        );
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

        if (isPendingVehicleField(rowData.lugares)) {
          occupancyValue.classList.add("transport-pending-value");
        }

        typeCell.appendChild(vehicleType);
        plateCell.appendChild(vehiclePlate);
        occupancyCell.appendChild(occupancyValue);
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
      const vehiclePanelsRoot = document.getElementById("tela01main_dir");
      if (vehiclePanelsRoot) {
        syncVehiclePanelExplicitHeights(vehiclePanelsRoot);
        updateVehicleGridLayouts(vehiclePanelsRoot);
      }
      syncRequestSectionToggleState();
    }

    function clearDashboard() {
      clearVehicleReferenceClock();
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
        if (state.sessionBootstrapPending) {
          return Promise.resolve(null);
        }
        state.dashboard = null;
        clearDashboard();
        setStatus("", "warning", { key: "status.locked" });
        return Promise.resolve(null);
      }

      const normalizedDate = startOfLocalDay(selectedDate || dateStore.getValue());
      const serviceDate = formatIsoDate(normalizedDate);
      const routeKind = getSelectedRouteKind();

      if (isTransportPageHidden() && loadOptions.allowWhileHidden !== true) {
        queueDeferredDashboardLoad(normalizedDate, loadOptions);
        return state.dashboardLoadPromise || Promise.resolve(null);
      }

      if (state.dashboardLoadPromise) {
        queueDashboardLoad(normalizedDate, loadOptions);
        return state.dashboardLoadPromise;
      }

      state.pendingAssignmentPreview = null;
      state.dragRequestId = null;
      state.isLoading = true;
      clearVehicleReferenceModeTimer();
      syncRouteTimeControls();
      if (shouldAnnounce) {
        setStatus("", "info", { key: "status.loadingDashboard" });
      }
      state.dashboardLoadPromise = requestJson(
        `${TRANSPORT_API_PREFIX}/dashboard?service_date=${encodeURIComponent(serviceDate)}&route_kind=${encodeURIComponent(routeKind)}`
      )
        .then(function (dashboard) {
          state.dashboard = dashboard || null;
          syncTransportReferenceClock(state.dashboard);
          reconcileProjectVisibility();
          state.selectedRouteKind = (dashboard && dashboard.selected_route) || routeKind;
          syncRouteInputs();
          syncRouteTimeControls();
          if (shouldAnnounce) {
            setStatus("", "info", { key: "status.dashboardUpdated" });
          }
          renderDashboard();
          applyStaticTranslations();
          scheduleVehicleReferenceModeTimer();
        })
        .catch(function (error) {
          state.dashboard = null;
          clearDashboard();
          applyStaticTranslations();
          if (error && Number(error.status) === 401) {
            clearTransportSession(getTransportSessionExpiredMessage());
            return;
          }
          const structuredDashboardErrorMessage = resolveTransportApiStructuredMessage(error && error.payload)
            || localizeTransportApiMessage(error && error.message);
          const dashboardErrorMessage = structuredDashboardErrorMessage || t("status.couldNotLoadDashboard");
          const dashboardErrorOptions = resolveTransportApiStructuredMessageOptions(error && error.payload)
            || (structuredDashboardErrorMessage ? undefined : { key: "status.couldNotLoadDashboard" });
          setStatus(dashboardErrorMessage, "error", dashboardErrorOptions);
        })
        .finally(function () {
          const queuedLoad = state.queuedDashboardLoad;
          state.dashboardLoadPromise = null;
          if (queuedLoad && state.isAuthenticated) {
            state.queuedDashboardLoad = null;
            if (isTransportPageHidden()) {
              queueDeferredDashboardLoad(queuedLoad.selectedDate, queuedLoad.options);
              state.isLoading = false;
              syncRouteTimeControls();
              return null;
            }
            return loadDashboard(queuedLoad.selectedDate, queuedLoad.options);
          }
          state.queuedDashboardLoad = null;
          state.isLoading = false;
          syncRouteTimeControls();
        });
      return state.dashboardLoadPromise;
    }

    return {
      __testCreateVehicleDetailsPanel: createVehicleDetailsPanel,
      bootstrapTransportSession,
      closeRouteTimePopover,
      handlePageVisibilityChange,
      loadDashboard,
      refreshVehicleGridLayouts: function () {
        const vehiclePanelsRoot = document.getElementById("tela01main_dir");
        if (vehiclePanelsRoot) {
          syncVehiclePanelExplicitHeights(vehiclePanelsRoot);
          updateVehicleGridLayouts(vehiclePanelsRoot);
          syncVehiclePanelResizeHandleState(vehiclePanelsRoot);
        } else {
          updateVehicleGridLayouts(document);
          syncVehiclePanelResizeHandleState(document);
        }
        scheduleExpandedVehicleDetailsPositionSync();
        syncAiButtonPlacement();
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
    document.querySelectorAll("[data-panel-resize-handle]").forEach(enableVehiclePanelResizeHandle);
    const vehiclePanelsRoot = document.getElementById("tela01main_dir");
    if (vehiclePanelsRoot) {
      syncVehiclePanelExplicitHeights(vehiclePanelsRoot);
      updateVehicleGridLayouts(vehiclePanelsRoot);
      syncVehiclePanelResizeHandleState(vehiclePanelsRoot);
    }
    const pageController = createTransportPageController(dateStore);
    globalScope.CheckingTransportPageController = pageController;
    globalScope.addEventListener("resize", function () {
      pageController.refreshVehicleGridLayouts();
    });
    document.addEventListener("visibilitychange", function () {
      pageController.handlePageVisibilityChange();
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
    extractStructuredTransportApiPayload,
    formatApiErrorMessage,
    formatTransportDate,
    formatIsoDate,
    formatExtraVehicleReferenceLabel,
    getEffectiveWorkToHomeDepartureTime,
    getExtraVehicleDepartureFieldKey,
    getTransportDateState,
    getDefaultAiAgentSettings,
    getVehicleDepartureTime,
    getVehicleReferenceLabel,
    getRoutineVehicleReferenceMode,
    getVehiclePendingAllocationMessage,
    getOrdinalSuffix,
    localizeTransportApiMessage,
    resolveTransportApiStructuredMessage,
    isPendingVehicleField,
    isVehicleReadyForAllocation,
    isValidTransportTimeValue,
    formatPendingVehicleField,
    formatVehicleOccupancyLabel,
    formatVehicleOccupancyCount,
    getDefaultVehicleFormValues,
    getDefaultVehicleSeatCount,
    getDefaultVehicleToleranceMinutes,
    formatTransportCurrencyOptionLabel,
    formatTransportCurrencyAmount,
    formatTransportPriceInputValue,
    normalizeTransportCurrencyCode,
    normalizeTransportPriceRateUnit,
    applyTransportVehicleToleranceDefault,
    resolveTransportCurrencyOptions,
    resolveTransportVehiclePriceDefaults,
    getActiveTransportLanguageCode: getActiveLanguageCode,
    setActiveTransportLanguageCode: setActiveLanguageCode,
    translateTransportText: t,
    buildVehicleBasePayload,
    resolveVehicleEditFocusField,
    syncVehicleTypeDependentDefaults,
    buildVehiclePassengerAwarenessRows,
    getPassengerAwarenessState,
    parseStoredTransportDate,
    resolveStoredTransportDate,
    setStoredTransportDate,
    shouldHighlightRequestName,
    mapVehicleIconPath,
    buildVehiclePassengerPreviewRows,
    groupAssignedRequestsByVehicleForDate,
    canRequestBeDroppedOnVehicle,
    resolveVehicleModalOpenState,
    resolveVehicleCreateValidationError,
    resolveVehicleSaveReloadDate,
    readAiAgentSettingsDraft,
    validateAiAgentSettingsDraft,
    getAiAgentRequestKindLabel,
    buildAiAgentSubmittingFeedbackOptions,
    buildTransportAiSettingsUpdatePayload,
    buildTransportAiDashboardScope,
    buildTransportAiRouteCalculationPayload,
    shouldContinuePollingAiRouteRun,
    hasRenderableTransportAiReview,
    resolveTransportAiStructuredMessage,
    resolveTransportAiBaselineComplement,
    getTransportAiSuggestionKey,
    buildTransportAiLatestSuggestionUrl,
    buildTransportAiSuggestionCommandUrl,
    getDefaultTransportAiSettingsDraft,
    normalizeTransportAiSettingsProvider,
    getTransportAiBidirectionalPlanContract,
    getTransportAiReviewTargetContract,
    readTransportAiSettingsDraft,
    resolveTransportAiSettingsProviderDefaults,
    shouldRefreshDashboardAfterAiSuggestionCommand,
    resolveAiChangesCommandState,
    renderAiChangesSummary,
    renderAiVehicleChanges,
    renderAiPassengerAllocations,
    renderAiRouteItineraries,
    renderAiChangesAudit,
    createTransportReferenceClock,
    parsePositiveNumber,
    parseTransportTimeToMinutes,
    formatRoutineVehicleReferenceLabel,
    resolveVehiclePassengerOperationalTime,
    resolveVehicleReferenceMode,
    getDefaultVehiclePanelHeight,
    getRoutineVehicleReferenceLabel,
    isVehiclePanelResizeEnabledForViewport,
    resolveTransportReferenceNow,
    resolveRoutineVehicleReferenceMode,
    resolveNextRoutineVehicleReferenceDelayMs,
    resolveVehiclePanelExplicitHeight,
    resolveVehiclePanelResizedHeight,
    resolvePanelSizes,
    resolveResizeConfig,
    updateVehicleGridLayout,
    updateVehicleGridLayouts,
    resolveVehicleDetailsPosition,
    startOfLocalDay,
    shiftLocalDay,
  };

  if (typeof document !== "undefined") {
    applyInitialDeclarativeTranslations();
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initTransportPage, { once: true });
    } else {
      initTransportPage();
    }
  }

  globalScope.CheckingTransportPage = transportPageApi;

  if (typeof module !== "undefined" && module.exports) {
    module.exports = Object.assign({}, transportPageApi, {
      __testCreateVehicleDetailsPanel: function () {
        const pageController = globalScope.CheckingTransportPageController;
        if (!pageController || typeof pageController.__testCreateVehicleDetailsPanel !== "function") {
          throw new Error("Transport page controller test helper is unavailable.");
        }
        return pageController.__testCreateVehicleDetailsPanel.apply(pageController, arguments);
      },
    });
  }
})(typeof window !== "undefined" ? window : globalThis);
