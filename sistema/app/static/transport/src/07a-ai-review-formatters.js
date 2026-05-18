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

