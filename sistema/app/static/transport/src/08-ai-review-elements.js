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
