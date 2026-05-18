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

