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

