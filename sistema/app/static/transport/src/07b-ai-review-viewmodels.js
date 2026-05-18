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

