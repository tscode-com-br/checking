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

